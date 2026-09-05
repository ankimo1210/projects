# ORBIT LAB Library Comparison Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Site source edits belong to the owning agent; delegated work, if authorized, is read-only review/research.

**Goal:** 既存の3D比較から、分析・ワークフロー・動き・データ取得・地図を体験して評価できる比較ラボへ発展させる。

**Architecture:** 共通の格子データと選択状態に、用途ごとの描画・操作adapterを接続する。`/lab`内の実験を遅延読み込みし、同条件での比較と各ツールの特長を試す操作を提供する。演算はUIから独立させ、性能測定は1実装ずつ行う。

**Tech Stack:** 現行React 19 / TypeScript / Vinext / Vite / npm、Plotly / R3F / Babylon、段階的にZod / Zustand / ECharts / React Flow / Motion / TanStack Query / MapLibre。

**Spec:** [library-comparison-design.md](library-comparison-design.md)。起点 `0268295f`、提案日2026-09-05。この文書は実装承認済みという意味ではない。

## Global Constraints

- 作業範囲は `komorebi-3d/`。React 19 / TypeScript / Vinext / Vite / npmを継続する。
- 初版は模擬データとローカルCSV。CSVは1 MB・5,000点以下、完全格子、Tは年、K/FとIVは小数。
- 既存4ルートとCSVの互換性を維持する。Blender・Unrealの生成物を変更しない。
- 新規依存は使用する段階で導入する。計画作成ではインストール・アプリ変更・デプロイを行わない。
- 各実験は遅延読み込み。390px以下のナビゲーション、キーボード操作、reduced-motionに対応する。
- HTTPサンプルは同一originの固定ファイル。CSVやフローの内容を外部送信しない。
- 実測と推測を区別する。SwiftShaderの数値を実機GPUの性能として扱わない。

## ファイルの責任と実行順

以下のパスは `komorebi-3d/` からの相対パス。作成と記したファイルは新規の提案。
各段階で必要なpackageとlockfile変更をまとめ、型・lint・対象テストが通る単位でコミットする。
実行前にこの計画の承認と依存追加の範囲を確認する。既に承認された範囲は再確認しない。

| 段階 | 完成するもの | 主な新規ファイル | 依存 |
|---|---|---|---|
| 0 | 全画面から入れるラボ入口・開発と本番の検証基準 | `web/app/lab/page.tsx`, `web/components/lab/lab.tsx`, `registry.ts` | なし |
| 1 | 既存Viewerの互換性を持つ共通データ・状態 | `web/components/volatility/schema.ts`, `web/components/lab/store.ts`, `provider.tsx` | 0 |
| 2 | 3D＋2D＋ヒートマップ＋A/B差分 | `web/components/lab/charts/{data,svg,echarts,analysis-panel}.tsx`等 | 1 |
| 3 | フォームとノードの同等な計算フロー | `web/components/lab/workflow/{model,evaluate,editor,form}.ts(x)` | 1、2 |
| 4 | CSSとMotionの動きの比較 | `web/components/lab/motion/{panel,css-demo,motion-demo}.tsx` | 0 |
| 5 | fetchとQueryのデータ取得比較 | `web/components/lab/data/{load-snapshot,use-native,use-query,panel}.ts(x)` | 1 |
| 6 | 実測結果と用途別の比較表 | `web/components/lab/benchmark/{contract,runner,results}.ts(x)` | 2〜5 |
| 7 | SVGとMapLibreの地図実験 | `web/components/lab/geo/{data,svg-map,maplibre-map,panel}.ts(x)` | 0、6 |

`.tsx`はReact表示、`.ts`は純粋なデータ/状態処理。具体的なファイル一覧は各段階を優先する。
Providerは`/lab`の画面インスタンスに属する。既存`/volatility`は同じSurface表示を
自身のProviderで使い、別ページとの暗黙の状態引継ぎは行わない。

## 段階0: ラボ入口と再現可能な検証

