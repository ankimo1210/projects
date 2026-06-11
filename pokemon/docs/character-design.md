# Quokka Wilds — キャラクターデザイン方針 v2（セミリアル）

対象: 既存20体の再設計指針。コード実装とは独立したアートディレクション文書。
方針: 「現実の動物 70% / ファンタジー 30%」。かわいいデフォルメではなく、
実在動物の説得力を土台にした original animal-inspired fantasy creatures。

---

## 1. 全体アートディレクション

### コンセプト
**「フィールドナチュラリストのスケッチブック」** — 博物画の正確さに、
すこしだけ不思議が混ざった生き物たち。図鑑に載っていそうで、載っていない。

### 5つの柱

1. **骨格主導（skeleton-first）**
   実在動物の骨格・比率・関節位置から始める。後肢のZ字関節、肩甲骨の位置、
   尾椎の付け根の太さなど、解剖学的に「動けそう」な構造を崩さない。
   ファンタジー要素は骨格の外側（模様・素材・小さな付加物）にのみ載せる。

2. **シルエット3距離読み**
   遠距離（64px相当）で種が判別でき、中距離で属性が分かり、近距離で素材感が
   見える。各キャラに「シルエットの要点」を1つ定義し、それ以外を盛らない。

3. **素材コントラスト**
   1体につき最低2〜3の素材ゾーン（毛皮/皮膚/角質/鱗/羽毛）。
   毛は塊（クランプ）で造形し、鼻鏡・爪・嘴・蹄はなめらかな角質として
   ラフネス差で対比させる。単一素材のツルッとした体は禁止。

4. **自然界パレット + 限定アクセント**
   ベースは土・枯草・岩・樹皮・川の色域。彩度の高い色は**アクセント1〜2色まで**、
   面積比5〜15%。属性は体全体の色ではなく、アクセントの「出方」で表現する
   （例: spark = 棘の先端だけ琥珀色に帯電）。

5. **ファンタジー30%ルール**
   許可される改変は次の3種のみ。1体につき最大2つ:
   - 模様の様式化（縞が回路状、斑が苔状 など）
   - 小さな自然要素の付加（耳元の若葉、甲羅の苔 など）
   - 実在の特徴1つの誇張（カスクの拡大、フリルの紋様 など）
   体型・頭身・関節の改変は不可。

### 共通規定

- **頭身**: 二足型 2.8〜3.2頭身 / 四足型は実獣比を基準に頭をわずかに大きく
  （+10%まで）。マスコット的2頭身は禁止。
- **目**: 実獣比+10〜20%まで。白目（強膜）はデフォルト非表示、動物らしい
  ダークアイ+小さなキャッチライトで親しみを出す。眼幅は頭幅の18%以下。
- **表情**: 造形で笑わせない。耳の角度・首のかしげ・姿勢で感情を出す
  （ニコッカのみ例外あり、後述）。
- **怖さの上限**: 牙・爪は実獣準拠で見せてよいが、血・傷・威嚇固定の造形は
  なし。捕食者系（Snapyle, Gnashling）は休息姿勢を基本ポーズにする。

### アンチパターン（ポケモン風回避リスト）

- 巨大な白目アニメアイ / 頬の丸マーク
- キャンディカラーのフラット単色ボディ
- 2頭身マスコット比率、人間風直立（二足歩行動物以外）
- 進化前提の「赤ちゃん顔」デザイン
- ボール・モンスター球体モチーフ全般

---

## 2. ニコッカ（Nikokka）詳細 — 主人公コンパニオン

### デザインコンセプト
「世界一幸せな動物」クオッカの**本物の口角**をそのまま生かす。
笑顔はデフォルメではなく、クオッカという動物が現実に持つ造形。
そこに leaf 属性の気配を「耳元の若葉」ひとつ分だけ足した、
野原の案内人のような小型有袋類。

### 外見の特徴
- 体長約45cm想定の小型ワラビー型。**2.9頭身**。
- 頭部: 丸みのある頭蓋 + **短すぎないマズル**（クオッカの鼻筋を保持）。
  鼻鏡は濃いトープ色の裸皮。口角は自然に上がるクオッカ固有のライン
  （アニメ的な三日月笑いにしない。口を閉じた状態で「微笑んで見える」だけ）。
