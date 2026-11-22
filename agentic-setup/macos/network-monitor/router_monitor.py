#!/usr/bin/env python3
"""Read-only BUFFALO telemetry. Authentication is the only permitted submission."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import hmac
import html
import http.cookiejar
import ipaddress
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time
import urllib.parse
import urllib.request

from network_monitor import TZ, append_log, atomic_json, lock, route_info

RUNTIME = Path.home() / "Library/Application Support/NetworkMonitor"
DEFAULT_LOGS = Path.home() / "Library/Logs/NetworkMonitor"
CONFIG = RUNTIME / "router-monitor.json"
INTERVAL = 60
LOG_INTERVAL = 300
GET_PATHS = {"/cgi-bin/cgi?req=twz", "/cgi-bin/cgi?req=frm&frm=packet.html",
             "/cgi-bin/cgi?req=frm&frm=log_disp.html", "/cgi-bin/cgi?req=twz&frm=logout.html"}
LOG_CATEGORIES = {"DHCPC", "NTP", "SYSTEM", "WIRED", "WIRELESS", "BOOT", "PPP",
                  "NAT", "FILTER", "FIREWALL", "CONFIGURE"}


class MonitorError(Exception):
    pass


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def attrs(value):
    return {m[0].lower(): html.unescape(next(v for v in m[1:] if v != ""))
            for m in re.findall(r'''([\w-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))''', value)
            if any(m[1:])}


def plain(value):
    return " ".join(html.unescape(re.sub(r"<[^>]*>", " ", value)).split())


def rates(value):
    match = re.fullmatch(r"([\d.]+)\s*([KMG]?)bps", str(value), re.I)
    return (round(float(match[1]) * {"": 1, "K": 1000, "M": 1000000,
                                  "G": 1000000000}[match[2].upper()] / 1000000, 6)
            if match else None)


def packet_counters(page):
    found = re.search(r'<input\b[^>]*\bid="packet_main_data"[^>]*\bvalue="([\s\S]*?)"', page, re.I)
    if not found:
        raise MonitorError("packet_page_unrecognized")
    content = html.unescape(found[1])
    result = {}
    for row in re.findall(r"<tr\b[^>]*>([\s\S]*?)</tr>", content, re.I):
        values = [plain(v) for v in re.findall(r"<td\b[^>]*>([\s\S]*?)</td>", row, re.I)]
        numbers = [int(v) for v in values if v.isdigit()]
        if len(numbers) != 4:
            continue
        if "label_label_wan1_packet_main" in row:
            name = "wan"
        elif "label_t13_packet_main" in row or "2.4" in plain(row) or "band2g" in row:
            name = "wifi_2g"
        elif "label_t12_packet_main" in row or "5 GHz" in plain(row) or "band5g" in row:
            name = "wifi_5g"
        else:
            continue
        result[name] = dict(zip(["tx_ok", "tx_error", "rx_ok", "rx_error"], numbers))
    if set(result) != {"wan", "wifi_2g", "wifi_5g"}:
        raise MonitorError("packet_counters_unrecognized")
    return result


def counter_changes(previous, current):
    changes = {}
    for name, values in current.items():
        before = previous.get(name)
        if before and all(values[k] >= before[k] for k in values):
            changes[name] = {k: values[k] - before[k] for k in values}
        elif before:
            changes[name] = {"reset_or_wrap": True}
    return changes


def gateway_mac_hash(gateway):
    result = subprocess.run(["/usr/sbin/arp", "-n", gateway], capture_output=True,
                            text=True, timeout=2)
    match = re.search(r"\bat ((?:[0-9a-f]{1,2}:){5}[0-9a-f]{1,2})\b", result.stdout, re.I)
    if not match:
        raise MonitorError("gateway_identity_unavailable")
    mac = ":".join(part.zfill(2) for part in match[1].lower().split(":"))
    return digest(mac)


def load_config(path):
    config = json.loads(path.read_text())
    if (config.get("schema") != 1 or config.get("host") != "192.168.11.1"
            or config.get("model") != "WXR-5950AX12"
            or any(not re.fullmatch(r"[0-9a-f]{64}", config.get(k, ""))
                   for k in ["gateway_mac_sha256", "public_key_sha256", "privacy_key"])):
        raise MonitorError("invalid_configuration")
    if path.stat().st_mode & 0o077:
        raise MonitorError("configuration_permissions")
    return config


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise MonitorError("redirect_refused")


class Router:
    def __init__(self, config):
        self.config = config
        self.base = "http://" + config["host"]
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                                                 urllib.request.HTTPCookieProcessor(self.cookies), NoRedirect())
        self.anonymous = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        self.authenticated = False
        self.next_login = 0.0
        self.ids_key = bytes.fromhex(config["privacy_key"])
        self.identity_check = None

    def device_id(self, mac):
        return hmac.new(self.ids_key, mac.lower().encode(), hashlib.sha256).hexdigest()[:12]

    def request(self, path, data=None):
        readonly_json = bool(re.fullmatch(
            r"/cgi-bin/cgi\?req=fnc&fnc=%24\{get_json_param\((?:DEVICE|DEVCTRL),\d+\)\}", path))
        login = path == "/cgi-bin/cgi?req=inp&res=login.html"
        if not ((data is None and path in GET_PATHS) or (data is not None and (readonly_json or login))):
            raise MonitorError("write_endpoint_refused")
        headers = {"User-Agent": "NetworkMonitor/1.0", "Referer": self.base + "/cgi-bin/cgi?req=twz"}
        encoded = None
        if data is not None:
            encoded = urllib.parse.urlencode(data).encode()
            headers.update({"Content-Type": "application/x-www-form-urlencoded", "Origin": self.base})
        req = urllib.request.Request(self.base + path, data=encoded, headers=headers)
        with self.opener.open(req, timeout=4) as response:
            payload = response.read(1000001)
            if len(payload) > 1000000:
                raise MonitorError("response_limit")
        return payload.decode("utf-8", errors="replace")

    def json(self, category):
        return json.loads(self.request("/cgi-bin/cgi?req=fnc&fnc=%24{get_json_param(" + category
                                       + "," + str(time.time_ns() // 1000000) + ")}", {}))

    def guard(self):
        route = route_info()
        if not route.get("ok") or route.get("gateway") != self.config["host"]:
            raise MonitorError("different_network")
        try:
            mac_hash = gateway_mac_hash(self.config["host"])
        except MonitorError as exc:
            if str(exc) != "gateway_identity_unavailable":
                raise
            # Some execution environments cannot inspect the host's ARP cache.
            # Verify the pinned RSA key anonymously before sending any session cookie.
            req = urllib.request.Request(self.base + "/cgi-bin/cgi?req=twz")
            with self.anonymous.open(req, timeout=4) as response:
                page = response.read(1000001).decode("utf-8", errors="replace")
            modulus = re.search(r'''\bmodulus\s*=\s*["']([0-9a-fA-F]+)["']''', page)
            if len(page) > 1000000 or not modulus or digest(modulus[1].lower()) != self.config["public_key_sha256"]:
                raise MonitorError("router_key_changed")
            self.identity_check = "pinned_public_key"
            return
        if mac_hash != self.config["gateway_mac_sha256"]:
            raise MonitorError("different_router")
        self.identity_check = "pinned_gateway_mac"

    def login(self):
        if time.monotonic() < self.next_login:
            raise MonitorError("authentication_backoff")
        # Failed/lost sessions must not cause a login attempt every minute.
        self.next_login = time.monotonic() + 900
        self.guard()
        if self.json("DEVICE").get("MODEL") != self.config["model"]:
            raise MonitorError("different_router_model")
        page = self.request("/cgi-bin/cgi?req=twz")
        modulus = re.search(r'''\bmodulus\s*=\s*["']([0-9a-fA-F]+)["']''', page)
        exponent = re.search(r'''\bexponent\s*=\s*["']?(\d+)''', page)
        if not modulus or not exponent or digest(modulus[1].lower()) != self.config["public_key_sha256"]:
            raise MonitorError("router_key_changed")
        inputs = [attrs(v) for v in re.findall(r"<input\b[^>]*>", page, re.I)]
        hidden = {v["name"]: v.get("value", "") for v in inputs if v.get("type") == "hidden"}
        if set(hidden) != {"sWebSessionnum", "sWebSessionid"}:
            raise MonitorError("login_page_unrecognized")
        result = subprocess.run([str(RUNTIME / "router-keychain"), "payload"],
                                input=json.dumps({"modulus": modulus[1], "exponent": exponent[1]}),
                                capture_output=True, text=True, timeout=5)
        if result.returncode:
            raise MonitorError("keychain_unavailable")
        payload = json.loads(result.stdout)
        if set(payload) != {"username", "encrypted"} or payload["username"] != "admin":
            raise MonitorError("credential_payload_unrecognized")
        self.request("/cgi-bin/cgi?req=inp&res=login.html",
                     {"airstation_uname": payload["username"], "encrypted": payload["encrypted"], **hidden})
        self.authenticated = True

    def sanitize(self, message):
        message = re.sub(r"\b(?:[0-9a-f]{2}[:-]){5}[0-9a-f]{2}\b",
                         lambda m: "[device:" + self.device_id(m[0].replace("-", ":")) + "]",
                         message, flags=re.I)
        message = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[IP]", message)
        message = re.sub(r"(?<!\w)[0-9a-f]*:[0-9a-f:]+(?:%\w+)?", "[IPv6]", message, flags=re.I)
        message = re.sub(r"Buffalo-[AG]-[\w-]+", "[SSID]", message, flags=re.I)
        message = re.sub(r"\b(?:pass(?:word)?|secret|token|sWebSession\w*)\s*[:=]\s*\S+",
                         "[credential]", message, flags=re.I)
        return message[:1200]

    def logout(self):
        if self.authenticated:
            try:
                self.guard()
                self.request("/cgi-bin/cgi?req=twz&frm=logout.html")
            except Exception:
                pass
            self.authenticated = False

    def logs(self):
        page = self.request("/cgi-bin/cgi?req=frm&frm=log_disp.html")
        rows = re.findall(r"<tr\b[^>]*>\s*<td>(\d{4}/\d{2}/\d{2}[^<]*)</td>\s*"
                          r"<td>([^<]*)</td>\s*<td>([\s\S]*?)</tr>", page, re.I)
        if not rows:
            raise MonitorError("log_page_unrecognized")
        return [{"router_time": at, "category": category, "message": self.sanitize(plain(message)),
                 "id": digest(at + category + message)}
                for at, category, message in rows if category in LOG_CATEGORIES]

    def collect(self):
        self.guard()
        if not self.authenticated:
            self.login()
        try:
            devices = self.json("DEVCTRL")
            if not isinstance(devices.get("DEVICE"), list):
                raise MonitorError("device_page_unrecognized")
            packets = packet_counters(self.request("/cgi-bin/cgi?req=frm&frm=packet.html"))
        except Exception:
            self.authenticated = False
            raise
        active = [v for v in devices["DEVICE"] if v.get("MAC") and v.get("ALIVE") is True]
        return {"identity_check": self.identity_check,
                "aggregate_up_mbps": rates(devices.get("UP")),
                "aggregate_down_mbps": rates(devices.get("DOWN")),
                "connected": len(active), "wireless_connected": sum(v.get("WIRELESS") is True for v in active),
                "devices": [{"id": self.device_id(v["MAC"]), "wireless": v.get("WIRELESS") is True,
                             "up_mbps": rates(v.get("UP")), "down_mbps": rates(v.get("DOWN"))}
                            for v in active], "router_reported_counters": packets}


def sample_once(router, log_dir):
    with lock(log_dir, name=".router.lock") as acquired:
        if not acquired:
            return {"skipped": "already_running"}
        started = time.time()
        state_path = log_dir / "router-latest.json"
        previous = json.loads(state_path.read_text()) if state_path.exists() else {}
        sample = {"at": dt.datetime.fromtimestamp(started, TZ).isoformat(timespec="seconds"),
                  "epoch": started, "condition": "unavailable", "configuration_writes": False}
        try:
            sample.update(router.collect())
            sample["condition"] = "collected"
            sample["counter_changes"] = counter_changes(previous.get("router_reported_counters", {}),
                                                         sample["router_reported_counters"])
            if started - previous.get("last_log_epoch", 0) >= LOG_INTERVAL:
                try:
                    rows = router.logs()
                    seen_path = log_dir / "router-log-seen.json"
                    seen = json.loads(seen_path.read_text()) if seen_path.exists() else []
                    seen_ids = set(seen)
                    new = [row for row in reversed(rows) if row["id"] not in seen_ids]
                    day = dt.datetime.fromtimestamp(started, TZ).date().isoformat()
                    for row in new:
                        append_log(log_dir / ("router-events-" + day + ".jsonl.gz"),
                                   {"collected_at": sample["at"], **row})
                    atomic_json(seen_path, [row["id"] for row in rows][:4096])
                    sample.update(last_log_epoch=started, new_log_entries=len(new))
                except Exception as exc:
                    sample["log_error"] = type(exc).__name__
            sample.setdefault("last_log_epoch", previous.get("last_log_epoch", 0))
        except Exception as exc:
            # Never include HTTP content, credentials, cookies, subprocess output, or URLs.
            sample["error"] = str(exc) if isinstance(exc, MonitorError) else type(exc).__name__
            sample["last_log_epoch"] = previous.get("last_log_epoch", 0)
        sample["collection_seconds"] = round(time.time() - started, 3)
        day = dt.datetime.fromtimestamp(started, TZ).date().isoformat()
        append_log(log_dir / ("router-samples-" + day + ".jsonl.gz"), sample)
        atomic_json(state_path, sample)
        return sample


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--log-dir", type=Path, default=DEFAULT_LOGS)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    os.umask(0o077)
    router = Router(load_config(args.config))
    stopping = False

    def stop(signum, frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        while not stopping:
            started = time.monotonic()
            result = sample_once(router, args.log_dir)
            if args.once:
                print(json.dumps(result, ensure_ascii=False))
                break
            # A config-only collector never controls the network or retries at high frequency.
            while not stopping and time.monotonic() - started < INTERVAL:
                time.sleep(1)
    finally:
        router.logout()


if __name__ == "__main__":
    main()
