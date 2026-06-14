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


def plotly_decision_boundary(
    X,
    y,
    sizes=(2, 16, 16, 2),
    epochs: int = 120,
    n_frames: int = 10,
    lr: float = 0.3,
    seed: int = 0,
    grid_steps: int = 60,
    margin: float = 0.5,
    title="Decision boundary as training proceeds",
    slider_name="epoch",
):
    """Train a NumPy MLP and animate its decision boundary over epochs (slider).

    Each frame shows P(class 1) as a heatmap with the data overlaid; the slider
    steps through training epochs. Self-contained (fixed seed) so it renders the
    same way in the notebook and in the static portal.
    """
    import plotly.graph_objects as go

    from .metrics import softmax_np
    from .models import MLP
    from .training import train_numpy_mlp

    X = np.asarray(X, dtype=np.float32)
    y = np.asarray(y)
    x_min, x_max = float(X[:, 0].min() - margin), float(X[:, 0].max() + margin)
    y_min, y_max = float(X[:, 1].min() - margin), float(X[:, 1].max() + margin)
    xs = np.linspace(x_min, x_max, grid_steps)
    ys = np.linspace(y_min, y_max, grid_steps)
    xx, yy = np.meshgrid(xs, ys)
    grid = np.c_[xx.ravel(), yy.ravel()].astype(np.float32)

    model = MLP(list(sizes), activation="relu", task="classification", seed=seed)

    def prob_grid():
        return softmax_np(model.forward(grid), axis=1)[:, 1].reshape(xx.shape)

    checkpoints = np.unique(np.linspace(0, epochs, n_frames).astype(int))
    snapshots = [(0, prob_grid())]
    prev = 0
    for c in checkpoints:
        if c == 0:
            continue
        train_numpy_mlp(model, X, y, lr=lr, epochs=int(c - prev), batch_size=32, seed=seed)
        prev = int(c)
        snapshots.append((int(c), prob_grid()))

    def traces(z):
        return [
            go.Heatmap(
                x=xs, y=ys, z=z, colorscale="RdBu", zmin=0, zmax=1, opacity=0.85, showscale=False
            ),
            go.Scatter(
                x=list(X[:, 0]),
                y=list(X[:, 1]),
                mode="markers",
                marker={
                    "color": list(map(int, y)),
                    "colorscale": "RdBu",
                    "line": {"color": "black", "width": 0.5},
                    "size": 7,
                },
                showlegend=False,
            ),
        ]

    fig = go.Figure(
        data=traces(snapshots[0][1]),
        frames=[go.Frame(data=traces(z), name=str(ep)) for ep, z in snapshots],
    )
    steps = [
        {
            "args": [[str(ep)], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
            "label": str(ep),
            "method": "animate",
        }
        for ep, _ in snapshots
    ]
    fig.update_layout(
        sliders=[{"steps": steps, "currentvalue": {"prefix": f"{slider_name} = "}}],
        width=560,
        height=540,
        title=title,
        xaxis={"title": "x1", "range": [x_min, x_max]},
        yaxis={"title": "x2", "range": [y_min, y_max], "scaleanchor": "x"},
        margin={"l": 50, "r": 20, "t": 50, "b": 40},
    )
    return fig


def plotly_training_curves(
    histories,
    labels,
    key: str = "loss",
    n_frames: int | None = None,
    title="Training loss by configuration",
    slider_name="epoch",
):
    """Reveal training-loss curves for several configs as the slider grows the window.

    ``histories`` is a list of history dicts (each holding ``key``); ``labels``
    names each configuration. Watch which setup descends fastest. Built on top of
    :func:`plotly_curve_slider`-style frames with trailing values masked to NaN.
    """
    import plotly.graph_objects as go

    series = [np.asarray(h[key], dtype=float) for h in histories]
    length = min(len(s) for s in series)
    series = [s[:length] for s in series]
    epochs = np.arange(length)
    if n_frames is None:
        n_frames = min(length, 15)
    cutoffs = np.unique(np.linspace(max(1, length // n_frames), length, n_frames).astype(int))

    def traces(c):
        shown = epochs < c
        out = []
        for lab, s in zip(labels, series, strict=True):
            out.append(
                go.Scatter(
                    x=list(epochs), y=list(np.where(shown, s, np.nan)), mode="lines", name=lab
                )
            )
        return out

    fig = go.Figure(
        data=traces(int(cutoffs[0])),
        frames=[go.Frame(data=traces(int(c)), name=str(int(c))) for c in cutoffs],
    )
    steps = [
        {
            "args": [
                [str(int(c))],
                {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"},
            ],
            "label": str(int(c)),
            "method": "animate",
        }
        for c in cutoffs
    ]
    ymax = max(float(s.max()) for s in series)
    ymin = min(float(s.min()) for s in series)
    pad = 0.05 * (ymax - ymin + 1e-9)
    fig.update_layout(
        sliders=[{"steps": steps, "currentvalue": {"prefix": f"{slider_name} = "}}],
        width=720,
        height=450,
        title=title,
        xaxis={"title": "epoch"},
        yaxis={"title": key, "range": [ymin - pad, ymax + pad]},
        margin={"l": 60, "r": 20, "t": 50, "b": 40},
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


def plotly_activations(
    names=("relu", "leaky_relu", "sigmoid", "tanh"),
    x_range=(-5, 5),
    title="Activations and their derivatives",
):
    """Slider over activation functions, each with its derivative.

    Makes the vanishing-gradient story visible: sigmoid/tanh derivatives die
    away from 0, while ReLU keeps a constant slope on the positive side.
    """
    import plotly.graph_objects as go

    x = np.linspace(*x_range, 300)

    def fns(name):
        if name == "relu":
            return np.maximum(0, x), (x > 0).astype(float)
        if name == "leaky_relu":
            a = 0.1
            return np.where(x > 0, x, a * x), np.where(x > 0, 1.0, a)
        if name == "sigmoid":
            s = 1 / (1 + np.exp(-x))
            return s, s * (1 - s)
        t = np.tanh(x)
        return t, 1 - t**2

    def traces(name):
        f, df = fns(name)
        return [
            go.Scatter(x=list(x), y=list(f), mode="lines", name="f(x)"),
            go.Scatter(x=list(x), y=list(df), mode="lines", name="f'(x)", line={"dash": "dash"}),
        ]

    frames = [go.Frame(data=traces(nm), name=nm) for nm in names]
    fig = go.Figure(data=traces(names[0]), frames=frames)
    steps = [
        {
            "args": [[nm], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
            "label": nm,
            "method": "animate",
        }
        for nm in names
    ]
    fig.update_layout(
        sliders=[{"steps": steps, "currentvalue": {"prefix": "activation = "}}],
        xaxis_title="x",
        width=680,
        height=420,
        title=title,
        margin={"l": 50, "r": 20, "t": 50, "b": 40},
    )
    return fig


def plotly_hidden_unfolding(
    X=None,
    y=None,
    sizes=(2, 16, 16, 2),
    epochs: int = 220,
    n_frames: int = 10,
    lr: float = 0.3,
    seed: int = 0,
    title="Output space: a net untangles the classes",
):
    """Train a NumPy MLP and animate how its 2-D output logits separate classes.

    Reuses :class:`models.MLP` + :func:`training.train_numpy_mlp`. At epoch 0
    the two classes overlap; as training proceeds they drift into linearly
    separable blobs (the network 'unfolds' a problem that was not separable in
    the input plane).
    """
    import plotly.graph_objects as go

    from .datasets import make_circles_dataset
    from .models import MLP
    from .training import train_numpy_mlp

    if X is None:
        X, y = make_circles_dataset(n=240, seed=0)
    X = np.asarray(X, dtype=np.float32)
    y = np.asarray(y)
    model = MLP(list(sizes), activation="relu", task="classification", seed=seed)
    checkpoints = np.unique(np.linspace(0, epochs, n_frames).astype(int))
    snaps = [(0, model.forward(X))]
    prev = 0
    for c in checkpoints:
        if c == 0:
            continue
        train_numpy_mlp(model, X, y, lr=lr, epochs=int(c - prev), batch_size=32, seed=seed)
        prev = int(c)
        snaps.append((int(c), model.forward(X)))

    def traces(H):
        return [
            go.Scatter(
                x=list(H[:, 0]),
                y=list(H[:, 1]),
                mode="markers",
                marker={
                    "color": list(map(int, y)),
                    "colorscale": "RdBu",
                    "size": 6,
                    "line": {"color": "black", "width": 0.4},
                },
                showlegend=False,
            )
        ]

    frames = [go.Frame(data=traces(H), name=str(ep)) for ep, H in snaps]
    fig = go.Figure(data=traces(snaps[0][1]), frames=frames)
    steps = [
        {
            "args": [[str(ep)], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
            "label": str(ep),
            "method": "animate",
        }
        for ep, _ in snaps
    ]
    fig.update_layout(
        sliders=[{"steps": steps, "currentvalue": {"prefix": "epoch = "}}],
        xaxis_title="output logit 0",
        yaxis_title="output logit 1",
        width=560,
        height=520,
        title=title,
        margin={"l": 50, "r": 20, "t": 50, "b": 40},
    )
    return fig


def plotly_ssm_impulse(
    decays=(0.3, 0.6, 0.85, 0.95), n_steps: int = 40, title="Diagonal linear SSM: memory vs decay"
):
    """Impulse response of a 1-state diagonal linear SSM, slider over the decay.

    Reuses :func:`models.linear_ssm_scan`. The response is A_diag**t, so larger
    A_diag = longer memory — the intuition behind state-space sequence models.
    """
    import plotly.graph_objects as go

    from .models import linear_ssm_scan

    t = np.arange(n_steps)
    x = np.zeros(n_steps)
    x[0] = 1.0  # unit impulse

    def traces(a):
        y = linear_ssm_scan(x, np.array([a]), np.array([1.0]), np.array([1.0]))
        return [go.Scatter(x=list(t), y=list(y), mode="lines+markers", name="impulse response")]

    frames = [go.Frame(data=traces(a), name=f"{a:g}") for a in decays]
    fig = go.Figure(data=traces(decays[0]), frames=frames)
    steps = [
        {
            "args": [[f"{a:g}"], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
            "label": f"{a:g}",
            "method": "animate",
        }
        for a in decays
    ]
    fig.update_layout(
        sliders=[{"steps": steps, "currentvalue": {"prefix": "A_diag = "}}],
        xaxis_title="time step",
        yaxis_title="output y",
        width=680,
        height=420,
        title=title,
        margin={"l": 50, "r": 20, "t": 50, "b": 40},
    )
    return fig


def plotly_function_approx(n_units_list=(1, 2, 4, 8, 16, 32, 64), seed: int = 0, title=None):
    """Slider over the number of ReLU units fitting a fixed target curve.

    Random ReLU features ``relu(w x + b)`` are fit to the target by least
    squares; more units -> better fit. Demonstrates the universal approximation
    idea (any continuous function on a bounded interval is reachable). The slider
    label shows the training RMSE. Works in the static Jupyter Book HTML.
    """
    import plotly.graph_objects as go

    rng = np.random.default_rng(seed)
    x = np.linspace(-3, 3, 200)
    target = np.sin(1.5 * x) + 0.3 * x
    max_n = max(n_units_list)
    w = rng.uniform(-3, 3, max_n)
    b = rng.uniform(-4, 4, max_n)

    def fit(n):
        phi = np.maximum(0.0, np.outer(x, w[:n]) + b[:n])
        phi = np.column_stack([np.ones_like(x), phi])
        coef, *_ = np.linalg.lstsq(phi, target, rcond=None)
        return phi @ coef

    fits = [(n, fit(n)) for n in n_units_list]
    labels = [
        f"{n} units (RMSE={np.sqrt(np.mean((yh - target) ** 2)):.3f})" for n, yh in fits
    ]

    def traces(yhat):
        return [
            go.Scatter(x=list(x), y=list(target), mode="lines",
                       line={"color": "gray", "width": 2}, name="target f(x)"),
            go.Scatter(x=list(x), y=list(yhat), mode="lines",
                       line={"color": "#d62728", "width": 2}, name="ReLU net fit"),
        ]

    frames = [go.Frame(data=traces(yh), name=lab) for (_, yh), lab in zip(fits, labels, strict=True)]
    fig = go.Figure(data=traces(fits[0][1]), frames=frames)
    steps = [
        {"args": [[lab], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
         "label": lab, "method": "animate"}
        for lab in labels
    ]
    fig.update_layout(
        sliders=[{"steps": steps, "currentvalue": {"prefix": ""}}],
        width=720, height=440,
        title=title or "ReLU ユニット数を増やすと任意関数に近づく（万能近似）",
        xaxis={"title": "x"}, yaxis={"title": "y"},
        margin={"l": 60, "r": 20, "t": 50, "b": 40},
    )
    return fig


def plotly_softmax_temperature(tokens, logits, temperatures=(0.25, 0.5, 1.0, 2.0, 4.0), title=None):
    """Slider over softmax temperature applied to fixed next-token logits.

    Low temperature -> peaky (greedy) distribution; high temperature -> flat
    (more random) — the core knob behind LLM sampling. Works in static HTML.
    """
    import plotly.graph_objects as go

    from .metrics import softmax_np

    logits = np.asarray(logits, dtype=float)
    dists = [softmax_np(logits / t) for t in temperatures]

    def traces(p):
        return [go.Bar(x=list(tokens), y=list(p), marker={"color": "#1f77b4"})]

    frames = [go.Frame(data=traces(p), name=f"{t:g}") for p, t in zip(dists, temperatures, strict=True)]
    fig = go.Figure(data=traces(dists[2 if len(dists) > 2 else 0]), frames=frames)
    steps = [
        {"args": [[f"{t:g}"], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
         "label": f"{t:g}", "method": "animate"}
        for t in temperatures
    ]
    fig.update_layout(
        sliders=[{"steps": steps, "currentvalue": {"prefix": "temperature = "}}],
        width=640, height=420,
        title=title or "サンプリング温度で次トークン分布が尖る／平らになる",
        xaxis={"title": "token"}, yaxis={"title": "probability", "range": [0, 1]},
        margin={"l": 60, "r": 20, "t": 50, "b": 50},
    )
    return fig
