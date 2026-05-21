"""
Generate Jupyter Notebook: Interest Rate Volatility Models (Part 3: Ch7-Final)
"""
import nbformat as nbf
import numpy as np
from scipy.stats import norm
import json

np.random.seed(42)

def md_cell(text):
    return nbf.v4.new_markdown_cell(text)

def code_cell(code):
    return nbf.v4.new_code_cell(code)

# =====================================================================
# CHAPTER 7: HJM Framework
# =====================================================================

def create_ch7():
    cells = []
    
    cells.append(md_cell("""
# Chapter 7: HJM Framework (Heath-Jarrow-Morton)

## 概要

**HJM Framework** は、金利モデルを統一的に理解するための枠組みです。

これまでのモデル（Vasicek等）は **short rate** に着目していましたが、  
HJM は **forward curve 全体** をモデル化します。

## 基本式

Forward curve の動学：

$$df(t,T) = \\alpha(t,T)dt + \\sigma(t,T)dW_t$$

**無裁定条件**：

$$\\alpha(t,T) = \\sigma(t,T) \\int_t^T \\sigma(t,u)du$$

この条件によって、**volatility structure が決まれば drift が自動決定** されます。

### 重要ポイント
- ✅ 多くのモデルは HJM framework の special case
- ✅ Volatility structure = Model の本質
- ✅ 無裁定 ⟹ Drift と vol の関係が固定
    """))
    
    cells.append(code_cell("""
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d

def hjm_forward_curve_evolution(T_array, t_array, vol_func, initial_forward_curve):
    \"\"\"
    1-factor HJM simulation
    
    f(t,T) : forward rate at time t for maturity T
    
    Arbitrage-free condition:
    α(t,T) = σ(t,T) * ∫_t^T σ(t,u) du  (CORRECTED: integral from t to T, not T to infinity)
    
    df(t,T) = α(t,T) dt + σ(t,T) dW_t
    \"\"\"
    n_T = len(T_array)
    n_t = len(t_array)
    n_paths = 500
    dt = np.mean(np.diff(t_array))
    
    # 初期化
    forward_curves = np.zeros((n_paths, n_t, n_T))
    forward_curves[:, 0, :] = initial_forward_curve[np.newaxis, :]
    
    for i in range(1, n_t):
        t = t_array[i-1]
        
        # volatility structure at time t
        vol_t = np.array([vol_func(t, T) for T in T_array])
        
        # Drift (no-arbitrage condition)
        # α(t,T) = σ(t,T) * ∫_t^T σ(t,u) du
        alpha = np.zeros(n_T)
        for j in range(n_T):
            if T_array[j] > t:
                # Integral from t to T: we need indices where T_array[k] >= T_array[j]
                # Find where T_array >= T_array[j]
                mask = T_array >= T_array[j]
                if np.any(mask):
                    integral_vol = np.trapz(vol_t[mask], T_array[mask])
                    alpha[j] = vol_t[j] * integral_vol
                else:
                    alpha[j] = 0
            else:
                # T <= t: forward rate is fixed (已matured)
                alpha[j] = 0
        
        # Forward rate update
        dW = np.random.normal(0, np.sqrt(dt), n_paths)
        
        for j in range(n_T):
            if T_array[j] > t:
                forward_curves[:, i, j] = (
                    forward_curves[:, i-1, j] + 
                    alpha[j] * dt + 
                    vol_t[j] * dW
                )
            else:
                # T <= t: forward rate does not evolve (no longer relevant)
                forward_curves[:, i, j] = forward_curves[:, i-1, j]
    
    return forward_curves

# Initial curve
T_array = np.linspace(0.1, 10, 50)
initial_forward_curve = 0.02 + 0.03 * (1 - np.exp(-T_array / 5))

# Vol structure: parallel shifts
def vol_parallel(t, T):
    return 0.01  # Constant

t_array = np.linspace(0, 5, 20)

print("HJM 1-Factor Simulation initialized")
print(f"Initial forward curve shape: {initial_forward_curve.shape}")
print(f"Maturity range: {T_array[0]:.2f} to {T_array[-1]:.2f} years")
    """))
    
    cells.append(code_cell("""
# ===== HJM Forward Curve Evolution 可視化 =====

def plot_hjm_forward_evolution(vol_type):
    \"\"\"
    異なるvolatility structureでの forward curve evolution
    \"\"\"
    
    T_array = np.linspace(0.1, 10, 50)
    initial_forward = 0.02 + 0.03 * (1 - np.exp(-T_array / 5))
    
    # Vol structure selection
    if vol_type == 'Parallel':
        def vol_func(t, T):
            return 0.01
        title_suffix = 'Parallel Shifts'
    elif vol_type == 'Hump':
        def vol_func(t, T):
            return 0.01 * np.exp(-(T - 5)**2 / 10)
        title_suffix = 'Hump-Shaped Vol'
    else:  # Downward slope
        def vol_func(t, T):
            return 0.015 - 0.001 * T
        title_suffix = 'Downward Sloping Vol'
    
    t_array = np.linspace(0, 5, 10)
    
    forward_curves = hjm_forward_curve_evolution(T_array, t_array, vol_func, initial_forward)
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle(f'HJM Framework: {title_suffix}', fontsize=12, fontweight='bold')
    
    # Panel 1: Multiple forward curves over time
    for i in range(0, len(t_array), 2):
        axes[0].plot(T_array, forward_curves[0, i, :] * 100, 
                    alpha=0.3 + 0.7*(i/len(t_array)), 
                    linewidth=1.5, label=f't={t_array[i]:.1f}y')
    
    axes[0].set_xlabel('Maturity (years)', fontsize=10)
    axes[0].set_ylabel('Forward Rate (%)', fontsize=10)
    axes[0].set_title('Forward Curve Evolution (Sample Path)', fontsize=11, fontweight='bold')
    axes[0].legend(fontsize=8, loc='best')
    axes[0].grid(True, alpha=0.3)
    
    # Panel 2: Volatility structure
    t_sample = 2.5
    vols = np.array([vol_func(t_sample, T) for T in T_array])
    axes[1].plot(T_array, vols * 100, 'b-', linewidth=2, label='Vol(T)')
    axes[1].fill_between(T_array, vols * 100, alpha=0.3)
    axes[1].set_xlabel('Maturity (years)', fontsize=10)
    axes[1].set_ylabel('Volatility (%)', fontsize=10)
    axes[1].set_title(f'Volatility Structure (t={t_sample:.1f}y)', fontsize=11, fontweight='bold')
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()

from ipywidgets import RadioButtons, interact

interact(
    plot_hjm_forward_evolution,
    vol_type=RadioButtons(
        options=['Parallel', 'Hump', 'Downward'],
        description='Vol Shape:',
        value='Parallel'
    )
)
    """))
    
    cells.append(md_cell("""
## 主な特徴

### 強み
- ✅ **統一的な理論枠組み**
- ✅ 多くのモデルを包含（special case）
- ✅ Vol structure = 本質 の理解
- ✅ 一般性が高い

### 弱み
- ❌ 一般形は高次元で計算が重い
- ❌ 実装には特殊化が必要（PCA等でfactor圧縮）
- ❌ 初期化が複雑

### 使用場面
- 🏦 理論的理解
- 🏦 ファクター分解（PCA）
- 🏦 高度なモデル構築
    """))
    
    return cells


