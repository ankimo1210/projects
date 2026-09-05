from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pandas as pd

from quantcurve.cli import build_parser, main
from synthetic import clean_frame, write_frame

SRC = str(Path(__file__).resolve().parents[1] / "src")
def _benchmark_data() -> Path:
    """Locate the public data set without hardcoding anyone's home directory.

    Order: the QUANTCURVE_MARKET_DATA environment variable, then the conventional
    ``input/market_data/market_observations.csv`` relative to any ancestor of the
    project root.  Absent all of that, the end-to-end test skips itself.
    """
    override = os.environ.get("QUANTCURVE_MARKET_DATA")
    if override:
        return Path(override)
    relative = Path("input") / "market_data" / "market_observations.csv"
    root = Path(__file__).resolve().parent
    for ancestor in [root, *root.parents]:
        candidate = ancestor / relative
        if candidate.is_file():
            return candidate
    return root / relative


BENCHMARK_DATA = _benchmark_data()
CONTRACT_FILES = (
    "curves/curve.csv",
    "diagnostics/cleaning.csv",
    "diagnostics/repricing.csv",
    "diagnostics/risk.csv",
    "diagnostics/model_comparison.json",
    "diagnostics/sensitivity.json",
    "charts/zero_curve.png",
    "charts/forward_curve.png",
    "charts/repricing.png",
    "charts/model_comparison.png",
    "reports/research_report.html",
)


