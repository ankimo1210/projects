# STRUCTURAL REPRODUCTION ON SYNTHETIC DATA

## 結論

5研究対象、12 implementation profiles の provenance、合成 fixture、architecture、主要
lifecycle を実装し、CPU smoke を完走した。これは論文の実データ数値結果の再現ではない。
FI-2010/LOBSTER 上の paper-reported accuracy/F1 は試行していない。

## 検証サマリー

| check | result |
|---|---|
| source verification | 5 paper PDFs + 2 author repositories、取得済み全 hash が一致 |
| profile validation | 12/12 valid。`B_PAPER_EXACT` に unresolved material field なし |
| tests | 33 passed |
| lint | Ruff passed |
| CPU smoke matrix | 12/12 profiles completed |
| public-data numerical benchmark | not attempted |

PyTorch の even-kernel `padding='same'` に関する性能 warning が1件出るが、期待する
paper-profile shape `[B,16,100,*]` はテスト済みで、correctness failure ではない。

## profile 別 status

| target | profile class | structural result |
|---|---|---|
| Queue imbalance paper / chronological audit | B / D | strict interval causal alignment、random/chronological split、logistic/local logistic pass |
| DeepLOB paper | B | 16/32 channels、same temporal padding、LSTM64、3-class output pass |
| DeepLOB TF2 author / dropout audit | A target / D | analytic shapes and displayed count 142,435 pass; native TF not run |
| DeepLOB PyTorch author | A target | valid-time shape 100→82、displayed count 143,907、deterministic forward pass |
| TLOB paper / author / corrected audit | C / A / D | alternating unequal axes、no mask/dropout、BiN and EMA lifecycle pass |
| MLPLOB paper / author | C / A | alternating MLP axes、BiN、runtime count pass |
| Sirignano–Cont | C | 3-layer LSTM、state-detach seam、asset-specific/pooled/unseen synthetic paths pass |

`A_AUTHOR_CODE_EXACT` は pinned source behavior の target 名である。各 smoke 自体は合成
clean-room execution で、native/reference side-by-side を実行していないことを warning に
記録する。TLOB のテストスイートでは、MIT source 取得時に別途 direct golden comparison
を行う。

## golden architecture results

| model/profile | parameter count | evidence status |
|---|---:|---|
| DeepLOB paper clean port | 60,947 | paper diagram-derived structural count |
| DeepLOB TF2 notebook | 142,435 | notebook displayed count matched analytically |
| DeepLOB PyTorch notebook | 143,907 | notebook displayed count matched |
| TLOB repository FI-2010 runtime | 2,656,724 | pinned source + clean port count matched |
| MLPLOB repository FI-2010 runtime | 6,327,908 | pinned source + clean port count matched |

TLOB static config の hidden 40 だけを使うと `1,140,342` / `3,016,782` だが、FI-2010
entrypoint は hidden を 144 に上書きする。paper Table2 の概数 `1e7` / `6.3e7` は
どちらとも一致せず、definition/configuration は未解決のまま分離した。

## 合成 protocol の観測値

Queue fixture（12日、1,200 observations、paper random 80/20）では次を得た。

| forecast | ROC-AUC | mean squared residual |
|---|---:|---:|
| parametric logistic | 0.8585 | 0.1455 |
| local logistic, bandwidth 0.65 | 0.8585 | 0.1452 |
| null probability 0.5 | 0.5000 | 0.2500 |

推定 queue-imbalance slope は `3.4295`、全 sample は target move 前の open interval 内、
post-move features は0件。これは generator の latent mapping と配線を検証する sanity
result であり、Gould–Bonart の empirical result ではない。

Universal fixture の scaled audit では pooled linear unseen-asset accuracy `0.9117`、
scaled pooled LSTM unseen-asset accuracy `0.7807`。LSTM smoke は history20、hidden8、
15 epochs、Adam `.02` の明示的 audit configuration であり、Sirignano–Cont paper の
数値比較ではない。mapping removal と shuffled-label sanity もテスト済み。

## 直接 golden comparison

TLOB MIT source `f1c0af4...` がローカルにある場合、同一 state/input で以下を比較する。

- BiN output
- model-parameter gradients
- SGD one-step update
- 小型 TLOB/MLPLOB final logits
- FI-2010 runtime hidden144 の source parameter counts

全比較は pass。pinned BiN の in-place temporal-std guard は input tensor に gradient を
要求した場合に autograd error を起こすため、reference behavior として記録し、safe
behavior は `tlob_corrected_bin_audit` に隔離した。

## 残存リスク

- DeepLOB source commit は license absent。substantial source は同梱しない。
- DeepLOB exact TF/PyTorch framework versions と runtime-default Adam epsilon は未固定。
- TensorFlow native execution、real FI-2010 numerical runs、proprietary LOBSTER runs は未実行。
- Sirignano–Cont の主要 lifecycle/input details と TLOB paper parameter definition は未解決。
- Phase 0 初期に親 Git object の一時的な読み取り失敗があったが、agent は修復しておらず、
  最終 `git status` / `git cat-file` は成功した。初期 artifact には当時の error が残り得る。

詳細な根拠と次の作業は `docs/evidence_ledger.md`、`docs/discrepancy_matrix.md`、
`docs/unresolved_assumptions.md`、`HANDOFF.md` を参照。
