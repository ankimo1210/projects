# 較正込み市場クオートGreeksのDML — v1結果

更新2026-10-09。**30 NN fits＋4回帰、独立fresh再計算、310速度計測、
288費用対照、両保管庫復元、artifact-only研究3図を作成・実行した。
独立最終成果レビューを承認済み。`a25345e1`をmainへ統合し、統合後の全関連suiteとrelease gateもPASS。NNの標準価格/Greek器への昇格は不採用。**

[研究設計](../../../docs/superpowers/specs/2026-10-09-calibrated-quote-dml-design.md)／
[実施計画](../../../docs/superpowers/plans/2026-10-09-calibrated-quote-dml.md)／
[実装レビュー記録](REVIEW.md)。
既存の [RB-F07 v1](../README.md) と [RB-F05 digital v1](../../RB-F05/README.md) は保持する。

## 現時点の結果

- **H1：Q-DMLはQ-priceより正規化6Greek RMSEが低い。**
  両学習サイズ・全3seedでpaired差の95% CI上端が0未満。
  ただし価格・spot Delta・35ショック混合のヘッジ残余は全6組で悪化した。
  集約Greek指標の改善を「価格・全Greek・ヘッジの改善」と呼ばない。
- **H2：quote入力の優位は支持されない。**
  同じ市場risk metricを使うTheta-quote-metricのほうが、全6組でQ-DMLより正規化6Greek RMSEが低い。
  Q-DML−Theta-quote-metricの95% CI下端は全6組で正。
  内部対角metricのTheta-DMLだけを対照にして、quote座標の優位を主張しない。
- **低次元differential ridgeは強い対照になった。**
  正規化6Greek RMSEはn512で0.340881、n2048で0.326669と、全NN方式より低い。
  価格とspot Deltaの誤差は別に残るため、全指標で最良とは呼ばない。
  digitalの曲線依存を既知の1スカラーに要約できることを利用している。
- **H3：Q-DMLのGreek集約誤差は低下したが、35ショック混合の固定ヘッジ残余は低下しなかった。**
  金利だけの1bp/10bp残余は全6組で改善したが、spot/組合せは悪化した。
  35種類の固定ショックを等しく混ぜた残余RMSEは、対応するQ-priceより全6組で大きい。
  入口費用が低いことと、ヘッジが良いことも分けて評価する。
- **H4：価格＋6Greekの全面的な速度優位は支持されない。**
  prepared解析に対するraw102対照、同じ較正条件のsafe42対照で、median/p95とも近似器の優位なし。
  e2e42対照の5件だけmedianで約0.2–1.0%速いが、解析と精度同等ではなく計時CIもない。
  小幅な観測差と条件付き償却を示し、速度/Greek標準器への採用根拠にはしない。

上記は固定した合成protocol・512 optimizer updatesの結果。
結果を見てseed・領域・loss重み・checkpointを選び直していない。
悪化の原因分解や再チューニングの効果は検証していない。

## 固定した市場・商品・分割

| 項目 | 本実験の条件 |
|---|---|
| 較正 | 決定論的な単一曲線、正方5商品。柱zero rateは0.5/1/2/3/5年、zero線形補間・区間外zeroフラット |
| quote中心 | 6か月預金3%、6×12 FRA3.2%、2/3/5年swap3.3/3.45/3.6%。各quoteを独立一様±50bp |
| 価格対象 | 無配当GBMのcash-or-nothing call、K=100、payout=1、sigma=20%。年時刻のみ、日付/day countなし |
| 入力領域 | S=80–120、T=0.05–5年。train/validationのTはlog-uniform |
| train | 256市場曲線×8契約=2048行。n512は先頭64市場×8行の入れ子部分集合 |
| validation | 独立64市場×8契約=512行。診断のみ、設定/seed/checkpoint選択に使わない |
| test | 独立128市場×固定8契約=1024行 |
| test契約(S,T) | (80,.05)、(95,.25)、(100,1.5)、(110,4.5)、(120,5)、(100,.5)、(100,1)、(110,3) |
| RNG | SeedSequence([20261009, split])、train/validation/testはsplit0/1/2。市場ID・契約IDを保存 |
| 比較数 | 5 NN方式×2サイズ×3seed=30 fits、2 ridge方式×2サイズ=4 fits、計34保存モデル |

同じ市場曲線の8行は独立な8市場ではない。分割と統計評価の群単位を市場曲線に揃える。
このtestは8契約に限定した比較で、領域全体の任意契約に対する精度保証ではない。

## 数式・座標・単位

列勾配を使い、較正残差F(z,q)=0の局所可逆性を仮定する。
A=dz/dqは「zero柱が行、quoteが列」で、内部勾配の市場座標への変換はAの転置で行う。

\[
A=-F_z^{-1}F_q,\qquad g_q=A^\top g_z .
\]

