"""Shared plotting helpers.

Matplotlib figures use English labels (no Japanese font setup needed); the
notebook prose carries the Japanese explanation. The ``plotly_*`` functions build
slider interactives that — unlike ipywidgets — keep working in the exported
static Jupyter Book HTML, so they are the book's primary interactive surface.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

CMAP_PTS = "coolwarm"


# ---------------------------------------------------------------------------
# Splits
# ---------------------------------------------------------------------------


def plot_train_test_split(X, train_idx, test_idx, ax=None, title: str | None = None):
    """Scatter a 2-D dataset coloured by whether each point is train or test."""
    X = np.asarray(X)
    if ax is None:
        _, ax = plt.subplots(figsize=(5.5, 5))
    ax.scatter(X[train_idx, 0], X[train_idx, 1], c="#1f77b4", s=18, label="train", alpha=0.7)
    ax.scatter(X[test_idx, 0], X[test_idx, 1], c="#d62728", s=22, marker="^", label="test")
    ax.legend()
    ax.grid(alpha=0.2)
    ax.set_title(title or "Train / test split")
    return ax


def plot_time_series_split(n_samples: int, n_splits: int = 5, ax=None):
    """Visualise forward-chaining time-series CV folds as stacked index bars."""
    from sklearn.model_selection import TimeSeriesSplit

    if ax is None:
        _, ax = plt.subplots(figsize=(8, 0.6 * n_splits + 1))
    tscv = TimeSeriesSplit(n_splits=n_splits)
    for i, (tr, te) in enumerate(tscv.split(np.zeros(n_samples))):
        ax.scatter(tr, [i] * len(tr), c="#1f77b4", marker="_", s=40, linewidths=6)
        ax.scatter(te, [i] * len(te), c="#d62728", marker="_", s=40, linewidths=6)
    ax.set_xlabel("time index")
    ax.set_ylabel("CV fold")
    ax.set_yticks(range(n_splits))
    ax.set_title("TimeSeriesSplit: test is always in the future (blue=train, red=test)")
    return ax


# ---------------------------------------------------------------------------
# Decision boundaries / fits
# ---------------------------------------------------------------------------


def plot_decision_boundary(
    predict_fn, X, y, ax=None, title: str | None = None, steps: int = 300, margin: float = 0.5
):
    """Shade the predicted class over a grid, then overlay the data.

    ``predict_fn`` maps points (M, 2) -> class labels (M,).
    """
    X = np.asarray(X)
    if ax is None:
        _, ax = plt.subplots(figsize=(5.5, 5))
    x_min, x_max = X[:, 0].min() - margin, X[:, 0].max() + margin
    y_min, y_max = X[:, 1].min() - margin, X[:, 1].max() + margin
    xx, yy = np.meshgrid(np.linspace(x_min, x_max, steps), np.linspace(y_min, y_max, steps))
    grid = np.c_[xx.ravel(), yy.ravel()]
    Z = np.asarray(predict_fn(grid)).reshape(xx.shape)
    ax.contourf(xx, yy, Z, alpha=0.3, cmap=CMAP_PTS, levels=max(1, int(np.max(Z))))
    ax.scatter(X[:, 0], X[:, 1], c=y, cmap=CMAP_PTS, s=16, edgecolors="k", linewidths=0.3)
    if title:
        ax.set_title(title)
    return ax


def plot_regression_fit(x, y, predict_fn=None, ax=None, title: str | None = None):
    """Scatter 1-D (x, y) and overlay a fitted curve from ``predict_fn(grid)``."""
    x = np.asarray(x).ravel()
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 4))
    ax.scatter(x, y, s=18, alpha=0.6, label="data", color="#444")
    if predict_fn is not None:
        grid = np.linspace(x.min(), x.max(), 300)[:, None]
        ax.plot(grid.ravel(), predict_fn(grid), color="#d62728", lw=2, label="model")
        ax.legend()
    ax.grid(alpha=0.3)
    if title:
        ax.set_title(title)
    return ax


# ---------------------------------------------------------------------------
# Learning / validation curves (model selection)
# ---------------------------------------------------------------------------


def plot_learning_curve(estimator, X, y, ax=None, cv: int = 5, scoring=None, n_points: int = 6):
    """Train/validation score vs training-set size (diagnoses bias vs variance)."""
    from sklearn.model_selection import learning_curve

    if ax is None:
        _, ax = plt.subplots(figsize=(6, 4))
    sizes, train, val = learning_curve(
        estimator, X, y, cv=cv, scoring=scoring, train_sizes=np.linspace(0.1, 1.0, n_points)
    )
    ax.plot(sizes, train.mean(axis=1), "o-", label="train", color="#1f77b4")
    ax.plot(sizes, val.mean(axis=1), "o-", label="validation", color="#d62728")
    ax.fill_between(
        sizes, val.mean(1) - val.std(1), val.mean(1) + val.std(1), alpha=0.15, color="#d62728"
    )
    ax.set_xlabel("training examples")
    ax.set_ylabel(scoring or "score")
    ax.grid(alpha=0.3)
    ax.legend()
    ax.set_title("Learning curve")
    return ax


def plot_validation_curve(
    estimator,
    X,
    y,
    param_name: str,
    param_range,
    ax=None,
    cv: int = 5,
    scoring=None,
    logx: bool = False,
):
    """Train/validation score vs one hyper-parameter (the over/underfit U-curve)."""
    from sklearn.model_selection import validation_curve

    if ax is None:
        _, ax = plt.subplots(figsize=(6, 4))
    train, val = validation_curve(
        estimator, X, y, param_name=param_name, param_range=param_range, cv=cv, scoring=scoring
    )
    xs = list(param_range)
    ax.plot(xs, train.mean(axis=1), "o-", label="train", color="#1f77b4")
    ax.plot(xs, val.mean(axis=1), "o-", label="validation", color="#d62728")
    if logx:
        ax.set_xscale("log")
    ax.set_xlabel(param_name)
    ax.set_ylabel(scoring or "score")
    ax.grid(alpha=0.3)
    ax.legend()
    ax.set_title(f"Validation curve over {param_name}")
    return ax


# ---------------------------------------------------------------------------
# Classification diagnostics
# ---------------------------------------------------------------------------


def plot_confusion_matrix(cm, class_names=None, ax=None, cmap: str = "Blues"):
    """Heatmap of a confusion matrix with the cell counts written in."""
    cm = np.asarray(cm)
    if ax is None:
        _, ax = plt.subplots(figsize=(5, 4.5))
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
                fontsize=9,
            )
    ax.set_xlabel("predicted")
    ax.set_ylabel("true")
    return ax


def plot_roc_curve(y_true, y_score, ax=None, label: str | None = None):
    """ROC curve with its AUC; the diagonal is a random classifier."""
    from sklearn.metrics import roc_auc_score, roc_curve

    if ax is None:
        _, ax = plt.subplots(figsize=(5, 5))
    fpr, tpr, _ = roc_curve(y_true, y_score)
    auc = roc_auc_score(y_true, y_score)
    ax.plot(fpr, tpr, lw=2, label=f"{label + ' ' if label else ''}AUC = {auc:.3f}")
    ax.plot([0, 1], [0, 1], "--", color="gray", lw=1, label="random")
    ax.set_xlabel("false positive rate")
    ax.set_ylabel("true positive rate")
    ax.set_title("ROC curve")
    ax.legend()
    ax.grid(alpha=0.3)
    return ax


def plot_precision_recall_curve(y_true, y_score, ax=None, label: str | None = None):
    """Precision-recall curve with its average precision (PR-AUC)."""
    from sklearn.metrics import average_precision_score, precision_recall_curve

    if ax is None:
        _, ax = plt.subplots(figsize=(5, 5))
    prec, rec, _ = precision_recall_curve(y_true, y_score)
    ap = average_precision_score(y_true, y_score)
    base = float(np.mean(y_true))
    ax.plot(rec, prec, lw=2, label=f"{label + ' ' if label else ''}AP = {ap:.3f}")
    ax.axhline(base, ls="--", color="gray", lw=1, label=f"baseline (prevalence {base:.2f})")
    ax.set_xlabel("recall")
    ax.set_ylabel("precision")
    ax.set_title("Precision-recall curve")
    ax.legend()
    ax.grid(alpha=0.3)
    return ax


def plot_calibration_curve(y_true, y_prob, ax=None, n_bins: int = 10, label: str | None = None):
    """Reliability diagram: predicted probability vs observed frequency."""
    from sklearn.calibration import calibration_curve

    if ax is None:
        _, ax = plt.subplots(figsize=(5, 5))
    frac_pos, mean_pred = calibration_curve(y_true, y_prob, n_bins=n_bins, strategy="quantile")
    ax.plot(mean_pred, frac_pos, "o-", lw=2, label=label or "model")
    ax.plot([0, 1], [0, 1], "--", color="gray", lw=1, label="perfectly calibrated")
    ax.set_xlabel("mean predicted probability")
    ax.set_ylabel("observed frequency")
    ax.set_title("Calibration curve")
    ax.legend()
    ax.grid(alpha=0.3)
    return ax


# ---------------------------------------------------------------------------
# Importance / interpretation
# ---------------------------------------------------------------------------


def plot_feature_importance(
    names, importances, ax=None, title: str = "Feature importance", top: int | None = None
):
    """Horizontal bar chart of feature importances (or |coefficients|), sorted."""
    names = np.asarray(names)
    importances = np.asarray(importances, dtype=float)
    order = np.argsort(importances)
    if top is not None:
        order = order[-top:]
    if ax is None:
        _, ax = plt.subplots(figsize=(6, max(3, 0.35 * len(order))))
    ax.barh(range(len(order)), importances[order], color="#1f77b4")
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(names[order])
    ax.set_xlabel("importance")
    ax.set_title(title)
    ax.grid(alpha=0.3, axis="x")
    return ax


def plot_permutation_importance(result, names, ax=None, top: int | None = None):
    """Box-style bar chart from a scikit-learn ``permutation_importance`` result."""
    names = np.asarray(names)
    means = result.importances_mean
    stds = result.importances_std
    order = np.argsort(means)
    if top is not None:
        order = order[-top:]
    if ax is None:
        _, ax = plt.subplots(figsize=(6, max(3, 0.35 * len(order))))
    ax.barh(range(len(order)), means[order], xerr=stds[order], color="#2ca02c")
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(names[order])
    ax.set_xlabel("drop in score when shuffled")
    ax.set_title("Permutation importance")
    ax.grid(alpha=0.3, axis="x")
    return ax


def plot_partial_dependence(estimator, X, features, ax=None, kind: str = "average"):
    """Partial-dependence (and optionally ICE) plot via scikit-learn's display."""
    from sklearn.inspection import PartialDependenceDisplay

    return PartialDependenceDisplay.from_estimator(estimator, X, features, ax=ax, kind=kind)


