# Akinator MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A local web app that guesses a person/character the user is thinking of by asking attribute-based questions, with entities auto-sourced from Wikidata and a probabilistic candidate-updating engine (not a fixed decision tree).

**Architecture:** Four separated layers — (1) Wikidata fetch script → `data/raw/`, (2) normalize + auto-generate questions → `data/processed/`, (3) pure-function inference engine (scoring + question selection), (4) FastAPI + Jinja2 + SQLite web/API. The inference layer imports neither FastAPI nor SQLite, so it is unit-testable in isolation.

**Tech Stack:** Python 3.12, FastAPI, uvicorn, Jinja2, httpx (Wikidata SPARQL), SQLite (stdlib `sqlite3`), pytest. All deps already present in the workspace `.venv`. New uv workspace member `akinator/` (src-less flat `app/` package, matching the spec layout).

---

## File Structure

```
akinator/
  pyproject.toml                     # workspace member, deps, package config
  README.md
  app/
    __init__.py
    config.py                        # paths: DATA_DIR, processed/raw, DB_PATH
    models.py                        # dataclasses: Entity, Question, Answer enum
    data_loader.py                   # load entities.json / questions.json -> objects
    normalize.py                     # raw Wikidata binding -> Entity (feature dict)
    question_gen.py                  # entities -> list[Question] (auto from attrs)
    inference/
      __init__.py
      scoring.py                     # log-score update; missing=neutral+soft penalty
      question_selection.py          # pick best-splitting unasked question
    services/
      __init__.py
      entity_service.py              # load + cache entities/questions singletons
      game_service.py                # game state machine over a session
    db.py                            # sqlite schema + connection helper
    templates/
      base.html  start.html  question.html  guess.html  wrong.html  debug.html
    main.py                          # FastAPI routes + session wiring
  scripts/
    __init__.py
    fetch_wikidata_entities.py       # SPARQL fetch -> data/raw/*.json
    build_questions.py               # raw -> processed/{entities,questions}.json
  data/
    raw/.gitkeep                     # gitignored contents
    processed/.gitkeep               # entities.json / questions.json committed
  tests/
    __init__.py
    conftest.py                      # tiny fixture entities/questions
    test_normalize.py
    test_question_gen.py
    test_scoring.py
    test_question_selection.py
    test_game_service.py
    test_data_loader.py
    test_build_pipeline.py
    test_db.py
    test_api.py
```

Module responsibilities are single-purpose: `normalize.py` only maps raw→Entity; `scoring.py` only updates scores; `question_selection.py` only ranks questions; `game_service.py` orchestrates a session using the two pure modules; `main.py` is thin HTTP glue.

---

## Task 1: Scaffold the akinator workspace member

**Files:**
- Create: `akinator/pyproject.toml`
- Create: `akinator/app/__init__.py` (empty)
- Create: `akinator/app/config.py`
- Create: `akinator/tests/__init__.py` (empty)
- Create: `akinator/data/raw/.gitkeep` (empty)
- Create: `akinator/data/processed/.gitkeep` (empty)
- Create: `akinator/.gitignore`
- Modify: `pyproject.toml` (root) — add member + testpath
- Create: `akinator/README.md`

- [ ] **Step 1: Create `akinator/pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "akinator"
version = "0.1.0"
description = "Local Akinator-style guesser sourced from Wikidata"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.110",
    "uvicorn>=0.27",
    "jinja2>=3.1",
    "httpx>=0.27",
    "python-multipart>=0.0.9",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[tool.setuptools.packages.find]
where = ["."]
include = ["app*"]
```

- [ ] **Step 2: Create `akinator/app/config.py`**

```python
"""Filesystem paths for akinator data and DB. Single source of truth."""
from __future__ import annotations

from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
ENTITIES_PATH = PROCESSED_DIR / "entities.json"
QUESTIONS_PATH = PROCESSED_DIR / "questions.json"
DB_PATH = PROJECT_DIR / "akinator.db"
```

- [ ] **Step 3: Create empty `akinator/app/__init__.py`, `akinator/tests/__init__.py`, `akinator/data/raw/.gitkeep`, `akinator/data/processed/.gitkeep`**

All four are empty files.

- [ ] **Step 4: Create `akinator/.gitignore`**

```gitignore
# raw Wikidata responses are regenerable; processed/ is committed
data/raw/*
!data/raw/.gitkeep
# sqlite runtime
akinator.db
akinator.db-*
__pycache__/
```

- [ ] **Step 5: Create `akinator/README.md`**

```markdown
# akinator

Local Akinator-style guesser. Entities are sourced from Wikidata (no hand-built
dataset); the engine is a probabilistic candidate updater, not a fixed tree.

## Run

```bash
cd ~/projects && make install            # once, installs workspace .venv
# (re)build data from Wikidata — optional, processed/ is committed:
uv run --no-sync python akinator/scripts/fetch_wikidata_entities.py
uv run --no-sync python akinator/scripts/build_questions.py
# serve
uv run --no-sync uvicorn app.main:app --app-dir akinator --reload --port 8100
# tests
uv run --no-sync pytest akinator/tests -v
```

Open http://localhost:8100/ to play. `/debug/{game_id}` shows engine internals.
```

- [ ] **Step 6: Register member in root `pyproject.toml`**

In `[tool.uv.workspace] members`, add `"akinator",` after `"land_price_api_app",`:

```toml
members = [
    "gto",
    "market-viz",
    "stock",
    "nbody-gpu",
    "line_backup",
    "land_price_api_app",
    "akinator",
]
```

In `[tool.pytest.ini_options] testpaths`, add `"akinator/tests",` after `"line_backup/tests",`:

```toml
testpaths = [
    "gto/tests",
    "market-viz/tests",
    "stock/tests",
    "nbody-gpu/tests",
    "line_backup/tests",
    "akinator/tests",
]
```

- [ ] **Step 7: Sync and verify the member resolves**

Run: `cd ~/projects && uv sync --all-packages 2>&1 | tail -3`
Expected: completes without error; `akinator` is built/installed editable.

Run: `uv lock --check`
Expected: exit 0.

- [ ] **Step 8: Commit**

```bash
git add akinator/pyproject.toml akinator/app akinator/tests akinator/data akinator/.gitignore akinator/README.md pyproject.toml uv.lock
git commit -m "feat(akinator): scaffold workspace member"
```

---

## Task 2: Data models

**Files:**
- Create: `akinator/app/models.py`
- Test: `akinator/tests/test_data_loader.py` (model construction part)

- [ ] **Step 1: Write the failing test** (create `akinator/tests/test_data_loader.py`)

```python
from app.models import Answer, Entity, Question


def test_entity_feature_access():
    e = Entity(
        id="Q1",
        name="Test",
        aliases=["T"],
        description="d",
        image_url=None,
        features={"gender": "male", "occupation": ["actor"], "birth_century": 20},
    )
    assert e.feature("gender") == "male"
    assert e.feature("missing") is None
    assert e.has_feature("gender") is True
    assert e.has_feature("missing") is False


def test_question_fields():
    q = Question(
        id="q_gender_male",
        text="男性ですか？",
        feature_key="gender",
        expected_value="male",
        match_type="equals",
    )
    assert q.feature_key == "gender"
    assert q.match_type == "equals"


def test_answer_enum_values():
    assert Answer.YES.value == "yes"
    assert {a.value for a in Answer} == {
        "yes", "no", "probably_yes", "probably_no", "unknown",
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --no-sync pytest akinator/tests/test_data_loader.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.models'`.

- [ ] **Step 3: Write `akinator/app/models.py`**

```python
"""Core data shapes for akinator. Dataclasses + enum only — no logic beyond
trivial feature access."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Answer(str, Enum):
    YES = "yes"
    NO = "no"
    PROBABLY_YES = "probably_yes"
    PROBABLY_NO = "probably_no"
    UNKNOWN = "unknown"


@dataclass
class Entity:
    id: str
    name: str
    aliases: list[str]
    description: str
    image_url: str | None
    features: dict[str, Any] = field(default_factory=dict)

    def feature(self, key: str) -> Any:
        return self.features.get(key)

    def has_feature(self, key: str) -> bool:
        return key in self.features and self.features[key] not in (None, [], "")


@dataclass
class Question:
    id: str
    text: str
    feature_key: str
    expected_value: Any
    match_type: str  # "equals" | "list_contains" | "numeric"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --no-sync pytest akinator/tests/test_data_loader.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add akinator/app/models.py akinator/tests/test_data_loader.py
git commit -m "feat(akinator): Entity/Question/Answer models"
```

---

## Task 3: Expected-answer derivation (the heart of matching)

This pure function decides, for a given entity and question, whether the entity
"matches" — returning one of `match` / `mismatch` / `missing`. Both scoring and
question selection depend on it.

**Files:**
- Create: `akinator/app/inference/__init__.py` (empty)
- Create: `akinator/app/inference/scoring.py` (the `expected_match` function for now)
- Test: `akinator/tests/test_scoring.py`

- [ ] **Step 1: Write the failing test** (create `akinator/tests/test_scoring.py`)

