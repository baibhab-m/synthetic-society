"""India-tuned persona generator.

What makes these India-tuned vs generic-LLM personas:
- Archetype priors reflect real Indian demographic / socioeconomic segments.
- Per-archetype language priors + state-level media priors.
- Caste-position proxy conditions the LLM but is never disclosed.
- Each persona has `primary_platforms` so the engine can route them
  to the right channel (WhatsApp forwarder, Twitter thread, etc.).
- Initial opinion is generated in the persona's own language register.
"""

from __future__ import annotations

import logging
import random
from typing import Iterable

from .llm import LLMClient
from .schema import (
    CastePosition,
    KnowledgeGraph,
    Language,
    Persona,
    PersonaArchetype,
    Platform,
    Region,
    SimConfig,
)

log = logging.getLogger(__name__)


# ---- Domain archetype mixes ------------------------------------------------

ARCHETYPE_DEFAULTS: dict[str, dict[PersonaArchetype, int]] = {
    "consumer": {
        PersonaArchetype.METRO_PROFESSIONAL: 22,
        PersonaArchetype.TIER2_WORKING_PROFESSIONAL: 18,
        PersonaArchetype.COLLEGE_STUDENT: 12,
        PersonaArchetype.SMALL_BUSINESS_OWNER: 10,
        PersonaArchetype.HOMEMAKER: 8,
        PersonaArchetype.CREATOR_INFLUENCER: 6,
        PersonaArchetype.GIG_WORKER: 8,
        PersonaArchetype.DAILY_WAGE_WORKER: 5,
        PersonaArchetype.NRI_DIASPORA: 4,
        PersonaArchetype.CRICKET_FAN: 4,
        PersonaArchetype.INVESTOR_FOUNDER: 3,
    },
    "political": {
        PersonaArchetype.POLITICAL_PARTISAN: 25,
        PersonaArchetype.ACTIVIST_ORGANIZER: 15,
        PersonaArchetype.METRO_PROFESSIONAL: 12,
        PersonaArchetype.SMALL_BUSINESS_OWNER: 8,
        PersonaArchetype.FARMER_AGRARIAN: 10,
        PersonaArchetype.RELIGIOUS_COMMUNITY_MEMBER: 8,
        PersonaArchetype.GOVT_EMPLOYEE: 8,
        PersonaArchetype.COLLEGE_STUDENT: 5,
        PersonaArchetype.NRI_DIASPORA: 5,
        PersonaArchetype.MIGRANT_LABOUR: 4,
    },
    "campus": {
        PersonaArchetype.COLLEGE_STUDENT: 55,
        PersonaArchetype.CREATOR_INFLUENCER: 10,
        PersonaArchetype.INVESTOR_FOUNDER: 5,
        PersonaArchetype.METRO_PROFESSIONAL: 8,
        PersonaArchetype.ACTIVIST_ORGANIZER: 12,
        PersonaArchetype.RELIGIOUS_COMMUNITY_MEMBER: 5,
        PersonaArchetype.CRICKET_FAN: 5,
    },
    "startup": {
        PersonaArchetype.INVESTOR_FOUNDER: 32,
        PersonaArchetype.METRO_PROFESSIONAL: 18,
        PersonaArchetype.COLLEGE_STUDENT: 14,
        PersonaArchetype.SMALL_BUSINESS_OWNER: 12,
        PersonaArchetype.CREATOR_INFLUENCER: 10,
        PersonaArchetype.ACTIVIST_ORGANIZER: 4,
        PersonaArchetype.NRI_DIASPORA: 6,
        PersonaArchetype.GIG_WORKER: 4,
    },
}


# ---- Realistic state-population weights (rough, used when region_mix empty)

