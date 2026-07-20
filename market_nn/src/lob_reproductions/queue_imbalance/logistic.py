from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit


@dataclass
class ParametricLogisticRegression:
    """Unregularized maximum-likelihood logistic regression from Eq. 17."""

    coefficients_: np.ndarray | None = None
    converged_: bool = False
    n_iter_: int = 0

    def fit(self, imbalance: np.ndarray, response: np.ndarray) -> ParametricLogisticRegression:
        x = np.asarray(imbalance, dtype=float).reshape(-1)
        y = np.asarray(response, dtype=float).reshape(-1)
        if x.shape != y.shape or x.size < 2:
            raise ValueError("imbalance and response must be aligned non-trivial vectors")
        if not np.all(np.isin(y, (0.0, 1.0))):
            raise ValueError("response must be binary")
        design = np.column_stack((np.ones_like(x), x))

        def objective(beta: np.ndarray) -> tuple[float, np.ndarray]:
            linear = design @ beta
            loss = np.logaddexp(0.0, linear).sum() - y @ linear
            gradient = design.T @ (expit(linear) - y)
            return float(loss), gradient

        result = minimize(
            objective,
            x0=np.zeros(2, dtype=float),
            method="BFGS",
            jac=True,
            options={"gtol": 1e-10, "maxiter": 1_000},
        )
        self.coefficients_ = np.asarray(result.x, dtype=float)
        self.converged_ = bool(result.success or np.linalg.norm(result.jac) < 1e-6)
        self.n_iter_ = int(result.nit)
        return self

    @property
    def intercept_(self) -> float:
        self._require_fit()
        return float(self.coefficients_[0])

    @property
    def slope_(self) -> float:
        self._require_fit()
        return float(self.coefficients_[1])

    def predict_proba(self, imbalance: np.ndarray) -> np.ndarray:
        self._require_fit()
        x = np.asarray(imbalance, dtype=float)
        return expit(self.coefficients_[0] + self.coefficients_[1] * x)

    def _require_fit(self) -> None:
        if self.coefficients_ is None:
            raise RuntimeError("model is not fitted")
