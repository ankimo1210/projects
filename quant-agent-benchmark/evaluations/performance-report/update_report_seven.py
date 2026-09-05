#!/usr/bin/env python3
"""Update the current canonical report without reverting earlier layout edits.

Only presentation/evaluation files are written. Candidate code and scorers are
immutable. Source SQL is actually executed and independently reconciled.
"""
import contextlib
import copy
import csv
import hashlib
import io
import json
import math
import re
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
SNAP = 'analysis/final-review-20260905/expanded-7-models'
OLD = ['fable', 'opus', 'sol', 'astra']
NEW = ['terra', 'luna', 'sonnet']
CATS = [
    ('numerical', 'numerical_correctness', '数値精度', 30),
    ('model_quality', 'quantitative_model_quality', 'モデル品質', 20),
    ('robustness', 'hidden_scenario_robustness', '頑健性', 15),
    ('software_engineering', 'software_engineering_reproducibility', 'ソフトウェア', 15),
    ('data_quality', 'data_quality_handling', 'データ品質', 10),
    ('report', 'report_completeness', 'レポート', 5),
    ('completion', 'completion_integrity', '完遂', 5),
]
CHECKS, INPUTS = [], {}


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(rel, csv_file=False):
    path = BASE / rel
    INPUTS[rel] = digest(path)
    text = path.read_text(encoding='utf-8-sig')
    return list(csv.DictReader(text.splitlines())) if csv_file else json.loads(text)


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def check(test, label):
    if not test:
        raise AssertionError(label)
    CHECKS.append(label)


def close(a, b, label, tolerance=1e-7):
    check(math.isclose(float(a), float(b), abs_tol=tolerance, rel_tol=0), label)


def fmt(n, places=3):
    return f'{float(n):,.{places}f}'


def integer(n):
    return f'{int(n):,}'


