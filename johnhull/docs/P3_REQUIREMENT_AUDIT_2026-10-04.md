# P3要求監査 — 2026-10-04
対象: `/home/kazumasa/projects/johnhull`、読み取り専用。Git/プロジェクトファイル未変更。監査開始HEAD `0aa51b13`。成果物は `/tmp/p3-requirement-audit-20261004.md`。

## 結論

P3は37節（Ch28=8、Ch29=4、Ch30=4〔付録含む〕、Ch31=5、Ch32=7、Ch33=3、Ch34=6）。台帳acceptedは§28.1/28.2の2節、残35節は全て`unreviewed`かつ`requirements=[]`。草稿は7c4bb109時点の要求で受入記録ではない。特に28.1/2の「専用なし」は現在と矛盾するので現行台帳/2026-10-03受入を優先。以下の残35節要求は草稿表を省略せず列挙した。

## 判定原則と検証の範囲

- 5観点（explanation/implementation/independent_validation/visualization/rendered）を要求ごとに閉じる。既存API、印刷pin一つ、過去のnotebook実行だけで節をacceptedにしない。
- D3ではexplanation/renderedが必須。計算・誤差・条件付き期待値・行使要求を、説明節という分類でN/Aにしない。N/Aは要求ごとの理由が必要。
- 原典が価格入力を与えない箇所は透明なsynthetic例で手順を検証できるが、本文の歴史データ/印刷MC値/実市場価格を再現したという証明にはならない。
- 今回はsource/ledger/notebook JSON/テスト内容の静的照合。価格計算・pytest・fresh execution・browser・保管庫gateを再実行していない。accepted2節は現在の受入記録を尊重し、その実行成績を今回の新実行成績と混同しない。
- 公開API/production依存追加はP3_DESIGNとAGENTSの承認条件を既存ユーザー指示と照合する。最小のprivate lesson/fixture実装で進められる箇所は先行し、既存APIの仕様を黙って広げない。

## 現行資産の実体

| 現行ソース/教材 | 再利用できる具体的範囲 | 現在の境界 |
|---|---|---|
| `hullkit/src/hullkit/ir_options.py` | 欧州Black 4入口、cap=sum、convexity結果式/年複利bond微分 | F/K>0、σ/T>0。σ=0/T=0は拒否。shifted wrapper/strip/schedule/timing/quantoなし |
| `hullkit/src/hullkit/hull_white.py` | 定数a/σ、zero-mean OU状態exact transition、curve-fit bond、ZCB option、positive-coupon unit-strike Jamshidian、constant calibration | a>0（Ho–Lee不可）、integral r exact sampler/木/BK/2F/σ(t)/Bermudanなし |
| `hullkit/src/hullkit/rates.py` | 連続複利yield/Macaulay、線形zero補間、半期債bootstrap | 半年複利modified-duration入口/汎用quote curveなし |
| `hullkit/src/hullkit/swaps.py` | standard/seasoned IRS、既知両通貨CFのPV差 | 単一schedule/元本前提。一般leg/day-count/currency-basis engineなし |
| `hullkit/src/hullkit/rfr.py`, `rfr_options.py` | 既知日次RFR複利/calendar、Bachelier、与えたdaily rate pathsのpayoff平均 | 全Following term-sheet生成/Ch29 midpoint RFRモデル/一般確率割引の教師ではない |
| `volumes/10_exotics_martingales/exotics.ipynb` | 235セル、accepted28.1/2、exchange accepted26.14 | §5のmartingaleは無条件平均/zero-drift説明、§7は定数rでQ/T-forward同一spot分布 |
| `volumes/11_ir_derivatives_market/ir_options.ipynb` | 36セル、Black合成例、inline strip、Ch30式/相関表 | 原典例と測度/非標準規約/近似誤差の網羅なし。受入節ごとの保存gate要追加 |
| `volumes/07_swaps/swaps.ipynb` | 33セル、standard/currency/DV01/別条件compounding、Ch34説明 | Ch34のterm sheet/途中equity MTM/embedded state教師なし |
| `interest_rate_models/ir_models.ipynb` | 55セル、RB/Vasicek/CIR、HL/HW/BDT/BKの例示/curve fit、t0 HJM図 | CIRゼロ切上げEuler、RB2次cumulant+clip。LMMは初期DF恒等式のみ。full dynamic HJM/LMM/金利木なし |

既存pin: Ex29.1、Ex29.4、Ex30.1、Ex30.4 N100、Table32.3解析。Ex29.3は元本1Mの519.0046（原典10Mの5190.046）として既存テストあり。これらを再利用し、新規教師と教材の対応を追加する。

## 全37節の明示要求・差分・依存

### §28.1 The Market Price of Risk（pp.671–674） — accepted

出典草稿: `docs/prep/sections/ch28.md:23`。
**現行受入要求（草稿より優先）**

| ID | statement |
|---|---|
| RP01 | 共通単因子・無配当の取引証券、符号付きsとλの関係と単位を説明し逆算・順算する。 |
| RP02 | 原典の株数hedgeと教材の金額weightsを区別し、拡散相殺と無リスク年率収益を検証する。 |
| RP03 | Examples 28.1/28.2の.2/−.15/1.5%を再現し、消費財spotへの機械適用を避ける。 |
| RP04 | P→QのRN符号、ドリフト変更・拡散保存、負sの座標と非正規化重みを検証する。 |
| RP05 | 独立12市場/6power求積と262144標本×4、ペア差SE、有限値、4保存改変/4実API変異を検査する。 |
| RP06 | 6小節・4共有図、旧213セル、既受入25節のD1と両画面16状態を再検査する。 |

**既存で再利用できるもの:** risk_premium.py、_risk_premium_lesson.py、vol10 §6.1–6.6。RP01–06を2026-10-03受入。

**残る受入作業/新実装:** 新機能不要。新節による共有builder/portal等の変更をD1で再確認する。

**依存と独立参照:** 後続28.3/28.8の単因子基礎。既存acceptedの範囲を変更しない。

### §28.2 Several State Variables（pp.674–675） — accepted

出典草稿: `docs/prep/sections/ch28.md:43`。
**現行受入要求（草稿より優先）**

| ID | statement |
|---|---|
| FR01 | 式28.11–28.13とsigned係数/年率単位/最終因子軸を説明し、因子寄与・超過/総収益を計算する。 |
| FR02 | Example28.3の+1%,-1%,+6%と合計6%を超過収益として固定し、合成r=4%の総収益10%と区別する。 |
| FR03 | 正/負/ゼロのλs、負loading、無価格追加因子の条件、単因子縮約を検証する。 |
| FR04 | 金額比率の二因子相殺/SVD零空間と直交回転の内積/volatility不変性、同一基底の規約を検証する。 |
| FR05 | 独立12市場・CAPMの仮定付き計算・APTとの関係を説明し、保存4改変/API4変異を拒否する。 |
| FR06 | 6小節/4共有図、旧224セル、既受入26節D1と両画面16状態・幅700px以上を検証する。 |

**既存で再利用できるもの:** factor_risk.pyの3関数、_factor_risk_lesson.py、vol10 §6A.1–6A.6。FR01–06を2026-10-03受入。

**残る受入作業/新実装:** 一般相関の白色化、多因子測度変更は未受入。28.5に残す。

**依存と独立参照:** 28.5のsigned-loading内積と同一基底規約へ再利用。acceptedを無条件に広げない。

### §28.3 Martingales（pp.675–676） — unreviewed

出典草稿: `docs/prep/sections/ch28.md:63`。
**草稿の全要求**（まだ台帳要求として確定/受入されていない）

| ID | 原典上の要点（頁） | 検証の手がかり |
|---|---|---|
| D28.3-01 | 脚注の条件付き定義と式28.14（675–676） | Itô drift の相殺 |
| D28.3-02 | 正値 numeraire と式28.15（676） | 同じ給付の価格不変性 |

**既存で再利用できるもの:** vol10 §5に定義と価格式、§7に定数金利の3測度MC。sde.girsanov_weightsの単因子部品。

**残る受入作業/新実装:** D28.3-01: 条件付き定義、Itôの比のdrift相殺、可積分性の説明。現行§5の「ドリフトゼロ＝martingale/無条件平均」説明を精密化。-02: 正値numeraire、同一給付の価格不変性を2時点条件付き解析値と区間別MCで示す。専用lesson/数値参照/両画面証跡が必要。

**依存と独立参照:** 28.1→28.3→28.4/28.5。定数GBMのjoint Gaussian条件付き指数モーメントをhullkit非依存の教師にできる。まずM28。

### §28.4 Alternative Choices for the Numeraire（pp.676–679） — unreviewed

