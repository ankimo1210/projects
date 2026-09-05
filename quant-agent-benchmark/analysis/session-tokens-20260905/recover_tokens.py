#!/usr/bin/env python3
"""Recover audited user-turn and API-response token usage from four named logs.

Only usage metadata, user-prompt labels, and tool metadata are exported.
Reasoning text is neither extracted nor exported. All timestamps retain UTC
and Asia/Tokyo representations. Run with Python 3.12; no network is needed.
"""
from __future__ import annotations

import ast
import collections
import csv
import hashlib
import json
import platform
import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path(__file__).resolve().parent
LOCAL = ZoneInfo("Asia/Tokyo")
SOURCES = {
    "astra": {
        "title": "Model Test Astra", "provider": "codex",
        "path": "/Users/ankimo1210/.codex/sessions/2026/09/05/rollout-2026-09-05T09-40-46-01a06f02-c11c-7ab0-971a-f7abd9ce99ab.jsonl",
        "primary_turn": 4,
        "turn_labels": ["初回準備", "ベンチマーク指示・確認", "モデル名確認", "ベンチマーク本実行", "終了後のグラフ表示"],
        "prior_reported_total": 4446365,
    },
    "sol": {
        "title": "Model Test Sol", "provider": "codex",
        "path": "/Users/ankimo1210/.codex/sessions/2026/09/05/rollout-2026-09-05T09-41-32-01a06f03-72e9-70a1-a254-f7b4e04a719f.jsonl",
        "primary_turn": 2,
        "turn_labels": ["初回準備（中断）", "ベンチマーク本実行", "モデル名確認", "出力先確認", "出力先修正の依頼", "終了後のグラフ表示"],
        "prior_reported_total": 10349887,
    },
    "opus": {
        "title": "model-test-opus", "provider": "claude",
        "path": "/Users/ankimo1210/.claude/projects/-Users-ankimo1210-Documents-projects/8f376df0-177d-4bfc-adf2-21852ba5358b.jsonl",
        "primary_turn": 1, "turn_labels": ["ベンチマーク本実行"],
        "prior_reported_total": 53575487,
    },
    "fable": {
        "title": "model-test-fable", "provider": "claude",
        "path": "/Users/ankimo1210/.claude/projects/-Users-ankimo1210-Documents-projects/bf368b2b-b291-4750-a82f-8ff314837922.jsonl",
        "primary_turn": 1, "turn_labels": ["ベンチマーク本実行"],
        "prior_reported_total": 29313090,
    },
}
FIELDS = ["uncached_input", "cache_read_input", "cache_creation_input", "input_total", "output_nonreasoning", "output_reasoning", "output_total", "total_tokens"]


