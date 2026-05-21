"""PII マスキングのテスト。"""

from __future__ import annotations

from api.services.pii import mask, mask_text


def test_phone_numbers():
    r = mask("お電話 03-1234-5678 または 090-1111-2222 まで")
    assert "03-1234-5678" not in r.text
    assert "090-1111-2222" not in r.text
    assert r.counts.get("PHONE") == 2


def test_email():
    r = mask("お問合わせ: agent@example.co.jp")
    assert "agent@example.co.jp" not in r.text
    assert r.counts.get("EMAIL") == 1


def test_postal_and_address():
    r = mask("〒160-0023 東京都新宿区西新宿1-2-3 西新宿レジデンス504号")
    assert "160-0023" not in r.text
    assert "1-2-3" not in r.text
    # 「東京都新宿区西新宿」は残ってよい (市区町村レベル)
    assert "新宿区" in r.text


def test_honorific_name():
    r = mask("山田太郎 様 / 田中 氏")
    assert "山田太郎" not in r.text
    assert r.counts.get("NAME", 0) >= 2


def test_company():
    r = mask("株式会社サンプル不動産 まで")
    assert "株式会社サンプル不動産" not in r.text
    assert r.counts.get("COMPANY", 0) >= 1


def test_numbers_preserved():
    """価格・賃料・面積など数値は残す (PII ではない)。"""
    txt = "価格 3,980万円 / 月額 145,000円 / 38.4㎡"
    r = mask(txt)
    assert "3,980" in r.text
    assert "145,000" in r.text
    assert "38.4" in r.text


def test_mask_text_helper():
    assert mask_text("test@example.com") != "test@example.com"