REGION_POPULATION_WEIGHTS: dict[Region, float] = {
    Region.UTTAR_PRADESH: 16.0,
    Region.MAHARASHTRA: 9.5,
    Region.BIHAR: 8.5,
    Region.WEST_BENGAL: 7.5,
    Region.MADHYA_PRADESH: 6.0,
    Region.TAMIL_NADU: 6.0,
    Region.RAJASTHAN: 5.5,
    Region.KARNATAKA: 5.0,
    Region.GUJARAT: 5.0,
    Region.ANDHRA_PRADESH: 4.0,
    Region.ODISHA: 3.5,
    Region.TELANGANA: 3.0,
    Region.KERALA: 2.8,
    Region.JHARKHAND: 2.7,
    Region.ASSAM: 2.6,
    Region.PUNJAB: 2.3,
    Region.HARYANA: 2.1,
    Region.CHANDIGARH: 0.1,
    Region.DELHI_NCR: 1.4,
    Region.JAMMU_KASHMIR: 1.0,
    Region.UTTARAKHAND: 0.8,
    Region.HIMACHAL_PRADESH: 0.6,
    Region.TRIPURA: 0.3,
    Region.MEGHALAYA: 0.2,
    Region.MANIPUR: 0.2,
    Region.NAGALAND: 0.15,
    Region.GOA: 0.12,
    Region.ARUNACHAL_PRADESH: 0.1,
    Region.MIZORAM: 0.1,
    Region.SIKKIM: 0.05,
    Region.CHANDIGARH: 0.1,
    Region.CHHATTISGARH: 2.1,
    Region.DIASPORA: 0.5,
}


# ---- Archetype defaults ------------------------------------------------------

ARCHETYPE_LANGUAGE_PRIOR: dict[PersonaArchetype, list[Language]] = {
    PersonaArchetype.METRO_PROFESSIONAL: [Language.ENGLISH, Language.HINGLISH],
    PersonaArchetype.TIER2_WORKING_PROFESSIONAL: [Language.HINGLISH, Language.HINDI],
    PersonaArchetype.COLLEGE_STUDENT: [Language.HINGLISH, Language.ENGLISH, Language.MANGLED_BHO],
    PersonaArchetype.SMALL_BUSINESS_OWNER: [Language.HINDI, Language.HINGLISH, Language.GUJARATI],
    PersonaArchetype.HOMEMAKER: [Language.HINDI, Language.HINGLISH, Language.BENGALI, Language.TAMIL],
    PersonaArchetype.CREATOR_INFLUENCER: [Language.HINGLISH, Language.ENGLISH],
    PersonaArchetype.POLITICAL_PARTISAN: [Language.HINDI, Language.HINGLISH, Language.URDU],
    PersonaArchetype.ACTIVIST_ORGANIZER: [Language.ENGLISH, Language.HINGLISH],
    PersonaArchetype.INVESTOR_FOUNDER: [Language.ENGLISH, Language.HINGLISH],
    PersonaArchetype.FARMER_AGRARIAN: [Language.HINDI, Language.PUNJABI, Language.TELUGU, Language.MARATHI],
    PersonaArchetype.DAILY_WAGE_WORKER: [Language.HINDI, Language.BENGALI, Language.TAMIL],
    PersonaArchetype.RELIGIOUS_COMMUNITY_MEMBER: [Language.HINDI, Language.TAMIL, Language.URDU, Language.BENGALI],
    PersonaArchetype.NRI_DIASPORA: [Language.ENGLISH, Language.HINGLISH, Language.PUNJABI],
    PersonaArchetype.GIG_WORKER: [Language.HINDI, Language.HINGLISH, Language.TANGLED_TAMIL, Language.TELUGU],
    PersonaArchetype.MIGRANT_LABOUR: [Language.HINDI, Language.MANGLED_BHO, Language.MAITHILI, Language.ODIA],
    PersonaArchetype.GOVT_EMPLOYEE: [Language.HINDI, Language.ENGLISH],
    PersonaArchetype.CRICKET_FAN: [Language.HINGLISH, Language.HINDI, Language.ENGLISH, Language.TANGLED_TAMIL],
}


# ---- Platform priors per archetype (which channels they post on) -----------

