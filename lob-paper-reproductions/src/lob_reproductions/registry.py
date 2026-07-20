from __future__ import annotations

from typing import Any

import torch
from torch import nn

from lob_reproductions.deeplob import (
    DeepLOBAuthorPyTorch,
    DeepLOBAuthorTF2Spec,
    DeepLOBPaperIEEE2019,
)
from lob_reproductions.deeplob.shape_trace import parameter_counts_by_module
from lob_reproductions.tlob import MLPLOBReference, TLOBReference
from lob_reproductions.universal_features import PaperConstrainedUniversalLSTM


def _seeded_random(shape: tuple[int, ...], seed: int) -> torch.Tensor:
    generator = torch.Generator(device="cpu").manual_seed(seed)
    return torch.randn(shape, generator=generator)


def build_profile_model(
    profile: dict[str, Any],
) -> tuple[nn.Module | DeepLOBAuthorTF2Spec, torch.Tensor | None]:
    name = profile["implementation_profile"]
    if name in {
        "deeplob_author_tf2_ff14d7c",
        "deeplob_author_tf2_corrected_dropout_audit",
    }:
        forced = name == "deeplob_author_tf2_ff14d7c"
        return DeepLOBAuthorTF2Spec(dropout_forced_training=forced), None

    seed_value = profile["random_seed"]
    seed = int(seed_value.get("smoke", 0) if isinstance(seed_value, dict) else seed_value)
    if name == "deeplob_ieee_2019":
        return DeepLOBPaperIEEE2019(), _seeded_random((2, 1, 100, 40), seed)
    if name == "deeplob_author_pytorch_ff14d7c":
        return DeepLOBAuthorPyTorch(), _seeded_random((2, 1, 100, 40), seed)
    if name in {
        "tlob_author_repo_f1c0af4",
        "tlob_paper_arxiv_2502_15757",
        "tlob_corrected_bin_audit",
    }:
        model_config = profile["model"]
        data_config = profile["data"]
        model = TLOBReference(
            hidden_dim=int(model_config["hidden_dim"]),
            num_layers=int(model_config["num_layers"]),
            sequence_length=int(model_config["sequence_length"]),
            feature_count=int(data_config["features"]),
            num_heads=int(model_config["num_heads"]),
            sinusoidal_embedding=(
                str(model_config.get("positional_embedding", "sinusoidal")) == "sinusoidal"
            ),
            bin_mode=str(model_config["bin_mode"]),
            detach_order_type_embedding=bool(model_config.get("detach_order_type_embedding", True)),
        )
        return model, _seeded_random(
            (2, int(model_config["sequence_length"]), int(data_config["features"])), seed
        )
    if name in {"mlplob_author_repo_f1c0af4", "mlplob_paper_arxiv_2502_15757"}:
        model_config = profile["model"]
        data_config = profile["data"]
        model = MLPLOBReference(
            hidden_dim=int(model_config["hidden_dim"]),
            num_layers=int(model_config["num_layers"]),
            sequence_length=int(model_config["sequence_length"]),
            feature_count=int(data_config["features"]),
            bin_mode=str(model_config["bin_mode"]),
            detach_order_type_embedding=bool(model_config.get("detach_order_type_embedding", True)),
        )
        return model, _seeded_random(
            (2, int(model_config["sequence_length"]), int(data_config["features"])), seed
        )
    if name == "sirignano_cont_2019_paper_constrained":
        return PaperConstrainedUniversalLSTM(), _seeded_random((2, 100, 8), seed)
    raise ValueError(f"profile does not have a registered neural model: {name}")


def inspect_neural_profile(profile: dict[str, Any]) -> dict[str, Any]:
    model, sample = build_profile_model(profile)
    if isinstance(model, DeepLOBAuthorTF2Spec):
        breakdown = model.parameter_breakdown()
        return {
            "shape_trace": model.shape_trace(batch_size=2),
            "parameter_count": {
                "total": sum(breakdown.values()),
                "trainable": sum(breakdown.values()),
                "by_parameter_owner": breakdown,
            },
            "output": None,
            "runtime": "analytic TensorFlow specification",
            "tensorflow_available": model.tensorflow_available,
        }
    assert sample is not None
    model.eval()
    with torch.no_grad():
        output, trace = model.shape_trace(sample)
    return {
        "shape_trace": trace,
        "parameter_count": parameter_counts_by_module(model),
        "output": output,
        "runtime": f"torch {torch.__version__}",
    }
