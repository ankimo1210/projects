"""Does handing TimesFM 3.0 a covariate actually help?

TimesFM 3.0's headline feature is native covariate support, and the main bench
does not touch it — every number there comes from a univariate context. This
module runs the one comparison that isolates it: the *same* model on the *same*
windows, with and without extra channels.

Three settings, chosen so the answer is interpretable rather than merely
positive:

- ``syn_nonlinear_driver`` hands over the true latent driver. We built the
  process, so we know the covariate is the whole story and we know the ceiling.
  If covariates cannot help here, they cannot help anywhere.
- ``ett_h1`` predicts the oil temperature from the six load channels — the
  standard multivariate setup on the standard benchmark.
- ``fin_range_vol`` adds log volume to volatility, the one pairing in finance
  where a lead-lag relationship is actually documented.
"""

from __future__ import annotations

import dataclasses

import numpy as np

from .datasets import SPEC_BY_KEY, DatasetSpec, Window, build_windows


@dataclasses.dataclass(frozen=True)
class CovariateSetting:
    key: str
    title: str
    note: str
    dataset: str


SETTINGS: tuple[CovariateSetting, ...] = (
    CovariateSetting(
        key="cov_syn_driver",
        title="合成: 未観測ドライバを渡す",
        note="真の潜在AR(1)ドライバをそのまま共変量にする。効かないなら何にも効かない。",
        dataset="syn_nonlinear_driver",
    ),
    CovariateSetting(
        key="cov_ett_h1",
        title="ETTh1: 油温を6負荷チャネルから",
        note="長期予測ベンチの標準的な多変量設定。",
        dataset="ett_h1",
    ),
    CovariateSetting(
        key="cov_fin_vol",
        title="金融: ボラに出来高を足す",
        note="金融でリードラグ関係が実証されている数少ない組み合わせ。",
        dataset="fin_range_vol",
    ),
)


def _with_covariates(w: Window, cov: np.ndarray) -> Window:
    return dataclasses.replace(w, past_covariates=np.asarray(cov, dtype=np.float32))


def build_driver_windows(seed: int = 0) -> list[Window]:
    """Synthetic windows carrying the true latent driver as a past-only covariate."""
    from .synthetic import PROCESS_BY_KEY

    spec = SPEC_BY_KEY["syn_nonlinear_driver"]
    proc = PROCESS_BY_KEY["syn_nonlinear_driver"]
    import zlib

    n = spec.context_length + spec.horizon * spec.n_windows + 64
    aux_by_series = {}
    for s in range(spec.n_series):
        rng = np.random.default_rng([seed, zlib.crc32(spec.key.encode()), s])
        # Same seed recipe as datasets._build_synthetic_windows, so the driver
        # belongs to the very series the window was cut from.
        _values, aux_by_series[f"S{s:03d}"] = proc.generate(rng, n)

    out: list[Window] = []
    for w in build_windows(spec, seed=seed):
        aux = aux_by_series[w.series_id]
        u = proc.driver(aux, w.cutoff - spec.context_length, w.cutoff)
        out.append(_with_covariates(w, u[None, :]))
    return out


def build_ett_windows(seed: int = 0) -> list[Window]:
    """ETTh1 OT windows with the six load channels as past-only covariates."""
    from .datasets import load_series

    spec = SPEC_BY_KEY["ett_h1"]
    channels = dict(load_series(spec))
    others = [c for c in channels if c != "OT"]
    out: list[Window] = []
    for w in build_windows(spec, seed=seed):
        if w.series_id != "OT":
            continue
        lo, hi = w.cutoff - spec.context_length, w.cutoff
        cov = np.stack([channels[c][lo:hi] for c in others])
        if not np.isfinite(cov).all():
            continue
        out.append(_with_covariates(w, cov))
    return out


def build_finance_windows(seed: int = 0) -> list[Window]:
    """Range-volatility windows with the same ticker's log volume alongside."""
    from .finance import build_targets, load_ohlcv

    spec = SPEC_BY_KEY["fin_range_vol"]
    targets = build_targets(load_ohlcv())
    volume = {t: v for t, v, _d in targets["fin_log_volume"]}
    vol_dates = {t: d for t, _v, d in targets["fin_log_volume"]}
    vol_target_dates = {t: d for t, _v, d in targets["fin_range_vol"]}
    out: list[Window] = []
    for w in build_windows(spec, seed=seed):
        if w.series_id not in volume:
            continue
        # The two targets drop different rows, so align on dates rather than index.
        want = vol_target_dates[w.series_id][w.cutoff - spec.context_length : w.cutoff]
        have = vol_dates[w.series_id]
        pos = np.searchsorted(have, want)
        if pos.max() >= len(have) or not (have[pos] == want).all():
            continue
        out.append(_with_covariates(w, volume[w.series_id][pos][None, :]))
    return out


BUILDERS = {
    "cov_syn_driver": build_driver_windows,
    "cov_ett_h1": build_ett_windows,
    "cov_fin_vol": build_finance_windows,
}


def run_setting(setting: CovariateSetting, runner, seed: int = 0) -> dict:
    """Score the same windows twice: context only, then context plus covariates."""
    from .baselines import Forecast
    from .bench import score

    spec: DatasetSpec = SPEC_BY_KEY[setting.dataset]
    windows = BUILDERS[setting.key](seed)
    if not windows:
        raise ValueError(f"{setting.key}: no windows built")

    contexts = [w.context for w in windows]
    plain, _ = runner.predict(contexts, spec.horizon)
    withcov, _ = runner.predict_with_covariates(
        contexts, [w.past_covariates for w in windows], spec.horizon
    )

    rows = []
    for w, a, b in zip(windows, plain, withcov, strict=True):
        base = {"setting": setting.key, "dataset": spec.key, "series_id": w.series_id,
                "cutoff": w.cutoff, "n_covariates": int(w.past_covariates.shape[0])}
        rows.append(base | {"arm": "univariate"} | score(w, a))
        rows.append(base | {"arm": "with_covariates"} | score(w, b))
        if w.oracle_point is not None:
            oracle = Forecast(w.oracle_point, w.oracle_quantiles)
            rows.append(base | {"arm": "process_optimum"} | score(w, oracle))
    return {"setting": setting, "rows": rows, "n_windows": len(windows)}


def paired_arm_test(df, setting: str, metric: str = "mase") -> dict:
    """Wilcoxon signed-rank on the covariate arm minus the univariate arm.

    Paired on the window, like :func:`timesfm_lab.bench.paired_win_rate`. The
    two arms are the *same* model on the *same* windows, so the pairing is
    exact and the only difference is the extra channels.
    """
    import pandas as pd
    from scipy.stats import wilcoxon

    sub = df[df.setting == setting]
    key = ["dataset", "series_id", "cutoff"]
    a = sub[sub.arm == "with_covariates"].set_index(key)[metric]
    b = sub[sub.arm == "univariate"].set_index(key)[metric]
    joined = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    if joined.empty:
        return {"setting": setting, "metric": metric, "n": 0}
    try:
        p = float(wilcoxon(joined.a, joined.b).pvalue)
    except ValueError:
        p = float("nan")
    return {
        "setting": setting,
        "metric": metric,
        "n": len(joined),
        "univariate": float(joined.b.mean()),
        "with_covariates": float(joined.a.mean()),
        "delta_pct": float(100.0 * (joined.a.mean() / joined.b.mean() - 1.0)),
        "win_rate": float((joined.a < joined.b).mean()),
        "p_value": p,
    }
