> 未受入の準備資料。原典回収とscratchの結果であり、製品実装・全5軸の正式受入は別途必要。

# M33 §28.8 Change of Numeraire — 原典・private契約・独立教師

- 日付: 2026-10-04。準備資料。**節の実装・受入・製品検証ではない。**
- 読み取りroot: `/home/kazumasa/worktrees/m29/johnhull`。
- 対象: P3全37節のうち§28.8。D28.8-01/02/03を保持する。
- 成果: `/tmp/m33-source-design.md`、`/tmp/m33-fixtures.py`、`/tmp/m33-fixtures.json`。
- Hull GEの実際の見出し: **28.8 CHANGE OF NUMERAIRE**、印刷/PDF pp.682–684。
- 本節にはExample・表・印刷された価格数値pinはない。教師の数値は全て合成入力。
- Git、repository編集、public API、製品pytest/browser/D1/releaseを実行していない。

## 1. 原典の確認と保存

本文は `pdftotext -layout` で抽出し、画像で式のstar位置・添字・脚注を確認した。

| 出典 | 範囲・証拠 | 留意点 |
|---|---|---|
| Hull GE p.682 | §28.8開始の見出し・対象変数f | 同頁前半の交換オプションと配当式は§28.7の要求。ここで再受入しない |
| p.683本文 | 取引fの2world、非取引v、式28.33–35、w=h/g | 変換はold g → new h。λ*−λを抽出テキストだけで判断しない |
| p.683脚注8 | 独立正規incrementからcovariance identity | 有限期間の共分散はΔtに比例。瞬間covarianceはCov/Δtの極限 |
| p.684本文 | P→Qの負λ内積、非取引変数にも同じ規則 | 非取引変数のQ driftがrだとは書かれていない |
| p.684 A Final Point | relative return/volatilityとabsolute drift/deviation | μ*=μf、σ*=σf。ゼロや負の状態にはabsolute表現が必要 |
| Technical Note 20 pp.1–2 | 非取引θに依存する取引fへのItô証明、複数因子拡張 | 本文p.683が明示的に引用している補助原典 |

保存した本文: `/tmp/m33-source-pages.txt`。背景の§28.4/28.5: `/tmp/m33-source-background.txt`。
画像: `/tmp/m33-source-p683.png`、`/tmp/m33-source-p684.png`、既存 `/tmp/m31-source-p682.png`。
TN20: `/tmp/m33-TechnicalNote20.pdf` / `.txt`、`/tmp/m33-tn20-p1.png` / `p2.png`。
本文pp.683–684とTN20両頁は画像確認済み。

### 1.1 Technical Note 20の来歴

公式Rotman FinHubのHull資料保管庫から、既に確認された固定commitを用いて回収した。

- repository: <https://github.com/rotmanfinhub/john-hull-textbook-resources>
- commit: `9b8dbfe37661dbd3de65d3a1489dc1297e840de7`
- source path: `Options, Futures, and Other Derivatives, 11th Edition/Technical Notes/TechnicalNote20.pdf`
- Git blob: `d6419be812b5aaf5663db718c1f598f641b1bc4b`
- 42,992 bytes、2頁、SHA256 `cb40c65d72a1e08b2ae130106c762655f9ab71e2e22b15f3f1f9334bc8819080`
- 固定raw URL: <https://raw.githubusercontent.com/rotmanfinhub/john-hull-textbook-resources/9b8dbfe37661dbd3de65d3a1489dc1297e840de7/Options%2C%20Futures%2C%20and%20Other%20Derivatives%2C%2011th%20Edition/Technical%20Notes/TechnicalNote20.pdf>

web取得はcontent-typeの制約で読めなかったため、同じURLのPDFを/tmpへ取得し画像確認した。
book SHA256、TN20来歴はfixtures JSONの`source_catalog`にも保存。
TN20 p.2には∂f/θと印刷された箇所があるが、直前のItô式/p.1の式と合わせれば∂f/∂θ。
最終行のλは添字が省かれている。教師は同じfactor iの差を用い、印刷の表記崩れを意味の違いとして実装しない。

## 2. 元要求を落とさない具体化

草稿3件は原典本文全体を表す索引であり、次の10点へ具体化できる。
CN08–10は原典式の適用条件・既存機能との接続を明示する受入契約であり、原典にない数値例を追加したという意味ではない。

