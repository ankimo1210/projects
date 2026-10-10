
"""Independent pure probes of pending saved-check observer; native/worker never read."""
from pathlib import Path
from time import perf_counter,process_time
from unittest.mock import patch
import ast,copy,hashlib,importlib.util,json,sys,tempfile
D=Path('/home/kazumasa/worktrees/johnhull-storage-codec/.superpowers/sdd/2026-10-10-dynamic-storage-codec');P='task-5-full-pilot-root-saved-check-';OP='independent-saved-check-observer-v1'
start=perf_counter();cpu=process_time();checks=[];forbidden_hits=[]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def check(n,value):
 checks.append({'name':n,'PASS':bool(value)})
 if not value:raise AssertionError(n)
def reject(n,fn,text=None):
 try:fn()
 except (ValueError,AssertionError,KeyError) as e:
  if text is not None:check(n,text in str(e))
  else:check(n,True)
  return
 check(n,False)
def forbidden(*a,**k):
 forbidden_hits.append('reached');raise AssertionError('native/worker/financial boundary prohibited')
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
fixed={'observer-v1.py':'9277b8097cf499129f93a8e8d44e41063c0f0279a5865a9b0f5cc68249b4efb4','enclosing-v1.py':'2116df010e19aa3bbfcacbbd8ba3872eb7927e05f6525c9b0d9abf036976a503','resource-candidate-v1.json':'a5face84365a5ee437d55e680da1414075b7ef761894e842f2377aff73a5723e','fixed-manifest-v1.json':'7070e54eaca88106360f535eaed278fc472599fd29c5f5831d55e41866d591f5'}
for n,h in fixed.items():check('fixed:'+n,sha(D/(P+n))==h)
manifest=read(D/(P+'fixed-manifest-v1.json'))
for name,row in manifest['files'].items():
 path=Path(name) if Path(name).is_absolute() else D/name
 check('manifest:'+path.name,sha(path)==row['sha256'] and path.stat().st_size==row['bytes'])
m=load('independent_saved_observer',D/(P+'observer-v1.py'));outer=load('independent_saved_outer',D/(P+'enclosing-v1.py'))
c=read(D/(P+'resource-candidate-v1.json'))
check('false_candidate_no_approval',c['root_preapproved'] is False and c['execute_saved_check'] is False and c['finance_acceptance'] is False and c['new_saved_check_budget_approved'] is False and c['formal_phase_completion_claimed'] is False)
check('pending_terminal_and_capacity_unknown',c['original_terminal_monitor_receipt']['sha256'] is None and c['original_terminal_enclosing_receipt']['sha256'] is None and c['closed_native']['files'] is None and c['closed_native']['latest_checkpoint'] is None and c['whole_hydrated_job_result_RSS_fit'] is None and c['full_capacity_or_duration_guarantee'] is False)
with patch.object(m.subprocess,'Popen',forbidden),patch.object(m,'source_binding',forbidden),patch.object(m,'closed_native_binding',forbidden):
 reject('pending_guard_early_refusal',lambda:m.load_guard(D/(P+'resource-candidate-v1.json')),'root saved-check prior')
 reject('outer_pending_refusal',lambda:outer.main(['--guard',str(D/(P+'resource-candidate-v1.json')),'--guard-sha256',fixed['resource-candidate-v1.json']]))
 # Approval booleans only changed in an in-memory JSON parsing fixture, not an approval file.
 approved=copy.deepcopy(c);approved.update(root_preapproved=True,execute_saved_check=True,saved_check_authorized_by='root')
 original_loads=m.json.loads
 original_exists=Path.exists
 def exists_with_live(pid):
  def check_exists(p):
   if str(p).startswith('/proc/'):return str(p)==f'/proc/{pid}'
   return original_exists(p)
  return check_exists
 for pid in m.ORIGINAL_PIDS:
  with patch.object(m.json,'loads',lambda *a,**k:copy.deepcopy(approved)),patch.object(Path,'exists',exists_with_live(pid)):
   reject('each_original_PID_live:'+str(pid),lambda:m.load_guard(D/(P+'resource-candidate-v1.json')),'must all be terminal')
 with patch.object(m.json,'loads',lambda *a,**k:copy.deepcopy(approved)),patch.object(Path,'exists',exists_with_live(-1)):
  reject('both_terminal_refs_pending_before_heavy',lambda:m.load_guard(D/(P+'resource-candidate-v1.json')),'pending reference SHA')
