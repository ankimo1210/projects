# Sauna Design

東京で検討中の男性専用サウナ（A案20×14m仮）の内装と実3D。内装の現行は**v8**、建築条件を重ねた照合用試作は[v9](docs/V9_BUILDING_STUDY.md)。v8は水風呂2槽を縮めて空いた床を休憩の離れ（寝椅子4）にし、サブ2室（セルフロウリュ・高温ドライ）の座り方を作り替えた概念3D。施工承認ではない。席数・水風呂に入れる人数は成人の仮寸法を置いた位置の数で定員ではなく、ストーブ機種とメーカー離隔・熱と蒸気の流れ・浴槽設備・構造・法適合・費用は未検証。

**新しい比較版V10（元案は保持）**：[設計・検証](docs/V10_PARENT_REVIEW.md)。170㎡・24人目標/主室12＋セルフ5/休憩16の別案を同じFable/highと制作。画像9点・編集可能BLEND・GLB・フロアマップを出力し、3Dを実表示確認済み。<http://127.0.0.1:8790/viewer/>。生成物は `\\wsl.localhost\Ubuntu\home\kazumasa\projects\_data\sauna-design\fable-v10`。サ室前0.756mや全員休憩8不足、床下/メーカー/法適合/費用は残条件。採用/1億円成立の確定ではない。

v3〜v6とv8はユーザー指定のFable/highがBlender/Cyclesで制作。v7は同じ会話が利用上限で止まり、親が製品反映を仕上げた。同じ会話と旧版を保存している。

生成物（Git管理外）: `\\wsl.localhost\Ubuntu\home\kazumasa\projects\_data\sauna-design\fable-v8`

| 内容 | v8以下のパス |
|---|---|
| 全体フロアマップ（番号と凡例） / 元の真上レンダリング | diagrams/sauna_floor_map_v8.png / renders/sauna_plan_v8.png |
| 編集可能なモデル / 携帯用GLB | model/sauna_a_v8.blend / model/sauna_a_v8.glb |
| セルフロウリュ（扉から / 席から） | renders/sauna_self_v8.png / sauna_self_seat_v8.png |
| 高温ドライ（扉から / 確認用の人体入り） | renders/sauna_dry_v8.png / sauna_dry_people_v8.png |
| 浴室全景 / 休憩の離れ / 離れと水風呂の関係 | renders/sauna_water_v8.png / sauna_annex_v8.png / sauna_annex_pool_v8.png |
| 浴室とサブ2室の真上 | renders/sauna_bath_top_v8.png |
| 寸法入りの検討図（平面・断面、人体・動線・通路幅） | diagrams/v8_plan.png |
| 軽量3D | viewer/index.html（HTTPサーバー経由。確認用の人体を切替可） |
| 実メッシュの確認とv7との照合 | verification/v8_design_check.json |
| 照明の記録 / 配布ハッシュ | verification/lighting_v8.json / delivery_manifest.json |

