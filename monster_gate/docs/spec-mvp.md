# MVP 詳細仕様

`plan-mvp.md` のフェーズ 1〜5 を実装できる粒度まで落としたもの。数値はすべて「初期値」で、フェーズ 6 の調整対象。
出典を持つ数値（敵 HP、WIN など）は `research-original-game.md` 準拠、それ以外は本書で仮置きした値。

---

## 0. 用語と単位

- **マス (cell)**: 整数座標 `{x, y}`。原点は左上。8 方向移動。
- **ターン**: プレイヤーが 1 行動を確定 → 全敵が 1 回ずつ行動 → ターン終了処理（リジェネ等）。
- **HP / MP / ATK / DEF**: すべて整数。
- **WIN**: 拠点で使う通貨（ダンジョン外）。**MP**: ダンジョン内でカードを撃つ資源。

---

## 1. 型定義（`src/engine/types.ts`）

```ts
type Vec = { x: number; y: number };
type Dir = 0|1|2|3|4|5|6|7;           // N, NE, E, SE, S, SW, W, NW

type TileKind = "wall" | "floor" | "door" | "stairsDown" | "altar";
type Tile = { kind: TileKind; roomId: number | -1; lit: boolean };

type Room = { id: number; x: number; y: number; w: number; h: number };  // 内側の床領域

type FloorMap = {
  width: number; height: number;
  tiles: Tile[];                        // row-major
  rooms: Room[];
  entrance: Vec; stairs: Vec | null;    // 最下層は stairs=null, altar あり
};

type PlayerStats = { hp: number; maxHp: number; mp: number; maxMp: number; atk: number; def: number };

type Player = PlayerStats & {
  pos: Vec;
  hand: CardId[];                       // 最大 handSize
  handSize: number;                     // 通常 10
  kills: Record<EnemyKind, number>;     // 成長上限判定用
  status: StatusEffects;
  equipment: { weaponBonus: number };   // ブロンズソードなど（そのダンジョン中のみ）
  visitedRooms: Set<number>;            // MP/HP 回復判定用（floor ごとにリセット）
};

type StatusEffects = { haste: number; sleep: number; regen: number };  // 残りターン

type Enemy = {
  id: number; kind: EnemyKind; pos: Vec;
  hp: number; maxHp: number; atk: number; def: number;
  awake: boolean;                       // 入室で起動
  lastSeen: Vec | null;                 // 見失ったときの目標
  status: { sleep: number };
  ranged: boolean;
};

type CardItem = { id: number; card: CardId; pos: Vec };

type DungeonState = {
  seed: number; rng: RngState;
  floorNo: number;                      // 1..N
  map: FloorMap;
  player: Player;
  enemies: Enemy[];
  items: CardItem[];
  turn: number;
  turnsOnFloor: number;                 // 追加湧き判定用
  winCollected: number;                 // 拾った WIN
  result: null | "clear" | "dead" | "escaped";
};

type Action =
  | { type: "move"; dir: Dir }
  | { type: "attack"; dir: Dir }
  | { type: "wait" }                    // 空振り
  | { type: "useCard"; index: number; target?: Vec | Dir }
  | { type: "discardCard"; index: number }
  | { type: "descend" }                 // 階段の上で
  | { type: "takeAltar" };              // 祭壇の上で

type Event =
  | { t: "moved"; from: Vec; to: Vec }
  | { t: "attack"; by: "player" | number; target: "player" | number; dmg: number; crit: boolean }
  | { t: "died"; enemyId: number; kind: EnemyKind }
  | { t: "grow"; atk: number; def: number; hp: number }
  | { t: "pickup"; card: CardId } | { t: "pickupWin"; amount: number }
  | { t: "handFull"; card: CardId }
  | { t: "cardUsed"; card: CardId; mpCost: number } | { t: "notEnoughMp"; card: CardId }
  | { t: "discarded"; card: CardId; mpBack: number }
  | { t: "roomEntered"; roomId: number; hpGain: number; mpGain: number }
  | { t: "floorChanged"; floorNo: number }
  | { t: "playerDied" } | { t: "cleared"; win: number } | { t: "escaped" }
  | { t: "log"; msg: string };

function step(state: DungeonState, action: Action): { state: DungeonState; events: Event[] };
```

