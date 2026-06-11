# AISAN 4667 Excel / PPTX Improvement Progress

Updated: 2026-06-11 (round 7 — assumption rebase + classic-white redesign)  
Scope: Excel / PPTX / HTML deliverables.

## 2026-06-11 round 7 — 2.0x leverage / 80% sweep rebase + classic-white redesign

- [x] **Assumption rebase (user-directed)**: `Assumptions!G5` 1.0x → 2.0x (new senior / FY26E EBITDA, ¥1,600mm), `G8` 100% → 80% sweep. Sanity-checked as realistic (JP senior ~2-4x, conservative end given investigation; 80% = standard covenant) → adopted, no alternative scenario needed. Headline 2.07x/15.6% → **2.17x/16.8%**; walk-to-price ¥2,031 → **¥2,116**; recommendation (sub-hurdle → DD-gated) unchanged.
- [x] **Sweep<100% cash-conservation bug fixed**: `Debt_FCF!F20:J20` redefined as "FCF retained in cash (after sweep)" (= MAX(0,FCF)+paydown); Lev mini-schedule paydowns now reference `Assumptions!$G$8` (were hardwired 100%).
- [x] **Logic-check finding fixed**: Upside scenario triangulation (8% growth × 16% margin ⇒ EBITDA 1,693 vs hardcode 1,760) → `E7`=1,690, `C7`=960; exit-cash overrides documented vs mechanical schedule (Scenarios!A16).
- [x] **Systematic assumption notes**: Assumptions NOTES (1)-(8) block + note refs on input rows + per-sheet Source lines; PPT slide 10 key-assumptions footnote; per-slide Source lines added to 14 slides (data sources explicit).
- [x] **Extras**: Gross debt/EBITDA credit row; FINANCING POLICY SENSITIVITY (sweep 80 vs 100%: 16.75% vs 16.77%; rate 3.5/4.5/5.5%: 16.75/16.71/16.67%) via 3 clone mini-schedules (rows 60-82, outside print range).
- [x] **Classic-white redesign**: Excel all 8 tabs (white, Arial, navy headers, gold title rules, heatmap removed — ≥20% grid cells navy-boxed bold, 2.0x base row highlighted; 8 clean print pages re-verified). PPTX all 20 slides (cover/conclusion flipped to white, decorative circles removed, square corners, shadows off, gold header rules, teal bands → navy, slide-13 grid de-heatmapped with light-gold ≥20% highlights, chart4 legend colors disambiguated).
- [x] **Numbers propagated**: 82 text edits + chart4 cache + embedded worksheet (stale 9.03 legacy also fixed) + IRR grid 20 cells + "(base)" marker on 2.0x lev row.
- [x] **HTML regenerated** (builder hardcodes fixed: ~1.0x / 100% sweep / 0.0x net → live or new wording; Playwright check ok).
- [x] **Verification**: recalc 566 formulas 0 errors; independent Python re-implementation **93/93 PASS** (incl. 80% sweep schedule, exact 2.0x tie-out); zip dups 0; subagent visual QA of all 20 slides → fixes (slide10 footnote collision, slide18 double source line, 9/14/15 gold-rule-through-band, slide2/11 card-edge clips, slide1 SECTOR wrap) → re-verified; pytest 4 passed.
- Known cosmetic carry-over (pre-round-7, unchanged): banded-row striping on slides 9/14/15 tables has uneven row heights; footer x-offset differs on those 3 slides (separate layout).

## 2026-06-11 round 7b — three further analyses + price-move log

