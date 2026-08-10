import numpy as np
import pandas as pd
import pytest
from quant_textbook import (
    ClaimMetadata,
    EventWindowSpecification,
    announcement_event_study,
    placebo_event_study,
    two_period_did,
)
from scipy.stats import t as student_t


def _market_series_and_events():
    index = pd.date_range("2025-01-01", periods=800, freq="1min", tz="UTC")
    returns = pd.Series(np.zeros(index.size), index=index, name="adjusted_log_return")
    events = index[[100, 300, 500]]
    response_values = np.array([0.001, 0.003, 0.005])
    anticipation_values = np.array([-0.002, 0.0, 0.001])
    for event, response, anticipation in zip(
        events, response_values, anticipation_values, strict=True
    ):
        returns.loc[event] = response
        returns.loc[event - pd.Timedelta("1min")] = anticipation
    return returns, events, response_values, anticipation_values


def _specification(**kwargs):
    defaults = {
        "anticipation_start": "-2min",
        "anticipation_end": "-1min",
        "response_start": "0min",
        "response_end": "2min",
        "timezone": "UTC",
        "timestamp_precision": "1s",
    }
    defaults.update(kwargs)
    return EventWindowSpecification(**defaults)


def test_announcement_study_aggregates_pre_specified_windows_and_uses_t_interval() -> None:
    returns, events, responses, anticipations = _market_series_and_events()
    result = announcement_event_study(returns, events, _specification())

    assert result.mean_response == pytest.approx(responses.mean())
    assert result.mean_anticipation_response == pytest.approx(anticipations.mean())
    expected_se = responses.std(ddof=1) / np.sqrt(responses.size)
    expected_half_width = student_t.ppf(0.975, 2) * expected_se
    assert result.response_standard_error == pytest.approx(expected_se)
    np.testing.assert_allclose(
        result.confidence_interval,
        [responses.mean() - expected_half_width, responses.mean() + expected_half_width],
    )
    assert result.confidence_degrees_of_freedom == 2
    assert result.confidence_reference.startswith("Student-t")
    assert result.diagnostics.timestamp_precision_sufficient
    assert result.diagnostics.expected_cadence == pd.Timedelta("1min")
    assert result.diagnostics.cadence_source == "inferred"
    assert result.diagnostics.timezone == "UTC"
    assert any("caller-enforced" in warning for warning in result.diagnostics.warnings)
    assert result.event_responses["included"].all()
    assert result.claim_class == "announcement-response"


def test_timezone_conversion_preserves_event_membership() -> None:
    returns, events, responses, _ = _market_series_and_events()
    tokyo_specification = _specification(timezone="Asia/Tokyo")
    result = announcement_event_study(
        returns,
        events.tz_convert("Asia/Tokyo"),
        tokyo_specification,
    )

    assert result.mean_response == pytest.approx(responses.mean())
    assert str(result.event_responses.index.tz) == "Asia/Tokyo"


def test_overlap_policies_error_drop_or_warn_explicitly() -> None:
    returns, events, _, _ = _market_series_and_events()
    overlapping = events.append(pd.DatetimeIndex([events[0] + pd.Timedelta("2min")])).sort_values()
    with pytest.raises(ValueError, match="overlap"):
        announcement_event_study(returns, overlapping, _specification(overlap_policy="error"))

    dropped = announcement_event_study(
        returns,
        overlapping,
        _specification(overlap_policy="drop"),
    )
    assert dropped.diagnostics.excluded_for_overlap == 2
    assert dropped.n_events == 2

    allowed = announcement_event_study(
        returns,
        overlapping,
        _specification(overlap_policy="allow"),
    )
    assert allowed.diagnostics.overlapping_event_pairs
    assert any("not independent" in warning for warning in allowed.diagnostics.warnings)
    assert allowed.response_standard_error >= 0.0


def test_timestamp_precision_diagnostic_flags_coarser_event_metadata() -> None:
    returns, events, _, _ = _market_series_and_events()
    result = announcement_event_study(
        returns,
        events,
        _specification(timestamp_precision="5min"),
    )

    assert not result.diagnostics.timestamp_precision_sufficient
    assert any("coarser" in warning for warning in result.diagnostics.warnings)


