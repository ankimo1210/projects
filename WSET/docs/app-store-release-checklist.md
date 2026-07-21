# App Store商用リリースチェックリスト

- [x] App Store Connectへ`CruNote for WSET`を日本語・iOSアプリとして登録（Apple ID: `6792630743`、Bundle ID: `com.ankimo.WSET`、SKU: `crunote-wset-ios`）
- [x] 四択1100問と記述式10問をReleaseパックへ収録
- [x] `pro_lifetime`をNon-ConsumableとしてApp Store Connectへ登録（Apple ID: `6792636673`）
- [x] 発売価格¥1,500、通常価格¥5,000（2026-08-17開始）をApp Store Connectで確定し、アプリへ直書きしない
- [x] App Store Connectの有料アプリ契約へ署名
- [x] 売上受取用の銀行口座をApp Store Connectへ登録し、「有効」を確認
- [x] App Store ConnectでW-8BENと外国人ステータス証明を提出し、両方「有効」を確認

無料Offer Code `NYANCO Free Access`は全利用資格・全175地域を対象に作成済み。本番カスタムコード`NYANCO`は、アプリが配信準備完了となり`pro_lifetime`がApp Reviewで承認された後に発行する。

自動検証は2026-07-21に完了（Python 58件、iOS単体117件、UI 28件。うち`StoreKitConfigurationTests` 9件、`R6UITests` 9件。すべて成功）。以下はStoreKit実取引または実機Sandboxでの最終確認待ち。

`StoreKitTest`による実取引自動化は、Xcode 26.6・iOS 26.5 Simulatorで`SKInternalErrorDomain Code=3`が発生するため未完了。実機Sandboxテストで代替する。

- [ ] StoreKit Configurationで成功、キャンセル、保留、復元を確認
- [ ] Sandboxで購入、返金・取消後の権利、再インストール後の復元を確認
- [ ] オフライン起動時に検証済み買い切り権利が保持されることを確認
- [ ] 無料ユーザーの進捗を購入後も保持することを確認
- [x] WSET非提携、独自教材、自己採点である旨をストア説明へ記載
- [x] プライバシーポリシーの運営者名・連絡先・保持期間を確定し、GitHub Pagesへ公開
- [x] App Privacy回答とアプリ内表示を一致させ、App Store Connectで公開
- [x] 地図素材が自作図・参照のみの独自要約であること、利用条件とWSET非提携表記を確認
- [x] Small Business Programの対象条件を確認し、関連アカウントなし・基準額以内として申請（Apple審査待ち）
- [x] 日本語スクリーンショット、説明文、サポートURLを用意