- [x] **Illustrative LP net returns** (`Scenarios` rows 18-27): 2/20-style economics (2% fee ×5yr, 20% carry over 8% pref, 5% MIP) → **net ≈ 1.84x / 13.0%** vs 2.17x/16.8% gross. Propagated to Slide 15 note + HTML (live from Scenarios C27/D27).
- [x] **Quarterly seasonality panel** (`Debt_FCF` rows 32-42): FY27E phasing 15/20/25/40% (blue), even costs → trough **−¥137mm at Q2-end** (below the ¥0.8bn floor) → recommend ~¥0.5bn WC RCF. Annual tie-out exact (Q4 cash 1,237.6 + sweep 350.1 = 887.5 = F21). Propagated to Slide 17 seasonality risk bullet.
- [x] **Exit routes / buyer universe**: one-line strip on Slide 14 (auto OEM/Tier-1/AV · map consolidators · construction-software strategics · sponsor secondary; appetite unverified; strategic premium = upside only).
- [x] **Share-price move logged (8-10 Jun)**: ¥1,551 → ¥1,951 (limit-up, Tier IV TSE-Growth listing application speculation per Kabutan) → ¥1,847. Added 10-Jun close to Assumptions premium panel (+24.6% implied) + Slide 8 note + FACT_CHECK. Reference ¥1,680 (labeled 5-Jun) kept — re-base is a pre-submission decision.
- [x] Verify: recalc 601 formulas 0 errors; new blocks match side-calc; 8 print pages; slides 8/14/15/17 re-rendered clean; pytest 4 passed.

## 2026-06-11 round 7c — data/design double-check + GS-style classic pass

- [x] **Data cross-check (scripted, deck+HTML vs Excel cache)** found 3 rounding-propagation errors in the PPT (Excel/HTML were correct): walk premium +26.0% → **+25.9%** (25.946%), grid 30%/10x 18.8% → **18.7%**, grid 40%/8x 11.7% → **11.6%**. All other 18 headline metrics, 20 grid cells, bridge and invariants matched. Logs updated.
- [x] **GS-results-deck restyle (all 20 slides)**: all 46 icon images + colored circles removed (functional timeline dots kept); colored heading bands → plain navy bold + hairline rule (band rects converted to their own bottom hairline); slide-2 banner → light gray + navy left bar; slide-12 returns panel → white; tables fully de-striped with hairline grids injected (slides 9/14/15 previously had zero borders and relied on striping) + navy header rules; green/red/gold headings, tags and accent bars unified to navy (semantic value colors, gold kickers, slide-8 offer highlight and waterfall up/down colors deliberately retained); slide 6/16 icon-gap layouts tightened; slide 9/14/15 footers/page numbers aligned to the standard positions.
- [x] Verify: subagent full-deck visual QA → 14 real fixes applied (taste-level findings triaged and documented); zip dups 0; 20 sldIds; stale wrong-value grep 0.

## 2026-06-11 round 8 — strategic-fit analysis (evaluator = mobility-platform strategy team)

- [x] **Research (FACT_CHECK rows added)**: AISAN × Tier IV (2017 alliance + equity investment; AutowareMaps co-development 2018; JapanTaxi AV-taxi pilot 2019; KDDI remote-ops pilot 2017; AV-bus rollouts) — AISAN is the map layer of the Autoware ecosystem. Platform context: DiDi AD × GAC Aion L4 robotaxi mass production end-2025 / 2026 pilots; DiDi Japan runs Japan rideshare (SoftBank JV).
- [x] **Synergy walk (Excel `Scenarios` rows 33-42)**: supportable offer vs exit synergy EBITDA — S=0 → ¥2,116 (walk) / **S≈¥244mm → ¥2,302 (exactly the +37% offer)** / S=¥500mm → ¥2,496. Required synergy ≈ 17% of FY31E EBITDA ≈ 2.5% of revenue.
- [x] **New slide 17 "Strategic Fit — Mobility-Platform Lens"** (deck 20 → **21 slides**): platform-fit four-point case + synergy-walk table + takeaway; acquirer kept generic ("mobility-platform owner"). Part slide21.xml (rId27/sldId 277); Content_Types, app.xml (Slides=21, TitlesOfParts), downstream chips/pages renumbered (Key Risks 17/p.18, Gating 18/p.19, Appendix p.21) and in-text (p.18)/(p.20) references updated.
- [x] **HTML**: strategic-owner-lens banner added to the walk section (live from Scenarios C39/D39).
- [x] Verify: recalc 610 formulas 0 errors; synergy table ties to side-calc (S=244.0 → ¥2,302/+37.0% exact); Excel 8 print pages; new + renumbered slides rendered clean; zip dups 0, 21 sldIds; pytest 4 passed.

