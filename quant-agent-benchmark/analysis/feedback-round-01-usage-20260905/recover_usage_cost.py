#!/usr/bin/env python3
"""Read-only, metadata-only recovery of benchmark initial and feedback usage.

Print JSON; never mutate candidates, source logs, or previous evaluations.
Use --snapshot result.json to reproduce the exact saved log prefixes.
"""
import argparse
import collections
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / 'analysis/final-review-20260905/expanded-7-models'
MODELS = ['astra', 'sol', 'terra', 'luna', 'sonnet', 'opus', 'fable']
INITIAL = {'astra': [4], 'sol': [2], 'terra': [2], 'luna': [1],
           'sonnet': [3], 'opus': [1, 2], 'fable': [1]}
# Claude interruption markers are NOT treated as new user turns.
PREP = {'astra': [6], 'sol': [7], 'terra': [4], 'luna': [2],
        'sonnet': [], 'opus': [3], 'fable': []}
MAIN = {'astra': [7], 'sol': [8], 'terra': [5], 'luna': [3],
        'sonnet': [4], 'opus': [4], 'fable': [2]}
# USD per million tokens: uncached / cache-read / 5m-write / 1h-write / output.
RATES = {'gpt-6-astra': [10, 1, 12.5, 12.5, 50],
         'gpt-5.6-sol': [4, .4, 5, 5, 20],
         'gpt-5.6-terra': [2, .2, 2.5, 2.5, 12],
         'gpt-5.6-luna': [.2, .02, .25, .25, 1.2],
         'claude-sonnet-5': [2, .2, 2.5, 4, 10],
         'claude-opus-5': [5, .5, 6.25, 10, 25],
         'claude-fable-5-1': [10, .25, 12.5, 20, 50]}
FIELDS = ['uncached_input', 'cache_read_input', 'cache_write_5m',
          'cache_write_1h', 'input_total', 'output_total', 'total_tokens']


def dt(s):
    return datetime.fromisoformat(s.replace('Z', '+00:00'))


def total(rows):
    rows = list(rows)
    return {k: sum(r[k] for r in rows) for k in FIELDS}


def normalize(u, codex):
    read = int(u.get('cached_input_tokens' if codex else 'cache_read_input_tokens') or 0)
    write = int(u.get('cache_write_input_tokens' if codex else 'cache_creation_input_tokens') or 0)
    inp = int(u.get('input_tokens') or 0)
    uncached = inp - read - write if codex else inp
    cache = u.get('cache_creation') or {}
    one_hour = int(cache.get('ephemeral_1h_input_tokens') or 0)
    five_min = write - one_hour
    if not codex:
        assert 'ephemeral_5m_input_tokens' in cache or write == 0, u
        assert five_min == int(cache.get('ephemeral_5m_input_tokens') or 0)
    output = int(u.get('output_tokens') or 0)
    reasoning = u.get('reasoning_output_tokens') if codex else (u.get('output_tokens_details') or {}).get('thinking_tokens')
    result = dict(zip(FIELDS, [uncached, read, five_min, one_hour,
                               uncached + read + write, output,
                               uncached + read + write + output]))
    assert all(v >= 0 for v in result.values())
    assert reasoning is None or 0 <= reasoning <= output
    if codex:
        assert result['total_tokens'] == u['total_tokens']
    return result, reasoning


def price(row):
    rates = RATES[row['model_id']]
    long = row['model_id'].startswith('gpt-') and row['input_total'] > 272000
    input_multiplier, output_multiplier = (2, 1.5) if long else (1, 1)
    fields = ['uncached_input', 'cache_read_input', 'cache_write_5m', 'cache_write_1h']
    cost = sum(row[k] * rate for k, rate in zip(fields, rates[:4])) * input_multiplier
    return (cost + row['output_total'] * rates[4] * output_multiplier) / 1e6


def human_text(d):
    if d.get('type') != 'user' or d.get('isMeta'):
        return None
    c = (d.get('message') or {}).get('content')
    if isinstance(c, list) and any(x.get('type') == 'tool_result' for x in c):
        return None
    text = c if isinstance(c, str) else ' '.join(x.get('text', '') for x in c or [] if x.get('type') == 'text')
    if not text.strip() or text.startswith(('<system-reminder>', '<command-name>', '<local-command', 'This session is being continued from a previous conversation')):
        return None
    return text


