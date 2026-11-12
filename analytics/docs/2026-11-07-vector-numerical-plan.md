# ベクトル解析・数値解析：並行実装とOpusレビュー計画

> **For agentic workers:** superpowers:subagent-driven-development、TDD、独立数学/表示レビューを使用。ユーザーは既存と同じHTMLで実装→Opusレビュー→統合/内部試読、および2科目の並行進行を明示した。通常の設計判断は担当者/rootで行い、既存承認を再確認しない。

**Goal:** 空間の局所/境界の関係と、近似解を信用する条件を理解できる各10章を完成させる。
**Architecture:** 既存7科目61章を保持し、vector/numericalの各10原稿と純粋JS/操作UIを加える。共有catalog/build/template/QAへの統合はrootが一元管理。
**Tech Stack:** 標準Python、HTML/MathML/inline SVG/native tables、plain classic JS、Node built-in tests、既存Chromium/Playwright。新依存なし。
**Spec:** 本書の設計、およびユーザーの動機/なぜ役に立つ/コラム/図表重視の既存指示。

## 共通方針と範囲

高校既習〜大学基礎。各章は問い→定義→短い証明→条件/反例→接続、任意コラム1、演習3（各2ヒントと解答）、振り返り3。概念図2以上/比較表1以上を概念の近くへ。院生向け理論・一般多様体・大規模数値ライブラリ・既存本の全面改稿は含めない。既存線形代数/ODE/Fourier/統計4入口は維持し、必修にはしない。

既存61章、JS19、共通CSS、serve.py、先行ユーザー変更を保持。既存checkoutを継続し、依存追加・commit/push・公開・worktree切替なし。原本は科目/担当ごとに分離する。基準hashは _data/math-foundations/vector-numerical-2026-11-07/baseline.json。

SVGは360viewBox/22px以上/token色/固有title/desc/ARIA/data-visual。マーカー付き矢印は1path1subpath、方向/位置/縮尺を検算。表はnative caption/th scope/focuswrapper/data-visual、短い式のみtable-math、文章normal。文章列が狭すぎる場合に対象tableだけmin-width:30remを使用。NoJSで本文・図表・演習解答を読める。

## ベクトル解析の10章

| 章 | slug | 内容と証明境界 |
|---|---|---|
| 01 | vector-fields | 3成分内積/外積、右手系・面積恒等式、場と流線/粒子位置の区別 |
| 02 | vector-curves | 区分C¹、速度と速度非零の単位接線、弧長/スカラー線積分 |
| 03 | vector-line-integrals | F·dr、向きと再param、仕事。vector-work |
| 04 | vector-potentials | 勾配FTC/経路独立、C¹星形領域/偏微分対称性によるpotentialを補題込みで証明、穴反例 |
| 05 | vector-green | 矩形をFTC/Fubiniで証明、一般曲線境界/有限穴版は条件を明記して借用 |
| 06 | vector-div-curl | div/curlの座標定義、局所の意味、C²でcurl grad/div curl、05/04との接続 |
| 07 | vector-surfaces | 正則patch/単射と重複計数、面積と外積、向き/座標変更、球の継ぎ目 |
| 08 | vector-flux | F·n dS、面積との差、向き/投影。vector-flux |
| 09 | vector-gauss | 箱の三重Riemann和/連続箱Fubiniの借用を導入、箱Gaussを証明、一般閉領域は借用/特異点条件 |
| 10 | vector-stokes | 一枚C²patchをGreen/連鎖律で導出、連続単位法線を選べる一般C²曲面への拡張を明示借用、誘導境界・固定境界の面変更。vector-stokes |

04では未導入curlを条件にせず∂iFj=∂jFiを使い06へ接続。積分内の微分は連続偏微分の一様評価から補題を示す。06のdivは08の一般面積分から定義しない。07の正則patchはru×rv≠0、内部単射、有限patchの境界共有を明示。球の極/継ぎ目を正則と偽らない。09は三重積分を未導入で使わず、一般有界領域は箱への0拡張で定め、その可積分性を一般Gaussとともに明示借用する。Greenの一般Dも既存の二重積分の0拡張を使う。Stokesは連続単位法線を選べるC²曲面を十分条件とし、Gaussの内境界は空洞側を向く。一般Green/Gauss/Stokesは閉領域/曲面を含む開近傍でのC¹、境界の滑らかさと向きを明記し、相殺図だけで一般版の証明を装わない。