# =====================================================================
# CHAPTER 8: LMM / BGM
# =====================================================================

def create_ch8():
    cells = []
    
    cells.append(md_cell("""
# Chapter 8: LMM / BGM (LIBOR Market Model)

## 概要

**LMM (Libor Market Model)** または **BGM (Brace-Gatarek-Musiela)** は、  
複数の **forward LIBOR rate** を直接モデル化するmarketモデルです。

### 特徴
- Forward rate (Libor) を直接ターゲット
- Caplet pricing と市場データの整合性が強い
- 実務で非常によく使われている

## 基本式

複数テナーの forward LIBOR:

$$\\frac{dL_i(t)}{L_i(t)} = \\sigma_i(t) dW_t^{(i)}$$

多ファクター版：

$$\\frac{dL_i(t)}{L_i(t)} = \\sum_k \\sigma_{i,k}(t) dW_t^{(k)}$$

**ポイント:**
- 各テナーが独立のブラウン運動
- Lognormal distributionを仮定
- Caplet = Black76 formula で直接価格付け
    """))
    
    cells.append(code_cell("""
def lmm_forward_libor_simulation(L_initial, tenors, vols, corr_matrix, T, n_steps, n_paths=500):
    \"\"\"
    LMM simulation: Multiple forward LIBORs
    
    dL_i(t) / L_i(t) = μ_i(t) dt + σ_i(t) dW_t^(i)
    
    CORRECTED: Added drift term μ_i(t) from spot measure dynamics
    \"\"\"
    n_tenors = len(tenors)
    dt = T / n_steps
    
    # Initialize
    L_paths = np.zeros((n_paths, n_steps + 1, n_tenors))
    L_paths[:, 0, :] = L_initial[np.newaxis, :]
    
    # Cholesky decomposition for correlated Brownians
    L_chol = np.linalg.cholesky(corr_matrix)
    
    for i in range(1, n_steps + 1):
        t = (i - 1) * dt
        
        # Uncorrelated normals
        dZ = np.random.normal(0, np.sqrt(dt), (n_paths, n_tenors))
        
        # Correlate
        dW = np.dot(dZ, L_chol.T)  # shape: (n_paths, n_tenors)
        
        # Update each forward rate
        for j in range(n_tenors):
            if vols[j] > 0:
                L_t = L_paths[:, i-1, j]
                
                # Compute drift term (spot measure)
                # μ_j = σ_j * Σ_{k>j} ρ_{jk} σ_k τ_k L_k / (1 + τ_k L_k)
                mu_j = 0.0
                tau = np.diff(np.concatenate(([0], tenors)))  # Tenor length
                
                for k in range(j+1, n_tenors):
                    L_k = L_paths[:, i-1, k]
                    tau_k = tau[k] if k < len(tau) else tenors[k] - tenors[k-1]
                    rho_jk = corr_matrix[j, k]
                    term = rho_jk * vols[k] * tau_k * L_k / (1 + tau_k * L_k)
                    mu_j += term
                
                mu_j *= vols[j]
                
                # Lognormal update with drift
                drift_correction = (mu_j - 0.5 * vols[j]**2) * dt
                diffusion = vols[j] * dW[:, j]
                
                L_paths[:, i, j] = L_t * np.exp(drift_correction + diffusion)
            else:
                L_paths[:, i, j] = L_paths[:, i-1, j]
    
    return L_paths

# Test
tenors = np.array([0.25, 0.5, 1.0, 2.0, 5.0])
L_initial = np.array([0.05, 0.052, 0.055, 0.056, 0.055])
vols = np.array([0.15, 0.14, 0.12, 0.10, 0.08])

# Correlation matrix (decreasing with tenor distance)
n_tenors = len(tenors)
corr_matrix = np.zeros((n_tenors, n_tenors))
for i in range(n_tenors):
    for j in range(n_tenors):
        corr_matrix[i, j] = np.exp(-0.1 * abs(tenors[i] - tenors[j]))

np.fill_diagonal(corr_matrix, 1.0)

print("LMM Parameters:")
print(f"Tenors: {tenors}")
print(f"Initial forward rates: {L_initial * 100}")
print(f"Volatilities: {vols * 100}")

# Simulate
L_paths = lmm_forward_libor_simulation(L_initial, tenors, vols, corr_matrix, T=1.0, n_steps=20, n_paths=300)
print(f"\\nSimulation output shape: {L_paths.shape}")
    """))
    
    cells.append(code_cell("""
# ===== LMM Forward Rate Paths + Correlation Heatmap =====

def plot_lmm_analysis():
    \"\"\"
    LMM simulation and correlation visualization
    \"\"\"
    
    tenors = np.array([0.25, 0.5, 1.0, 2.0, 5.0])
    L_initial = np.array([0.05, 0.052, 0.055, 0.056, 0.055])
    vols = np.array([0.15, 0.14, 0.12, 0.10, 0.08])
    
    n_tenors = len(tenors)
    corr_matrix = np.zeros((n_tenors, n_tenors))
    for i in range(n_tenors):
        for j in range(n_tenors):
            corr_matrix[i, j] = np.exp(-0.1 * abs(tenors[i] - tenors[j]))
    np.fill_diagonal(corr_matrix, 1.0)
    
    L_paths = lmm_forward_libor_simulation(L_initial, tenors, vols, corr_matrix, T=1.0, n_steps=20, n_paths=300)
    time_grid = np.linspace(0, 1.0, L_paths.shape[1])
    
    fig = plt.figure(figsize=(14, 9))
    gs = fig.add_gridspec(2, 3, hspace=0.3, wspace=0.3)
    
    fig.suptitle('LMM: Multiple Forward LIBOR Rates', fontsize=12, fontweight='bold')
    
    # Panel 1-5: Forward rate paths for each tenor
    for idx, tenor in enumerate(tenors):
        ax = fig.add_subplot(gs[idx // 3, idx % 3])
        
        for path_idx in range(min(100, L_paths.shape[0])):
            ax.plot(time_grid, L_paths[path_idx, :, idx] * 100, 'b-', alpha=0.1, linewidth=0.5)
        
        mean_path = np.mean(L_paths[:, :, idx], axis=0)
        ax.plot(time_grid, mean_path * 100, 'r-', linewidth=2, label='Mean')
        ax.set_xlabel('Time (years)', fontsize=9)
        ax.set_ylabel('Rate (%)', fontsize=9)
        ax.set_title(f'L({tenor}y) paths', fontsize=10, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)
    
    # Panel 6: Correlation heatmap
    ax = fig.add_subplot(gs[1, 2])
    im = ax.imshow(corr_matrix, cmap='RdBu_r', vmin=0, vmax=1, aspect='auto')
    
    tenor_labels = [f'{t:.2f}y' for t in tenors]
    ax.set_xticks(range(n_tenors))
    ax.set_yticks(range(n_tenors))
    ax.set_xticklabels(tenor_labels, fontsize=8, rotation=45)
    ax.set_yticklabels(tenor_labels, fontsize=8)
    ax.set_title('Correlation Matrix', fontsize=10, fontweight='bold')
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Correlation', fontsize=8)
    
    # Add text annotations
    for i in range(n_tenors):
        for j in range(n_tenors):
            ax.text(j, i, f'{corr_matrix[i, j]:.2f}', ha='center', va='center', 
                   fontsize=7, color='black' if abs(corr_matrix[i, j] - 0.5) > 0.3 else 'white')
    
    plt.show()

plot_lmm_analysis()
    """))
    
    cells.append(md_cell("""
## 主な特徴

### 強み
- ✅ **Market modelとして直感的**
- ✅ Caplet pricing と市場一致
- ✅ テナー毎に独立に volatility 設定可能
- ✅ Correlation 構造を細かく制御

### 弱み
- ❌ Smile/Skew を本来は表現できない（Lognormal前提）
- ❌ 多数のテナー → 高次元で計算負荷
- ❌ LIBOR廃止後の適用に課題

### 使用場面
- 🏦 **Cap/Floor市場との整合性**
- 🏦 複数テナーの同時モデリング
- 🏦 Swaption + Caplet の同時価格付け
    """))
    
    return cells