- 目: ダークブラウンの丸い目、実獣比+15%。下まぶたをわずかに上げ、
  穏やかな印象に。白目なし、上縁に細いキャッチライト。
- 耳: 短く丸い耳。**左耳の付け根から若葉3枚の小さな芽**（体高の8%以下）。
  これが主役の識別子であり、leaf属性の表現。
- 体: 前肢は短く華奢、後肢は太く力強いマクロポッド構造。座位（後肢に体重、
  前肢を胸の前）が基本ポーズ。背中に**葉脈状のわずかに濃い差し毛模様**
  （ファンタジー要素2つめ、ごく薄く）。
- 尾: 毛の薄い円錐形の尾。付け根は太く、地面の支えに使う。

### シルエットの要点
「丸い頭 + 猫背の座位 + 太い後肢と地に着いた尾」。
遠目にはネズミでもウサギでもなく「小さなカンガルー類」と読めること。
耳の若葉がシルエット上の唯一の突起アクセント。

### 配色案
| 部位 | 色 | 備考 |
|---|---|---|
| 背・外側 | 灰褐色 `#8d7a5f` | 粗い差し毛で `#6e5f4a` を混ぜる |
| 腹・頬・胸 | 温かいクリーム `#d9c9a8` | 顔の下半分を明るくし表情を読ませる |
| 鼻鏡・爪・足裏 | ダークトープ `#4a4038` | 裸皮ゾーン |
| アクセント1 | 苔緑 `#5a7d4a` | 背の葉脈模様（低コントラスト） |
| アクセント2 | 若葉 `#8fae5d` | 耳元の芽のみ。彩度最高点をここに集中 |

### 素材感
- 毛: 短く粗い密毛。頬と腰に毛クランプを造形。ラフネス0.85〜0.95。
- 鼻鏡: しっとりした裸皮。ラフネス0.55、わずかな赤みのSSS風ティント。
- 爪: 半透明がかった角質。ラフネス0.4。
- 若葉: 薄い葉。両面描画、縁にわずかな透過光（明るいリム）。

### 3Dモデリング時の注意点
- マズルを潰さない。鼻先→額のラインに段差（ストップ）を残す。
- 後肢はZ字関節（股→膝→踵→中足骨）を正しく入れる。座位で踵接地。
- 尾の付け根は骨盤幅の60%程度の太さから始めてテーパー。
- 笑顔は口角ジオメトリの恒久造形にする（表情モーフ不要、リグ簡略化）。
- 耳の若葉は別メッシュ。風揺れ用に独立ボーン1本。
- ヒーローモデルにつき他より1段高密度（後述の3D制作ルール参照）。

### 画像生成プロンプト
```
semi-realistic fantasy creature design, a quokka-inspired companion animal,
small wallaby anatomy with accurate macropod skeleton, sitting upright on
strong hind legs and thick tail base, gentle natural smile unique to quokkas
(no cartoon grin), warm grey-brown coarse fur with cream chest, small dark
brown eyes with soft catchlight (no oversized anime eyes), short round ears
with a tiny three-leaf sprout behind the left ear, subtle moss-green
leaf-vein markings on its back, naturalist field guide illustration style,
soft daylight, neutral background, full body turnaround, 70% real animal
30% fantasy, not pokemon style
```

---

## 3. 残り19体 簡易デザイン仕様

各体: ①コンセプト ②外見 ③シルエット ④配色（ベース/アクセント）⑤素材感
⑥3D注意 ⑦プロンプト断片（共通プリフィックスは後述）。

**プロンプト共通プリフィックス**:
```
semi-realistic fantasy creature design, accurate real-animal anatomy,
naturalist field guide illustration, natural earth-tone palette with 1-2
accent colors, visible material contrast between fur/skin/keratin,
soft daylight, full body, 70% real animal 30% fantasy, not pokemon style,
```

