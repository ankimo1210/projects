# johnhull Web App (W0–W2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serve the johnhull Book, the supplementary site (補足教材) and an in-browser binomial-tree calculator (Hull 11e GE Ch.13, computed by the unchanged hullkit under Pyodide) from a private Cloudflare Pages site behind Cloudflare Access, with every page that was opened once readable offline.

**Architecture:** Python build steps in `johnhull/web/py/hull_web_build` fetch the pinned Pyodide files with hash checks, pack the browser copy of hullkit (byte-identical `trees.py` and `bsm.py` plus one JSON entry point, `hull_web_calc.binomial.run`), generate the golden file and the example data from native CPython, and assemble `johnhull/web/dist/` from the Vite app shell, the existing Book and report builds, and Pyodide. The calculator page (React) sends request texts to a module Web Worker that runs `run(request_json) -> response_json` in Pyodide; Playwright compares the browser's answers with the golden file. A generated service worker keeps the app shell, Pyodide and every opened page for offline use. Deployment is `wrangler pages deploy`, only after a probe shows Access in front.

**Tech Stack:** Python 3.12 (shared venv; the build uses the standard library only), Pyodide 314.0.7 (Python 3.14.2, numpy 2.4.6, scipy 1.18.0), Vite 8.3.2, React 19.3.0, TypeScript 6.0.3, Node 26 built-in test runner, Playwright 1.56.0 with ms-playwright Chromium 1208, wrangler 4.147.0 (`pages dev`, `pages deploy`), pnpm 11.1.0 through npx.

**Spec:** `johnhull/docs/superpowers/specs/2026-10-18-hull-web-app-design.md` (approved by the owner on 2026-10-18). Read it before Task 1. Where this plan and the spec disagree, the spec wins; record a ruling.

## Global Constraints

- Scope: W0–W2 of the spec (§6). W3 and later (re-deploys after the guide merges, more calculators, the public-release decision) are separate plans.
- Start only after the reading-guide revision round is finished and the owner tells you to start (spec §8). Work in `/home/kazumasa/worktrees/hull-web` on branch `codex/hull-web`, never on the guide branch.
- Never run `uv sync` or `uv run` inside the worktree. Use `/home/kazumasa/projects/.venv/bin/python` with an explicit `PYTHONPATH`; the shared venv's own `hullkit` is the main checkout's copy. `make hull-web*` takes `HULL_WEB_PY=/home/kazumasa/projects/.venv/bin/python` in the worktree.
- Data outside Git lives under `/home/kazumasa/projects/_data/johnhull/hull-web/` (environment variable `HULL_WEB_DATA`), never inside the worktree: removing a worktree deletes its ignored files.
- Node is the v26 on the static PATH (`nvm` is not available). pnpm is always `npx --yes pnpm@11.1.0 … --ignore-scripts`, and `johnhull/web/.npmrc` sets `ignore-scripts=true`. wrangler is always `npx --yes wrangler@4.147.0` with `WRANGLER_SEND_METRICS=false`; `pages dev` also gets `--compatibility-date 2026-10-01`.
- Pins: Pyodide 314.0.7 from `https://cdn.jsdelivr.net/pyodide/v314.0.7/full/`, whose `pyodide-lock.json` has SHA-256 `5dc2fc119108bc148c7457dc86e7675b5c87e1cafd420b9c34c1eaef7b36c010`. npm versions are exact (no `^` or `~`), as in the `package.json` files below.
- Pyodide floors (spec §3.4): Python ≥ 3.12, numpy ≥ 2.0, scipy ≥ 1.13; the release is at least two weeks old when pinned.
- Do not change hullkit (`johnhull/hullkit/`), the Book's configuration, extensions and static files (the shared runtime), the section ledger, or the report builder (spec §3.3, §7). The browser package copies `trees.py` and `bsm.py` byte for byte; only its `hullkit/__init__.py` is generated, and it contains imports only.
- Pyodide and numpy load only on the calculator page, which calculates its default example as it opens (D-10); scipy loads only for the BSM comparison; reading pages never request `/pyodide/` (spec §3.4).
- The site contains no PDF, no `_sources/`, no `.buildinfo`, no file over 25 MiB and at most 20,000 files (spec §3.2, §5; the last two are Cloudflare Pages limits).
- Example checks use only number literals that appear in the pinned hullkit tests (spec §3.5: 「新しい値は作らない」).
- The browser-versus-native tolerance is the W0 measurement, not widened (spec §5: 「根拠のない余裕は足さない」).
- UI text is Japanese. Code, comments and commit messages are English. Documents for the owner (README, W0 report, ROADMAP) are Japanese.
- Every deploy needs the owner's approval for that deploy. The Cloudflare API token lives only in the shell of whoever deploys: never in the repo, a log, a commit message, a record file or memory. The owner's email address and Cloudflare account ID are not written to the repo either (the repo is public).
- Update `johnhull/ROADMAP.md` 「現在地」 and 「完了までの計画」 in the same commit as each stage start and finish (`johnhull/AGENTS.md`). Copy counts from command output; never count by hand.
- Stop points: after Task 5 (the W0 report) and after Task 12 (the branch is complete; Claude verifies it and the owner approves the merge). Task 13 runs from the main checkout together with the owner.
- Stage every commit with explicit paths (`git add <paths>`), never `git add -A` or `git add .`: other sessions share this repository.

## Review Focus

These input classes and failure modes follow from the spec but are easy to miss; each has a test in the task that owns the code.

1. **Numbers typed the way people type them** — full-width digits from a Japanese IME, surrounding spaces, `5%`, a decimal comma `0,05`, `1e2` as the number of steps: spaces and full-width digits are accepted; `5%`, `0,05` and `1e2` are refused with the field's message and nothing is sent to Python. Pinned in `src/calc/params.test.ts` (Task 6).
2. **A saved page opened offline under another spelling** — `x.html` versus `x`, `index.html` versus `/`, with or without `#anchor`: the same saved page opens. Pinned in `sw/sw.test.mjs` ("both spellings", "the calculator opens from the shell", Task 8) and `tests/offline.spec.ts` (Task 10).
3. **The Access session expires while the service worker is installed** — a navigation answered by a redirect to the Access login, or by a login page reached through a redirect: handed to the browser and never stored, so offline never shows a login page. Pinned in `sw/sw.test.mjs` ("redirects and foreign answers…", Task 8).
4. **A missing or deliberately left-out path** — a mistyped URL, `/book/_build/html/_sources/…`, `.buildinfo`: a real 404 with the site's 404 page, not the entry page with 200 (what Pages serves when `404.html` is missing). Pinned in `tests/routes.spec.ts` (Task 10) and `site.REQUIRED` (Task 9).
5. **A redeploy while pages are saved** — pages opened before the redeploy still open offline, and online every saved static file is fetched again once after the deploy, so no stale file is served. Pinned in `sw/sw.test.mjs` ("saved before a redeploy", "fetched again once", Task 8).

## Decisions this plan makes

The plan check (2026-10-19) ran every file below in a scratch copy of the repository: the Python suite at the end of each Python task with the repository's ruff and pytest settings, the TypeScript type check and unit tests at Tasks 6–8, the W0 measurement against `wrangler pages dev` with only the Task 1–5 files, and `make hull-web-check` with all files (21 browser checks, offline included). These findings shaped the plan:

- **D-1 `404.html` is required.** Without a top-level `404.html`, Pages treats the site as a single-page app and answers every unknown path with the entry page and status 200. With it, unknown paths, `_sources/` and `.buildinfo` get 404.
- **D-2 The Book's "download source" links are removed by design.** Each Book page links to its `_sources/…` file (31 links on main on 2026-10-19). Spec §3.2 leaves `_sources/` out, so the link check counts these as removed by design and fails only on other broken links.
- **D-3 Browser results are not always bitwise equal to native results.** In the plan check, 41 of the 42 golden cases returned identical text; the other differed by 1 ulp (`edge:convergence-arbitrage-gaps`, `$.prices[17]`). Of 300 random requests, 291 were identical and the largest difference was 20 ulps. The cause is probably the C math library inside Pyodide (not verified). W0 measures the tolerance and `tests/tolerance.json` records it.
- **D-4 Slow-phone timing runs Pyodide on the main thread.** Chromium's CPU throttling does not slow dedicated workers, so the W0 page has a `?main` mode. Plan check: 9.0 s to the first result at 390 px with 4× throttling, 2.0 s unthrottled.
- **D-5 Content Security Policy.** `script-src 'self' 'wasm-unsafe-eval'` runs Pyodide, numpy and scipy with no violations; `'unsafe-eval'` is not needed. A worker takes its policy from its own response, so `/assets/*` (where Vite puts the worker) carries the calculator's policy. The Book and the report get no CSP (they use inline scripts).
- **D-6 The report pages load MathJax from a CDN.** 33 of the report's pages load MathJax from `cdn.jsdelivr.net`; this comes from the report builder, which this plan does not change. The display check allows exactly that host on `/report/site/` pages; offline, math on those pages shows as TeX source. (Earlier notes said the report also loads Google Fonts: it does not, the reference is inside a CSS comment.) The owner decides whether to change the report builder separately.
- **D-7 Saved pages survive redeploys.** The service worker keeps Book and report pages in one cache, `pages`, across deploys (spec §1, condition 3: 「一度開いたページ…は、オフラインでも動く」). Each entry records the deploy that stored it; a static file stored under an older deploy is fetched again once when online. The app shell and Pyodide caches are versioned and replaced. The `pages` cache only grows; the README tells the owner how to clear it.
- **D-8 The access check takes the host name.** A `*.pages.dev` name that is already taken gets a suffix, so `access-check` and `make hull-web-deploy` take `HULL_WEB_HOST` (default `$(HULL_WEB_PROJECT).pages.dev`, project `hull-notes`).
- **D-9 W2 deploys from main.** The branch is verified by Claude and merged with the owner's approval after Task 12; Task 13 builds and deploys from the main checkout.
- **D-10 Opening the calculator loads Python.** Spec §3.4 and §3.6 load and store Pyodide and numpy when the calculator is opened, so the calculator computes the default example (Hull §13.10, 5 steps) as it opens; buttons stay disabled until Python is ready, and 「中止」 stops the load. scipy still waits for the BSM comparison.

## Calculator contract

`hull_web_calc.binomial.run(request_json: str) -> str` is the only interface between the page and Python. The browser and the native tests call the same function.

Request (a JSON object):

| Field | Values |
|---|---|
| `op` | `"price"`, `"convergence"` (CRR only; n = 1…100, 150, 200, 300, 400, 500), `"bsm"` (CRR and European only) |
| `tree` | `"crr"` (needs `sigma` > 0) or `"ud"` (needs `u` > 0, `d` > 0, `d` < `u`) |
| `asset` | `"stock"` (q = 0), `"index"` (q = dividend yield), `"currency"` (q = foreign rate r_f), `"futures"` (q = r, so a = 1) |
| `kind`, `american` | `"call"`/`"put"`, `true`/`false` |
| `S0`, `K`, `T` | finite numbers > 0 (`S0` is F0 for futures) |
| `r`, `q` | finite numbers (`q` is read only for index and currency) |
| `n` | integer 1…500 (a JSON float such as `2.0` is refused) |

Responses:

- price: `{"ok": true, "price": f, "params": {"dt", "u", "d", "a", "p", "q"}, "tree": null | {"stock", "option", "delta", "exercise"}}`; the tree (levels i = 0…n, node j = 0 on top, as in hullkit) is returned for n ≤ 6 only.
- convergence: `{"ok": true, "steps": [...], "prices": [f | null, ...]}`; `null` where 0 < p < 1 fails at that n.
- bsm: `{"ok": true, "bsm": f}`.
- errors (bad input never raises): `{"ok": false, "error": {"code": "input", "field": ..., "reason": ...}}` with reason `not_json`, `not_object`, `unknown`, `not_bool`, `not_int`, `range`, `not_number`, `not_finite`, `not_positive`, `not_below_u`, `degenerate`, `needs_crr` or `needs_european`; `{"code": "arbitrage", "a", "u", "d", "p"}`; `{"code": "nonfinite"}`.

## File Structure

| Path | Responsibility | Task |
|---|---|---|
| `johnhull/web/package.json`, `pnpm-lock.yaml`, `.npmrc`, `.gitignore` | exact npm pins; ignore rules | 1, 6 |
| `johnhull/web/pins.json`, `pyodide-lock.json` | Pyodide version and file hashes; the pinned lock | 1 |
| `johnhull/web/py/hull_web_build/paths.py` | every filesystem location, derived from the file's own location | 1 |
| `…/pyodide_fetch.py` | download Pyodide into `$HULL_WEB_DATA/pyodide/<version>/`, checking every SHA-256 | 1 |
| `…/cli.py`, `__main__.py` | `python -m hull_web_build <command>` | 1, 3, 4, 5, 9, 12 |
| `johnhull/web/py/hull_web_calc/binomial.py` | `run()`: validation, price, tree, convergence, BSM (runs in Pyodide) | 2 |
| `…/hull_web_build/package.py` | `build/hullkit_browser.zip`: hullkit modules byte for byte plus `hull_web_calc` | 3 |
| `…/examples.py`, `golden.py` | example buttons from pinned-test literals; `tests/golden.json`; the W0 sweep | 4 |
| `johnhull/web/tests/ulps.mts` | ulp distance and JSON comparison (W0 script and browser tests) | 5 |
| `…/hull_web_build/site.py` | copy and check the site contents; assemble the W0 site and `dist/` | 5, 9 |
| `johnhull/web/w0/`, `scripts/w0_measure.mjs` | W0 spike page and measurement (kept as the W0 record) | 5 |
| `johnhull/web/src/calc/*.ts` | protocol types, formatting, form parsing, example checks, messages, SVG geometry | 6 |
| `johnhull/web/src/calc/client.ts`, `worker.ts` | page side and worker side of the Pyodide calculator | 7 |
| `johnhull/web/sw/sw.template.js`, `sw.test.mjs` | service worker (the build fills in 4 placeholders) and its tests | 8 |
| `…/hull_web_build/links.py`, `icons.py` | in-site link check; generated app icons | 9 |
| root `Makefile`, root `pyproject.toml` | `hull-web`, `hull-web-check` (Task 9), `hull-web-deploy` (Task 12); `testpaths` (Task 1) | 1, 9, 12 |
| `johnhull/web/index.html`, `calc/binomial/index.html`, `src/*.ts`, `src/styles.css`, `src/calc/*.tsx`, `public/*`, `vite.config.ts` | entry page, calculator UI, static files, headers | 10 |
| `johnhull/web/playwright.config.ts`, `tests/*.spec.ts`, `tests/helpers.ts` | browser checks: calculation, routes and headers, display, offline | 10 |
| `johnhull/web/README.md` | how to build, check and deploy; the offline rules | 11 |
| `…/hull_web_build/access_check.py` | probe that Access answers before any content | 12 |
| `johnhull/docs/validation/hull-web/` | `w0.json`, `W0_REPORT.md`, `w1.json`, `w2.json` | 5, 11, 13 |

## Commands used in every task

Run everything from the worktree root. Set these once per shell (if your shell does not keep variables between commands, put the lines in front of each command):

```bash
cd /home/kazumasa/worktrees/hull-web
export HULL_WEB_DATA=/home/kazumasa/projects/_data/johnhull/hull-web
export CHROMIUM_BIN=/home/kazumasa/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome
PY=/home/kazumasa/projects/.venv/bin/python
PYT="env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=johnhull/web/py:johnhull/hullkit/src $PY"
PNPM="npx --yes pnpm@11.1.0 --dir johnhull/web"
```

- Python tests: `$PYT -m pytest johnhull/web/py/tests -q`
- Python lint: `$PY -m ruff check johnhull/web/py && $PY -m ruff format --check johnhull/web/py`
- Build steps: `$PYT -m hull_web_build <command>`
- From Task 6: `$PNPM run typecheck` and `$PNPM run test:unit`; from Task 10: `$PNPM run test:browser` (needs `CHROMIUM_BIN` and a built `dist/`).

---

### Task 1: Worktree, pins and the verified Pyodide download

**Files:**
- Create: `johnhull/web/.gitignore`, `johnhull/web/.npmrc`, `johnhull/web/package.json`, `johnhull/web/pnpm-lock.yaml` (written by pnpm), `johnhull/web/pins.json`, `johnhull/web/pyodide-lock.json` (downloaded)
- Create: `johnhull/web/py/hull_web_build/__init__.py`, `__main__.py`, `paths.py`, `pyodide_fetch.py`, `cli.py`
- Create: `johnhull/web/py/tests/conftest.py`, `johnhull/web/py/tests/test_pyodide_fetch.py`
- Modify: `pyproject.toml` (`[tool.pytest.ini_options] testpaths`), `johnhull/ROADMAP.md`

**Interfaces:**
- Produces: `hull_web_build.paths` constants (every later task uses them; see the file). Functions read `paths.X` at call time (`path or paths.X`), so tests can monkeypatch `paths`.
- Produces: `pyodide_fetch.IntegrityError`; `sha256(path: Path) -> str`; `load_pins(path=None) -> dict`; `load_lock(pins, path=None) -> dict` (raises `IntegrityError` unless the lock is the pinned one); `wheel_closure(lock, roots: list[str]) -> list[str]`; `expected_files(pins, lock) -> dict[str, str]` (file name → SHA-256 of everything served under `/pyodide/` except the lock); `fetch(pins, lock, cache_dir=None, opener=urllib.request.urlopen) -> Path` (returns `<cache>/<version>/`).
- Produces: `python -m hull_web_build fetch-pyodide`.

- [ ] **Step 1: Check the start condition and create the worktree**

Ask the owner whether the reading-guide revision round is finished (spec §8). Start only on a yes.

```bash
git -C /home/kazumasa/projects worktree add -b codex/hull-web /home/kazumasa/worktrees/hull-web main
mkdir -p /home/kazumasa/projects/_data/johnhull/hull-web
cd /home/kazumasa/worktrees/hull-web && git log --oneline -1
```

Expected: the worktree exists on branch `codex/hull-web` at main's HEAD.

- [ ] **Step 2: Write the npm scaffolding**

`johnhull/web/.gitignore`:

```text
node_modules/
build/
dist/
.wrangler/
test-results/
playwright-report/
```

`johnhull/web/.npmrc`:

```text
ignore-scripts=true
```

