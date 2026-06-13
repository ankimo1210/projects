"""Tests for the CPU/GPU benchmark utilities (run on CPU; GPU optional)."""

import torch.nn as nn
from nn_textbook import benchmark


def test_available_devices_includes_cpu():
    devs = benchmark.available_devices()
    assert "cpu" in devs
    assert all(d in ("cpu", "cuda") for d in devs)


def test_device_label_cpu():
    assert benchmark.device_label("cpu") == "CPU"


def test_time_callable_returns_positive():
    counter = {"n": 0}

    def fn():
        counter["n"] += 1

    sec = benchmark.time_callable(fn, device="cpu", n_warmup=2, n_iters=5, n_repeats=3)
    assert sec >= 0.0
    assert counter["n"] == 2 + 3 * 5  # warmup + n_repeats * n_iters calls ran


def test_benchmark_matmul_cpu_structure():
    recs = benchmark.benchmark_matmul([32, 64], devices=["cpu"], n_iters=3)
    assert len(recs) == 2
    for r in recs:
        assert r["device"] == "cpu"
        assert r["size"] in (32, 64)
        assert r["ms"] >= 0.0


def test_benchmark_matmul_dtype():
    import torch

    recs = benchmark.benchmark_matmul([32], devices=["cpu"], n_iters=2, dtype=torch.float16)
    assert len(recs) == 1
    assert recs[0]["ms"] >= 0.0


def test_benchmark_training_step_cpu():
    def make_model():
        return nn.Sequential(nn.Flatten(), nn.Linear(16, 8), nn.ReLU(), nn.Linear(8, 3))

    recs = benchmark.benchmark_training_step(
        make_model,
        input_shape=(16,),
        n_classes=3,
        batch_sizes=[8, 16],
        devices=["cpu"],
        n_iters=2,
    )
    assert {r["batch_size"] for r in recs} == {8, 16}
    assert all(r["ms"] >= 0.0 for r in recs)


def test_speedup_table_cpu_only():
    recs = [
        {"device": "cpu", "size": 64, "ms": 1.0},
        {"device": "cpu", "size": 128, "ms": 4.0},
    ]
    table = benchmark.speedup_table(recs, x_key="size")
    assert [row["size"] for row in table] == [64, 128]
    assert table[0]["cpu_ms"] == 1.0
    assert "speedup" not in table[0]  # no GPU records -> no speedup column


def test_speedup_table_with_gpu():
    recs = [
        {"device": "cpu", "size": 64, "ms": 10.0},
        {"device": "cuda", "size": 64, "ms": 2.0},
    ]
    table = benchmark.speedup_table(recs, x_key="size")
    assert table[0]["speedup"] == 5.0