| 仮ID | 元要求 | 内容・原典 | 独立教師 / 必要な証跡 |
|---|---|---|---|
| CN01 | D28.8-01 | 2worldの取引f、Δμ=(λ*−λ)·s_f、28.33前段 | signed vectors、基底回転、P/Q/g/hの整合 |
| CN02 | D28.8-01/02 | 非取引vにも28.33、TN20のchain rule | 非取引μ_Qをrに置かない例、θ→fの独立Itô照合 |
| CN03 | D28.8-01 | new/oldのw=h/g、s_w=s_h−s_g、28.34 | forward/reverse、ratio密度、条件付き未来平均 |
| CN04 | D28.8-01 | 28.35と脚注8: signed covariance=ρσ_vσ_w | 負covariance、PSD端、zero loading、瞬間/有限期間単位 |
| CN05 | D28.8-02 | P→Qは−λ_P·s_v、p.684 | 非正規化RN密度と加重平均、非取引を含む |
| CN06 | D28.8-03 | relative/absoluteの2表現、p.684 | 正/ゼロ/負state、absolute b·Δλ、時間・値の単位 |
| CN07 | D28.8-01/02 | Brownian方向と任意worldの同一risk basis | independent/相関座標、Cの重複適用を拒否 |
| CN08 | D28.8-01/03 | 局所式とstate-dependent/predictable volatility | HW annuityの局所loading、OU状態とbounded確率volの教師 |
| CN09 | D28.8-01 | 正値・取引・自己金融numeraire、income境界 | reinvested total-returnとspot densityの違い、可積分性 |
| CN10 | D28.8-01 | 同じ給付と条件付き期待値の測度整合 | Q/g/h価格、fix/paymentの金利、swap率、annuity mixture |

source/API/numerical/notebook/browserの5軸を各点に対応させる。
本/tmp成果はsource/design/numerical pilotのみ。browser、配布教材、台帳、D1の代わりにはならない。

## 3. 数学の規約

### 3.1 独立Brownianと符号

同じ独立因子に対して

\[
\frac{dv}{v}=\mu_v^{old}dt+s_v^\top dZ^{old},\qquad
\Delta\lambda=\lambda_{new}-\lambda_{old}.
\]

Hullのworld表現では

\[
dZ^{new}=dZ^{old}-\Delta\lambda\,dt,\quad
\mu_v^{new}=\mu_v^{old}+s_v^\top\Delta\lambda.
\]

したがって**同じ確率経路の座標表示**はold increment = new increment + Δλdt。
これを市場のtime series予測と取り違えない。
P→Qではλ_new=0なので、Δμ=−s_v·λ_P。g→hではΔλ=s_h−s_g。

\[
\frac{dw}{w}=s_w^\top dZ^g,\quad w=h/g,\quad s_w=s_h-s_g,
\]

\[
\alpha_v=\mu_v^h-\mu_v^g=s_v^\top s_w=\rho\sigma_v\sigma_w.
\]

wのg-measure相対driftは0。wの**log drift**は−||s_w||²/2。
vのlog drift差は、同じ局所diffusionではrelative drift差と同じだが、drift自体とlog drift自体は同じではない。

g/hは同じ通貨の正値取引numeraire。λ=s_gという表記は独立risk basisでのもの。
λの推定、非取引リスクを含む不完備市場の測度の一意性はこの恒等式からは得られない。
選んだλ/測度を明示して、同じ測度の下で非取引変数のdriftを変える。

### 3.2 条件付きRN密度

正値・自己金融numeraireのold gからnew hへの条件付き密度は

\[
D_{h/g}(t,T)=\frac{h_T/g_T}{h_t/g_t}.
\]

定数loadingの教師では

\[
D=\exp\{s_w^\top\Delta Z^g-\tfrac12\|s_w\|^2(T-t)\},\quad E_g[D\mid\mathcal F_t]=1.
\]

\[
E_h[X_T\mid\mathcal F_t]=E_g[D X_T\mid\mathcal F_t].
\]

未来の観測値v_tに条件付けた有限GBMは
E_h[v_T|F_t]=v_t exp((μ_g+s_v·s_w)(T−t))。
逆変換の密度は同じpathで1/D。逆向きのworldでincrementを生成する際はそのworldのBrownianを使う。
同じnormal標本へ符号だけを変えた重みを掛けて両方向が一致したと判断しない。
raw densityの平均1と加重値の双方を検査する。自己正規化しない。

bounded predictable loadingなら有限horizonでNovikov条件を満たす教師を構成できる。
一般の局所martingaleを密度として使える、zero driftだけで真のmartingaleといえる、という主張はしない。
一定GBMのdensity formulaを、将来の状態依存loadingにそのまま代入しない。

