"""Factor-exposure attribution — regress strategy returns on factor returns.

An OLS of the strategy's returns on one or more factor return series (with an
intercept) splits performance into **betas** (systematic exposure to each factor)
and **alpha** (the intercept — return unexplained by the factors). ``r_squared``
says how much of the strategy is just factor exposure in disguise. This is the
attribution question "is my edge real, or am I long the market?".
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def factor_exposure(strategy_returns: pd.Series, factors: pd.DataFrame) -> pd.DataFrame:
    """OLS exposure of ``strategy_returns`` on ``factors`` (intercept = alpha).

    Returns a frame indexed ``["alpha", *factor names]`` with columns ``beta`` (the
    coefficient; ``alpha`` row is the intercept) and ``t_stat``. The regression
    ``r_squared`` is attached on ``result.attrs["r_squared"]``. Rows with any NaN are
    dropped (no silent fill).
    """
    df = pd.concat([strategy_returns.rename("y"), factors], axis=1).dropna()
    y = df["y"].to_numpy(dtype=float)
    names = list(factors.columns)
    X = np.column_stack([np.ones(len(df)), df[names].to_numpy(dtype=float)])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    dof = max(len(y) - X.shape[1], 1)
    sigma2 = float(resid @ resid) / dof
    xtx_inv = np.linalg.pinv(X.T @ X)
    se = np.sqrt(np.maximum(np.diag(xtx_inv) * sigma2, 0.0))
    t_stat = np.divide(beta, se, out=np.full_like(beta, np.nan), where=se > 0)
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - float(resid @ resid) / ss_tot if ss_tot > 0 else float("nan")
    out = pd.DataFrame(
        {"beta": beta, "t_stat": t_stat},
        index=["alpha", *names],
    )
    out.attrs["r_squared"] = r2
    return out
