# 0001 — Monorepo tooling and core packaging

Status: Accepted (2026-07-09)

## Context

学習ラボとして「同一アプリを React / Vue / Angular / Next.js / Express / NestJS で
並列実装し、共通ドメインロジックを 1 箇所に置く」構成が必要。ワークスペース
(~/projects) の JS 側には統一ツールチェーンが存在しない（pokemon=npm+Vite、
gto/web・market-viz=pnpm+Next）。各ツールチェーンの TS 対応バージョンも異なる。

## Decision

- **pnpm workspace** を採用（packages/* + apps/* + dashboard）。Turborepo/Nx は
  導入しない — ビルドオーケストレーションを学ぶのが目的ではないため。
- **TypeScript 5.8 系で統一**（Angular 20 の対応上限に合わせる。pokemon の TS6 は
  追わない）。共通 strict 設定は `tsconfig.base.json`。
- **@rosetta/core は TS ソース配布**（`exports.import` → `src/index.ts`）。
  Vite 系はそのまま transpile、Next は `transpilePackages` で対応。
  - 例外は CJS しか読めない **NestJS**: `prepare` スクリプトで `dist/cjs` を
    自動ビルドし `exports.require` / `main` に割り当てる（`"type": "module"`
    パッケージ内なので `dist/cjs/package.json` に `{"type":"commonjs"}` を書く）。
- core の相対 import は**拡張子なし**（`./store`）。`.js` 拡張子方式は Next の
  webpack が `extensionAlias` 未設定で解決できないため却下。純 Node ESM 実行は
  しない（consumers は全員バンドラ or tsx）ので問題ない。
- core は **DOM lib 非依存**で型チェックが通ること（`requestAnimationFrame` は
  `globalThis` 経由で参照）。server-express / server-nest が `lib: ES2022` で
  core のソースを再チェックするため。
- ベンチ計測・UI 検証は **Playwright（root devDep）+ tools/verify-bench.mjs**。
  数値は prod ビルド（vite preview / 静的配信）に対して測る。

## Consequences

- `pnpm install` だけで core の CJS dist まで揃う（prepare 自動実行）。
- Angular / Nest のバージョンを上げる際は TS バージョン上限を再確認する必要がある。
- core に DOM 依存コードを足すと server 2 実装の型チェックが壊れる（意図的な檻）。
- 各実装のツールチェーン差（Vite / Angular CLI / next / tsc / nest build）は
  学習対象としてあえて残している。
