# B737 Ops Sim 現状レビュー・フィードバック

レビュー日: 2026-08-02  
対象: `87729c7` (`main`) および未追跡の `CHANGELOG.md`

## 結論

アーキテクチャの分離、単位を明示した schema、決定的な訓練ロジック、スクリプト化された 3D asset pipeline は良い基盤になっている。Mock 正常系は Playwright で操作でき、typecheck・lint・build も通る。

一方で、現状の **Milestone 1 / 2 「完了」判定は再オープンすべき**である。特に FlightGear 再接続、stale state、RTO autobrake、時間倍率、runway exit、safety-critical 採点、cockpit assembly には、完了条件と直接矛盾する再現済みの不具合がある。

## 検証結果

WSL2 / Node 22 / pnpm 11.1.0 で確認した。

| コマンド                | 結果          | 備考                                                                                                                       |
| ----------------------- | ------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `pnpm test`             | **FAIL**      | Vitest が Playwright 用 `apps/web/e2e/smoke.spec.ts` まで収集し、`Playwright Test did not expect test() to be called here` |
| unit / integration 本体 | 91 tests pass | 上記 E2E suite の誤収集を除く                                                                                              |
| `pnpm test:e2e`         | 3/3 pass      | generated assets あり。この環境では `TMPDIR=/tmp TEMP=/tmp TMP=/tmp` が必要だった                                          |
| `pnpm typecheck`        | pass          | 全 package                                                                                                                 |
| `pnpm lint`             | pass          | 全体                                                                                                                       |
| `pnpm build`            | pass          | web bundle 5.68 MB の warning あり。local-only なので現時点では blocker ではない                                           |

実 FlightGear と aircraft-dependent property map は README どおり未検証。以下の FlightGear 所見は fake server を使って再現した。

## 優先順位サマリー

| ID   | 優先度 | 内容                                                                             |
| ---- | ------ | -------------------------------------------------------------------------------- |
| R-01 | P0     | 親 workspace に統合されず、remote なしの nested Git repo になっている            |
| R-02 | P0     | 公式の `pnpm test` が red。DoD の all-green 証跡が現在の設定では再現しない       |
| R-03 | P0     | 任意 Origin から hello/version 合意なしで localhost の機体を操作できる           |
| R-04 | P1     | FlightGear 初回接続失敗後の reconnect が状態配信停止・socket 重複・leak を起こす |
| R-05 | P1     | FlightGear の stale / partial cache を新しい時刻の正常 state として配信する      |
| R-06 | P1     | 許可済み `STATE_RATE_HZ` によって Mock の時間倍率が変わる                        |
| R-07 | P1     | RTO autobrake が rejected takeoff で全く作動しない                               |
| R-08 | P1     | runway exit / runway incursion を位置で判定していない                            |
| R-09 | P1     | `safety_critical` 1 件でも `FAIL` にならない                                     |
| R-10 | P1     | 着陸前に Landing / After Landing checklist を完了できる                          |
| R-11 | P1     | 3D cockpit の assembly rotation を抽出しながら runtime で捨てている              |
| R-12 | P1     | Positive-rate callout が state stream rate 依存で欠落する                        |

## 必須修正項目

### R-01 [P0] nested Git repository を workspace の管理方針に合わせる

**根拠**

- 親 repo では `b737-ops-sim/` 全体が untracked。
- `b737-ops-sim/.git/` に独立 history があるが remote はない。
- 親 [`AGENTS.md`](../AGENTS.md) は「top-level projects は 1 つの Git repository で管理」としている。親 `README.md` の project index にも未登録。

**影響**

親 repo から通常の `git add b737-ops-sim` をすると、ソース一式ではなく embedded repository / gitlink として扱われる危険がある。remote と `.gitmodules` がないため、他環境で再構成できない。

**推奨**

親 repo に取り込むか、明示的な別 repo / submodule にするかを決める。現在の 10 commit を保存した上で移行し、親 index を更新する。**history 保存前に単純に `.git/` を削除しないこと。**

### R-02 [P0] `pnpm test` から Playwright suite を除外する

**根拠**

- [`package.json:15`](package.json) は `pnpm -r --no-bail test` を公式 test にする。
- [`apps/web/package.json:10`](apps/web/package.json) は `vitest run`。
- [`apps/web/vite.config.ts:5`](apps/web/vite.config.ts) に test include / exclude がない。
- Vitest が [`apps/web/e2e/smoke.spec.ts:9`](apps/web/e2e/smoke.spec.ts) を収集し、Playwright の `test()` 読み込みで suite が失敗する。
- [`docs/milestones/MILESTONE_01_DOD.md:3`](docs/milestones/MILESTONE_01_DOD.md) と [`MILESTONE_02_DOD.md:14`](docs/milestones/MILESTONE_02_DOD.md) の all-green 主張と矛盾。

