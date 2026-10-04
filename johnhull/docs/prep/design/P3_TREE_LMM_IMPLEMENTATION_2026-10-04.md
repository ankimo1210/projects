# P3後半：HW/BK三項木・時間依存vol・LMMの実装可能設計

作成日：2026-10-04。独立設計メモ。対象プロジェクト：/home/kazumasa/projects/johnhull。
このメモは実装・受入の完了記録ではない。プロジェクト/Gitは変更していない。scratchは/tmpのみ。
原典：同プロジェクトの「options, futures and other derivatives 11th.pdf」、Hull 11e Global Edition、Ch32 pp732–752、Ch33 pp755–768。PDF物理ページ番号と印刷番号が一致。
照合：docs/prep/design/P3_DESIGN.md、docs/prep/sections/ch32.md/ch33.md、hullkit/src/hullkit/hull_white.py/ir_options.py。
使用スキル：hull-derivatives、document-skills:pdf。式33.19はPDF p765を画像でも確認した。

## 0. この設計の完了条件と境界

要求された後半の最小の実装は、(i)HW/BKの曲線fitと木、(ii)coupon bond/欧州/複数日行使とcashflow規約、(iii)時間依存volと較正診断、(iv)LMMのjoint dynamics・fixing・両測度・非標準caps・swaption・Bermudanである。capletだけ、frozen driftだけ、BKの説明だけへの縮小は不可。

本文の要求には数値実装が必要なものと説明が必要なものがある。HW2Fのhump、BDTのa(t)=-σ'(t)/σ(t)、多曲線の割引/給付curveの役割、CEV skew、因子数への批判、一般HJMの非Markov性は教材の受入対象に残す。一般任意ボラHJM、多通貨・多曲線jointモデル、大規模G2++製品エンジン、実データprepaymentは本メモの新設エンジンへ暗黙に足さない。Ch33.3 MBSは親の別単位で要求照合する。

既存公開API・__init__.py・依存は変更しない。新しいprivate modulesとprivate dataclassesを直接教材/検証からimportする。候補：
- hullkit/src/hullkit/_ir_tree.py：三項木、曲線fit、bond cashflows、exercise rollback。
- hullkit/src/hullkit/_lmm.py：tenor/loading、測度別simulation、契約payoff、LSM/境界方策。
- hullkit/src/hullkit/_ir_reference.py：独立参照を製品ロジックと共有しないための参照用（あるいはtestsのreference helpers）。公開exportしない。
- 既存NumPy/SciPyを利用。np.interp/scipy.optimize.brentq/least_squares、必要ならscipy.stats.ncx2、scipy.linalgで十分。新依存は不要。

注意：下記「独立」は価格式・遷移・求積/有限差分/経路列挙を別に実装すること。共通curve fixture、units、契約日付を共有することは独立性を壊さない。同じproduction driftやrollbackを両側から呼ぶ比較は独立ではない。

## 1. 実装関数と返却する証拠

全てprivate。公開API拡大を伴わない関数案：
- _validate_curve(curve, event_times, model, rate_shift=0)：有限positive DF、補間/外挿規約、BK適用可能性。
- _event_grid(horizon, required_times, max_dt, sigma_breaks=(), a_breaks=())：支払/行使/fixing/σ/a節点を必ず入れる。日時を丸めてcouponを動かさない。
- _constant_hull_geometry(a, sigma_period, dt, steps, jmax=None)：原典Euler momentsと3種類branchの再現。
- _ou_step_moments(a_schedule, sigma_schedule, t0, t1)：rho、v。piecewise constantは解析積分しbreakを分割。
- _moment_matched_geometry(grid, a_schedule, sigma_schedule)：event grid/時間依存vol用、nearest-center recombining layers。
- _fit_tree(curve, geometry, model='hw'|'bk', rate_shift=0)：alpha、period_rate、discount、Arrow–Debreu Q、残差、bracket/solver status。
- _rollback(tree, terminal_values, cashflows=None, exercise_values=None, event_order='pay_then_exercise')：raw valuesとcontinuation、exercise mask。
- _zcb_lattice(tree, maturity_index)：maturityで1、node割引でrollback。
- _coupon_lattice(tree, payments, amounts, clean=False)：dirty/ex-coupon価格、coupon eventを明示。
- _hw_period_bond(t, T, period_R, dt, curve, a_schedule, sigma_schedule)：式32.15–17のR→rの換算。
- _bond_option_tree(tree, payments, amounts, strike, exercise_indices, kind, strike_type='cash'|'quoted', accruals=...)。
- _swaption_tree(tree, exercise_indices, fixed_payments, fixed_rate, notional, kind, start_indices=...)：行使時のremaining swapから価値を作る。
- _calibrate_tree(quotes, curve, parameter_spec, starts, weights, smoothness)：paramsだけでなくresidual vector、success、nfev、Jacobian singular values、各開始点の結果を返す。
- _lmm_initial_forwards(tenor, discount_curve)、_bootstrap_stationary_loadings(spot_vols, tenor)。
- _lmm_drift(forwards, accruals, loadings, alive_start, measure)。
- _simulate_lmm(tenor, forward0, loading_schedule, n_paths, seed, measure, scheme, substeps, antithetic)：fixing values、event-state forwards、spot Bまたはterminal bond、path contractsの十分な履歴。
- _lmm_cap_payoffs/_ratchet_payoffs/_sticky_payoffs/_greedy_flexicap_payoffs：pay dates・strike履歴を含む。
- _swap_rate_and_annuity(forwards, accruals, swap_start, swap_end, fixed_schedule)。
- _frozen_swaption_vol(...)：式33.18/19の近似であることを返却metadataに残す。
- _fit_lmm(...)/_pca_scaled_loadings(...)。
- _fit_bermudan_lsm(train_paths,...)/_evaluate_bermudan_policy(eval_paths, policy,...)。
- _fit_intrinsic_boundary(train_paths,...)/_evaluate_boundary(eval_paths,...)：Andersen型の独立な方策候補。
- _price_and_se(discounted_payoffs, antithetic_pairs)：pair平均を標本単位とする。

返却診断にはgeometry/state/R/α/Q/branch、curve残差、CF event convention、exercise mask、numeraire、scheme、step、seed、paths/pairs、SE、訓練/評価seed、回帰rankを残す。教材が「実装した」を表示する根拠になる。