def dt(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def local(value):
    return dt(value).astimezone(LOCAL).isoformat(timespec="milliseconds")


def elapsed(start, end):
    return (dt(end) - dt(start)).total_seconds()


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def records(path):
    with Path(path).open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if line.strip():
                # Fail rather than silently omit malformed usage-bearing records.
                yield number, json.loads(line)


def normalized_usage(u, provider):
    output = int(u.get("output_tokens") or 0)
    if provider == "codex":
        input_total = int(u.get("input_tokens") or 0)
        read = int(u.get("cached_input_tokens") or 0)
        creation = int(u.get("cache_write_input_tokens") or 0)
        reasoning = int(u.get("reasoning_output_tokens") or 0)
        uncached = input_total - read - creation
    else:
        uncached = int(u.get("input_tokens") or 0)
        read = int(u.get("cache_read_input_tokens") or 0)
        creation = int(u.get("cache_creation_input_tokens") or 0)
        input_total = uncached + read + creation
        reasoning = (u.get("output_tokens_details") or {}).get("thinking_tokens")
        if reasoning is None:
            raise ValueError("non-synthetic Claude response lacks thinking-token metadata")
        reasoning = int(reasoning)
    result = dict(zip(FIELDS, [uncached, read, creation, input_total, output - reasoning, reasoning, output, input_total + output]))
    assert all(v >= 0 for v in result.values()), result
    if provider == "codex":
        assert result["total_tokens"] == int(u["total_tokens"])
    return result


def counter_segment_totals(values):
    """Independent cumulative audit; ignore repeats, restart on decreases."""
    totals = collections.Counter()
    previous = None
    repeats = resets = 0
    for usage in values:
        if previous is not None and usage["total_tokens"] == previous["total_tokens"]:
            assert usage == previous
            repeats += 1
        elif previous is not None and usage["total_tokens"] < previous["total_tokens"]:
            totals.update(previous)
            resets += 1
        previous = usage
    if previous is not None:
        totals.update(previous)
    return dict(totals), repeats, resets


def text_content(content):
    if isinstance(content, str):
        return content
    return " ".join(x.get("text", "") for x in (content or []) if isinstance(x, dict) and x.get("type") in ("text", "input_text", "output_text"))


def is_actual_claude_prompt(record):
    if record.get("type") != "user" or record.get("isMeta"):
        return False
    content = (record.get("message") or {}).get("content")
    if isinstance(content, list) and any(x.get("type") == "tool_result" for x in content if isinstance(x, dict)):
        return False
    text = text_content(content).strip()
    return bool(text) and not text.startswith(("<system-reminder>", "<command-name>", "<local-command", "This session is being continued from a previous conversation"))


def tool_category(name, arguments):
    """Coarse, noncausal labels of observable calls; contents are not exported."""
    command = str(arguments)
    lower = name.lower()
    if lower in ("write", "edit", "apply_patch") or "tools.apply_patch(" in command or "*** Begin Patch" in command:
        return "write_edit"
    if lower in ("read", "glob", "grep"):
        return "read_inspect"
    if any(x in lower for x in ("browser", "computer", "navigate", "view_image", "screenshot")) or "cua." in command or "view_image(" in command:
        return "visual_check"
    if "write_stdin" in command or lower in ("wait", "sleep"):
        return "poll_wait"
    if "toolsearch" in lower:
        return "tool_discovery"
    if re.search(r"(?:pytest|unittest|py_compile|ruff check|compileall)", command):
        return "test_command"
    if re.search(r"(?:write_text\(|write_bytes\(|cat\s*>|cat\s+<<|\.to_csv\(|\.savefig\()", command):
        return "write_edit"
    if re.search(r"(?:\bpip\s+install|uv sync|\bvenv\b|mkdir|docker|cp -)", command):
        return "environment_files"
    if re.search(r"(?:\bsed\s|\brg\s|\bls\s|\bhead\s|\bcat\s|read_text\(|read_csv\()", command):
        return "read_inspect"
    return "execute_other"


def error_from_output(value):
    """Extract explicit recorded failures only; not an estimate of failed tests."""
    s = str(value)
    if "data:image/" in s:
        return False
    # Tool wrapper can contain Python-literal MCP content with escaped JSON.
    try:
        parsed = ast.literal_eval(s)
        if isinstance(parsed, list):
            s = "\n".join(x.get("text", "") for x in parsed if isinstance(x, dict))
    except (ValueError, SyntaxError):
        pass
    return bool(re.search(r'"exit_code"\s*:\s*[1-9]\d*|Process exited with code [1-9]\d*|Exit code: [1-9]\d*|Script error:', s))


def common_turn(config, number, tid, start):
    return {"turn_number": number, "turn_id": tid, "start_utc": start, "end_utc": start,
            "label": config["turn_labels"][number-1] if number <= len(config["turn_labels"]) else "追加依頼",
            "status": "no_completion_marker", "is_primary_benchmark": number == config["primary_turn"]}


def parse_codex(config):
    turns, calls, api, cumulative, audit = [], {}, [], [], {}
    turn_by_id, contexts = {}, {}
    seen_response, pending_calls = set(), []
    current = None
    for line, d in records(config["path"]):
        p = d.get("payload") or {}
        t, typ, ts = d.get("type"), p.get("type"), d.get("timestamp")
        if t == "session_meta":
            audit["session_id"] = p["id"]
        if t == "event_msg" and typ == "task_started":
            assert not pending_calls, "orphaned calls before new turn"
            current = common_turn(config, len(turns)+1, p["turn_id"], ts)
            turns.append(current); turn_by_id[current["turn_id"]] = current
        elif t == "turn_context":
            contexts[p["turn_id"]] = {"model_id": p.get("model"), "reasoning_effort": p.get("effort")}
        elif t == "event_msg" and typ in ("task_complete", "turn_aborted"):
            target = turn_by_id[p["turn_id"]]
            target["end_utc"] = ts
            target["status"] = typ
            target["reported_duration_ms"] = p.get("duration_ms")
        elif t == "response_item" and typ in ("custom_tool_call", "function_call"):
            cid = p.get("call_id") or p.get("id")
            if cid in calls:
                continue
            args = p.get("input", p.get("arguments", ""))
            calls[cid] = {"call_id": cid, "turn_number": current["turn_number"], "timestamp_utc": ts,
                          "tool_name": p.get("name", "unknown"), "activity": tool_category(p.get("name", ""), args),
                          "explicit_error": False, "error_detection": "structured_exit_or_wrapper", "source_line": line}
            pending_calls.append(cid)
        elif t == "response_item" and typ in ("custom_tool_call_output", "function_call_output"):
            if p.get("call_id") in calls:
                call = calls[p["call_id"]]
                call["explicit_error"] = error_from_output(p.get("output"))
                call["result_timestamp_utc"] = ts
        elif t == "token_usage_record":
            rid = p["response_id"]
            if rid in seen_response:
                continue
            seen_response.add(rid)
            turn = turn_by_id[p["turn_id"]]
            usage = normalized_usage(p["usage"], "codex")
            api.append({"response_id": rid, "request_id": "", "turn_id": p["turn_id"], "turn_number": turn["turn_number"],
                        "timestamp_utc": ts, "first_record_timestamp_utc": ts, "last_record_timestamp_utc": ts,
                        "source_line_first": line, "source_line_last": line, "usage_records": 1,
                        "model_id": contexts.get(p["turn_id"], {}).get("model_id"),
                        "reasoning_effort": contexts.get(p["turn_id"], {}).get("reasoning_effort"),
                        "call_ids": pending_calls[:], **usage})
            pending_calls.clear()
            assert usage["total_tokens"] <= p["turn_token_usage"]["total_tokens"]
            audit["final_thread_counter"] = p["thread_token_usage"]
        elif t == "event_msg" and typ == "token_count":
            u = (p.get("info") or {}).get("total_token_usage")
            if u:
                cumulative.append(normalized_usage(u, "codex"))
    assert not pending_calls, "call lacks a usage record"
    independent, repeated, resets = counter_segment_totals(cumulative)
    actual = {k: sum(a[k] for a in api) for k in FIELDS}
    assert actual == independent, (actual, independent)
    assert actual == normalized_usage(audit["final_thread_counter"], "codex")
    audit.update({"usage_method": "response_id-deduplicated token_usage_record.usage", "raw_usage_records": len(seen_response),
                  "token_count_events": len(cumulative), "duplicate_counter_events": repeated, "counter_resets": resets,
                  "independent_cumulative_reconciliation": True, "duplicate_api_blocks_removed": 0})
    return turns, api, list(calls.values()), audit


def parse_claude(config):
    turns, calls, groups, audit = [], {}, {}, {}
    current = None
    raw_sum = collections.Counter()
    synthetic = meta_excluded = compact = 0
    for line, d in records(config["path"]):
        t, ts = d.get("type"), d.get("timestamp")
        if d.get("sessionId"):
            audit["session_id"] = d["sessionId"]
        if t == "user":
            if is_actual_claude_prompt(d):
                current = common_turn(config, len(turns)+1, d.get("promptId") or d.get("uuid"), ts)
                turns.append(current)
            else:
                content = (d.get("message") or {}).get("content")
                if isinstance(content, list):
                    for block in content:
                        if block.get("type") == "tool_result" and block.get("tool_use_id") in calls:
                            c = calls[block["tool_use_id"]]
                            c["explicit_error"] = bool(block.get("is_error"))
                            c["result_timestamp_utc"] = ts
                else:
                    meta_excluded += 1
        elif t == "assistant":
            msg, u = d.get("message") or {}, (d.get("message") or {}).get("usage") or {}
            if msg.get("model") == "<synthetic>":
                assert sum(int(u.get(k) or 0) for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")) == 0
                synthetic += 1
                continue
            if not u:
                raise ValueError(f"assistant record without usage on line {line}")
            assert current is not None, "API response before human prompt"
            rid = msg.get("id")
            assert rid, "Claude message.id required"
            usage = normalized_usage(u, "claude")
            raw_sum.update(usage)
            if rid not in groups:
                groups[rid] = {"response_id": rid, "request_id": d.get("requestId", ""),
                               "turn_id": current["turn_id"], "turn_number": current["turn_number"],
                               "timestamp_utc": ts, "first_record_timestamp_utc": ts, "last_record_timestamp_utc": ts,
                               "source_line_first": line, "source_line_last": line, "usage_records": 0,
                               "model_id": msg.get("model"), "reasoning_effort": d.get("effort"), "call_ids": [], **usage}
            group = groups[rid]
            assert {k: group[k] for k in FIELDS} == usage, f"usage revisions for {rid}; manual review required"
            assert group["request_id"] == d.get("requestId", ""), "message ID reused across requests"
            group["usage_records"] += 1
            group["last_record_timestamp_utc"] = ts
            group["source_line_last"] = line
            current["end_utc"] = max(current["end_utc"], ts)
            for block in msg.get("content") or []:
                if block.get("type") == "tool_use":
                    cid = block["id"]
                    if cid not in calls:
                        calls[cid] = {"call_id": cid, "turn_number": current["turn_number"], "timestamp_utc": ts,
                                      "tool_name": block.get("name", "unknown"),
                                      "activity": tool_category(block.get("name", ""), block.get("input")),
                                      "explicit_error": False, "error_detection": "tool_result.is_error", "source_line": line}
                        group["call_ids"].append(cid)
        elif t == "system" and d.get("subtype") == "compact_boundary":
            compact += 1
            audit["compaction"] = {"timestamp_utc": ts, **{k: (d.get("compactMetadata") or {}).get(k) for k in ("trigger", "preTokens", "postTokens", "durationMs")}}
        elif t == "system" and d.get("subtype") == "turn_duration" and current:
            current.update(end_utc=ts, status="turn_duration", reported_duration_ms=d.get("durationMs"))
    api = list(groups.values())
    unique_request_ids = {g["request_id"] for g in api}
    assert len(unique_request_ids) == len(api), "multiple message IDs per request need review"
    audit.update({"usage_method": "one identical usage per message.id; requestId independently cross-checked",
                  "raw_usage_records": sum(g["usage_records"] for g in api),
                  "duplicate_api_blocks_removed": sum(g["usage_records"]-1 for g in api),
                  "raw_block_totals": dict(raw_sum), "synthetic_zero_usage_records": synthetic,
                  "excluded_nonhuman_user_messages": meta_excluded, "compaction_events": compact,
                  "all_repeated_usage_identical": True, "unique_request_ids": len(unique_request_ids)})
    return turns, api, list(calls.values()), audit


def aggregate(rows):
    return {k: sum(row[k] for row in rows) for k in FIELDS}


def write_csv(path, rows):
    assert rows
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in row.items()})


