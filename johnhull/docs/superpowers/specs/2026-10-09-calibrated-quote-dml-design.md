# 較正込み市場クオートGreeksのDML — 調査・研究設計

- 更新日：2026-10-09
- 状態：**実装開始。解析教師・独立参照を対象検証中。学習本実験・研究採否は未完了。**
- 調査時のコード基準：`736f3a8a8f2d5b504871dd063509c9319a1cc92a`
- 依頼：既存モデルの追加より、価格・較正・Greeks・ヘッジをつなぐ研究を優先できるか調べ、実行可能な計画にする。
- [実施手順](../plans/2026-10-09-calibrated-quote-dml.md)／[既存研究計画](../plans/2026-09-27-research-backlog.md)／[収録索引](../../../CONTENTS_INDEX.md)

## 1. 調査の結論

**RB-F07の較正感応度とRB-F05の正しい微分教師を接続する、小さな比較実験を推奨する。**
最初に固定CFのポートフォリオで配線を検証し、次に同じ曲線で割り引くGBMデジタルを使う。
解析解のある問題で、教師誤差・座標・損失の重み・ヘッジ数量・総費用を分離する。
高コスト商品の高速化や実市場の動的ヘッジは、ここでの比較を終えてから別計画にする。

次の点を調査で明確にした。

1. **DML＋較正、クオート感応度、市場情報を入力するNNは既存研究がある。** 組合せだけの新規性は主張しない。
2. **滑らかな正方較正では、内部Greekから市場Greekへ変換できる。** 比較相手にも正しいchain ruleを使う。
3. **較正商品のクオートと、保有ヘッジ契約の固定金利は別。** ショック後に契約を新しいpar条件へ書き換えない。
4. **デジタルの金利Greekは、分布のscoreと割引因子の微分の両方が必要。** spot用LRMをそのまま流用しない。
5. **小さな問題ではNNが速度で負ける可能性が高い。** 解析・低次元の回帰も対照に含め、否定的な結果を完成した成果として残す。

### 研究候補の比較

| 候補 | 再利用できるもの | 追加で難しいもの | 推奨 |
|---|---|---|---|
| 単一曲線＋デジタルのquote DML | F07の解析Jacobian・F05の教師・CPU学習 | 多変量Greek、座標を揃えたloss、固定契約ヘッジ | **最初の1本**。解析参照があり原因を分離しやすい |
| 同一較正面のモデル横断ヘッジ | vol14/19/20/21、F04メモ、deep hedging | 市場生成／評価モデルの分離、時間・取引・CF・費用の台帳 | 2本目の候補。静的面が合うことと動的頑健性を区別する |
| 多曲線の統合リスク／P&L | vol23/26、金利補足、F07 | 曲線間の依存、日付・fixing、複数曲線のquote units | 単一曲線の比較後。既存F07 v2/v3への承認を兼ねない |
| 増分XVA＋IM・資本 | Ch9増分CVA・IM資金費用、vol16/28 | IM算定・担保動学・資本定義・規制／商品条件 | 独立した計画へ。既存の増分CVAを再実装しない |
| execution／cross-impact接続 | 金利計算、別プロジェクトの資産 | 約定・流動性・執行状態の境界 | johnhull本研究の完了条件に含めない |

この推奨を受けた本人の「研究ロードマップを完遂せよ」により、quote DMLを先行する。既存backlogの離散バリア→F04→F08→F06と後続候補を保持し、全研究の完了をquote DMLだけで代用しない。

## 2. 一次資料の調査記録

確認日はいずれも2026-10-09。12項目を調査した。本文を確認した範囲とabstractのみの確認を区別する。
論文・公式ライブラリの性能結果は独立再現していない。PDF本文・コードの転載は行わず、リンクと要約を保存する。