## 2. 定数HW/BK：Hull本文に忠実な木

### 2.1 第一段階：Euler momentsと端点branch

X=R*（HW）、X=log R−α（BK）、dX=−aXdt+σdW。
本文のuniform dtではh=σ√(3dt)、X(i,j)=jh。これは本文の一次Euler momentsを再現するfixture mode。
d=-ajdt、E[Δj]=d、E[(Δj)^2]=1/3+d²。
最高/中/最低branch順にp_u,p_m,p_d。枝先は数値と同時に保存し、上下順を取り違えない。

内点：offset [1,0,−1]、
p_u=1/6+(d²+d)/2、p_m=2/3−d²、p_d=1/6+(d²−d)/2。

上端：offset [0,−1,−2]、
p_u=7/6+(d²+3d)/2、
p_m=−1/3−d²−2d、
p_d=1/6+(d²+d)/2。

下端：offset [2,1,0]、
p_u=1/6+(d²−d)/2、
p_m=−1/3−d²+2d、
p_d=7/6+(d²−3d)/2。

上記はd=-ajdt。正負jを取り違えると負確率が出る。独立側はこれらの閉形式を使用せず、
[[1,1,1],[o_u,o_m,o_d],[o_u²,o_m²,o_d²]]p=[1,d,1/3+d²]
をsolveして照合する。

jmaxは「0.184/(a dt)より厳密に大きい最小整数」なのでfloor(...)+1。ceilは整数境界で一致しない。jmin=−jmax。
a=0はjmaxなし、layer iの−i..iのHo–Lee木。
粗すぎるa dtで整数jmaxと非負性が保証されない時は刻みを縮小し、pのclip/renormalizeで黙って修正しない。全reachable nodeでsum、min、momentsを検査する。

Fixture：a=.1, σ=.01, dt=1、jmax=2、j=1 p=(.1216666667,.6566666667,.2216666667)、j=2 inward p=(.8866666667,.0266666667,.0866666667)。BK a=.22,σ=.25,dt=.5 はjmax=2、j=1 p=(.1177166667,.6545666667,.2277166667)、j=2 p=(.8608666667,.0582666667,.0808666667)。

本文の0.184係数の選択は計算効率に関するもの。rate-endpoint感度は別の有効jmax（各nodeの確率を検証）でも比較する。曲線fitだけでは枝の正しさは分からない。

### 2.2 第二段階：初期curve fit

Q_0,0=1。Q_i,jは「node(i,j)で1を払う請求権の時点0価格」であり、実確率ではない。

HW：
S_i=Σ_j Q_i,j exp(−X_i,j dt_i)、
α_i=[log S_i−log P0(t_{i+1})]/dt_i、
R_i,j=α_i+X_i,j。

BK：
R_i,j=exp(α_i+X_i,j)、
solve Σ_j Q_i,j exp[−R_i,j dt_i]=P0(t_{i+1})。
左辺はαについて厳密減少。α→−∞でΣQ_i,j=P0(t_i)、α→+∞で0。
したがって正金利BKの有限rootには0<P0(t_{i+1})<P0(t_i)が必要。横ばいDFはrate→0のlimitで有限log-shiftなし。DF増加は正金利BKでは不可能。正のDFという条件だけでは不足。

shifted BKのlower rate=−s：
R=exp(α+X)−s、
root可能条件 0<P0(t_{i+1})<exp(s dt_i) P0(t_i)。
s>=0、固定shiftを契約に明示、fitできないnegative-forward区間をclipしない。
BK/HWの負金利差とshifted BKは本文説明対象に残す。

rootはlogsumexp(log Q−exp(α+X)dt)−log targetで組むとunderflowに強い。
bracketを対数rate単位で両側拡張し、確実な符号変化後brentq。overflowのexpはdiscount→0という極限として扱い、rate capで別モデルを作らない。root残差と境界を保存。

前進：
Q_{i+1,l}=Σ_j Q_i,j p_{j→l} exp(−R_i,j dt_i)。
ΣQ_{i+1}=P0(t_{i+1})、backward ZCB値も同じDFになる。
曲線補間は既存ratesと一致する「連続複利zero rate線形補間」（Ex32.1）。log-DF線形へ勝手に変えない。
支払/行使契約に必要な範囲外を無言で外挿しない。最後のRを使う式32.15にはexpiryの次intervalのcurveが必要なので、expiryで木を終える場合もα_expiryのfitを追加する。

## 3. 期間rate Rと瞬間rate r、既存HWの要修正候補

これは価格・測度の整合性を左右する。木はR、既存hw_phiは瞬間rに対するもの。

### 3.1 連続時間Gaussian oracle（定数a、σまたはpiecewise constant）

Q測度でzero-mean OU x_t。定数a：
q(t)=Var_Q(x_t)=∫0^t σ(u)² exp[−2a(t−u)]du。
c(t)=Cov_Q(x_t,∫0^t x_s ds)=∫0^t σ(u)² exp[−a(t−u)] B(u,t)du。
B(t,T)=(1−exp[−a(T−t)])/a、a=0ならT−t。
r_t=x_t+φ(t)、φ(t)=f0(t)+c(t)。

正しいQ zero-mean stateによるconditional bondは
P(t,T|x)=P0(T)/P0(t) × exp{−B(t,T)[x+c(t)]−q(t)B(t,T)²/2}。

定数σならc(t)=σ²(1−e^(−at))²/(2a²)。
時点tのforward測度Q^tでは x_t~Normal(−c(t),q(t))。
y_t=x_t+c(t) と置けばQ^tでzero-mean、bondはDF比×exp(−By−qB²/2)。
この状態変換は全bondに共通だがQのsimulate xとQ^t中心yを混同してはいけない。

既存hw_discount_bondの返値はDF比×exp(−B state−qB²/2)。
そのdocstringはQのzero-mean OU x、hw_phi/simulate_hw_pathsもQのxとして記載されているため、−Bc(t)が欠落する疑いがある。
一方その式はstate=y（Q^tの中心状態）なら正しい。hw_zcb_optionは正しい解析分布を使うので直接の不整合なし。
hw_jamshidian_swaptionも根stateの平行移動でstrikesが変わらず、欧州価格だけの既存テストではこの式差を発見できない可能性が高い。

