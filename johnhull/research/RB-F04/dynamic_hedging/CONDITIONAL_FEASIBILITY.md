# RB-F04 dynamic conditional evaluator 実現性メモ

2026-10-09。担当範囲：既存 RESEARCH.md と private dynamics/surface の読解、独立の小probe、数式導出だけ。正式source・成果JSON・main・Gitは変更していない。下の数量・精度は設計検討であり、正式pilot/freeze結果ではない。

## 1. 結論

**月次arithmetic Asian / Hestonとlocal / 固定K100,T*=1.25 call / 共通Qへscalar fit / 同一価格面からVS,Vθを出す完全な最小版は構成できる。ただし旧Heston CM2-lognormal variance schemeは母分散無限のため正式不採用。「last-step conditioning + N4096」だけで全state精度が成立するとは見做せない。**

現在の小規模主候補は12ヘッジ日、24/48日を精緻化比較に残す。claimの月次12fixingsは変えない。下の48日workloadは元提案のstress見積りとして保持し、正式mainが固定済みとは扱わない。

必要な変更点は次の5件。

1. Hestonは `(t,v,x)`、localは `(t,logS,logℓ,x)`。localの追加ℓ軸とspot依存を落とさない。
2. localの最後stock incrementは左端stateに条件付ければlognormalだが、その初期S/ℓへの感応度には前段pathと係数の依存もある。同じ価格面の完全なchain ruleと、独立CRN bumpで検査する。
3. 既存local fieldはt0でS0だけ支持。time-midpoint/spot-left規約、t0近傍spot-bump用sheet、元calendar-time長期PDEが必要。
4. 既知期待値の**auxiliary GBM geometric control**は数学的に利用できる。β=1固定を候補とする。正式Heston schemeのfinite momentsを先に保証し、そのschemeでSE/Greek gateを測る。旧CM2-LN試作からNを選定しない。
5. 全node独立normal保存はoriginal-highで約89.4GB。明示した共通CRN driver、または sufficient-statistics 境界を採用する。後者を全SDE再生の証明と呼ばない。

必須はC,VS,Vθ、call CS,Cθ、再較正bump、保有量/動的P&Lの精度。Gammaは追加診断とし、主研究を欧州callだけへ縮小しない。

## 1.1 重要：旧Heston試作schemeは正式不採用

独立reviewで、CIRの2 momentsに合わせたlognormal variance更新 + old-v logstock Eulerは、非退化設定の2 stepで E[S²]=∞となることが確認された。v1がlognormalなら E[exp(dt v1)]=∞。第2 stock stepを積分すると条件付き2乗meanにexp(dt v1)が現れ、stock/varianceの相関を入れてもこのlognormal exponential tailを抑えられない。one-step Q martingale propertyや有限sampleの見た目が良いことは、population variance / MSE / SEの認証にならない。

そのため:
- /tmp/rbf04-auxiliary-gbm-control-probe.json の旧Heston raw/condition/CV数値と費用は試作履歴として保持するが、sample std/sqrt(N)を有効なpopulation SEやN選定根拠として扱わない。
- auxiliary GBM差引controlは既知期待値identityとしてvalidだが、有限momentsのGBMを差し引いて旧Heston heavy tailを解消したことにはならない。
- 正式Heston generatorはfinite exponential-momentを持つCIR schemeへrevisionする。候補はdrift-implicit sqrt-Lamperti、QE-M、exact-CIR等。名称だけで認証せず、採用stock結合と選んだstepの必要moment条件を検証する。
- 新候補Lampertiは y=sqrt(v)、a=(4κ barv−ξ²)/8、b=κ/2、c=ξ/2、u=y+c sqrt(dt) Zv とし、y_next=[u+sqrt(u²+4(1+b dt)a dt)]/[2(1+b dt)]。a>0等の数学的入力条件と安定した負u評価、old-v stock coupling、p=2/4等の必要finite momentを正式reviewで確認してからpilotする。
- このメモでは新schemeの実probe、formal pilot、mainをまだ行っていない。旧SE表を新schemeへ外挿しない。

## 2. 状態・contract・threshold の定義

月次fixingは12個。時点tの直前に終わったfixingをA=sum、n=countへ反映してから新保有量を決める。残りm=12−n、未来fixing間隔をτj=tj−t、支払はT=1。

