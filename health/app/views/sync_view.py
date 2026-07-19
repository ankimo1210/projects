"""Sync page: on-demand sync with progress, token status."""
from datetime import datetime

import streamlit as st

from health.client import FitbitClient
from health.sync import SyncEngine

from common import get_auth, get_store


def sync_page() -> None:
    st.title("同期")
    auth = get_auth()
    store = get_store()

    tokens = auth.load_tokens()
    exp = datetime.fromtimestamp(tokens["expires_at"]).strftime("%H:%M") if tokens else "-"
    st.caption(f"アクセストークン有効期限: {exp} / スコープ: {tokens.get('scope', '') if tokens else '-'}")

    states = store.sync_states()
    if not states.empty:
        st.dataframe(states, use_container_width=True)

    if st.button("Fitbit からデータを同期", type="primary"):
        client = FitbitClient(auth)
        engine = SyncEngine(client, store)
        with st.status("同期中...", expanded=True) as status:
            report = engine.sync_all(
                progress_cb=lambda metric, msg: status.write(f"{metric}: {msg}"))
        if report.paused:
            mins = (report.resume_in_s or 3600) // 60 + 1
            st.warning(f"レート制限に達しました。進捗は保存済みです。約 {mins} 分後にもう一度同期してください。")
        else:
            st.success("同期が完了しました")
        st.rerun()
