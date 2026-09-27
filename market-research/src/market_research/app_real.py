"""Offline saved-data views; each input is an explicit immutable snapshot."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from .research.baskets import BasketDefinition, basket_series, compare_basket
from .research.dataset import load_price_dataset
from .research.fundamentals import (
    FundamentalField,
    FundamentalRequest,
    load_fundamental_table,
)
from .research.indicators import close_history, indicator_table
from .research.overview import market_overview
from .research.portfolio import VirtualConstraints, virtual_risk_report
from .research.screener import ThresholdRule, screen_research
from .storage import ResearchStore

TITLES = (
    "市場概要",
    "銘柄・バスケット",
    "シグナル・スクリーナー",
    "戦略比較",
    "マクロと公表",
    "仮想配分・リスク",
    "品質・実行履歴",
)


def _financial_request(snapshot, instrument_id: str) -> FundamentalRequest:
    parts = snapshot.key.identity.split(":")
    if len(parts) != 5 or not parts[0].startswith("CIK"):
        raise ValueError("SEC snapshot identity is invalid")
    cik = int(parts[0][3:])
    field = FundamentalField(parts[2].lower(), parts[1], parts[2], parts[3], parts[4])
    return FundamentalRequest(instrument_id, cik, field, snapshot.snapshot_id)


def render_real_app() -> None:
    """Show local snapshots without triggering any provider request."""
    default_root = os.environ.get(
        "MARKET_RESEARCH_DATA_ROOT", str(Path.home() / ".local/share/market-research")
    )
    root = st.sidebar.text_input("保存先（WSLパス）", value=default_root)
    as_of_text = st.sidebar.text_input(
        "基準時刻（タイムゾーン付き）", value=datetime.now(UTC).replace(microsecond=0).isoformat()
    )
    try:
        as_of = datetime.fromisoformat(as_of_text)
        if as_of.utcoffset() is None:
            raise ValueError("timezone-aware as_of required")
        as_of = as_of.astimezone(UTC)
    except ValueError:
        st.error("基準時刻はタイムゾーン付きISO形式で入力してください。")
        return
    st.title("market-research")
    st.caption("保存済みデータ | 明示snapshotのみ | 通信なし | 個人口座データなし")
    try:
        with ResearchStore(Path(root)) as store:
            snapshots = {
                item.snapshot_id: item
                for item in store.snapshots(1000)
                if item.complete and item.observed_at <= as_of
            }
            price_options = tuple(
                snapshot_id
                for snapshot_id, item in snapshots.items()
                if item.key.dataset == "prices"
            )
            if not price_options:
                st.info("この保存先に利用可能な価格snapshotがありません。")
                return
            selected_prices = st.sidebar.multiselect(
                "価格snapshot",
                price_options,
                format_func=lambda snapshot_id: (
                    f"{snapshots[snapshot_id].key.identity} / "
                    f"{snapshots[snapshot_id].key.provider} / "
                    f"{snapshots[snapshot_id].observed_at.isoformat()}"
                ),
            )
            if not selected_prices:
                st.info("価格snapshotを選択してください。")
                return
            first = snapshots[selected_prices[0]]
            momentum_window = int(st.sidebar.number_input("変化率の観測数", min_value=1, value=5))
            volatility_window = int(st.sidebar.number_input("変動率の観測数", min_value=2, value=5))
            periods_per_year = int(
                st.sidebar.number_input("年率換算の年間観測数", min_value=1, value=252)
            )
            composition_date = st.sidebar.date_input("構成基準日", value=as_of.date())
            momentum_floor = float(st.sidebar.number_input("変化率の下限", value=0.0, step=0.01))
            dataset = load_price_dataset(
                store,
                tuple(selected_prices),
                as_of=as_of,
                currency=first.key.currency,
                adjustment=first.key.adjustment,
            )
            history = close_history(dataset)
            indicators = indicator_table(
                history,
                momentum_window=momentum_window,
                volatility_window=volatility_window,
                periods_per_year=periods_per_year,
            )
            assets = tuple(indicators.index)
            benchmark_id = st.sidebar.selectbox(
                "比較対象の価格snapshot",
                ("選択なし", *(item for item in price_options if item not in selected_prices)),
                format_func=lambda snapshot_id: (
                    snapshot_id
                    if snapshot_id == "選択なし"
                    else f"{snapshots[snapshot_id].key.identity} / "
                    f"{snapshots[snapshot_id].key.provider} / "
                    f"{snapshots[snapshot_id].observed_at.isoformat()}"
                ),
            )
            benchmark_dataset = (
                load_price_dataset(
                    store,
                    (benchmark_id,),
                    as_of=as_of,
                    currency=dataset.currency,
                    adjustment=dataset.adjustment,
                )
                if benchmark_id != "選択なし"
                else None
            )
            fundamental_options = tuple(
                snapshot_id
                for snapshot_id, item in snapshots.items()
                if item.key.dataset == "fundamental" and item.key.provider == "sec"
            )
            financial_id = st.sidebar.selectbox(
                "財務snapshot",
                ("選択なし", *fundamental_options),
                format_func=lambda snapshot_id: (
                    snapshot_id
                    if snapshot_id == "選択なし"
                    else f"{snapshots[snapshot_id].key.identity} / "
                    f"{snapshots[snapshot_id].observed_at.isoformat()}"
                ),
            )
            request = None
            if financial_id != "選択なし":
                financial_asset = st.sidebar.selectbox("財務の対応銘柄", assets)
                candidate = _financial_request(snapshots[financial_id], financial_asset)
                cik_label = f"CIK{candidate.cik:010d}"
                typed_cik = st.sidebar.text_input(
                    f"{financial_asset} と {cik_label} の対応を確認（CIKを入力）"
                )
                st.sidebar.caption(
                    "保存データに企業名の対応表はありません。選択した銘柄とCIKを照合してください。"
                )
                if typed_cik.strip() == cik_label:
                    request = candidate
                elif typed_cik:
                    st.sidebar.warning("CIKが一致しません。財務値を表示しません。")
            if request is None:
                fundamentals = pd.DataFrame(
                    columns=["value", "unit", "missing_reason"],
                    index=pd.MultiIndex.from_tuples([], names=["instrument_id", "field"]),
                )
            else:
                fundamentals = load_fundamental_table(store, (request,), as_of=as_of)
    except (ValueError, OSError) as error:
        st.error(f"保存済みデータを読み込めません: {type(error).__name__}: {error}")
        return

    rules = (
        ThresholdRule(
            "momentum",
            "technical",
            "momentum",
            "ge",
            momentum_floor,
            "fraction",
        ),
    )
    financial_floor = None
    if request is not None:
        financial_floor = float(st.sidebar.number_input("財務値の下限", value=0.0, step=1.0))
        rules += (
            ThresholdRule(
                request.field.name,
                "fundamental",
                request.field.name,
                "ge",
                financial_floor,
                request.field.unit,
                field_definition=request.field,
            ),
        )
    screened = screen_research(indicators, fundamentals, rules)
    correlation_window = int(
        st.sidebar.number_input(
            "相関の観測数", min_value=3, value=min(20, max(3, len(history.prices) - 1))
        )
    )
    drawdown_alert = float(
        st.sidebar.number_input("下落アラートの閾値", min_value=-1.0, max_value=-0.01, value=-0.2)
    )
    zscore_alert = float(st.sidebar.number_input("Zスコアアラートの閾値", min_value=0.1, value=2.0))
    overview = market_overview(
        history,
        indicators,
        correlation_window=correlation_window,
        drawdown_alert=drawdown_alert,
        zscore_alert=zscore_alert,
    )
    risk_lookback = int(
        st.sidebar.number_input(
            "リスク観測数", min_value=2, value=min(20, max(2, len(history.prices) - 1))
        )
    )
    risk_cash_min = float(
        st.sidebar.number_input("仮想配分の最低現金比率", min_value=0.0, max_value=0.99, value=0.0)
    )
    risk_max_name = float(
        st.sidebar.number_input("仮想配分の銘柄上限", min_value=0.01, max_value=1.0, value=1.0)
    )
    risk_weights = pd.Series(
        {
            asset: float(
                st.sidebar.number_input(
                    f"仮想ウェイト {asset}",
                    min_value=0.0,
                    max_value=1.0,
                    value=1.0 / len(assets),
                    step=0.05,
                )
            )
            for asset in assets
        }
    )
    payload = {
        "price_snapshot_ids": selected_prices,
        "benchmark_snapshot_id": benchmark_id if benchmark_id != "選択なし" else None,
        "fundamental_snapshot_id": request.snapshot_id if request else None,
        "fundamental_asset": request.instrument_id if request else None,
        "fundamental_field": request.field.name if request else None,
        "fundamental_cik": request.cik if request else None,
        "fundamental_taxonomy": request.field.taxonomy if request else None,
        "fundamental_concept": request.field.concept if request else None,
        "fundamental_form": request.field.form if request else None,
        "financial_floor": financial_floor,
        "as_of": as_of.isoformat(),
        "momentum_window": momentum_window,
        "volatility_window": volatility_window,
        "periods_per_year": periods_per_year,
        "composition_date": composition_date.isoformat(),
        "momentum_floor": momentum_floor,
        "risk_lookback": risk_lookback,
        "risk_cash_min": risk_cash_min,
        "risk_max_name": risk_max_name,
        "risk_weights": risk_weights.to_dict(),
        "correlation_window": correlation_window,
        "drawdown_alert": drawdown_alert,
        "zscore_alert": zscore_alert,
    }
    st.caption(f"研究run未保存 | {dataset.currency} | {dataset.adjustment}")
    tabs = st.tabs(TITLES)
    with tabs[0]:
        st.subheader("市場概要")
        st.dataframe(overview.summary)
        st.dataframe(overview.correlations)
        st.dataframe(overview.pair_counts)
        st.caption(
            f"{overview.mode} / {overview.currency} / {overview.adjustment}。"
            f"相関の有効組数を別表に表示（最低3組）。観測窓: {overview.correlation_window}リターン。"
        )
    with tabs[1]:
        st.subheader("銘柄・バスケット")
        st.dataframe(history.prices)
        st.caption(f"履歴の種類: {history.mode} / 基準時刻: {dataset.as_of.isoformat()}")
        st.dataframe(fundamentals)
        st.caption("財務はSECの選択済み開示値のみ。未取得項目は補完しません。")
        if request is not None:
            st.caption(
                f"手動対応: {request.instrument_id} ↔ CIK{request.cik:010d} / "
                f"{request.field.taxonomy}:{request.field.concept}:{request.field.form}"
            )
        try:
            definition = BasketDefinition(
                "手動選択バスケット",
                assets,
                composition_date,
                "保存済みsnapshotからの手動選択",
                "price",
            )
            basket = basket_series(dataset, definition)
            st.line_chart(basket.values["level"])
            st.dataframe(basket.weights)
            st.caption(
                f"現在の構成を過去へ固定したretrospective近似。PAF=1（仮定日: "
                f"{definition.factors_as_of.isoformat()}）で、公式指数やPITバックテストではありません。"
            )
            if benchmark_dataset is not None:
                compared = compare_basket(basket, benchmark_dataset, benchmark_name=benchmark_id)
                st.line_chart(compared.values[["basket_level", "benchmark_level"]])
                st.dataframe(compared.values)
                st.caption("比較対象は同じ通貨・調整方式・日付・確定時刻の保存済み価格のみ。")
        except ValueError as error:
            st.warning(f"バスケットを計算できません: {error}")
    with tabs[2]:
        st.subheader("シグナル・スクリーナー")
        st.dataframe(indicators)
        st.dataframe(screened)
        st.caption("pass / fail / unknown を分けて表示。品質理由と欠損理由を保持します。")
    for tab, title in zip(tabs[3:5], TITLES[3:5], strict=True):
        with tab:
            st.subheader(title)
            st.info("この保存データ画面は後続で接続します。")
    with tabs[5]:
        st.subheader("仮想配分・リスク")
        try:
            risk = virtual_risk_report(
                history,
                risk_weights,
                base_currency=dataset.currency,
                lookback=risk_lookback,
                periods_per_year=periods_per_year,
                constraints=VirtualConstraints(
                    max_name_weight=risk_max_name, cash_min=risk_cash_min
                ),
            )
            st.metric("年率ボラティリティ", f"{risk.total_vol_annualized:.1%}")
            st.metric("現金比率", f"{risk.cash_weight:.1%}")
            st.dataframe(
                pd.DataFrame(
                    {
                        "weight": risk.weights,
                        "component_vol_annualized": risk.component_vol_annualized,
                        "quality_reasons": pd.Series(risk.quality_reasons),
                    }
                )
            )
            st.caption(
                f"{risk.mode} / {risk.base_currency} / {risk.adjustment} / "
                f"{risk.lookback}リターン / 年間{risk.periods_per_year}観測。"
                "実口座配分・FX換算・PITバックテストではありません。"
            )
        except ValueError as error:
            st.warning(f"仮想リスクを計算できません: {error}")
    with tabs[6]:
        st.subheader("品質・実行履歴")
        used_ids = (*selected_prices,)
        if benchmark_id != "選択なし":
            used_ids += (benchmark_id,)
        if request is not None:
            used_ids += (request.snapshot_id,)
        st.dataframe(
            pd.DataFrame.from_records(
                [
                    {
                        "snapshot_id": snapshot_id,
                        "provider": snapshots[snapshot_id].key.provider,
                        "identity": snapshots[snapshot_id].key.identity,
                        "observed_at": snapshots[snapshot_id].observed_at,
                    }
                    for snapshot_id in used_ids
                ]
            )
        )
        st.dataframe(overview.alerts)
        st.caption("アプリ内アラートのみ。品質・欠損・閾値を表示し、外部へ通知しません。")
        st.dataframe(
            pd.DataFrame.from_records(
                [
                    {
                        "instrument_id": gap.instrument.instrument_id,
                        "session_date": gap.session_date,
                        "kind": "gap",
                    }
                    for gap in dataset.gaps
                ]
                + [
                    {
                        "instrument_id": exclusion.bar.instrument.instrument_id,
                        "session_date": exclusion.bar.session_date,
                        "kind": exclusion.reason,
                    }
                    for exclusion in dataset.exclusions
                ],
                columns=["instrument_id", "session_date", "kind"],
            )
        )
        st.info("保存runと取得失敗履歴はまだ記録していません。")
        st.json({"research_run_saved": False, "inputs": payload, "network_fetch": False})