`johnhull/web/package.json` (W0 needs only the browser driver for the measurement script; Task 6 adds the app's packages):

```json
{
  "name": "hull-web",
  "private": true,
  "type": "module",
  "devDependencies": {
    "@playwright/test": "1.56.0"
  }
}
```

Run: `$PNPM install --ignore-scripts`
Expected: `+ @playwright/test 1.56.0`; `johnhull/web/pnpm-lock.yaml` is written; `git status --short johnhull/web` lists no `node_modules`.

- [ ] **Step 3: Pin Pyodide**

`johnhull/web/pins.json`:

```json
{
  "pyodide": {
    "version": "314.0.7",
    "base_url": "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/",
    "lock_sha256": "5dc2fc119108bc148c7457dc86e7675b5c87e1cafd420b9c34c1eaef7b36c010",
    "core": {
      "pyodide.mjs": "6f1d60f7bf529beb300f0f47983c921d3982363640ba20af0e38efdddbc66109",
      "pyodide.asm.mjs": "f7cdc8ece80678ceb712f8e65ebe6d3a83203a180c399865f49612a051693635",
      "pyodide.asm.wasm": "cc36e3cab04fdfc9a63ff13eb52eae2b911bf46c025cc7b281f394bd3de1d5e6",
      "python_stdlib.zip": "fa1957e5777068fc4f7437f96d860ae2fbe9c19732ba06c84e004ec16dd7dd7a"
    },
    "packages": ["numpy", "scipy"]
  },
  "tools": {
    "node": "26",
    "pnpm": "11.1.0",
    "wrangler": "4.147.0",
    "playwright": "1.56.0"
  }
}
```

Download the lock and check it:

```bash
curl -fsSL https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide-lock.json -o johnhull/web/pyodide-lock.json
sha256sum johnhull/web/pyodide-lock.json
```

Expected: `5dc2fc119108bc148c7457dc86e7675b5c87e1cafd420b9c34c1eaef7b36c010`. If the hash differs, stop and tell the owner: the published lock changed and the pin must be decided again. The other hashes in `pins.json` come from the same release; `fetch` checks them in Step 8.

- [ ] **Step 4: Write the failing tests**

`johnhull/web/py/tests/conftest.py`:

```python
"""Make the web build packages importable when pytest collects this tree.

`johnhull/web/py` is not a uv workspace member, so its directory goes on sys.path
here, the same way johnhull/report/tests/conftest.py handles report_builder.
"""

import sys
from pathlib import Path

PY_DIR = Path(__file__).resolve().parents[1]
if str(PY_DIR) not in sys.path:
    sys.path.insert(0, str(PY_DIR))
```

`johnhull/web/py/tests/test_pyodide_fetch.py`:

```python
import hashlib
import io

import pytest
from hull_web_build import paths, pyodide_fetch


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fake_dist():
    blobs = {"pyodide.mjs": b"core", "a-1.0.whl": b"wheel a", "b-2.0.whl": b"wheel b"}
    pins = {
        "pyodide": {
            "version": "0.0.1",
            "base_url": "https://example.invalid/full/",
            "core": {"pyodide.mjs": _digest(blobs["pyodide.mjs"])},
            "packages": ["a"],
        }
    }
    lock = {
        "packages": {
            "a": {
                "file_name": "a-1.0.whl",
                "sha256": _digest(blobs["a-1.0.whl"]),
                "depends": ["b"],
            },
            "b": {"file_name": "b-2.0.whl", "sha256": _digest(blobs["b-2.0.whl"]), "depends": []},
            "c": {"file_name": "c-3.0.whl", "sha256": "0" * 64, "depends": []},
        }
    }
    return blobs, pins, lock


class _Opener:
    def __init__(self, blobs: dict[str, bytes], tamper: str | None = None):
        self.blobs, self.tamper, self.calls = blobs, tamper, []

    def __call__(self, url: str, timeout: float):
        name = url.rsplit("/", 1)[1]
        self.calls.append(name)
        data = self.blobs[name] + (b"!" if name == self.tamper else b"")
        return io.BytesIO(data)


def test_wheel_closure_follows_depends():
    _, _, lock = _fake_dist()
    assert pyodide_fetch.wheel_closure(lock, ["a"]) == ["a", "b"]


def test_wheel_closure_rejects_an_unknown_package():
    _, _, lock = _fake_dist()
    with pytest.raises(KeyError, match="zz"):
        pyodide_fetch.wheel_closure(lock, ["zz"])


def test_fetch_verifies_downloads_and_reuses_the_cache(tmp_path):
    blobs, pins, lock = _fake_dist()
    opener = _Opener(blobs)
    target = pyodide_fetch.fetch(pins, lock, tmp_path, opener)
    assert sorted(p.name for p in target.iterdir()) == ["a-1.0.whl", "b-2.0.whl", "pyodide.mjs"]
    assert sorted(opener.calls) == ["a-1.0.whl", "b-2.0.whl", "pyodide.mjs"]
    pyodide_fetch.fetch(pins, lock, tmp_path, opener)
    assert len(opener.calls) == 3  # second run downloads nothing


def test_fetch_rejects_a_tampered_download_and_leaves_no_file(tmp_path):
    blobs, pins, lock = _fake_dist()
    with pytest.raises(pyodide_fetch.IntegrityError, match=r"b-2\.0\.whl"):
        pyodide_fetch.fetch(pins, lock, tmp_path, _Opener(blobs, tamper="b-2.0.whl"))
    names = sorted(p.name for p in (tmp_path / "0.0.1").iterdir())
    assert "b-2.0.whl" not in names
    assert not any(name.endswith(".part") for name in names)


def test_committed_lock_is_the_pinned_one():
    pins = pyodide_fetch.load_pins()
    assert pyodide_fetch.sha256(paths.LOCK) == pins["pyodide"]["lock_sha256"]


def test_pinned_distribution_is_core_numpy_and_scipy():
    pins = pyodide_fetch.load_pins()
    files = pyodide_fetch.expected_files(pins, pyodide_fetch.load_lock(pins))
    assert sorted(files) == [
        "numpy-2.4.6-cp314-cp314-pyemscripten_2026_0_wasm32.whl",
        "pyodide.asm.mjs",
        "pyodide.asm.wasm",
        "pyodide.mjs",
        "python_stdlib.zip",
        "scipy-1.18.0-cp314-cp314-pyemscripten_2026_0_wasm32.whl",
    ]


def _version(text: str) -> tuple[int, int]:
    major, minor = text.split(".")[:2]
    return int(major), int(minor)


def test_pinned_versions_meet_the_spec_floors():
    # spec §3.4: Python >= 3.12, numpy >= 2.0, scipy >= 1.13
    lock = pyodide_fetch.load_lock(pyodide_fetch.load_pins())
    assert _version(lock["info"]["python"]) >= (3, 12)
    assert _version(lock["packages"]["numpy"]["version"]) >= (2, 0)
    assert _version(lock["packages"]["scipy"]["version"]) >= (1, 13)
```

- [ ] **Step 5: Run the tests to see them fail**

Run: `$PYT -m pytest johnhull/web/py/tests/test_pyodide_fetch.py -q`
Expected: collection error, `ModuleNotFoundError: No module named 'hull_web_build'`.

- [ ] **Step 6: Implement the package, the paths and the fetch step**

`johnhull/web/py/hull_web_build/__init__.py`:

```python
"""Build steps for the johnhull web app (spec: johnhull/docs/superpowers/specs/2026-10-18-hull-web-app-design.md)."""
```

`johnhull/web/py/hull_web_build/__main__.py`:

```python
from .cli import main

raise SystemExit(main())
```

`johnhull/web/py/hull_web_build/paths.py`:

```python
"""Filesystem locations used by the build steps, all derived from this file's location."""

from __future__ import annotations

import os
from pathlib import Path

WEB_DIR = Path(__file__).resolve().parents[2]
JOHNHULL_DIR = WEB_DIR.parent
HULLKIT_SRC = JOHNHULL_DIR / "hullkit" / "src" / "hullkit"
HULLKIT_TESTS = JOHNHULL_DIR / "hullkit" / "tests"
CALC_SRC = WEB_DIR / "py" / "hull_web_calc"
PINS = WEB_DIR / "pins.json"
LOCK = WEB_DIR / "pyodide-lock.json"
BUILD_DIR = WEB_DIR / "build"
APP_BUILD = BUILD_DIR / "app"
PACKAGE_ZIP = BUILD_DIR / "hullkit_browser.zip"
W0_PAGE = WEB_DIR / "w0"
W0_SITE = BUILD_DIR / "w0-site"
W0_SWEEP = BUILD_DIR / "w0-sweep.json"
DIST = WEB_DIR / "dist"
SW_TEMPLATE = WEB_DIR / "sw" / "sw.template.js"
EXAMPLES_JSON = WEB_DIR / "src" / "calc" / "examples.json"
GOLDEN_JSON = WEB_DIR / "tests" / "golden.json"
BOOK_HTML = JOHNHULL_DIR / "book" / "_build" / "html"
REPORT_SITE = JOHNHULL_DIR / "report" / "site"
GUIDE_TABLES = JOHNHULL_DIR / "docs" / "validation" / "reading-guide"
DATA_DIR = Path(os.environ.get("HULL_WEB_DATA", "/home/kazumasa/projects/_data/johnhull/hull-web"))
PYODIDE_CACHE = DATA_DIR / "pyodide"
```

`johnhull/web/py/hull_web_build/pyodide_fetch.py`:

```python
"""Fetch the pinned Pyodide distribution into a local cache, verifying every byte (spec §3.4)."""

from __future__ import annotations

import hashlib
import json
import shutil
import urllib.request
from collections.abc import Callable
from pathlib import Path

from . import paths

Opener = Callable[..., object]


class IntegrityError(RuntimeError):
    """A downloaded or cached file does not match its pinned SHA-256."""


def sha256(path: Path) -> str:
    """Hex SHA-256 of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_pins(path: Path | None = None) -> dict:
    """The committed pins (Pyodide version, file hashes, tool versions)."""
    return json.loads((path or paths.PINS).read_text(encoding="utf-8"))


def load_lock(pins: dict, path: Path | None = None) -> dict:
    """The committed pyodide-lock.json, after checking it is the pinned one."""
    path = path or paths.LOCK
    got = sha256(path)
    if got != pins["pyodide"]["lock_sha256"]:
        raise IntegrityError(f"{path}: expected sha256 {pins['pyodide']['lock_sha256']}, got {got}")
    return json.loads(path.read_text(encoding="utf-8"))


def wheel_closure(lock: dict, roots: list[str]) -> list[str]:
    """`roots` and every package they depend on in the lock, sorted by name."""
    packages = lock["packages"]
    seen: set[str] = set()
    stack = list(roots)
    while stack:
        name = stack.pop()
        if name in seen:
            continue
        if name not in packages:
            raise KeyError(f"{name} is not in pyodide-lock.json")
        seen.add(name)
        stack.extend(packages[name]["depends"])
    return sorted(seen)


def expected_files(pins: dict, lock: dict) -> dict[str, str]:
    """File name -> SHA-256 of everything served under /pyodide/ except the lock itself."""
    files = dict(pins["pyodide"]["core"])
    for name in wheel_closure(lock, pins["pyodide"]["packages"]):
        entry = lock["packages"][name]
        files[entry["file_name"]] = entry["sha256"]
    return files


def fetch(
    pins: dict,
    lock: dict,
    cache_dir: Path | None = None,
    opener: Opener = urllib.request.urlopen,
) -> Path:
    """Make `cache_dir/<version>/` hold the verified distribution and return that directory."""
    target = (cache_dir or paths.PYODIDE_CACHE) / pins["pyodide"]["version"]
    target.mkdir(parents=True, exist_ok=True)
    for name, digest in expected_files(pins, lock).items():
        _ensure(target / name, pins["pyodide"]["base_url"] + name, digest, opener)
    return target


def _ensure(path: Path, url: str, digest: str, opener: Opener) -> None:
    if path.exists() and sha256(path) == digest:
        return
    partial = path.with_name(path.name + ".part")
    with opener(url, timeout=300) as response, partial.open("wb") as out:
        shutil.copyfileobj(response, out)
    got = sha256(partial)
    if got != digest:
        partial.unlink()
        raise IntegrityError(f"{url}: expected sha256 {digest}, got {got}")
    partial.replace(path)
```

`johnhull/web/py/hull_web_build/cli.py`:

```python
"""Command line: python -m hull_web_build <command> (run from the repository root)."""

from __future__ import annotations

import argparse

from . import pyodide_fetch


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m hull_web_build")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("fetch-pyodide", help="download and verify the pinned Pyodide files")
    args = parser.parse_args(argv)

    if args.command == "fetch-pyodide":
        pins = pyodide_fetch.load_pins()
        print(pyodide_fetch.fetch(pins, pyodide_fetch.load_lock(pins)))
    return 0
```

- [ ] **Step 7: Run the tests to see them pass**

Run: `$PYT -m pytest johnhull/web/py/tests/test_pyodide_fetch.py -q`
Expected: `7 passed`.

- [ ] **Step 8: Download the pinned files**

Run: `$PYT -m hull_web_build fetch-pyodide && ls $HULL_WEB_DATA/pyodide/314.0.7`
Expected: the first line is `/home/kazumasa/projects/_data/johnhull/hull-web/pyodide/314.0.7`, followed by six files: `numpy-2.4.6-cp314-cp314-pyemscripten_2026_0_wasm32.whl`, `pyodide.asm.mjs`, `pyodide.asm.wasm`, `pyodide.mjs`, `python_stdlib.zip`, `scipy-1.18.0-cp314-cp314-pyemscripten_2026_0_wasm32.whl`. A second run downloads nothing.

- [ ] **Step 9: Register the tests with `make test`**

In the root `pyproject.toml`, `[tool.pytest.ini_options] testpaths`, add one line after `"johnhull/report/tests",`:

```toml
    "johnhull/report/tests",
    "johnhull/web/py/tests",
```

Run: `$PY -m pytest --collect-only -q 2>/dev/null | grep -c '^johnhull/web/py/tests/'`
Expected: `7` (a full collection, so this proves the `testpaths` entry; it takes a minute).

- [ ] **Step 10: Record the start of W0 in the ROADMAP**

`johnhull/ROADMAP.md` has two web-app lines: in 「現在地」 the line that starts with `ウェブアプリ（2026-10-18 設計、`, and in 「完了までの計画」 the line that starts with `ウェブアプリ（2026-10-18 設計）：`. The **status** is the text of the first line between `ウェブアプリ（` and the first `）：`. Set the status to

```text
2026-10-18 設計、ユーザー承認。2026-10-19 実装計画。W0 作業中、branch `codex/hull-web`
```

and in the 「完了までの計画」 line that starts with `ウェブアプリ（2026-10-18 設計）：`, replace `W0 試作と実測（タスク1〜5）` with `W0 試作と実測（タスク1〜5、着手 DATE）`. Here and below, DATE is the day you make the change (for example `2026-10-25`), and earlier dates stay as they are.

- [ ] **Step 11: Lint and commit**

Run: `$PY -m ruff check johnhull/web/py && $PY -m ruff format --check johnhull/web/py`
Expected: `All checks passed!` and `7 files already formatted`.

```bash
git add johnhull/web/.gitignore johnhull/web/.npmrc johnhull/web/package.json johnhull/web/pnpm-lock.yaml \
  johnhull/web/pins.json johnhull/web/pyodide-lock.json johnhull/web/py pyproject.toml johnhull/ROADMAP.md
git commit -m "Pin Pyodide 314.0.7 and fetch it with hash checks (hull web W0)"
```

---

### Task 2: The calculator's entry point, `hull_web_calc.binomial.run`

**Files:**
- Create: `johnhull/web/py/hull_web_calc/__init__.py`, `johnhull/web/py/hull_web_calc/binomial.py`
- Test: `johnhull/web/py/tests/test_binomial.py`

**Interfaces:**
- Consumes (hullkit, unchanged): `trees.crr_params(sigma, dt) -> (u, d)`; `trees.risk_neutral_p(u, d, r, dt, q=0.0) -> p` (raises `ValueError` unless 0 < p < 1); `trees.binomial_tree(S0, K, r, T, N, u, d, q=0.0, kind="call", american=False) -> (stock, option)` (lists of numpy arrays; level i has i+1 nodes, j = 0 on top); `trees.crr_price(S0, K, r, sigma, T, N, q=0.0, kind="call", american=False) -> float`; `trees.tree_delta(stock, option) -> float` (uses levels 0 and 1); `bsm.call_price` / `bsm.put_price(S, K, r, sigma, T, q=0.0)`.
- Produces: `run(request_json: str) -> str` (the contract above); `MAX_STEPS = 500`, `TREE_MAX_STEPS = 6`, `CONVERGENCE_STEPS`.

- [ ] **Step 1: Write the failing tests**

`johnhull/web/py/tests/test_binomial.py`:

```python
import json

import pytest
from hull_web_calc.binomial import CONVERGENCE_STEPS, run
from hullkit import bsm, trees

S13_10 = {
    "op": "price",
    "tree": "crr",
    "asset": "stock",
    "kind": "put",
    "american": True,
    "S0": 50.0,
    "K": 52.0,
    "r": 0.05,
    "q": 0.0,
    "sigma": 0.3,
    "T": 2.0,
    "n": 2,
}
S13_3 = {
    "op": "price",
    "tree": "ud",
    "asset": "stock",
    "kind": "call",
    "american": False,
    "S0": 20.0,
    "K": 21.0,
    "r": 0.04,
    "q": 0.0,
    "u": 1.1,
    "d": 0.9,
    "T": 0.5,
    "n": 2,
}


def _call(request: dict) -> dict:
    return json.loads(run(json.dumps(request)))


def _strict(text: str) -> dict:
    def refuse(token: str) -> float:
        raise AssertionError(f"non-JSON constant {token}")

    return json.loads(text, parse_constant=refuse)


@pytest.mark.parametrize("american", [True, False])
@pytest.mark.parametrize("n", [2, 5, 500])
def test_price_is_bitwise_hullkit_crr_price(n, american):
    out = _call({**S13_10, "n": n, "american": american})
    assert out["price"] == trees.crr_price(
        50.0, 52.0, 0.05, 0.3, 2.0, n, kind="put", american=american
    )


def test_ud_tree_returns_hullkit_nodes_and_tree_delta():
    out = _call(S13_3)
    stock, option = trees.binomial_tree(20.0, 21.0, 0.04, 0.5, 2, u=1.1, d=0.9)
    assert out["tree"]["stock"] == [[float(x) for x in level] for level in stock]
    assert out["tree"]["option"] == [[float(x) for x in level] for level in option]
    assert out["tree"]["delta"][0][0] == trees.tree_delta(stock, option)
    second = (option[2][0] - option[2][1]) / (stock[2][0] - stock[2][1])
    assert out["tree"]["delta"][1][0] == float(second)


def test_exercise_flags_mark_hull_fig_13_10_node_c():
    out = _call(S13_10)
    assert out["tree"]["exercise"] == [[False], [False, True]]


def test_european_trees_flag_no_exercise():
    out = _call({**S13_10, "american": False})
    assert out["tree"]["exercise"] == [[False], [False, False]]


def test_tree_is_returned_up_to_six_steps_only():
    assert len(_call({**S13_10, "n": 6})["tree"]["stock"]) == 7
    assert _call({**S13_10, "n": 7})["tree"] is None


@pytest.mark.parametrize(
    ("asset", "q_in", "q_used"),
    [("stock", 0.5, 0.0), ("index", 0.02, 0.02), ("currency", 0.07, 0.07), ("futures", 0.5, 0.05)],
)
def test_asset_type_sets_q(asset, q_in, q_used):
    out = _call({**S13_10, "asset": asset, "q": q_in})
    assert out["params"]["q"] == q_used


def test_futures_tree_has_a_equal_to_one():
    assert _call({**S13_10, "asset": "futures"})["params"]["a"] == 1.0


def test_ud_arbitrage_is_refused_with_p():
    out = _call({**S13_3, "u": 1.1, "d": 1.06, "r": 0.05, "T": 1.0, "n": 1})
    assert out["ok"] is False
    assert out["error"]["code"] == "arbitrage"
    assert out["error"]["p"] < 0


def test_crr_arbitrage_is_refused_with_p():
    out = _call({**S13_10, "sigma": 0.01, "T": 1.0, "n": 1})
    assert out["error"]["code"] == "arbitrage"
    assert out["error"]["p"] > 1


@pytest.mark.parametrize(
    ("change", "field", "reason"),
    [
        ({"n": 0}, "n", "range"),
        ({"n": 501}, "n", "range"),
        ({"n": 2.0}, "n", "not_int"),
        ({"n": True}, "n", "not_int"),
        ({"S0": 0.0}, "S0", "not_positive"),
        ({"K": -1.0}, "K", "not_positive"),
        ({"T": "1"}, "T", "not_number"),
        ({"r": None}, "r", "not_number"),
        ({"sigma": 0.0}, "sigma", "not_positive"),
        ({"sigma": 1e-300}, "sigma", "degenerate"),
        ({"asset": "bond"}, "asset", "unknown"),
        ({"kind": "straddle"}, "kind", "unknown"),
        ({"tree": ["crr"]}, "tree", "unknown"),
        ({"american": "yes"}, "american", "not_bool"),
        ({"op": "greeks"}, "op", "unknown"),
        ({"asset": "index", "q": None}, "q", "not_number"),
    ],
)
def test_bad_fields_are_named(change, field, reason):
    out = _call({**S13_10, **change})
    assert out == {"ok": False, "error": {"code": "input", "field": field, "reason": reason}}


def test_d_must_be_below_u():
    out = _call({**S13_3, "u": 0.9, "d": 1.1})
    assert out["error"] == {"code": "input", "field": "d", "reason": "not_below_u"}


@pytest.mark.parametrize("text", ["not json", "[1, 2]", '{"S0": NaN}'])
def test_malformed_requests_are_input_errors(text):
    assert _strict(run(text))["error"]["code"] == "input"


def test_nan_and_huge_numbers_are_rejected():
    assert _call({**S13_10, "S0": float("nan")})["error"]["reason"] == "not_finite"
    assert (
        json.loads(run(json.dumps(S13_10).replace('"S0": 50.0', '"S0": ' + "9" * 400)))["error"][
            "reason"
        ]
        == "not_finite"
    )


@pytest.mark.parametrize(
    "change",
    [
        {"sigma": 1000.0, "T": 1.0, "n": 1},
        {"tree": "ud", "u": 1.1, "d": 0.9, "S0": 1e300, "n": 500, "kind": "call"},
    ],
)
def test_overflow_is_reported_not_raised(change):
    assert _strict(run(json.dumps({**S13_10, **change})))["error"]["code"] == "nonfinite"


def test_convergence_marks_arbitrage_steps_as_null():
    out = _call({**S13_10, "op": "convergence", "sigma": 0.1, "r": 0.2, "T": 1.0, "kind": "call"})
    assert out["steps"] == list(CONVERGENCE_STEPS)
    # a >= u exactly when dt >= (sigma / r)^2 = 0.25, i.e. n <= 4
    assert out["prices"][:4] == [None] * 4
    assert all(isinstance(price, float) for price in out["prices"][4:])


def test_convergence_matches_crr_price_at_every_step():
    out = _call({**S13_10, "op": "convergence"})
    for n, price in zip(out["steps"], out["prices"], strict=True):
        assert price == trees.crr_price(50.0, 52.0, 0.05, 0.3, 2.0, n, kind="put", american=True)


def test_convergence_and_bsm_need_a_crr_tree():
    assert _call({**S13_3, "op": "convergence"})["error"] == {
        "code": "input",
        "field": "tree",
        "reason": "needs_crr",
    }
    assert _call({**S13_3, "op": "bsm"})["error"]["reason"] == "needs_crr"


def test_bsm_needs_a_european_contract():
    assert _call({**S13_10, "op": "bsm"})["error"] == {
        "code": "input",
        "field": "american",
        "reason": "needs_european",
    }


def test_bsm_is_hullkit_bsm_with_the_asset_q():
    out = _call({**S13_10, "op": "bsm", "american": False})
    assert out["bsm"] == float(bsm.put_price(50.0, 52.0, 0.05, 0.3, 2.0))
    index = {**S13_10, "op": "bsm", "american": False, "asset": "index", "q": 0.02, "kind": "call"}
    assert _call(index)["bsm"] == float(bsm.call_price(50.0, 52.0, 0.05, 0.3, 2.0, q=0.02))
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `$PYT -m pytest johnhull/web/py/tests/test_binomial.py -q`
Expected: collection error, `ModuleNotFoundError: No module named 'hull_web_calc'`.

- [ ] **Step 3: Implement `run`**

`johnhull/web/py/hull_web_calc/__init__.py`:

```python
"""Calculator glue that runs inside Pyodide next to the browser copy of hullkit."""
```

`johnhull/web/py/hull_web_calc/binomial.py`:

```python
"""JSON entry point of the browser binomial-tree calculator (Hull 11e GE, Ch.13).

The Web Worker calls `run(request_json)` and shows the JSON text it returns. The
native tests call the same function, so the golden file compares like with like:
the browser must return the same text as native CPython.
"""

from __future__ import annotations

import json
import math

import numpy as np
from hullkit import trees

MAX_STEPS = 500
TREE_MAX_STEPS = 6
CONVERGENCE_STEPS = (*range(1, 101), 150, 200, 300, 400, 500)
OPS = ("price", "convergence", "bsm")
TREES = ("crr", "ud")
ASSETS = ("stock", "index", "currency", "futures")
KINDS = ("call", "put")


class InputError(ValueError):
    """A request field is missing, has the wrong type, or is out of range."""

    def __init__(self, field: str, reason: str) -> None:
        super().__init__(f"{field}: {reason}")
        self.field = field
        self.reason = reason


class ArbitrageError(Exception):
    """0 < p < 1 fails, i.e. d < a < u does not hold (Hull eq. 13.18)."""

    def __init__(self, *, a: float, u: float, d: float, p: float) -> None:
        super().__init__(f"arbitrage: p={p}")
        self.details = {"a": a, "u": u, "d": d, "p": p}


def run(request_json: str) -> str:
    """Answer one calculator request with a JSON text; bad input never raises."""
    try:
        request = json.loads(request_json)
    except json.JSONDecodeError:
        return _error("input", field="request", reason="not_json")
    try:
        if not isinstance(request, dict):
            raise InputError("request", "not_object")
        op = request.get("op")
        if op not in OPS:
            raise InputError("op", "unknown")
        contract = _contract(request)
        with np.errstate(all="ignore"):
            if op == "price":
                body = _price(contract)
            elif op == "convergence":
                body = _convergence(contract)
            else:
                body = _bsm(contract)
    except InputError as exc:
        return _error("input", field=exc.field, reason=exc.reason)
    except ArbitrageError as exc:
        return _error("arbitrage", **exc.details)
    except OverflowError:
        return _error("nonfinite")
    try:
        return json.dumps({"ok": True, **body}, allow_nan=False)
    except ValueError:
        return _error("nonfinite")


def _error(code: str, **details: object) -> str:
    return json.dumps({"ok": False, "error": {"code": code, **details}}, allow_nan=False)


def _contract(request: dict) -> dict:
    tree = _choice(request, "tree", TREES)
    asset = _choice(request, "asset", ASSETS)
    kind = _choice(request, "kind", KINDS)
    american = request.get("american")
    if not isinstance(american, bool):
        raise InputError("american", "not_bool")
    n = request.get("n")
    if not isinstance(n, int) or isinstance(n, bool):
        raise InputError("n", "not_int")
    if not 1 <= n <= MAX_STEPS:
        raise InputError("n", "range")
    contract = {
        "tree": tree,
        "asset": asset,
        "kind": kind,
        "american": american,
        "n": n,
        "S0": _number(request, "S0", positive=True),
        "K": _number(request, "K", positive=True),
        "r": _number(request, "r"),
        "T": _number(request, "T", positive=True),
    }
    if asset == "stock":
        contract["q"] = 0.0
    elif asset == "futures":
        contract["q"] = contract["r"]
    else:
        contract["q"] = _number(request, "q")
    if tree == "crr":
        contract["sigma"] = _number(request, "sigma", positive=True)
    else:
        contract["u"] = _number(request, "u", positive=True)
        contract["d"] = _number(request, "d", positive=True)
        if not contract["d"] < contract["u"]:
            raise InputError("d", "not_below_u")
    return contract


def _choice(request: dict, field: str, allowed: tuple[str, ...]) -> str:
    value = request.get(field)
    if not isinstance(value, str) or value not in allowed:
        raise InputError(field, "unknown")
    return value


def _number(request: dict, field: str, *, positive: bool = False) -> float:
    value = request.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InputError(field, "not_number")
    try:
        value = float(value)
    except OverflowError:
        raise InputError(field, "not_finite") from None
    if not math.isfinite(value):
        raise InputError(field, "not_finite")
    if positive and not value > 0:
        raise InputError(field, "not_positive")
    return value


def _factors(contract: dict, dt: float) -> tuple[float, float]:
    if contract["tree"] == "ud":
        return contract["u"], contract["d"]
    u, d = trees.crr_params(contract["sigma"], dt)
    if not u > d:
        raise InputError("sigma", "degenerate")
    return u, d


def _probability(u: float, d: float, r: float, dt: float, q: float) -> tuple[float, float]:
    a = math.exp((r - q) * dt)
    try:
        p = trees.risk_neutral_p(u, d, r, dt, q)
    except ValueError:
        raise ArbitrageError(a=a, u=u, d=d, p=(a - d) / (u - d)) from None
    return a, p


def _price(contract: dict) -> dict:
    n = contract["n"]
    dt = contract["T"] / n
    u, d = _factors(contract, dt)
    a, p = _probability(u, d, contract["r"], dt, contract["q"])
    stock, option = trees.binomial_tree(
        contract["S0"],
        contract["K"],
        contract["r"],
        contract["T"],
        n,
        u,
        d,
        q=contract["q"],
        kind=contract["kind"],
        american=contract["american"],
    )
    body = {
        "price": float(option[0][0]),
        "params": {"dt": dt, "u": u, "d": d, "a": a, "p": p, "q": contract["q"]},
        "tree": None,
    }
    if n <= TREE_MAX_STEPS:
        body["tree"] = _nodes(contract, stock, option, p, dt)
    return body


def _nodes(contract: dict, stock: list, option: list, p: float, dt: float) -> dict:
    """Node values, per-node delta (hullkit's tree_delta on each one-step slice) and
    early-exercise flags (payoff above the continuation value hullkit computed)."""
    n = contract["n"]
    disc = math.exp(-contract["r"] * dt)
    delta, exercise = [], []
    for i in range(n):
        delta.append(
            [
                trees.tree_delta(
                    [stock[i][j : j + 1], stock[i + 1][j : j + 2]],
                    [option[i][j : j + 1], option[i + 1][j : j + 2]],
                )
                for j in range(i + 1)
            ]
        )
        if contract["american"]:
            cont = disc * (p * option[i + 1][:-1] + (1.0 - p) * option[i + 1][1:])
            if contract["kind"] == "call":
                payoff = np.maximum(stock[i] - contract["K"], 0.0)
            else:
                payoff = np.maximum(contract["K"] - stock[i], 0.0)
            exercise.append([bool(flag) for flag in payoff > cont])
        else:
            exercise.append([False] * (i + 1))
    return {
        "stock": [[float(x) for x in level] for level in stock],
        "option": [[float(x) for x in level] for level in option],
        "delta": delta,
        "exercise": exercise,
    }


def _convergence(contract: dict) -> dict:
    if contract["tree"] != "crr":
        raise InputError("tree", "needs_crr")
    prices: list[float | None] = []
    for n in CONVERGENCE_STEPS:
        dt = contract["T"] / n
        u, d = _factors(contract, dt)
        try:
            _probability(u, d, contract["r"], dt, contract["q"])
        except ArbitrageError:
            prices.append(None)
            continue
        prices.append(
            trees.crr_price(
                contract["S0"],
                contract["K"],
                contract["r"],
                contract["sigma"],
                contract["T"],
                n,
                q=contract["q"],
                kind=contract["kind"],
                american=contract["american"],
            )
        )
    return {"steps": list(CONVERGENCE_STEPS), "prices": prices}


def _bsm(contract: dict) -> dict:
    if contract["tree"] != "crr":
        raise InputError("tree", "needs_crr")
    if contract["american"]:
        raise InputError("american", "needs_european")
    from hullkit import bsm  # imported here so scipy loads only for the comparison

    price = bsm.call_price if contract["kind"] == "call" else bsm.put_price
    value = price(
        contract["S0"],
        contract["K"],
        contract["r"],
        contract["sigma"],
        contract["T"],
        q=contract["q"],
    )
    return {"bsm": float(value)}
```

Notes for the reader of this code:
- The per-node delta applies hullkit's `tree_delta` to the one-step slice under each node, so the numbers are hullkit's.
- The early-exercise flag compares the payoff with the continuation value written the same way hullkit computes it; `test_exercise_flags_mark_hull_fig_13_10_node_c` pins Hull Fig. 13.10 (node C exercises).
- `np.errstate(all="ignore")` plus `allow_nan=False` turns overflow into `{"code": "nonfinite"}` instead of a warning or a non-JSON `Infinity`.

- [ ] **Step 4: Run the tests to see them pass**

Run: `$PYT -m pytest johnhull/web/py/tests/test_binomial.py -q`
Expected: `45 passed`.

- [ ] **Step 5: Lint and commit**

Run: `$PY -m ruff check johnhull/web/py && $PY -m ruff format --check johnhull/web/py`
Expected: `All checks passed!` and `10 files already formatted`.

```bash
git add johnhull/web/py/hull_web_calc johnhull/web/py/tests/test_binomial.py
git commit -m "Add the binomial calculator's JSON entry point over hullkit.trees"
```

---

### Task 3: The browser package (hullkit modules byte for byte)

**Files:**
- Create: `johnhull/web/py/hull_web_build/package.py`
- Modify: `johnhull/web/py/hull_web_build/cli.py` (add `package`)
- Test: `johnhull/web/py/tests/test_package.py`

**Interfaces:**
- Consumes: `paths.HULLKIT_SRC`, `paths.CALC_SRC`, `paths.PACKAGE_ZIP`.
- Produces: `HULLKIT_MODULES = ("trees.py", "bsm.py")`; `INIT_SOURCE = "from . import trees\n"`; `members() -> dict[str, bytes]`; `zip_bytes(files) -> bytes` (stored, fixed timestamps); `build(dest=None) -> dict` (writes `build/hullkit_browser.zip` and `build/hullkit_browser.manifest.json`, returns the manifest); `init_is_imports_only(source) -> bool`; `verify(zip_path) -> list[str]` (empty means identical to the repo).

- [ ] **Step 1: Write the failing tests**

`johnhull/web/py/tests/test_package.py`:

```python
import hashlib
import subprocess
import sys
import zipfile

from hull_web_build import package, paths


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_hullkit_modules_are_byte_identical_to_the_repo(tmp_path):
    dest = tmp_path / "hullkit_browser.zip"
    package.build(dest)
    with zipfile.ZipFile(dest) as archive:
        for name in package.HULLKIT_MODULES:
            assert _sha(archive.read(f"hullkit/{name}")) == _sha(
                (paths.HULLKIT_SRC / name).read_bytes()
            )
    assert package.verify(dest) == []


def test_generated_init_only_imports():
    assert package.members()["hullkit/__init__.py"] == package.INIT_SOURCE.encode("utf-8")
    assert package.init_is_imports_only(package.INIT_SOURCE)


def test_init_check_rejects_anything_but_imports():
    assert not package.init_is_imports_only("from . import trees\nx = 1\n")
    assert not package.init_is_imports_only('"""doc"""\nfrom . import trees\n')


def test_zip_bytes_are_deterministic(tmp_path):
    first, second = tmp_path / "a.zip", tmp_path / "b.zip"
    package.build(first)
    package.build(second)
    assert first.read_bytes() == second.read_bytes()


def test_verify_names_a_modified_module(tmp_path):
    files = package.members()
    files["hullkit/trees.py"] += b"\n# edited\n"
    dest = tmp_path / "tampered.zip"
    dest.write_bytes(package.zip_bytes(files))
    problems = package.verify(dest)
    assert len(problems) == 1
    assert problems[0].startswith("hullkit/trees.py: sha256")


def test_package_imports_without_plotly_or_scipy(tmp_path):
    dest = tmp_path / "hullkit_browser.zip"
    package.build(dest)
    root = tmp_path / "unpacked"
    with zipfile.ZipFile(dest) as archive:
        archive.extractall(root)
    probe = (
        "import sys; sys.path.insert(0, sys.argv[1]);"
        "import hullkit; from hull_web_calc import binomial;"
        "print(hullkit.__file__.startswith(sys.argv[1]), 'plotly' in sys.modules, 'scipy' in sys.modules)"
    )
    out = subprocess.run(
        [sys.executable, "-I", "-c", probe, str(root)], capture_output=True, text=True, check=True
    )
    assert out.stdout.split() == ["True", "False", "False"]
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `$PYT -m pytest johnhull/web/py/tests/test_package.py -q`
Expected: collection error, `ImportError: cannot import name 'package' from 'hull_web_build'`.

- [ ] **Step 3: Implement the package and the command**

`johnhull/web/py/hull_web_build/package.py`:

```python
"""Browser package: hullkit modules byte-identical to the repo plus the calculator glue (spec §3.3).

`import hullkit` in the repo loads every module, plotly_viz included, so the browser
gets a new package that holds only the modules it uses, unchanged. Only
`hullkit/__init__.py` is generated, and it may contain imports and nothing else.
"""

from __future__ import annotations

import ast
import hashlib
import io
import json
import zipfile
from pathlib import Path

from . import paths

HULLKIT_MODULES = ("trees.py", "bsm.py")
INIT_SOURCE = "from . import trees\n"
ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)


def members() -> dict[str, bytes]:
    """Archive path -> bytes of every file in the browser package."""
    files = {"hullkit/__init__.py": INIT_SOURCE.encode("utf-8")}
    for name in HULLKIT_MODULES:
        files[f"hullkit/{name}"] = (paths.HULLKIT_SRC / name).read_bytes()
    for path in sorted(paths.CALC_SRC.glob("*.py")):
        files[f"hull_web_calc/{path.name}"] = path.read_bytes()
    return files


def zip_bytes(files: dict[str, bytes]) -> bytes:
    """A stored (uncompressed) zip with fixed timestamps: equal files give equal bytes."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, date_time=ZIP_EPOCH)
            info.external_attr = 0o644 << 16
            archive.writestr(info, files[name])
    return buffer.getvalue()


def build(dest: Path | None = None) -> dict:
    """Write the zip and its manifest next to it; return the manifest."""
    dest = dest or paths.PACKAGE_ZIP
    files = members()
    data = zip_bytes(files)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    manifest = {
        "zip_sha256": hashlib.sha256(data).hexdigest(),
        "members": {name: hashlib.sha256(blob).hexdigest() for name, blob in sorted(files.items())},
    }
    manifest_path = dest.with_name(dest.stem + ".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def init_is_imports_only(source: str) -> bool:
    """True when every top-level statement of `source` is an import."""
    return all(isinstance(node, (ast.Import, ast.ImportFrom)) for node in ast.parse(source).body)


def verify(zip_path: Path) -> list[str]:
    """Differences between a built zip and the repo; an empty list means byte-identical."""
    expected = {name: hashlib.sha256(blob).hexdigest() for name, blob in members().items()}
    problems = []
    with zipfile.ZipFile(zip_path) as archive:
        got = {name: hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist()}
        init = (
            archive.read("hullkit/__init__.py").decode("utf-8")
            if "hullkit/__init__.py" in got
            else ""
        )
    if sorted(got) != sorted(expected):
        problems.append(f"members {sorted(got)} != {sorted(expected)}")
    for name in sorted(set(got) & set(expected)):
        if got[name] != expected[name]:
            problems.append(f"{name}: sha256 {got[name]} != repo {expected[name]}")
    if not init_is_imports_only(init):
        problems.append("hullkit/__init__.py has statements other than imports")
    return problems
```

Replace `johnhull/web/py/hull_web_build/cli.py` with:

```python
"""Command line: python -m hull_web_build <command> (run from the repository root)."""

from __future__ import annotations

import argparse
import json

from . import package, pyodide_fetch


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m hull_web_build")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("fetch-pyodide", help="download and verify the pinned Pyodide files")
    commands.add_parser("package", help="build build/hullkit_browser.zip")
    args = parser.parse_args(argv)

    if args.command == "fetch-pyodide":
        pins = pyodide_fetch.load_pins()
        print(pyodide_fetch.fetch(pins, pyodide_fetch.load_lock(pins)))
    elif args.command == "package":
        print(json.dumps(package.build(), indent=2))
    return 0
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `$PYT -m pytest johnhull/web/py/tests -q`
Expected: `58 passed`.

- [ ] **Step 5: Build the package once**

Run: `$PYT -m hull_web_build package`
Expected: a manifest whose `members` are exactly `hull_web_calc/__init__.py`, `hull_web_calc/binomial.py`, `hullkit/__init__.py`, `hullkit/bsm.py`, `hullkit/trees.py`; `hullkit/trees.py` and `hullkit/bsm.py` carry the SHA-256 of `sha256sum johnhull/hullkit/src/hullkit/trees.py johnhull/hullkit/src/hullkit/bsm.py`.

- [ ] **Step 6: Lint and commit**

Run: `$PY -m ruff check johnhull/web/py && $PY -m ruff format --check johnhull/web/py`
Expected: `All checks passed!` and `12 files already formatted`.

```bash
git add johnhull/web/py/hull_web_build/package.py johnhull/web/py/hull_web_build/cli.py johnhull/web/py/tests/test_package.py
git commit -m "Build the browser package with hullkit modules byte-identical to the repo"
```

---

### Task 4: Example checks, the golden file and the W0 sweep

**Files:**
- Create: `johnhull/web/py/hull_web_build/examples.py`, `johnhull/web/py/hull_web_build/golden.py`
- Create (generated, committed): `johnhull/web/tests/golden.json`, `johnhull/web/src/calc/examples.json`
- Modify: `johnhull/web/py/hull_web_build/cli.py` (add `golden`, `sweep`)
- Test: `johnhull/web/py/tests/test_examples.py`, `test_golden.py`, `test_cli.py`

**Interfaces:**
- Consumes: `binomial.run`; `paths.GOLDEN_JSON`, `paths.EXAMPLES_JSON`, `paths.W0_SWEEP`, `paths.JOHNHULL_DIR`.
- Produces: `examples.Check(quantity, expected, tol, rule, source, printed=None, note=None)` and `Example(id, label, request, checks)`; `EXAMPLES` (11 buttons); quantity names `price`, `bsm`, `u`, `d`, `a`, `p`, `dt`, `stock[i][j]`, `option[i][j]`, `delta[i][j]`; `rule` is `"approx"` (|x − e| ≤ tol) or `"allclose"` (|x − e| ≤ tol + 1e-7·|e|); `quantity_value(quantity, price, bsm=None) -> float`; `passes(check, value) -> bool`; `payload() -> dict`.
- Produces: `golden.EDGE_CASES` (30); `cases() -> list[tuple[str, str]]`; `golden() -> dict`; `write() -> list[Path]`; `stale() -> list[Path]`; `sweep(count=300, seed=20261019) -> dict`; `write_sweep(path=None) -> Path`.
- Produces: `tests/golden.json` (`{"about", "cases": [{"name", "request", "response"}]}`, 42 cases: 11 examples, 1 example BSM request, 30 edge cases) and `src/calc/examples.json` (`{"about", "examples": [{"id", "label", "request", "checks": [...]}]}`); later tasks read both.

- [ ] **Step 1: Write the failing tests**

`johnhull/web/py/tests/test_examples.py` (the first test reads each pinned test function's source and requires every `expected`, `tol` and `printed` string to appear in it, so no value here is new):

```python
import ast
import io
import json
import tokenize
from functools import cache

import pytest
from hull_web_build import examples, paths
from hull_web_calc.binomial import run

REPO_ROOT = paths.JOHNHULL_DIR.parent
CHECKS = [(example, check) for example in examples.EXAMPLES for check in example.checks]


@cache
def _function_source(source: str) -> str:
    file, name = source.split("::")
    text = (REPO_ROOT / file).read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(text, node)
    raise AssertionError(f"{name} not found in {file}")


@cache
def _number_literals(source: str) -> frozenset[str]:
    tokens = tokenize.generate_tokens(io.StringIO(_function_source(source)).readline)
    return frozenset(token.string for token in tokens if token.type == tokenize.NUMBER)


@pytest.mark.parametrize(
    ("example", "check"), CHECKS, ids=lambda x: getattr(x, "id", None) or x.quantity
)
def test_expected_and_tolerance_are_literals_of_the_pinned_test(example, check):
    literals = _number_literals(check.source)
    assert check.expected in literals
    assert check.tol in literals
    if check.printed is not None:
        assert check.printed in _function_source(check.source)


def test_every_example_passes_its_checks_natively():
    for example in examples.EXAMPLES:
        price = json.loads(run(json.dumps(example.request)))
        bsm = None
        if any(check.quantity == "bsm" for check in example.checks):
            bsm = json.loads(run(json.dumps({**example.request, "op": "bsm"})))["bsm"]
        for check in example.checks:
            value = examples.quantity_value(check.quantity, price, bsm)
            assert examples.passes(check, value), (example.id, check)


def test_examples_cover_the_sections_the_spec_names():
    labels = " ".join(example.label for example in examples.EXAMPLES)
    for section in (
        "§13.1",
        "§13.3",
        "§13.4",
        "§13.5",
        "§13.8",
        "§13.10",
        "例題13.1",
        "例題13.2",
        "例題13.3",
    ):
        assert section in labels


def test_allclose_rule_adds_numpy_default_rtol():
    check = examples.Check("price", "100", "0", "allclose", "x")
    assert examples.passes(check, 100 + 0.9e-5)
    assert not examples.passes(examples.Check("price", "100", "0", "approx", "x"), 100 + 0.9e-5)


def test_quantity_value_reads_params_tree_and_bsm():
    price = {
        "price": 1.0,
        "params": {"u": 2.0},
        "tree": {"delta": [[0.5]], "stock": [[1.0], [3.0, 4.0]]},
    }
    assert examples.quantity_value("u", price) == 2.0
    assert examples.quantity_value("stock[1][1]", price) == 4.0
    assert examples.quantity_value("delta[0][0]", price) == 0.5
    assert examples.quantity_value("bsm", price, 7.0) == 7.0
    with pytest.raises(ValueError):
        examples.quantity_value("bsm", price)
```

`johnhull/web/py/tests/test_golden.py`:

```python
import json

from hull_web_build import golden


def test_committed_golden_and_examples_are_fresh():
    stale = golden.stale()
    assert stale == [], f"run `python -m hull_web_build golden`; stale: {stale}"


def test_golden_case_names_are_unique():
    names = [name for name, _ in golden.cases()]
    assert len(names) == len(set(names))


def test_golden_covers_errors_and_every_op():
    responses = [json.loads(case["response"]) for case in golden.golden()["cases"]]
    codes = {r["error"]["code"] for r in responses if not r["ok"]}
    assert codes == {"input", "arbitrage", "nonfinite"}
    assert any(r.get("tree") for r in responses if r["ok"])
    assert any("steps" in r for r in responses if r["ok"])
    assert any("bsm" in r for r in responses if r["ok"])


def test_sweep_is_deterministic_and_covers_every_op():
    first, second = golden.sweep(40), golden.sweep(40)
    assert first == second
    ops = {json.loads(case["request"])["op"] for case in first["cases"]}
    assert ops == {"price", "convergence", "bsm"}


def test_write_sweep_writes_300_native_cases(tmp_path):
    path = golden.write_sweep(tmp_path / "w0-sweep.json")
    cases = json.loads(path.read_text(encoding="utf-8"))["cases"]
    assert len(cases) == 300
    assert cases[0] == golden.sweep(1)["cases"][0]
```

`johnhull/web/py/tests/test_cli.py`:

```python
from hull_web_build import cli, golden


def test_golden_check_passes_when_fresh(capsys):
    assert golden.stale() == []
    assert cli.main(["golden", "--check"]) == 0


def test_golden_check_fails_and_names_stale_files(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(golden, "stale", lambda: [tmp_path / "golden.json"])
    assert cli.main(["golden", "--check"]) == 1
    assert "golden.json" in capsys.readouterr().err
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `$PYT -m pytest johnhull/web/py/tests/test_examples.py johnhull/web/py/tests/test_golden.py johnhull/web/py/tests/test_cli.py -q`
Expected: collection errors, `ImportError: cannot import name 'examples' from 'hull_web_build'` (and `golden`).

- [ ] **Step 3: Implement the examples, the golden file and the commands**

`johnhull/web/py/hull_web_build/examples.py`:

```python
"""Example buttons (spec §3.5): Hull 11e GE Ch.13 cases checked against pinned tests.

Every `expected` and `tol` below is the literal text of a number inside the named
hullkit test function, and `rule` mirrors how that test compares: "approx" is
pytest.approx(abs=tol), "allclose" is np.testing.assert_allclose(atol=tol), whose
default rtol is 1e-7. tests/test_examples.py checks the literals, so no value here
is new. `printed` is Hull's printed value where the pin records a different one.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

TREES_TEST = "johnhull/hullkit/tests/test_trees.py"
CRR_TEST = "johnhull/hullkit/tests/test_binomial_foundations_crr.py"
PINS_TEST = "johnhull/hullkit/tests/test_hull_pins_options.py"

S13_1 = f"{TREES_TEST}::test_one_step_call_hull_13_1_global_edition"
S13_3 = f"{TREES_TEST}::test_two_step_call_hull_fig_13_4_global_edition"
S13_45 = f"{TREES_TEST}::test_american_put_hull_fig_13_8"
S13_8 = f"{CRR_TEST}::test_hull_crr_coefficients_and_all_figure_13_10_nodes"
S13_10 = f"{PINS_TEST}::test_derivagem_american_put_section_13_10"
EX13_1 = f"{PINS_TEST}::test_example_13_1_index_call_two_step_tree"
EX13_2 = f"{PINS_TEST}::test_example_13_2_currency_american_call_three_step_tree"
EX13_3 = f"{PINS_TEST}::test_example_13_3_futures_american_put_three_step_tree"

ROUNDED_P = "原典は p を丸めてから計算した値を印刷している（固定テストの注記）"


@dataclass(frozen=True)
class Check:
    """One displayed comparison: `quantity` of the result against a pinned literal."""

    quantity: str
    expected: str
    tol: str
    rule: str
    source: str
    printed: str | None = None
    note: str | None = None


@dataclass(frozen=True)
class Example:
    """One example button: the request it fills in and the checks it shows."""

    id: str
    label: str
    request: dict
    checks: tuple[Check, ...]


def _request(tree, asset, kind, american, S0, K, r, T, n, *, q=0.0, sigma=None, u=None, d=None):
    request = {
        "op": "price",
        "tree": tree,
        "asset": asset,
        "kind": kind,
        "american": american,
        "S0": S0,
        "K": K,
        "r": r,
        "q": q,
        "T": T,
        "n": n,
    }
    if tree == "crr":
        request["sigma"] = sigma
    else:
        request["u"], request["d"] = u, d
    return request


def _checks(source, rule, tol, **quantities):
    return tuple(
        Check(name.replace("_", "."), lit, tol, rule, source) for name, lit in quantities.items()
    )


def _row(source, rule, tol, name, level, literals):
    return tuple(
        Check(f"{name}[{level}][{j}]", literal, tol, rule, source)
        for j, literal in enumerate(literals)
    )


EXAMPLES: tuple[Example, ...] = (
    Example(
        "s13-1",
        "§13.1 1段の木（コール）",
        _request("ud", "stock", "call", False, 20.0, 21.0, 0.04, 0.25, 1, u=1.1, d=0.9),
        (
            Check("p", "0.5503", "5e-5", "approx", S13_1),
            Check("price", "0.545", "5e-4", "approx", S13_1),
            Check("delta[0][0]", "0.25", "1e-12", "approx", S13_1),
        ),
    ),
    Example(
        "s13-3",
        "§13.3 2段の木（コール）",
        _request("ud", "stock", "call", False, 20.0, 21.0, 0.04, 0.5, 2, u=1.1, d=0.9),
        (
            Check("option[1][0]", "1.7433", "5e-5", "approx", S13_3),
            Check("price", "0.9497", "5e-5", "approx", S13_3),
            Check("delta[0][0]", "0.4358", "5e-5", "approx", S13_3),
            Check("delta[1][0]", "0.7273", "5e-5", "approx", S13_3),
        ),
    ),
    Example(
        "s13-4",
        "§13.4 ヨーロピアン・プット",
        _request("ud", "stock", "put", False, 50.0, 52.0, 0.05, 2.0, 2, u=1.2, d=0.8),
        (Check("price", "4.1927", "1e-3", "approx", S13_45, printed="4.1923", note=ROUNDED_P),),
    ),
    Example(
        "s13-5",
        "§13.5 アメリカン・プット",
        _request("ud", "stock", "put", True, 50.0, 52.0, 0.05, 2.0, 2, u=1.2, d=0.8),
        (Check("price", "5.0896", "1e-3", "approx", S13_45, printed="5.0894", note=ROUNDED_P),),
    ),
    Example(
        "s13-8",
        "§13.8 σ から作る木（アメリカン・プット、2段）",
        _request("crr", "stock", "put", True, 50.0, 52.0, 0.05, 2.0, 2, sigma=0.3),
        (
            *_checks(S13_8, "approx", "0.00005", u="1.3499", d="0.7408", a="1.0513", p="0.5097"),
            *_row(S13_8, "approx", "0.005", "stock", 1, ("67.49", "37.04")),
            *_row(S13_8, "approx", "0.005", "stock", 2, ("91.11", "50", "27.44")),
            Check("price", "7.43", "0.005", "approx", S13_8),
            *_row(S13_8, "approx", "0.005", "option", 1, ("0.93", "14.96")),
            *_row(S13_8, "approx", "0.005", "option", 2, ("0", "2", "24.56")),
            Check("price", "7.428", "5e-4", "approx", S13_10),
        ),
    ),
    Example(
        "s13-10-5",
        "§13.10 DerivaGem 5段",
        _request("crr", "stock", "put", True, 50.0, 52.0, 0.05, 2.0, 5, sigma=0.3),
        (
            *_checks(S13_10, "approx", "5e-5", u="1.2089", d="0.8272", a="1.0202", p="0.5056"),
            Check("price", "7.671", "5e-4", "approx", S13_10),
        ),
    ),
    Example(
        "s13-10-500",
        "§13.10 DerivaGem 500段（アメリカン）",
        _request("crr", "stock", "put", True, 50.0, 52.0, 0.05, 2.0, 500, sigma=0.3),
        (Check("price", "7.47", "5e-3", "approx", S13_10),),
    ),
    Example(
        "s13-10-500e",
        "§13.10 500段（ヨーロピアン）と BSM",
        _request("crr", "stock", "put", False, 50.0, 52.0, 0.05, 2.0, 500, sigma=0.3),
        (
            Check("price", "6.76", "5e-3", "approx", S13_10),
            Check("bsm", "6.76", "5e-3", "approx", S13_10),
        ),
    ),
    Example(
        "ex13-1",
        "例題13.1 株価指数のコール",
        _request("crr", "index", "call", False, 810.0, 800.0, 0.05, 0.5, 2, q=0.02, sigma=0.2),
        (
            *_checks(EX13_1, "approx", "5e-5", u="1.1052", d="0.9048", a="1.0075", p="0.5126"),
            Check("price", "53.39", "5e-3", "approx", EX13_1),
            *_row(EX13_1, "allclose", "5e-3", "stock", 1, ("895.19", "732.92")),
            *_row(EX13_1, "allclose", "5e-3", "option", 1, ("100.66", "5.06")),
            *_row(EX13_1, "allclose", "5e-3", "stock", 2, ("989.34", "810.00", "663.17")),
            *_row(EX13_1, "allclose", "5e-3", "option", 2, ("189.34", "10.00", "0.00")),
        ),
    ),
    Example(
        "ex13-2",
        "例題13.2 通貨のアメリカン・コール",
        _request("crr", "currency", "call", True, 0.61, 0.60, 0.05, 0.25, 3, q=0.07, sigma=0.12),
        (
            *_checks(EX13_2, "approx", "5e-5", u="1.0352", d="0.9660", a="0.9983", p="0.4673"),
            Check("price", "0.019", "5e-4", "approx", EX13_2),
            Check("price", "0.01888", "5e-6", "approx", EX13_2),
            *_row(EX13_2, "allclose", "5e-4", "stock", 1, ("0.632", "0.589")),
            *_row(EX13_2, "allclose", "5e-4", "option", 1, ("0.033", "0.007")),
            *_row(EX13_2, "allclose", "5e-4", "stock", 2, ("0.654", "0.610", "0.569")),
            *_row(EX13_2, "allclose", "5e-4", "option", 2, ("0.054", "0.015", "0.000")),
            *_row(EX13_2, "allclose", "5e-4", "stock", 3, ("0.677", "0.632", "0.589", "0.550")),
            *_row(EX13_2, "allclose", "5e-4", "option", 3, ("0.077", "0.032", "0.000", "0.000")),
        ),
    ),
    Example(
        "ex13-3",
        "例題13.3 先物のアメリカン・プット",
        _request("crr", "futures", "put", True, 31.0, 30.0, 0.05, 0.75, 3, sigma=0.3),
        (
            *_checks(EX13_3, "approx", "5e-5", u="1.1618", d="0.8607"),
            Check("a", "1.000", "1e-12", "approx", EX13_3),
            Check("p", "0.4626", "5e-5", "approx", EX13_3),
            Check("price", "2.84", "5e-3", "approx", EX13_3),
            *_row(EX13_3, "allclose", "5e-3", "stock", 1, ("36.02", "26.68")),
            *_row(EX13_3, "allclose", "5e-3", "option", 1, ("0.93", "4.54")),
            *_row(EX13_3, "allclose", "5e-3", "stock", 2, ("41.85", "31.00", "22.97")),
            *_row(EX13_3, "allclose", "5e-3", "option", 2, ("0.00", "1.76", "7.03")),
            *_row(EX13_3, "allclose", "5e-3", "stock", 3, ("48.62", "36.02", "26.68", "19.77")),
            *_row(EX13_3, "allclose", "5e-3", "option", 3, ("0.00", "0.00", "3.32", "10.23")),
        ),
    ),
)


def quantity_value(quantity: str, price: dict, bsm: float | None = None) -> float:
    """The number a check reads from a price response (and the BSM value for "bsm")."""
    if quantity == "price":
        return price["price"]
    if quantity == "bsm":
        if bsm is None:
            raise ValueError("this check needs the BSM response")
        return bsm
    if quantity in ("u", "d", "a", "p", "dt"):
        return price["params"][quantity]
    name, rest = quantity.split("[", 1)
    i, j = (int(part) for part in rest.rstrip("]").split("]["))
    return price["tree"][name][i][j]


def passes(check: Check, value: float) -> bool:
    """The same comparison as the pinned test (see the module docstring)."""
    expected, tol = float(check.expected), float(check.tol)
    bound = tol + 1e-7 * abs(expected) if check.rule == "allclose" else tol
    return abs(value - expected) <= bound


def payload() -> dict:
    """What src/calc/examples.json holds for the browser."""
    return {
        "about": "Generated by `python -m hull_web_build golden` from hull_web_build/examples.py.",
        "examples": [
            {**asdict(example), "checks": [asdict(check) for check in example.checks]}
            for example in EXAMPLES
        ],
    }
```

`johnhull/web/py/hull_web_build/golden.py`:

```python
"""Golden file and example data, generated from native CPython (spec §3.5, §5).

tests/golden.json holds, for each case, the request text and the exact response text
of hull_web_calc.binomial.run; the browser test requires the same text back.
src/calc/examples.json is what the example buttons read.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from hull_web_calc.binomial import run

from . import examples, paths


def _req(**change) -> str:
    request = {
        "op": "price",
        "tree": "crr",
        "asset": "stock",
        "kind": "put",
        "american": True,
        "S0": 50.0,
        "K": 52.0,
        "r": 0.05,
        "q": 0.0,
        "sigma": 0.3,
        "T": 2.0,
        "n": 2,
    }
    request.update(change)
    if request["tree"] == "ud":
        request.pop("sigma", None)
    return json.dumps(request, sort_keys=True)


EX13_1 = {"asset": "index", "kind": "call", "american": False, "S0": 810.0, "K": 800.0}
EX13_1 |= {"q": 0.02, "sigma": 0.2, "T": 0.5}
UD = {"tree": "ud", "u": 1.1, "d": 0.9}

EDGE_CASES: tuple[tuple[str, str], ...] = (
    ("edge:crr-american-put-n1", _req(n=1)),
    (
        "edge:crr-american-call-no-dividend-n500",
        _req(kind="call", S0=100.0, K=100.0, r=0.03, sigma=0.25, T=1.0, n=500),
    ),
    ("edge:crr-european-call-n6-tree", _req(kind="call", american=False, n=6)),
    ("edge:crr-european-call-n7-no-tree", _req(kind="call", american=False, n=7)),
    ("edge:deep-in-the-money-call", _req(kind="call", american=False, K=5.0, T=1.0, n=6)),
    ("edge:deep-out-of-the-money-put", _req(K=0.5, T=1.0, n=6)),
    ("edge:negative-rate-call", _req(kind="call", american=False, r=-0.01, n=5)),
    ("edge:one-day-maturity", _req(T=1 / 365, n=50)),
    ("edge:index-american-put", _req(asset="index", q=0.03, n=6)),
    (
        "edge:currency-american-put",
        _req(asset="currency", S0=0.61, K=0.6, q=0.07, sigma=0.12, T=0.25, n=6),
    ),
    (
        "edge:futures-european-call",
        _req(asset="futures", kind="call", american=False, S0=31.0, K=30.0, T=0.75, n=6),
    ),
    ("edge:ud-american-call", _req(**UD, kind="call", n=3)),
    ("edge:arbitrage-ud", _req(tree="ud", u=1.1, d=1.06, T=1.0, n=1)),
    ("edge:arbitrage-crr", _req(sigma=0.01, T=1.0, n=1)),
    ("edge:input-n0", _req(n=0)),
    ("edge:input-n501", _req(n=501)),
    ("edge:input-n-float", _req(n=2.0)),
    ("edge:input-negative-sigma", _req(sigma=-0.3)),
    ("edge:input-d-above-u", _req(tree="ud", u=0.9, d=1.1)),
    ("edge:input-unknown-asset", _req(asset="bond")),
    ("edge:input-not-json", "not json"),
    ("edge:overflow-sigma", _req(sigma=1000.0, T=1.0, n=1)),
    ("edge:overflow-tree", _req(**UD, kind="call", S0=1e300, n=500)),
    ("edge:convergence-american-put", _req(op="convergence")),
    ("edge:convergence-index-call", _req(op="convergence", **EX13_1)),
    (
        "edge:convergence-arbitrage-gaps",
        _req(op="convergence", kind="call", american=False, sigma=0.1, r=0.2, T=1.0),
    ),
    ("edge:convergence-needs-crr", _req(op="convergence", **UD)),
    ("edge:bsm-index-call", _req(op="bsm", **EX13_1)),
    (
        "edge:bsm-futures-put",
        _req(op="bsm", asset="futures", american=False, S0=31.0, K=30.0, T=0.75),
    ),
    ("edge:bsm-needs-european", _req(op="bsm")),
)


def cases() -> list[tuple[str, str]]:
    """(name, request text) for every golden case: each example, then the edge cases."""
    out = []
    for example in examples.EXAMPLES:
        out.append((f"example:{example.id}", json.dumps(example.request, sort_keys=True)))
        if any(check.quantity == "bsm" for check in example.checks):
            bsm_request = {**example.request, "op": "bsm"}
            out.append((f"example:{example.id}:bsm", json.dumps(bsm_request, sort_keys=True)))
    return out + list(EDGE_CASES)


def golden() -> dict:
    """The golden payload: native responses as exact text."""
    return {
        "about": "Native responses of hull_web_calc.binomial.run; the browser must return identical text.",
        "cases": [{"name": name, "request": text, "response": run(text)} for name, text in cases()],
    }


def _dump(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def outputs() -> dict[Path, str]:
    """File -> exact text of every generated file."""
    return {paths.GOLDEN_JSON: _dump(golden()), paths.EXAMPLES_JSON: _dump(examples.payload())}


def write() -> list[Path]:
    """Regenerate the files; return those whose text changed."""
    changed = []
    for path, text in outputs().items():
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            changed.append(path)
    return changed


def stale() -> list[Path]:
    """Generated files that differ from what `write()` would produce."""
    return [
        path
        for path, text in outputs().items()
        if not path.exists() or path.read_text(encoding="utf-8") != text
    ]


TREES_FOR_SWEEP = ("crr", "crr", "ud")


def sweep(count: int = 300, seed: int = 20261019) -> dict:
    """Random requests with native responses, for W0's browser-versus-native measurement."""
    rng = random.Random(seed)
    cases = []
    for k in range(count):
        tree = rng.choice(TREES_FOR_SWEEP)
        op = "price" if tree == "ud" else rng.choice(("price", "price", "convergence", "bsm"))
        request = {
            "op": op,
            "tree": tree,
            "asset": rng.choice(("stock", "index", "currency", "futures")),
            "kind": rng.choice(("call", "put")),
            "american": op != "bsm" and rng.random() < 0.5,
            "S0": round(rng.uniform(5.0, 200.0), 2),
            "K": round(rng.uniform(5.0, 200.0), 2),
            "r": round(rng.uniform(-0.01, 0.10), 4),
            "q": round(rng.uniform(0.0, 0.08), 4),
            "T": round(rng.uniform(0.05, 3.0), 3),
            "n": rng.choice((1, 2, 3, 5, 6, 7, 20, 50, 100, 250, 500)),
        }
        if tree == "crr":
            request["sigma"] = round(rng.uniform(0.05, 0.8), 3)
        else:
            request["u"] = round(rng.uniform(1.01, 1.5), 3)
            request["d"] = round(rng.uniform(0.6, 0.99), 3)
        text = json.dumps(request, sort_keys=True)
        cases.append({"name": f"sweep:{k}", "request": text, "response": run(text)})
    return {"about": "Random requests for W0 only (not committed).", "seed": seed, "cases": cases}


def write_sweep(path: Path | None = None) -> Path:
    """Write the W0 sweep (build/w0-sweep.json by default) and return its path."""
    path = path or paths.W0_SWEEP
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sweep()) + "\n", encoding="utf-8")
    return path
```

Replace `johnhull/web/py/hull_web_build/cli.py` with:

```python
"""Command line: python -m hull_web_build <command> (run from the repository root)."""

from __future__ import annotations

import argparse
import json
import sys

from . import golden, package, pyodide_fetch


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m hull_web_build")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("fetch-pyodide", help="download and verify the pinned Pyodide files")
    commands.add_parser("package", help="build build/hullkit_browser.zip")
    golden_parser = commands.add_parser(
        "golden", help="write tests/golden.json and src/calc/examples.json"
    )
    golden_parser.add_argument("--check", action="store_true", help="fail instead of writing")
    commands.add_parser("sweep", help="write build/w0-sweep.json (W0 only)")
    args = parser.parse_args(argv)

    if args.command == "fetch-pyodide":
        pins = pyodide_fetch.load_pins()
        print(pyodide_fetch.fetch(pins, pyodide_fetch.load_lock(pins)))
    elif args.command == "package":
        print(json.dumps(package.build(), indent=2))
    elif args.command == "golden":
        if args.check:
            stale = golden.stale()
            if stale:
                print(
                    "stale (run python -m hull_web_build golden):",
                    *stale,
                    sep="\n  ",
                    file=sys.stderr,
                )
                return 1
        else:
            for path in golden.write():
                print("wrote", path)
    elif args.command == "sweep":
        print("wrote", golden.write_sweep())
    return 0
```

- [ ] **Step 4: Generate the two data files**

Run: `$PYT -m hull_web_build golden`
Expected: `wrote …/johnhull/web/tests/golden.json` and `wrote …/johnhull/web/src/calc/examples.json`. Then `$PY -c "import json; print(len(json.load(open('johnhull/web/tests/golden.json'))['cases']))"` prints `42`.

- [ ] **Step 5: Run the tests to see them pass**

Run: `$PYT -m pytest johnhull/web/py/tests -q`
Expected: `164 passed` (99 of them are the literal checks in `test_examples.py`).

- [ ] **Step 6: Lint and commit**

Run: `$PY -m ruff check johnhull/web/py && $PY -m ruff format --check johnhull/web/py`
Expected: `All checks passed!` and `17 files already formatted`.

```bash
git add johnhull/web/py/hull_web_build/examples.py johnhull/web/py/hull_web_build/golden.py \
  johnhull/web/py/hull_web_build/cli.py johnhull/web/py/tests/test_examples.py johnhull/web/py/tests/test_golden.py \
  johnhull/web/py/tests/test_cli.py johnhull/web/tests/golden.json johnhull/web/src/calc/examples.json
git commit -m "Generate the golden file and example checks from pinned hullkit tests"
```

---

### Task 5: W0 — spike site, measurements and report (then stop)

**Files:**
- Create: `johnhull/web/tests/ulps.mts`, `johnhull/web/tests/ulps.test.mts`
- Create: `johnhull/web/py/hull_web_build/site.py` (W0 part), `johnhull/web/py/tests/test_site.py` (W0 part)
- Create: `johnhull/web/w0/index.html`, `w0/boot.js`, `w0/worker.js`, `w0/main.js`, `johnhull/web/scripts/w0_measure.mjs`
- Create: `johnhull/docs/validation/hull-web/w0.json`, `johnhull/docs/validation/hull-web/W0_REPORT.md`, `johnhull/web/tests/tolerance.json`
- Modify: `johnhull/web/py/hull_web_build/cli.py` (add `w0-site`), `johnhull/ROADMAP.md`

**Interfaces:**
- Consumes: `package.build`, `package.verify`, `pyodide_fetch.*`, `golden.write_sweep`, `paths.*`.
- Produces: `ulps.mts`: `ulpDistance(a, b): number` and `compareJson(want, got, path = "$"): {maxUlps, where, mismatch}` (numbers may differ by ulps; any other difference is a mismatch). Task 10 uses it.
- Produces: `site.SiteError`; `copy_content(out)`; `copy_pyodide(out, pins, lock, source)`; `check_files(out) -> {"files", "bytes"}`; `assemble_w0(out=None, pyodide_dir=None) -> dict`; `MAX_FILE_BYTES`, `MAX_FILES`. Task 9 extends this module.
- Produces: `tests/tolerance.json` with `max_ulps` (Task 10's golden test reads it).

- [ ] **Step 1: Write the failing ulp tests**

`johnhull/web/tests/ulps.test.mts`:

```ts
import assert from "node:assert/strict";
import { test } from "node:test";
import { compareJson, ulpDistance } from "./ulps.mts";

test("neighbouring doubles are one ulp apart", () => {
  assert.equal(ulpDistance(1, 1 + Number.EPSILON), 1);
  assert.equal(ulpDistance(-1, -1 - Number.EPSILON), 1);
  assert.equal(ulpDistance(7.499383460575638, 7.499383460575639), 1);
  assert.equal(ulpDistance(0, -0), 0);
});

test("a sign change or a non-finite value is infinitely far", () => {
  assert.equal(ulpDistance(1e-300, -1e-300), Number.POSITIVE_INFINITY);
  assert.equal(ulpDistance(Number.NaN, 1), Number.POSITIVE_INFINITY);
});

test("compareJson reports the largest ulp distance and where it is", () => {
  const want = { ok: true, prices: [1, 7.499383460575638, null] };
  const got = { ok: true, prices: [1, 7.499383460575639, null] };
  assert.deepEqual(compareJson(want, got), { maxUlps: 1, where: "$.prices[1]", mismatch: null });
});

test("compareJson treats any other difference as a mismatch", () => {
  assert.match(compareJson({ a: [1, null] }, { a: [1, 2] }).mismatch ?? "", /null != 2/);
  assert.match(compareJson({ a: 1 }, { b: 1 }).mismatch ?? "", /keys/);
  assert.match(compareJson([1], [1, 2]).mismatch ?? "", /length/);
  assert.match(compareJson({ ok: true }, { ok: false }).mismatch ?? "", /true != false/);
});
```

Run: `node --test johnhull/web/tests/ulps.test.mts`
Expected: FAIL, `ERR_MODULE_NOT_FOUND` for `ulps.mts`.

- [ ] **Step 2: Implement the ulp comparison**

`johnhull/web/tests/ulps.mts`:

```ts
// How far apart two doubles are, in units in the last place (ulps), and the largest
// such distance between two JSON values of the same shape (spec §5: 計算の一致).

export function ulpDistance(a: number, b: number): number {
  if (a === b) return 0;
  if (!Number.isFinite(a) || !Number.isFinite(b) || Math.sign(a) !== Math.sign(b)) return Number.POSITIVE_INFINITY;
  const view = new DataView(new ArrayBuffer(16));
  view.setFloat64(0, a);
  view.setFloat64(8, b);
  const diff = view.getBigInt64(0) - view.getBigInt64(8);
  return Number(diff < 0n ? -diff : diff);
}

export interface Comparison {
  maxUlps: number;
  where: string;
  mismatch: string | null;
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function worst(parts: Comparison[], path: string): Comparison {
  let result: Comparison = { maxUlps: 0, where: path, mismatch: null };
  for (const part of parts) {
    if (part.mismatch !== null) return part;
    if (part.maxUlps > result.maxUlps) result = part;
  }
  return result;
}

// Numbers may differ by some ulps; everything else (keys, lengths, null, booleans, strings) must be equal.
export function compareJson(want: unknown, got: unknown, path = "$"): Comparison {
  if (typeof want === "number" && typeof got === "number") {
    return { maxUlps: ulpDistance(want, got), where: path, mismatch: null };
  }
  if (Array.isArray(want) && Array.isArray(got)) {
    if (want.length !== got.length) {
      return { maxUlps: Number.POSITIVE_INFINITY, where: path, mismatch: `length ${want.length} != ${got.length}` };
    }
    return worst(
      want.map((item, k) => compareJson(item, got[k], `${path}[${k}]`)),
      path,
    );
  }
  if (isObject(want) && isObject(got)) {
    const keys = Object.keys(want).sort();
    const gotKeys = Object.keys(got).sort();
    if (keys.join("\n") !== gotKeys.join("\n")) {
      return { maxUlps: Number.POSITIVE_INFINITY, where: path, mismatch: `keys ${keys} != ${gotKeys}` };
    }
    return worst(
      keys.map((key) => compareJson(want[key], got[key], `${path}.${key}`)),
      path,
    );
  }
  if (want === got) return { maxUlps: 0, where: path, mismatch: null };
  return { maxUlps: Number.POSITIVE_INFINITY, where: path, mismatch: `${JSON.stringify(want)} != ${JSON.stringify(got)}` };
}
```

Run: `node --test johnhull/web/tests/ulps.test.mts`
Expected: `ℹ pass 4`, `ℹ fail 0`.

- [ ] **Step 3: Write the failing site tests**

`johnhull/web/py/tests/test_site.py` (the `world` fixture builds a small Book, report, app build and Pyodide cache and points `paths` at them; Task 9 adds tests that use the app build):

```python
import hashlib
import json

import pytest
from hull_web_build import package, paths, pyodide_fetch, site


def _write(root, files: dict[str, str | bytes]):
    for name, data in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, bytes):
            path.write_bytes(data)
        else:
            path.write_text(data, encoding="utf-8")


@pytest.fixture
def world(tmp_path, monkeypatch):
    """Small Book, report, app build and Pyodide cache wired into `paths`."""
    book, report, app, cache = (tmp_path / n for n in ("book", "report", "app", "cache"))
    _write(
        book,
        {
            "index.html": '<a href="notebooks/x.html">x</a><a href="_sources/x.ipynb">src</a>',
            "notebooks/x.html": '<a href="../index.html">up</a><a href="../../../../report/site/">r</a>',
            "_sources/x.ipynb": "{}",
            ".buildinfo": "x",
            "paper.pdf": b"%PDF",
            "_static/macros.html": "<a href=\"{{ pathto('x') }}\">t</a>",
        },
    )
    _write(
        report, {"index.html": '<a href="../../book/_build/html/">book</a>', "hull.pdf": b"%PDF"}
    )
    _write(
        app,
        {
            "index.html": (
                '<link rel="manifest" href="/manifest.webmanifest">'
                '<link rel="icon" href="/icons/icon-192.png">'
                '<a href="/book/_build/html/">b</a><a href="/report/site/">r</a>'
                '<a href="/calc/binomial/">c</a><script src="/assets/main.js"></script>'
            ),
            "calc/binomial/index.html": '<script src="/assets/calc.js"></script>',
            "assets/main.js": "",
            "assets/calc.js": "",
            "404.html": '<a href="/">top</a>',
            "_headers": "/*\n  X-Robots-Tag: noindex\n",
            "robots.txt": "User-agent: *\nDisallow: /\n",
            "manifest.webmanifest": "{}",
        },
    )
    blobs = {"pyodide.mjs": b"m", "pyodide.asm.wasm": b"w", "numpy-1-x.whl": b"n"}
    _write(cache, dict(blobs))
    lock = {
        "info": {"python": "3.14.2"},
        "packages": {
            "numpy": {
                "file_name": "numpy-1-x.whl",
                "sha256": hashlib.sha256(b"n").hexdigest(),
                "depends": [],
            }
        },
    }
    lock_path = tmp_path / "pyodide-lock.json"
    lock_path.write_text(json.dumps(lock), encoding="utf-8")
    pins = {
        "pyodide": {
            "version": "9.9.9",
            "base_url": "https://example.invalid/",
            "lock_sha256": pyodide_fetch.sha256(lock_path),
            "core": {
                name: hashlib.sha256(blobs[name]).hexdigest()
                for name in ("pyodide.mjs", "pyodide.asm.wasm")
            },
            "packages": ["numpy"],
        }
    }
    pins_path = tmp_path / "pins.json"
    pins_path.write_text(json.dumps(pins), encoding="utf-8")
    zip_path = tmp_path / "build" / "hullkit_browser.zip"
    package.build(zip_path)
    for name, value in {
        "BOOK_HTML": book,
        "REPORT_SITE": report,
        "GUIDE_TABLES": tmp_path / "no-guide-yet",
        "APP_BUILD": app,
        "PACKAGE_ZIP": zip_path,
        "LOCK": lock_path,
        "PINS": pins_path,
    }.items():
        monkeypatch.setattr(paths, name, value)
    return {"tmp": tmp_path, "cache": cache, "pins": pins, "lock": lock}


def test_content_copy_leaves_out_sources_buildinfo_and_pdfs(world):
    out = world["tmp"] / "out"
    site.copy_content(out)
    names = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    assert names == [
        "book/_build/html/_static/macros.html",
        "book/_build/html/index.html",
        "book/_build/html/notebooks/x.html",
        "report/site/index.html",
    ]


def test_guide_tables_are_copied_once_they_exist(world, monkeypatch):
    guide = world["tmp"] / "guide"
    _write(guide, {"numerics.json": "{}"})
    monkeypatch.setattr(paths, "GUIDE_TABLES", guide)
    out = world["tmp"] / "out"
    site.copy_content(out)
    assert (out / "docs/validation/reading-guide/numerics.json").is_file()


def test_missing_book_build_names_the_make_target(world, monkeypatch):
    monkeypatch.setattr(paths, "BOOK_HTML", world["tmp"] / "nothing")
    with pytest.raises(site.SiteError, match="make hull-book"):
        site.copy_content(world["tmp"] / "out")


def test_check_files_rejects_forbidden_large_and_too_many_files(tmp_path, monkeypatch):
    _write(tmp_path, {"a.pdf": b"x", "b/_sources/c.txt": "x", "big.bin": b"0123456789"})
    monkeypatch.setattr(site, "MAX_FILE_BYTES", 5)
    monkeypatch.setattr(site, "MAX_FILES", 2)
    with pytest.raises(site.SiteError) as caught:
        site.check_files(tmp_path)
    message = str(caught.value)
    assert "a.pdf" in message and "b/_sources/c.txt" in message
    assert "big.bin" in message and "3 files" in message


def test_pyodide_copy_rejects_a_corrupted_cache(world):
    (world["cache"] / "pyodide.asm.wasm").write_bytes(b"tampered")
    with pytest.raises(pyodide_fetch.IntegrityError, match=r"pyodide\.asm\.wasm"):
        site.copy_pyodide(world["tmp"] / "out", world["pins"], world["lock"], world["cache"])


def test_w0_site_serves_the_spike_under_two_policies(world):
    out = world["tmp"] / "w0-site"
    site.assemble_w0(out, world["cache"])
    headers = (out / "_headers").read_text(encoding="utf-8")
    assert (
        "/w0/*\n  Content-Security-Policy: default-src 'self'; script-src 'self' 'wasm-unsafe-eval';"
        in headers
    )
    assert "script-src 'self' 'wasm-unsafe-eval' 'unsafe-eval';" in headers
    assert (out / "w0/index.html").is_file() and (out / "w0-eval/worker.js").is_file()
    assert (out / "404.html").is_file()
    assert (out / "pyodide/hullkit_browser.zip").is_file()
```

Run: `$PYT -m pytest johnhull/web/py/tests/test_site.py -q`
Expected: collection error, `ImportError: cannot import name 'site' from 'hull_web_build'`.

- [ ] **Step 4: Implement the W0 part of the site module and the command**

`johnhull/web/py/hull_web_build/site.py`:

```python
"""Assemble a site directory and check what it may contain (spec §3.2, §5)."""

from __future__ import annotations

import shutil
from pathlib import Path

from . import package, paths, pyodide_fetch

MAX_FILE_BYTES = 25 * 1024 * 1024
MAX_FILES = 20_000
W0_CSP = (
    "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; connect-src 'self'; "
    "worker-src 'self'; object-src 'none'; base-uri 'self'"
)
W0_HEADERS = """/*
  X-Robots-Tag: noindex
  X-Content-Type-Options: nosniff
  Referrer-Policy: same-origin

/w0/*
  Content-Security-Policy: {strict}

/w0-eval/*
  Content-Security-Policy: {with_eval}
"""


class SiteError(RuntimeError):
    """An input is missing or the assembled site breaks a rule of the spec."""


def _require(path: Path, how: str) -> None:
    if not path.exists():
        raise SiteError(f"{path} is missing; run `{how}` first")


def _skip_book(directory: str, names: list[str]) -> set[str]:
    return {n for n in names if n in ("_sources", ".buildinfo") or n.lower().endswith(".pdf")}


def _skip_pdf(directory: str, names: list[str]) -> set[str]:
    return {n for n in names if n.lower().endswith(".pdf")}


def copy_content(out: Path) -> None:
    """Copy the Book, the supplementary site and, once merged, the guide tables (spec §3.2)."""
    _require(paths.BOOK_HTML / "index.html", "make hull-book")
    _require(paths.REPORT_SITE / "index.html", "make hull-report")
    shutil.copytree(paths.BOOK_HTML, out / "book" / "_build" / "html", ignore=_skip_book)
    shutil.copytree(paths.REPORT_SITE, out / "report" / "site", ignore=_skip_pdf)
    if paths.GUIDE_TABLES.is_dir():
        target = out / "docs" / "validation" / "reading-guide"
        shutil.copytree(paths.GUIDE_TABLES, target, ignore=_skip_pdf)


def copy_pyodide(out: Path, pins: dict, lock: dict, source: Path) -> None:
    """Copy the pinned Pyodide files and the browser package to /pyodide/, re-verifying each."""
    target = out / "pyodide"
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(paths.LOCK, target / "pyodide-lock.json")
    for name, digest in pyodide_fetch.expected_files(pins, lock).items():
        _require(source / name, "python -m hull_web_build fetch-pyodide")
        shutil.copy2(source / name, target / name)
        if pyodide_fetch.sha256(target / name) != digest:
            raise pyodide_fetch.IntegrityError(f"{source / name} does not match its pin")
    _require(paths.PACKAGE_ZIP, "python -m hull_web_build package")
    shutil.copy2(paths.PACKAGE_ZIP, target / "hullkit_browser.zip")
    problems = package.verify(target / "hullkit_browser.zip")
    if problems:
        raise SiteError("browser package differs from the repo: " + "; ".join(problems))


def check_files(out: Path) -> dict:
    """Forbidden files, the 25 MiB per-file limit and the 20,000-file limit."""
    files = sorted(p for p in out.rglob("*") if p.is_file())
    names = [p.relative_to(out).as_posix() for p in files]
    problems = []
    forbidden = [
        n
        for n in names
        if n.lower().endswith(".pdf") or "/_sources/" in f"/{n}" or n.endswith(".buildinfo")
    ]
    if forbidden:
        problems.append(f"forbidden files: {forbidden[:10]}")
    large = [n for p, n in zip(files, names, strict=True) if p.stat().st_size > MAX_FILE_BYTES]
    if large:
        problems.append(f"files over 25 MiB: {large}")
    if len(files) > MAX_FILES:
        problems.append(f"{len(files)} files is over the {MAX_FILES} limit")
    if problems:
        raise SiteError("\n".join(problems))
    return {"files": len(files), "bytes": sum(p.stat().st_size for p in files)}


def _fresh(out: Path) -> None:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)


def assemble_w0(out: Path | None = None, pyodide_dir: Path | None = None) -> dict:
    """W0 spike site: content, Pyodide and the spike page at /w0/ (strict CSP) and /w0-eval/."""
    out = out or paths.W0_SITE
    pins = pyodide_fetch.load_pins()
    lock = pyodide_fetch.load_lock(pins)
    _fresh(out)
    copy_content(out)
    copy_pyodide(out, pins, lock, pyodide_dir or paths.PYODIDE_CACHE / pins["pyodide"]["version"])
    for mount in ("w0", "w0-eval"):
        shutil.copytree(paths.W0_PAGE, out / mount)
    with_eval = W0_CSP.replace("'wasm-unsafe-eval'", "'wasm-unsafe-eval' 'unsafe-eval'")
    headers = W0_HEADERS.format(strict=W0_CSP, with_eval=with_eval)
    (out / "_headers").write_text(headers, encoding="utf-8")
    (out / "404.html").write_text(
        "<!doctype html><title>404</title><p>Not found</p>\n", encoding="utf-8"
    )
    (out / "index.html").write_text(
        '<!doctype html><title>W0</title><a href="/w0/">W0</a>\n', encoding="utf-8"
    )
    return check_files(out)
```

Replace `johnhull/web/py/hull_web_build/cli.py` with:

```python
"""Command line: python -m hull_web_build <command> (run from the repository root)."""

from __future__ import annotations

import argparse
import json
import sys

from . import golden, package, pyodide_fetch, site


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m hull_web_build")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("fetch-pyodide", help="download and verify the pinned Pyodide files")
    commands.add_parser("package", help="build build/hullkit_browser.zip")
    golden_parser = commands.add_parser(
        "golden", help="write tests/golden.json and src/calc/examples.json"
    )
    golden_parser.add_argument("--check", action="store_true", help="fail instead of writing")
    commands.add_parser("sweep", help="write build/w0-sweep.json (W0 only)")
    commands.add_parser("w0-site", help="assemble the W0 spike site in build/w0-site")
    args = parser.parse_args(argv)

    if args.command == "fetch-pyodide":
        pins = pyodide_fetch.load_pins()
        print(pyodide_fetch.fetch(pins, pyodide_fetch.load_lock(pins)))
    elif args.command == "package":
        print(json.dumps(package.build(), indent=2))
    elif args.command == "golden":
        if args.check:
            stale = golden.stale()
            if stale:
                print(
                    "stale (run python -m hull_web_build golden):",
                    *stale,
                    sep="\n  ",
                    file=sys.stderr,
                )
                return 1
        else:
            for path in golden.write():
                print("wrote", path)
    elif args.command == "sweep":
        print("wrote", golden.write_sweep())
    elif args.command == "w0-site":
        print(json.dumps(site.assemble_w0(), indent=2))
    return 0
```

Run: `$PYT -m pytest johnhull/web/py/tests -q`
Expected: `170 passed`.

- [ ] **Step 5: Write the spike page**

`johnhull/web/w0/index.html`:

```html
<!doctype html>
<html lang="ja">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>W0 spike — Pyodide + trees.py</title>
    <script type="module" src="./main.js"></script>
  </head>
  <body>
    <p id="status">loading</p>
  </body>
</html>
```

`johnhull/web/w0/boot.js`:

```js
// Pyodide + numpy + the browser package, shared by the worker and the main-thread timing mode.
export function createCalculator(resourceEntries) {
  const marks = {};
  let pyodide = null;
  let ready = null;

  async function boot() {
    const start = performance.now();
    const { loadPyodide } = await import("/pyodide/pyodide.mjs");
    pyodide = await loadPyodide({ indexURL: "/pyodide/" });
    marks.pyodide_ms = performance.now() - start;
    await pyodide.loadPackage("numpy", { messageCallback: () => {} });
    marks.numpy_ms = performance.now() - start;
    const response = await fetch("/pyodide/hullkit_browser.zip");
    if (!response.ok) throw new Error(`hullkit_browser.zip: HTTP ${response.status}`);
    pyodide.unpackArchive(await response.arrayBuffer(), "zip", { extractDir: "/home/pyodide/browser" });
    pyodide.runPython(
      'import sys\nsys.path.insert(0, "/home/pyodide/browser")\nfrom hull_web_calc.binomial import run as hull_run',
    );
    marks.package_ms = performance.now() - start;
    return pyodide.globals.get("hull_run");
  }

  return async function handle(type, request) {
    if (type === "info") return { marks, resources: resourceEntries() };
    ready ??= boot();
    const run = await ready;
    if (type === "scipy") {
      const start = performance.now();
      await pyodide.loadPackage("scipy", { messageCallback: () => {} });
      marks.scipy_ms = performance.now() - start;
      return "loaded";
    }
    return run(request);
  };
}
```

`johnhull/web/w0/worker.js`:

```js
// W0 spike worker: runs boot.js and reports CSP violations seen inside the worker.
import { createCalculator } from "./boot.js";

const handle = createCalculator(() =>
  performance.getEntriesByType("resource").map((entry) => ({ name: entry.name, transferSize: entry.transferSize })),
);

self.addEventListener("securitypolicyviolation", (event) => {
  self.postMessage({
    type: "violation",
    violation: { where: "worker", directive: event.effectiveDirective, blocked: event.blockedURI },
  });
});

self.onmessage = async (event) => {
  const { id, type, request } = event.data;
  try {
    self.postMessage({ id, type: "result", value: await handle(type, request) });
  } catch (error) {
    self.postMessage({ id, type: "failed", error: String(error?.stack ?? error) });
  }
};
```

`johnhull/web/w0/main.js`:

```js
// W0 spike page (spec §6 W0): hooks for scripts/w0_measure.mjs, no UI.
// /w0/ runs Pyodide in a module worker like the calculator; /w0/?main runs it on the page,
// because DevTools CPU throttling slows the page's main thread but not workers.
import { createCalculator } from "./boot.js";

const violations = [];
document.addEventListener("securitypolicyviolation", (event) => {
  violations.push({ where: "page", directive: event.effectiveDirective, blocked: event.blockedURI });
});

function workerCaller() {
  const worker = new Worker(new URL("./worker.js", import.meta.url), { type: "module" });
  const pending = new Map();
  let nextId = 1;
  worker.onmessage = (event) => {
    const message = event.data;
    if (message.type === "violation") {
      violations.push(message.violation);
      return;
    }
    const entry = pending.get(message.id);
    if (!entry) return;
    pending.delete(message.id);
    if (message.type === "result") entry.resolve(message.value);
    else entry.reject(new Error(message.error));
  };
  return (type, request = "") =>
    new Promise((resolve, reject) => {
      const id = nextId++;
      pending.set(id, { resolve, reject });
      worker.postMessage({ id, type, request });
    });
}

const mode = new URLSearchParams(location.search).has("main") ? "main" : "worker";
const call = mode === "main" ? createCalculator(() => []) : workerCaller();

window.__w0 = {
  mode,
  calc: (request) => call("run", request),
  loadScipy: () => call("scipy"),
  workerInfo: () => call("info"),
  violations,
};
document.getElementById("status").textContent = `ready (${mode})`;
```

- [ ] **Step 6: Write the measurement script**

`johnhull/web/scripts/w0_measure.mjs` (① package identity as served, ② golden and sweep comparisons, ③ bytes and time to the first result, ④ CSP, ⑤ every file served including `_` directories, ⑥ pretty URLs, anchors, search and the external-request census; spec §6 W0):

```js
// W0 measurements (spec §6 W0 ①–⑥) of build/w0-site served by `wrangler pages dev`.
// Run from the repository root after `python -m hull_web_build w0-site` and `... sweep`:
//   CHROMIUM_BIN=/home/kazumasa/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome \
//   node johnhull/web/scripts/w0_measure.mjs
// Writes $HULL_WEB_DATA/w0/results.json (default /home/kazumasa/projects/_data/johnhull/hull-web).
import { chromium } from "@playwright/test";
import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import { gzipSync } from "node:zlib";
import { compareJson } from "../tests/ulps.mts";

const require = createRequire(import.meta.url);
const WEB = path.resolve(import.meta.dirname, "..");
const SITE = path.join(WEB, "build", "w0-site");
const DATA = process.env.HULL_WEB_DATA ?? "/home/kazumasa/projects/_data/johnhull/hull-web";
const OUT = path.join(DATA, "w0");
const PORT = 8788;
const BASE = `http://127.0.0.1:${PORT}`;
const WRANGLER = "wrangler@4.147.0";

const sha256 = (data) => createHash("sha256").update(data).digest("hex");
const readJson = (file) => JSON.parse(readFileSync(file, "utf8"));
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const pins = readJson(path.join(WEB, "pins.json"));
const lock = readJson(path.join(WEB, "pyodide-lock.json"));
const golden = readJson(path.join(WEB, "tests", "golden.json")).cases;
const FIRST_REQUEST = golden.find((c) => c.name === "example:s13-1").request;

function siteFiles(dir = SITE, prefix = "") {
  const out = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const rel = `${prefix}${entry.name}`;
    if (entry.isDirectory()) out.push(...siteFiles(path.join(dir, entry.name), `${rel}/`));
    else out.push(rel);
  }
  return out.sort();
}

const urlFor = (rel) => `${BASE}/${rel.split("/").map(encodeURIComponent).join("/")}`;

function startServer() {
  const args = ["--yes", WRANGLER, "pages", "dev", SITE, "--ip", "127.0.0.1", "--port", String(PORT)];
  args.push("--compatibility-date", "2026-10-01");
  const env = { ...process.env, WRANGLER_SEND_METRICS: "false" };
  return spawn("npx", args, { env, stdio: "ignore", detached: true });
}

async function waitUntilUp() {
  for (let attempt = 0; attempt < 120; attempt++) {
    try {
      if ((await fetch(`${BASE}/`)).ok) return;
    } catch {
      // not up yet
    }
    await sleep(1000);
  }
  throw new Error("wrangler pages dev did not start");
}

async function openSpike(context, mount = "w0") {
  const page = await context.newPage();
  const response = await page.goto(`${BASE}/${mount}/`);
  await page.waitForFunction(() => window.__w0 !== undefined);
  return { page, response };
}

// ① the served browser package is the built one (member identity is tested in Python)
async function checkPackage() {
  const served = Buffer.from(await (await fetch(`${BASE}/pyodide/hullkit_browser.zip`)).arrayBuffer());
  const built = readFileSync(path.join(WEB, "build", "hullkit_browser.zip"));
  const manifest = readJson(path.join(WEB, "build", "hullkit_browser.manifest.json"));
  return { served_sha256: sha256(served), equal_to_build: sha256(served) === sha256(built), members: manifest.members };
}

// ② browser versus native, as exact text and as the largest ulp distance
async function compareCases(page, cases) {
  const summary = { cases: cases.length, identical_text: 0, max_ulps: 0, worst: null, ulps: {}, mismatches: [] };
  let scipy = false;
  for (const item of cases) {
    let op = null;
    try {
      op = JSON.parse(item.request).op;
    } catch {
      // the not-JSON edge case
    }
    if (op === "bsm" && !scipy) {
      await page.evaluate(() => window.__w0.loadScipy());
      scipy = true;
    }
    const got = await page.evaluate((request) => window.__w0.calc(request), item.request);
    if (got === item.response) {
      summary.identical_text += 1;
      summary.ulps[0] = (summary.ulps[0] ?? 0) + 1;
      continue;
    }
    const result = compareJson(JSON.parse(item.response), JSON.parse(got));
    if (result.mismatch !== null) {
      summary.mismatches.push({ name: item.name, where: result.where, mismatch: result.mismatch });
      continue;
    }
    summary.ulps[result.maxUlps] = (summary.ulps[result.maxUlps] ?? 0) + 1;
    if (result.maxUlps > summary.max_ulps) {
      summary.max_ulps = result.maxUlps;
      summary.worst = `${item.name} ${result.where}`;
    }
  }
  return summary;
}

async function transferred(page) {
  return page.evaluate(async () => {
    const pageEntries = [...performance.getEntriesByType("navigation"), ...performance.getEntriesByType("resource")];
    const { resources } = await window.__w0.workerInfo();
    return [...pageEntries.map((e) => ({ name: e.name, transferSize: e.transferSize })), ...resources];
  });
}

const total = (entries) => entries.reduce((sum, entry) => sum + entry.transferSize, 0);

// ③ load bytes and time to the first result (fresh context, so nothing is cached)
async function measureLoad(browser, { width, height, cpuSlowdown, mode }) {
  const context = await browser.newContext({ viewport: { width, height } });
  const page = await context.newPage();
  if (cpuSlowdown > 1) {
    const cdp = await context.newCDPSession(page);
    await cdp.send("Emulation.setCPUThrottlingRate", { rate: cpuSlowdown });
  }
  await page.goto(`${BASE}/w0/${mode === "main" ? "?main" : ""}`);
  await page.waitForFunction(() => window.__w0 !== undefined);
  const firstResultMs = await page.evaluate(async (request) => {
    await window.__w0.calc(request);
    return performance.now();
  }, FIRST_REQUEST);
  const first = await transferred(page);
  const scipyMs = await page.evaluate(async () => {
    const start = performance.now();
    await window.__w0.loadScipy();
    return performance.now() - start;
  });
  const withScipy = await transferred(page);
  const { marks } = await page.evaluate(() => window.__w0.workerInfo());
  await context.close();
  return {
    mode,
    width,
    cpu_slowdown: cpuSlowdown,
    first_result_ms: Math.round(firstResultMs),
    scipy_load_ms: Math.round(scipyMs),
    bytes_until_first_result: total(first),
    bytes_with_scipy: total(withScipy),
    worker_marks_ms: Object.fromEntries(Object.entries(marks).map(([k, v]) => [k, Math.round(v)])),
    largest: withScipy.sort((a, b) => b.transferSize - a.transferSize).slice(0, 8),
  };
}

// what a compressing server (real Pages) could send, for comparison with the local numbers
function referenceSizes() {
  const wheel = (name) => lock.packages[name].file_name;
  const groups = {
    first: [...Object.keys(pins.pyodide.core), "pyodide-lock.json", wheel("numpy"), "hullkit_browser.zip"],
    scipy: [wheel("scipy")],
  };
  return Object.fromEntries(
    Object.entries(groups).map(([group, names]) => {
      const blobs = names.map((name) => readFileSync(path.join(SITE, "pyodide", name)));
      const raw = blobs.reduce((sum, blob) => sum + blob.length, 0);
      const gzip = blobs.reduce((sum, blob) => sum + gzipSync(blob, { level: 9 }).length, 0);
      return [group, { files: names, raw_bytes: raw, gzip9_bytes: gzip }];
    }),
  );
}

// ④ which CSP the calculator needs: /w0/ has the strict policy, /w0-eval/ adds 'unsafe-eval'
async function checkCsp(browser, mount) {
  const context = await browser.newContext();
  const consoleCsp = [];
  context.on("console", (message) => {
    if (/Content Security Policy|Refused to/i.test(message.text())) consoleCsp.push(message.text());
  });
  const { page, response } = await openSpike(context, mount);
  const workerResponse = await fetch(`${BASE}/${mount}/worker.js`);
  let error = null;
  try {
    await page.evaluate((request) => window.__w0.calc(request), FIRST_REQUEST);
    await page.evaluate(() => window.__w0.loadScipy());
  } catch (caught) {
    error = String(caught);
  }
  const violations = await page.evaluate(() => window.__w0.violations);
  await context.close();
  return {
    mount,
    document_csp: response.headers()["content-security-policy"] ?? null,
    worker_csp: workerResponse.headers.get("content-security-policy"),
    pyodide_numpy_scipy_ok: error === null,
    error,
    violations,
    console_messages: consoleCsp,
  };
}

// ⑤ every file is served with its bytes, including under _build, _static, _images, ...
async function checkFiles() {
  const result = { checked: 0, ok: 0, redirected: 0, underscore_dirs: {}, failures: [] };
  for (const rel of siteFiles()) {
    if (rel === "_headers" || rel === "404.html") continue;
    let url = urlFor(rel);
    let response = await fetch(url, { redirect: "manual" });
    if ([301, 302, 303, 307, 308].includes(response.status)) {
      result.redirected += 1;
      url = new URL(response.headers.get("location"), url).href;
      response = await fetch(url, { redirect: "manual" });
    }
    const body = Buffer.from(await response.arrayBuffer());
    result.checked += 1;
    if (response.status === 200 && sha256(body) === sha256(readFileSync(path.join(SITE, rel)))) {
      result.ok += 1;
      for (const dir of new Set(rel.split("/").slice(0, -1).filter((part) => part.startsWith("_")))) {
        result.underscore_dirs[dir] = (result.underscore_dirs[dir] ?? 0) + 1;
      }
    } else {
      result.failures.push({ rel, status: response.status, url });
    }
  }
  return result;
}

async function checkStatuses() {
  const expected = {
    "/no-such-page": 404,
    "/book/_build/html/_sources/": 404,
    "/book/_build/html/.buildinfo": 404,
    "/book/_build/html/notebooks/01_foundations": 200,
  };
  const out = {};
  for (const [route, want] of Object.entries(expected)) {
    const status = (await fetch(`${BASE}${route}`, { redirect: "manual" })).status;
    out[route] = { status, expected: want, ok: status === want };
  }
  return out;
}

// Two section ids of the loaded page (the Book on main has no cross-page anchors yet;
// the reading guide will link to sections like these through `<page>.html#<id>`).
async function sectionIds(page) {
  const read = () => page.$$eval("section[id]", (elements) => elements.slice(1, 3).map((element) => element.id));
  try {
    return await read();
  } catch {
    await page.waitForLoadState("load");
    return read();
  }
}

// ⑥ pretty URLs in the browser: every page, cross-page anchors, search; plus the external-request census
async function crawl(browser) {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();
  const external = [];
  await context.route("**/*", (route) => {
    const url = new URL(route.request().url());
    if (url.hostname === "127.0.0.1") return route.continue();
    external.push({ page: new URL(page.url()).pathname, url: `${url.hostname}${url.pathname}` });
    return route.abort();
  });
  const failures = [];
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push({ page: page.url(), error: String(error) }));
  page.on("response", (response) => {
    if (response.status() >= 400 && new URL(response.url()).hostname === "127.0.0.1") {
      failures.push({ page: page.url(), url: response.url(), status: response.status() });
    }
  });
  const pages = siteFiles().filter(
    (rel) => rel.endsWith(".html") && /^(book|report)\//.test(rel) && !rel.includes("/_static/"),
  );
  const navigation = { pages: pages.length, ok: 0, bad: [] };
  const anchors = { checked: 0, ok: 0, bad: [] };
  for (const rel of pages) {
    const response = await page.goto(urlFor(rel));
    if (response?.status() === 200) navigation.ok += 1;
    else navigation.bad.push({ rel, status: response?.status() ?? null });
    if (!rel.startsWith("book/")) continue;
    // index.html is a meta-refresh stub: wait until the page it forwards to has loaded
    await page.waitForLoadState("load");
    for (const id of await sectionIds(page)) {
      anchors.checked += 1;
      const hash = `#${encodeURIComponent(id)}`;
      await page.goto(`${urlFor(rel)}${hash}`);
      const found = await page.evaluate((target) => document.getElementById(target) !== null, id);
      if (new URL(page.url()).hash === hash && found) anchors.ok += 1;
      else anchors.bad.push({ from: rel, id, landed: page.url(), found });
    }
  }
  const search = { query: "CRR", results: 0, first_result_status: null, error: null };
  try {
    await page.goto(`${BASE}/book/_build/html/search.html?q=CRR`);
    const results = page.locator("#search-results ul.search li a");
    await results.first().waitFor({ timeout: 30_000 });
    search.results = await results.count();
    const [response] = await Promise.all([page.waitForNavigation(), results.first().click()]);
    search.first_result_status = response?.status() ?? null;
  } catch (error) {
    search.error = String(error);
  }
  await context.close();
  const hosts = {};
  for (const item of external) hosts[item.url.split("/")[0]] = (hosts[item.url.split("/")[0]] ?? 0) + 1;
  const pagesWithExternal = [...new Set(external.map((item) => item.page))];
  return { navigation, anchors, search, subresource_failures: failures, page_errors: pageErrors, external_hosts: hosts, pages_with_external: pagesWithExternal };
}

const results = { measured_at: new Date().toISOString() };
mkdirSync(OUT, { recursive: true });
const server = startServer();
try {
  await waitUntilUp();
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_BIN, args: ["--no-sandbox"] });
  try {
    results.environment = {
      node: process.version,
      chromium: browser.version(),
      playwright: require("@playwright/test/package.json").version,
      wrangler: WRANGLER,
      pyodide: pins.pyodide.version,
    };
    results.package = await checkPackage();
    const context = await browser.newContext();
    const { page } = await openSpike(context);
    results.golden = await compareCases(page, golden);
    const sweepPath = path.join(WEB, "build", "w0-sweep.json");
    if (existsSync(sweepPath)) results.sweep = await compareCases(page, readJson(sweepPath).cases);
    await context.close();
    results.load = [
      await measureLoad(browser, { width: 390, height: 844, cpuSlowdown: 4, mode: "main" }),
      await measureLoad(browser, { width: 390, height: 844, cpuSlowdown: 1, mode: "main" }),
      await measureLoad(browser, { width: 1280, height: 900, cpuSlowdown: 1, mode: "worker" }),
    ];
    results.reference_sizes = referenceSizes();
    results.csp = [await checkCsp(browser, "w0"), await checkCsp(browser, "w0-eval")];
    results.files = await checkFiles();
    results.statuses = await checkStatuses();
    results.crawl = await crawl(browser);
  } finally {
    await browser.close();
  }
} finally {
  process.kill(-server.pid, "SIGTERM");
}
writeFileSync(path.join(OUT, "results.json"), `${JSON.stringify(results, null, 2)}\n`);
const c = results.crawl;
console.log(`① package served = built: ${results.package.equal_to_build}`);
console.log(`② golden: ${results.golden.identical_text}/${results.golden.cases} identical text, max ${results.golden.max_ulps} ulp (${results.golden.worst}), mismatches ${results.golden.mismatches.length}`);
if (results.sweep) console.log(`   sweep: ${results.sweep.identical_text}/${results.sweep.cases} identical text, max ${results.sweep.max_ulps} ulp, mismatches ${results.sweep.mismatches.length}`);
for (const load of results.load) console.log(`③ ${load.mode} ${load.width}px x${load.cpu_slowdown}: first result ${load.first_result_ms} ms, ${load.bytes_until_first_result} B; +scipy ${load.scipy_load_ms} ms, ${load.bytes_with_scipy} B`);
for (const csp of results.csp) console.log(`④ ${csp.mount}: ok=${csp.pyodide_numpy_scipy_ok} violations=${csp.violations.length} console=${csp.console_messages.length}`);
console.log(`⑤ files ${results.files.ok}/${results.files.checked} served (${results.files.redirected} via redirect), underscore dirs ${JSON.stringify(results.files.underscore_dirs)}`);
console.log(`   statuses ${JSON.stringify(Object.fromEntries(Object.entries(results.statuses).map(([k, v]) => [k, v.status])))}`);
console.log(`⑥ pages ${c.navigation.ok}/${c.navigation.pages}, anchors ${c.anchors.ok}/${c.anchors.checked}, search ${c.search.results} results -> ${c.search.first_result_status}, subresource failures ${c.subresource_failures.length}, page errors ${c.page_errors.length}`);
console.log(`   external hosts ${JSON.stringify(c.external_hosts)} on ${c.pages_with_external.length} pages`);
console.log(`results: ${path.join(OUT, "results.json")}`);
```

- [ ] **Step 7: Build the W0 site**

The Book and the report must be built in the worktree first (they are not in Git). In the worktree, run their builders with the shared venv instead of `make`:

```bash
/home/kazumasa/projects/.venv/bin/jupyter-book build johnhull/book/ > $HULL_WEB_DATA/book-build.log 2>&1; tail -2 $HULL_WEB_DATA/book-build.log
PYTHONPATH=johnhull/hullkit/src:johnhull/report $PY -m report_builder.build
PYTHONPATH=johnhull/hullkit/src $PY johnhull/scripts/build_chapter01_portal.py
for s in fast_acceptance fast_acceptance_options fast_acceptance_advanced_options fast_acceptance_risk_credit fast_acceptance_final; do
  PYTHONPATH=johnhull/hullkit/src $PY johnhull/scripts/$s.py build
