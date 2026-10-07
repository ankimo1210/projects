# Ch1 節別受入 — 2026-10-07

開始2026-10-06、最終受入2026-10-07。

目的：古い章から教材と計算を受け入れる。第1便は Hull 11e Global Edition
Ch1 §1.1–§1.10 の10節・23要件。計算ロジック先行の基点は
`995188e6`、作業ブランチは `codex/johnhull-acceptance`。
開発側の P7/P8 と作業場所を分離し、mainへの統合・pushは行わない。

## 原典と範囲

原典は `options, futures and other derivatives 11th.pdf` pp.24–40。
SHA-256: `8bc6e2f04fad95e4eeb40d0526219ba5f9228ee3d2ea3eaaf80870bdf7ccb482`。
既存の [Ch1節メモ](prep/sections/ch01.md) の23要件を、原典本文、
教材、別方法の算術参照、実際のBook/portal表示で確認した。章末問題、
現在の制度調査、投資推奨、市場モデル較正は受入範囲に含めない。

| 節 | ページ | 要件数 | 独立照合した値 | 共有図 |
|---|---|---:|---:|---|
| 1.1 取引所 | 24–25 | 2 | — | — |
| 1.2 OTC | 25–28 | 3 | — | — |
| 1.3 forward | 28–30 | 3 | 9 | 買い・売りの満期受払 |
| 1.4 futures | 30–31 | 2 | — | — |
| 1.5 options | 31–33 | 3 | 6 | call買い・put売りの利益 |
| 1.6 取引目的 | 33–34 | 2 | — | — |
| 1.7 hedgers | 34–36 | 2 | 8 | 費用込みput保険 |
| 1.8 speculators | 36–39 | 3 | 13 | 同じ初期資金の株・call比較 |
| 1.9 arbitrage | 39 | 1 | 1 | — |
| 1.10 dangers | 39–40 | 2 | — | — |
| **計** | | **23** | **37** | **4図・8trace** |

制度・市場規模は原典時点（2019年末）、quoteは2020-05-21の例。
USD/GBPは1GBP当たりUSD。金額はUSD、数量は株数・GBP額・契約倍率を
各表・図で明示する。option・現物/先物の比較は資金利息・手数料を省略する。
§1.3 carry例は例外で、年5%の利息3 USDを含めて価格63と利益4/5を照合する。

## 教材と修正

[private教材](../hullkit/src/hullkit/_chapter01_lesson.py) を
[vol12](../volumes/12_qualitative_summary/qualitative_summary.ipynb) と
`report/site/chapters/ch01.html` で共有する。既存portalの204図/12テーマと
公開APIは変更しない。Ch1ページは既存portalの子ディレクトリへ生成し、
Bookから到達できる。通常の `make hull-report` もCh1を再生成する。
直接生成はreportのREADMEにある2コマンドを実行する。
専用builderのclean出力先・既存ページ更新を回帰テストで確認し、
実際のmakeターゲットでも欠落からの再生成を確認する。
旧証跡がpinする `report_builder/build.py` はそのままに、
MakefileのJohnHull専用ターゲットにCh1生成を追加した。
vol12のCh8以降のソースセルは基点と同一。

- 不足していた10節の説明・確認問い・数値表を追加。単位・現金符号・
  担保と費用・契約数と原資産数量・満期payoffとpremium込みprofitを区別。
- 株価非負の領域ではlong forwardの損失は固定数量×Kで有限。
  古い概説の「両側に無限」を修正し、zeroを含む図を描く。
- 独立レビュー指摘を修正：premium式に数量を明示、§1.9のUSD/GBP
  二通貨収支表を追加、Book↔portalリンクを実際にクリックして到達確認。
- 表示幅変更に図が追随するようResizeObserverを追加。固定幅で検査し、
  証跡撮影時だけ高さを拡張する。fullPage撮影の再レイアウトによる
  見切れを避け、節見出しから図末尾まで保存した。

