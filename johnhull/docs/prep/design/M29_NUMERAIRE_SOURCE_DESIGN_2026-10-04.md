# M29 §28.4 原典要件・独立参照・教材設計（準備のみ）

日付: 2026-10-04。対象: /home/kazumasa/worktrees/m28/johnhull。
依頼: root が M28 を完了している間に、次節 M29 を読み取り専用で準備する。
この文書と /tmp の scratch 以外は変更していない。Git 操作、pytest、notebook fresh execution、browser/配布受入は行っていない。
以下は実装/受入ではなく、原典照合と独立小例の再計算結果である。

## 1. 原典・照合済み範囲

一次出典: Hull, Options, Futures, and Other Derivatives, 11e Global Edition、
/home/kazumasa/worktrees/m28/johnhull/options, futures and other derivatives 11th.pdf。
SHA256: 8bc6e2f04fad95e4eeb40d0526219ba5f9228ee3d2ea3eaaf80870bdf7ccb482。
PDF ページ番号と印刷ページ番号は一致。§28.4 は pp.676–679。
pdftotext -layout の文字抽出と、全4頁の PNG を見て式の記号・上下限・脚注を照合した。
抽出は /tmp/m29-source-pages-676-679.txt、画像は /tmp/m29-page-676.png ... -679.png。
特に p678 の一般変数は θ（抽出で u に見える）；原典の期待値表記は Q の箇所が \hat E。
画像 p676 の上部は §28.3 の式28.14/15、末尾から §28.4 が始まる。
p679 末尾の §28.5/脚注7は次節であり、本節の原典要求に混ぜない。

既存草稿: docs/prep/sections/ch28.md:82。
現行監査: docs/P3_REQUIREMENT_AUDIT_2026-10-04.md:90–105。
関連準備設計: docs/prep/design/P3_DESIGN.md と
docs/prep/design/P3_TREE_LMM_IMPLEMENTATION_2026-10-04.md:116–150。
草稿の「既存専用なし」等は古い。本節未受入という点と本節の3原典要求を使い、
M28 の進行状態は root の現在の成果を優先する。

**印刷値の扱い:** §28.4 に Example、Table、Figure、印刷された価格/MC ピンはない。
p677 の口座初期価値 $1、p679 の元本 $1 は定義/規約。
p678 の 0.5 年と 0.25 年は半期・四半期複利の説明入力であり、価格の出力ピンではない。
以下の a=.2、η=.02、flat zero4%、spot100、strike105 等はすべて合成入力。
「Hull の数値例を再現した」と表示してはならない。原典の恒等式を数値検証する独立小例である。

## 2. 原典の全項目と式の場所（草稿3項目を展開）

