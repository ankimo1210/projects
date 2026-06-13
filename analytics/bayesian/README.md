# ベイズ推定の体験 — 信念の更新装置としての統計

Jupyter Notebook ベースのベイズ推定教科書。
単なる数式解説ではなく、**直感 → 数式 → Python 実装 → シミュレーション → インタラクティブ可視化 → 実務応用 → 演習** を一体化した教材。

- 対象: Python と基礎的な確率統計は少し分かるが、ベイズ推定を本格的に学び直したい人
- 全章を貫くフロー: **仮説 → 事前分布 → データ → 尤度 → 事後分布 → 予測・意思決定**
- 本文は日本語、コードは英語、LaTeX 内に日本語なし。乱数は seed 固定(`default_rng(42)`)
- 外部 API・ダウンロード依存なし(データはすべて合成・再現可能)

$$
p(\theta \mid x) = \frac{p(x \mid \theta)\, p(\theta)}{p(x)}
$$

## 章構成(全 14 Notebook)

| Notebook | 内容 | 状態 |
|---|---|---|
| `00_overview` | ベイズとは何か・頻度主義との違い・コイン投げ予告 | ✅ |
| `01_bayes_theorem_and_probability` | 条件付き確率・医療検査の PPV・スパム判定・基準率の錯誤 | ✅ |
| `02_distributions_and_simulation` | 頻出 7 分布の役割・パラメータ探索・大数の法則 | ✅ |
| `03_beta_binomial_model` | **コア**: コイン→CVR→A/B テスト、事前/尤度/事後、信用区間 | ✅ |
| `04_conjugate_priors_and_posterior_predictive` | 共役 4 ペア・データと事前の綱引き・事後予測分布 | ✅ |
| `05_bayesian_linear_regression` | ベイズ線形回帰・信用/予測バンド・Ridge = 正規事前の MAP | ✅ |
| `06_hierarchical_bayes` | **コア**: 部分プーリング・shrinkage・8 schools | ✅ |
| `07_mcmc_intuition` | MH を 20 行で自作・提案幅と受容率・Gibbs・HMC/NUTS | ✅ |
| `08_pymc_practical_modeling` | PyMC + ArviZ 実践(R-hat・ESS・PPC、閉形式と照合) | ✅ |
| `09_model_checking_and_applications` | PPC・LOO-CV・ベイズファクター・実務応用 5 本 | ✅ |
| `11_variational_inference_advi` | 変分推論(ADVI)・ELBO・平均場の限界・VAE との接続 | ✅ |
| `12_bayesian_optimization_thompson` | ベイズ最適化・Thompson サンプリング・多腕バンディット | ✅ |
| `13_capstone_three_lenses` | キャップストーン: 1つの回帰を3冊の視点で(事後平均 = リッジ = MAP) | ✅ |
| `10_exercise_solutions` | 全演習(49 問)の解答 | ✅ |

共通コードは `src/bayes_textbook/`
(`conjugacy` / `distributions` / `simulation` / `models` / `visualization` / `widgets` / `utils`)。
小さなサンプル CSV は `data/`(すべて seed 固定で再生成可能)。

## セットアップ

### この workspace 内で使う場合(推奨)

リポジトリルート(`~/projects`)の uv workspace のメンバー。

```bash
cd ~/projects
make install          # = uv sync --all-packages
```

### 単体で使う場合

```bash
cd analytics/bayesian
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## 実行方法

```bash
cd ~/projects
uv run jupyter lab analytics/bayesian/notebooks/
```

各 Notebook は上から順に実行できる(00→03 は各 1 分以内、08 の PyMC のみ数分)。
ipywidgets のデモは JupyterLab 上でのみ動く。主要なインタラクションには
**Plotly スライダー版** があり、こちらは静的 HTML でも動く。

## Jupyter Book のビルド

Notebook は出力込みでコミット、ビルド時は再実行しない(`execute_notebooks: "off"`)。

```bash
cd ~/projects/analytics/bayesian
uv run jupyter-book build book/
# 出力: book/_build/html/index.html
```

## テスト

```bash
cd ~/projects
uv run pytest analytics/bayesian/tests -q
```

共役更新の閉形式 vs モンテカルロ一致、ベイズ回帰 vs Ridge の等価性、
自作 MCMC のモーメント検証、widgets のコールバック発火などをカバー。

## トラブルシューティング

**PyMC が `Python.h: No such file or directory` で失敗する**(08 章) —
pytensor の C バックエンドが Python 開発ヘッダを要求するため。2 つの解決策:

1. **推奨(sudo 不要)**: numba バックエンドを使う。08 章の Notebook は冒頭で
   `os.environ.setdefault("PYTENSOR_FLAGS", "cxx=,mode=NUMBA")` を設定済みなので、
   そのまま動く。
2. C バックエンドを使いたい場合: `sudo apt install python3.12-dev`

**PyMC が無い環境** — 00〜07 章は PyMC なしで完結する。08〜09 章の PyMC セルは
import 失敗時に案内を表示してスキップする。

## 学習順序

00 → 01 → 02 → **03(コア)** と進み、ベイズ更新の気持ちよさを体感してから
04 → 05 → **06(コア)** → 07 → 08 → 09。演習の解答は 10。

## 関連教材

- [`analytics/linear_algebra`](../linear_algebra/) — 線形代数。05 章ベイズ回帰の行列計算の基礎
- [`analytics/neural_net`](../neural_net/) — ニューラルネット。正則化 = 事前分布(05 章)、VAE の変分推論と地続き
- [`analytics/report`](../report/) — **統合インタラクティブポータル**。3教材の代表可視化を
  オフラインで束ねるショーケース(`make report`)。本書の信念更新・MCMC 収束・事後予測帯の
  スライダーもここで一望できる。

## 今後追加すべき内容

