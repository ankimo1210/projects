# RB-F05 short-maturity learner cross review

2026-10-09。担当は読み取り専用レビュー。source/test/Gitの変更なし。

## 対象・結論

- `deep_hedge_price/src/deep_hedge_price/_short_maturity_dml.py`
- `deep_hedge_price/tests/test_short_maturity_dml.py`
- 正式spec §12、spec §6–8、正式plan Task3との照合。
- 価格・物理Delta/Gammaの式、train-only normalization、paired init/batch、通常の失敗・費用記録は整合。
- 環境状態の重要指摘2件、ambient no-gradへの堅牢性指摘1件。金融coreはレビューしていない。

## 指摘

### L1 [P2] CPU-only forkの外側でaccelerator RNG状態を変更する

source lines137–138。`torch.random.fork_rng(devices=[])`はCPU乱数のみ復元するが、`torch.manual_seed(seed)`はCUDA等のgeneratorもseedする。CPU float64の実験が既存accelerator generator又はlazy-seed状態を変更し得る。

再現: `torch.cuda.manual_seed_all`をmockでinstrumentし、通常の2update CPU DMLを実行。呼出1回、引数11。CPUのみで実行してもこの経路へ入る。実GPU状態の実測はしていない。

最小候補: CPU `torch.random.default_generator.manual_seed(seed)`のみに限定する。CPU乱数とthread countの復元テストを維持し、CUDA seed関数を禁止したCPU train regressionを追加する。

### L2 [P2] ambient非CPU deviceでAdam内部stateが非CPUに生成される

source lines140/177–180。モデル/入力を明示CPUにしても、Adam内部で新しく作るstate tensorの全てをambient default deviceから隔離していない。

再現: `with torch.device("meta"):` 内で通常2updates、batch4、budget30秒のDMLを実行。保存結果は `status="optimizer_error"`, `reason="Tensor.item() cannot be called on meta tensors"`, `updates=0`, `batch_attempts=1`。数学的に有効な同じデータは通常CPU環境で完了する。

既存test `test_cpu_model_ignores_an_ambient_non_cpu_default_device` は `teacher_s=40 > budget30` としているため、Adam.stepを一度も実行しない。重要な更新経路を検証していない。

最小候補: trainのモデル初期化・optimizer/stepを明示CPU device contextに置き、callerのambient contextを復元する。meta ambientで少なくとも1updateを完了し、全parameter/optimizer生成stateがCPUであることを検査する。

### L3 [P3] predictはambient no-gradの下でGreeksを計算できない

source lines238–245。入力の`requires_grad_(True)`だけでは、callerの`torch.no_grad()`を上書きできない。

再現: 完了済みFitに対して `with torch.no_grad(): predict(fit,x)` が `RuntimeError: element 0 of tensors does not require grad and does not have a grad_fn`。

最小候補: physical Greeksを算出する内部区間を`torch.enable_grad()`で囲み、callerのgrad modeを復元する。trainにも同じambient no-grad依存があるので、入口の契約を明記するか、学習内部でgradを有効にする。現在の通常main呼出がno-gradを使うという証拠はないため、L1/L2と区別してP3とした。

## 整合を確認した項目

- Smooth 3→32→32→1 tanh、train-only shift/scale付きunconstrained total C/K。intrinsic kinkやclipなし。
- Torchはraw Sから価格を微分するためphysical Delta/Gammaを直接返す。
- NumPyはlog-spot xの導関数を明示計算し、`Delta=C_x/S`, `Gamma=(C_xx-C_x)/S²` を適用。tanhの1/2階連鎖とfeature stdを含む。
- 保存weightsからのNumPy再生はRNG/optimizerなし。Torchとの2階導関数・3幅spot差分のテストが通る。
- Normalizationはtrain引数だけから作り、validation/testを受け取らない。価格scaleはC/K、Delta scaleはphysical DeltaのRMS。
- 同seed初期weights、別batch_seedの独立local NumPy generator。paired両方式のbatch順序は同じ。attempted batchと完了updateを別々に保存する。
- Optimizer例外時はattempt1/update0、nonfinite loss/gradient/parameter失敗は元Fitに残る。通常成功/optimizer失敗時はCPU RNG/threadを復元する。
- teacher_s + setup/validation/training/evaluation/thread restorationの実測範囲を保存。module import費用は明記して除外。
- 時間上限はupdate前チェックであり、最後のupdate/最終evaluationで超過し得る。指定max_updatesを達成した場合は`completed=True`でも`overrun_s>0`となる（1update/2秒、budget1秒で再現）。これは現docstring/planのoverrun保持と整合。研究採否では「更新数完了」と「予算内」を同じ意味として扱わないこと。

## 検証

```bash
cd /home/kazumasa/worktrees/johnhull-research-roadmap
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
PYTHONPATH=/home/kazumasa/worktrees/johnhull-research-roadmap/deep_hedge_price/src \
/home/kazumasa/projects/.venv/bin/python -m pytest -q \
deep_hedge_price/tests/test_short_maturity_dml.py
```

19 passed（1.62秒）。追加の読み取り専用instrumentはtiny4rows×2updatesのみ。正式6mainfits、pilot教師生成、全suiteは実行していない。

instrument出力:

```json
{"cuda_manual_seed_all_calls":1,"cuda_seed_argument":[11]}
{"predict_under_no_grad":"element 0 of tensors does not require grad and does not have a grad_fn"}
{"ambient_meta_full_updates":0,"status":"optimizer_error"}
{"status":"optimizer_error","reason":"Tensor.item() cannot be called on meta tensors","updates":0,"batch_attempts":1}
{"status":"completed","complete":true,"updates":1,"batch_attempts":1,"training_s":2.0,"budget_s":1.0,"overrun_s":1.0}
```

修正・TDD regressionはsource所有agent/rootが行う。レビュー自身はsourceを変更していない。
