# 素材の制作記録

2026-11-18。架空の港の地理、商店名、庁舎の意匠、人物の衣服と動作、市営渡船の標章を本作のために設計した。

| ゲーム内の素材 | 制作方法 |
|---|---|
| 夜勤設備員と徘徊者 | Three.js のスキンメッシュをコードで造形。設備員の高襟、無線機、反射帯、港章と、徘徊者の服や非対称な歩行を個別に作成 |
| ターミナル・街並み・警察署 | メートル単位で地形と建物を配置。案内標識、運航掲示板、きっぷ、商店看板は Canvas で描画 |
| 雨・サイレン・足音・金属音・ゲームの効果音 | Web Audio のノイズ・フィルタ・発振器・定位を組み合わせて生成 |
| 防災無線・携帯無線 | 本作用に書いた日本語の2本の台詞をローカルの日本語音声で読み上げ、無線の帯域に整えてMP3化 |
| 日本語見出し書体 | Noto Serif JP のサブセット。ライセンスを [OFL.txt](../public/fonts/OFL.txt) に同梱 |

## 画像生成

内蔵の ImageGen で制作し、ゲーム用に WebP に圧縮した。以下は各画像に与えた制作指示。

### 港の遠景

[outer-harbor.webp](../public/art/outer-harbor.webp)

Use case: stylized-concept. Asset type: seamless-looking very wide environmental matte painting for a real-time original Japanese survival-horror game's distant harbor sky and reflections, landscape aspect ratio 3:1. Full bleed. View directly over dark harbor water from a low waterfront ferry terminal at 2 AM in a torrential downpour in a fictional small late-1980s Japanese coastal city. Wide cinematic detailed photograph-like rendering, analog 35mm film aesthetic, a sense of deserted layered physical space. Across the water on the far shore: dense low industrial waterfront and a few taller buildings with sparse cyan-white lit square windows and 3 tiny red aircraft lamps, a moored worn passenger ferry on the left, two towering angular dockyard cranes with dim red marker lights in the middle right, faint blue grey mist in the background, rooflines and industrial masts. Horizon below midline at 62%, clouds and fog layered in dark petroleum blue, separated distinguishable silhouettes. Wet water at bottom has silver teal broken vertical reflections and a few sodium amber lights. Moody cinematic lighting, restrained desaturated teal and charcoal with amber pinpoints. Texture and atmospheric details visible; no crushing into pure black. No large foreground objects, railings or roofs, no people, no text, no UI, logos, borders, bright moon, neon overkill or recognizable real landmarks. Edges of the image dissolve in matching blue-grey harbor fog.

### 待合通路の観光ポスター

[island-poster.webp](../public/art/island-poster.webp)

Use case: stylized-concept. Asset type: a single flat, front-on, edge-to-edge printed vintage Japanese ferry-route poster texture, portrait 2:3. A lighthouse on a rocky offshore island with a small side-on ferry riding broad choppy gouache ocean waves. Screen-printed Japanese mid-century public transport illustration, powerful simple asymmetric shapes, weathered muted turquoise, old cream, faded black, terracotta setting sun. Fine halftone dots, paper grain and very subtle age. Japanese heading exactly 「沖灯島」 across the top in bold dark teal ink. Footer exactly 「汐凪市営渡船」. Art fills the frame. No wall, external borders, glass, extra text, mockup, modern brands, shadow or perspective. A believable original diegetic artwork to mount in the ferry waiting hall of an eerie game.

### 建材の表面

[port-concrete.webp](../public/art/port-concrete.webp)

Use case: photorealistic-natural. Create a high quality ORIGINAL square seamless flat material albedo photo texture for a 3D game, showing a close straight-on orthographic 2m by 2m patch of decades-old exposed salt-stained concrete of a coastal Japanese ferry terminal. Medium-gray desaturated green slate cement, incredibly tactile fine sandy aggregate, pale efflorescence, charcoal hairline fractures with variation in scale, eroded darker speckled small zones, lightly pitted, old dried water stains feather into the concrete. Fragmentary faint lines from formwork. Fairly low overall contrast, lots of fine natural mineral texture. Flat evenly overcast neutral illumination, edge-to-edge, continuous in both directions. No plane edges, staging, shadows, objects, text, tiles, squares, repeating patterns, lights, puddles, paint markings or photographic perspective. PBR material diffuse photograph.
