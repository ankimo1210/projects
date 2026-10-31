# Windows の Citrix App Protection 確認結果

確認日: 2026-10-31

このWindows環境にはCitrix App Protectionが導入されている。
確認時点のバージョンは26.3.10.54で、サービスと関連ドライバー3つはすべて停止していた。
導入済みであることと、保護が稼働していることを区別する。

| コンポーネント | 観測した状態 | 起動設定 |
|---|---|---|
| appprotectionsvc | Stopped | Manual |
| ctxapdriver | Stopped | Manual |
| ctxapinject | Stopped | Manual |
| ctxapusbfilter | Stopped | Manual |

Windowsのサービス・ドライバー情報とCitrixの製品情報を読み取って確認した。
設定変更、サービスの停止操作、保護の回避操作は行っていない。
同日の作業ではCitrix画面のスクリーンショットも取得できた。

## 次回の判断

- この表は確認時点の状態であり、常時無効という意味ではない。
- App Protectionの対象リソースを開くとサービスが起動する場合がある。
  再接続や別の接続先での作業時は状態を確認し直す。
- 接続先の管理設定であるAppProtectionScreenCaptureRequiredの値は未確認。
  ローカルの停止状態だけから管理側ポリシーを断定しない。
- Mac側の導入・稼働状態は未確認。Windowsでの結果をMacへ流用しない。

再確認には、次の読み取り専用コマンドを使える。

~~~powershell
sc.exe query appprotectionsvc
sc.exe query ctxapdriver
sc.exe query ctxapinject
sc.exe query ctxapusbfilter
~~~

## 公式資料

- [導入・稼働状態の確認](https://docs.citrix.com/us/en/citrix-workspace-app/app-protection/troubleshoot.html)
- [停止状態と保護対象リソースによる起動](https://docs.citrix.com/us/en/citrix-workspace-app/app-protection/configure/disable-app-protection.html)
- [AIツールによる画面取得への保護](https://docs.citrix.com/us/en/citrix-workspace-app/app-protection/app-protection-blocking-unauthorized-ai.html)
