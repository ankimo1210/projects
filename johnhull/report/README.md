# johnhull 可視化ポータル(インタラクティブ HTML)

johnhull の Hull 11e ノートで学ぶ価格付け・リスク管理を束ねる、
**オフライン自己完結のインタラクティブ静的サイト**を生成するジェネレータ。
`analytics/report` と同じ設計(jinja2 + plotly)。

- ランディング + コンセプトギャラリー + テーマ別ショーケース + 統合(背骨)ページ
- 図はすべて `hullkit.plotly_viz` の `plotly_*` ビルダーから生成 → 本文と常に同期(単一の真実源)
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
A1–A4 深掘り(確率解析 / 確率ボラ&Fourier / 高度な数値 / XVA)の図はここに順次登録される。

## テスト

```bash
uv run --no-sync pytest johnhull/report/tests -q
```

全図ビルドの完走・6ページ生成・`Plotly.newPlot` 数・**外部 URL ゼロ(完全オフライン)**を検証する。