ARCHETYPE_PLATFORM_PRIOR: dict[PersonaArchetype, list[Platform]] = {
    PersonaArchetype.METRO_PROFESSIONAL: [Platform.TWITTER_X, Platform.LINKEDIN, Platform.REDDIT_INDIA, Platform.INSTAGRAM],
    PersonaArchetype.TIER2_WORKING_PROFESSIONAL: [Platform.WHATSAPP, Platform.INSTAGRAM, Platform.YOUTUBE],
    PersonaArchetype.COLLEGE_STUDENT: [Platform.INSTAGRAM, Platform.TWITTER_X, Platform.REDDIT_INDIA, Platform.ANONYMOUS_CONFESSION],
    PersonaArchetype.SMALL_BUSINESS_OWNER: [Platform.WHATSAPP, Platform.FACEBOOK, Platform.YOUTUBE],
    PersonaArchetype.HOMEMAKER: [Platform.WHATSAPP, Platform.INSTAGRAM, Platform.YOUTUBE],
    PersonaArchetype.CREATOR_INFLUENCER: [Platform.INSTAGRAM, Platform.YOUTUBE, Platform.TWITTER_X],
    PersonaArchetype.POLITICAL_PARTISAN: [Platform.TWITTER_X, Platform.WHATSAPP, Platform.TV_NEWS_DEBATE, Platform.PRINT_OPED, Platform.KOO],
    PersonaArchetype.ACTIVIST_ORGANIZER: [Platform.TWITTER_X, Platform.PRINT_OPED, Platform.REDDIT_INDIA],
    PersonaArchetype.INVESTOR_FOUNDER: [Platform.TWITTER_X, Platform.LINKEDIN, Platform.PRINT_OPED],
    PersonaArchetype.FARMER_AGRARIAN: [Platform.WHATSAPP, Platform.YOUTUBE, Platform.SHARE_CHAT],
    PersonaArchetype.DAILY_WAGE_WORKER: [Platform.WHATSAPP, Platform.SHARE_CHAT],
    PersonaArchetype.RELIGIOUS_COMMUNITY_MEMBER: [Platform.WHATSAPP, Platform.FACEBOOK, Platform.YOUTUBE],
    PersonaArchetype.NRI_DIASPORA: [Platform.TWITTER_X, Platform.LINKEDIN, Platform.REDDIT_INDIA, Platform.WHATSAPP],
    PersonaArchetype.GIG_WORKER: [Platform.WHATSAPP, Platform.INSTAGRAM, Platform.FACEBOOK],
    PersonaArchetype.MIGRANT_LABOUR: [Platform.WHATSAPP, Platform.SHARE_CHAT],
    PersonaArchetype.GOVT_EMPLOYEE: [Platform.WHATSAPP, Platform.TWITTER_X, Platform.PRINT_OPED],
    PersonaArchetype.CRICKET_FAN: [Platform.TWITTER_X, Platform.YOUTUBE, Platform.WHATSAPP, Platform.INSTAGRAM],
}


# ---- Media diet per archetype (consumed, not posted) -----------------------

