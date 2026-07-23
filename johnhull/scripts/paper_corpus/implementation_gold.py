"""Resolve P0 implementation symbols to manually reviewed paper evidence."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from .baseline import PROJECT_ROOT
from .claim_gold import DEFAULT_CLAIM_SPECS_OUTPUT
from .gold import DEFAULT_ASSERTIONS_OUTPUT, GOLD_ROOT
from .schema import P0_PAPER_IDS

DEFAULT_IMPLEMENTATION_EVIDENCE_OUTPUT = GOLD_ROOT / "gold_implementation_evidence.json"
DEFAULT_IMPLEMENTATION_METRICS_OUTPUT = GOLD_ROOT / "gold_implementation_metrics.json"

IMPLEMENTATION_COMPONENTS: tuple[dict[str, Any], ...] = (
    {
        "component_id": "hull-white-state-and-curve",
        "implementation": {
            "path": "johnhull/hullkit/src/hullkit/hull_white.py",
            "symbols": (
                "hw_b",
                "hw_phi",
                "hw_discount_bond",
                "hw_exact_transition",
                "simulate_hw_paths",
                "calibrate_hw1f",
            ),
        },
        "claim_ids": (
            "1990-hull-white-interest-rate-derivative-securities:claim:curve-fit",
            "1990-hull-white-interest-rate-derivative-securities:claim:short-rate-dynamics",
            "1990-hull-white-interest-rate-derivative-securities:claim:bond-loading",
            "1990-hull-white-interest-rate-derivative-securities:claim:calibration",
        ),
        "equation_assertion_ids": (
            "hw-p4-short-rate-dynamics",
            "hw-p6-vasicek-b",
            "hw-p6-mean-reversion",
        ),
        "table_assertion_ids": (),
    },
    {
        "component_id": "hull-white-bond-options",
        "implementation": {
            "path": "johnhull/hullkit/src/hullkit/hull_white.py",
            "symbols": ("hw_zcb_option", "hw_jamshidian_swaption"),
        },
        "claim_ids": (
            "1990-hull-white-interest-rate-derivative-securities:claim:analytic-approximation",
        ),
        "equation_assertion_ids": (
            "hw-p7-zcb-call",
            "hw-p7-zcb-call-d1",
            "hw-p7-zcb-call-total-variance",
        ),
        "table_assertion_ids": (
            "hw-p17-table4-ext-vas-102",
            "hw-p17-table4-cir-102",
            "hw-p17-table3-ext-vas-200-100",
            "hw-p17-table4-cir-200-100",
        ),
    },
    {
        "component_id": "heston-pricing",
        "implementation": {
            "path": "johnhull/hullkit/src/hullkit/heston.py",
            "symbols": ("heston_cf", "heston_mc_price"),
        },
        "claim_ids": (
            "1993-heston-closed-form-stochastic-volatility:claim:closed-form",
            "1993-heston-closed-form-stochastic-volatility:claim:variance-process",
            "1993-heston-closed-form-stochastic-volatility:claim:volatility-risk-premium",
            "1993-heston-closed-form-stochastic-volatility:claim:characteristic-function",
            "1993-heston-closed-form-stochastic-volatility:claim:correlation-skew",
        ),
        "equation_assertion_ids": (
            "heston-p2-asset-dynamics",
            "heston-p3-variance-dynamics",
            "heston-p5-g",
            "heston-p5-d",
        ),
        "table_assertion_ids": (),
    },
    {
        "component_id": "evt-var-es",
        "implementation": {
            "path": "johnhull/hullkit/src/hullkit/tail_risk.py",
            "symbols": (
                "filtered_historical_var_es",
                "fit_gpd_pot",
                "evt_var_es",
                "mean_excess",
            ),
        },
        "claim_ids": (
            "2000-mcneil-frey-tail-risk-evt:claim:two-stage-method",
            "2000-mcneil-frey-tail-risk-evt:claim:conditional-risk",
            "2000-mcneil-frey-tail-risk-evt:claim:es-location-scale",
            "2000-mcneil-frey-tail-risk-evt:claim:gpd-tail",
            "2000-mcneil-frey-tail-risk-evt:claim:es-backtest",
        ),
        "equation_assertion_ids": (
            "mcneil-frey-p8-gpd-quantile",
            "mcneil-frey-p14-es",
            "mcneil-frey-p14-gpd-mean",
        ),
        "table_assertion_ids": (),
    },
    {
        "component_id": "sabr-smile-and-hedging",
        "implementation": {
            "path": "johnhull/hullkit/src/hullkit/sabr.py",
            "symbols": (
                "sabr_implied_vol",
                "sabr_smile_delta",
                "sabr_greeks",
                "calibrate_sabr",
            ),
        },
        "secondary_implementation": {
            "path": "johnhull/hullkit/src/hullkit/sabr_normal.py",
            "symbols": (
                "normal_sabr_implied_vol",
                "shifted_sabr_implied_vol",
                "bartlett_delta",
                "hagan_error_diagnostics",
            ),
        },
        "claim_ids": (
            "2002-hagan-et-al-managing-smile-risk:claim:local-vol-warning",
            "2002-hagan-et-al-managing-smile-risk:claim:sabr-dynamics",
            "2002-hagan-et-al-managing-smile-risk:claim:singular-perturbation",
            "2002-hagan-et-al-managing-smile-risk:claim:calibration",
            "2002-hagan-et-al-managing-smile-risk:claim:single-expiry-scope",
        ),
        "equation_assertion_ids": (
            "hagan-p8-sabr-forward-dynamics",
            "hagan-p8-sabr-volatility-dynamics",
            "hagan-p8-sabr-correlation",
            "hagan-p9-sabr-implied-volatility",
            "hagan-p9-sabr-z",
            "hagan-p9-sabr-xz",
        ),
        "table_assertion_ids": (),
    },
    {
        "component_id": "jarrow-yildirim-inflation",
        "implementation": {
            "path": "johnhull/hullkit/src/hullkit/jarrow_yildirim.py",
            "symbols": (
                "jy_correlation_matrix",
                "jy_cpi_forward",
                "jy_cpi_log_covariance",
                "jy_payment_forward_cpi",
                "jy_expected_cpi_ratio",
                "jy_cpi_option",
                "jy_zcis_value",
                "jy_yoy_value",
                "simulate_jy_forward_levels",
                "simulate_jy_paths",
            ),
        },
        "claim_ids": (
            "2003-jarrow-yildirim-inflation-hjm:claim:foreign-currency-analogy",
            "2003-jarrow-yildirim-inflation-hjm:claim:curve-and-factor-fit",
            "2003-jarrow-yildirim-inflation-hjm:claim:q-martingales",
            "2003-jarrow-yildirim-inflation-hjm:claim:cpi-q-dynamics",
            "2003-jarrow-yildirim-inflation-hjm:claim:inflation-risk-premium",
        ),
        "equation_assertion_ids": (
            "jy-p7-q-martingales",
            "jy-p9-cpi-q-dynamics",
            "jy-p21-cpi-call-payoff",
            "jy-p21-cpi-call-risk-neutral-value",
            "jy-p21-cpi-call-closed-form",
        ),
        "table_assertion_ids": (),
    },
    {
        "component_id": "inflation-swaps-and-seasonality",
        "implementation": {
            "path": "johnhull/hullkit/src/hullkit/inflation.py",
            "symbols": (
                "MonthlySeasonality",
                "cpi_observation",
                "seasonal_forward_index",
                "zcis_cashflow",
                "zcis_npv",
                "zcis_par_rate",
                "yoy_rate",
                "yoy_swap_npv",
            ),
        },
        "claim_ids": (
            "2009-canty-seasonally-adjusted-inflation-linked-bonds:claim:bei-seasonality-warning",
            "2009-canty-seasonally-adjusted-inflation-linked-bonds:claim:multiplicative-seasonality",
            "2009-canty-seasonally-adjusted-inflation-linked-bonds:claim:seasonally-adjusted-price",
            "2009-canty-seasonally-adjusted-inflation-linked-bonds:claim:repeating-monthly-factors",
            "2009-canty-seasonally-adjusted-inflation-linked-bonds:claim:lagged-interpolation",
            "2013-wu-inflation-rate-derivatives:claim:market-model",
            "2013-wu-inflation-rate-derivatives:claim:foreign-currency-analogy",
            "2013-wu-inflation-rate-derivatives:claim:zciis-payoff",
            "2013-wu-inflation-rate-derivatives:claim:fisher-relation",
            "2013-wu-inflation-rate-derivatives:claim:forward-measure",
        ),
        "equation_assertion_ids": (
            "canty-p2-seasonality-decomposition",
            "wu-p7-zciis-fixed-payoff",
            "wu-p8-fisher-relation",
            "wu-p9-yoy-floating-payoff",
            "wu-p14-forward-measure-density",
        ),
        "table_assertion_ids": (),
    },
    {
        "component_id": "backward-looking-rfr",
        "implementation": {
            "path": "johnhull/hullkit/src/hullkit/rfr.py",
            "symbols": (
                "daily_accrual_schedule",
                "compounded_rfr",
                "rfr_coupon",
                "RfrCurve",
                "collateralized_present_value",
            ),
        },
        "claim_ids": (
            "2019-lyashenko-mercurio-backward-looking-rates:claim:unified-rates",
            "2019-lyashenko-mercurio-backward-looking-rates:claim:risk-neutral-numeraire",
            "2019-lyashenko-mercurio-backward-looking-rates:claim:extended-forward-measure",
            "2019-lyashenko-mercurio-backward-looking-rates:claim:measure-drift-adjustment",
            "2019-lyashenko-mercurio-backward-looking-rates:claim:analytics-and-implementation",
        ),
        "equation_assertion_ids": (
            "lyashenko-p4-risk-neutral-bond-price",
            "lyashenko-p4-bond-after-maturity",
        ),
        "table_assertion_ids": (),
    },
    {
        "component_id": "jgbi-conventions-and-floor",
        "implementation": {
            "path": "johnhull/hullkit/src/hullkit/jgbi.py",
            "symbols": (
                "jgbi_reference_index",
                "jgbi_indexation_coefficient",
                "jgbi_cashflows",
                "jgbi_accrued_interest",
                "jgbi_real_clean_price",
                "jgbi_nominal_settlement_amount",
                "jgbi_real_yield",
                "jgbi_nominal_present_value",
                "jgbi_breakeven_inflation",
                "jgbi_deflation_floor_black",
                "jgbi_deflation_floor_jy",
                "jgbi_deflation_floor_jy_mc",
                "jgbi_floor_adjusted_price",
                "jgbi_floor_risk",
            ),
        },
        "claim_ids": (
            "2021-mof-jgbi-indexation-notice:claim:notional-principal",
            "2021-mof-jgbi-indexation-notice:claim:coefficient-regime",
            "2021-mof-jgbi-indexation-notice:claim:cpi-definition",
            "2021-mof-jgbi-indexation-notice:claim:issue-date-definition",
            "2021-mof-jgbi-indexation-notice:claim:reopening-rule",
            "2024-mof-jgbi-bei-guide:claim:bei-definition-bias",
            "2024-mof-jgbi-bei-guide:claim:principal-floor",
            "2024-mof-jgbi-bei-guide:claim:floor-coupon-scope",
            "2024-mof-jgbi-bei-guide:claim:indexation-coefficient",
            "2024-mof-jgbi-bei-guide:claim:lag-and-interpolation",
        ),
        "equation_assertion_ids": (
            "jgbi-p1-notional-principal",
            "jgbi-p5-reference-index-on-tenth",
            "jgbi-p5-reference-index-after-tenth",
            "jgbi-p6-reference-index-before-tenth",
            "jy-p21-cpi-call-payoff",
            "jy-p21-cpi-call-risk-neutral-value",
            "jy-p21-cpi-call-closed-form",
        ),
        "table_assertion_ids": (),
    },
)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _source_symbols(relative_path: str) -> set[str]:
    source = PROJECT_ROOT.parent / relative_path
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    return {
        node.name
        for node in tree.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _implementation_status(component: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    resolved: list[dict[str, Any]] = []
    missing_count = 0
    for key in ("implementation", "secondary_implementation"):
        spec = component.get(key)
        if spec is None:
            continue
        defined = _source_symbols(str(spec["path"]))
        symbols = [str(value) for value in spec["symbols"]]
        missing = sorted(set(symbols) - defined)
        missing_count += len(missing)
        resolved.append(
            {
                "path": spec["path"],
                "symbols": symbols,
                "missing_symbols": missing,
                "status": "pass" if not missing else "fail",
            }
        )
    return resolved, missing_count


def build_implementation_evidence(corpus_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build resolved P0 implementation evidence and aggregate coverage metrics."""

    assertions = _read_jsonl(DEFAULT_ASSERTIONS_OUTPUT)
    assertion_by_id = {item["assertion_id"]: item for item in assertions}
    claims = _read_jsonl(DEFAULT_CLAIM_SPECS_OUTPUT)
    claim_by_id = {item["claim_id"]: item for item in claims}

    equation_by_assertion: dict[str, dict[str, Any]] = {}
    table_cell_by_assertion: dict[str, tuple[str, dict[str, Any]]] = {}
    for paper_dir in sorted(corpus_root.iterdir()):
        equation_path = paper_dir / "equations.jsonl"
        if equation_path.is_file():
            for equation in _read_jsonl(equation_path):
                assertion_id = equation.get("assertion_id")
                if assertion_id:
                    equation_by_assertion[str(assertion_id)] = equation
        table_path = paper_dir / "tables.jsonl"
        if table_path.is_file():
            for table in _read_jsonl(table_path):
                for cell in table["cells"]:
                    assertion_id = cell.get("assertion_id")
                    if assertion_id:
                        table_cell_by_assertion[str(assertion_id)] = (table["table_id"], cell)

    components: list[dict[str, Any]] = []
    mapped_claims: set[str] = set()
    mapped_equations: set[str] = set()
    mapped_tables: set[str] = set()
    covered_papers: set[str] = set()
    missing_symbols = 0
    unresolved_evidence: list[str] = []

    for definition in IMPLEMENTATION_COMPONENTS:
        implementations, component_missing_symbols = _implementation_status(definition)
        missing_symbols += component_missing_symbols
        resolved_claims: list[dict[str, Any]] = []
        for claim_id in definition["claim_ids"]:
            claim = claim_by_id.get(claim_id)
            status = (
                "pass"
                if claim
                and claim["verification_status"] == "verified"
                and claim["source_review_status"] == "manual_page_review_pass"
                else "fail"
            )
            if status == "fail":
                unresolved_evidence.append(claim_id)
            else:
                mapped_claims.add(claim_id)
                covered_papers.add(str(claim["paper_id"]))
            resolved_claims.append({"claim_id": claim_id, "status": status})

        resolved_equations: list[dict[str, Any]] = []
        for assertion_id in definition["equation_assertion_ids"]:
            assertion = assertion_by_id.get(assertion_id)
            equation = equation_by_assertion.get(assertion_id)
            status = (
                "pass"
                if assertion
                and equation
                and assertion["verification_status"] == "verified"
                and equation["verification_status"] == "verified"
                and equation["latex_compile_status"] == "passed"
                and equation["render_validation_status"] == "passed"
                and equation["source_comparison_status"] == "manual_review_pass"
                else "fail"
            )
            if status == "fail":
                unresolved_evidence.append(assertion_id)
            else:
                mapped_equations.add(assertion_id)
                covered_papers.add(str(assertion["paper_id"]))
            resolved_equations.append(
                {
                    "assertion_id": assertion_id,
                    "paper_id": assertion.get("paper_id") if assertion else None,
                    "page_number": assertion.get("page_number") if assertion else None,
                    "source_bbox_normalized": (
                        assertion.get("source_bbox_normalized") if assertion else None
                    ),
                    "status": status,
                }
            )

        resolved_tables: list[dict[str, Any]] = []
        for assertion_id in definition["table_assertion_ids"]:
            assertion = assertion_by_id.get(assertion_id)
            resolved = table_cell_by_assertion.get(assertion_id)
            status = (
                "pass"
                if assertion
                and resolved
                and assertion["verification_status"] == "verified"
                and resolved[1]["verification_status"] == "verified"
                else "fail"
            )
            if status == "fail":
                unresolved_evidence.append(assertion_id)
            else:
                mapped_tables.add(assertion_id)
                covered_papers.add(str(assertion["paper_id"]))
            resolved_tables.append(
                {
                    "assertion_id": assertion_id,
                    "paper_id": assertion.get("paper_id") if assertion else None,
                    "page_number": assertion.get("page_number") if assertion else None,
                    "source_bbox_normalized": (
                        assertion.get("source_bbox_normalized") if assertion else None
                    ),
                    "status": status,
                }
            )

        component_statuses = [item["status"] for item in implementations]
        component_statuses.extend(item["status"] for item in resolved_claims)
        component_statuses.extend(item["status"] for item in resolved_equations)
        component_statuses.extend(item["status"] for item in resolved_tables)
        components.append(
            {
                "component_id": definition["component_id"],
                "implementations": implementations,
                "claims": resolved_claims,
                "equations": resolved_equations,
                "table_cells": resolved_tables,
                "status": "pass" if set(component_statuses) == {"pass"} else "fail",
            }
        )

    required_equations = {
        item["assertion_id"]
        for item in assertions
        if item["paper_id"] in P0_PAPER_IDS and item["kind"] == "display_formula"
    }
    required_tables = {
        item["assertion_id"]
        for item in assertions
        if item["paper_id"] in P0_PAPER_IDS and item["kind"] == "table_cell"
    }
    missing_equation_mappings = sorted(required_equations - mapped_equations)
    missing_table_mappings = sorted(required_tables - mapped_tables)
    missing_papers = sorted(set(P0_PAPER_IDS) - covered_papers)
    metrics = {
        "gold_implementation_metrics_version": "1.0.0",
        "audit_basis": "AST-resolved implementation symbols plus manually reviewed claim, formula, and table evidence",
        "component_count": len(components),
        "passing_component_count": sum(item["status"] == "pass" for item in components),
        "implementation_symbol_count": sum(
            len(item["symbols"])
            for component in components
            for item in component["implementations"]
        ),
        "missing_implementation_symbol_count": missing_symbols,
        "mapped_claim_count": len(mapped_claims),
        "required_p0_formula_count": len(required_equations),
        "mapped_p0_formula_count": len(required_equations & mapped_equations),
        "p0_formula_mapping_rate": (
            len(required_equations & mapped_equations) / len(required_equations)
            if required_equations
            else 1.0
        ),
        "required_p0_table_assertion_count": len(required_tables),
        "mapped_p0_table_assertion_count": len(required_tables & mapped_tables),
        "p0_table_assertion_mapping_rate": (
            len(required_tables & mapped_tables) / len(required_tables) if required_tables else 1.0
        ),
        "p0_paper_count": len(P0_PAPER_IDS),
        "covered_p0_paper_count": len(set(P0_PAPER_IDS) & covered_papers),
        "p0_paper_coverage_rate": len(set(P0_PAPER_IDS) & covered_papers) / len(P0_PAPER_IDS),
        "missing_equation_mappings": missing_equation_mappings,
        "missing_table_mappings": missing_table_mappings,
        "missing_p0_papers": missing_papers,
        "unresolved_evidence": sorted(set(unresolved_evidence)),
        "overall_status": (
            "pass"
            if not missing_symbols
            and not missing_equation_mappings
            and not missing_table_mappings
            and not missing_papers
            and not unresolved_evidence
            and all(item["status"] == "pass" for item in components)
            else "fail"
        ),
    }
    evidence = {
        "gold_implementation_evidence_version": "1.1.0",
        "components": components,
    }
    return evidence, metrics


def validate_implementation_evidence(evidence: dict[str, Any], metrics: dict[str, Any]) -> None:
    """Fail closed unless every P0 implementation evidence gate passes."""

    if not evidence["components"] or metrics["component_count"] != len(evidence["components"]):
        raise ValueError("implementation evidence components are missing or inconsistent")
    if metrics["overall_status"] != "pass":
        raise ValueError("P0 implementation evidence is incomplete")
    for key in (
        "p0_formula_mapping_rate",
        "p0_table_assertion_mapping_rate",
        "p0_paper_coverage_rate",
    ):
        if metrics[key] != 1.0:
            raise ValueError(f"implementation evidence gate failed: {key}")


def render_json(value: dict[str, Any]) -> str:
    """Serialize a deterministic evidence artifact."""

    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
