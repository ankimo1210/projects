# Market Research Saved Macro View Plan

**Goal:** 工程3cのF06画面を、工程3bで保存したマクロ・公表カレンダーsnapshotにオフライン接続する。

**Boundary:** 画面閲覧は取得を行わない。マクロ値は完全snapshotの観測時刻と公表時刻の両方が `as_of` 以前の場合だけ表示する。過去の既知値比較には同じprovider・indicator・単位・頻度の旧snapshotを明示する。公表予定は、選択したカレンダーsnapshotで当時知られた予定として表示し、実際の公表済み値と混同しない。

## Task 1: 明示snapshotのマクロ比較表

**Files:** `market-research/src/market_research/research/macro_view.py`、`market-research/tests/test_research_macro_view.py`。

- `macro_snapshot_table(store, snapshot_id, *, as_of, previous_snapshot_id=None)` は完全なマクロsnapshotを検証し、`snapshot_macro_view` の時点別値を表にする。前snapshotを選ぶ場合は同一 `CacheKey` かつ過去に観測した版に限る。
- 行は期の開始日、現在値、旧値、改定差、公表日時、観測日時、vintage精度、単位、provider、snapshot IDを保持する。
- **Red:** 当時未取得・未公表、別indicator/provider、部分snapshot、後日改定、naive時刻、同一snapshot比較。

## Task 2: 保存データのマクロ・公表画面

**Files:** `market-research/src/market_research/app_real.py`、`market-research/tests/test_workflow.py`、READMEとSTATUS。

- 完全マクロsnapshotをCIK同様に出典・観測日時付きで選ぶ。比較版は同じkeyの過去snapshotから選ぶ。最新値・改定差・全期表を表示する。
- ESRI calendarの完全snapshotを別に選び、取得時に既知だったGDP公表予定・状態を表示する。未取得時は説明を出す。カレンダーの予定を実測済み公表時刻と呼ばない。
- オフラインAppTestで価格・マクロを同じ画面から閲覧し、通信を行わないことを確認する。

2026-09-27 実装記録: 同一keyの明示snapshotだけでマクロ値と改定差を比較する共通関数を追加。
保存データ画面でマクロ・ESRI公表calendarを選べ、価格snapshotがなくても7画面のマクロタブを使える。
calendarの予定を実際の公表済み値とは区別して表示する。

2026-09-27 独立レビュー対応: `CacheKey` が同一でも行の単位・頻度・季節調整を検査してから改定差を計算する。
過去snapshotが一覧上限1000件から外れた場合、明示IDを最大20件まで追加できる。完全性・基準時刻・原本読取を検査し、不適格IDは選択肢へ入れない。
