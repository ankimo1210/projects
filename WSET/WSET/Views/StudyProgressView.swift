import SwiftData
import SwiftUI

struct StudyProgressView: View {
    @Query private var questions: [StudyQuestion]
    @Query private var progressRecords: [QuestionProgress]
    @Query(sort: \StudyAttempt.studiedAt, order: .reverse) private var attempts: [StudyAttempt]

    private var accuracy: Double {
        guard !attempts.isEmpty else { return 0 }
        return Double(attempts.count(where: \.isCorrect)) / Double(attempts.count)
    }

    private var questionByID: [String: StudyQuestion] {
        Dictionary(uniqueKeysWithValues: questions.map { ($0.id, $0) })
    }

    var body: some View {
        NavigationStack {
            List {
                Section {
                    HStack(spacing: 12) {
                        StatCard(title: "Attempts", value: attempts.count.formatted(), systemImage: "number")
                        StatCard(
                            title: "Accuracy",
                            value: accuracy.formatted(.percent.precision(.fractionLength(0))),
                            systemImage: "target"
                        )
                    }
                    .listRowInsets(EdgeInsets())
                    .listRowBackground(Color.clear)
                }

                Section("By learning outcome") {
                    ForEach(LearningOutcome.allCases.filter { $0 != .all }) { outcome in
                        let outcomeAttempts = attempts.filter {
                            questionByID[$0.questionID]?.learningOutcome == outcome.rawValue
                        }
                        let correct = outcomeAttempts.count(where: \.isCorrect)
                        VStack(alignment: .leading, spacing: 7) {
                            HStack {
                                Text(outcome.shortLabel)
                                Spacer()
                                Text("\(correct)/\(outcomeAttempts.count)")
                                    .foregroundStyle(.secondary)
                            }
                            ProgressView(
                                value: outcomeAttempts.isEmpty
                                    ? 0
                                    : Double(correct) / Double(outcomeAttempts.count)
                            )
                            .tint(AppTheme.wine)
                        }
                        .padding(.vertical, 4)
                    }
                }

                Section("Mock examinations") {
                    NavigationLink {
                        MockExamHistoryView()
                    } label: {
                        Label("Score history and trends", systemImage: "chart.xyaxis.line")
                    }
                }

                Section("Recent activity") {
                    if attempts.isEmpty {
                        Text("No attempts yet")
                            .foregroundStyle(.secondary)
                    } else {
                        ForEach(attempts.prefix(20)) { attempt in
                            HStack {
                                Image(systemName: attempt.isCorrect ? "checkmark.circle.fill" : "xmark.circle.fill")
                                    .foregroundStyle(attempt.isCorrect ? .green : .red)
                                VStack(alignment: .leading) {
                                    Text(questionByID[attempt.questionID]?.prompt ?? "問題")
                                        .lineLimit(1)
                                    Text(attempt.studiedAt, style: .relative)
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                            }
                        }
                    }
                }
            }
            .navigationTitle("Progress")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    NavigationLink {
                        SettingsView()
                    } label: {
                        Image(systemName: "gearshape")
                    }
                    .accessibilityLabel("Settings")
                }
            }
        }
    }
}
