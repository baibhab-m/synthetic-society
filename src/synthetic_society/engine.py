"""The simulation loop.

Each round, every persona is asked to act on their assigned platform(s):
speak publicly, DM a peer, react silently, or do nothing. Decisions are
driven by the LLM with the persona's current memory and a sample of the
round's platform-scoped transcript as context.

v0.2 changes:
- Each agent now posts to ONE of their `primary_platforms`. The engine
  routes the message; visibility rules differ per platform (WhatsApp
  forwards are smaller audience, Twitter is public, Reddit is anonymous).
- Cost budget enforcement: each LLM call charges a model-priced estimate;
  once `config.cost_budget_usd` is hit, the sim halts early.
- god_variables (legacy free-text) is kept for back-compat, alongside the
  richer `timeline_events` list.
"""

from __future__ import annotations

import asyncio
import logging
import random
from collections import defaultdict
from datetime import datetime
from typing import Any

from .config import get_settings
from .llm import LLMClient
from .schema import (
    AgentMemory,
    AgentMessage,
    EvidenceCitation,
    Language,
    Persona,
    Platform,
    PlatformMix,
    SimConfig,
    SimResult,
    SimRound,
    TimelineEvent,
)

log = logging.getLogger(__name__)


# Per-platform reach (audience size) priors + virality multipliers.
PLATFORM_REACH: dict[Platform, int] = {
    Platform.TWITTER_X: 5_000,
    Platform.WHATSAPP: 250,
    Platform.INSTAGRAM: 2_000,
    Platform.FACEBOOK: 1_500,
    Platform.YOUTUBE: 8_000,
    Platform.REDDIT: 4_000,
    Platform.REDDIT_INDIA: 6_000,
    Platform.LINKEDIN: 3_000,
    Platform.LINKEDIN_NEWS: 3_500,
    Platform.TV_NEWS_DEBATE: 50_000,
    Platform.PRINT_OPED: 20_000,
    Platform.ANONYMOUS_CONFESSION: 1_000,
    Platform.QUORA: 3_000,
    Platform.KOO: 2_500,
    Platform.SHARE_CHAT: 800,
}

PLATFORM_VIRALITY: dict[Platform, float] = {
    Platform.TWITTER_X: 0.7,
    Platform.WHATSAPP: 0.9,  # forwards virally but small per-message
    Platform.INSTAGRAM: 0.5,
    Platform.FACEBOOK: 0.3,
    Platform.YOUTUBE: 0.4,
    Platform.REDDIT: 0.6,
    Platform.REDDIT_INDIA: 0.65,
    Platform.LINKEDIN: 0.3,
    Platform.LINKEDIN_NEWS: 0.3,
    Platform.TV_NEWS_DEBATE: 0.95,
    Platform.PRINT_OPED: 0.6,
    Platform.ANONYMOUS_CONFESSION: 0.7,
    Platform.QUORA: 0.4,
    Platform.KOO: 0.5,
    Platform.SHARE_CHAT: 0.6,
}


# Cheap cost-per-call heuristic. Real engines track tokens; we approximate.
# Tuned so that a 60-persona x 8-round sim ≈ $0.30 with gpt-4o-mini.
COST_PER_CALL_USD: dict[str, float] = {
    "extract": 0.005,   # graph extraction calls
    "persona": 0.008,   # persona batch generation
    "agent":   0.003,   # per-agent per-round action call
    "report":  0.05,   # report render
}


ACTION_SYSTEM = """You are driving a single fictional Indian persona inside a
multi-agent social simulation. You must decide what THIS persona does next,
given their background, current memory, and the messages they have just
seen on their platform(s).

Actions you can take (output one per call):
- "speak"   — post publicly on one of your primary platforms
- "dm"      — message one specific other persona privately
- "react"   — update your internal stance, say nothing publicly
- "ignore"  — do nothing this round

Output JSON only. Format:
{
  "action": "speak" | "dm" | "react" | "ignore",
  "platform": "<twitter_x|whatsapp|instagram|...>",
  "target_id": "<other persona id, or empty>",
  "content": "<your utterance, in your own language register; empty for react/ignore>",
  "language": "<language code>",
  "sentiment": <float in [-1..1]>,
  "importance": <float in [0..1]>,
  "stance_shift": <float in [-1..1] vs your prior position>,
  "cites": [{"entity_id": "...", "entity_name": "...", "entity_type": "..."}],
  "reasoning": "<1-sentence internal monologue>"
}

Rules:
- Write in the persona's natural register. A college student in Bandra
  does not write formal English. A small-business owner in Surat writes
  Hinglish or Gujarati with WhatsApp-style spelling. Stay in character.
- Adapt to your platform: WhatsApp forwards are short, English-mixed,
  with emojis and "pls share". Twitter is sharp, hashtags, threads. Reddit
  India is long-form, sarcastic. LinkedIn is professional. Stay in voice.
- Be specific. Mention real entities from the world (brands, parties,
  policies, schemes) when relevant — vague platitudes make the sim useless.
- When you reference a real entity (RBI circular, PM-KISAN, a brand,
  a politician), add it to `cites` so the report can aggregate evidence.
- Don't moralize at length. Most rounds you should speak 1-3 short messages.
- For "react" / "ignore", leave content empty and just report stance_shift.
"""