- Heston forecast stateは現在v。κ/長期mean variance `barv`/ξ/ρは固定。
- local forecast stateはℓ>0。時点t以降の係数を `ℓ a_base(u,s)` とし、forecast中ℓを固定。再hedgeで観測call Qへ再fitする。
- ℓは新たな確率的vol factorではない。G=localの実市場生成はbase field、ℓ=1。
- θは一般state名であり、Hestonの長期mean variance θと混同しない。
- effective strike k*=12K−A。x=k*/S。nは各ヘッジ日で確定し、別の連続grid軸にしなくてよい。
- A>=12Kでは、未来spotsが正である限り payoff は常に線形。これはexact route:
  V=D/12 [A−12K + S Σj exp((r−q)τj)]、
  VS=D/12 Σj exp((r−q)τj)、Vθ=0。
  このbranchのためにMCや不安定なcall-vega割算を走らせる必要はない。
- t=T/残りfixing0は決済event。48個のtrade時点と混ぜない。

### Heston homogeneity

future normalized sum B=Σj S_tj/S、D=exp(−r(T−t))、
f(t,v,x)=E[(B−x)+] とすると、

V=D S f/12、
VS|v=D (f−x fx)/12、
Vv=D S fv/12。

Gammaを診断する場合だけ VSS=D x² fxx/(12S)。fxxを粗いhistogramで作らない。v-gridは0を含めるか、positive lower boundかを先に定める。logv axisはv=0では定義できず、boundをactiveにしたfitを成功へ変えない。

### localでは同じ式を流用できない

normalized sumのlaw自体が現在Sに依存する。y=logS、u=logℓ として f=f(t,y,u,x) と定義すれば、

V=D S f/12、
**VS|ℓ=D (f+fy−x fx)/12**、
Vℓ=D S fu/(12ℓ)。

optional Gammaは
VSS=D [fy+fyy−2x fxy+x² fxx]/(12S)。

fyを落とすと、価格に合ってもspot Greekが誤る。scratch one-step local例では omitted Delta=.000479553、naive .042842061に対し正しいchain Delta=.043321615。3幅spot FDが一致した。

thresholdをt依存の標準化距離へ変換する場合も、そのscaleがS/v/ℓ依存なら追加chain termが生じる。最小版は**各tで固定したthreshold axis**を使うか、全chainを明示する。last-date付近のB分布幅は狭いので0..広範囲の一様65点だけでは不十分。中心近傍にnonuniform nodes、exact linear sheet、尾部支持境界を設ける。

## 3. 最後Gaussianのconditionは有限step価格のsmoothing

最後のstock step直前までを保存し、normalized B=b+c exp(μ+σZ) とする。ここでbはそれまでの残りfixing sum、cは最後stock step左端のnormalized spot、μ=(r−q−a/2)dt、σ=sqrt(a dt)。

k=x−b>0、σ>0なら F=c exp(μ+σ²/2)、d2=(log(c/k)+μ)/σ、d1=d2+σ。

f=F Φ(d1)−k Φ(d2)、
fx=−Φ(d2)、
fxx=φ(d2)/(k σ)。

x<=bは f=b+F−x、fx=−1、fxx=0。σ=0はatomであり、threshold一致では普通のDelta/Gammaが存在しない。価格を返せてもGreek-readyとしない。小Nでpayoff/Greekの全標本0、SE0になったtailもprecision証明ではなくunderresolvedとして元Nを残す。

Hestonで最後variance更新が同じZに依存しても、Asian満期payoffがterminal varianceを使わないため、stock最後Zを積分できる。最後stock incrementが既知leftvarianceと新Gaussianで定義されるschemeにもこの条件は成立する。ただし旧CIR2moment-LN schemeは§1.1の理由で正式不採用。

localでは最後のa=ℓ a_base(u_last,S_left)がpathごとに既知なので同じlognormal積分が可能。ただしS_left、b,c,a全てが**initial Sとℓに依存**する。last coefficientだけ固定したhomogeneous DeltaをlocalのVSとは呼ばない。

これは finite-step Euler/CM2価格をsmoothingするもの。continuous-time Heston/localの離散化biasを消すものではない。substepを粗くしてconditioning区間だけを長くすれば、局所係数freeze biasも変わる。

## 4. Auxiliary GBM geometric control（valid candidate）

独立のHeston geometric expectationやlocal geometric expectationは不要。モデルと同じstock Brownian W1を使い、**別の定数σcのauxiliary GBM**を走らせる。

未来fixing geometric meanを Gaux=(Πj Saux_tj)^(1/m) とし、
Haux=((A+m Gaux)/12−K)+。
k_aux=(12K−A)/m>0なら Haux=(m/12)(Gaux−k_aux)+。

