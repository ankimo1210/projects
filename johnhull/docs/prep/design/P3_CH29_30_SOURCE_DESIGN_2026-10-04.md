# P3 後続 Ch29–30：原典全要求・印刷値・既存API・独立教師の準備

- 日付: 2026-10-04。
- **読み取り専用の準備。実装・受入・main統合・pushの報告ではない。**
- 対象root: `/home/kazumasa/worktrees/m29/johnhull`。
- 原典: Hull 11e Global Edition、`options, futures and other derivatives 11th.pdf`。
- 実際のinventory: `docs/section_inventory.json`。台帳: `docs/section_ledger.json`。
- 参照: `docs/prep/sections/ch29.md`、`ch30.md`、
  `docs/P3_REQUIREMENT_AUDIT_2026-10-04.md` §§29.1–30.appendix。
- 原典本文: `/tmp/ch29-source.txt`、`/tmp/ch30-source.txt`、`/tmp/ch30-appendix.txt`。
- 原典画像: `/tmp/p3-ch29-30-p688.png` から p703、p707からp714、p718。
  **25頁すべて画像で式・符号・脚注・印刷値を確認済み。**
- 生成: `/tmp/p3-ch29-30-fixtures.py` → `/tmp/p3-ch29-30-fixtures.json`。
  math/numpy/scipyのみ、**hullkitをimportしない**独立教師。
- repository/Git/製品pytest/browser/D1/releaseは操作していない。
- 本資料の8受入単位はinventoryで全てunreviewed。draft要求40件。
  **P3全37節の完了対象を保持する。準備完了でaccepted件数は増やさない。**

## 1. 実際の節・頁・依存

| ID | 原典の節名 | 原典範囲 | draft要求数 | 主な前提・後続境界 |
|---|---|---|---:|---|
| 29.1 | Bond Options | 688–692 | 7 | 28.6 Black/4.10 bond規約。組込権利の実数値評価は32.5へ |
| 29.2 | Interest Rate Caps and Floors | 693–699 | 13 | 28.4/28.6、29.1。日付・曲線・測度は33.2/34でも使用 |
| 29.3 | European Swap Options | 699–702 | 7 | 28.4/28.6、29.2、HW既存部品。32.2の解析教師にも接続 |
| 29.4 | Hedging Interest Rate Derivatives | 703 | 3 | 29.2/29.3。同じportfolioの全感応度。32.7へ接続 |
| 30.1 | Convexity Adjustments | 707–710 | 3 | 28.8/29.1。CMS近似の範囲を明示 |
| 30.2 | Timing Adjustments | 710–711 | 2 | 28.8、単一観測/単一支払。34.3/34.5へ接続 |
| 30.3 | Quantos | 711–714 | 3 | 28.8/30.2。FX quote方向。34.3へ接続 |
| 30.appendix | Proof of the Convexity Adjustment Formula | 718 | 2 | 30.1と同じ教師、独立の台帳行として証明を受入 |
| 合計 | 8受入単位 | 25原典頁 | **40** | 本文・脚注・例・模式図・付録を保持 |

Ch29冒頭の4難点も教材に置く: 個々の金利の振舞い、曲線全体、異なるvol、
同じ金利がpayoffとdiscountの両方に現れること。
Ch30冒頭の「forward期待値→risk-free割引」という2段階手順が、
非標準給付では観測/支払/通貨/非線形変換に応じた補正を要する理由を導入にする。

## 2. 全要求と最小契約

### 2.1 §29.1 — Bond Options

| 要求 | 原典にある内容 | 実装・教材契約 / 教師 |
|---|---|---|
| D29.1-01 | callable/puttable/deposit/prepayment/loan commitment、yield方向、p689 | callable=straight−issuer call、puttable=straight+holder put。holder/issuerの向きを対応表へ。数値のcall scheduleは契約例であり価格pinではない |
| D29.1-02 | Black call/put、式29.1/29.2、p689 | FB/Kは現金単位、P0Tは無リスクdiscount、σBはrelative forward-price vol。parity、positive-small-σ極限。math payoff積分 |
| D29.1-03 | FB=(B0−I)/P0T、式29.3、p690 | B0/FB dirty、Iはoption期間内couponPV。quoted strikeなら満期accruedを加算。現時点のaccruedで代用しない |
| D29.1-04 | Ex29.1、p690 | I/FB/P/Kcash、9.49/7.97。途中印刷値の丸めを連鎖計算に入れずfull precisionを保持 |
| D29.1-05 | Figure29.1/29.2、p691 | std(log future bond price)は0→山→0、年率forward-price volはoption期間で低下。原典は模式図。モデルを明示して形を再現、原図の数値pinを捏造しない |
| D29.1-06 | σB=D y0 σy、式29.4、p692 | y0はforward yield、Dはそのyield頻度でのmodified duration。D=5,y0=.08,σy=.2ならσB=.08。連続複利Macaulayを半期yieldへそのまま掛けない |
| D29.1-07 | Ex29.2、p692 | **European put**。半年複利forward yieldとmodified Dを解く。spot122.82、quoted-K put2.36、cash-K put1.74。教師は独立coupon求根 |