| 細項目 | 原典の正確な位置 | 必須内容・数値/契約確認 |
|---|---|---|
| N01 | p676末尾、§28.4導入 | §28.3の同値martingale結果が従来のrisk-neutral評価と整合し、bond option/cap/swap optionへの基礎になる。 |
| N02 | p677上部 Money Market Account、式28.16 | M0=1、dM=r M dt。rは確率的でよい。Mのdriftは確率的でも瞬間拡散/二次変分はゼロ。ゼロvolを「Mが決定的」と読み替えない。 |
| N03 | p677上部～中央、式28.17–19 | Qは口座numeraireの測度。\hat E[M0 fT/MT]、MT=exp(∫0^T r dt)、f0=E_Q[exp(-∫r) fT]=E_Q[exp(-rbar T) fT]。各経路の給付を同じ経路の平均短期金利で割引する。 |
| N04 | p677中央下、定数金利の無番号式 | r一定なら exp(-rT) E_Q[fT]。確率rでこの形に戻さない。σr→0の極限と対比する。 |
| N05 | p677脚注5 | 短期口座は Δt期間の投資/再投資を連続化したもの。別通貨の口座も同様だが、教材は同一通貨に固定。 |
| N06 | p677下部～p678冒頭、式28.20 | P(t,T)は時点Tに$1を払う無リスクZCB。P(T,T)=1、f0=P(0,T)E_T[fT]。割引は外側の既知DF、終点Tだけの給付に便利。QとTの期待値を区別する。 |
| N07 | p678上部、θT−Kの契約→無番号2式→式28.21 | 金利以外の任意変数θのforward給付をθT−Kと定義し、f0=P0T(E_T θT−K)を導く。ゼロ価値を与えるK=FなのでF=E_T θT。stockは一例。 |
| N08 | p678式28.21直後、脚注6 | futuresは従来のQ下の期待spot（§18.6）、forwardはT測度下の期待spot。確率rでは差がありうる。金利FRAの定義/支払が異なるので、金利へθの式を機械適用しない。 |
| N09 | p678下半 Forward Interest Rates 第1–2段落 | F(t)は[T,T*]の金利、複利期間δ=T*−Tに合わせた年率表示。Rも同じ頻度。δ=.5は半期、δ=.25は四半期。F(t)−RがT*で払われるFRAは時点tにゼロ価値。元本Lを加える教材なら給付Lδ(F−R)。 |
| N10 | p678下半、式28.22と直後 | E^{T*}[R|Ft]=F(t)。numeraireは支払日T*のP(t,T*)。原典のE表記の条件付けは時点tとして説明。overnight risk-free curveのRはT*まで未確定、その他curveのRはTで既知。どちらにも同じ支払測度原理。 |
| N11 | p679上部 Annuity Factor 第1段落～式28.23 | swap開始T、T0=T、Ti支払、元本1、t≤T。A(t)=Σi=0..N−1 (Ti+1−Ti)P(t,Ti+1)>0。固定側=s(t)A(t)、浮動側=V(t)、s=V/A。schedule/day-count年率、開始/支払を区別。 |
| N12 | p679中央、式28.24–25と最後の段落 | E_A[s(T)|Ft]=s(t)、V0=A0 E_A[V(T)/A(T)]。Aはrisk-free zero curve、Vは任意のprojection yield curveを使える（原典例LIBOR vs OIS）。Aをprojection curveで作らない。後続Ch29の欧州swaptionの基礎。 |

草稿要求との対応:
D28.4-01 = N02–06（Q内側割引とT外側割引、同一給付価格）。
D28.4-02 = N07–10（一般forward、futuresとの差、金利の支払日/確定時点）。
D28.4-03 = N11–12（annuity/swap、2曲線の役割）。
N01/脚注N05/N08の意味も教材に残す。草稿の短い行を原典全体として扱わない。

式をまとめると（式番号/頁は原典どおり）:

- 28.16 (p677): dM_t = r_t M_t dt.
- 28.17 (p677): f_0 = M_0 \hat E[f_T/M_T].
- 28.18 (p677): f_0 = \hat E[e^{-\int_0^T r_t dt} f_T].
- 28.19 (p677): f_0 = \hat E[e^{-\bar r T} f_T], \bar r = T^{-1}∫r.
- 28.20 (p677): f_0 = P(0,T) E_T[f_T].
- 28.21 (p678): F = E_T[θ_T].
- 28.22 (p678): E_{T*}[R] = F(t), with implicit conditional information at t.
- 28.23 (p679): s(t) = V(t)/A(t).
- 28.24 (p679): s(t) = E_A[s(T)], conditional at t.
- 28.25 (p679): V(0) = A(0) E_A[V(T)/A(T)].

## 3. 計算契約と必要な補足

本節の原典定理は特定モデルを指定しない。実演モデルは以下の定数係数1因子Gaussian短期金利である、と明示する。
一般の多因子導出は§28.5、一般numeraireのdrift補正は§28.8、Blackのlognormal分布仮定は§28.6/29に残す。
原典にある確率r・支払日・annuity・複数curveの論点は本節から除外しない。

