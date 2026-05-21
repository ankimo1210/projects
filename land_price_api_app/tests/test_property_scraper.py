"""
tests/test_property_scraper.py
property_scraper の抽出ロジック回帰テスト。

ネットワークアクセスなし: fixtures/ に保存済みの HTML を使ってローカルで実行する。
実行方法:
    python -m pytest tests/test_property_scraper.py -v
    # または pytest 未インストール時:
    python tests/test_property_scraper.py
"""

import dataclasses
import json
import pathlib
import sys

# プロジェクトルートを sys.path に追加（tests/ から起動された場合も動作するように）
_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from property_scraper import extract_property_data  # noqa: E402

_FIXTURES = pathlib.Path(__file__).parent / "fixtures"

# ── フィールド別の許容誤差設定 ────────────────────────────────────────────
# float フィールド: 絶対誤差（単位は各フィールドと同じ）
_FLOAT_TOL: dict[str, float] = {
    "gross_yield_pct": 0.01,
    "building_area_sqm": 0.1,
    "land_area_sqm": 0.1,
    "legal_far_pct": 1.0,
    "bcr_pct": 1.0,
}
# int フィールド: 絶対誤差
_INT_TOL: dict[str, int] = {
    "asking_price_yen": 0,
    "gross_rent_annual_yen": 100,  # 端数丸め差を許容
    "gross_rent_monthly_yen": 10,
    "age_years": 1,  # 年度境界で±1
    "station_walk_min": 0,
    "num_units": 0,
    "num_floors": 0,
}

# ── テストケース定義 ───────────────────────────────────────────────────────
# 各ケース: { "fixture": "ファイル名ベース", "skip_fields": [...] }
# skip_fields には「ページによって値が変わるフィールド」を列挙する
# (updated_date / listing_date はページ更新で変わるためスキップ)
TEST_CASES = [
    {
        "fixture": "rakumachi_3603574",
        "description": "楽待 1棟マンション（沖縄那覇市・アーバンヒルズ松尾）",
        "skip_fields": ["updated_date", "listing_date"],
    },
    {
        "fixture": "rakumachi_3600711",
        "description": "楽待 1棟アパート（沖縄那覇市・表面利回り非掲載→計算フォールバック）",
        # gross_yield_pct は賃料/価格から計算するため端数ずれを許容
        "skip_fields": ["updated_date", "listing_date"],
    },
    {
        "fixture": "rakumachi_3598628",
        "description": "楽待 1棟アパート（沖縄那覇市・ラリアンス・27/27全項目取得）",
        "skip_fields": ["updated_date", "listing_date"],
    },
    {
        "fixture": "kenbiya_4338280jq8",
        "description": "健美家 1棟マンション（沖縄那覇市・高良2丁目アパート）",
        "skip_fields": ["updated_date", "listing_date"],
    },
    {
        "fixture": "kenbiya_4394631uwb",
        "description": "健美家 1棟マンション（沖縄那覇市・前田ビル）",
        "skip_fields": [],
    },
    {
        "fixture": "kenbiya_44565007vq",
        "description": "健美家 1棟マンション（沖縄那覇市・国場 一棟RCマンション）",
        "skip_fields": [],
    },
]


# ── ヘルパー ──────────────────────────────────────────────────────────────


def _load_fixture(name: str) -> tuple[str, dict]:
    html_path = _FIXTURES / f"{name}.html"
    json_path = _FIXTURES / f"{name}_expected.json"
    html = html_path.read_text(encoding="utf-8")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    return html, data


def _assert_field(field: str, actual, expected, errors: list) -> None:
    """1フィールドの検証。不一致を errors リストに追記する。"""
    # 両方 None → OK
    if expected is None and actual is None:
        return
    # 期待値 None だが実際は値あり → 許容（追加情報）
    if expected is None:
        return
    # 期待値あり・実際は None → NG
    if actual is None:
        errors.append(f"  {field}: expected {expected!r}, got None")
        return

    if field in _FLOAT_TOL:
        tol = _FLOAT_TOL[field]
        if abs(float(actual) - float(expected)) > tol:
            errors.append(f"  {field}: expected {expected} ± {tol}, got {actual}")
    elif field in _INT_TOL:
        tol = _INT_TOL[field]
        if abs(int(actual) - int(expected)) > tol:
            errors.append(f"  {field}: expected {expected} ± {tol}, got {actual}")
    else:
        if str(actual) != str(expected):
            errors.append(f"  {field}: expected {expected!r}, got {actual!r}")


# ── テスト本体 ────────────────────────────────────────────────────────────


def run_test_case(tc: dict) -> tuple[bool, str]:
    """1テストケースを実行。(passed: bool, message: str) を返す。"""
    name = tc["fixture"]
    desc = tc.get("description", name)
    skip = set(tc.get("skip_fields", []))

    html, fixture = _load_fixture(name)
    url = fixture["url"]
    expected = fixture["expected"]

    prop = extract_property_data(html, url)
    actual = dataclasses.asdict(prop)
    actual.pop("raw_extraction", None)

    errors: list[str] = []
    for field, exp_val in expected.items():
        if field in skip:
            continue
        if field in ("llm_filled_fields",):
            continue
        _assert_field(field, actual.get(field), exp_val, errors)

    if errors:
        msg = f"FAIL [{desc}]\n" + "\n".join(errors)
        return False, msg
    return True, f"PASS [{desc}]"


def run_all() -> None:
    """全テストケースを実行してサマリーを表示する。"""
    passed = failed = 0
    for tc in TEST_CASES:
        ok, msg = run_test_case(tc)
        print(msg)
        if ok:
            passed += 1
        else:
            failed += 1

    total = passed + failed
    print(f"\n{'─' * 50}")
    print(
        f"結果: {passed}/{total} passed" + (f"  ← {failed} FAILED" if failed else "  ✅ ALL PASSED")
    )
    if failed:
        sys.exit(1)


# ── pytest インテグレーション ─────────────────────────────────────────────


def pytest_cases():
    """pytest の parametrize 用にテストケースを展開する。"""
    return [(tc["fixture"], tc) for tc in TEST_CASES]


try:
    import pytest

    @pytest.mark.parametrize("name,tc", pytest_cases())
    def test_extract(name: str, tc: dict):
        ok, msg = run_test_case(tc)
        assert ok, msg

except ImportError:
    pass  # pytest なし → run_all() でのみ動作


if __name__ == "__main__":
    run_all()
