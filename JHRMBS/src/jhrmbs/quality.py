from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal, cast

import pandas as pd

from jhrmbs.exceptions import DataQualityError

Severity = Literal["critical", "high", "medium", "low"]


@dataclass(frozen=True)
class QualityFinding:
    check: str
    severity: Severity
    failed_count: int
    failed_rate: float
    message: str
    examples: tuple[dict[str, Any], ...] = ()


def _examples(
    frame: pd.DataFrame, columns: list[str], limit: int = 5
) -> tuple[dict[str, Any], ...]:
    if frame.empty:
        return ()
    records = frame.loc[:, [column for column in columns if column in frame.columns]].head(limit)
    values = records.astype(object).where(pd.notna(records), None).to_dict("records")
    return tuple(cast(list[dict[str, Any]], values))


def validate_panel(
    panel: pd.DataFrame,
    *,
    fail_on_critical: bool = True,
    as_of: pd.Timestamp | None = None,
) -> dict[str, Any]:
    findings: list[QualityFinding] = []
    row_count = len(panel)
    denominator = max(row_count, 1)

    required = ["issue_id", "payment_month", "scheduled_factor", "face_amount_jpy", "coupon_pct"]
    missing_columns = [column for column in required if column not in panel.columns]
    if missing_columns:
        findings.append(
            QualityFinding(
                check="required_columns",
                severity="critical",
                failed_count=len(missing_columns),
                failed_rate=1.0,
                message=f"Missing required columns: {', '.join(missing_columns)}",
            )
        )
    else:
        null_mask = panel[required].isna().any(axis=1)
        if null_mask.any():
            findings.append(
                QualityFinding(
                    check="required_values",
                    severity="critical",
                    failed_count=int(null_mask.sum()),
                    failed_rate=float(null_mask.mean()),
                    message="Required grain or instrument fields contain nulls.",
                    examples=_examples(panel[null_mask], ["issue_id", "payment_month"]),
                )
            )

    if {"issue_id", "payment_month"}.issubset(panel.columns):
        duplicate_mask = panel.duplicated(["issue_id", "payment_month"], keep=False)
        if duplicate_mask.any():
            findings.append(
                QualityFinding(
                    check="grain_uniqueness",
                    severity="critical",
                    failed_count=int(duplicate_mask.sum()),
                    failed_rate=float(duplicate_mask.mean()),
                    message="Issue-month grain is not unique.",
                    examples=_examples(panel[duplicate_mask], ["issue_id", "payment_month"]),
                )
            )

    for column, lower, upper, severity in (
        ("scheduled_factor", 0.0, 1.000001, "critical"),
        ("actual_factor", 0.0, 1.000001, "critical"),
        ("voluntary_cpr_pct", 0.0, 100.0, "high"),
        ("wac_pct", 0.0, 20.0, "high"),
        ("wam_years", 0.0, 50.0, "high"),
        ("wala_months", 0.0, 600.0, "high"),
    ):
        if column not in panel.columns:
            continue
        values = pd.to_numeric(panel[column], errors="coerce")
        invalid = values.notna() & ((values < lower) | (values > upper))
        if invalid.any():
            findings.append(
                QualityFinding(
                    check=f"{column}_range",
                    severity=severity,  # type: ignore[arg-type]
                    failed_count=int(invalid.sum()),
                    failed_rate=float(invalid.sum() / denominator),
                    message=f"{column} is outside [{lower}, {upper}].",
                    examples=_examples(panel[invalid], ["issue_id", "payment_month", column]),
                )
            )

    if {"issue_id", "scheduled_factor"}.issubset(panel.columns):
        ordered = panel.sort_values(["issue_id", "payment_month"])
        increase = ordered.groupby("issue_id")["scheduled_factor"].diff() > 1e-8
        if increase.any():
            findings.append(
                QualityFinding(
                    check="scheduled_factor_monotonicity",
                    severity="critical",
                    failed_count=int(increase.sum()),
                    failed_rate=float(increase.sum() / denominator),
                    message="Scheduled factor increases within an issue.",
                    examples=_examples(
                        ordered[increase], ["issue_id", "payment_month", "scheduled_factor"]
                    ),
                )
            )

    if {"issue_id", "actual_factor"}.issubset(panel.columns):
        observed = panel[panel["actual_factor"].notna()].sort_values(["issue_id", "payment_month"])
        increase = observed.groupby("issue_id")["actual_factor"].diff() > 1e-8
        if increase.any():
            findings.append(
                QualityFinding(
                    check="actual_factor_monotonicity",
                    severity="high",
                    failed_count=int(increase.sum()),
                    failed_rate=float(increase.sum() / max(len(observed), 1)),
                    message="Actual factor increases; investigate replacement/rescheduling or format drift.",
                    examples=_examples(
                        observed[increase], ["issue_id", "payment_month", "actual_factor"]
                    ),
                )
            )

    if "reconciliation_bps" in panel.columns:
        reconciliation = pd.to_numeric(panel["reconciliation_bps"], errors="coerce").abs()
        material = reconciliation > 50.0
        if material.any():
            findings.append(
                QualityFinding(
                    check="factor_decrement_reconciliation",
                    severity="medium",
                    failed_count=int(material.sum()),
                    failed_rate=float(material.sum() / max(reconciliation.notna().sum(), 1)),
                    message=(
                        "Factor-implied total decrement differs from combined published components by more "
                        "than 50 bp. This is diagnostic, not an equality requirement."
                    ),
                    examples=_examples(
                        panel[material], ["issue_id", "payment_month", "reconciliation_bps"]
                    ),
                )
            )

    observed_month: pd.Timestamp | None = None
    staleness_months: int | None = None
    if {"payment_month", "actual_factor"}.issubset(panel.columns):
        observed_values = panel.loc[panel["actual_factor"].notna(), "payment_month"]
        if not observed_values.empty:
            observed_month = pd.Timestamp(observed_values.max())
            reference = pd.Timestamp(as_of or pd.Timestamp.now()).normalize()
            staleness_months = (
                reference.to_period("M").ordinal - observed_month.to_period("M").ordinal
            )
            if staleness_months > 3:
                findings.append(
                    QualityFinding(
                        check="freshness",
                        severity="medium",
                        failed_count=1,
                        failed_rate=1.0,
                        message=(
                            f"Latest observed payment month is {observed_month:%Y-%m}; "
                            f"{staleness_months} months behind the validation month."
                        ),
                    )
                )

    report = {
        "dataset": "jhf_issue_month_panel",
        "grain": "one row per issue_id and payment_month",
        "row_count": row_count,
        "issue_count": int(panel["issue_id"].nunique()) if "issue_id" in panel else 0,
        "finding_count": len(findings),
        "critical_count": sum(finding.severity == "critical" for finding in findings),
        "latest_observed_payment_month": str(observed_month.date()) if observed_month else None,
        "staleness_months": staleness_months,
        "findings": [asdict(finding) for finding in findings],
    }
    if fail_on_critical and report["critical_count"]:
        names = ", ".join(finding.check for finding in findings if finding.severity == "critical")
        raise DataQualityError(f"critical panel checks failed: {names}")
    return report


def validate_features(features: pd.DataFrame) -> dict[str, Any]:
    target_source = (
        features["target_smm"]
        if "target_smm" in features
        else pd.Series(float("nan"), index=features.index)
    )
    target = pd.to_numeric(target_source, errors="coerce")
    observed = target.notna()
    invalid = observed & ((target < 0.0) | (target > 1.0))
    duplicate_count = int(features.duplicated(["issue_id", "payment_month"]).sum())
    rate_missing = (
        float(features.loc[observed, "rate_feature_pct"].isna().mean()) if observed.any() else 1.0
    )
    return {
        "dataset": "model_features",
        "grain": "one row per issue_id and prediction payment_month",
        "row_count": len(features),
        "observed_target_rows": int(observed.sum()),
        "invalid_target_rows": int(invalid.sum()),
        "duplicate_rows": duplicate_count,
        "rate_feature_missing_rate": rate_missing,
        "status": "pass" if not invalid.any() and duplicate_count == 0 else "fail",
    }
