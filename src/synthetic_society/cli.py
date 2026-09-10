"""Typer CLI.

Examples:
  synsoc run consumer --rounds 8 --pop 60
  synsoc run political --rounds 12 --pop 100 --seed-text @bill.txt
  synsoc run campus --rounds 5 --pop 40
  synsoc presets
  synsoc serve
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown

from .presets import PRESETS, build_config_for
from .runner import SyntheticSociety, run_preset
from .schema import (
    Platform,
    PlatformMix,
    PersonaArchetype,
    Region,
    SimConfig,
    TimelineEvent,
)

app = typer.Typer(add_completion=False, help="Synthetic Society CLI.")
console = Console()


@app.command()
def presets() -> None:
    """List built-in domain presets."""
    for name, p in PRESETS.items():
        console.print(f"[bold cyan]{name}[/bold cyan]")
        console.print(f"  seed:     {p.default_seed[:100]}...")
        console.print(f"  question: {p.default_question}")
        console.print()


@app.command()
def run(
    domain: str = typer.Option(..., help="consumer | political | campus | startup"),
    seed_text: Optional[str] = typer.Option(None, "--seed-text"),
    seed_file: Optional[Path] = typer.Option(None, "--seed-file", exists=True, dir_okay=False),
    question: Optional[str] = typer.Option(None, "--question", "-q"),
    pop: int = typer.Option(60, "--pop", help="population size"),
    rounds: int = typer.Option(8, "--rounds", "-r"),
    god: list[str] = typer.Option([], "--god", help="god-event, can repeat"),
    timeline: list[str] = typer.Option(
        [], "--timeline",
        help="Scheduled drop, format 'ROUND|LABEL|CONTENT|SOURCE|PLATFORM' (PLATFORM optional)",
    ),
    platform: list[str] = typer.Option(
        [], "--platform", "-p",
        help="platform=weight, can repeat (overrides preset defaults)",
    ),
    watcher: list[str] = typer.Option(
        [], "--watch", help="archetype to drill into in the report",
    ),
    budget: float = typer.Option(5.0, "--budget", help="USD cap on LLM spend"),
    output: Path = typer.Option(Path("./runs"), "--output", "-o"),
    print_report: bool = typer.Option(True, "--print/--no-print"),
) -> None:
    """Run a simulation end-to-end and render the report."""
    if domain not in PRESETS:
        raise typer.BadParameter(f"domain must be one of: {list(PRESETS.keys())}")

    if seed_file is not None:
        seed_text = seed_file.read_text(encoding="utf-8")
    elif seed_text is None:
        seed_text = PRESETS[domain].default_seed
    if "@" in (seed_text or "") and seed_file is None:
        ref = seed_text.strip()[1:]
        seed_text = Path(ref).read_text(encoding="utf-8")

    if question is None:
        question = PRESETS[domain].default_question

    cfg = build_config_for(domain)
    cfg.population_size = pop
    cfg.max_rounds = rounds
    cfg.god_variables = list(god)
    cfg.cost_budget_usd = budget

    for entry in timeline:
        parts = entry.split("|")
        if len(parts) < 3:
            raise typer.BadParameter(f"--timeline entry must be 'ROUND|LABEL|CONTENT[|SOURCE[|PLATFORM]]', got: {entry}")
        round_no, label, content = parts[0], parts[1], parts[2]
        source = parts[3] if len(parts) > 3 else ""
        try:
            pl = Platform(parts[4]) if len(parts) > 4 else Platform.TWITTER_X
        except ValueError:
            pl = Platform.TWITTER_X
        cfg.timeline_events.append(
            TimelineEvent(
                round=int(round_no),
                label=label,
                content=content,
                source=source,
                platform=pl,
            )
        )

    if platform:
        weights: dict[Platform, float] = {}
        for entry in platform:
            if "=" not in entry:
                raise typer.BadParameter(f"--platform entry must be 'platform=weight', got: {entry}")
            key, val = entry.split("=", 1)
            weights[Platform(key)] = float(val)
        cfg.platform_mix = PlatformMix(weights=weights)

    if watcher:
        cfg.watcher_archetypes = [PersonaArchetype(w) for w in watcher]

    console.print(
        f"[bold green]→ Running {domain} sim[/bold green] "
        f"({pop} personas × {rounds} rounds, budget ${budget:.2f})"
    )

    result = asyncio.run(
        SyntheticSociety().run_full(
            config=cfg,
            seed_text=seed_text,
            question=question,
            output_dir=output,
            save_transcript=True,
        )
    )

    console.print(
        f"[dim]Run finished. Cost: ${result.total_cost_usd:.3f} "
        f"(budget {'EXCEEDED' if result.budget_exceeded else 'OK'})[/dim]"
    )
    if print_report:
        console.print(Markdown(result.report_markdown))


@app.command()
def serve(
    host: str = "0.0.0.0",
    port: int = 8765,
    reload: bool = False,
) -> None:
    """Launch the FastAPI server."""
    import uvicorn
    uvicorn.run(
        "synthetic_society.server:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    app()