## 2026-06-08 session additions

- [x] Independent re-verification of all Excel cached values (bridge, sensitivity grid, Lev_Sensitivity tie-out) — consistent.
- [x] **Repaired PPTX package**: `Valuation Context` part-name collision with `slide9.xml` (LBO Structure) caused duplicate zip entries / content-loss risk → ValCtx moved to `slide19.xml`, rels / Content_Types / sldIdLst rebuilt, zero duplicates confirmed.
- [x] Moved new slides into main body: Valuation Context = slide 9 (sec 08), Walk-to-Price & Leverage = slide 14 (sec 13). All section chips / page footers renumbered and position-verified (slides 11–13 had chip/footer swaps — fixed by Y-coordinate).
- [x] Fixed stale slide-14 (now 16) text "~14% (upside ~20%)" → "~15.6% (upside ~21%)".
- [x] Removed internal-revision wording ("corrected", "treasury-share correction") and internal filenames from submission slides.
- [x] Upside card label → "Clears if DD clears" (21.3% now above hurdle).
- [x] Added capex reconciliation footnote (slide 7), gross-returns / single-CF IRR note (slide 12), squeeze-out ≥2/3 (slide 8).
- [x] Added peer LTM EV/EBITDA numbers + positioning line to Valuation Context (Fukui 5.3x / Zenrin 4.0x / TRMB 15.9x / ADSK 22.6x / BSY 25.6x / TomTom 10.2x; Hexagon excluded).
- [x] Excel leftovers via cache-preserving zip edit: `B7` label, `C29`=C5 link, Cover contents row for Lev_Sensitivity.
- [x] FACT_CHECK "Shusoku" → "Akisoku" (kanji 有限会社秋測; romanization unverified).
- [x] pytest re-run: `4 passed in 0.97s`. markitdown + python-pptx stale grep: 0 hits.
- [x] LibreOffice installed → `recalc.py` → `{"status": "success", "total_errors": 0, "total_formulas": 428}` (after Lev_Sensitivity formula-isation); 11 key values re-verified unchanged post-recalc.
- [x] **Visual QA completed (all 19 slides rendered & inspected, 4 fix-and-verify cycles)**:
  - Slide 8: STRUCTURE stat-card value was a full sentence at 16pt overflowing the card → "Sponsor-led / MBO" + short caption.
  - Slide 9 / 14 (new slides): PASCO table cells and note lines had no explicit font size (rendered ~18pt, overflowing slide edges) → 7.5/7.0pt with word-wrap; headers restyled to deck standard (gold section number, Georgia navy left-aligned title, italic subtitle; `wrap="none"+spAutoFit` removed — it made LibreOffice center the titles).
  - Slide 19: footer note / page number / "A" chip normalized to deck styles.
  - Final pass: zip duplicates 0, section/page numbering ALL OK, stale-value grep 0 hits.

## 2026-06-08 round 4 — analytical review (GPT) response