原典の契約例(p689):

- callable10年、最初2年lockout、3–4年call110、5–6年107.5、7–8年106、9–10年103。
- puttable10年、5年末償還権。penaltyなし解約可能5年fixed depositはAmerican bond put。
- loan/mortgage prepaymentはissuer/borrowerのcall。
- 5年3%のloan commitmentを2か月有効にする例は、借手がfaceで5年3%coupon債を売るput。
  rate上昇時にexerciseする。これらに原典価格はない。

**Ex29.1 source input:** 9.75年bond/face1000/coupon10%semiannual、spot dirty960、
option10か月、zero3mo9%・9mo9.5%・10mo10%(cont)、σB9%、coupons50 at.25/.75。
current accrued25→clean935、expiry accrued100/12→cashK1008.3333333333334。

**Ex29.2 source input:** 10年face100/coupon8%semiannual、option2.25、strike115、
forward-yield-vol20%、discountzero5%cont。
独立の再現規約:

1. spot dirty = Σ4 exp(−.05 t)+100 exp(−.05·10) = 122.82450061368152。
2. optionまでの4couponPV = 15.036480963574235。
3. forward dirty120.6225824180047、expiry accrued2、quoted115→cash117。
4. 残余coupon時点(.25,.75,…,7.75)で
   `Σ CF_i(1+y/2)^(−2 t_i)=dirty_forward` を解く。
5. y=.05063024104885763、Macaulay5.994304807874645、modified5.846304894839231。
6. σB=.05919996521416531。
7. quoted117 put2.360719121398572、cash115 put1.741707042457788。

これは印刷値を再現する**明示した独立規約**。
DerivaGemの内部実装を同一と断言しない。既存rates.bond_yieldは連続複利で別契約。

Figureのsynthetic教師はVasicek ZCB M=10,a=.15,η=.02:
`B(t,M)=(1−exp(−a(M−t)))/a`、
`sd(log P(t,M))=B(t,M)η sqrt((1−exp(−2at))/(2a))`。
option annual relative vol=sd/sqrt(t)、t=0は限界で定義。
coupon債のstdをこのZCB式のまま正確と呼ばない。

### 2.2 §29.2 — Interest Rate Caps and Floors

| 要求 | 原典にある内容 | 実装・教材契約 / 教師 |
|---|---|---|
| D29.2-01 | payoff式29.5、25,000/12,500、p693、脚注1/2 | Lαmax(R−K,0)をpay日、Rはfix日決定。rate tenor/compoundingをaccrualに合わせる。daycountはαで別に持つ |
| D29.2-02 | ZCB put portfolio式29.6、p694 | fix時即時価値Lαmax(R−K,0)/(1+Rα)=max(L−L(1+Kα)/(1+Rα),0)。face L(1+Kα)、strike L、maturity pay。floorはcall |
| D29.2-03 | floors/floorlets/collars、p694 | long cap−short floor、異なるcap/floor strikes。zero-cost floor strikeは単調求根・bracketと不成立を区別 |
| D29.2-04 | cap−floor parity、Business Snapshot29.1、p695 | 同strike/scheduleでreceivefloat/payfixed swap。ただし初回resetで交換なし。既に固定済みの初回couponをfullswapに含めると差を明示調整 |
| D29.2-05 | Black caplet/floorlet式29.7/29.8、pp694–695 | LαP(0,pay) Black(F,K,σ,**fix**)。Blackの分散時刻をpayに変えない |
| D29.2-06 | Ex29.3、pp695–696 | 原典元本**10M**、P/d1/d2/0.00519million全pin。既存1M testの519.0046だけでは原典単位の表示を満たさない |
| D29.2-07 | flat/spot volatility、p696、脚注3 | 同一strike/cap prefixからspotを逐次strip、flat全quoteを再構築。increment<0/intrinsic未満/upper bound未満の解不可をforce-fitしない |
| D29.2-08 | smile/skew、SABR、p696 | flat/spotの用語とstrike方向のsmileを区別。SABR数値は受入済27.2を参照 |
| D29.2-09 | pay-bond measure Epay[Rfix]=F、式29.9、pp696–697 | 独立Gaussian rateモデルでRN密度の平均1、pay-measure平均F、Q path-discount価格を照合。projectionとdiscount曲線の契約を別入力化 |
| D29.2-10 | backwards dates、p697 | 末尾からtenorで遡り、初回はregularの0.5–1.5倍。1.22→2.80の6期間を厳密に再現。浮動小数点boundary誤差はDecimal/Fractionで回避 |
| D29.2-11 | ACT360、p697 | 5/1→8/1=92days、α92/360=.2556。1+αF=Pproj_fix/Pproj_pay。ACT365へF/Kを同時変換してcashを保存 |
| D29.2-12 | negative rates/shifted lognormal/Bachelier、pp697–698 | F+a,K+a>0、shift maturity依存。σB relativeとσN absoluteを区別。shift→0、両model parity、ATM同価格normal vol |
| D29.2-13 | backward RFR/midpoint/期中既知分、pp698–699 | OIS forward、Black variance fix→.5(fix+pay)は**quick approximation**。期中既知factorをFに含め、残り観測平均。日次compounding/残存重みの共分散に対する誤差を示す |

