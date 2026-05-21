"""
patch_bsm_nb.py — bsm_chapter15.ipynb を差分修正するスクリプト
実行: python3 patch_bsm_nb.py
"""
import json, random

random.seed(9999)

def make_id():
    return format(random.randint(0, 0xFFFFFFFF), "08x")

def to_lines(s: str):
    """複数行文字列を Jupyter source 形式（末尾 \\n つきリスト）に変換する。"""
    raw = s.split("\n")
    result = []
    for i, line in enumerate(raw):
        if i < len(raw) - 1:
            result.append(line + "\n")
        elif line:            # 最後の行が空でなければ追加
            result.append(line)
    return result

def md_cell(s):
    return {"cell_type": "markdown", "id": make_id(), "metadata": {}, "source": to_lines(s)}

def code_cell(s):
    return {"cell_type": "code", "id": make_id(), "execution_count": None,
            "metadata": {}, "outputs": [], "source": to_lines(s)}


# ===========================================================================
# 新しいコードセル [04] — 共通関数  (updated)
# ===========================================================================
NEW_COMMON_FUNCTIONS = """\
# ===== 2-1. GBM シミュレーション =====

def simulate_gbm_paths(S0, mu, sigma, T, n_steps, n_paths, rng):
    \"\"\"幾何ブラウン運動のサンプルパスを生成する。

    Parameters
    ----------
    S0 : float  -- 初期価格
    mu : float  -- ドリフト (年率)
    sigma : float  -- ボラティリティ (年率; >= 0)
    T : float  -- 期間 (年; > 0)
    n_steps : int  -- 時間ステップ数
    n_paths : int  -- パス数
    rng : np.random.Generator

    Returns
    -------
    t : ndarray, shape (n_steps+1,)
    S : ndarray, shape (n_paths, n_steps+1)
    \"\"\"
    dt = T / n_steps
    t = np.linspace(0, T, n_steps + 1)
    Z = rng.standard_normal((n_paths, n_steps))
    log_increments = (mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * Z
    log_S = np.zeros((n_paths, n_steps + 1))
    log_S[:, 0] = np.log(S0)
    log_S[:, 1:] = np.log(S0) + np.cumsum(log_increments, axis=1)
    S = np.exp(log_S)
    return t, S


# ===== 2-2. 対数収益率 =====

def compute_log_returns(prices):
    \"\"\"価格系列から対数収益率を計算する。\"\"\"
    prices = np.asarray(prices, dtype=float)
    return np.diff(np.log(prices))


# ===== 2-3. 年率化ボラティリティ =====

def annualized_volatility(log_returns, periods_per_year=252):
    \"\"\"対数収益率の標準偏差を年率化する。\"\"\"
    return np.std(log_returns, ddof=1) * np.sqrt(periods_per_year)


# ===== 2-4. 入力バリデーションヘルパー  [updated] =====

def _validate_bsm_inputs(S, K, T, sigma):
    \"\"\"BSM 関数の入力を検証する。不正値のとき ValueError を送出する。\"\"\"
    S_arr = np.asarray(S, dtype=float)
    if np.any(S_arr <= 0):
        raise ValueError(f"S は正の値でなければなりません (受け取った値: {S_arr})")
    if K <= 0:
        raise ValueError(f"K は正の値でなければなりません (受け取った値: {K})")
    if T < 0:
        raise ValueError(f"T は 0 以上でなければなりません (受け取った値: {T})")
    if sigma < 0:
        raise ValueError(f"sigma は 0 以上でなければなりません (受け取った値: {sigma})")


# ===== 2-5. BSM d1, d2  [updated: edge case handling] =====

def bsm_d1_d2(S, K, T, r, sigma):
    \"\"\"BSM 公式の d1, d2 を計算する。

    Parameters
    ----------
    S : float または array  -- 現在の株価 (> 0)
    K : float  -- 行使価格 (> 0)
    T : float  -- 満期までの時間 (年; >= 0)
    r : float  -- 無リスク金利 (連続複利)
    sigma : float  -- ボラティリティ (年率; >= 0)

    Returns
    -------
    d1, d2 : float または ndarray
        T == 0 または sigma == 0 の場合は (nan, nan) を返す。
        呼び出し側の価格/デルタ関数がエッジケース処理を行う。

    Raises
    ------
    ValueError : S <= 0, K <= 0, T < 0, sigma < 0 のとき
    \"\"\"
    _validate_bsm_inputs(S, K, T, sigma)
    S_arr = np.asarray(S, dtype=float)
    denom = float(sigma) * np.sqrt(float(T))  # sigma, T ともにスカラーを前提
    if denom == 0.0:
        # T==0 または sigma==0 → 標準式は適用不可; nan を返し呼び出し側で処理
        nan_val = np.full_like(S_arr, np.nan) if S_arr.ndim > 0 else np.nan
        return nan_val, nan_val
    d1 = (np.log(S_arr / K) + (r + 0.5 * sigma**2) * T) / denom
    d2 = d1 - denom
    return d1, d2


# ===== 2-6. BSM Call / Put  [updated: edge cases] =====

def bsm_call_price(S, K, T, r, sigma):
    \"\"\"European call の BSM 価格。

    Edge cases
    ----------
    T == 0     : max(S - K, 0)            （満期ペイオフ）
    sigma == 0 : max(S - K*exp(-r*T), 0)  （確定的 forward の割引現在価値）
    \"\"\"
    _validate_bsm_inputs(S, K, T, sigma)
    S = np.asarray(S, dtype=float)
    if T == 0.0:
        return np.maximum(S - K, 0.0)          # updated: 満期ペイオフ
    if sigma == 0.0:
        return np.maximum(S - K * np.exp(-r * T), 0.0)  # updated: vol=0
    d1, d2 = bsm_d1_d2(S, K, T, r, sigma)
    return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)


def bsm_put_price(S, K, T, r, sigma):
    \"\"\"European put の BSM 価格。

    Edge cases
    ----------
    T == 0     : max(K - S, 0)
    sigma == 0 : max(K*exp(-r*T) - S, 0)
    \"\"\"
    _validate_bsm_inputs(S, K, T, sigma)
    S = np.asarray(S, dtype=float)
    if T == 0.0:
        return np.maximum(K - S, 0.0)          # updated
    if sigma == 0.0:
        return np.maximum(K * np.exp(-r * T) - S, 0.0)  # updated
    d1, d2 = bsm_d1_d2(S, K, T, r, sigma)
    return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)


# ===== 2-7. BSM Delta  [updated: edge cases] =====

def bsm_call_delta(S, K, T, r, sigma):
    \"\"\"European call の delta（dC/dS）。

    Edge cases
    ----------
    T == 0     : S > K → 1, S < K → 0, S == K → 0.5（不連続点の中点規則）
    sigma == 0 : S > K*exp(-rT) → 1, それ以外 → 0（確定的 forward に対応）
    \"\"\"
    _validate_bsm_inputs(S, K, T, sigma)
    S = np.asarray(S, dtype=float)
    if T == 0.0:
        # updated: 満期での delta は不連続; 慣例として中点を 0.5 とする
        return np.where(S > K, 1.0, np.where(S < K, 0.0, 0.5))
    if sigma == 0.0:
        forward_pv = K * np.exp(-r * T)
        return np.where(S > forward_pv, 1.0, 0.0)  # updated
    d1, _ = bsm_d1_d2(S, K, T, r, sigma)
    return norm.cdf(d1)


def bsm_put_delta(S, K, T, r, sigma):
    \"\"\"European put の delta（dP/dS）。

    Edge cases
    ----------
    T == 0     : S > K → 0, S < K → -1, S == K → -0.5
    sigma == 0 : S > K*exp(-rT) → 0, それ以外 → -1
    \"\"\"
    _validate_bsm_inputs(S, K, T, sigma)
    S = np.asarray(S, dtype=float)
    if T == 0.0:
        return np.where(S > K, 0.0, np.where(S < K, -1.0, -0.5))  # updated
    if sigma == 0.0:
        forward_pv = K * np.exp(-r * T)
        return np.where(S > forward_pv, 0.0, -1.0)  # updated
    d1, _ = bsm_d1_d2(S, K, T, r, sigma)
    return norm.cdf(d1) - 1.0


# ===== 2-8. Put-Call Parity =====

def put_call_parity_gap(S, K, T, r, call_price, put_price):
    \"\"\"Put-call parity の残差を返す。C - P - (S - K*exp(-rT)) = 0 が成立するなら 0。\"\"\"
    return call_price - put_price - (S - K * np.exp(-r * T))


# ===== 2-9. BSM Vega  [updated: edge cases] =====

def bsm_vega(S, K, T, r, sigma):
    \"\"\"BSM Vega（call/put 共通）。T==0 または sigma==0 のとき 0 を返す。\"\"\"
    _validate_bsm_inputs(S, K, T, sigma)
    if T == 0.0 or sigma == 0.0:
        return 0.0  # updated: edge case
    d1, _ = bsm_d1_d2(S, K, T, r, sigma)
    return float(S) * norm.pdf(d1) * np.sqrt(T)


# ===== 2-10. Implied Volatility (Bisection)  [updated] =====

def implied_vol_bisection(market_price, S, K, T, r, option_type="call",
                          tol=1e-8, max_iter=200):
    \"\"\"二分法で implied volatility を求める。

    Parameters
    ----------
    market_price : float  -- 市場で観測されたオプション価格
    S, K, T, r   : float  -- BSM パラメータ
    option_type  : str    -- 'call' or 'put'
    tol          : float  -- 許容誤差（価格差の絶対値）
    max_iter     : int    -- 最大反復数

    Returns
    -------
    dict with keys
        iv         : float  -- 解のボラティリティ（不収束時は最終推定値または nan）
        history    : list   -- 各反復での sigma の推移
        converged  : bool
        iterations : int
        message    : str
    \"\"\"
    price_func = bsm_call_price if option_type == "call" else bsm_put_price
    disc = np.exp(-r * T)

    # updated: no-arbitrage bounds チェック
    if option_type == "call":
        lb = max(S - K * disc, 0.0)   # lower bound: intrinsic (discounted forward)
        ub = S                          # upper bound: call cannot exceed spot
    else:
        lb = max(K * disc - S, 0.0)    # lower bound: put intrinsic
        ub = K * disc                   # upper bound: put cannot exceed PV(K)

    if market_price < lb - tol:
        msg = (f"市場価格 {market_price:.4f} が no-arbitrage 下限 {lb:.4f} を"
               f"下回っています。IV を計算できません。")
        return {"iv": np.nan, "history": [], "converged": False,
                "iterations": 0, "message": msg}
    if market_price > ub + tol:
        msg = (f"市場価格 {market_price:.4f} が no-arbitrage 上限 {ub:.4f} を"
               f"上回っています。IV を計算できません。")
        return {"iv": np.nan, "history": [], "converged": False,
                "iterations": 0, "message": msg}

    lo, hi = 1e-6, 5.0
    history = []
    mid = 0.5 * (lo + hi)
    for i in range(max_iter):
        mid = 0.5 * (lo + hi)
        history.append(mid)
        diff = price_func(S, K, T, r, mid) - market_price
        if abs(diff) < tol:
            return {"iv": mid, "history": history, "converged": True,
                    "iterations": i + 1, "message": "収束しました"}
        if diff > 0:
            hi = mid
        else:
            lo = mid

    return {"iv": mid, "history": history, "converged": False,
            "iterations": max_iter,
            "message": f"最大反復数 {max_iter} に達しました（不収束）"}


# ===== 2-11. Implied Volatility (Newton)  [updated] =====

def implied_vol_newton(market_price, S, K, T, r, option_type="call",
                       sigma0=0.3, tol=1e-8, max_iter=100):
    \"\"\"Newton-Raphson 法で implied volatility を求める。

    Parameters
    ----------
    market_price : float
    S, K, T, r   : float
    option_type  : str    -- 'call' or 'put'
    sigma0       : float  -- 初期推定値（デフォルト 0.3）
    tol          : float  -- 許容誤差
    max_iter     : int    -- 最大反復数

    Returns
    -------
    dict with keys: iv, history, converged, iterations, message
    \"\"\"
    price_func = bsm_call_price if option_type == "call" else bsm_put_price
    sigma = sigma0
    history = [sigma]
    VEGA_MIN = 1e-8   # updated: vega が極端に小さいときは更新を停止
    SIGMA_MAX = 10.0  # updated: 発散ガード（sigma > 1000% は非現実的）

    for i in range(max_iter):
        price_est = price_func(S, K, T, r, sigma)
        diff = price_est - market_price
        if abs(diff) < tol:
            return {"iv": sigma, "history": history, "converged": True,
                    "iterations": i + 1, "message": "収束しました"}
        vega = bsm_vega(S, K, T, r, sigma)
        if vega < VEGA_MIN:
            # updated: vega 極小 → Newton step 不安定; 反復を停止
            return {"iv": sigma, "history": history, "converged": False,
                    "iterations": i + 1,
                    "message": f"Vega が {vega:.2e} と極小のため更新を停止しました"}
        sigma_new = sigma - diff / vega
        sigma_new = float(np.clip(sigma_new, 1e-6, SIGMA_MAX))  # updated: 発散・負値ガード
        history.append(sigma_new)
        sigma = sigma_new

    return {"iv": sigma, "history": history, "converged": False,
            "iterations": max_iter,
            "message": f"最大反復数 {max_iter} に達しました（不収束）"}


def implied_vol(market_price, S, K, T, r, option_type="call",
                sigma0=0.3, tol=1e-8, max_iter=100):
    \"\"\"Newton-Raphson を試み、失敗した場合は Bisection にフォールバックするラッパー。  [updated]

    Parameters / Returns は implied_vol_newton と同じ。
    \"\"\"
    result = implied_vol_newton(market_price, S, K, T, r, option_type,
                                sigma0=sigma0, tol=tol, max_iter=max_iter)
    if result["converged"]:
        return result
    # updated: Newton 失敗 → Bisection にフォールバック
    bi_result = implied_vol_bisection(market_price, S, K, T, r, option_type,
                                      tol=tol, max_iter=200)
    bi_result["message"] = ("Newton 法が収束せず Bisection にフォールバック: "
                             + bi_result["message"])
    return bi_result


# ===== 2-12. BSM with dividend yield =====

def bsm_call_with_dividend_yield(S, K, T, r, sigma, q):
    \"\"\"配当利回り q を考慮した European call の BSM 価格。T==0 のとき満期ペイオフを返す。\"\"\"
    S = np.asarray(S, dtype=float)
    if T == 0.0:
        return np.maximum(S - K, 0.0)
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)


def bsm_put_with_dividend_yield(S, K, T, r, sigma, q):
    \"\"\"配当利回り q を考慮した European put の BSM 価格。T==0 のとき満期ペイオフを返す。\"\"\"
    S = np.asarray(S, dtype=float)
    if T == 0.0:
        return np.maximum(K - S, 0.0)
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)


print("共通関数の定義が完了しました。")
"""