# =====================================================================
# CHAPTER 9: SABR
# =====================================================================

def create_ch9():
    cells = []
    
    cells.append(md_cell("""
# Chapter 9: SABR Model (Stochastic Alpha-Beta-Rho)

## 概要

**SABR** は、**Smile/Skew を自然に表現** する重要なモデルです。

金利オプション（Swaption）の市場では、 SABR smile が標準的です。

## 基本式

$$dF_t = \\alpha_t F_t^\\beta dW_t^{(1)}$$

$$d\\alpha_t = \\nu \\alpha_t dW_t^{(2)}$$

$$dW_t^{(1)} dW_t^{(2)} = \\rho dt$$

**パラメータ（4つ）:**
- $\\alpha$ = Volatility of volatility (initial)
- $\\beta$ = CEV exponent (0=Normal, 1=Lognormal, 0<β<1=Hybrid)
- $\\rho$ = Correlation between rate and vol (skew)
- $\\nu$ = Vol of vol (smile curvature)
    """))
    
    cells.append(code_cell("""
def hagan_sabr_formula(F, K, T, alpha, beta, rho, nu):
    \"\"\"
    Hagan SABR approximation for implied volatility
    
    Returns implied Black volatility
    \"\"\"
    if abs(F - K) < 1e-8:  # ATM
        sigma_atm = alpha / (F ** (1 - beta))
        
        term2 = (2 - 3*rho**2) / 24 * (nu/alpha)**2 * (F ** (2*(1-beta)))
        term3 = rho * beta * nu / (4*alpha) * (F ** (1-beta))
        term4 = (1 - beta)**2 / 24 * (alpha / (F ** (1-beta)))**2
        
        sigma_atm = sigma_atm * (1 + T * (term2 + term3 + term4))
        
        return sigma_atm
    else:
        z = nu / alpha * (F * K) ** ((1-beta)/2) * np.log(F/K)
        x_z = np.log((np.sqrt(1 - 2*rho*z + z**2) + z - rho) / (1 - rho))
        
        sig_K = (alpha / ((F*K)**((1-beta)/2) * (1 + (1-beta)**2/24 * (np.log(F/K))**2))) * \
                (z / x_z) * (1 + ((1-beta)**2/24 * (alpha/(F*K)**(1-beta))**2 + 
                             rho*beta*nu/(4*alpha) + 
                             (2-3*rho**2)/24*nu**2) * T)
        
        return sig_K

# Test
F_atm = 0.03  # 3% forward
strikes = np.linspace(0.01, 0.05, 50)
T = 1.0

# SABR parameters
alpha_param = 0.3 * F_atm  # 30% of forward
beta_param = 0.5  # CEV exponent
rho_param = -0.5  # Negative correlation (downward skew)
nu_param = 0.5  # Vol of vol

impl_vols = np.array([hagan_sabr_formula(F_atm, K, T, alpha_param, beta_param, rho_param, nu_param) 
                      for K in strikes])

print("SABR Implied Volatility Smile:")
print(f"Parameters: α={alpha_param*100:.2f}%, β={beta_param}, ρ={rho_param}, ν={nu_param}")
print(f"Forward: {F_atm*100:.2f}%, T: {T:.1f}y")
print(f"\\nStrike vs Implied Vol:")
for K, iv in zip(strikes[::5], impl_vols[::5]):
    print(f"  K={K*100:.2f}%: σ={iv*100:.3f}%")
    """))
    
    cells.append(code_cell("""
# ===== SABR Interactive: Smile/Skew 動的可視化 =====

from ipywidgets import FloatSlider, interact

def plot_sabr_smile(alpha_pct, beta_param, rho_param, nu_param):
    \"\"\"
    SABR parameters を変更してsmile/skewを可視化
    \"\"\"
    
    F_atm = 0.03
    alpha = alpha_pct / 100 * F_atm
    T = 1.0
    
    strikes = np.linspace(0.01, 0.05, 100)
    impl_vols = np.array([hagan_sabr_formula(F_atm, K, T, alpha, beta_param, rho_param, nu_param) 
                          for K in strikes])
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle(f'SABR Smile: α={alpha_pct:.1f}%, β={beta_param:.2f}, ρ={rho_param:.2f}, ν={nu_param:.2f}',
                 fontsize=12, fontweight='bold')
    
    # Panel 1: Implied vol curve
    axes[0].plot(strikes * 100, impl_vols * 100, 'b-', linewidth=2.5, label='SABR Smile')
    axes[0].axvline(F_atm * 100, color='r', linestyle='--', alpha=0.7, linewidth=2, label='ATM')
    axes[0].set_xlabel('Strike (%)', fontsize=10)
    axes[0].set_ylabel('Implied Volatility (%)', fontsize=10)
    axes[0].set_title('Smile / Skew Shape', fontsize=11, fontweight='bold')
    axes[0].legend(fontsize=10)
    axes[0].grid(True, alpha=0.3)
    
    # Panel 2: Greeks sensitivity (Vega by strike)
    atm_vol = hagan_sabr_formula(F_atm, F_atm, T, alpha, beta_param, rho_param, nu_param)
    
    # Numerical vega
    dv = 0.001
    vegas = []
    for K in strikes:
        vol_up = hagan_sabr_formula(F_atm, K, T, alpha, beta_param, rho_param, nu_param + dv)
        vol_down = hagan_sabr_formula(F_atm, K, T, alpha, beta_param, rho_param, nu_param - dv)
        vega_numeric = (vol_up - vol_down) / (2 * dv)
        vegas.append(vega_numeric)
    
    axes[1].plot(strikes * 100, vegas, 'g-', linewidth=2.5)
    axes[1].axvline(F_atm * 100, color='r', linestyle='--', alpha=0.7, linewidth=2)
    axes[1].set_xlabel('Strike (%)', fontsize=10)
    axes[1].set_ylabel('Vega Smile (d implied vol / d ν)', fontsize=10)
    axes[1].set_title('Vega Sensitivity to Vol-of-Vol', fontsize=11, fontweight='bold')
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()

interact(
    plot_sabr_smile,
    alpha_pct=FloatSlider(min=5, max=50, step=2, value=30, description='α (% of F):'),
    beta_param=FloatSlider(min=0, max=1, step=0.1, value=0.5, description='β:'),
    rho_param=FloatSlider(min=-0.9, max=0.9, step=0.1, value=-0.5, description='ρ (skew):'),
    nu_param=FloatSlider(min=0.01, max=2, step=0.1, value=0.5, description='ν (smile):')
)

print("✓ Adjust parameters to see smile/skew change")
    """))
    
    cells.append(md_cell("""
## SABR キャリブレーション（市場クォートへのフィット）

実際の市場では、各ストライクの **Implied Vol を観測** し、
SABR パラメータ (α, ρ, ν) を最小二乗でフィットします。
β は通常 0.5 に固定します（market convention）。

$$\\min_{\\alpha, \\rho, \\nu} \\sum_j \\left( \\sigma_{SABR}(K_j) - \\sigma^{mkt}_j \\right)^2$$

詳細な Vol Surface キャリブレーションは **Chapter 11** で扱います。
    """))

    cells.append(code_cell("""
from scipy.optimize import minimize

def calibrate_sabr_ch9(F, T, strikes, market_vols, beta=0.5):
    \"\"\"Simple SABR calibration for Ch9 demo\"\"\"
    alpha0 = market_vols[len(market_vols)//2] * F**(1 - beta)
    bounds = [(1e-4, None), (-0.9999, 0.9999), (1e-4, None)]

    def obj(params):
        a, r, n = params
        model_v = np.array([hagan_sabr_formula(F, K, T, a, beta, r, n) for K in strikes])
        mask = ~np.isnan(model_v)
        return np.sum((model_v[mask] - market_vols[mask])**2) if np.any(mask) else 1e6

    res = minimize(obj, [alpha0, -0.3, 0.4], method='L-BFGS-B', bounds=bounds)
    a_fit, r_fit, n_fit = res.x
    fitted = np.array([hagan_sabr_formula(F, K, T, a_fit, beta, r_fit, n_fit) for K in strikes])
    rmse_bp = np.sqrt(np.mean((fitted - market_vols)**2)) * 10000
    return a_fit, r_fit, n_fit, rmse_bp, fitted

# ===== 疑似市場クォートの生成（True SABR + ノイズ） =====
np.random.seed(42)
F_cal = 0.03
T_cal = 1.0
beta_cal = 0.5
true_alpha, true_rho, true_nu = 0.014, -0.45, 0.45
offsets_bp = np.array([-100, -75, -50, -25, 0, 25, 50, 75, 100])
strikes_cal = np.maximum(F_cal + offsets_bp / 10000, 1e-4)

true_vols = np.array([hagan_sabr_formula(F_cal, K, T_cal, true_alpha, beta_cal, true_rho, true_nu)
                      for K in strikes_cal])
market_vols_cal = true_vols + np.random.normal(0, 2e-4, len(strikes_cal))  # 2bp noise

# ===== キャリブレーション実行 =====
a_fit, r_fit, n_fit, rmse, fitted_v = calibrate_sabr_ch9(
    F_cal, T_cal, strikes_cal, market_vols_cal, beta=beta_cal
)

print("=== SABR Calibration Demo ===")
print(f"True:   α={true_alpha:.4f}, ρ={true_rho:.3f}, ν={true_nu:.3f}")
print(f"Fitted: α={a_fit:.4f}, ρ={r_fit:.3f}, ν={n_fit:.3f}")
print(f"RMSE: {rmse:.2f} bp")

# ===== 可視化 =====
fine_k = np.linspace(0.005, 0.055, 200)
true_fine = np.array([hagan_sabr_formula(F_cal, K, T_cal, true_alpha, beta_cal, true_rho, true_nu)
                      for K in fine_k])
fit_fine = np.array([hagan_sabr_formula(F_cal, K, T_cal, a_fit, beta_cal, r_fit, n_fit)
                     for K in fine_k])

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle('SABR Calibration to Market Quotes', fontsize=13, fontweight='bold')

axes[0].plot(fine_k*100, true_fine*100, 'k--', lw=1.5, label='True SABR')
axes[0].plot(fine_k*100, fit_fine*100, 'b-', lw=2.5, label=f'Calibrated (RMSE={rmse:.1f}bp)')
axes[0].scatter(strikes_cal*100, market_vols_cal*100, color='red', s=60, zorder=5, label='Market quotes')
axes[0].axvline(F_cal*100, color='gray', ls=':', lw=1.5, label='ATM')
axes[0].set_xlabel('Strike (%)'); axes[0].set_ylabel('Implied Vol (%)')
axes[0].set_title('Smile Fit'); axes[0].legend(); axes[0].grid(True, alpha=0.3)

residuals = (fitted_v - market_vols_cal) * 10000
colors = ['#d62728' if e > 0 else '#1f77b4' for e in residuals]
axes[1].bar(offsets_bp, residuals, color=colors, alpha=0.8)
axes[1].axhline(0, color='k', lw=0.8)
axes[1].set_xlabel('Strike Offset (bp)'); axes[1].set_ylabel('Fitted − Market (bp)')
axes[1].set_title('Calibration Residuals'); axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.show()
print("✓ SABR calibration demo complete  →  詳細は Chapter 11 へ")
    """))

    cells.append(md_cell("""
## 主な特徴

### 強み
- ✅ **Smile/Skew を自然に表現**
- ✅ 少数パラメータ（4つ）で直感的
- ✅ Hagan公式により高速計算
- ✅ Swaption市場で標準

### 弱み
- ❌ 解析的closed-form解はない（Hagan近似）
- ❌ パラメータキャリブレーションが必要
- ❌ Short maturities では精度低下

### 使用場面
- 🏦 **Swaption smile価格付け**
- 🏦 Exotics（Bermudan等）
- 🏦 **Vol surface calibration** → 詳細は Chapter 11
    """))

    return cells