出典草稿: `docs/prep/sections/ch28.md:82`。
**草稿の全要求**（まだ台帳要求として確定/受入されていない）

| ID | 原典上の要点（頁） | 検証の手がかり |
|---|---|---|
| D28.4-01 | $E^Q[e^{-\int rdt}f_T]=P(0,T)E^T[f_T]$（677–678） | 確率金利で別測度の価格 |
| D28.4-02 | $E^T[S_T]=F_0$、$E^{T^*}[R]=F$（678） | spot と金利の fixing / payment の区別 |
| D28.4-03 | $A=\sum\delta_iP(t,T_i)$、$s=V/A$（679） | swap rate の平均と2曲線の役割 |

**既存で再利用できるもの:** vol10 §7の定数rのQ/stock/T-forward MC、HWの状態遷移/債券式、swaption_black。

**残る受入作業/新実装:** -01: 確率rで経路割引QとT-forward直接標本の別計算一致。-02: spot/fixing/payment測度とE[R]=F。-03: annuity measureとprojection/discount curveの役割。現行定数rの比較ではQ/T-forward分布差を証明しない。積分rateの精度管理と支払測度の教師を新規作成。

**依存と独立参照:** 28.3→28.4→28.6、29.2/29.3、31.1。Gaussian積分rateと状態のjoint分布を解析基準にする。

### §28.5 Extension to Several Factors（pp.679–680） — unreviewed

出典草稿: `docs/prep/sections/ch28.md:102`。
**草稿の全要求**（まだ台帳要求として確定/受入されていない）

| ID | 原典上の要点（頁） | 検証の手がかり |
|---|---|---|
| D28.5-01 | 多因子 drift / diffusion と $\lambda_i=s_{g,i}$（679–680） | 比の Itô drift ゼロ |
| D28.5-02 | 脚注7の直交化（679） | 基底変更で価格・共分散を保存 |

**既存で再利用できるもの:** 28.2のfactor_risk内積、直交回転/hedge教材は基礎として再利用。単因子sde部品。

**残る受入作業/新実装:** -01: 多因子ratioのItô driftとλ_i=s_gi、2因子以上のmartingale実験。-02: 相関行列PSD/退化、直交化で価格/共分散保存。28.2の直交回転だけでは一般相関の白色化を受入できない。

**依存と独立参照:** 28.2/28.3→28.5→28.7/28.8/33.1。joint Gaussian指数モーメントと別実装factorization。

### §28.6 Black’s Model Revisited（pp.680–681） — unreviewed

出典草稿: `docs/prep/sections/ch28.md:121`。
**草稿の全要求**（まだ台帳要求として確定/受入されていない）

| ID | 原典上の要点（頁） | 検証の手がかり |
|---|---|---|
| D28.6-01 | 式28.26–28.29 の期待値と Black 公式（680–681） | lognormal 給付求積と parity |
| D28.6-02 | option と forward の満期一致、$\sigma_F$（681） | futures を使える条件の限定 |

**既存で再利用できるもの:** ir_optionsのBlack核・bond_option_black・caplet_black。vol10短い根拠、vol11市場式。

**残る受入作業/新実装:** -01: T-forward lognormal給付求積/価格/parityと確率rでの根拠。-02: 満期一致、forward vol、futures代用成立条件。既存核はσ=0/T=0を拒否するため、極限は小σ収束または別の明示的入口で確認。

**依存と独立参照:** 28.4→28.6→Ch29。T-forward密度求積＋Qの確率r MC。

### §28.7 Option to Exchange One Asset for Another（pp.681–682） — unreviewed

出典草稿: `docs/prep/sections/ch28.md:140`。
**草稿の全要求**（まだ台帳要求として確定/受入されていない）

| ID | 原典上の要点（頁） | 検証の手がかり |
|---|---|---|
| D28.7-01 | 式28.30–28.32、無配当で $E^U[V_T/U_T]=V_0/U_0$（681–682） | 比の平均と給付価格 |
| D28.7-02 | 配当時は平均比率 $e^{(q_U-q_V)T}V_0/U_0$（682） | 受入済 §26.14 の値 |

**既存で再利用できるもの:** exotics.exchange_option/exchange_spread_volatility、受入§26.14の独立参照/vol10 §4.4。

**残る受入作業/新実装:** -01: U測度ratio drift/平均と給付価格。-02: 配当差の平均比率、配当spotと再投資numeraireの区別。§26.14の数値受入だけでは本節の導出受入にならない。

**依存と独立参照:** 28.5/28.4→28.7。§26.14教師を参照しつつratio条件付き分布を独立構成。

### §28.8 Change of Numeraire（pp.682–684） — unreviewed

出典草稿: `docs/prep/sections/ch28.md:159`。
**草稿の全要求**（まだ台帳要求として確定/受入されていない）

| ID | 原典上の要点（頁） | 検証の手がかり |
|---|---|---|
| D28.8-01 | 式28.33–28.35、比は新/旧（683） | 逆変換で drift 差が相殺 |
| D28.8-02 | P→Q は $-\sum\lambda_i s_{v,i}$（684） | 取引・非取引変数の平均 |
| D28.8-03 | 相対 drift と絶対 drift（684） | 単位と係数 |

**既存で再利用できるもの:** 単因子sde.girsanov_weights、vol10 §8のdrift比較、28.1/2のsigned係数。

**残る受入作業/新実装:** -01: w=h/g（新/旧）と多因子covarianceによるdrift補正、往復相殺。-02: P→Qの負λ内積と非取引変数。-03: 相対/絶対driftの単位。joint-lognormal密度傾斜・非正規化RN比較を追加。

**依存と独立参照:** 28.5→28.8→30.2/30.3、31.3、33.1/33.2。式28.33–35の向きは原PDF確認。

### §29.1 Bond Options（pp.688–692） — unreviewed

出典草稿: `docs/prep/sections/ch29.md:20`。
**草稿の全要求**（まだ台帳要求として確定/受入されていない）

| ID | 原典上の要点（頁） | 検証の手がかり |
|---|---|---|
| D29.1-01 | 組込オプション（callable・puttable・期限前解約できる預金・ローン・コミットメント）と利回りへの影響（p.689） | 定性。数値化は §32 のツリーの後（callable と straight の差）。ここでは説明と対応表だけ |
| D29.1-02 | Black の債券オプション式 (29.1)・(29.2)。$K$ は現金ストライク、$P(0,T)$ は無リスク割引（p.689） | put–call parity $c-p=P(0,T)(F_B-K)$、$\sigma_B\to0$ の極限 |
| D29.1-03 | $F_B=(B_0-I)/P(0,T)$（式 29.3）。clean と dirty、quoted strike のときは満期の経過利子を足す（p.690） | Ex 29.1 の $I$・$F_B$・経過利子 25・quoted 935 |
| D29.1-04 | Example 29.1：現金ストライク 1,000 で 9.49、quoted ストライク（現金 1,008.33）で 7.97（p.690） | 下の印刷値 |
| D29.1-05 | Figure 29.1・29.2：対数価格の標準偏差の山型、$\sigma_B$ はオプション期間とともに低下（p.691） | 原典は模式図でモデルを指定していない。受入ではモデル（HW か Vasicek）を明示して形だけを再現する |
| D29.1-06 | 利回りボラの換算 $\sigma_B=Dy_0\sigma_y$（式 29.4）。例 $5\times0.08\times0.2=0.08$（p.692） | 数値。forward yield の複利頻度と「修正」デュレーションの規約を仕様にする |
| D29.1-07 | Example 29.2：10 年 8%（半年払い）、期間 2.25 年、ストライク 115、利回りボラ 20%、フラット 5%（連続）。債券 122.82、quoted ストライクで 2.36、現金ストライクで 1.74（p.692、Problem 29.16 が手計算） | 下の印刷値。規約を固定して再現 |

**既存で再利用できるもの:** bond_option_black、Ex29.1の6値pin、ratesの連続複利bond_price/yield/duration、vol11 §2の合成例。

**残る受入作業/新実装:** -01: 組込権利対応表。-02/-04: parityとEx29.1の教材化。-03: dirty/clean/accrualと現金strike。-05: Figure29.1/2のモデル明示再現。-06/-07: 半年複利forward yield＋modified duration、Ex29.2=122.82/2.36/1.74を教師とpinへ追加。既存連続複利関数の流用だけでは一致しない。

**依存と独立参照:** 28.6、4.10部品。図は既存HWを明示利用。組込権利数値は32.5後、現節では説明。DerivaGem同一実装と断言しない。

### §29.2 Interest Rate Caps and Floors（pp.693–699） — unreviewed

出典草稿: `docs/prep/sections/ch29.md:74`。
**草稿の全要求**（まだ台帳要求として確定/受入されていない）