`step` は入力 state を変更せず新しい state を返す（structural sharing でよい、immer は使わない）。

---

## 2. マップ生成（`mapgen.ts`）

方式: **部屋グリッド + 短い通路**（元ネタ準拠。BSP は使わない）。
通路は両部屋の向かい合う壁に置いたドア同士を結ぶ（中心同士を結ぶと壁沿いにドアが並ぶ不具合が出たため）。セル内で部屋の右/下に壁 2 マス以上残し、通路が曲がる列/行を確保する。

パラメータ（フロア定義から受け取る）:

| 名前 | 「ゆかい」の値 | 意味 |
|---|---|---|
| `cols × rows` | 3 × 3 | 部屋グリッドのセル数 |
| `cellW × cellH` | 14 × 10 | 1 セルの外寸（マス） |
| `roomMin / roomMax` | 4 / 9（幅）, 3 / 6（高さ） | 部屋内側サイズ |
| `roomChance` | 0.85 | セルに部屋を置く確率（外れたセルは通路交差点だけ） |
| `extraLinks` | 2 | 全域木に足すループ本数 |

手順:
1. 各セルに `roomChance` で部屋を置く。置かない場合は 1×1 の「交差点」を置く（通路として扱う）。
2. 隣接セル同士を辺として全域木（ランダム Kruskal）を作り、`extraLinks` 本ランダムに追加。
3. 辺ごとに通路を掘る: 両部屋の辺上に `door` を 1 つずつ置き、L 字（水平→垂直）で `floor(roomId=-1)` を掘る。
4. 入口 `entrance` はランダムな部屋、`stairs` は入口と **異なる部屋**（最下層は `altar`）。
5. 全 floor/door から入口へ BFS で到達可能であることを検証。失敗したら seed を +1 して再生成（上限 20 回）。

`lit`: 部屋内は true、通路/交差点は false。

---

## 3. 視界（`fov.ts`）

- プレイヤーが **部屋内**: その部屋の全マス + 部屋の壁に接する door が見える。
- プレイヤーが **通路**: 隣接 8 マスのみ。
- `bright` 状態（ブライト使用中）: そのフロアの全マスが見える（フロア移動で解除）。
- 敵の「視認」もこの関数で判定（対称とみなす）。
- 一度見たマスは `explored` として記憶し、UI では暗く描画（敵・カードは記憶しない）。

---

## 4. ターン処理（`turn.ts`）

```
step(state, action):
  1. validate(action)            // 壁・範囲外・MP 不足なら events に理由を入れて state はそのまま返す（ターン消費なし）
  2. applyPlayerAction(action)   // 移動/攻撃/カード/待機
  3. if haste>0 and action consumed a turn: haste-- ; return（敵は動かない）  ← ヘイスト中は 2 行動に 1 回だけ敵が動く
  4. for each enemy (id 昇順): enemyAct(enemy)
  5. endOfTurn: regen, sleep カウンタ減, turnsOnFloor++, spawn 判定
  6. resolve: 死亡なら result="dead"
```

移動:
- 移動先が `floor/door/stairs/altar` で、敵がいなければ移動。敵がいれば **攻撃に変換**。
- 斜め移動は角抜け禁止（`dir` の両直交成分が壁なら不可）。
- 移動後、そのマスにカードがあれば拾う（手札が満杯なら `handFull` を出して床に残す）。
- 初めて入る部屋: `hp += 5`（maxHp 上限）, `mp += 10`（maxMp 上限）, `roomEntered`。

---

## 4.5 職業（`CLASSES`, `dungeon-def.ts`）

3 職。原作の初代と同じ顔ぶれ。数値はシミュレータで調整。

| | 戦士 | 魔法使い | ギャンブラー |
|---|---|---|---|
| HP / MP(最大) | 30 / 30(100) | 24 / 40(120) | 24 / 30(100) |
| ATK / DEF | 8 / 1 | 6 / 1 | 7 / 0 |
| 会心率 | 5% | 5% | 8% |
| 通路の視界 | 1 | **2** | 1 |
| 攻撃カード | ×1.0 | **×1.5** | ×1.0 |
| ポーション | ×1.0 | **×1.25** | ×1.0 |
| その他 | – | – | 宝/ダブルアップ/ゴールがミニマップに映る、レアカード出現 ×3、ダブルアップ出現 ×2、カジノが有利 |