def main():
    current_hash = digest(HERE / 'artifact.json')
    artifact = read('evaluations/performance-report/artifact.json')
    original = copy.deepcopy(artifact)
    summary = read(f'{SNAP}/combined_summary.json')
    models = [r['model'] for r in summary]
    check(set(models) == set(OLD + NEW) and len(models) == 7, 'Seven unique models')
    if {r['model'].lower() for r in artifact['snapshot']['datasets']['ranking']} == set(models):
        # Do not apply the one-time table expansion a second time or roll back
        # user edits. A changed snapshot needs a separately reviewed update.
        prior_validation = read('evaluations/performance-report/validation.json')
        for path, expected in prior_validation['input_sha256'].items():
            if path.startswith(SNAP+'/'):
                check(digest(BASE/path)==expected, 'Existing seven-model evidence unchanged: '+path)
        check(digest(HERE/'artifact.json') == prior_validation['artifact_sha256'], 'Existing report matches validated artifact')
        repair_source_bindings(artifact)
        save(HERE/'artifact.json',artifact)
        prior_validation['artifact_sha256']=digest(HERE/'artifact.json')
        prior_validation['provenance_review']='Mixed score/time narrative has no single-source binding; all material source files are declared.'
        save(HERE/'validation.json',prior_validation)
        print('Seven-model report is current; provenance reviewed. Package artifact.json with the canonical builder.')
        return
    s = {r['model']: r for r in summary}
    e = {m: read(f'{SNAP}/{m}_score.json') for m in models}
    runtime = {r['model']: r for r in read(f'{SNAP}/runtime_tokens.csv', True)}
    turns = read(f'{SNAP}/user_turns.csv', True)
    apis = read(f'{SNAP}/api_responses.csv', True)
    audit = read(f'{SNAP}/evaluation_audit.json')
    usage = read(f'{SNAP}/usage_audit.json')
    tests = read(f'{SNAP}/pytest_verification.json')
    check(bool(audit.get('completed_utc')) and audit['original_candidates_unchanged'], 'Completed immutable candidate audit')
    for phase in ['manifest_before', 'manifest_after']:
        for scope, count in [('input', 12), ('evaluator', 108)]:
            v = audit[phase][scope]
            check(v['files_verified'] == count and not v['mismatches'], f'{phase} {scope}: manifest matches')
    selected = [t for t in turns if t['selected_work_turn'] == 'True']
    check(len(selected) == 8, 'Eight measured work turns')
    check(all(t['minutes'] and t['end_jst'] for t in selected), 'Work intervals have completion boundaries')
    check(all(not t['minutes'] and not t['end_jst'] for t in turns if t['model'] == 'sonnet' and t['turn_number'] in ['1', '2']), 'Unmeasured Sonnet setup time is null, not zero')
    for m in models:
        r = runtime[m]
        close(sum(e[m]['category_scores'].values()), s[m]['score'], m + ': category sum', .002)
        close(e[m]['total_score'], s[m]['score'], m + ': score summary')
        for alias, key, _, maximum in CATS:
            close(e[m]['category_scores'][key], s[m][alias], m + ': ' + key)
            check(0 <= s[m][alias] <= maximum, m + ': category bounds ' + key)
        for part in ['uncached_input', 'cache_read_input', 'cache_creation_input', 'output_nonreasoning', 'output_reasoning', 'input_total', 'output_total', 'total_tokens']:
            main_api = [a for a in apis if a['model'] == m and a['selected_work_turn'] == 'True']
            check(sum(int(a[part]) for a in main_api) == int(r[part]), m + ': API sum ' + part)
            check(sum(int(t[part]) for t in selected if t['model'] == m) == int(r[part]), m + ': turn sum ' + part)
        check(sum(int(r[k]) for k in ['uncached_input', 'cache_read_input', 'cache_creation_input', 'output_nonreasoning', 'output_reasoning']) == s[m]['total_tokens'], m + ': exclusive token sum')
        check(int(r['output_nonreasoning']) + int(r['output_reasoning']) == int(r['output_total']), m + ': reasoning output is subset')
        close(sum(float(t['minutes']) for t in selected if t['model'] == m), s[m]['work_time_min'], m + ': work minutes')
        close(s[m]['work_time_min'] + s[m]['between_work_turn_idle_min'], s[m]['work_span_min'], m + ': elapsed identity')
        check(sum(int(t['total_tokens']) for t in turns if t['model'] == m) == s[m]['session_total_tokens'], m + ': session sum')
        check(tests[m]['returncode'] == 0 and not tests[m]['timed_out'], m + ': pytest succeeded')
        check(re.search(rf'\b{s[m]["verified_tests_passed"]} passed\b', tests[m]['stdout']) is not None, m + ': pytest count')
        check(s[m]['reported_usd_cost'] is None, m + ': cost remains unknown')
        u = usage[m]
        check(u.get('independent_cumulative_reconciliation') or u.get('all_repeated_usage_identical'), m + ': independent usage reconciliation')
        d = e[m]['quantitative_diagnostics']
        check(len(d['hidden_scenarios']) == 10 and all(x['valid'] for x in d['hidden_scenarios'].values()), m + ': ten valid stress scenarios')
        check(len(e[m]['hidden_tests']['details']) == 41, m + ': 41 scoring checks')

    # Keep and execute the current artifact's genuine queries, including earlier
    # report improvements. No SQL-shaped pseudo provenance is substituted.
    db = sqlite3.connect(':memory:')
    db.row_factory = sqlite3.Row
    for name, records in [('raw_evaluations', e), ('raw_pytest', tests)]:
        db.execute(f'CREATE TABLE {name} (model TEXT PRIMARY KEY, document TEXT)')
        db.executemany(f'INSERT INTO {name} VALUES (?, ?)', [(m, json.dumps(v)) for m, v in records.items()])
    fields = list(turns[0])
    db.execute('CREATE TABLE raw_user_turns (' + ','.join('"' + k + '" TEXT' for k in fields) + ')')
    db.executemany('INSERT INTO raw_user_turns VALUES (' + ','.join('?' for _ in fields) + ')', [[t[k] for k in fields] for t in turns])
    sources = {q['id']: q for q in artifact['manifest']['sources']}
    sql_rows = {sid: [dict(r) for r in db.execute(sources[sid]['query']['sql'])] for sid in ['scores', 'precision', 'usage', 'qa']}
    for row in sql_rows['scores']:
        close(row['category_score'], e[row['model']]['category_scores'][row['category']], 'SQL score ' + row['model'] + row['category'])
        close(row['attainment'], row['category_score'] / row['category_maximum'], 'SQL attainment ' + row['model'] + row['category'])
    for row in sql_rows['usage']:
        for key, val in row.items():
            if key not in ['model', 'output_per_api']:
                close(val, runtime[row['model']][key], 'SQL usage ' + row['model'] + key)
                runtime[row['model']][key] = val
    for row in sql_rows['qa']:
        m = row['model']
        check(row['pytest_passed'] == s[m]['verified_tests_passed'], m + ': SQL pytest count')
        check(row['hidden_passed'] == s[m]['hidden_checks_passed'], m + ': SQL scoring check count')
        check(row['valid_scenarios'] == 10 and row['hidden_checks'] == 41, m + ': SQL evaluation population')
    diagnostics = {(x['model'], x['scope']): json.loads(x['metrics']) for x in sql_rows['precision']}
    d = {m: diagnostics[m, 'main'] for m in models}
    winners = {f's{i:02d}': [m for m in models if next(r for r in sql_rows['precision'] if r['model'] == m and r['scope'] == f's{i:02d}')['zero_error_rank'] == 1] for i in range(1, 11)}
    scenario_wins = {m: sum(m in v for v in winners.values()) for m in models}
    excache = {m: int(runtime[m]['total_tokens']) - int(runtime[m]['cache_read_input']) for m in models}
    best, second = models[:2]
    fast = min(models, key=lambda m: s[m]['work_time_min'])
    few = min(models, key=lambda m: s[m]['total_tokens'])
    check(best == 'fable' and second == 'opus', 'Narrative anchor: Fable and Opus lead')
    check(fast == few == 'terra', 'Narrative anchor: Terra least time and volume')
    stamp = datetime.now(timezone.utc).isoformat()
    manifest, data = artifact['manifest'], artifact['snapshot']['datasets']
    manifest['description'] = '7モデルの最終スコア・数値精度・実行時間・トークン・再現性・評価上の限界を統合。'
    manifest['generatedAt'] = artifact['snapshot']['generatedAt'] = stamp
    data['headlines'] = [dict(best_score=s[best]['score'], score_lead=round(s[best]['score']-s[second]['score'], 3), fastest_min=s[fast]['work_time_min'], fewest_tokens=s[few]['total_tokens'])]
    manifest['cards'][1]['metrics'][0]['label'] = 'Terra · 最短作業時間（分）'
    manifest['cards'][2]['metrics'][0]['label'] = 'Terra · 最少処理トークン'
    data['ranking'] = [dict(model=m.title(), score=s[m]['score'], rank=s[m]['rank'], core_score=sum(s[m][k] for k in ['numerical','model_quality','robustness']), max_score=100, candidate=s[m]['candidate_path']) for m in models]
    for index, row in enumerate(data['category-scores']):
        for m in models:
            row[m.title()] = fmt(s[m][CATS[index][0]] if index < 7 else s[m]['score'])
    data['category-attainment'] = [dict(category=f'{label} /{maximum}', maximum=maximum, **{m.title(): s[m][alias]/maximum for m in models}) for alias, key, label, maximum in CATS]
    data['score-gaps'] = [dict(category=label, max=maximum, **{f'vs_{m}': fmt(s['fable'][alias]-s[m][alias]) for m in ['astra','sol','terra','luna']}) for alias, key, label, maximum in CATS]
    data['zero-errors'] = [dict(model=m.title(), zero_rmse=d[m]['zero_rate_rmse_bps'], forward_rmse=d[m]['forward_rate_rmse_bps'], short_rmse=d[m]['short_end_zero_rmse_bps'], long_rmse=d[m]['long_end_zero_rmse_bps']) for m in sorted(models,key=lambda m: d[m]['zero_rate_rmse_bps'])]
    metric_keys = ['zero_rate_rmse_bps','weighted_zero_rate_rmse_bps','forward_rate_rmse_bps','short_end_zero_rmse_bps','long_end_zero_rmse_bps','hidden_instrument_normalized_rmse']
    for row, key in zip(data['accuracy-detail'], metric_keys, strict=True):
        for m in models:
            row[m.title()] = fmt(d[m][key])
    data['risk-detail'] = [dict(model=m.title(), bidask=fmt(d[m]['bid_ask_normalized_pricing_rmse']), n=d[m]['risk_instruments_checked'], dv01=fmt(100*d[m]['dv01_median_relative_error'],4)+'%', key=f"{d[m]['key_rate_sum_median_relative_error']:.3e}") for m in models]
    data['scenario-zero'] = [dict(model=m.title(), valid_scenarios=10, **{scenario: diagnostics[m,scenario]['zero_rate_rmse_bps'] for scenario in winners}) for m in models]
    data['scenario-forward'] = [dict(scenario=scenario, **{m.title():fmt(diagnostics[m,scenario]['forward_rate_rmse_bps']) for m in models}, lowest=min(models,key=lambda m:diagnostics[m,scenario]['forward_rate_rmse_bps']).title()) for scenario in winners]
    data['work-time'] = [dict(model=m.title(), minutes=s[m]['work_time_min'], span_minutes=s[m]['work_span_min'], idle_minutes=s[m]['between_work_turn_idle_min'], work_turns=runtime[m]['work_turns']) for m in sorted(models,key=lambda m:s[m]['work_time_min'])]
    data['time-detail'] = [dict(model=m.title(), work=fmt(s[m]['work_time_min'],2), idle=fmt(s[m]['between_work_turn_idle_min'],2), span=fmt(s[m]['work_span_min'],2), reported=fmt(runtime[m]['self_reported_wall_minutes'],2)) for m in models]
    data['selected-turns'] = [dict(start_sort=t['start_jst'], model=f"{t['model'].title()} T{t['turn_number']}", start=t['start_jst'][11:19], end=t['end_jst'][11:19], minutes=fmt(t['minutes'],2), api=int(t['api_responses']), tokens=integer(t['total_tokens'])) for t in selected]
    data['token-composition'] = [dict(model=m.title(), part=label, tokens=int(runtime[m][key]), work_total=s[m]['total_tokens'], session_total=s[m]['session_total_tokens']) for m in sorted(models,key=lambda m:s[m]['total_tokens']) for label,key in [('入力（キャッシュ含む）','input_total'),('出力（推論含む）','output_total')]]
    for row,key in zip(data['input-token-detail'], ['uncached_input','cache_read_input','cache_creation_input','output_total','total_tokens','excache'], strict=True):
        for m in models:
            row[m.title()] = integer(excache[m] if key == 'excache' else runtime[m][key])
    data['output-composition'] = [dict(model=m.title(), part=label, tokens=int(runtime[m][key]), output_total=int(runtime[m]['output_total']), api_responses=int(runtime[m]['work_api_responses'])) for m in sorted(models,key=lambda m:int(runtime[m]['output_total'])) for label,key in [('通常出力','output_nonreasoning'),('推論出力','output_reasoning')]]
    for m in models:
        r = runtime[m]
        vals = [integer(r['work_api_responses']), integer(r['output_nonreasoning']), integer(r['output_reasoning']), f"{int(r['output_reasoning'])/int(r['output_total']):.1%}", fmt(int(r['output_total'])/int(r['work_api_responses']),0), f"{int(r['cache_read_input'])/int(r['input_total']):.1%}"]
        for row, value in zip(data['work-patterns'], vals, strict=True): row[m.title()] = value
    data['sessions'] = [dict(model=m.title(), session=runtime[m]['session_name'], turns=sum(t['model']==m for t in turns), selected=runtime[m]['work_turns'], total=integer(s[m]['session_total_tokens']), excluded=integer(s[m]['session_total_tokens']-s[m]['total_tokens'])) for m in models]
    data['test-results'] = [dict(model=m.title(), pytest=s[m]['verified_tests_passed'], pytest_fail=s[m]['verified_tests_failed'], checks=f"{s[m]['hidden_checks_passed']} / 41", fails=s[m]['hidden_checks_failed'], valid='10 / 10') for m in models]

    # Preserve compact, transposed tables. Seven model columns would recreate a
    # known reader overflow, so use adjacent old-four / added-three panels.
    for t in list(manifest['tables']):
        if t['id'] in ['category-scores','accuracy-detail','scenario-forward','input-token-detail','work-patterns']:
            added = copy.deepcopy(t)
            added['id'] += '-added'
            added['title'] += ' — 追加3モデル'
            retained = [c for c in t['columns'] if c['field'] not in [m.title() for m in OLD]]
            model_columns = [dict(field=m.title(),label=m.title(),type='text') for m in NEW]
            added['columns'] = [c for c in retained if c['field'] != 'lowest'] + model_columns
            if any(c['field']=='lowest' for c in retained): added['columns'] += [dict(field='lowest',label='7モデル中の最小',type='text')]
            t['title'] += ' — 既存4モデル'
            t['subtitle'] = '行は指標、列はモデル。追加3モデルは直後の同一定義の表で比較。' if t['id']!='scenario-forward' else '単位bp、小さいほど良い。「最小」は7モデル全体で判定。'
            added['subtitle'] = '直前の既存4モデルと同じ指標・単位・採点条件。'
            if any(c['field']=='lowest' for c in t['columns']):
                next(c for c in t['columns'] if c['field']=='lowest')['label']='7モデル中の最小'
            manifest['tables'].insert(manifest['tables'].index(t)+1, added)
            old_block = next(b for b in manifest['blocks'] if b['id'] == t['id']+'-block')
            new_block = copy.deepcopy(old_block)
            new_block['id'] += '-added'
            # Native table block uses tableId, preserve all other properties.
            new_block['tableId'] = added['id']
            manifest['blocks'].insert(manifest['blocks'].index(old_block)+1, new_block)
    table = next(t for t in manifest['tables'] if t['id']=='score-gaps')
    table['columns'] += [dict(field='vs_'+m,label='Fable − '+m.title()+'（点）',type='text') for m in ['terra','luna']]
    table = next(t for t in manifest['tables'] if t['id']=='risk-detail')
    table['title'] = '非公開商品の価格誤差とDV01の照合'
    table['subtitle'] = '価格誤差は非公開商品の真値と比較し、半スプレッド（下限付き）で正規化。公開クォートの再現誤差ではない。'
    next(c for c in table['columns'] if c['field']=='bidask')['label'] = '非公開価格誤差（半幅比）'
    next(c for c in manifest['charts'] if c['id']=='category-matrix')['encodings']['y']['fields']=[m.title() for m in models]
    update_narrative(manifest, models, s, runtime, d, scenario_wins, excache, turns)
    for src in manifest['sources']:
        src['path'] = src['path'].replace('analysis/final-review-20260905/matched/', SNAP+'/')
        query = src['query']
        query['executed_at'] = stamp
        query['filters'] = ['2026年9月5日に完了した7モデル各1実行。提出物の自動再採点と選択した本実行ターンを比較。']
        query['tables_used'] = [p.replace('analysis/final-review-20260905/matched/', SNAP+'/').replace('evaluations/performance-report/build_report.py','evaluations/performance-report/update_report_seven.py') for p in query['tables_used']]
        query['tables_used'] += [f'{SNAP}/{m}_score.json' for m in NEW] if src['id'] in ['scores','precision','qa'] else []
        query['tables_used'] += ['analysis/final-review-20260905/expand_seven.py'] if src['id'] in ['usage','qa'] else []
        if src['id']=='precision':
            query['metric_definitions']=[v for v in query['metric_definitions'] if not v.startswith('公開クォート再現=')]
            query['metric_definitions'].append('非公開価格誤差=非公開holdout_instrumentsのtrue_quoteとの誤差 / max(|ask−bid|/2, 金利0.002または債券0.02) のRMSE。無次元。公開観測クォートの再現ではない。')
        if src['id']=='usage':
            query['metric_definitions']=[v.replace('Astra T4、Sol T2、Opus T1+T2、Fable T1。','Astra T4、Sol T2、Opus T1+T2、Fable T1、Terra T2、Luna T1、Sonnet T3。') for v in query['metric_definitions']]
            query['metric_definitions']=[v if not v.startswith('キャッシュ読取を除く=') else 'キャッシュ読取を除く=未キャッシュ入力+キャッシュ作成+出力総量。総トークンとは異なる処理量の尺度であり料金の代理ではない。' for v in query['metric_definitions']]
        if src['id']=='qa':
            query['description'] += ' 追加3モデルは同じ隔離環境で採点・全pytestを実行。既存4モデルは候補と採点器の完全なハッシュ一致を条件に検証済み値を継承。'
        if src['id']=='profiles':
            query['tables_used'] += ['output/luna/README.md','output/luna/outputs/diagnostics/model_comparison.json','output/sonnet/README.md','output/sonnet/outputs/diagnostics/model_comparison.json',f'{SNAP}/candidate_review.json']
            query['description'] += ' Terraの実体はベンチマーク外のDocuments/terra。移動せず読取確認し、対象ハッシュとレビュー抜粋を監査記録に保存。'

    repair_source_bindings(artifact)

    # Source and reading-order preservation checks are mandatory for this edit.
    old_ids = [b['id'] for b in original['manifest']['blocks']]
    new_ids = [b['id'] for b in manifest['blocks']]
    check([x for x in new_ids if x in old_ids] == old_ids, 'Original blocks and reading order retained')
    for kind in ['charts','tables','cards','sources']:
        check({x['id'] for x in original['manifest'][kind]} <= {x['id'] for x in manifest[kind]}, 'All original '+kind+' preserved')
    for name, old_rows in original['snapshot']['datasets'].items():
        check(name in data and set(old_rows[0]) <= set(data[name][0]), name+': dataset fields retained')
    for t in manifest['tables']:
        check(len(t['columns']) <= 6, t['id']+': no wide table regression')
        check(t['defaultSort']['field'] in [c['field'] for c in t['columns']], t['id']+': explicit sort column')
    check(len(data)<=50 and all(len(rows)<=2000 for rows in data.values()), 'Bounded data snapshot')
    serialized=json.dumps(artifact,ensure_ascii=False,allow_nan=False)
    check(len(serialized.encode())<3_000_000 and '/Users/' not in serialized and '../' not in serialized, 'Portable bounded payload without private paths')
    check(digest(HERE/'artifact.json') == current_hash, 'Current report has not changed while preparing update')
    backup = HERE/'versions'/'four-models-before-seven'
    backup.mkdir(parents=True,exist_ok=True)
    for path in [HERE/'artifact.json', HERE/'DESIGN.md', HERE/'validation.json', HERE/'delivery-receipt.json', BASE/'evaluations/performance_report.html', BASE/'evaluations/combined_summary.json', BASE/'evaluations/combined_summary.csv', BASE/'evaluations/methodology.json', BASE/'evaluations/README.md']:
        if path.exists() and not (backup/path.name).exists(): shutil.copy2(path,backup/path.name)
    save(HERE/'artifact.json',artifact)
    for name in ['combined_summary.json','combined_summary.csv']:
        shutil.copy2(BASE/SNAP/name,BASE/'evaluations'/name)
    for m in NEW: shutil.copy2(BASE/SNAP/f'{m}_score.json',BASE/'evaluations'/f'{m}.json')
    method=read('evaluations/methodology.json')
    method.update(generated_utc=stamp,audit=SNAP+'/evaluation_audit.json',usage_audit=SNAP+'/usage_audit.json',test_verification=SNAP+'/pytest_verification.json',expanded_models=models,verification_reuse=audit['reused_evaluations'])
    method['caveats'] += ['Terra is evaluated in its actual Documents/terra directory, without moving it.','Added selected work turns: Terra T2, Luna T1, Sonnet T3.','All seven logs were freshly recovered. Old-four scores/pytest were reused only on exact candidate/evaluator hash match.','The bid/ask-normalized pricing metric compares hidden true_quote, not public observed quotes.']
    save(BASE/'evaluations/methodology.json',method)
    update_readme(summary)
    make_notebook(summary)
    save(HERE/'validation.json',dict(status='passed_with_caveats',generated_at=stamp,checks_passed=len(CHECKS),checks=CHECKS,input_sha256=INPUTS,artifact_sha256=digest(HERE/'artifact.json'),query_rows={k:len(v) for k,v in sql_rows.items()},scenario_zero_wins=scenario_wins,original_blocks_preserved=True,charts=len(manifest['charts']),tables=len(manifest['tables']),notebook_execution='All code cells executed sequentially in a fresh Python namespace; standard library only.'))
    print(json.dumps(dict(models=[dict(model=m,score=s[m]['score'],minutes=s[m]['work_time_min'],tokens=s[m]['total_tokens']) for m in models],checks=len(CHECKS),wins=scenario_wins,pytest=sum(s[m]['verified_tests_passed'] for m in models),charts=len(manifest['charts']),tables=len(manifest['tables'])),ensure_ascii=False))


