"""Small NumPy neural-network primitives for the B9 textbook chapters."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.special import expit


@dataclass(frozen=True)
class MLPParameters:
    """Parameters for one-hidden-layer scalar regression."""

    input_weights: np.ndarray
    hidden_bias: np.ndarray
    output_weights: np.ndarray
    output_bias: float


@dataclass(frozen=True)
class MLPGradients:
    """Analytic gradients matching :class:`MLPParameters`."""

    input_weights: np.ndarray
    hidden_bias: np.ndarray
    output_weights: np.ndarray
    output_bias: float


@dataclass(frozen=True)
class MLPTrainingResult:
    """A trained model and deterministic loss trace."""

    parameters: MLPParameters
    training_losses: np.ndarray
    validation_losses: np.ndarray
    best_epoch: int


@dataclass(frozen=True)
class GradientCheck:
    """Centered finite-difference comparison for an MLP parameter vector."""

    analytic: np.ndarray
    numerical: np.ndarray
    maximum_relative_error: float
    passed: bool


@dataclass(frozen=True)
class LSTMParameters:
    """Parameters for a four-gate LSTM followed by a scalar readout."""

    input_weights: np.ndarray
    recurrent_weights: np.ndarray
    bias: np.ndarray
    output_weights: np.ndarray
    output_bias: float


@dataclass(frozen=True)
class LSTMGradients:
    """Reverse-time derivatives matching :class:`LSTMParameters`."""

    input_weights: np.ndarray
    recurrent_weights: np.ndarray
    bias: np.ndarray
    output_weights: np.ndarray
    output_bias: float


@dataclass(frozen=True)
class LSTMTrainingResult:
    """A trained LSTM regressor and deterministic loss trace."""

    parameters: LSTMParameters
    training_losses: np.ndarray
    validation_losses: np.ndarray
    best_epoch: int


def _matrix(values: np.ndarray, *, name: str) -> np.ndarray:
    matrix = np.asarray(values, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] == 0 or matrix.shape[1] == 0:
        raise ValueError(f"{name} must be a non-empty two-dimensional array")
    if not np.isfinite(matrix).all():
        raise ValueError(f"{name} must contain finite values")
    return matrix


def initialize_mlp(
    input_dimension: int, hidden_width: int, *, rng: np.random.Generator
) -> MLPParameters:
    """Xavier-initialize a one-hidden-layer tanh regressor."""

    if (
        isinstance(input_dimension, bool)
        or not isinstance(input_dimension, int)
        or input_dimension <= 0
    ):
        raise ValueError("input_dimension must be a positive integer")
    if isinstance(hidden_width, bool) or not isinstance(hidden_width, int) or hidden_width <= 0:
        raise ValueError("hidden_width must be a positive integer")
    if not isinstance(rng, np.random.Generator):
        raise TypeError("rng must be a numpy.random.Generator")
    input_scale = np.sqrt(2.0 / (input_dimension + hidden_width))
    output_scale = np.sqrt(2.0 / (hidden_width + 1))
    return MLPParameters(
        input_weights=rng.normal(scale=input_scale, size=(input_dimension, hidden_width)),
        hidden_bias=np.zeros(hidden_width),
        output_weights=rng.normal(scale=output_scale, size=hidden_width),
        output_bias=0.0,
    )


def mlp_predict(parameters: MLPParameters, features: np.ndarray) -> np.ndarray:
    """Run a deterministic full-batch forward pass."""

    matrix = _matrix(features, name="features")
    if parameters.input_weights.shape != (matrix.shape[1], parameters.hidden_bias.size):
        raise ValueError("MLP parameter shapes are incompatible with features")
    if parameters.output_weights.shape != parameters.hidden_bias.shape:
        raise ValueError("MLP output weights have an incompatible shape")
    hidden = np.tanh(matrix @ parameters.input_weights + parameters.hidden_bias)
    return hidden @ parameters.output_weights + parameters.output_bias


def mlp_loss_and_gradients(
    parameters: MLPParameters,
    features: np.ndarray,
    target: np.ndarray,
    *,
    l2: float = 0.0,
) -> tuple[float, MLPGradients]:
    """Return mean squared-error loss and reverse-mode derivatives."""

    matrix = _matrix(features, name="features")
    response = np.asarray(target, dtype=float)
    if response.shape != (matrix.shape[0],) or not np.isfinite(response).all():
        raise ValueError("target must be finite with one value per row")
    if not np.isfinite(l2) or l2 < 0.0:
        raise ValueError("l2 must be finite and nonnegative")
    linear = matrix @ parameters.input_weights + parameters.hidden_bias
    hidden = np.tanh(linear)
    predicted = hidden @ parameters.output_weights + parameters.output_bias
    residual = predicted - response
    loss = 0.5 * float(np.mean(residual**2))
    loss += (
        0.5 * l2 * float(np.sum(parameters.input_weights**2) + np.sum(parameters.output_weights**2))
    )
    output_adjoint = residual / matrix.shape[0]
    output_weights = hidden.T @ output_adjoint + l2 * parameters.output_weights
    output_bias = float(output_adjoint.sum())
    hidden_adjoint = np.outer(output_adjoint, parameters.output_weights)
    linear_adjoint = hidden_adjoint * (1.0 - hidden**2)
    input_weights = matrix.T @ linear_adjoint + l2 * parameters.input_weights
    hidden_bias = linear_adjoint.sum(axis=0)
    return loss, MLPGradients(
        input_weights=input_weights,
        hidden_bias=hidden_bias,
        output_weights=output_weights,
        output_bias=output_bias,
    )


def _flatten(parameters: MLPParameters) -> np.ndarray:
    return np.concatenate(
        [
            parameters.input_weights.ravel(),
            parameters.hidden_bias,
            parameters.output_weights,
            np.asarray([parameters.output_bias]),
        ]
    )


def _unflatten(template: MLPParameters, vector: np.ndarray) -> MLPParameters:
    values = np.asarray(vector, dtype=float)
    input_size = template.input_weights.size
    hidden_size = template.hidden_bias.size
    output_size = template.output_weights.size
    if values.size != input_size + hidden_size + output_size + 1:
        raise ValueError("parameter vector has an incompatible size")
    start = 0
    input_weights = values[start : start + input_size].reshape(template.input_weights.shape)
    start += input_size
    hidden_bias = values[start : start + hidden_size]
    start += hidden_size
    output_weights = values[start : start + output_size]
    return MLPParameters(
        input_weights=input_weights,
        hidden_bias=hidden_bias,
        output_weights=output_weights,
        output_bias=float(values[-1]),
    )


def check_mlp_gradients(
    parameters: MLPParameters,
    features: np.ndarray,
    target: np.ndarray,
    *,
    step: float = 1e-6,
    tolerance: float = 2e-5,
) -> GradientCheck:
    """Audit every parameter with centered finite differences."""

    if not np.isfinite(step) or step <= 0.0:
        raise ValueError("step must be finite and positive")
    if not np.isfinite(tolerance) or tolerance <= 0.0:
        raise ValueError("tolerance must be finite and positive")
    _, gradients = mlp_loss_and_gradients(parameters, features, target)
    analytic = _flatten(
        MLPParameters(
            input_weights=gradients.input_weights,
            hidden_bias=gradients.hidden_bias,
            output_weights=gradients.output_weights,
            output_bias=gradients.output_bias,
        )
    )
    base = _flatten(parameters)
    numerical = np.empty_like(base)
    for index in range(base.size):
        plus = base.copy()
        minus = base.copy()
        plus[index] += step
        minus[index] -= step
        plus_loss = mlp_loss_and_gradients(_unflatten(parameters, plus), features, target)[0]
        minus_loss = mlp_loss_and_gradients(_unflatten(parameters, minus), features, target)[0]
        numerical[index] = (plus_loss - minus_loss) / (2.0 * step)
    scale = np.maximum(1e-12, np.abs(analytic) + np.abs(numerical))
    maximum = float(np.max(np.abs(analytic - numerical) / scale))
    return GradientCheck(
        analytic=analytic,
        numerical=numerical,
        maximum_relative_error=maximum,
        passed=maximum <= tolerance,
    )


def train_mlp(
    training_features: np.ndarray,
    training_target: np.ndarray,
    validation_features: np.ndarray,
    validation_target: np.ndarray,
    *,
    hidden_width: int,
    learning_rate: float,
    epochs: int,
    patience: int,
    rng: np.random.Generator,
    l2: float = 0.0,
) -> MLPTrainingResult:
    """Train by full-batch Adam and restore the best validation parameters."""

    train_x = _matrix(training_features, name="training_features")
    valid_x = _matrix(validation_features, name="validation_features")
    train_y = np.asarray(training_target, dtype=float)
    valid_y = np.asarray(validation_target, dtype=float)
    if train_x.shape[1] != valid_x.shape[1]:
        raise ValueError("training and validation features need the same columns")
    if train_y.shape != (train_x.shape[0],) or valid_y.shape != (valid_x.shape[0],):
        raise ValueError("targets need one value per feature row")
    if not np.isfinite(learning_rate) or learning_rate <= 0.0:
        raise ValueError("learning_rate must be finite and positive")
    if (
        isinstance(epochs, bool)
        or not isinstance(epochs, int)
        or epochs <= 0
        or isinstance(patience, bool)
        or not isinstance(patience, int)
        or patience <= 0
    ):
        raise ValueError("epochs and patience must be positive integers")
    parameters = initialize_mlp(train_x.shape[1], hidden_width, rng=rng)
    vector = _flatten(parameters)
    first = np.zeros_like(vector)
    second = np.zeros_like(vector)
    training_losses: list[float] = []
    validation_losses: list[float] = []
    best_vector = vector.copy()
    best_loss = np.inf
    best_epoch = 0
    stale = 0
    for epoch in range(int(epochs)):
        parameters = _unflatten(parameters, vector)
        train_loss, gradient = mlp_loss_and_gradients(parameters, train_x, train_y, l2=l2)
        gradient_vector = _flatten(
            MLPParameters(
                gradient.input_weights,
                gradient.hidden_bias,
                gradient.output_weights,
                gradient.output_bias,
            )
        )
        first = 0.9 * first + 0.1 * gradient_vector
        second = 0.999 * second + 0.001 * gradient_vector**2
        step_number = epoch + 1
        corrected_first = first / (1.0 - 0.9**step_number)
        corrected_second = second / (1.0 - 0.999**step_number)
        vector = vector - learning_rate * corrected_first / (np.sqrt(corrected_second) + 1e-8)
        parameters = _unflatten(parameters, vector)
        validation_residual = mlp_predict(parameters, valid_x) - valid_y
        validation_loss = 0.5 * float(np.mean(validation_residual**2))
        training_losses.append(train_loss)
        validation_losses.append(validation_loss)
        if validation_loss < best_loss - 1e-12:
            best_loss = validation_loss
            best_vector = vector.copy()
            best_epoch = epoch
            stale = 0
        else:
            stale += 1
        if stale >= patience:
            break
    return MLPTrainingResult(
        parameters=_unflatten(parameters, best_vector),
        training_losses=np.asarray(training_losses),
        validation_losses=np.asarray(validation_losses),
        best_epoch=best_epoch,
    )


def lstm_encode(
    embeddings: np.ndarray,
    input_weights: np.ndarray,
    recurrent_weights: np.ndarray,
    bias: np.ndarray,
) -> np.ndarray:
    """Encode sequences with an explicit four-gate LSTM forward recurrence."""

    values = np.asarray(embeddings, dtype=float)
    if values.ndim != 3 or not np.isfinite(values).all():
        raise ValueError("embeddings must have shape (batch, time, input) and be finite")
    batch, _, input_width = values.shape
    hidden_width = recurrent_weights.shape[0]
    if input_weights.shape != (input_width, 4 * hidden_width):
        raise ValueError("input_weights have an incompatible shape")
    if recurrent_weights.shape != (hidden_width, 4 * hidden_width):
        raise ValueError("recurrent_weights have an incompatible shape")
    if bias.shape != (4 * hidden_width,):
        raise ValueError("bias has an incompatible shape")
    hidden = np.zeros((batch, hidden_width))
    cell = np.zeros_like(hidden)
    for time_index in range(values.shape[1]):
        gates = values[:, time_index] @ input_weights + hidden @ recurrent_weights + bias
        forget, update, output, candidate = np.split(gates, 4, axis=1)
        cell = expit(forget) * cell + expit(update) * np.tanh(candidate)
        hidden = expit(output) * np.tanh(cell)
    return hidden


def lstm_predict(parameters: LSTMParameters, embeddings: np.ndarray) -> np.ndarray:
    """Run the LSTM encoder followed by its scalar regression readout."""

    values = np.asarray(embeddings, dtype=float)
    encoded = lstm_encode(
        values,
        parameters.input_weights,
        parameters.recurrent_weights,
        parameters.bias,
    )
    if parameters.output_weights.shape != (encoded.shape[1],):
        raise ValueError("LSTM output weights have an incompatible shape")
    return encoded @ parameters.output_weights + parameters.output_bias


def initialize_lstm(
    input_width: int, hidden_width: int, *, rng: np.random.Generator
) -> LSTMParameters:
    """Initialize a small LSTM regressor with a positive forget bias."""

    if (
        isinstance(input_width, bool)
        or not isinstance(input_width, int)
        or input_width <= 0
        or isinstance(hidden_width, bool)
        or not isinstance(hidden_width, int)
        or hidden_width <= 0
    ):
        raise ValueError("input_width and hidden_width must be positive integers")
    if not isinstance(rng, np.random.Generator):
        raise TypeError("rng must be a numpy.random.Generator")
    input_scale = 1.0 / np.sqrt(input_width)
    recurrent_scale = 1.0 / np.sqrt(hidden_width)
    bias = np.zeros(4 * hidden_width)
    bias[:hidden_width] = 1.0
    return LSTMParameters(
        input_weights=rng.normal(scale=input_scale, size=(input_width, 4 * hidden_width)),
        recurrent_weights=rng.normal(scale=recurrent_scale, size=(hidden_width, 4 * hidden_width)),
        bias=bias,
        output_weights=rng.normal(scale=recurrent_scale, size=hidden_width),
        output_bias=0.0,
    )


def lstm_loss_and_gradients(
    parameters: LSTMParameters, embeddings: np.ndarray, target: np.ndarray
) -> tuple[float, LSTMGradients]:
    """Return scalar-regression loss and explicit backpropagation through time."""

    values = np.asarray(embeddings, dtype=float)
    response = np.asarray(target, dtype=float)
    if values.ndim != 3 or values.shape[0] == 0 or values.shape[1] == 0:
        raise ValueError("embeddings must have shape (batch, time, input)")
    if not np.isfinite(values).all():
        raise ValueError("embeddings must be finite")
    if response.shape != (values.shape[0],) or not np.isfinite(response).all():
        raise ValueError("target must be finite with one value per sequence")
    input_width = values.shape[2]
    hidden_width = parameters.output_weights.size
    if parameters.input_weights.shape != (input_width, 4 * hidden_width):
        raise ValueError("LSTM input weights have an incompatible shape")
    if parameters.recurrent_weights.shape != (hidden_width, 4 * hidden_width):
        raise ValueError("LSTM recurrent weights have an incompatible shape")
    if parameters.bias.shape != (4 * hidden_width,):
        raise ValueError("LSTM bias has an incompatible shape")

    batch = values.shape[0]
    hidden = np.zeros((batch, hidden_width))
    cell = np.zeros_like(hidden)
    cache: list[tuple[np.ndarray, ...]] = []
    for time_index in range(values.shape[1]):
        previous_hidden = hidden
        previous_cell = cell
        gates = (
            values[:, time_index] @ parameters.input_weights
            + previous_hidden @ parameters.recurrent_weights
            + parameters.bias
        )
        forget_raw, update_raw, output_raw, candidate_raw = np.split(gates, 4, axis=1)
        forget = expit(forget_raw)
        update = expit(update_raw)
        output = expit(output_raw)
        candidate = np.tanh(candidate_raw)
        cell = forget * previous_cell + update * candidate
        hidden = output * np.tanh(cell)
        cache.append(
            (
                values[:, time_index],
                previous_hidden,
                previous_cell,
                forget,
                update,
                output,
                candidate,
                cell,
            )
        )

    predicted = hidden @ parameters.output_weights + parameters.output_bias
    residual = predicted - response
    loss = 0.5 * float(np.mean(residual**2))
    prediction_adjoint = residual / batch
    output_weights_gradient = hidden.T @ prediction_adjoint
    output_bias_gradient = float(prediction_adjoint.sum())
    hidden_adjoint = np.outer(prediction_adjoint, parameters.output_weights)
    cell_adjoint = np.zeros_like(hidden_adjoint)
    input_weights_gradient = np.zeros_like(parameters.input_weights)
    recurrent_weights_gradient = np.zeros_like(parameters.recurrent_weights)
    bias_gradient = np.zeros_like(parameters.bias)

    for cached in reversed(cache):
        (
            current_input,
            previous_hidden,
            previous_cell,
            forget,
            update,
            output,
            candidate,
            current_cell,
        ) = cached
        tanh_cell = np.tanh(current_cell)
        output_adjoint = hidden_adjoint * tanh_cell
        total_cell_adjoint = cell_adjoint + hidden_adjoint * output * (1.0 - tanh_cell**2)
        forget_adjoint = total_cell_adjoint * previous_cell
        update_adjoint = total_cell_adjoint * candidate
        candidate_adjoint = total_cell_adjoint * update
        gate_adjoint = np.concatenate(
            [
                forget_adjoint * forget * (1.0 - forget),
                update_adjoint * update * (1.0 - update),
                output_adjoint * output * (1.0 - output),
                candidate_adjoint * (1.0 - candidate**2),
            ],
            axis=1,
        )
        input_weights_gradient += current_input.T @ gate_adjoint
        recurrent_weights_gradient += previous_hidden.T @ gate_adjoint
        bias_gradient += gate_adjoint.sum(axis=0)
        hidden_adjoint = gate_adjoint @ parameters.recurrent_weights.T
        cell_adjoint = total_cell_adjoint * forget

    return loss, LSTMGradients(
        input_weights=input_weights_gradient,
        recurrent_weights=recurrent_weights_gradient,
        bias=bias_gradient,
        output_weights=output_weights_gradient,
        output_bias=output_bias_gradient,
    )


def _flatten_lstm(parameters: LSTMParameters) -> np.ndarray:
    return np.concatenate(
        [
            parameters.input_weights.ravel(),
            parameters.recurrent_weights.ravel(),
            parameters.bias,
            parameters.output_weights,
            np.asarray([parameters.output_bias]),
        ]
    )


def _unflatten_lstm(template: LSTMParameters, vector: np.ndarray) -> LSTMParameters:
    values = np.asarray(vector, dtype=float)
    sizes = (
        template.input_weights.size,
        template.recurrent_weights.size,
        template.bias.size,
        template.output_weights.size,
    )
    if values.size != sum(sizes) + 1:
        raise ValueError("LSTM parameter vector has an incompatible size")
    offsets = np.cumsum((0, *sizes))
    return LSTMParameters(
        input_weights=values[offsets[0] : offsets[1]].reshape(template.input_weights.shape),
        recurrent_weights=values[offsets[1] : offsets[2]].reshape(template.recurrent_weights.shape),
        bias=values[offsets[2] : offsets[3]],
        output_weights=values[offsets[3] : offsets[4]],
        output_bias=float(values[-1]),
    )


def train_lstm(
    training_embeddings: np.ndarray,
    training_target: np.ndarray,
    validation_embeddings: np.ndarray,
    validation_target: np.ndarray,
    *,
    hidden_width: int,
    learning_rate: float,
    epochs: int,
    patience: int,
    rng: np.random.Generator,
) -> LSTMTrainingResult:
    """Train a small LSTM by full-batch Adam and restore best validation weights."""

    train_x = np.asarray(training_embeddings, dtype=float)
    valid_x = np.asarray(validation_embeddings, dtype=float)
    train_y = np.asarray(training_target, dtype=float)
    valid_y = np.asarray(validation_target, dtype=float)
    if (
        train_x.ndim != 3
        or valid_x.ndim != 3
        or train_x.shape[1:] != valid_x.shape[1:]
        or train_x.shape[0] == 0
        or valid_x.shape[0] == 0
    ):
        raise ValueError(
            "training and validation embeddings must have matching non-empty 3D shapes"
        )
    if train_y.shape != (train_x.shape[0],) or valid_y.shape != (valid_x.shape[0],):
        raise ValueError("targets need one value per sequence")
    if not np.isfinite(train_x).all() or not np.isfinite(valid_x).all():
        raise ValueError("embeddings must be finite")
    if not np.isfinite(train_y).all() or not np.isfinite(valid_y).all():
        raise ValueError("targets must be finite")
    if not np.isfinite(learning_rate) or learning_rate <= 0.0:
        raise ValueError("learning_rate must be finite and positive")
    if (
        isinstance(epochs, bool)
        or not isinstance(epochs, int)
        or epochs <= 0
        or isinstance(patience, bool)
        or not isinstance(patience, int)
        or patience <= 0
    ):
        raise ValueError("epochs and patience must be positive integers")
    parameters = initialize_lstm(train_x.shape[2], hidden_width, rng=rng)
    vector = _flatten_lstm(parameters)
    first = np.zeros_like(vector)
    second = np.zeros_like(vector)
    training_losses: list[float] = []
    validation_losses: list[float] = []
    best_vector = vector.copy()
    best_loss = np.inf
    best_epoch = 0
    stale = 0
    for epoch in range(int(epochs)):
        parameters = _unflatten_lstm(parameters, vector)
        train_loss, gradient = lstm_loss_and_gradients(parameters, train_x, train_y)
        gradient_vector = _flatten_lstm(
            LSTMParameters(
                input_weights=gradient.input_weights,
                recurrent_weights=gradient.recurrent_weights,
                bias=gradient.bias,
                output_weights=gradient.output_weights,
                output_bias=gradient.output_bias,
            )
        )
        first = 0.9 * first + 0.1 * gradient_vector
        second = 0.999 * second + 0.001 * gradient_vector**2
        step_number = epoch + 1
        corrected_first = first / (1.0 - 0.9**step_number)
        corrected_second = second / (1.0 - 0.999**step_number)
        vector = vector - learning_rate * corrected_first / (np.sqrt(corrected_second) + 1e-8)
        parameters = _unflatten_lstm(parameters, vector)
        validation_residual = lstm_predict(parameters, valid_x) - valid_y
        validation_loss = 0.5 * float(np.mean(validation_residual**2))
        training_losses.append(train_loss)
        validation_losses.append(validation_loss)
        if validation_loss < best_loss - 1e-12:
            best_loss = validation_loss
            best_vector = vector.copy()
            best_epoch = epoch
            stale = 0
        else:
            stale += 1
        if stale >= patience:
            break
    return LSTMTrainingResult(
        parameters=_unflatten_lstm(parameters, best_vector),
        training_losses=np.asarray(training_losses),
        validation_losses=np.asarray(validation_losses),
        best_epoch=best_epoch,
    )


def check_lstm_gradients(
    parameters: LSTMParameters,
    embeddings: np.ndarray,
    target: np.ndarray,
    *,
    step: float = 1e-6,
    tolerance: float = 5e-5,
) -> GradientCheck:
    """Audit explicit BPTT against centered finite differences."""

    if not np.isfinite(step) or step <= 0.0:
        raise ValueError("step must be finite and positive")
    if not np.isfinite(tolerance) or tolerance <= 0.0:
        raise ValueError("tolerance must be finite and positive")
    _, gradients = lstm_loss_and_gradients(parameters, embeddings, target)
    analytic = _flatten_lstm(
        LSTMParameters(
            input_weights=gradients.input_weights,
            recurrent_weights=gradients.recurrent_weights,
            bias=gradients.bias,
            output_weights=gradients.output_weights,
            output_bias=gradients.output_bias,
        )
    )
    base = _flatten_lstm(parameters)
    numerical = np.empty_like(base)
    for index in range(base.size):
        plus = base.copy()
        minus = base.copy()
        plus[index] += step
        minus[index] -= step
        plus_loss = lstm_loss_and_gradients(_unflatten_lstm(parameters, plus), embeddings, target)[
            0
        ]
        minus_loss = lstm_loss_and_gradients(
            _unflatten_lstm(parameters, minus), embeddings, target
        )[0]
        numerical[index] = (plus_loss - minus_loss) / (2.0 * step)
    scale = np.maximum(1e-12, np.abs(analytic) + np.abs(numerical))
    maximum = float(np.max(np.abs(analytic - numerical) / scale))
    return GradientCheck(
        analytic=analytic,
        numerical=numerical,
        maximum_relative_error=maximum,
        passed=maximum <= tolerance,
    )


def temporal_convolution_encode(
    embeddings: np.ndarray, kernels: np.ndarray, bias: np.ndarray
) -> np.ndarray:
    """Apply a causal one-layer TCN and global-average pool its activations."""

    values = np.asarray(embeddings, dtype=float)
    filters = np.asarray(kernels, dtype=float)
    offset = np.asarray(bias, dtype=float)
    if values.ndim != 3 or filters.ndim != 3:
        raise ValueError("embeddings and kernels must be three-dimensional")
    batch, times, input_width = values.shape
    kernel_width, kernel_input, channels = filters.shape
    if kernel_input != input_width or offset.shape != (channels,) or kernel_width > times:
        raise ValueError("TCN parameter shapes are incompatible")
    padded = np.pad(values, ((0, 0), (kernel_width - 1, 0), (0, 0)))
    activations = np.empty((batch, times, channels))
    for time_index in range(times):
        window = padded[:, time_index : time_index + kernel_width]
        activations[:, time_index] = np.maximum(
            0.0, np.einsum("bki,kic->bc", window, filters) + offset
        )
    return activations.mean(axis=1)


def self_attention(
    embeddings: np.ndarray,
    query_weights: np.ndarray,
    key_weights: np.ndarray,
    value_weights: np.ndarray,
    *,
    causal: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    """Return scaled dot-product self-attention output and row-stochastic weights."""

    values = np.asarray(embeddings, dtype=float)
    if values.ndim != 3 or not np.isfinite(values).all():
        raise ValueError("embeddings must have shape (batch, time, width)")
    width = values.shape[2]
    matrices = [
        np.asarray(weight, dtype=float) for weight in (query_weights, key_weights, value_weights)
    ]
    if any(weight.shape != (width, width) for weight in matrices):
        raise ValueError("attention weights must be square with the embedding width")
    query = values @ matrices[0]
    key = values @ matrices[1]
    projected_value = values @ matrices[2]
    scores = query @ np.swapaxes(key, 1, 2) / np.sqrt(float(width))
    if causal:
        mask = np.triu(np.ones(scores.shape[1:], dtype=bool), k=1)
        scores = np.where(mask[None, :, :], -np.inf, scores)
    shifted = scores - np.max(scores, axis=-1, keepdims=True)
    weights = np.exp(shifted)
    weights /= weights.sum(axis=-1, keepdims=True)
    return weights @ projected_value, weights


def token_embedding(token_hashes: np.ndarray, width: int, *, seed: int) -> np.ndarray:
    """Map lossy many-to-one token hashes to deterministic teaching embeddings."""

    tokens = np.asarray(token_hashes)
    if tokens.ndim != 2 or not np.issubdtype(tokens.dtype, np.integer) or (tokens <= 0).any():
        raise ValueError("token_hashes must be a positive integer matrix")
    if isinstance(width, bool) or width <= 0:
        raise ValueError("width must be a positive integer")
    unique = int(tokens.max()) + 1
    rng = np.random.default_rng(np.random.SeedSequence([int(seed), unique, width]))
    table = rng.normal(scale=1.0 / np.sqrt(width), size=(unique, width))
    table[0] = 0.0
    return table[tokens]


__all__ = [
    "GradientCheck",
    "LSTMGradients",
    "LSTMParameters",
    "LSTMTrainingResult",
    "MLPGradients",
    "MLPParameters",
    "MLPTrainingResult",
    "check_lstm_gradients",
    "check_mlp_gradients",
    "initialize_lstm",
    "initialize_mlp",
    "lstm_encode",
    "lstm_loss_and_gradients",
    "lstm_predict",
    "mlp_loss_and_gradients",
    "mlp_predict",
    "self_attention",
    "temporal_convolution_encode",
    "token_embedding",
    "train_lstm",
    "train_mlp",
]
