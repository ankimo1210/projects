# Topic: Exotic Options

## 対応章
- Ch.26 Exotic Options — [chapters/ch26_exotics.md](../chapters/ch26_exotics.md)

## クイック公式

### Forward-start option (ATM at $T_1$)
$$V_0 = c \cdot e^{-qT_1}$$
- $c$: 残存期間 $T_2 - T_1$ の ATM コール現在価値；無配当株では通常の ATM コールと同値
- Cliquet: フォワードスタートの系列の合計
- See: ch26 §26.5

### Chooser option
$$V = c(K, T_2) + e^{-q(T_2-T_1)} p\!\left(Ke^{-(r-q)(T_2-T_1)},\, T_1\right)$$
- 同一 $K$ のコール（満期 $T_2$）と割引プット（満期 $T_1$、行使 $Ke^{-(r-q)(T_2-T_1)}$）のパッケージ
- See: ch26 §26.6

### Barrier option: key parameters
$$\lambda = \frac{r-q+\sigma^2/2}{\sigma^2}, \quad y = \frac{\ln[H^2/(S_0 K)]}{\sigma\sqrt{T}} + \lambda\sigma\sqrt{T}$$
$$x_1 = \frac{\ln(S_0/H)}{\sigma\sqrt{T}} + \lambda\sigma\sqrt{T}, \quad y_1 = \frac{\ln(H/S_0)}{\sigma\sqrt{T}} + \lambda\sigma\sqrt{T}$$
**Down-and-in call** ($H \le K$):
$$c_{\mathrm{di}} = S_0 e^{-qT}(H/S_0)^{2\lambda}N(y) - Ke^{-rT}(H/S_0)^{2\lambda-2}N(y-\sigma\sqrt{T})$$
**ノックイン + ノックアウト = バニラ**: $c_{\mathrm{di}} + c_{\mathrm{do}} = c$
- See: ch26 §26.9

### Binary / Digital options
$$c_{\mathrm{con}} = Qe^{-rT}N(d_2), \quad c_{\mathrm{aon}} = S_0 e^{-qT}N(d_1)$$
$$p_{\mathrm{con}} = Qe^{-rT}N(-d_2), \quad p_{\mathrm{aon}} = S_0 e^{-qT}N(-d_1)$$
- バニラ分解: $c_{\mathrm{vanilla}} = c_{\mathrm{aon}}(K) - K \cdot c_{\mathrm{con}}(K)$
- See: ch26 §26.10

### Asian geometric call（連続平均、閉形式）
Modified BSM に $\sigma_a = \sigma/\sqrt{3}$, $b = \tfrac{1}{2}(r-q-\sigma^2/6)$ を代入
$$d_1 = \frac{\ln(S/K) + (b+\tfrac{1}{2}\sigma_a^2)T}{\sigma_a\sqrt{T}}, \quad V = Se^{(b-r)T}N(d_1) - Ke^{-rT}N(d_2)$$
- 算術平均アジアンに閉形式なし → モーメント整合近似 (Turnbull-Wakeman) または MC
- See: ch26 §26.13

### Margrabe exchange option
$$V = V_0 e^{-q_V T}N(d_1) - U_0 e^{-q_U T}N(d_2), \quad \hat\sigma = \sqrt{\sigma_V^2+\sigma_U^2-2\rho\sigma_V\sigma_U}$$
$$d_1 = \frac{\ln(V_0/U_0)+(q_U-q_V+\hat\sigma^2/2)T}{\hat\sigma\sqrt{T}}, \quad d_2 = d_1 - \hat\sigma\sqrt{T}$$
- 無リスク金利 $r$ に依存しない（成長率増加と割引率上昇が相殺）
- See: ch26 §26.15, eq.(26.5)

### Quanto adjustment (domestic drift)
$$\mu^d = \mu^f - \rho\,\sigma_S\,\sigma_V$$
- 外国資産の国内リスク中立測度でのドリフト補正；$\rho$: 資産と為替の相関
- See: ch26 §26.16, ch30 eq.(30.7)

### Variance swap fair rate (log-contract replication)
$$\hat{E}[\bar{V}] \approx \frac{2}{T}\sum_{i=1}^n \frac{\Delta K_i}{K_i^2}e^{rT}Q(K_i) + \text{log-term}$$
- OTM オプションのストリップで静的複製；スキューがない仮定下のみ完全
- See: ch26 §26.17, eq.(26.10)

## 実装スニペット