ボットでの「ゆかい」クリア率: 戦士 44% / 魔法使い 44% / ギャンブラー 31%
（ギャンブラーの取り分＝配当と引き＝はクリア率に出ない）。

## 5. 戦闘・成長（`combat.ts`）

**近接ダメージ**
```
base = atk - def
dmg  = max(1, base + rngInt(-1, 1))
crit = rng() < 0.05 → dmg *= 2         // 戦士の会心率
```
プレイヤー atk には `equipment.weaponBonus` を加算。

**射撃（敵）**: 直線 8 方向上、距離 `d` (1..6)、間に壁/他敵がなければ `dmg = max(1, floor((atk - def) / d))`。

**召喚モンスター（`ally.ts`）**: 手札のモンスターカードで隣に出現、最大 2 体。プレイヤーを追い、見えた敵に向かい、
隣接した敵を殴る。歩いてぶつかると**入れ替わる**（滑走はしない）。敵はプレイヤーが隣にいないとき召喚モンスターを殴る。
召喚モンスターが倒した敵の XP は入らない。階段を降りるとはぐれる（消える）。

**成長（敵撃破時）— 隠しレベル方式**（実装時に per-kill 方式から変更。per-kill は ATK が 1 フロアで +4 伸びて調整不能だった）
```
if player.level > ENEMY[kind].trivialAt: XP なし（雑魚は無益）
xp += ENEMY[kind].xp
while xp >= xpToNext(level):  xp -= xpToNext(level); level++
  maxHp += 3（毎レベル）; atk += 1（level % 2 == 0）; def += 1（level % 5 == 0）
xpToNext(level) = 3 + floor(level / 2)
```
`LEVELING` テーブル（`dungeon-def.ts`）で全て調整可能。

**初期値（戦士）**: HP 30 / MP 30 (max 100) / ATK 8 / DEF 1 / Lv1 / handSize 10。

---

## 6. 敵（`dungeon-def.ts` の `ENEMY` テーブル）

「ゆかい」に出す 8 種。HP は元ネタ、それ以外はシミュレータで調整済み（2026-08-29）。

| kind | HP | ATK | DEF | 射撃 | XP | trivialAt(Lv) |
|---|---|---|---|---|---|---|
| puunya_g | 9 | 5 | 0 | – | 3 | 8 |
| puunya_y | 10 | 6 | 0 | – | 3 | 10 |
| killerbee | 11 | 7 | 1 | – | 4 | 12 |
| skeleton | 14 | 9 | 2 | – | 5 | 15 |
| kemunpa | 17 | 10 | 2 | ○ | 6 | 18 |
| goblin | 21 | 13 | 3 | – | 7 | 22 |
| mage | 26 | 15 | 2 | ○ | 9 | 26 |
| dragon | 67 | 18 | 8 | ○ | 23 | 40 |

**敵 AI（`ai.ts`）** — 毎ターン 1 行動:
```
if sleep>0: sleep--; return
if !awake: return                            // 入室で awake=true にする（その部屋の敵全部）
if canSee(player):
   lastSeen = player.pos
   if ranged and onLine(player) and dist<=6 and clearLine: shoot
   elif adjacent: attack
   else: stepToward(player.pos)              // 距離が縮まる 8 方向のうち最良、埋まってれば斜めの代替、なければ待機
elif lastSeen: stepToward(lastSeen); if pos==lastSeen: lastSeen=null
else: wander                                 // 現在の部屋内をランダム、通路にいるなら隣接部屋へ
```
`stepToward` はチェビシェフ距離を減らす方向のみ（近づかない移動はしない）。

**追加湧き**: `turnsOnFloor` が 40 を超えると 15 ターンごとにそのフロアの敵テーブルから 1 体、プレイヤーの視界外の部屋に `awake=true` で出現。1 フロア最大 6 体。

---

## 7. カード（`cards.ts`）

`hand` 上限 10。使用で消滅。**MP 不足なら使えない**（ターン消費なし）。
捨てる（`discardCard`）と `mpCost` と同量の MP を回収（maxMp 上限、ターン消費なし）。

