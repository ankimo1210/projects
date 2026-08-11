# 2026-08-11 — B9 development tournament（outer前）

## 結論

M6で固定したSEC cohortのうち、**development partitionだけ**で最初のcandidate runを完了した。
locked outer (413)行は数えただけで、outer文書・特徴量・予測値は読み込んでいない。実行した候補の範囲では
採用gateを満たすnomineeはなく、結果は `no_model_selected`（implemented-family interim）である。
これはouterへ進む許可ではなく、未実装のsequence/joint familyを追加する前の中間結果である。

## 固定した入力と分割

| 項目 | 実測 |
|---|---:|
| development | 2,195 rows / 102 CIK / 534 availability dates |
| inner train | 1,504 rows |
| inner validation | 691 rows / 68 CIK / 190 availability dates |
| locked outer（未開封） | 413 rows / 38 CIK / 183 availability dates |
| development text coverage | 100% |
| inner splitを跨ぐduplicate family | 0 |

panel、previous-filing sidecar、normalized text manifest、pre-analysis contractのhashはrunnerの外部
artifactへ保存した。raw/normalized textとCIK・accessionをrepositoryへコピーしていない。

| input | SHA-256 |
|---|---|
| M6 panel | `6c6008c2f28c30299e15e37613cfb0b3b22e8fd283858f5b459227c7e4a412a8` |
| previous-filing sidecar | `9ff2efef335357f4b2e8799fc4ee5d830c55843a50026fbbc` |
| normalized manifest | `1283b9cb0992cfd2caaa942f6c869e212762c90a9abbc9a050173f5e3963daba` |
| pre-analysis contract | `0aa180acbcd2b685509d6ec65fdf40f9edfcfc544ecec62c930facd0d4615b20` |

実行時のベースcommitは `63868f23855437de26877dfe3a6e1a9cd7e7dbbb`、runner source SHAは
`f20dbbf31aa44351f259456ef39205cc10c9c75fa813aa797d404629e1c52bb6` である。runtime秒は環境依存のため、
候補の順位・metric・seed・入力fingerprintを再現性の主対象とし、runtimeは診断値として記録する。

## inner-validation結果

primaryはMAE、secondaryはmedAE、company-macro MAEはguardrailである。baselineはprediction時点より前に
利用可能なtraining rowsだけで計算した。

| model | MAE | medAE | RMSE | company-macro MAE |
|---|---:|---:|---:|---:|
| zero | 0.060331 | 0.024565 | 0.171455 | 0.058765 |
| pooled drift | 0.061785 | 0.027180 | 0.172000 | 0.059529 |
| seasonal | 0.072384 | 0.028945 | 0.193330 | 0.071261 |
| company mean | 0.069082 | 0.032700 | 0.175258 | 0.067311 |
| best TF-IDF ridge（5,000 / bigram / λ=10） | 0.062185 | 0.028265 | 0.171873 | 0.060161 |
| best numeric ridge（λ=10） | 0.064360 | 0.028308 | 0.179238 | 0.062015 |
| best NumPy MLP（width=16 / lr=.003） | 0.099851 | 0.063130 | 0.193460 | 0.096723 |

TF-IDF ridgeはzero baselineのMAEを改善せず、medAE/company-macro MAEもbaseline最小値を満たさない。
NumPy MLPも同様である。そのため amended selection gate（best fixed baselineからMAE 1%以上改善、かつ
medAE/company-macro MAE非悪化）を通過する候補は0件となった。

## 実装範囲と未実装範囲

実行済みは `numeric_ridge` 4設定、`tfidf_ridge` 12設定、`numpy_mlp` 12設定である。TF-IDFは512-token
chunkを最大8個まで決定論的に選び、training-only document frequency / IDFをfitした。candidate runは
NumPy、SciPy、pandas、標準ライブラリだけを使う。

次のfamilyはまだcandidateとして実行していない。

- NumPy LSTM（end-to-end training loop）
- causal TCN（trainable readoutを含む固定予算の実装）
- small self-attention（position/maskを含むtrainable readout）
- joint text+numeric MLP

したがって今回の `no_model_selected` は、実装済みfamilyのpre-outer interimであり、全Core familyを
評価した最終nominee freezeではない。

## 再現性と次のゲート

runnerは `tools/run_b9_tournament.py`、共通処理は `src/quant_textbook/b9_tournament.py` に置いた。
外部artifactは `b9_development_tournament_v1.json` とし、`outer_accessed=false`を保存する。company-cluster
paired bootstrapは候補がselection gateを通過した場合だけ計算する設計で、今回は正式nomineeがないため
outer比較用bootstrapを生成していない。

次は以下の順序で進める。

1. LSTMについてはBPTT primitiveにpre-registered budget内の決定論的Adam training loopを追加済みである。
   ただし512-token×最大8 chunksのdocument-level aggregationをrunnerへ接続する候補runは未実施であり、
   次のrunでparameter-countとchunk-level validationを監査する。
2. joint text+numeric variantを同じinner splitで実行する。
3. TCN / self-attentionのtrainable readoutを同じ契約へ接続する。
4. 全Core familyを比較し、accepted nomineeがある場合のみcompany-cluster paired bootstrapとnominee
   manifestをfreezeする。なければ `no_model_selected` をfreezeする。
5. nominee manifest、feature manifest、seed、code commitを確認してから、別途明示承認を得てlocked outerを
   **一度だけ**開く。

outer結果を見てarchitecture、feature、threshold、comparatorを変更しない。
