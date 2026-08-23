# Ch.12 Trading Strategies Involving Options

> **Source**: Hull 11e, Chapter 12 (pp. 268-287). Paraphrased summary for personal use.

## 1. 要点

- オプションをゼロクーポン債と組み合わせることで元本保護ノート（principal-protected note）が作れる。投資家は元本リスクなしにリスク資産のアップサイドを享受できるが、銀行の収益確保には十分な金利水準と配当利回りが必要。
- 株式と単一オプションの組み合わせ（covered call・protective put）は、プット・コール・パリティにより別の単独オプションのポジションと等価になる。
- スプレッド戦略（bull / bear / box / butterfly / calendar / diagonal）は同種オプション2本以上のポジション。リスクと利益ポテンシャルをともに限定し、相場観に合わせて選択する。
- コンビネーション戦略（straddle / strip / strap / strangle）はコールとプットを組み合わせ、方向感なく大きな値動きを期待する場面で使う。
- butterfly spreadのペイオフは「スパイク」と解釈できる。十分に細かいスパイクの線形結合で任意のペイオフ関数を近似できるため、butterﬂy spreadは建築ブロックとして機能する。

## 2. キー用語

- **principal-protected note（元本保護ノート）**: ゼロクーポン債＋コールオプションの組み合わせ。元本は保証されつつ、原資産上昇時に利益を得る。
- **covered call（カバードコール）**: 株式ロング＋コールショート。コール売りのプレミアムを受け取るが、上値を抑制する。
- **protective put（プロテクティブ・プット）**: 株式ロング＋プットロング。下値を限定した保険として機能。
- **bull spread（ブルスプレッド）**: 低行使価格買い＋高行使価格売り。上昇相場で使用。コールでもプットでも作成可能。
- **bear spread（ベアスプレッド）**: 高行使価格買い＋低行使価格売り（プット）。下落相場で使用。
- **box spread（ボックススプレッド）**: bull call spread＋bear put spread。ペイオフは常に $K_2 - K_1$、価値は $(K_2-K_1)e^{-rT}$。裁定戦略。
- **butterfly spread（バタフライスプレッド）**: $K_1, K_3$ ロング＋$K_2$ 2枚ショート（$K_2=(K_1+K_3)/2$）。小動き予想で利益。
- **calendar spread（カレンダースプレッド）**: 同行使価格・異限月。短期売り・長期買いが基本形。
- **diagonal spread（ダイアゴナルスプレッド）**: 行使価格も限月も異なる2枚のオプションポジション。
- **straddle（ストラドル）**: 同行使価格・同限月のコール＋プット両買い。大きな方向不明の動きを期待。
- **strip**: コール1枚＋プット2枚（同行使・同限月）。下落方向の大きな動きを想定。
- **strap**: コール2枚＋プット1枚（同行使・同限月）。上昇方向の大きな動きを想定。
- **strangle（ストラングル）**: OTMコール＋OTMプット（異なる行使価格・同限月）。ストラドルより値動きが必要だが初期コストが低い。
- **bottom straddle / straddle purchase**: ストラドルの買いポジション（通常の「ストラドル」）。
- **top straddle / straddle write**: ストラドルの売りポジション。無限のリスクを持つ。
- **reverse butterfly**: $K_2$ 2枚ロング＋$K_1, K_3$ ショート。大きな動きで小利益。

## 3. 主要公式

### Put-call parity（Chapter 11 から参照）
<!-- Hull eq. (12.1) -->
$$p + S_0 = c + Ke^{-rT} + D$$
- $p$: ヨーロピアンプット価格、$S_0$: 株価、$c$: ヨーロピアンコール価格
- $K$: 行使価格、$r$: 無リスク金利、$T$: 満期、$D$: 配当現在価値

### Box spread value
$$\text{Value} = (K_2 - K_1)e^{-rT}$$
- $K_1 < K_2$: 2つの行使価格（Europeanオプションのみ有効）

### Bull call spread payoff
$$\text{Payoff} = \begin{cases} 0, & S_T \le K_1 \\ S_T - K_1, & K_1 < S_T < K_2 \\ K_2 - K_1, & S_T \ge K_2 \end{cases}$$
- $K_1 < K_2$: 低行使価格（ロング）、高行使価格（ショート）