**Modify:** `web/components/orbit/experience.tsx`, `web/app/globals.css`, `web/vite.config.ts`, `web/playwright.config.ts`, `web/tests/orbit.spec.ts`, `web/README.md`。
**Create:** `web/app/lab/page.tsx`, `web/components/lab/lab.tsx`, `web/components/lab/registry.ts`, `web/components/lab/styles.css`, `web/tests/lab-navigation.spec.ts`。

**Interfaces:** `ExperimentId = 'surface' | 'workflow' | 'motion' | 'data' | 'geo' | 'results'`。
`ExperimentDefinition = { id: ExperimentId; label: string; available: boolean }`。
`/lab?experiment=<id>`は存在しない/未完成idならSurfaceを表示する。

- [ ] 390pxでトップのCompare・Volatilityリンクへ到達できないことを再現し、メニュー経由のブラウザテストを先に追加する。

```ts
await page.setViewportSize({ width: 390, height: 844 });
await page.goto('/');
await page.getByRole('button', { name: 'メニューを開く' }).click();
await page.getByRole('link', { name: 'Volatility', exact: true }).click();
await expect(page).toHaveURL(/\/volatility$/);
```

- [ ] 現行のCollectionボタンを失わず、全ルートへ到達できるスマホメニューを作る。ラボのSurfaceには現行Viewerを表示する。

```tsx
// web/app/lab/page.tsx
import Lab from '@/components/lab/lab';
export default function Page() { return <Lab />; }
// registryは完成したidだけをナビゲーションへ渡す。
```

- [ ] 開発時の初回React Flow等の依存最適化は、本番の性能問題とは分ける。
  現在再現済みの`@babylonjs/core/Culling/ray`をViteの`optimizeDeps.include`へ指定し、
  新しいcacheで `/ → /compare → /volatility → 3つ比較` が途中reloadしないか確認する。
  blanketな全依存事前読込や開発用エラー表示の無効化は行わない。
- [ ] テストのURLをbaseURLから受け取る。既存mobileテスト内の3101固定も修正する。
  開発用は指定した3100の既存serverを使う別設定、本番用は現在のbuild＋3101を維持する。
- [ ] 正常系は両server、強制障害からの復帰は開発overlayを混ぜない本番版で検証する。
  1440px / 390px / 200%文字拡大でメニューと操作が使えることを確認する。
- [ ] 初期JS量の既存scriptでbaselineを保存し、READMEに計測条件を追記してコミットする。

**完了条件:** 既存機能が使え、スマホから比較・Viewer・Labへ移動できる。未完成タブは表示されない。

## 段階1: ZodとZustandによる共通データ・状態

**Create:** `web/components/volatility/schema.ts`, `web/components/lab/store.ts`, `web/components/lab/provider.tsx`, `web/tests/lab-store.test.ts`。
**Modify:** `web/components/volatility/model.ts`, `viewer.tsx`, `web/components/lab/lab.tsx`, `web/tests/volatility-model.test.ts`, `web/tests/volatility-state.spec.ts`, package/lockfile。

**Interfaces:** 既存`SurfaceGrid`、`Parameters`、`View`を再利用する。

```ts
type Selection = { moneyness: number; tenor: number };
type SourceKind = 'demo' | 'csv' | 'snapshot' | 'workflow';
type LabState = {
  grid: SurfaceGrid; referenceGrid: SurfaceGrid | null;
  selection: Selection; view: View; wireframe: boolean;
  sourceKind: SourceKind; intent: number;
  beginIntent(): number;
  acceptGrid(intent: number, grid: SurfaceGrid, source: SourceKind): boolean;
  setSelection(selection: Selection): void;
  setView(view: View): void;
  pinReference(): void;
};
// createLabStore(initial: SurfaceGrid): StoreApi<LabState>
// parseSnapshot(input: unknown): { id: string; revision: string; grid: SurfaceGrid }
// SnapshotのschemaVersionは1。gridはrowsから再構成して検証する。
```

