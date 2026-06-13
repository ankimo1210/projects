# ラプラス変換の風景 — 時間・複素周波数・システムの言語

Jupyter Notebook ベースのラプラス変換教科書プロジェクト。
ラプラス変換を「変換表の暗記」ではなく、

> 時間変化を、複素周波数 $s=\sigma+i\omega$ の世界で代数的に扱うための道具

として、図・可視化・Python 実験から理解することを目指す。中心テーマは
**成長・減衰・振動をまとめて扱い、微分方程式・信号・システムを代数的に理解する**こと。

- 対象: 大学 1〜2 年生 / 微分積分と線形代数を学んだ読者 / ODE・制御・回路・信号・確率に関心のある読者
- 方針: 定義から始めない。「なぜ時間関数を別の領域へ移すのか」「なぜ微分方程式が代数になるのか」から入る
- 各章は Basic(最低限)/ Applied(Python 実装・応用)/ Advanced(証明・発展)の 3 層構成
- 厳密な証明・収束条件は Advanced Notes に分離

## 章構成

| Notebook | 内容 |
|---|---|
| `00_overview` | 全体像・なぜ学ぶか・$s$ 領域・フーリエとの違い・読み方・環境準備 |
| `01_exponential_decay_complex_frequency` | 指数・成長/減衰/振動・複素指数・複素周波数・$s$ 平面の直感 |
| `02_definition_basic_properties` | 定義・収束域(ROC)・線形性・微分/積分/シフト・初期値定理 |
| `03_inverse_laplace_partial_fractions` | 逆変換・変換表・部分分数(単純極/重根/複素極)・SymPy |
| `04_solving_odes_with_laplace` | ODE を代数に・1階/2階・減衰/強制振動・ステップ(数値解と一致確認) |
| `05_convolution_impulse_response_transfer_functions` | 畳み込み定理・インパルス応答・伝達関数・$Y=HX$・LTI |
| `06_poles_zeros_stability` | 極と零点・$s$ 平面・極と応答・左半面/虚軸/右半面・安定性 |
| `07_control_systems_and_circuits` | RC/RLC・ステップ/インパルス応答・フィードバック・Bode の入口 |
| `08_applications_probability_signals_finance` | 確率の MGF・割引現在価値(Gordon 成長と ROC)・待ち行列の入口 |
| `09_capstone_three_lenses` | キャップストーン: 1つの2次系を ODE/畳み込み/極の3視点で解き一致を確認 |
| `10_exercise_solutions` | 付録: 01〜08 章 演習の解答例 |

重点実装は **01・02・04・05・06・09**。03・07・08 は実内容に加え「今後の拡張(TODO)」を明記している。

共通関数は `src/laplace_book/` にまとまっている:

- `transforms.py` — 記号(SymPy)/数値(求積)のラプラス変換、変換表、微分則の検証、
  数値逆変換(Gaver-Stehfest / Talbot)
- `systems.py` — 伝達関数、極/零点、安定性判定、ステップ/インパルス/強制応答、直列・フィードバック、
  根軌跡(root locus)、畳み込み
- `circuits.py` — RC/RLC 回路の伝達関数と減衰パラメータ
- `plotting.py` — 指数・減衰振動・$s$ 平面・極と応答・畳み込み・Bode・根軌跡、Plotly の $|F(s)|$ サーフェス
- `widgets.py` — ipywidgets による複素周波数 / 2 次系 / フィードバックの対話的探索
- `datasets.py` — 合成信号(ステップ・近似インパルス・減衰正弦など、seed 固定)

## 環境構築

### この workspace 内で使う場合(推奨)

リポジトリルート(`~/projects`)の uv workspace のメンバーになっているので:

```bash
cd ~/projects
make install          # = uv sync --all-packages
```

### 単体で使う場合

```bash
cd analytics/laplace
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## JupyterLab の起動

```bash
cd ~/projects
uv run jupyter lab analytics/laplace/notebooks/
```

## Notebook の実行・再生成

各 Notebook は上から順に実行できる(乱数は seed 固定)。Notebook は `tools/build_notebooks.py` で
**生成される成果物**で、出力込みでコミットされている。全 Notebook を再生成 → 再実行するには:

```bash
cd ~/projects/analytics/laplace
export PYTHONPATH=$PWD/src
python tools/build_notebooks.py                       # regenerate .ipynb from source
for nb in notebooks/0*.ipynb; do
  jupyter nbconvert --to notebook --execute --inplace "$nb"
done
```

ipywidgets を使うセルは JupyterLab 上でのみ操作できる(静的 HTML では各章の対話図の直前に
同じ対象の静的図を置いてあるので、本文だけで意味が分かる)。

## Jupyter Book のビルド

Notebook は出力込みでコミットされており、ビルド時には再実行しない
(`book/_config.yml` で `execute_notebooks: "off"`)。`book/notebooks` は `../notebooks` への symlink。

```bash
cd ~/projects/analytics/laplace
uv run jupyter-book build book/
# 出力: book/_build/html/index.html
```

## テスト

```bash
cd ~/projects
uv run pytest analytics/laplace/tests -q
# 単体環境なら: cd analytics/laplace && PYTHONPATH=src pytest tests -q
```

主要な共通関数(変換則・伝達関数・安定性・回路)に対する検証テストが入っている
(数値ラプラス変換 vs 解析解、畳み込み定理、ODE のラプラス解 vs `solve_ivp` など)。

## データについて

外部ダウンロードには依存しない(入力信号はすべて `datasets.py` の seed 固定合成データ)。

## 関連教材

姉妹教材(同じ Jupyter Book 流儀の analytics シリーズ):

- [`analytics/differential_equation`](../differential_equation/) — 微分方程式。本書の 04 章(ODE → 代数)は
  その時間領域の解法と表裏一体。極の位置(06 章)は相平面の固定点分類に対応する。
- [`analytics/fourier`](../fourier/) — フーリエ変換。$s=i\omega$(虚軸)に制限すると周波数応答になる。
- [`analytics/linear_algebra`](../linear_algebra/) — 固有値・固有関数の視点($e^{st}$ は微分作用素の固有関数)。

## 今後追加すべき内容

- 03 章: ヘヴィサイド展開定理の手計算、`scipy.signal.residue` による数値部分分数、むだ時間 $e^{-as}$ の逆変換
- 07 章: PID 設計、位相余裕/ゲイン余裕、ナイキスト線図、オペアンプ回路(根軌跡は実装済み)
- 08 章: ラプラス-スティルチェス変換と M/M/1、債券・期間構造、特性関数との対応、SDE 生成作用素
- 全体: 両側変換・$z$ 変換への橋渡し、アニメーション(変換パイプライン・根軌跡・共振)、
  `analytics/report` ポータルへの代表可視化の登録