done
ls johnhull/book/_build/html/index.html johnhull/report/site/index.html
git status --short johnhull/report johnhull/book
```

These are the commands of `make hull-book` and `make hull-report` with the shared venv in place of `uv run --no-sync`.
Expected: both `index.html` files exist. `git status` may list `johnhull/report/site/chapters/ch29.html`…`ch37.html` as modified: those nine generated pages are tracked although `site/` is ignored. Never commit them on this branch; mention in the report whether they changed.

Then build the spike site:

```bash
$PYT -m hull_web_build package > /dev/null
$PYT -m hull_web_build golden --check
$PYT -m hull_web_build sweep
$PYT -m hull_web_build w0-site
```

Expected: `golden --check` prints nothing and exits 0; `sweep` prints `wrote …/johnhull/web/build/w0-sweep.json`; `w0-site` prints `{"files": …, "bytes": …}` (plan check: 507 files, about 117.5 MB).

- [ ] **Step 8: Run the measurement**

Run: `node johnhull/web/scripts/w0_measure.mjs`
Expected (plan check values; ③ depends on the machine, and ⑤⑥ counts depend on the Book and report at the time):

```text
① package served = built: true
② golden: 41/42 identical text, max 1 ulp (edge:convergence-arbitrage-gaps $.prices[17]), mismatches 0
   sweep: 291/300 identical text, max 20 ulp, mismatches 0
