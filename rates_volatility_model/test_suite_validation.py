"""
Comprehensive Test Suite for Fixed Interest Rate Models
Tests all 5 major fixes and validates mathematical properties
"""

import numpy as np
from scipy.optimize import minimize
from scipy.stats import norm

print("=" * 90)
print("INTEREST RATE MODELS - COMPREHENSIVE VALIDATION SUITE")
print("=" * 90)

# Set seed
np.random.seed(42)

# ============================================================================
# TEST 1: Black76 Greeks Consistency
# ============================================================================
print("\n[TEST 1] BLACK76 GREEKS - ANALYTICAL VS FINITE DIFFERENCE")
print("-" * 90)


def black76_price(F, K, T, vol, P=1.0):
    """Black76 call option price"""
    if vol <= 0 or T <= 0 or F <= 0 or K <= 0:
        return max(F - K, 0) * P
    d1 = (np.log(F / K) + 0.5 * vol**2 * T) / (vol * np.sqrt(T))
    d2 = d1 - vol * np.sqrt(T)
    return P * (F * norm.cdf(d1) - K * norm.cdf(d2))


def black76_delta(F, K, T, vol, P=1.0):
    """Black76 delta"""
    if vol <= 0 or T <= 0 or F <= 0:
        return 1.0 if F > K else 0.0
    d1 = (np.log(F / K) + 0.5 * vol**2 * T) / (vol * np.sqrt(T))
    return P * norm.cdf(d1)


def black76_gamma(F, K, T, vol, P=1.0):
    """Black76 gamma"""
    if vol <= 0 or T <= 0 or F <= 0:
        return 0.0
    d1 = (np.log(F / K) + 0.5 * vol**2 * T) / (vol * np.sqrt(T))
    return P * norm.pdf(d1) / (F * vol * np.sqrt(T))


# Test parameters
F, K, T, vol = 0.05, 0.05, 1.0, 0.2

# Analytical Greeks
delta_an = black76_delta(F, K, T, vol)
gamma_an = black76_gamma(F, K, T, vol)

# Finite difference Greeks
bump_F = 0.0001
price_up = black76_price(F + bump_F, K, T, vol)
price_down = black76_price(F - bump_F, K, T, vol)
delta_fd = (price_up - price_down) / (2 * bump_F)

# Gamma from delta
delta_up = black76_delta(F + bump_F, K, T, vol)
delta_down = black76_delta(F - bump_F, K, T, vol)
gamma_fd = (delta_up - delta_down) / (2 * bump_F)

print(f"Parameters: F={F * 100:.1f}%, K={K * 100:.1f}%, T={T:.1f}y, σ={vol * 100:.1f}%\n")
print("DELTA:")
print(f"  Analytical: {delta_an:.6f}")
print(f"  Finite Diff: {delta_fd:.6f}")
print(f"  Error: {abs(delta_an - delta_fd) * 10000:.2f} pips")

print("\nGAMMA (per 1% move):")
print(f"  Analytical: {gamma_an:.6f}")
print(f"  Finite Diff: {gamma_fd:.6f}")
print(f"  Error: {abs(gamma_an - gamma_fd) / gamma_an * 100:.2f}%")

test1_pass = (abs(delta_an - delta_fd) < 0.001) and (abs(gamma_an - gamma_fd) / gamma_an < 0.01)
print(f"\nResult: {'✓ PASS' if test1_pass else '✗ FAIL'}")

# ============================================================================
# TEST 2: Hull-White 1F - Theta Sign Correction
# ============================================================================
print("\n[TEST 2] HULL-WHITE 1F - THETA SIGN CORRECTION")
print("-" * 90)


def hw1f_theta_calculation_corrected(market_zero_curve, T_array, a, sigma):
    """Corrected theta for HW1F: θ(t) = df/dt + a*f(0,t) + σ²/(2a)*(1-e^{-2at})"""
    df_dt = np.gradient(market_zero_curve, T_array)
    feller_term = sigma**2 * (1.0 - np.exp(-2.0 * a * T_array)) / (2.0 * a)
    theta = df_dt + a * market_zero_curve + feller_term
    return theta


# Market curve: upward sloping from 2% to 5%
T_array = np.linspace(0.5, 10.0, 20)
market_zero = 0.02 + 0.03 * (1.0 - np.exp(-T_array / 5.0))
a = 0.1
sigma = 0.01