auxiliary logGはnormal:
meanlogG=logS+(r−q−σc²/2) mean_j τj、
Wgeo=σc² Σij min(τi,τj)/m²、
Fgeo=S exp((r−q−σc²/2) meanτ+Wgeo/2)。

discounted auxiliary meanは D E[Haux]=D(m/12) Black(Fgeo,k_aux,Wgeo)。k_aux<=0はexact linear expression。m=1は通常のBlack controlになる。

β=1で
Y=D CE_last(Hmodel−Haux)+D E[Haux]
を使う。Hmodel/Hauxは未discountの満期payoff、Dは現在tからTまでのdiscount。モデルとcontrolを**同じ最後Z**についてconditionするのでE[Y]=finite-scheme model price。β=1固定なら同じ標本でbetaを学習するbiasもない。

σc²をstate依存にすること自体はvalid:
- Heston候補: barv+(v−barv)(1−exp(−κτ))/(κτ)。
- local候補: ℓ a_base(first future midpoint,S)。

**S/θ bumpごとにσc、auxiliary paths、解析mean全部を再計算する。** delta/vegaだけ別labelsを足す構成にしない。σcのfloor/clamp/knotを導入する場合はderivativeのbranchも記録する。現在fieldのlinear z interpolationは係数knotを持つため、近傍S-bumpとtime-refinementの一致を確認する。price interpolantがC1でも、粗いEuler teacherの係数kinkを消した証明とは呼ばない。

CV有限標本の価格曲線は「positive conditional payoffの平均」の形ではなく差+knownmeanになる。有限Nでprice bounds/convexityが崩れる可能性をrawのまま検査し、clipでrepairしたGreekを主baselineへ渡さない。

### 小probe：最後conditioningだけでは不足

GBM月次Asian、t0/SK100/σ.2、N4096、最後dt=1/768:
- raw price SE=.126554、conditioned price SE=.126576（ほぼ減らない）。
- conditioned Delta SE=.008435。
- 3幅CRN Vv SE≈1.618。
- 既知GBM geometric control β1でprice SE=.004780、Vv SE≈.124。

これはGBM limitのscratchで、Heston/local固有のgeometric式が既に実装されているという結果ではない。

### 旧auxiliary control試作の履歴（Heston population-SE根拠には使用不可）

scratch N16384、192steps、Nprefix1024/4096/16384。Hestonは旧CM2-lognormal v/logstock、localは別のCEV proxy a(S)=.04(S/100)^−.6、ℓを固定。A0/m12だけ。公式Heston-marginal local field、main labels、独立oracleではない。**以下のHeston「SE」は有限sampleのsd/sqrt(N)という記述量だけであり、母分散無限のためprecision/CLT/採否の根拠として無効。**

| Model | N | conditional price SE | aux-CV price SE | conditional Vθ SE | aux-CV Vθ SE | conditional VS SE | aux-CV VS SE |
|---|---:|---:|---:|---:|---:|---:|---:|
| Heston |4096|.110329|.043829|1.096299|.570294|.008227|.004044|
| Heston |16384|.055309|.021209|.543206|.282930|.004127|.001958|
| CEV-local proxy |4096|.128233|.004321|.064164|.004808|.008163|.001565|
| CEV-local proxy |16384|.063455|.002120|.031616|.002354|.004087|.000783|

Vθは同じpriceの3幅CRN FDで、analytic Asian Greekではない。VSはphysical S±.1のCRN。controlと期待値は全bumpで再計算した。旧Heston sampleではresidual第二factorノイズも見えるが、tailが未観測でsample-SEはそもそも有効なprecision根拠ではない。local proxyにもactual Heston-marginal local fieldへの外挿はできない。正式schemeの必要momentsを確認後、actual fieldとselected statesでGreek/position/P&L予算を実測し、必要なvariance reduction・state領域をpilotで選ぶ。

auxiliary pathは既存W1だけで生成でき、新しいnormalが不要。scratch full conditional/control価格生成（N16384×192）の単回時間はHeston .0780s、local proxy .0539s。これは簡単なproxyの記述値であり、actual grid/保存/validationを含むbenchmark・runtime保証ではない。

## 5. 長期call PDE / inversion の支持

### Calendar time / t0

既存 LocalVarianceGrid:
- t=0はS==S0のみ `initial_state`、S99.9/100.1も `unsupported_initial_state`。
- t>max(times)はunsupported。現F04 maxT1なのでT*=1.25延長・CF grid/cutoff/wing/PDE検証が新規に必要。
- 0<t<tminは明示early-time proxy。wingはedge extension。これらはsilently全域支持へ格上げしない。

