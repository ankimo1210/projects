# M31 §28.6 / 次節§28.7 — 原典・独立oracle・実装境界の準備

- 日付: 2026-10-04。**読み取り専用の準備資料。実装・受入・D1・main統合の宣言ではない。**
- root: /home/kazumasa/worktrees/m29/johnhull。
- 原典: Hull 11e Global Edition、options, futures and other derivatives 11th.pdf、PDF/印刷pp.680–682。
- 原典本文の抽出: /tmp/m31-source-pages.txt。
- 画像を確認: p.680はM30作業の /tmp/m30-source-p680.png、
  p.681/682は /tmp/m31-source-p681.png、/tmp/m31-source-p682.png。
- 参照したprep: docs/prep/sections/ch28.md、docs/P3_REQUIREMENT_AUDIT_2026-10-04.md。
- 既存§26.14の対応: docs/SECTION_26_14_ACCEPTANCE_2026-09-17.md、
  scripts/build_exchange_reference.py、hullkit/tests/test_exchange_reference.py。
- 出力: /tmp/m31-source-design.md、/tmp/m31-fixtures.py、/tmp/m31-fixtures.json。
- **§28.6・§28.7とも原典に数値例・印刷価格pin・表・図はない。全fixtureはsynthetic。**
- 重要な節名訂正:
  - §28.6 = **Black's Model Revisited** (pp.680–681)。
  - §28.7 = **Option to Exchange One Asset for Another** (pp.681–682)。
  - 「Black's Model for Pricing Futures Options」「利子率オプション」は実際の節名と一致しない。
    M31は§28.6、M32を§28.7とする次順序を想定した。個々の受入は分ける。

## 1. §28.6 原典の全範囲

### 1.1 ページ/式/要点

| 場所 | 本文内容 | 受入で落とさないこと |
|---|---|---|
| p.680開始 | §18.8は定数金利でforward/futures価格によるBlack模型を説明。本節は確率金利へ拡張 | 確率金利下で一般にfuturesをそのまま代用する導出ではない |
| p.680式28.26 | c=P(0,T) E^T[max(S_T−K,0)]、T満期ZCB numeraire | Qで割引因子を外に置く誤りと区別 |
| p.680次行 | T満期forward F_0/F_Tを定義し、S_T=F_T | optionの給付日とforward満期の一致 |
| p.680対数正規の仮定 | T-forward worldでF_Tがlognormal、std(log F_T)=σ_F sqrt(T) | QやPのspot lognormalだけでは仮定を満たすと断言しない |
| p.680式28.27 | lognormal call payoffの期待値。式15A.1から導く | 求積教師でlognormal payoffを直接確認 |
| p.681前半 | E^T[F_T]=E^T[S_T]=F_0を28.21から使う。d1/d2を定義 | 期待値はF_0であり、実測度の将来予測でもfutures価格一般でもない |
| p.681式28.28/28.29 | callとputのBlack式 | 両方向、同じσ_F/DF/F_0/Tとparity |
| p.681 §28.6末尾 | investment/consumption assets双方に適用。確率金利でも同じ満期のforward asset priceを使う | consumption spotへno-income投資資産のcost-of-carryを勝手に適用しない |
| p.681 §28.6末尾 | σ_Fはforward asset priceのvolatilityと解釈できる | spot volatilityとの相違、terminal分散/Tという有効volatility |

脚注は§28.6の対象段落にない。新しい式番号は28.26–28.29。
以後の§28.7は別の受入単位。Ch29の利子率商品・schedule・notionalはこの節に暗黙に追加しない。

### 1.2 要求分解案

元D28.6-01/02を保持し、例えば6要求へ分解する。

| 仮ID | 元要求 | 内容 | 独立証跡 |
|---|---|---|---|
| BF01 | D28.6-01 | T債numeraireと28.26、S_T=F_T | 経路割引Qと直接T標本の別計算 |
| BF02 | D28.6-01 | E^T[F_T]=F_0、28.27のlognormal期待値 | momentsとcall/putの独立求積 |
| BF03 | D28.6-01 | 28.28/28.29、d1/d2、parity | 3strike・call/put・全数値表 |
| BF04 | D28.6-02 | T-forwardのlognormal仮定、σ_F sqrt(T) | spot σ≠forward σ、確率rでの別分布 |
| BF05 | D28.6-02 | option/forward満期一致、futures代用の条件 | futures≠forwardのcounterexampleと定数r/zero covarianceの極限 |
| BF06 | D28.6-02 | investment/consumption適用範囲、正値lognormal契約と極限 | F市場入力を直接与えた2asset-type例、σ/T→0、DF>1のnegative-rate例 |

