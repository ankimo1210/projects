# P3 Ch34 全節：原典要求・TN19・独立教師・実装契約

- 日付: 2026-10-04。**読み取り専用の準備。実装/受入/main統合ではない。**
- root: `/home/kazumasa/worktrees/m29/johnhull`。
- 原典: Hull 11e Global Edition、`options, futures and other derivatives 11th.pdf`、pp773–782。
- 出典草稿: `docs/prep/sections/ch34.md`、`docs/P3_REQUIREMENT_AUDIT_2026-10-04.md`。
- 実inventory: `docs/section_inventory.json`。台帳: `docs/section_ledger.json`。
  **34.1–34.6の6単位、全unreviewed/requirements=[]、draft19要求**。
- 本文抽出: `/tmp/ch34-source.txt`。全10頁をPNGで目視:
  `/tmp/p3-ch34-p773.png` … `/tmp/p3-ch34-p782.png`。
- TN19: `/tmp/p3-input-recovery/TechnicalNote19.pdf`、全1頁を
  `/tmp/p3-input-recovery/tn19-1.png`で目視。全文textも照合。
- 出力: `/tmp/p3-ch34-source-design.md`、`/tmp/p3-ch34-fixtures.py`、`.json`。
- 教師はmath/numpy/scipyのみ、**hullkitをimportしない**。
- repository/Git/製品pytest/browser/D1/releaseを操作していない。
- P3全37節の対象を保持。本準備でaccepted件数を増やさない。

## 1. 原典単位・全要求

| 節 | 実際の節名 | 頁 | draft数 | 依存と範囲 |
|---|---|---|---:|---|
| 34.1 | Variations on the Vanilla Deal | 773–775 | 3 | 29.2/3のschedule/curve。両脚別notional/frequency/daycount |
| 34.2 | Compounding Swaps | 775–776 | 3 | 34.1、couponとcompound rateの別条件、footnote1 |
| 34.3 | Currency and Nonstandard Swaps | 776–777 | 3 | 7/30.1–3、projection/OIS/FX/market-mid整合 |
| 34.4 | Equity Swaps | 777–778 | 3 | 34.1、TR index/reset、canonical TN19とdaily RFRを区別 |
| 34.5 | Swaps with Embedded Options | 779–781 | 4 | 29.3/30.2/32/33、daily binaryとcancelable/compound state |
| 34.6 | Other Swaps | 781–782 | 3 | 商品比較、commodity単位算術、P&Gのpayoff構造 |
| 合計 | 6受入単位 | 10頁＋TN19 1頁 | **19** | 説明部分のD3候補は数値要求の省略を意味しない |

Ch34冒頭は、standard forward-realized/OIS-discount手順と、
convexity/timing/quanto補正やembedded optionが必要な場合の区別を導入にする。
本章に新しい番号付き式34.nはない。TN19には式(1)/(2)、本文にはunnumbered payoff式がある。

### §34.1

| 要求 | 原典要点 | 最小契約 / 教師 |
|---|---|---|
| D34.1-01 | step-up/amortizing、両脚別元本/頻度/daycount、pp773–774 | scheduled notional列、脚ごとのaccrualとpayment、principal exchange有無。各coupon×DF独立cashflow表 |
| D34.1-02 | BS34.1、p774 | fixed100M/float120M、semiannual/quarterly、ACT365/360、source datesを保持。concrete U.S. calendarが未確定ならadjusted datesを原典pinとしない |
| D34.1-03 | projectionとOIS/basis、pp774–775 | referenceごとprojection curveとcurrency OIS discount別入力。same notional/frequencyへ戻してstandard IRSと照合。異なるreference curvesを同一視しない |

source BS34.1:

- trade2021-01-04、effective2021-01-11、termination2026-01-11。
- **Following(all dates)、Holiday calendar U.S.**。
- Microsoft fixedpayer、USD100M、2%、ACT365、Jan/Jul11、first2021-07-11。
- Goldman floatpayer、USD120M、3-month compounded SOFR、ACT360、Jan/Apr/Jul/Oct11、first2021-04-11。
- **sourceに価格はない。contract入力である。**

