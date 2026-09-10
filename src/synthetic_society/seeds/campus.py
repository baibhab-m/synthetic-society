"""Campus seed loaders — Indian college ecosystem.

Tuned for: BITS / IIM / IIT / NIT / IIIT / private universities /
state-level state universities. Placements, fests, culture, dating,
politics (SFI / ABVP / NSUI), entrepreneurship, mental health.
"""

from __future__ import annotations


def policy_change(institute: str, policy: str, why_now: str,
                  likely_supporters: list[str], likely_resistors: list[str]) -> str:
    return (
        f"INSTITUTE: {institute}\n"
        f"POLICY CHANGE: {policy}\n"
        f"WHY NOW: {why_now}\n\n"
        f"LIKELY SUPPORTERS:\n" + "\n".join(f"- {s}" for s in likely_supporters) + "\n\n"
        f"LIKELY RESISTORS:\n" + "\n".join(f"- {r}" for r in likely_resistors) + "\n\n"
        "Simulate student + faculty + alumni reaction over the next 30 days. "
        "Capture WhatsApp-group dynamics, Twitter/X discourse, and Reddit-style "
        "anonymous confession-board behaviour."
    )


def placement_season(institute: str, season: str, top_recruiters: list[str],
                     avg_ctc: float, highest_ctc: float,
                     international_offers: int) -> str:
    return (
        f"PLACEMENT SEASON — {institute}, {season}\n"
        f"Top recruiters: {', '.join(top_recruiters)}\n"
        f"Average CTC: ₹{avg_ctc} LPA\n"
        f"Highest CTC: ₹{highest_ctc} LPA\n"
        f"International offers: {international_offers}\n\n"
        "Simulate senior + junior + alumni + faculty reaction. Capture the "
        "inequality discourse (CSE vs non-CSE, male vs female, English vs "
        "regional-medium), the LinkedIn flex culture, and the placement "
        "whatsapp group vibe."
    )