def main():
    import importlib.metadata
    all_api, all_turns, all_tools, all_bins, summaries = [], [], [], [], []
    audits = {}
    for model, config in SOURCES.items():
        source_sha = digest(config["path"])
        turns, api, calls, audit = (parse_codex if config["provider"] == "codex" else parse_claude)(config)
        assert source_sha == digest(config["path"]), "source changed while being read"
        call_map = {c["call_id"]: c for c in calls}
        turn_map = {t["turn_number"]: t for t in turns}
        primary = turn_map[config["primary_turn"]]
        cumulative = 0
        for n, response in enumerate(api, 1):
            turn = turn_map[response["turn_number"]]
            cumulative += response["total_tokens"]
            response.update(model=model, session_name=config["title"], session_id=audit["session_id"], api_step=n,
                            timestamp_jst=local(response["timestamp_utc"]), turn_label=turn["label"],
                            is_primary_benchmark=turn["is_primary_benchmark"],
                            elapsed_session_minutes=elapsed(turns[0]["start_utc"], response["timestamp_utc"])/60,
                            elapsed_turn_minutes=elapsed(turn["start_utc"], response["timestamp_utc"])/60,
                            cumulative_total_tokens=cumulative)
            response["tool_calls"] = len(response["call_ids"])
            response["tool_names"] = [call_map[c]["tool_name"] for c in response["call_ids"]]
            response["observable_activities"] = sorted({call_map[c]["activity"] for c in response["call_ids"]}) or ["response_without_tool"]
            response["explicit_tool_errors"] = sum(call_map[c]["explicit_error"] for c in response["call_ids"])
        for turn in turns:
            children = [a for a in api if a["turn_number"] == turn["turn_number"]]
            turn_calls = [c for c in calls if c["turn_number"] == turn["turn_number"]]
            turn.update(model=model, session_name=config["title"], session_id=audit["session_id"],
                        start_jst=local(turn["start_utc"]), end_jst=local(turn["end_utc"]),
                        elapsed_seconds=elapsed(turn["start_utc"], turn["end_utc"]),
                        api_responses=len(children), tool_calls=len(turn_calls),
                        explicit_tool_errors=sum(c["explicit_error"] for c in turn_calls), **aggregate(children))
        for call in calls:
            call.update(model=model, session_name=config["title"], timestamp_jst=local(call["timestamp_utc"]))
            if call.get("result_timestamp_utc"):
                call["observed_tool_interval_seconds"] = elapsed(call["timestamp_utc"], call["result_timestamp_utc"])
        primary_api = [a for a in api if a["is_primary_benchmark"]]
        summary = {"model": model, "session_name": config["title"], "session_id": audit["session_id"],
                   "model_ids": sorted({a["model_id"] for a in api}),
                   "reasoning_efforts": sorted({a["reasoning_effort"] for a in api if a["reasoning_effort"]}),
                   "user_turns": len(turns), "api_responses": len(api), "tool_calls": len(calls),
                   "explicit_tool_errors": sum(c["explicit_error"] for c in calls),
                   "start_jst": turns[0]["start_jst"], "end_jst": turns[-1]["end_jst"],
                   "active_turn_minutes": sum(t["elapsed_seconds"] for t in turns)/60,
                   "session_elapsed_minutes": elapsed(turns[0]["start_utc"], turns[-1]["end_utc"])/60,
                   "primary_elapsed_minutes": primary["elapsed_seconds"]/60,
                   "primary_api_responses": len(primary_api), "primary_total_tokens": primary["total_tokens"],
                   "primary_output_tokens": primary["output_total"], "primary_reasoning_tokens": primary["output_reasoning"],
                   "primary_mean_input_tokens": sum(a["input_total"] for a in primary_api)/len(primary_api),
                   "primary_mean_output_tokens": sum(a["output_total"] for a in primary_api)/len(primary_api),
                   "prior_reported_total": config["prior_reported_total"], **aggregate(api)}
        summary["overcount_in_prior_report"] = config["prior_reported_total"] - summary["total_tokens"]
        summary["cache_read_fraction_of_input"] = summary["cache_read_input"]/summary["input_total"]
        summary["reasoning_fraction_of_output"] = summary["output_reasoning"]/summary["output_total"]
        assert aggregate(turns) == aggregate(api)
        # Exact five-minute bins, using observed record timestamps (no interpolation).
        buckets = collections.defaultdict(list)
        for a in api:
            ts = dt(a["timestamp_utc"]).astimezone(LOCAL)
            key = ts.replace(minute=ts.minute//5*5, second=0, microsecond=0).isoformat()
            buckets[key].append(a)
        for key, children in sorted(buckets.items()):
            all_bins.append({"model": model, "session_name": config["title"], "bin_start_jst": key,
                             "api_responses": len(children), "user_turns": sorted({a["turn_number"] for a in children}), **aggregate(children)})
        assert aggregate([b for b in all_bins if b["model"] == model]) == aggregate(api)
        audit.update(source_path=config["path"], source_sha256=source_sha, source_bytes=Path(config["path"]).stat().st_size,
                     normalized_totals=aggregate(api), user_turn_totals_reconcile=True, five_minute_bins_reconcile=True)
        audits[model] = audit
        all_api.extend(api); all_turns.extend(turns); all_tools.extend(calls); summaries.append(summary)
    for filename, rows in (("api_responses.csv", all_api), ("user_turns.csv", all_turns), ("tool_events.csv", all_tools), ("timeline_5min.csv", all_bins), ("session_summary.csv", summaries)):
        write_csv(BASE/filename, rows)
    (BASE/"audit.json").write_text(json.dumps({"schema_version": "1.0", "generated_utc": datetime.now(timezone.utc).isoformat(),
                                            "python": platform.python_version(), "packages": {n: importlib.metadata.version(n) for n in ("numpy", "matplotlib")},
                                            "sources": audits}, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    chart_and_notes(summaries, all_turns, all_api, all_tools, audits)
    print(json.dumps({"sessions": summaries, "turns": [{k:t[k] for k in ("model","turn_number","label","api_responses","total_tokens","output_total","elapsed_seconds")} for t in all_turns],
                      "checks": "API totals = user-turn totals = five-minute bins; source hashes stable", "output_dir": str(BASE)}, ensure_ascii=False, indent=2))


def chart_and_notes(summaries, turns, api, tools, audits):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    colors = {"astra": "#1769aa", "sol": "#b77912", "opus": "#cc5a18", "fable": "#a84378"}
    styles = {"astra": "-", "sol": "--", "opus": "-.", "fable": ":"}
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.titlesize": 12, "svg.hashsalt": "token-audit-v1"})
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), constrained_layout=True)
    fig.suptitle("Benchmark session token timeline | 2026-09-05", fontsize=18, weight="bold")
    ax = axes[0, 0]
    for s in summaries:
        model = s["model"]
        data = [a for a in api if a["model"] == model and a["is_primary_benchmark"]]
        x = [0]+[a["elapsed_turn_minutes"] for a in data]
        y = [0]+(np.cumsum([a["total_tokens"] for a in data])/1e6).tolist()
        ax.step(x, y, where="post", color=colors[model], linestyle=styles[model], label=f"{model.title()} ({len(data)} responses)", linewidth=2)
    ax.set(title="Cumulative processed tokens: primary execution turn", xlabel="Minutes since primary turn start", ylabel="Tokens (millions)")
    ax.set_xlim(left=0); ax.set_ylim(bottom=0); ax.legend(fontsize=9); ax.grid(alpha=.2)
    ax = axes[0, 1]
    for s in summaries:
        model = s["model"]; data = [a for a in api if a["model"] == model and a["is_primary_benchmark"]]
        ax.plot(range(1, len(data)+1), np.array([a["input_total"] for a in data])/1000,
                color=colors[model], linestyle=styles[model], label=model.title(), linewidth=1.8)
    ax.set(title="Input tokens per API response: primary turn", xlabel="API response index within primary turn", ylabel="Input tokens (thousands; cache included)")
    ax.set_xlim(left=1); ax.set_ylim(bottom=0); ax.grid(alpha=.2)
    ax = axes[1, 0]
    data = [[a["output_total"]/1000 for a in api if a["model"] == s["model"] and a["is_primary_benchmark"]] for s in summaries]
    box = ax.boxplot(data, tick_labels=[s["model"].title() for s in summaries], patch_artist=True,
                     medianprops={"color": "#222222", "linewidth": 1.6}, flierprops={"marker": ".", "markersize": 4})
    for patch, s in zip(box["boxes"], summaries): patch.set_facecolor(colors[s["model"]]); patch.set_alpha(.55)
    ax.set(title="Output tokens per API response: primary turn", ylabel="Output tokens (thousands; reasoning included)")
    ax.set_ylim(bottom=0); ax.grid(axis="y", alpha=.2)
    ax = axes[1, 1]
    positions = np.arange(len(summaries))
    main = np.array([s["primary_total_tokens"] for s in summaries])/1e6
    other = np.array([s["total_tokens"]-s["primary_total_tokens"] for s in summaries])/1e6
    ax.barh(positions, main, color="#1769aa", label="Primary execution turn")
    ax.barh(positions, other, left=main, color="#c4c9cf", hatch="///", label="Other session turns")
    for y, s in zip(positions, summaries): ax.text(s["total_tokens"]/1e6+.15, y, f'{s["total_tokens"]/1e6:.2f}M', va="center", fontsize=9)
    ax.set_yticks(positions, [s["model"].title() for s in summaries]); ax.invert_yaxis()
    ax.set(title="Session totals split by user-turn scope", xlabel="Processed tokens (millions; deduplicated)")
    ax.set_xlim(0, max(s["total_tokens"] for s in summaries)/1e6*1.19); ax.legend(loc="lower right", fontsize=9); ax.grid(axis="x", alpha=.2)
    fig.savefig(BASE/"token_timeline.png", dpi=160)
    fig.savefig(BASE/"token_timeline.svg")
    plt.close(fig)

    lines = ["# セッション別・ターン別トークン監査", "",
             "4セッションのローカルログに記録された使用量を再集計したデータです。`Model Test Prep` は対象外です。", "",
             "## 集計の訂正", "",
             "前回のClaude集計はレコードUUIDを優先したため、同じAPI応答がcontent blockごとに二重・多重計上されていました。今回は `message.id` で統合し、`requestId` でも1対1を照合しています。同一応答のusageは全コピーで一致しました。推論量は `output_tokens_details.thinking_tokens` にあり、出力総量の内数として分離できます。", "",
             "| セッション | API応答数 | 前回報告 | 今回の総量 | 重複分の除去 |",
             "|---|---:|---:|---:|---:|"]
    for s in summaries:
        lines.append(f'| {s["session_name"]} | {s["api_responses"]} | {s["prior_reported_total"]:,} | {s["total_tokens"]:,} | {s["overcount_in_prior_report"]:,} |')
    lines += ["", "## セッション内の重複しない内訳", "",
              "| モデル | 非キャッシュ入力 | キャッシュ読取 | キャッシュ作成 | 推論出力 | 非推論出力 | 合計 |",
              "|---|---:|---:|---:|---:|---:|---:|"]
    for s in summaries:
        lines.append(f'| {s["model"].title()} | {s["uncached_input"]:,} | {s["cache_read_input"]:,} | {s["cache_creation_input"]:,} | {s["output_reasoning"]:,} | {s["output_nonreasoning"]:,} | {s["total_tokens"]:,} |')
    lines += ["", "## ターン別", "", "ターンはユーザーの実際の依頼1回から、その応答・ツール実行が終わるまでです。Claudeのツール結果（role=user）、ローカルコマンド、システム通知、自動要約は新しいユーザーターンに数えません。", "",
              "| セッション | ターン | 作業 | 開始–終了（JST） | 分 | API応答 | 合計tokens | 推論 | 非推論出力 |",
              "|---|---:|---|---|---:|---:|---:|---:|---:|"]
    for t in turns:
        begin, end = dt(t["start_utc"]).astimezone(LOCAL).strftime("%H:%M:%S"), dt(t["end_utc"]).astimezone(LOCAL).strftime("%H:%M:%S")
        lines.append(f'| {t["session_name"]} | {t["turn_number"]} | {t["label"]} | {begin}–{end} | {t["elapsed_seconds"]/60:.2f} | {t["api_responses"]} | {t["total_tokens"]:,} | {t["output_reasoning"]:,} | {t["output_nonreasoning"]:,} |')
    lines += ["", "## 本実行の比較", "",
              "本実行はAstraのターン4、Solのターン2、Opus/Fableのターン1です。各依頼の内容とログ上のイベント境界を照合して選びました。Astraの追加パス確認やSolの終了後出力先修正は別ターンです。この差があるため、本実行だけの比較と全セッション比較の両方を残しています。", "",
              "| モデル | 本実行時間（分） | API応答 | 平均入力/応答 | 平均出力/応答 | 本実行総量 |",
              "|---|---:|---:|---:|---:|---:|"]
    for s in summaries:
        lines.append(f'| {s["model"].title()} | {s["primary_elapsed_minutes"]:.2f} | {s["primary_api_responses"]} | {s["primary_mean_input_tokens"]:,.0f} | {s["primary_mean_output_tokens"]:,.0f} | {s["primary_total_tokens"]:,} |')
    lines += ["", "## この実行で観測できる進め方の違い", "",
              "- Astraは本実行40応答、Solは72応答。Solは応答回数が多く、平均入力文脈も大きいため、本実行の処理総量が増えています。出力総量だけを見るとAstraは83,220、Solは74,001です。",
              "- Opusは114応答、Fableは41応答。両者の平均入力は約256,000トークンで近い一方、平均出力はOpus約2,647、Fable約6,762です。この実行ではFableは少ない応答に大きな出力をまとめる傾向がありました。",
              "- 入力文脈が積み重なるため、後半の1応答は前半より処理量が大きくなります。総トークンが多いことは、その分だけ新しいコードや推論を生成したことを意味しません。",
              "- Solには本実行終了後の出力先修正依頼ターンがあり、その使用量は731,055です。本実行の34.60分だけを『完全な引き渡しまでの時間』とは扱えません。",
              "- Opus末尾には自動要約イベントがあります。記録されたturn_durationにはこの待ち時間も含まれ、API応答の単純な生成速度とは異なります。", "",
              "以下は本実行で出力が大きかったAPI応答です。作業タグは同じ応答に付随するツール操作を示し、思考内容や厳密な目的別コストを表しません。", "",
              "| モデル | セッション内API番号 | 記録時刻（JST） | 出力合計 | 推論 | 非推論 | 作業タグ |",
              "|---|---:|---|---:|---:|---:|---|"]
    for s in summaries:
        sample = sorted([a for a in api if a["model"] == s["model"] and a["is_primary_benchmark"]], key=lambda a: a["output_total"], reverse=True)[:2]
        for a in sample:
            lines.append(f'| {s["model"].title()} | {a["api_step"]} | {dt(a["timestamp_utc"]).astimezone(LOCAL).strftime("%H:%M:%S")} | {a["output_total"]:,} | {a["output_reasoning"]:,} | {a["output_nonreasoning"]:,} | {", ".join(a["observable_activities"])} |')
    lines += ["", "![トークン時系列](token_timeline.png)", "", "## ファイル", "",
              "- `api_responses.csv`: API応答ごとの使用量、推論内訳、ユーザーターン、記録時刻、累積量、ツール活動。", 
              "- `user_turns.csv`: ユーザー依頼単位の使用量、実時間、API数。",
              "- `timeline_5min.csv`: JSTの5分窓ごとのトークン量。記録がない窓はCSVに行を作りません。",
              "- `session_summary.csv`: セッション・本実行の集計。",
              "- `tool_events.csv`: ツール名、時刻、粗い作業分類、明示的エラーフラグ。本文やコマンド全文は含みません。",
              "- `audit.json`: ログの絶対パス、SHA-256、重複除去件数、照合結果、実行環境。",
              "- `token_timeline.png` / `.svg`: 保存用の時系列・入力文脈量・出力分布・ターン範囲比較。", "",
              "## 定義・検証・限界", "",
              "1. Codexは `token_usage_record.usage` をresponse_idで一意化して合算。別系統の `token_count.total_token_usage` と最終thread counterの双方へ一致しました。繰り返し累計イベントは二重計上しません。",
              "2. Claudeはmessage.idで一意化。requestIdも照合。usageの値が同一ID内で異なる場合やJSON破損は黙って無視せず停止します。Opusの自動要約後にあるsynthetic・ゼロusage応答はAPI数から除外しました。",
              "3. 入力総量＝非キャッシュ入力＋キャッシュ読取＋キャッシュ作成。出力総量＝推論出力＋非推論出力。合計＝入力総量＋出力総量。非推論出力は最終回答だけでなくコード・ツール引数等も含みます。",
              "4. API応答・ユーザーターン・5分窓・セッションの合計は一致し、読取前後の元ログSHA-256も一致しました。入力市場データ・評価器・候補成果物には変更を加えていません。",
              "5. API時刻はログに記録されたusage応答時刻で、推論開始時刻ではありません。Claudeの同一APIの複数blockは最初と最後の記録時刻を両方保存し、時系列集計には最初の時刻を使います。ストリーミング中の秒単位消費は復元できません。",
              "6. 実行時間はユーザーターンの実時間で、ツール待機・要約・一時停止等を含みます。セッション全体の経過時間にはユーザーの返信待ちも入り、APIレイテンシや純粋な生成速度ではありません。",
              "7. `observable_activities` はツール名・引数に基づく粗い分類で、使用量の厳密な作業別帰属ではありません。入力の多くは過去文脈の再読込です。API数・ツール呼出数はクライアントのまとめ方にも依存します。",
              "8. reasoningはログにある数値だけを使用し、思考本文は分析・保存しません。課金・価格は計算していません。総処理トークンはキャッシュ反復と異なるトークナイザを含むため、そのまま能力・コスト・効率の順位にはなりません。",
              "9. 記録されていない内部処理・別子エージェントファイル・API使用量が非公開の要約処理は含みません。これらをゼロコストとみなしません。実行1回ずつの観測であり、モデル固有の性格や品質を断定する根拠ではありません。", "",
              "## 再実行", "", "```bash", f"python3.12 {BASE/'recover_tokens.py'}", f"python3.12 -m unittest discover -s {BASE} -p 'test_*.py' -v", "```", "",
              "可視化は visualize-data の手順に沿い、合計の照合後に、共通の単位・軸・凡例で出力しています。", ""]
    (BASE/"README.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
