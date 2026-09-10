"""The simulation loop.

Each round, every persona is asked to act: speak publicly, DM a peer,
react silently, or do nothing. Decisions are driven by the LLM with the
persona's current memory and a sample of the round's public transcript
as context. We then update each persona's memory + trust scores.

Why hand-rolled vs framework:
- We need fine-grained control over language register, audience targeting,
  sentiment drift, and god-events (operator perturbations). Off-the-shelf
  agent frameworks (autogen, langgraph) push you toward tool-calling and
  chat loops; we don't want that surface area here.
- We want the simulation to be reproducible from a single SimConfig +
  seed; no hidden framework state.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from collections import defaultdict
from typing import Any

from .config import get_settings
from .llm import LLMClient
from .schema import (
    AgentMemory,
    AgentMessage,
    Language,
    Persona,
    SimConfig,
    SimResult,
    SimRound,
)

log = logging.getLogger(__name__)


ACTION_SYSTEM = """You are driving a single fictional Indian persona inside a
multi-agent social simulation. You must decide what THIS persona does next,
given their background, current memory, and the messages they have just seen.

Actions you can take (output one per call):
- "speak"   — say something in public (everyone in the simulation sees it)
- "dm"      — message one specific other persona privately
- "react"   — update your internal stance, say nothing publicly
- "ignore"  — do nothing this round

Output JSON only. Format:
{
  "action": "speak" | "dm" | "react" | "ignore",
  "target_id": "<other persona id, or empty>",
  "content": "<your utterance, in your own language register; empty for react/ignore>",
  "language": "<language code>",
  "sentiment": <float in [-1, 1]>,
  "importance": <float in [0, 1]>,
  "stance_shift": <float in [-1, 1] vs your prior position>,
  "reasoning": "<1-sentence internal monologue>"
}

Rules:
- Write in the persona's natural register. A college student in Bandra
  does not write formal English. A small-business owner in Surat writes
  Hinglish or Gujarati with WhatsApp-style spelling. Stay in character.
- Be specific. Mention real entities from the world (brands, parties,
  policies) when relevant — vague platitudes make the simulation useless.
- Don't moralize at length. Most rounds you should speak 1-3 short messages,
  not essays.
