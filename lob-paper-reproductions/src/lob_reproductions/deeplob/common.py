from __future__ import annotations

from collections.abc import Callable

import torch
from torch import nn


def shape_record(name: str, tensor: torch.Tensor, **metadata: object) -> dict[str, object]:
    return {"name": name, "shape": list(tensor.shape), **metadata}


class InceptionModule(nn.Module):
    def __init__(
        self,
        in_channels: int,
        branch_channels: int,
        *,
        activation_factory: Callable[[], nn.Module],
        batch_norm: bool,
    ) -> None:
        super().__init__()

        def conv_step(input_channels: int, output_channels: int, kernel: tuple[int, int]):
            layers: list[nn.Module] = [
                nn.Conv2d(input_channels, output_channels, kernel, padding="same"),
                activation_factory(),
            ]
            if batch_norm:
                layers.append(nn.BatchNorm2d(output_channels))
            return layers

        self.branch_3 = nn.Sequential(
            *conv_step(in_channels, branch_channels, (1, 1)),
            *conv_step(branch_channels, branch_channels, (3, 1)),
        )
        self.branch_5 = nn.Sequential(
            *conv_step(in_channels, branch_channels, (1, 1)),
            *conv_step(branch_channels, branch_channels, (5, 1)),
        )
        pool_layers: list[nn.Module] = [
            nn.MaxPool2d((3, 1), stride=(1, 1), padding=(1, 0)),
            *conv_step(in_channels, branch_channels, (1, 1)),
        ]
        self.branch_pool = nn.Sequential(*pool_layers)

    def forward(self, tensor: torch.Tensor) -> torch.Tensor:
        return torch.cat(
            (self.branch_3(tensor), self.branch_5(tensor), self.branch_pool(tensor)), dim=1
        )

    def forward_with_branches(
        self, tensor: torch.Tensor
    ) -> tuple[torch.Tensor, tuple[torch.Tensor, torch.Tensor, torch.Tensor]]:
        branch_3 = self.branch_3(tensor)
        branch_5 = self.branch_5(tensor)
        branch_pool = self.branch_pool(tensor)
        return torch.cat((branch_3, branch_5, branch_pool), dim=1), (
            branch_3,
            branch_5,
            branch_pool,
        )


def channels_to_sequence(tensor: torch.Tensor) -> torch.Tensor:
    """Named B,C,T,1 -> B,T,C permutation used before the LSTM."""

    if tensor.ndim != 4 or tensor.shape[-1] != 1:
        raise ValueError(f"expected [B,C,T,1] before LSTM, got {tuple(tensor.shape)}")
    return tensor.squeeze(-1).permute(0, 2, 1).contiguous()