class SimulationLoop:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm
        self.s = get_settings()

    async def run(self, config: SimConfig, personas: list[Persona]) -> SimResult:
        if self.s.max_agents_per_sim < len(personas):
            raise ValueError(
                f"Population {len(personas)} exceeds MAX_AGENTS_PER_SIM "
                f"({self.s.max_agents_per_sim}). Raise the env var or shrink the sim."
            )

        result = SimResult(
            config=config,
            graph=None,  # type: ignore[arg-type]
            personas=personas,
        )

        platform_mix = self._resolve_platform_mix(config, personas)
        log.info("Platform mix: %s", platform_mix.weights)

        memories: dict[str, AgentMemory] = {
            p.id: AgentMemory(p.id, 0) for p in personas  # type: ignore[arg-call]
        }
        feeds_by_platform: dict[Platform, list[AgentMessage]] = defaultdict(list)
        cost_usd = 0.0
        budget_hit = False

        for round_no in range(1, config.max_rounds + 1):
            if budget_hit:
                log.warning("Budget exhausted at round %d; halting sim", round_no - 1)
                break
            log.info("Sim round %d/%d (cost so far: $%.3f)", round_no, config.max_rounds, cost_usd)

            # Legacy god-vars fire first; timeline events for this round layered on top.
            god_text: str | None = (
                config.god_variables[round_no - 1]
                if round_no <= len(config.god_variables)
                else None
            )
            timeline_this_round = [
                e for e in config.timeline_events if e.round == round_no
            ]

            round_obj = SimRound(
                round=round_no,
                god_event=god_text,
                timeline_events=timeline_this_round,
                cost_usd_so_far=cost_usd,
            )

            sem = asyncio.Semaphore(self.s.parallel_agents)
            tasks = [
                self._step(
                    sem=sem,
                    persona=p,
                    memory=memories[p.id],
                    feeds_by_platform=feeds_by_platform,
                    round_no=round_no,
                    god_event=god_text,
                    timeline_events=timeline_this_round,
                    platform_mix=platform_mix,
                )
                for p in personas
            ]
            outputs = await asyncio.gather(*tasks, return_exceptions=True)

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
                    feeds_by_platform[msg.platform].append(msg)

            cost_usd += len(personas) * COST_PER_CALL_USD["agent"]
            if cost_usd >= config.cost_budget_usd:
                budget_hit = True
            round_obj.cost_usd_so_far = cost_usd
            result.rounds.append(round_obj)

        result.total_cost_usd = round(cost_usd, 4)
        result.budget_exceeded = budget_hit
        result.finished_at = datetime.utcnow()
        return result

    async def _step(
        self,
        *,
        sem: asyncio.Semaphore,
        persona: Persona,
        memory: AgentMemory,
        feeds_by_platform: dict[Platform, list[AgentMessage]],
        round_no: int,
        god_event: str | None,
        timeline_events: list[TimelineEvent],
        platform_mix: PlatformMix,
    ) -> tuple[AgentMessage | None, AgentMemory] | None:
        async with sem:
            chosen_platform = _pick_platform(persona, platform_mix)
            recent = feeds_by_platform[chosen_platform][-12:]
            peer_brief = "\n".join(
                f"[{m.sender_id}] ({m.language.value}, {m.platform.value}): {m.content[:200]}"
                for m in recent
            )

            user = self._build_user_prompt(
                persona=persona,
                memory=memory,
                recent_feed=peer_brief,
                god_event=god_event,
                timeline_events=timeline_events,
                round_no=round_no,
                platform=chosen_platform,
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

            platform_str = raw.get("platform")
            try:
                platform = Platform(platform_str) if platform_str else chosen_platform
            except ValueError:
                platform = chosen_platform

            citations: list[EvidenceCitation] = []
            for c in raw.get("cites", []) or []:
                try:
                    citations.append(
                        EvidenceCitation(
                            entity_id=c.get("entity_id", ""),
                            entity_name=c.get("entity_name", ""),
                            entity_type=c.get("entity_type", "trend"),
                            quote=c.get("quote", ""),
                        )
                    )
                except Exception:  # noqa: BLE001
                    pass

            msg: AgentMessage | None = None
            if action == "speak" and content:
                msg = AgentMessage(
                    sender_id=persona.id,
                    content=content,
                    language=_lang(raw.get("language"), persona.language),
                    platform=platform,
                    round=round_no,
                    visibility="public",
                    sentiment=sentiment,
                    importance=importance,
                    reach=PLATFORM_REACH.get(platform, 500),
                    virality_score=PLATFORM_VIRALITY.get(platform, 0.5) * importance,
                    evidence_citations=citations,
                )
            elif action == "dm" and content and target:
                msg = AgentMessage(
                    sender_id=persona.id,
                    content=content,
                    language=_lang(raw.get("language"), persona.language),
                    platform=platform,
                    round=round_no,
                    visibility="dm",
                    audience=[target],
                    sentiment=sentiment,
                    importance=importance,
                    reach=1,
                    virality_score=0.0,
                    evidence_citations=citations,
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
        timeline_events: list[TimelineEvent],
        round_no: int,
        platform: Platform,
    ) -> str:
        head = (
            f"Round {round_no}.\n\n"
            f"You are {persona.name}, a {persona.age}-year-old "
            f"{persona.occupation} ({persona.archetype.value}). "
            f"Based in {persona.region.value}, city tier {persona.city_tier}. "
            f"Class {persona.socioeconomic_class}. "
            f"Language: {persona.language.value}. "
            f"Political lean: {persona.political_lean}. Religiosity: {persona.religiosity}.\n\n"
            f"Bio: {persona.bio}\n"
            f"Your initial take on this topic: {persona.initial_opinion}\n"
            f"Key concerns in your life right now: {', '.join(persona.key_concerns) or '—'}\n"
            f"Media you consume: {', '.join(persona.media_diet) or '—'}\n"
            f"Your primary platforms: {', '.join(p.value for p in persona.primary_platforms)}\n\n"
            f"You are currently posting on: {platform.value}\n"
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
            f"--- Recent public messages on {platform.value} ---\n"
            f"{recent_feed or '(no public messages yet on this platform)'}\n"
        )

        drops: list[str] = []
        if god_event:
            drops.append(f"GOD EVENT: {god_event}")
        for ev in timeline_events:
            tag = f"[{ev.platform.value}] {ev.label}" if ev.label else ev.content
            drops.append(f"{tag}: {ev.content} (source: {ev.source or 'unknown'})")
        drops_block = (
            ("\n--- Operator drops this round ---\n" + "\n".join(drops))
            if drops
            else ""
        )

        tail = "\nDecide your action now. Stay in character. Output JSON only."
        return head + mem_block + feed_block + drops_block + tail

    def _update_memory(
        self,
        *,
        persona: Persona,
        prev: AgentMemory,
        msg: AgentMessage | None,
        stance_shift: float,
        round_no: int,
    ) -> AgentMemory:
        short = list(prev.short_term)
        if msg is not None and msg.content:
            short.append(f"[r{round_no} {msg.platform.value}] you said: {msg.content[:200]}")
            if len(short) > 5:
                short = short[-5:]

        new_stance = max(-1.0, min(1.0, prev.stance_shift + stance_shift))
        emotional = "neutral"
        if stance_shift > 0.4:
            emotional = "energized"
        elif stance_shift < -0.4:
            emotional = "disturbed"

        long_term = prev.long_term_summary
        if msg is not None and msg.content and round_no % 3 == 0:
            long_term = (
                f"{long_term}\n[r{round_no}] {persona.name} ({persona.archetype.value}) "
                f"said: {msg.content[:160]}"
            ).strip()

        return AgentMemory(
            persona_id=persona.id,
            round=round_no,
            short_term=short,
            long_term_summary=long_term[-2000:],
            stance_shift=new_stance,
            emotional_state=emotional,
        )

    def _resolve_platform_mix(
        self, config: SimConfig, personas: list[Persona]
    ) -> PlatformMix:
        mix = config.platform_mix
        if mix.weights:
            return mix.normalize()
        # Fallback: count where personas actually post.
        counts: dict[Platform, int] = defaultdict(int)
        for p in personas:
            for pl in p.primary_platforms:
                counts[pl] += 1
        if not counts:
            counts = {Platform.TWITTER_X: 1, Platform.WHATSAPP: 1}
        return PlatformMix(weights=dict(counts)).normalize()


def _pick_platform(persona: Persona, mix: PlatformMix) -> Platform:
    """Pick a platform for this persona, biased by persona priors AND the
    sim-level mix (so political sims can run mostly on Twitter)."""
    priors = persona.primary_platforms or [Platform.TWITTER_X]
    weights = [mix.weights.get(p, 0.5) for p in priors]
    if not any(weights):
        return random.Random().choice(priors)
    return random.Random().choices(priors, weights=weights, k=1)[0]


def _lang(code: Any, fallback: Language) -> Language:
    if not code:
        return fallback
    try:
        return Language(code)
    except ValueError:
        return fallback