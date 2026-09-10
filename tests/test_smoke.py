"""Smoke tests — make sure the engine is wired correctly without burning
LLM budget. Run: `pytest -q`."""

from __future__ import annotations

import pytest

from synthetic_society.presets import PRESETS, build_config_for
from synthetic_society.schema import (
    AgentMessage,
    Entity,
    EntityType,
    EvidenceCitation,
    KnowledgeGraph,
    Language,
    Persona,
    PersonaArchetype,
    Platform,
    PlatformMix,
    Region,
    Relation,
    SimConfig,
    TimelineEvent,
)


def test_presets_present() -> None:
    assert {"consumer", "political", "campus", "startup"} <= set(PRESETS.keys())


def test_build_config_for_each_domain() -> None:
    for domain in PRESETS:
        cfg = build_config_for(domain)
        assert cfg.domain == domain
        assert cfg.population_size > 0
        assert cfg.max_rounds > 0
        # Presets should now default a platform mix per domain.
        assert cfg.platform_mix.weights, f"missing platform mix for {domain}"


def test_schema_round_trip() -> None:
    g = KnowledgeGraph(
        entities=[
            Entity(id="cred", type=EntityType.BRAND, name="CRED"),
            Entity(id="ranveer", type=EntityType.PERSON, name="Ranveer Singh"),
        ],
        relations=[
            Relation(src="ranveer", dst="cred", kind="endorsed_by", weight=0.9),
        ],
    )
    restored = KnowledgeGraph.model_validate_json(g.model_dump_json())
    assert restored.entities[0].name == "CRED"
    assert restored.entities[0].type == EntityType.BRAND
    assert restored.relations[0].kind == "endorsed_by"


def test_persona_construction() -> None:
    p = Persona(
        id="p0001",
        name="Asha",
        archetype=PersonaArchetype.HOMEMAKER,
        language=Language.HINGLISH,
        region=Region.MAHARASHTRA,
        city_tier=1,
        age=34,
        occupation="homemaker",
        bio="Cares about kids' school fees.",
        initial_opinion="₹10k/year is too much.",
        primary_platforms=[Platform.WHATSAPP, Platform.INSTAGRAM],
    )
    assert p.archetype == PersonaArchetype.HOMEMAKER
    assert p.region == Region.MAHARASHTRA
    assert Platform.WHATSAPP in p.primary_platforms


def test_removed_archetypes_gone() -> None:
    """Make sure dead archetypes are not in the enum anymore."""
    for dead in ("retired_govt_servant", "homemaker_rural", "homemaker_urban",
                 "senior_citizen"):
        assert dead not in {a.value for a in PersonaArchetype}


def test_new_archetypes_present() -> None:
    for new in ("nri_diaspora", "gig_worker", "migrant_labour",
                "govt_employee", "cricket_fan"):
        assert new in {a.value for a in PersonaArchetype}


def test_languages_expanded() -> None:
    codes = {l.value for l in Language}
    for new in ("or", "as", "ur", "mai"):
        assert new in codes, f"missing language code {new}"
    for removed in ("bhinglish", "tanglish"):
        assert removed not in codes, f"dead language still present: {removed}"


def test_agent_message_with_evidence() -> None:
    m = AgentMessage(
        sender_id="p0001",
        content="RBI just hiked rates",
        language=Language.ENGLISH,
        platform=Platform.TWITTER_X,
        round=1,
        evidence_citations=[
            EvidenceCitation(
                entity_id="rbi", entity_name="RBI", entity_type=EntityType.ORGANIZATION,
            )
        ],
    )
    assert m.platform == Platform.TWITTER_X
    assert m.evidence_citations[0].entity_name == "RBI"


def test_timeline_event_on_config() -> None:
    cfg = SimConfig(
        name="t", seed_topic="x", domain="consumer",
        timeline_events=[
            TimelineEvent(round=2, label="rbi_hike", content="Repo +25bps",
                          source="RBI circular", platform=Platform.TWITTER_X),
        ],
    )
    assert cfg.timeline_events[0].round == 2


def test_platform_mix_normalize() -> None:
    mix = PlatformMix(weights={Platform.TWITTER_X: 3, Platform.WHATSAPP: 1}).normalize()
    assert abs(sum(mix.weights.values()) - 1.0) < 1e-9
    assert mix.weights[Platform.TWITTER_X] == 0.75


@pytest.mark.asyncio
async def test_dry_run_does_not_call_llm() -> None:
    """Pure-Python helpers don't hit the network."""
    from synthetic_society.report import (
        _per_archetype_stats, _per_platform_stats, _stance_drift,
        _evidence_aggregation,
    )

    cfg = build_config_for("consumer", name="dry")
    personas = [
        Persona(
            id=f"p{i:04d}",
            name=f"p{i}",
            archetype=PersonaArchetype.METRO_PROFESSIONAL,
            language=Language.ENGLISH,
            region=Region.MAHARASHTRA,
            city_tier=1,
            age=30,
            occupation="dev",
            bio=".",
            initial_opinion=".",
            primary_platforms=[Platform.TWITTER_X],
        )
        for i in range(3)
    ]
    from synthetic_society.schema import SimResult

    result = SimResult(
        config=cfg,
        graph=KnowledgeGraph(),
        personas=personas,
    )
    assert _per_archetype_stats(result) == {}
    assert _per_platform_stats(result) == {}
    assert _stance_drift(result) == {}
    assert _evidence_aggregation(result) == []