- [ ] Zod / Zustandの互換性を確認して追加。CSVの現在の正例・負例を移行前後で照合する。
- [ ] storeの独立性と古い読込破棄を、Reactに依存しないテストで先に表現する。

```ts
const a = createLabStore(createDemoSurface(presets.equity.parameters));
const b = createLabStore(createDemoSurface(presets.equity.parameters));
const old = a.getState().beginIntent();
const current = a.getState().beginIntent();
const stress = createDemoSurface(presets.stress.parameters);
assert.equal(a.getState().acceptGrid(current, stress, 'demo'), true);
assert.equal(a.getState().acceptGrid(old, b.getState().grid, 'csv'), false);
assert.equal(a.getState().grid.iv[11][12], 0.32);
assert.equal(b.getState().grid.iv[11][12], 0.20);
```

- [ ] CSVの列・BOM・数値化処理は既存の契約を保つ。数値化した行の検証をschemaへ集約し、
  有限値・範囲・重複・欠損・サイズのチェックを削らない。JSONはZodの`safeParse`を入口にする。
  `SurfaceGrid.source.kind`の既存契約は維持する。固定HTTPサンプルは`demo`として模擬データと明示し、
  フロー出力は入力の出所を保持する。取得・加工経路は別の`sourceKind`で表示し、CSVと誤表示しない。
- [ ] `createStore`でProviderごとにstoreを作り、SSR共有を避ける。
  `acceptGrid`はintent一致の場合だけ状態を更新し、入力の整合性は受理前に確定させる。
  格子の変更時は現在の選択に最も近い有効な点へ選択を合わせ、範囲外の行列番号を残さない。

```ts
acceptGrid: (intent, grid, sourceKind) => {
  if (get().intent !== intent) return false;
  set({ grid, sourceKind });
  return true;
}
```

- [ ] Viewerは必要なselectorだけを購読する。カメラ更新でCSVパネルや全格子を作り直さない。
  ホバー等のイベントはその場の表示へ閉じ込め、instanceやGPU資源をstoreへ入れない。
- [ ] 既存のCSV競合5件、数値7件、SSR/hydration、2つの独立したProviderを検証してコミットする。

**完了条件:** 表示値・CSV・カメラの互換性を保ち、共通の状態から3D/2D/フローを動かせる。

## 段階2: SVG / ECharts分析とA/B差分

**Create:** `web/components/lab/charts/data.ts`, `svg.tsx`, `echarts.tsx`, `analysis-panel.tsx`, `web/tests/lab-charts.test.ts`, `web/tests/lab-charts.spec.ts`。
**Modify:** `web/components/volatility/slices.tsx`, `web/components/lab/lab.tsx`, `styles.css`, package/lockfile。

**Interfaces:**

```ts
type HeatmapCell = {
  row: number; column: number;
  x0: number; x1: number; y0: number; y1: number; value: number;
};
// heatmapCells(grid: SurfaceGrid): HeatmapCell[]
// sliceSeries(grid: SurfaceGrid, selected: PointIndex):
//   { smile: [number, number][]; term: [number, number][] }
// differencePp(a: SurfaceGrid, b: SurfaceGrid): number[][]
// differencePpは軸不一致なら例外。戻り値はb-aをppに変換した配列。
```

- [ ] 不等間隔の軸と差分をテストする。gridのshapeを変えた場合に比較拒否することも確認する。

```ts
const a = parseSurfaceCsv('tenor_years,moneyness,iv\n0.25,0.9,0.2\n0.25,1.1,0.3\n2,0.9,0.4\n2,1.1,0.5');
const b = parseSurfaceCsv('tenor_years,moneyness,iv\n0.25,0.9,0.25\n0.25,1.1,0.25\n2,0.9,0.4\n2,1.1,0.6');
const diff = differencePp(a, b);
assert.ok(Math.abs(diff[0][0] - 5) < 1e-12);
assert.ok(Math.abs(diff[0][1] + 5) < 1e-12);
assert.equal(diff[1][0], 0);
```

