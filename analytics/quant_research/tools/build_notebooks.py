"""Regenerate the B1-B10 textbook notebooks from Python builders.

Run from ``analytics/quant_research``::

    python tools/build_notebooks.py
    python tools/build_notebooks.py 02 05
    python tools/build_notebooks.py --check

``--check`` builds into a temporary directory, validates notebook structure,
compiles every code cell, and checks that two independent generations are
byte-identical.  It never overwrites committed notebooks.
"""

from __future__ import annotations

import argparse
import importlib
import pathlib
import re
import sys
import tempfile

import nbformat

TOOLS = pathlib.Path(__file__).resolve().parent
PROJECT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

NOTEBOOKS = [
    ("build_nb00", "00_overview"),
    ("build_nb01", "01_week1_least_squares"),
    ("build_nb02", "02_week2_numerical_stability"),
    ("build_nb03", "03_week3_svd_pca_yield_curve"),
    ("build_nb04", "04_week4_regularization_curve_fitting"),
    ("build_nb05", "05_b1_project_jgb_curve_fitter"),
    ("build_nb06", "06_b2_overview"),
    ("build_nb07", "07_week5_conditional_probability"),
    ("build_nb08", "08_week6_convergence_heavy_tails"),
    ("build_nb09", "09_week7_markov_martingales"),
    ("build_nb10", "10_week8_brownian_monte_carlo"),
    ("build_nb11", "11_b2_project_monte_carlo_library"),
    ("build_nb12", "12_b3_overview"),
    ("build_nb13", "13_week9_likelihood_estimands"),
    ("build_nb14", "14_week10_testing_resampling"),
    ("build_nb15", "15_week11_robust_inference"),
    ("build_nb16", "16_week12_causal_event_study"),
    ("build_nb17", "17_b3_project_boj_announcement_study"),
    ("build_nb18", "18_b4_overview"),
    ("build_nb19", "19_week13_convex_modeling"),
    ("build_nb20", "20_week14_duality_kkt_sensitivity"),
    ("build_nb21", "21_week15_optimization_algorithms"),
    ("build_nb22", "22_week16_research_software"),
    ("build_nb23", "23_b4_project_constrained_curve_fitter"),
    ("build_nb24", "24_b5_overview"),
    ("build_nb25", "25_week17_learning_baselines"),
    ("build_nb26", "26_week18_regularized_models"),
    ("build_nb27", "27_week19_classification_calibration"),
    ("build_nb28", "28_week20_validation_pipelines"),
    ("build_nb29", "29_b5_project_treasury_baseline_pipeline"),
    ("build_nb30", "30_b6_overview"),
    ("build_nb31", "31_week21_trees_boosting"),
    ("build_nb32", "32_week22_kernels_gaussian_processes"),
    ("build_nb33", "33_week23_unsupervised_regimes"),
    ("build_nb34", "34_week24_evaluation_under_shift"),
    ("build_nb35", "35_b6_project_treasury_model_tournament"),
    ("build_nb36", "36_b7_overview"),
    ("build_nb37", "37_week25_stationarity_arima"),
    ("build_nb38", "38_week26_var_cointegration"),
    ("build_nb39", "39_week27_state_space_dns"),
    ("build_nb40", "40_week28_volatility_breaks"),
    ("build_nb41", "41_b7_project_dynamic_treasury_curve"),
    ("build_nb42", "42_b8_overview"),
    ("build_nb43", "43_week29_bayesian_foundations"),
    ("build_nb44", "44_week30_hierarchical_models"),
    ("build_nb45", "45_week31_graphical_latent_hmm"),
    ("build_nb46", "46_week32_mcmc_approximate_inference"),
    ("build_nb47", "47_b8_project_treasury_regime_uncertainty"),
    ("build_nb48", "48_b9_overview"),
    ("build_nb49", "49_week33_neural_networks_backprop"),
    ("build_nb50", "50_week34_sequence_models"),
    ("build_nb51", "51_week35_attention_transformers"),
    ("build_nb52", "52_week36_financial_nlp_multimodal"),
    ("build_nb53", "53_b9_project_sec_filing_forecast"),
    ("build_nb54", "54_b10_overview"),
    ("build_nb55", "55_week37_performance_numerical_computing"),
    ("build_nb56", "56_week38_research_software_engineering"),
    ("build_nb57", "57_week39_data_systems_pit"),
    ("build_nb58", "58_week40_experiment_infrastructure"),
    ("build_nb59", "59_b10_project_reproducible_research_package"),
]

