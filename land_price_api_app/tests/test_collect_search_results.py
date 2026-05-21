from collect_search_results import (
    extract_rakumachi_listing_urls,
    extract_rakumachi_next_page_url,
    normalize_detail_url,
)


def test_normalize_detail_url_accepts_rakumachi_detail() -> None:
    url = normalize_detail_url(
        "https://www.rakumachi.jp/syuuekibukken/area/prefecture/dimAll/?pref=47",
        "/syuuekibukken/kyushu/okinawa/dim1002/3598628/show.html?device_type=pc",
    )
    assert url == "https://www.rakumachi.jp/syuuekibukken/kyushu/okinawa/dim1002/3598628/show.html"


def test_extract_rakumachi_listing_urls_deduplicates_and_filters() -> None:
    html = """
    <html><body>
      <a href="/syuuekibukken/kyushu/okinawa/dim1002/3598628/show.html?device_type=pc">a</a>
      <a href="https://www.rakumachi.jp/syuuekibukken/kyushu/okinawa/dim1001/3603574/show.html">b</a>
      <a href="/syuuekibukken/kyushu/okinawa/dim1002/3598628/show.html">dup</a>
      <a href="/news/">ignore</a>
    </body></html>
    """
    urls = extract_rakumachi_listing_urls(
        html,
        "https://www.rakumachi.jp/syuuekibukken/area/prefecture/dimAll/?pref=47",
    )
    assert urls == [
        "https://www.rakumachi.jp/syuuekibukken/kyushu/okinawa/dim1002/3598628/show.html",
        "https://www.rakumachi.jp/syuuekibukken/kyushu/okinawa/dim1001/3603574/show.html",
    ]


def test_extract_rakumachi_next_page_url_prefers_rel_next() -> None:
    html = """
    <html><body>
      <a rel="next" href="/syuuekibukken/area/prefecture/dimAll/?pref=47&page=2">次へ</a>
    </body></html>
    """
    next_url = extract_rakumachi_next_page_url(
        html,
        "https://www.rakumachi.jp/syuuekibukken/area/prefecture/dimAll/?pref=47&page=1",
    )
    assert next_url == "https://www.rakumachi.jp/syuuekibukken/area/prefecture/dimAll/?pref=47&page=2"


def test_extract_rakumachi_next_page_url_uses_page_query() -> None:
    html = """
    <html><body>
      <a href="/syuuekibukken/area/prefecture/dimAll/?pref=47&page=3">3</a>
      <a href="/syuuekibukken/area/prefecture/dimAll/?pref=47&page=2">2</a>
    </body></html>
    """
    next_url = extract_rakumachi_next_page_url(
        html,
        "https://www.rakumachi.jp/syuuekibukken/area/prefecture/dimAll/?pref=47&page=1",
    )
    assert next_url == "https://www.rakumachi.jp/syuuekibukken/area/prefecture/dimAll/?pref=47&page=2"