| ID | 原典上の要点（頁） | 検証の手がかり |
|---|---|---|
| D29.2-01 | キャップとフロアの支払い（25,000・12,500）、式 (29.5)、tenor（p.693） | 下の印刷値 |
| D29.2-02 | キャップ＝ZCB プットのポートフォリオ（式 29.6、額面 $L(1+R_K\delta_k)$、ストライク $L$）（p.694） | 支払いの恒等式を乱数の $R_k$ で確かめる（モデルに依らない） |
| D29.2-03 | フロア・フロアレット・カラー。ゼロコスト・カラー（p.694） | カラー＝キャップ − フロア。ゼロコストになるフロア金利の求解 |
| D29.2-04 | パリティ：キャップ − フロア ＝ スワップ（初回リセットの交換なし）（p.695、BS 29.1） | 同じストライク・満期で恒等式。LIBOR 型では初回の扱いを調整する旨も説明 |
| D29.2-05 | Black のキャップレット式 (29.7)・フロアレット式 (29.8)（pp.694–695） | Example 29.3 |
| D29.2-06 | Example 29.3：$L$=1,000 万、$R_K$=8%、$F_k$=7%、$\sigma_k$=20%、$t_k$=1、$t_{k+1}$=1.25、ゼロ 6.5%（連続）。0.00519（百万ドル）（pp.695–696） | 下の印刷値 |
| D29.2-07 | spot vol と flat vol。市場は flat で呼び、トレーダーは spot を推定する（p.696、Problem 29.20） | flat → spot のストリップ。spot vol で各満期のキャップを再評価すると flat の価格を再現 |
| D29.2-08 | スマイル・スキューと SABR（p.696） | 説明のみ（SABR の数値は §27.2、M11 で受入済み） |
| D29.2-09 | 理論的根拠：$t_{k+1}$-フォワード測度で $E_{k+1}(R_k)=F_k$（式 29.9）（pp.696–697） | 何らかの金利モデルの MC で、$t_{k+1}$ 債をニュメレールにした $R_k$ の平均が $F_k$ に一致 |
| D29.2-10 | DerivaGem の支払日：期間の末尾から tenor で遡り、初回は通常期間の 0.5〜1.5 倍（例：1.22–2.80 年で 6 期間）（p.697） | 下の印刷値 |
| D29.2-11 | 日数計算：$\delta_k$ を $\alpha_k$（act/360）に置き換え、$1+\alpha_kF_k=P(0,t_k)/P(0,t_{k+1})$ で $F_k$ を定義（p.697） | 5/1→8/1 の 92 日で 0.2556。act/actual で計算しても影響はほぼ同じ、という主張を数値で確かめる |
| D29.2-12 | 負の金利：shifted lognormal（$F_k+\alpha$、$R_K+\alpha$）、Bachelier のキャップレット・フロアレット式、$\sigma_k$ 33% に対し $\sigma_k^*$ は約 1%（pp.697–698） | shift → 0 で Black に一致。Bachelier の put–call parity。ATM 価格を合わせた normal vol |
| D29.2-13 | 後ろ向き RFR：$F_k$ を OIS から取り、$d_1,d_2$ の $t_k$ を $0.5(t_k+t_{k+1})$ に置き換える。期中は観測済みの分を $F_k$ に入れ、残りの観測時点の平均を使う（pp.698–699） | 日次複利の MC と比べる（下の「注意」） |

**既存で再利用できるもの:** caplet_black/cap_black、parityとspot-vol配列テスト、vol11 inline brentq strip、rfr_options Bachelier/日次複利MC、非公開shifted Black。

**残る受入作業/新実装:** -01–06: cashflow/ZCB-put恒等式/collar/first reset/Ex29.3のL=10M・P・d1/d2 pinsを追加。-07: stripを検証可能な再利用部品へ。-08: SABR説明は27.2参照。-09: 支払債measureのE[R]=F検証。-10/11: 後ろ遡り6期間とACT360。-12: shifted/Bachelierの単位・ATM一致・parity。-13: 後ろ向きRFRのmidpoint/期中既知分近似と独立日次MC、近似誤差。単なる既存MC呼出は教師ではない。

**依存と独立参照:** 28.4/28.6→29.2。schedule/curve/measureを33.2/34へ共有。public API追加は別承認条件を照合し、既存入口を黙って変更しない。

### §29.3 European Swap Options（pp.699–702） — unreviewed

出典草稿: `docs/prep/sections/ch29.md:143`。
**草稿の全要求**（まだ台帳要求として確定/受入されていない）

| ID | 原典上の要点（頁） | 検証の手がかり |
|---|---|---|
| D29.3-01 | スワプションの使い方、forward swap との違い（p.699） | 定性（説明のみ） |
| D29.3-02 | スワプション＝固定利付債のオプション（payer＝プット、receiver＝コール、ストライク＝元本）（p.700、BS 29.2） | 満期での支払いの恒等式。HW では Jamshidian（既存）と短期金利 MC が一致 |
| D29.3-03 | 支払いの列と Black 式 (29.10)・(29.11)、$A$ の定義（pp.700–701） | payer − receiver ＝ $LA(s_F-s_K)$（Problem 29.18）、ATM で payer＝receiver |
| D29.3-04 | Example 29.4：フラット 6%（連続）、5 年後開始の 3 年スワップ（半年払い）、$s_K$=6.2%、$s_F$=6.1%（連続）＝6.194%（半年）、$\sigma$=20%、1 億ドル。2.19（百万ドル）（p.701） | 下の印刷値 |
| D29.3-05 | annuity 測度で $E_A(s_T)=s_F$ と、割引を定数扱いできる理由（pp.701–702） | 何らかの金利モデルの MC で、annuity をニュメレールにした $s_T$ の平均が $s_F$ |
| D29.3-06 | 日数計算：$A=\sum\alpha_iP(0,T_i)$、3/1→9/1 の act/365 で 0.5041（p.702） | 下の印刷値 |
| D29.3-07 | 負の金利：shifted lognormal と Bachelier 式（p.702） | shift → 0 で Black、Bachelier の payer−receiver パリティ |

**既存で再利用できるもの:** swaption_blackとparity、Ex29.4のA/sF/2.19 pin、HW Jamshidianと1D求積テスト、Bachelier。

**残る受入作業/新実装:** -01: forward swapとの用途差。-02: payer=債券put/receiver=callのpayoff。-03/-04: 元本/annuity/Black支払列とEx29.4教材化、d1/d2。-05: annuity測度の平均。-06: ACT365 annuity。-07: shifted/normal比較。Ex29.4の6.1%連続forwardは独立入力で割引flat6%から作り直さない。Aの印刷2.0035は切捨て。

**依存と独立参照:** 28.4/28.6、32.2解析教師。29.1とbuild共有可能だが要求ID/証跡は別。

### §29.4 Hedging Interest Rate Derivatives（p.703） — unreviewed

出典草稿: `docs/prep/sections/ch29.md:195`。
**草稿の全要求**（まだ台帳要求として確定/受入されていない）

| ID | 原典上の要点（頁） | 検証の手がかり |
|---|---|---|
| D29.4-01 | デルタの 4 定義（DV01、クオート、バケット、PCA）と、実務が (2) を好む理由（p.703） | 同じポートフォリオで 4 種を計算。クオート・デルタの合計＝全クオートを同時に動かして再構築した差分、バケットの合計≈DV01（補間の規約に依存） |
| D29.4-02 | ガンマの数：10 商品で 55 個。対角のみ、平行シフトの 2 階、PCA 2 因子（p.703） | $n(n+1)/2$。有限差分のヘッセ行列が対称であること、対角と平行の 2 階の関係 |
| D29.4-03 | ベガ：Black vol の平行シフト（1 因子の仮定）と、vol の PCA（p.703） | 合成の vol 変動から PCA ベガを出し、平行ベガとの差を示す |

**既存で再利用できるもの:** vol07のswap parallel DV01、rates.bootstrap_zero_curve（半年債）、29.2/3再価格部品。

**残る受入作業/新実装:** -01: 同portfolioのparallel/quote再構築/bucket/PCA delta。quote合計は有限bumpの厳密等価でなく一次一致。-02: Hessian対称、10商品55、parallel/対角/PCA gammaの関係。-03: parallel/PCA vega。新感応度・合成factor教師・誤差bump診断必要。説明だけのD3は不可。

**依存と独立参照:** 29.2/3→29.4↔32.7。補間とbucket形状を固定。RB-F07解析Jacobianは必須拡張にしない。

### §30.1 Convexity Adjustments（pp.707–710） — unreviewed

