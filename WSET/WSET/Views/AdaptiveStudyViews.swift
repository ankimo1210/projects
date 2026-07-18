import SwiftData
import SwiftUI

struct DailyStudyView: View {
    @Query private var questions: [StudyQuestion]
    @Query private var progressRecords: [QuestionProgress]
    @Query private var attempts: [StudyAttempt]
    @Query private var termProgressRecords: [ReferenceTermProgress]

    @State private var sessionSize = 20
    @State private var sessionQuestions: [StudyQuestion] = []
    @State private var showingSession = false

    private let referenceStore = ReferenceStore.shared

    private var result: StudyRecommendationResult {
        StudyRecommendationEngine.recommend(
            questions: questions,
            progressRecords: progressRecords,
            attempts: attempts,
            weakGlossaryQuestionIDs: weakGlossaryQuestionIDs,
            configuration: StudyRecommendationConfiguration(count: sessionSize)
        )
    }

    private var weakGlossaryQuestionIDs: Set<String> {
        Set(
            termProgressRecords
                .filter { $0.reviewAttemptCount > 0 && $0.lastReviewWasCorrect == false }
                .flatMap { progress in
                    referenceStore.term(id: progress.termID)?.questionIDs ?? []
                }
        )
    }

    private var questionsByID: [String: StudyQuestion] {
        var result: [String: StudyQuestion] = [:]
        for question in questions where result[question.id] == nil {
            result[question.id] = question
        }
        return result
    }

    private var recommendedQuestions: [StudyQuestion] {
        result.questionIDs.compactMap { questionsByID[$0] }
    }

    private var termReviewPlan: ReferenceReviewPlan {
        ReferenceReviewScheduler.plan(
            for: .today,
            allTerms: referenceStore.terms,
            progressRecords: termProgressRecords
        )
    }

    private var recommendedTerms: [ReferenceTerm] {
        termReviewPlan.termIDs.compactMap { referenceStore.term(id: $0) }
    }

    var body: some View {
        PremiumFeatureGate(feature: .adaptiveStudy) {
            adaptiveContent
        }
    }

