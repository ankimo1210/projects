# B737 Ops Sim 修正確認レビュー（第3回）

レビュー日: 2026-08-02

対象: `26990559`（`fix(b737-ops-sim): second-review remediation — F-01..F-10`）

目的: `docs/REVIEW_RESPONSE.md` / `docs/REVIEW_RESPONSE_2.md` の「修正済み」を、コード・回帰テスト・追加 probe で再検証する。

## 結論

前回までの修正は広く反映され、公式の unit/integration・Playwright・typecheck・lint・build はすべて green になった。特に repository 統合、WebSocket 防御、reconnect owner の一本化、runway geometry、checklist phase gate、3D assembly rotation、入力 target、V1 failure の browser wiring は改善を確認した。

ただし、**「全 finding 修正済み」および Milestone 5 完了をそのまま承認することはできない**。FlightGear adapter は不正値を正常 state として配信し、無効 frame だけで stale 判定を回避できる。asset pipeline も空の manifest を「verified」として skip でき、不完全な生成物を成功扱いできる。さらに Go-around、failure lifecycle、ATC 訂正、RTO override など訓練フロー上の不具合が残る。

少なくとも V-01〜V-09 を修正し、対応する regression test を追加するまで、M5 と第1・第2回レビューの完了判定は再オープンすることを推奨する。

## 検証結果

WSL2 / Node v22.22.2 / pnpm 11.1.0、built assets ありで確認した。

| コマンド                | 結果                               |
| ----------------------- | ---------------------------------- |
| `pnpm test`             | PASS — 213 unit/integration tests  |
| `pnpm test:e2e`         | PASS — 8/8 Playwright specs        |
| `pnpm typecheck`        | PASS                               |
| `pnpm lint`             | PASS                               |
| `pnpm build`            | PASS（5.7 MB bundle warning のみ） |
| project-scoped worktree | レビュー開始時 clean               |

追加 probe では FlightGear fake server、MockFlightModel、TrainingSession、asset fetch の隔離コピーを使用した。実 FlightGear は未導入のため、実機接続は今回も未検証である。

## 優先度サマリー

| ID   | 優先度 | 内容                                                                                 |
| ---- | ------ | ------------------------------------------------------------------------------------ |
| V-01 | P1     | FlightGear の不正値・無効 frame を正常かつ fresh な state として配信する             |
| V-02 | P1     | asset pipeline が空・不完全 manifest / output を verified build として成功扱いできる |
| V-03 | P2     | 正常な Go-around 完了でも debrief が必ず `FAIL` になる                               |
| V-04 | P2     | Go-around 後の2回目の進入で FO の安全 callout が再作動しない                         |
| V-05 | P2     | failure injection の ack・永続性・clear semantics が一致していない                   |
| V-06 | P2     | V1 engine failure が左右非対称運動を全く生まず、rudder も空中で効かない              |
| V-07 | P2     | 誤った ATC readback を1回で訂正できず、UI / voice が pending のまま残る              |
| V-08 | P2     | RTO の manual brake override が次の physics step で取り消される                      |
| V-09 | P2     | FlightGear sim time fallback と diagnostic write/restore が信頼できない              |
| V-10 | P2     | F-02 は一部のみ修正され、gust→IAS と visibility の効果が未実装                       |
| V-11 | P2     | `once: false` rule が条件成立中、state tick ごとにイベントを生成する                 |
| V-12 | P2     | asset swap は実際には atomic ではない                                                |
| V-13 | P3     | 3D drag の cancel・continuous command の送信責任・E2E isolation が未完               |
| V-14 | P3     | cold-and-dark が DC power off なのに beacon on で始まる                              |
| V-15 | P3     | README / M5 docs / review response が現在の実装・テストと矛盾する                    |

## 必須修正項目

### V-01 [P1] FlightGear ingress validation と freshness が未完成

**根拠**

- `packages/flightgear-adapter/src/flightgear/flightgearBackend.ts:149-159` は `value !== undefined` なら cache に保存し、JSON parse・known path・type 検証前に `lastMessageAtMs` を更新する。
- `missingRequired()` (`:188-193`) は `cache.has()` だけを見る。property map の `type` は受信検証に使われない。
- `num()` / `bool()` が invalid / null を 0 / false に変えた後で `AircraftStateSchema` を通すため、最終 schema validation では異常を検出できない。

fake FG で次を再現した。

