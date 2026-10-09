# RB-F05 主 short-maturity 実験 独立レビュー

- 日付: 2026-10-09
- 数値・記録レビュー: **PASS、Critical 0 / Important 0、既知の非阻害 Minor 2。**
- 実験結果: **全 6 NN fit の raw / safe は固定精度条件を未達。NN の高速標準器採用は不成立。** Hermite は全 336 点で同条件を満たす。
- 対象: root が生成完了を通知した正式 reference.json / reference.npz、serialization_cost.json、process_cost.json。原記録の accepted=false / teaching_acceptance=false を維持。
- 範囲: read-only source / saved data、独立数式・原 seed の provenance 再生。新 MC 観測、NN training、checkpoint 選び直し、source / test / Git / 正式 artifact 変更なし。

## 証拠と binding

独立再実行:

- /tmp/rbf05_main_independent_audit.py — teacher、initial weights / batches、physical spot の 2 次微分、全 metrics / timings / costs。
- /tmp/rbf05_main_reference_audit.py — project pricing / BPoly 評価を使わない Poisson / Merton / tail / density / scalar quintic Hermite。
- /tmp/rbf05_main_combined_review.py — 両検査を実保存物に対して全数実行し、binding と結論を保存。
- /tmp/rbf05-main-independent-review.json — numeric_review_approved=true、critical_findings=[] / important_findings=[]。標準器判断は not_adopted_accuracy_failed。cold / fresh 費用は別 receipt 待ち。
- /tmp/rbf05-main-independent-numeric-audit.json と /tmp/rbf05_main_reference_audit.json — 全詳細。

最終 combined audit は exit 0、audit API 計測 3.7879 秒。共有 Python、BLAS / OMP / MKL single thread、bytecode 書込みなし。financial source registry 全 10 件は正式 pilot 承認時の registry と一致し、監査前後も不変。runtime NumPy / SciPy / Torch の版本と保存 thread 条件を照合。seed ledger 3,870 行を独立構成し重複なし。

- protocol_digest と source_registry: typed main review JSON の実値。
- main_record_digest: c116e01cbcfa0ef3d42b1b623a85eb976c6d3c3545ffca1b38cc97e06b03aebe
- main_arrays_digest: 8d270b341fae01de439f4a99edf81b61704fb1a2b9e98e545dbf5289169b44b6

hash / byte identity は provenance を検証する。金融値の正しさは以下の独立数式と許容誤差比較による。

## 全 teacher 640 件

train 512 / validation 128、元 N=1,048,576。balanced event / scenario geometry を元 reserved scenario seed から再構成した。全 teacher の元 count、active indices / counts、active-only normal marks、zero block、active C / physical Delta / Gamma、mean / joint M2 / covariance / SE、label array、precision / rare / reason の元 roster を検査した。

原 count / mark を予約 seed から再生し dtype / byte identity を確認。新しい observations やラベル追加・N 再選択ではない。analytic lambda=0 は予約 N を保持し、実 count / normal draws は 0 のまま。active subset を元 N 分母に読み替えない。

全 640 件が fixed precision_ready。元 observed MC count 合計 335,544,320、actual primitive draws 341,043,926。最大 SE は C 0.00103651、Delta 0.000126999、K Gamma 0.0128566。Gamma gate は各 case の 0.01 max(1, |K Gamma_ref|) で全数 PASS。active ≥100、6 SE と reference tolerances の gate も全数一致。主結果都合の緩和なし。

集計は original N の weighted first / second sums を long-double で独立計算。通常金融比較 atol=1e-10 / rtol=2e-9、M2 atol=5e-7 / rtol=2e-9。主検査 16,267 numeric comparisons が PASS。最大 mean 差 1.99e-12、M2 差 7.38e-8、covariance 差 7.04e-14、SE 差 6.00e-17。clock は saved datetime の microsecond quantization を入力規約として再現する。

## 全参照と strong C² Hermite

固定 test 336 の全 ordinary Poisson mixture と independently tilted Merton price、tail envelope、元代表 density 2 件を照合。ordinary reference 最大 C / Delta / Gamma 差は 3.15e-14 / 1.22e-15 / 2.13e-14、core 比較は 1.01e-13 / 2.61e-13 / 1.49e-12、tilted Merton 価格差 2.82e-14。

Hermite は全 4,680 node の scalar C / C_x / C_xx を独立参照で照合し、BPoly を呼ばない正規化区間 quintic 係数と解析微分から全 train 512 / validation 128 / test 336 予測を再構成した。physical Delta=C_x/S、Gamma=(C_xx-C_x)/S² とし、同じ scalar price を微分。保存 Gamma 差は最大 5.95e-13。全 endpoint / adjacency の C² 条件を確認。log spot における C² であり、log-time affine blend の Theta smoothness は保証しない。

全 48 bucket の original weights と error summary を照合。time × event 各 group の元 21 行、ATM + tail = 21 を保持。10 diagnostics は invalid 4、価格定義 6、普通 Greeks 定義 5、expiry ATM unknown 1。全 6 fit の fallback も元 roster のまま一致。QUADPACK の error estimate と Poisson tail bound は区別する。

## 3 paired seeds / 全 6 fit の scalar derivatives

元 seeds 11 / 29 / 47、各 price-only / Delta-DML で同 initial weights と master batches。project learner を呼ばず CPU Torch standard initializer から原 seed initial plain weights を byte 再生。batch seeds から全 512 × 128 master / attempted batches を byte 再生した。全 6 fit が completed / 512 updates / 512 attempts、time cap と overrun の記録も一致。

