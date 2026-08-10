"""Timestamp-safe announcement studies and a minimal two-period DiD.

The default announcement design estimates an observed response in a
pre-specified window.  It deliberately does not label that response a causal
effect.  Timezone, timestamp precision, and overlap handling are enforced here.
The simultaneous-news rule is recorded, while the caller must prefilter and
separately audit event eligibility because returns alone cannot reveal news.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import numpy as np
import pandas as pd
from numpy.typing import ArrayLike, NDArray
from scipy.stats import t as student_t

from .robust import OLSInferenceResult, fit_ols_inference

FloatArray = NDArray[np.float64]
OverlapPolicy = Literal["error", "drop", "allow"]
ClaimClass = Literal["association", "announcement-response", "causal-effect"]
ReturnAggregation = Literal["sum", "compound"]


def _timedelta(value: str | pd.Timedelta, *, name: str, positive: bool = False) -> pd.Timedelta:
    try:
        result = pd.Timedelta(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be convertible to pandas.Timedelta") from error
    if pd.isna(result):
        raise ValueError(f"{name} must not be missing")
    if positive and result <= pd.Timedelta(0):
        raise ValueError(f"{name} must be strictly positive")
    return result


@dataclass(frozen=True)
class EventWindowSpecification:
    """Pre-analysis contract for one announcement-window estimand.

    All offset and precision fields accept ``pandas.Timedelta`` or a pandas
    duration string and are normalized to ``Timedelta`` during construction.
    Window endpoints are inclusive.  ``sum`` is appropriate for log returns;
    use ``compound`` for simple returns.  ``simultaneous_news_rule`` is a
    declarative pre-analysis field; callers must apply it before passing
    ``event_times`` and retain their event registry as the enforcement audit.
    """

    anticipation_start: str | pd.Timedelta = "-30min"
    anticipation_end: str | pd.Timedelta = "-1min"
    response_start: str | pd.Timedelta = "0min"
    response_end: str | pd.Timedelta = "30min"
    timezone: str = "Asia/Tokyo"
    timestamp_precision: str | pd.Timedelta = "1s"
    overlap_policy: OverlapPolicy = "error"
    simultaneous_news_rule: str = "exclude events with known simultaneous market-moving news"
    estimand: str = "mean adjusted return in the pre-specified response window"
    claim_class: ClaimClass = "announcement-response"
    return_aggregation: ReturnAggregation = "sum"
    minimum_observations_per_window: int = 1
    expected_cadence: str | pd.Timedelta | None = None

    def __post_init__(self) -> None:
        anticipation_start = _timedelta(self.anticipation_start, name="anticipation_start")
        anticipation_end = _timedelta(self.anticipation_end, name="anticipation_end")
        response_start = _timedelta(self.response_start, name="response_start")
        response_end = _timedelta(self.response_end, name="response_end")
        timestamp_precision = _timedelta(
            self.timestamp_precision,
            name="timestamp_precision",
            positive=True,
        )
        expected_cadence = (
            None
            if self.expected_cadence is None
            else _timedelta(
                self.expected_cadence,
                name="expected_cadence",
                positive=True,
            )
        )
        if anticipation_start > anticipation_end:
            raise ValueError("anticipation_start must not exceed anticipation_end")
        if response_start > response_end:
            raise ValueError("response_start must not exceed response_end")
        if anticipation_end >= response_start:
            raise ValueError("anticipation and response windows must not overlap")
        if self.overlap_policy not in {"error", "drop", "allow"}:
            raise ValueError("overlap_policy must be 'error', 'drop', or 'allow'")
        if self.claim_class not in {"association", "announcement-response", "causal-effect"}:
            raise ValueError("unknown claim_class")
        if self.return_aggregation not in {"sum", "compound"}:
            raise ValueError("return_aggregation must be 'sum' or 'compound'")
        if (
            isinstance(self.minimum_observations_per_window, bool)
            or not isinstance(self.minimum_observations_per_window, (int, np.integer))
            or self.minimum_observations_per_window < 1
        ):
            raise ValueError("minimum_observations_per_window must be a positive integer")
        if not isinstance(self.timezone, str) or not self.timezone.strip():
            raise ValueError("timezone must be a non-empty IANA timezone string")
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as error:
            raise ValueError(f"unknown IANA timezone: {self.timezone!r}") from error
        if (
            not isinstance(self.simultaneous_news_rule, str)
            or not self.simultaneous_news_rule.strip()
        ):
            raise ValueError("simultaneous_news_rule must be a non-empty string")
        if not isinstance(self.estimand, str) or not self.estimand.strip():
            raise ValueError("estimand must be a non-empty string")
        object.__setattr__(self, "anticipation_start", anticipation_start)
        object.__setattr__(self, "anticipation_end", anticipation_end)
        object.__setattr__(self, "response_start", response_start)
        object.__setattr__(self, "response_end", response_end)
        object.__setattr__(self, "timestamp_precision", timestamp_precision)
        object.__setattr__(self, "expected_cadence", expected_cadence)
        object.__setattr__(
            self,
            "minimum_observations_per_window",
            int(self.minimum_observations_per_window),
        )


@dataclass(frozen=True)
class AnnouncementStudyDiagnostics:
    """Audit trail for event eligibility and timestamp compatibility."""

    total_events: int
    included_events: int
    excluded_events: int
    excluded_for_overlap: int
    excluded_for_market_coverage: int
    excluded_for_cadence: int
    excluded_for_insufficient_observations: int
    overlapping_event_pairs: tuple[tuple[pd.Timestamp, pd.Timestamp], ...]
    median_data_frequency: pd.Timedelta
    expected_cadence: pd.Timedelta
    cadence_source: Literal["specified", "inferred"]
    timestamp_precision_sufficient: bool
    timezone: str
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class AnnouncementStudyResult:
    """Event-level window responses and an event-level mean interval."""

    event_responses: pd.DataFrame
    mean_response: float
    response_standard_error: float
    confidence_interval: tuple[float, float]
    confidence_degrees_of_freedom: int
    confidence_reference: str
    mean_anticipation_response: float
    n_events: int
    estimand: str
    claim_class: ClaimClass
    specification: EventWindowSpecification
    diagnostics: AnnouncementStudyDiagnostics


def _validated_returns(returns: pd.Series, timezone: str) -> pd.Series:
    if not isinstance(returns, pd.Series):
        raise TypeError("returns must be a pandas.Series")
    if not isinstance(returns.index, pd.DatetimeIndex):
        raise TypeError("returns must have a pandas.DatetimeIndex")
    if returns.index.tz is None:
        raise ValueError("returns index must be timezone-aware")
    if returns.size < 2:
        raise ValueError("returns must contain at least two observations")
    if not returns.index.is_monotonic_increasing or returns.index.has_duplicates:
        raise ValueError("returns index must be sorted and unique")
    numeric = pd.to_numeric(returns, errors="coerce").astype(float)
    if not np.all(np.isfinite(numeric.to_numpy())):
        raise ValueError("returns must contain only finite numeric values")
    converted = numeric.copy()
    converted.index = returns.index.tz_convert(timezone)
    return converted


def _validated_event_times(event_times: ArrayLike, timezone: str) -> pd.DatetimeIndex:
    try:
        events = pd.DatetimeIndex(event_times)
    except (TypeError, ValueError) as error:
        raise ValueError("event_times must be convertible to pandas.DatetimeIndex") from error
    if events.size == 0:
        raise ValueError("event_times must not be empty")
    if events.hasnans:
        raise ValueError("event_times must not contain NaT")
    if events.tz is None:
        raise ValueError("event_times must be timezone-aware")
    if events.has_duplicates:
        raise ValueError("event_times must be unique")
    return events.tz_convert(timezone).sort_values()


def _aggregate_returns(values: pd.Series, method: ReturnAggregation) -> float:
    array = values.to_numpy(dtype=float)
    if method == "sum":
        result = float(array.sum())
    else:
        if np.any(array <= -1.0):
            raise ValueError("compound simple returns must all be greater than -1")
        result = float(np.prod(1.0 + array) - 1.0)
    if not np.isfinite(result):
        raise FloatingPointError("event-window return aggregation is non-finite")
    return result


def _overlapping_pairs(
    events: pd.DatetimeIndex,
    specification: EventWindowSpecification,
) -> tuple[tuple[pd.Timestamp, pd.Timestamp], ...]:
    relative_intervals = (
        (specification.anticipation_start, specification.anticipation_end),
        (specification.response_start, specification.response_end),
    )
    earliest_start = min(start for start, _ in relative_intervals)
    latest_end = max(end for _, end in relative_intervals)
    pairs: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    for first_index, first_event in enumerate(events[:-1]):
        for second_event in events[first_index + 1 :]:
            if second_event + earliest_start > first_event + latest_end:
                break
            overlaps = any(
                max(first_event + first_start, second_event + second_start)
                <= min(first_event + first_end, second_event + second_end)
                for first_start, first_end in relative_intervals
                for second_start, second_end in relative_intervals
            )
            if overlaps:
                pairs.append((first_event, second_event))
    return tuple(pairs)


def _window_has_cadence_coverage(
    observations: pd.DatetimeIndex,
    window_start: pd.Timestamp,
    window_end: pd.Timestamp,
    cadence: pd.Timedelta,
) -> bool:
    if observations.size == 0:
        return False
    if observations[0] - window_start >= cadence:
        return False
    if window_end - observations[-1] >= cadence:
        return False
    duration = window_end - window_start
    minimum_count = max(1, int(duration // cadence))
    if observations.size < minimum_count:
        return False
    if observations.size > 1:
        gaps = observations[1:] - observations[:-1]
        if np.any(gaps > 1.5 * cadence):
            return False
    return True


def announcement_event_study(
    returns: pd.Series,
    event_times: ArrayLike,
    specification: EventWindowSpecification,
    *,
    confidence_level: float = 0.95,
) -> AnnouncementStudyResult:
    """Estimate an event-level mean announcement response.

    The input series must contain additive log returns when ``sum`` is selected
    or simple returns when ``compound`` is selected.  Events without full
    boundary coverage are retained in the audit table but excluded from the
    aggregate.  At least two eligible events are required for uncertainty.
    ``event_times`` must already satisfy externally defined news and liquidity
    eligibility rules; this function cannot infer those flags from returns.
    """

    if not isinstance(specification, EventWindowSpecification):
        raise TypeError("specification must be an EventWindowSpecification")
    level = float(confidence_level)
    if not np.isfinite(level) or not 0.0 < level < 1.0:
        raise ValueError("confidence_level must be strictly between zero and one")
    market_returns = _validated_returns(returns, specification.timezone)
    events = _validated_event_times(event_times, specification.timezone)
    differences = market_returns.index.to_series().diff().dropna()
    median_frequency = pd.Timedelta(differences.median())
    cadence = (
        median_frequency
        if specification.expected_cadence is None
        else specification.expected_cadence
    )
    cadence_source: Literal["specified", "inferred"] = (
        "inferred" if specification.expected_cadence is None else "specified"
    )
    precision_sufficient = bool(specification.timestamp_precision <= median_frequency)
    overlaps = _overlapping_pairs(events, specification)
    if overlaps and specification.overlap_policy == "error":
        raise ValueError("event windows overlap; pre-specify overlap_policy='drop' or 'allow'")
    overlapping_events = {event for pair in overlaps for event in pair}
    overall_start = min(specification.anticipation_start, specification.response_start)
    overall_end = max(specification.anticipation_end, specification.response_end)
    rows: list[dict[str, object]] = []
    excluded_overlap = 0
    excluded_coverage = 0
    excluded_cadence = 0
    excluded_observations = 0
    for event in events:
        exclusion_reason = ""
        if specification.overlap_policy == "drop" and event in overlapping_events:
            exclusion_reason = "overlapping event window"
            excluded_overlap += 1
        elif (
            event + overall_start < market_returns.index[0]
            or event + overall_end > market_returns.index[-1]
        ):
            exclusion_reason = "market data do not cover the full event window"
            excluded_coverage += 1
        anticipation = market_returns.loc[
            event + specification.anticipation_start : event + specification.anticipation_end
        ]
        response = market_returns.loc[
            event + specification.response_start : event + specification.response_end
        ]
        cadence_covered = _window_has_cadence_coverage(
            anticipation.index,
            event + specification.anticipation_start,
            event + specification.anticipation_end,
            cadence,
        ) and _window_has_cadence_coverage(
            response.index,
            event + specification.response_start,
            event + specification.response_end,
            cadence,
        )
        if not exclusion_reason and not cadence_covered:
            exclusion_reason = "event window violates the expected cadence"
            excluded_cadence += 1
        elif not exclusion_reason and (
            anticipation.size < specification.minimum_observations_per_window
            or response.size < specification.minimum_observations_per_window
        ):
            exclusion_reason = "insufficient observations in an event window"
            excluded_observations += 1
        included = not exclusion_reason
        rows.append(
            {
                "event_time": event,
                "anticipation_response": _aggregate_returns(
                    anticipation, specification.return_aggregation
                )
                if anticipation.size
                else np.nan,
                "response": _aggregate_returns(response, specification.return_aggregation)
                if response.size
                else np.nan,
                "anticipation_observations": int(anticipation.size),
                "response_observations": int(response.size),
                "overlap_flag": event in overlapping_events,
                "included": included,
                "exclusion_reason": exclusion_reason,
            }
        )
    event_responses = pd.DataFrame(rows).set_index("event_time")
    eligible = event_responses.loc[event_responses["included"].astype(bool)]
    if eligible.shape[0] < 2:
        raise RuntimeError("fewer than two eligible events remain after applying the specification")
    response_values = eligible["response"].to_numpy(dtype=float)
    anticipation_values = eligible["anticipation_response"].to_numpy(dtype=float)
    mean_response = float(response_values.mean())
    standard_error = float(response_values.std(ddof=1) / np.sqrt(response_values.size))
    confidence_df = response_values.size - 1
    critical_value = float(student_t.ppf((1.0 + level) / 2.0, confidence_df))
    warnings: list[str] = [
        "simultaneous-news and external eligibility rules are caller-enforced; "
        "retain the prefiltered event registry"
    ]
    if not precision_sufficient:
        warnings.append("event timestamp precision is coarser than the median data frequency")
    if overlaps and specification.overlap_policy == "allow":
        warnings.append("overlapping event windows were retained and are not independent")
    if eligible.shape[0] < 30:
        warnings.append(
            "fewer than 30 eligible events; the Student-t interval still relies on "
            "event independence and an approximately normal event-mean model"
        )
    if specification.claim_class == "causal-effect":
        warnings.append(
            "a response window alone does not identify a causal effect; document extra identification"
        )
    diagnostics = AnnouncementStudyDiagnostics(
        total_events=events.size,
        included_events=eligible.shape[0],
        excluded_events=events.size - eligible.shape[0],
        excluded_for_overlap=excluded_overlap,
        excluded_for_market_coverage=excluded_coverage,
        excluded_for_cadence=excluded_cadence,
        excluded_for_insufficient_observations=excluded_observations,
        overlapping_event_pairs=overlaps,
        median_data_frequency=median_frequency,
        expected_cadence=cadence,
        cadence_source=cadence_source,
        timestamp_precision_sufficient=precision_sufficient,
        timezone=specification.timezone,
        warnings=tuple(warnings),
    )
    half_width = critical_value * standard_error
    return AnnouncementStudyResult(
        event_responses=event_responses,
        mean_response=mean_response,
        response_standard_error=standard_error,
        confidence_interval=(mean_response - half_width, mean_response + half_width),
        confidence_degrees_of_freedom=confidence_df,
        confidence_reference="Student-t over eligible events",
        mean_anticipation_response=float(anticipation_values.mean()),
        n_events=eligible.shape[0],
        estimand=specification.estimand,
        claim_class=specification.claim_class,
        specification=specification,
        diagnostics=diagnostics,
    )


def event_window_responses(
    returns: pd.Series,
    event_times: ArrayLike,
    specification: EventWindowSpecification,
) -> pd.DataFrame:
    """Return the audited event-level table used by ``announcement_event_study``."""

    return announcement_event_study(returns, event_times, specification).event_responses.copy()


@dataclass(frozen=True)
class PlaceboStudyResult:
    """Placebo-date responses and an optional randomization-style comparison."""

    event_study: AnnouncementStudyResult
    observed_response: float | None
    empirical_two_sided_p_value: float | None
    comparison_rule: str = "plus-one absolute placebo exceedance"


def placebo_event_study(
    returns: pd.Series,
    placebo_event_times: ArrayLike,
    specification: EventWindowSpecification,
    *,
    observed_response: float | None = None,
    confidence_level: float = 0.95,
) -> PlaceboStudyResult:
    """Apply the pre-specified event design to placebo dates.

    When ``observed_response`` is supplied, the event-level placebo responses
    form an empirical reference distribution with a plus-one two-sided p-value.
    The validity still depends on how the placebo dates were sampled.
    """

    study = announcement_event_study(
        returns,
        placebo_event_times,
        specification,
        confidence_level=confidence_level,
    )
    if observed_response is None:
        observed = None
        p_value = None
    else:
        observed = float(observed_response)
        if not np.isfinite(observed):
            raise ValueError("observed_response must be finite")
        eligible = study.event_responses.loc[
            study.event_responses["included"].astype(bool), "response"
        ].to_numpy(dtype=float)
        exceedances = int(np.count_nonzero(np.abs(eligible) >= abs(observed)))
        p_value = float((exceedances + 1.0) / (eligible.size + 1.0))
    return PlaceboStudyResult(
        event_study=study,
        observed_response=observed,
        empirical_two_sided_p_value=p_value,
    )


@dataclass(frozen=True)
class ClaimMetadata:
    """What a reported estimate is allowed to claim and under which assumptions."""

    estimand: str
    claim_class: ClaimClass
    counterfactual: str | None
    identification_assumptions: tuple[str, ...]
    causal_claim_supported: bool
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.estimand, str) or not self.estimand.strip():
            raise ValueError("estimand must be a non-empty string")
        if self.claim_class not in {"association", "announcement-response", "causal-effect"}:
            raise ValueError("unknown claim_class")
        if self.counterfactual is not None and (
            not isinstance(self.counterfactual, str) or not self.counterfactual.strip()
        ):
            raise ValueError("counterfactual must be None or a non-empty string")
        if not isinstance(self.causal_claim_supported, (bool, np.bool_)):
            raise TypeError("causal_claim_supported must be a boolean")
        if isinstance(self.identification_assumptions, str):
            raise TypeError("identification_assumptions must be a tuple of strings")
        if isinstance(self.limitations, str):
            raise TypeError("limitations must be a tuple of strings")
        assumptions = tuple(self.identification_assumptions)
        limitations = tuple(self.limitations)
        if not all(isinstance(item, str) and item.strip() for item in assumptions):
            raise ValueError("identification_assumptions must contain non-empty strings")
        if not all(isinstance(item, str) and item.strip() for item in limitations):
            raise ValueError("limitations must contain non-empty strings")
        if self.causal_claim_supported and self.claim_class != "causal-effect":
            raise ValueError("causal_claim_supported requires claim_class='causal-effect'")
        if self.causal_claim_supported and (self.counterfactual is None or not assumptions):
            raise ValueError("a supported causal claim requires a counterfactual and assumptions")
        object.__setattr__(self, "causal_claim_supported", bool(self.causal_claim_supported))
        object.__setattr__(self, "identification_assumptions", assumptions)
        object.__setattr__(self, "limitations", limitations)


@dataclass(frozen=True)
class DifferenceInDifferencesResult:
    """Saturated two-group, two-period DiD coefficient and honest metadata."""

    estimate: float
    standard_error: float
    confidence_interval: tuple[float, float]
    confidence_degrees_of_freedom: int
    confidence_reference: str
    cell_means: FloatArray
    regression: OLSInferenceResult
    claim: ClaimMetadata


def two_period_did(
    outcome: ArrayLike,
    treatment: ArrayLike,
    post: ArrayLike,
    *,
    covariance_type: str = "HC3",
    clusters: ArrayLike | None = None,
    confidence_level: float = 0.95,
    claim: ClaimMetadata | None = None,
) -> DifferenceInDifferencesResult:
    """Estimate the two-by-two DiD contrast with an explicit claim audit."""

    response = np.asarray(outcome, dtype=float)
    treated = np.asarray(treatment, dtype=float)
    after = np.asarray(post, dtype=float)
    if response.ndim != 1 or response.size < 5:
        raise ValueError("outcome must be one-dimensional with at least five entries")
    if treated.shape != response.shape or after.shape != response.shape:
        raise ValueError("treatment and post must have one entry per outcome")
    if not np.all(np.isfinite(response)):
        raise ValueError("outcome must contain only finite values")
    if not np.all((treated == 0.0) | (treated == 1.0)):
        raise ValueError("treatment must contain only zero and one")
    if not np.all((after == 0.0) | (after == 1.0)):
        raise ValueError("post must contain only zero and one")
    cell_means = np.empty((2, 2), dtype=float)
    for treatment_value in (0, 1):
        for post_value in (0, 1):
            mask = (treated == treatment_value) & (after == post_value)
            if not np.any(mask):
                raise ValueError("all four treatment-by-period cells must be observed")
            cell_means[treatment_value, post_value] = response[mask].mean()
    design = np.column_stack((np.ones(response.size), treated, after, treated * after))
    regression = fit_ols_inference(
        design,
        response,
        covariance_type=covariance_type,
        clusters=clusters,
    )
    level = float(confidence_level)
    if not np.isfinite(level) or not 0.0 < level < 1.0:
        raise ValueError("confidence_level must be strictly between zero and one")
    estimate = float(regression.coefficients[3])
    standard_error = float(regression.standard_errors[3])
    cluster_count = regression.diagnostics.covariance.n_clusters
    confidence_df = (
        cluster_count - 1
        if regression.diagnostics.covariance.covariance_type == "cluster"
        and cluster_count is not None
        else regression.diagnostics.covariance.residual_degrees_of_freedom
    )
    critical_value = float(student_t.ppf((1.0 + level) / 2.0, confidence_df))
    if claim is None:
        claim = ClaimMetadata(
            estimand="treated-group change minus control-group change",
            claim_class="causal-effect",
            counterfactual="treated units' post-period outcome absent treatment",
            identification_assumptions=(
                "parallel untreated trends",
                "no anticipation",
                "no interference or composition change",
            ),
            causal_claim_supported=False,
            limitations=(
                "the two-period design cannot diagnose pre-trends",
                "the supplied data alone do not verify parallel trends",
            ),
        )
    elif not isinstance(claim, ClaimMetadata):
        raise TypeError("claim must be a ClaimMetadata or None")
    half_width = critical_value * standard_error
    return DifferenceInDifferencesResult(
        estimate=estimate,
        standard_error=standard_error,
        confidence_interval=(estimate - half_width, estimate + half_width),
        confidence_degrees_of_freedom=confidence_df,
        confidence_reference="Student-t with cluster or residual degrees of freedom",
        cell_means=cell_means,
        regression=regression,
        claim=claim,
    )
