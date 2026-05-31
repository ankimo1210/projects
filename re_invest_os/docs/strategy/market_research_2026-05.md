# Market Research — re_invest_os (2026-05)

- Date: 2026-05-31
- Purpose: MVP再定義（中立DDエンジン）の市場検証と「何ができるか」の方向づけ
- Method: Web リサーチ（競合・料金・金利環境・周辺SaaS）
- Related: `docs/design/2026-05-30-mvp-redefinition-design.md`

## 1. 市場構造は3層、空白地帯あり

| 層 | 代表 | 数字 | 収益モデル | 弱点 |
|---|---|---|---|---|
| 無料CFシミュレータ（集客装置） | 楽待 / 健美家 | 楽待 **45万会員**(2025-06)、50年CF試算が無料 | 物件**送客**・広告 | 売主寄りバイアス |
| 多機能シミュレータ | アセットランクシミュレーター | 2009年〜で**5,121名**のみ | 無料+一部有料 | 国交省 不動産情報ライブラリ連携済だが16年で5千人＝**データ連携は堀にならない** |
| 人力セカンドオピニオン | 不動産投資の教科書 / 銀座なみきFP / 東京FAS / RENOSY | スポット **¥15,000(90分)〜¥50,000/年**、多くは"無料相談"で結局送客 | 相談料 or 送客 | 手作業でスケールしない／中立を謳い funnel 化 |

**空白 = 「営業資料を自動で読み、前提の甘さ・ストレス耐性を中立に検証する」スケーラブルなエンジンは不在。**
人力セカンドオピニオンの"前提検証"を製品化し、その担い手（FP法人・スクール・管理会社）にB2Bで売るのが re_invest_os の位置。再定義の仮説は市場で裏取りできた。

## 2. タイミング（追い風）

- 日銀が短期金利を **0.75%へ（2025-12利上げ）**、2026は更に動く環境。
- ワンルーム投資は「低金利・地価上昇という前提が崩れた」(2026)、**逆ザヤ**（支払利息＞収益）リスクが現実化。
- → 甘さスコア＋ストレス（金利+1%でDSCRがどう崩れるか）= Spec 1/2 が直接答える不安。プロダクトのくさびになる物語が今ある。

## 3. 何ができるか

### A. B2C = 集客装置（既存エンジンで即着手可）
甘さスコアエンジン（Spec 1完了）で実在のワンルーム営業PDFを匿名診断（Spec 3テンプレ）→ X/note 投稿。「逆ザヤ」「前提崩壊」文脈に乗せる。最も安い需要検証。

### B. B2B/OEM = 本命の収益
- 中立FP法人: ¥15k–50kの手作業セカンドオピニオンの"前提検証"を自動化・ホワイトレーベル供給。
- 投資スクール/大家会: 受講生向け中立DDレポート生成ツール（月¥1–3万、高ARPU）。
- 賃貸管理会社: 既存オーナーへの買増し/売却/修繕提案の根拠資料（@property はポートフォリオで競合、こちらは前提検証/ストレスで差別化）。
- 融資相談（モゲチェック/INVASE隣接）: 金融機関提出前の収支耐性チェック。

### C. 差別化の軸（無料シミュレータに対して）
- 甘さスコア（confidence A–D＋risk）— "前提がどれだけ甘いか"を出すのは他になし。
- 崩れ方＋収支耐性価格帯（Spec 2）— 2026金利不安に直球。
- PDF/URLを直接読んで前提を抽出→critique — 競合は手入力前提。
- 送客しない中立性 — FP funnel に対する信頼の堀。

### D. データ連携（Market Grounding の再評価）
アセットランクが国交省ライブラリ連携済＝実現可能だが採用5千人＝B2Cの堀にならない→棚上げ判断は妥当。
ただし B2B では"根拠ある数字"が刺さるため、confidence-A 昇格機能として **B2B商品化のタイミングで復活** させる価値あり。

## 4. 次の安い検証
1. 匿名診断 5–10件を実エンジンで作成→投稿→反応計測（甘さスコアのルール検証も兼ねる）。
2. 中立FP法人/スクール 3–5社にサンプルDDレポートで打診→B2B支払い意欲を測る（¥15k–50kがアンカー）。
3. 次の実装は **Spec 2（ストレス＋収支耐性価格帯）**＝2026金利物語に最も効く・B2Bレポートの核。

## 5. 開発プラン上の含意（確定）

- **次の実装は Spec 2（ストレス＋収支耐性価格帯）** に確定。理由: 金利上昇＝逆ザヤ物語に直球で、B2Bレポートの中核であり、既存 `sensitivity.py` / `bid_ranges.py` / `max_offer.py` を再フレーミングするだけで実装コストが低い。
- Market Grounding は引き続き B2C では棚上げ。B2B商品化フェーズで confidence-A 機能として再検討。

## Sources
- 楽待: https://www.rakumachi.jp/ ／ No.1リリース: https://prtimes.jp/main/html/rd/p/000000552.000001240.html ／ CFシミュレータ: https://www.rakumachi.jp/property/investment_simulator
- アセットランクシミュレーター: https://assetranksimulator.com/ ／ ×国交省ライブラリ: https://www.atpress.ne.jp/news/413144
- 東急リバブル 2026金利見通し: https://www.livable.co.jp/solution/brand/contents/260415-1.html
- GFS ワンルーム2026検証: https://official.gfs.tokyo/blog/ue-one-room-investment
- INVASE 投資ローン金利2026: https://investment.mogecheck.jp/media/real-estate-investment-loan-interest-rates-2025
- 不動産投資の教科書 セカンドオピニオン: https://fudousan-kyokasho.com/lp-secondopinion
- 銀座なみきFP: https://www.realasset.jp/secondopinion.html
- RENOSY セカンドオピニオン: https://www.renosy.com/magazine/entries/5373
- 不動産テック市場規模: https://service.xenobrain.jp/forecastresults/market-size/saas-for-the-real-estate-industry
- 不動産SaaS 7選: https://biz-journal.jp/it/post_390535.html
