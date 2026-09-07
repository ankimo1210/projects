# Google Health 読み取り source 契約

公式公開文書確認日: **2026-09-07**。本人 API、実 DB、token、`.env` はこの確認で使用していない。
この文書は `src/health/source_catalog.json` の根拠と、取得側の公開インターフェースを記録する。
表示用 `endpoints.CATALOG` と取得対象は別である。

## 公式資料と判定

| 根拠 | 確認した契約 |
|---|---|
| [型一覧](https://developers.google.com/health/data-types) | 型、record 構造、公開 method、scope。43型を観測。件数を API 全体の不変条件にはしない |
| [list](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints/list) | 元 dataPoints、任意の filter、nextPageToken。通常最大10000点、exercise/sleep は最大25点 |
| [get](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints/get) | list が返す識別可能な name の単一 DataPoint。list/get 間の詳細差は実アカウントで未確認 |
| [reconcile](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints/reconcile) | 複数 source を統合した系列。元 source の完全な代用にはならない |
| [dailyRollUp](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints/dailyRollUp) | civil closed-open range 必須。calories-in-heart-rate-zone / heart-rate / active-minutes / total-calories は最大14日、それ以外は90日。日次集約を原本と混同しない |
| [nutrition](https://developers.google.com/health/data-types/nutrition) | food と food-measurement-unit は共有参照、nutrition-log/hydration-log は本人の記録。scope は nutrition.readonly |
| [resource 一覧](https://developers.google.com/health/reference/rest) | profile、identity、settings、IRN profile、pairedDevices と各 read method |
| [quotas](https://developers.google.com/health/rate-limits) | request pacing と429停止の根拠。既存 client の physical-send budget/pace を共有 |

`candidate` は公開された読み取り契約があるという意味で、本人の認可・データの存在を確認済みという意味ではない。
`unsupported` は公式一覧に読み取り method/scope がない型。
`unverified` は資料間の不一致や未実装の別形式契約を含む。詳細理由は各 `notes` に残す。
`methods` は公開された操作を記録するため write 名も含むが、実行対象は `preferred_method` の読み取りだけ。
`readonly_scopes` に write scope がある JSON は loader が拒否する。

## 範囲と取得完全性

- list/reconcile の filter は任意。しかし「省略するとアカウントの全履歴を漏れなく返す」という保証や最古の境界は確認できていない。時系列の `unbounded_verified` はすべて false。
- ArchiveEngine は `build_request(s, allow_unverified_unbounded=True)` で明示的に filter を省略し、全ページを試行できる。これは完了した query の証拠であり、全履歴の証明ではない。履歴状態は `unknown_history` を維持する。
- 日付引数は `start <= time < end`。civil 日付に架空の UTC offset を付けない。list/reconcile の `max_range_days=None` は上限未記載であり、5年等の独自打ち切りを意味しない。安全な probe は通常1日の範囲を使うが、これを API の最大日数とは呼ばない。
- interval/session は `{type_snake}.interval.civil_start_time`、sample は `{type_snake}.sample_time.civil_time`、daily は `{type_snake}.date`。公式の list filter パターンと型一覧の識別子に従う。daily の公式例は camelCase も含むため、実アカウントで拒否された場合に成功扱いせず証拠として記録する。
- sleep は `sleep.interval.civil_end_time`。ECG は `electrocardiogram.interval.start_time >= "...Z"` **のみ**。ECG に `< end` を足す builder 呼び出しは拒否する。ECG の date 入力は明示的に UTC 0時を意味する。ECG query は下限以降であり、1日だけ取得したとは主張しない。
- `dailyRollUp` の required range と最大日数は builder が検証する。page token は POST body、list/reconcile は query parameter に入れ、他の条件を変えない。
- `dailyRollUp` の両端は `{"date": {"year": ..., "month": ..., "day": ...}, "time": {}}` とし、civil の午前0時を明示する。[CivilDateTime](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints#CivilDateTime) は `time` を optional・省略時は午前0時と記載しているが、builder では既存 projection と同じ明示形式を使う。
- `dailyRollUp` の optional `pageSize` は送らず、API の既定値を使う。2026-09-07 の実API動作確認では、`total-calories` と `calories-in-heart-rate-zone` は両端に `time: {}` を追加しても `pageSize: 1000` 付きでは HTTP 400、`pageSize` を省くと両方 HTTP 200・7点だった。原因を未対応 field や backend の仕様と推測せず、この観測に合わせる。[公式 dailyRollUp](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints/dailyRollUp) の既定上限1440点は、日次14日/90日の要求区間より大きい。ただし終端は件数から推定せず、レスポンスに `nextPageToken` があれば POST body の `pageToken` で続行する。list/reconcile の `pageSize` は従来どおり指定する。比較用の private raw response は本修正では読まず、変更・commit しない。
- metadata は現在の resource snapshot、food は参照データ。いずれも時系列の全履歴状態とは別に扱う。

### 2026-09-07: VO2 Max の識別子訂正

[型一覧](https://developers.google.com/health/data-types)の `dataType`・`filter parameter` 列と、同一覧がリンクする DataPoint 定義を再照合した。表示名を切り詰めて識別子を生成せず、次の正式値を使用する。[dailyRollUp](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints/dailyRollUp) も `run-vo2-max` を明記している。

| 正式 dataType（list の key は `.list` を付加） | list filter field |
|---|---|
| `daily-vo2-max` | `daily_vo2_max.date` |
| `run-vo2-max` | `run_vo2_max.sample_time.civil_time` |
| `vo2-max` | `vo2_max.sample_time.civil_time` |

request path は `/v4/users/me/dataTypes/{dataType}/dataPoints`。旧 `daily-vo` / `run-vo` / `vo` は取得契約の誤りであり、provider の未対応判定ではない。この訂正は静的 catalog と builder のみを変更し、旧 ID の失敗観測・保存済みレスポンスは削除しない。修正後の live 成否は別途の bounded probe で確認する。

## 公開 Python インターフェース

```python
@dataclass(frozen=True)
class RequestSpec:
    method: str                     # HTTP verb: GET / readonly POST
    path: str                       # /v4/...; host/header/token を含めない
    params: dict = field(default_factory=dict)
    body: dict | None = None

# SourceSpec の必須フィールドは実装計画どおり:
# key, data_type, label, path, methods, preferred_method, readonly_scopes,
# filter_kind, filter_field, page_size, max_range_days, unbounded_verified,
# representation, availability, evidence_url, checked_at
# 後方互換の追加既定値:
# response_key='dataPoints', detail_parent=None, range_evidence_url=None, notes=''

load_sources(path: Path | None = None) -> tuple[SourceSpec, ...]
build_request(source: SourceSpec, *, start: date | None = None,
              end: date | None = None, page_token: str | None = None,
              resource_name: str | None = None,
              allow_unverified_unbounded: bool = False) -> RequestSpec
with_page_token(request: RequestSpec, token: str | None) -> RequestSpec
source_points(source: SourceSpec, payload: dict) -> list[dict]
HealthClient.request_page(request: RequestSpec, budget: RequestBudget,
                          *, capture: Callable[[bytes, int], None] | None = None) -> dict
run_source_probe(client, output_dir: Path, sources: Sequence[SourceSpec],
                 today: date | None = None, max_requests: int = 200,
                 *, report: Callable[[str], None] | None = None) -> dict
```

`SourceSpec.path` は実際の request route を保持する。list に suffix はなく、reconcile/dailyRollUp は明示した suffix を持つ。
get の `{dataPoint}` / `{pairedDevice}` は親 list の `name` で解決する。`resource_name` は `users/...` 形式のみ許可し、host/query/traversal/別 data_type を拒否する。
`detail_parent` は親 source の **key**。詳細の未観測 ID を推測しない。親一覧に名前がなければ詳細は pending として残す。
`response_key=None` は単一 resource、`pairedDevices` は device のリスト、aggregate は `rollupDataPoints`。
Proto JSON の空 repeated field 省略は空配列、明示的 null/不正型はエラー。未知属性・同時刻の複数 source を削除しない。

`HealthClient(..., response_observer=callback)` の callback は `(RequestSpec, bytes, status_code)`。
既存 daily_rollup/iter_reconciled も同じ経路を通る。順序は physical send → capture → observer → 401 refresh 判定 → JSON/error parse。
401 の各応答を保存し、再試行も request budget に数える。OAuth token endpoint は observer に渡さない。
保存 callback の例外はそのまま伝播する。保存失敗を握りつぶして parser/refresh へ進まない。
ここで保存する bytes は `requests.Response.content`（HTTP content decoding 後の本文）であり、TCP/HTTP header や圧縮転送 bytes の packet capture ではない。

## 本人 metadata と詳細

| Resource | method / path | readonly scope | 補足 |
|---|---|---|---|
| Profile | [getProfile](https://developers.google.com/health/reference/rest/v4/users/getProfile), `/v4/users/me/profile` | profile | 単一 snapshot |
| Identity | [getIdentity](https://developers.google.com/health/reference/rest/v4/users/getIdentity), `/v4/users/me/identity` | activity_and_fitness | 公式には複数 scope のいずれかで可。既存 scope から1つだけ選ぶ |
| Settings | [getSettings](https://developers.google.com/health/reference/rest/v4/users/getSettings), `/v4/users/me/settings` | settings | 単一 snapshot |
| IRN profile | [getIrnProfile](https://developers.google.com/health/reference/rest/v4/users/getIrnProfile), `/v4/users/me/irnProfile` | irn | 単一 snapshot |
| Paired devices | [list](https://developers.google.com/health/reference/rest/v4/users.pairedDevices/list), `/v4/users/me/pairedDevices` | settings | 最大100、nextPageToken。返却キー pairedDevices |
| Paired device detail | [get](https://developers.google.com/health/reference/rest/v4/users.pairedDevices/get), list の name | settings | prose に devices とあるが HTTP template は pairedDevices。HTTP template と観測 name に限定 |

get が公開されている body-fat / blood-glucose / core-body-temperature / exercise / height / hydration-log / nutrition-log / sleep / weight / food / food-measurement-unit は別 stream として登録する。
[exercise TCX export](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints/exportExerciseTcx) は activity_and_fitness **かつ** location の readonly scope が必要。
HTTP では `alt=media` の専用 TCX 本文契約があり、今回の dict を返す request_page では自動取得しない。
`exercise.exportExerciseTcx` は unverified として一覧に残す。通常の exercise get で TCX まで取得済みとは主張しない。

## Probe の出力と運用

```bash
PYTHONPATH=/home/kazumasa/projects/.claude/worktrees/health-full-archive-nextjs/health/src \
  /home/kazumasa/projects/.venv/bin/python health/scripts/probe_datatypes.py \
  --all-sources --max-requests 200 --output-dir /path/to/private-probe
```

上記は本人認可を使う手動実行例。この実装検証では実行していない。
`--all-sources` がなければ従来の14 metric probe を維持する。
全 source モードは最近・31日前・暦上5年前より1日前を独立した query にし、全体 request budget を共有する。
全ページが揃った成功 query だけ complete/empty。通常の source failure は他 source を継続し、401認可失効・429・cap・storage error は停止する。
未訪問は pending、途中は partial。各 entry の `history_status` は時系列について unknown_history のまま。
各 source の `requests` に要求範囲・query状態・page cursor、`responses` に正確な request と本文 path / HTTP status / byte数を記録する。
raw byte count とデコード済み point count は別で、source の page_count は401/errorを含む観測応答数。

- `manifest.json`: 最新 run の要約。エラー理由は固定分類で、upstream の本文や秘密値を載せない。
- `runs/<uuid>/manifest.json`: run ごとの要約。
- `runs/<uuid>/<source-key>/response-00000.bin`: JSON/error/不正 JSON を含む原本文。新 run は旧本文を上書きしない。
- ファイルは0600、作成する directory は0700。atomic replace/fsync。ユーザーが指定した既存親 directory の権限は変更しない。
- stdout は source key・状態・件数のみ。出力はすべて private health data として扱い、commit/公開しない。
- 終了コード0は audit の予定 request が終了した意味で、全履歴取得完了ではない。途中停止/失敗/未訪問 detail は1、認可失効は2。unsupported/unverified の catalog 記録は manifest に残る。

## 型ごとの source 一覧

scope の表記 `x` は `https://www.googleapis.com/auth/googlehealth.x.readonly` の省略。
各行の公開操作は JSON の `methods`、詳細 root は `evidence_url`、range 根拠は `range_evidence_url` に保存する。

| 型 | 優先 method | 保存形態 | scope | 公開契約状態 |
|---|---|---|---|---|
| `active-energy-burned` | list | source | activity_and_fitness | candidate |
| `active-minutes` | list | source | activity_and_fitness | candidate |
| `active-zone-minutes` | list | source | activity_and_fitness | candidate |
| `activity-level` | list | source | activity_and_fitness | candidate |
| `altitude` | list | source | activity_and_fitness | candidate |
| `blood-glucose` | list | source | health_metrics_and_measurements | candidate |
| `body-fat` | list | source | health_metrics_and_measurements | candidate |
| `calories-in-heart-rate-zone` | dailyRollUp | aggregate | activity_and_fitness | candidate |
| `core-body-temperature` | list | source | health_metrics_and_measurements | candidate |
| `daily-heart-rate-variability` | list | source | health_metrics_and_measurements | candidate |
| `daily-heart-rate-zones` | list | source | health_metrics_and_measurements | candidate |
| `daily-oxygen-saturation` | list | source | health_metrics_and_measurements | candidate |
| `daily-respiratory-rate` | list | source | health_metrics_and_measurements | candidate |
| `daily-resting-heart-rate` | list | source | health_metrics_and_measurements | candidate |
| `daily-sleep-temperature-derivations` | list | source | health_metrics_and_measurements | candidate |
| `daily-vo2-max` | list | source | activity_and_fitness | candidate |
| `distance` | list | source | activity_and_fitness | candidate |
| `electrocardiogram` | list | source | ecg | candidate |
| `exercise` | list | source | activity_and_fitness | candidate |
| `floors` | reconcile | reconciled | activity_and_fitness | candidate |
| `food` | list | reference | nutrition | candidate |
| `food-measurement-unit` | list | reference | nutrition | candidate |
| `heart-rate` | list | source | health_metrics_and_measurements | candidate |
| `heart-rate-variability` | list | source | health_metrics_and_measurements | candidate |
| `height` | list | source | health_metrics_and_measurements | candidate |
| `hydration-log` | list | source | nutrition | candidate |
| `irregular-rhythm-notification` | list | source | irn | candidate |
| `menstrual-period` | なし | source | なし | unsupported |
| `moods` | なし | source | なし | unsupported |
| `nutrition-log` | list | source | nutrition | candidate |
| `ovulation-test` | なし | source | なし | unsupported |
| `oxygen-saturation` | list | source | health_metrics_and_measurements | candidate |
| `respiratory-rate-sleep-summary` | list | source | health_metrics_and_measurements | candidate |
| `run-vo2-max` | list | source | activity_and_fitness | candidate |
| `sedentary-period` | list | source | activity_and_fitness | candidate |
| `sleep` | list | source | sleep | candidate |
| `steps` | list | source | activity_and_fitness | candidate |
| `swim-lengths-data` | list | source | activity_and_fitness | candidate |
| `symptoms` | なし | source | なし | unsupported |
| `time-in-heart-rate-zone` | list | source | activity_and_fitness | candidate |
| `total-calories` | dailyRollUp | aggregate | activity_and_fitness | candidate |
| `vo2-max` | list | source | activity_and_fitness | candidate |
| `weight` | list | source | health_metrics_and_measurements | candidate |
| `basal-energy-burned` | なし | source | activity_and_fitness | unverified |

`basal-energy-burned` は旧一覧に存在し、現行型一覧にはない。reconcile の union に名前が残るため、廃止とも list 対応とも断定しない。write-only 型を消さず、読み取り permission を捏造しない。

## Tasks 1 / 4 の検証記録

以下は `/home/kazumasa/projects/.claude/worktrees/health-full-archive-nextjs` を cwd として実行。
fixture/fake HTTP と一時 directory のみを使用した。

```bash
# 198 passed
PYTHONPATH=/home/kazumasa/projects/.claude/worktrees/health-full-archive-nextjs/health/src /home/kazumasa/projects/.venv/bin/python -m pytest health/tests/test_source_catalog.py health/tests/test_client.py health/tests/test_source_probe.py health/tests/test_probe_datatypes.py health/tests/test_auth.py health/tests/test_endpoints.py health/tests/test_inventory.py -q

# 64 passed: 既存同期・保存および担当者間の projection 互換性
PYTHONPATH=/home/kazumasa/projects/.claude/worktrees/health-full-archive-nextjs/health/src /home/kazumasa/projects/.venv/bin/python -m pytest health/tests/test_sync.py health/tests/test_store.py health/tests/test_projection_history.py -q

# All checks passed / 9 files already formatted
/home/kazumasa/projects/.venv/bin/ruff check health/src/health/source_catalog.py health/src/health/client.py health/src/health/probe.py health/scripts/probe_datatypes.py health/tests/fakes.py health/tests/test_source_catalog.py health/tests/test_client.py health/tests/test_source_probe.py health/tests/test_probe_datatypes.py
/home/kazumasa/projects/.venv/bin/ruff format --check health/src/health/source_catalog.py health/src/health/client.py health/src/health/probe.py health/scripts/probe_datatypes.py health/tests/fakes.py health/tests/test_source_catalog.py health/tests/test_client.py health/tests/test_source_probe.py health/tests/test_probe_datatypes.py

# 認可をロードしない CLI help の確認
PYTHONPATH=/home/kazumasa/projects/.claude/worktrees/health-full-archive-nextjs/health/src /home/kazumasa/projects/.venv/bin/python health/scripts/probe_datatypes.py --help

git diff --check
```

TDD の未実装 import、未実装 helper 引数、CLI 引数、失敗要約・page request 識別の failing test を確認してから対応実装を追加した。
実アカウントの取得確認、TCX 専用 transport、全履歴の到達保証、ArchiveEngine 本体はこの担当の完了判定に含めない。
