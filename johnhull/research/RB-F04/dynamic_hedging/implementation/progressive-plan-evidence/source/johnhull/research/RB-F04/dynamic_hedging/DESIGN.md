# RB-F04 動的モデル横断ヘッジ — formal design草案 v2

2026-10-09。研究ロードマップ完遂指示に基づく実装契約。金融source・正式pilot・主実験は未実行。数式/設計の独立レビューはDESIGN_REVIEW.md、実装手順は../../../docs/superpowers/plans/2026-10-09-dynamic-cross-model-hedging.md。

基礎文書：`johnhull/research/RB-F04/dynamic_hedging/RESEARCH.md`。金融sourceと既存F05成果を変更せず、設計・実現性・レビューを正本へ保存した。candidateの精度・時間を実測済みと扱わない。

## 1. 目的と完成条件

同じ合成初期vanilla面にfitするHeston/localの二つの評価モデルを、二つの市場生成器で月次Asianの**実際に時間を進める自己資金ヘッジ**に使う。Greek/band/NNを、同じstock・固定長期call・費用・情報・原始経路で比べる。

RB-F07に接続し、モデル内部variance/vol倍率ではなく、観測した取引callの市場価格Qを同じ規則で再fitした**市場クオート感応度**から保有量を作る。

v1完成は以下を全て満たすこと。

1. common vanilla fit、条件付きAsian/取引call、再較正Greeks、cash会計の数値証拠が保存・再検算される。
2. frozen rosterの全market/policy/seed/level/training attemptを実行又は理由付き失敗として保存する。良いseed/経路だけで結果を作らない。
3. Q主評価とempty-claim/drift診断、全費用、3図、artifact-only notebookを保存する。合成Pdriftはsecondary optional。
4. 独立reviewがsource/protocol/pilot/main原始証拠と結び付けられる。

NN優越、model gap検出、速度優位は完了条件にしない。unknown/不支持/失敗も成果として残す。静的shock、欧州callだけの結果、既存RB-F04価格比較で動的Asianヘッジが完了したとは呼ばない。

公開API/`__init__`/依存は変更しない。hullkitはTorch-free、学習はdeep_hedge_priceのprivate module。rough、execution/LOB、real-data fit、funding/IM/capitalはv1範囲外。

## 2. 固定する契約・モデル・観測

| 項目 | v1 candidate値 |
|---|---|
| 初期spot/r/q | 100/.03/0、通貨単位はspotと同じ |
| Heston | v0=.04、κ=2、長期mean variance=.04、ξ=.3、ρ=−.7 |
| claim | cash-settled arithmetic Asian call、K100、T1、quantity1 |
| claim観測 | t=j/12、j=1..12。S0を含めない |
| hedge日時 | 主はt=i/12、i=0..11で固定。24/48はselected Greek/bandの取引頻度診断。t=1は観測・決済・手仕舞いのみ |
| U1 | stock+cash（call価格は観測できる） |
| U2 | stock+cash+固定欧州call K100,T*=1.25。rolling ATMではない |
| half-spread | stock.0005、call.005。init/interim/finalに同じ規則 |
| 制約 | stock/call各−2..2契約。raw targetと制約後holdingを両方保存 |
| cash | borrow/lendともr、cash-settled claim、q0の主条件 |

claim memoryはA=確定済み月次spot sum、n=観測count、m=12−n。月次時点は観測をA/nへ追加してから新holdingを決める。内部SDE stepsやhedgegridを増やしてclaim観測を増やさない。

market generator G、valuation M、policy Π、training generatorを別IDにする。Gがstockとcall実価格、Mが価格/Greeks、Πが保有量を決める。Mの理論midで約定したことにしない。

## 3. 初期面fit

- fit25点：T={.25,.5,.75,1,1.25}×K={80,90,100,110,120}。
- holdout12点：T={1/3,2/3,1.125}×K={85,95,105,115}。
- 独立Heston CFを合成quote truth、Heston marginalからlocal varianceを構築する。
- full calendar-time local PDEで37点を再価格する。各価格の絶対誤差≤.001通貨、独立CF order/cutoff差≤1e-8をcandidate gateにする。
- local surfaceはT*=1.25まで作る。T≤1のfieldを一定延長したことにしない。
- 各quoteのerror/support、density/cutoff/grid/domainのrefinement、wing/early-proxyを保存する。

このv1は既知Hestonパラメータの合成common fit。optimizerによるHeston parameter recovery、市場データ較正、有限37点以外の全価格面一致を主張しない。

## 4. 主市場生成器の数値規約

### 4.1 Heston：drift-implicit sqrt-CIR + adapted stock log-Euler

旧RB-F04 full-truncationは負のraw varianceを保持する。負stateをCFのcurrent vへ渡せない。**max(v,0)をcall pricingだけへ貼って整合的Qと宣言しない。** 旧core/publicは変更しない。

**CM2 lognormal variance候補は不採用。** そのvarianceがlognormal tailを持つため、次のold-v stock log-Eulerの2step株価2次momentが無限となる。有限sampleのsample SEが小さくても、MSE/variance/通常SEの根拠にならない。旧LN scratchはauxiliary-control identityの有限sample仮検証だけであり、新scheme精度の証拠に使わない。

新private candidateはLamperti y=√vのdrift-implicit CIR。a=(4κvbar−ξ²)/8=.02875>0、b=κ/2=1、c=ξ/2=.15、d=1+bδ、u=y+c√δZvとして

