# 多曲線統合クオートリスク / 商品横断 P&L explain — 研究ドラフト

2026-10-09。作成者: rates_research_next。対象 checkout: `/home/kazumasa/worktrees/johnhull-research-roadmap`。

**結論:** 次テーマは RB-F07 の統合後続として `research/RB-F07/multicurve/` に置く候補が自然である。新 RB-ID は割り当てない。正方 exact calibration を割引 D + synthetic term projection P3/P6 の3曲線へ拡張し、同じ日付・fixing・保有契約 CF から全クオート感応度、cross gamma、full revaluation と一/二次 P&L 残余を計算する。sourcechecks と研究採否を分離し、改善しない条件や非収束を保存する。

これは設計検討用のドラフトであり、正式設計/実施計画/研究 acceptance ではない。リポジトリ、ソース、Git は変更していない。独立小例だけを `/tmp/johnhull-next-rates-probe.py` で試算した。実市場の性能・無裁定動学・法的取引規約の承認を意味しない。

## 1. 現在地と権限

確認した正本: worktree root と johnhull の AGENTS.md、MODEL_INDEX.md §5/§6/RB-F07、ROADMAP.md の研究ロードマップ、research/RB-F07/README.md、docs/prep/design/RB-F07_DESIGN.md、docs/superpowers/plans/2026-09-27-research-backlog.md §6.2。

- ROADMAP は quote DML、離散barrier、F04、F08、F06、短期満期の後続に「多曲線統合risk / P&L」を必須の未設計テーマとして保持している。動的モデル横断ヘッジが先行中。
- F07 v1 は単一通貨/曲線、正方 root、日付なし、直接quote依存0。v2 非正方 least squares、v3 HW1F、public API昇格は既存文書で別承認。今回の主提案は exact multicurve と CF/P&L の私的研究で、v2/v3 の無断実装を含めない。LS/KKT は誤用防止の式と独立反例として設計に必ず書く。
- hullkit は torch-free。NumPy/SciPy/標準ライブラリで完結。production依存追加、公開API変更、market feed、licensed data、外部送信/公開は範囲外。
- 技能: hull-derivatives は概念/既存境界の確認、brainstorming は研究spike、writing-plans は工程とファイル境界の検討に使用した。承認済み調査のため追加質問や実装開始はしていない。

## 2. 実在するコードの棚卸し

以下は実際にファイル/シンボルを読んで確認した。パスは checkout 相対、`module:symbol` は実在する名前。再利用の可能性と独立オラクルの役割を区別する。

| 実装とテスト | 実在する module:symbol | 再利用と不足 |
|---|---|---|
| hullkit/src/hullkit/_quote_risk.py; tests/test_quote_risk.py | `hullkit._quote_risk:Quote`, `Calibration`, `QuoteRisk`, `discount_factors`, `model_quotes`, `calibrate`, `cashflow_value`, `receiver_swap_value`, `quote_sensitivity` | exact square Newton/analytic J、随伴、zero/logDF補間、quote単位/rank規約。単一curve限定。`receiver_swap_value` の floating PV=N(1-Dlast) は at-reset singlecurve 専用で多曲線へ流用不可 |
| hullkit/src/hullkit/rfr.py; tests/test_rfr.py | `hullkit.rfr:BusinessCalendar`, `RFRConvention`, `DailyAccrual`, `CompoundedRFR`, `daily_accrual_schedule`, `compounded_rfr`, `rfr_coupon`, `RfrCurve`, `MultiCurveScenario`, `curve_basis_spread`, `collateralized_present_value`, `futures_forward_from_covariance` | calendar/日次複利実現CF、日付zero線形曲線。RfrCurveのtimeはACT365、simple_forwardの既定はACT360。MultiCurveScenarioはforecast/discountラベル+担保通貨の簡易検査のみ。複数curve同時較正、publication-timeによる既知/未知分離、quote Jacobianなし。BusinessCalendarはpreceding/shift/business_datesのみでmodified-following/EOMなし |
| hullkit/src/hullkit/_swap_foundations.py | `hullkit._swap_foundations:interest_swap_cash`, `ois_bootstrap`, `dated_interest`, `ois_swap_value`, `swap_roll_schedule` | CF符号・日付利息・deterministic rollの独立基準。ois_swap_valueは観測済log-growth+単一curveの条件付きforecastで、exact daily-compounding multi-curveの教師ではない |
| hullkit/src/hullkit/_rates_foundations.py | `hullkit._rates_foundations:compounded_reference_rate`, `bootstrap_piecewise_zero`, `curve_forward`, `fra_settlement`, `fra_contract_value`, `bond_sensitivities`, `bond_taylor_change` | FRAのterm-endとadvance-settlementの契約差、単純CF/複利の検算に使用。fra_contract_valueの年分数はtime差で日付multi-curveにはそのまま使えない |
| hullkit/src/hullkit/rates.py; swaps.py | `hullkit.rates:discount_factor`, `zero_interp`, `bootstrap_zero_curve`, `bond_price`; `hullkit.swaps:swap_rate`, `irs_value_bonds`, `irs_value_fras` | singlecurve/同一curve極限の独立既存検算。bootstrap_zero_curveは半年利払bond価格quote用でgeneral curve engineではない |
| hullkit/src/hullkit/_quote_dml_hedging.py; tests/test_quote_dml_hedging.py | `hullkit._quote_dml_hedging:held_prices`, `held_risk`, `solve_hedge`, `entry_cost` | center-marketでcouponを固定しshocked parへresetしない設計。spot+5singlecurve quote、静的shockだけ。term-end FRAのCFをadvance-settled FRAへ読み替えない |
| hullkit/src/hullkit/pnl_explain.py; tests/test_pnl_explain.py | `hullkit.pnl_explain:aggregate_exposures`, `delta_gamma_vega_pnl`, `pnl_attribution`, `desk_report` | 既存表示/JSON形式は参照可能。gammaが対角のみでD/P・P3/P6 cross gammaを欠く。unexplained_shareのmax(abs(full),1e-12)だけを研究の成功分母にしない |
| research/RB-F07/quote_dml/reference_methods.py | `reference_methods:bootstrap`, `model_jacobian`, `held_prices`, `held_risk`（研究ローカルmodule） | 独立brent/complex-step/frozen契約の検証パターンを参照。現状5quote singlecurveなので新実験の独立教師としてそのまま呼ばない |
| research/RB-F07/quote_dml/costs.py | `costs:cost_summary`（研究ローカルmodule） | 原始時間とdenominatorから再計算する形式を参照。NN/fitのschemaを無理に再利用しない |

