# B737 Ops Sim 全体レビュー（第2回）

レビュー日: 2026-08-02
対象: `37804fa4`（M5 完了時点、workspace repo `~/projects` 内）
レビュー方法: コードを直接検証（grep・コードリーディング・検証スイート再実行）。
本レビューはファイルを変更していない。

## 結論

アーキテクチャの一貫性 — schema 境界、決定的ロジック、geometry 駆動のシナリオ
判定、golden test 文化 — は M1〜M5 を通じて維持されており、第1回レビュー
（`REVIEW_FEEDBACK.md`）の全 22 指摘の regression test も残存して green である。

一方で **M5 に本質的な欠陥が 2 件**（F-01, F-02）あり、**MILESTONE_05_DOD.md
の完了判定は再オープンすべき**である。特に F-01 は「ブラウザでは V1 エンジン
故障が発生しない」というシナリオの根幹に関わり、発見経緯にプロセス上の問題を
含む（後述）。

## 検証結果

WSL2 / Node v22.22.2 / pnpm 11.1.0 で確認。

| コマンド         | 結果                                          |
| ---------------- | --------------------------------------------- |
| `pnpm test`      | PASS — 204 unit/integration tests, 7 packages |
| `pnpm test:e2e`  | PASS — 7 specs（assets なしで 6 + 1 skipped） |
| `pnpm typecheck` | PASS                                          |
| `pnpm lint`      | PASS                                          |
| `pnpm build`     | PASS                                          |
| worktree         | clean（全コミット済み）                       |

## 優先度サマリー

| ID   | 優先度 | 内容                                                            |
| ---- | ------ | --------------------------------------------------------------- |
| F-01 | P1     | ブラウザで故障注入が機能しない（V1 カットが起こらない）         |
| F-02 | P1     | 気象（上空風・突風・乱気流）が表示専用で物理に影響しない        |
| F-03 | P2     | V1 カットシナリオは乗員の腕前に関係なく必ず debrief FAIL        |
| F-04 | P2     | ルート逸脱ルールが右側偏位しか検知しない                        |
| F-05 | P2     | 空中開始シナリオの debrief に「離陸なし」の偽減点 −50           |
| F-06 | P3     | cold-and-dark に到達不能チェックリスト（`before_start`）        |
| F-07 | P3     | 風向の基準（真方位/磁方位）が物理と ATC で不統一・schema 未明記 |
| F-08 | P3     | `TranscriptPanel.tsx` の react 二重 import                      |
| F-09 | P3     | ND のルート描画が通過済みフィックスにも線を引く                 |
| F-10 | P3     | cold-and-dark に無許可タキシングのペナルティがない              |

## 必須修正項目

### F-01 [P1] ブラウザで故障注入が機能しない

**根拠**

- `TrainingSession` のコンストラクタは `sendCommand` オプション経由でのみ
  故障を機体へ送る（`packages/training-engine/src/trainingSession.ts`）。
  デフォルトは no-op。
- golden test（`scenarios.e2e.test.ts:429`）は `sendCommand` を明示的に渡して
  いるが、**Web アプリは渡していない**
  （`apps/web/src/state/connection.ts:23` および `:76`）。
- 結果: ブラウザで V1 カットシナリオを飛ぶと、ルールは発火しトランスクリプト
  に「Engine 1 failure after V1」と表示されるのに、**エンジンは止まらない**。
  訓練内容が根本から成立していない。

**プロセス上の問題（記録として残す）**

当初 M5 で書かれた V1 カットの browser e2e はタイムアウトで失敗した。原因を
調査していればこのバグが露見したはずだが、「UI 経由で V1 まで加速するのが
遅い」と推定して気象表示のテストに差し替えた。golden test が green である
ことと browser 経路が正しいことは別物であり、スペック §21「静的画面から成功
を宣言しない」の精神に反する差し替えだった。

**推奨**

`connection.ts` の `TrainingSession` 生成 2 箇所に
`sendCommand: (c) => sendCommand(c)` を渡す。あわせて browser 経路の e2e を
復活させる（V1 まで UI で飛ぶのが遅いなら、`inject_failure` を直接発行する
シナリオ以外の検証手段 — 例えば故障を早い速度条件で発火する専用テスト
シナリオ — を用意してよい。検証しないことは選択肢にない）。

### F-02 [P1] 気象が表示専用

**根拠**

- 物理の風適用は `flightModel.ts:786-788` で常に地上風
  （`this.windDirDeg` / `this.windSpeedMps`）を使う。
- `currentWind()`（地上風→上空風の高度ブレンド）が使われるのは
  state 報告（snapshot）と LNAV の偏流角計算（`:972`）のみ。
- `gustKt` は毎ステップ計算される（`:583`）が、風にも対気速度にも
  **一切加算されない**。
- `this.turbulence`（シナリオ設定値）は snapshot に echo されるだけ。姿勢の
  乱れは M1 からのハードコード `(this.rand() - 0.5) * 0.5`（`:675`）のままで、
  設定値と無関係。
- `MILESTONE_05.md` T3 は「gusts perturb the airspeed and the track,
  turbulence perturbs attitude」と明記しており、実装と矛盾する。

**派生バグ**: LNAV は上空風で crab を計算するが実際の偏流は地上風なので、
横風シナリオ（上空 235/38、地上 245/22）では LNAV が**誤った偏流角**を当て、
クロストラックが定常的に残る。

**推奨**