M_t=exp(J_t)、J_t=∫0^t r_u du。
正値取引numeraire、無裁定、比の可積分性等はM28の数学的補足を引き継ぐ。
Aは最初の支払前t≤Tにおける正のZCB portfolio。
短期金利やV、swap rateはGaussian実演では負でもよい。必要な正値はnumeraireであり、
V/Aを既存の「positive ratio専用」関数へ押し込まない。

時点tのRN:
Z_t^T = dQ^T/dQ|Ft = P(t,T)/(M_t P(0,T)).
終点では Z_T^T = exp(-J_T)/P(0,T)。
Z_T^A = A(T) exp(-J_T)/A(0)。
E_Q Z=1をraw weightsで確認。価格:
E_Q[D_T H_T] = P0T E_T[H_T]、
E_Q[D_T C_T] = A0 E_A[C_T/A(T)]。
重みをself-normalizeして誤ったZを隠さない。正規化式とforward/fixing方向をmetadataに固定する。

年を時間単位にする。r,F,R,sはyear^-1、OU aはyear^-1、
spot loading s_Sはyear^-1/2、short-rate diffusion ηはrate/year^1/2。
δはyear、Pはunit-notional価格、Aはyear×unit-notional価格。
forward priceとoption priceは名目価格。元本1のVと率sを混同しない。
金利のsource symbol Rと割引のD、curveとstateを明確に分ける。

## 4. 独立Gaussian参照: joint(state, integrated rate)

合成 Q モデル:
dx_t = -a x_t dt + η dW_t, x0=0、
r_t = x_t + φ(t)、P0t=exp(-r0 t)、
φ(t)=r0+c(t)。

B(h)=(1-exp(-a h))/a、
q(h)=Var(x_h)=η²(1-exp(-2ah))/(2a)、
v(h)=Var(∫0^h x_u du)=η²/a²[h−2B(h)+(1-exp(-2ah))/(2a)]、
c(h)=Cov(x_h,∫0^h x_u du)=η² B(h)²/2。
E_Q[J_t]=r0 t+v(t)/2、E_Q exp(-J_t)=P0t。

独立oracleでは上記閉形式だけをproductionと共通化しない:
K_x(u)=η exp(-a(t-u))、
K_J(u)=η B(t-u)の積/平方を数値積分してq,v,cを別に得る。
φの積分も別にquadする。
条件付き [x_u, ∫t^u r] は同じfuture incrementから生成する。
OU stateのexact endpointだけを生成し、台形積分rを「exact」と呼ばない。
η=0は決定的分岐、a>0をモデル境界とする。a≈0/small a hでは安定なseries又はkernel積分を検討し、public a>0契約を黙って拡張しない。

正しいconditional bond:
P(t,U|x_t) =
exp[-∫t^U φ(v)dv − B(U−t)x_t + v(U−t)/2]
= P0U/P0t × exp[-B(U−t)(x_t+c(t)) − B(U−t)² q(t)/2]。
時点0curve fitだけでなく
E_Q[e^{-J_t}P(t,U|x_t)]=P0U
および条件付きtowerを必須検査にする。

一般joint Gaussian Xのcash→T tiltは mean_T=mean_Q−Cov_Q(X,J_T)、covarianceは不変。
Qのdirect joint samplerとTのdirect tilted samplerを別に動かし、同じpayoffを計算する。
stock実演:
dS/S=r_t dt+s_S dW_t（無収入・同一因子）、
logS_T=logS0+J_T−s_S²T/2+s_S W_T、
Cov(J_T,W_T)=η/a[T−B(T)]。
var(logS)=v+s_S²T+2s_S Cov(J,W)。
E_T S_T=S0/P0T、
E_Q S_T=(S0/P0T)exp[v+s_S Cov(J,W)]。
s_S正/負でfutures−forwardの符号を反転できる。s_S=0でもrの積分の乱数がSに入る。
stockをprice-only消費財や配当spotと同一視しない。

### 金利の二つの実現方式

