# M30 §28.5 Extension to Several Factors — 原典・private契約・独立参照の準備

- 日付: 2026-10-04。**準備資料。実装・節受入・D1・releaseの実行ではない。**
- 参照root: /home/kazumasa/worktrees/m29/johnhull。
- 対象: P3全37節のうち§28.5。D28.5-01/02を保持し、後続§28.6–28.8/Ch33へ必要な多因子規約を作る。
- 作成物: /tmp/m30-source-design.md、/tmp/m30-fixtures.py、/tmp/m30-fixtures.json。
- 原典: Hull 11e Global Edition, options, futures and other derivatives 11th.pdf、印刷/PDF pp.679–680。
- 原典の確認: pdftotext -layout の抽出後、両ページをPNGへレンダーし画像を確認した。
  - /tmp/m30-source-pages.txt
  - /tmp/m30-source-p679.png
  - /tmp/m30-source-p680.png
- 補助参照: docs/prep/sections/ch28.md、docs/prep/design/P3_DESIGN.md、docs/P3_REQUIREMENT_AUDIT_2026-10-04.md。
- 源泉が不足しているM30要求は現在見つかっていない。**本節には印刷された数値価格、表、Example、番号付きの新しい公式はない。** 以下の数値はすべてsynthetic教師。これを原典数値pinと表示しない。

## 1. 原典の範囲をページで確定

| 場所 | 原典の内容 | 受入で確認する事項 |
|---|---|---|
| p.679 §28.5開始 | §28.3/28.4の結果をn個の独立因子へ拡張 | 単因子だけの演示で本節を完了としない |
| p.679 脚注7 | 非独立因子も直交化できるため、独立性の条件は本質ではない | 一般相関、PSD・退化を含むfactorizationと価格/共分散の保存 |
| p.680 前半 | 伝統的risk-neutral worldではf/gの各資産driftはr、独立Wiener loadingはs_fi/s_gi | 実際のvolatilityとsigned loadingを分ける |
| p.680 中段 | 別の整合的なworldでは資産driftはr+Σλ_i s_fi、r+Σλ_i s_gi。現実世界もその一つ | 同じ因子基底のλとloading。予測/リスク価格の推定機能は約束しない |
| p.680 §28.5最終段落 | gで定義するworldはすべてのiでλ_i=s_gi。独立WienerとItôによりf/gのdriftが0 | 比の**相対**Itô drift、条件付き平均、有限GBMでの可積分性 |
| p.680 §28.5最終段落 | 式28.15以降の前2節の結果も成立 | 同じ給付のQ経路割引価格とg-numeraire価格の一致 |
| p.686 Problem28.12 | ln f/ln gの過程から§28.5のmartingale結果を証明する課題 | 対数driftと相対driftを混同しない補助導出。本文に数値pinを追加する根拠ではない |

§28.5はp.680の§28.6見出しより前で終了する。式28.26/28.27とBlackの確率金利導出はM31（§28.6）の要求に残す。
p.679のannuity式28.23–25自体はM29範囲だが、「その結果が多因子でも成立する」という接続は本節で説明する。

## 2. 要求草稿の具体化案

元のD28.5-01/02は削除しない。例えば次の6要求へ分解し、原典要求と試料の対応を固定する。

| 仮ID | 元要求 | 内容 | 独立数値/教材/画面での受入 |
|---|---|---|---|
| MF01 | D28.5-01 | n因子のQ drift rと一般world drift r+λ・s | n=1縮約、3因子signed例、既存28.2との同じ基底 |
| MF02 | D28.5-01 | 多因子の比のItô drift、λ=s_gでzero drift | 一般driftの独立式とg driftを比較。符号誤り改変がFAILする |
| MF03 | D28.5-01 | 真の条件付きmartingale | 3観測比×4未来horizonで解析/求積/MC。現在値へ条件付ける |
| MF04 | D28.5-01 | 式28.15以降の価格結果の拡張 | 同じfのcall給付をQと複数gで評価。単なる各資産の平均では代用しない |
| MF05 | D28.5-02 | 相関因子の直交化 | C=L Lᵀ、s独立=s相関 L。共分散/比の分散/価格を保存する |
| MF06 | D28.5-02 | PSD退化、基底回転、入力契約 | ρ=±1/near-singular、zero loading、無効C・非有限/temporal/shape拒否、同じpathの回転保存 |