全要求へsource/API/numerical/notebook/browserを割り当てる。
既存Black核があるだけではBF01/BF04/BF05を受け入れない。

## 2. §28.6 契約・単位と既存関数

- F_0/Kは同じ通貨価格、σ_Fはyear^-1/2、Tはyear、P(0,T)はdimensionless。
- F_0>0、K>0はlognormal模型。負Fのnormal/shiftedはこの導出とは別の模型。
- P(0,T)>0。**P<=1という制約は付けない。** negative interest rateならDF>1もvalid。
- σ_F>=0/T>=0の極限はdeterministic payoffへ連続。既存核はσ=0/T=0を拒否するため、
  既存public APIを黙って変更しない。
- optionとforwardは同じ満期T。異なるforward満期を代入したものは同じ契約にならない。
- 実装がspot σを受け取る場合、forward σへの変換モデルを明示する。Black式自体へspot σを渡さない。
- 条件はterminal lawがT-forward worldでlognormalであること。
  instantaneous σ_F(t)がdeterministicなら、
  variance(log F_T)=integral σ_F(t)^2 dt、
  effective σ_F=sqrt(variance/T)でBlack式を使える。
  本文もterminal対数正規分布を直接仮定し、constant instantaneous volatilityだけに限っていない。

利用候補:

| 関数/資産 | 使えること | 注意 |
|---|---|---|
| ir_options._black | 汎用scalar Black代数。既存private kernel | finite/P0Tの包括的検査やσ/T=0入口ではない |
| ir_options.bond_option_black | 同じBlack代数を公開入口から呼ぶ数値比較 | APIはbond optionと命名・記載されている。generic asset formulaと同じ代数であることを説明 |
| ir_options.caplet_black/swaption_black | 後続Ch29の接続例 | notional/accrual/annuityはこの節のoptionと区別 |
| M29 Gaussian/measure private helpers（確定後） | model-consistent stochastic-rate dataset候補 | 参照教師まで同じ関数に依存させない |
| M30のfactor covariance規約 | forward driverの統合分散/測度loadingの説明 | 汎用price engineの新public export不要 |

最小実装案はprivateのforward_black_price(DF,F,K,σ_F,T,kind)あるいはlesson dataset buildだけ。
finite real/temporal/complex/正値/domainの検証とzero-limitをprivate境界で明示し、
正のσ/Tなら既存Black核を呼べる。公開signatureやdependency追加は不要。
kindはcall/putのみ。batch対応を作るならaxis/broadcast・invalid+empty batchの規約を固定する。
公開入口のσ/T=0拒否は既存仕様であり、そのまま保持した場合は極限を小σ/Tで検査してよい。

## 3. §28.6 独立oracle: arbitrage-free Gaussian rate教師

### 3.1 モデル

これはsynthetic Ho–Lee型のillustrationであり、Ch32 §32.1の受入ではない。

under Q:
r_t = r0 + η W_t^r、
dS/S = r_t dt + σ_S dW_t^S、
dW^r dW^S = ρ dt。

J=integral_0^T r_s ds、Y=log S_T。

m_J=r0 T、
v_J=η² T³/3、
cov(J,W_T^S)=ρ η T²/2、

m_Y=log S0+m_J−0.5 σ_S² T、
v_Y=v_J+σ_S²T+ρ η σ_S T²、
cov(J,Y)=v_J+σ_S cov(J,W_T^S)。

P(0,T)=E^Q[exp(−J)]=exp(−m_J+0.5v_J)、
F0=S0/P(0,T)。

T-forward密度はexp(−J)/P(0,T)。Gaussian tiltによって

Y under T ~ Normal(m_Y−cov(J,Y), v_Y)、
E^T[S_T]=F0。

これに対し、futures proxy E^Q[S_T]=exp(m_Y+0.5v_Y)は一般に違う。

forward volatilityは

σ_F(t)^2=σ_S²+2ρ σ_S η(T−t)+η²(T−t)²、
integral_0^T σ_F(t)^2 dt=v_Y、
effective σ_F=sqrt(v_Y/T)。

σ_S=0でもstochastic rateからσ_F>0になり得る。
投資資産だけでS0/Pという導出を使う。consumption assetのfixtureは市場Fを外から与える。

### 3.2 2つの求積経路

教師はstdlib math/numpy/scipy.quadのみで、hullkitも既存Black/BSM/Margrabe関数もimportしない。

1. under QのYについて、条件付きdiscount E[exp(−J)|Y]をGaussian momentで解き、
   payoffと掛けて1次元求積する。
