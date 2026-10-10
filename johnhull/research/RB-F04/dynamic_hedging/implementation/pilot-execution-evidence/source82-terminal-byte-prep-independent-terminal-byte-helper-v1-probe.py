from pathlib import Path
import ast,copy,hashlib,importlib.util,json,os,subprocess,tempfile,time,traceback,types
from unittest.mock import patch
D=Path('/home/kazumasa/worktrees/johnhull-storage-codec/.superpowers/sdd/2026-10-10-dynamic-storage-codec')
W=D.parents[2]
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path)
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
helper=load('ind_terminal_helper',D/'task-5-native-terminal-byte-candidate-v1.py')
pre=load('ind_terminal_fixture',D/'task-5-native-terminal-byte-candidate-preflight-v1.py')
checks=[];defects=[];started=time.perf_counter();cpu=time.process_time()
def check(name,ok,detail=None):
 checks.append({'name':name,'PASS':bool(ok),'detail':detail})
 if not ok: defects.append(name)
fixed={
 'task-5-native-terminal-byte-candidate-v1.py':'5e213f68be278ee087f08171966b24c3bcc0cb3526ab83b89b639f92491c667c',
 'task-5-native-terminal-byte-candidate-preflight-v1.py':'94cc8770608e10756dc3b29012fc02050519200f605d8cb7a96e82d267b937ad',
 'task-5-native-terminal-byte-candidate-fixed-manifest-v1.json':'898908fe5c3dcd74b7853241e3cd6155f874a8fa599eea0005820eb4d3e43b6d'}
for name,sha in fixed.items(): check('fixed:'+name,pre.sha(D/name)==sha)
manifest=json.loads((D/'task-5-native-terminal-byte-candidate-fixed-manifest-v1.json').read_text())
for name,spec in manifest['files'].items():
 check('manifest:'+name,(D/name).stat().st_size==spec['bytes'] and pre.sha(D/name)==spec['sha256'])
for name,sha in manifest['immutable_existing_contract_refs'].items():check('legacy:'+name,pre.sha(D/name)==sha)
closure=json.loads((D/'current-production-source-closure-v1.json').read_text())
check('source82_bytes',len(closure['files'])==82 and not closure['dynamic_imports'] and all(pre.sha(W/k)==v for k,v in closure['files'].items()))
def run_case(name, mutate=None, expect=None):
 with tempfile.TemporaryDirectory(prefix='ind-terminal-helper-',dir=D) as td:
  root=Path(td);observer,prior,checkpoint,seen=pre.fixture(root);output=root/'new-false.json'
  if mutate: mutate(observer,prior,checkpoint,output)
  before=copy.deepcopy(prior);count=[];original=helper._native_inventory
  def inv(o):count.append(1);return original(o)
  with patch.object(helper,'_native_inventory',inv),patch.object(subprocess,'Popen',side_effect=AssertionError('worker prohibited')):
   try: result=helper.freeze_candidate(observer,prior,output,capacity_reader=lambda p:{'fixture_only':True,'whole_RSS_fit':None})
   except Exception as exc:
    if expect:
     check(name,expect in str(exc) and not output.exists(),{'exception':type(exc).__name__,'reason':str(exc),'inventory_calls':len(count)})
    else:raise
   else:
    check(name,expect is None and result['root_preapproved'] is False and result['execute_saved_check'] is False and result['finance_acceptance'] is False and result['expense_scope']==prior['expense_scope'] and result['original_counts']==prior['original_counts'])
    observer.closed_native_binding(result)
  check(name+':template_unchanged',prior==before)
  return count
