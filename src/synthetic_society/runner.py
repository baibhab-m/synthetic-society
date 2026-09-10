"""End-to-end orchestration: seed -> graph -> personas -> sim -> report."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from .engine import SimulationLoop
from .graph import GraphBuilder
from .llm import LLMClient
from .personas import PersonaGenerator
from .report import ReportAgent
from .schema import KnowledgeGraph, SimConfig, SimResult

log = logging.getLogger(__name__)


class SyntheticSociety:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or LLMClient()
        self.graph_builder = GraphBuilder(self.llm)
        self.persona_generator = PersonaGenerator(self.llm)
        self.loop = SimulationLoop(self.llm)
        self.reporter = ReportAgent(self.llm)

    async def aclose(self) -> None:
        await self.llm.aclose()

    async def run_full(
        self,
        *,
        config: SimConfig,
        seed_text: str,
        question: str,
        output_dir: str | Path = "./runs",
        save_transcript: bool = True,
    ) -> SimResult:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        run_id = f"{datetime.utcnow():%Y%m%d_%H%M%S}_{config.domain}_{config.name}"

        # 1. Graph
        log.info("Building knowledge graph for run %s", run_id)
        graph = await self.graph_builder.build(seed_text, hint=config.seed_topic)

        # 2. Personas
        log.info("Generating personas")
        personas = await self.persona_generator.generate(config, graph)

        # 3. Sim
        log.info(
            "Running simulation: %d rounds x %d personas (budget $%.2f)",
            config.max_rounds, len(personas), config.cost_budget_usd,
        )
        result = SimResult(config=config, graph=graph, personas=personas)
        sim = await self.loop.run(config, personas)
        result.rounds = sim.rounds
        result.finished_at = sim.finished_at
        result.total_cost_usd = sim.total_cost_usd
        result.budget_exceeded = sim.budget_exceeded

        # 4. Report
        log.info("Rendering report")
        result.report_markdown = await self.reporter.render(result, question)
        result.finished_at = result.finished_at or datetime.utcnow()

        # 5. Persist
        if save_transcript:
            run_path = Path(output_dir) / f"{run_id}.json"
            run_path.write_text(result.model_dump_json(indent=2))
            log.info("Saved run to %s", run_path)
            (Path(output_dir) / f"{run_id}.md").write_text(
                f"# {config.name}\n\n**Topic:** {config.seed_topic}\n\n"
                f"**Question:** {question}\n\n---\n\n{result.report_markdown}"
            )

        return result


async def run_preset(
    preset: str,
    *,
    seed_text: str | None = None,
    question: str | None = None,
    population_size: int = 60,
    max_rounds: int = 8,
    god_variables: list[str] | None = None,
    output_dir: str = "./runs",
) -> SimResult:
    """Convenience: pick a domain preset + sensible defaults."""

    from .presets import PRESETS, build_config_for

    if preset not in PRESETS:
        raise ValueError(f"Unknown preset '{preset}'. Choose from: {list(PRESETS.keys())}")
    cfg = build_config_for(preset)
    cfg.population_size = population_size
    cfg.max_rounds = max_rounds
    if god_variables is not None:
        cfg.god_variables = god_variables

    soc = SyntheticSociety()
    try:
        seed = seed_text or PRESETS[preset].default_seed
        q = question or PRESETS[preset].default_question
        return await soc.run_full(
            config=cfg,
            seed_text=seed,
            question=q,
            output_dir=output_dir,
        )
    finally:
        await soc.aclose()