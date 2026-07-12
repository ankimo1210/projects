import SwiftData
import SwiftUI

struct HomeView: View {
    @Query private var questions: [StudyQuestion]
    @Query private var progressRecords: [QuestionProgress]
    @Query private var attempts: [StudyAttempt]

    private var visibleQuestions: [StudyQuestion] {
        questions
    }

    private var studiedCount: Int {
        progressRecords.count(where: { $0.attemptCount > 0 })
    }

    private var dueCount: Int {
        progressRecords.count(where: { $0.attemptCount > 0 && $0.dueDate <= .now })
    }

    private var bookmarkedCount: Int {
        progressRecords.count(where: \.isBookmarked)
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
                        StatCard(title: "Questions", value: visibleQuestions.count.formatted(), systemImage: "books.vertical")
                        StatCard(title: "Studied", value: studiedCount.formatted(), systemImage: "checkmark.circle")
                        StatCard(title: "Due", value: dueCount.formatted(), systemImage: "calendar")
                        StatCard(title: "Bookmarks", value: bookmarkedCount.formatted(), systemImage: "bookmark")
                    }

                    VStack(alignment: .leading, spacing: 14) {
                        Text("Coverage")
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
                            "No study history yet",
                            systemImage: "rectangle.stack",
                            description: Text("Start a session to build your personal progress profile.")
                        )
                    }
                }
                .padding()
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("WSET Study")
        }
    }
}