try:
 run_case('normal_nonzero_unknown_false_candidate')
 def approval(o,p,c,out):p['execute_saved_check']=True
 count=run_case('approval_rejected',approval,'candidate cannot supply approval')
 check('approval_before_inventory',not count)
 def monitor_bool(o,p,c,out):
  path=Path(p['original_terminal_monitor_receipt']['path']);v=json.loads(path.read_text());v['child_exit_code']=False;pre.dump(path,v)
 count=run_case('bool_child_exit_rejected',monitor_bool,'terminal child');check('bool_before_inventory',not count)
 def outer_bool(o,p,c,out):
  path=Path(p['original_terminal_enclosing_receipt']['path']);v=json.loads(path.read_text());v['monitor_exit_code']=False;pre.dump(path,v)
 run_case('bool_monitor_exit_rejected',outer_bool,'nonterminal')
 def roster(o,p,c,out):p['original_counts']['jobs']=3137
 run_case('original_job_count_tamper_rejected',roster,'authority differs')
 def ns(o,p,c,out):p['original_teacher_N_candidates']=[1024]
 run_case('original_N_tamper_rejected',ns,'authority differs')
 # P2 counterexample: deterministic UUID temporary-name collision.
 with tempfile.TemporaryDirectory(prefix='ind-terminal-publish-',dir=D) as td:
  root=Path(td);o,p,c,seen=pre.fixture(root);out=root/'candidate.json'
  tmp=out.with_name(out.name+'.candidate-occupied.tmp');raw=b'user-owned collision bytes';tmp.write_bytes(raw)
  error=None
  with patch.object(helper.uuid,'uuid4',return_value=types.SimpleNamespace(hex='occupied')):
   try:helper._publish_new(o,out,'false candidate\n')
   except Exception as exc:error={'type':type(exc).__name__,'reason':str(exc),'trace':traceback.format_exc()}
  retained=tmp.exists() and tmp.read_bytes()==raw
  check('existing_temp_collision_preserves_original_bytes',retained,{'observed_existing_temp_survives':tmp.exists(),'output_published':out.exists(),'exception':error})
 # Contract counterexample: existing observer accepts all saved .tmp bytes after terminal.
 with tempfile.TemporaryDirectory(prefix='ind-terminal-saved-tmp-',dir=D) as td:
  root=Path(td);o,p,c,seen=pre.fixture(root);(c/'solver-state.tmp').write_bytes(b'partial saved evidence remains unknown\n')
  files={str(f.relative_to(o.ORIGINAL_NATIVE)):pre.sha(f) for f in o.ORIGINAL_NATIVE.rglob('*') if f.is_file()}
  cf={str(f.relative_to(c)):pre.sha(f) for f in c.rglob('*') if f.is_file()}
  p['closed_native']={'path':str(o.ORIGINAL_NATIVE),'files':files,'tree_sha256':o.digest(files),'latest_checkpoint':{'path':str(c),'files':cf,'tree_sha256':o.digest(cf),'receipt_sha256':cf['receipt.json']}}
  o.closed_native_binding(p);prior_observer_accepts=True
  error=None
  try:helper.freeze_candidate(o,p,root/'partial-false.json',capacity_reader=lambda p:{'fixture_only':True})
  except Exception as exc:error={'type':type(exc).__name__,'reason':str(exc),'trace':traceback.format_exc()}
  check('terminal_partial_tmp_evidence_remains_collectable',error is None,{'existing_observer_accepts_all5files':prior_observer_accepts,'helper_exception':error,'financial_qualification':p['financial_qualification']})
 for name,sha in fixed.items():check('fixed_after:'+name,pre.sha(D/name)==sha)
except Exception:
 result={'status':'probe_tool_exception','trace':traceback.format_exc(),'checks':checks}
else:
 result={'schema':'rb-f04-independent-terminal-byte-helper-pure-results-v1','status':'FAIL' if defects else 'PASS','checks':checks,'check_count':len(checks),'defects':defects,
 'fixture_native_files':4,'counterexample_partial_files':5,'genuine_native_inventory_or_decode':0,'finance_RNG_SDE_solver_worker_CAS_Git_production':0,
 'wall_before_result_write':time.perf_counter()-started,'CPU_before_result_write':time.process_time()-cpu,'total_review_outer_and_tail_cost':'unknown','financial_qualification':'unknown','actual_root_permission_and_savedlaunch':False}
(D/'independent-terminal-byte-helper-v1-results.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'status':result['status'],'checks':len(checks),'defects':defects},ensure_ascii=False))