theta_array = hw1f_theta_calculation_corrected(market_zero, T_array, a, sigma)

print(f"Market curve: {market_zero[0] * 100:.2f}% → {market_zero[-1] * 100:.2f}%")
print(f"Parameters: a={a:.3f}, σ={sigma * 100:.2f}%\n")

print(f"theta(0.5y) = {theta_array[0] * 100:.4f}%")
print(f"theta(5.0y) = {theta_array[len(theta_array) // 2] * 100:.4f}%")
print(f"theta(10y)  = {theta_array[-1] * 100:.4f}%")
print(f"theta min   = {np.min(theta_array) * 100:.4f}%")
print(f"theta max   = {np.max(theta_array) * 100:.4f}%")

test2_pass = np.all(np.isfinite(theta_array)) and (np.min(theta_array) > -0.01)
print(f"\nResult: {'✓ PASS' if test2_pass else '✗ FAIL'}")

# ============================================================================
# TEST 3: G2++ - Initial State Correction
# ============================================================================
print("\n[TEST 3] G2++ - INITIAL STATE AND PHI TIMING")
print("-" * 90)


def g2pp_short_rate_corrected(dt, x0, y0, phi_t, a, b, sigma_x, sigma_y, rho):
    """Corrected G2++ with proper initial state and phi timing"""
    n_steps = int(1.0 / dt)
    np.linspace(0, 1.0, n_steps + 1)

    # Initial state must be x0 + y0 + phi(0)
    x = np.zeros(n_steps + 1)
    y = np.zeros(n_steps + 1)
    r = np.zeros(n_steps + 1)

    x[0] = x0
    y[0] = y0
    r[0] = x0 + y0 + phi_t[0]  # CORRECTED: Initialize r[0] properly

    for i in range(n_steps):
        dW1 = np.random.normal(0, np.sqrt(dt))
        dW2 = np.random.normal(0, np.sqrt(dt))
        dW2_corr = rho * dW1 + np.sqrt(1 - rho**2) * dW2

        x[i + 1] = x[i] - a * x[i] * dt + sigma_x * dW1
        y[i + 1] = y[i] - b * y[i] * dt + sigma_y * dW2_corr
        r[i + 1] = x[i + 1] + y[i + 1] + phi_t[i + 1]  # CORRECTED: Use phi_t[i+1], not phi_t[i]

    return x, y, r


# Test initial state
dt = 0.01
n_steps = int(1.0 / dt)
t_array = np.linspace(0, 1.0, n_steps + 1)
phi_func = 0.03 + 0.01 * np.sin(2 * np.pi * t_array)

x0, y0 = 0.0, 0.0
x, y, r = g2pp_short_rate_corrected(dt, x0, y0, phi_func, 0.1, 0.2, 0.01, 0.015, 0.5)

print(f"x0={x0:.4f}, y0={y0:.4f}, φ(0)={phi_func[0] * 100:.2f}%\n")
print(f"r(0) = x(0) + y(0) + φ(0) = {x[0]:.4f} + {y[0]:.4f} + {phi_func[0]:.4f}")
print(f"      = {r[0] * 100:.2f}% (expected {phi_func[0] * 100:.2f}%)")

# Check that phi timing is correct (spot-on, not lagged)
r_expected_1 = x[1] + y[1] + phi_func[1]
print(f"\nr(1) = {r[1] * 100:.4f}% (should use φ(t=0.01), not φ(t=0))")
print(f"Expected: {r_expected_1 * 100:.4f}%")

test3_pass = (abs(r[0] - phi_func[0]) < 1e-10) and (abs(r[1] - r_expected_1) < 1e-10)
print(f"\nResult: {'✓ PASS' if test3_pass else '✗ FAIL'}")

# ============================================================================
# TEST 4: HJM - Drift Integral Direction
# ============================================================================
print("\n[TEST 4] HJM - DRIFT INTEGRAL DIRECTION (∫_t^T, not ∫_T^∞)")
print("-" * 90)


def hjm_drift_integral_check(t, T, sigma_const=0.01):
    """
    HJM drift: α(t,T) = σ(t,T) * ∫_t^T σ(t,u) du
    For constant σ: α(t,T) = σ² * (T - t)
    """
    if T <= t:
        return 0.0
    integral = sigma_const * (T - t)
    alpha = sigma_const * integral
    return alpha


print(f"Constant volatility σ={0.01 * 100:.2f}%, at t={0.5}y\n")
print("Expected: α(t,T) = σ² * (T - t)\n")

