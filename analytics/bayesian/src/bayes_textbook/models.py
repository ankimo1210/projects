"""Models: Bayesian linear regression (closed form), partial pooling, MCMC.

Everything here is NumPy/SciPy only. Chapter 08 re-fits the same models with
PyMC; these closed forms are what the samplers are validated against.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import optimize, stats

from .conjugacy import BetaBinomial


class BayesianLinearRegression:
    """y = X w + eps with w ~ N(0, sigma_w^2 I), eps ~ N(0, sigma^2 I).

    The posterior over weights is Gaussian with closed form:
        cov  = (X^T X / sigma^2 + I / sigma_w^2)^{-1}
        mean = cov X^T y / sigma^2
    The posterior mean equals ridge regression with lambda = sigma^2 / sigma_w^2.
    """

    def __init__(self, sigma: float = 1.0, sigma_w: float = 10.0):
        self.sigma = sigma
        self.sigma_w = sigma_w
        self.w_mean = None
        self.w_cov = None

    def fit(self, X, y):
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        d = X.shape[1]
        prec = X.T @ X / self.sigma**2 + np.eye(d) / self.sigma_w**2
        self.w_cov = np.linalg.inv(prec)
        self.w_mean = self.w_cov @ X.T @ y / self.sigma**2
        return self

    def sample_weights(self, n: int, seed: int = 42):
        r = np.random.default_rng(seed)
        return r.multivariate_normal(self.w_mean, self.w_cov, size=n)

    def predict(self, X, level: float = 0.95):
        """Predictive summary at new inputs.

        Returns dict with 'mean', credible band for the regression FUNCTION
        ('cred_lo/hi', uncertainty in w only) and the predictive band for new
        OBSERVATIONS ('pred_lo/hi', adds the noise sigma^2).
        """
        X = np.asarray(X, dtype=float)
        mean = X @ self.w_mean
        func_var = np.einsum("ij,jk,ik->i", X, self.w_cov, X)
        z = stats.norm.ppf(0.5 + level / 2)
        cred_sd = np.sqrt(func_var)
        pred_sd = np.sqrt(func_var + self.sigma**2)
        return {
            "mean": mean,
            "cred_lo": mean - z * cred_sd,
            "cred_hi": mean + z * cred_sd,
            "pred_lo": mean - z * pred_sd,
            "pred_hi": mean + z * pred_sd,
        }


def ridge_solution(X, y, lam: float):
    """Plain ridge regression weights (for the equivalence check)."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    d = X.shape[1]
    return np.linalg.solve(X.T @ X + lam * np.eye(d), X.T @ y)


# ---------------------------------------------------------------------------
# Partial pooling (hierarchical Bayes, empirical-Bayes flavored closed forms)
# ---------------------------------------------------------------------------


@dataclass
class PoolingResult:
    """Per-group estimates under the three pooling regimes."""

    unpooled: np.ndarray  # raw per-group rates
    pooled: float  # one shared rate for everyone
    partial: np.ndarray  # hierarchical posterior means
    posteriors: list  # per-group BetaBinomial posteriors
    prior: BetaBinomial  # the shared (estimated) prior


def fit_partial_pooling_beta(
    successes, trials, prior_strength: float | None = None
) -> PoolingResult:
    """Hierarchical binomial rates via an empirical-Bayes Beta prior.

    The shared Beta prior is estimated from the groups themselves
    (method of moments on the observed rates; ``prior_strength`` overrides
    the implied alpha+beta if given). Each group is then updated with its own
    data: small groups shrink toward the global mean, big groups stay put.
    """
    s = np.asarray(successes, dtype=float)
    n = np.asarray(trials, dtype=float)
    rates = s / n
    pooled = s.sum() / n.sum()

    if prior_strength is None:
        # Method of moments: match the across-group variance of observed rates.
        var = rates.var(ddof=1)
        mean = pooled
        # Var of Beta(mean, k): mean(1-mean)/(k+1). Solve for k, keep it sane.
        k = mean * (1 - mean) / max(var, 1e-8) - 1
        prior_strength = float(np.clip(k, 1.0, 1e4))

    alpha0 = pooled * prior_strength
    beta0 = (1 - pooled) * prior_strength
    prior = BetaBinomial(alpha0, beta0)
    posteriors = [prior.update(int(si), int(ni - si)) for si, ni in zip(s, n, strict=True)]
    partial = np.array([p.mean for p in posteriors])
    return PoolingResult(rates, float(pooled), partial, posteriors, prior)


