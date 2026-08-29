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
| `assets/src/kenney/miniature-dungeon/` | Kenney "Isometric Miniature Dungeon"（Dungeon Pack 2.3, 2019-02-15）https://kenney.nl/assets/isometric-miniature-dungeon | CC0 1.0 | 288 タイル（4 方位）＋ 8 方向キャラ。256×512 の共通キャンバス、真の 2:1 等角、地面菱形は 256×128 で中心 (128, 448)。zip 14.2MB は git 管理外（`assets/src/**/*.zip`） |

## 生成スプライト（`public/art/`）

| ID | ファイル | 元 | 加工 |
|---|---|---|---|
| `tile.floor` | `yukai/floor.png` | `Isometric/stone_N.png` | 2x 書き出し＋余白トリム |
| `tile.floor.b` | `yukai/floor.b.png` | `Isometric/dirt_N.png` | 同上。12 マスに 1 枚の割合で混ぜる |
| `tile.wall` | `yukai/wall.png` | `stoneWallCorner_E` + `stoneWallCorner_W` + `stone`(-92px) | パックに 1 マス丸ごとの壁が無いため、辺に載る 2 つのコーナー壁で四方を閉じ、床タイルで天面を塞いだ合成 |
| `tile.stairs` | `yukai/stairs.png` | `Isometric/stairsSpiral_N.png` | 2x 書き出し |
| `tile.door.ns` / `.ew` | `yukai/door.ns.png` / `door.ew.png` | `stoneWallArchway_N` / `_E` | 通路の向きで描画側が選ぶ |

## キャラ（`public/art/chars/`）

`scripts/build_chars.py` が**コードで描いている**（生成 AI ではない）。スタイルガイドの
「面塗り＋太い輪郭線＋影 1 段・光源は右上」はプログラムで再現できる種類の絵なので、
図形を組んで 512×512 に描き、接地点 (256, 440)・`scale` 0.21 で書き出している。

```bash
uv run --no-sync python monster_gate/scripts/build_chars.py
```

| ID | 見た目 |
|---|---|
| `class.warrior` | 赤い上衣・鉄兜に赤い前立て・丸盾・短剣 |
| `class.mage` | とんがり帽子と紫のローブ・白ひげ・金の宝珠の杖 |
| `class.gambler` | 黒いつば広帽と外套・金貨・サイコロ |
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

ゆかい以外の 5 城のタイル、攻撃／被弾ポーズ、ポートレート。manifest に無い ID は
絵文字で描画されるので、1 枚ずつ足していける。
