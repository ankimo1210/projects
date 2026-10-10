# 全49日付 call cache M2/M3：保存値の限定独立レビュー

更新：2026-10-10T03:35:47.971498+00:00

**判断：保存済み M2/M3 部品観測を限定承認。金融精度・正式予算・pilot/main・phase受入は承認しない。**

## 確認結果

| 項目 | M2 Heston | M3 local |
|---|---:|---:|
| 元形状 | 49×65×33 | 49×65×7 |
| 元スロット／保存値 | 105,105／105,105 | 22,295／22,295 |
| finite／NaN／inf | 105,105／0／0 | 22,295／0／0 |
| 保存した初期 NaN・unprocessed | 105,105、processed=0 | 22,295、processed=0 |
| 全49日付 source node check | PASS | PASS |
| 保存ノードの価格上下限（許容差1e-10） | 違反0 | 違反0 |
| qualification／reference_status | unknown／unmeasured | unknown／unmeasured |

- source80ファイルと全固定入力が prior budget、root before/after、現在の実ファイルに一致。独立検査中にも変化なし。
- 元3138jobs/121cases/51attemptsの保存graphから各call-current行を読み、元parameters・field-current・軸を解決した。planned/resolved argumentの出所SHAを再照合し、raw/初期artifactの型付き引数も一致した。数値値の比較には許容誤差を使用し、SHAは出所認証に限定。
- fieldの元257×321・257times/321z_nodes、order1024/frequency512/density floor1e-10、support/wing/parametersを保存値から照合。raw field82497値は全finiteで、原NaNの生成・埋め替えなし。
- 初期全NaN/unprocessed artifactがworker開始より前に記録され、返却rawがsource node checkより前に保存された時計順序を確認。欠損スロット0。price_error/derivative_errorのNaN、Heston coefficient_min_timesのNaNと原solver診断は保持。
- M2診断はCF/order1024・元49残存満期。M3の7診断はspace1201/幅1.8、元49datesとbase960のunion975区間、failure=None、負のoperator係数0。これは保存診断の照合であり独立価格精度の証明ではない。
- root/packのreceiptを別計算で検算：JSON/NPZ/array roster・shape/dtype/nbytes・SHA・expandedサイズ。最大packは初期M2 payload8,319,945B / expanded8,321,225Bで、128MiB/256MiB上限内。読み取った観測34ファイルは不変。
- source node checkは保存値のtensor splineノード再評価だけ。新CF/PDE/dispatch/RNGを拒否するsentinel下でPASSした。独立参照、格子収束、オフノード精度・Greeks精度の資格へ広げない。

## 費用と cap

| interval | M2 秒 | M3 秒 |
|---|---:|---:|
| 金融worker（原root保存値） | 46.277233899 | 3.467180509 |
| whole child | 55.121985580 | 7.078935287 |
| whole parent | 55.600923910 | 7.636735810 |
| root outer enclosing（最終receipt/stdout尾部込み） | **55.631469809** | **7.666767393** |
| outer-minus-parent | 0.030545899 | 0.030031583 |
| outer child CPU | 56.356544000 | 7.735771000 |

- start/stop差分、parent自身+childのCPU差分、worker⊂child⊂parent⊂outerの包含を保存時計から検算。CPUとwallは別指標。
- 最大記録個別process RSS：M2 **854,126,592B**、M3 **854,421,504B**。outerの累積子process RSS値とinnerのsampling/kernel値は測定範囲が違うため、最大値を使用した。
- 各部品 prior行政上限300秒・4GiBに収まり、observed_cap=None、overrun=0。0.01秒samplingとkernel最大値による個別RSS監視であり、RSS合計や仮想アドレス制限ではない。今回cap failure経路の再実行はしていない。
- この49日付部品の費用を金融教師全job・本実験・全phaseの速度/RSS/予算成立へ転用しない。準備・旧失敗・研究全体の費用はここで閉じていない。
- 独立saved-only probeの測定parent費用：**9.388496794秒**、子CPU **9.380665000秒**。追加の読み取り・準備・報告費用は未測定unknown。

## 境界と証跡

新金融worker/RNG/追加agent/全191suiteの実行なし。source/tests/project docs/Git編集なし。原失敗・原値・receiptは保持。

- 判定：task-5-current-whole-call-cache-independent-v3-decision.json
- 数値・費用：task-5-current-whole-call-cache-independent-v3-results.json / -parent-cost.json
- 再現用検査：task-5-current-whole-call-cache-independent-v3-probe.py / -probe.log
- 固定root budget SHA：e7f8b53e5ba662d606545bdb6f071637d889f94c7c4d41721b4002eb0950dc23
- 固定measurement source SHA：2ca6c134e2cacf0ca76da8bd0142f960f9cf8831c4b0fe6d3813319dbe90aa1b