③ main 390px x4: first result 9025 ms, 9434895 B; +scipy 5197 ms, 23464945 B
③ main 390px x1: first result 2031 ms, 9434895 B; +scipy 1133 ms, 23464945 B
③ worker 1280px x1: first result 2046 ms, 9435934 B; +scipy 1075 ms, 23465984 B
④ w0: ok=true violations=0 console=0
④ w0-eval: ok=true violations=0 console=0
⑤ files 505/505 served (88 via redirect), underscore dirs {"_build":437,"_images":252,"_sphinx_design_static":2,"_static":147}
   statuses {"/no-such-page":404,"/book/_build/html/_sources/":404,"/book/_build/html/.buildinfo":404,"/book/_build/html/notebooks/01_foundations":200}
⑥ pages 83/83, anchors 62/62, search 5 results -> 200, subresource failures 0, page errors 0
   external hosts {"cdn.jsdelivr.net":33} on 33 pages
```

Any `mismatches` above 0 in ②, `ok=false` or a violation for `w0` in ④, a file not served in ⑤, or a failed page, anchor or search in ⑥ is a finding for the report, not something to fix silently.

- [ ] **Step 9: Record the results**

```bash
mkdir -p johnhull/docs/validation/hull-web
cp $HULL_WEB_DATA/w0/results.json johnhull/docs/validation/hull-web/w0.json
```

Write `johnhull/web/tests/tolerance.json`, copying the numbers from `w0.json` (`golden.max_ulps`, `golden.worst`, `sweep.max_ulps`, `measured_at`):

```json
{
  "max_ulps": 1,
  "about": "Largest ulp distance between browser and native responses over tests/golden.json, measured in W0 (johnhull/docs/validation/hull-web/w0.json); not widened (spec §5).",
  "measured_at": "2026-10-19T00:00:00.000Z",
  "golden_worst": "edge:convergence-arbitrage-gaps $.prices[17]",
  "sweep_max_ulps": 20
}
```

(The values shown are the plan check's; write yours.)

Write `johnhull/docs/validation/hull-web/W0_REPORT.md` in Japanese with exactly these sections, every number copied from `w0.json`:

```markdown
# ウェブアプリ W0（試作と実測）の結果

- 実施：<measured_at の日付>、branch `codex/hull-web`
- 環境：Node <environment.node>、Chromium <environment.chromium>、Playwright <environment.playwright>、wrangler 4.147.0（`pages dev`）、Pyodide 314.0.7
- 生データ：[w0.json](w0.json)

## 設計 §6 W0 の6項目

| 項目 | 結果 | 設計を変える必要 |
|---|---|---|
| ① パッケージがバイト単位で一致 | 配信された zip と組み立てた zip が同じ（package.equal_to_build）。各モジュールの一致は test_package.py | なし／あり（理由） |
| ② 計算結果の一致 | golden：identical_text/cases が文字列で同一、最大 max_ulps ulp（worst）、構造の不一致 mismatches 件。乱数 300 件：identical_text/300、最大 max_ulps ulp、分布 ulps | |
| ③ 読み込み量と時間 | 最初の計算まで bytes_until_first_result B（wrangler の圧縮後）、gzip -9 の参考値 reference_sizes.first.gzip9_bytes B。scipy を足すと bytes_with_scipy B。390px・CPU 4 倍遅い・主スレッド：first_result_ms ms、scipy scipy_load_ms ms。等速：…。Worker・1280px：… | |
| ④ 必要な CSP | script-src 'self' 'wasm-unsafe-eval' で Pyodide・numpy・scipy が動くか（csp[0].pyodide_numpy_scipy_ok、違反 件数）。'unsafe-eval' の要否 | |
| ⑤ `_` で始まるディレクトリ | files.ok/files.checked をバイト一致で配信（転送 files.redirected 件）。underscore_dirs | |
| ⑥ pretty URL の転送 | ページ navigation.ok/pages、アンカー anchors.ok/checked、検索「CRR」results 件 → first_result_status、ページエラー 件数、外部通信 external_hosts（pages_with_external の件数 ページ） | |

## 許容誤差の提案

tests/tolerance.json の max_ulps を golden の最大値とする。理由と、乱数 300 件の分布との関係。

## 目標値（本人と決める）

③ の実測値と、目標値の案（決めるのは本人）。

## 設計を変える必要があるか

項目ごとの結論。補足教材の MathJax（計画 D-6）を含む。

## 気づいたこと
```

- [ ] **Step 10: Record the end of W0 in the ROADMAP**

Set the status (Task 1, Step 10) to

```text
2026-10-18 設計、ユーザー承認。2026-10-19 実装計画。W0 完了（DATE、[W0 報告](docs/validation/hull-web/W0_REPORT.md)）。W1 は本人と Claude の確認待ち、branch `codex/hull-web`
```

and in the 「完了までの計画」 line add `、完了 DATE` after the W0 start date, so it reads `W0 試作と実測（タスク1〜5、着手 <Task 1 date>、完了 DATE）`.

- [ ] **Step 11: Lint and commit**

Run: `$PY -m ruff check johnhull/web/py && $PY -m ruff format --check johnhull/web/py && node --test johnhull/web/tests/ulps.test.mts`
Expected: `All checks passed!`, `19 files already formatted`, `ℹ pass 4`.

```bash
git add johnhull/web/tests/ulps.mts johnhull/web/tests/ulps.test.mts johnhull/web/tests/tolerance.json \
  johnhull/web/py/hull_web_build/site.py johnhull/web/py/hull_web_build/cli.py johnhull/web/py/tests/test_site.py \
  johnhull/web/w0 johnhull/web/scripts/w0_measure.mjs johnhull/docs/validation/hull-web johnhull/ROADMAP.md
git commit -m "Record the W0 spike: package identity, browser-native ulps, load, CSP, Pages routing"
```

- [ ] **Step 12: STOP and report**

Do not start Task 6. Tell the owner (and Claude) the path of `W0_REPORT.md`, the six results in one line each, the proposed `max_ulps`, and whether any design change is needed (spec §8: 「W0 の結果を報告したら止める」). Continue only when the owner says so; if the review changes the tolerance or the design, apply that first and record it in the ledger.

---

### Task 6: W1 begins — protocol types and the calculator's pure modules

**Files:**
- Modify: `johnhull/web/package.json` (the app's packages), `johnhull/web/pnpm-lock.yaml` (pnpm), `johnhull/ROADMAP.md`
- Create: `johnhull/web/tsconfig.json`, `johnhull/web/src/calc/protocol.ts`
- Create: `src/calc/format.ts`, `params.ts`, `checks.ts`, `messages.ts`, `layout.ts`
- Test: `src/calc/format.test.ts`, `params.test.ts`, `checks.test.ts`, `messages.test.ts`, `layout.test.ts`

**Interfaces:**
- Consumes: `src/calc/examples.json` and `tests/golden.json` (Task 4).
- Produces (`protocol.ts`): `TreeKind`, `Asset`, `OptionKind`, `Op`, `Contract`, `CalcRequest`, `Params`, `TreeNodes`, `PriceResult`, `ConvergenceResult`, `BsmResult`, `CalcError`, `ErrorResult`, `Stage = "idle" | "pyodide" | "numpy" | "package" | "scipy" | "ready"`, `ToWorker {id, request}`, `FromWorker` (`stage` | `result` | `failed` with `stage: "load" | "run"`).
- Produces: `format.ts` `formatValue(x, digits = 6)`, `formatDiff(x)`, `percentHint(text)`; `params.ts` `MAX_STEPS`, `FormState`, `NumberField`, `FieldErrors`, `ExampleRequest`, `MESSAGES`, `DEFAULT_FORM` (§13.10, n = 5), `visibleFields(form)`, `parseForm(form) -> {ok: true, contract} | {ok: false, errors}`, `formFromRequest(request, base)`; `checks.ts` `Check`, `Example`, `quantityValue(quantity, price, bsm)`, `passes(check, value)`, `quantityLabel(quantity)`, `needsBsm(example)`; `messages.ts` `STAGE_TEXT`, `describeError(error)`; `layout.ts` `BOX`, `treeLayout(n)`, `chartLayout(steps, prices, bsm, digits = 4)`.

- [ ] **Step 1: Record the start of W1 in the ROADMAP**

Set the status (Task 1, Step 10) to the Task 5 text with `W1 は本人と Claude の確認待ち` replaced by `W1 作業中`, and in the 「完了までの計画」 line replace `W1 二項木の計算機とサイトの組み立て（タスク6〜11）` with `W1 二項木の計算機とサイトの組み立て（タスク6〜11、着手 DATE）`.

- [ ] **Step 2: Add the app's packages**

Replace `johnhull/web/package.json` with:

```json
{
  "name": "hull-web",
  "private": true,
  "type": "module",
  "scripts": {
    "build": "vite build",
    "typecheck": "tsc -p tsconfig.json",
    "test:unit": "node --test \"src/**/*.test.ts\" \"sw/*.test.mjs\" \"tests/*.test.mts\"",
    "test:browser": "playwright test"
  },
  "dependencies": {
    "react": "19.3.0",
    "react-dom": "19.3.0"
  },
  "devDependencies": {
    "@playwright/test": "1.56.0",
    "@types/node": "26.6.4",
    "@types/react": "19.3.0",
    "@types/react-dom": "19.3.0",
    "@vitejs/plugin-react": "6.1.2",
    "typescript": "6.0.3",
    "vite": "8.3.2"
  }
}
```

Run: `$PNPM install --ignore-scripts`
Expected: the lockfile now lists `react 19.3.0`, `react-dom 19.3.0`, `@types/node 26.6.4`, `@types/react 19.3.0`, `@types/react-dom 19.3.0`, `@vitejs/plugin-react 6.1.2`, `typescript 6.0.3`, `vite 8.3.2`, `@playwright/test 1.56.0`.

`johnhull/web/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2023",
    "lib": ["ES2023", "DOM"],
    "module": "preserve",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noEmit": true,
    "allowImportingTsExtensions": true,
    "verbatimModuleSyntax": true,
    "erasableSyntaxOnly": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "skipLibCheck": true,
    "types": ["node"]
  },
  "include": ["src", "tests", "vite.config.ts", "playwright.config.ts"]
}
```

`johnhull/web/src/calc/protocol.ts` (types only; the shapes of the calculator contract above):

```ts
// Shapes of the JSON texts exchanged with hull_web_calc.binomial.run and the Web Worker.

export type TreeKind = "crr" | "ud";
export type Asset = "stock" | "index" | "currency" | "futures";
export type OptionKind = "call" | "put";
export type Op = "price" | "convergence" | "bsm";

export interface Contract {
  tree: TreeKind;
  asset: Asset;
  kind: OptionKind;
  american: boolean;
  S0: number;
  K: number;
  r: number;
  q: number;
  T: number;
  n: number;
  sigma?: number;
  u?: number;
  d?: number;
}

export interface CalcRequest extends Contract {
  op: Op;
}

export interface Params {
  dt: number;
  u: number;
  d: number;
  a: number;
  p: number;
  q: number;
}

export interface TreeNodes {
  stock: number[][];
  option: number[][];
  delta: number[][];
  exercise: boolean[][];
}

export interface PriceResult {
  ok: true;
  price: number;
  params: Params;
  tree: TreeNodes | null;
}

export interface ConvergenceResult {
  ok: true;
  steps: number[];
  prices: (number | null)[];
}

export interface BsmResult {
  ok: true;
  bsm: number;
}

export type CalcError =
  | { code: "input"; field: string; reason: string }
  | { code: "arbitrage"; a: number; u: number; d: number; p: number }
  | { code: "nonfinite" };

export interface ErrorResult {
  ok: false;
  error: CalcError;
}

export type Stage = "idle" | "pyodide" | "numpy" | "package" | "scipy" | "ready";

export interface ToWorker {
  id: number;
  request: string;
}

export type FromWorker =
  | { type: "stage"; stage: Stage }
  | { type: "result"; id: number; text: string }
  | { type: "failed"; id: number; stage: "load" | "run"; message: string };
```

- [ ] **Step 3: Formatting — test, fail, implement, pass**

`johnhull/web/src/calc/format.test.ts`:

```ts
import assert from "node:assert/strict";
import { test } from "node:test";
import { formatDiff, formatValue, percentHint } from "./format.ts";

test("formatValue keeps six significant digits without trailing zeros", () => {
  assert.equal(formatValue(7.428401902704835), "7.4284");
  assert.equal(formatValue(989.3398), "989.34");
  assert.equal(formatValue(0.018880123), "0.0188801");
  assert.equal(formatValue(-0.46060612177263727), "-0.460606");
  assert.equal(formatValue(0), "0");
  assert.equal(formatValue(0.5502509, 8), "0.5502509");
});

test("formatDiff uses one decimal of scientific notation", () => {
  assert.equal(formatDiff(0.00043), "4.3e-4");
  assert.equal(formatDiff(0), "0");
});

test("percentHint reads a decimal rate as a percentage", () => {
  assert.equal(percentHint("0.05"), "= 5%");
  assert.equal(percentHint("0.125"), "= 12.5%");
  assert.equal(percentHint(""), "");
  assert.equal(percentHint("abc"), "");
});
```

Run: `node --test johnhull/web/src/calc/format.test.ts`
Expected: FAIL, `ERR_MODULE_NOT_FOUND` for `format.ts`.

`johnhull/web/src/calc/format.ts`:

```ts
// Display formatting only; checks and comparisons always use the full doubles.

export function formatValue(x: number, digits = 6): string {
  if (!Number.isFinite(x)) return String(x);
  return String(Number(x.toPrecision(digits)));
}

export function formatDiff(x: number): string {
  return x === 0 ? "0" : x.toExponential(1);
}

export function percentHint(text: string): string {
  const value = Number(text.trim());
  if (text.trim() === "" || !Number.isFinite(value)) return "";
  return `= ${formatValue(value * 100)}%`;
}
```

Run: `node --test johnhull/web/src/calc/format.test.ts`
Expected: `ℹ pass 3`.

- [ ] **Step 4: Form parsing — test, fail, implement, pass**

`johnhull/web/src/calc/params.test.ts` (includes Review Focus 1):

```ts
import assert from "node:assert/strict";
import { test } from "node:test";
import data from "./examples.json" with { type: "json" };
import { DEFAULT_FORM, type ExampleRequest, formFromRequest, MESSAGES, parseForm, visibleFields } from "./params.ts";

test("the default form is Hull §13.10 and parses", () => {
  const parsed = parseForm(DEFAULT_FORM);
  assert.ok(parsed.ok);
  assert.deepEqual(parsed.contract, {
    tree: "crr",
    asset: "stock",
    kind: "put",
    american: true,
    S0: 50,
    K: 52,
    r: 0.05,
    q: 0,
    T: 2,
    n: 5,
    sigma: 0.3,
  });
});

test("every example button fills in exactly the doubles of its golden request", () => {
  for (const example of data.examples) {
    const request = example.request as ExampleRequest;
    const parsed = parseForm(formFromRequest(request, DEFAULT_FORM));
    assert.ok(parsed.ok, example.id);
    const { op, ...contract } = request;
    assert.equal(op, "price");
    assert.deepEqual(parsed.contract, contract, example.id);
  }
});

test("fields follow the tree and the asset", () => {
  assert.deepEqual(visibleFields({ tree: "crr", asset: "stock" }), ["S0", "K", "r", "sigma", "T", "n"]);
  assert.deepEqual(visibleFields({ tree: "ud", asset: "currency" }), ["S0", "K", "r", "q", "u", "d", "T", "n"]);
});

test("steps must be an integer from 1 to 500", () => {
  for (const n of ["0", "501", "2.5", "", "-1", "1e2"]) {
    const parsed = parseForm({ ...DEFAULT_FORM, n });
    assert.ok(!parsed.ok && parsed.errors.n === MESSAGES.steps, n);
  }
  assert.ok(parseForm({ ...DEFAULT_FORM, n: "500" }).ok);
});

test("prices, strike, volatility and maturity must be positive numbers", () => {
  for (const field of ["S0", "K", "sigma", "T"] as const) {
    const zero = parseForm({ ...DEFAULT_FORM, [field]: "0" });
    assert.ok(!zero.ok && zero.errors[field] === MESSAGES.positive, field);
    const text = parseForm({ ...DEFAULT_FORM, [field]: "abc" });
    assert.ok(!text.ok && text.errors[field] === MESSAGES.number, field);
  }
});

