# Health: Fitbit Personal Dashboard — Design

**Date:** 2026-07-20
**Status:** Approved (design review passed; spec review pending)
**Project:** `/home/kazumasa/projects/health` (new uv workspace member)

## Goal

A personal Streamlit dashboard for daily monitoring of Fitbit data (sleep,
activity, heart, body metrics), synced on demand via an in-app button from the
Fitbit Web API. Daily summaries cover the full account history; intraday
(minute-level) data starts with the trailing 30 days and accumulates
incrementally. A data-inventory page enumerates every known endpoint so the
user can see what other data their account exposes.

## Decisions (from brainstorming)

| Topic | Decision |
|---|---|
| Usage | Continuously used dashboard (not a one-off report) |
| Data source | Fitbit Web API, personal app registered at dev.fitbit.com, OAuth2 |
| Data scope | Sleep, activity, heart (incl. intraday HR + HRV), body (weight, SpO2, skin temp, respiratory rate) + inventory of everything else |
| App form | New Streamlit app (`health`), Streamlit + Plotly + DuckDB, following the market-viz pattern |
| Sync trigger | In-app sync button (browser-only workflow) |
| History depth | Daily summaries: full history. Intraday: trailing 30 days at first sync, then incremental; fetched data is never pruned |
| Approach | Layered mini-package (core client/store/sync + thin Streamlit UI), hand-rolled thin API client (no python-fitbit dependency) |

## Architecture

```
health/
├── pyproject.toml        # package "health"; deps: streamlit, plotly, duckdb,
│                         # pandas, requests, python-dotenv
├── README.md / CLAUDE.md # run/sync/verify commands
├── .env.example          # FITBIT_CLIENT_ID / FITBIT_CLIENT_SECRET
├── src/health/
│   ├── auth.py           # OAuth2 authorization-code + PKCE; token persistence
│   │                     # and auto-refresh (rotating refresh tokens)
│   ├── client.py         # thin API client; rate-limit aware (429/Retry-After)
│   ├── endpoints.py      # metric catalog: endpoint defs, max date-range per
│   │                     # request, chunking rules
│   ├── store.py          # DuckDB store: raw JSON + typed tables + sync state
│   ├── sync.py           # backfill/incremental engine; interrupt & resume
│   └── inventory.py      # data discovery: which endpoints have data
├── app/
│   ├── main.py           # entry: auth status, navigation
│   └── views/            # sleep / activity / heart / body / inventory / sync
├── data/                 # gitignored: health.duckdb, tokens.json
└── tests/                # core tests with mocked HTTP; no live API
```

Registered as a uv workspace member in the root `pyproject.toml`. Known
pitfall: a member whose directory name equals its package name breaks under
root-level pytest 9 (namespace-package shadowing); if it bites, add the
one-line import fix to the root `conftest.py` (same treatment as gto/quantkit).

## Authentication (browser-only OAuth2)

- First run: the app shows a "Connect Fitbit" link → authorization URL for the
  personal app → redirect URI is the Streamlit app itself
  (`http://localhost:8501/`) → the app reads `?code=` from query params and
  exchanges it for tokens.
- Tokens persist to `data/tokens.json` (mode 600, gitignored). Access tokens
  expire after 8 h; refresh is automatic. Fitbit rotates refresh tokens, so
  the new pair is written back atomically on every refresh.
- If refresh fails, the UI prompts for re-authorization.
- Scopes: `activity heartrate sleep weight oxygen_saturation
  respiratory_rate temperature profile`.
- Prerequisite (user, ~5 min): register a personal app at dev.fitbit.com and
  put Client ID/Secret into `health/.env`.

## Data store (DuckDB, `data/health.duckdb`)

- **Raw layer:** `raw_json(endpoint, date_key, fetched_at, payload)` — every
  API response verbatim, so typed tables can be rebuilt without re-fetching.
- **Typed layer:** `daily_activity` (steps, distance, calories, active
  minutes), `sleep_sessions` (bed/wake times, stage minutes, score),
  `daily_heart` (resting HR, zone minutes), `body` (weight, body fat),
  `daily_spo2`, `daily_hrv`, `daily_temp`, `daily_br`, `intraday_hr`,
  `intraday_steps`.
- **Sync state:** `sync_state(metric, last_synced_date, status)` — the basis
  for resume and debugging.

## Sync engine

- Per metric: compute missing date ranges from `sync_state`, chunk by each
  endpoint's max range (e.g., steps 1095 d/request, heart 365 d/request,
  sleep via paginated list API), fetch, upsert raw + typed.
- Rate limit (150 requests/hour/user) is managed as a request budget: on
  exhaustion the engine stops cleanly, persists progress, and the UI shows
  when sync can resume.
- The trailing 3 days are always re-fetched (device sync lag changes recent
  data after the fact).
- The Streamlit sync button calls the engine in-process and renders
  per-metric progress.

## Dashboard UI (Streamlit + Plotly)

- **Overview:** today/this-week cards (steps, sleep duration, resting HR) with
  sparklines.
- **Sleep:** hypnogram-style stage chart, duration trend, bed/wake-time
  scatter, weekday pattern.
- **Activity:** steps/calories/active-minutes trends, exercise log, weekly
  heatmap.
- **Heart:** long-term resting-HR trend, HRV trend, per-day intraday HR
  viewer.
- **Body:** weight trend, SpO2 / skin temp / respiratory rate.
- **Inventory:** all known endpoints × has-data / date range / sample value —
  answers "what else is there?".
- **Sync:** sync button, per-metric status, token status.
- Chart implementation follows the dataviz skill (colors, marks, layout).

## Error handling

- 429 → honor `Retry-After`, stop cleanly, persist progress.
- 401 → auto-refresh; refresh failure → re-auth prompt.
- Device not yet synced → covered by the trailing-3-day re-fetch.

## Testing & acceptance

- Core-layer tests with mocked HTTP (token refresh incl. rotation, range
  chunking, store upserts, sync resume). No live API in tests; optional
  `HEALTH_LIVE=1` smoke test only.
- Acceptance: `uv run --no-sync pytest health/tests` green from repo root +
  first sync writes real data into tables + dashboard renders the user's own
  data.

## Out of scope

- Automatic scheduled sync (cron) — can be added later; the engine is already
  CLI-callable.
- Multi-user support, deployment, non-Fitbit data sources.
