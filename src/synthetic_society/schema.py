"""Typed schema for everything that flows through the engine.

Kept narrow on purpose — these are the contract between modules. Adding
fields is cheap; renaming them later is expensive.

Schema additions (v0.2):
  * PersonaArchetype: + NRI_DIASPORA, GIG_WORKER, MIGRANT_LABOUR, GOVT_EMPLOYEE,
    CRICKET_FAN; - RETIRED_GOVT_SERVANT, HOMEMAKER_RURAL, HOMEMAKER_URBAN
    (folded into HOMEMAKER with region/urbanity), SENIOR_CITIZEN (folded
    via age).
  * Language: - BHINGLISH, TANGISH (subsumed by HINGLISH + region);
    + ODIA, ASSAMESE, URDU, MAITHILI.
  * Region enum: Indian states + "diaspora".
  * Platform enum: which channel a message lives on.
  * EntityType enum: replaces free-text `Entity.type`.
  * CastePosition enum: high-level proxy the LLM conditions on; never
    surfaced as a per-agent disclosure.
  * SimConfig: + platform_mix, cost_budget_usd, watcher_archetypes,
    stance_target, timeline_events.
  * AgentMessage: + platform, evidence_citations, reach, virality_score.
  * Removed: RelationshipKind enum (unused), trust_scores (unwired),
    required `gender`, free-text `Entity.type`, dead `created_at` use.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---- Enums -----------------------------------------------------------------


class PersonaArchetype(str, Enum):
    METRO_PROFESSIONAL = "metro_professional"
    TIER2_WORKING_PROFESSIONAL = "tier2_working_professional"
    COLLEGE_STUDENT = "college_student"
    SMALL_BUSINESS_OWNER = "small_business_owner"
    HOMEMAKER = "homemaker"  # urban/rural folded in via region/urbanity
    CREATOR_INFLUENCER = "creator_influencer"
    POLITICAL_PARTISAN = "political_partisan"
    ACTIVIST_ORGANIZER = "activist_organizer"
    INVESTOR_FOUNDER = "investor_founder"
    FARMER_AGRARIAN = "farmer_agrarian"
    DAILY_WAGE_WORKER = "daily_wage_worker"
    RELIGIOUS_COMMUNITY_MEMBER = "religious_community_member"
    # v0.2 additions
    NRI_DIASPORA = "nri_diaspora"
    GIG_WORKER = "gig_worker"
    MIGRANT_LABOUR = "migrant_labour"
    GOVT_EMPLOYEE = "govt_employee"
    CRICKET_FAN = "cricket_fan"


class Language(str, Enum):
    ENGLISH = "en"
    HINDI = "hi"
    BENGALI = "bn"
    TAMIL = "ta"
    TELUGU = "te"
    MARATHI = "mr"
    GUJARATI = "gu"
    KANNADA = "kn"
    MALAYALAM = "ml"
    PUNJABI = "pa"
    ODIA = "or"
    ASSAMESE = "as"
    URDU = "ur"
    MAITHILI = "mai"
    # Mixed-language registers (kept — they're useful code-switching buckets)
    HINGLISH = "hinglish"  # Hindi + English code-switch, urban
    TANGLED_TAMIL = "tangled_tamil"  # Tamil + English code-switch, urban TN
    MANGLED_BHO = "bho_anglish"  # Bhojpuri + English code-switch, Bihar


class Region(str, Enum):
    """Indian state / UT, plus diaspora. Used as prior on Persona.location."""

    ANDHRA_PRADESH = "andhra_pradesh"
    ARUNACHAL_PRADESH = "arunachal_pradesh"
    ASSAM = "assam"
    BIHAR = "bihar"
    CHHATTISGARH = "chhattisgarh"
    GOA = "goa"
    GUJARAT = "gujarat"
    HARYANA = "haryana"
    HIMACHAL_PRADESH = "himachal_pradesh"
    JHARKHAND = "jharkhand"
    KARNATAKA = "karnataka"
    KERALA = "kerala"
    MADHYA_PRADESH = "madhya_pradesh"
    MAHARASHTRA = "maharashtra"
    MANIPUR = "manipur"
    MEGHALAYA = "meghalaya"
    MIZORAM = "mizoram"
    NAGALAND = "nagaland"
    ODISHA = "odisha"
    PUNJAB = "punjab"
    RAJASTHAN = "rajasthan"
    SIKKIM = "sikkim"
    TAMIL_NADU = "tamil_nadu"
    TELANGANA = "telangana"
    TRIPURA = "tripura"
    UTTAR_PRADESH = "uttar_pradesh"
    UTTARAKHAND = "uttarakhand"
    WEST_BENGAL = "west_bengal"
    DELHI_NCR = "delhi_ncr"
    JAMMU_KASHMIR = "jammu_kashmir"
    CHANDIGARH = "chandigarh"
    DIASPORA = "diaspora"


class CastePosition(str, Enum):
    """Sanitised high-level proxy. Drives priors only; never disclosed.

    The simulation never reveals this to other agents or in reports as
    an identifier — it only conditions the LLM's persona generation."""

    GENERAL = "general"
    FORWARD = "forward_obo"  # "upper" castes that are also OBC in some states
    OBC = "obc"
    SC = "sc"
    ST = "st"
    MINORITY = "minority"  # religious minorities