source「U.S.」だけで銀行/政府証券/株式exchangeのholiday setを識別できない。
fixtureはunadjusted source20quarterly/10semiannual datesと、
weekend-onlyおよび2021-10-11を追加holidayとする**明示synthetic calendar**を保存した。
2021-10-11がcalendarAでは翌日、calendarBでは当日になる例は、
calendar未定義の差を示すもので、実際のmarket calendarを回収したという主張ではない。

定義するdate列:
`unadjusted contractual date / adjusted accrual start/end / observation start/end /
index reset timestamp / fixing availability timestamp / actual pay date / calendar ID`。
Followingで支払だけを動かすかaccrual端点も動かすか、sourceのall datesと整合するよう指定する。
termination2026-01-11を無条件にそのまま営業日と扱わない。

元本が予定済みのamortizingと、34.6のrate-dependent index-amortizingを分ける。
既存IRS scalar-notional APIへstep-upを黙って混ぜず、private typed leg helperに持つ。

### §34.2

| 要求 | 原典要点 | 最小契約 / 教師 |
|---|---|---|
| D34.2-01 | coupon発生/未払残高の利息、pp775–776 | `A_i=A_{i-1}*growth_i+coupon_i`。couponを期末加算してから、そのcouponには同期間growthを重ねない。独立coupon×remaining-productsの和 |
| D34.2-02 | additive/multiplicative compound spread、p776/脚注1 | additive1+(R+sc)α、multiplicative(1+Rα)(1+scα)。sc0/後者はforward-realizedの厳密条件、前者は一般に近似。source LIBOR脚注をdaily RFRへ無条件転記しない |
| D34.2-03 | BS34.2、p775 | 20quarterly計算、両脚terminal一括pay。fixedcoupon2%/compound2.3%、floatcouponSOFR+20bp/compoundSOFR。逐次couponpayとはPVが違う |

source BS34.2はBS34.1と同じtrade/effective/end/Following/U.S.。
双方100M、fixedACT365/floatACT360、quarterly compounding、final2026-01-11一括pay。
fixtureにsource rate構造を使った20period残高表と独立products和を保存した。
曲線とadjusted calendarが未回収なので、これは**synthetic deterministic曲線/unadjusteddates**。
原典印刷price pinではない。

**Example34.1 source inputs:**
3年annualreset、N100M、fixedcoupon4%/compound3.9%、
floatcoupon12monthreference、allforward5%、floatcompoundreference−20bp=4.8%、
OIS4%annual、receivefloating/payfixed。daycountを省いた近似例。

| 状態 | full precision millionUSD | 原典表示 | 規則 |
|---|---:|---:|---|
| first fixedcoupon | 4 | 4 | exact |
| fixed accrued atyear2 beforecoupon | 4.156 | 4.156 | nearest |
| fixed year2 total | 8.156 | 8.156 | nearest |
| fixed beforeyear3coupon | 8.474084 | 8.474 | nearest |
| fixed terminal | 12.474084 | 12.474 | nearest |
| first floatcoupon | 5 | 5 | exact |
| float accrued atyear2 beforecoupon | 5.24 | 5.24 | nearest |
| float year2 total | 10.24 | 10.24 | nearest |
| float beforeyear3coupon | 10.731520 | 10.731 | **truncation** |
| float terminal | 15.731520 | 15.731 | **truncation** |
| PV from displayed balances | 2.8954611401911694 | 2.895 | nearest |

full precision `(15.731520−12.474084)/1.04³=2.8958487426035533`。
通常3decimalroundは**2.896**。印刷2.895を教師へ強制するため計算を曲げない。
source表示経路とfull precision arithmeticを別fixtureとして照合する。
このPVはsourceのforward-realized近似で、unique stochastic-model exact priceではない。