出典草稿: `docs/prep/sections/ch30.md:16`。
**草稿の全要求**（まだ台帳要求として確定/受入されていない）

| ID | 原典上の要点（頁） | 検証の手がかり |
|---|---|---|
| D30.1-01 | Figure30.1 の価格平均と利回り平均、式30.1（708–709） | $G'<0,G''>0$ と正の補正 |
| D30.1-02 | Ex30.1：年払3年6%債、vol22%、観測3年、割引5%年複利（709–710） | derivatives / 期待利回り / PV |
| D30.1-03 | swap rate を債券利回りで近似する前提（709） | 近似誤差の領域を説明 |

**既存で再利用できるもの:** bond_yield_convexity/convexity_adjustment、Ex30.1の5値と差分微分テスト、vol11 §7。

**残る受入作業/新実装:** -01: Figure30.1の価格平均/利回り平均とG′<0/G″>0。-02: pinを教材へ。-03: CMSのpar-bond近似前提/誤差域。yield逆変換求積で2次近似残差を追加。古いtestコメントのG″/G′符号は説明修正が必要だが関数挙動は正しい。

**依存と独立参照:** 28.8/29.1→30.1＋30.appendix。教師は価格分布求積＋各点root solve。

### §30.2 Timing Adjustments（pp.710–711） — unreviewed

出典草稿: `docs/prep/sections/ch30.md:36`。
**草稿の全要求**（まだ台帳要求として確定/受入されていない）

| ID | 原典上の要点（頁） | 検証の手がかり |
|---|---|---|
| D30.2-01 | 式30.2–30.3、bond ratio と forward rate の符号（710–711） | $\rho=0$、$T^*=T$ で補正ゼロ |
| D30.2-02 | Ex30.2：5年観測、6年支払、forward1200、vol20%/18%、相関−.4、金利8%年複利（711） | 係数・期待値・割引・PV |

**既存で再利用できるもの:** vol11 §8の式のみ。convexity_adjustmentはtiming公式の代替でない。

**残る受入作業/新実装:** -01: 観測/支払date、bond ratio、covariance符号、ρ=0/lag=0。-02: Ex30.2=1.00535/1206.42/.6302/760.25 pins、凍結係数近似域を明示。rate/asset jointのRN教師を追加。

**依存と独立参照:** 28.8→30.2→34.3/34.5。signed loadingとρを同時に反転して二重補正しない。

### §30.3 Quantos（pp.711–714） — unreviewed

出典草稿: `docs/prep/sections/ch30.md:55`。
**草稿の全要求**（まだ台帳要求として確定/受入されていない）

| ID | 原典上の要点（頁） | 検証の手がかり |
|---|---|---|
| D30.3-01 | 式30.4–30.6、FX は Y units per X（712） | FX を逆数にすると相関符号も変わる |
| D30.3-02 | Ex30.3 日経 quanto forward（712–713） | 15150.75 → 15260.23 |
| D30.3-03 | 式30.7、Ex30.4、Siegel’s paradox（713–714） | effective yield と100step価格 |

**既存で再利用できるもの:** vol11 §9相関表、CRR、Ex30.4 drift=.006/q=.029/N100=179.826 pin。

**残る受入作業/新実装:** -01: Y per XのFX quote/同一通貨numeraire比/逆FXのItô、Siegel説明。-02: Ex30.3=15150.75→15260.23 pins。-03: AmericanのspotFXと単一決済forwardFXを区別、独立PDE/欧州積分、N収束。100step一致を収束値としない。

**依存と独立参照:** 28.8/30.2→30.3→34.3。FX方向をterm fixtureに固定。

### §30.appendix Proof of the Convexity Adjustment Formula（p.718） — unreviewed

出典草稿: `docs/prep/sections/ch30.md:75`。
**草稿の全要求**（まだ台帳要求として確定/受入されていない）

| ID | 原典上の要点（頁） | 検証の手がかり |
|---|---|---|
| D30.appendix-01 | Taylor 展開・期待値・forward price の関係（718） | 一次項と二次項の期待残差 |
| D30.appendix-02 | 二乗偏差の近似と高次項の省略（718） | 小vol・小Tの誤差縮小 |

**既存で再利用できるもの:** 30.1の結果式と微分テストのみ。専用導出なし。

**残る受入作業/新実装:** -01: Taylor一次/二次項とforward期待価格。-02: 二乗偏差の近似、分散との関係、高次項省略と小σ/T誤差縮小。証明のみD3候補でも計算要求を一括N/Aにしない。

**依存と独立参照:** 30.1と同じyield逆変換教師/build共有。

### §31.1 Background（pp.719–721） — unreviewed

出典草稿: `docs/prep/sections/ch31.md:17`。
**草稿の全要求**（まだ台帳要求として確定/受入されていない）

| ID | 原典上の要点（頁） | 検証の手がかり |
|---|---|---|
| D31.1-01 | 式31.1–31.4、経路割引からzero rate（720） | 定数rの極限と MC 債券価格 |
| D31.1-02 | 式31.5、$P=e^{-r(t)(T-t)}$ の矛盾（720–721） | 全満期で PDE を満たすには drift / diffusion がゼロ |

**既存で再利用できるもの:** legacy ir_modelsの背景/分類説明、HW解析bondは後章基準。

**残る受入作業/新実装:** -01: Q経路積分→bond→zero、定数r極限/MC。-02: PDE導出とP=e^(-r(T-t))の残差、全満期flat stochastic curve反例。一般PDEを既存HWテストで検証済みとはしない。

**依存と独立参照:** 28.4→31.1→31.2。Gaussian積分r教師。

### §31.2 One-Factor Models（pp.721–726） — unreviewed

出典草稿: `docs/prep/sections/ch31.md:36`。
**草稿の全要求**（まだ台帳要求として確定/受入されていない）

| ID | 原典上の要点（頁） | 検証の手がかり |
|---|---|---|
| D31.2-01 | 3 SDE、平均回帰、Vasicek/CIRのA・B（721–724） | $P(T,T)=1$、PDE残差、MC割引 |
| D31.2-02 | CIRのFeller条件とVasicekの負金利（724） | 非中心χ²の遷移とEulerの境界bias |
| D31.2-03 | Ex31.1、$\hat D=B$、式31.11–12のbond diffusion（725） | finite difference のshort-rate感度 |
| D31.2-04 | 同じ局所標準偏差でVasicek/CIRを比較（726） | $\sigma_{\rm Vas}=\sigma_{\rm CIR}\sqrt r$ |

**既存で再利用できるもの:** legacy simulate_vasicek/vasicek_zero_curve、simulate_cir/cir_zero_curve、simulate_rb/rb_zero_curve。

**残る受入作業/新実装:** -01: 3SDEとaffine A/B、maturity/PDE/MC。-02: CIR exact noncentral χ²と境界bias、Vasicek負rate。-03: Ex31.1感度/hatD pin。-04: 局所vol一致の比較。現在CIRはゼロ切上げEuler、RB曲線は2次cumulant+clip。専用再利用コード/教師/境界検証必要。

**依存と独立参照:** 31.1→31.2→31.3/31.4。a→0、σ→0/CIR境界。ratesvol import/改変せず独立数値fixture比較だけ候補。

### §31.3 Real-World vs. Risk-Neutral Processes（pp.726–727） — unreviewed

出典草稿: `docs/prep/sections/ch31.md:57`。
**草稿の全要求**（まだ台帳要求として確定/受入されていない）

| ID | 原典上の要点（頁） | 検証の手がかり |
|---|---|---|
| D31.3-01 | Vasicekの $b^*$ と式31.13（726） | P→Q→P の往復 |
| D31.3-02 | CIRの $a^*,b^*$、bond excess drift（726–727） | drift展開一致、$a^*b^*=ab$ |

**既存で再利用できるもの:** 28.1/28.8の測度基礎、legacy Qモデル説明。金利P/Q変換の専用部品なし。

**残る受入作業/新実装:** -01: Vasicek b*=b+λσ/aとP→Q→P。-02: CIR a*=a−kσ、a*b*=ab、bond excess drift。P/Q構造/符号を新規明示しRN/解析bond diffusion照合。

**依存と独立参照:** 28.8/31.2→31.3→31.4。本文の負risk priceを市場の普遍法則にしない。

### §31.4 Estimating Parameters（pp.727–728） — unreviewed

出典草稿: `docs/prep/sections/ch31.md:76`。
**草稿の全要求**（まだ台帳要求として確定/受入されていない）

| ID | 原典上の要点（頁） | 検証の手がかり |
|---|---|---|
| D31.4-01 | 日次回帰から年率パラメータへ（727） | 下記係数換算、合成OUで回復 |
| D31.4-02 | P→Q変換とλのfit（727–728） | 固定データ・時点で目的関数再計算 |
| D31.4-03 | Table31.1の残差、推定期間依存（728） | モデル値と市場値を別列保存 |

