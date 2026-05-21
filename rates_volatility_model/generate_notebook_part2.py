"""
Generate Jupyter Notebook: Interest Rate Volatility Models (Part 2: Ch3-Ch6)
"""

import nbformat as nbf
import numpy as np

np.random.seed(42)


def md_cell(text):
    return nbf.v4.new_markdown_cell(text)


def code_cell(code):
    return nbf.v4.new_code_cell(code)


# =====================================================================
# CHAPTER 3: Vasicek Model
# =====================================================================


def create_ch3():
    cells = []

    cells.append(
        md_cell("""
# Chapter 3: Vasicek Model

## 概要

**Vasicek Model** は、短期金利（short rate）の **平均回帰** (mean reversion) 動学を記述する最初の重要なモデルです。

### 特徴
- 短期金利 $r_t$ が確率的に動く
- 長期平均 $b$ に向かってドリフト
- ガウス過程（マイナス金利も許す）

## 基本式

$$dr_t = a(b - r_t)dt + \\sigma dW_t$$

**パラメータの意味:**
- $a$ = Mean reversion speed（大きいほど素早く平均に戻る）
- $b$ = Long-term mean（目標金利）
- $\\sigma$ = Volatility（ランダムショックの大きさ）

## 解析解

$$r_t = b + (r_0 - b)e^{-at} + \\sigma\\int_0^t e^{-a(t-s)} dW_s$$

期待値：$E[r_t] = b + (r_0 - b)e^{-at}$

分散：$V[r_t] = \\frac{\\sigma^2}{2a}(1 - e^{-2at})$

長期分散：$\\lim_{t\\to\\infty} V[r_t] = \\frac{\\sigma^2}{2a}$
    """)
    )

    cells.append(
        code_cell("""
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import odeint

def vasicek_path_euler(r0, a, b, sigma, T, n_steps, n_paths=1000):
    \"\"\"
    Vasicek SDE を Euler-Maruyama スキームで simulation
    
    dr_t = a(b - r_t)dt + sigma * dW_t
    \"\"\"
    dt = T / n_steps
    paths = np.zeros((n_paths, n_steps + 1))
    paths[:, 0] = r0
    
    for i in range(n_steps):
        dW = np.random.normal(0, np.sqrt(dt), n_paths)
        paths[:, i+1] = paths[:, i] + a * (b - paths[:, i]) * dt + sigma * dW
    
    return paths

def vasicek_path_analytical(r0, a, b, sigma, T, n_steps, n_paths=1000):
    \"\"\"
    Vasicek の解析解を使った simulation
    
    より正確な方法
    \"\"\"
    dt = T / n_steps
    t_array = np.linspace(0, T, n_steps + 1)
    paths = np.zeros((n_paths, n_steps + 1))
    paths[:, 0] = r0
    
    for i in range(n_steps):
        t = t_array[i]
        exp_minus_a_dt = np.exp(-a * dt)
        
        # Conditional mean and variance
        cond_mean = b + (paths[:, i] - b) * exp_minus_a_dt
        cond_var = sigma**2 * (1 - exp_minus_a_dt**2) / (2 * a)
        
        paths[:, i+1] = cond_mean + np.sqrt(cond_var) * np.random.normal(0, 1, n_paths)
    
    return paths

# テスト設定
r0 = 0.03  # 初期短期金利 3%
a_val = 0.15
b_val = 0.05  # 長期平均 5%
sigma_val = 0.02  # 2% volatility

T = 10.0
n_steps = 100
n_paths = 1000

print("Parameters:")
print(f"  r0: {r0*100:.2f}%")
print(f"  a (mean reversion): {a_val}")
print(f"  b (long-term mean): {b_val*100:.2f}%")
print(f"  sigma: {sigma_val*100:.2f}%")
print(f"  T: {T} years, n_paths: {n_paths}")

# Analytical simulation
paths = vasicek_path_analytical(r0, a_val, b_val, sigma_val, T, n_steps, n_paths)
time_grid = np.linspace(0, T, n_steps + 1)

print(f"\\nPath statistics at T={T}:")
print(f"  Mean: {np.mean(paths[:, -1])*100:.4f}%")
print(f"  Std: {np.std(paths[:, -1])*100:.4f}%")
print(f"  Expected: {b_val*100:.4f}% (long-term mean)")
    """)
    )

    cells.append(
        code_cell("""
# ===== Vasicek 動的可視化（ipywidgets）=====

from ipywidgets import FloatSlider, interact

def plot_vasicek_sensitivity(a_param, b_param, sigma_param):
    \"\"\"
    a, b, sigma をスライダーで調整
    パスの形状がリアルタイムで変わる
    \"\"\"
    
    r0 = 0.03
    T = 10.0
    n_steps = 100
    n_paths = 500
    
    paths = vasicek_path_analytical(r0, a_param, b_param, sigma_param, T, n_steps, n_paths)
    time_grid = np.linspace(0, T, n_steps + 1)
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle(f'Vasicek Sensitivity: a={a_param:.2f}, b={b_param*100:.2f}%, σ={sigma_param*100:.2f}%',
                 fontsize=12, fontweight='bold')
    
    # Panel 1: Sample paths
    for i in range(min(100, n_paths)):
        axes[0].plot(time_grid, paths[i, :] * 100, 'b-', alpha=0.1, linewidth=0.5)
    
    # Mean path
    mean_path = np.mean(paths, axis=0)
    axes[0].plot(time_grid, mean_path * 100, 'r-', linewidth=2.5, label='Mean Path')
    
    # Long-term mean
    axes[0].axhline(b_param * 100, color='green', linestyle='--', linewidth=2, label='Long-term Mean')
    axes[0].set_xlabel('Time (years)', fontsize=10)
    axes[0].set_ylabel('Short Rate (%)', fontsize=10)
    axes[0].set_title('Short Rate Paths (Blue) vs Mean (Red)', fontsize=11, fontweight='bold')
    axes[0].legend(fontsize=9)
    axes[0].grid(True, alpha=0.3)
    
    # Panel 2: Distribution at terminal time
    terminal_rates = paths[:, -1]
    axes[1].hist(terminal_rates * 100, bins=50, density=True, alpha=0.7, color='skyblue', edgecolor='black')
    
    # Theoretical distribution
    from scipy.stats import norm as sp_norm
    expected_mean = b_param + (r0 - b_param) * np.exp(-a_param * T)
    expected_var = sigma_param**2 * (1 - np.exp(-2 * a_param * T)) / (2 * a_param)
    expected_std = np.sqrt(expected_var)
    
    x_range = np.linspace(expected_mean - 4*expected_std, expected_mean + 4*expected_std, 200)
    axes[1].plot(x_range * 100, sp_norm.pdf(x_range, expected_mean, expected_std), 
                 'r-', linewidth=2, label='Theoretical')
    
    axes[1].set_xlabel('Short Rate at T (%)', fontsize=10)
    axes[1].set_ylabel('Density', fontsize=10)
    axes[1].set_title(f'Terminal Distribution (T={T} years)', fontsize=11, fontweight='bold')
    axes[1].legend(fontsize=9)
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()

# インタラクティブ実行
interact(
    plot_vasicek_sensitivity,
    a_param=FloatSlider(min=0.01, max=1.0, step=0.05, value=0.15, description='a (Mean Rev.):'),
    b_param=FloatSlider(min=0.01, max=0.10, step=0.005, value=0.05, description='b (Long-term %):'),
    sigma_param=FloatSlider(min=0.001, max=0.05, step=0.005, value=0.02, description='σ (%):')
)

print("✓ Adjust sliders to see path dynamics change")
    """)
    )

    cells.append(
        md_cell("""
## 簡易キャリブレーション：Zero Curve フィット

Vasicek モデルを initial zero curve にフィットさせます。

市場の zero curve が観測されているとき、 $a, b, \\sigma$ を推定します。
    """)
    )

    cells.append(
        code_cell("""
from scipy.optimize import minimize

def vasicek_bond_price_analytical(r, a, b, sigma, tau):
    \"\"\"
    Vasicek zero coupon bond price
    P(r, tau) = A(tau) * exp(-B(tau) * r)
    \"\"\"
    B = (1 - np.exp(-a * tau)) / a
    A_log = (b - sigma**2 / (2 * a**2)) * (B - tau) - sigma**2 * B**2 / (4 * a)
    A = np.exp(A_log)
    
    price = A * np.exp(-B * r)
    return price

def vasicek_zero_rate(r, a, b, sigma, tau):
    \"\"\"Bond price から zero rate を導出\"\"\"
    P = vasicek_bond_price_analytical(r, a, b, sigma, tau)
    return -np.log(P) / tau

def calibrate_vasicek(market_zero_curve, T_array, r0):
    \"\"\"
    Market zero curve に Vasicek をフィット
    \"\"\"
    def objective(params):
        a, b, sigma = params
        
        # 負や不合理なパラメータを拒否
        if a <= 0 or b <= 0 or sigma <= 0:
            return 1e10
        
        model_zeros = np.array([vasicek_zero_rate(r0, a, b, sigma, T) for T in T_array])
        
        # Mean squared error
        mse = np.sum((model_zeros - market_zero_curve)**2)
        return mse
    
    # 初期値
    x0 = [0.1, 0.05, 0.01]
    
    result = minimize(
        objective,
        x0,
        bounds=[(0.01, 1.0), (0.001, 0.2), (0.001, 0.1)],
        method='L-BFGS-B'
    )
    
    return result.x, result.fun

# テスト：Upward sloping zero curve
T_array = np.linspace(0.5, 10, 20)
market_zero_curve = 0.02 + 0.03 * (1 - np.exp(-T_array / 5))  # Upward curve
r0 = market_zero_curve[0]

print("Market Zero Curve (sample):")
for T, Z in zip(T_array[::2], market_zero_curve[::2]):
    print(f"  T={T:4.1f}y: {Z*100:.3f}%")

# Calibrate
params, error = calibrate_vasicek(market_zero_curve, T_array, r0)
a_cal, b_cal, sigma_cal = params

print(f"\\nCalibrated Parameters:")
print(f"  a: {a_cal:.4f}")
print(f"  b: {b_cal*100:.4f}%")
print(f"  σ: {sigma_cal*100:.4f}%")
print(f"  MSE: {error:.6e}")

# Check fit
model_zeros = np.array([vasicek_zero_rate(r0, a_cal, b_cal, sigma_cal, T) for T in T_array])

print(f"\\nFit Quality:")
print(f"  Market vs Model at selected maturities:")
for T, Z_mkt, Z_mdl in zip(T_array[::4], market_zero_curve[::4], model_zeros[::4]):
    print(f"    T={T:4.1f}y: Market={Z_mkt*100:.3f}% Model={Z_mdl*100:.3f}% Diff={abs(Z_mkt-Z_mdl)*10000:.1f}bps")
    """)
    )

    cells.append(
        md_cell("""
## 主な特徴

### 強み
- ✅ **平均回帰** を自然に表現
- ✅ 解析的に扱いやすい
- ✅ Bond pricing が解析的
- ✅ Greeks 計算が容易

### 弱み
- ❌ 金利がマイナスになり得る
- ❌ 初期 zero curve に自動フィットしない（手動パラメータ設定）
- ❌ 単一ファクターなので curve の形を柔軟に表現できない

### 使用場面
- 🏦 学術研究・教育
- 🏦 シンプルな金利動学が必要な場合
- 🏦 解析的結果が欲しい場合
    """)
    )

    return cells