| ID | 一次資料・版 | 確認した範囲 | この計画への反映・限界 |
|---|---|---|---|
| Q01 | Henrard, [Adjoint Algorithmic Differentiation: Calibration and Implicit Function Theorem](https://quant.opengamma.io/Adjoint-Algorithmic-Differentiation-OpenGamma.pdf)、8頁の著者／OpenGamma公開版 | §2–3、陰関数と較正、§4の例 | solverの反復を微分せず残差から感応度を計算する根拠。記載の速度比を本実装へ移さない。既存S003とも照合 |
| Q02 | Huge–Savine, [Differential Machine Learning v4](https://arxiv.org/html/2005.02347v4)、2020-09-30 | §1.2、§2、Appx1–3の関連部分 | 正しい微分ラベル、サンプルと期待値の区別、前処理、differential regressionを確認。固定予算で必ず改善するという保証に読み替えない |
| Q03 | Glasserman–Karmarkar, [Differential ML with a Difference v2](https://arxiv.org/html/2512.05301v2)、2026-04-22 | §3.1–3.6、§4 | 不連続payoffのpathwise bias、LRMの短期分散、離散過程に対する不偏性の範囲。既存S002の密度式の指摘を保持し、教師は標準GBMから独立に導出 |
| Q04 | Polala–Hientzsch, [Parametric DML for Pricing and Calibration v2](https://arxiv.org/html/2302.06682v2)、2023-02-19 | §4.3、§6、abstractのモデル範囲 | パラメータ／契約を含むDMLと較正は既存研究。小さい価格の相対誤差・sampling依存に注意。本研究ではtestを見てsamplingを変更しない |
| Q05 | Sridi–Bilokon, [Applying Deep Learning to Calibrate Stochastic Volatility Models v2](https://arxiv.org/html/2309.07843v2)、2023-09-25 | §2.1、§5、Tables15/19/20 | DML価格器を使うHeston較正の近接研究。速度だけでなく元の価格器でrepricingを確認する。著者の速度比・パラメータ一致を採否基準に転用しない |
| Q06 | OpenGamma Strata, [MarketQuoteSensitivityCalculator](https://strata.opengamma.io/apidocs/com/opengamma/strata/pricer/sensitivity/MarketQuoteSensitivityCalculator.html)、[公式曲線・PV01例](https://opengamma.com/strata-and-multi-curve-calibration-and-bucketed-pv01/) | 公式API契約、Jacobian metadataとparameter→quote sensitivityの説明 | リスク座標・curve metadataを明示する実装例。APIの閲覧でありStrataとの数値照合は未実施。既存L01の実装確認記録を参照 |
| Q07 | Cao–Chen–Hull–Poulos, [Deep Learning for Exotic Option Valuation v2](https://arxiv.org/abs/2103.12551v2)、2021-09-07 | 書誌・abstract。HTML本文は取得できず | 市場のvolatility featuresを直接入力するVFAは既存。本研究の「選んだモデルを再較正した価格写像」とVFAの価格対象を同一視しない |
| Q08 | Blondel et al., [Efficient and Modular Implicit Differentiation v5](https://arxiv.org/html/2105.15183v5)、2022-10-12 | §2のroot／stationary／KKT、§3の関連説明 | 最小二乗は最適性条件、制約付きは正則なKKTを微分する。近似解の誤差・非微分点を考慮する。JAX等を追加する理由にはしない |
| Q09 | Buehler et al., [Deep Hedging](https://arxiv.org/html/1802.03042) | §1–2の市場・取引・費用・情報の定義 | 動的ヘッジには時系列と自己資金・CF・費用の台帳が必要。瞬間ショックの再評価を動的ヘッジ性能と呼ばない |
| Q10 | Bennedsen–Lunde–Pakkanen, [Hybrid scheme for Brownian semistationary processes](https://arxiv.org/abs/1507.03004)、[著者機関の出版記録](https://spiral.imperial.ac.uk/entities/publication/eb2b3840-271c-42b2-bb92-b7674b33ac8d)、2015初稿／2017出版 | abstract・出版記録 | rough教師のMC誤差と時間離散化を分ける必要性。今回はroughを実装せず、hybridの数値性能も未再現 |
| Q11 | Huge–Savine, [Axes that matter: PCA with a difference v2](https://arxiv.org/abs/2503.06707v2)、2025-03-18 | 書誌・abstract | 差分情報を使う次元削減は後続候補。v1では既知の解析的な低次元構造を対照に使い、PCA研究を増やさない |
| Q12 | Molent–Vellekoop, [Neural Calibration of a Complete Market Model v1](https://arxiv.org/abs/2608.30867v1)、2026-08-31 | 書誌・abstract | 市場価格から離散木を作り複製へ接続する近接研究。モデルの追加候補であり、本研究のquote DMLや費用込みヘッジ改善の証拠ではない |

**調査範囲の限界：** 関連文献を対象にした探索で、網羅的なsystematic reviewではない。
VFA・deep calibration・PDML・implicit differentiationとの関係は確認できたが、同一条件のquote／parameter DML比較の新規性は確定していない。
新規性を追う場合は、過剰決定較正の残差方向、不連続性、active-set切替、識別不良とヘッジへの増幅のどれかに別途絞る。

## 3. 現行コードの到達段階

| 実装 | 確認した到達段階 | そのまま使えない範囲 |
|---|---|---|
| [F07計算](../../../hullkit/src/hullkit/_quote_risk.py) | 単一曲線・正方較正、解析J、随伴、単位・rank・増幅診断 | 多曲線、最小二乗、価格の直接quote依存はない |
| [F07テスト](../../../hullkit/tests/test_quote_risk.py) | 手計算・独立brentq・bump・座標／残差不変性・補間変更 | 今回の候補モデルやNNを検証したテストではない。2026-10-09再実行24 passed |
| [F05教師](../../../hullkit/src/hullkit/_digital_teachers.py) | 固定rateのGBM digital、spot LRM・厳密conditioning・CRN・ramp・SE | 曲線quote Greek、割引の金利微分、複数risk labelsは未実装 |
| [F05学習](../../../../deep_hedge_price/src/deep_hedge_price/_digital_dml.py) | 2入力spot/T、train-only尺度、CPU学習、価格とspot delta | 7入力・6Greek、parameter→quote loss、汎用曲線の商品価格には変更せず専用private実験を作る |
| [vol18損失](../../../../deep_hedge_price/src/deep_hedge_price/pricing_losses.py) | 主にspot deltaのDML、価格／Greek head比較 | 既存公開APIを多変量quote用へ変更しない |
| [Ch9 XVA](../../../hullkit/src/hullkit/_xva_foundations.py) | 増分CVA、IM増減の資金費用 | IM算定・資本エンジンではない。優先4の全機能が未実装という扱いもしない |

金融教師はtorch-free hullkit、学習はdeep_hedge_price、教材はresearchに置く境界を維持する。

## 4. 数学的契約

### 4.1 較正の総微分

列勾配、残差 $R(\theta,q)=0$ とし、局所微分可能・正方 $R_\theta$ が可逆の場合、

$$
A=\frac{d\theta}{dq}=-R_\theta^{-1}R_q,\qquad
g_q=g_q^{direct}+A^\top g_\theta.
$$

$R_\theta^\top a=g_\theta$ を解けば $g_q=g_q^{direct}-R_q^\top a$。
v1は $R=m(\theta)-q$、$R_q=-I$、$g_q^{direct}=0$ なので既存F07を使える。
実装では逆行列を明示的に作らずlinear solveを使う。

パラメータDMLの評価も $A^\top\widehat g_\theta$ へ変換する。
quote metric $W_q$ での損失は内部座標では $A W_q A^\top$ に対応する。
内部座標の対角重みだけのlossとの差を、quote DMLの理論的優位と呼ばない。

### 4.2 解析参照を持つdigital

固定した年時刻 $T$、strike $K=100$、cash payout 1、無配当、$\sigma=20\%$。
各シナリオ内では曲線を決定論的とし、$D=P(0,T)$、$R_T=-\log D$、$v=\sigma\sqrt T$ とする。

$$
S_T=S_0\exp(R_T-v^2/2+vZ),\quad
d_2=\frac{\log(S_0/K)+R_T-v^2/2}{v},\quad
V=D\Phi(d_2).
$$

$a_q=\nabla_qR_T$ なら、

$$
\Delta_S=\frac{D\varphi(d_2)}{S_0v},\qquad
g_q=D\left[-\Phi(d_2)+\frac{\varphi(d_2)}v\right]a_q.
$$

この2項は割引と分布の寄与。quote Greekの符号は一律に正ではない。
曲線柱への $a_\theta=T w(T)$ を既存補間から求め、F07の随伴でquote座標に変換する。
商品条件 $K,T,\sigma$ とspotはquote bumpで固定。spot bumpでは曲線を固定する。
これは確率金利・quanto・金利／株式相関を含むモデルではない。

### 4.3 不連続教師と負の対照

$Y=D1_{\{S_T>K\}}$ に対し、同じIID $Z$ のLRM教師は

$$
\widehat\Delta_S=Y\frac Z{S_0v},\qquad
\widehat g_q=Y\left(-1+\frac Zv\right)a_q.
$$

`-1`を落とすと割引微分が欠ける。素朴なpathwiseではspot教師0、quote教師 $-Y a_q$ となり、境界の寄与を落とす。
どちらも負の対照として独立積分と比較する。

$\alpha=1/2$（中間時点 $\alpha T$）の厳密conditioningでは

$$
b=\frac{\log(S_0/K)+R_T-v^2/2+\sigma\sqrt{\alpha T}Z}
 {\sigma\sqrt{(1-\alpha)T}},\qquad
Y_c=D\Phi(b),
$$

$$
\widehat\Delta_c=\frac{D\varphi(b)}{S_0\sigma\sqrt{(1-\alpha)T}},\quad
\widehat g_{q,c}=D\left[-\Phi(b)+\frac{\varphi(b)}{\sigma\sqrt{(1-\alpha)T}}\right]a_q.
$$

中間時点の曲線依存も含めると、決定論的rateの積分は $R_T$ にまとまる。
独立1次元積分・既存固定rate教師で検証し、rampは別payoff、CRNは有限bumpの推定と記録する。
主学習は解析教師を使い、MC教師の学習比較はv1の完了条件に含めない。

### 4.4 ヘッジ契約

5本の較正商品を各元本100万の固定契約として保有する。中心シナリオ $q_0$ のクオートを契約金利 $k_i$ に固定する。
receive-fixed側の価格は、預金 $N[(1+k\tau)D(\tau)-1]$、FRA $N[(1+k\Delta)D(t_2)-D(t_1)]$、swap $N[k\sum\Delta_iD(t_i)+D(t_n)-1]$。
FRAはこの実験では期末支払型。既存の期初決済FRAとは契約を区別する。

株式1単位を6本目のヘッジとし、risk vectorはspot delta＋5 quote Greek。
$B_{ji}=\partial H_i/\partial x_j$、$x=(S_0,q)$ として

$$
Bh=-g_x,\qquad
\varepsilon(\delta x)=V(x+\delta x)-V(x)+\sum_i h_i[H_i(x+\delta x;k_i)-H_i(x;k_i)].
$$

全方式で $B$ は独立参照の同一行列を使い、対象商品のGreekの差だけを比較する。
これは時刻を進めない瞬間ショック再評価で、動的・自己資金ヘッジの成績ではない。
ヘッジ列順は株式、預金、FRA、2/3/5年swap。risk行順はspot、5 quote。
ヘッジ列は既に「株式1単位／rate契約100万元本」に揃い、solveでは $L=\operatorname{diag}(1,10^{-4},\ldots,10^{-4})$ を両辺に掛けて $(LB)h=-Lg_x$ を解く。
riskの表示はspot単位とquote 1bp。元本を変える検査では列の変化に対して数量が逆比例し、保有cashflowsと再評価が一致することを確認する。
rank不足は黙って擬似逆やridgeへ逃げず、そのヘッジ問題を未定義と記録する。

## 5. 調査用の小さな数値確認

既存コード＋使い捨てscratchで式と契約差を確認した。製品モジュール・受入記録は作っていない。
独立参照は自作の逐次brentq、`math.erfc`、正規密度の`scipy.integrate.quad`。
quote bumpは $10^{-5}$（0.1bp）、元の契約条件を固定した。

| S | T（年） | digital価格 | 独立価格積分との絶対差 | 再bootstrap Greekとの差（最大、payout/1bp） |
|---:|---:|---:|---:|---:|
| 80 | .05 | 0.0000003195708125 | 4.77e-22 | 6.15e-20 |
| 95 | .25 | 0.3102829851 | 5.56e-17 | 9.69e-15 |
| 100 | 1.5 | 0.5039021628 | 1.12e-16 | 1.18e-14 |
| 110 | 4.5 | 0.5548854270 | 1.12e-16 | 2.00e-13 |
| 120 | 5 | 0.6023741960 | 5.56e-16 | 8.82e-14 |

LRMのscore項を独立積分した値と解析quote Greekの最大差は9.49e-20/1bp。このscratch比較では較正Jacobianを共有しており、score／割引項の検証である。
曲線を通した全Greekの別方式検証は、上表の独立再bootstrap bumpで行った。実装計画では参照Jacobianも自作complex-stepへ分離する。
5年swap quote +1bpでは、元本100万・元の固定金利3.6%の保有swapは **−451.6857814**。
固定金利を新quote3.61%へ書き換えると **−1.11e-10**（新しいpar契約）。
この差を負の対照として固定する。上の丸め表を数値オラクルにはしない。

## 6. v1実験の固定仕様

### データと分割

| 項目 | 設定 |
|---|---|
| 曲線 | F07と同じ単一曲線、zero線形補間・区間外zeroフラット |
| 5クオート | 6か月預金3%、6×12 FRA3.2%、2/3/5年swap3.3/3.45/3.6%。各中心から独立一様±50bp |
| 商品条件 | K100、payout1、sigma.20、spot80–120、T.05–5年。Tはlog-uniform、日付・day countなし |
| 主学習 | 解析価格＋spot delta＋5 quote Greek。zero Greekと $A=dz/dq$ も保存 |
| train | 256市場曲線×8契約=2048行。小データ比較は先頭64曲線×8=512行の入れ子部分集合 |
| validation | 別の64曲線×8契約=512行。診断のみ、checkpoint／設定選択に使わない |
| test | 別の128曲線×8契約=1024行。契約は§5の5組＋(100,.5),(100,1),(110,3)の8組 |
| RNG | `SeedSequence([20261009, split])`、split0/1/2でtrain/validation/test。market IDとcontract IDを保存 |
| 独立性 | 同一曲線の8行を1群とする。分割・bootstrap・CIを行単位でなく市場曲線単位で行う |
| MC診断 | S95/100/105×T.05/.25/1.5/4.5、各65536 IID normals。seed1107、pilot seed6017。trainの教師には使わない |

pilotはモデル比較のtestを開く前に実行。生成失敗や数学的に無効な曲線を黙って除外・置換しない。
失敗件数・入力・理由を保存し、設計上の問題があれば新しいprotocol版として修正する。

### 比較器

| 名称 | 入力・loss | 評価されるrisk |
|---|---|---|
| Exact＋adjoint | 原曲線・解析式・随伴 | 参照値。再bootstrap bumpは別検証器 |
| Q-price NN | q5＋spot＋T、価格のみ | 物理入力へのautograd、spot＋q5 |
| Theta-price NN | zero5＋spot＋T、価格のみ | zeroへのautogradを $A^\top$ でquoteへ変換 |
| Theta-DML NN | zero5＋spot＋T、内部Greekの対角尺度loss | 同じ変換を行う。損失metric差の対照 |
| Theta-quote-metric NN | 同じ内部入力、予測Greekをquoteへ変換してloss | Q-DMLと同じ市場risk metric。**公平性の主要対照** |
| Q-DML NN | q5＋spot＋T、価格＋市場quote Greek＋spot delta | 市場入力のautograd |
| Reduced price／differential ridge | $(\log(S/K),R_T,\log T)$ の全3次以下monomial（20項） | 独立な特徴微分＋$a_q$。既知の低次元構造を利用する強い対照 |

digitalの曲線依存は $R_T$ 1スカラーに要約できる。7入力NNだけを比べて次元削減の利益をquote DMLの利益と混同しない。
既存PolynomialRidgeの3次特徴は全ての交差項を含むとは限らないので、専用private実験では20項を明示する。

NNは全方式で7→64→64→1、tanh、線形出力、CPU float64・1 thread、Adam lr.001、batch256、512 updates、seed11/29/47。
入力の保存順はq5（またはzero5）、spot、T。NNにはrate5、$\log(S/K)$、$\log T$ を標準化して渡し、autogradは標準化前の物理入力に対して取る。
評価riskの保存順はspot、q5。Theta方式ではzeroへの5勾配に $A^\top$ を掛け、spot勾配と合わせてこの順へ並べ直す。
同じseedでは同じ初期重み・同じbatch順を使う。全方式の設定は同一で、結果を見て個別に調整しない。
512 updatesが120秒を超えるfitはbudget failureを残し、同updates比較の成功扱いにはしない。
5方式×2サイズ×3seed=30 fits。ridgeは各サイズでprice／differential各1回、`lstsq`を使い係数罰則1e-8、切片は罰しない。

特徴の平均・標準偏差、価格mean/std、GreekのRMSはtrainのみ。
物理単位のlossは価格項＋$\lambda/6$×6Greek項、lambda1。
scaleの下限はprice std1e-8、各raw-unit Greek RMS1e-8。
Theta-DMLのみ内部Greekのtrain尺度、Theta-quote-metricはQ-DMLと同じquote尺度を使う。
Tはnuisance inputで、maturity Greek・gamma・vegaはv1の学習ラベル／採否に含めない。

## 7. 誤差と検証

**主実験の価格参照にはMC／時間格子／空間格子誤差がない。** 解析教師・浮動小数・較正残差・NN／回帰近似を分離する。
MC診断は別表にmean・SE・解析2次モーメント・sample sizeを保存する。
将来roughへ進む場合はMC・時間離散化・教師推定値との差を別に評価する。

| 検査 | 基準案（主学習前にprotocolへ固定） |
|---|---|
| 解析価格 vs 独立密度積分 | abs1e-12、rel1e-10。tailはabs中心 |
| 解析Greek vs 独立score積分 | raw quote／spotでabs1e-10、rel1e-9 |
| 再bootstrap bump | q幅1e-4/1e-5/1e-6、安定域でraw quote abs1e-7＋rel1e-6。bump幅ごとの値を残す |
| 座標／単位変換 | zero→quote、zero→log DF、rate decimal→bpで価格・物理riskが許容差内一致 |
| NNのGreek取り出し | 固定した小NNのautograd vs 入力中央差分、abs1e-8＋rel1e-6 |
| MC教師 | 12 nominal条件で6SE＋独立参照誤差。SEのpath axis、discount derivativeを確認 |
| rare event | S80/T.05は解析・積分で確認。expected hit count<20は通常6SE検査の対象外として事前分類。ゼロhit/SEを正しさの証拠にしない |
| 固定契約ヘッジ | 独立CF価格・risk行列・数量・ショック再評価に一致。契約resetの負の対照を拒否 |
| raw arrays→report | 保存prediction・risk・hedge・timingから全指標を再計算。保存済みPASSフラグだけで合格させない |

数値比較は許容誤差つき。SHAは成果物の完全性だけに用い、数値オラクルには用いない。
許容差変更はpilotの根拠とprotocol版を保存し、main testの結果を見て緩めない。

## 8. ショック・OOD・費用・採否

### ショック評価

test各中心で6本のヘッジを組み、spot0/±1%と、5 quoteの単独・平行・steepener（後2本+／前2本−、中央0）の各±1bp/±10bpを別々に評価する。
同時spot＋rate shockはspot±1%×parallel±10bpの4組。Tは変えず、時間価値・carry・途中CFは追加しない。
価格再評価は全方式で独立参照、hedge quantitiesだけが方式によって変わる。
ゼロショックで残余0、参照Greek hedgeの微小ショック残余が2次で減ることを検証する。

費用は実市場の推定ではなく教育用stress。
rate商品は「参照の自バケットPV01絶対値×半spread 0/.1/.5/1bp」、株式は「spot×0/1/5bp」を1ヘッジ単位の入口費用とする。
$\sum_i|h_i|c_i$ と残余を別に表示し、組合せごとに同じ価格／費用を使う。動的turnoverや利益率へ一般化しない。

### OODと失敗

q箱・spot・T・instrument schedule・pillar・補間・strike・sigmaのprotocol適合を確認する。
sigma変更、pillar／schedule変更、負rate・±100bp quote、spot70/130、T.01/6は明示的なOOD。
negative rate自体を数学的な無効入力と呼ばない。
中心箱内で較正が失敗／rank不足／増幅>10となる入力は安全な通常予測の対象にしない。
安全wrapperは既存較正と診断を毎回行い、警告／bounds違反時は解析器へfallback、較正不能なら失敗を返す。
q／spot／TのOODと、解析器が対応するstrike／sigma変更は、較正可能なら解析器へfallback。
pillar／schedule／補間の変更はv1の固定曲線契約外なので `unsupported_context` として予測を返さない。元の曲線で代用しない。
生NN出力・安全wrapper出力・fallback件数を別に保存し、fallbackがNNの誤差を隠さないようにする。
q-only NNの単体速度と、安全wrapperの総速度を別に計測する。
v1は安全wrapperを省いて「較正不要」と主張しない。例外をclipして正常値に偽装しない。
wrapperの検査範囲はdomain・較正・価格boundsであり、通過したNNのGreek精度を保証しない。risk誤差は独立参照との比較結果で判断する。

### 指標と費用

- 価格：MAE/RMSE/p99/max、payout1単位、T／moneyness別。ゼロ近傍の相対誤差を主指標にしない。
- risk：spotと各quoteの物理単位、train RMSで正規化した6Greek RMSE、p99/max、ゼロbucketへの漏れ。
- hedge：数量の単位別差、残余RMSE/p99/max、入口費用。参照Greekの曲率残余と推定Greekの誤差を分ける。
- seed：全3seedを個別に残す。市場曲線群単位のpaired bootstrap 2000回、seed20261010、95% CIは各seed条件付き。seed数3から一般的な有意性を主張しない。
- 時間：教師・変換・optimizer setup・学習・load・較正・price・price＋6Greek・OOD/fallback・ヘッジsolveを分離。単一件／batch32／batch1024をwarmup後100反復、median/p95を記録。
- キャッシュ：同一marketで曲線を一度共有する場合と、各行で再較正する場合を別に測る。入力数・calibration count・CPU/threads/versionを記録する。
- 総費用：$C(N)=C_{offline}+N C_{online}$。差の分母が正の場合だけ損益分岐点を出す。学習器単体やbumpだけとの比較で速度採用を決めない。

**研究完了と性能採用は分ける。**
教師・単位・分割・比較器・固定契約ヘッジ・保存結果の再計算が検証され、全方法の良い／悪い結果を報告できればv1研究完了。
NNの精度改善や速度改善は完了の必須条件ではない。
教育上の有用性、Greek改善、費用を含む実行上の有用性を別判定にする。
事前に固定する検証仮説は、(H1) Q-DMLとQ-priceのrisk差、(H2) Q-DMLとTheta-quote-metricの差、(H3) Greek誤差から固定契約ヘッジ残余への伝播、(H4) 解析・reduced ridgeを含む総費用の比較。
H1/H2の改善を述べる場合は3seed全てで正規化risk RMSEが低下し、各seedのpaired差の95% CI上端が0未満であることを必要とする。price・各bucket・hedgeの悪化は別に併記し、方向の違う指標をまとめて「改善」と呼ばない。
利用側の許容risk誤差はまだ指定されていないため、速度／精度のPareto表と損益分岐点を残し、速度採用へ自動昇格しない。
公開API・本番利用・実市場での採用は本計画で承認しない。

## 9. 成果物・段階・資源

置き場は `research/RB-F07/quote_dml/`（F07 v1のファイルは保持）。仮の新RB番号は付けない。
教師・hedgeはhullkitの新private modules、torchはdeep_hedge_priceのnew private module。
授業／比較結果はJSON+NPZ、再実行器、artifact-only notebook3図、READMEに保存する。
全モデル台帳の再編やBook／portalへの追加はこのv1の前提にしない。

| 段階 | 成果 | 完了条件 | 規模の目安 |
|---|---|---|---|
| 調査・設計 | 本文書・実施計画 | 文献／数式／コード／制限・手順を照合 | **今回完了する範囲** |
| 1 教師・参照 | 解析／LRM／conditioning、独立bootstrap／積分 | 教師・割引項・単位の検証 | M |
| 2 データ・学習 | 分割、5NN＋2ridge、chain rule | train-only尺度・公平metric・全seed記録 | M |
| 3 固定契約ヘッジ | B、数量、再評価、費用stress | 契約reset・rank不足・単位の負の対照 | M |
| 4 結果・採否 | 保存配列・再計算・研究3図 | 改竄検出・artifact-only実行・レビュー | S–M |
| 後続 | 多曲線／最小二乗／model hedge／XVA | v1の結果で選ぶ別計画 | 未着手 |

実装・対象検証・文書化は合計 **約8–16時間のagent作業**を暫定見積りとする。
30 fitsのwatchdog上限は合計60分で、独立参照・計時・文書・レビュー時間は別。
所要時間は未実測の計画値で、人日やGPTモデル間の固定換算ではない。段階1終了時に実測から更新する。
GPU・実市場データ・新しいproduction dependency・public API変更は不要。

## 10. 後続へ進む条件

1. **高コストの金利商品：** 金利optionの教師と曲線quote Greekを独立検証し、価格器・較正の総費用が代理器を必要とすることを確認する。
2. **最小二乗較正：** 定数Wと残差rに対し $H=J^\top WJ+\sum_i(Wr)_i\nabla^2m_i$ を含む最適性条件を微分する。非ゼロ残差でGauss–Newtonとの相違をテストする。
3. **制約付き較正：** 正則なactive setのKKT、片側変化・非微分点を明示。最小二乗／制約の追加をv1の暗黙の要件にしない。
4. **モデル横断ヘッジ：** 同じ較正誤差・取引商品・時刻・CF・費用を固定し、市場生成モデル・価格モデル・方策の3軸を別々に評価する。
5. **rough／MC教師：** 有限格子の価格 $V_h$、MC教師 $\widehat V_{h,M}$、連続時間参照Vを区別。対照モデル側も同じ精度条件で計時する。

本編P0–P8・306節の受入状態は変えない。今回の計画は既存モデルの正確性／本番利用可能性の新たな認定ではない。