def update_readme(summary):
    path=BASE/'evaluations/README.md'
    text=path.read_text(encoding='utf-8')
    table='\n'.join(f"| {r['rank']} | {r['model'].title()} | {r['score']:.3f} | {r['work_time_min']:.1f} | {r['total_tokens']:,} | {r['verified_tests_passed']}件合格 |" for r in summary)
    text=re.sub(r'(\| 1 \| Fable.*?)(?=\n\n)',table,text,count=1,flags=re.S)
    rows='\n'.join('| '+r['model'].title()+' | '+' | '.join(fmt(r[c[0]]) for c in CATS)+' |' for r in summary)
    text=re.sub(r'(\| Fable \| 29\.384.*?)(?=\n\n)',rows,text,count=1,flags=re.S)
    text=text.replace('![最終実行時間](execution_time_final.png)','[7モデルの実行時間グラフ・トークン内訳・スコア詳細](performance_report.html)\n\n旧 `execution_time_final.png` は4モデル時点の図として保持し、最新値には使用しません。')
    text=text.replace('## 時間・トークンの範囲','## 7モデルへの追加更新\n\nTerraは `Documents/terra`（ベンチマーク外）、Luna・Sonnetは `output/` から評価。提出物は移動・変更していません。追加3モデルは同一の採点器・隔離環境で新たに採点と全pytestを実行。既存4モデルは候補・採点器のハッシュ一致を確認し、検証済み値を継承しました。全7セッションの使用量を再読込し、Terra T2・Luna T1・Sonnet T3を本実行に追加しました。\n\n最新監査は `analysis/final-review-20260905/expanded-7-models/`（ベンチマークルートからの相対位置）。以下の4モデル固有の経緯・留保は過去確認として保持します。\n\n## 時間・トークンの範囲')
    text += '\n\n補足訂正：HTMLの旧「公開クォート再現」は、採点器を再確認した結果、非公開商品の真値との誤差を半スプレッド（下限付き）で正規化した指標でした。数値は保持し、名称と解釈を訂正しました。最新の全件数と追加3モデルの形式依存減点はHTMLを参照してください。\n'
    path.write_text(text,encoding='utf-8')