数値反例：a=.1,σ=.01,t=2,T=7、c(t)=.0001642926994、B*c=.0006464414005。
同じQ状態xで既存価格/正しい価格=1.000646650389。誤差は約6.47bp相当のbond price比。
修正対象とする場合は親が独立RED→GREENの順で扱う（この設計サブタスクでは変更しない）。

独立RED候補：
- 原典式32.6–8をr=x+hw_phiに代入した値とhw_discount_bondを照合。
- Q^tのGaussian densityでE_Qt[P(t,T|x)] = P0(T)/P0(t)をGH求積。
- Qでxと積分Iをjoint Gaussianとして生成し、E_Q[e^(−I−∫φ)P(t,T|x)] = P0(T)。
既存bond関数をoracleにして生成したexpectedを比較しない。

時間依存aも必要なら
rho(u,t)=exp(−∫u^t a(s)ds)、B(t,T)=∫t^T rho(t,u)du、
q(t)=∫0^t σ(u)² rho(u,t)²du、c(t)=∫0^t σ(u)² rho(u,t)B(u,t)du
へ置換する。a/σのstep knotで区間を分ける。

### 3.2 HW finite R mapping：式32.15–17

dt_i=δ、Bδ=B(t,t+δ)、BT=B(t,T)。
R=−log P(t,t+δ|x)/δなので、
x+c(t)=[Rδ+log(P0(t+δ)/P0(t))−q(t)Bδ²/2]/Bδ。

したがって
Btilde=δ BT/Bδ、
log Atilde=log(P0(T)/P0(t))−(BT/Bδ)log(P0(t+δ)/P0(t))
             −q(t) BT(BT−Bδ)/2、
P(t,T|R)=Atilde exp(−Btilde R)。

T=tなら1、T=t+δならexp(−Rδ)を厳密再現する。
a→0ではBtilde=T−t、q(t)=∫σ²。
Ex32.1のcurve kink直後にはRを瞬間rとして使用した場合の誤差が大きい。これは必須反例。
Rの拡散係数は連続状態の換算で σ_R(t)=(Bδ/δ)σ(t)。本文第一段階の「same process」はdt→0での近似、有限dtでのDerivaGem相当実装との対比を分ける。

## 4. 時間依存vol・不均一event grid

本文§32.6はaまたはσのstep functionsとsmoothness penaltyを明示する。時間依存σを研究拡張へ追い出さない。最低限constant a+piecewise σ、加えてpiecewise aも同じmoment integratorで扱える。

### 4.1 exact OU momentsを用いる層別木

区間[t_i,t_{i+1}]：
rho_i=exp(−∫a)、v_i=∫σ(u)² exp(−2∫u^{t_{i+1}}a)du。
positive v_iなら次層spacing h_{i+1}=√(3v_i)。
親X=j h_iのconditional mean M=rho_i X。
k=nearest integer(M/h_{i+1})（tie ruleは一つに固定）、ε=M/h_{i+1}−k∈[−.5,.5]。
子X=(k+1,k,k−1) h_{i+1}、
p_+=(1/3+ε²+ε)/2、p0=2/3−ε²、p_-=(1/3+ε²−ε)/2。
常に非負。各層の全親から到達する整数jのunionを保存し、その層はrecombineする。
この方式は原典定数Euler pin modeとはschemeが異なる。本文pinとexact-modeの値を同じ固定値で判定しない。

v_i=0でh_i>0ならh_{i+1}=rho_i h_i、子j=j、p=1。確率的な既存状態を1nodeに潰さない。
最初からσ=0なら1nodeでX=0。zero→positiveでは通常の3枝へ戻る。
positive→小σでhが小さくなると到達node数が増える。計算予算を越す場合は診断を出し、state/rateをclipしない。有限個のpiecewise knotという本文教材に必要な範囲でpilotする。

独立moments fixture：
a=.2,dt=.5,σ=.025,oldh=.005,j=20 →
h_next=.0291496071148、center child k=3、
p=(.2241443222,.6558266683,.1200290095)。
平均error=0、分散error=−2.28e−18（scratch）。
イベントを挿入してもcurve fitは各intervalごとに続ける。shifted BKの同じlog Gaussian geometryを再利用できる。

#### 状態・volのmodeを混ぜない

時間依存event treeではgeometryのXが「瞬間OU state」か「period-rate OU state」かをmetadataで固定する。
- 原典Euler再現mode：XはR*、h=σ_period√(3dt)、R=α+X。本文Fig32.6/7はσ_periodを入力値として扱う。
- instantaneous-OU exact mode：geometryは瞬間xのrho/vを使う。HWではR_i,j=α_i+b_i X_i,j、b_i=B(t_i,t_{i+1})/dt_i とし、S_i=ΣQ exp(−b_i X dt_i)でαをfitする。これならdtが変わってもGaussian stateのunitsを保ち、period-rate volatilityはb_iσになる。
- constant uniform-gridなら瞬間xのspacingをb倍してR* geometryを作っても同値。ただし非uniformではb_iも変わるため、σ_Rだけを各stepで入れ替え、過去stateを同じR*として運ぶ方法は正しくない。
- BKではperiod R=exp(α+X)を近似する本文geometryで進める。瞬間logrと有限period Rの厳密な変換にはconditional one-step bondの数値計算が必要。event-grid/step refinementで連続modelへの誤差を評価する。

extra terminal shiftを計算し、解析finite-Rのpayoffへ渡す場合も同じmodeを維持する。curve fit、variance、σ_R、tilde A/Bを1つのmodeの中で定義してからpriceを比較する。

### 4.2 時間依存HWの解析価格と較正

ZCB option expiry E、maturity Tの総log variance= q(E) B(E,T)²。
これは既存定数APIを変更せずprivate解析参照を作れる。
Coupon bond optionはQ^Eでx~N(−c(E),q(E))を積分：
price=P0(E)∫max(direction(Σ C_m P(E,T_m|x)−K),0) normal_density dx。
正couponならJamshidian、任意signed couponなら求積/PDEで扱う。根の存在・単調性を仮定しない。