```python
from app.inference.scoring import MatchResult, expected_match
from app.models import Entity, Question


def _entity(features):
    return Entity(id="Q", name="n", aliases=[], description="", image_url=None,
                  features=features)


def test_equals_match_and_mismatch():
    q = Question("q", "?", "gender", "male", "equals")
    assert expected_match(_entity({"gender": "male"}), q) == MatchResult.MATCH
    assert expected_match(_entity({"gender": "female"}), q) == MatchResult.MISMATCH


def test_missing_feature_is_missing():
    q = Question("q", "?", "gender", "male", "equals")
    assert expected_match(_entity({}), q) == MatchResult.MISSING


def test_list_contains():
    q = Question("q", "?", "occupation", "actor", "list_contains")
    assert expected_match(_entity({"occupation": ["actor", "singer"]}), q) == MatchResult.MATCH
    assert expected_match(_entity({"occupation": ["singer"]}), q) == MatchResult.MISMATCH
    assert expected_match(_entity({"occupation": []}), q) == MatchResult.MISSING


def test_numeric_equals():
    q = Question("q", "?", "birth_century", 20, "numeric")
    assert expected_match(_entity({"birth_century": 20}), q) == MatchResult.MATCH
    assert expected_match(_entity({"birth_century": 19}), q) == MatchResult.MISMATCH
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --no-sync pytest akinator/tests/test_scoring.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.inference.scoring'`.

- [ ] **Step 3: Create empty `akinator/app/inference/__init__.py`, then write `akinator/app/inference/scoring.py`**

```python
"""Probabilistic scoring for akinator candidates.

`expected_match` classifies an entity against a question. `update_log_score`
applies a Bayesian-style log-likelihood update keyed on the user's answer,
with missing attributes treated as neutral + a soft penalty (so sparse Wikidata
entities are not eliminated)."""
from __future__ import annotations

import math
from enum import Enum

from app.models import Answer, Entity, Question


class MatchResult(str, Enum):
    MATCH = "match"
    MISMATCH = "mismatch"
    MISSING = "missing"


def expected_match(entity: Entity, question: Question) -> MatchResult:
    if not entity.has_feature(question.feature_key):
        return MatchResult.MISSING
    value = entity.feature(question.feature_key)
    mt = question.match_type
    if mt == "list_contains":
        return MatchResult.MATCH if question.expected_value in value else MatchResult.MISMATCH
    # equals / numeric
    return MatchResult.MATCH if value == question.expected_value else MatchResult.MISMATCH
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --no-sync pytest akinator/tests/test_scoring.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add akinator/app/inference/__init__.py akinator/app/inference/scoring.py akinator/tests/test_scoring.py
git commit -m "feat(akinator): expected_match classifier"
```

---

## Task 4: Log-score update

**Files:**
- Modify: `akinator/app/inference/scoring.py` (add constants + `update_log_score`)
- Test: `akinator/tests/test_scoring.py` (append)

- [ ] **Step 1: Append failing tests to `akinator/tests/test_scoring.py`**

```python
from app.inference.scoring import update_log_score


def test_yes_raises_match_lowers_mismatch():
    q = Question("q", "?", "gender", "male", "equals")
    male = _entity({"gender": "male"})
    female = _entity({"gender": "female"})
    assert update_log_score(0.0, male, q, Answer.YES) > 0.0
    assert update_log_score(0.0, female, q, Answer.YES) < 0.0


def test_no_is_mirror_of_yes():
    q = Question("q", "?", "gender", "male", "equals")
    male = _entity({"gender": "male"})
    assert update_log_score(0.0, male, q, Answer.NO) < 0.0


def test_unknown_is_noop():
    q = Question("q", "?", "gender", "male", "equals")
    male = _entity({"gender": "male"})
    assert update_log_score(1.23, male, q, Answer.UNKNOWN) == 1.23


def test_missing_feature_soft_penalty_not_elimination():
    q = Question("q", "?", "gender", "male", "equals")
    nofeat = _entity({})
    delta = update_log_score(0.0, nofeat, q, Answer.YES)
    # small negative, strictly greater than a full mismatch
    mismatch = update_log_score(0.0, _entity({"gender": "female"}), q, Answer.YES)
    assert mismatch < delta < 0.0


def test_probably_yes_is_weaker_than_yes():
    q = Question("q", "?", "gender", "male", "equals")
    male = _entity({"gender": "male"})
    strong = update_log_score(0.0, male, q, Answer.YES)
    weak = update_log_score(0.0, male, q, Answer.PROBABLY_YES)
    assert 0.0 < weak < strong
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run --no-sync pytest akinator/tests/test_scoring.py -v`
Expected: FAIL — `ImportError: cannot import name 'update_log_score'`.

- [ ] **Step 3: Append to `akinator/app/inference/scoring.py`**

```python
# Log-likelihood magnitudes. Tunable in one place.
STRONG = math.log(0.9 / 0.1)          # decisive evidence
WEAK_MISSING = math.log(0.6 / 0.4)    # soft penalty for missing attribute
_PROBABLY_SCALE = 0.5                  # "probably_*" is half as confident


def _signed_delta(result: MatchResult, asked_positive: bool) -> float:
    """Delta for a definite yes/no answer. asked_positive=True means the user
    said the property holds (YES); False means it does not (NO)."""
    if result is MatchResult.MISSING:
        return -WEAK_MISSING
    agrees = (result is MatchResult.MATCH) == asked_positive
    return STRONG if agrees else -STRONG


def update_log_score(
    log_score: float, entity: Entity, question: Question, answer: Answer
) -> float:
    if answer is Answer.UNKNOWN:
        return log_score
    result = expected_match(entity, question)
    if answer in (Answer.YES, Answer.NO):
        return log_score + _signed_delta(result, answer is Answer.YES)
    # probably_yes / probably_no — same direction, scaled down
    asked_positive = answer is Answer.PROBABLY_YES
    return log_score + _PROBABLY_SCALE * _signed_delta(result, asked_positive)
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run --no-sync pytest akinator/tests/test_scoring.py -v`
Expected: 9 passed (4 from Task 3 + 5 new).

- [ ] **Step 5: Commit**

```bash
git add akinator/app/inference/scoring.py akinator/tests/test_scoring.py
git commit -m "feat(akinator): Bayesian-style log-score update with soft missing penalty"
```

---

## Task 5: Posterior + top candidates helper

**Files:**
- Modify: `akinator/app/inference/scoring.py` (add `posteriors`, `top_candidates`)
- Test: `akinator/tests/test_scoring.py` (append)

- [ ] **Step 1: Append failing tests**

```python
from app.inference.scoring import posteriors, top_candidates


def test_posteriors_sum_to_one_and_rank():
    scores = {"a": 2.0, "b": 0.0, "c": -1.0}
    p = posteriors(scores)
    assert abs(sum(p.values()) - 1.0) < 1e-9
    assert p["a"] > p["b"] > p["c"]


def test_top_candidates_orders_desc():
    scores = {"a": 0.0, "b": 5.0, "c": 1.0}
    top = top_candidates(scores, k=2)
    assert [eid for eid, _ in top] == ["b", "c"]
    assert len(top) == 2
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run --no-sync pytest akinator/tests/test_scoring.py -v`
Expected: FAIL — `ImportError: cannot import name 'posteriors'`.

- [ ] **Step 3: Append to `scoring.py`**

```python
def posteriors(scores: dict[str, float]) -> dict[str, float]:
    """Softmax over log-scores -> probability per entity id."""
    if not scores:
        return {}
    m = max(scores.values())
    exps = {k: math.exp(v - m) for k, v in scores.items()}
    z = sum(exps.values())
    return {k: v / z for k, v in exps.items()}


def top_candidates(scores: dict[str, float], k: int = 5) -> list[tuple[str, float]]:
    """Return [(entity_id, posterior), ...] sorted by posterior descending."""
    post = posteriors(scores)
    return sorted(post.items(), key=lambda kv: kv[1], reverse=True)[:k]
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run --no-sync pytest akinator/tests/test_scoring.py -v`
Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add akinator/app/inference/scoring.py akinator/tests/test_scoring.py
git commit -m "feat(akinator): posteriors + top_candidates"
```

---

## Task 6: Question selection (split score)

**Files:**
- Create: `akinator/app/inference/question_selection.py`
- Test: `akinator/tests/test_question_selection.py`

- [ ] **Step 1: Write the failing test**

```python
from app.inference.question_selection import select_question, split_score
from app.models import Entity, Question


def _e(eid, features):
    return Entity(id=eid, name=eid, aliases=[], description="", image_url=None,
                  features=features)


def _make_pool():
    # 4 entities: 2 male, 2 female; 1 actor, 3 not
    return [
        _e("a", {"gender": "male", "occupation": ["actor"]}),
        _e("b", {"gender": "male", "occupation": ["singer"]}),
        _e("c", {"gender": "female", "occupation": ["singer"]}),
        _e("d", {"gender": "female", "occupation": ["singer"]}),
    ]


def test_split_score_prefers_even_split():
    pool = _make_pool()
    weights = {e.id: 1.0 for e in pool}
    q_gender = Question("qg", "?", "gender", "male", "equals")     # 2/2 even
    q_actor = Question("qa", "?", "occupation", "actor", "list_contains")  # 1/3 skewed
    # lower split_score = more balanced = better
    assert split_score(q_gender, pool, weights) < split_score(q_actor, pool, weights)


