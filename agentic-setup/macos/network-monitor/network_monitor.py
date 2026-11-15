#!/usr/bin/env python3
"""Small, local-only connectivity recorder for macOS. No third-party packages."""
from __future__ import annotations

import argparse
import concurrent.futures
import contextlib
import datetime as dt
import fcntl
import gzip
import json
import math
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import tempfile
import time
from zoneinfo import ZoneInfo

INTERVAL = 15
FULL_INTERVAL = 60
LABEL = "com.ankimo.network-monitor"
DEFAULT_LOG_DIR = Path.home() / "Library/Logs/NetworkMonitor"
HTTPS_TARGETS = {
    "apple": "https://www.apple.com/library/test/success.html",
    "anthropic": "https://api.anthropic.com/",
    "openai": "https://api.openai.com/v1/models",
    "ip": "https://1.1.1.1/cdn-cgi/trace",
}
TZ = ZoneInfo("Asia/Tokyo")


def command(args, timeout=4):
    start = time.monotonic()
    try:
        result = subprocess.run(args, capture_output=True, text=True,
                                errors="replace", timeout=timeout)
        return {"code": result.returncode, "text": result.stdout,
                "error": result.stderr.strip()[:160],
                "elapsed_ms": round((time.monotonic() - start) * 1000, 2)}
    except (subprocess.TimeoutExpired, OSError) as exc:
        return {"code": -1, "text": "", "error": type(exc).__name__,
                "elapsed_ms": round((time.monotonic() - start) * 1000, 2)}


def route_info():
    result = command(["/sbin/route", "-n", "get", "default"], 2)
    values = dict(re.findall(r"^\s*(gateway|interface):\s*(\S+)",
                             result["text"], re.M))
    values["ok"] = result["code"] == 0 and bool(values.get("gateway"))
    return values


def ping(host):
    if not host:
        return {"ok": False, "error": "no_gateway"}
    result = command(["/sbin/ping", "-n", "-q", "-c", "2", "-i", "0.2",
                      "-W", "1000", host], 3)
    match = re.search(r"(\d+) packets transmitted, (\d+) packets received",
                      result["text"])
    timing = re.search(r"= ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+) ms",
                       result["text"])
    received = int(match[2]) if match else 0
    return {"ok": received > 0, "sent": int(match[1]) if match else 2,
            "received": received,
            "rtt_ms": float(timing[2]) if timing else None,
            **({"error": result["error"] or "no_reply"} if not received else {})}


def dns(server, tcp=False):
    args = ["/usr/bin/dig", "@" + server, "api.anthropic.com", "A",
            "+tries=1", "+time=2", "+noall", "+comments", "+answer", "+stats"]
    if tcp:
        args.append("+tcp")
    result = command(args, 3)
    status = re.search(r"status: ([A-Z]+)", result["text"])
    timing = re.search(r"Query time: (\d+) msec", result["text"])
    answer = re.search(r"^api\.anthropic\.com\.\s+\d+\s+IN\s+(?:A|CNAME)\s+",
                       result["text"], re.M)
    return {"ok": result["code"] == 0 and bool(status)
            and status[1] == "NOERROR" and bool(answer),
            "status": status[1] if status else None,
            "ms": int(timing[1]) if timing else None,
            "code": result["code"]}


def https(url, ipv6=False):
    args = ["/usr/bin/curl", "--silent", "--show-error", "--output", "/dev/null",
            "--connect-timeout", "2", "--max-time", "4", "--write-out", "%{json}"]
    args += ["--ipv6"] if ipv6 else ["--ipv4"]
    result = command([*args, url], 5)
    try:
        data = json.loads(result["text"])
    except json.JSONDecodeError:
        data = {}
    status = data.get("http_code", 0)
    # 401/404 are expected without credentials/on the API root; they prove transport.
    values = {"ok": result["code"] == 0 and status > 0,
              "code": result["code"], "status": status}
    for key, field in [("dns_ms", "time_namelookup"), ("connect_ms", "time_connect"),
                       ("tls_ms", "time_appconnect"), ("ttfb_ms", "time_starttransfer"),
                       ("total_ms", "time_total")]:
        if isinstance(data.get(field), (int, float)):
            values[key] = round(data[field] * 1000, 2)
    for name, end, start in [("tcp_phase_ms", "connect_ms", "dns_ms"),
                              ("tls_phase_ms", "tls_ms", "connect_ms"),
                              ("response_wait_ms", "ttfb_ms", "tls_ms")]:
        if values.get(end, 0) > 0 and values[end] >= values.get(start, 0):
            values[name] = round(values[end] - values.get(start, 0), 2)
    if not values["ok"]:
        values["error"] = result["error"] or "transport_failure"
    return values


