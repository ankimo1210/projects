from __future__ import annotations

import torch

from lob_reproductions.deeplob.author_pytorch_spec import DeepLOBAuthorPyTorch
from lob_reproductions.deeplob.author_tf2_spec import DeepLOBAuthorTF2Spec
from lob_reproductions.deeplob.common import channels_to_sequence
from lob_reproductions.deeplob.paper_ieee_2019 import DeepLOBPaperIEEE2019


def _trace_shapes(trace: list[dict[str, object]]) -> dict[str, list[int]]:
    return {str(item["name"]): item["shape"] for item in trace}


def test_deeplob_parameter_counts_are_frozen_per_profile() -> None:
    paper = DeepLOBPaperIEEE2019()
    pytorch_author = DeepLOBAuthorPyTorch()
    tensorflow_author = DeepLOBAuthorTF2Spec()
    assert sum(parameter.numel() for parameter in paper.parameters()) == 60_947
    assert sum(parameter.numel() for parameter in pytorch_author.parameters()) == 143_907
    assert sum(tensorflow_author.parameter_breakdown().values()) == 142_435


def test_paper_and_author_padding_profiles_have_distinct_shape_traces() -> None:
    sample = torch.randn(1, 1, 100, 40)
    paper = DeepLOBPaperIEEE2019().eval()
    author = DeepLOBAuthorPyTorch().eval()
    with torch.no_grad():
        paper_output, paper_trace = paper.shape_trace(sample)
        author_output, author_trace = author.shape_trace(sample)
    paper_shapes = _trace_shapes(paper_trace)
    author_shapes = _trace_shapes(author_trace)
    assert paper_shapes["conv_block_1"] == [1, 16, 100, 20]
    assert paper_shapes["conv_block_2"] == [1, 16, 100, 10]
    assert paper_shapes["conv_block_3"] == [1, 16, 100, 1]
    assert paper_shapes["inception_concat_channels"] == [1, 96, 100, 1]
    assert author_shapes["conv_block_1_valid_time"] == [1, 32, 94, 20]
    assert author_shapes["conv_block_2_tanh_valid_time"] == [1, 32, 88, 10]
    assert author_shapes["conv_block_3_valid_time"] == [1, 32, 82, 1]
    assert author_shapes["inception_concat_channels"] == [1, 192, 82, 1]
    assert paper_output.shape == author_output.shape == (1, 3)
    torch.testing.assert_close(author_output.sum(dim=1), torch.ones(1))


def test_channels_to_sequence_is_the_named_bctf_to_btc_permutation() -> None:
    tensor = torch.arange(2 * 3 * 4).reshape(2, 3, 4, 1)
    actual = channels_to_sequence(tensor)
    expected = tensor[:, :, :, 0].permute(0, 2, 1)
    assert actual.shape == (2, 4, 3)
    torch.testing.assert_close(actual, expected)


def test_tensorflow_notebook_dropout_behavior_is_separate_from_corrected_audit() -> None:
    exact = DeepLOBAuthorTF2Spec(dropout_forced_training=True)
    corrected = DeepLOBAuthorTF2Spec(dropout_forced_training=False)
    assert exact.dropout == corrected.dropout == 0.2
    assert exact.dropout_forced_training is True
    assert corrected.dropout_forced_training is False
    assert exact.shape_trace()[-3]["name"] == "forced_training_dropout"
    assert corrected.shape_trace()[-3]["name"] == "standard_mode_aware_dropout"


def test_temporal_padding_behavior_is_visible_at_both_sequence_boundaries() -> None:
    paper = DeepLOBPaperIEEE2019().eval()
    author = DeepLOBAuthorPyTorch().eval()
    for time_index in (0, 99):
        impulse = torch.zeros(1, 1, 100, 40)
        impulse[0, 0, time_index, 0] = 1.0
        with torch.no_grad():
            paper_features = paper.block_1(impulse)
            author_features = author.block_1(impulse)
        assert paper_features.shape[2] == 100
        assert author_features.shape[2] == 94


def test_deeplob_cpu_forward_is_deterministic_with_fixed_state_and_input() -> None:
    model = DeepLOBAuthorPyTorch().eval()
    sample = torch.randn(2, 1, 100, 40)
    with torch.no_grad():
        first = model(sample)
        second = model(sample)
    torch.testing.assert_close(first, second, rtol=0, atol=0)
