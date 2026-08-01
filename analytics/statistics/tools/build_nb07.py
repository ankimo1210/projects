"""Builder for notebook 07 — Confidence intervals and the bootstrap."""

from nbkit import code, md

cells = [
    md(r"""
# 07. 信頼区間とブートストラップ — 「95%」は何についての主張か

> 信頼区間の 95% は、この区間についての確率ではない。手続きについての長期頻度である。

## この章で分かること

- 信頼区間の**正しい読み方**と、最もよくある誤解
- 被覆確率は導出を信じるものではなく、**実測するもの**であること
- なぜ $t$ 分布を使うのか。正規分位点で代用すると何が起きるか
- **ブートストラップ** — 標準誤差の公式が無い統計量に区間を付ける
- percentile 法と BCa 法の違い、そして**どちらも万能ではない**こと
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
## 1. よくある誤解から始める

「95% 信頼区間 $[1.2, 3.4]$ が得られた」とき、次の読み方は **誤り** である。

> 真値がこの区間に入る確率は 95% である。

頻度論では真値 $\theta$ は定数であって確率変数ではない。
だから「$\theta$ が $[1.2, 3.4]$ に入る確率」は 0 か 1 のどちらかで、95% ではない。
ランダムなのは**区間の方**である。データが変われば区間も変わる。

**正しい読み方**:

> この手続きを繰り返すと、作られる区間のうち 95% が真値を含む。

抽象的に聞こえるので、実際に 100 本作って数えてみよう。
"""),
    code("""
plotting.coverage_intervals(n_intervals=100, n=12, truth=0.0, seed=RANDOM_SEED)
"""),
    md(r"""
青が真値(破線)を含んだ区間、赤が外した区間である。

**どの 1 本を取っても「95%」ではない。** 含むか含まないかのどちらかである。
95% という数字は、100 本を並べて初めて意味を持つ。

そして「95%」は導出された主張なので、実測して確かめられる。本書の第 2 原則である。
"""),
    code("""
r = simulation.coverage_probability(
    lambda n, rng: rng.normal(0.0, 1.0, n),
    lambda s: tuple(intervals.t_interval(s)),
    truth=0.0, n=12, n_reps=20_000, seed=1,
)
lo, hi = r.ci95()
print(f"実測被覆率 = {r.estimate:.4f}")
print(f"モンテカルロ 95% 区間 = [{lo:.4f}, {hi:.4f}]")
print(f"名目値 0.95 は区間の中: {lo <= 0.95 <= hi}")
"""),
    md(r"""
## 2. なぜ $t$ 分布なのか

真の標準偏差 $\sigma$ が分かっていれば

$$
\frac{\bar X - \mu}{\sigma/\sqrt{n}} \sim N(0, 1)
$$

だが、実際には $\sigma$ も推定しなければならない。標本標準偏差 $S$ で置き換えると

$$
\frac{\bar X - \mu}{S/\sqrt{n}} \sim t_{n-1}
$$

になる(03 章)。分母がぶれる分だけ裾が重い。
それを無視して正規分位点 1.96 を使うと、区間が狭すぎて被覆率が落ちる。
どのくらい落ちるかを測ろう。
"""),
    code("""
def normal_interval(s):
    half = 1.96 * s.std(ddof=1) / np.sqrt(s.size)
    return float(s.mean() - half), float(s.mean() + half)

print(f"{'n':>5} {'t 区間':>12} {'正規分位点':>12}")
for n in [5, 10, 30, 100]:
    a = simulation.coverage_probability(
        lambda m, rng: rng.normal(0, 1, m), lambda s: tuple(intervals.t_interval(s)),
        truth=0.0, n=n, n_reps=8000, seed=2,
    ).estimate
    b = simulation.coverage_probability(
        lambda m, rng: rng.normal(0, 1, m), normal_interval, truth=0.0, n=n, n_reps=8000, seed=2,
    ).estimate
    print(f"{n:5d} {a:12.4f} {b:12.4f}")
print("\\n小標本では正規分位点が明確に過小被覆。n が増えると差は消える")
"""),
    md(r"""
## 3. ピボット法 — 区間はどこから来るのか

$\frac{\bar X - \mu}{S/\sqrt{n}}$ のように、**母数を含むのに分布が母数に依らない**量を
**ピボット**という。ピボットが見つかれば、その分位点を不等式に入れて $\mu$ について解くだけで
区間ができる。

$$
P\left(-t_{0.975} \le \frac{\bar X - \mu}{S/\sqrt{n}} \le t_{0.975}\right) = 0.95
\;\Longrightarrow\;
\bar X \pm t_{0.975}\frac{S}{\sqrt{n}}
$$

問題は、**中央値や分位点や比にはピボットが無い**ことである。ここで次の道具が要る。

## 4. ブートストラップ

考え方は一行で言える。**標本を母集団と見なして、そこから再標本する。**

真の母集団から何度も標本を取れれば標本分布が分かる。それができないので、
手元の標本を母集団の代用にする。中央値の分布を見てみよう。
"""),
    code("""
rng = np.random.default_rng(3)
sample = rng.exponential(1.0, 60)
print(f"標本中央値 = {np.median(sample):.4f}   真の中央値 = log(2) = {np.log(2):.4f}")
plotting.bootstrap_distribution(sample, np.median, n_boot=3000, seed=0)
"""),
    code("""
truth = float(np.log(2.0))
r = simulation.coverage_probability(
    lambda n, rng: rng.exponential(1.0, n),
    lambda s: tuple(intervals.bootstrap_interval(s, np.median, n_boot=400, seed=0)),
    truth=truth, n=60, n_reps=1000, seed=5,
)
print(f"中央値のブートストラップ区間の実測被覆率 = {r.estimate:.4f}(名目 0.95)")
print("標準誤差の公式が存在しない統計量に、区間が付いた")
"""),
    md(r"""
## 5. percentile と BCa — そして、どちらも万能ではない

**percentile 法** はブートストラップ分布の 2.5% 点と 97.5% 点をそのまま使う。
統計量が偏っていたり歪んでいたりすると、これは当たらない。

**BCa 法** は 2 つの補正を入れる。

- **偏り補正** $z_0$: 観測値がブートストラップ分布の中央からどれだけずれているか
- **加速** $a$: 統計量の分散が母数とともに変わる度合い(ジャックナイフから推定)

歪んだ統計量で比べよう。指数分布の**分散**を推定する。
"""),
    code("""
truth = 1.0                      # 指数分布(rate 1)の分散
print(f"{'手法':>12} {'被覆率':>10}   (名目 0.95)")
for method in ["percentile", "bca"]:
    r = simulation.coverage_probability(
        lambda n, rng: rng.exponential(1.0, n),
        lambda s, _m=method: tuple(
            intervals.bootstrap_interval(s, lambda a: a.var(ddof=1), method=_m, n_boot=400, seed=0)
        ),
        truth=truth, n=40, n_reps=600, seed=6,
    )
    print(f"{method:>12} {r.estimate:10.4f}")
print("\\nBCa の方が良い。しかし、どちらも 0.95 には届かない。")
print("小標本で歪んだ統計量にブートストラップを使うと、区間は狭すぎる方に外れる")
"""),
    md(r"""
これは重要な結果である。ブートストラップは万能ではない。
**「標準誤差が計算できたから正しい」とは言えない** ことが、数字で見えている。

だからこそ、新しい統計量に区間を付けるときは被覆率を一度測るべきである。
"""),
    md(r"""
```{admonition} 核心 — ひとことで
:class: tip
95% 信頼区間の 95% は、手続きの長期頻度であって、目の前の区間の確率ではない。
だから被覆率は実測できるし、実測すべきである。
導出が正しくても、手元の標本サイズで名目値どおりに動く保証はない。
```
"""),
    md(r"""
## 6. 順列検定 — 検定側のリサンプリング

ブートストラップが**区間**の道具なら、順列は**検定**の道具である。

帰無仮説「2 群に差はない」が正しければ、どちらの群に属するかというラベルは
データと無関係である。ならばラベルを混ぜても分布は変わらないはずである。
これを **交換可能性** という。分布の形は一切仮定しない。
"""),
    code("""
rng = np.random.default_rng(8)
a, b = rng.normal(0, 1, 60), rng.normal(0, 1, 60)
c, d = rng.normal(0, 1, 60), rng.normal(0.6, 1, 60)
print(f"差が無い 2 群: p = {intervals.permutation_test(a, b, n_perm=5000, seed=0):.4f}")
print(f"差がある 2 群: p = {intervals.permutation_test(c, d, n_perm=5000, seed=0):.4f}")
print("\\n分布の形を仮定していないので、正規性が怪しいデータでも使える")
"""),
    md(r"""
```{admonition} 実社会では
:class: note
論文やダッシュボードに並ぶ誤差棒の多くは、名目上の被覆率で描かれている。
モデルの仮定が現場のデータに合っていなければ、その棒は見た目より短い。
新しい指標に区間を付けるときは、手元のデータ生成過程を模したシミュレーションで
被覆率を一度測っておくと、後で高くつく誤解を防げる。
```
"""),
    md(r"""
## 7. 落とし穴

### 複数の区間を同時に見ると、同時被覆率は下がる

3 本の 95% 区間を同時に見て「全部当たっている確率」は 95% ではない。
独立なら $0.95^3 = 0.857$ である。この構造は 08 章の多重比較と同じものである。
"""),
    code("""
rng = np.random.default_rng(10)
hits = 0
reps = 40_000                       # 5,000 では MC 誤差が理論値との差を覆い隠す
for _ in range(reps):
    ok = True
    for truth in [0.0, 1.0, 2.0]:
        s = rng.normal(truth, 1.0, 15)
        if not intervals.t_interval(s).contains(truth):
            ok = False
    hits += ok
p = hits / reps
se = np.sqrt(p * (1 - p) / reps)
print(f"3 本すべてが当たった割合 = {p:.4f}  ± {1.96 * se:.4f}")
print(f"独立なら 0.95^3        = {0.95 ** 3:.4f}")
print("\\n1 本ずつは 95% でも、3 本同時では 86% しかない。08 章の多重比較と同じ構造")
"""),
    md(r"""
### ブートストラップは標本が母集団を代表していることに依存する

再標本は元の標本の中からしか値を取れない。だから**分布の端**に関する量では破綻する。
"""),
    code("""
rng = np.random.default_rng(9)
sample = rng.uniform(0, 10, 50)
boot_ci = intervals.bootstrap_interval(sample, np.max, n_boot=3000, seed=0)
print(f"標本最大値 = {sample.max():.4f}   真の上限 = 10.0")
print(f"ブートストラップ 95% 区間 = [{boot_ci.lo:.4f}, {boot_ci.hi:.4f}]")
print(f"真値 10.0 を含む: {boot_ci.contains(10.0)}")
print("\\n再標本は元の最大値を超えられないので、区間は真値の手前で頭打ちになる")
"""),
    md(r"""
## 8. 演習

1. 名目 95% の区間を 3 本同時に見たときの同時被覆率を、相関のある場合でも測れ。
   Bonferroni 的な補正で 95% に戻すには各区間を何 % にすればよいか。
2. 対数正規分布のような歪んだ分布で $n$ を変えて $t$ 区間の被覆率を測り、
   名目値に十分近づく $n$ を決めよ。04 章の KS 統計量の結果と関係づけよ。
3. 比 $\bar X / \bar Y$ のブートストラップ区間を作り、被覆率を測れ。
   $\bar Y$ が 0 に近づくとき何が起きるか。
4. 順列検定と $t$ 検定を、裾の重い分布で比較せよ。どちらの第 1 種の誤り率が名目どおりか。
"""),
]
