# M4/M5 native独立コール表：保存証跡の限定独立レビュー

更新：2026-10-10T03:54:07.190400+00:00

**判断：fixed v56のM4/M5保存部品観測を限定承認。formal全state精度資格・全体予算・pilot/main・phase受入は承認しない。**

## 原分母・由来・保存値

| 項目 | M4 CF | M5 PDE |
|---|---:|---:|
| 元形状 | 3levels×1date×7spots×33states | 4levels×1date×7spots×7states |
| 元slot／finite価格 | 693／693 | 196／196 |
| 初期price/errorの全NaN・unprocessed | 各693、processed=0 | 各196、processed=0 |
| 保存evidence | 693cells／1386integrals | 28state-level curves |
| 再構成＋source check_call_table | PASS | PASS |
| native qualification／独立判定 | unchecked／unknown | unchecked／unknown |

- 元graphは3138jobs/121cases/51attempts。original graph arguments SHA、prior controls適用後planned SHA、元parameters/field-currentを解決後resolved SHAの3段を検算。controls以外の元arguments・1date/7spots/33or7states・state全boundsは不変。
- **controls変更は事前固定**：元graph controlsは空dict。root priorはupper250/space2401/time1920/log-half-width1.8を明示した。top-level epsabs/epsrel/quadrature_limitを入れず、native第3CF levelの厳しい既定値を維持。original graphの空controlsと同じSHAだとは扱わない。
- 元fullfield257×321、257times/321z_nodes、order1024/frequency512/density_floor1e-10、surface descriptor/signature、parametersを照合。source80・全固定入力がroot before/after、prior、現在実ファイルに一致し、独立検査の前後にも不変。
- raw/initialのnative JSON/NPZ/array roster・shape/dtype/nbytes、pack coverage・origin receipt・expanded bytesを別計算で検算。保存観測34ファイルは不変。最大pack M5raw payload4,788,481B / expanded4,822,017Bで128MiB/256MiB内。
- 初期NaN/unprocessed保存→実worker→返却raw保存→saved checkerの順序を時計で照合。返却価格NaN/inf/欠損0。**M5のprice_unit_errors196件は原NaNのまま**で、精度値として0へ補充していない。

## 原quad/PDEの検算

- M4：1386 adaptive integralsの全subinterval coverage、区間和・absolute error和・convergence/message、price/raw_prices/price_unit_errorsを照合し、保存積分値から価格を別の式で再計算。CFの新integrand/quadは呼ばない。全693値がsource checkerと一致、価格上下限違反0。
- 第3CF level全231cells：upper500、quadrature_limit1600、epsabs1e-13、epsrel1e-12。第1/2levelはlimit800、epsabs1e-12、epsrel1e-11でupper250/500。全1386integralsの保存statusはconverged。
- M4保存最大price-unit quad errorは2.047395707e-10。base対cutoff差0、base対quadrature最大差4.263256415e-14。報告quad errorはcutoff biasや全state金融精度の保証ではない。
- M5：base(2401,1920,1.8)、space(4801,1920,1.8)、time(2401,3840,1.8)、domain(2401,1920,2.25)を全28rowsで照合。保存snapshots/grid.values/row.values/spot-grid・全日付・supported/failure・status counts・coeff midpoint範囲・Rannacher2・負operator係数0を検算。
- M5保存curveからquery7spotsへlog-coordinate CubicSpline（外挿なし）を別途適用し、全196価格とsource checkerを照合。価格上下限違反0。solver step・係数の再評価なし。
- M5baseに対する最大価格差はspace7.290203662e-5、time4.221588519e-7、domain5.472002935e-5。この**t0近傍7spot表**の観測値であり、49date全域・Greeks・formal全state精度へ資格を広げない。

## 費用と cap

| interval | M4 秒 | M5 秒 |
|---|---:|---:|
| 元financial worker | 0.733389719 | 32.177527820 |
| whole child | 4.813418843 | 34.935049111 |
| whole parent | 5.425978319 | 35.527945750 |
| root enclosing（最終receipt/stdout尾部込み） | **5.467673219** | **35.560855959** |
| enclosing子CPU | 5.250679000 | 36.269271000 |
| enclosing−inner parent | 0.041694900 | 0.032910209 |

- start/stop差分、parent自身+child CPU差分、worker⊂child⊂parent⊂outer、全level expense時計のworker内包含とunique IDを検算。level timingをparentと二重加算しない。
- 最大記録個別RSS：M4 **853,876,736B**、M5 **854,016,000B**。累積outer metricとinner sampling/kernel metricは別として最大値を使った。RSS合計やRLIMIT_ASへ読み替えない。
- rootの事前承認時刻は各parent開始より前。各行政上限M4 120秒／M5 300秒・4GiB内、observed_cap=None、overrun0。worker内部deadline=Noneでもroot enclosing cap監視は別に存在する。今回cap failure経路を新実行していない。
- 新saved-only独立probeは成功3.328489956秒・子CPU3.310484秒。最初のレビュー用import先誤り（HestonParametersをrun_pilot属性と誤認）はsource defectではなく、原script/log/3.216240341秒を保持。測定subprocess合計 **6.544730297秒**。他の読込・準備・報告費用は未測定unknown。
- この部品測定を全teacherjob・本実験・全phaseの速度/RSS/予算成立へ転用しない。

## 境界と証跡

new solver/dispatch/quad/solve_banded/RNGを拒否するsentinel下で検査し、呼出0。source/tests/Git変更、全191suite、新金融実行なし。原失敗・原値・receiptは保持。production sourceを変更する前のv56限定観測である。

- task-5-current-independent-call-table-independent-v3-decision.json
- task-5-current-independent-call-table-independent-v3-results.json / -parent-cost.json
- task-5-current-independent-call-table-independent-v3-probe.py / -probe.log
- task-5-current-independent-call-table-independent-v3-original-review-import-failure-*（原レビュー失敗）
- root fixed budget origin SHA：a28dd5334854aea96e72431617c92b61989c3a71d260d34042f3982b7add5b70
- measurement source origin SHA：b314b5a97a826d9d952e690332ca55acf1f0d9d372e088b4bc4293404c9440c6