test("rates may be zero or negative but must be numbers", () => {
  assert.ok(parseForm({ ...DEFAULT_FORM, r: "-0.01" }).ok);
  const hex = parseForm({ ...DEFAULT_FORM, r: "0x10" });
  assert.ok(!hex.ok && hex.errors.r === MESSAGES.number);
});

test("full-width digits from a Japanese keyboard are accepted", () => {
  const parsed = parseForm({ ...DEFAULT_FORM, S0: "５０．５", n: "１０" });
  assert.ok(parsed.ok);
  assert.equal(parsed.contract.S0, 50.5);
  assert.equal(parsed.contract.n, 10);
});

test("a percent sign or a decimal comma is refused, not guessed; spaces are trimmed", () => {
  for (const r of ["5%", "0,05"]) {
    const parsed = parseForm({ ...DEFAULT_FORM, r });
    assert.ok(!parsed.ok && parsed.errors.r === MESSAGES.number, r);
  }
  const spaced = parseForm({ ...DEFAULT_FORM, r: " 0.05 " });
  assert.ok(spaced.ok && spaced.contract.r === 0.05);
});

test("a u/d tree needs d below u", () => {
  const parsed = parseForm({ ...DEFAULT_FORM, tree: "ud", u: "0.9", d: "1.1" });
  assert.ok(!parsed.ok && parsed.errors.d === MESSAGES.dBelowU);
});

test("q is sent only for an index or a currency", () => {
  const stock = parseForm({ ...DEFAULT_FORM, q: "0.5" });
  assert.ok(stock.ok && stock.contract.q === 0);
  const index = parseForm({ ...DEFAULT_FORM, asset: "index", q: "0.02" });
  assert.ok(index.ok && index.contract.q === 0.02);
});
```

Run: `node --test johnhull/web/src/calc/params.test.ts`
Expected: FAIL, `ERR_MODULE_NOT_FOUND` for `params.ts`.

`johnhull/web/src/calc/params.ts`:

```ts
// Form state <-> calculator contract. Validation here gives immediate messages;
// hull_web_calc.binomial.run checks everything again.
import type { Asset, Contract, OptionKind, TreeKind } from "./protocol.ts";

export const MAX_STEPS = 500;

export interface FormState {
  tree: TreeKind;
  asset: Asset;
  kind: OptionKind;
  american: boolean;
  S0: string;
  K: string;
  r: string;
  q: string;
  sigma: string;
  u: string;
  d: string;
  T: string;
  n: string;
}

export type NumberField = "S0" | "K" | "r" | "q" | "sigma" | "u" | "d" | "T" | "n";
export type FieldErrors = Partial<Record<NumberField, string>>;
export type Parsed = { ok: true; contract: Contract } | { ok: false; errors: FieldErrors };

export interface ExampleRequest extends Contract {
  op: "price";
}

export const MESSAGES = {
  number: "数値を入れてください",
  positive: "0 より大きい値を入れてください",
  steps: `1 から ${MAX_STEPS} までの整数を入れてください`,
  dBelowU: "d は u より小さくしてください",
} as const;

// Hull 11e GE §13.10: S0 = 50, K = 52, r = 5%, sigma = 30%, T = 2, American put.
export const DEFAULT_FORM: FormState = {
  tree: "crr",
  asset: "stock",
  kind: "put",
  american: true,
  S0: "50",
  K: "52",
  r: "0.05",
  q: "0",
  sigma: "0.3",
  u: "1.2",
  d: "0.8",
  T: "2",
  n: "5",
};

const DECIMAL = /^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/;
const INTEGER = /^\d+$/;

export function visibleFields(form: Pick<FormState, "tree" | "asset">): NumberField[] {
  const fields: NumberField[] = ["S0", "K", "r"];
  if (form.asset === "index" || form.asset === "currency") fields.push("q");
  if (form.tree === "crr") fields.push("sigma");
  else fields.push("u", "d");
  fields.push("T", "n");
  return fields;
}

function normalize(text: string): string {
  return text.normalize("NFKC").trim();
}

export function parseForm(form: FormState): Parsed {
  const errors: FieldErrors = {};
  const values: Partial<Record<NumberField, number>> = {};
  for (const field of visibleFields(form)) {
    const text = normalize(form[field]);
    if (field === "n") {
      const n = INTEGER.test(text) ? Number(text) : Number.NaN;
      if (n >= 1 && n <= MAX_STEPS) values.n = n;
      else errors.n = MESSAGES.steps;
      continue;
    }
    const value = DECIMAL.test(text) ? Number(text) : Number.NaN;
    if (!Number.isFinite(value)) errors[field] = MESSAGES.number;
    else if (field !== "r" && field !== "q" && !(value > 0)) errors[field] = MESSAGES.positive;
    else values[field] = value;
  }
  if (form.tree === "ud" && values.u !== undefined && values.d !== undefined && !(values.d < values.u)) {
    errors.d = MESSAGES.dBelowU;
  }
  if (Object.keys(errors).length > 0) return { ok: false, errors };
  const contract: Contract = {
    tree: form.tree,
    asset: form.asset,
    kind: form.kind,
    american: form.american,
    S0: values.S0 as number,
    K: values.K as number,
    r: values.r as number,
    q: values.q ?? 0,
    T: values.T as number,
    n: values.n as number,
  };
  if (form.tree === "crr") contract.sigma = values.sigma as number;
  else {
    contract.u = values.u as number;
    contract.d = values.d as number;
  }
  return { ok: true, contract };
}

export function formFromRequest(request: ExampleRequest, base: FormState): FormState {
  return {
    ...base,
    tree: request.tree,
    asset: request.asset,
    kind: request.kind,
    american: request.american,
    S0: String(request.S0),
    K: String(request.K),
    r: String(request.r),
    q: String(request.q),
    T: String(request.T),
    n: String(request.n),
    sigma: request.sigma === undefined ? base.sigma : String(request.sigma),
    u: request.u === undefined ? base.u : String(request.u),
    d: request.d === undefined ? base.d : String(request.d),
  };
}
```

Run: `node --test johnhull/web/src/calc/params.test.ts`
Expected: `ℹ pass 10`.

- [ ] **Step 5: Example checks — test, fail, implement, pass**

`johnhull/web/src/calc/checks.test.ts` (runs every example's checks on the golden native responses, so the TypeScript comparison agrees with `examples.passes`):

```ts
import assert from "node:assert/strict";
import { test } from "node:test";
import golden from "../../tests/golden.json" with { type: "json" };
import { type Check, type Example, needsBsm, passes, quantityLabel, quantityValue } from "./checks.ts";
import data from "./examples.json" with { type: "json" };
import type { PriceResult } from "./protocol.ts";

const examples = data.examples as Example[];
const responses = new Map(golden.cases.map((c) => [c.name, JSON.parse(c.response)]));

test("every example passes its checks on the golden (native) responses", () => {
  for (const example of examples) {
    const price = responses.get(`example:${example.id}`) as PriceResult;
    const bsm = needsBsm(example) ? (responses.get(`example:${example.id}:bsm`).bsm as number) : null;
    for (const check of example.checks) {
      const value = quantityValue(check.quantity, price, bsm);
      assert.ok(value !== null && passes(check, value), `${example.id} ${check.quantity}`);
    }
  }
});

test("allclose adds numpy's default rtol, approx does not", () => {
  const base: Check = { quantity: "price", expected: "100", tol: "0", rule: "approx", source: "", printed: null, note: null };
  assert.equal(passes(base, 100 + 0.9e-5), false);
  assert.equal(passes({ ...base, rule: "allclose" }, 100 + 0.9e-5), true);
});

test("quantities read params, nodes and the BSM value", () => {
  const price: PriceResult = {
    ok: true,
    price: 1,
    params: { dt: 1, u: 2, d: 0.5, a: 1, p: 0.5, q: 0 },
    tree: { stock: [[1], [2, 0.5]], option: [[1], [3, 0]], delta: [[2]], exercise: [[false]] },
  };
  assert.equal(quantityValue("u", price, null), 2);
  assert.equal(quantityValue("stock[1][1]", price, null), 0.5);
  assert.equal(quantityValue("delta[0][0]", price, null), 2);
  assert.equal(quantityValue("bsm", price, 7), 7);
  assert.equal(quantityValue("stock[5][0]", price, null), null);
});

test("labels name nodes the way the tree diagram does", () => {
  assert.equal(quantityLabel("stock[2][1]"), "株価 S(2, 1)");
  assert.equal(quantityLabel("delta[0][0]"), "デルタ Δ(0, 0)");
  assert.equal(quantityLabel("price"), "価格");
});
```

Run: `node --test johnhull/web/src/calc/checks.test.ts`
Expected: FAIL, `ERR_MODULE_NOT_FOUND` for `checks.ts`.

`johnhull/web/src/calc/checks.ts`:

```ts
// Example checks: read a quantity from a result and compare it the way the pinned test does
// (see johnhull/web/py/hull_web_build/examples.py).
import type { ExampleRequest } from "./params.ts";
import type { Params, PriceResult } from "./protocol.ts";

export interface Check {
  quantity: string;
  expected: string;
  tol: string;
  rule: "approx" | "allclose";
  source: string;
  printed: string | null;
  note: string | null;
}

export interface Example {
  id: string;
  label: string;
  request: ExampleRequest;
  checks: Check[];
}

const PARAMS = new Set(["dt", "u", "d", "a", "p", "q"]);
const NODE = /^(stock|option|delta)\[(\d+)\]\[(\d+)\]$/;
const NODE_LABELS = { stock: "株価 S", option: "オプション価値 f", delta: "デルタ Δ" } as const;

export function quantityValue(quantity: string, price: PriceResult, bsm: number | null): number | null {
  if (quantity === "price") return price.price;
  if (quantity === "bsm") return bsm;
  if (PARAMS.has(quantity)) return price.params[quantity as keyof Params];
  const match = NODE.exec(quantity);
  if (!match || !price.tree) return null;
  const level = price.tree[match[1] as keyof typeof NODE_LABELS][Number(match[2])];
  return level?.[Number(match[3])] ?? null;
}

export function passes(check: Check, value: number): boolean {
  const expected = Number(check.expected);
  const tol = Number(check.tol);
  const bound = check.rule === "allclose" ? tol + 1e-7 * Math.abs(expected) : tol;
  return Math.abs(value - expected) <= bound;
}

export function quantityLabel(quantity: string): string {
  if (quantity === "price") return "価格";
  if (quantity === "bsm") return "BSM の価格";
  if (quantity === "dt") return "Δt";
  const match = NODE.exec(quantity);
  if (!match) return quantity;
  return `${NODE_LABELS[match[1] as keyof typeof NODE_LABELS]}(${match[2]}, ${match[3]})`;
}

export function needsBsm(example: Example | null): boolean {
  return example?.checks.some((check) => check.quantity === "bsm") ?? false;
}
```

Run: `node --test johnhull/web/src/calc/checks.test.ts`
Expected: `ℹ pass 4`.

- [ ] **Step 6: Messages — test, fail, implement, pass**

`johnhull/web/src/calc/messages.test.ts`:

```ts
import assert from "node:assert/strict";
import { test } from "node:test";
import { describeError } from "./messages.ts";

test("arbitrage explains the violated condition with the numbers", () => {
  const text = describeError({ code: "arbitrage", a: 1.0512710963760241, u: 1.1, d: 1.06, p: -0.21822259059939822 });
  assert.match(text, /d < a < u（0 < p < 1）が成り立ちません/);
  assert.match(text, /p = -0\.218223/);
});

test("input errors name the field and the reason", () => {
  assert.equal(
    describeError({ code: "input", field: "n", reason: "range" }),
    "入力 n を受け付けられません：範囲の外です。",
  );
  assert.equal(
    describeError({ code: "input", field: "x", reason: "odd" }),
    "入力 x を受け付けられません：odd。",
  );
});

test("overflow asks to check the input", () => {
  assert.match(describeError({ code: "nonfinite" }), /大きくなりすぎました/);
});
```

Run: `node --test johnhull/web/src/calc/messages.test.ts`
Expected: FAIL, `ERR_MODULE_NOT_FOUND` for `messages.ts`.

`johnhull/web/src/calc/messages.ts`:

```ts
// Japanese text for calculator states and errors.
import { formatValue } from "./format.ts";
import type { CalcError, Stage } from "./protocol.ts";

export const STAGE_TEXT: Record<Stage, string> = {
  idle: "",
  pyodide: "Python（Pyodide）を読み込んでいます。初回は数秒から十数秒かかります。",
  numpy: "numpy を読み込んでいます。",
  package: "hullkit を読み込んでいます。",
  scipy: "BSM と比べるために scipy を読み込んでいます。",
  ready: "計算しています。",
};

const FIELD_TEXT: Record<string, string> = {
  S0: "S0",
  K: "K",
  r: "r",
  q: "q",
  sigma: "σ",
  u: "u",
  d: "d",
  T: "T",
  n: "n",
  tree: "木の作り方",
  american: "行使のしかた",
};

const REASON_TEXT: Record<string, string> = {
  range: "範囲の外です",
  not_int: "整数ではありません",
  not_number: "数値ではありません",
  not_finite: "有限の数値ではありません",
  not_positive: "0 より大きくしてください",
  not_below_u: "u より小さくしてください",
  degenerate: "小さすぎて u と d が同じ値になります",
  needs_crr: "σ から作る木でだけ使えます",
  needs_european: "ヨーロピアンでだけ使えます",
};

export function describeError(error: CalcError): string {
  if (error.code === "arbitrage") {
    const values = `a = ${formatValue(error.a)}、u = ${formatValue(error.u)}、d = ${formatValue(error.d)}、p = ${formatValue(error.p)}`;
    return `裁定機会があるため計算しません。d < a < u（0 < p < 1）が成り立ちません（${values}）。`;
  }
  if (error.code === "nonfinite") {
    return "計算の途中で値が大きくなりすぎました。入力を見直してください。";
  }
  const field = FIELD_TEXT[error.field] ?? error.field;
  return `入力 ${field} を受け付けられません：${REASON_TEXT[error.reason] ?? error.reason}。`;
}
```

Run: `node --test johnhull/web/src/calc/messages.test.ts`
Expected: `ℹ pass 3`.

- [ ] **Step 7: Diagram geometry — test, fail, implement, pass**

`johnhull/web/src/calc/layout.test.ts`:

```ts
import assert from "node:assert/strict";
import { test } from "node:test";
import { BOX, chartLayout, treeLayout } from "./layout.ts";

test("tree nodes stay inside the drawing for every n up to 6", () => {
  for (let n = 1; n <= 6; n++) {
    const layout = treeLayout(n);
    assert.equal(layout.nodes.length, ((n + 1) * (n + 2)) / 2);
    assert.equal(layout.edges.length, n * (n + 1));
    for (const node of layout.nodes) {
      assert.ok(node.x >= 0 && node.x + BOX.w <= layout.width, `n=${n} x`);
      assert.ok(node.y >= 0 && node.y + BOX.h <= layout.height, `n=${n} y`);
    }
    const root = layout.nodes[0];
    assert.equal(root.y + BOX.h / 2, layout.height / 2);
  }
});

test("each node links to its up and down children", () => {
  const { edges } = treeLayout(2);
  const pairs = edges.map(([a, b]) => `${a.i}${a.j}-${b.i}${b.j}`);
  assert.deepEqual(pairs, ["00-10", "00-11", "10-20", "10-21", "11-21", "11-22"]);
});

const inside = (layout: ReturnType<typeof chartLayout>) =>
  layout.segments.every((segment) =>
    segment
      .slice(1)
      .split(/ [ML]/)
      .every((point) => {
        const [x, y] = point.replace(/^[ML]/, "").split(",").map(Number);
        const { left, right, top, bottom } = layout.plot;
        return x >= left - 1e-9 && x <= right + 1e-9 && y >= top - 1e-9 && y <= bottom + 1e-9;
      }),
  );

test("chart points stay in the plot and arbitrage gaps split the line", () => {
  const steps = [1, 2, 3, 4, 5, 500];
  const layout = chartLayout(steps, [null, 7.4, null, 7.5, 7.45, 7.47], 6.76);
  assert.equal(layout.segments.length, 2);
  assert.ok(inside(layout));
  assert.ok(layout.bsmY !== null && layout.bsmY >= layout.plot.top && layout.bsmY <= layout.plot.bottom);
  assert.deepEqual(
    layout.xTicks.map((t) => t.label),
    ["1", "10", "100", "500"],
  );
});

test("a flat series still gets a finite scale", () => {
  const layout = chartLayout([1, 2, 3], [2, 2, 2], null);
  assert.ok(inside(layout));
  assert.ok(layout.yTicks.every((t) => Number.isFinite(t.at)));
});
```

Run: `node --test johnhull/web/src/calc/layout.test.ts`
Expected: FAIL, `ERR_MODULE_NOT_FOUND` for `layout.ts`.

`johnhull/web/src/calc/layout.ts`:

```ts
// Geometry of the tree diagram and the convergence chart (SVG user units).

export const BOX = { w: 96, h: 54 } as const;
const GAP_X = 28;
const GAP_Y = 10;
const PAD = 8;

export interface NodeBox {
  i: number;
  j: number;
  x: number;
  y: number;
}

export interface TreeLayout {
  width: number;
  height: number;
  nodes: NodeBox[];
  edges: [NodeBox, NodeBox][];
}

// Level i has nodes j = 0..i with j = 0 on top (hullkit's convention).
export function treeLayout(n: number): TreeLayout {
  const half = (BOX.h + GAP_Y) / 2;
  const nodes: NodeBox[] = [];
  const at = new Map<string, NodeBox>();
  for (let i = 0; i <= n; i++) {
    for (let j = 0; j <= i; j++) {
      const node = { i, j, x: PAD + i * (BOX.w + GAP_X), y: PAD + (n - i + 2 * j) * half };
      nodes.push(node);
      at.set(`${i},${j}`, node);
    }
  }
  const edges: [NodeBox, NodeBox][] = [];
  for (const node of nodes) {
    if (node.i === n) continue;
    for (const child of [at.get(`${node.i + 1},${node.j}`), at.get(`${node.i + 1},${node.j + 1}`)]) {
      if (child) edges.push([node, child]);
    }
  }
  return {
    width: 2 * PAD + (n + 1) * BOX.w + n * GAP_X,
    height: 2 * PAD + BOX.h + n * (BOX.h + GAP_Y),
    nodes,
    edges,
  };
}

export interface Tick {
  at: number;
  label: string;
}

export interface ChartLayout {
  width: number;
  height: number;
  plot: { left: number; top: number; right: number; bottom: number };
  segments: string[];
  xTicks: Tick[];
  yTicks: Tick[];
  bsmY: number | null;
}

const CHART = { width: 600, height: 320, left: 72, top: 16, right: 584, bottom: 272 } as const;
const X_TICKS = [1, 10, 100, 500];

// x is log10(steps), so the dense 1..100 range and 150..500 both stay readable.
export function chartLayout(steps: number[], prices: (number | null)[], bsm: number | null, digits = 4): ChartLayout {
  const { left, top, right, bottom } = CHART;
  const xMax = Math.log10(Math.max(...steps, 10));
  const x = (n: number) => left + (Math.log10(n) / xMax) * (right - left);
  const values = [...prices.filter((v): v is number => v !== null), ...(bsm === null ? [] : [bsm])];
  let lo = values.length ? Math.min(...values) : 0;
  let hi = values.length ? Math.max(...values) : 1;
  if (hi - lo < 1e-12 * Math.max(1, Math.abs(hi))) {
    const spread = Math.max(Math.abs(hi) * 0.01, 1e-6);
    lo -= spread;
    hi += spread;
  }
  const margin = (hi - lo) * 0.05;
  lo -= margin;
  hi += margin;
  const y = (v: number) => bottom - ((v - lo) / (hi - lo)) * (bottom - top);
  const segments: string[] = [];
  let current: string[] = [];
  steps.forEach((n, k) => {
    const v = prices[k];
    if (v === null || v === undefined) {
      if (current.length) segments.push(current.join(" "));
      current = [];
      return;
    }
    current.push(`${current.length ? "L" : "M"}${x(n).toFixed(2)},${y(v).toFixed(2)}`);
  });
  if (current.length) segments.push(current.join(" "));
  const yTicks = Array.from({ length: 5 }, (_, k) => {
    const v = lo + ((hi - lo) * k) / 4;
    return { at: y(v), label: String(Number(v.toPrecision(digits))) };
  });
  return {
    width: CHART.width,
    height: CHART.height,
    plot: { left, top, right, bottom },
    segments,
    xTicks: X_TICKS.filter((n) => Math.log10(n) <= xMax).map((n) => ({ at: x(n), label: String(n) })),
    yTicks,
    bsmY: bsm === null ? null : y(bsm),
  };
}
```

Run: `node --test johnhull/web/src/calc/layout.test.ts`
Expected: `ℹ pass 4`.

- [ ] **Step 8: Type check and the whole unit suite**

Run: `$PNPM run typecheck && $PNPM run test:unit`
Expected: `tsc` prints nothing; `ℹ tests 28`, `ℹ pass 28`, `ℹ fail 0`.

- [ ] **Step 9: Commit**

```bash
git add johnhull/web/package.json johnhull/web/pnpm-lock.yaml johnhull/web/tsconfig.json johnhull/web/src/calc/protocol.ts \
  johnhull/web/src/calc/format.ts johnhull/web/src/calc/format.test.ts johnhull/web/src/calc/params.ts \
  johnhull/web/src/calc/params.test.ts johnhull/web/src/calc/checks.ts johnhull/web/src/calc/checks.test.ts \
  johnhull/web/src/calc/messages.ts johnhull/web/src/calc/messages.test.ts johnhull/web/src/calc/layout.ts \
  johnhull/web/src/calc/layout.test.ts johnhull/ROADMAP.md
git commit -m "Add the calculator's protocol types, form parsing, checks, messages and geometry (hull web W1)"
```

---

### Task 7: The Pyodide worker and its client

**Files:**
- Create: `johnhull/web/src/calc/client.ts`, `johnhull/web/src/calc/worker.ts`
- Test: `johnhull/web/src/calc/client.test.ts`

**Interfaces:**
- Consumes: `protocol.ts` (Task 6); `/pyodide/pyodide.mjs`, `/pyodide/hullkit_browser.zip` at run time (Task 9 puts them there).
- Produces: `client.ts` `WorkerLike`, `CalcCancelled`, `CalcFailed(stage: "load" | "run", message)`, `CalcClient(createWorker = defaultWorker)` with `subscribe(listener) -> unsubscribe`, `getStage() -> Stage` (for `useSyncExternalStore`), `calcText(request: string) -> Promise<string>`, `calc<T>(request: CalcRequest) -> Promise<T | ErrorResult>`, `cancel()`, `reset(reason?)`. Cancelling terminates the worker (Python cannot be interrupted); the next request starts a new worker. A load failure does the same (the stage returns to `idle`, so the page's buttons work again); a run failure rejects only its request.
- Produces: `worker.ts`: the first request loads Pyodide, numpy and the package (stages `pyodide` → `numpy` → `package` → `ready`); an `op: "bsm"` request loads scipy first (stage `scipy`); every answer is `run()`'s text; a load failure answers `failed` with `stage: "load"`.

- [ ] **Step 1: Write the failing client tests**

`johnhull/web/src/calc/client.test.ts`:

```ts
import assert from "node:assert/strict";
import { test } from "node:test";
import { CalcCancelled, CalcClient, CalcFailed, type WorkerLike } from "./client.ts";
import type { FromWorker, ToWorker } from "./protocol.ts";

class FakeWorker implements WorkerLike {
  sent: ToWorker[] = [];
  terminated = false;
  onmessage: ((event: MessageEvent<FromWorker>) => void) | null = null;
  onerror: ((event: ErrorEvent) => void) | null = null;
  postMessage(message: ToWorker): void {
    this.sent.push(message);
  }
  terminate(): void {
    this.terminated = true;
  }
  reply(message: FromWorker): void {
    this.onmessage?.({ data: message } as MessageEvent<FromWorker>);
  }
}

function setup() {
  const workers: FakeWorker[] = [];
  const client = new CalcClient(() => {
    const worker = new FakeWorker();
    workers.push(worker);
    return worker;
  });
  return { client, workers };
}

test("answers are matched to requests by id", async () => {
  const { client, workers } = setup();
  const first = client.calcText("a");
  const second = client.calcText("b");
  const [worker] = workers;
  worker.reply({ type: "result", id: worker.sent[1].id, text: "B" });
  worker.reply({ type: "result", id: worker.sent[0].id, text: "A" });
  assert.deepEqual(await Promise.all([first, second]), ["A", "B"]);
  assert.equal(workers.length, 1);
});

test("stage messages reach subscribers", () => {
  const { client, workers } = setup();
  const seen: string[] = [];
  client.subscribe(() => seen.push(client.getStage()));
  void client.calcText("a");
  workers[0].reply({ type: "stage", stage: "pyodide" });
  workers[0].reply({ type: "stage", stage: "ready" });
  assert.deepEqual(seen, ["pyodide", "ready"]);
});

test("cancel rejects waiting requests, stops the worker and the next request starts a new one", async () => {
  const { client, workers } = setup();
  const waiting = client.calcText("slow");
  client.cancel();
  await assert.rejects(waiting, CalcCancelled);
  assert.equal(workers[0].terminated, true);
  assert.equal(client.getStage(), "idle");
  void client.calcText("again");
  assert.equal(workers.length, 2);
});

test("a load failure rejects with its stage, returns to idle and the next request starts a new worker", async () => {
  const { client, workers } = setup();
  const waiting = client.calcText("a");
  workers[0].reply({ type: "stage", stage: "package" });
  workers[0].reply({ type: "failed", id: workers[0].sent[0].id, stage: "load", message: "HTTP 503" });
  await assert.rejects(waiting, (error: unknown) => error instanceof CalcFailed && error.stage === "load");
  assert.equal(client.getStage(), "idle");
  assert.equal(workers[0].terminated, true);
  void client.calcText("b");
  assert.equal(workers.length, 2);
});

test("a run failure rejects that request only and keeps the worker", async () => {
  const { client, workers } = setup();
  const waiting = client.calcText("a");
  workers[0].reply({ type: "failed", id: workers[0].sent[0].id, stage: "run", message: "boom" });
  await assert.rejects(waiting, (error: unknown) => error instanceof CalcFailed && error.stage === "run");
  void client.calcText("b");
  assert.equal(workers.length, 1);
  assert.equal(workers[0].terminated, false);
});

test("a crashed worker rejects everything and is replaced", async () => {
  const { client, workers } = setup();
  const waiting = client.calcText("a");
  workers[0].onerror?.({ message: "boom" } as ErrorEvent);
  await assert.rejects(waiting, /boom/);
  void client.calcText("b");
  assert.equal(workers.length, 2);
});
```

Run: `node --test johnhull/web/src/calc/client.test.ts`
Expected: FAIL, `ERR_MODULE_NOT_FOUND` for `client.ts`.

- [ ] **Step 2: Implement the client and the worker**

`johnhull/web/src/calc/client.ts`:

```ts
// Page side of the calculator: one module Web Worker, requests matched by id.
// Cancelling terminates the worker (Python cannot be interrupted); the next request starts a new one.
import type { CalcRequest, ErrorResult, FromWorker, Stage, ToWorker } from "./protocol.ts";

export interface WorkerLike {
  postMessage(message: ToWorker): void;
  terminate(): void;
  onmessage: ((event: MessageEvent<FromWorker>) => void) | null;
  onerror: ((event: ErrorEvent) => void) | null;
}

export class CalcCancelled extends Error {
  constructor() {
    super("cancelled");
  }
}

export class CalcFailed extends Error {
  readonly stage: "load" | "run";
  constructor(stage: "load" | "run", message: string) {
    super(message);
    this.stage = stage;
  }
}

interface Pending {
  resolve: (text: string) => void;
  reject: (error: Error) => void;
}

function defaultWorker(): WorkerLike {
  return new Worker(new URL("./worker.ts", import.meta.url), { type: "module" }) as unknown as WorkerLike;
}

export class CalcClient {
  private worker: WorkerLike | null = null;
  private nextId = 1;
  private readonly pending = new Map<number, Pending>();
  private stage: Stage = "idle";
  private readonly listeners = new Set<() => void>();
  private readonly createWorker: () => WorkerLike;

  constructor(createWorker: () => WorkerLike = defaultWorker) {
    this.createWorker = createWorker;
  }

  readonly subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  };

  readonly getStage = (): Stage => this.stage;

  calcText(request: string): Promise<string> {
    const worker = this.ensureWorker();
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      worker.postMessage({ id, request });
    });
  }

  async calc<T>(request: CalcRequest): Promise<T | ErrorResult> {
    return JSON.parse(await this.calcText(JSON.stringify(request))) as T | ErrorResult;
  }

  cancel(): void {
    this.reset(new CalcCancelled());
  }

  reset(reason: Error = new CalcCancelled()): void {
    this.worker?.terminate();
    this.worker = null;
    const waiting = [...this.pending.values()];
    this.pending.clear();
    for (const entry of waiting) entry.reject(reason);
    this.setStage("idle");
  }

  private setStage(stage: Stage): void {
    this.stage = stage;
    for (const listener of this.listeners) listener();
  }

  private ensureWorker(): WorkerLike {
    if (this.worker) return this.worker;
    const worker = this.createWorker();
    worker.onmessage = (event) => {
      const message = event.data;
      if (message.type === "stage") {
        this.setStage(message.stage);
        return;
      }
      const entry = this.pending.get(message.id);
      if (!entry) return;
      if (message.type === "failed" && message.stage === "load") {
        // A worker whose Python did not load cannot recover: drop it, so the next request starts afresh.
        this.reset(new CalcFailed("load", message.message));
        return;
      }
      this.pending.delete(message.id);
      if (message.type === "result") entry.resolve(message.text);
      else entry.reject(new CalcFailed(message.stage, message.message));
    };
    worker.onerror = (event) => {
      this.reset(new CalcFailed("load", event.message || "the calculator worker stopped"));
    };
    this.worker = worker;
    return worker;
  }
}
```

`johnhull/web/src/calc/worker.ts` (exercised in the browser by Task 10's checks):

```ts
// Module Web Worker. The first request loads Pyodide, numpy and the browser package
// (spec §3.4); scipy loads only for a "bsm" request. Every answer is run()'s JSON text.
import type { FromWorker, ToWorker } from "./protocol.ts";

interface Pyodide {
  loadPackage(names: string | string[], options?: { messageCallback?: (message: string) => void }): Promise<unknown>;
  unpackArchive(buffer: ArrayBuffer, format: string, options?: { extractDir?: string }): void;
  runPython(code: string): unknown;
  globals: { get(name: string): unknown };
}

interface WorkerScope {
  postMessage(message: FromWorker): void;
  onmessage: ((event: MessageEvent<ToWorker>) => void) | null;
}

type Run = (request: string) => string;

const scope = globalThis as unknown as WorkerScope;
const PYODIDE_MODULE = "/pyodide/pyodide.mjs";
const PYODIDE_INDEX = "/pyodide/";
const PACKAGE_URL = "/pyodide/hullkit_browser.zip";
const EXTRACT_DIR = "/home/pyodide/browser";
const quiet = { messageCallback: () => {} };

let pyodide: Pyodide | null = null;
let ready: Promise<Run> | null = null;
let scipy: Promise<unknown> | null = null;

async function boot(): Promise<Run> {
  scope.postMessage({ type: "stage", stage: "pyodide" });
  const { loadPyodide } = await import(/* @vite-ignore */ PYODIDE_MODULE);
  const py = (await loadPyodide({ indexURL: PYODIDE_INDEX })) as Pyodide;
  pyodide = py;
  scope.postMessage({ type: "stage", stage: "numpy" });
  await py.loadPackage("numpy", quiet);
  scope.postMessage({ type: "stage", stage: "package" });
  const response = await fetch(PACKAGE_URL);
  if (!response.ok) throw new Error(`${PACKAGE_URL}: HTTP ${response.status}`);
  py.unpackArchive(await response.arrayBuffer(), "zip", { extractDir: EXTRACT_DIR });
  py.runPython(
    `import sys\nsys.path.insert(0, ${JSON.stringify(EXTRACT_DIR)})\nfrom hull_web_calc.binomial import run as hull_run`,
  );
  scope.postMessage({ type: "stage", stage: "ready" });
  return py.globals.get("hull_run") as Run;
}

async function ensureScipy(py: Pyodide): Promise<void> {
  if (!scipy) {
    scope.postMessage({ type: "stage", stage: "scipy" });
    scipy = py.loadPackage("scipy", quiet);
  }
  await scipy;
  scope.postMessage({ type: "stage", stage: "ready" });
}

function asksForBsm(request: string): boolean {
  try {
    return JSON.parse(request)?.op === "bsm";
  } catch {
    return false;
  }
}

