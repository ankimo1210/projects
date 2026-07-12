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
                    "No mock exams yet",
                    systemImage: "timer",
                    description: Text("Completed 50-question mock exams will appear here.")
                )
            } else {
                Section("Score trend") {
                    Chart(sessions) { session in
                        LineMark(
                            x: .value("Date", session.completedAt),
                            y: .value("Score", session.score * 100)
                        )
                        .foregroundStyle(AppTheme.wine)
                        .interpolationMethod(.catmullRom)

                        PointMark(
                            x: .value("Date", session.completedAt),
                            y: .value("Score", session.score * 100)
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

                Section("History") {
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
                                    Text("\(session.correctCount) of \(session.questionCount) correct")
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
        .navigationTitle("Mock exam history")
    }

    private var questionByID: [String: StudyQuestion] {
        Dictionary(uniqueKeysWithValues: questions.map { ($0.id, $0) })
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

            Section("By learning outcome") {
                ForEach(LearningOutcome.allCases.filter { $0 != .all }) { outcome in
                    if let result = session.outcomeResults[outcome.rawValue], result.total > 0 {
                        LabeledContent(outcome.shortLabel, value: "\(result.correct)/\(result.total)")
                    }
                }
            }

            Section("Missed questions") {
                if session.missedQuestionIDs.isEmpty {
                    Label("Perfect score", systemImage: "checkmark.seal.fill")
                        .foregroundStyle(.green)
                } else {
                    ForEach(session.missedQuestionIDs, id: \.self) { questionID in
                        if let question = questionByID[questionID] {
                            NavigationLink {
                                QuestionDetailView(question: question)
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
