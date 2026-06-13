"""
notebook_utils.py
Jupyter Notebook から API / DB / 分析関数を簡単に呼べる高レベルユーティリティ。

使用例:
    from notebook_utils import load_env_and_connect, load_year_from_db, plot_points_map
    conn, df_2026 = load_env_and_connect()
    df = load_year_from_db(conn, 2026)
    plot_points_map(df)
"""

from pathlib import Path

import analytics
import db
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sync_public_notice as sync
from config import ensure_dirs, get_logger, validate_api_key

logger = get_logger(__name__)


# --------------------------------------------------------------------------
# 初期化
# --------------------------------------------------------------------------


def load_env_and_connect(db_path: Path | None = None, read_only: bool = False):
    """
    .env を読み込み、DuckDB 接続を確立する。
    DB がロックされている場合は None を返す（Parquet フォールバック用）。

    Parameters
    ----------
    read_only : bool
        True の場合、読み取り専用で接続する。複数カーネルから同時参照する場合に指定。

    Returns
    -------
    conn : duckdb.DuckDBPyConnection | None
        接続できない場合は None。load_year_from_db は None でも動作する。
    """
    try:
        validate_api_key()
        print("✓ APIキーを確認しました")
    except OSError as e:
        print(f"✗ {e}")
        raise

    ensure_dirs()
    try:
        conn = db.get_connection(db_path, read_only=read_only)
        if not read_only:
            try:
                db.create_tables_if_needed(conn)
            except Exception:
                pass
        stats = db.get_stats(conn)
        mode_label = " (読み取り専用)" if read_only else ""
        print(
            f"✓ DB 接続成功{mode_label}: {stats['total_records']:,} レコード / 年度: {stats['available_years']}"
        )
        return conn
    except Exception as e:
        print(f"⚠ DB に接続できないため Parquet モードで動作します ({e.__class__.__name__})")
        print(
            "  → Parquet ファイルから直接読み込みます。別カーネルで DB を使用中の場合はそちらを終了してください。"
        )
        return None


# --------------------------------------------------------------------------
# データロード
# --------------------------------------------------------------------------


def load_year_from_api(
    year: int,
    z: int = 13,
    prefecture_code: str | None = None,
    overwrite: bool = False,
    conn=None,
) -> pd.DataFrame:
    """
    API からデータを取得して DB に保存し、DataFrame を返す。

    Parameters
    ----------
    year : int
        取得対象年 (例: 2026)。
    z : int
        ズームレベル（全国同期は z=13 推奨）。
    prefecture_code : str, optional
        都道府県コード指定で部分取得（デバッグ・テスト用）。
    overwrite : bool
        取得済みタイルキャッシュを無視して再取得する。
    conn : duckdb.DuckDBPyConnection, optional
        既存の DB 接続を渡すと競合を回避できる。省略時は内部で接続を開く。

    Returns
    -------
    pd.DataFrame
    """
    print(f"API から year={year} を取得中... (z={z})")
    df = sync.sync_public_notice_year(
        year=year,
        z=z,
        prefecture_code=prefecture_code,
        overwrite=overwrite,
        conn=conn,
    )
    if df.empty:
        print(
            f"⚠ year={year} のデータが 0 件でした。"
            f" year={year - 1} を試すか、API キーを確認してください。"
        )
    else:
        print(f"✓ {len(df):,} 件取得・保存完了 (year={year})")
    return df


def load_year_from_db(
    conn,
    year: int,
    prefecture_code: str | None = None,
    city_code: str | None = None,
) -> pd.DataFrame:
    """
    DB（または Parquet）からデータを読み込む。

    conn が None の場合（DB ロック中）は Parquet ファイルから読む。

    Parameters
    ----------
    conn : duckdb.DuckDBPyConnection | None
    year : int
    prefecture_code : str, optional
    city_code : str, optional

    Returns
    -------
    pd.DataFrame
    """
    # --- Parquet フォールバック（DB ロック中） ---
    if conn is None:
        return _load_year_from_parquet(year, prefecture_code, city_code)

    # --- DB から読み込み ---
    filters: dict = {"year": year}
    if prefecture_code:
        filters["prefecture_code"] = prefecture_code.zfill(2)
    if city_code:
        filters["city_code"] = city_code

    df = db.read_land_prices(conn, filters=filters)
    print(f"✓ DB から {len(df):,} 件ロード (year={year})")
    return df


def _load_year_from_parquet(
    year: int,
    prefecture_code: str | None = None,
    city_code: str | None = None,
) -> pd.DataFrame:
    """Parquet ファイルから指定年のデータを読む（DB ロック時のフォールバック）。"""
    from config import PROCESSED_DIR

    parquet_path = PROCESSED_DIR / f"land_prices_y{year}_pc0.parquet"
    if not parquet_path.exists():
        # 他の price_classification も探す
        candidates = list(PROCESSED_DIR.glob(f"land_prices_y{year}_pc*.parquet"))
        if not candidates:
            print(f"⚠ Parquet ファイルが見つかりません: {parquet_path}")
            print(f"  → 先に sync_public_notice.py --year {year} を実行してください。")
            return pd.DataFrame()
        parquet_path = candidates[0]

    df = pd.read_parquet(parquet_path)
    if prefecture_code:
        df = df[df["prefecture_code"] == prefecture_code.zfill(2)]
    if city_code:
        df = df[df["city_code"] == city_code]
    print(f"✓ Parquet から {len(df):,} 件ロード (year={year}, file={parquet_path.name})")
    return df


# --------------------------------------------------------------------------
# サマリー表示
# --------------------------------------------------------------------------


