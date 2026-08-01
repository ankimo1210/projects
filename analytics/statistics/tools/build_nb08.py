"""Builder for notebook 08 — Hypothesis testing."""

from nbkit import code, md

cells = [
    md(r"""
# 08. 仮説検定 — 何を保証し、何を保証しないのか

> p 値は仮説が正しい確率ではない。帰無仮説の下でデータがこれほど極端になる確率である。

## この章で分かること

- 検定の構造と、$\alpha$ が**こちらの選ぶ数**であること
- 帰無仮説の下で p 値は**一様分布**する。だから小さい p 値は珍しくない
- **検出力** — 効果量・標本サイズ・$\alpha$ の 3 つで決まる
- 検定を繰り返すと偽の「有意」が量産されること
- **Bonferroni と BH は違うものを制御している**
"""),
    code("""
import numpy as np
import plotly.io as pio
pio.renderers.default = "plotly_mimetype+notebook_connected"

from stats_textbook import (
    datasets, distributions, estimation, intervals, plotting, processes, simulation, testing
)

RANDOM_SEED = 0
print("setup ok")
"""),
    md(r"""
## 1. 検定の構造

**帰無仮説** $H_0$ と**対立仮説** $H_1$ を立て、検定統計量が棄却域に落ちたら $H_0$ を棄却する。
誤りは 2 種類ある。

| | $H_0$ が真 | $H_1$ が真 |
|---|---|---|
| 棄却しない | 正しい | **第 2 種の誤り**($\beta$) |
| 棄却する | **第 1 種の誤り**($\alpha$) | 正しい(検出力 $1-\beta$) |

重要なのは、$\alpha$ が**データから決まる数ではなく、こちらが選ぶ数**だということである。
「第 1 種の誤りをこれ以下に抑える」という設計目標であり、検定はそれを守るように作られている。

守られているか確かめよう。
"""),
    code("""
print(f"{'alpha':>7} {'実測の棄却率':>14} {'モンテカルロ 95% 区間':>26}")
for alpha in [0.01, 0.05, 0.10]:
    r = simulation.rejection_rate(
        lambda n, rng: rng.normal(0.0, 1.0, n),
        lambda s: testing.t_test(s).pvalue,
        alpha=alpha, n=20, n_reps=20_000, seed=RANDOM_SEED,
    )
    lo, hi = r.ci95()
    print(f"{alpha:7.2f} {r.estimate:14.4f} {f'[{lo:.4f}, {hi:.4f}]':>26}")
print("\\n帰無仮説が真のとき、棄却率は指定した alpha に一致する。これが検定の設計目標")
"""),
    md(r"""
## 2. p 値の定義と 4 つの誤解

**定義**: 帰無仮説が正しいとして、観測されたものと同じかそれ以上に極端なデータが出る確率。

$$
p = P(\,|T| \ge |t_{\text{obs}}| \mid H_0\,)
$$

**誤解 1**: 帰無仮説が正しい確率である。→ 違う。$P(\text{data} \mid H_0)$ であって
$P(H_0 \mid \text{data})$ ではない(01 章の検察官の誤謬と同じ構造)。

**誤解 2**: 効果の大きさを表す。→ 違う。標本サイズを増やせばどんな小さな差でも p は下がる(§7)。

**誤解 3**: 再現性の指標である。→ 違う。$p = 0.04$ の研究を再現しても、また 0.04 付近になるとは限らない。

**誤解 4**: $p > 0.05$ は「差が無い」ことの証明である。→ 違う。検出力が足りないだけかもしれない。

誤解の根を断つ最短経路は、帰無仮説の下での p 値の分布を見ることである。
"""),
    code("""
pvals = simulation.sampling_distribution(
    lambda s: testing.t_test(s).pvalue,
    lambda n, rng: rng.normal(0.0, 1.0, n),
    n=20, n_reps=20_000, seed=1,
)
print("帰無仮説が真のときの p 値の分布(理論上は一様):")
for lo in [0.0, 0.2, 0.4, 0.6, 0.8]:
    share = float(np.mean((pvals >= lo) & (pvals < lo + 0.2)))
    print(f"  [{lo:.1f}, {lo + 0.2:.1f}) に {share:.4f}(理論 0.2000)")
print(f"\\np < 0.05 の割合 = {float(np.mean(pvals < 0.05)):.4f}")
print("\\n一様ということは、p = 0.04 も p = 0.96 も同じくらい起きるということである。")
print("小さい p 値は「珍しい」のではなく、「珍しいと定義した領域」に入っただけである")
"""),
    md(r"""
## 3. Neyman–Pearson 補題

単純仮説 $H_0: \theta = \theta_0$ 対 $H_1: \theta = \theta_1$ に限れば、最良の検定が一意に決まる。

**主張** 水準 $\alpha$ の検定のうち検出力を最大にするのは、尤度比

$$
\Lambda(x) = \frac{L(\theta_1 \mid x)}{L(\theta_0 \mid x)}
$$

がある閾値を超えたら棄却する検定である。

「どの統計量を使うべきか」という問いに、少なくとも単純仮説の場合には答えが出ている。
$t$ 検定や $\chi^2$ 検定が使われるのは、慣習ではなくこの種の最適性に基づいている。

## 4. 検出力 — 見つけられる能力

$1 - \beta$。効果量 $d$、標本サイズ $n$、水準 $\alpha$ の 3 つで決まる。
"""),
    code("""
plotting.power_curves(effects=[0.2, 0.5, 0.8], ns=[5, 10, 20, 40, 80, 160], alpha=0.05)
"""),
    code("""
print(f"{'効果量':>8} {'検出力 0.8 に必要な n':>24}")
for effect in [0.2, 0.35, 0.5, 0.8, 1.2]:
    print(f"{effect:8.2f} {testing.required_n(effect, alpha=0.05, power=0.8):24d}")
print("\\n効果量が半分になると必要な n は約 4 倍。小さな差の検出が高くつく理由がこれ")
"""),
    md(r"""
検出力は非心 $t$ 分布から解析的に計算できる。
その値が正しいかどうかは、実際に検定を 2 万回走らせれば確かめられる。
"""),
    code("""
effect, n = 0.6, 25
analytic = testing.power_t_test(effect, n, alpha=0.05)
sim_r = simulation.rejection_rate(
    lambda m, rng: rng.normal(effect, 1.0, m),
    lambda s: testing.t_test(s).pvalue,
    alpha=0.05, n=n, n_reps=20_000, seed=3,
)
lo, hi = sim_r.ci95()
print(f"非心 t による解析値      = {analytic:.4f}")
print(f"実際に 2 万回検定した実測 = {sim_r.estimate:.4f}   95% 区間 [{lo:.4f}, {hi:.4f}]")
print(f"解析値は実測の区間の中: {lo <= analytic <= hi}")
"""),
    md(r"""
## 5. 多重比較 — 検定を繰り返すとどうなるか

$m$ 回の独立な検定で少なくとも 1 回誤る確率は $1 - (1-\alpha)^m$ である。
$m = 20$ で 0.64、$m = 200$ でほぼ 1 になる。

効果が**まったく無い**データに 200 回検定してみよう。
"""),
    code("""
plotting.phacking_demo(n_tests=200, n=30, seed=4)
"""),
    code("""
rng = np.random.default_rng(4)
pvals = np.array([testing.t_test(rng.normal(0, 1, 30)).pvalue for _ in range(200)])
raw = int((pvals < 0.05).sum())
print("200 回すべて帰無仮説が真(効果はゼロ):")
print(f"  補正なしで p < 0.05      : {raw:3d} 件   (期待値 200 * 0.05 = 10 件)")
print(f"  Bonferroni 補正後        : {int(testing.bonferroni(pvals).sum()):3d} 件")
print(f"  Benjamini-Hochberg 補正後 : {int(testing.benjamini_hochberg(pvals).sum()):3d} 件")
print(f"\\n少なくとも 1 回誤る確率(理論) = {1 - 0.95 ** 200:.6f}")
print(f"補正なしの {raw} 件は「発見」ではなく、検定を 200 回行った当然の結果である")
"""),
    md(r"""
## 6. Bonferroni と BH は違うものを制御している

- **Bonferroni** は **FWER**(family-wise error rate)を制御する。
  「1 つでも誤って棄却する確率」を $\alpha$ 以下にする。閾値は $\alpha/m$
- **BH** は **FDR**(false discovery rate)を制御する。
  「棄却したもののうち誤りの割合」の期待値を $\alpha$ 以下にする

前者の方が強い保証で、その分だけ保守的になる。
本物の効果が混じっている状況で、両者がどう振る舞うかを見よう。
"""),
    code("""
rng = np.random.default_rng(5)
fdps, bh_power, bonf_power = [], [], []
for _ in range(300):
    null_p = rng.uniform(0, 1, 180)                      # 180 個は効果なし
    alt_p = np.array([testing.t_test(rng.normal(1.0, 1.0, 20)).pvalue for _ in range(20)])
    pvals = np.concatenate([null_p, alt_p])
    is_null = np.concatenate([np.ones(180, bool), np.zeros(20, bool)])

    bh_rej = testing.benjamini_hochberg(pvals, alpha=0.1)
    fdps.append(testing.false_discovery_proportion(bh_rej, is_null))
    bh_power.append(float((bh_rej & ~is_null).sum() / 20))
    bonf_power.append(float((testing.bonferroni(pvals, 0.1) & ~is_null).sum() / 20))

print("180 個は効果なし、20 個は本物の効果(効果量 1.0、n = 20):")
print(f"  BH(alpha = 0.1)の平均 FDP     = {np.mean(fdps):.4f}   <- 0.1 以下に抑えられている")
print(f"  BH が本物を拾えた割合          = {np.mean(bh_power):.4f}")
print(f"  Bonferroni が本物を拾えた割合   = {np.mean(bonf_power):.4f}   <- 保守的すぎて取り逃がす")
"""),
    md(r"""
探索的な解析では、いくつか偽陽性が混じっても本物を拾いたい。そういう場面では BH が使われる。
確証的な試験では、1 つの誤りも許したくない。そこでは Bonferroni 系が使われる。
**どちらが正しいかではなく、何を守りたいかで選ぶ。**
"""),
    md(r"""
```{admonition} 核心 — ひとことで
:class: tip
p 値は帰無仮説が正しい確率ではない。帰無仮説の下でこれほど極端なデータが出る確率である。
帰無仮説が真なら p 値は一様分布するので、0.05 を切る結果は 20 回に 1 回は必ず出る。
検定を何回行ったかを数えずに p 値を読むことはできない。
```
"""),
    md(r"""
```{admonition} 実社会では
:class: note
A/B テストのダッシュボードで有意になるまで毎日眺める運用は、
検定回数を数えずに繰り返しているのと同じである。
事前に標本サイズを決めておくか、逐次検定の枠組みを使うかのどちらかが要る。
医学研究の事前登録制度も、解析の自由度を封じて同じ問題に対処している。
```
"""),
    md(r"""
## 7. 落とし穴

### 有意差と実質的な差は別物

標本を増やせば、どんなに小さな差も有意になる。p 値は大きさを語らない。
"""),
    code("""
rng = np.random.default_rng(6)
big = rng.normal(0.02, 1.0, 100_000)      # 真の効果 0.02 = 実質ゼロ
r = testing.t_test(big)
ci = intervals.t_interval(big)
print("n = 100,000、真の効果 0.02")
print(f"  p 値 = {r.pvalue:.6f}   -> 有意")
print(f"  95% 信頼区間 = [{ci.lo:.4f}, {ci.hi:.4f}]   -> 差は 0.02 前後で実質ゼロ")
print("\\n有意性と重要性は別である。だから p 値の隣には必ず区間を書く")
"""),
    md(r"""
### $p > 0.05$ は「差が無い」ことの証拠ではない

検出力が足りなければ、本物の効果があっても検出できない。
「有意差なし」と報告するときは、どの程度の効果なら検出できたはずかを併記する。
"""),
    code("""
effect = 0.3
for n in [10, 30, 100]:
    power = testing.power_t_test(effect, n, alpha=0.05)
    print(f"効果量 {effect}、n = {n:3d}: 検出力 = {power:.4f}"
          f"  -> {1 - power:.1%} の確率で見逃す")
print("\\nn = 10 では本物の効果があっても 9 割方見逃す。")
print("この状況の「有意差なし」に情報はほとんど無い")
"""),
    md(r"""
## 8. 演習

1. $m$ 回の独立な検定で少なくとも 1 回誤る確率 $1-(1-\alpha)^m$ を導き、
   シミュレーションで確認せよ。検定が独立でない場合はどうなるか。
2. 検出力 0.8 に必要な $n$ を効果量の関数として図示し、$n \propto 1/d^2$ を確認せよ。
3. 帰無仮説が真である割合を変えて(たとえば 50% と 95%)、BH の FDR 制御と
   検出力がどう変わるかを測れ。
4. 逐次的に検定を繰り返す(毎日データを足して検定する)と、
   第 1 種の誤り率がどこまで上がるか測れ。
5. 同じデータに対する $t$ 検定と順列検定(07 章)の p 値を、
   正規分布と裾の重い分布の両方で比較せよ。
"""),
]
