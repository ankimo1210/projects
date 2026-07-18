import Charts
import SwiftData
import SwiftUI

struct WrittenScorePoint: Identifiable, Equatable {
    let id: UUID
    let attemptNumber: Int
    let scorePercent: Double
}

enum WrittenPracticeInsights {
    static func scorePoints(from attempts: [StudyAttempt]) -> [WrittenScorePoint] {
        attempts
            .filter { $0.awardedMarks != nil && ($0.maximumMarks ?? 0) > 0 }
            .sorted {
                if $0.studiedAt != $1.studiedAt { return $0.studiedAt < $1.studiedAt }
                return $0.id.uuidString < $1.id.uuidString
            }
            .enumerated()
            .map { index, attempt in
                WrittenScorePoint(
                    id: attempt.id,
                    attemptNumber: index + 1,
                    scorePercent: Double(attempt.awardedMarks ?? 0)
                        / Double(attempt.maximumMarks ?? 1) * 100
                )
            }
    }

    static func unearnedRubricItems(
        for question: StudyQuestion,
        selectedRubricIDs: Set<String>
    ) -> [WrittenRubricItem] {
        question.rubricItems.filter { !selectedRubricIDs.contains($0.id) }
    }

    static func relatedTermIDs(
        for question: StudyQuestion,
        selectedRubricIDs: Set<String>
    ) -> [String] {
        var seen: Set<String> = []
        return unearnedRubricItems(for: question, selectedRubricIDs: selectedRubricIDs)
            .flatMap(\.relatedTermIDs)
            .filter { seen.insert($0).inserted }
    }
}

struct WrittenPracticeHistoryListView: View {
    @Query private var questions: [StudyQuestion]
    @Query(sort: \StudyAttempt.studiedAt, order: .reverse)
    private var attempts: [StudyAttempt]

    private var writtenQuestionsWithHistory: [StudyQuestion] {
        let attemptedIDs = Set(
            attempts
                .filter { $0.awardedMarks != nil && $0.responseText != nil }
                .map(\.questionID)
        )
        return questions
            .filter {
                $0.studyMode == "written_answer"
                    && FeatureAccessPolicy.canReadHistoricalQuestion(
                        id: $0.id,
                        recordedQuestionIDs: attemptedIDs
                    )
            }
            .sorted {
                latestAttemptDate(for: $0.id) > latestAttemptDate(for: $1.id)
            }
    }

    var body: some View {
        List {
            ForEach(writtenQuestionsWithHistory) { question in
                NavigationLink {
                    WrittenAnswerHistoryView(question: question)
                } label: {
                    VStack(alignment: .leading, spacing: 6) {
                        Text(question.displayPrompt)
                            .font(.body.weight(.semibold))
                            .lineLimit(2)
                        HStack {
                            Text("\(attempts(for: question.id).count)回")
                            if let latest = attempts(for: question.id).first,
                               let awarded = latest.awardedMarks,
                               let maximum = latest.maximumMarks {
                                Text("最新 \(awarded)/\(maximum)点")
                            }
                        }
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    }
                    .padding(.vertical, 3)
                }
                .accessibilityIdentifier("written.history.question.\(question.id)")
            }
        }
        .navigationTitle("記述式の過去回答")
        .overlay {
            if writtenQuestionsWithHistory.isEmpty {
                ContentUnavailableView(
                    "過去回答はありません",
                    systemImage: "square.and.pencil",
                    description: Text("記述式問題を自己採点すると、回答と得点推移を確認できます。")
                )
            }
        }
    }

    private func attempts(for questionID: String) -> [StudyAttempt] {
        attempts.filter { $0.questionID == questionID && $0.awardedMarks != nil }
    }

    private func latestAttemptDate(for questionID: String) -> Date {
        attempts(for: questionID).first?.studiedAt ?? .distantPast
    }
}

struct WrittenAnswerHistoryView: View {
    @Query(sort: \StudyAttempt.studiedAt, order: .reverse)
    private var allAttempts: [StudyAttempt]

    let question: StudyQuestion

