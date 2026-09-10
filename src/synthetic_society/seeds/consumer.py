"""Consumer-product seed loaders.

Pulls Indian-market signals: Twitter/X, Reddit India, YouTube comments,
news coverage, app-store reviews. Returns a string ready to feed into
the graph builder.

You can plug any of these into `SyntheticSociety.run_full(seed_text=...)`.
"""

from __future__ import annotations

import logging
from typing import Iterable

log = logging.getLogger(__name__)


def brand_press_kit(brand: str, one_liner: str, pricing: str = "",
                    claims: Iterable[str] = ()) -> str:
    """Manual seed when you just want to think about a launch."""
    claims_list = "\n".join(f"- {c}" for c in claims) or "- (no extra claims given)"
    return (
        f"Brand: {brand}\n"
        f"One-liner: {one_liner}\n"
        f"Pricing: {pricing or 'unspecified'}\n"
        f"Claims:\n{claims_list}\n\n"
        "Context: This is the seed text for a Synthetic Society run. "
        "We want to simulate Indian consumer reaction across metros, tier-2, "
        "tier-3, students, homemakers, SMB owners, creators, and seniors."
    )


def hashtag_x_search(hashtag: str, n: int = 200) -> str:
    """Pull recent tweets around an Indian brand hashtag.

    Stub: real version uses the `bird` CLI (already on this machine) or
    Apify's Twitter actor. We return a placeholder for now so the rest of
    the engine still works without API keys.
    """
    log.warning("hashtag_x_search is a stub; returning synthetic placeholder")
    return (
        f"[Stub] {n} recent tweets about #{hashtag} would be aggregated here.\n"
        "Replace this stub with a real Twitter/X data pull before relying on it."
    )