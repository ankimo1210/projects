# Task 4 金融リスク実装報告

2026-10-09。Task 4 の金融リスク担当。独立レビュー前。

## 変更と証拠

- `johnhull/hullkit/src/hullkit/_dynamic_hedging_risk.py`：private / NumPy-only。IFT positions、minimum-variance stock projection、Heston/local diffusion covariance、SD band と合法制約、原始 paired d/r scores。
- `johnhull/hullkit/tests/test_dynamic_hedging_risk.py`：21 ケース。非線形解析価格を独立 brentq で Q/S ごとに毎回再fit、3幅 central bumps、physical/logtheta 不変、手計算 IFT .4/.5、悪条件分母、Heston 相関/PSD/dt、local multiplier/rank 1、null 無取引、width 0、raw/legal holdings と拘束件数、原始ランダム baseline と NaN/元 N。
- 学習、公開 API、`__init__.py`、依存、索引、Git は担当範囲外。

TDD RED：実装作成前に 21 failed / 0.60s、全ケースが `dynamic hedge risk is not implemented` assertion。最初のコマンドに用いた `$PWD` は PowerShell→WSL 経由で意図した WT PYTHONPATH にならなかったため、実装後は明示絶対パスに変更した（RED 時点では両 checkout に対象実装なし）。

GREEN（明示 WT package を読み込む）：

```bash
cd /home/kazumasa/worktrees/johnhull-research-roadmap
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
PYTHONPATH=/home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/hullkit/src \
/home/kazumasa/projects/.venv/bin/python -m pytest -q --noconftest \
  johnhull/hullkit/tests/test_dynamic_hedging_risk.py
# 21 passed in 0.54s

/home/kazumasa/projects/.venv/bin/python -m ruff check \
  johnhull/hullkit/src/hullkit/_dynamic_hedging_risk.py \
  johnhull/hullkit/tests/test_dynamic_hedging_risk.py
# All checks passed!
/home/kazumasa/projects/.venv/bin/python -m ruff format --check \
  johnhull/hullkit/src/hullkit/_dynamic_hedging_risk.py \
  johnhull/hullkit/tests/test_dynamic_hedging_risk.py
# 2 files already formatted
```

全 suite は承認済み計画の最終 gate で root が1回実行する。今回の検証は指定 scoped のみ。

## Interface / shape

Task brief の5 signaturesを維持。

- `quote_positions`：入力を broadcast した shape。`stock`, `call`, `denominator`, `denominator_error`, `valid`, `status`。非finite/`|Ctheta| <= 3 deltaJ` は対象 position が NaN / unknown、原始分母と誤差は保持。
- `stock_only_target`：broadcast shape の raw target。Heston の `c_theta` は physical `C_v`（logstateで作った不変 positions を使っても、この引数は物理導関数）。unknown は NaN。制約なし。
- `price_covariance`：入力 shape + `(2,2)` の `covariance`、入力 shape の `rank`, `valid`, `status`。unknown rank は -1。Heston physical v/Cv、local frozen multiplier + base variance、year dt。local ridgeなし。
- `band_holdings`：holdings shape `(...,1)` または `(...,2)`、covariance の row shape と broadcast。`raw_target`, `raw_holdings`, `holdings`, `sd`, `constrained`, `constraint_counts`（row）, `constraint_count`（total）, `valid`, `status`。band 後の有限 raw holding のみ [-2,2] 合法制約を適用。unknown row は NaN、hold/zero fallbackなし。
- `improvement_scores`：同一非empty形の原始 paired squared losses。`d`, `r` と同じ配列の `absolute`, `relative` aliases、`original_count`, `valid_count`, `invalid_count`, 個票 `valid`, 集計 `status`, `d_mean`, `d_se`, `r_mean`, `r_se`。原始形/全 N を保持。nonfinite個票が一つでもあれば集計 NaN / unknown、singleton は SE/集計status unknown。

## 限界・次工程

- IFT の root 一意性、支持、state-scale qualification、教師共分散からの ratio uncertainty は caller が原始 fit/教師証拠で検証する。この関数の finite/denominator gate はそれらの認証ではない。
- covariance は連続 diffusion の局所近似。finite-step actual 市場 covariance、正式 pilot/main を検証したとは扱わない。
- band の有限 covariance は対称/PSD を検査。固有値の machine arithmetic tolerance は診断許容のみで、covariance の修復や ridge はしない。負 quadratic SD は unknown。
- paired IID SE は記述値。saved block-bootstrap/Bonferroni/IUT/numerical envelope/support 判定は Task 5 runner。
- 独立レビューと root による索引/文書・全suite gate が残る。commit は行っていない。
