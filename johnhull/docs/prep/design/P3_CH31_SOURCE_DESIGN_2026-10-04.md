> 未受入の準備資料。原典回収とscratchの結果であり、製品実装・全5軸の正式受入は別途必要。

# P3 Ch31 — 原典全体・単因子・推定・二因子の実装前準備

更新: 2026-10-04。読み取り専用の source/design 準備。Repo/Git/公開API/製品pytest/browser/D1 は操作していない。独立計算は `/tmp` で実施し、hullkit を import していない。**正式受入・製品実装の完了を意味しない。**

## 1. 結論と実際の台帳

- GE Ch31 本文は **pp.719–728、§31.1–31.5**。729–731 は要約・文献・章末問題。**Ch31 専用 Appendix はない**。台帳の実単位は5節で、読み取り時点はすべて `unreviewed`・`requirements=[]`。
- `docs/prep/sections/ch31.md` の **13 draft 要件 (2+4+2+3+2)** を保持した。草稿と正式登録済み要件を混同しない。TN14 の全 Appendix と TN15 の coupon option は補助資料で、別台帳単位に増やさない。
- 既回収の §31.4 原 worksheet、完全日次系列、独立 OLS/λ/Table31.1 と、§31.5/TN14 全数式の Gaussian kernel 設計を再利用。
- 単因子 Vasicek/CIR の bond/PDE/conditional moments、CIR χ²/zero boundary、P/Q変換、bond option 別積分、RB の経路割引、原系列の推定期間感度を独立計算した。
- 新規に著者公式 **GE Problem31_15.xls / Problem31_16.xls** を回収。31.16 の保存 curve-fit は **CIR の B 分母に本文と異なる EXP(γT−1)** を使う。元結果を再現し、本文の正しい CIR 計算と分離した。
- 実際の `hullkit.vasicek` / `hullkit.cir` 金利モジュールはこの checkout にない。信用損失の同名 Vasicek 関数、既存 HW、旧 notebook の例示を金利 Vasicek/CIR 専用受入と数えない。

源の不足と実装工程を区別する。31.4 の入力不足は既回収で解消したが、external series identifier/basis は未確定。新31.16の式不整合、TN14記号、TN15印刷末尾桁の差は明示して保持する。

## 2. 一次資料と固定版

原本: `/home/kazumasa/projects/johnhull/options, futures and other derivatives 11th.pdf`、880頁、印刷=物理頁。SHA256 **`8bc6e2f04fad95e4eeb40d0526219ba5f9228ee3d2ea3eaaf80870bdf7ccb482`**。