`hullkit.aad:pathwise_greeks` 等はGBMのMC教師で汎用calibration AAD engineではない。今回は小規模解析微分+IFTで良く、名前がAADだからと使用しない。

## 3. 選択肢

1. **推奨: exact three-curve CF研究。** DとP3をまず較正し、D/P3依存のbasis quotesでP6を較正。full block IFTと全再較正bumpを比較する。依存伝播・日付・cross gammaが主目的に直接つながる。小規模、torch不要。これは多曲線統合研究のbaselineで、単一curveデモに縮小しない。
2. 同時にLS/smoothing/拘束を主研究に追加。noisy quotesの実用性は高いが、最適性/KKT/active-setの追加検証が必要で、F07v2の別承認とscopeが衝突する。主研究では式/反例を残し、実装は条件付き後続。
3. HW/LMM確率basis、先物convexity、option volまで一度に扱う。大きな商品範囲を得るが、初期curve-risk研究と動学教師の混同リスクがある。main acceptanceの必要条件にしない。

## 4. 状態とデータ契約（私的型の候補）

**dateとtime:** 実際のGregorian日付を入力し、全CFは保存したscheduleを使う。curve time `t=(date-valuation_date).days/365` は座標で、coupon accrual ACT360/ACT365や30/360と分ける。最初はACT360/ACT365のみ。30/360/ACTACTが必要なら方式を指定して独立date oracleを足すまで unsupported とする。

**calendar:** weekend/holidayはfixtureに明示。synthetic calendar `CAL_SYNTH` を使い、その休日を実際の米英市場calendarと呼ばない。following/modified-following/preceding、EOMとstub、spot lag、payment lag、fixing lagはresolved date列に保存する。既存BusinessCalendarから勝手にmodified-followingが得られると想定しない。

**fixings:** index, observation_date, publication_at (timezone付き), value_decimal, revision_id/sourceを持つ。as_of以前に公開されたレコードだけ既知。単にobservation_date<=valuation_dateを既知判定にしない。既知必須だが欠損のfixingはエラー、未公開はforecast。quote shocks中は既知fixingを固定する。同日境界のas_ofはexplicit fixtureでpublication前/後を作る。

**curves:** ordered curve_ids `[D,P3,P6]`、valuation_date、node_dates、node-coordinate zeroまたはlogDF、interpolation/extrapolation_id、projection-index、currency/collateral_currency。同一valuation date/通貨を強制。本提案は単一通貨の担保付き研究で、FX/cross-currency CSAやmulti-currency basisへ一般化しない。projection P3/P6はforward-rateを表現するpseudo-discount factorsであり、cashをdiscountする取引可能bondではない。

**quotes:** quote_id/curve calibration group/order、raw_value、raw_unit、display_step、quote_transform、resolved calibration contract、notional conventions、time_stamp。rates decimalで1bp=1e-4、basisも1bp=1e-4。bond価格はface100のprice point1.00ならN/100換算を明示。主12quoteはrates/basis、価格quoteは単位対照の追加oracle。先物100-100rは公式商品契約とconvexity仮定を追加するまで主実験に入れない。