**推奨**

Vitest を `test/**/*.test.ts` などに限定するか `e2e/**` を明示除外する。CI 相当で `pnpm test && pnpm test:e2e && pnpm typecheck && pnpm lint && pnpm build` を一度に確認し、DoD の test 数も実測値に合わせる。

### R-03 [P0] WebSocket の Origin と protocol handshake を強制する

**根拠**

- [`apps/bridge/src/server.ts:46`](apps/bridge/src/server.ts) は任意 Origin を許可。
- `saidHello` は同ファイル `:25,127` で設定するだけで、command 前に検査しない。version mismatch 後も接続が継続する。
- `Origin: https://evil.example` から hello なしで `set_light` を送る probe に `{ok:true}` が返った。
- `reset_scenario` / `set_paused` は rate limit 対象外。

**影響**

loopback bind でも、ブラウザが開いた悪意のある Web ページから localhost bridge へ WebSocket 接続され、Mock / FlightGear を操作される。

**推奨**

Vite の既知 Origin の allowlist、hello 完了前の command 拒否、version mismatch の close code `1002`、pause/reset の rate limit を追加する。foreign Origin、pre-hello command、version mismatch の bridge integration tests も追加する。

### R-04 [P1] FlightGear reconnect を単一の state machine にする

**根拠**

- [`flightgearBackend.ts:75-80`](packages/flightgear-adapter/src/flightgear/flightgearBackend.ts) だけが publish timer を開始する。
- internal reconnect (`:112-121`) は `openSocket()` だけを呼ぶため、初回失敗後に内部再接続が成功しても state が 0 件。
- [`apps/bridge/src/main.ts:40-55`](apps/bridge/src/main.ts) も別の retry loop を持ち、内部 reconnect と競合する。
- 再現で FG client が 2 本になり、`disconnect()` 後も 1 本残った。古い socket の close handler が新しい socket を無視して `this.ws = null` にする。

**推奨**

retry owner を backend または main の一方だけにする。`connect()` を idempotent にし、socket generation guard を付ける。初回失敗→server 起動、重複 `connect()`、古い socket の close、完全 disconnect を結合 test にする。

### R-05 [P1] stale / partial FlightGear state の配信を止める

**根拠**

- [`flightgearBackend.ts:284-358`](packages/flightgear-adapter/src/flightgear/flightgearBackend.ts) は `cache.size > 0` だけで state を構成。missing required property は 0 / default になり、property map の `optional` も使わない。
- `getStatus()` が stale と判定しても publish は継続。
- altitude を 1 度だけ送る probe で、`connected=false` 後も同じ altitude に新しい timestamp / 進む simTime を付けて配信した。`lastStateAgeMs` も新鮮に見える。
- `simTimeSec` は FG simulation time ではなく wall clock。

**推奨**

初回は全 required property が揃うまで publish せず、各 property の freshness を管理する。stale 時は publish を止め、reconnect 時に cache をクリアする。FG simulation-time property を map に追加し、構成した state を `AircraftStateSchema` で検証する。

### R-06 [P1] physics 60 Hz と state publish rate を分離する

**根拠**

[`mockBackend.ts:43-49`](packages/flightgear-adapter/src/mock/mockBackend.ts) が publish 周期を `step()` に渡し、[`flightModel.ts:325-329`](packages/flightgear-adapter/src/mock/flightModel.ts) が毎 tick で step 数を `round()` する。

| State rate | wall 1 s 相当後の simTime |
| ---------: | ------------------------: |
|      25 Hz |                0.833333 s |
|      30 Hz |                1.000000 s |
|      40 Hz |                1.333333 s |
|      50 Hz |                0.833333 s |
|      60 Hz |                1.000000 s |

**推奨**

fractional accumulator を持つか、physics の 60 Hz timer と publish timer を完全に分ける。許可範囲の 25 / 40 / 50 Hz も regression test に入れる。

### R-07 [P1] RTO autobrake の状態機械を実装する

**根拠**

- [`flightModel.ts:294-297`](packages/flightgear-adapter/src/mock/flightModel.ts) は selection 時に `autobrakeActive=false`。
- active にするのは touchdown の `:494-502` だけ。そこでは RTO も landing autobrake として有効化する。
- [`mvpCircuit.ts:262-268`](packages/scenario-engine/src/scenarios/mvpCircuit.ts) は「RTO で rejected takeoff を自動制動」と案内。
- probe で throttle idle 後の OFF / RTO は同一軌跡、`brakeNorm=0`。