- [x] **#1 Excess cash treatment (key)**: added cash-availability sensitivity to Excel `Returns` (Full extraction 2.07x/15.6% → Cash retained 1.76x/12.0% → Trapped 1.47x/8.1%, formula-driven) + **new Slide 15 "Excess Cash Is Central to Returns"**; Exec Summary caveat added. Headline 15.6% retained; cash framed as DD item, not underwritten.
- [x] **#3 MIP dilution**: added MIP block to `Returns` (0/5/10% → 2.07x/1.96x/1.86x · 15.6/14.4/13.2%); shown on new Slide 15.
- [x] **#2 Segment economics (illustrative)**: added a labelled "reported/estimated, non-bottom-up" segment table to `Model`. Full bottom-up segment rebuild deliberately not done (data not verifiable).
- [x] **#4 wording hedges** (Sticky/semi-recurring, Founder/related (reported), potential recurring data need).
- [x] **#7 conclusion language**: next-steps → watchlist + "excess-cash availability verified" gate.
- [ ] #5/#6 medium-priority extras (SOTP, WC seasonality, buyer universe) — out of scope this round (deadline + existing coverage).
- [x] Post-change verify: PPTX 20 slides, structure ALL CLEAN, stale 0; Excel 446 formulas, errors 0, cash/MIP values match review; pytest 4 passed.

## 2026-06-08 round 5 — second analytical review (GPT) response

- [x] **#1 Excel print/PDF layout**: fixed round-4 additions — Model segment table (merge margin D:E & value-up G:J, shortened headers) and Returns cash table (wrapped headers, shortened case labels) no longer crowd/clip; Assumptions left-block notes tightened so they stop colliding with the right block. All 8 tabs render to 8 clean single pages.
- [x] **#4 wording**: softened "fraud" → "investigation / special probe" across PPT (matches FACT_CHECK's "suspected misconduct"); kept "suspected forgery & concealment" per IR disclosure.
- [x] **#3 Slide 2**: shortened cash caveat bullet to 2 lines → bottom bullet no longer tight/cut.
- [x] **#2 stale logs**: current-state refs updated to 20 slides / 446 formulas / Source Appendix Slide 20; dated round logs kept as historical record.
- [x] Re-verify: 8-page clean Excel, 20-slide PPTX structure ALL CLEAN, stale 0, invariants hold, pytest 4 passed.

## 2026-06-08 round 6 — logic re-check + HTML build

- [x] **Independent logic check (PASS)**: re-implemented the LBO logic in Python from Assumptions and cross-checked vs Excel cache — 60+ checks (entry, S&U, operating chain, debt/FCF sweep, returns, bridge reconciliation, cash availability, MIP, walk-to-price, leverage tie-out, scenarios) all match (<0.5 tol). Methodology sound.
- [x] **Label fix**: `Debt_FCF!B13` "pre-financing" → "after interest & tax" (it is post-interest levered FCF). Values/IRR unchanged; recalc 446 formulas, 0 errors.
- [x] **HTML deliverable**: `docs/AISAN_4667_Case_Study.html` (self-contained, 37 KB) via `src/report/build_case_html.py` — numbers read live from the Excel model + peer/precedent CSVs (no hand-typing). 14 sections, inline SVG charts (rev/EBITDA bars, value-creation waterfall) + IRR heatmap. Visually QA'd in headless Chromium; tag balance OK, all key figures present, no leaked None.

## Current Status

| Area | Status | Notes |
|---|---|---|
| Excel model mechanics | Done | Treasury-share correction, reference price update, walk-to-price, leverage sensitivity and formula-cache QA completed. |
| PPTX core corrections | Done | Existing slides updated for corrected price, share count, returns, recommendation and source appendix. |
| PPTX addendum slides | Done | Added `Valuation Context` + `Walk-to-Price & Leverage` (initially appendix; later moved into body — now Slide 9 / 14). Round 4 added `Excess Cash Is Central to Returns` (Slide 15). Source Appendix is now Slide 20. |
| Fact-check log | Done | `docs/FACT_CHECK_2026-06.md` created with source URLs and retrieval dates. |
| Static QA | Done | Excel invariants, PPTX stale-value search and pytest completed. |
| Visual render QA | **Done (2026-06-08)** | LibreOffice installed; all 20 slides + all 8 Excel tabs rendered & inspected. Print/PDF layout: 8 tabs → 8 clean pages; Lev / segment / cash tables header-wrapped, Assumptions notes tightened — no touching/clipping after round-5 fixes. |
| Package structure QA | Done (2026-06-08) | All slide rels resolve, Content-Types complete, 20 unique sldIds, notes use auto slidenum fields, zip duplicates 0. |
| Metadata cleanup | Done (2026-06-08) | PPTX subject (was "PptxGenJS Presentation") and XLSX creator (was "openpyxl") replaced. |
| Peer multiples refresh | Done with caveats | `peer_multiples.csv` created from yfinance; Topcon/PASCO missing and Hexagon requires currency validation. |
| Precedent source tightening | Done with caveats | `precedent_premium_check.csv` created; PASCO and Topcon now tied to official documents, Tecnos/Kaonavi to M&A Online. |

