# Project Measure — Handoff Note
**AISAN TECHNOLOGY CO., LTD.（アイサンテクノロジー / TSE Standard: 4667）— Take-Private (LBO) Case Study**

| | |
|---|---|
| **Status** | Preliminary case study for internal IC discussion — **not actionable** |
| **Recommendation** | **Too early; proceed to confirmatory DD only** |
| **Date / as of** | 2026-06-07 (sources retrieved 7 Jun 2026) |
| **Deliverables** | `AISAN_4667_Take_Private_Case_Study.pptx`（17 slides, EN）/ `AISAN_4667_LBO_Model.xlsx`（7 tabs, EN, live formulas） |
| **Language** | 成果物は英語（IC/英語監査向け）。本ノートは日本語ベース＋数値・固有表現は英語 |
| **Confidentiality** | Strictly Private & Confidential。投資助言・バリュエーション意見・オファーではない |
| **Data policy** | 会社・株主・経営陣への接触なし。公開情報のみ。接触は "subject to explicit authorization" の場合に限る |

---

## 1. 結論サマリ / Recommendation

> **Too early; proceed to confirmatory DD only. No bid pending the investigation report, audited / restated FY2026 financials, QoE, cash-availability analysis and clean re-underwriting.**

ファンダ的には魅力（recurring・高マージンのソフト中核＋過剰現金）だが、**子会社の特別調査（係争中）と修正後リターンのハードル未達**により、現時点での入札は時期尚早。判断は調査結果と財務再表示のクリアを前提とする。

---

## 2. ゲーティング項目 / Gating item — 子会社特別調査（最重要）

- **2026-04-03**、100%子会社 **有限会社秋測（Akisoku、秋田／2024年1月買収）** で、取締役による不適切取引・**書類偽装・在庫紛失の隠蔽・未払債務**の疑いが判明し、外部専門家＋社外役員からなる**特別調査委員会**を設置。
- 発端は **2026-03-11** の取引先からの未払債務（マーケティングセンター・長野県上田市）に関する問い合わせ。
- **FY2026.3 連結業績への影響は未確定**（業績修正・財務再表示の可能性、決算発表の遅延可能性）。
- 株価はこの開示で急落し**年初来安値 ~¥1,643**。→ モデルの参照株価 **¥1,675 は不正報道後の水準**であり、プレミアム／バリュエーションは**クリーンな株価で再設定が必要**。
- 出所: AISAN IR（特別調査委員会設置のお知らせ, 3 Apr 2026）, 日経, Yahoo Finance（PPT Slide 17 参照）。

---

## 3. 投資判断サマリ / Investment view

**ファンダ（potential, but DD-gated）**
- **公共（Public）**: 測量・土木向けCADソフト。recurring・sticky・~26%セグメントマージン（reported H1 FY26）。キャッシュカウ。
- **モビリティ・DX**: MMS／高精度3D（ダイナミック）マップ／レベル4自動運転SI。成長オプションだが**現状赤字**（reported）。
- **過剰資本**: FY25A ネット現金 ~¥4.1bn（時価総額の約44%）＋投資有価証券。capital-efficiency 改善余地は大きいが **DD-gated・pre-DDでは underwritable でない**。
- **資本構成**: ほぼ無借金。ただし買収レバレッジは QoE・調査・季節性・レンダー次第で**抑制すべき**（classic leverage-driven LBO ではない）。
- **株主**: 創業家／関係保有 ~18.5%（reported）。MBO を facilitate し得るが、**意思確認とロールオーバー経済性は confirmatory DD 項目**。

**リターン（全ケースで ~20% ハードル未達）**

| Scenario | Drivers | MOIC | Gross IRR |
|---|---|---|---|
| Downside | Rev +3% / margin ~8.5% / exit 8.0x / restatement drag | 0.78x | **−4.9%**（資本毀損） |
| **Base** | Rev +6% / margin →12% / exit 10.0x / ~1.0x leverage | **1.93x** | **14.1%** |
| Upside | Rev +8% / margin →16% / exit 11.5x（追加レバレッジは増分） | 2.46x | 19.7% |

