# 2026-08-11 — B9 development tournament（outer前）

## 結論

M6で固定したSEC cohortのうち、**development partitionだけ**でselection-eligible familyのcandidate runを完了した。
locked outer (413)行は数えただけで、outer文書・特徴量・予測値は読み込んでいない。実行した候補の範囲では
overall採用gateを満たす候補はなく、結果は `no_model_selected` である。ただし、LSTMはTF-IDF ridgeに
対するneural gateとcompany-cluster paired bootstrapを通過し、neural nominee候補になった。
これはouterへ進む許可ではなく、locked outerを開くにはnominee manifestのfreezeと明示承認が必要である。

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

今回の外部artifactは76候補（selection-eligible familyは各最大12設定、probeはdiagnostic-only）を含む。
実行時のベースcommitは `73d1f93b56e46ccd26bea96b879080fe81b113b3`、runner source SHAは
`4eb878e5c762a1b7272ce73a8b8e16a11c846ca80d6493e83b245922b03a742f`、artifact snapshot SHAは
`92bce4fd5f89f58aac0df9d00db19e6d3b78504685f140d5eee0fe0b63732853` である。runtime秒は環境依存のため、
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
| best joint text+numeric MLP（width=32 / lr=.003） | 0.079472 | 0.042376 | 0.175479 | 0.077414 |
| best NumPy LSTM（width=16 / lr=.003） | 0.059718 | 0.024893 | 0.171244 | 0.058006 |
| best TCN probe（diagnostic only） | 0.063560 | 0.028949 | 0.172410 | 0.061590 |
| best self-attention probe（diagnostic only） | 0.061506 | 0.026503 | 0.171893 | 0.059526 |

TF-IDF ridgeはzero baselineのMAEを改善せず、medAE/company-macro MAEもbaseline最小値を満たさない。
NumPy MLP、joint MLPも同様である。LSTMはzero baselineのmedAE guardrailを満たさないためoverall gateは
通らないが、TF-IDF ridgeに対するneural gateは通過した。best LSTMのpaired company bootstrapは
`delta_mae=-0.002155`、95%区間 `[-0.003665,-0.000736]`（2,000回、seed=20260812）であり、
pre-outerのneural nominee候補として記録する。

## 実装範囲と未実装範囲

実行済みは `numeric_ridge` 4設定、`tfidf_ridge` 12設定、`numpy_mlp` 12設定、
`joint_text_numeric_mlp` 12設定、`numpy_lstm` 12設定である。LSTMは512-token chunkを最大8個まで
決定論的に選び、各chunkの固定token embedding平均をpadding mask channel付きsequenceとして、chunk列を
LSTMへ入力した。TCN 12設定とself-attention 12設定は、短い64-token固定encoderとtrainable MLP
readoutのdiagnostic probeとして評価した。TF-IDFとLSTMは同じprevious primary document scopeを使い、
candidate runはNumPy、SciPy、pandas、標準ライブラリだけを使う。

selection-eligible familyのcandidate未実行はない。

- causal TCN（今回のprobeはencoder固定で、end-to-endではない）
- small self-attention（今回のprobeはencoder固定で、end-to-endではない）

したがって今回の `no_model_selected` はoverall gateの正式結果であり、LSTMのneural nominee候補とは
別である。TCN/self-attentionはdiagnostic-onlyのためselection gateへ入れていない。nominee manifestを
freezeしてouterへ進むかは、別途明示承認を受ける。

## 再現性と次のゲート

runnerは `tools/run_b9_tournament.py`、共通処理は `src/quant_textbook/b9_tournament.py` に置いた。
外部artifactは `b9_development_tournament_v1.json` とし、`outer_accessed=false`を保存する。company-cluster
paired bootstrapはcandidateごとではなくgate通過したneural nominee候補に対して計算した。overall nomineeは
ないため、overall-vs-primary bootstrapは生成していない。

次は以下の順序で進める。

1. LSTMは512-token×最大8 chunksのdocument-level aggregationへ接続済みで、12設定のparameter-count・
   chunk-level validationを実行した。neural gateとbootstrapを通過したため、候補IDをfreeze対象とする。
2. TCN / self-attentionを固定encoder probeからend-to-end trainable readoutへ拡張する場合は、別の
   development runとして契約・予算・seedを先に追記する。現状はdiagnostic-onlyを正式記録する。
3. neural nominee manifest、feature manifest、seed、code commitを確認し、全入力fingerprintとbootstrapを
   保存する。overallは `no_model_selected` としてfreezeする。
4. その後、別途明示承認を得た場合のみ、locked outerを一度だけ開く。承認がなければouterは未開封のまま
   `no_model_selected` / neural nominee候補をdevelopment結果として保持する。

outer結果を見てarchitecture、feature、threshold、comparatorを変更しない。