- [ ] EChartsは`echarts/core`から必要なline/custom/grid/tooltip/visualMap/CanvasRendererだけを登録。
  SVGと同じsliceSeriesを使用し、ヒートマップは共通cell境界を数値座標へ描画するcustom seriesにする。

```ts
// 両方のadapterがこの数値列を受け取る。補間・丸めは表示文字だけに適用。
const series = sliceSeries(grid, selected);
const option = {
  animation: false,
  xAxis: { type: 'value' }, yAxis: { type: 'value' },
  series: [{ type: 'line', data: series.smile }],
};
```

- [ ] 2Dのクリックは行列番号を経由して共通Selectionへ変換。3Dと同じ点、同じ数値を示す。
  grid変更時には軸・凡例・選択マーカーも更新し、listener・ResizeObserver・chartを破棄する。
- [ ] `pinReference()`は不変のAを保持する。Bだけ変えて差分を出し、0中心の共通色を使う。
  軸が違うCSVを読んだ場合は差分を止め、Aの再固定を案内する。
- [ ] 390pxでの読取、キーボード、WebGL不可時の2D継続、600/5,000点の操作を検証してコミットする。

**完了条件:** 3D・SVG・EChartsが同じ格子と選択を示す。A/B比較の単位と範囲を誤解なく読める。

## 段階3: React Flowとフォームによる同じ処理

**Create:** `web/components/lab/workflow/model.ts`, `evaluate.ts`, `editor.tsx`, `form.tsx`, `panel.tsx`, `web/tests/lab-workflow.test.ts`, `web/tests/lab-workflow.spec.ts`。
**Modify:** Lab registry/store、package/lockfile。

**Interfaces:**

```ts
type FlowNode =
  | { id: string; kind: 'source' }
  | { id: string; kind: 'shift'; pp: number }
  | { id: string; kind: 'preview' };
type FlowEdge = { from: string; to: string };
type FlowGraph = { version: 1; nodes: FlowNode[]; edges: FlowEdge[] };
type FlowResult =
  | { ok: true; grid: SurfaceGrid }
  | { ok: false; nodeId?: string; message: string };
// evaluateFlow(graph: FlowGraph, source: SurfaceGrid): FlowResult
```

- [ ] 設計書のノード数・接続・循環・範囲規則をZodとグラフ検証に分けてテストする。

```ts
const graph: FlowGraph = { version: 1, nodes: [
  { id: 'a', kind: 'source' }, { id: 'b', kind: 'shift', pp: 5 },
  { id: 'c', kind: 'preview' },
], edges: [{ from: 'a', to: 'b' }, { from: 'b', to: 'c' }] };
const source = createDemoSurface(presets.equity.parameters);
const result = evaluateFlow(graph, source);
assert.equal(result.ok, true);
if (result.ok) assert.equal(result.grid.iv[11][12], 0.25);
assert.equal(source.iv[11][12], 0.20);
```

- [ ] `evaluateFlow`は接続を検証→トポロジカル順で評価→出力格子を検証する純粋関数として実装する。
  shiftは各値へ`pp / 100`を加算。配列を不変に保ち、新しいidと共通表示範囲を再計算する。
- [ ] React Flowはノード配置・接続・編集のUIに限定する。フォームも同じFlowGraphを更新する。

```tsx
// 操作経路が違っても実行関数とエラー表示は同じ。
const result = evaluateFlow(graph, source);
if (result.ok) store.getState().acceptGrid(intent, result.grid, 'workflow');
```

- [ ] 最後の有効なgridと現在の編集中graphを別に保持する。無効な接続で表示結果を消さない。
  sourceは処理前のsnapshotを固定し、出力gridを再入力して+5ppを無限に加算しない。
- [ ] source→shift→previewの接続編集とフォーム操作が同じ値になることをブラウザで確認。
  ノード移動だけでは再計算せず、キーボード/スマホの代替フォームを検証してコミットする。

