# Ch32 Table32.3 一次資料による数値規約回収

更新: 2026-10-04。read-only investigation; repository/Git/public API/product tests/browser/D1 を変更・実行していない。スクラッチのみ。

## 結論

**Table32.3 全6行を印刷4桁の半単位 5e-5 内で再現した。** 価格targetへのfittingも許容差拡大も行っていない。著者配布の旧版 DerivaGem 2.01 (DG201) の終端期間を用いると、著者ブックの保存値との差は最大1.72e-11。

前pilotが使った sigma_R = sigma B(Delta)/Delta の修正は、この表の生成規約ではない。sigma=.01を無補正で使う Euler trinomial tree と、行使時点直後の**1日ノットを保存する終端期間**で全行が一致する。

3年expiryは1095日、9年bond maturityは3285日を保持する。curveの1096日/3287日をexpiry/bond maturityへ代入しない。

## 本文とソフトの規約

- Hull11e pp740-745: Rにrと同じSDEを仮定する有限刻み近似。R*はOU中心状態、mean increment=-a R* Delta、variance=sigma^2 Delta、spacing=sigma sqrt(3 Delta)。jmaxは0.184/(a Delta)より**strictに大きい最小整数**。
- Figure32.6/7の本文constant-step例はa=.1/sigma=.01/Delta=1、jmax=2。別曲線Table32.1で、alpha=(.03824,.05205,.062520499997)と印刷R値を再現できる。Figure32.6のcenter pm印刷値 .6666 は exact 2/3 の通常の四捨五入ではない; exact moment probabilitiesを計算し、印刷確率を演算入力にしない。
- DG201 `DataSetUp` は等間隔のuser treeをexpiryまで作り、expiryの後にrate datesを追加する。1096/365のノットはexpiry=3より後で、その次の3.5年bond dateまで.05年以上あるため保持される。3から最初の追加時点への距離は delta_star=1096/365-3=1/365。
- DG201 `BuildHWTree` は前のstepの間隔で次のrowのspacingを決める。このためexpiry rowのspacingは .01 sqrt(3*(3/N)) のまま。
- 最終rowにおけるRの期間は **delta_star**。最終alphaは sum_j Q[N,j] exp[-(alpha_N+j h) delta_star]=P0(3+delta_star) を解いて得る。expiryまでのQ propagationではDelta=3/Nを使用する。
- DG201 `AnalyticRate` は最終rowから次のrowまでのdelta_starを使用する。Eq32.15-17でも Bdelta=B(delta_star), Btilde=B(6)/Bdelta*delta_star, lnAtilde=ln(P0(9)/P0(3))-B(6)/Bdelta*ln(P0(3+delta_star)/P0(3))-.5*v3*B(6)*(B(6)-Bdelta)、v3=sigma^2*(1-exp(-2*a*3))/(2*a)。payoff=max(63-100*exp(lnAtilde-Btilde*R),0)、price=sum Q[N,j]*payoff。
- Qはdiscounted state prices。discountはparent-node R、exp(-R Delta)。最終ノードのanalytic ZCBをtree-consistent full-maturity bondと同一視しない。

これを全区間uniform Deltaと誤認すると最終alpha/analytic rate conversionが異なる。sigma_R修正はこの誤認による主差を近似的に消すが、残差を残していた。

## 再計算と著者ブックの比較

DG201 applicationsのシート名は `Trinomial Convergence`。A6:B20がTable32.2のcurve。入力はE6=3, E7=9, E8=0(coupon), E9=100, E10=2, E12=0(put), E15=.01, E16=.1, E17=63, E18=0。D列がsteps、E列がtree、F列がanalytic。

