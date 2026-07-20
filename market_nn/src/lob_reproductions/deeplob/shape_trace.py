from __future__ import annotations

from collections import defaultdict

from torch import nn


def parameter_counts_by_module(model: nn.Module) -> dict[str, object]:
    leaves: dict[str, int] = defaultdict(int)
    for name, parameter in model.named_parameters():
        module_name = name.rsplit(".", 1)[0] if "." in name else "<root>"
        leaves[module_name] += parameter.numel()
    return {
        "total": sum(parameter.numel() for parameter in model.parameters()),
        "trainable": sum(
            parameter.numel() for parameter in model.parameters() if parameter.requires_grad
        ),
        "by_parameter_owner": dict(sorted(leaves.items())),
    }