実装者の独立監査で順序を確認した。原著教科書/講義資料の条件を確認（2026-11-07）：[OpenStax Green](https://openstax.org/books/calculus-volume-3/pages/6-4-greens-theorem)、[Stokes](https://openstax.org/books/calculus-volume-3/pages/6-7-stokes-theorem)、[Gauss](https://openstax.org/books/calculus-volume-3/pages/6-8-the-divergence-theorem)、[MIT星形領域](https://ocw.mit.edu/courses/18-022-calculus-of-several-variables-fall-2010/317ce269a2203c2c151936d8c554a1bc_MIT18_022F10_l_29.pdf)。本文と図は自作する。

## 数値解析の10章

| 章 | slug | 内容と条件 |
|---|---|---|
| 01 | numerical-errors | 絶対/相対誤差、表示桁、丸めと打切りの区別 |
| 02 | numerical-conditioning | 問題の感度、相対条件数、0近傍の注意、安定性との区別 |
| 03 | numerical-bisection | 連続/符号変化/区間保証と幅、numerical-root |
| 04 | numerical-newton | 接線反復、局所条件、微分0/周期/非収束、03と比較 |
| 05 | numerical-linear-systems | 消去/pivot、残差と解誤差、小さい行列、既存線形代数へ |
| 06 | numerical-interpolation | 補間と近似、節点、誤差の仮定と過剰振動 |
| 07 | numerical-differentiation | 前進/中心差分、打切りと丸めの競合、numerical-difference |
| 08 | numerical-quadrature | 中点/台形、滑らかさと誤差、有限値の比較と保証の違い |
| 09 | numerical-ode | y′=λyとEuler、有限時間収束と絶対安定性、numerical-ode |
| 10 | numerical-reliability | 残差/刻み変更/独立手法/条件の確認と検算の限界 |

実数の数学的上界、浮動小数丸めモデル、実際のJS計算結果を区別。Math.expの丸め尺度を処理系保証の厳密上界と呼ばない。Newton初期値の入力範囲と反復値の範囲を区別。Eulerの負λでも|1+hλ|>1なら不安定、λ>0の真の増大を数値不安定と混同しない。既存ODE本の修了は不要。

## 新6実験の契約

各科目はfrozen MathVector/MathNumerical＋Node exportsとclassic UI。入力の型/有限範囲を検証し、不定義はnull＋理由で0と区別。ネイティブcontrols/reset、data-key/data-value/data-raw/data-raw-value、正常labError=false/予期せぬ例外true、意図した停止/定義域と分ける。root QAは独立式/境界/キー/reset/NoJSを確認する。

- vector-work: workState({field:gradient|rotation,path:straight|parabola|x-first|y-first,orientation:±1,n:16..128/16})。gradient=(y,x)、rotation=(-y,x)、(0,0)→(1,1)。exact gradient全1、rotation直線0/放物線1/3/x先1/y先−1、向きで符号反転。各smoothpiece中点n、放物線numericはgradient 1−1/(4n²)、rotation 1/3−1/(12n²)。
- vector-flux: fluxState({a,b:−1..1,c:−2..2,orientation:±1})。r=(u,v,au+bv),[-1,1]²、F=(0,0,c)。area=4sqrt(1+a²+b²)、normal=±(-a,-b,1)/norm、flux=±4c。面積は正、fluxは符号/0を持つ。
- vector-stokes: stokesState({height:−1.5..1.5,alpha:−1..1,orientation:±1,n:8..128/8})。graph z=h(1−r²)、F=(-y(1+αr²)/2,x(1+αr²)/2,0)、curl_z=1+2αr²。両exactは±π(1+α)、径方向中点numeric=±(π(1+α)−πα/(2n²))。高さを変えても境界は単位円z=0。α=−1でexact0/残差非0を区別。
- numerical-root: rootState({function:square|cycle,method:bisection|newton,x0:−2..2,steps:0..12整数})。square=x²−2 bracket[0,2]、cycle=x³−2x+2 bracket[-2,0]。二分幅2/2^steps、Newton cycle0↔1/微分0/停止理由を独立確認。
- numerical-difference: differenceState({x:−2..2,exponent:0..16整数})、h=10^−exponent。expの前進/中心差商、真値/実誤差/打切り上界と丸めモデルを区別。独立expm1式で打切り、機械解像度で観察を確認。
- numerical-ode: odeState({lambda:−4..2,y0:−2..2,n:1..64整数})、T=2、h=2/n。Euler q=1+hλ、k段はy0 q^k、厳密y0 exp(λkh)。符号/0/|q|境界/正λの真の成長と数値安定性の区別。

## 担当とファイル

- vector-author: 新01〜04/07〜08の6HTMLのみ。
- vector-labs: 新assets/vector.js,vector-experiments.js,tests/vector.test.cjsのみ。
- numerical-book: 新numerical10HTMLとassets/numerical.js,numerical-experiments.js,tests/numerical.test.cjsのみ。
- root: 新vector05/06/09/10、catalog/build/template/tests/test_build.py/tools/browser_qa.cjs、README/STATUS/本計画/reviews。
- 仕上がった担当から独立レビューを分担。Opusは既存win math/maxへ設計・実装・必要な差分レビューを依頼し能動poll、待つ間に独立作業を進める。自分のbrowser操作可、一時browser/serverだけ終了、ユーザー8765維持。

## Tasks / progress

- [x] Task1: 現況hash、2科目の章順/証明境界/API、担当分離。
- [x] Task2: ベクトル10章/3実験、数学/図表/演習の自己確認。
- [x] Task3: 数値10章/3実験、数学/誤差/演習の自己確認。
- [x] Task4: 新20ページ/6labのportable期待を先にRED、catalog/build/template統合→82ページ/31labsでGREEN。
- [x] Task5: 各科目の独立数学/視覚レビューとOpusレビュー、重要修正/差分再確認。
- [x] Task6: 全82ページ×3幅×明暗=492状態、NoJS82、31実験、243演習/486ヒント/243解答、図表/表スクロール/既存4入口を検証。
- [x] Task7: 現在版source/pages hashと検証対応、サイズ/README/STATUS/完了記録を確定。

TDDは新API/portable期待で実際のRED→GREENを記録する。通常本文変更の実装を鏡写しにするだけのテストは作らず、数学レビュー/HTML/XML/実描画で確認する。

## Review Focus

1. orientation/法線/誘導境界、スカラー線積分と仕事の符号差。
2. 星形/穴/正則性、Green/Gauss/Stokes一般版の借用と特異点/閉領域の条件。
3. crossとpatch、三重積分/Fubiniの導入順。曲面を一枚で覆えると偽らない。
4. 打切り/丸め/条件数/安定性、残差と解誤差、モデル目安と保証の違い。
5. Newton非収束/分母0、二分保証の条件、Euler安定境界、有限実験と一般証明。

出力見積：82HTML×約250KiB≒20MiB、QA/図表/レビュー証拠は同1root40MiB前後。巨大配列なし、retryは同名上書き、失敗は要約とhashだけ。30GiBには遠く及ばず、実測duを最終記録する。

## Opus設計レビュー対応

重要1件：一般領域の三重積分を箱への0拡張で定義し、可積分性/境界体積0を一般Gaussとともに借用と明記。GreenのDも既存0拡張へ参照。Stokesの連続単位法線/Gaussの空洞向きは原稿で明記する。数値側はNewton局所収束/残差と解誤差/補間観察/Euler定数λ収束/丸めモデルの前提と処理系近似を担当が具体化する。IEEE/JS関数の仕様に関するレビュー提言も一次仕様へ照合し、無条件には採用しない。

数値解析の丸めの設計判断：実機のIEEE定数の説明を必修化せず、有効数字4桁の自作十進モデルで誤差と後退安定性の意味を自給する。実験の実刻み(x+h)−xとx−(x−h)を表示し、Math.exp/expm1や丸め尺度は処理系依存/目安と明示。05の残差は∞ノルムの一般不等式を各行の三角不等式から示し、pivotの効果は具体例に限る。09の収束は定数λに限定しlogの積分評価からO(h)を導く。

## 完了

2026-11-07。20章/40SVG/20表/6実験を追加し9科目81章へ。独立数学/視覚レビュー、Opus最終差分承認、Python21/Node98、修正後492状態/19385checks失敗0、NoJS82/全31実験を確認。32原本/82HTML hash照合、旧61原稿/19JS/CSS/serve保持、既存4入口維持。初回のHTML比較記号欠落は17箇所を修正し、文字をパース後に確認する回帰テストとREADME規則を追加。[完了記録](reviews/2026-11-07-vector-numerical-completion-response.md)。
