(guide-models)=
# モデル地図：問いから道具へ進む

モデルの名前を覚える前に、何を動かし、何の支払いを求めたいかを決めます。株価を動かす BSM と、計算を近似する有限差分法は役割が違います。この地図は商品・確率モデル・数値手法・検証手順を区別して読み、同じ問いに使う道具を見渡すためのページです。

[用語と記号](glossary.md) ／ {ref}`章どうしのつながり <chapter-connections>`

## 地図の読み方

まず系統を選び、拡大・縮小やドラッグで位置を動かします。点をクリック・タップするとモデルカードへ進みます。名前の選択欄でも移動できます。JS が使えない場合も、下の早見表・関係表・すべてのカードを読めます。

矢印は、矢印の元から先へ次の関係を読みます。特殊な場合はパラメーター等を制限する向き、極限・近似は条件を満たして近づける向き、入力・較正は推定・評価に入力を渡す向きです。優劣や学習の前後を示す線ではありません。線のないカードにも独立した役割があり、数学的な関係を確認できたものだけを結んでいます。

```{raw} html
:file: model_map/runtime.html
```

```{raw} html
:file: model_map/figure.html
```

## 問いから選ぶ早見表

| 知りたいこと | 最初に開くカード | 選ぶときの分かれ目 |
|---|---|---|
| まず株式の権利へ値段を付けたい | [ブラック＝ショールズ＝マートン](#model-bsm)・[CRR 二項ツリー](#model-crr) | 満期だけの行使か、途中にも行使できるか |
| アメリカン・プットを評価したい | [CRR 二項ツリー](#model-crr)・[有限差分法と安定性](#model-fd)・[最小二乗 MC と行使方策](#model-lsm) | 状態の数と経路依存、行使日と精度の予算 |
| 平均やバリアを含む支払いを読みたい | [平均価格・平均行使価格オプション](#model-asian)・[バリア・オプション](#model-barrier)・[GBM モンテカルロ評価](#model-mc) | 観測日と、状態に残す履歴 |
| 現在のスマイルとモデルの動きを比べたい | [Dupire 局所ボラティリティ](#model-local-vol)・[Heston 確率ボラティリティ](#model-heston)・[SABR](#model-sabr)・[IV とスマイルの軸](#model-implied-vol) | 現在のバニラへの適合と将来の条件付き変動は別 |
| 金利の期間全体を動かしたい | [Hull–White 一因子](#model-hull-white)・[HJM](#model-hjm)・[LIBOR 市場モデル](#model-lmm) | 短期金利、瞬間フォワード、期間金利のどれを状態にするか |
| 支払通貨や時点が違う | [クオント調整](#model-quanto)・[支払時点の調整](#model-timing)・[クロスカレンシー・スワップ](#model-cross-currency) | 建値・支払日・基準資産を先に定める |
| 証券化で損失がどこへ届くか知りたい | [証券化の損失配分](#model-securitization)・[Vasicek 信用損失とコピュラ](#model-credit-copula)・[CDO・第 k デフォルトと相関](#model-cdo) | 決まった損失の配分と、その損失が起きる確率 |
| 取引相手と担保の影響を測りたい | [ハザード曲線](#model-hazard)・[単一名 CDS](#model-cds)・[エクスポージャと XVA](#model-xva) | 回収・依存・ネッティング・担保の遅れ |
| 将来の損失と変動を測りたい | [VaR と期待ショートフォール](#model-var-es)・[EWMA 分散・共分散](#model-ewma)・[GARCH 分散](#model-garch)・[FHS と EVT の裾](#model-tail-risk) | 予測期間、分布の裾と標本の情報時点 |
| 高価な価格器を速く近似したい | [誤差つきの教師データ](#model-teacher-data)・[価格サロゲートと DML](#model-pricing-surrogate)・[無裁定の事後検証](#model-hard-validation) | 教師の誤差・学習外入力・無裁定の検査 |
| SPX と VIX を一緒に考えたい | [経路依存ボラティリティ](#model-pdv)・[前方分散と rough Heston カーネル](#model-rough-kernel)・[SPX/VIX の共同目的関数](#model-joint-spx-vix) | 核の部品と完全な価格器・較正器を区別する |
| インフレや新しい契約へ進みたい | [Jarrow–Yildirim インフレモデル](#model-jarrow-yildirim)・[気温・度日とベーシス・リスク](#model-weather)・[再生可能電力 PPA](#model-ppa)・[撤退・拡張のリアル・オプション](#model-real-options) | 複製できるリスクと、別の評価原理が必要なリスク |

## 関係を、条件と一緒に読む

各関係はここで条件を確認できます。カード側にも行き先・戻り先を表示します。

(map-relation-1)=
### CRR 二項ツリー → ブラック＝ショールズ＝マートン

**極限・近似。** 同じ無配当のヨーロピアン契約で、金利 $r$・ボラ $\sigma$・満期 $T$ を固定し、$\Delta t=T/n$、$u=e^{\sigma\sqrt{\Delta t}}$、$d=u^{-1}$ として $n\to\infty$ とすると価格が BSM に近づきます。有限段数の価格が厳密に一致するという意味ではありません。 出典：GE §13.7（pp.300–302）、§13.appendix（pp.312–315）。

(map-relation-2)=
### GBM モンテカルロ評価 → ブラック＝ショールズ＝マートン

**極限・近似。** 無配当 GBM の厳密な終値 $S_T=S_0e^{(r-\sigma^2/2)T+\sigma W_T}$ を使い、独立標本数を増やすと、割引したヨーロピアン給付の標本平均が BSM 価格へ近づきます。離散化した経路を使う場合は刻みの誤差も別に残ります。 出典：GE §21.6（pp.489–495）。

(map-relation-3)=
### 有限差分法と安定性 → ブラック＝ショールズ＝マートン

**極限・近似。** 同じ BSM PDE、終端給付と整合する境界を使い、安定なスキームで時間・株価格子を細かくし、切り詰めた領域も適切に広げた極限です。$\Delta t,\Delta S\to0$ だけで誤った境界条件まで直るわけではありません。 出典：GE §21.8（pp.498–508）。

(map-relation-4)=
### 指数・通貨オプション → ブラック＝ショールズ＝マートン

**特殊な場合。** 連続配当利回り $q$ を用いる株価指数モデルで $q=0$ とすれば無配当 BSM になります。通貨の場合も、国内通貨建ての条件をそろえ、外国金利 $r_f=0$ とした場合の対応です。 出典：GE §17.3（pp.389–391）、§18.7（pp.408–409）。

(map-relation-5)=
### キャリーによる先渡価格 → Black の市場モデル

**入力・較正。** 一定の金利と連続配当利回りの下で $F_0=S_0e^{(r-q)T}$ を求め、同じ満期のフォワードに対する Black の式へ渡します。先物と先渡を同じ入力にするには、金利の確定性等の追加条件が必要です。 出典：GE §17.3（pp.389–391）、§18.7（pp.408–409）。

(map-relation-6)=
### 時間依存ボラティリティ → ブラック＝ショールズ＝マートン

**特殊な場合。** 確定的な $\sigma(t)$ を一定の $\sigma$ に制限すると、期間平均分散 $T^{-1}\int_0^T\sigma(t)^2dt$ も $\sigma^2$ になり、同じ契約の BSM 評価になります。 出典：GE §27.2（pp.646–649）。

(map-relation-7)=
### CEV → ブラック＝ショールズ＝マートン

**特殊な場合。** $dS=(r-q)Sdt+\sigma S^\beta dW$ という規約で $\beta=1$ とすると GBM です。同じ配当条件の BSM を使い、無配当カードとの比較では $q=0$ にします。 出典：GE §27.1（pp.641–646）。

(map-relation-8)=
### Merton ジャンプ拡散 → ブラック＝ショールズ＝マートン

**特殊な場合。** ジャンプ到来強度 $\lambda=0$ とするとジャンプとそのドリフト補正が消え、連続拡散の BSM に戻ります。残る拡散ボラと配当条件もそろえます。 出典：GE §27.1（pp.641–646）。

(map-relation-9)=
### バリアンス・ガンマ → ブラック＝ショールズ＝マートン

**極限・近似。** ガンマ時計の分散率 $\nu\to0$ とすると時計が確定的になり、価格のドリフト補正を含む VG 過程は GBM へ近づきます。残るブラウン成分のボラとキャリーをそろえる極限です。 出典：GE §27.1（pp.641–646）。

(map-relation-10)=
### Heston 確率ボラティリティ → 時間依存ボラティリティ

**特殊な場合。** Heston の分散 SDE $dv=\kappa(\theta-v)dt+\xi\sqrt v,dW$ で $\xi=0$ とすると、$v(t)=\theta+(v_0-\theta)e^{-\kappa t}$ が確定的になります。状態としてのランダムな分散を除いた特殊化です。 出典：[Heston（1993）§1、pp.328–329、式(1)〜(4)](https://finance.martinsewell.com/stylized-facts/volatility/Heston1993.pdf)。

(map-relation-11)=
### Heston 確率ボラティリティ → ブラック＝ショールズ＝マートン

**特殊な場合。** 分散のボラ $\xi=0$ に加え、初期分散 $v_0=\theta=\sigma^2$ とすると分散は一定です。同じ金利・配当・給付なら BSM の過程になります。これはモデルの式の特殊化で、すべての Heston 実装が境界入力を受け付けるという意味ではありません。 出典：[Heston（1993）§1、pp.328–329、式(1)〜(4)](https://finance.martinsewell.com/stylized-facts/volatility/Heston1993.pdf)。

(map-relation-12)=
### IV とスマイルの軸 → Dupire 局所ボラティリティ

**入力・較正。** 同じ建値と割引で IV を滑らかなコール価格面 $C(K,T)$ へ直し、Dupire の式へ渡します。$\partial_{KK}C>0$ 等の条件が必要です。長い式を読みやすくするため、この地図では分子を $A$、分母を $B$ として次のように分けます。$A$ の単位は通貨／年、$B$ は通貨で、比は年の逆数の分散率になります。 出典：GE §27.3（pp.649–650）。

$$
\begin{aligned}
\sigma_{\rm loc}^2(K,T)&=\frac{A(K,T)}{B(K,T)},\\
A(K,T)&=\partial_TC+qC\\
&\quad +(r-q)K\partial_KC,\\
B(K,T)&=\tfrac12 K^2\partial_{KK}C.
\end{aligned}
$$

(map-relation-13)=
### Dupire 局所ボラティリティ → ブラック＝ショールズ＝マートン

**特殊な場合。** 局所ボラを全時刻・全価格で $\sigma_{\rm loc}(t,S)=\sigma$ に固定すると、同じキャリーの GBM になります。現在の一つの点だけでボラが同じでも、この条件は満たしません。 出典：GE §27.3（pp.649–650）。

(map-relation-14)=
### IV とスマイルの軸 → 価格から読む確率密度

**入力・較正。** 一定の金利で、滑らかなヨーロピアン価格面を使うと、終値の Q 密度は $g(K)=e^{rT}\partial^2C/\partial K^2$ です。IV をそのまま密度と呼ばず、価格へ戻して行使価格方向に微分します。 出典：GE §20.appendix（pp.467–469）。

(map-relation-15)=
### SSVI の総分散面 → IV とスマイルの軸

**入力・較正。** 総分散 $w(k,T)$ から $T>0$ で $\sigma_{\rm IV}(k,T)=\sqrt{w(k,T)/T}$ として IV を得ます。静的無裁定には SSVI のパラメーターと満期方向の条件を別に確認します。 出典：[Gatheral–Jacquier、§1 Notations・§4（2013年改訂版、2014年刊行）](https://arxiv.org/pdf/1204.0646)。

(map-relation-16)=
### GARCH 分散 → EWMA 分散・共分散

**特殊な場合。** GARCH の $\omega+\alpha r_{t-1}^2+\beta v_{t-1}$ に対して、$\omega=0,\alpha=1-\lambda,\beta=\lambda$ と置けば EWMA の更新です。$\alpha+\beta=1$ の境界なので、定常 GARCH の長期分散の式は流用しません。 出典：GE §23.2（pp.544–546）、§23.3（pp.546–547）。

(map-relation-17)=
### EWMA 分散・共分散 → 古典的な変動予測

**入力・較正。** 観測済みの二乗収益率で $v_{t+1}=\lambda v_t+(1-\lambda)r_t^2$ を更新し、同じ観測間隔の翌期分散予測へ使います。リターン、日次/年率、情報時点をそろえる条件です。 出典：GE §23.2（pp.544–546）、§23.3（pp.546–547）。

(map-relation-18)=
### Hull–White 一因子 → Ho–Lee

**特殊な場合。** $dr=[\theta(t)-ar]dt+\sigma dW$ で $a=0$ とすれば平均回帰項が消えます。同じ初期曲線へ合わせる $\theta(t)$ を選び直したガウス型が Ho–Lee です。正の $a$ 用の式へ無条件にゼロを代入する手順とは区別します。 出典：GE §31.2（pp.721–726）、§32.1（pp.732–736）、§32.2（pp.736–737）。

(map-relation-19)=
### Hull–White 一因子 → Vasicek 短期金利

**特殊な場合。** $a,\sigma$ が一定で、時刻依存項を $\theta(t)=ab$ という定数に制限すれば $dr=a(b-r)dt+\sigma dW$ となります。そのパラメーターが生む初期曲線に一致する場合に限る比較です。 出典：GE §31.2（pp.721–726）、§32.1（pp.732–736）、§32.2（pp.736–737）。

(map-relation-20)=
### HJM → Hull–White 一因子

**特殊な場合。** 一因子で瞬間フォワードのボラを $\sigma_f(t,T)=\sigma e^{-a(T-t)}$ としたガウス HJM は、同じ初期曲線の Hull–White と対応します。任意の HJM のボラが一因子短期金利へ縮約できるという意味ではありません。 出典：GE §33.1（pp.755–758）、GE §31.2（pp.721–726）、§32.1（pp.732–736）、§32.2（pp.736–737）。

(map-relation-21)=
### 債券とゼロ曲線 → Hull–White 一因子

**入力・較正。** 初期の割引因子 $P(0,T)$、その満期微分と金利の係数から時刻依存項を決め、モデルの $P_{\rm model}(0,T)=P(0,T)$ を満たすようにします。曲線適合とオプションのボラ較正は別です。 出典：GE §31.2（pp.721–726）、§32.1（pp.732–736）、§32.2（pp.736–737）。

(map-relation-22)=
### 債券とゼロ曲線 → LIBOR 市場モデル

**入力・較正。** 単一曲線で $L_i(0)=[P(0,T_i)/P(0,T_{i+1})-1]/\delta_i$ を初期期間金利へ渡します。$\delta_i$ は年分数です。複数曲線では同じ式を割引曲線だけから使いません。 出典：GE §33.2（pp.758–768）。

(map-relation-23)=
### ハザード曲線 → 単一名 CDS

**入力・較正。** ハザード率から $Q(\tau>t)=\exp[-\int_0^t\lambda(s)ds]$ を求め、回収・未払利息の条件とともに CDS の両レッグへ渡します。市場価格へ使う確率と履歴の PD を区別します。 出典：GE §24.4（pp.564–566）、§25.2（pp.591–595）、§25.10（pp.601–608）。

(map-relation-24)=
### Vasicek 信用損失とコピュラ → CDO・第 k デフォルトと相関

**入力・較正。** 一因子ガウス型で $p_i(z)=N((N^{-1}(\rm PD_i)-\sqrt{\rho_i}z)/\sqrt{1-\rho_i})$ という条件付き確率を作り、損失状態とトランシェの受払いを平均します。正の loading と指定した期間・回収の下の関係で、相関だけから価格が決まるわけではありません。 出典：GE §24.4（pp.564–566）、§25.2（pp.591–595）、§25.10（pp.601–608）。

(map-relation-25)=
### 証券化の損失配分 → CDO・第 k デフォルトと相関

**入力・較正。** 原資産損失率 $L$ と attachment $A$、detachment $D>A$ から、層の損失割合を $\min(\max(L-A,0),D-A)/(D-A)$ で作れます。CDO の期待損失には、この配分に加えて $L$ の分布と支払時点が必要です。 出典：GE §8.1（pp.201–205）、§25.8（pp.599–601）、§25.10（pp.601–608）。

(map-relation-26)=
### 誤差つきの教師データ → 価格サロゲートと DML

**入力・較正。** 同じ入力 $x_i$ の価格ラベル $y_i$ を二乗誤差 $\sum_i(v_\theta(x_i)-y_i)^2$ へ渡し、DML では入力微分のラベルとの二乗誤差も加えます。教師の誤差・単位の正規化・学習と評価の分離が前提です。 出典：[Huge–Savine（2020）§1・付録1](https://arxiv.org/pdf/2005.02347)。

(map-relation-27)=
### ブラック＝ショールズ＝マートン → 誤差つきの教師データ

**入力・較正。** 同じ $S,K,r,\sigma,T$ と契約条件で得た解析価格 $C_{\rm BSM}$ を、教師の価格ラベルとして使います。解析価格のある問題でも、近似器の学習誤差は別に測ります。 出典：[Huge–Savine（2020）§1・付録1](https://arxiv.org/pdf/2005.02347)。

(model-cards)=
## モデルカード

索引の対象 178 行を 135 枚へ対応づけています。同じモデルの公開実装・非公開教材・図の生成部品は同じカードにまとめ、異なる状態や契約は区別しました。実装名・テストの範囲は各カードから MODEL_INDEX の該当節へ進めます。§15 の基盤と RB-F* の研究行は対象に含めていません。

合成データでの恒等式・独立比較・再現性の確認と、市場での性能は別です。各章のガイドは現在 Ch8・Ch13 があり、残りは追加後にリンクします。

## BSM・二項ツリー・数値手法

同じ支払いを作るという評価の原理から、閉じた式、格子、標本による期待値へ進みます。商品を表すカードと、その商品を解く手法のカードを読み分けてください。

(model-bsm)=
### ブラック＝ショールズ＝マートン

Black–Scholes–Merton（BSM）。

**何を表すか：** 株価 S（通貨／株）を連続的に動かし、コール・プットの価値（通貨）を求めます。

**仮定と限界：** 一定の金利・ボラティリティ、連続売買等を仮定します。ジャンプや取引費用の影響はこのままでは表せません。

**解き方・手順：** 複製から得る PDE の解析解とグリークスを使います。

**使う場面：** 標準的なヨーロピアン契約の基準価格。

**実装と検証の範囲：** 価格・パリティ・グリークスと原典の例を検証。市場のスマイルへの適合を認定するものではありません。

**読む場所：** Hull： §15.6（pp.348–351）、§15.7（pp.351–352）、§15.8（pp.352–355）。<a href="../15_bsm_ch15.html#bsm">Book：7. §15.8 BSM 公式の実装</a> ／ <a href="../../../../../MODEL_INDEX.md#1-core-pricing-black-scholes-trees-monte-carlo">実装・テスト：MODEL_INDEX 1</a> ／ <a href="../../../../../MODEL_INDEX.md#p4-logic-first-private-models">実装・テスト：MODEL_INDEX P4 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch15.html#section-15-6">補足教材 §15.6</a>。

**関係：** [CRR 二項ツリー](#model-crr) から（[条件・出典](#map-relation-1)：極限・近似）。[GBM モンテカルロ評価](#model-mc) から（[条件・出典](#map-relation-2)：極限・近似）。[有限差分法と安定性](#model-fd) から（[条件・出典](#map-relation-3)：極限・近似）。[指数・通貨オプション](#model-index-currency) から（[条件・出典](#map-relation-4)：特殊な場合）。[時間依存ボラティリティ](#model-time-vol) から（[条件・出典](#map-relation-6)：特殊な場合）。[CEV](#model-cev) から（[条件・出典](#map-relation-7)：特殊な場合）。[Merton ジャンプ拡散](#model-merton-jump) から（[条件・出典](#map-relation-8)：特殊な場合）。[バリアンス・ガンマ](#model-variance-gamma) から（[条件・出典](#map-relation-9)：極限・近似）。[Heston 確率ボラティリティ](#model-heston) から（[条件・出典](#map-relation-11)：特殊な場合）。[Dupire 局所ボラティリティ](#model-local-vol) から（[条件・出典](#map-relation-13)：特殊な場合）。[誤差つきの教師データ](#model-teacher-data) へ（[条件・出典](#map-relation-27)：入力・較正）。

(model-cash-dividends)=
### 既知の現金配当

Known cash dividends and exercise conditions。

**何を表すか：** 株価と配当金（ともに通貨）、配当日と行使日を分けます。

**仮定と限界：** 配当の時点と額が既知です。配当利回り一定のモデルと同じ式にはなりません。

**解き方・手順：** 配当の現在価値を引く近似、Black の米国型コール近似、格子や上下限で比べます。

**使う場面：** 配当をまたぐ株式オプションの行使判断。

**実装と検証の範囲：** 原典例・パリティ・条件付き行使と独立な格子/PDE比較。現金配当の扱いごとに近似と厳密な会計を区別します。

**読む場所：** Hull： §11.7（pp.262–263）、§15.12（pp.360–363）。<a href="../15_bsm_ch15.html#id19">Book：11. §15.12 配当</a> ／ <a href="../../../../../MODEL_INDEX.md#1-core-pricing-black-scholes-trees-monte-carlo">実装・テスト：MODEL_INDEX 1</a> ／ <a href="../../../../../MODEL_INDEX.md#p4-logic-first-private-models">実装・テスト：MODEL_INDEX P4 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch11.html#section-11-7">補足教材 §11.7</a>。

(model-crr)=
### CRR 二項ツリー

Cox–Ross–Rubinstein binomial tree（CRR）。

**何を表すか：** 時刻ごとの株価（通貨／株）とノードの契約価値（通貨）を動かします。

**仮定と限界：** 上下倍率と金利で無裁定確率を作れ、必要な状態がツリーに残ることが条件です。

**解き方・手順：** 上下の枝で支払いを複製し、後退帰納で価格・行使判断・デルタを求めます。

**使う場面：** アメリカンの早期行使、BSM との収束比較。

**実装と検証の範囲：** 確率の裁定ガード、原典の複製・行使と独立な状態列挙/PDEを検証。有限段数の誤差は残ります。

**読む場所：** Hull： §13.1（pp.288–292）、§13.7（pp.300–302）、§21.1（pp.470–477）。<a href="../01_foundations.html#id1">Book：1. 1ステップ二項ツリーとリスク中立評価（§13.1–13.2）</a> ／ <a href="../../../../../MODEL_INDEX.md#1-core-pricing-black-scholes-trees-monte-carlo">実装・テスト：MODEL_INDEX 1</a> ／ <a href="../../../../../MODEL_INDEX.md#p4-logic-first-private-models">実装・テスト：MODEL_INDEX P4 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch13.html#section-13-1">補足教材 §13.1</a>。

[Ch13のガイド](ch13.md)から説明を読み直せます。

**関係：** [ブラック＝ショールズ＝マートン](#model-bsm) へ（[条件・出典](#map-relation-1)：極限・近似）。

(model-mc)=
### GBM モンテカルロ評価

Geometric Brownian motion Monte Carlo pricing（MC）。

**何を表すか：** 株価経路（通貨／株）から各経路の支払額（通貨）を作ります。

**仮定と限界：** リスク中立の過程と契約の観測日を指定します。標本誤差と経路離散化誤差は別です。

**解き方・手順：** 支払いの標本平均を割り引き、標準誤差を添えます。

**使う場面：** 経路依存商品や解析式のない期待値。

**実装と検証の範囲：** GBM のモーメント・BSM・与えた乱数の再生と分散減少を検証。乱数を増やしても誤った過程は直りません。

**読む場所：** Hull： §21.6（pp.489–495）。<a href="../06_numerical.html#ch-21eq-21-16">Book：3. モンテカルロ法（Ch.21、eq 21.16）</a> ／ <a href="../../../../../MODEL_INDEX.md#1-core-pricing-black-scholes-trees-monte-carlo">実装・テスト：MODEL_INDEX 1</a> ／ <a href="../../../../../MODEL_INDEX.md#p4-logic-first-private-models">実装・テスト：MODEL_INDEX P4 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch21.html#section-21-6">補足教材 §21.6</a>。

**関係：** [ブラック＝ショールズ＝マートン](#model-bsm) へ（[条件・出典](#map-relation-2)：極限・近似）。

(model-lsm)=
### 最小二乗 MC と行使方策

Least-squares Monte Carlo and exercise-boundary parameterization（LSM）。

**何を表すか：** 行使日に観測する状態（株価等）と継続価値（通貨）を扱います。

**仮定と限界：** 回帰の基底、状態、行使日を指定します。学習した経路で方策の良さを評価すると上振れしえます。

**解き方・手順：** 回帰による継続価値または境界を学習し、別の経路で方策を評価します。

**使う場面：** 多因子・経路依存契約の早期行使。

**実装と検証の範囲：** 原典経路、独立求積、ツリー/PDEとの比較と fit/fresh 分離を検証。連続行使は離散日程からの近似です。

**読む場所：** Hull： §27.8（pp.660–665）。<a href="../06_numerical.html#id39">Book：14. モンテカルロ法とアメリカン・オプション（§27.8）</a> ／ <a href="../../../../../MODEL_INDEX.md#1-core-pricing-black-scholes-trees-monte-carlo">実装・テスト：MODEL_INDEX 1</a> ／ <a href="../../../../../MODEL_INDEX.md#2-volatility--smile">実装・テスト：MODEL_INDEX 2</a>。

(model-fd)=
### 有限差分法と安定性

Finite differences for option pricing（FD・PDE）。

**何を表すか：** 時刻と株価の格子上の価格（通貨）を求めます。

**仮定と限界：** PDE の係数・終端条件・境界条件が必要です。陽解法では刻みの安定性条件も必要です。

**解き方・手順：** 陽解法、陰解法、Crank–Nicolson 等で微分を差に置き換えます。

**使う場面：** バニラ、早期行使、ほかの数値法との独立比較。

**実装と検証の範囲：** 解析価格・独立格子・原典の不安定例を検証。境界や格子を変えた収束の確認が必要です。

**読む場所：** Hull： §21.8（pp.498–508）。<a href="../06_numerical.html#id3">Book：5. 有限差分法（Ch.21）</a> ／ <a href="../../../../../MODEL_INDEX.md#1-core-pricing-black-scholes-trees-monte-carlo">実装・テスト：MODEL_INDEX 1</a> ／ <a href="../../../../../MODEL_INDEX.md#4-numerical-methods-variance-reduction-qmc-aad">実装・テスト：MODEL_INDEX 4</a> ／ <a href="../../../../../MODEL_INDEX.md#p4-logic-first-private-models">実装・テスト：MODEL_INDEX P4 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch21.html#section-21-8">補足教材 §21.8</a>。

**関係：** [ブラック＝ショールズ＝マートン](#model-bsm) へ（[条件・出典](#map-relation-3)：極限・近似）。

(model-strategies)=
### オプション戦略と複製

Option strategies and payoff replication。

**何を表すか：** 各オプションの受払額と購入・売却代金（通貨）を合算します。

**仮定と限界：** 同じ満期か、残存価値を別に評価すべきかを区別します。

**解き方・手順：** 区分的なペイオフ、資金の会計、必要なら密度積分/PDEで確認します。

**使う場面：** スプレッド、ストラドル、元本保護商品の仕組み。

**実装と検証の範囲：** 原典例と独立な損益・会計・複製を検証。満期の図だけで途中の損益を保証しません。

**読む場所：** Hull： §12.1（pp.268–270）。<a href="../02_options_basics.html#ch-12">Book：6. トレーディング戦略の全体像（Ch.12）</a> ／ <a href="../../../../../MODEL_INDEX.md#1-core-pricing-black-scholes-trees-monte-carlo">実装・テスト：MODEL_INDEX 1</a> ／ <a href="../../../../../MODEL_INDEX.md#p4-logic-first-private-models">実装・テスト：MODEL_INDEX P4 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch12.html#section-12-1">補足教材 §12.1</a>。

(model-delta-hedge)=
### デルタ・ヘッジとグリークス

Delta hedging and Greek exposures。

**何を表すか：** 株価、オプション価格、保有株数、現金（通貨）を時点ごとに追います。

**仮定と限界：** モデルの感応度で離散的に売買します。連続時間での複製と実際の取引間隔は異なります。

**解き方・手順：** 解析感応度・差分・自己資金の会計で、ヘッジ損益を再生します。

**使う場面：** 価格変化の説明と動的ヘッジ。

**実装と検証の範囲：** グリークスの単位と独立な受払/PDEを検証。原典の特定のランダム経路をすべて再現したとは扱いません。

**読む場所：** Hull： §19.4（pp.421–427）。<a href="../03_greeks.html#id2">Book：4. 動的デルタヘッジ（§19.4）</a> ／ <a href="../../../../../MODEL_INDEX.md#1-core-pricing-black-scholes-trees-monte-carlo">実装・テスト：MODEL_INDEX 1</a> ／ <a href="../../../../../MODEL_INDEX.md#p4-logic-first-private-models">実装・テスト：MODEL_INDEX P4 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch19.html#section-19-4">補足教材 §19.4</a>。

(model-brownian)=
### ウィーナー過程と伊藤の補題

Wiener processes and Itô calculus。

**何を表すか：** ブラウン運動（時間の平方根の単位）と、その関数の変化を扱います。

**仮定と限界：** 独立な正規増分と連続経路を仮定します。ジャンプ過程には同じ微分則をそのまま使えません。

**解き方・手順：** 経路・二次変分・伊藤補正を計算し、対数正規分布へ進みます。

**使う場面：** 株価 SDE と複製 PDE の準備。

**実装と検証の範囲：** 独立な算術・正規積分・スペクトル比較を含む教材。fBM の実装もありますが通常の伊藤過程と同一視しません。

**読む場所：** Hull の前提： §14.2（pp.317–322）、§14.6（pp.327–328）。<a href="../13_stochastic_calculus.html#id2">Book：1. ブラウン運動と二次変分</a> ／ <a href="../../../../../MODEL_INDEX.md#3-stochastic-calculus--sde">実装・テスト：MODEL_INDEX 3</a> ／ <a href="../../../../../MODEL_INDEX.md#p4-logic-first-private-models">実装・テスト：MODEL_INDEX P4 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch14.html#section-14-2">補足教材 §14.2</a>。

(model-euler)=
### オイラー＝丸山法

Euler–Maruyama discretization。

**何を表すか：** SDE の状態変数を時間の格子上に近似します。単位は元の状態と同じです。

**仮定と限界：** 小さな時間刻みを使う近似です。正値性等が離散化で崩れるモデルもあります。

**解き方・手順：** ドリフトとブラウン増分を各刻みで足します。

**使う場面：** 解析的に経路を作れない SDE の基礎。

**実装と検証の範囲：** GBM の厳密遷移とのモーメント比較。すべての SDE に同じ誤差保証を付けたものではありません。

**読む場所：** Hull の前提： §21.6（pp.489–495）。<a href="../13_stochastic_calculus.html#id5">Book：4. 確率微分方程式と数値解法</a> ／ <a href="../../../../../MODEL_INDEX.md#3-stochastic-calculus--sde">実装・テスト：MODEL_INDEX 3</a> ／ <a href="../../../../../report/site/chapters/ch21.html#section-21-6">補足教材 §21.6</a>。

(model-girsanov)=
### 確率測度の変更

Girsanov change of measure。

**何を表すか：** 同じ状態経路への確率の重みとドリフトを変えます。重みは無次元です。

**仮定と限界：** 密度が適切な確率を定義する条件が必要です。価格予測の確率と評価の確率を混ぜません。

**解き方・手順：** 密度比とブラウン増分の変更を計算し、同じ期待値を別の測度で比較します。

**使う場面：** P/Q の切替えとニュメレール変更。

**実装と検証の範囲：** 符号つき共分散、独立な正規傾斜と MC を検証。単にドリフトだけを書き換える操作ではありません。

**読む場所：** Hull： §28.8（pp.682–684）。<a href="../13_stochastic_calculus.html#girsanov">Book：5. Girsanov の定理 — 測度変換とリスク中立評価</a> ／ <a href="../../../../../MODEL_INDEX.md#3-stochastic-calculus--sde">実装・テスト：MODEL_INDEX 3</a> ／ <a href="../../../../../MODEL_INDEX.md#p3-logic-first-private-models">実装・テスト：MODEL_INDEX P3 logic-first private models</a>。

(model-variance-reduction)=
### 分散減少と準 MC

Control variates, importance sampling and Sobol QMC。

**何を表すか：** 同じ期待値を求める推定量と標本点を変えます。推定値の単位は価格です。

**仮定と限界：** コントロールの平均や密度比を正しく与えます。QMC の点列を独立標本とみなした誤差計算はしません。

**解き方・手順：** 既知平均との差、重点的な標本と重み、低食い違い点列を使います。

**使う場面：** 高価な経路評価の精度改善。

**実装と検証の範囲：** 分散の減少や誤差の推移を合成例で検証。あらゆる契約で速いという主張ではありません。

**読む場所：** Hull の前提： §21.7（pp.495–498）。<a href="../15_advanced_numerics.html#id2">Book：1. モンテカルロ誤差と分散減少</a> ／ <a href="../../../../../MODEL_INDEX.md#4-numerical-methods-variance-reduction-qmc-aad">実装・テスト：MODEL_INDEX 4</a> ／ <a href="../../../../../report/site/chapters/ch21.html#section-21-7">補足教材 §21.7</a>。

(model-mc-greeks)=
### MC のグリークス

Pathwise, likelihood-ratio and bump sensitivities。

**何を表すか：** 価格の入力に対する微分を推定します。単位は各グリークスに従います。

**仮定と限界：** 経路の滑らかさや密度の微分可能性等、手法ごとの条件が必要です。

**解き方・手順：** 経路微分、尤度比、有限差分を解析値や自動微分と比べます。

**使う場面：** シミュレーションによるヘッジ量の計算。

**実装と検証の範囲：** vol15 は AAD tape を持ちません。自動微分と直接ヘッドの整合性も、モデルの価格精度とは別に検証します。

**読む場所：** Hull の前提： §21.6（pp.489–495）。<a href="../15_advanced_numerics.html#pathwise-lr-aad">Book：5. グリークス：pathwise / LR / AAD</a> ／ <a href="../../../../../MODEL_INDEX.md#4-numerical-methods-variance-reduction-qmc-aad">実装・テスト：MODEL_INDEX 4</a> ／ <a href="../../../../../MODEL_INDEX.md#8-ml-surrogates--differential-machine-learning">実装・テスト：MODEL_INDEX 8</a> ／ <a href="../../../../../report/site/chapters/ch21.html#section-21-6">補足教材 §21.6</a>。

(model-contract-cashflows)=
### 契約の受払いと会計

Contract payoffs and cash-flow accounting。

**何を表すか：** 契約の数量、通貨、時刻ごとの受払額を扱います。

**仮定と限界：** 契約倍率、プレミアム、決済方法を先に指定します。価格モデルがなくても受払いは定義できます。

**解き方・手順：** 受払列挙と独立な十進数会計で損益を確認します。

**使う場面：** 先渡・オプション・ヘッジの最初の整理。

**実装と検証の範囲：** 原典の金額と契約条件を固定した非公開教材。法的な契約条項の網羅ではありません。

**読む場所：** Hull： §1.3（pp.28–30）、§10.1（pp.227–229）。<a href="../12_qualitative_summary.html#id2">Book：§1.3 フォワード契約</a> ／ <a href="../../../../../MODEL_INDEX.md#p3-logic-first-private-models">実装・テスト：MODEL_INDEX P3 logic-first private models</a> ／ <a href="../../../../../MODEL_INDEX.md#p4-logic-first-private-models">実装・テスト：MODEL_INDEX P4 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch01.html#section-1-3">補足教材 §1.3</a>。

(model-employee-options)=
### 従業員オプション

Employee stock options。

**何を表すか：** 株価、勤続・権利確定・行使の状態と報酬価値（通貨）を追います。

**仮定と限界：** 譲渡制約や退職時の扱いを設定します。市場のアメリカンと同じ行使主体ではありません。

**解き方・手順：** 期待寿命近似と従業員向け格子を会計・状態列挙で比べます。

**使う場面：** 報酬としてのオプション評価。

**実装と検証の範囲：** 原典値と独立な会計・密度・経路を検証。特定企業の付与価値を認定するものではありません。

**読む場所：** Hull： §16.1（pp.371–372）、§16.4（pp.375–379）。<a href="../12_qualitative_summary.html#eso-ch-16">Book：3. 従業員ストックオプション（ESO, Ch.16）</a> ／ <a href="../../../../../MODEL_INDEX.md#p4-logic-first-private-models">実装・テスト：MODEL_INDEX P4 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch16.html#section-16-1">補足教材 §16.1</a>。

(model-index-currency)=
### 指数・通貨オプション

Options on indices and currencies。

**何を表すか：** 指数ポイントまたは為替レート（国内通貨／外国通貨）を状態にします。

**仮定と限界：** 配当利回りまたは外国金利を保有利益として指定します。通貨の向きを逆転すると条件も変わります。

**解き方・手順：** キャリーを変えた BSM・ツリーと複製会計を使います。

**使う場面：** 指数保険や通貨ヘッジ。

**実装と検証の範囲：** 独立な会計・求積・ツリー/PDEを比較。株価モデルとの対応は同じ建値と金利の下で読みます。

**読む場所：** Hull： §17.1（pp.384–386）、§17.3（pp.389–391）。<a href="../02_options_basics.html#id8">Book：7. 株価指数オプションとポートフォリオ保険（§17.1–17.4）</a> ／ <a href="../../../../../MODEL_INDEX.md#p4-logic-first-private-models">実装・テスト：MODEL_INDEX P4 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch17.html#section-17-1">補足教材 §17.1</a>。

**関係：** [ブラック＝ショールズ＝マートン](#model-bsm) へ（[条件・出典](#map-relation-4)：特殊な場合）。

(model-convertible)=
### デフォルト可能な転換社債ツリー

Defaultable convertible bond tree。

**何を表すか：** 株価（通貨／株）、転換比率、社債価値と回収額（通貨）を状態にします。

**仮定と限界：** 転換・償還・デフォルト時の契約条件を固定します。株式オプション単体のツリーでは足りません。

**解き方・手順：** 株価の枝とデフォルト枝を含めて後退帰納します。

**使う場面：** 信用と株式の両方に依存する転換社債。

**実装と検証の範囲：** 原典ノード、独立な再帰、無デフォルト時の分解を検証。

**読む場所：** Hull： §27.4（pp.650–653）。<a href="../06_numerical.html#id14">Book：10. 転換社債（§27.4）</a> ／ <a href="../../../../../MODEL_INDEX.md#2-volatility--smile">実装・テスト：MODEL_INDEX 2</a>。

(model-asian)=
### 平均価格・平均行使価格オプション

Asian options and path-dependent trees。

**何を表すか：** 株価と、それまでの平均（ともに通貨／株）を状態に加えます。

**仮定と限界：** 算術平均と幾何平均、観測日、既観測分を指定します。平均を落とすと経路依存性を失います。

**解き方・手順：** 拡張ツリー、モーメント一致近似、求積・コントロールつき MC で比べます。

**使う場面：** 平均を使うアジアン契約。

**実装と検証の範囲：** 原典例と独立モーメント・経路を検証。算術平均の対数正規近似には上下両方向の誤差があり、厳密解ではありません。

**読む場所：** Hull： §26.13（pp.626–627）、§27.5（pp.653–656）。<a href="../10_exotics.html#id21">Book：4.3 アジアン・オプション（§26.13）</a> ／ <a href="../../../../../MODEL_INDEX.md#2-volatility--smile">実装・テスト：MODEL_INDEX 2</a> ／ <a href="../../../../../MODEL_INDEX.md#7-exotics--martingales">実装・テスト：MODEL_INDEX 7</a>。

(model-barrier)=
### バリア・オプション

Barrier options and barrier-aware trees。

**何を表すか：** 株価とバリアへの到達履歴を扱います。バリアの単位は株価と同じです。

**仮定と限界：** 連続監視か離散監視かを明記します。格子上だけの到達判定には誤差が生じます。

**解き方・手順：** 解析式、二項・三項ツリー、補間、PDE、監視間隔の補正を比べます。

**使う場面：** ノックイン・ノックアウト契約。

**実装と検証の範囲：** in/out 恒等式、独立ブリッジ積分、格子収束を検証。バリア近傍の不適切な設定は拒否します。

**読む場所：** Hull： §26.9（pp.620–622）、§27.6（pp.656–658）。<a href="../10_exotics.html#ge-pp-620622">Book：3. バリア・オプション（§26.9、GE pp.620–622）</a> ／ <a href="../../../../../MODEL_INDEX.md#2-volatility--smile">実装・テスト：MODEL_INDEX 2</a> ／ <a href="../../../../../MODEL_INDEX.md#7-exotics--martingales">実装・テスト：MODEL_INDEX 7</a>。

(model-two-asset)=
### 二資産のツリー

Two-asset lattices。

**何を表すか：** 二つの資産価格（各々の通貨建値）と相関を状態にします。

**仮定と限界：** 相関と枝の確率が整合し、支払いに必要な二資産を残すことが条件です。

**解き方・手順：** 多次元の状態格子から後退帰納し、交換オプション等と比較します。

**使う場面：** 二資産の最大値や交換の権利。

**実装と検証の範囲：** 原典格子、対数モーメント、独立積分と縮約したツリー/PDEを比較。

**読む場所：** Hull： §27.7（pp.658–661）。<a href="../06_numerical.html#id34">Book：13. 相関のある二資産のオプション（§27.7）</a> ／ <a href="../../../../../MODEL_INDEX.md#2-volatility--smile">実装・テスト：MODEL_INDEX 2</a>。

(model-digital)=
### バイナリ・オプション

Digital or cash-or-nothing options。

**何を表すか：** 株価と行使条件の成立を扱い、条件付きの一定金額（通貨）を払います。

**仮定と限界：** 境界での支払いの取り決めを指定します。狭いスプレッドによる近似は境界に敏感です。

**解き方・手順：** 対数正規確率またはバニラ価格の行使価格微分で評価します。

**使う場面：** 条件付き支払い、ギャップ等の分解。

**実装と検証の範囲：** 解析価格と独立な分布積分・複製を検証。

**読む場所：** Hull： §26.10（pp.622–623）。<a href="../10_exotics.html#id1">Book：2. バイナリ・オプション（§26.10）</a> ／ <a href="../../../../../MODEL_INDEX.md#7-exotics--martingales">実装・テスト：MODEL_INDEX 7</a>。

(model-lookback)=
### ルックバック・オプション

Lookback options。

**何を表すか：** 株価と、過去の最高値または最安値（同じ建値単位）を使います。

**仮定と限界：** 観測履歴と連続・離散 fixing を指定します。開始後の最高値を取り直してはいけません。

**解き方・手順：** 解析式、極値分布の積分、経路 MC を比べます。

**使う場面：** 過去の極値を参照する契約。

**実装と検証の範囲：** 原典例・独立な極値積分・パリティを確認。監視間隔の差は別に扱います。

**読む場所：** Hull： §26.11（pp.623–625）。<a href="../10_exotics.html#id9">Book：4.1 ルックバック・オプション（§26.11）</a> ／ <a href="../../../../../MODEL_INDEX.md#7-exotics--martingales">実装・テスト：MODEL_INDEX 7</a>。

(model-basket)=
### 正のバスケットの近似

Positive-basket moment matching。

**何を表すか：** 複数資産の加重合計（通貨）と共分散を扱います。

**仮定と限界：** 正のバスケットを対数正規分布で近似します。モーメント一致だけでは裾全体は一致しません。

**解き方・手順：** 平均と二次モーメントから Black 型の近似価格を作ります。

**使う場面：** 複数資産のバスケット・オプション。

**実装と検証の範囲：** 単一資産等の極限と独立条件付き積分/MCを比較。近似残差を精度保証と取り違えません。

**読む場所：** Hull： §26.15（pp.628–629）。<a href="../10_exotics.html#ge-pp-628629">Book：4.5 レインボーとバスケット（§26.15、GE pp.628–629）</a> ／ <a href="../../../../../MODEL_INDEX.md#7-exotics--martingales">実装・テスト：MODEL_INDEX 7</a>。

(model-shout)=
### 一回シャウトする権利

Single-shout option。

**何を表すか：** 株価と、一度だけ確定できる最低支払額（通貨）を扱います。

**仮定と限界：** 宣言回数と行使日を固定します。有限日程は連続宣言の近似です。

**解き方・手順：** 宣言しない継続価値と、宣言後の価値をツリーで比較します。

**使う場面：** 途中で利益水準を確保する契約。

**実装と検証の範囲：** 原典のコールと独立拡張のプットを、別の価格・実ノード境界で検証します。

**読む場所：** Hull： §26.12（pp.625–626）。<a href="../10_exotics.html#id15">Book：4.2 シャウト・オプション（§26.12）</a> ／ <a href="../../../../../MODEL_INDEX.md#7-exotics--martingales">実装・テスト：MODEL_INDEX 7</a>。

(model-exchange)=
### 交換オプションと比率測度

Margrabe exchange option。

**何を表すか：** 二資産の価格と、その比（無次元）を使います。

**仮定と限界：** 両資産の対数正規変動と相関、配当を指定します。支払通貨とニュメレールをそろえます。

**解き方・手順：** 資産を基準にした比率へ変えて解析解またはアメリカンのツリーを使います。

**使う場面：** 一方の資産を他方へ交換する権利。

**実装と検証の範囲：** 独立求積・測度密度・米国型の縮約格子を検証。無配当等の条件つき性質を一般化しません。

**読む場所：** Hull： §26.14（pp.627–628）、§28.7（pp.681–682）。<a href="../10_exotics.html#ge-pp-627628">Book：4.4 交換オプション（§26.14、GE pp.627–628）</a> ／ <a href="../../../../../MODEL_INDEX.md#7-exotics--martingales">実装・テスト：MODEL_INDEX 7</a> ／ <a href="../../../../../MODEL_INDEX.md#p3-logic-first-private-models">実装・テスト：MODEL_INDEX P3 logic-first private models</a>。

(model-variance-swap)=
### バリアンス・ボラティリティ・スワップ

Variance and volatility swaps。

**何を表すか：** 累積した収益率の二乗またはその平方根と、契約の名目を扱います。

**仮定と限界：** 分散とボラティリティの名目換算を区別します。ジャンプや有限の行使価格範囲で複製誤差が変わります。

**解き方・手順：** OTM オプションの静的ストリップと積分、平方根の期待値を計算します。

**使う場面：** 実現分散・ボラティリティを交換する契約。

**実装と検証の範囲：** 原典例、独立 Heston 参照、格子・翼の誤差を検証。平方根の平均を平均の平方根で置き換えません。

**読む場所：** Hull： §26.16（pp.629–632）。<a href="../10_exotics.html#ge-pp-629632">Book：4.6 ボラティリティ・スワップとバリアンス・スワップ（§26.16、GE pp.629–632）</a> ／ <a href="../../../../../MODEL_INDEX.md#7-exotics--martingales">実装・テスト：MODEL_INDEX 7</a>。

(model-static-barrier)=
### バリアの静的複製

Static call-ladder replication。

**何を表すか：** 複数のコールの保有数量と境界での価値（通貨）をそろえます。

**仮定と限界：** 有限本のコールで境界を近似します。ノード間の残差が残ります。

**解き方・手順：** 境界条件を三角状の連立計算で合わせ、コールの束を作ります。

**使う場面：** 動的売買を減らすバリアのヘッジ。

**実装と検証の範囲：** 独立な連続監視価格と、照合点を増やした近似を比較。有限本での完全複製は主張しません。

**読む場所：** Hull： §26.17（pp.632–634）。<a href="../10_exotics.html#id34">Book：4.7 静的オプション複製（§26.17）</a> ／ <a href="../../../../../MODEL_INDEX.md#7-exotics--martingales">実装・テスト：MODEL_INDEX 7</a>。

(model-packages)=
### レンジ先渡しと後払いの権利

Range forwards and deferred-payment options。

**何を表すか：** 複数の権利の代金と満期の受払い（通貨）を合算します。

**仮定と限界：** ゼロ費用は損失ゼロとは異なります。プレミアムを支払う時点をそろえます。

**解き方・手順：** バニラ価格と割引で行使価格・後払い額を決め、損益を分けます。

**使う場面：** 通貨のレンジ先渡し、ブレークフォワード。

**実装と検証の範囲：** 原典値と独立価格・求積・会計を確認。リスク表は保存済み参照であり公開 API とは別です。

**読む場所：** Hull： §26.1（pp.614–615）。<a href="../10_exotics.html#ge-pp-614615">Book：4.8 パッケージ（§26.1、GE pp.614–615）</a> ／ <a href="../../../../../MODEL_INDEX.md#7-exotics--martingales">実装・テスト：MODEL_INDEX 7</a>。

(model-perpetual-option)=
### 永久アメリカン・オプション

Perpetual American options。

**何を表すか：** 満期のない株式オプションの価格と行使境界（通貨／株）を求めます。

**仮定と限界：** 係数や配当が時間で変わらず、無限期間を考えます。有限満期への流用には差が残ります。

**解き方・手順：** 常微分方程式の解析解と価値一致・滑らかな接続を使います。

**使う場面：** 行使境界の原理と長満期の比較基準。

**実装と検証の範囲：** 独立積分・行使境界・長満期 CRR を比較。無配当コールの境界は有限とは限りません。

**読む場所：** Hull： §26.2（pp.615–616）。<a href="../10_exotics.html#ge-pp-615616">Book：4.9 永久アメリカン・コールとプット（§26.2、GE pp.615–616）</a> ／ <a href="../../../../../MODEL_INDEX.md#7-exotics--martingales">実装・テスト：MODEL_INDEX 7</a>。

(model-scheduled-option)=
### 非標準の行使日程

Nonstandard American exercise schedules。

**何を表すか：** 株価と、日付ごとの行使価格（通貨／株）を扱います。

**仮定と限界：** 行使可能日と行使価格を正確なツリーの段に割り当てます。

**解き方・手順：** 許可されたノードだけで即時行使と継続を比較します。

**使う場面：** ワラントや限られた日程での行使。

**実装と検証の範囲：** 原典条件、全経路列挙、独立な後退帰納を比較。

**読む場所：** Hull： §26.3（p.616）。<a href="../10_exotics.html#ge-p-616">Book：4.10 非標準アメリカン・オプション（§26.3、GE p.616）</a> ／ <a href="../../../../../MODEL_INDEX.md#7-exotics--martingales">実装・テスト：MODEL_INDEX 7</a>。

(model-gap)=
### ギャップ・オプション

Gap options。

**何を表すか：** 権利が成立する閾値と、支払額を決める価格（ともに株価単位）を分けます。

**仮定と限界：** 支払いが負になりうる定義もあり、通常のコールと同じ max を勝手に加えません。

**解き方・手順：** バニラとバイナリの分解または符号つき給付の積分を使います。

**使う場面：** トリガーと決済価格が異なる契約。

**実装と検証の範囲：** 原典値と独立な符号つき密度積分・保険契約の会計を検証。

**読む場所：** Hull： §26.4（p.617）。<a href="../10_exotics.html#ge-p-617">Book：4.11 ギャップ・オプション（§26.4、GE p.617）</a> ／ <a href="../../../../../MODEL_INDEX.md#7-exotics--martingales">実装・テスト：MODEL_INDEX 7</a>。

(model-forward-start)=
### フォワード・スタート

Forward-start options。

**何を表すか：** 将来の開始時点の株価で行使価格（通貨／株）を定めます。

**仮定と限界：** 開始時と満期を区別します。価格の同次性が使えるモデル条件が必要です。

**解き方・手順：** 開始時点での条件付き価格を、さらに現在へ平均・割引します。

**使う場面：** 後日開始する ATM コール。

**実装と検証の範囲：** 独立な二時点積分・MC と株価に対する同次性を検証。

**読む場所：** Hull： §26.5（p.618）。<a href="../10_exotics.html#ge-p-618">Book：4.12 フォワード・スタート・オプション（§26.5、GE p.618）</a> ／ <a href="../../../../../MODEL_INDEX.md#7-exotics--martingales">実装・テスト：MODEL_INDEX 7</a>。

(model-cliquet)=
### 単純なクリケット

Simple stock-price cliquets。

**何を表すか：** 各リセット期間の株価と、その都度の支払額（通貨）を扱います。

**仮定と限界：** 各期の決済、リセット価格と名目の取り方を固定します。リターン型等へ無条件では広げません。

**解き方・手順：** 各期間のオプション価値を足し、複数時点の経路で確認します。

**使う場面：** 原典の単純な株価リセット契約。

**実装と検証の範囲：** 独立密度積分・多時点 MC で検証。global/local 制約の違いを区別します。

**読む場所：** Hull： §26.6（p.618）。<a href="../10_exotics.html#cliquet-strikereset-26-6ge-p-618">Book：4.13 Cliquet：strikeのresetと各期の支払（§26.6、GE p.618）</a> ／ <a href="../../../../../MODEL_INDEX.md#7-exotics--martingales">実装・テスト：MODEL_INDEX 7</a>。

(model-compound)=
### 複合オプション

Compound options。

**何を表すか：** 原資産株価と、内側のオプション価格（ともに指定した通貨単位）を扱います。

**仮定と限界：** 外側と内側の行使価格・満期・コール/プットを別に定めます。

**解き方・手順：** 臨界株価を求め、二変量正規の式または条件付き積分で評価します。

**使う場面：** オプションを買う・売る権利。

**実装と検証の範囲：** 独立求積・条件付き MC と入力変異の拒否を検証。

**読む場所：** Hull： §26.7（pp.618–619）。<a href="../10_exotics.html#ge-pp-618619">Book：4.14 コンパウンド・オプション：二つの行使日（§26.7、GE pp.618–619）</a> ／ <a href="../../../../../MODEL_INDEX.md#7-exotics--martingales">実装・テスト：MODEL_INDEX 7</a>。

(model-chooser)=
### 単純なチューザー

Simple chooser options。

**何を表すか：** 選択日の株価と、同じ満期・行使価格のコールとプットを扱います。

**仮定と限界：** 選択日と最終満期を区別します。一般の異なる条件のチューザーではありません。

**解き方・手順：** パリティによる配当調整済み分解と条件付き期待値を使います。

**使う場面：** 後でコールかプットかを選ぶ権利。

**実装と検証の範囲：** 端点・独立積分・条件付き MC を検証。

**読む場所：** Hull： §26.8（pp.619–620）。<a href="../10_exotics.html#chooser-callput-26-8ge-pp-619620">Book：4.15 Chooser：後からcallかputを選ぶ（§26.8、GE pp.619–620）</a> ／ <a href="../../../../../MODEL_INDEX.md#7-exotics--martingales">実装・テスト：MODEL_INDEX 7</a>。

## ボラティリティ：局所・確率・ジャンプ

一定のボラティリティで表せない形を、状態依存、別のランダム因子、ジャンプのどれで表すかを考えます。同じ現在の価格に合っても、将来の動きまで同じとは限りません。

(model-implied-vol)=
### IV とスマイルの軸

Implied volatility and smile coordinates（IV）。

**何を表すか：** オプション価格から、年率換算 IV と行使価格・デルタ等の軸を求めます。

**仮定と限界：** 逆算の価格式と通貨・配当を指定します。IV は独立に観測する状態過程ではありません。

**解き方・手順：** 価格の根を解き、パリティ・軸変換・条件付きヘッジを確認します。

**使う場面：** 市場価格を比較する共通の表示。

**実装と検証の範囲：** 逆算の往復と独立積分・軸の変換を検証。

**読む場所：** Hull： §20.1（pp.451–452）、§20.4（p.458）。<a href="../05_vol_smile.html#ch-20eq-20-120-2">Book：1. インプライド・ボラティリティとパリティ（Ch.20、eq 20.1–20.2）</a> ／ <a href="../../../../../MODEL_INDEX.md#2-volatility--smile">実装・テスト：MODEL_INDEX 2</a> ／ <a href="../../../../../MODEL_INDEX.md#p4-logic-first-private-models">実装・テスト：MODEL_INDEX P4 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch20.html#section-20-1">補足教材 §20.1</a>。

**関係：** [Dupire 局所ボラティリティ](#model-local-vol) へ（[条件・出典](#map-relation-12)：入力・較正）。[価格から読む確率密度](#model-density) へ（[条件・出典](#map-relation-14)：入力・較正）。[SSVI の総分散面](#model-ssvi) から（[条件・出典](#map-relation-15)：入力・較正）。

(model-cev)=
### CEV

Constant elasticity of variance（CEV）。

**何を表すか：** 株価 S によって絶対的な変動幅が変わります。S の単位は通貨／株です。

**仮定と限界：** べき乗のボラティリティと境界の扱いを指定します。株価ゼロ付近に注意が必要です。

**解き方・手順：** 解析式と独立な PDE を比べます。

**使う場面：** 価格水準で変動が変わるスマイルの例。

**実装と検証の範囲：** BSM への特殊化と独立 PDE を検証。

**読む場所：** Hull： §27.1（pp.641–646）。<a href="../06_numerical.html#blackscholesmerton-27-1">Book：7. Black–Scholes–Merton 以外のモデル（§27.1）</a> ／ <a href="../../../../../MODEL_INDEX.md#2-volatility--smile">実装・テスト：MODEL_INDEX 2</a>。

**関係：** [ブラック＝ショールズ＝マートン](#model-bsm) へ（[条件・出典](#map-relation-7)：特殊な場合）。

(model-merton-jump)=
### Merton ジャンプ拡散

Merton jump diffusion。

**何を表すか：** 株価に連続変動と不連続なジャンプを加えます。強度は時間の逆数です。

**仮定と限界：** ジャンプ回数・大きさの分布を固定します。拡散だけによる完全複製は使えません。

**解き方・手順：** ポアソン混合の価格を足し、独立な期待値計算と比べます。

**使う場面：** 突発的な価格変動とスマイル。

**実装と検証の範囲：** ジャンプなしの極限と独立混合積分を検証。

**読む場所：** Hull： §27.1（pp.641–646）。<a href="../06_numerical.html#blackscholesmerton-27-1">Book：7. Black–Scholes–Merton 以外のモデル（§27.1）</a> ／ <a href="../../../../../MODEL_INDEX.md#2-volatility--smile">実装・テスト：MODEL_INDEX 2</a>。

**関係：** [ブラック＝ショールズ＝マートン](#model-bsm) へ（[条件・出典](#map-relation-8)：特殊な場合）。

(model-variance-gamma)=
### バリアンス・ガンマ

Variance gamma（VG）。

**何を表すか：** ランダムなガンマ時計でブラウン運動を動かした対数価格を扱います。

**仮定と限界：** 時計とドリフト補正を指定します。過程の裾とモーメントが存在する条件が必要です。

**解き方・手順：** ガンマ混合または特性関数による評価を使います。

**使う場面：** 連続拡散とは違う尖りと裾を持つ価格モデル。

**実装と検証の範囲：** BSM 極限と独立なガンマ密度積分を検証。

**読む場所：** Hull： §27.1（pp.641–646）。<a href="../06_numerical.html#blackscholesmerton-27-1">Book：7. Black–Scholes–Merton 以外のモデル（§27.1）</a> ／ <a href="../../../../../MODEL_INDEX.md#2-volatility--smile">実装・テスト：MODEL_INDEX 2</a>。

**関係：** [ブラック＝ショールズ＝マートン](#model-bsm) へ（[条件・出典](#map-relation-9)：極限・近似）。

(model-time-vol)=
### 時間依存ボラティリティ

Deterministic time-dependent volatility。

**何を表すか：** 時刻ごとの分散率（時間の逆数）を与えます。

**仮定と限界：** 将来の変動幅の時系列が確定的です。ランダムな分散とは違います。

**解き方・手順：** 期間にわたる分散率の積分を平均し、BSM に渡します。

**使う場面：** 満期ごとに異なる総分散の表現。

**実装と検証の範囲：** 独立な時間依存 PDE と比較。

**読む場所：** Hull： §27.2（pp.646–649）。<a href="../06_numerical.html#id8">Book：8. 確率ボラティリティ・モデル（§27.2）</a> ／ <a href="../../../../../MODEL_INDEX.md#2-volatility--smile">実装・テスト：MODEL_INDEX 2</a>。

**関係：** [ブラック＝ショールズ＝マートン](#model-bsm) へ（[条件・出典](#map-relation-6)：特殊な場合）。[Heston 確率ボラティリティ](#model-heston) から（[条件・出典](#map-relation-10)：特殊な場合）。

(model-vol-mixing)=
### Hull–White の分散混合

Hull–White stochastic-volatility mixing。

**何を表すか：** 期間平均分散（時間の逆数）の分布を用います。

**仮定と限界：** 株価側と分散側の独立性等、混合式の条件を指定します。相関があれば同じ混合を無条件では使えません。

**解き方・手順：** 平均分散ごとの条件付き BSM 価格を、さらに平均します。

**使う場面：** 平均分散にランダム性がある価格の理解。

**実装と検証の範囲：** 独立な積分と条件付き MC を比較。平均分散だけを価格式に代入する方法とは区別します。

**読む場所：** Hull： §27.2（pp.646–649）。<a href="../06_numerical.html#id8">Book：8. 確率ボラティリティ・モデル（§27.2）</a> ／ <a href="../../../../../MODEL_INDEX.md#2-volatility--smile">実装・テスト：MODEL_INDEX 2</a>。

(model-heston)=
### Heston 確率ボラティリティ

Heston stochastic volatility。

**何を表すか：** 株価（通貨／株）と非負の瞬間分散（時間の逆数）を同時に動かします。

**仮定と限界：** 平方根拡散の分散と、株価との相関を指定します。離散化は非負性に注意が必要です。

**解き方・手順：** 特性関数を COS・積分へ渡し、MC と比較します。

**使う場面：** レバレッジ効果を含むスマイル。

**実装と検証の範囲：** 特性関数、独立積分、MC の一致を検証。市場への較正の一意性までは保証しません。

**読む場所：** Hull の前提： §27.2（pp.646–649）。<a href="../14_stoch_vol_fourier.html#heston">Book：2. Heston モデル</a> ／ <a href="../../../../../MODEL_INDEX.md#2-volatility--smile">実装・テスト：MODEL_INDEX 2</a>。

**関係：** [時間依存ボラティリティ](#model-time-vol) へ（[条件・出典](#map-relation-10)：特殊な場合）。[ブラック＝ショールズ＝マートン](#model-bsm) へ（[条件・出典](#map-relation-11)：特殊な場合）。

(model-local-vol)=
### Dupire 局所ボラティリティ

Dupire local volatility。

**何を表すか：** 時刻と株価の関数として分散率を決めます。

**仮定と限界：** 滑らかで無裁定なヨーロピアン価格面と、微分の安定性が必要です。

**解き方・手順：** 価格面の満期・行使価格微分から局所ボラを求めます。

**使う場面：** 現在のバニラ価格面を再価格するモデル。

**実装と検証の範囲：** 解析混合面・独立 PDE と経路比較を検証。現在面が合っても将来の条件付き動学は一意ではありません。

**読む場所：** Hull： §27.3（pp.649–650）。<a href="../06_numerical.html#ivf-27-3">Book：9. IVF（局所ボラティリティ）モデル（§27.3）</a> ／ <a href="../../../../../MODEL_INDEX.md#2-volatility--smile">実装・テスト：MODEL_INDEX 2</a>。

**関係：** [IV とスマイルの軸](#model-implied-vol) から（[条件・出典](#map-relation-12)：入力・較正）。[ブラック＝ショールズ＝マートン](#model-bsm) へ（[条件・出典](#map-relation-13)：特殊な場合）。

(model-density)=
### 価格から読む確率密度

Breeden–Litzenberger implied density。

**何を表すか：** 行使価格に沿うコール価格の曲率から Q の終値密度を読みます。密度は価格単位の逆数です。

**仮定と限界：** 十分滑らかな価格面と割引の指定が必要です。有限差分や補間は負の密度を生みえます。

**解き方・手順：** 行使価格による二階微分と密度の積分を確認します。

**使う場面：** スマイルの背後にある評価分布の理解。

**実装と検証の範囲：** 原典付録の区間確率と平坦ボラの分布を比較。

**読む場所：** Hull： §20.appendix（pp.467–469）。<a href="../05_vol_smile.html#breeden-litzenberger-20a">Book：4. インプライド分布 — Breeden-Litzenberger（付録 20A）</a> ／ <a href="../../../../../MODEL_INDEX.md#2-volatility--smile">実装・テスト：MODEL_INDEX 2</a> ／ <a href="../../../../../report/site/chapters/ch20.html#section-20-appendix">補足教材 §20.appendix</a>。

**関係：** [IV とスマイルの軸](#model-implied-vol) から（[条件・出典](#map-relation-14)：入力・較正）。

(model-cos)=
### COS フーリエ評価

Fourier-cosine pricing（COS）。

**何を表すか：** 対数価格等の特性関数（無次元）から価格・密度を求めます。

**仮定と限界：** 積分区間と打切り項数を選びます。特性関数があっても打切り誤差は残ります。

**解き方・手順：** 余弦展開の係数とペイオフ係数を合わせます。

**使う場面：** Heston 等の多数のヨーロピアン価格。

**実装と検証の範囲：** 対数正規モデルの BSM と密度積分を検証。

**読む場所：** Hull の前提： §27.2（pp.646–649）。<a href="../14_stoch_vol_fourier.html#cos-fourier">Book：4. COS 法による Fourier 価格付け</a> ／ <a href="../../../../../MODEL_INDEX.md#2-volatility--smile">実装・テスト：MODEL_INDEX 2</a>。

(model-sabr)=
### SABR

Stochastic alpha beta rho model（SABR）。

**何を表すか：** フォワード価格とその変動係数を同時に動かします。単位は正規型・対数正規型で異なります。

**仮定と限界：** べき指数と相関等を固定し、漸近 IV の適用範囲を意識します。

**解き方・手順：** Hagan 型の IV 近似と較正・感応度を使います。

**使う場面：** 金利等のスマイルのパラメーター表示。

**実装と検証の範囲：** 原典の式、極限、MC 教師を比較。近似式の全領域での無裁定は保証しません。

**読む場所：** Hull の前提： §27.2（pp.646–649）。<a href="../14_stoch_vol_fourier.html#sabr-hagan">Book：6. SABR と Hagan 公式</a> ／ <a href="../../../../../MODEL_INDEX.md#2-volatility--smile">実装・テスト：MODEL_INDEX 2</a>。

(model-normal-sabr)=
### 正規型・シフト SABR

Normal, shifted and explicit-boundary SABR。

**何を表すか：** 金利等のフォワードと変動係数を扱い、必要に応じて価格軸をシフトします。

**仮定と限界：** 負の値を許す範囲と境界を明記します。異なる境界モデルを同じものと呼びません。

**解き方・手順：** 正規 IV・シフト IV の近似、Bartlett 型デルタを比較します。

**使う場面：** 負金利を含むスマイルの教材。

**実装と検証の範囲：** vol23 の free-boundary は明示 shift 境界で、Antonov 型の内生境界を実装したものではありません。

**読む場所：** Hull の前提： §27.2（pp.646–649）。<a href="../23_rfr_post_libor.html#bachelier-shifted-sabr-smile">Book：Bachelier/shifted SABR smile</a> ／ <a href="../../../../../MODEL_INDEX.md#2-volatility--smile">実装・テスト：MODEL_INDEX 2</a>。

(model-ssvi)=
### SSVI の総分散面

Surface stochastic volatility inspired parameterization（SSVI）。

**何を表すか：** 満期と対数マネーネスごとの総分散（無次元）を表します。

**仮定と限界：** パラメーターの無裁定条件を確認します。価格面の表現であり将来の状態過程ではありません。

**解き方・手順：** パラメーターを当てはめ、バタフライ条件の余裕を計算します。

**使う場面：** 滑らかなスマイル面の構築。

**実装と検証の範囲：** 安全なパラメーター域での無裁定条件を検証。

**読む場所：** Hull の前提： §20.5（pp.458–460）。<a href="../19_inverse_surfaces.html#iv-fitvariance-termpareto-frontier">Book：IV fitとvariance termのPareto frontier</a> ／ <a href="../../../../../MODEL_INDEX.md#9-inverse-problems--arbitrage-aware-surfaces">実装・テスト：MODEL_INDEX 9</a> ／ <a href="../../../../../report/site/chapters/ch20.html#section-20-5">補足教材 §20.5</a>。

**関係：** [IV とスマイルの軸](#model-implied-vol) へ（[条件・出典](#map-relation-15)：入力・較正）。

(model-convex-projection)=
### コール価格の凸射影

Convex call-price projection。

**何を表すか：** 行使価格ごとの価格（通貨）の列を扱います。

**仮定と限界：** 指定した格子上の単調性・凸性等を課します。格子外や全満期の無裁定は別に確認します。

**解き方・手順：** 制約集合へ価格を射影し、無制約・ソフト制約との残差を比べます。

**使う場面：** ノイズを含む価格面の整形。

**実装と検証の範囲：** 制約と再価格のトレードオフを合成データで検証。

**読む場所：** Hull の前提： §20.5（pp.458–460）。<a href="../19_inverse_surfaces.html#clean-teacherhard-constrained-fit">Book：clean teacher価格とhard-constrained fit</a> ／ <a href="../../../../../MODEL_INDEX.md#9-inverse-problems--arbitrage-aware-surfaces">実装・テスト：MODEL_INDEX 9</a> ／ <a href="../../../../../report/site/chapters/ch20.html#section-20-5">補足教材 §20.5</a>。

## 金利：曲線・短期金利・HJM・LMM

確定した受払列を曲線で割り引く段階から、将来の曲線の動きをモデル化する段階へ進みます。通貨、期間、割引と予測の曲線を先に決めます。

(model-zero-curve)=
### 債券とゼロ曲線

Bond cash flows and zero-curve bootstrap。

**何を表すか：** 満期ごとの割引因子（無次元）と債券の受払額（通貨）を扱います。

**仮定と限界：** 複利、日数、補間と受払日を指定します。利回りとゼロ金利は同じ量ではありません。

**解き方・手順：** 受払額を割り引き、価格から順にゼロ曲線を求めます。

**使う場面：** 債券・FRA・スワップ評価の共通入力。

**実装と検証の範囲：** 原典値と独立な成長率・根・同時方程式・複製を検証。

**読む場所：** Hull： §4.5（pp.104–105）、§4.6（pp.105–106）、§4.7（pp.106–108）、§4.8（pp.109–110）。<a href="../04_futures_rates.html#ytm-4-54-6">Book：4. ゼロレート・債券価格・YTM・パーイールド（§4.5–4.6）</a> ／ <a href="../../../../../MODEL_INDEX.md#5-rates--swaps-curves-ir-options-rfr-post-libor">実装・テスト：MODEL_INDEX 5</a> ／ <a href="../../../../../MODEL_INDEX.md#p4-logic-first-private-models">実装・テスト：MODEL_INDEX P4 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch04.html#section-4-5">補足教材 §4.5</a>。

**関係：** [Hull–White 一因子](#model-hull-white) へ（[条件・出典](#map-relation-21)：入力・較正）。[LIBOR 市場モデル](#model-lmm) へ（[条件・出典](#map-relation-22)：入力・較正）。

(model-swaps)=
### 金利・通貨スワップ

Interest-rate and currency swaps。

**何を表すか：** 各通貨の固定・変動の受払列と価値（通貨）を扱います。

**仮定と限界：** 既知の fixing、年分数、割引曲線と予測曲線をそろえます。比較優位の資金調達と市場価値は別です。

**解き方・手順：** 債券の差または FRA の束として評価し、受払を再生します。

**使う場面：** 固定・変動の交換と通貨の調達。

**実装と検証の範囲：** 原典例・既経過契約・通貨別会計を独立に検証。

**読む場所：** Hull： §7.6（pp.183–185）、§7.9（pp.190–192）。<a href="../07_swaps.html#ch-7">Book：1. 金利スワップの仕組み（Ch.7）</a> ／ <a href="../../../../../MODEL_INDEX.md#5-rates--swaps-curves-ir-options-rfr-post-libor">実装・テスト：MODEL_INDEX 5</a> ／ <a href="../../../../../MODEL_INDEX.md#p4-logic-first-private-models">実装・テスト：MODEL_INDEX P4 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch07.html#section-7-6">補足教材 §7.6</a>。

(model-black76)=
### Black の市場モデル

Black market models for forwards, futures and rates。

**何を表すか：** 先物・フォワード価格または金利と、そのオプション価値（通貨）を扱います。

**仮定と限界：** 対応する測度での対数正規性、割引・年分数・アニュイティを指定します。負の金利にはそのまま使えません。

**解き方・手順：** Black 式を債券オプション・キャップ・スワップション等の受払いへ合わせます。

**使う場面：** 市場ボラの表示とヨーロピアン金利オプション。

**実装と検証の範囲：** 原典値、パリティ、独立積分と適切な測度の MC を検証。単一満期の市場モデルを曲線全体の動学と同一視しません。

**読む場所：** Hull： §18.7（pp.408–409）、§29.1（pp.688–692）、§29.2（pp.693–699）、§29.3（pp.699–702）。<a href="../02_options_basics.html#black-76-18-118-7">Book：9. 先物オプションと Black-76（§18.1–18.7）</a> ／ <a href="../../../../../MODEL_INDEX.md#5-rates--swaps-curves-ir-options-rfr-post-libor">実装・テスト：MODEL_INDEX 5</a> ／ <a href="../../../../../MODEL_INDEX.md#p3-logic-first-private-models">実装・テスト：MODEL_INDEX P3 logic-first private models</a> ／ <a href="../../../../../MODEL_INDEX.md#p4-logic-first-private-models">実装・テスト：MODEL_INDEX P4 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch18.html#section-18-7">補足教材 §18.7</a>。

**関係：** [キャリーによる先渡価格](#model-forward-carry) から（[条件・出典](#map-relation-5)：入力・較正）。

(model-rfr)=
### 翌日物 RFR の複利

Backward-looking compounded RFR（RFR）。

**何を表すか：** 日々の金利（年率）、年分数、確定済み部分と未確定部分を扱います。

**仮定と限界：** 休日暦、観測のずらし方、支払日と fixing を指定します。

**解き方・手順：** 日次の利息係数を掛け合わせ、必要なら予測と割引の曲線を分けます。

**使う場面：** 後決め複利のクーポンと旧指標からの読み替え。

**実装と検証の範囲：** 独立な日次積と暦の端点を検証。旧 LIBOR の単純金利を機械的に置き換えるものではありません。

**読む場所：** Hull の前提： §29.2（pp.693–699）。<a href="../23_rfr_post_libor.html#daily-compounded-rfr">Book：daily compounded RFR</a> ／ <a href="../../../../../MODEL_INDEX.md#5-rates--swaps-curves-ir-options-rfr-post-libor">実装・テスト：MODEL_INDEX 5</a> ／ <a href="../../../../../report/site/chapters/ch29.html#section-29-2">補足教材 §29.2</a>。

(model-bachelier)=
### Bachelier の正規型オプション

Bachelier normal model。

**何を表すか：** フォワード金利等を正規分布で表します。絶対ボラの単位は状態単位／時間の平方根です。

**仮定と限界：** 対数正規型と異なり負の値も取りえます。同じ数値のボラを Black と交換できません。

**解き方・手順：** 正規型の解析式、求積と MC を比較します。

**使う場面：** 正規ボラで表示する金利オプション。

**実装と検証の範囲：** 複利金利の独立求積・MC と閉じた式を検証。

**読む場所：** Hull の前提： §29.2（pp.693–699）。<a href="../23_rfr_post_libor.html#bachelier-shifted-sabr-smile">Book：Bachelier/shifted SABR smile</a> ／ <a href="../../../../../MODEL_INDEX.md#5-rates--swaps-curves-ir-options-rfr-post-libor">実装・テスト：MODEL_INDEX 5</a> ／ <a href="../../../../../report/site/chapters/ch29.html#section-29-2">補足教材 §29.2</a>。

(model-hull-white)=
### Hull–White 一因子

Hull–White one-factor short-rate model（HW）。

**何を表すか：** 短期金利 r（年率）を平均回帰するガウス過程で動かします。

**仮定と限界：** 初期曲線に合わせる時刻依存項を持ち、負金利を許します。一因子で全曲線の変動を説明する理想化です。

**解き方・手順：** 債券・債券オプションの解析解、格子、Jamshidian 分解と較正を使います。

**使う場面：** 曲線に合わせた金利オプション、Bermudan の比較基準。

**実装と検証の範囲：** 初期曲線・独立積分・Ho–Lee 極限・合成較正を検証。実市場の較正品質の承認ではありません。

**読む場所：** Hull の前提： §32.1（pp.732–736）、§32.2（pp.736–737）、§32.6（pp.749–751）。<a href="../26_inflation_jgbi.html#hull-white-initial-curve-fit">Book：Hull–White initial-curve fit</a> ／ <a href="../../../../../MODEL_INDEX.md#5-rates--swaps-curves-ir-options-rfr-post-libor">実装・テスト：MODEL_INDEX 5</a> ／ <a href="../../../../../MODEL_INDEX.md#p3-logic-first-private-models">実装・テスト：MODEL_INDEX P3 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch32.html#section-32-1">補足教材 §32.1</a>。

**関係：** [Ho–Lee](#model-ho-lee) へ（[条件・出典](#map-relation-18)：特殊な場合）。[Vasicek 短期金利](#model-vasicek-rate) へ（[条件・出典](#map-relation-19)：特殊な場合）。[HJM](#model-hjm) から（[条件・出典](#map-relation-20)：特殊な場合）。[債券とゼロ曲線](#model-zero-curve) から（[条件・出典](#map-relation-21)：入力・較正）。

(model-ho-lee)=
### Ho–Lee

Ho–Lee short-rate model。

**何を表すか：** 短期金利（年率）を、平均回帰のないガウス過程で動かします。

**仮定と限界：** 初期曲線に合わせるドリフトを指定します。負金利や長期分散の拡大を許すモデルです。

**解き方・手順：** ガウス積分または格子を使います。

**使う場面：** Hull–White の平均回帰なしの比較。

**実装と検証の範囲：** 非公開金利教材のガウス債券・オプションで特殊化を確認します。

**読む場所：** Hull の前提： §32.1（pp.732–736）、§32.2（pp.736–737）。<a href="../31_ir_models.html#holee-1986">Book：2.1 Ho–Lee モデル（1986）</a> ／ <a href="../../../../../MODEL_INDEX.md#p3-logic-first-private-models">実装・テスト：MODEL_INDEX P3 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch32.html#section-32-1">補足教材 §32.1</a>。

**関係：** [Hull–White 一因子](#model-hull-white) から（[条件・出典](#map-relation-18)：特殊な場合）。

(model-inflation-cashflows)=
### CPI とインフレ・スワップ

CPI conventions, ZCIS and year-on-year swaps（CPI・ZCIS）。

**何を表すか：** 消費者物価指数 CPI（指数ポイント）と名目の受払額（通貨）を扱います。

**仮定と限界：** 公表ラグ、補間、季節性と基準指数を明記します。既知の指数と予測指数を区別します。

**解き方・手順：** 指数比から受払いを作り、ゼロクーポン・前年比の評価を行います。

**使う場面：** インフレ連動のクーポンとスワップ。

**実装と検証の範囲：** fixing/予測の分離・価格の往復・季節性の相殺を検証。前年比の期待比率と比率の期待値を混ぜません。

**読む場所：** Hull の前提： §34.6（pp.781–782）。<a href="../26_inflation_jgbi.html#cpi-trendfixing3lagrebasing">Book：CPI trend・fixing・3か月lag・rebasing</a> ／ <a href="../../../../../MODEL_INDEX.md#5-rates--swaps-curves-ir-options-rfr-post-libor">実装・テスト：MODEL_INDEX 5</a> ／ <a href="../../../../../report/site/chapters/ch34.html#section-34-6">補足教材 §34.6</a>。

(model-jgbi)=
### 物価連動国債と償還フロア

Japanese inflation-linked bonds and redemption floor（JGBi）。

**何を表すか：** CPI の参照指数、連動係数、実質価格、償還額（通貨）を扱います。

**仮定と限界：** 指数ラグ、丸めと償還時だけのフロアを指定します。途中のクーポンと償還を区別します。

**解き方・手順：** 債券の受払と、フロアのオプション部分を分けて評価します。

**使う場面：** 日本の物価連動国債の仕組みを読む教材。

**実装と検証の範囲：** 明示した契約規約と Jarrow–Yildirim の解析/MC 分解を検証。現行発行条件の網羅ではありません。

**読む場所：** Hull の前提： §34.6（pp.781–782）。<a href="../26_inflation_jgbi.html#jgbi-cash-flow10indexsettlement">Book：JGBi cash flow・10日基準index・settlement</a> ／ <a href="../../../../../MODEL_INDEX.md#5-rates--swaps-curves-ir-options-rfr-post-libor">実装・テスト：MODEL_INDEX 5</a> ／ <a href="../../../../../report/site/chapters/ch34.html#section-34-6">補足教材 §34.6</a>。

(model-jarrow-yildirim)=
### Jarrow–Yildirim インフレモデル

Jarrow–Yildirim inflation model（JY）。

**何を表すか：** 名目・実質の短期金利（年率）と CPI（指数ポイント）を同時に動かします。

**仮定と限界：** 両通貨のように扱うニュメレールと相関をそろえます。実質金利側のクオント・ドリフトを落とせません。

**解き方・手順：** 支払時点の測度で指数比の分布を求め、解析式と MC を使います。

**使う場面：** CPI オプションとインフレ連動商品の評価。

**実装と検証の範囲：** 名目/実質の測度変更・CPI 比率・解析/MC を検証。

**読む場所：** Hull の前提： §30.3（pp.711–714）。<a href="../26_inflation_jgbi.html#jarrow-yildirim-payment-forward-measure">Book：Jarrow–Yildirim payment-forward measure</a> ／ <a href="../../../../../MODEL_INDEX.md#5-rates--swaps-curves-ir-options-rfr-post-libor">実装・テスト：MODEL_INDEX 5</a> ／ <a href="../../../../../report/site/chapters/ch30.html#section-30-3">補足教材 §30.3</a>。

(model-ir-hedging)=
### 金利オプションの感応度

Rate and volatility hedging。

**何を表すか：** 曲線の各点やボラ入力に対する価値の変化（通貨）を追います。

**仮定と限界：** ショックの単位、曲線の持上げ方、PCA の標本期間を明記します。

**解き方・手順：** 有限差分・解析微分・PCA 因子で感応度を分けます。

**使う場面：** キャップやスワップションのヘッジ。

**実装と検証の範囲：** 独立な微分と SVD、bump の収束を検証。因子数を減らすと残余リスクが残ります。

**読む場所：** Hull： §29.4（p.703）。<a href="../11_ir_options.html#ch-29">Book：1. なぜ金利は難しいか（Ch.29）</a> ／ <a href="../../../../../MODEL_INDEX.md#p3-logic-first-private-models">実装・テスト：MODEL_INDEX P3 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch29.html#section-29-4">補足教材 §29.4</a>。

(model-convexity)=
### 利回りの凸性調整

Yield convexity adjustment。

**何を表すか：** 利回り（年率）と債券価格（通貨）の非線形な関係を扱います。

**仮定と限界：** 局所テイラー近似と評価測度を指定します。平均利回りをそのまま価格関数へ入れません。

**解き方・手順：** 価格の一階・二階微分と分散から補正し、独立積分で差を見ます。

**使う場面：** CMS 等の利回りに連動する支払い。

**実装と検証の範囲：** 原典例・独立求積・省略項の収束を検証。局所近似の残差を保持します。

**読む場所：** Hull： §30.1（pp.707–710）。<a href="../11_ir_options.html#eq-30-1">Book：7. コンベクシティ調整（§30.1、eq 30.1）</a> ／ <a href="../../../../../MODEL_INDEX.md#p3-logic-first-private-models">実装・テスト：MODEL_INDEX P3 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch30.html#section-30-1">補足教材 §30.1</a>。

(model-timing)=
### 支払時点の調整

Timing adjustment。

**何を表すか：** 同じ金利を参照しても異なる日に払う価値（通貨）を区別します。

**仮定と限界：** 参照期間と支払期間を明記します。割引債の比率を固定する近似の条件が必要です。

**解き方・手順：** 測度変更の密度と共分散による調整を比較します。

**使う場面：** 前払い・後払いなどの決済時点の違い。

**実装と検証の範囲：** 原典値・独立ガウス積分・生の密度 MC を比較。

**読む場所：** Hull： §30.2（pp.710–711）。<a href="../11_ir_options.html#eq-30-2-30-3">Book：8. タイミング調整（§30.2、eq 30.2/30.3）</a> ／ <a href="../../../../../MODEL_INDEX.md#p3-logic-first-private-models">実装・テスト：MODEL_INDEX P3 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch30.html#section-30-2">補足教材 §30.2</a>。

(model-quanto)=
### クオント調整

Quanto pricing and measure adjustment。

**何を表すか：** 原資産価格と為替レート、支払通貨の受払額を扱います。

**仮定と限界：** 相関と為替の向きを指定します。外国資産を持つことと国内通貨払いの権利を持つことは異なります。

**解き方・手順：** 測度変更でドリフトを調整し、解析式・求積・PDE を比較します。

**使う場面：** 通貨を固定した外国資産への支払い。

**実装と検証の範囲：** 原典値と独立な為替密度・積分・米国型 PDE を検証。

**読む場所：** Hull： §30.3（pp.711–714）。<a href="../11_ir_options.html#eq-30-5">Book：9. クォント調整（§30.3、eq 30.5）</a> ／ <a href="../../../../../MODEL_INDEX.md#p3-logic-first-private-models">実装・テスト：MODEL_INDEX P3 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch30.html#section-30-3">補足教材 §30.3</a>。

(model-short-rate-pde)=
### 短期金利による割引と PDE

Short-rate discounting and pricing PDE。

**何を表すか：** 短期金利の経路（年率）と割引債価値を扱います。

**仮定と限界：** どの確率測度のドリフトかを指定します。将来金利を単に平均して割り引く操作とは異なります。

**解き方・手順：** 経路上の積分割引と金利 PDE を比べます。

**使う場面：** 短期金利モデル全体の評価原理。

**実装と検証の範囲：** 独立なガウス経路・差分 PDE・一定曲線での整合性を検証。

**読む場所：** Hull： §31.1（pp.719–721）。<a href="../31_ir_models.html#hullwhite-1990">Book：2.2 Hull–White モデル（1990）</a> ／ <a href="../../../../../MODEL_INDEX.md#p3-logic-first-private-models">実装・テスト：MODEL_INDEX P3 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch31.html#section-31-1">補足教材 §31.1</a>。

(model-vasicek-rate)=
### Vasicek 短期金利

Vasicek short-rate model。

**何を表すか：** 短期金利（年率）を一定の長期水準へ戻るガウス過程で動かします。

**仮定と限界：** 一定係数を仮定し、負金利を許します。現在の曲線へ自動的に一致するとは限りません。

**解き方・手順：** ガウスの遷移とアフィン型の債券価格を使います。

**使う場面：** 均衡型モデルの基礎と長短金利の動き。

**実装と検証の範囲：** 独立ガウス積分・原典の感応度・経路比較を検証。信用の Vasicek 損失モデルとは別のカードです。

**読む場所：** Hull： §31.2（pp.721–726）。<a href="../31_ir_models.html#vasicek-1977">Book：1.1 Vasicek モデル（1977）</a> ／ <a href="../../../../../MODEL_INDEX.md#p3-logic-first-private-models">実装・テスト：MODEL_INDEX P3 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch31.html#section-31-2">補足教材 §31.2</a>。

**関係：** [Hull–White 一因子](#model-hull-white) から（[条件・出典](#map-relation-19)：特殊な場合）。

(model-cir-rate)=
### CIR 短期金利

Cox–Ingersoll–Ross short-rate model（CIR）。

**何を表すか：** 非負の短期金利（年率）を平方根拡散で動かします。

**仮定と限界：** ゼロ境界の性質はパラメーターに依存します。単純な Euler 法では負値を作ることがあります。

**解き方・手順：** アフィン債券式、Riccati 方程式、非心カイ二乗遷移を使います。

**使う場面：** 正値金利を意識した均衡型モデル。

**実装と検証の範囲：** 独立な積分・遷移分布・原典のリスク量を検証。

**読む場所：** Hull： §31.2（pp.721–726）。<a href="../31_ir_models.html#cir-cox-ingersoll-ross-1985">Book：1.2 CIR モデル（Cox-Ingersoll-Ross, 1985）</a> ／ <a href="../../../../../MODEL_INDEX.md#p3-logic-first-private-models">実装・テスト：MODEL_INDEX P3 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch31.html#section-31-2">補足教材 §31.2</a>。

(model-rendleman-bartter)=
### Rendleman–Bartter 短期金利

Rendleman–Bartter short-rate model。

**何を表すか：** 短期金利（年率）に比例するドリフトと変動を置きます。

**仮定と限界：** 対数正規型の正値性を持ちますが、平均回帰を標準では持ちません。

**解き方・手順：** 経路シミュレーションと独立な金利 PDE を比べます。

**使う場面：** 均衡型短期金利の仮定の比較。

**実装と検証の範囲：** 独立 PDE と経路、係数の扱いを検証。

**読む場所：** Hull： §31.2（pp.721–726）。<a href="../31_ir_models.html#rendlemanbartter">Book：1.3 Rendleman–Bartter モデル</a> ／ <a href="../../../../../MODEL_INDEX.md#p3-logic-first-private-models">実装・テスト：MODEL_INDEX P3 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch31.html#section-31-2">補足教材 §31.2</a>。

(model-short-rate-measure)=
### 短期金利の P と Q

Short-rate risk premiums and measures。

**何を表すか：** 観測下と評価下の短期金利のドリフト（年率／時間）を区別します。

**仮定と限界：** 金利リスクの市場価格と符号の規約が必要です。時系列推定だけでは Q を決められません。

**解き方・手順：** 測度の傾斜と債券の期待収益/PDE を対応づけます。

**使う場面：** 観測した金利モデルを価格評価へ移す場面。

**実装と検証の範囲：** 独立ガウス傾斜・MC・CIR ドリフトを検証。

**読む場所：** Hull： §31.3（pp.726–727）。<a href="../31_ir_models.html#id3">Book：モデル分類図</a> ／ <a href="../../../../../MODEL_INDEX.md#p3-logic-first-private-models">実装・テスト：MODEL_INDEX P3 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch31.html#section-31-3">補足教材 §31.3</a>。

(model-rate-estimation)=
### 短期金利の時系列推定

Short-rate parameter estimation。

**何を表すか：** 観測間隔つきの金利時系列（年率）からドリフトと変動を推定します。

**仮定と限界：** 離散観測、分布仮定と評価測度への追加情報を分けます。

**解き方・手順：** Vasicek の回帰と CIR の Euler 推定、価格リスクの推定を比べます。

**使う場面：** P の推定と Q の較正の違いを学ぶ教材。

**実装と検証の範囲：** 原典表・独立回帰/積分/最適化を検証。将来の予測力の承認ではありません。

**読む場所：** Hull： §31.4（pp.727–728）。<a href="../31_ir_models.html#section-1-3">Book：Section 1 まとめ: 均衡3モデル比較</a> ／ <a href="../../../../../MODEL_INDEX.md#p3-logic-first-private-models">実装・テスト：MODEL_INDEX P3 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch31.html#section-31-4">補足教材 §31.4</a>。

(model-two-factor-rates)=
### 二因子ガウス金利

Two-factor Gaussian rate models。

**何を表すか：** 二つのガウス因子とその和の短期金利（年率）を扱います。

**仮定と限界：** 因子の相関と初期曲線への適合を指定します。一因子より柔軟でもすべての曲線リスクは表せません。

**解き方・手順：** 共分散積分・債券式・二因子オプションの期待値を求めます。

**使う場面：** 曲線の複数の変動方向。

**実装と検証の範囲：** 独立な行列指数・積分・MCを比較。クーポン債の近似と厳密な給付の教師を区別します。

**読む場所：** Hull： §31.5（p.728）。<a href="../31_ir_models.html#id3">Book：モデル分類図</a> ／ <a href="../../../../../MODEL_INDEX.md#p3-logic-first-private-models">実装・テスト：MODEL_INDEX P3 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch31.html#section-31-5">補足教材 §31.5</a>。

(model-forward-vol)=
### フォワード金利の変動

Finite-tenor forward-rate volatility。

**何を表すか：** 短期金利モデルから期間金利（年率）の変動へ換算します。

**仮定と限界：** 金利期間と正規/Black のボラ単位を明示します。短期金利の係数をそのまま代入しません。

**解き方・手順：** 割引債の比率と共分散からボラを求めます。

**使う場面：** 短期金利モデルと市場のボラ表示の比較。

**実装と検証の範囲：** 独立ブロック指数と短時間 MC を検証。

**読む場所：** Hull： §32.3（pp.737–738）。<a href="../31_ir_models.html#hjm-heath-jarrow-morton-1992">Book：3.1 HJM フレームワーク（Heath-Jarrow-Morton, 1992）</a> ／ <a href="../../../../../MODEL_INDEX.md#p3-logic-first-private-models">実装・テスト：MODEL_INDEX P3 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch32.html#section-32-3">補足教材 §32.3</a>。

(model-rate-tree)=
### 曲線に合わせた金利ツリー

Calibrated trinomial short-rate tree。

**何を表すか：** 金利のノードと状態価格、各満期の債券価値を扱います。

**仮定と限界：** 枝のモーメントと初期曲線を合わせます。年率と有限期間の複利換算をそろえます。

**解き方・手順：** 三項の枝を作り、各段のシフトで曲線に合わせ、割り引いて戻ります。

**使う場面：** 金利商品の途中行使。

**実装と検証の範囲：** 原典ノード、全経路列挙、Hull–White の解析価格と期間換算を検証。

**読む場所：** Hull： §32.4（pp.738–740）、§32.5（pp.740–750）。<a href="../31_ir_models.html#hullwhite-1990">Book：2.2 Hull–White モデル（1990）</a> ／ <a href="../../../../../MODEL_INDEX.md#p3-logic-first-private-models">実装・テスト：MODEL_INDEX P3 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch32.html#section-32-4">補足教材 §32.4</a>。

(model-outside-hedge)=
### モデル外の金利リスク

Outside-model rate and volatility shocks。

**何を表すか：** 一因子モデルの価格を、外から曲線・ボラを動かして再評価します。金額単位は通貨です。

**仮定と限界：** モデル内の因子だけでヘッジ可能とは仮定しません。外部ショックを明示します。

**解き方・手順：** 曲線・絶対ボラに対する解析微分と独立ガウス積分を比較します。

**使う場面：** 価格モデルが表さないリスク方向の把握。

**実装と検証の範囲：** PV01・ガンマ・片側ベガ等を検証。モデル外のショックの確率を推定したものではありません。

**読む場所：** Hull： §32.7（pp.751–752）。<a href="../31_ir_models.html#hullwhite-1990">Book：2.2 Hull–White モデル（1990）</a> ／ <a href="../../../../../MODEL_INDEX.md#p3-logic-first-private-models">実装・テスト：MODEL_INDEX P3 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch32.html#section-32-7">補足教材 §32.7</a>。

(model-hjm)=
### HJM

Heath–Jarrow–Morton forward-rate model（HJM）。

**何を表すか：** 満期ごとの瞬間フォワード金利（年率）の曲線を状態にします。

**仮定と限界：** 無裁定ドリフトがボラ構造で決まります。満期方向と時間方向の離散化も必要です。

**解き方・手順：** ボラの積分からドリフトを求め、曲線の SDE をシミュレートします。

**使う場面：** 曲線全体の動学と債券オプション。

**実装と検証の範囲：** 多因子の符号・独立債券価格/MC・履歴と同時点の金利の違いを検証。

**読む場所：** Hull： §33.1（pp.755–758）。<a href="../31_ir_models.html#hjm-heath-jarrow-morton-1992">Book：3.1 HJM フレームワーク（Heath-Jarrow-Morton, 1992）</a> ／ <a href="../../../../../MODEL_INDEX.md#p3-logic-first-private-models">実装・テスト：MODEL_INDEX P3 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch33.html#section-33-1">補足教材 §33.1</a>。

**関係：** [Hull–White 一因子](#model-hull-white) へ（[条件・出典](#map-relation-20)：特殊な場合）。

(model-lmm)=
### LIBOR 市場モデル

LIBOR market model / BGM（LMM・BGM）。

**何を表すか：** 各期間のフォワード金利（年率）の列を同時に動かします。

**仮定と限界：** 有限期間・支払測度・リセット日と単一曲線を指定します。現行 RFR の契約を自動で表すわけではありません。

**解き方・手順：** 期間金利 SDE、キャップの受払い、凍結近似のスワップションと PCA を使います。

**使う場面：** 市場のキャップ等と金利の相関構造。

**実装と検証の範囲：** private 単一曲線 LMM。原典 flexicap の strike・日付・MC 規約と sticky K0 が不足し、指定条件の検証を無条件の印刷値再現とは扱いません。

**読む場所：** Hull： §33.2（pp.758–768）。<a href="../31_ir_models.html#bgm-libor-market-model-brace-gatarek-musiela-1997">Book：3.2 BGM / LIBOR Market Model（Brace-Gatarek-Musiela, 1997）</a> ／ <a href="../../../../../MODEL_INDEX.md#p3-logic-first-private-models">実装・テスト：MODEL_INDEX P3 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch33.html#section-33-2">補足教材 §33.2</a>。

**関係：** [債券とゼロ曲線](#model-zero-curve) から（[条件・出典](#map-relation-22)：入力・較正）。

(model-mortgage)=
### 住宅ローンと CMO の受払い

Mortgage amortization and sequential CMO（CMO・OAS）。

**何を表すか：** ローン残高、返済、繰上返済、層ごとの元本（通貨）を追います。

**仮定と限界：** 返済と繰上返済の仮定を指定します。OAS はその仮定に依存します。

**解き方・手順：** 償還表と元本の配分を作り、曲線割引と条件付きスプレッドで評価します。

**使う場面：** MBS の金利リスクと繰上返済。

**実装と検証の範囲：** 独立な償還/PV・元本保存・ガウス割引 MC を検証。

**読む場所：** Hull： §33.3（pp.768–770）。<a href="../12_qualitative_summary.html#ch-8">Book：証券化の入口（CMOは補足教材§33.3）</a> ／ <a href="../../../../../MODEL_INDEX.md#p3-logic-first-private-models">実装・テスト：MODEL_INDEX P3 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch33.html#section-33-3">補足教材 §33.3</a>。

(model-nonstandard-legs)=
### 非標準のスワップ・レッグ

Nonstandard fixed, floating and RFR legs。

**何を表すか：** 日程ごとの元本、年分数、既知と未確定の金利、受払額を扱います。

**仮定と限界：** 休日暦と契約日程を固定します。既に決まった fixing を再予測しません。

**解き方・手順：** 契約の受払列を作り、独立な和・FRA 分解・日次積で確認します。

**使う場面：** 償還型・変則日程のスワップ。

**実装と検証の範囲：** 原典の契約条件と独立受払会計を検証。

**読む場所：** Hull： §34.1（pp.773–775）。<a href="../07_swaps.html#ch-34">Book：5. 非標準スワップの動物園（Ch.34）</a> ／ <a href="../../../../../MODEL_INDEX.md#p3-logic-first-private-models">実装・テスト：MODEL_INDEX P3 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch34.html#section-34-1">補足教材 §34.1</a>。

(model-compounding-swaps)=
### 複利スワップ

Compounding swaps。

**何を表すか：** 期間ごとの累積残高（通貨）を状態にします。

**仮定と限界：** 利息をいつ元本へ組み入れるか、支払時点を指定します。

**解き方・手順：** 成長係数の積と残高の再帰を計算し、確定・不確実な場合を比べます。

**使う場面：** 利息を繰り延べて複利で払う契約。

**実装と検証の範囲：** 独立な積・幾何級数・状態列挙を確認。近似と厳密な受払いを分けます。

**読む場所：** Hull： §34.2（pp.775–776）。<a href="../07_swaps.html#ch-34">Book：5. 非標準スワップの動物園（Ch.34）</a> ／ <a href="../../../../../MODEL_INDEX.md#p3-logic-first-private-models">実装・テスト：MODEL_INDEX P3 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch34.html#section-34-2">補足教材 §34.2</a>。

(model-cross-currency)=
### クロスカレンシー・スワップ

Cross-currency swaps。

**何を表すか：** 通貨ごとの元本とクーポン、為替レートを扱います。

**仮定と限界：** 通貨の向き・担保/曲線・ベーシスを指定します。単一の金利差で一般契約を表しません。

**解き方・手順：** 各レッグの価値と FX フォワードによる換算からスプレッドを解きます。

**使う場面：** 異通貨の資金と受払の交換。

**実装と検証の範囲：** 独立なレッグ和・為替先渡・CMS/時点/クオント調整を検証。

**読む場所：** Hull： §34.3（pp.776–777）。<a href="../07_swaps.html#id3">Book：4. 通貨スワップ（Ch.7）</a> ／ <a href="../../../../../MODEL_INDEX.md#p3-logic-first-private-models">実装・テスト：MODEL_INDEX P3 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch34.html#section-34-3">補足教材 §34.3</a>。

(model-equity-swaps)=
### 株式スワップ

Equity swaps。

**何を表すか：** 株式の総収益と金利レッグ、リセット後の元本（通貨）を扱います。

**仮定と限界：** 配当・リセット・未払決済と既知の金利をそろえます。

**解き方・手順：** 株式と資金の受払会計、残存期間の割引で評価します。

**使う場面：** 株式の収益と金利の交換。

**実装と検証の範囲：** 独立ガウス/銀行株式 MC・リセット後の残高・RFR 積を検証。

**読む場所：** Hull： §34.4（pp.777–779）。<a href="../07_swaps.html#id5">Book：7. エクイティスワップとキャンセラブル（Ch.34）</a> ／ <a href="../../../../../MODEL_INDEX.md#p3-logic-first-private-models">実装・テスト：MODEL_INDEX P3 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch34.html#section-34-4">補足教材 §34.4</a>。

(model-embedded-swaps)=
### スワップ内の選択権

Embedded options in swaps。

**何を表すか：** 金利状態と、取り消し等の権利、複利残高（通貨）を扱います。

**仮定と限界：** 誰がどの条件で取り消すか、必要な累積状態を指定します。

**解き方・手順：** バイナリの期待値と、取り消し/継続の後退帰納を使います。

**使う場面：** 解約可能スワップと金利条件付きクーポン。

**実装と検証の範囲：** 独立積分と全停止方策を比較。複利を含む完全状態と単純な proxy を区別します。

**読む場所：** Hull： §34.5（pp.779–781）。<a href="../07_swaps.html#id5">Book：7. エクイティスワップとキャンセラブル（Ch.34）</a> ／ <a href="../../../../../MODEL_INDEX.md#p3-logic-first-private-models">実装・テスト：MODEL_INDEX P3 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch34.html#section-34-5">補足教材 §34.5</a>。

(model-other-swaps)=
### 商品・変動元本のスワップ

Commodity, differential and index-amortizing swaps。

**何を表すか：** 商品価格、金利条件、適応的な元本と受払額を扱います。

**仮定と限界：** 契約ごとに単位と元本更新の時点を明記します。

**解き方・手順：** 受払いを列挙し、正部分の期待値や元本保存を確認します。

**使う場面：** 標準 IRS に収まらないスワップ契約。

**実装と検証の範囲：** 原典値・独立期待値/MC・元本の会計を検証。

**読む場所：** Hull： §34.6（pp.781–782）。<a href="../07_swaps.html#ch-34">Book：5. 非標準スワップの動物園（Ch.34）</a> ／ <a href="../../../../../MODEL_INDEX.md#p3-logic-first-private-models">実装・テスト：MODEL_INDEX P3 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch34.html#section-34-6">補足教材 §34.6</a>。

(model-forward-measure)=
### フォワード測度での評価

Forward-measure Black pricing。

**何を表すか：** 将来支払日の債券を基準に、フォワード価格と支払いを扱います。

**仮定と限界：** 支払日とニュメレールをそろえます。Q の割引済み平均と同じ式を無条件では使いません。

**解き方・手順：** 同じ給付を Q と支払時点の測度で積分し、価格の一致を見ます。

**使う場面：** 債券・金利オプションの市場モデルへの橋渡し。

**実装と検証の範囲：** 独立 Q/T 積分・生の MC・希少事象の重みを検証。

**読む場所：** Hull： §28.6（pp.680–681）。<a href="../10_exotics.html#e-black-28-6">Book：6E. Blackのモデルを測度から再訪（§28.6）</a> ／ <a href="../../../../../MODEL_INDEX.md#p3-logic-first-private-models">実装・テスト：MODEL_INDEX P3 logic-first private models</a>。

(model-futures-market)=
### 先物の値洗いと証拠金

Futures marking to market。

**何を表すか：** 契約倍率、値洗い、追加証拠金と現金（通貨）を時点ごとに扱います。

**仮定と限界：** 建値の変化と入出金の時点を区別します。先渡の一括決済とは資金の動きが違います。

**解き方・手順：** 日々の現金台帳と終価を独立に合計します。

**使う場面：** 先物の仕組みと会計。

**実装と検証の範囲：** 原典の表と独立累積収支を検証。

**読む場所：** Hull： §2.4（pp.51–54）。<a href="../04_futures_rates.html#ch-2">Book：1. 先物市場の仕組み（Ch.2 ダイジェスト）</a> ／ <a href="../../../../../MODEL_INDEX.md#p4-logic-first-private-models">実装・テスト：MODEL_INDEX P4 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch02.html#section-2-4">補足教材 §2.4</a>。

(model-forward-carry)=
### キャリーによる先渡価格

Cost-of-carry forward pricing。

**何を表すか：** 現物、借入れ、配当・保管費と将来の受渡価格を扱います。

**仮定と限界：** 資産を保有・空売りできる範囲や収入を指定します。消費財では便利利回り等の役割も残ります。

**解き方・手順：** 借入れと現物の複製会計から先渡価格と既存契約価値を求めます。

**使う場面：** 株式・通貨・商品の先渡と先物。

**実装と検証の範囲：** 原典例・独立受払/PV・数量の複製を検証。原典入力不足と丸め差は P6_STATUS に保持します。

**読む場所：** Hull： §5.4（pp.127–130）。<a href="../04_futures_rates.html#id6">Book：8. フォワード価格＝コストオブキャリー（§5.4–5.7, §5.11–5.12）</a> ／ <a href="../../../../../MODEL_INDEX.md#p4-logic-first-private-models">実装・テスト：MODEL_INDEX P4 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch05.html#section-5-4">補足教材 §5.4</a>。

**関係：** [Black の市場モデル](#model-black76) へ（[条件・出典](#map-relation-5)：入力・較正）。

(model-rate-futures)=
### 金利先物とデュレーション・ヘッジ

Interest-rate futures and duration hedging。

**何を表すか：** 債券の建値、変換係数、金利と契約数量を扱います。

**仮定と限界：** 日数、受渡日、最割安銘柄と商品ごとの建値単位を指定します。

**解き方・手順：** 価格換算・受渡会計・割引因子列と再評価で確認します。

**使う場面：** 債券・短期金利先物によるヘッジ。

**実装と検証の範囲：** 原典の価格/受渡例と独立な有理数会計・年金式・融資台帳を検証。

**読む場所：** Hull： §6.1（pp.152–154）。<a href="../04_futures_rates.html#id10">Book：11. 金利先物によるデュレーションヘッジ（§6.3–6.4）</a> ／ <a href="../../../../../MODEL_INDEX.md#p4-logic-first-private-models">実装・テスト：MODEL_INDEX P4 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch06.html#section-6-1">補足教材 §6.1</a>。

## 信用：構造型・強度型・コピュラ・XVA

損失が起きる時刻と額、相手との依存、損失の受払順位を別々に考えます。証券化は配分の規則で、デフォルト確率を作るモデルとは役割が異なります。

(model-securitization)=
### 証券化の損失配分

ABS and ABS-CDO loss waterfalls。

**何を表すか：** 原資産と各トランシェの元本・損失（通貨、または元本に対する割合）を扱います。

**仮定と限界：** 支払いの優先順と損失の分母を固定します。配分規則だけではデフォルト確率は分かりません。

**解き方・手順：** 元本の層を下から使い切る会計と、二段の再証券化を計算します。

**使う場面：** 損失がどこへ届くかの理解。

**実装と検証の範囲：** 原典の損失表と独立なドル損失の保存を検証。格付けの再現や保証ではありません。

**読む場所：** Hull： §8.1（pp.201–205）。<a href="../12_qualitative_summary.html#ch-8">Book：2. 証券化と金融危機（Ch.8）</a> ／ <a href="../../../../../MODEL_INDEX.md#p4-logic-first-private-models">実装・テスト：MODEL_INDEX P4 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch08.html#section-8-1">補足教材 §8.1</a>。

[Ch8のガイド](ch08.md)から説明を読み直せます。

**関係：** [CDO・第 k デフォルトと相関](#model-cdo) へ（[条件・出典](#map-relation-25)：入力・較正）。

(model-hazard)=
### ハザード曲線

Hazard-rate curves and credit bootstraps。

**何を表すか：** 生存確率（無次元）と区分的なハザード率（年の逆数）を扱います。

**仮定と限界：** 回収率とデフォルト時の支払い、P/Q を指定します。スプレッドからの逆算には仮定が必要です。

**解き方・手順：** 生存確率を積分し、債券やスプレッドから順にハザードを求めます。

**使う場面：** 信用曲線と単一名 CDS 評価の入力。

**実装と検証の範囲：** 原典例・債券損失の現在価値・価格の往復を検証。

**読む場所：** Hull の前提： §24.4（pp.564–566）。<a href="../28_credit_desk.html#vs-hull-ex-24-2">Book：債券価格ブートストラップ vs Hull Ex 24.2</a> ／ <a href="../../../../../MODEL_INDEX.md#6-risk--credit-var-cds-xva-copula">実装・テスト：MODEL_INDEX 6</a> ／ <a href="../../../../../report/site/chapters/ch24.html#section-24-4">補足教材 §24.4</a>。

**関係：** [単一名 CDS](#model-cds) へ（[条件・出典](#map-relation-23)：入力・較正）。

(model-merton-default)=
### Merton 構造型デフォルト

Merton structural credit model。

**何を表すか：** 企業資産価値と負債の境界（通貨）から満期のデフォルトを定めます。

**仮定と限界：** 資産の対数正規性と単純な負債構造を仮定します。市場で資産価値を直接観測できるとは限りません。

**解き方・手順：** 企業株式をコールとして考え、終値分布とデフォルト確率を求めます。

**使う場面：** 企業価値と株式・信用のつながり。

**実装と検証の範囲：** 原典値・独立積分/ODE/MC と d2 の規約を検証。P と Q の確率を混ぜません。

**読む場所：** Hull： §24.6（pp.570–571）。<a href="../09_credit_xva.html#merton-ch-24">Book：3. Merton 構造モデル（Ch.24）</a> ／ <a href="../../../../../MODEL_INDEX.md#6-risk--credit-var-cds-xva-copula">実装・テスト：MODEL_INDEX 6</a> ／ <a href="../../../../../MODEL_INDEX.md#p4-logic-first-private-models">実装・テスト：MODEL_INDEX P4 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch24.html#section-24-6">補足教材 §24.6</a>。

(model-credit-copula)=
### Vasicek 信用損失とコピュラ

Vasicek portfolio losses and Gaussian/double-t copulas。

**何を表すか：** 個別 PD、共通因子と損失割合（無次元）を扱います。

**仮定と限界：** 依存構造と回収を指定します。同じ相関でも分布族が違えば裾は変わります。

**解き方・手順：** 条件付きデフォルト確率から損失分布を積分・標本化します。

**使う場面：** 多数の借り手が同時に傷むリスク。

**実装と検証の範囲：** 平均損失・独立 t/normal MC・状態列挙と較正の非一意性を検証。短期金利の Vasicek とは別です。

**読む場所：** Hull： §24.8（pp.577–580）、§25.11（pp.608–610）。<a href="../09_credit_xva.html#id1">Book：4. デフォルト相関とガウスコピュラ（Ch.24）</a> ／ <a href="../../../../../MODEL_INDEX.md#6-risk--credit-var-cds-xva-copula">実装・テスト：MODEL_INDEX 6</a> ／ <a href="../../../../../MODEL_INDEX.md#p4-logic-first-private-models">実装・テスト：MODEL_INDEX P4 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch24.html#section-24-8">補足教材 §24.8</a>。

**関係：** [CDO・第 k デフォルトと相関](#model-cdo) へ（[条件・出典](#map-relation-24)：入力・較正）。

(model-xva)=
### エクスポージャと XVA

Exposure, netting, collateral and XVA（XVA）。

**何を表すか：** 取引価値と担保、正のエクスポージャ、資金費用（通貨）を扱います。

**仮定と限界：** 相手と自分のデフォルト、回収、依存、担保の時間差と符号を定めます。

**解き方・手順：** EE/PFE を作り、デフォルト時損失や資金費用の期待値を割り引きます。

**使う場面：** CVA/DVA/FVA と取引の増分リスク。

**実装と検証の範囲：** 独立積分/MC・担保/ネッティング・資金会計を検証。調整の単純な合算で二重計上が消えるとは限りません。

**読む場所：** Hull の前提： §9.1（pp.216–219）、§24.7（pp.571–577）。<a href="../16_xva_credit.html#cva-dva-fva">Book：2. CVA / DVA / FVA</a> ／ <a href="../../../../../MODEL_INDEX.md#6-risk--credit-var-cds-xva-copula">実装・テスト：MODEL_INDEX 6</a> ／ <a href="../../../../../MODEL_INDEX.md#p4-logic-first-private-models">実装・テスト：MODEL_INDEX P4 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch09.html#section-9-1">補足教材 §9.1</a>。

(model-cds)=
### 単一名 CDS

Single-name credit default swaps（CDS）。

**何を表すか：** 保険料レッグと信用事由時の支払額（通貨）を扱います。

**仮定と限界：** 年分数、未払利息、デフォルト/回収時点を指定します。

**解き方・手順：** 二つのレッグの現在価値を合わせ、パー・スプレッド、MTM、前払金等を求めます。

**使う場面：** 信用リスクの移転、曲線の較正。

**実装と検証の範囲：** 原典の全対象表・独立受払/求積/MC・オプションのパリティを検証。

**読む場所：** Hull の前提： §25.2（pp.591–595）、§25.5（p.597）。<a href="../28_credit_desk.html#cds-pv-table-25-3-vs-25-4">Book：CDS レッグの年別 PV（Table 25.3 vs 25.4）</a> ／ <a href="../../../../../MODEL_INDEX.md#6-risk--credit-var-cds-xva-copula">実装・テスト：MODEL_INDEX 6</a> ／ <a href="../../../../../MODEL_INDEX.md#p4-logic-first-private-models">実装・テスト：MODEL_INDEX P4 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch25.html#section-25-2">補足教材 §25.2</a>。

**関係：** [ハザード曲線](#model-hazard) から（[条件・出典](#map-relation-23)：入力・較正）。

(model-cdo)=
### CDO・第 k デフォルトと相関

Synthetic CDO and kth-to-default valuation（CDO）。

**何を表すか：** デフォルト数・損失とトランシェ元本（通貨）を扱います。

**仮定と限界：** 依存モデル、回収、支払時点を固定します。相関は商品の観測価格に依存した較正量にもなります。

**解き方・手順：** 一因子求積、異質な借り手の再帰、受払列から価格を求めます。

**使う場面：** トランシェ、バスケット CDS、base/compound correlation。

**実装と検証の範囲：** 原典表・独立状態列挙/デフォルト時刻 MC・損失保存を検証。相関の一つの数値で全構造を決めません。

**読む場所：** Hull の前提： §25.6（p.597）、§25.8（pp.599–601）、§25.10（pp.601–608）。<a href="../28_credit_desk.html#vs">Book：標準トランシェのブレークイーブンスプレッド vs ρ</a> ／ <a href="../../../../../MODEL_INDEX.md#6-risk--credit-var-cds-xva-copula">実装・テスト：MODEL_INDEX 6</a> ／ <a href="../../../../../MODEL_INDEX.md#p4-logic-first-private-models">実装・テスト：MODEL_INDEX P4 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch25.html#section-25-6">補足教材 §25.6</a>。

**関係：** [Vasicek 信用損失とコピュラ](#model-credit-copula) から（[条件・出典](#map-relation-24)：入力・較正）。[証券化の損失配分](#model-securitization) から（[条件・出典](#map-relation-25)：入力・較正）。

(model-creditmetrics)=
### CreditMetrics

Rating-transition credit VaR。

**何を表すか：** 格付けの遷移状態と、遷移後の債券価値・損失（通貨）を扱います。

**仮定と限界：** 遷移確率・相関と遷移後の価格条件を固定します。デフォルトだけを数えるモデルとは異なります。

**解き方・手順：** 潜在変数を閾値で格付けへ写し、損失分布を作ります。

**使う場面：** 格下げも含めた信用 VaR。

**実装と検証の範囲：** 原典閾値・デフォルト頻度・相関による裾の変化を検証。

**読む場所：** Hull の前提： §24.9（pp.580–582）。<a href="../28_credit_desk.html#creditmetrics-aaa-vs-bbb-table-24-4-6">Book：CreditMetrics 閾値：AAA vs BBB（Table 24.4、生存格付間の 6 境界）</a> ／ <a href="../../../../../MODEL_INDEX.md#6-risk--credit-var-cds-xva-copula">実装・テスト：MODEL_INDEX 6</a> ／ <a href="../../../../../report/site/chapters/ch24.html#section-24-9">補足教材 §24.9</a>。

## リスク計量：VaR・EWMA・GARCH

価格を整合させる Q の評価から、損失を予測し検証する仕事へ視点を替えます。期間、損失の符号、確率の水準、分散の単位がそろっているかを確認します。

(model-var-es)=
### VaR と期待ショートフォール

Historical and normal VaR/ES（VaR・ES）。

**何を表すか：** 指定期間のポートフォリオ損失（通貨）の分布を扱います。

**仮定と限界：** 損失の符号、期間、確率水準と分位点/裾平均の標本規約を指定します。

**解き方・手順：** 履歴シナリオまたは正規分布の式から分位点と裾平均を求めます。

**使う場面：** 市場損失の集約と比較。

**実装と検証の範囲：** 原典値と独立積分・シミュレーション・非線形再評価を検証。将来の裾を保証するものではありません。

**読む場所：** Hull： §22.1（pp.514–517）、§22.2（pp.517–521）。<a href="../08_risk_var.html#ch-22">Book：1. 定義（Ch.22）</a> ／ <a href="../../../../../MODEL_INDEX.md#6-risk--credit-var-cds-xva-copula">実装・テスト：MODEL_INDEX 6</a> ／ <a href="../../../../../MODEL_INDEX.md#p4-logic-first-private-models">実装・テスト：MODEL_INDEX P4 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch22.html#section-22-1">補足教材 §22.1</a>。

(model-var-backtest)=
### VaR バックテスト

Kupiec and Christoffersen backtests。

**何を表すか：** VaR を超えた日の指示変数（無次元）と超過の並びを扱います。

**仮定と限界：** 帰無仮説と標本期間を定めます。少数の超過から高い精度は得られません。

**解き方・手順：** 超過率・独立性の尤度比を求め、歴史的な規制ゾーンの例と分けて読みます。

**使う場面：** リスク予測を事後に点検する方法。

**実装と検証の範囲：** 手計算の尤度比と検定間の恒等式を検証。現行規制の適用認定ではありません。

**読む場所：** Hull の前提： §22.8（p.534）。<a href="../27_risk_desk.html#kupiec-pof-size-study-nominal-5">Book：Kupiec POF size study（nominal 5%）</a> ／ <a href="../../../../../MODEL_INDEX.md#6-risk--credit-var-cds-xva-copula">実装・テスト：MODEL_INDEX 6</a> ／ <a href="../../../../../report/site/chapters/ch22.html#section-22-8">補足教材 §22.8</a>。

(model-tail-risk)=
### FHS と EVT の裾

Filtered historical simulation and EVT/GPD（FHS・EVT・GPD）。

**何を表すか：** 変動で標準化した損失、閾値を超える損失（通貨または標準化単位）を扱います。

**仮定と限界：** 分散フィルターと裾の閾値・分布仮定を指定します。裾の標本不足に敏感です。

**解き方・手順：** FHS で標本を再尺度化し、GPD で超過の裾を当てはめます。

**使う場面：** 非正規のリスク量とストレス。

**実装と検証の範囲：** 一定分散・指数裾等の極限と独立分位点/求積を検証。

**読む場所：** Hull の前提： §22.2（pp.517–521）。<a href="../27_risk_desk.html#evt-vs-var-ladder">Book：EVT vs 経験 VaR ladder</a> ／ <a href="../../../../../MODEL_INDEX.md#6-risk--credit-var-cds-xva-copula">実装・テスト：MODEL_INDEX 6</a> ／ <a href="../../../../../report/site/chapters/ch22.html#section-22-2">補足教材 §22.2</a>。

(model-risk-allocation)=
### リスク量の分解

Euler marginal, component and incremental risk。

**何を表すか：** 全体の VaR/ES とポジション別の寄与（通貨）を扱います。

**仮定と限界：** 同次性や微分の条件と、同値の損失標本の扱いを指定します。

**解き方・手順：** 限界寄与・Euler 分解・追加前後の差を区別します。

**使う場面：** リスク限度や資本の配賦。

**実装と検証の範囲：** 寄与の合計・独立差分・裾の同値行を検証。増分と限界を同じ量と呼びません。

**読む場所：** Hull の前提： §22.1（pp.514–517）。<a href="../27_risk_desk.html#component-vs-incremental-var">Book：component vs incremental VaR</a> ／ <a href="../../../../../MODEL_INDEX.md#6-risk--credit-var-cds-xva-copula">実装・テスト：MODEL_INDEX 6</a> ／ <a href="../../../../../report/site/chapters/ch22.html#section-22-1">補足教材 §22.1</a>。

(model-pnl-explain)=
### 損益の説明とリミット

P&L explain and limit monitoring。

**何を表すか：** 因子の変化、感応度、再評価損益（通貨）を並べます。

**仮定と限界：** 近似に含める因子と二次項を明記します。残差の原因を一つに決めつけません。

**解き方・手順：** デルタ・ガンマ・ベガの寄与と full revaluation を比較します。

**使う場面：** デスクの損益説明と限度の監視。

**実装と検証の範囲：** 線形/二次の厳密例と BSM の残差収束を検証。交差ガンマは対象外です。

**読む場所：** Hull の前提： §22.5（pp.530–533）。<a href="../27_risk_desk.html#p-l-explain-delta-gamma-vega">Book：P&amp;L explain：delta-gamma-vega 分解</a> ／ <a href="../../../../../MODEL_INDEX.md#6-risk--credit-var-cds-xva-copula">実装・テスト：MODEL_INDEX 6</a> ／ <a href="../../../../../report/site/chapters/ch22.html#section-22-5">補足教材 §22.5</a>。

(model-ewma)=
### EWMA 分散・共分散

Exponentially weighted moving-average variance（EWMA）。

**何を表すか：** 収益率と条件付き分散・共分散（同じ時間単位の収益率の二乗）を扱います。

**仮定と限界：** 減衰率と観測頻度を固定します。一定の長期分散へ戻す項はありません。

**解き方・手順：** 前回の分散と最新の二乗収益率を重み付きで更新します。

**使う場面：** 変動の変化に追随するリスク推定。

**実装と検証の範囲：** 原典値・日次/年率・独立な更新と共分散を検証。Q の価格ボラと同一ではありません。

**読む場所：** Hull： §23.2（pp.544–546）。<a href="../05_vol_smile.html#ewma-ch-23eq-23-3-23-7">Book：6. ヒストリカル・ボラティリティと EWMA（Ch.23、eq 23.3, 23.7）</a> ／ <a href="../../../../../MODEL_INDEX.md#2-volatility--smile">実装・テスト：MODEL_INDEX 2</a> ／ <a href="../../../../../MODEL_INDEX.md#p4-logic-first-private-models">実装・テスト：MODEL_INDEX P4 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch23.html#section-23-2">補足教材 §23.2</a>。

**関係：** [GARCH 分散](#model-garch) から（[条件・出典](#map-relation-16)：特殊な場合）。[古典的な変動予測](#model-classical-forecast) へ（[条件・出典](#map-relation-17)：入力・較正）。

(model-garch)=
### GARCH 分散

Generalized autoregressive conditional heteroskedasticity（GARCH）。

**何を表すか：** 収益率のショックと条件付き分散を扱います。分散の単位は観測間隔に従います。

**仮定と限界：** 係数の正値性と長期分散の存在条件を確認します。

**解き方・手順：** 定数、最新の二乗ショック、前回分散から更新し、推定・予測を行います。

**使う場面：** 長期水準への復帰を持つ分散予測。

**実装と検証の範囲：** 長期分散・期間構造・推定を検証。定常性を失う境界は定常モデルと区別します。

**読む場所：** Hull： §23.3（pp.546–547）、§23.5（pp.548–553）、§23.6（pp.553–556）。<a href="../05_vol_smile.html#garch-1-1-ch-23eq-23-823-9">Book：7. GARCH(1,1)（Ch.23、eq 23.8–23.9）</a> ／ <a href="../../../../../MODEL_INDEX.md#2-volatility--smile">実装・テスト：MODEL_INDEX 2</a> ／ <a href="../../../../../MODEL_INDEX.md#p4-logic-first-private-models">実装・テスト：MODEL_INDEX P4 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch23.html#section-23-3">補足教材 §23.3</a>。

**関係：** [EWMA 分散・共分散](#model-ewma) へ（[条件・出典](#map-relation-16)：特殊な場合）。

(model-futures-hedging)=
### 最小分散の先物ヘッジ

Minimum-variance futures hedging。

**何を表すか：** 現物と先物の価格変化（各建値）と、保有する契約数量を扱います。

**仮定と限界：** 相関と変動の標本期間、建値・契約倍率を指定します。

**解き方・手順：** 共分散と回帰からヘッジ比率を求め、現金の損益を確認します。

**使う場面：** ベーシス・リスク、株価指数のベータ・ヘッジ。

**実装と検証の範囲：** 独立 OLS・分散最小化・受払会計を検証。将来も同じ相関が続く保証ではありません。

**読む場所：** Hull： §3.3（pp.75–79）。<a href="../04_futures_rates.html#id1">Book：2. 先物によるヘッジとベーシスリスク（§3.1–3.3）</a> ／ <a href="../../../../../MODEL_INDEX.md#p4-logic-first-private-models">実装・テスト：MODEL_INDEX P4 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch03.html#section-3-3">補足教材 §3.3</a>。

(model-market-risk-price)=
### リスクの市場価格

One- and multi-factor market prices of risk。

**何を表すか：** 因子への符号つき負荷と超過期待収益（年率）を結び付けます。

**仮定と限界：** 取引可能性、局所ヘッジと因子の向きを指定します。価格が付かない因子もあります。

**解き方・手順：** 一因子の収益/負荷、多因子の寄与と局所複製を比べます。

**使う場面：** P の期待収益と Q の評価の接続。

**実装と検証の範囲：** 原典例・独立ガウス積分・SVD ヘッジを検証。

**読む場所：** Hull： §28.1（pp.671–674）、§28.2（pp.674–675）。<a href="../10_exotics.html#id80">Book：6. 市場リスクの価格 λ（§28.1）</a> ／ <a href="../../../../../MODEL_INDEX.md#7-exotics--martingales">実装・テスト：MODEL_INDEX 7</a>。

(model-mishap-statistics)=
### 連勝と集中の算術

Streak probabilities and equal-correlation portfolios。

**何を表すか：** 連勝の指示変数と、等重みポートフォリオの分散（収益率の二乗）を扱います。

**仮定と限界：** 独立試行または等相関などの単純化を明記します。

**解き方・手順：** 二項列挙と共分散の和を独立に計算します。

**使う場面：** 偶然の好成績と分散したつもりの集中を見分ける入口。

**実装と検証の範囲：** 原典の算術と固定 seed MC を検証。組織統制・不正防止の完全なモデルではありません。

**読む場所：** Hull： §37.1（pp.815–819）。<a href="../12_qualitative_summary.html#ch-37">Book：6. デリバティブの失敗事例（Ch.37）</a> ／ <a href="../../../../../MODEL_INDEX.md#p4-logic-first-private-models">実装・テスト：MODEL_INDEX P4 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch37.html#section-37-1">補足教材 §37.1</a>。

## Beyond Hull：学習・新市場・事業

価格計算を学習する方法と、予測やヘッジの意思決定、非完備な市場の契約へ広げます。教師の誤差、学習外の入力、合成データという制限をカードごとに確かめます。

(model-teacher-data)=
### 誤差つきの教師データ

Pricing teachers with Monte Carlo uncertainty。

**何を表すか：** 価格（通貨）、グリークスと教師の標準誤差をデータとして持ちます。

**仮定と限界：** 教師も近似です。共通乱数による相関と独立な検証を区別します。

**解き方・手順：** 解析式・COS・MC で価格を作り、誤差を評価します。

**使う場面：** 価格近似を学習する前のデータ作り。

**実装と検証の範囲：** BSM/Heston の比較と MC の標準誤差を検証。rBergomi は有限格子の教師であり連続時間の厳密解ではありません。

**読む場所：** Hull の前提： §21.5（pp.488–489）。<a href="../18_ml_surrogates.html#artifactdata-policy">Book：Artifact契約とdata policy</a> ／ <a href="../../../../../MODEL_INDEX.md#8-ml-surrogates--differential-machine-learning">実装・テスト：MODEL_INDEX 8</a> ／ <a href="../../../../../report/site/chapters/ch21.html#section-21-5">補足教材 §21.5</a>。

**関係：** [価格サロゲートと DML](#model-pricing-surrogate) へ（[条件・出典](#map-relation-26)：入力・較正）。[ブラック＝ショールズ＝マートン](#model-bsm) から（[条件・出典](#map-relation-27)：入力・較正）。

(model-hard-validation)=
### 無裁定の事後検証

Hard no-arbitrage validation。

**何を表すか：** 学習した価格（通貨）の上下限・パリティ・曲率等を点検します。

**仮定と限界：** チェックした範囲と入力格子を明示します。個別のチェックだけで無裁定を宣言しません。

**解き方・手順：** 独立した検査集合を価格器へ適用します。

**使う場面：** サロゲートの結果を受け取る前の点検。

**実装と検証の範囲：** 完全な検査集合が通った範囲で判定。未検査の入力全体を保証しません。

**読む場所：** Hull の前提： §11.3（pp.252–254）。<a href="../18_ml_surrogates.html#run">Book：価格のみの近似器と採用runの無裁定違反</a> ／ <a href="../../../../../MODEL_INDEX.md#8-ml-surrogates--differential-machine-learning">実装・テスト：MODEL_INDEX 8</a> ／ <a href="../../../../../report/site/chapters/ch11.html#section-11-3">補足教材 §11.3</a>。

(model-dataset-artifacts)=
### 固定したデータと参照成果物

Fingerprinted datasets and reference artifacts。

**何を表すか：** 入力・教師・分割・結果の配列とハッシュを扱います。単位は各データ列で保持します。

**仮定と限界：** 同一性の確認と金融上の正しさを分けます。署名やフラグだけを合格の根拠にしません。

**解き方・手順：** 分割の重複と指紋を確認し、保存配列から受入指標を再計算します。

**使う場面：** 再現可能な学習・教材の配布。

**実装と検証の範囲：** データ改変の検出と再計算の契約を検証。金融モデル自体とは別の検証手順です。

**読む場所：** Hull の前提： §21.5（pp.488–489）。<a href="../18_ml_surrogates.html#artifactdata-policy">Book：Artifact契約とdata policy</a> ／ <a href="../../../../../MODEL_INDEX.md#8-ml-surrogates--differential-machine-learning">実装・テスト：MODEL_INDEX 8</a> ／ <a href="../../../../../MODEL_INDEX.md#9-inverse-problems--arbitrage-aware-surfaces">実装・テスト：MODEL_INDEX 9</a> ／ <a href="../../../../../report/site/chapters/ch21.html#section-21-5">補足教材 §21.5</a>。

(model-pricing-surrogate)=
### 価格サロゲートと DML

Neural pricing surrogate and differential learning（DML）。

**何を表すか：** 価格入力から価格（通貨）とグリークスを近似する関数を学習します。

**仮定と限界：** 教師と学習範囲を固定します。学習外の入力や不連続な給付には別の点検が必要です。

**解き方・手順：** 価格のみ・複数出力・微分損失を同じ分割で比べます。

**使う場面：** 高価な教師を繰り返し呼ぶ場面の近似。

**実装と検証の範囲：** 値/微分・速度・無裁定・合成範囲を別々に検証。torch 実装は deep_hedge_price 側です。

**読む場所：** Hull の前提： §15.6（pp.348–351）、§19.4（pp.421–427）。<a href="../18_ml_surrogates.html#id7">Book：価格誤差サーフェス</a> ／ <a href="../../../../../MODEL_INDEX.md#8-ml-surrogates--differential-machine-learning">実装・テスト：MODEL_INDEX 8</a> ／ <a href="../../../../../report/site/chapters/ch15.html#section-15-6">補足教材 §15.6</a>。

**関係：** [誤差つきの教師データ](#model-teacher-data) から（[条件・出典](#map-relation-26)：入力・較正）。

(model-soft-penalty)=
### ソフトな無裁定制約

Soft arbitrage penalties。

**何を表すか：** 価格の違反量と学習損失を扱います。価格は通貨、損失の尺度は設定に依存します。

**仮定と限界：** 罰則の重みを増やしても制約を厳密に満たすとは限りません。

**解き方・手順：** 価格境界や曲率の違反を損失へ加え、別の hard check で測ります。

**使う場面：** 学習精度と制約違反の比較。

**実装と検証の範囲：** 罰則前後の違反量を報告。hard な射影と同等とは扱いません。

**読む場所：** Hull の前提： §11.3（pp.252–254）。<a href="../18_ml_surrogates.html#run">Book：価格のみの近似器と採用runの無裁定違反</a> ／ <a href="../../../../../MODEL_INDEX.md#8-ml-surrogates--differential-machine-learning">実装・テスト：MODEL_INDEX 8</a> ／ <a href="../../../../../report/site/chapters/ch11.html#section-11-3">補足教材 §11.3</a>。

(model-ablation)=
### 条件をそろえた比較

Seeded ablation protocol。

**何を表すか：** 学習条件と seed ごとの指標・計算費用を扱います。

**仮定と限界：** 同じ分割・教師・計算予算をそろえます。良い seed だけを選びません。

**解き方・手順：** 要素を替えた比較を固定し、負の結果も記録します。

**使う場面：** サロゲートの改善がどこから来たかの検証。

**実装と検証の範囲：** CPU の保存済み参照で比較を再現。価格モデルそのものではありません。

**読む場所：** Hull の前提： §21.5（pp.488–489）。<a href="../18_ml_surrogates.html#negative-results">Book：限界とnegative results</a> ／ <a href="../../../../../MODEL_INDEX.md#8-ml-surrogates--differential-machine-learning">実装・テスト：MODEL_INDEX 8</a> ／ <a href="../../../../../report/site/chapters/ch21.html#section-21-5">補足教材 §21.5</a>。

(model-two-step-calibration)=
### サロゲートを使う二段階較正

Two-step calibration with a forward surrogate。

**何を表すか：** 市場の価格/IV とモデルパラメーターを結ぶ逆問題を扱います。

**仮定と限界：** 順方向の近似誤差と最適化の非一意性を分けます。

**解き方・手順：** サロゲートの再価格を目的関数にし、初期値を変えて最適化します。

**使う場面：** 価格計算の高い較正。

**実装と検証の範囲：** 再価格残差と開始点によるばらつきを検証。直接逆写像の ridge 基準もあり、逆 NN が唯一の推奨という意味ではありません。

**読む場所：** Hull の前提： §32.6（pp.749–751）。<a href="../19_inverse_surfaces.html#multi-start-parameter-repricing-rmse">Book：multi-start parameter/repricing RMSE</a> ／ <a href="../../../../../MODEL_INDEX.md#9-inverse-problems--arbitrage-aware-surfaces">実装・テスト：MODEL_INDEX 9</a> ／ <a href="../../../../../report/site/chapters/ch32.html#section-32-6">補足教材 §32.6</a>。

(model-teacher-surfaces)=
### Heston・SABR・rBergomi の教師面

Teacher implied-volatility surfaces。

**何を表すか：** パラメーターと満期/行使価格ごとの IV・分散期間構造を扱います。

**仮定と限界：** 教師モデル・有限格子と誤差を明示します。表を作ることと順方向サロゲートを学習することは違います。

**解き方・手順：** 各教師の評価器から価格を作り、IV へ逆算します。

**使う場面：** 面からモデルを識別する教材。

**実装と検証の範囲：** 価格面と分散期間構造の目的のトレードオフを比較。rBergomi は有限格子です。

**読む場所：** Hull の前提： §20.5（pp.458–460）、§27.2（pp.646–649）。<a href="../19_inverse_surfaces.html#clean-teacherhard-constrained-fit">Book：clean teacher価格とhard-constrained fit</a> ／ <a href="../../../../../MODEL_INDEX.md#9-inverse-problems--arbitrage-aware-surfaces">実装・テスト：MODEL_INDEX 9</a> ／ <a href="../../../../../report/site/chapters/ch20.html#section-20-5">補足教材 §20.5</a>。

(model-walk-forward)=
### 時系列分割と前処理

Purged walk-forward splits and train-window transforms。

**何を表すか：** 時刻つきの説明変数と将来の予測対象を扱います。

**仮定と限界：** 予測期間が重なる標本と学習窓を明示します。将来のデータで標準化しません。

**解き方・手順：** purge/embargo と学習窓だけの標準化・PCA を使います。

**使う場面：** リークを防ぐ変動予測の比較。

**実装と検証の範囲：** 期間の重なり・学習範囲・変換の fit を検証。金融上の予測モデルとは別の実験手順です。

**読む場所：** Hull の前提： §23.1（pp.542–544）。<a href="../20_surface_dynamics.html#walk-forward-rv-forecast">Book：walk-forward RV forecast</a> ／ <a href="../../../../../MODEL_INDEX.md#10-surface-dynamics-forecasting--hedging-decisions">実装・テスト：MODEL_INDEX 10</a> ／ <a href="../../../../../report/site/chapters/ch23.html#section-23-1">補足教材 §23.1</a>。

(model-classical-forecast)=
### 古典的な変動予測

Persistence, EWMA/GARCH and Log-HAR forecasts。

**何を表すか：** 日次等の実現分散・対数分散を予測します。単位と年率換算はデータに合わせます。

**仮定と限界：** 過去の情報だけを使い、対数から戻すときの補正を定めます。

**解き方・手順：** 持続性、EWMA/GARCH、異なる期間の情報を使う Log-HAR を比較します。

**使う場面：** ニューラル予測の前に置く基準。

**実装と検証の範囲：** Log-HAR を必須の基準とし、学習残差による smearing を検証。Q の価格予測ではありません。

**読む場所：** Hull の前提： §23.2（pp.544–546）、§23.3（pp.546–547）、§23.6（pp.553–556）。<a href="../20_surface_dynamics.html#walk-forward-rv-forecast">Book：walk-forward RV forecast</a> ／ <a href="../../../../../MODEL_INDEX.md#10-surface-dynamics-forecasting--hedging-decisions">実装・テスト：MODEL_INDEX 10</a> ／ <a href="../../../../../report/site/chapters/ch23.html#section-23-2">補足教材 §23.2</a>。

**関係：** [EWMA 分散・共分散](#model-ewma) から（[条件・出典](#map-relation-17)：入力・較正）。

(model-neural-forecast)=
### ニューラル時系列予測

HARNet, TCN, LSTM and Transformer challengers。

**何を表すか：** 過去の特徴の列から将来の変動指標を予測します。

**仮定と限界：** 学習期間・予測期間とネットワーク容量をそろえます。将来の regime を知っている前提にしません。

**解き方・手順：** 系列モデルを学習し、古典的な基準と時系列分割で比べます。

**使う場面：** 変動予測の挑戦モデル。

**実装と検証の範囲：** QLIKE/RMSE/MAE と block bootstrap を報告。勝者や市場収益を既定にしたものではありません。

**読む場所：** Hull の前提： §23.1（pp.542–544）。<a href="../20_surface_dynamics.html#qlikermse">Book：4モデルの予測誤差：QLIKEとRMSE</a> ／ <a href="../../../../../MODEL_INDEX.md#10-surface-dynamics-forecasting--hedging-decisions">実装・テスト：MODEL_INDEX 10</a> ／ <a href="../../../../../report/site/chapters/ch23.html#section-23-1">補足教材 §23.1</a>。

(model-forecast-metrics)=
### 予測指標と不確実性

Forecast losses and block-bootstrap intervals。

**何を表すか：** 予測誤差と指標（各尺度の単位）、連続する誤差の列を扱います。

**仮定と限界：** 比較する対象とスケール、時間依存を保つブロックを指定します。

**解き方・手順：** QLIKE 等の損失を計算し、ブロックで再標本化して区間を求めます。

**使う場面：** 予測手法の差を評価する場面。

**実装と検証の範囲：** 期間/状態ごとの集計と不確実性を確認。単一の平均指標で全局面の優劣は決めません。

**読む場所：** Hull の前提： §23.1（pp.542–544）。<a href="../20_surface_dynamics.html#qlikermse">Book：4モデルの予測誤差：QLIKEとRMSE</a> ／ <a href="../../../../../MODEL_INDEX.md#10-surface-dynamics-forecasting--hedging-decisions">実装・テスト：MODEL_INDEX 10</a> ／ <a href="../../../../../report/site/chapters/ch23.html#section-23-1">補足教材 §23.1</a>。

(model-feature-diagnostics)=
### 特徴・attention の診断

Feature and attention diagnostics。

**何を表すか：** 特徴を崩したときの予測変化や勾配、順位を扱います。

**仮定と限界：** 診断が示す関連と因果説明を分けます。attention の値だけを説明とみなしません。

**解き方・手順：** 置換、遮蔽、積分勾配など複数の方法で順位の安定性を比べます。

**使う場面：** 学習した時系列モデルの点検。

**実装と検証の範囲：** 方法間の一致と不安定性を報告。説明可能性の保証ではありません。

**読む場所：** Hull の前提： §23.1（pp.542–544）。<a href="../20_surface_dynamics.html#negative-results">Book：限界とnegative results</a> ／ <a href="../../../../../MODEL_INDEX.md#10-surface-dynamics-forecasting--hedging-decisions">実装・テスト：MODEL_INDEX 10</a> ／ <a href="../../../../../report/site/chapters/ch23.html#section-23-1">補足教材 §23.1</a>。

(model-deep-hedging)=
### 深層ヘッジと共通経路の比較

Deep hedging and common-path comparison。

**何を表すか：** 状態から保有数量を決め、取引費用とヘッジ損益（通貨）を追います。

**仮定と限界：** リスク目的、制約と取引費用を指定します。評価経路を学習から分けます。

**解き方・手順：** 方策を学習し、BS デルタ・無ヘッジ等を同じ経路と価格で比較します。

**使う場面：** 価格誤差だけでなく損益と費用で意思決定を見る教材。

**実装と検証の範囲：** Phase1 方策と合成サーフェスの比較。oracle の価格と予測ボラを区別し、市場収益の証明にはしません。

**読む場所：** Hull の前提： §19.4（pp.421–427）。<a href="../20_surface_dynamics.html#common-path-hedge-p-l">Book：common-path hedge P&amp;L</a> ／ <a href="../../../../../MODEL_INDEX.md#10-surface-dynamics-forecasting--hedging-decisions">実装・テスト：MODEL_INDEX 10</a> ／ <a href="../../../../../report/site/chapters/ch19.html#section-19-4">補足教材 §19.4</a>。

(model-pdv)=
### 経路依存ボラティリティ

Four-factor path-dependent volatility（PDV）。

**何を表すか：** 過去のリターンと変動のフィルターから、現在の分散率を作ります。

**仮定と限界：** 係数と減衰、有限の履歴と時間格子を指定します。

**解き方・手順：** 複数の履歴因子を更新して株価経路を作ります。

**使う場面：** 過去の動きと現在のボラの関係。

**実装と検証の範囲：** 係数・減衰の契約と有限経路を確認。一般市場への較正の成功は主張しません。

**読む場所：** Hull の前提： §27.2（pp.646–649）。<a href="../21_spx_vix.html#pdv-afv-rough-quintic">Book：PDV/AFV/rough/quintic比較</a> ／ <a href="../../../../../MODEL_INDEX.md#11-spxvix--path-dependent-volatility">実装・テスト：MODEL_INDEX 11</a>。

(model-rough-kernel)=
### 前方分散と rough Heston カーネル

Affine forward variance and rough Heston kernel。

**何を表すか：** 将来の分散率と、時間差を重みにするカーネルを扱います。

**仮定と限界：** 長い記憶を表す核の指数と時間の単位を指定します。通常の Markov 分散だけでは記憶を残せません。

**解き方・手順：** 前方分散の表現と分数べきの核を計算します。

**使う場面：** SPX/VIX のモデル構成を学ぶ入口。

**実装と検証の範囲：** vol21 の rough Heston は kernel のみ。rough Heston の完全な価格器・較正器を収録したという意味ではありません。

**読む場所：** Hull の前提： §27.2（pp.646–649）。<a href="../21_spx_vix.html#pdv-afv-rough-quintic">Book：PDV/AFV/rough/quintic比較</a> ／ <a href="../../../../../MODEL_INDEX.md#11-spxvix--path-dependent-volatility">実装・テスト：MODEL_INDEX 11</a>。

(model-quintic-ou)=
### quintic OU ボラティリティ

Quintic Ornstein–Uhlenbeck volatility。

**何を表すか：** ガウスの OU 因子を多項式へ通し、二乗して分散率を作ります。

**仮定と限界：** 多項式の係数と時間尺度を指定します。二乗による非負性と価格の適切なモーメント条件は別です。

**解き方・手順：** OU の経路と多項式の評価を組み合わせます。

**使う場面：** 柔軟なボラティリティ形状の教師。

**実装と検証の範囲：** 多項式の二乗分散を検証。市場への完全な較正を承認したものではありません。

**読む場所：** Hull の前提： §27.2（pp.646–649）。<a href="../21_spx_vix.html#pdv-afv-rough-quintic">Book：PDV/AFV/rough/quintic比較</a> ／ <a href="../../../../../MODEL_INDEX.md#11-spxvix--path-dependent-volatility">実装・テスト：MODEL_INDEX 11</a>。

(model-joint-spx-vix)=
### SPX/VIX の共同目的関数

Joint SPX/VIX calibration objective。

**何を表すか：** 株価指数の価格と将来分散に関わる VIX の目標を合わせます。単位は目標ごとに固定します。

**仮定と限界：** 各目標のスケールと測度、VIX の条件付き期待を指定します。

**解き方・手順：** nested MC 教師と複数の残差をまとめた目的関数を使います。

**使う場面：** 株価と分散の両側からモデルを制約する教材。

**実装と検証の範囲：** 目的関数・教師の実装です。一般市場の同時較正を完成したという意味ではありません。

**読む場所：** Hull の前提： §26.16（pp.629–632）。<a href="../21_spx_vix.html#spx-iv-joint-fit">Book：SPX IV joint fit</a> ／ <a href="../../../../../MODEL_INDEX.md#11-spxvix--path-dependent-volatility">実装・テスト：MODEL_INDEX 11</a>。

(model-polynomial-surrogate)=
### 二次サロゲートと範囲外判定

CPU quadratic surrogate with domain flags。

**何を表すか：** パラメーターから価格・指標を二次関数で近似します。単位は目的量に従います。

**仮定と限界：** 学習した入力の範囲を明示します。範囲内でも精度確認は必要です。

**解き方・手順：** 二次回帰と有限差分感応度、入力ボックスによる OOD 判定を使います。

**使う場面：** 軽量な基準価格近似。

**実装と検証の範囲：** 合成の学習領域と範囲外フラグを検証。範囲外の安全な外挿は保証しません。

**読む場所：** Hull の前提： §21.5（pp.488–489）。<a href="../21_spx_vix.html#nested-mc-vs-surrogate">Book：nested MC vs surrogate</a> ／ <a href="../../../../../MODEL_INDEX.md#11-spxvix--path-dependent-volatility">実装・テスト：MODEL_INDEX 11</a> ／ <a href="../../../../../report/site/chapters/ch21.html#section-21-5">補足教材 §21.5</a>。

(model-variance-clock)=
### 取引時間と分散時計

Trading-session variance clock。

**何を表すか：** 決済までの取引秒数と累積分散の比（無次元）を扱います。

**仮定と限界：** タイムゾーン・取引日程・決済時刻を指定します。暦時間と変動時間は同じとは限りません。

**解き方・手順：** 取引時間を集計し、時刻ごとの分散配分へ写します。

**使う場面：** 超短期満期の時間の扱い。

**実装と検証の範囲：** 暦の境界と決済時刻を検証。市場固有の現行取引規則の網羅ではありません。

**読む場所：** Hull の前提： §21.6（pp.489–495）。<a href="../22_zero_dte.html#intraday-variance-clock">Book：intraday variance clock</a> ／ <a href="../../../../../MODEL_INDEX.md#12-0dte-intraday-clocks-events-jumps">実装・テスト：MODEL_INDEX 12</a> ／ <a href="../../../../../report/site/chapters/ch21.html#section-21-6">補足教材 §21.6</a>。

(model-event-variance)=
### 予定イベントとジャンプ分散

Scheduled events and intraday jumps。

**何を表すか：** イベント時刻、ジャンプ強度（時間の逆数）と総分散を扱います。

**仮定と限界：** 予定された変動と通常時の変動を分けます。強度とジャンプの大きさの両方が必要です。

**解き方・手順：** 時刻ごとの強度と予定分散を積み上げ、MC の注入分散と比べます。

**使う場面：** イベントを含む当日満期の教材。

**実装と検証の範囲：** 総分散の整合性を合成データで検証。現実のイベント規模の予測器ではありません。

**読む場所：** Hull の前提： §27.1（pp.641–646）。<a href="../22_zero_dte.html#event-non-event-jump-intensity">Book：event/non-event jump intensity</a> ／ <a href="../../../../../MODEL_INDEX.md#12-0dte-intraday-clocks-events-jumps">実装・テスト：MODEL_INDEX 12</a>。

(model-sv-jump-teacher)=
### 確率ボラ＋ジャンプの超短期教師

Stochastic-volatility jump teacher for intraday options。

**何を表すか：** 価格と分散の経路に、日中のジャンプを加えます。

**仮定と限界：** イベント日/通常日と時間帯、刻みと係数を固定します。

**解き方・手順：** 確率ボラとジャンプを同じ経路で標本化します。

**使う場面：** 短い満期での教師比較。

**実装と検証の範囲：** 合成のイベント・時間帯別指標を報告。実市場の当日価格性能の認定ではありません。

**読む場所：** Hull の前提： §27.1（pp.641–646）、§27.2（pp.646–649）。<a href="../22_zero_dte.html#adjacent-expiry-total-variance">Book：adjacent-expiry total variance</a> ／ <a href="../../../../../MODEL_INDEX.md#12-0dte-intraday-clocks-events-jumps">実装・テスト：MODEL_INDEX 12</a>。

(model-perpetual-funding)=
### 無期限先物の funding

Perpetual-futures funding and basis feedback。

**何を表すか：** 現物・無期限先物の価格と当事者間の funding 受払（通貨）を追います。

**仮定と限界：** funding 規則と時刻、建値・ポジションを固定します。実取引所の全規則ではありません。

**解き方・手順：** funding と評価損益の台帳を作り、ベーシスの帰還をシミュレートします。

**使う場面：** 満期のない先物と現物とのつながり。

**実装と検証の範囲：** 当事者間の資金保存と合成フィードバックを検証。

**読む場所：** Hull の前提： §2.4（pp.51–54）、§5.4（pp.127–130）。<a href="../24_crypto_market_structure.html#index-mark-last-price-states">Book：index/mark/last price states</a> ／ <a href="../../../../../MODEL_INDEX.md#13-crypto-market-structure-perps-liquidation-amm">実装・テスト：MODEL_INDEX 13</a> ／ <a href="../../../../../report/site/chapters/ch02.html#section-2-4">補足教材 §2.4</a>。

(model-liquidation)=
### 証拠金・清算の連鎖

Margin, liquidation waterfall and insurance/ADL。

**何を表すか：** ポジション、担保、オラクル価格と残余損失（通貨）を扱います。

**仮定と限界：** 清算閾値・手数料・保険/ADL の負担順を明示します。

**解き方・手順：** ショック後の資産と負債を順に精算します。

**使う場面：** 暗号資産市場の清算と価格参照リスク。

**実装と検証の範囲：** 合成シナリオの現金保存とオラクルの影響を確認。特定取引所の支払能力を保証しません。

**読む場所：** Hull の前提： §2.4（pp.51–54）。<a href="../24_crypto_market_structure.html#insurance-fund-and-adl-waterfall">Book：insurance fund and ADL waterfall</a> ／ <a href="../../../../../MODEL_INDEX.md#13-crypto-market-structure-perps-liquidation-amm">実装・テスト：MODEL_INDEX 13</a> ／ <a href="../../../../../report/site/chapters/ch02.html#section-2-4">補足教材 §2.4</a>。

(model-amm)=
### AMM と LVR

Constant-product AMM and loss versus rebalancing（AMM・LVR）。

**何を表すか：** プールの二資産在庫と外部価格、手数料・損失（通貨）を扱います。

**仮定と限界：** 不変量と外部価格への裁定、比較する再均衡戦略を指定します。

**解き方・手順：** 交換による在庫更新と、再均衡との差を計算します。

**使う場面：** 流動性供給者が引き受ける選択のリスク。

**実装と検証の範囲：** 積の保存・LVR の符号・手数料の規則を検証。実取引環境の収益保証ではありません。

**読む場所：** Hull の前提： §3.1（pp.70–72）。<a href="../24_crypto_market_structure.html#amm-lvr-and-fee-compensation">Book：AMM LVR and fee compensation</a> ／ <a href="../../../../../MODEL_INDEX.md#13-crypto-market-structure-perps-liquidation-amm">実装・テスト：MODEL_INDEX 13</a> ／ <a href="../../../../../report/site/chapters/ch03.html#section-3-1">補足教材 §3.1</a>。

(model-carbon)=
### 排出枠オプション

Carbon-allowance options。

**何を表すか：** 排出枠の先物価格と変動・ジャンプ、プレミアム（通貨）を扱います。

**仮定と限界：** 価格過程と評価上のリスクプレミアムを明示します。

**解き方・手順：** Black、確率ボラ、ジャンプつき MC の段階を比べます。

**使う場面：** 排出枠市場のモデル仮定の比較。

**実装と検証の範囲：** 合成価格と Black 基準・プレミアム分解を検証。現行制度の価格予測ではありません。

**読む場所：** Hull の前提： §35.4（pp.789–795）。<a href="../25_climate_energy.html#carbon-gbm-vs-sv-jump-smile">Book：carbon GBM vs SV+jump smile</a> ／ <a href="../../../../../MODEL_INDEX.md#14-climate--energy-carbon-weather-ppa">実装・テスト：MODEL_INDEX 14</a> ／ <a href="../../../../../report/site/chapters/ch35.html#section-35-4">補足教材 §35.4</a>。

(model-weather)=
### 気温・度日とベーシス・リスク

OU/fractional-OU weather models and degree days（HDD・CDD）。

**何を表すか：** 気温（温度）、HDD/CDD（温度×日）、契約の受払い（通貨）を扱います。

**仮定と限界：** 季節性、平均回帰、記憶と価格付け原理を明示します。気温を直接売買して完全複製できるとは仮定しません。

**解き方・手順：** OU/fOU の経路から度日を作り、期待値やリスクプレミアム、最小分散ヘッジを計算します。

**使う場面：** 天候デリバティブと地域の違い。

**実装と検証の範囲：** 独立モーメント・求積/MC・holdout のヘッジを検証。不完備市場の選んだ評価原理を保持します。

**読む場所：** Hull の前提： §35.5（pp.795–796）、§35.7（pp.797–798）。<a href="../25_climate_energy.html#temperature-ou-vs-fou">Book：temperature OU vs fOU</a> ／ <a href="../../../../../MODEL_INDEX.md#14-climate--energy-carbon-weather-ppa">実装・テスト：MODEL_INDEX 14</a> ／ <a href="../../../../../MODEL_INDEX.md#p4-logic-first-private-models">実装・テスト：MODEL_INDEX P4 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch35.html#section-35-5">補足教材 §35.5</a>。

(model-commodity)=
### 商品・エネルギーの契約とモデル

Commodity and energy pricing foundations。

**何を表すか：** 商品価格、季節性、保険/再保険と事業受払（通貨）を扱います。

**仮定と限界：** 貯蔵・季節・リスクプレミアム・契約の観測条件を指定します。

**解き方・手順：** 先物に合わせたツリー、OU/jump、コール・スプレッド等の会計で比べます。

**使う場面：** エネルギー契約から天候・保険への橋渡し。

**実装と検証の範囲：** 原典例と独立経路/求積/Itô・共分散を検証。複製不能なリスクの価格は一意とは限りません。

**読む場所：** Hull の前提： §35.4（pp.789–795）、§35.6（pp.796–797）、§35.8（pp.798–799）。<a href="../12_qualitative_summary.html#ch-35">Book：4. エネルギー・コモディティ・デリバティブ（Ch.35）</a> ／ <a href="../../../../../MODEL_INDEX.md#p4-logic-first-private-models">実装・テスト：MODEL_INDEX P4 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch35.html#section-35-4">補足教材 §35.4</a>。

(model-ppa)=
### 再生可能電力 PPA

Renewable power-purchase agreement（PPA）。

**何を表すか：** 電力価格、発電量、時間帯の形と受払額（通貨）を扱います。

**仮定と限界：** 価格と量の依存、契約の固定/変動部分とヘッジ比率を指定します。

**解き方・手順：** 共同シナリオから受払いを作り、CFaR/CVaR とヘッジ感応度を比較します。

**使う場面：** 数量・shape・profile リスクのある買電契約。

**実装と検証の範囲：** 保存済み標本からリスクを再計算。実契約の法律・信用・すべての時間帯の評価は含みません。

**読む場所：** Hull の前提： §35.3（pp.787–789）、§35.8（pp.798–799）。<a href="../25_climate_energy.html#ppa-cfar-cvar-and-hedge-residual">Book：PPA CFaR/CVaR and hedge residual</a> ／ <a href="../../../../../MODEL_INDEX.md#14-climate--energy-carbon-weather-ppa">実装・テスト：MODEL_INDEX 14</a> ／ <a href="../../../../../report/site/chapters/ch35.html#section-35-3">補足教材 §35.3</a>。

(model-schwartz-moon)=
### Schwartz–Moon の事業価値

Schwartz–Moon business valuation。

**何を表すか：** 売上、成長率、費用、現金と株式価値（通貨）を状態にします。

**仮定と限界：** 四半期の税・デフォルト・報酬/ESO の時点を明示します。

**解き方・手順：** OU の因子と会計 CF を経路で積み上げ、独立に比較します。

**使う場面：** 事業価値と不確実な成長。

**実装と検証の範囲：** private 教材。原著の会計/ESO 時点が不足し原著価格は未再現です。指定した会計条件での検証と区別します。

**読む場所：** Hull の前提： §36.4（pp.806–807）。<a href="../12_qualitative_summary.html#ch-36">Book：5. リアルオプション（Ch.36）</a> ／ <a href="../../../../../MODEL_INDEX.md#p3-logic-first-private-models">実装・テスト：MODEL_INDEX P3 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch36.html#section-36-4">補足教材 §36.4</a>。

(model-real-options)=
### 撤退・拡張のリアル・オプション

Abandonment and expansion real options。

**何を表すか：** 事業の価格・収益状態、撤退/拡張の選択と価値（通貨）を扱います。

**仮定と限界：** P/Q のリスク調整、投資費用、選択の相互作用を指定します。

**解き方・手順：** NPV、複製、格子と全方策の列挙で選択の価値を求めます。

**使う場面：** 事業の柔軟性を固定した投資計画から分ける場面。

**実装と検証の範囲：** 原典例と独立方策/状態列挙を比較。共同の撤退・拡張では原典脚注と異なる相互作用を保持します。

**読む場所：** Hull の前提： §36.1（pp.802–803）、§36.5（pp.806–813）。<a href="../12_qualitative_summary.html#ch-36">Book：5. リアルオプション（Ch.36）</a> ／ <a href="../../../../../MODEL_INDEX.md#p4-logic-first-private-models">実装・テスト：MODEL_INDEX P4 logic-first private models</a> ／ <a href="../../../../../report/site/chapters/ch36.html#section-36-1">補足教材 §36.1</a>。

## 出典と更新

Hull の章節・頁は Global Edition の本文と照合しています。モデルカードの記述は本書の案内と、この repo の実装・検証範囲を独自にまとめたものです。Beyond Hull の理論文献は MODEL_INDEX 各行の Theory 欄、制限は各巻の VALIDATION と CONTENTS_INDEX §7 に戻って確認できます。新しい数値例はこの地図には置いていません。図の条件・カード・索引行の対応の正本は `model_map.json` です。