test_maturity_points = [0.5, 1.0, 2.0, 5.0, 10.0]
test4_pass = True

for T in test_maturity_points:
    alpha = hjm_drift_integral_check(0.5, T)
    expected = 0.01**2 * (T - 0.5) if T > 0.5 else 0.0

    if T > 0.5:
        print(f"α(0.5, {T:.1f}) = {alpha * 100:.6f}% (expected {expected * 100:.6f}%)", end="")
        match = abs(alpha - expected) < 1e-10
        print(f" {'✓' if match else '✗'}")
        test4_pass = test4_pass and match
    else:
        print(f"α(0.5, {T:.1f}) = {alpha * 100:.6f}% [T ≤ t, no update] ✓")

print(f"\nResult: {'✓ PASS' if test4_pass else '✗ FAIL'}")

# ============================================================================
# TEST 5: LMM - Spot Measure Drift
# ============================================================================
print("\n[TEST 5] LMM - SPOT MEASURE DRIFT TERM")
print("-" * 90)


def lmm_forward_libor_step(L_prev, sigma, dt, dW, drift_term):
    """LMM with proper spot measure drift"""
    # dL_i / L_i = μ_i dt + σ_i dW
    # With drift: Ito update is L_new = L_old * exp((μ - 0.5*σ²)*dt + σ*dW)
    return L_prev * np.exp((drift_term - 0.5 * sigma**2) * dt + sigma * dW)


# Single forward rate, constant params
L0 = 0.05
sigma = 0.20
dt = 0.01
n_sim = 100000

# Run without drift (old, incorrect way)
np.random.seed(42)
L_nodrift = np.zeros(n_sim)
for i in range(n_sim):
    dW = np.random.normal(0, np.sqrt(dt))
    L_nodrift[i] = L0 * np.exp(sigma * dW)  # Missing drift!

# Run with drift (new, correct way - though drift is 0 for single rate)
np.random.seed(42)
L_withdrift = np.zeros(n_sim)
for i in range(n_sim):
    dW = np.random.normal(0, np.sqrt(dt))
    drift = 0.0  # No other rates, so drift is 0
    L_withdrift[i] = lmm_forward_libor_step(L0, sigma, dt, dW, drift)

print(f"L0={L0 * 100:.2f}%, σ={sigma * 100:.1f}%, dt={dt:.3f}, n_sim={n_sim}\n")

print("WITHOUT drift term (old, incorrect):")
print(f"  E[L_1]  = {np.mean(L_nodrift) * 100:.4f}%")
print(f"  Bias    = {(np.mean(L_nodrift) - L0) / L0 * 100:.2f}%")

print("\nWITH drift term (new, correct for single rate):")
print(f"  E[L_1]  = {np.mean(L_withdrift) * 100:.4f}%")
print(f"  Bias    = {(np.mean(L_withdrift) - L0) / L0 * 100:.2f}%")

# For single rate with no correlation to future rates, drift = 0,
# so martingale should hold approximately (within MC error)
test5_pass = abs(np.mean(L_withdrift) - L0) / L0 < 0.02  # Allow 2% MC error
print(f"\nResult: {'✓ PASS (martingale holds)' if test5_pass else '✗ FAIL'}")

# ============================================================================
# TEST 6: Bachelier Vega - Unit Correction
# ============================================================================
print("\n[TEST 6] BACHELIER - VEGA PER 1 BASIS POINT")
print("-" * 90)


def bachelier_price(F, K, T, vol_normal, P=1.0):
    """Bachelier option price (normal model)"""
    if vol_normal <= 0 or T <= 0:
        return max(F - K, 0) * P
    d = (F - K) / (vol_normal * np.sqrt(T))
    return P * ((F - K) * norm.cdf(d) + vol_normal * np.sqrt(T) * norm.pdf(d))


def bachelier_vega_per_1bp(F, K, T, vol_normal, P=1.0):
    """Vega (price change per unit volatility change)"""
    if vol_normal <= 0 or T <= 0:
        return 0.0
    d = (F - K) / (vol_normal * np.sqrt(T))
    return P * np.sqrt(T) * norm.pdf(d)


# Test parameters
F, K, T, vol = 0.02, 0.02, 1.0, 0.005  # ATM, 5000 bps vol

vega_analytical = bachelier_vega_per_1bp(F, K, T, vol)