# ---------------------------------------------------------------------------
# Unsupervised
# ---------------------------------------------------------------------------


def plot_pca_projection(X, y=None, ax=None, title: str = "PCA projection"):
    """Fit a 2-component PCA and scatter the projection (coloured by ``y`` if given)."""
    from sklearn.decomposition import PCA

    if ax is None:
        _, ax = plt.subplots(figsize=(6, 5))
    Z = PCA(n_components=2, random_state=0).fit_transform(np.asarray(X))
    sc = ax.scatter(Z[:, 0], Z[:, 1], c=y, cmap="tab10", s=14, alpha=0.7)
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.set_title(title)
    if y is not None:
        plt.colorbar(sc, ax=ax, fraction=0.046)
    return ax


def plot_cluster_assignments(X, labels, centers=None, ax=None, title: str = "Clusters"):
    """Scatter 2-D points coloured by cluster label, optionally marking centroids."""
    X = np.asarray(X)
    if ax is None:
        _, ax = plt.subplots(figsize=(5.5, 5))
    ax.scatter(X[:, 0], X[:, 1], c=labels, cmap="tab10", s=16, alpha=0.7)
    if centers is not None:
        centers = np.asarray(centers)
        ax.scatter(centers[:, 0], centers[:, 1], c="black", marker="X", s=160, label="centroids")
        ax.legend()
    ax.set_title(title)
    ax.grid(alpha=0.2)
    return ax