---

## 4. モデル主要数値 / Key model figures（Excel = PPT 一致）

| 項目 | 値 |
|---|---|
| Unaffected/reference price | ¥1,675（**fraud-hit**; re-base needed） |
| Offer price | **¥2,295**（+37%） |
| Equity purchase price | ¥12,734m |
| Transaction & financing fees | ¥400m |
| New senior term loan | ¥800m（**1.0x** net debt/EBITDA） |
| Excess cash used | ¥3,400m |
| **Sponsor equity** | **¥9,034m**（Equity % ≈ 91.9%） |
| Net debt at close | **¥0**（≈0.0x; net-cash company） |
| Entry EV / EV/EBITDA / EV/EBIT | ¥8,634m / 10.79x / 14.4x |
| Exit EBITDA (FY31E) / exit multiple | ¥1,432m / 10.0x |
| Exit EV / exit net cash / exit equity | ¥14,320m / ¥3,152m / ¥17,472m |
| **MOIC / Gross IRR** | **1.93x / 14.1%** |

**Operating assumptions**: Revenue +5–7%/yr（CAGR ~6%）, EBIT margin 9.2%→12.0%, D&A ¥0.21–0.27bn, Capex 2.5% of revenue, ΔNWC 6% of Δrevenue, cash tax 31%, 100% cash sweep, 5-yr hold.

**Value-creation bridge（reconciles）**: Entry equity 9.03 + EBITDA growth 6.82 − Multiple change 1.13 + Deleverage/FCF/fees 2.75 = Exit equity **17.47**（`Returns!C9 = J9`）。

---

## 5. 修正履歴 / Corrections vs first draft（重要）

初版にはモデル数式の重大バグと過度に強い結論があり、レビューを経て修正済み。

**Excel（`build_lbo.py`）**
1. **税金**: 空セル `Assumptions!C14` 参照で全期間ゼロ → 実効税率 `G14`（31%）参照に修正。
2. **支払利息**: 二重符号で EBIT に加算していた → 正しく控除（`Pre-tax = EBIT + (負の利息)`）。
3. **手数料**: `C10`（既存債務 ¥100m）参照 → `G10`（¥400m）に修正。Uses 過小を解消。
4. **バリュエーション・ブリッジ**: 純負債項の定義誤りで非整合 → 再定義し `C9` に完全一致。
5. **レバレッジ**: 3.5x → **1.0x**（小型・季節性・調査リスクを踏まえ抑制）。
6. **注記**: 旧「conservative ~2.5x」→「~zero net debt at close; leverage deliberately constrained pending QoE / investigation / seasonality / lender diligence」。

**リターンへの影響**: 過大評価 **2.55x / 20.6%** → 修正後 **1.93x / 14.1%**。

**PPT（`build_deck.js`, 17 slides）**
- 推奨を「Proceed」→ **「Too early; proceed to confirmatory DD only」**に反転・**全箇所統一**（Slide 2 / Slide 16）。
- **子会社調査**を Slide 2（WHY NOT NOW 筆頭）・専用 Slide 15・Slide 14（リスク/DD 筆頭）・結論に反映。
- トーン緩和: "clean MBO realistic" / "ample capacity" / "textbook self-help" / "certain lever" / "Lazy balance sheet" を全廃 → "DD-gated" / "constrained" / "over-capitalised" / "not a classic leverage-driven LBO" 等へ。
- MBO 表現緩和: "supports/anchors an MBO" → "may facilitate an MBO if aligned; willingness & roll-over economics are DD items"。
- **Source Appendix（Slide 17）**: フルURL＋retrieval date＋supports のリスト化。shares outstanding を Yahoo → **AISAN公式「株主メモ」**に変更。

---

## 6. 出典 / Source traceability（PPT Slide 17、retrieved 7 Jun 2026）

