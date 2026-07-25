"""Sync page: bounded on-demand Google Health sync and connection status."""

from datetime import datetime, timedelta

import streamlit as st
from common import get_auth, get_store
from health.auth import AuthError
from health.client import ApiError, HealthClient
from health.endpoints import PayloadError
from health.sync import MAX_REQUESTS_PER_RUN, SyncEngine

_FAILURE_KIND_LABELS = {"api": "API エラー", "payload": "データ解析エラー"}


def _show_last_report() -> None:
    last = st.session_state.pop("last_sync_report", None)
    if last is None:
        return
    if last["paused"]:
        resume_in = last["resume_in_s"] or 60
        minutes = max(1, -(-resume_in // 60))
        resume_at = (datetime.now() + timedelta(seconds=resume_in)).strftime("%H:%M")
        st.warning(
            "Google Health のレート制限（429）で停止しました。完了chunkは保存済みです。"
            f"{resume_at} 頃（約 {minutes} 分後）にもう一度同期してください。"
        )
    elif last["stopped_early"]:
        # `max_requests` reflects the cap the user actually selected for this
        # run; `.get` falls back to the module default so a report dict from
        # an older session shape (before this field existed) cannot raise.
        cap = last.get("max_requests", MAX_REQUESTS_PER_RUN)
        st.warning(
            f"1回の実行上限（{cap} requests）に達したため停止しました。"
            "完了chunkは保存済みです。もう一度同期すると未完了chunkから再開します。"
        )
    else:
        st.success(f"同期が完了しました（{last['requests_made']} requests）")

    remaining = last.get("history_remaining", 0)
    if remaining:
        st.info(
            f"履歴の残りは約 {remaining} chunk です。もう一度同期すると古い期間へ遡ります。"
            "直近のデータは全メトリクスで取得済みです。"
        )
    for failure in last.get("failures", []):
        kind_label = _FAILURE_KIND_LABELS.get(failure["kind"], failure["kind"])
        detail_parts = [kind_label]
        if failure["status_code"]:
            detail_parts.append(f"HTTP {failure['status_code']}")
        detail_parts.append(failure["message"])
        st.warning(
            f"{failure['metric']}: 取得できませんでした（{' '.join(detail_parts)}）。"
            "他のメトリクスは同期済みです。"
        )


def _token_panel(auth) -> None:
    tokens = auth.load_tokens()
    if not tokens:
        return
    access_expiry = datetime.fromtimestamp(tokens["expires_at"]).strftime("%Y-%m-%d %H:%M")
    st.caption(f"アクセストークン有効期限: {access_expiry}")
    refresh_days = auth.refresh_expires_in_days()
    if refresh_days is not None:
        if refresh_days <= 2:
            st.warning(
                f"refresh token の残りが約 {max(0, refresh_days):.1f} 日です。"
                "失効すると再接続が必要になります。"
            )
        else:
            st.caption(f"refresh token 残り: {refresh_days:.1f} 日")
    st.caption(f"認可スコープ: {tokens.get('scope', '-')}")


CAP_OPTIONS = {"200 requests（既定）": 200, "500 requests": 500, "1000 requests": 1000}


def _run_sync(auth, max_requests: int) -> None:
    try:
        engine = SyncEngine(HealthClient(auth), get_store(), max_requests=max_requests)
        with st.status("同期中...", expanded=True) as status:
            report = engine.sync_all(
                progress_cb=lambda metric, message: status.write(f"{metric}: {message}")
            )
    except AuthError as exc:
        st.error(f"Google Health の認証が失効しています: {exc}。再接続してください。")
    # ApiError / PayloadError are unreachable through this call today:
    # SyncEngine._guarded() catches both per metric and records them in
    # SyncReport.failures (rendered by _show_last_report below), letting the
    # run continue with the remaining metrics instead of raising. These two
    # handlers are kept as defence in depth in case a future code path calls
    # into the engine below _guarded (e.g. a direct chunk fetch), so the copy
    # must stay accurate for that case rather than describing today's
    # per-metric isolation, which never reaches here.
    except ApiError as exc:
        st.error(f"Google Health API エラー（HTTP {exc.status_code}）: {exc.message}")
        if exc.status_code == 403:
            st.caption(
                "スコープ不足か API 未有効化の可能性があります。"
                "health/README.md の OAuth 設定を確認してください。"
            )
    except PayloadError as exc:
        st.error(
            f"{exc.metric} の応答を解釈できません: {exc.detail}。"
            "ここまでに完了したchunkは保存済みです。もう一度同期してください。"
        )
    else:
        st.session_state["last_sync_report"] = {
            "paused": report.paused,
            "resume_in_s": report.resume_in_s,
            "stopped_early": report.stopped_early,
            "requests_made": report.requests_made,
            "max_requests": max_requests,
            "history_remaining": sum(report.history_remaining.values()),
            "failures": [
                {
                    "metric": f.metric,
                    "kind": f.kind,
                    "status_code": f.status_code,
                    "message": f.message,
                }
                for f in report.failures
            ],
        }
        st.rerun()
    finally:
        # The engine commits one completed chunk at a time. A later API or
        # payload error can therefore follow real DB changes, so invalidate
        # cached frames on every outcome once a sync attempt has started.
        st.cache_data.clear()
        get_store().checkpoint()


def sync_page() -> None:
    st.title("同期")
    auth = get_auth()
    _show_last_report()
    _token_panel(auth)

    label = st.selectbox("1回の同期の上限", list(CAP_OPTIONS), index=0)
    if st.button("Google Health からデータを同期", type="primary"):
        _run_sync(auth, CAP_OPTIONS[label])

    states = get_store().sync_states()
    if not states.empty:
        states = states.copy()
        states["status"] = states["status"].replace({"ok": "完了", "in_progress": "途中"})
        st.subheader("メトリクス別の同期状態")
        st.dataframe(
            states,
            width="stretch",
            hide_index=True,
            column_config={
                "metric": st.column_config.TextColumn("メトリクス"),
                "last_synced_date": st.column_config.DateColumn("最終同期日"),
                "status": st.column_config.TextColumn("状態"),
                "backfilled_from": st.column_config.DateColumn("履歴開始日"),
            },
        )

    st.divider()
    if st.button("Google Health を再接続（保存トークンを破棄して再認可）"):
        auth.forget_tokens()
        st.cache_data.clear()
        st.rerun()
