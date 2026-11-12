# 離散数学：実装・Opusレビュー・統合試読の計画

> **For agentic workers:** superpowers:subagent-driven-development と独立レビューで進める。ユーザーは「今までと同じように実装・Opusレビュー・統合と試読まで」を明示している。既存の設計・環境・承認を再確認のために止めない。

**Goal:** 数える・同一視する・つながりを調べる・手順の正しさを説明する大学基礎の離散数学10章を完成させる。
**Architecture:** 既存readerへbook=discreteを追加。本文HTML/MathML/inline SVG/native table、純粋計算と操作UIのJS、標準Python buildを継続。
**Tech Stack:** Python標準、HTML/CSS/MathML/SVG、plain JS、Node built-in tests。新依存なし。
**Spec:** ユーザーの「数学の気持ち・役立つ理由・面白い話・図表を増やす」、既存HTML教科書の構成と本書設計。実装までの通常の内容判断はrootが行う。

## 設計と範囲

高校数学の既習者が、数学の言葉と証明8章から進める。微積分と確率を修了条件にしない。集合・帰納法・Euclid、順列/組合せは復習リンクと最小定義で回収する。各章の目安25–45分、章6/9は30–50分。10章の全主要結果を初等的に説明し、一般の母関数理論・抽象代数・Hall・計算困難性を必須にしない。

| No | slug | 題名 / 内容 | 証明・図表 |
|---|---|---|---|
| 01 | discrete-relations | 同じとみなして、まとめる / 二項関係・同値関係・類・分割 | 分割↔同値関係、対称/反対称の区別へ予告、余りの自作6要素図 |
| 02 | discrete-orders | 全部を比べなくても、順序はある / 半順序・比較不能・Hasse・有限DAG・トポロジカル順序 | 有限DAGに入次数0の点、除去帰納法。矢印関係をこの章で定義し後のグラフを前提にしない |
| 03 | discrete-counting | 数えずに、数をそろえる / 全単射・等しい重複度・二重計数・鳩ノ巣 | kC(n,k)=nC(n−1,k−1)、箱容量の背理法。順列公式の再講義はしない |
| 04 | inclusion-exclusion | 重なりを、足し引きで戻す / 二・三集合包除・一般有限式・禁止位置の例 | 各要素の係数、所属表。集合の独立性を仮定しない。一般式は二項和または指示関数で説明 |
| 05 | modular-arithmetic | 余りを残して、計算する / 合同・gcd・Bézout・逆元・消去条件 | 加算乗算保存、拡張Euclid例、逆元⇔gcd1。割算不可の反例。lab=discrete-modular |
| 06 | recurrence-relations | 次の一手から、全体を決める / 初期値・タイル漸化式・一次漸化式・再帰/DP・回数 | T0=T1=1、帰納法、a(n+1)=2a(n)+1。母関数は任意の係数比較の小節/コラムに留め解析収束不要。lab=discrete-recurrence |
| 07 | discrete-graphs | 形を捨てて、つながりを残す / 有限単純無向グラフ・歩道/道/閉路・次数・連結・Euler | 握手、奇次数の偶数性、辺あり頂点の連結性とEuler条件。有限構成/閉歩道継ぎ足しで十分性 |
| 08 | discrete-trees | つなぎながら、余分をなくす / 木・唯一の道・葉・n−1・全域木・BFS | 有限非空を明示、n−1だけでは木でない反例。BFSの層と親辺、辺数による最短性 |
| 09 | shortest-paths | 近道を、確かな手順で探す / 重み・緩和・Dijkstra・非負性・到達不能 | 確定集合の不変量、負辺反例、BFSとの条件差。lab=discrete-shortest |
| 10 | graph-coloring | 隣り合うものを、分けて置く / 頂点彩色・二部性・奇閉路・greedy Δ+1 | 奇閉路と二部性の同値、根からの距離の偶奇、greedy上界と最小値の違い。割当や時間割の自作モデル |

章ごとに問い→定義の動機→短い証明→仮定/反例→接続、任意コラム1、演習3（各ヒント2・解答1）、振り返り3。最低1つでなく各主題を図表化する。全章に少なくとも概念図2/比較表1を目安とするが装飾の水増しはしない。SVG22px、360viewBox、長い説明はcaptionへ、共通token色、明暗/320px/NoJSで読む。表は式のみnowrap、長文を固定しない、native captionと既存の枠内固定を保つ。原図は正確なコードで描く。

コラムは本文の概念が役に立つ自作モデルか、検証できる一次資料に接続。実社会の万能な主張・未確認の歴史逸話は避ける。数学自体の意外さも扱う。資料: MIT OCW Mathematics for Computer Scienceのreadingsで学部基礎の範囲を確認済み（2026-11-07）。https://ocw.mit.edu/courses/6-042j-mathematics-for-computer-science-spring-2015/pages/readings/

## 数学実験の境界

新内部APIは assets/discrete.js のグローバルMathDiscrete/Node exports。実装担当が具体的signatureを確定しrootへ伝える。assets/discrete-experiments.js はclassic script、各[data-lab]を一度初期化、native controls/reset/status/NoJS。外部fetch/moduleなし。
1. discrete-modular: 法m=2..12、乗数a=0..m−1、入力x=0..m−1。ax mod m、像、逆元の有無/gcd、選択点を表示。m減少時はa/xを範囲へ保つ。逆元なしを0と混同しない。
2. discrete-recurrence: n=0..20、T0=T1=1。Tnと二つの部分問題、DPの加算回数を表示。実際に指数時間の再帰を走らせない。空盤n0は1。
3. discrete-shortest: 6頂点A..Fの固定無向非負重みグラフ、通常/0重み同距離/到達不能の3preset。始点A・終点F、初期状態を含む確定ステップ選択。各dist/親/経路、∞と0、未確定/確定を色と記号で区別。到達不能を偽の経路にしない。負重みはAPIで拒否し、本文の反例で説明。

