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
from .schema import SimConfig

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
        # Treat @path syntax as file ref
        ref = seed_text.strip()[1:]
        seed_text = Path(ref).read_text(encoding="utf-8")

    if question is None:
        question = PRESETS[domain].default_question

    cfg = build_config_for(domain)
    cfg.population_size = pop
    cfg.max_rounds = rounds
    cfg.god_variables = list(god)

    console.print(f"[bold green]→ Running {domain} sim[/bold green] "
                  f"({pop} personas × {rounds} rounds)")

    result = asyncio.run(
        SyntheticSociety().run_full(
            config=cfg,
            seed_text=seed_text,
            question=question,
            output_dir=output,
            save_transcript=True,
        )
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