### 3.3 相関座標とPSD

dW dWᵀ=Cdt、C=L Lᵀ、row loadingの独立座標はs@L。

\[
\alpha_v=s_v^\top C(s_h-s_g),\quad
 dW^h=dW^g-C(s_h-s_g)dt.
\]

相関座標のBrownian shiftは**C(s_h−s_g)**。
単純内積形式にしたい場合のrisk vectorはC s_gであり、s_gそのものではない。
一般のworldのrisk priceは同じ独立basisで与えるか、相関座標のshiftの定義を明示する。
PSD rank欠損も有効。C^-1やCholesky jitterは必要ない。
null方向で異なるloading/risk表示は同じ市場を表せるため、raw vectorの一意性を要求しない。
直交回転時はs_v、s_g、s_h、λの全てを変換する。Cを二度掛けない。

σ_v=0やσ_w=0ならcovarianceは0、ρは未定義。ρ=0と定義したように表示せず、積を直接計算する。
脚注8が扱うCov(Δv,Δw)は小さいΔtでv w α_v Δt。
年率のα_vへ戻すにはv w Δtで割る。有限Δtのlognormal incrementでは高次項が残る。

### 3.4 absolute表現、状態依存、確率volatility

\[
dX=a_X^{old}(t,state)dt+b_X(t,state)^\top dZ^{old}
\]

なら

\[
a_X^{new}=a_X^{old}+b_X^\top\Delta\lambda.
\]

b_Xはvalue/√year、a_Xはvalue/year。X=0・負の金利・swap率にも適用できる。
相対loading b_X/Xへの除算はX≠0のときだけ行う。
本節の式は**時点・状態ごとの**補正。状態が将来変わればloadingと補正も変わる。

diffusion mapは測度変更で同じでも、状態のdriftが変わり、その状態の将来分布も変わり得る。
特に確率volのstate Yもb_Y·Δλを受ける。volatility lawが不変だとは一般化しない。
教師の確率vol例でYが不変なのは、YはB2、numeraire loadingsはB1、λ2=0という明示的な構成による。
一般のstate-dependentモデルをterminal joint lognormalと仮定しない。

### 3.5 income境界

配当spot gのprice driftはr−q_g。spotのg_T/(g_t M_T/M_t)の平均はe^(−q_g h)で、densityではない。
再投資したtotal-return numeraire G=e^(q_g t)gを用いる。

\[
W=H/G=e^{(q_h-q_g)t}h/g,
\quad D_{H/G}=e^{(q_h-q_g)(T-t)}\frac{h_T/g_T}{h_t/g_t}.
\]

同じrelative loadingsなので局所drift補正は変わらないが、densityのdeterministic income factorを落とせない。
spot h/gのG-measure平均は現在比×e^((q_g−q_h)h)。exchange節の配当結果と整合する。
annuityは開始/最初の支払前の固定債券portfolioとして使う。支払後は残存portfolio/再投資の定義が必要。
本教師はt≤swap開始T<最初の支払に限定し、途中の支払を跨ぐnumeraireを暗黙に使わない。

## 4. M29/M30との接続と不足するprivate契約

| 現行部品 | 利用候補 | 本節で埋める不足 |
|---|---|---|
| `_multi_factor_martingales.correlation_factor` | symmetric PSD、rank欠損、s@Lの規約 | 新しいpublic correlation APIは不要 |
| `factor_numeraire_drifts` / `factor_ratio_drift` | gのworldとratio Itôの縮約 | 任意old→new、非取引基準drift、absolute coefficientの説明 |
| `_multi_factor_lesson` §6D | signed、基底、raw RN、log/relativeの区別 | §28.8の非取引/P→Q/absolute/state依存要求は別に受け入れる |
| `factor_risk.factor_excess_return` | independent basisの(new λ−old λ)·loading | 既存APIは相関変換をしない。Cを渡すpublic拡張は不要 |
| `_numeraire_choices.FlatHW` / `joint_moments` | QのOU座標、支払測度のGaussian tilt | x/rのabsolute driftを局所signed covarianceで説明 |
| `annuity_values` / `annuity_statistics` | 同じadditive projection basis、OIS annuity、payment Gaussian mixture | Aのloadingは状態依存。単一Gaussianへの置換・V>0制約をしない |
| `rate_statistics` | termはfix T、overnightは実現U、同じpay U | P(T,U)/P(T,T)の正しい方向、fix測度をpay測度に取り違えるcontrol |
| `sde.girsanov_weights` | 既存単因子の尤度方向の説明 | terminal stockからWを回復する専用部品。汎用多因子/状態依存densityへ拡大解釈しない |

