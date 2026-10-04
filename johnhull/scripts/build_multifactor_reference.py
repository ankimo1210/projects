"""Independent mathematics for Hull GE section 28.5.
No hullkit imports. Synthetic inputs, no printed pins.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.integrate import quad

PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / "docs/validation/section-28-5/reference.json"
F0, G0, K, RATE, HORIZON = 100.0, 80.0, 105.0, 0.04, 1.5
N_PATHS = 262144
SQRT_2PI = math.sqrt(2.0 * math.pi)


def phi(z):
    return math.exp(-0.5 * z * z) / SQRT_2PI


def bilinear(left, corr, right):
    return math.fsum(
        float(left[i]) * float(corr[i, j]) * float(right[j])
        for i in range(len(left))
        for j in range(len(right))
    )


def moment(mean, var):
    return math.exp(mean + 0.5 * var)


def integrate_split(fun, kink=None):
    if kink is None or not -12.0 < kink < 12.0:
        return quad(fun, -12.0, 12.0, epsabs=1e-11, epsrel=2e-12, limit=200)[0]
    return math.fsum(
        (
            quad(fun, -12.0, kink, epsabs=1e-11, epsrel=2e-12)[0],
            quad(fun, kink, 12.0, epsabs=1e-11, epsrel=2e-12)[0],
        )
    )


def tilted_tail(coefficient, cutoff=12.0):
    return (
        math.exp(0.5 * coefficient**2)
        * 0.5
        * (
            math.erfc((cutoff + coefficient) / math.sqrt(2))
            + math.erfc((cutoff - coefficient) / math.sqrt(2))
        )
    )


def price_quadratures(sf, sg, corr):
    vf = bilinear(sf, corr, sf)
    vg = bilinear(sg, corr, sg)
    cov = bilinear(sf, corr, sg)
    sigma = math.sqrt(max(vf, 0.0))
    mean_f_q = (RATE - 0.5 * vf) * HORIZON
    mean_f_g = (RATE + cov - 0.5 * vf) * HORIZON
    mean_g_g = (RATE + 0.5 * vg) * HORIZON
    if sigma == 0.0:
        q_price = math.exp(-RATE * HORIZON) * max(F0 * math.exp(RATE * HORIZON) - K, 0.0)
        g_price = (
            G0 * max(F0 * math.exp(RATE * HORIZON) - K, 0.0) / G0 * moment(-mean_g_g, vg * HORIZON)
        )
    else:
        beta = cov / sigma
        gamma2 = max(vg - beta * beta, 0.0)
        q_kink = (math.log(K / F0) - mean_f_q) / (sigma * math.sqrt(HORIZON))
        g_kink = (math.log(K / F0) - mean_f_g) / (sigma * math.sqrt(HORIZON))
        q_price = math.exp(-RATE * HORIZON) * integrate_split(
            lambda z: (
                max(F0 * math.exp(mean_f_q + sigma * math.sqrt(HORIZON) * z) - K, 0.0) * phi(z)
            ),
            q_kink,
        )
        # Under g, integrate independent g-only normal analytically, then f normal by scipy quad.
        g_price = math.exp(-mean_g_g + 0.5 * gamma2 * HORIZON) * integrate_split(
            lambda z: (
                max(F0 * math.exp(mean_f_g + sigma * math.sqrt(HORIZON) * z) - K, 0.0)
                * math.exp(-beta * math.sqrt(HORIZON) * z)
                * phi(z)
            ),
            g_kink,
        )
    q_tail_bound = (
        F0 * math.exp(mean_f_q - RATE * HORIZON) * tilted_tail(sigma * math.sqrt(HORIZON))
    )
    if sigma == 0:
        g_tail_bound = 0.0
    else:
        g_tail_bound = (
            F0
            * math.exp(mean_f_g - mean_g_g + 0.5 * gamma2 * HORIZON)
            * tilted_tail((sigma - beta) * math.sqrt(HORIZON))
        )
    return dict(
        q_price=q_price,
        g_price=g_price,
        q_tail_bound=q_tail_bound,
        g_tail_bound=g_tail_bound,
        absolute_difference=abs(q_price - g_price),
        f_variance=vf,
        g_variance=vg,
        f_g_covariance=cov,
    )


def sample_summary(values, truth):
    mean = float(np.mean(values))
    se = float(np.std(values, ddof=1) / math.sqrt(len(values)))
    return {
        "mean": mean,
        "se": se,
        "truth": truth,
        "z_error": None if se < 1e-14 else (mean - truth) / se,
        "absolute_difference": abs(mean - truth),
    }


CASES = [
    ("independent_3", [0.20, -0.10, 0.15], [0.12, 0.08, -0.18], np.eye(3)),
    (
        "correlated_3",
        [0.20, -0.10, 0.15],
        [0.12, 0.08, -0.18],
        [[1, 0.45, -0.30], [0.45, 1, 0.20], [-0.30, 0.20, 1]],
    ),
    (
        "correlated_3_negative_g",
        [0.20, -0.10, 0.15],
        [-0.12, -0.08, 0.18],
        [[1, 0.45, -0.30], [0.45, 1, 0.20], [-0.30, 0.20, 1]],
    ),
    (
        "correlated_3_zero_g",
        [0.20, -0.10, 0.15],
        [0, 0, 0],
        [[1, 0.45, -0.30], [0.45, 1, 0.20], [-0.30, 0.20, 1]],
    ),
    ("negative_covariance_2", [0.30, 0.10], [-0.15, 0.12], [[1, -0.60], [-0.60, 1]]),
    ("singular_plus_ratio_zero", [0.20, -0.10], [0.08, 0.02], [[1, 1], [1, 1]]),
    ("singular_minus_2", [0.20, 0.05], [-0.10, 0.15], [[1, -1], [-1, 1]]),
    ("one_factor_negative_g", [0.30], [-0.15], [[1]]),
    ("zero_f_2", [0, 0], [0.12, -0.18], [[1, 0.25], [0.25, 1]]),
    ("zero_all_2", [0, 0], [0, 0], [[1, 0.25], [0.25, 1]]),
    ("near_singular_2", [0.20, -0.10], [0.08, 0.02], [[1, 1 - 1e-12], [1 - 1e-12, 1]]),
]


def build():
    output = {
        "section": "28.5",
        "source_pages": [679, 680],
        "source_printed_pins": [],
        "synthetic": True,
        "units": {"rate": "year^-1", "loading": "year^-1/2", "time": "year"},
        "market": {"f0": F0, "g0": G0, "strike": K, "r": RATE, "horizon": HORIZON},
        "n_paths": N_PATHS,
        "quadrature_cutoff": 12.0,
        "note": "Synthetic finite GBM, signed correlated loadings, independent quadrature and raw iid MC.",
        "cases": [],
    }
    for number, (name, raw_f, raw_g, raw_corr) in enumerate(CASES):
        sf, sg, corr = np.array(raw_f), np.array(raw_g), np.array(raw_corr)
        eig, vec = np.linalg.eigh(corr)
        factor = vec * np.sqrt(np.maximum(eig, 0))[None, :]
        rank = int(np.sum(eig > 64 * np.finfo(float).eps * len(eig) * np.linalg.norm(corr, ord=2)))
        f_ind, g_ind = sf @ factor, sg @ factor
        vf, vg, cov = bilinear(sf, corr, sf), bilinear(sg, corr, sg), bilinear(sf, corr, sg)
        q_var = max(bilinear(sf - sg, corr, sf - sg), 0.0)
        mu_f_g, mu_g_g = RATE + cov, RATE + vg
        ratio_q_drift = vg - cov
        ratio_g_drift = mu_f_g - mu_g_g + vg - cov
        reconstruction = float(np.max(np.abs(factor @ factor.T - corr)))
        basis_dot_error = max(
            abs(float(f_ind @ f_ind) - vf),
            abs(float(g_ind @ g_ind) - vg),
            abs(float(f_ind @ g_ind) - cov),
        )
        price = price_quadratures(sf, sg, corr)
        conditional = []
        for observed in [0.65, 1.25, 2.0]:
            for h in [0.0, 0.25, 1.0, 2.5]:
                conditional.append(
                    {
                        "observed_ratio": observed,
                        "horizon": h,
                        "g_mean": observed,
                        "q_mean": observed * math.exp(ratio_q_drift * h),
                        "g_second_moment": observed**2 * math.exp(q_var * h),
                        "g_mean_quadrature": integrate_split(
                            lambda z, observed=observed, q_var=q_var, h=h: (
                                observed
                                * math.exp(-0.5 * q_var * h + math.sqrt(q_var * h) * z)
                                * phi(z)
                            )
                        ),
                        "mean_quadrature_tail_bound": observed
                        * math.exp(-0.5 * q_var * h)
                        * tilted_tail(math.sqrt(q_var * h)),
                        "second_moment_quadrature_tail_bound": observed**2
                        * math.exp(-q_var * h)
                        * tilted_tail(2 * math.sqrt(q_var * h)),
                        "g_second_moment_quadrature": integrate_split(
                            lambda z, observed=observed, q_var=q_var, h=h: (
                                observed**2
                                * math.exp(-q_var * h + 2 * math.sqrt(q_var * h) * z)
                                * phi(z)
                            )
                        ),
                    }
                )
        rng = np.random.default_rng(285730 + number)
        z = rng.standard_normal((N_PATHS, len(sf)))
        w = z @ factor.T * math.sqrt(HORIZON)
        f_q = F0 * np.exp((RATE - 0.5 * vf) * HORIZON + w @ sf)
        g_q = G0 * np.exp((RATE - 0.5 * vg) * HORIZON + w @ sg)
        f_g = F0 * np.exp((mu_f_g - 0.5 * vf) * HORIZON + w @ sf)
        g_g = G0 * np.exp((mu_g_g - 0.5 * vg) * HORIZON + w @ sg)
        density = g_q / G0 * math.exp(-RATE * HORIZON)
        rotation_input = np.arange(1, len(sf) ** 2 + 1, dtype=float).reshape(
            len(sf), len(sf)
        ) + np.eye(len(sf))
        rotation, _ = np.linalg.qr(rotation_input)
        transformed_w = (z @ rotation) @ (factor @ rotation).T * math.sqrt(HORIZON)
        rotation_error = float(np.max(np.abs(w - transformed_w)))
        chol_error = None
        if eig.min() > 1e-10:
            chol = np.linalg.cholesky(corr)
            chol_error = max(
                abs(float((sf @ chol) @ (sf @ chol)) - vf),
                abs(float((sf @ chol) @ (sg @ chol)) - cov),
            )
        row = {
            "id": name,
            "f_loadings": sf.tolist(),
            "g_loadings": sg.tolist(),
            "correlation": corr.tolist(),
            "eigenvalues": eig.tolist(),
            "rank": rank,
            "factor": factor.tolist(),
            "independent_f_loadings": f_ind.tolist(),
            "independent_g_loadings": g_ind.tolist(),
            "factor_reconstruction_error": reconstruction,
            "basis_dot_error": basis_dot_error,
            "cholesky_dot_error": chol_error,
            "rotation_pathwise_error": rotation_error,
            "g_drifts": [mu_f_g, mu_g_g],
            "ratio_q_drift": ratio_q_drift,
            "ratio_g_drift": ratio_g_drift,
            "relative_ratio_variance": q_var,
            "prices": price,
            "conditional": conditional,
            "mc": {
                "seed": 285730 + number,
                "density_q": sample_summary(density, 1.0),
                "ratio_g": sample_summary(f_g / g_g, F0 / G0),
                "ratio_reweighted_q": sample_summary(density * f_q / g_q, F0 / G0),
                "call_q": sample_summary(
                    math.exp(-RATE * HORIZON) * np.maximum(f_q - K, 0), price["q_price"]
                ),
                "call_g": sample_summary(G0 * np.maximum(f_g - K, 0) / g_g, price["q_price"]),
            },
        }
        output["cases"].append(row)
    assert max(row["prices"]["absolute_difference"] for row in output["cases"]) < 1e-10
    assert max(abs(row["ratio_g_drift"]) for row in output["cases"]) < 1e-15
    assert max(row["factor_reconstruction_error"] for row in output["cases"]) < 1e-14
    assert max(row["rotation_pathwise_error"] for row in output["cases"]) < 1e-13
    output["source_requirements"] = [f"MF{i:02}" for i in range(1, 7)]
    output["source_points"] = [
        {
            "id": "MF01",
            "pages": [679, 680],
            "statement": "Independent-factor Q/general-world drift and signed common basis",
        },
        {
            "id": "MF02",
            "pages": [680],
            "statement": "Relative/log Ito ratio drift, g risk loading cancels relative drift",
        },
        {
            "id": "MF03",
            "pages": [680],
            "statement": "Conditional future ratio, integrable finite constant GBM and local/general distinction",
        },
        {
            "id": "MF04",
            "pages": [680],
            "statement": "Same payoff Q/G prices extend prior numeraire identities",
        },
        {
            "id": "MF05",
            "pages": [679],
            "statement": "Footnote7 correlated factors via independent orthogonal basis",
        },
        {
            "id": "MF06",
            "pages": [679, 680],
            "statement": "Rank-deficient PSD, coordinate invariance and explicit units/domains",
        },
    ]
    output["source_sha256"] = {
        name: hashlib.sha256((PROJECT / name).read_bytes()).hexdigest()
        for name in (
            "scripts/build_multifactor_reference.py",
            "options, futures and other derivatives 11th.pdf",
        )
    }
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = json.dumps(build(), indent=2, allow_nan=False) + "\n"
    if args.check:
        if not OUT.is_file() or OUT.read_text() != payload:
            raise ValueError("independent multifactor reference is stale")
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(payload)
    print("PASS: §28.5 independent11 markets/132 conditioned states/correlated Q-G pricing")


if __name__ == "__main__":
    main()