較正残差：
[(model_i−quote_i)/scale_i]を連結し、
√w1(σ_i−σ_{i−1})、√w2(σ_{i−1}+σ_{i+1}−2σ_i)もresidualとして追加。
a固定/推定、σ節点、重みを明示。fit curveは各候補パラメータでやり直す。
価格residualとpenalty residualを分けて表示。数値param数≤quote数を原典規則として守り、低rankの識別性はSVDで報告する。
a≥0、σ≥0。logparamはゼロを表せないのでゼロvolのfixtureは別branch。
複数初期値、合成truth、held-out quote、optimizer失敗statusを検査。小residualでtruthの一意回復を要求しない。
本文例Bermudan(5..9年→10年満期)の関連quoteは5×5,6×4,7×3,8×2,9×1。
Black volをHW σへ直接代入しない。Black vol→price→model implied σ。
未来のvol非stationarityは教材で説明する。

## 5. Bond/coupon/欧州・Bermudan/American行使

### 5.1 Cashflowと行使イベント

単位：年、率は小数、元本N、coupon=N*K*accrual。元本は最終couponに別加算または合算を明示。
P(t,t)=1。bond dirty priceとclean priceを区別する。
支払日に行使するfixtureの規約はcouponを既存holderへ払い、exerciseはex-coupon（pay_then_exercise）で統一する。
t=pay_dateでaccrued=0。直前ならdirty=ex-coupon+当日coupon。
通常accrual(t)=次回coupon額×(t−前回coupon日)/(次回coupon日−前回coupon日)。
quoted strikeならcash strike=quoted strike+accrual(t)。
call/put intrinsic=max(±(dirty bond−cash strike),0)。一つのcashflowをbondにもstrike/accrualにも重複計上しない。

木bond rollback：
B_i = CF_i + discount_i Σ p B_{i+1} はcum-coupon時点。
ex-couponはCF_iを引く。APIのevent_orderでexerciseが参照する側を固定する。

Bermudan：
continuation_i=discount_i Σp V_{i+1}、
行使日だけ V_i=max(intrinsic_i,continuation_i)、
非行使日はcontinuation。満期intrinsic、権利行使後は二重行使しない。
Americanは格子上の全行使日のBermudan近似。grid refinementで連続行使へ収束することを確認し、有限gridで「連続時間厳密」と呼ばない。

### 5.2 Swaption

同一curve・単一currencyのspot-start行使時e、remaining paydates T_m：
A_e=Σ δ_m P(e,T_m)、
floating PV=N[1−P(e,T_last)]（eでreset開始）、
payer intrinsic=N max(1−P(e,T_last)−K A_e,0)、
receiverは符号反転。

行使日を追加するとremaining swapのstartもそのexerciseへ移り、maturityは固定。全行使日に同じ元のcashflowを使い続ける誤りを反例とする。
future start S>eならfloating PV=N[P(e,S)−P(e,Tlast)]。
exercise/payment/reset dateの仕様が上式の適用条件。single-curveのpar floating legを多curve契約に流用しない。

tree capletにもbond putとの等価性：
at fixing Tk、δ N(F−K)^+ P(Tk,Tk+1)
= N(1+δK)[1/(1+δK)−P(Tk,Tk+1)]^+。
paymentはTk+1、fixingはTk。σ=0やTk=0はdeterministic payoff。

### 5.3 BK Figure32.9と独立reference

flat continuous5%、coupon5%半期、bond maturity10、face100 →
root bond=99.51020873（curveからの確定CF PV）。quotedK105、American horizon1.5、a=.05、σ_log=.20。
本文N4のdt=.375、coupon scheduleは.5,1,1.5,...,10。
.375 option gridに.5 couponが乗らない。couponをnearest dateへ丸めるのは禁止。
正式event-grid implementationは例としてdt=.125なら.375 exercise/.5 coupons/10maturity全てを含む。
その格子を使った値は本文の4-step DerivaGem表示と同じschemeではない。原典はbond値を「much larger tree」で別に計算すると明記している。

表示4-step pinを再現するには、coarse option latticeのperiod Rと、conditional bondを求めるinner fine modelの状態の関係を固定する必要がある。HWのような解析変換をBKへ流用しない。
具体的候補：
1. BK log-stateの独立PDE/fine treeをinitial curveへfitし、conditional one-step bond P(t,t+.375|x)を計算。
2. −log P/.375=coarse Rの単調rootを解いて状態xを同定。
3. 同じ状態でcoupon bond価格を求め、coarse option latticeへintrinsicとして与える。
4. inner grid/domainとcoarse dtを別々にrefineし、表示cash bond/option/rateを比較。
この方法とDerivaGem内部法が一致することは未確認。表示pinは完全再現まで保留する。

本番minimumはcoupon/event完全整合の単一treeを10年まで延長し、coupon bondとoptionを同じモデルでrollbackすること。BK本文/Americanの価格手順を受入できるが、それだけでFig32.9全pin再現と書かない。
独立BK oracleはlog-stateのbackward PDE
∂t V−a x∂x V+(σ(t)²/2)∂xx V−g(x+α(t))V=0、
paydatesでCF加算、exerciseでmax。
initial curveのαはPDE側でforward killed-densityを使ってfitし、production Q helperを呼ばない。
x domainを広げ、space/timeを独立refine。time-dependent θを備えたlogr表現を使う場合はα'とaαを落とさない。
欧州にはGaussian quadrature + conditional discount MCでも比較できるがBKには解析ZCB oracleを発明しない。

## 6. LMM：index、fixing、測度、numeraire

### 6.1 契約とalive mask

tenor T0=0<T1<...<TN、δ_i=T_{i+1}−T_i。
F_i(t)=[P(t,T_i)/P(t,T_{i+1})−1]/δ_i、i=0..N−1。
ordinary lognormal LMMはF_i(0)>0、δ>0。F0はT0で既に固定。
fixing T_i後のF_i(T_i)はpayment T_{i+1}のcouponへ保存。以後そのrateをsimulationで変化させない。
活性rateはT_i>t。区間[T_j,T_{j+1})ではm=j+1、alive i≥m。
本文の「t≤T_m最小index」はreset点でleft-limit/right-limitの曖昧さがある。実装ではreset前にfixingを記録し、その後mをincrement。区間のright-continuous scheduleを使う。
片側のfloat比較でexpiry/fixingをすり抜けない。event indicesは整数で管理する。