2. under TのYを直接求積し、P(0,T)を外から掛ける。
3. 比較用closed式はmath.erfcによるCDFを使ったpure math Black式で、
   実装側の関数とはコードパスを共有しない。
4. Qでは(J,W_S)を厳密joint Gaussianで生成し経路割引する。
   TではYのmeanをGaussian tiltで直接変更した標本を使う。

Brownian integralは、terminal W_rと独立bridgeから
J=r0T+η[(T/2) W_T^r+sqrt(T³/12) Z_bridge]
と生成する。Eulerや時間離散割引は使わない。

### 3.3 fixture

- 7市場、各strike=70/105/140、call/putで21契約・42方向。
- 共通S0=100、T=2、通常σ_S=.25。ηは0/.03。
- 定数r、stochastic正相関ρ=.75、負相関−.75、rate-stock相関0、negative r0=−.02、
  cov(J,Y)=0の特殊例、σ_S=0のstochastic rateを含む。
- provided forwardのinvestment/consumption各1例とDF>1の1例も保存。
  investment/consumptionの同じF/K/DF/σ/Tでは同じ価格になる。spot cost-of-carryは仮定しない。
- 12個のσ/T極限入力をpure math oracleへ保存。

主要counterexample (r0=.04, η=.03, σ_S=.25, ρ=.75, T=2, S0=100, K=105):

| 量 | 値 |
|---|---:|
| P(0,T) | .9242247509120064 |
| forward F0 | 108.19879028485443 |
| futures Q mean | 109.68582972743454 |
| effective σ_F | .27376997644007645 |
| 正しいcall (Q求積) | 16.646020956477173 |
| 正しいcall (T求積) | 16.646020956477162 |
| 正しいput (T求積) | 13.689619802237797 |
| futuresをF0へ代入したcall | 17.489345461300253 |
| P0T×Qのpayoff期待値 | 17.489345461300243 |
| σ_Sをσ_Fへ代入したcall | 15.351654561793541 |

r0=−.02の例はP0T=1.04206049680502でvalid。
ρ=−2ηT/(3σ_S)の例ではcov(J,Y)=0、Gaussianによりdiscountとterminal assetは独立になり、
stochastic rateでもこの契約のfutures meanとforwardが一致する。
これは特別な模型条件であり、一般のfutures代用を許可する結論ではない。

### 3.4 MC zero-hitの扱い

262144 direct pathでは、σ_S=0・K=140のcallにpayoff hitがなかった。
**true priceは7.168352139439199e−8で、sampling SE=0をdeterministic/価格0として受け入れてはいけない。**

該当caseと極小K=70 putには独立normal importance shiftを追加した。
non-normalized Gaussian likelihood exp(−θZ−θ²/2)を使用し、
Q側はshiftしたYとJ|Yを直接生成、T側はshiftしたYを直接生成する。
shiftと元hit count/各SEをJSONへ記録した。既存girsanov_weightsは使っていない。
zero-hitを受入PASSとして隠さず、最終numerical gateではこのimportance routeまたは独立求積を使う。

### 3.5 実測結果

- Q/T求積とpure math closed式の価格差最大: 8.526512829121202e−14。
- call-put parity差最大: 8.526512829121202e−14。
- E^T[S_T]とF0の差最大: 7.105427357601002e−14。
- 非退化direct MC価格の最大|z error|: 1.7575034441185464 SE。
- zero-hit caseのimportance MCの最大|z error|: .9211494194831541 SE。
- 受入threshold案: price absolute 1e−9/relative 1e−11、moments 1e−10、MC5SE。
  極小rare-eventではabsolute-only一致を完全なMC検証と呼ばず、zero-hitを明示する。

## 4. §28.7 原典の全範囲と要求

### 4.1 本文

