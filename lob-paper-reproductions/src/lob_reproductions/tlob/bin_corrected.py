from __future__ import annotations

import torch
from torch import nn


class BiNCorrected(nn.Module):
    """Device/autograd-safe audit port with state-dict-compatible parameters."""

    def __init__(self, feature_count: int, sequence_length: int) -> None:
        super().__init__()
        self.t1 = sequence_length
        self.d1 = feature_count
        self.B1 = nn.Parameter(torch.zeros(sequence_length, 1))
        self.l1 = nn.Parameter(torch.empty(sequence_length, 1))
        nn.init.xavier_normal_(self.l1)
        self.B2 = nn.Parameter(torch.zeros(feature_count, 1))
        self.l2 = nn.Parameter(torch.empty(feature_count, 1))
        nn.init.xavier_normal_(self.l2)
        self.y1 = nn.Parameter(torch.full((1,), 0.5))
        self.y2 = nn.Parameter(torch.full((1,), 0.5))

    @staticmethod
    def _safe_standard_deviation(tensor: torch.Tensor, dim: int) -> torch.Tensor:
        standard_deviation = torch.std(tensor, dim=dim, correction=1, keepdim=True)
        return torch.where(
            standard_deviation < 1e-4, torch.ones_like(standard_deviation), standard_deviation
        )

    def forward(self, tensor: torch.Tensor) -> torch.Tensor:
        if tensor.ndim != 3 or tuple(tensor.shape[1:]) != (self.d1, self.t1):
            raise ValueError(
                f"BiNCorrected expects [B,{self.d1},{self.t1}], got {tuple(tensor.shape)}"
            )
        temporal_mean = tensor.mean(dim=2, keepdim=True)
        temporal_z = (tensor - temporal_mean) / self._safe_standard_deviation(tensor, dim=2)
        temporal_output = self.l2.unsqueeze(0) * temporal_z + self.B2.unsqueeze(0)

        feature_mean = tensor.mean(dim=1, keepdim=True)
        feature_z = (tensor - feature_mean) / self._safe_standard_deviation(tensor, dim=1)
        feature_output = self.l1.T.unsqueeze(0) * feature_z + self.B1.T.unsqueeze(0)

        weight_feature = torch.clamp(self.y1, min=0.01)
        weight_temporal = torch.clamp(self.y2, min=0.01)
        return weight_feature * feature_output + weight_temporal * temporal_output
