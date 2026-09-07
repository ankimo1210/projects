"""The contamination tiers: every dataset lands in exactly one, by rule."""

import pytest
from timesfm_lab.datasets import ALL_SPECS
from timesfm_lab.tiers import TIER_LABEL, TIER_ORDER, VERIFIED_IN_CORPUS, tier_of


@pytest.mark.parametrize("spec", ALL_SPECS, ids=lambda s: s.key)
def test_every_dataset_has_a_known_tier(spec):
    assert tier_of(spec.key) in TIER_ORDER


def test_labels_cover_the_order():
    assert set(TIER_LABEL) == set(TIER_ORDER)


def test_the_verified_datasets_are_the_only_tier_a():
    tier_a = {s.key for s in ALL_SPECS if tier_of(s.key) == "A"}
    assert tier_a == set(VERIFIED_IN_CORPUS)


def test_generated_and_post_cutoff_datasets_are_never_tier_b():
    for spec in ALL_SPECS:
        if spec.key.startswith("syn_"):
            assert tier_of(spec.key) == "C_synthetic"
        elif spec.key.startswith("fin_"):
            assert tier_of(spec.key) == "C_post_cutoff"


def test_the_uk_control_is_not_confused_with_the_monash_traffic_set():
    """The whole point of the control is that it shares a domain with a tier-A
    dataset while sitting after the cutoff."""
    assert tier_of("traffic_hourly") == "A"
    assert tier_of("traffic_uk_2026") == "C_domain_control"
    # And it must not be averaged in with finance, which is the other
    # post-cutoff tier but a completely different domain.
    assert tier_of("fin_range_vol") == "C_post_cutoff"
