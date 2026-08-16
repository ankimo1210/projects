"""The Bayesian side of chapter 11, kept inside this book.

NB11 compares two procedures on the same data, so it needs a working
Bayesian analysis. Importing ``bayes_textbook`` would be the obvious
route and is deliberately not taken: the analytics books do not depend on
each other, and a conjugate beta-binomial is twenty lines.

Scope is exactly what the comparison needs -- one model, three priors, an
interval and a Bayes factor. Anything more belongs in the sibling book.
"""

from __future__ import annotations

import math

from scipy import special, stats

from .intervals import Interval

__all__ = [
    "PRIORS",
    "bayes_factor_proportion",
    "beta_binomial_posterior",
    "credible_interval",
    "posterior_mean",
]

# The three priors NB11 contrasts. Jeffreys is the "let the data speak"
# default; strong_high has a mean of 0.8 and the weight of 25 observations.
PRIORS: dict[str, tuple[float, float]] = {
    "jeffreys": (0.5, 0.5),
    "uniform": (1.0, 1.0),
    "strong_high": (20.0, 5.0),
}


def _check(k: int, n: int) -> None:
    if not 0 <= k <= n:
        raise ValueError(f"k must satisfy 0 <= k <= n; got k={k}, n={n}")


def beta_binomial_posterior(k: int, n: int, prior_a: float = 0.5, prior_b: float = 0.5):
    """Posterior for a proportion after ``k`` successes in ``n`` trials.

    Conjugacy makes this exact: Beta(a, b) prior, Binomial likelihood, and
    the posterior is Beta(a + k, b + n - k). The prior's parameters read as
    pseudo-counts, which is what makes "how much data is this prior worth"
    a question with a number for an answer.
    """
    _check(k, n)
    return stats.beta(prior_a + k, prior_b + n - k)


def posterior_mean(k: int, n: int, prior_a: float = 0.5, prior_b: float = 0.5) -> float:
    """(a + k) / (a + b + n) -- a weighted average of prior mean and MLE."""
    _check(k, n)
    return (prior_a + k) / (prior_a + prior_b + n)


def credible_interval(
    k: int, n: int, prior_a: float = 0.5, prior_b: float = 0.5, level: float = 0.95
) -> Interval:
    """Equal-tailed posterior interval.

    Unlike a Wald interval this cannot leave [0, 1]: it is built from
    quantiles of a distribution that lives there. NB11 uses that as the
    concrete difference between the two kinds of interval.
    """
    post = beta_binomial_posterior(k, n, prior_a, prior_b)
    lo, hi = post.ppf([(1.0 - level) / 2.0, 1.0 - (1.0 - level) / 2.0])
    return Interval(float(lo), float(hi))


def bayes_factor_proportion(
    k: int, n: int, p0: float = 0.5, prior_a: float = 1.0, prior_b: float = 1.0
) -> float:
    """Marginal likelihood of H1 (p ~ Beta) over H0 (p = p0).

    Under H0 the likelihood is just Binomial(n, p0) at k. Under H1 the
    proportion is integrated out, which conjugacy does in closed form via
    the Beta function. The ratio answers "how much more likely is this
    data under a free p than under p0", which is a different question from
    the p-value's "how extreme is this data if p = p0".
    """
    _check(k, n)
    # Both marginal likelihoods carry the binomial coefficient. It cancels in
    # the ratio -- but only if it appears on both sides. stats.binom.logpmf
    # includes it, so the Beta-function form for H1 needs it added back
    # explicitly; omitting it silently scales every Bayes factor by C(n, k),
    # which at n=100 is a factor of 1e29.
    log_coef = special.gammaln(n + 1) - special.gammaln(k + 1) - special.gammaln(n - k + 1)
    log_h0 = stats.binom.logpmf(k, n, p0)
    log_h1 = (
        log_coef + special.betaln(prior_a + k, prior_b + n - k) - special.betaln(prior_a, prior_b)
    )
    return float(math.exp(log_h1 - log_h0))
