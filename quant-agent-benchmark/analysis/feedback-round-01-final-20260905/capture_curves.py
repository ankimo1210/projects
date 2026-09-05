"""Retain owner-side curve shapes from unchanged final submissions and scorer CLI.

No candidate receives private truth: truth is read only after its CLI returns.
Captured curves must reproduce all previously frozen final RMSEs.
"""
import concurrent.futures
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
import tempfile

import numpy as np
import pandas as pd
import evaluate_final as final

OUT = Path(__file__).resolve().parent / 'curve_shapes'
SC = final.scoring


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def capture(model):
    target = OUT / model
    target.mkdir(exist_ok=True)
    frozen = json.loads((final.OUT / f'{model}_score.json').read_text())['quantitative_diagnostics']
    cases = [('main', SC.VISIBLE_MARKET, SC.GROUND_ROOT / 'main_curve.csv', SC.GROUND_ROOT / 'all_instruments_truth.csv')]
    cases += [(p.name, p / 'market_data.csv', p / 'truth_curve.csv', p / 'instrument_truth.csv') for p in sorted(SC.SCENARIO_ROOT.glob('s*'))]
    rows = []
    with tempfile.TemporaryDirectory(prefix=f'quant-curve-shapes-{model}-') as temp:
        project = Path(temp) / 'candidate'
        shutil.copytree(final.PATHS[model], project, ignore=shutil.ignore_patterns('.git', '.venv', '__pycache__', '.pytest_cache', 'outputs'))
        for sid, market, truth_path, instrument_path in cases:
            receipt_path = target / f'{sid}_audit.json'
            if receipt_path.exists():
                rows.append(json.loads(receipt_path.read_text()))
                print(f'REUSE {model} {sid}', flush=True)
                continue
            print(f'RUN {model} {sid}', flush=True)
            output = Path(temp) / sid
            run = SC.run_cli(project, market, output, 240 if sid == 'main' else 180)
            assert run['returncode'] == 0, (model, sid, run)
            raw, error = SC.safe_read_csv(output / 'curves/curve.csv', SC.CURVE_COLUMNS)
            assert raw is not None, (model, sid, error)
            curve = SC.normalize_curve(raw)
            assert len(curve) >= 361 and curve['maturity_years'].is_unique
            assert np.isfinite(curve[list(SC.CURVE_COLUMNS)]).all().all()
            assert (curve['discount_factor'] > 0).all()
            truth = pd.read_csv(truth_path)
            instruments = pd.read_csv(instrument_path)
            metrics = SC.curve_metrics(curve, truth, instruments)
            expected = frozen if sid == 'main' else frozen['hidden_scenarios'][sid]
            for key in ['zero_rate_rmse_bps', 'forward_rate_rmse_bps', 'short_end_zero_rmse_bps', 'long_end_zero_rmse_bps']:
                assert np.isclose(metrics[key], expected[key], rtol=1e-9, atol=1e-9), (model, sid, key, metrics[key], expected[key])
            # Curves, not bulky candidate HTML/diagnostics, are retained.
            curve.to_csv(target / f'{sid}_curve.csv', index=False, float_format='%.17g')
            result = dict(model=model, case=sid, curve_rows=len(curve), truth_rows=len(truth), market_rows=len(pd.read_csv(market)),
                          market=str(market.relative_to(final.ROOT)), truth=str(truth_path.relative_to(final.ROOT)),
                          metrics=metrics, rmse_matches_frozen_score=True, cli_seconds=run['wall_time_seconds'])
            save(receipt_path, result)
            rows.append(result)
            print(f'OK {model} {sid}: zero={metrics["zero_rate_rmse_bps"]:.6f} bp', flush=True)
    return rows


if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    assert not (OUT / 'capture_audit.json').exists(), 'Completed capture is immutable'
    started = datetime.now(timezone.utc).isoformat()
    frozen_hashes = json.loads((final.OUT / 'candidate_hashes_after.json').read_text())
    before = {m: final.prior.candidate_hashes(final.PATHS[m]) for m in final.MODELS}
    assert before == frozen_hashes, 'Submissions changed since frozen final scores'
    manifest_before = final.prior.manifest_check()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = [r for group in pool.map(capture, final.MODELS) for r in group]
    after = {m: final.prior.candidate_hashes(final.PATHS[m]) for m in final.MODELS}
    assert before == after
    save(OUT / 'capture_audit.json', dict(started_utc=started, completed_utc=datetime.now(timezone.utc).isoformat(),
         candidates_unchanged=True, candidates_match_frozen=True, manifest_before=manifest_before,
         manifest_after=final.prior.manifest_check(), runs=results,
         definition='Each market is independently calibrated with the same frozen submitted algorithm. Private truths only enter owner-side metrics and charts, never fitting inputs. This capture runtime is excluded from agent development time and token/API cost.'))
    print('DONE: 77 valid curves reproduce frozen final errors; all sources unchanged.', flush=True)
