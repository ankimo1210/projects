# 同一較正条件の動的モデル横断ヘッジ：設計調査

調査日：2026-10-09。作業先：`/home/kazumasa/worktrees/johnhull-research-roadmap`。
これは次の研究の設計案であり、承認済み仕様・実装済み機能・実証結果ではない。正式文書、金融ソース、ROADMAP、Gitは変更していない。主MC・学習は実行していない。

## 1. 結論

**RB-F04と同じ月次観測のarithmetic Asianを、Hestonとlocal volatilityの二つの市場で、時間を進めてヘッジする研究を勧める。** 初期vanilla価格の一致、条件付き価格・Greeksの精度、方策の適応性、自己資金会計を別々に検証してから、費用込みの終端P&Lを比較する。主2商品基準はRB-F07のIFTに接続した**市場クオートヘッジ**にする。内部variance/vol倍率の感応度を直接比較しない。

再利用の基盤は十分にある。ただし現在のRB-F04は月次13時点の価格比較、既存deep hedgeはstock-onlyの欧州callデモである。**ヘッジ時点の状態出力、条件付きAsian価格・Greeks、stockとcallの自己資金会計が主要な新規作業**になる。瞬間shockのP&Lや静的quote riskでこの作業を代替できない。

最初の対象をHeston/local・Asian・stock/固定長期call・比例費用に限定する。rough model、LOB、cross-impact、RL execution、多銘柄、実データ共同較正は次の研究へ回す。動的な経路依存claim・複数ヘッジ商品・モデルを変えた評価はこの研究に含める。

研究問いは次の三つ。

1. 同じ初期vanilla面に適合したモデルでも、Asianの動的Greeks・推奨保有量・P&Lはどれほど異なるか。
2. その差はSDE離散化、条件付き価格/Greek近似、方策、売買費用のどこから生じるか。
3. ある市場生成モデルで学習した方策は、別の生成モデルでもGreek/band基準よりリスクを減らすか。

NNの優越やmodel gapの検出は成功条件にしない。差が識別できない・未知・基準が優れる結果も、原始証拠と費用が揃えば研究成果として残す。

## 2. 一次資料と読んだ範囲

### 2.1 Deep Hedging

