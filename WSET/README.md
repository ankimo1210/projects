# WSET学習

日本語で学習できる、個人利用向けのオフライン WSET Level 3 学習アプリです。問題データと学習履歴は端末内に保存されます。

## 主な機能

- 自作した日本語4択候補1100問（全問が外部専門家レビュー待ち）
- 採点基準付きの開発用記述式候補10問（外部人手レビュー待ち）、入力下書き、過去回答・得点推移、不足用語復習
- 10問・20問・50問の四択学習セッション
- 国→産地の階層、国際・準国際・地域品種、ワイン区分、知識領域、難易度、思考スキル別の重点学習
- 期限、誤答、弱点、未学習、LOの偏りを使う「今日の学習」と詳細弱点分析
- 680語の用語辞書（日本語、可能な範囲の英語・フランス語、別名、ラベル、関連問題）
- 用語の期限付きSRSと双方向カード
- 問題詳細と解答後の用語注釈、用語からの重点学習
- ボルドー、ブルゴーニュ、シャンパーニュの格付け一覧
- 50問ミニ模試と、公開済み問題が揃った場合の四択50問＋記述4問・120分の理論模擬試験
- フランス主要10産地のオフライン概略マップ、関連問題・用語、出典付き9軸の2産地比較
- ブックマーク、間違い復習、期限付き復習、学習統計
- WSET Level 3 SAT形式のテイスティング記録
- 2本比較のブラインド練習と、中断再開できる30分テイスティング試験
- テイスティング語彙候補、記録の編集・削除、JSON／CSV書き出し
- 模擬試験履歴、LO別結果、スコア推移グラフ
- SRS復習通知
- 学習履歴・記述採点・用語SRS・テイスティング・模試のJSONバックアップ／復元
- 無料体験＋StoreKit 2の買い切りPro、購入復元、オフライン権利キャッシュ

表示言語と問題言語は日本語に固定しています。

## 問題データ

問題の正本は `QuestionSources/wset_level3_original_questions_1100_v6.xlsx` です。次のコマンドでアプリ用JSONを生成します。

```sh
python3 scripts/build_question_pack.py
```

生成先は `WSET/QuestionData/question_pack.json` です。`wset_l3_question_corpus/` は過去の調査結果を参照用に残していますが、アプリの問題データには使用しません。

四択1100問の`reviewStatus`は現時点ですべて`ai_reviewed_pending_expert`です。このうち130問は`needsReview: true`で、商用リリース前の外部専門家レビューが未完了です。生成物には`distributionStatus: development_only`が付き、ReleaseビルドのImporterは読み込みません。全問が正本上で`公開`となるまではRelease配布できません。収録数は公開品質を保証するものではありません。

外部レビューは[`docs/content-review-workflow.md`](docs/content-review-workflow.md)に従い、依頼対象ハッシュ、指摘、修正、正本の承認状態を追跡します。次のコマンドで現在の四択1100問、記述式10問、地図・比較素材に結び付いた依頼パケットを生成します。

```sh
python3 scripts/build_content_review_packet.py
```

公開時は担当者・確認日だけでなく、レビュー時点の内容ハッシュとの一致を必須にしています。承認後に内容が変わった項目や、`ContentReviews/review_issues.json`に未解決指摘がある状態では商用ゲートを通過できません。

記述式問題の正本は `QuestionSources/wset_level3_written_questions.json` です。

Release配布用は、人手レビュー情報が揃った`published`問題だけを生成します（現時点では0問です）。

```sh
python3 scripts/build_written_question_pack.py
```

Debug開発用には、外部レビュー待ちの候補10問を明示的に含めます。生成物には`distributionStatus: development_only`が付き、ReleaseビルドではImporterが読み込みません。

```sh
python3 scripts/build_written_question_pack.py --include-pending-for-development
```

生成先は `WSET/QuestionData/written_question_pack.json` です。レビュー状態・担当者・日時、配点と採点基準の合計、関連用語ID、メタデータ、参照パック依存ハッシュ、決定的出力を生成時に検証します。候補10問はすべて`pending_external_review`で、内容・配点の外部人手レビュー待ちです。

## 用語・格付けデータ

用語辞書と格付けの正本は `ReferenceSources/wset_reference_master.xlsx` です。次のコマンドでアプリ用JSONを生成します。

同義・表記違い候補の判定は`ReferenceSources/glossary_term_id_review.json`へ記録します。実正規化規則で検出した9組はすべて専門家レビュー待ちで、現時点のID移行は0件です。承認済み統合だけが生成物の`termIDMigrations`へ入り、既存の用語SRS・バックアップ履歴は[`用語ID統合レビューと履歴移行契約`](docs/glossary-term-id-migration.md)に従って合流します。