# ---------------------------------------------------------------------------
# Time series / monitoring
# ---------------------------------------------------------------------------


def plot_forecast(t, y_true, y_pred=None, split_idx=None, ax=None, title: str | None = None):
    """Plot a series, an optional forecast, and an optional train/test boundary."""
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 3.5))
    ax.plot(t, y_true, label="actual", lw=1.5, color="#444")
    if y_pred is not None:
        tp = t[-len(y_pred) :] if len(y_pred) < len(t) else t
        ax.plot(tp, y_pred, "--", label="forecast", lw=1.8, color="#d62728")
    if split_idx is not None:
        ax.axvline(t[split_idx], color="gray", ls=":", label="train/test split")
    ax.grid(alpha=0.3)
    ax.legend()
    if title:
        ax.set_title(title)
    return ax


def plot_drift_simulation(x, scores, drift_at=None, ax=None, metric_name: str = "score"):
    """Plot a performance metric over time, marking where drift was injected."""
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 3.5))
    ax.plot(x, scores, "o-", lw=1.5, color="#1f77b4")
    if drift_at is not None:
        ax.axvline(drift_at, color="#d62728", ls="--", lw=1.5, label="drift onset")
        ax.legend()
    ax.set_xlabel("batch")
    ax.set_ylabel(metric_name)
    ax.grid(alpha=0.3)
    ax.set_title("Performance under drift")
    return ax


