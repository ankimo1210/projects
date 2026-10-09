# RB-F05 正式 short-maturity pilot 独立レビュー

- 日付: 2026-10-09
- 結論: **承認。Critical 0 / Important 0 / 非阻害 Minor 2。**
- 対象: 完了済みの合成 short-call teacher pilot と、その数値に結び付けた freeze 判定。主 6 NN fit、Gamma の有用性、速度・性能採用、市場較正・coverage は別レビュー。
- 操作: 金融 source、test、Git、canonical artifact を変更せず、既存 seed の provenance 再生と独立計算のみを実施。新しい観測・ラベル追加・N 選択更新・NN 学習なし。

## 対象と再実行可能な証拠

対象は /home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/research/RB-F05/short_maturity/pilot/pilot.json と pilot.npz、および同 short_maturity directory の pilot_process_cost.json。正式 pilot 完了通知後に読んだ。金融 source の固定 commit 9960ebf9 と全 1,275 tests / 16 Ruff format PASS は root からの報告であり、このレビューでは Git 操作・全 suite 再実行をしていない。

独立監査スクリプト:

- /tmp/rbf05_formal_pilot_audit.py — seed、compact labels、raw/CRN、joint moments、roster、cost の独立計算。
- /tmp/rbf05_pilot_reference_audit.py — project pricing 関数を呼ばない clock、Poisson mixture、density、tail、60 桁有限差分参照。
- /tmp/rbf05_formal_pilot_review.py — 上記全数再実行、実データ binding、typed review 検証と保存。

共有 Python を利用し、OPENBLAS_NUM_THREADS=1 / OMP_NUM_THREADS=1 / MKL_NUM_THREADS=1 / PYTHONDONTWRITEBYTECODE=1 で実行。combined audit は exit 0、独立 audit API 計測 10.0066 秒。新規依存追加なし。

保存結果:

- /tmp/rbf05-formal-pilot-review.json — schema RB-F05-short-pilot-review-v1、approved=true / decision=approved、critical_findings=[] / important_findings=[]。protocol._validate_review による actual binding 検証 PASS。
- /tmp/rbf05-formal-pilot-seed-moment-audit.json — 全数 seed/moment/raw/cost の詳細。
- /tmp/rbf05_pilot_reference_audit.json — 全 84 case の独立参照詳細。
- /tmp/rbf05-formal-pilot-combined-evidence.json — 統合結果。

## 元 roster と seed provenance

84 case × 3 stream = 252 conditioned stream、4 prefix = 1,008 prefix を全数検査。raw は元の 252 stream × 65,536 paths、CRN は 3 h 幅 × 252 = 756 行を全数検査。NPZ の 17,724 array は全て参照され、余分な未参照 key・object array なし。

seed ledger 全 3,870 行を master seed / sorted logical ID / SeedSequence derivation から再構成し、logical ID と physical seed の重複なしを確認。registry 全 10 金融 source が存在し、saved registry と current source が一致、監査前後で不変。source registry は private teacher / learner、reference_methods、protocol、pilot、build_reference、analytics、zero_dte、alternative_models、bsm の閉集合。

全使用 raw count / z_brown / z_jump を original reserved seed から再生成。conditioning は full N count を先に生成し、active indices/counts に対してのみ marks を再生成。元の dtype と byte identity を検査した。これは保存物の provenance の検算であり、金融値の正しさを SHA で判定していない。

selection の actual observed count は 132,120,576、raw observed count は 16,515,072。記録の actual primitive draw 合計 184,221,365 を一致確認。lambda=0 の analytic stream は予約 N を保持し、実観測 count・draw は 0 のまま。active subset を元 N 分母に読み替えない。

## 独立金融計算と固定 readiness gate

独立に C / Delta / Gamma、mean、joint M2、covariance、SE を再計算した。compact zero block と active block を元 prefix N で集計し、広い raw LR 統計量の cancellation に対して long-double の joint sums を使用。全 23,688 numeric comparisons が許容誤差内。

金融値は明示した tolerance 比較。通常 atol=5e-11 / rtol=2e-9、conditional values atol=1e-10 / rtol=2e-9、M2 atol=5e-7 / rtol=2e-9、独立 mixture atol=8e-11 / rtol=2e-10。最大保存差は conditioned active values 2.2165e-12、mean 1.7289e-11、SE 1.8197e-13。raw の大きな統計量を含む M2 の最大絶対差は 0.00102234、covariance は 1.5600e-8 で、それぞれ値のスケールに対する相対許容差内である。

固定 gate を独立に再判定した:

- SE(C) ≤ 0.002、SE(Delta) ≤ 0.0005。
- K SE(Gamma) ≤ 0.01 max(1, |K Gamma_reference|)、K=100。
- 各成分の reference agreement は original 6 SE と固定 absolute / relative reference tolerance。
- event stream の active count ≥ 100。analytic stream の deterministic branch は保存契約通り。
- 全 case・全 stream ready の最小 candidate N を採用。元失敗・unknown と N 選択を分離。

| 元 prefix N | ready / 252 | not ready / 252 | event stream 最小 active count |
|---:|---:|---:|---:|
| 16,384 | 126 | 126 | 9 |
| 65,536 | 157 | 95 | 54 |
| 262,144 | 235 | 17 | 218 |
| 1,048,576 | 252 | 0 | 905 |

従って唯一の全 ready candidate、かつ最小 N は **1,048,576**。その N の最大 SE は C=0.00106944 / Delta=0.000128006 / K Gamma=0.0129732。Gamma の上限は case ごとの相対スケールを含むため、この最大値だけを 0.01 と比較しない。全 252 判定が PASS。6 SE は経験的整合性の診断であり、不偏性や coverage の証明ではない。

