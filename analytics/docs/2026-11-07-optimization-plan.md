# 最適化：実装・Opusレビュー・統合試読の計画

> **For agentic workers:** superpowers:subagent-driven-development / TDD / 独立レビューを使用。ユーザーは既存と同じ工程で最適化も進めることを承認済み。通常の実装判断を自律実行し、再承認で停止しない。

**Goal:** 問題の構造、必要/十分条件、有限反復と最適性の証拠を区別できる大学基礎の10章を完成させる。
**Architecture:** 既存9科目81章/31実験へoptimization10章/3実験を追加。本文2担当、数学UI1担当、共有統合/検証とレビュー調整はroot。
**Tech Stack:** 標準Python、HTML/MathML/inline SVG/native tables、plain classic JS、Node built-in tests、既存Chromium/Playwright。新依存なし。
**Spec:** 本計画と既存の「数学の気持ち・なぜ役立つ・図表とコラム・条件/反例」方針。

## 前提・制約

微積分Ⅰ/Ⅱの勾配・全微分・Hessian、線形代数への橋、数値解析の誤差/条件/根Newtonへ必要箇所だけ戻る。確率・離散・複素・ベクトル解析や旧大型本の修了は必修にしない。一般凸解析/多様体/測度/大規模solverは含めない。

各章：動機→定義→正しい短い証明→仮定/反例→接続、任意コラム1、演習3（各2ヒント/解答）、振り返り3。概念SVG2以上/比較表1。SVG360viewBox/文字22px以上/token色/固有title・desc・ARIA/data-visual、矢印は1path1subpath。定量図は正確な座標・共通尺度を使い、尺度の違う図は明示。表はcaption/th scope/focuswrapper、短式のみtable-math、長文normal、必要な対象tableだけmin-width30rem。数式テキストの比較記号は必ずHTML escape。NoJSでも本文/図表/ヒント/解答を読む。

既存81原稿/23JS/CSS/serveを保持。既存4大型教材への入口も維持。新依存/公開/commit/push/worktree切替なし。先行ベクトル/数値の最終Opus承認と記録をrootが先に確定し、その32固定原本を変更するcatalog/build/QA統合は後で行う。新optimization原稿/JS/testの独立作成は並行可。

## 10章と証明の境界

| 章 | slug | 内容・仮定と証明 |
|---|---|---|
| 01 | optimization-problems | 目的/実行可能/最小値とinf/存在。非空compact＋連続の極値定理は借用を明示。閉/凸だけでは存在しない |
| 02 | optimization-convexity | 凸集合/関数、開近傍C¹の一次条件を線分で導出、凸なら局所=大域、狭義凸は存在時の一意性 |
| 03 | optimization-optimality | 内点grad0、C²二次必要/十分、境界や退化Hessianの反例、候補と証明の違い |
| 04 | optimization-gradient | 線分上のL-Lipschitz勾配→下降補題をFTCで証明、step条件、下降/停留/収束を区別。opt-gradient |
| 05 | optimization-newton | Hp=−grad f、PDなら下降、可逆不定値で保証なし。Armijo有限停止をC¹/下降方向/0<c,β<1から説明。一般二次収束は必須にせず |
| 06 | optimization-scaling | 対角二次関数の曲率比、座標変換u=x,v=√κ y、元座標では前処理。条件数/metric/問題そのものの変更を区別 |
| 07 | optimization-projections | 非空closed convex C⊂R²のEuclid射影。compact極値を借用して存在、VI/一意性を証明。disk/boxと射影勾配。opt-projection |
| 08 | optimization-lagrange | 等式制約、regularity、候補と大域。L=f+νhを統一し、旧章g=c / ∇f=λ∇gに対してh=g−c / ν=−λと明記 |
| 09 | optimization-kkt | g≤0/λ≥0、active/complement/stationarity。C¹＋全等式/有効不等式grad全体LICQの必要性は借用。f/gᵢが凸C¹、hⱼがアフィンのもとで、実行可能性/非負乗数/相補性/停留を満たせば大域最小であることを証明。十分性にLICQ不要。opt-kkt |
| 10 | optimization-duality | infは元変数領域全体、弱双対性を証明、1D二次モデルで強双対性を直接計算。一般strongdualityを必修にしない |