function describe(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

scope.onmessage = async (event) => {
  const { id, request } = event.data;
  let run: Run;
  try {
    ready ??= boot();
    run = await ready;
    if (asksForBsm(request) && pyodide) await ensureScipy(pyodide);
  } catch (error) {
    scope.postMessage({ type: "failed", id, stage: "load", message: describe(error) });
    return;
  }
  try {
    scope.postMessage({ type: "result", id, text: run(request) });
  } catch (error) {
    scope.postMessage({ type: "failed", id, stage: "run", message: describe(error) });
  }
};
```

- [ ] **Step 3: Run the tests and the type check**

Run: `$PNPM run typecheck && $PNPM run test:unit`
Expected: `tsc` prints nothing; `ℹ tests 34`, `ℹ pass 34`.

- [ ] **Step 4: Commit**

```bash
git add johnhull/web/src/calc/client.ts johnhull/web/src/calc/client.test.ts johnhull/web/src/calc/worker.ts
git commit -m "Run the calculator in a module worker with cancel and load-failure handling"
```

---

### Task 8: The service worker

**Files:**
- Create: `johnhull/web/sw/sw.template.js`
- Test: `johnhull/web/sw/sw.test.mjs`

**Interfaces:**
- Produces: a template with exactly four placeholders, `__VERSION__`, `__PYODIDE_VERSION__`, `__SHELL__` (JSON array of paths), `__PYODIDE_FILES__` (JSON array of paths); Task 9's `write_service_worker` fills them.
- Behaviour (spec §3.6, plan D-7): caches `shell-<VERSION>` (stored at install), `pyodide-<PYODIDE_VERSION>`, `pages` (kept across deploys; each entry carries `X-Hull-Version`). HTML: network first, stored under a key without `.html` / `index.html`; offline: the saved page, else the shell, else a 503 page that says the page is not saved. Other files: cache first (a `pages` entry from an older deploy is fetched again once; offline it is still served). Only same-origin 200 responses that were not redirected are stored. Range requests and other origins pass through.

- [ ] **Step 1: Write the failing tests**

`johnhull/web/sw/sw.test.mjs` (Review Focus 2, 3 and 5):

```js
// Unit tests of sw.template.js, run in a node:vm sandbox with an in-memory Cache API.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import vm from "node:vm";

const ORIGIN = "https://hull.example";
const SHELL = ["/", "/calc/binomial/", "/assets/app.js"];

function render(version) {
  return readFileSync(new URL("./sw.template.js", import.meta.url), "utf8")
    .replace("__VERSION__", version)
    .replace("__PYODIDE_VERSION__", "314.0.7")
    .replace("__SHELL__", JSON.stringify(SHELL))
    .replace("__PYODIDE_FILES__", JSON.stringify(["/pyodide/pyodide.asm.wasm"]));
}

// What fetch() gives a service worker: real Responses cannot be made with type "basic" or redirected.
function reply(status, body, { type = "basic", redirected = false } = {}) {
  return {
    status,
    statusText: "",
    type,
    redirected,
    body,
    headers: new Headers(),
    clone() {
      return { ...this };
    },
    async text() {
      return body;
    },
  };
}

class FakeCache {
  entries = new Map();
  key(request) {
    return typeof request === "string" ? new URL(request, ORIGIN).href : request.url;
  }
  // Like the Cache API, every match is a new Response, so a stored body can be read again.
  async match(request) {
    return this.entries.get(this.key(request))?.clone();
  }
  async put(request, response) {
    this.entries.set(this.key(request), response);
  }
  async addAll(urls) {
    for (const url of urls) this.entries.set(this.key(url), reply(200, `shell ${url}`));
  }
}

class FakeCacheStorage {
  stores = new Map();
  async open(name) {
    if (!this.stores.has(name)) this.stores.set(name, new FakeCache());
    return this.stores.get(name);
  }
  async keys() {
    return [...this.stores.keys()];
  }
  async delete(name) {
    return this.stores.delete(name);
  }
}

const offline = async () => {
  throw new TypeError("offline");
};
const online = (body) => async () => reply(200, body);

// One installed service worker; a redeploy is a second boot() on the same caches.
function boot({ version = "v2", caches = new FakeCacheStorage() } = {}) {
  const listeners = {};
  const sw = { listeners, caches, requests: [], network: offline };
  const self = {
    location: new URL(`${ORIGIN}/sw.js`),
    addEventListener: (type, listener) => {
      listeners[type] = listener;
    },
    skipWaiting: async () => {},
    clients: { claim: async () => {} },
  };
  const fetch = (request) => {
    sw.requests.push(request.url);
    return sw.network(request);
  };
  const context = { self, caches, fetch, Response, Headers, URL, Set, Promise };
  vm.runInContext(render(version), vm.createContext(context));
  return sw;
}

async function lifecycle(sw, type) {
  let pending;
  sw.listeners[type]({ waitUntil: (promise) => (pending = promise) });
  await pending;
}

async function get(sw, path, { mode = "no-cors", headers = {}, origin = ORIGIN } = {}) {
  let answer = null;
  const request = { url: new URL(path, origin).href, method: "GET", mode, headers: new Headers(headers) };
  sw.listeners.fetch({ request, respondWith: (promise) => (answer = promise) });
  return answer === null ? null : await answer;
}

const read = async (sw, path, options) => (await get(sw, path, options)).text();

test("install stores the shell", async () => {
  const sw = boot();
  await lifecycle(sw, "install");
  const shell = await sw.caches.open("shell-v2");
  assert.deepEqual([...shell.entries.keys()], SHELL.map((p) => ORIGIN + p));
});

test("a page opened online is stored under its key without .html", async () => {
  const sw = boot();
  sw.network = online("chapter");
  assert.equal(await read(sw, "/book/_build/html/notebooks/x.html", { mode: "navigate" }), "chapter");
  const pages = await sw.caches.open("pages");
  assert.deepEqual([...pages.entries.keys()], [`${ORIGIN}/book/_build/html/notebooks/x`]);
});

test("offline, a stored page opens under both spellings", async () => {
  const sw = boot();
  sw.network = online("chapter");
  await get(sw, "/book/_build/html/notebooks/x", { mode: "navigate" });
  sw.network = offline;
  for (const path of ["/book/_build/html/notebooks/x", "/book/_build/html/notebooks/x.html"]) {
    assert.equal(await read(sw, path, { mode: "navigate" }), "chapter");
  }
});

test("offline, the calculator opens from the shell", async () => {
  const sw = boot();
  await lifecycle(sw, "install");
  assert.equal(await read(sw, "/calc/binomial/index.html", { mode: "navigate" }), "shell /calc/binomial/");
});

test("offline, an unsaved page says so with 503", async () => {
  const sw = boot();
  const response = await get(sw, "/report/site/index.html", { mode: "navigate" });
  assert.equal(response.status, 503);
  assert.match(await response.text(), /このページはまだこの端末に保存されていません/);
});

test("redirects and foreign answers are passed through and never stored", async () => {
  for (const answer of [
    reply(0, "", { type: "opaqueredirect" }),
    reply(200, "login", { redirected: true }),
    reply(200, "login", { type: "cors" }),
    reply(404, "missing"),
  ]) {
    const sw = boot();
    sw.network = async () => answer;
    assert.equal(await get(sw, "/book/_build/html/index.html", { mode: "navigate" }), answer);
    assert.equal(await get(sw, "/book/_build/html/_static/a.css"), answer);
    for (const name of await sw.caches.keys()) {
      assert.equal((await sw.caches.open(name)).entries.size, 0, name);
    }
  }
});

test("range requests and other origins are left to the browser", async () => {
  const sw = boot();
  assert.equal(await get(sw, "/pyodide/pyodide.asm.wasm", { headers: { Range: "bytes=0-10" } }), null);
  assert.equal(await get(sw, "/x.js", { origin: "https://cdn.example" }), null);
});

test("assets are cache-first and Pyodide files go to the Pyodide cache", async () => {
  const sw = boot();
  sw.network = online("wasm");
  await get(sw, "/pyodide/pyodide.asm.wasm");
  await get(sw, "/pyodide/pyodide.asm.wasm");
  sw.network = online("css");
  await get(sw, "/book/_build/html/_static/a.css");
  assert.equal(await read(sw, "/book/_build/html/_static/a.css"), "css");
  assert.equal(sw.requests.length, 2);
  assert.equal((await sw.caches.open("pyodide-314.0.7")).entries.size, 1);
});

test("a page saved before a redeploy still opens offline", async () => {
  const before = boot({ version: "v1" });
  before.network = online("chapter v1");
  await get(before, "/book/_build/html/notebooks/x.html", { mode: "navigate" });
  before.network = online("css v1");
  await get(before, "/book/_build/html/_static/a.css");
  const after = boot({ version: "v2", caches: before.caches });
  await lifecycle(after, "activate");
  assert.equal(await read(after, "/book/_build/html/notebooks/x", { mode: "navigate" }), "chapter v1");
  assert.equal(await read(after, "/book/_build/html/_static/a.css"), "css v1");
});

test("after a redeploy, a saved file is fetched again once, then served from the cache", async () => {
  const before = boot({ version: "v1" });
  before.network = online("css v1");
  await get(before, "/book/_build/html/_static/a.css");
  const after = boot({ version: "v2", caches: before.caches });
  after.network = online("css v2");
  assert.equal(await read(after, "/book/_build/html/_static/a.css"), "css v2");
  assert.equal(await read(after, "/book/_build/html/_static/a.css"), "css v2");
  assert.equal(after.requests.length, 1);
});

test("activate removes the old shell and Pyodide caches and keeps the saved pages", async () => {
  const sw = boot();
  for (const name of ["shell-v1", "pages", "pyodide-314.0.6", "pyodide-314.0.7", "shell-v2"]) {
    await sw.caches.open(name);
  }
  await lifecycle(sw, "activate");
  assert.deepEqual((await sw.caches.keys()).sort(), ["pages", "pyodide-314.0.7", "shell-v2"]);
});
```

Run: `node --test johnhull/web/sw/sw.test.mjs`
Expected: FAIL, `ENOENT` for `sw.template.js`.

- [ ] **Step 2: Implement the template**

`johnhull/web/sw/sw.template.js`:

```js
/* Service worker of the johnhull site (spec §3.6). hull_web_build.site fills in the
   four placeholders; the rest of this file is served unchanged.

   shell-VERSION   app shell, stored at install; replaced on every deploy
   pyodide-VER     Pyodide files; replaced only when the Pyodide version changes
   pages           Book and report pages and their files; kept across deploys, so a
                   page opened once stays readable offline (spec §1 condition 3) */
const VERSION = "__VERSION__";
const PYODIDE_VERSION = "__PYODIDE_VERSION__";
const SHELL = __SHELL__;
const PYODIDE_FILES = __PYODIDE_FILES__;

const SHELL_CACHE = `shell-${VERSION}`;
const PAGES_CACHE = "pages";
const PYODIDE_CACHE = `pyodide-${PYODIDE_VERSION}`;
const SHELL_PATHS = new Set(SHELL);
const PYODIDE_PATHS = new Set(PYODIDE_FILES);
// The deploy that stored a pages entry; a file stored under an older deploy is fetched again once.
const STORED_BY = "X-Hull-Version";
const OFFLINE_PAGE = `<!doctype html>
<html lang="ja">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>オフライン</title></head>
<body>
<h1>オフラインです</h1>
<p>このページはまだこの端末に保存されていません。ネットワークにつながっているときに一度開くと、次からはオフラインでも読めます。</p>
<p><a href="/">入口へ戻る</a></p>
</body>
</html>`;

// Pages serves /a/b.html at /a/b and /a/index.html at /a/, so both spellings share a key.
function pageKey(url) {
  let path = url.pathname;
  if (path.endsWith("/index.html")) path = path.slice(0, -"index.html".length);
  else if (path.endsWith(".html")) path = path.slice(0, -".html".length);
  return url.origin + path;
}

function isPage(request, url) {
  return request.mode === "navigate" || url.pathname.endsWith(".html") || url.pathname.endsWith("/");
}

// Only same-origin 200 answers are stored: never a redirect (pretty URL or Access login).
function isCacheable(response) {
  return response.status === 200 && response.type === "basic" && !response.redirected;
}

function stamped(response) {
  const headers = new Headers(response.headers);
  headers.set(STORED_BY, VERSION);
  return new Response(response.body, { status: response.status, statusText: response.statusText, headers });
}

async function networkFirst(request, url) {
  const key = pageKey(url);
  let response;
  try {
    response = await fetch(request);
  } catch {
    const pages = await caches.open(PAGES_CACHE);
    const shell = await caches.open(SHELL_CACHE);
    const cached = (await pages.match(key, { ignoreVary: true })) || (await shell.match(key, { ignoreVary: true }));
    return cached || new Response(OFFLINE_PAGE, { status: 503, headers: { "Content-Type": "text/html; charset=utf-8" } });
  }
  if (isCacheable(response)) {
    await (await caches.open(PAGES_CACHE)).put(key, stamped(response.clone()));
  }
  return response;
}

async function cacheFirst(request, url) {
  const name = PYODIDE_PATHS.has(url.pathname) ? PYODIDE_CACHE : SHELL_PATHS.has(url.pathname) ? SHELL_CACHE : PAGES_CACHE;
  const cache = await caches.open(name);
  const cached = await cache.match(request, { ignoreVary: true });
  if (cached && (name !== PAGES_CACHE || cached.headers.get(STORED_BY) === VERSION)) return cached;
  let response;
  try {
    response = await fetch(request);
  } catch (error) {
    if (cached) return cached;
    throw error;
  }
  if (isCacheable(response)) await cache.put(request, name === PAGES_CACHE ? stamped(response.clone()) : response.clone());
  return response;
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) => cache.addAll(SHELL)).then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  const keep = new Set([SHELL_CACHE, PAGES_CACHE, PYODIDE_CACHE]);
  event.waitUntil(
    caches
      .keys()
      .then((names) => Promise.all(names.filter((name) => !keep.has(name)).map((name) => caches.delete(name))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET" || request.headers.has("range")) return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  event.respondWith(isPage(request, url) ? networkFirst(request, url) : cacheFirst(request, url));
});
```

- [ ] **Step 3: Run the tests to see them pass**

Run: `$PNPM run test:unit`
Expected: `ℹ tests 45`, `ℹ pass 45` (11 of them in `sw.test.mjs`).

- [ ] **Step 4: Commit**

```bash
git add johnhull/web/sw/sw.template.js johnhull/web/sw/sw.test.mjs
git commit -m "Add the service worker: offline pages that survive redeploys, no stored redirects"
```

---

### Task 9: Site assembly, link check, icons and the make targets

**Files:**
- Create: `johnhull/web/py/hull_web_build/links.py`, `johnhull/web/py/hull_web_build/icons.py`
- Modify: `johnhull/web/py/hull_web_build/site.py` (W1 part), `johnhull/web/py/hull_web_build/cli.py` (add `site`), root `Makefile`
- Test: `johnhull/web/py/tests/test_links.py`, `test_icons.py`, `test_site.py` (three more tests)

**Interfaces:**
- Consumes: `paths.APP_BUILD` (`build/app`, written by `vite build` in Task 10), `paths.SW_TEMPLATE` (Task 8), `site.copy_content`, `copy_pyodide`, `check_files` (Task 5).
- Produces: `links.REMOVED_BY_DESIGN`, `LinkReport(checked, removed_by_design, broken)`, `resolve(page, link) -> str | None`, `exists(root, target) -> bool` (a file, a directory with `index.html`, or a pretty URL), `check_site(root) -> LinkReport`.
- Produces: `icons.png(size) -> bytes` (deterministic RGB PNG).
- Produces: `site.ICON_SIZES`, `SHELL_PAGES`, `REQUIRED`, `site_version(out) -> str` (16 hex digits over every file except `sw.js`), `write_service_worker(out, pins, lock) -> str`, `assemble(out=None, pyodide_dir=None) -> dict` (`files`, `bytes`, `version`, `links_checked`, `removed_by_design`); it raises `SiteError` on a broken link or a missing required file.
- Produces: `make hull-web`, `make hull-web-check`.

- [ ] **Step 1: Write the failing tests**

`johnhull/web/py/tests/test_links.py`:

```python
from hull_web_build import links


def _site(tmp_path, files: dict[str, str]):
    for name, text in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return tmp_path


def test_resolve_handles_relative_absolute_and_external_links():
    assert links.resolve("book/a/b.html", "../c.html#x") == "book/c.html"
    assert links.resolve("book/a/b.html", "/calc/binomial/") == "calc/binomial"
    assert links.resolve("index.html", "/") == ""
    assert links.resolve("book/a/b.html", "https://example.com/") is None
    assert links.resolve("book/a/b.html", "#top") is None
    assert links.resolve("book/a/b.html", "?q=1") is None
    assert links.resolve("book/a/b.html", "mailto:x@example.com") is None


def test_check_site_reports_broken_and_removed_by_design_links(tmp_path):
    root = _site(
        tmp_path,
        {
            "index.html": '<a href="/book/_build/html/">b</a><a href="/missing.html">m</a>',
            "book/_build/html/index.html": (
                '<a href="notebooks/x.html#a">x</a><img src="_images/p.png">'
                '<a href="_sources/notebooks/x.ipynb">src</a><a href="../../../report/site/">r</a>'
            ),
            "book/_build/html/notebooks/x.html": '<a href="../index.html">up</a><a href="../../../../../etc">out</a>',
            "book/_build/html/_images/p.png": "",
            "book/_build/html/_static/macros.html": "<a href=\"{{ pathto('x') }}\">t</a>",
            "report/site/index.html": '<a href="../../book/_build/html/notebooks/x">pretty</a>',
        },
    )
    report = links.check_site(root)
    assert report.broken == [
        ("book/_build/html/notebooks/x.html", "../../../../../etc"),
        ("index.html", "/missing.html"),
    ]
    assert report.removed_by_design == [
        ("book/_build/html/index.html", "_sources/notebooks/x.ipynb")
    ]
    assert report.checked == 9
```

`johnhull/web/py/tests/test_icons.py`:

```python
import struct
import zlib

import pytest
from hull_web_build import icons


@pytest.mark.parametrize("size", [180, 192, 512])
def test_icon_is_a_valid_rgb_png_of_the_requested_size(size):
    data = icons.png(size)
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    width, height, depth, color = struct.unpack(">IIBB", data[16:26])
    assert (width, height, depth, color) == (size, size, 8, 2)
    idat_length = struct.unpack(">I", data[33:37])[0]
    raw = zlib.decompress(data[41 : 41 + idat_length])
    assert len(raw) == size * (1 + 3 * size)
    assert icons.FOREGROUND in raw and icons.BACKGROUND in raw


def test_icon_bytes_are_deterministic():
    assert icons.png(64) == icons.png(64)
```

In `johnhull/web/py/tests/test_site.py`, change the first import line from `import hashlib\nimport json` to also import `re` (the imports become `import hashlib`, `import json`, `import re`), and append:

```python
def test_assemble_builds_a_checked_site_with_a_filled_service_worker(world):
    out = world["tmp"] / "dist"
    summary = site.assemble(out, world["cache"])
    sw = (out / "sw.js").read_text(encoding="utf-8")
    assert not re.search(r"__[A-Z_]+__", sw)
    shell = json.loads(re.search(r"const SHELL = (\[.*?\]);", sw).group(1))
    assert {"/", "/calc/binomial/", "/assets/main.js", "/icons/icon-512.png"} <= set(shell)
    assert '"/pyodide/pyodide.asm.wasm"' in sw
    assert summary["removed_by_design"] == 1
    assert {"apple-touch-icon.png", "icon-192.png", "icon-512.png"} == {
        p.name for p in (out / "icons").iterdir()
    }


def test_site_version_changes_with_content_but_not_with_sw_js(world):
    out = world["tmp"] / "dist"
    site.assemble(out, world["cache"])
    before = site.site_version(out)
    (out / "sw.js").write_text("changed", encoding="utf-8")
    assert site.site_version(out) == before
    (out / "report/site/index.html").write_text("changed", encoding="utf-8")
    assert site.site_version(out) != before


def test_assemble_refuses_broken_links(world):
    _write(paths.APP_BUILD, {"calc/binomial/index.html": '<a href="/nowhere/">x</a>'})
    with pytest.raises(site.SiteError, match="nowhere"):
        site.assemble(world["tmp"] / "dist", world["cache"])
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `$PYT -m pytest johnhull/web/py/tests/test_links.py johnhull/web/py/tests/test_icons.py johnhull/web/py/tests/test_site.py -q`
Expected: collection errors for `links` and `icons`, and `AttributeError: module 'hull_web_build.site' has no attribute 'assemble'` in `test_site.py`.

- [ ] **Step 3: Implement the link check, the icons and the full site module**

`johnhull/web/py/hull_web_build/links.py`:

```python
"""Relative-link check over an assembled site (spec §5: every in-site link resolves)."""

from __future__ import annotations

import html.parser
import posixpath
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote, urlsplit

# The Book's "download source" buttons point here; spec §3.2 leaves _sources/ out.
REMOVED_BY_DESIGN = ("book/_build/html/_sources/",)
SKIP_PREFIXES = ("#", "mailto:", "javascript:", "data:", "tel:")


@dataclass
class LinkReport:
    """Counts and failures of one link check."""

    checked: int = 0
    removed_by_design: list[tuple[str, str]] = field(default_factory=list)
    broken: list[tuple[str, str]] = field(default_factory=list)


class _Links(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.found: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name in ("href", "src") and value:
                self.found.append(value.strip())


def resolve(page: str, link: str) -> str | None:
    """Site-relative path that `link` on `page` points to, or None if it leaves the site."""
    if link.lower().startswith(SKIP_PREFIXES):
        return None
    parts = urlsplit(link)
    if parts.scheme or parts.netloc or not parts.path:
        return None
    target = unquote(parts.path)
    if target.startswith("/"):
        stripped = target.lstrip("/")
        return posixpath.normpath(stripped) if stripped else ""
    return posixpath.normpath(posixpath.join(posixpath.dirname(page), target))


def exists(root: Path, target: str) -> bool:
    """True if `target` names a file, a directory with index.html, or a pretty URL."""
    if target == ".." or target.startswith("../"):
        return False
    path = root / target if target else root
    return (
        path.is_file()
        or (path / "index.html").is_file()
        or path.with_name(path.name + ".html").is_file()
    )


def check_site(root: Path) -> LinkReport:
    """Check href/src of every HTML page under `root` (theme templates in _static/ excepted)."""
    report = LinkReport()
    for path in sorted(root.rglob("*.html")):
        page = path.relative_to(root).as_posix()
        if "/_static/" in f"/{page}":
            continue
        parser = _Links()
        parser.feed(path.read_text(encoding="utf-8", errors="replace"))
        for link in parser.found:
            target = resolve(page, link)
            if target is None:
                continue
            report.checked += 1
            if exists(root, target):
                continue
            if target.startswith(REMOVED_BY_DESIGN):
                report.removed_by_design.append((page, link))
            else:
                report.broken.append((page, link))
    return report
```

`johnhull/web/py/hull_web_build/icons.py`:

```python
"""App icons drawn with the standard library: a three-step recombining tree on navy."""

from __future__ import annotations

import math
import struct
import zlib

BACKGROUND = bytes((0x1F, 0x3A, 0x5F))
FOREGROUND = bytes((0xFF, 0xFF, 0xFF))
NODES = ((0.22, 0.50), (0.50, 0.30), (0.50, 0.70), (0.78, 0.15), (0.78, 0.50), (0.78, 0.85))
EDGES = ((0, 1), (0, 2), (1, 3), (1, 4), (2, 4), (2, 5))


def png(size: int) -> bytes:
    """PNG bytes of a `size` x `size` RGB icon."""
    rows = [bytearray(BACKGROUND * size) for _ in range(size)]
    for a, b in EDGES:
        _segment(rows, size, NODES[a], NODES[b], 0.022 * size)
    for x, y in NODES:
        _disc(rows, size, x * size, y * size, 0.07 * size)
    raw = b"".join(b"\x00" + bytes(row) for row in rows)
    header = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(raw, 9))
        + _chunk(b"IEND", b"")
    )


def _chunk(kind: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(kind + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)


def _paint(rows: list[bytearray], x: int, y: int) -> None:
    rows[y][3 * x : 3 * x + 3] = FOREGROUND


def _disc(rows: list[bytearray], size: int, cx: float, cy: float, radius: float) -> None:
    for y in range(max(0, int(cy - radius)), min(size, int(cy + radius) + 2)):
        for x in range(max(0, int(cx - radius)), min(size, int(cx + radius) + 2)):
            if math.hypot(x + 0.5 - cx, y + 0.5 - cy) <= radius:
                _paint(rows, x, y)


def _segment(rows, size, start, end, half_width) -> None:
    ax, ay, bx, by = start[0] * size, start[1] * size, end[0] * size, end[1] * size
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    for y in range(
        max(0, int(min(ay, by) - half_width)), min(size, int(max(ay, by) + half_width) + 2)
    ):
        for x in range(
            max(0, int(min(ax, bx) - half_width)), min(size, int(max(ax, bx) + half_width) + 2)
        ):
            px, py = x + 0.5, y + 0.5
            t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length2))
            if math.hypot(px - (ax + t * dx), py - (ay + t * dy)) <= half_width:
                _paint(rows, x, y)
```

Replace `johnhull/web/py/hull_web_build/site.py` with:

```python
"""Assemble a site directory and check what it may contain (spec §3.2, §5)."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from . import icons, links, package, paths, pyodide_fetch

MAX_FILE_BYTES = 25 * 1024 * 1024
MAX_FILES = 20_000
ICON_SIZES = {"apple-touch-icon.png": 180, "icon-192.png": 192, "icon-512.png": 512}
SHELL_PAGES = ("/", "/calc/binomial/")
REQUIRED = ("404.html", "_headers", "robots.txt", "manifest.webmanifest", "sw.js")
W0_CSP = (
    "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; connect-src 'self'; "
    "worker-src 'self'; object-src 'none'; base-uri 'self'"
)
W0_HEADERS = """/*
  X-Robots-Tag: noindex
  X-Content-Type-Options: nosniff
  Referrer-Policy: same-origin

/w0/*
  Content-Security-Policy: {strict}

/w0-eval/*
  Content-Security-Policy: {with_eval}
"""


class SiteError(RuntimeError):
    """An input is missing or the assembled site breaks a rule of the spec."""


def _require(path: Path, how: str) -> None:
    if not path.exists():
        raise SiteError(f"{path} is missing; run `{how}` first")


def _skip_book(directory: str, names: list[str]) -> set[str]:
    return {n for n in names if n in ("_sources", ".buildinfo") or n.lower().endswith(".pdf")}


def _skip_pdf(directory: str, names: list[str]) -> set[str]:
    return {n for n in names if n.lower().endswith(".pdf")}


def copy_content(out: Path) -> None:
    """Copy the Book, the supplementary site and, once merged, the guide tables (spec §3.2)."""
    _require(paths.BOOK_HTML / "index.html", "make hull-book")
    _require(paths.REPORT_SITE / "index.html", "make hull-report")
    shutil.copytree(paths.BOOK_HTML, out / "book" / "_build" / "html", ignore=_skip_book)
    shutil.copytree(paths.REPORT_SITE, out / "report" / "site", ignore=_skip_pdf)
    if paths.GUIDE_TABLES.is_dir():
        target = out / "docs" / "validation" / "reading-guide"
        shutil.copytree(paths.GUIDE_TABLES, target, ignore=_skip_pdf)


def copy_pyodide(out: Path, pins: dict, lock: dict, source: Path) -> None:
    """Copy the pinned Pyodide files and the browser package to /pyodide/, re-verifying each."""
    target = out / "pyodide"
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(paths.LOCK, target / "pyodide-lock.json")
    for name, digest in pyodide_fetch.expected_files(pins, lock).items():
        _require(source / name, "python -m hull_web_build fetch-pyodide")
        shutil.copy2(source / name, target / name)
        if pyodide_fetch.sha256(target / name) != digest:
            raise pyodide_fetch.IntegrityError(f"{source / name} does not match its pin")
    _require(paths.PACKAGE_ZIP, "python -m hull_web_build package")
    shutil.copy2(paths.PACKAGE_ZIP, target / "hullkit_browser.zip")
    problems = package.verify(target / "hullkit_browser.zip")
    if problems:
        raise SiteError("browser package differs from the repo: " + "; ".join(problems))


def check_files(out: Path) -> dict:
    """Forbidden files, the 25 MiB per-file limit and the 20,000-file limit."""
    files = sorted(p for p in out.rglob("*") if p.is_file())
    names = [p.relative_to(out).as_posix() for p in files]
    problems = []
    forbidden = [
        n
        for n in names
        if n.lower().endswith(".pdf") or "/_sources/" in f"/{n}" or n.endswith(".buildinfo")
    ]
    if forbidden:
        problems.append(f"forbidden files: {forbidden[:10]}")
    large = [n for p, n in zip(files, names, strict=True) if p.stat().st_size > MAX_FILE_BYTES]
    if large:
        problems.append(f"files over 25 MiB: {large}")
    if len(files) > MAX_FILES:
        problems.append(f"{len(files)} files is over the {MAX_FILES} limit")
    if problems:
        raise SiteError("\n".join(problems))
    return {"files": len(files), "bytes": sum(p.stat().st_size for p in files)}


def _fresh(out: Path) -> None:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)


def assemble_w0(out: Path | None = None, pyodide_dir: Path | None = None) -> dict:
    """W0 spike site: content, Pyodide and the spike page at /w0/ (strict CSP) and /w0-eval/."""
    out = out or paths.W0_SITE
    pins = pyodide_fetch.load_pins()
    lock = pyodide_fetch.load_lock(pins)
    _fresh(out)
    copy_content(out)
    copy_pyodide(out, pins, lock, pyodide_dir or paths.PYODIDE_CACHE / pins["pyodide"]["version"])
    for mount in ("w0", "w0-eval"):
        shutil.copytree(paths.W0_PAGE, out / mount)
    with_eval = W0_CSP.replace("'wasm-unsafe-eval'", "'wasm-unsafe-eval' 'unsafe-eval'")
    headers = W0_HEADERS.format(strict=W0_CSP, with_eval=with_eval)
    (out / "_headers").write_text(headers, encoding="utf-8")
    (out / "404.html").write_text(
        "<!doctype html><title>404</title><p>Not found</p>\n", encoding="utf-8"
    )
    (out / "index.html").write_text(
        '<!doctype html><title>W0</title><a href="/w0/">W0</a>\n', encoding="utf-8"
    )
    return check_files(out)


def site_version(out: Path) -> str:
    """16 hex digits that change whenever any file except sw.js changes."""
    digest = hashlib.sha256()
    for path in sorted(p for p in out.rglob("*") if p.is_file() and p != out / "sw.js"):
        digest.update(path.relative_to(out).as_posix().encode("utf-8") + b"\0")
        digest.update(pyodide_fetch.sha256(path).encode("ascii") + b"\n")
    return digest.hexdigest()[:16]


def write_service_worker(out: Path, pins: dict, lock: dict) -> str:
    """Fill sw.template.js with the version, the shell list and the Pyodide file list."""
    pyodide_files = ["/pyodide/pyodide-lock.json"]
    pyodide_files += [f"/pyodide/{name}" for name in pyodide_fetch.expected_files(pins, lock)]
    assets = sorted(
        "/" + p.relative_to(out).as_posix() for p in (out / "assets").rglob("*") if p.is_file()
    )
    shell = [*SHELL_PAGES, "/manifest.webmanifest", "/pyodide/hullkit_browser.zip"]
    shell += [f"/icons/{name}" for name in sorted(ICON_SIZES)] + assets
    version = site_version(out)
    text = paths.SW_TEMPLATE.read_text(encoding="utf-8")
    values = {
        "__VERSION__": version,
        "__PYODIDE_VERSION__": pins["pyodide"]["version"],
        "__SHELL__": json.dumps(shell),
        "__PYODIDE_FILES__": json.dumps(sorted(pyodide_files)),
    }
    for placeholder, value in values.items():
        if text.count(placeholder) != 1:
            raise SiteError(f"{placeholder} must appear exactly once in {paths.SW_TEMPLATE}")
        text = text.replace(placeholder, value)
    (out / "sw.js").write_text(text, encoding="utf-8")
    return version


def assemble(out: Path | None = None, pyodide_dir: Path | None = None) -> dict:
    """Build dist/: app shell, content, Pyodide, icons and service worker; then check it."""
    out = out or paths.DIST
    pins = pyodide_fetch.load_pins()
    lock = pyodide_fetch.load_lock(pins)
    _require(paths.APP_BUILD / "index.html", "npx --yes pnpm@11.1.0 build")
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(paths.APP_BUILD, out)
    copy_content(out)
    copy_pyodide(out, pins, lock, pyodide_dir or paths.PYODIDE_CACHE / pins["pyodide"]["version"])
    (out / "icons").mkdir(exist_ok=True)
    for name, size in ICON_SIZES.items():
        (out / "icons" / name).write_bytes(icons.png(size))
    version = write_service_worker(out, pins, lock)
    summary = check_files(out)
    report = links.check_site(out)
    problems = [f"broken link {link!r} on {page}" for page, link in report.broken]
    problems += [f"{name} is missing" for name in REQUIRED if not (out / name).is_file()]
    if problems:
        raise SiteError("\n".join(problems))
    return {
        **summary,
        "version": version,
        "links_checked": report.checked,
        "removed_by_design": len(report.removed_by_design),
    }
```

Replace `johnhull/web/py/hull_web_build/cli.py` with:

```python
"""Command line: python -m hull_web_build <command> (run from the repository root)."""

from __future__ import annotations

import argparse
import json
import sys

from . import golden, package, pyodide_fetch, site


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m hull_web_build")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("fetch-pyodide", help="download and verify the pinned Pyodide files")
    commands.add_parser("package", help="build build/hullkit_browser.zip")
    golden_parser = commands.add_parser(
        "golden", help="write tests/golden.json and src/calc/examples.json"
    )
    golden_parser.add_argument("--check", action="store_true", help="fail instead of writing")
    commands.add_parser("sweep", help="write build/w0-sweep.json (W0 only)")
    commands.add_parser("w0-site", help="assemble the W0 spike site in build/w0-site")
    commands.add_parser("site", help="assemble dist/")
    args = parser.parse_args(argv)

    if args.command == "fetch-pyodide":
        pins = pyodide_fetch.load_pins()
        print(pyodide_fetch.fetch(pins, pyodide_fetch.load_lock(pins)))
    elif args.command == "package":
        print(json.dumps(package.build(), indent=2))
    elif args.command == "golden":
        if args.check:
            stale = golden.stale()
            if stale:
                print(
                    "stale (run python -m hull_web_build golden):",
                    *stale,
                    sep="\n  ",
                    file=sys.stderr,
                )
                return 1
        else:
            for path in golden.write():
                print("wrote", path)
    elif args.command == "sweep":
        print("wrote", golden.write_sweep())
    elif args.command == "w0-site":
        print(json.dumps(site.assemble_w0(), indent=2))
    elif args.command == "site":
        print(json.dumps(site.assemble(), indent=2))
    return 0
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `$PYT -m pytest johnhull/web/py/tests -q`
Expected: `179 passed`.

- [ ] **Step 5: Add the make targets**

In the root `Makefile`:

1. In the `.PHONY` line, replace `hull-release-check hull-release rough-vol` with `hull-release-check hull-release hull-web hull-web-check rough-vol`.
2. In `help`, after the line `@echo "  make hull-release - fresh project tests/lint/notebooks/report/book/release gate"`, add:

```makefile
	@echo "  make hull-web   - build the johnhull web app into johnhull/web/dist/"
	@echo "  make hull-web-check - hull-web, then its unit and browser checks"
```

3. Directly above the `rough-vol:` target, add:

```makefile
# johnhull web app (johnhull/web/README.md). In a git worktree, pass
# HULL_WEB_PY=/home/kazumasa/projects/.venv/bin/python instead of using uv there.
HULL_WEB_PY ?= uv run --no-sync python
HULL_WEB_RUN = PYTHONPATH=johnhull/web/py:johnhull/hullkit/src $(HULL_WEB_PY) -m hull_web_build
HULL_WEB_PNPM = npx --yes pnpm@11.1.0 --dir johnhull/web
CHROMIUM_BIN ?= /home/kazumasa/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome

hull-web:
	$(HULL_WEB_RUN) fetch-pyodide
	$(HULL_WEB_RUN) package
	$(HULL_WEB_RUN) golden --check
	$(HULL_WEB_PNPM) install --frozen-lockfile --ignore-scripts
	$(HULL_WEB_PNPM) run typecheck
	$(HULL_WEB_PNPM) run build
	$(HULL_WEB_RUN) site

hull-web-check: hull-web
	$(HULL_WEB_PNPM) run test:unit
	CHROMIUM_BIN=$(CHROMIUM_BIN) $(HULL_WEB_PNPM) run test:browser
```

Run: `make -n hull-web HULL_WEB_PY=$PY | head -3`
Expected: the first line is `PYTHONPATH=johnhull/web/py:johnhull/hullkit/src /home/kazumasa/projects/.venv/bin/python -m hull_web_build fetch-pyodide`. (`make hull-web` itself fails until Task 10 adds the app.)

- [ ] **Step 6: Lint and commit**

Run: `$PY -m ruff check johnhull/web/py && $PY -m ruff format --check johnhull/web/py`
Expected: `All checks passed!` and `23 files already formatted`.

```bash
git add johnhull/web/py/hull_web_build/links.py johnhull/web/py/hull_web_build/icons.py \
  johnhull/web/py/hull_web_build/site.py johnhull/web/py/hull_web_build/cli.py \
  johnhull/web/py/tests/test_links.py johnhull/web/py/tests/test_icons.py johnhull/web/py/tests/test_site.py Makefile
git commit -m "Assemble dist/ with link and content checks; add make hull-web and hull-web-check"
```

---

### Task 10: The app shell, the calculator UI and the browser checks

**Files:**
- Create: `johnhull/web/playwright.config.ts`, `johnhull/web/tests/helpers.ts`, `tests/calc.spec.ts`, `tests/routes.spec.ts`, `tests/display.spec.ts`, `tests/offline.spec.ts`
- Create: `johnhull/web/vite.config.ts`, `johnhull/web/index.html`, `johnhull/web/calc/binomial/index.html`
- Create: `johnhull/web/src/entry.ts`, `src/sw-register.ts`, `src/styles.css`
- Create: `johnhull/web/public/_headers`, `public/robots.txt`, `public/404.html`, `public/manifest.webmanifest`
- Create: `johnhull/web/src/calc/Form.tsx`, `TreeDiagram.tsx`, `ConvergenceChart.tsx`, `Results.tsx`, `ExampleChecks.tsx`, `App.tsx`, `main.tsx`

**Interfaces:**
- Consumes: everything in `src/calc/*.ts` (Tasks 6–7), `tests/ulps.mts` and `tests/tolerance.json` (Task 5), `tests/golden.json` and `src/calc/examples.json` (Task 4), `make hull-web` (Task 9).
- Behaviour: opening `/calc/binomial/` starts the worker and calculates the default form (plan D-10).
- Produces: the DOM hooks the checks use: `[data-example="<id>"]` buttons; `input[name=<field>]`; `button[type=submit]`; `[data-testid=price]`, `[data-testid=bsm]`, `[data-testid=verdict]` (「一致」/「不一致」), `[data-testid=tree-scroll]`, `[data-node="i,j"]` with class `exercise`, `details.bsm`, `.status button` (中止), `.error[role=alert] button` (再試行); `/calc/binomial/?selftest` exposes `window.__hullCalc(requestText) -> Promise<responseText>`.

- [ ] **Step 1: Write the browser checks**

`johnhull/web/playwright.config.ts`:

```ts
import { defineConfig } from "@playwright/test";

const chromium = process.env.CHROMIUM_BIN;
if (!chromium) throw new Error("Set CHROMIUM_BIN to the Chromium used by the Book checks");
const data = process.env.HULL_WEB_DATA ?? "/home/kazumasa/projects/_data/johnhull/hull-web";

// wrangler pages dev emulates Pages: pretty URLs, _headers, 404.html (W0 ⑤⑥ checked it against Pages rules).
export default defineConfig({
  testDir: "tests",
  testMatch: "*.spec.ts",
  outputDir: `${data}/playwright`,
  workers: 1,
  retries: 0,
  timeout: 300_000,
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:8788",
    browserName: "chromium",
    launchOptions: { executablePath: chromium, args: ["--no-sandbox"] },
    serviceWorkers: "block",
  },
  webServer: {
    command: "npx --yes wrangler@4.147.0 pages dev dist --ip 127.0.0.1 --port 8788 --compatibility-date 2026-10-01",
    url: "http://127.0.0.1:8788/",
    reuseExistingServer: false,
    timeout: 120_000,
    env: { WRANGLER_SEND_METRICS: "false" },
  },
});
```

`johnhull/web/tests/helpers.ts`:

```ts
import type { Page } from "@playwright/test";
import { readFileSync } from "node:fs";

export const DATA_DIR = process.env.HULL_WEB_DATA ?? "/home/kazumasa/projects/_data/johnhull/hull-web";
export const WEB_DIR = new URL("..", import.meta.url).pathname;

// 33 report pages load MathJax from this host (W0 census; the report builder, not this app, links it).
// Nothing else may leave the site.
export const REPORT_EXTERNAL_HOSTS = ["cdn.jsdelivr.net"];

export interface GoldenCase {
  name: string;
  request: string;
  response: string;
}

export interface Example {
  id: string;
  label: string;
}

const read = (name: string) => JSON.parse(readFileSync(new URL(name, import.meta.url), "utf8"));

export const golden = (): GoldenCase[] => read("./golden.json").cases;
export const tolerance = (): { max_ulps: number } => read("./tolerance.json");
export const examples = (): Example[] => read("../src/calc/examples.json").examples;

// Abort every request that leaves 127.0.0.1 (tests never need the internet) and record it.
export async function blockExternal(page: Page): Promise<string[]> {
  const seen: string[] = [];
  await page.route("**/*", (route) => {
    const url = new URL(route.request().url());
    if (url.hostname === "127.0.0.1") return route.continue();
    seen.push(`${url.hostname}${url.pathname}`);
    return route.abort();
  });
  return seen;
}

