import pytest
from stockkit.data.symbols import is_japanese, normalize_symbol


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("7203", "7203.T"),
        (" 7203 ", "7203.T"),
        ("7203.t", "7203.T"),
        ("aapl", "AAPL"),
        ("BRK-B", "BRK-B"),
        ("005930.KS", "005930.KS"),  # 6 digits -> not the 4-digit JP rule
    ],
)
def test_normalize_symbol(raw, expected):
    assert normalize_symbol(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("7203", True),
        ("7203.T", True),
        ("AAPL", False),
        ("005930.KS", False),
    ],
)
def test_is_japanese(raw, expected):
    assert is_japanese(raw) is expected