local mainを a_base(t_i+dt/2,S_i) のtime-midpoint/spot-left logEulerにすれば、未来spotを使わずt0 offspot coefficientを定義できる。正式草案担当が採用検討中。t0 cacheは初期S0とnearby spot bumpsのspecial sheet、t>=1/48はfullS grid。

dt halfとS-bumpでclosure biasを確認する。旧tmin1/4096に対し1536-step midpoint1/3072は上回るが、更に3072以上へrefineするとearly proxyに入る。time refinementの度にtmin/supportを再確認する。

local long-callは各ℓについてbackward PDEを一回 [0,1.25] で解き、全ヘッジ時点snapshotを共有できる:
Ct+(r−q)S CS + .5ℓ a_base(t,S)S² CSS−rC=0。

過去にもℓを適用したPDEfamilyを一回解くことは、未来からのbackward solveのt snapshotを使う限り「現時点以降ℓ forecast」と整合する。市場生成Gをℓへ変更する意味ではない。残存期間を0から同じbase surfaceへ貼り直す方法は誤り。

### Reversibility is conditional, not automatic

fit C_M(t,S,θ)=Qは各queryで次を保存:
bracket Q-range、price residual、rootθ、Cθ、境界、支持/monotonicity、near-zero derivative、解なし/非一意。

local continuumでは、regular positive field/linear carry/convex European payoffの条件下で
Cℓ = E_t integral exp(−r(u−t)) [.5 a_base(u,S_u) S_u² CSS(u,S_u;ℓ)] du
となりnonnegative。ただしfinite-domain PDEやinterpolantの単調性は別に検査する。strictness、finite bracket内Q、十分なCℓを保証しない。

Heston v>=0のfamily minimum callはv=0でもfuture mean-reversion varianceを持つ。local GのQがこのminimumより低い場合、Heston fitは解なしになり得る。vを負に延ばす/nearest clipして合わせない。Heston C_vのpositivity/uniquenessも選んだ領域でCF/bump・field derivativeから確認し、global theoremとして置かない。

deep ITM/OTMではCθが小さく、price1e-3合格だけではrisk ratioが支持されない。denominator誤差δCθを含め、
δhC approximately [δVθ−hC δCθ]/Cθ、
δhS approximately δVS−CS δhC−hC δCS
の単位付き予算を使う。|Cθ|<=uncertaintyならunknown。単位の違うv/ℓのraw J thresholdを同じ数値にしない。

3ℓnodesではSciPy RegularGridInterpolator(method='cubic')は構築不能（probeでValueError、各軸4点以上）。正式草案は4+coarse/7fineへ修正検討中。logℓ interpolationを使えば Cℓ=Cu/ℓ、Vℓ=Vu/ℓ。ratioはVu/Cuで不変。Heston v/logvも有効領域内で同じ原則。

### IFT market quote vs raw model parameter

Qはactual traded-call currency price:
VQ=Vθ/Cθ、
VS|Q=VS|θ−(Vθ/Cθ) CS|θ。

両モデルが同じobserved Qへfitしてからこの式を使う。raw Vv/Vℓを共通quote hedgeと呼ばない。fit後の再較正Q±hおよびS±h,Q固定bumpと比較する。localℓはfixed forecast axisで、二つ目のBrownianリスクを追加したものではない。local Gのstock/callは同じ一factorである。

## 6. Workload / primitive storage / saved-checker boundary

元48dates提案 i=0..47、768steps/年なら残りsteps=768−16i、合計18,816。以下は全部full gridのworst countで、t0 special sheetやexact-linear branch削減を入れていない。現在の12日主候補では残りsteps合計4,992、24日では9,600（各hedge日のt0 sheetを含む）。48日表のpath-step量との比は12日で約0.2653、24日で約0.5102、terminal統計row/threshold量はdate数に比例する。全cacheを高密度化する前に12/24/48日でposition/P&L refinementをpilotする。

| Candidate | Heston path-steps | local path-steps | Heston threshold tail evals | local threshold tail evals |
|---|---:|---:|---:|---:|
| N1024,v7,S9,ℓ3,x65（旧low）|134,873,088|520,224,768|22,364,160|86,261,760|
| N4096,v13,S17,ℓ7,x129 |1,001,914,368|9,171,369,984|329,711,616|3,018,129,408|
| N16384,v13,S17,ℓ7,x129 |4,007,657,472|36,685,479,936|1,318,846,464|12,072,517,632|