# =====================================================================
# CHAPTER 4: CIR Model
# =====================================================================


def create_ch4():
    cells = []

    cells.append(
        md_cell("""
# Chapter 4: CIR Model (Cox-Ingersoll-Ross)

## 概要

**CIR Model** は、金利の **非負性** を保証するために、ボラティリティを金利水準に依存させたモデルです。

### 特徴
- 短期金利が常に非負
- ボラティリティが金利に依存
- 平均回帰＋ level-dependent volatility

## 基本式

$$dr_t = a(b - r_t)dt + \\sigma\\sqrt{r_t} dW_t$$

**パラメータ:**
- $a$ = Mean reversion speed
- $b$ = Long-term mean
- $\\sigma$ = Volatility scale

## Feller Condition（非負性を保証する条件）

CIR が非負を保つためには：

$$2ab \\geq \\sigma^2$$

この条件が満たされれば、$r_t \\geq 0$ が保証されます。

### 条件を満たさない場合
- 金利がゼロに達すると、$\\sqrt{r_t}$ の項がゼロになり反射
- Boundary condition: $r_t$ がゼロに達すると反射
    """)
    )

    cells.append(
        code_cell("""
def cir_path_euler(r0, a, b, sigma, T, n_steps, n_paths=1000):
    \"\"\"
    CIR SDE を Euler-Maruyama で simulation
    
    dr_t = a(b - r_t)dt + sigma * sqrt(r_t) * dW_t
    
    非負性を保つため、r_t < 0 になったら 0 に設定（Reflection）
    \"\"\"
    dt = T / n_steps
    paths = np.zeros((n_paths, n_steps + 1))
    paths[:, 0] = r0
    
    for i in range(n_steps):
        sqrt_r = np.sqrt(np.maximum(paths[:, i], 0))  # 非負性を保つ
        dW = np.random.normal(0, np.sqrt(dt), n_paths)
        
        paths[:, i+1] = paths[:, i] + a * (b - paths[:, i]) * dt + sigma * sqrt_r * dW
        paths[:, i+1] = np.maximum(paths[:, i+1], 0)  # Reflection at zero
    
    return paths

def feller_condition_check(a, b, sigma):
    \"\"\"
    Feller condition: 2ab >= sigma^2 を check
    
    Returns:
        True if condition is satisfied (non-negative guaranteed)
        False otherwise
    \"\"\"
    return 2 * a * b >= sigma**2

# テスト
r0 = 0.03
a_val = 0.15
b_val = 0.05
sigma_val = 0.02

T = 10.0
n_steps = 100
n_paths = 1000

# Feller condition
feller_ok = feller_condition_check(a_val, b_val, sigma_val)
print(f"Parameters: a={a_val}, b={b_val*100:.2f}%, σ={sigma_val*100:.2f}%")
print(f"Feller Condition (2ab >= σ²): {feller_ok}")
print(f"  2ab = {2*a_val*b_val:.6f}")
print(f"  σ² = {sigma_val**2:.6f}")

# Simulate
paths_cir = cir_path_euler(r0, a_val, b_val, sigma_val, T, n_steps, n_paths)
time_grid = np.linspace(0, T, n_steps + 1)

print(f"\\nCIR Simulation:")
print(f"  Terminal mean: {np.mean(paths_cir[:, -1])*100:.4f}%")
print(f"  Terminal min: {np.min(paths_cir[:, -1])*100:.4f}%")
print(f"  Terminal max: {np.max(paths_cir[:, -1])*100:.4f}%")
print(f"  % time at r=0: {(np.sum(paths_cir < 0.0001) / paths_cir.size)*100:.2f}%")
    """)
    )

    cells.append(
        code_cell("""
# ===== Vasicek vs CIR 比較 + ipywidgets =====

from ipywidgets import FloatSlider, interact

def plot_vasicek_vs_cir(a_param, b_param, sigma_param):
    \"\"\"
    Vasicek vs CIR の path 比較
    \"\"\"
    
    r0 = 0.03
    T = 10.0
    n_steps = 100
    n_paths = 500
    
    # Vasicek
    paths_vasicek = vasicek_path_analytical(r0, a_param, b_param, sigma_param, T, n_steps, n_paths)
    
    # CIR
    paths_cir = cir_path_euler(r0, a_param, b_param, sigma_param, T, n_steps, n_paths)
    
    time_grid = np.linspace(0, T, n_steps + 1)
    feller_ok = feller_condition_check(a_param, b_param, sigma_param)
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle(f'Vasicek vs CIR: a={a_param:.2f}, b={b_param*100:.2f}%, σ={sigma_param*100:.2f}%',
                 fontsize=12, fontweight='bold')
    
    # Vasicek
    for i in range(min(100, n_paths)):
        axes[0].plot(time_grid, paths_vasicek[i, :] * 100, 'b-', alpha=0.1, linewidth=0.5)
    axes[0].plot(time_grid, np.mean(paths_vasicek, axis=0) * 100, 'b-', linewidth=2.5, label='Vasicek Mean')
    axes[0].axhline(b_param * 100, color='green', linestyle='--', linewidth=2, label='Long-term Mean')
    axes[0].set_xlabel('Time (years)', fontsize=10)
    axes[0].set_ylabel('Short Rate (%)', fontsize=10)
    axes[0].set_title('Vasicek Paths (Can go negative)', fontsize=11, fontweight='bold')
    axes[0].legend(fontsize=9)
    axes[0].grid(True, alpha=0.3)
    
    # CIR
    for i in range(min(100, n_paths)):
        axes[1].plot(time_grid, paths_cir[i, :] * 100, 'r-', alpha=0.1, linewidth=0.5)
    axes[1].plot(time_grid, np.mean(paths_cir, axis=0) * 100, 'r-', linewidth=2.5, label='CIR Mean')
    axes[1].axhline(b_param * 100, color='green', linestyle='--', linewidth=2, label='Long-term Mean')
    axes[1].axhline(0, color='black', linestyle='-', linewidth=1, alpha=0.5)
    axes[1].set_xlabel('Time (years)', fontsize=10)
    axes[1].set_ylabel('Short Rate (%)', fontsize=10)
    feller_str = "✓ Feller OK (Non-neg)" if feller_ok else "✗ Feller Violated"
    axes[1].set_title(f'CIR Paths (Always non-neg) - {feller_str}', fontsize=11, fontweight='bold')
    axes[1].legend(fontsize=9)
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()

interact(
    plot_vasicek_vs_cir,
    a_param=FloatSlider(min=0.01, max=1.0, step=0.05, value=0.15, description='a:'),
    b_param=FloatSlider(min=0.01, max=0.10, step=0.005, value=0.05, description='b (%):'),
    sigma_param=FloatSlider(min=0.001, max=0.05, step=0.005, value=0.02, description='σ (%):')
)
    """)
    )

    cells.append(
        md_cell("""
## 主な特徴

### 強み
- ✅ **非負性を保証**（Feller条件下で）
- ✅ 高い金利ほどボラティリティが大きい（現実的）
- ✅ 平均回帰＋レベル依存ボラ

### 弱み
- ❌ 計算が Vasicek より複雑
- ❌ 解析的結果が限定的
- ❌ パラメータ推定が難しい（Feller条件の制約）

### 使用場面
- 🏦 非負性が重要な場合
- 🏦 金利が低い環境での risk management
- 🏦 学術的応用
    """)
    )

    return cells


