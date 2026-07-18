import SwiftData
import SwiftUI

struct StudyProgressView: View {
    @Query private var questions: [StudyQuestion]
    @Query private var progressRecords: [QuestionProgress]
    @Query(sort: \StudyAttempt.studiedAt, order: .reverse) private var attempts: [StudyAttempt]

    private var accuracy: Double {
        guard !visibleAttempts.isEmpty else { return 0 }
        return Double(visibleAttempts.count(where: \.isCorrect))
            / Double(visibleAttempts.count)
    }

    private var questionByID: [String: StudyQuestion] {
        let historicalQuestionIDs = Set(attempts.map(\.questionID))
        return Dictionary(uniqueKeysWithValues: questions.compactMap { question in
            FeatureAccessPolicy.canReadHistoricalQuestion(
                id: question.id,
                recordedQuestionIDs: historicalQuestionIDs
            ) ? (question.id, question) : nil
        })
    }

    private var visibleAttempts: [StudyAttempt] {
        attempts.filter { questionByID[$0.questionID] != nil }
    }

    var body: some View {
        NavigationStack {
            List {
                Section {
                    HStack(spacing: 12) {
                        StatCard(
                            title: "回答回数",
                            value: visibleAttempts.count.formatted(),
                            systemImage: "number"
                        )
                        StatCard(
                            title: "正答率",
                            value: accuracy.formatted(.percent.precision(.fractionLength(0))),
                            systemImage: "target"
                        )
                    }
                    .listRowInsets(EdgeInsets())
                    .listRowBackground(Color.clear)
                }

                Section("学習成果別") {
                    ForEach(LearningOutcome.allCases.filter { $0 != .all }) { outcome in
                        let outcomeAttempts = visibleAttempts.filter {
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

                Section("模擬試験") {
                    NavigationLink {
                        MockExamHistoryView()
                    } label: {
                        Label("スコア履歴と推移", systemImage: "chart.xyaxis.line")
                    }
                }

                Section("最近の学習") {
                    if visibleAttempts.isEmpty {
                        Text("回答履歴はまだありません")
                            .foregroundStyle(.secondary)
                    } else {
                        ForEach(visibleAttempts.prefix(20)) { attempt in
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
            .navigationTitle("進捗")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    NavigationLink {
                        SettingsView()
                    } label: {
                        Image(systemName: "gearshape")
                    }
                    .accessibilityLabel("設定")
                }
            }
        }
    }
}