**held contracts:** contract_id、signed quantity、currency、immutable fixed_coupon/spread/notional_schedule、principal exchange、accrual_start/end/reset/payment_dates、index/convention、settlement style。shocked marketでpar contractを再発行しない。IRSの元本交換は0、bondは償還元本あり、FRAはadvanceとterm-endを別契約種にする。

**failure record:** scheduled case_id/cell_id、attempt_id、status/reason、original inputs、iterations、residual vector、scaledJ/SVD/rank、node/curve response、solve backward residual、warnings、wall_seconds/CPU_seconds/peak memory。failed NaN outputsをaccepted rowsへ黙って置換しない。oracleが失敗した場合もsource器勝利とはしない。

## 5. 価格と較正式（本ドラフトで導出した決定論的教師）

D(t)は担保discount、P_a(t)はa-tenor projectionのpseudoDF。単純term rateを

F_a(s,e)=[P_a(s)/P_a(e)-1]/alpha(s,e)

と定義する。synthetic契約の支払pにおける浮動coupon forecastは `N alpha F_a`。receiver-fixed IRS:

V_IRS = sum_i N_i D(p_i)[K alpha_i^fix - F_a(s_i,e_i) alpha_i^float].

単一curve・同一期日・同一alpha・unseasonedの場合だけtelescopingを検算できる。多曲線では一般にfloating legはN[1-D(T)]にならない。異なるtenor間のbasis swap（P3+sを受取/P6を支払）のpar basisは

s = [sum_j N_j D(p_j^6) alpha_j^6 F6_j - sum_i N_i D(p_i^3) alpha_i^3 F3_i] / [sum_i N_i D(p_i^3) alpha_i^3].

sの向きと付加legをinputに固定する。このquoteでP6を較正するとDとP3のquoteがP6へ伝播する。

**RFR coupon:** G = prod_i(1+r_i w_i), C=N(G-1)。w_i=日数/basis。lookupは観測日、w_iはobservation_shiftの有無による区間、lockoutはrate再利用。複利spreadとsimple-added spreadは別契約。既知部分G_knownと未知のforecast product G_forecastを分離。forecastは本研究では決定論的forward pathと定義する。prod E[r] が一般に E[prod r] と同じだと主張しない。payment delayを伴う未知RFRの一般的確率モデルではtiming/measure/convexity調整が必要になり、本研究はそれをmarket-correctに済ませたと数えない。

日次simple_forwardsを同一Dから作り、lag/lookback無し・payment=eの場合、未知複利はD(s)/D(e)へtelescopingする。これはOIS curve calibration用の基準ケース。payment lag/shiftで崩れる場合はexplicit daily productをteacherとしてprice/derivativesを検算する。

**FRA:** term-end deterministic teacherはN alpha D(e)(F-K)。advance-settled realized CFはN alpha(L-K)/(1+alpha L)をsで支払う。pre-fixingの確率的expectationは単純にFをLへ代入するだけで厳密にならない。主研究のterm-end FRAと、fixing後のadvance cash oracleを明確に分ける。

## 6. 全クオートリスク、二次、LS/KKTの境界

theta=(theta_D,theta_3,theta_6), qは市場quote原順。F(theta,q)=0、J=F_thetaが正方局所可逆なら

A=dtheta/dq=-J^{-1}F_q,

g_q=V_q+A^T V_theta.

`J.T lambda=V_theta` と解き、g_q=V_q-F_q.T lambdaを返す。quote residual m(theta)-qならF_q=-Iだが、PV residualやquote transformではそうとは限らない。主held bookのV_q=0を固定し、明示direct exposureのsmall fixtureでV_qの漏れを検出する。

逐次D→P3→P6ではJの下の非対角blocksが重要。P3/Dを独立凍結してP6をbumpするwrong-modelを対照にする。隣接curveが動く効果を無視したquote-riskは統合リスクではない。完全に絡むcurve群なら同時solve。順序交換の不変性は同じ数学problemを単に並べ替えた場合だけ成立し、順序と一緒にinstrument/pillarを変えた場合には要求しない。

direction vについてa=A vとし、

b=theta''[v,v]=-J^{-1}{F_theta_theta[a,a]+2 F_theta_q[a,v]+F_q_q[v,v]},

V''[v,v]=a^T V_theta_theta a+V_theta^T b+2 V_theta_q[a,v]+V_q_q[v,v].

全H_qはdirections/混合方向から構築し、H_ij=H_jiを検算する。quote-P&Lの二次ではthetaの二階較正response `V_theta^T b` も必要で、固定curveのgammaをAだけでsandwichする方式はwrong control。

**単位:** S_q=diag(display_steps)、g_step=S_q g_q、H_step=S_q H_q S_q。moves u=delta q/display_steps。R1=DeltaV-g_step^T u、R2=R1-0.5 u^T H_step u。rate/basisは通貨/bp、Hは通貨/bp²、price quoteは通貨/price point。他の単位のbucketの数字を足す場合は「各bucketを1 declared step動かすscenario」のように定義する。

