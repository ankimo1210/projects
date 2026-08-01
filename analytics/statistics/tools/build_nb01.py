"""Builder for notebook 01 — Foundations of probability."""

from nbkit import code, md

cells = [
    md(r"""
# 01. 確率の土台 — 条件付き確率が直感を裏切るとき

> 確率の規則そのものは単純である。裏切るのは規則ではなく、私たちの読み方の方である。

## この章で分かること

- 標本空間と事象という舞台設定、そして確率の 3 公理
- **独立** の定義は直感より狭いこと。「無関係に見える」ことではない
- 条件付き確率と乗法定理。モンティ・ホールがなぜ 2/3 になるか
- ベイズの定理を **計算道具として** 使うこと(流儀の話は 11 章)
- 優秀な検査でも、稀な病気では陽性者の大半が健康であること
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
## 1. 標本空間・事象・確率の公理

**標本空間** $\Omega$ は起こりうる結果を全部並べた集合である。
サイコロなら $\Omega = \{1,2,3,4,5,6\}$。
**事象** は $\Omega$ の部分集合で、「偶数が出る」は $\{2,4,6\}$ のこと。

確率とは、事象に $[0,1]$ の数を割り当てる関数で、次の 3 つを満たすものをいう
(コルモゴロフの公理)。

**定義**

1. すべての事象 $A$ について $P(A) \ge 0$
2. $P(\Omega) = 1$
3. 互いに排反な $A_1, A_2, \dots$ について $P(\bigcup_i A_i) = \sum_i P(A_i)$

これだけである。ここから出てくる主張はすべて、この 3 つの帰結にすぎない。

**主張**(公理から従う。証明は易しいので演習に回す)

- $P(A^c) = 1 - P(A)$
- $A \subseteq B$ ならば $P(A) \le P(B)$
- $P(A \cup B) = P(A) + P(B) - P(A \cap B)$
"""),
    md(r"""
## 2. 条件付き確率と独立

$B$ が起きたと分かった後の $A$ の確率を **条件付き確率** という。

$$
P(A \mid B) = \frac{P(A \cap B)}{P(B)}, \qquad P(B) > 0
$$

これは新しい仮定ではなく、標本空間を $B$ に取り替えて確率を測り直しただけである。
分母の $P(B)$ は、縮んだ舞台の上で全体が 1 になるように帳尻を合わせている。

両辺に $P(B)$ を掛けると **乗法定理** になる。

$$
P(A \cap B) = P(A \mid B)\, P(B)
$$

**独立** の定義は次のとおり。

$$
P(A \cap B) = P(A) P(B)
\quad\Longleftrightarrow\quad
P(A \mid B) = P(A)
$$

つまり「$B$ を知っても $A$ の確率が変わらない」ことである。
「因果関係がない」でも「別々の実験だ」でもない。
**確率が変わらないという等式**であって、それ以上でも以下でもない。

サイコロ 2 個の例で確かめよう。
「和が偶数」と「1 個目が偶数」は独立だろうか。直感では従属に見えるかもしれない。
"""),
    code("""
rng = np.random.default_rng(RANDOM_SEED)
d1, d2 = rng.integers(1, 7, 200_000), rng.integers(1, 7, 200_000)

even_sum, even_first = (d1 + d2) % 2 == 0, d1 % 2 == 0
p_a, p_b = even_sum.mean(), even_first.mean()
p_ab = (even_sum & even_first).mean()

print(f"P(A) = {p_a:.4f}   P(B) = {p_b:.4f}")
print(f"P(A and B) = {p_ab:.4f}   P(A) * P(B) = {p_a * p_b:.4f}")
print("-> 独立" if abs(p_ab - p_a * p_b) < 0.005 else "-> 従属")
"""),
    md(r"""
独立である。1 個目が偶数だと知っても、和が偶数になる確率は 1/2 のままで変わらない。
2 個目の偶奇がまだ決まっていないからである。

一方、「和が偶数」と「2 個の目が一致」は独立ではない。
一致すれば和は必ず偶数になるので、片方が他方を強く縛る。
"""),
    code("""
same = d1 == d2
p_c = same.mean()
p_ac = (even_sum & same).mean()
print(f"P(A) = {p_a:.4f}   P(C) = {p_c:.4f}")
print(f"P(A and C) = {p_ac:.4f}   P(A) * P(C) = {p_a * p_c:.4f}")
print(f"P(A | C) = {p_ac / p_c:.4f}   <- 1 になる(一致すれば和は必ず偶数)")
"""),
    md(r"""
## 3. モンティ・ホール

3 つの扉のうち 1 つに車、2 つにヤギがいる。あなたが 1 つ選ぶ。
司会は残り 2 つのうち **ヤギのいる扉** を開けて見せ、選び直すかと聞く。変えるべきか。

**変えるべきである。** 乗法定理で追える。

最初に選んだ扉が当たりである確率は $1/3$。この確率は司会が扉を開けても変わらない。
司会は必ずヤギの扉を開けるので、その行為は最初の選択について何も教えないからである。

したがって「最初の扉が外れ」の確率は $2/3$ で、そのときは残った扉が必ず当たりである。
変えれば $2/3$ で勝つ。

重要なのは **司会が答えを知っていて、必ずヤギを開ける** という前提である。
司会が無作為に開けてたまたまヤギだった場合、答えは $1/2$ になる。両方数えてみよう。
"""),
    code("""
def monty_hall(n_games, switch, host_knows=True, seed=0):
    \"\"\"Returns the win rate. With host_knows=False, games where the host
    happens to reveal the car are discarded -- that is the different problem.\"\"\"
    rng = np.random.default_rng(seed)
    car = rng.integers(0, 3, n_games)
    pick = rng.integers(0, 3, n_games)
    if host_knows:
        # The host never opens the car, so switching wins exactly when the
        # first pick was wrong.
        return float(np.mean(car != pick)) if switch else float(np.mean(car == pick))
    # An ignorant host opens one of the two unpicked doors at random.
    offsets = rng.integers(1, 3, n_games)
    opened = (pick + offsets) % 3
    valid = opened != car                     # discard the games he spoiled
    stay_win = (car == pick)[valid]
    return float(1.0 - stay_win.mean()) if switch else float(stay_win.mean())


print(f"{'':28s} {'変えない':>10s} {'変える':>10s}")
for label, knows in [("司会が答えを知っている", True), ("司会が無作為に開ける", False)]:
    stay = monty_hall(200_000, switch=False, host_knows=knows, seed=1)
    swap = monty_hall(200_000, switch=True, host_knows=knows, seed=1)
    print(f"{label:26s} {stay:10.4f} {swap:10.4f}")
print("\\n理論値: 知っている 1/3 と 2/3、無作為 1/2 と 1/2")
"""),
    md(r"""
同じ「ヤギの扉が開いた」という光景でも、**それがどういう手続きで生じたか** によって
答えが変わる。データだけを見て確率を更新することはできない。
データの生成過程を知る必要がある。これは本書で何度も戻ってくる主題である。
"""),
    md(r"""
## 4. ベイズの定理

条件付き確率の定義を 2 通りに書くと $P(A \cap B) = P(A \mid B) P(B) = P(B \mid A) P(A)$
となり、整理すれば

$$
P(A \mid B) = \frac{P(B \mid A)\, P(A)}{P(B)}
$$

を得る。これが **ベイズの定理** である。公理からの帰結にすぎず、
ここには何の哲学も含まれていない。

$P(B)$ は分解できる。$A$ と $A^c$ で場合分けすれば

$$
P(B) = P(B \mid A) P(A) + P(B \mid A^c) P(A^c)
$$

この定理は「$B \to A$ の向きの確率が欲しいのに、$A \to B$ の向きしか分からない」
という場面で効く。次節がまさにそれである。

なお、母数 $\theta$ に確率分布を置いてよいかという論点は、この定理とは **別の問題** である。
そちらは 11 章で扱う。ここでは事象に対する計算道具として使う。
"""),
    md(r"""
## 5. 検査の偽陽性パラドクス

ある病気の検査を考える。

- **感度** $P(\text{陽性} \mid \text{病気}) = 0.99$
- **特異度** $P(\text{陰性} \mid \text{健康}) = 0.95$
- **有病率** $P(\text{病気}) = 0.001$

あなたの検査結果が陽性だった。病気である確率はいくらか。

多くの人は 95% 前後と答える。実際には 2% にも満たない。
100 万人を検査して数えてみよう。
"""),
    code("""
counts = datasets.disease_test_counts(
    1_000_000, prevalence=0.001, sensitivity=0.99, specificity=0.95, seed=RANDOM_SEED
)
ppv = counts["tp"] / (counts["tp"] + counts["fp"])

print(f"真陽性(病気で陽性): {counts['tp']:>7,}")
print(f"偽陽性(健康で陽性): {counts['fp']:>7,}")
print(f"偽陰性(病気で陰性): {counts['fn']:>7,}")
print(f"真陰性(健康で陰性): {counts['tn']:>7,}")
print(f"\\n陽性者 {counts['tp'] + counts['fp']:,} 人のうち本当に病気なのは {ppv:.2%}")
"""),
    md(r"""
理由は数のバランスにある。病気の人は 1,000 人しかいないので真陽性はどう頑張っても
1,000 人が上限である。一方、健康な人は 999,000 人いて、その 5% が誤って陽性になる。
つまり偽陽性は約 50,000 人。**健康な人の母数が大きすぎる** のである。

ベイズの定理で書けば

$$
P(\text{病気} \mid \text{陽性})
= \frac{0.99 \times 0.001}{0.99 \times 0.001 + 0.05 \times 0.999}
$$

分子が小さいのは有病率 $0.001$ が掛かっているからで、
検査の性能とは関係がない。有病率を動かして、この綱引きを見よう。
"""),
    code("""
plotting.ppv_slider(
    [0.0005, 0.001, 0.005, 0.02, 0.1, 0.3, 0.5], sensitivity=0.99, specificity=0.95
)
"""),
    md(r"""
有病率が 10% を超えたあたりから、ようやく真陽性が偽陽性を上回る。
同じ検査が、対象集団によって役に立ったり立たなかったりする。
"""),
    md(r"""
```{admonition} 核心 — ひとことで
:class: tip
検査の性能(感度・特異度)だけでは、陽性者が病気である確率は決まらない。
有病率という事前の情報が必ず要る。
稀な病気では、優秀な検査でも陽性者の大半が健康な人になる。
```
"""),
    md(r"""
```{admonition} 実社会では
:class: note
空港のセキュリティ検査、クレジットカードの不正検知、迷惑メールのフィルタ。
いずれも探している対象が稀なので、同じ算術に支配される。
だから実務では、精度を上げる努力と同じくらい、
「まず対象を絞って有病率を上げる」設計が効いてくる。
```
"""),
    md(r"""
## 6. 落とし穴

### $P(A \mid B)$ と $P(B \mid A)$ の取り違え(検察官の誤謬)

「無実なら証拠が一致する確率は 100 万分の 1」と
「証拠が一致したから無実である確率は 100 万分の 1」は別物である。
前者は $P(\text{一致} \mid \text{無実})$、後者は $P(\text{無実} \mid \text{一致})$。
両者をつなぐには、容疑者候補の母数(事前確率)が要る。
偽陽性パラドクスとまったく同じ構造である。

### 「独立」を確かめずに仮定する

独立を仮定すると計算がとても楽になるので、つい仮定してしまう。
2 つの検査を独立と見なして掛け算すると、どうなるか。
"""),
    code("""
# 1 回目陽性の後、2 回目も陽性だったら?
# 誤: 2 回の検査結果を独立と見なして特異度を二乗する
prev, sens, spec = 0.001, 0.99, 0.95
naive = (sens**2 * prev) / (sens**2 * prev + (1 - spec) ** 2 * (1 - prev))

# 実際には同じ人の体質や検体の状態が両方に効くので、誤りは相関する。
# 相関 rho で偽陽性が繰り返されやすいとすると:
for rho in [0.0, 0.3, 0.6]:
    fp2 = (1 - spec) * ((1 - spec) + rho * (1 - (1 - spec)))
    p = (sens**2 * prev) / (sens**2 * prev + fp2 * (1 - prev))
    tag = " <- 独立を仮定した場合" if rho == 0.0 else ""
    print(f"誤りの相関 rho = {rho:.1f}: 2 回陽性後の確率 = {p:.2%}{tag}")
print(f"\\n独立仮定での値 {naive:.2%} は、相関があると楽観的すぎる")
"""),
    md(r"""
### 分母を忘れる

$P(A \mid B)$ を計算するとき、$P(B)$ が小さい事象だと分母の見積もりが効いてくる。
「$B$ が起きた」という条件がどれくらい絞り込みになっているかを常に意識する。
"""),
    md(r"""
## 7. 演習

1. 公理 1–3 だけを使って $P(A \cup B) = P(A) + P(B) - P(A \cap B)$ を示せ。
2. 有病率 0.001 の集団で、感度を 0.99 から 0.999 に上げた場合と、
   特異度を 0.95 から 0.99 に上げた場合とで、PPV はそれぞれいくらになるか。
   数値で比べ、どちらに投資すべきか論じよ。有病率 0.3 ではどうか。
3. 独立な 2 回目の検査が受けられるとして、2 回続けて陽性だったときの
   $P(\text{病気} \mid \text{陽陽})$ を求めよ。1 回目の事後確率を
   2 回目の事前確率として使えることを、乗法定理から確かめよ。
4. 相関 0 だが独立でない 2 つの事象の例を作り、
   $P(A \cap B) \ne P(A)P(B)$ を数値で確かめよ。
5. モンティ・ホールを扉 $n$ 枚に一般化する。司会が $n-2$ 枚のヤギの扉を開けるとき、
   変える戦略の勝率を $n$ の式で書き、シミュレーションで確かめよ。
"""),
]