### Bear put spread payoff
$$\text{Payoff} = \begin{cases} K_2 - K_1, & S_T \le K_1 \\ K_2 - S_T, & K_1 < S_T < K_2 \\ 0, & S_T \ge K_2 \end{cases}$$
- $K_1 < K_2$: 低行使価格（ショート）、高行使価格（ロング）

### Butterfly spread payoff（calls または puts）
$$\text{Payoff} = \begin{cases} 0, & S_T \le K_1 \\ S_T - K_1, & K_1 < S_T \le K_2 \\ K_3 - S_T, & K_2 < S_T < K_3 \\ 0, & S_T \ge K_3 \end{cases}$$
- $K_1 < K_2 < K_3$、$K_2 = (K_1 + K_3)/2$

### Straddle payoff
$$\text{Payoff} = \begin{cases} K - S_T, & S_T \le K \\ S_T - K, & S_T > K \end{cases} = |S_T - K|$$

### Strangle payoff（$K_1 < K_2$）
$$\text{Payoff} = \begin{cases} K_1 - S_T, & S_T \le K_1 \\ 0, & K_1 < S_T < K_2 \\ S_T - K_2, & S_T \ge K_2 \end{cases}$$
- $K_1$: プット行使価格（低）、$K_2$: コール行使価格（高）

### Covered call / Protective put（put-call parityによる等価性）
$$S_0 - c = Ke^{-rT} + D - p \quad \Rightarrow \quad \text{covered call} \equiv \text{short put（+cash）}$$
$$p + S_0 = c + Ke^{-rT} + D \quad \Rightarrow \quad \text{protective put} \equiv \text{long call（+cash）}$$

## 4. アルゴリズム / 手順

戦略選択ガイド（相場観 × ボラティリティ観）：

| 相場観 | ボラティリティ観 | 推奨戦略 |
|--------|-----------------|---------|
| 強気（上昇） | 無関心 | Bull call spread（保守的）または naked long call（積極的） |
| 弱気（下落） | 無関心 | Bear put spread または naked long put |
| 中立（横ばい） | 低い | Butterfly spread（long）、calendar spread（long） |
| 中立（横ばい） | 低い | Covered call（株保有者向け） |
| 方向不明 | 高い | Straddle（コスト高だがシンプル） |
| 方向不明 | 高い | Strangle（コスト低、より大きな動きが必要） |
| 方向不明・下落寄り | 高い | Strip |
| 方向不明・上昇寄り | 高い | Strap |
| 元本保護＋上昇参加 | 中 | Principal-protected note（ゼロクーポン債＋ATM call） |
| 裁定（価格乖離） | — | Box spread（European optionsのみ） |

戦略セットアップ手順（bull call spreadを例に）：

1. 行使価格 $K_1$（ATM付近）のコールを買う（プレミアム $c_1$ 支払い）
2. 行使価格 $K_2 > K_1$ のコールを売る（プレミアム $c_2$ 受取り）
3. 純コスト = $c_1 - c_2 > 0$
4. 最大利益 = $K_2 - K_1 - (c_1 - c_2)$、最大損失 = $c_1 - c_2$
5. 損益分岐点 = $K_1 + (c_1 - c_2)$

## 5. Python reference