**Ex29.3 input:** L10M、F7%/K8%(quarter comp)、α.25、fix1/pay1.25、σ20%、OISzero6.5%cont。
P=.9219631718378983、d1=−.5676569631226124、d2=−.7676569631226124、
caplet5190.0459174404905 USD=.005190045917440491 million。

**原典backwards schedule:**
`[1.22,1.55] [1.55,1.80] [1.80,2.05] [2.05,2.30] [2.30,2.55] [2.55,2.80]`。
first.33 =1.32 regular periods。単純に1.30を残すとfirst.08<.125となり規約違反。

**曲線とZCB同一性の境界:** 原典後半はprojection forwardがOIS discountと別でもよい。
式29.6は支払までのdiscountを1/(1+Rα)で表す同一rate/bond identity。
LIBOR/projection spreadを持つRへそのままOIS ZCB putと名付けない。
Black formulaのcurve入力分離と、single-curve ZCB-payoff identityを分けて教材化する。

**日数と単位:** annual rateはfraction、relative volは1/sqrt(year)、normal rate volは
annual-rate fraction/sqrt(year)。33% relative at F3%はσN約1%であり、33% normalではない。
ACT365変換はF365=F360·365/360、Kも同率に変え、αF/αKとPVを保持。
「basisだけ変えて同じ数値rateを入れて同価格」とはしない。

ATM normal volを**Black価格へ**合わせる式:
`σN=F sqrt(2π)/sqrt(T) [2N(.5σB sqrt(T))−1]`。
F=.03、σB=.33、T=.5/1/5で約.00988/.00986/.00968。
原典の「約1%」は精密な印刷価格pinでなくvol単位の例。

**独立pay measure教師:** Ho-Lee Q r_t=r0+ηW_t、
`P(t,U)=exp(−r_t(U−t)+η²(U−t)^3/6)`、
`E[D0T|rT]=exp(−r0T−.5T(rT−r0)+η²T³/24)`。
U-measure rT meanはr0−η²(T²/2+T(U−T))。
R=(1/P(T,U)−1)/(U−T)のE_Uが(P0T/P0U−1)/(U−T)に一致する。
このモデルのcap価格はshifted-lognormal rateに基づき、standard Black R-modelの価格との
完全一致を要求する教師ではない。

**独立RFR教師（OISと銀行勘定を一致）:**
65日、α=.25/65、obs=.5+iα、Q日次連続short rate=r0+ηWobs。
quoted overnight simple rate=expm1(r_iα)/α、daily factor=exp(r_iα)、
realized R=(prod factors−1)/.25。
pre-accrualのBrownian integralは正確、期間内の積分は左観測点の日次銀行勘定として定義。
Qの同じ銀行勘定からP0T/P0UとU-measure Gaussian tiltを独立導出する。
未知観測の共分散=min(t_i,t_j)、tilt loadingは割引積分との共分散。
期中26/65既知分では既知productと現在の状態を条件として保持する。
FをMC平均から作らず、条件付きGaussian product mean/OIS比の両経路で求める。

- fix前: exact compounded price749.1719766、pay-measure daily MC746.4271936±3.0305306(SE)、
  Black midpoint767.5535903。近似誤差+18.3816136。
- 26/65既知: exact131.4971432、MC131.3478244±.5318712、
  naive remaining-mean-time Black268.6246780。近似誤差+137.1275348。
- この教師のσB選択はη/Fというsynthetic local conversionで、empirical RFR quoteではない。
  原典のquick ruleが常に正確、期中は平均時刻だけで分散を決められる、とは主張しない。
- arithmetic-average Brownianの分散もfix+δ/3（finite observation補正あり）であり、
  midpointのfix+δ/2とは違う。期中は未知fractionと各観測の重みも分散に入る。
- 実装側が既知factorを落とす/未知factorの割合を落とす欠陥と、
  approximation自体の残差を別の証跡にする。

### 2.3 §29.3 — European Swap Options

| 要求 | 原典にある内容 | 実装・教材契約 / 教師 |
|---|---|---|
| D29.3-01 | 将来floating loanの保険/forward swapとの違い、p699 | 6か月後5年loanでpayer option3%の契約例。swaptionは権利、zero-initial-cost forward swapは義務 |
| D29.3-02 | fixed bond option identity、BS29.2、p700 | payer=par strike put、receiver=call。single-curve float leg開始par前提。full stochastic-rate MCとJamshidian・独立求積 |
| D29.3-03 | Black式29.10/29.11、pp700–701 | LA Black(sF,sK,σ,T)、A=ΣαP。期首で同じsTが全couponへ適用される契約、各支払独立fixing optionの和ではない。payer−receiver=LA(sF−sK) |
| D29.3-04 | Ex29.4、p701 | forward6.1%contは独立入力、discount6%contから導出しない。A印刷2.0035は切捨て。2.19millionとd1/d2 |
| D29.3-05 | annuity numeraire、pp701–702 | E_A[sT]=sF。A_tも確率変数。initial annuityを外へ置く理由は測度変換、全金利をconstantと仮定したためではない |
| D29.3-06 | ACT365、p702 | 3/1→9/1=184days、α184/365=.5041。irregular scheduleでA=Σα_iP_i |
| D29.3-07 | negative rate shifted/Bachelier、p702 | shifted domain、payer/receiver parity。shiftはoption tenorとswap lengthに依存。normal absolute volとrelative volを区別 |