**LS（別実装範囲）:** Phi=0.5 r^T W r+lambda/2||L(theta-theta0)||²、r=m(theta)-q、Wは固定正定値。最適性G=J^T W r+lambda L^T L(theta-theta0)=0を微分する:

H_Phi=J^T W J+sum_i (W r)_i Hess(m_i)+lambda L^T L,

dtheta/dq=H_Phi^{-1} J^T W.

非ゼロ残差でGauss-Newton J^T W Jだけに置換したgradientはexactでない。W/lambda/theta0がquotesに依存する場合はさらにG_q項が必要。非正方Jを疑似逆行列にするだけではこの最適性感応度を保証しない。LSでPV residualとquote residualの重みを安易に変えると目的関数自体が変わり、exact-rootの残差書換不変性を適用できない。

**拘束:** equality/active inequalityがある場合はLagrangian最適性+active constraintsのKKT systemを微分する。LICQ・active set安定・二次十分条件を確認し、active set切替は通常滑らかでない。global2階Taylorやcentral differenceをそこで成功条件にしない。solver success flagだけをrisk acceptanceに使わない。

**座標/補間/悪条件:** invertible zero↔logDF変換では同一補間モデルを表現した場合のquote risk/Hが一致する。zero線形とlogDF線形は異なるmodelで、一致を要求しない。現行F07は両補間とも区間外flat-zeroである。新研究の通常ケースはcoverage内、外挿は明示対照としてflat-zeroまたはrejectを選び記録。negative rateでDF>1はあり得るため単純なD<=1/単調性を無条件強制しない。一方DF>0、simple成長factor>0、finite CFは必要。

scaled J = diag(1/quote_steps) J diag(theta_steps) でSVD/rank、normalized backward error、quote-step→zero-bp responseを保存。元F07の10bp/bp警告は研究上の設計値として引継可能で、market standardではない。logDF raw condition numberだけで停止しない。隣接pillar、redundant basis quote、遠いnodeがinstrumentに観測されないケースを作り、full-risk相殺/illconditioningも隠さず保存する。

## 7. 独立オラクルと実際のscratch数値

主器はanalyticJ/derivatives、独立参照はmain price/calibration helperをimportせず、日付表を独自に列挙してDF ratioとsigned CFから価格を作る。逐次独立brentq（局所補間baseline）、別の同時root/SciPy method（絡むstress）、再較正central bumpsのh sweep。complex-stepは滑らかなpure kernelだけに使う（日付変更、abs/max、active-setを跨がない）。同一CF helper呼出を独立価格検証と称しない。Decimal/fractionsで既知RFR CFと日数を検算する。

小例はD1/D2/P1/P2の2曲線4quoteで手計算可能:

D1=1/(1+d1), D2=(1-d2 D1)/(1+d2), f2=p2+(D1/D2)(p2-p1), P1=1/(1+p1), P2=P1/(1+f2).

ここで1/2年のdiscount deposit/OIS quote d1/d2、term1年/2年IRS quote p1/p2、annual accrual1。1.5年はlogDF補間し、D15=sqrt(D1D2)、F(1,1.5)=2[sqrt(P1/P2)-1]。held receiver K=.042、1年coupon accrual1、1.5年stub accrual.5、元本1000万、1.5年discount bond売り300万:

V=1e7[(.042-p1)D1+.5(.042-F15)D15]-3e6 D15.

q=[.03,.035,.04,.045]のscratch結果（2026-10-09、既存venv NumPy/SciPy、production code未使用）:

- D1=.970873786407767、D2=.9333520941794475、P1=.9615384615384615、P2=.915575644031551。
- PV=-2,872,474.865768164。
- complex-step quote/bp=[135.98757145,280.26451348,-487.75358309,-947.56909444]。
- D/P cross-gamma通貨/bp²=[[.02319755,.09269944],[.04738072,-.00137773]]。Hはcomplex-step勾配のcentral difference h=1e-5で近似したもの（完全解析second oracleではない）。
- move direction [1,-.7,.8,-.6]bpを8/4/2/1/.5倍するとR1=[-.93492125,-.23397217,-.05852330,-.01463461,-.00365913]、R2=[.00193585,.00024211,.00003027,.000003784,.000000472]。R1は約4分の1、R2は約8分の1。これは小例の数値観測で、多曲線主studyのacceptanceではない。

LS反例（主実装scopeではなく誤用防止）: m(theta)=(theta,theta²), q=(1,0), W=I。2theta³+theta-1=0をbrentqで解くとtheta=.5897545123014584、残差非ゼロ。exact dtheta/dq=[.32395355,.38210613]、誤ったGN=[.41819280,.49326218]。本提案の式とexact-rootの適用境界を明瞭に固定できる。拘束反例はtheta>=0のm=theta、qが0を跨ぐ場合のleft/right derivative 0/1。

## 8. 商品横断のP&L契約

