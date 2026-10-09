# 増分XVA＋IM・資本：次段階研究設計案（2026-10-09）

状態：読取調査に基づく設計ドラフト。実装・採否・規制準拠を意味しない。既存の提案書H09とバックログ§0のRB-prefix規約に従いRB-H09へ配置する。新しい研究IDは作らない。研究ロードマップの「増分XVA＋IM・資本」を対象とし、CVAだけのtoyへの縮小はしない。以下の数式・実験条件は提案した研究規約であり、実銀行の規約や各文献の数値再現ではない。

## 1. 問い・完了条件

新規取引aによる費用は、既存book Pに追加した後の値と追加前との差で定義する：ΔX(P;a)=X(P∪{a})−X(P)。単独X({a})、偏微分によるmarginal、Euler配賦、同時に実行するhedge hを含むΔX(P;{a,h})は別の量として保存する。対象は清算前のbilateral OTC、synthetic IRSを主商品とする。各legal netting set/CSAを別に計算し、資本・資金プールには別の集計境界を指定する。

必須成果は、credit CVA/DVA、VM/closeout残余gap、算定したposted/received IMとMVA、資金残高からのFCA/FBA、CCR資本とCVA-risk資本からのKVA、book前後・単独・hedge bundleの比較。IM/資本は外生定数を置くだけで完了としない。非線形valuationの一般解や全商品・全規制の実装は次revisionへ明記する。独立参照・原始配列・収束/SE/費用・失敗母数・artifact-only教材・最終数学/金融レビュー・採否を揃えた時点でv1完了。高速化やNN勝利は完了条件にしない。

## 2. 現存コードの再利用と限界（実ソース確認）

| exact module:symbol | 再利用 | そのままでは足りない点 |
|---|---|---|
| `hullkit._xva_foundations:incremental_cva` | scenario×intervalのbook/trade、独立PD/DF、LGDと共通path before/after loss | VM/IM・first-to-default・WWR・資本算定がない。返されたpath差からpaired SEを作る。平均後に独立SEを合成しない |
| `hullkit._xva_foundations:credit_adjustments` | 条件付き・既割引LGD lossと無条件interval PDの積、clean−CVA+DVA | 両デフォルトを独立に足す教材規約。bilateral first-to-defaultになっていない。既LGDに再度(1−R)を掛けない |
| `hullkit._xva_foundations:funding_cash_costs` | 符号付き残高、segregated incremental IMのnode台形積分 | survival/closeout/funding policyなし。IM算定器でもfair priceでもない |
| `hullkit.xva:forward_exposure`, `hullkit.xva:netting_set_exposure`, `hullkit.xva:collateralized_exposure`, `hullkit.xva:cva`, `hullkit.xva:dva`, `hullkit.xva:fva` | GBM forward/手計算/従来の独立EE approximation baseline | collateralized_exposureはHull教材のcure exposure式。legal closeout ledgerとは同一視しない。fvaのEPE×spreadは残高の代わりに使わない |
| `hullkit.credit_curve:HazardCurve`, `hullkit.cds:bootstrap_from_cds` | piecewise hazard/survival、synthetic CDSからQ hazard整合 | physical PDや規制risk weightをCDS hazardに読み替えない |
| `hullkit.hull_white:HullWhiteParams`, `hullkit.hull_white:hw_discount_bond`, `hullkit.hull_white:hw_exact_transition`, `hullkit.hull_white:simulate_hw_paths` | OU state/clean bond pricing | stateのexact生成だけではdiscount integralはexactにならない |
| `hullkit._numeraire_choices:FlatHW`, `hullkit._numeraire_choices:joint_moments`, `hullkit._numeraire_choices:sample_joint`, `hullkit._numeraire_choices:bond` | (x,∫r d t,W)のrank-two exact GaussianとQ/payment tilt、flat synthetic OIS | 任意initial curveのstate/discount規約と混ぜない。v1はこのflat modelで揃える |
| `hullkit._nonstandard_legs:leg_schedule`, `hullkit._nonstandard_legs:fixed_leg`, `hullkit._nonstandard_legs:projected_floating_leg`, `hullkit.swaps:irs_value_bonds`, `hullkit.swaps:irs_value_fras` | dates/fixings/clean couponと独立bond/FRA分解 | live curve engineではない。past fixingはscenarioごとに保存。future realized couponを無条件forwardで置換しない |
| `hullkit.rfr:BusinessCalendar`, `hullkit.rfr:MultiCurveScenario` | synthetic calendar、projection/discount/collateral currency区別 | multi-curve動態・法的担保契約を与えない。v1はsingle OIS curveと明示したzero deterministic basis |
| `hullkit._market_risk:normal_loss_risk`, `hullkit._market_risk:weighted_tail_risk`, `hullkit._market_risk:empirical_risk`, `hullkit._market_risk:quantile_standard_error` | Gaussian anchor/weighted VaR-ES/量子誤差 | loss/gain符号とquantile ruleを固定。IM規制承認・資本要件を表さない |
| `hullkit.risk_allocation:incremental_var`, `hullkit.risk_allocation:euler_es_components` | book riskの補助比較 | incremental_varはpositionを除外した差。追加差と混同しない。VaR/ESを無断でKVA capitalに置換しない |

