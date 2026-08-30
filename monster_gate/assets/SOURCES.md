# 素材の出典

1 行 1 素材。CC0 以外は入れない。生成物はツールとプロンプトも残す（`docs/style-guide.md` §8）。

`public/art/` の中身は `scripts/build_art.py` が元素材から生成する。手で編集しない:

```bash
# リポジトリルートから（workspace の venv に Pillow がある）
uv run --no-sync python monster_gate/scripts/build_art.py
```

## 元素材

| 置き場所 | 出典 | ライセンス | 備考 |
|---|---|---|---|
| `assets/src/kenney/miniature-dungeon/` | Kenney "Isometric Miniature Dungeon" https://kenney.nl/assets/isometric-miniature-dungeon | CC0 1.0 | **現在は未使用**。等角投影をやめて真上からの視点にした（2026-08-30）ため、このパックの絵は 1 枚も使っていない。プロップ用に再検討する余地はあるが、そのときも真上から見た絵が要る。zip は git 管理外 |

いま `public/art/` の中身は**すべてコードで描いている**。手で編集しない:

```bash
# リポジトリルートから（workspace の venv に Pillow がある）
uv run --no-sync python monster_gate/scripts/build_art.py     # タイル（6 城）
uv run --no-sync python monster_gate/scripts/build_heroes.py  # プレイヤー 3 職
uv run --no-sync python monster_gate/scripts/build_chars.py   # モンスター 8 体
uv run --no-sync python monster_gate/scripts/build_cards.py   # カードイラスト 24 種
```

## 城ごとのタイル（`public/art/<城 id>/`）

真上から見た 48×48 の正方タイル。6 城とも**同じ形を、城ごとのランプ**
（輝度 0..1 → 色）で塗り分けている（`scripts/build_art.py` の `THEMES`）。

| 城 | ランプ | 目地に混ぜる色 | 氷 |
|---|---|---|---|
| ゆかい（既定・接頭辞なし） | 灰×茶 | — | — |
| `light` | 白→金 | — | — |
| `vague` | 苔緑→灰緑 | — | — |
| `cold` | 紺→白 | — | 専用の高彩度シアンランプ |
| `cruel` | 紫 | 黄緑（酸） | — |
| `tight` | 黒 | 赤（溶岩） | — |

- 床は **1 マス 1 枚の石畳**、壁はレンガ。**壁は床よりはっきり暗くする** — 真上からは
  高さで区別できないので、明度差だけが手掛かりになる。
- 色付きの城でも**目地に混ぜるのは 34% まで**。原液を敷くと床が蛍光色の格子になる。
  原液はアクセント床の亀裂にだけ使う。
- ID は `<城 id>.tile.floor` のように城 id を接頭辞にする。無ければ接頭辞なしの既定セット
  （＝ゆかいの石）にフォールバックするので、城の絵は 1 つずつ足せる。
- `thumb.<城 id>` は同じタイルで組んだ 5×4 の部屋（拠点の城選択用、中心アンカー）。

## プレイヤー 3 職（`public/art/chars/class-*.png`）

`scripts/build_heroes.py` が **3 向き × 3 ポーズ = 9 枚 × 3 職 = 27 枚**を描く。
真上から見ると背中が見えるので横向き 1 枚では足りない。8 方向は 48px では
見分けがつかないので作っていない。

| 職 | 見た目 |
|---|---|
| `class.warrior` | 赤い前立ての兜・赤いサーコート・丸盾・幅広の剣（原作の初期職） |
| `class.mage` | とんがり帽子と紫のローブ・白ひげ・金の宝珠の杖 |
| `class.gambler` | つば広の黒帽と外套・骨のダガー |

ポーズは 無印=立ち / `.w`=踏み出し / `.a`=振り。振りでは武器を**横に薙ぐ**——
真上から見て刃をカメラ方向に突き出すと、ただの灰色の板にしか見えないため。