Term（合成advance-set risk-free rate）:
R_T=(1/P(T,T*)−1)/δ、Tで既知。
overnight:
R_on=(exp(J_T*−J_T)−1)/δ、T*で既知。
どちらもF0=(P0T/P0T*−1)/δ。
termにovernightの未知期間を足したり、R_onをTで固定したりしない。

Q^{T*}下のterm状態:
x_T ~ N(−c(T)−B(T*−T)q(T),q(T))。
Q^T下のmeanは−c(T)であり、一般にはE_T R≠F0。

overnight区間 I=J_T*−J_T の kernel:
K_I(u)=η[B(T*−u)−1_{u<T}B(T−u)] (0≤u≤T*)。
m_I=r0δ+[v(T*)−v(T)]/2。
v_I=∫K_I²、Cov(I,J_T*)=∫K_I K_JT*。
支払測度 mean(I)=m_I−Cov(I,J_T*)。
その指数モーメントからE^{T*}R_on=F0を計算する。
2区間に同じ過去stateが効くので、J_TとJ_T*を独立に生成してはいけない。

### Annuity測度はexact finite Gaussian mixture

expiry T、future payments U_i>T、accrual δ_i>0。
A(T,x)=Σδ_i P(T,U_i|x)。
w_i=δ_i P0Ui/A0、Σw_i=1。
Q^Aにおけるx_Tは、component Q^{U_i}:
N(m_i,q(T)), m_i=−c(T)−B(U_i−T)q(T)、weights w_i の混合。
単一Gaussian/単一lognormal swap-rateへ置き換える必要はない。

単一curve浮動leg:
V(t)=P(t,T)−P(t,U_N)、s=V/A。
原典の2曲線の役割を保つcoherent小例:
time0 projection zero5%、discount zero4%、各δ=.5。
b_i=F_p(0;U_{i−1},U_i)−F_d(0;U_{i−1},U_i) を決定的spreadと定義し、
projected realized couponは同じterm R_d+b_i。
V(t)=P_d(t,T)−P_d(t,U_N)+Σδ_i b_i P_d(t,U_i)。
A(t)はP_dで作り、projection curveはb_i/浮動cashflowにのみ作用する。
この例はtime0のprojection curveを一致させた合成決定的basisモデルであり、
「任意の二つのcurveを独立に確率発展させれば無裁定」とは主張しない。
sourceのLIBOR/OIS例を現市場データと称さず、2曲線の機能を示す。

conditional t<T, observed x:
h=T−t、
mi(t)=exp(-ah)x−c(h)−B(U_i−T)q(h)、
wi(t)=δ_i P(t,U_i|x)/A(t,x)。
直接mixtureの積分でE_A[s(T)|Ft]=s(t)を、複数t/stateで確認する。
s0の無条件平均1点だけでmartingaleを証明したとは書かない。
必要に応じC_T=max(V(T)−K A(T),0)を
Q joint integral と A0 E_A[(sT−K)+]で比較する（Black分布仮定は追加しない）。

## 5. 独立数値fixture（実行済みpilot。全入力synthetic）

保存:
- /tmp/m29-fixtures-20261004.py（hullkit importなし、math/scipy kernel/条件付き求積）
- /tmp/m29-fixtures-20261004.json
- /tmp/m29-conditional-20261004.py（独立conditional求積と、現行APIの別診断）
- /tmp/m29-conditional-20261004.json

a=.2、η=.02、r0=.04。
T=2のmJ=.0803993902503167、vJ=.0007987805006333891、
q=.0005506710358827785、c=.000543444360229715、
Cov(J,W)=.035160023017819654、P0T=.9231163463866358。
閉形式v/cとkernel別積分は約1e−18まで一致。

stock S0=100、K=105、T=2:

| signed s_S | E_Q S_T（futures参照） | E_T S_T = F0 | Q求積call | T求積call | 誤ったP0T E_Q payoff |
|---:|---:|---:|---:|---:|---:|
| +.25 | 109.37244366983968 | 108.32870676749582 | 16.371618639526922 | 16.371618639526908 | 16.961233852890174 |
| −.25 | 107.46647739330601 | 108.32870676749592 | 14.457903895380923 | 14.457903895380921 | 13.982226733077484 |
| 0 | 108.41527219490550 | 108.32870676749582 | 3.262096905703644 | 3.262096905703631 | 3.331721538361991 |

