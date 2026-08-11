# 2026-08-11 — Opus alignment follow-up

## 結論

Opus reviewで再現した4件を修正した。B9のmodel-selection gateは固定baseline 4本を同じ
inner validationで比較する規約へamendし、B6はbaggingと時系列split guardの欠落を補った。
B9 locked outerは未開封で、正式decisionは引き続き`no_model_selected`である。

## B9 selection contract

- fixed baselineは`zero`、`pooled_drift`、`seasonal`、`company_mean`の4本とする。
- nomineeのinner-validation MAEは4本中の最小値を1%以上改善する必要がある。
- median absolute errorとcompany-macro MAEも、各metricにおける4本の最小値を悪化させない。
- primary baselineはMAEと固定tie-breakで選び、nominee manifestとともにouter前にfreezeする。
- outerではfrozen baselineとのcompany-cluster paired intervalだけを評価し、outer outcomeから
  comparatorを選び直さない。

この変更はteaching fixture上で`zero`が`pooled_drift`より強いことを確認した後だが、full candidate
evaluation、nominee freeze、company-cluster bootstrap、outer accessより前に行った。以前のcontract hash、
観測済み情報、理由、非変更範囲を`amendments`へ残した。

| artifact | SHA-256 |
|---|---|
| amendment前 contract | `fbe69fdf3b3bccba7fab70bcbb726d0df61685901cc0322d76fc66be1d7bbd6e` |
| 現 contract | `0aa180acbcd2b685509d6ec65fdf40f9edfcfc544ecec62c930facd0d4615b20` |
| 現 teaching fixture | `953c9b06c6c1dc1ef68c5e21f1ee88c4fe20d1ee34d5887150e51843184ad0b0` |

Project Notebookの64-row development-only validationでは、fixed baselineの結果は次のとおりだった。
これは規約の実行確認であり、正式nominee選定には使わない。

| baseline | MAE | medAE | company-macro MAE |
|---|---:|---:|---:|
| zero | 0.049469 | 0.020475 | 0.043651 |
| pooled drift | 0.052109 | 0.024111 | 0.046102 |
| company mean | 0.064327 | 0.031272 | 0.055345 |
| seasonal | 0.069820 | 0.020475 | 0.062704 |

したがって、このfixtureでfreezeされるprimary baselineは`zero`である。outer comparatorを
`pooled_drift`へ固定していた旧文言は使用しない。

## B6 curriculum gaps

### Week 21

baggingを、相関したbase learnerの平均における

$$
\operatorname{Var}(\bar e)=\sigma^2\left(\rho+\frac{1-\rho}{B}\right)
$$

として追加した。Treasury training期間をmoving-block bootstrapした24本のstumpで、single stumpとの
validation比較とcross-bag prediction dispersionを表示する。実行値はsingle stump RMSE 7.204943 bp、
bagged RMSE 7.210941 bpであり、このfixtureではaccuracy改善はない。baggingを常に精度向上する手法とは
主張せず、共通errorは平均しても消えないこととboostingとの差を教材の中心に置いた。

### Week 24

grouped split、purging、embargoを別々のguardとして追加した。単一の公式Treasury curve系列なので
entity-group splitは適用せず、selection開始時点までにlabelが完結しない境界1行をpurgeする。
追加embargoは0 publicationとし、適用しない理由も表に残す。どのguardも無条件の儀式ではなく、
information set、label horizon、entity構造から要否を決める。

## 検証

- 変更した14 Notebookのdeterministic builder check: pass
- 変更した14 Notebookのclean-kernel top-to-bottom実行: pass、error 0、execution count連続
- B9 fixture: inner train 192行、inner validation 64行、locked outer row 0
- Project output: fixed baseline 4本を表示し、primary baseline=`zero`
- Week 24 output: grouped 0 / purge 1 / embargo 0
- quant_research tests: 413 passed
- 60 Notebookのvalid Python・決定的JSON: pass
- Ruff check / format check: pass
- Jupyter Book warning-as-error full build: pass