| id | 名前 | MP | 対象 | 効果 |
|---|---|---|---|---|
| potion20 | ポーション20 | 2 | 自分 | HP +20 |
| potion40 | ポーション40 | 4 | 自分 | HP +40 |
| potion80 | ポーション80 | 8 | 自分 | HP +80 |
| fire | ファイア | 3 | 方向 | 直線射程 5 の最初の敵に 15（防御無視） |
| multiFire | マルチファイア | 6 | なし | 視界内の全敵に 15 |
| thunder | サンダー | 6 | 方向 | 直線射程 5 の最初の敵に 30 |
| sleep | スリープ | 3 | 方向 | 直線射程 5 の最初の敵を 8 ターン睡眠 |
| haste | ヘイスト | 4 | 自分 | 4 ターン、2 行動に 1 回だけ敵が動く |
| bright | ブライト | 3 | 自分 | このフロアの間、全マス可視 |
| warp | ワープ | 2 | 自分 | 同フロアのランダムな床マスへ |
| escape | エスケープ | 5 | 自分 | 手札・拾った WIN を持ってダンジョン脱出（result="escaped"、WIN は全額） |
| bronzeSword | ブロンズソード | 5 | 自分 | このダンジョン中 weaponBonus +4（ロングソードより弱ければ無視） |
| multiThunder | マルチサンダー | 12 | なし | 視界内の全敵に 30 |
| meteor | メテオ | 10 | 方向 | 直線射程 5 の最初の敵に 60 |
| panic | パニック | 3 | 方向 | 6 ターン混乱（ランダムに歩き回り攻撃しない） |
| multiPanic | マルチパニック | 6 | なし | 視界内の全敵を 6 ターン混乱 |
| search | サーチ | 3 | 自分 | このフロアの敵の位置がマップに出る |
| map | マップ | 3 | 自分 | このフロアの地形とカードが全て見える（DARK でも有効） |
| regen | リジェネ | 3 | 自分 | 100 ターン毎ターン HP+1 |
| longSword | ロングソード | 8 | 自分 | weaponBonus +8 |
| powerShield | パワーシールド | 6 | 自分 | shieldBonus +4（DEF に加算） |
| pocket2 | ポケット+2 | 4 | 自分 | 手札上限 +2（1 回のみ） |
| reviveRing | リバイブリング | 6 | 自分 | 死亡時に 1 度だけ HP 半分で復活 |
| powerUp | パワーアップ | 12 | 自分 | レベル +10（通常レベルアップと同じ上昇）+ HP 10 |

**ボスのドロップ**（`BOSS_DROPS`）: meteor / multiThunder / multiPanic / longSword / powerShield / reviveRing / pocket2 / potion80 / regen / powerUp から重み付き 1 枚、必ず落とす。

**カードの出現**: フロアごとに `cardDrops`（枚数）と重み表。WIN も床に落ちる（`winDrops`、1 個 3〜8 枚）。

---

## 8. ダンジョン定義（`dungeon-def.ts`）

### 8.0 城ルール（`DungeonRules`）とボス

| ルール | 効果 |
|---|---|
| `litCorridors` | 通路での視界が半径 3（敵の視認も同じ）。飛び道具持ちが通路で撃ってくる |
| `dormantEnemies` | 敵は `dormant`: 入室や視認では起きず、隣接するか攻撃されたときだけ起きる |
| `acidFloor` | 通路のマスへ移動するたび HP-1（部屋は安全） |
| `enemyCrit` | 敵の近接攻撃に会心率（ダメージ 2 倍） |
| `playerCrit` | プレイヤーの会心率を上書き（既定 5%） |
| `dark` | 画面には今見えているマスしか出ない（エンジン側の記憶は保持、`knownTiles()` で描画用に絞る）。マップカードで解除 |
| 氷（`MapGenParams.ice`） | 部屋の中に矩形の氷。**プレイヤーだけ**が滑り、氷を踏んでいる間は同じ方向に進み続ける（1 ターン）。壁・敵・召喚モンスターで停止。1 部屋 1 枚まで、部屋を埋め尽くさない（必ず止まれる床が残る） |
| ショップ / カジノ（`MapGenParams.shop` / `.casino`） | 部屋の中に 1 マス。踏むとパネルが開く（Esc で閉じる、ターンは消費しない） |
| `handSize` | 手札上限 = 持ち込み上限 |

