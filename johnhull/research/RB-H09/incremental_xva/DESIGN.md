# 増分XVA＋IM・資本 — 正式設計 v1

2026-10-11 / RB-H09 / **正式設計の独立レビュー承認済み（Critical 0 / Important 0 / Minor 1）。実装・数値結果・資源予算・規制適合・launch・研究受入は未実施。** 元32主cells×3seedsと全範囲を保持し、M1のCSA coverage境界を明確にした。金融実装・測定は#9→#10→#11の順で進める。

正本となる既存調査は [RESEARCH.md](RESEARCH.md)、[独立再レビュー](../../../docs/superpowers/reviews/2026-10-09-next-research-design-rereview.md)。実装工程は [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)。[独立レビュー](design/incremental-xva-formal-design-independent-review-v1.md)と[限定判断](design/incremental-xva-formal-design-independent-decision-v1.json)、レビュー対象候補を原byteで保存した。本正本は状態・参照先とM1を整理した文書で、計算・テスト・金融workerを実行していない。

## 1. 目的と完了の意味

「新しいIRSとヘッジを追加すると、既存bookの信用・担保・資金・IM・資本の費用がどれだけ変わるか」を、法的集計境界と数値誤差を分けて比較する。CVAだけの小例への縮小はしない。

\[
\Delta X(P;a)=X(P\cup\{a\})-X(P),\qquad
\Delta X(P;\{a,h\})=X(P\cup\{a,h\})-X(P).
\]

before、after、standalone、hedge bundleを同じ原始経路で保存する。偏微分marginalとEuler配賦は追加差とは別ラベルの解説・補助比較とし、主表へ代用しない。

完了にはprivate計算、独立参照、主32cells×3seeds、保存値からの数値再検算、独立fresh再実行、C/F各保管庫からの独立復元再検算、全費用・失敗母数、artifact-only教材、数学/金融の独立レビュー、採用/条件付き採用/不採用の記録をすべて要求する。数値integrity、精度、研究採否、実行/資源上限、規制適合は別状態。速度向上やNNの勝利は完了条件にしない。本編306節の件数は変えない。

## 2. 選択する評価規約と代替

| 方針 | 得られるもの・負担 | v1の扱い |
|---|---|---|
| clean Q価格＋明示したdesk cash-cost policy | 法的台帳と増分を追跡しやすい。価格依存の一般的再帰FVAは解かない | 採用候補 |
| Burgard–Kjaer/Green–Kenyonのsemi-replication | own debt/default hedge、資本のfunding利用を一貫して指定する必要がある | 簡約条件の独立対応表 |
| recursive closeout/funding valuation | 内生価格とportfolio増分を再solveするBSDE/PDE | 次revisionの制限 |

銀行から見てclean \(V>0\)は資産、正のadjustmentは費用。単一synthetic通貨、年率decimal、時間ACT/365F、bpはcurrency/基準notional×10,000。

\[
V_{\rm credit}=V_{\rm clean}-CVA+DVA,\quad
A=FCA-FBA+MVA+KVA+COLVA,\quad
V_{\rm desk}=V_{\rm credit}-A.
\]

最後はこのpolicyのinternal transfer value。一般的な市場fair valueとは呼ばない。DVAを交渉chargeへ含めない別表は、計算したDVAを消さず表示規約だけ分離する。phi=0を主条件とし、資本のfunding利用phi>0はreserve勘定と投資収益まで記載した独立validationで扱う。liquidity spreadにDVAやown-debt default windfallを加算しない。

## 3. 基準モデル・商品・安定した依存境界

- 既存 `hullkit._numeraire_choices.FlatHW(a=.2, eta=.01, zero=.02)` のQ OU座標、exact stateとdiscount integralを一貫して使用。一般曲線のHull–White座標を混ぜない。
- 単一OIS、projectionとdiscountのdeterministic basis=0。outerはQ。IMは独立したsynthetic physical/stressed kernel P_IM。P_IMのドリフト0、基準vol=eta、stressは1.5倍、fat-tail対照は0.95 N(0,sigma²)+0.05 N(0,9 sigma²)と固定する。
- annual fixed/simple-floating vanilla IRS。元dated schedule、fixing、settlement、known past ratesを保存。forward-looking single-period couponを使い、backward compounded RFRとして表示しない。
- currency notional N_ref=1,000,000。synthetic calendarは土日休業・休日追加なし、Following、ACT/365F。起点2027-01-04、1/3/5年の原満期を置く。business-day期間とACT/365F期間、規制subsetの250営業日換算を別欄にする。
- #10の多曲線研究は研究実行順序上の先行テーマ。ただしv1の数学・sourceはその新APIに依存しない。接続境界は dated terms、realized fixing ledger、clean marks、discount/projection provenance、legal-set/counterparty IDs。12quotes・market Greeks・roll/fixing四項P&Lは#10の範囲で、v1へ暗黙導入しない。
- #9のtransport/費用の教訓を使うが、その3,138 jobs、source authority、実予算、旧rawを#11へ移植しない。#11独自の元roster/計画/source/入力を実行前に固定する。

