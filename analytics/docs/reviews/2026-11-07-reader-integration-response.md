# 全体統合・内部試読の記録

更新日: 2026-11-07。状態: 現行HTML版の全体統合・内部試読・実ブラウザQA・Opusの独立画面確認と最終再確認まで完了。

## 対象と修正

現行31章・入口込み32ページを3担当で内部試読した。高校数学既習者が、なぜ定義や定理が必要かをたどれるかを確認したもので、実学生への学習効果調査ではない。既存Jupyter Book全11巻の再ビルド/全通読や新科目の追加は行っていない。

| 変更箇所 | 問題と対応 |
|---|---|
| chapters/integration-methods.html | 本文外の台形公式を尋ねる振返りを、本文の1/xの相殺と広義積分の収束の違いへ変更。C¹の初出でfとf′の連続性・閉区間端の片側微分を説明 |
| chapters/proofs.html | 演習前に有理数/無理数を復習し、整数比の分母は0以外と明記 |
| chapters/hessian-extrema.html、partial-derivatives.html | 転置の初出を、列→行・行と列の入れ替えとして具体化 |
| chapters/invariants.html | 盤の静止SVGを追加。62升/黒30白32、除外2升、黒白一升ずつのドミノを本文と照合。色は共通tokens、aria/title/descあり |
| template.html、style.css、reader.js | 狭幅の章内目次をnative detailsにし、キー操作・節への移動を可能にした。desktopは展開、狭幅は折畳み、JS無効は初期open。全幅でsummaryを表示してNoJSの幅切替後も再開可。matchMedia changeでJS有効時の両目次を同期 |
| build.py、tests/test_build.py | 最終章を発展教材の学習マップへ接続。入口の技術説明を除き、未生成教材は「準備中」と表示。長い式の読み方案内を追加 |
| tools/browser_qa.cjs（新規）、README.md | 任意の実ブラウザQAを追加・文書化。既存のplaywright-core/Chromiumを指定し、依存を追加せず、既知32HTMLのみローカル配信・入力hash・失敗exit・finally終了を実装 |

数学の定理・演習の値・31章/14実験/31コラム/93演習の構成は変えていない。別担当が盤の62升・偶奇・30/32・除外座標と、定義補足の正確さを再確認した。盤の作成中に使った未定義の--paperは、定義済みの--surfaceへ修正した。

巻末リンクはPython期待値を先に変更してRED→GREEN。狭幅の章内目次も実ブラウザで可視toggleがない旧版をRED→GREEN。同じ文書で320→1280へ広げるとclosed menuが残る挙動も再現し、event待ちを含むRED→GREENで修正した。

## rootの最終QA

Linux headless Chromium 145.0.7632.6、playwright-core 1.56.0。Windowsのユーザーブラウザ/プロファイルは使わない。

- **4620 checks・失敗0、harnessError 0**。
- 32ページ×幅1280/390/320×light/dark = **192表示状態**。
- 全31章の前後リンク実クリック、ヒント/解答、テーマ、章メニューのキー操作。
- 全31章×390/320の章内目次操作62ケース。summary可視→Enter開閉→定義節リンクへ実クリック。
- リロード無し320→1280→320で、chapter-menuとsection-menuが両方操作可能。
- 数式のある24章では狭幅のheaderに横スクロールの案内を1回表示。footer実クリックでheader/目次まで戻り、NoJSで閉じた目次も幅切替後のsummaryから再開できる。
- 全14実験の操作/reset、新5実験の端点・零勾配・曲率4例・解析点・範囲キー・積分規則・極座標を確認。
- JavaScript無効の別contextで32ページ・93演習と解答、31章のnative目次初期open/開閉を確認。
- console/pageerror/requestFailure/httpError/blockedRequest、ページ全体の横はみ出し・ID重複・未定義SVGトークンは0。
- Taylorの内側mathを実mouse.wheelでscrollLeft 0→84=maxへ動かし、末尾右端319.47pxが枠右端327px以内に入り、ページ幅390pxを維持することを確認。
- QA入力のSHA-256と現在の32生成HTMLがすべて一致。11対象原本も固定版と一致。
- Python **5/5**、Node **51/51**、QAサーバ許可リストのself-test成功。

実行時刻: 2026-11-07T08:35:20.357Z ～ 2026-11-07T08:36:30.126Z（UTC）。toolは入力HTMLを起動時にsnapshotし、外部ページを要求させず、終了時にブラウザとサーバを閉じる。生成HTMLは 4,329,835 bytes。最終JSONと11PNGは _data/math-foundations/integration-2026-11-07/ の1rootだけで、logical 2,111,688 bytes・du実測2.1M。失敗版を別に保持していない。

## 目視と測定の区別

rootは入口・盤・新5実験・長い数式・desktop凡例と軸・狭幅の章内目次の最終11PNGを目視した。SVG文字bboxの約1px超過候補12件はJSONに残したが、代表画像の実字形は欠けておらず、製品を変更していない。

320pxの最小実フォントは盤13.78px、新5実験13.32〜14.35px。従来7実験の軸ラベル10.25pxは今後の見やすさの改善候補として記録する。MathMLの描画・矩形・スクロールの確認は、数学の意味の検証の代替ではない。

## 検証側で補正した仮定

- 経路をx軸にしたとき意図的にdisabledになる係数を操作する誤判定を修正。
- 長い式のスクロール所有者を外側divと仮定せず、内側mathへ実入力して確認。
- closed details内に残るlayout boxを可視と数えないよう、祖先のopen状態を加味。
- 長い要素のPNGにfixed skip-linkが混入する撮影アーティファクトは、幅を保ってviewportを対象高さに広げて解消。実寸法をJSONに記録し、製品CSSを都合よく変えて撮影していない。

## Opusレビュー

初回のソース/導線/QAツールレビューは重要・必須指摘なし。任意5点（盤ラベル、転置の初出、巻末、狭幅目次、C¹説明）も採用した。

初回はrootの分担判断でOpusをソース/QA結果の確認に限定していたが、Windows操作の失敗を正常に動くLinuxまでの禁止へ広げる必要はないため解除した。Opus自身も独立したLinuxブラウザで操作・描画を確認し、最後の修正後確認も終了した。

原文：[初回レビュー](2026-11-07-reader-integration-opus-review.md)／[独立した画面確認](2026-11-07-reader-integration-opus-visual-review.md)／[最終修正後確認](2026-11-07-reader-integration-opus-verification.md)。

独立画面確認の任意3点（数式の続きの案内、footerの戻り先、読者向けの入口文）とNoJSの幅切替も修正。実操作の3 RED→3 GREEN、availability表示のPython RED→GREENを確認した。式の案内は微妙な影だけにせず、狭幅の章冒頭へ明示した。

最終確認は「4点とも解消・重要な退行なし・新たな任意改善なし」。Opus自身も現在32HTMLの操作・画像、Python5/5・Node51/51、章間リンク131本を確認し、サーバとブラウザをすべて終了した。**未解決の重要指摘なし。**

## 未確認の範囲

Windows Computer Useは黒画面とactivate失敗が再取得後にも再現したため、Windows実機操作は未実施。Linux検証と同一視しない。file:直接閲覧、Firefox/Safari/実モバイル、スクリーンリーダー、実学生の学習効果も確認対象外。先行Windows検査のmessage-channelエラー4件は発生元未特定であり、今回Linuxで0件だったことを修正済みの根拠にはしない。