def fit_partial_pooling_normal(means, sems, tau: float | None = None):
    """Hierarchical normal means (the 8-schools setup).

    Group effects theta_i ~ N(mu, tau^2); observed means y_i ~ N(theta_i, sem_i^2).
    If tau is None it is estimated by maximizing the marginal likelihood on a
    grid. Returns (shrunk means, mu_hat, tau_hat).
    """
    y = np.asarray(means, dtype=float)
    se = np.asarray(sems, dtype=float)

    def neg_marginal_loglik(log_tau):
        t2 = np.exp(log_tau) ** 2
        var = se**2 + t2
        mu = np.sum(y / var) / np.sum(1 / var)
        return 0.5 * np.sum(np.log(var) + (y - mu) ** 2 / var)

    if tau is None:
        res = optimize.minimize_scalar(neg_marginal_loglik, bounds=(-6, 3), method="bounded")
        tau = float(np.exp(res.x))
    var = se**2 + tau**2
    mu_hat = float(np.sum(y / var) / np.sum(1 / var))
    # Posterior mean per group: precision-weighted blend of y_i and mu_hat.
    w = (tau**2) / (tau**2 + se**2) if tau > 0 else np.zeros_like(se)
    shrunk = w * y + (1 - w) * mu_hat
    return shrunk, mu_hat, tau


# ---------------------------------------------------------------------------
# From-scratch samplers (chapter 07)
# ---------------------------------------------------------------------------


def metropolis_hastings(log_target, x0: float, n_steps: int, proposal_sd: float, seed: int = 42):
    """Random-walk Metropolis on a 1-D target. Returns (samples, accept_rate)."""
    r = np.random.default_rng(seed)
    x = float(x0)
    logp = log_target(x)
    samples = np.empty(n_steps)
    accepted = 0
    for t in range(n_steps):
        prop = x + proposal_sd * r.standard_normal()
        logp_prop = log_target(prop)
        if np.log(r.random()) < logp_prop - logp:
            x, logp = prop, logp_prop
            accepted += 1
        samples[t] = x
    return samples, accepted / n_steps


def gibbs_bivariate_normal(rho: float, n_steps: int, seed: int = 42):
    """Gibbs sampler for a standard bivariate normal with correlation rho.

    Each conditional is Normal(rho * other, 1 - rho^2) — the classic teaching
    example of coordinate-wise sampling. Returns samples of shape (n_steps, 2).
    """
    r = np.random.default_rng(seed)
    x = y = 0.0
    out = np.empty((n_steps, 2))
    sd = np.sqrt(1 - rho**2)
    for t in range(n_steps):
        x = rho * y + sd * r.standard_normal()
        y = rho * x + sd * r.standard_normal()
        out[t] = (x, y)
    return out


def leapfrog(q0, p0, grad_logp, step_size: float, n_steps: int):
    """Leapfrog integration of Hamiltonian dynamics (for the HMC intuition plot).

    Returns the trajectory of positions, shape (n_steps + 1, dim).
    """
    q = np.array(q0, dtype=float)
    p = np.array(p0, dtype=float)
    path = [q.copy()]
    p = p + 0.5 * step_size * grad_logp(q)
    for i in range(n_steps):
        q = q + step_size * p
        g = grad_logp(q)
        if i < n_steps - 1:
            p = p + step_size * g
        path.append(q.copy())
    return np.array(path)


def autocorrelation(samples, max_lag: int = 50):
    """Normalized autocorrelation function of a 1-D chain."""
    x = np.asarray(samples, dtype=float)
    x = x - x.mean()
    acf = np.correlate(x, x, mode="full")[len(x) - 1 :]
    acf = acf / acf[0]
    return acf[: max_lag + 1]


# ---------------------------------------------------------------------------
# Gaussian process + bandits (chapter 12: Bayesian optimization / Thompson)
# ---------------------------------------------------------------------------


