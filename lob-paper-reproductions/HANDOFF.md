# Handoff

## 現在地

本プロジェクトは、実データの数値再現を行わない structural-reproduction MVP まで実装済み。
既定の CI/smoke は決定論的な合成データだけを使う。`outputs/`、取得 PDF、取得 repository、
raw data は Git 管理外である。

| profile | fidelity | 実装・検証状態 |
|---|---|---|
| `gould_bonart_2015_paper` | `B_PAPER_EXACT` | open-interval sampling、random 80/20、parametric/local logistic、ROC-AUC/MSR |
| `gould_bonart_2015_chronological_audit` | `D_MODERNIZED_AUDIT` | chronological split を exact 出力と分離 |
| `deeplob_ieee_2019` | `B_PAPER_EXACT` | paper 16/32-channel architecture、shape/count trace |
| `deeplob_author_tf2_ff14d7c` | `A_AUTHOR_CODE_EXACT` target | analytic TF2 shape/count spec。native TensorFlow は未実行 |
| `deeplob_author_tf2_corrected_dropout_audit` | `D_MODERNIZED_AUDIT` | forced-training dropout だけを訂正 |
| `deeplob_author_pytorch_ff14d7c` | `A_AUTHOR_CODE_EXACT` target | independent PyTorch clean port、forward/count trace |
| `tlob_paper_arxiv_2502_15757` | `C_PAPER_CONSTRAINED` | paper settings + explicit BiN/hidden assumptions |
| `tlob_author_repo_f1c0af4` | `A_AUTHOR_CODE_EXACT` | author forward/BiN/lifecycle semantics、source golden tests |
| `tlob_corrected_bin_audit` | `D_MODERNIZED_AUDIT` | safe BiN + trainable order-type embedding |
| `mlplob_paper_arxiv_2502_15757` | `C_PAPER_CONSTRAINED` | paper lr/sequence settings + assumptions |
| `mlplob_author_repo_f1c0af4` | `A_AUTHOR_CODE_EXACT` | author forward/BiN/lifecycle semantics |
| `sirignano_cont_2019_paper_constrained` | `C_PAPER_CONSTRAINED` | disclosed 3-layer LSTM + pooled/unseen-asset synthetic protocol |

## 固定した一次資料

- Gould & Bonart: arXiv `1512.03492v1`
- DeepLOB: arXiv `1808.03668v6` / IEEE TSP 2019, author repository
  `ff14d7c2fd38bdfc143389786993d0f0236d4eb8`
- Sirignano & Cont: arXiv `1803.06917v1`
- TLOB: arXiv `2502.15757v3`, author repository
  `f1c0af4d81067978914361766db0457a7d8b6a46`
- FI-2010: arXiv `1705.03233v5`

PDF、repository archive、使用 evidence files の SHA-256 は `manifests/sources/` に固定。
`lob-repro sources fetch` は full-commit codeload archive と evidence-file hash の両方を
検証する。

## 検証結果

- pytest: 41 passed。TLOB MIT source が取得済みの場合、pinned source と clean port の
  BiN output、parameter gradients、SGD 1-step update、小型 TLOB/MLPLOB logits を比較。
- Ruff: pass。
- provenance: 12 profiles valid、取得済み 5 PDF + 2 repositories は hash match。
- CPU smoke matrix: 12 profiles pass。
- golden counts: DeepLOB paper clean port `60,947`、TF2 `142,435`、PyTorch `143,907`、
  TLOB FI-2010 runtime `2,656,724`、MLPLOB FI-2010 runtime `6,327,908`。

再実行:

```bash
cd /home/kazumasa/projects
uv sync --package lob-paper-reproductions --group dev
make -C lob-paper-reproductions verify-provenance
make -C lob-paper-reproductions test
make -C lob-paper-reproductions lint
uv run --no-sync --package lob-paper-reproductions \
  python lob-paper-reproductions/scripts/run_reproduction_matrix.py
```

## 確認済みの重要な paper/code 差分

- DeepLOB paper は conv/Inception `16/32`、notebooks は `32/64`。PyTorch notebook だけが
  valid temporal conv、BatchNorm、block-2 Tanh、softmax後の `CrossEntropyLoss` を使う。