本実験は直接quote依存なし、F=m(z)−qの正方較正。
曲線discountをD、R=−log D、v=sigma sqrt(T)、a_q=∇q Rとして、

\[
d_2=\frac{\log(S/K)+R-v^2/2}{v},\quad
V=D\Phi(d_2),\quad
\Delta_S=\frac{D\phi(d_2)}{Sv},\quad
g_q=D\left[-\Phi(d_2)+\frac{\phi(d_2)}v\right]a_q .
\]

quote bump中はS/K/T/sigmaを固定し、spot bump中は曲線を固定する。
discountとGBM分布の両方の曲線依存を微分する。

保存入力はquote5（またはzero5）、spot、T。
NN特徴はrate5、log(S/K)、log Tで、trainのみから標準化する。
保存risk順はspot、deposit6m、fra6x12、swap2y、swap3y、swap5y。
spot Deltaは通貨/spot単位、quote Greekは通貨/rate decimal。1bp表示にはquote成分だけ1e-4を掛ける。

正規化6Greek RMSEは、各成分の物理誤差を当該trainのquote Greek RMSで割り、
全test行×6成分の二乗平均の平方根を取る。
同じnの全方式に共通尺度を使うが、n512とn2048ではtrain RMSが異なる。
サイズ間の改善をこの正規化値だけで判定しない。
内部Theta-DMLの学習尺度と、全方式共通の評価quote尺度も区別する。

## 34モデルの比較仕様

| 保存方式名 | 入力・学習loss | 評価時のGreek |
|---|---|---|
| q_price | quote入力、価格のみ | 物理quote/spotへの微分 |
| theta_price | zero入力、価格のみ | spotとA転置によるquote変換 |
| theta_dml | zero入力、価格＋内部Greek対角尺度loss | 同じ物理quote変換 |
| theta_quote_metric | zero入力、価格＋変換後の市場Greek loss | Q-DMLと共通の市場risk metric |
| q_dml | quote入力、価格＋市場Greek loss | 物理quote/spotへの微分 |
| ridge_price | (log(S/K),R,log T)の全3次以下20項、価格回帰 | 特徴の解析微分とa_q |
| ridge_dml | 同じ20項、価格＋市場Greek回帰 | 同じ特徴微分 |

NNは7→64→64→1、tanh・線形出力、CPU float64/1 thread、Adam lr=.001、
batch256、512 updates、seed11/29/47、Greek loss重み1。
同じseedの5方式は同じ初期重みとbatch順。30本とも512 updatesを完了し、
120秒watchdogのbudget failureは0。4本の回帰も保存済み。

ridgeの罰則は1e-8、切片は罰しない。価格行と6Greek行の平均を揃えてlstsqする。
既知のRへの要約を利用するため、汎用7入力NNと同じ表現能力の比較ではない。
価格/Greekの尺度・係数・全重みを保存し、独立NumPy replayで取り出せる。

## H1/H2：市場群paired bootstrap

差は「Q-DMLの正規化6Greek RMSE−比較相手のRMSE」。負はQ-DMLのほうが低い。
H1の相手はQ-price、H2はTheta-quote-metric。同じn・同じ学習seedで比較する。
128市場を復元抽出し、各市場の8契約をまとめて引く。2000反復、seed20261010、
percentile 95% CI。各群の平均二乗誤差を集約してから平方根を取る。

| train n | seed | H1差 | H1の95% CI | H2差 | H2の95% CI |
|---:|---:|---:|---|---:|---|
| 512 | 11 | -8.0322 | [-8.37734, -7.6907] | 0.0157627 | [0.00717051, 0.0250782] |
| 512 | 29 | -8.39445 | [-8.8911, -7.93323] | 0.0308821 | [0.0203823, 0.0415087] |
| 512 | 47 | -8.30665 | [-8.72858, -7.88318] | 0.0252998 | [0.0172409, 0.033647] |
| 2048 | 11 | -5.71887 | [-6.0744, -5.39082] | 0.0482643 | [0.037135, 0.0607505] |
| 2048 | 29 | -4.79935 | [-5.03394, -4.5652] | 0.0222775 | [0.0151689, 0.0301629] |
| 2048 | 47 | -4.57143 | [-4.84711, -4.32148] | 0.047192 | [0.0408856, 0.0540234] |

CIは固定した学習済みモデル/学習seedに条件付きのtest市場群の不確実性。
学習seedの分散・将来市場・時系列依存・複数仮説を含む一般的な有意性を保証しない。
H1/H2の改善主張には事前規約の「全3seedで低下、各CI上端<0」を使う。
H1は両nでこの条件を満たすが、H2のQ-DML優位は満たさず、逆方向の差を得た。

## 全34モデルのmainコア実測

