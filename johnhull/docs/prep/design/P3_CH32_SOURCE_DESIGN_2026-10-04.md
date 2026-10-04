# P3 Ch32 原典・設計・独立数値棚卸し

更新: 2026-10-04。**読み取り専用の将来準備。実装・節受入・製品検証ではない。**
対象: Hull 11e Global Edition 第32章 pp.732–752、7節・21 draft requirements。
repository/Git/public API を変更していない。product pytest/browser/D1 は実行していない。

## 1. 結論と今回の重要な訂正

1. **Table32.3 は6行すべて原入力から再現した。** 旧著者 DerivaGem 2.01 は expiry=1095日直後の1096日 curve knotを残す。最終ノードの期間だけ `delta_star=1/365`。a=.1/sigma=.01 の Euler 木、最終alphaと式32.15–17にこの期間を使うと全印刷半単位5e-5内、著者geometryの保存セルとの差1.72e-11以内、独立3moment+jmax版でも2.3e-11以内になる。
2. 以前の `sigma_R=sigma*B(dt)/dt` 提案は、この印刷表の生成規約ではない。期間rate Rにinstantaneous rと同じSDEを仮定する本文の有限刻み近似を保持する。**instantaneous Gaussian OUの別離散化と混ぜない。** DG400の近接knot除去も別scheme。
3. **Figure32.9 全75表示値も原入力から再現した。** DG201全10年BK木・conditionalZCB rollback・localzero補間・quotedstrike/accrualで4step `0.671933260258`、100step `0.702581409362`。全75 fieldsが個別印刷半単位内。印刷bond入力のみの条件付きrollback/丸め幅も別fixtureとして保持し、全BK原入力再現との違いを示す。
4. §32.6は時間依存a/sigma、smoothness penalty、対象Bermudanに近いEuropean basketまで本文要求に含む。合成較正は準備済みだが、市場quoteを本文から回収したとは主張しない。
5. 現在の `hull_white.py` のzero-mean Q OU座標の `-B*c` はM29で修正済み。既存P3設計の「欠落」は現在の欠陥として再掲しない。Ho–Lee a=0は公開APIが現在rejectするためprivate候補に保つ。

## 2. 根拠と版

### 2.1 読んだプロジェクト資料

- `/home/kazumasa/projects/johnhull/docs/prep/sections/ch32.md`: 2026-09-27 draft、21要求、7節。過去の未再計算ラベルは今回のscratchで上書き可能な項目を個別に示す。
- `/home/kazumasa/projects/johnhull/docs/prep/design/P3_TREE_LMM_IMPLEMENTATION_2026-10-04.md`: finite-R、event grid、BK、Bermudan、time-vol較正の契約。
- `docs/prep/sources/sources_S001-S031.md`, `sources_S032-S062_L01-L03.md`: research-source catalog。新たなCh32市場quote datasetは見つからない。
- `hullkit/src/hullkit/hull_white.py`, `rates.py`: 現行公開helperの定義とdomainを直接読む。製品コードは計算scratchからimportしない。

### 2.2 原典

- licensed original `/home/kazumasa/projects/johnhull/options, futures and other derivatives 11th.pdf`。
- SHA256 `8bc6e2f04fad95e4eeb40d0526219ba5f9228ee3d2ea3eaaf80870bdf7ccb482`。
- 本文抽出 `/tmp/p3-ch32/ch32-original.txt`、Fig32.9のページ画像 `/tmp/p3-ch32/fig329.png`。頁番号を本文と突き合わせ、図のbranch/early exerciseを画像で確認した。抽出・画像をrepoへ配布する成果物にはしない。

### 2.3 著者一次資料アーカイブ

