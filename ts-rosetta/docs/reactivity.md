# 高頻度ライブ盤面 — リアクティビティ比較（実測）

同一のティックエンジン（`packages/core/src/market.ts`）が毎秒 N 回、銘柄の 10% を
ランダムウォーク更新する。5 つの盤面（React naive / React optimized / Vue /
Angular / Solid）は**同じ更新ストリーム**（シード固定）を受け取り、
自分のリアクティビティ機構で DOM に配線する。違いはそこだけ。

計測日: 2026-07-10 / WSL2, Chrome Headless Shell 149 (Playwright), prod ビルド,
3〜6 サンプル中央値。再計測: `node tools/verify-board.mjs`（手順はファイル冒頭）。

## 指標

- **upd/s** — 実際に適用された quote 更新数/秒。メインスレッドが詰まると
  setInterval が間引かれて下がる＝スループットの正直な信号
- **work/s** — フレームワークが行った仕事の単位/秒。**意味が実装ごとに違う**:
  React=行の再レンダー、Vue=行コンポーネント更新、Angular=行の CD チェック、
  Solid=last セルの effect 実行
- **fps / long** — rAF フレームレート / 32ms 超フレーム数（体感カクつき）

## 結果

### work/s — リアクティビティ戦略の差はここに出る

| 構成 (touched/s) | React naive | React opt | Vue | Angular | Solid |
|---|--:|--:|--:|--:|--:|
| 200 銘柄 @40tps (~750) | **8,000** | 751 | 752 | 745 | 749 |
| 1,000 銘柄 @60tps (~5,900) | **62,161** | 5,872 | 5,887 | 5,887 | 5,887 |
| 5,000 銘柄 @60tps | **95,247** | 11,198 | 8,734 | 10,538 | 9,167 |

- naive React の work/s は**正確に 行数 × tick数**（200×40=8,000、1,000×60=60,000）。
  親の `setState` が毎 tick 全行を再レンダーするため。**触られた行の ~10.6 倍**。
- optimized React / Vue / Angular / Solid は **work/s ≈ touched/s**。
  4 つの異なる機構（外部ストア購読 / reactive オブジェクト / signal+OnPush /
  fine-grained effect）が全く同じ数字に収束する — 「変わった行だけ触る」を
  実現する手段が違うだけ。

### fps — この題材ではフレームワーク差が出ない（重要な発見）

| 構成 | React naive | React opt | Vue | Angular | Solid |
|---|--:|--:|--:|--:|--:|
| 1,000 @60tps | 60 | 60 | 60 | 60 | 60 |
| 1,000 @60tps + CPU 4x 絞り | 34 | 30 | 27 | 26 | 23 |
| 5,000 @60tps | 29 | 25 | 19 | 24 | 20 |

- デスクトップでは 1,000 行 ×60tps でも全員 60fps — naive の 10 倍の無駄すら
  マシンが吸収してしまう。
- 負荷を上げる（CPU 絞り・5,000 行）と **全員ほぼ同じだけ崩れる**。
  差の順序はラン間で入れ替わるノイズ水準で、naive が最下位にすらならない。
- 理由: 崩れる時のボトルネックは**巨大テーブルのブラウザ layout**
  （5,000 行 ≈ 30k+ ノード）で、これは全フレームワーク共通のコスト。
  この盤面の行（5 セル・素の td）は軽量すぎて、フレームワークの JS 差が
  layout の影に隠れる。

## 結論 — 何が本当の教訓か

1. **リアクティビティ戦略の差は「fps」ではなく「CPU 予算の消費量」に出る**（10.6 倍）。
   naive でも 60fps は出る。ただしその裏で CPU を 10 倍食っており、
   チャート描画・計算・GC など**他の仕事をする余裕**が消えている。
   行コンポーネントが重い実アプリ（ネストしたコンポーネント・アイコン・
   フォーマッタ）ほど、この倍率がそのまま fps に直撃するようになる。
2. **fps を守る本命はフレームワーク選択ではなく仮想化**。5,000 行で全員崩壊
   したのが証拠 — 見えている ~40 行だけ DOM 化すれば layout コストは消える
   （ag-Grid / TanStack Virtual / CDK Virtual Scroll がやっていること）。
3. **「変わった行だけ触る」の実現コストがフレームワークで違う**:
   Vue / Solid はそれが既定の動作、Angular は signal + OnPush + zone 外実行の
   組み合わせで到達、React だけ**自分で外部ストアを組む必要があった**。

## 各実装の罠と対策（コード対応表）

### React — 罠: 素朴な setState は全行再レンダー

```tsx
// 罠 (apps/react/src/Board.tsx NaiveBoard): 親の state を毎 tick 更新
setQuotes(prev => { /* コピーして差し替え */ });  // → 全 <Row> 再実行

// 対策 (boardStore.ts + OptRow): 外部ストア + 行単位購読
const q = useSyncExternalStore(store.subscribes[i], store.snapshots[i]);
// → 自分のスロットが変わった行だけ再レンダー (work 10.6x → 1x)
```

React は既定でコンポーネント木を上から再帰する。細粒度が欲しければ
`useSyncExternalStore` / zustand セレクタ / memo で**自分で彫る**。

### Vue — 既定で細粒度（ただし行をコンポーネントに切ること）

```ts
// apps/vue/src/Board.vue: reactive オブジェクトを in-place 変更
Object.assign(quotes.value[u.index], { last, bid, ask, changePct, dir });
// BoardRow.vue が行ごとの render effect → 変わった行だけ更新
```

注意: 1 コンポーネント内の巨大 `v-for` は**コンポーネント単位**で再レンダー
される。行を `BoardRow` に切り出して初めて行単位になる。

### Angular — 罠: zone.js は何でも全体 CD にする

```ts
// 対策 (board.component.ts): エンジンと rAF を zone の外で回す
this.zone.runOutsideAngular(() => { engine.start(); this.perf.start(); });
// 行ごとの WritableSignal<Quote> + OnPush 行コンポーネント
row.q.set({ ...row.q(), last: u.last, ... });  // → その行だけ dirty
```

zone 内で setInterval を回すと毎 tick アプリ全体の変更検知が走る（60 回/秒）。
signal 書き込みは zone 外からでも対象ビューだけを dirty にできる（v18+）。

### Solid — 設計で罠を消した側

```tsx
// apps/solid/src/Board.tsx: 再レンダーという概念がない
setRows(u.index, { last: u.last, ... });  // store パス更新
// JSX の各 {式} がセル単位の effect → 変わったセルの DOM だけ patch
```

「optimized React が手作業で組んだ構造」が Solid では言語設計そのもの。
バンドルも 19.3 kB (gzip 7.8 kB) と React の約 1/10。

## 制限・正直な注記

- headless / WSL2 の数値。実ブラウザ・実 GPU では絶対値が変わる（傾向は同じはず）。
- fps は 60 上限に張り付くため、健全域では差が見えない。work/s と upd/s が主指標。
- work/s の定義がフレームワークごとに違う（上記）。「行を触った回数」として
  揃えているが、1 回あたりの実コストは同一ではない。
- CPU 4x 絞りは Chrome DevTools のエミュレーション。実機のミドル帯スマホとは
  熱・メモリ帯域の挙動が異なる。
- 仮想化は実装していない（このラボの範囲外）。5,000 行の崩壊がその必要性の実証。