### 最小追加案（privateのみ）

1. `numeraire_drift_adjustment(variable_loading, old_loading, new_loading, correlation=None)`。
   - cov = variable_loadingᵀ C (new_loading−old_loading)。
   - old/new numeraire loadingはrelative。variable_loadingは対象SDEのrelative sかabsolute b。
   - 結果の単位は対象SDEのdriftと同じ。呼び出し側でrelative/absoluteを明記する。
   - final factor axisと先行broadcastはM30規約と同じ。Cは1枚のNxN PSD。
   - NaN/inf/bool/string/complex/object/temporal、empty factor、shape不一致、不正C、overflowを拒否。
   - zero/negative target stateを理由に係数を拒否しない。helperがXを割らない設計にする。
2. 任意worldの差は既存independent `factor_excess_return(new_risk-old_risk, variable_loading)`で表せる。
   - 追加private wrapperが必要なら同じbasisとold/newの順序を固定。public exportは不要。
3. density/path/constant conditional momentは教材と独立教師に置く。
   - 汎用state-dependent SDE simulatorやrisk-price estimatorを本節のためにpublic追加しない。
   - 瞬間helperからjoint lognormal、可積分性、市場較正が自動的に得られるとしない。

M29のHW座標はQでdx=−a xdt+ηdW、r=x+φ(t)。P(t,U) loadingは−ηB(U−t)。
Q→Uでdx driftは−a x−η²B(U−t)。短期金利のrelative volatilityへη/rを使う必要はない。
A=Σδ_iP_iのloadingはs_A=−ηΣδ_i B_i P_i/A。
swap率s=V/Aは符号を持ち得るのでabsolute loading b_s=η∂_x sを使い、Q→Aで
μ_s^A=μ_s^Q+b_s s_A=0を検査する。

## 5. 独立教師の内容と実行結果

実行: `/home/kazumasa/projects/.venv/bin/python /tmp/m33-fixtures.py`。
stdlib/numpy/scipyのみ。hullkitやratesvolのimport、製品コードの呼び出しはない。

### 5.1 signed多因子・条件付き密度・価格

9ケース: independent3、correlated3、negative covariance2、signed1、ρ=±1、near-singular、zero numeraire、zero target loading。
定数r=4%、未来horizon1.7年、tradedF0=100、g0=80、h0=110、callK=105。
非取引v0=2、μ_P=8%を別に置き、μ_Q=μ_P−s_v·λ_Pとする。
観測時点からの未来incrementへ条件付ける合成市場であり、歴史的な観測市場の再現とは表示しない。

Q価格は給付の1次元lognormal求積。
g/h価格はstock logを条件にした1/numeraireのGaussian指数momentを用い、別の被積分関数を求積する。
exercise境界で積分を分割してkinkによる誤差を抑える。

- 同一給付Q/g/hの最大差: **4.97e−14**。
- old weighted mean vs new conditional mean: **4.44e−16**。
- 直交回転差: **1.39e−17**、C再構成: **3.33e−16**。
- ρ=+1のnull方向にrisk representationを動かしても補正不変。
- density/reverse density/weighted Brownian meanはraw MCを保存。

correlated3例のg→h補正は−0.0059/year。比の向きを逆にすると符号が反転する。
相関Cを無視すると−0.0121/year、Cを二度掛けると+0.001855/yearの誤差が出る。

### 5.2 非取引とabsolute単位

TN20の独立chain-rule teacherはf(θ)=θ²+2、3状態、2signed因子。
f Δμ = θ Δm ∂_θ fの最大差は**2.22e−16**。
さらにX=−20/0/50のabsolute loadingを置く。X=0でも補正が有限、relative loadingは未定義。
nontraded μ_Qをrに置く必要がないことを数値と本文で示す。

### 5.3 M29の金利・swap/annuity

1因子HWのGaussian covarianceはOU kernelをSciPy積分して構成する。
条件付きbondは将来の短期金利積分のmean/varianceから計算する。M29関数は教師に使わない。
annuityはpayment-measure Gaussian mixture、Q側はX_Tに条件付けたpath discountを求積する。

4状態x=−.07/−.01/0/.025、t=.6、開始1.2年、支払1.7/2.2/2.7/3.2年、additive basis .005/.008/.006/.009。
負swap率（x=−.07では−.00385128）も扱う。