[Buehler et al., Deep Hedging, arXiv:1802.03042v1](https://arxiv.org/html/1802.03042v1) の§2、§3、§5.1–5.2を読んだ。取引商品ベクトル、適応的保有量、費用・制約、リスク目的関数を分離する根拠として使う。Hestonの数値例ではvariance-linked hedge instrumentも扱う。今回のstock/実際に値付けされたcall/Asianという契約構成は本研究の設計判断であり、その実験の複製ではない。

論文の一般的な終端費用と数値例の終端費用省略を混同しない。この研究では手仕舞いを明示する。HTMLの変換表示日ではなくarXiv版を出典識別子にする。

### 2.2 Drift removal

[Buehler et al., Deep Hedging: Learning to Remove the Drift, arXiv:2111.07844v3](https://arxiv.org/html/2111.07844v3) の導入、martingale/near-martingaleの説明、§3、§4の数値設定概要を読んだ。統計的driftの収益をヘッジ性能と混ぜる危険、費用がある場合のbid/ask内の条件付き期待値という論点に使う。

本研究は主評価を整合的なQ生成器で行い、drift removalの推定器やMEMMを実装したとは呼ばない。任意のspot+option simulatorでspot driftだけをrに置き換えても、optionのdiscounted gainsがmartingaleになる保証はない。この点は以下の取引価格の定義とmartingale診断で扱う。

### 2.3 ローカルprocessed資料とS038は別論文

実読したローカル資料：

`johnhull/references/processed/2025-francois-et-al-deep-hedging-iv-surface/paper.md`

表題・abstract、§2、§4.1–4.3、§5、Appendix Fを読んだ。実際の表題は **Deep Hedging with Options Using the Implied Volatility Surface**、59ページ、表紙2025-08-14である。[公式arXiv:2504.06208v3 PDF](https://arxiv.org/pdf/2504.06208v3) の表題・59ページ・表紙日付と一致する。ローカルblobとのbyte同一性は検査していない。stockと長めのcall、IV情報、straddleの費用込み比較を次の設計の参考にする。OCRの自己資金数式には記号崩れがあるため、その式を転記して会計を実装しない。

一方、台帳S038は以下の別論文である。

`johnhull/docs/prep/sources/sources_S032-S062_L01-L03.md` のS038、[公式arXiv:2407.21138v2](https://arxiv.org/html/2407.21138v2)：**Enhancing Deep Hedging of Options with Implied Volatility Surface Feedback Information**、50ページ。一次資料の表題、§1、§2.1–2.2、§3概要を確認した。stock-onlyの欧州callヘッジでIV feedbackの価値を検討する。S038とprocessedの論文を同一の出典、callとstraddleを同一の契約群として扱わない。

両論文のOptionMetrics/JIVR実データの再現は今回行わない。商用生データ、推定履歴、当日の実行可能quote/費用を取得していない。著者GitHubの存在は検索で確認したが、コードの実読・commit/license検証・再実行はしていない。

### 2.4 ここから先は本プロジェクト向けの提案

以下のパラメータ、契約、比較表、許容差、サンプル数、3図、費用台帳は、既存RB-F04と実装制約に基づく提案である。上記論文の性能値をこのプロジェクトの結果へ移していない。

## 3. 実コードの再利用と不足

以下のパスはすべて作業先worktreeを基準にしたもの。正式ソースの変更はしていない。

| 実読した資産 | 再利用できる部分 | 次の研究の不足/注意 |
|---|---|---|
| `johnhull/research/RB-F04/README.md`, `REVIEW.md` | 合成面、原始分母、固定seed、paired refinement、独立PDE/CF、unknownの記録方法 | 現在の実験はAsian価格。動的ヘッジ・barrier・他のパラメータ領域は範囲外 |
| `hullkit/src/hullkit/_model_dynamics.py` 全体 | 入力normal配列、Heston full-truncation log-Euler、local log-Euler、CRN、Brownian aggregation、failureの保持 | 出力は初期+月次12時点だけ。任意のヘッジ時点/claim観測時点、条件付きrestart、現金CFは未実装 |
| `hullkit/src/hullkit/_heston_local_surface.py` 全体 | stable Heston CF、Fourier price/density、variance-weighted density、local variance gridと支持状態 | `ck/ckk`は**strike**微分でありspot Delta/Gammaではない。gridはt0ではS0だけ支持、現F04はT≤1、条件付きAsian値付けはない |
| `hullkit/src/hullkit/hedging.py` 全体 | BSM delta hedgeの独立control、金利を含むcash/debtの考え方 | 欧州call・stock・q0・内部GBM RNG・費用なし。main会計には直接使えない |
| `deep_hedge_price/src/deep_hedge_price/policy.py` 全体 | shared MLP、previous holdingを含む状態、action範囲、checkpoint | 5特徴・1stock action。Asianのpast sum、観測call、2保有量、train-only scalerが必要 |
| 同`pnl.py` 全体と`tests/test_pnl.py` | discounted price gain、trade/fee、premiumを分けた結果 | q0/stock/欧州call専用、**満期liquidation費用を課さない規約**がテストで明示されている。この研究の会計へ黙って流用不可 |
| 同`risks.py` 全体 | MSE、安定log-sum-exp entropic、CVaR目的関数 | 主学習はMSE一つに固定し、ES95は評価指標。目的関数を3種に増やすと比較数/学習費用が膨らむ |
| 同`simulation.py` 全体 | exact GBM limit/control、generator/device管理 | Heston/local主生成器ではない。`auto` deviceを主実験で使わず固定deviceにする |
| 同`pricing_calibration.py` のmulti-start adapter | forward callable+TRF、複数start、残差/NFEV/optimalityの保存 | Heston物理パラメータ専用の較正器ではない。全start失敗を例外にしてしまう入口を主rosterへ直接流用しない |
| `_quote_risk.py` の`quote_sensitivity`/`calibrate`、RB-F07 | 較正残差のJacobian/随伴、再較正bump、内部座標と市場quoteの区別 | 既存実装はcurve cashflow向け。次のscalar call state fitにはIFTの式と検証方法を再利用し、curve APIへ無理にoptionを追加しない |
| `RB-F04/reference_methods.py` の`pde_call`と独立CF | calendar-time CN/Rannacher、独立call値、境界/格子検査 | 返り値はt0価格と最終grid。各ヘッジ時点のcall surface、Asianの条件付き価格/Greeksはない |
| `_quote_dml_hedging.py`, `_outside_model_hedging.py` の設計説明 | quote sensitivity/外部モデルの考え方 | 静的shock比較であり、自己資金・time advance・動的P&Lの代替にはならない |

RB-F04で確認済みの一例では、768-step Asianのlocal−Heston価格差は約0.00367、paired SE約0.00439で、凍結された検出基準では`difference_not_identified`だった。これは動的ヘッジ差がゼロという証明でも、次の研究で差を必ず検出できる根拠でもない。

## 4. 三つの層を分ける

| 層 | 主実験の候補 | 役割 |
|---|---|---|
| 市場生成器G | Heston-Q、local-Q | 実際のspot経路・取引callのmid・claim payoffを生成 |
| 価格/GreeksモデルM | Heston、local | 同じ時点/claim memoryから条件付きVとGreeksを出す |
| 方策Π | no hedge、model Greek、band、NN | 観測可能な現在/過去の情報から保有量を決める |

同じ初期面でも、将来の条件付き分布は異なる。**取引callの価格はGの整合的なQ条件付き価格に統一**し、Mの理論価格で約定したことにしない。Mのcallと実際のcallの価格gapも保存する。

cross比較はG×Mの4組合せ。NNは訓練Gと評価Gを別々に持つ。主NNに将来normal、将来payoff、Gの非観測latent variance、test由来の正規化を渡さない。

## 5. 初期vanilla fitと契約

### 5.1 共通の合成面

RB-F04と同じ基点を使う：

\[
S_0=100,\ r=.03,\ q=0,\ v_0=.04,\ \kappa=2,\ \theta=.04,\ \xi=.3,\ \rho=-.7.
\]

Hestonの独立CFを合成quoteの参照とする。以下を候補protocolへ固定し、pilot後に変更する場合はmainを見る前にrevisionを作る。

- fit quote：T∈{.25,.5,.75,1,1.25}、K∈{80,90,100,110,120}、25点。
- 独立holdout：T∈{1/3,2/3,1.125}、K∈{85,95,105,115}、12点。
- local variance構築：Heston marginalから構築し、独立calendar-time PDEで全37点を再価格。
- 価格単位はS0と同じ通貨。fit/holdoutの各点で絶対誤差≤1e-3を初期の数値目標とする。独立CFのorder/cutoff誤差は別に≤1e-8を目標とする。これは提案値であり、pilotで妥当性/費用を確認して凍結する。
- quoteごとのraw error、支持状態、domain/cutoff/grid refinementを保存する。RMSEだけでwingの失敗を隠さない。

この最小版は**既知Hestonパラメータからの合成common fit**である。市場データの較正成功、optimizerによるパラメータ回復、全連続価格面の一致とは呼ばない。有限37点の合格だけで全surfaceを証明しない。

optimizer較正の効果まで主張する場合は、追加でprivate Heston multistart TRFと全start失敗保持が必要。ただし初期面をそろえた動学比較という主問いには、パラメータ回復を必須にしなくてもよい。

### 5.2 売るclaimとヘッジ商品

- 主claim：月次arithmetic Asian call、T=1、K=100、quantity=1。
- payoff：`max((S(1/12)+...+S(12/12))/12 - K,0)`。S0を平均に含めない。
- 主memory：現在までに確定した観測spotのsum `A`とcount `n`。
- claim観測は月次12回のまま固定。内部SDE stepsやヘッジ回数を増やしても観測回数を変えない。
- ヘッジuniverse U1：stock+cash。
- U2：stock+cash+**固定K=100、T*=1.25の欧州call**。rolling ATMを採用しない。満期Tで残存.25のcallをmidで手仕舞いし、追加のcontract選択/roll費用を避ける。
- 欧州call K=100,T=1を会計/Greeksのcontrolとする。Asianを欧州callに置き換えて主研究が完了したとはしない。
- 主ヘッジgridは1/48。pilot候補は12/24/48で、どれを主gridにするか事前凍結。月次観測直後にAを更新してから新しい保有量を決める。最終観測→claim決済→両asset手仕舞いを明記する。

現surfaceがT≤1なので、T*=1.25への延長は必要。T=1までのcoefficientsを一定に延長して長期callを値付けする代用はしない。

## 6. 自己資金会計

時点iのex-dividend mid price vectorをP_i=(S_i,C_i)、区間(i−1,i]で支払われた一単位当たりの現金CFをD_i、cash口座をBとする。主実験q0でD_i=0だが、会計関数はCFを受け取る。

1. 初期cashは共通premium p0、初期holdingsは0。
2. 前の保有量h_{i−1}のまま金利とCFを受け取る：
   \[
   B_i^- = B_{i-1}^+e^{r\Delta t_i}+h_{i-1}\cdot D_i.
   \]
   CFが区間内の別日付なら、その支払日とcash利息を別eventとして扱う。
3. 観測可能状態からh_iを選び、Δh_i=h_i−h_{i−1}を取引：
   \[
   B_i^+=B_i^- -\Delta h_i\cdot P_i
          -\sum_a\lambda_a P_i^a|\Delta h_i^a|.
   \]
4. TではΔh_T=−h_{T−}を約定してliquidation費用を払い、cash-settled H_Tを一回だけ払う。
5. `discounted_pnl=e^{-rT}B_T`、positive lossは`-discounted_pnl`。premiumを除いたlossも別に保存する。

q0の場合の独立なdiscounted gain表式：

\[
\mathrm{P\&L}=p_0+\sum_{i=0}^{m-1}h_i\cdot
 (e^{-rt_{i+1}}P_{i+1}-e^{-rt_i}P_i)
 -\sum_{i=0}^{m}e^{-rt_i}\mathrm{cost}_i-e^{-rT}H_T.
\]

配当/クーポンがあればdiscounted CFの項を加える。ex-dividend priceと現金CFを二重に数えない。T*callはTで価格C_Tを回収するので、Tでcall payoffも受け取る扱いにしない。stockのphysical settlementとcash-settled claimを混ぜない。

**小さな独立会計例を実行した。** r=.05、t=(0,.5,1)、P=((100,6),(104,8),(102,5))、h=((.4,.5),(.6,.2))、λ=(.001,.005)、p0=7、H=3。初期/中間/終端feeは.055/.0328/.0662。cash再帰からB_T=2.330792066559754、discounted P&L=2.2171179961044647。別のdiscounted gain表式は2.217117996104470で、差は約5.3e-15。これは会計identityのtoy検証であり、ヘッジ性能の結果ではない。

主費用候補はstock5bp、call50bp。これはsynthetic half-spreadとして明示する。実市場の費用推定値ではない。cash借入と貸付のrは同一、funding/IM/capitalは扱わない。

## 7. 条件付き価格・Greeks：主要な新規作業

### 7.1 既存価格関数では足りない

各ヘッジ日でAsianのV(t,S,v,A,n)またはV(t,S,ℓ,A,n)が必要。主市場クオートヘッジの必須微分はVS|θとVθ、およびcallのCS|θとCθ。spot Gammaはraw Delta-Gamma対照/数値診断を追加する場合の微分であり、主IFT hedgeの必要条件とは分ける。RB-F04のt0価格差とFourier strike微分では、この関数を得られない。

取引callの条件付きprice/GreeksはHeston独立CFとlocalのcalendar-time PDE snapshotsで構築できる。local PDEは**元のcalendar time**のσ_loc(t,S)を使う。残存期間をt0から始め直して同じsurfaceを再利用してはいけない。

### 7.2 実装案を三つ比較する

| 案 | 利点 | 費用/制限 | 判断 |
|---|---|---|---|
| 全trade/stateごとのnested MC | 条件付きpriceの意味が明確、surrogateなし | path×date×policy×inner pathsで膨大。ノイズのあるGammaが売買量を壊す | 主評価器には使わず、独立selected-state oracle |
| Asian PDE/ADI | MCと異なる価格参照、localは(S,A)、Hestonは(S,v,A) | Heston3D solver/domain/観測日のjump条件が新規で大きい | localのselected-state参照は有力。Heston完全3D主エンジンは今回の前提にしない |
| 独立conditional labelsをcacheし、同じ滑らかな価格表面からC/Δ/Γを出す | 高価な生成を全方策で共用、MC/補間/Greek誤差を分離可能 | surrogate/grid近似の独立検証が必須 | **主評価器として推奨** |

主候補は「最後のBrownian incrementを解析的に積分した条件付きMC教師」+「決定的滑らかな補間」である。主IFT hedgeはC¹とVS/Vθを検証する。Gamma診断を行う場合はC²まで検証する。局所支持範囲と教師Nはpilotで選び、mainで表面を訓練し直さない。範囲外、Greek未解決、条件付き価格未収束をnearest clippingで直さない。

### 7.3 Hestonで使える次元削減

Hestonではfuture spotのSへのhomogeneityを利用できる。残り観測のnormalized sumをB、x=(12K−A)/Sとすると、固定vで

\[
V=e^{-r(T-t)}\frac{S}{12}E[(B-x)^+],
\quad V_S=e^{-r(T-t)}\frac{1}{12}E[B1_{B>x}],
\quad V_{SS}=e^{-r(T-t)}\frac{x^2}{12S}f_B(x).
\]

この式は本調査での導出案。単にhistogram densityをGammaとして採用しない。最後のstock incrementに条件付けると、B=b+c exp(μ+σZ)のlognormal tailとdensityを解析的に積分できる。bを超えないthresholdでは線形/確定領域を別扱いする。σ=0のatomで通常Gammaが存在しない場合は理由付きunknownにする。

一つの(t,v)のfuture simulationで多くのA/S thresholdを共用できる。各tでv-gridとthreshold-gridを作ることで、全tradeのnested MCを避ける。これをlocalにそのまま使わない：σ_locはspot水準に依存し、Hestonのhomogeneityは一般に成立しない。

### 7.4 Local教師

各(t,S)でfuture pathsをcacheし、Aの違いは同じfuture sumと最後のlognormal条件付き値で処理する。S±hのfuture pathsはCRNで生成し、複数hの中央差分とSEを記録する。素朴なpathwise二階微分や不連続payoffのautograd値を正しいGammaと決めつけない。

価格表面の候補はSciPyの既存spline系。価格と独立のNNでGreeksだけを作らず、同じprice表面の微分を使う。補間されたC/VS/Vℓを教師のraw値・bump参照と比較し、quote hedge ratioまで再較正bumpで検証する。Gamma対照を追加する場合はC²/Γも検証する。負Gammaやprice bound違反をclipで隠さず、数値未解決として保存する。

pilot候補：conditional N=1024/4096、Heston v-nodes7/13、local S-nodes9/17、thresholdノード65/129。48ヘッジ日を維持してraw教師の共用を行う。支持範囲はpilot+固定stressで設計し、main外挿はunknown。これらは**初期候補であって計算量/精度の保証ではない**。pilotで仕事量とselected-state誤差が成立しなければ、conditional evaluatorの修正へ戻る。主実験を欧州callだけに縮小しない。

### 7.5 独立oracleと精度gate

- Heston vanilla：別CF、bump Delta/Gamma、MC、deterministic-variance Black limit。
- Local vanilla：calendar-time PDEのgrid/domain/time refinement、独立bump。traded callのsnapshot全体を保存。
- Asian selected states：別seed、別実装の直接conditional MC、複数幅CRN価格bump、teacherとは別のSDE refinement。Hestonはfull-truncation Eulerと独立positivity-preserving/QE系の比較を候補にする。両方がMCなので、common discretization biasがゼロとは呼ばない。
- GBM limit：月次**geometric** Asianの解析価格/Greeksを別controlとして使う。主arithmetic Asianと取り違えない。arithmeticは独立quadrature/conditional MC controlを別に必要とする。
- local Asianには(S,A) backward PDE selected-state参照を追加候補にする。全面的Heston3D PDEは未実装であり、完成済み独立oracleとして計画に書かない。
- 代表statesをt、moneyness、past sum、vol、wing、最終観測前で事前指定する。oracle SEの6倍だけで全て合格にせず、finite-h/time-grid/interpolation errorも別に比較する。
- Greek誤差gateは価格誤差だけで決めない。独立Greekの相対/絶対誤差と、許容誤差が誘発する保有量・リスク幅で判断する。数値閾値はpilot前candidateに記載し、main後に緩めない。

## 8. 観測情報とcross-model state

### 8.1 初期面fitとrebalance一quote fitは別作業

主方策の共通情報は `(t,S,A,n,Q,previous stock/call holdings,spreads)`。QはGが値付けしたactual hedge-call mid。stock-only方策にもcall観測は使えるがcallの保有量を0へ固定する。future状態やactual latent vは主方策へ渡さない。

time0の25quote/12holdout fitは§5の固定モデルを作る作業。各rebalanceでは、そのモデルの**一つのscalar state**を同じQへ合わせる。

| M | scalar state θ | 今回固定するforecastの意味 |
|---|---|---|
| Heston | 現在variance v | κ/長期mean variance/ξ/ρは初期fitのまま、現在vからHeston dynamicsを進める |
| local | 正のfuture local-variance倍率 ℓ | 現時点t以降の条件付き価格用のfieldを `ℓ σ_base²(u,s)` とする。現在ℓを条件付きforecast内で固定し、次の実際のrebalanceで再fitする |

local multiplierはquoteをfitする限定的なstate/forecast規約であり、新たな確率的vol因子のSDEを実装したとは呼ばない。市場生成Gのlocal fieldは元のbase fieldのまま。Heston θ=vとlocal θ=ℓを同じ物理量・同じ感応度として比較しない。

両Mに対して `C_M(t,S,θ)=Q` を同じbracket/root tolerance/唯一解検査で解く。Hestonの一方だけactual vを渡すことはしない。

- 全モデルパラメータやfuture smileを毎時点fitする作業ではない。observed call一価格だけをfitする。
- price bracket、bounds、Cθ、支持状態、fit residual、解の一意性を保存。解なし/非一意/bounds/支持外/near-zero Cθをunknownとして原始pathを保持する。
- local quoteが固定Heston族の最小価格より低い可能性がある。逆算成功を当然とせず、pilotで解なし率を確認する。mainで都合の良いpathsだけ採用しない。
- Qへfit前のcall gapとfit後のresidualを両方保存する。fit一価格が一致しても他のstrike/maturityが一致したとは呼ばない。
- actual Heston vを使うfull-information hedgeは別diagnostic。これと観測NNの差をNN性能と呼ばない。
- ℓを導入するとlocal Asian教師/conditional call表面にscalar axisが増える。§7のlocal教師候補は `(t,S,ℓ)` のcacheへ拡張し、ℓ-nodes3/7とθ-bumpをpilotで測る。元の固定local教師だけでQ riskを作ったことにしない。

### 8.2 RB-F07/IFTから共通市場座標へ変換

t,A,nを固定し、較正残差をR=C_M(t,S,θ)−Qとする。θは各Mのscalarで、Cθ≠0と局所一意性を仮定する。合成関数は

\[
\bar V_M(t,S,Q,A,n)=V_M(t,S,\theta_M(t,S,Q),A,n).
\]

IFTより

\[
\theta_Q=1/C_\theta,\qquad
\theta_{S\mid Q}=-C_S/C_\theta,
\]

したがって

\[
\boxed{\bar V_Q=V_\theta/C_\theta},\qquad
\boxed{\bar V_{S\mid Q}=V_{S\mid\theta}-V_\theta C_{S\mid\theta}/C_\theta}.
\]

ここでVS/CSは内部θを固定したspot微分。一般のscalar state記号θとHestonの長期mean varianceを区別する。両モデルともQは**IVやvolパラメータではなく実際に取引するcallの通貨価格**であり、VQの単位はcall契約数、VS|Qはstock数量。この変換を主比較に使う。scalarの単調な座標変換θ=g(η)では両θ微分に同じg'がかかるため比と保有量は不変になる。

RB-F07の`quote_sensitivity`はgeneral calibration adjointを実装しているが、この研究ではscalar式をprivate helperへ実装し、独立の再較正bumpで確認する。APIを広げる必要はない。

**小Black controlを別実装で計算した。** S=100,r=.03,q0,σ=.2、hedge call K100,T1.25、claim control K110,T1の欧州callを使った（Asianの検証ではない）。Q=10.700593492990613、V=5.293398058044907、VQ=0.9064930364808234、VS|Q=−0.1426401579548237。

毎回callをfitし直す中央bump幅.001ではVQ=0.9064930360125345、VS|Q=−0.1426401587742987。σ²座標による独立bump比は0.9064930364284705。両market-coordinate微分が直接の内部vega比と一致した。負stock保有量を誤りやbound違反としてclipしない。

新研究のmeaningful testsは、Asian selected-stateに対する再較正bump、σ/σ²またはℓ/logℓ座標変換、near-zero Cθ、非一意/支持外/active bounds、call実価格のcash会計。解析Jとraw bumpの金融比較はapprox、SHAはsource identityだけに使う。

### 8.3 適用限界

このquote-neutralityは一次のdS/dQ exposureを一致させる。離散時間、費用、制約、gap risk、model misspecificationを消さない。local Gではstockとcallは同じ一Brownian因子に依存するため、独立な市場リスクを二つ観測したことにもならない。

scalar逆算が広く失敗するなら「当該情報条件でのM hedgeが未解決」とする。共通Qをfitしたθ、J分母、境界/失敗を保存し、数値支持の限界を隠してHeston/local比較を成立させない。local/NNの動的結果は個別の支持状態として残せる。

## 9. 方策の候補と対照

### 9.1 Greek/band

- No hedge：cashと共通premiumだけ。会計/claim分母の対照。
- U2主基準は**市場クオートヘッジ**：
  \[
  h_C=\bar V_Q=V_\theta/C_\theta,\qquad
  h_S=\bar V_{S\mid Q}=V_S-h_CC_S.
  \]
- Hestonとlocalそれぞれが同じQをfitしてから、この共通market-coordinate targetを出す。内部VvとVℓをrawのまま並べない。near-zero call state感応度で無限大を0へ変えない。
- U1基準にはstock-onlyの強い局所risk projectionを推奨する。MのQ/spot瞬間covariance比βMを使い、`h_S=VS|Q + VQ βM`。Hestonでは `βM=CS + C_v ρ ξ/S`、localの固定multiplier forecastでは `βM=CS`。前者はmodel minimum-variance stock hedge、後者は同じQ fit後のmodel Deltaになる。主U2の共通Q座標をstockだけへ射影した基準で、VS|Qだけを強いstock-only baselineと呼ばない。
- raw stock Delta `VS|θ` とraw Delta-Gamma `hC=VSS/CSS, hS=VS−hC CS` は追加diagnostic候補。market-quote hedgeとは異なる目的/固定量なので、主結果と区別する。
- band型：old holdingのまま残るリスク距離が固定threshold内なら取引しない。thresholdはpilot/train validationのみで選ぶ。U2はoption含むtarget距離のスケールを事前に固定する。
- 共通position/turnover constraintsを採用するなら全方策で同じ値を使い、raw quote-risk targetとconstraint適用後holdingを両方保存する。これはモデルのrisk-neutral targetが完全実行可能という主張ではない。
- Hestonのv-factor hedge `h_C=V_v/C_v`は、scalar call state fit後なら上の市場クオート比になる。localにも同じ**観測call価格**で比を作ることが本研究の要点。raw Delta-GammaだけでHestonのvol factorを完全にspanできるとは呼ばない。

### 9.2 NN

- private実装は`deep_hedge_price`側。hullkitはTorch-freeのまま保つ。
- two-action shared MLP、previous holdingsをstateに含める。AsianのA/nがmemoryとして必要で、欧州5特徴policyを流用しただけでは足りない。
- scalerはtrainのみ、全G/Uで定義・単位を揃える。test全体のmean/stdは使わない。
- 主目的関数は共通p0を含むdiscounted P&LのMSE。ES95、mean loss、費用は評価指標。MSE最小化は完備市場の価格計算という意味ではない。
- 訓練G∈{Heston,local}×U∈{stock,stock+call}×初期化3seed＝**12fits**を候補にする。一次の訓練費用は正のspreadに固定する。
- 同じholdingをzero-cost会計で評価するcounterfactualは残すが、zero-cost-optimal NNと呼ばない。zero-cost用の追加12fitsは初回範囲外。
- optimizer、device、RNG状態、paired batch、updates、time cap/overrun、失敗理由を保存。中断/失敗seedをrosterから落とさない。
- 主評価とsaved checkerはexport済みNumPy weightsによるforward replay。notebookが学習し直さない。

### 9.3 初期価格を共通化する

p0はpilot/freeze以前の独立Heston Asian評価で固定する。同じGの全方策と別Gの全方策で同じp0を使う。各Mに都合の良いpremiumを使ってmodel gapを消さない。

別欄にprice gap、premium除外loss、各Gの独立fair-value推定を表示する。共通premiumのMSEはmean loss成分も含むため、variance-only指標も併記する。

## 10. 主実験のroster・seed・統計

以下の数量はcandidate。actual pilotから精度/費用を確認し、review/freeze後にmainを開始する。

- pilot：各G 4096paths、内部steps192/384/768、代表conditional statesと少量学習。主test normalは生成しない。
- main test：各G `32768×3`独立seed。96%以上のcoverageなど架空の達成値は置かない。
- fine Brownian normalsを粗stepへaggregateし、各G/各policy/各refinementで同じpath slotを使用。localは第1shockを使い、第2shockを無理に利用しない。
- SDE levels192/384/768とヘッジgrid48は別の軸。step refinementでhedge日時を変えない。
- train/validation/pilot/test/independent oracle/state-grid/初期化/bootstrapは別stream。master SeedSequenceから全rosterを事前に固定し、観測を見てseedを追加しない。
- 3初期化NNを別結果として表示する。経路SEと訓練seed間ばらつきを合体して「3倍path」と数えない。
- 初回はIIDでantitheticなしを候補とする。採用するならpairを統計単位にする。
- main testのoriginal denominators、失敗数、finite数、unknown数をG/U/policy/init/level単位で保持する。

Uごとの方策はno hedge、M=2のGreek、M=2のband、訓練G=2×init3のNN、計11。G2×U2×11＝44 primary cells。zero-cost counterfactual44は同じholding/pathを使うので新しい独立試行ではない。

### 10.1 指標とSE

| 指標 | 単位/比較方法 |
|---|---|
| mean discounted P&L/loss | 通貨、paired差のSE |
| MSE/RMSE | 通貨²/通貨、同じpathのloss²差/保存bootstrap indices |
| variance of loss | 通貨²、common premiumのmean成分と分離 |
| empirical ES95 | 通貨、original finite tail countとpaired bootstrap。標本ESをpopulation保証にしない |
| trade cost、gross gain、net gain | discounted通貨、init/interim/finalを別項 |
| turnover | stock/callの単位数量を別表示。異商品数量の無意味な単純和を主要指標にしない |
| constraints/unknown/failure | 原始pathsを分母にした件数と原因 |

同じGのA/B比較はpathごとのpaired differenceからSEを計算する。別GはCRNでcoupleできるが、同じ実現spotではない。cross-G差の意味はgenerator効果として区別する。

NaN/unsupported pathsを除いて全N結果を出すことはしない。全体指標が定義できなければunknownとし、有限subsetのdescriptive数値は「N_finite/N_original」と表示する。採用判断にfinite-onlyのMSEを使わない。

### 10.2 誤差を四つ分ける

1. SDE time discretization：192/384/768のpaired P&L/Greek/action差。
2. conditional MC/bump誤差：inner N、独立seeds、finite h、SE。
3. conditional price表面とtraded call PDEの補間/domain誤差。
4. 上の誤差を抑えた後のmodel gap/方策差。

model gapは単一の比較差から判定しない。価格・Greeks・会計・生成器の数値誤差に比べて差が識別できるかを確認する。非単調の3level差を厳密bias boundと呼ばない。

## 11. Drift・情報漏洩の検査

Q spotと、同じGによる条件付きQ call midを使う。別モデルでspotを生成しながら固定Black call quoteを貼ると、取引callの予測可能なdriftをNNが学ぶ恐れがある。

- discounted stock+CF、discounted call gainsの全体平均と事前のstate binsを保存。binはpilotにより固定、最低件数を定める。
- empty claimでno hedge/単純適応tradesのgainを確認する。fee後に有意な正gainがあればprice surface/補間/生成器の整合性を診断し、ヘッジ改善とは呼ばない。
- これは全適応方策に対するno-arbitrage証明ではない。必要なら小さなempty-claim NN検出器を追加し、別cost/rosterで記録する。
- train/testのraw path/hash identity、source/frozen protocol、scaler/training seedsをbindする。identity hashはprovenanceだけ。金融数値の照合は許容誤差を使う。
- 任意P drift stressはsecondary候補。μ=r±.05などを事前に固定する場合も、option価格drift/配当の整合性とspeculationを別に検査する。drift removal論文を再現したとは呼ばない。

## 12. 保存証拠・checker・全費用

### 12.1 原始証拠

JSONはimmutable metadata、NPZ/CASはnon-object typed arrays。最低限以下を保存する。

- source registry、candidate/frozen protocol、レビュー、全phase seed roster、全original slot IDs。
- quote/holdout price、raw local variance支持、PDE snapshots/grid/cutoff診断。
- conditional teacherのnormalsまたは再検算可能な原始draw、states、N、原始moments/SE、Greek h、interpolation nodes、支持範囲、selected independent oracle。
- testの全path hedge-date state、monthly observations、latent状態のdiagnostic、market prices/CF、path status/reasons。
- 全policyのholdings、trade/feeの十分統計、claim payoff、terminal cash、P&L、constraints、失敗metadata。cash全time配列を保存しなくても、全primitiveとholdingsからreplayできることを必須にする。
- NN全initのweight/scaler/batches/optimizer状態・time cap/updates/失敗を保存。best seedだけ保存しない。
- bootstrap indicesを保存し、notebookで乱数を再生成しない。

32768×3×768×2のnormalはG共用で約1.21GBのfloat64原始データ。全positions等もGB級になり得る。chunk生成/NPZ圧縮/CASによる分割保存をpilotで測る。保存するprimitiveを減らす場合は数値replay可能性を先に確認し、あとから観測の悪いpathだけ省かない。

### 12.2 Saved-only checker

checkerはRNG、optimizer、学習、networkなし。

- 原始roster、seed provenance、schema、status固有の必須timing/cost keysetを確認する。
- 全pathsのcash recursion/discounted gain identity、費用、payoff、P&Lを再算出する。
- 保存stateから決定的call/conditional spline/NumPy policyを再生し、selected C/Δ/Γ/oracleを照合する。
- SVD/optimizerがある場合はsign/basis不変量で比べ、floatは非ゼロ許容差。
- unknown reasonとinvalid primitive maskを照合する。valid slotをunknownへ書き換えて悪い結果を隠せないようにする。
- 全統計・SE・bootstrap・採否をrawから再算出。保存済み「PASS」文字列を証拠にしない。
- freshは別receiptで、凍結seedの代表case再生成/独立再評価を行い、原始recordを改変しない。

### 12.3 全費用

complete unique expense registryを使い、status固有の必須項目とscopeを先に固定する。timersとexpensesを同時に削除して「全て無料」にできないgateを必要とする。

| phase/仕事 | 数えるもの |
|---|---|
| initial fit/surface | 独立CF、surface生成、PDE、grid/cutoff validation、optimizerを実行した場合は全start |
| conditional teacher | RNG、SDE、last-step conditioning、全Greek bump、oracle、補間構築/validation、fallback |
| pilot/freeze | 全pilot paths/fits、判断に使わなかったfailed trial、independent review/freeze検算 |
| training | train/validation generationとcall quote、全12fits/全init、CPU/GPU、失敗/overrun、export |
| main | GのRNG/engine、call pricing/state inference、policy inference、cash accounting、統計/bootstrap |
| artifact/replay | serialization、compression/CAS upload/load、cold import、saved check、fresh、3図/notebookbuild |

methodに配賦する共通expenseとresearch-only expenseを区別する。親inclusive時間と子breakdownを両方課金しない。未測定はNone/pendingであって0ではない。生timingとscopeを変更せず、別bound receiptでpendingを解決する。

比較表示は(1)state/prices既知のpolicy online、(2)市場stateからGreek/quote込みmain、(3)教師/学習込みcold、(4)候補trade数でのamortizedを分ける。accuracy未達の高速methodとのspeedupを採用根拠にしない。

本調査の設計値から実行時間を断定できない。条件付きAsian教師、call quote snapshots、12NNfits、GB級保存の孤立pilot計測が工数見積もりの前提になる。現在のF05 full計算とは同時に重いpilotを走らせない。

## 13. 必須3図と採否

### 図1：価格面と動的リスクの支持

初期fit25/holdout12のerror、条件付きselected statesのC/VS|Q/VQと再較正bump比較、current call quoteのfit前gap/fit後residual/逆算unknown率を表示。価格面にfitしただけでGreekが検証済みだと見せない。元quote/state数とfailureも併記する。Gammaは追加diagnosticがある場合に別欄で表示する。

### 図2：動的P&Lと費用

G×Uの4panelでGreek/band/各NN initのnet P&L分布、MSE/RMSE、ES95、gross gain、費用を表示。zero-cost counterfactualは同じholdingsという注記、unknown/失敗は専用欄で残す。薄い平均線だけで全seedを隠さない。

### 図3：cross-generator頑健性と数値/費用予算

訓練G×評価Gのpaired risk差、3SDE levels/conditional teacher refinement差、online/main/cold/amortized費用を表示。rawデータ不足やpendingを空白の成功plotにしない。

### 採否の分離

| 状態 | 条件 |
|---|---|
| `numerically_supported` | 初期fit、conditional C/Greeks、call/martingale、cash/check/fresh、原始分母/全失敗/費用が揃う |
| `teaching_candidate` | 上の条件と3図/説明が揃う。独立review未完ならaccepted/retainedと呼ばない |
| `risk_improvement_supported` | 事前に固定した基準/最小改善幅に対し、同じG/Uのpaired CIが支持。数値誤差やfailureを含め不明ならunknown |
| `cross_generator_robustness_supported` | 訓練モデル外の主セルでも基準比risk支持。train内の改善だけでは不可 |
| `speedup_supported` | 同等精度の比較器とのmain/cold scopeが整う。NN price/Greek誤差未解決なら不可 |
| `practical_adoption` | 今回はunknown。合成2モデル、固定費用、単一claim/期間では市場運用を判定できない |

複数比較は主比較を事前指定する。候補は「同じUの最善train-validation band baselineとのNN差」。mainの各cellで基準を選び直さない。全44セルと3initを表示し、都合のよい一つの勝者だけ採用しない。

## 14. 実装順序案と完成条件

| 段階 | 仕事 | 次段階へ進む条件 |
|---|---|---|
| D0 設計/source整備 | 2論文identity分離、candidate契約/roster/費用/採否固定 | formal specレビュー、未解決を明示 |
| D1 動的core/会計 | 任意record grid、月次claim memory、vector prices/CF/fees、cash/discounted二重計算 | hand toy、GBM limit、terminalfee、dividendCF、failedpathsの独立テスト |
| D2 conditional evaluator | 長期call snapshots、Asian条件付き教師/補間、Greeks/oracle、state inference | 代表stateとgrid/step/bump/MC gate成立、支持範囲明確 |
| D3 dynamic Greek/band | G×M、U1/U2、完全P&L、martingale/emptyclaim | no trainingのtiny end-to-end saved/check。瞬間shockだけで代替不可 |
| D4 pilot/NN | 12fits rosterの小pilot、時間/精度/seed/費用/state guard | 独立review、source/candidate/pilotにbindしたfreeze |
| D5 frozen main | 全seed/全G/U/policy/level、unknown/失敗を保持 | 数値支持とfullcost saved/check/fresh |
| D6 artifact/受入 | 3図、artifact-only notebook、source/失敗/費用説明 | 別セッション受入方針に合わせ独立review/台帳更新 |

ルーチンのpublic API、依存、既存deep demo規約を変えない。将来の追加はprivate hullkit金融coreとprivate deep learner、research orchestrator/reference/artifactに分ける。正式filename/interfaceはまだ決定していない。

## 15. 具体的な不足・未確認

### 実装不足

1. 任意ヘッジgridとmonthly Asian memoryを持つ条件付きrestart/state recorder。
2. T*=1.25まで支持・検証したlocal surfaceと、calendar-time条件付きcall snapshots。
3. Asian条件付きC/VS/Vθ教師、滑らかな補間、独立selected-state/recalibration oracle、数値支持/外挿state。Gamma対照を加える場合は二階検証。
4. cross-GのHeston v/local multiplier一quote state fit、IFT market-coordinate変換、再較正bumpと解なし/非一意/near-zero J診断。
5. stock+call+CF+金利+init/interim/final費用のNumPy/Torch一致会計。
6. 同一情報・二action・train-only scaler・private NN export/replayと12fits runner。
7. 全original roster、timing/status/scope gate、CAS/chunk保存、saved-only checker、費用receipt、3図。

### 出典/独立検証不足

1. processed 2504.06208v3との公式PDF byte identity、正式source_id/metadata分離（今回調査だけで正式台帳は未更新）。
2. 長期callのconditionalPDE snapshots、Asian smoothing/homogeneity式、local Asian PDE/QE参照について、実装前に一次数値資料を追加照合する必要がある。本メモの導出だけで外部検証済みと呼ばない。
3. 著者コードのcommit/license/APIは未確認。実証を複製するなら別途取得/検査が必要。
4. OptionMetrics/JIVR原始価格、実行可能spread、配当/利率履歴、契約rosterの利用権とデータは未取得。歴史backtestの再現・主張は範囲外。
5. 条件付きAsian教師と12fitsの実測費用、GB級artifact保存/復元の時間は未計測。

### 実施済みの検証と未実施

実施済み：指定コードとRB-F04受入文書/一次資料の読解、2論文identityの一次資料照合、二assetの小さなcash/discounted会計identity計算。

未実施：新金融ソース、formal spec/plan、主MC、training、T*=1.25 surface生成、conditional oracle、pilot、主P&L、3図、採否、受入、commit/push。現在進行中のF05計算とは独立した設計メモに留めている。