**完了条件:** 線をつなぐ実験が実際の数値と3D結果を変える。無効なフローは反映されない。

## 段階4: CSS / Motionによる操作演出の比較

**Create:** `web/components/lab/motion/panel.tsx`, `css-demo.tsx`, `motion-demo.tsx`, `web/tests/lab-motion.spec.ts`。
**Modify:** Lab registry/styles、package/lockfile。

**Interfaces:** `MotionDemoProps = { open: boolean; reduced: boolean; onToggle(): void }`。
同じ内容のパネルで開閉と配置変更を比較し、統制モードの時間は200ms、移動量は16pxとする。

- [ ] どちらでもフォーカスが消えず、reduced-motion時は移動しないことをテストする。

```ts
await page.emulateMedia({ reducedMotion: 'reduce' });
await page.goto('/lab?experiment=motion');
await page.getByRole('button', { name: '両方のパネルを開く' }).click();
await expect(page.getByRole('region', { name: 'CSS preview' })).toBeVisible();
await expect(page.getByRole('region', { name: 'Motion preview' })).toBeVisible();
```

- [ ] CSSはtransition、Motionはmotion要素を使い、同じ寸法・内容・durationにする。

```tsx
<motion.div
  initial={false}
  animate={{ opacity: open ? 1 : 0, y: reduced || open ? 0 : 16 }}
  transition={{ duration: reduced ? 0 : 0.2 }}
/>
```

- [ ] 閉じた要素はフォーカス対象から外し、開閉後のフォーカスを共通の規則で扱う。
  バネやlayoutアニメーションは「表現を試す」で有効化し、統制比較と区別する。
- [ ] IV数値や金融データの変更自体には演出を混ぜず、チャートの速度比較中も演出を停止する。
- [ ] キーボード・タッチ・連続開閉・reduced-motionを検証してコミットする。

**完了条件:** 動きの違いを同じ操作で確認でき、動きを減らす設定でも機能が保たれる。

## 段階5: fetch / TanStack Queryの取得・キャッシュ比較

**Create:** `web/components/lab/data/load-snapshot.ts`, `use-native.ts`, `use-query.ts`, `panel.tsx`, `web/public/lab-data/{a,b}.json`, `web/tests/lab-data.spec.ts`。
**Modify:** Lab registry/store/schema、package/lockfile。

**Interfaces:** snapshot JSONは`{ schemaVersion: 1, id, revision, source: 'synthetic', rows }`。
rowsの各行は`{ tenor_years: number; moneyness: number; iv: number }`。

```ts
type Snapshot = { id: string; revision: string; grid: SurfaceGrid };
type TransportScenario = 'normal' | 'delay' | 'fail';
type LoadState = {
  status: 'idle' | 'pending' | 'success' | 'error';
  snapshot?: Snapshot; message?: string; fetching: boolean;
  reload(): void; cancel(): void;
};
// loadSnapshot(id: 'a' | 'b', signal: AbortSignal,
//   scenario: TransportScenario): Promise<Snapshot>
// useNativeSnapshot(id: 'a' | 'b', scenario: TransportScenario): LoadState
// useQuerySnapshot(id: 'a' | 'b', scenario: TransportScenario): LoadState
```

- [ ] 正常、2秒遅延、失敗、A→B→Aのテストを追加。fixtureのHTTP応答だけを制御し、UI/検証処理は実物を使う。
  Aの完了が遅れてもBが残る、キャンセルがエラー表示にならない、入力不正で前の結果を保持することを確認する。
- [ ] native版はAbortControllerと操作番号、Query版はquery keyとsignalを使う。
  データは同一originの固定JSONを共有し、どちらも`response.ok`とZod検証を通す。
  fixtureのrevisionは`v1`に固定し、応答のid/revisionが要求と一致することも検証する。
  `delay`は取得前の2秒待機もAbortSignalで中断し、`fail`は模擬通信エラーを返す。