## Global Constraintsと担当境界

- Scope: analytics/math_foundations、analytics/docsとanalytics/READMEの入口のみ。生成証拠は_data/math-foundations/discrete-2026-11-07/の1root。
- 既存checkout/mainで続行（前の承認設計とユーザー「同じように」に基づく）。既存未追跡原本・同時変更を保つ。branch/worktree切替・commit/push/deploy・新依存なし。
- author A: 新01〜05の5 HTMLだけ。author B: 新07〜10の4 HTMLだけ。math UI担当: discrete.js/discrete-experiments.js/tests/discrete.test.cjsだけ。root: 新06、catalog/build/template/tests/serve/QA/docs統合。共有CSSはrootのみ、既存デザインで足りるなら変更不要。
- 一次実装と数学検算・実画面レビューの担当を分ける。Opusは既存win math/Opus max sessionを使い、段階レビュー/最終固定版を依頼して完了を能動確認。自分の実ブラウザ操作を禁止しない。レビュー中は独立の統合/QAを進める。
- 既存41章/19実験と前回図表を維持する。数学API7本を変更しない。

## Review Focus

1. 同値と半順序/反対称、DAGの向きとHasse省略。循環した前提がないこと。
2. 数え上げの対象/区別/重複度、包除の一要素の係数、pigeonholeの境界。
3. 合同の消去条件、Bézoutの根拠、m変更/非可逆/0のUI。
4. タイルn0/1、初期値/一意性、一般証明と有限列挙、DP回数と実行時間の区別。
5. Eulerの辺と道/閉路、木の非空/連結、BFSとDijkstraの重み条件、∞と0、greedy彩色の上界と最適性。

## Tasks / progress ledger

- [x] Task 1: 既存教材/設計の監査、独立カリキュラム確認、担当と境界・有限実験を設計。
- [x] Task 2: A/B/rootで10原稿を実装。定義/証明/仮定/反例、図表、各3演習と2段階ヒント、コラムを確認。
- [x] Task 3: 新純粋計算を意味ある境界/独立列挙テストから実装（REDを確認）、3UIを追加し単体チェック。
- [x] Task 4: catalogへ離散数学10章、buildへ2JS、入口/科目案内/前後リンク、serveへ新10ページを反映。既存portable testへ新10ページ/3labを先に追加しRED→GREEN。
- [x] Task 5: 独立数学/視覚レビューとOpusの段階レビュー、重要指摘を修正し差分再確認。
- [x] Task 6: 全52ページ×1280/390/320×明暗、NoJS52、全22実験、各節目次、全図表/表左右/全153演習/306ヒント/153解答を数えて検証。既存QAの固定数はcatalog/原稿から導出し不足を隠さない。
- [x] Task 7: 最終Opus固定原本レビュー、全体統合/内部試読、hash/件数/サイズとSTATUS/README/完了記録を同期。

検証: Python既存20と必要な新構造テスト、Node既存65+新math実験の境界/列挙。SVG XML/ID/ARIA/MathML/全章構造/リンク、19既存+3新操作、全図表の狭幅明暗実読。Windows HTTP200とLinux Chromiumの実表示は区別する。実学生・他browser・Windows描画は未確認なら明記。

出力見積: 生成52HTML×約210KiB≒10.7MiB、全図表切抜/QA/独立レビュー証拠は1root20MiB前後を目安、30GiBに遠く及ばない。反復は同じファイルへ上書き、重複の中間出力は保存しない。最終duを記録。

## Opus設計レビューへの反映（2026-11-07）

- 01に順序対/直積の最小定義、02の入次数0証明は最長有向道で後章の鳩ノ巣を先取りしない。
- 03/04で固定要素を入れ替える全単射、または指示関数の有限積展開により包除の係数を証明。確率編の二項定理を前提にしない。
- 05のBézoutは各余りの整数線形結合を隣接する2余りの組で通常帰納し一般証明。06はQ(n)=初項からn項までの主張を通常帰納する形を説明し、前二項を使う根拠を補う。
- 09の最短距離は有限の道の最小から定義し、非負重みなら歩道の閉部分を除けることを示す。失敗例は局所定義した有向・負辺・閉路なしの例。
- 10の同層の隣接辺から奇閉路を作る際は、BFS木の分岐点で重複を除くか、奇閉歩道の補題を証明する。

[設計レビュー原文](reviews/2026-11-07-discrete-opus-design.md)。上記は実装範囲内の証明の補完で、依存/公開API/科目数は変えない。

## 完了証拠

2026-11-07。10章24SVG/10表、3実験、30演習/60ヒント/30解答/30振り返りを実装。Python20/Node76、全52ページ312状態の10824checks失敗0。Opus全体の重要数学欠陥なし、商写像1図を6入力/6矢印/3出力へ修正。1ページを12状態/452checks失敗0で追試、他51ページのhash不変。最終Opus差分確認で指摘解消・重要退行なし。全19原本/52ページの検証対応とサイズを確定し完了。[完了記録](reviews/2026-11-07-discrete-completion-response.md)に対応と限界を整理。

最終実測：生成HTML 10,344,733 bytes、QA/独立レビュー等の1root 19,795,927 bytes（du 20M）。Windows描画や実学生試読は今回未検証、Linux実表示/内部試読と区別する。
