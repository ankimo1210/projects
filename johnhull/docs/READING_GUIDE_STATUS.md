# 章ごとに読むガイド：T0・T1 の状態

更新日：2026-10-18。計画：[READING_GUIDE_PLAN_2026-10-18.md](READING_GUIDE_PLAN_2026-10-18.md)。

## 目標と停止条件

既存の notebook・節別補足教材・節台帳を変更せず、Book に独自の日本語解説を追加する。
今回は T0 の影響実測と T1 の Ch13・Ch8 だけを扱う。ユーザーの読後判断と Claude の独立検証を待ち、T2・B1–B6 には進まない。
main への merge・push は行わない。

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
| T1 | 本文作成・自己検査済み、ここで停止 | Ch13・Ch8をBookへ反映。数値44 tests・2幅の表示・lint・全体test・releaseを確認。本人の読後判断とClaudeの独立検証待ち |
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

### T1 の提出物と計測

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
mainへのmerge・pushは行わず、worktreeと外部データをパイロット読後判断・独立検証まで残す。

## 引き継ぎと未完了

- 基点 `7f668a39`、ブランチ `codex/reading-guide`。着手記録 `a30ace0e`、T0実測 `00b7f44d`。パイロット提出は本ファイルを含む同ブランチの最新commit（最終報告にcommit IDを記す）。
- 変更は新規ガイド2章、BookのTOCとoverview、共有runtime manifest、表示検査器、数値・検証・進捗文書。既存notebook・補足教材・hullkit・台帳の差分は0。
- Claudeへ：計画§4、上の原典照合表・数値一覧・`t0.json`・`verification.json` を基に、主張・数値・GE頁・翻訳類似性・初学者の読みやすさ・基準から残るartifact検査FAILを独立確認する。
- 本人へ：2章の分量・文体・型を読んで判断する。**その判断までT2・B1–B6へ進まない。** 全37章ガイドの完成・節受入の更新・統合承認は行っていない。

原典PDFと抽出本文は新たに公開する成果物へ含めない。ガイドは節順を道標にした独自解説とし、原典の図表や連続した訳文は再掲しない。
