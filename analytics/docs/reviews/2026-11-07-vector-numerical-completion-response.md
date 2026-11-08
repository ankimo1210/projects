# ベクトル解析・数値解析：並行実装と検証の記録

2026-11-07。**ベクトル解析10章と数値解析10章・新6実験の並行実装、独立レビュー、Opus設計/実装/最終差分レビュー、現在版全体QA・内部試読まで完了。重要な未解決指摘・残作業はない。**

## 範囲と変更

先行7科目61章/25実験を保持し、各科目10章/20SVG/10表/3実験/10コラム/30演習60ヒント30解答30振り返りを追加。全体は9科目81章/82ページ、SVG163/表61/31実験/243演習486ヒント243解答243振り返り。

| 原本 | 変更と目的 |
|---|---|
| 新vector10章 | 場/線積分からGreen/Gauss/Stokes、条件/非循環証明/図表/演習 |
| 新numerical10章 | 誤差/条件/近似法と保証の限界、失敗と検算の理由 |
| vector/numericalの純粋JS・UI・Node test | 有限の6実験、独立式/0/符号/境界/停止理由/リセット |
| catalog/build/template/portable test/QA | 新2科目の目次・配布・章間移動と独立値/表示検証 |
| README/analytics入口/STATUS/計画/reviews | 読み方、前提/借用、現在の状態と証拠 |

既存61原稿/JS19/CSS/serveは保持し、線形代数/ODE/Fourier/統計4入口も継続。旧本の全文再構成/再build、新依存、外部公開、commit/push/worktree変更なし。先行未追跡ファイルとanalytics READMEの先行変更を保持する。

## 現在の検証

portable期待のRED（新20ページ不足のassertion failure1、harness error0）→統合GREEN Python20を確認。新APIそれぞれRED6→GREEN6、既存86と合わせNode98を作者が実行。HTML修正後の全体QAは492状態/19261checks失敗0、32原本/82HTMLhash一致。投影修正後の最終検証も成功し、末尾に確定した。

独立ベクトルレビューで01〜10/30演習と3APIを確認。10演習1の積分対象をF自身からcurl Fへ修正、05/09の一意ID、04/06/10の図ラベル交差を修正した。独立数値レビューは30演習と二分26/Newton17/Euler4800設定160800点/差分85設定を確認し、重要数式誤りなし。作者自己確認を独立合格の代用にはしていない。

Opus設計レビュー：[受領原文](2026-11-07-vector-numerical-opus-design.md)。一般三重積分を箱への0拡張/境界体積0/可積分性の借用として明示。数値Newton局所二次評価、行列∞ノルムの残差評価、補間反例、定数λのEuler/log評価を原稿で根拠付ける。実機IEEE定数の追加はせず、自作十進丸めモデルという担当判断を採用した。

証拠rootは _data/math-foundations/vector-numerical-2026-11-07/。見積82HTML約20MiB/証拠40MiB前後、実測は最終記録に確定する。ユーザー8765維持、一時browser/serverは所有者が終了する。

## 限界と閲覧

Linux Chromiumの内部試読とWindows側HTTPを区別し、Windows実機/file直接/他browser/実学生/実スクリーンリーダーは未確認。旧実験3種の微小bbox候補12/先行Windows message-channel4件/旧4本の全通読は範囲外。

