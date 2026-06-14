# analytics — 体験型インタラクティブ教科書シリーズ

数学・機械学習のトピックを「直感 → 図 → 最小限の数式 → Python 実装 → 実験 → 演習」の順で
学ぶ、Jupyter Book ベースの教科書群。共通の流儀で揃えており、多くは uv workspace メンバー
(`differential_equation` は `ode-book` / `pde-book` の2サブパッケージがメンバー、`report` のみ
メンバー外)。

- 本文は日本語、コード・コメント・識別子は英語、**LaTeX 内に日本語を入れない**
- 乱数は seed 固定で再現可能・**外部ダウンロード依存なし**(データは合成・同梱)
- Notebook は出力込みでコミット / 図ヘルパは純関数でテスト付き
- 可視化はライブカーネル不要の **クライアントサイド Plotly**(静的 HTML でも動くスライダー)

## 教材

| ディレクトリ | 内容 | Notebook |
|---|---|---|
| [`linear_algebra/`](linear_algebra/) | 線形代数の風景 — 空間・情報・変換の言語 | 13 |
| [`neural_net/`](neural_net/) | ニューラルネットの中身 — 関数近似から Transformer まで | 14 |
| [`bayesian/`](bayesian/) | ベイズ推定の体験 — 信念の更新装置としての統計 | 14 |
| [`fourier/`](fourier/) | フーリエ解析の風景 — 波・周波数・分解の言語 | 10 |
| [`laplace/`](laplace/) | ラプラス変換の風景 — 時間・複素周波数・システムの言語 | 11 |
| [`differential_equation/`](differential_equation/) | 微分方程式 — ODE / PDE の2分冊（変化・流れ・場の言語） | 18 (ODE 9 / PDE 9) |
| [`machine_learning/`](machine_learning/) | 機械学習の実践 — 正しく定式化し、検証し、解釈する | 14 |

> Notebook 数は時点の目安(各教材は随時加筆)。

## ポータル

| ディレクトリ | 内容 |
|---|---|
| [`report/`](report/) | **統合インタラクティブ HTML ポータル**。線形代数・NN・ベイズ・ラプラス・機械学習の代表可視化をギャラリーに束ね、フーリエ・微分方程式(ODE/PDE)へもカード+教科書リンクで導線化。横断キャップストーン付き・オフライン自己完結。`make report` で生成 |

## ビルド

リポジトリ root から:

```bash
make books     # 各 Jupyter Book をビルド(<book>/book/_build/html/)
make report    # 統合ポータルをビルド(analytics/report/site/index.html、オフライン動作)
```

個別ビルド: `uv run jupyter-book build analytics/<book>/book/`
(`differential_equation` は `ode-book/` / `pde-book/`)。
`book/_build/` と `report/site/` はビルド成果物(gitignore)。

## テスト

各教材の図・数値ヘルパには `tests/` がある。root から:

```bash
uv run pytest analytics/<book>/tests -q
```
