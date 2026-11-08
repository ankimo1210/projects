# 微分積分Ⅱ 第7〜8章の実装計画

更新日: 2026-11-07
状態: 実装・自動検証・Opusレビューと修正後確認まで完了。追加5章の実画面QAはツール制限により保留。

## 完了条件と範囲

二重積分と変数変換を追加し、微分積分Ⅱを8/8章にする。全体31章・入口込み32ページ、14実験、93演習。各章に問い・定義・証明・仮定と反例・一次出典付きコラム・3演習（2ヒントと完全解答）・3振り返り・静的代替を用意する。追加依存なし。一般変数変換定理は明示した借用とし、局所線形近似から一般定理が証明されたようには書かない。三重積分・ベクトル解析は対象外。

## 第7章 double-integrals

矩形のDarboux下和・上和を2軸の格子で定義し、共通細分・上限下限・epsilon基準を説明する。定数・線形性・単調性は有限和から導く。

閉矩形の連続関数の積分可能性を証明する。成分ごとのBolzano–Weierstrassによる逐次コンパクト性を使い、有界性と一様連続性を背理法で導出。セルの振動を一様に抑えて上和−下和≤eta×面積とする。

連続関数に限定した反復積分交換を証明する。F(x)=integral f(x,y)dy の連続性を一様連続性と積分上界で示し、格子のセル下限・上限で内側と外側の積分を挟んでDarbouxの差を0へ。一般の広義積分のFubiniには拡張しない。

単純領域 a≤x≤b, phi(x)≤y≤psi(x)（phi,psi連続）も扱う。境界グラフを含む格子セルの総面積が一様連続性から0へ向かうことを説明し、矩形上で0拡張した関数のRiemann可積分性と可変端点の反復積分公式につなぐ。境界上の1次元の有限個の跳びの影響も短く説明。三角形の領域図で積分順序の変更を実演する。

演習:
1. f=x+2y, [0,1]×[0,2]、両順で5、面積2、平均5/2。
2. 0≤y≤x≤1 上の x+y、両順で1/2、逆順は0≤y≤1, y≤x≤1。
3. 単位正方形の x²+y²。n等分で L=(n−1)(2n−1)/(3n²), U=(n+1)(2n+1)/(3n²), M=2/3−1/(6n²), I=2/3, U−L=2/n。n=2なら1/4,5/4,5/8。幅≤0.1にはn≥20。平方和の既存証明を参照。

コラムは降雨量×面積など、単位と重み付けの意味が見える一次資料を調査。歴史や事実はwebで確認し、自作例と区別する。

実験 host: multivariable-double-integral。n=1..32（初期4）、rule=lower/upper/midpoint（初期midpoint）。x²+y²のセル密度・代表点と、nに対する上下和/中点和/真値2/3の収束図。SVG2枚、同縮尺平面、長文はHTML。n=2中点和0.625が既知値。

## 第8章 change-of-variables

行列式の面積倍率と合成関数の値を結ぶ。T(u,v)=(2u+v,3v)、det=6のアフィン例から始める。線形写像でセル面積が正確に6倍である点と、連続関数の細分和の考えを示す。

一般の変数変換定理は借用と明記する。U開集合、T∈C¹、単射、det DT≠0、コンパクトJordan可測領域D⊂U、f連続（像領域の可測性・積分可能性も借用定理に含む）。絶対値が向きと面積を区別することを説明する。

極座標T(r,theta)=(r cos theta,r sin theta)のJacobian det=rを計算。r>0かつ角幅<2piの扇形で定理を適用。円板全体への拡張は原点と継ぎ目を除く領域r≥r0, epsilon≤theta≤2pi−epsilonで行い、除外部分を中心の正方形（面積4r0²）と継ぎ目の矩形（面積2R²epsilon、sin epsilon≤epsilon）で覆って有界積分の誤差を0へ。右辺もM(pi r0²+epsilon R²)で評価できる。円の面積公式をこの説明の前提に使わない。円板の面積pi R²、r²の積分pi R⁴/2へ。

演習:
1. 上記アフィン像の x+2y、変換後6(2u+7v)、答27、像面積6。
2. 単位円板のx²+y²、極座標でpi/2。原点・継ぎ目の扱いを参照。
3. D=([-1,-1/2]∪[1/2,1])×[0,1], T=(u²,v)。D上で|det|=2|u|≥1でも単射でない。像面積3/4、DでJacobian積分3/2、2重計数。原点の特異性とは区別。

