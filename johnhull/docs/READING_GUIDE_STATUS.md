# 章ごとに読むガイド：T0・T1 の状態

更新日：2026-10-18。計画：[READING_GUIDE_PLAN_2026-10-18.md](READING_GUIDE_PLAN_2026-10-18.md)。

## 目標と停止条件

既存の notebook・節別補足教材・節台帳を変更せず、Book に独自の日本語解説を追加する。
今回は T0 の影響実測と T1 の Ch13・Ch8 だけを扱う。ユーザーの読後判断と Claude の独立検証を待ち、T2・B1–B6 には進まない。
main への merge と main の push はしない（作業branchは初稿e491b454までpush済み）。今回の修正はpushしない。

## 判断と作業環境

- §7 の1〜3：2026-10-18 にユーザーが推奨3点を承認。新しいガイドのみ、原典1頁あたり和文300〜500字を目安とし、Ch13・Ch8で分量・文体を確かめる。
- 基点：main `7f668a39af1d9e9b2e91e4c191f74b8b788c2c8a`。ブランチ：`codex/reading-guide`。worktree：`/home/kazumasa/worktrees/reading-guide`。
- アプリの worktree 作成は Windows Git の UNC 所有権判定で失敗したため、WSL Git で作成。Git の trust 設定は変更していない。
- 作業データ：`/home/kazumasa/projects/_data/johnhull/reading-guide/`。Book の `_build` と portal の `site` は、そこに生成した実体への bind mount。検証器が外部 symlink を拒否するため、この構成にした。既存の補足教材ソース・コミット済み HTML は不変。
- `uv` の呼出しで worktree の hullkit/src と report を絶対 `PYTHONPATH` の先頭へ置く薄いラッパーを使用。import 先が worktree 内であることを実測した。共有 `.venv` は再同期していない。
- worktree の `.venv` は main の共有環境への symlink。既存研究が使う RB-F04 の `reference.npz` は main の既存ファイルを読取専用で bind mount した。F: は既存 `/mnt/f` の接続不良を避け、別の読取専用マウントを使う。元データのコピー・再生成・移動はしていない。
- 追加容量の事前見積もり：Book 約0.3 GiB×再生成1組、画像・ログ・PDF抽出・検査の一時データを含め4 GiB未満、逐次実行の最大メモリー4 GiB未満。大規模研究・配列保存は行わない。終了時に `du -sh` を記録する。
- 並列エージェントを使わず、原典照合と自己検査を実装者が実施する。独立レビューは指定どおり Claude に引き継ぐ。

## 進捗

| 段 | 状態 | 完了条件・次の操作 |
|---|---|---|
| T0 | 影響の実測済み | 新規の台帳エラーなし。基準からのartifact検査FAILを保持。全体testは環境整備後の残1件の再検査まで実施 |
| T1 | 独立検証の指摘修正・指定検査済み、ここで停止 | §2の修正をBookへ反映。数値44 tests・2幅の表示・目視・lint・共有runtime・通常release・全体testを確認。commit後にtracked releaseを確認し、修正差分の再検証と本人の読後判断を待つ |
| T2・B1–B6 | 停止 | パイロット読後のユーザー判断後、別途着手する |

## 検証・引き継ぎ

検査の生ログと時刻・使用量は上記データ root に保存する。T0の全結果・失敗出力は [t0.json](validation/reading-guide/t0.json)。

### T0 の結果

| 検査 | 変更前 → 空ページ＋TOC追加後 |
|---|---|
| `jupyter-book build --all` | 両方終了コード0、154件（153 WARNING・既存1 ERRORの表示）。新しい警告なし |
| `verify_section_ledger.py --check-artifacts` | 両方FAIL、同じ158エラー。増減0。受入済み306件の状態は不変 |
| 共有MathJax検査 | 元の31ページでPASS。元の30 notebookのarticle DOMも main と一致（overviewは生成目次が変わる） |
| release / 共有runtime | manifest更新前はTOCのハッシュ不一致だけでFAIL。更新後は両方PASS |
| `make test` | 初回は9 failed / 11,896 passed / 76 skipped / 2 errors。環境整備後は1 failed / 11,906 passed / 76 skipped。残1件は `.venv` 入口整備後に1/1 PASS。全体の最終再検査はT1で行う |

