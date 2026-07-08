# Titanic - Machine Learning from Disaster

Kaggle competition: predict `Survived` (0/1) for 418 test passengers.
Metric: accuracy.

## Layout

- `titanic/` — competition data (`train.csv`, `test.csv`, `gender_submission.csv`)
- `src/train.py` — ML baseline: engineered features (title, family size, ticket
  group, cabin flag) → 5-fold CV comparison of logistic regression / random
  forest / HistGradientBoosting → `submission.csv`
- `src/wcg.py` — v2: gender rule overridden by same-surname group evidence
  (women/boys) → `submission_wcg.csv`
- `src/wcg2.py` — v3/v4: gender rule + ticket/surname union-find groups +
  1st/2nd-class boy rule (+ v4 only: 3rd-class/Embarked-S demographic priors,
  since disproven — see below) → `submission_v3.csv` / `submission_v4.csv`
- `submission*.csv` are gitignored (repo-wide `*.csv` rule); regenerate via `uv run`

## Run

```bash
uv run python kaggle/titanic/src/train.py   # v1: ML models
uv run python kaggle/titanic/src/wcg.py     # v2: gender + surname groups
uv run python kaggle/titanic/src/wcg2.py    # v3 + v4: ticket-linked groups
```

## Approach & trial-and-error

Data facts that drove every decision: `Age` 20% missing, `Cabin` 77% missing
(kept only as a has/hasn't flag), no duplicate `PassengerId`s, one `Fare`
missing in test. Baseline "predict survival iff female" already scores 0.7868
train accuracy — any model has to beat that on genuinely unseen structure, not
just fit training noise.

**v1 — supervised ML (CV 0.8395, LB 0.75119).** Logistic regression / random
forest / HistGradientBoosting on engineered features, picked by 5-fold CV.
The best CV model (HistGB) scored **worse than the plain gender rule on the
public LB** (0.75119 vs 0.76555). With only 891 training rows, CV
systematically overstates generalization — the model was fitting
train-specific noise (e.g. fine `Fare` thresholds) that doesn't transfer.
**Lesson: on this dataset, CV rank order is not trustworthy for picking
between a flexible model and a simple rule.**

**v2 — gender rule + surname-group evidence (LB 0.80143, +16/-1 vs gender rule).**
Switched away from black-box ML entirely. Default to the gender rule; override
only where the *training data itself* gives direct evidence for a specific
family: if all labeled women/boys sharing a surname died, predict death for
the rest of that surname's women in test (and the mirror image for boys,
title "Master"). This is the well-known "women/children by family group"
pattern for Titanic. 17 flips vs. the gender rule, 16 confirmed correct on
LB — validates that group evidence generalizes far better than fitted models.

**v3 — ticket-linked groups + class-based boy rule (LB 0.80382, current best).**
Two refinements grounded in what the columns actually mean:
- `Ticket` is shared by travel companions regardless of surname (nannies,
  servants, relatives) — connected-components (union-find) over shared
  `Ticket` OR shared `(Surname, Pclass)` catches these, not just exact-surname
  matches. Rescued one case in test (a maid sharing a ticket with a family
  that fully perished) — confirmed correct on LB (+1 vs v2).
- `Master` (boy) survival is 12/12 in 1st/2nd class train — "women and
  children first" was fully honored there regardless of family fate, so it's
  applied as a class-level rule, not just group evidence.
- OOF 0.8418 (measured with group statistics computed from training folds
  only, so no label leakage into the fold-level accuracy estimate).

**v4 — demographic priors on top of v3 (LB 0.79665, DISPROVEN).** Added rules
for the segment gender+group evidence can't reach: 3rd-class, Embarked=S women
with no surviving group evidence, split by ticket-group size (solo travelers
41% survive in train, groups of 4+ only 8%). OOF looked good (0.8485), but on
LB this went 5/13 correct — worse than doing nothing. **The population-level
survival rate in train did not transfer to test** (test's actual rate for that
segment was ~62%, not ~41%). Confirms v1's lesson at a finer grain:
**demographic/statistical priors overfit small-sample training quirks; only
direct group-membership evidence (this specific family/ticket) generalizes.**
A guard was kept in the code regardless — group evidence must override any
demographic prior (e.g. the Dean family's infant boy survived in train, so the
prior "solo/small-group 3rd-class women mostly die" must not apply to his
mother) — this is now moot since v4's segment rules were dropped in the
adopted submission, but the precedence logic stays as a correctness guard.

**Explored and rejected (no LB test needed — OOF-only signal was already too
weak or noisy to risk a submission):**
- Ticket-number adjacency (linking still-unlabeled test passengers to a
  nearby-numbered, same-class/port train ticket as a weak proxy for "booked
  together"): OOF +0.11pt over 891 rows — indistinguishable from noise given
  v4's lesson that even +1.0pt OOF swung 5/13 wrong on LB.
- Any rule to flip adult (non-`Master`) males to "survives": even males in
  groups where every labeled woman/boy survived only reach 22.6% survival
  (n=84) — "women and children first" left no exploitable signal on the male
  side at any level of group evidence.

## Score progression (accuracy)

| version | CV / OOF | Public LB | vs. gender rule |
|---|---|---|---|
| gender rule (baseline) | 0.7868 (train) | 0.76555 | — |
| v1: HistGradientBoosting | 0.8395 (5-fold CV) | 0.75119 | worse |
| v2: + surname-group evidence | 0.8361 (OOF) | 0.80143 | +16 / -1 |
| v3: + ticket-linked groups + boy-class rule | 0.8418 (OOF) | **0.80382** | +17 / -1 |
| v4: + demographic priors (dropped) | 0.8485 (OOF) | 0.79665 | +18 / -13 |

**Current best: v3, `submission_v3.csv`, LB 0.80382.** Remaining errors
(~82/418) are dominated by adult male survivors and isolated female deaths
that group/family/class structure genuinely cannot predict from this data —
further gains would require either overfitting test-specific priors (v4
showed this loses) or looking up real passenger identities (not modeling).