**推奨**

RTO selection + takeoff thrust 到達で arm、地上・一定速度以上で thrust retard を検知して activate、liftoff で disarm する。touchdown activation から RTO を除く。OFF と RTO の停止距離差を test する。

### R-08 [P1] runway geometry で entry / exit / touchdown を判定する

**根拠**

- [`mvpCircuit.ts:129-155`](packages/scenario-engine/src/scenarios/mvpCircuit.ts) は `weightOnWheels && gsKt < 30` だけで `runway_exit`、checklist + `gsKt < 20` で debrief。
- golden test の [`fullCircuit.e2e.test.ts:185-196`](packages/training-engine/test/fullCircuit.e2e.test.ts) は着陸後に steering せず、センターライン上で After Landing checklist を実行して「exit」を pass する。
- `runway_incursion` (`mvpCircuit.ts:162-173`) も位置ではなく clearance なし + `gsKt > 15`。probe で runway 外の cross offset 76 m で発火した。逆に 15 kt 以下の entry は見逃す。
- Mock の touchdown も runway footprint に関係なく field elevation で発生する。
- [`MILESTONE_01_DOD.md:20`](docs/milestones/MILESTONE_01_DOD.md) の runway exit 検出済みと矛盾。

**推奨**

runway frame の `alongM` / `crossM` と footprint を derived state にする。`rollout_complete` と `runway_exited` を分け、滑走路境界の crossing を要求する。golden test も実際に steering して exit させる。そこまで実装しないなら DoD / README の表現を「rollout to taxi speed」に下げる。

### R-09 [P1] safety-critical 1 件で必ず FAIL にする

**根拠**

- [`debrief.ts:392-399`](packages/training-engine/src/debrief.ts) は `safetyCritical.length > 1` のみ強制 FAIL。
- runway incursion 1 件は takeoff score 60 で `PASS_WITH_DEVIATIONS`。landed-without-clearance も score 50 のため `< 50` を通過する。
- [`SCENARIO_AUTHORING.md:70-75`](SCENARIO_AUTHORING.md) は `safety_critical` が flight を fail させると明記。
- [`debrief.test.ts:160-174`](packages/training-engine/test/debrief.test.ts) の test 名は「fails」だが、実際の assertion は `FAIL` または `PASS_WITH_DEVIATIONS` の両方を許す。

**推奨**

`safetyCritical.length > 0` で FAIL にし、test を `toBe('FAIL')` にする。例外を認めるなら severity 名と authoring contract の方を変える。

### R-10 [P1] checklist に有効 phase を持たせる

**根拠**

- [`ScenarioRuntime.answerChecklistItem():149-185`](packages/scenario-engine/src/scenarioRuntime.ts) に phase gate がない。
- [`ChecklistPanel.tsx:23-35`](apps/web/src/panels/ChecklistPanel.tsx) は全 checklist tab を常に操作可能。
- probe で `before_takeoff` 中に Landing / After Landing を完了し、`afterLandingChecklistComplete=true` まで立った。

**推奨**

ChecklistDefinition に `allowedPhaseIds` を追加し、Runtime で拒否する。UI の非該当 tab も read-only にする。debrief は completion time が許可 phase 内からかも確認する。

### R-11 [P1] cockpit assembly の `rDeg` を runtime で適用する

**根拠**

- [`cockpitLoader.ts:135-149`](apps/web/src/sim3d/cockpitLoader.ts) は offset chain の非ゼロ rotation に warning を出して無視する。
- 生成済み bindings には flightdesk `-15°`、overhead `[90°, 90°, 0°]`、MCP には flightdesk から継承する `-15°` がある。
- [`ASSET_PIPELINE.md:60-69`](ASSET_PIPELINE.md) と [`MILESTONE_02_DOD.md:9-11`](docs/milestones/MILESTONE_02_DOD.md) の offset assembly / real cockpit 完了と矛盾。

**推奨**

FlightGear XML の Euler 順序・座標系を明示し、各 chain link に quaternion として適用する。flightdesk、overhead、MCP の world transform を pipeline/runtime 自動 test で固定する。目視 screenshot だけで完了にしない。

### R-12 [P1] Positive-rate callout を sample 差分から切り離す

**根拠**

[`firstOfficer.ts:72-79`](packages/training-engine/src/firstOfficer.ts) の `ra > lastRaFt + 1` は 1 sample で 1 ft より大きく上がることを必須にする。900 fpm 上昇を 30 Hz で入れると 0.5 ft/sample のため callout が一度も出ず、5 Hz では出た。

