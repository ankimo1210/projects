"""
property_state.py
物件分析タブのセッション状態を一元管理する dataclass。

st.session_state に散在していた "prop_*" キーをまとめ、
型安全な読み書きインターフェースを提供する。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import streamlit as st

from property_scraper import PropertyData

_SESSION_KEY = "prop_analysis_state"


@dataclass
class PropertyAnalysisState:
    prop: Optional[PropertyData] = None
    geo: Optional[tuple[float, float]] = None
    city_code: Optional[str] = None
    source_url: str = ""
    region_label: Optional[str] = None
    persisted_listing_id: Optional[str] = None

    # ------------------------------------------------------------------ #
    # ファクトリ / 永続化
    # ------------------------------------------------------------------ #

    @classmethod
    def load(cls) -> "PropertyAnalysisState":
        """セッションから現在の状態を読み込む。未初期化なら空の状態を返す。"""
        return st.session_state.get(_SESSION_KEY) or cls()

    def save(self) -> None:
        """現在の状態をセッションに書き込む。"""
        st.session_state[_SESSION_KEY] = self

    # ------------------------------------------------------------------ #
    # 便利メソッド
    # ------------------------------------------------------------------ #

    def set_property(
        self,
        prop: PropertyData,
        geo: Optional[tuple[float, float]] = None,
        city_code: Optional[str] = None,
    ) -> None:
        """物件データとジオコーディング結果をまとめてセットして保存する。"""
        self.prop = prop
        if geo is not None:
            self.geo = geo
        if city_code is not None:
            self.city_code = city_code
        self.save()

    def clear(self) -> None:
        """状態をリセットする。"""
        st.session_state.pop(_SESSION_KEY, None)

    @property
    def has_geo(self) -> bool:
        return self.geo is not None

    @property
    def has_prop(self) -> bool:
        return self.prop is not None
