from __future__ import annotations

import torch
from torch import nn

type LSTMState = tuple[torch.Tensor, torch.Tensor]


class PaperConstrainedUniversalLSTM(nn.Module):
    """Disclosed Sirignano-Cont architecture with unresolved choices isolated."""

    def __init__(
        self,
        input_features: int = 8,
        hidden_units: int = 50,
        layers: int = 3,
        classes: int = 2,
    ) -> None:
        super().__init__()
        if layers != 3:
            raise ValueError("the disclosed main architecture has exactly three LSTM layers")
        self.input_features = input_features
        self.hidden_units = hidden_units
        self.layers = layers
        self.lstm = nn.LSTM(
            input_size=input_features,
            hidden_size=hidden_units,
            num_layers=layers,
            batch_first=True,
        )
        self.feed_forward = nn.Linear(hidden_units, hidden_units)
        self.relu = nn.ReLU()
        self.classifier = nn.Linear(hidden_units, classes)

    def forward(
        self, features: torch.Tensor, state: LSTMState | None = None
    ) -> tuple[torch.Tensor, LSTMState]:
        sequence, next_state = self.lstm(features, state)
        representation = self.relu(self.feed_forward(sequence[:, -1, :]))
        logits = self.classifier(representation)
        return logits, next_state

    @staticmethod
    def detach_state(state: LSTMState) -> LSTMState:
        """Alternate truncated-BPTT carry semantics (SC2019-A004)."""

        return state[0].detach(), state[1].detach()

    def predict_proba(self, features: torch.Tensor) -> torch.Tensor:
        logits, _ = self(features)
        return torch.softmax(logits, dim=-1)

    def shape_trace(self, features: torch.Tensor) -> tuple[torch.Tensor, list[dict[str, object]]]:
        trace: list[dict[str, object]] = [
            {"name": "input_BTF", "shape": list(features.shape)},
            {
                "name": "hidden_state_policy",
                "shape": [self.layers, features.shape[0], self.hidden_units],
                "assumption": "SC2019-A001",
            },
        ]
        sequence, state = self.lstm(features)
        trace.append({"name": "three_layer_lstm_sequence", "shape": list(sequence.shape)})
        representation = self.relu(self.feed_forward(sequence[:, -1, :]))
        trace.append({"name": "feed_forward_relu", "shape": list(representation.shape)})
        logits = self.classifier(representation)
        trace.append({"name": "next_move_logits", "shape": list(logits.shape)})
        trace.append({"name": "lstm_h_n", "shape": list(state[0].shape)})
        return logits, trace