全要求へsource/API/numerical/notebook/browserの5軸を付ける。導出だけの説明をD3で受け入れて多因子数値要求を落とさない。

## 3. 多因子の数学規約

### 3.1 独立因子

d f/f = μ_f dt + s_fᵀ dZ、
d g/g = μ_g dt + s_gᵀ dZ、
dZ dZᵀ = I dt。

loadingとλはyear^-1/2、μ/rはyear^-1、hはyear。loadingには符号がある。
資産のvolatilityは ||s|| であり、各成分を正値volatilityとして絶対値に変えない。

X=f/gについて

a_X = μ_f − μ_g + ||s_g||² − s_fᵀ s_g、
dX/X = a_X dt + (s_f−s_g)ᵀdZ。

一般world μ_f=r+λᵀs_f、μ_g=r+λᵀs_gなら

a_X = (λ−s_g)ᵀ(s_f−s_g)。

したがってg worldでλ=s_gならa_X=0。
対数のdriftはa_X − 0.5 ||s_f−s_g||²であり、zeroにはならない。
定数loadingの正値GBM・有限horizonでは全lognormal momentが有限なので、
E^g[X_(t+h)|F_t]=X_t。一般モデルではzero driftだけでtrue martingaleを断言しない。

### 3.2 相関因子

元のWienerをdW dWᵀ=C dtとして、資産loadingは同じ相関座標の列vector s_f/s_g。
Cはdimensionlessの対称PSD correlation matrix。C=L Lᵀ、dW=L dZとする。
独立座標のloadingは列ならLᵀs、rowならsᵀL。

比の式は

a_X = μ_f − μ_g + s_gᵀ C s_g − s_fᵀ C s_g、
v_X = (s_f−s_g)ᵀ C (s_f−s_g) >= 0。

g worldでは

μ_f^g = r + s_fᵀ C s_g、
μ_g^g = r + s_gᵀ C s_g。

**相関座標でλ=s_gをそのまま通常の内積へ代入しない。**
本文のλ=s_gは独立座標での式で、独立λ=Lᵀs_g。
相関座標に μ−r=λ_corrᵀ s という記法を置く場合、
gのλ_corr=C s_gとなる。Cを2回掛けてもいけない。

PSD退化ではLが非可逆でも全式と価格は成立する。C^-1や「whiteningで逆行列を取る」
操作は不要。脚注7の直交化の実装は、相関noiseを独立noiseから生成する分解として説明すると
rank欠損で壊れず、入力risk-priceの識別問題も増やさない。

### 3.3 価格不変性と独立密度

定数rのsynthetic教師で、Qの正値無配当gは

D_g = (g_T/g_t) exp(−r h)、E^Q[D_g|F_t]=1、
dQ^g/dQ|_(t,T)=D_g。

同一call H=max(f_T−K,0)に対して

price_Q = exp(−r h) E^Q[H]、
price_g = g_t E^g[H/g_T]。

両者は同じ価格。gのloadingを変えてもfのQ市場が同じなら価格は変わらない。
Qのf/gがmartingaleであることは不要で、一般にa_X^Q = s_gᵀC s_g−s_fᵀC s_gは非zero。

M29は確率金利とT/pay/annuityの測度差を扱う。M30のGBM教師の定数rは
多因子loading・相関・基底保存の検査に適した限定fixtureである。
「多因子なら定数金利に戻る」と説明しない。Itôの点ごとのdrift相殺自体はrの状態依存性を仮定しない。

## 4. 既存部品の再利用と新privateの最小契約

