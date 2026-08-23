# Ch.11 Properties of Stock Options

> **Source**: Hull 11e, Chapter 11 (pp. 247-267). Paraphrased summary for personal use.

## 1. 要点

- オプション価格に影響する6要因: 原資産価格 $S_0$、行使価格 $K$、満期 $T$、ボラティリティ $\sigma$、無リスク金利 $r$、配当。Table 11.1 にまとめられる。
- 裁定不等式によりオプション価格には上限・下限が定まる。コール上限は $S_0$、プット上限は $Ke^{-rT}$（欧州）または $K$（米国）。
- **プット・コール・パリティ**（欧州、無配当）: $c + Ke^{-rT} = p + S_0$。これはモデルフリーの裁定条件。
- 無配当株の米国コールは早期行使が最適でないため $C = c$。米国プットは深くインザマネーなら早期行使が合理的で $P > p$。
- 配当があるとコールの早期行使が権利落ち直前で合理的になり得る。配当付きプット・コール・パリティは $c + D + Ke^{-rT} = p + S_0$。

## 2. キー用語

- **$c, p$**: 欧州コール・プットの価格
- **$C, P$**: 米国コール・プットの価格
- **$S_0$**: 現在の株価
- **$K$**: 行使価格（ストライク）
- **$T$**: 満期までの時間（年）
- **$r$**: 連続複利の無リスク金利
- **$D$**: オプション有効期間中の配当の現在価値（離散）
- **$q$**: 連続配当利回り
- **プット・コール・パリティ**: 同一満期・行使価格の欧州コールとプットの間の無裁定等式
- **下限 (lower bound)**: これを下回る価格は裁定機会を生む最低価格水準
- **早期行使プレミアム**: $P - p \ge 0$（米国プットが欧州プットより高い理由）
- **イントリンシック・バリュー (intrinsic value)**: コール $\max(S_0 - K, 0)$、プット $\max(K - S_0, 0)$

## 3. 主要公式

### 上限: コール（欧州・米国）
$$c \le S_0, \quad C \le S_0$$
<!-- Hull eq. (11.1) -->
- コールは株そのものより高くなれない。

### 上限: プット（米国）
$$P \le K$$
<!-- Hull eq. (11.2) -->
- 株価が0になっても利益は $K$ を超えない。

### 上限: プット（欧州）
$$p \le Ke^{-rT}$$
<!-- Hull eq. (11.3) -->
- 満期時点で $K$ 以上にならないため現在価値が上限。

### 下限: 欧州コール（無配当）
$$c \ge \max(S_0 - Ke^{-rT},\; 0)$$
<!-- Hull eq. (11.4) -->
- 導出: ポートフォリオA（コール＋割引債 $Ke^{-rT}$）≥ ポートフォリオB（株1株）

### 下限: 欧州プット（無配当）
$$p \ge \max(Ke^{-rT} - S_0,\; 0)$$
<!-- Hull eq. (11.5) -->
- 導出: ポートフォリオC（プット＋株）≥ ポートフォリオD（割引債 $Ke^{-rT}$）

### プット・コール・パリティ（欧州、無配当）
$$c + Ke^{-rT} = p + S_0$$
<!-- Hull eq. (11.6) -->
- 両辺が同じペイオフ $\max(S_T, K)$ を持つため等値。

### プット・コール・パリティ（欧州、連続配当利回り $q$）
$$c + Ke^{-rT} = p + S_0 e^{-qT}$$
- $S_0$ を $S_0 e^{-qT}$（配当落ち後の現在価値）に置き換え。

### プット・コール・パリティ（欧州、離散配当 $D$）
$$c + D + Ke^{-rT} = p + S_0$$
<!-- Hull eq. (11.10) -->
- $D$ はオプション有効期間中の配当の現在価値。

### 米国オプション: コール ≥ 欧州コール、プット ≥ 欧州プット
$$C \ge c, \quad P \ge p$$
- 米国オプションは欧州オプションの早期行使権を含むため常に同値以上。
- 無配当株では $C = c$（早期行使が最適でない）。

### 米国プット・コール不等式（無配当）
$$S_0 - K \le C - P \le S_0 - Ke^{-rT}$$
<!-- Hull eq. (11.7) -->
- 等式でなく不等式になるのは米国オプションの早期行使可能性のため。

### 配当付き米国プット・コール不等式
$$S_0 - D - K \le C - P \le S_0 - Ke^{-rT}$$
<!-- Hull eq. (11.11) -->

### Table 11.1: 変数がオプション価格に与える影響

| 変数が増加 | 欧州コール $c$ | 欧州プット $p$ | 米国コール $C$ | 米国プット $P$ |
|---|---|---|---|---|
| 株価 $S_0$ | + | − | + | − |
| 行使価格 $K$ | − | + | − | + |
| 満期 $T$ | ? | ? | + | + |
| ボラティリティ $\sigma$ | + | + | + | + |
| 無リスク金利 $r$ | + | − | + | − |
| 配当額 | − | + | − | + |

（+: 増加または不変、−: 減少または不変、?: 不確定）

## 4. アルゴリズム / 手順

### シンセティック・プットの構築（プット・コール・パリティから）

1. パリティ式 $p = c + Ke^{-rT} - S_0$ を使う。
2. 欧州コール1単位を購入する（価格 $c$）。
3. 現価値 $Ke^{-rT}$ の割引債（ゼロクーポン債）を購入する。
4. 株を1株空売り（ショート）する。
5. 合成プットのコスト = $c + Ke^{-rT} - S_0$。これが $p$ と等しくなければ裁定機会。

### 米国コールの早期行使判断（無配当株）