def repair_source_bindings(artifact):
    # The time narrative now includes score comparisons, so do not imply that
    # its block-wide source is solely the usage reduction.
    next(b for b in artifact['manifest']['blocks'] if b['id']=='time').pop('sourceId',None)
    supplements={
        'precision':[SNAP+'/candidate_review.json'],
        'qa':[SNAP+'/usage_audit.json'],
        'profiles':[SNAP+'/runtime_tokens.csv',SNAP+'/combined_summary.json'],
        'limits':[SNAP+'/candidate_review.json']+[SNAP+'/'+m+'_score.json' for m in NEW],
    }
    for source in artifact['manifest']['sources']:
        query=source['query']
        query['tables_used']=list(dict.fromkeys(query['tables_used']+supplements.get(source['id'],[])))
        for path in query['tables_used']:
            if not path.startswith('main.'):
                check((BASE/path).exists(),source['id']+': provenance file exists '+path)


def make_notebook(summary):
    # nbformat/nbclient are absent from bundled Python. A small v4.5 notebook
    # uses only stdlib; execute every code cell, capture outputs and validate
    # schema fields rather than installing dependencies into the user's env.
    cells=[]
    def md(text): cells.append(dict(cell_type='markdown',id=f'cell-{len(cells):02d}',metadata={},source=text.splitlines(True)))
    def code(text): cells.append(dict(cell_type='code',id=f'cell-{len(cells):02d}',metadata={},source=text.splitlines(True),execution_count=None,outputs=[]))
    md('## tl;dr\n\n7モデルを同一採点定義で比較。総合首位はFable、時間・総トークン最少はTerra。以下はHTMLの数値と元スナップショットを独立照合する監査ノート。')
    md('## Context & Methods\n\n2026年9月5日の各1実行。スコア・時間・トークンを混ぜず比較する。追加3モデルを新規採点し、既存4モデルは候補・採点器のハッシュ一致で前回値を継承。ログは全7件を再集計。\n\n### Key Assumptions\n\n本実行はAstra T4、Sol T2、Opus T1+T2、Fable T1、Terra T2、Luna T1、Sonnet T3。待機・準備・終了後依頼は除外。推論は出力の内数。料金は未測定。単一実行のため一般的能力順位ではない。')
    md('## Data\n\n### 1. 監査済みスナップショットを読む\n\nベンチマークルートまたはこのノートのディレクトリから実行する。元のJSONLはプライベート監査で参照し、このノートには会話本文・推論本文を含めない。')
    code("import csv, json, math, sqlite3\nfrom pathlib import Path\nroot = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / 'evaluator/scoring.py').exists())\nsnap = root / 'analysis/final-review-20260905/expanded-7-models'\nsummary = json.loads((snap / 'combined_summary.json').read_text())\nturns = list(csv.DictReader((snap / 'user_turns.csv').open(encoding='utf-8-sig')))\nscores = {r['model']: json.loads((snap / (r['model'] + '_score.json')).read_text()) for r in summary}\nprint(f'{len(summary)} models; {len(turns)} user turns; {sum(t[\"selected_work_turn\"] == \"True\" for t in turns)} work turns')\n")
    md('### 2. トークン・時間・点数・保全を照合する')
    code("for r in summary:\n    work = [t for t in turns if t['model'] == r['model'] and t['selected_work_turn'] == 'True']\n    assert sum(int(t['total_tokens']) for t in work) == r['total_tokens']\n    assert math.isclose(sum(float(t['minutes']) for t in work), r['work_time_min'])\n    assert r['input_tokens'] + r['output_tokens'] == r['total_tokens']\n    assert math.isclose(sum(scores[r['model']]['category_scores'].values()), r['score'], abs_tol=.002)\n    assert r['pytest_exit_code'] == 0\naudit = json.loads((snap / 'evaluation_audit.json').read_text())\nassert audit['original_candidates_unchanged'] and audit['completed_utc']\nprint('Token, time, category, pytest and immutable-snapshot checks: PASS')\n")
    md('## Results\n\n### 3. 元データからHTMLのソースSQLを再実行する\n\nSQL全文は同梱の `report_queries.sql` およびartifact内の出典に保存。')
    code("artifact = json.loads((root / 'evaluations/performance-report/artifact.json').read_text())\ndb = sqlite3.connect(':memory:')\ndb.row_factory = sqlite3.Row\ndb.execute('CREATE TABLE raw_evaluations (model TEXT, document TEXT)')\ndb.executemany('INSERT INTO raw_evaluations VALUES (?, ?)', [(m, json.dumps(d)) for m, d in scores.items()])\nsource = next(s for s in artifact['manifest']['sources'] if s['id'] == 'scores')\nrows = list(db.execute(source['query']['sql']))\nassert len(rows) == 49\nfor x in rows:\n    assert math.isclose(x['category_score'], scores[x['model']]['category_scores'][x['category']])\nprint('49 category cells independently reconciled by SQL')\n")
    md('### 4. 7モデル比較（点 / 分 / 処理トークン）')
    code("for r in summary:\n    print(f\"{r['model']:7s} {r['score']:7.3f} / {r['work_time_min']:7.2f} min / {r['total_tokens']:12,} tokens\")\nprint('Candidate-written pytest passes:', sum(r['verified_tests_passed'] for r in summary))\n")
    md('## Takeaways\n\n追加モデルで比較対象と用途別候補が変わる。Lunaは91.021点でAstra・Solを上回り、Terraは18.30分・3,701,783トークン。本実行と全セッション、キャッシュ読取とそれ以外を区別する。採点の形式依存・価格付け規約の留保はHTMLに保持した。\n\n検証：標準ライブラリによる全コードセルの順次実行済み。nbformat/nbclientが環境にないためJupyterカーネル実行は使用していない。通常のNotebook v4.5形式として保存し、セル構造と実行結果を検査した。')
    namespace={}
    previous=Path.cwd()
    import os
    os.chdir(BASE)
    try:
        count=0
        for cell in cells:
            check(cell['cell_type'] in ['code','markdown'] and isinstance(cell['source'],list), 'Notebook cell schema '+cell['id'])
            if cell['cell_type']!='code':continue
            count+=1
            capture=io.StringIO()
            with contextlib.redirect_stdout(capture): exec(compile(''.join(cell['source']),cell['id'],'exec'),namespace)
            cell['execution_count']=count
            cell['outputs']=[dict(output_type='stream',name='stdout',text=capture.getvalue().splitlines(True))]
        check(count==4,'Notebook all four code cells executed')
    finally: os.chdir(previous)
    save(HERE/'seven_model_audit.ipynb',dict(nbformat=4,nbformat_minor=5,metadata=dict(kernelspec=dict(display_name='Python 3',language='python',name='python3'),language_info=dict(name='python',version=sys.version.split()[0])),cells=cells))