```sh
python3 scripts/build_reference_pack.py
```

生成先は `WSET/ReferenceData/reference_pack.json` です。問題データの構造化タグと本文を照合し、用語と関連問題を相互にリンクします。

## 産地マップデータ

産地、概略位置、問題・用語参照の正本は `ReferenceSources/wset_region_map_master.json`、自作ベクター地図は `ReferenceSources/RegionMaps/` です。

```sh
python3 scripts/build_region_map_pack.py
```

生成先は `WSET/MapData/region_map_pack.json` と `WSET/Assets.xcassets/RegionMaps/` です。表示位置は学習用の概略で、法的境界や正確な縮尺を表しません。

## 課金と任意オンライン機能

ローカルStoreKitテスト商品は `WSET/Configuration.storekit` の `pro_lifetime`（Non-Consumable）です。実価格はStoreKitから取得し、App Store Connect側で確定します。バックアップと購入復元は有料壁にしません。

無料範囲は `WSET/FreeContentManifest.json` の固定IDで管理し、四択100問（LO1〜5を各20問）、11カテゴリに分散した用語60語、フランス産地マップを収録します。格付け一覧は用語辞書とは独立した基礎資料として無料で閲覧できます。記述式は無料枠のIDを1問分予約していますが、現時点のRelease配布用`published`パックは0問のため利用できません。人手レビュー後にそのIDが公開された時点で無料枠へ加わります。データの並び替えや追加だけで無料内容は変わりません。

iCloudとAI記述添削は条件付きの技術検証です。iCloud entitlement・containerと実バックエンドは未設定で、既定状態では外部転送しません。ReleaseのAI送信先はInfo.plistから供給する運営者管理HTTPSバックエンドだけに限定し、利用者は変更できません。Debugだけ開発用URLを指定できます。どちらも送信先別の明示同意を必須とし、APIキーをアプリへ埋め込みません。
本番有効化の保持・削除・競合解決・セキュリティ条件は [`docs/online-feature-readiness.md`](docs/online-feature-readiness.md) に固定しています。

本アプリはWSET（Wine & Spirit Education Trust）と提携・承認された公式アプリではありません。

## 起動

1. `WSET.xcodeproj` をXcodeで開く。
2. Signing & Capabilitiesで自分のDevelopment Teamを選ぶ。
3. iOS 17以降の自分のiPhoneまたはSimulatorを選び、Runする。

## 検証

データ形式、SwiftData、バックアップ、Accessibility Identifierの変更規則は
[`docs/data-versioning-and-accessibility.md`](docs/data-versioning-and-accessibility.md)を参照してください。

日常の生成・データ検証は次の1コマンドへ集約しています。

```sh
make verify
```

App Store archive前は、日常検証とは別のfail-closedゲートを実行します。

```sh
make release-check
```

これは四択・記述式の公開状態、地図出典、App Store手動チェックリスト、プライバシーポリシー確定を検査します。現時点では専門家レビューと商用手続きが未完了のため、`NO-GO`で終了することが正しい状態です。

個別コマンドは以下です。

```sh
python3 -m unittest \
  scripts.tests.test_build_question_pack \
  scripts.tests.test_build_reference_pack \
  scripts.tests.test_build_written_question_pack \
  scripts.tests.test_build_region_map_pack \
  scripts.tests.test_build_content_review_packet \
  scripts.tests.test_validate_ai_review_fixture \
  scripts.tests.test_validate_free_content_manifest \
  scripts.tests.test_validate_release_readiness
python3 scripts/build_question_pack.py --check
python3 scripts/build_reference_pack.py --check
python3 scripts/build_written_question_pack.py --check --include-pending-for-development
python3 scripts/build_region_map_pack.py --check
python3 scripts/build_content_review_packet.py --check
python3 scripts/validate_ai_review_fixture.py
python3 scripts/validate_free_content_manifest.py
python3 scripts/validate_release_readiness.py  # App Store archive前のみ（未完了なら非0終了）

xcodebuild -project WSET.xcodeproj -scheme WSET \
  -sdk iphonesimulator -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  test CODE_SIGNING_ALLOWED=NO
```

iOSテストは`make test-unit`（単体）と`make test-ui`（UI）、すべてまとめて実行する場合は`make test`も利用できます。UI自動テストに加え、リリース前にライト／ダーク、最大Dynamic Type、VoiceOver、機内モード、バックグラウンド復帰を実機で確認します。