def test_local_window_gaps_are_excluded_by_inferred_cadence() -> None:
    returns, events, _, _ = _market_series_and_events()
    damaged = returns.drop(index=[events[0], events[0] + pd.Timedelta("1min")])
    result = announcement_event_study(damaged, events, _specification())

    assert result.n_events == 2
    assert result.diagnostics.excluded_for_cadence == 1
    assert (
        result.event_responses.loc[events[0], "exclusion_reason"]
        == "event window violates the expected cadence"
    )


def test_overlap_detection_uses_actual_windows_not_their_convex_hull() -> None:
    index = pd.date_range("2025-01-01", periods=180, freq="1min", tz="UTC")
    returns = pd.Series(np.zeros(index.size), index=index)
    events = index[[60, 95]]
    specification = EventWindowSpecification(
        anticipation_start="-30min",
        anticipation_end="-20min",
        response_start="20min",
        response_end="30min",
        timezone="UTC",
        overlap_policy="error",
    )
    result = announcement_event_study(returns, events, specification)

    assert result.diagnostics.overlapping_event_pairs == ()
    assert result.n_events == 2


def test_placebo_study_uses_event_level_plus_one_reference() -> None:
    returns, events, _, _ = _market_series_and_events()
    result = placebo_event_study(
        returns,
        events,
        _specification(),
        observed_response=0.02,
    )

    assert result.observed_response == pytest.approx(0.02)
    assert result.empirical_two_sided_p_value == pytest.approx(1.0 / 4.0)
    assert result.event_study.n_events == 3


def test_two_period_did_matches_cell_mean_contrast_and_limits_causal_claim() -> None:
    n_per_cell = 12
    treatment = np.repeat([0.0, 0.0, 1.0, 1.0], n_per_cell)
    post = np.repeat([0.0, 1.0, 0.0, 1.0], n_per_cell)
    cell_levels = np.array([0.0, 1.0, 2.0, 5.0])
    centered_noise = np.tile(np.linspace(-0.1, 0.1, n_per_cell), 4)
    outcome = np.repeat(cell_levels, n_per_cell) + centered_noise
    result = two_period_did(outcome, treatment, post)

    assert result.estimate == pytest.approx((5.0 - 2.0) - (1.0 - 0.0))
    np.testing.assert_allclose(result.cell_means, [[0.0, 1.0], [2.0, 5.0]], atol=1e-14)
    assert result.standard_error > 0.0
    assert result.confidence_degrees_of_freedom == outcome.size - 4
    assert result.claim.claim_class == "causal-effect"
    assert not result.claim.causal_claim_supported
    assert "parallel untreated trends" in result.claim.identification_assumptions


def test_claim_metadata_requires_identification_for_supported_causality() -> None:
    with pytest.raises(ValueError, match="counterfactual and assumptions"):
        ClaimMetadata(
            estimand="ATE",
            claim_class="causal-effect",
            counterfactual=None,
            identification_assumptions=(),
            causal_claim_supported=True,
            limitations=(),
        )

    with pytest.raises(TypeError, match="tuple of strings"):
        ClaimMetadata(
            estimand="ATE",
            claim_class="causal-effect",
            counterfactual="untreated outcome",
            identification_assumptions="parallel trends",  # type: ignore[arg-type]
            causal_claim_supported=False,
            limitations=(),
        )


@pytest.mark.parametrize(
    ("function", "message"),
    [
        (
            lambda: EventWindowSpecification(
                anticipation_start="-1min",
                anticipation_end="1min",
                response_start="0min",
                response_end="2min",
            ),
            "must not overlap",
        ),
        (
            lambda: announcement_event_study(
                pd.Series(
                    [0.0, 0.0],
                    index=pd.date_range("2025-01-01", periods=2, freq="1min"),
                ),
                pd.DatetimeIndex(["2025-01-01 00:00:00+00:00"]),
                _specification(),
            ),
            "timezone-aware",
        ),
        (
            lambda: announcement_event_study(
                _market_series_and_events()[0],
                pd.DatetimeIndex([_market_series_and_events()[1][0], pd.NaT]),
                _specification(),
            ),
            "must not contain NaT",
        ),
        (
            lambda: two_period_did(
                np.arange(8.0),
                np.zeros(8),
                np.tile([0.0, 1.0], 4),
            ),
            "all four",
        ),
    ],
)
def test_event_and_did_contracts_reject_invalid_inputs(function, message) -> None:
    with pytest.raises(ValueError, match=message):
        function()