コラムはOpenCV warpPolar等の一次資料。画像の画素値の再標本化に積分の密度変換が自動適用されるとは書かない。

実験 host: multivariable-polar。innerRadius=0..1.5 step0.1（初期0.5）、radialWidth=0.1..0.5 step0.1（初期0.5）、angle度−180..180 step5（初期0）、angularWidth度5..90 step5（初期90）。xy同縮尺[-2.2,2.2]、選択環状扇形と(r,theta)の矩形を比較。面積は厳密な扇形公式。dr*dthetaは座標領域の積でありxy面積と区別。比は中点半径。SVG2枚。

## 純粋数値API

新規 assets/multivariable-integration.js、UMD MathMultivariableIntegration。既存Math*を上書きしない。UIの有限な安全域を契約にし、巨大/非正規化数を広く扱う追加実装はしない。

rectangleSumState(n,rule): n整数1..32。rule lower/upper/midpoint。
返り値 n,rule,cellArea,sum,lower,upper,midpoint,integral(2/3),gap,cells。
cellsはi,j,x,y,density,weightedValue、i,j=0..n−1、代表点offset0/1/0.5、density=x²+y²、weighted=density/n²。セル加算と既知の公式を独立に検算。最大1024セル。

polarCellState({innerRadius,radialWidth,angleRad,angularWidth}): 上記範囲（角幅pi/36..pi/2）。
返り値入力4個、outerRadius,endAngle,midpointRadius,jacobianAtMidpoint,exactArea,coordinateProduct,areaRatio,corners。
corners順: (r0,theta0),(r1,theta0),(r1,theta1),(r0,theta1)をxyへ。
exactArea=(r1²−r0²)*角幅/2、coordinateProduct=dr*角幅、areaRatio=中点半径。
既知値: r0=.5,dr=.5,theta0=0,角幅pi/2 →面積3pi/16,積pi/4,比.75。
r0=0→pi/16,比.25。r0=1→5pi/16,比1.25。theta0=−pi/2で角の座標を検算。
型違いTypeError、範囲・不明ruleはRangeError。誤差のある浮動小数計算であることをUIに短く明示。

## 担当・検証順序

- 本文担当: 新規2HTMLのみ。既存章/共通メタデータは編集しない。
- 数値・UI担当: 新規integration.js、integration-experiments.js、integration.test.cjsのみ。TDDで既知値・全端点・不正入力・既存UMD共存。DOM境界確認後、rootがブラウザ表示を検証。
- root: catalog/build/test_buildのRED→登録→GREEN、共通README/STATUS、独立レビューの統合、Opus依頼と能動的完了確認。
- 中盤レビュー中の対象6ファイルは固定し、最後2章の実装を並行する。
- 最終32ページのリンク・アンカー・自己完結性・再生成一致、MathML/XML、演習/ヒント/解答/コラム/振り返りの数と整合、Node、Python、lintと空白検査。
- ローカルHTTPで新5章/5実験、幅390/320相当の表示、ライト/ダーク、キー操作、リセット、目次/前後移動。実施不能の項目は完了扱いにしない。
- Opus 5.5/max「win math」へ中盤と最終をレビュー依頼。終了をポーリングで確認し、指摘は原本と照合、修正、再検証・再確認して記録。
- 重要指摘が解消し全8章の完了条件を満たしてから全工程進捗表で報告する。コミット・公開はしない。

## 完了記録（2026-11-07）

全8章の実装・自動検証・独立数学レビュー・Opusの重要指摘対応と再確認まで完了。中盤の任意2点と最終の任意3点も全て反映し、未解決の重要指摘なし。追加5章の実画面QAだけはWindowsツールのURL判定不能で未実施。[現在の進捗と検証の限界](STATUS.md)と[レビュー対応](reviews/2026-11-07-multivariable-completion-response.md)を参照。

後続の[統合・試読](2026-11-07-reader-integration-plan.md)で、現行32頁のLinux実表示・操作とOpus独立画面確認まで完了。上記の実画面QA保留は、この計画の完了記録時点のWindowsツール制約を指す。現在の確認範囲は[STATUS](STATUS.md)を参照。