check('early_native_and_Popen_zero',forbidden_hits==[])
# Synthetic terminal row dictionaries are confined to helper-level pure call mocks.
original=read(D/m.ORIGINAL_GUARD_NAME)
monitor={'status':'completed_or_partial_terminal','child_exit_code':0,'child_pid':m.ORIGINAL_PIDS[2],'prior_sha256':m.ORIGINAL_GUARD_SHA,'native_output_path':str(m.ORIGINAL_NATIVE)}
enclosing={'schema':'rb-f04-root-formal-monitor-enclosing-cost-v1','status':'terminal_requires_native_and_saved_result_inspection','monitor_exit_code':0,'monitor_pid':m.ORIGINAL_PIDS[1],'guard_sha256':m.ORIGINAL_GUARD_SHA}
def terminal_probe(change=None,change_prior=None):
 mon=copy.deepcopy(monitor);encl=copy.deepcopy(enclosing);pr=copy.deepcopy(c)
 if change:change(mon,encl)
 if change_prior:change_prior(pr)
 def fixed_mock(spec,*a,**kw):
  if spec['path'].endswith(m.ORIGINAL_GUARD_NAME):return copy.deepcopy(original)
  if spec['path']==pr['original_terminal_monitor_receipt']['path']:return mon
  if spec['path']==pr['original_terminal_enclosing_receipt']['path']:return encl
  raise AssertionError('unexpected helper read')
 with patch.object(Path,'exists',lambda p:False),patch.object(m,'fixed_reference',fixed_mock):
  return m.terminal_authority(pr)
check('closed_two_terminal_helpers_allow_fixture',terminal_probe()['historical_cost_or_failure_reclassified'] is False)
for label,change in [
 ('monitor_unknown_exit',lambda a,b:a.update(child_exit_code=None)),
 ('monitor_bool_exit',lambda a,b:a.update(child_exit_code=False)),
 ('monitor_wrong_actual_child',lambda a,b:a.update(child_pid=3)),
 ('monitor_wrong_guard',lambda a,b:a.update(prior_sha256='0'*64)),
 ('outer_unknown_exit',lambda a,b:b.update(monitor_exit_code=None)),
 ('outer_nonterminal',lambda a,b:b.update(status='running')),
 ('outer_wrong_actual_monitor',lambda a,b:b.update(monitor_pid=2)),
 ('outer_wrong_guard',lambda a,b:b.update(guard_sha256='0'*64))]:
 reject('terminal:'+label,lambda change=change:terminal_probe(change))
reject('original_source_substitution',lambda:terminal_probe(change_prior=lambda p:p.update(source_identity_sha256='0'*64)))
# Tiny synthetic byte catalog; never list or hash actual live native.
with tempfile.TemporaryDirectory(prefix='independent-saved-observer-fixture-',dir=D) as temp:
 native=Path(temp)/'native';native.mkdir()
 for name in ('checkpoint0000','checkpoint0001'):
  q=native/name;q.mkdir();(q/'metadata.json').write_text('{}\n');(q/'receipt.json').write_text('{}\n')
 def fixture_prior(latest='checkpoint0001'):
  files={str(p.relative_to(native)):sha(p) for p in native.rglob('*') if p.is_file()}
  cp=native/latest;cpf={str(p.relative_to(cp)):sha(p) for p in cp.rglob('*') if p.is_file()}
  return {'closed_native':{'path':str(native),'files':files,'tree_sha256':m.digest(files),'latest_checkpoint':{'path':str(cp),'files':cpf,'tree_sha256':m.digest(cpf),'receipt_sha256':cpf['receipt.json']}}}
 with patch.object(m,'ORIGINAL_NATIVE',native):
  small=fixture_prior()
  check('synthetic_closed_finite_catalog',m.closed_native_binding(small)['physical_files']==4)
  reject('older_checkpoint_even_consistent_catalog',lambda:m.closed_native_binding(fixture_prior('checkpoint0000')),'not the original final')
  bad=copy.deepcopy(small);bad['closed_native']['files']=None
  reject('missing_catalog_before_hash',lambda:m.closed_native_binding(bad),'finite file set')
  bad=copy.deepcopy(small);bad['closed_native']['tree_sha256']='0'*64
  reject('wrong_catalog_digest',lambda:m.closed_native_binding(bad),'changed or incomplete')
  bad=copy.deepcopy(small);bad['closed_native']['latest_checkpoint']['receipt_sha256']='0'*64
  reject('checkpoint_receipt_tamper',lambda:m.closed_native_binding(bad),'root artifact receipt')
  bad=copy.deepcopy(small);bad['closed_native']['files']['../outside']='0'*64
  reject('unsafe_catalog_path',lambda:m.closed_native_binding(bad),'unsafe or pending')
  (native/'extra').write_text('x')
  reject('extra_closed_file',lambda:m.closed_native_binding(small),'changed or incomplete')
  (native/'extra').unlink();(native/'link').symlink_to(native/'checkpoint0000/metadata.json')
  reject('symbolic_native_catalog',lambda:m.closed_native_binding(fixture_prior()),'symbolic links')
