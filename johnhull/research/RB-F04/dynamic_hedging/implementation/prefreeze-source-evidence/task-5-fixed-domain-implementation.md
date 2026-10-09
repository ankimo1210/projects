# Task 5 B fixed-domain implementation handoff

更新UTC: 2026-10-09T16:10:59.250559+00:00

## 判定と範囲

B の optional private interface を限定実装し、変更した専用テストの TDD / scoped regression / ruff を通した。独立 source review と deep generation / replay binding は root と他担当の次工程。実際の候補 bounds、金融 SE / Greeks / oracle、正式 pilot / freeze / main integration は承認も資格化もしていない。

変更は次の 2 ファイルだけ。canonical docs、deep study/replay/runner、Git、依存、public exports は変更していない。

- johnhull/hullkit/src/hullkit/_dynamic_hedging_surfaces.py
- johnhull/hullkit/tests/test_dynamic_hedging_surfaces.py

承認対象設計 SHA256: 3728b09ab65b0960a13bc54309dee13f476c606c36c6ce9b6cbcc10281ea271b
現在読取 proposal SHA256: 3728b09ab65b0960a13bc54309dee13f476c606c36c6ce9b6cbcc10281ea271b
読取 HEAD: 94895c5c2d5da71036395eab1f9e7dcc99f8dde3

## Interface / saved bindings

build_asian_cache(..., evaluation_domains=None) の既定 None は新しい metadata を追加せず、既存の global operator / rejection reason を維持する。

明示値は dates と同じ長さの list / tuple。各要素は None（その exact date の非線形評価を利用不可）または dict。Heston は state / threshold、local は spot / state / threshold のキーを過不足なく持つ。各値は half-open index pair [start, stop]。元軸の連続した 4 点以上が必要。データや query を見て箱を自動選択しない。

local date zero の spot indices は専用 t0_sheet の元軸、他は元 main 軸。呼出側の range 配列を変更しても保存 range は変わらない。保存 metadata は JSON 化できる Python int / float / dict / list:

- evaluation_domains: detached per-date descriptor list
- evaluation_domain_schema: rb-f04-asian-fixed-domain-v1
- evaluation_domain_bounds: physical endpoint bounds; unavailable date is None
- evaluation_domain_sheets: t0_sheet / main per date

正確な index range、全元 axes、上記 schema / bounds / sheet mapping と source SHA を generation / saved cache / replay / freeze の双方で結合する必要がある。構造 metadata と checksum は金融 precision gate の代替にはならない。

## Evaluation behavior

- 元 f / block_means / support_mask / primitive_groups（生 status と数値）/ original_N / shared driver IDs を削除・補修・再分母化しない。
- 明示箱で mean と 16 個の CV block component 2 に同じ fixed subaxes の既存 not-a-knot tensor cubic を適用。価格、全 Greeks、16 block Greeks / covariance を同じ価格面から得る。CV block の負値を clip しない。
- 必要 mean node の非有限値 => nonfinite_domain_nodes。必要 CV block の 1 非有限値 => nonfinite_domain_blocks。箱内部の mean raw node が既存の価格上限/下限を超える場合は domain_price_bounds（raw min/max を残す）。
- 選択箱外 => outside_evaluation_domain。明示 None date => no_evaluation_domain。元 axes の support rejection と local t0 support rejection はそのまま先行。
- exact settled / linear branch は箱、未知 state、primitive の可否に依存せず従来どおり。
- local は log S / log ell と実際の f_z を含めた spot chain を維持。Heston の homogeneity を local に流用しない。
- C2（したがって C1）は固定箱の内側、境界からの内側極限に限る。unknown gaps / outside / 別 box / exact date 間の連続性は主張しない。
- call cache / fit_quote_state の実装は無変更。元 full common call root domain と root multiplicity を狭めない。3 根の call が、Asian box 内に 1 根だけあっても nonunique のままになる専用回帰を追加。

## TDD / validation

全ログはこの ignored SDD directory にそのまま保存。

1. 新 feature 25 cases を先に追加し元 source で RED: 25 failed / 20 passed, 6.31s。新引数がまだないことによる想定 fail。
2. 初期実装 GREEN: 45 passed, 5.51s。
3. conserved groups / signed CV blocks / post interpolation bounds まで含む新 29 feature cases を original source snapshot だけ別プロセスで実行: 29 failed / 20 deselected, 0.51s。canonical source は巻き戻していない。
4. 既定 early rejection order の 2 cases を追加、初期実装で 2 failed / 49 deselected, 0.60s。missing block_means を premature lookup したことが原因。旧既定の NaN / price-bounds rejection を先行するよう修正。
5. 整形前 GREEN: 51 passed, 5.74s。
6. owned 2 files の ruff format、ruff check / ruff format --check PASS。
7. 整形後最新 GREEN: 51 passed, 5.77s; subprocess wall 6.057388106s。旧 20 tests は変更せず全て PASS、新 31 cases を追加。
8. owned paths に限定した git diff --check PASS。

専用テストは独立 reverse-axis SciPy CubicSpline 参照、価格の finite difference 3 widths、16 block / covariance 同一 operator、local f_z を落とした値との差、t0 sheet、fixed bounds / interior continuity / one-sided boundary derivative、full-root multiplicity、original N / status / NaN 保持を含む。解析 fixture / 既存固定 RNG regression に限定。新しい金融 MC、pilot/main data run、全 test suite は実行していない。

## Source binding / costs

original source SHA256:
fff3bc88d497210a846956d464317d5ddb00941a1e3ef25193f9cbaa26a8c406

final source SHA256:
d04ab70b83d19545e121338a54dd8daf5e9f5aef8dded3f1c764d4e14b6a83fe

final dedicated tests SHA256:
98e2b6f569e07a55f66c9a3cc44443c125c793d9209e10cc6d2af3dc74a18396

正確な元・新 source/test snapshots、owned diff、pytest stdout、command/returncode/SHA/wall receipts、ruff と diff-check receipts を保存した。unit-test subprocess の時間は各 receipt に記録。金融計算データ・RNG 費用は追加していない。金銭 fees / token charges は本担当の tool output に存在せず未計測。

## 次工程

1. root による独立 source review。
2. deep generation / replay 側の全 axes / 原 N / status / 16 blocks / domains detached binding を別担当が仕上げる。
3. candidate-specific financial precision / Greek / coverage gate と freeze binding を再評価。構造 PASS で financial qualification を引き上げない。