- For "react" / "ignore", leave content empty and just report stance_shift.
"""


class SimulationLoop:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm
        self.s = get_settings()

    async def run(self, config: SimConfig, personas: list[Persona]) -> SimResult:
        assert self.s.max_agents_per_sim >= len(personas), (
            f"Population {len(personas)} exceeds MAX_AGENTS_PER_SIM "
            f"({self.s.max_agents_per_sim}). Raise the env var or shrink the sim."
        )

        result = SimResult(
            config=config,
            graph=None,  # type: ignore[arg-type]  # filled by caller
            personas=personas,
        )

        memories: dict[str, AgentMemory] = {
            p.id: AgentMemory(persona_id=p.id, round=0) for p in personas
        }
        public_feed: list[AgentMessage] = []

        for round_no in range(1, config.max_rounds + 1):
            log.info("Sim round %d/%d", round_no, config.max_rounds)

            god_event: str | None = None
            if round_no <= len(config.god_variables):
                god_event = config.god_variables[round_no - 1]

            round_obj = SimRound(round=round_no, god_event=god_event)

            # Each persona decides once per round, in parallel batches.
            sem = asyncio.Semaphore(self.s.parallel_agents)
            tasks = [
                self._step(
                    sem=sem,
                    persona=p,
                    memory=memories[p.id],
                    public_feed=public_feed,
                    round_no=round_no,
                    god_event=god_event,
                )
                for p in personas
            ]
            outputs = await asyncio.gather(*tasks, return_exceptions=True)

            # Roll memories forward and collect messages.
            for persona, out in zip(personas, outputs):
                if isinstance(out, Exception):
                    log.warning("Agent %s threw: %s", persona.id, out)
                    continue
                if out is None:
                    continue
                msg, memory = out
                memories[persona.id] = memory
                if msg is not None:
                    round_obj.messages.append(msg)
                    if msg.visibility == "public":
                        public_feed.append(msg)

            result.rounds.append(round_obj)

        result.finished_at = _now()
        return result

    async def _step(
        self,
        *,
        sem: asyncio.Semaphore,
        persona: Persona,
        memory: AgentMemory,
        public_feed: list[AgentMessage],
        round_no: int,
        god_event: str | None,
    ) -> tuple[AgentMessage | None, AgentMemory] | None:
        async with sem:
            # Build context window: most recent public messages + persona memory.
            recent = public_feed[-12:]  # cheap cap; full feed is in result.rounds
            peer_brief = "\n".join(
                f"[{m.sender_id}] ({m.language.value}): {m.content[:200]}"
                for m in recent
            )

            user = self._build_user_prompt(
                persona=persona,
                memory=memory,
                recent_feed=peer_brief,
                god_event=god_event,
                round_no=round_no,
            )

            raw = await self.llm.chat_json(
                [
                    {"role": "system", "content": ACTION_SYSTEM},
                    {"role": "user", "content": user},
                ],
                temperature=self.s.llm_temp_agent,
                max_tokens=600,
            )

            action = raw.get("action", "ignore")
            content = (raw.get("content") or "").strip()
            target = (raw.get("target_id") or "").strip()
            sentiment = float(raw.get("sentiment", 0.0))
            importance = float(raw.get("importance", 0.5))
            stance_shift = float(raw.get("stance_shift", 0.0))

            msg: AgentMessage | None = None
            if action == "speak" and content:
                msg = AgentMessage(
                    sender_id=persona.id,
                    content=content,
                    language=_lang(raw.get("language"), persona.language),
                    round=round_no,
                    visibility="public",
                    sentiment=sentiment,
                    importance=importance,
                )
            elif action == "dm" and content and target:
                msg = AgentMessage(
                    sender_id=persona.id,
                    content=content,
                    language=_lang(raw.get("language"), persona.language),
                    round=round_no,
                    visibility="dm",
                    audience=[target],
                    sentiment=sentiment,
                    importance=importance,
                )

            new_memory = self._update_memory(
                persona=persona,
                prev=memory,
                msg=msg,
                stance_shift=stance_shift,
                round_no=round_no,
            )
            return msg, new_memory

    def _build_user_prompt(
        self,
        *,
        persona: Persona,
        memory: AgentMemory,
        recent_feed: str,
        god_event: str | None,
        round_no: int,
    ) -> str:
        head = (
            f"Round {round_no}.\n\n"
            f"You are {persona.name}, a {persona.age}-year-old "
            f"{persona.occupation} ({persona.archetype.value}). "
            f"City tier {persona.city_tier}. Class {persona.socioeconomic_class}. "
            f"Language: {persona.language.value}. "
            f"Political lean: {persona.political_lean}. Religiosity: {persona.religiosity}.\n\n"
            f"Bio: {persona.bio}\n"
            f"Your initial take on this topic: {persona.initial_opinion}\n"
            f"Key concerns in your life right now: {', '.join(persona.key_concerns) or '—'}\n"
            f"Media you consume: {', '.join(persona.media_diet) or '—'}\n\n"
        )

        mem_block = (
            f"--- Your current memory ---\n"
            f"Last 5 things you remember verbatim:\n"
            + "\n".join(f"  - {m}" for m in memory.short_term[-5:])
            + f"\n\nRolling summary of earlier rounds:\n{memory.long_term_summary or '(none)'}\n"
            f"Net stance shift since start: {memory.stance_shift:+.2f}\n"
            f"Emotional state: {memory.emotional_state}\n"
        )

        feed_block = (
            f"--- Recent public messages in this simulation ---\n"
            f"{recent_feed or '(no public messages yet)'}\n"
        )

        god_block = ""
        if god_event:
            god_block = f"--- GOD EVENT (just dropped) ---\n{god_event}\n"

        tail = (
            "\nDecide your action now. Stay in character. Output JSON only."
        )
        return head + mem_block + feed_block + god_block + tail

    def _update_memory(
        self,
        *,
        persona: Persona,
        prev: AgentMemory,
        msg: AgentMessage | None,
        stance_shift: float,
        round_no: int,
    ) -> AgentMemory:
        short = list(prev["short_term"]) if isinstance(prev, dict) else list(prev.short_term)
        if msg is not None and msg.content:
            short.append(f"[r{round_no}] you said: {msg.content[:200]}")
            if len(short) > 5:
                short = short[-5:]

        new_stance = (prev.stance_shift if hasattr(prev, "stance_shift") else 0.0) + stance_shift
        new_stance = max(-1.0, min(1.0, new_stance))

        emotional = "neutral"
        if stance_shift > 0.4:
            emotional = "energized"
        elif stance_shift < -0.4:
            emotional = "disturbed"

        long_term = prev.long_term_summary if hasattr(prev, "long_term_summary") else ""
        if msg is not None and msg.content and round_no % 3 == 0:
            long_term = (
                f"{long_term}\n[r{round_no}] {persona.name} ({persona.archetype.value}) "
                f"said: {msg.content[:160]}"
            ).strip()

        trust = dict(prev.trust_scores if hasattr(prev, "trust_scores") else {})

        return AgentMemory(
            persona_id=persona.id,
            round=round_no,
            short_term=short,
            long_term_summary=long_term[-2000:],
            stance_shift=new_stance,
            trust_scores=trust,
            emotional_state=emotional,
        )


def _lang(code: Any, fallback: Language) -> Language:
    if not code:
        return fallback
    try:
        return Language(code)
    except ValueError:
        return fallback


def _now():
    from datetime import datetime
    return datetime.utcnow()