# ===========================================================================
# デルタヘッジの制約 — Markdown セル  [新規挿入: cell[14] の直後]
# ===========================================================================
DELTA_HEDGE_LIMITATIONS_MD = """\
> **注意: このデモが示していること・示していないこと**
>
> ここで可視化しているのは**現時点での局所的な価格変化に対する one-shot ヘッジ**です。
> 以下の要素は意図的に簡略化しています：
>
> | 簡略化している項目 | 実際の影響 |
> |---|---|
> | **時間経過** | $\\Delta t$ ごとに delta を再計算して再ヘッジ（re-hedging）が必要 |
> | **資金調達コスト** | 株のロングポジションを金利 $r$ で借り入れて構築 |
> | **離散再ヘッジ誤差** | 連続再ヘッジは理論上のみ; 現実は離散的 → gamma P&L が残る |
> | **ボラティリティ変化** | BSM は $\\sigma$ 一定を仮定しているが実際は変動する |
>
> したがって、ここの `pnl_hedged` がほぼゼロに見えるのは
> **「完全ヘッジの証明」ではなく**、
> BSM PDE の直感「デルタ量だけ株を保有すれば $\\delta S$ 1次のリスクが相殺される」
> を確認するための図です。
>
> 実際の連続デルタヘッジでの損益分析（gamma P&L など）は **Chapter 19（Greeks）**で扱います。
"""