公式保存庫: [Rotman FinHub](https://github.com/rotmanfinhub/john-hull-textbook-resources)、固定 full commit **`9b8dbfe37661dbd3de65d3a1489dc1297e840de7`**。変動 main、Git tree SHA、blob SHA、SHA256 を区別する。

| 資料 / 範囲 | 保存パス | SHA256 |
|---|---|---|
| 原 VasicekCIR worksheet 全6 sheets、31.4日次データ・回帰・curve fit | `/tmp/p3-input-recovery/VasicekCIR.xls` | `f384c34b0bf745e2841eaae89d8fc06d84a41bf6cf754dd4a49a908f0d5229d5` |
| TN14 全4頁＋全 Appendix、二因子HW | `/tmp/p3-input-recovery/TechnicalNote14.pdf` | `9068c1d786837a5946fc7a3cd2114cafc4edb0293975f70508b4cadedc31af5f` |
| TN15 全2頁、単因子coupon option | `/tmp/p3-ch32/TechnicalNote15.pdf` | `83a848667055c71a8f060e1c46d559c422b1799e87cf3a3e3be20021d46cfa88` |
| GE Ch31 解答、全問題31.1–16 | `/tmp/p3-input-recovery/HullOFOD11eSolutionsCh31.pdf` | `b95c721a29f943062f8ff76bce15d76f029e06e543e11bcfbed5c7a93ab13dd1` |
| GE 問題31.15 元XLS（今回取得） | `/tmp/p3-ch31/HullOFOD11eProblem 31_15.xls` | `5b4049ac8152fa2704bb38e38fd9e0fa5e48eb9323b1c8b73d39fabb7a3e859d` |
| GE 問題31.16 元XLS（今回取得） | `/tmp/p3-ch31/HullOFOD11eProblem 31_16.xls` | `920a7244bd0617eebe82cede318f7351ddd50a7471fa84c808a491a75f178045` |
| Ch31 著者 slides 13枚（今回取得、全XML text抽出） | `/tmp/p3-ch31/Ch31HullOFOD11thEdition.pptx` | `78349cf2e52c6d362ade51a6aabe378b0e0e50b8d8e4bdfe9eb4e94ffb350227` |
| 11e errata 全2頁、固定snapshot | `/tmp/p3-input-recovery/Errata (11th  edition).pdf` | `197cce401783dc947737bfec778a33fe428a1b7690642c523f4dd7b46a46576d` |

新規3ファイルは固定raw byteから Git blob も照合し、XLSはOLE magic、PPTXはZIP magicを確認。元XLSを改変しない。RawURLとblob/bytes/content typeは `/tmp/p3-ch31/source-downloads.json` に保存。

- [VasicekCIR.xls](https://raw.githubusercontent.com/rotmanfinhub/john-hull-textbook-resources/9b8dbfe37661dbd3de65d3a1489dc1297e840de7/Options%2C%20Futures%2C%20and%20Other%20Derivatives%2C%2011th%20Edition/Vasicek%20and%20CIR%20worksheets/VasicekCIR.xls)
- [GE Problem31.15](https://raw.githubusercontent.com/rotmanfinhub/john-hull-textbook-resources/9b8dbfe37661dbd3de65d3a1489dc1297e840de7/Options%2C%20Futures%2C%20and%20Other%20Derivatives%2C%2011th%20Edition/Answers%20to%20End%20of%20Chapter%20Questions/Answers%20to%20End%20of%20Chapter%20Questions%20in%20Global%20Edition/HullOFOD11eProblem%2031_15.xls)
- [GE Problem31.16](https://raw.githubusercontent.com/rotmanfinhub/john-hull-textbook-resources/9b8dbfe37661dbd3de65d3a1489dc1297e840de7/Options%2C%20Futures%2C%20and%20Other%20Derivatives%2C%2011th%20Edition/Answers%20to%20End%20of%20Chapter%20Questions/Answers%20to%20End%20of%20Chapter%20Questions%20in%20Global%20Edition/HullOFOD11eProblem%2031_16.xls)
- [GE Ch31 solutions](https://raw.githubusercontent.com/rotmanfinhub/john-hull-textbook-resources/9b8dbfe37661dbd3de65d3a1489dc1297e840de7/Options%2C%20Futures%2C%20and%20Other%20Derivatives%2C%2011th%20Edition/Answers%20to%20End%20of%20Chapter%20Questions/Answers%20to%20End%20of%20Chapter%20Questions%20in%20Global%20Edition/HullOFOD11eSolutionsCh31.pdf)
- [Ch31 slides](https://raw.githubusercontent.com/rotmanfinhub/john-hull-textbook-resources/9b8dbfe37661dbd3de65d3a1489dc1297e840de7/Options%2C%20Futures%2C%20and%20Other%20Derivatives%2C%2011th%20Edition/Download%20PowerPoint%20Slides/Ch31HullOFOD11thEdition.pptx)
- [TN14](https://raw.githubusercontent.com/rotmanfinhub/john-hull-textbook-resources/9b8dbfe37661dbd3de65d3a1489dc1297e840de7/Options%2C%20Futures%2C%20and%20Other%20Derivatives%2C%2011th%20Edition/Technical%20Notes/TechnicalNote14.pdf)、[TN15](https://raw.githubusercontent.com/rotmanfinhub/john-hull-textbook-resources/9b8dbfe37661dbd3de65d3a1489dc1297e840de7/Options%2C%20Futures%2C%20and%20Other%20Derivatives%2C%2011th%20Edition/Technical%20Notes/TechnicalNote15.pdf)

固定errataにp727/Ch31/Problem31.16の訂正はない。現時点で新しい公式訂正が存在しないと保証するものではない。Source差を著者確認済みの訂正として表現しない。

既存記録: `docs/prep/sections/ch31.md`、`docs/prep/design/P3_PRIMARY_INPUT_RECOVERY_2026-10-04.md`、`P3_TWO_FACTOR_DESIGN_2026-10-04.md`、`P3_TREE_LMM_IMPLEMENTATION_2026-10-04.md`。今回scratch内の source_hashes に読み取り源と再利用artifactのhashを固定した。

## 3. 全 draft 要件の対応

| ID | GE 要点 | 今回の数値/設計 | 未受入・後続 |
|---|---|---|---|
| D31.1-01 | 720、31.1–4: Q経路割引とzero curve | OU積分分布、CIR/RB割引設計、σ0/定数r | private実装・図・独立validation/rendered |
| D31.1-02 | 720–721、31.5: PDE、flat stochastic curveの矛盾 | 全満期残差 polynomial、bond PDE有限差分 | Markov/no-income/terminal条件の導出 |
| D31.2-01 | 721–724: RB/Vas/CIR、A/B/mean reversion | Gaussian kernels、CIR Riccati ODE、RB exact endpoints | 三モデルを保持、RB近似を厳密と呼ばない |
| D31.2-02 | 724: Vas負rate/CIR Feller | χ² conditional moments、reachablezero、df0吸収branch、reflectedEuler bias | CIR path discountのscheme/収束、境界検査 |
| D31.2-03 | 725: Ex31.1、duration/bond diffusion31.9–12 | Ex31.1、coupon duration/convexity、signed bond vol | Yield durationとshort-rate durationを区別 |
| D31.2-04 | 726: equal local vol 比較 | .01/.sqrt(.04)=.05、practice31.9 | Vol units、同じ初期局所分散≠全分布一致 |
| D31.3-01 | 726: Vas bP/bQ、31.13 | 往復変換、bond excess drift | λの符号/単位、time-series Pとprice Qの境界 |
| D31.3-02 | 726–727: CIR aP/bP、λ=k√r | aP*bP=aQ*bQ、drift展開 | zero κでlevel割算しない、riskprice仮定 |
| D31.4-01 | 727: daily Euler OLS→年率 | canonical 8663pairs、df n−2/n、exactOU比較 | Proxy/basis/欠測、model誤差を維持 |
| D31.4-02 | 727–728: P→Qとλ当日fit | 既独立λ最適解、新31.15/16sourceと比較 | p727誤表記、CIRworksheet誤式を明示 |
| D31.4-03 | 728: Table31.1 residual、期間依存 | 全9点、等weight SSE、3推定window | Originalmarket lineage未同定、現在dataへ置換不可 |
| D31.5-01 | 728: twofactor SDE/B/C31.14 | 既coupledGaussian kernels/重根/ρlimits | Private実装・conditional state・equilibrium θ0 |
| D31.5-02 | 728: A省略→TN14 | 全Appendix η/γ1–6/φ/θ/option variance再利用 | f(r)非linear/treeは別scope、curve-fit記号を明示 |

実台帳5節の受入判定は行わない。Ch31には純D3候補の節全体はなく、31.1背景/31.5紹介など部分説明だけが候補。PDE・モデル価格・推定の数値要件は残す。

## 4. 背景31.1、評価と単位

\[
 V_t=E_t^Q[e^{-\int_t^T r_sds}H_T],\quad
 P(t,T)=E_t^Q[e^{-\int_t^T r_sds}],\quad
 R(t,T)=-\frac{\log P(t,T)}{T-t}.
\]

31.1/2のaverage r は瞬間rateの区間平均で、確率的に変動する。`exp(-E[∫r])` と `E[exp(-∫r)]` は別物。Gaussian積分ではconvexityのhalfvarianceを落とさない。

No-income Markov claimのPDEは `V_t+m(r,t)V_r+.5s(r,t)^2 V_rr=rV`、31.5はZCB terminal conditionP(T,T)=1。Coupon claimのcoupon日・ex/cum規約は別event。Equilibrium stationaryモデルのパラメータは時刻非依存なので、初期curveの完全fitを保証しない。

Flatcurve候補 P=exp(-r h)を代入すると、PDE residual/P=`−m*h+.5s²h²`。全hで0になるにはm=s0。初期flatcurveと、将来常にflatで確率変動する仮定を混同しない。

| 量 | 規約/単位 |
|---|---|
| t/T/h | 年、h=T−t>=0。Instantaneous rとcontinuous zero Rはannual-rate decimal |
| a | 年^-1、mean-reversion。bはannual-rate decimal |
| Vas σ | annual-rate decimal/√year |
| CIR σ | √(annual-rate decimal)/√year、diffusion=σ√r |
| RB μ/σ | 年^-1 / 年^-1/2。Diffusion=σr |
| λ_short | 年^-1/2、Pdrift−Qdrift=λ_short*absolute diffusion |
| CIR k | λ_short=k√r。λとkを同じ数値・単位で扱わない |
| B/short duration | 年。∂r priceの感度。Short convexityB²は年² |
| Return / price | Q expectedbondreturn=r、bondrelative diffusionはsigned負。元本1と100を区別 |

Figure31.1 (p722) は平均回帰の概念図、Figure31.2 (p724) はup/down/humpcurveの概念図で、入力数値はない。原図に存在しない値を印刷pinへ昇格しない。著者worksheetのstatic13tenor曲線は別の補助source入力として全A/B/Rを検算した。

## 5. Vasicek と conditional Gaussian 核

Q: `dr=a(b−r)dt+σdW`。B=(1−exp(−ah))/a、31.6–8 P=A exp(−Br)。a>0の本文式:

\[
 \log A=(B-h)\left(b-\frac{\sigma^2}{2a^2}\right)-\frac{\sigma^2B^2}{4a}.
\]

独立 kernel: m_r=b+(r−b)e^-ah、Var_r=σ²(1−e^-2ah)/(2a)、m_I=bh+(r−b)B、Var_I=σ²∫_0^h B(a,u)²du、Cov(r_h,I)=σ²∫e^-au B(a,u)du。Bond=exp(−m_I+Var_I/2)。これでconditional r/integralをjoint生成でき、rateとdiscountを独立sampleしない。

a0ではrはarithmeticBrownian、B=h、A=exp(σ²h³/6)、rはsigned許容。σ0ではdeterministicOU discount。h0ではidentity/bond1。a→0の本文A式は巨大差の差し引きになるため、private計算ではkernel/series/expm1等で安定化する。本文はnonnegativeconstantsを述べるがVasicek r はnegativeになり得る。Signed b拡張を採用するなら原baselineとの差を明記する。

Longzero yield (a>0) は b−σ²/(2a²)。負値になってもdiscount>1が数学上不正とは限らない。率/volの単位だけで境界を設けず、表現可能性を検査する。

Scratch4cases（a0、σ0、negative r含む）でbookA/BとGaussian核bondはdouble表示差0。全9 Vas/CIRcasesのPDE有限差分 residual/Pは≤1.11e−11。積分法とRiccati/閉式は別計算にした。

## 6. CIR、正値・境界・bond

Q: `dr=a(b−r)dt+σ√r dW`。γ=sqrt(a²+2σ²)。31.2の閉式:

\[
 B=\frac{2(e^{\gamma h}-1)}{(\gamma+a)(e^{\gamma h}-1)+2\gamma},\qquad
 A=\left[\frac{2\gamma e^{(a+\gamma)h/2}}{(\gamma+a)(e^{\gamma h}-1)+2\gamma}\right]^{2ab/\sigma^2}.
\]

独立Riccati: `B_h=1−aB−.5σ²B²`、`logA_h=−abB`、B(0)=logA(0)=0。ClosedbondとODE差≤7.22e−16。Closed計算はe^-γhでscalingし、longhのoverflowを避けた。

Exactstate transition、a>0/σ>0/h>0:

\[
 r_{t+h}=q\chi'^2_d(nc),\ q=\frac{\sigma^2(1-e^{-ah})}{4a},\ d=\frac{4ab}{\sigma^2},\ nc=\frac{r_t e^{-ah}}q.
\]

Mean=b+(r−b)e^-ah、Var=rσ² e^-ah(1−e^-ah)/a+bσ²(1−e^-ah)²/(2a)。χ² pdfの別積分で3casesのconditionalmean差≤2.14e−13、variance差≤4.41e−14、Laplace差≤9.10e−13（tail cutoffも含む）。

- Feller2ab>=σ² (d>=2) ではpositive initial rからzeroに到達しない。ab>0,d<2ではzeroが到達可能でもpositivefuturetimeのendpointlawにzeroatomはない。r0=0からの状態と「常にstrictpositive initialrate」の前提を区別する。
- ab0 (df0) はabsorbingzero atomがある。Scipy df0へそのまま投げない。a0/r0.04/σ.1/h2例をPoisson mixture centralχ²(2n)＋zeroatomexp(−nc/2)で検算、zeroatom=.0183156。Mean/variance/LaplaceをJSONに保存。
- σ0はdeterministic OU、h0はidentity、r<0はCIRbaseline不適合。
- Eulerendpointはnegativeになり得る。Reflection/abs/clampは分布を変更する。Nearzero例のnegativeprobabilityとreflectedmeanbiasを保存。**Exactendpointだけでは∫r discountのexactsampleは得られない**。CIRpath pricingはtime integration/refinement/別bondoracleを必要とする。

Longyield=2ab/(a+γ)。Localvolmatching例r=.04、Vasσ=.01→CIRσ=.05。初期同じlocalvolでも、将来distribution/meanreversion/curveのconvexityは一致しない。

## 7. Duration、bond process、option

31.9/10: ∂rP=−BP、R=−logA/h+(B/h)r。Alternative shortduration Dhat=B、convexity Chat=B²。Coupon Q=ΣciPiのDhat/ChatはPVweightsによるB/B²平均。`hullkit.rates.macaulay_duration` はyield sensitivityで別物。

Ex31.1 p725: D_yield=4、10bp→approx.4% price drop。a.1/h4でB=3.29679953964、10bp→approx.329679954%（掲載.33%）。Exactfinitebumpは1−exp(−B*.001)なので近似との差も保存。

31.11/12: `dP/P=r dt−σ B_vas dW`、CIRは `r dt−σ√r B_cir dW`。Bondnoiseの符号をpositivevolmagnitudeと区別し、P/Qriskpremiumへ正しく用いる。

補助practicepins（本文Ex31.1とは別、GE730/著者解答）:

- 31.4: a.1/b.03/σ.01/r.02/5y、ZCB1のpriceが.8966へ丸まる。
- 31.8: a.13/b.012/σ.01/r.01、2y/face100/annualcoupon3/semiannual1.5。Q=103.9083303564、Dhat=1.72536854376、Chat=3.01098639556、r+.0005のexactQ=103.8187293710。掲載103.9083/1.7254/103.8187に丸まる。解答proseの乗算に **1.7524** があるがtableは1.7254。数学結果と原表記を区別する。
- 31.9: a.1/b.1/r.1/h10/Vasσ.02、CIRσ=.02/√.1。掲載bond.38046/.37986へ丸まる。

### 7.1 合成 ZCB option の独立 kernel/density 検査

Ch31本文はbondoptionの価格式/価格例を掲載しない。下記は**明示synthetic補助fixture**で原典pricepinではない。

Expiry S/bond U/K。VasicekはQ^S下でr_SのmeanがQmean−Cov(r_S,I_S)、varianceは不変。Gaussiantruncatedpayoff integralとbondBlackvarianceB(U−S)²Var(r_S)を比較し差7.29e−17。

CIRのQ^Sdriftはab−[a+σ²B(S−t)]r。Time-dependentCIRtransitionをg'=-k(t)g、q'=σ²/4−k(t)qから構成、degree4ab/σ²。Rate lawはqχ²_d(r0g/q)。Underlyingbond=Ae^-Brのexponentialtiltでχ²CDFのclosedpriceを作り、別pdfpayoff quadratureと比較。差1.15e−14、discountsemigroup差3.34e−16、putcallparity差0。**Q endpointlawの期待payoffに初期P(S)を掛けるだけの誤測度**を避ける。

### 7.2 TN15 coupon option の再利用境界

Positive futurecashflows、単因子monotonebondならJamshidianの共通r*を使える。Expired/alreadypaidcoupon、negativeCF、payment=expiryのeventsideを勝手に増補しない。

TN15例a.1/b.1/σ.02/r0.1、expiry3/strike98、futurepayments[3.5,4,4.5,5]、CF[5,5,5,105]。既Ch32scratchのr*=.10952220733、componentstrikes[4.73414862,4.48365349,4.24769127,84.53450661]、Jamshidian=.875125636367、独立Gaussian integral=.875125636367、差2.33e−15。

原掲載total **.8752** との差はhalfunit.00005を超える。原component末尾桁/早期丸め/誤植の可能性はあるが原因未確定。Exactcanonicalpriceを.8752へ丸め合わせない。TN15はCh31bodypinへ新しく混入せず、補助source差として保存する。

## 8. §31.3 P/Q と market price of risk

Bookの規約: **P drift=Q drift+λ_short*s(r)**。λ_short<0は本文のbondpremium説明の仮定で、すべての時代の実証法則とはしない。

Vas: aP=aQ=a、σ共通、bP=bQ+λσ/a、inverse bQ=bP−λσ/a。Pbondreturn=r−λσB。CIR λ=k√r: aP=aQ−kσ、bP=aQbQ/aP、inverse aQ=aP+kσ、bQ=aPbP/aQ。Productab不変、Pbondreturn=r−kσBr。

aP/aQ0のときb=constantdrift/aを割算せず、driftcoefficientsを用いる。MappingでCIRpositiveimmigration/meanreversiondomainが失われる場合を検査する。Affineλのpractice31.6/13ではより一般に `aP=aQ−λ2σ`、`aPbP=aQbQ+λ1σ`。CIRλ1/√rはzeroでsingularなので、測度同値性の条件を省略しない。

Scratchの31.5/12parametersで往復、practice31.10 λ=−.6/B5=3.93469、Qbondreturn4%→P6.3608%を保存。`girsanov_weights` のGBM例を金利 P/Q変換専用APIの代用に数えない。

## 9. §31.4 canonical case study、OLS/ML、Table31.1

既回収元seriesは1982-01-04〜2016-08-23、**8664rateobservations、8663adjacentpairs**。Header3monthrate(%)を100で割る。Min.01%/max15.49%、numericfinite・重複0・欠測cell0。Calendar日gap1/2/3/4/5日は6756/99/1537/270/1本。休日/欠測原因のlineageは不明。本文の手法は各observedpairを **1/250year** としgap別Δtに変更しない。3monthrateをinstantaneousshortのproxyに使った原設定を明示する。

Euler Δr=α+βr+ε、α=abPdt、β=−adt。OLSsource保存:

| 量 | 元未丸め値 |
|---|---:|
| intercept | .000009146996484883016 |
| slope | −.0005446147281124214 |
| residualSD (df n−2) | .0007540332971975618 |
| a / bP / σ | .13615368202810535 / .016795352774585375 / .01192231325375477 |
| r0 / savedλ | .003 / −.1746227999177317 |
| fittedbQ | .03208621888158632 |

本文p727丸めintercept .00000915/slope−.000545/SD.000754、a.136/bP.0168/σ.0119と一致。本文Qb式の **.168** は前記.0168/worksheetと不整合。未丸めbPを採用し、原誤字を消さない。

Table31.1(p728)、market/modelは%表示、date2016-08-23:

| T | Market% | Model% |
|---:|---:|---:|
|.5|.45|.40|
|1|.58|.49|
|2|.74|.65|
|3|.86|.80|
|5|1.15|1.06|
|7|1.40|1.27|
|10|1.55|1.52|
|20|1.88|2.02|
|30|2.24|2.26|

元9 fullprecisionrowsは主JSONと `/tmp/p3-input-recovery/vasicek-independent-check.json`。Objectiveはcontinuouszerorate差の二乗和、9点等weight、σ/a/Pparams固定でλだけfit。IndependentOLS元との差≤3.09e−15、元λの9rates差≤6.77e−16。Affineλでclosedoptimum **−.17462279986916754**、元Solver差4.86e−11、SSE6.64899468309e−6。

Externalprovider/seriesid/basis、marketpointsのquoteconstructionは元worksheet未記載。DTB3/DGS3MOなど別seriesに置換せず、originalsnapshotをcanonicalにする。旧notebookの「curveへa,b,σを直接fit」は本文のP時系列→Qλ2段階と別。

### 9.1 今回取得した31.15の Euler MLE

Problem31.15は同じ全series（差0）。元annualsaved a=.136157109925、bP=.016796243296、σ=.011920937057、objective115914.222878。

EulerGaussianMLEとOLSはintercept/slopeが同じ最適解になるが、σの分母は **n**（OLSunbiasedSDはn−2）。Solverの未丸め差とこの自由度差を残す。「同じ結果」という掲載3桁の主張と、全桁同一を区別する。

ExactOUtransitionMLEはlevelAR coefficientρ=1+Eulerβからa=−logρ/dt、σ²=innovationvar*2a/(1−ρ²)。ExactOUとbookEulerのモデルが異なるので、exactMLEを元pin代替にしない。系列の2000以降/2010以降cutoffのOLSを追加し期間感度をJSON保存した。Forecastvalidation/新market calibrationとは扱わない。

### 9.2 新しい31.16の source不整合（重要）

同じseriesでCIREulerGaussianpseudo-likelihoodはvar=σ²r_prev dt。元annualsaved Pparams **aP=.200688493067/bP=.024675993141/σ=.077192937618**、objective118585.717597。独立formulaを元値で評価し元objectiveを再現。ClosedweightedLS（weight1/r_prev）からaP=.200663642532/bP=.024679119170/σ=.077193028297。原Solverの丸め前差を保ち、掲載.201/.025/.077と整合する。

Qcurvefit元saved **k=−.026596672649**、aQ=.198635417774/bQ=.024931041673/r0=.003、9点marketはTable31.1と同じ。元SSE6.68906923084e−6。

**元H5:H13の式は**
`2*(EXP(gamma*T)-1)/((gamma+a)*EXP(gamma*T-1)+2*gamma)`。
**本文の正しい式は**
`2*(EXP(gamma*T)-1)/((gamma+a)*(EXP(gamma*T)-1)+2*gamma)`。

RawBIFFtokensとscratchLibreOffice→XLSXの括弧を照合。Aの式は本文CIR式と整合し、Bだけが異なる。T.5のsavedB=.381833613511に対しcanonicalB=.475860135328。Wrongformulaは元9ratecached値を≤8.16e−17で再現。元ファイルを修正していない。

保存Pparamsを固定し本文canonicalCIRで独立fitすると、aQ≈.180440557303/bQ≈.027444982172/**k≈−.262302956570**、SSE≈**3.30364491570e−6**。正式著者訂正ではなく、同一data/weight/parameter mappingでの数学比較。解答の「kが極小でP/Q差が小さい」は元誤Bfitに依存するため、canonicalCIRの結論として転載しない。

元curvefitcached/誤式再現/canonicalat元params/canonicalrefitをすべて別列で保存。正しい式の結果を元保存pinに強制一致させない。ExactCIRtransitionχ²loglikelihoodも元Pparamsで評価したが、exacttransitionMLEoptimizerは未実行。NormalEulerpseudo-likelihoodを「正のCIR厳密遷移尤度」と呼ばない。

証拠: `/tmp/p3-ch31/problem3116-formulas-raw.json`、`problem3116-converted-formulas.json`、`converted/HullOFOD11eProblem 31_16.xlsx`。Convertedcachedは式の補助確認で、原cachedを上書きしない。

## 10. §31.5 / TN14 全 Appendix を再利用

GE31.14は `dr=(u−ar)dt+σ1dW1, du=−bu dt+σ2dW2`、**equilibrium θ0**。TN14は `d f(r)=[θ(t)+u−a f(r)]dt+σ1dW1`、初期u0=0、correlationρ明示、θはinitialcurvefit。f(r)=rのみ解析Gaussianで、genericf/logr/tree説明を同じclosedbondのscopeに混ぜない。

B=B(a,h)、C=∫_0^h D(v)dv、D=(e^-bh−e^-ah)/(a−b)、P=exp[−Br−Cu+V_I/2]（θ0）。u/θはrate/year、σ2はrate/(year√year)、Cはyear²。Cのa=b極限とa/b0はGaussian核で除去可能特異点を扱う。

再利用 `/tmp/p3-two-factor-design.md`、`p3-two-factor-fixtures.py/json`、独立notesは次を全て含む:

- (r,u,I)conditionalmean/cov、θ0とcurvefitの整合、singlefactor、negative r/u、u0の原設定と明示拡張。
- TN14Appendixのηと**γ1–6**を独立kernelsで照合。原gamma閉式のcancellationとvol係数込み価格誤差を区別。
- F(0,t)/φ(0,t)のθ式のsuffix微分は**maturity方向**が必要。Firstargumentpartialとしての読みと区別し、公式errataではなく記号導出を明示。
- ExactZCBoptionvariance、a=b、ρ±1、allvol0、h0。Instantaneousrank1でもfinitehorizonstatecovarianceはrank2になり得る。
- y=r+u/(b−a)変換、σ3/ρ23、a=b/σ3=0境界。Equilibriumr0/u0とcurvefitcenteredstateを混ぜない。
- Couponmomentlognormalは**近似**。2DconditionalGaussian/rootintegralの独立教師を別保存。TwofactorをTN15単因子Jamshidianで分解しない。

TN14のhump例a1/b.1/σ1.01/σ2.0165/ρ.6は原数値。曲線/価格を任意生成したsynthetic値は印刷pinではない。GE31.5自体はρを明示しないので、実装入力でρを記録する。解答31.14のcrossσ1σ2にρが書かれない式を一般ρの公式として用いない。

Longstaff–Schwartz1992のtwofactorCIR型は紹介であり、別モデル全実装を必須に発明しない。Ch27.8のLSM（M17）と名前だけで同一視しない。Ch31章単位の不足を、既存M29flatHW＋deterministicprojectionbasisで受入済みに置換しない。

## 11. 公開coverage、private仕様候補、依存

| 部品 | 実際のcoverage | Gap |
|---|---|---|
| `hullkit.hull_white` | Constanta/σ、curvefit、OUcenteredstate、ZCB/Jamshidian/calibration | Params a>0のみ。StationaryQ Vas/CIR/RB/θ0HW2Fとは別 |
| `hullkit.rates` | Continuouscurve/CFdiscount、yield/duration/convexity、bootstrap | Modelconditionalbond/PDE/PQestimationではない |
| `hullkit.credit` / `copula` Vasicek | OnefactorGaussiancreditloss | 金利OUとは別 |
| 旧 IR notebook | simulateVas/CIR/RB、curveillustration | CIRreflectedEuler/RBcumulantapprox、再利用専用受入ではない |
| `hullkit._numeraire_choices` M29 | FlatHW conditionalpayment/annuityGaussianmixture | FullCIR/RB/多曲線jointdynamicsではない |
| Twofactor/Gaussian scratch | 全source式の独立教師 | 製品module/API/lesson/gatesは未作成 |

Scope内private候補: `ShortRateParameters(measure,model,kappa,constant_drift,sigma)`、Vasexactjoint/conditionalbond、CIRbond/exacttransition/boundary、RBexactendpoint＋pathdiscount、shortduration/couponCF、P/Qdriftmapping、bookEulerOLS/MLと固定curveλfit、twofactorequilibrium/curvefitを明示したkernel。公開API/依存追加は今回行わない。

入力: finite、year/rate/vol単位、h>=0、model/measure、sourceparams、coupon/pay/eventside、samplingcount/seed/pairSE。Outputは価格、method exact/approx、validationoracle、sourcepin/derived/synthetic区分、MC/quad/refinement誤差、calibrationobjective/rank/optimizerstatusを保持する。

P3依存: §28のQ/numeraire/riskprice、Ch4CF/rateunit、Ch32curvefit/tree、Ch33HJM/LMM特殊例、RB-H31/H32。Ch31正式5単位もP3全体も未受入を維持。任意initialcurve完全fitはCh32側、HJMgeneralhistory/LMMmulti-curveはCh33側。今回準備で公開契約を先に変更しない。

## 12. 保存・検証・次の工程

保存物:

- `/tmp/p3-ch31-fixtures.py/json`: 原sourcehash、新archive原本、5実台帳/13draft、Vas/CIR/RB/PQ/OLS/ML/31.16両式/option/conditionalmoments、再利用TN14/15へのhash参照。
- `/tmp/p3-ch31-source-design.md`: 本メモ。
- `/tmp/p3-ch31/source-downloads.json`、元XLS/PPTX、slides-text、BIFF/convertedformula証拠。
- `/tmp/p3-ch31-audit.json`: source/fixturehash、要件count、finite/数値誤差の読み取りsnapshot。正式製品gateではない。

再実行: `/home/kazumasa/projects/.venv/bin/python /tmp/p3-ch31-fixtures.py`。Python3.12.3/numpy2.4.6/scipy1.17.1、xlrdは既installed環境を使用。新productiondependenciesなし。

今回実行: 原典GE本文/問題/著者補助sourceを照合、元31.15/16download/blob検証、31.16式のraw/converted照合、独立math/quad/Riccati/χ²/Poisson/OLS/WLS/1parameterfit、RB5000antitheticpairsの16/64/256sharednoise比較、source系列期間感度。旧TN14/31.4/15の計算は参照再利用し、全旧scriptを再実行したとは主張しない。

未実行: productpytest/ruff/release/ledgergate/browser/D1、製品実装、lesson/renderedfigure、CIRjoint-integralexactsample、exactCIRMLEoptimization、newrealmarketfit、twofactortree、genericnonlinearf(r)、source誤式の公式著者確認。Source数値の準備完了を5節acceptedと表示しない。

後続は31.1/2のprivate数学・境界→31.3測度→31.4canonical2段階推定とsource差→31.5/TN14kernel/curvefitの順に進める。Draft要件登録、独立validation、visualization/rendered、要求台帳/ROADMAP照合を実装時に行う。原印刷値との不整合は消さず、元資料の再現と数学上のcanonicalを並列に説明する。