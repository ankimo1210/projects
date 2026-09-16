# CruNote for WSET リリース手順

## バージョン1.0.1（2026-09-16 提出準備）

- バージョン: `1.0.1`、ビルド: `2`
- バックアップ復元時の回答保護とテイスティング模試の破棄処理を修正。
- iOSテスト: 153件成功、実機限定13件スキップ、失敗0件。Python: 58件成功。
- App Store Connectへ更新内容を保存済み。審査承認後の自動リリースを設定。
- 実機向けReleaseビルド・Archive・Cloud Managed Apple Distribution署名に成功。2026-09-16 13:16 JSTにビルド2のアップロードが成功。
- 保存済みCruNote APIキーはApp Manager権限のためクラウド署名に使えず、書き出しとアップロードにはXcodeの既存アカウントを使用。
- 2026-09-16の確認では、1.0は承認済みだが配信対象から削除されていた。修正版を公開する際に日本向け配信の再設定が必要。
- Sandbox購入・復元確認とストア製品ページ確認が未完了のため、商用ReleaseゲートはNO-GO。アーカイブは提出準備用で、審査提出・本番公開は未実施。

### このバージョンの最新情報

・バックアップの復元時に、端末上の新しい回答が古い回答で上書きされる問題を修正しました。
・テイスティング模試を破棄したあと、新しい模試が正しい制限時間と空の回答で開始されるように修正しました。

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
