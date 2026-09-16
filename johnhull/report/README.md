# johnhull 可視化ポータル(インタラクティブ HTML)

johnhull の Hull 11e ノートで学ぶ価格付け・リスク管理を束ねる、
**オフライン自己完結のインタラクティブ静的サイト**を生成するジェネレータ。
`analytics/report` と同じ設計(jinja2 + plotly)。

- ランディング + コンセプトギャラリー + 12テーマ別ショーケース（全94図、exotics 14図）+ 統合(背骨)ページ
- 図は `hullkit.plotly_viz`、内部教材モジュール `hullkit._binary_lesson` / `hullkit._lookback_lesson` / `hullkit._shout_lesson`、またはvol 18–28のversioned reference artifactから生成。共有ソースに加え、値・操作・実画面を検査する
- **カーネル不要・ネット不要**: plotly はローカル同梱、図はブラウザ内で動く(スライダー/ホバー/ズーム)

## 生成

リポジトリ root から:

```bash
make hull-report   # -> johnhull/report/site/index.html
make hull-book     # johnhull の Jupyter Book(教科書本体)をビルド
```

または直接:

```bash
PYTHONPATH=johnhull/report uv run --no-sync python -m report_builder.build
```

出力された `site/index.html` をブラウザで開くだけ(オフラインで動作)。`site/` は gitignore 済み。

## 図を追加する

`report_builder/figures.py` の `FIGURES` に `FigureSpec` を1つ足すだけ
(`build` には `hullkit.plotly_viz` の `plotly_*` を渡す)。新テーマは `BOOKS` に `BookMeta` を1行。
A1–A4に加え、A5–A8のML・市場構造・新市場の図もここへ登録される。

## テスト

```bash
uv run --no-sync pytest johnhull/report/tests -q
```

全図ビルドの完走・registry由来の全ページ生成・`Plotly.newPlot` 数・**外部 URL ゼロ**を検証する。

§26.12 シャウトの4図は保存済み数値を共有し、ビルド時に価格探索を実行しない。
`johnhull/scripts/verify_shout_lesson_browser.cjs` はビルド済み Book/portal の実メニューを操作し、
1440/1000px の両方で13状態を独立参照値と照合する。既存 Playwright/Chromium を
`PLAYWRIGHT_MODULE` / `CHROMIUM_BIN` で指定して実行し、
`docs/validation/section-26-12/browser-m4b-check.json` に実際の検査範囲・ハッシュ・18画像を記録する。
Portal の HTTP(S) は遮断し、Book の既存 MathJax リクエストは許可して記録する。