loading λ_i(t)∈R^p、covariance c_ik(t)=λ_i·λ_k。
stationary book loadingはλ_i(t)=l_{i−m(t)}（fixingまでのwhole accrual periods）。
noiseは同じ時間step・同じpathの全alive forwardsへ共通p次元Zを使用。各forward独立にZを引くとfactor correlationが消える。

### 6.2 Drift式（relative drift）

w_i=δ_i F_i/(1+δ_i F_i)。

terminal measure Q^N：
dF_k/F_k = μ_k^N dt + λ_k·dW^N、
μ_k^N = −Σ_{i=k+1}^{N−1} w_i c_ki。
最後のrate k=N−1はdrift0。fixing前までlognormal martingaleで最も簡単な独立oracle。

rolling/spot measure Q^B：
μ_k^B=+Σ_{i=m(t)}^k w_i c_ki。
自項i=kを含む。最も近い未fix rateでもdrift0ではない。
common forward measure Q^{k+1}でのみ、そのF_kのdriftが0。
spot driftをnegativeにする、terminal自項を含める、spot最寄rateを0driftにする、fixed forwardsをsumに残す、全periodをdrift0で別々に動かす、全て必須mutation反例。

導出の独立基準：
bond volatility difference v_i−v_{i+1}=w_i λ_i。
numeraire changeより μ_k=λ_k·(v_num−v_{k+1})。
terminalはv_N−v_{k+1}=−Σ_{i=k+1}^{N−1}w_iλ_i。
rollingはv_m−v_{k+1}=Σ_{i=m}^k w_iλ_i。
テスト側でbond productsを微分し数値volを作り、production _lmm_driftの式をコピーしてexpectedにしない。

### 6.3 discount / measure weighting

Spot rolling account：B(T0)=1、
B(T_{j+1})=B(T_j)[1+δ_j F_j(T_j)]。
reset datesでP(T_j,T_l)=∏_{i=j}^{l−1}(1+δ_i F_i(T_j))^−1。
payment T_{k+1}のpayoff HはE_B[H/B(T_{k+1})]。

固定済みcaplet payoffならfixing T_kで
PV=E_B[H P(T_k,T_{k+1})/B(T_k)]
=E_B[H/{B(T_k)(1+δ_k F_k(T_k))}]。
paymentまでrateを余計に変化させる必要がなくvarianceを下げられる。

terminal：numeraire P(t,T_N)、P0(T_N)を外側に掛ける。
PV=P0(T_N) E_N[H/P(T_{k+1},T_N)]、
fixingのequivalent estimator
PV=P0(T_N) E_N[H P(T_k,T_{k+1})/P(T_k,T_N)]
=P0(T_N) E_N[H ∏_{i=k+1}^{N−1}(1+δ_i F_i(T_k))]。
最後のcapletはproduct1になる。Spot Bでterminal pathを割引してはいけない。

非tenorの時刻ではstub bond P(t,T_m)の絶対価格をlive forwardsだけからは定義できない。spot B(t)にもstubが必要。
minimumのexercise/payment/fixingはtenor上（本文Bermudan）。substepではsimulation/driftだけ進め、event payoff/numeraireはtenorで評価する。
任意非tenor行使をサポートする場合はstub dynamicsを具体化してから別仕様とする。黙ってBをpiecewise定数にして非tenorの価格を出さない。
future bond ratios P(t,T_i)/P(t,T_N)、T_i≥T_mはsubstepでもforwardsのproductから分かるのでterminal martingale検査は可能。

### 6.4 Scheme：本文log Euler＋predictor-corrector

log Euler（本文33.14/16）：
log F_k(t+dt)=log F_k(t)+(μ_k(F(t))−||λ_k||²/2)dt+λ_k·√dt Z。
「driftをその時間stepで固定」は本文scheme。全simulation開始から最後までμ(F0)を固定するfrozen driftとは違う。

predictor-corrector：
1. alive全ratesをold stateで同時predict。
2. μ_newはpredicted all-rate vectorから計算。
3. corrected log F = old log F + [(.5)(μ_old+μ_new)−.5||λ||²]dt+同一noise。
4. step終了のfixingを記録してfreeze。
λのknot/tenorをまたぐstepは分割。predictorの途中で一部ratesだけ更新して他rate driftへ使う非対称schemeは別物。
terminal drift計算はbackward cumulative sums、spotはforward cumulative sumsでO(n_rates×p)化できるが、独立fixtureでは単純double sumを使う。

実際の検証はEuler vs PC、1/4/16 substeps、MC SEを分ける。同じfinest incrementsを集計して粗step用noiseを作るとscheme差のSEを抑えられる。seedだけ一致してもtime gridsで消費順が違うとcommon random numbersにはならない。

## 7. LMMの本文契約・vol bootstrap・swaption・較正

### 7.1 Spot→forward vol

annual equal accrualならΛ_{k−1}² = k σ_k² −(k−1)σ_{k−1}²。
unequal δではbook式
σ_k² T_k =Σ_{i=1}^k Λ_{k−i}² δ_{i−1}
をtriangularにsolve：
Λ_{k−1}²=[σ_k² T_k−Σ_{i=2}^k Λ_{k−i}² δ_{i−1}]/δ_0。
差分variance<0はinput incompatible（rounding toleranceのみ根拠付ける）としてerror/status。無言で0へclipしない。

Ex33.1 24/22/20%→24/19.79898987/15.23154621%。
Table33.1の10個。2/3因子の表を使う場合、その丸めたcomponentsのnormがspot集計volと完全一致しないことを記録。
vanilla capのfactor数非依存実験では各rowを同一targetΛへrescaleしてnormを揃える。Table本文価格再現では原表のraw componentsを別fixtureとして維持し、raw/rescaledを混ぜない。

### 7.2 Ratchet/sticky/flexi