# ===========================================================================
# Put-Call Parity sanity check  [新規挿入: cell[22] の直後]
# ===========================================================================
SANITY_PCP = """\
# --- [Sanity] 7-1. Put-call parity の残差確認  [updated: sanity check] ---
pcp_res = put_call_parity_gap(S_ex, K_ex, T_ex, r_ex, C_ex, P_ex)
print(f"Put-Call Parity Residual = {pcp_res:.2e}")
assert abs(pcp_res) < 1e-12, f"Put-call parity が成立していません: {pcp_res}"
print("-> OK: 残差が数値誤差 (< 1e-12) に収まっています")
"""

# ===========================================================================
# Bisection vs Newton 収束比較セル  [updated: dict 形式に対応]
# ===========================================================================
NEW_CELL_36 = """\
# --- 10-2. Bisection vs Newton 収束比較  [updated: dict 形式に対応] ---

res_bi = implied_vol_bisection(target_price, S_iv, K_iv, T_iv, r_iv)
res_nw = implied_vol_newton(target_price, S_iv, K_iv, T_iv, r_iv)

iv_bi  = res_bi["iv"]
hist_bi = res_bi["history"]
iv_nw  = res_nw["iv"]
hist_nw = res_nw["history"]

print(f"Bisection IV = {iv_bi:.8f}  ({res_bi['iterations']} iters, converged={res_bi['converged']})")
print(f"Newton    IV = {iv_nw:.8f}  ({res_nw['iterations']} iters, converged={res_nw['converged']})")
print(f"Bisection: {res_bi['message']}")
print(f"Newton:    {res_nw['message']}")

fig, ax = plt.subplots()
ax.plot(range(len(hist_bi)), hist_bi, "o-", markersize=3, label="Bisection")
ax.plot(range(len(hist_nw)), hist_nw, "s-", markersize=4, label="Newton-Raphson")
ax.axhline(iv_bi, color="gray", linestyle=":", alpha=0.5)
ax.set_title("IV Root-Finding: 収束過程の比較")
ax.set_xlabel("Iteration")
ax.set_ylabel(r"$\\sigma$ estimate")
ax.legend()
plt.tight_layout()
plt.show()
"""

