from __future__ import annotations

import torch
from torch import nn

from .mlplob_reference import MLP, _bin_factory


class ComputeQKV(nn.Module):
    def __init__(self, hidden_dim: int, num_heads: int) -> None:
        super().__init__()
        self.q = nn.Linear(hidden_dim, hidden_dim * num_heads)
        self.k = nn.Linear(hidden_dim, hidden_dim * num_heads)
        self.v = nn.Linear(hidden_dim, hidden_dim * num_heads)

    def forward(self, tensor: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        return self.q(tensor), self.k(tensor), self.v(tensor)


class TransformerLayer(nn.Module):
    def __init__(self, hidden_dim: int, num_heads: int, final_dim: int) -> None:
        super().__init__()
        self.hidden_dim = hidden_dim
        self.num_heads = num_heads
        self.norm = nn.LayerNorm(hidden_dim)
        self.qkv = ComputeQKV(hidden_dim, num_heads)
        self.attention = nn.MultiheadAttention(hidden_dim * num_heads, num_heads, batch_first=True)
        self.mlp = MLP(hidden_dim, hidden_dim * 4, final_dim)
        self.w0 = nn.Linear(hidden_dim * num_heads, hidden_dim)

    def forward(self, tensor: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        residual = tensor
        query, key, value = self.qkv(tensor)
        # No causal or padding mask: this is explicit reference behavior.
        tensor, attention = self.attention(
            query,
            key,
            value,
            average_attn_weights=False,
            need_weights=True,
        )
        tensor = self.w0(tensor)
        tensor = self.norm(tensor + residual)
        tensor = self.mlp(tensor)
        if tensor.shape[-1] == residual.shape[-1]:
            tensor = tensor + residual
        return tensor, attention


def sinusoidal_positional_embedding(
    sequence_length: int, hidden_dim: int, n: float = 10_000.0
) -> torch.Tensor:
    if hidden_dim % 2:
        raise ValueError("sinusoidal positional embedding requires an even hidden dimension")
    positions = torch.arange(sequence_length, dtype=torch.float32).unsqueeze(1)
    denominator = torch.pow(n, 2 * torch.arange(hidden_dim // 2) / hidden_dim)
    embedding = torch.zeros(sequence_length, hidden_dim)
    embedding[:, 0::2] = torch.sin(positions / denominator)
    embedding[:, 1::2] = torch.cos(positions / denominator)
    return embedding


class TLOBReference(nn.Module):
    def __init__(
        self,
        hidden_dim: int,
        num_layers: int,
        sequence_length: int,
        feature_count: int,
        num_heads: int,
        sinusoidal_embedding: bool = True,
        dataset_type: str = "FI_2010",
        *,
        bin_mode: str = "reference_compat",
        detach_order_type_embedding: bool = True,
    ) -> None:
        super().__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.sequence_length = sequence_length
        self.feature_count = feature_count
        self.num_heads = num_heads
        self.dataset_type = dataset_type
        self.detach_order_type_embedding = detach_order_type_embedding
        self.layers = nn.ModuleList()
        self.order_type_embedder = nn.Embedding(3, 1)
        self.norm_layer = _bin_factory(bin_mode)(feature_count, sequence_length)
        self.emb_layer = nn.Linear(feature_count, hidden_dim)
        if sinusoidal_embedding:
            self.register_buffer(
                "pos_encoder",
                sinusoidal_positional_embedding(sequence_length, hidden_dim),
                persistent=False,
            )
        else:
            self.pos_encoder = nn.Parameter(torch.randn(1, sequence_length, hidden_dim))

        for index in range(num_layers):
            if index != num_layers - 1:
                self.layers.append(TransformerLayer(hidden_dim, num_heads, hidden_dim))
                self.layers.append(TransformerLayer(sequence_length, num_heads, sequence_length))
            else:
                self.layers.append(TransformerLayer(hidden_dim, num_heads, hidden_dim // 4))
                self.layers.append(
                    TransformerLayer(sequence_length, num_heads, sequence_length // 4)
                )

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

    def _encode(self, tensor: torch.Tensor) -> torch.Tensor:
        tensor = tensor.permute(0, 2, 1)
        tensor = self.norm_layer(tensor)
        tensor = tensor.permute(0, 2, 1)
        return self.emb_layer(tensor) + self.pos_encoder

    @staticmethod
    def _feature_major_flatten(tensor: torch.Tensor) -> torch.Tensor:
        # Exact einops semantics of: b s f -> b (f s) 1, followed by reshape.
        return tensor.permute(0, 2, 1).contiguous().reshape(tensor.shape[0], -1)

    def forward(self, tensor: torch.Tensor) -> torch.Tensor:
        tensor = self._encode(self._prepare_input(tensor))
        for layer in self.layers:
            tensor, attention = layer(tensor)
            _ = attention.detach()
            tensor = tensor.permute(0, 2, 1)
        tensor = self._feature_major_flatten(tensor)
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
        tensor = self.emb_layer(tensor) + self.pos_encoder
        trace.append({"name": "feature_projection_plus_position", "shape": list(tensor.shape)})
        for index, layer in enumerate(self.layers):
            axis = "temporal" if index % 2 == 0 else "feature"
            before = list(tensor.shape)
            tensor, attention = layer(tensor)
            trace.append(
                {
                    "name": f"{axis}_attention_layer_{index}",
                    "shape": list(tensor.shape),
                    "input_shape": before,
                    "attention_shape": list(attention.shape),
                    "causal_mask": False,
                }
            )
            tensor = tensor.permute(0, 2, 1)
            trace.append(
                {
                    "name": f"axis_permutation_after_{axis}_{index}",
                    "shape": list(tensor.shape),
                    "permutation": "swap axes 1 and 2",
                }
            )
        tensor = self._feature_major_flatten(tensor)
        trace.append(
            {
                "name": "feature_major_flatten",
                "shape": list(tensor.shape),
                "permutation": "B,S,F -> B,F,S -> B,(F*S)",
            }
        )
        for index, layer in enumerate(self.final_layers):
            tensor = layer(tensor)
            trace.append(
                {"name": f"final_{index}_{layer.__class__.__name__}", "shape": list(tensor.shape)}
            )
        return tensor, trace