initial K1はF0(T0)+s、s=.0025、first stochastic caplet period[T1,T2]。
R_j=F_j(T_j)。
ratchet K_{j+1}=R_j+s。
sticky K_{j+1}=min(R_j,K_j)+s。
payoff_j=N δ_j max(R_j−K_j,0)、payment T_{j+1}。
strike updateに将来R_{j+1}を使わない。coupon paidとしてrateを消す前にprevious fixingを保存。
flat continuous5%はannual simple exp(.05)−1=.05127109638。
first strike=.05377109638、N100、annual dates、Tables33.1/4/5、antithetic。
Tables33.2/3は100k simulations SE約.001。exact printed last digitsをseedで合わせない。60個の個別capletとsum capを区別。

flexicap本文は「ITMなら順に行使し、最大5回」のgreedy契約。最良の5回を後から選ぶlook-ahead payoffは別契約。
先頭のpositive payoffでcounterを減らす。quota0→0、quota>=number periods→ordinary cap、quota追加でpathwise非減少。
本文3.43/3.58/3.61にはstrikeが当該段落で明示されていない。初期strike、対象期間の一次資料/DerivaGemを確認するまでpin未解決。印刷価格に合わせてKを逆推定しない。
最適multi-exercise契約を扱うならremaining rightsを状態としてLSM continuationを分けるが、本文greedy flexicapとの混同を避ける。

### 7.3 European swaption：本文近似とjoint MC

reset exercise E=T_s、swap final T_e。
current bond productsからfloating P(T_s,T_s)−P(T_s,T_e)、annuity A=Σ fixed δ P。
payer/receiver intrinsicを測度に応じたnumeraireで割引。
単一支払1-period swaptionはcaplet with exercise/payment差を揃えてBlackと一致する独立特殊例。

本文33.18のg_kはlog swap rate sensitivity。安全な一般形：
S(F)=[1−P(E,T_e)]/A(F)（start bondを1に正規化）、
H_i=∂S/∂F_i（analyticまたは独立finite difference）、
relative swap diffusion η_q=Σ_i H_i F_i λ_i,q/S0。
frozen initial-forwards variance I=∫0^E Σq η_q(t;F0)²dt、
Black swap vol=√(I/E)。

本文式に直接合わせるなら
U=∏_{j=0}^{M−1}(1+τ_j G_j)、D=Σ_{i=0}^{M−1}τ_i∏_{j=i+1}^{M−1}(1+τ_j G_j)、
S=(U−1)/D、
g_k=U/(U−1)−[Σ_{i=0}^{k−1}τ_i∏_{j=i+1}^{M−1}(1+τ_j G_j)]/D、
∂logS/∂G_k=τ_k g_k/(1+τ_kG_k)。
gの第2項k=0のsumは0。出力はrelative variance、rate-unit varianceと取り違えない。
λのstep scheduleを区間分割すれば積分はexact weighted sum。

different cap/swap tenor：
1+τ_k G_k=∏_{m=1}^{subperiods}(1+δ_{k,m}F_{k,m})。
fixed annuityはcoarse swap payment datesで作る。細かいcapletを単に加重平均してGへ置換しない。
∂logS/∂F_{k,m}=[δ_{k,m}/(1+δ_{k,m}F_{k,m})]g_k。
このJacobianから式33.19を実装できる。
PDF p765画像上もΣ_{k=n}^{N−1}と印刷されているがn未定義。OCRの誤りではない。
全swap区間を含めるk=0がMsub=1で33.18へ戻り、直接product/Jacobianとも整合する。教材に原典表記の注記を残す。

frozen approximationはMC価格のoracleではない。low/moderate volで差を記録し、高volや長いtenorを反例として近似誤差を表示する。近似一致だけでjoint dynamicsを受入しない。

### 7.4 PCA、較正、CEV

歴史データからfactor方向を求め、rowごとにtarget Λへnormを合わせる：
l_j,q=Λ_j (s_q a_j,q)/√Σ_{r=1}^p(s_r a_j,r)²。
norm0かつΛ>0は未定義。PCAのfactor全体符号反転はcovを保持する。row一つだけの符号反転はcorrelationを変える。
歴史の変化がabsolute rateかlog returnかを記録し、relativeλとの単位変換を明記する。

fit対象cap/European swaption prices、objectiveΣ(model−market)²+first/second-difference penalties。
各capletのtotal integrated norm、PCA directions、swaption approximate formulaを合わせる。合成truth/複数starts/heldout quote/SVD、curveを除くloading quote sensitivityまで診断を残す。市場の実測parameter回復を教材完了要件に発明しない。

CEV本文33.21は0<α<1、absolute diffusion η_i,q=z_i,q F_i^α。
lognormal limit α=1。absolute/relative volのunitsを分ける。
測度別absolute drift：
terminal b_k=−η_k·Σ_{i=k+1}^{N−1} δ_i η_i/(1+δ_iF_i)、
spot b_k=+η_k·Σ_{i=m}^k δ_i η_i/(1+δ_iF_i)。
CEVへlognormal μをそのまま代入しない。

本文のminimum数値説明としてforward-measure CEV caplet閉形式とα=1極限を用意できる：
β=1−α、J=∫||z(t)||²dt、
x=F0^(2β)/(2β²J)、y=K^(2β)/(2β²J)、
call forward-price =
F0 * ncx2.sf(2y, df=2+1/β, nc=2x)
− K * ncx2.cdf(2x, df=1/β, nc=2y)。
price=NδP0(payment)×call。
吸収境界F=0を採用。floorはmartingale put-call parityで求める。α=1は別branchでBlack、J=0はintrinsic。
β→0で巨大argumentになるので安定性pilotが必要、α=1近傍の無根拠thresholdでsilent model変更しない。
独立oracleは1D forward PDE/CEVのnoncentral χ² derivation。general CEV joint/Bermudanを要求するならzero吸収のschemeまで必要で、普通のlogEulerをCEVへ流用しただけでは受入不可。
本文のskew説明・閉形式・極限は残し、normal/shifted lognormal拡張とは区別する。

## 8. LMM Bermudan：完全な行使手順と独立基準

stateは行使時のalive forward vector、annuity、swap MTM。1factor loadingでも全forward vectorの経路依存は一般に1D Markovにならない。HW1Fの価格を「同じLMMのexact oracle」と呼ばない。

training/evaluation pathをseedも含めて分離。normalization/standardization、PCA/basis selection、threshold fitはtrainingだけ。
cashflowはexercise時remaining swap MTM（その時の市場stateから観測できる値）でsettle-equivalent。

