# 線形代数本編：統合・補強の実装計画

> **For agentic workers:** superpowers:subagent-driven-development / 独立レビュー / TDDを使用。ユーザーは同工程での並行実装を明示承認済み。通常の設計判断はrootが行い、再承認やcommitで停止しない。

**Goal:** 既存の橋4章を生かし、連立方程式・座標・直交・固有構造・情報圧縮を結ぶ大学基礎10章を完成する。
**Architecture:** 既存10科目91章/34実験へlinear-core10章/3実験を追加。本文2担当、数学UI1担当、rootが共有統合とOpus/全体QAを管理。初回は最適化の19固定原本/92生成物のレビュー記録まで共有統合を待った。現在は追加の全科目品質要件に従い、102版へ統合済み（下記の更新された順序）。
**Tech Stack:** 標準Python、HTML/MathML/inline SVG/native tables、plain classic JS、Node builtin tests、既存Playwright/Chromium。新依存なし。
**Spec:** ユーザーの「数学の気持ち」「なぜ役立ち面白いか」「図表とコラム」の既存方針と本書の章/証明/API契約。

## 意図・範囲・制約

数学の言葉/集合写像/証明と橋4章の公理・基底・rank-nullity・2×2detを必要箇所だけリンクする。微積分・最適化・確率・旧大型本修了は必修にしない。旧13notebookは読み取り資料として独自例を再構成し、旧本と生成物を変更せず入口を維持。全文移植、Jordan標準形、テンソル、大規模反復solver、測度/PCA統計論、量子を必須にしない。

各章：動機→定義→短い正しい証明→条件/反例→接続、概念SVG2以上、比較表1、任意コラム1、演習3（各2ヒント/解答）、振り返り3。実数有限次元を基本とし複素固有は任意の入口。図360viewBox/文字22px以上/token色/title・desc・ARIA/data-visual、矢印1path1subpath、定量図の共通尺度/値は正確にする。表はcaption/th scope/focuswrapper、短式のみtable-math、長文を囲わず適切に折返す。長表だけmin-width30rem。数式テキストの比較記号はHTML escape。NoJSでも全本文/図表/演習を読む。既存CSS/25JS/91原稿/serveと先行ユーザー変更は保持。新依存/公開/commit/push/worktree切替なし。

## 10章と証明境界

| 章 | slug | 内容と証明 |
|---|---|---|
| 01 | linear-systems | Ax=bを列の組合せ/行の条件から読む。配合自作例A=[[2,1],[1,3]],b=(8,9),x=(3,2)。一意/無し/無限、特殊解＋核は03へ |
| 02 | linear-elimination | 可逆な基本行操作は解集合を保存、消去/pivot/矛盾行/自由変数。積/合成は橋を復習。linear-core-map |
| 03 | linear-kernel-image | kernel/image/rank、rank-nullityは既存橋の証明へ戻り具体適用。Ax=bの全解=xp+ker Aを証明。直交した四基本空間は05以降へ |
| 04 | linear-basis-change | x=Pz、出力基底も異なればQ⁻¹AP、同空間の相似P⁻¹AP。行基本操作と基底変更を区別。可逆Pの条件 |
| 05 | linear-orthogonality | 内積/norm、平方完成からCauchy–Schwarz、Pythagoras、Gram–Schmidtで0を割らない、列独立時QR。直交は距離保存/鏡映も含む |
| 06 | linear-least-squares | 部分空間の直交基底から射影存在/一意を証明、残差直交⇔正規方程式、列独立時AᵀA可逆。予測一意/係数非一意、四基本空間への接続。linear-core-least-squares |
| 07 | linear-eigenvalues | Av=λv,v≠0、負λ反転/λ0で像0、反復は各固有成分から判断。回転の実固有なし、優勢固有値だけで全初期値発散としない |
| 08 | linear-diagonalization | n独立固有vector⇔P⁻¹AP=D、異なる固有値の独立を短証明、重複でも可/不可（Iとshear）。対角化と直交対角化を区別 |
| 09 | linear-symmetric | 実2×2対称の実根/異固有値直交/重根scalarから直交対角化を直接証明、一般n有限実スペクトルのみ借用。二次形式の符号/正定値と最適化への任意接続。linear-core-spectral |
| 10 | linear-svd | 2×2実AのAᵀA半正定値からV、正σのu=Av/σ、σ0は割らず直交補完してSVD構成。一般m×n完成定理は借用。σ非負/鏡映/重複の非一意。2×2のrank≤1最良Frobenius誤差σ₂は直証明（unit v∈ker Bを使い||A−B||F≥||(A−B)v||=||Av||≥σ₂、truncationで達成）、一般Eckart–Youngを必修にしない |