| 場所 | 内容 | 受入範囲 |
|---|---|---|
| p.681 §28.7最初 | investment asset Uを渡しVを受け取るoption。§26.14既出 | 給付max(V_T−U_T,0)、U/Vの向き |
| p.681式28.30 | 無配当のU numeraireでV0=U0 E^U[V_T/U_T] | 各assetが違うWienerに依存するので多因子28.15を使う |
| p.681式28.31 | optionもfにでき、価格=U0 E^U[max(V_T/U_T−1,0)] | ratio strike=1、option自身のpriceのmeasure pricing |
| p.682上段 | σhat²=σ_U²+σ_V²−2ρσ_Uσ_V、Problem28.13参照 | covariance cross term、±1/σhat=0 |
| p.682式28.32 | V0N(d1)−U0N(d2)、d1/d2 | lognormal ratio求積とclosed式の対応 |
| p.682中段 | income q_f/q_gがあると28.15はe^((q_f−q_g)T)補正。Problem28.8参照 | dividend spotをそのまま無配当tradable numeraireと呼ばない |
| p.682中段 | E^U[V_T/U_T]=e^((q_U−q_V)T)V0/U0 | no-income martingaleとincome driftの区別 |
| p.682下段 | price=e^(−q_U T)U0 E^U[max(V_T/U_T−1,0)] | optionはincome0、numeraireのincome q_Uによるprefactor |
| p.682最後 | e^(−q_V T)V0N(d1)−e^(−q_U T)U0N(d2)、d1 dividend差、式26.5に一致 | 既受入§26.14へ数値的/論理的に接続 |

新しい番号付き式は28.30–28.32。income式は番号がない。
脚注は本節本文にない。§28.8はp.682最下段見出しから別範囲。
§28.7にはAmerican exercise/better-of/worse-ofの再受入要求はない。
§26.14の既受入のそれらの内容は保持し、この節のU measure導出の代用にしない。

### 4.2 6要求の案

| 仮ID | 元要求 | 内容 |
|---|---|---|
| XE01 | D28.7-01 | 28.30、無配当U measureのconditional ratio mean |
| XE02 | D28.7-01 | terminal exchange payoff、ratio strike1、28.31 |
| XE03 | D28.7-01 | σhat、multi-factor loading差、28.32の価格 |
| XE04 | D28.7-02 | income-adjusted28.15、総収益U numeraireとspot Uの区別 |
| XE05 | D28.7-02 | dividend差のconditional ratio mean、e^-qUT price prefactor |
| XE06 | D28.7-02 | 26.5との接続、既受入synthetic anchor、退化/r非依存/契約 |

## 5. §28.7 配当の数学規約

under Q:
dU/U=(r−q_U)dt+s_UᵀdW、
dV/V=(r−q_V)dt+s_VᵀdW。

numeraireは配当再投資を含む総収益Ubar_t=e^(q_U t) U_t。
spot U_tにincomeがあるとき、U_tそのものをself-financing numeraireと記載しない。
本文の「U world」はこの総収益資産を使う解釈で、

under U:
mu_U = r−q_U+||s_U||²、
mu_V = r−q_V+s_Vᵀs_U、

d(V/U)/(V/U) = (q_U−q_V)dt+(s_V−s_U)ᵀdW^U。

したがって
E^U[R_(t+h)|F_t]=R_t exp((q_U−q_V)h)、
no incomeならconditional martingale。

Rはspot V/U。総収益ratio Vbar/Ubarならmartingale。
price_t = U_t exp(−q_U h) E^U[max(R_(t+h)−1,0)|F_t]。

discounted-Q密度は
D_U = exp(−J) Ubar_T/U0
    = exp(s_UᵀW_T−0.5||s_U||²T)。
q_Uもrの共通integralも密度から消える。measureの方向はQ→U。

既存exotics.exchange_option/exchange_spread_volatilityは価格/σhatに再利用できる。
M30 private multifactor helperを使う場合、元のU/V spot driftに
−q_U/−q_Vを加えてincome effectを明示する。no-income helperだけをそのまま使わない。
新公開signature/public exportは不要。
既存exchange_optionはT=0を拒否する。intrinsicの正確なT=0極限はprivate教師または小T収束で扱う。

## 6. §28.7 独立oracleと数値結果

- 11市場×V0/U0=.8/1/1.25の33契約。
- 常にU0=100。σ=.2/.25、asymmetric .15/.45、ρ=0/.3/.5/±1、
  q_U/q_V=0/.01/.02/.03/.06、T=1/1.5/2。
- U measureのratio lognormalを1次元で求積。
- Q measureではdiscounted VをU shockへ条件付け、
  内側のtruncated-normal momentsをmath.erfcで計算し、外側を独立に求積。
  Margrabeのclosed式やhullkitを教師から呼ばない。
- 正しいpriceから「e^-qUTを省く」「ratio meanのdividend差を省く」誤りを保存。
- 3観測ratio×3horizonのconditional U/Q平均を各契約へ保存。
- 262144 pathのratio直接U sampler、Q sampler、density momentを保存。
- r0=0/.08/−.02の定数rと、r0=.04/η=.03の共通stochastic rを比較。
  stochastic rate driverはstock driversと相関させている。

