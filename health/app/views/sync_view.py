"""Sync page: on-demand sync with progress, token status."""
from datetime import datetime

import streamlit as st

from health.auth import AuthError
from health.client import FitbitClient
from health.sync import SyncEngine

from common import get_auth, get_store


def sync_page() -> None:
    st.title("同期")
    auth = get_auth()
    store = get_store()

    last = st.session_state.pop("last_sync_report", None)
    if last is not None:
        if last["paused"]:
            mins = (last["resume_in_s"] or 3600) // 60 + 1
            st.warning(f"レート制限に達しました。進捗は保存済みです。約 {mins} 分後にもう一度同期してください。")
        else:
            st.success("同期が完了しました")

    tokens = auth.load_tokens()
    exp = datetime.fromtimestamp(tokens["expires_at"]).strftime("%H:%M") if tokens else "-"
    st.caption(f"アクセストークン有効期限: {exp} / スコープ: {tokens.get('scope', '') if tokens else '-'}")

    states = store.sync_states()
    if not states.empty:
        st.dataframe(states, use_container_width=True)

    if st.button("Fitbit からデータを同期", type="primary"):
        try:
            client = FitbitClient(auth)
            engine = SyncEngine(client, store)
            with st.status("同期中...", expanded=True) as status:
                report = engine.sync_all(
                    progress_cb=lambda metric, msg: status.write(f"{metric}: {msg}"))
        except AuthError:
            st.error("認証が失効しています。health/data/tokens.json を削除してから、"
                     "アプリを開き直して Fitbit と再接続してください。")
        else:
            st.session_state["last_sync_report"] = {
                "paused": report.paused, "resume_in_s": report.resume_in_s}
            st.rerun()
