"""Tests for dataset generators (shapes, reproducibility, basic properties)."""

import numpy as np
from nn_textbook import datasets


def test_2d_dataset_shapes_and_dtypes():
    for maker in (
        datasets.make_moons_dataset,
        datasets.make_circles_dataset,
    ):
        X, y = maker(n=200, seed=0)
        assert X.shape == (200, 2)
        assert X.dtype == np.float32
        assert y.shape == (200,)
        assert set(np.unique(y)) == {0, 1}


def test_spiral_classes_balanced():
    X, y = datasets.make_spiral_dataset(n_per_class=50, n_classes=3, seed=0)
    assert X.shape == (150, 2)
    counts = np.bincount(y)
    assert (counts == 50).all()


def test_reproducible_seeds():
    a = datasets.make_moons_dataset(n=100, seed=7)[0]
    b = datasets.make_moons_dataset(n=100, seed=7)[0]
    np.testing.assert_array_equal(a, b)
    c = datasets.make_moons_dataset(n=100, seed=8)[0]
    assert not np.array_equal(a, c)


def test_sequence_windows_shapes():
    series = np.arange(20, dtype=np.float32)
    X, Y = datasets.make_sequence_windows(series, window=5, horizon=1)
    assert X.shape == (15, 5, 1)
    assert Y.shape == (15, 1)
    # First window is [0..4] predicting 5.
    np.testing.assert_array_equal(X[0, :, 0], series[:5])
    assert Y[0, 0] == 5.0


def test_ar_process_runs_and_is_finite():
    y = datasets.make_ar_process_dataset(n_steps=200, seed=0)
    assert y.shape == (200,)
    assert np.isfinite(y).all()


def test_gaussian_mixture_on_ring():
    X, _comp = datasets.make_gaussian_mixture_dataset(
        n=500, n_components=8, radius=2.0, std=0.1, seed=0
    )
    assert X.shape == (500, 2)
    # Points cluster near radius 2 from the origin.
    r = np.linalg.norm(X, axis=1)
    assert abs(r.mean() - 2.0) < 0.3


def test_tiny_text_and_tokenizer_roundtrip():
    text = datasets.make_tiny_text_corpus()
    tok = datasets.CharTokenizer(text)
    ids = tok.encode(text)
    assert tok.decode(ids) == text
    assert tok.vocab_size == len(set(text))


def test_train_val_split_partition():
    X = np.arange(100)[:, None]
    y = np.arange(100)
    Xtr, ytr, Xval, yval = datasets.train_val_split(X, y, val_frac=0.2, seed=0)
    assert len(Xval) == 20 and len(Xtr) == 80
    # Disjoint and covering.
    assert set(ytr.tolist()) | set(yval.tolist()) == set(range(100))
    assert not (set(ytr.tolist()) & set(yval.tolist()))