台帳のFAILは、ガイド追加前から、旧来の外部MathJaxを含む `book_assets` の指紋と古いBook HTMLの厳密ハッシュが現在の生成物に合わないために出ている。
記録時と同じ Node・Playwright・Chromium・フォント・locale・TZ未設定でも、`book_assets` の差が残ることを確認した。
台帳・過去証跡・検証器を変更してPASSにする作業は範囲外とする。TOC追加による新規の失敗はなく、共有runtime更新で新規のハッシュ不一致は解消するため、配置は計画どおり維持する。

環境由来の失敗は、repo内に置いたpytest一時保存先、ローカル参照ファイルの不足、`.venv` の入口不足だった。
pytest固有の一時領域は通常設定に戻し、ガイドの作業データは上記データrootへ保存する。

### T1 初稿の提出物と計測（e491b454）

| 章 | ソース | 和文の文字数 | 対象原典頁 | 初稿区間の時間 | 初稿区間の出力tokens |
|---|---|---:|---:|---:|---:|
| Ch13 | [ch13.md](../book/notebooks/guide/ch13.md) | 10,266 | 25頁 | 246.902秒（約4分7秒） | 14,447 |
| Ch8 | [ch08.md](../book/notebooks/guide/ch08.md) | 5,969 | 12頁 | 172.034秒（約2分52秒） | 9,671 |

文字数は漢字・かなの範囲（Unicode U+3040–30FF / U+3400–9FFF）を機械的に数えた。見出し、長音符・中黒など同範囲の記号を含み、英数字・句読点（、。）・数式のASCII記法・空白は含めない。
MyST記法を含むソース全体の非空白文字数とSHA-256は [verification.json](validation/reading-guide/verification.json) に併記する。
Ch13は本文pp.288–308と付録pp.312–315の25頁で、章末問題pp.309–311を除く。Ch8はpp.201–212の12頁。

| 初稿区間 | 入力tokens計 | うちキャッシュ再利用 | うち再利用外の入力 |
|---|---:|---:|---:|
| Ch13（10:35:41–10:39:48 JST） | 1,192,632 | 1,190,528 | 2,104 |
| Ch8（10:39:48–10:42:40 JST） | 1,287,098 | 1,281,024 | 6,074 |

時間・使用量は各初稿の前後で取得した累積カウンタの差分。共通の原典下調べ・環境整備・待ち時間・後半の修正・回帰検査は含まない。
したがって上表を「1章全体の完了費用」とせず、残35章の所要時間・料金をこの値だけから外挿しない。使用量はトークンの観測値で、料金への換算はしていない。
共通の全体テストには1回約17〜19分を要した（最終run 1,119.41秒）。分量・文体を本人が決めたあと、原典照合・独立レビュー・便ごとの共通検査も含めて見積もる。

### 計画§5の検証1〜6

| # | 結果 | 証拠・制限 |
|---|---|---|
| 1 原典との照合 | 著者照合済み、独立検証待ち | [節別の照合範囲](validation/reading-guide/README.md)。GEの各節・頁・数値・記号を照合。Claudeの独立検証は未実施 |
| 2 数値 | PASS | 既存44 tests。入力・印刷値・未丸め値・単位・台帳ID・20箇所のテスト参照を [numerics.json](validation/reading-guide/numerics.json) に記録 |
| 3 読みやすさ | 著者点検済み、本人の読後判断待ち | 初出語・単位・丸め・分母・記号の再利用を点検。独立した初学者レビューはClaudeに引き継ぐ |
| 4 表示 | PASS | Playwright 1.56.0 / Chromium 145.0.7632.6、1280px・390px。2章の数式・ローカルリンク・外部通信・ページエラー・幅を検査し画像を目視 |
| 5 回帰 | PASS（台帳artifact検査は基準FAILのまま） | `make test` は11,907 passed / 76 skipped、SDEのtypecheck・lint・12 testsもPASS。lint・Book全build・既存31ページのMathJax・release・共有runtimeはPASS。台帳artifact検査は基準から同じ158エラー、新規0 |
| 6 進捗文書 | 更新済み | ROADMAPの「現在地」と「完了までの計画」をパイロット提出と同じcommitで更新 |