**Ex29.4 input:** option5y、swap5→8、semiannualpay5.5,…,8、N100M、K6.2%、σ20%、
discountzero6%cont、**forward input6.1%cont**。
sF=2expm1(.061/2)=.06193978009756169、A=2.0035576486220465、
d1=.22143387464262848、d2=−.2257797208573295、payer=2.190823164891525million。
Aを4decimal通常四捨五入すると2.0036。
原典2.0035を合致させるため内部Aを改変しない。印刷照合規則をtruncationとして保存した。

**annuity教師:** 前節Ho-Lee同じモデルでA_T=ΣαP(T,T_i)、
sT=(1−P(T,last))/A_T、密度D0T A_T/A0。
E_Q[density]=1、E_Q[density*sT]=(P0T−P0last)/A0。
以下の独立positive-a HW教師も用意:

- a=.15、η=.012、初期flat4%cont、expiry1、pay1.5/2/2.5/3、fixed.045。
- Q zero-mean OU状態、discount積分とのjoint Gaussian、初期曲線fit用deterministic shiftを明示。
- pure math Jamshidian decomposition=.003758519551308271（単位元本）。
- 独立Q1D求積=.0037585195513083138、差4.29e−17。
- exact joint-Q MC=.0037778803800496154、SE1.47295e−5（1.3144SE）。
- 固定coupon正値の前提。negative fixed cashflowで同じJamshidian分解を許可しない。

multi-curveでfloating bondがOISの下でparになると仮定しない。
standard Blackは与えたprojection sF/discount annuityで使えるが、
fixed-bond-option payoff identityは別のsingle-curve契約として示す。

### 2.4 §29.4 — Hedging Interest Rate Derivatives

| 要求 | 原典にある内容 | 実装・教材契約 / 教師 |
|---|---|---|
| D29.4-01 | 4delta（parallelzero、quote rebuild、bucket、PCA）、p703 | **同じcap+swaption portfolio**で4定義。quote→curveを再較正して全instrument再価格。bucket shape/interpolation/unitsを固定。実務のquote deltaの理由を説明 |
| D29.4-02 | 10instrumentで55gamma、p703 | full symmetric Hessian、diagonal approximation、parallel1ᵀH1、PCA2factorの2×2H。parallel gammaはtrace(H)ではない |
| D29.4-03 | Blackvol平行bumpとvolPCA、p703 | one-vol-factor仮定、2–3volfactor。ratePCAとvolPCAは別data/basis。全volを同幅動かすvegaとPCA方向vegaを比較 |

新private契約の最小形:

- `quote_curve(quotes, instrument_spec)` → curve。quoteの意味/単位/再較正残差を返す。
- `portfolio_price(curve, vol_vector, contracts)`。
- `sensitivity_summary(base_quotes, builder, price, bump_spec, bucket_basis, factor_basis)`。
- quote/rate bumpsはannual fraction、1bp=1e−4。signed DV01の定義はPV(+1bp)−PV。
  central差分も使うなら別label（本教師は両方を保存）。gammaはcash/rate²、perbp²は×1e−8。
- relative Black vol1point=.01、normal vol1pointとは別。
- PCA loadingは正規化・符号規約・training windowを明示。
  合成covarianceを歴史的market PCAと名付けない。
- **個別有限bump差の合計と同時bump差は厳密一致しない。**
  片側差ではcross-gamma由来O(h²)、central差ではO(h³)。一次のbucket合計→parallelをbump縮小で確認。

独立synthetic教師は10deposit simple-rate quotes q_i→P_i=1/(1+q_iT_i)、
zero z_i=log1p(q_iT_i)/T_i、linear zero interpolation。
これはbootstrapを数学で独立に完結できる特定instrument set。
既存rates.bootstrap_zero_curveのsemiannual bond契約と同一だとはしない。
実装はこのprivate deposit-builderか、別途独立bond-bootstrap教師を選ぶ。

- portfolio元本1M、7caplets+1European payer swaption、PV17589.8041082276。
- signedone-sided parallelzeroDV01=+242.4901916262。
- 全quote+1bp→rebuild difference=+189.8831510267。zero+bumpとquote+bumpは違う。
- 個別one-sided bucket合計とparallel差: zero+29.0664267、quote+22.6855523。
- centralquote bucket和−同時bump: h1bp−.0180790、.5bp−.00226097、.25bp−.000282655。
  half-bumpで約1/8となり、central差の3次残差を示す。
- zeroHessianからparallelγ2.06326565e8、trace6.02471528e9。
  quoteHessianからparallelγ1.21059968e8、trace4.66222366e9。
- Hessian step.1bpでdirect parallel γとのrelative差はzero1.025e−4、quote1.064e−4。
- 55unique entries、rate PCA3directionsのdeltaとfirst2factor fullγ、volPCA2directionsのvega。
- RB-F07解析Jacobianを本節の必須追加要件にしない。bump/再較正教師で受入可能。

