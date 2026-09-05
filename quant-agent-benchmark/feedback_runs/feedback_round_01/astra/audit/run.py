"""Logged local commands using only the explicitly authorized runtime."""
from pathlib import Path
import argparse, json, os, subprocess, time
p=argparse.ArgumentParser();p.add_argument('label');p.add_argument('--cwd',required=True);p.add_argument('--test',action='store_true');p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
audit=Path(__file__).resolve().parent;env=os.environ.copy();env.update(PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(audit/'tmp'),MPLCONFIGDIR=str(audit/'tmp/matplotlib'),XDG_CACHE_HOME=str(audit/'tmp/cache'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONHASHSEED='0',PYTHONPATH=str(Path(a.cwd)/'src'))
cmd=a.command[1:] if a.command and a.command[0]=='--' else a.command
start=time.time();result=subprocess.run(cmd,cwd=a.cwd,env=env,text=True,capture_output=True)
record={'command':cmd,'cwd':a.cwd,'start_epoch_seconds':start,'end_epoch_seconds':time.time(),'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr};record['wall_seconds']=record['end_epoch_seconds']-start
(audit/'logs'/f'{a.label}.json').write_text(json.dumps(record,indent=2)+'\n');print(result.stdout,end='');print(result.stderr,end='')
if a.test:
 s=json.loads((audit/'round_summary.json').read_text());s['test_runs']+=1;s['failed_test_runs']+=int(result.returncode!=0);(audit/'round_summary.json').write_text(json.dumps(s,indent=2)+'\n')
raise SystemExit(result.returncode)
