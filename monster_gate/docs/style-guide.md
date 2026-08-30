# スタイルガイド — キャラ・カード・ダンジョン

`docs/plan-design.md` §3 の具体化。素材を作る人（生成 AI に指示する人）とコードの両方がこれに従う。

## 1. 世界観とトーン

- 城の地下に潜って WIN を持ち帰るアーケード的ローグライク。緊張感より **軽快さ**。
- コミカルで色鮮やか、少しレトロなファンタジー。キーワード: トゥーン・ジオラマ、おもちゃ箱、ボードゲームの駒。

## 2. スタイル規定

- 面塗り＋太めの輪郭線（暗色 `#1a1420`、外側 2px @1x）。影は 1 段（ベース色の 70% 明度）、ハイライト 1 段。
- ドット絵にしない。グラデーションは最小限、テクスチャは使わない（細部は線で表す）。
- **光源は画面右上。** キャラの落ち影は左下。壁は左側面が暗い（コードのシェーディング 0.48 / 0.7 と一致）。
- 頭身 2.5。ボスは同じ絵を 1.5 倍で使う。
- **左向き（画面左下方向）で描く。** 右向きはプログラムが反転する。左右非対称の持ち物（盾・杖）は左手側に。
- キャラ・アイテムは彩度高め。床・壁は彩度低めにして、その上に立つものが浮くようにする。

## 3. パレット

共通アクセント: HP `#2ecc40` / MP `#3b7ddd` / WIN・金 `#ffd85a` / 危険 `#e64a4a` / 召喚 `#44ccff` / 輪郭 `#1a1420`

| 城 | 印象 | 床 | 壁 | アクセント |
|---|---|---|---|---|
| ゆかい | 石の地下城 | `#8a8a80` | `#5a5a6c` | 松明の橙 `#ff9a3c` |
| LIGHT | 白い大聖堂 | `#d9d3c4` | `#bfb8a8` | 金 `#ffd85a` |
| VAGUE | 苔むした遺跡 | `#6f7d63` | `#4a5548` | 霧 `#aab7ad` |
| COLD | 氷の洞窟 | `#8fc4d8` | `#5a7c94` | 白 `#eaffff` |
| CRUEL | 腐食した工房 | `#5f5a6e` | `#4a3d5c` | 酸 `#b5ff5a` |
| TIGHT | 竜の巣 | `#3a2a2a` | `#2a1a1a` | 赤 `#ff4a3c` |

> 現在のキャラはこの規定に沿って `scripts/build_chars.py` が**コードで描いている**。
> 生成 AI や発注の絵に差し替えるときも、以下の寸法・接地点・向きの規約を守れば
> manifest の 1 行を書き換えるだけで入れ替わる（`assets/SOURCES.md`）。

## 4. 素材の仕様

画面の 1 マスは **48×48px の正方形**（真上から）。以下の「画面上の大きさ」はこの基準。

### キャラ（職業・モンスター）

- 元画像: 透過 PNG、**512×512**、キャラは中央、**接地点を (256, 440)** に揃える。余白は残してよい（manifest の `scale` で合わせる）。
- 画面上: 高さ 55〜70px（1.2〜1.4 マス、2.5 頭身）。`scale` はプレイヤー 0.175 / モンスター 0.15。
  **1 マスより少し高い**のが要点で、マスに収めると床の模様に埋もれる。
- 接地点はマスの中心ではなくやや下（`FOOT` = マスの 34%）。上のマスに体が重なることで、
  グリッドが「地面」に見える。真ん中に置くと方眼紙に見える。
- ID: `class.warrior` `class.mage` `class.gambler` /
  `enemy.puunya_g` `enemy.puunya_y` `enemy.killerbee` `enemy.skeleton` `enemy.kemunpa` `enemy.goblin` `enemy.mage` `enemy.dragon`。
- 向き・ポーズは §「向きとポーズ」を参照。描画側は
  `<id>.<向き><ポーズ>` → `<id>.<向き>` → `<id>` の順に引くので、**1 枚しか無い素材もそのまま動く**。
