# WSET 問題ブラッシュアップ記録 — 2026-09-14

四択168問、記述式10問、関連用語2項目を改訂し、アプリ用データへ反映しました。四択のうち91問は内容の改善、77問は解説冒頭の重複表現の整理です。内容改善には、誤った選択肢を正答としていた16問の訂正を含みます。

## 変更範囲

| 対象 | 改訂数 | 主な変更 |
|---|---:|---|
| LO1：栽培・醸造 | 37問 | 正答整合性、栽培対策、コルク、発酵・再発酵の説明 |
| LO2：スティルワイン | 26問 | 産地・品種の正答、標高と気温、川の光反射と気温緩和 |
| LO3：スパークリングワイン | 29問 | リザーヴワイン、白亜質土壌、グラス・保存、甘味区分 |
| LO4：酒精強化ワイン | 30問 | 熟成、フロール、ソレラ、VOS/VORSの意味 |
| LO5：サービス・料理 | 46問 | 嗜好、澱、注ぐ量、酸・塩・うま味、酩酊時の説明 |
| 記述式 | 10問 | 小問ごとの配点、1点ごとの採点観点、模範解答の因果関係 |
| 関連用語 | 2項目 | アルヴァリーニョ、ロウレイロの品種説明 |

全1100問の件数・ID・選択肢・正答対応・重複表現を検査し、正答と誤答理由を中心に内容を点検しました。四択の「別の論点だから誤り」という汎用説明は、設問の条件と仕組みに沿った説明へ置き換えています。

## 正答を訂正した16問

正答位置のA〜Dを維持し、正しい内容の選択肢と対応する解説をその位置へ移しました。問題IDも維持しています。

| 問題ID | 論点 | 訂正後の正答 |
|---|---|---|
| LO1-116 | コルクの酸素透過 | コルクごとに酸素透過性や密閉性がわずかに異なる |
| LO1-127 | 株仕立て | 低い樹冠が果房へ自然な日陰を作り、風に耐え、支柱費を抑えられる |
| LO1-135 | 被覆作物 | 浸食を抑え、有機物と生物多様性を高め、過剰な樹勢を競合で抑えることがある |
| LO1-147 | 遮光ネット | 果房と葉の温度を下げ、日焼けと光合成停止のリスクを減らす |
| LO2-023 | クリュ・ボージョレ | 北部の花崗岩質丘陵など、ガメイに適した特定区画から低めの収量で造られることが多い |
| LO2-030 | ラインガウ | 南向き斜面が日射を受け、川が気温を緩和し、光を反射する |
| LO2-040 | ヴィーニョ・ヴェルデ | 大西洋の影響を受ける比較的冷涼で雨の多い気候で、早めに収穫されることが多い |
| LO2-079 | ペイ・ドックIGP | 幅広い品種を使用でき、品種名表示と柔軟なブレンドが可能である |
| LO2-174 | ハウエル・マウンテン | 霧の上で日照を得やすく、水はけのよい痩せた土壌で小粒の凝縮した果実を得やすいため |
| LO3-042 | リザーヴワインとヴィンテージ差 | 不足する酸、果実味、熟成香を他年のワインで補い、ハウス・スタイルを維持できる |
| LO3-095 | トレントDOC | アルプスの高標高畑で夜間が冷涼になり、シャルドネやピノ・ノワールの酸が保持される |
| LO3-150 | 白亜質土壌 | 排水しながら冬の水分を保持し、根へ安定して供給できる |
| LO4-120 | 若い型と熟成型の酒精強化マスカット | 若い型は新鮮なブドウと花の香り、熟成型はレーズン、キャラメル、ナッツの香りが中心 |
| LO4-178 | ラザグレンの樽位置 | 高温が化学反応と蒸発を速め、濃縮と熟成香の発達を進める |
| LO5-040 | 個人の好みと感受性 | 同じ品質のワインでも、甘味、酸、タンニン、香りなどへの好みや反応が人によって異なるため |
| LO5-163 | 澱の説明 | 自然な熟成で色素とタンニンが沈殿したもので、デカンティングして提供できる |

16件の指摘と修正理由は `ContentReviews/review_issues.json` に記録しました。`resolved` は今回の修正対応を示し、外部専門家の承認を意味しません。

## 記述式と関連辞書

記述式は、要求する説明と配点・採点基準が一致するように整理しました。春霜対策では説明すべき対策を明示し、放射霜と逆転層などの条件を補いました。産地比較では残糖やアルコールなどの前提を示し、バローロでは標高・方位から成熟へつながる説明を明確にしました。フィノの辛口は発酵完了、フロールによるグリセロール消費は質感として説明を分け、トカイ・アスーの浸漬対象も修正しました。

辞書2項目には、LO2-040の旧誤正答だった凍結収穫の説明が転用されていました。産地委員会CVRVVの品種情報を確認し、各品種の香り、構成、適した気候へ訂正しました。

## 正本・生成物・変更履歴

- 四択の新正本：`QuestionSources/wset_level3_original_questions_1100_v8.xlsx`
- 記述式の正本：`QuestionSources/wset_level3_written_questions.json`
- 辞書の正本：`ReferenceSources/wset_reference_master.xlsx`
- 全変更の項目別before/after・理由・参照資料：`ContentReviews/question_revision_2026-09-14.json`
- 正答訂正の指摘ログ：`ContentReviews/review_issues.json`
- 四択・記述式・辞書・地図の参照ハッシュ・レビュー依頼パケットを正本から再生成