### No.02 Wombolt（ウォンバット / stone）
1. 岩盤を背負う穴掘り屋。ウォンバットの「硬い尻」を石化方向に誇張。
2. 樽型胴、短肢、広い鼻鏡。**腰〜尻に六角形の板岩スクート**が毛から覗く。
3. シルエット: 首のない低い長方形。前後どちらが頭か尻のスクートで分かる。
4. 土埃の灰褐 `#8a7866` / 腹 `#bfae98`、アクセント: 黄土のダストライン `#b08d4f`。
5. 短い剛毛 + マットな板岩（ラフネス0.7、エッジに欠け）。鼻鏡は裸皮。
6. スクートは体に埋め込み造形（貼り付け感を出さない）。脚は短くても4関節維持。
7. `a wombat-inspired burrower, barrel body, hexagonal slate plates embedded in its rump fur, dusty ochre stripes`

### No.03 Quillvolt（ハリモグラ / spark）
1. 静電気を棘に蓄える地面の歩く蓄電器。
2. 低い体、長い筒状の吻、強い前肢の掘削爪。棘の**先端2cmだけ琥珀色の半透明**。
3. シルエット: ドーム + 前方に伸びる細い吻。棘の外周がギザギザの輪郭線。
4. 焦げ茶 `#6b5a3e` / 棘基部 `#d9c878`、アクセント: 琥珀 `#f5d442`（先端のみ、微発光可）。
5. 棘=硬い角質（ラフネス0.45）、下毛=粗毛、吻=革質。素材3種のお手本キャラ。
6. 棘は法線方向に揃えてインスタンス配置。吻先の鼻孔を忘れない。
7. `an echidna-inspired creature, dome of keratin quills with translucent amber static-charged tips, long tubular snout, powerful digging claws`

### No.04 Billabog（カモノハシ / tide）
1. 水面の反射を体にまとう半水棲の予報士。
2. 流線型の低い体、革質の嘴、水かき、櫂状の尾。**脇腹に水面のゆらぎ模様の
   淡い斑点**（青緑、湿っている時だけ目立つ想定）。
3. シルエット: 平たい嘴 + 低い紡錘形 + ビーバー的な平尾。
4. 濡れた灰青の毛 `#5d7a8a` / 嘴・足 `#c98e54`、アクセント: 浅瀬の青緑斑 `#4f9ed9`。
5. 防水毛（濡れ感: ラフネス0.6に下げ、束感を強調）、嘴はセンサー孔の点描。
6. 嘴と頭部の接合を裂け目なく。尾は上下に平たく（左右ではない）。
7. `a platypus-inspired semi-aquatic creature, sleek waterproof fur, leathery bill with sensory pores, faint teal water-ripple speckles along flanks`

### No.05 Glidewisp（フクロモモンガ / breeze）
1. 夜風に乗る滑空獣。巻雲のしっぽ。
2. 大きな夜行性の目（**実獣として自然なので大目OK**の唯一枠）、体側の滑空膜、
   背中の黒い正中線。膜の縁の毛が**風になびく薄い房**。
3. シルエット: 滑空時は四角い凧、静止時は膜のたるみが脇に波打つ小獣。
4. 青灰 `#9aa7b8` / 腹 `#e3e8ee`、アクセント: 膜の縁の銀白 `#dfe6ef`+濃紺の正中線。
5. 極細の柔毛（ラフネス0.95）、膜は薄い皮膚で透過光あり。
6. 膜は腕〜足首に正しく接続。滑空ポーズと静止ポーズ両方で破綻しない
   トポロジーに。
7. `a sugar glider-inspired creature, naturally large nocturnal eyes, patagium gliding membrane with wispy silver fur edges, dark dorsal stripe, cirrus-cloud tail`

### No.06 Emberoo（カンガルー / ember）
1. 焚き火の残り火のようなアカカンガルー。跳ねた後に熱が残る。
2. 筋肉質の後肢と太い尾、小さな前肢。**前腕と足先が炭化したような黒**、
   耳の内側と尾先に**残り火のグラデーション**（発光は最小限）。
3. シルエット: 直立気味の三角形（尾が三脚の3本目）。
4. 赤砂色 `#c4663a` / 胸 `#e8b48a`、アクセント: 炭黒 `#2e2622` + 残り火 `#e8612f`。
5. 短毛、炭部分はマットで乾いた質感（ラフネス0.9）、残り火部はごく弱い emissive。
6. 跳躍をさせるならアキレス腱のラインを造形で見せる。尾は第5の肢として太く。
7. `a red kangaroo-inspired creature, muscular hind legs and thick tail, charcoal-blackened forearms and feet, faint smoldering ember gradient inside ears and tail tip, no open flames`

