# akinator — Claude Code Guide

Local Akinator-style guesser. Entities are sourced from **Wikidata** (no
hand-built dataset). The engine is a **probabilistic candidate updater**, not a
fixed decision tree.

## Layers (kept separate)

- `app/normalize.py` — raw Wikidata binding → `Entity` (feature dict). Pure.
- `app/question_gen.py` — entities → questions, auto from attribute values. Pure.
- `app/inference/scoring.py` — log-score Bayesian update; **missing attribute =
  neutral + soft penalty** (entities are never eliminated for missing data).
- `app/inference/question_selection.py` — pick the unasked question that splits
  candidates most evenly (`split_score`). Swap-in point for entropy/IG later.
- `app/services/{entity,game}_service.py` — load data; run a session.
- `app/main.py` — FastAPI glue + Jinja2 screens + `/debug/{gid}`.

The inference layer imports neither FastAPI nor SQLite — unit-test it directly.

## Run / test

```bash
cd ~/projects && make install
uv run --no-sync pytest akinator/tests -v
uv run --no-sync uvicorn app.main:app --app-dir akinator --reload --port 8100
```

## Data (processed/ is committed; raw/ is gitignored)

The committed `data/processed/` is currently an **offline seed** (35 curated
entities via `scripts/seed_data.py`), generated because WDQS was in an active
outage at build time. It runs through the same normalize + question-generation
pipeline as the live fetch. Replace it with the real ~400-entity Wikidata set
once WDQS is healthy:

```bash
uv run --no-sync python akinator/scripts/fetch_wikidata_entities.py --refresh
uv run --no-sync python akinator/scripts/build_questions.py
# fallback if WDQS is unavailable:
uv run --no-sync python akinator/scripts/seed_data.py
```

The fetch hits the public WDQS SPARQL endpoint. The real-people query is bounded
to humans holding one of the mapped occupations (P106) and ordered by sitelinks;
the fictional query is bounded by `instance of` ∈ {fictional human, fictional
character}. Both retry with backoff and respect WDQS rate-limiting. If WDQS is
down/overloaded the script leaves any existing cache untouched.

## Conventions

- New feature key → add to `normalize.py` (QID map), `question_gen.py`
  (`_*_FEATURES` set + label/template), done. Don't hand-write questions.
- Scoring constants live only in `scoring.py` (`STRONG`, `WEAK_MISSING`).
- Game history + wrong-answer corrections persist to SQLite
  (`corrections` table = future learning data; not yet consumed).
- `EntityService.from_disk` tolerates missing processed data (empty pool) so the
  app imports before the first build.