def test_select_question_picks_most_balanced_and_skips_asked():
    pool = _make_pool()
    weights = {e.id: 1.0 for e in pool}
    q_gender = Question("qg", "?", "gender", "male", "equals")
    q_actor = Question("qa", "?", "occupation", "actor", "list_contains")
    chosen = select_question([q_gender, q_actor], pool, weights, asked_ids=set())
    assert chosen.id == "qg"
    # if gender already asked, must fall back to actor
    chosen2 = select_question([q_gender, q_actor], pool, weights, asked_ids={"qg"})
    assert chosen2.id == "qa"


def test_select_question_returns_none_when_all_asked():
    pool = _make_pool()
    weights = {e.id: 1.0 for e in pool}
    q = Question("qg", "?", "gender", "male", "equals")
    assert select_question([q], pool, weights, asked_ids={"qg"}) is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run --no-sync pytest akinator/tests/test_question_selection.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.inference.question_selection'`.

- [ ] **Step 3: Write `akinator/app/inference/question_selection.py`**

```python
"""Choose the next question that best splits current candidates.

MVP metric: minimize the weighted imbalance |yes_weight - no_weight| between
entities that would answer yes vs no. Missing-feature entities count as a half
to each side so they don't dominate selection. Lower score = more balanced =
better. Designed so the metric can later be swapped for entropy/info-gain
without touching callers."""
from __future__ import annotations

from app.inference.scoring import MatchResult, expected_match
from app.models import Entity, Question


def split_score(question: Question, pool: list[Entity], weights: dict[str, float]) -> float:
    yes_w = 0.0
    no_w = 0.0
    for e in pool:
        w = weights.get(e.id, 0.0)
        result = expected_match(e, question)
        if result is MatchResult.MATCH:
            yes_w += w
        elif result is MatchResult.MISMATCH:
            no_w += w
        else:  # MISSING -> split evenly
            yes_w += w / 2
            no_w += w / 2
    return abs(yes_w - no_w)


def select_question(
    questions: list[Question],
    pool: list[Entity],
    weights: dict[str, float],
    asked_ids: set[str],
) -> Question | None:
    candidates = [q for q in questions if q.id not in asked_ids]
    if not candidates:
        return None
    return min(candidates, key=lambda q: split_score(q, pool, weights))
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run --no-sync pytest akinator/tests/test_question_selection.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add akinator/app/inference/question_selection.py akinator/tests/test_question_selection.py
git commit -m "feat(akinator): split-score question selection"
```

---

## Task 7: Normalize raw Wikidata bindings → Entity

**Files:**
- Create: `akinator/app/normalize.py`
- Test: `akinator/tests/test_normalize.py`

The fetch script (Task 10) produces, per entity, a dict of raw SPARQL values.
`normalize_binding` converts one such dict into an `Entity`. This is tested
against a hand-written raw sample so it does not require network access.

- [ ] **Step 1: Write the failing test**

```python
from app.normalize import normalize_binding
from app.models import Entity


def _raw_einstein():
    return {
        "id": "Q937",
        "name_ja": "アルベルト・アインシュタイン",
        "name_en": "Albert Einstein",
        "aliases": ["Einstein"],
        "description": "理論物理学者",
        "image_url": "http://commons/einstein.jpg",
        "instance_of": ["Q5"],            # human
        "gender": "Q6581097",             # male
        "occupations": ["Q169470"],       # physicist
        "countries": ["Q183", "Q30"],     # Germany, United States
        "birth_year": 1879,
        "death_year": 1955,
        "in_anime": False,
    }


def test_normalize_real_person():
    e = normalize_binding(_raw_einstein())
    assert isinstance(e, Entity)
    assert e.id == "Q937"
    assert e.name == "アルベルト・アインシュタイン"
    assert "Albert Einstein" in e.aliases
    assert e.features["is_fictional"] is False
    assert e.features["gender"] == "male"
    assert "physicist" in e.features["occupation"]
    assert e.features["birth_century"] == 19   # 1879 -> 19th century
    assert e.features["is_dead"] is True
    assert e.features["in_anime"] is False


def test_normalize_fictional_uses_en_name_when_ja_missing():
    raw = {
        "id": "Q3010",
        "name_ja": None,
        "name_en": "Goku",
        "aliases": [],
        "description": "fictional character",
        "image_url": None,
        "instance_of": ["Q15632617"],   # fictional human
        "gender": "Q6581097",
        "occupations": [],
        "countries": [],
        "birth_year": None,
        "death_year": None,
        "in_anime": True,
    }
    e = normalize_binding(raw)
    assert e.name == "Goku"
    assert e.features["is_fictional"] is True
    assert e.features["in_anime"] is True
    assert "birth_century" not in e.features   # missing stays missing
    assert e.features["is_dead"] is False       # no death + not fictional-dead -> False only if known
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run --no-sync pytest akinator/tests/test_normalize.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.normalize'`.

- [ ] **Step 3: Write `akinator/app/normalize.py`**

```python
"""Convert one raw Wikidata binding dict into a normalized Entity.

Raw QIDs/years are mapped to question-ready feature values. Missing inputs are
omitted from `features` entirely (so downstream `has_feature` is False) rather
than stored as None — except booleans we can determine with confidence."""
from __future__ import annotations

from typing import Any

from app.models import Entity

# Minimal QID lookup tables. Extend as the fetch query grows.
_GENDER = {"Q6581097": "male", "Q6581072": "female"}
# instance-of QIDs that mean "fictional"
_FICTIONAL_INSTANCE = {"Q15632617", "Q95074", "Q15773347", "Q20085850"}
# occupation QID -> english slug used in questions
_OCCUPATION = {
    "Q169470": "physicist",
    "Q33999": "actor",
    "Q177220": "singer",
    "Q82955": "politician",
    "Q36180": "writer",
    "Q937857": "athlete",
    "Q639669": "musician",
    "Q1028181": "painter",
    "Q170790": "mathematician",
    "Q2526255": "film_director",
}
_COUNTRY = {
    "Q17": "Japan", "Q183": "Germany", "Q30": "United States",
    "Q145": "United Kingdom", "Q142": "France", "Q38": "Italy",
    "Q148": "China", "Q159": "Russia",
}


def _century(year: int | None) -> int | None:
    if year is None:
        return None
    return (year - 1) // 100 + 1


def _map_list(qids: list[str], table: dict[str, str]) -> list[str]:
    return [table[q] for q in qids if q in table]


def normalize_binding(raw: dict[str, Any]) -> Entity:
    name = raw.get("name_ja") or raw.get("name_en") or raw["id"]

    is_fictional = any(q in _FICTIONAL_INSTANCE for q in raw.get("instance_of", []))

    features: dict[str, Any] = {"is_fictional": is_fictional}

    gender = _GENDER.get(raw.get("gender"))
    if gender is not None:
        features["gender"] = gender

    occupations = _map_list(raw.get("occupations", []), _OCCUPATION)
    if occupations:
        features["occupation"] = occupations

    countries = _map_list(raw.get("countries", []), _COUNTRY)
    if countries:
        features["country"] = countries

    century = _century(raw.get("birth_year"))
    if century is not None:
        features["birth_century"] = century

    # is_dead: real person with a death year is dead; real person with a birth
    # year and no death year we treat as alive. Fictional: leave unknown.
    if not is_fictional and raw.get("birth_year") is not None:
        features["is_dead"] = raw.get("death_year") is not None

    if raw.get("in_anime") is not None:
        features["in_anime"] = bool(raw.get("in_anime"))

    aliases = [a for a in raw.get("aliases", []) if a]
    if raw.get("name_en") and raw.get("name_en") != name:
        aliases = [raw["name_en"], *aliases]

    return Entity(
        id=raw["id"],
        name=name,
        aliases=aliases,
        description=raw.get("description") or "",
        image_url=raw.get("image_url"),
        features=features,
    )
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run --no-sync pytest akinator/tests/test_normalize.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add akinator/app/normalize.py akinator/tests/test_normalize.py
git commit -m "feat(akinator): normalize raw Wikidata binding -> Entity"
```

---

## Task 8: Auto-generate questions from entities

**Files:**
- Create: `akinator/app/question_gen.py`
- Test: `akinator/tests/test_question_gen.py`

- [ ] **Step 1: Write the failing test**

```python
from app.question_gen import generate_questions
from app.models import Entity


def _pool():
    return [
        Entity("a", "A", [], "", None, {"is_fictional": False, "gender": "male",
                                        "occupation": ["actor"], "birth_century": 20}),
        Entity("b", "B", [], "", None, {"is_fictional": False, "gender": "female",
                                        "occupation": ["singer"], "birth_century": 20}),
        Entity("c", "C", [], "", None, {"is_fictional": True, "gender": "male",
                                        "occupation": ["actor"], "in_anime": True}),
        Entity("d", "D", [], "", None, {"is_fictional": True, "gender": "female",
                                        "in_anime": True}),
    ]


def test_generates_questions_from_attribute_values():
    qs = generate_questions(_pool(), min_fraction=0.1, max_fraction=0.9)
    keys = {(q.feature_key, q.expected_value) for q in qs}
    # boolean is_fictional split 2/2 -> kept
    assert ("is_fictional", True) in keys
    # gender male appears 2/4 -> kept
    assert ("gender", "male") in keys
    # occupation actor appears 2/4 (list_contains) -> kept
    assert ("occupation", "actor") in keys


def test_questions_have_japanese_text_and_match_type():
    qs = generate_questions(_pool(), min_fraction=0.1, max_fraction=0.9)
    q_male = next(q for q in qs if (q.feature_key, q.expected_value) == ("gender", "male"))
    assert q_male.match_type == "equals"
    assert "男" in q_male.text and q_male.text.endswith("？")
    q_actor = next(q for q in qs if (q.feature_key, q.expected_value) == ("occupation", "actor"))
    assert q_actor.match_type == "list_contains"


def test_drops_non_discriminative_values():
    # every entity is_fictional True -> useless, must be dropped
    pool = [Entity(str(i), str(i), [], "", None, {"is_fictional": True}) for i in range(4)]
    qs = generate_questions(pool, min_fraction=0.1, max_fraction=0.9)
    assert all(q.feature_key != "is_fictional" for q in qs)


def test_question_ids_unique_and_stable():
    qs = generate_questions(_pool(), min_fraction=0.1, max_fraction=0.9)
    ids = [q.id for q in qs]
    assert len(ids) == len(set(ids))
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run --no-sync pytest akinator/tests/test_question_gen.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.question_gen'`.