- TF2 notebook は dropout 0.2 を `training=True` で常時有効化する。
- DeepLOB paper は Adam lr `.01`, eps `1`, batch 32。TF2/PyTorch は lr `1e-4`,
  batch 128/64。
- TLOB paper v3 Table10 の MLPLOB sequence は `384`。prompt seed の `128` は誤り。
  実在する paper/repository conflict は MLPLOB lr `.003` vs `.0003`。
- TLOB static config は hidden 40 だが、`main.py` が FI-2010 で 144 に上書きする。
  author-exact profile と golden count は runtime 144 を使う。
- TLOB paper Table2 の概数 `1e7` / `6.3e7` は、runtime author counts
  `2,656,724` / `6,327,908` と一致しない。
- BiN source は temporal zero-std だけを guard し、feature zero-std は未処理。負 mixture
  parameter を forward 中に置換し、in-place std guard は input-gradient autograd を壊す。
- LOBSTER order-type embedding は `.detach()` され、author profile では gradient がない。
- TLOB repository label は `mean(abs(change))/2` threshold、up/stable/down=`0/1/2`。
- TLOB/MLPLOB の EMA は `torch_ema` デフォルト `use_num_updates=True` により実効 decay が
  `min(.999,(1+n)/(10+n))` でウォームアップする。lifecycle port はこのスケジュールを再現し、
  profile は `training.ema_use_num_updates` として固定する。

詳細は `docs/discrepancy_matrix.md` と各 paper/code comparison document を参照。

## 未解決・制約

- DeepLOB commit に license file がないため substantial source は vendor しない。
- DeepLOB notebooks は exact framework version を固定していない。TF2/PyTorch の runtime
  default Adam epsilon も完全には固定できない。TF2 native package は既定環境に未導入。
- Sirignano–Cont は complete input vector、transform、optimizer schedule、regularization、
  batching、state carry/reset、TBPTT、initialization、stopping、async update semantics が未開示。
- TLOB/MLPLOB paper の hidden dimension、exact BiN edge behavior、Table2 parameter-count
  definition は未解決。
- optional download が固定するのは DeepLOB decimal-precision FI-2010 archive。TLOB
  author profile が使う ZScore variant は別途、利用条件を満たす正規取得と hash 固定が必要。
- 親 workspace の Git object `148d090affd2e106a2720d79fd1fca69896c57be` は Phase 0
  開始時だけ読み取りに失敗した。本作業では修復していないが、最終時点の `git status`
  と `git cat-file` は成功。初期 run の `git_state.json` は当時の error を保持し得る。

## optional FI-2010 の次手

まず source/terms を表示し、同意後に decimal-precision archive を取得する。

```bash
uv run --no-sync --package lob-paper-reproductions lob-repro data fetch-fi2010
uv run --no-sync --package lob-paper-reproductions lob-repro data fetch-fi2010 --accept-terms
uv run --no-sync --package lob-paper-reproductions lob-repro data verify-fi2010
uv run --no-sync --package lob-paper-reproductions lob-repro data audit-fi2010
```

`audit-fi2010` は取得済み archive の shape・horizon別ラベル分布・author-contiguity
windowing を構造監査する（学習・評価は行わず、数値再現は主張しない）。

TLOB ZScore numerical run を追加する場合は、DecPre を代用せず、ZScore CF7/8/9 の正当な
source、terms、filenames、archive/file hashes を新しい dataset manifest に固定する。
その後、author code の 80/20 train/validation、contiguous-file windows、144 features、
horizon mapping、seed 1、torch 2.5.0+cu121 lifecycle を別 runner として実装する。strict
profiles 自体は変更しない。

## 数値再現を主張する前の必須条件

1. exact dataset variant と redistribution/利用条件を確認し、raw files を hash 固定する。
2. paper/author profile の split、label formula、horizon、feature set、metric を完全一致させる。
3. 未固定 framework/default を解決するか、deviation として明示する。
4. source 規定 seed、未規定時は複数 seed、hardware/runtime、confidence interval を記録する。
5. paper-reported table と同じ averaging/class order で評価し、比較 guard を通す。
6. synthetic output を根拠にしない。現状は numerical benchmark not attempted である。