独立3stepQ simple-rate treeの全8pathでsc=0/additiveとsc=0/multiplicativeは
forward-realized価格へ約1e−10USDで一致。
sc−.002のadditiveではforward残差−.7020659USD、sc+.01では+3.5103296USD（N1M）。
multiplicativeの場合はどちらも約1e−10USD。
これはspecified synthetic single-curveモデルでsource脚注の厳密条件を検証する教師。
credit/basis/担保条件まで任意に拡張して同じexact結果を要求しない。

### §34.3

| 要求 | 原典要点 | 最小契約 / 教師 |
|---|---|---|
| D34.3-01 | fixed/fixed、float/float、fixed/float通貨swap、pp776–777 | 各通貨legを各通貨curveで価格→spotFX換算。FX方向/receive-pay/principal初末交換を固定、反転価値は通貨換算後逆符号 |
| D34.3-02 | negotiated market-mid dealはzeroになる曲線整合、p777/脚注2 | 何を校正したか明示（basis/coupon/discountなど）。arbitrary curveを価格0にclipしない。CIP forward換算とspot leg PVを独立照合 |
| D34.3-03 | bondyield/CMS convexity、非standard timing、diff-swap quanto、p777 | 3補正の必要条件を分ける。vol0で補正0、timing/quantoはρ0で1。convexityはρ0だけで消えない |

sourceに新価格例はない。
fixtureのUSD100M/GBP80M/spot1.25、各coupon/curveはsynthetic。
`F_USD/GBP(t)=spot*P_GBP(t)/P_USD(t)`により
`Σ P_USD F_USD/GBP CF_GBP = spot ΣP_GBP CF_GBP`を確認した。
market-mid zeroを作る例は**GBP coupon spreadを校正した**。
歴史的FX basis/collateral曲線を回収したという意味ではない。
sourceの「discount rates often adjusted」はmarket consistencyの記述。
研究拡張で担保・basisを追加するなら具体contract/curveを別定義する。

CMS/timing/quantoはCh30教師の契約を使えるが、関数存在を全商品の受入証拠にしない。
fixtureにも3補正のvol/ρ退化caseと、quanto pay-measure RN積分を保存した。

## 2. §34.4 / TN19 — 契約を分離する

| 要求 | 原典要点 | 最小契約 / 教師 |
|---|---|---|
| D34.4-01 | TR index/配当再投資/resetshares/principal、pp777–778 | shares=L/I_lastreset、total-return indexとprice indexを明確化。frictionless fairfunding/no-lagでreset後net0。一般projection basisで無条件zeroを課さない |
| D34.4-02 | BS34.3同L/schedule、p778 | both100M、quarterly、MicrosoftpayTR/GoldmanpaySOFR。borrowing＋reinvested-index replicationとdiscountedlegsを独立に一致させる |
| D34.4-03 | 既観測RFR/残りforward/途中legPV、p778/TN19 | LIBOR knowncouponとRFR knowncompoundproductを別state型にする。source L(E−E0)/E0を単独legPVや一般netMTMへ無条件採用しない。payment/observation/calendar/dividends/curveを固定 |

source BS34.3:
2021-01-04 trade、Jan11 effective、2026-Jan11 maturity、Following(all dates)/U.S.、
双方USD100M、Microsoft equitypayer、**Total Return S&P500**、Goldman3month compoundedSOFR/ACT360。
Jan/Apr/Jul/Oct11 pay、first2021-Apr11。
I0は直前paydateのindex、最初は2021-Jan11のindex。
原典にI fixing数値、SOFR dailyseries、swap価格はない。

### 2.1 canonical TN19 source catalog

- タイトル **Valuation of an Equity Swap**、John Hull、Technical Note19、1頁。
- bytes34858、PDFmagic`%PDF-1.4`。
- SHA256 `fbd0c0b8bb7051bb988f2a2add19dd41cba1b2a8366cb8e69a13f7e9ecb84356`。
- author教材を保存するRotmanFinHub officialarchive:
  `https://github.com/rotmanfinhub/john-hull-textbook-resources`。