sourceのθT−K forward PVは全ケース3.072783629403247。
Q conditional-discount求積、T直接分布求積、独立erfc lognormal閉形式の3経路を照合した。
η→0 fixtureは次工程で追加（sourceのconstant-rate極限）。

支払測度の金利:

| T | T* | δ | F0 | term E_Q | term E_pay | term E_wrong_fix | overnight E_Q | overnight E_pay | overnight E_wrong_fix |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1.25 | .25 | .04020066833667223 | .04044174384154650 | .04020066833667223 | .04027987386649393 | .04044985301292015 | .04020066833667225 | .04028798271299435 |
| 1 | 1.5 | .5 | .04040268005351162 | .04071450075951733 | .04040268005351169 | .04055497906211700 | .04074607693161754 | .04040268005351161 | .04058655276592262 |
| 2 | 2.5 | .5 | .04040268005351162 | .04118481143545717 | .04040268005351171 | .04065707450452432 | .04121639488471980 | .04040268005351157 | .04068864978806257 |

FRA PV=Lδ P0T*(F0−E_pay R) は unit Lで約4e−17以下。
δ=.25/.5は原典にある複利説明を使った合成市場である。
rates.forward_rateの連続forward=.04をこのsimple rateと混同しない。

annuity expiry T=1、U=(1.5,2,2.5,3)、δ=(.5,.5,.5,.5)：
A0=1.8283193673620008、
w=(.2575492417780046,.25244942510196083,.24745059156199511,.24255074155803938)、
component mean x=
(−.0003211586776035506,−.00046309688430040425,
−.0005915278847686396,−.0007077370596280928)、
q=.00032967995396436067。

| curve設定 | V0 | s0 | E_A s(T) | E_Q s(T) | E_T s(T) | Q値E[D V(T)] |
|---|---:|---:|---:|---:|---:|---:|
| discount=projection4% | .07386900243516570 | .04040268005351162 | .04040268005351162 | .04083906496053721 | .04070055262064586 | .07386900243516571 |
| discount4%/initial projection5% | .09256825028383309 | .05063024104885768 | .05063024104885768 | .05106662595588325 | .05092811361599191 | .09256825028383310 |

各b=.01022756099534606。A0はcurve間で同一（OIS側が同じ）。
synthetic K=.045 のC=max(V−K A,0)：
single curve Q=.007475487515170067 / A=.007475487515067669、
basis Q=.017039215473552423 / A=.01703921547369889。
求積のkinkにより約1.5e−13の差；受入oracleではrootで分割積分すればさらに安定する。
これは原典の印刷swaption価格ではなく、同じ給付の測度不変性の補助例。

条件付きfixture（contract T=1,T*=1.5、同じannuity schedule）：

| t | x_t | F(t,x) | pay-measure mean(term) | s(t,x) | A-measure mean(s_T) |
|---:|---:|---:|---:|---:|---:|
| .25 | −.015 | .02798793138663802 | .02798793138663788 | .02966040842473685 | .02966040842473687 |
| .25 | 0 | .04048428485644040 | .04048428485644044 | .04050776810336686 | .04050776810336688 |
| .25 | .02 | .05726595208460639 | .05726595208460642 | .05508373669397536 | .05508373669397544 |
| .75 | −.015 | .02679784809886865 | .02679784809886862 | .02870713201755571 | .02870713201755572 |
| .75 | 0 | .04060481427529039 | .04060481427529061 | .04069206810680105 | .04069206810680102 |
| .75 | .02 | .05916052232080693 | .05916052232080703 | .05680980597957411 | .05680980597957413 |

## 6. 既存APIの再利用危険（本準備で修正していない）

### HW stateの不整合:独立診断で実際の関数値を確認