def update_narrative(manifest, models, s, runtime, d, wins, excache, turns):
    blocks={b['id']:b for b in manifest['blocks']}
    def put(key,text): blocks[key]['body']=text
    def replace(key,old,new):
        check(old in blocks[key]['body'], 'Expected prior narrative in '+key)
        blocks[key]['body']=blocks[key]['body'].replace(old,new)
    total_tests=sum(s[m]['verified_tests_passed'] for m in models)
    check(total_tests==403,'403 candidate-written pytest passes across seven models')
    check(wins['fable']==9 and wins['opus']==1, 'Stress-error leadership unchanged after expansion')
    core={m:sum(s[m][k] for k in ['numerical','model_quality','robustness']) for m in models}
    put('title', '# '+manifest['title']+'\n\n量的リサーチ・ベンチマーク最終レポート · 2026年9月5日更新 · 時刻は日本標準時（JST）\n\n対象：Astra / Sol / Opus / Fable / Terra / Luna / Sonnet。各1回の完了済み提出物を同じ採点定義で比較。時間は本実行ターンの壁時計、トークンはキャッシュを含む処理量。')
    put('executive-summary', f'''## Executive Summary

- **Fableが94.473点で首位、Opusが93.431点、追加されたLunaが91.021点で続く。** Terraは82.835点、Sonnetは75.050点。GPT側でもLunaはAstra・Solを10点以上上回り、モデルファミリー単位の優劣という結論にはできない。
- **最短・最少処理量はTerra。精度とのバランスではLunaも有力。** Terraは18.3分・3.70Mトークン、Lunaは33.0分・11.23M、Sonnetは63.0分・39.17M。Fableは55.9分・10.79M、Opusは124.2分・59.40M。時間・トークンは採点には混ぜていない。
- **全7モデルが10/10の隠しシナリオを完走し、自作pytestは計{total_tests}件合格。ただし精度は異なる。** Fableは隠しゼロ金利RMSEで9/10最小、Opusは主データで最小。Lunaの主データRMSEは2.649bp、Sonnetは6.859bpで、とくに短期20.906bp・フォワード70.857bpが課題だった。
- **単一実行と採点上の留保を維持する。** キャッシュ読取を除くとTerra 0.154M、Luna 0.338M、Sonnet 0.662Mで、処理総量や料金とは別の尺度。主カーブ誤差の重複配点、JSONキー、言語判定、支払規約の影響があり、普遍的な能力順位や原因別の寄与は未確定。''')
    put('overall', '''## 1. Fable・Opusが上位を維持、Lunaが3位に加わる

生の自動採点はFable 94.473、Opus 93.431、Luna 91.021、Terra 82.835、Sol 80.438、Astra 80.103、Sonnet 75.050点。FableとOpusの差は1.042点、OpusとLunaの差は2.410点。形式依存の減点もあるため、微差から安定した順位までは判断できない。

採点は100点満点の7カテゴリ。時間・トークンは得点に混ぜず別軸で示す。リスク表の任意列の衝突を避ける互換処理だけを適用し、計算式・配点・閾値は変更していない。誤検知を手作業で加点補正した値ではない。カテゴリ達成率は満点を分母にした比率で、濃いほど高いが、総合点への寄与は配点で異なる。''')
    oldgap=blocks['gap']['body']
    oldgap=oldgap.replace('## 2. GPT側の差は、完遂よりも数値・モデル品質に集中','## 2. Lunaの追加で、GPT側を一括りにはできなくなった')
    oldgap=oldgap.replace('全モデルの完遂点は5/5。','LunaはSolより10.583点、Astraより10.918点高い。完遂点はTerraのみ4/5（サマリーのキー不足）、他6モデルは5/5で、Terraも本実行と10シナリオは完了している。')
    oldgap += f"\n\n追加組では、Fableとの中核3カテゴリ（65点）の差はLuna {core['fable']-core['luna']:.3f}点、Terra {core['fable']-core['terra']:.3f}点、Sonnet {core['fable']-core['sonnet']:.3f}点。Lunaは主カーブ精度を改善し、Sonnetは同じClaude系の上位2モデルから大きく離れた。ファミリー名より、今回の実装・検証設計ごとに比較する必要がある。"
    put('gap',oldgap)
    put('precision', '''## 3. Lunaは主カーブ精度を改善。Sonnetは短期・フォワードが課題

主データのゼロ金利RMSEはOpus 1.112bp、Fable 1.150bp、Luna 2.649bp。Astra 5.021bp、Sol 5.587bp、Terra 5.655bp、Sonnet 6.859bpと続く。小さいほど正解カーブに近く、1bpは0.01パーセントポイント。LunaはAstra・Solより改善したが、Opus・Fableと同水準ではない。

年限別では、Solの2年以下20.223bp、Astraの15年以上6.202bpという既存の特徴が残る。Terraは長期7.399bp、Sonnetは短期20.906bp。フォワードRMSEはOpus 12.713bp・Fable 14.679bpに対しLuna 29.277bp・Terra 29.600bp、Sonnet 70.857bpだった。どの年限・指標を重視するかで選択は変わる。''')
    put('risk-readout', '''### DV01は全7モデルで合格。価格誤差とは別に読む

DV01有限差分とキーレート合計の整合性チェックは全モデルが合格した。ただし照合商品数は119〜136件と異なるため、相対誤差だけでリスク計算の優劣を順位付けしない。

非公開商品の価格誤差チェック（正規化RMSE < 3）はOpus・Fable・Lunaが合格、Astra・Sol・Terra・Sonnetが不合格。Lunaは2.922で閾値に近い。別の半スプレッド正規化指標は、Fable 5.141、Opus 5.427、Luna 8.928、Terra 17.058、Astra 17.708、Sol 63.615、Sonnet 67.252だった。

**指標名を訂正した。** 旧版の「公開クォート再現」は、実際には非公開商品の真値との誤差を半スプレッド（下限付き）で割ったRMSE。元の数値は変更していない。この値から「公開入力を再現できていない」とは結論できない。Sonnetでは別途、出力フォワードと割引係数の離散微分との照合も不合格だった。区分線形カーブの微分方式の違いが影響し得るため、数理的な誤実装と即断しない。''')
    blocks['scenarios']['body'] += '\n\n追加組のゼロRMSEは、Lunaが10条件で1.896〜3.330bpと比較的狭い範囲、Terraはs08で10.815bp、Sonnetはs04で10.795bpまで増えた。追加後もFableの9/10、Opusの1/10という最小誤差の分担は変わらない。図の濃色は誤差の大きさであり、前の達成率図とは良否の向きが逆。'
    put('time', '''## 5. 最短はTerra、Lunaも33分。Opusの再開待ちは分離

作業ターンの合計はTerra 18.3分、Luna 33.0分、Sol 34.6分、Astra 52.0分、Fable 55.9分、Sonnet 63.0分、Opus 124.2分。今回、TerraはSolより約47%短い時間で高い得点、LunaはFableより約41%短い時間で91.021点だった。ただし精度の水準は同じではなく、計算機の競合・ツール待ち・自動要約を含むため、純粋なモデル推論速度でもない。

Opusは途中で止まった後に再開している。69.8818分＋54.3365分が作業合計で、再開待ち78.3329分を含む開始から終了までは202.5513分。以前の69.9分という値は途中時点であり、最終値を使用する。FableはOpusより作業時間が55.0%短く、総合点も高かったという今回の観測は変わらない。''')
    cache_shares=[int(runtime[m]['cache_read_input'])/s[m]['total_tokens'] for m in models]
    put('tokens', f'''## 6. Terraが最少処理量。総量の大半はキャッシュ読取

本実行の総量はTerra 3.70M、Astra 3.80M、Sol 8.98M、Fable 10.79M、Luna 11.23M、Sonnet 39.17M、Opus 59.40M。各モデルの総量の約{min(cache_shares):.0%}〜{max(cache_shares):.0%}はキャッシュ読取で、これを除くとTerra 153,751、Astra 215,612、Sol 229,299、Luna 338,288、Sonnet 661,554、Fable 1,051,441、Opus 1,285,431トークンとなる。

OpusはFableの総量の約5.50倍だが、キャッシュ読取を除く量では1.22倍。Sonnetも総量はFableの3.63倍ながら、読取を除く量は約0.63倍に逆転する。どちらも「生成した文章量」「消費料金」や「推論の深さ」とは読み替えられない。モデルファミリーごとの一律な倍率は示さない。

通常入力・キャッシュ読み込み・キャッシュ作成・通常出力・推論出力を排他的に足す。推論を出力総量へもう一度加えることはしない。API事業者間でトークナイザやキャッシュ計測が異なり、課金額・エネルギー・割当消費率は未測定。図は入力と出力の構成、下表はキャッシュを分けた正確な値を示す。''')
    blocks['output']['body'] += '\n\n追加組はTerraが48回・47.5k出力、Lunaが83回・76.8k、Sonnetが139回・281.6k。SonnetはFableに近い出力総量でも約3.4倍のAPI応答に分かれ、推論出力の比率は60.3%。この観測が多い検討や良い検証を意味するとは限らず、今回の得点差とも単純な比例関係はない。'
    blocks['scope-note']['body'] += '\n\n追加組ではTerra T2、Luna T1、Sonnet T3を採用。TerraのT1（指示・出力先確認）とT3（終了後の出力先に関する依頼）は除外した。Terraの実体は `Documents/terra`（ベンチマーク外）で、採点のための移動はしていない。Sonnet T1/T2にはAPI応答も終了マーカーもなく、時間は未測定（ゼロではない）。両ターンの記録済みトークンは0で、採用したT3の量と全セッション量は一致する。全セッション値は回復時点のスナップショットで、後続会話が増えれば変わる。'
    replace('profile-astra','キャッシュを含む処理総量は今回最少だった。','キャッシュを含む処理総量は既存4モデルでは最少で、7モデルではTerraに次いで少ない。')
    replace('profile-sol','### Sol — 最短でソフトウェア満点、短期カーブの選択が再検証点','### Sol — ソフトウェア満点、短期カーブの選択が再検証点')
    profiles={
        'terra':'''### Terra — 最短・最少処理量だが、長期精度と形式チェックに課題

線形log-DF基準モデルと自然3次log-DFスプラインを比較。スプレッド・流動性の重み、Huber反復、年限バケットを丸ごと抜く検証で高度モデルを選択した。18.3分・3.70Mトークンで82.835点は、今回の時間制約下の候補になるが、長期ゼロRMSE7.399bp・非公開商品RMSE6.321は精度面の留保。

完遂4/5は未完走ではなく、サマリーに採点器が求める `failed_test_runs` がないことによる。実際には `failed_test_suite_runs` を記録している。感度JSONは2つのトップレベルキーしかなく形式判定が不合格。単位処理・bid/ask反転のチェックも不合格で、形式と処理判断を切り分けて見直す必要がある。''',
        'luna':'''### Luna — 33分で91点。改善の余地はフォワードと提出形式

堅牢なdeposit/OISブートストラップを基準とし、連続複利ゼロ金利の区分線形グリッドに曲率ペナルティと4回のロバスト反復を加えた高度モデルを採用した。年限群をまとめてホールドアウトし、「高度モデルの誤差が基準の5%増以内」という許容条件も使う。これは最小誤差だけで選ぶ規則とは異なるため、モデル選択方針の感度を調べる余地がある。

ゼロRMSE2.649bp、非公開商品RMSE2.922で、Astra・Solより高精度。ただしフォワードRMSE29.277bpはOpus・Fableより大きい。`model_selected` と `selected_model` のキー不一致、レポートの8/9概念認識で失点している。これらは数値誤差とは別の修正候補で、今回は点数を補正していない。''',
        'sonnet':'''### Sonnet — 基準モデルを選択。短期精度と検証対象の偏りを再点検

商品種別ごとに残差スケールを調整した区分線形ゼロ金利モデルと、累積log-DFの自然3次スプライン＋曲率ペナルティ＋Tukey反復を比較。内部ホールドアウトは基準2.1026、高度2.2159のため基準モデルを採用した。しかし非公開評価では短期ゼロRMSE20.906bp、フォワード70.857bpで、75.050点だった。

検証分割ではdepositをすべて学習に残し、OISのホールドアウト候補を局所的な滑らかさで選別する。難しい年限を検証から外す選択が未見条件への代表性を弱めた可能性はあるが、原因寄与は未測定。基準モデルの解析的フォワードと採点器の離散微分との照合差もあり、共通の微分規約で確認する必要がある。

自作49テストは合格し、ソフトウェア15/15、完遂5/5。低得点は未完遂とは異なる。追加の提出済みカーブを直接採点しても主要誤差は隔離再実行と一致しており、今回の低精度を単に再採点環境のせいとは説明できない。'''}
    anchor=blocks['profile-fable']
    for m in NEW:
        new=dict(id='profile-'+m,type='markdown',body=profiles[m],layout='full')
        manifest['blocks'].insert(manifest['blocks'].index(anchor)+1,new)
        anchor=new
    put('model-metadata-notes','### 実行モデルと自己申告の修正回数\n\nモデルID・推論設定はログの記録値。修正回数は自己申告で、共通定義の測定ではない。\n\n'+'\n'.join(f"- {m.title()} · `{runtime[m]['model_id']}` · {runtime[m]['reasoning_effort']} · 修正{ s[m]['corrective_iterations']}回（自己申告） · 提出先：{s[m]['candidate_path']}" for m in models))
    put('test-heading', '''## 8. 全7モデルの自作pytestは合格。件数は性能点ではない

全pytestの検証結果はAstra45、Sol20、Opus204、Fable60、Terra13、Luna12、Sonnet49件、合計403件が合格。追加3モデルは今回、既存4モデルと同じ数値ライブラリの隔離コピーで再実行した。既存4モデルは候補・採点器のハッシュが前回と完全一致したため、その検証済み結果を継承している。候補が自分で書いた異なるテスト群であり、件数が多いほど未見データに強いとは限らない。

元の採点器のunittest探索ではAstra・Sol・Fableは各7件のみが対象だった。下表は全pytestと41件の採点チェックを分離している。SolとLunaは採点チェック38/41で最多だが、チェックの件数と連続値の数値得点は同じ尺度ではない。''')
    blocks['integrity']['body'] += '\n\n今回の追加採点はTerra・Luna・Sonnetの3件、ハッシュ一致で継承した既存採点は4件。全7ログの使用量は新規に再読込した。Sonnetでは312個のusage付きブロックを139個のAPI応答に一意化し、重複173個を除外。Codexは累積値と応答単位値を照合し、Terraで記録されたカウンタのリセットも回復処理で扱った。追加3モデルも候補・公開入力・評価側の採点前後の保全検査を通過している。'
    replace('rubric','4モデルが同一の理由で落とした欠損クォートのチェック（各1.0点）','既存4モデルに加えてLuna・Sonnetも落とした欠損クォートのチェック（各1.0点、Terraは合格）')
    replace('rubric-limitations-notes','対象：全モデル · 確認した事実：採点器は欠損クォート4件','対象：既存4モデル＋Luna・Sonnet（Terraは合格） · 確認した事実：採点器は欠損クォート4件')
    replace('rubric-limitations-notes','4モデルとも二者間bid/askの中値で復元して採用（correct/downweight）し、全員が0/4で不合格、データ品質から各1.0点減。','既存4モデルはbid/ask中値で復元して採用し0/4で不合格だった。追加後もLuna・Sonnetは0/4、Terraは除外処理で4/4合格。')
    replace('rubric-limitations-notes','4モデル同一の失点は実装の弱点ではなく採点規則の選択。中値復元は妥当な処理であり、次回は仕様で扱いを固定する。','既存4モデルの共通失点は中値復元か除外かという規則の選択を反映する。中値復元にも除外にも前提があるため、一律の実装ミスと断定せず次回は仕様で固定する。')
    replace('rubric-limitations-notes','対象：Astra / Opus · 確認した事実：model_selected','対象：Astra / Opus / Luna / Sonnet · 確認した事実：model_selected')
    replace('rubric-limitations-notes','対象：Fable · 確認した事実：checksリストに結果があるが','対象：Fable / Terra · 確認した事実：checksリストに結果があるが')
    blocks['rubric-limitations-notes']['body'] += '\n- 優先：10 · 論点：追加モデルの提出形式 · 対象：Terra / Luna · 確認した事実：Terraはfailed_test_suite_runsを記録するがfailed_test_runsがなく完遂点を1点失う。Lunaは章の英語キーワード8/9で4.556/5。 · 解釈への影響：タスク未完了・内容不足と形式適合を区別する。\n- 優先：11 · 論点：静的スキャンの対象パス · 対象：採点器 · 確認した事実：他結果参照の検索対象名がAstra・Sol・Opus・Fableの4つに固定されている。 · 解釈への影響：追加3モデルの警告ゼロを完全なアクセス隔離の証明にしない。今回の点数は元の判定を維持。\n- 優先：12 · 論点：フォワードの微分規約 · 対象：Sonnet · 確認した事実：区分線形ゼロから解析的に出力したforwardと、採点器の格子上の離散微分のRMSEが0.00237。 · 解釈への影響：整合性チェック不合格を、真値とのフォワードRMSE70.857bpとは分けて読む。'
    blocks['schedules']['body'] += '\n\n追加3モデルも同じ未修正の採点規約で評価した。この更新では7実装を共通規約へ書き換える対照実験は行っていない。とくにSonnetのフォワード微分方式・ホールドアウト候補の選別は、支払規約と別々に検証すべき論点である。'
    text=blocks['next-steps']['body']
    text=text.replace('両者の検証分割を1要因ずつ比較する。','両者の検証分割を1要因ずつ比較する。追加組ではSonnetの微分規約と検証対象の選別、Terraの長期誤差、Lunaのモデル選択許容幅を別々に検証する。')
    text=text.replace('時間制約ではSol、処理量制約ではAstraを候補として残し','時間・処理量制約ではTerra、90点台と33分の両立ではLunaを追加候補とし')
    text=text.replace('処理量はキャッシュ読取を除いた値で比較し','処理量は総量とキャッシュ読取を除いた値を両方比較し')
    put('next-steps',text)
    replace('caveats','対象4モデル','対象7モデル')


if __name__ == '__main__':
    main()