**ボス**（`FloorDef.boss`）: 階段（最終階は祭壇）の隣接マスに配置。HP ×2.5、ATK ×1.3、射撃なし、**移動しない**、
50% の確率で行動し、隣にプレイヤーがいれば殴り、いなければ召喚モンスターを殴る。倒すと `BOSS_DROPS` から
1 枚をその場に落とす。素通りできる。

**ショップ / カジノ**: 支払いは**ダンジョン内で拾った WIN**（`winCollected`）。
ショップは 1 フロア 3 品（価格 = MP×2、最低 4）。カジノは BET 5、1 台 5 回まで、配当 0 / 2 / 4 / 10 倍
（重み 70/20/7/3、ギャンブラーは 60/25/10/5 = 期待値プラス）。どちらもターンを消費しない。

**ダブルアップ**: 床に落ちている金のカード（1 フロアにつき 35%、ギャンブラーは 70%）。拾うと
`winMultiplier` が 2 倍（累乗）。**祭壇に到達したときだけ**効く — 脱出・死亡では無視される。

### 8.1 一覧（2026-08-29 シミュレータ結果つき）

| id | 名前 | ★ | 階 | BET/WIN | ルール | ボス | 初期手札 / 強デッキ クリア率 |
|---|---|---|---|---|---|---|---|
| light | LIGHT城 | 2 | 4 | 10/20 | litCorridors、2F ショップ | 3F skeleton | 91% / 100% |
| yukai | ゆかい | 3 | 7 | 10/90 | 3F・5F ショップ、6F カジノ | 4F goblin | 44% / 100% |
| vague | VAGUE城 | 3 | 5 | 10/100 | dormantEnemies（敵 1.5 倍）、3F ショップ | 3F goblin | 31% / 100% |
| cold | COLD城 | 4 | 5 | 10/140 | 氷、2F ショップ、4F カジノ | 3F goblin | 18% / 93% |
| cruel | CRUEL城 | 4 | 5 | 10/160 | acidFloor + enemyCrit 10%、3F ショップ | 3F mage | 2% / 84% |
| tight | TIGHT城 | 5 | 5 | 10/240 | handSize 6 + dark、ドラゴン複数 | 3F goblin, 5F dragon | 6% / 27% |

強デッキ = powerUp, potion80×2, meteor, thunder, multiFire, longSword, powerShield, reviveRing, potion40（TIGHT は先頭 6 枚）。
COLD ではボットが氷の上で行き詰まり、100 回中 3〜7 回は 3000 ターンで打ち切りになる。
祭壇・ショップ・カジノ・落ちているカードは**滑りを考慮しても必ず到達できる**ことを
`expansion.test.ts` が 60 seed × 全フロアで検証しているので、これはボット側の限界。

### 8.2 「ゆかい」

- BET 10 / WIN 90 / 7F / handSize 10。
- 各フロアの敵テーブル（種類: 初期数）と落とし物:

| F | 敵 | カード枚数 | WIN 個数 |
|---|---|---|---|
| 1 | puunya_g 3, puunya_y 3 | 3 | 1 |
| 2 | puunya_y 3, killerbee 3 | 3 | 1 |
| 3 | killerbee 3, skeleton 3 | 3 | 2 |
| 4 | skeleton 3, kemunpa 3 + ボス goblin | 4 | 2 |
| 5 | kemunpa 3, goblin 3 | 4 | 2 |
| 6 | goblin 3, mage 3 | 4 | 3 |
| 7 | mage 3, goblin 2, dragon 1 | 4 | 3 + 祭壇 |

カード重み（全フロア共通、深いほど上位が増える簡単な線形補正）:
potion20 30, potion40 15, potion80 5, fire 20, multiFire 8, thunder 8, sleep 6, haste 4, bright 4, warp 4, escape 2, bronzeSword 2。

