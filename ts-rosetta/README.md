# TS Rosetta — TypeScript エコシステム学習ラボ

**同一のタスク管理アプリ（＋ベンチマークモード）を、TypeScript エコシステムの
各階層の技術で並列実装**した Rosetta Stone 方式の学習リポジトリ。
アプリが同じなので、純粋に技術の違い — 構文・できること/できないこと・
パフォーマンス・階層関係 — だけが浮かび上がる。

## 階層マップ

```
言語         TypeScript ──(tsc / bundler が変換)──> JavaScript
                                                       │
実行環境                        ブラウザ ◄─────────────┴─────────────► Node.js
UI ライブラリ      React 19 │ Vue 3 │ Angular 20                        │
フレームワーク     Next.js 15 (React の上・SSR・両側で動く)   Express 5 │ NestJS 11
プラットフォーム   Electron (デスクトップ) / React Native (モバイル) — docs のみ
```

## セットアップと起動

```bash
pnpm install          # 全依存 + @rosetta/core の CJS dist を自動ビルド
pnpm test             # core の Vitest (8 tests)
pnpm build            # 全パッケージ prod ビルド
```

| コマンド | 何が起きるか | URL |
|---|---|---|
| `pnpm dev:dashboard` | **ここから始める** — 階層マップ + 比較表 | localhost:8080 |
| `pnpm dev:ui` | React / Vue / Angular をまとめて並列起動 | 5173 / 5174 / 4200 |
| `pnpm dev:react` | React 実装（`#board` = ライブ盤面） | localhost:5173 |
| `pnpm dev:vue` | Vue 実装（`#board` = ライブ盤面） | localhost:5174 |
| `pnpm dev:angular` | Angular 実装（`#board` = ライブ盤面） | localhost:4200 |
| `pnpm dev:solid` | Solid ライブ盤面（比較参加者） | localhost:5175 |
| `pnpm dev:next` | Next.js 実装 (SSR) | localhost:3000 |
| `pnpm dev:express` | Express API | localhost:4000/tasks |
| `pnpm dev:nest` | NestJS API | localhost:4001/tasks |

## 学習コース（推奨順）

1. **言語**: `pnpm --filter @rosetta/core demo:ts` と `demo:js` を実行。
   同じバグが TS ではコンパイル時に止まり、JS では実行時に NaN/クラッシュに
   なるのを見る → `docs/js-vs-ts.md`
2. **共通コア**: `packages/core/src/` を読む。フレームワーク非依存の純 TS 関数。
   全実装がこれを import している。
3. **UI 3 実装**: `apps/react` → `apps/vue` → `apps/angular` の順に
   App を読み比べる。同じ機能・同じ core・違うのはリアクティビティと構文だけ。
   各アプリの Bench ボタンで 10,000 件描画の実測差を見る。
4. **サーバー**: `apps/server-express/src/main.ts`（67 行 1 ファイル）と
   `apps/server-nest/src/`（6 ファイル DI 構造）。同じ API を curl で叩いて確認:
   `curl localhost:4000/tasks` / `curl localhost:4001/tasks`
5. **Web フレームワーク**: Next.js を起動して `curl -s localhost:3000` —
   HTML にタスクが入っている（SSR）。React 版 (5173) の空 `<div id="root">` と
   見比べる。
6. **プラットフォーム**: `docs/platforms.md` — Electron / React Native は
   何が同じで何が違うか。
7. **リアクティビティ（発展）**: 各 UI アプリの `#board`（Solid は :5175）で
   高頻度ライブ盤面を動かす。React だけ naive / optimized の 2 モードがあり、
   同じ負荷で work/s が 10.6 倍違うのを見る → `docs/reactivity.md`。
   結論: 差は fps ではなく CPU 予算に出る。fps を守る本命は仮想化。

## 実測比較

`docs/comparison.md` に LOC / バンドルサイズ / ベンチ結果（環境明記）。
再計測は `node tools/verify-bench.mjs`（Playwright で機能検証も兼ねる）。

## 構成

```
packages/core/       @rosetta/core — 共有ドメインロジック + ティックエンジン (純 TS)
apps/react|vue|angular/              UI 実装 (tasks + #board ライブ盤面)
apps/solid/                          Solid ライブ盤面 (リアクティビティ比較)
apps/next/                           Next.js (SSR 対比)
apps/server-express|server-nest/     REST API 実装 (挙動同一)
dashboard/           学習ダッシュボード (依存ゼロ静的配信)
docs/                comparison / js-vs-ts / platforms / reactivity / ADR
tools/verify-bench.mjs   タスクUI 機能検証 + ベンチ (Playwright)
tools/verify-board.mjs   ライブ盤面 機能検証 + 計測 (Playwright + CPU throttle)
```

設計判断の経緯は `docs/decisions/`（0001 = monorepo/packaging、0002 = 盤面設計）。