class Platform(str, Enum):
    TWITTER_X = "twitter_x"
    WHATSAPP = "whatsapp"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    YOUTUBE = "youtube"
    REDDIT = "reddit"
    LINKEDIN = "linkedin"
    LINKEDIN_NEWS = "linkedin_news"
    TV_NEWS_DEBATE = "tv_news_debate"
    PRINT_OPED = "print_oped"
    REDDIT_INDIA = "reddit_india"
    ANONYMOUS_CONFESSION = "anonymous_confession"
    QUORA = "quora"
    KOO = "koo"
    SHARE_CHAT = "share_chat"


class EntityType(str, Enum):
    PERSON = "person"
    ORGANIZATION = "organization"
    COMPANY = "company"
    PRODUCT = "product"
    BRAND = "brand"
    EVENT = "event"
    POLICY = "policy"
    POLICY_TEXT = "policy_text"
    COURT_CASE = "court_case"
    SCHEME = "scheme"  # PM-KISAN, MGNREGA, Ayushman Bharat, ...
    LOCATION = "location"
    CITY = "city"
    STATE = "state"
    COMMUNITY = "community"
    HASHTAG = "hashtag"
    PARTY = "party"
    RELIGION = "religion"
    SECTOR = "sector"
    ASSET = "asset"
    RISK = "risk"
    TREND = "trend"


# ---- Graph layer -----------------------------------------------------------


class Entity(BaseModel):
    id: str
    type: EntityType
    name: str
    attrs: dict[str, Any] = Field(default_factory=dict)


class Relation(BaseModel):
    src: str
    dst: str
    kind: str
    weight: float = 1.0
    attrs: dict[str, Any] = Field(default_factory=dict)


class KnowledgeGraph(BaseModel):
    entities: list[Entity] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)


# ---- Persona layer ---------------------------------------------------------


class Persona(BaseModel):
    id: str
    name: str
    archetype: PersonaArchetype
    language: Language
    region: Region
    city_tier: int = Field(ge=1, le=3)  # 1 = metro, 2 = tier-2, 3 = tier-3/rural
    age: int = Field(ge=14, le=90)
    gender: str | None = None  # optional; rarely moves sim behavior
    occupation: str
    caste_position: CastePosition = CastePosition.GENERAL
    political_lean: str = "centrist"
    religiosity: str = "moderate"
    socioeconomic_class: str = "middle"
    media_diet: list[str] = Field(default_factory=list)
    primary_platforms: list[Platform] = Field(default_factory=list)
    """Which platforms this persona actively posts on. Drives engine routing."""
    key_concerns: list[str] = Field(default_factory=list)
    bio: str
    initial_opinion: str


# ---- Agent memory / message layer ------------------------------------------