numeraire N_e=spot B_e または terminal P(e,T_N)。
normalized exercise g_e=G_e/N_e。
training backwardで次の選択済みcashflowのnormalized valueをtargetにし、
C_e(state)≈E[V_next/N_next | state_e]を回帰。
ITM subsetを使用するならsample count/rank/condition numberを記録。
basis minimum：current relevant log forwards（全aliveからtrainingで選択したPC）、swap rate、annuity、二次項/交差項。factor数pだけに状態を勝手に縮めない。
g_e>Ĉ_eかつg_e>0でexercise。tieはcontinue等に固定。
fit不足ならcontinuation方策を明示、失敗を隠して0 continuationにしない。

evaluationではfitted policyを前向きに一度だけ適用し、最初のexercise後はstop。
value=N0×mean(selected G_e/N_e)、SEはantithetic pairs。
これは方策価値の下界。回帰残差やMC SEは方策suboptimalityの上限ではない。厳密価格や完成したdual intervalと表示しない。
本文Andersen型も別basisからintrinsic threshold boundaryをtrainingでfitし、同じ独立eval pathsでLSMとのpaired differenceを求める。boundaryのみの方策も一般には下界。

独立small reference：
- 2exercise dates、少数rates、1factor→1/2 substeps/period、GH9/15。非再結合conditional quadrature木を全列挙しbackward max。moment/driftはnumeraire-bond-vol差から別実装する。
- 2factorならGH3/5各factor、2exercise、各period2substepで最大(5²)^4=390625 leaves。この範囲で高次求積感度を確認できる。
- production simulationと同じEuler/PC schemeに対するexact discrete exercise valueをまず比較する。GH次数誤差、MC SE、回帰policy gap、時間刻み誤差を分ける。
- 1exerciseなら回帰不要、European joint MCそのもの。payer/receiver、period reset後freezeをこの極限で確認。
- best single-date欧州の比較、exercise dates追加でexact価格非減少はquadrature referenceに厳密適用。LSM推定値が単一欧州以下ならpolicyが悪い可能性であり、独立SEとpolicy gapを調べる。
- training上でbest deterministic single-date policyも候補に含め、training選択後evalする。eval側のmax選択で上方biasを入れない。

dualは必要時にP1/S001のmartingale基盤を再利用できるが、本メモminimumのLSMをdual exactへ言い換えない。dualを加えるなら条件付き期待値nested MC、martingale drift、outer SE、upper−lower gapを別gateとする。

## 9. 独立検証マトリクス・反例・許容差pilot

### 9.1 Deterministic invariants（価格pilotに関係なく先に固定）

| 対象 | 独立参照/反例 | 初期gate |
|---|---|---|
| 枝確率 | 3×3 moment solve、j=0/+端/−端、a→0 | sum abs≤5e−14、min≥−5e−14。負値を補正して通すことは不可 |
| Gaussian moments | exact rho/v、σ節点、zero-vol interval | mean error≤1e−13×state scale、variance error≤1e−13×variance scale+1e−16 |
| curve | Q前進とZCB backward両方 | abs DF residual≤5e−12、solver status成功 |
| HW finite R | T=t、T=t+dt、curve kink | identity relative≤5e−13 |
| contract | 元本/coupon保存、quoted/dirty payoff等価、exercise day CF順 | deterministic PV relative≤1e−12 |
| LMM drift | bond numeraire vol差、最後terminal μ=0、spot self term | abs algebra residual≤1e−13 |
| fixing | fixed Fのbitwise equality、pay dates offset1 | exact bookkeeping |
| vol bootstrap | Ex33.1/variance復元、negative increments reject | integrated variance abs≤5e−14 |
| factor norm/PCA | norm target、sign-global flip | raw 表丸めfixtureは別tolerance |
| martingale | terminal future-bond ratios、spot P/B at tenor | mean error 4SE+事前に測定したstep bias |
| caplet | Black各k、σ=0、k0 fixing | MC error 4SE+事前step allowance |

float scaleと単位を記録。百分率表示pinを小数rateに変換し、印刷最小桁のhalf-unit以上の許容差が必要。上表はdouble precision/小fixtureを想定する初期候補、経済価格の受入toleranceとは別。

### 9.2 Tree European/coupon/Bermudan acceptance

HW欧州：ZCB option解析＋coupon GH（64/128/256nodesまたはrootで分割したadaptive quad）。GHはkinkで遅く収束するので「nodesを増やしただけ」を十分な精度としない。
unitnotional priceの収束budget初案1e−5、face100なら1e−3。target参照誤差はその1/10以内。N128/256/512/1024でtree差とoracle差を記録し、価格だけの偶然相殺を避ける。
a=0/1e−8/.1/1、σ=0/.001/.01/.03、negative HW curve、短期expiry、ITM/ATM/OTM、nonflat kinkをpilot setとする。
single-exercise=欧州、Bermudan≥各single-exercise（同一tree）、行使集合supersetで非減少は離散tree上で機械精度の関係。
Bermudan oracleはPDE/quadratureに対する差とexercise boundaryで判断、上記1e−3 face100をpilot後固定する。
BKは初期curveとpositive-forward制約、σ_log=0/.1/.2/.4、flat/nonflat、quotedstrike/CFaccrual、lower-shift曲線、negative-input拒否。
PDE domainを±(6/8/10)state SDへ拡大、space/time倍化による差<price budget/10を確認してからoracleとする。σ=0ではdomain固定のPDEを使わずdeterministic CF。

### 9.3 実測scratch：Table32.3（未解決あり）

/tmp/p3-pilot.py（そのままσ_R=σと仮定）、/tmp/p3-pilot-rsigma.py（σ_R=σ Bδ/δへ換算）。
3y expiry/9y bond、face100、K63、a=.1、instant σ=.01、Table32.2 linear-zero curve、Actual/365。
解析 put=1.8092941675909984。
Q curve residual max<6e−16。