**既存で再利用できるもの:** legacy fit_vasicekは当日curve直接fitで、日次系列→P推定→λfitの代用不可。

**残る受入作業/新実装:** -01: 250観測年の係数換算と合成OU回復。-02: 本文の1982-01-04〜2016-08-23米3mT-bill時系列OLS、P→Q/λ=-.175再fit。-03: Table31.1モデル9点と残差・期間依存。原データsnapshot/利用条件/欠測処理/当日r0不足。合成OUは方法だけ検証し歴史回帰/λ/表再現を未証明のまま記録。0.168印刷は0.0168との不整合を区別。

**依存と独立参照:** 31.3先行。入力不足をN/Aにしない。係数→a=.13625,b*=.01678899,σ=.01192179の独立算術と本番歴史再現は別証跡。

### §31.5 More Sophisticated Models（p.728） — unreviewed

出典草稿: `docs/prep/sections/ch31.md:98`。
**草稿の全要求**（まだ台帳要求として確定/受入されていない）

| ID | 原典上の要点（頁） | 検証の手がかり |
|---|---|---|
| D31.5-01 | 2因子SDEとB/C loading、式31.14（728） | 線形SDEの行列指数と一致 |
| D31.5-02 | Aは本文で省略、Technical Note14への参照（728） | 積分rateのGaussian cumulantから独立構成 |

**既存で再利用できるもの:** 専用2因子金利API/notebook/testsなし。既存1F HWは代用不可。

**残る受入作業/新実装:** -01: dr=(u−ar)dt+σ1dW1、du=−bu dt+σ2dW2、B/C、a=b極限とmatrix exponential比較。-02: AのGaussian積分分散構成。TechnicalNote14の公式を原本文のequilibrium特殊例へ正しく制限し相関規約を定める。モデル紹介のD3だけで2因子数値を除外しない。

**依存と独立参照:** 31.2/28.5→31.5→32.1/32.3。公式サイトTN14は検索索引内容あり、現行PDF本文取得失敗（詳細末尾）。

### §32.1 Extensions of Equilibrium Models（pp.732–736） — unreviewed

出典草稿: `docs/prep/sections/ch32.md:19`。
**草稿の全要求**（まだ台帳要求として確定/受入されていない）

| ID | 原典上の要点（頁） | 検証の手がかり |
|---|---|---|
| D32.1-01 | Ho–Leeのθ、A、式32.1–3（733） | 任意の入力curveを再現 |
| D32.1-02 | HWのθ、A/B、式32.4–8（734–735） | $a\to0$ でHo–Lee、解析bondとMC |
| D32.1-03 | BDT/BK/HW2Fの特徴（735–736） | BDTのσ一定ならa=0、対数rの正値性 |

**既存で再利用できるもの:** hull_white定数a/σのshift/解析bond/OU状態、legacy HL/HW/BDT/BK。

**残る受入作業/新実装:** -01: Ho–Lee θ/Aと任意curve。-02: HW θ/A/B、a→0と解析bond/積分r MC。-03: BDT/BK/HW2F特徴とBDT σ一定→a=0/positive lograte。HW params/hw_bはa=0不可、HL別入口か明示極限検証。旧MC fit/constantθ pathと完全curve fitted過程を区別。

**依存と独立参照:** 31.1/31.2/31.5→32.1→32.2/32.3/33.1。BK/時間依存σの本文説明を研究扱いで除外しない。

### §32.2 Options on Bonds（pp.736–737） — unreviewed

出典草稿: `docs/prep/sections/ch32.md:39`。
**草稿の全要求**（まだ台帳要求として確定/受入されていない）

| ID | 原典上の要点（頁） | 検証の手がかり |
|---|---|---|
| D32.2-01 | 式32.10とHWの $\sigma_P=\sigma(1-e^{-a(s-T)})\sqrt{(1-e^{-2aT})/(2a)}/a$（736–737） | parity、ゼロvol、Ho–Lee極限 |
| D32.2-02 | Ho–Lee $\sigma_P=\sigma(s-T)\sqrt T$（737） | HWのa→0 |
| D32.2-03 | coupon bondの臨界rとJamshidian分解、CIR非中心χ²への言及（737） | payoff単位の等価性、1次元積分 |

**既存で再利用できるもの:** hw_zcb_option、正coupon Jamshidian unit-strike、HW parity/σ0/独立1D forward求積。

**残る受入作業/新実装:** -01/-02: σP式とHo–Lee limit。-03: 一般coupon bond臨界r/正coupon単調根とCIR言及、cap/floor ZCB分解の教材。既存swaption専用unit-strikeを一般coupon仕様と同一視しない。CIR数値を追加するなら非centralχ²教師。

**依存と独立参照:** 32.1/29.2/29.3→32.2→32.5欧州基準。TN15公式取得可否は末尾。

### §32.3 Volatility Structures（pp.737–738） — unreviewed

出典草稿: `docs/prep/sections/ch32.md:59`。
**草稿の全要求**（まだ台帳要求として確定/受入されていない）

| ID | 原典上の要点（頁） | 検証の手がかり |
|---|---|---|
| D32.3-01 | Figure32.3の3形状（737–738） | 同じforward tenor・vol単位で比較 |
| D32.3-02 | mean reversionとhump（738） | 1因子極限、2因子の交差項 |

**既存で再利用できるもの:** legacy HJM normal vol/Black換算曲線、hw_b loading。

**残る受入作業/新実装:** -01: HL flat/HW1F下降/HW2F humpを同3m tenor/同vol単位で表示。-02: 1F極限/2F交差項、synthetic humpパラメータ、MC小時間bond ratio variance。implied cap volとinstantaneous fwd volを混同しない。

**依存と独立参照:** 31.5/32.1→32.3→33.1。原図は数値指定なし、形状再現の仮定をラベル化。

### §32.4 Interest Rate Trees（pp.738–740） — unreviewed

出典草稿: `docs/prep/sections/ch32.md:78`。
**草稿の全要求**（まだ台帳要求として確定/受入されていない）

| ID | 原典上の要点（頁） | 検証の手がかり |
|---|---|---|
| D32.4-01 | Figure32.4、Δt=1、確率(.25,.5,.25)、給付 $100(R-.11)^+$（738–739） | node別割引のrollback |
| D32.4-02 | Figure32.5の標準/上向き/下向きbranch（739–740） | 枝と後継nodeの対応、確率和1 |

**既存で再利用できるもの:** 金利木なし。stock CRR/trinomialはnode別rate割引器の代用不可。

**残る受入作業/新実装:** -01: Fig32.4 rates/payoffs、独立9経路列挙とrollback、B1.108650546/C.226209355/A.353128468 pins。-02: 3branchの後継node対応/確率。金利木基盤を新設。

**依存と独立参照:** 32.4→32.5。最小2step explicit treeを先に検証。

### §32.5 A General Tree-Building Procedure（pp.740–750） — unreviewed

出典草稿: `docs/prep/sections/ch32.md:96`。
**草稿の全要求**（まだ台帳要求として確定/受入されていない）

| ID | 原典上の要点（頁） | 検証の手がかり |
|---|---|---|
| D32.5-01 | $\Delta R=\sigma\sqrt{3\Delta t}$、jmax、3branchのモーメント整合（740–742） | 非負確率、平均・分散、Fig32.6 |
| D32.5-02 | αとQの前進較正、式32.11–14（743–746） | 全格子満期のbond価格が入力curveと一致 |
| D32.5-03 | HW/BK、負金利・shifted BK・多曲線（746–747） | 対数の定義域とcurveの役割 |
| D32.5-04 | 期間rate用の $\tilde A,\tilde B$、式32.15–17（748） | 同じRからΔt債価格を再現 |
| D32.5-05 | Ex32.1 / Table32.2–3、Fig32.9 American（748–750） | 解析値、格子収束、accrual込み行使 |

**既存で再利用できるもの:** HW bond/ZCB-option解析、Table32.3解析1.809294のpin。legacy BDT/BK bootstrapはMCで本文木ではない。

**残る受入作業/新実装:** -01: ΔR/jmax/3branch moments/nonnegative probability/Fig32.6。-02: α/Q前進curve fit。-03: HW/BK正値/負rate・shifted BK・multi-curve役割の本文範囲。-04: finite-period Rとinstantaneous r、Atilde/Btilde。-05: Table32.1/32.2 inputs、HW/BK Fig32.7/8 node/state price、Table32.3 tree N10…500、BK American Fig32.9 accrual/clean strike/K105と4/100step。最後2つ未再現。新木/rollback/schedule/格子収束/PDE教師が必要。

