"""Builder for notebook 05 — Stochastic processes."""

from nbkit import code, md

cells = [
    md(r"""
# 05. 確率過程 — 時間軸の上の確率

> 独立同分布の世界を離れる唯一の章。目的地は決まっている — MCMC がなぜ動くのか。

## この章で分かること

- 独立同分布の仮定を外すと何が変わるか
- ランダムウォークが $\sqrt{t}$ で広がること
- **マルコフ性** — 未来は現在だけに依るという記憶の無さ
- **定常分布** と **エルゴード性** — 出発点を忘れ、時間平均が空間平均に一致する
- ポアソン過程が指数分布の間隔から生まれること
"""),
    code("""
import numpy as np
import plotly.io as pio
pio.renderers.default = "plotly_mimetype+notebook_connected"

from stats_textbook import datasets, distributions, plotting, processes, simulation

RANDOM_SEED = 0
print("setup ok")
"""),
    md(r"""
## 1. 独立同分布を離れる

ここまでの 4 章は「独立に同じ分布から何度も引く」設定だった。
標本の順番には意味がなく、並べ替えても何も変わらない。

現実のデータの多くはそうではない。株価、気温、待ち行列の長さ、遺伝子配列。
**今日の値は昨日の値と関係している。**

時間軸の入った確率変数の族 $\{X_t\}$ を **確率過程** という。
本書ではその入口だけを扱う。目的は 3 つの対象を通じて、
「依存があるとはどういうことか」を具体的にすることである。
"""),
    md(r"""
## 2. ランダムウォーク

$S_0 = 0$ から出発し、毎ステップ $\pm 1$ を等確率で足していく。

$$
S_t = \sum_{i=1}^{t} \xi_i, \qquad P(\xi_i = \pm 1) = \tfrac{1}{2}
$$

増分 $\xi_i$ は独立同分布だが、**位置 $S_t$ は独立ではない**。
$S_{t+1}$ は $S_t$ から 1 しか動けないからである。
"""),
    code("""
paths = processes.random_walk(500, n_paths=200, step="rademacher", seed=RANDOM_SEED)
plotting.random_walk_paths(paths, n_show=25)
"""),
    md(r"""
帯は $\pm\sqrt{t}$ を示している。多くの経路がこの中に収まる。

$\mathrm{Var}(S_t) = t$ なので標準偏差は $\sqrt{t}$。
時間に **比例** せず、その平方根で広がる。
100 ステップ後の典型的な位置のずれは 100 ではなく 10 である。
"""),
    code("""
paths = processes.random_walk(2_000, n_paths=5_000, seed=1)
print(f"{'t':>6} {'位置の sd':>12} {'sqrt(t)':>10} {'|S_t| の平均':>14}")
for t in [10, 100, 500, 2_000]:
    print(f"{t:6d} {paths[:, t].std():12.3f} {np.sqrt(t):10.3f} {np.abs(paths[:, t]).mean():14.3f}")
print("\\n位置の sd は sqrt(t) に一致する(増分が独立なので分散が足し算になる)")
"""),
    md(r"""
これは 02 章の分散の加法性そのものである。増分が独立だから $\mathrm{Var}(S_t) = \sum \mathrm{Var}(\xi_i) = t$。

さらに 04 章の中心極限定理から、$S_t/\sqrt{t}$ は正規分布に近づく。
ランダムウォークは前の章の道具でほぼ説明できる。
本当に新しいのは次の節である。
"""),
    md(r"""
## 3. マルコフ連鎖

**定義(マルコフ性)**

$$
P(X_{t+1} = j \mid X_t = i,\, X_{t-1}, \dots, X_0) = P(X_{t+1} = j \mid X_t = i)
$$

過去をどれだけ細かく知っていても、現在が分かっていれば予測は変わらない。
**現在が過去のすべての情報を要約している** ということである。

このとき遷移確率 $P_{ij}$ が過程を完全に決める。$n$ ステップ後の分布は

$$
p_n = p_0 P^n
$$

天気の 2 状態モデルで動かそう。晴れの翌日が晴れである確率 0.9、
雨の翌日が晴れである確率 0.5 とする。
"""),
    code("""
P = np.array([[0.9, 0.1], [0.5, 0.5]])
chain = processes.MarkovChain(P, states=("sunny", "rainy"))
p0 = np.array([1.0, 0.0])          # 今日は晴れ

print(f"{'n 日後':>8} {'晴れ':>8} {'雨':>8}")
for n in [0, 1, 2, 3, 5, 10, 30]:
    p = chain.distribution_after(n, p0)
    print(f"{n:8d} {p[0]:8.4f} {p[1]:8.4f}")
print(f"\\n定常分布  {chain.stationary().round(4)}")
"""),
    md(r"""
何日か経つと、今日が晴れだったことの影響が消えて一定の分布に落ち着く。
この落ち着き先が **定常分布** $\pi$ で、$\pi P = \pi$ を満たす。

スライダーで収束を追ってみよう。
"""),
    code("""
plotting.markov_convergence_slider(chain, p0=np.array([1.0, 0.0]), n_steps=30)
"""),
    code("""
# 出発点を変えても同じ場所に行き着く
for start, label in [(np.array([1.0, 0.0]), "晴れから"), (np.array([0.0, 1.0]), "雨から")]:
    p = chain.distribution_after(50, start)
    print(f"{label}出発して 50 日後: {p.round(6)}")
print(f"定常分布                : {chain.stationary().round(6)}")
"""),
    md(r"""
## 4. エルゴード性 — 時間平均が空間平均に一致する

定常分布に収束するには条件が要る。

- **既約** — どの状態からどの状態へも(何ステップかかっても)到達できる
- **非周期** — 戻ってくるタイミングが特定の周期に縛られていない

この 2 つが成り立つとき、収束するだけでなく、もっと強いことが言える。

**主張(エルゴード定理)** 既約かつ非周期な有限マルコフ連鎖では、
**1 本の長い経路の時間平均** が定常分布の期待値に一致する。

$$
\frac{1}{T}\sum_{t=1}^{T} f(X_t) \;\longrightarrow\; \sum_i \pi_i f(i)
$$

これは実務的に決定的である。$\pi$ を直接計算できなくても、
連鎖を長く走らせて平均を取れば $\pi$ が分かる。
"""),
    code("""
path = chain.simulate(200_000, x0=0, seed=2)
visited = np.bincount(path, minlength=2) / path.size

print(f"1 本の経路(20 万ステップ)の時間平均: {visited.round(4)}")
print(f"定常分布(固有ベクトルから計算)      : {chain.stationary().round(4)}")
print(f"\\n既約: {chain.is_irreducible()}   周期: {chain.period()}")
"""),
    md(r"""
一致する。**これが MCMC の原理である。**

欲しい分布 $\pi$ が与えられたとき、$\pi$ を定常分布に持つマルコフ連鎖を設計できれば、
その連鎖を走らせるだけで $\pi$ からの標本が得られる。
$\pi$ の正規化定数を知らなくてもよい。
姉妹本 `analytics/bayesian` の 07 章がこの構成を扱う。

条件が要ると書いた。破ってみよう。決定的に振動する 2 状態連鎖は既約だが周期 2 である。
"""),
    code("""
cycle = processes.MarkovChain(np.array([[0.0, 1.0], [1.0, 0.0]]))
print(f"既約: {cycle.is_irreducible()}   周期: {cycle.period()}")
print("\\n分布は振動し続けて収束しない:")
for n in range(6):
    print(f"  n = {n}: {cycle.distribution_after(n, np.array([1.0, 0.0])).round(3)}")

path = cycle.simulate(200_000, x0=0, seed=3)
print(f"\\nただし時間平均は収束する: {(np.bincount(path, minlength=2) / path.size).round(4)}")
print("-> 非周期性は「分布の収束」に要る。「時間平均の収束」には要らない")
"""),
    md(r"""
周期的な連鎖では、分布は 2 つの状態を行き来し続けて収束しない。
しかし時間平均は $(0.5, 0.5)$ に落ち着く。
**2 つの主張は別物である。** MCMC で必要なのは前者の方で、
だから実装では非周期性を確保する工夫(自己遷移を許すなど)が入る。
"""),
    md(r"""
## 5. ポアソン過程

事象がランダムな時刻に起きる。到着間隔が独立に $\mathrm{Exponential}(\lambda)$ に従うとき、
これを **ポアソン過程** という。

このとき長さ $T$ の区間に入る事象の数は $\mathrm{Poisson}(\lambda T)$ になる。
「指数の間隔」と「ポアソンの個数」は同じ過程の 2 つの見方である。

本書の実装は **間隔から作っている**。それがこの対応を説明する構成だからである。
"""),
    code("""
times = processes.poisson_process(rate=3.0, t_max=20.0, seed=3)
gaps = np.diff(np.concatenate([[0.0], times]))

print(f"[0, 20] に起きた事象: {times.size} 件   (期待 {3.0 * 20.0:.0f} 件)")
print(f"間隔の平均: {gaps.mean():.4f}   (期待 1/lambda = {1 / 3:.4f})")
print(f"間隔の sd : {gaps.std():.4f}   (指数分布は平均 = sd)")
print(f"\\n最初の 8 件の時刻: {times[:8].round(3)}")
"""),
    code("""
counts = processes.poisson_counts(rate=3.0, t_max=4.0, n_reps=50_000, seed=4)
print(f"長さ 4 の区間に入る件数を 5 万回:")
print(f"  平均 = {counts.mean():.3f}   分散 = {counts.var():.3f}   (どちらも lambda*T = 12)")
print("\\n平均と分散が等しいのがポアソン分布の指紋である")
print("(実データで分散が平均を大きく上回るなら過分散。10 章で扱う)")
"""),
    md(r"""
### 無記憶性

指数分布には特徴的な性質がある。

$$
P(X > s + t \mid X > s) = P(X > t)
$$

「すでに $s$ だけ待った」という情報が、残りの待ち時間の分布を変えない。
バスを 10 分待っても、次の 5 分以内に来る確率は待ち始めたときと同じである。
"""),
    code("""
gaps = np.diff(processes.poisson_process(rate=1.0, t_max=200_000.0, seed=5))
print(f"{'すでに待った時間 s':>20} {'P(あと 1 以上待つ | s 待った)':>32}")
for s in [0.0, 0.5, 1.0, 2.0, 3.0]:
    sel = gaps > s
    print(f"{s:20.1f} {np.mean(gaps[sel] > s + 1.0):32.4f}")
print(f"\\n理論値 exp(-1) = {np.exp(-1):.4f} — s に依らず一定")
"""),
    md(r"""
```{admonition} 核心 — ひとことで
:class: tip
既約で非周期なマルコフ連鎖は、出発点を忘れて定常分布に落ち着く。
さらに、1 本の長い経路の時間平均が定常分布の期待値に一致する。
この 2 つがあるから、目的の分布を定常分布に持つ連鎖を作れば標本が得られる。
それが MCMC である。
```
"""),
    md(r"""
```{admonition} 実社会では
:class: note
コールセンターの待ち行列、ウェブサーバへのリクエスト、放射性崩壊。
いずれもポアソン過程が第一近似になる。
ただし現実の到着は時間帯で強度が変わるので、
一様なポアソン過程を当てはめる前に定常性を疑う必要がある。
昼のピークと深夜を同じ $\lambda$ で扱えば、どちらの予測も外れる。
```
"""),
    md(r"""
## 6. 落とし穴

### マルコフ性を確かめずに仮定する

マルコフ性は強い仮定である。「現在で十分」が成り立たない系は多い。
状態の定義を広げれば(たとえば直近 2 期を状態にすれば)マルコフにできることもあるが、
状態空間は指数的に膨らむ。

### 周期性を見落として「収束しない」と誤解する

§4 で見たとおり、周期的な連鎖の分布は振動し続ける。
実装のバグではなく、連鎖の性質である。

### 強度が時間変化する系に一様ポアソンを当てる

到着率が時間帯で変わる場合、一様ポアソンを当てはめると
ピーク時を過小評価し、閑散時を過大評価する。
"""),
    code("""
# 昼は rate 10、夜は rate 1 の系に、一様ポアソン(平均 5.5)を当てはめると
rng = np.random.default_rng(6)
day = rng.poisson(10.0, 10_000)
night = rng.poisson(1.0, 10_000)
mixed = np.concatenate([day, night])

uniform_fit = rng.poisson(mixed.mean(), 100_000)

print(f"実際の混合系: 平均 = {mixed.mean():.3f}   分散 = {mixed.var():.3f}")
print(f"一様ポアソンなら 平均 = 分散 のはずだが、分散は {mixed.var() / mixed.mean():.2f} 倍")
print("\\n容量設計に使う 95 パーセンタイル:")
print(f"  実際のピーク時間帯      {np.quantile(day, 0.95):.0f} 件")
print(f"  一様ポアソンの当てはめ  {np.quantile(uniform_fit, 0.95):.0f} 件")
print("-> 一様仮定はピークを過小評価する。この差がそのまま設備の不足になる")
"""),
    md(r"""
## 7. 演習

1. 3 状態のマルコフ連鎖を作り、定常分布を $\pi P = \pi$ と $\sum \pi_i = 1$ から
   手計算で解き、`stationary()` の値と照合せよ。
2. 可約な連鎖(2 つの閉じたクラスを持つもの)で `stationary()` が何を返すか調べ、
   なぜその値に意味がないかを説明せよ。出発点を変えると時間平均はどうなるか。
3. 正規増分のランダムウォークでも位置の sd が $\sqrt{t}$ になることを確かめよ。
   増分の分布を裾の重いものに変えるとどうなるか(04 章と関連づけよ)。
4. 強度が $\lambda(t) = 5 + 4\sin(2\pi t / 24)$ で変化する非一様ポアソン過程を作り、
   一様ポアソンを当てはめたときに何がどれだけ外れるかを測れ。
5. 指数分布以外に無記憶性を持つ連続分布は存在しないことを、
   $P(X > s+t) = P(X > s)P(X > t)$ という関数方程式から示せ。
"""),
]
