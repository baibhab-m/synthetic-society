"""Post-simulation analysis & synthesis.

The ReportAgent walks the entire transcript, then either:
  a) writes a free-form markdown report answering the operator's question, or
  b) (optionally) dumps a structured JSON summary for downstream tools.

It uses cheap summary heuristics (per-archetype stance, message-count,
sentiment drift) as anchors, then asks the LLM to interpret.
"""

from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict

from .config import get_settings
from .llm import LLMClient
from .schema import SimResult

log = logging.getLogger(__name__)


def _per_archetype_stats(result: SimResult) -> dict[str, dict[str, float]]:
    by_arch: dict[str, list[float]] = defaultdict(list)
    sentiment_by_arch: dict[str, list[float]] = defaultdict(list)
    activity_by_arch: dict[str, int] = defaultdict(int)

    for rnd in result.rounds:
        for m in rnd.messages:
            # We don't store persona->archetype on the message; resolve by
            # walking the persona table.
            for persona in result.personas:
                if persona.id == m.sender_id:
                    activity_by_arch[persona.archetype.value] += 1
                    sentiment_by_arch[persona.archetype.value].append(m.sentiment)
                    break

    stats: dict[str, dict[str, float]] = {}
    for arch, sents in sentiment_by_arch.items():
        stats[arch] = {
            "avg_sentiment": round(sum(sents) / len(sents), 3) if sents else 0.0,
            "message_count": float(activity_by_arch.get(arch, 0)),
        }
    return stats


def _top_quotes(result: SimResult, n: int = 12) -> list[str]:
    """Pick highest-importance public messages across the run."""

    msgs = [
        m
        for rnd in result.rounds
        for m in rnd.messages
        if m.visibility == "public" and m.importance >= 0.6
    ]
    msgs.sort(key=lambda m: m.importance, reverse=True)
    return [f"- {m.content[:240]}" for m in msgs[:n]]


def _stance_drift(result: SimResult) -> dict[str, float]:
    """Net per-archetype sentiment drift, very rough proxy."""

    early: dict[str, list[float]] = defaultdict(list)
    late: dict[str, list[float]] = defaultdict(list)
    n_rounds = max(1, len(result.rounds))
    cutoff = max(1, n_rounds // 3)

    for rnd in result.rounds:
        for m in rnd.messages:
            if m.visibility != "public":
                continue
            for persona in result.personas:
                if persona.id == m.sender_id:
                    arch = persona.archetype.value
                    if rnd.round <= cutoff:
                        early[arch].append(m.sentiment)
                    elif rnd.round > n_rounds - cutoff:
                        late[arch].append(m.sentiment)
                    break

    drift: dict[str, float] = {}
    for arch in set(list(early.keys()) + list(late.keys())):
        e = sum(early.get(arch, [0.0])) / max(1, len(early.get(arch, [1])))
        l = sum(late.get(arch, [0.0])) / max(1, len(late.get(arch, [1])))
        drift[arch] = round(l - e, 3)
    return drift


REPORT_SYSTEM = """You are the ReportAgent for an Indian-market multi-agent simulation.

You are given:
  - The seed topic and what they wanted predicted.
  - Aggregate stats over the run (per-archetype activity, sentiment, drift).
  - A curated set of the highest-importance quotes from the population.
  - The full persona list with their initial opinions.

Your output is a markdown report. Required sections (in this order):
  1. TL;DR (3-5 bullets)
  2. Population snapshot (what the sim built)
  3. Sentiment & activity heatmap (by archetype)
  4. Notable voices (3-6 quotes with archetype tags + why they matter)
  5. Trajectory (how the discourse shifted; what triggered it)
  6. Predicted outcome for the operator's question
  7. Confidence & failure modes (what could be wrong with this prediction)
  8. Suggested god-events to test next (3 perturbation experiments)

Tone: blunt, specific, India-aware. No filler. Use tables where useful.
Do NOT start with "Based on the simulation..." — get to the point."""


class ReportAgent:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm
        self.s = get_settings()

    async def render(self, result: SimResult, question: str) -> str:
        stats = _per_archetype_stats(result)
        drift = _stance_drift(result)
        quotes = _top_quotes(result)

        sample_personas = "\n".join(
            f"- {p.name} ({p.archetype.value}, {p.language.value}): {p.initial_opinion[:160]}"
            for p in result.personas[:25]
        )

        user = (
            f"Seed topic: {result.config.seed_topic}\n"
            f"Domain: {result.config.domain}\n"
            f"Rounds run: {len(result.rounds)}\n"
            f"Population: {len(result.personas)} personas\n\n"
            f"Operator question:\n{question}\n\n"
            f"--- Aggregate stats ---\n{json.dumps(stats, indent=2)}\n\n"
            f"--- Stance drift (early -> late) ---\n{json.dumps(drift, indent=2)}\n\n"
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
            max_tokens=2500,
        )
        return text.strip()