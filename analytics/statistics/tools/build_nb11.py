"""Builder for notebook 11 — Frequentist and Bayesian inference, side by side."""

from nbkit import code, md

cells = [
    md(r"""
# 11. 頻度論とベイズ — 同じデータ、2 つの流儀

> どちらが正しいかではなく、何を確率変数と見なすかが違う。

## この章で分かること

- 2 つの流儀の違いが **母数を定数と見なすか確率変数と見なすか** の 1 点に集約されること
- 信頼区間と信用区間は「何がランダムか」が逆であること
- 事前分布のパラメータは **疑似観測数** として読めて、データが増えると影響が消えること
- 極端な比率では、ベイズの信用区間が **頻度論の採点基準(被覆率)でも勝つ** こと
- p 値とベイズ因子は違う量で、同じデータから逆の結論が出ること
"""),
    code("""
import numpy as np
import plotly.io as pio
pio.renderers.default = "plotly_mimetype+notebook_connected"

from stats_textbook import (
    bridge, datasets, distributions, estimation, glm, intervals, plotting,
    processes, regression, simulation, testing
)

RANDOM_SEED = 0
print("setup ok")
"""),
    md(r"""
## 1. 違いは 1 点に集約される

頻度論は母数 $p$ を **定数** と見なす。分からないだけで、値は決まっている。
ランダムなのはデータの方であり、したがって手続きの方である。

ベイズは母数 $p$ を **確率変数** と見なす。データを見る前の信念が事前分布であり、
データを見た後の信念が事後分布である。

この 1 点から、以下がすべて従う。

| | 頻度論 | ベイズ |
|---|---|---|
| $p$ は | 定数 | 確率変数 |
| ランダムなのは | 区間 | 母数 |
| 事前分布 | 不要 | 必須 |
| 区間の読み方 | 手続きの性質 | $p$ についての確率 |
| 証拠の指標 | p 値 | ベイズ因子 |

「どちらが正しいか」ではなく「何を問いたいか」で選ぶ。
本章はその主張を、実測できる形にして確かめる。
"""),
    md(r"""
## 2. 同じデータで両方を計算する

10 回試して 8 回成功した。比率 $p$ をどう報告するか。
"""),
    code("""
k, n = 8, 10
p_hat = k / n

wald = intervals.wald_interval(p_hat, float(np.sqrt(p_hat * (1 - p_hat) / n)))
cred = bridge.credible_interval(k, n)                      # Jeffreys 事前

print(f"観測: {n} 回中 {k} 回成功   MLE = {p_hat:.4f}")
print(f"  頻度論 95% 信頼区間(Wald) = [{wald.lo:.4f}, {wald.hi:.4f}]")
print(f"  ベイズ 95% 信用区間        = [{cred.lo:.4f}, {cred.hi:.4f}]")
print(f"  ベイズ事後平均             = {bridge.posterior_mean(k, n):.4f}")
print(f"\\n信頼区間の上限が {wald.hi:.4f} -- 比率なのに 1 を超えている")
"""),
    code("""
plotting.interval_comparison([(8, 10), (80, 100), (800, 1000)])
"""),
    md(r"""
## 3. 読み方が違う

- **信頼区間**: 「この手続きを繰り返せば、95% の区間が真値を含む」(07 章)。
  ランダムなのは区間であり、いま手元にある 1 本の区間について確率は語れない
- **信用区間**: 「事後分布のもとで $p$ がこの範囲にある確率が 95%」。
  ランダムなのは母数の方であり、$p$ について確率を語れる

多くの人が信頼区間を後者の意味で読むが、それは頻度論の枠組みでは意味を持たない。
$p$ について確率を語りたいならベイズを使う必要があり、その代償が事前分布である。

Wald 区間が 1 を超えたのは偶然ではない。正規近似は $\hat{p} \pm z \cdot \mathrm{SE}$ を
実数直線上で計算するので、母数空間 $[0, 1]$ を知らない。
信用区間は $[0, 1]$ 上の分布の分位点なので、原理的に外に出られない。
"""),
    md(r"""
## 4. 事前分布は何をしているのか

共役なベータ二項では、事前分布のパラメータが **疑似観測数** として読める。
$\mathrm{Beta}(a, b)$ は「すでに $a$ 回の成功と $b$ 回の失敗を見た」に相当し、事後分布は

$$
p \mid k, n \sim \mathrm{Beta}(a + k,\; b + n - k)
$$

事後平均 $(a + k) / (a + b + n)$ は、事前平均と MLE の加重平均である。
重みは $a + b$ 対 $n$、つまり「事前分布は何件分のデータに相当するか」で決まる。
"""),
    code("""
plotting.prior_influence(ns=[5, 20, 100, 1000, 10_000], p_true=0.7)
"""),
    code("""
print(f"{'n':>7} {'MLE':>8} {'一様事前':>10} {'強い事前(平均0.8)':>18} {'強い事前との差':>16}")
for n in [5, 20, 100, 1000, 10_000]:
    k = int(0.7 * n)
    mle = k / n
    unif = bridge.posterior_mean(k, n, *bridge.PRIORS["uniform"])
    strong = bridge.posterior_mean(k, n, *bridge.PRIORS["strong_high"])
    print(f"{n:7d} {mle:8.4f} {unif:10.4f} {strong:18.4f} {abs(strong - mle):16.4f}")
print("\\n強い事前でも n = 10000 では MLE とほとんど違わない。")
print("事前分布が効くのはデータが少ないときだけである")
"""),
    code("""
plotting.posterior_slider([(4, 5), (14, 20), (70, 100), (700, 1000)])
"""),
    md(r"""
## 5. 信用区間は頻度論的被覆を持つか

ここが本章で最も面白いところである。
ベイズの区間を、頻度論の採点基準そのもの、つまり **被覆率** で採点してみる。

真の $p$ を固定して大量に標本を作り、各標本から区間を計算し、
真値を含んだ割合を数える。名目はどちらも 0.95 である。
"""),
    code("""
def wald_from_counts(s):
    k, n = int(s.sum()), s.size
    p = k / n
    se = float(np.sqrt(max(p * (1 - p), 1e-12) / n))
    return tuple(intervals.wald_interval(p, se))

def credible_from_counts(s):
    return tuple(bridge.credible_interval(int(s.sum()), s.size))

print(f"{'真の p':>8} {'n':>5} {'Wald 信頼区間':>16} {'Jeffreys 信用区間':>20}")
for p in [0.1, 0.3, 0.5, 0.8]:
    for n in [20, 100]:
        sampler = lambda m, rng, _p=p: (rng.random(m) < _p).astype(float)
        cw = simulation.coverage_probability(
            sampler, wald_from_counts, truth=p, n=n, n_reps=8000, seed=0).estimate
        cj = simulation.coverage_probability(
            sampler, credible_from_counts, truth=p, n=n, n_reps=8000, seed=0).estimate
        print(f"{p:8.1f} {n:5d} {cw:16.4f} {cj:20.4f}")
print("\\n名目はどちらも 0.95。")
print("極端な p では、ベイズの区間の方が頻度論の基準でも優れている")
"""),
    md(r"""
$p = 0.1$、$n = 20$ で Wald は 0.881、Jeffreys 信用区間は 0.957。
ベイズの答えが、頻度論の採点基準で勝っている。

これは「どちらの流儀が正しいか」という問いの立て方が成り立たないことを示している。
頻度論の基準で採点しても、ベイズの手続きの方が良い場合がある。
選ぶべきは流儀ではなく、目的に合った手続きである。
"""),
    md(r"""
```{admonition} 核心 — ひとことで
:class: tip
頻度論とベイズの違いは、母数を定数と見なすか確率変数と見なすかの 1 点に尽きる。
そこから区間の解釈も事前分布の要否も従う。
そして極端な比率では、ベイズの信用区間の方が頻度論の被覆率でも優れている。
どちらが正しいかではなく、何を問いたいかで選ぶ。
```
"""),
    md(r"""
## 6. p 値とベイズ因子

p 値は「$H_0$ が正しいとき、これほど極端なデータが出る確率」である。
ベイズ因子は「$H_1$ と $H_0$ でデータの起こりやすさが何倍違うか」である。

$$
\mathrm{BF}_{10} = \frac{P(\text{data} \mid H_1)}{P(\text{data} \mid H_0)}
$$

違う量なので、片方から他方を読むことはできない。
"""),
    code("""
from scipy import stats as sps

print(f"{'観測':>12} {'p 値(両側)':>12} {'ベイズ因子':>16} {'読み方':>12}")
for k, n in [(6, 10), (90, 100), (600, 1000)]:
    p_value = float(sps.binomtest(k, n, 0.5).pvalue)
    bf = bridge.bayes_factor_proportion(k, n, p0=0.5)
    verdict = "H1 支持" if bf > 3 else ("どちらとも" if bf > 1 / 3 else "H0 支持")
    print(f"{f'{k}/{n}':>12} {p_value:12.6f} {bf:16.4f} {verdict:>12}")
"""),
    md(r"""
### 6b. 同じデータで逆の結論が出る

各 $n$ について、p 値が 0.05 を切る最小の $k$ を取る。
つまり「ぎりぎり有意」なデータを $n$ ごとに集める。
頻度論はどの行でも「有意」と言う。ベイズ因子はどうなるか。
"""),
    code("""
from scipy import stats as sps

print("各 n で「ぎりぎり有意」になるデータを取る:")
print(f"{'n':>9} {'k':>9} {'p_hat':>8} {'p 値':>9} {'ベイズ因子':>12} {'ベイズの判定':>14}")
for n in [100, 1_000, 10_000, 100_000, 1_000_000]:
    for k in range(n // 2, n):
        if float(sps.binomtest(k, n, 0.5).pvalue) < 0.05:
            break
    p_value = float(sps.binomtest(k, n, 0.5).pvalue)
    bf = bridge.bayes_factor_proportion(k, n, p0=0.5)
    verdict = "H1 支持" if bf > 3 else ("どちらとも" if bf > 1 / 3 else "H0 支持")
    print(f"{n:9d} {k:9d} {k / n:8.4f} {p_value:9.5f} {bf:12.4f} {verdict:>14}")
print("\\nどの行も p 値は 0.05 を切っている(頻度論は「有意」と言う)。")
print("しかしベイズ因子は n が増えるほど H0 に傾き、n = 10^6 では 116 倍 H0 有利になる。")
print("これが Jeffreys-Lindley のパラドックス。同じデータ、逆の結論である")
"""),
    md(r"""
```{admonition} 実社会では
:class: note
医薬品の承認は頻度論の枠組みで動いている。第 1 種の誤りを規制当局が管理したいからである。
一方、A/B テストの逐次的な打ち切りや、データが少ない領域の意思決定ではベイズが実用的である。
事前分布を明示する義務が、逆に前提を議論の対象にできるという利点になる。
選択は哲学ではなく、誰が何を保証したいかで決まる。
```
"""),
    md(r"""
## 7. 落とし穴

- **無情報事前という言い訳**。事前分布を「無情報」と呼んでも責任は消えない。
  $p$ について一様な事前は $\log \frac{p}{1-p}$ については一様でない。
  無情報性は母数の取り方に依存する
- **ベイズ因子は事前分布に敏感**。$H_1$ の事前を広げるほど $H_0$ が自動的に有利になる
  (Lindley のパラドクス)。事前分布を書かずにベイズ因子だけ報告した数字は読めない
- **信用区間の確率は事前分布に条件付いている**。「95% の確率で真値が入る」は正しいが、
  それは選んだ事前分布のもとでの確率である
"""),
    code("""
print("H1 の事前分布を広げるとベイズ因子が下がる(Lindley のパラドクス):")
print(f"{'H1 の事前':>22} {'ベイズ因子(60/100)':>22}")
for a, b, label in [(50, 50, "Beta(50,50) 狭い"), (5, 5, "Beta(5,5)"),
                    (1, 1, "Beta(1,1) 一様"), (0.1, 0.1, "Beta(0.1,0.1) 広い")]:
    bf = bridge.bayes_factor_proportion(60, 100, p0=0.5, prior_a=a, prior_b=b)
    print(f"{label:>22} {bf:22.4f}")
print("\\n同じデータでも H1 の事前を広げるほど H0 が有利になる。")
print("ベイズ因子を報告するときは事前分布も一緒に報告しなければ意味がない")
"""),
    md(r"""
## 8. 演習

1. 一様事前 $\mathrm{Beta}(1, 1)$ と Jeffreys 事前 $\mathrm{Beta}(0.5, 0.5)$ で、
   信用区間の頻度論的被覆率を $p = 0.05, 0.5$ について比較せよ。どちらが名目 0.95 に近いか。
2. $p$ について一様な事前分布が、$\theta = \log \frac{p}{1-p}$ については一様でないことを、
   変数変換の Jacobian を使って示せ。数値的に密度を描いて確かめてもよい。
3. Wald 区間の代わりに Wilson 区間を使うと被覆率がどう変わるか測れ。
   $p = 0.1$、$n = 20$ で Jeffreys 信用区間と比べてどうか。
4. ベイズ因子と p 値が逆の結論を出すデータを、$n \le 1000$ の範囲で構成せよ。

解答は 13 章にある。
"""),
]