\[
Z_v=\rho Z_S+\sqrt{1-\rho^2}Z_\perp,
\]
\[
y'=\frac{u+\sqrt{u^2+4da\delta}}{2d},\qquad v'=(y')^2,
\]
\[
u<0\text{ では }y'=\frac{2a\delta}{\sqrt{u^2+4da\delta}-u}
\text{ の同値な数値安定式を用いる},
\]
\[
S'=S\exp((r-q-v/2)\delta+\sqrt{v\delta}Z_S).
\]

ξ=0はexact deterministic CIR variance transitionを別branchにする。stockは旧vを使うので、各discrete stepのE[S'|past]=S exp((r−q)δ)。varianceの正値化を価格/Greek clipとは混同しない。overflow/nonfiniteはfailure、clipしない。

このschemeはcontinuous Hestonの近似でありexact Heston/Broadie–Kayaではない。finite-step joint-law、CF callとのmartingale gap、Greek/P&L差を保存する。主levels192/384/768 peryear、独立selected refinement1536。旧full-truncationはscheme差の診断へ残し、moment未確認の試作をCI oracleにしない。

#### 固定gridの4次momentを数学gateにする

P&L MSEのSEには株価2次だけでなく4次momentが必要。正値だけでは十分でない。

`y'≤y+c√δ|Zv|+√(aδ)` とYoung不等式により、A=Σδv_iは `C_(N,ε)+(1+ε)c²δ²||L||F² ||Z_v||²` で上から抑えられる。Lはstrict lower-triangularの1行列、`||L||F²=N(N−1)/2`。Cは有限の決定的定数。

株価p次をexponential martingaleとCauchy–Schwarzで抑えると、`E exp((2p²−p)A)<∞` が十分条件。p4、ε=.01ではGaussian二次式の係数条件はT1で.6363、T1.25で.99421875<1。ρに依存せず、主候補ρ−.7も含む**固定finite-grid**の有限4次が成立する。

別の直接boundとして `v'≤(y+c√δZv)²/d²+2aδ/d` から後退mgf係数
`η_i=λδ+η_(i+1)/(d²−2c²δη_(i+1))`、λ=2p²−p、η_N=0を得る。各分母が正であることを保存する小checkを候補protocolへ入れる。p2/3/4、T1/1.25、192/384/768/1536peryearの全24cellで正分母を確認済み（`design/implicit_cir_moment_bound.json`）。

bounded actions、call≤S、Asian≤月次spot平均、有限取引回数によりP&L4次も有限。**uniform dt convergence、continuous-model4次の証明、解析Greek導関数のmoment、有限Nの精度達成はこのboundで認証しない。** local generatorはglobal bounded variance/wing規約を確認して同じ4次根拠を保存する。

### 4.2 Local：calendar midpoint / spot left

\[
a_i=\sigma_{base}^2(t_i+\delta/2,S_i),\qquad
S'=S\exp((r-q-a_i/2)\delta+\sqrt{a_i\delta}Z_S).
\]

未来spotは使わない。calendar timeをremaining-time0へリセットしない。市場Gの倍率は常に1。fieldの支持/wing/early proxy/failureは保存する。

既存field.evaluate(0,S)はS0以外unsupported。t0 spot restart/Greekには上のmidpoint規約を使い、t0 cacheはS0近傍[99.5,99.75,100,100.25,100.5]を別表にする。S全域をt0へ貼らない。t0のS-bumpとδ/2でclosure biasを独立測定する。midpoint規約は数値scopeの変更として明記する。

### 4.3 traded callのQ整合性gate

Heston actual callはconditional Heston price、local actual callはbasefieldのcalendar PDE price。どちらも連続モデルの値を十分精度のsurfaceとして共用する。有限-step市場経路とのズレは別の予算。

- 独立one-step conditional quadrature/MCでstockとcallのdiscounted gainsを検査。
- 18事前statesでδ=1/192,1/384,1/768、δ/2refinement。
- callのconditional one-step biasの保守的な累積指標 `768*max_abs_bias_at_1/768` ≤.01通貨をcandidate gateにする。reference quadratureの未収束をsmall biasと数えない。
- testのdiscounted gainsの全体平均・固定state binsも6SE+reference errorと比較する。binはpilot固定、原始count256未満はunknown。
- これは全適応方策のno-arbitrage証明ではない。CF/PDEとのズレ、field/price補間drift、生成器の離散化を別記する。

## 5. 取引call surfaceを共用する

main path×dateでCF/PDEを逐一解かない。

- Heston：49dates（12/24/48hedges共通のsupergrid）×spot/varianceのprice table。S65nodes=geomspace(50,200,65)、v33nodesは[0,.08]の17等間隔点の0を1e−5へ置換し、(.08,.5]の16等間隔点を追加。v=.04を含む。C/CS/Cvは同じC¹以上のprice spline。
- local：各倍率ℓで一つのcalendar PDEをT*=1.25から後退し、49snapshotsを保存。ℓ候補7nodes [.25,.5,.75,1,1.5,2,4]、S65nodes上記。actual G quoteはℓ=1。
- splineは固定not-a-knot tensor cubicを各axisへ順次適用する線形operator。positive priceをclipして作らず、補間後の価格bound/支持を検査する。線形θ補間でℓ=1のnodeに左右別のCθを作らない。coarse θaxisにも4nodes以上必要。
- finite-positive rawprice、Cθ、CS、boundary/reference/domain checksを保存。Cθのmonotonicityと一意rootは価格曲線の各pieceの微分/extremaから検査する。単に二つのendpointの符号が違えば唯一解と扱わない。
- independent selected CF/PDEのprice .001、CS .002 stock units、scaled Cθ .01通貨をcandidate絶対gate。grid倍密度で同じ量を確認する。
- bounds外はunknown。nearest extension/price clipで成功にしない。

## 6. 毎rebalanceの一quote state fitとF07

初期fullvanilla fitとは別に、観測call mid Qへ **C_M(t,S,θ_M)=Q** をfitする。

- Heston θM=current v、κ/long-run/ξ/ρは固定。
- local θM=ℓ、条件付きforecastではt以降のℓ σ_base²(u,s)を使い、ℓを固定して進める。次の実rebalanceで再fit。
- local倍率はlimited forecast closure。新しいstochastic-vol-factor SDEやfuture fullsmile fitではない。
- actual latent vはGのQ生成とsource diagnosticだけ。NNのfeature/Greekfitの初期値/直接teacher stateへ渡さない。
- fit boundsはcall/Asian cache支持域の共通部分、初期anchor Heston.04/local1、scaled scalar bracketing。xtol/rtol1e-10、maxiter100候補。
- bounds、非一意、solver failure、支持外、Cθ悪条件を保存。前stateや0を黙って代入しない。

R=C−Q、t/A/n固定、θ局所一意でCθ≠0なら

\[
\theta_Q=1/C_\theta,\quad \theta_{S|Q}=-C_S/C_\theta,
\]
\[
\boxed{V_Q=V_\theta/C_\theta},\quad
\boxed{V_{S|Q}=V_{S|\theta}-V_\theta C_{S|\theta}/C_\theta}.
\]

主U2 targetはh_call=VQ、h_stock=VS|Q。同じmarket Qに対するcall契約数とstock数量なので、v/ℓの内部感応度を直接並べない。単調scalar座標変換に不変。raw Delta-Gammaは任意diagnosticであり主定義ではない。

悪条件を次で検査する。

- state scale sθ=(.04,1)、1cent quote bumpによるstate move `κQ=.01/|Cθ sθ|`。κQ>.25はcandidate未解決。
- independent Cθ error δJを保存、`|Cθ|<=3δJ`なら未解決。
- raw label covariance/spline誤差からhS/hQのSEとdeterministic errorを伝播。単にglobal-relative-J normだけで比を認証しない。
- θ/spot3幅bumpと**Q/Sの再較正bump**をselected statesで照合。boundsで通常IFTを保証しない。

## 7. 条件付きAsian教師・制御変量

### 7.1 normalized priceとchain rule

x=(12K−A)/S、D=exp(−r(T−t))。

Hestonはf(t,v,x)=E[(Σfuture S_j/S−x)^+]とすれば

\[
V=DSf/12,\quad V_S=D(f-xf_x)/12,\quad V_v=DSf_v/12.
\]

localはz=logS、w=logℓでf=f(t,z,w,x)だから

\[
V=DSf/12,\quad
\boxed{V_S=D(f+f_z-xf_x)/12},\quad
V_\ell=DSf_w/(12\ell).
\]

localのfzを落としてHeston homogeneity式を流用しない。x≤0なら全future spot正なのでexact linear branch。m=0はsettled payoff/手仕舞い、通常Greek不要。linear branchのscalar fit不要性はstatus `not_required_linear_claim` として明示し、未知の0/0比を計算しない。

### 7.2 最後のstock incrementのconditioning

同じ月次claimに対し最後のinternal stock stepだけ解析的に積分する。left stateに条件付けるとfuture sumはb+c exp(μ+σZ)であり、positive effective strikeのlognormal call/negative strikeのlinear branchを使う。future varianceはclaim payoffに直接入らない。

**last-step conditioningだけで十分なSE削減があるとは仮定しない。** scratch GBM N4096でprice SE約.1266のままという事実をpilot設計へ反映する。

### 7.3 known auxiliary GBM geometric control

main教師候補を `CE_last(H_model−H_aux)+E[H_aux]`、β=1固定とする。auxは同じstock Brownianのconstant-vol GBM、m残り観測のgeometric average Gc。

\[
H_{aux}=\frac{m}{12}(G_c-k_{eff})^+,
\quad k_{eff}=(12K-A)/m,
\]
\[
\log G_c\sim N(\log S+(r-q-\sigma_c^2/2)\bar d,\ \sigma_c^2c_d),
\quad \bar d=m^{-1}\sum d_j,\quad c_d=m^{-2}\sum_{i,j}\min(d_i,d_j).
\]

d_jは実際の残存月次fixing日時。k_eff>0の期待値は通常lognormal call期待値、k_eff≤0はlinear。Heston/local自体のgeometric価格が解析既知とは仮定しない。解析既知なのは**別のauxiliary GBM**。

- Heston σc²=long-run+(v−long-run)(1−exp(−κτ))/(κτ)。
- local σc²=ℓ σ_base²(first future step midpoint,S)。
- σcはstate dependent。S/θbumpではauxsimとanalytic meanも同じ定義で変える。
- model/auxを同じlast stock Zでconditionする。m=0/negative threshold/σc0を別処理。
- raw/conditioned/CVのmean、SE、cross-component covariance、同じNの比較を全て保存。CV個票がnegativeでも期待価格boundでclipしない。
- β最適化/QMC追加はv1対象外。β1が役に立たないstateも保存する。

### 7.4 cacheの形と誤差

- exact main hedge dates（12主条件、24/48はpilot refinement、monthly nは各date固定）。時間をinterpolateして観測jumpを跨がない。
- Heston：9state-v nodes [1e−5,.005,.01,.02,.04,.08,.16,.32,.5]×33threshold nodes候補。上限13nodesは追加 [.0025,.0075,.03,.06] のsorted union。
- local：9S nodes=geomspace(50,200,9)×5ℓnodes [.25,.5,1,2,4]×33thresholdを初期候補、17S=geomspace(50,200,17)×7ℓnodes [.25,.5,.75,1,1.5,2,4]×65thresholdを上限候補。call/Asian fitboundsはHeston [1e−5,.5]、local [.25,4] で共通。bounds拡張を単なるrefinementに隠さない。
- thresholdは各dateの残りmに応じ中心x=m、scale s=.15√m、range[0,24]を固定する。33nodesでは左右16区間：左 `m−s sinh(linspace(asinh(m/s),0,17))`、右 `m+s sinh(linspace(0,asinh((24−m)/s),17))[1:]` の連結。65nodesは左右32区間。同じrangeでnear-strikeを細かくし、x=0/m/24を含む。positive xが支持外ならunknown、x≤0だけexact linear。
- t0 Sだけは§4の専用near-S0表。t>0のS全域表を初期へ流用しない。
- 一つのglobal 768-step IID driverをdate/node/同じMの全restartへ再利用する明示CRN。driverはmarket/train/test/oracleから独立。
- nodeを独立標本として数えない。各node原始分母はN、node間の共有path cluster covarianceを保存する。
- Nprefix={1024,4096,16384,65536}。モデル別に最小qualified Nをpilotで選ぶ。選ばれたNを全該当cacheで使い、mainで成功until Nを増やさない。
- independent IID16blocks（Nは16の倍数）のcurve momentsを保存し、同じfixed not-a-knot linear tensor cubic operatorを各blockへ適用してC/VS/Vθ/hS/hQの相関を保持する。node varianceだけから独立SEを足さない。call denominatorは独立精度評価付きのdeterministic surface、teacherのblock random誤差とは別に伝播する。
- priceとGreeksは同じsmooth f surface。θ=nodeでも通常微分とderivative errorを検査する。

last primitives `(b,c,μ,σ,aux_logG_prefix,aux_last_loading)` とblock summariesを保存する。全node×N×future-stepのnormalを保存しない。saved primitiveからCE/CV curve/means/SE/derivativesを再算出できる。ただしそれだけで前段SDEの全byte replayを証明したとは呼ばない。freshのreserved selected restartで前段を再生成し、許容差でprimitiveを照合する。

### 7.5 pilotの固定精度gate

18selected states：t={0,1/12,.25,.5,.75,11/12}×3scenario。t>0のS={80,100,120}、v={.02,.04,.08}、A=n*100。t0 S={99.95,100,100.05}。common QはHeston conditional callから作り、両Mをfitする。24/48refinementの追加代表dateは別ID/元分母で保存する。

candidate targets：priceSE≤.03通貨、hS SE≤.002 stock、hQ SE≤.005 call、quoted derivative uncertaintyのfinite checks。caseがinvalid/未収束ならqualifiedでない。oracle N/SE不足は価格一致と数えない。

独立参照差は6SEにreference/finite-h/time-grid errorを加えて比較する。加えて実務的な絶対error budgetを固定する：selected hS/hQ差≤.01units、call価格差≤.001、Asian価格差≤.05通貨。

全pilot Greek/bandで次の事前Nprefix（1024→4096→16384→65536）、state-grid refine、SDE768→1536の各P&L RMS差≤.05通貨、MSE差≤max(.001通貨²,.02*基準MSE)をcandidate numeric gateにする。65536でSE未達なら主main未着手でsourcefreeze前revisionへ戻る。最高Nの再精度比較は独立reserved stream/格子を使い、未予約262144を勝手に足さない。達成できなければ教師改良/予算revisionへ戻る。主Asianを欧州callに変えて完了にしない。

これらをv1 candidate gateとして採用する。main後に緩めない。proxyのscratch達成を本物localfieldのgate達成と数えない。取引頻度12→24/48は経済的な方策/費用条件の変更であり、同じモデルの数値誤差gateにはしない。selected Greek/bandで別診断し、近接を受入の必要条件にしない。内部SDE・teacher・補間の精度予算とは分離する。主12回の全44cells/12fitsを優先し、24/48でNNを再訓練したと主張しない。

## 8. 方策rosterと情報

各G/Uで11policy：no hedge、Heston/localのmarket-quote Greek2、Heston/localのband2、訓練G2×init3のNN6。G2×U2で**44主cell**。各cellに3test seeds×3SDElevelsがある。

U1のstrong targetはquote exposureをstockへ射影したminimum-variance hedge：hS=VS|Q+VQ βM。Heston βM=CS+Cv ρξ/S、local frozen-multiplier forecast βM=CS。VS|Qだけをstrong stock-only hedgeと呼ばない。U2は§6のtwo-asset target。

bandのextra predicted loss SDは `sd=sqrt((h_old−h_target)^T Σ_M (h_old−h_target))`、U1はstockだけ。具体則は `sd≤wならold`、`sd>wならtarget+(w/sd)*(old−target)`。width候補{0,.01,.02,.05,.1,.2}通貨。同じU/Gのtrain-validationでGreek/各bandを選ぶ**algorithm**をfreezeし、testで選び直さない。baseline ID/選択score/全failed candidateを保存する。

Σ_Mは次のrebalanceまでのcontinuous diffusion局所covarianceにΔtを掛ける。

\[
\Sigma_H/\Delta t=v\begin{pmatrix}S^2&S(SC_S+\rho\xi C_v)\\S(SC_S+\rho\xi C_v)&(SC_S)^2+2\rho\xi SC_SC_v+\xi^2C_v^2\end{pmatrix},
\]
\[
\Sigma_L/\Delta t=\ell\sigma_{base}^2 S^2\begin{pmatrix}1&C_S\\C_S&C_S^2\end{pmatrix}.
\]

これはlocal forecastでℓ固定なのでrank1になるという仕様。null方向のportfolio差はsd0となりbandが取引しない。full-rankと偽装するridgeは加えない。PSD、Heston ξ0/local limit、rank1 null direction、w0/sd0を独立手計算で検証する。finite-step市場covarianceとのズレはpilotで別計上する。

observablesは9features：logS/K、t/T、A/(12K)、n/12、Q/K、oldstock、oldcall、stockspread、callspread。actual v、G ID、future shock/payoff、Greekfitの内部stateをNNへ渡さない。NNは直接policy、金融SDE/価格をautogradで微分しない。

制約後holdingは合法portfolio ruleとして保存し、raw target/拘束件数を残す。calibration bounds failureとaction constraintsを混同しない。数値failureのimplicit hold/0/nearest fallbackは使わない。raw policyの全体P&Lが定義できなければunknown。別safe/emergency policyはv1で増やさない。

## 9. 自己資金・premium・費用

ex-dividend prices P_i=(S_i,Q_i)、前holding h_{i−1}、区間の一単位CF D_i。

\[
B_i^-=B_{i-1}^+e^{r\Delta t_i}+h_{i-1}\cdot D_i,
\quad B_i^+=B_i^- -\Delta h_i\cdot P_i-\sum_a\lambda_aP_i^a|\Delta h_i^a|.
\]

B_0^−=common reporting premium p0、h_{−1}=0。Tでclaimを一度支払い、Δh_T=−h_{T−}でstock/callをliquidateしてfeeを払う。T*callのT価格回収とcall payoffを二重計上しない。

独立discounted-gain式で全pathsを再算出する。q/別CF fixturesでは実cash支払日時をeventとして反映する。借入/貸付r同一、funding/IMなし。

p0はfreeze前の独立Heston arithmetic Asian pilot（65536 IID paths、1536steps/year、reserved独立seed、別実装の直接MC）から固定する。同じpremiumを全G/M/Πへ使う。p0をexact fair valueと呼ばずMC SEとscheme errorを保存する。MSEの主比較はこの固定p0を条件とする。variance、mean loss、premium除外loss、G別fair-price gapとp0の推定SEを別に表示する。

zero-costは同じholdingにfee0を適用するcounterfactual。zero-cost最適NNと呼ばず新たな独立試行にも数えない。

## 10. 学習・OOS・必須Q診断とoptional Pdrift

- 主訓練G2×U2×init{11,29,47}＝12fits。価格付きmarket dataはfine768。
- candidate train8192、validation2048/G。testは後述別streams。元price failure pathをsilent dropしない。
- architecture9→32→32→2 tanh、action各±2、U1はcallaction0固定、CPU float64、512updates/batch256/Adam.003/cap300s候補。
- scalerはtrainのみ。全featureの単位、zero-variance featureの固定scaleを保存。sameinit/batch pairingのscopeを明記する。
- lossはdiscounted net P&L MSE。CVaR学習は増やさずES95を評価する。
- global NumPy/Torch RNG/device/threadsはrestore、local generators、主device固定。train data pricesはconstants、past holdingsはBPTTでつながる。
- attempt開始/更新完了/last-finite weights/nonfinite/timecap/overrunを記録。requested512未達、cap超過は主completed familyの一員として認証しない。全失敗weights/log/costを残す。
- test生成/読み込みはfit/validation選択完了後。checkpoint・band・設定・seedをtestで選び直さない。
- NumPy weights replayとTorch training/inferenceを許容差比較。artifact-only checker/notebookでtrainを呼ばない。

### Q主評価

N candidates8192/16384/32768×3test seeds。pilotのGreek/band worst-case MSE-SEとmean-loss-SEから選ぶ選択式をfreezeする。目標mean-loss SE≤.01通貨、MSE-SE≤max(.001,.02*pilot baselineMSE)、最小N8192。NNの事後SE不足はunknownであり、main Nを増やして有意untilを行わない。

fine Brownianを192/384へaggregate。全G/policy/levelでoriginal IDsを共有、G間はCRNだが同じspot実現ではない。antitheticなし。3test seedsと3train seedsは別のばらつきであり9倍pathとは数えない。

### 合成Pdrift診断

secondary optional。主fit/価格/variance dynamicsはQのまま、spot physical μ=r±.05に変えた別diagnostic 4096paths×3seeds、fine768。固定weights、trainingなし。同じPdriverで±driftをcoupleし、Qmainとは別ID。実市場P推定/MEMMではない。未実施なら未実施を表示し、Q動的研究の完成を止めない。

**必須Q診断**はempty claimとbounded adapted stock/call controlの平均gross/net gains、state-bin discounted gains、actualcallのone-step条件付きdrift。no-cost empty-claimのgross gainとfee負担を別表示する。stock/call/NNの見かけのdrift利用、future/information leakage、価格surface/SDE不整合が未解決ならQのrisk支持も条件付き又はunknown。optional Pmean改善をヘッジ改善と呼ばない。

## 11. 独立数値参照

1. call：別Heston CF、local calendar PDE/grid/domain/refinement、Black deterministic limit。
2. positive variance：CIR exact conditional momentに対するfinite-step bias/positivity、fixed-grid指数moment gate、stock one-step lognormal martingale、old full-truncation scheme差。新implicit schemeがexact CIR momentsを一致させるとは言わない。
3. Asian：独立conditional direct MC/CRN price bumps、別normal streams、1536step。same last-conditioning codeを参照にコピーしない。
4. auxiliary：remaining fixing time Gaussian lawと独立normal quadrature、m0/negative threshold/θ-dependent σc chain。
5. F07：Q/Sを動かして毎回θを再fitする独立bump、θ↔logθ座標不変、Cθ悪条件、node/bounds/nonunique。
6. control：GBM geometric Asian closed price/Greeks（主arithmeticと区別）、m1/2/3の独立quadrature arithmetic、cash手計算、cash/Torch/discounted identity。

pilot/freshの参照が失敗した場合はprice/Greek truthを都合よく埋めない。reference uncertainty、MC SE、bump bias、SDE error、grid error、model gapを別に保存する。

## 12. Statistical decision

全original Nのmean loss、MSE/RMSE、variance、empirical ES95、cost/turnover、constraint/unknownを表示。原始pathがunknownなら全体指標もunknown。finite subsetはdescriptiveと明記し採否に使わない。

primary NN比較は、同じ評価G/Uでvalidation選択済みstrong Greek/band baseline。各train-G familyの3init全てを表示し、一つでも失敗/unknownならfamily支持はunknown。

- 同じpathのpaired scoresを `d=L_NN²−L_B²` と `r=L_NN²−.95L_B²` として保存する。MSE/meanのper-path IID SEも併記する。random sample baselineMSEから5%閾値をCI外へ作らない。
- sourcefreeze前の正式候補は64path等長block、3test seeds内stratified block-bootstrap2000回。N8192/16384/32768で各seed128/256/512blocks。block meanのiid/finite-moment条件と近似CIを明記する。原始per-path値は保持する。
- saved `int16` resampling indices shape(2000,3,B)を全method/G/initへ共用し、block meanからpaired d/r/meanのbootstrapを再算出する。最大約6.14MB（N16384は3.07MB）。元196MB級のfull-path bootstrapと同じ有限標本分布とは呼ばない。
- 8NN families（trainG2×testG2×U2）の改善主張はBonferroni upper confidence 1−.05/8。各familyの3init全てと二つの条件d/r全てを満たすintersection-union判定なので、family内部の3init/2条件には追加α割りをしない。init平均やbestinitだけで支持しない。
- empirical numerical envelopes u_d/u_rは独立reserved streamsのSDE/teacher/grid/refinementによるpaired score変化から保存する。重み・方策・精度比較規則は固定し、refinement結果で再訓練/選択しない。**厳密な確率bias boundとは呼ばない。**
- `risk_improvement_supported`は、全3init/全original countで **`U_d+u_d<−.001通貨² AND U_r+u_r<0`** が成立する場合。絶対.001とrelative5%の両条件を、各score自身の不確実性を含めて検査する。
- trainmodel外でも上を満たす場合だけcross-generator robustnessを支持。otherwise not_supported/unknown。未達をstudy failureと混同しない。
- ES95は原始individual lossのempirical point/tail original countを副次表示し、主支持判定に使わない。blockmeanのESをtail-loss ESと呼ばない。v1のES CIは「未評価」を許容する。複数riskobjectiveを後付けで選ばない。

## 13. 保存・費用・freeze

### 原始証拠

JSON immutable metadata+non-object NPZ/CAS。

- source registry、candidate/frozen protocol、seed roster、全state/fit/policy/cell ID。
- initial quote/holdout、call price surfaces、derivatives、domain/wing/closure/support。
- teacher shared driver、last primitives、原始N、node間共有scope、block covariance、全failed nodes/reference attempts。
- main全market state/stock/call/monthly sum/count/status、policy holdings/constraints、payoff、gains/fee/P&L。fullN perpath scoresを保存。
- 全12fitのtraining/validation/weights/RNG/attempt/cap/cost。failed seedを落とさない。
- bootstrap indices/block scores、必須Qdiagnostic、optional Pdiagnostic（未実施も明示）、独立fresh/check/review。

fullfuture normal cubeをnodeごとに保存しない。coarse levelのholdingをdeterministic saved replayにより再構成する場合、raw perpath P&L/costsと全market primitives/weights/teacherを残し、保存範囲を明記する。

### 費用

unique expense IDs、status-specific必須timing keys/scopes、parent/childの二重charge拒否。未測定はNone/pending。raw recordを書き換えずreceipt/assessmentをrecord/arrays/protocol digestへbindする。

surface/fit、teacher raw/cond/CV/oracle、pilot全部、freeze、alltrain/validation/12fits/failed/overrun、test RNG/engine/call/statefit/Greek/policy/accounting/bootstrap、必須Q/独立refinement、実行したoptional Pstress、serialization/CAS/load/cold imports/savedcheck/fresh/plotsを数える。

policy-only online、quote/Greekまで含むmain、教師/学習込みcold、明示trade件数でのamortizedを別表示。精度未達methodのspeedup/回収を採用根拠にしない。

### 段階順序

1. tiny fixture（m1/2、少量paths、smokeでmain達成値にしない）。
2. pilot：全18state/初期面/conditionalprecision/4tinyNN/費用・幾何・N候補。
3. source完成→独立code/math/pilot review→**source+candidate+pilot artifact+reviewへbindしたfreeze**。
4. frozen main train/validation→全fit→test/OOS/必須Qdiagnostic/独立refinement、optional Pdiagnostic。source変更が必要なら新revision、旧結果/費用を保存し無断混合しない。
5. saved-only check、selected fresh receipt、3図、独立final review、別assessment、章/研究受入。

checkpointはsurface、teacher date、market dataset、training fit、evaluation cellの完了境界だけ。resumeにはsource/protocol/primitive identity一致が必要。金融floatはapprox、hashはprovenanceのみ。checkerはRNG/optimizer/train/network禁止、bootstrap saved indicesを使用。

## 14. 3図

1. **Common initial面＋動的quote risk**：25/12quote、18stateのC/VS|Q/VQ/ref errors、t0closure、Cθ悪条件/fit/support failure数。
2. **動的P&L/費用**：G×Uの4panel、全Greek/band/NN init、3test seeds、MSE/ES95/mean/variance、gross/cost/net、original/unknown、zero-fee同holdingcounterfactual。
3. **Cross-G＋誤差/全費用**：trainG×testG効果、各initCI、numerical envelope、192/384/768/N/grid差、online/main/cold/amortized、pending/不採用理由。

notebookはsaved-only、決定的cell ID、3PNG、guards。numerical/teaching/independent acceptance/adoptionは別。NN/Greek/market性能の採否を表示builderが創作しない。

## 15. 実現可否・サイズ・未確定判断

### 計算サイズ（見積もり、実測runtimeではない）

768fine残存steps合計は主12restartで4992、24で9600、48で18816。claimの12fixingsは不変。

- 主12teacher H9/local9S×5ℓ、N4096なら約11.0億path-step。high H13/local17S×7ℓなら約27.0億。N16384は該当部分4倍、N65536は16倍。24/48full-cacheは主12の約1.92/3.77倍なので、selected-state/dynamic pilot refinementのscopeと追加仕事を別に記録する。aux/CDF/価格差分/oracleは別仕事。
- shared global driver N4096×768×2float64は約50MB。nodeごとのfullfuture独立normal保存は数十GBになるので採用しない。
- 主12highgrid last primitives4成分で約0.21GB、auxを足した6成分は約0.31GB（N4096）。N16384では4倍、N65536では16倍。数百MB〜GB級CASとserializationが必要。48restart全量は4成分だけでも約0.83GB。
- 主test N16384×3/GのSDE合計はG2×(192+384+768)×49152≈1.32億steps。全44policy×3levelの原始P&L、12主/fine refinement holdings、market stateの保存量をpilot実測する。bootstrap indices2000×3×256int16は約3.07MB。
- 独立numeric-envelope候補は別3seeds×4096/G、768/1536steps、全固定weights/Greek/band replay。計約5660万SDEstepsにteacher/grid補助価格費用を足す。primary OOSと混ぜず、量と精度をsourcefreeze前固定する。
- NN12fitsのcap最大3600sに加え、教師/市場生成/価格surface/全検査費用。capを見積もり所要時間と呼ばない。

旧CM2-LN scratchではauxβ1の有限sample priceSEがHeston N4096約.044/N16384約.021、localproxy N4096約.0043となった。しかしLN方式のpopulation moment欠陥により、そのsample SEをCI/必要Nの根拠に使わない。auxiliary GBM期待値identity自体は有効。新implicit CIRと本物localfieldを用いる18stateのprecision/cost pilotを改めて行う。**N4096で全部安く通る前提は採用しない。** 詳細は `CONDITIONAL_FEASIBILITY.md`。

### pilotの選択・上限をmain前に固定

選択順は数学moment→actualfield selected18stateのraw/cond/CV→hS/hQ ratios→coarse full12cache→small全Greek/band dynamic→12/24/48・teacher N/grid・SDErefinement→tiny4NNと費用。pilotの入力roster・Nprefix・精度gate・failures・全費用を保存し、failed状態を除いて最小Nを選ばない。

候補maxはN65536・highgrid・48hedges・1536selected SDEまで。上限まで自動に全直積を回す規約にはしない。各phaseの実測path-step/sと費用から、次prefix又はgridの予定expenseと保存sizeを記録してから実行する。最高候補でも精度未達なら未支持とし、sourcefreeze前revisionする。rootが正式planでphaseのwork/cost capを固定する。

### v1として決めた事項

1. priceSE .03、positionSE .002/.005、P&L .05など§7の候補精度gateを採用。未達ならsourcefreeze前にrevisionし、旧失敗/費用を保持する。main後の緩和は不可。
2. conditional Nは65536、highgrid、主12hedgesをv1 candidate上限。24/48はselected Greek/bandの取引頻度診断であり、精度近接や全NN再訓練を必須にしない。上限まで全直積を自動実行しない。
3. 計算jobを10億path-step以下、NPZを256MiB uncompressed以下に分割し、date/state/path-chunkで再開可能にする。総実行時間を保証する値ではない。各次段階の予定path-step/保存byte/実測費用を先に記録する。訓練attempt cap300秒は全12fitsで共通。
4. 共通premiumは§9の独立Heston pilot値とSE。主MSEは固定premium条件付きの比較。
5. safe policyは増やさない。Pdriftはsecondary optional、Qdiagnosticは必須。64path block-bootstrap、paired d/r二条件IUT、全原分母/全initを維持する。bootstrap CIは名目近似で、有限Nの被覆保証ではない。

金融source実装前に数学レビューを通し、正式pilot・費用・sourcefreezeを主実験前に行う。

## 16. private file职责・依存・checkpoint案

rootのmap案に合わせ、金融/研究/学習を次の小単位に分ける。公開API・依存・`__init__`変更はない。

| 新private file | 責務 | 主要再利用・不足 |
|---|---|---|
| hullkit `_dynamic_hedging_core.py` | implicit sqrt-CIR/stock・local driver、原始recorders、月次Asian memory、cash/gain | `_model_dynamics.py`のnormal aggregation/parameter conventions、`hedging.py`のstock会計。旧fulltrunc/current-vCFはそのまま代替不可、terminalcall売却fee/CFを追加 |
| hullkit `_dynamic_hedging_conditional.py` | last CE、aux GBM、saved primitives、curve labels/16blocks | 既存Asian unconditional price/controlを参考、条件付きA/mとnormalizedx/local spot chainは新規 |
| hullkit `_dynamic_hedging_surfaces.py` | calendar call snapshots、C1 conditional cache/derivatives、bounded scalar fit | `_heston_local_surface.py`のfield/support、既存Heston/localPDE。T*1.25/t0closure/callstate面は新規、価格面同一の導関数を維持 |
| hullkit `_dynamic_hedging_risk.py` | F07IFT positions、Σ/PSD、band、paired stats | `_quote_risk.py`のcoordinate原則。singlequote scalarIFT、rank1 band、shared blockindicesは新規 |
| deep private `_dynamic_hedging_policy.py` | CPU Torch9feature2action、12attempts、NumPy export/replay | 既存policyのBPTT/previous holdings。5feature1assetを公開変更せずprivate2assetへ |
| deep private `_dynamic_hedging_study.py` | protocol-bound phase runner、allattempt/check/checkpoints/costs | 既存simulation/pnl/risksは数式比較に再利用、call+AsianCF原始再検算とQdiagnosticを追加 |
| research `reference_methods.py` | 独立CF/PDE/direct MC・3幅bump・quad/cash hand references | production CE/教師coreをoracleへコピーしない。別streams・selectedstate/費用・失敗を保持 |
| research protocol/analytics/build_notebook | originalroster/sourcefreeze/arrays・採否・saved-only3図 | F05/F08の保存規約を参考に共通インターフェースを固定、金融source依存registryはtransitive実依存を漏らさない |

checkpointはsurface/teacher date/market dataset/fit/evaluation cellの完了時だけ。perpath/peroptimizerstepの大量I/Oを増やさない。原始recordはimmutable、complete expense keyset/statusscopeがなければsaved checkerをPASSにしない。

完成前のtiny E2Eは2fixings・少量paths・toy surfaceで会計/IFT/12fit roster失敗保存を確認する。正式12fixings/原始分母をそれで受け入れたとは呼ばない。fullpilotは金融sourceと数学scheme review完了後。

## 17. 一次資料・実読・probe

既存RESEARCH記載のDeep Hedging [1802.03042v1](https://arxiv.org/html/1802.03042v1)、drift [2111.07844v3](https://arxiv.org/html/2111.07844v3)、S038 [2407.21138v2](https://arxiv.org/html/2407.21138v2)、option hedge [2504.06208v3](https://arxiv.org/pdf/2504.06208v3) は別々の論文として使用する。

追加実読：[Chan & Joshi, First and Second Order Greeks in the Heston Model](https://fbe.unimelb.edu.au/__data/assets/pdf_file/0012/2591796/211.pdf) §1、§2、§3.1。価格schemeとGreek推定の違い/不安定性を確認した。LN正値化だけでstock momentを保証できない点は今回独立reviewで発見したもので、同論文が本草案old-v stockとのjoint schemeを保証するとは読まない。

[Alfonsi, Strong convergence of some drift implicit Euler scheme, arXiv:1206.3855](https://arxiv.org/pdf/1206.3855) pp.1–2のLamperti transform/positive quadratic root/strong convergence条件を実読した。今回κvbar=.08<ξ²=.09なので同論文のorder1の強い条件を満たさず、order1を約束しない。上記finite-grid4次boundは本草案/独立reviewの導出、数値精度・uniform convergenceの論文定理を流用したものではない。

Andersenのauthor稿URLは取得timeout。書誌は[SSRN 946405](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=946405)を確認したが、QE-Mの式を実読済みとして採用しない。

小probe実施：aux GBM remaining6fixingsのclosed price1.9912261122676889と独立normal quadrature1.9912261122676964、差約7.5e-15。local σ(S)=.2+.001(S−100)、S/K100、T.5ではtotal Delta .5979302341、homogeneous式流用 .5701581024、欠落chain .0277721317。会計/IFT toyは既存RESEARCHの数値を参照。新主MC・学習・canonical source/F05/Gitは変更/実行していない。

### 追加の指数可積分性の一次資料

[Cozma & Reisinger, arXiv:1601.00919v1](https://arxiv.org/abs/1601.00919), §2 eq(2.7)–(2.9) / §3 Proposition3.4 / §4 eq(4.3)を独立レビューで照合した。同じsqrt-CIR implicit schemeについて指数可積分性を扱う。本条件のp4では論文の時間下限3.1111年が1.25年を上回るが、stepの定理はsufficiently-smallの存在型。192/384/768/1536の具体fixed-grid資格は上の十分条件と保存certificateで別検査する。continuous-limitの精度やGreekの分散をこの定理で認証しない。

独立probeの記録はdesign/design_probes.jsonとsource、momentの別再計算はdesign/moment_recheck.json。旧LN試作はdesign/旧probeファイルとCONDITIONAL_FEASIBILITYで無効範囲を明示し保持する。
