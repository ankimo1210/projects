# P5 ロジック先行の実装状態

更新2026-10-06。目的：Ch22–25（台帳36項目）の計算ロジックを実装する。計算対象32項目（§25.5/6の既存価格計算の検証を含む）と、説明中心4項目（§22.7/23.4/24.1/24.3）を区別する。

- 完了条件：本文の式・数値例を節メモで確認し、private計算部品と本文再現・独立検証をそろえ、変更モジュールのtests/ruffを通す。原典入力が足りない箇所は不足を記録し、計算できる範囲を検証する。
- 本人承認のロジック先行方針を継続。計画は既存節メモに数行、1節1コミット/P5 §xx.y、節ごとpush。新公開API・依存追加なし。
- 実装ブランチ：`codex/p5-logic`。P4の計算を引き継ぐ。mainは進捗文書のみ反映する。
- 正式受入：P5 0/36、全体33/306。説明・教材・章受入・全suite・D1・保管庫復元は保留。
- 現在：計算32/32。次はP5対象全計算の確認と進捗文書の反映。Ch22→23→24→25まで継続する。

## 節別の実装

検証件数はその節の変更モジュールの累計で、合算しない。表の完了は記載した計算範囲と対象検証を表す。

| 節 | 実装ファイル | 再現した本文の数値／独立検証 | 未解決の点 | 対象検証 |
|---|---|---|---|---|
| §22.1 | `_market_risk.py` | 固有の印刷価格なし。正常/tの同じVaR・異なるES、sqrt(N)とAR(1)集計分散。独立裾積分・共分散和、固定seed MCの分位点6SE | 計算部分完了。loss_meanは正が損失。AR(1)はstationary日次SD。規制・説明/教材/正式受入は保留 | 8 passed・ruff check/format PASS |
| §22.2 | `_market_risk.py` | Table22.3の4行（印刷丸め許容.06千ドル）、Table22.4 VaR422.291/ES669.391、BRW VaR653.541/ES約833.2。独立Decimal cash、整数重複分布・分位関数の裾積分 | 計算部分完了。501日原系列は未保有、既知15最悪損失の下側はテスト用合成補完。p521累積.004833は誤植。Hull/Excel/stressedのVaR規約を分離し、250点ESはfractional tail mass。説明・受入保留 | 17 passed・ruff check/format PASS |
| §22.3 | `_market_risk.py` | MSFT/AT&T/相関.3のVaR1,471,300/367,800/1,620,100、ESの厳密値。印刷MSFT ES1,687,000はz2.326で再現。独立正規/対数正規裾積分・固定seed相関MC6SE | 計算部分完了。MSFT印刷ESと厳密ES1,685,629.5の丸め規約差を分離。正規はloss_mean/利益平均の符号を明示、lognormalにsqrt(N)を仮定しない。説明・受入保留 | 27 passed・ruff check/format PASS |
| §22.4 | `_market_risk.py` | Tables22.7/8 分散14404（印刷14406.193との丸め差）、VaR279.222/ES319.894、Ex22.1 sigma7.099、本文3CF30000/30000/1030000。独立多変量求積・債券再評価・mapping求根・FX/OIS cashflow | 計算部分完了。mappingは各cashflowのPV/分散を保存、bookの全cross covariance保存は保証しない。TN25配布先はエラーページ、公式検索に残る設定は確認したが全中間印刷pinは保留。説明・受入保留 | 35 passed・ruff check/format PASS |
| §22.5 | `_market_risk.py` | 脚注10の3 raw moments、TN10 mean−.2/SD2.2/skew−.4→normal−5.326/CF−5.976。独立多変量Gauss求積・二次式の正規区間CDF求根・full Hessian再評価 | 計算完了。CFは第三モーメントの近似で強い歪度で精度・単調性の保証なし。TN10の公式索引の式・例は確認、配布PDF取得不可。説明・受入保留 | 44 passed・ruff check/format PASS |
| §22.6 | `_market_risk.py` | 5000標本99%50位/95%250位。独立線形正規と単調BSM分位点を固定seed MC6SEで照合、full/partial同一shock・実際の10日maturity再評価 | 計算完了。Gaussian arithmetic return、future_bookがtheta/carryの扱いを決める。sqrt(N)はoptionに厳密でない。説明・受入保留 | 50 passed・ruff check/format PASS |
| §22.8 | `_market_risk.py` | 本文1%/7%（100日を明示した合成例）。独立二項和・尤度式・遷移表、将来値を変えても事前予測が変わらないこと | 計算完了。超過頻度だけでESやモデル全体の妥当性は判定しない。本文の標本数は未指定。説明・受入保留 | 55 passed・ruff check/format PASS |
| §22.9 | `_market_risk.py` | 全64loading/8SD、総分散152.5185、87.3%/95.6%/.96bp/2.42bp。Table22.11露出−1.998/−3.067→sigma25.49837/VaR59.31808。独立SVD/固有分解・trace・符号不変 | 計算完了。2631観測は未保有。印刷sigma25.45/VaR59.2は丸め表から一致しないため補正せず記録。市場説明率とbook残余riskを区別。説明・受入保留 | 60 passed・ruff check/format PASS |
| §23.1 | `_volatility_estimation.py` | 固有印刷価格なし。式23.1–6のlog/sample mean/m−1とsimple/zero mean/m、ARCH重みを独立小標本算術と解析MLEで照合 | 計算完了。日次分散を返し年率換算は別。ARCH historyは予測日前までのchronological履歴。説明・受入保留 | 4 passed・ruff check/format PASS |
| §23.2 | `_volatility_estimation.py` | Ex23.1 lambda.9/vol.01/return.02→variance.00013・vol1.14%。独立幾何重み和+lambda^m初期項、予測への当日return不混入 | 計算完了。n+1 forecastsで最後は翌日予測、initial必須。RiskMetrics.94を普遍最適としない。説明・受入保留 | 7 passed・ruff check/format PASS |
| §23.3 | `_volatility_estimation.py` | Ex23.2 gamma.01/VL.0002・更新.00023516→vol1.53%。独立beta幾何和と再帰・EWMA極限、連続近似a.01/xi=.13sqrt2 | 計算完了。betaは履歴重み、alpha+betaは予測持続性。非定常時はVLなし。連続対応は原典の近似。説明・受入保留 | 10 passed・ruff check/format PASS |
| §23.5 | `_volatility_estimation.py` | p1/10=.1、Table23.1先頭4variance/尤度、VL.0001391、Table23.2全30ACFからQ2139.60985/12.94915・閾値25。独立normal密度・別optimizer・grid | 計算完了。1259価格未保有で原系列fit/全尤度10837.4227は保留。尤度第三行8.6333とACF統計2170/13.2との不一致を保持。自由度補正は明示。説明・受入保留 | 17 passed・ruff check/format PASS |
| §23.6 | `_volatility_estimation.py` | 10/100日v.0002594/.0001479、Table23.3 26.5/24.9/23.8/22.0/19.5%、Table23.4 +1point→.90/.74/.61/.41/.10point。独立quad・反復期待値・中心差分 | 計算完了。sqrt(E[v])とE[sqrt(v)]、P予測とQ IVを区別。ショックは相対1%でなく1percentage point。説明・受入保留 | 21 passed・ruff check/format PASS |
| §23.7 | `_volatility_estimation.py` | Ex23.3 variance.00009625/.00041125/cov.00012025→rho.6044。式23.17 book variance−.6・最小eigen−.2727922。独立outer-product幾何和・matrix反復・PSD特異例 | 計算完了。ゼロvarianceの相関はNaN、PSD特異行列は許容。ペア別範囲内でもglobal PSDとは限らない。説明・受入保留 | 26 passed・ruff check/format PASS |
| §24.2 | `_credit_risk.py` | Table24.1 BBB2年.29%/CCC3年4.77%/2年生存63.36%/条件付き7.53%。独立ODEと生存比・確率積 | 計算完了。Table24.1は観測入力で再推定しない。累積/区間/条件付きPDと年率hazard、P/Qを明示。説明・受入保留 | 4 passed・ruff check/format PASS |
| §24.4 | `_credit_risk.py` | Ex24.1平均2.5/3/3.25%・区間2.5/3.5/3.75%。Ex24.2価格/差/3hazard/forward104.12/102.71・lossPV63.33/60.40の全21印刷値。独立同時root+生存CF/回収events | 計算完了。半年中央default・額面回収でISDA慣行モデルとは異なる。割引curveと信用curveを分離。説明・受入保留 | 8 passed・ruff check/format PASS |
| §24.5 | `_credit_risk.py` | Tables24.2/3の全ratio/difference/compensation/excess28値、BBB7年hazard.34%/Q3%/Baa損失spread28.2bp。独立Decimal比/積・指数CDF求根 | 計算完了。P/Q変換モデルではなく観測入力の比較。印刷補償spread整数bpを先に丸めた差とraw差を区別。式24.10参照は24.1の原典誤参照。説明・受入保留 | 10 passed・ruff check/format PASS |
| §24.6 | `_credit_risk.py` | Ex24.3全7値 asset12.40/vol.2123/d2 1.1408/PD12.7%/debt9.40/riskfree9.51/loss約1.2%。独立payoff/delta求積+log root（T1/2.5）、固定seed default6SE | 計算完了。N(−d2)はQ PD。指定P driftの構造PDは非公開EDFの較正ではない。単一満期/満期default仮定。説明・受入保留 | 14 passed・ruff check/format PASS |
| §24.7 | `_credit_risk.py` | Ex24.4 5/0/0/5、40→15・10000中250位、Ex24.5 2.91、Ex24.6全7値CVA5.77/調整84.71。独立lognormal求積・共通GBM MC6SE・担保lag恒等式・factor求積 | 計算完了。1oz単位と1m oz総額を区別。PDは無条件区間、LGD/割引各1回。wrong-wayは明示したGaussian factor例で一般契約/first-to-default解ではない。担保lagは指定grid段数。説明・受入保留 | 21 passed・ruff check/format PASS |
| §24.8 | `_credit_risk.py` | 5/10%とEx24.7全5threshold（計7値）、10社rho.2/5年PD15%を固定seed MC6SE。独立正規CDF逆積分・条件付き2latent積分・factor積分 | 計算完了。latent相関、indicator相関、default時刻相関を区別。year0は年限後生存でnever defaultではない。TN26の詳細原文は未取得。説明・受入保留 | 25 passed・ruff check/format PASS |
| §24.9 | `_credit_risk.py` | Ex24.8 PD12.8%/VaR5.13m、Table24.4全7threshold。独立factor/5000社有限pool MC6SE、bond cashflow再評価・2社状態列挙 | 計算完了。total loss VaRとEL控除capitalを分離。格付再評価は渡したspread曲線のflat例、default回収は額面。BBB→A原典区間逆転/既存docstring残差記述の問題は未変更。説明・受入保留 | 30 passed・ruff check/format PASS |
| §25.1 | `_credit_contracts.py` | 90bp→四半期22.5bp/225000、回収35%→65m・2か月経過150000、250/260bp→2.5/2.6%、保護付きyield5%の全7値。独立Decimal cash・生存/default CF列挙 | 計算完了。年分数の概算規約でcalendar dates/auction CTD/legal契約モデルは対象外。信用事由と取引相手defaultを区別。説明・受入保留 | 3 passed・ruff check/format PASS |
| §25.2 | `_credit_contracts.py` | Tables25.1–5全54cell/合計+7結果=61値、par123bp/MTM±.0111/100bp→hazard1.63%/binary205bp。独立default年CF列挙・指数時刻MC6SE・回収再較正 | 計算完了。中央default/元本1・spread1の係数。quote固定でhazard再較正、通常CDS回収近似不感応を厳密不変としない。説明・受入保留 | 7 passed・ruff check/format PASS |
| §25.3 | `_credit_contracts.py` | 125社800000×65/66bp→650000/660000、1社減少5280、1000/10bp単純平均505bp。独立2社default状態CF・zero NPV求根でindex加重 | 計算完了。実際の加重priceは原典入力不足でpinなし、合成r/T/Rを明記。観測125社指数の現在仕様は扱わない。説明・受入保留 | 10 passed・ruff check/format PASS |
| §25.4 | `_credit_contracts.py` | Ex25.1年率.345/.406%・hazard.5717%・D4.447・price100.27の5値。独立default時刻別CF+upfront NPV0・受払符号 | 計算完了。365/360固定例で閏年/任意calendar日数一般化なし。Dはpremium PV係数でbond durationと異なる。説明・受入保留 | 13 passed・ruff check/format PASS |
| §25.5 | `_credit_contracts.py` | 原典1年開始/5年保護/280bpの契約設定と期前default KO。価格印刷なし。明示した合成vol等で独立lognormal payoff求積・parity・ゼロvol | 計算完了。原典価格/vol入力不足で価格pinなし。Blackはforward annuity測度のspread lognormal仮定、Aは時点0の無条件生存/割引込み。front-end protectionは別範囲。説明・受入保留 | 16 passed・ruff check/format PASS |
| §25.6 | `_credit_portfolio_extensions.py` | 本文に価格印刷なし。3社のadd-up/first/second/kth発動と終了。独立27default年状態CF列挙による3順位のprice | 計算完了。例のnotional/回収・hazardは明示合成入力。本文価格Ex25.3は§25.10で扱う。法的netting/同時defaultの契約規約は別範囲、同時刻は入力順。説明・受入保留 | 5 passed・ruff check/format PASS |
| §25.7 | `_credit_contracts.py` | 本文100m・5年・floating+25bp、+10%→10m/−15%→−15m。独立借入購入のcash accountでcoupon/financing/priceの全CFを照合 | 計算完了。固定initial notionalベースのprice marks、couponは金額。fair spread/信用調整の本文入力なし。calendar/periodic notional resetは別規約。説明・受入保留 | 19 passed・ruff check/format PASS |
| §25.8 | `_credit_portfolio_extensions.py` | 本文100mの5/15/80mトランシェ、loss2mでequity3m、loss6mでequity0/mezz14m。1000/100/10bpの残存元本premium。独立優先順位cash allocationと総損失保存 | 計算完了。整数default件数に変換せず任意金額lossを配分。Table25.6は2007–2009年観測quote入力で再推定しない。既存vol12境界5/15%との差は据置。説明・受入保留 | 7 passed・ruff check/format PASS |
| §25.9 | `_credit_portfolio_extensions.py` | 100社5年PD2%：独立>=1 86.74%、>=10 .0034%、完全相関100社2%/0社98%。独立組合せ和・latent-normal MC6SE、総期待loss保存とtranche再配分 | 計算完了。2%は5年累積PD。rho=1は解析2状態。全層同riskは回収0条件、40%に一般化せず明示。説明・受入保留 | 11 passed・ruff check/format PASS |
| §25.10 | `_credit_portfolio_extensions.py` | Ex25.2/Table25.7/Ex25.3/Table25.8の113印刷値、348/153bp。独立Gaussian default時刻MC6SE、標準quote再価格と単調凹loss curveの4–8%補間 | 計算完了。源60点・未丸めhazard、midpoint default規約。非標準区間はcompound較正の全標準leg/time curveを保存した区分線形補間、PV loss単独からannuityは推測しない。市場無裁定の普遍保証ではなく入力curve制約を検査。説明・受入保留 | 18 passed・ruff check/format PASS |
| §25.11 | `_credit_alternatives.py` | 原典計算結果なし、double-t自由度4。ASB countを独立2^n状態積分、t潜在変数MC、因子依存PD/terminal loss MC、hazard混合を独立default年CF列挙・既知weights回復 | 計算範囲完了。因子依存モデルはPDを再較正した明示合成例、著者の全市場モデル再現ではない。mixtureはfixed hazard gridの静的同質版でquote不足時非一意。CR-11動的モデル・その他全copula・市場parameter不足は研究項目、説明・受入保留 | 8 passed・ruff check/format PASS |

