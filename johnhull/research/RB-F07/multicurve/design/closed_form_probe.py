import numpy as np
from scipy.optimize import brentq

N = 1e7
q = np.array([0.03, 0.035, 0.04, 0.045])


def price(x):
    d1, d2, p1, p2 = x
    D1 = 1 / (1 + d1)
    D2 = (1 - d2 * D1) / (1 + d2)
    f2 = p2 + (D1 / D2) * (p2 - p1)
    P1 = 1 / (1 + p1)
    P2 = P1 / (1 + f2)
    D15 = np.sqrt(D1 * D2)
    f15 = (np.sqrt(P1 / P2) - 1) / 0.5
    return N * ((0.042 - p1) * D1 + 0.5 * (0.042 - f15) * D15) - 3e6 * D15


def grad(x):
    return np.array(
        [price(x.astype(complex) + 1e-24j * np.eye(4)[j]).imag / 1e-24 for j in range(4)]
    )


G = grad(q)
h = 1e-5
H = np.column_stack(
    [(grad(q + h * np.eye(4)[j]) - grad(q - h * np.eye(4)[j])) / (2 * h) for j in range(4)]
)
print("PV", price(q), "quote_per_bp", G * 1e-4, "H_asym", np.max(np.abs(H - H.T)))
print("cross_gamma_per_bp_squared", H[:2, 2:] * 1e-8)
v = np.array([1.0, -0.7, 0.8, -0.6]) * 1e-4
for a in [8.0, 4.0, 2.0, 1.0, 0.5]:
    move = a * v
    full = price(q + move) - price(q)
    print(a, full, full - G @ move, full - G @ move - 0.5 * move @ H @ move)
theta = brentq(lambda t: 2 * t**3 + t - 1, 0, 1, xtol=1e-15)
J = np.array([1.0, 2 * theta])
print("LS_theta", theta, "exact", J / (1 + 6 * theta**2), "wrong_GN", J / (J @ J))
