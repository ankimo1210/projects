# ゲームエンジン／ライブラリ調査

「モンスターゲート風の 2D ターン制ローグライク」を作るのに使える基盤の調査。
調査日: 2026-08-30。

## 0. 結論

**このプロジェクトは素の Canvas 2D のままでよい。** 乗り換えるほどの利得が無い。

理由は「エンジンが埋めてくれる層」と「このリポジトリで既に埋まっている層」がほとんど
重なっているため。下の表の ✅ が自前で持っている部分。

| 層 | 代表的な提供元 | 本作の現状 |
|---|---|---|
| 乱数（シード固定） | rot.js, pure-rand | ✅ `src/engine/rng.ts` |
| ダンジョン生成 | rot.js | ✅ `src/engine/mapgen.ts`（部屋グリッド） |
| 視界 (FOV) | rot.js | ✅ `src/engine/fov.ts` |
| 経路探索 | rot.js | ✅ `src/engine/ai.ts` |
| ターン進行 | rot.js scheduler | ✅ `src/engine/turn.ts` |
| 描画・入力・カメラ | Phaser, Excalibur, Pixi | ⚠️ `src/ui/render/`（自前 Canvas 2D） |
| RPG システム（戦闘・所持品・セーブ） | **どれも提供しない** | ✅ `src/engine/`, `src/game/meta.ts` |

つまり乗り換えても得られるのは 1 行だけ（描画・入力・カメラ）で、その 1 行は
すでに動いていて 74KB / gzip 27KB に収まっている。

## 1. 各候補

### rot.js — ローグライク特化のアルゴリズム集
- FOV・経路探索・ダンジョン生成・スケジューラ・シード付き RNG。依存ゼロ。
- **README 自身が feature-complete と宣言**しており、最後のリリースは 2024-11 のメンテナンス版。
  止まっているのではなく「完成して落ち着いている」状態。
- 本作にとっては**まるごと重複**。ゼロから始めるなら第一候補だが、今から入れる理由は無い。

### Phaser（4 系）
- HTML5 で最大のコミュニティ。WebGL/Canvas 両対応、Pixi のカスタムビルドを内部で使う。
- シーン管理・入力・カメラ・タイルマップ・アニメーション・物理が一式入る。
- 代償はバンドルサイズと「Phaser の作法」への追従。ターン制には物理も補間も要らない。

### Excalibur.js
- **TypeScript ファースト**。actor/scene モデルが明快で、型と構造を重視する人向け。
- 本作の `strict` + `noUncheckedIndexedAccess` な書き方と相性は良い。
- ただし提供するのはやはり描画・入力・カメラの層。

### PixiJS（v8）
- 2D レンダラとして最速・最小。v8 は WebGPU 前提。エンジンではなく描画だけ。
- **将来ここに移るなら理由は 1 つ**: スプライトが数百枚に増えて Canvas 2D の
  `drawImage` 連打が重くなったとき。今は 1 フレーム数百枚に届いていない。

### melonJS
- Tiled マップエディタ連携が標準装備。タイルベースの見下ろし RPG に向く。
- **Tiled で手作りマップを描くなら**強い。本作は手続き生成なので恩恵が薄い。

### 使わない方がよいもの
- RPG システム層のライブラリ（`turn-based-combat-framework` は 2018-11 で更新停止、
  `Malwoden` は 2022-01 が最後）。この層は**毎回みんな書き直している**のが実情で、
  半端に古い依存を入れるより自前の方が安全。

## 2. 乗り換えるとしたらの判断基準

今の構成を捨てる価値があるのは、次のどれかが起きたとき。

1. **描画が重くなった** → PixiJS。engine は無傷で `src/ui/render/` だけ差し替えられる
   （`ArtBank` がスプライト解決を 1 箇所に閉じているので境界は既にある）。
2. **アニメーションのフレーム管理が破綻した** → Phaser か Excalibur のアニメーション機構。
   歩行 2 フレーム程度なら自前で足りるが、状態×方向×フレームが増えると管理コストが効いてくる。
3. **マップを手で描きたくなった** → melonJS + Tiled。
4. **モバイル配信** → Phaser（実績とドキュメントの量）。

## 3. 本作の立ち位置

engine（`src/engine/`）は DOM にもキャンバスにも依存しない純粋な TypeScript で、
94 件のテストが Node 上で走る。**この分離があるかぎり、描画基盤の選択はいつでもやり直せる。**
逆に言えば、今エンジンを選ぶ意思決定を急ぐ必要がない。

## 参考資料

- [rot.js（GitHub）](https://github.com/ondras/rot.js/) / [ホームページ](https://ondras.github.io/rot.js/hp/)
- [JavaScript roguelike development in 2026（Paul's Programming Notes）](https://www.paulsprogrammingnotes.com/2026/08/javascript-roguelike-development.html)
- [11 Best Web Game Engines for 2026（Cinevva）](https://app.cinevva.com/guides/web-game-engines-comparison)
- [Top JavaScript Game Engines & Libraries 2026（codersera）](https://codersera.com/blog/top-javascript-game-engines-and-libraries/)
- [js-game-rendering-benchmark（描画性能の比較）](https://github.com/Shirajuki/js-game-rendering-benchmark)
- [Building a roguelike game with Rot.js（LogRocket）](https://blog.logrocket.com/building-a-roguelike-game-with-rot-js/)