# Source/admin mechanics only; no run or child call.
vol=[{'id':k,'path':'/','reserve_bytes':10*m.GiB,'free_bytes':11*m.GiB} for k in ('WSL','C','F')]
check('admin_original_limits',c['phase_wall_limit_seconds']==2592000 and c['parent_rss_limit_bytes']==c['child_rss_limit_bytes']==16*m.GiB and c['poll_seconds']==1 and [x['path'] for x in c['volume_probes']]==['/','/mnt/c','/mnt/f'] and all(x['reserve_bytes']==10*m.GiB for x in c['volume_probes']))
check('wall_stop',m.choose_stop(2592000,0,0,vol,c)['metric']=='outer_phase_wall')
check('individual_child_stop',m.choose_stop(0,16*m.GiB+1,0,vol,c)['metric']=='individual_child_rss')
check('individual_parent_stop',m.choose_stop(0,0,16*m.GiB+1,vol,c)['metric']=='individual_parent_rss')
low=copy.deepcopy(vol);low[0]['free_bytes']=10*m.GiB
check('volume_reserve_stop',m.choose_stop(0,0,0,low,c)['metric']=='volume_reserve')
check('RSS_unknown_not_zero_claim',m.choose_stop(0,None,None,vol,c) is None)
check('source_fault_unclosed',m.terminal_status(0,None,False,[],False)=='unclosed_source_or_input_binding_changed')
check('worker_error_not_resource_cap',m.terminal_status(1,None,False,[],True)=='unclosed_child_exit')
check('unknown_child_terminal_unclosed',m.terminal_status(None,None,False,[],True)=='unclosed_child_terminal_unknown')
check('real_signal_stop_partial',m.terminal_status(-9,{'metric':'individual_child_rss'},True,[],True)=='administrative_partial_unclosed')
check('raced_stop_no_financial_cap',m.terminal_status(0,{'metric':'volume_reserve'},False,[],True)=='administrative_limit_observed_terminal_unclosed')
src=(D/(P+'observer-v1.py')).read_text();tree=ast.parse(src);f={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
call=next(n for n in ast.walk(f['child']) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='check_pilot')
context=next(k.value for k in call.keywords if k.arg=='context')
check('actual_full_API_context',isinstance(context,ast.Dict) and [k.value for k in context.keys]==['inputs','parameters'] and ast.unparse(context.values[1])=="inputs['parameters']")
check('full_result_written_without_subset',any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='write_pilot_artifact' and ast.unparse(n.args[1])=='result' for n in ast.walk(f['child'])))
check('heavy_imports_after_loadguard',f['child'].body[1].value.func.id=='load_guard' and isinstance(f['child'].body[2],ast.ImportFrom))
check('expense_clock_all_outer_preflight',ast.unparse(f['run'].body[0])=='started = clock()')
check('full_return_unknown_capacity',c['whole_hydrated_job_result_RSS_fit'] is None and c['cap_values_are_runtime_predictions'] is False and c['required_external_expenses_are_automatically_closed'] is False)
for n,h in fixed.items():check('fixed_after:'+n,sha(D/(P+n))==h)
check('no_financial_modules_imported',not any(n in sys.modules for n in ('numpy','run_pilot','check_pilot','run_reference')))
check('no_worker_or_heavy_native_spy_calls',forbidden_hits==[])
result={'schema':'rb-f04-independent-saved-check-observer-pure-results-v1','status':'PASS','checks':checks,'check_count':len(checks),'fixed':fixed,'source_mechanics_scope_only':True,'root_candidate_preapproved':False,'actual_saved_check_worker_launches':0,'actual_live_native_tree_reads_or_large_decode':0,'finance_RNG_SDE_solver_CAS_Git_production_edits':0,'synthetic_fixture_scope':'four tiny JSON files; no nativeNPZ/finance arrays','financial_qualification':'unknown','fullcapacity_finance_actuallaunch_main_phase_approved':False,'cost':{'direct_wall_seconds_before_result_write':perf_counter()-start,'direct_CPU_seconds_before_result_write':process_time()-cpu,'full_review_and_tail_seconds':None}}
(D/(OP+'-results-v1.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':'PASS','checks':len(checks),'cost':result['cost'],'worker_calls':0,'live_native_reads':0}))