### 2.5 §30.1 — Convexity Adjustments

| 要求 | 原典にある内容 | 実装・教材契約 / 教師 |
|---|---|---|
| D30.1-01 | Figure30.1/式30.1、pp708–709 | E_T[B]=BF=G(yF)、G nonlinear、E_T[y]>yF。3equallylikely/equallyspaced bond prices→unequallyspaced yields。G′<0/G″>0を示す |
| D30.1-02 | Ex30.1、pp709–710 | yF6%、annual3y6%coupon bond、σy22%、T3、discount5%annual。G′/G″/Ey/PV5.27/5.18。discountをcontinuousに変えない |
| D30.1-03 | CMSのpar-bond yield近似、p709 | CMS swap rate≈同期間bond yield、couponはtoday's forward swap rate。stochastic curve下でexact identityではない。flat/nonflat statesと近似残差 |

式30.1:
`E_T[y_T]≈yF−.5 yF² σy² T (G″/G′)`。
既存convexity_adjustmentへは**−G″/G′というpositive量**を渡す。
argument名g2_over_g1は紛らわしいが挙動は正しく、別承認なしでpublic APIを変えない。
古いtestの「G″/G′>0」コメントは将来当該節実装時に説明修正する。

Ex30.1はface1:
`G(y)=.06/(1+y)+.06/(1+y)^2+1.06/(1+y)^3`。
G′=−2.6730119494616353、G″=9.891031991585809、
Ey=.060967118804628434（6.097%印刷）、
PV100Ey/(1.05)^3=5.266568949757342→5.27、unadjusted5.183025591188856→5.18。

**独立逆変換教師:** T-measureでbond priceを正のlognormalとしmeanBF=G(yF)を固定。
local-matched price vol `σB=−G′/BF·yFσy` を明示し、各normal積分点でG(y)=BTをbrentqで解く。
Tmeasureで正確なyield期待/分散/二乗偏差を求め、原典の2次近似と比較する。
このsynthetic価格模型は、yield自体が正確なlognormalという主張ではない。

- σparameter .22→.11→.055→.0275、T3で期待yield近似誤差
  5.53418e−7→3.45722e−8→2.16050e−9→1.35027e−10。
- σ半分で約1/16（4次残差）。T3→.75→.1875→.046875でも同じ縮小。
- CMS par-bond近似はflat curveで一致するが、annual zero(.03,.06,.09)で
  bondyield−swaprate+9.4155bp、(.09,.06,.03)で+9.6686bp。
  これは特定synthetic stateの差で、原典の普遍的誤差boundではない。

### 2.6 §30.2 — Timing Adjustments

| 要求 | 原典にある内容 | 実装・教材契約 / 教師 |
|---|---|---|
| D30.2-01 | 式30.2/30.3、pp710–711、脚注1 | observationT/payTstar、W=P(t,Tstar)/P(t,T)。samecurrency tradable ratio。signed loadingとcorrelationを二重反転しない。lag0/ρ0で1 |
| D30.2-02 | Ex30.2、p711 | T5/pay6/forward1200、σV.2/σR.18/ρ−.4、RF.08annual。1.00535/1206.42/.6302/760.25。freezing近似と区別 |

W=(1+RF/m)^(−m lag)、signed proportional loading
`σW=−σR RF lag/(1+RF/m)`。
従ってfrozen coefficient補正:
`E_Tstar[V]=E_T[V] exp(−ρ_VR σV σR RF lag T/(1+RF/m))`。

**脚注の2通り:**

1. signednegativeσW、ρVW=ρVR。
2. positive|σW|、ρVW=−ρVR。

両方を同時に反転すると同じ式にならず誤り。本文の相関記法だけを機械的に写さない。
rateはRFのcompounding frequency mを指定、1+RF/m>0。
relative rate-volという模型入力がnegative RFに自然に定義されるとは仮定しない。
汎用covarianceの計算契約と、このpositive-rate freezing例の模型前提を区別する。

Ex30.2 signedloading−.013333333333333332、factor1.0053475808732542、
mean1206.417097047905、P06=(1.08)^−6=.6301696268831045、PV760.2474119120764。

教師はjointGaussianのVとnumeraire ratio、density=exp(σW√T Z−σW²T/2)。
weight平均1、Eold[density V]とchanged-measure期待値を求積/MCで照合する。
これは**constant covariance/freezing模型では正確**。
任意stochastic RF/bond ratioについて式30.3をexactとする教師ではない。
実モデルでは時変covarianceを積分するか残差を評価し、source近似の説明を残す。

### 2.7 §30.3 — Quantos

