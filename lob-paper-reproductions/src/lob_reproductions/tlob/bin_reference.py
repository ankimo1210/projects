from __future__ import annotations

import torch
from torch import nn


class BiNReference(nn.Module):
    """Reference-compatible BiN from TLOB@f1c0af4 models/bin.py.

    It intentionally preserves parameter replacement for a negative mixture
    scalar and the asymmetric zero-variance handling. The only portability seam
    is that helper tensors follow the input device instead of a module-global one.

    The legacy torch.cuda.FloatTensor constructor is retained for author fidelity
    and is only reachable on CUDA inputs; if a future PyTorch removes that
    constructor, replace it with the torch.empty branch below (behavior-equivalent
    up to uninitialized-memory contents, which nn.init.constant_ overwrites).
    """

    def __init__(self, feature_count: int, sequence_length: int) -> None:
        super().__init__()
        self.t1 = sequence_length
        self.d1 = feature_count
        self.B1 = nn.Parameter(torch.empty(sequence_length, 1))
        nn.init.constant_(self.B1, 0)
        self.l1 = nn.Parameter(torch.empty(sequence_length, 1))
        nn.init.xavier_normal_(self.l1)
        self.B2 = nn.Parameter(torch.empty(feature_count, 1))
        nn.init.constant_(self.B2, 0)
        self.l2 = nn.Parameter(torch.empty(feature_count, 1))
        nn.init.xavier_normal_(self.l2)
        self.y1 = nn.Parameter(torch.empty(1))
        nn.init.constant_(self.y1, 0.5)
        self.y2 = nn.Parameter(torch.empty(1))
        nn.init.constant_(self.y2, 0.5)

    @staticmethod
    def _replacement_parameter(reference: torch.Tensor) -> nn.Parameter:
        if reference.device.type == "cuda":
            value = torch.cuda.FloatTensor(1)  # source-specific constructor retained on CUDA
        else:
            value = torch.empty(1, device=reference.device, dtype=reference.dtype)
        parameter = nn.Parameter(value)
        nn.init.constant_(parameter, 0.01)
        return parameter

    def forward(self, tensor: torch.Tensor) -> torch.Tensor:
        if tensor.ndim != 3 or tuple(tensor.shape[1:]) != (self.d1, self.t1):
            raise ValueError(
                f"BiNReference expects [B,{self.d1},{self.t1}], got {tuple(tensor.shape)}"
            )
        if self.y1[0] < 0:
            self.y1 = self._replacement_parameter(self.y1)
        if self.y2[0] < 0:
            self.y2 = self._replacement_parameter(self.y2)

        temporal_ones = torch.ones((self.t1, 1), device=tensor.device, dtype=tensor.dtype)
        temporal_mean = torch.mean(tensor, dim=2).reshape(tensor.shape[0], tensor.shape[1], 1)
        temporal_std = torch.std(tensor, dim=2).reshape(tensor.shape[0], tensor.shape[1], 1)
        temporal_std[temporal_std < 1e-4] = 1
        temporal_z = (tensor - temporal_mean @ temporal_ones.T) / (temporal_std @ temporal_ones.T)
        temporal_output = (self.l2 @ temporal_ones.T) * temporal_z + self.B2 @ temporal_ones.T

        feature_ones = torch.ones((self.d1, 1), device=tensor.device, dtype=tensor.dtype)
        feature_mean = torch.mean(tensor, dim=1).reshape(tensor.shape[0], tensor.shape[2], 1)
        feature_std = torch.std(tensor, dim=1).reshape(tensor.shape[0], tensor.shape[2], 1)
        mean_matrix = torch.permute(feature_mean @ feature_ones.T, (0, 2, 1))
        std_matrix = torch.permute(feature_std @ feature_ones.T, (0, 2, 1))
        feature_z = (tensor - mean_matrix) / std_matrix
        feature_output = (feature_ones @ self.l1.T) * feature_z + feature_ones @ self.B1.T
        return self.y1 * feature_output + self.y2 * temporal_output