_CJK = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")
_MATH = re.compile(r"\$\$(.*?)\$\$|(?<!\$)\$(?!\$)(.*?)(?<!\$)\$(?!\$)", re.DOTALL)
_REQUIRED_SECTIONS = (
    "学習目標",
    "前提知識",
    "失敗モード",
    "段階別演習",
    "Exit Criteria",
    "出典",
)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chapters", nargs="*", help="chapter numbers, for example 01 04")
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate deterministic generation without overwriting notebooks",
    )
    return parser.parse_args(argv)


def _select(chapters: list[str]) -> list[tuple[str, str]]:
    if not chapters:
        return NOTEBOOKS
    selected: list[tuple[str, str]] = []
    for chapter in chapters:
        prefix = chapter.zfill(2)
        matches = [entry for entry in NOTEBOOKS if entry[1].startswith(prefix)]
        if not matches:
            known = ", ".join(stem[:2] for _, stem in NOTEBOOKS)
            raise SystemExit(f"unknown chapter {chapter!r}; known chapters: {known}")
        selected.extend(matches)
    return selected


def _generate(selected: list[tuple[str, str]], output_dir: pathlib.Path) -> list[pathlib.Path]:
    import nbkit

    paths: list[pathlib.Path] = []
    for module_name, stem in selected:
        module = importlib.import_module(module_name)
        paths.append(nbkit.build(module.cells, output_dir / f"{stem}.ipynb"))
    return paths


def _validate_code(paths: list[pathlib.Path]) -> None:
    for path in paths:
        notebook = nbformat.read(path, as_version=4)
        nbformat.validate(notebook)
        markdown = "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "markdown")
        missing = [section for section in _REQUIRED_SECTIONS if section not in markdown]
        if missing:
            raise ValueError(f"{path.name} is missing required sections: {missing}")

        all_code = "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "code")
        if "plotly" not in all_code.lower() or ".show()" not in all_code:
            raise ValueError(f"{path.name} must contain a runnable Plotly visualization")

        for math_match in _MATH.finditer(markdown):
            math = math_match.group(1) if math_match.group(1) is not None else math_match.group(2)
            if _CJK.search(math):
                raise ValueError(f"{path.name} contains Japanese inside LaTeX: {math!r}")

        for cell_number, cell in enumerate(notebook.cells, start=1):
            if cell.cell_type != "code":
                continue
            if _CJK.search(cell.source):
                raise ValueError(f"{path.name}: code cell {cell_number} contains Japanese")
            compile(cell.source, f"{path.name}:cell-{cell_number}", "exec")


def _check(selected: list[tuple[str, str]]) -> int:
    with tempfile.TemporaryDirectory(prefix="quant_nb_a_") as first_dir_name:
        with tempfile.TemporaryDirectory(prefix="quant_nb_b_") as second_dir_name:
            first_dir = pathlib.Path(first_dir_name)
            second_dir = pathlib.Path(second_dir_name)
            first_paths = _generate(selected, first_dir)
            second_paths = _generate(selected, second_dir)
            _validate_code(first_paths)
            for first, second in zip(first_paths, second_paths, strict=True):
                if first.read_bytes() != second.read_bytes():
                    raise SystemExit(f"non-deterministic generation: {first.name}")
    print(f"checked {len(selected)} notebooks: valid Python and deterministic JSON")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    selected = _select(args.chapters)
    if args.check:
        return _check(selected)
    paths = _generate(selected, PROJECT / "notebooks")
    _validate_code(paths)
    print(f"generated {len(paths)} notebooks; execute them before publication")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
