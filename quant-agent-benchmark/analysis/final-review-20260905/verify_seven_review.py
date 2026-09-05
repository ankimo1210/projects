"""Read-only candidate review and shipped/rerun metric reconciliation."""
import json
import sys
from pathlib import Path
import pandas as pd

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=HERE/'expanded-7-models'
sys.path.insert(0,str(HERE))
import evaluate_compatible as adapter
from recheck_final import recovery

review={}
for model,relative in [('terra','/Users/ankimo1210/Documents/terra'),('luna','output/luna'),('sonnet','output/sonnet')]:
    project=ROOT/relative
    scoring=adapter.scoring
    recomputed=scoring.curve_metrics(pd.read_csv(project/'outputs/curves/curve.csv'),
        pd.read_csv(scoring.GROUND_ROOT/'main_curve.csv'),pd.read_csv(scoring.GROUND_ROOT/'holdout_instruments.csv'))
    scored=json.loads((OUT/f'{model}_score.json').read_text())['quantitative_diagnostics']
    # All displayed diagnostics are rounded to 3 decimals. Set an explicit
    # acceptance threshold below half a displayed unit (0.0005), not bitwise
    # identity across numerical execution environments.
    differences={k:abs(v-scored[k]) for k,v in recomputed.items()}
    assert all(v<0.0001 for v in differences.values()),(model,differences)
    files=['README.md','benchmark_summary.json','outputs/diagnostics/model_comparison.json',
           'outputs/diagnostics/sensitivity.json','outputs/curves/curve.csv']
    files += ['src/quantcurve/calibration.py','src/quantcurve/curve.py'] if model=='sonnet' else []
    comparison=json.loads((project/files[2]).read_text())
    sensitivity=json.loads((project/files[3]).read_text())
    summary=json.loads((project/files[1]).read_text())
    review[model]=dict(candidate_path=relative,source_sha256={f:recovery.digest(project/f) for f in files},
        model_comparison_keys=list(comparison),model_selection={k:v for k,v in comparison.items() if k in ['selected_model','model_selected','selection_rationale','holdout_method','advanced_smoothing_selection']},
        sensitivity_top_level_keys=list(sensitivity),summary_keys=list(summary),
        shipped_vs_isolated_metrics={k:dict(shipped=v,isolated=scored[k],absolute_difference=differences[k]) for k,v in recomputed.items()},
        diagnostic_tolerance=0.0001,diagnostic_tolerance_reason='Smaller than half a unit at the displayed 3-decimal precision.',
        max_difference=max(differences.values()),unchanged_display_precision=True)
review['scoring_metric_definition']={
    'source':'evaluator/scoring.py',
    'sha256':recovery.digest(ROOT/'evaluator/scoring.py'),
    'bid_ask_normalized_pricing_rmse':'model_quote minus hidden holdout true_quote, divided by max(half_spread, rate 0.002 or bond 0.02); not public quote fit',
    'static_scan_limitation':'Four old model names hardcoded; new-name paths are not covered by the original other-results scan.',
    'sonnet_forward':'Baseline exports analytical z(t)+t*z_prime(t); scorer compares exported values with np.gradient(-log(df),grid).',
    'sonnet_holdout':'Deposits entirely in training; OIS candidate maturities screened for local smoothness. Selection-bias hypothesis, no ablation.'}
(OUT/'candidate_review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print({m:review[m]['max_difference'] for m in ['terra','luna','sonnet']})