- [ ] **Step 3: Write `akinator/app/question_gen.py`**

```python
"""Auto-generate questions from the attribute values present across entities.

For each (feature_key, value) pair, count how many entities match. Keep only
values that are discriminative — present in a fraction of the pool between
min_fraction and max_fraction (neither ~all nor ~none). Question text is
composed from Japanese label templates, NOT hand-written per entity."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.models import Entity, Question

# Feature handling: which match_type and how to enumerate values.
_LIST_FEATURES = {"occupation", "country", "notable_work"}
_BOOL_FEATURES = {"is_fictional", "is_dead", "in_anime"}
_SCALAR_FEATURES = {"gender", "birth_century", "species"}

# Japanese templates. {v} is the value label.
_VALUE_LABELS = {
    ("gender", "male"): "男性", ("gender", "female"): "女性",
    ("occupation", "actor"): "俳優", ("occupation", "singer"): "歌手",
    ("occupation", "physicist"): "物理学者", ("occupation", "politician"): "政治家",
    ("occupation", "writer"): "作家", ("occupation", "athlete"): "スポーツ選手",
    ("occupation", "musician"): "音楽家", ("occupation", "painter"): "画家",
    ("occupation", "mathematician"): "数学者", ("occupation", "film_director"): "映画監督",
    ("country", "Japan"): "日本", ("country", "United States"): "アメリカ",
    ("country", "Germany"): "ドイツ", ("country", "United Kingdom"): "イギリス",
    ("country", "France"): "フランス", ("country", "Italy"): "イタリア",
    ("country", "China"): "中国", ("country", "Russia"): "ロシア",
}


def _label(feature_key: str, value: Any) -> str:
    return _VALUE_LABELS.get((feature_key, value), str(value))


def _question_text(feature_key: str, value: Any) -> str:
    if feature_key == "is_fictional":
        return "架空のキャラクターですか？" if value else "実在する人物ですか？"
    if feature_key == "is_dead":
        return "すでに亡くなっていますか？" if value else "存命ですか？"
    if feature_key == "in_anime":
        return "アニメ作品に登場しますか？"
    if feature_key == "gender":
        return f"{_label(feature_key, value)}ですか？"
    if feature_key == "occupation":
        return f"{_label(feature_key, value)}ですか？"
    if feature_key == "country":
        return f"{_label(feature_key, value)}と関係がありますか？"
    if feature_key == "birth_century":
        return f"{value}世紀生まれですか？"
    if feature_key == "species":
        return f"{value}ですか？"
    return f"{feature_key} は {value} ですか？"


def _match_type(feature_key: str) -> str:
    if feature_key in _LIST_FEATURES:
        return "list_contains"
    if feature_key == "birth_century":
        return "numeric"
    return "equals"


def _question_id(feature_key: str, value: Any) -> str:
    return f"q_{feature_key}_{value}"


def generate_questions(
    entities: list[Entity], min_fraction: float = 0.05, max_fraction: float = 0.95
) -> list[Question]:
    n = len(entities)
    if n == 0:
        return []
    # count entities matching each (feature_key, value)
    counts: dict[tuple[str, Any], int] = defaultdict(int)
    considered = _LIST_FEATURES | _BOOL_FEATURES | _SCALAR_FEATURES
    for e in entities:
        for key in considered:
            if key not in e.features:
                continue
            val = e.features[key]
            if key in _LIST_FEATURES:
                for item in val:
                    counts[(key, item)] += 1
            else:
                counts[(key, val)] += 1

    questions: list[Question] = []
    for (key, val), c in sorted(counts.items(), key=lambda kv: str(kv[0])):
        frac = c / n
        if frac < min_fraction or frac > max_fraction:
            continue
        questions.append(
            Question(
                id=_question_id(key, val),
                text=_question_text(key, val),
                feature_key=key,
                expected_value=val,
                match_type=_match_type(key),
            )
        )
    return questions
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run --no-sync pytest akinator/tests/test_question_gen.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add akinator/app/question_gen.py akinator/tests/test_question_gen.py
git commit -m "feat(akinator): auto-generate questions from attribute values"
```

---

## Task 9: Data loader (JSON ↔ objects)

**Files:**
- Create: `akinator/app/data_loader.py`
- Test: `akinator/tests/test_data_loader.py` (append)

- [ ] **Step 1: Append failing tests to `akinator/tests/test_data_loader.py`**

```python
import json
from app.data_loader import (
    dump_entities, dump_questions, load_entities, load_questions,
)
from app.models import Entity, Question


def test_entities_roundtrip(tmp_path):
    entities = [
        Entity("Q1", "A", ["a"], "d", None, {"gender": "male", "occupation": ["actor"]}),
    ]
    path = tmp_path / "entities.json"
    dump_entities(entities, path)
    loaded = load_entities(path)
    assert loaded[0].id == "Q1"
    assert loaded[0].features["occupation"] == ["actor"]


def test_questions_roundtrip(tmp_path):
    qs = [Question("q1", "?", "gender", "male", "equals")]
    path = tmp_path / "questions.json"
    dump_questions(qs, path)
    loaded = load_questions(path)
    assert loaded[0].id == "q1"
    assert loaded[0].match_type == "equals"
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run --no-sync pytest akinator/tests/test_data_loader.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.data_loader'`.

- [ ] **Step 3: Write `akinator/app/data_loader.py`**

```python
"""Serialize/deserialize entities and questions to/from JSON on disk."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from app.models import Entity, Question


def dump_entities(entities: list[Entity], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [asdict(e) for e in entities]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_entities(path: Path) -> list[Entity]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Entity(**d) for d in data]


def dump_questions(questions: list[Question], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [asdict(q) for q in questions]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_questions(path: Path) -> list[Question]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Question(**d) for d in data]
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run --no-sync pytest akinator/tests/test_data_loader.py -v`
Expected: 5 passed (3 model + 2 roundtrip).

- [ ] **Step 5: Commit**

```bash
git add akinator/app/data_loader.py akinator/tests/test_data_loader.py
git commit -m "feat(akinator): JSON data loader for entities/questions"
```

---

## Task 10: Wikidata fetch script + build script

These scripts hit the network, so they are not unit-tested against live WDQS.
The normalization they call (`normalize_binding`) and question generation
(`generate_questions`) are already tested. We add one offline test that the
build step wires fetch-output → processed files using a stubbed raw file.

**Files:**
- Create: `akinator/scripts/fetch_wikidata_entities.py`
- Create: `akinator/scripts/build_questions.py`
- Test: `akinator/tests/test_build_pipeline.py`

- [ ] **Step 1: Write the failing test** (`akinator/tests/test_build_pipeline.py`)

```python
import json
from pathlib import Path

from app.data_loader import load_entities, load_questions

# build_questions exposes a pure function we can call without network
from scripts.build_questions import build_from_raw


def test_build_from_raw_writes_processed(tmp_path):
    raw = [
        {"id": "Q1", "name_ja": "俳優A", "name_en": "ActorA", "aliases": [],
         "description": "d", "image_url": None, "instance_of": ["Q5"],
         "gender": "Q6581097", "occupations": ["Q33999"], "countries": ["Q17"],
         "birth_year": 1970, "death_year": None, "in_anime": False},
        {"id": "Q2", "name_ja": "歌手B", "name_en": "SingerB", "aliases": [],
         "description": "d", "image_url": None, "instance_of": ["Q5"],
         "gender": "Q6581072", "occupations": ["Q177220"], "countries": ["Q30"],
         "birth_year": 1985, "death_year": None, "in_anime": False},
    ]
    raw_path = tmp_path / "raw.json"
    raw_path.write_text(json.dumps(raw), encoding="utf-8")
    ent_path = tmp_path / "entities.json"
    q_path = tmp_path / "questions.json"

    build_from_raw(raw_path, ent_path, q_path, min_fraction=0.1, max_fraction=0.95)

    entities = load_entities(ent_path)
    questions = load_questions(q_path)
    assert {e.id for e in entities} == {"Q1", "Q2"}
    assert len(questions) > 0
    # gender splits 1/1 -> a gender question should exist
    assert any(q.feature_key == "gender" for q in questions)
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run --no-sync pytest akinator/tests/test_build_pipeline.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.build_questions'`.

- [ ] **Step 3a: Create `akinator/scripts/__init__.py`** (empty)

- [ ] **Step 3b: Write `akinator/scripts/build_questions.py`**