```ts
const query = useQuery({
  queryKey: ['lab-snapshot', id, 'v1', scenario],
  queryFn: ({ signal }) => loadSnapshot(id, signal, scenario),
  staleTime: 60_000,
  retry: false,
  refetchOnWindowFocus: false,
});
```

- [ ] QueryのProviderはData実験内で維持し、Query版のデータ切替でキャッシュを再利用する。
  native版はキャッシュなしの基準であることを明記し、Queryにもキャッシュを空にする操作を用意する。
  Queryの既定retryやfocus再取得を比較条件に混ぜない。中断操作はnativeのcontrollerと
  Queryの対象キーに対する`cancelQueries`へ接続し、最後の成功結果を消さない。
- [ ] 取得結果の表示とSurfaceへの採用を分離する。「このデータをSurfaceで使う」で
  新しいintentを発行してsnapshotを固定する。背景取得だけでCSVやフロー出力を置き換えない。
- [ ] A→B→Aでnativeは3要求、Queryはfresh cacheなら2要求になるテストを行う。
  遅延/失敗を試すUIは「通信のシミュレーション」と明示し、共通のabort可能なloaderへ同じ条件を渡す。
  この要求数の検証は`normal`条件の60秒以内に行い、HTTPキャッシュは無効にする。
- [ ] キャンセル・再試行・schema違反・キャッシュ再利用・データ採用を確認してコミットする。

**完了条件:** 取得中と再取得中、キャッシュ、失敗時の違いを操作して観察できる。

## 段階6: 性能と用途別の比較結果

**Create:** `web/components/lab/benchmark/contract.ts`, `runner.ts`, `results.tsx`, `web/scripts/compare-lab-load.mjs`, `web/tests/lab-benchmark.test.ts`, `web/tests/lab-benchmark.spec.ts`。
**Modify:** `web/components/orbit/measurement.ts`の再利用箇所、各実験adapter、Lab registry、README。

**Interfaces:**

```ts
type RunCondition = {
  experiment: ExperimentId; implementation: string;
  points?: number; width: number; height: number; dpr: number;
  cache: 'cold' | 'warm'; seed: number;
};
type DrawEvent = { revision: number; at: number }; // CPU側の描画処理完了通知
type RunResult = {
  condition: RunCondition; status: 'complete' | 'aborted' | 'unsupported';
  reason?: string; frames?: FrameMeasurement;
  readyMs?: number; updateMedianMs?: number; updateP95Ms?: number;
};
// 各adapterはrequest revisionに対応するDrawEventを通知する。
// Runnerは古いrevisionやmountだけのreadyを計測完了として採用しない。
// Surfaceのpointsは600/2500/5000から選ぶ。Geoは別の点数を記録する。
// Motionや通信など点数が意味を持たない実験ではpointsを省略する。
```

- [ ] 準備前のフレーム、古い更新通知、hidden/resize/context lostの途中結果を破棄するテストを先に追加する。

```ts
const measure = createFrameMeasurement(1000, 4000);
assert.equal(measure(0), null);
assert.equal(measure(999), null);
assert.equal(measure(1000), null);
const result = measure(5000);
assert.equal(result?.durationMs, 4000);
assert.equal(result?.frames, 1);
// この単体例は時計処理のみ。実際の性能はブラウザで十分なフレームを採取する。
```

- [ ] Plotlyの描画完了通知、Three/Babylonの描画後通知、ECharts/SVGの更新完了を
  同じRunResultへ変換する。実GPUの提示完了を測ったとは扱わない。
- [ ] 1実装ずつmountして固定操作を実行し、設計書のwarmup・5回・順序循環を守る。
  同じ表示条件を満たせない組合せはunsupportedとし、数値を補わない。
- [ ] Coldは新しいbrowser context＋初期navigation、warmは読み込み済み依存/資源で再実行。
  表示時間は5回の中央値と範囲、連続描画はFPSとフレーム間隔p95を示す。
