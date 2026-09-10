"""India-tuned persona generator.

Given a seed topic + extracted knowledge graph, produce N personas whose
archetype distribution matches `config.archetype_mix` (or falls back to a
sensible default per domain).

What makes these India-tuned vs generic-LLM personas:
- Archetype priors reflect actual Indian demographic/socioeconomic segments
  (not US/UK defaults like "soccer mom" / "tech bro").
- Language is forced per archetype (Hinglish for college students, Tanglish
  for tier-2 Tamil Nadu SMB, formal Hindi for political actors, etc.).
- Media diet reflects the real Indian news ecosystem (WhatsApp forwards +
  TV news channel + Twitter/X India + Reddit India + YouTube).
- Initial opinion is generated in the persona's own language register.
"""

from __future__ import annotations

import logging
import random
from typing import Iterable

from .config import get_settings
from .llm import LLMClient
from .schema import (
    KnowledgeGraph,
    Language,
    Persona,
    PersonaArchetype,
    SimConfig,
)

log = logging.getLogger(__name__)


ARCHETYPE_DEFAULTS: dict[str, dict[PersonaArchetype, int]] = {
    "consumer": {
        PersonaArchetype.METRO_PROFESSIONAL: 25,
        PersonaArchetype.TIER2_WORKING_PROFESSIONAL: 20,
        PersonaArchetype.COLLEGE_STUDENT: 15,
        PersonaArchetype.SMALL_BUSINESS_OWNER: 10,
        PersonaArchetype.HOMEMAKER_URBAN: 10,
        PersonaArchetype.HOMEMAKER_RURAL: 5,
        PersonaArchetype.CREATOR_INFLUENCER: 5,
        PersonaArchetype.SENIOR_CITIZEN: 5,
        PersonaArchetype.DAILY_WAGE_WORKER: 5,
    },
    "political": {
        PersonaArchetype.POLITICAL_PARTISAN: 30,
        PersonaArchetype.ACTIVIST_ORGANIZER: 15,
        PersonaArchetype.METRO_PROFESSIONAL: 15,
        PersonaArchetype.SMALL_BUSINESS_OWNER: 10,
        PersonaArchetype.FARMER_AGRARIAN: 10,
        PersonaArchetype.RELIGIOUS_COMMUNITY_MEMBER: 10,
        PersonaArchetype.SENIOR_CITIZEN: 5,
        PersonaArchetype.COLLEGE_STUDENT: 5,
    },
    "campus": {
        PersonaArchetype.COLLEGE_STUDENT: 60,
        PersonaArchetype.CREATOR_INFLUENCER: 10,
        PersonaArchetype.INVESTOR_FOUNDER: 5,
        PersonaArchetype.METRO_PROFESSIONAL: 10,
        PersonaArchetype.ACTIVIST_ORGANIZER: 10,
        PersonaArchetype.RELIGIOUS_COMMUNITY_MEMBER: 5,
    },
    "startup": {
        PersonaArchetype.INVESTOR_FOUNDER: 35,
        PersonaArchetype.METRO_PROFESSIONAL: 20,
        PersonaArchetype.COLLEGE_STUDENT: 15,
        PersonaArchetype.SMALL_BUSINESS_OWNER: 15,
        PersonaArchetype.CREATOR_INFLUENCER: 10,
        PersonaArchetype.ACTIVIST_ORGANIZER: 5,
    },
}


ARCHETYPE_LANGUAGE_PRIOR: dict[PersonaArchetype, list[Language]] = {
    PersonaArchetype.METRO_PROFESSIONAL: [Language.ENGLISH, Language.HINGLISH],
    PersonaArchetype.TIER2_WORKING_PROFESSIONAL: [Language.HINGLISH, Language.HINDI],
    PersonaArchetype.COLLEGE_STUDENT: [Language.HINGLISH, Language.ENGLISH, Language.BHINGLISH],
    PersonaArchetype.SMALL_BUSINESS_OWNER: [Language.HINDI, Language.HINGLISH, Language.GUJARATI],
    PersonaArchetype.HOMEMAKER_URBAN: [Language.HINDI, Language.HINGLISH],
    PersonaArchetype.HOMEMAKER_RURAL: [Language.HINDI, Language.BENGALI, Language.TAMIL],
    PersonaArchetype.SENIOR_CITIZEN: [Language.HINDI, Language.ENGLISH],
    PersonaArchetype.CREATOR_INFLUENCER: [Language.HINGLISH, Language.ENGLISH],
    PersonaArchetype.POLITICAL_PARTISAN: [Language.HINDI, Language.HINGLISH],
    PersonaArchetype.ACTIVIST_ORGANIZER: [Language.ENGLISH, Language.HINGLISH],
    PersonaArchetype.INVESTOR_FOUNDER: [Language.ENGLISH, Language.HINGLISH],
    PersonaArchetype.FARMER_AGRARIAN: [Language.HINDI, Language.PUNJABI, Language.TELUGU],
    PersonaArchetype.DAILY_WAGE_WORKER: [Language.HINDI, Language.BENGALI, Language.TAMIL],
    PersonaArchetype.RELIGIOUS_COMMUNITY_MEMBER: [Language.HINDI, Language.TAMIL, Language.BENGALI],
    PersonaArchetype.RETIRED_GOVT_SERVANT: [Language.HINDI, Language.ENGLISH],
}


