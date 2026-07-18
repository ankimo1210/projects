# コンテンツ外部レビュー運用

## 1. 目的

四択、記述式、産地マップを、外部レビューの依頼から商用Release判定まで同じ証跡で追跡する。自動検証はレビュアーの専門性や判断内容を代替しない。運営者は依頼前に、担当者がWSET Level 3相当の内容、採点、地図・表示・権利条件を確認できる人物であることを別途確認する。

## 2. レビュー依頼を作る

正本を修正したら、次を実行する。

```sh
python3 scripts/build_question_pack.py
python3 scripts/build_reference_pack.py
python3 scripts/build_written_question_pack.py --include-pending-for-development
python3 scripts/build_region_map_pack.py
python3 scripts/build_content_review_packet.py
```

依頼時に次を渡す。

- `ContentReviews/external-review-request.md`
- `ContentReviews/content_review_request.json`
- `QuestionSources/wset_level3_original_questions_1100_v6.xlsx`
- `QuestionSources/wset_level3_written_questions.json`
- `ReferenceSources/wset_region_map_master.json`
- `ReferenceSources/RegionMaps/france.svg`

`content_review_request.json`の`reviewTargetHash`または`requestHash`は、レビュー対象内容の版を識別する。レビュー後に問題文、選択肢、正答、解説、模範解答、採点基準、位置、比較記述、出典またはSVGを変更した場合、古いハッシュを再利用せず、状態をレビュー待ちへ戻して依頼パケットを再生成する。

## 3. 指摘を記録する

指摘は`ContentReviews/review_issues.json`へ1件ずつ記録する。

```json
{
  "id": "CR-0001",
  "targetType": "mcq",
  "itemID": "LO1-001",
  "severity": "high",
  "status": "open",
  "finding": "指摘内容",
  "reportedBy": "外部担当者名",
  "resolution": null,
  "updatedAt": "2026-07-19"
}
```

- `targetType`: `mcq`、`written`、`region_map`
- `severity`: `low`、`medium`、`high`、`critical`
- `status`: `open`または`resolved`
- 修正後は`status`を`resolved`にし、`resolution`へ正本の変更内容を記録する
- 指摘がなかった項目はissueを作らず、正本側の承認情報を証跡にする
- `open`が1件でもある場合、商用Releaseゲートは通らない

## 4. 正本の状態を更新する

### 四択

Excelの各行について、内容確認が完了した行だけ次を設定する。`レビュー対象ハッシュ`列がなければ列を追加し、依頼パケットの同一問題IDの値をコピーする。

| 列 | 公開時の値 |
|---|---|
| `レビュー状態` | `公開` |
| `要レビュー` | `N` |
| `レビュアー` | 外部担当者の氏名または識別可能な表記 |
| `レビュー日` | `YYYY-MM-DD` |
| `レビューコメント` | 確認範囲、判断、修正内容 |
| `レビュー対象ハッシュ` | 同一IDの`reviewTargetHash` |

`AI`、`生成AI`、`AI誤答レビュー`は公開レビュアーとして認めない。指摘対応中は`レビュー状態=修正要`、`要レビュー=Y`とし、理由を残す。

### 記述式

問題ごとに次を設定する。

- `reviewStatus`: `published`
- `reviewer`: 外部担当者
- `reviewedAt`: タイムゾーン付きISO 8601日時
- `reviewedContentHash`: 同一IDの`reviewTargetHash`
- `metadata.externalReviewRequired`: `false`
- `metadata.reviewNotes`: 確認範囲、判断、修正内容

問題文だけでなく、模範解答、配点、全`rubricItems`、指示語、関連用語を確認する。理論模試を有効にするには公開済みが最低4問必要である。

### 産地マップ

`ReferenceSources/wset_region_map_master.json`の`review`を更新する。次の5範囲をすべて人手確認した場合だけ各値を`true`にする。

- `regionNamesAndPositions`: 名称、概略位置、集約対象
- `comparisonContent`: 10産地×9比較軸の内容と基準日
- `sourceLicenses`: 出典、URL、利用条件、転載有無
- `trademarkAndAttribution`: 非提携表記、商標、表示上必要な帰属
- `svgOriginality`: SVGが自作であり、第三者図版を複製していないこと

全範囲が完了したら、`status=published`、外部担当者、`YYYY-MM-DD`の確認日、依頼パケットの`regionMap.requestHash`を`reviewedContentHash`へ設定する。

## 5. 生成と判定

正本更新後に生成物を作り直す。

```sh
python3 scripts/build_question_pack.py
python3 scripts/build_reference_pack.py
python3 scripts/build_written_question_pack.py --include-pending-for-development
python3 scripts/build_region_map_pack.py
python3 scripts/build_content_review_packet.py
make verify
make release-check
```

`make verify`は正本、生成物、依頼パケット、指摘ログの整合性を検証する。`make release-check`はさらに、全四択の公開証跡、公開済み記述式4問以上、地図5範囲の承認、未解決指摘0件、App Store手動項目を要求する。

公開状態へ変えただけで証跡がない場合、または承認後に内容が変わった場合は、生成かReleaseゲートが失敗する。