**静的:** t0、as_of、既知fixings、immutable contractsを固定し、q0→q1で全curveを再較正したDeltaVをfull revaluationとする。CF product別とbook全体のg/H/R1/R2、D/P3/P6 block contributionを保存。bookだけ相殺して良く見える結果を避け、商品別検証も必須。

**roll/event:** t1にcash account換算したCFをC(t0,t1]とし、total contractual P&L=V1-V0+C。t0とt1のPVはそれぞれvaluation日通貨、CFはt1へ指定担保口座で累積する。資金調達損益を含める場合はそのcash accountも別ledgerに追加し、差引zero-cost-gainと混ぜない。

baseline old-stateをt1へrollした反実仮想Vrは、残存dateを固定し、D_roll(t1,u)=D0(u)/D0(t1)、projection ratioもP0(u)/P0(t1)と定義。新たなfixingsはその旧curve deterministic forecastを使用する。quote coordinatesはt1で新たにresolvedしたcalibration instrumentsに対するq_roll=m_t1(theta_roll)。t0のtenor quotesを黙ってt1のquotesとして流用しない。

順番を固定したexact bridge:

P&L = [Vr - V0 + C0] + [Vf - Vr + (Cf-C0)] + [V1 - Vf].

最初はroll/carry/cash、次は新fixing到来とactual cashとforecast cashの差、最後は新quotes/recalibration。Vfは新fixingを受け取り市場曲線shock前の状態。market TaylorのcenterはVf（t1 date/fixing状態）、move=q1-q_roll。eventでcurve再較正quote centerが変わるならfixing-conditioned center quotesを再算出して保存する。各反実仮想stateとcashを保存し、順序依存を無視した唯一のtheta/fixing寄与と呼ばない。

観測数が減るRFR coupon、term reset、payment、expiry、missingfixing/publication直前直後はdiscrete state changes。そこを滑らかなTheta+gamma残余で説明しきったとみなさない。ex-payment評価は直後cashflowをvalueから除外し、cash ledgerに一度だけ入れる。旧couponを消さず新curveのparcouponに更新するwrong controlも用意する。

## 9. 必要な主fixtureと比較

mainはD4nodes/P3 4nodes/P6 4nodesと12quotesを候補にする（date scheduleを解決後、pilotでrank/coverageを先に確認）:

- D: 3m/6m/1y/2y synthetic OIS、主基準はpayment delay0。
- P3: 0×3m、3×6mのterm-end forward quotes + 1y/2y3m IRS。
- P6: 0×6m forward anchor + 1y/18m/2y P3-versus-P6 basis quotes。P6 nodes6m/1y/18m/2y。
- 全quoteは生成用truth曲線から独立CF engineで作る。truth復元が不可能なvariant（misspecified interpolationなど）も分けて保持。
- book: 18mfixed coupon bond/discount bond、off-pillar forward-start3m IRS、seasoned6m IRS（first fixing既知）、term-end FRA、3m/6m basis swap、partial-known RFR OIS。amortizing or stub IRSを追加。主商品にoptionを必須化しない。

市場shape: flat/sloped/humped、negative-rate、positive/negative basis、near-redundant quote、information-thin node。shockはsinglebucket、D-only、P3-only、basis-only、allquote parallel、twist、mixed directionsを両符号で0.5/1/2/4/8bp、stress25/50bp。stressで二次が一次より悪い結果もそのまま保存。

date cases: 月末followingが翌月へ跨ぐのでmodified-followingがprecedingになるケース、年越し/休日weekend多日数、leap day2028-02-29、short/longstub、spot/payment/reset各lag、同日publication前/後、knownfixing欠損、payment/expiry前/後、lookbackのみとobservation_shiftとlockoutをそれぞれ含む。fixture calendarsは手指定し、realcalendar準拠というlabelを付けない。

追加wrong controls: singlecurve D=P3=P6、discount quote shock時のP3/P6freeze、P6をP3independentとして扱う、P3-P6basis符号反転、ACT360とcurveACT365混同、knownfixingをforecastへ戻す、diagonal-gamma only、calibration curvature省略、shockcoupon reset、ex-payment二重計上。

## 10. 成功・誤差・費用の候補（pilot前に固定する）

以下は外部基準ではなく研究の候補契約。pilotで数値到達性/費用を確かめる際は目標を「結果が通るまで」緩めず、変更理由・before/after・acceptanceへの影響を設計へ残して独立レビューする。