class EvidenceCitation(BaseModel):
    """A real-world entity a message references. Lets reports say '7 agents
    cited RBI circular X' instead of just quoting noise."""

    entity_id: str
    entity_name: str
    entity_type: EntityType
    quote: str = ""  # the span of the message that cited it


class AgentMessage(BaseModel):
    sender_id: str
    content: str
    language: Language
    platform: Platform
    round: int
    visibility: str = "public"  # public, group, dm
    audience: list[str] = Field(default_factory=list)
    sentiment: float = 0.0  # -1..+1
    importance: float = 0.5  # 0..1; used for memory compression
    reach: int = 0  # estimated audience size given platform + persona
    virality_score: float = 0.0  # 0..1; did this quote get amplified?
    evidence_citations: list[EvidenceCitation] = Field(default_factory=list)


class AgentMemory(BaseModel):
    """Per-agent memory summary. Full transcript lives in SimResult.rounds."""

    persona_id: str
    round: int
    short_term: list[str] = Field(default_factory=list)  # last 5 verbatim
    long_term_summary: str = ""  # rolling summary of prior rounds
    stance_shift: float = 0.0  # -1..+1 net movement since start
    emotional_state: str = "neutral"


# ---- Simulation core -------------------------------------------------------


class TimelineEvent(BaseModel):
    """Scheduled operator drop. Fires at the given round; the population
    sees it before deciding their action."""

    round: int
    label: str  # short tag shown in reports ("rbi_rate_hike", "viral_tweet_X")
    content: str  # the actual drop, surfaced in the agent prompt
    source: str = ""  # e.g. "RBI circular", "@twitter_user handle"
    platform: Platform = Platform.TWITTER_X


class PlatformMix(BaseModel):
    """What fraction of the population each platform hosts. Sums to ~1.0."""

    weights: dict[Platform, float] = Field(default_factory=dict)

    def normalize(self) -> "PlatformMix":
        total = sum(self.weights.values()) or 1.0
        return PlatformMix(
            weights={p: w / total for p, w in self.weights.items()}
        )


class SimConfig(BaseModel):
    name: str
    seed_topic: str
    domain: str  # "consumer" | "political" | "campus" | "startup" | "custom"
    max_rounds: int = 20
    population_size: int = 80

    # v0.2 additions
    archetype_mix: dict[PersonaArchetype, int] = Field(default_factory=dict)
    region_mix: dict[Region, int] = Field(default_factory=dict)
    """Optional prior; if empty, persona region is LLM-sampled from realistic
    state-population weights."""
    language_mix: dict[Language, float] = Field(default_factory=dict)
    platform_mix: PlatformMix = Field(default_factory=PlatformMix)
    """Which platforms host this sim. Empty = equal weight across Twitter,
    WhatsApp, Reddit India, YouTube."""
    cost_budget_usd: float = 5.0
    """Hard cap on LLM spend per run. Engine stops if exceeded."""
    watcher_archetypes: list[PersonaArchetype] = Field(default_factory=list)
    """If non-empty, the ReportAgent drills into these archetypes first.
    If empty, all archetypes are reported."""
    stance_target: dict[str, float] = Field(default_factory=dict)
    """Bias the initial opinion distribution. Keys are stance labels
    ('pro', 'anti', 'neutral', 'undecided'); values are fractions summing
    to ~1.0. Empty = let the LLM decide."""
    timeline_events: list[TimelineEvent] = Field(default_factory=list)
    """Scheduled news drops at specific rounds. Independent of `god_variables`
    (which is the legacy free-text list, still supported for back-compat)."""
    god_variables: list[str] = Field(default_factory=list)


class SimRound(BaseModel):
    round: int
    messages: list[AgentMessage] = Field(default_factory=list)
    god_event: str | None = None  # legacy compat
    timeline_events: list[TimelineEvent] = Field(default_factory=list)
    cost_usd_so_far: float = 0.0


class SimResult(BaseModel):
    config: SimConfig
    graph: KnowledgeGraph
    personas: list[Persona]
    rounds: list[SimRound] = Field(default_factory=list)
    report_markdown: str = ""
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: datetime | None = None
    total_cost_usd: float = 0.0
    budget_exceeded: bool = False