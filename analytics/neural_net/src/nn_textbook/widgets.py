"""ipywidgets interactive demos.

These need a live Jupyter kernel. Each notebook pairs them with a static figure
so the exported Jupyter Book HTML still tells the story.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

from . import plotting


def activation_explorer():
    """Slider over activations and an input value; shows value + derivative."""
    import ipywidgets as widgets

    def draw(name, x0):
        _, ax = plt.subplots(figsize=(6, 4))
        plotting.plot_activation_function(name, ax=ax)
        f = {"relu": max(0.0, x0), "sigmoid": 1 / (1 + np.exp(-x0)), "tanh": np.tanh(x0)}[name]
        ax.plot([x0], [f], "ro", ms=8)
        ax.set_title(f"{name}({x0:.2f}) = {f:.3f}")
        plt.show()

    return widgets.interact(
        draw,
        name=widgets.Dropdown(options=["relu", "sigmoid", "tanh"], value="relu"),
        x0=widgets.FloatSlider(value=1.0, min=-5, max=5, step=0.1, description="x"),
    )


def learning_rate_explorer(model_fn, X, y, train_fn):
    """Slider over learning rate; redraws the decision boundary after training.

    model_fn() -> fresh model, train_fn(model, X, y, lr) -> history.
    """
    import ipywidgets as widgets

    def draw(log_lr):
        lr = 10**log_lr
        model = model_fn()
        train_fn(model, X, y, lr)
        _, ax = plt.subplots(figsize=(5.5, 5))
        plotting.plot_decision_boundary(model.predict, X, y, ax=ax, title=f"lr = {lr:.3g}")
        plt.show()

    return widgets.interact(
        draw,
        log_lr=widgets.FloatSlider(value=-1.0, min=-3, max=0.5, step=0.25, description="log10 lr"),
    )


def decision_boundary_trainer(model, X, y, step_fn, max_steps: int = 400, stride: int = 20):
    """Slider that scrubs through training steps and redraws the boundary.

    step_fn(model, n_steps) trains the model in place for n_steps from scratch.
    Re-trains from the same seed each time so scrubbing is deterministic.
    """
    import ipywidgets as widgets

    def draw(steps):
        step_fn(model, steps)
        _, ax = plt.subplots(figsize=(5.5, 5))
        plotting.plot_decision_boundary(model.predict, X, y, ax=ax, title=f"after {steps} steps")
        plt.show()

    return widgets.interact(
        draw,
        steps=widgets.IntSlider(value=0, min=0, max=max_steps, step=stride, description="steps"),
    )


def convolution_kernel_explorer(image):
    """Slide a 3x3 kernel over an image; show the convolved output live."""
    import ipywidgets as widgets
    from scipy.signal import convolve2d

    image = np.asarray(image, dtype=float).squeeze()
    kernels = {
        "edge": np.array([[-1, -1, -1], [-1, 8, -1], [-1, -1, -1]]),
        "sharpen": np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]]),
        "blur": np.ones((3, 3)) / 9,
        "sobel_x": np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]]),
    }

    def draw(name):
        k = kernels[name]
        out = convolve2d(image, k, mode="same", boundary="symm")
        _, axes = plt.subplots(1, 3, figsize=(11, 3.6))
        axes[0].imshow(image, cmap="gray")
        axes[0].set_title("input")
        axes[1].imshow(k, cmap="RdBu", vmin=-2, vmax=2)
        axes[1].set_title(f"kernel: {name}")
        axes[2].imshow(out, cmap="gray")
        axes[2].set_title("output")
        for ax in axes:
            ax.axis("off")
        plt.show()

    return widgets.interact(draw, name=widgets.Dropdown(options=list(kernels), value="edge"))


def attention_matrix_explorer(tokens, embeddings):
    """Slider over a temperature that sharpens/softens the QK attention matrix."""
    import ipywidgets as widgets

    from .metrics import softmax_np

    E = np.asarray(embeddings, dtype=float)
    scores = E @ E.T / np.sqrt(E.shape[1])

    def draw(temperature):
        attn = softmax_np(scores / temperature, axis=1)
        _, ax = plt.subplots(figsize=(5.5, 5))
        plotting.plot_attention_heatmap(
            attn, tokens=tokens, ax=ax, title=f"attention (temperature = {temperature:.2f})"
        )
        plt.show()

    return widgets.interact(
        draw,
        temperature=widgets.FloatSlider(value=1.0, min=0.2, max=3.0, step=0.1, description="temp"),
    )


def positional_encoding_explorer(seq_len: int = 50, d_model: int = 32):
    """Slider over the embedding dimension; show its positional-encoding curve."""
    import ipywidgets as widgets

    pos = np.arange(seq_len)[:, None]
    i = np.arange(d_model)[None, :]
    angle = pos / np.power(10000, (2 * (i // 2)) / d_model)
    pe = np.where(i % 2 == 0, np.sin(angle), np.cos(angle))

    def draw(dim):
        _, axes = plt.subplots(1, 2, figsize=(11, 4))
        axes[0].imshow(pe.T, cmap="RdBu", aspect="auto")
        axes[0].set_xlabel("position")
        axes[0].set_ylabel("dimension")
        axes[0].set_title("positional encoding")
        axes[1].plot(pos.ravel(), pe[:, dim])
        axes[1].set_title(f"dimension {dim}")
        axes[1].set_xlabel("position")
        axes[1].grid(alpha=0.3)
        plt.show()

    return widgets.interact(
        draw, dim=widgets.IntSlider(value=0, min=0, max=d_model - 1, description="dim")
    )


def latent_interpolation_explorer(decode_fn, z_a, z_b, image_shape=(28, 28)):
    """Slider that interpolates between two latent vectors and decodes the result.

    decode_fn(z[1, latent_dim]) -> flat image array.
    """
    import ipywidgets as widgets

    z_a = np.asarray(z_a, dtype=float)
    z_b = np.asarray(z_b, dtype=float)

    def draw(alpha):
        z = (1 - alpha) * z_a + alpha * z_b
        img = np.asarray(decode_fn(z[None, :])).reshape(image_shape)
        _, ax = plt.subplots(figsize=(3.2, 3.2))
        ax.imshow(img, cmap="gray")
        ax.axis("off")
        ax.set_title(f"alpha = {alpha:.2f}")
        plt.show()

    return widgets.interact(
        draw, alpha=widgets.FloatSlider(value=0.5, min=0.0, max=1.0, step=0.05, description="alpha")
    )


def diffusion_noising_explorer(image):
    """Slider over the diffusion timestep; show the image getting noisier.

    Uses the standard variance-preserving schedule x_t = sqrt(a) x0 + sqrt(1-a) eps.
    """
    import ipywidgets as widgets

    image = np.asarray(image, dtype=float).squeeze()
    rng = np.random.default_rng(0)
    noise = rng.standard_normal(image.shape)

    def draw(t):
        alpha_bar = np.cos((t / 1.0) * np.pi / 2) ** 2  # smooth 1 -> 0 schedule
        xt = np.sqrt(alpha_bar) * image + np.sqrt(1 - alpha_bar) * noise
        _, ax = plt.subplots(figsize=(3.4, 3.4))
        ax.imshow(xt, cmap="gray")
        ax.axis("off")
        ax.set_title(f"t = {t:.2f}  (signal {alpha_bar:.2f})")
        plt.show()

    return widgets.interact(
        draw, t=widgets.FloatSlider(value=0.3, min=0.0, max=1.0, step=0.05, description="t")
    )
