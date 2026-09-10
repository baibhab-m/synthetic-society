"""Startup / GTM seed loaders.

Indian fundraising, launch, and partnership ecosystem.
"""

from __future__ import annotations


def fundraise_pitch(company: str, sector: str, round: str, ask: str,
                    traction: str, investors_in_flight: list[str],
                    differentiators: list[str]) -> str:
    return (
        f"COMPANY: {company}\n"
        f"SECTOR: {sector}\n"
        f"ROUND: {round}\n"
        f"ASK: {ask}\n"
        f"TRACTION: {traction}\n\n"
        f"INVESTORS IN FLIGHT: {', '.join(investors_in_flight)}\n"
        f"DIFFERENTIATORS: {', '.join(differentiators)}\n\n"
        "Simulate: (a) which investor is most likely to lead and at what terms; "
        "(b) what concerns will come up in partner meetings; (c) how will the "
        "founder community and Twitter India react; (d) what will skeptics and "
        "competitors say on launch day."
    )


def launch_plan(company: str, product: str, target_user: str,
                pricing: str, launch_channels: list[str]) -> str:
    return (
        f"COMPANY: {company}\n"
        f"PRODUCT: {product}\n"
        f"TARGET USER: {target_user}\n"
        f"PRICING: {pricing}\n"
        f"CHANNELS: {', '.join(launch_channels)}\n\n"
        "Simulate launch-day and week-after reaction across investors, "
        "users (urban + tier-2/3), creators, and competitors. Include "
        "WhatsApp-forwards / Reddit-India / Twitter / YouTube-tech-reviewer "
        "voices."
    )