数値は保存JSONから6桁に丸めた表示。丸め表を数値オラクルにしない。
価格はpayout1の通貨単位、Deltaは通貨/spot単位、残余・入口費用も通貨単位。
「参照残余との差」は各ショックにおける推定Greek hedge残余−参照Greek hedge残余のRMSE。
入口費用meanは全test中心に対する金利半spread0.5bp・株式半spread1bpの1回の組成費用。

### train n=512

| 保存モデルID | 価格RMSE | 正規化6Greek RMSE | spot Delta RMSE | 残余RMSE | 参照残余との差RMSE | 入口費用mean |
|---|---:|---:|---:|---:|---:|---:|
| q_price_n512_s11 | 0.0349821 | 9.00913 | 0.00459431 | 0.00415412 | 0.00415348 | 0.000665576 |
| q_price_n512_s29 | 0.027593 | 9.34525 | 0.00371501 | 0.00334494 | 0.00334423 | 0.000732516 |
| q_price_n512_s47 | 0.0364146 | 9.22689 | 0.00475247 | 0.00387744 | 0.00387733 | 0.000727603 |
| theta_price_n512_s11 | 0.0356154 | 8.78402 | 0.00431126 | 0.00451302 | 0.00451267 | 0.000705893 |
| theta_price_n512_s29 | 0.0289622 | 8.14845 | 0.00372452 | 0.00326224 | 0.00326147 | 0.000692103 |
| theta_price_n512_s47 | 0.0371436 | 8.90285 | 0.00480527 | 0.00429087 | 0.0042908 | 0.000745247 |
| theta_dml_n512_s11 | 0.190434 | 0.956506 | 0.0186058 | 0.00756934 | 0.00757588 | 5.64354e-05 |
| theta_dml_n512_s29 | 0.187536 | 0.930127 | 0.0183812 | 0.00747513 | 0.00748167 | 6.26926e-05 |
| theta_dml_n512_s47 | 0.186635 | 0.908315 | 0.0184065 | 0.00748583 | 0.00749237 | 6.27251e-05 |
| theta_quote_metric_n512_s11 | 0.190527 | 0.961168 | 0.0185969 | 0.00756551 | 0.00757205 | 5.96052e-05 |
| theta_quote_metric_n512_s29 | 0.186267 | 0.919915 | 0.0182868 | 0.0074348 | 0.00744134 | 6.72682e-05 |
| theta_quote_metric_n512_s47 | 0.187607 | 0.89494 | 0.0184477 | 0.00750234 | 0.00750888 | 6.27329e-05 |
| q_dml_n512_s11 | 0.191342 | 0.976931 | 0.0187014 | 0.00760957 | 0.0076161 | 6.20702e-05 |
| q_dml_n512_s29 | 0.18792 | 0.950797 | 0.018378 | 0.00747358 | 0.00748013 | 6.24689e-05 |
| q_dml_n512_s47 | 0.190114 | 0.92024 | 0.0186482 | 0.00758603 | 0.00759256 | 5.9922e-05 |
| ridge_price_n512 | 0.0377946 | 5.0674 | 0.00743494 | 0.00389839 | 0.00389698 | 0.000287877 |
| ridge_dml_n512 | 0.0535958 | 0.340881 | 0.00866011 | 0.00417685 | 0.00417621 | 0.000206722 |

### train n=2048

| 保存モデルID | 価格RMSE | 正規化6Greek RMSE | spot Delta RMSE | 残余RMSE | 参照残余との差RMSE | 入口費用mean |
|---|---:|---:|---:|---:|---:|---:|
| q_price_n2048_s11 | 0.0252274 | 6.67593 | 0.00260934 | 0.00293581 | 0.00293407 | 0.000568341 |
| q_price_n2048_s29 | 0.023929 | 5.71583 | 0.00311216 | 0.0024493 | 0.00244738 | 0.000497531 |
| q_price_n2048_s47 | 0.0255136 | 5.46553 | 0.00347504 | 0.00236453 | 0.00236347 | 0.000455618 |
| theta_price_n2048_s11 | 0.0242823 | 6.17867 | 0.00257763 | 0.00297169 | 0.00297003 | 0.00056631 |
| theta_price_n2048_s29 | 0.0227533 | 4.91527 | 0.00283173 | 0.00236742 | 0.00236533 | 0.000468708 |
| theta_price_n2048_s47 | 0.0250241 | 4.75205 | 0.00329522 | 0.00227211 | 0.00227098 | 0.00044785 |
| theta_dml_n2048_s11 | 0.193234 | 0.914762 | 0.0186107 | 0.00757088 | 0.00757742 | 5.91819e-05 |
| theta_dml_n2048_s29 | 0.191147 | 0.902044 | 0.0183506 | 0.00746223 | 0.00746877 | 6.48787e-05 |
| theta_dml_n2048_s47 | 0.190276 | 0.856223 | 0.018408 | 0.00748631 | 0.00749285 | 6.11925e-05 |
| theta_quote_metric_n2048_s11 | 0.19341 | 0.908792 | 0.0185948 | 0.00756392 | 0.00757046 | 5.87779e-05 |
| theta_quote_metric_n2048_s29 | 0.190126 | 0.894199 | 0.0182816 | 0.00743281 | 0.00743936 | 6.88488e-05 |
| theta_quote_metric_n2048_s47 | 0.19057 | 0.846911 | 0.0184219 | 0.00749165 | 0.00749819 | 6.234e-05 |
| q_dml_n2048_s11 | 0.194849 | 0.957056 | 0.0187367 | 0.00762445 | 0.00763098 | 5.81876e-05 |
| q_dml_n2048_s29 | 0.191601 | 0.916477 | 0.0183996 | 0.0074826 | 0.00748914 | 6.58833e-05 |
| q_dml_n2048_s47 | 0.19337 | 0.894103 | 0.0186718 | 0.00759644 | 0.00760297 | 5.75797e-05 |
| ridge_price_n2048 | 0.0415022 | 3.49139 | 0.00873549 | 0.00428686 | 0.00428518 | 0.000280391 |
| ridge_dml_n2048 | 0.059464 | 0.326669 | 0.00933935 | 0.00452858 | 0.0045276 | 0.000211356 |

