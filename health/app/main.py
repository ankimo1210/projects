"""Streamlit entry: OAuth callback handling, navigation."""

import streamlit as st
from common import get_auth
from health.auth import AuthError


def main() -> None:
    st.set_page_config(page_title="Health", page_icon="🏃", layout="wide")
    try:
        auth = get_auth()
    except AuthError as exc:
        st.error(f"設定エラー: {exc}")
        st.stop()

    qp = st.query_params
    if "code" in qp or "error" in qp:
        try:
            auth.complete_auth(
                qp.get("code"),
                qp.get("state"),
                qp.get("error"),
                qp.get("error_description"),
            )
            st.success("Google Health と接続しました")
        except AuthError as exc:
            st.error(f"認証に失敗しました: {exc}")
        finally:
            # Authorization codes and OAuth errors are single-use and must not
            # remain in browser history after either outcome.
            st.query_params.clear()

    if auth.load_tokens() is None:
        st.title("Health ダッシュボード")
        st.markdown(f"[Google Health と接続する]({auth.begin_auth()})")
        st.caption(
            "Google Cloud の OAuth クライアント ID/Secret を "
            "health/.env に設定してから接続してください。"
        )
        st.stop()

    from views.activity_view import activity_page
    from views.body_view import body_page
    from views.heart_view import heart_page
    from views.inventory_view import inventory_page
    from views.overview_view import overview_page
    from views.sleep_view import sleep_page
    from views.sync_view import sync_page

    nav = st.navigation(
        {
            "ダッシュボード": [
                st.Page(overview_page, title="概要", icon="🏠", default=True),
                st.Page(sleep_page, title="睡眠", icon="😴"),
                st.Page(activity_page, title="活動", icon="👟"),
                st.Page(heart_page, title="心拍", icon="❤️"),
                st.Page(body_page, title="身体", icon="⚖️"),
            ],
            "管理": [
                st.Page(sync_page, title="同期", icon="🔄"),
                st.Page(inventory_page, title="データ棚卸し", icon="📋"),
            ],
        }
    )
    nav.run()


if __name__ == "__main__":
    main()