# ===========================================================================
# IV round-trip sanity check  [新規挿入: cell[36] の直後]
# ===========================================================================
SANITY_IV_ROUNDTRIP = """\
# --- [Sanity] 10-2. IV round-trip 確認  [updated: sanity check] ---
# 逆算した IV を再度 BSM に入れると元の市場価格に戻ることを確認
roundtrip_price = bsm_call_price(S_iv, K_iv, T_iv, r_iv, iv_bi)
print(f"Round-trip: target={target_price:.6f}, BSM(IV)={roundtrip_price:.6f}, "
      f"diff={abs(roundtrip_price - target_price):.2e}")
assert abs(roundtrip_price - target_price) < 1e-6, "IV round-trip の残差が許容誤差を超えています"
print("-> OK: IV round-trip の残差が 1e-6 以内です")
"""

# ===========================================================================
# Strike 別 IV セル  [updated: dict 形式に対応]
# ===========================================================================
NEW_CELL_37 = """\
# --- 10-3. Strike 別 IV (Volatility Smile の入口) ---

# サンプルの市場オプション価格（人工データ: 軽い U字型 smile を仕込む）
strikes = np.array([80, 85, 90, 95, 100, 105, 110, 115, 120])
true_ivs = 0.20 + 0.0003 * (strikes - 100)**2  # 簡単な U 字型 smile

# 対応する市場価格を BSM で計算
market_prices = np.array([
    bsm_call_price(S_iv, k, T_iv, r_iv, iv) for k, iv in zip(strikes, true_ivs)
])

# IV を逆算  [updated: dict 形式に対応]
recovered_ivs = []
for k, mp in zip(strikes, market_prices):
    res = implied_vol_bisection(mp, S_iv, k, T_iv, r_iv)
    recovered_ivs.append(res["iv"])
recovered_ivs = np.array(recovered_ivs)

fig, ax = plt.subplots()
ax.plot(strikes, true_ivs * 100, "o-", label="True IV")
ax.plot(strikes, recovered_ivs * 100, "x--", label="Recovered IV")
ax.set_title("Strike vs Implied Volatility")
ax.set_xlabel("Strike Price $K$")
ax.set_ylabel("Implied Volatility (%)")
ax.legend()
plt.tight_layout()
plt.show()

print("-> BSM では sigma 一定を仮定するが、市場では Strike ごとに IV が異なる (Volatility Smile)")
"""

