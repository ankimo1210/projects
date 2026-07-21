import SwiftUI

struct PrivacyInformationView: View {
    var body: some View {
        List {
            Section("端末内に保存する情報") {
                Text("問題の進捗、解答履歴、自由記述、テイスティング記録、用語復習状態、模擬試験結果を端末内に保存します。")
                Text("これらの学習内容を広告目的で収集・販売しません。")
            }
            Section("バックアップ") {
                Text("書き出したバックアップには自由記述とテイスティング記録が含まれます。共有先と保存場所は利用者が管理してください。")
                Text("購入権利はバックアップに含まれず、App Storeから検証・復元します。")
            }
            Section("任意のオンライン機能") {
                Text("現在のRelease版は学習データを外部サーバへ送信しません。購入と購入権利の復元はAppleのStoreKitを通じて処理されます。")
            }
            Section("公開情報") {
                Link("プライバシーポリシー", destination: URL(string: "https://ankimo1210.github.io/projects/crunote/privacy.html")!)
                Link("サポート", destination: URL(string: "https://ankimo1210.github.io/projects/crunote/")!)
            }
        }
        .navigationTitle("プライバシーとデータ")
        .navigationBarTitleDisplayMode(.inline)
    }
}

struct LegalInformationView: View {
    var body: some View {
        List {
            Section("非提携の表示") {
                Text("本アプリは独立した学習支援アプリであり、WSET（Wine & Spirit Education Trust）と提携・承認された公式アプリではありません。")
            }
            Section("学習内容") {
                Text("問題、解説、採点基準、地図は独自に作成した学習素材です。公式過去問は収録していません。自己採点と模擬試験結果は公式の合否や採点結果を保証しません。")
            }
            Section("購入") {
                Text("Proは買い切り型の商品です。実際の価格は購入画面にApp Storeから表示される金額が優先されます。購入の復元とデータのバックアップは無料で利用できます。")
            }
        }
        .navigationTitle("本アプリについて")
        .navigationBarTitleDisplayMode(.inline)
    }
}