### No.07 Gumdrowse（コアラ / leaf）
1. ユーカリと半分同化しかけた眠り屋。
2. ずんぐりした体、大きな鼻鏡、眠たい半眼。耳の縁の房毛が**葉形のフリンジ**、
   背に**地衣類のような淡い緑斑**。
3. シルエット: 丸+丸（頭と体）、横に張り出す丸耳。木に抱きつく腕の長さ。
4. 灰 `#9c9c94` / 腹 `#d8d8d0`、アクセント: 地衣の緑 `#54705a`（低彩度厳守）。
5. 羊毛質の厚い毛（最も毛足の長いキャラ）、鼻鏡は大きな裸皮でラフネス0.5。
6. 鼻を頭部体積の1/4まで大きく（実獣準拠の誇張）。爪は枝掴み用に長く。
7. `a koala-inspired creature, dense woolly grey fur, large leathery nose, sleepy half-closed eyes, eucalyptus-leaf-shaped ear fringes, faint lichen patches on back`

### No.08 Sundingo（ディンゴ / ember）
1. 夕暮れの色を背負う野犬。群れない一匹狼。
2. 引き締まったディンゴ体型、立ち耳、ふさ尾。背に**夕焼けのグラデーション
   サドル**（砂色→緋色）、四肢の先は焦げた濃色。
3. シルエット: 痩身の犬科。尾は下げ気味、耳は常に立てる。
4. 砂金色 `#d49a52` / 喉・腹 `#f0d9b0`、アクセント: 緋 `#b3431f`（サドルのみ）。
5. 短い粗毛、鼻鏡と肉球は乾いた革質。
6. 犬科の肩甲骨の動きが見える胸郭造形。マズルは細め、目はアーモンド形琥珀。
7. `a dingo-inspired lean wild dog, sandy coat with a sunset-gradient crimson saddle marking, scorched dark lower legs, amber almond eyes, alert pricked ears`

### No.09 Casshelm（ヒクイドリ / stone）
1. 板岩のカスクを戴く森の重戦車。実物がすでに恐竜なので誇張は最小限。
2. 黒い毛状羽毛、青い首、赤い肉垂（**実在の配色をそのまま採用**）。
   カスクを**積層した板岩**として1.2倍に拡大。脚は鱗装甲、三本指の大爪。
3. シルエット: 涙滴形の胴 + 縦に立つ首 + カスクの台形。
4. 黒羽 `#2e3440` / 首の青 `#4f8a8b`・肉垂の赤（実在色）、カスク: 石灰岩 `#d9d3c0`。
5. 羽毛=毛髪状の粗い束、首=裸皮の鮮色、カスク=層状の石（ラフネス0.6）。
6. 羽はカードではなく髪の毛状ストランドの束で。脚の鱗は前面のみ大判に。
7. `a cassowary-inspired creature, coarse hair-like black plumage, vivid blue bare neck, enlarged casque made of layered slate stone, armored scaly legs with large claws`

### No.10 Numbuzz（フクロアリクイ / spark）
1. 縞模様がときどき帯電するアリ食い。
2. 細身の体、尖った顔、ふさふさの尾。背の白縞が**フィラメント状に微発光**
   （興奮時のみの想定、常時は白縞）。静電気で**尾の毛が逆立つ**。
3. シルエット: 低い紡錘形 + ボトルブラシの尾。
4. 赤褐 `#b3683a` / クリーム縞 `#e8cfa0`、アクセント: 帯電の琥珀 `#f5d442`（縞の芯のみ）。
5. 滑らかな短毛と逆立つ尾毛の対比。鼻先は裸皮。
6. 縞は体の流れに沿わせてUVを切る。尾は体長と同じ長さ。
7. `a numbat-inspired creature, slender body with cream back stripes that faintly glow like charged filaments, bottlebrush tail frizzed by static, pointed snout`

### No.11 Quollast（フクロネコ / stone）
1. 斑点が小石になった夜の岩場歩き。
2. ネコ風だが有袋類のずんぐり腰。**白斑の中心に小さな石英の粒**が
   埋まっている（既存設定の図像化）。
