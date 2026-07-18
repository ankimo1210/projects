import SwiftData
import SwiftUI

struct HomeView: View {
    @Environment(EntitlementStore.self) private var entitlementStore
    @Query private var questions: [StudyQuestion]
    @Query private var progressRecords: [QuestionProgress]
    @Query private var attempts: [StudyAttempt]

    private var visibleQuestions: [StudyQuestion] {
        questions.filter {
            entitlementStore.policy.canAccessQuestion(id: $0.id, studyMode: $0.studyMode)
        }
    }

    private var visibleQuestionIDs: Set<String> {
        Set(visibleQuestions.map(\.id))
    }

    private var studiedCount: Int {
        progressRecords.count {
            visibleQuestionIDs.contains($0.questionID) && $0.attemptCount > 0
        }
    }

    private var dueCount: Int {
        progressRecords.count {
            visibleQuestionIDs.contains($0.questionID)
                && $0.attemptCount > 0
                && $0.dueDate <= .now
        }
    }

    private var bookmarkedCount: Int {
        progressRecords.count {
            visibleQuestionIDs.contains($0.questionID) && $0.isBookmarked
        }
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 24) {
                    VStack(alignment: .leading, spacing: 6) {
                        Text("WSET Level 3 学習")
                            .font(.title2.bold())
                        Text("オフライン問題集と学習進捗")
                            .foregroundStyle(.secondary)
                    }

                    LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 14) {
                        StatCard(title: "問題数", value: visibleQuestions.count.formatted(), systemImage: "books.vertical")
                        StatCard(title: "学習済み", value: studiedCount.formatted(), systemImage: "checkmark.circle")
                        StatCard(title: "復習期限", value: dueCount.formatted(), systemImage: "calendar")
                        StatCard(title: "ブックマーク", value: bookmarkedCount.formatted(), systemImage: "bookmark")
                    }

                    VStack(alignment: .leading, spacing: 14) {
                        Text("学習成果別の収録数")
                            .font(.headline)
                        ForEach(LearningOutcome.allCases.filter { $0 != .all }) { outcome in
                            let count = visibleQuestions.count(where: { $0.learningOutcome == outcome.rawValue })
                            HStack {
                                Text(outcome.shortLabel)
                                Spacer()
                                Text(count.formatted())
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                    .padding()
                    .background(.background, in: RoundedRectangle(cornerRadius: 16))
                    .shadow(color: .black.opacity(0.05), radius: 8, y: 3)

                    if attempts.isEmpty {
                        ContentUnavailableView(
                            "学習履歴はまだありません",
                            systemImage: "rectangle.stack",
                            description: Text("学習セッションを開始すると進捗が記録されます。")
                        )
                    }
                }
                .padding()
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("WSET学習")
        }
    }
}
