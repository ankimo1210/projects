# P6 ロジック先行の実装状態

更新2026-10-06。目的：Ch1–9（台帳80項目）の計算ロジックを実装する。下調べの計算54項目（混在節と§3.appendixを含む）、説明中心26項目を区別する。旧監査の定性31とは分類基準が異なる。

- 完了条件：本文の式・数値例を既存節メモで確認し、private計算部品、本文再現と別方法の独立検証をそろえ、変更モジュールのtests/ruffを通す。本文入力が足りない部分は不足と計算範囲を明記する。
- 計画は節メモの数行、1節1コミット（P6 §xx.y）。新公開API・依存追加なし。コード・節メモ/索引はcodex/p6-logicへ節ごとpush、mainは進捗文書のみ。
- 正式受入：P6 0/80、全体33/306。説明・教材・画面・台帳更新・章受入・全suite・D1・両保管庫は保留。
- 現在：計算54/54。次はP6対象54項目の最終照合。Ch1→9を順に継続する。

## 節別の実装

検証件数は当該節完了時の変更モジュール累計で、合算しない。

| 節 | 実装ファイル | 再現した本文の数値／独立検証 | 未解決の点 | 対象検証 |
|---|---|---|---|---|
| §1.3 | `_intro_contracts.py` | £1m ask1.2230→支払1,223,000、long77,000/−23,000・単位.077/−.023。$60年5%→63/利息3・forward67/58→gain4/5の全9値。独立1期木のQ期待/2状態replication | 計算完了。年5%は1年単利/年複利、連続複利を混ぜない。満期payoffと現時点価値を区別。逆carryはinventory/shortingの仮定。市場quoteは2020年入力。説明・受入保留 | 3 passed・ruff check/format PASS |
| §1.5 | `_intro_contracts.py` | Apple call premium2030/payoff6000/profit3970、short put premium1270/支払4000/損失2730の6値。独立lognormal payoff積分と解析call/put期待値 | 計算完了。premium込みprofitとpayoffを区別。2020年の72market quotesはモデル出力の正解表にしない。数量=契約数×倍率、金利/手数料は原典で無視。説明・受入保留 | 7 passed・ruff check/format PASS |
| §1.7 | `_intro_contracts.py` | FX支払12,225,000/受取36,660,000、無ヘッジ12m/13m。put1契約100・10契約1000、最低27,500・費用後26,500の全8値。独立受払と解析lognormal保有価値 | 計算完了。pay/receiveのcash符号、保有価値と購入時からの利益を分離。FX bid/askとquantity単位、金利なしのpremium費用。説明・受入保留 | 10 passed・ruff check/format PASS |
| §1.8 | `_intro_contracts.py` | Table1.4/1.5の全13値（305500/20000、19500/19425、−5500/−5575、700/−500、4.5/9000/7000/−2000、10倍）。独立解析lognormal期待と固定seed MC6SE | 計算完了。金利/手数料なし、marginは費用ではない。fractional数量は理論上の比較。説明・受入保留 | 13 passed・ruff check/format PASS |
| §1.9 | `_intro_contracts.py` | NY120/London100GBP/FX1.23/100株→300。独立USD/GBP収支の線形方程式、手数料とGBP/pence座標変更 | 計算完了。同一株・同時執行と入力quoteの売買方向を仮定、現行裁定機会の判定ではない。説明・受入保留 | 15 passed・ruff check/format PASS |
| §2.4 | `_futures_market.py` | Table2.1全53値。独立当初＋累積損益＋累積入金で全日を検算 | 計算完了。利息/余剰引出しなし、最後のcallはpendingで未入金。説明・受入保留 | 2 passed・ruff check/format PASS |
| §2.6 | `_futures_market.py` | 金(1725.5−1752.1)×100=−2660。独立Decimal購入/売却収支とcents換算 | 計算完了。low1713.3/1715.3の原典不一致は採用せず。2020market表は入力、現行情報ではない。説明・受入保留 | 4 passed・ruff check/format PASS |
| §2.10 | `_futures_market.py` | 2020/2021通常1000/500、hedge2021に1500。独立最終売買収支と期間配分 | 計算完了。hedge指定はこの歴史的例の配分規約、実際の資格判定/税法を実装しない。説明・受入保留 | 6 passed・ruff check/format PASS |
| §2.11 | `_futures_market.py` | 16契約・200000・1.3333。独立望遠鏡和と区分金利の解析cash終価 | 計算完了。日次経路はsynthetic、終価差は利益実現時点の効果で価格のconvexityモデルではない。説明・受入保留 | 8 passed・ruff check/format PASS |
| §3.1 | `_futures_hedging.py` | 原油1000枚/4/4M/49M/−6、銅4枚/5000/325000/320000/−15000/305000。独立cash状態列挙 | 計算完了。終了時S=F、日次資金繰りなし、銅cents換算。説明・受入保留 | 2 passed・ruff check/format PASS |
| §3.2 | `_futures_hedging.py` | 原油49→59のshort損失10M。独立売上/原料/先物cash、転嫁あり/なしの符号 | 計算完了。転嫁率は合成の経済条件、事後利益と事前risk削減を区別。説明・受入保留 | 4 passed・ruff check/format PASS |
| §3.3 | `_futures_hedging.py` | .30/.10/2.30、JPY4枚/.055/−.005/1.075c/537500、原油20枚/1.10/.90/48.90/978000。独立cash/交差basis分解 | 計算完了。basis=S−F、JPY quoteはcents、sell/buyのcash符号を明示。説明・受入保留 | 6 passed・ruff check/format PASS |
| §3.4 | `_futures_hedging.py` | 全9値: SD .0313/.0263、rho .928、h .78、37枚、VA2.2M/VF54600/32.23/32枚。独立OLS/分散min、tailingは補足 | 計算完了。ddof1、日次例.8をhと解釈するためSD比1を仮定。tailing30.70は原典外。SD/rho/hの許容差を各表示桁の半単位に分けて確認。説明・受入保留 | 14 passed・ruff check/format PASS |
| §3.5 | `_futures_hedging.py` | Table3.4全25値＋252500/20/30/15short/10long、stock picking2M/105000/20.95/21/−200000/262500/62500。独立CAPM factorとcash | 計算完了。ドル値±1、market table日付混在は留保。beta0に残差riskがない保証はしない。説明・受入保留 | 10 passed・ruff check/format PASS |
| §3.6 | `_futures_hedging.py` | 100枚/.80/.50/.40/1.70/現物下落3.00。独立全6売買cash列、47.70は導出値 | 計算完了。利息/roll費用なし、信用/流動性riskと価格hedgeを区別。説明・受入保留 | 12 passed・ruff check/format PASS |
| §3.appendix | `_futures_hedging.py` | beta0→5%、beta.75→11%。独立OLS/2状態期待、portfolio covariance線形性 | 計算完了。期待marketと実現marketを区別しCAPMの1期仮定を記録。説明・受入保留 | 14 passed・ruff check/format PASS |
| §4.2 | `_rates_foundations.py` | 原典に印刷数値なし。式の日数1/3/1手計算と定率閉形式、独立Decimal再投資 | 計算完了。day weightsはcaller指定、制度/最新参照金利は対象外。説明・受入保留 | 2 passed・ruff check/format PASS |
| §4.4 | `_rates_foundations.py` | Table4.1六値、連続110.52、10.25%/5.96%、9.758%/8.08%/20.20の全12値。独立成長係数 | 計算完了。年率quoteと支払frequencyを分離、Ch1単利と混ぜない。説明・受入保留 | 4 passed・ruff check/format PASS |
| §4.5 | `_rates_foundations.py` | 100/5年zero5%→128.40。独立現金成長ODE、DF積の無裁定 | 計算完了。連続複利、Ch4はday countなし。説明・受入保留 | 6 passed・ruff check/format PASS |
| §4.6 | `_rates_foundations.py` | 98.39/6.76%、DF .87284、annuity3.70027、par coupon6.87。独立Newton/価格root | 計算完了。年couponは額面100あたりcash、全率continuous、par機能はprivate。説明・受入保留 | 8 passed・ruff check/format PASS |
| §4.7 | `_rates_foundations.py` | Table4.3 yields5値/Table4.4 zeros5値、DF.96631/1.25年2.255%/補間価格108.5。独立DF線形/zero非線形同時solve | 計算完了。一般cash datesはcaller指定、linear zero/flat端、半期固定公開APIは変更しない。説明・受入保留 | 11 passed・ruff check/format PASS |
| §4.8 | `_rates_foundations.py` | 5.0/5.8/6.2/6.5%、6.2%例、103.05/108.33/114.80/122.14、curve play2.3%。独立cash/解析微分 | 計算完了。linear zeroの柱で微分は平均、期待将来金利とforwardを同一視しない。説明・受入保留 | 13 passed・ruff check/format PASS |
| §4.9 | `_rates_foundations.py` | 125000（2.25年）/Ex4.3 369200（369246.54、表示丸め）。独立2債券replication/前払再投資 | 計算完了。fixed/forwardは期間単利、discountだけcontinuous。前払額は補足。説明・受入保留 | 15 passed・ruff check/format PASS |
| §4.10 | `_rates_foundations.py` | Table4.6全22値＋Ex4.4三値/Ex4.5八値。独立continuous/periodic価格差分とportfolio PV重み | 計算完了。丸め前のduration使用、1bpはquote軸に対する感応度。説明・受入保留 | 18 passed・ruff check/format PASS |
| §4.11 | `_rates_foundations.py` | 印刷数値なし。Table4.6補足C7.570/2%価格変化と独立2階差分、同Dの分散CF、3moment免疫 | 計算完了。補足例はsynthetic、平行yield quoteでの小変化、非平行riskは残る。説明・受入保留 | 20 passed・ruff check/format PASS |
| §5.2 | `_forward_pricing.py` | 60000/500/50000/9500。独立3CFとlong符号反転 | 計算完了。借株料は原典0、呼戻し/証拠金は説明範囲。説明・受入保留 | 2 passed・ruff check/format PASS |
| §5.4 | `_forward_pricing.py` | 40.50/2.50/1.50、bond948.79、strip70.70/.70。独立借入ODEと2方向cash carry | 計算完了。金利はforward満期のzero、負金利でF>Sを仮定しない。説明・受入保留 | 4 passed・ruff check/format PASS |
| §5.5 | `_forward_pricing.py` | I39.60/残860.40/F886.60/益23.40/16.60、配当PV2.162/F51.14。独立coupon充当借入solve | 計算完了。満期後income除外、途中丸めなし、known額とyieldを分離。説明・受入保留 | 6 passed・ruff check/format PASS |
| §5.6 | `_forward_pricing.py` | q=2log1.02=3.96%、F25.77。独立借入額/再投資数量、単位carry | 計算完了。q=.04直入れを避けcontinuous換算、税/貸借料なし。説明・受入保留 | 8 passed・ruff check/format PASS |
| §5.7 | `_forward_pricing.py` | F26.28/f2.17、16契約/満期4000。独立spot/割引債と反対forwardの確定cash | 計算完了。BS5.2 ±3900は金利がなく再現対象外、PV4000の構造のみ。fとFを分離。説明・受入保留 | 10 passed・ruff check/format PASS |
| §5.9 | `_forward_pricing.py` | Ex5.5 1313.07。独立満期basket数量とfunding、symbolic5S/5QSの通貨換算 | 計算完了。qは期間平均continuous、quanto価格はCh30既存機能の範囲。説明・受入保留 | 12 passed・ruff check/format PASS |
| §5.10 | `_forward_pricing.py` | F.7206、1061.84/743.29/765.15/21.87、1333.33/1075.99/1020.20/55.79、概算.8%。独立2通貨借入/換算 | 計算完了。AUD1415.79は正確値1415.782062→1415.78と1cent差。中間丸めを再投入しない。説明・受入保留 | 14 passed・ruff check/format PASS |
| §5.11 | `_forward_pricing.py` | U1.865/F484.63。独立S終価+期末2cash、便益yieldの上限/逆算 | 計算完了。consumptionではcash carry値は上限、convenience推定は入力依存。説明・受入保留 | 16 passed・ruff check/format PASS |
| §5.12 | `_forward_pricing.py` | 印刷数値なし。無収入/index/FX/storage/consumptionの全式、独立cash/数量終価と価値 | 計算完了。consumption式はconvenience input条件付き、上限と区別。説明・受入保留 | 18 passed・ruff check/format PASS |
| §5.14 | `_forward_pricing.py` | 印刷数値なし。k=r/正負systematic premiumの3式。独立DCF root/固定seed期待MC6SE | 計算完了。P期待とQ価格を区別、日次決済なし、Fから真の期待を一意推定しない。説明・受入保留 | 20 passed・ruff check/format PASS |
| §6.1 | `_rate_futures.py` | 124/184/122/180、2.6957/2.7111、1/3日、bill2.0222/2.064%/4、120156.25、54/181/1.64/157.14/157140。独立月表/Fraction | 計算完了。30/360はFeb EOMなしのbond basis、現金157140はprice小数2桁からの表示。説明・受入保留 | 2 passed・ruff check/format PASS |
| §6.2 | `_rate_futures.py` | 32nds全5例、168.60/168600、CF146.23/1.4623/125.8323/1.4889%/123.99/121.99/1.2199、CTD2.69/1.87/2.12、Ex6.2全7値。独立年金/loan ledger | 計算完了。Hullの3月切捨て/Note月丸め規約、CTD/受渡日既知、Ex6.2は365基準。説明・受入保留 | 4 passed・ruff check/format PASS |
| §6.3 | `_rate_futures.py` | 99.250/25bp/100損失、Table6.2 −12.5/−125/25/225、475/700/999300、May.0475%/June-July.055%/41.67、Ex6.3 79/197500/700000/502500・41/102500/400000/502500、2.916%/3.033%/2.75%。独立cash/DF chain | 計算完了。July.55%/197000/102250/502250は原典誤記。convexity cの数値入力/Technical Note不足、減算構造のみ。週末複利はfixingごとの日数係数（同率の別fixingも分離）を独立利息台帳でRED→GREEN確認。説明・受入保留 | 11 passed・ruff check/format PASS |
| §6.4 | `_rate_futures.py` | 93.0625/93062.50/79.42/79short。独立±1bp full repricing、CTD duration変更 | 計算完了。Dのquote座標を一致、Pはforward期間価値、CTD9.20は原典入力で推測再計算しない。説明・受入保留 | 10 passed・ruff check/format PASS |
| §7.1 | `_swap_foundations.py` | floating550/650/700/775/825/850/900/950k、fixed750k×8、net−200/−100/−50/25/75/100/150/200k。独立双方cash | 計算完了。daycount省略とfixing時点を分離、LIBOR記述は原典時点。説明・受入保留 | 2 passed・ruff check/format PASS |
| §7.2 | `_swap_foundations.py` | 1M1.7987/3M1.9950/6M2.1880/1Y2.4693/2Y2.9994/5Y4.0401%、最終100950/100750k。独立全node nonlinear root | 計算完了。長期zero線形補間、quarterly coupon。100000の本文単位は100Mと解釈。説明・受入保留 | 4 passed・ruff check/format PASS |
| §7.3 | `_swap_foundations.py` | 3.1%、floating+.23%、floating−.30%、2.77%。独立外部3CFでfloating相殺 | 計算完了。spreadは年率、PV評価と実効支払率を分離。説明・受入保留 | 6 passed・ruff check/format PASS |
| §7.4 | `_swap_foundations.py` | mid2.985/3.065/3.170/3.280/3.420/3.500%、spread3/3/4/4/4/4bp、562222。独立quote2経路/actual利息 | 計算完了。confirm/calendar制度は説明へ、全祝日engineは追加せず。説明・受入保留 | 8 passed・ruff check/format PASS |
| §7.5 | `_swap_foundations.py` | a1.2/b.7/total.5%、direct AAA−.35/BBB4.95/各.25、dealer AAA−.33/BBB4.97/bank.04/各.23、悪化BBB5.97%。独立当事者CF保存 | 計算完了。長期固定/短期信用条件が異なり無リスク裁定とはしない。説明・受入保留 | 10 passed・ruff check/format PASS |
| §7.6 | `_swap_foundations.py` | continuous2.50/3.36/3.68%、semiannual2.516/3.388/3.714%、Table固定/変動/net/DF/PV各3＋.292M。独立floating/fixed bond | 計算完了。単curveOIS、LIBOR初回presetと混同しない。丸め前value.291845813M。説明・受入保留 | 12 passed・ruff check/format PASS |
| §7.7 | `_swap_foundations.py` | 印刷数値なし。10交換/4符号case、par合計0、独立残存PV−終了済CFとroll DF | 計算完了。initial curveに沿うdeterministic rollで確率的期待を主張しない。説明・受入保留 | 16 passed・ruff check/format PASS |
| §7.8 | `_swap_foundations.py` | USD15/−.45×4/−15.45、GBP−10/.4×4/10.4M、spread2/.4/joint1.6/各.7/dealer1.3/−1.1/差.2%、USD195000/AUD−220000/残余1.1×2。独立通貨CF | 計算完了。dealer差.2%は2通貨を無視した説明、forward curveなくhedged利益PVは未特定。説明・受入保留 | 18 passed・ruff check/format PASS |
| §7.9 | `_swap_foundations.py` | CF6/spot/FXforward3/converted3/net3/PV3、domPV3/forPV3/leg合計2。value .9627879765→.9628M。独立2通貨bond/forward CF | 計算完了。.9629Mは2箇所とも表示精度で不一致、許容幅を緩めない。説明・受入保留 | 20 passed・ruff check/format PASS |
| §7.10 | `_swap_foundations.py` | 印刷価格なし。GBP7M/USD10M、3%/補助4%/半年10年のCF構成、独立1/2 IRS分解と補助率不変 | 計算完了。曲線/spot/初回fixingはsynthetic入力、通貨basisモデルは範囲外。説明・受入保留 | 23 passed・ruff check/format PASS |
| §7.12 | `_swap_foundations.py` | 100M/120bp→1.2M/year、40%回収→60M。独立bond recovery＋protection=元本 | 計算完了。5年は契約条件、premium schedule/hazard/価格はCh25、此節で推測しない。説明・受入保留 | 25 passed・ruff check/format PASS |
| §8.1 | `_securitization_foundations.py` | ABS mezz33.3/53.3/80/100%、CDO equity100×4、mezz93.3/100/100/100、senior0/28.2/69.2/100の全16値、AAA89.75≈90・開始10.25・ABS5.25/35・12/80・45/65→69.2の7関係。独立ドル台帳 | 計算完了。全ABS同じ損失率、PD/格付けモデルではない。説明・受入保留 | 2 passed・ruff check/format PASS |
| §9.1 | `_xva_foundations.py` | 2.2/2.1/2.35%→10/15bp。独立定数EE hazard積分、fixed seed default-time MC6SE、CVA/DVA反転 | 計算完了。qはunconditional区間PD、vはdefault条件付きdiscount/LGD込loss、金額の原典価格表なし。説明・受入保留 | 3 passed・ruff check/format PASS |
| §9.2 | `_xva_foundations.py` | 10bp/120bp/30bp/平均2.75%。独立constant cash fundingとdiscount利息積分、IM増分負値 | 計算完了。原典にEE/IM価格表なし、node台形積分のillustration、費用を無条件に価格へ足さない。説明・受入保留 | 6 passed・ruff check/format PASS |
| §9.4 | `_xva_foundations.py` | 印刷数値なし。before/after増分、独立2状態全列挙とpaired fixed seed MC6SE、単体CVA加法性の破れ | 計算完了。defaultとmarket独立のillustration、価格教師/NN学習・規制資本engineは範囲外。説明・受入保留 | 8 passed・ruff check/format PASS |

