# App Store商用リリースチェックリスト

## 現在の状態（2026-08-23）

**2026-08-23にリリース済み。** バージョン1.0は`READY_FOR_SALE`。App Review自体は
2026-07-29に完了していたが、リリース方法が手動のため約3週間`PENDING_DEVELOPER_RELEASE`で
止まっていた。App Store Connect APIからリリース要求を送って解消した
（version id `ac7ecb81-d346-4971-9101-a18b62ffe228`）。

ストア掲載への反映は最大24時間かかるため、`READY_FOR_SALE`になった直後は
iTunes Lookup APIが0件を返す。

### 価格の実態

アプリ本体は**無料**で、¥1,500／¥5,000は**IAP `pro_lifetime`の価格**。
リリース時点でIAPは`APPROVED`だが、価格スケジュールが入っておらず¥5,000一本だった。
当初の「発売価格¥1,500」を復活させるため、リリース直前に次のスケジュールを適用した。

| 期間 | 価格 | proceeds |
| ---- | ---- | -------- |
| 〜2026-09-21 16:00 JST | ¥1,500 | ¥1,275 |
| 2026-09-21 16:00 JST〜 | ¥5,000 | ¥4,250 |

境界はApple内部では米西部時間の0時で保持されるため、JSTでは同日16:00に切り替わる。
proceedsが85%なのはSmall Business Programの手数料15%が効いているため。

`inAppPurchasePriceSchedules`は区間の隙間も重なりも許さない。前の価格の`endDate`と
次の価格の`startDate`は**同じ日付**にする（`endDate`は排他）。1日ずらすと
`ENTITY_ERROR.INVALID_INTERVAL`で弾かれる。

- [x] App Store Connectへ`CruNote for WSET`を日本語・iOSアプリとして登録（Apple ID: `6792630743`、Bundle ID: `com.ankimo.WSET`、SKU: `crunote-wset-ios`）
- [x] 四択1100問と記述式10問をReleaseパックへ収録
- [x] `pro_lifetime`をNon-ConsumableとしてApp Store Connectへ登録（Apple ID: `6792636673`）
- [x] 発売価格¥1,500、通常価格¥5,000（2026-08-17開始）をApp Store Connectで確定し、アプリへ直書きしない
- [x] **価格スケジュールの再確認（2026-08-23）**: リリース直前の実測で、IAPは¥5,000一本でスケジュールが無い状態だった。¥1,500（〜2026-09-21）→¥5,000へ再設定して公開した
- [x] App Store Connectの有料アプリ契約へ署名
- [x] 売上受取用の銀行口座をApp Store Connectへ登録し、「有効」を確認
- [x] App Store ConnectでW-8BENと外国人ステータス証明を提出し、両方「有効」を確認

無料Offer Code `NYANCO Free Access`は全利用資格・全175地域を対象に作成済み。本番カスタムコード`NYANCO`は、アプリが配信準備完了となり`pro_lifetime`がApp Reviewで承認された後に発行する。

自動検証は2026-07-21に完了（Python 58件、iOS単体117件、UI 28件。うち`StoreKitConfigurationTests` 9件、`R6UITests` 9件。すべて成功）。以下はStoreKit実取引または実機Sandboxでの最終確認待ち。

`StoreKitTest`による実取引自動化は、Xcode 26.6・iOS 26.5 Simulatorでは`SKInternalErrorDomain Code=3`が発生して利用できない。2026-07-30に実機（iPhone 16 Pro / iOS 26.5.2、USB接続）で再検証し、原因を切り分けた。

- 実機では`SKTestSession`が完全に動作する。`resetToDefaultState`・`clearTransactions`・`disableDialogs`・`buyProduct`・`approveAskToBuyTransaction`・`refundTransaction`・`setSimulatedError(forAPI:)`のすべてが成功する。`Code=3`はSimulator固有の制約だった。
- schemeの`StoreKitConfigurationFileReference`のパスが`../WSET/Configuration.storekit`で、実体を指していなかった。`../../../WSET/Configuration.storekit`へ修正すると、実機では`SKTestSession`なしでも`¥1,500`／`JPY`／storefront`JPN`が適用される。修正前は既定スタブの`$9.99`／`USD`／`USA`が返っており、これが前回「設定ファイルが読まれない」と記録した現象の原因。
- Simulatorはパス修正後も`$9.99`のままで設定ファイルを読まない。購入フローの検証はSimulatorでは不可能で、実機が必要。
- `xcrun simctl`にStoreKit設定を注入するサブコマンドはなく、CLIからの回避手段はない。

実機検証は`DeviceStoreKitFlowTests`（10件）と`DeviceEntitlementPersistenceTests`（3件）として自動化した。いずれもSimulatorでは`XCTSkip`するため、`make test-unit`は緑のまま（130件中13件スキップ）。実機での実行は次のコマンド。

```sh
xcodebuild test -project WSET.xcodeproj -scheme WSET \
  -destination 'platform=iOS,id=<device-udid>' \
  -only-testing:WSETTests/DeviceStoreKitFlowTests \
  -only-testing:WSETTests/DeviceEntitlementPersistenceTests \
  -allowProvisioningUpdates -parallel-testing-enabled NO
```

`DeviceEntitlementPersistenceTests`は実機のKeychainとディスク上のSwiftDataストアを使うため、モック版（`StoreKitConfigurationTests`）では検証できないハードウェア依存部分を補完する。

残存リスク（意図的に受容）:

- オフライン確認は、実機Keychainへの永続と「StoreKitに到達できないときにキャッシュ済み権利を維持する」経路で検証しており、実際に機内モードで電波を落とした起動は未実測。アプリから見た失敗経路は同一なため差分はないと判断した。
- 返金・取消後の権利失効はApple Sandboxではテスターから返金を発行できないため、実機の`SKTestSession.refundTransaction`（`testRefundedPurchaseRevokesProAccess`・`testRefundedPurchaseIsNotRestorable`）と単体テスト`testRevocationUpdateClearsVerifiedRightAndCache`で代替検証している。

- [x] StoreKit Configurationで成功、キャンセル、保留、復元を確認（実機`DeviceStoreKitFlowTests`で自動化、2026-07-30に13件成功）
- [ ] Sandboxで購入、返金・取消後の権利、再インストール後の復元を確認
- [x] オフライン起動時に検証済み買い切り権利が保持されることを確認（実機Keychain永続＋StoreKit到達不能時のフォールバックで確認）
- [x] 無料ユーザーの進捗を購入後も保持することを確認（実機・ディスク永続・実購入で確認）
- [x] WSET非提携、独自教材、自己採点である旨をストア説明へ記載
- [x] プライバシーポリシーの運営者名・連絡先・保持期間を確定し、GitHub Pagesへ公開
- [x] App Privacy回答とアプリ内表示を一致させ、App Store Connectで公開
- [x] 地図素材が自作図・参照のみの独自要約であること、利用条件とWSET非提携表記を確認
- [x] Small Business Programの対象条件を確認し、関連アカウントなし・基準額以内として申請。2026-08-15にAppleが承認し、手数料率は15%（メール `Welcome to the App Store Small Business Program.`）
- [x] 日本語スクリーンショット、説明文、サポートURLを用意
- [x] App Store Connectで「このバージョンをリリース」を実行（2026-08-23、API経由。`PENDING_DEVELOPER_RELEASE`→`READY_FOR_SALE`）
- [ ] 日本のApp Store製品ページで、説明・スクリーンショット・サポートURL・IAP価格¥1,500の表示を確認（反映まで最大24時間）