全方式のMAE/p99/max、6成分ごとの物理/正規化Greek、数量差、
満期別(short T≤.25 / medium .25<T≤1 / long T>1)、
moneyness別(OTM S/K<.95 / ATM .95≤S/K≤1.05 / ITM S/K>1.05)、
ショック別残余、12種類の費用mean/p99はreference.jsonのmetrics.modelsに保存する。

真のabs Greek<1e-12をゼロbucketとして、漏れの件数と物理誤差も保存する。
各サイズのゼロbucketはtestで2304成分。ridgeはa_qを使う構造により、
この集合での漏れRMSEは約1e-17。NNの漏れはゼロにならない。
ゼロ判定や成功フラグだけで、価格・Greekの正しさを宣言しない。

## H3のショック別分解

35ショックの混合指標だけでは、rate hedgeとspot hedgeを区別できない。
保存済みby_shock RMSEを使い、群内の二乗平均から残余RMSEを再集計した事後の記述的分解を示す。
主protocol、35本の重み、loss、seed、H1/H2を変更する追加検定ではない。

次表はQ-DML/Q-priceの残余RMSE比。1未満はQ-DMLのほうが小さい。
金利1bp/10bpは各14本、spotは2本、組合せは4本。ゼロshockはこの分解へ混ぜない。

| 学習組 | 金利1bp | 金利10bp | spot ±1% | spot＋金利 |
|---|---:|---:|---:|---:|
| n512 / s11 | 0.094 | 0.094 | 4.527 | 2.094 |
| n512 / s29 | 0.098 | 0.098 | 5.174 | 3.179 |
| n512 / s47 | 0.089 | 0.089 | 4.303 | 2.401 |
| n2048 / s11 | 0.132 | 0.132 | 6.213 | 2.980 |
| n2048 / s29 | 0.160 | 0.160 | 5.613 | 3.525 |
| n2048 / s47 | 0.172 | 0.172 | 5.186 | 3.667 |

金利だけの残余は全6組で約83–91%小さい一方、spot/組合せは悪化し、35本を等しく混ぜたRMSEは悪化する。
市場quote riskの改善をspot Deltaや全商品hedgeの改善へ外挿できないことが、この実験の結果である。

n2048/seed11の絶対値（payout1の通貨単位）は次のとおり。

| ショック群 | Q-price RMSE | Q-DML RMSE |
|---|---:|---:|
| 金利1bp | 0.000305018 | 4.03078e-05 |
| 金利10bp | 0.00305019 | 0.000403111 |
| spot ±1% | 0.00296166 | 0.0184008 |
| spot＋金利 | 0.00617593 | 0.0184062 |

群別の低下率もこのstress集合の記述であり、発生確率付きの市場P&Lや新しい有意性主張ではない。
NNの再チューニングやGreek損失の変更はこの結果に含めない。

## 固定契約・35ショック・入口費用

ヘッジ列順は株式1単位、預金、FRA、2/3/5年swap。
金利商品は各100万元本。各test市場の開始quoteをcoupon kへ固定して保有し、
ショック後もcoupon・支払時刻・元本を変えない。FRAは期末支払型。
中心市場ごとに異なる固定契約で、全128市場に同じcouponを流用する実験ではない。

全モデルで同じ独立参照のrisk行列Bを使い、Bh=−gを解く。
ヘッジ数量の単位は株数と100万元本金利契約数。
bp行正規化を使ってsolveし、rank不足は失敗として扱う。

