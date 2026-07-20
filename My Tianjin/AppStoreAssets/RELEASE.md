# My Tianjin リリース手順

## 現在のリリース

- バージョン: `1.0 (2)`
- App Store Connect提出日時: 2026年7月20日 13:28 JST
- 提出ID: `3974f127-9db7-4564-aec4-0089808673a0`
- 提出時ステータス: `審査待ち`
- 価格: 無料
- 配信地域: 日本のみ
- リリース方法: App Review承認後に手動でリリース
- サポートURL: <https://ankimo1210.github.io/projects/my-tianjin/>
- プライバシーポリシー: <https://ankimo1210.github.io/projects/my-tianjin/privacy.html>

App Review専用の連絡先はApp Store Connect内で管理し、電話番号はリポジトリへ記録しない。公開用のサポートメールアドレスはサポートページとプライバシーポリシーで管理する。

## App Review承認後

1. App Store Connectの「アプリ」から「My Tianjin」を開く。
2. iOSバージョン `1.0` のステータスが承認済みであることを確認する。
3. バージョン画面の「このバージョンをリリース」を実行する。
4. ステータスが配信可能になったことを確認する。
5. 日本のApp Store製品ページで、説明、スクリーンショット、サポートURLを確認する。

手動リリースを実行しても、App Storeへの反映には時間がかかる場合がある。

## 修正依頼または却下の場合

1. App Store Connectの「App Review」で指摘内容と添付画像を確認する。
2. メタデータだけの問題か、アプリ修正が必要かを切り分ける。
3. 必要最小限の修正を行い、該当テストとReleaseビルドを再実行する。
4. アプリを修正した場合はビルド番号を増やし、新しいビルドをアップロードする。
5. App Reviewへの回答に、変更内容と確認手順を簡潔に記載して再提出する。

## 次回バージョンのチェックリスト

1. `MARKETING_VERSION` と `CURRENT_PROJECT_VERSION` を更新する。
2. 自動テストとReleaseビルドを実行する。
3. 実機または対象シミュレータで主要導線、音声、権限ダイアログを確認する。
4. 必要に応じて `AppStoreAssets/Screenshots/` と `metadata-ja.md` を更新する。
5. XcodeでArchiveを作成し、App Store Connectへアップロードする。
6. App Store Connectで新しいビルドを選択する。
7. 説明、プライバシー回答、年齢制限、配信地域、価格を再確認する。
8. バージョンを審査用に追加し、App Reviewへ提出する。
9. 承認後、手動でリリースする。

## 公開ページの更新

サポートページとプライバシーポリシーは、このリポジトリの `gh-pages` ブランチにある `my-tianjin/` からGitHub Pagesへ公開している。内容を変更した場合は、公開ページのHTTP表示とアプリ内リンクの両方を確認する。
