"""Sync page: bounded on-demand Google Health sync and connection status."""

from datetime import datetime

import streamlit as st
from common import get_auth, get_store
from health.auth import AuthError
from health.client import ApiError, HealthClient
from health.endpoints import PayloadError
from health.sync import SyncEngine


def sync_page() -> None:
    st.title("同期")
    auth = get_auth()
    store = get_store()

    last = st.session_state.pop("last_sync_report", None)
    if last is not None:
        if last["paused"]:
            seconds = last["resume_in_s"] or 60
            st.warning(
                "Google Health のレート制限（429）で停止しました。"
                f"完了chunkは保存済みです。約 {seconds // 60 + 1} 分後に再開できます。"
            )
        elif last["stopped_early"]:
            st.warning(
                f"1回の上限（{last['requests_made']} requests）で停止しました。"
                "もう一度同期すると未完了chunkから再開します。"
            )
        else:
            st.success(f"同期が完了しました（{last['requests_made']} requests）")

    tokens = auth.load_tokens()
    if tokens:
        access_expiry = datetime.fromtimestamp(tokens["expires_at"]).strftime("%Y-%m-%d %H:%M")
        st.caption(f"アクセストークン有効期限: {access_expiry}")
        refresh_days = auth.refresh_expires_in_days()
        if refresh_days is not None:
            st.caption(f"refresh token 残り: {max(0, refresh_days):.1f} 日")
        st.caption(f"認可スコープ: {tokens.get('scope', '-')}")

    states = store.sync_states()
    if not states.empty:
        st.dataframe(states, use_container_width=True)

    if st.button("Google Health からデータを同期", type="primary"):
        try:
            engine = SyncEngine(HealthClient(auth), store)
            with st.status("同期中...", expanded=True) as status:
                report = engine.sync_all(
                    progress_cb=lambda metric, message: status.write(f"{metric}: {message}")
                )
        except AuthError as exc:
            st.error(f"Google Health の認証が失効しています: {exc}。再接続してください。")
        except ApiError as exc:
            st.error(f"Google Health API エラー（HTTP {exc.status_code}）: {exc.message}")
        except PayloadError as exc:
            st.error(
                f"{exc.metric} の応答を解釈できません: {exc.detail}。"
                "このchunkは保存せず、既存データを維持して停止しました。"
            )
        else:
            st.session_state["last_sync_report"] = {
                "paused": report.paused,
                "resume_in_s": report.resume_in_s,
                "stopped_early": report.stopped_early,
                "requests_made": report.requests_made,
            }
            st.rerun()

    if st.button("Google Health を再接続"):
        auth.forget_tokens()
        st.rerun()