    private var attempts: [StudyAttempt] {
        allAttempts.filter {
            $0.questionID == question.id
                && $0.responseText != nil
                && $0.awardedMarks != nil
        }
    }

    private var scorePoints: [WrittenScorePoint] {
        WrittenPracticeInsights.scorePoints(from: attempts)
    }

    var body: some View {
        if attempts.isEmpty {
            ContentUnavailableView(
                "過去回答はありません",
                systemImage: "clock.arrow.circlepath",
                description: Text("この問題を自己採点すると履歴が保存されます。")
            )
            .navigationTitle("過去回答")
            .navigationBarTitleDisplayMode(.inline)
        } else {
            historyContent
        }
    }

    private var historyContent: some View {
        List {
            Section("問題") {
                Text(question.displayPrompt)
            }

            Section("模範解答") {
                Text(question.displayAnswer)
                    .textSelection(.enabled)
            }

            if !scorePoints.isEmpty {
                Section("得点推移") {
                    Chart(scorePoints) { point in
                        LineMark(
                            x: .value("回答回", point.attemptNumber),
                            y: .value("得点率", point.scorePercent)
                        )
                        .foregroundStyle(AppTheme.wine)
                        PointMark(
                            x: .value("回答回", point.attemptNumber),
                            y: .value("得点率", point.scorePercent)
                        )
                        .foregroundStyle(AppTheme.wine)
                    }
                    .chartYScale(domain: 0...100)
                    .frame(height: 180)
                    .accessibilityIdentifier("written.history.scoreTrend")
                }
            }

            ForEach(attempts) { attempt in
                Section {
                    Text(attempt.responseText ?? "")
                        .textSelection(.enabled)

                    ForEach(question.rubricItems) { item in
                        Label {
                            HStack {
                                Text(item.criterion)
                                Spacer()
                                Text("\(item.marks)点")
                                    .foregroundStyle(.secondary)
                            }
                        } icon: {
                            Image(systemName: attempt.rubricSelections.contains(item.id)
                                  ? "checkmark.circle.fill"
                                  : "xmark.circle")
                                .foregroundStyle(
                                    attempt.rubricSelections.contains(item.id)
                                        ? AppTheme.success
                                        : AppTheme.warning
                                )
                        }
                    }

                    let termIDs = WrittenPracticeInsights.relatedTermIDs(
                        for: question,
                        selectedRubricIDs: Set(attempt.rubricSelections)
                    )
                    if !termIDs.isEmpty {
                        WrittenRubricReviewLinks(termIDs: termIDs)
                    }
                } header: {
                    HStack {
                        Text(attempt.studiedAt, format: .dateTime.year().month().day().hour().minute())
                        Spacer()
                        if let awarded = attempt.awardedMarks,
                           let maximum = attempt.maximumMarks {
                            Text("\(awarded)/\(maximum)点")
                        }
                    }
                } footer: {
                    if let seconds = attempt.durationSeconds {
                        Text("回答時間 \(WrittenPracticeTiming.durationText(seconds))")
                    }
                }
            }
        }
        .navigationTitle("過去回答")
        .navigationBarTitleDisplayMode(.inline)
    }

}

struct WrittenRubricReviewLinks: View {
    @Environment(EntitlementStore.self) private var entitlementStore
    let termIDs: [String]
    private let store = ReferenceStore.shared

    private var resolvedTerms: [ReferenceTerm] {
        termIDs
            .compactMap { store.term(id: $0) }
            .filter { entitlementStore.policy.canAccessGlossaryTerm(id: $0.id) }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("不足論点の復習")
                .font(.subheadline.weight(.semibold))

            NavigationLink {
                PremiumFeatureGate(feature: .glossarySRS) {
                    GlossaryReviewView(source: .selected(resolvedTerms.map(\.id)))
                }
            } label: {
                Label(
                    "関連用語をカードで復習（\(resolvedTerms.count)語）",
                    systemImage: "rectangle.stack"
                )
            }

            ForEach(resolvedTerms) { term in
                NavigationLink(term.nameJapanese) {
                    GlossaryTermDetailView(term: term)
                }
            }
        }
    }
}
