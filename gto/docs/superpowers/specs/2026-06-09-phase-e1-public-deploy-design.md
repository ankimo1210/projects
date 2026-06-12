# Phase E1 — Public Deploy + Auth + Rate Limiting — Design

Date: 2026-06-09 (rev 2: 2026-06-12 — gating tables revised post-M1/M2)
Status: approved (brainstorm with user, gating model A)

## Rev 2 — post-M1/M2 gating revision (supersedes §2's table)

M1 made GameSpec `POST /api/solve` the API contract and M2 migrated /solver
and /simulation onto it; the gating input is now the **cost class** from
`GET /api/solve/capabilities`:

| Tier | Surface | Cost class | Public deploy |
|---|---|---|---|
| Public, no auth | `/api/library/*` (instant-preview tier, `equilibrium_claim=false`), `/api/trainer/*`, static `/solutions/*`, frontend | static | open |
| Auth + rate limit | `/api/equity`; `POST /api/solve` river (sync ~1s) and turn_river (sync-capped ~37s); legacy `/api/hu/*` (deprecated alias) | CPU seconds | login required |
| Disabled (503) | `POST /api/solve` flop (async tier — 10.5 GB / ~49 min, local-only), `/api/solve/jobs/*`, `/api/solver/solve` 3-card preview (needs gto_cuda GPU), `/api/simulation/run` 3-card branch | GPU / heavy RAM | 503 `local-only` |

Notes:
- `/api/solver/solve` and `/api/simulation/run` 4/5-card paths run gto-hu on
  CPU since M2 — they move from "disabled" (old table) to **gated** (same
  budget as `/api/solve` turn_river). Their 3-card (gto-cuda) branches stay
  disabled in public deploy.
- turn+river at ~37 s vs proxy timeouts: Fly/Cloud Run default timeouts are
  60 s+ — acceptable, but the iteration clamp must keep worst-case under
  ~50 s (`ITER_CLAMP` already does at 30k).
- The flop async job tier is NOT exposed publicly in E1 even behind auth
  (one job pins ~12 GB for ~50 min — trivially DoS-able on a free-tier box).
  Revisit in E3 with queue limits + per-user quotas if wanted.
Project: `gto/` — first sub-project of Phase E (commercialization)
Parent: PROGRESS.md "Phase E: 商用化" (decomposed; billing dropped —
the near-term goal is **free public app + accounts**, not paid SaaS)

> Goal: make the GTO Poker Suite a **free, publicly reachable web app with
> user accounts**, serving only the CPU-light / precomputed features.
> Heavy GPU features stay local (CLI / dev box).

---

## 1. Phase E decomposition (context)

Phase E splits into sequenced sub-projects, each with its own
spec → plan → implementation cycle:

- **E1 (this doc)**: public deploy + Supabase auth + rate limiting.
  The foundation; on its own it delivers the "free public + accounts" core.
- **E2**: user history / persistence (saved solves, trainer progress;
  Postgres + RLS). Depends on E1.
- **E3**: operational hardening (monitoring, error tracking, CI deploy,
  cost watch). Depends on E1.

Billing/Stripe is **out of scope for all of Phase E** under the current
free-public goal; if a paid tier is ever added it becomes a new sub-project.

## 2. Goal & constraints

- **Goal**: anyone can reach the app on a custom domain; accounts gate the
  live CPU solvers and (later, E2) persist history.
- **Hard constraint — compute**: the live GPU solver (`gto-cuda`, RTX 5080)
  and `gto-core` multistreet are too heavy/expensive to host for a free
  public app. Only CPU-light + precomputed features are served publicly.
- **Solo dev, free tier**: minimize moving parts and cost. Single
  container, managed Supabase free tier, scale-to-zero-capable host.

### Feature classification (drives gating)

| Tier | Features | Backend cost |
|---|---|---|
| Public, no auth | library lookups (`/api/library/*`), trainer (`/api/trainer/*`), static `/solutions/*`, static frontend | static / trivial |
| Auth required | equity (`/api/equity`, CPU MC), river GTO (`/api/hu/river`, CPU ~1.6 s), turn+river (`/api/hu/turn-river`, CPU ~30-40 s) | CPU seconds — rate-limited |
| Disabled in public deploy (503) | live GPU solve (`/api/solver/solve`), simulation (`/api/simulation/run`) | needs RTX 5080 |

**Gating model A** (chosen): anonymous users browse the static library and
trainer (acquisition funnel); the live CPU solvers require login and are
per-user rate-limited.

## 3. Architecture

