from pathlib import Path
import ast,copy,hashlib,importlib.util,json,os,subprocess,tempfile,time,traceback,types
from unittest.mock import patch
D=Path('/home/kazumasa/worktrees/johnhull-storage-codec/.superpowers/sdd/2026-10-10-dynamic-storage-codec')
W=D.parents[2]
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
helper=load('ind_terminal_helper_v2',D/'task-5-native-terminal-byte-candidate-v2.py')
pre=load('ind_terminal_fixture_old',D/'task-5-native-terminal-byte-candidate-preflight-v1.py')
checks=[];started=time.perf_counter();cpu=time.process_time()
def check(n,ok,d=None): checks.append({'name':n,'PASS':bool(ok),'detail':d})
fixed={'task-5-native-terminal-byte-candidate-v2.py':'179d4475e3dadaa591aa6c401f613188a590268d9fd34d786b830b660c2a6dde','task-5-native-terminal-byte-candidate-preflight-v2.py':'684665bb5a6aa8eec754bd06e8daf5160a86da2b14d009e4215d4928c0be9849','task-5-native-terminal-byte-candidate-fixed-manifest-v2.json':'eebd369f171253fd56f2a57f1c06d8c9cbe14c08f2f88e6a047db25d4dc0a0f5'}
try:
 for n,s in fixed.items():check('fixed:'+n,pre.sha(D/n)==s)
 manifest=json.loads((D/'task-5-native-terminal-byte-candidate-fixed-manifest-v2.json').read_text())
 for n,s in manifest['files'].items():check('manifest:'+n,(D/n).stat().st_size==s['bytes'] and pre.sha(D/n)==s['sha256'])
 for n,s in manifest['original_contract_refs'].items():check('legacy:'+n,pre.sha(D/n)==s)
 check('immutable_v1_helper',pre.sha(D/'task-5-native-terminal-byte-candidate-v1.py')==manifest['immutable_v1_sha256'])
 v1checks=json.loads((D/'independent-terminal-byte-helper-v1-results.json').read_text())
 check('v1_failure_records_unchanged',pre.sha(D/'independent-terminal-byte-helper-v1-results.json')=='6b0111f4daaeba2e82252083f2df9698962ba991ac06659666fa6747915705f1' and pre.sha(D/'independent-terminal-byte-helper-v1-decision.json')=='63974bff8e72ff93bf18836fc0f87dbcc49f6fba54bf237c5063e85710105101' and v1checks['status']=='FAIL' and len(v1checks['checks'])==37)
 old=ast.parse((D/'task-5-native-terminal-byte-candidate-v1.py').read_text());new=ast.parse((D/'task-5-native-terminal-byte-candidate-v2.py').read_text())
 funcs={}
 for label,tree in [('old',old),('new',new)]:
  funcs[label]={n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,ast.FunctionDef)}
 changed=[n for n in funcs['old'] if funcs['old'][n]!=funcs['new'][n]]
 for t in (old,new):t.body=[n for n in t.body if not (isinstance(n,ast.FunctionDef) and n.name in ['_publish_new','_native_inventory'])]
 check('only_two_function_AST_changes',changed==['_native_inventory','_publish_new'] and ast.dump(old,include_attributes=False)==ast.dump(new,include_attributes=False),changed)
 closure=json.loads((D/'current-production-source-closure-v1.json').read_text())
 check('source82_exactbytes',len(closure['files'])==82 and not closure['dynamic_imports'] and all(pre.sha(W/k)==v for k,v in closure['files'].items()))
 # Boundary 1: normal complete false candidate, old 4 tiny files.
 with tempfile.TemporaryDirectory(prefix='ind-terminal-v2-normal-',dir=D) as td:
  o,p,c,seen=pre.fixture(Path(td));out=Path(td)/'normal-false.json';before=copy.deepcopy(p)
  with patch.object(subprocess,'Popen',side_effect=AssertionError('worker prohibited')):
   result=helper.freeze_candidate(o,p,out,capacity_reader=lambda p:{'fixture_only':True,'whole_RSS_fit':None})
  flags=['root_preapproved','execute_saved_check','finance_acceptance','new_saved_check_budget_approved','formal_financial_launch_authorized','financial_A_cap_projection_approved','formal_phase_completion_claimed']
  check('normal_false_publication',all(result[k] is False for k in flags) and result['financial_qualification']=='unknown' and json.loads(out.read_text())==result and len(result['closed_native']['files'])==4 and p==before)
  allowed={'original_terminal_monitor_receipt','original_terminal_enclosing_receipt','closed_native','root_fresh_capacity_snapshot','terminal_provenance_preparation'}
  check('original_scope_limits_external_unknown_preserved',all(result[k]==before[k] for k in before if k not in allowed))
  check('original_source_authority_rechecked',seen==['fixture_source_authority','fixture_source_authority'])
 # Boundary 2: v1 collision counterexample; original user bytes now survive.
 with tempfile.TemporaryDirectory(prefix='ind-terminal-v2-collision-',dir=D) as td:
  root=Path(td);o,p,c,seen=pre.fixture(root);out=root/'candidate.json'
  tmp=out.with_name(out.name+'.candidate-occupied.tmp');raw=b'user-owned collision bytes';tmp.write_bytes(raw);exc=None
  with patch.object(helper.uuid,'uuid4',return_value=types.SimpleNamespace(hex='occupied')):
   try:helper._publish_new(o,out,'candidate\n')
   except o.GuardRejectedError as e:exc=str(e)
  check('existing_temp_collision_preserves_original_bytes',exc is not None and tmp.exists() and tmp.read_bytes()==raw and not out.exists(),{'exception':exc})
 # Boundary 3: stable .tmp remains collectable with original observer.
 with tempfile.TemporaryDirectory(prefix='ind-terminal-v2-stable-tmp-',dir=D) as td:
  o,p,c,seen=pre.fixture(Path(td));tmp=c/'solver-state.tmp';tmp.write_bytes(b'partial saved evidence remains unknown\n')
  result=helper.freeze_candidate(o,p,Path(td)/'partial-false.json',capacity_reader=lambda p:{'fixture_only':True})
  o.closed_native_binding(result)
  check('terminal_partial_tmp_original_all5bytes',len(result['closed_native']['files'])==5 and result['closed_native']['files']['checkpoint000001/solver-state.tmp']==pre.sha(tmp) and result['financial_qualification']=='unknown' and result['terminal_provenance_preparation']['terminal_authority']['native_child_exit_code']==1 and not result['financial_A_cap_projection_approved'])
 # Boundary 4: created temporary name is replaced with other owner before link fails.
 with tempfile.TemporaryDirectory(prefix='ind-terminal-v2-replaced-',dir=D) as td:
  root=Path(td);o,p,c,seen=pre.fixture(root);out=root/'candidate.json';tmp=out.with_name(out.name+'.candidate-replaced.tmp');saved=root/'original-created-temp.bin'
  other=b'replacement owned by another actor';exc=None
  def replace_then_fail(src,dst):
   Path(src).rename(saved);Path(src).write_bytes(other);raise OSError('simulated publication I/O failure after path replacement')
  with patch.object(helper.uuid,'uuid4',return_value=types.SimpleNamespace(hex='replaced')),patch.object(helper.os,'link',side_effect=replace_then_fail):
   try:helper._publish_new(o,out,'our candidate\n')
   except OSError as e:exc={'type':type(e).__name__,'reason':str(e)}
  check('created_then_replaced_temp_preserved_IO_error_propagates',exc is not None and tmp.read_bytes()==other and saved.read_text()=='our candidate\n' and not out.exists(),exc)
 for n,s in fixed.items():check('fixed_after:'+n,pre.sha(D/n)==s)
 result={'schema':'rb-f04-independent-terminal-byte-helper-pure-results-v2','status':'PASS' if all(c['PASS'] for c in checks) else 'FAIL','checks':checks,'check_count':len(checks),'runtime_boundary_cases':4,'historical_v1_37_checks_not_reexecuted':True,'author21_probes_not_recounted_as_independent':True,'genuine_native_hash_or_decode_finance_worker_RNG_SDE_solver_CAS_Git_production_edits':0,'actual_root_permission_and_savedlaunch':False,'financial_qualification':'unknown','wall_before_result_write':time.perf_counter()-started,'CPU_before_result_write':time.process_time()-cpu,'review_outer_and_tail_cost':'unknown'}
except Exception:
 result={'status':'probe_tool_exception','checks':checks,'trace':traceback.format_exc(),'genuine_native_hash_or_decode_finance_worker':0}
(D/'independent-terminal-byte-helper-v2-results.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'status':result['status'],'checks':len(checks),'failed':[c['name'] for c in checks if not c['PASS']]},ensure_ascii=False))