## 残りと検証

- Ch22：8計算項目、§22.7の説明は保留。HSの501日原系列、PCAの2631観測、TN10の原典数値入力は未保有。
- Ch23：6計算項目、§23.4の説明は保留。原系列からの最尤推定と印刷係数からの再帰を区別する。
- Ch24：7計算項目、§24.1/24.3の説明は保留。P/QのPD、年率hazardと累積PD、回収率と損失率の単位を明示する。
- Ch25：11計算項目（本文の定性節§25.5/6も既存の計算部品を検証）。契約支払と経過分、CDOの全体元本/トランシェ元本を区別する。概観にとどまる動的モデルの実装は研究設計が別途必要。

## レビュー対応

- 2026-10-06 R1：既存docstringゲートの3失敗を再現し、7関数に意味・単位・規約を追記。ゲート変更なし。P5の変更4モジュール123 tests PASS、test_docstrings.py 154 passed、ruff check/format PASS。全suiteは再実行していない。
- 2026-10-06 R2：小gammaの巨大noncentralityでNaN/誤値を再現。遠い第2根のtail massが浮動小数の範囲外となる領域では正規分位点を単調枝へ直接写す。正負gamma/linearの16回帰を追加し、market risk 76 passed・docstring対象1 passed・ruff PASS。
- 2026-10-06 R3：EWMA尤度の単峰仮定による局所解を4観測/seed918で再現。uniform+endpoint対数gridで複数極値を探索・精密化し両端と比較。独立20001点grid/ゼロ端点の3回帰、volatility estimation 29 passed・docstring対象1 passed・ruff PASS。数値探索は最適解の一意性の証明ではない。
- 2026-10-06 R4：alpha=beta=0の有効な定数variance推定を予測側が拒否することを再現。day0は初期値、正のhorizonはomega（連続補間のp=0極限）として処理。解析Gaussian MLE→forecast/term vol回帰を追加、volatility estimation 30 passed・docstring対象1 passed・ruff PASS。

- 2026-10-06 レビューchatからの報告：R1–R4は独立再検証済みとしてclose。Ch25.1–25.3（8160c4b6まで）に追加重大指摘なし。同chatが実行したhullkit全suiteは5257 passed・6 skipped・2既存warnings（開始HEAD8160c4b6、実行中の開発継続あり）。この件数は後続全HEADの保証とせず、本chatはP5変更対象のみ再検証する。
