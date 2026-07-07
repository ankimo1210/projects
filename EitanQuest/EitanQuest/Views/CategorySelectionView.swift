import SwiftUI
import SwiftData

/// クイズ画面への遷移先を表す
private enum QuizDestination: Hashable {
    case category(WordCategory)
    case review
}

struct CategorySelectionView: View {
    @Query private var words: [Word]

    private var reviewCount: Int {
        words.filter { $0.needsReview }.count
    }

    var body: some View {
        NavigationStack {
            List {
                Section("カテゴリから学習") {
                    ForEach(WordCategory.allCases) { category in
                        NavigationLink(value: QuizDestination.category(category)) {
                            CategoryRow(category: category, words: wordsFor(category))
                        }
                    }
                }

                Section("復習") {
                    NavigationLink(value: QuizDestination.review) {
                        Label {
                            Text("苦手単語を復習する（\(reviewCount)語）")
                        } icon: {
                            Image(systemName: "arrow.counterclockwise.circle.fill")
                                .foregroundStyle(reviewCount == 0 ? Color.gray : Color.accentColor)
                        }
                    }
                    .disabled(reviewCount == 0)
                }
            }
            .navigationTitle("カテゴリを選択")
            .navigationDestination(for: QuizDestination.self) { destination in
                switch destination {
                case .category(let category):
                    QuizView(words: wordsFor(category), title: category.displayName)
                case .review:
                    QuizView(words: words.filter { $0.needsReview }, title: "苦手単語の復習")
                }
            }
        }
    }

    private func wordsFor(_ category: WordCategory) -> [Word] {
        words.filter { $0.category == category }
    }
}

private struct CategoryRow: View {
    let category: WordCategory
    let words: [Word]

    private var learnedCount: Int {
        words.filter(\.isLearned).count
    }

    private var progress: Double {
        words.isEmpty ? 0 : Double(learnedCount) / Double(words.count)
    }

    var body: some View {
        HStack(spacing: 14) {
            Image(systemName: category.symbolName)
                .font(.title3)
                .foregroundStyle(.white)
                .frame(width: 40, height: 40)
                .background(category.tint.gradient)
                .clipShape(RoundedRectangle(cornerRadius: 10))

            VStack(alignment: .leading, spacing: 6) {
                Text(category.displayName)
                    .font(.headline)
                ProgressView(value: progress)
                    .tint(category.tint)
                Text("\(learnedCount) / \(words.count)語 学習済み")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 4)
    }
}

#Preview {
    CategorySelectionView()
        .modelContainer(for: Word.self, inMemory: true)
}