```python
import numpy as np

# ── Payoff functions (all take array-like S_T) ──────────────────────────────

def bull_call_spread(S: np.ndarray, K1: float, K2: float) -> np.ndarray:
    """Bull spread payoff using calls. K1 < K2."""
    return np.clip(S - K1, 0, K2 - K1)

def bear_put_spread(S: np.ndarray, K1: float, K2: float) -> np.ndarray:
    """Bear spread payoff using puts. K1 < K2 (long K2 put, short K1 put)."""
    return np.clip(K2 - S, 0, K2 - K1)

def butterfly(S: np.ndarray, K1: float, K2: float, K3: float) -> np.ndarray:
    """Long butterfly payoff (calls or puts). K2 = (K1+K3)/2."""
    return (np.maximum(S - K1, 0)
            - 2 * np.maximum(S - K2, 0)
            + np.maximum(S - K3, 0))

def straddle(S: np.ndarray, K: float) -> np.ndarray:
    """Long straddle payoff (long call + long put, same K)."""
    return np.abs(S - K)

def strangle(S: np.ndarray, K1: float, K2: float) -> np.ndarray:
    """Long strangle payoff. K1 = put strike (low), K2 = call strike (high)."""
    return np.maximum(K1 - S, 0) + np.maximum(S - K2, 0)

def box_spread(K1: float, K2: float, r: float, T: float) -> float:
    """Theoretical value of a box spread (European options only)."""
    return (K2 - K1) * np.exp(-r * T)

def strip(S: np.ndarray, K: float) -> np.ndarray:
    """Strip payoff: long 1 call + long 2 puts."""
    return np.maximum(S - K, 0) + 2 * np.maximum(K - S, 0)

def strap(S: np.ndarray, K: float) -> np.ndarray:
    """Strap payoff: long 2 calls + long 1 put."""
    return 2 * np.maximum(S - K, 0) + np.maximum(K - S, 0)

# ── Profit = payoff − initial cost ──────────────────────────────────────────

def profit(payoff_fn, S, cost, **kwargs):
    """Generic profit = payoff - net premium paid."""
    return payoff_fn(S, **kwargs) - cost

# ── Plotting example (commented out) ────────────────────────────────────────
# import matplotlib.pyplot as plt
#
# S = np.linspace(40, 90, 300)
# K1, K2, K3 = 55.0, 60.0, 65.0
# net_premium = 1.0  # e.g. buy K1@10, sell 2xK2@7, buy K3@5 → cost=1
#
# fig, ax = plt.subplots()
# ax.plot(S, butterfly(S, K1, K2, K3) - net_premium, label="Butterfly profit")
# ax.axhline(0, color="black", linewidth=0.8)
# ax.set_xlabel("Stock price at expiry $S_T$")
# ax.set_ylabel("Profit ($)")
# ax.set_title(f"Butterfly spread  K1={K1}  K2={K2}  K3={K3}")
# ax.legend()
# plt.tight_layout()
# plt.show()
```

## 6. 注意点 / 典型的なミス

- **Box spreadにAmericanオプションを使わない**: ボックスのペイオフ $(K_2-K_1)$ はEuropeanオプションを前提とする。Americanオプションでは早期行使リスクがあり、公正価値より高い価格で売るつもりが損失を被ることがある（Business Snapshot 12.1 参照）。
- **ストラドルの期待値は市場価格に織り込まれる**: 大きな値動きが予想されるイベント（M&A、訴訟等）では、すでにIVが上昇しているためストラドルが割高になっている可能性が高い。差別化した見解がなければ期待リターンは低い。
- **bull spreadのコールとプットで初期キャッシュフローが逆**: コールbull spreadは純支払い（debit）、プットbull spreadは純受取り（credit）。どちらも同じペイオフプロファイルだが証拠金要件が異なる。
- **butterfly spreadのK2は中間点**: $K_2 \ne (K_1+K_3)/2$ の場合、ペイオフは非対称になり Table 12.4 の式が成立しない。
- **calendar spreadの損益は評価時点に依存**: 通常、短期オプション満期時点での損益として図示される。長期オプションの時間価値がまだ残っている点を忘れないこと。
- **protective putは保険であり「無料」ではない**: プットプレミアムは保険料であり、保有期間中に消耗する。株価が横ばいでも継続的なコストが発生する。
- **ストラングルはストラドルより幅広い動きが必要**: 行使価格の間の範囲では利益がゼロであり、損益分岐点はストラドルより遠い。

## 7. 関連トピック

- See: [Ch.10](ch10_options_mechanics.md) — オプション市場の仕組み・基本ペイオフ
- See: [Ch.11](ch11_option_properties.md) — プット・コール・パリティ、オプション価格の上下限
- See: Ch.17 — 株価指数・通貨オプション、レンジフォワード
- See: Ch.19 — グリーク文字によるリスク管理（delta, gamma, vega）
- See: Ch.26 — エキゾチックオプション、静的レプリケーション