# =====================================================================
# CHAPTER 5: Hull-White 1 Factor
# =====================================================================


def create_ch5():
    cells = []

    cells.append(
        md_cell("""
# Chapter 5: Hull-White 1-Factor Model

## 概要

**Hull-White 1F Model** は Vasicek を拡張し、 **initial zero curve に自動フィット** させるモデルです。

### 特徴
- 時間依存のドリフト項 $\\theta(t)$
- 初期カーブへの正確なフィット
- 実務で最も使われる short-rate model
- Bermudan option や callable bond の価格付けに標準

## 基本式

$$dr_t = (\\theta(t) - a r_t)dt + \\sigma dW_t$$

**パラメータ:**
- $\\theta(t)$ = Time-dependent drift（初期カーブから計算）
- $a$ = Mean reversion speed
- $\\sigma$ = Constant volatility

## $\\theta(t)$ の決定

初期 zero curve と市場価格にフィットさせるために、 $\\theta(t)$ を自動計算します。

$$\\theta(t) = -\\frac{\\partial f^m(0,t)}{\\partial t} - a f^m(0,t) + \\sigma^2(1 - e^{-2at})/(2a)$$

ここで $f^m(0,t)$ は市場の instantaneous forward rate。
    """)
    )

    cells.append(
        code_cell("""
def hw1f_theta_calculation(market_zero_curve, T_array, a, sigma):
    \"\"\"
    Hull-White theta(t) を市場ゼロカーブから計算
    
    Standard formula (Hull-White 1990):
    θ(t) = ∂f(0,t)/∂t + a*f(0,t) + σ²/(2a) * (1 - e^(-2at))
    
    CORRECTED: Changed -df_dt and -a* to +df_dt and +a* (逆符号バグ fix)
    \"\"\"
    from scipy.interpolate import interp1d
    
    # Forward rate curve を計算
    f_curve = interp1d(T_array, market_zero_curve, kind='cubic', fill_value='extrapolate')
    
    # Derivative of forward rate
    dt = np.min(np.diff(T_array)) / 2
    df_dt = np.gradient(market_zero_curve, T_array)
    
    # theta(t) = +df/dt + a*f + sigma^2 * correction_term (FIXED: now +, not -)
    correction = sigma**2 * (1 - np.exp(-2 * a * T_array)) / (2 * a)
    theta = df_dt + a * market_zero_curve + correction
    
    return theta

def hw1f_path_euler(r0, a, sigma, theta_func, T, n_steps, n_paths=1000):
    \"\"\"
    Hull-White 1F を Euler で simulation
    \"\"\"
    dt = T / n_steps
    paths = np.zeros((n_paths, n_steps + 1))
    paths[:, 0] = r0
    
    for i in range(n_steps):
        t = i * dt
        theta_t = theta_func(t)
        
        dW = np.random.normal(0, np.sqrt(dt), n_paths)
        paths[:, i+1] = paths[:, i] + (theta_t - a * paths[:, i]) * dt + sigma * dW
    
    return paths

# テスト
T_array = np.linspace(0, 10, 50)
market_zero_curve = 0.02 + 0.03 * (1 - np.exp(-T_array / 5))

a_param = 0.1
sigma_param = 0.01

# theta(t) 計算
theta_array = hw1f_theta_calculation(market_zero_curve, T_array, a_param, sigma_param)

print("Hull-White theta(t) from market zero curve:")
print(f"Parameters: a={a_param}, σ={sigma_param*100:.2f}%")
print(f"\\ntheta(t) samples:")
for t, theta in zip(T_array[::5], theta_array[::5]):
    print(f"  t={t:4.1f}y: θ(t)={theta*100:7.4f}%")
    """)
    )

    cells.append(
        code_cell("""
# ===== Hull-White Path + Initial Curve Fit =====

from scipy.interpolate import interp1d

def plot_hw1f_analysis(a_param, sigma_pct):
    \"\"\"
    Hull-White simulation + initial curve fit
    \"\"\"
    
    r0 = 0.02
    T_array = np.linspace(0.01, 10, 50)
    market_zero_curve = 0.02 + 0.03 * (1 - np.exp(-T_array / 5))
    
    sigma_param = sigma_pct / 100
    
    # theta 計算
    theta_array = hw1f_theta_calculation(market_zero_curve, T_array, a_param, sigma_param)
    theta_func = interp1d(T_array, theta_array, kind='linear', fill_value='extrapolate')
    
    # Simulation
    T = 10.0
    n_steps = 100
    n_paths = 300
    
    paths = hw1f_path_euler(r0, a_param, sigma_param, theta_func, T, n_steps, n_paths)
    time_grid = np.linspace(0, T, n_steps + 1)
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle(f'Hull-White 1F: a={a_param:.2f}, σ={sigma_param*100:.2f}%',
                 fontsize=12, fontweight='bold')
    
    # Paths
    for i in range(min(100, n_paths)):
        axes[0].plot(time_grid, paths[i, :] * 100, 'b-', alpha=0.1, linewidth=0.5)
    axes[0].plot(time_grid, np.mean(paths, axis=0) * 100, 'r-', linewidth=2.5, label='Mean Path')
    axes[0].set_xlabel('Time (years)', fontsize=10)
    axes[0].set_ylabel('Short Rate (%)', fontsize=10)
    axes[0].set_title('HW1F Short Rate Paths', fontsize=11, fontweight='bold')
    axes[0].legend(fontsize=9)
    axes[0].grid(True, alpha=0.3)
    
    # theta(t) profile
    t_fine = np.linspace(0, T, 100)
    theta_fine = np.array([theta_func(t) for t in t_fine])
    
    axes[1].plot(T_array, market_zero_curve * 100, 'g-', linewidth=2, label='Market Zero Curve')
    ax2 = axes[1].twinx()
    ax2.plot(t_fine, theta_fine * 100, 'b-', linewidth=2, label='θ(t) drift')
    
    axes[1].set_xlabel('Time (years)', fontsize=10)
    axes[1].set_ylabel('Zero Rate (%)', fontsize=10, color='g')
    ax2.set_ylabel('θ(t) (%)', fontsize=10, color='b')
    axes[1].set_title('Initial Curve & HW Drift', fontsize=11, fontweight='bold')
    axes[1].tick_params(axis='y', labelcolor='g')
    ax2.tick_params(axis='y', labelcolor='b')
    axes[1].grid(True, alpha=0.3)
    
    # Legend
    lines1, labels1 = axes[1].get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    axes[1].legend(lines1 + lines2, labels1 + labels2, fontsize=9)
    
    plt.tight_layout()
    plt.show()

interact(
    plot_hw1f_analysis,
    a_param=FloatSlider(min=0.01, max=1.0, step=0.05, value=0.1, description='a:'),
    sigma_pct=FloatSlider(min=0.1, max=5, step=0.2, value=1, description='σ (%):')
)
    """)
    )

    cells.append(
        md_cell("""
## 主な特徴

### 強み
- ✅ **初期カーブに正確フィット**
- ✅ 実務で最も使われている（標準モデル）
- ✅ Bond option / Callable product の価格付けに最適
- ✅ 解析的結果が多い

### 弱み
- ❌ 単一ファクター → Curve形状の自由度が限定的
- ❌ マイナス金利を許す（負のレートが可能）
- ❌ Smile/Skew を表現できない

### 使用場面
- 🏦 **標準的な金利デリバティブ価格付け**
- 🏦 構造化商品（Callable bond, Bermudan等）
- 🏦 金利リスク管理・シナリオ分析
    """)
    )

    return cells