# ===========================================================================
# Volatility Smile 補足説明 Markdown  [新規挿入: cell[37] の直後]
# ===========================================================================
SMILE_EXPLANATION_MD = """\
> **Volatility Smile に関する補足**
>
> ここで使っているデータは **人工データ** です（ATM IV = 20%、U字型 smile を仮定）。
> 実際の市場では資産クラスによって形が大きく異なります。
>
> | 資産クラス | 典型的な形 | 主な背景 |
> |---|---|---|
> | **Equity Index**（日経、S&P など） | 左右非対称の **スキュー**（低 Strike 側の IV が高い） | クラッシュリスクへの需要；レバレッジ効果 |
> | **FX** | ほぼ対称な **Smile** | 双方向のテールリスク |
> | **Interest Rate Cap/Floor** | フラットまたは右上がり | 高金利方向の不確実性 |
>
> Equity index では一般に **「OTM put の IV が高い（左スキュー）」** が観測されます。
> 本 Notebook の U 字型 smile は説明のための简化モデルです。
>
> BSM の定数ボラティリティ仮定を超えた**ボラティリティ曲面モデル（SVI, SABR など）**は
> **Chapter 20** で詳しく扱います。
"""

# ===========================================================================
# q=0 match sanity check  [新規挿入: cell[41] の直後]
# ===========================================================================
SANITY_Q0 = """\
# --- [Sanity] 11-2. q=0 での一致確認  [updated: sanity check] ---
# q=0 の dividend-adjusted BSM が通常 BSM と一致することを確認
_call_no_q   = bsm_call_price(100.0, 100.0, 1.0, 0.05, 0.20)
_call_zero_q = bsm_call_with_dividend_yield(100.0, 100.0, 1.0, 0.05, 0.20, q=0.0)
_put_no_q    = bsm_put_price(100.0, 100.0, 1.0, 0.05, 0.20)
_put_zero_q  = bsm_put_with_dividend_yield(100.0, 100.0, 1.0, 0.05, 0.20, q=0.0)
print(f"Call q=0 vs 通常 BSM: diff = {abs(_call_no_q - _call_zero_q):.2e}")
print(f"Put  q=0 vs 通常 BSM: diff = {abs(_put_no_q  - _put_zero_q):.2e}")
assert abs(_call_no_q - _call_zero_q) < 1e-12
assert abs(_put_no_q  - _put_zero_q ) < 1e-12
print("-> OK: q=0 の dividend-adjusted BSM が通常 BSM と一致しています")
"""

