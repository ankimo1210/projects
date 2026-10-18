"""Features F, P, CP inputs, M and X, and the transforms fitted inside the window (design §6.1, R4).

F   the one-year yield and one-year forwards f(n) = n y(n) - (n-1) y(n-1), n = 2..10, standardized
P   three principal components of the demeaned 1..10-year yields
M   FRED-MD transformed series: outliers (|x - median| > 10 IQR) to missing, standardized,
    series with more than 20 % missing dropped, remaining gaps set to 0; linear models use 8 PCs
X   only the L1 rules use it: the 10-year minus 3-month slope and the trailing 12-month excess return
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .data.fred import bey_to_cc

YIELD_MONTHS = tuple(12 * n for n in range(1, 11))
N_YIELD_PCS = 3
N_MACRO_PCS = 8
OUTLIER_IQR = 10.0
MAX_NAN_SHARE = 0.20


def forwards(Y: np.ndarray) -> np.ndarray:
    n = np.arange(1.0, 11.0)
    out = np.array(Y, dtype=float, copy=True)
    out[:, 1:] = n[1:] * Y[:, 1:] - n[:-1] * Y[:, :-1]
    return out


class Standardizer:
    def fit(self, X: np.ndarray) -> Standardizer:
        self.mean_ = X.mean(axis=0)
        std = X.std(axis=0)
        self.std_ = np.where(std > 0, std, 1.0)
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        return (X - self.mean_) / self.std_


class Pca:
    def __init__(self, k: int):
        self.k = k

    def fit(self, X: np.ndarray) -> Pca:
        self.mean_ = X.mean(axis=0)
        _, _, vt = np.linalg.svd(X - self.mean_, full_matrices=False)
        components = vt[: self.k]
        signs = np.sign(components[np.arange(len(components)), np.abs(components).argmax(axis=1)])
        self.components_ = components * signs[:, None]
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        return (X - self.mean_) @ self.components_.T


class MacroCleaner:
    def fit(self, M: np.ndarray) -> MacroCleaner:
        with warnings.catch_warnings(), np.errstate(invalid="ignore"):
            warnings.simplefilter("ignore", RuntimeWarning)
            self.median_ = np.nanmedian(M, axis=0)
            q75, q25 = np.nanpercentile(M, [75, 25], axis=0)
            self.iqr_ = q75 - q25
            clean = self._outliers(M)
            share = np.isnan(clean).mean(axis=0)
            mean = np.nanmean(clean, axis=0)
            std = np.nanstd(clean, axis=0)
        self.keep_ = (share <= MAX_NAN_SHARE) & np.isfinite(std) & (std > 0)
        self.mean_, self.std_ = mean[self.keep_], std[self.keep_]
        return self

    def _outliers(self, M: np.ndarray) -> np.ndarray:
        with np.errstate(invalid="ignore"):
            far = (np.abs(M - self.median_) > OUTLIER_IQR * self.iqr_) & (self.iqr_ > 0)
        return np.where(far, np.nan, M)

    def transform(self, M: np.ndarray) -> np.ndarray:
        z = (self._outliers(M)[:, self.keep_] - self.mean_) / self.std_
        return np.nan_to_num(z, nan=0.0)


@dataclass(frozen=True)
class InputSpec:
    yields: str  # "P" (principal components) or "F" (standardized forwards)
    macro: str  # "" (none), "PC" (8 components of M) or "M" (all of M)


INPUTS = {
    "P": InputSpec("P", ""),
    "PM": InputSpec("P", "PC"),
    "F": InputSpec("F", ""),
    "FM": InputSpec("F", "M"),
}


class InputTransform:
    def __init__(self, spec: InputSpec):
        self.spec = spec

    def fit(self, Y: np.ndarray, M: np.ndarray | None) -> InputTransform:
        if self.spec.yields == "P":
            self.yields_ = Pca(N_YIELD_PCS).fit(Y)
        else:
            self.yields_ = Standardizer().fit(forwards(Y))
        if self.spec.macro:
            if M is None:
                raise ValueError(f"inputs {self.spec} need macro data")
            self.macro_ = MacroCleaner().fit(M)
            if self.spec.macro == "PC":
                self.macro_pca_ = Pca(N_MACRO_PCS).fit(self.macro_.transform(M))
        return self

    def transform(self, Y: np.ndarray, M: np.ndarray | None) -> np.ndarray:
        parts = [self.yields_.transform(Y if self.spec.yields == "P" else forwards(Y))]
        if self.spec.macro:
            cleaned = self.macro_.transform(M)
            parts.append(self.macro_pca_.transform(cleaned) if self.spec.macro == "PC" else cleaned)
        return np.hstack(parts)


def slope(zeros: pd.DataFrame, bey: pd.Series) -> pd.Series:
    """GSW 10-year zero minus the 3-month bill, both continuously compounded (decision months)."""
    return zeros[120] - bey_to_cc(bey)


def trailing_sum(excess: pd.Series, window: int = 12) -> pd.Series:
    """Sum of the last ``window`` monthly excess returns; month t is observed at decision t."""
    return excess.rolling(window).sum()