local actual fieldのqueryperpathを入れない「Npathsだけ」の見積りは過小。existing evaluator + unsorted spots + status unique counting + logupdate のconstant positive proxyは1024/4096batchで約165/166ns/path-step。original-high local更新だけなら外挿約25.4分、N16k whole high gridなら約101.5分。tail integrations、RNG、Greek bumps、call PDE、spline、oracle、serialization/CAS、checksを含まない。簡単なproxy/単一環境からの外挿であり正式所要時間ではない。

### Storage choices

全(t,S,ℓ,v) nodeが独立driverを丸保存するとfloat64 Heston2factor+local1factor:
- 旧low:6.32GB。
- original-high:89.40GB。
- high N16384:357.61GB。

threshold/Aノードは**同じfuture trajectoriesを共用**する。thresholdごとに再simulation/RNGを行わない。

許される縮約は2種類（混同しない）:

1. **明示CRN reuse + full SDE replay可能なdriver保存**
   - 各tごとにnodes/modelでcommon normalsならhighで約1.85GB（model2factor+1factor）。
   - 各restartで同じ768-step global standardized driverの該当future sliceを共有する明示couplingなら、N4096×768×2×8=50.33MB（N16kは201.33MB）。
   - これはnode間・date間・model間の意図的な相関。独立Nをnode数倍に数えない。perstate IIDはsample indexごとに保たれる。
   - oracle/train/testは別stream。同じnormalsを使う価格/Greek/refinement比較ではjoint moments/paired covarianceを保存する。
   - 全node前段SDEを再計算できるが、checker費用はgenerationと同程度のbillions work。二CAScopyの再検査で再び支払うことを明示する。

2. **Last conditional sufficient statisticsを保存するboundary**
   - 全rowの (b,c,μ,σ)、原N、state/source/seed/step/domain/statusを保存すれば、全threshold価格、同じprice surface、VS/Vθ、callfit/IFT/holding/P&Lをsaved-only再計算できる。
   - high N4096の4float係数はHeston+local計約830MB、N16kは約3.32GB。thresholdごとの全sample値は保存不要。
   - earlier SDEからb,cを全byte/全step再生した証明ではない。selected-state independent future paths/refinement、primitive seed provenance、known limitsを別検証する。
   - last-left stateも保存し、μ/σが正しいcalendar coefficient・local S dependence・CIRleftvariance由来かを全rowで再確認できる。
   - default checkerのboundaryとfull/selected fresh SDE replay範囲を明記する。SHAだけを金融正しさの根拠にしない。

最小v1にはshared fine drivers+last-statistics保存を勧める。default checkerは全cache-to-price/Greeks/IFT/P&L、selected driver-to-last-stateを別gate。full driver-to-all-cache replayは計時した追加reproducibility receiptにするか、必要ならgateとして費用を予算化する。どちらを採るかformal specで先に固定する。

## 7. Queryperpath cost と主評価の共有

元48日提案 per G/level:32768×3×48=4,718,592 state queries。G2×level3=28,311,552 state points、M2のfit/risk評価は最大56,623,104 model-state queries。12日主候補では同じpath roster/3substep levelsなら各1/4、24日では1/2。ここで3levelsはSDE step refinementであり、12/24/48 hedging datesのrefinementとは別。正式mainはpilotでどのlevelを主比較に使うかを固定する。

- state-fit/conditional face/riskをpolicyごとに再計算しない。同じpath/date/M/A,QでGreek/band/U1/U2が共有できる。
- no hedge/NNに必要な市場price・claim memoryはG由来の同じcache。NNはactual latent vを入力にしない。
- Heston traded callをperpath 1024-frequency CFで評価すると数十billion frequency queriesになる。date×v×logspotでprecomputeし、同じprice面のCS,Cvをqueryする。
- local market callはℓ1 PDE snapshot、local prediction familyはℓaxis PDE snapshotsを共有。
- scalar rootsはvectorized bracket/Newton-bisectionにし、iterations/call-price evaluation countと費用を保存。支持外/非一意/nearzeroを数値0に置換しない。
- face derivative + inversionを含むmain費用、既知Q/θからholdingだけのonline費用、teacher/PDE込みcold研究費用を分ける。call pricing/setupを除いたNN inferenceとのspeedupを混ぜない。

## 8. 推奨する最小でも完全なv1 とpilot順序

### Scopeを保つ