def parse(records, codex):
    turns, contexts, responses = {}, {}, {}
    current = None
    audit = collections.Counter()
    last_activity = None
    for line_no, d in enumerate(records, 1):
        ts, typ = d.get('timestamp'), d.get('type')
        p = d.get('payload') or {}
        if ts:
            last_activity = max(last_activity or ts, ts)
        if codex:
            if typ == 'event_msg' and p.get('type') == 'task_started':
                current = p['turn_id']
                turns[current] = dict(turn_number=len(turns) + 1, start_utc=ts, end_utc=None, status='running')
            elif typ == 'turn_context':
                contexts[p['turn_id']] = dict(model_id=p.get('model'), effort=p.get('effort'))
            elif typ == 'event_msg' and p.get('type') in ('task_complete', 'turn_aborted'):
                turns[p['turn_id']].update(end_utc=ts, status=p['type'])
            elif typ == 'token_usage_record':
                rid, tid = p['response_id'], p['turn_id']
                u, reasoning = normalize(p['usage'], True)
                row = dict(**u, reasoning_tokens=reasoning, turn_id=tid, response_id=rid,
                           timestamp_utc=ts, source_line=line_no, **contexts.get(tid, {}))
                if rid in responses:
                    assert {k: responses[rid][k] for k in FIELDS} == u
                    audit['duplicate_usage_records'] += 1
                    continue
                responses[rid] = row
                assert total(responses.values()) == normalize(p['thread_token_usage'], True)[0]
                assert total(x for x in responses.values() if x['turn_id'] == tid) == normalize(p['turn_token_usage'], True)[0]
                audit['verified_thread_and_turn_counter_steps'] += 1
        else:
            text = human_text(d)
            if text is not None:
                if text.startswith('[Request interrupted by user'):
                    assert current is not None
                    turns[current].update(end_utc=ts, status='turn_aborted')
                    audit['interruption_markers_not_counted_as_prompts'] += 1
                    continue
                current = d.get('promptId') or d['uuid']
                turns[current] = dict(turn_number=len(turns) + 1, start_utc=ts, end_utc=None, status='running')
            elif typ == 'assistant':
                msg = d.get('message') or {}
                if msg.get('model') == '<synthetic>':
                    continue
                rid, usage = msg['id'], msg['usage']
                u, reasoning = normalize(usage, False)
                if rid in responses:
                    prior = responses[rid]
                    assert {k: prior[k] for k in FIELDS} == u
                    assert prior['reasoning_tokens'] == reasoning
                    assert prior['request_id'] == d.get('requestId')
                    audit['duplicate_usage_records'] += 1
                    continue
                assert current is not None
                server = usage.get('server_tool_use') or {}
                assert not server.get('web_search_requests', 0), 'Server web-search fees need review'
                responses[rid] = dict(**u, reasoning_tokens=reasoning,
                    turn_id=current, response_id=rid, request_id=d.get('requestId'),
                    timestamp_utc=ts, source_line=line_no, model_id=msg['model'],
                    effort=d.get('effort'), service_tier=usage.get('service_tier'), speed=usage.get('speed'))
            elif typ == 'system' and d.get('subtype') == 'turn_duration' and current:
                turns[current].update(end_utc=ts, status='task_complete')
    if not codex:
        request_ids = [r['request_id'] for r in responses.values() if r['request_id']]
        assert len(request_ids) == len(set(request_ids))
        audit['request_ids_unique'] = True
        audit['missing_request_ids'] = sum(not r['request_id'] for r in responses.values())
    for r in responses.values():
        if codex and not r.get('model_id'):
            # Compaction can be logged before the resumed turn_context record.
            r.update(contexts[r['turn_id']])
        r['turn_number'] = turns[r['turn_id']]['turn_number']
        r['usd_standard'] = price(r)
    return turns, list(responses.values()), dict(audit), last_activity


def group(selected_turns, rows, asof):
    ids = {t['turn_number'] for t in selected_turns}
    rows = [r for r in rows if r['turn_number'] in ids]
    seconds = sum((dt(t['end_utc'] or asof) - dt(t['start_utc'])).total_seconds() for t in selected_turns)
    return dict(**total(rows), work_minutes=seconds / 60,
        usd_standard=sum(r['usd_standard'] for r in rows),
        usd_fast_scenario=sum(r['usd_standard'] * (2 if r['model_id'].startswith('gpt-') else 1) for r in rows),
        api_responses=len(rows), turn_numbers=sorted(ids),
        status='running' if any(t['status'] == 'running' for t in selected_turns) else 'complete',
        max_request_input_tokens=max((r['input_total'] for r in rows), default=0),
        long_context_requests=sum(r['model_id'].startswith('gpt-') and r['input_total'] > 272000 for r in rows),
        known_reasoning_tokens=sum(r['reasoning_tokens'] or 0 for r in rows),
        reasoning_unknown_responses=sum(r['reasoning_tokens'] is None for r in rows),
        cache_read_share=(sum(r['cache_read_input'] for r in rows) / sum(r['input_total'] for r in rows)) if rows else None)