- fixedsourcecommit `9b8dbfe37661dbd3de65d3a1489dc1297e840de7`、
  blob`a438ff4e383d56c15cedc10226de23abe662ea7f`。
- fullsource URL/download recordをfixtures JSONのsource_catalogへ保存。
- archived README/個別PDFの著者帰属・利用条件を保管庫へ引き継ぐ。
- 旧Rotman HTMLerrorをPDF取得成功と扱う問題は、このcanonical source回収で解消。
  ただし**LIBOR契約の式がSOFR契約の式へ自動変更されたという意味ではない**。

### 2.2 TN19 の定義と複製

R0=前resetで既に決まった次回floatingcoupon rate、
τ0=前reset→次payの全accrual、τ=現在→次payの残期間、
E0=前resetindex、E=現在index、R=残期間LIBOR(simple annual)、L=principal。

式(1): 現在borrow `L E/E0`、indexへ投資。
次payの株式 `L E1/E0` と借入返済 `L E/E0 (1+Rτ)` の交換はcostless。
式(2): actualswap両脚へ同じLを加え、
株式 `L E1/E0` と既知 `L(1+R0τ0)` の交換にする。
従ってreceiveequity net:

`V_eq = L E/E0 − L(1+R0τ0)/(1+Rτ)`。
receivefloatingは逆符号。
R0/τ0とR/τは別変数。R0を残期間forwardへ書換えない。

TN19はsingle financing curveの単純複製でP=1/(1+Rτ)。
現代のknownLIBOR coupon＋OIS discount契約なら、nextperiodの式は
`L E/E0 − L P_OIS(t,T)(1+R0τ0)`。
この場合LIBOR projection curveから取るRをOIS discountに代用しない。
projection/funding basisがあるならfuture reset後tailの価値も一般に0ではない。
TN19の「後続resetで価値0だからnextcouponだけ」を無条件に多curveへ拡張しない。

### 2.3 単独 equity leg、本文の表現、net MTM

配当再投資index Iが同通貨でtradable、pay/observation=Tなら
`E_Q[D(t,T) I_T]=I_t`。
従って単独次回equitycouponの正確PV:

`PV_equity = L[I_t/I0 − P_d(t,T)]`。

TN19 floatingcouponなら`PV_float=L R0τ0 P`、
`PV_equity−PV_float=L I/I0−LP(1+R0τ0)`となりcanonical noteと一致する。

**原典p778の表現 `L(E−E0)/E0=L(I/I0−1)` はcurrent index accrued change**。
単独equitylegPVとの差は`L(1−P_d)`。
一般netMTMとしても、TN19との差は`L[P(1+R0τ0)−1]`で消えない。
この差を説明なしに「financing調整済net式だから正しい」と断言しない。
原典式・canonical note・無裁定leg導出・各式の限定条件を並べて教材化する。
sourceの表現不一致を捏造したpricepinで隠さない。

fixture例（**synthetic**）:
L100M、I/I0=1、R0=.045、τ0=.25、R=.05、τ=.125、P=.9937888198757763。

- source currentindexchange0。
- 単独equitylegPV+621118.01242237 USD。
- 既知LIBORcouponPV1118012.42236025。
- netreceiveequity−496894.409937876、receivefloatは逆。
- independentleg−TN19式のfloat誤差最大1.12e−8USD（L100Mの桁落ち）、
  financingexchangeのPVは0。

### 2.4 backwards RFR：known productとprojection/OIS

A_known=`∏ observed(1+r_i*d_i/360)`、G_proj=remainingperiodのpay-measure expectedgrowth。
same equityobservation/pay=T、次の浮動couponは
`L(A_known G_future−1)`。

`PV_RFR = L P_d(t,T)[A_known G_proj−1]`。
`V_next,receiveequity = L I_t/I0 − L P_d(t,T) A_known G_proj`。