# ---------------------------------------------------------------------------
# Plotly interactives — these sliders also work in the static Jupyter Book HTML.
# ---------------------------------------------------------------------------


def plotly_model_complexity(x, y, degrees=range(1, 13), test_size: float = 0.3, seed: int = 0):
    """Slider over polynomial degree showing fit + train/test error.

    Fits a polynomial regression of each degree on a fixed train split and draws
    the curve over the data; the title reports train vs test RMSE so the
    over-fitting turn (test error rises while train keeps falling) is visible.
    """
    import plotly.graph_objects as go
    from sklearn.linear_model import LinearRegression
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import PolynomialFeatures

    x = np.asarray(x, dtype=float).reshape(-1, 1)
    y = np.asarray(y, dtype=float).ravel()
    xtr, xte, ytr, yte = train_test_split(x, y, test_size=test_size, random_state=seed)
    grid = np.linspace(x.min(), x.max(), 300)[:, None]

    frames, titles = [], {}
    for d in degrees:
        model = make_pipeline(PolynomialFeatures(d), LinearRegression()).fit(xtr, ytr)
        tr_rmse = float(np.sqrt(np.mean((model.predict(xtr) - ytr) ** 2)))
        te_rmse = float(np.sqrt(np.mean((model.predict(xte) - yte) ** 2)))
        titles[str(d)] = f"degree {d}  —  train RMSE {tr_rmse:.2f}, test RMSE {te_rmse:.2f}"
        frames.append(
            go.Frame(
                name=str(d),
                data=[
                    go.Scatter(
                        x=list(xtr.ravel()),
                        y=list(ytr),
                        mode="markers",
                        name="train",
                        marker={"color": "#1f77b4", "size": 7},
                    ),
                    go.Scatter(
                        x=list(xte.ravel()),
                        y=list(yte),
                        mode="markers",
                        name="test",
                        marker={"color": "#d62728", "size": 7, "symbol": "triangle-up"},
                    ),
                    go.Scatter(
                        x=list(grid.ravel()),
                        y=list(model.predict(grid)),
                        mode="lines",
                        name="fit",
                        line={"color": "black"},
                    ),
                ],
                layout={"title": titles[str(d)]},
            )
        )
    first = list(degrees)[0]
    fig = go.Figure(data=frames[0].data, frames=frames)
    steps = [
        {
            "args": [[str(d)], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
            "label": str(d),
            "method": "animate",
        }
        for d in degrees
    ]
    fig.update_layout(
        sliders=[{"steps": steps, "currentvalue": {"prefix": "degree = "}}],
        title=titles[str(first)],
        width=720,
        height=460,
        xaxis_title="x",
        yaxis_title="y",
        margin={"l": 50, "r": 20, "t": 60, "b": 40},
    )
    return fig


def plotly_threshold_explorer(y_true, y_score, n_thresholds: int = 19):
    """Slider over the decision threshold showing precision/recall/F1/accuracy.

    The single most useful interactive for the evaluation notebook: it makes the
    precision-recall trade-off tangible — slide the threshold up and watch
    precision rise while recall falls.
    """
    import plotly.graph_objects as go

    from .metrics import accuracy, f1_score, precision, recall

    y_true = np.asarray(y_true, dtype=int)
    y_score = np.asarray(y_score, dtype=float)
    thresholds = np.linspace(0.05, 0.95, n_thresholds)
    names = ["precision", "recall", "f1", "accuracy"]

    def metrics_at(t):
        pred = (y_score >= t).astype(int)
        return [
            precision(y_true, pred),
            recall(y_true, pred),
            f1_score(y_true, pred),
            accuracy(y_true, pred),
        ]

    frames = [
        go.Frame(
            name=f"{t:.2f}",
            data=[
                go.Bar(
                    x=names,
                    y=metrics_at(t),
                    marker_color=["#1f77b4", "#d62728", "#2ca02c", "#9467bd"],
                )
            ],
            layout={"title": f"threshold = {t:.2f}"},
        )
        for t in thresholds
    ]
    fig = go.Figure(data=frames[0].data, frames=frames)
    steps = [
        {
            "args": [[f"{t:.2f}"], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
            "label": f"{t:.2f}",
            "method": "animate",
        }
        for t in thresholds
    ]
    fig.update_layout(
        sliders=[{"steps": steps, "currentvalue": {"prefix": "threshold = "}}],
        title=f"threshold = {thresholds[0]:.2f}",
        yaxis={"range": [0, 1.05], "title": "metric value"},
        width=640,
        height=460,
        margin={"l": 50, "r": 20, "t": 60, "b": 40},
    )
    return fig
