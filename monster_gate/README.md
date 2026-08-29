# monster_gate

コナミ『モンスターゲート』(2001) 風のローグライク。使い切りカード 10 枚 + MP 経済 + 1 ダンジョン。
Web (TypeScript + Vite + Canvas 2D)、フレームワークなし。

## Docs

- `docs/research-original-game.md` — 元ネタ調査
- `docs/plan-mvp.md` — MVP 計画とフェーズ
- `docs/spec-mvp.md` — 詳細仕様（型・数値・テスト観点）
- `docs/plan-design.md` — キャラ・カード・ダンジョンのデザイン計画（アート方針・素材パイプライン・フェーズ）
- `docs/style-guide.md` — 素材のスタイル規定・寸法・manifest 形式・生成 AI のプロンプト雛形
- `assets/SOURCES.md` — 素材の出典とライセンス台帳（`public/art/` に置くものはここに記録）

## Run

```bash
npx --yes pnpm@11.1.0 install
npx --yes pnpm@11.1.0 dev        # http://localhost:5173
npx --yes pnpm@11.1.0 test       # vitest
npx --yes pnpm@11.1.0 typecheck
npx --yes pnpm@11.1.0 lint
```

## Status (2026-08-29)

職業 3 種（戦士・魔法使い・ギャンブラー）、ダンジョン 6 つ（城ごとの特殊ルール: 明るい通路 / 眠る敵 / 氷 / 酸の床 / 手札制限+暗闇）、
カード 37 種（召喚・装備・ダブルアップ含む）、階段を守るボス、ダンジョン内ショップとカジノ、MP 経済、
拠点（倉庫 / 持ち込み / ショップ / localStorage 保存）。`pnpm test` 91 件緑（バランス用シミュレーション含む）。

操作: 矢印 / `qezc`（斜め）/ テンキー移動、`.` 待機、`1`〜`0` カード、`d`+番号で捨てる、Enter で階段・祭壇、Esc 取消。
拠点では ←→ でダンジョン選択、`c` で職業変更、Tab で倉庫/ショップ切替。
ショップ・カジノのマスに乗るとパネルが開く（1-3 で購入 / Space で回す、Esc で閉じる）。

## Layout

- `src/engine/` — 純粋・決定的なゲームロジック（DOM 非依存）。`step(state, action)` が唯一の状態遷移。`bot.ts` / `sim.ts` はバランス計測用。
- `src/game/` — 拠点・セーブ（localStorage）。
- `src/ui/` — Canvas 描画と入力。
- `tests/` — vitest。