| 要求 | 原典にある内容 | 実装・教材契約 / 教師 |
|---|---|---|
| D30.3-01 | FX方向と式30.4–30.6、pp711–712 | Vの単位Y、payoff通貨X、S=**Y units per 1 X**。同一通貨へ変換したnumeraire ratio W=(PX/PY)S=forward FX。EXV=EYV exp(covT)、1+covTは一次近似 |
| D30.3-02 | Ex30.3日経、pp712–713 | yen-forward15150.75→USD quanto forward15260.23。JPY/USD forwardFXのvol/correlationを固定。positive .0072補正 |
| D30.3-03 | 式30.7/Ex30.4/Siegel、pp713–714 | American/複数給付はmoneyaccount比gX S/gY、**spotFX** covariance。q_eff=.029、CRR100179.83。inverseFXのItôとmeasure変更。独立AmericanPDE/European積分/格子収束 |

同一満期bond numeraireはsingle settlement、moneyaccount numeraireは複数給付・American。
forwardFXとspotFX vol/correlationはstochastic金利下で一般に同一ではない。
通貨変換は同じcurrency単位でratioを作ってからdriftを取る。
Sを逆数にするならnoise loading/correlationも反転。
単にJPY/USDとUSD/JPYのlabelを交換して同じρを使わない。

**Ex30.3:** Nikkei15000JPY、T1、USD5%/JPY2%/dividend1%、
indexσ20%、**forwardJPY/USD**σ12%、ρ.3。
yenforward15000 exp(.02−.01)=15150.75250626252、
covarianceadj .3·.2·.12=.0072、
quanto forward15260.231576009528。
原典はforwardと「approximately futures」の説明。一般stochastic-rateでfuturesとexact同値とはしない。

**Ex30.4:** indexS=K1200、T2、UK5%/US3%、indexσ25%、
**spotUSD/GBP**σ12%、ρ.2、dividend1.5%。
USDindexdrift.015→GBPdrift.021、q_eff=.05−.021=.029。
価格単位GBP。給付は固定換算index−Kであって、market FXをpayoffに掛ける通常外貨asset callではない。

- puremath CRR100=179.82607364328325→**179.83印刷**。
- CRR200/400/800/1600/3200=180.0246735/180.1240540/180.1737597/
  180.1986172/180.2110468。
- **印刷100stepは有限格子値。収束値という受入条件にしない。**
- independent monotoneAmerican obstacle PDE、Smax4800、space400→800、
  time25001→100001で180.2095596481→180.2199977420。
- sameM800/time156251=180.2199038389（time差−9.39e−5）。
- sameΔS6/sameΔt/Smax6000/M1000で同価格（domain差0）。
- empirical CRR1/N extrapolation180.2234763721、PDE1/M² extrapolation180.2234771066。
  extrapolationの良い一致だけで誤差0/無条件PASSにしない。格子・time・domainのbudgetも記録する。
- Europeanclosed179.9963708099と独立payoff積分を一致させる。**CRR100 American179.826は
  continuous European179.996より低い**ため、有限格子のAmericanとcontinuous Europeanを
  誤差budgetなしで比較するgateを置かない。同一NのAmerican≥European、または
  grid収束を確認したAmerican≥continuous Europeanを検証する。sameN100 EuropeanもJSONに保存。

**Siegel’s paradox:** Ymeasureで
`dS/S=(rY−rX)dt+σS dW`、同じYmeasureのinverseは
`d(1/S)/(1/S)=(rX−rY+σS²)dt−σS dW`。
Xmeasureへ換えるとcovariance−σS²がdriftへ加わり、inverse drift=rX−rY。
単なる逆数Itôと測度変更の2段階を両方示す。
同一測度で`E[1/S]=1/E[S]`を課さない。

### 2.8 §30.appendix — proof

| 要求 | 原典にある内容 | 実装・教材契約 / 教師 |
|---|---|---|
| D30.appendix-01 | Taylor/期待値/forward価格、p718 | BT=G(yF)+G′Δy+.5G″Δy²+高次、E_TBT=G(yF)。一次と二次の期待項を独立計算、sum残差を記録 |
| D30.appendix-02 | 二乗偏差の近似/高次省略、p718 | E(Δy²)=Var(y)+(Ey−yF)²。原典のyF²σy²Tはvariance/bias/highmomentの小量近似。smallσ/smallTで残差縮小 |

証明節をD3候補としても、計算要求すべてをN/Aにしない。
§30.1逆yield教師からEbond−BF、Ey、variance、bias²、二乗偏差、一次/二次項を共有する。
ledger row/requirement IDs/出典/証跡は30.1と付録でそれぞれ持つ。

## 3. 全印刷出力pinと規則

fixtures JSONの`printed_pins`は36件。**36/36原典表示規則に一致**。
下表はgroup化した一覧。契約inputやsource模式図をsyntheticの印刷price pinに格上げしない。