def network_details():
    text = command(["/usr/sbin/scutil", "--dns"], 2)["text"]
    servers = list(dict.fromkeys(re.findall(r"nameserver\[\d+\]\s*:\s*(\S+)", text)))
    nwi = command(["/usr/sbin/scutil", "--nwi"], 2)["text"]
    ipv6 = nwi.split("IPv6 network interface information", 1)[-1]
    proxy = command(["/usr/sbin/scutil", "--proxy"], 2)["text"]
    return {"dns_servers": servers,
            "system_proxy_enabled": bool(re.search(r"(?:HTTP|HTTPS|SOCKS|ProxyAutoConfig)Enable\s*:\s*1", proxy)),
            "ipv6_available": "IPv6 network interface information" in nwi
            and "No IPv6 states found" not in ipv6 and bool(re.search(r"address\s*:", ipv6))}


def wifi_info(interface):
    helper = Path(__file__).with_name("wifi-info")
    if not helper.is_file() or not interface:
        return {"available": False}
    result = command([str(helper), interface], 2)
    try:
        return json.loads(result["text"])
    except json.JSONDecodeError:
        return {"available": False, "error": result["error"] or "telemetry_unavailable"}


def classify(sample):
    if not sample["route"].get("ok"):
        return "no_default_route"
    web = sample.get("https")
    if web:
        failed = [name for name, value in web.items() if not value.get("ok")]
        named = [web[name] for name in ["apple", "anthropic", "openai"]]
        if web["ip"].get("ok") and sum(v.get("code") == 6 for v in named) >= 2:
            return "dns_issue_suspected"
        dns_results = sample.get("dns", {})
        if (dns_results.get("primary", {}).get("ok") is False
                and dns_results.get("public_udp", {}).get("ok")
                and web["ip"].get("ok")):
            return "primary_dns_issue_suspected"
        if len(failed) >= 2:
            if sample.get("ipv6_https", {}).get("ok"):
                return "ipv4_path_issue_suspected"
            return ("upstream_issue_suspected" if sample["ping"]["gateway"].get("ok")
                    else "local_or_router_issue_suspected")
        if failed:
            return "single_destination_issue"
        if any(v.get("status", 0) >= 500 for v in web.values()):
            return "http_server_error"
        if sum(v.get("total_ms", 0) >= 1500 for v in web.values()) >= 2:
            return "high_latency"
    losses = any(v.get("received", 0) < v.get("sent", 1)
                 for v in sample["ping"].values())
    dns_losses = any(not v.get("ok") for v in sample.get("dns", {}).values())
    return "probe_loss_only" if losses or dns_losses else "healthy"


def transition_events(previous, sample):
    events = []
    gap = sample["epoch"] - previous.get("epoch", sample["epoch"])
    boot_changed = bool(previous) and previous.get("boot") != sample.get("boot")
    if previous and (gap > INTERVAL * 3 or gap < 0 or boot_changed):
        events.append({"kind": "observation_gap", "seconds": round(gap, 1),
                       "reason": "boot_changed" if boot_changed else "sleep_pause_or_clock_change"})
    if not previous:
        events.append({"kind": "monitor_started"})
    elif sample["route"] != previous.get("route"):
        events.append({"kind": "route_changed", "before": previous.get("route"),
                       "after": sample["route"]})
    before_wifi = previous.get("wifi", {})
    after_wifi = sample.get("wifi", {})
    for field in ["channel", "width_mhz"]:
        if (before_wifi.get(field) is not None and after_wifi.get(field) is not None
                and before_wifi[field] != after_wifi[field]):
            events.append({"kind": "wifi_" + field + "_changed",
                           "before": before_wifi[field], "after": after_wifi[field]})
    if previous.get("condition") != sample["condition"]:
        events.append({"kind": "condition_changed", "before": previous.get("condition"),
                       "after": sample["condition"]})
    return events


def atomic_json(path, value):
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, prefix=".state-",
                                     delete=False) as handle:
        os.chmod(handle.name, 0o600)
        json.dump(value, handle, ensure_ascii=False)
        handle.flush()
        os.fsync(handle.fileno())
        temporary = handle.name
    os.replace(temporary, path)


def append_log(path, value):
    # One independent gzip member per JSON line: bounded work, no log deletion.
    payload = (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
    compressed = gzip.compress(payload, compresslevel=5, mtime=0)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "ab") as handle:
        handle.write(compressed)
        handle.flush()
        os.fsync(handle.fileno())


