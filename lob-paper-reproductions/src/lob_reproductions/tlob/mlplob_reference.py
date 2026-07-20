from __future__ import annotations

from collections.abc import Callable

import torch
from torch import nn

from .bin_corrected import BiNCorrected
from .bin_reference import BiNReference


class MLP(nn.Module):
    def __init__(self, start_dim: int, hidden_dim: int, final_dim: int) -> None:
        super().__init__()
        self.layer_norm = nn.LayerNorm(final_dim)
        self.fc = nn.Linear(start_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, final_dim)
        self.gelu = nn.GELU()

    def forward(self, tensor: torch.Tensor) -> torch.Tensor:
        residual = tensor
        tensor = self.gelu(self.fc(tensor))
        tensor = self.fc2(tensor)
        if tensor.shape[2] == residual.shape[2]:
            tensor = tensor + residual
        return self.gelu(self.layer_norm(tensor))


def _bin_factory(mode: str) -> Callable[[int, int], nn.Module]:
    if mode == "reference_compat":
        return BiNReference
    if mode == "corrected_port":
        return BiNCorrected
    raise ValueError(f"unknown BiN mode: {mode}")


class MLPLOBReference(nn.Module):
    def __init__(
        self,
        hidden_dim: int,
        num_layers: int,
        sequence_length: int,
        feature_count: int,
        dataset_type: str = "FI_2010",
        *,
        bin_mode: str = "reference_compat",
        detach_order_type_embedding: bool = True,
    ) -> None:
        super().__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.dataset_type = dataset_type
        self.sequence_length = sequence_length
        self.feature_count = feature_count
        self.detach_order_type_embedding = detach_order_type_embedding
        self.layers = nn.ModuleList()
        self.order_type_embedder = nn.Embedding(3, 1)
        self.first_layer = nn.Linear(feature_count, hidden_dim)
        self.norm_layer = _bin_factory(bin_mode)(feature_count, sequence_length)
        self.layers.append(self.first_layer)
        self.layers.append(nn.GELU())
        for index in range(num_layers):
            if index != num_layers - 1:
                self.layers.append(MLP(hidden_dim, hidden_dim * 4, hidden_dim))
                self.layers.append(MLP(sequence_length, sequence_length * 4, sequence_length))
            else:
                self.layers.append(MLP(hidden_dim, hidden_dim * 2, hidden_dim // 4))
                self.layers.append(MLP(sequence_length, sequence_length * 2, sequence_length // 4))

        total_dim = (hidden_dim // 4) * (sequence_length // 4)
        self.final_layers = nn.ModuleList()
        while total_dim > 128:
            self.final_layers.append(nn.Linear(total_dim, total_dim // 4))
            self.final_layers.append(nn.GELU())
            total_dim //= 4
        self.final_layers.append(nn.Linear(total_dim, 3))

    def _prepare_input(self, tensor: torch.Tensor) -> torch.Tensor:
        if self.dataset_type == "LOBSTER":
            continuous = torch.cat((tensor[:, :, :41], tensor[:, :, 42:]), dim=2)
            order_type = tensor[:, :, 41].long()
            embedding = self.order_type_embedder(order_type)
            if self.detach_order_type_embedding:
                embedding = embedding.detach()
            return torch.cat((continuous, embedding), dim=2)
        return tensor

    def forward(self, tensor: torch.Tensor) -> torch.Tensor:
        tensor = self._prepare_input(tensor)
        tensor = tensor.permute(0, 2, 1)
        tensor = self.norm_layer(tensor)
        tensor = tensor.permute(0, 2, 1)
        for layer in self.layers:
            tensor = layer(tensor)
            tensor = tensor.permute(0, 2, 1)
        tensor = tensor.reshape(tensor.shape[0], -1)
        for layer in self.final_layers:
            tensor = layer(tensor)
        return tensor

    def shape_trace(self, tensor: torch.Tensor) -> tuple[torch.Tensor, list[dict[str, object]]]:
        trace: list[dict[str, object]] = [{"name": "input_BSF", "shape": list(tensor.shape)}]
        tensor = self._prepare_input(tensor)
        trace.append({"name": "prepared_features", "shape": list(tensor.shape)})
        tensor = tensor.permute(0, 2, 1)
        trace.append(
            {
                "name": "permute_for_BiN",
                "shape": list(tensor.shape),
                "permutation": "B,S,F -> B,F,S",
            }
        )
        tensor = self.norm_layer(tensor).permute(0, 2, 1)
        trace.append({"name": "BiN_then_restore_BSF", "shape": list(tensor.shape)})
        for index, layer in enumerate(self.layers):
            tensor = layer(tensor)
            trace.append(
                {"name": f"layer_{index}_{layer.__class__.__name__}", "shape": list(tensor.shape)}
            )
            tensor = tensor.permute(0, 2, 1)
            trace.append(
                {
                    "name": f"axis_permutation_after_layer_{index}",
                    "shape": list(tensor.shape),
                    "permutation": "swap axes 1 and 2",
                }
            )
        tensor = tensor.reshape(tensor.shape[0], -1)
        trace.append({"name": "flatten", "shape": list(tensor.shape)})
        for index, layer in enumerate(self.final_layers):
            tensor = layer(tensor)
            trace.append(
                {"name": f"final_{index}_{layer.__class__.__name__}", "shape": list(tensor.shape)}
            )
        return tensor, trace