| 原典 | 印刷値（出力） | 規則・注意 |
|---|---|---|
| Ex29.1 p690 | I95.45、FB939.68、P.9200、cash quoted-K1008.33、call9.49/7.97 | 通常の表示桁rounding。内部はfull precision |
| Ex29.2 p692 | spot122.82、put2.36/1.74 | source quoted/cash strikeを別case。半期yield/modifiedD |
| cap/floor p693 | 25000/12500 USD | 元本10M、rate/δ規約 |
| Ex29.3 pp695–696 | P.9220、d1−.5677、d2−.7677、cap.00519 millionUSD | **notional10M**。5190.0459USDとmillion表示を区別 |
| daycount p697 | 92/360=.2556 | 92daysはexact、αは4decimal表示 |
| Ex29.4 p701 | sF.06194、A2.0035、d1.2214、d2−.2258、payer2.19 million | **Aのみtruncation**。計算精度を2.0035へ丸めない |
| daycount p702 | 184/365=.5041 | 184days exact、α4decimal |
| Ex30.1 pp709–710 | G′−2.6730、G″9.8910、Ey.06097（6.097%）、PV5.27/unadjusted5.18 | annual-compounded discount5%、face1 derivatives/payoff100 |
| Ex30.2 p711 | factor1.00535、mean1206.42、P.6302、PV760.25 | RF8%annual、T5/pay6、signedratio−.0133333 |
| Ex30.3 p713 | yenforward15150.75、quanto15260.23 | yenからUSD fixed-rate quanto契約、sourceFX方向 |
| Ex30.4 p714 | driftadj.006、q_eff.029、American179.83 GBP | **100step有限格子**。sourceT2、spotFX covariance |

追加でsource契約inputをそのまま保持するもの:
currentaccrued25/clean935、duration換算5·.08·.2=.08、callable110/107.5/106/103、
backwards6period endpoint列、33%relative→約1%normal。
これらはpricing-output精密pinと同じ区分にしない。
式29.1–29.11/30.1–30.7は全て要求表に対応。
Figure29.1/29.2/30.1に原典の数値axis/dataはない。

## 4. 既存hullkit対応と新private部品

| 既存 | 再利用できる範囲 | 足りない/混同しない契約 |
|---|---|---|
| `hullkit/ir_options.py:32` bond_option_black | Black European bond call/put | cash/quoted/accrual/forwardcoupon helper、semiannualyield、modifiedD |
| `ir_options.py:42,53` caplet_black/cap_black | 正F/Kのcap/floor、spot vol列 | strip再利用部品、collar bracket、初回reset、backwardsdates、typed unit/curve分離 |
| `ir_options.py:66` swaption_black | European payer/receiver、given A/sF | future-start schedule、α/curve forward helper、annuitymeasure教師 |
| `ir_options.py:76,86` convexity_adjustment/bond_yield_convexity | 結果式とannual/regularfreq bond G′/G″ | sign説明、inverseyield教師/CMS近似、timing/quantoは別式 |
| `rates.py` bond_price/yield/macaulay_duration | continuous-compounded bond | Ex29.2半期yieldでは契約が違う。private helperを追加 |
| `rates.py` discount_factor/forward_discount/zero_interp | OIS discount/forwardDF/zero interpolation | projectionとdiscountの別curve入力。quote-builder instrument規約 |
| `rates.py:134` bootstrap_zero_curve | 半年払いbond quote→curve | synthetic deposit-builderとは別。curve再較正の教師を合わせる |
| `swaps.py:26` swap_rate | t0-starting regular future payments | **start0固定**。Ex29.4のstart5 annuity/sF helperにそのまま使わない |
| `rfr.py` RFRConvention/calendar/accrual/compounding | 日数・lookback/lockout/observation shift、既知factor | stochastic-rate model/generation/numeraireの教師ではない |
| `rfr_options.py` bachelier_price/delta | negative rates、absolute normal vol | annuity AをDF引数へ入れるならA>1も可という計算意味を説明。Lは外で掛ける |
| `rfr_options.py:128` compounded_rate_option_mc | **given daily paths**のcompounded payoff、fixedDF | pathsを独立modelから作る必要。modelなしでstochastic discount pricing検証済みとはしない |
| `rfr_options.py` gaussian_quadrature_price | 製品側normal payoff求積 | independent教師として同関数を呼ばない |
| `sabr_normal.py` private shifted Black | F+a/K+aのBlackunit | SABR model/shiftedSABR entryとgeneric fixedvol shiftedBlackを混同しない |
| `hull_white.py` hw_zcb_option/hw_jamshidian_swaption | fixedpositivecoupon European教師/モデル | source Black模型のpriceそのものではない。a>0 public契約をHo-Lee a0へ黙って変更しない |
| `_numeraire_choices.py` rate_statistics/annuity_values/statistics | M29のpay-bond/annuity curve・measure部品 | 教師は独立math。source要求IDを29.2/29.3へ別に持つ |
| `trees.py:59` crr_price | Ex30.4AmericanfiniteN、q_eff入力 | 独立AmericanPDE・欧州積分・N収束を別経路にする |
| vol11/既存Hull pin tests | 一部例・inline教材/strip | 本文全要求の受入を代用しない。今回36出力pinと全40要求を追跡 |

提案する最小private実装（名前は設計案、repo未変更）:

1. `_ir_standard_models.py`: cash/quotedbond、半期yield/modifiedD、backwards schedule、
   daycount、flat→spot strip、generic shiftedBlack、future-start annuity。
   数値計算だけ共用し、29.1/29.2/29.3教材/台帳は個別。
2. `_ir_hedging_lesson.py` またはprivate sensitivity helper:
   instrument-spec quote rebuild、sameportfolio、bucket/PCA、rate/quoteHessian、vegaPCA。
