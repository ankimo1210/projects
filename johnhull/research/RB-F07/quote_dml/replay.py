"""Independent NumPy evaluation of exported quote-DML comparison models.

Only saved arrays are consumed. Neither torch, hullkit, nor the training module
is imported. Input columns are curve coordinates, spot and maturity; returned
physical-risk columns are spot delta and the five rate derivatives.
"""

import numpy as np

_MODES = ("q_price", "theta_price", "theta_dml", "theta_quote_metric", "q_dml")


def _rows(values):
    x = np.asarray(values, dtype=float)
    if x.ndim != 2 or x.shape[1] != 7 or not len(x) or not np.isfinite(x).all():
        raise ValueError("finite nonempty [curve5,spot,maturity] rows required")
    if np.any(x[:, 5:] <= 0):
        raise ValueError("positive spot and maturity required")
    return x


def _array(values, shape, name):
    result = np.asarray(values, dtype=float)
    if result.shape != shape or not np.isfinite(result).all():
        raise ValueError(f"finite {name} array of shape {shape} required")
    return result


def _scales(exported, dimension):
    mean = _array(exported["feature_mean"], (dimension,), "feature mean")
    std = _array(exported["feature_std"], (dimension,), "feature scale")
    price_mean = float(exported["price_mean"])
    price_scale = float(exported["price_scale"])
    if (
        np.any(std <= 0)
        or not np.isfinite(price_mean)
        or not np.isfinite(price_scale)
        or price_scale <= 0
    ):
        raise ValueError("positive finite feature/price scales required")
    return mean, std, price_mean, price_scale


def nn_predict(exported, x, A):
    """Replay two tanh layers and their physical spot/native/quote derivatives.

    Linear weights use the export's ``[out,in]`` orientation. A has theta rows
    and quote columns: theta-mode gradients are transformed by A transpose.
    Maturity is an input but is not one of the six reported risk components.
    """
    if exported["kind"] != "nn" or exported["mode"] not in _MODES:
        raise ValueError("recognized NN kind and quote-DML mode required")
    x = _rows(x)
    a = _array(A, (len(x), 5, 5), "calibration Jacobian")
    mean, std, price_mean, price_scale = _scales(exported, 7)
    features = np.column_stack([x[:, :5], np.log(x[:, 5] / 100.0), np.log(x[:, 6])])
    hidden = (features - mean) / std
    activations = []
    weights = []
    for layer in range(3):
        weight = np.asarray(exported[f"layer{layer}_weight"], dtype=float)
        if (
            weight.ndim != 2
            or weight.shape[1] != hidden.shape[1]
            or not np.isfinite(weight).all()
            or not weight.shape[0]
        ):
            raise ValueError("finite dimensionally consistent linear weights required")
        bias = _array(exported[f"layer{layer}_bias"], (weight.shape[0],), "layer bias")
        hidden = hidden @ weight.T + bias
        weights.append(weight)
        if layer < 2:
            hidden = np.tanh(hidden)
            activations.append(hidden)
    if hidden.shape[1] != 1:
        raise ValueError("one price output required")
    price = price_mean + price_scale * hidden[:, 0]
    gradient = np.broadcast_to(weights[2][0], activations[1].shape).copy()
    for layer in (1, 0):
        gradient *= 1 - activations[layer] ** 2
        gradient = gradient @ weights[layer]
    gradient *= price_scale / std
    gradient[:, 5] /= x[:, 5]
    native = np.column_stack([gradient[:, 5], gradient[:, :5]])
    quoted = native.copy()
    if exported["mode"].startswith("theta"):
        quoted[:, 1:] = np.einsum("nij,ni->nj", a, native[:, 1:])
    return {"price": price, "g_native": native, "g_quote": quoted}