# =====================================================================
# CHAPTER 10: RFR Framework
# =====================================================================

def create_ch10():
    cells = []
    
    cells.append(md_cell("""
# Chapter 10: RFR Framework

## 概要

**LIBOR廃止**（2023年）に伴い、世界の金利市場は **Reference Rate (RFR)** へ移行しました。

従来のモデルは **固定テナーの LIBOR** を前提としていましたが、  
現在は **日次複利 RFR** をベースにした金利モデリングが必須です。

### 各国のRFR
| 地域 | 旧LIBOR | 新RFR | 特徴 |
|-----|--------|-------|------|
| **米国** | USD LIBOR | SOFR | Treasury Repo Rate（セキュア） |
| **英国** | GBP LIBOR | SONIA | Bank of England政策レート |
| **日本** | JPY LIBOR | TONA | 無担保コール市場 |
| **EU** | EUR LIBOR | ESTR | ECB政策レート |

## RFRの本質

### LIBOR（テナー・アベレージ）
\\[
L_i(T_{start}, T_{end}) = \\frac{1}{\\delta}\\left( \\frac{P(T_{start})}{P(T_{end})} - 1 \\right)
\\]
- 将来のテナー期間（3M, 6M等）の平均金利を**前もって決定**
- 市場参加者のサーベイに基づく（LIBOR scandal の原因）

### RFR（日次複利）
\\[
R(T_{start}, T_{end}) = \\prod_{d=1}^{D}(1 + r_d \\delta_d) - 1
\\]
- **毎日の** overnight rate を実績ベースで複利
- 透明性が高い（取引ベース）
- **離散複利** → **連続複利**への近似
    """))
    
    cells.append(code_cell("""
import numpy as np
import matplotlib.pyplot as plt

# RFR simulation: daily overnight rates
np.random.seed(42)

def rfr_compounding_simulation(n_days=252, overnight_level=0.05, overnight_vol=0.001):
    \"\"\"
    Daily overnight rate から RFR compounded rate を計算
    
    Parameters:
    - n_days: 期間（日数）
    - overnight_level: 平均overnight rate
    - overnight_vol: overnight rateのボラティリティ
    \"\"\"
    
    # Daily overnight rates (Vasicek-like simulation)
    dt = 1 / 252
    r_on = overnight_level * np.ones(n_days)
    
    for i in range(1, n_days):
        drift = -0.01 * (r_on[i-1] - overnight_level)
        diffusion = overnight_vol * np.random.randn() * np.sqrt(dt)
        r_on[i] = r_on[i-1] + drift * dt + diffusion
        r_on[i] = max(r_on[i], 0)  # Non-negative floor
    
    # RFR compounding: product form
    rfr_compound = np.prod(1 + r_on * dt) - 1
    
    # Continuous approximation (easier for analytics)
    rfr_continuous = np.exp(np.mean(np.log(1 + r_on * dt)) * n_days) - 1
    
    return r_on, rfr_compound, rfr_continuous

# Simulation
r_on, rfr_compound, rfr_continuous = rfr_compounding_simulation(
    n_days=252, overnight_level=0.05, overnight_vol=0.002
)

print(f"RFR Compounding Example (1 year, 252 days):")
print(f"  Average overnight rate: {np.mean(r_on)*100:.3f}%")
print(f"  RFR (discrete compounding): {rfr_compound*100:.3f}%")
print(f"  RFR (continuous approx): {rfr_continuous*100:.3f}%")
print(f"  Difference: {(rfr_compound - rfr_continuous)*10000:.2f} bps")

# Comparison over different compounding periods
periods = [63, 126, 252]  # 3M, 6M, 1Y
rfr_rates = []
for p in periods:
    _, rfi_c, rfi_cont = rfr_compounding_simulation(n_days=p, overnight_level=0.05, overnight_vol=0.002)
    rfr_rates.append((rfi_c, rfi_cont))

print(f"\\nRFR by Period:")
for p, (c, cont) in zip(periods, rfr_rates):
    print(f"  {p}d ({p/252*12:3.1f}M): Discrete={c*100:6.3f}%, Continuous={cont*100:6.3f}%")
    """))
    
    cells.append(code_cell("""
# ===== RFR Curve Evolution =====

def plot_rfr_framework(vol_level, curve_slope):
    \"\"\"
    RFR曲線の進化を可視化
    \"\"\"
    
    T_array = np.linspace(0.25, 10, 40)  # 3M から 10Y
    
    # RFR discount curve (simpler than LIBOR - single curve)
    base_level = 0.05
    rfr_curve = base_level + curve_slope * (1 - np.exp(-T_array / 5))
    
    # Simulate path of overnight rate
    np.random.seed(42)
    dt = 1 / 252
    n_days = 252
    r_on = np.zeros(n_days)
    r_on[0] = base_level
    for i in range(1, n_days):
        drift = -0.05 * (r_on[i-1] - base_level)
        r_on[i] = r_on[i-1] + drift * dt + vol_level * np.random.randn() * np.sqrt(dt)
        r_on[i] = max(r_on[i], 0)
    
    # Discount curve
    df_rfr = np.exp(-rfr_curve * T_array)
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle(f'RFR Framework: Overnight Vol={vol_level:.3f}, Curve Slope={curve_slope:.2%}',
                 fontsize=12, fontweight='bold')
    
    # Panel 1: RFR Zero Curve
    axes[0].plot(T_array, rfr_curve * 100, 'g-', linewidth=2.5, marker='o', markersize=4)
    axes[0].fill_between(T_array, 0, rfr_curve * 100, alpha=0.2, color='green')
    axes[0].set_xlabel('Maturity (years)', fontsize=10)
    axes[0].set_ylabel('Zero Rate (%)', fontsize=10)
    axes[0].set_title('RFR Zero Curve (Single Curve)', fontsize=11, fontweight='bold')
    axes[0].grid(True, alpha=0.3)
    
    # Panel 2: Overnight Rate Path
    days = np.arange(n_days)
    axes[1].plot(days, r_on * 100, 'b-', linewidth=1, alpha=0.7)
    axes[1].axhline(y=np.mean(r_on)*100, color='r', linestyle='--', linewidth=2, label=f'Mean={np.mean(r_on)*100:.2f}%')
    axes[1].fill_between(days, 0, r_on * 100, alpha=0.2, color='blue')
    axes[1].set_xlabel('Days', fontsize=10)
    axes[1].set_ylabel('Overnight Rate (%)', fontsize=10)
    axes[1].set_title('Daily ON Rate (1Y simulation)', fontsize=11, fontweight='bold')
    axes[1].legend(fontsize=9)
    axes[1].grid(True, alpha=0.3)
    
    # Panel 3: Discount Factors
    axes[2].plot(T_array, df_rfr, 'g-', linewidth=2.5, marker='o', markersize=4)
    axes[2].set_xlabel('Maturity (years)', fontsize=10)
    axes[2].set_ylabel('Discount Factor', fontsize=10)
    axes[2].set_title('RFR Discount Factors', fontsize=11, fontweight='bold')
    axes[2].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()

from ipywidgets import FloatSlider, interact

interact(
    plot_rfr_framework,
    vol_level=FloatSlider(min=0.0005, max=0.01, step=0.0005, value=0.002, description='ON Vol:'),
    curve_slope=FloatSlider(min=0, max=0.05, step=0.005, value=0.02, description='Curve Slope:')
)
    """))
    
    cells.append(md_cell("""
## RFR vs LIBOR in モデリング

### Single Curve vs Multi-Curve

**LIBOR時代（2020年以前）:**
- Forward LIBOR と Discounting が一つのcurveで混在
- Basis spread は副次的（低）

**RFR時代（2023年以降）:**
- **単一RFR曲線**でDiscounting & Forward rateを統一
- LIBOR legacy商品とRFR新商品を区別管理

### 金利モデルへの影響

| 項目 | LIBOR | RFR |
|------|-------|-----|
| **State Variable** | Tenor-based forward rate | Overnight rate + 複利演算 |
| **Curve数** | Multi-curve（OIS+LIBOR）| Single curve |
| **Compounding** | 単一テナー | 日次複利 |
| **モデル** | LMM/BGM | RFR-based LMM |
| **Smile** | High（LIBOR basis） | Low（単純化） |

## 主な特徴

### 強み
- ✅ **単一曲線で完結**（シンプル）
- ✅ 透明性・統一性が高い
- ✅ ベンチマーク金利として信頼性
- ✅ Global移行の標準

### 弱み
- ❌ Legacy LIBOR商品との管理複雑化
- ❌ Transition期間（2020-2023）でのconvexity
- ❌ RFR basis（テナー別RFRは存在しない）

### 使用場面
- 🏦 **現在のすべての新規取引**
- 🏦 金利デリバティブ（IRS, Caps, Swaptions）
- 🏦 融資・貸出金利ベンチマーク
- 🏦 Legacy LIBOR商品のヘッジ・管理
    """))
    
    return cells


