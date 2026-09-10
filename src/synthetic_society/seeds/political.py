"""Political / civic seed loaders.

Indian context: state vs central, language-region dynamics, party-aligned
media ecosystems (Republic / Times Now / News18 / Newslaundry / The Wire /
Scroll.in / The Print), Twitter India, Reddit India, manifesto PDFs.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def policy_brief(title: str, summary: str, *, proponents: list[str],
                 opponents: list[str], affected_groups: list[str]) -> str:
    return (
        f"POLICY: {title}\n\n"
        f"SUMMARY:\n{summary}\n\n"
        f"PROPONENTS:\n" + "\n".join(f"- {p}" for p in proponents) + "\n\n"
        f"OPPONENTS:\n" + "\n".join(f"- {p}" for p in opponents) + "\n\n"
        f"AFFECTED GROUPS:\n" + "\n".join(f"- {g}" for g in affected_groups) + "\n\n"
        "Build a knowledge graph of entities (parties, ministries, industry "
        "bodies, civil-society orgs, regions, religions, sectors) and the "
        "relations between them. Then simulate public discourse over 3 months."
    )


def election_state(state: str, bjp_seats: int, inc_seats: int,
                   regional_seats: dict[str, int], indie_seats: int = 0) -> str:
    return (
        f"ELECTION CONTEXT ({state} state assembly):\n"
        f"- BJP: {bjp_seats}\n"
        f"- INC: {inc_seats}\n"
        f"- Regional parties: {regional_seats}\n"
        f"- Independents: {indie_seats}\n\n"
        "Generate the entity graph (candidates, parties, caste coalitions, "
        "industry groups, civil-society actors) and simulate discourse "
        "across partisan, activist, professional, and agrarian archetypes."
    )