3. シルエット: 低い猫科風 + 太く長い尾。背のラインは直線的。
4. 灰褐 `#7d6b5d` / 腹 `#cfc0ae`、アクセント: 石英白 `#e8e3d8`（斑のみ、艶あり）。
5. 短毛 + 斑の石粒だけ滑らか（ラフネス0.3）。素材差を点で見せる珍しい型。
6. 石粒は浅浮き彫り(2mm弱)。盛りすぎるとゴーレム化するので高さ厳守。
7. `a quoll-inspired creature, grey-brown spotted coat where each white spot holds a tiny embedded quartz pebble, stocky marsupial build, long thick tail`

### No.12 Moonbilby（ミミナガバンディクート / breeze）
1. 月夜の風の音を全部聞いている大耳の砂漠ウサギもどき。
2. 巨大な耳（実在比準拠でOK）、絹のような銀青毛、黒→白のバナー尾。
   耳の内側に**蛾の羽のような淡い紋**。
3. シルエット: 耳が全身の1/3。アーチ状の背、華奢な脚。
4. 銀青灰 `#aab0c4` / 腹 `#e8e6f0`、アクセント: 月光の藍 `#6470a0`（耳紋のみ）。
5. 絹質の長毛（毛先に光沢）、耳は薄い皮膚で透過光、尾先は旗状の白毛。
6. 耳は薄板でなく付け根に厚み。透過光（リムライト）が映えるよう両面法線に注意。
7. `a bilby-inspired creature, enormous translucent ears with faint moth-wing patterns inside, silky silver-blue fur with moonlit sheen, black-and-white banner tail`

### No.13 Frillare（エリマキトカゲ / ember）
1. フリルを開くと熾火の紋様が現れる乾燥地のランナー。
2. 樹皮色の鱗、長い尾、二足疾走の後肢。閉じたフリルは樹皮、**開くと
   ひび割れた熾火模様**（赤橙、emissive弱）。
3. シルエット: 閉=細身のトカゲ、開=頭の周りに円盤。開閉で別シルエット。
4. 樹皮褐 `#a3552e` / 腹 `#e0a060`、アクセント: 熾火 `#e83b2f`（フリル内面のみ）。
5. 細かい鱗（ラフネス0.55）、フリルは薄い皮膜で開閉時に張りが変わる。
6. フリルは開閉ボーン必須。閉状態の畳みジワを造形しておく。
7. `a frilled lizard-inspired creature, bark-brown scales, neck frill that opens to reveal cracked glowing-coal patterns, long tail, bipedal sprint pose`

### No.14 Chucklewing（ワライカワセミ / breeze）
1. 笑い声で風向きを変える、ずんぐりした森のカワセミ。
2. 大きな頭と頑丈な嘴（実在比準拠）、茶のアイマスク、翼に**風の流線状の
   青いバンド**（実在のコバルト斑の様式化）。
3. シルエット: 頭でっかちの寸詰まり鳥。嘴は頭長と同じ。
4. 灰白 `#e8e2d5` / 背・翼 `#8d9aa8`、アクセント: コバルト `#4a6fa5`（翼帯のみ）。
5. ふっくらした羽毛（胸は柔らか、翼は硬い羽弁）、嘴は角質ラフネス0.4。
6. 頭部:胴=1:1.4の実在比を守る（かわいくしようと頭を盛らない。すでに大きい）。
7. `a kookaburra-inspired stocky kingfisher, oversized sturdy beak, brown eye-mask, wind-streak cobalt bands on wings, fluffy cream chest`

### No.15 Dunestrider（エミュー / breeze）
1. 砂塵の渦を裾にまとう、決して後退しない長距離走者。
2. もしゃもしゃの二重羽軸の羽毛、裸皮の青い首、強靭な3本指の脚。
   羽の裾が**砂煙のようにかすれて消える**グラデーション。
