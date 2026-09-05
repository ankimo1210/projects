"""Build the final seven-model feedback report from immutable owner audits."""
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
import sys
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NEW = 'analysis/feedback-round-01-final-20260905'
OLD = 'analysis/final-review-20260905/expanded-7-models'
MODELS = ['astra','sol','terra','luna','sonnet','opus','fable']
CATS = [('numerical_correctness','数値精度',30),('quantitative_model_quality','モデル品質',20),
        ('hidden_scenario_robustness','頑健性',15),('software_engineering_reproducibility','ソフトウェア',15),
        ('data_quality_handling','データ品質',10),('report_completeness','レポート',5),('completion_integrity','完遂',5)]
INPUTS, CHECKS, DATA, BLOCKS, CHARTS, TABLES, CARDS, SOURCES, CHART_MAP = {}, [], {}, [], [], [], [], [], []


def read(rel):
    p=ROOT/rel
    INPUTS[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
    return json.loads(p.read_text())


def check(ok,label):
    if not ok: raise AssertionError(label)
    CHECKS.append(label)


def save(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def md(id,body,source=None):
    b=dict(id=id,type='markdown',body=body.strip(),layout='full')
    if source:b['sourceId']=source
    BLOCKS.append(b)


def table(id,title,subtitle,rows,cols,source='scores',sort=('model','asc')):
    DATA[id]=rows
    TABLES.append(dict(id=id,title=title,subtitle=subtitle,dataset=id,sourceId=source,layout='full',density='spacious',
        defaultSort=dict(field=sort[0],direction=sort[1]),
        columns=[dict(field=f,label=label,type=typ) for f,label,typ in cols]))
    BLOCKS.append(dict(id=id+'-block',type='table',tableId=id,layout='full'))


def chart(id,title,subtitle,rows,x,ys,unit,source='scores',kind='bar'):
    DATA[id]=rows
    c=dict(id=id,title=title,subtitle=subtitle,type=kind,dataset=id,sourceId=source,layout='full',
        encodings={'x':dict(field=x,type='nominal',label='モデル' if x=='model' else 'シナリオ'),
                   'y':dict(fields=ys,type='quantitative',label=unit)},
        unit=unit,valueFormat='number',labels={'values':'all'},showDescription=True,
        palette={'kind':'sequential' if kind=='heatmap' else 'categorical','name':'blue'},
        settings={'sort':'none','showValues':True},
        surface={'surface':'card','showControls':False,'interactiveLegend':False})
    if kind!='heatmap':
        c['settings']['orientation']='horizontal'
        c['settings']['groupMode']='grouped'
        c['legend']={'position':'bottom','sort':'spec'}
    if kind=='horizontalStackedBar':c['settings']['groupMode']='stacked'
    CHARTS.append(c)
    BLOCKS.append(dict(id=id+'-block',type='chart',chartId=id,layout='full'))
    CHART_MAP.append(dict(id=id,question=title,family='matrix' if kind=='heatmap' else ('composition' if 'Stacked' in kind else 'comparison'),
        rows=len(rows),grain='model' if x=='model' else 'scenario',fields=[x]+ys,source=source,
        palette='Sequential blue for magnitude; packaged categorical palette distinguishes the two phases or four exclusive token components.',
        distinction='Axis labels, series legend and exact table values; never color alone.',
        footprint='Full report width; mobile stack; canonical portable reader.',
        limitation='Discrete before/after comparison, not a time trend; no interpolation between phases.'))


def source(id,label,path,files,sql,definitions,description):
    SOURCES.append(dict(id=id,label=label,path=path,query=dict(engine='SQLite in-memory',language='sql',sql=sql,
        description=description,executed_at=STAMP,tables_used=files,
        filters=['Seven named models; one original run and one feedback round per model; 2026-09-05.',
                 'Original scores frozen; feedback scores freshly executed with identical evaluator and compatibility adapter.'],
        metric_definitions=definitions)))


def num(x,n=3):return f'{x:,.{n}f}'
def pair(a,b,n=3):return f'{num(a,n)} → {num(b,n)}'


def main():
    global STAMP
    STAMP=datetime.now(timezone.utc).isoformat()
    audit=read(f'{NEW}/evaluation_audit.json')
    supplemental=read(f'{NEW}/opus_e2e_verification.json')
    check(supplemental['returncode']==0 and supplemental['source_unchanged'],'Opus skipped E2E tests independently verified with documented public-data path')
    check(bool(re.search(r'7 passed',supplemental['stdout'])),'Seven supplemental Opus tests passed')
    prior=read(f'{OLD}/evaluation_audit.json')
    usage=read(f'{NEW}/usage_cost_snapshot.json')
    original_tests=read(f'{OLD}/pytest_verification.json')
    initial={m:read(f'{OLD}/{m}_score.json') for m in MODELS}
    final={m:read(f'{NEW}/{m}_score.json') for m in MODELS}
    u={x['model']:x for x in usage['summaries']}
    check(audit['candidates_unchanged'],'Submitted files unchanged during owner evaluation')
    for phase in ['manifest_before','manifest_after']:
        for part,n in [('input',12),('evaluator',108)]:
            check(audit[phase][part]['files_verified']==n and not audit[phase][part]['mismatches'],phase+part)
    for key,path in [('scoring_sha256','evaluator/scoring.py'),('wrapper_sha256','tools/evaluate_candidate.py'),
                     ('adapter_sha256','analysis/final-review-20260905/evaluate_compatible.py')]:
        check(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==prior[key],'Same evaluator component: '+path)
    for m in MODELS:
        check(u[m]['feedback_all']['status']=='complete',m+': completed feedback usage')
        check(audit['results'][m]['scorer_returncode']==0,m+': scorer success')
        for phase,score in [('initial',initial[m]),('feedback',final[m])]:
            check(abs(sum(score['category_scores'].values())-score['total_score'])<.002,m+phase+': category sum')
            check(len(score['hidden_tests']['details'])==41,m+phase+': 41 scoring checks')
            check(len(score['quantitative_diagnostics']['hidden_scenarios'])==10,m+phase+': 10 scenarios')
        for phase in ['initial','feedback_prep','feedback_main','feedback_all']:
            v=u[m][phase]
            check(v['total_tokens']==v['input_total']+v['output_total'],m+phase+': exclusive token identity')
            rates=usage['rates_usd_per_million'][u[m]['model_ids'][0]]
            cost=sum(v[k]*r for k,r in zip(['uncached_input','cache_read_input','cache_write_5m','cache_write_1h','output_total'],rates))/1e6
            check(v['long_context_requests']==0 and math.isclose(cost,v['usd_standard'],abs_tol=1e-8),m+phase+': independent price')

    db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
    db.execute('CREATE TABLE evaluations(model TEXT, phase TEXT, document TEXT)')
    db.executemany('INSERT INTO evaluations VALUES(?,?,?)',[(m,p,json.dumps(d[m])) for p,d in [('initial',initial),('feedback',final)] for m in MODELS])
    db.execute('CREATE TABLE usage(model TEXT, phase TEXT, document TEXT)')
    db.executemany('INSERT INTO usage VALUES(?,?,?)',[(m,p,json.dumps(u[m][p])) for m in MODELS for p in ['initial','feedback_prep','feedback_main','feedback_all']])
    score_sql="""SELECT model, phase, json_extract(document,'$.total_score') AS score,
 json_extract(document,'$.category_scores') AS categories,
 json_extract(document,'$.quantitative_diagnostics') AS metrics,
 json_array_length(json_extract(document,'$.hidden_tests.passed')) AS checks_passed,
 json_extract(document,'$.failed_test_identifiers') AS failed_checks
FROM main.evaluations ORDER BY model, phase;"""
    usage_sql="""SELECT model, phase, json_extract(document,'$.work_minutes') AS minutes,
 json_extract(document,'$.total_tokens') AS tokens,
 json_extract(document,'$.uncached_input') AS uncached_input,
 json_extract(document,'$.cache_read_input') AS cache_read_input,
 json_extract(document,'$.cache_write_5m') AS cache_write_5m,
 json_extract(document,'$.cache_write_1h') AS cache_write_1h,
 json_extract(document,'$.output_total') AS output_tokens,
 json_extract(document,'$.usd_standard') AS usd_standard,
 json_extract(document,'$.usd_fast_scenario') AS usd_fast_scenario
FROM main.usage ORDER BY model, phase;"""
    score_rows=[dict(r) for r in db.execute(score_sql)]
    usage_rows=[dict(r) for r in db.execute(usage_sql)]
    check(len(score_rows)==14 and len(usage_rows)==28,'SQL grain: 14 evaluations, 28 usage phases')
    save(HERE/'query_results.json',{'evaluations':score_rows,'usage':usage_rows})
    (HERE/'report_queries.sql').write_text(score_sql+'\n\n'+usage_sql+'\n')
    scorefiles=[f'{p}/{m}_score.json' for p in [OLD,NEW] for m in MODELS]+['evaluator/scoring.py',f'{NEW}/evaluate_final.py','main.evaluations']
    source('scores','初回と改善後の共通採点',f'{NEW}/evaluation_audit.json',scorefiles,score_sql,
        ['Total = seven original categories, maximum 100. Time and cost excluded.',
         'Zero/forward RMSE in bp, 1 bp = 0.01 percentage point. Lower is better.',
         'Short <=2Y, long >=15Y. Forward metric differentiates estimated z(T)*T on the evaluator grid.',
         'Hidden instrument normalized RMSE pools yield errors in bp and bond price errors in 0.1-price units; NOT pure bp.',
         'Scenario summaries are unweighted means over the same ten scenarios, not pooled observations.'],
        'Fresh execution on temporary copies. Original Python 3.12 and package versions; only existing risk-column compatibility adapter. No manual score correction.')
    source('usage','初回・改善ラウンドの実測時間と料金換算',f'{NEW}/usage_cost_snapshot.json',
        [f'{NEW}/usage_cost_snapshot.json','analysis/feedback-round-01-usage-20260905/recover_usage_cost.py',
         'https://developers.openai.com/api/docs/pricing','https://platform.claude.com/docs/en/about-claude/pricing','main.usage'],usage_sql,
        list(usage['definitions'].values()),'Response-ID deduplication, per-response counters reconciled; Claude 1h cache-write TTL. USD Standard API equivalent; actual subscription invoice and Codex service tier unavailable.')
    SOURCES.append(dict(id='qa',label='独立再実行・原本保全の監査',path=f'{NEW}/evaluation_audit.json',query=dict(
        description='Owner-side full pytest on temporary copies; source hashes and public/evaluator manifests before and after.',
        tables_used=[f'{NEW}/evaluation_audit.json',f'{OLD}/evaluation_audit.json',f'{NEW}/candidate_hashes_before.json',f'{NEW}/candidate_hashes_after.json',f'{NEW}/opus_e2e_verification.json'])))
    profilepaths=[('output/luna/audit/round_summary.json' if m=='luna' else f'feedback_runs/feedback_round_01/{m}/audit/round_summary.json') for m in MODELS]
    profiles={m:read(p) for m,p in zip(MODELS,profilepaths)}
    SOURCES.append(dict(id='methods',label='共通指示・候補の実験記録',path='prompts/feedback_improvement_round_01.md',query=dict(
        description='Methods and artificial-experiment figures are candidate-reported diagnostics, not common hidden scores or independent causal estimates.',
        tables_used=['prompts/feedback_improvement_round_01.md']+profilepaths+
        [f'feedback_runs/feedback_round_01/{m}/audit/feedback_response.md' for m in MODELS if m not in ['luna','sonnet']]+['output/luna/audit/feedback_response.md'])))
    SOURCES.append(dict(id='synthesis',label='複数証拠の照合：採点・使用量・独立監査・候補実験',path=f'{NEW}/combined_summary.json',query=dict(
        description='Joined model-level summaries computed by evaluations/feedback-round-01-report/build_report.py from frozen initial scores, fresh feedback scores, deduplicated usage and independent pytest. Candidate self-reported methods remain separate from owner-verified metrics.',
        tables_used=scorefiles+[f'{NEW}/usage_cost_snapshot.json',f'{NEW}/evaluation_audit.json',f'{NEW}/opus_e2e_verification.json','prompts/feedback_improvement_round_01.md']+profilepaths)))

    ranked=sorted(MODELS,key=lambda m:final[m]['total_score'],reverse=True)
    main_improved=[m for m in MODELS if final[m]['quantitative_diagnostics']['zero_rate_rmse_bps'] < initial[m]['quantitative_diagnostics']['zero_rate_rmse_bps']-1e-8]
    main_unchanged=[m for m in MODELS if abs(final[m]['quantitative_diagnostics']['zero_rate_rmse_bps']-initial[m]['quantitative_diagnostics']['zero_rate_rmse_bps'])<1e-8]
    extra_cost=sum(u[m]['feedback_all']['usd_standard'] for m in MODELS)
    extra_tokens=sum(u[m]['feedback_all']['total_tokens'] for m in MODELS)
    passed={m:int(re.search(r'(\d+) passed',audit['results'][m]['pytest']['stdout']).group(1)) if re.search(r'(\d+) passed',audit['results'][m]['pytest']['stdout']) else 0 for m in MODELS}
    skipped={m:int(re.search(r'(\d+) skipped',audit['results'][m]['pytest']['stdout']).group(1)) if re.search(r'(\d+) skipped',audit['results'][m]['pytest']['stdout']) else 0 for m in MODELS}
    check(skipped['opus']==7 and sum(skipped.values())==7,'Exactly seven initial pytest skips, all Opus E2E')
    passed['opus']+=7
    pytest_ok=all(audit['results'][m]['pytest']['returncode']==0 for m in MODELS)
    all_valid=all(x['valid'] for m in MODELS for x in final[m]['quantitative_diagnostics']['hidden_scenarios'].values())
    rows=[];scenario_rows=[];catrows=[]
    for m in MODELS:
        a,b=initial[m],final[m];x,y=a['quantitative_diagnostics'],b['quantitative_diagnostics']
        ss=[]
        for sid in sorted(x['hidden_scenarios']):
            p,q=x['hidden_scenarios'][sid],y['hidden_scenarios'][sid]
            sr=dict(model=m,scenario=sid,zero_initial=p['zero_rate_rmse_bps'],zero_final=q.get('zero_rate_rmse_bps'),
                forward_initial=p['forward_rate_rmse_bps'],forward_final=q.get('forward_rate_rmse_bps'),valid=q['valid'])
            sr['zero_delta']=sr['zero_final']-sr['zero_initial'] if sr['zero_final'] is not None else None
            scenario_rows.append(sr);ss.append(sr)
        row=dict(model=m.title(),key=m,score_initial=a['total_score'],score_final=b['total_score'],score_delta=b['total_score']-a['total_score'],
            zero_initial=x['zero_rate_rmse_bps'],zero_final=y['zero_rate_rmse_bps'],
            short_initial=x['short_end_zero_rmse_bps'],short_final=y['short_end_zero_rmse_bps'],
            long_initial=x['long_end_zero_rmse_bps'],long_final=y['long_end_zero_rmse_bps'],
            forward_initial=x['forward_rate_rmse_bps'],forward_final=y['forward_rate_rmse_bps'],
            hidden_price_initial=x['hidden_instrument_normalized_rmse'],hidden_price_final=y['hidden_instrument_normalized_rmse'],
            scenario_zero_initial=sum(r['zero_initial'] for r in ss)/10,scenario_zero_final=sum(r['zero_final'] for r in ss)/10,
            scenario_forward_initial=sum(r['forward_initial'] for r in ss)/10,scenario_forward_final=sum(r['forward_final'] for r in ss)/10,
            scenario_zero_better=sum(r['zero_delta'] < -1e-8 for r in ss),scenario_zero_worse=sum(r['zero_delta'] > 1e-8 for r in ss),
            tests_passed=passed[m],initial_test_skips=skipped[m],unverified_test_skips=0,checks_passed=len(b['hidden_tests']['passed']),
            additional_minutes=u[m]['feedback_all']['work_minutes'],additional_tokens=u[m]['feedback_all']['total_tokens'],additional_usd=u[m]['feedback_all']['usd_standard'])
        rows.append(row)
        catrows += [dict(model=m.title(),category=label,initial=a['category_scores'][key],final=b['category_scores'][key],
                         delta=b['category_scores'][key]-a['category_scores'][key],maximum=maximum) for key,label,maximum in CATS]
    by={r['key']:r for r in rows};rankrows=[by[m] for m in ranked]
    save(ROOT/NEW/'combined_summary.json',rows)
    save(ROOT/NEW/'scenario_comparison.json',scenario_rows)
    save(ROOT/NEW/'category_comparison.json',catrows)
    with (ROOT/NEW/'combined_summary.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

    title='金利カーブ・ベンチマーク：共通フィードバック後の最終評価'
    md('title',f'# {title}\n\n2026年9月5日 · 7モデルの初回提出と改善ラウンドを比較 · 時刻は日本標準時（JST）\n\n初回のブラインド成績を固定し、改善提出を同じ採点器で新たに検証。初回レポートは別ファイルとして保持。')
    tr=by['terra'];fa=by['fable']
    md('summary',f'''## 結論：得点改善と、推定器の改善は分けて読む

- **最終自動得点は{ranked[0].title()} {num(final[ranked[0]]['total_score'])}点、{ranked[1].title()} {num(final[ranked[1]]['total_score'])}点、{ranked[2].title()} {num(final[ranked[2]]['total_score'])}点。** 上位2モデルの差は{num(final[ranked[0]]['total_score']-final[ranked[1]]['total_score'])}点のみ。順位は今回1回の観測で、普遍的な能力順位ではない。
- **主データのゼロ金利RMSEが改善したのは{len(main_improved)}/7モデル。** Terraは{pair(tr['zero_initial'],tr['zero_final'])}bp（誤差{100*(1-tr['zero_final']/tr['zero_initial']):.1f}%減）。隠しシナリオは{tr['scenario_zero_better']}件改善・{tr['scenario_zero_worse']}件悪化し、一様な改善ではない。他{len(main_unchanged)}モデルの主ゼロRMSEは不変。形式対応の加点をカーブ精度の改善に数えない。
- **Fableの人工実験上の改善は、共通ストレス試験のゼロRMSEには表れなかった。** 隠し10シナリオ平均は{pair(fa['scenario_zero_initial'],fa['scenario_zero_final'])}bp。改善{fa['scenario_zero_better']}件・悪化{fa['scenario_zero_worse']}件・不変{10-fa['scenario_zero_better']-fa['scenario_zero_worse']}件。クラッシュ修正や特定人工条件での改善を否定するものではないが、共通10条件への効果は未観測。
- **追加投入量は{extra_tokens/1e6:.2f}Mトークン、標準API換算${extra_cost:.2f}。** Fableも完了値。実際の請求額ではない。7モデルの追加時間は各{min(u[m]['feedback_all']['work_minutes'] for m in MODELS):.1f}〜{max(u[m]['feedback_all']['work_minutes'] for m in MODELS):.1f}分で、同時実行時間の合計ではない。
- **独立pytestは補足再実行込みで計{sum(passed.values())}件合格。** 最初は422件合格・7件スキップだったが、公開入力の配置に起因するOpusの7件を追加実行し全件合格。隠しシナリオは{'70/70で有効なカーブ' if all_valid else '無効な出力あり'}。Lunaの初回出力上書きと、支払規約の不整合は残る比較上の留保。''','synthesis')
    md('definitions','''## 比較範囲と読み方

対象は同じ7モデルの初回1実行と、共通フィードバック後の1ラウンド。追加上限は60分、初回と同じモデル設定が意図された。初回の真値誤差に関するフィードバックを受けているため、改善後は新たなブラインド試験ではない。

得点は高いほど良い100点満点。数値精度30・モデル品質20・頑健性15・ソフトウェア15・データ品質10・レポート5・完遂5で、時間とコストは含まない。**ゼロ金利・フォワードRMSEは低いほど良いbp**（1bp=0.01%ポイント）。短期は2年以下、長期は15年以上。フォワードは各候補の出力列ではなく、採点格子上の推定ゼロ金利から数値微分して比較する。

非公開商品RMSE〈正規化値〉は金利誤差をbp、債券誤差を0.1価格単位に換算して混ぜた尺度で、純粋なbpではない。主データ、隠し10シナリオ、各モデルが自作した人工市場の結果は分ける。人工市場同士は形状・雑音・分割が異なるため横並び採点に使わない。''','synthesis')

    md('scores-heading','''## 1. 自動得点の変化は、項目別に分解できる

初回と改善後を同じ配点で並べた。総合点の上昇だけでは推定精度が上がったとは限らない。とくに比較JSONのキー、感度JSONの構造、英語見出し、サマリーの必須項目は、数値を変えなくても加点される。差分表はこの機械判定を含む生の採点結果で、手動補正していない。''','scores')
    chart('scores','モデル別総合得点','初回と改善後・100点満点。時間とコストを含まない。',
          [dict(model=r['model'],初回=r['score_initial'],改善後=r['score_final'],delta=r['score_delta'],zero_rmse=r['zero_final']) for r in rankrows],'model',['初回','改善後'],'点')
    table('score-table','総合得点と合格チェック数','点差は改善後−初回。チェック合格数は連続精度スコアとは別。',
        [dict(model=r['model'],initial=num(r['score_initial']),final=num(r['score_final']),delta=f"{r['score_delta']:+.3f}",checks=f"{r['checks_passed']}/41") for r in rankrows],
        [('model','モデル','text'),('initial','初回','text'),('final','改善後','text'),('delta','点差','text'),('checks','チェック','text')])
    table('category-deltas','カテゴリ別の得点差','0.000以外を表示。丸め誤差の範囲で総得点差に一致する。',
        [dict(model=r['model'],category=r['category'],before=num(r['initial']),after=num(r['final']),delta=f"{r['delta']:+.3f}") for r in catrows if abs(r['delta'])>.0001],
        [('model','モデル','text'),('category','カテゴリ','text'),('before','初回','text'),('after','改善後','text'),('delta','点差','text')])
    table('category-final-quality','改善後のカテゴリ得点 — 数値・推定・頑健性','満点が異なるため、単純な列の大小ではなく満点と併せて読む。',
        [dict(model=m.title(),numeric=num(final[m]['category_scores']['numerical_correctness']),quality=num(final[m]['category_scores']['quantitative_model_quality']),robust=num(final[m]['category_scores']['hidden_scenario_robustness'])) for m in ranked],
        [('model','モデル','text'),('numeric','数値 /30','text'),('quality','モデル品質 /20','text'),('robust','頑健性 /15','text')])
    table('category-final-delivery','改善後のカテゴリ得点 — 実装・データ・報告','時間やコストは含めない。点差に加え、変化しなかった項目も表示。',
        [dict(model=m.title(),software=num(final[m]['category_scores']['software_engineering_reproducibility']),data=num(final[m]['category_scores']['data_quality_handling']),report=num(final[m]['category_scores']['report_completeness']),complete=num(final[m]['category_scores']['completion_integrity'])) for m in ranked],
        [('model','モデル','text'),('software','実装 /15','text'),('data','データ /10','text'),('report','報告 /5','text'),('complete','完遂 /5','text')])

    md('precision-heading',f'''## 2. 主カーブはTerraが改善、他モデルは局所的な変更が中心

Terraは15年以上の平滑化ペナルティ倍率だけを0.5へ変更し、主データの長期ゼロRMSEが{pair(tr['long_initial'],tr['long_final'])}bpになった。一方、Astra・Sol・Opus・Sonnetは最終推定器を維持。Lunaは出力フォワードの計算式を変えたが、共通評価が使うゼロ金利カーブは維持した。Fableも主データの既定出力を保持している。

年限別の誤差を読むと、SolとSonnetの短期、AstraとTerraの長期という初回の弱点が一様に解消したわけではない。以下の前後比較は**同じ真値・同じ採点格子**による。''','synthesis')
    chart('zero-rmse','主データのゼロ金利RMSE','初回と改善後・bp。低いほど良い。',
        [dict(model=r['model'],初回=r['zero_initial'],改善後=r['zero_final'],short=r['short_final'],long=r['long_final'],forward=r['forward_final']) for r in rankrows],'model',['初回','改善後'],'bp')
    table('tenor-errors','年限別ゼロ金利・フォワード誤差','各セルは初回 → 改善後。いずれもbp。',
        [dict(model=r['model'],short=pair(r['short_initial'],r['short_final']),long=pair(r['long_initial'],r['long_final']),forward=pair(r['forward_initial'],r['forward_final'])) for r in rankrows],
        [('model','モデル','text'),('short','短期 ≤2年','text'),('long','長期 ≥15年','text'),('forward','フォワード','text')])
    table('risk-errors','非公開商品の再価格付けとリスク整合性','商品RMSEは混合正規化尺度。DV01・KRDは相対誤差の中央値（%）、対象商品数はモデルごとに異なる。',
        [dict(model=m.title(),price=pair(by[m]['hidden_price_initial'],by[m]['hidden_price_final']),
              dv01=pair(100*initial[m]['quantitative_diagnostics']['dv01_median_relative_error'],100*final[m]['quantitative_diagnostics']['dv01_median_relative_error']),
              krd=pair(100*initial[m]['quantitative_diagnostics']['key_rate_sum_median_relative_error'],100*final[m]['quantitative_diagnostics']['key_rate_sum_median_relative_error']),n=final[m]['quantitative_diagnostics']['risk_instruments_checked']) for m in ranked],
        [('model','モデル','text'),('price','商品RMSE','text'),('dv01','DV01 %','text'),('krd','KRD合計 %','text'),('n','商品数','number')])
    md('precision-limits','''採点器の「数値精度」には、価格再現だけでなく出力列同士の整合性も入る。Lunaの解析フォワードへの変更は、自作の人工データのフォワード評価を改善しても、共通の真値比較や出力格子上の整合性で同じ改善を保証しない。数値カテゴリの変化とゼロRMSEの変化を混同しない。''','scores')

    md('stress-heading','''## 3. 未見条件への変化は、10シナリオの前後で判定する

主データが同じでも、ロバスト処理のガードは別の観測配置で挙動を変える。ここでは候補の自己評価ではなく、採点側の同じ非公開10シナリオを初回・改善後で比較した。平均はシナリオの単純平均であり、全観測をプールしたRMSEではない。改善／悪化件数はゼロRMSEの差の符号で数え、統計的有意性を表さない。''','scores')
    table('scenario-summary','隠しシナリオの平均誤差','各セルは初回 → 改善後。改善/悪化/不変はゼロRMSEの10シナリオ内訳。',
        [dict(model=r['model'],zero=pair(r['scenario_zero_initial'],r['scenario_zero_final']),forward=pair(r['scenario_forward_initial'],r['scenario_forward_final']),
              direction=f"{r['scenario_zero_better']} / {r['scenario_zero_worse']} / {10-r['scenario_zero_better']-r['scenario_zero_worse']}") for r in rankrows],
        [('model','モデル','text'),('zero','ゼロ平均 bp','text'),('forward','フォワード平均 bp','text'),('direction','改善/悪化/不変','text')])
    matrix=[dict(scenario=sid,**{m.title():final[m]['quantitative_diagnostics']['hidden_scenarios'][sid]['zero_rate_rmse_bps'] for m in ranked}) for sid in sorted(initial['astra']['quantitative_diagnostics']['hidden_scenarios'])]
    md('matrix-reading','次のマトリクスはモデル×シナリオごとの改善後の誤差を示し、濃いほどゼロ金利RMSEが大きい。総合順位より、特定条件に誤差が集中するかを見るための図である。','scores')
    chart('scenario-matrix','改善後のシナリオ別ゼロ金利RMSE','10シナリオ×7モデル・bp。濃いセルほど誤差が大きい。',matrix,'scenario',[m.title() for m in ranked],'bp',kind='heatmap')
    changed=[r for r in scenario_rows if abs(r['zero_delta'] or 0)>1e-8]
    if changed:
        md('stress-changes','平均が改善していても悪化ケースは残り得る。次表はゼロRMSEが変わったモデル×シナリオだけを抽出しており、無変化のケースを黙って改善扱いしていない。人工実験で改善したケースと隠しシナリオは別の母集団である。','scores')
        table('scenario-changes','変化した隠しシナリオ','ゼロRMSEが変化したケースのみ。bp、負の差分が改善。',
            [dict(model=r['model'].title(),scenario=r['scenario'],zero=pair(r['zero_initial'],r['zero_final']),delta=f"{r['zero_delta']:+.3f}",forward=pair(r['forward_initial'],r['forward_final'])) for r in changed],
            [('model','モデル','text'),('scenario','ケース','text'),('zero','ゼロ bp','text'),('delta','差分 bp','text'),('forward','フォワード bp','text')])

    md('time-heading','''## 4. 追加時間は、申告値ではなく作業ターンで揃えた

時間は関連する指示の開始から完了までの壁時計時間。ツール実行・待機・文脈圧縮を含み、純粋な推論時間ではない。最初の中断試行も改善コストに含め、指示を再送するまでのターン間待ちは除いた。各モデルは並行して動いたので、モデル別時間の和をユーザーが待った時間とは解釈しない。

Sonnetの自己申告24.5分は独自の計測開始が遅く、ログでは39.31分。Fableの最終追加作業は33.37分。初回Opusは途中停止後の再開を含む作業124.22分で、再開待ち78.33分は除外した。''','synthesis')
    chart('time-comparison','初回と改善ラウンドの作業時間','分。改善には中断試行を含み、ターン間待ち時間は含まない。',
        [dict(model=m.title(),初回=u[m]['initial']['work_minutes'],改善追加=u[m]['feedback_all']['work_minutes'],main=u[m]['feedback_main']['work_minutes'],prep=u[m]['feedback_prep']['work_minutes']) for m in ranked],
        'model',['初回','改善追加'],'分',source='usage')
    table('time-detail','改善作業時間の内訳','本実行＋中断試行＝改善追加。累計は初回＋改善追加。',
        [dict(model=m.title(),main=num(u[m]['feedback_main']['work_minutes'],2),prep=num(u[m]['feedback_prep']['work_minutes'],2),extra=num(u[m]['feedback_all']['work_minutes'],2),total=num(u[m]['initial']['work_minutes']+u[m]['feedback_all']['work_minutes'],2)) for m in ranked],
        [('model','モデル','text'),('main','本実行 分','text'),('prep','中断分 分','text'),('extra','追加計 分','text'),('total','累計 分','text')],source='usage')
    timing_rows=[]
    for t in usage['turns']:
        local=lambda ts:datetime.fromisoformat(ts.replace('Z','+00:00')).astimezone(ZoneInfo('Asia/Tokyo')).strftime('%H:%M:%S')
        timing_rows.append(dict(model=t['model'].title(),phase='中断試行' if t['status']=='turn_aborted' else '本実行',
            interval=local(t['start_utc'])+' → '+local(t['end_utc']),minutes=num(t['work_minutes'],2)))
    table('turn-timing','改善ラウンドの時系列','2026年9月5日・JST。各ターンの開始→完了または中断。',timing_rows,
        [('model','モデル','text'),('phase','区分','text'),('interval','開始 → 終了','text'),('minutes','分','text')],source='usage',sort=('interval','asc'))

    md('tokens-heading',f'''## 5. 追加処理は{extra_tokens/1e6:.2f}Mトークン、読み直しの割合が大きい

トークンは「入力＋出力」の総処理量で、キャッシュ読み取りも含む。同じ履歴を繰り返し読む分が累積するため、生成文章の長さではない。推論トークンは出力の内数で、加算し直していない。プロバイダー間でトークナイザーも異なる。

Codexは応答ID別の使用量を取り、全応答でターン累計・タスク累計の両方と一致を確認した。今回は文脈圧縮を含むため、従来の画面用累積カウンターだけでは一部を落とす。Claudeは同じmessage.idの複数ブロックを重複除去し、requestIdも照合した。''','usage')
    chart('token-composition','改善ラウンドのトークン内訳','M=100万トークン。4区分は排他的で、合計が追加総量に一致する。',
        [dict(model=m.title(),キャッシュ読取=u[m]['feedback_all']['cache_read_input']/1e6,
              キャッシュ書込=(u[m]['feedback_all']['cache_write_5m']+u[m]['feedback_all']['cache_write_1h'])/1e6,
              通常入力=u[m]['feedback_all']['uncached_input']/1e6,出力=u[m]['feedback_all']['output_total']/1e6,
              total=u[m]['feedback_all']['total_tokens']) for m in ranked],'model',['キャッシュ読取','キャッシュ書込','通常入力','出力'],'M tokens',source='usage',kind='horizontalStackedBar')
    table('token-totals','初回・追加・累計トークン','監査用の正確な値。キャッシュ読取率の分母は入力全体。',
        [dict(model=m.title(),initial=f"{u[m]['initial']['total_tokens']:,}",extra=f"{u[m]['feedback_all']['total_tokens']:,}",total=f"{u[m]['initial']['total_tokens']+u[m]['feedback_all']['total_tokens']:,}",read=f"{100*u[m]['feedback_all']['cache_read_share']:.2f}%") for m in ranked],
        [('model','モデル','text'),('initial','初回','text'),('extra','追加','text'),('total','累計','text'),('read','読取率','text')],source='usage')
    table('token-output','追加の出力・推論トークン','推論は出力に含まれる。Opus中断中の1応答（出力3token）の推論内訳のみ不明。',
        [dict(model=m.title(),output=f"{u[m]['feedback_all']['output_total']:,}",reasoning=f"{u[m]['feedback_all']['known_reasoning_tokens']:,}"+('以上' if u[m]['feedback_all']['reasoning_unknown_responses'] else ''),requests=u[m]['feedback_all']['api_responses']) for m in ranked],
        [('model','モデル','text'),('output','出力総数','text'),('reasoning','うち推論','text'),('requests','応答数','number')],source='usage')

    md('cost-heading',f'''## 6. 追加費用は標準API換算${extra_cost:.2f}、実請求額ではない

料金は2026年9月5日に確認した公開API Standard単価で、通常入力・キャッシュ読取・書込・出力を別々に計算した。Claudeの書込はログ上すべて1時間TTLなので通常入力の2倍単価。Sonnet 5は予定されていた値上げが撤回され、入力$2・出力$10/MTokが標準。Fable 5.1のキャッシュ読取は$0.25/MTokで、Fable 5の$1とは異なる。[OpenAI公式料金表](https://developers.openai.com/api/docs/pricing)、[Claude公式料金表](https://platform.claude.com/docs/en/about-claude/pricing)に基づく。

**Codexの実サービス階層は記録から確定できない。** 下図はStandardで揃えた比較であり、FastならGPT4モデルの換算額は2倍。税・為替・地域加算・契約割引・定額プラン料金・ローカル計算費を含まない。GPTの272K入力超割増も確認したが今回の対象応答に該当なし。Claudeの今回のモデルには長文割増なし。''','usage')
    chart('cost-comparison','初回と改善追加の推定APIコスト','USD、Standard単価換算。実請求額・月額プラン料金ではない。',
        [dict(model=m.title(),初回=u[m]['initial']['usd_standard'],改善追加=u[m]['feedback_all']['usd_standard'],tokens=u[m]['feedback_all']['total_tokens'],time=u[m]['feedback_all']['work_minutes']) for m in ranked],
        'model',['初回','改善追加'],'USD',source='usage')
    table('cost-totals','推定コストと料金階層の感度','USD。Fast列はGPTのみ2倍にした仮定、Claudeは記録されたStandardのまま。',
        [dict(model=m.title(),initial=f"${u[m]['initial']['usd_standard']:.2f}",extra=f"${u[m]['feedback_all']['usd_standard']:.2f}",total=f"${u[m]['initial']['usd_standard']+u[m]['feedback_all']['usd_standard']:.2f}",fast=f"${u[m]['feedback_all']['usd_fast_scenario']:.2f}") for m in ranked],
        [('model','モデル','text'),('initial','初回','text'),('extra','追加','text'),('total','累計','text'),('fast','追加 Fast仮定','text')],source='usage')
    table('rates','換算に用いた公開単価','USD / 100万token。書込欄は実際に観測されたTTL（Claudeは1時間）。',
        [dict(model=u[m]['model_ids'][0],input=num(usage['rates_usd_per_million'][u[m]['model_ids'][0]][0],2),read=num(usage['rates_usd_per_million'][u[m]['model_ids'][0]][1],2),write=num(usage['rates_usd_per_million'][u[m]['model_ids'][0]][3],2),output=num(usage['rates_usd_per_million'][u[m]['model_ids'][0]][4],2)) for m in MODELS],
        [('model','実行モデルID','text'),('input','通常入力','text'),('read','読取','text'),('write','書込','text'),('output','出力','text')],source='usage')

    md('methods-heading','''## 7. 各モデルが何を変え、何を見送ったか

以下はソースと候補の実験記録に基づく設計・採否の整理。人工実験の数値は候補側の報告であり、前節までの共通採点値とは別である。変更を見送ったこと自体を失敗とは扱わず、検証が目的の精度を測れていたかを確認する。''','methods')
    profiles_text={
      'astra':'''**ゼロ金利をlog(1+年限)上の自然3次スプラインで推定**。Huber損失と年限グループ検証で平滑化を選ぶ。改善では長期ノット、罰則、端点、ロバスト重みを一要因ずつ検証。人工条件で良くなる案も他条件や公開短期で悪化したため不採用。最終カーブは維持し、直接割引係数による価格診断・JSON・英日見出しを追加。「過剰平滑化が主因」との断定には至っていない。''',
      'sol':'''**商品ごとの一定利回り→半年バケット→移動中央値→PCHIP**の基準モデルを維持。高度スプラインより公開ホールドアウトが良かったため選択。集約解除で人工短期ゼロ誤差は大幅改善したが、フォワードと公開検証が悪化して不採用。非平坦な人工カーブで、利付商品の一定利回りを満期ゼロに近似する誤差も確認。課題は補間だけでなく、情報圧縮と選択指標の整合性。''',
      'terra':'''**自然3次スプラインで対数割引係数を推定**し、局所フォワード変化を抑制。15年以上の平滑化倍率だけを0.25/0.5/1/2/4で比較し、0.5を採用。人工真値と公開長期債の双方で改善を確認し、価格規約や短期モデルは維持。単位・bid/askの監査ラベルやサマリーも整備。共通評価での改善・悪化は前節のシナリオ表で確認できる。''',
      'luna':'''**区分線形ゼロ金利を全商品へロバストにフィット**。高度モデルは基準比5%以内の悪化でも採用可能という選択ゲートを維持。ノットや罰則を調べたが、採用はf=z+Tz′による出力フォワードの解析式化のみ。人工フォワードRMSEの改善は報告したものの、ゼロ金利の推定は変えていない。初回フォルダを直接改変した点は実験規約上の問題。''',
      'sonnet':'''**全商品を重み付き非線形最小二乗で合わせる区分線形ゼロ金利**を採用。平滑化した高度モデルは公開ホールドアウトで負けたため見送り。改善で短期ホールドアウトがないこと、基準モデルのフォワードがノットで跳ぶことを診断したが、検証設計や最終推定器は変更していない。選択JSONの別名キー、平滑性診断、支払規約の説明を補修。''',
      'opus':'''**瞬間フォワードの3次スプラインを積分して割引係数を構成**。年限依存罰則、商品別誤差スケール、Huber→Tukey再重み付け、年限ブロックCVと安全ゲートを使用。改善では「疎な年限＋汚染」の失敗を小さな例で再現。1-SE選択や罰則下限は別条件を悪化させ、事前基準に従って不採用。数値モデルは維持し、テストの個人パスと形式・診断を改善。''',
      'fable':'''**瞬間フォワードの3次Bスプライン＋年限依存罰則**。整合する観測群を残す外れ値ガードと年限別5-fold CVが特徴。改善では疎なfoldでの商品別スケール欠損によるKeyErrorを修正し、単独クラスタにHuberを使うガードを採用。自作のhump＋20%欠損で短期RMSE7.92→0.70bpと報告。他の人工24条件と公開既定出力は不変。非既定ceil規則のスタブaccrualも修正し、規約感度とJSON形式を整備。'''}
    for m in MODELS:md('method-'+m,'### '+m.title()+'\n\n'+profiles_text[m],'methods')

    original_paths={'astra':ROOT/'results/astra','sol':ROOT/'output/sol','terra':Path('/Users/ankimo1210/Documents/terra'),
                    'luna':ROOT/'output/luna','sonnet':ROOT/'output/sonnet','opus':ROOT/'results/opus','fable':ROOT/'results/fable'}
    preservation=[]
    for m,hashes in prior['candidate_before'].items():
        changes=[];missing=[]
        for rel,h in hashes.items():
            p=original_paths[m]/rel
            if not p.exists():missing.append(rel)
            elif hashlib.sha256(p.read_bytes()).hexdigest()!=h:changes.append(rel)
        preservation.append(dict(model=m,tracked=len(hashes),changed=changes,missing=missing))
    save(ROOT/NEW/'original_preservation.json',preservation)
    next(s for s in SOURCES if s['id']=='qa')['query']['tables_used'].append(f'{NEW}/original_preservation.json')
    md('validation-heading',f'''## 8. 完走・テスト・保全を別々に検証した

改善版は一時ディレクトリへコピーし、CLIを2回、隠し10シナリオ、採点器のunittest、さらに各候補のpytest全体を実行した。最初は422件合格・7件スキップ。Opusの実データE2Eテスト7件は、一時コピーの親階層に公開入力がなく自動スキップされていた。実装が提供するQUANTCURVE_MARKET_DATA環境変数で公開入力を指定し、その7件だけを再実行して全件合格を確認した。重複を除いた確認済み合格は計{sum(passed.values())}件、未確認スキップは0件。候補コードは変更していない。採点器が実行するunittestとpytestの件数は別で、足し合わせた成功件数ではない。

環境はPython 3.12.11、NumPy 2.5.2、pandas 2.3.3、SciPy 1.18.1、Matplotlib 3.11.1、pytest 8.4.2。初回と同じ採点器・互換ラッパーのハッシュを確認。公開入力12ファイル・評価側108ファイルのマニフェストも実行前後で一致し、今回採点した7提出物は採点前後で不変。''','qa')
    qa_rows=[dict(model=m.title(),pytest=passed[m],result=('203＋補足7合格' if m=='opus' else '合格') if audit['results'][m]['pytest']['returncode']==0 else '失敗あり',checks=f"{len(final[m]['hidden_tests']['passed'])}/41",scenarios=f"{sum(s['valid'] for s in final[m]['quantitative_diagnostics']['hidden_scenarios'].values())}/10") for m in ranked]
    # This lookup is derived from two controlling sources, so use a dedicated executed query.
    db.execute('CREATE TABLE qa(model TEXT, document TEXT)')
    db.executemany('INSERT INTO qa VALUES(?,?)',[(r['model'],json.dumps(r)) for r in qa_rows])
    qa_sql='SELECT model, json_extract(document,\'$.pytest\') AS pytest, json_extract(document,\'$.result\') AS result, json_extract(document,\'$.checks\') AS checks, json_extract(document,\'$.scenarios\') AS scenarios FROM main.qa ORDER BY model;'
    db.execute(qa_sql).fetchall()
    source('test-results','独立pytestと共通採点チェック',f'{NEW}/evaluation_audit.json',[f'{NEW}/evaluation_audit.json',f'{NEW}/opus_e2e_verification.json']+[f'{NEW}/{m}_score.json' for m in MODELS]+['main.qa'],qa_sql,
        ['pytest pass count from independent captured pytest output. Checklist out of 41. Valid scenario count out of 10.'],
        'qa rows derived by this report script from saved pytest stdout and scorer JSON; NOT the candidate-reported test counts.')
    table('tests','独立再検証の結果','pytestは今回の再実行。チェック数とシナリオ数は共通採点器。',qa_rows,
        [('model','モデル','text'),('pytest','pytest合格','number'),('result','pytest結果','text'),('checks','採点チェック','text'),('scenarios','有効ケース','text')],source='test-results')
    md('protocol','''## 9. 公平性・採点規約の留保は解消していない

**原本保全：** 初回に記録したファイル集合はLuna以外の6モデルで不変。Lunaは初回出力先を直接編集し、11ファイルが変化した。初回成績は保存済みJSONを使用し、改変済みフォルダを「初回」として再採点していない。Astra・Terra・Opusには完全な指示の受領前に原本配下へ作業用ディレクトリを作成した記録もある。既存ファイルのハッシュ一致は「新規書込が一切なかった」ことまで保証しない。

**セッションと介入：** 全モデルが初回と同じセッションを継続している。新規セッションは推奨条件だったが実施されていない。Astra・Sol・Terra・Luna・Opusは冒頭試行が中断され、完全な指示を再送された。主比較ではその作業・使用量を含め、完全指示後だけの値も別途保存した。プロンプトには共通指摘とモデル別コメントがあり、全モデルが同じ量・内容の情報を受けた完全対称実験ではない。

**支払規約：** 公開の満期元本・クーポン説明と、生成器・採点器のround(T×frequency)支払列には端数年限で不整合がある。今回採点器は変更しておらず、適合度に規約差の影響が残る。候補の独立価格テストは自己採用規約の実装確認であり、生成側と同一規約だった証明ではない。

**得点設計：** モデル品質20点のうち18点は主カーブの誤差に基づき、数値精度との証拠は独立でない。英語キーワード、JSONキー、個人パス検索、欠損のaction=exclude判定には形式依存がある。静的な「他モデル参照」警告は自身のパスも拾うため、それだけで不正閲覧を断定しない。

**統計的限界：** 各モデル各ラウンド1実行、同じ10シナリオであり、試行間分散・信頼区間・未知市場での一般化は未測定。経過時間にはツール待ちや同時実行負荷が入り、純粋な生成速度ではない。追加コストもAPI換算で実請求額ではない。得点/ドルだけで順位を作ると、形式加点を経済的な推定性能と誤認するため採用しない。''','synthesis')
    md('reader-verification','''### HTML表示の検証範囲

数値・入力ハッシュ・埋込データ・HTML構造は検証済み。対応するChromiumが環境にないため、ブラウザー上での見た目・狭幅表示・ソース画面操作・グラフSVG抽出は未検証。自己完結型の共通リーダーと、同じデータから生成した代替表を保持している。''')
    md('next','''## 10. 次の実験は、規約の共通化と反復を優先する

1. **評価側で支払規約を明文化し、生成器・採点器・公開仕様を一致させる。** 元の初回・今回スコアは固定し、修正規約での結果は別バージョンとして保存する。
2. **価格付けだけ共通化した再フィットを行う。** カーブ表現や重みを変えず、規約差の寄与を切り分ける。真値を使う調査は採点側だけで実施する。
3. **短期・長期の悪化を拾う採用条件を全モデルで統一する。** Sol・Sonnetの短期ホールドアウト、Astra・Terraの長期制御、Fable・Opusの疎な観測と汚染を同じ人工市場群で測る。単独の改善案と複数案の相互作用を分ける。
4. **新規セッション・同一予算・複数seedで反復する。** 数値誤差、ストレス悪化件数、失敗率、時間、API換算費を別々に報告し、形式点を外した感度分析も併記する。

現時点で採用できる結論は、この実行・規約・採点器の下でどの変更が改善したかまで。最初から高設定でやり直せば改善する、あるいは特定のカーブ表現が常に優れるとは示していない。''')
    md('questions','''## 残る問い

- 支払日・accrualを統一すると、初回のモデル間の精度差はどの程度残るか。
- 自作の検証で拒否された変更は、共通の短期・長期の採用条件なら選ばれるか。
- Fableの単独クラスタ保護は、小さな孤立外れ値を残す副作用を持つか。
- 規約を修正した新規データと複数seedでも、同じ精度・コストの関係が再現するか。''')

    artifact=dict(surface='report',manifest=dict(version=1,surface='report',title=title,
        description='初回と共通フィードバック改善後を比較する7モデルの最終技術評価。',generatedAt=STAMP,
        blocks=BLOCKS,cards=CARDS,charts=CHARTS,tables=TABLES,sources=SOURCES),
        snapshot=dict(version=1,status='ready',generatedAt=STAMP,datasets=DATA),sources=SOURCES)
    from report_extensions import extend, companion_notebook
    extend(sys.modules[__name__], artifact)
    companion_notebook(sys.modules[__name__])
    # Keep every statistic finite and every referenced dataset resolvable.
    for chart_spec in CHARTS:
        check(chart_spec['dataset'] in DATA,'Chart dataset: '+chart_spec['id'])
    for table_spec in TABLES:
        check(table_spec['defaultSort']['field'] in {c['field'] for c in table_spec['columns']},'Table sort: '+table_spec['id'])
    check(all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in INPUTS.items()),'Sources unchanged during report build')
    save(HERE/'artifact.json',artifact)
    save(HERE/'validation.json',dict(checks_passed=len(CHECKS),checks=CHECKS,input_sha256=INPUTS,
        artifact_sha256=hashlib.sha256((HERE/'artifact.json').read_bytes()).hexdigest(),pytest_all_pass=pytest_ok,
        report_mode='html',audience='technical',chart_map=CHART_MAP,
        section_mapping={'Title':'title','Technical summary':'summary','Key findings':'sections 1–6',
          'Scope/data/metric definitions':'definitions moved before figures to prevent ambiguous units',
          'Methodology/experimental design':'section 7','Limitations/robustness':'sections 3, 8, 9',
          'Recommended next steps':'section 10','Further questions':'questions'},
        omissions={'scatter':'Seven model observations; no spurious trend or invented repeats. Exact lookup tables used.',
                   'standalone data-source appendix':'Canonical source modals and source inventory preserve provenance.',
                   'cost_roi_ranking':'Composite score includes format points; no single score-per-dollar recommendation.',
                   'style':'Canonical packaged reader owns layout/tokens; no parallel HTML renderer or external CSS.'}))
    print(json.dumps(dict(models=7,blocks=len(BLOCKS),charts=len(CHARTS),tables=len(TABLES),checks=len(CHECKS),
        extra_tokens=extra_tokens,extra_usd=extra_cost,summary=rows),ensure_ascii=False))


if __name__=='__main__':main()
