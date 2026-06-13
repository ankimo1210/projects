# ニューラルネットの中身 — 関数近似から Transformer まで

Jupyter Notebook ベースのニューラルネットワーク教科書。
ニューラルネットを「ブラックボックス」ではなく、
**線形変換と非線形変換の合成・微分可能な計算グラフ・勾配降下で最適化される系・表現学習機械**
として、直感 → 最小限の数式 → NumPy/PyTorch 実装 → 可視化 → 実験 → 演習 の順で学ぶ。

- 対象: Python の基礎・線形代数の基礎・微分の基礎を知っている読者
- 方針: 標準的で軽量なデータセットのみ使用。ノート PC で全 Notebook が走る。乱数 seed 固定
- 本文は日本語、コードとコメントは英語、LaTeX 内に日本語を入れない

## 章構成(全 14 Notebook)

| Notebook | 内容 | 状態 |
|---|---|---|
| `01_overview_and_function_approximation` | 関数近似・線形 vs 非線形・隠れ層が空間をほぐす | ✅ |
| `02_calculus_computation_graphs_backprop` | 連鎖律・計算グラフ・自作 autograd・勾配チェック | ✅ |
| `03_mlp_from_scratch` | NumPy で Linear/活性化/損失/SGD/学習ループを自作 | ✅ |
| `04_training_dynamics_and_stabilization` | 初期化・BatchNorm/LayerNorm・Dropout・残差・正則化 | ✅ |
| `05_convolutional_neural_networks` | 畳み込み・プーリング・CNN(MNIST/Fashion-MNIST) | ✅ |
| `06_sequence_models_rnn_lstm_gru` | RNN/LSTM/GRU・系列予測・勾配減衰 | ✅ |
| `07_attention_and_transformers` | QKV・自己注意・マルチヘッド・Transformer・文字レベル LM | ✅ |
| `08_representation_learning_autoencoders` | AE/DAE/VAE・潜在空間・補間・t-SNE | ✅ |
| `09_generative_models_gan_diffusion` | GAN・モード崩壊・拡散の前向き/逆過程 | ✅ |
| `10_modern_llm_concepts` | トークナイズ・次トークン予測・RLHF/DPO・RAG・LoRA・スケーリング則 | ✅ |
| `11_appendix_cpu_vs_gpu` | 付録: CPU vs GPU 速度比較(行列積・fp16・CNN/Transformer 学習ステップ) | ✅ |
| `13_efficient_attention_state_space` | 付録: 効率的注意(FlashAttention)・線形注意・SSM/Mamba | ✅ |
| `14_capstone_three_lenses` | キャップストーン: 1つの回帰を3冊の視点で(勾配降下が閉形式リッジ解に収束) | ✅ |
| `12_exercise_solutions` | 付録: 全演習(64 問)の解答 | ✅ |

共通コードは `src/nn_textbook/` にまとめている
(`datasets` / `plotting` / `widgets` / `autograd` / `layers` / `models` / `training` / `metrics` / `benchmark`)。

CPU と GPU の速度比較は付録 `11_appendix_cpu_vs_gpu` と `nn_textbook.benchmark`
(ウォームアップ・CUDA 同期・複数試行の最小値を扱うベンチユーティリティ)で行える。
GPU が無い環境でも CPU のみの結果でそのまま実行できる。

## 環境構築

### この workspace 内で使う場合(推奨)

リポジトリルート(`~/projects`)の uv workspace のメンバー。

```bash
cd ~/projects
make install          # = uv sync --all-packages
```

`torch` / `torchvision` は CUDA 12.8 ビルド(RTX 5080 / Blackwell 対応)を
ルートの `[tool.uv.sources]` で固定している。GPU が無くても CPU で動く。

### 単体で使う場合

```bash
cd analytics/neural_net
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
# CUDA torch が必要なら:
#   pip install --index-url https://download.pytorch.org/whl/cu128 torch torchvision
```

## JupyterLab の起動

```bash
cd ~/projects
uv run jupyter lab analytics/neural_net/notebooks/
```

## Notebook の実行

各 Notebook は上から順に実行できる(乱数 seed 固定、CPU 実行で各数分以内)。
ipywidgets を使うセルは JupyterLab 上でのみ動く。主要なインタラクションには
**Plotly スライダー版**(07 注意温度・08 潜在補間・09 拡散ノイズ)があり、こちらは静的 HTML でも動く。

**GPU で実行する場合**(04〜09 章対応): 環境変数を立てて起動するだけ。

```bash
NN_TEXTBOOK_GPU=1 uv run jupyter lab analytics/neural_net/notebooks/
```

コミット済みの出力は再現性のため CPU 実行で固定している。

```bash
cd ~/projects/analytics/neural_net
for nb in notebooks/*.ipynb; do
  uv run jupyter nbconvert --to notebook --execute --inplace "$nb"
done
```

CPU 実行での目安: 大半は数十秒、最も重い 09(GAN/拡散)で約 3 分。
MNIST / Fashion-MNIST は初回のみ `_data/` に自動ダウンロード(各 ~30MB、以後キャッシュ)。
合成データはすべてローカル生成で外部依存なし。

## Jupyter Book のビルド

Notebook は出力込みでコミットされ、ビルド時には再実行しない
(`book/_config.yml` で `execute_notebooks: "off"`)。`book/notebooks` は `../notebooks` への symlink。

```bash
cd ~/projects/analytics/neural_net
uv run jupyter-book build book/
# 出力: book/_build/html/index.html
```

## テスト

```bash
cd ~/projects
uv run pytest analytics/neural_net/tests -q
```

`autograd`(数値勾配チェック)・NumPy 層(PyTorch を参照実装に一致検証)・
MLP のスモークトレーニング・データセットの shape/再現性・ベンチマーク・widgets/モデルをカバー(53 本)。

## データの差し替え(bring your own data)

画像は MNIST / Fashion-MNIST(実データ)を既定で使用。テキストは内蔵ミニコーパスが既定だが、
`nn_textbook.datasets.load_text_corpus(path="your.txt")` に自分のコーパス(Tiny Shakespeare 等)の
パスを渡せば 07・10 章の言語モデルをそのまま差し替えられる(ダウンロード不要)。

## 関連教材

姉妹教材(同じ Jupyter Book 流儀の analytics シリーズ):

- [`analytics/linear_algebra`](../linear_algebra/) — 線形代数。
  本書の 08 章(AE と PCA)・10 章(LoRA と低ランク近似)は、その 05 章「行列分解・SVD・PCA」と地続き。
- [`analytics/bayesian`](../bayesian/) — ベイズ推定。
  本書の正則化(weight decay)は事前分布、VAE の変分推論はベイズ推論そのもの(その 05・08 章)。
- [`analytics/report`](../report/) — **統合インタラクティブポータル**。3教材の代表可視化を
  オフラインで束ねるショーケース(`make report`)。本書の決定境界の学習過程・注意の温度・学習曲線の
  スライダーもここで一望できる。

## 今後追加すべき内容

- 残る ipywidgets デモ(畳み込みカーネル・学習率など)の Plotly 化
- ブラウザでのウィジェット動作の手動確認(コールバックはテスト済み、視覚的描画は未確認)