## 残りと検証

説明中心26項目：§1.1, §1.2, §1.4, §1.6, §1.10, §2.1, §2.2, §2.3, §2.5, §2.7, §2.8, §2.9, §4.1, §4.3, §4.12, §5.1, §5.3, §5.8, §5.13, §6.5, §7.11, §7.13, §8.2, §8.3, §8.4, §9.3。計算ロジックの完了と正式受入を区別する。

- Ch1：計算5/10項目。対象 §1.3, §1.5, §1.7, §1.8, §1.9。
- Ch2：計算4/11項目。対象 §2.4, §2.6, §2.10, §2.11。
- Ch3：計算7/7項目。対象 §3.1, §3.2, §3.3, §3.4, §3.5, §3.6, §3.appendix。
- Ch4：計算9/12項目。対象 §4.2, §4.4, §4.5, §4.6, §4.7, §4.8, §4.9, §4.10, §4.11。
- Ch5：計算10/14項目。対象 §5.2, §5.4, §5.5, §5.6, §5.7, §5.9, §5.10, §5.11, §5.12, §5.14。
- Ch6：計算4/5項目。対象 §6.1, §6.2, §6.3, §6.4。
- Ch7：計算11/13項目。対象 §7.1, §7.2, §7.3, §7.4, §7.5, §7.6, §7.7, §7.8, §7.9, §7.10, §7.12。
- Ch8：計算1/4項目。対象 §8.1。
- Ch9：計算3/4項目。対象 §9.1, §9.2, §9.4。