```python
"""Build processed entities.json + questions.json from a raw Wikidata dump.

`build_from_raw` is pure (no network) and unit-tested. Run as a script to use
the default data/raw -> data/processed paths."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config  # noqa: E402
from app.data_loader import dump_entities, dump_questions  # noqa: E402
from app.normalize import normalize_binding  # noqa: E402
from app.question_gen import generate_questions  # noqa: E402


def build_from_raw(
    raw_path: Path,
    entities_path: Path,
    questions_path: Path,
    min_fraction: float = 0.05,
    max_fraction: float = 0.95,
) -> None:
    raw = json.loads(Path(raw_path).read_text(encoding="utf-8"))
    entities = [normalize_binding(r) for r in raw]
    questions = generate_questions(entities, min_fraction, max_fraction)
    dump_entities(entities, entities_path)
    dump_questions(questions, questions_path)
    print(f"wrote {len(entities)} entities, {len(questions)} questions")


def main() -> None:
    raw_path = config.RAW_DIR / "wikidata_entities.json"
    build_from_raw(raw_path, config.ENTITIES_PATH, config.QUESTIONS_PATH)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run --no-sync pytest akinator/tests/test_build_pipeline.py -v`
Expected: 1 passed.

- [ ] **Step 5a: Write `akinator/scripts/fetch_wikidata_entities.py`** (network; not unit-tested)

```python
"""Fetch ~200 real notable people + ~200 fictional/anime characters from
Wikidata via SPARQL, writing one raw JSON list to data/raw/.

Polite usage: explicit User-Agent, sleep between the two queries, LIMIT caps.
On fetch failure, falls back to the existing cached raw (left untouched)."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import config  # noqa: E402

WDQS = "https://query.wikidata.org/sparql"
USER_AGENT = "akinator-mvp/0.1 (local hobby project; https://github.com/ankimo1210)"

REAL_PEOPLE_QUERY = """
SELECT ?item ?itemLabel ?itemLabelEn ?desc ?img ?gender ?birth ?death
       (GROUP_CONCAT(DISTINCT ?occ; separator="|") AS ?occs)
       (GROUP_CONCAT(DISTINCT ?cit; separator="|") AS ?cits)
WHERE {
  ?item wdt:P31 wd:Q5 ;
        wikibase:sitelinks ?sl .
  FILTER(?sl > 80)
  OPTIONAL { ?item wdt:P21 ?gender. }
  OPTIONAL { ?item wdt:P106 ?occ. }
  OPTIONAL { ?item wdt:P27 ?cit. }
  OPTIONAL { ?item wdt:P569 ?birth. }
  OPTIONAL { ?item wdt:P570 ?death. }
  OPTIONAL { ?item wdt:P18 ?img. }
  OPTIONAL { ?item schema:description ?desc. FILTER(LANG(?desc)="ja") }
  OPTIONAL { ?item rdfs:label ?itemLabel. FILTER(LANG(?itemLabel)="ja") }
  OPTIONAL { ?item rdfs:label ?itemLabelEn. FILTER(LANG(?itemLabelEn)="en") }
}
GROUP BY ?item ?itemLabel ?itemLabelEn ?desc ?img ?gender ?birth ?death
ORDER BY DESC(?sl)
LIMIT 200
"""

FICTIONAL_QUERY = """
SELECT ?item ?itemLabel ?itemLabelEn ?desc ?img ?gender
       (GROUP_CONCAT(DISTINCT ?inst; separator="|") AS ?insts)
WHERE {
  ?item wdt:P31 ?inst .
  VALUES ?inst { wd:Q15632617 wd:Q95074 }   # fictional human / fictional character
  ?item wikibase:sitelinks ?sl .
  FILTER(?sl > 30)
  OPTIONAL { ?item wdt:P21 ?gender. }
  OPTIONAL { ?item wdt:P18 ?img. }
  OPTIONAL { ?item schema:description ?desc. FILTER(LANG(?desc)="ja") }
  OPTIONAL { ?item rdfs:label ?itemLabel. FILTER(LANG(?itemLabel)="ja") }
  OPTIONAL { ?item rdfs:label ?itemLabelEn. FILTER(LANG(?itemLabelEn)="en") }
}
GROUP BY ?item ?itemLabel ?itemLabelEn ?desc ?img ?gender
ORDER BY DESC(?sl)
LIMIT 200
"""


def _qid(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


def _year(iso: str | None) -> int | None:
    if not iso:
        return None
    try:
        # handles leading '-' for BCE and 'T...' suffix
        head = iso.split("T")[0]
        sign = -1 if head.startswith("-") else 1
        return sign * int(head.lstrip("-").split("-")[0])
    except (ValueError, IndexError):
        return None


def _run_query(client: httpx.Client, query: str) -> list[dict]:
    resp = client.get(WDQS, params={"query": query, "format": "json"},
                      headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"},
                      timeout=120)
    resp.raise_for_status()
    return resp.json()["results"]["bindings"]


def _v(row: dict, key: str) -> str | None:
    cell = row.get(key)
    return cell["value"] if cell else None


def _split(row: dict, key: str) -> list[str]:
    raw = _v(row, key)
    return [p for p in raw.split("|") if p] if raw else []


def fetch() -> list[dict]:
    out: list[dict] = []
    with httpx.Client() as client:
        for row in _run_query(client, REAL_PEOPLE_QUERY):
            out.append({
                "id": _qid(_v(row, "item")),
                "name_ja": _v(row, "itemLabel"),
                "name_en": _v(row, "itemLabelEn"),
                "aliases": [],
                "description": _v(row, "desc"),
                "image_url": _v(row, "img"),
                "instance_of": ["Q5"],
                "gender": _qid(_v(row, "gender")) if _v(row, "gender") else None,
                "occupations": [_qid(u) for u in _split(row, "occs")],
                "countries": [_qid(u) for u in _split(row, "cits")],
                "birth_year": _year(_v(row, "birth")),
                "death_year": _year(_v(row, "death")),
                "in_anime": False,
            })
        time.sleep(2)
        for row in _run_query(client, FICTIONAL_QUERY):
            out.append({
                "id": _qid(_v(row, "item")),
                "name_ja": _v(row, "itemLabel"),
                "name_en": _v(row, "itemLabelEn"),
                "aliases": [],
                "description": _v(row, "desc"),
                "image_url": _v(row, "img"),
                "instance_of": [_qid(u) for u in _split(row, "insts")],
                "gender": _qid(_v(row, "gender")) if _v(row, "gender") else None,
                "occupations": [],
                "countries": [],
                "birth_year": None,
                "death_year": None,
                "in_anime": True,
            })
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true",
                        help="re-fetch even if cache exists")
    args = parser.parse_args()
    out_path = config.RAW_DIR / "wikidata_entities.json"
    if out_path.exists() and not args.refresh:
        print(f"cache exists at {out_path}; use --refresh to re-fetch")
        return
    try:
        data = fetch()
    except (httpx.HTTPError, KeyError) as exc:
        # Spec policy: on fetch failure, fall back to cached raw if present.
        if out_path.exists():
            print(f"fetch failed ({exc}); keeping cached raw at {out_path}")
            return
        raise
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"fetched {len(data)} raw entities -> {out_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5b: Run the real fetch + build to produce committed data**

Run: `cd ~/projects && uv run --no-sync python akinator/scripts/fetch_wikidata_entities.py`
Expected: `fetched <N> raw entities -> .../data/raw/wikidata_entities.json` (N in the few-hundreds).

Run: `uv run --no-sync python akinator/scripts/build_questions.py`
Expected: `wrote <E> entities, <Q> questions` with E≈300-400, Q≈15-40.

If WDQS is unreachable, note it in the report and proceed — a later manual run can regenerate. The app still works once `processed/` exists.

- [ ] **Step 6: Commit (code + generated processed data, raw stays ignored)**

```bash
git add akinator/scripts/__init__.py akinator/scripts/build_questions.py akinator/scripts/fetch_wikidata_entities.py akinator/tests/test_build_pipeline.py
git add -f akinator/data/processed/entities.json akinator/data/processed/questions.json
git commit -m "feat(akinator): Wikidata fetch + build pipeline; commit processed data"
```

---

## Task 11: Entity service (singleton load + lookup)

**Files:**
- Create: `akinator/app/services/__init__.py` (empty)
- Create: `akinator/app/services/entity_service.py`
- Test: `akinator/tests/test_game_service.py` (entity-service part)

- [ ] **Step 1: Create `akinator/tests/conftest.py` with a shared tiny fixture**

```python
import pytest

from app.models import Entity, Question


@pytest.fixture
def small_pool():
    return [
        Entity("a", "アクターA", [], "俳優", None,
               {"is_fictional": False, "gender": "male", "occupation": ["actor"],
                "birth_century": 20, "is_dead": False}),
        Entity("b", "シンガーB", [], "歌手", None,
               {"is_fictional": False, "gender": "female", "occupation": ["singer"],
                "birth_century": 20, "is_dead": False}),
        Entity("c", "悟空", [], "キャラ", None,
               {"is_fictional": True, "gender": "male", "in_anime": True}),
        Entity("d", "セーラーD", [], "キャラ", None,
               {"is_fictional": True, "gender": "female", "in_anime": True}),
    ]


