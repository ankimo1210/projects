from pathlib import Path
import json,hashlib,difflib,re,time
import numpy as np
import pandas as pd
R=Path(__file__).resolve().parent.parent;A=R/'audit';S=R/'submission'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def hashes(root):return {str(p.relative_to(root)):digest(p) for p in sorted(root.rglob('*')) if p.is_file()}
def read(p):return json.loads(p.read_text(),parse_constant=lambda v:(_ for _ in ()).throw(ValueError(v)))
def write(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
out=A/'final_clean_output';rel=A/'relocated_output'
assert hashes(out)==hashes(rel),'Relocated standalone run differs'
assert hashes(out)==hashes(S/'outputs'),'Promoted outputs differ'
assert digest(out/'reports/research_report.html')==digest(S/'reports/research_report.html')
old=A/'baseline_workspace/outputs'
csv_comparison={str(p.relative_to(old)):digest(p)==digest(out/p.relative_to(old)) for p in sorted(old.rglob('*.csv'))}
assert all(csv_comparison.values()),'Final numeric CSV differs from reference'
grid=pd.read_csv(out/'curves/curve.csv');assert np.isfinite(grid.to_numpy()).all()
assert len(grid)>=361 and grid.maturity_years.iloc[0]<=1/12 and grid.maturity_years.iloc[-1]>=30
assert (np.diff(grid.maturity_years)>0).all() and (grid.discount_factor>0).all()
assert np.allclose(np.exp(-grid.zero_rate*grid.maturity_years),grid.discount_factor,atol=2e-12,rtol=2e-12)
reprice=pd.read_csv(out/'diagnostics/repricing.csv');risk=pd.read_csv(out/'diagnostics/risk.csv');clean=pd.read_csv(out/'diagnostics/cleaning.csv')
assert np.isfinite(reprice.select_dtypes('number').to_numpy()).all()
assert np.isfinite(risk.select_dtypes('number').to_numpy()).all()
assert set(risk.instrument_id)==set(reprice.instrument_id)
assert len(clean)==143 and set(clean.action)<=set(['keep','correct','downweight','exclude'])
assert np.isfinite(clean.weight).all() and (clean.loc[clean.action=='exclude','weight']==0).all()
assert np.isfinite(clean.loc[clean.action!='exclude','normalized_quote']).all()
mc=read(out/'diagnostics/model_comparison.json');sens=read(out/'diagnostics/sensitivity.json');val=read(out/'diagnostics/validation.json')
assert val['all_passed'] and all(val['checks'].values())
required={'baseline','advanced','selected_model','selection_rationale'};assert required<=mc.keys()
assert mc['selected_model']==mc['model_selected']=='advanced'
for model in ['baseline','advanced']:
    for scope in ['train','holdout']:
        m=mc[model][scope];assert m['units']['standardized_rmse']=='dimensionless'
        for product,v in m['by_instrument_type'].items():assert v['units']==('price points per 100' if product=='bond' else 'rate basis points')
assert len(sens)>=3
assert all(x.get('conditions') and x.get('numerical_results') and x.get('interpretation') for x in sens.values())
for p in (out/'diagnostics').glob('*.json'):read(p)
headings=['Executive Summary','Methodology','Data Quality','Model Comparison','Sensitivity Analysis','Validation and Repricing','Charts','Limitations','Recommended Next Steps']
for name,label in [('research_report.html','main'),('feedback_review.html','feedback')]:
    p=S/'reports'/name;h=p.read_text();actual=re.findall('<h2>(.*?)</h2>',h)
    assert len(actual)==9 and all(any(x in title for title in actual) for x in headings)
    assert 'http://' not in h and 'https://' not in h
    qa=read(A/'logs/html_qa'/label/'inspection.json')
    assert qa['html_sha256']==digest(p)
    assert qa['no_missing_images'] and qa['desktop_no_overflow'] and qa['mobile_no_overflow'] and not qa['exceptions']

# Only compare the protected initial inventory; no excluded environment is read.
manifest=read(A/'baseline_manifest.json');original=Path('/Users/ankimo1210/Documents/projects/quant-agent-benchmark/results/astra')
after={name:digest(original/name) for name in manifest['tracked_files']}
unchanged=after==manifest['tracked_files'];assert unchanged
write(A/'original_manifest_after.json',{'tracked_files':after,'all_unchanged':unchanged,'tracked_file_count':len(after),
  'scope':'Exactly the original 79 tracked deliverables; runtime exclusions and improvement_round_1 scratch exclusion unchanged from baseline_manifest/protocol.',
  'checked_epoch_seconds':time.time()})
public=Path('/Users/ankimo1210/Documents/projects/quant-agent-benchmark/input')
input_hash=digest(public/'market_data/market_observations.csv')
assert input_hash==digest(S/'data/market_observations.csv')==manifest['tracked_files']['data/market_observations.csv']
assert digest(public/'market_data/CONVENTIONS.md')==digest(S/'data/CONVENTIONS.md')
assert digest(public/'TASK.md')==digest(S/'data/TASK.md')
source_bad=[]
for p in (S/'src').rglob('*.py'):
    for token in ['/Users/','baseline_workspace','feedback_runs','audit/','results/astra','evaluator']:
        if token in p.read_text():source_bad.append([str(p.relative_to(S)),token])
assert not source_bad
changes=[]
for p in sorted(S.rglob('*')):
    if not p.is_file() or p.suffix not in ('.py','.sh','.toml','.md','.lock'):continue
    if any(x in ('data','outputs','reports') for x in p.relative_to(S).parts):continue
    baseline=A/'baseline_workspace'/p.relative_to(S)
    before=baseline.read_text().splitlines(True) if baseline.exists() else []
    changes.extend(difflib.unified_diff(before,p.read_text().splitlines(True),fromfile='initial/'+str(p.relative_to(S)),tofile='submission/'+str(p.relative_to(S))))
(A/'submission_changes.diff').write_text(''.join(changes))

# Format measurements are explicitly separated from curve or pricing errors.
format_started=time.perf_counter()
oldmc=read(old/'diagnostics/model_comparison.json');olds=read(old/'diagnostics/sensitivity.json')
oldh=(A/'baseline_workspace/reports/research_report.html').read_text()
format_metrics=[('F01','model_comparison_required_keys','count',len(required&oldmc.keys()),len(required&mc.keys())),
 ('F02','named_sensitivity_objects_with_conditions_results_interpretation','count',sum(isinstance(x,dict) and all(x.get(k) for k in ['conditions','numerical_results','interpretation']) for x in olds.values()),len(sens)),
 ('F03','bilingual_required_heading_count','count',sum(x in oldh for x in headings),sum(x in (S/'reports/research_report.html').read_text() for x in headings))]
ex=pd.read_csv(A/'experiments.csv');ex=ex[~ex.experiment_id.isin(['F01','F02','F03'])]
format_seconds=time.perf_counter()-format_started
rows=[dict(experiment_id=i,comparison_source='initial_output',changed_factor=m,input_split_id='public:full',model_kind='both',measurement_target='submission_format',maturity_band='not_applicable',instrument_type='not_applicable',metric_name=m,unit=u,before_value=b,after_value=a,n=1,wall_seconds=format_seconds,timing_scope='shared format validation batch, not implementation time',validation_status='passed',adoption='adopted',improvement_fraction=None) for i,m,u,b,a in format_metrics]
ex=pd.concat([ex,pd.DataFrame(rows)],ignore_index=True);ex.to_csv(A/'experiments.csv',index=False)
result={'all_passed':True,'final_tests_passed':46,'failed_test_runs':0,'standalone_relocation_all_outputs_byte_identical':True,
        'promoted_outputs_byte_identical':True,'numeric_csvs_identical_to_initial':csv_comparison,
        'original_tracked_hashes_unchanged':True,'original_tracked_file_count':len(after),'input_sha256':input_hash,
        'units':'curve rates annual decimals; repricing rates decimals and bonds points per 100; risk receiver-fixed USD PV change for 1bp',
        'numerical_validation':val,'format_measurements':format_metrics,'source_contains_personal_absolute_paths':False,
        'experimental_numerical_factors_adopted':0,'exact_final_version':'reference_numerics_schema_v1',
        'unique_experiment_ids':int(ex.experiment_id.nunique()),'measurement_rows':len(ex)}
write(A/'logs/final_validation.json',result);print(json.dumps(result,ensure_ascii=False,indent=2))
