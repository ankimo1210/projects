"""Streamlit entry: OAuth callback handling, navigation."""
import streamlit as st

from health.auth import AuthError

from common import get_auth


def main() -> None:
    st.set_page_config(page_title="Health", page_icon="🏃", layout="wide")
    try:
        auth = get_auth()
    except AuthError as exc:
        st.error(f"設定エラー: {exc}")
        st.stop()

    qp = st.query_params
    if "code" in qp and auth.load_tokens() is None:
        try:
            auth.complete_auth(qp["code"], qp.get("state", ""))
            st.query_params.clear()
            st.success("Fitbit と接続しました")
        except AuthError as exc:
            st.error(f"認証に失敗しました: {exc}")

    if auth.load_tokens() is None:
        st.title("Health ダッシュボード")
        st.markdown(f"[Fitbit と接続する]({auth.begin_auth()})")
        st.caption("dev.fitbit.com の個人アプリ (Client ID/Secret) を health/.env に設定してから接続してください。")
        st.stop()

    from views.body_view import body_page
    from views.heart_view import heart_page
    from views.inventory_view import inventory_page
    from views.overview_view import overview_page
    from views.sleep_view import sleep_page
    from views.activity_view import activity_page
    from views.sync_view import sync_page

    nav = st.navigation({
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
    })
    nav.run()


if __name__ == "__main__":
    main()