| N | 本文印刷 | independent scratch | 著者cached | 差/印刷 | 差/cached | cached cell |
|---:|---:|---:|---:|---:|---:|---|
| 10 | 1.8468 | 1.846840135541 | 1.846840135523 | +4.014e-05 | +1.715e-11 | E29 |
| 30 | 1.8172 | 1.817227104825 | 1.817227104838 | +2.710e-05 | -1.262e-11 | E49 |
| 50 | 1.8057 | 1.805681323290 | 1.805681323277 | -1.868e-05 | +1.296e-11 | E69 |
| 100 | 1.8128 | 1.812768730069 | 1.812768730067 | -3.127e-05 | +2.047e-12 | E95 |
| 200 | 1.8090 | 1.808974826171 | 1.808974826166 | -2.517e-05 | +4.335e-12 | E96 |
| 500 | 1.8091 | 1.809081553064 | 1.809081553079 | -1.845e-05 | -1.578e-11 | E99 |

全行でabs(差/印刷)<=5e-5。max curve-fit residual=4.45e-16。解析式(ndtr)のput=1.8092941675909984、独立forward-measure Gaussian quadrature=1.8092941675909997。

著者cached analytic=1.8092918769951747。DG201 `Util_NormDist.n_cdf` の多項式近似を再計算すると1.8092918769951858。約2.29e-6の差はCDF近似から説明でき、いずれも本文1.8093と整合する。

## DG201とDG400を区別する

DG201 applicationsのシートは旧版7e Example30.1/Problem30.26の名称を残すが、入力と全6価格は11e Table32.3と一致する。cached値との機械精度近傍の照合はこの旧版アルゴリズムを表fixtureの一次証拠として支持する。

現行DG400の`DataSetUp`はexpiry直後.015年未満のknotをexpiryへ移動する。1096日のknotが消え、semiannual bond datesを含めると次の3.5年まで.1年刻みを挿入し、terminal delta=.1。これはDG201のdelta=1/365と異なる。sigma_R補正なしのDG400 geometry/terminal-deltaを同じ数式に適用すると(N10=1.8529932990,N30=1.8234351875,N50=1.8118982215,N100=1.8187549400,N200=1.8150860186,N500=1.8150260960)。後ろ2行は公開TreeBondOptのnsteps上限100を外した数学スクラッチであり、DG400 APIの実行結果として表現しない。

DG400の再計算は著者ブック内で実行した証拠ではない。DG201数値pinにDG400のdate-removal規約を混ぜない。普遍的なevent treeは元のcurve datesを保持する方針とし、この旧版の表再現fixtureと別の受入基準を持つ。

## VBAへの位置証拠

抽出VBAは`/tmp/p3-ch32-DG201-functions-vba.txt`。番号は結合抽出ファイルの1-based lineで、ブック内部行番号ではない。

- `Calc_IR_Tree.MakeHW_Tree`:6454, constant a/sigma selection:6512-6517。
- `Calc_IR_Tree.DataSetUp`:6524; user-range条件`T<=lastUserDate`:6588; expiryより後のrate-date merging閾値.05:6610; rate-calculation step追加:6647。
- `Calc_IR_Tree.BuildHWTree`:6729; spacing:6763-6764。
- `Calc_IR_Tree.TreeAdvance`:6773; variance=sig^2*dt:6800; Euler expected rate:6805; closest-center/moment probabilities:6807 onward。
- `Calc_IR_Tree.TreeAdjust`:6902; source uses Newton alpha fit; normal-model closed logarithm in scratch is equivalent。
- `Calc_IR_Tree.aval_tree`:7258; `bval_tree`:7296; `AnalyticRate`:7313 (delta from next row:7329; analytic conversion:7334)。
- `Util_NormDist.n_cdf`:1297。

DG400 extracted `/tmp/p3-ch32-DG400-functions-vba.txt`: `TreeBondOpt`上限100:4729; `DataSetUp`:8806; expiry直後knot removal:8883; `BuildHWTree`:9011; `TreeAdvance`:9041; `TreeAdjust`:9158; `AnalyticRate`:8738。

## 一次資料、版、hash

すべて著者公式アーカイブの固定commit `9b8dbfe37661dbd3de65d3a1489dc1297e840de7` から、必要ファイルだけを読み取り取得した。