```python
import math
import numpy as np
from scipy.stats import norm


def asian_geometric_call(S, K, r, sigma, T, q=0.0):
    """Closed-form geometric Asian call (continuous average, modified BSM).
    Hull §26.13.
    """
    sigma_a = sigma / math.sqrt(3.0)
    b = 0.5 * (r - q - sigma**2 / 6.0)
    d1 = (math.log(S/K) + (b + 0.5*sigma_a**2)*T) / (sigma_a*math.sqrt(T))
    d2 = d1 - sigma_a * math.sqrt(T)
    return S * math.exp((b - r)*T) * norm.cdf(d1) - K * math.exp(-r*T) * norm.cdf(d2)


def asian_arithmetic_call_mc(S, K, r, sigma, T,
                              n_steps=252, n_paths=50_000, q=0.0, rng=None):
    """Arithmetic average Asian call via MC with geometric control variate.
    Hull §26.13 + control variate variance reduction.
    """
    rng = rng or np.random.default_rng(0)
    dt = T / n_steps
    drift = (r - q - 0.5 * sigma**2) * dt
    vol = sigma * math.sqrt(dt)
    Z = rng.standard_normal((n_paths, n_steps))
    log_paths = np.log(S) + np.cumsum(drift + vol * Z, axis=1)
    paths = np.exp(log_paths)
    disc = math.exp(-r * T)
    arith_pay = np.maximum(paths.mean(axis=1) - K, 0.0) * disc
    geom_pay  = np.maximum(np.exp(np.log(paths).mean(axis=1)) - K, 0.0) * disc
    geom_true = asian_geometric_call(S, K, r, sigma, T, q)
    beta = np.cov(arith_pay, geom_pay)[0, 1] / np.var(geom_pay)
    adj = arith_pay - beta * (geom_pay - geom_true)
    return float(adj.mean()), float(adj.std(ddof=1) / math.sqrt(n_paths))


def barrier_down_and_out_call_mc(S, K, H, r, sigma, T,
                                  n_steps=252, n_paths=50_000, rng=None):
    """Down-and-out call via MC (discrete monitoring). Hull §26.9."""
    rng = rng or np.random.default_rng(1)
    dt = T / n_steps
    drift = (r - 0.5 * sigma**2) * dt
    vol = sigma * math.sqrt(dt)
    Z = rng.standard_normal((n_paths, n_steps))
    paths = np.exp(np.log(S) + np.cumsum(drift + vol * Z, axis=1))
    alive = paths.min(axis=1) > H
    payoff = np.where(alive, np.maximum(paths[:, -1] - K, 0.0), 0.0)
    disc = payoff * math.exp(-r * T)
    return float(disc.mean()), float(disc.std(ddof=1) / math.sqrt(n_paths))


def margrabe_exchange(V0, U0, sigma_v, sigma_u, rho, q_v, q_u, T):
    """Margrabe formula: right to receive V and give up U. Hull eq. (26.5)."""
    sigma_hat = math.sqrt(sigma_v**2 + sigma_u**2 - 2*rho*sigma_v*sigma_u)
    d1 = (math.log(V0/U0) + (q_u - q_v + 0.5*sigma_hat**2)*T) / (sigma_hat*math.sqrt(T))
    d2 = d1 - sigma_hat * math.sqrt(T)
    return V0*math.exp(-q_v*T)*norm.cdf(d1) - U0*math.exp(-q_u*T)*norm.cdf(d2)
```

## デシジョンガイド

**閉形式 vs MC vs PDE**
| オプション種別 | 推奨手法 | 注意点 |
|---|---|---|
| 幾何平均アジアン | 修正 BSM 閉形式 | 連続平均仮定；離散版は近似 |
| 算術平均アジアン | MC + 幾何平均コントロール変量 | 閉形式なし；CVのみで標準誤差 10 倍以上改善 |
| バリア（連続モニタリング） | 閉形式（$\lambda, y, x_1, y_1$ パラメータ） | knock-in + knock-out = vanilla の check |
| バリア（離散モニタリング） | MC + Brownian-bridge 補正 | 補正なし MC はノックアウトを過大評価（安く出る） |
| ルックバック | 連続モニタリング閉形式または MC | 離散モニタリングとの乖離に注意；BGK 補正が利用可能 |
| Margrabe（exchange） | 閉形式 | $r$ 依存なし；$\hat\sigma$ を両方の $\sigma$ から計算 |
| Binary | 閉形式 | 行使価格付近で価格操作インセンティブ発生 |
| Compound | Geske 閉形式（二変量正規分布） | $S^*$（臨界資産価格）を数値的に解く |

**バリア MC の Brownian-bridge 補正**
- 離散モニタリングバリアは連続モニタリング解析値より安く出る（ノックアウト）
- Broadie-Glasserman-Kou 補正: バリア $H$ を $He^{\pm 0.5826\sigma\sqrt{T/m}}$ に調整
- 精度が必要な場合は必ず適用；ステップ数を増やすだけでは収束が遅い

**算術平均アジアンのコントロール変量**
- 幾何平均アジアン（閉形式値が既知）をコントロール変量として使う
- $\hat{P}_A = P_A - \beta(P_G - P_G^*)$ の平均を取る（$\beta$ は回帰係数）
- 分散削減率は大きく、必要パス数を 10〜100 倍程度削減できる

**バリアンス・スワップの複製とスキュー**
- ログ・コントラクト = OTM オプションのストリップ（$\Delta K_i / K_i^2$ ウェイト）
- 「スキューなし」仮定下のみ静的複製が完全；スキューがあると動的ヘッジが必要
- VIX 計算はこのフレームワークの離散近似版

**Quanto 調整の方向**
- $\rho > 0$（資産と為替が正相関）: 国内期待値 > 外国期待値
- 日経 225 と円/ドル: 一般に $\rho < 0$ → 国内期待値 < 外国期待値
- 調整を忘れるとクオントデリバティブが系統的に誤価格される
