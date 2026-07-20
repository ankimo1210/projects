from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec
from typing import Any


@dataclass(frozen=True)
class DeepLOBAuthorTF2Spec:
    sequence_length: int = 100
    raw_features: int = 40
    conv_channels: int = 32
    inception_branch_channels: int = 64
    lstm_hidden: int = 64
    dropout: float = 0.2
    dropout_forced_training: bool = True
    expected_parameter_count: int = 142_435
    input_layout: str = "[batch, time=100, features=40, channels=1]"

    def parameter_breakdown(self) -> dict[str, int]:
        # Keras Conv2D: kh*kw*in*out + out bias.
        block_1 = (1 * 2 * 1 * 32 + 32) + 2 * (4 * 1 * 32 * 32 + 32)
        block_2 = (1 * 2 * 32 * 32 + 32) + 2 * (4 * 1 * 32 * 32 + 32)
        block_3 = (1 * 10 * 32 * 32 + 32) + 2 * (4 * 1 * 32 * 32 + 32)
        branch_3 = (1 * 1 * 32 * 64 + 64) + (3 * 1 * 64 * 64 + 64)
        branch_5 = (1 * 1 * 32 * 64 + 64) + (5 * 1 * 64 * 64 + 64)
        branch_pool = 1 * 1 * 32 * 64 + 64
        lstm = 4 * (192 + 64 + 1) * 64
        dense = 64 * 3 + 3
        breakdown = {
            "conv_block_1": block_1,
            "conv_block_2": block_2,
            "conv_block_3": block_3,
            "inception_branch_3": branch_3,
            "inception_branch_5": branch_5,
            "inception_branch_pool": branch_pool,
            "lstm": lstm,
            "dense": dense,
        }
        if sum(breakdown.values()) != self.expected_parameter_count:
            raise AssertionError("analytic TensorFlow parameter count drifted")
        return breakdown

    def shape_trace(self, batch_size: int = 1) -> list[dict[str, object]]:
        return [
            {"name": "input_BTFC", "shape": [batch_size, 100, 40, 1]},
            {"name": "conv_block_1", "shape": [batch_size, 100, 20, 32]},
            {"name": "conv_block_2", "shape": [batch_size, 100, 10, 32]},
            {"name": "conv_block_3", "shape": [batch_size, 100, 1, 32]},
            {"name": "inception_concat_channels", "shape": [batch_size, 100, 1, 192]},
            {
                "name": "named_reshape_spatial_singleton_to_sequence",
                "shape": [batch_size, 100, 192],
                "permutation": "B,T,1,C -> B,T,C",
            },
            {
                "name": (
                    "forced_training_dropout"
                    if self.dropout_forced_training
                    else "standard_mode_aware_dropout"
                ),
                "shape": [batch_size, 100, 192],
            },
            {"name": "lstm_last", "shape": [batch_size, 64]},
            {"name": "three_class_softmax", "shape": [batch_size, 3]},
        ]

    @property
    def tensorflow_available(self) -> bool:
        return find_spec("tensorflow") is not None


def build_tensorflow_model(*, dropout_forced_training: bool = True) -> Any:
    """Build the pinned notebook model without importing TensorFlow at package import time."""

    try:
        import tensorflow as tf
    except ImportError as exc:  # pragma: no cover - optional environment
        raise RuntimeError(
            "TensorFlow is optional; install the project tensorflow extra for native comparison"
        ) from exc

    keras = tf.keras
    inputs = keras.layers.Input(shape=(100, 40, 1))

    def activate(tensor):
        return keras.layers.LeakyReLU(negative_slope=0.01)(tensor)

    tensor = activate(keras.layers.Conv2D(32, (1, 2), strides=(1, 2))(inputs))
    tensor = activate(keras.layers.Conv2D(32, (4, 1), padding="same")(tensor))
    tensor = activate(keras.layers.Conv2D(32, (4, 1), padding="same")(tensor))
    tensor = activate(keras.layers.Conv2D(32, (1, 2), strides=(1, 2))(tensor))
    tensor = activate(keras.layers.Conv2D(32, (4, 1), padding="same")(tensor))
    tensor = activate(keras.layers.Conv2D(32, (4, 1), padding="same")(tensor))
    tensor = activate(keras.layers.Conv2D(32, (1, 10))(tensor))
    tensor = activate(keras.layers.Conv2D(32, (4, 1), padding="same")(tensor))
    tensor = activate(keras.layers.Conv2D(32, (4, 1), padding="same")(tensor))

    branch_3 = activate(keras.layers.Conv2D(64, (1, 1), padding="same")(tensor))
    branch_3 = activate(keras.layers.Conv2D(64, (3, 1), padding="same")(branch_3))
    branch_5 = activate(keras.layers.Conv2D(64, (1, 1), padding="same")(tensor))
    branch_5 = activate(keras.layers.Conv2D(64, (5, 1), padding="same")(branch_5))
    branch_pool = keras.layers.MaxPooling2D((3, 1), strides=(1, 1), padding="same")(tensor)
    branch_pool = activate(keras.layers.Conv2D(64, (1, 1), padding="same")(branch_pool))
    tensor = keras.layers.Concatenate(axis=3)((branch_3, branch_5, branch_pool))
    tensor = keras.layers.Reshape((100, 192))(tensor)
    dropout_layer = keras.layers.Dropout(0.2, noise_shape=(None, 1, 192))
    tensor = (
        dropout_layer(tensor, training=True) if dropout_forced_training else dropout_layer(tensor)
    )
    tensor = keras.layers.LSTM(64)(tensor)
    outputs = keras.layers.Dense(3, activation="softmax")(tensor)
    model = keras.Model(inputs=inputs, outputs=outputs)
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=1e-4),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model