| 既存資産 | 再利用 | 境界 |
|---|---|---|
| hullkit.factor_risk:factor_contributions/excess_return/required_return | 独立座標のλ・loading、final factor axis規約、n=1の対応 | docstringが明記する通り相関/whitening APIではない。公開signatureを拡張しない |
| hullkit._martingales:ratio_drift/numeraire_drifts/ratio_conditional_mean | n=1極限、既受入教材・guardの参照 | 現在はONE Wiener専用。そのままn次元へ積を足した結果をpublicに出さない |
| hullkit._martingales:_numeric_inputs | 日時/durationをfloatへ落とす前のtemporal拒否、有限実数検査 | factorの形とCのPSD検査は新たに必要 |
| hullkit.sde:girsanov_weights | 尤度比の方向説明の参照 | terminal1資産からWを回復する単因子版。多因子RNを無理に再利用しない |
| 28.2の直交回転教材/独立参照 | loading回転が内積を保存する説明 | 一般相関Cのfactorization・singular入力の受入を代用できない |
| M29のGaussian/測度部品（実装確定後） | 有限実数/PSDの契約を揃える候補 | 完成前のprivate仕様へ依存を作らない。M29の現行仕様は別途確認 |

新たにprivate module（例えば _multi_factor_martingales.py）に次を置く案。
__init__.pyのexportやpublic signature、production dependencyの追加は不要。

1. correlation_factor(C) -> L。
   - まず単一N×NのCのみ。leading batch C対応は本節の要件ではない。
   - finite real/symmetric/unit-diagonal/PSDを検証する。
   - eigen分解でL Lᵀ=Cを再構成し、rank欠損を受け入れる。正定値だけならCholeskyも可。
   - 数値丸めレベルの負eigenvalueだけ0へclipし、再構成誤差を検査する。
   - 明らかな負eigenvalueをnearest-PSDへ修正しない。nonsymmetricを無条件symmetrizeしない。
   - L自体は一意ではない。eigenvectorの符号・縮退部分空間を原典pinにしない。

2. factor_ratio_drift(mu_f,mu_g,s_f,s_g,C=None) -> scalar/batch annual drift。
3. factor_numeraire_drifts(r,s_f,s_g,C=None) -> (mu_f^g,mu_g^g)。
4. factor_ratio_conditional_mean(value,mu_f,mu_g,s_f,s_g,h,C=None) -> mean。
   - C=NoneはI。s_f/s_gは最後のaxisが同じ非empty factor数N。
   - leading batchだけbroadcast。rate/value/hはfactor axisを持たず、reduced batchへbroadcast。
   - scalar loadingは拒否し、n=1はlength-1 vectorと明示する。
   - empty batchは許すがempty factor axisは拒否。domain検査はbroadcast前に実施する。
   - value>0、h>=0。μ/r/loadingは負値・zero可。NaN/inf/complex/temporal拒否。
   - 無効shape、overflow、有限正値meanのunderflow-to-zeroはValueError。
   - scalar marketはfloat、batchはndarray。dtype coercion（numeric string/bool等）は既存private規約と
     一致させる方が範囲が小さい。強化するなら仕様と既存callerの検証を先に固定する。

密度やpath生成はlessonの内部で厳密Gaussian samplingを行えば足りる。
汎用multi-asset Monte Carlo公開APIや完全なmulti-factor short-rate modelを本節で作る必要はない。
両者を「P3から除外」する意味でもない。後者は§31.5/32.1/Ch33の各原典要求で残る。

## 5. /tmpの独立教師

実行:

    /home/kazumasa/projects/.venv/bin/python /tmp/m30-fixtures.py

hullkitを一切importしない。既存数値関数や公開Black公式を参照priceに使わない。
stdlib math + numpy + scipy.integrate.quadのみで教師を構成した。

### 5.1 共通synthetic市場

f0=100、g0=80、K=105、r=4%年率、h=1.5年。
Q下fのcall価格をlognormalの1次元求積で計算する。

Gの価格教師は、f/gのjoint Gaussianをf方向とg固有方向へ分ける。
g固有normalの指数momentを解析積分し、f方向をSciPyで求積する。
同じ数値関数/同じBlack formulaを2回呼ぶ比較ではない。

signed factor 11ケース:

