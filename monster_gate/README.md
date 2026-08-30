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
- `docs/research-engines.md` — エンジン／ライブラリ調査（結論: 素の Canvas 2D のまま）

## Run

```bash
npx --yes pnpm@11.1.0 install
npx --yes pnpm@11.1.0 dev        # http://localhost:5173
npx --yes pnpm@11.1.0 test       # vitest
npx --yes pnpm@11.1.0 typecheck
npx --yes pnpm@11.1.0 lint
```

## Status (2026-08-30)

職業 3 種（戦士・魔法使い・ギャンブラー）、ダンジョン 6 つ（城ごとの特殊ルール: 明るい通路 / 眠る敵 / 氷 / 酸の床 / 手札制限+暗闇）、
カード 26 種（召喚・装備・ダブルアップ含む）、階段を守るボス、ダンジョン内ショップとカジノ、MP 経済、
拠点（倉庫 / 持ち込み / ショップ / localStorage 保存）。`pnpm test` 94 件緑（バランス用シミュレーション含む）。

**見た目は真上から見た正方グリッド**（1 マス 48px、不思議のダンジョン系と同じ）。
6 城はそれぞれ専用のタイルと環境パーティクルを持ち、カードは系統 8 色 × レア 3 段で描き分ける。
`public/art/` の絵はすべて `scripts/` の Python が生成する（手で編集しない）。

### 操作

ダンジョン:

| | |
|---|---|
| 移動 | 矢印 / `qezc`（斜め）/ テンキー（敵に歩き込んでも攻撃） |
| 攻撃 | `Space` または `A`、画面右下のボタン（向いている方向。空振りでもターンを使う） |
| 待機 | `.` |
| カード | `1`〜`0` で使用、`d`+番号で捨てる（MP が戻る） |
| 階段・祭壇 | `Enter` |
| ヘルプ / 取消 | `?` / `Esc` |

拠点: 矢印で倉庫のカードを選び `Space` で持ち込み、`s` で売却、`[` `]` でダンジョン選択、
`c` で職業変更、`Tab` で倉庫/ショップ切替、`Enter` で出発・購入。
ショップ・カジノのマスに乗るとパネルが開く（1-3 で購入 / Space で回す、Esc で閉じる）。

## Art

```bash
# リポジトリルート（projects/）から。workspace の venv に Pillow がある
uv run --no-sync python monster_gate/scripts/build_art.py     # 6 城のタイル
uv run --no-sync python monster_gate/scripts/build_heroes.py  # プレイヤー 3 職（3 向き × 3 ポーズ）
uv run --no-sync python monster_gate/scripts/build_chars.py   # モンスター 8 体
uv run --no-sync python monster_gate/scripts/build_cards.py   # カードイラスト 24 種
```

manifest に無い ID は絵文字で描かれるので、**素材ゼロでもゲームは動く**。
1 スプライト 1 エントリなので 1 枚ずつ差し替えられる（`assets/SOURCES.md`）。

## Layout

- `src/engine/` — 純粋・決定的なゲームロジック（DOM 非依存）。`step(state, action)` が唯一の状態遷移。`bot.ts` / `sim.ts` はバランス計測用。
- `src/game/` — 拠点・セーブ（localStorage）。
- `src/ui/` — Canvas 描画と入力。
- `tests/` — vitest。
