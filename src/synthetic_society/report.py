"""Post-simulation analysis & synthesis.

The ReportAgent walks the entire transcript, then renders a markdown
report answering the operator's question.

v0.2 additions:
- Per-platform activity / sentiment breakdown (so you can see Twitter
  vs WhatsApp vs Reddit India divergence).
- Evidence aggregation: which real-world entities got cited most often,
  by which archetypes. Lets reports say "12 agents across 4 archetypes
  cited PM-KISAN; sentiment on those posts averaged -0.4".
- `watcher_archetypes` respected — ReportAgent drills into those first
  when the operator pinned them.
"""

from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict

from .config import get_settings
from .llm import LLMClient
from .schema import PersonaArchetype, Platform, SimResult

log = logging.getLogger(__name__)


def _persona_index(result: SimResult) -> dict[str, object]:
    return {p.id: p for p in result.personas}


def _per_archetype_stats(result: SimResult) -> dict[str, dict[str, float]]:
    idx = _persona_index(result)
    by_arch_msg: dict[str, int] = defaultdict(int)
    by_arch_sent: dict[str, list[float]] = defaultdict(list)

    for rnd in result.rounds:
        for m in rnd.messages:
            persona = idx.get(m.sender_id)
            if persona is None:
                continue
            arch = persona.archetype.value
            by_arch_msg[arch] += 1
            by_arch_sent[arch].append(m.sentiment)

    return {
        arch: {
            "avg_sentiment": round(sum(s) / len(s), 3) if s else 0.0,
            "message_count": float(by_arch_msg.get(arch, 0)),
        }
        for arch, s in by_arch_sent.items()
    }


def _per_platform_stats(result: SimResult) -> dict[str, dict[str, float]]:
    counts: dict[str, int] = defaultdict(int)
    sents: dict[str, list[float]] = defaultdict(list)
    for rnd in result.rounds:
        for m in rnd.messages:
            if m.visibility != "public":
                continue
            pl = m.platform.value
            counts[pl] += 1
            sents[pl].append(m.sentiment)
    return {
        pl: {
            "messages": float(c),
            "avg_sentiment": round(sum(s) / len(s), 3) if s else 0.0,
            "avg_virality": 0.0,  # placeholder; filled below
        }
        for pl, c in counts.items()
    }


def _per_platform_virality(result: SimResult) -> dict[str, float]:
    vir: dict[str, list[float]] = defaultdict(list)
    for rnd in result.rounds:
        for m in rnd.messages:
            if m.visibility == "public":
                vir[m.platform.value].append(m.virality_score)
    return {
        pl: round(sum(v) / len(v), 3) if v else 0.0
        for pl, v in vir.items()
    }


def _top_quotes(result: SimResult, n: int = 12) -> list[str]:
    msgs = [
        m
        for rnd in result.rounds
        for m in rnd.messages
        if m.visibility == "public" and m.importance >= 0.6
    ]
    msgs.sort(key=lambda m: (m.importance, m.virality_score), reverse=True)
    idx = _persona_index(result)
    lines: list[str] = []
    for m in msgs[:n]:
        persona = idx.get(m.sender_id)
        tag = (
            f"{persona.archetype.value}/{persona.region.value}/{m.platform.value}"
            if persona is not None
            else m.platform.value
        )
        lines.append(f"- [{tag}] {m.content[:240]}")
    return lines


