"""Local authorization, bounded archival sync and static-data export."""

from __future__ import annotations

import argparse
import contextlib
import getpass
import json
import os
import re
import sys
import time
import webbrowser
from collections.abc import Sequence
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import duckdb

from health.archive import Archive, ObjectRef
from health.archive_index import ArchiveIndex
from health.archive_sync import ArchiveEngine
from health.auth import AuthError, GoogleHealthAuth
from health.backup import backup_database
from health.client import ApiError, HealthClient, RateLimited, RequestBudget, RequestCapExceeded
from health.endpoints import CATALOG, DAILY_ROLLUP
from health.oauth_loopback import authorize
from health.source_catalog import load_sources
from health.store import Store
from health.sync import SyncEngine
from health.web_export import export_web

_PROJECT = Path(__file__).resolve().parents[2]
_SCOPE_PREFIX = "https://www.googleapis.com/auth/googlehealth."
_REASONS = {
    "configuration": "引数または設定が不正です。health --help を確認してください。",
    "authorization": "認可を確認し、health auth を実行してください。",
    "oauth_port_unavailable": "認可用ポート8501が使用中です。使用中のアプリを終了して再実行してください。",
    "oauth_timeout": "認可が時間内に完了しませんでした。health auth を再実行してください。",
    "storage_error": "DB・バックアップ・原本の保存に失敗しました。保存先、空き容量、他のwriterを確認してください。",
    "rate_limited": "APIの要求上限に達しました。指定された秒数を待って再実行してください。",
    "request_cap": "今回の要求予算を使い切りました。再実行すると処理を継続します。",
    "permission_denied": "必要な読み取り権限が付与されていません。health auth で確認してください。",
    "failed": "取得または表示データへの変換に失敗しました。",
    "partial": "取得が完了していません。",
    "pending": "未取得です。",
    "unknown_history": "全履歴の取得範囲が確認できていません。",
    "unsupported": "確認済みの読み取り手段がありません。",
    "interrupted": "処理を中断しました。保存済みの原本は保持されています。",
    "internal_error": "処理を完了できませんでした。ローカルの設定と実装を確認してください。",
}


class _ArgumentsError(ValueError):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's default prints arbitrary argv values (including secrets).
        raise _ArgumentsError("invalid command arguments")


def _positive(value: str) -> int:
    try:
        result = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("positive integer required") from exc
    if result < 1:
        raise argparse.ArgumentTypeError("positive integer required")
    return result


def _history_date(value: str) -> date:
    try:
        result = date.fromisoformat(value)
        if result.isoformat() != value or result > date.today():
            raise ValueError
    except ValueError as exc:
        raise argparse.ArgumentTypeError("past or current ISO date required") from exc
    return result


def _parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="health", description="ローカルのGoogle Healthアーカイブと表示データを管理します。"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(os.environ.get("HEALTH_DATA_DIR", str(_PROJECT / "data"))),
    )
    parser.add_argument("--env-file", type=Path, default=os.environ.get("HEALTH_ENV_FILE"))
    commands = parser.add_subparsers(dest="command", required=True)
    auth = commands.add_parser("auth", help="ブラウザで読み取り権限を認可")
    auth.add_argument("--no-browser", action="store_true")
    sync = commands.add_parser("sync", help="原本と表示データを同期")
    sync.add_argument("--max-requests", type=_positive, default=200)
    sync.add_argument("--rescan", action="store_true")
    sync.add_argument("--history-start", type=_history_date)
    sync.add_argument(
        "--archive-only",
        action="store_true",
        help="表示用再集計を行わず、Google原本の全source・全page取得へ予算を使う",
    )
    hp_auth = commands.add_parser("auth-healthplanet", help="Health Planetの読み取り連携を認可")
    hp_auth.add_argument("--no-browser", action="store_true")
    hp_auth.add_argument("--begin", action="store_true", help="認可URLだけを発行")
    hp_auth.add_argument("--code-file", type=Path, help="ローカル保存した認可コードを交換")
    hp_sync = commands.add_parser("sync-healthplanet", help="Health Planetの原本と全測定を保存")
    hp_sync.add_argument("--history-start", type=_history_date, required=True)
    hp_sync.add_argument("--history-end", type=_history_date, default=date.today())
    hp_sync.add_argument("--max-requests", type=_positive, default=30)
    hp_sync.add_argument("--rescan", action="store_true")
    hp_sync.add_argument(
        "--endpoint",
        action="append",
        choices=("innerscan", "sphygmomanometer", "pedometer"),
        help="取得対象。省略時は全対象、複数指定可",
    )
    hp_sync.add_argument("--wait", action="store_true", help="指定区間の完了まで取得枠の回復を待つ")
    hp_sync.add_argument(
        "--export-dir", type=Path, help="各取得後に更新するローカルWebデータの保存先"
    )
    export = commands.add_parser("export-web", help="一貫したWebデータを生成")
    export.add_argument("--out-dir", type=Path, default=_PROJECT / "web" / "public" / "data")
    return parser


