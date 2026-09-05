from pathlib import Path
import json,hashlib,time,datetime
import pandas as pd
R=Path(__file__).resolve().parent.parent;A=R/'audit';S=R/'submission'
def read(p):return json.loads(p.read_text())
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
round_info=read(A/'round_summary.json');valid=read(A/'logs/final_validation.json');assert valid['all_passed']
tests=read(A/'logs/final_tests.json');assert tests['returncode']==0 and '46 passed' in tests['stdout']
assert round_info['test_runs']==2 and round_info['failed_test_runs']==0
experiments=pd.read_csv(A/'experiments.csv')
assert experiments.wall_seconds.notna().all()
assert not experiments.validation_status.isna().any()
for name in ['protocol.md','experiments.csv','feedback_response.md','baseline_manifest.json','original_manifest_after.json']:
    assert (A/name).stat().st_size>0
before=read(A/'baseline_manifest.json')['tracked_files']
original=Path('/Users/ankimo1210/Documents/projects/quant-agent-benchmark/results/astra')
assert all(sha(original/p)==h for p,h in before.items())
source_digest=hashlib.sha256()
for p in sorted((S/'src').rglob('*.py')):source_digest.update(str(p.relative_to(S)).encode()+b'\0'+p.read_bytes())
source_hash=source_digest.hexdigest()
visual={'all_cli_charts_visually_inspected':True,'cli_charts':['curve.png','forward_rate.png','repricing.png','model_comparison.png','sensitivity.png'],
 'all_research_charts_visually_inspected':True,'research_charts':['factor_comparison.png','synthetic_diagnostics.png','public_diagnostics.png'],
 'html_rendered_and_visually_inspected':True,'reports':['research_report.html','feedback_review.html'],
 'screenshots_inspected':{'main':['top.png','section-4.png','section-5.png','section-8.png','mobile-top.png'],
                          'feedback':['top.png','section-4.png','section-6.png','mobile-top.png']},
 'all_nine_sections_captured':True,'network_transport_used':False,
 'findings':['Axes retain declared units and all visible residuals, including extreme observations.',
             'Original and candidate curves miss the independently generated long-end hump.',
             'Reduced smoothing adds public mid-tenor forward undulations; these cannot be labeled truth or error without a known curve.',
             'Endpoint regression under long-end illiquidity is displayed together with its numeric RMSE.',
             'Both reports render nine bilingual roles and embedded figures with no page overflow on desktop or mobile.']}
write(A/'logs/visual_review.json',visual)
limits=[
 '採用可能な数値改善なし。初回の数値CSVを維持し、長期形状の精度上の弱点も残る。',
 '端数クーポンとOIS頻度の実際の生成規約は不明。独立式との一致は仮定した規約内の実装検証に限る。',
 '公開単位修正は分割前の全テープを参照する。4つの満期分割は時間外検証ではない。',
 '人工20条件は自作の研究集合で、採用判断後の独立確認集合ではない。隠し精度・スコアの推定は行っていない。',
 'ノット、平滑化、端点、ロバスト重みの相互作用は未検証。複数数値変更は最終版へ合成していない。',
 '人工全条件でCLIの内部CVまで含めて比較する手続きは未検証。固定lambdaによる一要因比較と区別する。',
 '異なるOS・BLAS・フォント・ライブラリでのバイト再現性と別日の精度は未確認。パッケージ導入は行わず承認済み環境でソース実行した。',
 '実行バックエンドのモデルID・reasoning effortは独立取得不可。Astra/xhighは指定された記録ラベル。',
 '正確なトークン、料金、クレジット、割当消費量は取得不可でnull。'
]
end=time.time();assert end-round_info['start_epoch_seconds']<round_info['time_limit_seconds']
finish=datetime.datetime.fromtimestamp(end,datetime.timezone.utc).isoformat().replace('+00:00','Z')
elapsed=end-round_info['start_epoch_seconds']
round_info.update(status='FINALIZED',finish_time_utc=finish,end_time_utc=finish,end_epoch_seconds=end,
 additional_work_seconds=elapsed,wall_time_seconds=elapsed,within_time_limit=True,
 final_adopted_version='reference_numerics_schema_v1',final_source_sha256=source_hash,
 selected_model='advanced',selected_smoothing=.001,numerical_factors_adopted=[],
 adopted_changes=['Direct D(t) pricing API with finite-positive-discount validation',
                 'Required comparison/sensitivity schema and explicit metric units',
                 'Nine bilingual report headings and undefined improvement ratio handling',
                 'Independent source-run documentation and round-specific evidence'],
 experiment_count=int(experiments.experiment_id.nunique()),
 experiment_count_definition='275 model × input/split evaluations (11 variants × 25 cases), 5 convention checks, 3 format checks; not a performance target',
 numerical_candidate_count=9,simple_baseline_count=1,reference_count=1,
 synthetic_conditions=20,public_holdout_splits=4,independent_pricing_comparisons=1965,
 test_results={'baseline_copy':{'passed':45,'failed':0},'final_submission':{'passed':46,'failed':0}},
 tests_passed=46,tests_failed=0,
 corrective_iterations=2,corrective_iteration_definition='Two validated submission change sets: direct discount pricing interface; schema/report/ratio edge case. Documentation and contract tests belong to those sets.',
 diagnostic_repair_iterations=1,
 diagnostic_failures=[{'log':'logs/diagnose.json','reason':'setuptools metadata absent in the authorized runtime','resolution':'Record only required installed package versions; no installation or numeric change.'}],
 nonfatal_warnings=['Pandas concat FutureWarning in format-audit recording; results and validations passed; raw stderr retained.'],
 original_hashes_unchanged=True,original_tracked_files=79,input_original_unchanged=True,
 original_manifest_after='original_manifest_after.json',environment=read(A/'environment.json'),
 seed=20260905,cli_seed=20260115,
 standalone_execution_verified=True,standalone_all_output_bytes_identical=True,
 final_numeric_csvs_identical_to_initial=True,all_charts_visually_inspected=True,html_rendered_and_inspected=True,
 unverified_items=limits,token_telemetry_available=False,cost_telemetry_available=False,quota_telemetry_available=False,
 actual_backend_model_id=None,actual_backend_reasoning_effort=None,human_interventions=1,
 human_intervention_definition='The complete instruction was supplied during preparation; original timer retained.',
 estimated_usd_cost=None)