@pytest.fixture
def small_questions():
    return [
        Question("q_is_fictional_True", "架空のキャラクターですか？", "is_fictional", True, "equals"),
        Question("q_gender_male", "男性ですか？", "gender", "male", "equals"),
        Question("q_occupation_actor", "俳優ですか？", "occupation", "actor", "list_contains"),
        Question("q_in_anime_True", "アニメ作品に登場しますか？", "in_anime", True, "equals"),
    ]
```

- [ ] **Step 2: Write the failing test** (create `akinator/tests/test_game_service.py`)

```python
from app.services.entity_service import EntityService


def test_entity_service_lookup(small_pool, small_questions):
    svc = EntityService(small_pool, small_questions)
    assert svc.get_entity("a").name == "アクターA"
    assert svc.get_entity("zzz") is None
    assert len(svc.entities) == 4
    assert len(svc.questions) == 4
```

- [ ] **Step 3: Run to verify it fails**

Run: `uv run --no-sync pytest akinator/tests/test_game_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.entity_service'`.

- [ ] **Step 4: Create empty `akinator/app/services/__init__.py`, then write `akinator/app/services/entity_service.py`**

```python
"""Holds the loaded entity/question collections and id lookups. Constructed once
from JSON at app startup (see main.py) or directly in tests."""
from __future__ import annotations

from app.config import ENTITIES_PATH, QUESTIONS_PATH
from app.data_loader import load_entities, load_questions
from app.models import Entity, Question


class EntityService:
    def __init__(self, entities: list[Entity], questions: list[Question]) -> None:
        self.entities = entities
        self.questions = questions
        self._by_id = {e.id: e for e in entities}

    @classmethod
    def from_disk(cls) -> "EntityService":
        return cls(load_entities(ENTITIES_PATH), load_questions(QUESTIONS_PATH))

    def get_entity(self, entity_id: str) -> Entity | None:
        return self._by_id.get(entity_id)
```

- [ ] **Step 5: Run to verify it passes**

Run: `uv run --no-sync pytest akinator/tests/test_game_service.py -v`
Expected: 1 passed.

- [ ] **Step 6: Commit**

```bash
git add akinator/app/services/__init__.py akinator/app/services/entity_service.py akinator/tests/conftest.py akinator/tests/test_game_service.py
git commit -m "feat(akinator): EntityService load + lookup"
```

---

## Task 12: Game service (session state machine)

**Files:**
- Create: `akinator/app/services/game_service.py`
- Test: `akinator/tests/test_game_service.py` (append)

A `GameState` holds per-session log-scores + asked question ids. The service
advances it: pick next question, record an answer, decide when to guess.

- [ ] **Step 1: Append failing tests to `akinator/tests/test_game_service.py`**

```python
from app.models import Answer
from app.services.game_service import GameService, GameState


def test_initial_scores_zero_and_first_question(small_pool, small_questions):
    svc = GameService(EntityService(small_pool, small_questions))
    state = svc.new_game()
    assert set(state.log_scores) == {"a", "b", "c", "d"}
    assert all(v == 0.0 for v in state.log_scores.values())
    q = svc.next_question(state)
    assert q is not None and q.id not in state.asked_ids


def test_answer_updates_scores_and_marks_asked(small_pool, small_questions):
    svc = GameService(EntityService(small_pool, small_questions))
    state = svc.new_game()
    q = next(q for q in small_questions if q.id == "q_gender_male")
    svc.record_answer(state, q, Answer.YES)
    assert q.id in state.asked_ids
    # males a, c rise above females b, d
    assert state.log_scores["a"] > state.log_scores["b"]
    assert state.log_scores["c"] > state.log_scores["d"]


def test_asked_question_not_reselected(small_pool, small_questions):
    svc = GameService(EntityService(small_pool, small_questions))
    state = svc.new_game()
    first = svc.next_question(state)
    svc.record_answer(state, first, Answer.YES)
    second = svc.next_question(state)
    assert second is None or second.id != first.id


def test_unknown_answer_keeps_scores(small_pool, small_questions):
    svc = GameService(EntityService(small_pool, small_questions))
    state = svc.new_game()
    q = next(q for q in small_questions if q.id == "q_gender_male")
    svc.record_answer(state, q, Answer.UNKNOWN)
    assert all(v == 0.0 for v in state.log_scores.values())
    assert q.id in state.asked_ids  # still consumed


def test_best_guess_returns_top_entity(small_pool, small_questions):
    svc = GameService(EntityService(small_pool, small_questions))
    state = svc.new_game()
    q = next(q for q in small_questions if q.id == "q_is_fictional_True")
    svc.record_answer(state, q, Answer.YES)   # favors c, d
    guess, posterior = svc.best_guess(state)
    assert guess.id in {"c", "d"}
    assert 0.0 < posterior <= 1.0


def test_should_guess_threshold(small_pool, small_questions):
    svc = GameService(EntityService(small_pool, small_questions), guess_threshold=0.6)
    state = svc.new_game()
    # answer several questions to concentrate mass on one entity
    for qid, ans in [("q_is_fictional_True", Answer.NO),
                     ("q_gender_male", Answer.YES),
                     ("q_occupation_actor", Answer.YES)]:
        q = next(q for q in small_questions if q.id == qid)
        svc.record_answer(state, q, ans)
    # 'a' should dominate; either threshold reached or no questions left
    assert svc.should_guess(state) in (True, False)
    guess, _ = svc.best_guess(state)
    assert guess.id == "a"
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run --no-sync pytest akinator/tests/test_game_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.game_service'`.

- [ ] **Step 3: Write `akinator/app/services/game_service.py`**

```python
"""Per-session game orchestration over the pure inference functions.

GameState is plain data (serializable to/from the request/DB). GameService is
stateless beyond the EntityService it wraps; all mutation lives on the passed-in
state."""
from __future__ import annotations

from dataclasses import dataclass, field

from app.inference.question_selection import select_question
from app.inference.scoring import top_candidates, update_log_score
from app.models import Answer, Entity, Question
from app.services.entity_service import EntityService


@dataclass
class GameState:
    log_scores: dict[str, float]
    asked_ids: set[str] = field(default_factory=set)
    history: list[tuple[str, str]] = field(default_factory=list)  # (question_id, answer)


class GameService:
    def __init__(self, entities: EntityService, guess_threshold: float = 0.85,
                 max_questions: int = 20) -> None:
        self.entities = entities
        self.guess_threshold = guess_threshold
        self.max_questions = max_questions

    def new_game(self) -> GameState:
        return GameState(log_scores={e.id: 0.0 for e in self.entities.entities})

    def _weights(self, state: GameState) -> dict[str, float]:
        from app.inference.scoring import posteriors
        return posteriors(state.log_scores)

    def next_question(self, state: GameState) -> Question | None:
        return select_question(
            self.entities.questions,
            self.entities.entities,
            self._weights(state),
            state.asked_ids,
        )

    def record_answer(self, state: GameState, question: Question, answer: Answer) -> None:
        for e in self.entities.entities:
            state.log_scores[e.id] = update_log_score(
                state.log_scores[e.id], e, question, answer
            )
        state.asked_ids.add(question.id)
        state.history.append((question.id, answer.value))

    def best_guess(self, state: GameState) -> tuple[Entity, float]:
        top = top_candidates(state.log_scores, k=1)
        entity_id, posterior = top[0]
        return self.entities.get_entity(entity_id), posterior

    def should_guess(self, state: GameState) -> bool:
        if len(state.asked_ids) >= self.max_questions:
            return True
        if self.next_question(state) is None:
            return True
        _, posterior = self.best_guess(state)
        return posterior >= self.guess_threshold
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run --no-sync pytest akinator/tests/test_game_service.py -v`
Expected: 7 passed (1 entity-service + 6 game).

- [ ] **Step 5: Commit**

```bash
git add akinator/app/services/game_service.py akinator/tests/test_game_service.py
git commit -m "feat(akinator): GameService session state machine"
```

---

## Task 13: SQLite persistence (games / answers / corrections)

**Files:**
- Create: `akinator/app/db.py`
- Test: `akinator/tests/test_db.py`

- [ ] **Step 1: Write the failing test** (`akinator/tests/test_db.py`)

```python
from app.db import (
    init_db, create_game, save_answer, finish_game, save_correction,
    get_game_answers,
)


def test_game_lifecycle(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    gid = create_game(db)
    assert isinstance(gid, int)
    save_answer(db, gid, "q_gender_male", "yes", 1)
    save_answer(db, gid, "q_in_anime_True", "no", 2)
    rows = get_game_answers(db, gid)
    assert [r["question_id"] for r in rows] == ["q_gender_male", "q_in_anime_True"]
    finish_game(db, gid, guessed_entity_id="a", was_correct=False)
    save_correction(db, gid, "実は別人B")
    # finishing + correction must not raise; answers still retrievable
    assert len(get_game_answers(db, gid)) == 2
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run --no-sync pytest akinator/tests/test_db.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.db'`.

- [ ] **Step 3: Write `akinator/app/db.py`**

