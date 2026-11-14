# CrewCheck: build plan (NASA Space Apps 2026)

## Context
The project folder `/Users/roma/Desktop/crew-health-monitor` is empty: no git yet, and Python 3.14.10 is installed. We are building CrewCheck in about 28 hours. It is an offline-first daily crew self-check that compares each astronaut to their own pre-flight baseline. It shows GREEN/AMBER/RED per health domain with a transparent "Why?", tells the astronaut what to do through action protocols stored as content files, and queues a summary for Earth behind a simulated comms delay. The goal is a working MVP with a 30-second demo story, and every number must be scientifically honest (sourced or marked ASSUMPTION).

## Key design decisions
- **Rules engine = pure Python functions** (`baseline.py`, `rules.py`) with no DB or FastAPI imports, so pytest can test them directly. This is the most important code.
- **Deviation logic**: z = (today − baseline_mean) / baseline_sd. Direction matters per metric: HR, RT and lapses are bad when high; HRV, sleep and SpO2 are bad when low. A metric fires AMBER when it is worse than z ≥ 2 for ≥ 3 consecutive days, and RED when it is worse than z ≥ 3 for ≥ 3 days, or immediately when it crosses an absolute safety limit (e.g. SpO2 floor). All cut-offs come from `thresholds.yaml`. The UI shows "flag needs 3 days in a row → fewer false alarms". The domain status is the worst status among its metrics.
- **Bone & Muscle**: a model estimate. Loss % = rate/month × (mission_day/30) × (1 − exercise adherence factor). The formula and source are shown on hover, with a MODEL-ESTIMATED badge.
- **Radiation**: cumulative dose = Σ daily background dose (from the mission profile) + SPE increments. It is compared with the career limit. An active SEP event → RED + shelter protocol.
- **Protocols**: YAML files in `backend/content/protocols/` (`{domain}_{status}.yaml`) with steps, re-test timing and escalation. The engine maps status to a protocol ID. Nothing is hardcoded in JS.
- **Comms delay**: real one-way delay per profile (ISS ≈ 0 s, Moon ≈ 1.3 s, Mars from a config value). A **demo time-acceleration factor** makes a Mars countdown visible in seconds. The UI always shows both the real delay and "accelerated ×N for demo".
- **SSE**: plain FastAPI `StreamingResponse` (`text/event-stream`), so no extra dependency is needed.
- **DONKI proxy**: `/api/space-weather` → fetch FLR + SEP using `NASA_API_KEY` (fallback `DEMO_KEY`) → write `backend/cache/donki.json`. If the network fails, it reads the cache, then the bundled `backend/scenarios/sample_donki.json`. The response says which source was used.
- **DB**: SQLite through SQLModel. It is seeded on startup (crew, 14-day baselines, history), so Render's temporary disk is fine.
- **Frontend**: vanilla ES modules with no build step. `api.js` wraps every fetch and, on failure, falls back to `frontend/demo-data/*.json` and shows a "FALLBACK DEMO MODE" banner. A permanent "SIMULATED DATA" badge sits in the header. Every metric carries a provenance badge: MEASURED / SELF-REPORTED / LAB-ENTERED / MODEL-ESTIMATED.
- **PVT**: client-side `performance.now()` timing, random 2–10 s intervals, lapse > 500 ms, false starts counted, 60 s demo / 180 s standard. Works with Space or a tap.

## Candidate thresholds (all go to thresholds.yaml; you verify)
Every value below starts as **status: ASSUMPTION + TODO** unless you confirm the source. I will put the best-known source title and URL next to each one so you can check it quickly:
- Career radiation limit 600 mSv effective (NASA-STD-3001 Vol 1 Rev B)
- Mars transit GCR ≈ 1.8 mSv/day (Zeitlin et al. 2013, MSL RAD, Science)
- ISS ≈ 0.5–0.8 mSv/day
- Bone loss ≈ 1–1.5 %/month weight-bearing sites (LeBlanc et al. 2000)
- PVT lapse 500 ms (Basner & Dinges 2011)
- Persistence 3 days, z cut-offs 2/3, SpO2 floor, BP limits, sleep target: ASSUMPTION (design choices)
- Comms delays: Moon 1.3 s; Mars 3–22 min (we pick one value, e.g. 12 min, as ASSUMPTION)
- The simulated data generator draws only from the ranges in this file.

