<div align="center">

# 🪔 Synthetic Society

**Spin up a synthetic India. Watch it argue about your idea.**

A multi-agent social-simulation engine tuned for the Indian market.
Seed any scenario — a product launch, a policy fight, a campus rumour, a
fundraising round — and 60–2000 personas will argue about it across
Twitter, WhatsApp, Reddit India, TV debates, confession boards, and
print op-eds, in 13 languages and 3 code-switching registers.

</div>

<div align="center">

[![PyPI](https://img.shields.io/pypi/v/synthetic-society?style=flat-square&color=blue)](https://pypi.org/project/synthetic-society/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue?style=flat-square)](https://www.python.org)
[![License: MIT-0](https://img.shields.io/badge/license-MIT--0-blue?style=flat-square)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000?style=flat-square)](https://docs.astral.sh/ruff/)
[![Docker](https://img.shields.io/badge/docker-ready-2496ed?style=flat-square&logo=docker&logoColor=white)](docker-compose.yml)
[![Stars](https://img.shields.io/github/stars/baibhab-m/synthetic-society?style=flat-square)](https://github.com/baibhab-m/synthetic-society/stargazers)

**Built by [Baibhab Mishra](https://github.com/baibhab-m)** · Inspired by
[666ghj/MiroFish](https://github.com/666ghj/MiroFish) and
[CAMEL-AI OASIS](https://github.com/camel-ai/oasis) — both credited below.

</div>

---

## Why this exists

Most multi-agent sim engines ship with US/EU priors: *soccer moms, tech
bros, suburban retirees.* India doesn't fit those defaults — and **the
difference is the whole point.**

| | CAMEL OASIS / MiroFish | Synthetic Society |
|---|---|---|
| Default archetypes | ~10 generic personas | **17 India-tuned** (NRI diaspora, gig workers, migrant labour, PSU babus, cricket fans, etc.) |
| Regions | Country-level | **31 Indian states + diaspora**, weighted by real population (UP-heavy, TN separate, NE separate) |
| Languages | English only | **13 + 3 code-switching registers** (Tanglish, Bhojpuri-English, Hinglish) |
| Platforms | 2–3 chat rooms | **15 platforms** with per-archetype priors (WhatsApp, Twitter, Reddit India, Koo, ShareChat, TV debate, print op-ed, anonymous confession boards…) |
| Media diet | Generic | **India-aware** — Aaj Tak, Republic TV, The Ken, Inc42, Reddit India, Newslaundry, WhatsApp forwards |
| Evidence | — | Agents tag **real entities** (PM-KISAN, RBI circular, a brand); report aggregates them |
| Cost control | — | **Hard USD cap**; sim halts on overrun |
| Seed loaders | Generic text | **First-class loaders** for consumer, political, campus, startup |

**Use it to:** pressure-test a launch in a Tier-2 city, stress-test a
policy brief against opposition framings, simulate a campus firestorm
before the principal sees it, or rehearse a Series-A pitch against an
LPs-shaped persona mix.

**Do not use it to:** ship policy, replace user research, or pretend a
simulation is ground truth. (See [Limits](#-limits--honesty).)

---

## What it actually does

```text
   your seed text
        │
        ▼
 ┌──────────────┐    ┌──────────────────┐    ┌─────────────────────┐
 │  GraphRAG    │───▶│   personas.py    │───▶│   engine.py loop    │
 │  entity →    │    │  archetype ×      │    │  round-by-round,    │
 │  relations   │    │  state × lang ×   │    │  memory + drift,    │
 └──────────────┘    │  platform priors  │    │  platform routing   │
                     └──────────────────┘    └──────────┬──────────┘
                                                        │
                                                        ▼
                                              ┌──────────────────┐
                                              │    report.py     │
                                              │  per-archetype + │
                                              │  per-platform +  │
                                              │  evidence rollup │
                                              └────────┬─────────┘
                                                       ▼
                                          runs/<ts>_<domain>_<name>.md
                                          runs/<ts>_<domain>_<name>.json
```

---

## 📺 What the output looks like

Run `synsoc run consumer --pop 80 --rounds 8` against the Boat earbuds
seed and the report renders something like this:

> ### Verdict: **mixed-positive, price-sensitive**
>
> 64% of synthetic India reached a stance by round 6. Of those:
> - **42% positive** — "Made in India silicon" lands hardest with the
>   *swadeshi-tech-evangelist* and *govt-employee* archetypes
> - **31% price-skeptical** — "₹4,999 for Boat is OnePlus territory now"
>   (NRI diaspora + gig workers, mostly on Twitter X and Reddit India)
> - **18% skeptical** — "ANC tuned for Indian traffic noise" is a
>   viral quote bait; WhatsApp forwards amplify it
> - **9% undecided** — mostly PrintOpEd and TVDebate voices
>
> **Top objections (by frequency):**
> 1. "Boat ka audio kabhi flagship nahi tha." — *tech-enthusiast*
> 2. "₹4,999 mein Sony bhi milta hai." — *value-seeker*
> 3. "ANC ka data toh dekhna padega." — *audiophile-purist*
>
> **Top amplifiers (who drove virality):**
> - *cricket-fan* archetype: 3.4× engagement multiplier
> - *nri-diaspora* on Twitter X: cross-pollinated to /r/india
> - *anonymous-confession-board* voices: invented a "my Boat broke in
>   6 months" narrative that went semi-viral
>
> **Evidence cited:** 14 unique entities (PM-KISAN, Make in India,
> Spotify India, OnePlus Nord, Sony WF-C500, Boat Rockerz lineage,
> Reddit r/IndianGaming, etc.)

*Actual numbers will vary — this is a representative sample from a
representative run.*

---

## ⚡ Install (60 seconds)

```bash
pip install synthetic-society
synsoc --help
```

…or from source:

```bash
git clone https://github.com/baibhab-m/synthetic-society.git
cd synthetic-society
pip install -e .

cp .env.example .env
# Add your LLM_API_KEY. Any OpenAI-compatible endpoint works:
# OpenAI, OpenRouter, Groq, Together, DashScope (Qwen), Sarvam,
# Mistral, a local llama.cpp server — anything.
```

> Requires **Python 3.11+**. Tested on macOS, Linux, WSL2.

**Zero-infra Docker mode:**

```bash
docker compose up
# API on :8765 — POST /runs, GET /runs/{id}, GET /runs/{id}/report.md
```

---

## 🚀 Quick start

```bash
# 1. List the domain presets you get out of the box
synsoc presets

# 2. Run one (≈ 500 LLM calls, ≈ $0.30 with gpt-4o-mini)
synsoc run consumer --pop 60 --rounds 8

# 3. Or pass your own seed
synsoc run startup --seed-file my_pitch.md --question "Will it clear the round?"

# 4. Mid-simulation perturbations — operators as minor deities
synsoc run political \
  --timeline "2|rbi_hike|Repo rate +25bps|RBI circular|twitter_x" \
  --timeline "4|viral_tweet|@opposition_leader calls it anti-farmer|@opposition_leader|twitter_x"

# 5. Multi-platform sim (Twitter + WhatsApp + Reddit, heavier but reads real)
synsoc run consumer --pop 80 --rounds 12 \
  --platform twitter_x=3 --platform whatsapp=2 --platform reddit_india=1 \
  --watch gig_worker --watch nri_diaspora --budget 1.50

# 6. Or fire up the API server
synsoc serve
```

Every run writes two files to `./runs/`:
- `<timestamp>_<domain>_<name>.json` — full transcript (every persona,
  every round, every message, the rendered report)
- `<timestamp>_<domain>_<name>.md` — just the report

---

## 🧬 Architecture

A 3-file reading order if you're new to the code:

| Read this | Why |
|---|---|
| 1. **`schema.py`** | The typed contract. 17 archetypes × 31 states × 13 languages × 15 platforms; cost budget, timeline events, evidence citations. |
| 2. **`runner.py`** | End-to-end orchestrator. `SyntheticSociety.run_full()`. 80 lines. The whole pipeline in one place. |
| 3. **`engine.py`** | Round-based loop. Routes each agent to their primary platform, enforces USD budget. |

Full module map:

| Module | What it does |
|---|---|
| `schema.py` | Typed contract — archetypes, regions, languages, platforms, evidence, cost. |
| `llm.py` | Thin async OpenAI-compatible HTTP client (no vendor lock). |
| `graph.py` | Two-pass GraphRAG: entity extraction → relation extraction. |
| `personas.py` | India-tuned persona generator: archetype / region / language / platform priors. |
| `engine.py` | Round-based sim loop. Platform routing + USD budget enforcement. |
| `report.py` | Per-archetype + per-platform stats, evidence aggregation, ReportAgent render. |
| `runner.py` | End-to-end orchestrator: `SyntheticSociety.run_full()`. |
| `presets.py` | Domain presets with default platform mixes. |
| `seeds/*.py` | Real-world seed loaders (brand kit, policy brief, campus policy, fundraise pitch). |
| `server.py` | FastAPI: `POST /runs`, `GET /runs/{id}`, `GET /presets`. |
| `cli.py` | Typer CLI: `synsoc run / presets / serve`. |

### Why hand-rolled, not autogen / langgraph?

We need fine-grained control over **(a)** language register per agent,
**(b)** platform routing (WhatsApp vs Twitter vs Reddit — different
reach & virality curves), **(c)** memory compression cadence
(intentionally lossy), and **(d)** operator-injected perturbations
mid-sim. Off-the-shelf agent frameworks push you toward tool-calling
chat loops; that surface area is exactly what we don't want here.

| Concern | autogen / langgraph | Synthetic Society |
|---|---|---|
| Language register per agent | chat message | first-class field |
| Platform routing | none | weighted priors + reach/virality curves |
| Memory compression | managed by framework | explicit per-archetype cadence |
| Mid-sim perturbations | re-prompt | structured `--timeline` + free-text `--god` |
| Cost cap | none | hard USD halt |

---

## 🎯 Domains (first-class seed loaders)

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

---

## 🌩️ God events & timeline

Two ways to inject perturbations mid-simulation:

```bash
# Legacy: free-text drops, one per round (1-indexed)
synsoc run consumer --god "RBI announces 28% GST on premium cards" \
                   --god "Viral tweet from @RandomHater about the campaign"

# Structured: scheduled drops with source + platform
synsoc run political \
  --timeline "2|rbi_hike|Repo rate +25bps|RBI circular|twitter_x" \
  --timeline "4|viral_tweet|@opposition_leader calls it anti-farmer|@opposition_leader|twitter_x"
```

`--god` and `--timeline` can be combined.

---

## ⚙️ Configuration knobs

### CLI

```bash
synsoc run consumer \
  --pop 80 --rounds 12 \
  --platform twitter_x=3 --platform instagram=2 --platform reddit_india=1 \
  --watch gig_worker --watch nri_diaspora \
  --budget 1.50
```

| Knob | What |
|---|---|
| `--platform k=v` | Per-platform weight. Multi-platform sims cost more tokens but read like the real Indian discourse. |
| `--watch ARCH` | Drill into specific archetypes in the report. |
| `--budget USD` | Hard cap on LLM spend. Sim halts when exceeded. |
| `--timeline` | Scheduled drops with source + platform attribution. |
| `--god` | Legacy free-text drops. |

### Server (FastAPI)

| Knob | What |
|---|---|
| `region_mix` | Pin state-level population priors (UP-heavy, Tamil Nadu-only, etc.). |
| `stance_target` | Bias the initial opinion distribution (`pro`/`anti`/`neutral`/`undecided`). |
| `cost_budget_usd` | Same as `--budget`. |

### Env vars

| Env var | Default | What |
|---|---|---|
| `LLM_API_KEY` | *(required)* | OpenAI-compatible key |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | Any OpenAI-compat endpoint |
| `LLM_MODEL_NAME` | `gpt-4o-mini` | Model id |
| `LLM_TEMP_EXTRACT` | `0.0` | Lower for graph extraction |
| `LLM_TEMP_AGENT` | `0.7` | Higher for persona voices |
| `LLM_TEMP_REPORT` | `0.3` | Lower for the rendered report |
| `MAX_AGENTS_PER_SIM` | `200` | Cap on persona count |
| `MAX_ROUNDS` | `20` | Cap on round count |
| `PARALLEL_AGENTS` | `8` | Concurrency for the loop |
| `DATABASE_URL` | SQLite | Swap to Postgres for >500-agent sims |

---

## 🧪 Tests

```bash
pytest tests/
# or with coverage
pytest --cov=synthetic_society tests/
```

Smoke tests cover the schema, the runner, and the four seed loaders.
Integration tests stub the LLM client so they run hermetically.

---

## ⚠️ Limits & honesty

A short list of things we won't pretend:

- **The simulation is a synthetic sketch, not ground truth.** Use it to
  surface hypotheses, not to ship policy or replace user research.
- **One LLM call per agent per round.** 60 personas × 8 rounds ≈ 500 calls.
  Each call has cost + latency — budget accordingly.
- **Memory is intentionally lossy.** We keep the last 5 events verbatim
  and a rolling summary. Do not treat the transcript as ground truth.
- **No framework, no vendor lock.** Drop in any OpenAI-compatible LLM —
  quality varies wildly between models. `gpt-4o-mini` and `Qwen2.5-72B`
  give the best persona voice in our tests.
- **MIT No Attribution.** Use it, ship it, don't credit back. See
  [LICENSE](LICENSE).

---

## 🗺️ Roadmap

- [x] v0.1 — Domain presets, CLI, FastAPI, GraphRAG, USD budget cap
- [ ] v0.2 — Calibrated priors from NSSO + Lokniti-CSDS + IAMAI (pull requests welcome)
- [ ] v0.3 — Persona memory export → fine-tuning dataset
- [ ] v0.4 — Real Twitter/Reddit ingestion as seed corpus
- [ ] v0.5 — Web UI for non-technical operators
- [ ] v1.0 — Validated against 3 published real-world discourse events

---

## 🤝 Contributing

PRs welcome — especially on:
- **Better priors.** Census/NSSO/IAMAI/Lokniti-CSDS data → persona
  weights. This is the moat.
- **New seed loaders.** Sector-specific (Fintech, Edtech, FMCG, D2C).
- **Model evaluations.** Persona-voice quality across providers.
- **Validation studies.** Run a sim, then run the real discourse, compare.

Open an issue first for big changes. Run `ruff check .` and
`pytest tests/` before pushing.

---

## 🙏 Credits & inspiration

This project exists because two teams proved the pattern works:

- **[666ghj/MiroFish](https://github.com/666ghj/MiroFish)** — the
  original multi-agent social-simulation demo (Shanda Group). The
  seed → graph → sim → report pipeline shape is theirs.
- **[CAMEL-AI OASIS](https://github.com/camel-ai/oasis)** — the
  open-source simulation engine MiroFish wraps. We learned a lot from
  reading their platform-routing design.

**All code in Synthetic Society is original.** We borrowed only the
high-level pattern, not any source.

Persona priors reference publicly available Indian-market data:
Lokniti-CSDS, IAMAI, NSSO, BARC India, and the Reuters Institute
Digital News Report (India chapter).

---

## 📄 License

[MIT No Attribution](LICENSE) — use it, ship it, don't credit back.

Built by [Baibhab Mishra](https://github.com/baibhab-m) · ⭐ if useful