# ===========================================================================
# MC 収束 sanity check  [新規挿入: cell[45] の直後]
# ===========================================================================
SANITY_MC = """\
# --- [Sanity] 12-2. MC 収束の確認  [updated: sanity check] ---
# 最大 N=500,000 での MC 価格が BSM と相対誤差 1% 以内に収まることを確認
_mc_large = mc_estimates[-1]
_rel_err  = abs(_mc_large - bsm_a) / bsm_a
print(f"BSM = {bsm_a:.6f},  MC (N=500k) = {_mc_large:.6f},  相対誤差 = {_rel_err:.4%}")
assert _rel_err < 0.01, f"MC 誤差が 1% を超えています: {_rel_err:.4%}"
print("-> OK: N=500,000 での MC 価格が BSM との相対誤差 1% 以内です")
"""

# ===========================================================================
# Exercise 2 解答セル  [updated: dict 形式に対応]
# ===========================================================================
NEW_CELL_51 = """\
# === 解答例 2 ===  [updated: dict 形式に対応]
S_q2, K_q2, T_q2, r_q2 = 110, 100, 0.25, 0.04
C_market_q2 = 14.50

res_bi_q2 = implied_vol_bisection(C_market_q2, S_q2, K_q2, T_q2, r_q2)
res_nw_q2 = implied_vol_newton(C_market_q2, S_q2, K_q2, T_q2, r_q2)
iv_bi_q2  = res_bi_q2["iv"]
iv_nw_q2  = res_nw_q2["iv"]

print(f"Bisection: IV = {iv_bi_q2:.6f}  ({res_bi_q2['iterations']} iters, converged={res_bi_q2['converged']})")
print(f"Newton:    IV = {iv_nw_q2:.6f}  ({res_nw_q2['iterations']} iters, converged={res_nw_q2['converged']})")
print(f"\\n-> Newton 法の方が圧倒的に少ない反復回数で収束する。")
print(f"-> Bisection: {res_bi_q2['message']}")
print(f"-> Newton:    {res_nw_q2['message']}")
"""

