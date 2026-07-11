import math

import torch
from jp_llm_lab.calibration.probability import (
    brier_top1,
    ece_equal_mass,
    ece_equal_width,
    fit_temperature,
    metrics_at_temperature,
)


def test_perfectly_calibrated_has_low_ece():
    # confidence == accuracy in each region → ECE ≈ 0
    torch.manual_seed(0)
    n = 20000
    conf = torch.rand(n)
    correct = (torch.rand(n) < conf)  # P(correct)=conf by construction
    ece_w, _ = ece_equal_width(conf, correct, n_bins=15)
    ece_m, _ = ece_equal_mass(conf, correct, n_bins=15)
    assert ece_w < 0.03
    assert ece_m < 0.03


def test_overconfident_has_high_ece():
    n = 10000
    conf = torch.full((n,), 0.95)
    correct = torch.rand(n) < 0.5  # only 50% correct despite 0.95 confidence
    ece, _ = ece_equal_width(conf, correct)
    assert ece > 0.4


def test_temperature_scaling_improves_overconfident_nll():
    """Over-sharp logits → T>1 reduces NLL without changing argmax/accuracy."""
    torch.manual_seed(0)
    n, V = 4000, 20
    true = torch.randint(0, V, (n,))
    logits = torch.randn(n, V)
    logits[torch.arange(n), true] += 1.5
    logits = logits * 4.0  # deliberately over-sharp

    acc_before = (logits.argmax(-1) == true).float().mean()
    T = fit_temperature(logits, true)
    assert T > 1.0  # cooling needed
    before = metrics_at_temperature(logits, true, 1.0)
    after = metrics_at_temperature(logits, true, T)
    assert after["nll"] < before["nll"]
    # argmax (accuracy) unchanged by temperature scaling
    assert abs(after["accuracy"] - float(acc_before)) < 1e-6


def test_brier_bounds():
    conf = torch.tensor([0.9, 0.1, 0.6])
    correct = torch.tensor([True, False, True])
    b = brier_top1(conf, correct)
    assert 0.0 <= b <= 1.0


def test_calibration_split_separation():
    """Fitting T on calibration and evaluating on test must use DISJOINT data."""
    torch.manual_seed(1)
    n, V = 6000, 15
    true = torch.randint(0, V, (n,))
    logits = torch.randn(n, V) * 3
    logits[torch.arange(n), true] += 1.0
    calib_idx = torch.arange(0, n // 2)
    test_idx = torch.arange(n // 2, n)
    assert set(calib_idx.tolist()).isdisjoint(test_idx.tolist())
    T = fit_temperature(logits[calib_idx], true[calib_idx])
    m = metrics_at_temperature(logits[test_idx], true[test_idx], T)
    assert math.isfinite(m["nll"]) and m["T"] == T