最初の表示検査はページ全体と外側の数式ブロックの幅だけを見ており、数式内部の横スクロールを見逃していた。
390pxで長い4式の欠けを目視で検出し、内側の `mjx-container` まで検査を拡張してFAILを確認したあと、4式を改行した。
強化後の検査は両幅でPASS。本文の数値・式の計算内容は同じで、元のnotebookや共有CSSは変更していない。
この数式の改行を全体test実行中に整え、その後の全Book再build・数式検査・表示検査・releaseを再実施した。pricingコードや元のnotebookは全体testの前後で不変。

TOC追加により既存ページのナビゲーションHTMLは変わる。元の30 notebookのarticle DOMが一致しても、ページ全体の厳密ハッシュの不変を意味しない。
台帳の既存FAILが残るため、受入証跡の全面的な鮮度や統合可能性を承認したとは扱わない。merge前にClaudeがこの点も独立確認する。

### 作業データ

最終Book・最小の表示画像・ログを外部データrootに保持する。再生成可能な分離プレビューと初回testの一時fixtureは削除した。
`du -shx /home/kazumasa/projects/_data/johnhull/reading-guide` は整理後 **319M**（整理前の観測は1.4G）。読取専用のF:マウントは `-x` で除外し、既存保管庫の容量を新規出力へ数えていない。
mainへのmergeとmainのpushはしない（作業branchは初稿e491b454までpush済み）。worktreeと外部データを修正差分の再検証・パイロット読後判断まで残す。

## 独立検証後の修正（2026-10-18）

指示書はmain `6c2daf2c` の `johnhull/docs/READING_GUIDE_REVIEW_2026-10-18.md` を指定パスから全文読了。
mainの変更は取り込まず、`codex/reading-guide` のe491b454から§2を修正した。

| 指摘 | 修正・扱い |
|---|---|
| N1・N2・N4・N5・N8 | 付録の境界をαへ訂正し、aとの別記号を明記。原典の1期間はT、デルタの分子の単位はオプション1単位あたりのドル。現実確率p*と、先物のa=1の理由を補足 |
| N3・N7 | プットへ移る理由はガイドの読み方として書き、原典の意図としない。GE第13章にない偶数・奇数段の振動の説明を削除 |
| N6・N9・N10 | 平均・分散からCRRの枝幅へ進む導出と初出語の定義を追加。丸めの注意を「数値の読み方」へ集約 |
| N11–N15 | subprime・ARM・teaser rate、ABX/TABX、LIBOR–OIS/TED、薄いBBB層の具体例を補足。BISのリンクを2019年4月の市中協議文書の名称・URLへ訂正 |
| N16・N17・N19・N20 | overviewの章順、push済み範囲の記録を訂正。表示検査の出力先を必須化しdisplay数式だけを幅検査する制限を明記。89.75%の恒等式と既存テストの許容差を区別 |
| N18 | 次回runtime更新時に各検査のcommit・時刻を残す要件をREADMEへ記録。今回manifestは変更しない |

変更した原典の頁・記号・歴史的数値はGE PDFの300dpi画像で照合し、画像は新しい外部出力rootだけに保存する。
新しい歴史的数値を `numerics.json` の `non_example_numbers` へ登録し、89.75%と損失5〜6%のBBB層は十進数で検算した。
任意のBaselの日程の一文は追加していない。指示書§3のstrict gate、bsm15のERROR、一般的なストーリーの出典の範囲は変更していない。