hullkit/src/hullkit/hull_white.py:
docstring 1–5、hw_phi 85–100、hw_discount_bond 103–119、
hw_exact_transition 122–141、simulate_hw_paths 144–168。
phi=f0+c(t)、stateはQのzero-mean OU xと書かれている。
現行bond式は P0U/P0t exp(-B state−B²q/2) で −B c(t)がない。
このbond式はstate=y=x+c(t)（Q^tでzero-mean）なら正しいが、
Q xのsimulate/phiと同じstateとして使うとtowerを破る。

a=.2,η=.02,flat zero4%,t=2,U=5,x=.01:
現行実API .8659217989431358、
独立conditional-integral .8648608476090708、
現行/正しい=1.0012267306781177。
Q割引tower:
correct .8187307530779819 = P0(5) .8187307530779818、
現行 .819735115209901。
hw_phi actual .04054344435582883 vs independent .04054344436022972は有限差分の約4.4e−12差。
同じ候補はP3_TREE_LMM_IMPLEMENTATION準備に既出。rootが次工程でRED→GREENを扱う。
独立oracleに現行bondをimportしてexpectedを作らない。

他の危険:
- simulate_hw_pathsはendpoint stateのexact transitionのみ。積分r/discountを返さず、MCの台形積分誤差は残る。
  またgridの最初にinitial_stateを置くので、grid[0]>0でも0→grid[0]を生成した意味ではない。
- rates.forward_rate は連続複利、source F/Rはδ自身の複利期間のsimple年率。
  対応はF=(DF(start)/DF(pay)−1)/δ。rates.forward_discountはDF(pay)/DF(start)（逆の向き）。
- hw_phiのinstantaneous_forwardは零曲線線形補間をfinite difference。曲線knot付近の微分を積分oracleと共通化しない。
  ∫f0 はDFのlog差で別計算できる。
- HullWhiteParamsはa>0・η≥0。Ho–Lee a=0を既存APIへ黙って許可しない。
- _martingales.pyはconstant-GBM、positive ratio、relative drift専用。確率r・integrated r・signed swap rateのエンジンではない。
- sde.girsanov_weightsはterminal GBM/constant driftでWを復元する単因子部品。
  stochastic-numeraireのZ=D/P0TやZ_A=D A/A0へそのまま適用できない。
- ir_options.swaption_blackは与えたs,AのBlack価格を返すだけ。annuity measureを生成/検証しない。
  caplet_blackはfixing timeとpayment DFを分けるが、overnight Rが期末まで未確定な分布の教師ではない。
  _blackはσ=0/T=0/F≤0を拒否するので本節のdeterministic/negative-rate極限のoracleにしない。
- Vol10現§7は定数rのQ/stock/T-forward MC。Q/Tの分布差を示す証拠ではない。
  builder 2866–2930は原典不足箇所を明示、2958–2965のswap measure pointerは未検証の説明。
  「numeraireの選択だけでBlackが成立」の短文は分布仮定が省かれているため、
  M29教材で§28.6/29への依存と、lognormal仮定が別に必要なことを明記する。

## 7. 最小private実装/参照の提案

public exports/APIやproduction依存を増やさず、private lesson/fixture moduleとして始める。
例えば _numeraire_choices.py に
(1) exact OU joint moments/state-integral sampler、
(2) stochastic discount/conditional bond（state規約明記）、
(3) payment-measure exact mean/sampler、
(4) annuity mixture parameters/direct sampler、
(5) scheduleからA,V,sを計算、を置く。
_general Gaussian density tiltを本節のconstant 1-factor範囲に限定して実演できる。
名前はrootの実装規約に合わせる。独立reference scriptは同じproduction関数を呼ばない。

Validation:
finite real inputs、complex/object complex、NaN/Inf、empty invalid settings、
times t≤fix≤pay（δ>0）、ordered payment>expiry、positive DFs/accruals、
factor/normal axisのshape、representable exp、varianceの非負。
sourceでは負のr/R/sを排除していない。η=0/T=tならdirect deterministic分岐を入れる。
stateがxかyか、numeraireがcash/pay/annuityか、fixingかrealized dateかをmetadataに保存する。

