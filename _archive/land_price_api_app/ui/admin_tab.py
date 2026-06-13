"""
ui/admin_tab.py
Admin タブ: API 疎通確認・データ同期・DB 管理。
"""

import logging

import api_client
import db
import modeling
import pandas as pd
import streamlit as st
import sync_public_notice as sync
import sync_trade_prices as sync_trade
from collect_listings_batch import run_import_urls
from collect_search_results import run_search_import
from config import PROCESSED_DIR, RAW_DIR, get_logger
from recompute_listing_features import run_recompute
from recompute_market_features import run_market_feature_backfill

logger = get_logger(__name__)


# ログをキャプチャして画面表示するためのハンドラ
class _StreamlitLogHandler(logging.Handler):
    def __init__(self, container):
        super().__init__()
        self._container = container
        self._logs: list[str] = []

    def emit(self, record):
        msg = self.format(record)
        self._logs.append(msg)
        self._container.code("\n".join(self._logs[-60:]), language="")  # 最新60行


def render_admin_tab(conn) -> None:
    st.header("⚙ Admin")

    # ---------- DB 統計 ----------
    st.subheader("DB 状態")
    stats = db.get_stats(conn)
    c1, c2, c3 = st.columns(3)
    c1.metric("総レコード数", f"{stats['total_records']:,}")
    c2.metric("格納済み年度数", len(stats["available_years"]))
    c3.metric("年度一覧", ", ".join(str(y) for y in stats["available_years"]) or "なし")

    if stats["year_counts"]:
        st.dataframe(
            pd.DataFrame(stats["year_counts"].items(), columns=["年度", "件数"]),
            use_container_width=False,
        )

    st.markdown("---")

    # ---------- API 疎通確認 ----------
    st.subheader("API スモークテスト")
    smoke_year = st.number_input("テスト年度", value=2026, min_value=2000, max_value=2030, step=1)

    if st.button("🔌 スモークテスト実行"):
        with st.spinner("テスト中..."):
            results = {}
            results["APIキー"] = api_client.smoke_test_api_key()
            results["XIT002 (都市リスト)"] = api_client.smoke_test_xit002()
            results["XPT002 (タイルデータ)"] = api_client.smoke_test_xpt002(year=smoke_year)
            results["DuckDB 書込確認"] = db.smoke_test_db()

        for name, ok in results.items():
            if ok:
                st.success(f"✓ {name}")
            else:
                st.error(f"✗ {name}")

    st.markdown("---")

    # ---------- データ同期 ----------
    st.subheader("データ同期")
    st.info(
        "⚠ 全国同期（z=13）は数万タイルを走査するため数時間かかります。"
        " まずは都道府県を指定した部分同期を試してください。"
    )

    col1, col2, col3, col4 = st.columns(4)
    sync_year = col1.number_input(
        "同期年度", value=2026, min_value=2000, max_value=2030, step=1, key="sync_year"
    )
    sync_z = col2.selectbox("ズームレベル", [13, 14], index=0, key="sync_z")
    sync_pref = col3.text_input("都道府県コード (空=全国)", placeholder="例: 13", key="sync_pref")
    sync_overwrite = col4.checkbox("上書き取得", value=False, key="sync_overwrite")

    log_container = st.empty()

    if st.button("▶ 同期開始", type="primary"):
        pref = sync_pref.strip() or None
        label = f"都道府県 {pref}" if pref else "全国"
        st.warning(f"{label} year={sync_year} の同期を開始します...")

        # ログキャプチャ設定
        handler = _StreamlitLogHandler(log_container)
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)

        try:
            with st.spinner("同期中..."):
                df = sync.sync_public_notice_year(
                    year=int(sync_year),
                    z=int(sync_z),
                    overwrite=bool(sync_overwrite),
                    prefecture_code=pref,
                    conn=conn,
                )
            if df.empty:
                st.warning(
                    f"year={sync_year} のデータが 0 件でした。"
                    f" API から未公開の可能性があります。year={sync_year - 1} をお試しください。"
                )
            else:
                st.success(f"✓ 同期完了: {len(df):,} 件 (year={sync_year})")
                st.cache_data.clear()
                st.rerun()
        except Exception as exc:
            st.error(f"同期エラー: {exc}")
        finally:
            root_logger.removeHandler(handler)

    st.markdown("---")

    # ---------- 年度範囲バッチ同期 ----------
    st.subheader("年度範囲バッチ同期")
    st.caption("複数年を一括取得します。都道府県を指定すると対象タイルが絞られ高速化されます。")

    b1, b2, b3, b4 = st.columns(4)
    batch_pref = b1.text_input("都道府県コード", placeholder="例: 47", key="batch_pref")
    batch_year_start = b2.number_input(
        "開始年", value=2010, min_value=2000, max_value=2030, step=1, key="batch_year_start"
    )
    batch_year_end = b3.number_input(
        "終了年", value=2026, min_value=2000, max_value=2030, step=1, key="batch_year_end"
    )
    batch_overwrite = b4.checkbox("上書き取得", value=False, key="batch_overwrite")

    if st.button("▶ バッチ同期開始", type="primary", key="batch_sync_btn"):
        pref = batch_pref.strip() or None
        years_to_sync = list(range(int(batch_year_start), int(batch_year_end) + 1))

        if not years_to_sync:
            st.error("終了年は開始年以上を指定してください。")
        else:
            label = f"都道府県 {pref}" if pref else "全国"
            st.info(
                f"{label} の {batch_year_start}〜{batch_year_end} 年を同期します（{len(years_to_sync)} 年分）"
            )

            progress_bar = st.progress(0)
            status_text = st.empty()
            batch_log = st.empty()
            log_lines: list[str] = []

            for i, yr in enumerate(years_to_sync):
                status_text.text(f"同期中: {yr}年 ({i + 1}/{len(years_to_sync)})")
                try:
                    yr_df = sync.sync_public_notice_year(
                        year=yr,
                        z=13,
                        overwrite=bool(batch_overwrite),
                        prefecture_code=pref,
                        conn=conn,
                    )
                    count = len(yr_df) if yr_df is not None and not yr_df.empty else 0
                    log_lines.append(f"✓ {yr}年: {count:,} 件")
                except Exception as exc:
                    log_lines.append(f"✗ {yr}年: {exc}")

                progress_bar.progress((i + 1) / len(years_to_sync))
                batch_log.code("\n".join(log_lines), language="")

            status_text.success(f"バッチ同期完了（{len(years_to_sync)} 年分処理）")
            st.cache_data.clear()
            st.rerun()

    st.markdown("---")

    # ---------- 取引価格同期 (XIT001) ----------
    st.subheader("取引価格同期 (XIT001)")
    st.caption("都道府県・年・四半期を指定して不動産取引価格データを取得します。")

    t1, t2, t3, t4 = st.columns(4)
    trade_pref = t1.text_input("都道府県コード", placeholder="例: 47", key="trade_sync_pref")
    trade_year = t2.number_input(
        "年", value=2024, min_value=2000, max_value=2030, step=1, key="trade_sync_year"
    )
    trade_quarter = t3.selectbox(
        "四半期", ["全四半期", "Q1", "Q2", "Q3", "Q4"], index=0, key="trade_sync_quarter"
    )
    trade_overwrite = t4.checkbox("上書き取得", value=False, key="trade_sync_overwrite")

    if st.button("▶ 取引価格同期開始", type="primary", key="trade_sync_btn"):
        pref = trade_pref.strip()
        if not pref:
            st.error("都道府県コードを入力してください。")
        else:
            qmap = {"全四半期": None, "Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}
            q_arg = qmap[trade_quarter]
            label = f"都道府県 {pref} / {trade_year}年" + (f" {trade_quarter}" if q_arg else "")
            st.info(f"{label} の同期を開始します...")

            trade_log = st.empty()
            trade_lines: list[str] = []
            quarters_to_run = [q_arg] if q_arg else [1, 2, 3, 4]
            prog = st.progress(0)

            for i, q in enumerate(quarters_to_run):
                trade_lines.append(f"取得中: Q{q}...")
                trade_log.code("\n".join(trade_lines), language="")
                try:
                    df_q = sync_trade.sync_trade_quarter(
                        pref=pref,
                        year=int(trade_year),
                        quarter=q,
                        overwrite=bool(trade_overwrite),
                        conn=conn,
                    )
                    count = len(df_q) if df_q is not None and not df_q.empty else 0
                    trade_lines[-1] = f"✓ Q{q}: {count:,} 件"
                except Exception as exc:
                    trade_lines[-1] = f"✗ Q{q}: {exc}"
                trade_log.code("\n".join(trade_lines), language="")
                prog.progress((i + 1) / len(quarters_to_run))

            st.success("取引価格同期完了")
            st.cache_data.clear()
            st.rerun()

    st.markdown("---")

    # ---------- 取引価格ジオコーディング ----------
    st.subheader("取引価格 座標付与（ジオコーディング）")
    st.caption(
        "取引価格データは緯度・経度が未設定のため、近傍検索が機能しません。"
        "国土地理院APIを使って市区町村・地区名から座標を付与します。"
    )

    ungeocoded_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT DISTINCT prefecture_name, city_name, district_name
            FROM trade_prices
            WHERE lat IS NULL AND city_name IS NOT NULL
        )
        """
    ).fetchone()[0]
    geocoded_count = conn.execute(
        "SELECT COUNT(*) FROM trade_prices WHERE lat IS NOT NULL"
    ).fetchone()[0]
    total_trade = conn.execute("SELECT COUNT(*) FROM trade_prices").fetchone()[0]

    gc1, gc2, gc3 = st.columns(3)
    gc1.metric("全取引件数", f"{total_trade:,}")
    gc2.metric("座標付き", f"{geocoded_count:,}")
    gc3.metric("未ジオコーディング地点数", f"{ungeocoded_count:,}")

    geo_limit = st.number_input(
        "処理件数上限（ユニーク地点数）",
        min_value=10,
        max_value=5000,
        value=200,
        step=50,
        key="geo_limit",
    )
    geo_sleep = st.number_input(
        "API間隔（秒）", min_value=0.1, max_value=2.0, value=0.3, step=0.1, key="geo_sleep"
    )

    if st.button("▶ ジオコーディング開始", type="primary", key="geocode_btn"):
        from geocode_trade_prices import run_geocoding

        geo_prog = st.progress(0.0)
        geo_status = st.empty()

        def _cb(done: int, total: int, address: str) -> None:
            if total > 0:
                geo_prog.progress(min(done / total, 1.0))
            geo_status.caption(f"{done}/{total} — {address}")

        with st.spinner("ジオコーディング実行中..."):
            result = run_geocoding(
                limit=int(geo_limit), sleep_sec=float(geo_sleep), progress_cb=_cb
            )

        geo_prog.progress(1.0)
        st.success(f"完了: 成功 {result['done']} 件 / 失敗 {result['failed']} 件")
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.subheader("掲載物件特徴量の再計算")
    r1, r2 = st.columns(2)
    rec_limit = r1.number_input(
        "再計算件数", min_value=1, max_value=5000, value=100, step=50, key="recompute_limit"
    )
    rec_stale = r2.number_input(
        "再計算TTL(日)", min_value=0, max_value=365, value=7, step=1, key="recompute_stale"
    )

    if st.button("▶ 掲載物件特徴量を再計算", type="primary", key="recompute_listing_btn"):
        prog = st.progress(0.0)
        status = st.empty()

        def _cb(done: int, total: int, listing_id: str) -> None:
            if total > 0:
                prog.progress(min(done / total, 1.0))
            status.caption(f"{done}/{total} — {listing_id}")

        with st.spinner("再計算中..."):
            result = run_recompute(limit=int(rec_limit), stale_days=int(rec_stale), progress_cb=_cb)
        prog.progress(1.0)
        st.success(f"完了: 成功 {result['done']} 件 / 失敗 {result['failed']} 件")
        st.cache_data.clear()

    st.markdown("---")
    st.subheader("市場地点への特徴量付与")
    m1, m2, m3 = st.columns(3)
    market_dataset = m1.selectbox("対象", ["public_notice", "trade"], key="market_feature_dataset")
    market_year = m2.number_input(
        "対象年 (0=全体)", min_value=0, max_value=2030, value=0, step=1, key="market_feature_year"
    )
    market_limit = m3.number_input(
        "件数上限", min_value=1, max_value=20000, value=500, step=100, key="market_feature_limit"
    )

    if st.button("▶ 市場地点へ特徴量付与", type="primary", key="market_feature_btn"):
        with st.spinner("特徴量付与中..."):
            result = run_market_feature_backfill(
                market_dataset,
                year=int(market_year) if int(market_year) > 0 else None,
                limit=int(market_limit),
            )
        st.success(f"完了: 成功 {result['done']} 件 / 失敗 {result['failed']} 件")
        st.cache_data.clear()

    st.markdown("---")
    st.subheader("価格モデル学習")
    model_year = st.number_input(
        "学習年 (0=全体)", min_value=0, max_value=2030, value=0, step=1, key="model_train_year"
    )
    model_limit = st.number_input(
        "学習件数上限",
        min_value=100,
        max_value=50000,
        value=10000,
        step=500,
        key="model_train_limit",
    )

    if st.button("▶ 線形モデルを学習", type="primary", key="train_model_btn"):
        with st.spinner("学習中..."):
            df_train = modeling.prepare_public_notice_training_data(
                conn,
                year=int(model_year) if int(model_year) > 0 else None,
                limit=int(model_limit),
            )
            if df_train.empty:
                st.warning("学習データがありません。先に市場地点へ特徴量付与を実行してください。")
            else:
                model = modeling.fit_linear_public_notice_model(df_train)
                path = modeling.save_model(model)
                st.success(
                    f"保存完了: {path.name} / rows={model['row_count']} / rmse_log={model['rmse_log']:.4f}"
                )

    st.markdown("---")
    st.subheader("楽待 検索URL収集")
    st.caption("検索結果URLから詳細URLを抽出し、そのまま掲載物件取込と特徴量計算まで実行します。")
    sr1, sr2 = st.columns(2)
    search_region_label = sr1.text_input(
        "地域ラベル",
        placeholder="例: 沖縄県 一棟アパート",
        key="search_import_region",
    )
    search_url = sr2.text_input(
        "楽待検索結果URL",
        placeholder="https://www.rakumachi.jp/syuuekibukken/area/...",
        key="search_import_url",
    )
    sr3, sr4, sr5, sr6 = st.columns(4)
    max_pages = sr3.number_input(
        "最大ページ数", min_value=1, max_value=50, value=3, step=1, key="search_import_pages"
    )
    max_listings = sr4.number_input(
        "最大物件数", min_value=1, max_value=500, value=60, step=10, key="search_import_listings"
    )
    search_sleep = sr5.number_input(
        "取込間隔(秒)",
        min_value=0.0,
        max_value=10.0,
        value=1.5,
        step=0.5,
        key="search_import_sleep",
    )
    compute_features = sr6.checkbox("特徴量まで計算", value=True, key="search_import_features")

    if st.button("▶ 検索結果URLから収集して取込", type="primary", key="search_import_btn"):
        if not search_url.strip():
            st.warning("検索結果URLを入力してください。")
        else:
            progress = st.progress(0.0)
            status = st.empty()
            detail = st.empty()
            log_box = st.empty()
            log_lines: list[str] = []

            def _fmt_elapsed(sec: float | None) -> str:
                if sec is None:
                    return ""
                sec = float(sec)
                if sec >= 60:
                    return f"{int(sec) // 60}m{int(sec) % 60:02d}s"
                return f"{sec:.1f}s"

            def _progress_cb(payload: dict[str, object]) -> None:
                stage = str(payload.get("stage") or "")
                event = str(payload.get("event") or "")
                batch_elapsed = payload.get("batch_elapsed_sec")
                elapsed_str = (
                    f" | 経過 {_fmt_elapsed(batch_elapsed)}" if batch_elapsed is not None else ""
                )
                if stage == "collect":
                    page_no = int(payload.get("page_no") or 0)
                    max_pages_local = int(payload.get("max_pages") or max_pages)
                    collected_urls_local = int(payload.get("collected_urls") or 0)
                    progress.progress(min(page_no / max(max_pages_local, 1) * 0.25, 0.25))
                    if event == "page_start":
                        status.caption(f"収集中: page {page_no}/{max_pages_local}")
                        detail.text(str(payload.get("current_url") or ""))
                    elif event == "page_done":
                        new_count = int(payload.get("page_new") or 0)
                        log_lines.append(
                            f"[収集] page {page_no}: +{new_count} 件 / total {collected_urls_local} 件"
                        )
                        log_box.code("\n".join(log_lines[-12:]), language="")
                elif stage == "import":
                    total = int(payload.get("total") or 0)
                    done = int(payload.get("done") or 0)
                    failed = int(payload.get("failed") or 0)
                    ratio = (done + failed) / max(total, 1) if total else 0.0
                    progress.progress(0.25 + ratio * 0.45)
                    url_elapsed = payload.get("url_elapsed_sec")
                    url_elapsed_str = (
                        f" ({_fmt_elapsed(url_elapsed)})" if url_elapsed is not None else ""
                    )
                    if event == "phase_start":
                        status.caption(f"取込開始: 0/{total}")
                    elif event == "start":
                        status.caption(
                            f"取込中: 成功 {done} / 失敗 {failed} / total {total}{elapsed_str}"
                        )
                        detail.text(str(payload.get("url") or ""))
                    elif event == "success":
                        property_name = str(payload.get("property_name") or "—")
                        status.caption(
                            f"取込中: 成功 {done} / 失敗 {failed} / total {total}{elapsed_str}"
                        )
                        log_lines.append(f"[取込]{url_elapsed_str} {property_name}")
                        log_box.code("\n".join(log_lines[-12:]), language="")
                    elif event == "failed":
                        status.caption(
                            f"取込中: 成功 {done} / 失敗 {failed} / total {total}{elapsed_str}"
                        )
                        error_detail = str(payload.get("error") or "")
                        log_lines.append(
                            f"[取込失敗]{url_elapsed_str} {payload.get('url')} — {error_detail}"
                        )
                        log_box.code("\n".join(log_lines[-12:]), language="")
                elif stage == "features":
                    total = int(payload.get("total") or 0)
                    done = int(payload.get("done") or 0)
                    ratio = done / max(total, 1) if total else 0.0
                    progress.progress(0.70 + ratio * 0.30)
                    if event == "phase_start":
                        status.caption(f"特徴量計算開始: 0/{total}")
                    elif event == "progress":
                        status.caption(f"特徴量計算中: {done}/{total}")
                        detail.text(str(payload.get("listing_id") or ""))

            with st.spinner("収集中..."):
                result = run_search_import(
                    search_url.strip(),
                    region_label=search_region_label or None,
                    max_pages=int(max_pages),
                    max_listings=int(max_listings),
                    sleep_sec=float(search_sleep),
                    compute_features=bool(compute_features),
                    progress_cb=_progress_cb,
                )
            progress.progress(1.0)
            status.caption("完了")
            detail.text("")
            st.success(
                "収集完了: "
                f"pages={result['pages']} / urls={result['collected_urls']} / "
                f"取込 成功 {result['imported_done']} 件 失敗 {result['imported_failed']} 件 / "
                f"特徴量 成功 {result['feature_done']} 件 失敗 {result['feature_failed']} 件"
            )
            if result.get("detail_urls"):
                st.code("\n".join(result["detail_urls"][:20]), language="")
            st.cache_data.clear()

    recent_jobs = db.read_recent_search_jobs(conn, limit=10)
    if not recent_jobs.empty:
        cols = [
            c
            for c in [
                "started_at",
                "source",
                "region_label",
                "status",
                "collected_pages",
                "collected_urls",
                "imported_done",
                "imported_failed",
                "feature_done",
                "feature_failed",
                "search_url",
            ]
            if c in recent_jobs.columns
        ]
        st.dataframe(recent_jobs[cols], use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("掲載URL 一括取込")
    region_label = st.text_input(
        "地域ラベル", placeholder="例: 新宿区一棟アパート", key="listing_import_region"
    )
    url_blob = st.text_area("URL一覧", placeholder="1行1URL", height=120, key="listing_import_urls")
    if st.button("▶ URL一覧を取込", type="primary", key="listing_import_btn"):
        urls = [line.strip() for line in url_blob.splitlines() if line.strip()]
        if not urls:
            st.warning("URLを1件以上入力してください。")
        else:
            with st.spinner("取込中..."):
                result = run_import_urls(urls, region_label=region_label or None)
            st.success(f"取込完了: 成功 {result['done']} 件 / 失敗 {result['failed']} 件")
            st.cache_data.clear()

    # ---------- DB 操作 ----------
    st.subheader("DB 操作")
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        if st.button("🔄 派生テーブル再構築"):
            db.rebuild_derived_tables(conn)
            st.success("派生テーブルを再構築しました")

    with col_b:
        if st.button("🗑 raw キャッシュ削除"):
            deleted = _delete_raw_cache()
            st.success(f"{deleted} ファイルを削除しました")

    with col_c:
        del_year = st.number_input("削除する年度", value=0, min_value=0, step=1, key="del_year")
        if st.button("⚠ 年度データ削除", type="secondary"):
            if del_year > 0:
                cnt = conn.execute(
                    "SELECT COUNT(*) FROM land_prices_public_notice WHERE year=?", [del_year]
                ).fetchone()[0]
                if cnt > 0:
                    conn.execute("DELETE FROM land_prices_public_notice WHERE year=?", [del_year])
                    st.warning(f"year={del_year} の {cnt:,} 件を削除しました")
                    st.rerun()
                else:
                    st.info(f"year={del_year} のデータはありません")
            else:
                st.error("有効な年度を入力してください")

    # ---------- ファイル一覧 ----------
    st.markdown("---")
    st.subheader("保存ファイル一覧")
    _show_file_list()


def _delete_raw_cache() -> int:
    deleted = 0
    for p in RAW_DIR.glob("fetched_tiles_*.json"):
        p.unlink()
        deleted += 1
    return deleted


def _show_file_list() -> None:
    files: list[dict] = []
    for d, label in [(RAW_DIR, "raw"), (PROCESSED_DIR, "processed")]:
        for p in sorted(d.glob("*")):
            if p.is_file():
                size_kb = p.stat().st_size / 1024
                files.append(
                    {"ディレクトリ": label, "ファイル名": p.name, "サイズ(KB)": f"{size_kb:.1f}"}
                )
    if files:
        st.dataframe(pd.DataFrame(files), use_container_width=True)
    else:
        st.info("保存ファイルなし")