## File tree
```
crew-health-monitor/
├── README.md  LICENSE  SOURCES.md  AI_USAGE.md  PLAN.md
├── .env.example  .gitignore  requirements.txt  render.yaml  .python-version
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, mounts /frontend, /api/health
│   │   ├── db.py  models.py   # SQLModel: CrewMember, Baseline, CheckIn, VitalSample, LabResult, ActionLog, DownlinkItem, MissionState
│   │   ├── config.py          # loads thresholds.yaml + protocols
│   │   ├── seed.py            # crew + 14-day baselines + history from documented ranges
│   │   ├── engine/
│   │   │   ├── baseline.py    # mean/SD, z-score, persistence counter
│   │   │   ├── rules.py       # per-domain status + reasons
│   │   │   ├── models_est.py  # bone-loss + radiation projections
│   │   │   └── protocols.py   # status → protocol lookup
│   │   ├── services/  donki.py  downlink.py  simulator.py (vitals SSE)
│   │   └── routers/   crew, checkins, vitals, assessment, protocols, actions, radiation, space_weather, downlink, scenario, mission
│   ├── config/thresholds.yaml  missions.yaml
│   ├── content/protocols/*.yaml
│   ├── scenarios/mars_day120.json  sample_donki.json
│   ├── cache/ (gitignored)
│   └── tests/ test_baseline.py  test_rules.py  test_models_est.py  test_protocols.py  test_api_smoke.py
└── frontend/
    ├── index.html
    ├── css/style.css          # dark mission-control theme, high contrast
    ├── js/ main.js api.js checkin.js pvt.js cards.js radiation.js downlink.js vitals.js
    ├── vendor/chart.umd.min.js  # downloaded once, served locally
    └── demo-data/ (fallback JSON)
```

## API (as suggested, plus)
`GET /api/health`, and the 11 endpoints from your brief. `GET /api/assessment/{id}` returns `{domain, status, meaning, triggers[{metric, value, z, days_persisting, provenance}], rule, source, protocol_id}`.

## Phases (each ends with: run it → browser check steps for you → tick PLAN.md → git commit; push from Phase 2 onward)
- **Phase 0**: `git init`, .gitignore, LICENSE (MIT), PLAN.md, venv, requirements (fastapi, uvicorn[standard], sqlmodel, pyyaml, httpx, pytest), `main.py` serving an empty UI shell + `/api/health`. You should see a dark page titled "CrewCheck", and `{"status":"ok"}` at /api/health.
- **Phase 1**: *First I ask you for the challenge Resources links.* Then thresholds.yaml, models, seed, baseline + rules + bone model, and pytest tests covering persistence (2 days → no flag, 3 → flag), direction, absolute limits, worst-of aggregation, and missing data. `pytest` should pass. Then I guide you through creating a public GitHub repo and pushing.
- **Phase 2**: check-in wizard, PVT, status cards with "Why?" panels, provenance badges, live vitals via SSE + Chart.js.
- **Phase 3**: protocol YAMLs + action logging, radiation module + DONKI proxy/cache/fallback, mission profile selector, downlink queue with per-item include/exclude toggles + countdown.
- **Phase 4**: one-click "Mars transit day 120" scenario (poor sleep 3 nights + slower RT → Behavioral AMBER → protocol → SPE → Radiation RED → shelter → summary queued with countdown), frontend fallback mode, polish. *Polish gets cut first if we are behind.*
- **Phase 5**: README (Mermaid architecture), SOURCES.md, AI_USAGE.md, screenshots, Render deploy (`render.yaml`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT` from `backend/`, `PYTHON_VERSION=3.14`), final test run.

Risk note: if any dependency lacks a Python 3.14 wheel (unlikely with current pydantic/SQLModel), I'll tell you, and we fall back to 3.13 instead of fighting it.

## Verification
- `cd backend && ../.venv/bin/pytest -q` → all green (engine tests are never cut).
- `cd backend && uvicorn app.main:app --reload` → open http://localhost:8000. Load the scenario, then check that Behavioral turns AMBER with a "Why?" showing 3 days of z-scores, an SPE turns Radiation RED with the shelter protocol, and the downlink countdown runs.
- Stop the backend while the page is open and reload → the fallback demo banner appears and the demo still plays.
- Turn off Wi-Fi → `/api/space-weather` reports source "cache" or "bundled sample".

---
## Phase checklist
- [x] Phase 0: git, LICENSE, venv, FastAPI skeleton + UI shell, /api/health
- [x] Phase 1: thresholds.yaml, models, baseline engine, rules + pytest
- [x] Phase 2: check-in wizard, PVT, status cards, "Why?"
- [x] Phase 3: protocols, radiation + DONKI, downlink queue
- [x] Phase 4: demo scenario, fallback mode, polish
- [x] Phase 5: docs, screenshots, render.yaml (deploy itself needs your Render account)
