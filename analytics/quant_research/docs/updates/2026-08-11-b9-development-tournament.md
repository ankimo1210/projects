# 2026-08-11 — B9 development tournament（outer前）

## 結論

M6で固定したSEC cohortのうち、**development partitionだけ**でselection-eligible familyのcandidate runを完了した。
locked outer (413)行は数えただけで、outer文書・特徴量・予測値は読み込んでいない。実行した候補の範囲では
overall採用gateを満たす候補はなく、結果は `no_model_selected` である。時間分割に加えて、CIK
remainder 1→2、2→1の企業分離foldを追加し、候補は3軸すべてのgateを通過する必要がある。今回の
neural gateも全軸同時には通らず、neural nomineeは生成していない。したがってbootstrapも生成していない。
locked outerへ進むには、今後nominee manifestをfreezeし、別途明示承認を受ける必要がある。

## 固定した入力と分割

| 項目 | 実測 |
|---|---:|
| development | 2,195 rows / 102 CIK / 534 availability dates |
| inner train | 1,504 rows |
| inner validation | 691 rows / 68 CIK / 190 availability dates |
| company fold 1→2 | train 1,092 rows / 49 CIK; validation 1,103 rows / 53 CIK |
| company fold 2→1 | train 1,103 rows / 53 CIK; validation 1,092 rows / 49 CIK |
| locked outer（未開封） | 413 rows / 38 CIK / 183 availability dates |
| development text coverage | 100% |
| 3軸いずれかを跨ぐduplicate family | 0 |

panel、previous-filing sidecar、normalized text manifest、pre-analysis contractのhashはrunnerの外部
artifactへ保存した。raw/normalized textとCIK・accessionをrepositoryへコピーしていない。

| input | SHA-256 |
|---|---|
| M6 panel | `6c6008c2f28c30299e15e37613cfb0b3b22e8fd283858f5b459227c7e4a412a8` |
| previous-filing sidecar | `9ff2efef335357ff53bb1e4ba5c57f4b2e8799fc4ee5d830c55843a50026fbbc` |
| normalized manifest | `1283b9cb0992cfd2caaa942f6c869e212762c90a9abbc9a050173f5e3963daba` |
| pre-analysis contract | `b9f8236a21737fd9e6dba56adcc18fe83769dc8bfc12b7279fcad95017db8ed8` |

今回の外部artifactは180候補（時間軸76、企業分離fold各52、selection-eligible familyは各最大12設定、
probeは時間軸のみdiagnostic-only）を含む。実行時のベースcommitは
`4db3c40ed8eef9dbf2666d37c5650ff126a47022`、runner source SHAは
`eafca12f9e7c9cbb1b0fee8014730551227bffffa897436bf794f3f9a655dbbb`、artifact snapshot SHAは
`e42e38cd044cfa944cf45e8d06e221fbbe786cdebd2bf7ec77249418f2e7937f` である。runtime秒は環境依存のため、
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
| best NumPy LSTM（width=32 / lr=.003） | 0.060263 | 0.024973 | 0.171512 | 0.058306 |
| best TCN probe（diagnostic only） | 0.063560 | 0.028949 | 0.172410 | 0.061590 |
| best self-attention probe（diagnostic only） | 0.061506 | 0.026503 | 0.171893 | 0.059526 |

時間軸ではzero baselineがprimary comparator（MAE 0.060331）で、best LSTMはMAEをわずかに下回るが、
medAEはzeroの最小値を満たさない。企業分離foldの代表値は以下の通りである。いずれの軸でも全metric
guardrailを同時に満たす候補はなく、neural gateのpaired bootstrapは実行していない。

| axis | zero MAE | best TF-IDF ridge MAE | best LSTM MAE |
|---|---:|---:|---:|
| time | 0.060331 | 0.062185 | 0.060263 |
| company 1→2 | 0.052922 | 0.052620 | 0.052430 |
| company 2→1 | 0.063763 | 0.064215 | 0.063296 |

LSTMとTF-IDFの比較対象・候補IDは軸ごとにartifactへ保存したが、all-axis gateが必須のため
`neural_nominee=null` である。

## 実装範囲と未実装範囲

実行済みは時間軸で `numeric_ridge` 4設定、`tfidf_ridge` 12設定、`numpy_mlp` 12設定、
`joint_text_numeric_mlp` 12設定、`numpy_lstm` 12設定、probe 24設定、企業分離foldで各selection-eligible
family 52設定である。LSTMは512-token chunkを最大8個まで決定論的に選び、各chunkを固定token
embeddingの平均へ写像し、trainable LSTMが各active chunkを予測して、その予測をdocument levelで平均した。
zero-padded chunkの予測は平均から除外している。TF-IDFとLSTMは同じprevious primary document scopeを
使い、candidate runはNumPy、SciPy、pandas、標準ライブラリだけを使う。

selection-eligible familyのcandidate未実行はない。

- causal TCN（今回のprobeはencoder固定で、end-to-endではない）
- small self-attention（今回のprobeはencoder固定で、end-to-endではない）

したがって今回の `no_model_selected` はall-axis overall gateの正式結果であり、neural nomineeもない。
TCN/self-attentionはdiagnostic-onlyのためselection gateへ入れていない。nominee manifestをfreezeして
outerへ進むかは、別途明示承認を受ける。

## 再現性と次のゲート

runnerは `tools/run_b9_tournament.py`、共通処理は `src/quant_textbook/b9_tournament.py` に置いた。
外部artifactは `b9_development_tournament_v1.json` とし、`outer_accessed=false`を保存する。company-cluster
paired bootstrapはall-axis gateを通過したneural nomineeに対してのみ計算する規則である。今回はnomineeが
ないため、neural/overallいずれのbootstrapも生成していない。artifactの`selection_axes`、軸別候補、
軸別gate、duplicate-family監査で企業分離の選択根拠を再確認できる。

次は以下の順序で進める。

1. all-axis gateが通る候補はなく、`no_model_selected` と `neural_nominee=null` をdevelopment結果として
   freezeする。outerはまだ開かない。
2. TCN / self-attentionを固定encoder probeからend-to-end trainable readoutへ拡張する場合は、別の
   development runとして契約・予算・seedを先に追記する。現状はdiagnostic-onlyを正式記録する。
3. nomineeを再検討する場合は、契約変更・seed・入力fingerprintを先に新しいdevelopment runへ登録する。
4. その後、別途明示承認を得た場合のみ、locked outerを一度だけ開く。承認がなければouterは未開封のまま
   `no_model_selected` を保持する。

outer結果を見てarchitecture、feature、threshold、comparatorを変更しない。