Excelでは「問題集」が現行本文、「v8改訂概要」が今回の168問の変更一覧です。「レビュー対象」の130問も現行本文に同期しました。「全問監査」「選択肢差分」「選択肢監査概要」「誤答レビュー概要」「ReviewData」等はv7以前の履歴として残し、READMEで区別しました。v6・v7の元ファイルは保持しています。

## 検証結果

- `make verify`：61テスト成功。各生成パック、レビュー依頼、AI採点評価用fixture、無料コンテンツ定義の検証も成功。
- その後のExcelの版表示・レビュー一覧更新と改行整備に対し、生成物を更新し `make check-generated` を再実行して成功。
- 正答訂正16問と辞書2項目は、旧内容で失敗する回帰テストを確認してから修正。
- 四択1100問は意図した改訂内容と一致。ID・LO・正答位置・レビュー状態を保持。正答位置はA〜D各275問。
- 記述式10問は小問の配点合計、採点基準内の1点項目の合計が各配点と一致。問題ID・採点項目ID・総配点・目安時間を保持。
- LibreOfficeでExcelを再計算。問題集95個・辞書4個の数式を保持し、計算済み値とセルエラー0件を確認。
- 辞書の本文修正は2項目に限定し、出典1件を追加。その他の用語・格付けの値を保持。
- `git diff --check`：成功。

## 確認範囲の限界

AI支援による改訂であり、外部専門家の承認状態は付けていません。既存の要レビュー130問と記述式の外部レビュー待ち状態を保持しています。全地域の現行法規を条文単位で再確認したものではありません。

このWindows/WSL環境ではXcodeが利用できないため、iOSのビルド・実機表示・UIテストは未実施です。過去の回答履歴を再採点する処理は追加していないため、上記16問の過去の学習結果は新版で再確認する余地があります。

## 主な参照資料

確認日：2026-09-14。各問題の対応資料はExcelのコメントと変更記録JSONにも記載しています。

| 確認した論点 | 一次資料 |
|---|---|
| Level 3の学習範囲・試験構成 | [WSET Level 3 Award in Wines](https://www.wsetglobal.com/qualifications/wset-level-3-award-in-wines) |
| コルクと酸素透過 | [Australian Wine Research Institute 技術資料](https://www.awri.com.au/files/attachment/248-october-2020-technical-review-godden/) |
| 被覆作物・土壌管理 | [WSET：regenerative viticulture](https://www.wsetglobal.com/knowledge-centre/blog/2025/an-introduction-to-regenerative-viticulture) |
| ラインガウ、モーゼルの地形・気候 | [VDP：Rheingau](https://www.vdp.de/en/the-wines/the-vdpregions/rheingau)、[VDP：Mosel](https://www.vdp.de/en/the-wines/the-vdpregions/mosel) |
| ハウエル・マウンテンの昼夜温と土壌 | [Howell Mountain Vintners & Growers Association](https://howellmountain.org/media-trade/facts-and-faqs/) |
| ヴィーニョ・ヴェルデの品種 | [CVRVV：White grape varieties](https://www.vinhoverde.pt/en/grape-varieties/white-wines/) |
| ボージョレのガメイとテロワール | [Inter Beaujolais：Gamay](https://www.beaujolais.com/en/cepage/gamay/)、[Moulin-à-Vent](https://www.beaujolais.com/appellation/moulin-a-vent/) |
| ペイ・ドックの品種選択 | [Pays d'Oc IGP](https://www.paysdoc-vin.com/the-grape-varieties/?lang=en) |
| シャンパーニュの土壌、トレントの山地 | [Comité Champagne](https://www.champagne.fr/en/about-champagne/the-champagne-terroir/champagne-and-its-soil)、[Trentodoc](https://www.trentodoc.com/en/territory-and-denomination/) |
| カバの熟成・甘味区分 | [D.O. Cava](https://www.cava.wine/en/categories-types/) |
| VOS/VORS、フィノとフロール | [Consejo Regulador：Special categories](https://www.sherry.wine/sherry-wine/special-categories)、[Fino](https://www.sherry.wine/sherry-wine/dry-sherry-wines/fino)、[Biological ageing](https://www.sherry.wine/news/biological-ageing-sherry-veil-flor-part-1) |
| 料理の酸・塩・うま味 | [WSET：Food matching](https://www.wsetglobal.com/knowledge-centre/blog/2020/december/21/winter-wine-and-food-matching)、[Understanding acidity](https://www.wsetglobal.com/knowledge-centre/blog/2026/understanding-acidity-in-wine) |
| トカイ・アスーの浸漬 | [Wines of Tokaj：In the cellar](https://www.winesoftokaj.hu/en/the-aszu/in-the-cellar) |
| アルコール過量摂取時の対応 | [NIAAA：Understanding the Dangers of Alcohol Overdose](https://www.niaaa.nih.gov/publications/brochures-and-fact-sheets/understanding-dangers-of-alcohol-overdose) |
