# Task5 統計部分の実装記録

2026-10-09。対象 worktree: `/home/kazumasa/worktrees/johnhull-research-roadmap`。

統計 source と独立参照テストを実装した。最終 scoped 検証は **42 passed, 186 deselected**、ruff check / format PASS。これは統計部分の source 検証であり、Task5 全体、正式 pilot、numerical accuracy、main、phase acceptance の完了を意味しない。

## 所有した変更

- `johnhull/hullkit/src/hullkit/_dynamic_hedging_statistics.py`: Torch-free private module。bootstrap indices 作成、個票 risk summary、paired score/保存済み bootstrap、全3initの IUT 判定。
- `johnhull/hullkit/tests/test_dynamic_hedging_statistics.py`: 手計算の block score / 全8通りの seed 層別列挙、NumPy 個票 moments、random baseline 閾値反例、厳密境界、個票 ES、元分母の poison、RNG 非変更、保存済み replay、全init IUT、overflow unknown。
- この ignored report。

共有 docs、MODEL_INDEX、public API、`__init__`、依存、Git は変更していない。MODEL_INDEX 配線は親担当。未知の `xaa` を操作していない。

## 参照した正本

- `johnhull/AGENTS.md`
- `johnhull/research/RB-F04/dynamic_hedging/DESIGN.md` §§8–13
- `johnhull/docs/superpowers/plans/2026-10-09-dynamic-cross-model-hedging.md` Task5
- TDD / writing-good-tests と verification-before-completion skill

## TDD と最終検証

先に38件のテストを書き、以下で **38 failed in 1.01s** を確認した。全件が `dynamic statistics is not implemented` という明示的 assertion による RED。import typo や collection error ではない。

```powershell
wsl -d Ubuntu -- env PYTHONPATH=/home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/hullkit/src /home/kazumasa/projects/.venv/bin/python -m pytest -q --confcutdir=/home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/hullkit /home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/hullkit/tests/test_dynamic_hedging_statistics.py
```

最初の GREEN 候補は37 passed / 1 failed。absolute 境界 fixture の浮動小数点 subtraction が厳密な `-.001` を表していなかったので、参照 NumPy square と小さい `.002` fixture で正確な境界を作った。判定への tolerance は追加していない。その後38 passed。

finite 個票でも squared-score 分散/SE が overflow する反例を追加し、1 failed / 39 passed の RED から、primary 判定を unknown とする修正を確認した。最後に finite `1e154` 個票の descriptive mean が warning を漏らす RED（1 failed / 1 passed / 39 deselected）を確認し、overflow 値を NaN、descriptive arithmetic status を unknown に保持する修正を行った。warning 抑制によって支持条件へ昇格させない。

最終 source の全 scoped 統計テストと該当 docstring guard:

```powershell
wsl -d Ubuntu -- env PYTHONPATH=/home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/hullkit/src /home/kazumasa/projects/.venv/bin/python -m pytest -q --confcutdir=/home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/hullkit /home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/hullkit/tests/test_dynamic_hedging_statistics.py /home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/hullkit/tests/test_docstrings.py -k dynamic_hedging_statistics
```

Exit 0: **42 passed, 186 deselected in 0.71s**（統計41件 + 当該module docstring1件）。

```powershell
wsl -d Ubuntu -- /home/kazumasa/projects/.venv/bin/ruff check /home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/hullkit/src/hullkit/_dynamic_hedging_statistics.py /home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/hullkit/tests/test_dynamic_hedging_statistics.py
wsl -d Ubuntu -- /home/kazumasa/projects/.venv/bin/ruff format --check /home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/hullkit/src/hullkit/_dynamic_hedging_statistics.py /home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/hullkit/tests/test_dynamic_hedging_statistics.py
```

両方 exit 0: `All checks passed!` / `2 files already formatted`。

WT の import 元を明示確認した:

```powershell
@'
import hullkit
from hullkit import _dynamic_hedging_statistics
print(hullkit.__file__)
print(_dynamic_hedging_statistics.__file__)
'@ | wsl -d Ubuntu -- env PYTHONPATH=/home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/hullkit/src /home/kazumasa/projects/.venv/bin/python -
```

Exit 0、実測値:

```text
/home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/hullkit/src/hullkit/__init__.py
/home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/hullkit/src/hullkit/_dynamic_hedging_statistics.py
```

親の指示通り全 suite / uv sync / numerical pilot は実行していない。

## 統合契約

### `make_bootstrap_indices(blocks_per_seed, *, seed, replicates=2000)`

- local `SeedSequence` / `Generator` のみ。global NumPy RNG 不変。
- `int16`、shape `(R, 3, B)`。各 seed の block ID を独立に B 個 resample。B は1..32768。
- caller が一度作成・保存し、全method/G/initで同じ indices を共用する。保存済み checker は生成関数を呼ばない。

### `risk_summary(losses, *, block_size=64)`