3. シルエット: 楕円の羽毛塊 + 上に伸びる細い首 + 長い脚。
4. 枯草褐 `#7a6f5a` / 羽裾 `#b8ad94`、アクセント: 首の青灰 `#3e4a5a`（実在準拠）。
5. 髪の毛状のシャギーな羽（カードではなくストランド）、脚は大判の鱗。
6. 体の羽は重力に従って垂れる流れを彫る。膝(踵)関節の向きを間違えない。
7. `an emu-inspired creature, shaggy double-shafted hair-like plumage fading at the hem like dust haze, bare blue-grey neck, powerful three-toed legs`

### No.16 Snapyle（ワニ / tide）
1. 川石と見分けがつかない待ち伏せ屋。基本ポーズは「浮かんで休む」。
2. 低く長い体、**川石そっくりの丸みを帯びた背鱗板（オステオダーム）**に
   薄く藻が生す。水面線で上下二色。
3. シルエット: 地を這う一直線 + 背のゴツゴツの稜線。
4. 上面: 川石灰緑 `#5a7a4e`、下面: 浅瀬の淡黄 `#cfd9a8`、アクセント: 藻 `#3a5230`。
5. 鱗板=濡れた石（ラフネス0.45）、喉と腹=柔らかい革、歯は見せすぎない。
6. 背鱗板は規則正しく並べず、川石の乱れで配置。尾は左右に平たく。
7. `a crocodile-inspired creature, low lounging pose, rounded river-stone osteoderms with thin algae film, two-tone waterline coloring, calm half-closed eyes`

### No.17 Shellbrook（カメ / tide）
1. 背中が小川の岸辺になっている歩く庭。
2. ドーム甲羅の溝に**本物の苔のクッションと小さなシダが根付く**。
   皮膚は革質のしわ、目は穏やかな琥珀。
3. シルエット: ドーム + 四本柱の脚 + 小さな頭。甲羅上の植生が不規則な突起。
4. 甲羅: 湿った石緑 `#4e7a6a`、皮膚: 枯草 `#d9c88a`、アクセント: 苔・シダ `#5d8a3e`。
5. 甲羅=濡れた鉱物(0.5)、苔=深いラフネス(1.0)で光を吸う、皮膚=しわの革質。
6. 植生は甲羅の溝（成長線）に沿って配置。シダは2〜3株まで、盆栽にしない。
7. `a turtle-inspired creature, mossy dome shell with small live ferns rooted in its growth-line grooves, wrinkled leathery skin, gentle amber eyes`

### No.18 Gnashling（タスマニアデビル / ember）
1. ぶつぶつ文句を言う黒い小型ファイター。胸の白帯が熱を持つ。
2. ずんぐりした黒い体、大きな頭と強い顎、丸い耳。**胸の白いV字帯**
   （実在準拠）が興奮時に**内側から熾火色に透ける**。
3. シルエット: 頭が大きい低い塊。尾は短く太い（脂肪蓄積、実在準拠）。
4. 炭黒 `#3a3338` / 胸帯 `#e8e3d8`、アクセント: 熾火 `#e8612f`（胸帯の芯のみ）。
5. 粗くて硬い黒毛、耳の内側と鼻周りは裸皮のピンク〜煤色。
6. 怖くしすぎない調整: 耳を丸く大きめ、基本表情は「不満顔」で牙は見せない。
7. `a tasmanian devil-inspired creature, stocky black build with a white chest chevron glowing faintly like embers from within, round ears, grumpy but harmless expression`

### No.19 Drowsum（フクロギツネ / leaf）
1. 落ち葉の柄を着た夜の居候。死んだふりの名人。
2. ふさふさの灰紫毛に**落ち葉のまだら柄**（leaf要素）、ピンクの鼻、
   裸皮の巻き尾の裏側が**蔓のような節**。
3. シルエット: 丸い背 + 大きな丸耳 + 太い巻き尾。
4. 灰紫 `#9a8ba0` / 腹 `#ded5e3`、アクセント: 枯葉 `#8a7340`+苔 `#54705a`（柄のみ）。
5. 長毛のもふもふ（毛先だけ色が抜ける）、尾の裏は無毛の把握面。
6. 尾は巻き付け可能な長さ（体長の0.9倍）。死んだふりポーズを別ポーズで用意すると楽しい。
7. `a brushtail possum-inspired creature, fluffy grey-mauve fur with leaf-litter dapple camouflage, pink nose, prehensile tail with vine-like bare underside`