- 何を比べて何を選んだか、寸法、限界: [v8設計メモ](docs/V8_DESIGN.md)
- 完了/進行/残課題: [STATUS](docs/STATUS.md)
- ChatGPT用の包括的技術引き継ぎ: [統合本文](docs/handoff/2026-11-15/HANDOFF.md)・[開始案内](docs/handoff/2026-11-15/START_HERE.md)。議論/採用要件、V8/V9、建築設備、費用/物件/収益、未解決と設計データ索引を統合。ZIP用の相対パスは展開後ルート基準。共有データchatgpt-handoff-v1/のsauna-chatgpt-handoff-2026-11-15.zip（約381MB/627ファイル）に、現行モデル・本番画像・図面/表/計算・元資料・再生成ソースを梱包し、SHA256/CRC・解析データ/相対参照を検証済み。元のFable会話・凍結版は保持し、今回の新規GPU/モデル生成・外部アップロードはない。
- 建築基本計画①〜⑤: [条件](docs/ARCHITECTURE_BRIEF.md)・[実行計画](docs/superpowers/plans/2026-11-15-sauna-architecture-basic-plan.md)・[成果と検証](docs/basic_design/REVIEW.md)。断面3案、寸法図、動線、設備概算、30項目の要件照合を作成。生成物は共有データのarchitecture-v1/で凍結。物件とメーカー等の条件は未確定。
- ⑥[費用試算](docs/basic_design/05-costs.md)：84項目、基準の総資金は運転3か月込み約2.26億円。2億円へ寄せる未交渉の目標例は約1.98億円。成約見積なし・物件改修等の未算入あり。PDF14ページと編集可能Excelは共有データのcost-v1/で凍結。
- ⑦[物件条件表・候補判定](docs/basic_design/06-property-and-handoff.md)：34条件・9主要確認・家賃/保証金の予算境界、PDF10ページ/Excel4シートと[照会文案（未送信）](docs/basic_design/property-inquiry.md)。未入力フォームはproperty-v1/で保持。
- ⑦現行は[ONE GINZA B101の詳細確認](docs/basic_design/11-one-ginza-detail.md)。347.21㎡分割案を朝〜22/23時の希望で照合。公開図の給水40A/排水100A/ガス80Aと不整形区画、非飲食の22時営業例外を確認したが、実賃料/浴場・時間承諾/支持・専用設備・分割避難は未確認。税抜月家賃315.09万/共益30万等を置く総資金の例は約3.19億円で、実価格予測や施工見積ではない。新one-ginza-detail-v1/に原図/比較/仮9条件を保存。[照会文案](docs/basic_design/one-ginza-inquiry.md)は未送信。予算上限は一旦解除のまま、物件別図面/最終3Dは成立資料取得後。
- 前段の[山手線・千代田線の駅徒歩10分以内の再探索](docs/basic_design/10-yamanote-chiyoda-search.md)は保存。大崎/いちご神宮前は除外。新確認対象はONE GINZA、大手町B1 353.72㎡、補欠は日比谷B1 280.99㎡。candidate-search-v3/の共通仮契約18条件は原280㎡の比較で、最新11の347㎡追加枠入り試算とは範囲が違う。
- 前段の[大崎・神宮前の詳細比較](docs/basic_design/09-osaki-jingumae-detail.md)は履歴として保存。大崎は貸主側掲載終了と事務所仕様の支持/設備、神宮前は募集面積の共用按分控除後約210.5㎡が判明し、現280㎡原型では未成立。ユーザー指定で今回から除外。出典/24条件のcandidate-detail-v1/と未送信照会文案を上書きしない。
- 前段の[山手線駅徒歩10分以内の抽出](docs/basic_design/08-yamanote-search.md)は募集面積で4件を選んだ履歴として保存。大崎/神宮前の最新判定は上記09を優先し、candidate-search-v2/は上書きしない。物件固有の最終3D統合は実条件/寸法図取得後。
- 前回の[郊外を含む実在候補比較](docs/basic_design/07-candidate-search.md)4件は、新しい立地条件から外れたため現行候補から除外して保存。candidate-search-v1/は上書きしない。前工程でGPU/Fableを再開し、同じ会話でソース作成→親のV9仮モデル/GPU4枚/GLB・表示確認まで完了済み。
- 実モデルの確認方法と結果: [検証](docs/VERIFICATION.md)
- 再現: [再生成](docs/REGENERATE.md)
- 全体マップの再生成: `bash scripts/blender.sh render plan --res 2400 --samples 400 --hide Ceilings --world 0.35 --name sauna_plan_v8` → `python3 -B scripts/floor_map.py`。同じ保存済みモデルの真上に番号を付けるだけで、配置は変更しない。
- 今回の依頼: [V8_BRIEF](docs/V8_BRIEF.md)
- 製品候補（v7のまま）: [製品選定](docs/PRODUCT_SELECTION.md)
- 保存した同じ会話: [FABLE_SESSION](docs/FABLE_SESSION.md)

v8の要点：水面12.16 → 6.42 m²、水の中の静止位置は通常5・詰めて6（階段を下りた床は別に空けてある）、休憩できる場所20 → 24、セルフ6位置（高さ3つ）、ドライ4位置（腰掛け2＋脚を伸ばす寝座2）、サブ2室の天井2.30 → 2.40 m。メインサウナ・休憩室・炭酸泉・扉・製品段階はv7と同じ形。

未解決のまま：アウフグース直後は水風呂に待ちが出る（2分に集中すると4〜5人）。休憩はなお40人に対して24か所。メインの6か所の出入りの協力、アウフグース床の制限はv6のまま。METOS ZL-300は1台の外形比較、LIXIL床はST-33Nの仮色（色・台数・離隔は未選定）。以前の図と画像はv3〜v7の凍結フォルダ、旧ソースはsessions/source-v6.zip・source-v7.zipに残る。
