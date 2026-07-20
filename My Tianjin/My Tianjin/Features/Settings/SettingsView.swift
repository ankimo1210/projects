import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var speech: SpeechService
    @EnvironmentObject private var contentStore: LearningContentStore
    @AppStorage("autoSpeakCorrectAnswer") private var autoSpeakCorrectAnswer = true
    @AppStorage("speechSpeedRawValue") private var speechSpeedRawValue = SpeechSpeed.normal.rawValue
    @AppStorage("readingShowsPinyin") private var readingShowsPinyin = true
    @AppStorage("readingShowsJapanese") private var readingShowsJapanese = false
    @AppStorage("conversationShowsPinyin") private var conversationShowsPinyin = true
    @AppStorage("conversationShowsJapanese") private var conversationShowsJapanese = false
    @AppStorage("conversationAutoSpeak") private var conversationAutoSpeak = true

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

            Section("自由会話") {
                Toggle("相手の返答を自動で発音", isOn: $conversationAutoSpeak)
                Toggle("ピンインを表示", isOn: $conversationShowsPinyin)
                Toggle("日本語訳を表示", isOn: $conversationShowsJapanese)
                Text("会話生成と音声認識はAppleの端末内機能を優先します。非対応端末では内蔵シナリオに自動で切り替わり、文字入力でも練習できます。")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
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

            Section("情報") {
                NavigationLink("コンテンツの出典とライセンス") {
                    ContentCreditsView()
                }
                Link(
                    "プライバシーポリシー",
                    destination: URL(string: "https://ankimo1210.github.io/projects/my-tianjin/privacy.html")!
                )
                Link(
                    "サポート",
                    destination: URL(string: "https://ankimo1210.github.io/projects/my-tianjin/")!
                )
            }
        }
        .navigationTitle("設定")
        .onDisappear { speech.stop() }
    }
}

private struct ContentCreditsView: View {
    var body: some View {
        List {
            Section("My Tianjin") {
                Text("日本語話者向けに制作した非公式の中国語学習アプリです。HSKの実施・運営団体とは関係ありません。")
            }

            Section("新版HSK考试大纲（2025）") {
                Text("語彙の見出し、ピンイン、品詞、公式通番、レベルの参照元です。公式過去問は収録していません。")
                Link(
                    "公式シラバスを開く",
                    destination: URL(string: "https://hsk.cn-bj.ufileos.com/3.0/%E6%96%B0%E7%89%88HSK%E8%80%83%E8%AF%95%E5%A4%A7%E7%BA%B21219.pdf")!
                )
            }

            Section("CC-CEDICT") {
                Text("一部の日本語仮訳は、CC-CEDICTの英語語義を補助情報として作成しています。該当する派生コンテンツはCC BY-SA 4.0に従います。")
                Link(
                    "CC-CEDICTを開く",
                    destination: URL(string: "https://www.mdbg.net/chinese/dictionary?page=cc-cedict")!
                )
                Link(
                    "CC BY-SA 4.0",
                    destination: URL(string: "https://creativecommons.org/licenses/by-sa/4.0/")!
                )
            }

            Section("練習コンテンツ") {
                Text("例文、語順問題、読解文、作文・翻訳・口頭課題は本アプリ向けに作成した教材です。機械生成または仮訳の項目にはアプリ内でラベルを表示します。")
            }
        }
        .navigationTitle("出典とライセンス")
    }
}