def exit_status(*, stopped: bool, incomplete: bool) -> int:
    return 1 if stopped else (2 if incomplete else 0)


def _error_reason(error: BaseException) -> str:
    if isinstance(error, AuthError):
        # Match only to choose a fixed explanation, never print the exception.
        text = str(error)
        if text.startswith("OAuth callback port ") and "is unavailable" in text:
            return "oauth_port_unavailable"
        if text == "Google Health authorization timed out; run health auth again":
            return "oauth_timeout"
        return "authorization"
    if isinstance(error, RateLimited):
        return "rate_limited"
    if isinstance(error, RequestCapExceeded):
        return "request_cap"
    if isinstance(error, (OSError, duckdb.Error)):
        return "storage_error"
    if isinstance(error, (ValueError, TypeError)):
        return "configuration"
    if isinstance(error, KeyboardInterrupt):
        return "interrupted"
    if isinstance(error, ApiError):
        return "failed"
    return "internal_error"


def _failure(stream_id, status, http_status=None) -> dict:
    return {
        "stream_id": stream_id,
        "status": status,
        "http_status": http_status,
        "reason": _REASONS.get(status, _REASONS["failed"]),
    }


@contextlib.contextmanager
def _open_store(data_dir: Path):
    path = data_dir / "health.duckdb"
    backup = backup_database(path)  # Must precede Store's schema/migration code.
    store = Store(path)
    try:
        yield store, backup is not None
    finally:
        store.close()


def _civil_date(value, *, today):
    if not isinstance(value, dict):
        return None
    parts = [value.get(key) for key in ("year", "month", "day")]
    if not all(type(part) is int for part in parts):
        return None
    try:
        result = date(*parts)
    except ValueError:
        return None
    return result if result <= today else None


def account_first_date(index, archive, *, today: date) -> date | None:
    """Read only saved successful Profile.membershipStartDate evidence.

    Official contract: https://developers.google.com/health/reference/rest/v4/Profile
    This does not fetch profile outside the shared API budget.
    """
    rows = index.con.execute(
        "SELECT p.sha256,p.object_path,p.byte_count FROM archive_pages p "
        "JOIN archive_attempts a ON a.id=p.attempt_id "
        "JOIN archive_sources s ON s.stream_id=a.stream_id "
        "WHERE json_extract_string(s.metadata,'$.data_type')='profile' "
        "AND json_extract_string(s.metadata,'$.preferred_method')='getProfile' "
        "AND a.representation='metadata' AND a.status IN ('complete','empty') "
        "AND p.http_status BETWEEN 200 AND 299 ORDER BY a.started_at DESC,a.id DESC,p.page_seq DESC"
    ).fetchall()
    for row in rows:
        payload = json.loads(archive.read(ObjectRef(*row)))
        result = (
            _civil_date(payload.get("membershipStartDate"), today=today)
            if isinstance(payload, dict)
            else None
        )
        if result is not None:
            return result
    return None


def _confirmed_starts(coverage, metric, today):
    confirmed = []
    for row in coverage:
        if (
            row["data_type"] != metric.data_type
            or row["representation"] == "legacy_json"
            or row["stream_id"].startswith("projection:")
        ):
            continue
        for interval in row.get("intervals", []):
            if interval.get("start") and interval.get("status", "complete") in {
                "complete",
                "empty",
            }:
                start = date.fromisoformat(interval["start"])
                if start <= today:
                    confirmed.append(start)
    return confirmed


def projection_history_floors(
    coverage, catalog, *, today: date, history_start: date | None = None
) -> dict[str, date]:
    """Explicit/confirmed request boundaries; an unknown start is never proof."""
    return {
        metric.name: history_start
        if history_start is not None
        else min(_confirmed_starts(coverage, metric, today), default=today - timedelta(days=6))
        for metric in catalog
    }