- exact根: max|F_i/quote_step_i|<=1e-10（rate絶対1e-14）+finite +scaledfullrank。illconditioned warningは成功flagと別。非収束、singular、support外はfailed row。
- oraclePV: abs error <=1e-7+1e-12 sum_abs_notional（N1000万なら~1e-5通貨）; g/bp <=2e-6+1e-8|g_ref|、H/bp² <=1e-5+1e-6|H_ref|候補。near0は絶対差で判断。H基準はmixedbump h sweepの安定域が確認できない場合unverifiedとする。
- coordinate/root-residual permutation/invariance: 同一problemのPV/g/Hが上の単位別許容差内。interpolation variant同士の一致はgateにしない。
- 静的smooth cases: least3 non-roundoff move sizesで|R1|がquadratic、|R2|がcubicへ近づく（log slope候補R1∈[1.8,2.2],R2∈[2.6,3.4]）。特定directionでleading coefficientがzeroになる場合はdegenerateと記録して絶対上界を検証、好都合なdirectionへ差し替えない。
- bookCF conservation: book value=sum product values、bookg/H=sum productg/H、payer/receiver anti-symmetry、paymentbridge恒等式。abs threshold1e-7+1e-12 grossCFscale。fixing/expiryの市場Taylor率はsmooth subsetと別。
- explain: |R|通貨、bp notional=1e4R/sum_abs_notional、original |DeltaV|、|R1|、|R2|、|DeltaV|-floor、valid flagを全部保存。ratio改善は|R1|>economic floor（候補1e-7+1e-12notional）のケースだけ定義し、分母0はundefined。総予定casesと各statusの件数を報告。failure/unstable/degenerateを落として100%勝率にしない。
- cost: 初期date resolution、quote construction、calibration、J/H build、factorization、CF PV/risk、full-revaluation bumps、I/O/loadを含むwall/CPU/peakmemとcallcounts。warm-start/cold-startを別計時し同じquotes/cases/accuracyで比べる。factorization reuseは市場1snapshotに対して再利用する回数を明示する。
- baselineは独立sequentialbrent+fullrevaluation、primaryはanalyticIFT。商品数1/10/100、quote数12/24の候補規模でprecision-equal比較。H-full vs directionalHは要求される出力が違うため同じ速度比でまとめない。未達精度はspeedwin不可、timeoutの元予算も原価へ算入。
- リソースcandidate: CPU only、pilot全体5分、正式主計算30分を初期hard capとする（計測に基づく見積りではない）。上限を超えたら失敗/費用記録を保存してformalprotocol更新判断へ戻る。高速化の勝利は完了条件ではない。

## 11. 段階・候補ファイル・deliverables

全て johnhull 内のprivate研究に局所化する。下記ファイル/シンボルは未実装の候補であり、棚卸し表の実在APIと区別する。既存 `_quote_risk.py` のv1規約を書き換えない。

| 段階 | 候補ファイル | 完了する独立deliverable |
|---|---|---|
| A formal design | research/RB-F07/multicurve/DESIGN.md; docs/superpowers/plans/2026-10-09-multicurve-risk-pnl.md | 3curves/12quote、date/fixing/coupon単位/範囲、oracles、failureと候補acceptanceの数学review。既存v2/v3別承認との境界を明記 |
| B date/CF contract | hullkit/src/hullkit/_multicurve_cashflows.py; tests/test_multicurve_cashflows.py | proposed `ResolvedCoupon`,`FixingState`,`resolve_schedule`,`realized_cashflows`,`forecast_cashflows`。独立Decimal/date-table fixtures。publication前後/seasoned/reset/payment conservation |
| C curve calibration | hullkit/src/hullkit/_multicurve_quotes.py; tests/test_multicurve_quotes.py; research/.../reference_methods.py | proposed `CurveGroup`,`ResolvedQuote`,`model_quotes`,`calibrate_group`。12unknown/12quote exact J、both coordinate/kernel校正、full/non-diagonalresponse。sequentialbrent+2curveclosedformと一致 |
| D risk/full curvature | hullkit/src/hullkit/_multicurve_risk.py; tests/test_multicurve_risk.py | proposed `quote_gradient`,`quote_directional_curvature`,`quote_hessian`。secondIFT/units/directquote項、全再較正mixedbump、scaledrank/near-singular、LS/GNnegative oracle |
| E P&L bridge | hullkit/src/hullkit/_multicurve_pnl.py; tests/test_multicurve_pnl.py | proposed `held_book_value`,`static_explain`,`roll_fixing_cash_bridge`。immutable coupons、book cross-gamma、exact反実仮想bridge、wholebook+product保存、wrong controls |
| F pilot/freeze/main | research/.../protocol.json, pilot.py, runner.py, build_reference.py, checker.py | protocol counters、allrows/原始配列、nonfinite/status、pre/post freeze、fresh独立cases、true cost。main未実行を完了扱いしない |
| G artifacts/review/adoption | research/.../reference.json,reference.npz,manifest.json,RESULTS.md,REVIEW.md,build_notebook.py,multicurve_risk.ipynb | stored-data-only3–4図、全失敗/分母・残余、独立fresh数値checkerと改変検知、保管庫C/F両復元、採否（not necessarily speedwin）、scoped regression/index/docstrings/release、roadmap更新 |