## Checklist

- [x] Create backups of Excel/PPTX before structural edits.
- [x] Correct treasury-share treatment in Excel and propagate master values to PPTX.
- [x] Add Excel `Lev_Sensitivity` tab and walk-to-price block.
- [x] Add PPTX valuation-context slide.
- [x] Add PPTX walk-to-price / leverage slide.
- [x] Create fact-check log with source URLs.
- [x] Run static Excel QA: Sources = Uses, Returns bridge, formula errors, leverage tie-out.
- [x] Run static PPTX QA: slide count, stale-value search, chart XML search.
- [x] Run repo tests: `4 passed, 1 warning`.
- [x] Refresh public peer multiples and save to `data/processed/peer_multiples.csv`.
- [x] Tighten precedent premium source notes.
- [x] Update `FACT_CHECK_2026-06.md` with peer / precedent progress.
- [x] Update handoff with remaining open items after peer / precedent work.
- [x] Complete visual render QA after LibreOffice is available. *(Done 2026-06-08 — see the 2026-06-08 session section above.)*

## Latest QA Outputs

| Check | Result |
|---|---|
| Excel Sources = Uses | `Sources_Uses!G10 = 0.0` |
| Returns bridge | `Returns!C9 = Returns!J9 = 16602.6117` (round 7) |
| Base return | `2.169x MOIC / 16.75% IRR` (2.0x gross / 80% sweep) |
| Walk-to-price | `JPY2,116/share` for 20% gross IRR hurdle (+25.9% vs ref; +9.7% vs 6m VWAP) |
| Leverage tie-out | `Lev_Sensitivity` **2.0x row** ties to base return (diff 0.000000) |
| Financing-policy sens. | sweep 100%: 16.77% / rate 4.5%: 16.71% / 5.5%: 16.67% |
| Independent re-implementation | 93/93 checks PASS (<0.5 tol; most exact) |
| Recalc | `{"status":"success","total_errors":0,"total_formulas":566}` |
| PPTX slide count | 20 slides (incl. new "Excess Cash Is Central to Returns") |
| PPTX stale-value search | No hits for old price / returns / P-E / wording terms |
| Python tests | `4 passed, 1 warning` |
| Peer multiples | Created `data/processed/peer_multiples.csv`; 6 peers sourced, 2 limited/missing, 1 needs currency check |
| Precedent premium check | Created `data/processed/precedent_premium_check.csv`; PASCO and Topcon tied to official documents |
| Final PPTX stale-value QA | 20 slides; text/XML/chart hits empty |
| Final Excel invariant QA | Sources = Uses, bridge and leverage tie-out all true |

## Blockers

| Blocker | Impact | Workaround |
|---|---|---|
| ~~No LibreOffice in WSL~~ **Resolved 2026-06-08** | LibreOffice installed; recalc + full visual QA completed | Remaining manual step: open both files once in Windows PowerPoint / Excel before submission (font-rendering differences). |
| Live peer-data reliability | yfinance may not return complete EV/EBITDA for Japanese names or delisted/take-private peers | Label missing values clearly; do not force multiples into the deck unless sourced. |
| Tender-doc verification | Tecnos/Kaonavi still rely on secondary sources; PASCO/Topcon are now tied to official documents | Use secondary-source precedents only as context unless primary tender documents are reviewed. |