非対称行列にスペクトル定理を使わない。SVDの特異値はsort(abs eigenvalues)ではなく一般にはsqrt eigenvalues(AᵀA)；対称labだけ前者と一致。重複特異値のベクトル選択、σ1=σ2>0でrank1最良近似非一意、σ2=0で元行列自身がrank≤1という区別。低ランク誤差のnorm種類を明記。旧本のPCA標準化/ノイズ等の断定は継承しない。

独立設計監査：map289 exact / LS44217 rational / spectral5733、最大固有残差8.88e−16。一次資料：[MIT最小二乗](https://ocw.mit.edu/courses/18-06sc-linear-algebra-fall-2011/198bde3a6536b62989b6cc09495575c1_MIT18_06SCF11_Ses2.3sum.pdf)、[実対称](https://ocw.mit.edu/courses/18-06sc-linear-algebra-fall-2011/804ab1e53134741d2044d241b50a285e_MIT18_06SCF11_Ses3.1sum.pdf)、[SVD](https://ocw.mit.edu/courses/18-06sc-linear-algebra-fall-2011/d273f75ee2552a5c3c35ccab37e5edce_MIT18_06SCF11_Ses3.5sum.pdf)。旧教材は条件を補って独自日本語で再構成する。

## 新3実験の固定契約

新assets/linear-core.js（MathLinearCore frozen UMD/Node）/linear-core-experiments.js（classic UI）、tests/linear-core.test.cjs。既存linear.jsやoptimization.jsは変更しない。UI data-labは下記、data-key native controls / data-value / data-raw / data-raw-value readouts / resetexact / 重複init抑止。正常labError=false、予期しない例外true、nullと0を区別。有限実験を一般証明と呼ばない。機械計算の非零残差を表示丸めだけで厳密0と断定しない。

### 02 linear-core-map：mapState({s,t,x,y,b1,b2})

s,t,x,y,b1,b2は[-2,2]の1/4格子（4v整数をAPIで検証）、defaults s=.5,t=1,x=1,y=1,b1=1,b2=1。A=[[1,t],[s,1]]、columns=[[1,s],[t,1]]、transformed=[x+t*y,s*x+y]、determinant=1−st。1/4格子なのでdetはbinaryexact、epsでrankを判定しない。diag1なのでrank0は無いと明記。
- rank=det≠0なら2、そうでなければ1。
- solutionKind=unique（det非零）/infinite（det0かつb2=s*b1）/none。
- representativeSolution=uniqueなら[(b1−t*b2)/det,(b2−s*b1)/det]、infiniteなら[b1,0]、noneならnull。
- kernelDirection=rank1なら[−t,1]、rank2ならnull。infiniteの全解=representativeSolution+u*kernelDirection。
- 戻り値は入力も含み、matrix/columns/transformed/determinant/rank/solutionKind/representativeSolution/kernelDirectionを公開。
図は二列と単位正方形の像、入力矢印の像とtarget bを同じ尺度で描く。負det/列が重なるrank1/解なし/無限を示す。ラベル衝突は図外の凡例も利用。

### 06 linear-core-least-squares：leastSquaresState({y0,y1,y2,deltaA,deltaB})

y0,y1,y2は[-2,2]、deltaA/deltaBは[-1,1]、いずれも1/4格子（4v整数）。defaults=(1,0,2,0,0)。観測x=[−1,0,1]でa+bxをfitする。
- a=(y0+y1+y2)/3、b=(y2−y0)/2。fitted=[a−b,a,a+b]、residual=observed−fitted。
- normalResiduals=[Σr,−r0+r2]、sse=Σr²、observedNormSquared/fitNormSquared、pythagoreanResidual=observedNormSquared−fitNormSquared−sse。
- candidateA=a+deltaA,candidateB=b+deltaB,candidateFittedとcandidateSSEは直接評価。excess=3deltaA²+2deltaB²は恒等式から安定計算。
- 戻り値は入力/observed/a/b/fitted/residual/normalResiduals/sse/observedNormSquared/fitNormSquared/pythagoreanResidual/candidateA/candidateB/candidateFitted/candidateSSE/excess。
- 独立oracleはd=y0−2y1+y2としてresidual=[d/6,−d/3,d/6]、最適SSE=d²/6。入力値を調整してcollinear/非collinear/zeroを検査する。
- 元の2D散布図では縦残差を描く。これは2D直線の法線方向ではなく、3成分データ空間での直交射影であると明記。残差三成分の棒図/表、2本の内積とSSE差で示し、不要な立体を避ける。

### 09 linear-core-spectral：spectralState({lambda1,lambda2,theta,x,y})

lambda1,lambda2は[-2,3]、x,yは[-2,2]の1/4格子、thetaは0..180の15度格子。defaults=(2,.5,30,1,1)。Q=R(theta)、A=Q diag(lambda1,lambda2) Qᵀ。0/90/180度のsin/cosは正確な値にする。他は通常浮動小数。
- matrixはmid=(λ1+λ2)/2,half=(λ1−λ2)/2を用い、a=mid+half*cos(2θ),d=mid−half*cos(2θ),off=half*sin(2θ)と生成して重複λで正確なscalarを保つ。2θの四分円も正確なsin/cosにする。eigenvalues=[lambda1,lambda2]（構成ラベル順、並べ替えない）/directions=[[cos,sin],[−sin,cos]]/transformed=A[x,y]/quadraticForm=[x,y]·transformed。
- trace=lambda1+lambda2,determinant=lambda1*lambda2,rank=非零lambdaの数（モデルの数学的値、行列丸めから推定しない）。
- formKind=positive-definite/negative-definite/indefinite/positive-semidefinite/negative-semidefinite/zero。zeroは両方0、semidefiniteは非零片方と0。
- repeatedEigenvalue=lambda1===lambda2、eigenDirectionsUnique=!repeatedEigenvalue（方向は符号を除く直線としての話）。
- singularValues=[abs lambdaを降順]、singularDirectionsUnique=abs(lambda1)!==abs(lambda2)。λ1=−λ2≠0ではeigendirは区別できるがsingulardirは非一意。
- 戻り値は入力と上記全て。単位円の像/固有方向・入力の像/値を表示。負λの反転/0の潰れ/重根では描いた基底が一例でしかないことを明記。有限polylineは模式近似で定理の証明としない。

## 担当と統合

A新01〜05のみ、B新06〜10のみ、C新2JS/testのみ。原稿のlab placeholderはdata-labだけでJSが構築。rootのみcatalog bookid linear-core/上記10slug/章順/3labs、build.py、template、test_build.py、tools/browser_qa.cjs、README、STATUS、analytics portalを統合。新共有CSSやserve変更は原則不要。最適化が固定解除されるまで共有ファイルと既存siteを触らない。各担当は必要なら自分だけの小HTMLを_data/linear-core-...内で生成し、専用server/browserだけ終了する。ユーザー8765はrootだけ更新。

## Tasks / progress

- [x] Task1：旧13冊/橋4章のmarkdown原本、重複/不足/誤移植リスクを独立監査。既存91原稿/25JS baseline。
- [x] Task2：本文10章/20図10表/30演習60ヒント30解答/10column30reflectionを作成、数学/図表selfcheck。
- [x] Task3：独立closedform oracleで新3APIの意味あるテストRED→GREEN。map det0で3解分類、LS零残差と不一致、spectral負/0/重根/±λ。
- [x] Task4：最適化承認後にportable期待102ページ/37labsを先にRED確認→共有実装→11科目101章/102ページへGREEN。
- [x] Task5：作者以外の数学/API/UI・全30図表教育レビューとOpus設計/実装/差分確認。最終指定の対称行列限定句を反映し、再レビュー不要の承認条件を満たした。
- [x] Task6：全102ページ×3幅×明暗=612状態、NoJS102/37labs/303exercise606hint303answer、旧4入口、全新図表/解答の内部試読。
- [x] Task7：source/生成HTML hash/件数/サイズ/テスト/QA実応答を照合しSTATUS/README/完了記録を更新。

Python unittest discover22件、Node --test全suite111件、ruff既存4py/JSsyntax/QA self-test。source→DOM全文と未知HTML要素0、承認済み全科目改修の差分と、保護16原本の不変を確認。生成物は再生成一致。目安102HTML約30MiB、証拠約50MiB。30GiBに遠く、最終du実測。出力は_data/math-foundations/linear-core-2026-11-07/に集約、不要な大配列なし。

## Review Focus

1. 基底/行操作/線形写像を区別し、Q⁻¹APの左右と相似の必要条件を誤らない。
2. 解なし/無限/一意と核像次元、列独立無しで(AᵀA)⁻¹を使わない。係数一意と予測一意は別。
3. Gram–Schmidt/σ0で0を割らず、重複固有/特異値で方向の一意性を主張しない。
4. 対称/一般行列、固有値/特異値、符号/非負、鏡映/回転、反復の全初期値/特殊軌道を区別。
5. 実験の射影が3成分空間であること、SSE/座標距離/norm種類、計算残差/厳密0を明記。

後続候補は常微分方程式の統合・接続。今回は新ODE実装は含めない。

## 追加品質ゲート（2026-11-08）

[図表メッセージ強化計画](2026-11-08-figure-message-quality-plan.md)を完成条件に追加。各図表の主張/可視根拠/読み方/条件/判断への接続を個別監査し、弱図表を再設計する。数学/表示QAの過去合格だけで完成としない。改修後の版で独立教育レビュー・Opus・必要なQAを行う。

## 統合順序の更新（2026-11-08）

最適化の初回固定19原本/92HTMLレビューとQA記録は受領・保存済み。追加の図表品質要件によって、最適化の軽微4と図表改修、線形代数の図表改修を並行して完了した。初回固定を解除し、rootが102ページへの共有統合を完了した。最終承認を前後別に済ませるための重複QAは避け、両科目の改修原本が固定してから、同じ最終102版を独立/Opus/全体612状態で確認する。初回92版のQAを改修後版の結果と混同しない。

## Opus設計指摘の対応境界（2026-11-08）

07の任意初期値の固有成分分解は固有基底がある場合と明記。行列式/特性方程式で求根する部分は2×2に限定し、一般nの行列式性質/特性多項式/代数学基本定理は使わない。rowrank=colrankを未証明で使わず、02〜03のpivot列補題は可逆な行操作Eで列関係を保存し、RREFのe_i列から元の像の基底を得る短証明（rank0含む）。CSの零ベクトル、SVD A=0の分解と近似一意性を別扱いする。反例の回転は90度であり、実固有値無しを0/π含む全回転へ拡張しない。

10の非対称自作例A=[[0,2],[1,0]]は固有値±√2に対し特異値2,1で、絶対固有値と特異値の一般的混同を防ぐ。06のSSE余分3δa²+2δb²はΣx=0を使い、一般横座標では交差項2δaδbΣxが残ると明記。LS UIは元から恒等式の否定をしていなかったことを確認し、さらにquarter整数dの共線分類と理論上の等式/計算残差の区別をstatusへ明示（APIは不変）。

最終102版の完了証拠：Python22/Node111、612状態25827checks失敗0、NoJS102/37labs、全科目Opus承認。現在150原本/102HTML hash照合と実測サイズは[STATUS](STATUS.md)・[全体完了記録](reviews/2026-11-08-textbook-quality-completion-response.md)を参照。