\[
\varepsilon=
 V(x+\delta x)-V(x)+
 \sum_i h_i[H_i(x+\delta x;k_i)-H_i(x;k_i)] .
\]

対象商品・保有契約のショック後価格は全方式で共通の価格器を使い、
NN/回帰で変わるのはgとそこから解くh。
推定価格差をヘッジ残余へ混ぜない。
参照Greekで組んでも曲率残余があるため、残余そのものと参照残余との差を分ける。

| ショック | 個数 | 変える量 |
|---|---:|---|
| ゼロ | 1 | なし |
| quote単独 | 20 | 5 bucket×±1/±10bp |
| 平行/steepener | 8 | 各±1/±10bp。steepener形状は(−1,−1,0,+1,+1) |
| spot単独 | 2 | ±1% |
| 組合せ | 4 | spot±1%×quote平行±10bp |
| 合計 | 35 | T・sigma・契約条件は固定 |

全35ショックの等重みRMSEはこのstress集合の指標。
発生確率を推定した実市場P&L・動的リバランス・自己資金ヘッジの成績ではない。
金利クオートを動かした後、保有契約を新par条件へ書き換えると別のヘッジになる。

金利の1契約当たり入口費用は自bucket PV01の絶対値×半spread、
株式はspot×半spread(bp)×1e-4。数量絶対値を掛けて合計する。
半spreadは金利0/.1/.5/1bp×株式0/1/5bpの4×3 stress。
料金の観測値・実市場の流動性推定ではない。残余へ足して利益率と呼ばず、別指標にする。

## MC教師診断とSE

主学習教師は解析価格・解析6Greek。主学習の比較結果にMCの教師ノイズはない。
別診断としてLRM、alpha=.5の厳密conditioning、naive PW、割引微分を落とした教師を保存する。

\[
Y=D1_{\{S_T>K\}},\qquad
\widehat\Delta=Y\frac Z{Sv},\qquad
\widehat g_q=Y\left(-1+\frac Zv\right)a_q .
\]

「−1」が割引微分。naive PWはspotが0、quoteは−Y a_qとなり境界寄与が欠ける。
これらの負の対照が理論上のbiased meanに一致しても、正しいGreek教師になったとは判断しない。

S95/100/105×T.05/.25/1.5/4.5の12 nominal条件と、
S80/T.05のrare条件を用意する。
65536 IID normal draws、main seed1107、独立pilot seed6017。
同じstreamは条件間で共有するため、各条件のpath軸から計算するSEは有効だが、
条件間の独立性やcross-condition有意性は主張しない。

mean/SE・2次モーメント・raw draws・hit/miss数を保存し、
独立密度積分/条件付き積分/解析2次モーメントと再計算する。
6SE＋固定数値許容差は本学習前に固定。pilotで主結果に合わせて緩めない。
expected hitまたはmiss数<20は通常6SE評価の対象外。
rare条件のゼロhit・ゼロSEを正しさの証拠にしない。
MC診断をNNのMC教師学習比較や短期/rough性能の結果へ読み替えない。

## raw・safe・OOD

rawは保存ネット/回帰の出力。safeはdomain・曲線診断・価格範囲[0,D]を確認した結果。
異常をclipして正常価格にしない。
q/spot/Tの領域外、対応可能なstrike/sigma変更、quote→zero増幅>10、
raw価格の範囲違反は、較正可能なら解析価格と全Greekへfallbackする。
数学的に有効なnegative rateを無効入力とは扱わない。

pillar/schedule/interpolation変更はunsupported_contextで価格を返さない。
数学的に無効な入力、較正不能・rank不足はfailure。
raw/safe予測・routing・fallback件数・理由は別配列へ保存する。
safeの価格/Greek誤差にはsaved safe出力を使い、raw誤差を流用しない。
wrapper通過はNN Greekの精度保証ではない。

上の34モデル表とH1/H2はraw出力の比較。
safeの保存出力は全34方式・全seedで集計でき、計時は事前の代表7方式だけである。
price-only NNとridgeは各128/1024（12.5%）fallback、DML NNの3方式は両n・全seedで0%。
全34合計2048/34816（5.88235%）は全てS80/T.05の負価格によるprice_bounds。
上限D違反は0である。通過したDML NNのGreekが正確になったことは意味しない。
OOD22件は正常control1を含み、各方式ok1/fallback17/unsupported3/failure1。
負金利は数学的無効ではなくquote OODとしてfallbackした。

## H4：計時・総費用・採否

warmup3後100反復、batch1/32/1024、median/p95と生標本を保存した。
単位はseconds per full batch。BLAS/OMP/MKL各1 thread、CPU環境を記録。
market共有較正はbatch1/32/1024で1/4/128回、row較正は1/32/1024回。
全310測定の内訳はcached解析6、raw204、較正6、e2e48、safe42、hedge3、bump1。
e2e/safeは事前固定の最大n・seed11の5 NN＋最大nの2 ridge、rawは全34方式。

