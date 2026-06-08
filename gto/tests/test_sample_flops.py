"""sample_flops: canonical-class counting and M-flop selection."""

from gto.library.sample_flops import canonical_class_counts, sample_flops


def test_class_counts_cover_all_raw_flops():
    counts = canonical_class_counts()
    assert len(counts) == 1755
    assert sum(counts.values()) == 22_100


def test_sample_is_deterministic_and_normalized():
    for strategy in ["diverse", "frequency", "random"]:
        a = sample_flops(4, strategy, seed=7)
        b = sample_flops(4, strategy, seed=7)
        assert a == b, f"{strategy} must be deterministic"
        assert len({f for f, _ in a}) == 4, "flops must be distinct"
        assert abs(sum(w for _, w in a) - 1.0) < 1e-9
        for f, w in a:
            assert len(f) == 6 and w > 0


def test_diverse_strategy_spans_textures():
    from gto.library.flop_canon import board_texture

    picks = sample_flops(4, "diverse", seed=1)
    textures = {board_texture(tuple(f[i : i + 2] for i in (0, 2, 4))) for f, _ in picks}
    assert len(textures) >= 3, f"diverse picks collapsed to {textures}"
