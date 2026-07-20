from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit

from jhrmbs.exceptions import ModelError
from jhrmbs.util import atomic_write_json, read_json


@dataclass
class FractionalLogitModel:
    feature_names: tuple[str, ...]
    l2_penalty: float = 0.0001
    imputation_values: np.ndarray | None = None
    means: np.ndarray | None = None
    scales: np.ndarray | None = None
    coefficients: np.ndarray | None = None
    converged: bool = False
    iterations: int = 0
    objective_value: float | None = None
    training_rows: int = 0

    def _prepare(self, frame: pd.DataFrame, *, fitting: bool) -> np.ndarray:
        missing = [name for name in self.feature_names if name not in frame.columns]
        if missing:
            raise ModelError(f"model features are missing: {missing}")
        values = (
            frame.loc[:, self.feature_names].apply(pd.to_numeric, errors="coerce").to_numpy(float)
        )
        if fitting:
            imputation = np.zeros(values.shape[1], dtype=float)
            for column in range(values.shape[1]):
                finite = values[np.isfinite(values[:, column]), column]
                imputation[column] = float(np.median(finite)) if finite.size else 0.0
            filled = np.where(np.isfinite(values), values, imputation)
            means = filled.mean(axis=0)
            scales = filled.std(axis=0)
            scales = np.where(scales > 1e-12, scales, 1.0)
            self.imputation_values = imputation
            self.means = means
            self.scales = scales
        if self.imputation_values is None or self.means is None or self.scales is None:
            raise ModelError("model preprocessing is not fitted")
        filled = np.where(np.isfinite(values), values, self.imputation_values)
        standardized = (filled - self.means) / self.scales
        return np.column_stack([np.ones(len(standardized)), standardized])

    def fit(
        self,
        frame: pd.DataFrame,
        target: pd.Series,
        *,
        sample_weight: pd.Series | None = None,
    ) -> FractionalLogitModel:
        design = self._prepare(frame, fitting=True)
        response = pd.to_numeric(target, errors="coerce").to_numpy(float)
        if not np.isfinite(response).all() or ((response < 0.0) | (response > 1.0)).any():
            raise ModelError("fractional-logit target must be finite and in [0, 1]")
        if sample_weight is None:
            weights = np.ones(len(response), dtype=float)
        else:
            weights = pd.to_numeric(sample_weight, errors="coerce").to_numpy(float)
            if not np.isfinite(weights).all() or (weights <= 0.0).any():
                raise ModelError("sample weights must be positive and finite")
            weights = weights / np.mean(weights)
            weights = np.minimum(weights, 20.0)
        normalizer = float(weights.sum())

        def objective(beta: np.ndarray) -> tuple[float, np.ndarray]:
            linear = design @ beta
            mean = expit(linear)
            epsilon = np.finfo(float).eps
            likelihood = response * np.log(np.clip(mean, epsilon, 1.0)) + (1.0 - response) * np.log(
                np.clip(1.0 - mean, epsilon, 1.0)
            )
            penalty = 0.5 * self.l2_penalty * float(beta[1:] @ beta[1:])
            value = -float(weights @ likelihood) / normalizer + penalty
            gradient = design.T @ (weights * (mean - response)) / normalizer
            gradient[1:] += self.l2_penalty * beta[1:]
            return value, gradient

        result = minimize(
            lambda beta: objective(beta)[0],
            np.zeros(design.shape[1], dtype=float),
            jac=lambda beta: objective(beta)[1],
            method="L-BFGS-B",
            options={"maxiter": 1_000, "ftol": 1e-12, "gtol": 1e-8},
        )
        if not result.success and float(np.linalg.norm(result.jac)) > 1e-5:
            raise ModelError(f"fractional logit did not converge: {result.message}")
        self.coefficients = np.asarray(result.x, dtype=float)
        self.converged = bool(result.success)
        self.iterations = int(result.nit)
        self.objective_value = float(result.fun)
        self.training_rows = len(frame)
        return self

    def predict_smm(self, frame: pd.DataFrame) -> np.ndarray:
        if self.coefficients is None:
            raise ModelError("model is not fitted")
        design = self._prepare(frame, fitting=False)
        return np.asarray(np.clip(expit(design @ self.coefficients), 0.0, 1.0), dtype=float)

    def to_dict(self) -> dict[str, Any]:
        if any(
            value is None
            for value in (
                self.imputation_values,
                self.means,
                self.scales,
                self.coefficients,
            )
        ):
            raise ModelError("cannot serialize an unfitted model")
        return {
            "model_type": "fractional_logit",
            "feature_names": list(self.feature_names),
            "l2_penalty": self.l2_penalty,
            "imputation_values": self.imputation_values.tolist(),  # type: ignore[union-attr]
            "means": self.means.tolist(),  # type: ignore[union-attr]
            "scales": self.scales.tolist(),  # type: ignore[union-attr]
            "coefficients": self.coefficients.tolist(),  # type: ignore[union-attr]
            "converged": self.converged,
            "iterations": self.iterations,
            "objective_value": self.objective_value,
            "training_rows": self.training_rows,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> FractionalLogitModel:
        if payload.get("model_type") != "fractional_logit":
            raise ModelError(f"unsupported model type: {payload.get('model_type')}")
        model = cls(
            feature_names=tuple(str(name) for name in payload["feature_names"]),
            l2_penalty=float(payload["l2_penalty"]),
        )
        model.imputation_values = np.asarray(payload["imputation_values"], dtype=float)
        model.means = np.asarray(payload["means"], dtype=float)
        model.scales = np.asarray(payload["scales"], dtype=float)
        model.coefficients = np.asarray(payload["coefficients"], dtype=float)
        model.converged = bool(payload.get("converged", False))
        model.iterations = int(payload.get("iterations", 0))
        model.objective_value = (
            float(payload["objective_value"])
            if payload.get("objective_value") is not None
            else None
        )
        model.training_rows = int(payload.get("training_rows", 0))
        return model

    def save(self, path: Path, *, metadata: dict[str, Any] | None = None) -> None:
        payload = self.to_dict()
        if metadata:
            payload["metadata"] = metadata
        atomic_write_json(path, payload)

    @classmethod
    def load(cls, path: Path) -> FractionalLogitModel:
        payload = read_json(path)
        if not isinstance(payload, dict):
            raise ModelError(f"invalid model artifact: {path}")
        return cls.from_dict(payload)