### 修正版の文字数

| 章 | ①従来方式（漢字・かな） | ②和文＋約物 | ③数式を除く可視文字 |
|---|---:|---:|---:|
| Ch13 | 10,330 | 11,359 | 12,582 |
| Ch8 | 5,989 | 6,634 | 7,752 |

①の原典1頁あたりはCh13約413字、Ch8約499字。①は初稿と同じUnicode範囲でソースを数える。
②③は生成HTMLのarticle本文からinline/display数式と見出しリンク記号を除き、②は漢字・かな＋UnicodeカテゴリーP、③は英数字・記号を含む空白以外を数える。
見出し・頁参照・リンクの表示文は含み、記法・URL・CSS生成のリスト番号は含めない。詳細と対象ファイルの指紋は [修正検証記録](validation/reading-guide/revision-2026-10-18.json)。

### 修正後の検査・計測

数値44 tests、出力先未指定/空白の停止確認、全Book build、既存31ページのMathJax、新規2章の1280px/390px検査、390pxの目視、共有runtime整合、lintはPASS。
通常releaseはPASS。全体testは11,907 passed / 76 skipped / 36 warnings、exit 0（pytest 1,132.99秒、make全体1,149.649秒）。SDEのtypecheck・lint・build・12 testsもPASS。
Bookは153 WARNING＋既存1 ERRORの計154件で従来と同じ。ガイド由来の警告は0。元の30 notebookのarticle DOMは初稿の生成物と一致する。
strict gateは今回は再実行せず、Claudeが基点と同じと確認した158件を保持する。
releaseの`--require-tracked`は修正中のoverviewとHEADの差で停止するため、最終commit後に実行し、`post-commit-checks.json`と最終報告へ結果を残す。
初稿の検証JSON・ログ・画像は保持し、新しい検査出力は `/home/kazumasa/projects/_data/johnhull/reading-guide/revision-20261018-n1-n20/` へ保存する。
Bookのbind mountは今回の `book/_build` へ切り替え、以前の `reading-guide/build/` は保持した。今回の容量実測は修正検証記録の `storage.du_shx` に残す。

修正依頼の受領からcommit前の記録締切りまで **2,301.540秒（38分22秒）**。原典照合・編集・道具の調整・待ち時間・回帰を含む。
使用量は入力 **16,399,192 tokens**（キャッシュ再利用16,124,544、再利用外274,648）、出力 **81,219 tokens**。
このchatの累積カウンタの差分で、料金ではない。記録締切りは2026-10-18 17:21:26 JST、最後に保存された使用量カウンタは17:20:41 JST。
締切り後の記録整理・commit・tracked release・最終応答は含めない。初稿だけの計測と区別し、残章の費用へこの値だけで外挿しない。

## 引き継ぎと未完了

- 基点 `7f668a39`、ブランチ `codex/reading-guide`。着手記録 `a30ace0e`、T0実測 `00b7f44d`。パイロット提出は本ファイルを含む同ブランチの最新commit（最終報告にcommit IDを記す）。
- 変更は新規ガイド2章、BookのTOCとoverview、共有runtime manifest、表示検査器、数値・検証・進捗文書。既存notebook・補足教材・hullkit・台帳の差分は0。
- Claudeへ：初稿e491b454の独立検証は完了。今回の差分、数値一覧と修正検証記録を基に§2の修正を再検証する。基準から残るartifact検査FAILの判断は指示書§3に保持する。
- 本人へ：2章の分量・文体・型を読んで判断する。**その判断までT2・B1–B6へ進まない。** 全37章ガイドの完成・節受入の更新・統合承認は行っていない。

原典PDFと抽出本文は新たに公開する成果物へ含めない。ガイドは節順を道標にした独自解説とし、原典の図表や連続した訳文は再掲しない。
