# Analytics 教材ポータル(インタラクティブ HTML レポート)

`analytics/` の3教材(線形代数 / ニューラルネット / ベイズ推定)を束ねる、
**オフライン自己完結のインタラクティブ静的サイト**を生成するジェネレータ。

- ランディング + コンセプトギャラリー + 教材別ショーケース + 3冊横断キャップストーン
- 図はすべて各教材の `plotly_*` ビルダーから生成 → 本文と常に同期(単一の真実源)
- **カーネル不要・ネット不要**:plotly はローカル同梱、図はブラウザ内で動く(スライダー/ホバー/ズーム)

## 生成

リポジトリ root から:

```bash
make report      # -> analytics/report/site/index.html
```

または直接:

```bash
cd analytics/report && PYTHONPATH=. uv run python -m report_builder.build
```

出力された `site/index.html` をブラウザで開くだけ(オフラインで動作)。
`site/` はビルド成果物なので gitignore 済み(各 Jupyter Book の `book/_build/` と同様)。

「教科書を開く」リンクは各 Jupyter Book のビルド出力(`<book>/book/_build/html/`)を指すので、
あわせてビルドしておくと相互に行き来できる:

```bash
make books       # 3冊の Jupyter Book を一括ビルド
```

## 構成

```
report/
  report_builder/
    figures.py   # 図レジストリ: 各 plotly_* ビルダー + メタ(タイトル/所属書/解説/NEW)
    render.py    # 図 -> 埋め込み HTML 断片 -> jinja テンプレートでページ組立
    build.py     # CLI: python -m report_builder.build [out_dir]
  templates/     # base / index / gallery / book / integration (jinja2)
  assets/style.css
  tests/         # ビルドが完走し、外部参照ゼロ(オフライン)であることを検証
  site/          # 生成物(gitignore)
```

## 図を追加する

`report_builder/figures.py` の `FIGURES` に `FigureSpec` を1つ足すだけ。
`build` には「`go.Figure` を返す関数」を渡す(教材の `plotly_*` を seed 固定のデモ入力で呼ぶ)。
新しい教材図を本文に足したら、ここにも一行足せばギャラリーに載る。

## テスト

```bash
uv run pytest analytics/report/tests -q
```

全図ビルドの完走・6ページ生成・`Plotly.newPlot` 数・**外部 URL ゼロ(完全オフライン)**を検証する。
ブラウザでの視覚描画のみ手動確認(図は plotly JS のクライアントサイド描画)。

関連: [線形代数](../linear_algebra/README.md) · [ニューラルネット](../neural_net/README.md) · [ベイズ推定](../bayesian/README.md)