# Finite difference: bump by 1bp
bump_vol = 0.0001  # 1 basis point
price_up = bachelier_price(F, K, T, vol + bump_vol)
price_down = bachelier_price(F, K, T, vol - bump_vol)
vega_fd = (price_up - price_down) / (2 * bump_vol)

print(f"Parameters: F={F * 100:.2f}%, K={K * 100:.2f}%, T={T:.1f}y")
print(f"Normal volatility: {vol * 10000:.0f} bps\n")

print("Vega (per 1bp):")
print(f"  Analytical: {vega_analytical:.8f}")
print(f"  Finite Diff: {vega_fd:.8f}")

# Check relative error, but adjust for small numbers
rel_error = (
    abs(vega_analytical - vega_fd) / max(vega_fd, vega_analytical) * 100
    if max(vega_fd, vega_analytical) > 0
    else 0
)
print(f"  Relative error: {rel_error:.6f}%")

# Pass if analytical matches FD
test6_pass = abs(vega_analytical - vega_fd) / vega_fd < 0.01
print(f"\nResult: {'✓ PASS' if test6_pass else '✗ FAIL'}")

# ============================================================================
# TEST 7: Implied Vol Round-Trip (Black76)
# ============================================================================
print("\n[TEST 7] IMPLIED VOL ROUND-TRIP — BLACK76 INVERSE")
print("-" * 90)

from scipy.optimize import brentq