same riskfree rolling-bank-account/OIS、no observation shift/lockout/paylagなら
`G_proj=1/P_d(t,T)`、従って**net=L[I_t/I0−A_known]**。
A_knownを1に戻すと途中accruedovernight利息が落ちる。
`A_known−1 + G_proj−1`と足し合わせるとcross term
`(A_known−1)(G_proj−1)`が落ちる。

projectionとdiscountが別なら、G_projはその投影契約から求める。
単純curve-ratioを本当に使えるか、lookback/lockout/observation shiftとの整合を検証する。
この式はまず**nextperiod net**。
後続periodのreset後PVが0にならないbasis契約ではremainingtailを別途評価する。
fixtureはdeterministicprojection .047/OIS .04でtail2periodを保存し、
nextperiod式をfullswapvalueと誤表示しないようにした。

known rates(.035,.036,.034,.038)、各days(3,1,1,2)のsynthetic A_known
=**1.000697391019808**。これはactualSOFRseriesではない。
データ不足を埋める原典価格再現に使わない。

### 2.5 独立stochastic teacher

Q Ho-Lee futurebank積分J、Var(J)=η²h³/3、
TRindex`I_T/I0=(I_t/I0) exp(J−σI²h/2+σI Wstock)`、
discount`D=exp(−J)`、futureRFRgrowth`exp(J+basis*h)`。
同じbankからOIS curveとRFR観測模型を作り、Qでpathwise割引する。

- `D*future_growth=exp(basis*h)`をpathwiseで確認。
- equityPV=`L(I/I0−P)`。
- floatingPV=`L(A_known exp(basis*h)−P)`。
- net=`L(I/I0−A_known exp(basis*h))`。
- source0basis/no-lag模型ではresetstateI/I0=A_known=1でnet0。
- nonzero basisでは無条件reset0を課さない。
- correlated equity/rateを使う262144path、8MCrecordの最大誤差約1.256SE。
- independentdiscountedstock normal求積も保存。hullkit numeraire部品を教師に使っていない。

dividend teacherはprice100→98(dividend2)→102。
reinvested shares1→1.0204081633、TRindex104.0816326531、
price-only return2%、nonreinvestedcashdiv return4%、TRreturn4.08163265%。
単にprice indexへdividendを二重加算しない。

### 2.6 timing/calendar/observation の必須契約

- indexresetdate、indexobservationdate/timeとactualpaydateを別に持つ。
- TRindexは配当再投資済み。priceindexならdividendcash/reinvestmentが別契約。
- RFRaccrualstart/end、ACT360、businessintervalの日数weightを保持。
- fixing publication遅延とvaluation時点のavailabilityでknown/unknownを判定。
- 「payment直後zero」は両脚が実際に決済済みの条件。observation/resetだけ先に来る
  paylag契約ではold couponのpending receivableを残し、resetで0に消さない。
  fixtureはoldperiod cash3M→両脚決済→newreference104/Aknown1/newPV0のsynthetic遷移を保存。
- Following休日調整とequity観測calendarが一致するとは仮定しない。
- lookback/observation shift/lockout/paymentlagをsourceが未指定なら値を勝手に足さない。
  standalone studyで0を仮定するなら明示synthetic contractにする。
- backwardcompで同じrateがFriday→Monday3日に適用される場合、
  observation日数とinterestdayweightを混同しない。
- valuationがaccrualinterval途中なら、knownfactorへの部分日割当規約を固定。
  3day simplefactorを独立3個の1dayfactorへ無断で置換するとcross interestが入る。
- paylagありではequityobservationTをpayTstarへ単に入替えない。
  deterministicsamecurveならlagfactorを導けるが、stochasticrateならCh30timing/measureが必要。
- lookbackでreferencegrowth≠bankgrowthとなるsyntheticfixtureは、
  同じcurve名でもresetnet0を保証しないことを示す。

## 3. §34.5 — 全stateを保持する

