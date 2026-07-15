import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var speech: SpeechService
    @EnvironmentObject private var contentStore: LearningContentStore
    @AppStorage("autoSpeakCorrectAnswer") private var autoSpeakCorrectAnswer = true
    @AppStorage("speechSpeedRawValue") private var speechSpeedRawValue = SpeechSpeed.normal.rawValue
    @AppStorage("readingShowsPinyin") private var readingShowsPinyin = true
    @AppStorage("readingShowsJapanese") private var readingShowsJapanese = false

    private var speed: SpeechSpeed {
        SpeechSpeed(rawValue: speechSpeedRawValue) ?? .normal
    }

    var body: some View {
        Form {
            Section("音声") {
                Toggle("正解を自動で発音", isOn: $autoSpeakCorrectAnswer)
                Button {
                    let nextSpeed = speed.next
                    speechSpeedRawValue = nextSpeed.rawValue
                    speech.speak("你好，欢迎学习中文。", speed: nextSpeed)
                } label: {
                    LabeledContent("再生速度", value: speed.label)
                }
                LabeledContent("使用中の声", value: speech.voiceDescription)
                Text("端末の中国語音声を使用します。設定アプリで高品質な中国語音声を追加すると、自然さが改善する場合があります。")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            Section("読解の初期表示") {
                Toggle("ピンインを表示", isOn: $readingShowsPinyin)
                Toggle("日本語訳を表示", isOn: $readingShowsJapanese)
            }

            Section("コンテンツ") {
                LabeledContent("シラバス", value: "HSK 3.0（2025年版）")
                LabeledContent("収録レベル", value: contentStore.availableLevels.map(\.rawValue).joined(separator: " / "))
                if let version = contentStore.manifest?.contentVersion {
                    LabeledContent("データ版", value: version)
                }
                Text("機械仮訳の語義にはラベルを表示します。重要語から順に人手確認へ置き換えられる構造です。")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
        }
        .navigationTitle("設定")
        .onDisappear { speech.stop() }
    }
}
