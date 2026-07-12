# ts-rosetta — ハンドオフ

最終更新: 2026-07-10 / 状態: **2 モジュール完成・動作検証済み・未コミット**

次のセッション（または別の担当）がこの状態から続けるための引き継ぎ書。
まず読む順: この HANDOFF → `README.md` → 各 `docs/*.md`。

---

## 1. これは何か

`~/projects/ts-rosetta/` は **TypeScript エコシステム学習ラボ**（pnpm monorepo）。
「表に並ぶ技術（TS/JS・React/Vue/Angular・Next・Node・Express/Nest・
Electron/RN）は**役割の階層が違う**」を体感するため、**同一の小さなアプリを
各階層で別実装して並べる** Rosetta Stone 方式。

現在 2 つの比較モジュールが載っている:

1. **タスク管理アプリ**（全 UI/サーバー階層で機能同一）— 構文・できること・
   階層関係・基本性能を比較。
2. **高頻度ライブ盤面**（`#board`）— リアクティビティ機構を負荷下で比較。
   トレーディング UI の議論から派生：「フレームワーク差が実際に出るのは
   多数要素を自前で高頻度更新する場面だけ」を実測で示す目的。

## 2. セッションの経緯（なぜ今この形か）

- 発端: ユーザーが「TS 周辺の言語/ライブラリの違いを広く浅く体感したい」。
- モジュール1（タスク）を構築 → 「見比べポイント」を対話。
- トレーディング UI（TWS 風スクショ）を題材に「どこで差が出るか」を議論 →
  結論「チャート等は専用ライブラリが主役、フレームワークは糊。差が出るのは
  多数要素の自前描画だけ」。
- その"差が出る唯一の場面"を実アプリで体感するため、モジュール2（ライブ盤面）を
  追加。**Solid** を比較参加者に採用（JSX は React 風・実行モデルだけ違うため
  「構文≠実行モデル」を最小差分で見せられる）。

## 3. 構成とポート

```
packages/core/       @rosetta/core — 共有ロジック(純TS) + ティックエンジン
  src/types,store,bench,api,market,styles.css   index.ts で再export
  src/*.test.ts       Vitest 14 tests
  js-vs-ts/           TS(コンパイル時停止) vs JS(実行時NaN/crash) デモ
  dist/cjs/           Nest 用 CJS ビルド(prepare で自動生成)
apps/react/    :5173  Tasks + #board(naive/optimized トグル)
apps/vue/      :5174  Tasks + #board
apps/angular/  :4200  Tasks + #board
apps/solid/    :5175  board のみ(リアクティビティ比較参加者)
apps/next/     :3000  SSR タスク + Route Handler
apps/server-express/ :4000  REST API(手続き的1ファイル)
apps/server-nest/    :4001  REST API(DI/DTO 構造化)
dashboard/     :8080  依存ゼロ静的ポータル(階層マップ+比較表)
tools/verify-bench.mjs   タスクUI 機能検証+ベンチ (Playwright)
tools/verify-board.mjs   盤面 機能検証+計測 (Playwright + CPU throttle)
docs/          comparison / js-vs-ts / platforms / reactivity / decisions(ADR)
```

環境: Node v22.22.2, pnpm 11.1.0, Playwright 1.61 + chromium-headless-shell。
TypeScript 5.8 で統一（Angular/Nest の対応上限に合わせる）。

## 4. 起動・検証コマンド

```bash
cd ~/projects/ts-rosetta
pnpm install            # core の CJS dist まで自動(prepare)
pnpm test               # core Vitest 14 tests
pnpm build              # 全パッケージ prod ビルド

pnpm dev:dashboard      # :8080 学習の地図。ここから始める
pnpm dev:react          # :5173 (/#board でライブ盤面)
pnpm dev:solid          # :5175
pnpm dev:express        # :4000  ; pnpm dev:nest → :4001
```

再計測（prod ビルド + preview サーバー起動が前提。手順は各 mjs 冒頭コメント）:

```bash
node tools/verify-bench.mjs   # タスクUI: 機能 + 10k ベンチ中央値
node tools/verify-board.mjs   # 盤面: live 検証 + fps/long/upd/work (CPU throttle込)
```

ポート後始末は `fuser -k <port>/tcp`（後述の落とし穴参照）。

## 5. 検証済みの事実（DoD）

- core: **14 tests passed**。`pnpm build` 全パッケージ **exit 0**。
- タスク UI（React/Vue/Angular）: Playwright で add/toggle/filter/delete/stats
  **全 OK**。10k ベンチが ms/fps を実表示。
- サーバー: Express/Nest を curl で叩き **201/200/204/404/400 が完全一致**。
- Next: `curl localhost:3000` の生 HTML にタスク `<li>` あり（SSR 実証）。
- js-vs-ts: `demo:ts` が `error TS2322`、`demo:js` が `total: NaN` → 実行時
  `TypeError` を実出力で確認。
- 盤面 5 実装: Playwright で **live=true × 20 構成**。Angular は zone 外 signal
  更新が dev モードでも実描画されることを確認（`▲488.96→▼488.98`）。

## 6. 実測サマリ（環境依存・headless/WSL2）

**タスク 10,000 件ベンチ**（2026-07-09、`docs/comparison.md`）:

| | バンドル gz | 10k render | 10k update-all |
|---|--:|--:|--:|
| React 19 | 62.3 kB | 336 ms(最遅) | 126 ms(最速) |
| Vue 3 | 27.2 kB | 233 ms | 181 ms(最遅) |
| Angular 20 | 47.0 kB | 224 ms | 156 ms |

→ 1,000 件では 3 者横並び(~30ms)。render と update で速い遅いが逆転。

**ライブ盤面**（2026-07-10、`docs/reactivity.md`、1,000銘柄@60tps, touched≈5,900/s）:

| | work/s | 意味 |
|---|--:|---|
| React **naive** | **62,161** | = 行数×tick数 = 触られた行の 10.6 倍 |
| React opt / Vue / Angular / Solid | ~5,887 | 4 機構が work≈touched に収束 |

→ **fps はどの負荷でも FW 間で差がつかない**（CPU 4x絞りで全員23-34、
5000行で全員19-29）。律速は巨大テーブルの browser layout（共通コスト）。
**結論: 差は fps でなく CPU 予算に出る／fps を守る本命は仮想化**。

## 7. 落とし穴（再発しやすい・最重要）

`docs/decisions/0001` `0002` に根拠。作業前に必ず目を通すこと。

- **core は TS ソース配布**（`exports.import`→src）。**Nest だけ CJS 必須** →
  `prepare` で `dist/cjs` 自動生成 + `dist/cjs/package.json` に
  `{"type":"commonjs"}`。
- core の相対 import は**拡張子なし**（`./store`）。`.js` 付きは Next webpack が
  解決不可。
- core は **DOM lib 非依存**で型が通ること（servers が `lib:ES2022` で再チェック）。
  `requestAnimationFrame` は `globalThis` 経由で参照。
- **Angular dev-server（`ng serve`）**は `angular.json` の `prebundle.exclude:
  ['@rosetta/core']` ＋ `tsconfig.app.json` の include に core src 追加が必要
  （prod `ng build` は不要）。
- **pnpm 11 は build script 承認制**（`pnpm-workspace.yaml` の `allowBuilds`）。
  esbuild/sharp/@parcel/watcher/lmdb/msgpackr-extract を承認済み。
- Next は `transpilePackages: ['@rosetta/core']`。
- **`pkill -f` は自分のコマンド文字列に自己マッチして exit 144 で自滅**する。
  ポート解放は `fuser -k <port>/tcp` を使う。
- 盤面の **work/s は FW ごとに定義が違う**（React=行レンダー/Vue=行更新/
  Angular=行CDチェック/Solid=last セル effect）。Solid のカウントは dir でなく
  **last のテキスト effect** に載せる（dir は半分しか変化せず過少計上になる）。

## 8. 未完了・制限（Not done）

- **Electron / React Native は非実行**（`docs/platforms.md` の解説＋スニペットのみ）。
- **仮想化なし**（5,000 行の全員崩壊がその必要性を実証している）。
- ESLint は各 app に flat config はあるが必須運用にしていない。Prettier/Biome なし。
- 盤面・ベンチ数値は headless Chrome / WSL2。実ブラウザ・実 GPU で絶対値が変わる。
- 認証/DB/デプロイ/CI なし（学習ラボのため範囲外）。
- **git 未コミット**（下記）。

## 9. git / 未コミット状態

`~/projects` リポジトリ内で **ts-rosetta/ 全体が untracked**、
ルートの `CLAUDE.md` `AGENTS.md` に ts-rosetta の 1 行追記（modified）。
リポジトリ外にも次を作成済み（未コミット）:

- memory: `~/.claude/projects/-home-kazumasa-projects/memory/project_ts_rosetta.md`
  ＋ `MEMORY.md` の索引 1 行。
- wiki inbox（レビュー待ち・push しない運用）:
  - `~/wiki/inbox/2026-07-09-shared-ts-package-multi-toolchain.md`
  - `~/wiki/inbox/2026-07-10-reactivity-perf-where-differences-show.md`
- VSCode 推奨拡張: `ts-rosetta/.vscode/extensions.json`（Vue.volar 等）。

コミットする場合の方針（ワークスペース規約）: **main で直接コミットせず先に
ブランチを切る**。破壊的操作・push は明示指示があるまで行わない。

## 10. 次の一手（backlog、優先度順の目安）

1. **git コミット**（feature ブランチを切って）。ユーザー指示待ち。
2. **重い行の実験**: 行を現実的な重さ（ネスト 10–20 コンポーネント）にして、
   naive React の fps が実際に分離し始める行数×tick を探る。※人工ベンチになる
   自覚を持つこと（ADR 0002 参照）。
3. **仮想化デモ**を各盤面に追加 → 5,000 行崩壊が消えることを実証。
4. **Vue Vapor / React Compiler / Svelte** を同一エンジン・同一指標で盤面に参戦。
5. Electron / React Native の**実動アプリ**化（現状 docs のみ）。
6. VSCode で `.vue` を認識するには **Vue.volar 拡張**が必要
   （`.vscode/extensions.json` に登録済み、`code --install-extension Vue.volar`）。

## 11. 深掘りポインタ

- 全体像・学習コース: `README.md`
- できる/できない・LOC・ベンチ: `docs/comparison.md`
- 言語階層(TS↔JS): `docs/js-vs-ts.md`
- Electron/RN: `docs/platforms.md`
- リアクティビティ比較の罠→対策コード・結論: `docs/reactivity.md`
- 設計判断: `docs/decisions/0001-monorepo-tooling.md`, `0002-live-board-design.md`