## 4. イベント・法的集計・cash ledger

各tradeはtrade_id、counterparty_id、legal_set_id、CSA_id、funding_pool_idを持つ。legal nettingはset内だけ。資金pool集計とcounterparty-wise資本集計は別map。同一counterpartyの別set間でVM/IMを相殺しない。

同日順序は fixing → contractual coupon/upfront settlement → VM/IM call calculation → due margin settlement → default check。default-before-couponの対照も独立anchorへ保存する。pending callはsettled collateralではない。MPOR内はdefault以前の最後のsettled VM/IMを凍結し、新しいcallを実行しない。

VM \(C=\) received−posted。主条件はcash/haircut0/two-way/reusable。thresholdは相手側・銀行側別field、MTAとroundingはtransfer amountへ作用し、before/afterの残高とcall理由を保存。nonreusable VMの対照ではreceived VMをfree cashへ入れない。

IM \(I_p,I_r\ge0\)はsegregated。received IMを資金に使わない。bank-posted IMはcounterparty defaultでbankruptcy remote返却、own defaultではcounterpartyが利用する。excess IMの返還を損失・利益と区別する。

F0はclean/OIS benchmark下のcoupon、upfront、hedge settlement、VM transfer/返還、free cashから得る借入残高（正=借入、負=投資余剰）。初期free cash=0。IRS開始upfrontはclean価格と整合し、par tradeは0。received reusable VMはcashを増やすがcollateral liabilityも記録する。segregated IMとblocked capitalは別勘定としてF0に含めない。benchmark cashはOISでcarryし、excess funding/IM/capital chargeは別費用勘定へ積み、F0へ再帰的にfeed backしない。自己金融・台帳保存は独立cash列挙で確認する。

| 口座/量 | 停止・settlement規約 |
|---|---|
| credit default event | 各setのcounterpartyと銀行のfirst-to-default、契約満期まで。closeout valueはtau+MPOR |
| VM/契約cash | default時はlegal closeoutまで原settlement記録を保持。生存hedgeはその契約満期/別defaultまで残す |
| F0のrunning spread | bank aliveかつpoolの実borrow/investment口座が開いている期間。counterparty defaultだけで生存hedgeを消さない |
| posted IM borrowing | bank aliveでposted IMが未返還の期間。counterparty closeout後1営業日のsynthetic返還lagを主条件とする |
| capital charge | bank alive。defaultしたsetの対象riskはcloseout終了まで、生存setは契約終了まで再算定 |
| own default後 | credit/closeout ledgerは残すが銀行の新規running costを加えない。own debt戦略を一般に解いた主張はしない |

これらは研究policy。停止時刻を一つのsurvival weightへまとめない。price/cash/historyの不一致はsource defect、実時間/メモリ上限での停止はadministrative partialとして別に保存する。

## 5. First-to-defaultとMPOR損失

piecewise deterministic Q hazardsとmarketは独立、同時default確率0。銀行tau_Bを全setで共有し、各counterpartyのtau_Cを共有するset mapを保存する。直接default-time法は同じuniformsからbefore/afterを作る。独立参照はdensity lambda_C S_C S_B（銀行側は逆）と条件付き損失の時間積分。

tau+gのreplacement mark＋tau以降の未払contractual cashを同時点へ運んだM_gap、利息付きC_gapとIMを用いる：

\[
E_C=[M_{\rm gap}-C_{\rm gap}-I_{r,\rm gap}]^+,\qquad
E_B=[-M_{\rm gap}+C_{\rm gap}-I_{p,\rm gap}]^+.
\]

