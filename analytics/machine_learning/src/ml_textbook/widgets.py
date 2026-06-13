"""ipywidgets interactive demos (need a live Jupyter kernel).

Each notebook pairs these with a static figure or a ``plotting.plotly_*`` slider
so the exported Jupyter Book HTML still tells the story. Every ``*_explorer``
returns the ``ipywidgets.interact`` handle; ``interact`` calls the inner ``draw``
once on creation, so importing + calling is enough to smoke-test the logic.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

from . import plotting


def model_complexity_explorer(X, y):
    """k-NN neighbours slider on 2-D data: fewer neighbours = more complex boundary."""
    import ipywidgets as widgets
    from sklearn.model_selection import train_test_split
    from sklearn.neighbors import KNeighborsClassifier

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, random_state=0)

    def draw(k):
        model = KNeighborsClassifier(n_neighbors=k).fit(Xtr, ytr)
        tr = model.score(Xtr, ytr)
        te = model.score(Xte, yte)
        _, ax = plt.subplots(figsize=(5.5, 5))
        plotting.plot_decision_boundary(
            model.predict, X, y, ax=ax, title=f"k = {k}  (train {tr:.2f}, test {te:.2f})"
        )
        plt.show()

    return widgets.interact(
        draw, k=widgets.IntSlider(value=15, min=1, max=60, step=2, description="k")
    )


def polynomial_degree_explorer(x, y):
    """Polynomial-degree slider on 1-D regression: watch over-fitting set in."""
    import ipywidgets as widgets
    from sklearn.linear_model import LinearRegression
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import PolynomialFeatures

    x = np.asarray(x).reshape(-1, 1)
    xtr, xte, ytr, yte = train_test_split(x, y, test_size=0.3, random_state=0)

    def draw(degree):
        model = make_pipeline(PolynomialFeatures(degree), LinearRegression()).fit(xtr, ytr)
        tr = np.sqrt(np.mean((model.predict(xtr) - ytr) ** 2))
        te = np.sqrt(np.mean((model.predict(xte) - yte) ** 2))
        _, ax = plt.subplots(figsize=(6, 4))
        plotting.plot_regression_fit(
            x,
            y,
            model.predict,
            ax=ax,
            title=f"degree {degree}  (train RMSE {tr:.2f}, test RMSE {te:.2f})",
        )
        plt.show()

    return widgets.interact(
        draw, degree=widgets.IntSlider(value=3, min=1, max=15, description="degree")
    )


def regularization_strength_explorer(X, y):
    """log10(alpha) slider for Ridge regression: coefficients shrink as alpha grows."""
    import ipywidgets as widgets
    from sklearn.linear_model import Ridge
    from sklearn.model_selection import train_test_split

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, random_state=0)

    def draw(log_alpha):
        alpha = 10.0**log_alpha
        model = Ridge(alpha=alpha).fit(Xtr, ytr)
        te = np.sqrt(np.mean((model.predict(Xte) - yte) ** 2))
        _, ax = plt.subplots(figsize=(7, 4))
        ax.bar(range(len(model.coef_)), model.coef_, color="#1f77b4")
        ax.axhline(0, color="gray", lw=0.6)
        ax.set_xlabel("feature index")
        ax.set_ylabel("coefficient")
        ax.set_title(f"alpha = {alpha:.3g}  (test RMSE {te:.2f})")
        plt.show()

    return widgets.interact(
        draw,
        log_alpha=widgets.FloatSlider(value=0.0, min=-3, max=4, step=0.25, description="log10 a"),
    )


def decision_tree_depth_explorer(X, y):
    """max_depth slider for a decision tree: deeper = more, smaller leaf regions."""
    import ipywidgets as widgets
    from sklearn.model_selection import train_test_split
    from sklearn.tree import DecisionTreeClassifier

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, random_state=0)

    def draw(depth):
        model = DecisionTreeClassifier(max_depth=depth, random_state=0).fit(Xtr, ytr)
        tr, te = model.score(Xtr, ytr), model.score(Xte, yte)
        _, ax = plt.subplots(figsize=(5.5, 5))
        plotting.plot_decision_boundary(
            model.predict, X, y, ax=ax, title=f"depth {depth}  (train {tr:.2f}, test {te:.2f})"
        )
        plt.show()

    return widgets.interact(
        draw, depth=widgets.IntSlider(value=3, min=1, max=15, description="depth")
    )


def random_forest_size_explorer(X, y):
    """n_estimators slider for a random forest: more trees = smoother boundary."""
    import ipywidgets as widgets
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, random_state=0)

    def draw(n_trees):
        model = RandomForestClassifier(n_estimators=n_trees, random_state=0).fit(Xtr, ytr)
        te = model.score(Xte, yte)
        _, ax = plt.subplots(figsize=(5.5, 5))
        plotting.plot_decision_boundary(
            model.predict, X, y, ax=ax, title=f"{n_trees} trees  (test {te:.2f})"
        )
        plt.show()

    return widgets.interact(
        draw, n_trees=widgets.IntSlider(value=20, min=1, max=200, step=5, description="trees")
    )


def svm_explorer(X, y):
    """Two sliders (log C, log gamma) for an RBF SVM decision boundary."""
    import ipywidgets as widgets
    from sklearn.svm import SVC

    def draw(log_C, log_gamma):
        model = SVC(C=10.0**log_C, gamma=10.0**log_gamma, kernel="rbf").fit(X, y)
        _, ax = plt.subplots(figsize=(5.5, 5))
        plotting.plot_decision_boundary(
            model.predict, X, y, ax=ax, title=f"C={10.0**log_C:.2g}, gamma={10.0**log_gamma:.2g}"
        )
        plt.show()

    return widgets.interact(
        draw,
        log_C=widgets.FloatSlider(value=0.0, min=-2, max=3, step=0.5, description="log10 C"),
        log_gamma=widgets.FloatSlider(value=-0.5, min=-2, max=1.5, step=0.5, description="log10 g"),
    )


def classification_threshold_explorer(y_true, y_score):
    """Threshold slider showing the confusion matrix and precision/recall/F1."""
    import ipywidgets as widgets

    from .metrics import confusion_matrix, f1_score, precision, recall

    y_true = np.asarray(y_true, dtype=int)
    y_score = np.asarray(y_score, dtype=float)

    def draw(threshold):
        pred = (y_score >= threshold).astype(int)
        cm = confusion_matrix(y_true, pred, n_classes=2)
        _, ax = plt.subplots(figsize=(4.5, 4))
        plotting.plot_confusion_matrix(cm, class_names=["neg", "pos"], ax=ax)
        ax.set_title(
            f"thr {threshold:.2f}: P={precision(y_true, pred):.2f} "
            f"R={recall(y_true, pred):.2f} F1={f1_score(y_true, pred):.2f}"
        )
        plt.show()

    return widgets.interact(
        draw,
        threshold=widgets.FloatSlider(value=0.5, min=0.0, max=1.0, step=0.02, description="thr"),
    )


def kmeans_explorer(X):
    """n_clusters slider for k-means; shows assignments, centroids and inertia."""
    import ipywidgets as widgets
    from sklearn.cluster import KMeans

    def draw(k):
        km = KMeans(n_clusters=k, n_init=10, random_state=0).fit(X)
        _, ax = plt.subplots(figsize=(5.5, 5))
        plotting.plot_cluster_assignments(
            X, km.labels_, km.cluster_centers_, ax=ax, title=f"k = {k}  (inertia {km.inertia_:.0f})"
        )
        plt.show()

    return widgets.interact(draw, k=widgets.IntSlider(value=3, min=2, max=10, description="k"))


def pca_components_explorer(X):
    """n_components slider showing cumulative explained variance."""
    import ipywidgets as widgets
    from sklearn.decomposition import PCA

    X = np.asarray(X)
    full = PCA().fit(X)
    cumvar = np.cumsum(full.explained_variance_ratio_)
    max_k = len(cumvar)

    def draw(n_components):
        _, ax = plt.subplots(figsize=(6, 4))
        ax.plot(range(1, max_k + 1), cumvar, "o-", color="#1f77b4")
        ax.axvline(n_components, color="#d62728", ls="--")
        ax.axhline(cumvar[n_components - 1], color="#d62728", ls=":")
        ax.set_xlabel("number of components")
        ax.set_ylabel("cumulative explained variance")
        ax.set_title(f"{n_components} comps explain {cumvar[n_components - 1]:.1%}")
        ax.grid(alpha=0.3)
        plt.show()

    return widgets.interact(
        draw, n_components=widgets.IntSlider(value=2, min=1, max=max_k, description="comps")
    )


def rolling_validation_explorer(n_samples: int = 120):
    """n_splits slider visualising forward-chaining time-series CV folds."""
    import ipywidgets as widgets

    def draw(n_splits):
        _, ax = plt.subplots(figsize=(8, 0.6 * n_splits + 1))
        plotting.plot_time_series_split(n_samples, n_splits=n_splits, ax=ax)
        plt.show()

    return widgets.interact(
        draw, n_splits=widgets.IntSlider(value=5, min=2, max=8, description="splits")
    )


def drift_severity_explorer(X, y):
    """Drift-severity slider: shift the test features and watch accuracy fall."""
    import ipywidgets as widgets
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.4, random_state=0)
    model = LogisticRegression(max_iter=1000).fit(Xtr, ytr)
    std = np.asarray(Xtr).std(axis=0)

    def draw(severity):
        shifted = np.asarray(Xte) + severity * std
        acc0 = model.score(Xte, yte)
        acc1 = model.score(shifted, yte)
        _, ax = plt.subplots(figsize=(5.5, 4))
        ax.bar(["no drift", f"drift {severity:.1f}σ"], [acc0, acc1], color=["#1f77b4", "#d62728"])
        ax.set_ylim(0, 1.05)
        ax.set_ylabel("accuracy")
        ax.set_title("Accuracy degrades as inputs drift")
        plt.show()

    return widgets.interact(
        draw,
        severity=widgets.FloatSlider(value=0.0, min=0.0, max=3.0, step=0.25, description="drift σ"),
    )
