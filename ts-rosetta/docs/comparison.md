# 実装比較 — 実測値と観察

計測日: 2026-07-09 / 環境: WSL2 (Linux 6.18), Node v22.22.2, pnpm 11.1.0,
Chrome Headless Shell 149 (Playwright 1.61), すべて production ビルド。

## 計測方法

- **LOC**: 各実装のアプリコード（設定ファイル除く）の行数。`wc -l`。
- **バンドル**: `pnpm build` の出力サイズ（フレームワーク込み初期ロード）。
- **bench**: 各アプリ内蔵のベンチモード。N 件生成→描画コミット+paint 完了までの
  `render` ms、全件 done 反転→paint 完了までの `update-all` ms。
  `tools/verify-bench.mjs`（Playwright）で 3 回計測の中央値。
  再計測: preview サーバー起動後 `node tools/verify-bench.mjs`。

## UI 3 実装（同一機能: 追加/トグル/削除/フィルタ/集計/ベンチ）

| 実装 | LOC | バンドル raw | gzip | 1k render | 1k update | 10k render | 10k update |
|---|--:|--:|--:|--:|--:|--:|--:|
| React 19 + Vite | 193 | 197.4 kB | 62.3 kB | 30.8 ms | 32.7 ms | 336.1 ms | 125.8 ms |
| Vue 3 + Vite | 182 | 68.5 kB | 27.2 kB | 30.1 ms | 33.4 ms | 232.9 ms | 181.2 ms |
| Angular 20 | 232 | 152.8 kB | 47.0 kB | 30.6 ms | 33.4 ms | 224.3 ms | 155.5 ms |

観察:

- **1,000 件では 3 者に差がない**（~30ms、paint 律速）。フレームワーク選定で
  「性能」が効いてくるのは桁が上がってから。
- **10,000 件で個性が出る**: 初回 render は React が最遅（VDOM 構築 + コミットが
  一体）、update-all は React が最速で Vue が最遅。同じ「宣言的 UI」でも
  再描画戦略（全再レンダー+差分 vs リアクティブ依存追跡）のトレードオフが逆に出る。
- **バンドルは Vue < Angular < React**。Angular は zone.js（34.6 kB raw）込み。
  React 19 + ReactDOM はランタイムが最も大きい。
- LOC はほぼ同水準。Angular が +40 行なのは service/DI の分離構造ぶん。

## サーバー 2 実装（同一 REST API: GET/POST/PATCH/DELETE /tasks + /stats）

| 実装 | LOC | ファイル数 | 構造 |
|---|--:|--:|---|
| Express 5 | 67 | 1 | 手続き的。ルート・状態・配線がすべて 1 ファイル |
| NestJS 11 | 137 | 6 | module / controller / service / DTO。DI + ValidationPipe |

- 同一挙動を curl で確認済み（201/200/204/404/400 が完全一致）。
- Express は「何も強制しない」= 小さいうちは速いが、構造は自分で決める必要がある。
- Nest は約 2 倍のコードと引き換えに、バリデーション（`class-validator` の
  デコレータ）・エラー処理（`NotFoundException`）・責務分離が枠組みで決まる。

## Next.js（React の「上」の階層）

- `curl -s localhost:3000` の生 HTML にタスク `<li>` が含まれる（**SSR**）。
  素の Vite React (5173) は `<div id="root"></div>` のみ → JS 実行後に描画。
- 同じプロジェクト内に Route Handler（`app/api/tasks/`）があり、Express/Nest が
  担う役割を Web アプリに内蔵できる。
- First Load JS 102 kB（gzip 後）。UI+API 込みで LOC 203。

## TS ↔ JS（言語階層）

`docs/js-vs-ts.md` 参照。同じバグが TS ではコンパイル時に止まり、JS では
`NaN` を静かに出力 → 実行時 TypeError で落ちる実出力を記録。

## 高頻度ライブ盤面（リアクティビティ比較・発展）

`docs/reactivity.md` 参照。各 UI アプリの `#board`（+ apps/solid）で同一
ティックストリームを 5 通りの配線で描画。naive React は work/s が触られた行の
10.6 倍（= 行数×tick数）、fps の律速は巨大テーブルの layout でフレームワーク間
に差が出ない、が実測の結論。

## 再計測手順

```bash
pnpm build                       # 全パッケージ prod ビルド
pnpm --filter @rosetta/app-react preview   # :4173
(cd apps/vue && pnpm exec vite preview --port 4174)
(cd apps/angular/dist/browser && python3 -m http.server 4175)
node tools/verify-bench.mjs      # 機能検証 + bench 中央値を出力
```