```python
"""SQLite persistence for game history and corrections (future training data).
Entities/questions are NOT stored here — they load from JSON."""
from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    status TEXT NOT NULL DEFAULT 'active',
    guessed_entity_id TEXT,
    was_correct INTEGER
);
CREATE TABLE IF NOT EXISTS game_answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL REFERENCES games(id),
    question_id TEXT NOT NULL,
    answer TEXT NOT NULL,
    asked_order INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS corrections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL REFERENCES games(id),
    correct_entity TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path) -> None:
    with closing(_connect(db_path)) as conn:
        conn.executescript(_SCHEMA)
        conn.commit()


def create_game(db_path: Path) -> int:
    with closing(_connect(db_path)) as conn:
        cur = conn.execute("INSERT INTO games DEFAULT VALUES")
        conn.commit()
        return int(cur.lastrowid)


def save_answer(db_path: Path, game_id: int, question_id: str, answer: str,
                asked_order: int) -> None:
    with closing(_connect(db_path)) as conn:
        conn.execute(
            "INSERT INTO game_answers (game_id, question_id, answer, asked_order) "
            "VALUES (?, ?, ?, ?)",
            (game_id, question_id, answer, asked_order),
        )
        conn.commit()


def finish_game(db_path: Path, game_id: int, guessed_entity_id: str,
                was_correct: bool) -> None:
    with closing(_connect(db_path)) as conn:
        conn.execute(
            "UPDATE games SET status='finished', guessed_entity_id=?, was_correct=? "
            "WHERE id=?",
            (guessed_entity_id, 1 if was_correct else 0, game_id),
        )
        conn.commit()


def save_correction(db_path: Path, game_id: int, correct_entity: str) -> None:
    with closing(_connect(db_path)) as conn:
        conn.execute(
            "INSERT INTO corrections (game_id, correct_entity) VALUES (?, ?)",
            (game_id, correct_entity),
        )
        conn.commit()


def get_game_answers(db_path: Path, game_id: int) -> list[dict]:
    with closing(_connect(db_path)) as conn:
        rows = conn.execute(
            "SELECT question_id, answer, asked_order FROM game_answers "
            "WHERE game_id=? ORDER BY asked_order",
            (game_id,),
        ).fetchall()
        return [dict(r) for r in rows]
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run --no-sync pytest akinator/tests/test_db.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add akinator/app/db.py akinator/tests/test_db.py
git commit -m "feat(akinator): SQLite persistence for games/answers/corrections"
```

---

## Task 14: FastAPI app + templates + in-memory session wiring

The web layer keeps `GameState` objects in an in-process dict keyed by game id
(the SQLite row id). State is plain data; for MVP in-memory session store is
sufficient and avoids serializing scores each request.

**Files:**
- Create: `akinator/app/main.py`
- Create: `akinator/app/templates/{base,start,question,guess,wrong,debug}.html`
- Test: `akinator/tests/test_api.py`

- [ ] **Step 1: Write the failing test** (`akinator/tests/test_api.py`)

```python
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch, small_pool, small_questions):
    # point the app at a temp DB and the fixture pool before importing
    import app.config as config
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "t.db")
    import app.main as main_mod
    monkeypatch.setattr(
        main_mod, "ENTITY_SERVICE",
        main_mod.EntityService(small_pool, small_questions), raising=False,
    )
    main_mod.GAME_SERVICE = main_mod.GameService(main_mod.ENTITY_SERVICE)
    main_mod.SESSIONS.clear()
    main_mod.db.init_db(config.DB_PATH)
    return TestClient(main_mod.app)


def test_start_page_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "アキネーター" in r.text


def test_full_game_flow_to_guess(client):
    # start a game
    r = client.post("/game/new", follow_redirects=False)
    assert r.status_code in (302, 303)
    location = r.headers["location"]
    game_id = int(location.rstrip("/").split("/")[-1].split("?")[0]) if location[-1].isdigit() else None
    # walk: fetch question page, answer 'yes' repeatedly until guess
    gid = location.split("/")[2]
    for _ in range(25):
        page = client.get(f"/game/{gid}")
        if "推測" in page.text or page.url.path.endswith("/guess"):
            break
        r = client.post(f"/game/{gid}/answer", data={"answer": "yes"},
                        follow_redirects=True)
        assert r.status_code == 200
    guess = client.get(f"/game/{gid}/guess")
    assert guess.status_code == 200


def test_debug_page_shows_candidates(client):
    r = client.post("/game/new", follow_redirects=True)
    gid = r.url.path.split("/")[2]
    dbg = client.get(f"/debug/{gid}")
    assert dbg.status_code == 200
    # shows at least one candidate id from the fixture
    assert any(name in dbg.text for name in ["アクターA", "シンガーB", "悟空", "セーラーD"])
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run --no-sync pytest akinator/tests/test_api.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.main'`.

- [ ] **Step 3a: Write the templates**

`akinator/app/templates/base.html`:

```html
<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>アキネーター</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 640px; margin: 2rem auto;
           padding: 0 1rem; color: #1a1a2e; background: #f4f4f8; }
    h1 { color: #4a2c8f; }
    .btn { display: inline-block; padding: .6rem 1.2rem; margin: .25rem;
           border: 0; border-radius: 8px; background: #6b46c1; color: #fff;
           font-size: 1rem; cursor: pointer; text-decoration: none; }
    .btn.secondary { background: #9f7aea; }
    .card { background: #fff; border-radius: 12px; padding: 1.5rem; margin: 1rem 0;
            box-shadow: 0 2px 8px rgba(0,0,0,.08); }
    img.portrait { max-width: 200px; border-radius: 8px; }
    table { border-collapse: collapse; width: 100%; }
    td, th { border: 1px solid #ddd; padding: .35rem .6rem; text-align: left; font-size: .9rem; }
    code { background: #eee; padding: .1rem .3rem; border-radius: 4px; }
  </style>
</head>
<body>
  {% block body %}{% endblock %}
</body>
</html>
```

`akinator/app/templates/start.html`:

```html
{% extends "base.html" %}
{% block body %}
<h1>アキネーター</h1>
<div class="card">
  <p>誰か有名人・キャラクターを思い浮かべてください。質問で当ててみせます。</p>
  <form action="/game/new" method="post">
    <button class="btn" type="submit">ゲーム開始</button>
  </form>
</div>
{% endblock %}
```

`akinator/app/templates/question.html`:

```html
{% extends "base.html" %}
{% block body %}
<h1>質問 {{ asked_count + 1 }}</h1>
<div class="card">
  <p style="font-size:1.3rem;">{{ question.text }}</p>
  <form action="/game/{{ game_id }}/answer" method="post">
    <button class="btn" name="answer" value="yes">はい</button>
    <button class="btn" name="answer" value="no">いいえ</button>
    <button class="btn secondary" name="answer" value="probably_yes">たぶんはい</button>
    <button class="btn secondary" name="answer" value="probably_no">たぶんいいえ</button>
    <button class="btn secondary" name="answer" value="unknown">わからない</button>
  </form>
</div>
<p><a href="/debug/{{ game_id }}">デバッグ表示</a></p>
{% endblock %}
```

`akinator/app/templates/guess.html`:

```html
{% extends "base.html" %}
{% block body %}
<h1>あなたが考えているのは…</h1>
<div class="card">
  {% if entity.image_url %}<img class="portrait" src="{{ entity.image_url }}" alt="">{% endif %}
  <h2>{{ entity.name }}</h2>
  <p>{{ entity.description }}</p>
  <p>確信度: {{ '%.0f' % (posterior * 100) }}%</p>
  <form action="/game/{{ game_id }}/result" method="post" style="display:inline">
    <button class="btn" name="correct" value="1">正解！</button>
  </form>
  <a class="btn secondary" href="/game/{{ game_id }}/wrong">はずれ</a>
</div>
<p><a href="/debug/{{ game_id }}">デバッグ表示</a></p>
{% endblock %}
```

`akinator/app/templates/wrong.html`:

```html
{% extends "base.html" %}
{% block body %}
<h1>残念！正解を教えてください</h1>
<div class="card">
  <form action="/game/{{ game_id }}/wrong" method="post">
    <input type="text" name="correct_entity" placeholder="正解の人物・キャラ名"
           style="padding:.5rem; width:70%;" required>
    <button class="btn" type="submit">送信</button>
  </form>
</div>
{% endblock %}
```

`akinator/app/templates/debug.html`:

```html
{% extends "base.html" %}
{% block body %}
<h1>デバッグ</h1>
<div class="card">
  <h3>上位候補</h3>
  <table>
    <tr><th>entity</th><th>posterior</th><th>log_score</th></tr>
    {% for row in candidates %}
    <tr><td>{{ row.name }} <code>{{ row.id }}</code></td>
        <td>{{ '%.4f' % row.posterior }}</td><td>{{ '%.3f' % row.log_score }}</td></tr>
    {% endfor %}
  </table>
  <h3>質問履歴</h3>
  <ul>{% for h in history %}<li>{{ h.text }} → <b>{{ h.answer }}</b></li>{% endfor %}</ul>
  <h3>次の質問候補（選定理由: 分割が最も均等）</h3>
  {% if next_question %}
    <p>選択: <b>{{ next_question.text }}</b>（split={{ '%.3f' % next_split }}）</p>
  {% else %}<p>質問は出尽くしました。</p>{% endif %}
  <h3>上位候補の元データ</h3>
  {% for row in candidates %}
    <p><code>{{ row.id }}</code> {{ row.features }}</p>
  {% endfor %}
</div>
<p><a href="/game/{{ game_id }}">ゲームに戻る</a></p>
{% endblock %}
```

- [ ] **Step 3b: Write `akinator/app/main.py`**

