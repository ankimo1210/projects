"""Train reproducible MNIST models and retain compact weights for the HTML lab.

Cached data only; no downloads. Run from the uv workspace root with -m.
The exported checkpoints are required for offline, interactive inference.
"""

from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import os
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import torch
from sklearn.model_selection import train_test_split
from torch import nn

from nn_textbook.datasets import DATA_ROOT
from nn_textbook.scale_experiment import hardware_info, synchronize, write_result

WORKSPACE = Path(__file__).resolve().parents[4]
DEFAULT_OUTPUT = WORKSPACE / "_data/analytics/neural_net/digit-lab/latest.json"
MODELS = [
    {"id": "cnn-small", "label": "CNN 小", "channels": [4, 8]},
    {"id": "cnn-medium", "label": "CNN 中", "channels": [12, 24]},
]


class DigitCNN(nn.Module):
    def __init__(self, channels):
        super().__init__()
        first, second = channels
        self.conv1 = nn.Conv2d(1, first, 5)
        self.conv2 = nn.Conv2d(first, second, 3)
        self.head = nn.Linear(second * 25, 10)

    def features(self, x):
        first = self.conv1(x).relu()
        pooled_first = nn.functional.max_pool2d(first, 2)
        second = self.conv2(pooled_first).relu()
        pooled_second = nn.functional.max_pool2d(second, 2)
        return first, pooled_first, second, pooled_second

    def forward(self, x):
        return self.head(self.features(x)[-1].flatten(1))


def encode(values):
    array = values.detach().cpu().contiguous().numpy().astype("<f4")
    return base64.b64encode(array.tobytes()).decode("ascii")


def pack_weights(model):
    return {name: encode(value) for name, value in model.state_dict().items()}


def prepare_data(images, labels, test_images, test_labels, *, validation_size=10_000):
    ids = np.arange(len(labels), dtype=np.int64)
    train_ids, val_ids = train_test_split(
        ids, test_size=validation_size, random_state=42, stratify=labels.numpy()
    )

    def batch(raw, targets, indices):
        return {
            "x": raw[indices].reshape(-1, 1, 28, 28).float() / 255,
            "y": targets[indices].long(),
            "ids": indices.tolist(),
        }

    return {
        "train": batch(images, labels, train_ids),
        "validation": batch(images, labels, val_ids),
        "test": batch(test_images, test_labels, np.arange(len(test_labels))),
        "split_sha256": hashlib.sha256(train_ids.tobytes() + val_ids.tobytes()).hexdigest(),
    }


def evaluate(model, batch, *, batch_size=1024):
    matrix = torch.zeros(100, dtype=torch.int64, device=batch["x"].device)
    loss = torch.zeros((), device=batch["x"].device)
    with torch.no_grad():
        for start in range(0, len(batch["y"]), batch_size):
            x, y = batch["x"][start : start + batch_size], batch["y"][start : start + batch_size]
            logits = model(x)
            loss += nn.functional.cross_entropy(logits, y, reduction="sum")
            matrix += torch.bincount(y * 10 + logits.argmax(1), minlength=100)
    confusion = matrix.reshape(10, 10).cpu()
    n = len(batch["y"])
    correct = confusion.diag().sum().item()
    return {
        "loss": loss.item() / n,
        "accuracy": correct / n,
        "correct": correct,
        "n": n,
        "confusion": confusion.tolist(),
    }


def train_model(data, spec, *, epochs=8, seed=11, batch_size=256, device="cuda"):
    """Only train updates weights; only validation selects; test is evaluated once."""
    torch.manual_seed(seed)
    channels = spec.get("channels")
    model = (
        DigitCNN(channels) if channels else nn.Sequential(nn.Flatten(), nn.Linear(784, 10))
    ).to(device)
    batches = {
        key: {"x": data[key]["x"].to(device), "y": data[key]["y"].to(device)}
        for key in ["train", "validation", "test"]
    }
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    generator = torch.Generator().manual_seed(seed)
    history = []
    best_loss, best_epoch, best_state = float("inf"), None, None
    if device == "cuda":
        torch.cuda.reset_peak_memory_stats()
    started = None
    for epoch in range(epochs + 1):
        update = None
        if epoch:
            order = torch.randperm(len(batches["train"]["y"]), generator=generator).to(device)
            for start in range(0, len(order), batch_size):
                indices = order[start : start + batch_size]
                x, y = batches["train"]["x"][indices], batches["train"]["y"][indices]
                last = channels and start + batch_size >= len(order)
                optimizer.zero_grad(set_to_none=True)
                loss = nn.functional.cross_entropy(model(x), y)
                loss.backward()
                if last:
                    original_ids = np.array(data["train"]["ids"], dtype="<i8")
                    batch_ids = original_ids[indices.cpu().numpy()]
                    update = {
                        "batch_size": len(indices),
                        "batch_ids_sha256": hashlib.sha256(batch_ids.tobytes()).hexdigest(),
                        "loss_before": loss.item(),
                        "before": encode(model.conv1.weight),
                        "gradient": encode(model.conv1.weight.grad),
                        "bias_before": encode(model.conv1.bias),
                        "bias_gradient": encode(model.conv1.bias.grad),
                    }
                optimizer.step()
                if last:
                    with torch.no_grad():
                        update["loss_after"] = nn.functional.cross_entropy(model(x), y).item()
                    update.update(
                        after=encode(model.conv1.weight),
                        bias_after=encode(model.conv1.bias),
                        optimizer_step=int(optimizer.state[model.conv1.weight]["step"].item()),
                    )
        train = evaluate(model, batches["train"])
        validation = evaluate(model, batches["validation"])
        if epoch and validation["loss"] < best_loss:
            best_loss, best_epoch = validation["loss"], epoch
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        synchronize(device)
        row = {
            "epoch": epoch,
            "elapsed_seconds": time.perf_counter() - started if started else 0,
            "train": train,
            "validation": validation,
        }
        if channels:
            row.update(weights=pack_weights(model), update=update)
        if started is not None:
            row["elapsed_seconds"] = time.perf_counter() - started
        history.append(row)
        print(
            f"{spec['id']} epoch {epoch}/{epochs}: "
            f"validation {validation['accuracy']:.2%}, CE {validation['loss']:.4f}",
            flush=True,
        )
        if started is None:
            synchronize(device)
            started = time.perf_counter()
    model.load_state_dict(best_state)
    result = {
        **spec,
        "parameters": sum(p.numel() for p in model.parameters()),
        "seed": seed,
        "best_epoch": best_epoch,
        "history": history,
        "test": evaluate(model, batches["test"]),
        "fit_seconds": history[-1]["elapsed_seconds"],
        "peak_allocated_bytes": torch.cuda.max_memory_allocated() if device == "cuda" else None,
    }
    return result, model, batches["validation"]


