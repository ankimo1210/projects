#!/usr/bin/env python3
"""Install only the read-only router collector; never reload existing probes."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import plistlib
import py_compile
import shutil
import subprocess
import tempfile
import time

SOURCE = Path(__file__).resolve().parent
RUNTIME = Path.home() / "Library/Application Support/NetworkMonitor"
LOGS = Path.home() / "Library/Logs/NetworkMonitor"
LABEL = "com.ankimo.network-router"
PLIST = Path.home() / "Library/LaunchAgents" / (LABEL + ".plist")
METADATA = RUNTIME / "router-component-manifest.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args):
    return subprocess.run([str(v) for v in args], capture_output=True, text=True, check=True)


def install(prepare):
    if os.uname().sysname != "Darwin" or os.getuid() == 0:
        raise SystemExit("Run as the logged-in macOS user, without sudo.")
    os.umask(0o077)
    domain = "gui/" + str(os.getuid())
    run(["/bin/launchctl", "print", domain])
    old_bytes = PLIST.read_bytes() if PLIST.exists() else None
    old = plistlib.loads(old_bytes) if old_bytes else {}
    if old and (old.get("Label") != LABEL or str(RUNTIME / "router_monitor.py") not in old.get("ProgramArguments", [])):
        raise SystemExit("STOP: existing plist is not owned by this collector")
    loaded = subprocess.run(["/bin/launchctl", "print", domain + "/" + LABEL], capture_output=True, text=True)
    if loaded.returncode and "Could not find service" not in loaded.stderr:
        raise SystemExit("STOP: unexpected launchctl failure")
    if not loaded.returncode and old_bytes is None:
        raise SystemExit("STOP: collector label loaded without expected plist")
    helper = RUNTIME / "router-keychain"
    source_hash = sha(SOURCE / "router_keychain.swift")
    metadata = json.loads(METADATA.read_text()) if METADATA.exists() else None
    if helper.exists() and (not metadata or metadata.get("swift_source_sha256") != source_hash
                            or metadata.get("helper_sha256") != sha(helper)):
        raise SystemExit("STOP: existing credential helper differs; preserve its Keychain identity")
    code_changed = (not (RUNTIME / "router_monitor.py").exists()
                    or sha(RUNTIME / "router_monitor.py") != sha(SOURCE / "router_monitor.py"))
    if prepare and loaded.returncode == 0 and code_changed:
        raise SystemExit("STOP: collector is running; use the full validated installer to update it")
    if not prepare:
        from router_monitor import load_config
        config_before = (RUNTIME / "router-monitor.json").read_bytes()
        load_config(RUNTIME / "router-monitor.json")
        if not helper.exists() or json.loads(run([helper, "status"]).stdout) != {"exists": True}:
            raise SystemExit("STOP: router credential is not provisioned")
    with tempfile.TemporaryDirectory(prefix="router-monitor-install-") as temporary:
        stage = Path(temporary)
        py_compile.compile(str(SOURCE / "router_monitor.py"), cfile=str(stage / "router_monitor.pyc"), doraise=True)
        shutil.copy2(SOURCE / "router_monitor.py", stage / "router_monitor.py")
        shutil.copy2(RUNTIME / "network_monitor.py", stage / "network_monitor.py")
        if not helper.exists():
            run(["/usr/bin/swiftc", SOURCE / "router_keychain.swift", "-O", "-o", stage / "router-keychain"])
            json.loads(run([stage / "router-keychain", "status"]).stdout)
        desired = {**old, "Label": LABEL,
                   "ProgramArguments": ["/opt/homebrew/bin/python3", str(RUNTIME / "router_monitor.py")],
                   "RunAtLoad": True, "KeepAlive": True, "ThrottleInterval": 60,
                   "ProcessType": "Standard", "Nice": 10, "LowPriorityIO": False,
                   "StandardOutPath": "/dev/null", "StandardErrorPath": "/dev/null"}
        staged_plist = stage / PLIST.name
        staged_plist.write_bytes(plistlib.dumps(desired, sort_keys=False))
        assert plistlib.loads(staged_plist.read_bytes()) == desired
        run(["/usr/bin/plutil", "-lint", staged_plist])
        if not prepare:
            preflight = json.loads(run(["/opt/homebrew/bin/python3", stage / "router_monitor.py",
                                        "--once", "--log-dir", stage / "preflight-logs"]).stdout)
            if preflight.get("condition") != "collected" or "log_error" in preflight:
                raise SystemExit("STOP: read-only live preflight failed: " + preflight.get("error", "log_fetch_failed"))
            if (RUNTIME / "router-monitor.json").read_bytes() != config_before:
                raise SystemExit("STOP: router collector configuration changed during preflight")
        actual = PLIST.read_bytes() if PLIST.exists() else None
        if actual != old_bytes:
            raise SystemExit("STOP: configuration changed during preflight")
        RUNTIME.mkdir(parents=True, exist_ok=True, mode=0o700)
        LOGS.mkdir(parents=True, exist_ok=True, mode=0o700)
        backup = RUNTIME / "backups" / ("router-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
        backup.mkdir(parents=True, mode=0o700)
        paths = [PLIST, helper, RUNTIME / "router_monitor.py", RUNTIME / "router-monitor.json", METADATA]
        manifest = {"absent": [], "sha256": {}}
        for path in paths:
            if not path.exists():
                manifest["absent"].append(str(path))
                continue
            shutil.copy2(path, backup / path.name)
            if sha(path) != sha(backup / path.name):
                raise SystemExit("STOP: backup verification failed")
            manifest["sha256"][str(path)] = sha(path)
        (backup / "manifest.json").write_text(json.dumps(manifest, indent=2))
        copies = [(stage / "router_monitor.py", RUNTIME / "router_monitor.py")]
        if not helper.exists():
            copies.append((stage / "router-keychain", helper))
        changed = old != desired
        if not prepare and changed:
            copies.append((staged_plist, PLIST))
        if not prepare and (changed or code_changed) and loaded.returncode == 0:
            run(["/bin/launchctl", "bootout", domain + "/" + LABEL])
            # bootout returns before a persistent process has fully left launchd.
            deadline = time.monotonic() + 15
            while True:
                status = subprocess.run(["/bin/launchctl", "print", domain + "/" + LABEL],
                                        capture_output=True, text=True)
                if status.returncode and "Could not find service" in status.stderr:
                    break
                if status.returncode or time.monotonic() >= deadline:
                    raise SystemExit("STOP: collector did not finish unloading")
                time.sleep(0.25)
        for source, destination in copies:
            staged = destination.with_name(destination.name + ".installing")
            shutil.copy2(source, staged)
            os.chmod(staged, 0o700 if destination == helper else 0o600)
            if sha(source) != sha(staged):
                raise SystemExit("STOP: staged copy verification failed")
            os.replace(staged, destination)
        new_metadata = {"swift_source_sha256": source_hash, "helper_sha256": sha(helper)}
        temporary_metadata = METADATA.with_suffix(".installing")
        temporary_metadata.write_text(json.dumps(new_metadata, indent=2))
        assert json.loads(temporary_metadata.read_text()) == new_metadata
        os.chmod(temporary_metadata, 0o600)
        os.replace(temporary_metadata, METADATA)
        if not prepare:
            assert plistlib.loads(PLIST.read_bytes()) == desired
            run(["/usr/bin/plutil", "-lint", PLIST])
            if changed or code_changed or loaded.returncode:
                run(["/bin/launchctl", "bootstrap", domain, PLIST])
            status = run(["/bin/launchctl", "print", domain + "/" + LABEL]).stdout
            if str(RUNTIME / "router_monitor.py") not in status:
                raise SystemExit("STOP: loaded program mismatch")
        print(json.dumps({"prepared": True, "loaded": not prepare,
                          "verified_backup": str(backup), "existing_probes_reloaded": False}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true", help="Install helper/code only, without starting a job")
    install(parser.parse_args().prepare)