def ridge_predict(exported, dataset):
    """Replay reduced-polynomial prices and physical spot/quote derivatives.

    Reduced coordinates are log(S/100), integrated rate R(T), and log(T).
    Each monomial is differentiated by reducing its exponent, so zero-valued
    standardized features do not introduce a division by zero. ``a_quote``
    supplies dR/dq; all contracts are held fixed during these derivatives.
    """
    if exported["kind"] != "ridge":
        raise ValueError("reduced-regression export required")
    x = _rows(dataset["x_quote"])
    rate = _array(dataset["integrated_rate"], (len(x),), "integrated rate")
    a_quote = _array(dataset["a_quote"], (len(x), 5), "integrated-rate quote risk")
    mean, std, price_mean, price_scale = _scales(exported, 3)
    raw_powers = _array(exported["powers"], (20, 3), "monomial powers")
    if (
        np.any(raw_powers < 0)
        or np.any(raw_powers != np.floor(raw_powers))
        or np.any(raw_powers.sum(axis=1) > 3)
    ):
        raise ValueError("nonnegative integer total-degree≤3 monomial powers required")
    powers = raw_powers.astype(int)
    coefficients = _array(exported["coefficients"], (20,), "polynomial coefficients")
    u = np.column_stack([np.log(x[:, 5] / 100.0), rate, np.log(x[:, 6])])
    u = (u - mean) / std
    value = np.zeros(len(x))
    reduced_gradient = np.zeros((len(x), 2))
    for power, coefficient in zip(powers, coefficients, strict=True):
        value += coefficient * np.prod(u**power, axis=1)
        for coordinate in range(2):
            if power[coordinate]:
                derivative_power = power.copy()
                derivative_power[coordinate] -= 1
                reduced_gradient[:, coordinate] += (
                    coefficient * power[coordinate] * np.prod(u**derivative_power, axis=1)
                )
    reduced_gradient *= price_scale / std[:2]
    quote_gradient = np.column_stack(
        [
            reduced_gradient[:, 0] / x[:, 5],
            reduced_gradient[:, 1:2] * a_quote,
        ]
    )
    return {"price": price_mean + price_scale * value, "g_quote": quote_gradient}


def _error_summary(error, *, axis=None):
    absolute = np.abs(error)
    if not absolute.size:
        return {"mae": None, "rmse": None, "p99": None, "max": None}
    values = {
        "mae": absolute.mean(axis=axis),
        "rmse": np.sqrt(np.mean(error**2, axis=axis)),
        "p99": np.quantile(absolute, 0.99, axis=axis),
        "max": absolute.max(axis=axis),
    }
    return {key: np.asarray(value).tolist() for key, value in values.items()}


def _model_coordinates(identifier):
    method, separator, suffix = identifier.rpartition("_n")
    if not separator or not method:
        raise ValueError("model ID requires method_nSIZE[_sSEED]")
    parts = suffix.split("_s")
    if len(parts) > 2:
        raise ValueError("model ID requires one training seed at most")
    try:
        size = int(parts[0])
        seed = int(parts[1]) if len(parts) == 2 else None
    except ValueError as exc:
        raise ValueError("numeric model training size/seed required") from exc
    if size <= 0:
        raise ValueError("positive model training size required")
    return method, size, seed


def _grouped_price(error, masks):
    return {
        label: {"count": int(mask.sum()), **_error_summary(error[mask])}
        for label, mask in masks.items()
    }