**依存と独立参照:** 32.1/32.2/32.4→32.5→32.6/34.5。期間rate変換と曲線補間を先に固定。早期行使点とcashflow点をgridへ。

### §32.6 Calibration（pp.749–751） — unreviewed

出典草稿: `docs/prep/sections/ch32.md:128`。
**草稿の全要求**（まだ台帳要求として確定/受入されていない）

| ID | 原典上の要点（頁） | 検証の手がかり |
|---|---|---|
| D32.6-01 | 二乗残差、パラメータ数、LM（749–750） | 合成市場から回復、再価格 |
| D32.6-02 | σ(t)の段差・曲率penalty（751） | penaltyゼロ/増加でfitとsmoothnessを比較 |
| D32.6-03 | Bermudan5–9年行使→5×5,6×4,7×3,8×2,9×1（751） | 行使日とunderlying満期10年の対応 |
| D32.6-04 | 固定aでimpliedσ、Black volとの区別（751） | Black price→HW impliedσの往復 |

**既存で再利用できるもの:** calibrate_hw1f定数a/σ、正European swaption basketと再価格テスト、vol26。

**残る受入作業/新実装:** -01: 合成truth/residual/複数初期値/識別性/失敗status。-02: σ(t)段差/曲率penalty、ゼロpenaltyとtradeoff。-03: 5×5…9×1 basketとunderlying10年Bermudan対応。-04: 固定aのHW impliedσ、Black volと区別。時間依存コード/診断は未実装。

**依存と独立参照:** 欧州価格→木/行使→較正の順。32.5/33.2と契約共有、全33.2完了を待つ必要はなくまずtree European/単行使Bermudanで較正基盤を構築。

### §32.7 Hedging Using a One-Factor Model（pp.751–752） — unreviewed

出典草稿: `docs/prep/sections/ch32.md:149`。
**草稿の全要求**（まだ台帳要求として確定/受入されていない）

| ID | 原典上の要点（頁） | 検証の手がかり |
|---|---|---|
| D32.7-01 | pricing factor数とhedging shock数を区別（751–752） | 1因子モデルでも複数bucketをbumpできる説明 |
| D32.7-02 | §29.4との接続（751） | zero curveとvol environmentを別shockとして表現 |

**既存で再利用できるもの:** vol07 DV01、HW再価格部品。

**残る受入作業/新実装:** -01/-02: pricing factor数とshock数の違い、outside-model curve/vol shockを説明し両画面で確認。純定性D3候補。数値を載せる場合は29.4と同一shock/PV01教師を付ける。29.4数値完了の代わりにしない。

**依存と独立参照:** 29.4共有。定性説明は32.1後に先行可能。

### §33.1 The Heath, Jarrow, and Morton Model — unreviewed

出典草稿: `docs/prep/sections/ch33.md:17`。
**草稿の全要求**（まだ台帳要求として確定/受入されていない）

| ID | 原典上の要点（頁） | 検証の手がかり |
|---|---|---|
| D33.1-01 | 債券 dP/P=r dt+v(t,T)dW から有限期間forwardと瞬間forwardの式を導く。v(t,t)=0、F=-∂T log P（755–757）。 | Itôの交差項と満期微分の符号を確認。債券拡散をvと置くとforward拡散は−∂Tv。 |
| D33.1-02 | 独立因子のforward拡散をσkと書けば μ(t,T)=Σk σk(t,T)∫t^Tσk(t,u)du（757）。 | 債券を数値積分して構成し、割引価格の平均ドリフトが0になることをMCで比較。 |
| D33.1-03 | σ一定→Ho–Lee、σ exp[−a(T−t)]→HW。一般HJMの非Markov性と計算量を説明（757–758）。 | 同じ初期曲線・ボラで解析ZCB/optionと比較し、有限因子数とMarkov性を同一視しない。 |

**既存で再利用できるもの:** legacy hjm_curvesはt0のexp vol/drift図だけ、一般HJM pathなし。HW解析特殊例。

**残る受入作業/新実装:** -01: bond v→forward −∂Tv、Itô/満期符号。-02: 多因子HJM drift=Σσ∫σ、discounted bond zero driftと二方向刻み収束。-03: HL/HW特殊例、一般nonMarkov、2^30状態。独立analytic bond/option+MC、有限因子とMarkov区別。

**依存と独立参照:** 28.4–8/32.1–3→33.1→33.2。一般任意vol製品engineは必須でなく、本文特殊例と多因子導出/検証を完了。

### §33.2 The BGM Model — unreviewed

出典草稿: `docs/prep/sections/ch33.md:47`。
**草稿の全要求**（まだ台帳要求として確定/受入されていない）

| ID | 原典上の要点（頁） | 検証の手がかり |
|---|---|---|
| D33.2-01 | δk=tk+1−tk と単利Fkを定義し、tk+1債券numeraireではFkがmartingale、rolling numeraireでは式33.12/33.16のドリフトを持つ（758–765）。 | numeraireごとの割引方法を明記。多因子のζiζkはベクトル内積になり、符号は使用測度による。 |
| D33.2-02 | spot caplet variance σk²tk=Σi=1..k Λk−i²δi−1 からΛを逐次復元（760–761）。 | Ex33.1/Table33.1を手計算。負の差分分散を無言で0へ切り上げない。 |
| D33.2-03 | 対数Euler更新、各リセット後の固定・割引、ratchet/sticky/flexicapのpayoffを分ける（761–765）。 | 同じcaplet価格を維持し相関だけを変更する対照実験。先読みせずpathごとにstrike/resetを更新。 |
| D33.2-04 | frozen-forward近似によるswaption variance、capとswapの異なるtenor、因子PCAと校正（765–767）。 | MCと近似価格を比較。式33.19はOCRが崩れているためPDF上で積・添字を再確認してから実装。 |
| D33.2-05 | CEV skew、BermudanのLSM/境界近似、因子数の実務上の論点を区別（767–768）。 | α=1のlognormal極限。単一因子でもBermudanが一般に正確になるとは要求しない。 |

**既存で再利用できるもの:** caplet_black/cap_black/swaption_black周辺基準。legacy lmm_initial_curve_zero_ratesはDF再構成のみ、dynamic LMMなし。stock price_american_lsmは不可。

**残る受入作業/新実装:** -01: tenor/state/支払measure・rolling drift・numeraire・内積factor。-02: Λ差分分散/Ex33.1/Table33.1、負varianceを黙ってclipしない。-03: logEuler・fix後凍結・rolling DF・ratchet/sticky/flexicap path reset、同caplet相関比較/60印刷MC価格。-04: frozen-forward swaption variance/別tenor/PCA/校正、式33.19 PDF確認。-05: CEV α=1/LSM独立評価/境界近似/因子論点。Table33.4 norm2行の丸めとMC SEを明記。flexicap初期strike/対象period未確定、3.43/3.58/3.61へ契約をfitしない。

**依存と独立参照:** 28.4–8/29.2–3/33.1＋32.5 exercise。caplet→Λ→joint paths→exotic cap→swaption→Bermudan。独立小木/Black/求積、LSM train/eval分離。

### §33.3 Agency Mortgage-Backed Securities — unreviewed

出典草稿: `docs/prep/sections/ch33.md:86`。
**草稿の全要求**（まだ台帳要求として確定/受入されていない）

| ID | 原典上の要点（頁） | 検証の手がかり |
|---|---|---|
| D33.3-01 | 信用保証と繰上返済リスク、pass-through/CMO/IO/POのcashflowを説明（768–769）。 | 繰上返済増加に対するIOとPOの方向性、tranche間のprincipal保存。 |
| D33.3-02 | 月次金利path→履歴依存prepayment→cashflow→Treasury曲線＋spreadで割引する評価手順（769–770）。 | σ=0かつprepaymentなしの極限を通常の償却表と比較。 |
| D33.3-03 | OASを市場価格への逆算とし、返済モデル・担保pool特性・rate modelに依存すると明記（770）。 | 固定cashflowではspreadと価格が単調逆向き。異なるprepayment仮定の価格/OAS感応度。 |

**既存で再利用できるもの:** MBS/prepayment/OAS専用部品なし。vol12 credit証券化とHW rate pathsは関連だけ。

**残る受入作業/新実装:** -01: Agency保証/prepayment/CMO/IO/POとprincipal保存。-02: 月次rate history→返済→CF→Treasury+spread評価、σ0/no-prepay償却極限。-03: OAS inverseとpool/prepay/model依存、price/spread単調。本文にpool/返済関数/価格がない。定性D3の理由は要求ごとに限定し、数値手順を除外しない。透明な合成償却/配賦/OASは機構だけ検証、実agency pool/OAS再現は未証明。