1. AISAN IR — Special Investigation Committee notice (3 Apr 2026) — 調査の scope/trigger/委員会構成 — https://www.aisantec.co.jp/information/4167/
2. AISAN IR — shareholder / stock info（株主メモ）— shares outstanding 5,548,979 — https://www.aisantec.co.jp/ir/stockholders-note.html
3. AISAN IR — FY2025 results & FY2026 guidance（決算短信; 例年5月発表）— https://www.aisantec.co.jp/ir/investors/
4. Nikkei（3 Apr 2026, 調査の独立確認）— https://www.nikkei.com/nkd/industry/article/
5. Yahoo Finance JP（株価・市場反応, 年初来安値 ~¥1,643）— https://finance.yahoo.co.jp/quote/4667.T
6. IRBANK — 4667 / E04980（P&L / B/S / CF / segment / multiples）— https://irbank.net/E04980/pl
7. M&A Online — 秋測買収（Oct 2023; 実行 Jan 2024）— https://maonline.jp/news/20231013b

> **Reported / estimated / to be verified in DD**: 創業家／関係保有 ~18.5%、segment margins（Public ~26%, Mobility 赤字）、投資有価証券、FY2026E ガイダンス、秋測の影響 — いずれも reported/estimated であり、調査結果・再表示で変動し得る。

---

## 7. 未解決論点 & 次フェーズ優先DD / Open items & priority DD

- [ ] **特別調査の結果**・scope・**FY26 への定量影響／再表示**の確認。問題が秋測に**限定されるか**（グループ全体の内部統制）。
- [ ] **FY2026 決算発表の時期／延期**の確認（TDnet）。決算は例年5月、調査は4月設置のため遅延可能性あり（延期PDFは現時点で未確認）。
- [ ] 現行 **cap table** と創業家／関係者の **MBO 意思・ロールオーバー経済性**。
- [ ] **QoE**（Q4偏重の収益認識）、ソフトウェア資産計上方針。
- [ ] close時の **ネット現金・投資有価証券のマーク**、分配可能原資。
- [ ] **モビリティ・DX 単体P&L** と黒字化への道筋。
- [ ] 公共売上の **backlog・予算感応度**、顧客／案件集中度。
- [ ] **レンダー意向・債務調達力**（季節性を踏まえた）。
- [ ] **オファー／プレミアムをクリーンな調査後株価で再設定**。

---

## 8. 検証ステータス / QC status（自動抽出で確認済み）

- `Sources_Uses!G10 = 0`（Sources = Uses 一致） ✓
- `Debt_FCF!F18:J18` ending debt 非負 `[343, 0, 0, 0, 0]` ✓
- 税金は `Assumptions!G14`（31%）参照、税金ゼロ問題解消 ✓
- `Returns!C9 = J9 = ¥17.47bn`（bridge 整合） ✓
- recalc エラー **0**、Base **1.93x / 14.1%** ✓
- 旧文言／旧数値（¥6.7bn・2.5x net leverage・ample capacity・20.6%・2.55x・DO NOT PROCEED・Approach the board）**残存ゼロ** ✓
- 推奨は **"Too early; proceed to confirmatory DD only"** に統一、no-contact policy 維持 ✓

---

## 9. ファイル再生成 / Regeneration（参考）

- Excel: `python build_lbo.py` → `AISAN_4667_LBO_Model.xlsx`；検証 `python /mnt/skills/public/xlsx/scripts/recalc.py <file>`（`error_summary` を確認）。
- PPT: `node build_deck.js` → `AISAN_4667_Take_Private_Case_Study.pptx`（アイコンは `make_icons.js` で生成）。
- ビルドスクリプト（`build_lbo.py` / `build_deck.js` / `make_icons.js`）は作業ディレクトリにあり。必要であれば書き出します。
- 注: Excel はライブ数式モデルのため、軽微な更新はスクリプト再実行より**xlsxを直接編集**する方が早い。

---

*End of handoff. 追加で英語版ハンドオフ、または build スクリプトの書き出しが必要であればお知らせください。*