1. 全 required path に `null` を返すと `connected: true` / `streaming` になり、lat / altitude / IAS / N1 = 0、WOW = true の state を配信した。
2. required cache を一度埋め、`staleAfterMs=100` で `not-json` を30 msごとに送ると、400 msの間に state が1件から21件へ増え、古い値に新 timestamp を付け続けた。

**推奨**

FG path から map entry への reverse index を作り、known path・expected type・finite number・nullability を受信境界で検証する。invalid required value は missing / invalid として扱う。freshness は「検証済み mapped value」を受理した時だけ更新し、可能なら required property ごとの最終 valid 時刻を管理する。null、wrong type、NaN / Infinity、unknown path、malformed JSON が streaming を維持しない integration tests を追加する。

### V-02 [P1] asset pipeline が false-green になる

**根拠**

- `scripts/fetch-cockpit-assets.mjs:84-104` の `manifestIntact()` は pinned SHA と manifest に記録された項目だけを検査し、必須 path 集合、重複、sha256 の存在・形式を検査しない。
- 隔離コピーで `files: []` と正しい pinned SHA だけを持つ manifest を置くと、`up to date and verified ... skipping` で終了した。
- `packages/asset-pipeline/src/convert.ts:65-69` は必須 model 欠落を `meshes: 0` として継続し、`:135-147` と `src/cli.ts:25-29` は sound 欠落を warning のみで exit 0 にする。
- assets 不在時の3D E2Eは skip されるため、不完全 build と test suite の両方が green になり得る。

**推奨**

manifest schema、必須 file allowlist、path 一意性、64桁 sha256、size を検証する。converter は必須 model、assembly bindings、runtime が利用する必須 sound の欠落で非0終了する。assets あり CI job では3D specの skipを失敗扱いにする。空 manifest、sha欠落、重複 path、必須 model / sound 欠落のnegative testsを追加する。

### V-03 [P2] 正常な Go-around が debrief `FAIL`

`APPROACH_DRILL_SCENARIO` は `go_around` から RA > 1,500 ft で `debrief` へ進む正規完了経路を持つ（`packages/scenario-engine/src/scenarios/approachDrill.ts:18-35`）。しかし `packages/training-engine/src/debrief.ts:415-420` は touchdown がなければ常に Landing −60 とし、overall の `minScore < 50` で `FAIL` にする。Landing / After Landing checklist も未完として減点される。

既存 golden test (`scenarios.e2e.test.ts:278-315`) は phase と event だけを確認し、debrief を assert しない。

Go-around が完了経路である scenario では landing category と着陸後 checklist を `not applicable` にするなど、scenario ごとの expected phase / category profile を導入する。正常 Go-around が `PASS` または意図した評価になる end-to-end assertion を追加する。

### V-04 [P2] 2回目の approach で FO が無言になる

MVP は Go-around 後に `approach_setup` へ戻り、Landing checklist を再armする（`mvpCircuit.ts:131-148`）。一方 `FirstOfficer` の `saidApproachAlt`、`saidGate`、`saidMinimums`、`saidGoAround`、`saidGearGreen` などは session 中に一度も reset されない（`packages/training-engine/src/firstOfficer.ts:42-55,147-228`）。そのため2回目の進入では高度 callout、1000 / 500 ft gate、minimums、再度の unstable advisory が出ない。

approach cycle の開始を明示し、Go-around 後に approach 用 latch と trend state を再armする。1回目 approach → Go-around → rejoin → 2回目 approach の test で安全 callout を両方の進入に要求する。

### V-05 [P2] failure lifecycle の契約が不整合

問題は3層にまたがる。

1. `TrainingSession` は failure event を確定してから戻り値なし callback を呼び、Web も fire-and-forget の `sendCommand()` を渡す。rate-limit / reject 時でも event は一度だけ成立し、debrief は「注入された課題」として auto-FAIL から除外するが、機体には故障が入らない。
2. `applyFailure()` は engine / generator / pump の状態を一度変更するだけで、`failures` Set は挙動を拘束しない。通常 switch / start command で復旧しても `activeFailures` は残り得る。
3. `clear_failures` (`flightModel.ts:523-525`) は Set だけを消し、実際の engine / generator / pump 状態を復元しない。probe では `activeFailures=[]` になっても left engine は stopped のままだった。

故障を latched fault とするのか一時的な command とするのかを schema / docs で定義する。scenario injection は ack 成功後に成立させるか、retry / `failure_injection_failed` event を持たせる。clear は定義済み recovery transition を実行するか、曖昧なら command 自体を削除する。各 failure kind の persistence / clear test と reject-path browser test が必要である。