| N | 本文印刷 | σ_R=σ pilot | σ_R=σ Bδ/δ pilot |
|---:|---:|---:|---:|
| 10 | 1.8468 | 1.8657926391 | 1.8467653950 |
| 30 | 1.8172 | 1.8234351875 | 1.8170782010 |
| 50 | 1.8057 | 1.8093361706 | 1.8055229732 |
| 100 | 1.8128 | 1.8144419531 | 1.8126006433 |
| 200 | 1.8090 | 1.8097427387 | 1.8088049724 |
| 500 | 1.8091 | 1.8092800800 | 1.8089144376 |

瞬間σをRへ直接入れると大きな差。σ_R換算で主要差は解消するがN30..500には約1.2e−4..2.0e−4が残る。印刷4桁半unit5e−5を超えるのでTable全pinの受入は未完了。許容差を2e−4へ広げて完了にしない。
σ_R=σ pilotのN1000=1.80975518、N2000=1.80934024。収束は単調でない。1点のN500一致は原因特定でも収束証明でもない。

残差を解く次の具体調査（1要因ずつ、expectedを価格に合わせない）：
1. days→years：expiry1095、bond3285、curveknot1096/3287を分ける。3y/9yをcurve tableの実日数へ勝手に置換しない。
2. zero-rate interpolation/外挿、DF補間との比較、input percentageの元値/印刷丸めの区間伝播。rounding boundsで2e−4を説明できるか確かめる。
3. α_N：expiry時点のRが必要なextra-next-step fitと、expiry直前shiftやanalytic φを使う違い。P0(T+dt)がcurve kinkの右側を読むことを確認する。
4. branches：jmax strict integer条件、Euler drift −ajdt vs exact exp(−adt)、variance σ_R²dt vs exact OU。4候補を明示してoutputとmoment errorを比較。
5. period-vol/mean reversion：R=(Bδ/δ)r+deterministicだからRのσとdriftは瞬間rとは異なる。σ_R換算とq(t)の瞬間σを式32.16へ使う組合せを確認。σ_Rを式32.16へ二重投入しない。
6. discount：exp(−Rdt) vs瞬間r、Qはdiscounted state priceでありunconditional probabilityでない。child rateで割引するbugの感度を見る。
7. node bond：tilde A/B、q BT(BT−Bδ)/2、T=t+δ identity、αとstateからbondのmappingを原典式と別に求める。
8. DerivaGem/libraryの元ソースやTechnical Note16を入手できる場合は版・そのcurve conventionを確認。原典が与えない内部schemeを想像で断定しない。
9. 印刷tableのwhole-N収束/分岐変更だけを模倣せず、解析価格の独立求積とmoment/curve invariantsを同時に保持する。

### 9.4 実測scratch：LMM caplets

/tmp/p3-lmm-pilot.py、160000 paths=80000 antithetic pairs、seed73017。
T=[0,1,2,3]、continuousflat5%、3forwards、N100、ATM F0、3×2 deterministic loading norms=.25。
rows λ=(.25,0),(.2,.15),(.075,.25√.91)。
PC、substeps1/4/16、spot/terminal両方。
fixing1のBlack=.4614912096、fixing2=.6192075767。

| measure/substeps | k1 price / SE | k2 price / SE |
|---|---|---|
| spot/1 | .4608999982 / .0015567595 | .6232895161 / .0022549861 |
| spot/4 | .4615836494 / .0015536248 | .6235784793 / .0022516496 |
| spot/16 | .4621958306 / .0015548619 | .6222806297 / .0022442086 |
| terminal/1 | .4609304289 / .0016338920 | .6235479887 / .0023795175 |
| terminal/4 | .4616373200 / .0016300603 | .6238210629 / .0023760850 |
| terminal/16 | .4622684918 / .0016315944 | .6223833338 / .0023666796 |

全て約2SE以内だが、異なるsubstepsはnoise消費順が違うためstep biasを分離できていない。このpilotは漂移/割引の符号とfixing実装可能性を確認する初期証拠。正式acceptanceにはfinest Brownian incrementsの集約・複数seed・higher-vol mutation・martingale testsが必要。
高vol=.6/1.0、longtenor、correlation符号反転、freeze-global drift、spot self項削除などを受入前のpilotで走らせる。
MC価格gateは4SE+独立に測ったscheme bias。60表値はmultiple comparisonsを考慮しfamily-wise bandまたは全体chi-squareを事前固定し、失敗した行を都度広げない。
抗対称pairを2n独立標本としてSEを計算しない。

## 10. 親が実装へ進む順序と受入上の未解決

1. private geometryとQ/curve-fit（本文constant Euler fixtureとevent/exact modeを区別）。
2. Gaussian state測度の既存HW不整合候補の独立RED→GREEN（親の承認範囲/既存API semanticsを確認）。
3. ZCB/finite R/coupon/single exercise、curvekink・dirty/clean・cashflow日付。
4. BK full-horizon CF tree+独立PDE、Bermudan/American、Fig32.9 inner-bond schemeの照合。
5. σ(t)/a(t) knots、zero intervals、合成校正/SVD、本文nearby co-terminal quotes。
6. LMMtenor/fixing/numeraire/drift、Black caplet/vol bootstrap、martingale。
7. ratchet/sticky/flexicap、factor covariance、Table pin uncertainty、swaption different tenor/Jacobian/MC。
8. LMM LSM＋intrinsic-boundary＋小GH oracle、独立eval/SE/policy gap。
9. 本文説明（BDT/BK/HW2F・HJM特殊例・CEV/PCA/非stationarity/outside-model hedge）と教材/Book/portal表示証跡を親が章要求へ紐付ける。

未解決（scopeから消さない）：
- Table32.3：期間vol換算後の最大約2e−4残差。印刷全pin未完。
- Fig32.9：coarseRとinner BK bond modelの対応、全node pin/100step価格の独立再計算未完。
- Flexicap：本文strike/対象期間不明、数値3値pin未完。
- 式33.19：未定義nが印刷されている。実装は全区間sumとM=1 consistencyでk0、注記が必要。
- 既存hw_discount_bond：QxとQ^t中心yのsemantics不整合候補。修正/状態説明の決定は親が独立テストの証拠から行う。
- CEVのα→1近傍安定性、BK PDE grid tolerance、大規模LSM policy gapはpilot後に価格budgetを固定する。

この設計とscratchの一致はP3の全節受入の代わりにはならない。原典要求ID→実装→独立数値/図/配布表示のmanifestへ親が対応付ける。
