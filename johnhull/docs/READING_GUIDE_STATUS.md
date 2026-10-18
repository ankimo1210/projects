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
| T1 | 着手 | 外部分離プレビューの Ch13・Ch8を作成し、数値44 tests・2幅の表示を確認。本worktreeへの反映と最終回帰を行う |
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

原典PDFと抽出本文は新たに公開する成果物へ含めない。ガイドは節順を道標にした独自解説とし、原典の図表や連続した訳文は再掲しない。
