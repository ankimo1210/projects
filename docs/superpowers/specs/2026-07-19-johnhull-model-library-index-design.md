# johnhull モデルライブラリ化 — MODEL_INDEX / CLAUDE.md / docstring 整備 設計

- 日付: 2026-07-19
- ステータス: 承認済み設計（実装前）
- 対象: `/home/kazumasa/projects/johnhull`（hullkit 40 modules）+
  `/home/kazumasa/projects/deep_hedge_price`（38 modules）+ volumes 1–25
- ブランチ: `codex/johnhull-beyond-hull-g8` に積む
- 背景: vol 18–25 実装完了（G8 release PASS）により、johnhull 系は 78 モジュール・
  約 150 のモデル/手法実装を持つ。ユーザーはこれを**参照実装カタログ + エージェント作業基盤**
  として使いたい。現状、モデル→実装の横断インデックスと johnhull/CLAUDE.md は存在せず、
  公開 API docstring は hullkit 77% / deep_hedge_price 48%。

## 1. 目的と成功基準

**目的:** agentic coding が「このモデルの検証済み実装はどこ？」に 1 ホップで答えられる状態にする。

**成功基準:**

1. モデル名（例: SABR, Deep BSDE 相当, HARNet, LVR）から実装・テスト・使用例 notebook・
   検証内容へ、`johnhull/MODEL_INDEX.md` 経由で到達できる。
2. 両パッケージの公開モジュール/関数/クラスの docstring カバレッジ 100% をテストが保証する。
3. インデックスの鮮度（全モジュール掲載・参照解決）をテストが保証し、将来の巻追加で腐らない。
4. 既存の全ゲート（294+88 tests、ruff、`make hull-release-check`）が引き続き通る。

## 2. 成果物

### 2.1 `johnhull/MODEL_INDEX.md`（英語）

- 冒頭に "How to use this index (for agents)" — 実装参照記法
  `package.module:symbol`、grep のヒント、関連ドキュメント（ROADMAP / release_manifest /
  VALIDATION）の役割分担。
- ドメイン別セクション（順序固定）:
  1. Core pricing (BS, trees, Monte Carlo)
  2. Volatility & smile (GARCH, implied vol, Heston, SABR, COS/Fourier)
  3. Stochastic calculus & SDE
  4. Numerical methods (FD, variance reduction, QMC, AAD)
  5. Rates & swaps (curves, swaps, IR options, RFR post-LIBOR)
  6. Risk & credit (VaR/ES, credit, XVA, copula)
  7. Exotics & martingales
  8. ML surrogates & differential ML
  9. Calibration & arbitrage-aware surfaces
  10. Volatility forecasting & hedging decisions (HAR → Transformer, deep hedging)
  11. SPX/VIX & path-dependent volatility
  12. 0DTE
  13. Crypto market structure (perp funding, liquidation, AMM/LVR)
  14. Climate & energy (carbon, weather, PPA)
  15. Infrastructure & utilities — モデルでないモジュール（nbplot, plotly_viz, teaching,
      cli, config, notebook builders 等）を役割一言つきで列挙する受け皿
- エントリ形式（セクションごとに 1 表）:
  `| Model | Theory | Implementation | Tests | Notebook | Validation |`
  - Theory: Hull 11e 章番号（GE 版）または論文（著者+年、既存 spec の検証済みリンクを再利用）
  - Implementation: `hullkit.sabr:hagan_lognormal_vol` 形式。複数可
  - Tests: テストファイル名（相対パス）
  - Notebook: 使用例のある volume 番号（例: vol 05, 19）
  - Validation: 検証の一言（例: "pinned to Hull Table 20.2" / "identity checks < 1e-12"）
- 末尾 "Cross-project pointers" 節: 正本が johnhull 外にあるモデル
  （exact rBergomi/fBM/Hawkes → `rough_volatility`、AC/OW/反応型 LOB/PPO →
  `optimal_execution`、ポートフォリオ/バックテスト → `quantkit`）。