future command examplesはrepo rootから対象checkout PYTHONPATHと共有venvを使う。NumPy/SciPy実装だけならdeep_hedge_priceを新たに変更する理由はない。maincurve/riskCFソースレビューがPASSでも研究pilot/freeze/main/保存値checker/教材/reviewが未完了なら「研究完了」ではない。sourcechecksのtest数は実測して書く。

suggested figures: (1) D/P3/P6 quotes→curve→products risk heatmapとfrozenwrongcontrol、(2) move size対R1/R2とdiagonalgammawrongcontrol、(3) date roll/fixing/cash exact bridgeとnearzero denominator、(4) illconditionedresponse/cost（必要なら）。artifact-only: notebookからbootstrap/計時/netfetchをしない。

正式designで受入が決まったらMODEL_INDEXに非公開module/symbolを登録してdocstring guardを通し、ROADMAPとresearch backlogsの「現在地」を同じ変更単位で更新する。本編節accepted件数は研究だけで増やさない。

## 12. 出典とprovenance（2026-10-09 webで確認）

一次資料/公式資料のみ。以下の各資料の支持する主張と今回確認した範囲を限定する。本文の数値/success threshold/契約schema/工程/secondIFT/LS・KKTの具体式は本ドラフトの導出・設計で、引用元にそのまま記載された規格とはしない。

