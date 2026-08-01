"""Builder for notebook 09 — Regression as inference."""

from nbkit import code, md

cells = [
    md(r"""
# 09. 回帰の推測 — 係数は推定量である

> 回帰の出力は数値ではなく分布である。標準誤差を読めなければ、係数を読んだことにならない。

## この章で分かること

- 回帰係数は推定量であり、**標本分布を持つ**こと
- $t$ 値・$p$ 値・$F$ 検定が、その分布についての主張であること
- **係数表を見ても仮定が成り立っているかは分からない**。残差を見る
- 等分散が破れても**係数は不偏のまま**。壊れるのは標準誤差の方であること
- **多重共線性** — 予測は悪化しないが、解釈が壊れる
"""),
    code("""
import numpy as np
import plotly.io as pio
pio.renderers.default = "plotly_mimetype+notebook_connected"

from stats_textbook import (
    datasets, distributions, estimation, glm, intervals, plotting,
    processes, regression, simulation, testing
)

RANDOM_SEED = 0
print("setup ok")
"""),
    md(r"""
## 1. モデルと 3 つの仮定

$$
y = X\beta + \varepsilon
$$

推測を行うには、誤差 $\varepsilon$ について 3 つを仮定する。

1. $E[\varepsilon] = 0$ — モデルに系統的なずれがない
2. $\mathrm{Var}(\varepsilon) = \sigma^2 I$ — **等分散かつ無相関**
3. $X$ は固定(または $\varepsilon$ と独立)

**2 つ目が現実で最も破れやすい。** この章の後半はその話である。

まず、係数が推定量であることを見ておこう。同じ真値から何度もデータを作れば、
推定される傾きはばらつく。
"""),
    code("""
plotting.coefficient_sampling(n=60, n_reps=4000, seed=RANDOM_SEED)
"""),
    md(r"""
## 2. 係数の分布

仮定が成り立つとき

$$
\hat\beta \sim N\!\left(\beta,\ \sigma^2 (X^\top X)^{-1}\right)
$$

$\sigma^2$ を残差から推定した $\hat\sigma^2$ で置き換えると、標準化した量は
$t_{n-k}$ 分布に従う(03 章)。だから回帰の出力表には $t$ 値が並ぶ。
"""),
    code("""
rng = np.random.default_rng(RANDOM_SEED)
n = 200
X = np.column_stack([np.ones(n), rng.normal(size=n), rng.normal(size=n)])
y = X @ np.array([1.0, 2.0, -0.5]) + rng.normal(0, 1.5, n)

fit = regression.ols(X, y)
print(f"{'':>8} {'推定値':>10} {'標準誤差':>10} {'t 値':>10} {'p 値':>12}")
for i, name in enumerate(["切片", "x1", "x2"]):
    print(f"{name:>8} {fit.params[i]:10.4f} {fit.se[i]:10.4f} "
          f"{fit.tvalues[i]:10.4f} {fit.pvalues[i]:12.3e}")
print(f"\\nR^2 = {fit.r_squared:.4f}   残差自由度 = {fit.df_resid}")
f, p = regression.f_test_overall(fit, X, y)
print(f"全体の F 検定: F = {f:.3f}, p = {p:.3e}(すべての傾きがゼロという仮説)")
"""),
    md(r"""
本書の回帰は numpy だけで書いてある(`regression.ols`)。
自前実装を信じてよい理由は、実務標準と一致することである。
"""),
    code("""
import statsmodels.api as sm

ref = sm.OLS(y, X).fit()
print(f"{'':>8} {'本書の実装':>16} {'statsmodels':>16} {'差':>12}")
for i, name in enumerate(["切片", "x1", "x2"]):
    print(f"{name:>8} {fit.params[i]:16.10f} {ref.params[i]:16.10f} "
          f"{abs(fit.params[i] - ref.params[i]):12.2e}")
assert np.allclose(fit.params, ref.params, rtol=1e-10)
assert np.allclose(fit.se, ref.bse, rtol=1e-10)
print("\\n係数も標準誤差も一致する")
"""),
    md(r"""
## 3. 残差診断 — 係数表は仮定を教えてくれない

ここからが本題である。**係数表を見ても、仮定が成り立っているかは分からない。**

3 つの違うデータで回帰してみよう。1 つは仮定どおり、
1 つは不均一分散、1 つは真の関係が曲がっている。
"""),
    code("""
rng = np.random.default_rng(1)
n = 200
x = np.sort(rng.uniform(-3, 3, n))
Xs = np.column_stack([np.ones(n), x])
designs = {
    "健全": 1.0 + 2.0 * x + rng.normal(0, 1.0, n),
    "不均一分散": 1.0 + 2.0 * x + rng.normal(0, 0.3 + 0.6 * np.abs(x), n),
    "非線形": 1.0 + 2.0 * x + 0.7 * x**2 + rng.normal(0, 1.0, n),
}
print(f"{'データ':>12} {'傾き':>9} {'標準誤差':>10} {'p 値':>12} {'R^2':>8}")
for label, yy in designs.items():
    f2 = regression.ols(Xs, yy)
    print(f"{label:>12} {f2.params[1]:9.4f} {f2.se[1]:10.4f} "
          f"{f2.pvalues[1]:12.3e} {f2.r_squared:8.4f}")
print("\\nどれも「傾きは 2 付近で極めて有意」と読める。")
print("R^2 は違うが、低い R^2 は単にノイズが多いだけでも起きる。")
print("-> 何かが違うことは分かっても、何が違うのかは分からない")
"""),
    code("""
plotting.residual_catalogue(seed=1, n=200)
"""),
    md(r"""
残差プロットなら一目で分かる。

- **健全**: 帯状に広がり、傾向がない
- **不均一分散**: 左右に向かって扇形に開く
- **非線形**: 明らかな曲線を描く(直線では吸収しきれなかった構造が残っている)
- **外れ値**: 数点だけが大きく飛んでいる

$R^2$ は「何かが違う」までしか言わない。残差プロットは「何が違うか」を言う。
"""),
    md(r"""
## 4. 不均一分散と頑健標準誤差

等分散の仮定が破れたとき、何が壊れるのか。

**係数の推定値は不偏のまま**である。壊れるのは**標準誤差**であり、
そこから作る $t$ 値・$p$ 値・信頼区間がすべて狂う。

White のサンドイッチ推定量(HC0–HC3)が直してくれる。
"""),
    code("""
plotting.robust_se_comparison(seed=2, ns=(50, 200, 1000))
"""),
    md(r"""
標準誤差が違うのは分かった。では**どちらが正しい**のか。
被覆率を測れば決着する(第 2 原則)。
"""),
    code("""
def coverage_of(kind, reps=2000):
    rng2 = np.random.default_rng(7)
    hits = 0
    for _ in range(reps):
        m = 100
        xx = rng2.normal(size=m)
        XX = np.column_stack([np.ones(m), xx])
        yy = 1.0 + 2.0 * xx + rng2.normal(0, 0.3 + 0.8 * np.abs(xx), m)
        f3 = regression.ols(XX, yy)
        se = f3.se[1] if kind == "ordinary" else regression.robust_se(XX, f3.resid, kind)[1]
        if abs(f3.params[1] - 2.0) <= 1.96 * se:
            hits += 1
    return hits / reps

print("不均一分散のデータで、傾きの 95% 区間の実測被覆率:")
for kind in ["ordinary", "HC0", "HC3"]:
    print(f"  {kind:>9}: {coverage_of(kind):.4f}")
print("\\n通常の標準誤差は名目 0.95 を下回る。HC3 が最も近い")
"""),
    md(r"""
```{admonition} 核心 — ひとことで
:class: tip
等分散の仮定が破れても、係数の推定値は不偏のままである。壊れるのは標準誤差の方である。
だから対処は「係数を捨てる」ことではなく「標準誤差を直す」ことになる。
頑健標準誤差は 1 行で計算でき、仮定が成り立っている場合でもほとんど損をしない。
```
"""),
    md(r"""
## 5. 多重共線性

説明変数どうしが強く相関していると、個々の係数の分散が跳ね上がる。
どれだけ跳ね上がるかを測るのが **VIF**(分散拡大係数)である。

$$
\mathrm{VIF}_j = \frac{1}{1 - R_j^2}
$$

$R_j^2$ は「変数 $j$ を他の変数で回帰したときの決定係数」。
他の変数で説明できてしまうほど、その係数は不安定になる。
"""),
    code("""
rng = np.random.default_rng(3)
n = 400
a = rng.normal(size=n)
X2 = np.column_stack([np.ones(n), a, a + rng.normal(0, 0.05, n), rng.normal(size=n)])
y2 = X2 @ np.array([1.0, 2.0, 1.0, -0.5]) + rng.normal(0, 1.0, n)

v = regression.vif(X2)
f4 = regression.ols(X2, y2)
print(f"{'':>10} {'真値':>7} {'VIF':>10} {'推定値':>10} {'標準誤差':>10}")
for i, (name, truth) in enumerate([("切片", 1.0), ("a", 2.0), ("a の複製", 1.0), ("独立", -0.5)]):
    print(f"{name:>10} {truth:7.2f} {v[i]:10.2f} {f4.params[i]:10.4f} {f4.se[i]:10.4f}")
print("\\n相関した 2 本は標準誤差が跳ね上がり、複製の係数は符号まで反転している。")
print(f"  a と複製の係数の和 = {f4.params[1] + f4.params[2]:.4f}   真値の和 = {2.0 + 1.0:.4f}")
print("  -> 和は当てられている。当てられないのは「内訳」の方である")
print(f"\\nそして当てはまりは良いまま: R^2 = {f4.r_squared:.4f}")
print("-> 予測は問題ない。壊れるのは「どちらがどれだけ効いたか」の解釈である")
"""),
    md(r"""
```{admonition} 実社会では
:class: note
広告費とブランド認知度のように、実務のデータでは説明変数が絡み合っていることが多い。
このとき「どの施策が効いたか」を係数から読み取ろうとすると、
符号が入れ替わるほど不安定な数字を根拠にすることになる。
予測が目的なら問題にならないという点も、同時に押さえておく必要がある。
目的が予測なのか解釈なのかを先に決めておくと、この判断は難しくない。
```
"""),
    md(r"""
## 6. 落とし穴

### $R^2$ は説明変数を足せば必ず上がる

まったく無関係な乱数を説明変数に加えても $R^2$ は上がる。
"""),
    code("""
rng = np.random.default_rng(5)
n = 100
y5 = rng.normal(size=n)
X5 = np.ones((n, 1))
print(f"{'追加した無関係な変数の数':>26} {'R^2':>10}")
for extra in [0, 5, 20, 50, 90]:
    Xe = np.column_stack([X5] + ([rng.normal(size=(n, extra))] if extra else []))
    print(f"{extra:26d} {regression.ols(Xe, y5).r_squared:10.4f}")
print("\\ny は純粋なノイズで、説明できるものは何も無い。")
print("それでも変数を 90 本足せば R^2 は 0.9 を超える")
"""),
    md(r"""
### 外れ値と高レバレッジ点は別物

**レバレッジ**は「その点が自分自身の当てはめ値をどれだけ引っ張るか」で、
$X$ だけで決まる($y$ は関係ない)。レバレッジが高い点は、
当てはめを大きく動かすのに**残差は小さい**ことがある。残差プロットでは目立たない。
"""),
    code("""
rng = np.random.default_rng(4)
n = 60
x5 = np.concatenate([rng.normal(0, 1, n - 1), [8.0]])     # 1 点だけ遠い
X6 = np.column_stack([np.ones(n), x5])
y6 = 1.0 + 2.0 * x5 + rng.normal(0, 1.0, n)
h = regression.leverage(X6)
fit6 = regression.ols(X6, y6)

print(f"レバレッジの合計 = {h.sum():.4f}(= 説明変数の本数 {X6.shape[1]})")
print(f"最大レバレッジ   = {h.max():.4f}(平均 {h.mean():.4f} の {h.max() / h.mean():.1f} 倍)")
print(f"その点の残差     = {fit6.resid[np.argmax(h)]:+.4f}"
      f"(残差の標準偏差 {fit6.resid.std():.4f})")
print("\\n当てはめを最も強く支配している点が、残差プロットでは平凡に見える")
"""),
    md(r"""
### 有意性は因果の証拠ではない

$p < 0.001$ は「この係数がゼロでない」ことの証拠であって、
「$x$ を動かせば $y$ が動く」ことの証拠ではない。
交絡変数の扱いは本書のスコープ外である
(姉妹本 `analytics/machine_learning` の 09 章が関連する話題を扱う)。
"""),
    md(r"""
## 7. 演習

1. 無関係な変数を足すと $R^2$ が必ず上がることを示せ。
   自由度調整済み $R^2 = 1 - (1-R^2)\frac{n-1}{n-k}$ が同じ実験でどう振る舞うか比べよ。
2. 誤差が自己相関している(たとえば AR(1))データを作り、
   通常の標準誤差の被覆率がどれだけ狂うか測れ。
3. HC0–HC3 の被覆率を標本サイズ $n = 20, 50, 200$ で比較し、
   小標本で HC3 が推奨される理由を数値で説明せよ。
4. レバレッジの高い点を除くと係数がどう動くか調べよ。
   Cook の距離を自分で実装し、レバレッジと残差の両方を含む指標であることを確かめよ。
"""),
]