| 要求 | 原典要点 | 最小契約 / 教師 |
|---|---|---|
| D34.5-01 | rangeaccrual normalQL n1/n2→conditionalQL n3/n2、p779 | n1=allcalendardays、n3=belowcutoffdays、n2=daysinyear。savedbinaryQL/n2。holidayはpreceding business fixing（脚注4）。日次日数/年basisとthreshold equalityを指定 |
| D34.5-02 | N(d2*)binary、natural/actualpay measure、p779 | natural=ti+τ、actual=si。meanへtiming補正、actualDF使用。positiveBlackdomain。alreadyknown fixingはindicator。GaussianRN積分とclosed probability |
| D34.5-03 | cancelerとoffsetdirection、p780 | ownreceivefixedcancel→longpayer、counterpartycancel→shortreceiver。exerciseafterpayment、remaining identicalswap。single date European、複数Bermudan |
| D34.5-04 | compoundingcancel残高/floatpar/4step近似、pp780–781/脚注5 | Afloating/Afixedとknownstate、解約時は未払残高を決済。literalzero exercise rewardへしない。par shortcutはaccrued/remaining exposure定義が前提。spreadによるexercise影響を省く4stepは近似 |

source contracts（価格pinなし）:

1. accrualfixedcouponQはSOFR<2%の日だけ発生、quarterlySOFRを交換。
2. 10y receive6%swap、自分にyear6cancel権→long **6×4 payer European swaption**。
3. 5y semiannual receive6%、counterpartyがyear2→year5のpaydatesでcancel権→shortreceiver Bermudan。
4. compoundingcancel時、両脚はその日までのcompoundbalanceを即時決済。

accrualではsourceがbelow(<)とabove(>)を使い、continuous modelではequalityprobability0。
quantized actualfixingがstrikeと同値なら具体inclusive/exclusive ruleが必要。
本fixtureはbelow<、saved complement>=を明示し、sourceにないequality慣行を原典pinにはしていない。
週末のratecarry、同値2%例、normalcoupon=conditionalcoupon+binarysavingsを保存。

binary式:
`day_amount=QL/n2`、
`d2=(log(F/K)−σ²ti/2)/(σsqrt(ti))`、
`PV_binary=day_amount P(0,si)N(d2*)`。
sourceのvolσiとactualpaydate siをコードで同じ変数名にしない。
両満期natural/actualはfixingより後。general reference tenorだと
actualpayがnaturalpayより前もあり得るため、signed timing differenceを固定する。
sourceの通常overnight例ではtiming correctionはsmallでoften ignoredだが、検証で0に強制しない。

### independent stopping teachers

3stepQ simple-rate tree、8paths、cancelat1/2、6decisionnodes→全64policiesを列挙。
primitivepathcashflow×discountから全policy価格を計算し、別のconditionalrollbackと比較。

- plain receivefixedbase15111.6950193、owncancelmax28022.1282292、counterpartycancelmin−9200.5446270。
- ownoptionpremium≥0、counterpartyoptionpremium≥0、方向が逆。
- compounding interest only final/cancelsettlement型で、
  no-spread ownmax27756.9184295、counterpartymin−11251.0478301。
- +1%compoundspread ownmax28437.5256369、counterpartymin−10874.7637701。
- exhaustive vs rollback差最大3.64e−12USD。
- 小木価格はsynthetic。source6×4/5yearBermudanのoriginal priceを作ったという意味ではない。

**fullbalance conventionのparの意味:**
riskfreecoupon/compoundのfloat accruedがAfなら、terminalprincipalを両脚へ加えた
fullfloat PVは**L+Af**。未払過去利息を含む全額がliteral Lになるわけではない。
current accruedを分離したremaining exposureがparL。
fixed側も同様にknown Afixを分け、cancelthresholdを整合させる。
fullstateでcancelのcashはAf−Afix。元本Lを両脚へ同時加えること自体はnetPVを変えない。
sourceのpar shortcutを採用する際はこのstate/残高分離の契約を明示し、
unpaid accruedを落としたzero-reward Bermudanへ置換しない。

