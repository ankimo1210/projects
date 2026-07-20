from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import numpy as np
import pytest
import torch
from torch import nn

from lob_reproductions.provenance.profiles import load_profile, project_root
from lob_reproductions.registry import build_profile_model
from lob_reproductions.tlob.bin_corrected import BiNCorrected
from lob_reproductions.tlob.bin_reference import BiNReference
from lob_reproductions.tlob.labeling import author_repository_labels
from lob_reproductions.tlob.mlplob_reference import MLP, MLPLOBReference
from lob_reproductions.tlob.tlob_reference import TLOBReference
from lob_reproductions.training.ema import ExponentialMovingAverage, TLOBRepositoryLifecycle


def _load_module(name: str, path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import pinned source module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _pinned_tlob_modules(monkeypatch: pytest.MonkeyPatch) -> tuple[types.ModuleType, ...]:
    root = project_root() / "sources" / "references" / "tlob_f1c0af4"
    if not root.is_dir():
        pytest.skip("optional pinned TLOB source tree is not fetched")

    constants = types.ModuleType("constants")
    constants.DEVICE = torch.device("cpu")
    models = types.ModuleType("models")
    models.__path__ = [str(root / "models")]
    einops = types.ModuleType("einops")

    def rearrange(tensor: torch.Tensor, pattern: str) -> torch.Tensor:
        if pattern in {"b s f -> b f s", "b f s -> b s f"}:
            return tensor.permute(0, 2, 1)
        if pattern == "b s f -> b (f s) 1":
            return tensor.permute(0, 2, 1).contiguous().reshape(tensor.shape[0], -1, 1)
        raise AssertionError(f"unexpected source rearrange pattern: {pattern}")

    einops.rearrange = rearrange
    matplotlib = types.ModuleType("matplotlib")
    matplotlib.__path__ = []
    pyplot = types.ModuleType("matplotlib.pyplot")
    matplotlib.pyplot = pyplot
    monkeypatch.setitem(sys.modules, "constants", constants)
    monkeypatch.setitem(sys.modules, "models", models)
    monkeypatch.setitem(sys.modules, "einops", einops)
    monkeypatch.setitem(sys.modules, "matplotlib", matplotlib)
    monkeypatch.setitem(sys.modules, "matplotlib.pyplot", pyplot)
    monkeypatch.setitem(sys.modules, "seaborn", types.ModuleType("seaborn"))
    source_bin = _load_module("models.bin", root / "models" / "bin.py")
    source_mlplob = _load_module("models.mlplob", root / "models" / "mlplob.py")
    source_tlob = _load_module("models.tlob", root / "models" / "tlob.py")
    return source_bin, source_mlplob, source_tlob


def _assert_parameter_gradients_equal(left: nn.Module, right: nn.Module) -> None:
    for (left_name, left_parameter), (right_name, right_parameter) in zip(
        left.named_parameters(), right.named_parameters(), strict=True
    ):
        assert left_name == right_name
        assert left_parameter.grad is not None
        assert right_parameter.grad is not None
        torch.testing.assert_close(left_parameter.grad, right_parameter.grad, rtol=1e-5, atol=1e-6)


def test_reference_bin_matches_pinned_mit_source_output_gradient_and_update(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_bin, _source_mlplob, _source_tlob = _pinned_tlob_modules(monkeypatch)
    source = source_bin.BiN(6, 8)
    clean = BiNReference(6, 8)
    clean.load_state_dict(source.state_dict())
    # The pinned source mutates its temporal std in place, so input-gradient
    # autograd is invalid. Ordinary training inputs do not require gradients;
    # parameter gradients and the optimizer update remain directly comparable.
    source_input = torch.randn(3, 6, 8)
    clean_input = source_input.clone()
    source_output = source(source_input)
    clean_output = clean(clean_input)
    torch.testing.assert_close(source_output, clean_output)
    source_output.square().mean().backward()
    clean_output.square().mean().backward()
    _assert_parameter_gradients_equal(source, clean)

    source_optimizer = torch.optim.SGD(source.parameters(), lr=0.01)
    clean_optimizer = torch.optim.SGD(clean.parameters(), lr=0.01)
    source_optimizer.step()
    clean_optimizer.step()
    for key, value in source.state_dict().items():
        torch.testing.assert_close(value, clean.state_dict()[key])


def test_reference_tlob_and_mlplob_logits_match_pinned_mit_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _source_bin, source_mlplob, source_tlob = _pinned_tlob_modules(monkeypatch)
    source_transformer = source_tlob.TLOB(8, 2, 16, 12, 1, True, "FI_2010")
    clean_transformer = TLOBReference(8, 2, 16, 12, 1)
    clean_transformer.load_state_dict(source_transformer.state_dict())
    tensor = torch.randn(2, 16, 12)
    torch.testing.assert_close(source_transformer(tensor), clean_transformer(tensor))

    source_mlp = source_mlplob.MLPLOB(8, 2, 16, 12, "FI_2010")
    clean_mlp = MLPLOBReference(8, 2, 16, 12)
    clean_mlp.load_state_dict(source_mlp.state_dict())
    torch.testing.assert_close(source_mlp(tensor), clean_mlp(tensor))

    source_runtime_tlob = source_tlob.TLOB(144, 4, 128, 144, 1, True, "FI_2010")
    source_runtime_mlplob = source_mlplob.MLPLOB(144, 3, 384, 144, "FI_2010")
    assert sum(parameter.numel() for parameter in source_runtime_tlob.parameters()) == 2_656_724
    assert sum(parameter.numel() for parameter in source_runtime_mlplob.parameters()) == 6_327_908


def test_bin_reference_and_corrected_match_on_regular_input_but_diverge_safely() -> None:
    reference = BiNReference(5, 7)
    corrected = BiNCorrected(5, 7)
    corrected.load_state_dict(reference.state_dict())
    regular = torch.randn(2, 5, 7)
    torch.testing.assert_close(reference(regular), corrected(regular))

    zero_feature_variance = torch.arange(7, dtype=torch.float32).repeat(2, 5, 1)
    assert torch.isnan(reference(zero_feature_variance)).any()
    assert torch.isfinite(corrected(zero_feature_variance)).all()

    reference_parameter_id = id(reference.y1)
    corrected_parameter_id = id(corrected.y1)
    with torch.no_grad():
        reference.y1.fill_(-1)
        corrected.y1.fill_(-1)
    reference(regular)
    corrected(regular)
    assert id(reference.y1) != reference_parameter_id
    assert reference.y1.item() == pytest.approx(0.01)
    assert id(corrected.y1) == corrected_parameter_id
    assert corrected.y1.item() == -1


def test_tlob_axes_masks_residual_conditions_and_canonical_parameter_counts() -> None:
    small = TLOBReference(
        hidden_dim=8,
        num_layers=2,
        sequence_length=16,
        feature_count=12,
        num_heads=1,
        bin_mode="corrected_port",
    )
    output, trace = small.shape_trace(torch.randn(2, 16, 12))
    attention = [item for item in trace if "attention_layer" in str(item["name"])]
    assert [item["shape"] for item in attention] == [
        [2, 16, 8],
        [2, 8, 16],
        [2, 16, 2],
        [2, 2, 4],
    ]
    assert all(item["causal_mask"] is False for item in attention)
    assert all(layer.attention.dropout == 0.0 for layer in small.layers)
    assert output.shape == (2, 3)

    same_width = MLP(4, 8, 4)
    shrinking = MLP(4, 8, 2)
    assert same_width(torch.randn(2, 3, 4)).shape == (2, 3, 4)
    assert shrinking(torch.randn(2, 3, 4)).shape == (2, 3, 2)

    static_config_tlob = TLOBReference(40, 4, 128, 144, 1)
    static_config_mlplob = MLPLOBReference(40, 3, 384, 144)
    runtime_tlob = TLOBReference(144, 4, 128, 144, 1)
    runtime_mlplob = MLPLOBReference(144, 3, 384, 144)
    assert sum(parameter.numel() for parameter in static_config_tlob.parameters()) == 1_140_342
    assert sum(parameter.numel() for parameter in static_config_mlplob.parameters()) == 3_016_782
    assert sum(parameter.numel() for parameter in runtime_tlob.parameters()) == 2_656_724
    assert sum(parameter.numel() for parameter in runtime_mlplob.parameters()) == 6_327_908


def test_registry_builds_tlob_models_from_profile_material_fields() -> None:
    author, _ = build_profile_model(load_profile("tlob_author_repo_f1c0af4"))
    audit, _ = build_profile_model(load_profile("tlob_corrected_bin_audit"))
    assert isinstance(author.norm_layer, BiNReference)
    assert author.detach_order_type_embedding is True
    assert isinstance(audit.norm_layer, BiNCorrected)
    assert audit.detach_order_type_embedding is False

    # frozen_config.yaml is the contract: an edited profile must change the model.
    mutated = load_profile("tlob_author_repo_f1c0af4")
    mutated["model"]["bin_mode"] = "corrected_port"
    mutated["model"]["detach_order_type_embedding"] = False
    rebuilt, _ = build_profile_model(mutated)
    assert isinstance(rebuilt.norm_layer, BiNCorrected)
    assert rebuilt.detach_order_type_embedding is False


def test_lobster_order_type_embedding_detach_is_profile_specific() -> None:
    def make(detach: bool) -> TLOBReference:
        return TLOBReference(
            8,
            1,
            16,
            44,
            1,
            dataset_type="LOBSTER",
            bin_mode="corrected_port",
            detach_order_type_embedding=detach,
        )

    tensor = torch.randn(2, 16, 44)
    tensor[:, :, 41] = torch.randint(0, 3, (2, 16), dtype=torch.int64)
    exact = make(True)
    corrected = make(False)
    exact(tensor).sum().backward()
    corrected(tensor).sum().backward()
    assert exact.order_type_embedder.weight.grad is None
    assert corrected.order_type_embedder.weight.grad is not None


def test_author_label_formula_uses_exact_sliding_window_endpoints() -> None:
    mid = np.array([100.0, 100.0, 101.0, 102.0, 102.0, 101.0, 100.0, 99.0])
    orderbook = np.zeros((mid.size, 4))
    orderbook[:, 0] = mid + 0.5
    orderbook[:, 2] = mid - 0.5
    result = author_repository_labels(orderbook, smoothing_length=2, horizon=3)
    windows = np.lib.stride_tricks.sliding_window_view(mid, 2)
    expected_change = (windows[3:].mean(axis=1) - windows[:-3].mean(axis=1)) / windows[:-3].mean(
        axis=1
    )
    np.testing.assert_allclose(result.percentage_change, expected_change)
    assert result.threshold == pytest.approx(np.abs(expected_change).mean() / 2)
    np.testing.assert_array_equal(
        result.labels,
        np.where(
            expected_change < -result.threshold,
            2,
            np.where(expected_change > result.threshold, 0, 1),
        ),
    )


def test_ema_decay_warmup_matches_pinned_torch_ema_default() -> None:
    # The pinned repository uses torch_ema with its default use_num_updates=True,
    # so the effective decay is min(decay, (1 + n) / (10 + n)) at update n.
    model = nn.Linear(1, 1, bias=False)
    with torch.no_grad():
        model.weight.fill_(0.0)
    ema = ExponentialMovingAverage(model, decay=0.999)
    expected = 0.0
    for step in range(1, 6):
        with torch.no_grad():
            model.weight.fill_(float(step))
        ema.update()
        decay = min(0.999, (1 + step) / (10 + step))
        expected = expected * decay + float(step) * (1.0 - decay)
        torch.testing.assert_close(ema.shadow[0], torch.full((1, 1), expected))
    assert ema.num_updates == 5


def test_ema_validation_swap_and_repository_learning_rate_rule() -> None:
    model = nn.Linear(1, 2, bias=False)
    with torch.no_grad():
        model.weight.fill_(1.0)
    ema = ExponentialMovingAverage(model, decay=0.5, use_num_updates=False)
    with torch.no_grad():
        model.weight.fill_(3.0)
    ema.update()
    with ema.average_parameters():
        torch.testing.assert_close(model.weight, torch.full_like(model.weight, 2.0))
    torch.testing.assert_close(model.weight, torch.full_like(model.weight, 3.0))

    lifecycle_model = nn.Linear(1, 2)
    lifecycle = TLOBRepositoryLifecycle(lifecycle_model, learning_rate=0.01)
    before = [parameter.detach().clone() for parameter in lifecycle_model.parameters()]
    lifecycle.train_one_step(torch.tensor([[1.0], [-1.0]]), torch.tensor([0, 1]))
    for shadow, original in zip(lifecycle.ema.shadow, before, strict=True):
        torch.testing.assert_close(shadow, original)
    assert lifecycle.apply_validation_loss_rule(1.0)["learning_rate"] == pytest.approx(0.01)
    assert lifecycle.apply_validation_loss_rule(0.999)["learning_rate"] == pytest.approx(0.005)
    assert lifecycle.apply_validation_loss_rule(1.1)["learning_rate"] == pytest.approx(0.0025)
