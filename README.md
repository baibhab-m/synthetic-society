<div align="center">

# 🧬🤖 Synthetic Society

**Synthetic India, before you ship.**

A multi-agent research engine that stress-tests your launch, pricing,
positioning, or pitch against 60-2,000 personas tuned to Indian
platforms, languages, and price-sensitivities. Generates the kind of
objections and viral framings real India will throw at you, in roughly
the time it takes to make coffee.

</div>

<div align="center">

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue?style=flat-square)](https://www.python.org)
[![License: MIT-0](https://img.shields.io/badge/license-MIT--0-blue?style=flat-square)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000?style=flat-square)](https://docs.astral.sh/ruff/)
[![Docker](https://img.shields.io/badge/docker-ready-2496ed?style=flat-square&logo=docker&logoColor=white)](docker-compose.yml)
[![Stars](https://img.shields.io/github/stars/baibhab-m/synthetic-society?style=flat-square)](https://github.com/baibhab-m/synthetic-society/stargazers)

**Built by [Baibhab Mishra](https://github.com/baibhab-m)**
</div>

---

> **Don't want to run a CLI?** Hosted version with web UI, Slack alerts,
> and one-click sims is coming in v0.5.
> [Join the waitlist](https://forms.gle/your-waitlist-link) to skip the
> `pip install`.

---

## What this is, in one breath

Spin up a synthetic India. Watch it argue about your idea. Get a verdict,
the top objections, the archetypes that will drive virality, and the
real entities (RBI circulars, brands, subreddits) that the discourse
will collide with.

It is **not** a survey panel. It is **not** social listening. It is a
30-minute pre-screen that tells you which of your 8 hypotheses is worth
a 4-week user-research study.

---

## Where this fits in your PM week

| Phase | Question it answers | Wall time | LLM cost |
|---|---|---|---|
| **Pre-PRD** | Is my ICP hypothesis real across 17 archetypes and 31 states? | ~8 min | ~$0.20 |
| **Pre-launch** | Which of 3 positioning variants wins, and what kills each? | ~12 min | ~$0.50 |
| **Pre-Tier-2 expansion** | What does UP/TN/NE actually do when they see the page? | ~15 min | ~$0.80 |
| **Post-incident** | What will the counter-narrative to a competitor's move look like? | ~10 min | ~$0.40 |
| **Pre-mortem** | What goes wrong if we ship the worst-case scenario? | ~12 min | ~$0.50 |

Not a replacement for talking to real customers. A pre-screen that
tells you which 3 hypotheses to actually test on humans.

---

## 📺 What the output looks like

Run `synsoc run product --pop 80 --rounds 8` against this seed (a
fictional UPI consumer-credit launch in Tier-2 India):

```python
from synthetic_society.seeds import product
seed = product.launch(
    product="QuickRupee",
    one_liner="QuickRupee: ₹50,000 personal loan in 5 minutes, no collateral",
    pricing="₹50k-₹2L, 24-36% APR",
    claims=["RBI-registered NBFC partner", "CIBIL-checked disbursal",
            "100% UPI, no paperwork", "11-language support"],
    target_segments=["gig_worker", "salaried_metro", "tier2_hindi_speaker"],
)
```

...and you get a report that reads like this:

> ### Verdict: **polarised, trust-fragile, Tier-1-skewed**
>
> 71% of synthetic India reached a stance by round 5. Of those:
> - **38% conditional-positive**  -  "If RBI-registered and CIBIL-checked,
>   will try" (salaried-metro + value-seeker, mostly WhatsApp forwards)
> - **29% trust-skeptical**  -  "Apps like this sell my data / chase
>   recovery agents" (gig_worker + small-merchant on Reddit India;
>   cited 2 viral LoanShark-scare threads)
> - **21% price-sensitive**  -  "₹50k at 36% APR? Banks charge 14%"
>   (nri_diaspora + salaried-metro on Twitter X)
> - **12% undecided**  -  PrintOpEd + TVDebate voices asked for SEBI
>   clarification
>
> **Top objections (by frequency):**
> 1. "Recovery agent horror stories are everywhere."  -  *gig_worker*
> 2. "APR mein hidden charges honge hi."  -  *value-seeker*
> 3. "Why no FD-backed option like banks?"  -  *salaried-metro*
> 4. "Language mein terms-and-conditions padhne ka koi tareeka nahi."
>     -  *tier2_hindi_speaker*
>
> **Killer-objection signal:** the "recovery agent" objection
> surfaced in round 3 from `gig_worker`, amplified by
> `tier2_hindi_speaker` on WhatsApp, and was the dominant negative
> frame by round 6. Recommendation: ship a "talk to a real human in
> your language" trust signal in onboarding before any feature work.
>
> **Top amplifiers (who drove virality):**
> - *tier2_hindi_speaker*: 3.8× engagement multiplier on WhatsApp
> - *salaried-metro* on Twitter X: cross-pollinated to /r/IndiaInvestments
> - *anonymous-confession-board*: invented a "QuickRupee deducted
>   ₹999 'processing fee' before approval" narrative that hit 1,200
>   synthetic upvotes by round 7
>
> **Evidence cited:** 19 unique entities (RBI digital lending
> guidelines, SEBI RIA list, CIBIL, KreditBee, MoneyView, LazyPay,
> /r/IndiaInvestments, /r/IndianPersonalFinance, WhatsApp
> recovery-agent forwarded messages).

*Actual numbers vary per run  -  this is a representative sample from a
representative run.*

> **Full sample report:** see [`runs/example_quickrupee.md`](runs/example_quickrupee.md)
> for the complete `.md` output (stance tables by archetype + platform,
> evidence rollup, cost & timing) from a real 60-persona, 8-round
> `$0.27, 9m 41s` run.

---

## What GTM teams use it for

Four concrete decisions where a 10-minute sim has saved a 4-week study:

### 1. Pricing change reaction forecast

> *"Before we lift our ₹99 plan to ₹149, which Indian customer segments
> will rage-quit on Twitter, and which will quietly stay?"*

Seed: current pricing + new pricing + 3 hypothesis segments. Sim returns
the *exact* archetype mix that will churn, the platform they'll churn
on, and the framing they'll use. Output: 12-min report, 1-page memo
to the founder.

### 2. New channel / geography expansion

> *"We're a UPI-first D2C brand considering Tier-2 / Tier-3 expansion.
> What happens to retention when our 11-language storefront lands in
> Patna, Lucknow, and Coimbatore?"*

Seed: brand kit + new geography + new language hypotheses. Sim returns
which regional archetype will adopt first, which language register
will get memed on ShareChat, and which trust signal will gate the
purchase. Output: 15-min report with a "ship it / wait / rework"
verdict per region.

### 3. Competitor counter-narrative pre-mortem

> *"Razorpay just launched a product that overlaps with ours. What will
> our buyers' counter-narrative actually look like?"*

Seed: competitor press release + your positioning. Inject a timeline
event at round 4 (`--timeline "4|competitor_launch|..."`). Sim returns
the dominant counter-frame, which archetype will amplify it, and which
of your current claims will get turned against you.

### 4. Churn recovery framing

> *"Our NPS dropped 8 points after the new onboarding change. What
> does the exit-WhatsApp-forward actually say, and which cohort
> writes it?"*

Seed: changelog + the new onboarding flow + last quarter's top 3
complaint themes. Sim returns the killer-objection signal (with
archetype attribution), the platform it will surface on first, and a
proposed counter-message that survives round-by-round pushback.

---

## How this compares to what you already do

| | Customer interviews + Mixpanel/Intercom | UserTesting / Survey panel | Social listening (Sprinklr / Brand24) | **Synthetic Society** |
|---|---|---|---|---|
| Time to first insight | 1-2 weeks | 2-4 weeks | real-time, noisy | **~10 min** |
| Cost per question | eng-time + tools | $500-$5k | $200-$2k/mo SaaS | **$0.30-$1.50** |
| Tests "what would happen if" | no | no | no | **yes, mid-run perturbations** |
| India realism | depends on who you talk to | panel-dependent | English/Twitter-only | **17 archetypes × 13 langs × 15 platforms** |
| Synthetic but reproducible | no | no | no | **yes** |
| Surfaces the *killer* objection before launch | no | sometimes | rarely | **explicit signal in every report** |

**The honest framing:** Synthetic Society does not replace talking to
customers, your analytics stack, or your social-listening dashboard.
It sits *before* them, as a 30-minute hypothesis pre-screen. If the
sim says "the gig-worker archetype will reject this on WhatsApp by
round 4," you know which 5 user interviews to run and which Mixpanel
funnel to instrument. If it says "no archetype objects," you've saved
a 4-week study.

---

## Built for... / Not for...

**Use it for three jobs:**
- **Validate ICP**  -  run your buyer persona through your messaging
  and pricing before you spec.
- **Stress-test positioning**  -  see which of 3 taglines wins across
  17 Indian archetypes.
- **De-risk a launch**  -  pre-run a UPI / SaaS / D2C launch in Tier-2
  India and surface the killer objection before you spend on ads.

**Also useful for:** Series-A pitch rehearsals (LP-shaped personas),
policy brief stress-tests (opposition framings), campus ecosystem
foresight (student/faculty reactions to policy changes).

**Don't use it to:**
- **Ship policy.** This is a synthetic sketch, not ground truth.
- **Replace user research.** Use it to generate hypotheses worth
  testing on real humans.
- **Claim "X% of Indians will buy this."** It is not a survey. It is
  a directional signal with a known synthetic bias toward
  English-literate, urban-prior archetypes unless you rebalance via
  `region_mix`.
- **Forecast sales.** It models *discourse*, not purchase behaviour.

---

## ⚡ Install (60 seconds)

```bash
git clone https://github.com/baibhab-m/synthetic-society.git
cd synthetic-society
pip install -e .

synsoc --help
```

```bash
cp .env.example .env
# Add your LLM_API_KEY. Any OpenAI-compatible endpoint works:
# OpenAI, OpenRouter, Groq, Together, DashScope (Qwen), Sarvam,
# Mistral, a local llama.cpp server  -  anything.
```

> Requires **Python 3.11+**. Tested on macOS, Linux, WSL2.

**Zero-infra Docker mode:**

```bash
docker compose up
# API on :8765  -  POST /runs, GET /runs/{id}, GET /runs/{id}/report.md
```

---

## 🚀 Quick start

```bash
# 1. List the domain presets
synsoc presets

# 2. Run one (~$0.30, ~10 min with gpt-4o-mini)
synsoc run product --pop 60 --rounds 8

# 3. Or pass your own seed (PM/GTM scenario)
synsoc run product --seed-file my_pricing_change.md --question "Which segment churns first?"

# 4. Inject a mid-run event (RBI circular, viral tweet, competitor PR)
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
- `<timestamp>_<domain>_<name>.md`  -  board-ready report (paste into
  Notion, Confluence, PRD)
- `<timestamp>_<domain>_<name>.json`  -  full transcript: every persona,
  every round, every message, stance shifts

> **Roadmap integrations:** Linear/Jira (top objections -> tickets),
> Slack webhook for "rival launched" alerts, CSV export of
> stance-by-archetype for BI import.

### What to do with the report (5-min decision template)

1. **Copy the *Killer-objection signal* line** into your PRD / launch
   doc / Slack to your founder.
2. **Copy the *Top objections* list** into your onboarding copy or
   positioning page as the FAQ you didn't write yet.
3. **Take the *Top amplifiers* list** to your growth lead and ask
   which archetype to seed-launch to first.
4. **Take the *Evidence cited* set** and search each entity on Twitter
   X + Reddit India to confirm it's a real collision surface (not a
   hallucination).
5. **Take the verdict + 3 top objections** into the next weekly
   review. If leadership disagrees with the verdict, ask "which
   archetype are we betting against?"  -  that one question usually
   surfaces the real disagreement.

---

## 🧬 Architecture (3-file reading order)

| Read this | Why |
|---|---|
| 1. **`schema.py`** | Typed contract. 17 archetypes × 31 states × 13 languages × 15 platforms; cost budget, timeline events, evidence citations. |
| 2. **`runner.py`** | End-to-end orchestrator. `SyntheticSociety.run_full()`. The whole pipeline in one place. |
| 3. **`engine.py`** | Round-based loop. Routes each agent to their primary platform, enforces USD budget. |

> Full module map, env-var reference, and the "why not autogen/langgraph"
> comparison live in [`docs/architecture.md`](docs/architecture.md).

---

## 🎯 Domains

### 1. Product / GTM  *(primary use case)*

The most common PM/GTM seed: a concrete product decision with a
specific buyer, a specific change, and a specific fear.

```python
from synthetic_society.seeds import product

seed = product.pricing_change(
    product="Acme Pro",
    current_pricing="₹999/mo (₹8,499/yr)",
    proposed_pricing="₹1,499/mo (₹12,999/yr)",
    customer_segments={
        "salaried_metro": "SMB ops managers, 50+ seats",
        "gig_worker":     "Solo freelancers, 1 seat, pay-monthly",
        "nri_diaspora":   "Cross-border SaaS buyers, USD-card billing",
    },
    expected_churn_pct=12,
    hypothesis_to_test="Salaried_metro will absorb; gig_worker will churn on WhatsApp; NRI will compare to USD-tier pricing.",
)
```

Other product/GTM seed loaders:

```python
# Pre-launch positioning A/B/C
seed = product.positioning_variants(
    product="BharatTax",
    audience="salaried_metro + small_merchant",
    variants=[
        "India's simplest ITR filing",
        "File ITR in 7 minutes, in your language",
        "CA-backed ITR, starting ₹499",
    ],
)

# New channel / geography expansion
seed = product.geography_expansion(
    product="Acme Pro",
    current_geography=["Bengaluru", "Mumbai", "Delhi NCR"],
    target_geography=["Patna", "Lucknow", "Indore", "Coimbatore"],
    hypothesis="Tier-2 SMBs will adopt if onboarding is vernacular-first",
)

# Competitor counter-narrative
seed = product.competitor_move(
    your_product="Acme Pro",
    competitor="BetaPlus",
    competitor_action="BetaPlus launched a free tier undercutting us 30%",
    your_positioning="Premium, support-heavy, 99.9% SLA",
)
```

### 2. Consumer / brand reaction

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

### 3. Political / civic

```python
from synthetic_society.seeds import political

seed = political.policy_brief(
    title="DPDP Act, 2025  -  Rules notified",
    summary="Mandatory explicit consent, 72-hour breach disclosure, Data Protection Board with civil-court powers.",
    proponents=["MeitY", "NASSCOM"],
    opponents=["Internet Freedom Foundation", "SFLC.in"],
    affected_groups=["D2C startups", "gig workers", "hospitality", "healthcare"],
)
```

### 4. Campus / college ecosystem

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

---

## 🌩️ Mid-run perturbations

Two ways to inject events:

```bash
# Free-text drops, one per round (1-indexed)
synsoc run consumer --god "RBI announces 28% GST on premium cards" \
                   --god "Viral tweet from @RandomHater about the campaign"

# Structured: scheduled drops with source + platform attribution
synsoc run political \
  --timeline "2|rbi_hike|Repo rate +25bps|RBI circular|twitter_x" \
  --timeline "4|viral_tweet|@opposition_leader calls it anti-farmer|@opposition_leader|twitter_x"
```

`--god` and `--timeline` can be combined.

---

## ⚙️ Configuration

CLI flags and env vars documented in
[`docs/configuration.md`](docs/configuration.md). The TL;DR:

- `--platform k=v`  -  per-platform weight (multi-platform reads like
  real Indian discourse)
- `--watch ARCH`  -  drill into specific archetypes in the report
- `--budget USD`  -  hard cap; sim halts when exceeded
- `--timeline` / `--god`  -  mid-run perturbations
- `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL_NAME`  -  any
  OpenAI-compatible endpoint

Cost rule of thumb: **$0.30 for a 60-persona 8-round run, $1.50 for
an 80-persona 12-round multi-platform run.**

---

## 🧪 Tests

```bash
pytest tests/
```

Smoke tests cover the schema, the runner, and the four seed loaders.
Integration tests stub the LLM client so they run hermetically.

---

## ⚠️ Limits & honesty

- **The simulation is a synthetic sketch, not ground truth.** Use it to
  surface hypotheses, not to ship policy or replace user research.
- **One LLM call per agent per round.** 60 personas × 8 rounds = 500
  calls. Budget for cost and latency.
- **Memory is intentionally lossy.** Last 5 events verbatim + a rolling
  summary. Do not treat the transcript as ground truth.
- **No framework, no vendor lock.** Drop in any OpenAI-compatible LLM
   -  quality varies wildly. `gpt-4o-mini` and `Qwen2.5-72B` give the
  best persona voice in our tests.
- **Validation is in progress.** Roadmap target: validated against 3
  published real-world discourse events by v1.0. Until then, treat
  outputs as directional, not predictive.

### Validation methodology (in progress)

For each event we validate against, we run the sim *blind* (without
reading the real discourse), then compare:

| Dimension | What we compare |
|---|---|
| **Killer-objection signal** | Did the sim surface the actual objection that went viral? |
| **Archetype attribution** | Did the sim attribute it to the right Indian persona segment? |
| **Platform attribution** | Did the sim predict the platform (WhatsApp vs Twitter vs Reddit)? |
| **Counter-narrative shape** | Did the sim's counter-frame match the actual counter-frame? |
| **Sentiment distribution** | Did the positive/negative/skeptical split land within ±15%? |

Pilot events being validated: a public consumer-brand launch, a public
fintech policy response, and a public startup-fundraise backlash.
Methodology and full results published at v1.0.

---

## 🗺️ Roadmap

- [x] v0.1  -  Domain presets, CLI, FastAPI, GraphRAG, USD budget cap
- [ ] v0.2  -  Calibrated priors from NSSO + Lokniti-CSDS + IAMAI
  *(PMs: this is what unlocks the "as reliable as a 30-person panel"
  claim)*
- [ ] v0.3  -  Persona memory export → fine-tuning dataset
- [ ] v0.4  -  Real Twitter/Reddit ingestion as seed corpus
- [ ] v0.5  -  Hosted SaaS: web UI, Slack alerts, no CLI *(waitlist)*
- [ ] v1.0  -  Validated against 3 published real-world discourse events

---

## 🤝 Contributing

PRs welcome  -  especially on:
- **Better priors.** Census / NSSO / IAMAI / Lokniti-CSDS data →
  persona weights. This is the moat.
- **New seed loaders.** Sector-specific (Fintech, Edtech, FMCG, D2C).
- **Model evaluations.** Persona-voice quality across providers.
- **Validation studies.** Run a sim, then run the real discourse,
  compare.

Open an issue first for big changes. Run `ruff check .` and
`pytest tests/` before pushing.

---

## 🙏 Credits

This project exists because two teams proved the pattern works:
[666ghj/MiroFish](https://github.com/666ghj/MiroFish) (Shanda Group)
and [CAMEL-AI OASIS](https://github.com/camel-ai/oasis). All code in
Synthetic Society is original; we borrowed only the high-level
pattern (seed → graph → sim → report), not any source.

Persona priors reference publicly available Indian-market data:
Lokniti-CSDS, IAMAI, NSSO, BARC India, and the Reuters Institute
Digital News Report (India chapter).

---

## 📄 License

[MIT No Attribution](LICENSE)  -  use it, ship it, don't credit back.

Built by [Baibhab Mishra](https://github.com/baibhab-m) · ⭐ if useful
