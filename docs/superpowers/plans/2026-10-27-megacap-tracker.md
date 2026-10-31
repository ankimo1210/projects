# Megacap tracker implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task by task. The user delegated requirements and implementation on 2026-10-27; proceed inline without another approval gate.

**Goal:** Mag7の株価・決算・PER/PBR・財務状況を比較できるローカルHTMLトラッカーを提供する。

**Architecture:** 既存market-researchの依存を使ってYahoo Financeを明示取得し、小さなJSON snapshotを置換保存する。HTML/CSS/JavaScriptは自己完結とし、標準ライブラリのlocalhostサーバーから更新でき、書き出したHTMLはオフラインでも閲覧できる。

**Tech Stack:** Python 3.12、既存pandas/yfinance、stdlib HTTP server、vanilla JavaScript、claude-report tokens。

**Spec:** 本書の「要件」が今回の委任範囲。既存7画面・取得CLIの挙動は変更しない。

## 要件・完了条件

- 対象はAAPL/MSFT/GOOGL/AMZN/META/NVDA/TSLA。USD。普通株クラス違いを重複計上しない。
- 株価と価格時点、PER(TTM)/予想PER/PBR/PSR/EV・EBITDA、売上・純利益・利益率・営業CF・設備投資・FCF、現預金等と有利子負債、自己資本比率を表示。
- 損益・CFのTTMは連続する4四半期だけを合計。期間、通貨、欠損を保つ。赤字EPS・非正のBPSから倍率を作らない。
- 決算予定は情報提供元の予定として表示。公式IRリンクで確認可能にする。実績とアナリスト予想を混同しない。
- 銘柄検索、数値ソート、ウォッチ登録、期間切替、銘柄詳細、CSV/HTML保存、テーマ切替、モバイル表示。
- ページ閲覧は通信せず、CLIの--refreshまたは更新ボタンの明示操作で取得。リアルタイム配信・売買助言・外部通知・公開・定時ジョブは追加しない。
- データは`_data/market-research/megacap-tracker/`に約1MB以下を想定して1セットだけ保存。取得失敗は旧版を時刻付きで保持し、失敗を可視化。

## Global constraints

- 新しい本番依存を追加しない。共通CSS全文をHTMLに埋め込み、追加の色は既存tokenで指定。
- 現在のクリーンなcheckoutで対象プロジェクトと本計画だけを変更。既存の公開APIは変更しない。
- 既存のREADMEとdocs/STATUS.mdに導線・実行結果を記載。コミット・push・公開は今回実施しない。

## Review focus

1. 赤字/ゼロ/NaN、通貨違い：倍率や利回りを捏造しない。
2. 四半期欠落とCFの符号：不完全TTMは空欄、FCFは営業CFから設備投資支出を控除。
3. 一部/全件取得失敗：新しい取得時刻で旧価格を新鮮に見せない。
4. 外部データのHTML埋込みとlocalhost更新：スクリプト注入を避け、外部originから更新不可。
5. 空の検索/ウォッチ、保存HTML、狭幅/ダーク：実際の操作と描画を確認。

## Task 1: 正規化・取得・保存

Files: `market-research/src/market_research/megacap.py`, `market-research/tests/test_megacap.py`

- [x] `build_company`の手計算テストを作成。PER=100/5=20、PBR=100/25=4、CF40・投資-10の4期FCF=120を確認。非正の分母、欠損四半期、通貨違い、取得失敗の旧版保持を検査。
- [x] `uv run --no-sync pytest market-research/tests/test_megacap.py -q`で未実装の失敗を確認。
- [x] `build_company`, `collect_snapshot`, `load_snapshot`, `save_snapshot`を実装。入力はyfinanceの辞書/DataFrame、出力は有限値またはnullのJSON。
- [x] 同テストを通し、7社の実データを小範囲で取得して欠損・時点・サイズを確認。

## Task 2: 自己完結HTMLとローカル更新

Files: `market-research/web/megacap.html`, `market-research/src/market_research/megacap_server.py`, `market-research/scripts/megacap_tracker.py`, `market-research/tests/test_megacap_server.py`

- [x] サーバーのGETが取得処理を呼ばないこと、JSON埋込、Host/Origin制限、POSTの明示ヘッダー、保存版をテストし未実装の失敗を確認。
- [x] `render_html(snapshot)`と`TrackerServer`を実装。`uv run --no-sync python market-research/scripts/megacap_tracker.py --refresh`で起動、`--export PATH --no-serve`でHTML出力。
- [x] HTMLに比較表・価格/四半期チャート・決算予定・出典/定義を実装。検索/ソート/ウォッチ/CSV/HTML保存を連動。
- [x] localhostを開き、ヘッドレスブラウザで全操作、オフライン版、390px幅、明暗を確認。

## Task 3: 統合検証・文書・引渡し

Files: `market-research/docs/MEGACAP_TRACKER.md`, `market-research/README.md`, `market-research/docs/STATUS.md`

- [x] 実行方法、指標定義、取得元/時点、予想/実績と会計期間の限界を記載。
- [x] member suite、変更PythonのRuff check/format、JS syntax、git diff --check、描画確認を実行。
- [x] 実装全体をレビューし指摘を修正。成果物のサイズ、検証結果、残りをSTATUSへ反映。
- [x] localhostと保存HTMLを引き渡す。

## 完了記録（2026-10-27）

member suite337件成功（新規20）。Ruff/JS構文/差分検査と実データ7社のブラウザ受入成功。独立レビューの全取得失敗時保持・設備投資表示の2件を再現して修正。最終状態とデータ制約はmarket-research/docs/STATUS.mdに反映。