次表の速度比はexact/surrogate。1超で近似器が速い。
**価格＋6Greekだけの対照**で、prepared、market共有、row較正を混ぜない。
p95は標本の遅延分位点であり、速度差のCIでも期待総費用でもない。

| source / cache | batch | 方式数 | median比の範囲 | p95比の範囲 | 1超の件数 median/p95 |
|---|---:|---:|---:|---:|---:|
| raw / prepared | 1 | 34 | 0.105–0.459 | 0.098–0.454 | 0/0 |
| raw / prepared | 32 | 34 | 0.087–0.215 | 0.079–0.193 | 0/0 |
| raw / prepared | 1024 | 34 | 0.029–0.031 | 0.028–0.035 | 0/0 |
| e2e / market | 1 | 7 | 0.834–0.983 | 0.792–1.072 | 0/1 |
| e2e / market | 32 | 7 | 0.945–0.990 | 0.939–1.000 | 0/0 |
| e2e / market | 1024 | 7 | 0.981–1.010 | 0.976–1.033 | 3/5 |
| e2e / row | 1 | 7 | 0.846–0.952 | 0.772–0.930 | 0/0 |
| e2e / row | 32 | 7 | 0.944–0.997 | 0.876–0.995 | 0/0 |
| e2e / row | 1024 | 7 | 0.993–1.002 | 0.985–0.999 | 2/0 |
| safe / market | 1 | 7 | 0.653–0.737 | 0.630–0.756 | 0/0 |
| safe / market | 32 | 7 | 0.196–0.245 | 0.203–0.255 | 0/0 |
| safe / market | 1024 | 7 | 0.196–0.241 | 0.200–0.247 | 0/0 |
| safe / row | 1 | 7 | 0.638–0.721 | 0.623–0.689 | 0/0 |
| safe / row | 32 | 7 | 0.645–0.716 | 0.603–0.710 | 0/0 |
| safe / row | 1024 | 7 | 0.665–0.724 | 0.659–0.718 | 0/0 |


準備済み解析よりrawは遅く、safeも同じ較正条件の解析より遅い。
e2eでは較正が大半を占め、大batchの一部で小さな観測差が出た。
全seedへの速度一般化、精度を合わせた費用優位、統計的な速度差は確認していない。
価格だけではraw102対照中34件にmedian優位があるが、価格＋Greekの結果へ読み替えない。

### バッチ単位の総費用

\[
C(N_{\rm calls})=C_{\rm offline}+N_{\rm calls}t_{\rm batch},\qquad
N_{\rm calls}=\left\lceil N_{\rm queries}/B\right\rceil .
\]

端数queryでも実測full batchを1回実行するとして、分数callの割引をしない。
288費用対照はraw204＋e2e42＋safe42で、同じoperation/batch/cacheの解析器を参照とする。
各対照に1/10/100/1000/10000 callとquery budgetのC(N)、連続償却点、
最初の整数call・処理行数を保存する。参照の追加fit原価は0で、共通準備は各onlineカテゴリで揃える。

1方式のtrain-only費用は、そのnの教師＋setup/fit/export。
NNではsetup、training、復元thread等のoverhead、exportを分ける。
ridgeはfitがexport辞書を返すので、setup/fit/exportはまとめたelapsedであり未測定の内訳を0とはしない。
deploymentシナリオにはwarm-cacheの**研究bundle全体**読み込み＋1方式decodeを追加する。
最小モデルだけの配布、cold IO、JSON parse、module import、process起動はこの計時に含まない。
NPZ読み込みはmedian 0.144787秒、p95 0.150425秒、各方式decodeも100標本を保存した。

次表は価格＋6Greekでmedianに正の観測savingがあった5対照だけ。
保存教師原価を含め、表の件数は**整数callの処理行数**（batch1024）である。
p95シナリオは別に保存し、median/p95成分の和を実測総費用のp95と呼ばない。

| e2eの方式 / cache | median速度比 | train-only最初のcall / 処理行数 | bundle loading込みcall / 処理行数 |
|---|---:|---:|---:|
| q_price_n2048_s11 / market | 1.00981 | 703 / 719,872 | 842 / 862,208 |
| theta_dml_n2048_s11 / market | 1.00836 | 1116 / 1,142,784 | 1278 / 1,308,672 |
| ridge_dml_n2048 / market | 1.00373 | 884 / 905,216 | 1248 / 1,277,952 |
| q_dml_n2048_s11 / row | 1.00205 | 586 / 600,064 | 670 / 686,080 |
| ridge_dml_n2048 / row | 1.00216 | 194 / 198,656 | 274 / 280,576 |


