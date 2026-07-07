import SwiftUI

struct SettingsView: View {
    @AppStorage("autoPronounceEnabled") private var autoPronounceEnabled = true
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Toggle("出題時に自動で発音する", isOn: $autoPronounceEnabled)
                        .accessibilityIdentifier("autoPronounceToggle")
                } footer: {
                    Text("問題が表示されたときに単語を自動で読み上げます。「発音を聞く」ボタンでいつでも聞き直せます。")
                }
            }
            .navigationTitle("設定")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("閉じる") { dismiss() }
                }
            }
        }
    }
}

#Preview {
    SettingsView()
}