# ===========================================================================
# Exercise 4 解答セル — self-contained  [updated]
# ===========================================================================
NEW_CELL_55 = """\
# === 解答例 4 ===  [updated: self-contained]
# prices が未定義の場合 (Section 4 を飛ばして実行した場合) に再生成する
try:
    _ = prices
    _prices_src = "Section 4 の prices を再利用しています"
except NameError:
    _, _S_tmp = simulate_gbm_paths(100.0, 0.10, 0.25, 2.0, 504, 1, np.random.default_rng(42))
    prices = _S_tmp[0]
    _prices_src = "Note: prices を Exercise 4 内で再生成しました (sigma=0.25, T=2y, 504日)"

print(_prices_src)

log_ret_q4 = compute_log_returns(prices)
series_q4 = pd.Series(log_ret_q4)

fig, ax = plt.subplots(figsize=(10, 4))
for w in [10, 30, 60]:
    rv = series_q4.rolling(window=w).std() * np.sqrt(252)
    ax.plot(rv.values, label=f"window={w}", linewidth=0.8)
ax.axhline(0.25, color="black", linestyle="--", label="True sigma=0.25")
ax.set_title("ローリング・ボラティリティ: 窓長比較")
ax.set_xlabel("Day")
ax.set_ylabel("Annualized Vol")
ax.legend()
plt.tight_layout()
plt.show()

print("-> 窓長が短いほどノイジーだが局所変動を捉えやすい。")
print("   窓長が長いほど滑らかだが変化への反応が遅い。")
"""

# ===========================================================================
# メインの修正ロジック
# ===========================================================================

with open("bsm_chapter15.ipynb", encoding="utf-8") as f:
    nb = json.load(f)

cells = nb["cells"]
new_cells = []

for i, cell in enumerate(cells):
    src = "".join(cell["source"])

    # --- セル内容の修正 ---
    if i == 4 and "2-1. GBM" in src:
        # 共通関数セルを完全に置き換え
        cell = dict(cell)
        cell["source"] = to_lines(NEW_COMMON_FUNCTIONS)
        cell["outputs"] = []
        cell["execution_count"] = None

    elif i == 36 and "10-2. Bisection vs Newton" in src:
        # dict 形式に対応した bisection vs newton セル
        cell = dict(cell)
        cell["source"] = to_lines(NEW_CELL_36)
        cell["outputs"] = []
        cell["execution_count"] = None

    elif i == 37 and "10-3. Strike" in src:
        # dict 形式に対応した smile セル
        cell = dict(cell)
        cell["source"] = to_lines(NEW_CELL_37)
        cell["outputs"] = []
        cell["execution_count"] = None

    elif i == 51 and "解答例 2" in src:
        # Ex 2 — dict 形式に対応
        cell = dict(cell)
        cell["source"] = to_lines(NEW_CELL_51)
        cell["outputs"] = []
        cell["execution_count"] = None

    elif i == 55 and "解答例 4" in src:
        # Ex 4 — self-contained
        cell = dict(cell)
        cell["source"] = to_lines(NEW_CELL_55)
        cell["outputs"] = []
        cell["execution_count"] = None

    else:
        # その他のセル: outputs のみクリア（再実行前提）
        cell = dict(cell)
        if cell["cell_type"] == "code":
            cell["outputs"] = []
            cell["execution_count"] = None

    new_cells.append(cell)

    # --- セルの直後に新規セルを挿入 ---
    if i == 14 and "5-1. デルタヘッジの数値デモ" in src:
        new_cells.append(md_cell(DELTA_HEDGE_LIMITATIONS_MD))

    elif i == 22 and "7-1. サンプルパラメータで価格計算" in src:
        new_cells.append(code_cell(SANITY_PCP))

    elif i == 36 and "10-2. Bisection vs Newton" in src:
        new_cells.append(code_cell(SANITY_IV_ROUNDTRIP))

    elif i == 37 and "10-3. Strike" in src:
        new_cells.append(md_cell(SMILE_EXPLANATION_MD))

    elif i == 41 and "11-2." in src:
        new_cells.append(code_cell(SANITY_Q0))

    elif i == 45 and "12-2." in src:
        new_cells.append(code_cell(SANITY_MC))

nb["cells"] = new_cells

with open("bsm_chapter15.ipynb", "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Done. Original: {len(cells)} cells → Modified: {len(new_cells)} cells")