Single Docker container + external managed Supabase.

```
[Browser] ──Supabase JS (email magic link / Google OAuth)──▶ [Supabase Auth]
    │  every gated API call carries Authorization: Bearer <supabase JWT>
    ▼
┌─ 1 container ───────────────────────────────────────────────┐
│ FastAPI (uvicorn)                                            │
│   GET  /              → Next.js static export (output:export)│
│   GET  /solutions/*   → precomputed library data (mounted)   │
│   *    /api/*          → public + gated routers              │
│        JWT verified server-side with the Supabase JWT secret │
└──────────────────────────────────────────────────────────────┘
        │ (DB only; E1 uses Supabase for AUTH only — see §7)
        ▼
   [Supabase] Auth (users, JWT) + Postgres (reserved for E2 history)
```

Why single container: the FastAPI backend already needs Docker (compiled
Rust `gto_py` wheel); the frontend is 100% client components, so a Next
static export can be served by the same FastAPI process. One image, one
domain, no CORS, one deploy. (Host choice — Fly.io / Cloud Run / Railway —
is deferred to the implementation plan; all three run one container with
scale-to-zero.)

## 4. Components (single-responsibility units)

1. **`src/gto/api/auth.py`** — FastAPI dependencies.
   - `require_user(authorization) -> UserId`: extract bearer token, verify
     Supabase JWT (HS256 against `SUPABASE_JWT_SECRET`, check `exp`, `aud`),
     return the `sub` (user id). Raise 401 on missing/invalid/expired.
   - `optional_user() -> UserId | None`: same but returns None instead of
     401 (for routes that vary by auth; not strictly needed in E1 but cheap).
   - Never trusts a client-supplied user id; the id always comes from the
     verified token.

2. **`src/gto/api/ratelimit.py`** — per-user fixed-window limiter.
   - In-memory `dict[user_id] -> (window_start, count)` for two windows
     (per-minute, per-day). Single container = single process, so in-memory
     is correct and sufficient; Postgres-persisted counters are deferred to
     multi-instance (YAGNI).
   - `check(user_id)` raises 429 with `Retry-After` when over a limit.
   - Limits are env-configurable; defaults: **30/min, 500/day**.
   - A FastAPI dependency `rate_limited_user = require_user + check`.

3. **`src/gto/api/config.py`** — env-driven settings (pydantic-settings or
   a small dataclass):
   - `PUBLIC_DEPLOY: bool` (default False) — when True, GPU routers 503 and
     CORS locks to `ALLOWED_ORIGINS`.
   - `SUPABASE_JWT_SECRET`, `SUPABASE_URL` (auth).
   - `ALLOWED_ORIGINS: list[str]` — locks CORS in public deploy (dev keeps `*`).
   - `RATE_PER_MIN`, `RATE_PER_DAY`.
   - All read from env; nothing secret committed.

4. **GPU-route gating** — `solver.py` and `simulation.py` gain a guard:
   when `PUBLIC_DEPLOY`, return 503 `{"detail":"GPU solve is local-only"}`.
   (Single source: a small `require_local()` dependency in `config.py`.)

5. **`web/lib/supabase.ts`** — Supabase browser client (URL + anon key from
   `NEXT_PUBLIC_*` env). Session helpers; `authHeader()` returns the bearer
   header or `{}`.

6. **Auth UI** — a login/signup modal (email magic link + Google OAuth) and
   a header user-menu slot in `NeonShell` (login button when signed out,
   email + sign-out when signed in). Any gated call that returns 401 opens
   the modal; which pages call which gated endpoint is enumerated in the
   plan (at minimum `/hu` → `/api/hu/*`; equity callers audited then).

7. **API client wiring** — existing `web/lib/*-api.ts` clients attach
   `authHeader()` to gated calls (`hu-api`, equity). On 401 they throw a
   typed `AuthRequiredError` the pages catch to open the login modal.

8. **GPU nav treatment** — when `NEXT_PUBLIC_DEPLOY` is set, SOLVER /
   SIMULATE nav items get a "LOCAL" badge and their pages show a notice
   ("This feature needs the local GPU build") instead of calling the 503.

9. **`Dockerfile`** (multi-stage):
   - stage 1: rust + maturin → build `gto_py` wheel (CPU; `gto_cuda` NOT
     needed in the public image — GPU routes are disabled).
   - stage 2: node → `next build` with `output: 'export'` → static `out/`.
   - stage 3: slim python → install deps + `gto_py` wheel, copy static
     `out/` + `_data/gto/solutions` cache, run uvicorn. `PUBLIC_DEPLOY=1`.