def show_basic_summary(df: pd.DataFrame) -> None:
    """DataFrame の基本統計をテキストで表示する。"""
    if df.empty:
        print("データが空です。")
        return

    stats = analytics.compute_basic_stats(df)
    print("=" * 50)
    print(f"総件数         : {stats['total']:,}")
    print(f"年度           : {stats.get('years', [])}")
    print(f"都道府県数     : {stats.get('prefecture_count', 'N/A')}")
    print(f"市区町村数     : {stats.get('city_count', 'N/A')}")
    if "price_mean" in stats:
        print(f"平均価格       : ¥{stats['price_mean']:,.0f}/m²")
        print(f"中央値価格     : ¥{stats['price_median']:,.0f}/m²")
        print(f"最高価格       : ¥{stats['price_max']:,.0f}/m²")
    if "yoy_mean" in stats:
        print(f"平均前年比     : {stats['yoy_mean']:+.2f}%")
    print("=" * 50)


# --------------------------------------------------------------------------
# 地図表示
# --------------------------------------------------------------------------


def plot_points_map(
    df: pd.DataFrame,
    color_col: str = "price_yen_per_sqm",
    title: str = "公示地価 地点マップ",
    mapbox_style: str = "open-street-map",
    max_points: int = 5000,
) -> go.Figure:
    """
    Plotly Express で地点を地図表示する。

    Parameters
    ----------
    df : DataFrame
    color_col : str
        色分けに使うカラム。
    max_points : int
        表示上限（重い場合にサンプリング）。
    """
    plot_df = df.dropna(subset=["lon", "lat", color_col]).copy()
    if len(plot_df) > max_points:
        plot_df = plot_df.sample(max_points, random_state=42)

    if plot_df.empty:
        print("表示できるデータがありません。")
        return go.Figure()

    hover_cols = [
        c
        for c in [
            "point_id",
            "location_text",
            "city_name",
            "prefecture_name",
            "price_yen_per_sqm",
            "yoy_change_pct",
            "use_category_name",
        ]
        if c in plot_df.columns
    ]

    fig = px.scatter_mapbox(
        plot_df,
        lat="lat",
        lon="lon",
        color=color_col,
        hover_data=hover_cols,
        color_continuous_scale="RdYlGn_r",
        mapbox_style=mapbox_style,
        zoom=5,
        center={"lat": 36.5, "lon": 137.0},
        title=title,
        height=600,
    )
    fig.update_layout(margin={"r": 0, "t": 40, "l": 0, "b": 0})
    fig.show()
    return fig


# --------------------------------------------------------------------------
# 時系列プロット
# --------------------------------------------------------------------------


def plot_point_history(
    df: pd.DataFrame,
    point_id: str,
) -> go.Figure:
    """
    特定地点の年次価格推移グラフを表示する。

    Parameters
    ----------
    df : DataFrame  （複数年分を含む全データ）
    point_id : str
    """
    ts = analytics.compute_point_timeseries(df, point_id)

    if ts.empty:
        print(f"point_id='{point_id}' のデータが見つかりません。")
        return go.Figure()

    location = ts["location_text"].iloc[0] if "location_text" in ts.columns else point_id

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=ts["year"],
            y=ts["price_yen_per_sqm"],
            mode="lines+markers",
            name="価格 (円/m²)",
            line=dict(width=2, color="#2196F3"),
            marker=dict(size=8),
        )
    )

    if "yoy_change_pct" in ts.columns and ts["yoy_change_pct"].notna().any():
        fig.add_trace(
            go.Bar(
                x=ts["year"],
                y=ts["yoy_change_pct"],
                name="前年比 (%)",
                yaxis="y2",
                marker_color=[
                    "#e53935" if v > 0 else "#1e88e5" for v in ts["yoy_change_pct"].fillna(0)
                ],
                opacity=0.6,
            )
        )

    fig.update_layout(
        title=f"年次推移: {location}",
        xaxis_title="年",
        yaxis=dict(title="価格 (円/m²)", tickformat=",.0f"),
        yaxis2=dict(title="前年比 (%)", overlaying="y", side="right"),
        legend=dict(x=0.01, y=0.99),
        height=450,
    )
    fig.show()
    return fig


# --------------------------------------------------------------------------
# ランキングプロット
# --------------------------------------------------------------------------


def plot_city_ranking(
    df: pd.DataFrame,
    year: int | None = None,
    top_n: int = 20,
) -> go.Figure:
    """
    市区町村別平均価格の横棒ランキンググラフを表示する。
    """
    target_year = year or (df["year"].max() if not df.empty else None)
    if target_year is None:
        print("データが空です。")
        return go.Figure()

    city_df = analytics.compute_city_summary(df[df["year"] == target_year])
    if city_df.empty:
        print(f"year={target_year} の市区町村集計データがありません。")
        return go.Figure()

    top = city_df.nlargest(top_n, "avg_price").sort_values("avg_price")
    label = top["city_name"].fillna("不明") + "（" + top["prefecture_name"].fillna("") + "）"

    fig = go.Figure(
        go.Bar(
            x=top["avg_price"],
            y=label,
            orientation="h",
            marker_color="#1976D2",
            text=top["avg_price"].map(lambda v: f"¥{v:,.0f}"),
            textposition="outside",
        )
    )
    fig.update_layout(
        title=f"市区町村別平均公示価格 TOP{top_n} ({target_year}年)",
        xaxis_title="平均価格 (円/m²)",
        height=max(400, top_n * 28),
        margin=dict(l=200),
    )
    fig.show()
    return fig
