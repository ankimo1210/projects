"""CPU vs GPU speed benchmarking utilities.

The main notebooks pin CPU for reproducible committed output. This module is
the exception: it measures wall-clock time on whatever devices are present so
the appendix notebook can show where a GPU helps (and where it does not).

Timings are hardware-specific. The helpers handle the two things people get
wrong when timing GPU code: a warmup phase (the first CUDA call pays one-time
costs) and ``torch.cuda.synchronize()`` (CUDA kernels are asynchronous, so a
naive timer would stop before the work finishes).
"""

from __future__ import annotations

import time


def available_devices() -> list[str]:
    """Devices to benchmark: always 'cpu', plus 'cuda' when a GPU is present."""
    import torch

    devices = ["cpu"]
    if torch.cuda.is_available():
        devices.append("cuda")
    return devices


def device_label(device: str) -> str:
    """Human-readable label, e.g. 'CPU' or 'GPU (NVIDIA GeForce RTX 5080)'."""
    import torch

    dev = torch.device(device)
    if dev.type == "cuda":
        return f"GPU ({torch.cuda.get_device_name(dev)})"
    return "CPU"


def time_callable(
    fn, *, device: str = "cpu", n_warmup: int = 3, n_iters: int = 20, n_repeats: int = 5
) -> float:
    """Seconds per call of ``fn`` (no args), with warmup and CUDA sync.

    Runs ``n_repeats`` trials of ``n_iters`` calls each and returns the **minimum**
    per-call time. The minimum is the standard robust estimator for a benchmark:
    external load (other processes) only ever adds time, so the fastest trial is
    the closest estimate of the uncontended cost. ``fn`` must run a self-contained
    op whose tensors already live on ``device``.
    """
    import torch

    is_cuda = torch.device(device).type == "cuda"
    for _ in range(n_warmup):
        fn()
    if is_cuda:
        torch.cuda.synchronize()
    best = float("inf")
    for _ in range(n_repeats):
        t0 = time.perf_counter()
        for _ in range(n_iters):
            fn()
        if is_cuda:
            torch.cuda.synchronize()
        best = min(best, (time.perf_counter() - t0) / n_iters)
    return best


def _make_matmul(a, b):
    """Bind the two operands so the timed closure is self-contained."""
    return lambda: a @ b


def _make_train_step(model, opt, x, y, loss_fn):
    """Bind everything a single forward+backward+step needs."""

    def step():
        opt.zero_grad()
        loss_fn(model(x), y).backward()
        opt.step()

    return step


def _warmup_device(dev):
    """Spin up the BLAS thread pool / CUDA context so the first timed size is
    not contaminated by one-time initialization cost."""
    import torch

    w = torch.randn(512, 512, device=dev)
    for _ in range(5):
        _ = w @ w
    if dev.type == "cuda":
        torch.cuda.synchronize()


def _iters_for_size(n: int) -> int:
    """Tiny ops finish in microseconds, so they need many repeats for a stable
    average; huge ops need only a few."""
    if n <= 512:
        return 200
    if n <= 2048:
        return 50
    return 20


def benchmark_matmul(sizes, devices=None, n_iters: int | None = None, dtype=None) -> list[dict]:
    """Time an n x n matrix multiply on each device and size.

    Each device is warmed up once before timing, and small sizes use more
    repeats (override the per-size count with ``n_iters``). ``dtype`` defaults
    to float32; pass e.g. torch.float16 to measure half precision. Returns a
    list of {'device', 'size', 'ms'} records (ms = milliseconds per call).
    """
    import torch

    devices = devices if devices is not None else available_devices()
    dtype = dtype if dtype is not None else torch.float32
    records = []
    for device in devices:
        dev = torch.device(device)
        _warmup_device(dev)
        for n in sizes:
            torch.manual_seed(0)
            a = torch.randn(n, n, device=dev, dtype=dtype)
            b = torch.randn(n, n, device=dev, dtype=dtype)
            matmul = _make_matmul(a, b)
            iters = n_iters if n_iters is not None else _iters_for_size(n)
            ms = 1000 * time_callable(matmul, device=device, n_iters=iters)
            records.append({"device": device, "size": int(n), "ms": ms})
    return records


def benchmark_training_step(
    make_model, input_shape, n_classes, batch_sizes, devices=None, n_iters: int = 10
) -> list[dict]:
    """Time one forward+backward+step of a model across batch sizes and devices.

    ``make_model`` is a zero-arg factory returning a fresh model. ``input_shape``
    is the per-sample shape (e.g. (1, 28, 28) for MNIST). Returns a list of
    {'device', 'batch_size', 'ms'} records.
    """
    import torch

    devices = devices if devices is not None else available_devices()
    loss_fn = torch.nn.CrossEntropyLoss()
    records = []
    for device in devices:
        dev = torch.device(device)
        for bs in batch_sizes:
            torch.manual_seed(0)
            model = make_model().to(dev)
            opt = torch.optim.Adam(model.parameters())
            x = torch.randn(bs, *input_shape, device=dev)
            y = torch.randint(0, n_classes, (bs,), device=dev)
            step = _make_train_step(model, opt, x, y, loss_fn)
            ms = 1000 * time_callable(step, device=device, n_iters=n_iters)
            records.append({"device": device, "batch_size": int(bs), "ms": ms})
    return records


def speedup_table(records, x_key: str):
    """Pivot benchmark records into a per-x speedup of GPU over CPU.

    Returns a list of {x_key, 'cpu_ms', 'gpu_ms', 'speedup'} (speedup omitted if
    there is no GPU). ``x_key`` is 'size' or 'batch_size'.
    """
    xs = sorted({r[x_key] for r in records})
    by = {(r["device"], r[x_key]): r["ms"] for r in records}
    has_gpu = any(r["device"] == "cuda" for r in records)
    out = []
    for x in xs:
        row = {x_key: x, "cpu_ms": by.get(("cpu", x))}
        if has_gpu:
            gpu_ms = by.get(("cuda", x))
            row["gpu_ms"] = gpu_ms
            row["speedup"] = (row["cpu_ms"] / gpu_ms) if (gpu_ms and row["cpu_ms"]) else None
        out.append(row)
    return out