| ID | 主要内容 | rank(C) | ratio Q drift | ratio annual variance | 同一call価格 |
|---|---|---:|---:|---:|---:|
| independent_3 | independent 3因子、s_f=(.20,-.10,.15)、s_g=(.12,.08,-.18) | 3 | .0642 | .1477 | 13.588476206717441 |
| correlated_3 | C_12=.45、C_13=-.30、C_23=.20 | 3 | .06684 | .09514 | 9.038314313908826 |
| correlated_3_negative_g | 同じf/Cでg loadingの符号を反転 | 3 | .07124 | .10394 | 9.038314313908826 |
| correlated_3_zero_g | 同じf/Cでg loading=0 | 3 | 0 | .0305 | 9.038314313908826 |
| negative_covariance_2 | ρ=-.60、s_f=(.30,.10)、s_g=(-.15,.12) | 2 | .1041 | .2137 | 12.808199045747472 |
| singular_plus_ratio_zero | ρ=1、s_f=(.20,-.10)、s_g=(.08,.02)。effective loadingが同じ | 1 | 0 | 0 | 5.433418591288858 |
| singular_minus_2 | ρ=-1、s_f=(.20,.05)、s_g=(-.10,.15) | 1 | .1 | .16 | 7.84882080505781 |
| one_factor_negative_g | s_f=.30、s_g=-.15 | 1 | .0675 | .2025 | 15.058829959708504 |
| zero_f_2 | fはdeterministic、gはstochastic | 2 | .036 | .036 | 1.1147239736538803 |
| zero_all_2 | f/g両方deterministic | 2 | 0 | 0 | 1.1147239736538803 |
| near_singular_2 | ρ=1−1e−12 | 2 | -7.20e−15程度 | 2.88e−14程度 | 5.433418591298516 |

注: tableのnear-singular driftは丸めによる値で、その絶対値を誤った非zero driftの教師にしない。
JSONにはC/loadings/eigenvalues/L/independent loadingsと丸め値をすべて残した。

### 5.2 条件付き検査

各市場のobserved ratio=.65/1.25/2.0とfuture h=0/.25/1/2.5の12状態、
合計132状態の解析値と1次元Gaussian求積を保存。

- under g: E[Xfuture|Xt]=Xt。
- under Q: E[Xfuture|Xt]=Xt exp(a_Q h)。
- under g: E[Xfuture²|Xt]=Xt² exp(v_X h)。

MCは各市場262144 path、seed=285730+case index。
Q/Gの厳密GBM terminalを直接構成し、
E^Q[D_g]、E^g[f/g]、E^Q[D_g f/g]、QとGの同一callを比較する。
MC結果はpilotで、公開受入記録ではない。独立incrementから観測状態へ条件付けるlesson MCを追加する際も
同じconditional analytic truthとSEを使い、初期の単一平均だけをmartingaleの証明にしない。

### 5.3 実際のscratch結果

- 11市場のQ/G求積価格差の最大: 3.552713678800501e−15。
- factor L Lᵀの再構成差最大: 3.3306690738754696e−16。
- conditional meanと求積の差最大: 8.881784197001252e−16。
- conditional second momentと求積の差最大: 8.881784197001252e−16。
- 基底を直交回転し、対応するnormal coordinateも回転した同一pathの差最大: 2.6645352591003757e−15。
- MCの非退化比較の|z error|最大: 2.161467009371749 SE。
- ±12σで切った求積の解析tail upper bound最大: 1.9661911028715037e−25。
- 各caseのg ratio relative driftは0、abs<=1e−15。
- 正定値Cでは独立にCholeskyでもloading内積を計算し、共分散の一致をJSONへ保存。

tail boundは指数normalのtilted tailをerfcで直接計算した。
価格の上界はcall payoff<=f、conditional momentは既知の指数normal momentを使う。
quad自身の絶対/相対許容差とtail切断誤差を混同しない。

### 5.4 実装前に固定する受入threshold案

- 符号とdriftの解析式/API: absolute 1e−12程度、必要なら|入力|に比例するrelative補助。
- price API/求積: absolute 1e−9、ここでのtailははるかに小さい。
- correlationのreconstruction、covariance、rotation invariant: scaled machine tolerance。
- conditional analytic/quad: absolute 1e−10。
- MC: 非退化は5SE、退化SE≈0はabsolute tolerance（1e−12等）。
- Cの丸め負eigenvalue許容案: 64 eps N ||C||_2。
  unit-diagonal/symmetryは別判定で、安易なnearest-PSD repair禁止。
