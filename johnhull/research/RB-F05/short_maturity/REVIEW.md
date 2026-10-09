# RB-F05 short maturity 最終 overlay 独立レビュー

- 日付: 2026-10-09
- 結論: **Critical 0、Important 0。保存済み金融結果と最終 overlay の整合性を承認。**
- 最新対象: assessment.json、cold/fresh receipts、current source proof、両 CAS 復元記録、実行済み short_maturity_dml.ipynb と 3 PNG。
- 作業: read-only。canonical source/test/artifact/Git 編集、新 RNG、追加教師、NN training、checkpoint 選び直しなし。
- 最終独立検査: **208 checks PASS**、2.529031 秒。実行 script は /tmp/rbf05_final_overlay_audit.py。
- phase acceptance / Git 統合は root 担当で、本承認とは別。元 main acceptedFalse / teachingAcceptanceFalse と pending/unknown は不変。

## 採否

固定 synthetic ドメインの教師 640 点は全 ready。Delta-DML は seed 11/29/47 の 3 paired 比較すべてで raw Delta RMSE を改善した。これは保存済み固定条件の教育比較である。

**標準 NN accelerator は不採用。** 原 336 test 点、全 6 fits、raw/safe の両方を対象に凍結済み C/Delta/KGamma の点ごとの精度条件を再計算し、全 fit が不合格。全 6 payback eligibleFalse / queriesNone を保持した。Hermite は同じ原 336 点すべてで合格。オンライン時刻の速さから等精度の NN 採用または費用回収を推論しない。

| fit | seed | raw 3 成分同時合格 /336 | safe 同時合格 /336 | payback |
| --- | --- | --- | --- | --- |
| fit0 price-only | 11 | 0 | 193 | ineligible / undefined |
| fit1 Delta-DML | 11 | 0 | 156 | ineligible / undefined |
| fit2 price-only | 29 | 0 | 191 | ineligible / undefined |
| fit3 Delta-DML | 29 | 0 | 190 | ineligible / undefined |
| fit4 price-only | 47 | 0 | 182 | ineligible / undefined |
| fit5 Delta-DML | 47 | 4 | 169 | ineligible / undefined |

Gamma は同じ scalar price の physical S 二階微分。Gamma training の主張や Gamma utility 承認には読み替えていない。

## 独立数値検査

### 既存 main 検査の identity

先の /tmp/rbf05-main-independent-review.json は、640 compact teacher の元 N/平均/M2/cov/SE、336 ordinary-mixture/Merton references、6 fits の paired initial/batch/update roster、全 raw/safe jet/prediction、48 buckets、10 OOD/expiry、Hermite 4680 nodes、448 timings、674 expense roster、7715 arrays を独立確認済み。現在の JSON/arrays/source はその対象と同一。今回も実 NPZ の arrays digest を算出し、assessment accuracy を再計算した。

保存値の SHA 一致は provenance/転送 identity の検査。金融値の成立は独立数学と明示 tolerance による数値検査に基づく。

### Fresh

/tmp/rbf05_fresh_independent_audit.py で全 12 cases、原 N=1048576、全 15 joint columns、全 180 method slots、84 arrays を検査した。保存 raw primitives から independent conditional/raw/CRN Greek 値、long-double 全 N の一次・二次集計、M2/cov/SE、ordinary mixture/density/tighter/tail references、finite-h targets、6SE 支持状態を再計算。新 RNG は禁止した。

原 roster: analytic_deterministic 18、supported 150、negative_control 12、unknown/unsupported/inconclusive 0。negative_control は 180 分母に残り、不合格を削除していない。36 seed roles は予約 ledger 3870 の実値/用途/重複なしを確認。今回 fresh seed byte 再生成は行っていない。

数値最大差: mean 1.78435e-12、M2 3.60012e-5（大きな joint scale に対する許容 relative tolerance 内）、cov 3.43334e-11、SE 4.3021e-16、primary/tighter reference 約 2.13e-14。固定 tolerance/gate を緩めていない。full-N diagnostic mark 費用と、main teacher の active-only policy を分離。

### Cold

子 reviewer の /tmp/rbf05_cold_receipt_audit.json が実 receipt、14 methods ×2 rows の C/Delta/Gamma/route、source captures と main actual bindings を独立確認。今回も current receipt/assessment/current source と結合して確認した。

初回 collector の schema KeyError は cold_process_cost_initial_failed.json に残り、金融 fit failure ではなく研究プロセス費用。金融 source/fit/selection は不変。

## 実測費用の範囲

| 独立 outer 実測 | 秒 | 範囲 |
| --- | --- | --- |
| Main construction CLI | 46.085081 | 完全 offline construction。categories 39.220165 と serialization 4.184680 は内側 |
| Successful cold process | 18.151012 | 新 interpreter、保存 artifact 検証と 2-row whole-Greek serving。内側計 17.815115 |
| Failed initial cold collector | 18.026820 | 別プロセスの研究費用、成功 cold に合算しない |
| Fresh generation CLI | 26.444452 | fresh function 26.154823 を包含。その中に categories 22.260426 と serialization 3.795266 |
| Separate fresh saved replay | 14.599338 | generation と別の研究検証 |
| Main CAS restore + semantic checks | 24.477096 | 両 store。shared setup をここへ 1 回課金 |
| Fresh store put | 5.278692 | 両 store 保存と manifest。restore と別 |
| Fresh CAS restore + semantic checks | 29.102934 | 両 store。実 repeated main saved check は内側。shared setup を再課金しない |