# =====================================================================
# CHAPTER 6: G2++ Model
# =====================================================================


def create_ch6():
    cells = []

    cells.append(
        md_cell("""
# Chapter 6: G2++ (Two-Factor Gaussian) Model

## 概要

**G2++ Model** は、Hull-White を **2ファクター** に拡張したモデルです。

曲線の **レベル** と **スロープ** の変動を独立に表現できます。

## 基本式

$$r_t = x_t + y_t + \\phi(t)$$

$$dx_t = -a x_t dt + \\sigma dW_t^{(1)}$$

$$dy_t = -b y_t dt + \\eta dW_t^{(2)}$$

$$dW_t^{(1)} dW_t^{(2)} = \\rho dt$$

**パラメータ:**
- $a, b$ = Mean reversion speeds (fast factor, slow factor)
- $\\sigma, \\eta$ = Volatilities
- $\\rho$ = Correlation between factors
- $\\phi(t)$ = Deterministic term (initial curve fit)
    """)
    )

    cells.append(
        code_cell("""
def g2pp_path_euler(x0, y0, a, b, sigma, eta, rho, phi_func, T, n_steps, n_paths=1000):
    \"\"\"
    G2++ two-factor model simulation
    
    r_t = x_t + y_t + phi(t)
    dx_t = -a*x_t*dt + sigma*dW1
    dy_t = -b*y_t*dt + eta*dW2
    
    CORRECTED:
    - Initialize r_paths[:, 0] = x0 + y0 + phi(0)
    - Use phi(t_next) when updating r at t_next
    \"\"\"
    dt = T / n_steps
    
    x_paths = np.zeros((n_paths, n_steps + 1))
    y_paths = np.zeros((n_paths, n_steps + 1))
    r_paths = np.zeros((n_paths, n_steps + 1))
    
    x_paths[:, 0] = x0
    y_paths[:, 0] = y0
    r_paths[:, 0] = x0 + y0 + phi_func(0)  # FIXED: initialize r_0 properly
    
    for i in range(n_steps):
        t_curr = i * dt
        t_next = (i + 1) * dt
        
        # Correlated Brownian increments
        dW1 = np.random.normal(0, np.sqrt(dt), n_paths)
        dZ = np.random.normal(0, np.sqrt(dt), n_paths)
        dW2 = rho * dW1 + np.sqrt(1 - rho**2) * dZ
        
        # Update x, y
        x_paths[:, i+1] = x_paths[:, i] - a * x_paths[:, i] * dt + sigma * dW1
        y_paths[:, i+1] = y_paths[:, i] - b * y_paths[:, i] * dt + eta * dW2
        
        # Update r with phi at t_next (FIXED: was phi_func(t) instead of phi_func(t_next))
        phi_next = phi_func(t_next)
        r_paths[:, i+1] = x_paths[:, i+1] + y_paths[:, i+1] + phi_next
    
    return x_paths, y_paths, r_paths

# Test
def constant_phi(t):
    return 0.02

x0, y0 = 0, 0
a, b = 0.1, 0.03
sigma, eta = 0.01, 0.005
rho = 0.5
T = 10.0
n_steps = 100
n_paths = 500

x_paths, y_paths, r_paths = g2pp_path_euler(x0, y0, a, b, sigma, eta, rho, constant_phi, T, n_steps, n_paths)
time_grid = np.linspace(0, T, n_steps + 1)

print("G2++ Simulation:")
print(f"Parameters: a={a}, b={b}, σ={sigma*100:.2f}%, η={eta*100:.2f}%, ρ={rho}")
print(f"Terminal r_t distribution:")
print(f"  Mean: {np.mean(r_paths[:, -1])*100:.4f}%")
print(f"  Std: {np.std(r_paths[:, -1])*100:.4f}%")
    """)
    )

    cells.append(
        code_cell("""
# ===== G2++ Interactive: 相関ρの効果を可視化 =====

from ipywidgets import FloatSlider, interact

def plot_g2pp_analysis(rho_param, a_param, b_param):
    \"\"\"
    G2++ two factors の動きを可視化
    相関を変えるとどう変わるか
    \"\"\"
    
    sigma_param = 0.01
    eta_param = 0.005
    T = 10.0
    n_steps = 100
    n_paths = 300
    
    x_paths, y_paths, r_paths = g2pp_path_euler(
        0, 0, a_param, b_param, sigma_param, eta_param, rho_param, 
        constant_phi, T, n_steps, n_paths
    )
    time_grid = np.linspace(0, T, n_steps + 1)
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    fig.suptitle(f'G2++: a={a_param:.2f}, b={b_param:.2f}, σ={sigma_param*100:.1f}%, η={eta_param*100:.1f}%, ρ={rho_param:.2f}',
                 fontsize=12, fontweight='bold')
    
    # Panel 1: x factor (fast)
    for i in range(min(50, n_paths)):
        axes[0, 0].plot(time_grid, x_paths[i, :] * 100, 'b-', alpha=0.2, linewidth=0.5)
    axes[0, 0].plot(time_grid, np.mean(x_paths, axis=0) * 100, 'b-', linewidth=2, label='Mean x_t')
    axes[0, 0].axhline(0, color='k', linestyle='-', alpha=0.3)
    axes[0, 0].set_ylabel('x_t (%)', fontsize=10)
    axes[0, 0].set_title('Factor 1 (Fast): x_t', fontsize=11, fontweight='bold')
    axes[0, 0].legend(fontsize=9)
    axes[0, 0].grid(True, alpha=0.3)
    
    # Panel 2: y factor (slow)
    for i in range(min(50, n_paths)):
        axes[0, 1].plot(time_grid, y_paths[i, :] * 100, 'g-', alpha=0.2, linewidth=0.5)
    axes[0, 1].plot(time_grid, np.mean(y_paths, axis=0) * 100, 'g-', linewidth=2, label='Mean y_t')
    axes[0, 1].axhline(0, color='k', linestyle='-', alpha=0.3)
    axes[0, 1].set_ylabel('y_t (%)', fontsize=10)
    axes[0, 1].set_title('Factor 2 (Slow): y_t', fontsize=11, fontweight='bold')
    axes[0, 1].legend(fontsize=9)
    axes[0, 1].grid(True, alpha=0.3)
    
    # Panel 3: Total r_t
    for i in range(min(50, n_paths)):
        axes[1, 0].plot(time_grid, r_paths[i, :] * 100, 'r-', alpha=0.2, linewidth=0.5)
    axes[1, 0].plot(time_grid, np.mean(r_paths, axis=0) * 100, 'r-', linewidth=2, label='Mean r_t = x_t + y_t')
    axes[1, 0].axhline(0.02*100, color='k', linestyle='--', alpha=0.5, label='φ(t) = 2%')
    axes[1, 0].set_xlabel('Time (years)', fontsize=10)
    axes[1, 0].set_ylabel('r_t (%)', fontsize=10)
    axes[1, 0].set_title('Total Short Rate: r_t = x_t + y_t + φ(t)', fontsize=11, fontweight='bold')
    axes[1, 0].legend(fontsize=9)
    axes[1, 0].grid(True, alpha=0.3)
    
    # Panel 4: Terminal distribution
    axes[1, 1].hist(r_paths[:, -1] * 100, bins=40, density=True, alpha=0.7, 
                    color='skyblue', edgecolor='black', label='Empirical')
    
    from scipy.stats import norm as sp_norm
    mean_term = np.mean(r_paths[:, -1])
    std_term = np.std(r_paths[:, -1])
    x_range = np.linspace(mean_term - 4*std_term, mean_term + 4*std_term, 200)
    axes[1, 1].plot(x_range * 100, sp_norm.pdf(x_range, mean_term, std_term), 
                    'r-', linewidth=2, label='Normal fit')
    
    axes[1, 1].set_xlabel('r_T (%)', fontsize=10)
    axes[1, 1].set_ylabel('Density', fontsize=10)
    axes[1, 1].set_title('Terminal r_T Distribution', fontsize=11, fontweight='bold')
    axes[1, 1].legend(fontsize=9)
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()

interact(
    plot_g2pp_analysis,
    rho_param=FloatSlider(min=-0.9, max=0.9, step=0.1, value=0.5, description='ρ (correlation):'),
    a_param=FloatSlider(min=0.01, max=0.5, step=0.05, value=0.1, description='a (fast):'),
    b_param=FloatSlider(min=0.001, max=0.1, step=0.01, value=0.03, description='b (slow):')
)

print("✓ Adjust ρ to see factor correlation effect")
    """)
    )

    cells.append(
        md_cell("""
## 主な特徴

### 強み
- ✅ **2ファクター** → 曲線のレベル・スロープを独立に表現
- ✅ Bermudan swaption など複雑な商品の価格付けに有力
- ✅ Hull-White 1F より柔軟
- ✅ 解析的結果が利用可能

### 弱み
- ❌ パラメータが6個（a, b, σ, η, ρ, φ(t)）で複雑
- ❌ キャリブレーションの計算量が大きい
- ❌ Smile/Skew を表現できない

### 使用場面
- 🏦 複雑なswaption / Bermudan option
- 🏦 Curve変形が重要な商品
- 🏦 マルチカーブ環境
    """)
    )

    return cells


# =====================================================================
# Assemble Notebook (Part 2)
# =====================================================================

if __name__ == "__main__":
    nb = nbf.v4.new_notebook()

    cells = []

    # Add chapters
    cells.extend(create_ch3())
    cells.extend(create_ch4())
    cells.extend(create_ch5())
    cells.extend(create_ch6())

    nb.cells = cells

    # Save
    output_path = (
        "/home/kazumasa/projects/rates_volatility_model/rates_volatility_models_part2.ipynb"
    )
    with open(output_path, "w") as f:
        nbf.write(nb, f)

    print(f"✓ Generated: {output_path}")
    print(f"  Total cells: {len(cells)}")