**推奨**

ScenarioRuntime の `positive_rate` event を callout の source にするか、経過時間で正規化した trend / vertical speed を使う。default 30 Hz と 60 Hz を test する。

## 次に修正すべき項目

### R-13 [P2] 3D / keyboard / gamepad の input target を一元化する

[`controlActions.ts:19-64`](apps/web/src/cockpit/controlActions.ts) は backend state を起点に 3D drag command を直接送信する一方、[`inputManager.ts:61-64`](apps/web/src/input/inputManager.ts) は独立の throttle / reverser target を初期値 0 で持つ。実ブラウザで 3D throttle を 50% にした後 `=` を短く押すと 4% に急落した。reverse も同じ構造。共通 input target を持つか、キー増減を latest backend state 起点にする。reset / reconnect でも同期する。

### R-14 [P2] 3D drag を 20 Hz に coalesce し、最終値を保証する

[`scene.ts:269-272`](apps/web/src/sim3d/scene.ts) から pointermove ごとに送信する。reverse / speedbrake は [`rateLimiter.ts:27-28`](apps/bridge/src/rateLimiter.ts) の continuous bucket にも入っていない。100-step speedbrake drag で最終 97% + `rate limited` を再現。60 Hz x 2 s では 120 command 中 81 件が reject された。requestAnimationFrame または 20 Hz に coalesce、pointerup で最終値を必ず送り、continuous control を適切な bucket に入れる。成功 ack で一過性 rejection 表示も clear する。

### R-15 [P2] StrictMode で残る pointer listener を dispose する

[`main.tsx:11-14`](apps/web/src/main.tsx) は React StrictMode。[`scene.ts:249,265,269,299`](apps/web/src/sim3d/scene.ts) の匿名 listener を `dispose():353-358` で外していない。初回 mount 後の実測で `dblclick adds=2 / removes=0`、pointer listener にも破棄 mount 分が残った。handler を名前付きにし、canvas / window の両方から cleanup する。

### R-16 [P2] pause / reset は backend ack 後に UI / session へ反映する

[`StatusBar.tsx:65-76`](apps/web/src/panels/StatusBar.tsx) は pause command の ack 前に local `paused` を反転する。[`connection.ts:28-36`](apps/web/src/state/connection.ts) も backend reset 前に TrainingSession を破棄する。切断中は `BridgeClient.send()` が黙って捨てるため、UI / training と機体 state が分離する。pending state を持ち、ack success 時だけ commit、reject / timeout で rollback する。

### R-17 [P2] Mock MCP Vertical Speed で選択符号を尊重する

[`flightModel.ts:383-393`](packages/flightgear-adapter/src/mock/flightModel.ts) は selected VS に `Math.abs()` を使い、方向を altitude 差から決める。selected VS `-1000`、selected altitude を現在+3000 ft にすると実測 `+1187 fpm` で上昇した。FlightGear backend は符号をそのまま送るため backend contract も不一致。ALT capture まで signed VS を尊重し、正負両方を test する。

### R-18 [P2] checklist / FO / scoring は lever ではなく actual state を検査する

- Landing flaps は [`mvpCircuit.ts:326-345`](packages/scenario-engine/src/scenarios/mvpCircuit.ts) で handle だけを見る。handle 30、actual surface は flaps 5 相当のまま checklist 完了を再現。
- After Landing は handle UP 直後の transit 中でも完了できる。
- FO / debrief の gear 判定も lever だけで down-locked を要求しない。
- flight-control check (`trainingSession.ts:130-145`) は hint で rudder 左右を要求するのに yaw を記録せず、backend ack 前の raw input で flag を立てる。

flaps は actual norm、gear は `gearPositionNorm > 0.99`、speedbrake は spoiler actual も検査する。HistorySample に actual positions を保存する。flight-control check は yaw も要求し、少なくとも accepted command または actual surface state を使う。

### R-19 [P2] FO safety callout を構造化 event として debrief へ残す

[`firstOfficer.ts:127-153`](packages/training-engine/src/firstOfficer.ts) の speed / LOC / GS 起因の「Go around」は transcript にだけ残る。[`debrief.ts:41-49,293-299`](packages/training-engine/src/debrief.ts) は input で transcript を受け取るが使わず、Scenario rule の unstable 条件も speed / path を含まない。そのため FO が go-around を呼んでも stability 減点が残らない。FO safety event を runtime event にするか、debrief が `relatedEventId` を評価する。FO / scenario の stable criteria も共通化する。

