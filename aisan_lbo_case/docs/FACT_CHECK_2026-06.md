# AISAN 4667 Fact Check Log - June 2026

Retrieved: 2026-06-07 JST  
Scope: public information only. No company, shareholder, management, lender or adviser contact.

| Claim / input | Verified value | Source URL | Retrieved | Action taken |
|---|---:|---|---:|---|
| Issued shares | 5,548,979 shares | https://www.aisantec.co.jp/ir/stock/status/ | 2026-06-07 | Use official issued shares as the gross share count. |
| Treasury shares | 268,816 shares | https://www.aisantec.co.jp/ir/stock/status/ | 2026-06-07 | Correct purchase shares to 5,280,163 shares, excluding treasury. |
| Share-status as-of date | 2026-03-31 | https://www.aisantec.co.jp/ir/stock/status/ | 2026-06-07 | Footnote treasury-share correction as official stock-status data. |
| Major shareholder: Kiyohisa Kato | 554,400 shares / 9.99% | https://www.aisantec.co.jp/ir/stock/status/ | 2026-06-07 | Keep founder/related alignment as a DD item, not an assumed rollover. |
| Major shareholder: Mitsubishi Electric | 350,000 shares / 6.30% | https://www.aisantec.co.jp/ir/stock/status/ | 2026-06-07 | Replace "remainder dispersed" with strategic-holder DD caveat. |
| Major shareholder: KDDI | 280,000 shares / 5.04% | https://www.aisantec.co.jp/ir/stock/status/ | 2026-06-07 | Replace "remainder dispersed" with strategic-holder DD caveat. |
| Major shareholder: AT Co., Ltd. | 254,000 shares / 4.57% | https://www.aisantec.co.jp/ir/stock/status/ | 2026-06-07 | Treat broader founder/related grouping as reported/estimated until legal beneficial ownership is verified. |
| Reference share price | JPY 1,680 close on 2026-06-05 | https://irbank.net/4667 and `data/processed/market_snapshot.csv` | 2026-06-07 | Rebase the model from JPY 1,675 to JPY 1,680. |
| 3-month VWAP | Approx. JPY 1,740 | `data/processed/market_snapshot.csv` from Yahoo Finance chart API | 2026-06-07 | Add premium re-basing panel. |
| 6-month VWAP | Approx. JPY 1,929 | `data/processed/market_snapshot.csv` from Yahoo Finance chart API | 2026-06-07 | Add premium re-basing panel and walk-to-price comparison. |
| May 2026 low area | Local price file shows 2026-05-20 low around JPY 1,494 and close around JPY 1,497 | `data/raw/market_data/4667_prices.csv` from Yahoo Finance chart API | 2026-06-07 | Replace stale "year-low JPY 1,643" phrasing with a May low-area caveat. |
| Subsidiary investigation notice | AISAN announced a special investigation committee on 2026-04-03 for suspected improper transactions / misconduct at 100% subsidiary Akisoku (有限会社秋測, Akita; romanization unverified — kanji per disclosure) | https://www.aisantec.co.jp/information/4167/ | 2026-06-07 | Keep governance/accounting matter as gating DD; deck uses "Akisoku" consistently. |
| FY2026 results delay notice | FY2026 results disclosure expected to exceed 50 days after fiscal year-end, submitted 2026-04-30 | https://irbank.net/4667/140120260430514374 | 2026-06-07 | Keep reporting delay as gating DD. |
| FY2026 guidance revenue / operating profit / net income | JPY 7,200mm revenue, JPY 600mm operating profit, JPY 382mm net income | https://www2.jpx.co.jp/disc/46670/140120260127539521.pdf and Yahoo Finance performance page | 2026-06-07 | Use JPY 382mm as explicit EPS/P-E input; label guidance-based. |
| Tecnos Japan precedent premium | Approx. +39% to undisturbed close, reported | https://quoteddata.com/2025/02/tender-offer-bid-announced-for-ajot-holding-tecnos-japan/ | 2026-06-07 | Use as Japan small-cap software take-private context; verify from tender documents before bid. |
| Kaonavi precedent premium | Approx. +121% to prior close, reported | https://www.smartkarma.com/home/daily-briefs/daily-brief-event-driven-kaonavi-4435-jp-small-hr-software-co-gets-121-premium-lbo-from-carlyle-and-more/ | 2026-06-07 | Use as growth buyout precedent, not a direct valuation comp. |
| Topcon precedent premium | Offer price JPY 3,300; reported premiums vary by reference date; deck uses reported prior-day / 6-month context pending source-file verification | https://global.topcon.com/invest/wp-content/uploads/ir-news/2025/TOPCON_Presentation_20250328_en.pdf | 2026-06-07 | Keep Topcon as industry/process context; verify exact premium bases before final bid. |
| PASCO precedent | Relevant geospatial take-private precedent, but mechanics differ from AISAN | `data/processed/precedent_transactions.csv` and source registry | 2026-06-07 | Include as qualitative precedent only until tender documentation is manually verified. |
| Peer multiples refresh | yfinance returned usable public snapshots for Fukui Computer, Zenrin, Trimble, Autodesk, Bentley and TomTom; Topcon/PASCO were limited or missing; Hexagon requires currency check | `data/processed/peer_multiples.csv` | 2026-06-07 | Keep peer multiples as contextual only; do not rely on them for bid valuation without terminal verification. |
| PASCO tender premium | JPY 2,140 offer represented 31.37% premium to the prior-day close and 17.45% to the six-month average | https://www.secom.co.jp/english/ir/lib_2024/notice20240905-1.pdf | 2026-06-07 | Replace PASCO "verify" placeholder with sourced premium context; note controlled-company mechanics differ. |
| Topcon tender premium | JPY 3,300 final KKR proposal represented 16.71% to prior-day close and 58.05% to six-month average | https://global.topcon.com/invest/wp-content/uploads/library/financial/2025/release_20250729_01_EN.pdf | 2026-06-07 | Keep Topcon premium in valuation-context slide; note much larger/global hardware profile. |
| Precedent premium check file | Tecnos, Kaonavi, PASCO and Topcon premium bases summarized with source quality labels | `data/processed/precedent_premium_check.csv` | 2026-06-07 | Use as the working source trace for precedent premium claims. |

## Open Verification Items

| Item | Status | Required next step |
|---|---|---|
| Founder/related holder grouping | Partly verified | Confirm beneficial ownership and whether AT Co., Ltd. is a founder-related vehicle from official securities filings / TOB counsel review. |
| Live peer multiples | Refreshed with caveats | yfinance data are public snapshots; Topcon/PASCO missing due take-private/inactive status and Hexagon requires currency validation. Verify in a live market-data terminal before bid. |
| Topcon and PASCO exact premium bases | Improved | Source bases now tied to official Topcon and SECOM/ITOCHU documents; final IC pack should still footnote exact reference dates. |
| Visual render QA | Completed 2026-06-08 | LibreOffice installed; all 19 slides and all 8 Excel tabs rendered and inspected; fixes applied and re-verified (see PROGRESS_TODO). |