- 推定 100–150 エントリ。網羅の定義は「両パッケージの全 78 モジュールが
  Implementation 列または §15 Infrastructure に登場する」こと（テストで担保、§2.4）。

### 2.2 `johnhull/CLAUDE.md`（日本語プローズ + 英語識別子）

1. **ナビゲーション:** モデル探索は MODEL_INDEX.md → 巻↔章対応は ROADMAP.md →
   vol 18–25 の成果物配線は release_manifest.json → 検証状態は VALIDATION.md。
2. **実行・検証コマンド:** scoped pytest（`uv run --no-sync --package hullkit pytest -q
   johnhull/hullkit/tests johnhull/report/tests` 等）、`make hull-report / hull-book /
   hull-artifacts-check / hull-notebooks-check / hull-release-check`。uv は repo root から。
3. **規約と落とし穴:**
   - hullkit は torch-free（torch 依存コードは deep_hedge_price 側へ）
   - notebook は artifact-only 実行（build 中の学習・ダウンロード・GPU 検出禁止）
   - artifact は fingerprint 付き JSON+NPZ、acceptance は `frontier_acceptance.py` で再計算
   - PDF は 11e Global Edition（節・図番号が US 版とズレる）
   - 深掘り巻の plotly は mimetype-only 出力（静的 book には出ない、ポータルが対話面）
   - build スクリプトは決定的 cell-id、`build_*_notebook.py` は ruff exclude

### 2.3 docstring 補完（公開 API 100%）

- 対象: hullkit 未記載 90 件 + deep_hedge_price 未記載 118 件（`ast` 監査による）。
- スタイル: 1 行要約（命令形）。シグネチャから自明でない引数・返り値のみ Args/Returns を追加。
  名前のあるモデルを実装する関数には理論典拠を一言
  （論文なら "Hagan et al. (2002) lognormal SABR approximation"、教科書なら
  "Hull 11e §19.6 delta hedging" の形式）。各パッケージの既存文体に合わせる。
- **コードロジックには一切触れない**（docstring 挿入のみの diff）。

### 2.4 鮮度テスト

- `johnhull/hullkit/tests/test_docstrings.py` / `deep_hedge_price/tests/test_docstrings.py`:
  公開モジュール・公開関数/クラス（`_` 始まりを除く）の docstring 100% を assert。
- `johnhull/hullkit/tests/test_model_index.py`:
  (a) hullkit 全モジュールが MODEL_INDEX.md の Implementation 列に登場、
  (b) インデックス中の `hullkit.*:symbol` 参照が import + getattr で解決できる。
- `deep_hedge_price/tests/test_model_index.py`:
  同様に `deep_hedge_price.*:symbol` 参照の掲載と解決を検証（torch 依存はこちら側のみ）。
- MODEL_INDEX.md のパスは両テストから repo root 相対で解決する。

## 3. 非対象（YAGNI）

- 機械可読 JSON/YAML インデックス（markdown + テストで十分）
- インデックスの自動生成スクリプト
- API 安定性保証・semver（利用形態は参照カタログであり import 契約ではない)
- volumes 1–17 notebook の内容改変、release artifact の再生成

## 4. 検証

1. 新規テスト含む scoped suite: hullkit + report、deep_hedge_price をフル実行。
2. `ruff check` / `ruff format --check`（対象ファイル）。
3. `make hull-release-check`（既存契約への無影響確認）。
4. 監査スクリプト再実行で docstring 100% を数値確認。

## 5. 実装順

1. docstring 補完（hullkit → deep_hedge_price、モジュール単位でバッチ、逐次テスト）
2. test_docstrings ×2 追加（この時点で green）
3. MODEL_INDEX.md 作成（ドメイン順、既存 spec の検証済み文献リンクを転記）
4. test_model_index ×2 追加（掲載網羅 + 参照解決）
5. CLAUDE.md 作成
6. 全ゲート実行 → docs/test でコミット分割
