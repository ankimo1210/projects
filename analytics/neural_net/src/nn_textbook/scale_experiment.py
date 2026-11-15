"""Measure model capacity, accuracy and CPU/CUDA cost on cached Fashion-MNIST.

Only compact final metrics are written. Datasets are never downloaded and model
weights/checkpoints stay in memory. Run from the uv workspace root with -m.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import platform
import statistics
import time
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path

import numpy as np
import torch
from sklearn.model_selection import train_test_split
from torch import nn

from nn_textbook.benchmark import time_callable
from nn_textbook.datasets import DATA_ROOT, FASHION_CLASSES

MODELS = [
    {"id": "linear", "label": "Linear", "hidden": []},
    {"id": "mlp-16", "label": "MLP 16×1", "hidden": [16]},
    {"id": "mlp-128", "label": "MLP 128×2", "hidden": [128, 128]},
    {"id": "mlp-512", "label": "MLP 512×3", "hidden": [512, 512, 512]},
    {"id": "mlp-2048", "label": "MLP 2048×4", "hidden": [2048] * 4},
]
WORKSPACE = Path(__file__).resolve().parents[4]
DEFAULT_OUTPUT = WORKSPACE / "_data/analytics/neural_net/scale-comparison/latest.json"


@dataclass
class Batch:
    x: torch.Tensor
    y: torch.Tensor
    ids: list[int]
    name: str

    def to(self, device):
        return replace(self, x=self.x.to(device), y=self.y.to(device))


@dataclass
class Data:
    train: Batch
    validation: Batch
    test: Batch
    mean: float
    std: float
    fingerprint: str

    def to(self, device):
        return replace(
            self,
            train=self.train.to(device),
            validation=self.validation.to(device),
            test=self.test.to(device),
        )


def prepare_data(
    images, labels, test_images, test_labels, *, validation_per_class=1000, split_seed=42
):
    """Stratify official training data and fit scalar normalization on training only."""
    labels = labels.long().cpu()
    indices = np.arange(len(labels))
    n_classes = len(torch.unique(labels))
    train_ids, val_ids = train_test_split(
        indices,
        test_size=validation_per_class * n_classes,
        random_state=split_seed,
        stratify=labels.numpy(),
    )
    raw_train = images[train_ids].flatten(1).float() / 255
    mean, std = raw_train.mean().item(), raw_train.std(unbiased=False).item()
    if std <= 0:
        raise ValueError("Training images must have nonzero variance")
    train = Batch((raw_train - mean) / std, labels[train_ids], train_ids.tolist(), "train")
    val = Batch(
        (images[val_ids].flatten(1).float() / 255 - mean) / std,
        labels[val_ids],
        val_ids.tolist(),
        "validation",
    )
    test = Batch(
        (test_images.flatten(1).float() / 255 - mean) / std,
        test_labels.long().cpu(),
        list(range(len(test_labels))),
        "test",
    )
    fingerprint = hashlib.sha256(train_ids.tobytes() + val_ids.tobytes()).hexdigest()
    return Data(train, val, test, mean, std, fingerprint)


def load_cached_data(root=DATA_ROOT):
    from torchvision.datasets import FashionMNIST

    train = FashionMNIST(str(root), train=True, download=False)
    test = FashionMNIST(str(root), train=False, download=False)
    data = prepare_data(train.data, train.targets, test.data, test.targets)
    previews = []
    for label, name in enumerate(FASHION_CLASSES):
        i = torch.where(train.targets == label)[0][0].item()
        previews.append({"label": label, "name": name, "pixels": train.data[i].flatten().tolist()})
    raw = Path(root) / "FashionMNIST/raw"
    files = [
        "train-images-idx3-ubyte",
        "train-labels-idx1-ubyte",
        "t10k-images-idx3-ubyte",
        "t10k-labels-idx1-ubyte",
    ]
    hashes = {}
    for name in files:
        with (raw / name).open("rb") as stream:
            hashes[name] = hashlib.file_digest(stream, "sha256").hexdigest()
    return data, previews, hashes


def make_model(hidden, *, input_features=784, n_classes=10, seed=11):
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        sizes = [input_features, *hidden, n_classes]
        layers = []
        for i, (before, after) in enumerate(pairwise(sizes)):
            layers.append(nn.Linear(before, after))
            if i < len(sizes) - 2:
                layers.append(nn.ReLU())
        return nn.Sequential(*layers)


def parameter_count(model):
    return sum(p.numel() for p in model.parameters())


def synchronize(device):
    if torch.device(device).type == "cuda":
        torch.cuda.synchronize(device)


def evaluate(model, data, *, batch_size=2048):
    training = model.training
    model.eval()
    n_classes = model[-1].out_features
    loss = torch.zeros((), device=data.x.device)
    confusion = torch.zeros(n_classes * n_classes, dtype=torch.int64, device=data.x.device)
    with torch.no_grad():
        for start in range(0, len(data.x), batch_size):
            x, y = data.x[start : start + batch_size], data.y[start : start + batch_size]
            logits = model(x)
            loss += nn.functional.cross_entropy(logits, y, reduction="sum")
            confusion += torch.bincount(y * n_classes + logits.argmax(1), minlength=n_classes**2)
    matrix = confusion.reshape(n_classes, n_classes).cpu()
    correct = matrix.diag().sum().item()
    model.train(training)
    return {
        "loss": loss.item() / len(data.x),
        "accuracy": correct / len(data.x),
        "correct": correct,
        "n": len(data.x),
        "confusion": matrix.tolist(),
    }


def train_run(
    data,
    spec,
    *,
    seed=11,
    epochs=8,
    batch_size=512,
    device="cuda",
    lr=0.001,
    weight_decay=0.0001,
    on_epoch=None,
):
    """Train on one fixed split; select by validation loss, then evaluate test once."""
    if epochs < 1 or batch_size < 1:
        raise ValueError("epochs and batch_size must be positive")
    on_device = data.to(device)
    model = make_model(
        spec["hidden"],
        input_features=data.train.x.shape[1],
        n_classes=len(torch.unique(data.train.y)),
        seed=seed,
    ).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    generator = torch.Generator().manual_seed(seed)
    history = [
        {
            "epoch": 0,
            "elapsed_seconds": 0,
            "train": evaluate(model, on_device.train),
            "validation": evaluate(model, on_device.validation),
        }
    ]
    is_cuda = torch.device(device).type == "cuda"
    if is_cuda:
        torch.cuda.reset_peak_memory_stats(device)
    best_loss, best_epoch, best_state, best_validation = float("inf"), 0, None, None
    synchronize(device)
    start_time = time.perf_counter()
    for epoch in range(1, epochs + 1):
        model.train()
        order = torch.randperm(len(on_device.train.x), generator=generator).to(device)
        for start in range(0, len(order), batch_size):
            indices = order[start : start + batch_size]
            optimizer.zero_grad(set_to_none=True)
            loss = nn.functional.cross_entropy(
                model(on_device.train.x[indices]), on_device.train.y[indices]
            )
            loss.backward()
            optimizer.step()
        train_metrics = evaluate(model, on_device.train)
        validation_metrics = evaluate(model, on_device.validation)
        if validation_metrics["loss"] < best_loss:
            best_loss, best_epoch, best_validation = (
                validation_metrics["loss"],
                epoch,
                validation_metrics,
            )
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        synchronize(device)
        history.append(
            {
                "epoch": epoch,
                "elapsed_seconds": time.perf_counter() - start_time,
                "train": train_metrics,
                "validation": validation_metrics,
            }
        )
        if on_epoch:
            on_epoch(history[-1])
    fit_seconds = history[-1]["elapsed_seconds"]
    model.load_state_dict(best_state)
    test_metrics = evaluate(model, on_device.test)
    result = {
        "model_id": spec["id"],
        "seed": seed,
        "parameters": parameter_count(model),
        "best_epoch": best_epoch,
        "best_validation": best_validation,
        "test": test_metrics,
        "fit_seconds": fit_seconds,
        "history": history,
        "peak_allocated_bytes": torch.cuda.max_memory_allocated(device) if is_cuda else None,
        "peak_reserved_bytes": torch.cuda.max_memory_reserved(device) if is_cuda else None,
    }
    del optimizer, model, on_device, best_state
    gc.collect()
    if is_cuda:
        torch.cuda.empty_cache()
    return result


def measure_steps(data, spec, *, device, batch_size=512):
    """Resident-data forward/backward/Adam timing; excludes I/O and evaluation."""
    model = make_model(spec["hidden"]).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=0.0001)
    x, y = data.train.x[:batch_size].to(device), data.train.y[:batch_size].to(device)

    def step(model=model, optimizer=optimizer, x=x, y=y):
        optimizer.zero_grad(set_to_none=True)
        nn.functional.cross_entropy(model(x), y).backward()
        optimizer.step()

    seconds = time_callable(step, device=device, n_warmup=5, n_iters=10, n_repeats=3)
    del step, model, optimizer, x, y
    gc.collect()
    if device == "cuda":
        torch.cuda.empty_cache()
    return {
        "device": device,
        "batch_size": batch_size,
        "step_ms": seconds * 1000,
        "samples_per_second": batch_size / seconds,
        "warmup": 5,
        "repeats": 3,
        "steps_per_repeat": 10,
    }


def aggregate(runs):
    output = []
    for model_id in dict.fromkeys(row["model_id"] for row in runs):
        matching = [r for r in runs if r["model_id"] == model_id]
        accuracies = [r["test"]["accuracy"] for r in matching]
        memory = [
            r["peak_allocated_bytes"] for r in matching if r["peak_allocated_bytes"] is not None
        ]
        output.append(
            {
                "model_id": model_id,
                "seeds": len(matching),
                "test_accuracy_mean": statistics.mean(accuracies),
                "test_accuracy_std": statistics.stdev(accuracies) if len(accuracies) > 1 else 0,
                "fit_seconds_mean": statistics.mean(r["fit_seconds"] for r in matching),
                "peak_allocated_bytes": max(memory) if memory else None,
            }
        )
    return output


def hardware_info():
    cpu_name = next(
        (
            line.split(":", 1)[1].strip()
            for line in Path("/proc/cpuinfo").read_text().splitlines()
            if line.startswith("model name")
        ),
        platform.processor(),
    )
    return {
        "cpu": cpu_name,
        "cpu_threads": torch.get_num_threads(),
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "gpu_total_bytes": torch.cuda.get_device_properties(0).total_memory
        if torch.cuda.is_available()
        else None,
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "python": platform.python_version(),
        "platform": platform.system(),
        "float32_matmul_precision": torch.get_float32_matmul_precision(),
    }


def write_result(path, result):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2) + "\n")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DATA_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--models", nargs="+", choices=[s["id"] for s in MODELS], default=[s["id"] for s in MODELS]
    )
    parser.add_argument("--seeds", type=int, nargs="+", default=[11, 22, 33])
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--cpu-threads", type=int, default=4)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cuda")
    parser.add_argument("--skip-step-timing", action="store_true")
    args = parser.parse_args()
    if (
        args.epochs < 1
        or args.batch_size < 1
        or args.cpu_threads < 1
        or len(set(args.seeds)) != len(args.seeds)
    ):
        parser.error("epochs, batch-size, cpu-threads must be positive; seeds must be unique")
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    torch.set_num_threads(args.cpu_threads)
    torch.set_float32_matmul_precision("highest")
    torch.use_deterministic_algorithms(True)
    if args.device == "cuda" and not torch.cuda.is_available():
        parser.error("CUDA unavailable; use --device cpu")
    data, previews, hashes = load_cached_data(args.data_root)
    specs = [s for s in MODELS if s["id"] in args.models]
    result = {
        "schema_version": 1,
        "status": "running",
        "created_at": datetime.now(UTC).isoformat(),
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "hardware": hardware_info(),
        "config": {
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "seeds": args.seeds,
            "device": args.device,
            "optimizer": "Adam",
            "lr": 0.001,
            "weight_decay": 0.0001,
            "dtype": "float32",
            "checkpoint": "minimum validation loss, epochs 1..N",
            "split_seed": 42,
            "cpu_threads": args.cpu_threads,
        },
        "data": {
            "name": "Fashion-MNIST",
            "source_url": "https://github.com/zalandoresearch/fashion-mnist",
            "train": len(data.train.x),
            "validation": len(data.validation.x),
            "test": len(data.test.x),
            "mean": data.mean,
            "std": data.std,
            "split_sha256": data.fingerprint,
            "input_sha256": hashes,
            "classes": FASHION_CLASSES,
            "previews": previews,
        },
        "models": [],
        "runs": [],
        "summary": [],
    }
    write_result(args.output, result)
    for spec in specs:
        model_info = {
            **spec,
            "parameters": parameter_count(make_model(spec["hidden"])),
            "timings": [],
        }
        print(f"MODEL {spec['id']} params={model_info['parameters']:,}", flush=True)
        if not args.skip_step_timing:
            for device in ["cpu", *(["cuda"] if torch.cuda.is_available() else [])]:
                timing = measure_steps(data, spec, device=device, batch_size=args.batch_size)
                model_info["timings"].append(timing)
                print(f"  STEP {device}: {timing['step_ms']:.3f} ms", flush=True)
        result["models"].append(model_info)
        for seed in args.seeds:

            def report(row, seed=seed, model_id=spec["id"]):
                print(
                    f"  {model_id} seed={seed} epoch={row['epoch']} "
                    f"val={row['validation']['accuracy']:.4f} t={row['elapsed_seconds']:.1f}s",
                    flush=True,
                )

            run = train_run(
                data,
                spec,
                seed=seed,
                epochs=args.epochs,
                batch_size=args.batch_size,
                device=args.device,
                on_epoch=report,
            )
            result["runs"].append(run)
            result["summary"] = aggregate(result["runs"])
            write_result(args.output, result)
    result["status"] = "complete"
    write_result(args.output, result)
    print(f"COMPLETE {args.output} ({args.output.stat().st_size:,} bytes)", flush=True)


if __name__ == "__main__":
    main()