### 原典4step spread近似を保存

1. 各canceldateのfloatingPVをforward-realizedで作る。
2. 同じobserved残高を保持し、futurecoupon/compoundをriskfreeとしてfloatingPVを作る。
3. excessをvalue_spreadsとする。
4. fixedvalueからspreadsを引いてcanceldecisionを行う。

fixtureではstateごとに1–4、forwardprojection残差、既知Af/Afix、cancelsettlementを保存。
fixed remaining proxy=`PV_aug_fixed−Afix_known−value_spreads`、thresholdL。
no-spread remaining-floatはpar、full accruedfloatはL+Af。
source脚注5のとおり、futurecompounding spreadがexercise decisionを変える効果を省く近似。
exact fullstate stopping教師を残し、4step価格をstrict exactとしてassertしない。

couponへのspreadをriskfreeでcompoundする場合は、spreadcashflowをfixed側へ移す
**pathwise algebra**も全8pathsで確認。compoundrateへのspread追加とは違う契約。
既存stock LSMをそのまま金利payoff/measureへ転用しない。
LSMを使うならexercise-state、discount、calibration、independent pricing pathsが必要。

## 4. §34.6

| 要求 | 原典要点 | 最小契約 / 教師 |
|---|---|---|
| D34.6-01 | index-amortizing/MBSとcommodity、p781 | futureinterestが低いほどprincipal減少大。scheduledamortizingと別。commodityquantity×unitprice、100000bbl/5M→50USD/bbl |
| D34.6-02 | asset/TRS/CDS/vol/varianceの他章参照、pp781–782 | 原資産/受払/元本・時価/credit-event比較。本文参照はassetCh24、TRS/CDSCh25、vol/varianceCh26。repo別研究章も区別 |
| D34.6-03 | BS34.4 P&G spread/payrate、p782/脚注6 | CMT百分率比、Treasurycashpriceper100、spreadはdecimalrate。givenCP6%/spread.1→pay15.25%。歴史データなしでactualpriceを捏造しない |

commodity exampleはannual100000barrels、annual5M fixed、10y→50USD/bbl。
consumerとproducerのreceive/payを反転する。source数量単価pinであってswapPVではない。

P&G source:
1993-11-02、5y semiannual、N200M、BTpay5.30%、
P&Gpay meanobserved30dayCP−75bp+spread、first1994-05-02spread0、残9paydates。
`spread=max(0,(98.5*(CMT5/.0578)−Treasury_cash_price_per100)/100)`。
Treasury6.25%coupon/maturity2023-Aug、bidaskmid cashprice。
**spread.1は10%rate、10bpではない**。
givenCP.06ならpay=.06−.0075+.1=.1525（15.25%）。
fixturesurfaceのCMT/TSY価格はsynthetic。sourceにactualseries/valuationpriceはない。
歴史的事件の当時記述を現在のmarket統計として掲載しない。

## 5. 既存APIと新private契約

| 既存部品 | 使用できる範囲 | 欠ける契約 |
|---|---|---|
| swaps.irs_value_bonds/irs_value_fras | constantnotional/seasoned/first_accrual | 2leg別schedule/notional/multi-referenceとall-datecalendar |
| swaps.currency_swap_value | fixed currencylegs＋spot aggregate | floatprojectedlegs/market-midbasis/collateral/curve separation |
| rates.discount_factor/forward_discount | discount/projection曲線比 | curve role/時点/daycountをtyped契約で指定 |
| rfr.BusinessCalendar/RFRConvention | explicitlyprovidedcalendar、lookback/lockout/obs-shift部品 | source「U.S.」holidayseries、全Following schedule/index timestampは自動取得しない |
| rfr.daily_accrual_schedule/compounded_rfr/rfr_coupon | knownratefactor/dayweights/実績coupon | remainingmodel/MTM/eqreset契約。knownfractionを教師から構築 |
| rfr.RfrCurve/MultiCurveScenario | separatecurve/basis/DFの一部 | full equityswapのnext＋tail/value0条件ではない |
| ir_options.swaption_black | European payer/receiver | regularcanceloffset限定。Bermudan/compoundbalance/terminationcashなし |
| hull_white.hw_jamshidian_swaption | positivefixedcoupon European教師 | dailyaccrualbinary、multi-exercisefullstate、compoundingは別scope |
| trees/exotics/stockLSM系 | underlyingstock option部品 | 金利state/curve fit/numeraire/accruedsettlementにそのまま適用できない |
| volatility/variance/CDS等既存 | 他章商品比較への参照 | Ch34具体contractの受入を代用しない |
| vol07教材 | swaps/dv01/別条件compounding/定性説明 | sourceBS termsheets、TN19/RFR中途MTM、embeddedstate教師が未充足 |