# =====================================================================
# FINAL: Model Comparison
# =====================================================================

def create_final():
    cells = []
    
    cells.append(md_cell("""
# Final Chapter: Model Comparison & Selection Guide

これまでの10のモデルを、横断的に比較します。

- モデル分類
- 機能比較
- 使用場面
- パラメータ数
- 計算複雑度
    """))
    
    cells.append(code_cell("""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ===== Model Comparison Table =====

models_data = {
    'Model': ['Black 76', 'Bachelier', 'Vasicek', 'CIR', 'Hull-White 1F', 'G2++', 'HJM', 'LMM/BGM', 'SABR', 'Multi-Curve'],
    'Type': ['Option', 'Option', 'SRM', 'SRM', 'SRM', 'SRM', 'Framework', 'Market', 'Option', 'Framework'],
    'Factors': [0, 0, 1, 1, 1, 2, 'Multi', 'Multi', 2, 'Multi'],
    'Neg Rates': ['No', 'Yes', 'Yes', 'No', 'Yes', 'Yes', 'Yes', 'Yes', 'Hybrid', 'Flexible'],
    'Smile': ['No', 'No', 'No', 'No', 'No', 'No', 'No', 'No', 'Yes', 'Yes'],
    'Curve Fit': ['N/A', 'N/A', 'Manual', 'Manual', 'Auto', 'Auto', 'Auto', 'Auto', 'Manual', 'Auto'],
    'Greeks': ['Analytical', 'Analytical', 'Analytical', 'Numerical', 'Analytical', 'Numerical', 'Numerical', 'Numerical', 'Hagan', 'Numerical'],
    'Complexity': [1, 1, 2, 2, 3, 4, 5, 5, 3, 5],
    'Industry Use': [10, 3, 4, 3, 10, 8, 2, 9, 9, 10]
}

df_comparison = pd.DataFrame(models_data)

print("="*100)
print("MODEL COMPARISON TABLE")
print("="*100)
print(df_comparison.to_string(index=False))
print("\\nLegend:")
print("  Type: Option=Option pricing model, SRM=Short Rate Model, Market=Market model, Framework=General framework")
print("  Neg Rates: Support for negative rates")
print("  Smile: Can express smile/skew")
print("  Curve Fit: Auto=Automatic initial curve fit, Manual=Requires manual tuning, N/A=Not applicable")
print("  Greeks: Analytical/Numerical/Hagan approximation")
print("  Complexity: 1(Simple) to 5(Complex)")
print("  Industry Use: 1(Academic) to 10(Standard in practice)")
    """))
    
    cells.append(code_cell("""
# ===== Model Classification Scatter =====

fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle('Interest Rate Model Classification', fontsize=12, fontweight='bold')

# Panel 1: Complexity vs Flexibility
models = df_comparison['Model'].values
complexity = df_comparison['Complexity'].values
industry_use = df_comparison['Industry Use'].values

scatter = axes[0].scatter(complexity, industry_use, s=300, alpha=0.6, c=range(len(models)), cmap='tab10')

for i, model in enumerate(models):
    axes[0].annotate(model, (complexity[i], industry_use[i]), 
                    fontsize=9, ha='center', va='center', fontweight='bold')

axes[0].set_xlabel('Complexity (1=Simple → 5=Complex)', fontsize=10)
axes[0].set_ylabel('Industry Usage (1=Academic → 10=Standard)', fontsize=10)
axes[0].set_title('Model Complexity vs Practical Use', fontsize=11, fontweight='bold')
axes[0].grid(True, alpha=0.3)
axes[0].set_xlim(0, 6)
axes[0].set_ylim(0, 11)

# Panel 2: Feature Capability Matrix
features = ['Neg Rates', 'Smile', 'Curve Fit', 'Quick Greeks']
capability_matrix = np.zeros((len(models), len(features)))

for i, model in enumerate(models):
    capability_matrix[i, 0] = 1 if df_comparison.loc[i, 'Neg Rates'] == 'Yes' else 0.5 if df_comparison.loc[i, 'Neg Rates'] == 'Hybrid' else 0
    capability_matrix[i, 1] = 1 if df_comparison.loc[i, 'Smile'] == 'Yes' else 0
    capability_matrix[i, 2] = 1 if df_comparison.loc[i, 'Curve Fit'] == 'Auto' else 0.5 if df_comparison.loc[i, 'Curve Fit'] == 'Manual' else 0
    capability_matrix[i, 3] = 1 if df_comparison.loc[i, 'Greeks'] == 'Analytical' else 0.5 if df_comparison.loc[i, 'Greeks'] == 'Hagan' else 0

im = axes[1].imshow(capability_matrix.T, cmap='RdYlGn', vmin=0, vmax=1, aspect='auto')

axes[1].set_xticks(range(len(models)))
axes[1].set_yticks(range(len(features)))
axes[1].set_xticklabels(models, fontsize=9, rotation=45, ha='right')
axes[1].set_yticklabels(features, fontsize=10)
axes[1].set_title('Feature Capability Heatmap', fontsize=11, fontweight='bold')

# Add colorbar
cbar = plt.colorbar(im, ax=axes[1], label='Capability')

# Add text annotations
for i in range(len(models)):
    for j in range(len(features)):
        val = capability_matrix[i, j]
        text = '✓' if val == 1 else '△' if val == 0.5 else '✗'
        axes[1].text(i, j, text, ha='center', va='center', fontsize=12, fontweight='bold')

plt.tight_layout()
plt.show()

print("✓ Model classification visualization complete")
    """))
    
    cells.append(md_cell("""
## 使用場面別ガイド

### Caplet / Cap-Floor
- ✅ **Black 76** (市場標準)
- ✅ **Bachelier** (マイナス金利環境)
- ✅ **LMM/BGM** (複数テナー同時)

### Swaption
- ✅ **Hull-White 1F** (シンプル)
- ✅ **G2++** (スロープ変動)
- ✅ **SABR** (Smile対応、市場標準)

### Bermudan Swaption
- ✅ **G2++** (2ファクター)
- ✅ **LMM/BGM** (多ファクター)

### 初期学習・教育
- ✅ **Vasicek** (基本)
- ✅ **Black 76 & Bachelier** (オプション基礎)
- ✅ **Hull-White 1F** (実務基本)

### 学術研究
- ✅ **HJM Framework** (理論的枠組み)
- ✅ **CIR** (非負性の数学)
- ✅ **SABR** (Smile理論)

### 現代的な金利管理
- ✅ **Multi-Curve Framework** (必須)
- ✅ **RFR Models** (SOFR/SONIA対応)
    """))
    
    cells.append(md_cell("""
## まとめ

### 金利モデル選択の視点

| 観点 | チェックポイント |
|------|-----------------|
| **市場データ** | Caplet? Swaption? Bermudan? 複数テナー? |
| **金利環境** | マイナス金利の可能性？ |
| **計算速度** | Real-time pricing 必要？ |
| **精度** | Smile/Skew を表現すべき？ |
| **実装コスト** | 開発リソース？ |
| **市場標準** | Industry convention への準拠 |

---

## 次のステップ

このノートブックで学習した内容：

1. ✅ 金利の基本概念（Yield curve, Forward rate）
2. ✅ オプション価格付けの基本（Black-Scholes → Black 76, Bachelier）
3. ✅ 短期金利モデル（Vasicek, CIR, Hull-White）
4. ✅ マルチファクターモデル（G2++）
5. ✅ 統一的枠組み（HJM）
6. ✅ マーケットモデル（LMM/BGM）
7. ✅ Smile表現（SABR）
8. ✅ 現代的枠組み（Multi-Curve, RFR）

### 実務への適用
- キャリブレーションの実装
- 価格付けエンジンの構築
- Greeks の計算
- ストレステスト・シナリオ分析

### さらに深堀りするテーマ
- Volatility surface interpolation
- Cross-gamma / Correlation risk
- XVA (CVA, DVA, KVA)
- Machine learning for calibration
    """))
    
    return cells


# =====================================================================
# Assemble Notebook (Part 3)
# =====================================================================

if __name__ == '__main__':
    nb = nbf.v4.new_notebook()
    
    cells = []
    
    # Add chapters
    cells.extend(create_ch7())
    cells.extend(create_ch8())
    cells.extend(create_ch9())
    cells.extend(create_ch10())
    cells.extend(create_final())
    
    nb.cells = cells
    
    # Save
    output_path = '/home/kazumasa/projects/rates_volatility_model/rates_volatility_models_part3.ipynb'
    with open(output_path, 'w') as f:
        nbf.write(nb, f)
    
    print(f"✓ Generated: {output_path}")
    print(f"  Total cells: {len(cells)}")