MEDIA_DIETS = {
    "metro_professional": ["The Ken", "Mint", "Twitter/X", "LinkedIn", "YouTube tech reviewers"],
    "tier2_working_professional": ["WhatsApp groups", "Aaj Tak", "Zee News", "YouTube", "Instagram"],
    "college_student": ["Instagram", "YouTube", "Reddit India", "Twitter/X", "college WhatsApp groups"],
    "small_business_owner": ["WhatsApp Business", "Aaj Tak", "CNBC Awaaz", "YouTube", "local cable news"],
    "homemaker_urban": ["WhatsApp family groups", "Star Plus", "Instagram", "YouTube cooking"],
    "homemaker_rural": ["WhatsApp forwards", "DD News", "Star Plus", "regional YouTube"],
    "senior_citizen": ["Aaj Tak", "ABP News", "DD News", "newspaper", "WhatsApp family"],
    "creator_influencer": ["Twitter/X", "Instagram", "YouTube analytics", "trending reels"],
    "political_partisan": ["Republic TV", "Times Now", "ABP Majha", "WhatsApp ideological groups", "Twitter/X"],
    "activist_organizer": ["Newslaundry", "Scroll.in", "The Wire", "Twitter/X", "Instagram"],
    "investor_founder": ["The Ken", "Inc42", "YourStory", "TechCrunch", "Twitter/X", "Substack"],
    "farmer_agrarian": ["DD Kisan", "WhatsApp mandi groups", "local radio", "Aaj Tak"],
    "daily_wage_worker": ["WhatsApp", "regional YouTube", "Star Plus"],
    "religious_community_member": ["WhatsApp devotional groups", "Sanskar TV", "regional religious channels"],
    "retired_govt_servant": ["DD News", "The Hindu", "Aaj Tak", "newspaper"],
}


SYSTEM_PROMPT = """You are a synthetic-population generator for India.

You are producing fictional, statistically-plausible personas that will be
used to drive a multi-agent simulation. Each persona must:
- Be grounded in a real Indian social archetype (use the seed topic and
  knowledge graph to pick a relevant slice of society).
- Have a distinct voice in their assigned language register (Hinglish for
  urban students, formal Hindi for political actors, Tanglish for tier-2
  Tamil Nadu SMB, etc.). Do NOT write everyone in the same flavour.
- Have a clear `initial_opinion` on the seed topic that is internally
  consistent with their background.
- Have realistic `key_concerns` (rent, EMI, child's school, caste dignity,
  pilgrimage, exam prep, dal rotations, etc.).

Output JSON only. Format:
{
  "personas": [
    {
      "name": "...",
      "age": 28,
      "gender": "...",
      "occupation": "...",
      "city_tier": 1,
      "political_lean": "...",
      "religiosity": "...",
      "socioeconomic_class": "...",
      "media_diet": ["..."],
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

        # Group batches by archetype so the LLM can produce coherent
        # voices for that slice instead of mixing every kind in one prompt.
        for archetype, count in mix.items():
            if count <= 0:
                continue
            batch = await self._generate_batch(
                archetype=archetype,
                count=count,
                seed_topic=config.seed_topic,
                graph=graph,
            )
            personas.extend(batch)

        # Assign stable ids.
        for i, p in enumerate(personas):
            p.id = f"p{i:04d}"

        log.info("Generated %d personas across %d archetypes", len(personas), len(mix))
        return personas

    def _resolve_mix(self, config: SimConfig) -> dict[PersonaArchetype, int]:
        if config.archetype_mix:
            return config.archetype_mix
        default = ARCHETYPE_DEFAULTS.get(config.domain, ARCHETYPE_DEFAULTS["consumer"])
        # Scale to population_size.
        total = sum(default.values())
        scale = max(1, config.population_size) / max(1, total)
        return {
            archetype: max(1, int(round(count * scale)))
            for archetype, count in default.items()
        }

    async def _generate_batch(
        self,
        *,
        archetype: PersonaArchetype,
        count: int,
        seed_topic: str,
        graph: KnowledgeGraph,
    ) -> list[Persona]:
        lang_options = ARCHETYPE_LANGUAGE_PRIOR.get(
            archetype, [Language.HINGLISH, Language.ENGLISH]
        )
        media_diet = MEDIA_DIETS.get(archetype.value, ["Twitter/X", "YouTube"])

        entity_table = "\n".join(
            f"- {e.name} ({e.type})" for e in graph.entities[:25]
        )
        user = (
            f"Seed topic: {seed_topic}\n\n"
            f"Key entities in this world:\n{entity_table or '(none)'}\n\n"
            f"Generate {count} personas of archetype `{archetype.value}`. "
            f"Language register prior: {', '.join(l.value for l in lang_options)}. "
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
            lang = self._pick_language(lang_options)
            batch.append(
                Persona(
                    id="",
                    name=raw.get("name", "Anonymous"),
                    archetype=archetype,
                    language=lang,
                    city_tier=int(raw.get("city_tier", 2)),
                    age=int(raw.get("age", 30)),
                    gender=raw.get("gender", "unspecified"),
                    occupation=raw.get("occupation", "unspecified"),
                    political_lean=raw.get("political_lean", "centrist"),
                    religiosity=raw.get("religiosity", "moderate"),
                    socioeconomic_class=raw.get("socioeconomic_class", "middle"),
                    media_diet=raw.get("media_diet", media_diet),
                    key_concerns=raw.get("key_concerns", []),
                    bio=raw.get("bio", ""),
                    initial_opinion=raw.get("initial_opinion", ""),
                )
            )
        return batch

    @staticmethod
    def _pick_language(options: Iterable[Language]) -> Language:
        opts = list(options)
        if not opts:
            return Language.HINGLISH
        return random.Random().choice(opts)