def _observed_source_starts(index, archive, sources, *, today):
    """Minimum observed civil dates, retaining uncertainty about older records.

    Derive using the catalog's official filter field and protobuf camelCase.
    Read one archived page at a time. Cache by immutable content hash and field
    in the existing archive_meta table, so repeated runs don't rescan bodies.
    """
    minima = {}
    for source in sources:
        if source.preferred_method != "list" or not source.filter_field:
            continue
        fields = [
            re.sub(r"_([a-z])", lambda match: match[1].upper(), part)
            for part in source.filter_field.split(".")
        ]
        refs = index.con.execute(
            "SELECT DISTINCT p.sha256,p.object_path,p.byte_count FROM archive_pages p "
            "JOIN archive_attempts a ON a.id=p.attempt_id WHERE a.stream_id=? "
            "AND p.http_status BETWEEN 200 AND 299 AND p.point_count IS NOT NULL ORDER BY p.sha256",
            [source.key],
        ).fetchall()
        for row in refs:
            cache_key = f"cli:observed-start:v1:{row[0]}:{source.filter_field}"
            saved = index.con.execute(
                "SELECT value FROM archive_meta WHERE key=?", [cache_key]
            ).fetchone()
            if saved:
                earliest = date.fromisoformat(saved[0]) if saved[0] else None
            else:
                payload = json.loads(archive.read(ObjectRef(*row)))
                points = payload.get("dataPoints", []) if isinstance(payload, dict) else []
                observed = []
                for point in points if isinstance(points, list) else []:
                    value = point
                    for field in fields:
                        value = value.get(field) if isinstance(value, dict) else None
                    if isinstance(value, dict) and "date" in value:
                        value = value["date"]
                    day = _civil_date(value, today=today)
                    if day is not None:
                        observed.append(day)
                earliest = min(observed, default=None)
                index.con.execute(
                    "INSERT INTO archive_meta VALUES (?,?) ON CONFLICT(key) DO NOTHING",
                    [cache_key, earliest.isoformat() if earliest else ""],
                )
            if earliest is not None:
                minima[source.data_type] = min(minima.get(source.data_type, earliest), earliest)
    return minima


def _projection_history(store, index, archive, sources, catalog, *, today, explicit):
    account = account_first_date(index, archive, today=today)
    coverage = index.coverage()
    observed = _observed_source_starts(index, archive, sources, today=today)
    tables = {
        "daily_series": store.series_stats().to_dict("records"),
        "intraday": store.intraday_stats().to_dict("records"),
        "sleep_sessions": store.sleep_stats().to_dict("records"),
    }
    policy = {}
    for metric in catalog:
        if explicit is not None:
            policy[metric.name] = {"start": explicit.isoformat(), "basis": "explicit"}
            continue
        candidates = [
            (day, "confirmed_range") for day in _confirmed_starts(coverage, metric, today)
        ]
        if account is not None:
            candidates.append((account, "account_profile"))
        if metric.data_type in observed:
            candidates.append((observed[metric.data_type], "source_observed"))
        for table in metric.storage_tables:
            for row in tables[table]:
                if row["n"] and (table == "sleep_sessions" or row["metric"] in metric.series_names):
                    candidates.append((row["first_date"].date(), "local_history"))
        day, basis = min(candidates, default=(today - timedelta(days=6), "unknown_history"))
        policy[metric.name] = {"start": day.isoformat(), "basis": basis}
    return policy


def _request_bounds(request) -> tuple[str | None, str | None]:
    if request.method == "POST":
        interval = (request.body or {}).get("range", {})
        values = [interval.get(key, {}).get("date", {}) for key in ("start", "end")]
        if all(all(key in value for key in ("year", "month", "day")) for value in values):
            return tuple(
                date(value["year"], value["month"], value["day"]).isoformat() for value in values
            )
    dates = re.findall(r'"(\d{4}-\d{2}-\d{2})"', request.params.get("filter", ""))
    return (dates[0], dates[1]) if len(dates) == 2 else (None, None)