全288対照ではmedian deploymentの償却可能39件、online優位なし249件。
39件には価格だけの34件が含まれ、上のGreek付き5件と区別する。
比較全体の測定小計は17.466秒
（全分割教師0.602775＋34fit 16.8619＋別計測NN export 0.00137327）。
独立oracle、長いbenchmark実行、serialization、図生成の費用は未計測で、
この小計を研究の全所要時間と呼ばない。

### 採否

- **教材・接続研究として保持する。** 正しい教師、市場単位、入力座標/metric、固定契約hedge、
  強い解析/回帰対照、fallback、群CI、原価を一つの保存配列で調べられる。
- **Q-DMLを価格/Greek/速度標準器へ昇格しない。**
  H1の集約risk改善だけでは価格・spot・混合hedge・強い参照との精度/費用の改善にならない。
  小幅e2e savingも精度を合わせた採用根拠ではない。公開API・本番依存は追加しない。
- **次はRB-F05離散バリア。** 解析digitalでの速度優位を前提にせず、
  不連続性の正しい教師、MC/時間格子/学習誤差の分離を先に検証する。

| 工程 | 現在の状態 |
|---|---|
| 主学習・全方式の保存結果 | 30 NN＋4 ridge完了、fit budget failure0 |
| mainの独立fresh check | 完了。保存重み・数値・固定CF・safe・費用を再計算 |
| 最終NPZ保管・両コピー復元 | 23,498,066 bytes、primary/mirror各PASS |
| 本計時・raw/safe・総費用/H4 | 310測定・288対照を保存、計時/loader summaryをrawから検査 |
| artifact-only研究3図 | 実行済み・目視済み。H1/H2の別尺度、rate/spot分解、公平cache別の費用表示 |
| 独立最終レビュー | 承認済み、修正要求なし。固定合成研究の採否まで |
| 関連3suite | main統合後に全再実行し6919 passed / 6 skipped、334.02秒、終了コード0。初回4 FAILはAgg表示修正で解消 |
| 配布生成 | 通常make hull-report PASS、旧教材の追跡ファイルは不変 |
| commit後release / main反映 | `a25345e1`をmainへfast-forward統合。candidateと統合後mainの`verify_release.py --require-tracked`ともPASS |

## 成果物と再実行

reference.json/manifest.jsonと実行済みnotebookを正本directoryへ配置した。
最終NPZは23,498,066 bytesで20MiB上限を超えるため、既存C:/F:保管庫とsmall manifestを使う。
NPZはgit管理外。両コピーの独立復元を確認し、SHAは完全性だけに使う。
価格/Greekは許容差付き独立計算、計時/費用は保存raw標本と構成原価から再検査する。

fit時の6source digestはpre-fit commit `b5fc6e85`に一致し、金融4moduleも同commitと不変。
本計時sourceは実行中に保持した修正前snapshotを事後照合し、
自動捕捉されていなかったdigestを当時から保存していたとは主張しない。
loaderは自己digestを保存し、format前のsourceを保持した。
`provenance`でfit/timing/loading/validationを分ける。
計ったbundleはloading配列追加前の23,476,290 bytesで、SHA/bytesはloading.input_npzに保存。
現行checker/表示コードへの修正は再学習・再計時の成果と混同しない。
[計時source履歴](measurement_sources/README.md)を保持する。
| ファイル | 役割 |
|---|---|
| protocol.json | 固定契約/分割/学習/ショック/費用/統計規約 |
| build_reference.py | 主実験、保存、学習なしのcheck/measure、manifestからの復元 |
| reference_methods.py | 自作brentq・complex-step・密度積分・固定CFの独立参照 |
| replay.py | torch/learnerをimportしない保存重み推論・指標/CI再計算 |
| policy.py / diagnostics.py / benchmark.py | 安全wrapper、教師MC、raw標本付き計時 |
| measure_loading.py / costs.py | artifact-only読み込み計時、full-batch原価と償却 |
| reference.json / manifest.json | 全結果metadata・指標と保管庫の論理参照 |
| reference.npz（git管理外） | 全入力/教師/A/IDs/重み/予測/B/h/ショック/費用/診断・計時根拠 |
| build_notebook.py / quote_dml.ipynb | 学習を起動しないartifact-only研究3図 |
| REVIEW.md | 実装指摘/対応。最終成果レビューと区別 |
| hullkit/_quote_dml_teachers.py / _quote_dml_hedging.py | torch-freeの非公開金融計算 |
| deep_hedge_price/_quote_dml.py | 非公開CPU学習 |

WSLの対象checkout rootで共有venvを使う。以下は保存済み成果を使うコマンド。
既存のPROJECTS_ARTIFACT_STORE / PROJECTS_ARTIFACT_MIRRORを設定しておく。
root checkoutとworktreeの混同を避けるためPYTHONPATHを現在のcheckoutへ向ける。