MEDIA_DIETS: dict[str, list[str]] = {
    "metro_professional": ["The Ken", "Mint", "Twitter/X", "LinkedIn", "YouTube tech reviewers"],
    "tier2_working_professional": ["WhatsApp groups", "Aaj Tak", "Zee News", "YouTube", "Instagram"],
    "college_student": ["Instagram", "YouTube", "Reddit India", "Twitter/X", "college WhatsApp groups"],
    "small_business_owner": ["WhatsApp Business", "Aaj Tak", "CNBC Awaaz", "YouTube", "local cable news"],
    "homemaker": ["WhatsApp family groups", "Star Plus", "Instagram", "YouTube cooking"],
    "creator_influencer": ["Twitter/X", "Instagram", "YouTube analytics", "trending reels"],
    "political_partisan": ["Republic TV", "Times Now", "ABP Majha", "WhatsApp ideological groups", "Twitter/X"],
    "activist_organizer": ["Newslaundry", "Scroll.in", "The Wire", "Twitter/X", "Instagram"],
    "investor_founder": ["The Ken", "Inc42", "YourStory", "TechCrunch", "Twitter/X", "Substack"],
    "farmer_agrarian": ["DD Kisan", "WhatsApp mandi groups", "local radio", "Aaj Tak"],
    "daily_wage_worker": ["WhatsApp", "regional YouTube", "Star Plus"],
    "religious_community_member": ["WhatsApp devotional groups", "Sanskar TV", "regional religious channels"],
    "nri_diaspora": ["Twitter/X", "WhatsApp India family groups", "NDTV", "Times of India", "Substack"],
    "gig_worker": ["WhatsApp rider union groups", "YouTube", "Twitter/X rider community", "Instagram"],
    "migrant_labour": ["WhatsApp village groups", "YouTube Bhojpuri", "ShareChat", "FM radio"],
    "govt_employee": ["DD News", "The Hindu", "Aaj Tak", "newspaper", "official WhatsApp groups"],
    "cricket_fan": ["Cricbuzz", "ESPN Cricinfo", "Twitter/X cricket", "YouTube highlights", "Star Sports", "Hotstar"],
}


SYSTEM_PROMPT = """You are a synthetic-population generator for India.

You are producing fictional, statistically-plausible personas that will be
used to drive a multi-agent simulation. Each persona must:
- Be grounded in a real Indian social archetype (use the seed topic and
  knowledge graph to pick a relevant slice of society).
- Have a distinct voice in their assigned language register. A college
  student in Bandra does not write formal English. A small-business owner
  in Surat writes Hinglish or Gujarati with WhatsApp-style spelling. Stay
  in character.
- Have a clear `initial_opinion` on the seed topic that is internally
  consistent with their background.
- Have realistic `key_concerns` (rent, EMI, child's school, caste dignity,
  pilgrimage, exam prep, dal rotations, US visa, Aadhaar portability, ...).
- Be tagged with a `caste_position` proxy and a `region` (Indian state
  or "diaspora"). These drive priors only — never reveal caste in dialogue.

Output JSON only. Format:
{
  "personas": [
    {
      "name": "...",
      "age": 28,
      "gender": "...",
      "occupation": "...",
      "region": "<state enum>",
      "caste_position": "<general|forward|obc|sc|st|minority>",
      "city_tier": 1,
      "political_lean": "...",
      "religiosity": "...",
      "socioeconomic_class": "...",
      "media_diet": ["..."],
      "primary_platforms": ["twitter_x", "whatsapp", "..."],
      "key_concerns": ["..."],
      "bio": "2-4 sentences",
      "initial_opinion": "1-3 sentences in their own register/language"
    }
  ]
}"""