### V-06 [P2] engine-out training が左右非対称をモデル化しない

`flightModel.ts:604-610` は左右 engine thrust を1本の scalar に平均する。airborne branch (`:676-689`) は rudder input を使用せず、rudder は ground steering (`:659-675`) にしか効かない。

同じ seed / command sequence で engine 1 と engine 2 をそれぞれ flameout させた120秒 probe は、heading、track、roll、lat/lon、IAS、RA が bit-for-bit 同一だった。`advanced.ts` の `asymmetric_heading` rule は操舵なしでも「Runway track maintained on one engine」を発火できる。

M5 の engine-failure training として扱うなら asymmetric yaw moment と airborne rudder authority を最低限モデル化し、neutral rudder では heading deviation、適切な rudder では track 維持となる test を追加する。2.5-DOF の範囲外とするなら、scenario 名・説明・callout を「片発推力低下 drill」に下げ、既知制約として明記する。

### V-07 [P2] ATC 訂正 readback が pending のまま残る

訂正 follow-up は新しい transcript entry だが (`packages/training-engine/src/atc.ts:425-435`)、再回答時は元 instruction の entry の `responseResult` だけが更新される。`TrainingSession` は follow-up id を元 instruction に map している (`trainingSession.ts:208-218`)。

wrong → correction の probe 結果:

- 元 entry: `incorrect` から `correct` に書き換わる
- 訂正 entry: `responseResult` が未設定のまま
- UI 上の未回答 entry: 訂正 entry が1件残る

同じ訂正をもう一度押さないと UI が消えず、`awaitingReadback` と voice input を塞ぐ。Controller 単体ではなく、現在回答している transcript entry に結果を記録する。TrainingSession + UI integration test で「誤答 → 訂正を1回 → pending 0」を要求する。

### V-08 [P2] RTO manual override が再作動する

`set_brakes` (`flightModel.ts:394-397`) は `autobrakeActive=false` にするが `rtoArmed` を残す。RTO 作動中に brake 0.7 を入力した probe は、`brakeNorm` が 0.9 → 0.7 → 1/60秒後 0.9 となった。

manual takeover 時には RTO arming latch も解除し、RTO を再選択するまで再作動させない。`docs/REVIEW_RESPONSE.md` は「brake command during abort」の regression test があると記すが、現行 RTO tests には存在しないため追加する。

### V-09 [P2] FlightGear time と diagnostic write test が未完

**Simulation time**

`config/flightgear/737-800-property-map.json:6-10` は `/sim/time/elapsed-sec` を optional とし、欠落時は `flightgearBackend.ts:382-387` で wall clock に fallback する。diagnostic も optional property を検査しない。pause / freeze 中も別 mapped frame が到着すると `simTimeSec` が進むため、「FlightGear clock を使う」という response は条件付きでしか正しくない。

**Diagnostic**

`apps/bridge/scripts/fg-diagnostic.ts` は taxi-light 初期値の応答を待たず、常に `true` を書き、default `false` へ restore する。初期 taxi light=true の fake FG で `ALL CHECKS PASSED` と表示しながら set sequence `[true, false]`、終了後 false を再現した。書込み値の read-back もなく、write test になっていない。

FG sim time を required にするか pause-aware fallback を定義する。diagnostic は元値を受信してから反対値を書き、read-back、元の型付き値へ restore、restore の read-back まで確認する。fake FG で true / false 両方の初期値と write rejection を検査する。

## 次に修正すべき項目

### V-10 [P2] F-02 weather fix は plan を満たし切っていない

`MILESTONE_05.md:55-60` は「gusts perturb the airspeed and track」と明記する。現実装で `gustKt` が使われるのは position / ground-track 計算 (`flightModel.ts:790-812`) と state 表示だけで、IAS dynamics (`:692-743`) には入らない。また `visibilityM` の利用箇所は state と `FmsPanel` readout だけで、3D scene の fog / range に影響しない。

gust response を IAS に接続し、visibility を scene に反映するか、plan / schema comment / DoD を実装済み範囲へ明示的に下げる。`docs/REVIEW_RESPONSE_2.md:38-40` は airspeed を約束として引用しながら、修正説明では track / attitude のみを挙げて「as the plan said」としており、現状を正確に表していない。

### V-11 [P2] `once: false` が event flood を起こす

