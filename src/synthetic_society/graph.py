"""Knowledge-graph extraction: seed text -> KnowledgeGraph.

Two-pass:
  1) entity extraction (typed, with attributes)
  2) relation extraction (typed edges between extracted entities)

Both passes use the same LLM with `response_format=json_object`. The graph
is built in-memory (NetworkX) and persisted as JSON in the run record.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from .llm import LLMClient
from .schema import Entity, KnowledgeGraph, Relation

log = logging.getLogger(__name__)


ENTITY_SYSTEM = """You are an entity extractor for an Indian-context knowledge graph.

Extract every concrete entity the seed text mentions or strongly implies.
Types you should use:
  Person, Organization, Company, Product, Brand, Event, Policy, Location,
  City, State, Community, Hashtag, Party, Religion, Sector, Asset, Risk

Rules:
- Names are in the original script (Devanagari, Tamil, etc. — preserve them).
- Add 2-5 attributes per entity when you can infer them (role, sector, region,
  price-point, sentiment-cue, etc.). Be conservative; skip if unsure.
- For ambiguous references, mark `attrs.canonical = true` so we can dedupe later.
- Output JSON only. Format:
{
  "entities": [
    {"id": "snake_case_id", "type": "Product", "name": "...", "attrs": {...}}
  ]
}"""


RELATION_SYSTEM = """You are a relation extractor for an Indian-context knowledge graph.

Given a seed text and the entities already extracted, produce all directed
relations between them. Use only these relation kinds:
  owns, employs, part_of, located_in, competes_with, partners_with,
  regulates, opposes, supports, follows, mentions, targets, sells_to,
  manufactures, distributes, markets_to, boycotted_by, endorsed_by,
  invested_in, acquired_by, parent_of, child_of, spouse_of

Rules:
- Both endpoints must be entity ids from the input list. If a needed entity
  is missing, add it under `extra_entities` with the same shape as before.
- weight ∈ [0, 1] encodes confidence/strength.
- Output JSON only. Format:
{
  "relations": [
    {"src": "...", "dst": "...", "kind": "...", "weight": 0.7, "attrs": {}}
  ],
  "extra_entities": []
}"""


class GraphBuilder:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    async def build(self, seed_text: str, *, hint: str = "") -> KnowledgeGraph:
        log.info("Extracting entities from seed (%d chars)", len(seed_text))
        entities_raw = await self._extract_entities(seed_text, hint)
        entities = [
            Entity(
                id=e["id"],
                type=e["type"],
                name=e["name"],
                attrs=e.get("attrs", {}),
            )
            for e in entities_raw
        ]

        log.info("Extracting relations between %d entities", len(entities))
        rels_raw = await self._extract_relations(seed_text, entities)
        relations = [
            Relation(
                src=r["src"],
                dst=r["dst"],
                kind=r["kind"],
                weight=float(r.get("weight", 0.5)),
                attrs=r.get("attrs", {}),
            )
            for r in rels_raw
        ]

        # Dedupe entities by id, keep first.
        seen: set[str] = set()
        unique_entities: list[Entity] = []
        for e in entities:
            if e.id in seen:
                continue
            seen.add(e.id)
            unique_entities.append(e)

        return KnowledgeGraph(entities=unique_entities, relations=relations)

    async def _extract_entities(self, text: str, hint: str) -> list[dict[str, Any]]:
        user = f"Seed text:\n```\n{text[:6000]}\n```\n"
        if hint:
            user += f"\nFocus hint: {hint}\n"
        out = await self.llm.chat_json(
            [
                {"role": "system", "content": ENTITY_SYSTEM},
                {"role": "user", "content": user},
            ],
            temperature=0.0,
        )
        return out.get("entities", [])

    async def _extract_relations(
        self, text: str, entities: list[Entity]
    ) -> list[dict[str, Any]]:
        ent_table = "\n".join(
            f"- {e.id} ({e.type}): {e.name}" for e in entities
        )
        user = (
            f"Seed text:\n```\n{text[:6000]}\n```\n\n"
            f"Entities:\n{ent_table}\n\n"
            "Produce relations between these entities."
        )
        out = await self.llm.chat_json(
            [
                {"role": "system", "content": RELATION_SYSTEM},
                {"role": "user", "content": user},
            ],
            temperature=0.0,
        )
        return out.get("relations", [])


def graph_to_dict(g: KnowledgeGraph) -> dict[str, Any]:
    return json.loads(g.model_dump_json())


def graph_from_dict(d: dict[str, Any]) -> KnowledgeGraph:
    return KnowledgeGraph.model_validate(d)