discounted terminal U/Vの共通Jがpathwiseに消えるので、
Qの割引給付はmax(V0 exp(−qV T−.5σV²T+σV W_V)
                − U0 exp(−qU T−.5σU²T+σU W_U), 0)となる。
rate-kernelを変えた同じGaussian stock noiseで価格が変わらないことを実測する。

結果:

- U-ratio/Q-conditioning求積の価格差最大: 1.2079226507921703e−13。
- 非退化MC（ratio mean/price/density）の|z error|最大: 1.5777687746633866 SE。
- stochastic/定数rateのdiscount cancellationの単一path差最大: 5.002220859751105e−12。
  これは大きいterminal cash値のfloating-point丸め。価格mean/variance差とは区別し、
  pathwise比較はabsolute+relative toleranceで扱う。
- M6 repo anchor: U0=V0=100, σU=σV=.2, ρ=.5, q=0, T=1で
  **7.965567455405798**。
  原典§26.14も数値例はなく、7.965567は既存リポジトリのsynthetic anchor。
  新たなprinted valueとして台帳へ登録しない。
- 本scratch全Black/交換求積の±12σ tail upper bound最大: 3.811398175010189e−28。

## 7. 図・Book/portalの提案

### M31

6小節を新たなvol10 §6E相当へ追加し、M29/M30までの既存セル・出力を保存。

1. forward vs futures、満期一致、何の測度でlognormalか。
2. 28.26–27とT-forwardの期待値。
3. call/put・d1/d2・parity。
4. 確率r下Q path-discountとT-forward sampling。
5. spot σとσ_F、convexityのcounterexample。
6. investment/consumption、zero limits、negative-rate DF、後続Ch29。

4図:
- black_forward_measure: Q/Tのterminal distributionとforward/futures平均。
- black_forward_prices: Q求積/T求積/Black、call/put/strike。
- black_forward_volatility: σ_S、instantaneous σ_F(t)、integrated/effective σ_F。
- black_forward_misuse: futures代用、Q discount外置き、spot σ代用の誤差。

### 次節M32

6小節をvol10 §6F相当へ追加し、旧§4.4交換教材は保持して出典を接続。

1. terminal exchange payoffとU measureの向き。
2. 無配当conditional ratio martingale。
3. multi-factor ratio volatilityと28.32。
4. 配当再投資Ubar numeraire。
5. income-adjusted ratio mean/price prefactor。
6. §26.14既受入との接続、退化/相関/共通rate cancellation。

4図:
- exchange_measure_ratio: observed ratio/horizonとU/Q mean。
- exchange_measure_income: q_U/q_Vによるratio meanとnumeraire prefactor。
- exchange_measure_prices: U-ratio/Q-conditioning、旧M6 anchor、ρ endpoints。
- exchange_measure_density: Q→U density moment、stock/total-return ratio、共通rate cancellation。

いずれも4図×Book/portal・所定の16状態を現行pipelineで確認する案。
σ_Fとspot σ、配当spotと総収益assetを軸/ラベル/凡例で曖昧にしない。
M29受入中の現在、browser/release/D1/pytestは実行していない。

## 8. 改変拒否と後続境界

M31数値改変:
Q payoff期待値に固定Pを掛ける、futuresをFへ代入、spot σを使用、
wrong maturityのforward、put式符号、time units二重変換、DF>1を拒否。
MC zero-hitをdeterministic PASSとして扱う変更も検出する。

M32数値改変:
V/UをU/Vへ反転、sigma covariance cross termを削除、
income meanのq_U−q_Vを反転、e^-qUT省略、spot Uを無配当numeraire扱い、
現在observed ratioを初期比へ固定、ρ=±1を逆行列で処理する。

入力契約:
finite real/temporal/complex拒否、positive price/forward/strike/DF、
nonnegative σ/T、ρ∈[-1,1]、negative rとfinite qは許す。
既存publicのzero-limit拒否をprivate wrapperで変更する場合も明示する。
invalid+empty batchやbroadcastによりvalidationが無効化されないよう検査する。

後続:
- Ch29 bond option/caps/floors/swaptionの商品CF、notional/accrual/schedule、
  RFR/negative-rate normal模型は個別原典要求として残る。
- Ch30 convexity/timing/quantoはここで示すcounterexampleだけで受入しない。
- §28.8はnew/old numeraire比と非取引変数のdrift補正で別受入。
- §31.5/32.1のHW2F/TechnicalNote14、Ch33 HJM/LMMは一般multi-factorという
  名前だけで本教材の範囲へ含めない。
- P3全37節・historical calibration/market inputsの要求は保持する。
  本scratchのsynthetic教師をその不足の代替acceptedにしない。
