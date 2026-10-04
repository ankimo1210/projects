# P3 §31.5 二因子Hull–White詳細設計 — 2026-10-04

## 結論・境界

**§31.5のequilibrium theta=0モデルとTN14のcurve-fitモデルは同じGaussian核で整合する。** TN14 Appendixのeta・全gamma・option varianceは独立積分と一致した。curve-fitのp4微分は満期方向を明記する必要がある。

この資料は親へ渡すprivate実装候補と独立教師の設計。repo/Git/公開API/production dependenciesは変更していない。製品pytest、D1、五軸受入は未実施。ここにある価格はすべて**明示synthetic fixture**（原典p1のhumpパラメータだけは原数値）で、印刷価格の代替と扱わない。

成果:

- `/tmp/p3-two-factor-fixtures.py` — hullkit不使用、math/numpy/SciPyのGaussian核教師。
- `/tmp/p3-two-factor-fixtures.json` — 全入力・全結果・境界fixture・scratch assertions。
- `/tmp/p3-two-factor-independent-notes.md` — 別エージェントによる代数的独立照合。

原資料:

- §31.5 / Eq31.14: `/home/kazumasa/worktrees/m29/johnhull/options, futures and other derivatives 11th.pdf` 印刷=物理p728。
- TN14全4頁: `/tmp/p3-input-recovery/TechnicalNote14.pdf`、SHA256 `9068c1d786837a5946fc7a3cd2114cafc4edb0293975f70508b4cadedc31af5f`。
- [Rotman FinHub原資料](https://github.com/rotmanfinhub/john-hull-textbook-resources)、固定full commit `9b8dbfe37661dbd3de65d3a1489dc1297e840de7`、git blob `dccb5d395680ee0bf1fea9bef8ab0c2ed56a83af`。取得詳細 `/tmp/p3-input-recovery/download-records.json`。

## 1. モデルと単位

Q測度、定数a,b,sigma1,sigma2,rho:

\[
dr_t=[\theta(t)+u_t-a r_t]dt+\sigma_1dW_{1t},\quad
 du_t=-bu_tdt+\sigma_2dW_{2t},\quad d\langle W_1,W_2\rangle=\rho dt.
\]

- t/T/hは年、r/f0はannual-rate decimal。
- a,bはyear−1、u/thetaはannual-rate decimal/year。
- sigma1はannual-rate decimal/sqrt(year)、sigma2はannual-rate decimal/(year sqrt(year))。
- Bはyear、Cはyear²、B*r/C*uは無次元。Pは1 currency支払のPV。
- このuはG2++の加法short-rate factorとは異なる。sigma1/sigma2を同じunitで表示しない。
- §31.5は**theta=0**。TN14 p1は**u0=0、初期curveにfitするtheta**。原文の違いをUI/教師/受入ノートで明示する。

## 2. Independent Gaussian核

h=T−t、

\[
B_a(h)=\int_0^he^{-as}ds,\quad D_{ab}(h)=\int_0^h e^{-a(h-s)-bs}ds,
\quad C_{ab}(h)=\int_0^h e^{-bs}B_a(h-s)ds.
\]

a≠bでD=(e^−bh−e^−ah)/(a−b)、C=(B_b−B_a)/(a−b)。Cは原典Eq31.14/TN14 p1と一致。B'=e^−ah、C'=D=B−bC。

将来状態とintegralのnoise kernel（順序r_T,u_T,I_tT）:

\[
g_1(z)=(e^{-az},0,B_a(z))^\top,\qquad
 g_2(z)=(D_{ab}(z),e^{-bz},C_{ab}(z))^\top.
\]

\[
\Sigma(h)=\int_0^h[\sigma_1^2g_1g_1^\top+\sigma_2^2g_2g_2^\top
+\rho\sigma_1\sigma_2(g_1g_2^\top+g_2g_1^\top)]dz.
\]

特にintegral variance V(h)=Σ_II:

\[
V(h)=\int_0^h\{\sigma_1^2B^2+\sigma_2^2C^2+2\rho\sigma_1\sigma_2BC\}dz.
\]

被積分関数は `(sigma1*B+rho*sigma2*C)^2+(1-rho^2)*sigma2^2*C^2`。rho endpointsでも非負。Σと瞬間Brownian相関を同一視しない。

## 3. 厳密conditional bondとequilibrium

\[
E_t[I_{tT}]=B(h)r_t+C(h)u_t+\int_t^TB_a(T-s)\theta(s)ds.
\]

\[
\boxed{P(t,T)=\exp[-B(h)r_t-C(h)u_t-\int_t^TB_a(T-s)\theta(s)ds+V(h)/2]}.
\]

§31.5 theta=0なら **lnA_eq=V(h)/2**。a,b定数なのでA/B/Cはhだけの関数。市場curveのP0比を任意に入れない。

equilibrium state mean:
`m_r=e^-ah*r_t+D(h)*u_t`、`m_u=e^-bh*u_t`、`m_I=B*r_t+C*u_t`。

PDEチェック: B'=1−aB、C'=B−bC、lnA_h'=V'(h)/2。`∂t P + (u−a*r)∂rP −b*u∂uP +.5σ1²∂rrP +.5σ2²∂uuP +ρσ1σ2∂ruP =rP` を満たす。

## 4. curve-fit shift、theta、u0

初期curveP0(T)>0、P0(0)=1。f0(T)=−d lnP0(T)/dT。

\[
\psi(t)=V'(t)/2,
\quad\varphi(t)=f_0(t)+\psi(t),
\quad r_t=\varphi(t)+x_t.
\]

TN14のphi(0,t)はpsi(t)に対応し、total deterministic shift varphiと名前を分ける。u0=0ではx0=0、r0=f0(0)、dx=(u−a*x)dt+sigma1dW1、

\[
\boxed{\theta(t)=\varphi'(t)+a\varphi(t)}.
\]

\[
\boxed{\ln P(t,T)=\ln[P_0(T)/P_0(t)]-B(h)[r_t-\varphi(t)]-C(h)u_t
+\tfrac12[V(h)-V(T)+V(t)]}.
\]

条件付き時点t>0では観測u_tは非ゼロ/負値を許す。**u0=0という初期前提をu_t=0へ拡張しない。**

u0≠0はTN14原設定外の明示拡張。v_t=u_t−u0*e^−btとcenterし、theta=varphi'+a*varphi−u0*e^−bt、上式−C*u_tを−C*(u_t−u0*e^−bt)へ変える。初期r0=f0(0)は保持。theta/Aの両方を変えずu0だけ足すと `P(0,T)=P0(T)*exp(-C(T)*u0)` になりfitが壊れる。private初回実装はTN14u0=0を既定にし、一般u0拡張は名前/契約を明示するか教師だけに留める。

**equilibriumとの整合:** equilibriumから生成した初期curve `lnP0(T)=−B(T)*r0−C(T)*u0+V(T)/2` を使うと、f0(t)=e^−at*r0+D(t)*u0−psi(t)。上のcorrected thetaは厳密に0となり、両bond式が一致する。fixture32ケースは差0。

curveの正則性: bond式はquery時点f0を必要とし、theta構築はf0'を必要とする。C²なlnP0で教師を示す。piecewise curveのknotでsmooth thetaを暗黙に仮定しない。既存公開curve APIへ微分機能を追加せず、private analytic lesson curve・明示one-sided convention等を別途設計する。tree curve calibrationはdiscount factors/shiftで行えるため、thetaの数値微分を無理に入れる必要はない。

## 5. TN14 Appendix 全照合

h=T−t。

\[
\eta_K=\tfrac12[V(T)-V(t)-V(h)]-B(h)\psi(t),
\quad\ln A=\ln[P_0(T)/P_0(t)]+B(h)f_0(t)-\eta_K.
\]

| 印刷gamma | 独立kernel積分 |
|---|---|
| gamma1 | ∫h^T e^−az D(z) dz |
| gamma2 | ∫h^T B(z) C(z) dz |
| gamma3 | ∫0^t e^−az D(z) dz |
| gamma4 | ∫0^t B(z) C(z) dz |
| gamma5 | ∫h^T C(z)² dz |
| gamma6 | ∫0^t C(z)² dz |

これらはTN14 p3の各閉形式と一致し、etaの全3項・符号を独立に復元する。21ケースのraw gamma最大差8.9658e−12は閉形式の差し引きによるcancellation。volatility係数込みeta最大差1.4567e−15。印刷gamma差だけをモデル欠陥としない一方、near a=bで印刷閉形式をproduction計算に使わない。

p4のthetaの印刷 `F_t(0,t)+aF(0,t)+phi_t(0,t)+a phi(0,t)` は、p3の引数定義（観測時刻t/満期T）と合わせるとfirst-argument partialとしては不整合。

採用する明示式:

\[
\theta(t)=\left.\partial_TF(0,T)\right|_{T=t}+aF(0,t)
+\left.\partial_T\phi(0,T)\right|_{T=t}+a\phi(0,t).
\]

または `d[F(0,t)+phi(0,t)]/dt+a[...]`。phi(s,T)=psi(T−s)なのでfirst partialは−psi'、maturity partialは+psi'。独立導出で必要な方向は確定するが、**著者の公式訂正と称さない**。synthetic flat4%/5y例でliteral first partialのP=.8233120472573889、正しいcurveP=.8187307530779818、差.004581294179407114。

## 6. Zero-coupon bond option: 厳密

option expiry tau、bond maturity S>=tau、現在時刻0、L principal、K strike（同じcurrency）。TN14 p3/p4のlog forward-bond variance:

\[
v=\int_0^\tau\{\sigma_1^2[B(S-s)-B(\tau-s)]^2+\sigma_2^2[C(S-s)-C(\tau-s)]^2
+2\rho\sigma_1\sigma_2[B(S-s)-B(\tau-s)][C(S-s)-C(\tau-s)]\}ds.
\]

同じvは `load=(B(S−tau),C(S−tau))`、`v=load^T Σ_state(tau) load` でも得る。

TN14 Appendix p4のfirst/second/cross componentをそのまま式へ転記し、独立kernel/state-loading双方と照合した。7ケース最大差1.3878e−16。a=bの極限もkernel=state loadingで一致。

F=L*P0(S)/P0(tau)、D=P0(tau)、sd=sqrt(v)、d1=[ln(F/K)+v/2]/sd、d2=d1−sd。call=D[F*N(d1)−K*N(d2)]、put parity。v=0はdiscounted intrinsic、tau=0もintrinsic。K=0はD*F、negative strikeを許すかはprivate契約で明示（初回候補はK>=0）。原p1のhはこのd1に対応。

T-forward状態meanはQ mean−Cov(state,I_0tau)、covarianceは不変。正規1D積分教師とcall閉形式の最大差7.1054e−15、parity residualをJSONに保存。

## 7. Coupon bond option: 近似と厳密教師を分ける

TN14 p1–2: 二因子でcoupon bond optionを一般にJamshidianのZCB optionへ分解できない。**最初の2momentsを計算してlognormalと仮定する価格は近似**。

正cashflows c_i、T_i>tau、coupon bond Y_tau=Σc_i P(tau,T_i)。T-forward F_i=P0(T_i)/P0(tau)、v_ij=load_i^T Σ_state load_j。

\[
m_1=\sum_i c_iF_i,\qquad m_2=\sum_{ij}c_ic_jF_iF_j e^{v_{ij}},
\quad v_{match}=\ln(m_2/m_1^2).
\]

m1/vmatchをBlack形へ入れるmoment matching。sum of correlated lognormalsを正確なlognormalと称さない。

厳密教師はjoint Gaussianの2D期待値。uで条件付けするとr|uが1D Gaussian。正cashflowsによりY(r,u)はrで単調減少、uごとにexercise root r*(u)を求め、各exponentialのtruncated-normal expectationを閉形式計算し、最後にuを数値積分する。これはモデル上の厳密Gaussian expectationを精度指定で近似積分する教師で、coupon optionの一般closed-formとは呼ばない。

synthetic契約: flat4%、a=.1,b=1,sigma1=.03,sigma2=.08,rho=−.5、tau=2、T=[3,4,5,7]、c=[4,4,4,104]、K=100。

- exact conditional-Gaussian call **9.88683278714467**。
- moment match **9.912082063880094**、誤差 **+.02524927673542443**。
- m1=96.23130320913457、m2=10269.396593382933、vmatch=.1034141430491208。
- 個別strikeをcashflow比例配分してcallを足すと10.093689668335742。この任意配分はJamshidianではなく、一般portfolio positive-part inequalityにより上界になる例。
- C_i/B_i=[.37305,.58110,.70376,.83063]。exercise boundary slopeが異なるため、2D全状態で共通になるconstant strike allocationを作れない。rho±1でもfinite-step state rank2なら同じ論点。
- sigma2=0/u0=0や特殊rank1退化ではeffective single-factorになるため、適切な共通exercise rootの分解が可能な場合がある。degenerate例を一律に拒否しない。
- signed cashflows/nonmonotone portfoliosはこの条件付root教師の対象外。moment法を導入する場合もmean>0・variance finiteだけではcontract全般の正確性を保証しない。

## 8. 境界とnumerical stability

1. **a=b:** D=h*e^−ah、C=[1−(1+ah)e^−ah]/a²。h smallはseries、a=b=0の数学的limitはB=h,D=h,C=h²/2。初回private候補のa/b domainは>0とし、zero mean reversion limitは教師で別扱いできる。
2. near a=b: 原式1/(a−b)の差のcancellationを避ける。fixturea=.3,b=.3000001,h4ではprintedC3.748585483330178、kernel3.7485854846910227。native coupled-state kernel/矩陣方法で安定化。
3. **TN14 y=r+u/(b−a)**はa=bに使えない。σ3²=σ1²+σ2²/(b−a)²+2rhoσ1σ2/(b−a)、rho23=(rhoσ1+σ2/(b−a))/σ3。σ3=0の場合rho23は未定義、y deterministic。
4. **rho±1:** 瞬間diffusion rank1でもfinite-step (r,u) covarianceは通常rank2。controllability determinant=σ2[epsilonσ1(a−b)−σ2]。0なら退化。inverse/Cholesky positive-definiteを無条件に要求しない。
5. σ2=0/u0=0はone-factor zero-level Vasicek/HW limit。equilibriumbondが既知Vasicek b=0の独立式と一致。σ1=0/σ2>0はintegrated second-factor modelで、同じVasicekへ短絡しない。
6. 全vol0/h0/negative rates/negative u/negative thetaは許容。discount factor>1を不正扱いしない。
7. Σのunitsが混在するため、絶対eigenvalue thresholdだけでconditioningを判定しない。PSD理論、対角によるscale、roundoff toleranceを分ける。
8. finite real/bool/complex/datetime/timedelta/NaT/empty broadcast/negative time/overflow/price-underflowをprivate契約で検証。現在のscratch教師は固定finite fixtureだけで、input-validatorを実装済みと称さない。

## 9. Private実装候補（公開変更なし）

仮の置き場 `hullkit._two_factor_short_rate`。公開__init__/API manifest/既存HW関数signatureへ触れない。

| candidate | contract |
|---|---|
| `two_factor_kernels` | finite h>=0、a/b>0、B/D/C；a=bとnear-equal安定 |
| `two_factor_joint_moments` | physical/centered coordinateを明示、(r,u,I) mean/cov、theta=0またはconfigured curve-fit |
| `two_factor_equilibrium_discount_bond` | theta=0、観測r/u、lnA=.5V、任意市場curveを混ぜない |
| `two_factor_curve_discount_bond` | positive initial curve、r0=f0(0)、u0=0既定；観測u_t非zero許容 |
| `two_factor_zcb_option` | principal/strike/expiry/underlying maturity、exact lognormal under expiry measure |
| `two_factor_coupon_moment_approx` | positive future cashflows、m1/m2とapprox priceを返しmethod/approx表示を必須 |

production候補の計算は独立教師と共有しないmatrix exponential法が適する。M=[[-a,1],[0,-b]]、augmented A3=[[-a,1,0],[0,-b,0],[1,0,0]]、Q3にdiffusion2x2を埋める。Van Loan block `exp(h*[[A3,Q3],[0,-A3.T]])` からE/Fを取りΣ=F*E.T。a=b/rho±1/vol0を同じcoupled coordinateで扱える。source gamma閉形式は独立比較に留める。これは提案で、まだproduction moduleもmatrix実装も作っていない。

## 10. 今回実行と未実施

scratch教師:

- equilibrium32cases、curve-fit40cases、equilibrium→curve-fit reconciliation32cases。
- source全gamma/eta21cases、ZCBoption7cases、near/equal a=b4cases、transform8cases。
- ΣPSD/price finite/h0 assertions、sigma2=0独立Vasicek、equal-a-boption、expiry0。
- coupon正規outer bounds10/11/12の収束比較、exact forward moments。
- gamma別agent代数、sourceunits/state/rank/p4記号の照合。

| 新しい検証 | 最大absolute residual |
|---|---:|
| equilibriumを同じ初期curveでfitしたbond | 0 |
| direct theta積分 vs curve-fit Gaussian式 | 1.1102230246251565e−16 |
| discounted tower | 1.1102230246251565e−16 |
| TN14 raw six gamma vs kernel | 8.965828079965377e−12 |
| TN14 eta vs kernel | 1.4567340389515238e−15 |
| option variance (printed/kernel/state) | 1.3877787807814457e−16 |
| exact ZCBcall vs independent normal integration | 7.105427357601002e−15 |

未実施: production module、TDD製品tests、既存API影響、lesson/notebook、実browser/図、D1、正式要求台帳、二因子tree、market calibration、非linear f(r)、couponmoment誤差の一般bound。§31.5/TN14に必須の原導出の取得不足はない。実装と受入の工程は親が継続する。