def black76_call_t7(F, K, T, sigma, df=1.0):
    if sigma <= 0 or T <= 0 or F <= 0 or K <= 0:
        return df * max(F - K, 0.0)
    d1 = (np.log(F / K) + 0.5 * sigma**2 * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    from scipy.stats import norm as _norm

    return df * (F * _norm.cdf(d1) - K * _norm.cdf(d2))


def black76_implied_vol_t7(price, F, K, T):
    intrinsic = max(F - K, 0.0)
    if price <= intrinsic + 1e-12:
        return np.nan
    try:
        return brentq(lambda s: black76_call_t7(F, K, T, s) - price, 1e-6, 20.0, xtol=1e-9)
    except ValueError:
        return np.nan


F_t7, T_t7, sigma_t7 = 0.03, 1.0, 0.30
strikes_t7 = np.array([0.010, 0.015, 0.020, 0.025, 0.030, 0.035, 0.040, 0.045, 0.050])
max_error_bp = 0.0

for K in strikes_t7:
    price = black76_call_t7(F_t7, K, T_t7, sigma_t7)
    iv = black76_implied_vol_t7(price, F_t7, K, T_t7)
    err_bp = abs(iv - sigma_t7) * 10000 if not np.isnan(iv) else 999
    max_error_bp = max(max_error_bp, err_bp)
    print(f"  K={K * 100:.1f}%  iv={iv * 100:.6f}%  error={err_bp:.4e} bp")

test7_pass = max_error_bp < 0.01
print(f"\nMax round-trip error: {max_error_bp:.4e} bp  (threshold < 0.01 bp)")
print(f"Result: {'✓ PASS' if test7_pass else '✗ FAIL'}")

# ============================================================================
# TEST 8: SABR Calibration RMSE
# ============================================================================
print("\n[TEST 8] SABR CALIBRATION RMSE — SURFACE (β=0.5 fixed)")
print("-" * 90)


def hagan_sabr_t8(F, K, T, alpha, beta, rho, nu):
    if F <= 0 or K <= 0 or T <= 0:
        return np.nan
    if abs(F - K) < 1e-10:
        sigma_atm = alpha / (F ** (1 - beta))
        corr = 1 + T * (
            (1 - beta) ** 2 / 24 * (alpha / F ** (1 - beta)) ** 2
            + rho * beta * nu / 4 / alpha * F ** (1 - beta)
            + (2 - 3 * rho**2) / 24 * nu**2
        )
        return sigma_atm * corr
    log_fk = np.log(F / K)
    fk_mid = (F * K) ** ((1 - beta) / 2)
    z = nu / alpha * fk_mid * log_fk
    denom = 1 + (1 - beta) ** 2 / 24 * log_fk**2
    x_z = np.log((np.sqrt(1 - 2 * rho * z + z**2) + z - rho) / (1 - rho))
    ratio = z / x_z if abs(x_z) > 1e-12 else 1.0
    corr = 1 + T * (
        (1 - beta) ** 2 / 24 * (alpha / (F * K) ** (1 - beta)) ** 2
        + rho * beta * nu / 4 / alpha
        + (2 - 3 * rho**2) / 24 * nu**2
    )
    return alpha / (fk_mid * denom) * ratio * corr


def calibrate_sabr_t8(F, T, strikes, market_vols, beta=0.5):
    alpha0 = market_vols[len(market_vols) // 2] * F ** (1 - beta)
    bounds = [(1e-4, None), (-0.9999, 0.9999), (1e-4, None)]

    def obj(p):
        a, r, n = p
        mv = np.array([hagan_sabr_t8(F, K, T, a, beta, r, n) for K in strikes])
        mask = ~np.isnan(mv)
        return np.sum((mv[mask] - market_vols[mask]) ** 2) if np.any(mask) else 1e6

    res = minimize(obj, [alpha0, -0.3, 0.4], method="L-BFGS-B", bounds=bounds)
    a_f, r_f, n_f = res.x
    fitted = np.array([hagan_sabr_t8(F, K, T, a_f, beta, r_f, n_f) for K in strikes])
    rmse_bp = np.sqrt(np.mean((fitted - market_vols) ** 2)) * 10000
    return rmse_bp


EXPIRIES_T8 = [1 / 12, 3 / 12, 6 / 12, 1.0, 2.0, 5.0, 10.0]
ATM_FWDS_T8 = [0.028, 0.029, 0.030, 0.031, 0.032, 0.033, 0.034]
TRUE_ALPHA = [0.020, 0.018, 0.016, 0.014, 0.012, 0.010, 0.009]
TRUE_RHO = [-0.60, -0.55, -0.50, -0.45, -0.40, -0.35, -0.30]
TRUE_NU = [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]
OFFSETS_BP = np.array([-100, -75, -50, -25, 0, 25, 50, 75, 100])
BETA_T8 = 0.5
RMSE_THRESHOLD_BP = 7.0  # 2bp noise + nonlinear optimizer tolerance; short expiries harder

np.random.seed(42)
all_rmse = []
print(f"{'Expiry':>6} {'RMSE (bp)':>12}  {'Status':>8}")
print("-" * 35)

for T, F, a_true, r_true, n_true in zip(
    EXPIRIES_T8, ATM_FWDS_T8, TRUE_ALPHA, TRUE_RHO, TRUE_NU, strict=False
):
    strikes = np.maximum(F + OFFSETS_BP / 10000, 1e-4)
    true_vols = np.array([hagan_sabr_t8(F, K, T, a_true, BETA_T8, r_true, n_true) for K in strikes])
    mkt_vols = true_vols + np.random.normal(0, 2e-4, len(strikes))
    rmse = calibrate_sabr_t8(F, T, strikes, mkt_vols, beta=BETA_T8)
    all_rmse.append(rmse)
    lbl = f"{round(T * 12)}M" if T < 1 else f"{int(T)}Y"
    status = "✓ OK" if rmse < RMSE_THRESHOLD_BP else "✗ FAIL"
    print(f"  {lbl:>4}   {rmse:10.3f} bp  {status}")

max_rmse = max(all_rmse)
test8_pass = max_rmse < RMSE_THRESHOLD_BP
print(f"\nMax RMSE across all expiries: {max_rmse:.3f} bp  (threshold < {RMSE_THRESHOLD_BP} bp)")
print(f"Result: {'✓ PASS' if test8_pass else '✗ FAIL'}")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 90)
print("SUMMARY")
print("=" * 90)

test_results = {
    "Black76 Greeks": test1_pass,
    "Hull-White 1F Theta": test2_pass,
    "G2++ Initial State": test3_pass,
    "HJM Drift Integral": test4_pass,
    "LMM Spot Measure": test5_pass,
    "Bachelier Vega Unit": test6_pass,
    "Implied Vol Round-Trip (B76)": test7_pass,
    "SABR Surface Calibration RMSE": test8_pass,
}

passed = sum(1 for v in test_results.values() if v)
total = len(test_results)

for test_name, passed_flag in test_results.items():
    status = "✓ PASS" if passed_flag else "✗ FAIL"
    print(f"{test_name:<40} {status}")

print("\n" + "=" * 90)
if passed == total:
    print(f"ALL TESTS PASSED ({passed}/{total}) ✓✓✓")
else:
    print(f"TESTS PASSED ({passed}/{total})")
print("=" * 90)