**依存と独立参照:** 32.1/33.1/2、Ch8→33.3→34.6。未来の実poolモデルを勝手に必須追加しないがP3原文要求を完了したと過大主張しない。

### §34.1 Variations on the Vanilla Deal — unreviewed

出典草稿: `docs/prep/sections/ch34.md:20`。
**草稿の全要求**（まだ台帳要求として確定/受入されていない）

| ID | 原典上の要点（頁） | 検証の手がかり |
|---|---|---|
| D34.1-01 | step-up/amortizing元本、支払頻度、accrual day countを脚ごとに指定（773–774）。 | 各couponを独立手計算したcashflow表と照合。元本交換の有無を別条件とする。 |
| D34.1-02 | BS34.1の両脚をterm sheetからschedule化（774）。 | 固定100M対変動120M、半年対四半期、ACT365対ACT360の違いを保持。 |
| D34.1-03 | forward projectionとOIS discountを分け、basis swapを説明（774–775）。 | 等しい元本/頻度に戻せば標準IRSと一致。異なるreference rateのcurveを同一視しない。 |

**既存で再利用できるもの:** swaps標準/seasoned IRS、swap_rate/discount、rfr calendar/convention/daily accrual部品、vol07動物園。

**残る受入作業/新実装:** -01: 両leg別notional/freq/daycount/principal exchange。-02: BS34.1 100M固定2% ACT365半期 vs 120M SOFR ACT360四半期/date。-03: separate projection/OIS/basis、standard limit。休日Following/U.S. calendar細部要確認。generic leg schedule/table/手計算PV教師が必要。

**依存と独立参照:** 29.2/3 schedule→34.1→34.2/34.4。規約を先に固定してfixture単位の私有lesson部品から。

### §34.2 Compounding Swaps — unreviewed

出典草稿: `docs/prep/sections/ch34.md:50`。
**草稿の全要求**（まだ台帳要求として確定/受入されていない）

| ID | 原典上の要点（頁） | 検証の手がかり |
|---|---|---|
| D34.2-01 | coupon発生と未払残高への利息付与を別ステップで記述（775–776）。 | Ex34.1の毎年残高を再帰と幾何級数で独立計算。 |
| D34.2-02 | additive spread Q[1+(R+s)τ] とmultiplicative Q(1+Rτ)(1+sτ)を区別しforward実現法の条件を明記（776）。 | s=0で一致、非zero spreadでは交差項の差を確認。 |
| D34.2-03 | BS34.2をschedule付きで解釈し、最後の一括支払を割引（775）。 | 標準逐次払と支払日が異なることをcashflow表で確認。 |

**既存で再利用できるもの:** vol07別param compounding実演とdiscount。専用残高API/Ex34.1 pinなし。

**残る受入作業/新実装:** -01: coupon/未払利息2step再帰と別coupon積和。-02: additive vs multiplicative spread、s0/交差項、forward-realization厳密条件。-03: BS34.2 final payment schedule。Ex34.1 exact fixed12.474084M/float15.731520M/PV2.895848743Mと原典切捨て2.895を両方保存。

**依存と独立参照:** 34.1/28.4→34.2→34.5 compounding cancelable。TN18のFRA条件を原本文に対応。

### §34.3 Currency and Nonstandard Swaps — unreviewed

出典草稿: `docs/prep/sections/ch34.md:84`。
**草稿の全要求**（まだ台帳要求として確定/受入されていない）

| ID | 原典上の要点（頁） | 検証の手がかり |
|---|---|---|
| D34.3-01 | 各通貨のcashflowを評価しdomestic−spot×foreignの符号で集約（776–777）。 | 通貨とreceive/payを反転するとFX換算後の価値が符号反転。元本交換も確認。 |
| D34.3-02 | curve/basisを整合させ、market mid-priceで初期価値0になる条件を明記（777）。 | 曲線・spreadを一つずつ変え、何を校正してzeroを作ったかを残す。 |
| D34.3-03 | CMS/非標準resetのconvexity、支払日のtiming、cross-currency quantoを区別（777）。 | 各correlation/vol=0の極限で標準forward評価へ戻る。 |

**既存で再利用できるもの:** currency_swap_valueは既知CFのdomestic−spot×foreign、vol07通貨例、Ch30式部品。

**残る受入作業/新実装:** -01: leg/FX quote/receive-pay/principal exchange反転の単位。-02: mid-market0のcurve/basis条件と何をfitしたか。-03: CMS convexity/timing/quanto適用とzero limit、joint rate/FX教師。一般multi-curve/collateral対応を既存CF合計だけから主張しない。

**依存と独立参照:** 34.1/30.1–3→34.3。cashflow zero-coupon/FX-forward分解を別計算。

### §34.4 Equity Swaps — unreviewed

出典草稿: `docs/prep/sections/ch34.md:114`。
**草稿の全要求**（まだ台帳要求として確定/受入されていない）

| ID | 原典上の要点（頁） | 検証の手がかり |
|---|---|---|
| D34.4-01 | total return index、resetごとの株式単位、元本Lを定義（777–778）。 | price indexのみの場合に配当を別途加える条件を説明。開始/支払直後のnet PV0を複製で確認。 |
| D34.4-02 | BS34.3のequity return L(I1/I0−1)とSOFR脚の同日決済（778）。 | 同一Lと同一期間でborrowing＋index investmentのcashflowが再現されること。 |
| D34.4-03 | 中途時点のleg PVとnet MTM、既知利息と未確定利息を分離（778–779）。 | 原典L(E−E0)/E0をそのまま単独legの一般PVとせず、Technical Note19の導出条件を確認。 |

**既存で再利用できるもの:** vol07説明、rfr実績CFとdiscount部品。equity reset専用なし。

**残る受入作業/新実装:** -01: total return index/reset shares/L/複製PV0。-02: BS34.3四半期同日settlement。-03: known/unknown RFR split、途中leg PV/net MTM/符号。TN19はLIBOR定義、SOFR観測ラグへ機械転記不可。単独equity leg L(E/E0−P)と本文L(E−E0)/E0のnet financing解釈を導出で解決。

**依存と独立参照:** 34.1→34.4。cash index＋borrowing複製とdiscounted legを独立計算。公式TN19検索索引で式確認、現行PDF未取得（末尾）。

### §34.5 Swaps with Embedded Options — unreviewed

出典草稿: `docs/prep/sections/ch34.md:144`。
**草稿の全要求**（まだ台帳要求として確定/受入されていない）

| ID | 原典上の要点（頁） | 検証の手がかり |
|---|---|---|
| D34.5-01 | accrual coupon QL n1/n2と通常couponから除く日次binary列（779）。 | 一日当たり額QL/n2、観測日/支払日、休日の参照fixingを一致させる。 |
| D34.5-02 | Black binaryのQL/n2×P(0,si)N(d2*)とtiming補正（779–780）。 | natural payment ti+τと実際siの違い。全日条件成立/不成立の極限。 |
| D34.5-03 | 解約者・receive/pay・残存期間からswaption向きを決める（780）。 | 自分が受固定10年6% swapを6年時点で解約可能→long 6×4 payer。相手に解約権を与える場合はshort option。 |
| D34.5-04 | 複数解約日はBermudan、compoundingでは残高もexercise状態に含める（780–781）。 | 支払後にfloatingをparにする条件、receive/payでmax/minの向き、spreadの4段階近似を明示。 |

**既存で再利用できるもの:** vol07cancelable説明、European Black/HW Jamshidian部品。accrual/Bermudan/cancelable compoundingなし。

**残る受入作業/新実装:** -01: QL n1/n2、daily fixing/休日/日割binary列。-02: payment-date DF・N(d2*)とtiming補正。-03: 解約側とlong/short、receive6%10年→6×4 payer。-04: multi-exercise/Bermudan、未払複利balance state、max/min、spread4段階近似。新obs schedule/binary/exercise/state教師必要。

**依存と独立参照:** 29.3/30.2/32.5–6/33.2/34.2。European decomposition→小木全path→複数行使、LSMは独立eval下界。

### §34.6 Other Swaps — unreviewed

出典草稿: `docs/prep/sections/ch34.md:175`。
**草稿の全要求**（まだ台帳要求として確定/受入されていない）