class GaussianProcess:
    """Zero-mean GP regression with an RBF kernel and Gaussian noise.

    The posterior over function values is Gaussian with closed form — the same
    "Normal prior x Normal likelihood -> Normal posterior" machinery as ch.04,
    lifted to functions. Used as the surrogate model in Bayesian optimization.
    """

    def __init__(self, length_scale: float = 1.0, signal_var: float = 1.0, noise: float = 1e-4):
        self.length_scale = length_scale
        self.signal_var = signal_var
        self.noise = noise
        self.X = None
        self.y = None
        self._L = None
        self._alpha = None

    def _kernel(self, A, B):
        A = np.atleast_2d(A)
        B = np.atleast_2d(B)
        sq = np.sum(A**2, 1)[:, None] + np.sum(B**2, 1)[None, :] - 2 * A @ B.T
        return self.signal_var * np.exp(-0.5 * sq / self.length_scale**2)

    def fit(self, X, y):
        self.X = np.atleast_2d(np.asarray(X, dtype=float))
        self.y = np.asarray(y, dtype=float)
        K = self._kernel(self.X, self.X) + self.noise * np.eye(len(self.X))
        self._L = np.linalg.cholesky(K)
        self._alpha = np.linalg.solve(self._L.T, np.linalg.solve(self._L, self.y))
        return self

    def predict(self, X_new):
        """Posterior mean and standard deviation at new inputs."""
        X_new = np.atleast_2d(np.asarray(X_new, dtype=float))
        Ks = self._kernel(self.X, X_new)
        mean = Ks.T @ self._alpha
        v = np.linalg.solve(self._L, Ks)
        var = np.diag(self._kernel(X_new, X_new)) - np.sum(v**2, 0)
        return mean, np.sqrt(np.clip(var, 0, None))


def expected_improvement(gp, X_grid, best_y, xi: float = 0.01):
    """EI acquisition for MINIMIZATION: how much we expect to beat best_y."""
    from scipy import stats

    mean, sd = gp.predict(X_grid)
    sd = np.maximum(sd, 1e-9)
    z = (best_y - mean - xi) / sd
    return (best_y - mean - xi) * stats.norm.cdf(z) + sd * stats.norm.pdf(z)


def thompson_bandit(true_rates, n_rounds: int = 2000, seed: int = 0):
    """Thompson sampling for Bernoulli bandits.

    Each round: draw theta_k ~ Beta posterior of each arm, pull the argmax,
    update that arm. Returns (pulls per arm, cumulative regret per round).
    """
    rng = np.random.default_rng(seed)
    true_rates = np.asarray(true_rates, dtype=float)
    k = len(true_rates)
    alpha = np.ones(k)
    beta = np.ones(k)
    best = true_rates.max()
    pulls = np.zeros(k, dtype=int)
    regret = np.empty(n_rounds)
    cum = 0.0
    for t in range(n_rounds):
        samples = rng.beta(alpha, beta)
        arm = int(np.argmax(samples))
        reward = rng.random() < true_rates[arm]
        alpha[arm] += reward
        beta[arm] += 1 - reward
        pulls[arm] += 1
        cum += best - true_rates[arm]
        regret[t] = cum
    return pulls, regret


def epsilon_greedy_bandit(true_rates, n_rounds: int = 2000, epsilon: float = 0.1, seed: int = 0):
    """Epsilon-greedy baseline for comparison with Thompson sampling."""
    rng = np.random.default_rng(seed)
    true_rates = np.asarray(true_rates, dtype=float)
    k = len(true_rates)
    wins = np.zeros(k)
    pulls = np.zeros(k, dtype=int)
    best = true_rates.max()
    regret = np.empty(n_rounds)
    cum = 0.0
    for t in range(n_rounds):
        if rng.random() < epsilon or pulls.min() == 0:
            arm = int(rng.integers(k))
        else:
            arm = int(np.argmax(wins / np.maximum(pulls, 1)))
        reward = rng.random() < true_rates[arm]
        wins[arm] += reward
        pulls[arm] += 1
        cum += best - true_rates[arm]
        regret[t] = cum
    return pulls, regret