write(A/'round_summary.json',round_info)
benchmark={
 'schema_version':'1.0','round_name':'feedback_round_01','model_name':'Astra','reasoning_effort':'xhigh',
 'model_setting_confirmation':'User requested label; backend setting not independently exposed; no model switching',
 'start_time':round_info['start_time_utc'],'finish_time':finish,'start_time_utc':round_info['start_time_utc'],
 'finish_time_utc':finish,'wall_time_seconds':elapsed,'additional_work_seconds':elapsed,'time_limit_seconds':3600,
 'test_runs':2,'failed_test_runs':0,'corrective_iterations':2,'tests_passed':46,'tests_failed':0,
 'human_interventions':1,'files_created':[], 'unresolved_limitations':limits,
 'quota_percentage_consumed':None,'credits_consumed':None,'estimated_usd_cost':None,
 'input_tokens':None,'cached_input_tokens':None,'output_tokens':None,'reasoning_tokens':None,'total_tokens':None,'reported_usd_cost':None,
 'status':'FINALIZED','final_adopted_version':'reference_numerics_schema_v1',
 'selected_model':'advanced','selected_smoothing':.001,'numerical_improvement_adopted':False,
 'final_numeric_csvs_identical_to_initial':True,
 'synthetic_fixed_lambda_reference':{'conditions':20,'long_zero_rmse_bp_mean':5.835620203119285,'long_forward_rmse_bp_mean':41.646886658451464,'meaning':'Known self-authored curves; not hidden scores; same method retained.'},
 'rejected_smoothing_lower':{'long_zero_rmse_bp_mean':3.915592777792836,'improvement_fraction':.3290185718906358,
                            'public_S2_short_ois_rmse_before_bp':2.027445206034055,'public_S2_short_ois_rmse_after_bp':9.107055069290043},
 'final_clean_end_to_end_passed':True,'independent_relocated_execution_passed':True,
 'all_charts_visually_inspected':True,'html_rendered_and_inspected':True,
 'original_hashes_unchanged':True,'original_tracked_file_count':79,'input_original_sha256':valid['input_sha256'],
 'environment':read(A/'environment.json'),'research_seed':20260905,'cli_seed':20260115,
 'final_source_sha256':source_hash,
 'audit_location':'../audit (research records only; not a runtime dependency)',
 'final_validation_log':'../audit/logs/final_validation.json','test_logs':['../audit/logs/baseline_tests.json','../audit/logs/final_tests.json'],
 'failed_auxiliary_command_logs':['../audit/logs/diagnose.json']}
write(S/'benchmark_summary.json',benchmark)
benchmark['files_created']=sorted({str(p.relative_to(S)) for p in S.rglob('*') if p.is_file()}|{'deliverable_manifest.json'})
write(S/'benchmark_summary.json',benchmark)
inventory={str(p.relative_to(S)):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and p.name!='deliverable_manifest.json'}
write(S/'deliverable_manifest.json',{'round_name':'feedback_round_01','sha256':inventory,'self_excluded':True})
required=['schema_version','model_name','reasoning_effort','start_time','finish_time','wall_time_seconds','test_runs','failed_test_runs','corrective_iterations','tests_passed','tests_failed','files_created','unresolved_limitations','quota_percentage_consumed','credits_consumed','estimated_usd_cost','human_interventions']
final=read(S/'benchmark_summary.json');assert all(k in final for k in required)
assert all((S/p).is_file() for p in final['files_created'])
assert all(sha(S/p)==h for p,h in inventory.items())
write(A/'logs/final_submission_schema.json',{'passed':True,'required_summary_fields_present':True,'inventory_files':len(inventory),
       'summary_is_new_round':True,'all_file_hashes_match':True,'elapsed_seconds':elapsed,'within_3600_seconds':elapsed<3600})
print(json.dumps({'status':'FINALIZED','submission':str(S),'finish_time_utc':finish,'additional_work_seconds':elapsed,
 'tests_passed':46,'failed_test_runs':0,'original_tracked_files_unchanged':79,
 'numerical_improvement_adopted':False,'final_source_sha256':source_hash},ensure_ascii=False,indent=2))