確認したtests：`test_xva.py`, `test_xva_foundations_credit.py`, `test_xva_foundations_funding.py`, `test_xva_foundations_incremental.py`, `test_hull_white.py`, `test_numeraire_choices.py`, `test_numeraire_hw_state.py`, `test_nonstandard_legs.py`。既存incremental testは二状態負増分とGaussian positive part/paired MCを検証する。これを回帰契約として保持する。MODEL_INDEX記載とscoped file名/definitionsの確認では、bilateral closeout ledger、conditional IM/full revaluation、SA-CCR算定器、BA-CVA算定器を再利用できる実装は見つからなかった。この不在はproject全体の監査結果とは主張しない。

## 3. 選ぶvaluation規約と代替

推奨v1は「clean market valuation＋明示したdesk incremental cash-cost policy」。clean priceはOIS numeraire下のQ期待値。信用価値と経営上のchargeを別欄で示す。固定したclean marks・margin policy・資金policy・capital policyからcash costsを構成する線形モデルなので、内生価格を含む一般FVAを加算できるという主張をしない。主表にはVcredit=Vclean−CVA+DVA、追加charge A=FCA−FBA+MVA+KVA+COLVAを表示し、Vdesk=Vcredit−Aを「このpolicyのinternal transfer value」と名付ける。DVAを価格交渉chargeに含めない対照も同一モデルで別label保存する。