def reference(model, batch, index):
    """Use float64 on CPU to match JavaScript, including maxpool subgradients.

    Float32 rounding can pick a different member of an almost tied maxpool.
    Training still uses float32; this oracle uses the identical learned weights.
    """
    original = batch["x"][index : index + 1].detach()
    with torch.no_grad():
        training_logits = model(original)[0].cpu().tolist()
    oracle = copy.deepcopy(model).cpu().double()
    x = ((original.cpu() * 255).round().double() / 255).requires_grad_(True)
    logits = oracle(x)
    target = int(logits.argmax(1).item())
    logits[0, target].backward()
    with torch.no_grad():
        features = oracle.features(x)
    return {
        "class": target,
        "precision": "float64 CPU; identical float32 weights and exact pixel/255",
        "training_logits": training_logits,
        "logits": logits[0].detach().cpu().tolist(),
        "probabilities": logits.softmax(1)[0].detach().cpu().tolist(),
        "features": [encode(values[0]) for values in features],
        "input_gradient": encode(x.grad[0]),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cuda")
    args = parser.parse_args()
    if args.epochs < 1:
        parser.error("epochs must be positive")
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.fp32_precision = "ieee"
    torch.backends.cudnn.conv.fp32_precision = "ieee"
    torch.use_deterministic_algorithms(True)
    from torchvision.datasets import MNIST

    raw_train = MNIST(str(DATA_ROOT), train=True, download=False)
    raw_test = MNIST(str(DATA_ROOT), train=False, download=False)
    data = prepare_data(raw_train.data, raw_train.targets, raw_test.data, raw_test.targets)
    hashes = {}
    for name in [
        "train-images-idx3-ubyte",
        "train-labels-idx1-ubyte",
        "t10k-images-idx3-ubyte",
        "t10k-labels-idx1-ubyte",
    ]:
        with (Path(DATA_ROOT) / "MNIST/raw" / name).open("rb") as stream:
            hashes[name] = hashlib.file_digest(stream, "sha256").hexdigest()
    run_config = {"epochs": args.epochs, "device": args.device}
    baseline, baseline_model, baseline_validation = train_model(
        data, {"id": "linear", "label": "線形分類器"}, **run_config
    )
    del baseline_model, baseline_validation
    results, selected_indices = [], []
    for label in range(10):
        selected_indices.extend(torch.where(data["validation"]["y"] == label)[0][:3].tolist())
    for spec in MODELS:
        result, model, validation = train_model(data, spec, **run_config)
        result["verification"] = {
            "sample_id": selected_indices[0],
            **reference(model, validation, selected_indices[0]),
        }
        errors = []
        with torch.no_grad():
            for start in range(0, len(validation["y"]), 1024):
                predicted = model(validation["x"][start : start + 1024]).argmax(1)
                errors.extend(
                    (torch.where(predicted != validation["y"][start : start + 1024])[0] + start)
                    .cpu()
                    .tolist()
                )
        result["error_ids"] = errors[:12]
        selected_indices.extend(errors[:12])
        results.append(result)
        del model, validation
        if args.device == "cuda":
            torch.cuda.empty_cache()
    examples = []
    for index in dict.fromkeys(selected_indices):
        original = data["validation"]["ids"][index]
        examples.append(
            {
                "id": index,
                "source_id": original,
                "label": int(data["validation"]["y"][index]),
                "pixels": base64.b64encode(raw_train.data[original].numpy().tobytes()).decode(
                    "ascii"
                ),
            }
        )
    result = {
        "schema_version": 1,
        "status": "complete",
        "created_at": datetime.now(UTC).isoformat(),
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "hardware": hardware_info(),
        "config": {
            "epochs": args.epochs,
            "seed": 11,
            "split_seed": 42,
            "batch_size": 256,
            "lr": 0.001,
            "optimizer": "Adam",
            "weight_decay": 0,
            "device": args.device,
            "normalization": "pixel / 255",
            "matmul_precision": torch.backends.cuda.matmul.fp32_precision,
            "convolution_precision": torch.backends.cudnn.conv.fp32_precision,
            "dtype": "float32",
        },
        "data": {
            "train": 50_000,
            "validation": 10_000,
            "test": 10_000,
            "split_sha256": data["split_sha256"],
            "input_sha256": hashes,
            "source": "MNIST (torchvision cache, download=False)",
            "examples": examples,
        },
        "baseline": baseline,
        "models": results,
    }
    write_result(args.output, result)
    print(f"Complete: {len(results)} CNNs + linear baseline; {args.output.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
