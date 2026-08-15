# Interactive Email Report Demo

メール本文内で指標を切り替えられる、週次レポートの検証用サンプルです。

- AMP for Email 対応環境: `Revenue` / `Orders` / `Margin` のボタンで棒グラフを切り替え
- 非対応環境: 通常の HTML またはプレーンテキストを表示
- ブラウザ: 同じデータを使ったインタラクティブ・プレビューを表示

外部サービスや Python パッケージには依存しません。生成・検査・テストは Python
標準ライブラリだけで実行できます。

## 生成物

```text
dist/
├── weekly-report.eml          # 3パート構成の送信可能なMIMEメール
├── weekly-report.amp.html     # Gmail Playground貼り付け用
├── weekly-report.html         # 通常HTMLフォールバック
├── weekly-report.txt          # プレーンテキスト版
└── browser-preview.html       # ローカル操作確認用
```

## ローカルで試す

```bash
cd /home/kazumasa/projects/interactive-email-demo
python3 scripts/build_email.py
python3 scripts/check_email.py dist/weekly-report.eml
python3 -m unittest discover -s tests -v
python3 -m http.server 8000 --directory dist
```

ブラウザで `http://localhost:8000/browser-preview.html` を開くと、メールに入る
指標切替をすぐ確認できます。

## GmailでAMP版を試す

1. `python3 scripts/build_email.py` を実行します。
2. `dist/weekly-report.amp.html` を
   [AMP Playground](https://playground.amp.dev/?runtime=amp4email) に貼り付けて検証します。
3. 自分の送信元を使う場合、Gmail の
   `設定 > 全般 > 動的メール > デベロッパー向け設定` で送信元を許可します。
4. 下記の環境変数を設定し、明示的に送信スクリプトを実行します。

```bash
export SMTP_HOST='smtp.example.com'
export SMTP_PORT='587'
export SMTP_USERNAME='reporter@example.com'
export SMTP_PASSWORD='set-this-outside-git'

python3 scripts/send_email.py \
  --eml dist/weekly-report.eml \
  --from-address reporter@example.com \
  --to-address your-account@gmail.com
```

`--dry-run` を付けると接続も送信も行わず、ヘッダーとMIME構造だけを確認します。
パスワードを引数や設定ファイルへ書かず、必ず環境変数から渡してください。

## 実運用前の注意

- `sample-report.json` の `dashboard_url` と送信元・宛先を実在する値へ変更します。
- AMPパートは通常HTMLより前に入っています。非対応環境では通常HTMLへフォールバックします。
- Gmailで登録外の送信元をテストする場合は、受信側のデベロッパー向け設定が必要です。
- 本番配信には送信元ごとのGoogle登録と、SPF・DKIM・DMARC・TLSなどの要件があります。
- AMPメールを転送するとAMPパートが除かれるため、テストは受信者へ直接送信します。
- メール内には機密データを直接埋め込まず、閲覧権限が必要な詳細は認証済み
  ダッシュボードへリンクする設計を推奨します。

## データを差し替える

`sample-report.json` をコピーして編集し、次のように指定します。

```bash
python3 scripts/build_email.py --data my-report.json --output-dir dist/my-report
```

各 `metrics[].id` は小文字英数字とハイフン、`values[].value` は0以上の数値にします。