代替1はBurgard–Kjaer/Green–Kenyonのsemi-replication：funding債券、own-default hedge error、capitalがfundingを減らす割合、IM返却を同時に決めるため整合的だが、own-funding default gainとDVAの選択が大きい。代替2はPallavicini等のrecursive funding/closeout valuation：非線形BSDE/PDEを必要とし、portfolio増分も再solveになる。v1と同じ全条件の一般解を達成したとは扱わない。ただしconstant-balance/zero-creditのdeterministic cash anchor、および公表semi-replicationのφ=0・funding-credit係数を指定した簡約条件との対応表を必須にし、署名変更や成分組替えでtotalが変わらないことを独立式で確認する。[Funding Costs, Funding Strategies, Burgard–Kjaer (2013)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2027195)、[Funding Valuation Adjustment: a consistent framework, Pallavicini–Perini–Brigo (2011/2012)](https://arxiv.org/abs/1112.1521)。

Hull–Whiteのfair-value議論も対立する評価目的として説明する。任意の銀行funding spreadやhurdleを市場fair valueと同一視しない。[The FVA Debate, Hull–White (2012)](https://www-2.rotman.utoronto.ca/~hull/downloadablepublications/FVA.pdf)。

### 3.1 通貨・numeraire・event順序

銀行から見たclean V>0は資産、正のlossは費用。全額は単一synthetic currencyのcurrency units、notional Nは同通貨、率は年率decimal、時間はACT/365F年、business horizonは明示したsynthetic calendar。価格bpsはcurrency/N×10000で換算。outer pathsはQ、D(0,t)=exp(−∫0^t rOIS ds)。E[D×loss]を推定し、stochastic DをE[D]E[loss]に分解しない。payment-measure quadratureは同じcashflowをP(0,t)E^t[loss]に読み替える独立対照。IMのinner shock kernel PIMはphysical/stressed synthetic入力とし、Q market pathと別の確率法則・seedを保存する。

同日順序は fixing→coupon/settlement→VM/IM call calculation→lagged settlement→default check。defaultがcoupon以前の別timing caseもanchor化し、選んだ順序を隠さない。coupon、pending margin、past fixingはcum/ex dividend差を明示。call日後settlement前の担保を受領済みとして控除しない。

### 3.2 Netting/VM/IM・closeout

C=受領VM−差入VM。VMはcash、haircut=0、再利用可のtwo-way CSAを主条件にし、再利用不可対照を1条件加える。threshold/MTA/rounding/lagはcontract fields。legal enforceabilityは研究仮定で、実契約の判定はしない。同一相手でも異なるnetting setを相殺しない。

Ip≥0は銀行がpostedしたsegregated IM、Ir≥0は相手がpostedしたsegregated IM。受領Irは銀行資金に使わない。Irはcounterparty default時の認められたcloseout損失吸収にだけ使う。銀行がpostedしたIpはcounterparty defaultでもbankruptcy remoteで返却され、counterpartyへのunsecured exposureに加えない。own defaultではcounterpartyがIpを使える。IM返還の遅れはfunding終了日まで別口座で保持する。

τ=min(τB,τC,T)、v1のQ intensitiesはdeterministic piecewise、independent defaults/market、同時default確率0。g>0のMPOR中、last settled C/IMは凍結し契約CFはcloseoutへ繰越す。τ+gでのreplacement clean markとτ～τ+gの未払net CFを、担保口座の利息とともに同じ時点へ運んだMgapを作る。EC=[Mgap−Cgap−Ir,gap]+、EB=[−Mgap+Cgap−Ip,gap]+を主closeout unsecured claimとする。defaultした相手の分別IMを超える余剰は生存相手に利益として帰属させず返還処理。担保不足claimにのみrecovery Rを適用し、secured collateralはhaircut0でfull recovery。counterparty default直後に銀行がpostedしたIpをlossから二重控除しない。

CVA=E^Q[1{τC<τB,τC≤T}D(0,τC+g)(1−RC)EC]、DVA=E^Q[1{τB<τC,τB≤T}D(0,τB+g)(1−RB)EB]。survivalのindependent anchorではcounterparty event density λC SC SBとown側λB SB SCを使う。単独SCだけの既存CVAとの違いを示す。maturity直後のcloseout延長もevent horizonに含める。

### 3.3 Funding/MVA/KVAの勘定

v1 funding poolは一つのclient set＋そのhedge set。F0はcoupon/upfront、hedge acquisition/settlement、VM transferとremuneration、free cashによるcash ledgerから生成し、`EE`を資金必要額に置き換えない。positive Fは借入、negative Fは投資可能余剰。segregated Ipとblocked capital KはF0から完全に除外する。借入/投資spreads sb,slはOISとの差、IM専用借入rate rbI、IM remuneration rIを入力する。

alive期間のrunning signed costは sb F0+−sl F0−+(rbI−rI)Ip+cK K+(rVM−rOIS)C。FCA/FBA、MVA、KVA、COLVAをこのcash-account分類から独立に積分する。FVA=FCA−FBA。v1はrVM=rOISでCOLVA0、cKはblocked capitalの運用利息を差し引いたannual excess capital chargeと定義する。full hurdle hとcKを同義にしない。credit eventで終了する口座とcloseout/IM返還まで残る口座のstop timeを別に保存する。simplified survival kernelを全口座へ機械的に掛けない。

主条件はcapitalのfunding利用φ=0。φ>0対照はreserveの取り崩し、Fφ=F0−φK、reserve investment returnの変化をcash ledgerに追加してからtotalを比較する。資金便益をFVAとKVAの両方に控除しない。資金spreadはsynthetic policyであり、DVAやown-funding default windfallを別途上乗せしない。信用spread全体を用いる対照はown debtのterminal/default cashを説明した指定戦略だけに限定し、主表のliquidity spreadと混ぜない。ΔMVAやΔKVAは負でもよいが、total posted IM・total capitalは負にしない。

## 4. IMとcapitalの算定範囲

### IM

mainは非SIMMのsynthetic full-revaluation IM。各outer time/stateで、10-business-day conditional PIM shocksによるcum-cash book change ΔΠを作る。銀行posted IM=max(q.99(−ΔΠ),0)、received IM=max(q.99(ΔΠ),0)を別計算する。zero drift physical Gaussian shockのanalytic normal anchor、normal/full-revaluation、stressed volatility×1.5とfat-tail mixtureを比較する。99%VaR、99%ESとsensitivity-based Gaussian proxyを別method labelにする。ESを規制IMの必須方法とは言わない。thresholdを扱うならlegal group allocationを別指定し、bookへの恣意的threshold割当をしない。

daily VM時のone-tail99%・10day/stress dataという国際基準は比較基準で、synthetic seriesには実stress履歴がないため承認された規制IMではない。[BCBS–IOSCO Margin requirements, MGN20 (2020/current)](https://www.bis.org/committees/bcbs/basel-framework/standard/mgn?allChapters=true)。非日次VMのhorizon拡張は別条件を明記する。

SIMMはversion/対象の解説だけにする。2026-10-09の公式公開検索で2.8+2512、2026-07-11発効を確認。ライセンス・governance・concentration/curvature等が必要で、手製delta proxyにSIMMの名を付けない。[ISDA SIMM公式infohub](https://www.isda.org/isda-solutions-infohub/isda-simm/)、[ISDA 2.8+2512公表 (2026-06-12)](https://www.isda.org/?p=1243627)。公式公表結果は検索本文で確認、直接openは403だった。このdraftではSIMM係数をコピー・実装しない。

### Capital

主必須は、linear vanilla single-currency IRSに限定したSA-CCR教材subsetとreduced BA-CVA。SA-CCRでは各setのEAD=1.4(RC+PFE)、margined/unmargined RC、NICA（segregated posted IMを含めない）、supervisory duration/delta、maturity factor/MPOR floor、3 maturity bucketsのoffset、PFE multiplier/floor、margined EAD capを実装対象にする。SA-CCRのPFE add-onは実MC quantile PFEとは別欄。IRS subset以外はrejectしてunhandled母数を示す。[BCBS CRE52, effective 2023/updated 2020](https://www.bis.org/committees/bcbs/basel-framework/standard/cre/52/inforce/2023-01-01/published/2020-06-05)。

CCR RWA=specified counterparty credit RW×EAD、KCCR=specified capital ratio×RWAとする。RW/ratioはsynthetic research inputでjurisdiction適合やbuffer/leverage floorを主張しない。KCVAはMAR50 reduced BA-CVAのcounterparty-wise SCVA、effective maturity、supervisory discount、credit-sector RW、ρ aggregation、discount scalarを明示し、hedge recognitionなしで算定する。all-counterparty aggregationをbook前後に再計算し、netting set単独SCVAの加算で代用しない。KCVAはalready capital amountで、再度0.08を掛けない。[BCBS MAR50, effective 2023/updated 2020](https://www.bis.org/committees/bcbs/basel-framework/standard/mar/50/inforce/2023-01-01/published/2020-07-08)。

main K=KCCR+KCVA（selected risk scope）。市場risk経済資本はPcapital下の1year ES−ELなど明示した別proxy比較であり、FRTB market-risk capitalとは呼ばず主Kへ無断加算しない。全銀行資本のmax/floors、SA-CVA、full BA-CVAのhedge認識、FRTB、operational/leverage/economic capital、CCP default fundは未実装欄に残す。新規hedge hにも別counterparty/setのCCR/CVA資本・IM/fundingを再計算する。

## 5. 独立参照と主要実験

参照はproduction helperを呼ぶだけのmirror testにしない。

1. 二状態/4経路列挙：coupon/default/call/settlementの全cash台帳、nettingあり/なし、VM不足/過担保、postedIM返還、IMの損失吸収上限。Decimal/Fraction等の既存stdlibでtotal保存とperspective reversalを検査。
2. GBM forward：無担保単側EEの解析call/put、deterministic hazard積分、bookに逆方向tradeを追加したnegative ΔCVA。BSM callからouter integrationする独立参照。
3. HW IRS：bond分解とFRA/coupon-sumの独立clean価格、OU/discountのGaussian kernelを直接積分する1～2dim Gauss-Hermite/adaptive quadrature。lagged VM/MPORはjoint past/current/future stateのconditioningで求積し、time grid/quadrature orderを倍化する。default density積分と直接default-time paired MCを比較。
4. IM：linear normal VaR=z.99 sd/ES=φ(z.99)sd/.01、conditional 1dim full-revaluation quantile根＋積分とnested iid MC、proxyとの差とquantile estimation biasを保存。surrogateは主参照完成後のchallenger。
5. SA-CCR：official CRE99 IRS examplesをterms/units/selected subsetが一致する場合のみ独立手算参照とし、原公式image/equationの転記レビュー必須。NICA/TH/MTA/MPOR/maturity-bucket境界/cap/floorを小例で固定。BA-CVAは1相手analytic、2相手のindependent scalar計算。CCRとCVA-risk capitalを区別する。
6. 全費用：constant F/Ip/Kとpiecewise hazardのclosed integral、zero spread/zero hazard/zero risk/zero new tradeの各限界。full costをledgerからdirect再計算し、saved totalとsign/classificationを照合。受領VMがOISで再運用されrVMで付利される場合のcost符号は(rVM−rOIS)Cで固定し、posted側では反転する。

pilotの代表4bundle：(a) existing receive-fixedに同方向を追加、(b)同maturity逆方向追加、(c)同じlegal netting set内の異maturity hedge、(d)client trade＋fully margined dealer hedge。a/bで増分と単独の非一致、bで負増分が出る条件、cで同setのIMが減ってもcapital residualが残る条件、dでcredit低減とMVA/KVA増加のtradeoffを調べる。cには同じhedgeをnon-nettableの別setへ置く独立validation対照を加える。別setの場合、既存setのIMは不変で新setのIMは非負なので、主v1のset別IM総和がそのhedgeだけで減るという結論を出さない。funding poolやcapital集計による別の増分効果とIM netting便益を分ける。この対照は主32cellのbundle数を事後に変更せず、validation rosterとして保存する。符号を結果から選ばない。

主grid候補はcoupon年次、maturities1/3/5y、OIS zero2%、HW a=.2/η=.01、counterparty λ=.02/ownλ=.01、RC=.4/RB=.4、dailyVM settlement lag1business day、MPOR10day、threshold0/.02N、sb50/150bp、sl0/25bp、IM remunerationOIS、cK5/10%（すべてsynthetic）。全cartesian積を作らず、4bundle×4CSA（unsecured/VM immediate zero-MPOR/laggedVM/laggedVM+IM）×2spread-capital policies=32main cellsをpilot後固定する。3独立outer seeds。zero-MPORは数値anchorで実規制条件ではない。η0、λB0、positive/negative rate、MTA境界、MPOR20dayは独立validation cell。future WWRは別revision（joint intensity/default exposureが必要）とし、independent baselineからWWR優位を主張しない。

## 6. 精度・統計・費用と採否

N=2^12/2^14/2^16 outer、M=2^8/2^10/2^12 innerをpilotの候補にする。1dim quantile/referenceが利用できるcoreではinner MCを主engineにしない。daily call calendarは契約固定、valuation integration gridのみh/h2/h4で増やす。grid変更時にVMをmonthlyへ変えてしまう比較は禁止。event datesを全gridへ入れる。

保存誤差はclean-price/discount、default/time/MPOR、IM quantile、capital境界、surrogate、outer samplingを分ける。deterministic ref errorは収束差とtail bound、MCはpaired path cost差のsd/√N（antitheticならpair averageを独立unit）を使う。nested IMのSEはinnerとouterをともに再生成するreplicateで評価し、outer alone CIをtotal-error CIとしない。quantile近傍densityが低い/point massならGaussian quantile SEを無理に使わずorder-statistic/binomial intervalかreplicate intervalを選ぶ。3seedは大域coverage保証ではない。

pilot固定のpractical error target案：Nに対するincremental total absolute0.5bp、主CVA/MVA/KVA components0.1bp。near-zero増分はabsolute基準を使いrelative ratioを除外理由付きで記録。independent reference toleranceとsampling intervalとcost model uncertaintyを混ぜない。pilotで達成不能なら精度target/compute ceiling/未解決biasをmain前に明示して親agentが計画へ反映する。

比較は exact/quadrature、paired MC、existing独立EE/simpleFVA、full revaluation IM対Gaussian sensitivity proxy、LS polynomial challenger。regression導入時はportfolio/schedule/threshold/market-state単位held-outを固定し、tail state/MPOR/change-of-signをtrain/testに漏らさない。信用/IM/kernel生成・capitalprofile・fit/selection・reference/convergence・main inference・検証再生成/復元を含むCPU時間、wall time、peak memory、bytes、ref failure、dropped/unsupported cellsを保存する。prepared query latencyだけで速度採用しない。採用はsame error budgetのtotal preparation+Q×query break-evenで判断し、低次元exactが速ければ教材保持・標準高速器不採用で完了する。

## 7. 実施段階とartifact契約

研究は`johnhull/research/RB-H09/incremental_xva/`、計算はhullkitの新規private modulesでtorch-free。公開API・production dependencies・license dataを追加しない。仮モジュール責務は `_incremental_xva_contracts`（dated termsとpolicy）、`_incremental_xva_margin`（VM/IM states）、`_incremental_xva_credit`（closeout/default）、`_incremental_xva_capital`（selected CCR/BA-CVA）、`_incremental_xva_costs`（残高/積分/差）、`_incremental_xva_references`（独立経路）。実装計画時に既存codeと照合して確定し、ここではsource編集しない。

段階1：signed convention表・legal/cash ledger・independent小例をDESIGNへ固定し数学review。段階2：clean HW/IRSとdefault/VM/MPOR independent baseline。段階3：full-revaluation IM/quadratureとSA-CCR/reduced BA-CVA/資本profile、回帰test。段階4：4bundle pilot、原価/精度/主要gridを固定してapproval済み設計を更新。段階5：32cells×3seed main、independent fresh replay・費用・増分/単独/hedge採否。段階6：3図＋artifact-only notebook/README、tamper checks、C/F両復元、最終独立review、ROADMAP/採否記録。同時研究一本の順序を守り、dynamic hedge/multi-curve完了後に着手する。

JSON manifestにはterms/CSA/legal netting/capital aggregation boundaries、measure/kernel/numeraire/rate units/default conventions/stop times、seed、grid、source/env digest、method、全試行分母、cost denominator、criterion/failureを保存。NPZにはouter normals/states/discount integral、coupon/fixings、VM call/settled balance、Ip/Ir/inner shock summaryまたはreplay seed、default times/closeout/CVA/DVA raw path losses、FCA/FBA/MVA/KVA/COLVA before/after/path increments、capital RC/PFE/EAD/RWA/SCVA/aggregate、quadrature refinement残差、MC independent unitsを保存する。NPZを読み戻して合計・SE・bps・全図を再計算し、signed metadataだけを信用しない。

3図：①single対book increment対hedge bundleのCVA/MVA/KVAとtotal（符号とSE）、②timeごとのEE/VM gap/Ip/Ir/F/capital（同じy単位とseparate panels）、③error budget対all-in expense/threshold・MPOR sensitivity。各図でmethod/model/legal policyとsyntheticを表示、unsupported/failureを消さない。教材は保存済みartifact読み込みだけ。`MODEL_INDEX.md`/docstrings/研究ROADMAPを同時更新、対象pytest、ruff/format、release、artifact/notebook/checkerと両復元の実測結果を記録する。

## 8. 一次出典の根拠・不足

- Green–Kenyon, *MVA: Initial Margin Valuation Adjustment by Replication and Regression*：2014 first submission、読めた版2015-01-13。IM segregation/fundingとexpected future IM/LSACの根拠。研究synthetic IM/規約の正しさや現行SIMM適合の根拠ではない。[原論文](https://arxiv.org/pdf/1405.0508)。
- Green–Kenyon（journal版にDennisを含む）, *KVA: Capital Valuation Adjustment*：2014。capital funding利用、market/CCR/CVA capital区別とhedge自体のcapitalの根拠。旧Basel事例数値を現行capitalへ流用しない。[原論文](https://arxiv.org/pdf/1405.0515)、[journal著者情報SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2400324)。
- Burgard–Kjaer, *Funding Costs, Funding Strategies*：2013 Risk、SSRN revised2015。issuer debt/default strategyごとにFCA/FVAが変わる根拠。一般的ad-hoc additivityを支持しない。[author paper record](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2027195)。
- Pallavicini–Perini–Brigo, *Funding Valuation Adjustment: a consistent framework including CVA, DVA, collateral, netting rules and re-hypothecation*：2011/2012。fundingのrecursive valuation/closeout依存の根拠。[原論文record](https://arxiv.org/abs/1112.1521)。
- Hull–White, *The FVA Debate*：2012。fair valueとfirm financing費用の論争を説明する一次資料。どの銀行でもFVA0が正しいという採否にはしない。[著者公開PDF](https://www-2.rotman.utoronto.ca/~hull/downloadablepublications/FVA.pdf)。
- BCBS current MGN20/CRE52/MAR50：2026-10-09に公式現行章を確認。IM international baseline、selected counterparty capital/CVA-risk capitalの定義と版固定だけを支持する。各jurisdictionの実装法、銀行の資格/監督承認を確認していない。
- ISDA公式2.8+2512公表/search本文、infohub、公開2.7+2412 methodology copyright notice：current versionとlicense依存を確認。2.8本文の全係数・legal useを検証していないためSIMM実装・licensed complianceは範囲外。

不足：主baseではWWR/own-funding default recoveryを実銀行に較正しない。selectedcapitalは銀行全体のbinding capitalを表さない。flat HWとGaussian/stressed synthetic shockの組合せがreal stress反応を示す証拠はない。これらをtotal-value精度のconfidence intervalへ吸収せずmodel/scope limitationとして残す。設計選択は出典からの推論であり、実測結果はまだない。

## 独立レビュー反映（草稿v2）

初回草稿のbundle(c)はnon-nettableの別setへhedgeを置きながらIM低下を狙っており、set別IMの定義と不整合だった。main(c)をsame-set異maturity hedgeに修正し、separate-setはIM offsetが生じないvalidation対照へ分けた。元草稿とレビューを保持し、cash/資本との集計境界を混同しない。
