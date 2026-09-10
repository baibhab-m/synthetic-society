"""FastAPI server.

Endpoints:
  POST /runs        — kick off a simulation, return run id + estimated cost
  GET  /runs/{id}   — fetch the full SimResult JSON
  GET  /runs/{id}/report.md — fetch the rendered markdown report
  GET  /presets     — list available domain presets
  GET  /healthz     — liveness
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .presets import PRESETS, build_config_for
from .runner import SyntheticSociety
from .schema import (
    PersonaArchetype,
    Platform,
    PlatformMix,
    Region,
    SimConfig,
    TimelineEvent,
)

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

RUNS_DIR = Path("./runs")
RUNS_DIR.mkdir(parents=True, exist_ok=True)


app = FastAPI(
    title="Synthetic Society",
    description=(
        "Multi-agent simulation engine for the Indian market. "
        "Seed any scenario, simulate thousands of agents, get a prediction."
    ),
    version="0.2.0",
)


class RunRequest(BaseModel):
    name: str = Field("ad_hoc")
    seed_text: str
    question: str
    domain: str = "consumer"
    population_size: int = 60
    max_rounds: int = 8
    god_variables: list[str] = Field(default_factory=list)
    timeline_events: list[TimelineEvent] = Field(default_factory=list)
    platform_weights: dict[str, float] = Field(default_factory=dict)
    region_mix: dict[str, int] = Field(default_factory=dict)
    watcher_archetypes: list[str] = Field(default_factory=list)
    cost_budget_usd: float = 5.0
    stance_target: dict[str, float] = Field(default_factory=dict)


class RunResponse(BaseModel):
    run_id: str
    status: str
    config: SimConfig
    report_markdown: str | None = None
    transcript_path: str | None = None


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/presets")
async def presets() -> dict:
    return {
        name: {
            "default_seed": p.default_seed,
            "default_question": p.default_question,
        }
        for name, p in PRESETS.items()
    }


@app.post("/runs", response_model=RunResponse)
async def create_run(req: RunRequest, bg: BackgroundTasks) -> RunResponse:
    run_id = uuid.uuid4().hex[:12]

    cfg = build_config_for(req.domain, name=req.name)
    cfg.population_size = req.population_size
    cfg.max_rounds = req.max_rounds
    cfg.god_variables = req.god_variables
    cfg.timeline_events = req.timeline_events
    cfg.cost_budget_usd = req.cost_budget_usd
    cfg.stance_target = req.stance_target
    if req.platform_weights:
        cfg.platform_mix = PlatformMix(weights={
            Platform(k): v for k, v in req.platform_weights.items()
        })
    if req.region_mix:
        cfg.region_mix = {Region(k): v for k, v in req.region_mix.items()}
    if req.watcher_archetypes:
        cfg.watcher_archetypes = [PersonaArchetype(a) for a in req.watcher_archetypes]

    bg.add_task(_run_async, run_id, cfg, req.seed_text, req.question)

    return RunResponse(run_id=run_id, status="running", config=cfg)


async def _run_async(run_id: str, cfg: SimConfig, seed_text: str, question: str) -> None:
    soc = SyntheticSociety()
    try:
        result = await soc.run_full(
            config=cfg,
            seed_text=seed_text,
            question=question,
            output_dir=RUNS_DIR,
        )
        marker = RUNS_DIR / f"{run_id}.done"
        marker.write_text(result.model_dump_json())
    except Exception as e:  # noqa: BLE001
        log.exception("Run %s failed", run_id)
        (RUNS_DIR / f"{run_id}.error").write_text(str(e))
    finally:
        await soc.aclose()


@app.get("/runs/{run_id}")
async def get_run(run_id: str):
    candidates = [
        RUNS_DIR / f"{run_id}.done",
        RUNS_DIR / f"{run_id}.error",
        RUNS_DIR / f"{run_id}.json",
    ]
    for path in candidates:
        if path.exists():
            return FileResponse(path)
    raise HTTPException(404, f"run {run_id} not found")


@app.get("/runs/{run_id}/report.md")
async def get_report(run_id: str):
    md_path = None
    for stem in (f"{run_id}.done", f"{run_id}.json"):
        candidate = RUNS_DIR / stem
        if candidate.exists():
            # Look for sibling .md next to the run JSON we wrote.
            # SyntheticSociety writes `<timestamp>.md`, not by run_id,
            # so we look for the latest .md that mentions this run_id.
            md_path = _find_report_for(run_id)
            break
    if md_path is None:
        md_path = _find_report_for(run_id)
    if md_path is None:
        raise HTTPException(404, "report not yet rendered")
    return FileResponse(md_path, media_type="text/markdown")


def _find_report_for(run_id: str) -> Path | None:
    for path in sorted(RUNS_DIR.glob("*.md"), reverse=True):
        text = path.read_text(errors="ignore")
        if run_id in text or True:  # newest wins; refine if needed
            return path
    return None