[Rotman FinHub / Hull archive](https://github.com/rotmanfinhub/john-hull-textbook-resources)、固定full commit **`9b8dbfe37661dbd3de65d3a1489dc1297e840de7`**。
今回の追加回収は `/tmp/p3-ch32/source-downloads.json` にfull URL、Git blob、blob検証、内容magic、bytes、SHA256を保存。実PDFは `%PDF`、pptxはZIPであることを確認し、HTMLエラーをPDFと数えない。

| 一次資料 | ローカル | SHA256 |
|---|---|---|
| TechnicalNote15、2頁 | /tmp/p3-ch32/TechnicalNote15.pdf | 83a848667055c71a8f060e1c46d559c422b1799e87cf3a3e3be20021d46cfa88 |
| TechnicalNote31、5頁 | /tmp/p3-ch32/TechnicalNote31.pdf | 43f5c0b6e1a48339214a3f7357e506176b5366ba1140883e0856218508a1b58a |
| Ch32著者slides | /tmp/p3-ch32/Ch32HullOFOD11thEdition.pptx | 0376c9a1c346502600896f14163a601c227c5c67cd0c744580438af62dcff200 |
| Ch32 GE solutions | /tmp/p3-ch32/HullOFOD11eSolutionsCh32.pdf | d35627ae367b5257b8bd721abb8680c1b5cbe831f5fa9265205daae43574fa74 |
| TechnicalNote16 | /tmp/p3-ch32-TN16.pdf | f3dcb0a5d26d7ab43b69d797b5fea81f28355ccbd20f5fe1535cd2f1ee3607b7 |
| TechnicalNote9 | /tmp/p3-ch32-TN9.pdf | 9f9bdf6783248a280cab862236b0cadd06e04676435df362c25e8577e83843bb |
| DG201 functions.xls | /tmp/p3-ch32-DG201-functions.xls | 273ebb1a0814724e962bd4e10bd643c73742f121b7703f813638204e3dee4493 |
| DG201 applications.xls | /tmp/p3-ch32-DG201-applications.xls | cb761768d4654a913c1d140f46107680b99be5ff0d3076d678c835585da8562d |
| DG400 functions.xls | /tmp/p3-ch32-DG400-functions.xls | 00dfde65a46dbae950f7cdcfb99dad66a522062e13e3df1da7ba3d3bb4ccc930 |

- [TechnicalNote15 at fixed commit](https://github.com/rotmanfinhub/john-hull-textbook-resources/blob/9b8dbfe37661dbd3de65d3a1489dc1297e840de7/Options%2C%20Futures%2C%20and%20Other%20Derivatives%2C%2011th%20Edition/Technical%20Notes/TechnicalNote15.pdf)
- [TechnicalNote31 at fixed commit](https://github.com/rotmanfinhub/john-hull-textbook-resources/blob/9b8dbfe37661dbd3de65d3a1489dc1297e840de7/Options%2C%20Futures%2C%20and%20Other%20Derivatives%2C%2011th%20Edition/Technical%20Notes/TechnicalNote31.pdf)

DG201 / DG400 / TN9 / TN16 の固定URL、保存セル、VBA抽出位置、版の差は `/tmp/p3-ch32-table323-notes.md`。TN14の全Appendixと二因子準備は `/tmp/p3-two-factor-design.md`、入力資料metadataは `/tmp/p3-input-recovery.md`。

## 3. 全21要件の実装境界

| draft ID | 原典頁・内容 | 現行helper / gap | 必要な受入証拠 |
|---|---|---|---|
| D32.1-01 | 733、Ho–Lee式32.1–3 | a=0 private必要、公開paramsはa>0 | arbitrary curve fit、Gaussian bond、theta、a→0 |
| D32.1-02 | 734–735、HW式32.4–8 | `hw_b/phi/discount_bond/exact_transition/simulate_hw_paths` | Q座標とshift、同一curve、Ho–Lee極限、独立kernel/求積 |
| D32.1-03 | 735–736、BDT/BK/HW2F | 旧notebookのみ、HW2F private設計済み | BDT a=-sigma'/sigma、BK独立a/sigma、positivity、2F特徴 |
| D32.2-01 | 736–737、式32.10、HW ZCB option | `hw_zcb_option` は単位face | cash face/strike変換、put-call parity、sigma0、E0 |
| D32.2-02 | 737、Ho–Lee option | a=0 public未対応 | sigmaP=sigma*(s-E)*sqrt(E)、HW極限 |
| D32.2-03 | 737、coupon/Jamshidian、CIRχ² | public swaption専用、一般coupon/CIRなし | critical r/state、positive CF、Gaussian payoff、cap/floor bond put |
| D32.3-01 | 737–738、3か月forwardの3形状 | 旧HJM関連、2F publicなし | 同じtenor/absolute vol、flat/decline/hump、未印刷params明記 |
| D32.3-02 | 738、mean reversion/交差項 | private2F準備 | one-factor limit、rho cross term、小時間bond-ratio検算 |
| D32.4-01 | 738–739、Fig32.4 | 金利rollbackなし | node discount、原rates/payoff、9経路列挙 |
| D32.4-02 | 739–740、Fig32.5 | stock CRRは流用不可 | 3branchの後継indices、mean/variance、sum1 |
| D32.5-01 | 740–742、spacing/jmax/Fig32.6 | treeなし | strict jmax、非負確率、端のmoment、sigma0/a0 |
| D32.5-02 | 743–746、alpha/Q式32.11–14 | curve DFのみ | 全event時点curve fit、Q state price、parent discount、Fig32.7/8 |
| D32.5-03 | 746–747、負rate/shiftedBK/multicurve | projection/discount区別必要 | log domain、feasible curve、OIS vs payoff curve、shift下限 |
| D32.5-04 | 748、finite R式32.15–17 | publicbondはinstantaneous-Q-state | R→bond、P(t,t+dt)=exp(-Rdt)、短いterminal dt保持 |
| D32.5-05 | 748–750、Ex32.1/Fig32.9 | 表/全BK原図のsource numerical blocker解決、製品未実装 | 全6N/analytic、quotedstrike+accrual、4step全node/100step、inner tree |
| D32.6-01 | 749–750、SSE/LM/paramcount | `calibrate_hw1f`定数のみ | multi-start、repricing、status、rank、quote>=params |
| D32.6-02 | 750–751、time a/sigma/penalties | publictime-volなし | step knots/event grid、first/second difference別、fit/smoothness tradeoff |
| D32.6-03 | 751、5x5...9x1 basket/Bermudan | exercise engineなし | 5..9 exercise→10 maturity、cashflow/reset order、singleexerciseEU |
| D32.6-04 | 751、fixed-a impliedsigma | helper再価格部品のみ | Black vol→Black price→HW sigma、units/monotonic root |
| D32.7-01 | 751–752、outside-model hedge | 専用bucket APIなし | pricing factorとshock数の区別、複数curve shock |
| D32.7-02 | 751、§29.4接続 | discount/reprice部品 | curve vs vol shock別、delta/gamma/vega、qual受入と数値実装の区別 |

最後のD32.7はD3説明受入候補だが、EX-08の数値bucket実装完了とは同じ主張にしない。§32.1–.3でBK/HW2Fの説明だけに狭めて本文モデル要件を落とさず、用途と対象範囲を明記する。

## 4. 本文の数値入力・印刷pinの完全な棚卸し

### 4.1 数値pinのない箇所

- §32.1導入の「bond1%の誤差→option25%」は入力なしのillustration。再現価格pinにしない。
- Fig32.1/32.2はモデル方向の図、Fig32.3は3か月tenorを指定するが軸数値/paramsなし。
- §32.2本文に価格例はない。TN15は別一次資料の例。
- §32.6のmarket prices Uiは数値datasetなし。5x5、6x4、7x3、8x2、9x1 は原典の契約tenorでありmarket priceではない。
- §32.7は定性命題。合成PV01は追加教材として区別する。

### 4.2 Fig32.4 pp738–739

- dt=1年、全node pu/pm/pd=.25/.50/.25。
- rates%: t0 `[10]`; t1 `[12,10,8]`; t2 `[14,12,10,8,6]`。
- t2 payoff `100*(R-.11)+`: `[3,1,0,0,0]`。
- 独立rollback: B=`1.108650545896`、C=`.226209354509`、D=0、A=`.353128468498`。印刷1.11/.23/.35と整合。
- 9経路列挙PVとの差は機械精度。印刷B/Cを先に2桁へ丸めてrollbackする手順は採用しない。

### 4.3 Table32.1 と Fig32.6/32.7 pp741–744

入力: maturities `[.5,1,1.5,2,2.5,3]` 年、continuous zero% `[3.430,3.824,4.183,4.512,4.812,5.086]`。
HW a=.1/year、sigma=.01 rate/sqrt(year)、dt=1、jmax=2、spacing=.01sqrt3。

- Fig32.6 Rstar%: t0 0; t1 `[1.732,0,-1.732]`; t2 `[3.464,1.732,0,-1.732,-3.464]`。
- j=0 p `[.1667,.6666,.1667]`; j=1 `[.1217,.6566,.2217]`; inward j=2 `[.8867,.0266,.0867]`。負jは鏡像。印刷 .6666 等は通常の四捨五入でないため、原分散の3moment解を基準に計算する。
- Fig32.7 A..I R%: `[3.824,6.937,5.205,3.473,9.716,7.984,6.252,4.520,2.788]`。
- 独立alpha `[.038240000000,.05204999999999,.06252049999699]`。
- Q1 upper→lower `[.16041365,.64165461,.16041365]`、Q2 `[.01820898,.19979709,.47359377,.20326122,.01885081]`。印刷8 Q値を復元、Q合計のcurve残差2.22e-16。
- 2年DF `.9137` = exp(-.04512*2)。Qを確率としてnormalizeしてrollbackしない。

### 4.4 Fig32.8 pp746–747

BK a=.22/year、sigma_log=.25/sqrt(year)、dt=.5。Table32.1同一curve、jmax=2、log spacing=.25sqrt1.5。

- A..I shifted x `[−3.373,−2.875,−3.181,−3.487,−2.430,−2.736,−3.042,−3.349,−3.655]`。
- R% `[3.430,5.642,4.154,3.058,8.803,6.481,4.772,3.513,2.587]`。
- alpha `[−3.372609924810,−3.181099331517,−3.042432028095]`。
- j=0 p `[.1667,.6666,.1667]`; j=1 `[.1177,.6546,.2277]`; inward j=2 `[.8609,.0582,.0809]`、負j鏡像。
- shifted x9/rate9を原表示桁で再現、Q合計のcurve残差1.11e-16。

### 4.5 Ex32.1 / Table32.2–3 pp748–749

Actual/365、continuous zero rateを **線形補間**。datesはyear fractionsへ変換後に使う。

| days | zero% | days | zero% | days | zero% |
|---:|---:|---:|---:|---:|---:|
|3|5.01772|367|5.09389|2194|7.08807|
|31|4.98284|731|5.79733|2558|7.27527|
|62|4.97234|1096|6.30595|2922|7.30852|
|94|4.96157|1461|6.73464|3287|7.39790|
|185|4.99058|1826|6.94816|3653|7.49015|

Contract: **expiry=3年=1095日、bond maturity=9年=3285日、face100、put、K63、a=.1、sigma=.01**。curve knot1096/3287を契約日と取り違えない。

| N | 印刷 | 独立3moment+jmax木、delta_star=1/365 |
|---:|---:|---:|
|10|1.8468|1.846840135541|
|30|1.8172|1.817227104825|
|50|1.8057|1.805681323300|
|100|1.8128|1.812768730069|
|200|1.8090|1.808974826171|
|500|1.8091|1.809081553064|

解析price `1.8092941675909984`、独立forward-measure求積 `1.8092941675909997`。印刷1.8093。
DG201保存解析 `1.8092918769951747` は著者CDF多項式近似で再現され、差2.29e-6の説明がつく。

DG201 worksheet `Trinomial Convergence`: curve A6:B20、expiry E6=3、bond E7=9、coupon E8=0、face E9=100、put E12=0、sigma E15=.01、a E16=.1、K E17=63、cashstrike E18=0。tree saved E29/E49/E69/E95/E96/E99。詳しい値・URL・VBA位置は table323-notes。

### 4.6 American Fig32.9 pp749–750

**call**, BK a=.05、sigma_log=.20、flat **continuous5%**、face100、maturity10年、annual coupon5% **semiannual** (cash2.5 every .5y)、quoted K105、expiry1.5、4 option steps dt=.375。
Printed root `.671933`→本文 `.672`。100 steps `.703`。今回DG201独立全BK木から4step `.671933260257658` /100step `.702581409362057` を再現。
Time/accrual cash: `(0,0),(.375,1.875),(.75,1.25),(1.125,.625),(1.5,0)`。

全nodeを上から下へ:

| t | cash bond | option | R% |
|---|---|---|---|
|0|99.51021|.671933|5.0000|
|.375|94.69 /101.4979 /107.6802|.058227 /.471654 /2.16306|6.1362 /4.9633 /4.0146|
|.75|87.0692 /94.32588 /100.9787 /107.0004 /112.3922|0 /.017063 /.273599 /1.771632 /6.142178|7.5348 /6.0946 /4.9297 /3.9874 /3.2253|
|1.125|79.19393 /86.85737 /93.96242 /100.4532 /106.3087 /111.5353 /116.1587|0 /0 /0 /.09907 /1.275943 /5.910323 /10.53372|9.2572 /7.4877 /6.0565 /4.8989 /3.9625 /3.2051 /2.5925|
|1.5|71.13165 /79.13643 /86.65577 /93.60053 /99.92196 /105.6054 /110.6623 /115.1222 /119.0263|0 /0 /0 /0 /0 /.605443 /5.662307 /10.12224 /14.02632|11.3744 /9.2003 /7.4417 /6.0193 /4.8687 /3.9381 /3.1854 /2.5765 /2.0840|

図右のbranch%は j=3/2/1/0に順に
`[14.0124,66.3503,19.6374]`, `[14.8620,66.5260,18.6120]`, `[15.7467,66.6315,17.6217]`, `[16.6667,66.6667,16.6667]`。negative jは鏡像。枝位置をp750画像で確認済み。

- cashstrike=105+accrual、cleanbond=cashbond−accrual。独立rollback interval25nodesに原option表示を含む（printed-input intervalsに加え表示丸め1e-6の境界）。
- accrualを落とす誤実装はroot `.783452019053`。本文値との差は丸めでは説明できない。
- earlier exercise: t.75 j=−2、t1.125 j=−2/−3（図shadedに一致）。terminal j<0はterminal exerciseであり「早期」と呼ばない。
- root cashbondはcurveの確定CFから `99.510212622775`。このrootだけでconditional BK node bondを受入しない。
- Option coarsegrid .375にcoupon .5/1が乗らない。couponをnearest nodeへ丸める実装は不可。
- DG201 `HW_TreeBondOption:4694` が全coupon datesをTermStructへ加え、`MakeHW_Tree`→`BuildRates:6991`が全10年のdiscount bondsをrollback。`DataSetUp:6647` dt1=.125、`Int(gap/dt1)+1`分割がcoupon gap .5を.1にする。t1.5のterminalRを.1期間でfitすると9 rate表示が一致する。この規約を含む全treeの独立計算で、cash bond25/option25/rate25の全75表示を再現した。詳細は `/tmp/p3-ch32-figure329-notes.md`。

### 4.7 Fig32.9 の回収した legacy algorithm と production境界

- DG201 `DataSetUp` はoptiongridをexpiryまで優先する。expiry前の **rate-calculation knots** .5/1をnearest option time .375/1.125へ移す。**coupon cashflow dates自体は .5/1のまま**。
- expiry後は全semiannual coupon datesをrate datesに保持し、gap .5を `floor(.5/.125)+1=5` intervalに分けてinnerdt=.1。4stepsならtotal89、100stepsならtotal185。
- incoming spacing `sigma_log*sqrt(3*previousdt)` とoutgoingdtを別にし、nextgrid nearest centerへのEuler mean/varianceをmatchする。負確率となるboundary candidateを採用せずpositive geometryを選ぶ。最終採用枝は全intervalで非負、deterministic fallbackは実行されない。
- alpha/QでflatDFへfit。`BuildRates` がrate maturityごとのunit ZCBをrollback、各optionnodeで **local continuous zero curveへ変換**。
- `TreeBondOption` はnexttimeのone-periodRをlocalcurveへ加え、actual coupon datesのzero rateを線形補間してcashbondを評価する。これがearlycouponをoptionnodeへ丸めるpayoff実装と異なる。
- 原入力からfull cashbond/option/periodRを出し、印刷値は比較にだけ使う。75 fieldsは各々の文字列桁からhalfunitを算出し、表示0はexact0で検証。
- maxcurve残差1.11e-16、maxmeanmoment残差8.89e-16、maxvariance残差2.09e-17。invalid boundary候補は4step33回/100step100回rejectしたが、最終negativep/fallbackは0。
- この特定の旧software date/curve policyで印刷例を再現した。future event-complete production treeは全coupon/exercise datesをmergeする別gridを持てるが、その価格を同一legacy fixtureと混同せずrefinementを検証する。

## 5. 必須数式・座標・単位

### 5.1 Constant Gaussianモデル

Time=year、rates=annual continuous decimal、a=1/year、sigma=rate/sqrt(year)、theta=rate/year。
`F(0,t)=-d log P0(t)/dt`。Brownianの符号は一因子なら全体反転可だが、二因子rhoとの符号関係を保持する。

- Ho–Lee: dr=theta dt+sigma dW、theta=F_t+sigma²t、B=T−t、lnA=ln(P0T/P0t)+B F−.5sigma²tB²。
- HW: dr=(theta−a r)dt+sigma dW、theta=F_t+aF+sigma²(1−e^(−2at))/(2a)。
- B=(1−e^(−a(T−t)))/a、q(t)=sigma²(1−e^(−2at))/(2a)、c(t)=.5sigma² B(0,t)²。
- Q zero-mean state x: r=x+F+c、P(t,T|x)=P0T/P0t * exp[−B(x+c)−.5qB²]。
- Actual-r form: lnA=lnratio+B F−.5qB²、P=A exp(−B r)。state xとrを混同しない。
- ZCB option std: sigmaP=B(E,s)*sqrt(q(E))、faceL・cashKは `L*hw_zcb_option(...,strike=K/L)` 相当。
- Call C=L P0s N(h)−K P0E N(h−sigmaP)、put parity、h=ln(LP0s/KP0E)/sigmaP+.5sigmaP。sigma0/E0/K0はdeterministic limit。

**曲線の線形zero補間**はinstantaneous Fをknotで不連続にしうる。theta図の普通微分を無根拠に滑らかと扱わない。bookの原price例はDF/period Rでfitし、derivative-dependent shiftを描く教材ではone-sided/weak derivativeや別smooth interpolationを明示する。smooth curveへ変更した価格を同じ印刷fixtureとしない。

### 5.2 finite-period R

bd=B(t,t+delta)、bT=B(t,T)、q=q(t)。

- R=−lnP(t,t+delta)/delta。
- Btilde=delta*bT/bd。
- lnAtilde=ln(P0T/P0t)−(bT/bd)*ln(P0(t+delta)/P0t)−.5q*bT*(bT−bd)。
- P(t,T)=exp(lnAtilde−Btilde*R)。T=t+deltaなら exp(−Rdelta)へ厳密に戻る。
- Table32.3の**最終deltaはexpiryまでのgrid spacingとは異なる**。terminalRの同定に必要な最初のpost-expiry knotを落とさない。
- scratch t2/delta.25/T7/r.052で直接価格 `.779975841966672`、R変換誤差1.11e-16。Rをrへ代入すると誤差 `.000394954541403`。

### 5.3 Time-dependent a/sigmaのprivate候補

G(s,t)=exp(−integral_s^t a)、B(t,T)=integral_t^T G(t,u)du。
q(t)=integral_0^t sigma(s)²G(s,t)² ds。
c(t)=integral_0^t sigma(s)²G(s,t)B(s,t) ds。
phi=F+c、theta=phi'+a phi=F'+aF+q。`q'=sigma²−2aq`, `c'=q−ac`。
同じP(t,T|x)式にq,c,Bを代入できる。ZCB option variance=q(E)*B(E,s)²。
Time knotsで区間を分割し積分。piecewise a/sigmaのexact Gaussian momentsと本文 Euler moment版を別modeにし、正確さの主張を混ぜない。TN16はTN9の一般moment geometryへ委譲するがexact-OUを指定したとは読まない。

## 6. 木・event・cashflowの設計

### 6.1 Branchとstate prices

- 本文constant-step: h=sigma*sqrt(3dt)、jmax=floor(.184/(a dt))+1（strict >）。a=0は無限幅を使わず有限horizonの到達nodeのみ。
- normalized mean d=−a*j*dt、variance=1/3。
- interior offsets `[1,0,−1]`、upper `[0,−1,−2]`、lower `[2,1,0]`。
- 3x3 system: sum p=1、sum p*offset=d、sum p*offset²=1/3+d²。expectedにproductionのprobability formulaをコピーしない。
- sigma0は単一deterministic state。hで割る一般処理へ通さない。
- coarse a*dt=2.1などはnegative probabilityを生成する。silent clipでprocessを変更せずgridをreject/refine。
- HW alpha=(ln(sum Q exp(−x dt))−lnP0next)/dt。
- BK R=exp(alpha+x)、sum Q exp(−Rdt)=P0nextをmonotonic scalar rootで解く。
- Qchild+=Qparent*p*exp(−Rparent dt)。QはArrow–Debreu state priceで、sum Q=P0(current)が全層で成立する。
- BK feasibility: 0<P0next<sum Q。plain BKはnegative-forward curveへfit不能。shiftedBK R=exp(alpha+x)−shiftなら上限 exp(shift dt)*sumQ。
- scratch negativecurve−.5%、shift1%はshiftedR−.5%でfit可能。普通BKへlog負値やfloor clipを足してfitさせない。

### 6.2 任意event grid

coupon/payment/fixing/exercise、curve interpolation knots、a/sigma knotsをmerge、calendar/daycount/duplicate policyを保持。option horizon後もunderlying conditional pricesが必要なdateまでmodelを延長する。

Nonuniform tree: incoming spacingとoutgoing dtを区別。meanを次gridへ投影したnearest center k、その前後3nodesでfirst/second momentsを解く。state geometry、rate period、curve-fit intervalを別fieldにする。
本文constant Euler tree / DG201 exact legacy fixture / Gaussian OU discretization / BK PDE oracle は別名・別収束主張とする。
著者旧VBAには極端なbranchにdeterministic fallbackがあるが、productionへ無条件移植しない。今回表の3moment+jmax版も同じ印刷価格を再現するのでlegacy fallbackが受入の必要条件ではない。

### 6.3 Cashflowと行使

- coupon paid at event→ex-coupon underlying→exercise を明示（別orderなら契約を別定義）。expiry dateのcouponをdoublecountしない。
- accrued=次couponcash×(t−lastcoupon)/(nextcoupon−lastcoupon) を指定daycountで計算。coupon dateの0/全利息はpayment/exercise orderに従う。
- quotedKの場合cashK=quotedK+accrual、intrinsic=max(cashbond−cashK,0)。cashK入力ならaccrualを足さない。
- American/Bermudan continuation=exp(−nodeR*dt)*sum p nextV、exercise datesでmax。
- single exerciseはEuropean、exercise set追加で非減少、never-exercise0、sigma0 deterministic。
- swap exerciseがreset/start Eならsingle-curve floatingPV=N[1−P(E,Tend)]。future start SならN[P(E,S)−P(E,Tend)]。projection curveが異なる場合この等価性をそのまま使わない。
- OIS discounts / projection generates payoff。deterministic forward spread方式とtwo-rate stochastic treeを区別して本編のmultiple-curves説明を残す。

## 7. Coupon optionsと別原典 TN15

一般coupon positive CFを選び、rstar (またはQ-state root)でcoupon price=K。Ki=P(E,si|root)、各CF*unitZCB optionへ分解。同時に **expiry-forward Gaussian payoff integral** を独立oracleに使う。signed CFならmonotonicity/一意rootを失うため一般求積/PDEが必要。

TN15の別例: Vasicek a=b=.1、sigma=.02、r0=.1、expiry3、bond5、face100、半年cashcoupon5、put K98。remaining dates3.5/4/4.5/5、CF5/5/5/105。

- rstar `.109522207329889`、component cashstrikes `[4.734148621642,4.483653493347,4.247691273875,84.534506611135]`、sum98。
- component prices `[.012448926860,.022829835138,.031429371077,.808417503292]`。
- full-precision Jamshidian `.875125636367292`、Gaussian `.875125636367295`、difference2.33e-15。
- TN15 printed total `.8752` is printed components `.0125+.0228+.0314+.8085` の和。全精度入力の通常roundingは `.8751`。第1/第4componentも半unitをわずかに超える。**公式全精度pin一致と書かず、表示値と全精度結果を並記する。中間丸め/記述誤差のどちらかはこの一次資料だけでは断定しない。** 複数表示値をtargetに逆較正しない。

CIR optionは本文でχ²式に言及するがCh32のnumerical pinなし。一般coupon decompositionの条件を保ち、CIR exact/ncx2 oracleは別model workとして残す。two-factorで同一criticalrによる全coupon分解が成立するとは主張しない。

## 8. 較正の入力と独立scratch

### 8.1 Canonical algorithm / input contract

- curve: times + continuous zero decimal + interpolation/daycount。
- quotes: instrument type/direction/expiry/start/payment accruals/final date/notional/fixed strike、**priceまたはBlack/Bachelier quote format**、price scale/weights。
- unknown: constanta/sigmaまたはpiecewise a/sigma、knots、bounds、initial guesses。
- 本文objective=sum(Ui−Vi)² + sum w1,i*(sigma_i−sigma_(i−1))² + sum w2,i*(sigma_(i−1)+sigma_(i+1)−2sigma_i)²。
- LM residualにはsqrt(weight)*differenceを追加。parameterization/unitsを明示し、unnormalized book SSEとの違いはscaleを説明する。
- #params<=#quotesは必要だが十分でない。unpenalized quote JacobianのSVD/conditioning、multi-start、optimizerstatus、held-out repricing、bounds hittingを記録。
- penalty objectiveのJacobian full rankを「市場が全parameterを識別した」と言い換えない。prior penaltyがrankを補える。
- basket5x5/6x4/7x3/8x2/9x1はexpiry5..9/final10。expiry+nSwapYearsのindexを取り違えない。
- fixed-a impliedsigma: priceのmonotonic scalar root。Black20%はHW absolute sigma20%ではない。

### 8.2 今回の合成較正

original canonical basketのtenorを保持、synthetic curve continuous4%、face1、annual par fixedcoupon exp(.04)−1、fixed a=.1、sigma knots0/5/7/9、truth `[.009,.012,.015]`。

- prices E5..9: `[.0191609663982,.0180740788785,.0152309396679,.0119609151858,.00672684742672]`。Jamshidianと独立Gaussian積分を両方保存。
- penalty0、2 startsからtruth回復、max price error1.16e-16、sigma error2e-16程度。
- common normalized first/second penalty weight=.001でmax price error1.92e-5、first diff norm .00418924; weight=.1でmax error.000775679、first diff norm .00246576。truthはlinearなのでsecond differenceが0であり、penalty増で両roughnessが一律改善するとの主張はしない。
- held-out: expiry7/3年/coupon5%をfitに使わず再価格。CSV market入力を回収した例ではない。
- 5年annualcaplet、Black vol20%のprice `.0056801806154`→fixeda.1 HW sigma `.01027934096865`、再価格差4e-17程度。

今回はa fixed/time sigmaだけのscratch。time-dependent aも本文の対応範囲として残す。最後のsigma interval以後のtail policy、nonstationary forward vol、Jacobian at allboundsはfuture private implementationで必要。

### 8.3 Bermudan合成teacher

annual finite-period Euler tree、a=.1/sigma=.01、curve4%、annual coupon=exp(.04)−1、exercise5..9、final10、receiver notional1。

- singleexercise5/6/7/8/9: `.022044952225/.019145373563/.015375667004/.010878819867/.005738411892`。
- exercise[5,9]: `.023939650173`、all5..9: `.027468360245`。
- 独立経路列挙とrollbackはmax1e-16内、全curve DFをnode別discountから復元。
- これは同じdiscrete treeの停止・discount・event semanticsの検証。連続HW/BKのBermudan価格収束を証明した例ではない。future minimumは別spacing/time refinementと独立PDE/conditional MC oracle。

## 9. 公開helperの再利用とprivate候補

| 現行helper | 使用可能な範囲 | 追加/注意 |
|---|---|---|
| rates.zero_interp/discount_factor/forward_discount | 原curve/discount | finite rates、positive DF、zero linear/flat tail仕様 |
| rates.instantaneous_forward | curve derivative関連 | knot sidedness、thetaに追加微分が必要 |
| HullWhiteParams/hw_b/hw_phi/hw_discount_bond | constant a>0、sigma>=0、Q OU | M29 coordinate修正採用、a=0/time-dependent無し |
| hw_exact_transition/simulate_hw_paths | constant exact OU | discount integral pathはstateだけから省略不可 |
| hw_zcb_option | constantGaussian欧州face1 | cashL/Kscale、HoLee極限/σ0 |
| HullWhiteSwaption/hw_jamshidian_swaption | positiveCF swaption strike1 | generalcouponK、CIR、multicurve、early exercise無し |
| calibrate_hw1f | constant2params / syntheticEU | timevol、penalty、basket、SVD/heldout無し |
| trees.crr_price / vol06 trinomial | equity/fixeddiscount | 金利のnode discount/Q calibration代替でない |
| 旧ir_models HoLee/HW/BDT/BK | 既存説明/試作 | MC bootstrapと本文Q木は別、BK clipping EX-17維持 |

将来privateモジュール候補: `_short_rate_tree`（branch/geometry/Q/rollback）、`_hw_time_dependent`（kernels）、`_rate_exercise`（bond/swap/event）、`_rate_calibration`（residual/penalty/diagnostics）。現時点でpublicAPI追加を決めない。旧notebookの公開化やdependency追加は別承認対象。

## 10. 未完・受入順・完了条件

1. §32.1–.3のモデル/analytics/2F hump。TN14 private kernel資料を採用し、HoLee limitをpreserve。
2. §32.4共通branch/rollback → §32.5 alpha/Q/HW/BKとfiniteR。Table32.3 source blockerは解消済み、実装/製品検証は未着手。
3. Figure32.9全conditional bond25nodes/option25nodes/rates25nodes/4step/100step、full10y inner date gridのsource fixtureは今回完了。legacy version固定とproduction refinement oracleの境界を残し、製品で再現・検証する。
4. §32.6 time a/sigma + penalties + canonical basket + Bermudan、Black↔HW price。qual化してtimevol要求を外さない。
5. §32.7原典命題のD3説明 + §29.4のshock実装境界。1因子pricingでもmulti-bucket curve sensitivityを示す。

未完: source numerical blockerではなく製品tree/event/calibration実装、continuous BK/PDE refinement、time-a production、CIR generaloption、realmarket calibration inputは本文に数値datasetなし。TN15表示誤差はpin-policyを明記。二因子には前メモのp4 phi/F notationの導出上不一致を維持する。Ch33 flexicap strike/periodsと33.19未定義indexは別章の未解決条件のまま。

### 本章節要求とは別の著者演習資料

GE solutionsも回収したが21 draft本編範囲へ勝手に追加しない。numerical worked exercisesは32.3/4 (Vasicek ZCB call2.59/put.14)、32.5/6 coupon call.815189/put.4644、32.7 HWcall.439、32.8 HWcouponcall.944596、32.9 smalltree、32.10bond81.88、32.11bond91.37、32.12bond93.92、32.15 impliedsigma/American、32.16 strike95/100/105 normal/BK American、32.17 tree convergence。元問題inputsまで読んで数値再計算したとの主張はしない。32.16 BK105=.703は本編pinの追加一次資料として確認できる。

## 11. 出力と実行

- `/tmp/p3-ch32-fixtures.py`：hullkit importなし、independent math/3moment solve/Gaussian integrals/path enumeration。
- `/tmp/p3-ch32-fixtures.json`：原例、conditional print interval、合成cases、Table32.3再現結果を保存。
- `/tmp/p3-ch32-table323.py/json` と `...-notes.md`：著者旧VBA規約と保存セル別の詳細。
- `/tmp/p3-ch32-figure329.py/json` と `...-notes.md`：full10y BK conditional bondsと全75 fields比較、4/100steps。
- `/tmp/p3-ch32/source-downloads.json`：今回回収したTN15/31/slides/GE solutionの固定URL・hash。

実行: `/home/kazumasa/projects/.venv/bin/python /tmp/p3-ch32-fixtures.py`。
本turnの最終auditは `/tmp/p3-ch32-audit.json`（metricsとscratch全7file SHA256）。
main scratchは `/tmp/p3-ch32-table323.py/json`、`/tmp/p3-ch32-figure329.py` とDG201のrawxlsを参照する。このsource dependencyを本番fixtureへ無断に持ち込まず、rootが原典保存方針/ライセンス方針に沿って整理する。

今回実行は数値scratchだけ。旧スイートgreen、製品pytest、release/D1/browser acceptance、commit/pushを今回実行したとは主張しない。