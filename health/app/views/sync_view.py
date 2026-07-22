"""Sync page: bounded on-demand Google Health sync and connection status."""

from datetime import datetime, timedelta

import streamlit as st
from common import get_auth, get_store
from health.auth import AuthError
from health.client import ApiError, HealthClient
from health.endpoints import PayloadError
from health.sync import MAX_REQUESTS_PER_RUN, SyncEngine


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
        st.warning(
            f"1回の実行上限（{MAX_REQUESTS_PER_RUN} requests）に達したため停止しました。"
            "完了chunkは保存済みです。もう一度同期すると未完了chunkから再開します。"
        )
    else:
        st.success(f"同期が完了しました（{last['requests_made']} requests）")


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


def _run_sync(auth) -> None:
    try:
        engine = SyncEngine(HealthClient(auth), get_store())
        with st.status("同期中...", expanded=True) as status:
            report = engine.sync_all(
                progress_cb=lambda metric, message: status.write(f"{metric}: {message}")
            )
    except AuthError as exc:
        st.error(f"Google Health の認証が失効しています: {exc}。再接続してください。")
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
            "このchunkは保存せず、既存データを維持して停止しました。"
        )
    else:
        st.cache_data.clear()  # cached loaders must observe the fresh rows
        st.session_state["last_sync_report"] = {
            "paused": report.paused,
            "resume_in_s": report.resume_in_s,
            "stopped_early": report.stopped_early,
            "requests_made": report.requests_made,
        }
        st.rerun()


def sync_page() -> None:
    st.title("同期")
    auth = get_auth()
    _show_last_report()
    _token_panel(auth)

    if st.button("Google Health からデータを同期", type="primary"):
        _run_sync(auth)

    states = get_store().sync_states()
    if not states.empty:
        st.subheader("メトリクス別の同期状態")
        st.dataframe(
            states,
            use_container_width=True,
            hide_index=True,
            column_config={
                "metric": st.column_config.TextColumn("メトリクス"),
                "last_synced_date": st.column_config.DateColumn("最終同期日"),
                "status": st.column_config.TextColumn("状態"),
            },
        )

    st.divider()
    if st.button("接続解除（トークンを削除。次回は再認可が必要です）"):
        auth.forget_tokens()
        st.cache_data.clear()
        st.rerun()