    private var adaptiveContent: some View {
        List {
            Section {
                Picker("問題数", selection: $sessionSize) {
                    Text("10問").tag(10)
                    Text("20問").tag(20)
                }
                .pickerStyle(.segmented)
                .accessibilityIdentifier("study.daily.sessionSize")

                Text("問題の期限・誤答・弱点と、用語の復習期限・「もう一度」をまとめて提案します。")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            } header: {
                Text("今日の学習提案")
            }

            Section("おすすめ問題（\(result.recommendations.count)問）") {
                if result.recommendations.isEmpty {
                    ContentUnavailableView(
                        "学習できる問題がありません",
                        systemImage: "checkmark.circle",
                        description: Text("問題データを確認してください。")
                    )
                } else {
                    LabeledContent("構成", value: result.summaryText)
                        .accessibilityIdentifier("study.daily.summary")
                    ForEach(StudyRecommendationReasonKind.allCases) { kind in
                        if let count = result.primaryReasonCounts[kind], count > 0 {
                            HStack {
                                Label(kind.label, systemImage: icon(for: kind))
                                Spacer()
                                Text("\(count)問")
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                }
            }

            if !result.recommendations.isEmpty {
                Section("問題プレビュー") {
                    ForEach(result.recommendations.prefix(5)) { recommendation in
                        VStack(alignment: .leading, spacing: 5) {
                            Text(questionsByID[recommendation.questionID]?.displayPrompt ?? "問題")
                                .lineLimit(2)
                            Text(recommendation.primaryReason.detail)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                    if result.recommendations.count > 5 {
                        Text("ほか\(result.recommendations.count - 5)問")
                            .foregroundStyle(.secondary)
                    }
                }

                Section {
                    Button {
                        sessionQuestions = recommendedQuestions
                        showingSession = !sessionQuestions.isEmpty
                    } label: {
                        Label("おすすめ問題を開始（\(recommendedQuestions.count)問）", systemImage: "play.fill")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(AppTheme.wine)
                    .accessibilityIdentifier("study.daily.startButton")
                }
            }

            Section("今日の用語カード（\(recommendedTerms.count)語）") {
                if recommendedTerms.isEmpty {
                    ContentUnavailableView(
                        "今日の用語復習は完了しています",
                        systemImage: "checkmark.circle",
                        description: Text("期限が来た用語や未学習の用語が追加されると、ここに表示されます。")
                    )
                } else {
                    LabeledContent("構成", value: termReviewPlan.summaryText)
                        .accessibilityIdentifier("study.daily.termSummary")

                    ForEach(ReferenceReviewReason.allCases) { reason in
                        if let count = termReviewPlan.reasonCounts[reason], count > 0 {
                            HStack {
                                Label(reason.label, systemImage: termIcon(for: reason))
                                Spacer()
                                Text("\(count)語")
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }

                    ForEach(recommendedTerms.prefix(3)) { term in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(term.nameJapanese)
                                .font(.subheadline.weight(.semibold))
                            Text(term.summary)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                                .lineLimit(2)
                        }
                    }

                    NavigationLink {
                        GlossaryReviewView(source: .selected(termReviewPlan.termIDs))
                    } label: {
                        Label("用語カードを開始（\(recommendedTerms.count)語）", systemImage: "rectangle.stack.fill")
                    }
                    .accessibilityIdentifier("study.daily.termStartButton")
                }
            }
        }
        .navigationTitle("今日の学習")
        .navigationDestination(isPresented: $showingSession) {
            StudySessionView(questions: sessionQuestions)
        }
    }

    private func icon(for kind: StudyRecommendationReasonKind) -> String {
        switch kind {
        case .due: "calendar.badge.clock"
        case .recentMistake: "xmark.circle"
        case .glossaryWeakness: "text.badge.exclamationmark"
        case .weakness: "chart.bar.xaxis"
        case .unstudied: "sparkles"
        case .learningOutcomeBalance: "scale.3d"
        case .mixedReview: "arrow.triangle.2.circlepath"
        }
    }

    private func termIcon(for reason: ReferenceReviewReason) -> String {
        switch reason {
        case .again: "arrow.counterclockwise.circle"
        case .due: "calendar.badge.clock"
        case .unseen: "sparkles"
        }
    }
}

struct WeaknessDashboardView: View {
    @Query private var questions: [StudyQuestion]
    @Query private var progressRecords: [QuestionProgress]
    @Query private var attempts: [StudyAttempt]

    @State private var selectedDimension = StudyStatisticsDimension.knowledgeArea

    private var eligibleQuestions: [StudyQuestion] {
        questions.filter {
            $0.studyMode == "multiple_choice" && $0.correctAnswerIndex != nil
        }
    }

    private var statistics: [StudyStatistic] {
        StudyStatisticsService.statistics(
            for: selectedDimension,
            questions: eligibleQuestions,
            progressRecords: progressRecords,
            attempts: attempts
        )
    }

    private var displayedStatistics: [StudyStatistic] {
        statistics.sorted { lhs, rhs in
            let lhsRank = displayRank(lhs)
            let rhsRank = displayRank(rhs)
            if lhsRank != rhsRank { return lhsRank < rhsRank }
            let lhsAccuracy = lhs.accuracy ?? 1
            let rhsAccuracy = rhs.accuracy ?? 1
            if lhsAccuracy != rhsAccuracy { return lhsAccuracy < rhsAccuracy }
            if lhs.attemptCount != rhs.attemptCount { return lhs.attemptCount > rhs.attemptCount }
            return lhs.value.localizedStandardCompare(rhs.value) == .orderedAscending
        }
    }

    var body: some View {
        PremiumFeatureGate(feature: .detailedStatistics) {
            statisticsContent
        }
    }

    private var statisticsContent: some View {
        List {
            Section {
                Picker("集計軸", selection: $selectedDimension) {
                    ForEach(StudyStatisticsDimension.allCases) { dimension in
                        Text(dimension.label).tag(dimension)
                    }
                }
                .accessibilityIdentifier("study.weakness.dimension")
            } footer: {
                Text("5回未満の試行は「データ不足」とし、弱点とは判定しません。")
            }

            Section(selectedDimension.label) {
                if displayedStatistics.isEmpty {
                    ContentUnavailableView(
                        "集計対象がありません",
                        systemImage: "chart.bar",
                        description: Text("別の集計軸を選択してください。")
                    )
                } else {
                    ForEach(displayedStatistics) { statistic in
                        NavigationLink {
                            StudySessionView(
                                questions: questions(for: statistic)
                            )
                        } label: {
                            WeaknessStatisticRow(statistic: statistic)
                        }
                        .accessibilityIdentifier("study.weakness.row.\(statistic.id)")
                    }
                }
            }
        }
        .navigationTitle("弱点分析")
    }

    private func questions(for statistic: StudyStatistic) -> [StudyQuestion] {
        let questionIDs = StudyStatisticsService.matchingQuestionIDs(
            for: statistic.dimension,
            value: statistic.value,
            questions: eligibleQuestions
        )
        return Array(
            eligibleQuestions
                .filter { questionIDs.contains($0.id) }
                .sorted { $0.id < $1.id }
                .prefix(20)
        )
    }

    private func displayRank(_ statistic: StudyStatistic) -> Int {
        switch statistic.sampleState {
        case .sufficient: statistic.isWeak() ? 0 : 1
        case .insufficient: 2
        case .noData: 3
        }
    }
}

private struct WeaknessStatisticRow: View {
    let statistic: StudyStatistic

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .firstTextBaseline) {
                Text(displayValue)
                    .font(.body.weight(.medium))
                Spacer()
                Text(accuracyLabel)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(metricColor)
            }

            if let accuracy = statistic.accuracy {
                ProgressView(value: accuracy)
                    .tint(metricColor)
            }

            HStack(spacing: 12) {
                Text("対象 \(statistic.questionCount)問")
                Text("学習済み \(statistic.studiedQuestionCount)問")
                Text("試行 \(statistic.attemptCount)回")
                if statistic.dueCount > 0 {
                    Text("期限 \(statistic.dueCount)問")
                }
            }
            .font(.caption)
            .foregroundStyle(.secondary)

            Text(recentAccuracyLabel)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(.vertical, 3)
    }

    private var displayValue: String {
        if statistic.dimension == .learningOutcome {
            return LearningOutcome(rawValue: statistic.value)?.shortLabel ?? statistic.value
        }
        return statistic.value
    }

    private var accuracyLabel: String {
        switch statistic.sampleState {
        case .noData:
            return "未学習"
        case .insufficient:
            if let accuracy = statistic.accuracy {
                return "\(accuracy.formatted(.percent.precision(.fractionLength(0)))) · データ不足"
            }
            return "データ不足"
        case .sufficient:
            return statistic.accuracy?.formatted(.percent.precision(.fractionLength(0))) ?? "未学習"
        }
    }

    private var metricColor: Color {
        guard statistic.sampleState == .sufficient, let accuracy = statistic.accuracy else {
            return .secondary
        }
        if accuracy < 0.7 { return AppTheme.error }
        if accuracy < 0.85 { return AppTheme.warning }
        return AppTheme.success
    }

    private var recentAccuracyLabel: String {
        guard let recentAccuracy = statistic.recentAccuracy else {
            return "直近正答率：記録なし"
        }
        return "直近正答率：\(recentAccuracy.formatted(.percent.precision(.fractionLength(0))))"
            + "（\(statistic.recentCorrectCount)/\(statistic.recentAttemptCount)回）"
    }
}
