import Charts
import SwiftData
import SwiftUI

struct MockExamHistoryView: View {
    @Query(sort: \MockExamSession.completedAt) private var sessions: [MockExamSession]
    @Query private var questions: [StudyQuestion]

    var body: some View {
        List {
            if sessions.isEmpty {
                ContentUnavailableView(
                    "模擬試験履歴はまだありません",
                    systemImage: "timer",
                    description: Text("完了した50問模擬試験がここに表示されます。")
                )
            } else {
                Section("スコア推移") {
                    Chart(sessions) { session in
                        LineMark(
                            x: .value("日付", session.completedAt),
                            y: .value("スコア", session.score * 100)
                        )
                        .foregroundStyle(AppTheme.wine)
                        .interpolationMethod(.catmullRom)

                        PointMark(
                            x: .value("日付", session.completedAt),
                            y: .value("スコア", session.score * 100)
                        )
                        .foregroundStyle(AppTheme.wine)
                    }
                    .chartYScale(domain: 0...100)
                    .chartYAxis {
                        AxisMarks(values: [0, 25, 50, 75, 100]) { value in
                            AxisGridLine()
                            AxisValueLabel {
                                if let score = value.as(Int.self) {
                                    Text("\(score)%")
                                }
                            }
                        }
                    }
                    .frame(height: 220)
                }

                Section("履歴") {
                    ForEach(sessions.reversed()) { session in
                        NavigationLink {
                            MockExamHistoryDetailView(
                                session: session,
                                questionByID: questionByID
                            )
                        } label: {
                            HStack {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(session.completedAt, format: .dateTime.year().month().day().hour().minute())
                                    Text("\(session.questionCount)問中\(session.correctCount)問正解")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                                Spacer()
                                Text(session.score, format: .percent.precision(.fractionLength(0)))
                                    .font(.title3.bold())
                                    .foregroundStyle(AppTheme.wine)
                            }
                        }
                    }
                }
            }
        }
        .navigationTitle("模擬試験履歴")
    }

    private var questionByID: [String: StudyQuestion] {
        let historicalQuestionIDs = Set(sessions.flatMap(\.missedQuestionIDs))
        return Dictionary(uniqueKeysWithValues: questions.compactMap { question in
            FeatureAccessPolicy.canReadHistoricalQuestion(
                id: question.id,
                recordedQuestionIDs: historicalQuestionIDs
            ) ? (question.id, question) : nil
        })
    }
}

private struct MockExamHistoryDetailView: View {
    let session: MockExamSession
    let questionByID: [String: StudyQuestion]

    var body: some View {
        List {
            Section {
                VStack(spacing: 8) {
                    Text(session.score, format: .percent.precision(.fractionLength(0)))
                        .font(.system(size: 46, weight: .bold, design: .rounded))
                        .foregroundStyle(AppTheme.wine)
                    Text("\(session.correctCount) / \(session.questionCount)")
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity)
            }

            Section("学習成果別") {
                ForEach(LearningOutcome.allCases.filter { $0 != .all }) { outcome in
                    if let result = session.outcomeResults[outcome.rawValue], result.total > 0 {
                        LabeledContent(outcome.shortLabel, value: "\(result.correct)/\(result.total)")
                    }
                }
            }

            Section("間違えた問題") {
                if session.missedQuestionIDs.isEmpty {
                    Label("全問正解", systemImage: "checkmark.seal.fill")
                        .foregroundStyle(AppTheme.success)
                } else {
                    ForEach(session.missedQuestionIDs, id: \.self) { questionID in
                        if let question = questionByID[questionID] {
                            NavigationLink {
                                HistoricalQuestionReviewView(question: question)
                            } label: {
                                Text(question.displayPrompt)
                                    .lineLimit(3)
                            }
                        }
                    }
                }
            }
        }
        .navigationTitle(
            session.completedAt.formatted(
                Date.FormatStyle(
                    date: .abbreviated,
                    time: .omitted,
                    locale: AppLanguage.locale
                )
            )
        )
        .navigationBarTitleDisplayMode(.inline)
    }
}

/// A read-only review surface for a question that belongs to a completed exam.
/// It deliberately does not link back into a new paid study session.
private struct HistoricalQuestionReviewView: View {
    let question: StudyQuestion

    var body: some View {
        List {
            Section("問題") {
                Text(question.displayPrompt)
            }
            Section("正解") {
                Text(question.displayAnswer)
            }
            if let explanation = question.displayExplanation, !explanation.isEmpty {
                Section("解説") {
                    Text(explanation)
                }
            }
        }
        .navigationTitle("過去の問題")
        .navigationBarTitleDisplayMode(.inline)
    }
}