def metrics(arrays, protocol):
    """Recompute quote-DML report metrics and paired market-group intervals.

    Prices, raw Greeks, held quantities, shock residuals and educational entry
    costs come from numeric arrays, never saved PASS/adoption flags. Quote RMS
    scales must agree across modes/seeds at the same training size. Intervals
    resample complete market groups and are conditional on the training seed;
    they do not represent uncertainty over future training seeds.

    The result is JSON-serializable. Coupon validity and model replay are checked
    by the experiment checker separately; this function summarizes their saved
    numeric outputs rather than treating a saved coupon/PASS flag as evidence.
    """
    x = _rows(arrays["test_x_quote"])
    n = len(x)
    true_price = _array(arrays["test_price"], (n,), "test price")
    true_risk = _array(arrays["test_g_quote"], (n, 6), "test quote risk")
    market_id = _array(arrays["test_market_id"], (n,), "test market ID")
    markets, inverse, counts = np.unique(market_id, return_inverse=True, return_counts=True)
    group_size = int(protocol.get("sampling", {}).get("contracts_per_market", 8))
    if group_size < 1 or np.any(counts != group_size):
        raise ValueError("every test market must contain the declared contract count")
    identifiers = np.asarray(arrays["model_ids"])
    if identifiers.ndim != 1 or not len(identifiers):
        raise ValueError("nonempty model ID vector required")
    identifiers = [str(identifier) for identifier in identifiers]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("unique model IDs required")
    labels = np.asarray(arrays["shock_labels"])
    if labels.ndim != 1 or not len(labels):
        raise ValueError("nonempty shock label vector required")
    labels = [str(label) for label in labels]
    if len(set(labels)) != len(labels):
        raise ValueError("unique shock labels required")
    reference_h = _array(arrays["reference_h"], (n, 6), "reference quantities")
    reference_residual = _array(
        arrays["reference_residual"], (n, len(labels)), "reference residual"
    )
    rate_cost = _array(arrays["cost_rate_bp"], (4,), "rate cost spreads")
    stock_cost = _array(arrays["cost_stock_bp"], (3,), "stock cost spreads")
    if np.any(rate_cost < 0) or np.any(stock_cost < 0):
        raise ValueError("nonnegative cost spreads required")
    strike = float(protocol["contract"]["strike"])
    if not np.isfinite(strike) or strike <= 0:
        raise ValueError("positive fixed strike required")
    ratio, maturity = x[:, 5] / strike, x[:, 6]
    maturity_masks = {
        "short": maturity <= 0.25,
        "medium": (maturity > 0.25) & (maturity <= 1.0),
        "long": maturity > 1.0,
    }
    moneyness_masks = {
        "otm": ratio < 0.95,
        "atm": (ratio >= 0.95) & (ratio <= 1.05),
        "itm": ratio > 1.05,
    }
    zero_bucket = np.abs(true_risk) < 1e-12
    result = {
        "models": {},
        "hypotheses": {"H1": [], "H2": []},
        "metadata": {
            "test_rows": n,
            "market_count": len(markets),
            "contracts_per_market": group_size,
            "risk_order": ["spot", "deposit6m", "fra6x12", "swap2y", "swap3y", "swap5y"],
            "risk_units": ["currency_per_spot"] + ["currency_per_rate_decimal"] * 5,
            "hedge_units": ["shares"] + ["contracts_of_1m_notional"] * 5,
            "normalized_risk_scale": "common quote RMS within each training size",
            "zero_bucket_threshold": 1e-12,
            "maturity_groups": "short T<=.25; medium .25<T<=1; long T>1",
            "moneyness_groups": "OTM S/K<.95; ATM .95<=S/K<=1.05; ITM S/K>1.05",
            "shock_labels": labels,
            "cost_rate_bp": rate_cost.tolist(),
            "cost_stock_bp": stock_cost.tolist(),
            "cost_axes": ["rate_bp", "stock_bp"],
        },
    }
    size_scales = {}
    cluster_mse = {}
    coordinates = {}
    for identifier in identifiers:
        method, size, seed = _model_coordinates(identifier)
        coordinates[identifier] = (method, size, seed)
        prefix = f"pred__{identifier}__"
        price = _array(arrays[prefix + "price"], (n,), identifier + " price")
        risk = _array(arrays[prefix + "g_quote"], (n, 6), identifier + " quote risk")
        quantity = _array(arrays[prefix + "h"], (n, 6), identifier + " quantities")
        residual = _array(arrays[prefix + "residual"], (n, len(labels)), identifier + " residual")
        cost = _array(arrays[prefix + "cost"], (n, 4, 3), identifier + " cost")
        scale = _array(arrays[prefix + "risk_scale"], (6,), identifier + " risk scale")
        if np.any(scale <= 0) or np.any(cost < 0):
            raise ValueError("positive risk RMS and nonnegative entry costs required")
        if size in size_scales and not np.allclose(scale, size_scales[size], atol=0.0, rtol=1e-12):
            raise ValueError("quote evaluation RMS differs between same-size comparison models")
        size_scales[size] = scale
        price_error, risk_error = price - true_price, risk - true_risk
        normalized = risk_error / scale
        normalized_summary = _error_summary(normalized)
        per_component = _error_summary(normalized, axis=0)
        for key in ("rmse", "p99", "max"):
            normalized_summary["component_" + key] = per_component[key]
        leakage = {
            "count": int(zero_bucket.sum()),
            "component_count": zero_bucket.sum(axis=0).tolist(),
            "by_component": [
                {
                    "count": int(zero_bucket[:, column].sum()),
                    **_error_summary(risk[zero_bucket[:, column], column]),
                }
                for column in range(6)
            ],
            **_error_summary(risk[zero_bucket]),
        }
        result["models"][identifier] = {
            "method": method,
            "training_size": size,
            "training_seed": seed,
            "price": _error_summary(price_error),
            "risk": _error_summary(risk_error, axis=0),
            "normalized_risk": normalized_summary,
            "risk_scale": scale.tolist(),
            "zero_bucket_leakage": leakage,
            "hedge_quantity_rmse": np.sqrt(np.mean((quantity - reference_h) ** 2, axis=0)).tolist(),
            "residual": {
                **_error_summary(residual),
                "by_shock": {
                    label: _error_summary(residual[:, column])
                    for column, label in enumerate(labels)
                },
            },
            "curvature_difference_rmse": float(
                np.sqrt(np.mean((residual - reference_residual) ** 2))
            ),
            "cost": {
                "mean": cost.mean(axis=0).tolist(),
                "p99": np.quantile(cost, 0.99, axis=0).tolist(),
            },
            "price_by_maturity": _grouped_price(price_error, maturity_masks),
            "price_by_moneyness": _grouped_price(price_error, moneyness_masks),
        }
        row_mse = np.mean(normalized**2, axis=1)
        cluster_mse[identifier] = np.bincount(inverse, weights=row_mse) / counts
    bootstrap = protocol.get("bootstrap", {})
    repeats = int(bootstrap.get("repeats", 2000))
    bootstrap_seed = int(bootstrap.get("seed", 20261010))
    confidence = float(bootstrap.get("confidence", 0.95))
    if repeats < 1 or not np.isclose(confidence, 0.95, atol=1e-12, rtol=0.0):
        raise ValueError("positive bootstrap repetitions and 95% confidence required")
    sampled = np.random.default_rng(bootstrap_seed).integers(
        len(markets), size=(repeats, len(markets))
    )
    result["metadata"]["bootstrap"] = {
        "unit": "market",
        "repeats": repeats,
        "seed": bootstrap_seed,
        "confidence": confidence,
        "conditional_on_training_seed": True,
        "statistic": "difference of square roots of mean group mean-squared normalized six-risk error",
    }
    for left, (method, size, seed) in coordinates.items():
        if method != "q_dml" or seed is None:
            continue
        for hypothesis, comparator in (("H1", "q_price"), ("H2", "theta_quote_metric")):
            right = f"{comparator}_n{size}_s{seed}"
            item = {"left": left, "right": right, "training_size": size, "training_seed": seed}
            if right not in cluster_mse:
                item["status"] = "missing_comparator"
            else:
                difference = np.sqrt(cluster_mse[left][sampled].mean(axis=1)) - np.sqrt(
                    cluster_mse[right][sampled].mean(axis=1)
                )
                item.update(
                    status="computed",
                    difference=float(
                        np.sqrt(cluster_mse[left].mean()) - np.sqrt(cluster_mse[right].mean())
                    ),
                    ci95=np.quantile(difference, [0.025, 0.975]).tolist(),
                    market_count=len(markets),
                )
            result["hypotheses"][hypothesis].append(item)
    return result