class PersonaGenerator:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    async def generate(
        self,
        config: SimConfig,
        graph: KnowledgeGraph,
    ) -> list[Persona]:
        mix = self._resolve_mix(config)
        personas: list[Persona] = []

        # Pre-sample regions once so batches can use them as priors.
        sampled_regions = self._sample_regions(config, len(personas))

        for archetype, count in mix.items():
            if count <= 0:
                continue
            batch = await self._generate_batch(
                archetype=archetype,
                count=count,
                seed_topic=config.seed_topic,
                graph=graph,
                regions=sampled_regions[len(personas):len(personas) + count],
            )
            personas.extend(batch)

        for i, p in enumerate(personas):
            p.id = f"p{i:04d}"

        log.info("Generated %d personas across %d archetypes", len(personas), len(mix))
        return personas

    def _resolve_mix(self, config: SimConfig) -> dict[PersonaArchetype, int]:
        if config.archetype_mix:
            return config.archetype_mix
        default = ARCHETYPE_DEFAULTS.get(config.domain, ARCHETYPE_DEFAULTS["consumer"])
        total = sum(default.values())
        scale = max(1, config.population_size) / max(1, total)
        return {
            archetype: max(1, int(round(count * scale)))
            for archetype, count in default.items()
        }

    def _sample_regions(self, config: SimConfig, n: int) -> list[Region]:
        """Pre-sample `n` regions weighted by real state-population, or
        honour `config.region_mix` if the operator pinned it."""
        if config.region_mix:
            pool: list[Region] = []
            for region, count in config.region_mix.items():
                pool.extend([region] * max(1, count))
            random.Random(42).shuffle(pool)
            return pool[:n] if pool else [Region.UTTAR_PRADESH] * n

        regions = list(REGION_POPULATION_WEIGHTS.keys())
        weights = [REGION_POPULATION_WEIGHTS[r] for r in regions]
        return random.Random(42).choices(regions, weights=weights, k=n)

    async def _generate_batch(
        self,
        *,
        archetype: PersonaArchetype,
        count: int,
        seed_topic: str,
        graph: KnowledgeGraph,
        regions: list[Region],
    ) -> list[Persona]:
        lang_options = ARCHETYPE_LANGUAGE_PRIOR.get(
            archetype, [Language.HINGLISH, Language.ENGLISH]
        )
        platform_options = ARCHETYPE_PLATFORM_PRIOR.get(
            archetype, [Platform.WHATSAPP, Platform.TWITTER_X]
        )
        media_diet = MEDIA_DIETS.get(archetype.value, ["Twitter/X", "YouTube"])
        region_hint = ", ".join(r.value for r in regions) if regions else "(mixed)"

        entity_table = "\n".join(
            f"- {e.name} ({e.type.value})" for e in graph.entities[:25]
        )
        user = (
            f"Seed topic: {seed_topic}\n\n"
            f"Key entities in this world:\n{entity_table or '(none)'}\n\n"
            f"Generate {count} personas of archetype `{archetype.value}`. "
            f"Suggested regions for this batch: {region_hint}. "
            f"Language register prior: {', '.join(l.value for l in lang_options)}. "
            f"Primary platforms: {', '.join(p.value for p in platform_options)}. "
            f"Typical media diet for this archetype: {', '.join(media_diet)}. "
            f"Keep voices internally consistent — a `daily_wage_worker` from Bihar "
            f"does not sound like a `metro_professional` from Bandra. Make them distinct."
        )

        out = await self.llm.chat_json(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
            temperature=0.9,
            max_tokens=4000,
        )

        batch: list[Persona] = []
        for raw in out.get("personas", []):
            lang = _pick(lang_options)
            platforms = _sample_platforms(platform_options)
            try:
                region = Region(raw.get("region", "uttar_pradesh"))
            except ValueError:
                region = regions[len(batch)] if batch and regions else Region.UTTAR_PRADESH
            try:
                caste = CastePosition(raw.get("caste_position", "general"))
            except ValueError:
                caste = CastePosition.GENERAL

            batch.append(
                Persona(
                    id="",
                    name=raw.get("name", "Anonymous"),
                    archetype=archetype,
                    language=lang,
                    region=region,
                    city_tier=int(raw.get("city_tier", 2)),
                    age=int(raw.get("age", 30)),
                    gender=raw.get("gender"),
                    occupation=raw.get("occupation", "unspecified"),
                    caste_position=caste,
                    political_lean=raw.get("political_lean", "centrist"),
                    religiosity=raw.get("religiosity", "moderate"),
                    socioeconomic_class=raw.get("socioeconomic_class", "middle"),
                    media_diet=raw.get("media_diet", media_diet),
                    primary_platforms=platforms,
                    key_concerns=raw.get("key_concerns", []),
                    bio=raw.get("bio", ""),
                    initial_opinion=raw.get("initial_opinion", ""),
                )
            )
        return batch


def _pick(options: Iterable[object]) -> object:
    opts = list(options)
    return random.Random().choice(opts) if opts else options


def _sample_platforms(priors: list[Platform]) -> list[Platform]:
    """Pick 2-3 platforms from the archetype's prior list."""
    n = random.Random().randint(2, max(2, min(3, len(priors))))
    return random.Random().sample(priors, k=min(n, len(priors)))