class _ProjectionCapture:
    """Observe projection responses; commit their success only after typed save."""

    def __init__(self, archive, index, catalog):
        self.archive, self.index = archive, index
        self.active = {}
        self.metrics = {}
        for metric in catalog:
            method = "dailyRollUp" if metric.method == DAILY_ROLLUP else "reconcile"
            path = f"/v4/users/me/dataTypes/{metric.data_type}/dataPoints:{method}"
            self.metrics[("POST" if method == "dailyRollUp" else "GET", path)] = metric
            index.register(
                SimpleNamespace(
                    key=f"projection:{metric.name}",
                    data_type=metric.data_type,
                    label=metric.name,
                    preferred_method=method,
                    representation="aggregate" if method == "dailyRollUp" else "reconciled",
                )
            )

    def __call__(self, request, body: bytes, status: int) -> None:
        reference = self.archive.put(body)  # Before any decoding or typed parsing.
        metric = self.metrics[(request.method, request.path)]
        info = asdict(request)
        info["params"] = {key: value for key, value in request.params.items() if key != "pageToken"}
        start, end = _request_bounds(request)
        info.update(range_start=start, range_end=end)
        identity = json.dumps(info, sort_keys=True)
        current = self.active.get(metric.name)
        if current is None or current["identity"] != identity:
            if current is not None:
                self._finish(metric.name, "partial")
            attempt = self.index.start(
                f"projection:{metric.name}",
                info,
                "aggregate" if metric.method == DAILY_ROLLUP else "reconciled",
            )
            current = {
                "attempt": attempt,
                "identity": identity,
                "terminal": False,
                "status": status,
            }
            self.active[metric.name] = current
        point_count, terminal = None, False
        if 200 <= status < 300:
            try:
                payload = json.loads(body)
                key = "rollupDataPoints" if metric.method == DAILY_ROLLUP else "dataPoints"
                points = payload.get(key, []) if isinstance(payload, dict) else None
                if isinstance(points, list):
                    point_count = len(points)
                    terminal = not payload.get("nextPageToken")
            except (ValueError, UnicodeDecodeError):
                pass
        self.index.record_page(
            current["attempt"],
            self.index.page_count(current["attempt"]),
            reference,
            status,
            point_count,
        )
        current.update(terminal=terminal, status=status)

    def _finish(self, name, status):
        current = self.active[name]
        self.index.finish(
            current["attempt"], status, _REASONS.get(status), http_status=current["status"]
        )
        del self.active[name]

    def committed(self, metric, _progress_text):
        current = self.active.get(metric)
        if current is None or not current["terminal"]:
            raise ValueError("typed save did not have a terminal response")
        self.index.confirm_terminal(current["attempt"], next_page_token=None)
        status = "complete" if self.index.point_count(current["attempt"]) else "empty"
        self._finish(metric, status)

    def failures(self, failures):
        for failure in failures:
            if failure.metric in self.active:
                self._finish(
                    failure.metric, "permission_denied" if failure.status_code == 403 else "failed"
                )

    def finish_pending(self, status="partial"):
        for metric in list(self.active):
            self._finish(metric, status)


