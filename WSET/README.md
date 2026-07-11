# WSET学習

日本語で学習できる、個人利用向けのオフライン WSET Level 3 学習アプリです。問題データと学習履歴は端末内に保存されます。

## 主な機能

- 自作した日本語4択問題300問
- 10問・20問・50問の四択学習セッション
- 50問の模擬試験とLearning Outcome別の結果
- ブックマーク、間違い復習、期限付き復習、学習統計
- WSET Level 3 SAT形式のテイスティング記録
- 2本比較のブラインドテイスティング練習
- テイスティング記録の編集・削除
- 模擬試験履歴、LO別結果、スコア推移グラフ
- SRS復習通知
- 学習履歴・テイスティング記録のJSONバックアップ／復元

表示言語と問題言語は日本語に固定しています。

## 問題データ

問題の正本は `QuestionSources/wset_level3_original_questions_300_v2.xlsx` です。次のコマンドでアプリ用JSONを生成します。

```sh
python3 scripts/build_question_pack.py
```

生成先は `WSET/QuestionData/question_pack.json` です。`wset_l3_question_corpus/` は過去の調査結果を参照用に残していますが、アプリの問題データには使用しません。

## 起動

1. `WSET.xcodeproj` をXcodeで開く。
2. Signing & Capabilitiesで自分のDevelopment Teamを選ぶ。
3. iOS 17以降の自分のiPhoneまたはSimulatorを選び、Runする。

## 検証

```sh
python3 -m unittest scripts.tests.test_build_question_pack
python3 scripts/build_question_pack.py --check

xcodebuild -project WSET.xcodeproj -scheme WSET \
  -sdk iphonesimulator -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  test CODE_SIGNING_ALLOWED=NO
```
