"""Re-run seven skipped Opus tests with the documented public-data environment."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import evaluate_final as final

out = Path(__file__).resolve().parent
target = out / 'opus_e2e_verification.json'
assert not target.exists(), 'Preserve completed supplemental audit'
before = final.prior.candidate_hashes(final.PATHS['opus'])
started = datetime.now(timezone.utc).isoformat()
with tempfile.TemporaryDirectory(prefix='quant-opus-e2e-') as temp:
    project = Path(temp) / 'candidate'
    shutil.copytree(final.PATHS['opus'], project,
                    ignore=shutil.ignore_patterns('.git', '.venv', '__pycache__', '.pytest_cache', 'outputs'))
    env = dict(os.environ, PYTHONPATH=str(project / 'src'), PYTHONDONTWRITEBYTECODE='1',
               QUANTCURVE_MARKET_DATA=str(final.ROOT / 'input/market_data/market_observations.csv'))
    command = [sys.executable, '-m', 'pytest', '-q', '-r', 's', '-p', 'no:cacheprovider',
               'tests/test_cli.py::TestEndToEndOnTheBenchmarkData']
    proc = subprocess.run(command, cwd=project, env=env, text=True, capture_output=True, timeout=600)
after = final.prior.candidate_hashes(final.PATHS['opus'])
result = dict(started_utc=started, completed_utc=datetime.now(timezone.utc).isoformat(),
              returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr,
              source_unchanged=before == after,
              public_data='input/market_data/market_observations.csv',
              explanation='Initial independent run skipped seven real-data tests because a temporary copy had no ancestor input directory. Supplemental run sets the documented QUANTCURVE_MARKET_DATA variable; candidate code is unchanged.')
target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(result, ensure_ascii=False))
assert before == after and proc.returncode == 0