## 全 84 primary reference と clock / tail / quadrature

独立実装で UTC ACT/365 carry、残存 session の区分積分 clock、pulse overlap を再計算。ordinary Poisson probabilities、conditional lognormal call / Delta / physical boundary-density Gamma、opposite-tail payoff / PW Delta integration と tighter quadrature、positive tilted-Poisson tail recurrence を比較。

保存 independent mixture の最大 C / Delta / Gamma 差は 2.13e-14 / 1.21e-14 / 2.71e-13。clock variance 差は 2.03e-20。density oracle との差は 1.20e-14 / 2.22e-16 / 0。saved quadrature と tighter quadrature は全数で固定 quarter-budget gate 内。最大 budget 比は通常 Delta=0.20218、tight Delta=0.06278。Poisson tail envelope は価格 2.00e-18、Delta 1.90e-20、より鋭い Gamma 2.66e-22 以下。core の conservative Gamma bound も 1.58e-20 以下。

QUADPACK error は数値誤差の推定で、rigorous bound と呼ばない。tail truncation の正の envelope は別に検査した。保存 floating input を固定して oracle 比較し、spot/clock の ULP 差を quadrature error に含めない。

## finite-h Gamma の丸めを分離

全 252 finite-h reference を、保存された floating S±h を入力とする独立 60 桁価格から再計算。最大 saved target 差は Delta 2.054e-12、Gamma 6.331e-9。

deep ITM / tiny h の Gamma は価格の subtraction roundoff が概ね eps_C / h² で増幅される。明示的な診断 allowance として B_C(x)=32 eps (x exp(-q tau)+K exp(-r tau))、B_D=(B_plus+B_minus)/(2h)、B_G=(B_plus+B_minus+2B_zero)/h² と小さい arithmetic allowance を使用。最大 target error / allowance は Delta 0.00677、Gamma 0.00615。これは libm の rigorous bound ではないが、独立高精度結果と整合する丸め診断である。teacher / reference precision gate は変更していない。

保存 finite_h_bias は finite-h target と true Gamma の差に価格の浮動小数丸めを含む。差全体を有限幅の数学的 bias や teacher の bias と呼ばない。

## raw / CRN の original failure と unknown

| 元診断 | supported | unsupported | inconclusive |
|---|---:|---:|---:|
| raw price | 246 | 2 | 4 |
| PW Delta | 247 | 1 | 4 |
| LR Delta | 246 | 2 | 4 |
| LR-PW Gamma | 248 | 0 | 4 |
| LR2 Gamma | 246 | 2 | 4 |
| CRN Delta（756 行） | 743 | 13 | 0 |
| CRN Gamma（756 行） | 625 | 3 | 128 |

naive pathwise Gamma は 252 行全て negative_control。上記 status、元分母、CRN crossing、width、finite-h targets/bias、martingale/logvariance の mean/SE/target を独立再計算した。unsupported / inconclusive を隠さず保持し、conditioned teacher readiness、main の採用・coverage 承認に読み替えない。

## 費用閉集合と CLI receipt

元 expense 1,512 件、方法・timer の exact roster と charge flags を検査。selection generation を price-only / DML 共通で 1 回のみ課金、raw は研究診断費用として維持。reference 6 timer × 84 と stream 4 timer × 252 が全て存在。setup / serialization / run の固定 roster も存在。

| scope | 秒 |
|---|---:|
| selection generation | 1.07823 |
| selection prefix summary | 0.15376 |
| raw RNG | 0.28670 |
| raw engine + summary | 2.63292 |
| serialization | 7.32191 |
| nonoverlapping components 合計 | 11.88534 |
| API run 全体 | 12.02928 |
| CLI wall 全体 | 12.60960 |

API overhead 0.14393 秒と CLI-over-API 0.58033 秒を残す。API は CLI wall の中に含まれ、加算しない。正式 CLI receipt の exit=0、formal command / path / scope、digest を検査。pilot 費用は主 run の cold / fresh / fit 費用の承認を意味しない。

## 残事項と承認 binding

非阻害 Minor は既知の 2 件:

1. Main runner の ±2 sigma ATM endpoint classification に浮動小数 roundoff があり、endpoint が隣 bucket に移る可能性。元の全行・分母は保持される。主結果解釈時の別レビュー事項。
2. 深い ITM / 小さい h の finite-h Gamma の価格差分丸め。上記の独立高精度確認により原因を分離した。保存 bias の解釈制約を維持。

正式 artifact は単一の合成 regular weekday 上の active 84 case。expiry boundary / holiday / DST はこの保存物の観測ではなく、以前の source foundation tests の範囲。root の両 CAS independent restore + saved numeric PASS は別証拠として受領したが、この reviewer 自身は CAS restore を実施していない。

typed approval は次の実データ 4 binding を持つ:

- protocol_digest: 9db9c8ff53314333fec503813eabbbc7539ca52563dfacec31533dc3940128e9
- pilot_record_digest: b10e1e28bddbd8fef4a9bfd1160523ed5b57a69e99d6a0cdb61036f9077571f8
- pilot_arrays_digest: f5a2000f6d54bb4220fafc706e32e96f0ff5d78fdeadae542971a2379b070d31
- source_registry: actual の全 10 path/digest。完全値は typed JSON / combined evidence に保存。

**この実 pilot と固定 source に対する teacher sample freeze review を承認する。主 6 fit、test / OOD / bucket / raw-safe Gamma の学習結果、cold/fresh/fit 費用、性能採用は次の別レビューである。**