## モンスター（`public/art/chars/enemy-*.png`）

`scripts/build_chars.py` が**コードで描いている**（生成 AI ではない）。スタイルガイドの
「面塗り＋太い輪郭線＋影 1 段・光源は右上」はプログラムで再現できる種類の絵なので、
図形を組んで 512×512 に描き、接地点 (256, 440)・`scale` 0.15 で書き出している。
モンスターは横向き 1 枚のまま（描画側が左右反転する）。

| ID | 見た目 |
|---|---|
| `enemy.puunya_g` / `_y` | 緑と黄のスライム（黄は一回り大きく吊り目） |
| `enemy.killerbee` | 縞の腹・複眼・羽・針 |
| `enemy.skeleton` | 頭骨と肋骨・錆びた剣 |
| `enemy.kemunpa` | 節のある芋虫・大きな口と牙 |
| `enemy.goblin` | 緑肌・尖った耳・革の胴着・棍棒 |
| `enemy.mage` | 深いフードで顔が見えない・紫の宝珠 |
| `enemy.dragon` | 赤い竜・翼と角（ボスは描画側で 1.5 倍） |

**差し替え前提**。manifest は 1 スプライト 1 エントリなので、生成 AI や発注の PNG を
`public/art/chars/` に置いて manifest の該当行だけ書き換えれば、他に影響なく入れ替わる。
その場合は上のスクリプトを再実行しないこと（上書きされる）。

## カードイラスト（`public/art/cards/`）

キャラと同じくコードで描いている（`scripts/build_cards.py`）。256×256、アンカーは中心
(128, 128)、`scale` 1.0。枠・コスト・射程・名前・説明はプログラム側（`card-face.ts`）が
描くので、素材はイラストだけ。

```bash
uv run --no-sync python monster_gate/scripts/build_cards.py
```

26 枚のカードを 24 種のアイコンで賄う（`potion20/40/80` は色違いの同じ薬瓶、
`bronzeSword` / `longSword` は刃の色違い）。共通パーツは `flame` / `bolt` / `swirl`
（アルキメデス螺旋のリボン）/ `zed`（ブロック体の Z）/ `blade`。

| 系統 | ID | 見た目 |
|---|---|---|
| heal | `card.potion20/40/80` `card.regen` | 薬瓶（緑→青→紫）、鼓動するハート |
| fire | `card.fire` `card.multiFire` `card.meteor` | 炎、3 つの炎、尾を引く火球 |
| bolt | `card.thunder` `card.multiThunder` | 稲妻、雷雲と 3 本の稲妻 |
| status | `card.sleep` `card.panic` `card.multiPanic` | 閉じた目と Z、螺旋、3 重の螺旋 |
| scout | `card.bright` `card.search` `card.map` `card.warp` | ランタン、目、巻物、青い渦の門 |
| buff | `card.haste` `card.bronzeSword` `card.longSword` `card.powerShield` `card.powerUp` | 走る脚、剣（銅／鋼）、盾、上向き矢印 |
| special | `card.escape` `card.pocket2` `card.reviveRing` | 開いた扉、袋、宝石つき指輪 |
| summon | `card.summonGoblin` `card.summonDragon` | ゴブリンの顔、竜の顔 |

**48px で読めること**を採否の基準にした。初版で `sleep` が単なる菱形、`panic` が
`warp` と同じ同心円になって判別できなかったため、目＋ Z と螺旋リボンに描き直している。
キャラと同じく **差し替え前提**（manifest の 1 行を書き換えるだけ）。

## まだ無いもの

床に置くプロップ（樽・柱・骨）、松明の照明、攻撃／被弾ポーズ、ポートレート。
manifest に無い ID は絵文字で描画されるので、1 枚ずつ足していける。

プロップだけは絵が無いのではなく**置き場所が無い**。歩ける床に置くと通り抜けてしまうので、
engine 側に通行不可のマス（`FloorMap.props`）が要る。Phase 4 では見送った。
