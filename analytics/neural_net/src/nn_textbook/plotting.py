"""Shared plotting helpers (matplotlib).

Figure labels are kept in English so no Japanese font setup is needed; the
surrounding notebook prose carries the Japanese explanation.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

CMAP_PTS = "coolwarm"


def plot_2d_dataset(X, y, ax=None, title: str | None = None, s: int = 18):
    """Scatter a 2-D labeled dataset."""
    X = np.asarray(X)
    if ax is None:
        _, ax = plt.subplots(figsize=(5, 5))
    sc = ax.scatter(X[:, 0], X[:, 1], c=y, cmap=CMAP_PTS, s=s, edgecolors="k", linewidths=0.3)
    ax.set_aspect("equal")
    ax.grid(alpha=0.2)
    if title:
        ax.set_title(title)
    return ax, sc


def plot_decision_boundary(
    predict_fn, X, y, ax=None, title: str | None = None, steps: int = 250, margin: float = 0.5
):
    """Shade the predicted class over a grid, then overlay the data.

    predict_fn maps an array of points (M, 2) -> class labels (M,).
    """
    X = np.asarray(X)
    if ax is None:
        _, ax = plt.subplots(figsize=(5.5, 5))
    x_min, x_max = X[:, 0].min() - margin, X[:, 0].max() + margin
    y_min, y_max = X[:, 1].min() - margin, X[:, 1].max() + margin
    xx, yy = np.meshgrid(np.linspace(x_min, x_max, steps), np.linspace(y_min, y_max, steps))
    grid = np.c_[xx.ravel(), yy.ravel()].astype(np.float32)
    Z = np.asarray(predict_fn(grid)).reshape(xx.shape)
    ax.contourf(xx, yy, Z, alpha=0.3, cmap=CMAP_PTS, levels=max(1, int(Z.max())))
    ax.scatter(X[:, 0], X[:, 1], c=y, cmap=CMAP_PTS, s=16, edgecolors="k", linewidths=0.3)
    ax.set_aspect("equal")
    if title:
        ax.set_title(title)
    return ax


def plot_loss_curve(history, ax=None, keys=("loss", "train_loss", "val_loss")):
    """Plot whichever loss keys are present in a history dict."""
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 4))
    xs = history.get("epoch")
    for key in keys:
        if key in history and len(history[key]):
            ax.plot(xs if xs else range(len(history[key])), history[key], label=key)
    ax.set_xlabel("epoch")
    ax.set_ylabel("loss")
    ax.grid(alpha=0.3)
    ax.legend()
    return ax


def plot_activation_function(name: str = "relu", ax=None, x_range=(-5, 5)):
    """Plot an activation and its derivative side by side on one axis."""
    x = np.linspace(*x_range, 300)
    fns = {
        "relu": (np.maximum(0, x), (x > 0).astype(float)),
        "sigmoid": (1 / (1 + np.exp(-x)), None),
        "tanh": (np.tanh(x), 1 - np.tanh(x) ** 2),
    }
    f, df = fns[name]
    if df is None:
        s = 1 / (1 + np.exp(-x))
        df = s * (1 - s)
    if ax is None:
        _, ax = plt.subplots(figsize=(5.5, 4))
    ax.plot(x, f, label=f"{name}(x)", lw=2)
    ax.plot(x, df, "--", label=f"{name}'(x)", lw=1.5, alpha=0.8)
    ax.axhline(0, color="gray", lw=0.6)
    ax.axvline(0, color="gray", lw=0.6)
    ax.grid(alpha=0.3)
    ax.legend()
    return ax


def plot_gradient_field(grad_fn, x_range=(-2, 2), y_range=(-2, 2), n: int = 20, ax=None):
    """Quiver plot of a 2-D vector field grad_fn(points[M, 2]) -> (M, 2)."""
    if ax is None:
        _, ax = plt.subplots(figsize=(5.5, 5))
    xs = np.linspace(*x_range, n)
    ys = np.linspace(*y_range, n)
    XX, YY = np.meshgrid(xs, ys)
    pts = np.c_[XX.ravel(), YY.ravel()]
    G = np.asarray(grad_fn(pts))
    U = G[:, 0].reshape(XX.shape)
    V = G[:, 1].reshape(XX.shape)
    ax.quiver(XX, YY, U, V, np.hypot(U, V), cmap="viridis")
    ax.set_aspect("equal")
    return ax


def plot_hidden_representation(H, y, ax=None, title: str | None = None):
    """Scatter a 2-D hidden representation colored by label."""
    H = np.asarray(H)
    if ax is None:
        _, ax = plt.subplots(figsize=(5, 5))
    ax.scatter(H[:, 0], H[:, 1], c=y, cmap=CMAP_PTS, s=16, edgecolors="k", linewidths=0.3)
    ax.grid(alpha=0.2)
    if title:
        ax.set_title(title)
    return ax


def plot_confusion_matrix(cm, class_names=None, ax=None, cmap: str = "Blues"):
    """Heatmap of a confusion matrix with cell counts."""
    cm = np.asarray(cm)
    if ax is None:
        _, ax = plt.subplots(figsize=(5.5, 5))
    ax.imshow(cm, cmap=cmap)
    n = cm.shape[0]
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    if class_names is not None:
        ax.set_xticklabels(class_names, rotation=45, ha="right")
        ax.set_yticklabels(class_names)
    thresh = cm.max() / 2 if cm.max() else 0.5
    for i in range(n):
        for j in range(n):
            ax.text(
                j,
                i,
                int(cm[i, j]),
                ha="center",
                va="center",
                color="white" if cm[i, j] > thresh else "black",
                fontsize=8,
            )
    ax.set_xlabel("predicted")
    ax.set_ylabel("true")
    return ax


def plot_image_grid(images, labels=None, ncols: int = 8, cmap: str = "gray", titles=None):
    """Show a grid of (H, W) or (1, H, W) images."""
    imgs = [np.asarray(im).squeeze() for im in images]
    n = len(imgs)
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(1.4 * ncols, 1.4 * nrows))
    axes = np.atleast_1d(axes).ravel()
    for k, ax in enumerate(axes):
        if k < n:
            ax.imshow(imgs[k], cmap=cmap)
            if titles is not None:
                ax.set_title(str(titles[k]), fontsize=8)
            elif labels is not None:
                ax.set_title(str(labels[k]), fontsize=8)
        ax.axis("off")
    fig.tight_layout()
    return axes


def plot_attention_heatmap(attn, tokens=None, ax=None, title: str | None = None):
    """Heatmap of an attention matrix attn[query, key]."""
    attn = np.asarray(attn)
    if ax is None:
        _, ax = plt.subplots(figsize=(5.5, 5))
    im = ax.imshow(attn, cmap="viridis", aspect="auto")
    if tokens is not None:
        ax.set_xticks(range(len(tokens)))
        ax.set_yticks(range(len(tokens)))
        ax.set_xticklabels(tokens, rotation=90, fontsize=7)
        ax.set_yticklabels(tokens, fontsize=7)
    ax.set_xlabel("key")
    ax.set_ylabel("query")
    if title:
        ax.set_title(title)
    plt.colorbar(im, ax=ax, fraction=0.046)
    return ax


def plot_latent_space(Z, y, ax=None, title: str | None = None):
    """Scatter a 2-D latent space colored by label."""
    Z = np.asarray(Z)
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 5))
    sc = ax.scatter(Z[:, 0], Z[:, 1], c=y, cmap="tab10", s=8, alpha=0.6)
    ax.set_xlabel("z1")
    ax.set_ylabel("z2")
    if title:
        ax.set_title(title)
    plt.colorbar(sc, ax=ax, fraction=0.046)
    return ax


# ---------------------------------------------------------------------------
# Plotly interactives — these sliders also work in the static Jupyter Book HTML
# (unlike ipywidgets, which need a live kernel).
# ---------------------------------------------------------------------------


def plotly_image_slider(images, labels, title: str | None = None, slider_name: str = "step"):
    """A grayscale image with a slider stepping through ``images``.

    images: list of 2-D arrays (same shape), labels: one label per image.
    Works in exported HTML because the slider is client-side plotly JS.
    """
    import plotly.graph_objects as go

    frames_z = [np.asarray(im, dtype=float)[::-1] for im in images]  # flip so row 0 is on top
    fig = go.Figure(
        data=[go.Heatmap(z=frames_z[0], colorscale="gray", showscale=False)],
        frames=[
            go.Frame(data=[go.Heatmap(z=z, colorscale="gray", showscale=False)], name=str(lab))
            for z, lab in zip(frames_z, labels, strict=True)
        ],
    )
    steps = [
        {
            "args": [[str(lab)], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
            "label": str(lab),
            "method": "animate",
        }
        for lab in labels
    ]
    fig.update_layout(
        sliders=[{"steps": steps, "currentvalue": {"prefix": f"{slider_name} = "}}],
        width=420,
        height=460,
        title=title,
        xaxis={"visible": False},
        yaxis={"visible": False, "scaleanchor": "x"},
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
    )
    return fig


def plotly_attention_slider(tokens, scores, temperatures, title: str | None = None):
    """Attention heatmap with a slider over softmax temperature.

    scores: raw (T, T) similarity matrix; each frame shows softmax(scores / temp).
    """
    import plotly.graph_objects as go

    from .metrics import softmax_np

    scores = np.asarray(scores, dtype=float)
    mats = [softmax_np(scores / t, axis=1) for t in temperatures]
    axis = {"tickvals": list(range(len(tokens))), "ticktext": list(tokens)}
    fig = go.Figure(
        data=[go.Heatmap(z=mats[0], colorscale="Viridis", zmin=0, zmax=1)],
        frames=[
            go.Frame(data=[go.Heatmap(z=m, colorscale="Viridis", zmin=0, zmax=1)], name=f"{t:g}")
            for m, t in zip(mats, temperatures, strict=True)
        ],
    )
    steps = [
        {
            "args": [[f"{t:g}"], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
            "label": f"{t:g}",
            "method": "animate",
        }
        for t in temperatures
    ]
    fig.update_layout(
        sliders=[{"steps": steps, "currentvalue": {"prefix": "temperature = "}}],
        width=520,
        height=500,
        title=title,
        xaxis={**axis, "title": "key"},
        yaxis={**axis, "title": "query", "autorange": "reversed"},
        margin={"l": 60, "r": 20, "t": 50, "b": 60},
    )
    return fig


def plot_benchmark(records, x_key, ax=None, title=None, log_y=True):
    """Grouped bar chart of benchmark timings (ms) by device across an x axis.

    ``records`` is the list of {'device', x_key, 'ms'} dicts from benchmark.py.
    """
    devices = sorted({r["device"] for r in records})
    xs = sorted({r[x_key] for r in records})
    by = {(r["device"], r[x_key]): r["ms"] for r in records}
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 4.5))
    width = 0.8 / max(1, len(devices))
    colors = {"cpu": "#1f77b4", "cuda": "#d62728"}
    for k, dev in enumerate(devices):
        offsets = np.arange(len(xs)) + k * width
        heights = [by.get((dev, x), np.nan) for x in xs]
        ax.bar(offsets, heights, width=width, label=dev.upper(), color=colors.get(dev))
    ax.set_xticks(np.arange(len(xs)) + width * (len(devices) - 1) / 2)
    ax.set_xticklabels([str(x) for x in xs])
    ax.set_xlabel(x_key)
    ax.set_ylabel("time per call (ms)")
    if log_y:
        ax.set_yscale("log")
    ax.grid(alpha=0.3, axis="y", which="both")
    ax.legend()
    if title:
        ax.set_title(title)
    return ax


def plot_sequence_prediction(t, true, pred=None, ax=None, split_idx=None, title=None):
    """Plot a 1-D sequence, an optional forecast, and an optional train/test split."""
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 3.5))
    ax.plot(t, true, label="true", lw=1.5)
    if pred is not None:
        tp = t[-len(pred) :] if len(pred) < len(t) else t
        ax.plot(tp, pred, "--", label="prediction", lw=1.5)
    if split_idx is not None:
        ax.axvline(t[split_idx], color="gray", ls=":", label="train/test split")
    ax.grid(alpha=0.3)
    ax.legend()
    if title:
        ax.set_title(title)
    return ax