| ID | 資料・年・link | 確認/支持する主張と限界 |
|---|---|---|
| M1 | Marc Henrard, *Adjoint Algorithmic Differentiation: Calibration and Implicit Function Theorem*, initial2011-01-01/revised2011-11-01, [OpenGamma author paper](https://quant.opengamma.io/Adjoint-Algorithmic-Differentiation-OpenGamma.pdf) | PDF8pages §2–3を閲覧。局所可逆root IFT、curveへの直接price依存とcalibratedparameter依存の両方をchainruleに含める。非正方LS/KKTをinverseJとして保証する資料ではない。paperのspeedratioを本研究の実測へ転用しない |
| M2 | Marc Henrard/OpenGamma, *Sensitivity computation*, v1.1 2014-06-20, [official PDF](https://quant.opengamma.io/Sensitivity-Computation-OpenGamma.pdf) | PDF18pages §2–3を閲覧。point/parameter/marketquote sensitivities、複数curveunitsを逐次較正するとpreviouscurvequotesへの依存も保存する、parquote/PV residualの区別。統合dependencyの根拠 |
| M3 | OpenGamma Strata, *JacobianCalibrationMatrix* / *MarketQuoteSensitivityCalculator*, publication year未表示（currentdocs閲覧2026-10-09）, [matrix](https://strata.opengamma.io/apidocs/com/opengamma/strata/market/curve/JacobianCalibrationMatrix.html), [calculator](https://strata.opengamma.io/apidocs/com/opengamma/strata/pricer/sensitivity/MarketQuoteSensitivityCalculator.html) | docsのmatrixはcurveparameters wrt marketquotesで向きがdtheta/dq。curveorder/unitsを持つ。parameter感応度からmarketquoteを算出。Java実行/Strata数値比較は未実施 |
| M4 | Ferdinando M. Ametrano / Marco Bianchetti, *Everything You Always Wanted to Know About Multiple Interest Rate Curve Bootstrapping but Were Afraid to Ask*,2013-04-02, [author-deposited SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2219548) | indexed author abstractを確認（open本文はinternal error）。discount/FRA-tenor curves、Deposits/FRA/Futures/Swaps/OIS/Basis、interpolation/negative rates/local vs nonlocaldeltaが論題。具体式/marketfixtureをfullPDF確認済みと扱わない |
| M5 | Ametrano / Bianchetti, *Bootstrapping the Illiquidity: Multiple Yield Curves Construction for Market Coherent Forward Rates Estimation*, authorPDF2009-03-10, [author site](https://www.bianchetti.org/finance/bootstrappingtheilliquidity-v1.0.pdf) | PDF34pages §1–2を閲覧。tenor-specificcurves、exactfit/interpolationの較正時相互作用、dates/fixing/turn-of-year/convexityの注意。2009historical前提のnonnegativerateを現在の一般契約にしない |
| M6 | Marco Bianchetti, *Two Curves, One Price: Pricing & Hedging Interest Rate Derivatives Decoupling Forwarding and Discounting Yield Curves*, arXiv first2009/revised2012、shortversionRisk2010, [author arXiv](https://arxiv.org/abs/0905.2770) | authorabstractを確認。discount/projection separationとbasis、measurechangeによる調整の必要性。本研究のdeterministicCFteacherを一般的なarbitrage-free stochasticmodelと呼ばない根拠。fullPDF再現は未実施 |
| M7 | Federal Reserve Bank of New York, *Additional Information about Reference Rates Administered by the New York Fed*,live methodページyear未表示（2026-10-09閲覧）, [official methodology](https://www.newyorkfed.org/markets/reference-rates/additional-information-about-reference-rates) | SOFRaverages/indexはbusinessday複利、nonbusinessdayはpreviousfixingでsimpleinterest、ACT360。SOFRvalue-dateとpublication-date差、indexrounding。newpublication時間等はページを確認したが本草稿fixtureは実際のdata/feedを利用していない |
| M8 | Bank of England, *Supporting Risk-Free Rate transition through the provision of compounded SONIA*,2020/updated2020-07-15, [official policy](https://www.bankofengland.co.uk/paper/2020/supporting-risk-free-rate-transition-through-the-provision-of-compounded-sonia)；*SONIA Key features and policies*,live year未表示, [official methodology](https://www.bankofengland.co.uk/markets/sonia-benchmark/sonia-key-features-and-policies) | indexのpublished/内部rounding差、observationinterval/日数basisの公式例。SONIAindex利用権を自動許可とせず、syntheticfixtureのみ。本研究のmodifiedfollowing/holidayをこのページが保証するとはしない |
| M9 | SciPy, *scipy.optimize.least_squares*,current1.18docs year未表示（2026-10-09閲覧）, [official docs](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html) | bounds/m×nresidualJ/termination/complex-stepanalyticcontinuationの条件。公開最新docsのversionをlocalinstalledversionとして主張しない。LSexactHessian式は本ドラフトの直接微分で、docsのsolverJacobianと同一視しない |

技能のtopic summariesにはsinglecurve par swap式と複数curve説明が混在する。ここでは既存コードと一次資料/直接導出を優先し、parswap=(1-Dlast)/annuityを一般dualcurveの価格式に使わなかった。

残る未確認: 主12quote日付fixtureの実際のrank・runtime・二次微分精度、全case count、同時絡むcurvevariant、mainartifactの保存/復元、source/research独立review。scratchの良い小例だけでこのリストを完了にしない。

## 13. 日付の具体入力例と実データへ進む前の条件

最初のdate oracleに使える完全指定例: valuation_date=2026-12-28、as_ofはsynthetic publication_atの前/後2状態、CAL_SYNTH休日={2026-12-25,2027-01-01}、weekend=(Sat,Sun)、coupon=[2026-12-24,2027-01-04)、ACT360、notional=1e7、observationsのfixings decimal={2026-12-24:.03,2026-12-28:.031,2026-12-29:.029,2026-12-30:.032,2026-12-31:.028}。daily accrual weightsは[4,1,1,1,4]/360、alpha=11/360、G=(1+.03*4/360)(1+.031/360)(1+.029/360)(1+.032/360)(1+.028*4/360)。publication_atはfixtureのtimestampとして各observationの次businessday09:00 UTCに明示（SOFR実際の公表時刻と呼ばない）。2026-12-28 08:59UTC/09:01UTCで2026-12-24のfixingが未知/既知へ変わる。missing recordがpublication後に発生した場合にはforecastへ逃げない。

modified-following date oracle: contractual end2027-01-31(Sunday)はfollowing2027-02-01(Monday)、modified-following2027-01-29(Friday)。yearfracの計算がunadjustedend/adjustedendのどちらに対するものかをcontractに保存する。leap-case=[2028-02-28,2028-03-01)のACT365 alpha=2/365、ACT360 alpha=2/360。fixed365 curve timeとは別のaccrual unitとしてテストする。

市場データ版にはas_of同期した各tenorOIS/IRS/basis quotes・bid/ask・quoteunits・各契約のindex/schedules/spot/payment/resetlags・CSA担保通貨/担保報酬・fixingpublication/revision history・使用calendar版・source/reuse権を揃える必要がある。quotesだけwebから取得してmissingfixingやCSAを推測したデータをformalstudyへ混ぜない。本研究ではこの取得/利用は未承認なので、synthetic resultsをmarket validationへ昇格させない。

## 14. sourcechecks と study acceptance の別台帳

| 証拠 | 確認できること | 確認できないこと |
|---|---|---|
| docstrings/index/ruff/scopedpytest/release | module契約・既存integration・独立numericalfixturesの一致 | 全formalcase性能、実市場再現、速度採用 |
| independent source数学review | IFT/secondIFT/CF/units/dateevent分離の妥当性 | freeze後main結果の成功/失敗件数、原価/保存再現 |
| pilot | tolerance到達性・実cost・casesupportを観測 | 未実行mainへの一般化、post-hoc条件変更の無断正当化 |
| frozen main原始arrays+freshoracle+tamper+両復元 | plannedcases全件のstatus/denominator/残余/費用を再計算できる | licensed market data、publicAPIに必要な全堅牢性 |
| independent final研究review+採否 | sourcecheckと別に研究の完了/境界を記録 | 研究採用を自動的な標準器/本編accepted節に昇格すること |

このscratchで実行したもの: pure closedform4quotePV/complex-stepg/gradientcentralH、shock-halving残余、nonzero-LS brentq反例のみ。repopytest、source実装、mainprotocol/mainstudy、artifactrestoreは実行していない。
