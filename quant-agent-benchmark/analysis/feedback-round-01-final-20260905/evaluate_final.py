"""Owner-side final feedback evaluation; preserves all submissions and originals."""
import concurrent.futures
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'analysis/final-review-20260905'))
import recheck_final as prior
from evaluate_compatible import scoring

MODELS = ['astra', 'sol', 'terra', 'luna', 'sonnet', 'opus', 'fable']
PATHS = {m: ROOT / 'feedback_runs/feedback_round_01' / m / 'submission' for m in MODELS}
PATHS['luna'] = ROOT / 'output/luna'


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, default=lambda v: v.item()) + '\n')


def run(model):
    command = [sys.executable, str(ROOT / 'analysis/final-review-20260905/evaluate_compatible.py'),
               str(PATHS[model]), '--json-out', str(OUT / f'{model}_score.json')]
    print(f'START {model}: original scorer + existing risk-column compatibility adapter', flush=True)
    with (OUT / f'{model}_evaluator.log').open('w') as log:
        proc = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=2400)
    if proc.returncode:
        return model, {'scorer_returncode': proc.returncode, 'pytest': None}
    score = json.loads((OUT / f'{model}_score.json').read_text())
    print(f'SCORE {model}: {score["total_score"]:.3f}', flush=True)
    with tempfile.TemporaryDirectory(prefix=f'quant-feedback-tests-{model}-') as temp:
        project = Path(temp) / 'candidate'
        shutil.copytree(PATHS[model], project,
                        ignore=shutil.ignore_patterns('.git', '.venv', '__pycache__', '.pytest_cache', 'outputs'))
        tests = scoring.run_command([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider'], project, timeout=600)
        (OUT / f'{model}_pytest.log').write_text(tests['stdout'] + '\n' + tests['stderr'])
    print(f'TEST {model}: exit={tests["returncode"]}; {tests["stdout"].splitlines()[-1:]}', flush=True)
    return model, {'scorer_returncode': 0, 'pytest': tests}


if __name__ == '__main__':
    assert not (OUT / 'evaluation_audit.json').exists(), 'Do not overwrite a completed audit'
    started = datetime.now(timezone.utc).isoformat()
    manifests = prior.manifest_check()
    before = {m: prior.candidate_hashes(PATHS[m]) for m in MODELS}
    save('candidate_hashes_before.json', before)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = dict(pool.map(run, MODELS))
    after = {m: prior.candidate_hashes(PATHS[m]) for m in MODELS}
    save('candidate_hashes_after.json', after)
    save('evaluation_audit.json', dict(started_utc=started, completed_utc=datetime.now(timezone.utc).isoformat(),
        python=sys.version, packages={k: importlib.metadata.version(k) for k in ['numpy','pandas','scipy','matplotlib','pytest']},
        manifest_before=manifests, manifest_after=prior.manifest_check(),
        submitted_paths={m: str(p) for m,p in PATHS.items()},
        candidates_unchanged=before == after, results=results,
        compatibility='Risk table projected to required fields only; original weights, thresholds, formulas and remaining checks unchanged.',
        timing='Evaluator and verification runtime is NOT candidate development runtime.'))
    assert before == after, 'Submission modified during evaluation'
    assert all(v['scorer_returncode'] == 0 for v in results.values()), 'Scorer failed; inspect per-model logs'
    print('DONE: seven completed evaluations; submission hashes and public/evaluator manifests verified.', flush=True)