- [DG201 functions](https://github.com/rotmanfinhub/john-hull-textbook-resources/blob/9b8dbfe37661dbd3de65d3a1489dc1297e840de7/Options%2C%20Futures%2C%20and%20Other%20Derivatives%2C%2011th%20Edition/DerivaGem%20Software/Earlier%20releases%20and%20corrections/2.01/DG201%20functions.xls)
- [DG201 applications](https://github.com/rotmanfinhub/john-hull-textbook-resources/blob/9b8dbfe37661dbd3de65d3a1489dc1297e840de7/Options%2C%20Futures%2C%20and%20Other%20Derivatives%2C%2011th%20Edition/DerivaGem%20Software/Earlier%20releases%20and%20corrections/2.01/DG201%20applications.xls)
- [DG400 functions](https://github.com/rotmanfinhub/john-hull-textbook-resources/blob/9b8dbfe37661dbd3de65d3a1489dc1297e840de7/Options%2C%20Futures%2C%20and%20Other%20Derivatives%2C%2011th%20Edition/DerivaGem%20Software/DG400%20functions.xls)
- [TN16](https://github.com/rotmanfinhub/john-hull-textbook-resources/blob/9b8dbfe37661dbd3de65d3a1489dc1297e840de7/Options%2C%20Futures%2C%20and%20Other%20Derivatives%2C%2011th%20Edition/Technical%20Notes/TechnicalNote16.pdf)
- [TN9](https://github.com/rotmanfinhub/john-hull-textbook-resources/blob/9b8dbfe37661dbd3de65d3a1489dc1297e840de7/Options%2C%20Futures%2C%20and%20Other%20Derivatives%2C%2011th%20Edition/Technical%20Notes/TechnicalNote9.pdf)


| local file | SHA-256 |
|---|---|
| /tmp/p3-ch32-DG201-functions.xls | 273ebb1a0814724e962bd4e10bd643c73742f121b7703f813638204e3dee4493 |
| /tmp/p3-ch32-DG201-applications.xls | cb761768d4654a913c1d140f46107680b99be5ff0d3076d678c835585da8562d |
| /tmp/p3-ch32-DG400-functions.xls | 00dfde65a46dbae950f7cdcfb99dad66a522062e13e3df1da7ba3d3bb4ccc930 |
| /tmp/p3-ch32-TN16.pdf | f3dcb0a5d26d7ab43b69d797b5fea81f28355ccbd20f5fe1535cd2f1ee3607b7 |
| /tmp/p3-ch32-TN9.pdf | 9f9bdf6783248a280cab862236b0cadd06e04676435df362c25e8577e83843bb |

DG201 Git blob SHA (not SHA-256): functions=9d412c83b5221fd82bb0dae0a7f60873c552a896; applications=434f2e4a09ac72a6c4dc4a2fa6e723d551b4c651。

TN16はvariable-step/parameter treeをTN9へ委譲し、中心状態のtreeの後で初期curveをfitする手順を述べる。TN9はnearest expected child centerと、M=m Delta/V=sigma^2 Deltaからfirst/second momentsを一致させる分枝式を与える。TN16自体がexact-OU momentsを指定するわけではない。ここはconstant Euler fixtureの根拠と区別する。

## 出力と未完

- `/tmp/p3-ch32-table323.py`: primary-source-based deterministic numerical reproduction; target prices are verification-only。run: `/home/kazumasa/projects/.venv/bin/python /tmp/p3-ch32-table323.py`。
- `/tmp/p3-ch32-table323.json`: all6prices, source hashes, precision comparisons, independent analytic quadrature, Figure32.6/7 scratch, old-pilot/current-software variants。
- `/tmp/p3-ch32-table323-notes.md`:この報告。
- 原典book text extract `/tmp/p3-ch32-primary-pages.txt`、TN16/TN9 extracts `/tmp/p3-ch32-TN16.txt` `/tmp/p3-ch32-TN9.txt` は調査用でrepoへコピーしない。

**Table32.3 numerical source/pin blockerは解決。** Figure32.9のBK全bond/option-node、100-step価格、LMM/flexicap、P3 product implementation/portal表示は本調査の受入対象ではなく、未完のまま保持する。