説明・renderedは全23要件で必須。§1.1/1.2/1.4/1.6/1.10と
D1.5-03（歴史的な市場quoteの傾向）の計算・独立数値軸は、
計算モデルを要求しないため理由付きN/A。制度や目的は文章、
少数の算術と通貨収支は単位付き表で確認する。追加図が不要な
要件には理由付きN/Aを設定し、節自体の画面検査は省略していない。

## 検証と証跡

- [Decimal参照](../hullkit/tests/_chapter01_reference.py) はhullkitを
  importせず、現金の脚と別の区分式で37値・4図の全点を照合。
  最大絶対誤差 `2.546585164964199e-11`、許容誤差 `1e-7`。
- vol12を新規実行し、保存出力を再実行結果と照合。
  portalとJupyter Bookを構築。Bookの既存MathJax依存は許可するが、
  Ch1 portalは外部runtime要求なし。
- 10節×Book/portal×幅1440/1000（高さ1050）の**40状態**で、
  見出し・意味・37表示値・4図の点と符号・凡例・軸・overflowを検査。
  凡例の非表示/復元と、図を1USD変更した負の対照を両画面で実施。
  全40枚のPNGを目視し、見切れ・重なりがないことを確認。
- 初回登録でN/Aの必須refs空リスト欠落を台帳検査が検出。
  登録処理を修正し、同じ台帳validatorで書込前に検査する。
- 不適切なpremium・数量100倍・役割・欠損図・NaNを独立参照が拒否。
  検査省略・capture欠損/重複も受入検証器の負のテストで拒否。
- hullkit+report全suiteは **6,098 passed・6 skipped**（登録前の全suite）。
  登録後は件数期待を43/263へ更新し、台帳の全41ケースを再検査してPASS。
  853ソースのうち変更はこの件数テストのみで、初回ソース/結果と
  metadata repairのコマンド・成功結果を記録した。計算ソースは不変。
  [full-suite.json](validation/chapter-01/full-suite.json) に最終ソースのハッシュを保持し、
  lint/format・release契約も確認。個別数値・画面結果は
  [numerical-check](validation/chapter-01/numerical-check.json) /
  [browser-check](validation/chapter-01/browser-check.json)。
- 旧33受入節は旧記録とartifact検査を保持。MyST CSSのcache queryだけが
  変わるページは、既存HTMLのSHA-256へ完全一致する表現のみ復元する。
  CSS内容を確認し、過去の記録は書き換えない。
  [cache検査](validation/chapter-01/book-cache-check.json)。
- 40画像を既存のprimary/mirror保管庫に保存し、両コピーから独立に
  復元する。実結果・ハッシュ・全要件の束ねは
  [acceptance-check](validation/chapter-01/acceptance-check.json) と
  [image-manifest](validation/chapter-01/image-manifest.json) に固定する。

最終判定は個別要件を持つ `section_ledger.json`、
[生成された集計](SECTION_LEDGER.md)、上記PASS証跡で確認する。
外部の原典データ欠落を補う必要はCh1本文範囲ではなく、歴史的quoteは
現在の市場条件を表さない。Americanは権利を説明し、利益図は終端比較。

## 再検証

リポジトリrootの既存Python環境とCh1作業先を使う。依存は追加しない。
`PYTHONPATH` に当該checkoutの `johnhull/hullkit/src`、
`johnhull/report` とrootを指定する。ブラウザは既存Playwright/Chromium、
保管庫は [D1方針](EVIDENCE_POLICY.md) の環境変数を設定する。

1. `python johnhull/scripts/verify_chapter01_acceptance.py build`
2. `node johnhull/scripts/verify_chapter01_browser.cjs`
3. `python johnhull/scripts/verify_chapter01_acceptance.py verify`
4. `chapter_acceptance.full_suite({"output_dir":"docs/validation/chapter-01"})`
5. `python johnhull/scripts/verify_chapter01_acceptance.py bind`
6. `python johnhull/scripts/verify_chapter01_acceptance.py register`
7. `python johnhull/scripts/verify_section_ledger.py --write-summary`
8. `python johnhull/scripts/verify_section_ledger.py --check-artifacts`

次はCh2の11節を同じ原典順で受け入れる。Ch1のローカル受入と
開発側のP8是正・main統合の状態を混同しない。
