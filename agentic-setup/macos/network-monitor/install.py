#!/usr/bin/env python3
"""Validate, back up, install and load this user's monitoring LaunchAgent."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import plistlib
import py_compile
import shutil
import subprocess
import sys
import tempfile

LABEL = "com.ankimo.network-monitor"
SOURCE = Path(__file__).resolve().parent
RUNTIME = Path.home() / "Library/Application Support/NetworkMonitor"
LOGS = Path.home() / "Library/Logs/NetworkMonitor"
PLIST = Path.home() / "Library/LaunchAgents" / (LABEL + ".plist")
PROFILES = [(LABEL, "network_monitor.py", 15),
            ("com.ankimo.network-speed", "speed_monitor.py", 300)]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args):
    return subprocess.run([str(v) for v in args], check=True, capture_output=True, text=True)


def install():
    if sys.platform != "darwin" or os.getuid() == 0:
        raise SystemExit("Run as the logged-in macOS user, without sudo.")
    os.umask(0o077)
    domain = "gui/" + str(os.getuid())
    run(["/bin/launchctl", "print", domain])
    jobs = []
    for label, script, interval in PROFILES:
        path = PLIST.parent / (label + ".plist")
        old_bytes = path.read_bytes() if path.exists() else None
        old = plistlib.loads(old_bytes) if old_bytes is not None else {}
        if old_bytes is not None and (old.get("Label") != label or str(RUNTIME / script) not in old.get("ProgramArguments", [])):
            raise SystemExit("STOP: existing plist is not owned by this monitor: " + str(path))
        current = subprocess.run(["/bin/launchctl", "print", domain + "/" + label], capture_output=True, text=True)
        if current.returncode != 0 and "Could not find service" not in current.stderr:
            raise SystemExit("STOP: unexpected launchctl error: " + current.stderr[:400])
        if current.returncode == 0 and old_bytes is None:
            raise SystemExit("STOP: label already loaded without the expected plist: " + label)
        jobs.append({"label": label, "script": script, "interval": interval,
                     "path": path, "old_bytes": old_bytes, "old": old,
                     "loaded": current.returncode == 0})
    # Keep Homebrew's stable entry point; a versioned Cellar path can disappear
    # during a later Python upgrade/cleanup.
    python = Path(shutil.which("python3") or sys.executable)
    run([python, "-c", "import sys; assert sys.version_info >= (3, 9)"])
    for binary in [python, Path("/usr/bin/swiftc"), Path("/usr/bin/dig"), Path("/usr/bin/curl"), Path("/sbin/ping")]:
        if not binary.is_file():
            raise SystemExit("Missing dependency: " + str(binary))
    with tempfile.TemporaryDirectory(prefix="network-monitor-install-") as temporary:
        stage = Path(temporary)
        for filename in ["network_monitor.py", "speed_monitor.py"]:
            py_compile.compile(str(SOURCE / filename), cfile=str(stage / (filename + "c")), doraise=True)
            shutil.copy2(SOURCE / filename, stage / filename)
        run(["/usr/bin/swiftc", SOURCE / "wifi_info.swift", "-O", "-o", stage / "wifi-info"])
        json.loads(run([stage / "wifi-info"]).stdout)
        run([python, stage / "network_monitor.py", "--once", "--full", "--log-dir", stage / "preflight-logs"])
        preflight = json.loads((stage / "preflight-logs/latest.json").read_text())
        if not all(key in preflight for key in ["at", "condition", "ping", "https", "wifi"]):
            raise SystemExit("STOP: live preflight did not produce a complete record")
        for job in jobs:
            desired = {**job["old"], "Label": job["label"],
                       "ProgramArguments": [str(python), str(RUNTIME / job["script"]), "--once", "--log-dir", str(LOGS)],
                       "RunAtLoad": True, "StartInterval": job["interval"],
                       "ProcessType": "Standard" if job["script"] == "speed_monitor.py" else "Background",
                       "LowPriorityIO": job["script"] != "speed_monitor.py",
                       "Nice": 0 if job["script"] == "speed_monitor.py" else 10,
                       "StandardOutPath": "/dev/null", "StandardErrorPath": "/dev/null"}
            new_bytes = plistlib.dumps(desired, sort_keys=False)
            assert plistlib.loads(new_bytes) == desired
            staged_plist = stage / job["path"].name
            staged_plist.write_bytes(new_bytes)
            run(["/usr/bin/plutil", "-lint", staged_plist])
            job.update(desired=desired, staged_plist=staged_plist, changed=job["old"] != desired)
            actual = job["path"].read_bytes() if job["path"].exists() else None
            if actual != job["old_bytes"]:
                raise SystemExit("STOP: configuration changed during preflight")
        RUNTIME.mkdir(parents=True, exist_ok=True, mode=0o700)
        LOGS.mkdir(parents=True, exist_ok=True, mode=0o700)
        PLIST.parent.mkdir(parents=True, exist_ok=True)
        backup = RUNTIME / "backups" / datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup.mkdir(parents=True, mode=0o700)
        manifest = {"plist_was_absent": {j["label"]: j["old_bytes"] is None for j in jobs}, "backups": {}}
        for path in [*(j["path"] for j in jobs), RUNTIME / "network_monitor.py",
                     RUNTIME / "speed_monitor.py", RUNTIME / "wifi-info"]:
            if path.exists():
                destination = backup / path.name
                shutil.copy2(path, destination)
                if sha(path) != sha(destination):
                    raise SystemExit("STOP: backup verification failed: " + str(path))
                manifest["backups"][str(path)] = sha(path)
        (backup / "manifest.json").write_text(json.dumps(manifest, indent=2))
        # Prechecks, compilation, syntax validation and backups all passed.
        for job in jobs:
            if job["loaded"] and job["changed"]:
                run(["/bin/launchctl", "bootout", domain + "/" + job["label"]])
        copies = [(SOURCE / "speed_monitor.py", RUNTIME / "speed_monitor.py"),
                  (SOURCE / "network_monitor.py", RUNTIME / "network_monitor.py"),
                  (stage / "wifi-info", RUNTIME / "wifi-info")]
        copies += [(j["staged_plist"], j["path"]) for j in jobs if j["changed"]]
        for source, destination in copies:
            staged = destination.with_name(destination.name + ".installing")
            shutil.copy2(source, staged)
            os.chmod(staged, 0o700 if destination.name == "wifi-info" else 0o600)
            if sha(source) != sha(staged):
                raise SystemExit("STOP: staged copy verification failed")
            os.replace(staged, destination)
        for job in jobs:
            assert plistlib.loads(job["path"].read_bytes()) == job["desired"]
            run(["/usr/bin/plutil", "-lint", job["path"]])
            if not job["loaded"] or job["changed"]:
                run(["/bin/launchctl", "bootstrap", domain, job["path"]])
            loaded = run(["/bin/launchctl", "print", domain + "/" + job["label"]]).stdout
            if str(RUNTIME / job["script"]) not in loaded or str(job["interval"]) + " seconds" not in loaded:
                raise SystemExit("STOP: loaded job does not match expected program/interval")
        print(json.dumps({"jobs": [{"label": j["label"], "interval_seconds": j["interval"]} for j in jobs],
                          "runtime": str(RUNTIME), "logs": str(LOGS),
                          "verified_backup": str(backup), "loaded": True}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    install()