閉有界集合上の連続関数の極値事実を借りる場合は明示。射影存在はbenchmark点を取り、その点より遠い部分を切ったcompact集合へ制限する。VIは(p−q)·(z−q)≤0、一般に直交等号ではない。原点/内点/境界入力の残差0では残差の単位化が未定義で、幾何の法線の不存在とは呼ばない。

勾配法の条件は更新線分全体で確認。任意非凸でgrad→0から大域最適を主張しない。必要ならconvex/Lsmooth/最小点存在/step1/Lの限定でO(1/n)を別proofとして示す。Newtonは一般二次収束を無条件に主張せず、rootのNewtonと最小化を区別。KKT必要性は各grad非零だけでなく全体の線形独立。凸十分性にはf/gᵢの凸C¹性とhⱼのアフィン性を明記し、LICQ/Slaterは不要。一般strongdualityは導入のみか任意の借用条件付き。

原則一・二変数で説明し、09〜10の有限n変数記法で使う勾配/連鎖律/一次凸性不等式の一般的微分法は標準的拡張として借用を明記する。inf∅=+∞、下に非有界なら−∞であり、最小点の存在と区別。双対章は主問題の実行可能集合が非空で最適値が有限な場合を基本とし、双対infは−∞や非達成も許す。gapを有限実数として計算するのは明示した二次モデルだけとする。

射影勾配の固定点x=P_C(x−α∇f(x))（α>0）はVIと同値で、凸性のもとで大域最適を保証する。反復の下降/収束には別の滑らかさとstep条件が要り、任意stepの収束を主張しない。