def invoke(argv: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        try:
            code = main(argv)
        except SystemExit as exc:  # argparse
            code = int(exc.code or 0)
    return code, out.getvalue(), err.getvalue()


class TestArgumentParsing(unittest.TestCase):
    def test_the_mandated_arguments_are_accepted(self) -> None:
        args = build_parser().parse_args(
            [
                "run",
                "--market-data", "/tmp/market.csv",
                "--output-dir", "/tmp/out",
                "--valuation-date", "2026-01-15",
            ]
        )
        self.assertEqual(args.command, "run")
        self.assertEqual(str(args.market_data), "/tmp/market.csv")
        self.assertEqual(str(args.output_dir), "/tmp/out")
        self.assertEqual(args.valuation_date, "2026-01-15")

    def test_missing_required_arguments_are_rejected(self) -> None:
        for argv in (
            ["run", "--output-dir", "/tmp/out", "--valuation-date", "2026-01-15"],
            ["run", "--market-data", "/tmp/m.csv", "--valuation-date", "2026-01-15"],
            ["run", "--market-data", "/tmp/m.csv", "--output-dir", "/tmp/out"],
        ):
            code, _, _ = invoke(argv)
            self.assertNotEqual(code, 0)


class TestErrorPaths(unittest.TestCase):
    def test_a_missing_file_exits_nonzero_with_an_actionable_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, _, err = invoke(
                [
                    "run",
                    "--market-data", str(Path(tmp) / "absent.csv"),
                    "--output-dir", str(Path(tmp) / "out"),
                    "--valuation-date", "2026-01-15",
                ]
            )
        self.assertEqual(code, 2)
        self.assertIn("error:", err)
        self.assertIn("hint:", err)

    def test_a_file_missing_required_columns_exits_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            path.write_text("a,b,c\n1,2,3\n")
            code, _, err = invoke(
                [
                    "run",
                    "--market-data", str(path),
                    "--output-dir", str(Path(tmp) / "out"),
                    "--valuation-date", "2026-01-15",
                ]
            )
        self.assertEqual(code, 2)
        self.assertIn("column", err.lower())

    def test_an_unparseable_valuation_date_exits_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_frame(clean_frame(), Path(tmp) / "market.csv")
            code, _, err = invoke(
                [
                    "run",
                    "--market-data", str(path),
                    "--output-dir", str(Path(tmp) / "out"),
                    "--valuation-date", "not-a-date",
                ]
            )
        self.assertEqual(code, 2)
        self.assertIn("error:", err)

    def test_an_empty_file_exits_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.csv"
            path.write_text("")
            code, _, err = invoke(
                [
                    "run",
                    "--market-data", str(path),
                    "--output-dir", str(Path(tmp) / "out"),
                    "--valuation-date", "2026-01-15",
                ]
            )
        self.assertEqual(code, 2)
        self.assertIn("error:", err)

    def test_a_too_short_grid_exits_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_frame(clean_frame(), Path(tmp) / "market.csv")
            code, _, err = invoke(
                [
                    "run",
                    "--market-data", str(path),
                    "--output-dir", str(Path(tmp) / "out"),
                    "--valuation-date", "2026-01-15",
                    "--grid-points", "10",
                ]
            )
        self.assertEqual(code, 2)
        self.assertIn("361", err)


class TestEndToEndOnSyntheticData(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.tmp = Path(cls._tmp.name)
        cls.data = write_frame(clean_frame(), cls.tmp / "market.csv")
        cls.out = cls.tmp / "out"
        cls.code, cls.stdout, cls.stderr = invoke(
            [
                "run",
                "--market-data", str(cls.data),
                "--output-dir", str(cls.out),
                "--valuation-date", "2026-01-15",
            ]
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_exits_zero(self) -> None:
        self.assertEqual(self.code, 0, self.stderr)

    def test_writes_every_contract_artefact(self) -> None:
        for relative in CONTRACT_FILES:
            path = self.out / relative
            self.assertTrue(path.exists(), relative)
            self.assertGreater(path.stat().st_size, 0, relative)

    def test_curve_meets_the_row_and_range_contract(self) -> None:
        table = pd.read_csv(self.out / "curves" / "curve.csv")
        self.assertGreaterEqual(len(table), 361)
        self.assertListEqual(
            table.columns.tolist(),
            ["maturity_years", "zero_rate", "discount_factor", "forward_rate"],
        )
        self.assertLessEqual(table["maturity_years"].iloc[0], 1.0 / 12.0 + 1e-12)
        self.assertGreaterEqual(table["maturity_years"].iloc[-1], 30.0 - 1e-12)
        self.assertTrue((table["discount_factor"] > 0).all())

    def test_report_is_self_contained_and_covers_the_required_sections(self) -> None:
        html = (self.out / "reports" / "research_report.html").read_text()
        self.assertIn("<!doctype html", html.lower())
        self.assertNotIn("<script src=", html)
        self.assertNotIn('<link rel="stylesheet" href="http', html)
        self.assertIn("data:image/png;base64,", html)
        # The nine mandated section names, each rendered in English with its
        # Japanese label, and each followed by real body text -- a heading with
        # nothing under it does not satisfy the requirement.
        import re

        mandated = [
            ("Executive Summary", "エグゼクティブサマリー"),
            ("Methodology", "手法"),
            ("Data Quality", "データ品質"),
            ("Model Comparison", "モデル比較"),
            ("Validation and Repricing", "検証と再価格付け"),
            ("Sensitivity Analysis", "感度分析"),
            ("Charts", "図表"),
            ("Limitations", "限界"),
            ("Recommended Next Steps", "推奨される次の手順"),
        ]
        positions = []
        for english, japanese in mandated:
            match = re.search(
                r'<h2 id="[^"]+">\d+\.\s*'
                + re.escape(english)
                + r'\s*<span class="jp">([^<]*'
                + re.escape(japanese)
                + r'[^<]*)</span></h2>',
                html,
            )
            self.assertIsNotNone(match, f"section heading missing: {english}")
            positions.append(match.end())
        self.assertEqual(positions, sorted(positions), "sections are out of order")

        # Each section carries body text, not just a heading.
        bounds = positions + [len(html)]
        for (english, _), start, stop in zip(mandated, bounds, bounds[1:]):
            body = re.sub(r"<[^>]+>", " ", html[start:stop])
            body = re.sub(r"data:image/png;base64,[A-Za-z0-9+/=]+", " ", body)
            self.assertGreater(
                len(body.strip()), 200, f"section has no body text: {english}"
            )

        # The Charts section is a gallery: every figure the workflow produced.
        charts_at = html.index('id="charts"')
        limits_at = html.index('id="limits"')
        self.assertGreaterEqual(
            html[charts_at:limits_at].count("data:image/png;base64,"), 7
        )

    def test_progress_output_names_the_written_files(self) -> None:
        self.assertIn("curve", self.stdout)
        self.assertIn("model selected", self.stdout)

    def test_running_twice_is_byte_identical(self) -> None:
        second = self.tmp / "out_again"
        code, _, err = invoke(
            [
                "run",
                "--market-data", str(self.data),
                "--output-dir", str(second),
                "--valuation-date", "2026-01-15",
            ]
        )
        self.assertEqual(code, 0, err)
        for relative in CONTRACT_FILES:
            self.assertEqual(
                (self.out / relative).read_bytes(),
                (second / relative).read_bytes(),
                f"{relative} is not reproducible",
            )

    def test_the_output_directory_is_created_if_absent(self) -> None:
        self.assertTrue(self.out.is_dir())

    def test_optional_flags_skip_the_matching_artefacts(self) -> None:
        light = self.tmp / "light"
        code, _, err = invoke(
            [
                "run",
                "--market-data", str(self.data),
                "--output-dir", str(light),
                "--valuation-date", "2026-01-15",
                "--no-charts", "--no-sensitivity", "--quiet",
            ]
        )
        self.assertEqual(code, 0, err)
        self.assertTrue((light / "curves" / "curve.csv").exists())
        self.assertFalse((light / "charts").exists())
        payload = json.loads((light / "diagnostics" / "sensitivity.json").read_text())
        self.assertEqual(payload["checks"], [])


@unittest.skipUnless(
    BENCHMARK_DATA.exists(), f"benchmark data set not present at {BENCHMARK_DATA}"
)
class TestEndToEndOnTheBenchmarkData(unittest.TestCase):
    """The mandated invocation, run exactly as specified, in a subprocess.

    Slow (about 45s): it is the only test that exercises the real 143-row file
    through a fresh interpreter with nothing but ``PYTHONPATH=src``.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls._tmp.name) / "out"
        env = dict(os.environ, PYTHONPATH=SRC)
        cls.proc = subprocess.run(
            [
                sys.executable, "-m", "quantcurve.cli", "run",
                "--market-data", str(BENCHMARK_DATA),
                "--output-dir", str(cls.out),
                "--valuation-date", "2026-01-15",
            ],
            capture_output=True, text=True, env=env, cwd=str(Path(SRC).parent),
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_exits_zero(self) -> None:
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr)

    def test_writes_every_contract_artefact(self) -> None:
        for relative in CONTRACT_FILES:
            path = self.out / relative
            self.assertTrue(path.exists(), relative)
            self.assertGreater(path.stat().st_size, 0, relative)

    def test_every_input_observation_is_accounted_for(self) -> None:
        raw = pd.read_csv(BENCHMARK_DATA)
        audit = pd.read_csv(self.out / "diagnostics" / "cleaning.csv")
        self.assertEqual(len(audit), len(raw))
        self.assertEqual(sorted(audit["obs_id"]), sorted(raw["obs_id"]))
        self.assertTrue(
            set(audit["action"]) <= {"keep", "correct", "downweight", "exclude"}
        )

    def test_risk_covers_every_usable_instrument(self) -> None:
        audit = pd.read_csv(self.out / "diagnostics" / "cleaning.csv")
        risk = pd.read_csv(self.out / "diagnostics" / "risk.csv")
        usable = set(audit.loc[audit["action"] != "exclude", "instrument_id"])
        self.assertEqual(set(risk["instrument_id"]), usable)
        self.assertTrue((risk["dv01"] > 0).all())

    def test_the_published_model_passes_the_admissibility_gate(self) -> None:
        payload = json.loads(
            (self.out / "diagnostics" / "model_comparison.json").read_text()
        )
        selected = payload["model_selected"]
        gate = payload[selected]["forward_admissibility"]
        self.assertTrue(gate["admissible"], gate)
        self.assertIn("admissib", payload["selection_rule"].lower())

    def test_sensitivity_reports_at_least_three_checks(self) -> None:
        payload = json.loads(
            (self.out / "diagnostics" / "sensitivity.json").read_text()
        )
        self.assertGreaterEqual(len(payload["checks"]), 3)

    def test_repricing_residuals_are_economically_small(self) -> None:
        repricing = pd.read_csv(self.out / "diagnostics" / "repricing.csv")
        rates = repricing[repricing["instrument_type"] != "bond"]
        self.assertLess(rates["residual"].abs().max(), 0.05)  # 5bp on a percent quote
        bonds = repricing[repricing["instrument_type"] == "bond"]
        self.assertLess(bonds["residual"].abs().max(), 1.0)  # 1 price point


if __name__ == "__main__":
    unittest.main()