- EA[s_T] vs current s: **6.25e−17**。
- payer Q price vs A mixture price: **1.56e−17**。
- raw A/Q density mean1: **2.22e−16**。
- local A swap absolute drift: **1.48e−12 (annual-rate units)/year**以下。
  time derivativeは±2e−5年の中心差分なので、これは厳密zeroのnumerical pilot誤差。
- Q平均をannuity平均と取り違えると最大**0.000248626**のrate誤差。

同じHWの3状態でfix1.2/pay1.7年のterm rateを確認。
new/old = P(t,1.7)/P(t,1.2)、ratio loading **−0.00844016/√year**。
x drift補正は**−0.000168803 (annual-rate units)/year**。
E_payment[R] vs currentforwardは**7.63e−17**。
wrong fixing-measure平均は最大**0.0000996232**違う。
これはM29のterm/overnight/pay契約を保つ接続教師。SOFR市場契約や未知fixingを追加した例ではない。

### 5.4 状態依存の確率volatility: exactly defined predictableモデル

非取引state Yは独立B2でOU(κ=.8,ξ=.7)、Y0=.25。
stock/g/h/vとP risk priceはB1、loadingはbounded tanh(Y)。
時点0/.4/1.0に観測したYでloadingを次の区間まで凍結し、満期1.7年までの**この区間一定モデルそのもの**を厳密segment GBMで扱う。
連続σ(Y_t)モデルのEuler近似を厳密解と呼んでいない。

未来Y1/Y2の2次元Gaussian求積、条件付きB1の指数moment/call積分を用いる。
32×32 / 48×48求積の全出力差は**2.76e−14**以下、callpriceは双方**11.080940449908265**。
Q/g/h/Pで同じcallpriceをraw MC比較する。PではQ/P likelihoodを自己正規化しない。

- 非取引vの平均: P **2.3033318673**、Q **2.0307498254**、g **1.9766759956**、h **2.1368093773**。
- integrated variance of log ratioの分散: **0.0006302643**。
- log ratioのexcess kurtosis: **0.46564846**。
- よって局所drift変換が正しくても、terminal ratioを1つのlognormalとする根拠にはならない。
- 26個のMC集計は各131072標本、最大|z| **3.2233**。生のSE/平均/教師をJSONへ保存。

このteacherでYのlawが不変なのはnumeraire shiftのB2成分0による。
相関基底やY自身がshiftを受けるモデルでは、Yのlawも変えて将来のloading分布を作り直す。

### 5.5 incomeと負のcontrol

q_g=.04、q_h=.015、1.7年。
raw spot gのQ density候補meanは**0.93426047**、raw spot h/g候補のg-world meanは**1.04341606**。
reinvested total-return ratioならmean1。
JSONには9つの誤りのwitness（方向、絶対値化、C無視/二重、P→Q符号、income2件、wrong payment、wrong Q swapmean）を保存。
製品側mutation検査は未実施。これらは将来の検査設計の入力である。

## 6. 範囲・後続・実装時の完了条件

M33で本節の全3草稿要求をsource mapへ残し、10具体点の説明・数値・教材消費・画面証拠へ対応させる。
Black/exchangeは§28.6/28.7の分布/契約要求を維持する。
Ch30のtiming/quantoはsigned ratioの実際の給付と通貨単位、Ch31はshort rateのabsolute drift、Ch33はHJM/LMMのtenor/numeraire契約で別に受け入れる。
§28.8の局所補正だけで後続37節をacceptedに増やさない。

1. private helper最小契約とsource mapを確定。
2. 生密度・条件付き平均・同一給付・PSD/基底・非取引/absolute・state依存の教師を製品検査へ取り込む。
3. 原典式とsynthetic入力を教材で分け、C/符号/単位/観測条件を図の近くへ表示。
4. 原典本文/式/脚注/TN20のsource hashと結果digestを教材消費時も確認。
5. 誤りcontrolの拒否、対象suite、既受入領域のregression、browser/配布証跡/D1を本作業で実施。

MCでzero-hit/SE=0が生じても、数学的に決定的だと示せない給付を厳密0のPASSにしない（M31で確認済みの規約）。
一般のRN densityはpositive/true-martingale条件が必要。income、支払を跨ぐannuity、非取引riskの選び方を暗黙に扱わない。
原典本文・TN20の入力不足は今回見つかっていない。本節の印刷価格pinはそもそも存在しない。
市場較正・実測のλ/vol/C推定・多通貨担保・一般stochastic-vol価格エンジンは追加研究契約として残る。