### No.20 Crestoo（キバタン / spark）
1. 冠羽が稲妻の形に逆立つ白いお調子者。
2. 白い羽毛、**ギザギザに逆立つ黄色い冠羽**（実在の冠羽を雷形に様式化）、
   煤色の嘴と足。羽の先にときどき**パチッと火花の名残**（emissive点、極小）。
3. シルエット: ずんぐりしたオウム + 展開する冠羽のギザギザ。
4. 白 `#ecebe6` / 翼裏 `#f5f4f0`、アクセント: 硫黄黄 `#f5d442`（冠羽のみ）+ 煤 `#3a3a40`。
5. 滑らかな体羽と、硬く尖った冠羽の対比。嘴は厚い角質ラフネス0.35。
6. 冠羽は開閉ボーン。白の単調さはAO焼き込みと羽のレイヤー影で防ぐ。
7. `a sulphur-crested cockatoo-inspired creature, white plumage, jagged lightning-shaped yellow crest that flares up, charcoal beak and feet, tiny static sparks at feather tips`

---

## 4. 3D制作ルール

### プロポーション標準
- 二足型: 2.8〜3.2頭身。四足型・鳥型: 実獣骨格比 ±10%以内。
- 眼幅 ≤ 頭幅の18%。白目はデフォルト非表示。
- 関節は実獣準拠（四足の後肢Z字、鳥の踵=逆膝に見える関節、など）。
- 検収: 64pxサムネイルでのシルエット判別テスト + ターンテーブル確認。

### モデル密度（ゲーム内リアルタイム想定）
| 用途 | 三角形数 | 備考 |
|---|---|---|
| ニコッカ（ヒーロー） | 8,000〜12,000 | 常時画面内のため最優先 |
| 野生クリーチャー LOD0 | 3,000〜6,000 | バトル・近距離用 |
| 野生クリーチャー LOD1 | ~50% | フィールド中距離 |
| 野生クリーチャー LOD2 | ~25% | 遠距離群れ表示 |
- 毛クランプ・鱗・スクートは法線マップ化を基本、シルエットに出る塊のみ実ジオメトリ。
- 制作パイプライン: スカルプト（高密度）→ リトポ → ベイク。
  現行のプリミティブ構成モデルは、本方針の**プロポーションと配色だけ先行適用**
  できる（頭身・マズル長・色は primitives でも反映可能）。

### マテリアル方針（PBR metallic-roughness）
- 1キャラ=1マテリアル（アトラス化）。metalness は全キャラ 0 固定。
- ラフネス基準値:
  - 毛皮 0.85〜0.95 / 羽毛 0.7〜0.85 / 鱗・甲羅 0.45〜0.65
  - 角質（嘴・爪・棘・カスク）0.35〜0.5 / 鼻鏡・裸皮 0.5〜0.6（湿り気）
- emissive は spark / ember 系のアクセントのみ。**面積5%以下・強度は
  「暗所でようやく分かる」程度**。発光で属性を説明しない（形と色で説明する）。
- 透過光（耳・膜・若葉）は薄物にのみ許可。SSS の代わりに縁色の明度上げで近似可。

### テクスチャ方針
- サイズ: ヒーロー2048px、その他1024px。1枚のカラーアトラス +
  ノーマル + ORM（AO/Roughness を同梱）。
- 描き方: 手描きのスタイライズド・リアリズム（博物画寄り）。写真テクスチャの
  貼り込みは禁止。AO とグラデーションランプをベイクして陰影の8割を作り、
  ライティング依存を減らす。
- 模様（縞・斑・サドル）は UV シームをまたがない配置に。アクセント色は
  テクスチャ上でも面積管理（5〜15%）を守る。
- web 配信: glTF + Draco/meshopt 圧縮、テクスチャは KTX2(BasisU) を標準。

### リグ最小構成
- 共通: ルート + 脊椎3 + 頭 + 尾2〜3 + 四肢各3。
- 追加ボーン: 耳（全キャラ）、ニコッカの若葉、Frillare/Crestoo の開閉冠・フリル、
  Glidewisp の膜端。表情モーフは原則なし（姿勢と耳で演技する方針のため）。