- [ ] 既存JS量scriptをラボの各実験へ広げ、初期取得と実験開始後の追加取得を分ける。
  サンプル数・環境・version・commit・データrevision付きJSONをローカル保存する。
- [ ] Resultsに用途別比較表を置く。機能と実装上の注意は説明、速度と容量は実測と明示し、
  異なる単位を混ぜた総合点や未測定のランキングを作らない。
- [ ] 本番3101で実描画・途中中止・履歴・JSON出力を検証し、読み込み失敗も確認してコミットする。

**完了条件:** ユーザー自身の端末で比較でき、結果から条件と限界を確認できる。

## 段階7: SVG / MapLibreの地図実験

**Create:** `web/components/lab/geo/data.ts`, `svg-map.tsx`, `maplibre-map.tsx`, `panel.tsx`, `web/public/lab-data/regions.geojson`, `web/tests/lab-geo.test.ts`, `web/tests/lab-geo.spec.ts`。
**Modify:** Lab registry/benchmark、package/lockfile、データ出所のREADME。

**Interfaces:**

```ts
type GeoPoint = { id: string; name: string; lng: number; lat: number; value: number };
type GeoView = { lng: number; lat: number; zoom: number };
// mercatorUnit(lng: number, lat: number): [number, number]
// validateGeoPoints(input: unknown): GeoPoint[]
// 入力緯度は±85.051129以内、経度は±180以内。ID重複・非有限値を拒否する。
```

- [ ] 同梱データの出所・利用条件・架空の指標であることを記録し、境界・重複・座標変換をテストする。

```ts
assert.deepEqual(mercatorUnit(0, 0), [0.5, 0.5]);
assert.equal(mercatorUnit(180, 0)[0], 1);
assert.throws(() => validateGeoPoints([
  { id: 'a', name: 'A', lng: 0, lat: 90, value: 1 },
]));
```

- [ ] MapLibreはローカルGeoJSONのsource/layerだけを持つstyleで開始する。
  SVGも同じ投影、境界、選択、色を使用する。外部tileを取得しないことをnetworkで確認する。

```ts
const x = (lng + 180) / 360;
const latitude = lat * Math.PI / 180;
const y = (1 - Math.asinh(Math.tan(latitude)) / Math.PI) / 2;
// 入力範囲の検証後に使用する。
```

- [ ] 点選択とzoomを同期し、標準フォームから地点も選択できるようにする。
  mapの`remove()`、observer、listenerのcleanupとWebGL不可時のSVG/数値表示を検証する。
- [ ] 地図の比較は独自の点数・viewport・投影条件でResultsへ記録し、IVの3Dランキングと混ぜない。
- [ ] 地理座標・選択同期・境界・通信遮断・スマホを確認してコミットする。

**完了条件:** 地図向けライブラリの操作と自由度を、実在の市場データを仮定せず試せる。

## 各段階の検証・引渡し

通常のWeb変更は `komorebi-3d/web` で以下を実施する。

```bash
npm run typecheck
npm run lint
npm run build
PLAYWRIGHT_CHROMIUM_EXECUTABLE=/path/to/chrome npm test
```

同一sourceの本番serverが既に起動していればテストで再利用し、無変更の再ビルドを繰り返さない。
再ビルド時は古い3101のserverを停止してから再起動する。3100の開発cache検証を速度測定に使わない。
データ・演算には既知の数値の単体テスト、操作・同期・破棄には必要なブラウザテストを使う。
重要な不具合は失敗を再現してから修正し、独立レビューを経て次段階へ進む。
プロジェクトのAGENTSに従い、Pythonの既存テスト・構文も最後に確認する。
実機のSafari/iPhone・読み上げソフトを未確認なら、その範囲を検証記録へ残す。

**最初の実装範囲の提案:** 段階0〜2を完成させる。Surfaceの比較価値が増えた状態で、
段階3のReact Flowへ進む。新規機能の実装や依存追加は、このプランに対する実行指示を受けて開始する。