教師の独立性:
- scalar math/kernel quad のmomentsとproduction vectorized moment式を別実装。
- Q direct joint discount積分とT direct Gaussian積分を別経路。
- annuityは Q conditional-discount積分 と direct mixture積分を別経路。
- source恒等式のclosed algebra、numerical integral、direct samplerの三者を使う。
- curve/schedule/unitsや固定入力の共有は可。production price/driftを共通化して独立と呼ばない。
- 保存数値JSONとそのdigests、非有限/shape/数式一致を描画前に検査する。

次工程のmeaningful tests / mutation候補:
1. E[D]=P0T、E[D P(t,U)]=P0U、条件付きtower（legacy欠落-cをRED検出）。
2. covarianceを除いたjoint discount、期待値の外にQのDFを出した誤式を拒否。
3. Q→pay RN逆向き、wrong fixing numeraire、term/on fixing日の入替を拒否。
4. sourceのδcompoundingをcontinuous rと取り違えたfixtureを拒否。
5. annuityをterminal/pay/Qで代替、単一Gaussian混合近似、projection DFでAを構成する誤りを拒否。
6. positive/negative spot loading、deterministic short rate、negative short rate、
   1payment annuity=δP（その測度はpayment forward）、scale notional、複数conditional stateを確認。
7. raw E[Z]、E[Z H]、逆重み、SE・second momentを保存。self-normalizationを検査しない救済策にしない。
8. direct MCは例として262144（pair数を明示）×複数seed/fixture、SEはindependent pair単位。
   conditional fixturesは観測stateを固定しfresh future noiseで評価。
   解析差≤事前固定5SEとdeterministic oracle budgetを別々に判定。
   acceptance sampleを見てtoleranceを広げない。
提案tolerance: closed/kernel deterministic moments約1e−12 relative＋1e−15 absolute、
価格独立求積はsourceの単位に合わせ1e−9以下をpilotで固定。これはsource printed toleranceではない。

## 8. 教材6小節・4共有図の全提案

本節既存§7を、原典順で6小節として深める案。
M28以前のaccepted cells/figuresは適切なbaselineにより保存する。
現§7の未受入inline MCをどう置換/併存するかはrootがnotebook preservation契約に明記する。
§8の既存Girsanov/§28.1 accepted contentを誤って巻き込まない。

| 小節案 | source原子 | 教えること・必須表示 |
|---|---|---|
| 7.1 基準資産で価格式を選ぶ | N01,N02,N05,N06,N11 | M/P(T)/P(T*)/Aの対応表。価格と期待値の単位。Mのvol0と確率rを両立。 |
| 7.2 口座と満期債：割引の位置 | N03,N04,N06 | Q経路割引 vs T外側DF、joint(state,integral) exact、同一call/forward/cash価格、不正なQ外側DF反例。 |
| 7.3 一般forwardとfutures | N07,N08 | θT−KからF=E_TθTを導出。Q futureとT forward差。s_S正/負、deterministic-r極限。脚注6金利例外。 |
| 7.4 金利は支払日測度 | N09,N10 | δ=.5/.25のcompounding、T fixing vs T* overnight realized、両者E_pay R=F、wrong-fix反例。 |
| 7.5 Annuityとswap rate | N11,N12 | schedule→A、float V、s=V/A、conditional mean、Q/T/Aの異なる平均、exact mixture、V0恒等式。 |
| 7.6 2曲線と検証範囲 | N12＋全体 | discountとprojectionの役割、OIS/LIBORは原典例、合成決定的basis実演、no lognormal assumption、後続Ch29と§28.5/8の範囲。 |

Figure 1（choices_forward）:
2 panels。cash/QとTのterminal S密度（同じvariance・異なるmean）、
futuresとforwardのmean markers。menu「正loading/負loading」、η=0のlimit点も保存する。
hoverにmeasure/numeraire/S mean/source eq28.21/model syntheticを表示。
N06–08の理解用。静的numeraire mappingだけで数値要求を代替しない。

