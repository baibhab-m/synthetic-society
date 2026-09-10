"""Domain presets — India-tuned defaults for each scenario.

Adding a new domain = adding one entry here + (optionally) a custom seed
loader under `synthetic_society.seeds.<domain>`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .schema import SimConfig


@dataclass
class Preset:
    default_seed: str
    default_question: str
    archetype_mix: dict = field(default_factory=dict)


PRESETS: dict[str, Preset] = {
    "consumer": Preset(
        default_seed=(
            "CRED is launching a new premium tier at ₹10,000/year with concierge "
            "bill-pay, airport lounge, and exclusive drop access. The card already "
            "has 12M users. The launch will be fronted by a Ranveer Singh campaign. "
            "Pricing is double of any existing Indian premium card."
        ),
        default_question=(
            "Will CRED Premium hit 200k paid subscribers in the first 90 days, "
            "and which consumer segment will drive/stall it?"
        ),
    ),
    "political": Preset(
        default_seed=(
            "The central government has tabled the Digital Personal Data Protection "
            "Bill, 2025. It mandates explicit consent for processing, 72-hour breach "
            "disclosure, and creates a Data Protection Board with sweeping penalties. "
            "Industry bodies (NASSCOM, CII) have called it 'compliance-heavy'; civil "
            "society groups (Internet Freedom Foundation, SFLC.in) say it doesn't go "
            "far enough on state surveillance carveouts."
        ),
        default_question=(
            "How will Indian public discourse around DPDP shift over the next "
            "3 months across urban professionals, political partisans, activists, "
            "and SMB owners? Will there be a sustained protest movement?"
        ),
    ),
    "campus": Preset(
        default_seed=(
            "BITS Pilani has announced a new 6-month 'AI-Native Builder' track that "
            "replaces the traditional 7th-semester thesis. Students split a company "
            "in cohorts of 4, get ₹20L seed funding from the institute, and must "
            "ship to paying customers before graduation. Placements for this batch "
            "will weigh shipped revenue 50%, CGPA 30%, interviews 20%."
        ),
        default_question=(
            "How will the BITS Pilani campus react? Which subgroups will lead, "
            "which will resist, and which side will faculty take?"
        ),
    ),
    "startup": Preset(
        default_seed=(
            "A Bengaluru-based seed-stage fintech called 'BharatPay' is going to "
            "market with an AI-powered UPI auto-pay feature that learns a user's "
            "recurring payments (rent, EMI, school fees, OTT subs) and executes "
            "them with one-tap confirmation. They're pitching Series A at a ₹450Cr "
            "pre-money valuation to Peak XV, Accel, and Z47. Differentiator: "
            "regional-language voice confirmations in 11 languages."
        ),
        default_question=(
            "Will BharatPay clear the round at or above the ask? Which investor "
            "is most likely to lead, what concerns will they raise in partner "
            "meet, and how will the founder community react publicly?"
        ),
    ),
}


def build_config_for(preset: str, *, name: str | None = None) -> SimConfig:
    p = PRESETS[preset]
    return SimConfig(
        name=name or preset,
        seed_topic=p.default_seed[:120],
        domain=preset,
        max_rounds=8,
        population_size=60,
        archetype_mix=p.archetype_mix,
    )