- 敵は入口の部屋には置かない。カード/WIN は床マスにランダム。
- `descend`: 階段の上で実行 → 次フロア生成（seed = baseSeed + floorNo）、`turnsOnFloor=0`、bright 解除、`visitedRooms` リセット。後戻り禁止（MVP では階段は下りのみ）。
- `takeAltar`: 祭壇の上で実行 → `result="clear"`, 報酬 `WIN 90 + winCollected`。
- 死亡: 報酬 `floor((90 + winCollected) / 2)`。手札は失う。

---

## 9. 拠点（`src/game/meta.ts`）

```ts
type SaveV1 = {
  version: 1;
  win: number;                 // 所持 WIN、初期 100
  storage: CardId[];           // 倉庫、上限 100
  stats: { runs: number; clears: number; deaths: number; escapes: number };
};
```
- localStorage key `monster_gate.save.v1`。読み込み失敗時は初期値。
- **持ち込み画面**: 倉庫から最大 10 枚を選ぶ。出発で BET 10 を WIN から引く（不足なら出発不可）。
- **帰還**: クリア/脱出は手札 → 倉庫（溢れた分は捨てる、通知）。死亡は手札消滅。
- **ショップ（最小）**: 固定価格でカードを買える（potion20 5, potion40 9, fire 6, multiFire 12, thunder 12, その他は非売品）。倉庫を空にした初心者が詰まないための最低限。
- 初期倉庫: potion20 ×3, potion40 ×1, fire ×3。

---

## 10. UI（`src/ui/`）

画面遷移: `Title → Base(倉庫/持ち込み/ショップ) → Dungeon → Result → Base`。

**Dungeon 画面**（論理 1280×720、`devicePixelRatio` 分だけ実ピクセルを増やして描く。アーケード版に倣い 上=ステータス / 中=マップ / 下=手札）
- 上 64px: ダンジョン名・フロア、HP/MP バー、Lv/ATK/DEF、クラス、状態タグ、WIN。
- 中央 1280×528: **クォータービュー（2:1 の等角投影）**。1 マス 96×48px、床は厚み 9px の板、
  壁は高さ 40px の箱（天面 + 左右の側面を明度違いで描く）。カメラはプレイヤーへ毎フレーム
  18% ずつ寄る補間追従（5 マス以上のワープ時はスナップ）。移動は 130ms で前のマスから補間。
- 下 88px: 手札 10 枠（番号・カード名・MP）。その上にログ 2 行（40px）。
- 描画コードは `src/ui/render/` に分割: `layout`（寸法）/ `iso`（投影・カメラ）/ `art`（素材）/
  `tiles`（コード描画の箱）/ `scene`（マップとキャラ、アニメ状態）/ `hud` / `screens`。`app.ts` は状態と入力だけ。
- ミニマップはマップ左上へ半透明で重ねる。
- 描画順は行優先（= 奥から手前）。同じマスに立つキャラは床・壁を描いた直後に描くので、
  手前の壁がキャラを隠す。プレイヤーの南東 3 マスが壁のときだけ、全部描いた後に
  50% のゴーストを重ねて位置を見失わせない（壁を透過させると背景の黒が抜けて穴に見えるため）。
- キャラ・アイテム・施設は `public/art/manifest.json` に登録されたスプライトで描き、無い ID は
  絵文字のビルボード（影の楕円 + 黒縁 + 足元のリング）にフォールバックする（`docs/style-guide.md` §5）。
  スプライトは左向きで用意し、右を向いたときはプログラムが反転する（移動方向・攻撃方向で更新）。
  🦸/🧙/🎲 = 戦士/魔法使い/ギャンブラー、🟢🟡🐝💀🐛👺🔮🐉 = 敵、
  🃏 = カード、💎 = ダブルアップ、🪙 = WIN、▼ = 階段、👑 = 祭壇、🏪 = ショップ、🎰 = カジノ。
  足元リングは緑 = 自分、水色 = 召喚モンスター、金 = ボス。
- 未探索は黒。FOV は部屋の外壁を含まないので、既知の床に接する壁は描画側で補って部屋の輪郭を出す。
- 視界外だが記憶している床・壁は、スプライトを暗く焼いたキャッシュ（`ArtBank.dim`、`source-atop` で
  スプライトの不透明部分だけを暗色で塗ったもの）で描く。`globalAlpha` で薄くすると背景の黒が透けて
  幽霊のように見えるため。