- 主候補12hedges、24/48hedgesを精緻化比較に残す。月次12fixings、AsianT1、fixedcallK100T*1.25、G2×M2、U1/U2は保持。
- 旧CM2-LN Hestonは不採用。finite-moment CIR scheme + 適切なstock couplingを正式review/pilotで固定してから主Gとする。local候補はtime-midpoint/spot-left。continuous modelとのCF/PDE/martingale/step誤差は別gate。
- private price cache + 同一C1価格面からVS/Vθ。optional Gammaは初回採否の必須条件にしない。
- auxiliary GBM β1をbaseline候補とし、raw/conditioned/conditioned-CVをpilotに残す。newQMC、最適beta学習、完全3D Asian PDEは追加しない。
- Heston7/13、localS9/17、ℓ4+/7、threshold65/129、Nprefix1024/4096/16384。全high N16kを最初から走らせず、selected-state gateを先に測る。

### Progressive pre-main gates

1. Heston scheme finite-moment gateを最初に置く。旧LN候補は拒否。採用CIR/stock schemeのpositivity、stock martingale、p=2/4等の必要moment・離散step条件を確認。数学toy:1remaining fixing Black、A>=12K linear、Heston deterministic-variance limit、local nonlinear coefficient spot-bump、zero-lastvariance atom、t0support、full coefficient/calendar correctness。
2. Longcall surface先行:37 initial/holdout plus dynamic selected S/v/ℓ states。T*1.25、calendar PDE snapshots、CF/PDE/time/domain/θ-bump、monotonicity/brackets/low-Jを確認。
3. Teacher selected states:早期/中期/最終fixing前、ATM/ITM/OTM、low/base/high v/ℓ、S-tail/t0近傍。同じoriginal Nprefixでraw/cond/CV、3θ幅/3S幅、192/384/768（必要selected1536）。独立seed＋別SDE implementation、local selected PDEやm1 Blackなど異なるcontrol。
4. Face→holding gate:teacher price errorだけで合格にしない。VS,Vθ、call CS,Cθ、hC/hS誤差と再較正bump一致、domain/threshold/θ grid refinement、cost/risk errorを測る。6SEだけでdeterministic interpolation/SDE biasを包まない。
5. Full conditional cacheは成立した各model N/degree/domainで構築。pilotが不成立ならvariance-reduction/支持範囲/conditional evaluatorのrevisionへ戻る。mainを見てN/h/支持を緩めない。
6. No-training tiny complete dynamic comparison:月次memory/全assetcash/terminalfees、common quote fit、martingale/empty claim、12日完全action/P&L＋24/48日精緻化、全failure保存、saved-only checker。単なるinstant shockでは代替しない。
7. NN/policy pilot→independent review/freeze→full main。all original pathsとunknownを残す。

境界でfitが失敗する場合の実行方策を先に固定する。nearest state clippingや失敗path削除は不可。「unknown時はno-trade/明示fallback」方策を採るならraw quote-risk unsupportedと実行fallbackを別保存し、それを完全IFT hedgeと呼ばない。fallbackなしでNaN holdingsを残すなら全N指標はunknownになることを受け入れる。

## 9. 実読した根拠と実施範囲

実読source:
- canonical `research/RB-F04/dynamic_hedging/RESEARCH.md` §§5/7/8/10/12。
- `_model_dynamics.py`全体:old fulltrunc、monthly-only recorder、local left-endpoint query、caller normals/原failure保持。
- `_heston_local_surface.py`全体の関連箇所:price/strike derivatives、LocalVarianceGrid t0/tmax/earlytime/wing/support。
- `RB-F04/reference_methods.py`:calendar-time CN/Rannacher、finite domain、独立HestonCF。
- F04 frozen protocol:existing surface tmin1/4096、129times/161z、maxT1。

独立scratch:
- /tmp/rbf04_dynamic_probe.py、
  /tmp/rbf04-dynamic-feasibility-probe.json。
- /tmp/rbf04_auxiliary_gbm_probe.py、
  /tmp/rbf04-auxiliary-gbm-control-probe.json。

数式はこのメモの導出。CM2-LN infinite-second-momentは独立reviewの重大指摘を反映し、上記2-step条件付きmeanから理由を確認した。CVはknown conditional expectation identity、GBM geometric lognormal lawから構成した。Heston/local自身のgeometric価格・Heston local full teacher precision・global inversion/coverage・主P&Lを証明していない。

未実施:official dynamic source、T1.25 Heston local grid/PDE生成、fullconditional cache、独立actual local oracle、formal pilot/freeze/main/training、全suite、Git。
