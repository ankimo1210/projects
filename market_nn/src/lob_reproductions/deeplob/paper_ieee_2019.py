from __future__ import annotations

import torch
from torch import nn

from .common import InceptionModule, channels_to_sequence, shape_record


def _paper_activation() -> nn.Module:
    return nn.LeakyReLU(negative_slope=0.01)


def _paper_block(
    in_channels: int,
    out_channels: int,
    feature_kernel: tuple[int, int],
    feature_stride: tuple[int, int],
) -> nn.Sequential:
    return nn.Sequential(
        nn.Conv2d(in_channels, out_channels, feature_kernel, stride=feature_stride),
        _paper_activation(),
        nn.Conv2d(out_channels, out_channels, (4, 1), padding="same"),
        _paper_activation(),
        nn.Conv2d(out_channels, out_channels, (4, 1), padding="same"),
        _paper_activation(),
    )


class DeepLOBPaperIEEE2019(nn.Module):
    """Independent clean-room implementation of the published 16/32-channel model."""

    input_layout = "[batch, channels=1, time=100, features=40]"

    def __init__(self) -> None:
        super().__init__()
        self.block_1 = _paper_block(1, 16, (1, 2), (1, 2))
        self.block_2 = _paper_block(16, 16, (1, 2), (1, 2))
        self.block_3 = _paper_block(16, 16, (1, 10), (1, 1))
        self.inception = InceptionModule(
            16,
            32,
            activation_factory=_paper_activation,
            batch_norm=False,
        )
        self.lstm = nn.LSTM(input_size=96, hidden_size=64, num_layers=1, batch_first=True)
        self.classifier = nn.Linear(64, 3)

    @staticmethod
    def _validate_input(tensor: torch.Tensor) -> None:
        if tensor.ndim != 4 or tuple(tensor.shape[1:]) != (1, 100, 40):
            raise ValueError(f"paper profile expects [B,1,100,40], got {tuple(tensor.shape)}")

    def forward(self, tensor: torch.Tensor) -> torch.Tensor:
        self._validate_input(tensor)
        tensor = self.block_1(tensor)
        tensor = self.block_2(tensor)
        tensor = self.block_3(tensor)
        tensor = self.inception(tensor)
        sequence = channels_to_sequence(tensor)
        sequence, _ = self.lstm(sequence)
        return self.classifier(sequence[:, -1, :])

    def shape_trace(self, tensor: torch.Tensor) -> tuple[torch.Tensor, list[dict[str, object]]]:
        self._validate_input(tensor)
        trace = [shape_record("input_BCTF", tensor, layout=self.input_layout)]
        tensor = self.block_1(tensor)
        trace.append(shape_record("conv_block_1", tensor))
        tensor = self.block_2(tensor)
        trace.append(shape_record("conv_block_2", tensor))
        tensor = self.block_3(tensor)
        trace.append(shape_record("conv_block_3", tensor))
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
        sequence, _ = self.lstm(sequence)
        trace.append(shape_record("lstm_sequence", sequence))
        logits = self.classifier(sequence[:, -1, :])
        trace.append(shape_record("three_class_logits", logits))
        return logits, trace