CVA/DVAは各first-default indicator×D(0,tau+g)×LGD×対応claimのQ平均。割引と損失を別々の平均へ分けない。secured部分の回収とunsecured LGD、余剰IM返還、posted IM返還を独立列にする。bank-posted IMをcounterparty損失からさらに引かない。満期直前defaultのcloseout/IM返還は満期後もevent horizonへ含める。

## 6. 非SIMM IM

各時点のset別cum-cash価値変化Delta Piを10営業日のP_IM full revaluationから作る。posted=max(q99(−Delta Pi),0)、received=max(q99(Delta Pi),0)。VaR、ES、Gaussian sensitivity proxyを別methodにする。主32cellsのIMはGaussian full revaluation、stress/fat-tail/ES/proxyはvalidation/challenger。

1 factorでもcoupon fixingを跨ぐ場合、必要なstate/integral/fixingのGaussian rankを実際に数える。1次元と確認できる場合だけquantile-root＋Gaussian積分を主参照にする。非単調revaluationは全root/bracketを分けてCDFを計算し、q=inf{x:F(x)>=p}のleft quantileを採用。eta=0、完全offset、point mass、quantile tail不足を扱う。Gaussian linear anchorはz99 sigmaとphi(z99) sigma/.01の独立式。

1次元に縮約できない場合は原始Gaussian座標を保存した独立cubatureとnested iid MCの対照をpilotへ含め、rank/誤差/費用を明記する。全historyを1–2次元参照と呼ばない。M候補256/1024/4096はnested対照用で、主engineが不要なinner MCを強制しない。quantile不安定・未収束はunknownを保持し、main前に解決/明示計画変更する。

本案は非SIMM。商用係数やライセンス資料を実装しない。現在版SIMMの番号を計算契約にしない。実stress履歴・監督承認・法的契約をsynthetic kernelから推定しない。

## 7. 資本と費用成分

