from __future__ import annotations

import torch
from torch import nn

from .common import InceptionModule, channels_to_sequence, shape_record


def _leaky() -> nn.Module:
    return nn.LeakyReLU(negative_slope=0.01)


def _author_block(
    in_channels: int,
    feature_kernel: tuple[int, int],
    feature_stride: tuple[int, int],
    activation_factory,
) -> nn.Sequential:
    return nn.Sequential(
        nn.Conv2d(in_channels, 32, feature_kernel, stride=feature_stride),
        activation_factory(),
        nn.BatchNorm2d(32),
        nn.Conv2d(32, 32, (4, 1)),
        activation_factory(),
        nn.BatchNorm2d(32),
        nn.Conv2d(32, 32, (4, 1)),
        activation_factory(),
        nn.BatchNorm2d(32),
    )


class DeepLOBAuthorPyTorch(nn.Module):
    """Behavioral clean-room port of the official PyTorch notebook at ff14d7c."""

    expected_parameter_count = 143_907
    input_layout = "[batch, channels=1, time=100, features=40]"

    def __init__(self) -> None:
        super().__init__()
        self.block_1 = _author_block(1, (1, 2), (1, 2), _leaky)
        self.block_2 = _author_block(32, (1, 2), (1, 2), nn.Tanh)
        self.block_3 = _author_block(32, (1, 10), (1, 1), _leaky)
        self.inception = InceptionModule(
            32,
            64,
            activation_factory=_leaky,
            batch_norm=True,
        )
        self.lstm = nn.LSTM(input_size=192, hidden_size=64, num_layers=1, batch_first=True)
        self.classifier = nn.Linear(64, 3)

    @staticmethod
    def _validate_input(tensor: torch.Tensor) -> None:
        if tensor.ndim != 4 or tuple(tensor.shape[1:]) != (1, 100, 40):
            raise ValueError(
                f"author PyTorch profile expects [B,1,100,40], got {tuple(tensor.shape)}"
            )

    def _features(self, tensor: torch.Tensor) -> torch.Tensor:
        tensor = self.block_1(tensor)
        tensor = self.block_2(tensor)
        tensor = self.block_3(tensor)
        return self.inception(tensor)

    def forward(self, tensor: torch.Tensor) -> torch.Tensor:
        self._validate_input(tensor)
        tensor = self._features(tensor)
        sequence = channels_to_sequence(tensor)
        h0 = sequence.new_zeros((1, sequence.shape[0], 64))
        c0 = sequence.new_zeros((1, sequence.shape[0], 64))
        sequence, _ = self.lstm(sequence, (h0, c0))
        logits = self.classifier(sequence[:, -1, :])
        # The notebook feeds this softmax output to CrossEntropyLoss. Preserve it.
        return torch.softmax(logits, dim=1)

    def shape_trace(self, tensor: torch.Tensor) -> tuple[torch.Tensor, list[dict[str, object]]]:
        self._validate_input(tensor)
        trace = [shape_record("input_BCTF", tensor, layout=self.input_layout)]
        tensor = self.block_1(tensor)
        trace.append(shape_record("conv_block_1_valid_time", tensor))
        tensor = self.block_2(tensor)
        trace.append(shape_record("conv_block_2_tanh_valid_time", tensor))
        tensor = self.block_3(tensor)
        trace.append(shape_record("conv_block_3_valid_time", tensor))
        tensor, branches = self.inception.forward_with_branches(tensor)
        for name, branch in zip(
            ("inception_3", "inception_5", "inception_pool"), branches, strict=True
        ):
            trace.append(shape_record(name, branch))
        trace.append(shape_record("inception_concat_channels", tensor, concat_axis=1))
        sequence = channels_to_sequence(tensor)
        trace.append(
            shape_record(
                "named_permutation_channels_to_sequence",
                sequence,
                permutation="B,C,T,1 -> B,T,C",
            )
        )
        h0 = sequence.new_zeros((1, sequence.shape[0], 64))
        c0 = sequence.new_zeros((1, sequence.shape[0], 64))
        sequence, _ = self.lstm(sequence, (h0, c0))
        trace.append(shape_record("lstm_sequence", sequence))
        probability = torch.softmax(self.classifier(sequence[:, -1, :]), dim=1)
        trace.append(shape_record("three_class_softmax", probability))
        return probability, trace