train-only log-feature / price / Delta scale を独立計算し、初期 / 最終 objective を全 6 件再計算。Gamma loss は使われていない。保存 final plain weights から physical S の値・1次・2次 jets を直接伝播し、価格・Delta・Gamma を独立計算した。全 976 行 × 6 fits の raw / safe、metrics、raw / safe 各 48 bucket、全 OOD / expiry を照合。最大 raw NN 比較差 1.67e-15。exact optimizer trajectory の再学習はしておらず、その独立再現を主張しない。

## 固定精度条件による実験結論

元 336 test 行を全 seed、全 component で保持。固定条件は |C error| ≤ 0.01、|Delta error| ≤ 0.005、|K Gamma error| ≤ 0.05 + 0.05 |K Gamma_ref|。finite / nonfinite の失敗を元分母から除外しない。今回の test 予測は全行 finite だが、大きな価格・Greek 誤差が残る。

| seed | fit | raw 3成分同時 PASS /336 | safe 同時 PASS /336 | test mixture fallback /336 |
|---:|---|---:|---:|---:|
| 11 | price-only | 0 | 193 | 193 |
| 11 | Delta-DML | 0 | 156 | 156 |
| 29 | price-only | 0 | 191 | 191 |
| 29 | Delta-DML | 0 | 190 | 190 |
| 47 | price-only | 0 | 182 | 182 |
| 47 | Delta-DML | 4 | 169 | 165 |
| — | Hermite | 336 | — | — |

safe の改善の多くは mixture に戻した行である。scalar bounds に合格した raw NN を精度保証と扱わない。Gamma を accuracy 条件から外して速度比較の採用 gate を通さない。

| seed | raw fit | C RMSE | Delta RMSE | K Gamma RMSE |
|---:|---|---:|---:|---:|
| 11 | price-only | 0.09686 | 0.18493 | 60.4530 |
| 11 | Delta-DML | 0.04050 | 0.06316 | 43.9083 |
| 29 | price-only | 0.11156 | 0.21095 | 62.0812 |
| 29 | Delta-DML | 0.04252 | 0.07352 | 47.2136 |
| 47 | price-only | 0.09710 | 0.19411 | 61.2178 |
| 47 | Delta-DML | 0.02782 | 0.04649 | 34.8256 |

DML は 3 paired seeds 全てで raw C / Delta / K Gamma の RMSE を下げた。この固定合成実験の比較結果であり、要求精度の成立や統計的普遍性を示さない。

Hermite は全 336 行・全 3 成分 PASS。最大 C / Delta / K Gamma error は 0.00046117 / 0.00055332 / 1.24608、component ごとの最大 error / fixed limit は 0.0461 / 0.1107 / 0.9028。Gamma の最大誤差を絶対項 0.05 のみと比較せず、固定相対項を含めて全 case で判定した。

## 全 timing output と費用閉集合

8 time × 2 event × 2 batch × 14 methods = 448 original timing slots。warmup 1 + repetitions 7 の全 3,584 保存 call outputs / routes を独立価格・Greeks で照合。indices の resize 順、14 methods の順序、保存秒の finite / nonnegative、元 batch 1 / 32 を確認。再 timing 計測ではなく、原 observations の数値・roster を監査した。

expense 全 674 件の exact id / category / charged / parent / scope を検査し、missing / extra / duplicate receipt なし。共有 train teacher generation 2.04611 秒はカテゴリで 1 回課金し、各 fit cap の teacher_s に含む。全 6 fit 時間の合計 3.87219 秒。最長個別 fit の teacher + training は 3.37273 秒で 120 秒 cap 内。

| measured scope | 秒 |
|---|---:|
| train teacher generation | 2.04611 |
| validation teacher generation | 0.49972 |
| fit 合計 | 3.87219 |
| Hermite grid + prepare | 0.09839 |
| timing envelope | 2.93451 |
| 保存 repetitions 秒合計 | 2.53435 |
| main categorized 合計 | 39.22017 |
| 別 record-bound serialization | 4.18468 |
| CLI wall 全体 | 46.08508 |

CLI exit=0 / formal command を確認。serialization receipt の record digest / NPZ size 177,133,184 bytes と照合した。main components + serialization = 43.40485 秒は CLI wall 内。CLI wall に nested components を加算しない。

original pending は serialization / cold_import / archive_load / pilot_freeze / fresh。serialization は外側の record-bound receipt で測定済みだが、immutable original record の pending を書き換えない。cold / fresh / archive-load などの外部 receipt の全 pipeline 評価は別レビュー。未計測費用を 0 にしない。

## Remaining findings / limits

Critical / Important の code・data finding は 0。既知の非阻害 Minor 2:

1. Literal ≤2 sqrt(W) ATM endpoint 分類の浮動小数 roundoff。隣 bucket に移り得るが元行・全 48 bucket・分母は保持。固定分類を結果に合わせて変更しない。
2. Pilot finite-h Gamma は deep ITM / tiny h の価格差分丸めを含み、概ね eps_C/h² で増幅。独立 60 桁価格で検証済み。保存 finite_h_bias 全体を teacher / model bias と呼ばない。

合成 regular weekday、固定単一 call 契約の実験であり、実市場 calendar / settlement / market calibration の承認ではない。expiry ATM と invalid の unknown は保持される。NN の固定 accuracy 未達は実験の負結果であり、保存 source や数値検算の defect と分類しない。

**数値検算と原記録の整合性は承認する。NN の高速標準器は固定 accuracy 未達につき採用しない。cold / fresh の bound receipt と最終報告・費用採用評価は parent の別作業である。**
