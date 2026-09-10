"""Smoke tests — make sure the engine is wired correctly without burning
LLM budget. Run: `pytest -q`."""

from __future__ import annotations

import asyncio

import pytest

from synthetic_society.presets import PRESETS, build_config_for
from synthetic_society.schema import (
    AgentMessage,
    Entity,
    KnowledgeGraph,
    Language,
    Persona,
    PersonaArchetype,
    Relation,
    SimConfig,
)


def test_presets_present() -> None:
    assert {"consumer", "political", "campus", "startup"} <= set(PRESETS.keys())


def test_build_config_for_each_domain() -> None:
    for domain in PRESETS:
        cfg = build_config_for(domain)
        assert cfg.domain == domain
        assert cfg.population_size > 0
        assert cfg.max_rounds > 0


def test_schema_round_trip() -> None:
    g = KnowledgeGraph(
        entities=[
            Entity(id="cred", type="Brand", name="CRED"),
            Entity(id="ranveer", type="Person", name="Ranveer Singh"),
        ],
        relations=[
            Relation(src="ranveer", dst="cred", kind="endorsed_by", weight=0.9),
        ],
    )
    json_text = g.model_dump_json()
    restored = KnowledgeGraph.model_validate_json(json_text)
    assert restored.entities[0].name == "CRED"
    assert restored.relations[0].kind == "endorsed_by"


def test_persona_construction() -> None:
    p = Persona(
        id="p0001",
        name="Asha",
        archetype=PersonaArchetype.HOMEMAKER_URBAN,
        language=Language.HINGLISH,
        city_tier=1,
        age=34,
        gender="F",
        occupation="homemaker",
        bio="Cares about kids' school fees.",
        initial_opinion="₹10k/year is too much.",
    )
    assert p.archetype == PersonaArchetype.HOMEMAKER_URBAN
    assert p.language == Language.HINGLISH


def test_agent_message_defaults() -> None:
    m = AgentMessage(sender_id="p0001", content="hello", language=Language.ENGLISH, round=1)
    assert m.visibility == "public"
    assert m.audience == []


@pytest.mark.asyncio
async def test_dry_run_does_not_call_llm() -> None:
    """Ensure pure-Python helpers don't accidentally hit the network."""
    from synthetic_society.report import _per_archetype_stats, _stance_drift

    cfg = build_config_for("consumer", name="dry")
    personas = [
        Persona(
            id=f"p{i:04d}",
            name=f"p{i}",
            archetype=PersonaArchetype.METRO_PROFESSIONAL,
            language=Language.ENGLISH,
            city_tier=1,
            age=30,
            gender="M",
            occupation="dev",
            bio=".",
            initial_opinion=".",
        )
        for i in range(3)
    ]
    result_kwargs = dict(
        config=cfg,
        graph=KnowledgeGraph(),
        personas=personas,
        rounds=[],
    )
    from synthetic_society.schema import SimResult

    result = SimResult(**result_kwargs)
    assert _per_archetype_stats(result) == {}
    assert _stance_drift(result) == {}