Figure 2（choices_pricing）:
同一terminal call HのQ discount・T direct・独立referenceの価格＋SE、
誤ったP0T E_Q[H]の値と差を別traceで示す。
menu「stochastic r/deterministic r」。
補助panelにraw weight E_Q Z=1とlog-discount/spot covariance。
N02–06、一般同一給付price invariance。callはsynthetic、Black derivationは§28.6。

Figure 3（choices_rates）:
TからT*のtimeline（term fixing T / overnight realized T* / payment T*）と、
F0/E_Q R/E_pay R/E_wrong-fix Rの対比。
menu「term/overnight」または「δ=.25/.5」を使用し、もう一軸はfacet/legendで明示。
F/Rは%表示、内部はdecimal year^-1。N09–10、0.5/0.25はsourceの規約入力。

Figure 4（choices_annuity）:
Q/T/Aのswap-rate平均とs0 marker、conditional state/mixture component weightを2panelで示す。
menu「single curve / discount4%-initial projection5%」。
A0、V0、s0、E_A s、QとAの価格、discount/projectionラベルをhoverに残す。
A0が同じでV0/s0が変わる理由を本文に説明。N11–12を全て数値と接続。
1payment/negative-rate conditional fixturesはテキスト表又は保存診断も使う。

共通:
4図のnotebook/Book/portalは同じ保存参照から描画し同一値を保証。
token-based paletteを既存スタイルから再利用、units/source/model/menu stateはtitle/axis/hoverに明記。
source formulaはMathJaxで表示し、captionには何がsourceで何がsyntheticかを含める。
各menuのtrace/customdata/SE/reference値を独立browser oracleで確認する。
両画面1440/1000（現行工程が要求する幅）でラベル/legend/axis overlapと最小plot幅700を検査。
4 figuresの必要なmenu全状態を検査対象にする；値改変negative controlも行う。
固定16画像など既存工程の件数へ無理に合わせるためにsource論点/menuを落とさない。

## 9. M29の受入要求候補（原典原子への逆引きを残す）

- NC01: N01–06、cash/terminal bondの定義・式28.16–20・footnote5・stochasticとdeterministic r、joint exact参照と同一価格。
- NC02: N07–08、θ forwardのゼロ価値導出・futures差・signed loading・rate exception。
- NC03: N09–10、δ頻度/term versus overnight/same payment measure/conditional mean、FRAゼロ価値。
- NC04: N11–12、schedule/annuity/V/A/conditional martingale/V0恒等式、2曲線の役割、positive Aとnegative rate。
- NC05: independent kernel/moment/conditional integrals/direct MC、limits、raw RN/SE、saved/API mutations、HW state tower hazard処置。
- NC06: 6小節/4共有図、旧accepted成果保存、Book/portal全menu/MathJax/width、D1/release evidenceとsource provenance。

NC01–06は全要求のexplanation/implementation/independent_validation/visualization/renderedを閉じる。
「数値印刷例なし」「説明主体」を理由に確率r/金利支払測度/annuity平均の検証をN/Aにしない。
M29完了判定とP3全37節の完了判定を分離する。

## 10. rootへの次の判断

1. 原典全12項目を確定specのNC01–04へ取り込み、M28 current baselineと§7置換範囲を明記する。
2. HW state x/yのRED fixtureを先に置く。既存public semanticsの変更はrootが承認済みscopeと照合する。
   ここでは独立oracleを既に作り、productionバグをそのoracleに取り込まない。
3. exact joint sampler/private utilitiesとterm/on/payment/annuityを順に実装し、本節5観点を検証する。
4. sourceには数値価格pinがない事実を維持。次節の印刷pinを本節のpinに流用しない。
5. Ch29へのlognormal価格式導入、§28.5多因子、§28.8一般drift変換は後続要件へそのまま残す。