- 最終thresholdはROOTが実装前preflightで固定し、受入試料の結果を見て緩めない。

## 6. 教材・図・配布画面の案

vol10ではM28/M29の追加済み節をbaselineに保存し、新規§6D相当へ6小節を追加する案。

1. 複数loadingと同じ因子基底。volatilityは成分の絶対値の和ではない。
2. Itôのcross termとratio relative/log driftの差。一般λからλ=s_gを代入。
3. 条件付きmartingale。3観測状態、未来horizon、平均とSE。QとGを区別。
4. 相関C→独立basis。Lの列がrisk factors、λとloadingへ相関を二重適用しない。
5. ρ=±1とnear singular。異なるvectorでもeffective ratio varianceが0になり得る。
6. 同じfのcallをQと3種類gで価格評価。GBM教師の定数rという限定、後続節へ接続。

図4枚の案:

| 図 | traceで見せること | 操作/画面で確認 |
|---|---|---|
| factor_ratio_ito | 項 μ_f−μ_g / s_gᵀC s_g / −s_fᵀC s_g と相殺 | independent/correlated、負loadingで符号と値 |
| factor_ratio_conditional | 条件付きratio mean、Q/G、MC±1.96SE | 3状態/horizon、名称/縦軸/判定帯5SEの区別 |
| factor_basis_covariance | 相関basisと独立basisの共分散・ratio variance | rotation/ρ±1で退化とPSDを明示 |
| factor_measure_price | 同じcallのQ/G価格と3g loading | price同一、ratio分布の差、求積/MC SE |

独立basisの成分は非一意なので、単に個々のloadingが前後で同じと表示しない。
保存されるのはasset covariance/ratio variance/価格。
表の「correlated_3/negative_g/zero_g」は同じQのf市場なので価格比較に適する。
独立/相関のCを変えた市場ではf volatilityも変わり、価格が違ってよい。

M30新規browser16状態、Book/portalの同じ数値/操作を検査する。
旧notebook source/outputの保存、Plotly/registry integration、public/private countは実装後に現行baselineで照合する。
M29がacceptedならM30のD1は既受入29節の再検査になり、M30受入後は全体30/306、P3 5/37となる。
これは順序の予測であり、このメモがM29/M30の受入を宣言するものではない。

## 7. 改変拒否と契約検査

数値改変の例:

- ratio driftのcross covarianceの符号を反転。
- gのμ_fをr+s_f・s_gへ変え、Cを省略する。
- Cをdouble applyする。
- correlated g risk-priceを独立sgと同一視する。
- ρ=1退化にinverse/Cholesky-onlyを使う。
- Q/G価格のg0またはpathwise1/g_Tを外す。
- 対数driftをratio相対driftとして出す。
- conditional meanの「現在ratio」をf0/g0へ固定する。

入力/shapeの例:

- C nonsquare、factor N mismatch、empty N、scalar loading。
- 明らかなnon-PSD（ρ=1.01）、unit-diagonal不一致、nonsymmetric、NaN/inf。
- ρ=±1はvalid、zero loadingとnegative rate/signed loadingはvalid。
- h<0、value<=0、temporal/datetime/timedelta、complex、nonfinite。
- invalid設定とempty batchの組合せでも拒否。
- rateやhがfactor axisへ誤broadcastしない。
- 有限入力でもoverflow/positive meanのunderflow-to-zeroを拒否。

## 8. 次節以降を残す境界

- §28.6: 確率金利T-forward worldでのforward lognormal仮定とBlack公式。
- §28.7: 交換給付、dividend spotと再投資numeraire、ratio varianceとMargrabeの導出。
- §28.8: new/old numeraire比、測度間drift補正の向き、非取引変数、absolute drift。
- §31.5/32.1: 2因子short-rate modelの原典公式/TechnicalNote14。M30の2factor GBMを
  2factor Hull–White実装と呼ばない。
- Ch33: HJM/LMMのmodel-specific volatility/drift、tenor/fixing/measure、calibration/exercise。

P3全37節と各原典の市場/較正/歴史入力要求は維持する。M30のsynthetic教師で
§31.4のhistorical calibrationやTechnicalNote本文不足をacceptedへ置き換えない。