export async function calcText(page: Page, request: string): Promise<string> {
  return page.evaluate(
    (text) => (window as unknown as { __hullCalc(t: string): Promise<string> }).__hullCalc(text),
    request,
  );
}

export async function runExample(page: Page, example: Example): Promise<string[]> {
  await page.click(`[data-example="${example.id}"]`);
  await page
    .locator(".example-checks h3")
    .filter({ hasText: `${example.label}：原典の値との照合` })
    .waitFor({ timeout: 120_000 });
  return page.locator("[data-testid=verdict]").allTextContents();
}
```

`johnhull/web/tests/calc.spec.ts` (spec §3.4, §3.5, §4, §5 計算の一致・原典の値):

```ts
import { expect, test } from "@playwright/test";
import { calcText, examples, golden, runExample, tolerance } from "./helpers.ts";
import { compareJson } from "./ulps.mts";

test("browser results equal native hullkit within the W0 ulp tolerance (spec §5 計算の一致)", async ({ page }) => {
  const { max_ulps } = tolerance();
  await page.goto("/calc/binomial/?selftest");
  await page.waitForFunction(() => "__hullCalc" in window);
  let worst = { ulps: 0, where: "none" };
  for (const item of golden()) {
    const got = await calcText(page, item.request);
    const result = compareJson(JSON.parse(item.response), JSON.parse(got));
    expect(result.mismatch, `${item.name} ${result.where}`).toBeNull();
    expect(result.maxUlps, `${item.name} ${result.where}`).toBeLessThanOrEqual(max_ulps);
    if (result.maxUlps > worst.ulps) worst = { ulps: result.maxUlps, where: `${item.name} ${result.where}` };
  }
  test.info().annotations.push({ type: "largest difference", description: `${worst.ulps} ulp at ${worst.where}` });
});

test("every example button shows only matching checks (spec §5 原典の値)", async ({ page }) => {
  await page.goto("/calc/binomial/");
  const all = examples();
  expect(all).toHaveLength(11);
  for (const example of all) {
    const verdicts = await runExample(page, example);
    expect(verdicts.length, example.id).toBeGreaterThan(0);
    expect(verdicts.filter((v) => v !== "一致"), example.id).toEqual([]);
  }
});

test("the tree marks early exercise at Hull Fig. 13.10 node C", async ({ page }) => {
  await page.goto("/calc/binomial/");
  await runExample(page, { id: "s13-8", label: "§13.8 σ から作る木（アメリカン・プット、2段）" });
  await expect(page.locator('[data-node="1,1"]')).toHaveClass(/exercise/);
  await expect(page.locator('[data-node="1,0"]')).not.toHaveClass(/exercise/);
});

test("an arbitrage tree is refused with its reason (spec §3.5)", async ({ page }) => {
  await page.goto("/calc/binomial/");
  await page.check('input[name="tree"][value="ud"]');
  for (const [name, value] of [["u", "1.1"], ["d", "1.06"], ["r", "0.05"], ["T", "1"], ["n", "1"]]) {
    await page.fill(`input[name="${name}"]`, value);
  }
  await page.click('button[type="submit"]');
  await expect(page.locator(".error[role=alert]")).toContainText("裁定機会があるため計算しません", { timeout: 120_000 });
});

test("more than 500 steps cannot be submitted (spec §3.5)", async ({ page }) => {
  await page.goto("/calc/binomial/");
  await page.fill('input[name="n"]', "501");
  await expect(page.getByText("1 から 500 までの整数を入れてください")).toBeVisible();
  await expect(page.locator('button[type="submit"]')).toBeDisabled();
});

test("scipy is fetched only when the BSM comparison is opened (spec §3.4)", async ({ page }) => {
  const fetched: string[] = [];
  page.on("request", (request) => fetched.push(new URL(request.url()).pathname));
  await page.goto("/calc/binomial/");
  await page.check('input[name="exercise"][value="european"]');
  await page.click('button[type="submit"]');
  await expect(page.getByTestId("price")).toBeVisible({ timeout: 120_000 });
  expect(fetched.some((path) => path.includes("numpy-"))).toBe(true);
  expect(fetched.some((path) => path.includes("scipy-"))).toBe(false);
  await page.click("details.bsm summary");
  await expect(page.getByTestId("bsm")).toBeVisible({ timeout: 120_000 });
  expect(fetched.some((path) => path.includes("scipy-"))).toBe(true);
});

test("opening the calculator loads Python and numpy, not scipy, and shows §13.10 (spec §3.4)", async ({ page }) => {
  const fetched: string[] = [];
  page.on("request", (request) => fetched.push(new URL(request.url()).pathname));
  await page.goto("/calc/binomial/");
  await expect(page.getByTestId("price")).toContainText("7.67", { timeout: 120_000 });
  expect(fetched.some((path) => path.includes("numpy-"))).toBe(true);
  expect(fetched.some((path) => path.includes("scipy-"))).toBe(false);
});

test("cancel stops loading and the next run starts again (spec §4)", async ({ page }) => {
  await page.goto("/calc/binomial/");
  await page.click(".status button");
  await expect(page.getByText("中止しました")).toBeVisible();
  await page.click('button[type="submit"]');
  await expect(page.getByTestId("price")).toBeVisible({ timeout: 120_000 });
});

test("a failed Pyodide download shows the reason and a working retry (spec §4)", async ({ page, context }) => {
  let block = true;
  await context.route("**/pyodide/hullkit_browser.zip", (route) =>
    block ? route.fulfill({ status: 503, body: "unavailable" }) : route.continue(),
  );
  await page.goto("/calc/binomial/");
  await expect(page.locator(".error[role=alert]")).toContainText("Python の読み込みに失敗しました", { timeout: 120_000 });
  await expect(page.locator(".status")).toHaveCount(0);
  await expect(page.locator('button[type="submit"]')).toBeEnabled();
  block = false;
  await page.click(".error[role=alert] button");
  await expect(page.getByTestId("price")).toBeVisible({ timeout: 120_000 });
});
```

`johnhull/web/tests/routes.spec.ts` (spec §3.2, §3.6, §3.7, W0 ⑥; Review Focus 4):

```ts
import { expect, test } from "@playwright/test";
import { readdirSync } from "node:fs";
import { WEB_DIR } from "./helpers.ts";

const CHAPTER = "/book/_build/html/notebooks/01_foundations";

test("the entry page and the calculator get a CSP; the Book does not (spec §3.7)", async ({ request }) => {
  for (const path of ["/", "/calc/binomial/"]) {
    const headers = (await request.get(path)).headers();
    expect(headers["content-security-policy"], path).toContain("default-src 'self'");
  }
  const worker = readdirSync(`${WEB_DIR}dist/assets`).find((name) => name.startsWith("worker-"));
  const workerHeaders = (await request.get(`/assets/${worker}`)).headers();
  expect(workerHeaders["content-security-policy"]).toContain("'wasm-unsafe-eval'");
  const book = (await request.get(CHAPTER)).headers();
  expect(book["content-security-policy"]).toBeUndefined();
  for (const headers of [book, workerHeaders]) {
    expect(headers["x-robots-tag"]).toBe("noindex");
    expect(headers["x-content-type-options"]).toBe("nosniff");
    expect(headers["referrer-policy"]).toBe("same-origin");
  }
});

test("robots.txt turns every crawler away (spec §3.6)", async ({ request }) => {
  expect(await (await request.get("/robots.txt")).text()).toBe("User-agent: *\nDisallow: /\n");
});

test("missing and left-out paths are 404, not the entry page (spec §3.2)", async ({ request }) => {
  for (const path of ["/no-such-page", "/book/_build/html/_sources/notebooks/00_overview.md", "/book/_build/html/.buildinfo"]) {
    const response = await request.get(path);
    expect(response.status(), path).toBe(404);
    expect(await response.text(), path).toContain("ページが見つかりません");
  }
});

test(".html links redirect to pretty URLs and keep the anchor (spec §6 W0 ⑥)", async ({ page, request }) => {
  const redirect = await request.get(`${CHAPTER}.html`, { maxRedirects: 0 });
  expect(redirect.status()).toBe(308);
  expect(redirect.headers().location).toMatch(/\/book\/_build\/html\/notebooks\/01_foundations$/);
  await page.goto(CHAPTER);
  const anchor = await page.locator("section[id]").nth(1).getAttribute("id");
  await page.goto(`${CHAPTER}.html#${anchor}`);
  expect(new URL(page.url()).hash).toBe(`#${anchor}`);
  await expect(page.locator(`[id="${anchor}"]`)).toBeInViewport();
});

test("Book search works through the pretty-URL redirect (spec §3.6)", async ({ page }) => {
  await page.goto("/book/_build/html/search.html?q=CRR");
  const results = page.locator("#search-results ul.search li a");
  await expect(results.first()).toBeVisible({ timeout: 30_000 });
  const response = await Promise.all([page.waitForNavigation(), results.first().click()]).then(([r]) => r);
  expect(response?.status()).toBe(200);
});

test("the manifest's icons and start page resolve (spec §3.6 PWA)", async ({ request }) => {
  const manifest = await (await request.get("/manifest.webmanifest")).json();
  expect(manifest.start_url).toBe("/");
  for (const icon of manifest.icons) {
    const response = await request.get(icon.src);
    expect(response.status(), icon.src).toBe(200);
    expect(response.headers()["content-type"]).toContain("image/png");
  }
});
```

`johnhull/web/tests/display.spec.ts` (spec §5 表示; screenshots go to `$HULL_WEB_DATA/screenshots/w1/`):

```ts
import { expect, test } from "@playwright/test";
import { mkdirSync, readdirSync } from "node:fs";
import { blockExternal, DATA_DIR, REPORT_EXTERNAL_HOSTS, runExample, WEB_DIR } from "./helpers.ts";

const SHOTS = `${DATA_DIR}/screenshots/w1`;
const WIDTHS = [1280, 390];
const PAGES = [
  ["entry", "/"],
  ["book-index", "/book/_build/html/"],
  ["book-ch13", "/book/_build/html/notebooks/01_foundations"],
  ["report-index", "/report/site/"],
  ["report-ch13", "/report/site/chapters/ch13"],
] as const;

test.beforeAll(() => mkdirSync(SHOTS, { recursive: true }));

for (const width of WIDTHS) {
  test(`reading pages at ${width}px: screenshot, no errors, no Pyodide (spec §5 表示)`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(String(error)));
    const fetched: string[] = [];
    page.on("request", (request) => fetched.push(new URL(request.url()).pathname));
    await blockExternal(page);
    for (const [name, path] of PAGES) {
      const response = await page.goto(path);
      expect(response?.status(), path).toBe(200);
      await page.screenshot({ path: `${SHOTS}/${name}-${width}.png`, fullPage: true });
    }
    expect(errors).toEqual([]);
    expect(fetched.filter((path) => path.startsWith("/pyodide/"))).toEqual([]);
  });

  test(`calculator at ${width}px: screenshot, figures inside the screen (spec §5 表示)`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(String(error)));
    page.on("console", (message) => {
      if (message.type() === "error") errors.push(message.text());
    });
    const external = await blockExternal(page);
    await page.goto("/calc/binomial/");
    await runExample(page, { id: "ex13-2", label: "例題13.2 通貨のアメリカン・コール" });
    await page.screenshot({ path: `${SHOTS}/calculator-${width}.png`, fullPage: true });
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow).toBeLessThanOrEqual(0);
    for (const selector of ["[data-testid=tree-scroll]", "figure.chart svg"]) {
      const box = await page.locator(selector).boundingBox();
      expect(box, selector).not.toBeNull();
      expect((box?.x ?? 0) + (box?.width ?? 0), selector).toBeLessThanOrEqual(width);
    }
    expect(errors).toEqual([]);
    expect(external).toEqual([]);
  });
}

test("every page: no page errors and no external requests beyond the report CDN hosts (spec §5 表示)", async ({ page }) => {
  const pages: string[] = [];
  const walk = (dir: string, prefix: string) => {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      if (entry.isDirectory() && entry.name !== "_static") walk(`${dir}/${entry.name}`, `${prefix}${entry.name}/`);
      else if (entry.name.endsWith(".html")) pages.push(`${prefix}${entry.name}`);
    }
  };
  walk(`${WEB_DIR}dist`, "/");
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(`${page.url()}: ${error}`));
  const external = await blockExternal(page);
  for (const path of pages.filter((p) => p !== "/404.html")) {
    const before = external.length;
    const response = await page.goto(path);
    expect(response?.status(), path).toBe(200);
    const added = external.slice(before);
    const allowed = path.startsWith("/report/site/")
      ? added.filter((url) => !REPORT_EXTERNAL_HOSTS.includes(url.split("/")[0]))
      : added;
    expect(allowed, path).toEqual([]);
  }
  expect(errors).toEqual([]);
});
```

`johnhull/web/tests/offline.spec.ts` (spec §3.6, §5 オフライン; its own `wrangler` on port 8790, so the test can take the network away by stopping it):

```ts
import { expect, test } from "@playwright/test";
import { type ChildProcess, spawn } from "node:child_process";
import { examples, runExample, WEB_DIR } from "./helpers.ts";

// Its own server, so the test can take the network away by stopping it.
const PORT = 8790;
const ORIGIN = `http://127.0.0.1:${PORT}`;
let server: ChildProcess | null = null;

async function waitUntilUp(): Promise<void> {
  for (let attempt = 0; attempt < 120; attempt++) {
    try {
      if ((await fetch(`${ORIGIN}/`)).ok) return;
    } catch {
      // not up yet
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  throw new Error("wrangler did not start");
}

function stopServer(): void {
  if (server?.pid) process.kill(-server.pid, "SIGTERM");
  server = null;
}

test.use({ serviceWorkers: "allow", baseURL: ORIGIN });

test.beforeAll(async () => {
  server = spawn("npx", ["--yes", "wrangler@4.147.0", "pages", "dev", "dist", "--ip", "127.0.0.1", "--port", String(PORT), "--compatibility-date", "2026-10-01"], {
    cwd: WEB_DIR,
    env: { ...process.env, WRANGLER_SEND_METRICS: "false" },
    stdio: "ignore",
    detached: true,
  });
  await waitUntilUp();
});

test.afterAll(() => stopServer());

test("pages and the calculator opened once keep working offline (spec §3.6, §5 オフライン)", async ({ page }) => {
  const byId = new Map(examples().map((example) => [example.id, example]));
  await page.goto("/");
  await page.waitForFunction(async () => (await navigator.serviceWorker.ready).active !== null);
  await page.reload();
  await page.waitForFunction(() => navigator.serviceWorker.controller !== null);
  await page.goto("/calc/binomial/");
  await runExample(page, byId.get("s13-8")!);
  await page.goto("/book/_build/html/notebooks/01_foundations.html");
  await expect(page.locator("h1:visible").first()).toContainText("基礎編");

  stopServer();
  await expect.poll(async () => fetch(`${ORIGIN}/`).then(() => "up", () => "down")).toBe("down");

  await page.goto("/calc/binomial/");
  const verdicts = await runExample(page, byId.get("ex13-1")!);
  expect(verdicts.filter((v) => v !== "一致")).toEqual([]);
  for (const path of ["/book/_build/html/notebooks/01_foundations.html", "/book/_build/html/notebooks/01_foundations"]) {
    await page.goto(path);
    await expect(page.locator("h1:visible").first()).toContainText("基礎編");
  }
  const unsaved = await page.goto("/report/site/");
  expect(unsaved?.status()).toBe(503);
  await expect(page.getByText("このページはまだこの端末に保存されていません")).toBeVisible();
});
```

- [ ] **Step 2: Run them to see the build fail**

Run: `make hull-web HULL_WEB_PY=$PY`
Expected: FAIL at `npx --yes pnpm@11.1.0 --dir johnhull/web run build` with `[UNRESOLVED_ENTRY] Cannot resolve entry module index.html.` (there is no app yet).

- [ ] **Step 3: Write the app shell and the static files**

`johnhull/web/vite.config.ts`:

```ts
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const root = import.meta.dirname;

// Builds only the app shell (entry page and calculator) into build/app;
// hull_web_build.site adds the Book, the supplementary site and Pyodide to dist/.
export default defineConfig({
  root,
  plugins: [react()],
  build: {
    outDir: "build/app",
    emptyOutDir: true,
    modulePreload: { polyfill: false },
    rolldownOptions: {
      input: {
        entry: `${root}/index.html`,
        binomial: `${root}/calc/binomial/index.html`,
      },
    },
  },
  worker: { format: "es" },
});
```

`johnhull/web/index.html`:

```html
<!doctype html>
<html lang="ja">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="robots" content="noindex" />
    <title>johnhull — デリバティブの数理を動かして学ぶ</title>
    <link rel="manifest" href="/manifest.webmanifest" />
    <link rel="icon" href="/icons/icon-192.png" />
    <link rel="apple-touch-icon" href="/icons/apple-touch-icon.png" />
    <meta name="theme-color" content="#1f3a5f" />
    <link rel="stylesheet" href="/src/styles.css" />
    <script type="module" src="/src/entry.ts"></script>
  </head>
  <body>
    <main class="entry">
      <h1>johnhull — デリバティブの数理を動かして学ぶ</h1>
      <p>Hull『Options, Futures, and Other Derivatives』11版の学習ノートです。</p>
      <ul class="cards">
        <li>
          <a href="/book/_build/html/"><strong>Book</strong><span>巻・章ごとのノートとモデル地図</span></a>
        </li>
        <li>
          <a href="/report/site/"><strong>補足教材</strong><span>章ごとの補足と可視化ポータル</span></a>
        </li>
        <li>
          <a href="/calc/binomial/"
            ><strong>二項木の計算機</strong><span>第13章の木をその場で計算します（初回は Python を読み込みます）</span></a
          >
        </li>
      </ul>
      <p class="note">一度開いたページと計算機は、オフラインでも開けます。</p>
    </main>
  </body>
</html>
```

`johnhull/web/calc/binomial/index.html`:

```html
<!doctype html>
<html lang="ja">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="robots" content="noindex" />
    <title>二項木の計算機 — johnhull</title>
    <link rel="manifest" href="/manifest.webmanifest" />
    <link rel="icon" href="/icons/icon-192.png" />
    <link rel="apple-touch-icon" href="/icons/apple-touch-icon.png" />
    <meta name="theme-color" content="#1f3a5f" />
    <link rel="stylesheet" href="/src/styles.css" />
    <script type="module" src="/src/calc/main.tsx"></script>
  </head>
  <body>
    <div id="root"></div>
    <noscript>この計算機は JavaScript を使います。</noscript>
  </body>
</html>
```

`johnhull/web/src/entry.ts`:

```ts
import { registerServiceWorker } from "./sw-register.ts";

registerServiceWorker();
```

`johnhull/web/src/sw-register.ts`:

```ts
// /sw.js is generated into dist/ by hull_web_build.site; under `vite dev` it does not exist.
export function registerServiceWorker(): void {
  if (!("serviceWorker" in navigator)) return;
  navigator.serviceWorker.register("/sw.js").catch((error: unknown) => {
    console.warn("service worker not registered:", error);
  });
}
```

`johnhull/web/src/styles.css`:

```css
:root {
  --bg: #ffffff;
  --fg: #1d2330;
  --muted: #5b6475;
  --line: #c9d1de;
  --accent: #1f3a5f;
  --accent-fg: #ffffff;
  --card: #f4f6fa;
  --good: #1f7a3a;
  --bad: #b3261e;
  --exercise: #ffe3b3;
  color-scheme: light dark;
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg: #12161d;
    --fg: #e6e9ef;
    --muted: #9aa3b2;
    --line: #3a4352;
    --accent: #8fb3e8;
    --accent-fg: #12161d;
    --card: #1b212b;
    --good: #6cc48a;
    --bad: #f08a80;
    --exercise: #5a4318;
  }
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  background: var(--bg);
  color: var(--fg);
  font-family: system-ui, -apple-system, "Hiragino Sans", "Noto Sans JP", sans-serif;
  line-height: 1.6;
}

main {
  max-width: 960px;
  margin: 0 auto;
  padding: 16px;
}

a {
  color: var(--accent);
}

h1 {
  font-size: 1.5rem;
  line-height: 1.3;
}

.cards {
  list-style: none;
  padding: 0;
  display: grid;
  gap: 12px;
}

.cards a {
  display: block;
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--card);
  text-decoration: none;
  color: var(--fg);
}

.cards strong {
  display: block;
  font-size: 1.1rem;
  color: var(--accent);
}

.note,
.sources,
figcaption,
.hint {
  color: var(--muted);
  font-size: 0.9rem;
}

.example-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

button {
  font: inherit;
  padding: 6px 12px;
  border-radius: 6px;
  border: 1px solid var(--accent);
  background: var(--accent);
  color: var(--accent-fg);
  cursor: pointer;
}

.example-buttons button {
  background: transparent;
  color: var(--accent);
}

button:disabled {
  opacity: 0.5;
  cursor: default;
}

.calc-form {
  margin-top: 16px;
  display: grid;
  gap: 12px;
}

.choices {
  border: 1px solid var(--line);
  border-radius: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px 16px;
}

.fields {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
  align-items: start;
}

.field {
  display: grid;
  gap: 2px;
  align-content: start;
}

.field input {
  font: inherit;
  padding: 6px 8px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: var(--bg);
  color: var(--fg);
  min-width: 0;
}

.field input[aria-invalid="true"] {
  border-color: var(--bad);
}

.error {
  color: var(--bad);
}

.status {
  display: flex;
  align-items: center;
  gap: 12px;
}

.price {
  font-size: 1.3rem;
}

.params th {
  text-align: left;
  font-weight: normal;
  padding-right: 16px;
}

.figure-scroll,
.table-scroll {
  max-width: 100%;
  overflow-x: auto;
}

figure {
  margin: 16px 0;
}

.tree svg,
.chart svg {
  display: block;
  height: auto;
}

.chart svg {
  width: 100%;
  max-width: 600px;
}

.node rect {
  fill: var(--card);
  stroke: var(--line);
}

.node.exercise rect {
  fill: var(--exercise);
  stroke: var(--accent);
}

.node text,
.tick {
  fill: var(--fg);
  font-size: 13px;
  font-family: ui-monospace, "SFMono-Regular", Menlo, monospace;
}

.tick {
  font-size: 15px;
}

.edge,
.axis {
  stroke: var(--line);
  stroke-width: 1.5;
}

.series {
  fill: none;
  stroke: var(--accent);
  stroke-width: 2;
}

.bsm {
  stroke: var(--bad);
  stroke-dasharray: 6 4;
  stroke-width: 1.5;
}

details.bsm summary {
  cursor: pointer;
  color: var(--accent);
}

.legend-exercise {
  background: var(--exercise);
  padding: 0 4px;
}

.example-checks table {
  border-collapse: collapse;
  font-size: 0.9rem;
}

.example-checks th,
.example-checks td {
  border-bottom: 1px solid var(--line);
  padding: 4px 8px;
  text-align: right;
  white-space: nowrap;
}

.example-checks td:first-child,
.example-checks th:first-child {
  text-align: left;
}

.example-checks tr.pass td.verdict {
  color: var(--good);
}

.example-checks tr.fail td.verdict {
  color: var(--bad);
  font-weight: bold;
}

