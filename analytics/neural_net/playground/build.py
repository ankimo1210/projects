"""Build an offline, single-file dashboard from the editable sources."""

import argparse
import json
import math
import statistics
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOKENS = HERE.parents[2] / "docs/templates/claude-report/tokens.css"
SNAPSHOT = HERE / "benchmark-results.json"


def load_snapshot(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    try:
        if data["status"] != "complete" or data["schema_version"] != 1:
            raise ValueError("Only a completed comparison may be embedded")
        hardware, config, dataset = data["hardware"], data["config"], data["data"]
        datetime.fromisoformat(data["created_at"])
        for text in [
            hardware["cpu"],
            hardware["torch"],
            dataset["split_sha256"],
            data["source_sha256"],
        ]:
            if not isinstance(text, str) or not text:
                raise ValueError("Missing display metadata")
        if (
            config["dtype"] != "float32"
            or hardware["float32_matmul_precision"] != "highest"
            or hardware["cpu_threads"] != config["cpu_threads"]
            or hardware["cpu_threads"] < 1
            or config["device"] not in {"cpu", "cuda"}
            or config["epochs"] < 1
            or config["batch_size"] < 1
            or not math.isfinite(config["lr"])
            or config["lr"] <= 0
            or not math.isfinite(config["weight_decay"])
            or config["weight_decay"] < 0
        ):
            raise ValueError("Unsupported precision or invalid experiment settings")
        if config["device"] == "cuda" and (not hardware["gpu"] or not hardware["gpu_total_bytes"]):
            raise ValueError("Missing GPU metadata")
        if (
            len(dataset["classes"]) != 10
            or len(dataset["previews"]) != 10
            or not math.isfinite(dataset["mean"])
            or not math.isfinite(dataset["std"])
            or dataset["std"] <= 0
        ):
            raise ValueError("Expected normalized, ten-class Fashion-MNIST data")
        for i, preview in enumerate(dataset["previews"]):
            if (
                preview["label"] != i
                or len(preview["pixels"]) != 784
                or any(type(p) is not int or not 0 <= p <= 255 for p in preview["pixels"])
            ):
                raise ValueError("Invalid preview image")
        for name in ["train", "validation", "test"]:
            if type(dataset[name]) is not int or dataset[name] <= 0:
                raise ValueError("Invalid population size")
        if len(dataset["input_sha256"]) != 4:
            raise ValueError("Missing source hashes")
        model_ids = [m["id"] for m in data["models"]]
        seeds = data["config"]["seeds"]
        if len(set(model_ids)) != len(model_ids) or len(set(seeds)) != len(seeds):
            raise ValueError("Duplicated model or seed")
        for model in data["models"]:
            if not model["label"] or any(type(n) is not int or n < 1 for n in model["hidden"]):
                raise ValueError("Invalid model architecture")
            sizes = [784, *model["hidden"], 10]
            parameters = sum((sizes[i] + 1) * sizes[i + 1] for i in range(len(sizes) - 1))
            if parameters != model["parameters"]:
                raise ValueError("Parameter count disagrees with architecture")
            devices = [t["device"] for t in model["timings"]]
            if len(devices) != len(set(devices)):
                raise ValueError("Duplicated device timing")
            for timing in model["timings"]:
                if (
                    timing["device"] not in {"cpu", "cuda"}
                    or timing["batch_size"] != config["batch_size"]
                    or not math.isfinite(timing["step_ms"])
                    or timing["step_ms"] <= 0
                    or not math.isclose(
                        timing["samples_per_second"],
                        1000 * config["batch_size"] / timing["step_ms"],
                        rel_tol=1e-9,
                    )
                ):
                    raise ValueError("Invalid step time or throughput")
        expected = {(model_id, seed) for model_id in model_ids for seed in seeds}
        actual = [(r["model_id"], r["seed"]) for r in data["runs"]]
        if not expected or len(actual) != len(expected) or set(actual) != expected:
            raise ValueError("Missing or duplicated model/seed runs")

        def check_metrics(metrics, population):
            matrix = metrics["confusion"]
            n = data["data"][population]
            if (
                len(matrix) != 10
                or any(len(row) != 10 for row in matrix)
                or any(type(count) is not int or count < 0 for row in matrix for count in row)
            ):
                raise ValueError("Invalid confusion matrix")
            correct = sum(row[i] for i, row in enumerate(matrix))
            if (
                sum(map(sum, matrix)) != n
                or metrics["n"] != n
                or correct != metrics["correct"]
                or metrics["accuracy"] != correct / n
                or not math.isfinite(metrics["loss"])
                or metrics["loss"] < 0
            ):
                raise ValueError("Metric counts or loss do not reconcile")

        epochs = data["config"]["epochs"]
        for run in data["runs"]:
            model = next(m for m in data["models"] if m["id"] == run["model_id"])
            if run["parameters"] != model["parameters"]:
                raise ValueError("Run has a different parameter count")
            memory, reserved = run["peak_allocated_bytes"], run["peak_reserved_bytes"]
            if memory is not None and (
                type(memory) is not int
                or memory <= 0
                or memory > hardware["gpu_total_bytes"]
                or reserved < memory
            ):
                raise ValueError("Invalid GPU memory measurement")
            if [row["epoch"] for row in run["history"]] != list(range(epochs + 1)):
                raise ValueError("Incomplete learning history")
            for row in run["history"]:
                check_metrics(row["train"], "train")
                check_metrics(row["validation"], "validation")
            times = [row["elapsed_seconds"] for row in run["history"]]
            if any(not math.isfinite(t) or t < 0 for t in times) or times != sorted(times):
                raise ValueError("Invalid history timing")
            check_metrics(run["test"], "test")
            best = min(run["history"][1:], key=lambda row: row["validation"]["loss"])
            if (
                run["best_epoch"] != best["epoch"]
                or not math.isfinite(run["fit_seconds"])
                or run["fit_seconds"] <= 0
            ):
                raise ValueError("Invalid checkpoint or timing")
            if run["best_validation"] != best["validation"] or run["fit_seconds"] != times[-1]:
                raise ValueError("Checkpoint or final time does not reconcile")
        if {r["model_id"] for r in data["summary"]} != set(model_ids):
            raise ValueError("Incomplete summary")
        for summary in data["summary"]:
            runs = [r for r in data["runs"] if r["model_id"] == summary["model_id"]]
            values = [r["test"]["accuracy"] for r in runs]
            memory = [
                r["peak_allocated_bytes"] for r in runs if r["peak_allocated_bytes"] is not None
            ]
            if summary["peak_allocated_bytes"] != (max(memory) if memory else None):
                raise ValueError("Memory summary disagrees with individual runs")
            expected_summary = {
                "test_accuracy_mean": statistics.mean(values),
                "test_accuracy_std": statistics.stdev(values) if len(values) > 1 else 0,
                "fit_seconds_mean": statistics.mean(r["fit_seconds"] for r in runs),
            }
            if summary["seeds"] != len(runs) or any(
                not math.isclose(summary[k], v, abs_tol=1e-12) for k, v in expected_summary.items()
            ):
                raise ValueError("Summary disagrees with individual runs")
    except (KeyError, TypeError, IndexError, ZeroDivisionError) as error:
        raise ValueError("Invalid comparison schema") from error
    return data


def render() -> str:
    html = (HERE / "page.html").read_text(encoding="utf-8")
    snapshot = load_snapshot(SNAPSHOT) if SNAPSHOT.exists() else None
    html = html.replace(
        "/*__SCALE_DATA__*/",
        json.dumps(snapshot, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c"),
    )
    for marker, path in {
        "TOKENS": TOKENS,
        "STYLES": HERE / "styles.css",
        "ENGINE": HERE / "engine.js",
        "APP": HERE / "app.js",
        "COMPARISON": HERE / "comparison.html",
        "COMPARISON_STYLE": HERE / "comparison.css",
        "COMPARISON_APP": HERE / "comparison.js",
        "INSPECTOR_STYLE": HERE / "inspector.css",
        "INSPECTOR_APP": HERE / "inspector.js",
    }.items():
        html = html.replace(f"/*__{marker}__*/", path.read_text(encoding="utf-8"))
    return html


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Check the committed HTML without writing"
    )
    parser.add_argument(
        "--import-comparison", type=Path, help="Validate and retain a completed result snapshot"
    )
    args = parser.parse_args()
    if args.import_comparison:
        if args.check:
            parser.error("--check cannot import a result")
        load_snapshot(args.import_comparison)
        SNAPSHOT.write_text(args.import_comparison.read_text(encoding="utf-8"), encoding="utf-8")
    output = HERE / "index.html"
    expected = render()
    if args.check:
        if not output.exists() or output.read_text(encoding="utf-8") != expected:
            raise SystemExit("Dashboard is stale; run build.py")
        print("Dashboard is up to date and self-contained")
    else:
        output.write_text(expected, encoding="utf-8")
        print(f"Built {output} ({len(expected.encode('utf-8')):,} bytes)")


if __name__ == "__main__":
    main()
