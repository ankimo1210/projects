# Quant Agent Benchmark

Version **1.0.0** is a deterministic, evaluator-separated benchmark for coding agents acting as quantitative researchers and developers. Public inputs live under `input/`; private truth, scenarios, tests, scoring, the reference, and calibration fixtures live under `evaluator/`. Candidate result directories are initially empty.

## Rebuild and validate

```bash
python3.12 tools/generate_benchmark.py --verify-reproducibility
PYTHONPATH=. python3.12 -m unittest discover -s evaluator/hidden_tests -v
PYTHONPATH=evaluator/reference_solution/src python3.12 -m unittest discover -s evaluator/reference_solution/tests -v
```

Static source and documentation are versioned in this directory. The generator deterministically rebuilds every synthetic market dataset, hidden curve, holdout, corruption label file, risk truth file, hidden scenario, and both manifests. It records the fixed seed, scenario seeds, Python/package versions, deterministic source timestamp, and evaluator hashes.

## Isolation preflight

The harness must grant exactly two paths: the common immutable input and one model's empty result directory. It must attest the complete grant to the fail-closed checker, for example:

```bash
python3.12 tools/verify_isolation.py \
  --candidate astra \
  --accessible-path /Users/ankimo1210/Documents/projects/quant-agent-benchmark/input \
  --accessible-path /Users/ankimo1210/Documents/projects/quant-agent-benchmark/results/astra
```

The filesystem sandbox or container enforcing those grants is external to this package; the checker refuses to pass without the explicit complete grant list.

## Evaluate a completed candidate

```bash
python3.12 tools/evaluate_candidate.py /absolute/path/to/candidate --json-out /tmp/evaluation.json
```

Evaluation copies candidate source to a temporary directory, ignores prior outputs and caches, executes the required CLI twice plus all private scenarios, and does not modify the original candidate. Capability is scored out of 100; time, cost, quota, and interventions are reported separately.

## 保存済みの評価結果

このチェックアウトには初回・共通フィードバック後の提出物と評価結果を保存しています。
最終比較は [`evaluations/feedback_round_01_report.html`](evaluations/feedback_round_01_report.html)、
再取得したカーブと監査記録は `analysis/feedback-round-01-final-20260905/` にあります。

`test_result_directories_empty` は実行前の空の提出先を検証する初期状態チェックです。
保存済み提出物を含むこの状態では失敗します。これを通すために提出物を削除したり、
採点器を変更したりしないでください。ローカル仮想環境・キャッシュはGit対象外です。
