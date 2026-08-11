from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest
from quant_textbook.deep_learning import (
    check_lstm_gradients,
    check_mlp_gradients,
    initialize_lstm,
    initialize_mlp,
    lstm_chunk_average_loss_and_gradients,
    lstm_chunk_average_predict,
    lstm_encode,
    lstm_predict,
    mlp_predict,
    self_attention,
    temporal_convolution_encode,
    token_embedding,
    train_lstm,
    train_lstm_chunk_average,
    train_mlp,
)


def test_mlp_backprop_matches_centered_finite_differences() -> None:
    rng = np.random.default_rng(1)
    features = rng.normal(size=(7, 3))
    target = rng.normal(size=7)
    parameters = initialize_mlp(3, 4, rng=rng)

    audit = check_mlp_gradients(parameters, features, target)

    assert audit.passed
    assert audit.maximum_relative_error < 2e-5


def test_mlp_training_is_deterministic_and_reduces_validation_loss() -> None:
    rng = np.random.default_rng(2)
    features = rng.normal(size=(120, 3))
    target = np.tanh(features[:, 0]) + 0.2 * features[:, 1]
    kwargs = dict(
        hidden_width=8,
        learning_rate=0.01,
        epochs=120,
        patience=20,
        l2=1e-4,
    )

    first = train_mlp(
        features[:80],
        target[:80],
        features[80:],
        target[80:],
        rng=np.random.default_rng(99),
        **kwargs,
    )
    second = train_mlp(
        features[:80],
        target[:80],
        features[80:],
        target[80:],
        rng=np.random.default_rng(99),
        **kwargs,
    )

    np.testing.assert_array_equal(first.training_losses, second.training_losses)
    np.testing.assert_array_equal(
        mlp_predict(first.parameters, features), mlp_predict(second.parameters, features)
    )
    assert first.validation_losses.min() < first.validation_losses[0]


def test_lstm_encoder_shapes_and_zero_candidate_behavior() -> None:
    embeddings = np.ones((3, 5, 2))
    input_weights = np.zeros((2, 16))
    recurrent_weights = np.zeros((4, 16))
    bias = np.zeros(16)

    encoded = lstm_encode(embeddings, input_weights, recurrent_weights, bias)

    assert encoded.shape == (3, 4)
    np.testing.assert_array_equal(encoded, 0.0)


def test_lstm_bptt_matches_centered_finite_differences() -> None:
    rng = np.random.default_rng(11)
    embeddings = rng.normal(size=(3, 4, 2))
    target = rng.normal(size=3)
    parameters = initialize_lstm(2, 2, rng=rng)

    audit = check_lstm_gradients(parameters, embeddings, target)

    assert audit.passed
    assert audit.maximum_relative_error < 5e-5


def test_lstm_training_is_deterministic_and_reduces_validation_loss() -> None:
    rng = np.random.default_rng(12)
    embeddings = rng.normal(size=(80, 5, 2))
    target = embeddings[:, :, 0].mean(axis=1) + 0.1 * embeddings[:, :, 1].mean(axis=1)
    kwargs = dict(
        hidden_width=3,
        learning_rate=0.01,
        epochs=40,
        patience=10,
    )
    first = train_lstm(
        embeddings[:50],
        target[:50],
        embeddings[50:],
        target[50:],
        rng=np.random.default_rng(99),
        **kwargs,
    )
    second = train_lstm(
        embeddings[:50],
        target[:50],
        embeddings[50:],
        target[50:],
        rng=np.random.default_rng(99),
        **kwargs,
    )
    np.testing.assert_array_equal(first.training_losses, second.training_losses)
    np.testing.assert_array_equal(
        lstm_predict(first.parameters, embeddings), lstm_predict(second.parameters, embeddings)
    )
    assert first.validation_losses.min() < first.validation_losses[0]


def test_lstm_chunk_average_has_masked_prediction_and_gradient_contract() -> None:
    rng = np.random.default_rng(13)
    embeddings = rng.normal(size=(40, 4, 2))
    active = np.asarray([[True, True, False, False]] * 40)
    target = embeddings[:, :2, 0].mean(axis=1)
    parameters = initialize_lstm(2, 2, rng=rng)
    _, gradients = lstm_chunk_average_loss_and_gradients(parameters, embeddings, active, target)
    step = 1e-6
    plus_weights = parameters.output_weights.copy()
    minus_weights = parameters.output_weights.copy()
    plus_weights[0] += step
    minus_weights[0] -= step
    plus_loss = lstm_chunk_average_loss_and_gradients(
        replace(parameters, output_weights=plus_weights), embeddings, active, target
    )[0]
    minus_loss = lstm_chunk_average_loss_and_gradients(
        replace(parameters, output_weights=minus_weights), embeddings, active, target
    )[0]
    numerical = (plus_loss - minus_loss) / (2.0 * step)
    np.testing.assert_allclose(gradients.output_weights[0], numerical, rtol=1e-5, atol=1e-7)
    padded_changed = embeddings.copy()
    padded_changed[:, 2:] += 1e4
    np.testing.assert_array_equal(
        lstm_chunk_average_predict(parameters, embeddings, active),
        lstm_chunk_average_predict(parameters, padded_changed, active),
    )
    first = train_lstm_chunk_average(
        embeddings[:25],
        active[:25],
        target[:25],
        embeddings[25:],
        active[25:],
        target[25:],
        hidden_width=3,
        learning_rate=0.01,
        epochs=30,
        patience=8,
        rng=np.random.default_rng(99),
    )
    second = train_lstm_chunk_average(
        embeddings[:25],
        active[:25],
        target[:25],
        embeddings[25:],
        active[25:],
        target[25:],
        hidden_width=3,
        learning_rate=0.01,
        epochs=30,
        patience=8,
        rng=np.random.default_rng(99),
    )
    np.testing.assert_array_equal(first.validation_losses, second.validation_losses)
    assert first.validation_losses.min() < first.validation_losses[0]


def test_causal_tcn_does_not_use_future_inputs() -> None:
    embeddings = np.arange(12, dtype=float).reshape(1, 6, 2)
    changed = embeddings.copy()
    changed[:, -1] += 1000.0
    kernels = np.ones((3, 2, 2))
    bias = np.zeros(2)

    full = temporal_convolution_encode(embeddings, kernels, bias)
    perturbed = temporal_convolution_encode(changed, kernels, bias)

    assert full.shape == (1, 2)
    assert np.all(perturbed > full)


def test_attention_weights_are_stochastic_and_causal() -> None:
    embeddings = np.arange(24, dtype=float).reshape(2, 3, 4) / 24.0
    identity = np.eye(4)

    output, weights = self_attention(embeddings, identity, identity, identity, causal=True)

    assert output.shape == embeddings.shape
    np.testing.assert_allclose(weights.sum(axis=-1), 1.0)
    assert np.allclose(np.triu(weights[0], k=1), 0.0)


def test_token_embedding_is_seeded_and_validated() -> None:
    tokens = np.array([[1, 2], [2, 1]])
    first = token_embedding(tokens, 3, seed=7)
    second = token_embedding(tokens, 3, seed=7)

    np.testing.assert_array_equal(first, second)
    np.testing.assert_array_equal(first[0, 0], first[1, 1])
    with pytest.raises(ValueError, match="positive integer"):
        token_embedding(np.array([[0]]), 3, seed=7)
