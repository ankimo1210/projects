# Akinator MVP — Design

**Date:** 2026-06-01
**Status:** Approved, ready for implementation plan
**Project:** `akinator/` (new workspace member)

## Goal

A local web app that guesses a person/character the user is thinking of, by
asking attribute-based questions. No hand-built dataset: initial entities are
fetched automatically from **Wikidata**. The engine is a **candidate
probability updater**, not a fixed decision tree.

## Scope (MVP)

- Domain: **real notable people (~200) + fictional/anime-manga characters (~200)**,
  ~400 entities total. The "is this person real / fictional / appears in anime"
  axis splits candidates well and feels Akinator-like.
- Local FastAPI + SQLite + Jinja2. No React.
- 5 screens + a debug screen.

## Architecture — 4 separated layers

```
Data fetch     scripts/fetch_wikidata_entities.py  -> data/raw/*.json          (gitignored)
Normalize+Qgen scripts/build_questions.py          -> data/processed/*.json    (committed)
Inference      app/inference/{scoring,question_selection}.py  (pure functions, UI-independent)
Web/API        app/main.py (FastAPI) + Jinja2 templates + SQLite (game history)
```

Data取得・正規化・推論・UI は互いに独立。推論層は JSON とユーザー回答だけに
依存し、FastAPI/SQLite を import しない（テスト容易性）。

## Data model

### Entity (`data/processed/entities.json`)

```json
{
  "id": "Q937",
  "name": "アルベルト・アインシュタイン",
  "aliases": ["Albert Einstein"],
  "description": "理論物理学者",
  "image_url": "https://...",
  "features": {
    "is_fictional": false,
    "gender": "male",
    "occupation": ["physicist"],
    "country": ["Germany", "United States"],
    "birth_century": 19,
    "is_dead": true,
    "in_anime": false
  }
}
```

`features` is the **normalized** attribute dict used by inference — not raw
Wikidata QIDs. The fetch step maps QIDs/dates to question-ready values
(e.g. P21→gender male/female, birth date→birth_century, P31 fictional-ness→
is_fictional boolean).

Target feature keys (from the requested attribute list, normalized):
`is_fictional, gender, occupation[], country[], birth_century, is_dead,
in_anime, species, creator, notable_work[], fictional_universe`.

### Question (`data/processed/questions.json`)

```json
{
  "id": "q_occupation_physicist",
  "text": "その人は物理学者ですか？",
  "feature_key": "occupation",
  "expected_value": "physicist",
  "match_type": "list_contains"
}
```

`match_type ∈ {equals, list_contains, numeric}`. Question text is composed from
templates: `feature_key` → Japanese label + `expected_value` → Japanese label.
NOT a fully hand-written question list. `build_questions.py` enumerates the
distinct attribute values present across entities and emits one question per
(feature_key, value) that is discriminative enough (appears in a useful
fraction of entities — neither ~all nor ~none).

## Inference — Bayesian-style score update

Each entity holds a `log_score` (start 0 = equal prior). For each asked
question, derive the entity's *expected answer* from its features, then update
against the user's answer:

| user answer \ entity-expected | match | mismatch | feature missing |
|---|---|---|---|
| yes              | +ln(0.9/0.1) | −strong | **−weak (near-neutral)** |
| no               | −strong | +ln(0.9/0.1) | **−weak** |
| probably_yes/no  | half weight | half | −tiny |
| unknown          | 0 (skip) | 0 | 0 |

**Missing-attribute policy (decided): neutral + soft penalty.** If an entity
lacks the feature a question asks about, it is NOT eliminated — it just gets a
small penalty and no positive evidence. This keeps sparse Wikidata entities
(e.g. historical figures missing birth_date) alive in the candidate pool.

Concrete constants live in `scoring.py` (e.g. `STRONG = ln(0.9/0.1)`,
`WEAK_MISSING = ln(0.6/0.4)`), tunable in one place.

Posterior = softmax over `log_score`. Guess when top candidate's posterior
exceeds a threshold (e.g. 0.85) or after a max question count.

## Question selection — split score

From unasked questions, pick the one that best splits the current top-candidate
set into yes/no halves. MVP metric: minimize `|count_yes − count_no|` over
weighted candidates (an information-gain approximation). Isolated in
`question_selection.py` with a clear interface so it can later be swapped for
entropy / information gain. Already-asked questions are excluded.

## Screens (5 + debug, Jinja2)

1. **Start** — begin a game.
2. **Question** — show current question + buttons: yes / no / probably_yes /
   probably_no / unknown.
3. **Guess** — top candidate (name, image, description).
4. **Wrong → correct entry** — user types the right answer; saved to
   `corrections` as future training data.
5. **Debug** — top candidates + scores, Q&A history, next-question candidates,
   *why* that question was chosen (split counts), entity raw data.

## Persistence (SQLite)

- `games` (session: id, created_at, status, guessed_entity_id, was_correct)
- `game_answers` (game_id, question_id, answer, asked_order)
- `corrections` (game_id, correct_entity_id_or_name, created_at)

Entities/questions are loaded from JSON, NOT stored in DB — keeps regeneration
cheap. Only game history/corrections are persisted.

## Wikidata fetch policy

- SPARQL via WDQS (`query.wikidata.org/sparql`), `LIMIT` ~200 real + ~200
  fictional, with `time.sleep` between requests and an explicit descriptive
  User-Agent.
- `--refresh` flag re-fetches; otherwise use `data/raw/` cache.
- On fetch failure, fall back to cached raw.
- `data/raw/` gitignored; `data/processed/{entities,questions}.json` committed
  so the app is playable right after clone (no fetch required). A make/CLI
  target re-fetches on demand.

## Layout

```
akinator/
  app/
    main.py
    models.py
    services/
      game_service.py
      entity_service.py
    inference/
      scoring.py
      question_selection.py
    templates/
  scripts/
    fetch_wikidata_entities.py
    build_questions.py
  data/
    raw/         (gitignored)
    processed/   (committed: entities.json, questions.json)
  tests/
  README.md
  pyproject.toml
```

Added as a uv workspace member in the root `pyproject.toml`.

## Tests (pytest, ≥7 required behaviors)

1. Wikidata fetch result normalizes correctly (raw QID → feature dict).
2. `entities.json` can be generated.
3. `questions.json` is auto-generated from attribute values.
4. Score changes in response to answers (yes raises matching candidate).
5. Already-asked questions are not reused.
6. A question that splits candidates is preferred by selection.
7. `unknown` answers don't break the engine (no NaN/elimination).

## Out of scope (YAGNI for MVP)

- entropy/information-gain selection (interface ready, not implemented)
- learning from corrections (stored, not yet consumed)
- multi-language UI, accounts, deployment
