"""Optional rendered acceptance check; no production dependency on Playwright.

uv run --no-project --with playwright python market-research/scripts/verify_megacap_browser.py
Start the tracker on localhost:8767 first. Evidence stays in _data/.
"""

from __future__ import annotations

import csv
import io
import json
import re
import subprocess
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "_data" / "market-research" / "megacap-tracker" / "qa"
URL = "http://127.0.0.1:8767"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    template = (ROOT / "market-research" / "web" / "megacap.html").read_text()
    script_path = OUT / "app.js"
    script_path.write_text(re.findall(r"<script>(.*?)</script>", template, flags=re.S)[0])
    subprocess.run(["node", "--check", str(script_path)], check=True)
    with urllib.request.urlopen(URL + "/api/snapshot") as response:
        snapshot = json.load(response)
    assert len(snapshot["companies"]) == 7
    assert all(c["fetch_status"] in {"ok", "partial"} for c in snapshot["companies"])
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path="/home/kazumasa/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome",
            headless=True,
            args=["--no-sandbox"],
        )
        context = browser.new_context(
            viewport={"width": 1440, "height": 1050}, accept_downloads=True
        )
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(URL)
        page.wait_for_selector(".company-card")
        assert page.locator(".company-card").count() == 7
        assert page.locator("#table-body tr").count() == 7
        assert "Microsoft" in page.locator("#price-title").inner_text()
        page.screenshot(path=str(OUT / "desktop.png"), full_page=True)

        # Sorting must change the actual company order, not just the arrow.
        expected = sorted(snapshot["companies"], key=lambda c: c["metrics"]["pe_ttm"])
        assert (
            page.locator("#table-body tr").first.get_attribute("data-select")
            == expected[0]["symbol"]
        )
        page.locator('[data-sort="pe_ttm"]').click()
        assert (
            page.locator("#table-body tr").first.get_attribute("data-select")
            == expected[-1]["symbol"]
        )
        page.locator('[data-view="financial"]').click()
        assert "営業CF TTM" in page.locator("#table-head").inner_text()
        assert "設備投資 TTM" in page.locator("#table-head").inner_text()
        expected_sales = max(
            (c for c in snapshot["companies"] if c["metrics"]["revenue_ttm"] is not None),
            key=lambda c: c["metrics"]["revenue_ttm"],
        )
        assert (
            page.locator("#table-body tr").first.get_attribute("data-select")
            == expected_sales["symbol"]
        )

        page.locator("#search").fill("NVDA")
        assert page.locator(".company-card").count() == 1
        assert page.locator("#table-body tr").count() == 1
        assert "NVIDIA" in page.locator("#financial-title").inner_text()
        assert page.locator(".vbar-row").count() == 1
        nvidia = next(c for c in snapshot["companies"] if c["symbol"] == "NVDA")
        assert (
            f"{nvidia['metrics']['pe_ttm']:.1f}"
            in page.locator(".summary-value").nth(1).inner_text()
        )
        with page.expect_download() as received:
            page.locator("#download-csv").click()
        downloaded = OUT / "filtered.csv"
        received.value.save_as(downloaded)
        csv_rows = list(csv.reader(io.StringIO(downloaded.read_text(encoding="utf-8-sig"))))
        assert len(csv_rows) == 2 and csv_rows[1][0] == "NVDA"
        assert (
            float(csv_rows[1][csv_rows[0].index("営業CF TTM (bn)")])
            == nvidia["metrics"]["operating_cf_ttm"] / 1e9
        )
        assert (
            float(csv_rows[1][csv_rows[0].index("設備投資 TTM (bn)")])
            == nvidia["metrics"]["capex_ttm"] / 1e9
        )

        with page.expect_download() as received:
            page.locator("#download-html").click()
        offline_path = OUT / "saved.html"
        received.value.save_as(offline_path)
        offline = context.new_page()
        offline.on("pageerror", lambda error: errors.append(str(error)))
        network = []
        offline.on("request", lambda request: network.append(request.url))
        offline.goto(offline_path.as_uri())
        assert offline.locator("#refresh").is_disabled()
        assert offline.locator("#table-body tr").count() == 1, (
            "saved HTML must retain the current filter"
        )
        assert offline.locator("#search").input_value() == "NVDA"
        assert not any(url.startswith(("https://", "http://")) for url in network)
        offline.close()

        page.locator("#search").fill("")
        page.locator('[data-watch="NVDA"]').click()
        page.locator("#watch-only").check()
        assert page.locator(".company-card").count() == 1
        page.locator('[data-watch="NVDA"]').click()
        assert page.locator(".company-card").count() == 0
        assert "表示対象がありません" in page.locator("#table-body").inner_text()
        page.locator("#watch-only").uncheck()
        page.locator('[data-view="valuation"]').click()
        page.locator('.company-select[data-select="MSFT"]').click()
        before = page.locator("#price-chart polyline").get_attribute("points").split()
        page.locator('[data-period="1M"]').click()
        after = page.locator("#price-chart polyline").get_attribute("points").split()
        assert len(after) < len(before)
        page.locator("#price-chart svg").focus()
        page.keyboard.press("ArrowLeft")
        assert page.locator("#chart-tooltip").is_visible()
        assert "MSFT" in page.locator("#chart-tooltip").inner_text()
        page.locator("#search").focus()
        page.locator('[data-period="3M"]').click()

        page.locator("#theme-toggle").click()
        assert page.locator("html").get_attribute("data-theme") == "dark"
        page.screenshot(path=str(OUT / "dark.png"), full_page=True)
        page.locator("#theme-toggle").click()
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_function(
            "document.querySelector('#price-chart svg').getBoundingClientRect().width / document.querySelector('#price-chart svg').viewBox.baseVal.width >= 0.9",
            timeout=3000,
        )
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path=str(OUT / "mobile.png"), full_page=True)
        page.locator("#prices").screenshot(path=str(OUT / "mobile-prices.png"))
        page.locator("#definitions summary").click()
        assert page.locator("#source-grid .source-item").count() == 7
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.set_viewport_size({"width": 1440, "height": 1050})
        page.locator("#definitions summary").click()
        page.locator("#refresh").click()
        page.wait_for_function(
            "document.getElementById('refresh').disabled === false", timeout=120000
        )
        assert "7/7社取得" in page.locator("#snapshot-status").inner_text()
        assert "更新に失敗" not in page.locator("#notice").inner_text()
        assert not errors, errors
        browser.close()
    print(
        "PASS: JS syntax, live data, filters, sort, financials, CSV, offline HTML, watchlist, charts, keyboard, theme, 390px, sources, refresh; no JS errors"
    )


if __name__ == "__main__":
    main()