また ILS approach 中に deviation が `null` でも [`firstOfficer.ts:132-135`](packages/training-engine/src/firstOfficer.ts) は stable とみなし、debrief も減点しない。`ilsTuned && loc !== null && gs !== null` を必要条件にする。

### R-20 [P2] ATC 誤読復唱後に訂正できるようにする

[`TrainingSession.respond():96-121`](packages/training-engine/src/trainingSession.ts) は誤答後に元 entry を `incorrect` にし、pending map から削除する。ATC は「negative — read back」と話すが follow-up に options がなく、再回答できない。さらに flags は誤答でも適用される。instruction を queue にし、訂正済みまたは timeout まで次を発行しない。誤答後は再回答可能 entry を出す。

Positive-rate prompt を未回答のままにすると `pending !== null` のため gear reminder が永久に抑止される (`firstOfficer.ts:96-115`)。保存済み `sinceSimTimeSec` を timeout / escalation に使う。

### R-21 [P2] asset pipeline の再現性と provenance を実際に検証する

- [`fetch-cockpit-assets.mjs:62-68`](scripts/fetch-cockpit-assets.mjs) は manifest の commit SHA だけで skip し、記録済み file hash を照合しない。
- `--force` でも destination を clean せず、optional failure の旧 file が残る。
- [`convert.ts:34-35,103-112`](packages/asset-pipeline/src/convert.ts) も output を clean せず、allowlist ではなくそこにある全 `.wav` をコピーする。
- current manifest は 96 records / 94 unique paths。fallback で解決済みのものも `missingOptional` に残る。

temp staging に allowlist だけを取得し、full hash を検証して atomic replace する。generated output も毎回 clean に作る。required engine samples の欠落は fail にする。

### R-22 [P2] FlightGear diagnostic を property map から導出する

[`apps/bridge/scripts/fg-diagnostic.ts:17-25,73-90`](apps/bridge/scripts/fg-diagnostic.ts) が raw property path を再ハードコードしている。これは [`propertyMap.ts:3-7`](packages/flightgear-adapter/src/flightgear/propertyMap.ts) の「map が single source of truth」に反する。診断は map の一部しか見ないため、`ALL CHECKS PASSED` でも実運用の state / command map が壊れている可能性がある。required state paths と harmless write probe を map から導出する。

## 軽微な所見 / 改善候補

- `COCKPIT_CONTROL_MAPPING.md` は declarative registry / no per-switch logic を謳うが、3D dispatch は [`controlActions.ts`](apps/web/src/cockpit/controlActions.ts) で再ハードコードされている。DOM / 3D / keyboard 共通 dispatcher を registry から作ると R-13 の再発も防げる。
- Evaluation mode でも [`ControlsPanel.tsx:178`](apps/web/src/cockpit/ControlsPanel.tsx) の light button だけ `showHints` を見ずに guided class が付く。
- control sound は backend ack 前に鳴るため、地上 gear-up など reject される操作でも音が出る。
- Checklist failure は event emit 直後に `retryActiveItem()` で active へ戻すため、UI の failed branch が実質表示されない。
- ATC はシナリオ風 290° / 6 kt に対し、takeoff / landing とも常に `wind calm` と発話する。
- FO が「Go around」を命じるが go-around phase / missed-approach flow はない。指示に従うとシナリオ完了経路から外れる。
- Phase 2 E2E は assets なしで主テストを skip し、assets ありでも gear 1 操作だけを検査する。CI で assets あり/なし matrix、6 controls、assembly transform、sample/fallback を検査する。CI では `reuseExistingServer` も無効化する。

## 推奨実装順

1. R-01 で repository の正規な保管先を確定し、R-02 で信頼できる green baseline を作る。
2. R-03〜R-05 の bridge / FlightGear connection contract を修正する。
3. R-06・R-07・R-12 の Mock timing / takeoff safety behavior を固める。
4. R-08〜R-10 の scenario / scoring contract を修正し、golden test を本当の runway exit まで飛ばす。
5. R-11・R-13〜R-15 の 3D assembly / interaction を修正する。
6. 残りの P2 を反映した後、assets あり/なしの両方で全 check を再実行し、DoD 文書を書き直す。

## 完了判定の提案

少なくとも R-01〜R-12 が修正され、下記が同一 commit で pass するまで Milestone 1 / 2 を「要修正」と扱う。

```bash
pnpm test
pnpm test:e2e
pnpm typecheck
pnpm lint
pnpm build
```

加えて、非 default state rate、RTO rejected takeoff、FG 初回失敗からの再接続、stale property stream、safety-critical 1 件、phase 外 checklist、実 runway exit、cockpit world transform、全 3D continuous controls を regression test に含める。