最後の 3 項目は disjoint research subtotal 58.858721 秒。これは cold-start minimum でも研究の総費用でもない。Main/fresh の categories、function、CLI、CAS inner semantic/restore と enclosing wall を重複加算しない。

cold 18.151 秒は artifact-backed validated serving の一測定。OS disk cache は flush されず、teacher/training の最初からの再実行を含まない。全 method の比較 cold benchmark ではない。

serialization/cold_import/archive_load/pilot_freeze/fresh の 5 overlay IDs に receipt があることは、正式 pilot 生成・独立 review・全復元を含む研究費全体の完全解消を意味しない。pilot_freeze 6.590492 秒は cold pipeline 内での凍結 pilot 再検証。元主実験の unknown/pending と区別した current 表示を確認した。

## Source proof と CAS

凍結 financial source 10 件は正式 pilot/main registry と current bytes が全件一致し、検査前後とも不変。registry は /tmp/rbf05-final-overlay-source-proof.json に保存。

fresh_support.py は元測定 SHA と不変。fresh stopwatch 2 本は Ruff の import order/format 後の current SHA と、保持した exact measured source TXT の旧 SHA を区別。TXT は元 receipt/CAS proof の SHA と一致。全 imports の alias/order を正規化した完全 AST と、その他の完全 AST が current .py と同値。測定し直して結果を交換していない。

両 primary/mirror の 4 実復元 NPZ を読み、canonical manifest と全 file SHA/byte count を直接照合。main metadata、fresh metadata、元測定 wrapper bytes/current measured map も照合。各 fresh reference.npz symlink は同 role の独立復元 main に向き、canonical fallback はない。

CAS semantic checker 自体の 4/4 実行は別 reviewer が担当し、RNG/training/optimizer traps、main 640/6/336/448、fresh 12/180 の成功 receipt を作成。本 reviewer は実復元 bytes と既に独立確認済み canonical の identity、実測 source、closed bindings、scope/費用関係を再確認した。ここで新しく CAS numerical execution をしたとは主張しない。

## 実 notebook / 表示

current notebook の実 4 cells execution_count=1,2,3,4、error なし、実 3 PNG。埋込 PNG と抽出 /tmp PNG と current NOTEBOOK_VISUAL_REVIEW.json の SHA/bytes が全一致。current assessment/notebook の source SHA も一致。

全 3 図を独立目視。ラベル・凡例・パネル/caption が読め、数値と結論の重要な表示欠陥なし。更新 figure3 は unresolved five external IDs と full pilot/review research cost を明示し、全 6 ineligible/Q unknown を表示した。

表も原 teacher 512/128、6 fits ×512 actual updates/336 denominator、576 bucket rows、各 fit 原 10 OOD/expiry、674 original expense rows、14 actual costs、5 resolved IDs、6 payback entriesを保持。expiry undefined Greeks と invalid contracts、元 pending/unknown は 0 に置換されない。

actual cell 1 の guard は checker より前に RNG/training/optimizer/network を禁止。実 assessment guard 関数を抽出し、current positive と missing→unknown を確認。wrong protocol/arrays、negative/bool cost、duplicate expense、foreign fit、negative queries、numeric eligible の 8 異常入力は全拒否。whole notebook の新実験は起動していない。

## 残る範囲・既知 Minor

新しい Critical/Important はない。先の literal ATM endpoint rounding と finite-h Gamma の price roundoff Minor は保持。小 h の Gamma 差分は price 誤差を h^-2 倍に増幅するため、保存 finite_h_bias 全体をモデル bias と呼ばない。6SE は diagnostic で、同時 coverage の証明ではない。synthetic calendar は実市場 holiday/early-close 契約の保証ではない。

root から full suites 7998 PASS /6 skip、文言変更対象 22 PASS、最終 Ruff/format 19 Python PASS、branch release gate PASS の報告を受けた。本 reviewer はこの broad suite を再実行せず、上記独立監査と実 notebook evidence を結論の根拠とした。

## 保存した根拠

- /tmp/rbf05-final-overlay-review.json — typed current result、208 checks、8 guards、実 bindings/source/costs/PNGs
- /tmp/rbf05-final-overlay-source-proof.json — frozen10/current supplemental/measured source/actual artifact SHA
- /tmp/rbf05_final_overlay_audit.py — 再現 script
- /tmp/rbf05-fresh-independent-audit.json / /tmp/rbf05_fresh_independent_audit.py
- /tmp/rbf05_cold_receipt_audit.json / /tmp/rbf05_cold_receipt_audit.py
- /tmp/rbf05-main-independent-review.json / .md
- /tmp/rbf05-formal-pilot-review.json / .md

金融主実験は未統合の immutable 記録としてレビュー済み。教育比較成立と標準 NN 不採用の結論を維持する。
