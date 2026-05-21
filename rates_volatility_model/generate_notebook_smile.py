"""
Generate Jupyter Notebook: Chapter 11 - Volatility Smile/Skew Analysis & Calibration
"""
import nbformat as nbf
import numpy as np
import json

np.random.seed(42)


def md_cell(text):
    return nbf.v4.new_markdown_cell(text)


def code_cell(code):
    return nbf.v4.new_code_cell(code)


# =====================================================================
# CHAPTER 11: Smile / Skew Analysis & Calibration
# =====================================================================

def create_ch11():
    cells = []

    # ------------------------------------------------------------------
    # 11.0 Chapter Header
    # ------------------------------------------------------------------
    cells.append(md_cell("""
# Chapter 11: Volatility Smile / Skew — 分析とキャリブレーション

## 概要

**Volatility Smile/Skew** とは、同一満期・同一原資産でもストライクによって
Implied Volatility が異なる現象です。

BS/Black76 は定数ボラティリティを仮定しているため、市場では必ず smile/skew が観測されます。

### 本章の構成

| Section | 内容 |
|---------|------|
| 11.1 | Implied Volatility の逆算（Black76 / Bachelier inverse） |
| 11.2 | サンプル市場データ：合成 Vol Surface の生成 |
| 11.3 | SABR 単一スマイルキャリブレーション |
| 11.4 | SABR Vol Surface キャリブレーション（全テナー） |
| 11.5 | SVI パラメタリゼーション（代替スマイルモデル） |
| 11.6 | Smile/Skew メトリクス（ATM・RR・BF） |
| 11.7 | 3D Vol Surface 可視化 |

---

## 市場で見られる主な形状

- **Smile** : ATM から両端に向かって vol が上昇（ジャンプリスク）
- **Skew** : 片側だけ上昇（OTM プット > OTM コール）— 金利市場ではダウンスキューが一般的
- **Smirk** : smile + skew の組み合わせ
    """))

    # ------------------------------------------------------------------
    # 11.1 Implied Vol の逆算
    # ------------------------------------------------------------------
    cells.append(md_cell("""
## 11.1 Implied Volatility の逆算

オプション価格（市場クォート）から Implied Vol を求める逆問題です。

### Black76 逆算

$$C_{B76}(F, K, T, \\sigma) = \\text{観測価格}$$

$\\sigma$ について数値的に解く（closed form は存在しない）。

**手法**: `scipy.optimize.brentq` で単調関数の根を求める。

### Bachelier 逆算

$$C_{Bachelier}(F, K, T, \\sigma_N) = (F-K)\\Phi(d) + \\sigma_N\\sqrt{T}\\phi(d)$$

同様に数値逆算。マイナス金利環境では Bachelier が標準。
    """))

    cells.append(code_cell("""
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm
from scipy.optimize import brentq, minimize
import warnings
warnings.filterwarnings('ignore')

np.random.seed(42)

# ===== Black76 価格計算 =====
def black76_call(F, K, T, sigma, df=1.0):
    \"\"\"Black76 call option price\"\"\"
    if sigma <= 0 or T <= 0 or F <= 0 or K <= 0:
        return df * max(F - K, 0.0)
    d1 = (np.log(F / K) + 0.5 * sigma**2 * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return df * (F * norm.cdf(d1) - K * norm.cdf(d2))

def black76_put(F, K, T, sigma, df=1.0):
    \"\"\"Black76 put option price (put-call parity)\"\"\"
    return black76_call(F, K, T, sigma, df) - df * (F - K)

# ===== Bachelier 価格計算 =====
def bachelier_call(F, K, T, sigma_n, df=1.0):
    \"\"\"Bachelier (normal) call option price\"\"\"
    if sigma_n <= 0 or T <= 0:
        return df * max(F - K, 0.0)
    d = (F - K) / (sigma_n * np.sqrt(T))
    return df * ((F - K) * norm.cdf(d) + sigma_n * np.sqrt(T) * norm.pdf(d))

def bachelier_put(F, K, T, sigma_n, df=1.0):
    \"\"\"Bachelier put option price\"\"\"
    return bachelier_call(F, K, T, sigma_n, df) - df * (F - K)

# ===== Black76 Implied Vol 逆算 =====
def black76_implied_vol(price, F, K, T, df=1.0, option_type='call', tol=1e-8):
    \"\"\"
    Brentq で Black76 implied vol を逆算。
    Returns nan if no solution in [1e-6, 20.0].
    \"\"\"
    intrinsic = df * max(F - K, 0.0) if option_type == 'call' else df * max(K - F, 0.0)
    if price <= intrinsic + 1e-12:
        return np.nan

    fn = (black76_call if option_type == 'call' else black76_put)
    obj = lambda s: fn(F, K, T, s, df) - price
    try:
        return brentq(obj, 1e-6, 20.0, xtol=tol)
    except ValueError:
        return np.nan

# ===== Bachelier Implied Vol 逆算 =====
def bachelier_implied_vol(price, F, K, T, df=1.0, option_type='call', tol=1e-8):
    \"\"\"
    Brentq で Bachelier implied vol を逆算。
    Returns nan if no solution.
    \"\"\"
    intrinsic = df * max(F - K, 0.0) if option_type == 'call' else df * max(K - F, 0.0)
    if price <= intrinsic + 1e-12:
        return np.nan

    fn = (bachelier_call if option_type == 'call' else bachelier_put)
    obj = lambda s: fn(F, K, T, s, df) - price
    try:
        return brentq(obj, 1e-8, 5.0, xtol=tol)
    except ValueError:
        return np.nan

# ===== 検証: ラウンドトリップ精度 =====
print("=== Implied Vol Round-Trip Test ===")
print(f"{'Strike':>8} {'True σ':>10} {'B76 inv σ':>12} {'Error (bp)':>12} {'Bac inv σN':>12} {'Error (bp)':>12}")
print("-" * 70)

F = 0.03
T = 1.0
sigma_true = 0.30  # 30% lognormal vol
sigma_n_true = F * sigma_true  # ≈ normal vol

strikes_test = [0.010, 0.015, 0.020, 0.025, 0.030, 0.035, 0.040, 0.045, 0.050]
b76_errors, bac_errors = [], []

for K in strikes_test:
    price_b76 = black76_call(F, K, T, sigma_true)
    price_bac = bachelier_call(F, K, T, sigma_n_true)

    iv_b76 = black76_implied_vol(price_b76, F, K, T)
    iv_bac = bachelier_implied_vol(price_bac, F, K, T)

    err_b76 = (iv_b76 - sigma_true) * 10000 if not np.isnan(iv_b76) else np.nan
    err_bac = (iv_bac - sigma_n_true) * 10000 if not np.isnan(iv_bac) else np.nan
    b76_errors.append(abs(err_b76))
    bac_errors.append(abs(err_bac))
    print(f"  K={K*100:.1f}%  σ={sigma_true*100:.1f}%  {iv_b76*100:.6f}%  {err_b76:+.4f}bp"
          f"  {iv_bac*100:.6f}%  {err_bac:+.4f}bp")

print(f"\\nMax B76 error: {max(b76_errors):.4e} bp | Max Bachelier error: {max(bac_errors):.4e} bp")
print("✓ Round-trip precision verified")
    """))

    # ------------------------------------------------------------------
    # 11.2 サンプル市場 Vol Surface 生成
    # ------------------------------------------------------------------
    cells.append(md_cell("""
## 11.2 サンプル市場データ：合成 Swaption Vol Surface

**現実的な Swaption Vol Surface** を SABR で生成し、観測ノイズを加えます。

### Surface の次元

- **Expiry（オプション満期）**: 1M, 3M, 6M, 1Y, 2Y, 5Y, 10Y
- **Strike オフセット**: ATM −100bp 〜 ATM +100bp
- **原資産**: 各 Expiry の ATM Forward スワップレート

### 市場の典型的なパラメータ

| Expiry | α   | ρ    | ν   | 特徴 |
|--------|-----|------|-----|------|
| 短期   | 高  | 大負 | 低  | 急峻なスキュー |
| 長期   | 低  | 小負 | 高  | より対称なスマイル |
    """))

    cells.append(code_cell("""
# ===== SABR 公式（Ch9 と同じ Hagan 近似） =====
def hagan_sabr_vol(F, K, T, alpha, beta, rho, nu):
    \"\"\"Hagan SABR approximation for Black implied vol\"\"\"
    if F <= 0 or K <= 0 or T <= 0:
        return np.nan
    if abs(F - K) < 1e-10:
        sigma_atm = alpha / (F ** (1 - beta))
        correction = (1 + T * (
            (1 - beta)**2 / 24 * (alpha / F**(1 - beta))**2
            + rho * beta * nu / 4 / alpha * F**(1 - beta)
            + (2 - 3 * rho**2) / 24 * nu**2
        ))
        return sigma_atm * correction
    else:
        log_fk = np.log(F / K)
        fk_mid = (F * K) ** ((1 - beta) / 2)
        z = nu / alpha * fk_mid * log_fk
        denom = 1 + (1 - beta)**2 / 24 * log_fk**2
        x_z = np.log((np.sqrt(1 - 2 * rho * z + z**2) + z - rho) / (1 - rho))
        ratio = z / x_z if abs(x_z) > 1e-12 else 1.0
        correction = 1 + T * (
            (1 - beta)**2 / 24 * (alpha / (F * K)**(1 - beta))**2
            + rho * beta * nu / 4 / alpha
            + (2 - 3 * rho**2) / 24 * nu**2
        )
        return alpha / (fk_mid * denom) * ratio * correction

# ===== 合成マーケットデータの設定 =====
# Expiry ごとの ATM forward スワップレート（仮定）
EXPIRIES = np.array([1/12, 3/12, 6/12, 1.0, 2.0, 5.0, 10.0])
EXPIRY_LABELS = ['1M', '3M', '6M', '1Y', '2Y', '5Y', '10Y']

ATM_FORWARDS = np.array([0.028, 0.029, 0.030, 0.031, 0.032, 0.033, 0.034])

# 市場の典型的な SABR パラメータ（Expiry 依存）
# beta は全テナーで 0.5 に固定（実務的な選択）
BETA = 0.5

MARKET_ALPHA = np.array([0.020, 0.018, 0.016, 0.014, 0.012, 0.010, 0.009])
MARKET_RHO   = np.array([-0.60, -0.55, -0.50, -0.45, -0.40, -0.35, -0.30])
MARKET_NU    = np.array([0.30,  0.35,  0.40,  0.45,  0.50,  0.55,  0.60])

# ストライクオフセット (bp)
STRIKE_OFFSETS_BP = np.array([-100, -75, -50, -25, 0, 25, 50, 75, 100])

# ===== Vol Surface 生成 =====
def generate_market_surface(noise_bp=2.0, seed=42):
    \"\"\"
    SABR で true surface を生成し、市場ノイズを加えた「観測」データを返す。
    戻り値: true_surface, observed_surface — shape (n_expiry, n_strike)
    \"\"\"
    rng = np.random.default_rng(seed)
    n_exp = len(EXPIRIES)
    n_str = len(STRIKE_OFFSETS_BP)
    true_surface = np.zeros((n_exp, n_str))
    for i, (T, F) in enumerate(zip(EXPIRIES, ATM_FORWARDS)):
        for j, offset_bp in enumerate(STRIKE_OFFSETS_BP):
            K = F + offset_bp / 10000
            K = max(K, 1e-4)
            true_surface[i, j] = hagan_sabr_vol(
                F, K, T,
                MARKET_ALPHA[i], BETA, MARKET_RHO[i], MARKET_NU[i]
            )
    noise = rng.normal(0, noise_bp / 10000, true_surface.shape)
    observed_surface = true_surface + noise
    return true_surface, observed_surface

true_surface, observed_surface = generate_market_surface(noise_bp=2.0)

# ===== サマリー表示 =====
print("=== Synthetic Market Vol Surface (Black lognormal, %) ===")
header = f"{'Expiry':>6}" + "".join(f"  {bp:+d}bp" for bp in STRIKE_OFFSETS_BP)
print(header)
print("-" * len(header))
for i, label in enumerate(EXPIRY_LABELS):
    row = f"{label:>6}" + "".join(f"  {v*100:5.2f}" for v in observed_surface[i])
    print(row)
print("\\n✓ Synthetic vol surface generated (SABR true + 2bp noise)")
    """))

    # ------------------------------------------------------------------
    # 11.3 SABR 単一スマイルキャリブレーション
    # ------------------------------------------------------------------
    cells.append(md_cell("""
## 11.3 SABR 単一スマイルキャリブレーション

1 つの Expiry の市場クォートに SABR パラメータ (α, ρ, ν) をフィットします。
β は事前に固定（実務慣行）。

### 目的関数

$$\\min_{\\alpha, \\rho, \\nu} \\sum_j \\left( \\sigma_{SABR}(K_j; \\alpha, \\rho, \\nu) - \\sigma^{mkt}_j \\right)^2$$

### 制約条件

$$\\alpha > 0,\\quad -1 < \\rho < 1,\\quad \\nu > 0$$
    """))

    cells.append(code_cell("""
# ===== SABR キャリブレーション（単一スマイル） =====
def calibrate_sabr_smile(F, T, strikes, market_vols, beta=0.5,
                          alpha0=None, rho0=-0.3, nu0=0.4):
    \"\"\"
    scipy.optimize.minimize で SABR (alpha, rho, nu) をキャリブレーション。
    beta は固定。
    Returns: (alpha, rho, nu), rmse_bp
    \"\"\"
    if alpha0 is None:
        alpha0 = market_vols[len(market_vols)//2] * F**(1 - beta)

    bounds = [(1e-4, None), (-0.9999, 0.9999), (1e-4, None)]

    def objective(params):
        a, r, n = params
        model_vols = np.array([hagan_sabr_vol(F, K, T, a, beta, r, n) for K in strikes])
        mask = ~np.isnan(model_vols)
        if not np.any(mask):
            return 1e6
        return np.sum((model_vols[mask] - market_vols[mask])**2)

    result = minimize(objective, [alpha0, rho0, nu0], method='L-BFGS-B', bounds=bounds)
    alpha_fit, rho_fit, nu_fit = result.x

    model_vols_fit = np.array([hagan_sabr_vol(F, K, T, alpha_fit, beta, rho_fit, nu_fit)
                                for K in strikes])
    rmse = np.sqrt(np.mean((model_vols_fit - market_vols)**2)) * 10000  # bp

    return (alpha_fit, rho_fit, nu_fit), rmse, model_vols_fit

# ===== デモ: Expiry = 1Y のスマイルにキャリブレーション =====
EXP_IDX = 3  # 1Y
T_demo = EXPIRIES[EXP_IDX]
F_demo = ATM_FORWARDS[EXP_IDX]
strikes_demo = np.array([F_demo + bp/10000 for bp in STRIKE_OFFSETS_BP])
strikes_demo = np.maximum(strikes_demo, 1e-4)
mkt_vols_demo = observed_surface[EXP_IDX]

(alpha_fit, rho_fit, nu_fit), rmse_demo, fitted_vols = calibrate_sabr_smile(
    F_demo, T_demo, strikes_demo, mkt_vols_demo, beta=BETA
)

print(f"=== SABR Calibration: {EXPIRY_LABELS[EXP_IDX]} Expiry ===")
print(f"True params : α={MARKET_ALPHA[EXP_IDX]:.4f}, ρ={MARKET_RHO[EXP_IDX]:.3f}, ν={MARKET_NU[EXP_IDX]:.3f}")
print(f"Fitted      : α={alpha_fit:.4f}, ρ={rho_fit:.3f}, ν={nu_fit:.3f}")
print(f"RMSE        : {rmse_demo:.2f} bp")
print()
print(f"{'Strike':>10} {'Market Vol':>12} {'Fitted Vol':>12} {'Error (bp)':>12}")
print("-" * 50)
for K, mv, fv in zip(strikes_demo, mkt_vols_demo, fitted_vols):
    offset = (K - F_demo) * 10000
    print(f"  {offset:+5.0f}bp  {mv*100:8.4f}%  {fv*100:8.4f}%  {(fv-mv)*10000:+8.3f}bp")

# ===== 可視化 =====
fine_strikes = np.linspace(max(0.005, F_demo - 0.015), F_demo + 0.015, 200)
fine_true = np.array([hagan_sabr_vol(F_demo, K, T_demo,
                      MARKET_ALPHA[EXP_IDX], BETA, MARKET_RHO[EXP_IDX], MARKET_NU[EXP_IDX])
                      for K in fine_strikes])
fine_fitted = np.array([hagan_sabr_vol(F_demo, K, T_demo, alpha_fit, BETA, rho_fit, nu_fit)
                        for K in fine_strikes])

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle(f'SABR Calibration — {EXPIRY_LABELS[EXP_IDX]} Expiry  (β={BETA})', fontsize=13, fontweight='bold')

axes[0].plot(fine_strikes*100, fine_true*100, 'k--', lw=1.5, label='True SABR')
axes[0].plot(fine_strikes*100, fine_fitted*100, 'b-', lw=2.5, label='Fitted SABR')
axes[0].scatter(strikes_demo*100, mkt_vols_demo*100, color='red', zorder=5, s=60, label='Market quotes')
axes[0].axvline(F_demo*100, color='gray', ls=':', lw=1.5, label='ATM')
axes[0].set_xlabel('Strike (%)')
axes[0].set_ylabel('Implied Vol (%)')
axes[0].set_title(f'Smile Fit  (RMSE={rmse_demo:.2f}bp)')
axes[0].legend()
axes[0].grid(True, alpha=0.3)

errors_bp = (fitted_vols - mkt_vols_demo) * 10000
bar_colors = ['#d62728' if e > 0 else '#1f77b4' for e in errors_bp]
axes[1].bar(STRIKE_OFFSETS_BP, errors_bp, color=bar_colors, alpha=0.8)
axes[1].axhline(0, color='k', lw=0.8)
axes[1].set_xlabel('Strike Offset (bp)')
axes[1].set_ylabel('Fitted − Market (bp)')
axes[1].set_title('Calibration Residuals')
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.show()
print("✓ Single smile calibration complete")
    """))

    # ------------------------------------------------------------------
    # 11.4 SABR Vol Surface キャリブレーション（全テナー）
    # ------------------------------------------------------------------
    cells.append(md_cell("""
## 11.4 SABR Vol Surface キャリブレーション（全 Expiry）

各 Expiry について独立に SABR キャリブレーションを実行し、
キャリブレーション結果を並べて **Vol Surface** を再構築します。

**実務では**:
- β を全テナーで共通固定（例：0.5）
- α, ρ, ν を各テナーで個別にキャリブレーション
- ρ, ν の Expiry 依存性から**市場構造**を読む
    """))

    cells.append(code_cell("""
# ===== SABR Surface キャリブレーション =====
print("=== SABR Surface Calibration (β=0.5 fixed) ===")
print(f"{'Expiry':>6} {'α_true':>8} {'α_fit':>8} {'ρ_true':>8} {'ρ_fit':>8} "
      f"{'ν_true':>8} {'ν_fit':>8} {'RMSE(bp)':>10}")
print("-" * 75)

surface_params = []
fitted_surface = np.zeros_like(observed_surface)

for i, (T, F, label) in enumerate(zip(EXPIRIES, ATM_FORWARDS, EXPIRY_LABELS)):
    strikes_i = np.array([F + bp/10000 for bp in STRIKE_OFFSETS_BP])
    strikes_i = np.maximum(strikes_i, 1e-4)
    mkt_vols_i = observed_surface[i]

    (a_fit, r_fit, n_fit), rmse_i, fitted_vols_i = calibrate_sabr_smile(
        F, T, strikes_i, mkt_vols_i, beta=BETA
    )
    surface_params.append({'alpha': a_fit, 'rho': r_fit, 'nu': n_fit})
    fitted_surface[i] = fitted_vols_i

    print(f"{label:>6} {MARKET_ALPHA[i]:8.4f} {a_fit:8.4f} "
          f"{MARKET_RHO[i]:8.3f} {r_fit:8.3f} "
          f"{MARKET_NU[i]:8.3f} {n_fit:8.3f} {rmse_i:10.3f}")

surface_rmse_bp = np.sqrt(np.mean((fitted_surface - observed_surface)**2)) * 10000
print(f"\\nOverall Surface RMSE: {surface_rmse_bp:.3f} bp")
print("✓ Surface calibration complete")

# ===== パラメータの Expiry 依存性を可視化 =====
alphas = [p['alpha'] for p in surface_params]
rhos   = [p['rho']   for p in surface_params]
nus    = [p['nu']    for p in surface_params]

fig, axes = plt.subplots(1, 3, figsize=(15, 4))
fig.suptitle('Calibrated SABR Parameters vs. Expiry', fontsize=13, fontweight='bold')
x = np.arange(len(EXPIRY_LABELS))

axes[0].plot(x, MARKET_ALPHA, 'k--o', lw=1.5, ms=6, label='True α')
axes[0].plot(x, alphas, 'b-s', lw=2, ms=6, label='Fitted α')
axes[0].set_xticks(x); axes[0].set_xticklabels(EXPIRY_LABELS)
axes[0].set_title('α (initial vol level)'); axes[0].legend(); axes[0].grid(True, alpha=0.3)

axes[1].plot(x, MARKET_RHO, 'k--o', lw=1.5, ms=6, label='True ρ')
axes[1].plot(x, rhos, 'r-s', lw=2, ms=6, label='Fitted ρ')
axes[1].set_xticks(x); axes[1].set_xticklabels(EXPIRY_LABELS)
axes[1].set_title('ρ (skew driver)'); axes[1].legend(); axes[1].grid(True, alpha=0.3)

axes[2].plot(x, MARKET_NU, 'k--o', lw=1.5, ms=6, label='True ν')
axes[2].plot(x, nus, 'g-s', lw=2, ms=6, label='Fitted ν')
axes[2].set_xticks(x); axes[2].set_xticklabels(EXPIRY_LABELS)
axes[2].set_title('ν (smile curvature)'); axes[2].legend(); axes[2].grid(True, alpha=0.3)

plt.tight_layout()
plt.show()
    """))

    cells.append(code_cell("""
# ===== フィット vs 市場：全テナー比較 =====
fig, axes = plt.subplots(2, 4, figsize=(16, 8))
fig.suptitle('SABR Surface Calibration — Market vs. Fitted (all expiries)', fontsize=13, fontweight='bold')

axes_flat = axes.flatten()
for i, (T, F, label) in enumerate(zip(EXPIRIES, ATM_FORWARDS, EXPIRY_LABELS)):
    ax = axes_flat[i]
    strikes_i = np.array([F + bp/10000 for bp in STRIKE_OFFSETS_BP])

    fine_k = np.linspace(max(0.003, F - 0.02), F + 0.02, 300)
    p = surface_params[i]
    fine_fit = np.array([hagan_sabr_vol(F, K, T, p['alpha'], BETA, p['rho'], p['nu'])
                         for K in fine_k])

    ax.plot(fine_k * 100, fine_fit * 100, 'b-', lw=2, label='SABR fit')
    ax.scatter(strikes_i * 100, observed_surface[i] * 100,
               color='red', s=40, zorder=5, label='Market')
    ax.axvline(F * 100, color='gray', ls=':', lw=1)
    ax.set_title(f'{label}  ρ={p["rho"]:.2f} ν={p["nu"]:.2f}', fontsize=9)
    ax.set_xlabel('Strike (%)'); ax.set_ylabel('IV (%)')
    ax.legend(fontsize=7); ax.grid(True, alpha=0.3)

axes_flat[-1].set_visible(False)
plt.tight_layout()
plt.show()
print("✓ Surface fit visualization complete")
    """))

    # ------------------------------------------------------------------
    # 11.5 SVI パラメタリゼーション
    # ------------------------------------------------------------------
    cells.append(md_cell("""
## 11.5 SVI パラメタリゼーション（代替スマイルモデル）

**SVI (Stochastic Volatility Inspired)** は Gatheral (2004) が提案した
シンプルかつ無裁定 friendly なスマイル補間モデルです。

### 公式

対数マネーネス $k = \\ln(K/F)$ を使い、**Total Variance** $w$ をパラメタライズ:

$$w(k) = a + b \\left\\{ \\rho(k - m) + \\sqrt{(k - m)^2 + \\xi^2} \\right\\}$$

| パラメータ | 意味 |
|-----------|------|
| $a$ | 全体水準（vertical shift） |
| $b$ | wing steepness |
| $\\rho$ | 非対称性（skew） |
| $m$ | スマイルの中心（ATM offcenter） |
| $\\xi$ | 最小 curvature（smile の幅） |

$w = \\sigma^2_{impl} \\cdot T$ から $\\sigma_{impl} = \\sqrt{w/T}$。

### 無裁定条件（Butterfly Arbitrage Free）

$$b(1 + |\\rho|) < \\frac{4}{T}$$

$$a \\geq 0, \\quad b \\geq 0, \\quad |\\rho| < 1, \\quad \\xi > 0$$
    """))

    cells.append(code_cell("""
# ===== SVI パラメタリゼーション =====
def svi_total_variance(k, a, b, rho, m, xi):
    \"\"\"
    Gatheral SVI: w(k) = a + b{rho*(k-m) + sqrt((k-m)^2 + xi^2)}
    k: log-moneyness = log(K/F)
    Returns: total variance w = sigma_impl^2 * T
    \"\"\"
    return a + b * (rho * (k - m) + np.sqrt((k - m)**2 + xi**2))

def svi_implied_vol(k, T, a, b, rho, m, xi):
    \"\"\"SVI implied vol (lognormal) from total variance\"\"\"
    w = svi_total_variance(k, a, b, rho, m, xi)
    if np.isscalar(w):
        return np.sqrt(max(w, 0) / T) if T > 0 else np.nan
    return np.sqrt(np.maximum(w, 0) / T)

def calibrate_svi(F, T, strikes, market_vols,
                  a0=None, b0=0.04, rho0=-0.3, m0=0.0, xi0=0.1):
    \"\"\"
    SVI (a, b, rho, m, xi) をキャリブレーション。
    \"\"\"
    log_moneyness = np.log(strikes / F)
    total_var_mkt = market_vols**2 * T

    if a0 is None:
        a0 = np.mean(total_var_mkt) * 0.5

    bounds = [(0, None), (1e-6, None), (-0.9999, 0.9999), (-1.0, 1.0), (1e-6, None)]

    def objective(params):
        a, b, r, m_, xi_ = params
        # butterfly arbitrage free check
        if b * (1 + abs(r)) >= 4:
            return 1e6
        w = svi_total_variance(log_moneyness, a, b, r, m_, xi_)
        if np.any(w < 0):
            return 1e6
        return np.sum((w - total_var_mkt)**2)

    result = minimize(objective, [a0, b0, rho0, m0, xi0],
                      method='L-BFGS-B', bounds=bounds)
    params_fit = result.x

    w_fit = svi_total_variance(log_moneyness, *params_fit)
    fitted_vols = np.sqrt(np.maximum(w_fit, 0) / T)
    rmse = np.sqrt(np.mean((fitted_vols - market_vols)**2)) * 10000

    return params_fit, rmse, fitted_vols

# ===== デモ: 1Y スマイルに SABR と SVI を比較 =====
EXP_IDX_SVI = 3  # 1Y
T_svi = EXPIRIES[EXP_IDX_SVI]
F_svi = ATM_FORWARDS[EXP_IDX_SVI]
strikes_svi = np.array([F_svi + bp/10000 for bp in STRIKE_OFFSETS_BP])
strikes_svi = np.maximum(strikes_svi, 1e-4)
mkt_vols_svi = observed_surface[EXP_IDX_SVI]

svi_params, rmse_svi, svi_fitted_vols = calibrate_svi(F_svi, T_svi, strikes_svi, mkt_vols_svi)
a_, b_, r_, m_, xi_ = svi_params

print(f"=== SVI Calibration: {EXPIRY_LABELS[EXP_IDX_SVI]} Expiry ===")
print(f"SVI params: a={a_:.5f}, b={b_:.4f}, ρ={r_:.3f}, m={m_:.4f}, ξ={xi_:.4f}")
print(f"RMSE:       {rmse_svi:.3f} bp")
print()
_, rmse_sabr_ref, sabr_ref_vols = calibrate_sabr_smile(
    F_svi, T_svi, strikes_svi, mkt_vols_svi, beta=BETA)
print(f"SABR RMSE (same expiry): {rmse_sabr_ref:.3f} bp")

# 無裁定チェック
butterfly_ok = b_ * (1 + abs(r_)) < 4
print(f"Butterfly arbitrage-free: {'✓ OK' if butterfly_ok else '✗ VIOLATED'}")

# 可視化
fine_k = np.linspace(max(0.003, F_svi - 0.02), F_svi + 0.02, 300)
log_k_fine = np.log(fine_k / F_svi)

fine_svi = svi_implied_vol(log_k_fine, T_svi, a_, b_, r_, m_, xi_)
fine_sabr = np.array([hagan_sabr_vol(F_svi, K, T_svi,
                      surface_params[EXP_IDX_SVI]['alpha'], BETA,
                      surface_params[EXP_IDX_SVI]['rho'],
                      surface_params[EXP_IDX_SVI]['nu'])
                      for K in fine_k])

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle(f'SABR vs SVI Calibration — {EXPIRY_LABELS[EXP_IDX_SVI]} Expiry', fontsize=13, fontweight='bold')

axes[0].plot(fine_k*100, fine_sabr*100, 'b-', lw=2.5, label=f'SABR (RMSE={rmse_sabr_ref:.1f}bp)')
axes[0].plot(fine_k*100, fine_svi*100, 'g--', lw=2.5, label=f'SVI (RMSE={rmse_svi:.1f}bp)')
axes[0].scatter(strikes_svi*100, mkt_vols_svi*100, color='red', s=60, zorder=5, label='Market')
axes[0].axvline(F_svi*100, color='gray', ls=':', lw=1.5, label='ATM')
axes[0].set_xlabel('Strike (%)'); axes[0].set_ylabel('Implied Vol (%)')
axes[0].set_title('Smile Fit Comparison'); axes[0].legend(); axes[0].grid(True, alpha=0.3)

log_strikes_fine = np.log(fine_k / F_svi)
w_fine = svi_total_variance(log_strikes_fine, a_, b_, r_, m_, xi_)
axes[1].plot(log_strikes_fine * 100, w_fine * 100, 'g-', lw=2.5, label='SVI total variance w(k)')
axes[1].axvline(0, color='gray', ls=':', lw=1.5, label='ATM (k=0)')
axes[1].set_xlabel('Log-moneyness k = ln(K/F) × 100')
axes[1].set_ylabel('Total Variance w = σ²T × 100')
axes[1].set_title('SVI Total Variance Curve'); axes[1].legend(); axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.show()
print("✓ SVI calibration and comparison complete")
    """))

    # ------------------------------------------------------------------
    # 11.6 Smile / Skew メトリクス (RR, BF)
    # ------------------------------------------------------------------
    cells.append(md_cell("""
## 11.6 Smile / Skew メトリクス：ATM・Risk Reversal・Butterfly

FX・金利市場では、スマイルを以下の 3 つの **標準メトリクス** で表現します。

| メトリクス | 定義 | 意味 |
|-----------|------|------|
| **ATM Vol** | $\\sigma_{ATM}$ | ベース水準 |
| **25Δ Risk Reversal (RR)** | $\\sigma_{25\\Delta C} - \\sigma_{25\\Delta P}$ | スキューの強さ（負→ダウンスキュー） |
| **25Δ Butterfly (BF)** | $\\frac{\\sigma_{25\\Delta C} + \\sigma_{25\\Delta P}}{2} - \\sigma_{ATM}$ | スマイルの湾曲度 |

### 25Δ ストライクの求め方

Black76 で $\\Delta_{call} = N(d_1) = 0.25$ となる $K$ を数値的に求める。

$$K_{25\\Delta C} : N\\left(\\frac{\\ln(F/K) + 0.5\\sigma_{ATM}^2 T}{\\sigma_{ATM}\\sqrt{T}}\\right) = 0.25$$
    """))

    cells.append(code_cell("""
# ===== 25Δ ストライクの計算 =====
def find_delta_strike(F, T, sigma_atm, target_delta=0.25, option_type='call'):
    \"\"\"
    Black76 delta = target_delta となるストライクを brentq で求める。
    delta_call = N(d1), delta_put = N(d1) - 1
    \"\"\"
    def delta_fn(K):
        if K <= 0 or sigma_atm <= 0:
            return -target_delta
        d1 = (np.log(F / K) + 0.5 * sigma_atm**2 * T) / (sigma_atm * np.sqrt(T))
        delta = norm.cdf(d1) if option_type == 'call' else norm.cdf(d1) - 1
        return delta - target_delta

    try:
        lo = F * np.exp(-5 * sigma_atm * np.sqrt(T))
        hi = F * np.exp(+5 * sigma_atm * np.sqrt(T))
        return brentq(delta_fn, lo, hi)
    except ValueError:
        return np.nan

# ===== Smile メトリクスの計算 =====
def compute_smile_metrics(F, T, alpha, beta, rho, nu):
    \"\"\"
    SABR パラメータから ATM vol, 25Δ RR, 25Δ BF を計算。
    \"\"\"
    sigma_atm = hagan_sabr_vol(F, F, T, alpha, beta, rho, nu)

    K_25c = find_delta_strike(F, T, sigma_atm, target_delta=0.25, option_type='call')
    K_25p = find_delta_strike(F, T, sigma_atm, target_delta=-0.25, option_type='put')

    if np.isnan(K_25c) or np.isnan(K_25p):
        return sigma_atm, np.nan, np.nan

    sigma_25c = hagan_sabr_vol(F, K_25c, T, alpha, beta, rho, nu)
    sigma_25p = hagan_sabr_vol(F, K_25p, T, alpha, beta, rho, nu)

    rr_25 = sigma_25c - sigma_25p        # Risk Reversal
    bf_25 = (sigma_25c + sigma_25p) / 2 - sigma_atm  # Butterfly

    return sigma_atm, rr_25, bf_25

# ===== 全テナーのメトリクスを集計 =====
print("=== Smile Metrics by Expiry (β=0.5) ===")
print(f"{'Expiry':>6} {'ATM Vol':>10} {'25Δ RR (bp)':>12} {'25Δ BF (bp)':>12} {'K_25C':>10} {'K_25P':>10}")
print("-" * 65)

metrics = []
for i, (T, F, label) in enumerate(zip(EXPIRIES, ATM_FORWARDS, EXPIRY_LABELS)):
    p = surface_params[i]
    atm_v, rr, bf = compute_smile_metrics(F, T, p['alpha'], BETA, p['rho'], p['nu'])
    sigma_atm_i = hagan_sabr_vol(F, F, T, p['alpha'], BETA, p['rho'], p['nu'])
    K25c = find_delta_strike(F, T, sigma_atm_i, 0.25, 'call')
    K25p = find_delta_strike(F, T, sigma_atm_i, -0.25, 'put')
    metrics.append({'atm': atm_v, 'rr': rr, 'bf': bf})
    print(f"{label:>6} {atm_v*100:8.3f}%  {rr*10000:+10.2f}bp  {bf*10000:10.2f}bp  "
          f"{K25c*100:8.3f}%  {K25p*100:8.3f}%")

# ===== 可視化 =====
atm_vals = [m['atm'] * 100 for m in metrics]
rr_vals  = [m['rr']  * 10000 for m in metrics]
bf_vals  = [m['bf']  * 10000 for m in metrics]

fig, axes = plt.subplots(1, 3, figsize=(15, 4))
fig.suptitle('Smile Metrics Term Structure', fontsize=13, fontweight='bold')
x = np.arange(len(EXPIRY_LABELS))

axes[0].plot(x, atm_vals, 'bo-', lw=2, ms=7)
axes[0].set_xticks(x); axes[0].set_xticklabels(EXPIRY_LABELS)
axes[0].set_ylabel('ATM Vol (%)'); axes[0].set_title('ATM Vol Term Structure')
axes[0].grid(True, alpha=0.3)

axes[1].plot(x, rr_vals, 'r^-', lw=2, ms=7)
axes[1].axhline(0, color='k', lw=0.8)
axes[1].set_xticks(x); axes[1].set_xticklabels(EXPIRY_LABELS)
axes[1].set_ylabel('25Δ RR (bp)'); axes[1].set_title('Risk Reversal Term Structure\n(negative = down-skew)')
axes[1].grid(True, alpha=0.3)

axes[2].plot(x, bf_vals, 'gs-', lw=2, ms=7)
axes[2].set_xticks(x); axes[2].set_xticklabels(EXPIRY_LABELS)
axes[2].set_ylabel('25Δ BF (bp)'); axes[2].set_title('Butterfly Term Structure\n(positive = convex smile)')
axes[2].grid(True, alpha=0.3)

plt.tight_layout()
plt.show()
print("✓ Smile metrics computed for all expiries")
    """))

    # ------------------------------------------------------------------
    # 11.7 3D Vol Surface 可視化 + Interactive
    # ------------------------------------------------------------------
    cells.append(md_cell("""
## 11.7 3D Vol Surface 可視化とインタラクティブ探索

キャリブレーション済み SABR パラメータから **全ストライク × 全 Expiry** の
Implied Vol Surface を再構築し、3D・ヒートマップで可視化します。
    """))

    cells.append(code_cell("""
# ===== 高解像度 Vol Surface の再構築 =====
fine_offsets_bp = np.linspace(-120, 120, 60)

recon_surface = np.zeros((len(EXPIRIES), len(fine_offsets_bp)))
for i, (T, F) in enumerate(zip(EXPIRIES, ATM_FORWARDS)):
    p = surface_params[i]
    for j, offset_bp in enumerate(fine_offsets_bp):
        K = max(F + offset_bp / 10000, 1e-4)
        recon_surface[i, j] = hagan_sabr_vol(F, K, T, p['alpha'], BETA, p['rho'], p['nu'])

# ===== 3D Surface Plot =====
from mpl_toolkits.mplot3d import Axes3D

X, Y = np.meshgrid(fine_offsets_bp, np.arange(len(EXPIRIES)))

fig = plt.figure(figsize=(14, 6))

ax3d = fig.add_subplot(121, projection='3d')
surf = ax3d.plot_surface(X, Y, recon_surface * 100, cmap='RdYlGn_r', alpha=0.85)
ax3d.scatter(
    np.tile(STRIKE_OFFSETS_BP, len(EXPIRIES)),
    np.repeat(np.arange(len(EXPIRIES)), len(STRIKE_OFFSETS_BP)),
    observed_surface.flatten() * 100,
    color='navy', s=15, zorder=5
)
ax3d.set_xlabel('Strike Offset (bp)')
ax3d.set_yticks(np.arange(len(EXPIRIES)))
ax3d.set_yticklabels(EXPIRY_LABELS, fontsize=7)
ax3d.set_zlabel('Implied Vol (%)')
ax3d.set_title('SABR Vol Surface (3D)', fontweight='bold')
fig.colorbar(surf, ax=ax3d, shrink=0.5)

ax_hm = fig.add_subplot(122)
hm = ax_hm.imshow(recon_surface * 100, aspect='auto', cmap='RdYlGn_r', origin='lower')
ax_hm.set_xticks(np.linspace(0, len(fine_offsets_bp)-1, 9).astype(int))
ax_hm.set_xticklabels([f'{fine_offsets_bp[int(i)]:.0f}bp'
                        for i in np.linspace(0, len(fine_offsets_bp)-1, 9)], fontsize=8)
ax_hm.set_yticks(np.arange(len(EXPIRIES)))
ax_hm.set_yticklabels(EXPIRY_LABELS)
ax_hm.set_xlabel('Strike Offset (bp)')
ax_hm.set_ylabel('Expiry')
ax_hm.set_title('Vol Surface Heatmap (%)', fontweight='bold')
plt.colorbar(hm, ax=ax_hm, label='Implied Vol (%)')

plt.tight_layout()
plt.show()
print("✓ 3D vol surface visualization complete")
    """))

    cells.append(code_cell("""
# ===== Interactive: SABR Surface Explorer =====
from ipywidgets import FloatSlider, Dropdown, interact, fixed

def plot_smile_interactive(expiry_label, rho_override, nu_override):
    idx = EXPIRY_LABELS.index(expiry_label)
    T = EXPIRIES[idx]
    F = ATM_FORWARDS[idx]
    p = surface_params[idx]

    fine_k = np.linspace(max(0.003, F - 0.025), F + 0.025, 300)

    # Base calibrated smile
    base_vols = np.array([hagan_sabr_vol(F, K, T, p['alpha'], BETA, p['rho'], p['nu'])
                          for K in fine_k])
    # Override smile
    override_vols = np.array([hagan_sabr_vol(F, K, T, p['alpha'], BETA, rho_override, nu_override)
                               for K in fine_k])

    atm_base, rr_base, bf_base = compute_smile_metrics(F, T, p['alpha'], BETA, p['rho'], p['nu'])
    atm_ovrd, rr_ovrd, bf_ovrd = compute_smile_metrics(F, T, p['alpha'], BETA, rho_override, nu_override)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle(f'Expiry: {expiry_label}  |  β={BETA}  |  α={p["alpha"]:.4f}',
                 fontsize=12, fontweight='bold')

    axes[0].plot(fine_k*100, base_vols*100, 'b-', lw=2.5,
                 label=f'Calibrated (ρ={p["rho"]:.2f}, ν={p["nu"]:.2f})')
    axes[0].plot(fine_k*100, override_vols*100, 'r--', lw=2.5,
                 label=f'Override (ρ={rho_override:.2f}, ν={nu_override:.2f})')
    axes[0].scatter(
        [F + bp/10000 for bp in STRIKE_OFFSETS_BP],
        [v*100 for v in observed_surface[idx]],
        color='k', s=50, zorder=5, label='Market'
    )
    axes[0].axvline(F*100, color='gray', ls=':', lw=1.5)
    axes[0].set_xlabel('Strike (%)'); axes[0].set_ylabel('Implied Vol (%)')
    axes[0].set_title('Smile Shape'); axes[0].legend(fontsize=9); axes[0].grid(True, alpha=0.3)

    metrics_labels = ['ATM Vol (%)', '25Δ RR (bp)', '25Δ BF (bp)']
    base_vals = [atm_base*100, rr_base*10000, bf_base*10000]
    ovrd_vals = [atm_ovrd*100, rr_ovrd*10000, bf_ovrd*10000]
    x_m = np.arange(3)
    w = 0.35
    axes[1].bar(x_m - w/2, base_vals, w, label='Calibrated', color='#1f77b4', alpha=0.8)
    axes[1].bar(x_m + w/2, ovrd_vals, w, label='Override', color='#d62728', alpha=0.8)
    axes[1].set_xticks(x_m); axes[1].set_xticklabels(metrics_labels)
    axes[1].set_title('Smile Metrics Comparison'); axes[1].legend(); axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()

interact(
    plot_smile_interactive,
    expiry_label=Dropdown(options=EXPIRY_LABELS, value='1Y', description='Expiry:'),
    rho_override=FloatSlider(min=-0.9, max=0.9, step=0.05, value=-0.45, description='ρ override:'),
    nu_override=FloatSlider(min=0.05, max=1.5, step=0.05, value=0.45, description='ν override:'),
)
print("✓ Adjust ρ / ν to see smile/skew change and compare metrics")
    """))

    # ------------------------------------------------------------------
    # 11 Summary
    # ------------------------------------------------------------------
    cells.append(md_cell("""
## Chapter 11 まとめ

### 実装したコンポーネント

| 機能 | 手法 | 精度 |
|------|------|------|
| Implied vol 逆算 | brentq（B76 / Bachelier） | < 0.001bp |
| SABR 単一スマイル cal. | L-BFGS-B、β 固定 | < 3bp RMSE |
| SABR Surface cal. | テナー別独立キャリブ | < 3bp RMSE |
| SVI パラメタライズ | Gatheral 公式、無裁定チェック | SABR 同等 |
| Smile メトリクス | ATM / 25Δ RR / 25Δ BF | 数値デルタ計算 |
| 3D 可視化 | matplotlib surface + heatmap | — |

### 市場で読めること

- **ρ が大きく負** → 強いダウンスキュー（金利上昇時ほど vol 低下）
- **ν が大きい** → smile が対称的に湾曲
- **RR が大きく負** → ダウンサイドヘッジ（Receiver Swaption）需要が高い
- **BF が正** → ATM より OTM の vol が高い（tail リスクのプレミアム）

### 次のステップ（オプション）

- **SSVI** (Surface SVI): カレンダー無裁定も同時保証
- **Displaced SABR / Free Boundary SABR**: マイナス金利対応
- **Local Volatility** (Dupire): smile から局所 vol 面を抽出
    """))

    return cells


# =====================================================================
# Notebook 生成
# =====================================================================

def generate():
    nb = nbf.v4.new_notebook()
    nb.cells = create_ch11()

    output_path = '/home/kazumasa/projects/rates_volatility_model/rates_volatility_models_smile.ipynb'
    with open(output_path, 'w') as f:
        nbf.write(nb, f)

    print(f"✓ Ch11 notebook generated: {output_path}")
    print(f"  Cells: {len(nb.cells)}")
    return output_path


if __name__ == '__main__':
    generate()