3. `_ir_adjustments.py`: signedcovarianceによるtiming/quanto expectations、
   source-specific quote方向、inverseFX drifts、yield/CMS近似の記録。
4. 教師builderはscratchのmath構成をrepoの独立scriptへ移し、runtime helperをimportしない。

新public APIやdependency追加はこの準備の既定にしない。
既存public挙動を黙って変えず、private finite-input wrapperを最小追加する。
Black public関数は現在σ>0/T>0を要求するため、σ=0極限はpositive-small-σで検証するか
private deterministic helperに持たせる。source極限説明のためpublic contract変更は不要。

共通validation契約案:
finite scalar/vector、times ordered、pay>fix、positive accrual/discount/notional、
curve numeraire identity、black F/K>0、shift F+a/K+a>0、normalσ>=0、
相関[−1,1]/covPSD、compounding base>0、yield root domain1+y/m>0。
negative curve/rateを一律拒否しない。Blackとnormal/shiftedの模型domainを区別。
scenarioが表現不能ならerror、clipして成功としない。

## 5. 独立教師の結果と受入gateへの引渡し

| 検証 | このscratchの実測 | 正式実装でのgate案 |
|---|---:|---|
| 原典出力pin | 36/36表示一致 | source-specific decimals/annuitytruncation/N100を固定 |
| Black bond payoff積分 | closed差最大1.0658e−13 USD | abs1e−9/rel1e−11、near-tail absolute合致だけでMC合格としない |
| Ho-Lee Epay[R] / Eannuity[s] | 誤差0、密度平均1 | mean abs1e−10、density1e−10、Q/pay/annuity両価格経路 |
| caplet Q/pay measure price | 差1.5179e−17(単位元本) | abs1e−10/relative1e−9、モデルcontractを固定 |
| payer=fixedbondput | 差4.3368e−18 | 全payoff stateと両price経路 |
| positive-a HW Jamshidian/Q求積 | 差4.2934e−17 | actual public positive-a部品と独立oracle照合 |
| flat→spot strip | maxσ差5.8287e−16/rebuild1.81899e−12 USD | exactsynthetic rebuild+inadmissiblequote rejection |
| ACT360→365 cash/PV保存 | −5.68434e−14 USD | F/K同時変換とschedule差を区別 |
| timing RN求積 | closed差2.2737e−13(asset units) | signedcoords反転/ρ0/lag0/ρ反転、sourcepins |
| quanto RN求積 | closed差0 | forwardFX/spotFX/逆数Itô/Siegel、FXdirection fixture |
| 全Gaussian MC | nondegenerate最大1.3198SE | fixedseed5SE、unnormalized RNweights、mean/massもSE保存 |
| RFROIS forward mean identity | fix前0、期中−8.8818e−16 | known product/state retained、MCforwardをteacher入力に使わない |
| RFRdailycompounded price | exactquad差最大5.8208e−11 USD、MC最大.9057SE | modelquad/MCを合格gate、midpoint誤差を0にするgateを置かない |
| fullgamma vs parallel | .1bp Hessianrelative差最大1.064e−4 | stepsweep、crossγ、quote/zero双方、rate/volunits |
| yield2次近似 | σhalfで誤差約1/16 | smallσ/smallTの残差縮小・variance/bias²分離 |
| AmericanCRR100 | 179.8260736433→179.83 | sourcefinitegrid pinと収束gateを分離 |
| American独立PDE | 400→800差.0104381 GBP、time差.0000939、domain差0 | grid/time/domain budgetを明示、samegrid/収束後Europeanlowerbound、price差の許容幅 |

このscratchはfixture準備。正式releaseの全suite/D1/ブラウザ/証跡整合の代わりではない。
MCはsampling SE、PDEはdiscretization/domain error、source数値は印刷rounding、
原典quick式はmodel/approximation residual。それぞれ異なる誤差として保存する。
MC zero-hit/SE0をprice0/決定論一致と誤認しない（M31教師の扱いを引き継ぐ）。

## 6. 後続への最短実装順と残作業

1. 28.6/28.7/28.8の全要求を保持して受入。
2. 29.1: cash/quoted/半期yield、全pin、図/組込契約対応表。
3. 29.2: caplet/strip/schedule/basis/negative rate、pay measureとRFR残差。
4. 29.3: future-start annuity、全pin、bondidentity/annuitymeasure/HW教師。
5. 29.4: 同portfolio全4delta/55gamma/PCAvega。説明だけのD3に縮めない。
6. 30.1＋30.appendix: inverseyield教師/build共有、ledger/requirements/evidenceは別。
7. 30.2: timing signedcovariance、sourcepins、freezing範囲。
8. 30.3: sourceFXdirectionとsourceN100、independentPDE/欧州教師/Siegel。

残るのはrepository private実装、教材セルとinteractive controls、原典/契約/数値/図の
正式証跡、台帳requirement投入、必要gate、独立レビューと受入、承認済mainpush。
本準備でaccepted件数を増やさず、P3全37節から8単位や付録を落とさない。
原典にないhistorical/market numerical inputsは必要に応じ明示syntheticとする。
原典の印刷例の欠損をsyntheticで代替acceptedにしない。