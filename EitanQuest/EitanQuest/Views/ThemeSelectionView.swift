import SwiftUI
import SwiftData

/// テーマ（意味グループ）別に出題・閲覧するための一覧画面
private enum ThemeDestination: Hashable {
    case quiz(WordTheme)
    case browse(WordTheme)
}

struct ThemeSelectionView: View {
    @Query private var words: [Word]

    var body: some View {
        NavigationStack {
            List {
                Section {
                    ForEach(WordTheme.allCases) { theme in
                        let themeWords = wordsFor(theme)
                        if !themeWords.isEmpty {
                            NavigationLink(value: ThemeDestination.quiz(theme)) {
                                ThemeRow(theme: theme, words: themeWords)
                            }
                            .swipeActions(edge: .trailing) {
                                NavigationLink(value: ThemeDestination.browse(theme)) {
                                    Label("単語一覧", systemImage: "list.bullet")
                                }
                                .tint(theme.tint)
                            }
                        }
                    }
                } footer: {
                    Text("テーマを選ぶと、そのテーマの単語だけでクイズができます。左スワイプで単語一覧を表示。")
                }
            }
            .navigationTitle("テーマ")
            .navigationDestination(for: ThemeDestination.self) { destination in
                switch destination {
                case .quiz(let theme):
                    QuizView(words: wordsFor(theme), title: theme.displayName)
                case .browse(let theme):
                    WordListView(words: wordsFor(theme), title: "\(theme.displayName) 一覧")
                }
            }
        }
    }

    private func wordsFor(_ theme: WordTheme) -> [Word] {
        words.filter { $0.theme == theme }
    }
}

private struct ThemeRow: View {
    let theme: WordTheme
    let words: [Word]

    private var learnedCount: Int {
        words.filter(\.isLearned).count
    }

    private var progress: Double {
        words.isEmpty ? 0 : Double(learnedCount) / Double(words.count)
    }

    var body: some View {
        HStack(spacing: 14) {
            Image(systemName: theme.symbolName)
                .font(.title3)
                .foregroundStyle(.white)
                .frame(width: 40, height: 40)
                .background(theme.tint.gradient)
                .clipShape(RoundedRectangle(cornerRadius: 10))

            VStack(alignment: .leading, spacing: 6) {
                Text(theme.displayName)
                    .font(.headline)
                ProgressView(value: progress)
                    .tint(theme.tint)
                Text("\(learnedCount) / \(words.count)語 学習済み")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 4)
    }
}

#Preview {
    ThemeSelectionView()
        .modelContainer(for: Word.self, inMemory: true)
}