[ベクトル解析](http://localhost:8765/index.html#book-vector) / [数値解析](http://localhost:8765/index.html#book-numerical)。閲覧serverのcatalogも82ページへ更新済みで、ユーザー用8765は維持。

[計画](../2026-11-07-vector-numerical-plan.md) / [進捗](../STATUS.md)。今回の全工程は完了。最適化と既存本の大きな本文統合は未着手。

## 独立レビューの実測

- **ベクトル数学/API**：全10章/30演習を精読、正則patch/星形の微分交換/Greenの境界/一般Gaussの0拡張/Stokesのpullbackと向きを確認。独立API888例＋不正型68例、最大差1.78e−15。
- **ベクトル試読**：10章×320/1280×明暗40状態、NoJS10、UI122状態、3完全reset、summary Enter/range ArrowRight/skip link Tab/表の実スクロール。新20図/10表と3UIを実画像で確認。
- **ベクトル再生成**：旧40状態のhashは保存し、後の数値JSの説明変更による再buildで現在pagehashを別記。ベクトル原本10/JS2/CSS不変と現HTML埋込みを確認。旧HTML未保存のため数値JSだけの厳密byte差分は独立に再現していない。現在版の全492状態はrootの別QAで確認した。
- **数値数学/API**：全10章/30演習、二分26/Newton17/Euler4800設定160800点/差分85設定。Decimal80桁で差分上界85例/Euler新上界4347例も検算。
- **数値試読**：10章×320/1280明暗40＋NoJS10=50状態、主要UI11項目、図20/表10を確認。最終3章の15状態と2lab計4設定で、補間ラベル/括弧付きdesc/正λと負初期値/差分入力丸めを差分確認。現原本と生成10章の本文が一致。
- **接続**：HTTP33件で新2入口/20章と既存4冊のindex/転送先/CSSが成功。既存ODEは新数値ODEの前提でなく、学習マップを経由する任意接続。これは旧4冊の全通読/描画/再buildではない。

独立レビューの専用browser/serverは終了。作者selfも別に保存し、ベクトルUI67項目、数値静的40状態/境界UIのRED→GREENを確認した。rootの全体QAとOpus原本レビューはそれぞれ別の証拠とする。

## 初回全体QAで検出したHTMLの欠落と対応

初回は全492状態/19261checksを完走したが、NoJSのnumerical-odeの解答で1件失敗した。数式の未escape比較記号がHTMLタグと解釈され、二分法の定理条件・Eulerの安定条件/解答・数値積分の導入/反例が欠けていた。4原稿17箇所の比較記号だけをescapeし、元の数学文に復元したときの全文一致を確認した。回帰テストは実際のHTMLパース後の文字列でRED3失敗を確認し、修正後Python21/Node98成功。READMEにも比較記号の執筆規約を加えた。

Stokes境界図の見出しとyラベルの小さな重なりも退避した。32原本中5章＋testの6ファイルだけ変更、API/JS/CSS不変。生成物は5ページだけ変わり、他77ページのbyte hashは初回版と同じ。旧原本6件と初回失敗の要約/hashを同rootに保存し、全体QAを修正版で再実行し492状態/19261checks失敗0、新候補0/旧微小候補12のみ。以前の失敗を削除して成功扱いにはしていない。

## 投影の手系と最終の数式/図差分

Opus全体レビューではHTML欠落の解消を確認する一方、共通3D投影の鏡映によりStokesの正向き境界が時計回りに見える重要1件を検出した。横座標を(y−x)/√2へ変更し、x/y軸・Fのラベルを追随させ、flux/Stokesの法線nとz軸ラベルも離した。数値のAPIは変えていない。

実SVG3本の橙の境界矢印を読み、画面のy下向きを含め orientation×det<0 を確認する回帰検査で、旧版RED（正のdet）→新版GREEN（負のdet）をroot/作者/独立担当がそれぞれ観測した。共通QAにも投影軸/境界回転/法線とzの離隔を追加した。作者は法線ラベル188状態接触0とUI75項目を確認。独立担当はStokes12/flux16代表状態とGauss2画像を確認し、正逆/高さ/傾き/0場の投影と読み方を検算した。

軽微3件は、04補題を固定x/jの二変数G(s,t)上の既存一様連続性に限定、台形証明から正しい補間剰余へ参照、法線ラベル離隔で解消。Gaussの箱のn_x/n_yを右手系にそろえた。数値微分の誤差釣合い図はEt=h/Er=0.1/h/合計Et+Er（0.1≤h≤1、共通縦縮尺）へ修正し、独立121点×3曲線の和の座標差は6桁丸め内。二分法の端点0をstrict符号判定前の初期分岐と明記した。

単なるbbox/overflowだけで向きや数式の和の正確さは保証できないため、今回の意味のある回転検査と執筆規則を残す。最新のOpus差分確認と、強化した全82ページQAの結果は最終節で確定した。

## 最終の全体検証とOpus承認

- Python21/21、Node98/98、Python4ファイルRuff lint/format、JS構文/QA self-test/対象diffの空白check成功。
- Linux Chromium 145.0.7632.6、82ページ×幅1280/390/320×明暗=492状態。19385 checks/失敗0、NoJS82、31実験の操作/境界/キー/reset、全243演習解答を確認。
- 代表PNG28、狭幅明暗/表左右の概念図表PNG544。ページoverflow/新図の文字重なり・領域外0、console/pageerror/外部要求/HTTP失敗0。旧3実験の微小bbox候補12は先行版と同じで対象外。
- 現在32原本と82生成HTMLのhashを照合。旧61原稿/JS19/CSS/serveは開始時と不変。初回の失敗はpre-fix-verification.json、修正前6原本はpre-fix-sources.jsonに記録し、最終版のbrowser-qa.jsonとは区別。
- [Opus設計原文](2026-11-07-vector-numerical-opus-design.md)、[実装全体原文](2026-11-07-vector-numerical-opus-implementation.md)、[最終差分原文](2026-11-07-vector-numerical-opus-final.md)。設計の一般三重積分、実装時のHTML比較記号、図ラベル等の必要修正を解消し、最終差分は承認可。
- Windows側HTTP6件/旧教材接続HTTP33件も成功。表示の証拠はLinux Chromiumであり、Windows実機描画を検証済みとはしない。
- 全QA/独立レビュー/Opusの専用browser・一時serverは終了。ローカル閲覧8765は維持。新依存/外部公開/commit/pushは行っていない。

実測：生成82HTML 21,930,760 bytes、証拠 31,466,459 bytes（du -sh: 32M）。見積40MiB前後/30GiB未満に収めた。
