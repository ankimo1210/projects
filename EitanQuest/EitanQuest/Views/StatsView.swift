import SwiftUI
import SwiftData

struct StatsView: View {
    @Query private var words: [Word]

    private var totalAnswered: Int {
        words.reduce(0) { $0 + $1.correctCount + $1.incorrectCount }
    }

    private var totalCorrect: Int {
        words.reduce(0) { $0 + $1.correctCount }
    }

    private var accuracy: Double {
        totalAnswered == 0 ? 0 : Double(totalCorrect) / Double(totalAnswered)
    }

    private var learnedCount: Int {
        words.filter(\.isLearned).count
    }

    private var reviewCount: Int {
        words.filter(\.needsReview).count
    }

    var body: some View {
        NavigationStack {
            List {
                Section("全体の進捗") {
                    StatRow(title: "学習済み単語数", value: "\(learnedCount) / \(words.count)")
                    StatRow(title: "正答率", value: String(format: "%.0f%%", accuracy * 100))
                    StatRow(title: "苦手単語数", value: "\(reviewCount)")
                }

                Section("カテゴリ別の進捗") {
                    ForEach(WordCategory.allCases) { category in
                        let categoryWords = words.filter { $0.category == category }
                        CategoryProgressRow(
                            category: category,
                            learned: categoryWords.filter(\.isLearned).count,
                            total: categoryWords.count
                        )
                    }
                }
            }
            .navigationTitle("学習統計")
        }
    }
}

private struct StatRow: View {
    let title: String
    let value: String

    var body: some View {
        HStack {
            Text(title)
            Spacer()
            Text(value).foregroundStyle(.secondary)
        }
    }
}

private struct CategoryProgressRow: View {
    let category: WordCategory
    let learned: Int
    let total: Int

    private var progress: Double {
        total == 0 ? 0 : Double(learned) / Double(total)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Label {
                Text(category.displayName)
            } icon: {
                Image(systemName: category.symbolName)
                    .foregroundStyle(category.tint)
            }
            ProgressView(value: progress)
                .tint(category.tint)
            Text("\(learned) / \(total)語")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(.vertical, 4)
    }
}

#Preview {
    StatsView()
        .modelContainer(for: Word.self, inMemory: true)
}