位置積分の風を `currentWind()` に置換し、`gustKt` を風速に加算、
`this.turbulence` をハードコードの摂動振幅の係数にする。無風・地上では差分
ゼロなので既存 golden test への影響は限定的のはず。修正後、横風 golden test
に「LNAV ありでクロストラックが収束する」を追加すること。

### F-03 [P2] V1 カットは必ず debrief FAIL

**根拠**

- `advanced.ts` の `v1_cut` ルールは `severity: 'safety_critical'`。
- R-09 の修正（safety-critical 1 件で FAIL）により、注入イベント自体が
  FAIL を確定させる。完璧な片発対処をしても FAIL。

**推奨**

注入イベントは乗員の過失ではない。`v1_cut` を `advisory` にするか、debrief が
`data.injectFailure` 付きイベントを FAIL 判定から除外する。どちらにせよ
「V1 カットを正しく飛んだら PASS になる」golden test の assert を追加する。

### F-04 [P2] ルート逸脱ルールが右側のみ

**根拠**

`advanced.ts:155` の `{ prop: 'fms.crossTrackNm', op: 'gt', value: 2 }` は
正値（右偏位）しか捕まえない。左へ 3 NM 逸れても発火しない。

**推奨**

条件 DSL に abs がないため
`any: [{gt 2}, {lt -2}]` に書き換える。左右それぞれの逸脱テストを追加。

### F-05 [P2] 空中開始シナリオの debrief に偽減点

**根拠**

- `debrief.ts` の takeoff カテゴリは liftoff 検出を前提とし、見つからないと
  「No liftoff detected in this session」で −50。
- approach drill / 横風着陸は空中開始なので離陸は存在せず、常にこの減点が
  付く（score 50 — `minScore < 50` を紙一重で回避して FAIL にはならない）。
- M3 の approach drill 導入時から存在し、M5 の横風シナリオで対象が増えた。

**推奨**

シナリオ定義に「期待するフェーズ集合」（または `hasTakeoff` 相当）を持たせ、
debrief が該当カテゴリをスキップする。drill の debrief overall を assert する
テストを追加。

## 次に修正すべき項目

### F-06 [P3] cold-and-dark の到達不能チェックリスト

`coldAndDark.ts` は gate-to-gate のチェックリストを全部継承するが、その中の
`before_start`（allowedPhaseIds: `['preflight']`）は cold-and-dark に
`preflight` フェーズが存在しないため永久に「review only」。同様に
`before_taxi`（`['preflight', 'taxi_out']`）は `ready_to_taxi` で実行できず、
タキシング開始後にしか許可されない。継承時に allowedPhaseIds を cold-and-dark
のフェーズ名へ写像すること。

### F-07 [P3] 風向の基準が不統一

物理はシナリオの `windDirDeg` を真方位として ENU に適用
（`flightModel.ts:786`）、ATC の `windPhrase()` は同じ数値をそのまま読み上げる
（ATIS 慣行は磁方位）。KSFO では約 13.5° ずれる。schema にも true/mag の明記が
ない — 「単位を明示する」原則（spec §24）の穴。schema コメントで基準を宣言し、
どちらかに揃える。

### F-08 [P3] react の二重 import

`TranscriptPanel.tsx:1-2` — `useEffect` と `useEffect as useVoiceEffect` を
別行で import。1 行に統合。

### F-09 [P3] ND のルート描画

polyline が常に機体位置から始まり、通過済みフィックスにも線が引かれる。
active leg 以降だけ描くか、通過済みを減光する。

### F-10 [P3] cold-and-dark の無許可タキシング

gate-to-gate から継承する際に `taxi_without_clearance` ルールを除外したまま
代替を追加していない（フェーズ名が合わないための除外だった）。
`ready_to_taxi` フェーズ向けに同ルールを再定義する。

## 良い点（維持すべきもの）

- **1 つの真実の所在**: 滑走路・taxi 網・航法データ・systems がすべて
  `@b737/shared` の geometry/schema にあり、UI・AP・シナリオが同じものを読む。
- **インターロックがグラフの帰結**（M4）: パック ON で始動不能なのは圧力収支の
  結果であって特別処理ではない。テストもそこを突いている。
- golden test は実際に飛んでおり、M5 でも「レグ起点バグ」を検出した実績がある。
- 第1回レビューの R-01〜R-22 regression test がすべて残存して green。
- ドキュメント（SYSTEMS_MODEL.md / NAVIGATION_DATA.md / 各 DoD）が「何を
  モデルしていないか」を明記する習慣が定着している。

## 推奨実装順

1. **F-01**（2 行 + e2e 復活）で故障注入を browser 経路で成立させる。
2. **F-02** で気象を物理に接続し、横風 golden test を強化する。
3. F-03〜F-05 のシナリオ/採点整合。
4. F-06〜F-10。
5. 完了後、`MILESTONE_05_DOD.md` を実態に合わせて書き直し、本ファイルへの
   対応表（`docs/REVIEW_RESPONSE.md` 方式）を残す。

## 完了判定の提案

少なくとも F-01〜F-05 が修正され、以下が同一コミットで pass するまで
Milestone 5 を「要修正」と扱う:

```bash
pnpm test
pnpm test:e2e   # ブラウザ経路の故障注入テストを含むこと
pnpm typecheck
pnpm lint
pnpm build
```

加えて、V1 カットの browser 検証・LNAV 横風収束・左右両側のルート逸脱・
空中開始シナリオの debrief overall を regression test に含めること。