- 入力は `L = -discounted net P&L`、shape `(3, N)`、通貨単位。元個票を `losses`、square を `squared_losses` として保存。
- `original_count=3N`。`counts.original_per_seed` / `finite_per_seed` / `unknown_per_seed` と total を保持。経路の非有限値を drop しない。
- `mean_loss` / `mse` は3seed平均の等重み平均、`rmse=sqrt(mse)`。`variance` は pooled 個票 sample variance（ddof=1）。
- `mean_loss_se` / `mse_se` は seed 内 per-path IID sample variance `s_j²`（ddof=1）から `sqrt(sum_j(s_j²/N))/3`。比較用 pooled IID SE は `pooled_mean_loss_se` / `pooled_mse_se` で明示。`per_seed` に各平均・分散を保持。
- `es95` は元の individual loss 全3Nの最大 `ceil(0.05*3N)` 個の平均。tie でも tail count を増やさない。`es95_tail_count` / `es95_original_count` を保存し `es95_ci_status=not_evaluated`。blockmean ES ではない。
- N が block_size で割り切れる場合だけ `block_means.loss` / `squared_loss` を保存。非整数block末尾を切り捨てない。`block_status` は分割可能性を表し、数値の適格性は primary `status` で確認する。
- 非有限original pathはprimary summaryをunknownにする。`finite_only` は pooled 有限個票による `descriptive_only`。ここから支持判定しない。descriptive算術overflowは値NaN / `arithmetic_status=unknown`。

### `paired_statistics(baseline_loss, candidate_loss, indices, *, block_size=64, alpha=.05/8, numerical_envelope=None)`

- 同じ元seed/pathのL配列 `(3,N)` が必須。Nはblock_sizeで割り切れる必要がある。整数indicesのshape/rangeを数学的に検証し、入力indicesをコピー保存。
- `scores.absolute = L_C² - L_B²`、`scores.relative = L_C² - .95 L_B²`。`means` / `iid_se` / `pooled_iid_se` / `per_seed` に個票統計を保存。
- `block_scores` / `bootstrap_scores` / `bootstrap_indices` を保持。各replicateは seed内block平均→3seed等重み平均。`bootstrap_mean_loss.baseline` / `candidate` も同じindicesから再計算する。
- `upper_bounds` は `1-alpha` one-sided upper percentile、NumPy `method=linear`。デフォルト `.05/8` を一度適用し、init数/condition数で割らない。nominal approximate block-bootstrap CI であり厳密有限標本coverageを主張しない。
- envelope input は `{'absolute': scalar, 'relative': scalar}`、非負・通貨²。欠落/None/nonfinite→unknown、有限negative/non-scalar→ValueError。0はcallerが実測/理論zeroを既に確認した場合のみ渡し、統計関数はzeroの意味を創作しない。
- `conditions.absolute` は `U_d+u_d < -.001`、`conditions.relative` は `U_r+u_r < 0`。両方Trueのとき `status=supported` / `risk_improvement_supported=True`。有限不支持は `not_supported` / False、未知経路・未知envelope・非有限uncertaintyは `unknown` / None。
- 元raw score/countsはunknownでも同じshape/分母。`finite_only.means` は descriptive のみ。
- training completion、Q drift、数値pilot精度/独立envelopeの資格はcaller責任。これらがunknownならfamilyへ渡す前に該当initをunknownとする。

### `family_assessment(initialization_results)`

- mapping keyは `11,29,47` のintまたはdecimal stringでexact roster。他seed/欠落/重複はValueError。
- 各resultの `status` と `conditions.absolute` / `relative` を検査する。全3initがsupportedかつ全6条件Trueで支持。
- failed/unknown/missing conditionが一つでもあればunknownを優先。未知がなく有限not_supported/false conditionがあればnot_supported。
- best seed/平均seedを採用せず、alphaを再分割しない。返すinit status/conditions/ID rosterも保存可能。

## 固定した source 指紋（provenanceのみ）

```text
d07d4d1524a005d5b9ebe765922748aadab2175ace98ff12c941c1a38e8497ce  johnhull/hullkit/src/hullkit/_dynamic_hedging_statistics.py
f5b433cbf55d24b687927fd72e982832500cfebc166cd8015f63f1ba43614f1d  johnhull/hullkit/tests/test_dynamic_hedging_statistics.py
```

実測command:

```powershell
wsl -d Ubuntu -- sha256sum /home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/hullkit/src/hullkit/_dynamic_hedging_statistics.py /home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/hullkit/tests/test_dynamic_hedging_statistics.py
```

## 未完了・material decisions

統計部分に未決定の実装選択はない。独立code/math reviewとrunnerのMODEL_INDEX配線は親で実施する。正式pilotでtest N、測定済みnumerical envelopes、training/Q適格性、近似CIの研究上の限界を保存する作業が残る。bootstrapの数学単体検証からその精度達成を推定しない。