| ID | 原典上の要点（頁） | 検証の手がかり |
|---|---|---|
| D34.6-01 | index-amortizingをMBS型のrate依存元本として、commodity swapをfixed-for-floating数量契約として説明（781）。 | 元本が予定済みのamortizingと区別。数量×単価の単位を確認。 |
| D34.6-02 | 他章のasset/TRS/CDS/variance swapへ参照を張る（781–782）。 | 原資産、受払対象、元本/時価、credit eventを比較表にする。 |
| D34.6-03 | BS34.4のspread構造と利率増幅を説明し、不透明な商品設計/理解不足の教訓を示す（782）。 | CMTは%表示、債券価格はpar100表示として同じ式へ入れる。 |

**既存で再利用できるもの:** vol07/12商品説明、26.16 variance swap等関連API。専用P&G/index-amortizingなし。

**残る受入作業/新実装:** -01: rate依存元本とscheduled amortizing区別/commodity quantity×unit。-02: asset/TRS/CDS/variance比較参照表。-03: P&G spread％/CMT％/bond par100/receive-pay、50USD/bblと15.25%を独立算術。実市場valuationは本文入力なし、payoff算術を当時価格再現としない。説明主体D3でも算術はN/Aにしない。

**依存と独立参照:** 33.3/34.1/24/26.16/37.3参照。説明＋小算術は先行可能、index-amortizing pricing engine発明不要。

## 安全な具体的実装順序

1. **M28 §28.3を先に閉じる。** 現行accepted28.1/2の235セルをbaselineに、条件付きmartingale定義/ratio Itô/正値numeraireを6小節程度へ整理。独立joint Gaussian条件付き教師→private lesson→notebook/portal→数値改変拒否/fresh実行/両画面→D1→台帳という順。既存§5の誤解を生む説明を本節範囲で修正する。
2. **§28.4/28.5/28.8の共通測度仕様を先に固める。** 年率単位、signed loadings、correlated Gaussian basis、new/old RN方向、joint (state, integral rate)を明記。28.4/5→28.8、28.6/7を各要求で閉じる。一般相関の退化とprice invarianceを独立教師で確認。
3. **Ch29の既存Black商品へ規約/参照を追加。** 29.1/3は同buildの別受入、29.2は13要求をschedule・strip・negative-rate・RFRへ分ける。29.4のshock/quote rebuildは商品後、32.7説明と共有。
4. **Ch30を28.8から閉じる。** 30.1+appendix教師を共有、30.2はlag/ρ極限、30.3はFX方向/Ex30.3/独立American PDE。印刷N100と収束値を別記録。
5. **31.1/2→31.3/4、並行して31.5参照を解決。** まずGaussian積分/VasicekとCIR厳密遷移、RBの近似境界。31.4の実系列snapshot/2016 curve/r0が揃うまで歴史再現はpendingを維持。合成回復を先に実装できる。31.5は公式TN14とmatrix-exp独立教師のモデル対応を確認。
6. **32.1/2/3→32.4→32.5。** HL/HW2Fの欠落を補い、まず原典2step金利rollbackを全pathで検証。次にmean-reversion branch→state-price curve fit→ZCB European→positive-coupon単行使→HW/BK Americanとclean/dirty→格子収束。Table32.3/BK Fig32.9は独立解/原典nodeの照合を必須にする。
7. **32.6と33.1/33.2を段階化する。** 単行使/多行使木ができたらtime-dependent σとpenalty/basket較正基盤。HJM特殊例→1caplet Black→Λ→rolling LMM paths/fix freeze→ratchet/sticky→swaption近似→CEV/LSM/Bermudan。校正と行使の依存を循環させずEuropean→exercise→calibrationを守る。flexicap入力を先に原典で解決。
8. **34.1/2/4はschedule/reset共有、34.3はCh30後、34.5はexercise後。** 33.3/34.6は構造説明/小算術から先行可能だが、P3全要求をD3で削らない。各節の5観点と不足を明示したまま、37節の閉鎖を追跡する。

## 取得不足・原典/合成の区別

| 要求 | 今回確認できる/合成で検証できること | 完了にはなお残ること |
|---|---|---|
| 31.4-01〜03 | 印刷OLS係数→年率、合成OU推定/有限標本bias、印刷curve列の保存 | 歴史生データの日付/欠測/単位、原回帰、当日r0、λ=-.175と9モデル点の再現。合成置換はこれらを未証明 |
| 31.5-02 | 独立Gaussian積分cumulant/matrix-expでAを構成 | TN14がno-arbitrage HW2Fで本文equilibriumのΘ=0特殊例を含む点の照合、相関/initial u/curve境界 |
| 32.5-05 | HW解析pinと小木枝/state価格の草稿再計算 | Table32.3の木6価格、BK American Fig32.9全node/4step/100step、finite-period Rとr、coupon/accrual処理 |
| 33.2-03〜05 | 単一caplet Black、Λ算術、factor norm/variance、合成契約のLMM/LSM検証 | 60印刷MC価格の誤差つき再現、flexicap初期strike/対象period、原PDF式33.19。価格へ契約をfitしない |
| 33.3 | 明示合成償却とCF保存/配賦、fixed-CF spread inverse/monotonicity | 実pool/prepay/OASの市場再現は本文入力不足で未証明。教材に手順/仮定依存を明記 |
| 34.1/2/4 | 年数fixtureによるleg PV/compound/reset identity | BS例dateの米営業日/Following/accrual/観測ラグを確定、TN19とSOFR版本文のleg/net式関係 |

§31.4印刷b=0.168は草稿で画像確認した不整合。0.0168を採用するなら訂正理由と両値を保存。§34.2原典2.895は途中切捨て、exact2.895848743を強制丸めしない。§33.2 Table33.4年1/9のnormは丸め誤差候補で誤植断定不可。

## 著者公式一次資料のブラウズ（2026-10-04）

検索で著者サイトの11e Technical Notes索引とTN14/TN19の索引テキストを確認した。本文PDFへの直接openはerror page（HTMLの404Handler）、索引openはtimeout後error page。検索索引の内容取得と現行PDFの完全取得を区別し、今回はPDFファイルをダウンロード/保存していない。

| 公式URL | ブラウズ結果と利用可能範囲 |
|---|---|
| [Technical Notes索引](https://www-2.rotman.utoronto.ca/~hull/TechnicalNotes/) | searchで11e索引31件確認。direct HTTPS timeout、HTTP→HTTPS error page。TN14 Hull-White Two-Factor、15 coupon bond、16 nonconstant tree、18 compounding、19 equity、31 Ho-Lee/HWの対応を確認 |
| [Technical Note14](https://www-2.rotman.utoronto.ca/~hull/technicalnotes/TechnicalNote14.pdf) | search索引にA(t,T)、correlation項、integrated σP varianceの本文あり。direct lower/upper-case pathはerror page。検索断片を完全取得扱いしない |
| [Technical Note19](https://www-2.rotman.utoronto.ca/~hull/technicalnotes/TechnicalNote19.pdf) | search索引にLIBOR設定のequity/net swap式あり。direct lower/upper-case pathはerror page。receive-equityはL E/E0−L(1+R0τ0)/(1+Rτ)というnet MTMを示すがSOFR lag拡張は別検証 |
| [Technical Note18](https://www-2.rotman.utoronto.ca/~hull/technicalnotes/TechnicalNote18.pdf) | searchでLIBOR compoundingとmultiplicative spread/FRA分解の冒頭確認。direct error page。原本文SOFRとの規約差を残す |
| [Technical Note15](https://www-2.rotman.utoronto.ca/~hull/technicalnotes/TechnicalNote15.pdf) / [16](https://www-2.rotman.utoronto.ca/~hull/technicalnotes/TechnicalNote16.pdf) / [31](https://www-2.rotman.utoronto.ca/~hull/technicalnotes/TechnicalNote31.pdf) | directいずれもerror page、今回は本文未取得 |

追加のWSL urllib直接取得でもwww-2の索引/TN14/TN19はHTTP200だがContent-Type=text/htmlで%PDF magicなし。www.rotmanのTN14/TN19別host候補はHTTP404。HTTP200をPDF取得成功と判定しない。

上記は著者公式ドメインのURL/検索索引を使った確認。第三者転載は受入教師に採用していない。現行PDFの入手不能はTN14/TN19の内容を推測で埋める許可ではない。原repo PDFの該当導出または一次論文で独立構成できる部分を先行し、参照照合はpendingに残す。

## 監査の機械チェック

- 台帳section数=37、accepted=2、unreviewed=35。章別数={28: 8, 29: 4, 30: 4, 31: 5, 32: 7, 33: 3, 34: 6}。
- 残35節の草稿要求表を全件抽出: 118行、空の節0。現行accepted2節の明示要求12件も列挙。
- 要求表の本文を人手で要約置換せず原草稿行で保存。既存/不足/依存の監査は節ごとの追加説明。
- API/legacy/notebook/testsを静的照合。pytest/数値実行/browser再検証はこの監査では未実施。