**入力**
- 移動/攻撃: 矢印 + 斜めは `q e z c`、またはテンキー。`.` / `Space` で待機。`>` または `Enter` で階段/祭壇。
- カード: `1`〜`0` で選択 → 方向が必要なカードは方向キーで確定、`Esc` でキャンセル。`d` + 番号で捨てる。
- 描画はイベント配列を受けて即時反映。演出は移動補間 130ms・被弾の白フラッシュ 150ms・
  ダメージ数値のフロート 700ms のみ（いずれも `step` の結果には影響しない）。
- フレームループは `requestAnimationFrame`。`App.busy`（カメラ移動中・フロート表示中・
  フラッシュ中）が false の間は 20fps に落として無駄な再描画を避ける。

---

## 11. 乱数（`rng.ts`）

- mulberry32。`rng()` [0,1)、`rngInt(lo, hi)` 両端含む、`shuffle`。
- `DungeonState.rng` は state の一部として持ち、`step` 内で進める（リプレイ可能）。

---

## 12. テスト一覧（vitest）

| ファイル | テスト |
|---|---|
| `mapgen.test.ts` | 1000 seed で入口→階段が BFS 到達可、部屋が重ならない、入口と階段が別部屋 |
| `fov.test.ts` | 部屋内で部屋全体が見える、通路で 8 近傍だけ、bright で全マス |
| `turn.test.ts` | 壁への移動はターン非消費、敵マスへの移動は攻撃、角抜け禁止、新部屋で HP/MP 回復は 1 回だけ |
| `combat.test.ts` | ダメージ下限 1、成長上限で停止、weaponBonus 反映 |
| `ai.test.ts` | 視認で接近、隣接で攻撃、直線上で射撃、見失い→lastSeen→巡回、睡眠中は不動 |
| `cards.test.ts` | 12 種の効果、MP 不足で不発かつターン非消費、捨てると MP 回収、手札満杯で拾えない |
| `dungeon.test.ts` | 7F 通しで descend→altar→clear の報酬、死亡で半額、escape で全額+手札保持 |
| `meta.test.ts` | 保存/復元、BET 不足で出発不可、倉庫溢れ処理 |
| `sim.test.ts`（フェーズ 6） | 探索ボット（既知タイルのみ使用、HP<50% でポーション、危険な敵にファイア/サンダー）で 200 seed 走らせクリア率を出力。初期手札で 15〜45%、空手札 < 初期手札 を保証 |

---

## 13. フェーズごとの成果物（plan-mvp.md の表を具体化）

| # | 実装ファイル | 動作確認 |
|---|---|---|
| 0 | `package.json`, `vite.config.ts`, `tsconfig.json`, `eslint.config.js`, `README.md` | `pnpm test`, `pnpm typecheck`, `pnpm dev` が空ページを出す |
| 1 | `rng.ts`, `types.ts`, `mapgen.ts`, `fov.ts` + tests | テスト緑。`pnpm dev` で seed 指定のマップが Canvas に描ける（デバッグ用に全可視） |
| 2 | `combat.ts`, `ai.ts`, `turn.ts`（移動/攻撃/待機/descend）, `dungeon-def.ts` の敵表 + tests | 1F で敵を倒して成長する、7F まで降りられる |
| 3 | `cards.ts`, `turn.ts` の useCard/discardCard + tests | 12 種が UI から使える |
| 4 | `ui/` 一式（Dungeon/Result 画面、入力、ログ、ミニマップ） | 通しプレイでクリアと死亡の両方を確認 |
| 5 | `game/meta.ts`, Base 画面 + tests | リロード後も倉庫/WIN が残る、BET/報酬の収支が合う |
| 6 | `sim.test.ts`, 数値調整 | 初見想定ボットのクリア率を出し、目標（仮 30%）に寄せる |

---

## 14. 未決事項（実装中に決める）

- ポーションのオーバーヒール切り捨てで良いか（元ネタ準拠で切り捨て）。
- 敵の会心を入れるか（MVP は無し）。
- ドラゴンの射撃をブレス（範囲）にするか（MVP は直線 1 体）。
- モバイル入力（タップ移動）は MVP 外だが、Canvas 座標→方向変換を後付けできる構造にしておく。