~~~bash
cd /home/kazumasa/worktrees/johnhull-research-roadmap
export PYTHONPATH="$PWD/johnhull/hullkit/src:$PWD/deep_hedge_price/src:$PWD"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
quote_artifact_dir="$PWD/johnhull/research/RB-F07/quote_dml"

# 保存済み重み/配列の独立再計算。fitを起動しない。
# NPZがなければ同directoryのmanifest.jsonから復元する。
/home/kazumasa/projects/.venv/bin/python \
  johnhull/research/RB-F07/quote_dml/build_reference.py \
  --check --output "$quote_artifact_dir"

# 明示的な復元。manifestを持つ正本directoryへ復元する。
/home/kazumasa/projects/.venv/bin/python johnhull/scripts/evidence_store.py \
  restore "$quote_artifact_dir/manifest.json" --dest "$quote_artifact_dir"

# primary/mirrorを各々独立復元して比較する。
/home/kazumasa/projects/.venv/bin/python johnhull/scripts/evidence_store.py \
  verify "$quote_artifact_dir/manifest.json" \
  --work /tmp/quote-dml-vault-verify

# 保存済みモデルの再計時だけを行う。fitは起動しない。
/home/kazumasa/projects/.venv/bin/python \
  johnhull/research/RB-F07/quote_dml/build_reference.py \
  --measure --output "$quote_artifact_dir"

# 再計時後はloadと原価も更新。再学習はしない。
/home/kazumasa/projects/.venv/bin/python \
  johnhull/research/RB-F07/quote_dml/build_reference.py \
  --measure-loading --output "$quote_artifact_dir"

# 保存済みartifactから研究3図を再生成・実行する。fitは起動しない。
/home/kazumasa/projects/.venv/bin/python \
  johnhull/research/RB-F07/quote_dml/build_notebook.py

# API/保存境界のsmoke。別directoryへ2updatesのモデルを生成。
/home/kazumasa/projects/.venv/bin/python \
  johnhull/research/RB-F07/quote_dml/build_reference.py \
  --smoke --output /tmp/quote-dml-smoke

# 全学習を新たに作り直す場合だけ。既存本実験のcheckには不要。
/home/kazumasa/projects/.venv/bin/python \
  johnhull/research/RB-F07/quote_dml/build_reference.py \
  --refresh --output /tmp/quote-dml-regenerated
~~~

再学習した場合は新しいrunとして、環境・全seed・壁時計値を保存する。
既存結果の検査や計時追加のために30fitsを繰り返さない。
失敗したfit/較正では入力・理由・部分成果を保存し、30fits完遂扱いにしない。
再生成後のバイト完全一致や同一壁時計時間は要求しない。

## 到達範囲・制限・一次出典

本v1は決定論的単一曲線・正方較正・固定sigmaのGBM digital・合成データ・瞬間ショック比較。
価格参照にMC/時間格子/空間格子誤差はなく、
較正残差・浮動小数・学習/回帰近似を分けて扱う。
保存教師と同じ式を使う検査だけでなく、自作bootstrap・complex-step・積分・bumpを置く。

最小二乗/KKT・多曲線・確率金利・金利株式相関・rough教師・実市場の共同較正・
動的ヘッジ/取引費用付き戦略の成果ではない。
Q/Theta metricの接続だけで研究の新規性を主張しない。
全研究ロードマップの完了は、この比較実験の完了とは別。
次の既存研究はRB-F05離散バリア、その後F04/F08/F06。
公開API・本番利用・本編306節への追加受入は本研究で承認しない。

主要な一次出典と調査範囲は
[設計§2](../../../docs/superpowers/specs/2026-10-09-calibrated-quote-dml-design.md#2-一次資料の調査記録)に記録。
著者の速度比/学習結果は独立再現していない。

- Henrard, [Adjoint Algorithmic Differentiation: Calibration and Implicit Function Theorem](https://quant.opengamma.io/Adjoint-Algorithmic-Differentiation-OpenGamma.pdf), §2–3：較正残差からの総微分。
- Huge–Savine, [Differential Machine Learning v4](https://arxiv.org/html/2005.02347v4), §2・付録：価格と正しい微分教師、前処理、differential regression。
- Glasserman–Karmarkar, [Differential ML with a Difference v2](https://arxiv.org/html/2512.05301v2), §3：不連続payoffのPW biasとLRM/分散。既存S002に記録したGBM/密度式の不整合を保持し、教師は標準GBMから独立導出。
- OpenGamma Strata, [MarketQuoteSensitivityCalculator](https://strata.opengamma.io/apidocs/com/opengamma/strata/pricer/sensitivity/MarketQuoteSensitivityCalculator.html)：parameter→quote変換と較正Jacobian metadata。Strataとの数値照合は未実施。