```python
"""FastAPI web layer. Thin glue: load services, keep in-memory session states,
render Jinja2 templates, persist history to SQLite."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app import config, db
from app.inference.question_selection import split_score
from app.inference.scoring import posteriors
from app.models import Answer
from app.services.entity_service import EntityService
from app.services.game_service import GameService, GameState

app = FastAPI(title="akinator")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

ENTITY_SERVICE = EntityService.from_disk()
GAME_SERVICE = GameService(ENTITY_SERVICE)
SESSIONS: dict[int, GameState] = {}


@app.on_event("startup")
def _startup() -> None:
    db.init_db(config.DB_PATH)


@app.get("/", response_class=HTMLResponse)
def start(request: Request):
    return templates.TemplateResponse("start.html", {"request": request})


@app.post("/game/new")
def new_game():
    gid = db.create_game(config.DB_PATH)
    SESSIONS[gid] = GAME_SERVICE.new_game()
    return RedirectResponse(f"/game/{gid}", status_code=303)


@app.get("/game/{gid}", response_class=HTMLResponse)
def game(request: Request, gid: int):
    state = SESSIONS.get(gid)
    if state is None:
        return RedirectResponse("/", status_code=303)
    if GAME_SERVICE.should_guess(state):
        return RedirectResponse(f"/game/{gid}/guess", status_code=303)
    q = GAME_SERVICE.next_question(state)
    if q is None:
        return RedirectResponse(f"/game/{gid}/guess", status_code=303)
    return templates.TemplateResponse(
        "question.html",
        {"request": request, "game_id": gid, "question": q,
         "asked_count": len(state.asked_ids)},
    )


@app.post("/game/{gid}/answer")
def answer(gid: int, answer: str = Form(...)):
    state = SESSIONS.get(gid)
    if state is None:
        return RedirectResponse("/", status_code=303)
    q = GAME_SERVICE.next_question(state)
    if q is not None:
        GAME_SERVICE.record_answer(state, q, Answer(answer))
        db.save_answer(config.DB_PATH, gid, q.id, answer, len(state.asked_ids))
    return RedirectResponse(f"/game/{gid}", status_code=303)


@app.get("/game/{gid}/guess", response_class=HTMLResponse)
def guess(request: Request, gid: int):
    state = SESSIONS.get(gid)
    if state is None:
        return RedirectResponse("/", status_code=303)
    entity, posterior = GAME_SERVICE.best_guess(state)
    return templates.TemplateResponse(
        "guess.html",
        {"request": request, "game_id": gid, "entity": entity, "posterior": posterior},
    )


@app.post("/game/{gid}/result")
def result(gid: int, correct: str = Form(...)):
    state = SESSIONS.get(gid)
    if state is not None:
        entity, _ = GAME_SERVICE.best_guess(state)
        db.finish_game(config.DB_PATH, gid, entity.id, was_correct=(correct == "1"))
    return RedirectResponse("/", status_code=303)


@app.get("/game/{gid}/wrong", response_class=HTMLResponse)
def wrong_form(request: Request, gid: int):
    return templates.TemplateResponse("wrong.html", {"request": request, "game_id": gid})


@app.post("/game/{gid}/wrong")
def wrong_submit(gid: int, correct_entity: str = Form(...)):
    state = SESSIONS.get(gid)
    if state is not None:
        entity, _ = GAME_SERVICE.best_guess(state)
        db.finish_game(config.DB_PATH, gid, entity.id, was_correct=False)
    db.save_correction(config.DB_PATH, gid, correct_entity)
    return RedirectResponse("/", status_code=303)


@app.get("/debug/{gid}", response_class=HTMLResponse)
def debug(request: Request, gid: int):
    state = SESSIONS.get(gid)
    if state is None:
        return RedirectResponse("/", status_code=303)
    post = posteriors(state.log_scores)
    ranked = sorted(post.items(), key=lambda kv: kv[1], reverse=True)[:8]
    candidates = []
    for eid, p in ranked:
        e = ENTITY_SERVICE.get_entity(eid)
        candidates.append({"id": eid, "name": e.name, "posterior": p,
                           "log_score": state.log_scores[eid], "features": e.features})
    qmap = {q.id: q for q in ENTITY_SERVICE.questions}
    history = [{"text": qmap[qid].text if qid in qmap else qid, "answer": ans}
               for qid, ans in state.history]
    nq = GAME_SERVICE.next_question(state)
    next_split = (split_score(nq, ENTITY_SERVICE.entities, post) if nq else 0.0)
    return templates.TemplateResponse(
        "debug.html",
        {"request": request, "game_id": gid, "candidates": candidates,
         "history": history, "next_question": nq, "next_split": next_split},
    )
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run --no-sync pytest akinator/tests/test_api.py -v`
Expected: 3 passed. If the redirect-target parsing in `test_full_game_flow_to_guess` is brittle, the test already tolerates either reaching a guess or exhausting questions; keep assertions on status codes.

- [ ] **Step 5: Commit**

```bash
git add akinator/app/main.py akinator/app/templates
git add akinator/tests/test_api.py
git commit -m "feat(akinator): FastAPI web layer + Jinja2 screens + debug page"
```

---

## Task 15: Full workspace test run + manual smoke + docs

**Files:**
- Create: `akinator/CLAUDE.md`
- Modify: `akinator/README.md` (if commands changed)

- [ ] **Step 1: Run the akinator suite**

Run: `uv run --no-sync pytest akinator/tests -v`
Expected: all tests pass (≈ 30+). Quote the summary line.

- [ ] **Step 2: Run the WHOLE workspace suite (Definition of Done: full suite, not just new)**

Run: `cd ~/projects && uv run --no-sync pytest -q 2>&1 | tail -15`
Expected: no new failures introduced by akinator. Note any pre-existing failures in unrelated members separately.

- [ ] **Step 3: Manual smoke through the real entry point**

Run (background): `uv run --no-sync uvicorn app.main:app --app-dir akinator --port 8100 &`
Then:
```bash
sleep 2
curl -s localhost:8100/ | grep -o 'アキネーター' | head -1
gid=$(curl -s -i -X POST localhost:8100/game/new | grep -i location | grep -o '[0-9]\+')
curl -s "localhost:8100/game/$gid" | grep -o 'btn" name="answer"' | head -1
curl -s -X POST "localhost:8100/game/$gid/answer" -d "answer=yes" -i | grep -i 'HTTP\|location' | head -2
curl -s "localhost:8100/debug/$gid" | grep -o 'デバッグ' | head -1
```
Expected: start page contains アキネーター; a game id is issued; answering redirects (303); debug page renders. Kill the server after.

- [ ] **Step 4: Write `akinator/CLAUDE.md`**

```markdown
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

## Regenerate data (processed/ is committed; raw/ is gitignored)

```bash
uv run --no-sync python akinator/scripts/fetch_wikidata_entities.py --refresh
uv run --no-sync python akinator/scripts/build_questions.py
```

## Conventions

- New feature key → add to `normalize.py` (QID map), `question_gen.py`
  (`_*_FEATURES` set + label/template), done. Don't hand-write questions.
- Scoring constants live only in `scoring.py` (`STRONG`, `WEAK_MISSING`).
- Game history + wrong-answer corrections persist to SQLite
  (`corrections` table = future learning data; not yet consumed).
```

- [ ] **Step 5: Commit**

```bash
git add akinator/CLAUDE.md akinator/README.md
git commit -m "docs(akinator): CLAUDE.md guide + smoke-tested MVP"
```

---

## Self-Review

**Spec coverage:**
- 4-layer separation → Tasks 7-9 (data), 3-6 (inference), 11-12 (services), 14 (web). ✓
- Real+fictional ~400 from Wikidata → Task 10 fetch (LIMIT 200+200). ✓
- Attribute list (name/aliases/description/instance_of/occupation/gender/country/birth/death/notable_work/creator/fictional_universe/species/image) → normalize.py maps the discriminative subset; extra keys are additive (documented in CLAUDE.md). ✓
- Probabilistic updater, not fixed tree → Tasks 4-5, 12. ✓
- Question auto-generation (not hand-written list) → Task 8. ✓
- 5 answer types yes/no/probably_*/unknown → Answer enum (Task 2) + scoring (Task 4). ✓
- Missing=neutral+soft penalty → Task 4 `WEAK_MISSING`. ✓
- Split-based selection, swap-in for entropy → Task 6. ✓
- 4 gameplay screens + debug → Task 14 templates. ✓
- SQLite games/answers/corrections → Task 13. ✓
- WDQS politeness (UA, sleep, LIMIT, cache, --refresh) → Task 10. ✓
- processed committed / raw ignored → Task 1 .gitignore + Task 10 `git add -f`. ✓
- 7 required tests → Tasks 7,9,8,4,12,6,12 (normalize, entities gen, questions gen, score change, asked-not-reused, split-preferred, unknown-safe). ✓

**Placeholder scan:** No TBD/TODO; every code step has full code. ✓

**Type consistency:** `Answer`, `Entity`, `Question`, `MatchResult`, `GameState`,
`expected_match`, `update_log_score`, `posteriors`, `top_candidates`,
`split_score`, `select_question`, `EntityService`, `GameService` — names used
identically across tasks. `match_type` strings `equals|list_contains|numeric`
consistent between models, normalize, question_gen, scoring. ✓

**Known soft spot:** `test_full_game_flow_to_guess` (Task 14) parses redirect
targets; assertions are written to tolerate either reaching a guess or running
out of questions, so it won't flake on the 4-entity fixture.