.sources code {
  display: block;
  overflow-wrap: anywhere;
}
```

`johnhull/web/public/_headers` (CSP only on the entry page, the calculator and `/assets/*`, where the worker script is; plan D-5):

```text
/*
  X-Robots-Tag: noindex
  X-Content-Type-Options: nosniff
  Referrer-Policy: same-origin

/
  Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; worker-src 'self'; manifest-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'

/calc/*
  Content-Security-Policy: default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self'; img-src 'self' data:; connect-src 'self'; worker-src 'self'; manifest-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'

/assets/*
  Content-Security-Policy: default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self'; img-src 'self' data:; connect-src 'self'; worker-src 'self'; manifest-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'
```

`johnhull/web/public/robots.txt`:

```text
User-agent: *
Disallow: /
```

`johnhull/web/public/404.html` (plan D-1):

```html
<!doctype html>
<html lang="ja">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="robots" content="noindex" />
    <title>ページが見つかりません — johnhull</title>
  </head>
  <body>
    <h1>ページが見つかりません</h1>
    <p><a href="/">入口へ戻る</a></p>
  </body>
</html>
```

`johnhull/web/public/manifest.webmanifest`:

```json
{
  "name": "johnhull — デリバティブの数理を動かして学ぶ",
  "short_name": "johnhull",
  "lang": "ja",
  "start_url": "/",
  "scope": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#1f3a5f",
  "icons": [
    { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

- [ ] **Step 4: Write the calculator components**

`johnhull/web/src/calc/Form.tsx`:

```tsx
import { percentHint } from "./format.ts";
import type { FieldErrors, FormState, NumberField } from "./params.ts";
import { visibleFields } from "./params.ts";

interface Choice<T extends string> {
  value: T;
  label: string;
}

const TREES: Choice<FormState["tree"]>[] = [
  { value: "crr", label: "σ から作る（CRR、§13.7 以降）" },
  { value: "ud", label: "u と d を直接入れる（§13.1〜13.5）" },
];
const ASSETS: Choice<FormState["asset"]>[] = [
  { value: "stock", label: "株式（配当なし）" },
  { value: "index", label: "株価指数（配当利回り q）" },
  { value: "currency", label: "通貨（外国の金利 r_f）" },
  { value: "futures", label: "先物（a = 1）" },
];
const KINDS: Choice<FormState["kind"]>[] = [
  { value: "call", label: "コール" },
  { value: "put", label: "プット" },
];
const EXERCISE: Choice<"european" | "american">[] = [
  { value: "european", label: "ヨーロピアン" },
  { value: "american", label: "アメリカン" },
];
const RATE_FIELDS = new Set<NumberField>(["r", "q", "sigma"]);

function fieldLabel(field: NumberField, form: FormState): string {
  switch (field) {
    case "S0":
      return form.asset === "futures" ? "F0（先物価格）" : "S0（現在の価格）";
    case "K":
      return "K（行使価格）";
    case "r":
      return "r（無リスク金利、年率。5% は 0.05）";
    case "q":
      return form.asset === "currency" ? "r_f（外国の無リスク金利、年率）" : "q（配当利回り、年率）";
    case "sigma":
      return "σ（ボラティリティ、年率）";
    case "u":
      return "u（1 段で上がる倍率）";
    case "d":
      return "d（1 段で下がる倍率）";
    case "T":
      return "T（満期までの年数）";
    case "n":
      return "n（段数、1〜500）";
  }
}

function Radio<T extends string>(props: {
  name: string;
  legend: string;
  choices: Choice<T>[];
  value: T;
  onChange: (value: T) => void;
}) {
  return (
    <fieldset className="choices">
      <legend>{props.legend}</legend>
      {props.choices.map((choice) => (
        <label key={choice.value}>
          <input
            type="radio"
            name={props.name}
            value={choice.value}
            checked={props.value === choice.value}
            onChange={() => props.onChange(choice.value)}
          />
          {choice.label}
        </label>
      ))}
    </fieldset>
  );
}

export function Form(props: {
  form: FormState;
  errors: FieldErrors;
  disabled: boolean;
  onChange: (form: FormState) => void;
  onSubmit: () => void;
}) {
  const { form, errors } = props;
  const set = (change: Partial<FormState>) => props.onChange({ ...form, ...change });
  return (
    <form
      className="calc-form"
      onSubmit={(event) => {
        event.preventDefault();
        props.onSubmit();
      }}
    >
      <Radio name="tree" legend="木の作り方" choices={TREES} value={form.tree} onChange={(tree) => set({ tree })} />
      <Radio name="asset" legend="原資産" choices={ASSETS} value={form.asset} onChange={(asset) => set({ asset })} />
      <Radio name="kind" legend="オプション" choices={KINDS} value={form.kind} onChange={(kind) => set({ kind })} />
      <Radio
        name="exercise"
        legend="行使のしかた"
        choices={EXERCISE}
        value={form.american ? "american" : "european"}
        onChange={(value) => set({ american: value === "american" })}
      />
      <div className="fields">
        {visibleFields(form).map((field) => (
          <label key={field} className="field">
            <span>{fieldLabel(field, form)}</span>
            <input
              name={field}
              inputMode="decimal"
              autoComplete="off"
              value={form[field]}
              aria-invalid={errors[field] ? true : undefined}
              onChange={(event) => set({ [field]: event.target.value })}
            />
            {RATE_FIELDS.has(field) && <small className="hint">{percentHint(form[field])}</small>}
            {errors[field] && <small className="error">{errors[field]}</small>}
          </label>
        ))}
      </div>
      <button type="submit" disabled={props.disabled}>
        計算する
      </button>
    </form>
  );
}
```

`johnhull/web/src/calc/TreeDiagram.tsx` (the diagram scrolls inside its box below 70% of its natural width instead of shrinking further):

```tsx
import { formatValue } from "./format.ts";
import { BOX, treeLayout } from "./layout.ts";
import type { TreeNodes } from "./protocol.ts";

// Below 70% of its natural width the diagram scrolls inside its box instead of shrinking further.
const MIN_SCALE = 0.7;

export function TreeDiagram({ tree }: { tree: TreeNodes }) {
  const n = tree.stock.length - 1;
  const layout = treeLayout(n);
  const anyExercise = tree.exercise.some((level) => level.some(Boolean));
  return (
    <figure className="tree">
      <div className="figure-scroll" data-testid="tree-scroll">
        <svg
          viewBox={`0 0 ${layout.width} ${layout.height}`}
          style={{ width: "100%", minWidth: `${Math.round(layout.width * MIN_SCALE)}px`, maxWidth: `${layout.width}px` }}
          role="img"
          aria-label={`${n} 段の二項木`}
        >
          {layout.edges.map(([a, b]) => (
            <line
              key={`${a.i}-${a.j}-${b.j}`}
              className="edge"
              x1={a.x + BOX.w}
              y1={a.y + BOX.h / 2}
              x2={b.x}
              y2={b.y + BOX.h / 2}
            />
          ))}
          {layout.nodes.map((node) => {
            const exercise = node.i < n && tree.exercise[node.i][node.j];
            const delta = node.i < n ? tree.delta[node.i][node.j] : null;
            return (
              <g key={`${node.i}-${node.j}`} className={exercise ? "node exercise" : "node"} data-node={`${node.i},${node.j}`}>
                <rect x={node.x} y={node.y} width={BOX.w} height={BOX.h} rx={6} />
                <text x={node.x + 6} y={node.y + 16}>
                  S {formatValue(tree.stock[node.i][node.j])}
                </text>
                <text x={node.x + 6} y={node.y + 32}>
                  f {formatValue(tree.option[node.i][node.j])}
                </text>
                {delta !== null && (
                  <text x={node.x + 6} y={node.y + 48}>
                    Δ {formatValue(delta, 4)}
                  </text>
                )}
              </g>
            );
          })}
        </svg>
      </div>
      <figcaption>
        各節点：S は原資産の価格、f はオプションの価値、Δ はその節点でのデルタ。
        {anyExercise && <span className="legend-exercise">色の付いた節点で早期行使します。</span>}
      </figcaption>
    </figure>
  );
}
```

`johnhull/web/src/calc/ConvergenceChart.tsx`:

```tsx
import { chartLayout } from "./layout.ts";
import type { ConvergenceResult } from "./protocol.ts";

export function ConvergenceChart({ result, bsm }: { result: ConvergenceResult; bsm: number | null }) {
  const layout = chartLayout(result.steps, result.prices, bsm);
  const { left, top, right, bottom } = layout.plot;
  return (
    <figure className="chart">
      <svg viewBox={`0 0 ${layout.width} ${layout.height}`} role="img" aria-label="段数と価格">
        <line className="axis" x1={left} y1={bottom} x2={right} y2={bottom} />
        <line className="axis" x1={left} y1={top} x2={left} y2={bottom} />
        {layout.xTicks.map((tick) => (
          <text key={tick.label} className="tick" x={tick.at} y={bottom + 22} textAnchor="middle">
            {tick.label}
          </text>
        ))}
        {layout.yTicks.map((tick) => (
          <text key={tick.at} className="tick" x={left - 8} y={tick.at + 5} textAnchor="end">
            {tick.label}
          </text>
        ))}
        <text className="tick" x={(left + right) / 2} y={layout.height - 4} textAnchor="middle">
          段数 n（対数目盛）
        </text>
        {layout.segments.map((d) => (
          <path key={d} className="series" d={d} />
        ))}
        {layout.bsmY !== null && <line className="bsm" x1={left} y1={layout.bsmY} x2={right} y2={layout.bsmY} />}
      </svg>
      <figcaption>
        n を変えたときの木の価格。
        {layout.bsmY !== null && "破線は BSM の価格。"}
        {result.prices.some((p) => p === null) && "線が切れている段では裁定条件が成り立たず、計算していません。"}
      </figcaption>
    </figure>
  );
}
```

`johnhull/web/src/calc/Results.tsx`:

```tsx
import { ConvergenceChart } from "./ConvergenceChart.tsx";
import { formatValue } from "./format.ts";
import type { ConvergenceResult, PriceResult } from "./protocol.ts";
import { TreeDiagram } from "./TreeDiagram.tsx";

export function Results(props: { price: PriceResult; convergence: ConvergenceResult | null; bsm: number | null }) {
  const { price, params } = { price: props.price, params: props.price.params };
  const rows: [string, number][] = [
    ["p（上昇の確率）", params.p],
    ["a = exp((r − q)Δt)", params.a],
    ["u", params.u],
    ["d", params.d],
    ["Δt", params.dt],
    ["q（計算に使った値）", params.q],
  ];
  return (
    <section className="results" aria-live="polite">
      <p className="price">
        価格 <output data-testid="price">{formatValue(price.price, 8)}</output>
      </p>
      <table className="params">
        <tbody>
          {rows.map(([label, value]) => (
            <tr key={label}>
              <th scope="row">{label}</th>
              <td>{formatValue(value, 8)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {price.tree ? <TreeDiagram tree={price.tree} /> : <p className="note">木の図は 6 段以下のときに表示します。</p>}
      {props.convergence && <ConvergenceChart result={props.convergence} bsm={props.bsm} />}
    </section>
  );
}
```

`johnhull/web/src/calc/ExampleChecks.tsx` (the verdict is the second column so a phone shows it without scrolling; the difference column is against the printed value, the verdict against the pinned expected value with the pinned tolerance):

```tsx
import { type Example, passes, quantityLabel, quantityValue } from "./checks.ts";
import { formatDiff, formatValue } from "./format.ts";
import type { PriceResult } from "./protocol.ts";

export function ExampleChecks(props: { example: Example; price: PriceResult; bsm: number | null }) {
  const sources = [...new Set(props.example.checks.map((check) => check.source))];
  const notes = [...new Set(props.example.checks.map((check) => check.note).filter(Boolean))];
  return (
    <section className="example-checks">
      <h3>{props.example.label}：原典の値との照合</h3>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>項目</th>
              <th>判定</th>
              <th>計算値</th>
              <th>原典の表示</th>
              <th>差</th>
              <th>許容差</th>
            </tr>
          </thead>
          <tbody>
            {props.example.checks.map((check, k) => {
              const value = quantityValue(check.quantity, props.price, props.bsm);
              const ok = value !== null && passes(check, value);
              return (
                <tr key={`${check.quantity}-${k}`} className={ok ? "pass" : "fail"}>
                  <td>{quantityLabel(check.quantity)}</td>
                  <td className="verdict" data-testid="verdict">
                    {ok ? "一致" : "不一致"}
                  </td>
                  <td>{value === null ? "—" : formatValue(value, 8)}</td>
                  <td>{check.printed ?? check.expected}</td>
                  <td>{value === null ? "—" : formatDiff(Math.abs(value - Number(check.printed ?? check.expected)))}</td>
                  <td>{check.tol}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {notes.map((note) => (
        <p key={note} className="note">
          {note}。許容差は固定テストと同じで、固定テストの期待値（
          {props.example.checks.filter((c) => c.note === note).map((c) => c.expected).join("、")}）に対して判定しています。
        </p>
      ))}
      <p className="sources">
        期待値の出典（hullkit の固定テスト）：
        {sources.map((source) => (
          <code key={source}>{source}</code>
        ))}
      </p>
    </section>
  );
}
```

`johnhull/web/src/calc/App.tsx`:

```tsx
import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { type Example, needsBsm } from "./checks.ts";
import { CalcCancelled, CalcFailed, type CalcClient } from "./client.ts";
import data from "./examples.json";
import { ExampleChecks } from "./ExampleChecks.tsx";
import { Form } from "./Form.tsx";
import { formatDiff, formatValue } from "./format.ts";
import { describeError, STAGE_TEXT } from "./messages.ts";
import { DEFAULT_FORM, type FormState, formFromRequest, parseForm } from "./params.ts";
import type { BsmResult, Contract, ConvergenceResult, PriceResult } from "./protocol.ts";
import { Results } from "./Results.tsx";

const EXAMPLES = data.examples as Example[];
const BOOK_CHAPTER = "/book/_build/html/notebooks/01_foundations.html";

type Done = {
  status: "done";
  contract: Contract;
  example: Example | null;
  price: PriceResult;
  convergence: ConvergenceResult | null;
  bsm: number | null;
  bsmError: string | null;
};

type RunState =
  | { status: "idle" }
  | { status: "running" }
  | Done
  | { status: "rejected"; message: string }
  | { status: "failed"; stage: "load" | "run"; message: string }
  | { status: "cancelled" };

export function App({ client }: { client: CalcClient }) {
  const stage = useSyncExternalStore(client.subscribe, client.getStage);
  const [form, setForm] = useState<FormState>(DEFAULT_FORM);
  const [example, setExample] = useState<Example | null>(null);
  const [state, setState] = useState<RunState>({ status: "idle" });
  const [bsmOpen, setBsmOpen] = useState(false);
  const run = useRef(0);
  const parsed = parseForm(form);
  const busy = state.status === "running" || (stage !== "idle" && stage !== "ready");

  function settle(token: number, error: unknown) {
    if (token !== run.current) return;
    if (error instanceof CalcCancelled) setState({ status: "cancelled" });
    else if (error instanceof CalcFailed) setState({ status: "failed", stage: error.stage, message: error.message });
    else throw error;
  }

  async function bsmFor(contract: Contract): Promise<Pick<Done, "bsm" | "bsmError">> {
    const result = await client.calc<BsmResult>({ op: "bsm", ...contract });
    return result.ok ? { bsm: result.bsm, bsmError: null } : { bsm: null, bsmError: describeError(result.error) };
  }

  async function calculate(nextForm: FormState, nextExample: Example | null) {
    const input = parseForm(nextForm);
    if (!input.ok) return;
    const token = ++run.current;
    setState({ status: "running" });
    try {
      const contract = input.contract;
      const price = await client.calc<PriceResult>({ op: "price", ...contract });
      if (!price.ok) {
        if (token === run.current) setState({ status: "rejected", message: describeError(price.error) });
        return;
      }
      let convergence: ConvergenceResult | null = null;
      if (contract.tree === "crr") {
        const result = await client.calc<ConvergenceResult>({ op: "convergence", ...contract });
        convergence = result.ok ? result : null;
      }
      const wantBsm = contract.tree === "crr" && !contract.american && (bsmOpen || needsBsm(nextExample));
      const extra = wantBsm ? await bsmFor(contract) : { bsm: null, bsmError: null };
      if (token === run.current) {
        setState({ status: "done", contract, example: nextExample, price, convergence, ...extra });
      }
    } catch (error) {
      settle(token, error);
    }
  }

  async function openBsm(current: Done) {
    setBsmOpen(true);
    if (current.bsm !== null || current.bsmError !== null) return;
    const token = run.current;
    try {
      const extra = await bsmFor(current.contract);
      if (token === run.current) setState({ ...current, ...extra });
    } catch (error) {
      settle(token, error);
    }
  }

  // Opening the calculator loads Python and numpy (spec §3.4, §3.6) and shows the default, Hull §13.10.
  // Runs once per page; `calculate` reads the state it needs when called.
  useEffect(() => {
    void calculate(DEFAULT_FORM, null);
  }, []);

  function chooseExample(next: Example) {
    const nextForm = formFromRequest(next.request, form);
    setForm(nextForm);
    setExample(next);
    void calculate(nextForm, next);
  }

  return (
    <main className="calc">
      <header>
        <p className="crumbs">
          <a href="/">入口</a> / 二項木の計算機
        </p>
        <h1>二項木の計算機</h1>
        <p>
          Hull『Options, Futures, and Other Derivatives』11版（Global Edition）第13章の二項木を、ブラウザの中の
          Python（Pyodide）と hullkit で計算します。<a href={BOOK_CHAPTER}>Book の該当章へ</a>
        </p>
      </header>
      <section aria-label="例題">
        <h2>例題</h2>
        <div className="example-buttons">
          {EXAMPLES.map((item) => (
            <button key={item.id} type="button" data-example={item.id} disabled={busy} onClick={() => chooseExample(item)}>
              {item.label}
            </button>
          ))}
        </div>
      </section>
      <Form
        form={form}
        errors={parsed.ok ? {} : parsed.errors}
        disabled={!parsed.ok || busy}
        onChange={(next) => {
          setForm(next);
          setExample(null);
        }}
        onSubmit={() => void calculate(form, example)}
      />
      {busy && (
        <p className="status" role="status">
          {STAGE_TEXT[stage === "idle" ? "ready" : stage]}
          <button type="button" onClick={() => client.cancel()}>
            中止
          </button>
        </p>
      )}
      {state.status === "cancelled" && (
        <p className="status">中止しました。次に計算するときは Python を読み込み直します。</p>
      )}
      {state.status === "rejected" && (
        <p className="error" role="alert">
          {state.message}
        </p>
      )}
      {state.status === "failed" && (
        <div className="error" role="alert">
          <p>
            {state.stage === "load" ? "Python の読み込みに失敗しました" : "計算の途中でエラーが起きました"}：
            {state.message}
          </p>
          <button
            type="button"
            onClick={() => {
              client.reset();
              void calculate(form, example);
            }}
          >
            再試行
          </button>
        </div>
      )}
      {state.status === "done" && (
        <>
          {state.example && <ExampleChecks example={state.example} price={state.price} bsm={state.bsm} />}
          <Results price={state.price} convergence={state.convergence} bsm={state.bsm} />
          {state.contract.tree === "crr" && !state.contract.american && (
            <details
              className="bsm"
              open={bsmOpen}
              onToggle={(event) => {
                if (event.currentTarget.open) void openBsm(state);
                else setBsmOpen(false);
              }}
            >
              <summary>BSM と比べる（初回は scipy を読み込みます）</summary>
              {state.bsm !== null && (
                <p>
                  BSM の価格 <output data-testid="bsm">{formatValue(state.bsm, 8)}</output>（木 − BSM ={" "}
                  {formatDiff(state.price.price - state.bsm)}）
                </p>
              )}
              {state.bsmError && <p className="error">{state.bsmError}</p>}
            </details>
          )}
        </>
      )}
    </main>
  );
}
```

`johnhull/web/src/calc/main.tsx`:

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { registerServiceWorker } from "../sw-register.ts";
import { App } from "./App.tsx";
import { CalcClient } from "./client.ts";

const client = new CalcClient();

// Test hook for the golden comparison (spec §5): /calc/binomial/?selftest exposes run() as raw text.
if (new URLSearchParams(window.location.search).has("selftest")) {
  Object.assign(window, { __hullCalc: (request: string) => client.calcText(request) });
}

const root = document.getElementById("root");
if (!root) throw new Error("#root is missing");
createRoot(root).render(
  <StrictMode>
    <App client={client} />
  </StrictMode>,
);
registerServiceWorker();
```

- [ ] **Step 5: Build the site**

Run: `make hull-web HULL_WEB_PY=$PY`
Expected: `tsc` passes, `vite build` writes `build/app/index.html`, `build/app/calc/binomial/index.html` and `build/app/assets/worker-*.js`, and the last command prints the site summary (plan check: `"files": 511`, `"links_checked": 3411`, `"removed_by_design": 31`). A `SiteError` names the broken link or the missing file.

- [ ] **Step 6: Run the unit and browser checks**

Run: `make hull-web-check HULL_WEB_PY=$PY`
Expected: `ℹ pass 45` for the unit tests, then `21 passed` for Playwright (9 in `calc.spec.ts`, 6 in `routes.spec.ts`, 5 in `display.spec.ts`, 1 in `offline.spec.ts`). The golden test's annotation names the largest difference, which must not exceed `tests/tolerance.json`.

- [ ] **Step 7: Commit**

```bash
git add johnhull/web/playwright.config.ts johnhull/web/tests/helpers.ts johnhull/web/tests/calc.spec.ts \
  johnhull/web/tests/routes.spec.ts johnhull/web/tests/display.spec.ts johnhull/web/tests/offline.spec.ts \
  johnhull/web/vite.config.ts johnhull/web/index.html johnhull/web/calc johnhull/web/src/entry.ts \
  johnhull/web/src/sw-register.ts johnhull/web/src/styles.css johnhull/web/public johnhull/web/src/calc/*.tsx
git commit -m "Add the entry page and the binomial calculator UI with browser checks (hull web W1)"
```

---

### Task 11: W1 record, README and regression checks

**Files:**
- Create: `johnhull/web/README.md`, `johnhull/docs/validation/hull-web/w1.json`
- Modify: `johnhull/ROADMAP.md`

- [ ] **Step 1: Look at the screenshots**

Open the 12 files in `$HULL_WEB_DATA/screenshots/w1/` (entry, Book index, Book Ch.13–14, report index, report Ch.13, calculator; each at 1280 and 390 px). Check by eye (spec §5 表示): nothing overlaps or is cut off; at 390 px the form is one column, the verdict column of the example table is visible, the tree scrolls inside its box, and the chart fits the screen; Japanese text renders (no boxes). Write down anything you see.

- [ ] **Step 2: Write the W1 record**

`johnhull/docs/validation/hull-web/w1.json`, every value from this branch's last `make hull-web-check` output or a command shown here:

```json
{
  "checked_at": "<ISO time of the run>",
  "commit": "<git rev-parse HEAD>",
  "tools": {"node": "<node --version>", "pnpm": "11.1.0", "playwright": "1.56.0", "chromium": "ms-playwright chromium-1208", "wrangler": "4.147.0", "pyodide": "314.0.7"},
  "site": {"files": 0, "bytes": 0, "version": "", "links_checked": 0, "removed_by_design": 0},
  "python_tests": "<last line of $PYT -m pytest johnhull/web/py/tests -q>",
  "unit_tests": {"tests": 45, "pass": 45},
  "browser_tests": {"passed": 21, "failed": 0, "largest_golden_difference": "<the golden test's annotation>"},
  "external_requests": {"allowed_on_report_pages": ["cdn.jsdelivr.net"]},
  "screenshots": {"dir": "$HULL_WEB_DATA/screenshots/w1", "files": {"<name>.png": "<sha256>"}, "observations": ["<what you saw>"]}
}
```

Fill `site` from the `site` command's JSON; `screenshots.files` from `sha256sum $HULL_WEB_DATA/screenshots/w1/*.png`.

- [ ] **Step 3: Write the README**

`johnhull/web/README.md`:

````markdown
# johnhull web — 読む＋その場で計算する

Book・補足教材・二項木の計算機をブラウザで使えるようにしたサイトです。今は本人だけが
Cloudflare Access の後ろで使います。設計は[設計書](../docs/superpowers/specs/2026-10-18-hull-web-app-design.md)、
作った手順は[実装計画](../docs/superpowers/plans/2026-10-19-hull-web-app.md)にあります。

## 組み立てと検査

リポジトリのルートで実行します。

```bash
make hull-book hull-report   # 中身（Book と補足教材）を先に作る
make hull-web                # johnhull/web/dist/ を組み立てる
make hull-web-check          # 組み立てたあと、単体テストとブラウザの検査を行う
```

- git worktree の中では uv を使わないので、`HULL_WEB_PY=/home/kazumasa/projects/.venv/bin/python` を付けます。
- Git の外のデータ（取得した Pyodide、Playwright の出力、スクリーンショット）は `HULL_WEB_DATA`
  （既定は `/home/kazumasa/projects/_data/johnhull/hull-web`）に置きます。
- ブラウザの検査には、Book の検査と同じ Playwright 1.56.0 と ms-playwright の Chromium 1208（`CHROMIUM_BIN`）を使います。
- Python の検査（パッケージの一致・期待値の鮮度・サイトの組み立て）は `make test` に入っています。

## サイトの中身

| サイトのパス | 元 |
|---|---|
| `/` | `index.html`（入口） |
| `/book/_build/html/` | `make hull-book` の出力（`_sources/` と `.buildinfo` を除く） |
| `/report/site/` | `make hull-report` の出力 |
| `/docs/validation/reading-guide/` | ガイドの数値表（ガイドを統合したあと） |
| `/calc/binomial/` | 二項木の計算機（`calc/binomial/index.html` と `src/calc/`） |
| `/pyodide/` | Pyodide 本体、numpy と scipy、ブラウザ用 hullkit（`hullkit_browser.zip`） |
| `/sw.js`・`/manifest.webmanifest`・`/_headers`・`/robots.txt`・`/404.html` | Service Worker、PWA の定義、ヘッダ、クローラの拒否、404 |

checkout と同じ相対配置なので、ガイドから補足教材へのリンクは書き換えずに動きます。PDF は載せません。

## 計算機

- 計算の入口は `py/hull_web_calc/binomial.py` の `run()` です。JSON の文字列を受け取り、JSON の文字列を返します。
  ブラウザ（Pyodide、Web Worker の中）とネイティブの検査は、同じ関数を呼びます。
- ブラウザ用 hullkit には `trees.py` と `bsm.py` を repo とバイト単位で同じまま入れ、`__init__.py` だけを生成します
  （`py/hull_web_build/package.py`）。hullkit 本体は変えません。
- 例題ボタンの期待値と許容差は、hullkit の固定テストに書かれた数字だけです（`py/hull_web_build/examples.py`。
  `py/tests/test_examples.py` が、どの数字も固定テストの関数の中にあることを確かめます）。
- `tests/golden.json`（ネイティブの応答）と `src/calc/examples.json` は生成物です。`py/` を変えたら
  `python -m hull_web_build golden` で作り直します。古いままだと `make test` が落ちます。
- ブラウザとネイティブの差の許容値（`tests/tolerance.json`）は W0 の実測値です（[W0 の報告](../docs/validation/hull-web/W0_REPORT.md)）。

## オフライン（Service Worker）

- Service Worker は、入口か計算機を初めて開いたときに入ります（Book と補足教材のページは登録しません）。
  そのときにアプリの枠（入口・計算機・アイコン）を保存します。それ以降は、Pyodide と numpy を計算機を開いたときに
  （計算機は開くと §13.10 の例を計算します）、Book と補足教材のページを開いたときに保存します。
  scipy は BSM との比較を開いたときに読み込みます。読むだけなら Pyodide を取りに行きません。
- HTML はネットワーク優先、静的ファイルはキャッシュ優先です。保存するのは同じオリジンの 200 応答だけで、
  転送（Access のログインへの転送を含む）は保存しません。
- 再配信のあとも、前に開いたページはオフラインで開けます。静的ファイルは、配信が変わったあと最初に使うときに
  一度だけ取り直します。
- 保存したページは自動では消えません。容量を空けたいときは、ブラウザでこのサイトのデータを消します。
- 補足教材のうち 33 ページ（2026-10-19 時点）は、数式の表示に MathJax を cdn.jsdelivr.net から読みます
  （補足教材の作り方による）。オフラインでは、これらのページの数式は TeX のまま表示されます。

## 配信

配信は毎回、本人の承認を得てから行います。トークンは本人のシェルの環境変数にだけ置き、ファイル・ログ・メモリーに残しません。

```bash
read -rs CLOUDFLARE_API_TOKEN && export CLOUDFLARE_API_TOKEN   # 画面にも履歴にも残らない
HULL_WEB_DEPLOY_APPROVED=yes make hull-web-deploy HULL_WEB_HOST=<pages.dev のホスト名>
```

`make hull-web-deploy` は、配信の前と後に、ログインせずに取ると Cloudflare Access への転送が返ることを確かめます
（`python -m hull_web_build access-check --host <ホスト名>`）。一つでも中身が返ったら止まります。

## 落とし穴

- `404.html` がないと、Pages は存在しないパスに入口ページを 200 で返します。
- Book の「ソースをダウンロード」のリンク（2026-10-19 の main で 31 件）は `_sources/` を指しますが、
  `_sources/` は配信しません（設計 §3.2）。リンク検査はこれを「設計どおり除いたもの」として数えます。
- DevTools の CPU 低速化は Web Worker に効きません。遅い端末での時間は、W0 のページ（`/w0/?main`）で
  Pyodide を主スレッドに載せて測りました。
- `wrangler pages dev` を動かすと `johnhull/web/.wrangler/` ができます（Git の対象外）。
````

- [ ] **Step 4: Run the regression checks (spec §5 回帰)**

```bash
$PY -m ruff check .                                   # = make lint
$PY -m ruff format --check johnhull/web/py
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 $PY -m pytest -q -p no:cacheprovider > $HULL_WEB_DATA/w1-pytest.log 2>&1; tail -3 $HULL_WEB_DATA/w1-pytest.log
PYTHONPATH=johnhull/report:johnhull/hullkit/src $PY johnhull/scripts/verify_release.py   # = make hull-release-check
git diff --stat main...HEAD -- johnhull/hullkit johnhull/book johnhull/report johnhull/docs/section_ledger.json \
  johnhull/docs/SECTION_LEDGER.md johnhull/docs/validation/shared-runtime.json
git diff --name-only main...HEAD | grep -v -E '^(johnhull/web/|johnhull/docs/validation/hull-web/|johnhull/ROADMAP.md$|pyproject.toml$|Makefile$)'
```

Expected: `All checks passed!`; `23 files already formatted`; the full pytest run ends with `passed` and no `failed` (it is the `make test` suite, minus `sde-check`, which needs that book's own npm install; johnhull/web adds 179 tests); `[PASS] johnhull A5--A8 release contract`; both `git diff` commands print nothing (hullkit, the Book, the report, the ledger and the shared runtime are unchanged, and nothing outside the listed paths changed).

If the full run fails outside `johnhull/web`, run the same test on main's checkout; a failure that main has too is pre-existing: name it in the report and do not fix it here.

- [ ] **Step 5: Record the end of W1 in the ROADMAP**

Set the status (Task 1, Step 10) to

```text
2026-10-18 設計、ユーザー承認。2026-10-19 実装計画。W0 完了（DATE0、[W0 報告](docs/validation/hull-web/W0_REPORT.md)）。W1 完了（DATE、[W1 記録](docs/validation/hull-web/w1.json)）。W2 の配信の道具を作成中、branch `codex/hull-web`
```

(DATE0 is the W0 date already there), and in the 「完了までの計画」 line add `、完了 DATE` after the W1 start date, so it reads `（タスク6〜11、着手 <Task 6 date>、完了 DATE）`.

- [ ] **Step 6: Commit**

```bash
git add johnhull/web/README.md johnhull/docs/validation/hull-web/w1.json johnhull/ROADMAP.md
git commit -m "Record W1 checks and document building, checking and deploying the web app"
```

---

### Task 12: W2 tooling — the Access probe and the guarded deploy target (then stop)

**Files:**
- Create: `johnhull/web/py/hull_web_build/access_check.py`
- Modify: `johnhull/web/py/hull_web_build/cli.py` (add `access-check`), root `Makefile`, `johnhull/ROADMAP.md`
- Test: `johnhull/web/py/tests/test_access_check.py`, `johnhull/web/py/tests/test_cli.py` (one more test)

**Interfaces:**
- Produces: `access_check.ACCESS_SUFFIX = ".cloudflareaccess.com"`, `PROBE_PATHS`, `Probe(url, status, location_host)` with `.protected` (a 301/302/303/307/308 to a host ending in `.cloudflareaccess.com`), `urls_for(host) -> list[str]` (production paths plus `https://access-probe.<host>/` under the preview wildcard), `probe(url) -> Probe` (no cookies, no redirect following), `check(urls) -> list[Probe]`.
- Produces: `python -m hull_web_build access-check --host <host>` (exit 1 and 「do not deploy」 if any URL is not protected); `make hull-web-deploy`.

- [ ] **Step 1: Write the failing tests**

`johnhull/web/py/tests/test_access_check.py` (a local HTTP server stands in for Pages and Access):

```python
import http.server
import threading

import pytest
from hull_web_build import access_check


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/protected":
            self.send_response(302)
            self.send_header("Location", "https://team.cloudflareaccess.com/cdn-cgi/access/login/x")
        elif self.path == "/elsewhere":
            self.send_response(302)
            self.send_header("Location", "https://example.com/login")
        elif self.path == "/missing":
            self.send_response(404)
        else:
            self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def server():
    httpd = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


@pytest.mark.parametrize(
    ("path", "protected"),
    [("/protected", True), ("/elsewhere", False), ("/open", False), ("/missing", False)],
)
def test_only_a_redirect_to_access_counts_as_protected(server, path, protected):
    result = access_check.probe(server + path)
    assert result.protected is protected


def test_redirect_is_not_followed(server):
    result = access_check.probe(server + "/protected")
    assert (result.status, result.location_host) == (302, "team.cloudflareaccess.com")


def test_urls_cover_production_paths_and_the_preview_wildcard():
    urls = access_check.urls_for("hull-notes.pages.dev")
    assert "https://hull-notes.pages.dev/" in urls
    assert "https://hull-notes.pages.dev/pyodide/pyodide-lock.json" in urls
    assert urls[-1] == "https://access-probe.hull-notes.pages.dev/"
```

Append to `johnhull/web/py/tests/test_cli.py`:

```python
def test_access_check_fails_when_a_url_is_open(monkeypatch, capsys):
    from hull_web_build import access_check

    monkeypatch.setattr(access_check, "probe", lambda url: access_check.Probe(url, 200, ""))
    assert cli.main(["access-check", "--host", "hull-notes.pages.dev"]) == 1
    assert "do not deploy" in capsys.readouterr().err
```

Run: `$PYT -m pytest johnhull/web/py/tests/test_access_check.py johnhull/web/py/tests/test_cli.py -q`
Expected: collection error, `ImportError: cannot import name 'access_check' from 'hull_web_build'`.

- [ ] **Step 2: Implement the probe and the command**

`johnhull/web/py/hull_web_build/access_check.py`:

```python
"""Check that requests without a login get Cloudflare Access, not site content (spec §3.7)."""

from __future__ import annotations

import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlsplit

ACCESS_SUFFIX = ".cloudflareaccess.com"
REDIRECTS = (301, 302, 303, 307, 308)
PROBE_PATHS = (
    "/",
    "/book/_build/html/",
    "/calc/binomial/",
    "/pyodide/pyodide-lock.json",
    "/robots.txt",
)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass(frozen=True)
class Probe:
    """What one unauthenticated GET returned."""

    url: str
    status: int
    location_host: str

    @property
    def protected(self) -> bool:
        return self.status in REDIRECTS and self.location_host.endswith(ACCESS_SUFFIX)


def urls_for(host: str) -> list[str]:
    """Production paths on `host` (e.g. hull-notes.pages.dev) plus one name under *.<host>."""
    base = f"https://{host}"
    return [base + path for path in PROBE_PATHS] + [f"https://access-probe.{host}/"]


def probe(url: str) -> Probe:
    """GET `url` without cookies and without following redirects."""
    opener = urllib.request.build_opener(_NoRedirect())
    request = urllib.request.Request(url, headers={"User-Agent": "hull-web-access-check"})
    try:
        with opener.open(request, timeout=30) as response:
            status, location = response.status, response.headers.get("Location", "")
    except urllib.error.HTTPError as exc:
        status, location = exc.code, exc.headers.get("Location", "")
    return Probe(url, status, urlsplit(location).hostname or "")


def check(urls: list[str]) -> list[Probe]:
    """Probe every URL; callers fail when any probe is not protected."""
    return [probe(url) for url in urls]
```

Replace `johnhull/web/py/hull_web_build/cli.py` with:

```python
"""Command line: python -m hull_web_build <command> (run from the repository root)."""

from __future__ import annotations

import argparse
import json
import sys

from . import access_check, golden, package, pyodide_fetch, site


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m hull_web_build")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("fetch-pyodide", help="download and verify the pinned Pyodide files")
    commands.add_parser("package", help="build build/hullkit_browser.zip")
    golden_parser = commands.add_parser(
        "golden", help="write tests/golden.json and src/calc/examples.json"
    )
    golden_parser.add_argument("--check", action="store_true", help="fail instead of writing")
    commands.add_parser("sweep", help="write build/w0-sweep.json (W0 only)")
    commands.add_parser("w0-site", help="assemble the W0 spike site in build/w0-site")
    commands.add_parser("site", help="assemble dist/")
    access_parser = commands.add_parser("access-check", help="verify Cloudflare Access is in front")
    access_parser.add_argument("--host", required=True, help="production host, e.g. x.pages.dev")
    args = parser.parse_args(argv)

    if args.command == "fetch-pyodide":
        pins = pyodide_fetch.load_pins()
        print(pyodide_fetch.fetch(pins, pyodide_fetch.load_lock(pins)))
    elif args.command == "package":
        print(json.dumps(package.build(), indent=2))
    elif args.command == "golden":
        if args.check:
            stale = golden.stale()
            if stale:
                print(
                    "stale (run python -m hull_web_build golden):",
                    *stale,
                    sep="\n  ",
                    file=sys.stderr,
                )
                return 1
        else:
            for path in golden.write():
                print("wrote", path)
    elif args.command == "sweep":
        print("wrote", golden.write_sweep())
    elif args.command == "w0-site":
        print(json.dumps(site.assemble_w0(), indent=2))
    elif args.command == "site":
        print(json.dumps(site.assemble(), indent=2))
    elif args.command == "access-check":
        probes = access_check.check(access_check.urls_for(args.host))
        for result in probes:
            mark = "ok " if result.protected else "BAD"
            print(f"{mark} {result.status} {result.url} -> {result.location_host or '-'}")
        if not all(result.protected for result in probes):
            print("Some URLs are not behind Cloudflare Access; do not deploy.", file=sys.stderr)
            return 1
    return 0
```

Run: `$PYT -m pytest johnhull/web/py/tests -q`
Expected: `186 passed`.

- [ ] **Step 3: Add the guarded deploy target**

In the root `Makefile`:

1. In the `.PHONY` line, replace `hull-web hull-web-check rough-vol` with `hull-web hull-web-check hull-web-deploy rough-vol`.
2. In `help`, after the `make hull-web-check` line, add:

```makefile
	@echo "  make hull-web-deploy - publish johnhull/web/dist (owner approval every time)"
```

3. Directly above the `rough-vol:` target (below `hull-web-check`), add:

```makefile
HULL_WEB_PROJECT ?= hull-notes
HULL_WEB_HOST ?= $(HULL_WEB_PROJECT).pages.dev

# Publishes johnhull/web/dist; build and check it with hull-web-check first. Every run
# needs the owner's approval (spec §3.7) and a token in the shell, never in a file.
hull-web-deploy:
	@test "$(HULL_WEB_DEPLOY_APPROVED)" = yes || { echo "Set HULL_WEB_DEPLOY_APPROVED=yes once the owner has approved this deploy." >&2; exit 1; }
	@test -n "$$CLOUDFLARE_API_TOKEN" || { echo "CLOUDFLARE_API_TOKEN is not set in this shell." >&2; exit 1; }
	@test -f johnhull/web/dist/sw.js || { echo "johnhull/web/dist is missing; run make hull-web-check first." >&2; exit 1; }
	$(HULL_WEB_RUN) access-check --host $(HULL_WEB_HOST)
	WRANGLER_SEND_METRICS=false npx --yes wrangler@4.147.0 pages deploy johnhull/web/dist --project-name $(HULL_WEB_PROJECT) --branch main
	$(HULL_WEB_RUN) access-check --host $(HULL_WEB_HOST)
```

Run: `make hull-web-deploy; echo "exit $?"`
Expected: `Set HULL_WEB_DEPLOY_APPROVED=yes once the owner has approved this deploy.` and a non-zero exit; nothing is sent anywhere.

Run: `env -u CLOUDFLARE_API_TOKEN make hull-web-deploy HULL_WEB_DEPLOY_APPROVED=yes; echo "exit $?"`
Expected: `CLOUDFLARE_API_TOKEN is not set in this shell.` and a non-zero exit.

- [ ] **Step 4: Record the state in the ROADMAP**

Set the status (Task 1, Step 10) to

```text
2026-10-18 設計、ユーザー承認。2026-10-19 実装計画。W0 完了（DATE0、[W0 報告](docs/validation/hull-web/W0_REPORT.md)）。W1 完了（DATE1、[W1 記録](docs/validation/hull-web/w1.json)）。W2 の配信の道具も完了（DATE）、未統合、branch `codex/hull-web`。merge 前に Claude が検証する
```

(DATE0 and DATE1 are the dates already there), and in the 「完了までの計画」 line replace `W2 非公開の配信（タスク12〜13。` with `W2 非公開の配信（タスク12〜13、道具は DATE に完了。`.

- [ ] **Step 5: Lint and commit**

Run: `$PY -m ruff check johnhull/web/py && $PY -m ruff format --check johnhull/web/py`
Expected: `All checks passed!` and `25 files already formatted`.

```bash
git add johnhull/web/py/hull_web_build/access_check.py johnhull/web/py/hull_web_build/cli.py \
  johnhull/web/py/tests/test_access_check.py johnhull/web/py/tests/test_cli.py Makefile johnhull/ROADMAP.md
git commit -m "Probe that Cloudflare Access answers first; guard make hull-web-deploy"
```

- [ ] **Step 6: STOP for verification and merge**

Tell the owner and Claude that the branch is complete: commits since main, the test counts (Python, unit, browser), the W0 and W1 records, and every ruling you made. Claude verifies the branch independently; the owner decides the merge (spec §8). Do not merge, push or deploy.

---

### Task 13: W2 — private deploy with the owner (from the main checkout)

Run this task from `/home/kazumasa/projects` after the merge, together with the owner. Here `make` may use uv (this is the main checkout). The owner prepares Cloudflare; whoever runs the commands keeps the token in their own shell only.

**Files:**
- Create: `johnhull/docs/validation/hull-web/w2.json`
- Modify: `johnhull/ROADMAP.md`

- [ ] **Step 1: The owner prepares the account and the token**

The owner creates (or uses) a Cloudflare account and an API token that can edit Cloudflare Pages, then in the shell that will run the commands:

```bash
read -rs CLOUDFLARE_API_TOKEN && export CLOUDFLARE_API_TOKEN   # not echoed, not in the history
read -r CLOUDFLARE_ACCOUNT_ID && export CLOUDFLARE_ACCOUNT_ID   # needed when the token sees several accounts
```

- [ ] **Step 2: Create the empty Pages project (spec §3.7 step 2)**

```bash
WRANGLER_SEND_METRICS=false npx --yes wrangler@4.147.0 pages project create hull-notes --production-branch main
```

Expected: the project is created with no deployment. Note the `*.pages.dev` host it reports; if `hull-notes.pages.dev` was taken, the host has a suffix. Below, `HOST` is that host (for example `hull-notes.pages.dev`).

- [ ] **Step 3: The owner puts Access in front (spec §3.7 step 3)**

In Cloudflare Zero Trust, the owner creates one self-hosted Access application whose domains are `HOST` and `*.HOST` (the Pages "Known issues" page describes protecting both the production name and the previews), with one Allow policy that includes only the owner's email address, and with the one-time PIN as the login method. Nothing from this step is written to the repo.

- [ ] **Step 4: Check that nothing is served without login, before any content (spec §3.7 step 4)**

Run: `PYTHONPATH=johnhull/web/py uv run --no-sync python -m hull_web_build access-check --host HOST`
Expected: six lines starting with `ok 302` (or another redirect status), each ending in `-> <team>.cloudflareaccess.com`, and exit 0. If any line starts with `BAD`, stop: fix Access first.

- [ ] **Step 5: Build, check and deploy (spec §3.7 step 5)**

```bash
make hull-book hull-report
make hull-web-check
```

Expected: as in Task 10, Step 6. Then, with the owner's approval for this deploy:

```bash
HULL_WEB_DEPLOY_APPROVED=yes make hull-web-deploy HULL_WEB_HOST=HOST
```

Expected: the access check passes, `wrangler pages deploy` uploads `johnhull/web/dist` and prints the deployment URL (under `*.HOST`), and the access check passes again. If the second check fails, tell the owner at once: the content may be reachable without login.

- [ ] **Step 6: The owner checks on the phone (spec §6 W2)**

Task 10 already opened every page of the same `dist/` locally. On the phone, the owner opens `https://HOST/`, logs in with the emailed code, and checks: the entry page; one Book chapter; the report index; the calculator with the 「§13.10 DerivaGem 5段」 example, all rows 「一致」; then, with the phone offline, the same Book chapter and the calculator again. Add the site to the home screen if wanted.

- [ ] **Step 7: Record W2 and update the ROADMAP**

`johnhull/docs/validation/hull-web/w2.json` (no token, account ID or email address):

```json
{
  "deployed_at": "<ISO time>",
  "commit": "<git rev-parse HEAD on main>",
  "host": "HOST",
  "deployment_url": "<printed by wrangler>",
  "site_version": "<the VERSION in johnhull/web/dist/sw.js>",
  "access_before_content": ["<each line of Step 4>"],
  "access_after_deploy": ["<each line of the second check in Step 5>"],
  "phone": {"device": "", "os": "", "browser": "", "login": "", "entry": "", "book_chapter": "", "report": "", "calculator_s13_10_5": "", "offline_book_chapter": "", "offline_calculator": ""}
}
```

Set the status (Task 1, Step 10) to `2026-10-18 設計、ユーザー承認。W0〜W2 完了（DATE）。Access の後ろに配信済み（[W2 記録](docs/validation/hull-web/w2.json)）`, and in the 「完了までの計画」 line add `配信は DATE。` after `道具は <Task 12 date> に完了。`. Commit on main with the owner's approval:

```bash
git add johnhull/docs/validation/hull-web/w2.json johnhull/ROADMAP.md
git commit -m "Record the first private deploy of the johnhull web app (W2)"
```
