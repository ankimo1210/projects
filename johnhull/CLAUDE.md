# CLAUDE.md — johnhull（モデルライブラリ / 学習ノート）

Hull 11e 全 37 章 + Beyond-Hull（vol 18–25）の教材・検証済みモデル実装群。
**参照実装カタログ + エージェント作業基盤**として使う。

## ナビゲーション（探す順番）

1. **`MODEL_INDEX.md`** — モデル・手法の横断カタログ。まずここを検索する。
   `package.module:symbol` 形式の実装参照・テスト・使用例 notebook・検証内容つき。
2. `ROADMAP.md` — 巻 ↔ Hull 章の対応と各巻の状態。
3. `release_manifest.json` — vol 18–25 の成果物配線（notebook / portal 図 / semantic tests / reference artifacts）。
4. `VALIDATION.md` — 検証の実行記録。**PASS = integration・数値恒等式・再現性のみ。
   モデル性能・市場予測力の承認ではない**（データは全て synthetic）。

## 実行・検証コマンド（すべて repo root から）

```bash
# scoped テスト
uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests johnhull/report/tests
uv run --no-sync --package deep-hedge-price pytest -q deep_hedge_price/tests

# 成果物ゲート
make hull-report            # オフラインポータル生成（johnhull/report/site/）
make hull-book              # Jupyter Book
make hull-artifacts-check   # reference artifact の semantic 一致 + byte 再現
make hull-notebooks-check   # vol 18-25 notebook の artifact-only 実行
make hull-release-check     # release 契約（scripts/verify_release.py）
```

acceptance は `johnhull/scripts/frontier_acceptance.py` がコミット済み配列から再計算する
（JSON のフラグを信用しない）。

## 規約と落とし穴

- **hullkit は torch-free。** torch 依存コード（学習・checkpoint・評価 pipeline）は
  `deep_hedge_price` 側に置く。`import hullkit` が torch を引き込んだら release 検証が落ちる。
- **notebook は artifact-only 実行。** build 中の学習・ネットワークダウンロード・GPU 検出は禁止。
  重い計算はコミット済み JSON+NPZ reference artifact（fingerprint 付き）から読む。
- **guard tests がドキュメントの鮮度を強制する:**
  `test_docstrings.py`（両パッケージ、公開 API docstring 100%）と
  `test_model_index.py`（両パッケージ、全モジュール掲載 + `module:symbol` 参照解決）。
  モジュールやシンボルを追加・改名したら MODEL_INDEX.md と docstring を同時に更新する。
- **PDF は 11e Global Edition。** 節・図番号・例題数値が US 版とズレる。引用は毎回 PDF と突合。
- 深掘り巻（13–17）の plotly 出力は mimetype-only — 静的 book には描画されない。
  対話可視化はポータル（`make hull-report`）が担当。
- build スクリプトは決定的 cell-id 方式。`build_*_notebook.py` は ruff exclude 対象。
- 巻を追加するときは `release_manifest.json` に notebook / portal 図 / semantic tests /
  references を登録し、`make hull-release-check` を通す。

## 境界（正本の所在）

| 対象 | 正本 |
|---|---|
| 金融教師（解析解 / COS / MC）・hard validation | `johnhull/hullkit` |
| torch 学習・checkpoint・walk-forward・経済評価 | `deep_hedge_price` |
| exact rBergomi / fBM / Hawkes の重い実験 | `~/projects/rough_volatility` |
| 執行アルゴ・RL 執行 | `~/projects/optimal_execution` |
