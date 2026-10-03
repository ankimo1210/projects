# M26 Market Price of Risk Implementation Plan

**Goal:** §28.1を独立計算・教材・実画面で検証し、D1と台帳受入へ渡す。
**Spec:** johnhull/docs/superpowers/specs/2026-10-03-section-28-1-market-price-of-risk.md

## Review Focus

1. loadingの符号（put・cash put）と|s|の区別、λ<0の例を正しく扱うか。
2. 無リスクportfolioの保有量の向き（式28.4）と、利回りrの確認が恒等式の言い換えに留まらないか。
3. 独立参照がItôやBSM偏微分方程式を使わず、実世界の1ステップ期待値から成長率を得ているか。
4. 消費財の注意を、convenience yieldを持つ原油の合成例で数値として示すか。
5. 旧213セルと後続節（## 7.以降）の保存を検査するか。

### Task 1: API・独立参照・数値ゲート
- [x] API unit tests（印刷3値、負のloading、broadcast、Itô、無効値10例）。
- [x] 独立求積38請求権・無リスク2組・5世界・原油・MC。hullkit禁止テスト。
- [x] 数値ゲートと保存改変5件・実API変異4件の拒否。
- [x] commit `Implement Hull market price of risk API and independent references`。

### Task 2: 4共有図・教材
- [x] `_market_price_of_risk_lesson._figures()` とhashガード。
- [x] vol10 §6.1–6.6を挿入して新セルを実行。旧213セル保存。
- [x] notebookゲートと負の対照。歴史M19–M25 pytestは新§6.xだけを除く。

### Task 3: Portal・Book・実画面
- [x] registry・件数・API索引・依存を更新。
- [x] Book/portal×1440/1000の実画面検査（16状態・16画像、MathJaxはCDN遮断のためローカルnpm mathjax@3）。

### Task 4: D1・台帳受入（所有者環境）
- [ ] 既受入25節のD1再検査とC:/F:両保管庫の復元。
- [ ] 台帳MP01–MP06、受入26・未評価280、ROADMAP/VALIDATION更新、全suite。