- ポートレート: `portrait.warrior` など。512×512、胸から上（上部バー・拠点・リザルト用）。**未実装**。

### アイテム・施設

- `item.card` `item.win` `item.doubleUp`、`tile.altar` `tile.shop` `tile.casino`: **いずれも未実装**で、
  現状は絵文字のビルボードにフォールバックしている。作るなら 256×256・接地点 (128, 220)、
  画面上の幅 ≈ 30px。
- `tile.altar` `tile.shop` `tile.casino`: 512×512、接地点 (256, 440)。画面上の幅 ≤ 90px。

### タイル

**視点は真上からのグリッド**（`src/ui/render/grid.ts`）。原作が下敷きにした不思議の
ダンジョン系と同じで、斜め上から見た等角投影はやめた。奥行きが無いので**何も何かを
隠さない** — 等角時代にあった遮蔽と透過表示の仕組みはまるごと不要になった。

- 1 マス 48×48 の正方形。書き出しは 2 倍の 96×96、アンカーは中心。
- 床は **1 マス 1 枚の石畳**。1 マスを 4 分割すると壁のレンガと同じ肌理になって
  床と壁が混ざるうえ、マス目が数えられなくなる（ローグライクでは致命的）。
- 壁は床よりはっきり暗く、レンガ目地と天面のハイライトで「質量」に見せる。
  床と壁の明度が近いと真上からでは区別がつかない。
- ID: `tile.floor` `tile.floor.b` `tile.wall` `tile.ice` `tile.door.ns` `tile.door.ew` `tile.stairs`。
- **城別は `<城 id>.` を頭に付ける**（`cold.tile.floor`）。描画側は「その城の ID → 接頭辞なし」の
  順で引くので、絵の無い城は既定（ゆかいの石）で出る。
- アクセント床 `tile.floor.b` は 12 マスに 1 枚。
- `thumb.<城 id>`: 拠点の城選択に出す 5×4 の部屋。**本編と同じタイルで組む**（色見本にしない）。

### 城の空気（パーティクル）

`src/ui/render/weather.ts` に城ごとに 1 レイヤー、最大 60 粒。位置は時刻と番号だけの
純関数なので状態を持たず、フレームが飛んでも跳ばない。半径が数 px を超える粒（霧）は
必ず放射グラデーションにする — 単色の円は黒背景でくっきりした円盤に見えてしまう。

| 城 | 粒 |
|---|---|
| ゆかい | 松明の火の粉（橙・上昇・加算） |
| LIGHT | 埃（暖白・ゆっくり落ちる） |
| VAGUE | 霧（大きく薄い・横流れ） |
| COLD | 雪（白・落ちる） |
| CRUEL | 酸の泡（黄緑・上昇・加算） |
| TIGHT | 火の粉（赤・速く上昇・加算） |

### カード

- 枠・帯・コスト・射程・名前・説明は **すべてプログラムが描く**（`src/ui/render/card-face.ts`）。
  素材として要るのは **イラスト 1 枚だけ**。
- イラストは **256×256、アンカーは中心 (128, 128)、`scale` 1.0**。カード面の
  イラスト枠（幅の約 0.42 倍の正方領域）にクリップして中央に置かれるので、
  余白を詰めて縁ぎりぎりまで描かない。背景は透過。
- ID は `card.<CardId>`（例 `card.fire`, `card.summonDragon`）。無い ID は絵文字にフォールバックする。
- 色は枠が受け持つ。イラストは**シルエットで判別できる**ことを優先し、枠色と同系色で塗り潰さない
  （紫枠の状態異常なら白系、赤枠の炎なら橙〜黄など）。
- カード面は 44px（手札）〜150px（拡大）まで同じ関数で描かれる。**48px で読めるか**が採否の基準。

#### ファミリーとレアリティ

`src/engine/cards.ts` の `family` / `rarity` が枠色と装飾を決める（データはここだけ）。