1. $C \ge c \ge S_0 - Ke^{-rT} > S_0 - K$（$r > 0, T > 0$ のとき）を確認。
2. 早期行使すると得られるのはイントリンシック・バリュー $S_0 - K$ のみ。
3. 待てば: (a) $K$ の支払いを遅らせ金利を稼げる、(b) 株価下落への保険が残る。
4. **結論**: 無配当株の米国コールは早期行使が最適でなく $C = c$。

### 米国プットの早期行使判断（無配当株）

1. 株価が十分低い（深くインザマネー）かどうかを確認。
2. 即時行使の利益 = $K - S_0$（現時点で受取り、金利 $r$ で運用可能）。
3. 待つことの損失: 金利逸失 + 株価反発リスク（保険価値は低下）。
4. 早期行使が魅力的になる条件: $S_0$ 低下・$r$ 上昇・$\sigma$ 低下。
5. **結論**: $P > p$。深くインザマネーならば即時行使が最適になり得る。

### 配当付きコールの早期行使判断

1. 早期行使を検討するのは配当の権利落ち日直前のみ。
2. 権利落ちによる株価下落額 $\approx D_i$ が「待つメリット」（金利＋保険）を上回るか確認。
3. 上回る場合のみ早期行使が最適。それ以外のタイミングでは早期行使しない。

## 5. Python reference

```python
import math

def put_call_parity_check(c: float, p: float, S: float, K: float,
                           r: float, T: float, q: float = 0.0) -> float:
    """
    Returns LHS - RHS of put-call parity.
    No dividends (q=0):  c + K*exp(-rT) = p + S*exp(-qT)
    With continuous yield q: same formula with S*exp(-qT).
    A nonzero result indicates a parity violation (potential arbitrage).
    """
    lhs = c + K * math.exp(-r * T)
    rhs = p + S * math.exp(-q * T)
    return lhs - rhs


def lower_bounds(S: float, K: float, r: float, T: float,
                 q: float = 0.0, D: float = 0.0) -> tuple[float, float]:
    """
    Returns (call_lower_bound, put_lower_bound) for European options.
    D: present value of discrete dividends during option life.
    q: continuous dividend yield (use one or the other, not both).
    """
    disc = math.exp(-r * T)
    S_adj = S * math.exp(-q * T)          # stock adjusted for continuous yield
    call_lb = max(S_adj - D - K * disc, 0.0)
    put_lb  = max(K * disc + D - S_adj, 0.0)
    return call_lb, put_lb


def american_put_call_bounds(S: float, K: float, r: float, T: float) -> tuple[float, float]:
    """
    Returns (lower, upper) bounds for C - P (American, no dividends).
    Hull eq. (11.7): S0 - K <= C - P <= S0 - K*exp(-rT)
    """
    return S - K, S - K * math.exp(-r * T)


# --- Numerical example (Hull Example 11.1 / parity illustration) ---
# European call: S=31, K=30, r=10%, T=0.25 yr, c=3, p=?
S, K, r, T = 31.0, 30.0, 0.10, 0.25
c = 3.0

# From parity: p = c + K*exp(-rT) - S
p_parity = c + K * math.exp(-r * T) - S
print(f"Implied put price from parity: {p_parity:.4f}")  # ≈ 1.2592

# Parity check with market put = 2.25 (overpriced put case)
p_market = 2.25
diff = put_call_parity_check(c, p_market, S, K, r, T)
print(f"Parity violation (>0 means RHS overpriced): {diff:.4f}")  # ≈ -0.99

# Lower bounds for call and put
call_lb, put_lb = lower_bounds(S=51, K=50, r=0.12, T=0.5)
print(f"Call lower bound (Hull Ex.11.1): {call_lb:.4f}")  # ≈ 3.91
put_lb2, _ = lower_bounds(S=38, K=40, r=0.10, T=0.25)[1], None
print(f"Put lower bound  (Hull Ex.11.2): {lower_bounds(38, 40, 0.10, 0.25)[1]:.4f}")  # ≈ 1.01
```

## 6. 注意点 / 典型的なミス

- **プット上限の違い**: 欧州プットの上限は $Ke^{-rT}$、米国プットの上限は $K$。早期行使できる米国プットは $K$ をすぐ受け取れるため割引なし。
- **満期と欧州オプション価値の関係**: 欧州オプションは必ずしも満期延長で価値増大しない。配当の大きい株では短期の方が高いケースがある（Table 11.1 の "?" に注意）。
- **$C = c$ の前提**: 「無配当」かつ「$r > 0$」が必要。配当があれば $C > c$ になり得る。
- **パリティは欧州専用**: 米国オプションにはパリティではなく不等式 (11.7) のみ成立。$C - P$ の範囲を特定できるが等式にはならない。
- **合成プットのデルタ管理**: 実際に $p = c - S + Ke^{-rT}$ を使ったシンセティック戦略では、株価変動に合わせてリバランスが必要（静的複製ではない）。
- **配当 $D$ の現在価値タイミング**: $D$ は配当支払時点で割引く。オプション満期後に支払われる配当は含めない。
- **ボラティリティと金利の独立仮定**: Table 11.1 の結果は「他の変数が一定」の場合。実際には金利上昇→株価下落が連動し、コール価値が下がる場合がある。

## 7. 関連トピック

- Ch.10: オプションの仕組み（コール・プットの定義、市場慣行）
- Ch.12: オプションを使ったトレーディング戦略（スプレッド、コンビネーション）
- Ch.15: Black-Scholes-Merton モデル（欧州オプションの厳密な価格公式）
- Ch.17: 株価指数・通貨オプション（連続配当利回り $q$ の適用）
- Ch.21: 米国オプションの数値計算（二項モデルによる早期行使価値の評価）
- See: [topics/options_basics.md](../topics/options_basics.md)
