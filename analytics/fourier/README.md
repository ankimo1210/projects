# フーリエ解析の風景 — 波・周波数・分解の言語

> シリーズ索引: [analytics 教材一覧](../README.md)

Jupyter Notebook ベースのフーリエ解析教科書プロジェクト。
フーリエ解析を「FFT のレシピ集」ではなく、

> 関数を直交する波の基底で展開する理論 — 複雑な信号を単純な振動成分に分解し、
> **構造・エネルギー・滑らかさ・時間変化** を読み解く

ものとして、図・可視化・Python 実験から理解することを目指す。

- 対象: 大学 1〜2 年生 / 微分積分と線形代数を学んだ読者 / PDE・信号処理・画像・物理・ML・金融時系列に関心のある読者
- 方針: 定義から始めない。「なぜ波に分解したいのか」「分解すると何が見えるのか」から入る
- 各章は Basic(最低限)/ Applied(Python 実装・応用)/ Advanced(証明・発展)の 3 層構成
- 厳密な証明・収束条件は Advanced Notes に分離

## 章構成

| Notebook | 内容 |
|---|---|
| `00_overview` | 全体像・時間/周波数領域・級数/変換/DFT/FFT の違い・読み方・環境準備 |
| `01_waves_complex_numbers_inner_products` | 正弦波・複素指数・Euler・関数の内積・直交性(関数版の線形代数) |
| `02_fourier_series_periodic_functions` | フーリエ級数・三角/複素係数・矩形/のこぎり/三角波・Gibbs 現象 |
| `03_convergence_energy_parseval` | 収束の種類・L² 誤差・Parseval・滑らかさ ↔ 係数減衰 |
| `04_fourier_transform_nonperiodic_functions` | フーリエ変換・逆変換・ガウス/矩形・不確定性原理 |
| `05_convolution_filtering_distributions` | 畳み込み・畳み込み定理・ロー/ハイ/バンドパス・平滑化 |
| `06_dft_fft_sampling_aliasing` | DFT/FFT・周波数ビン・Nyquist・aliasing・窓関数・スペクトル漏れ |
| `07_time_frequency_stft_wavelets_intro` | STFT・スペクトログラム・窓幅のトレードオフ・wavelet 入口 |
| `08_pde_spectral_methods` | 熱/波動方程式・モード分離・スペクトル微分・スペクトル法 |
| `09_applications_signal_image_finance_ml` | 音・画像 2D FFT・圧縮・金融時系列の探索的解析と限界・ML 接続 |

重点実装は **01・02・03・06・08**。00・04・05・07・09 は実内容に加え「今後の拡張(TODO)」を明記している。

共通関数は `src/fourier_book/` にまとまっている:

- `signals.py` — 正弦/余弦・複素指数・矩形/のこぎり/三角波・チャープ・ガウスパルス・加法ノイズ(seed 固定)
- `transforms.py` — DFT 行列 / 高速 FFT・振幅/パワースペクトル・フーリエ係数(三角/複素)・再構成・STFT
- `filters.py` — 周波数マスク(ロー/ハイ/バンド)・畳み込み(線形/巡回)・ガウス/移動平均平滑化
- `spectral.py` — 周期境界の波数・スペクトル微分・熱/波動/Poisson 方程式のスペクトル解
- `plotting.py` — 信号/スペクトル/部分和/係数減衰/スペクトログラム/2D FFT の matplotlib 図(ラベルは英語)
- `widgets.py` — ipywidgets による正弦波/波の和/矩形波部分和/ローパスの対話的探索
- `datasets.py` — 合成データ(多重トーン・チャープ・2トーンバースト・テスト画像・金融風系列、seed 固定)

## 環境構築

### この workspace 内で使う場合(推奨)

リポジトリルート(`~/projects`)の uv workspace を使う。**fourier をルート `pyproject.toml` の
`[tool.uv.workspace].members` に `"analytics/fourier"` として追加** したうえで:

```bash
cd ~/projects
make install          # = uv sync --all-packages
```

> まだ members に未登録でも、`tests/conftest.py` が `src/` を `sys.path` に追加するため
> テストと Notebook はそのまま動く(下記)。

### 単体で使う場合

```bash
cd analytics/fourier
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

09 章で実画像(`scikit-image`)を使いたい場合は `pip install -e ".[extras]"`。

## JupyterLab の起動

```bash
cd ~/projects
uv run jupyter lab analytics/fourier/notebooks/
```

## Notebook の実行・再生成

各 Notebook は上から順に実行できる(乱数は seed 固定)。Notebook は `tools/build_notebooks.py` で
**生成される成果物**で、出力込みでコミットされている。全 Notebook を再生成 → 再実行するには:

```bash
cd ~/projects/analytics/fourier
export PYTHONPATH=$PWD/src
python tools/build_notebooks.py                       # regenerate .ipynb from source
for nb in notebooks/0*.ipynb; do
  jupyter nbconvert --to notebook --execute --inplace "$nb"
done
```

ipywidgets を使うセルは JupyterLab 上でのみ操作できる(静的 HTML では各対話図の直前に
同じ対象の静的図を置いてあるので、本文だけで意味が分かる)。

## Jupyter Book のビルド

Notebook は出力込みでコミットされており、ビルド時には再実行しない
(`book/_config.yml` で `execute_notebooks: "off"`)。`book/notebooks` は `../notebooks` への symlink。

```bash
cd ~/projects/analytics/fourier
uv run jupyter-book build book/
# 出力: book/_build/html/index.html
```

## テスト

```bash
cd ~/projects
uv run --no-sync pytest analytics/fourier/tests -q
# 単体環境なら: cd analytics/fourier && PYTHONPATH=src pytest tests -q
```

主要な共通関数に検証テストが入っている(naive DFT vs `np.fft`、振幅スペクトルの校正、
DFT の Parseval、畳み込み定理、スペクトル微分 vs 解析微分、熱方程式の単一モード解析解との一致など)。

## データについて

外部ダウンロードには依存しない(入力信号・画像はすべて `datasets.py` の seed 固定合成データ)。
金融デモも合成系列が既定だが、`datasets.load_price_series(path="your.csv")` で実データに差し替えられる。

## 関連教材

姉妹教材(同じ Jupyter Book 流儀の analytics シリーズ):

- [`analytics/laplace`](../laplace/) — ラプラス変換。$s=i\omega$(虚軸)に制限すると本書の周波数応答になる。
- [`analytics/linear_algebra`](../linear_algebra/) — 内積・正射影・固有値分解。本書の「関数版の線形代数」の土台。
- [`analytics/differential_equation`](../differential_equation/) — 微分方程式。本書 08 章のスペクトル法と時間領域解法は表裏一体。

## 今後追加すべき内容

- 04 章: Plancherel の数値検証、変換性質(微分/平行移動/スケーリング)の表、SymPy による解析変換、δ・定数の超関数変換
- 05 章: δ 関数と Green 関数の入口、理想フィルタのリンギングと実用フィルタ(Butterworth)、特徴抽出デモ
- 07 章: 連続 wavelet 変換(スカログラム)、定 Q 変換、窓の再構成(COLA)
- 09 章: 実画像/音声(WAV・メルスペクトログラム)、Fourier features の回帰デモ、ウェルチ法とサロゲート検定
- 全体: 演習解答ノート(姉妹本の `08_exercise_solutions` 相当)、2D フーリエの理論、キャップストーン(1 つの信号を級数・変換・DFT の 3 視点で)