最小private追加案（repo未変更）:

- `_swap_contracts.py`: 2legのNotionalSchedule/CouponSchedule/ProjectionRole/DiscountRole、
  raw/adjusted/accrual/observation/paymentdates、explicitcalendar。
- `_compounding_swap.py`: coupon/spread/compound更新、remainingproducts、
  sourceprinted path/fullprecision、knownbalances。
- `_equity_swap.py`: **LiborResetState と BackwardRfrResetState を別型**、TR/priceindex、
  knownfactor、nextperiodlegs/net、futuretail、side、resetparの条件。
- `_embedded_swap.py`: dailybinarycalendar、natural/actualmeasure、
  cancellationafterpayment、full accruedsettlement、state/side/sourceapproxfields。
- ソース教材builderは各節ID別。shared numerichelperで19要求を一括N/Aにしない。

新public APIや依存追加は既定にしない。既存入口と挙動を黙って変えない。
validationはfiniteordereddate/vector、positivecompoundfactor、positiveDF/notional、
matchingcurrency/dimension、knownfixing availability、positiveBlackdomain、normal/shifted代替、
contract-defined threshold boundary。negativecurve/rateを全モデルで一律拒否しない。

## 6. 準備結果・pending・引渡し

- 印刷output/算術pin **13/13一致**。Ex34.1のfloat2残高はtruncation、PVはprintedcashflows経路。
- TN19全1頁SHA/変数/式1/2/net両方向を回収確認。LIBOR−RFR契約差の教師を作成。
- sourceCh34全10頁画像と19draftIDsを照合。
- stochasticbank/TRindex独立MC最大約1.256SE。
- currency spot/FXforward分解差0。
- binary RN probability求積−closed差1.11e−16。
- compoundedcouponremainingproductsとrecursion、couponspreadmove、全policyenum/rollbackを照合。
- 正式製品コード/requirements台帳/教材UI/証跡/五軸受入/D1は未実施。

**入力pendingを保持:**

1. sourceBS34.1–3のconcrete U.S. calendar、equityfixing/観測/支払lag等。
   explicit study assumptionsを足す場合はsynthetic contract。actualholidayreplicationと呼ばない。
2. BS34.3 actualindexfixings/dailySOFRは原典に掲載なし。
   教材検証はsynthetic複製で可能だが、originalpricedreplicationの達成を宣言しない。
3. P&G historicalCMT/TSY/CPseries/valuationpriceは掲載なし。
   15.25%のconditional算術と当時price再現を別にする。
4. p778のequityleg表現はTN19/discountedleg導出と区別した注記が必要。
   無裁定の式を本文のliteralprice式と同一だと扱わない。
5. compoundingpar shortcutはfullaccrued/remainingstateの定義を先に固定する。

Ch34.1→34.2/34.4のschedule/stateを共有し、34.3はCh30、34.5はCh32/33へ接続。
private実装→独立数値→source/contract/UI証跡→各節requirements→レビュー/受入の順。
P3全37節からCh34の6節を落とさず、原典不足をsyntheticoriginalpinへ置換しない。