## 5. Data flow

- **Anonymous**: load static frontend → browse library/trainer via public
  API + static `/solutions`. No token, no limit.
- **Login**: Supabase JS handles magic-link/OAuth entirely client-side; JWT
  lives in the browser session; header shows the user.
- **Gated solve**: client attaches `Authorization: Bearer <jwt>` →
  `rate_limited_user` verifies token + checks limit → router runs the CPU
  solve → response. 401 (no/invalid token) → frontend opens login modal;
  429 (over limit) → frontend shows "rate limit, retry in Ns".

## 6. Error handling & security

- **CORS**: `*` in dev; locked to `ALLOWED_ORIGINS` when `PUBLIC_DEPLOY`.
- **JWT**: verify signature (HS256, Supabase project secret) + `exp` + `aud`;
  reject otherwise with 401. User id only from `sub`.
- **GPU isolation**: GPU routers 503 in public deploy — the local-only GPU
  path is never exposed even by direct API call.
- **Rate limit**: 429 + `Retry-After`; per-user. Existing Pydantic
  validation and iteration caps (river ≤ 50k, turn+river ≤ 30k) stay.
- **Secrets**: Supabase keys via env only. The anon key is public by design
  (RLS-guarded); the JWT secret and service key are server-only, never in
  the image layers as plaintext (passed at runtime).
- **No PII** beyond Supabase-managed auth; no billing data.

## 7. Data model (E1 minimal)

E1 stores **no application data** — Supabase is used for AUTH only.
The rate limiter is in-memory. The Postgres instance exists (it ships with
Supabase) but E1 creates no tables; E2 adds the history schema with RLS.
This keeps E1 a clean auth+deploy slice.

## 8. Testing

- **Auth unit** (`tests/test_auth.py`): sign test JWTs with a known secret;
  assert valid → user id, expired/missing/tampered/wrong-aud → 401.
- **Gated endpoints** (extend `tests/test_hu_api.py`, new `test_equity_auth`):
  401 without token, 200 with a valid test token (override the secret via
  env in the test); confirm public routes (library/trainer/health) need no
  token.
- **Rate limiter** (`tests/test_ratelimit.py`): N calls pass, N+1 → 429;
  window reset restores; per-user isolation (user A's limit ≠ user B's).
- **Public-deploy flag**: with `PUBLIC_DEPLOY=1`, `/api/solver/solve` and
  `/api/simulation/run` → 503; gated CPU routes still work.
- **Container smoke** (manual / CI script, not unit): build image, run with
  test env, curl `/api/health`, static `/`, a gated route with a token.
- **Regression**: full existing pytest + cargo suites stay green; `next
  build` (export mode) succeeds.

## 9. Scope boundaries (YAGNI — explicit non-goals)

NOT in E1: billing/Stripe; history persistence (E2); multi-instance scaling
or distributed rate limiting; GPU hosting; job queue; monitoring/error
tracking (E3); admin panel; email templating beyond Supabase defaults.

## 10. Acceptance criteria

1. App builds to a single container; `docker run` serves frontend + API +
   library data on one port.
2. Anonymous users can browse library/trainer; live solvers return 401.
3. A logged-in user (Supabase magic link / Google) can run river/equity;
   over the limit returns 429.
4. `PUBLIC_DEPLOY=1` makes GPU routes 503 and locks CORS to the domain.
5. All new behavior has tests that fail without the change; full suite green.
6. Deployed to the chosen host on a custom domain (verified by visiting it).

## 11. Risks / notes

- **Next static export limits** (no SSR/ISR/`next/image` optimization,
  no middleware): acceptable — every page is already a client component
  fetching `/api`. Verify export builds during the plan.
- **Supabase JWT secret rotation**: documented runtime env, not baked in.
- **In-memory rate limit resets on container restart/scale**: acceptable at
  this scale; revisit if E3 introduces multiple instances.
- **`gto_cuda` excluded from the public image**: confirm no public code path
  imports it unconditionally (the solver/simulation routers import it
  lazily inside the handler — verify during implementation).
- **turn+river holds a worker ~30-40 s**: the existing `ThreadPoolExecutor`
  (2 workers) keeps the event loop free, but a handful of concurrent
  turn+river calls can saturate the pool and stall other gated solves.
  Per-user rate limits bound abuse; if it bites, add a stricter sub-limit
  for turn+river or a small queue (deferred — flag, don't pre-build).
  Equity and river (≤ ~2 s) are unaffected.
