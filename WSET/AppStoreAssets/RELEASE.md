# CruNote for WSET リリース手順

## バージョン1.0

- App Store Connect Apple ID: `6792630743`
- Bundle ID: `com.ankimo.WSET`
- IAP: `pro_lifetime`（Non-Consumable）
- 配信地域: 日本のみ
- リリース方法: App Review承認後に手動でリリース
- サポートURL: <https://ankimo1210.github.io/projects/crunote/>
- プライバシーポリシー: <https://ankimo1210.github.io/projects/crunote/privacy.html>

App Review専用の連絡先はApp Store Connect内で管理し、電話番号はリポジトリへ記録しない。公開用のサポートメールアドレスはサポートページとプライバシーポリシーで管理する。

## 提出手順

1. `make verify`とiOSテストを実行する。
2. StoreKit ConfigurationとSandboxで購入・復元・返金を確認する。
3. 実機でオフライン権利と無料版から購入後の進捗保持を確認する。
4. App Store用スクリーンショットを確認する。
5. XcodeでArchiveを作成し、App Store Connectへアップロードする。
6. App Store Connectでビルドと`pro_lifetime`を審査対象へ追加する。
7. `metadata-ja.md`の製品情報、App Privacy、年齢制限、配信地域を設定する。
8. App Reviewへ提出する。
9. 承認後、手動でリリースする。

## 公開ページ

サポートページとプライバシーポリシーは、リポジトリの`gh-pages`ブランチにある`crunote/`からGitHub Pagesへ公開する。