独立設計監査で勾配3125/射影150/KKT150ケースの閉形式/VI/相補性を検算済み。一次資料：[MIT KKT必要条件](https://ocw.mit.edu/courses/6-7220j-nonlinear-optimization-spring-2025/mit6_7220_s25_lec07.pdf)、[必要性と十分性](https://ocw.mit.edu/courses/6-7220j-nonlinear-optimization-spring-2025/mit6_7220_s25_lec08.pdf)。原稿は独自日本語/自作例とする。

## 新3実験・API

MathOptimization frozen UMD/Node exports、assets/optimization.jsとoptimization-experiments.js、tests/optimization.test.cjs。classic UI、native controls/reset/data-key/data-value/data-raw/data-raw-value、labError false正常/true予期せぬ例外、nullを0と区別。UI初期化重複防止。戻り値とdefaultは担当が早期root通知。

1. opt-gradient（04）：gradientState({kappa:整数1..16,alpha:0..0.5,n:整数0..40,x0,y0:−2..2})。f=(x²+κy²)/2、q₁=1−α,q₂=1−ακ、xₙ=q₁ⁿx₀/yₙ=q₂ⁿy₀。全初期値の厳密な収縮条件0<α<2/κ。y₀=0なら範囲外でも収束し得て、原点なら全αで不動。初期objective0の比率はnull。有限nで最大約1.3e69、指数表示/等縮尺描画/対数objectiveの0の扱いを明示。下降/収縮の保証と有限軌道を分ける。
2. opt-projection（07）：projectionState({kind:disk|box,x,y:−2..2,radius:.5..1.5})。diskは半径、boxは半辺長、中心0。内側はp、外diskはr p/||p||、boxは成分clip。residual=p−q、distance、残差のunitDirectionはdistance0ならnull。全z∈CのVIと境界を正しく図示。
3. opt-kkt（09）：kktState({a:−2..2,b:−1.5..1.5,lambda:0..4})。min .5(x−a)² s.t x≥b（g=b−x≤0）。x*=max(a,b),λ*=max(b−a,0),p*=.5max(b−a,0)²。d(λ)=λ(b−a)−λ²/2、gap≥0。δ=b−aとしてδ≥0ならgap=.5(λ−δ)²、δ<0なら.5λ²−δλで桁落ちを避ける。a=bはactiveなのにλ*=0。任意の入力λでstationarity/compが成立するとはせず、最適乗数との違いを見せる。

TDDは独立オラクルで実際のRED→GREENを観測。符号/0/範囲外/κとα境界/全初期値と特殊軌道/射影距離0/KKTactiveλ0/dual gapを確認。有限実験は一般の証明と呼ばない。

## 担当・共有統合

- author A：新01〜05 HTMLのみ。
- author B：新06〜10 HTMLのみ。
- math/UI：新optimization.js/optimization-experiments.js/optimization.test.cjsのみ。
- root：計画/既存9科目の締め/共有catalog/build/template/test_build/QA/README/STATUS/ポータル、独立レビュー/Opus/統合・内部試読。
- 完成担当から独立レビューを別に割当。Opusは既存win math/maxへ設計/実装/差分レビューを依頼し、能動poll。browser操作可、専用server/browserのみ終了、ユーザー8765維持。
- CLI認証はnative WSL /home/kazumasa/.local/bin/claudeを使用。Windows PATHのnpm shimと混同しない（認証検証先の誤りを避ける）。

## Tasks / progress

- [x] Task1: 現況hash/章順/証明境界/3有限実験、独立設計監査。
- [x] Task2: 新10章（図20/表10/30演習60ヒント30解答/コラム10/振り返り30）。
- [x] Task3: 新3実験/TDDと境界UI/0/null/keyboard/reset。
- [x] Task4: portable期待を先にRED、既存9科目締め後に10科目91章/92ページ34labsへ統合→GREEN。
- [x] Task5: 独立数学/視覚/全30図表教育とOpus改修後レビュー。初回軽微4を解消し、最終重要0・軽微0で10章承認。
- [x] Task6: 初回92版の552状態は履歴として完了済み。図表/正式見出し改修後の全102ページ612状態/NoJS102/37実験/303演習606ヒント303解答へ統合し、現在版を内部試読する。
- [x] Task7: 現在版原本/生成物hash、件数/サイズ、Opus承認、README/STATUS/完了記録。

## Review Focus

1. min/inf/存在/一意性と局所/大域、strict convexの存在時条件。
2. Lsmooth/線分の仮定、stepの全初期値保証と特殊軌道、NewtonのHessian条件。
3. 座標尺度/metric/前処理と問題変更、正しい等縮尺のレベル集合。
4. 射影VIの符号、残差0、box角の法線錐と非一意法線を混同しない。
5. KKTの符号/全体LICQ/activeλ0、弱双対性のinf領域と計算されたgap。

出力見積：92HTML×約300KiB≒27MiB、同1rootのQA/図表/レビュー証拠約40MiB。巨大配列なし、retry同名上書き、失敗は要約/hash/必要な旧原稿だけ保存。30GiBには遠く、最終du実測を記録する。

ユーザーの追加承認により線形代数本編も並行実装・統合を完了した。後続候補はODEとの接続。新ODE実装は今回に含めない。

## 追加品質ゲート（2026-11-08）

[図表メッセージ強化計画](2026-11-08-figure-message-quality-plan.md)を完成条件に追加。各図表の主張/可視根拠/読み方/条件/判断への接続を個別監査し、弱図表を再設計する。数学/表示QAの過去合格だけで完成としない。改修後の版で独立教育レビュー・Opus・必要なQAを行う。

## 統合順序の更新（2026-11-08）

最適化の初回固定19原本/92HTMLレビューとQA記録は受領・保存済み。追加の図表品質要件によって、最適化の軽微4と図表改修、線形代数の図表改修を並行して完了した。初回固定を解除し、rootが102ページへの共有統合を完了した。最終承認を前後別に済ませるための重複QAは避け、両科目の改修原本が固定してから、同じ最終102版を独立/Opus/全体612状態で確認する。初回92版のQAを改修後版の結果と混同しない。

現在の最適化改修版は、全30静的図表の実装/self確認まで完了。前半はC、後半はrootで、447exact検算/30表示/26UIcase/374checksと両面ink確認。作者以外の図だけ教育レビューはAが30/30承認、Opusも改修後版の重要0・軽微0で承認。全科目最終102ページ612状態QA・内部試読・hash照合も完了した。

最終102版の完了証拠：Python22/Node111、612状態25827checks失敗0、NoJS102/37labs、全科目Opus承認。現在150原本/102HTML hash照合と実測サイズは[STATUS](STATUS.md)・[全体完了記録](reviews/2026-11-08-textbook-quality-completion-response.md)を参照。