def recover(snapshot=None):
    old = json.loads((OLD / 'usage_audit.json').read_text())
    old_rows = {r['model']: r for r in csv.DictReader((OLD / 'runtime_tokens.csv').open(encoding='utf-8-sig'))}
    asof = snapshot['as_of_utc'] if snapshot else datetime.now(timezone.utc).isoformat()
    result = dict(as_of_utc=asof, price_checked_date='2026-09-05',
        pricing_sources=['https://developers.openai.com/api/docs/pricing',
                         'https://platform.claude.com/docs/en/about-claude/pricing'],
        rates_usd_per_million=RATES, summaries=[], turns=[], audits={},
        definitions={
            'feedback_all': 'Interrupted preparatory turn plus final common-feedback turn; inter-turn idle excluded.',
            'feedback_main': 'Final common-feedback turn only; tool time and time inside the turn included.',
            'total_tokens': 'Uncached input + cache-read + cache-write + output. Reasoning is contained in output.',
            'cost': 'API Standard-rate equivalent, NOT billed subscription cost. Actual Codex tier is unavailable; Fast scenario is separate. No tax, FX, regional surcharge, negotiated discount, or local compute.',
            'running': 'Elapsed time at snapshot; only usage records already written are counted. In-flight request usage is unavailable.',
            'codex': 'Deduplicate response_id; reconcile every response against both turn and thread counters, including compaction usage.',
            'claude': 'Deduplicate message.id and cross-check requestId; preserve 5m/1h cache-write split. Missing reasoning breakdown is unknown, not zero.'})
    for model in MODELS:
        path = Path(old[model]['source_path'])
        size = snapshot['audits'][model]['source_bytes'] if snapshot else path.stat().st_size
        with path.open('rb') as stream:
            data = stream.read(size)
        data = data[:data.rfind(b'\n') + 1]
        digest = hashlib.sha256(data).hexdigest()
        if snapshot:
            assert digest == snapshot['audits'][model]['source_sha256']
        records = [json.loads(line) for line in data.splitlines() if line.strip()]
        if not snapshot:
            # A file can append while other sources are read. Use one explicit cutoff.
            records = [d for d in records if not d.get('timestamp') or dt(d['timestamp']) <= dt(asof)]
        else:
            records = [d for d in records if not d.get('timestamp') or dt(d['timestamp']) <= dt(asof)]
        codex = '/.codex/' in str(path)
        turns, rows, audit, last_activity = parse(records, codex)
        items = list(turns.values())
        summary = dict(model=model, model_ids=sorted({r['model_id'] for r in rows}))
        for phase, selected in [('initial', INITIAL[model]), ('feedback_prep', PREP[model]),
                                ('feedback_main', MAIN[model]), ('feedback_all', PREP[model] + MAIN[model])]:
            chosen = [t for t in items if t['turn_number'] in selected]
            assert len(chosen) == len(selected)
            summary[phase] = group(chosen, rows, asof)
        for k in FIELDS:
            if k in old_rows[model]:
                assert summary['initial'][k] == int(old_rows[model][k]), (model, k)
        assert abs(summary['initial']['work_minutes'] - float(old_rows[model]['work_minutes'])) < 1e-6
        for t in items:
            if t['turn_number'] in PREP[model] + MAIN[model]:
                result['turns'].append({'model': model, **group([t], rows, asof), **t})
        result['summaries'].append(summary)
        result['audits'][model] = dict(**audit, source_path=str(path), source_bytes=len(data),
            source_sha256=digest, last_activity_utc=last_activity, initial_totals_reconciled=True,
            service_tiers=sorted({r['service_tier'] for r in rows if r.get('service_tier')}),
            speeds=sorted({r['speed'] for r in rows if r.get('speed')}))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--snapshot', type=Path)
    args = parser.parse_args()
    frozen = json.loads(args.snapshot.read_text()) if args.snapshot else None
    print(json.dumps(recover(frozen), ensure_ascii=False, indent=2))
