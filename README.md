# Synthetic Society

> A multi-agent social-simulation engine tuned for the **Indian market**.
> Seed any scenario — a product launch, a policy fight, a campus rumour, a fundraising round — and watch a synthetic India argue about it.

```
seed text  ─►  knowledge graph  ─►  personas (60+)
                                          │
                                          ▼
                              round-by-round agent loop
                              (memory, sentiment drift)
                                          │
                                          ▼
                                  markdown report
```

## Why this exists

Most multi-agent sim engines are written with US/EU defaults — soccer moms,
tech bros, suburban retirees. India doesn't fit those priors. Synthetic
Society ships with:

- **15 India-tuned persona archetypes** (tier-2 working professional,
  small-business owner, college student, homemaker rural/urban, farmer
  agrarian, daily-wage worker, political partisan, activist organizer,
  creator/influencer, investor/founder, …).
- **Per-archetype language priors** — Hinglish for urban students, Tanglish
  for tier-2 Tamil Nadu SMB, formal Hindi for political actors, Bengali/
  Marathi/Gujarati where it fits.
- **India-aware media diets** — WhatsApp forwards, Aaj Tak, Republic TV,
  The Ken, Inc42, Reddit India, Newslaundry, etc.
- **First-class seed loaders** for consumer, political, campus, and
  startup scenarios out of the box.

## Install

```bash
git clone https://github.com/baibhab-m/synthetic-society.git
cd synthetic-society
pip install -e .

cp .env.example .env
# Fill in LLM_API_KEY, optionally LLM_BASE_URL (OpenAI / OpenRouter / Qwen / etc.)
```

Any OpenAI-compatible endpoint works: OpenAI, OpenRouter, Groq, Together,
DashScope (Qwen), Sarvam, a local llama.cpp server, etc.

## Quick start

```bash
# 1. List domain presets
synsoc presets

# 2. Run one of them
synsoc run consumer --pop 60 --rounds 8

# 3. Or pass your own seed
synsoc run startup --seed-file my_pitch.md --question "Will it clear the round?"

# 4. Or fire up the API server
synsoc serve
# → POST /runs, GET /runs/{id}, GET /runs/{id}/report.md
```

Every run writes two files to `./runs/`:
- `<timestamp>_<domain>_<name>.json` — full transcript (every persona,
  every round, every message, the rendered report).
- `<timestamp>_<domain>_<name>.md` — just the report.

## Architecture

| Module | What it does |
|---|---|
| `schema.py` | Typed contract (Persona, Entity, Relation, AgentMessage, SimResult). |
| `llm.py` | Thin async OpenAI-compatible HTTP client (no vendor lock). |
| `graph.py` | Two-pass GraphRAG: entity extraction → relation extraction. |
| `personas.py` | India-tuned persona generator with archetype priors. |
| `engine.py` | Round-based simulation loop with memory, sentiment, stance drift. |
| `report.py` | Post-run analysis: per-archetype stats + ReportAgent LLM render. |
| `runner.py` | End-to-end orchestrator: `SyntheticSociety.run_full()`. |
| `presets.py` | Domain presets (consumer, political, campus, startup). |
| `seeds/*.py` | Real-world seed loaders (brand kit, policy brief, fundraise pitch). |
| `server.py` | FastAPI: `POST /runs`, `GET /runs/{id}`, `GET /presets`. |
| `cli.py` | Typer CLI: `synsoc run / presets / serve`. |

### Why hand-rolled, not autogen/langgraph?

We need fine-grained control over (a) language register per agent,
(b) audience targeting (public vs DM), (c) memory compression cadence,
(d) operator-injected "god events" mid-simulation. Off-the-shelf
agent frameworks push you toward tool-calling chat loops; that surface
area is exactly what we don't want.

## Domains

### 1. Consumer / brand reaction

```python
from synthetic_society.seeds import consumer
seed = consumer.brand_press_kit(
    brand="Boat",
    one_liner="Boat launches ₹4,999 ANC earbuds with 60hr battery",
    pricing="₹4,999 (intro), ₹5,999 (MRP)",
    claims=["Made in India silicon", "ANC tuned for Indian traffic noise",
            "60hr battery", "Spotify Tap integration"],
)
```

### 2. Political / civic

```python
from synthetic_society.seeds import political
seed = political.policy_brief(
    title="DPDP Act, 2025 — Rules notified",
    summary="Mandatory explicit consent, 72-hour breach disclosure, Data Protection Board with civil-court powers.",
    proponents=["MeitY", "NASSCOM"],
    opponents=["Internet Freedom Foundation", "SFLC.in"],
    affected_groups=["D2C startups", "gig workers", "hospitality", "healthcare"],
)
```

### 3. Campus / college ecosystem

```python
from synthetic_society.seeds import campus
seed = campus.policy_change(
    institute="BITS Pilani Goa",
    policy="Replace 7th-semester thesis with a 6-month AI-Native Builder track",
    why_now="Placements are down; institute wants shipped-revenue signal",
    likely_supporters=["CS/AI faculty", "serial-student founders"],
    likely_resistors=["non-CS faculty", "thesis-purist researchers"],
)
```

### 4. Startup / GTM

```python
from synthetic_society.seeds import startup
seed = startup.fundraise_pitch(
    company="BharatPay",
    sector="UPI fintech",
    round="Series A",
    ask="₹45 Cr at ₹450 Cr pre-money",
    traction="12 LPA UPI handles, 8% MoM growth",
    investors_in_flight=["Peak XV", "Accel", "Z47"],
    differentiators=["11-language voice confirmations", "auto-pay for recurring bills"],
)
```

## God events

Inject perturbations mid-simulation to test counterfactuals:

```bash
synsoc run consumer --god "RBI announces 28% GST on premium cards" \
                   --god "Viral tweet from @RandomHater about the campaign"
```

Each `--god` value is dropped on the population at the start of the
matching round (1-indexed).

## Configuration

| Env var | Default | What |
|---|---|---|
| `LLM_API_KEY` | (required) | OpenAI-compatible key |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | Any OpenAI-compat endpoint |
| `LLM_MODEL_NAME` | `gpt-4o-mini` | Model id |
| `MAX_AGENTS_PER_SIM` | `200` | Cap on persona count |
| `MAX_ROUNDS` | `20` | Cap on round count |
| `PARALLEL_AGENTS` | `8` | Concurrency for the loop |
| `DATABASE_URL` | SQLite | Swap to Postgres for >500-agent sims |

## Limits & honesty

- **The simulation is a synthetic sketch, not ground truth.** Use it to
  surface hypotheses, not to ship policy.
- **One LLM call per agent per round.** 60 personas × 8 rounds ≈ 500 calls.
  Each call has cost + latency — budget accordingly.
- **Memory is intentionally lossy.** We keep the last 5 events verbatim
  and a rolling summary; do not treat the transcript as ground-truth.
- **No framework, no vendor lock.** Drop in any OpenAI-compatible LLM.

## Inspired by

- [666ghj/MiroFish](https://github.com/666ghj/MiroFish) — the original
  multi-agent social-simulation demo (Shanda Group).
- [CAMEL-AI OASIS](https://github.com/camel-ai/oasis) — the open-source
  simulation engine MiroFish wraps.

All code in Synthetic Society is original. We borrowed only the high-level
pattern (seed → graph → sim → report), not any source.

## License

MIT No Attribution. See `LICENSE`.