def _stance_drift(result: SimResult) -> dict[str, float]:
    idx = _persona_index(result)
    early: dict[str, list[float]] = defaultdict(list)
    late: dict[str, list[float]] = defaultdict(list)
    n_rounds = max(1, len(result.rounds))
    cutoff = max(1, n_rounds // 3)

    for rnd in result.rounds:
        for m in rnd.messages:
            if m.visibility != "public":
                continue
            persona = idx.get(m.sender_id)
            if persona is None:
                continue
            arch = persona.archetype.value
            if rnd.round <= cutoff:
                early[arch].append(m.sentiment)
            elif rnd.round > n_rounds - cutoff:
                late[arch].append(m.sentiment)

    drift: dict[str, float] = {}
    for arch in set(list(early.keys()) + list(late.keys())):
        e = sum(early.get(arch, [0.0])) / max(1, len(early.get(arch, [1])))
        l = sum(late.get(arch, [0.0])) / max(1, len(late.get(arch, [1])))
        drift[arch] = round(l - e, 3)
    return drift


def _evidence_aggregation(result: SimResult) -> list[dict[str, object]]:
    """Which entities got cited, by which archetypes, with avg sentiment."""
    idx = _persona_index(result)
    by_entity: dict[str, dict[str, object]] = {}

    for rnd in result.rounds:
        for m in rnd.messages:
            persona = idx.get(m.sender_id)
            if persona is None:
                continue
            for cit in m.evidence_citations:
                eid = cit.entity_id or cit.entity_name
                slot = by_entity.setdefault(
                    eid,
                    {
                        "name": cit.entity_name,
                        "type": cit.entity_type.value
                        if hasattr(cit.entity_type, "value")
                        else str(cit.entity_type),
                        "cites": 0,
                        "archetypes": Counter(),
                        "sents": [],
                    },
                )
                slot["cites"] = int(slot["cites"]) + 1
                slot["archetypes"][persona.archetype.value] += 1
                slot["sents"].append(m.sentiment)

    rows: list[dict[str, object]] = []
    for eid, slot in by_entity.items():
        sents = slot["sents"]  # type: ignore[assignment]
        rows.append({
            "entity_id": eid,
            "name": slot["name"],
            "type": slot["type"],
            "cites": slot["cites"],
            "archetypes": dict(slot["archetypes"]),  # type: ignore[arg-type]
            "avg_sentiment": round(sum(sents) / len(sents), 3) if sents else 0.0,
        })
    rows.sort(key=lambda r: r["cites"], reverse=True)  # type: ignore[operator]
    return rows[:15]


REPORT_SYSTEM = """You are the ReportAgent for an Indian-market multi-agent simulation.

You are given:
  - The seed topic and the operator's prediction question.
  - Aggregate stats: per-archetype activity/sentiment + per-platform stats.
  - Per-archetype stance drift (early -> late rounds).
  - Evidence aggregation: which real-world entities were cited, and by whom.
  - The highest-importance quotes from the population, tagged with
    archetype / region / platform.
  - The full persona list with their initial opinions.

Required markdown sections (in this order):
  1. TL;DR (3-5 bullets)
  2. Population snapshot (what the sim built, region + archetype spread)
  3. Sentiment & activity heatmap (by archetype, then by platform)
  4. Notable voices (3-6 quotes with archetype + region + platform tags + why)
  5. Trajectory (how the discourse shifted; what triggered it)
  6. Evidence cited (real entities referenced by agents — brand/policy/scheme)
  7. Predicted outcome for the operator's question
  8. Confidence & failure modes
  9. Suggested god-events to test next (3 perturbation experiments)

Tone: blunt, specific, India-aware. No filler. Use tables where useful.
Do NOT start with "Based on the simulation..." — get to the point."""


class ReportAgent:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm
        self.s = get_settings()

    async def render(self, result: SimResult, question: str) -> str:
        arch_stats = _per_archetype_stats(result)
        platform_stats = _per_platform_stats(result)
        virality = _per_platform_virality(result)
        for pl, v in virality.items():
            if pl in platform_stats:
                platform_stats[pl]["avg_virality"] = v
        drift = _stance_drift(result)
        evidence = _evidence_aggregation(result)
        quotes = _top_quotes(result)

        watchers = result.config.watcher_archetypes
        watcher_note = ""
        if watchers:
            watcher_note = (
                "\nWATCHER ARCHETYPES (drill into these first): "
                + ", ".join(a.value for a in watchers)
            )

        sample_personas = "\n".join(
            f"- {p.name} ({p.archetype.value}, {p.region.value}, {p.language.value}): "
            f"{p.initial_opinion[:160]}"
            for p in result.personas[:25]
        )

        user = (
            f"Seed topic: {result.config.seed_topic}\n"
            f"Domain: {result.config.domain}\n"
            f"Rounds run: {len(result.rounds)}\n"
            f"Population: {len(result.personas)} personas\n"
            f"Total cost so far: ${result.total_cost_usd:.3f} "
            f"(budget {'EXCEEDED' if result.budget_exceeded else 'OK'})\n"
            f"{watcher_note}\n\n"
            f"Operator question:\n{question}\n\n"
            f"--- Aggregate stats by archetype ---\n{json.dumps(arch_stats, indent=2)}\n\n"
            f"--- Aggregate stats by platform ---\n{json.dumps(platform_stats, indent=2)}\n\n"
            f"--- Stance drift (early -> late, by archetype) ---\n{json.dumps(drift, indent=2)}\n\n"
            f"--- Evidence cited (top 15 entities) ---\n{json.dumps(evidence, indent=2)}\n\n"
            f"--- Top quotes ---\n" + "\n".join(quotes) + "\n\n"
            f"--- Sample personas ---\n{sample_personas}\n"
        )

        log.info("Rendering report (question length=%d)", len(question))
        text = await self.llm.chat(
            [
                {"role": "system", "content": REPORT_SYSTEM},
                {"role": "user", "content": user},
            ],
            temperature=self.s.llm_temp_report,
            max_tokens=3000,
        )
        return text.strip()