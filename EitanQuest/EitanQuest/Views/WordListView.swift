import SwiftUI

/// カテゴリ内の全単語を眺められる予習・復習用の一覧画面（クイズより前の下見用途）
struct WordListView: View {
    let words: [Word]
    let title: String

    private var sortedWords: [Word] {
        words.sorted { $0.headword.localizedCaseInsensitiveCompare($1.headword) == .orderedAscending }
    }

    var body: some View {
        Group {
            if words.isEmpty {
                ContentUnavailableView(
                    "単語がありません",
                    systemImage: "text.book.closed",
                    description: Text("このカテゴリにはまだ単語がありません。")
                )
            } else {
                List(sortedWords, id: \.id) { word in
                    WordListRow(word: word)
                }
            }
        }
        .navigationTitle(title)
        .navigationBarTitleDisplayMode(.inline)
    }
}

private struct WordListRow: View {
    let word: Word

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(alignment: .firstTextBaseline) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(word.headword)
                        .font(.headline)
                    if !word.phonetic.isEmpty {
                        Text(word.phonetic)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
                Spacer()
                Button {
                    SpeechService.shared.speak(word.headword)
                } label: {
                    Image(systemName: "speaker.wave.2.fill")
                }
                .buttonStyle(.borderless)
            }

            Text(word.meaning)
                .font(.subheadline)

            VStack(alignment: .leading, spacing: 2) {
                Text(word.exampleSentence)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                if !word.exampleSentenceJa.isEmpty {
                    Text(word.exampleSentenceJa)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding(.vertical, 4)
    }
}

#Preview {
    NavigationStack {
        WordListView(words: [], title: "プレビュー")
    }
}