@contextlib.contextmanager
def lock(log_dir, shared=False, name=".lock"):
    log_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(log_dir / name, os.O_RDWR | os.O_CREAT, 0o600)
    with os.fdopen(fd, "a") as handle:
        try:
            fcntl.flock(handle, (fcntl.LOCK_SH if shared else fcntl.LOCK_EX) | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        yield True


def speed_test_overlap(log_dir, started, ended):
    path = log_dir / "speed-active.json"
    if not path.exists():
        return False
    active = json.loads(path.read_text())
    start = active["started_epoch"]
    # A crashed test must not mark every future measurement as load-generated.
    end = active.get("ended_epoch") or start + 30
    return start <= ended and end >= started


def sample_once(log_dir, force_full=False):
    with lock(log_dir) as acquired:
        if not acquired:
            return {"skipped": "another_sample_or_report_running"}
        state_path = log_dir / "latest.json"
        previous = json.loads(state_path.read_text()) if state_path.exists() else {}
        now = time.time()
        boot = command(["/usr/sbin/sysctl", "-n", "kern.bootsessionuuid"], 2)["text"].strip()
        route = route_info()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            jobs = {name: pool.submit(ping, host) for name, host in
                    [("gateway", route.get("gateway")), ("cloudflare", "1.1.1.1"),
                     ("google", "8.8.8.8")]}
            wifi_job = pool.submit(wifi_info, route.get("interface"))
            sample = {"at": dt.datetime.fromtimestamp(now, TZ).isoformat(timespec="seconds"),
                      "epoch": round(now, 3), "boot": boot, "route": route,
                      "ping": {name: job.result() for name, job in jobs.items()},
                      "wifi": wifi_job.result()}
            loss = any(v.get("received", 0) < v.get("sent", 1) for v in sample["ping"].values())
            last_full = previous.get("last_full_epoch", 0)
            full = (force_full or not previous or now - last_full >= FULL_INTERVAL - 1
                    or now < last_full or previous.get("boot") != boot
                    or ((loss or previous.get("condition") != "healthy")
                        and now - last_full >= INTERVAL - 1))
            sample["full"] = full
            if full:
                details = network_details()
                sample.update(details)
                primary = details["dns_servers"][0] if details["dns_servers"] else None
                dns_jobs = {"public_udp": pool.submit(dns, "1.1.1.1"),
                            "public_tcp": pool.submit(dns, "1.1.1.1", True)}
                if primary:
                    dns_jobs["primary"] = pool.submit(dns, primary)
                web_jobs = {name: pool.submit(https, url) for name, url in HTTPS_TARGETS.items()}
                v6_job = pool.submit(https, HTTPS_TARGETS["apple"], True) if details["ipv6_available"] else None
                sample["dns"] = {name: job.result() for name, job in dns_jobs.items()}
                sample["https"] = {name: job.result() for name, job in web_jobs.items()}
                if v6_job:
                    sample["ipv6_https"] = v6_job.result()
        sample["speed_test_overlap"] = speed_test_overlap(log_dir, now, time.time())
        sample["condition"] = classify(sample)
        gap = now - previous.get("epoch", now)
        uninterrupted = previous.get("boot") == boot and 0 <= gap <= INTERVAL * 3
        sample["consecutive"] = (previous.get("consecutive", 0) + 1
                                 if uninterrupted and previous.get("condition") == sample["condition"] else 1)
        sample["last_full_epoch"] = now if full else previous.get("last_full_epoch", 0)
        events = transition_events(previous, sample)
        day = dt.datetime.fromtimestamp(now, TZ).date().isoformat()
        append_log(log_dir / ("samples-" + day + ".jsonl.gz"), sample)
        for event in events:
            append_log(log_dir / ("events-" + day + ".jsonl.gz"), {"at": sample["at"], **event})
        atomic_json(state_path, sample)
        return sample


def report(log_dir, hours):
    cutoff = time.time() - hours * 3600
    counts = {}
    latencies = {}
    failures = {}
    ping_stats = {}
    dns_stats = {}
    events = []
    count = 0
    first = last = None
    for path in sorted(log_dir.glob("samples-*.jsonl.gz")):
        day = dt.date.fromisoformat(path.name[8:18])
        if day < dt.datetime.fromtimestamp(cutoff, TZ).date():
            continue
        with gzip.open(path, "rt") as handle:
            for line in handle:
                row = json.loads(line)
                if row["epoch"] < cutoff:
                    continue
                count += 1
                first = first or row["at"]
                last = row["at"]
                condition = row["condition"]
                counts[condition] = counts.get(condition, 0) + 1
                for name, result in row.get("ping", {}).items():
                    item = ping_stats.setdefault(name, {"samples": 0, "sent": 0, "received": 0, "no_reply_samples": 0})
                    item["samples"] += 1
                    item["sent"] += result.get("sent", 0)
                    item["received"] += result.get("received", 0)
                    item["no_reply_samples"] += not result.get("ok")
                for name, result in row.get("dns", {}).items():
                    item = dns_stats.setdefault(name, {"samples": 0, "failures": 0, "max_ms": 0})
                    item["samples"] += 1
                    item["failures"] += not result.get("ok")
                    item["max_ms"] = max(item["max_ms"], result.get("ms") or 0)
                for name, result in row.get("https", {}).items():
                    failures[name] = failures.get(name, 0) + (not result["ok"])
                    if result.get("ok") and result.get("total_ms") is not None:
                        latencies.setdefault(name, []).append(result["total_ms"])
    for path in sorted(log_dir.glob("events-*.jsonl.gz")):
        day = dt.date.fromisoformat(path.name[7:17])
        if day < dt.datetime.fromtimestamp(cutoff, TZ).date():
            continue
        with gzip.open(path, "rt") as handle:
            for line in handle:
                event = json.loads(line)
                if dt.datetime.fromisoformat(event["at"]).timestamp() >= cutoff:
                    events.append(event)
    latest_path = log_dir / "latest.json"
    latest = json.loads(latest_path.read_text()) if latest_path.exists() else None
    age = round(time.time() - latest["epoch"], 1) if latest else None
    error_path = log_dir / "last-error.json"
    error = json.loads(error_path.read_text()) if error_path.exists() else None
    # Imported only for reports; normal 15-second checks remain independent.
    from speed_monitor import METHOD, recent_measurements
    all_speeds = recent_measurements(log_dir, cutoff)
    speeds = [row for row in all_speeds if row.get("method") == METHOD]
    speed_latest_path = log_dir / "speed-latest.json"
    speed_latest = json.loads(speed_latest_path.read_text()) if speed_latest_path.exists() else None
    throughput = {"samples": len(speeds), "latest": speed_latest,
                  "legacy_samples_excluded": len(all_speeds) - len(speeds),
                  "interval_seconds": 300, "daily_payload_limit_bytes": 1_000_000_000,
                  "failed_tests": sum(row.get("condition") == "transfer_failed" for row in speeds),
                  "relative_drop_tests": sum(row.get("condition") == "below_recent_baseline" for row in speeds)}
    for direction in ["download", "upload"]:
        values = [row[direction]["mbps"] for row in speeds if row.get(direction, {}).get("ok")]
        throughput[direction + "_mbps"] = ({"samples": len(values), "min": min(values),
            "median": statistics.median(values), "max": max(values)} if values else {"samples": 0})
    print(json.dumps({"samples": count, "first": first, "last": last,
                      "condition_counts": counts, "ping": ping_stats, "dns": dns_stats,
                      "throughput": throughput,
                      "https_transport_failures": failures,
                      "https_total_ms": {name: {"median": statistics.median(v),
                          "p95": sorted(v)[max(0, math.ceil(len(v)*.95)-1)], "max": max(v)}
                          for name, v in latencies.items()},
                      "recent_events": events[-20:], "latest": latest,
                      "last_sample_age_seconds": age,
                      "monitor_fresh": age is not None and 0 <= age < INTERVAL * 3,
                      "last_error": error,
                      "log_bytes": sum(p.stat().st_size for p in log_dir.glob("*.gz"))},
                     ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--hours", type=float, default=24)
    args = parser.parse_args()
    os.umask(0o077)
    if args.report:
        if args.hours <= 0:
            parser.error("--hours must be positive")
        with lock(args.log_dir, shared=True) as acquired, lock(args.log_dir, shared=True, name=".speed.lock") as speed_acquired:
            if not acquired or not speed_acquired:
                raise SystemExit("A sample is being written; retry in a few seconds.")
            report(args.log_dir, args.hours)
    else:
        try:
            result = sample_once(args.log_dir, args.full)
        except Exception as exc:
            args.log_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            atomic_json(args.log_dir / "last-error.json", {
                "at": dt.datetime.now(TZ).isoformat(timespec="seconds"),
                "epoch": time.time(), "error": type(exc).__name__,
                "message": str(exc)[:500]})
            raise
        if not args.once:
            print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