| family | 枠 | パネル | 例 |
|---|---|---|---|
| `heal` | 緑 `#3fae5a` | `#1e5636` | ポーション、リジェネ |
| `fire` | 赤 `#d8433a` | `#5f2222` | ファイア、メテオ |
| `bolt` | 黄 `#e0b13a` | `#5f4c1c` | サンダー |
| `status` | 紫 `#8a5bd0` | `#3a2661` | スリープ、パニック |
| `scout` | 青 `#3b7ddd` | `#1c3a6b` | マップ、サーチ、ワープ |
| `buff` | 橙 `#e08a34` | `#5e3a16` | ヘイスト、武器、盾 |
| `special` | 銀 `#b9c0cf` | `#3f4452` | エスケープ、リバイブリング |
| `summon` | 濃紺 `#3a3550` | `#191626` | 召喚ゴブリン／ドラゴン |

レアリティは `common` = 装飾なし、`rare` = 内側に白線、`epic` = 金線＋四隅の三角。

射程は文字ではなく **図形**（`self` = 点、`dir` = 三角、`none` = 輪）。8px の漢字は読めないため。

## 5. ファイル配置と manifest

```
public/art/manifest.json   読み込み定義（下記）
public/art/**/*.png        配信する画像（後処理済み）
assets/src/**              元素材（生成物・パックの原本）
assets/SOURCES.md          出典・ライセンス・プロンプト
```

```json
{
  "version": 1,
  "sprites": {
    "class.warrior": { "src": "class.warrior.png", "ax": 256, "ay": 440, "scale": 0.17 },
    "tile.floor": { "src": "yukai/floor.png", "ax": 48, "ay": 24 }
  }
}
```

- `ax, ay` = 元画像の中で「描画位置に置く点」（接地点）。`scale` = 元画像 → 画面の倍率（省略時 1）。
- manifest に無い ID は絵文字で描かれる。**1 枚ずつ足してよい。**

## 6. 生成 AI のプロンプト雛形

共通（英語で）:

```
cute toon fantasy game sprite, 2.5-head chibi proportion, thick dark outline,
flat cel shading with one shadow step, high saturation, light from upper right,
facing left, full body, standing idle pose, centered, plain white background,
no text, no watermark
```

- 最初に **参照シート**（戦士・魔法使い・ギャンブラーの 3 人並び）を 1 枚作り、以後は同じ参照画像＋同じ雛形で固定する。
- 各キャラの追加語:
  - 戦士: `knight with a large round shield and short sword, red and steel armor`
  - 魔法使い: `wizard with a tall pointed hat and long staff, purple and gold robe`
  - ギャンブラー: `gambler in a black cloak and hat, holding dice and a gold coin, sly grin`
  - プーニャ(緑): `round green slime with big friendly eyes` / (黄): `round yellow slime with sharp eyes, slightly larger`
  - キラービー: `giant bee with striped body and stinger, wings spread`
  - スケルトン: `skeleton warrior with a rusty sword, empty eye sockets`
  - ケムンパ: `fat caterpillar monster with a wide mouth, spits poison needles`
  - ゴブリン: `goblin with a wooden club and leather armor, green skin`
  - 魔道士: `hooded dark mage, face hidden in shadow, holding a purple orb`
  - ドラゴン: `small red dragon with wings, breathing a fireball`
- NG: リアル調、細い線、ドット絵、背景付き、複数体、テキスト入り。

## 7. 後処理チェックリスト

1. 背景除去（rembg 等）。縁に白が残っていないか確認
2. 512×512 に収め、接地点を (256, 440) へ
3. 輪郭線が 2px 相当になるよう補正（Phase 1 でスクリプト化）
4. パレット量子化（32〜48 色）で他の絵と馴染ませる
5. manifest に登録し、ゲーム内で影・足元リングとの位置を確認
6. `assets/SOURCES.md` に記録

## 8. 出典の記録

`assets/SOURCES.md` に 1 行 1 素材。CC0 以外は入れない。生成物はツールとプロンプトも残す。
