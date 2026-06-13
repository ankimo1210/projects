"""Training utilities for both NumPy and PyTorch models."""

from __future__ import annotations

import numpy as np


def set_seed(seed: int = 0):
    """Seed Python, NumPy and (if present) torch for reproducible notebooks."""
    import random

    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass


def get_device(prefer_gpu: bool = True):
    """Return a torch device. Notebooks pin CPU for reproducible committed output."""
    import torch

    if prefer_gpu and torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


# ---------------------------------------------------------------------------
# NumPy training (SGD on the from-scratch MLP)
# ---------------------------------------------------------------------------


def train_numpy_mlp(
    model,
    X,
    y,
    lr: float = 0.1,
    epochs: int = 200,
    batch_size: int = 32,
    X_val=None,
    y_val=None,
    seed: int = 0,
    record_every: int = 1,
):
    """Mini-batch SGD for the NumPy ``MLP``.

    Returns a history dict with 'loss' (and 'val_acc' when validation is given).
    """
    rng = np.random.default_rng(seed)
    n = len(X)
    history = {"loss": [], "val_acc": [], "epoch": []}
    for epoch in range(epochs):
        perm = rng.permutation(n)
        epoch_loss = 0.0
        for start in range(0, n, batch_size):
            idx = perm[start : start + batch_size]
            loss = model.loss(X[idx], y[idx])
            model.backward()
            for param, grad in model.params_and_grads():
                param -= lr * grad  # in-place SGD step
            epoch_loss += loss * len(idx)
        if epoch % record_every == 0 or epoch == epochs - 1:
            history["epoch"].append(epoch)
            history["loss"].append(epoch_loss / n)
            if X_val is not None:
                history["val_acc"].append(float((model.predict(X_val) == y_val).mean()))
    return history


# ---------------------------------------------------------------------------
# PyTorch training
# ---------------------------------------------------------------------------


def train_torch(
    model,
    loader,
    *,
    loss_fn,
    optimizer,
    epochs: int = 5,
    device=None,
    val_loader=None,
    on_epoch=None,
    grad_clip: float | None = None,
):
    """Generic PyTorch training loop.

    loss_fn(model_output, targets) -> scalar. Returns a history dict. ``on_epoch``
    is an optional callback(epoch, model) for logging gate values, samples, etc.
    """
    import torch

    device = device or get_device()
    model.to(device)
    history = {"train_loss": [], "val_loss": [], "val_acc": []}
    for epoch in range(epochs):
        model.train()
        total = 0.0
        n = 0
        for xb, yb in loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            out = model(xb)
            loss = loss_fn(out, yb)
            loss.backward()
            if grad_clip is not None:
                torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
            optimizer.step()
            total += loss.item() * len(xb)
            n += len(xb)
        history["train_loss"].append(total / max(n, 1))
        if val_loader is not None:
            vl, va = evaluate_torch(model, val_loader, loss_fn, device)
            history["val_loss"].append(vl)
            history["val_acc"].append(va)
        if on_epoch is not None:
            on_epoch(epoch, model)
    return history


def evaluate_torch(model, loader, loss_fn, device=None):
    """Return (mean_loss, accuracy) over a loader. Accuracy assumes class logits."""
    import torch

    device = device or get_device()
    model.eval()
    total_loss = 0.0
    correct = 0
    n = 0
    with torch.no_grad():
        for xb, yb in loader:
            xb, yb = xb.to(device), yb.to(device)
            out = model(xb)
            total_loss += loss_fn(out, yb).item() * len(xb)
            if out.ndim == 2 and out.shape[1] > 1:
                correct += (out.argmax(1) == yb).sum().item()
            n += len(xb)
    acc = correct / max(n, 1)
    return total_loss / max(n, 1), acc