def _sync(args, auth, sources) -> tuple[int, dict]:
    tokens = auth.load_tokens()
    if not tokens:
        raise AuthError("authorization required")
    required = {scope for source in sources for scope in source.readonly_scopes}
    required.update(f"{_SCOPE_PREFIX}{metric.scope}.readonly" for metric in CATALOG)
    granted = set(str(tokens.get("scope", "")).split()) & required
    missing = sorted(required - granted)
    if missing:
        print("未付与の読み取りscope: " + " ".join(missing), file=sys.stderr)
    today = date.today()
    with _open_store(args.data_dir) as (store, backed_up):
        index = ArchiveIndex(store.con)
        archive = Archive(args.data_dir / "archive")
        index.import_legacy(archive)
        run = index.next_run()
        client = HealthClient(auth)
        account_start = account_first_date(index, archive, today=today)
        engine = ArchiveEngine(
            client,
            archive,
            index,
            sources,
            today=today,
            history_start=args.history_start or account_start,
            granted_scopes=granted,
        )
        capture = _ProjectionCapture(archive, index, CATALOG)
        allowed = [
            metric for metric in CATALOG if f"{_SCOPE_PREFIX}{metric.scope}.readonly" in granted
        ]
        denied = [metric for metric in CATALOG if metric not in allowed]
        failures = []
        for metric in denied:
            attempt = index.start(
                f"projection:{metric.name}",
                {},
                "aggregate" if metric.method == DAILY_ROLLUP else "reconciled",
            )
            index.finish(
                attempt, "permission_denied", _REASONS["permission_denied"], http_status=403
            )
            failures.append(_failure(f"projection:{metric.name}", "permission_denied", 403))
        budgets = {phase: {"limit": 0, "used": 0} for phase in ("archive", "projection")}
        order = (
            ("archive",)
            if args.archive_only
            else (("archive", "projection") if run % 2 else ("projection", "archive"))
        )
        used, stopped, retry_after = 0, None, None
        projection_report = None
        history = _projection_history(
            store, index, archive, sources, CATALOG, today=today, explicit=args.history_start
        )
        hit_cap = False
        for position, phase in enumerate(order):
            limit = (
                args.max_requests - used
                if len(order) == 1
                else ((args.max_requests + 1) // 2 if position == 0 else args.max_requests - used)
            )
            if limit <= 0:
                continue
            budget = RequestBudget(limit)
            budgets[phase]["limit"] = limit
            print(f"{phase}: 最大{limit} requests", file=sys.stderr)
            try:
                if phase == "archive":
                    report = engine.sync(budget, rescan=args.rescan)
                    reason = report.stopped_reason
                    hit_cap |= reason == "request_cap"
                    if reason and reason != "request_cap":
                        stopped = reason if reason in _REASONS else "failed"
                        retry_after = report.retry_after_s
                else:
                    history = _projection_history(
                        store,
                        index,
                        archive,
                        sources,
                        CATALOG,
                        today=today,
                        explicit=args.history_start,
                    )
                    floors = {
                        metric.name: date.fromisoformat(history[metric.name]["start"])
                        for metric in allowed
                    }
                    projection_catalog = allowed
                    if allowed:
                        # Advance only when this phase gets a budget. Otherwise cap=1
                        # can pin every projection run to the same first metric.
                        row = store.con.execute(
                            "SELECT value FROM archive_meta WHERE key = 'projection_cursor'"
                        ).fetchone()
                        cursor = int(row[0]) if row else 0
                        offset = cursor % len(allowed)
                        projection_catalog = allowed[offset:] + allowed[:offset]
                        store.con.execute(
                            "INSERT INTO archive_meta VALUES ('projection_cursor', ?) "
                            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                            [str(cursor + 1)],
                        )
                    client.response_observer = capture
                    projection_report = SyncEngine(
                        client,
                        store,
                        catalog=projection_catalog,
                        today=today,
                        environ={},
                        history_floors=floors,
                        budget=budget,
                    ).sync_all(progress_cb=capture.committed)
                    capture.failures(projection_report.failures)
                    failures.extend(
                        _failure(
                            f"projection:{failure.metric}",
                            "permission_denied" if failure.status_code == 403 else "failed",
                            failure.status_code,
                        )
                        for failure in projection_report.failures
                    )
                    hit_cap |= projection_report.stopped_early
                    if projection_report.paused:
                        stopped, retry_after = "rate_limited", projection_report.resume_in_s
            except (Exception, KeyboardInterrupt) as error:
                stopped = _error_reason(error)
                if isinstance(error, RateLimited):
                    retry_after = error.retry_after_s
                if stopped == "request_cap":
                    hit_cap, stopped = True, None
            finally:
                client.response_observer = None
                budgets[phase]["used"] = budget.used
                used += budget.used
                if phase == "projection":
                    try:
                        capture.finish_pending(
                            "rate_limited"
                            if stopped == "rate_limited"
                            else (
                                "storage_error"
                                if stopped == "storage_error"
                                else ("failed" if stopped else "partial")
                            )
                        )
                    except (OSError, duckdb.Error):
                        stopped = "storage_error"
            if stopped:
                break
        coverage = index.coverage()
        source_rows = [
            row for row in coverage if not row["stream_id"].startswith(("projection:", "legacy:"))
        ]
        remaining = sum(
            row["status"] not in {"complete", "empty"} or not row["history_complete"]
            for row in source_rows
        )
        failures.extend(
            _failure(row["stream_id"], row["status"], row["http_status"])
            for row in source_rows
            if row["status"] not in {"complete", "empty", "partial", "pending"}
        )
        projection_remaining = (
            sum(
                max(
                    projection_report.history_remaining.get(metric.name, 0),
                    int(store.get_sync_checkpoint(metric.name) is None),
                )
                for metric in allowed
            )
            if projection_report
            else len(allowed)
        )
        unknown_history = any(row["basis"] == "unknown_history" for row in history.values())
        incomplete = bool(
            remaining
            or failures
            or projection_remaining
            or hit_cap
            or unknown_history
            or (projection_report is None and allowed)
        )
        code = exit_status(stopped=stopped is not None, incomplete=incomplete)
        return code, {
            "command": "sync",
            "status": "stopped" if stopped else ("incomplete" if incomplete else "complete"),
            "run_number": run,
            "max_requests": args.max_requests,
            "requests_made": used,
            "budgets": budgets,
            "remaining": remaining,
            "projection_remaining": projection_remaining,
            "failures": sorted(failures, key=lambda row: row["stream_id"]),
            "missing_scopes": missing,
            "stopped_reason": stopped or ("request_cap" if hit_cap else None),
            "retry_after_s": retry_after,
            "backup_created": backed_up,
            "history_scope": "requested_ranges",
            "projection_history": history,
        }


def _healthplanet(args):
    from health.healthplanet import sync as sync_healthplanet
    from health.healthplanet_auth import HealthPlanetAuth

    auth = HealthPlanetAuth.from_env(args.data_dir, args.env_file)
    if args.command == "auth-healthplanet":
        if args.code_file:
            if args.begin:
                raise ValueError("choose begin or code file")
            code = args.code_file.read_text().strip()
        else:
            url = auth.begin_auth()
            print(f"Health Planetの連携を許可してください: {url}", file=sys.stderr, flush=True)
            if not args.no_browser:
                webbrowser.open(url)
            if args.begin:
                return 2, {"command": args.command, "status": "awaiting_authorization"}
            if not sys.stdin.isatty():
                raise AuthError("interactive terminal or local code file required")
            code = getpass.getpass("成功画面の認可コード（入力は非表示）: ")
        auth.complete_auth(code)
        return 0, {"command": args.command, "status": "complete"}
    first = True
    while True:
        result = sync_healthplanet(
            args.data_dir,
            auth,
            start=args.history_start,
            end=args.history_end,
            max_requests=args.max_requests,
            rescan=args.rescan,
            endpoints=args.endpoint,
        )
        if args.export_dir and (first or result["requests_made"]):
            with _open_store(args.data_dir) as (store, _):
                export_web(store, args.export_dir)
        first = False
        if (
            not args.wait
            or result["failures"]
            or result["stopped_reason"] not in {"request_cap", "rate_limited"}
        ):
            break
        print(
            json.dumps(result, ensure_ascii=False, allow_nan=False, sort_keys=True),
            file=sys.stderr,
            flush=True,
        )
        if result["stopped_reason"] == "rate_limited":
            time.sleep(max(1, result["retry_after_s"] or 3600) + 1)
    result["command"] = args.command
    return (0 if result["status"] == "available" else 2), result


def main(argv: Sequence[str] | None = None) -> int:
    command = None
    try:
        args = _parser().parse_args(argv)
        command = args.command
        if command in {"auth-healthplanet", "sync-healthplanet"}:
            code, summary = _healthplanet(args)
        elif command == "export-web":
            with _open_store(args.data_dir) as (store, backed_up):
                manifest = export_web(store, args.out_dir)
                summary = {
                    "command": command,
                    "status": "complete",
                    "backup_created": backed_up,
                    "generation": json.loads(manifest.read_text())["generation"],
                }
            code = 0
        else:
            sources = load_sources()
            scopes = " ".join(
                sorted({scope for source in sources for scope in source.readonly_scopes})
            )
            auth = GoogleHealthAuth.from_env(args.data_dir, args.env_file, scopes=scopes)
            if command == "auth":
                authorize(auth, open_browser=not args.no_browser)
                code, summary = 0, {"command": command, "status": "complete"}
            else:
                code, summary = _sync(args, auth, sources)
    except SystemExit as error:
        return int(error.code or 0)  # argparse help has already printed its text.
    except (Exception, KeyboardInterrupt) as error:
        reason = _error_reason(error)
        if command in {"auth-healthplanet", "sync-healthplanet"} and reason == "authorization":
            print(
                "Health Planetの設定と認可期限を確認し、health auth-healthplanet を実行してください。",
                file=sys.stderr,
            )
        else:
            print(_REASONS[reason], file=sys.stderr)
        code, summary = 1, {"command": command, "status": "stopped", "stopped_reason": reason}
    print(json.dumps(summary, ensure_ascii=False, allow_nan=False, sort_keys=True), flush=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