主対象は単一通貨linear IRSのSA-CCR教材subsetとreduced BA-CVA。原典の版と条項を入力manifestへ固定し、未対応商品・同一legal setを複数CSAが覆う未対応の特殊coverage・set間の担保共有・非cash haircutはunsupportedとして全分母に残す。client/dealer別counterparty・別legal setへ各1CSAを割り当てる主bundle d、book全体の正常な複数CSA配置は対応範囲に含む。formula画像の転記/係数レビューは実装前に独立確認する。[固定CRE52](https://www.bis.org/committees/bcbs/basel-framework/standard/cre/52/inforce/2023-01-01/published/2020-06-05)。

SA-CCRはRC/NICA、signed supervisory delta/duration、3bucket、maturity factor/MPOR floor、multiplier floor、margined EAD capを計算。received eligible IMを含むregulatory CとVM-only Cを別fieldで保存し、NICAからsegregated posted IMを除外する。MC quantile PFEと規制add-on PFEを別名にする。K_CCRはsynthetic credit RW×EAD×明示capital ratio（主ratio=.08、RW=.5）である。

reduced BA-CVAはcounterpartyごとのSCVAと全counterpartyの集計をbefore/afterに再計算。銀行全体のcapital/floorsとは呼ばない。non-IMMのeffective maturityはmaster-netting内notional加重残存満期を基礎とし、主商品original maturity>=1年のため一般の1年floorを使い、BA-CVAには5年capを適用しない。empty/matured setはEAD/SCVA0へ落とす。短期例外は別入力eligibilityと原典確認が必要。[固定MAR50](https://www.bis.org/committees/bcbs/basel-framework/standard/mar/50/inforce/2023-01-01/published/2020-07-08)、[CRE32.46–54](https://www.bis.org/committees/bcbs/basel-framework/standard/cre/32/inforce/2023-01-01/published/2020-03-27)。

main \(K=K_{\rm CCR}+K_{\rm CVA}\)。K_CVAはcapital額であり再度.08を掛けない。sector/qualityはsynthetic financial/IGと明示し、対応RW/discount/rho/alphaは固定原典から得る。一般のSA-CVA、full BA hedge recognition、FRTB、leverage、operational/CCP資本は対象外。

running costsは口座ごとの実stop maskとstochastic discountを用いて計算する：

\[
s_bF_0^+-s_lF_0^-+(r_b^I-r_I)I_p+c_KK+(r_{\rm VM}-r_{\rm OIS})C.
\]

FCA、FBA、MVA、KVA、COLVAを別path integralへ保存。主r_VM=r_OISでCOLVA0。c_Kはblocked capitalの運用利息控除後のannual excess charge。負の増分MVA/KVAと非負total IM/Kを両立させる。

## 8. 実験roster

before PはN_refの3年receive-fixed par IRS。固定rateは同じflat OIS・原scheduleのt0 par rate。開始日/schedule/hedge量はmain結果から選ばない。

| bundle ID | 追加するa/h | 比較目的 |
|---|---|---|
| a | 同set・3年receive-fixed a、N_ref | same-direction増分とstandaloneの差 |
| b | 同set・同scheduleの3年pay-fixed a、N_ref | 完全reverse/負増分anchor |
| c | 同set・1年receive-fixed a＋5年pay-fixed h | 異満期same-set IM offsetと残存資本 |
| d | client setに3年receive-fixed a＋dealer別setの3年pay-fixed h、同notional | credit/IM/funding/capital tradeoff |

cのh notionalはaのt0 parallel-OIS DV01を中立にする比で固定し、独立coupon-sumによる中央差分とbond derivativeで照合する。Pのriskまで消す最適化はしない。dのdealer CSAは常にdaily lag1日/MPOR10日/VM+IM・TH/MTA0で、client側CSAだけを主4条件で変える。dealerも同じsynthetic hazard/recoveryから別counterpartyとして再計算する。

主CSA=unsecured、VM immediate/zero-MPOR、lagged VM、lagged VM+IM。主TH/MTA/rounding=0、lag1営業日、MPOR10営業日。zero-MPORは数値anchor。政策L=(sb50bp,sl0,IM excess50bp,cK5%)、H=(sb150bp,sl25bp,IM excess150bp,cK10%)。lambda_C=.02、lambda_B=.01、R_C=R_B=.4。**4×4×2=32主cells、3 independent outer seeds=96主seed-cells**。各cellにbefore/after/standalone/bundleの必要原配列を持たせる。

validation rosterはcと同じhを別non-nettable setへ置く対照を必須にし、既存set IM不変＋新set IM>=0を検査。funding/capital aggregateの便益をIM nettingに読み替えない。他にeta0、lambda_B0、符号両側rate、TH=.02N_ref、MTA境界、MPOR20日、nonreuse VM、IM返還lag変更、phi>0、default-before-coupon、stress/fat-tailを固定IDで登録する。validationを主32cellsの削減/増減に使わない。現時点で符号・便益・優劣の実測はない。

## 9. 私有モジュールとデータ境界（新API候補）

計算は `johnhull/hullkit/src/hullkit/`、公開__init__は変更しない。以下は**提案API**であり現存しない。

| file | 責務/API候補 | 消費→生成 |
|---|---|---|
| `_incremental_xva_contracts.py` | frozen `StudyTerms`, `TradeTerms`, `CSA`, `CostPolicy`; `event_grid(terms, refinement)` | dated/raw terms→不変IDs/axes/event roster |
| `_incremental_xva_market.py` | `clean_irs(trade, time, state, known_fixings, model)`; `hw_driver(terms, normals)` | callerの原normals→state/integral/clean/coupon配列 |
| `_incremental_xva_margin.py` | `conditional_im(book, time, state, history, terms)`; `margin_ledger(marks, im, terms)` | clean/history→call/pending/settled/Ip/Ir/root誤差 |
| `_incremental_xva_credit.py` | `closeout_losses(market, ledger, defaults, terms)` | 共通default/原cash→gap/secured/返還/原loss |
| `_incremental_xva_capital.py` | `capital_profile(book, marks, ledger, terms)` | set/counterparty原入力→RC/add-on/EAD/SCVA/K |
| `_incremental_xva_costs.py` | `cash_costs(market, ledger, capital, terms)`; `paired_increment(before, after)` | 実cash/stop masks→各path費用/差/SE |
| `_incremental_xva_references.py` | `enumerated_cash`, `gaussian_credit_reference`, `normal_im_reference`, `scalar_capital_reference`, `constant_cost_reference` | scalar/独立integral→参照と収束残差 |

辞書recordの数値shapeはmarket=path×event、trade marks=path×event×trade、set ledgers=path×event×set、counterparty资本=path×event×counterparty、path costs=path×component。component順はCVA,DVA,FCA,FBA,MVA,KVA,COLVA。axis IDsとmethod/status/error/stop maskを併記し、配列位置だけでsetを対応させない。同一seedからbefore/afterを生成し、pathごとの差を先に作る。driverはraw normalsを受けるpure計算で、乱数生成は研究runnerだけ。

referencesはproductionのpositive-part/closeout/capital helperを呼び直すmirror実装にしない。既存bond helperはmarketへ再利用するが、独立referenceは直接OU kernelの積分とcash sumsを使う。lagged VM参照はlast-settled/current/closeoutと必要積分・fixingを含むjoint Gaussian条件付きmatrix/rankを明示する。一般historyで低次元保証を作らない。

研究側に `run_study.py`, `check_study.py`, `lesson.py`, `study_plan.json` を置く候補。保存/receiptは既存research artifact契約を再利用し、巨大snapshot全hydrateを必須にしない。1cell/1chunkずつ原全行を検査・解放し、小reportと原artifact referenceを保持する。digestは由来、数値比較はapprox/allclose/SEによる。

## 10. 独立検証・精度・計画固定

| 要求 | 独立参照と必須負例 |
|---|---|
| cash/legal/default | Decimal/Fractionの2state/4path、perspective reversal；別set相殺、未settled VM、posted IM二重控除を拒否 |
| clean/Q discount | IRS bond/FRA/coupon分解、直接Gaussian積分/payment-measure；E[D]E[loss]置換を検出 |
| credit/MPOR | GBM unilateral解析、lambda_C S_C S_B時間積分と直接default MC、coupon跨ぎ；first-to-default欠落を検出 |
| IM | linear normal/quantile全root＋CDF、nested iid対照；tail不足/point mass/未収束をunknown |
| capital | 独立scalar、RC/NICA/floor/cap/bucket境界；MC PFE代用、KCVA×.08、dealer除外を検出 |
| total/increment | 定残高closed integrals、zero hazard/spread/new trade、path差SE；独立SE合成を検出 |
| saved/fresh/restores | 全counts/最後のpath/全component再算出、異source/input/default/control/末尾tamper；missingをPASSにしない |

CRE99 Example1はIRS2本に別通貨swaptionを含む。vanilla IRS部分のduration/delta/bucketの照合だけに原典ラベルを付け、例全体のEAD再現は主張しない。[CRE99固定版](https://www.bis.org/committees/bcbs/basel-framework/standard/cre/99/inforce/2023-01-01/published/2020-03-27)。

pilot候補outer N=4096/16384/65536、nested対照M=256/1024/4096、integration h/h2/h4。日次callと全contract/default/closeout/返還eventはどのgridでも保持。pilotはまず4代表bundles、2状態/極限参照を実測して、全32cellsとvalidationに必要なN/求積rank/order/grid、seed manifest、許容差、予算をmain開始前に固定する。

絶対精度候補はincremental total0.5bp、CVA/MVA/KVA各0.1bp。clean/ref bias、求積tail、default/MPOR/time bias、IM bias、capital境界、MC SE、challenger誤差を別欄にする。MCはpaired差の独立unit sd/sqrt(N)、antitheticはpair平均をunit。nestedはinner/outer両方を変えるreplicate、quantileは必要ならorder-statistic/binomial interval。near-zeroにrelative errorを強制しない。達成不能は黙って許容差/Nを変えず、未解決biasと計画変更理由をmain前に記録する。

## 11. 原始成果・費用・復元・教材

manifestへ全terms/法的map/measure/units/stop times/source+environment/method/seed/grid/全予定・実行・失敗・unsupported分母を保存。原配列はnormals、states、discount integral、fixings/coupons、call/settled VM、Ip/Ir、conditional IM入力/root/収束、default uniforms/times、closeout/損失、cash ledger、capital各途中量、各費用before/after/差、独立unitを含む。再生成seedだけを原数値検査の代わりにしない。

保存検算は原全arraysから総額・差・SE・bps・図を再計算。freshは独立contextで原全条件を再実行し、同一seedの近似数値一致を検査。C/F各vaultは単独で全必須blobを復元し、原pathを安全にrebaseして独立saved numerical check＋教材renderを実行する。receipt/byte PASSは数値受入の代用にしない。original producer sourceと新verifierを使う場合は両source authority/由来を別に記録し、旧rawへ新sourceを付け替えない。

費用対象はcold imports、source登録、reference/生成/IM/capital、fit/selection、pilot/main、全saved/fresh/各restore、serialization、primary/mirror CAS、math/code/research review、教材render。実wall/cpu start/stop ns、process/clock domain、peakRSS、physical/logical bytes、親子includes_children/実包含証拠、失敗/実overrunを残す。inclusive親と子breakdownを二重加算しない。receipt/write/stdout tailや不明費用はpending/Noneの行政行として残し、prefix時計やelapsedのみから全scopeを閉じない。全額採否には同error budgetの準備＋照会費用とbreak-evenを使う。

実予算は未測定。outer/grid/保存/fresh/各復元の部品実測と最大shape保存/読取の実RSSを、独立予算レビュー→root実承認後に固定する。#9の16GiB/30日や測定時間を#11の十分性/ETAへ流用しない。実capはpartial、数値/source例外はdefect。どちらも全母数から消さない。

教材は保存artifactだけを読む `lesson.py`＋3図＋研究notebook。図は①単独/増分/bundleの各成分/totalとSE、②EE/VM gap/IpIr/F/Kの別panel、③error budget/all-in expense/TH/MPOR。方法・policy・synthetic・失敗を表示する。build時のMC/training/network実行を禁止する。

## 12. 採否・到達状態・後続範囲

1. 独立参照と元全条件の数値integrityが通り、誤差目標・全費用・fresh/両semantic restore・教材・最終レビューが揃えば研究v1を完了にできる。
2. fast challengerはreference/core完成後のpolynomial LSだけを候補とする。holdoutはportfolio/schedule/TH/state/MPOR単位。失敗・tail・符号反転をtrainに移して報告から除外しない。
3. referenceが速い/安定ならchallenger不採用でも研究完了。未解決main bias、費用不明、missing restore、未closed reviewは「実装済み/研究未完」で保持する。
4. 制限はflat/一因子/独立default/synthetic P_IM、非SIMM、selected IRS資本、phi0/非再帰policy。WWR、任意曲線、多通貨、実銀行own debt/full capital、実データ較正は別revision。

## 13. 出典と今回の確認範囲

既存取得済み一次論文を再利用：[MVA (Green–Kenyon)](https://arxiv.org/pdf/1405.0508)、[KVA (Green–Kenyon)](https://arxiv.org/pdf/1405.0515)、[Burgard–Kjaer](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2027195)、[recursive funding (Pallavicini–Perini–Brigo)](https://arxiv.org/abs/1112.1521)、[Hull–White FVA debate](https://www-2.rotman.utoronto.ca/~hull/downloadablepublications/FVA.pdf)。これらは評価枠組みの根拠で、本候補のsynthetic数値や現在の法的適合を保証しない。

2026-10-11は不足していた公式CRE99とMAR50のmaturity参照CRE32を一次確認し、既存CRE52/MAR50の固定URLも読取確認。画像数式の完全転記・係数fixtureは実装Task1で独立レビューする。一般のcurrent regulation/SIMM版を新しく主張しない。IM国際比較は [BCBS MGN](https://www.bis.org/committees/bcbs/basel-framework/standard/mgn?allChapters=true)、SIMM境界は [ISDA infohub](https://www.isda.org/isda-solutions-infohub/isda-simm/)の既存調査を参照する。

読取sourceはMODEL_INDEX、`_xva_foundations`、`_numeraire_choices`、`_nonstandard_legs`および既存incremental/funding/HW test。既存公開計算を置き換える計画ではない。候補の新private symbols/runner/checkerはまだ存在せず、ETA・容量・精度・便益は未実測。

## 14. 候補の自点検

- book before/after/standalone/bundle、主32×3、same-set cとseparate-set validation、VM/IM/default/資金/資本境界を保持した。
- received IM資金利用、segregated posted IMのNICA混入、own-default double count、KCVA再8%化、公式mixed例全再現の誤表示を避ける必須テストを指定した。
- Gaussian dimension、stop times、費用prefix/未知、単独vault復元、source由来と数値比較の役割を分離した。
- 追加選択（calendar、fat-tail、返還lag、bundle notionals、policy組）を候補値として明記した。独立レビューとrootによる実行前固定の対象であり、実結果を見た選択ではない。

## 独立レビューM1の反映

主bundle dはclient/dealer別legal set・別CSAを持ち、双方のcredit/IM/funding/CCR/reduced BA-CVAを再計算する。unsupportedは未実装の同一set内複数CSA coverageやset間担保共有に限定し、book全体のCSA個数で拒否しない。Task1/6で、正常なdの正例とduplicate coverageの負例を独立参照と照合する。原32×3・別set対照・dealer資本・失敗分母は維持する。
