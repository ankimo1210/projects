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
                Text("iCloudへの手動バックアップ転送やAI添削は、対応状況と送信内容を表示し、利用者が明示的に操作・同意した場合だけ使用します。利用できない場合もローカル学習は継続できます。")
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
                Text("問題、解説、採点基準、地図は独自に作成した学習素材です。自己採点と模擬試験結果は公式の合否や採点結果を保証しません。")
            }
            Section("購入") {
                Text("Proは買い切り型の商品です。実際の価格は購入画面にApp Storeから表示される金額が優先されます。購入の復元とデータのバックアップは無料で利用できます。")
            }
        }
        .navigationTitle("本アプリについて")
        .navigationBarTitleDisplayMode(.inline)
    }
}