`ScenarioRuntime.update()` (`scenarioRuntime.ts:81-95`) は `once:false` rule の条件が true の間、毎 state update で event を emit する。30 Hz では `taxi_overspeed` と `master_warning_active` が1秒30件ずつ timeline を膨らませる。

`once:false` を false→true edge で再armするか、cooldown / occurrence key を定義する。持続条件が続く間は1件、解消後に再発したらもう1件となる test を追加する。

### V-12 [P2] asset swap は atomic ではない

`fetch-cockpit-assets.mjs:235-238` は既存 `DEST` を削除してから `STAGE` を rename する。rename failure、process kill、同時実行で既存資産を失う。`ASSET_PIPELINE.md:29-30` と M2 DoD の atomic claim は過大である。

`DEST → backup`、`STAGE → DEST`、成功後 backup 削除、失敗時 rollback の同一 filesystem rename sequence と、PID別 staging / lock を使う。

## 軽微な所見

### V-13 [P3] Web interaction の edge case

- `scene.ts:279-321` は `pointerup` だけで drag を終了し、`pointercancel` / window blur を処理しない。cancel 時は final flush されず `dragSession` が残り得る。
- 3D / DOM throttle は直接 command を送りつつ shared target を更新し、`InputManager` も50 ms周期で同じ target を送るため、最大約40 Hzの二重送信になる。continuous command の送信責任を1箇所に集約する。
- Playwright は `reuseExistingServer = !CI` かつ各 test の backend reset がなく、local の既存 server・test order に依存し得る。

### V-14 [P3] cold-and-dark で beacon が点灯済み

`MockFlightModel.reset()` は start mode に関係なく `lights.beacon=true` にする。probe では DC / AC bus が off なのに `lights.beacon=true` で、inherited Before Start checklist の beacon item も最初から満たされる。「everything off」の説明と矛盾する。

### V-15 [P3] 文書と証跡が stale / contradictory

- `README.md:210` は 136 unit/integration + 3 Playwright のまま。実測は 213 + 8。
- `MILESTONE_05.md:9-12` と `MILESTONE_05_DOD.md:57-63` は V1 browser test を weather test に置換したと記すが、現在は `smoke.spec.ts:295-325` に復活し、8/8で pass する。
- `docs/REVIEW_RESPONSE.md` の R-05 は sim time が FG clock 由来と断定し、R-07 は manual brake test あり、R-21 は atomic staging / missing required failure と記すが、それぞれ V-01 / V-08 / V-02・V-12 と一致しない。
- `THIRD_PARTY_ASSETS.md` の CFM loop 数と converter allowlist も一致しない。

## 修正確認済み

以下はコード・test・必要な probe で改善を確認した。

- workspace repository への統合と nested Git の解消
- `pnpm test` の Vitest / Playwright 分離
- WebSocket Origin allowlist、pre-hello command refusal、version mismatch close、pause/reset rate limit
- FlightGear reconnect owner 一本化、idempotent connect、generation guard、close 時 cache clear
- Mock physics time accumulator（25 / 30 / 40 / 50 / 60 Hz）
- runway entry / exit geometry、single safety-critical FAIL、checklist phase gate
- cockpit assembly rotation、StrictMode listener cleanup、shared control target、drag release flush
- positive-rate callout、actual flap / gear state、signed V/S、FO ILS-null stability
- F-01 browser success path、左右 route deviation、airborne-start takeoff deduction、wind true/magnetic 基準、ND active route

## 推奨実装順

1. V-01 で FlightGear state boundary を安全にし、V-02 で asset build の false-green を止める。
2. V-03・V-04 で Go-around の完了評価と再進入監視を成立させる。
3. V-05・V-06 で failure exercise の contract / fidelity を決める。
4. V-07〜V-09 で ATC、RTO、FG diagnostic の状態遷移を修正する。
5. V-10〜V-15 と文書を実装に合わせる。

## 完了判定

既存の全コマンドが green であることに加え、最低限次を regression suite に含める。

- invalid / null / malformed / unmapped FG frames と required property freshness
- empty / incomplete asset manifest、missing required model / sound、assets-required E2E
- normal Go-around debrief と2回目 approach の FO callouts
- failure command reject、failure persistence、`clear_failures`
- engine 1 / engine 2 failure の非対称性、または明示した non-goal
- ATC wrong → correct を1回で完了
- RTO manual override
- FG diagnostic write / read-back / exact restore
- `once:false` の edge-triggered recurrence
