import Foundation

enum StudyRecommendationReasonKind: String, CaseIterable, Identifiable, Hashable {
    case due
    case recentMistake
    case glossaryWeakness
    case weakness
    case unstudied
    case learningOutcomeBalance
    case mixedReview

    var id: String { rawValue }

    var label: String {
        switch self {
        case .due: "期限"
        case .recentMistake: "直近の間違い"
        case .glossaryWeakness: "用語の弱点"
        case .weakness: "弱点"
        case .unstudied: "未学習"
        case .learningOutcomeBalance: "LOバランス"
        case .mixedReview: "定着確認"
        }
    }

    fileprivate var priority: Int {
        switch self {
        case .due: 6
        case .recentMistake: 5
        case .glossaryWeakness: 4
        case .weakness: 3
        case .unstudied: 2
        case .learningOutcomeBalance: 1
        case .mixedReview: 0
        }
    }
}

struct StudyRecommendationScoreComponent: Identifiable, Hashable {
    let kind: StudyRecommendationReasonKind
    let points: Int
    let detail: String

    var id: String { "\(kind.rawValue)|\(detail)" }
}

struct StudyRecommendation: Identifiable, Hashable {
    let rank: Int
    let questionID: String
    let learningOutcome: String
    let score: Int
    let scoreBreakdown: [StudyRecommendationScoreComponent]

    var id: String { questionID }

    var primaryReason: StudyRecommendationScoreComponent {
        scoreBreakdown.sorted { Self.componentPrecedes($0, $1) }.first
            ?? StudyRecommendationScoreComponent(
                kind: .mixedReview,
                points: 0,
                detail: "学習範囲の定着確認"
            )
    }

    private static func componentPrecedes(
        _ lhs: StudyRecommendationScoreComponent,
        _ rhs: StudyRecommendationScoreComponent
    ) -> Bool {
        if lhs.kind.priority != rhs.kind.priority {
            return lhs.kind.priority > rhs.kind.priority
        }
        if lhs.points != rhs.points { return lhs.points > rhs.points }
        return lhs.detail < rhs.detail
    }
}

struct StudyRecommendationResult: Hashable {
    let recommendations: [StudyRecommendation]
    let primaryReasonCounts: [StudyRecommendationReasonKind: Int]

    var questionIDs: [String] { recommendations.map(\.questionID) }

    var summaryText: String {
        let parts = StudyRecommendationReasonKind.allCases.compactMap { kind -> String? in
            guard let count = primaryReasonCounts[kind], count > 0 else { return nil }
            return "\(kind.label)\(count)問"
        }
        return parts.isEmpty ? "提案できる問題がありません" : parts.joined(separator: "、")
    }
}

struct StudyRecommendationConfiguration: Hashable {
    var count: Int
    var excludedQuestionIDs: Set<String>
    var recentMistakeDays: Int
    var minimumWeaknessAttempts: Int
    var weaknessAccuracyThreshold: Double
    var learningOutcomeDiversityPenalty: Int

    init(
        count: Int = 20,
        excludedQuestionIDs: Set<String> = [],
        recentMistakeDays: Int = 30,
        minimumWeaknessAttempts: Int = StudyStatisticsService.defaultMinimumSampleSize,
        weaknessAccuracyThreshold: Double = 0.7,
        learningOutcomeDiversityPenalty: Int = 90
    ) {
        self.count = max(0, count)
        self.excludedQuestionIDs = excludedQuestionIDs
        self.recentMistakeDays = max(1, recentMistakeDays)
        self.minimumWeaknessAttempts = max(1, minimumWeaknessAttempts)
        self.weaknessAccuracyThreshold = min(max(weaknessAccuracyThreshold, 0), 1)
        self.learningOutcomeDiversityPenalty = max(0, learningOutcomeDiversityPenalty)
    }
}

enum StudyRecommendationEngine {
    static func recommend(
        questions: [StudyQuestion],
        progressRecords: [QuestionProgress],
        attempts: [StudyAttempt],
        weakGlossaryQuestionIDs: Set<String> = [],
        configuration: StudyRecommendationConfiguration = StudyRecommendationConfiguration(),
        now: Date = .now
    ) -> StudyRecommendationResult {
        let eligibleQuestions = questions.filter {
            $0.studyMode == "multiple_choice" && $0.correctAnswerIndex != nil
        }
        return recommend(
            questions: eligibleQuestions.map { StudyAnalyticsQuestion(question: $0) },
            progressRecords: progressRecords.map { StudyAnalyticsProgress(progress: $0) },
            attempts: attempts.map { StudyAnalyticsAttempt(attempt: $0) },
            weakGlossaryQuestionIDs: weakGlossaryQuestionIDs,
            configuration: configuration,
            now: now
        )
    }

    static func recommend(
        questions: [StudyAnalyticsQuestion],
        progressRecords: [StudyAnalyticsProgress],
        attempts: [StudyAnalyticsAttempt],
        weakGlossaryQuestionIDs: Set<String> = [],
        configuration: StudyRecommendationConfiguration,
        now: Date
    ) -> StudyRecommendationResult {
        guard configuration.count > 0 else {
            return StudyRecommendationResult(recommendations: [], primaryReasonCounts: [:])
        }

        let questions = uniqueQuestionsByID(questions)
            .filter { !configuration.excludedQuestionIDs.contains($0.id) }
        guard !questions.isEmpty else {
            return StudyRecommendationResult(recommendations: [], primaryReasonCounts: [:])
        }

        let progressByID = preferredProgressByID(progressRecords)
        let attemptsByID = Dictionary(grouping: attempts, by: \StudyAnalyticsAttempt.questionID)
        let weakAreas = weakKnowledgeAreas(
            questions: questions,
            progressRecords: progressRecords,
            attempts: attempts,
            configuration: configuration,
            now: now
        )
        let underrepresentedOutcomes = underrepresentedLearningOutcomes(
            questions: questions,
            progressRecords: progressRecords,
            attempts: attempts,
            now: now
        )

        var candidates = questions.map { question in
            candidate(
                for: question,
                progress: progressByID[question.id],
                attempts: attemptsByID[question.id] ?? [],
                isRelatedToWeakGlossaryTerm: weakGlossaryQuestionIDs.contains(question.id),
                weakAreas: weakAreas,
                underrepresentedOutcomes: underrepresentedOutcomes,
                configuration: configuration,
                now: now
            )
        }

        var selected: [Candidate] = []
        var selectedByOutcome: [String: Int] = [:]
        let targetCount = min(configuration.count, candidates.count)
        while selected.count < targetCount {
            candidates.sort { lhs, rhs in
                candidatePrecedes(
                    lhs,
                    rhs,
                    selectedByOutcome: selectedByOutcome,
                    diversityPenalty: configuration.learningOutcomeDiversityPenalty
                )
            }
            let next = candidates.removeFirst()
            selected.append(next)
            selectedByOutcome[next.question.learningOutcome, default: 0] += 1
        }

        let recommendations = selected.enumerated().map { index, candidate in
            StudyRecommendation(
                rank: index + 1,
                questionID: candidate.question.id,
                learningOutcome: candidate.question.learningOutcome,
                score: candidate.score,
                scoreBreakdown: candidate.components
            )
        }
        var reasonCounts: [StudyRecommendationReasonKind: Int] = [:]
        for recommendation in recommendations {
            reasonCounts[recommendation.primaryReason.kind, default: 0] += 1
        }
        return StudyRecommendationResult(
            recommendations: recommendations,
            primaryReasonCounts: reasonCounts
        )
    }

    private struct Candidate {
        let question: StudyAnalyticsQuestion
        let components: [StudyRecommendationScoreComponent]
        let score: Int
        let primaryPriority: Int
        let lastStudiedAt: Date?
    }

    private static func candidate(
        for question: StudyAnalyticsQuestion,
        progress: StudyAnalyticsProgress?,
        attempts: [StudyAnalyticsAttempt],
        isRelatedToWeakGlossaryTerm: Bool,
        weakAreas: [String: StudyStatistic],
        underrepresentedOutcomes: Set<String>,
        configuration: StudyRecommendationConfiguration,
        now: Date
    ) -> Candidate {
        let attempts = attempts.sorted { recentAttemptPrecedes($0, $1) }
        var components: [StudyRecommendationScoreComponent] = []

        if let progress, progress.attemptCount > 0, progress.dueDate <= now {
            let daysOverdue = wholeDays(from: progress.dueDate, to: now)
            components.append(
                StudyRecommendationScoreComponent(
                    kind: .due,
                    points: 1_000 + min(daysOverdue, 30) * 4,
                    detail: daysOverdue == 0 ? "復習期限が来ています" : "復習期限を\(daysOverdue)日超過"
                )
            )
        }

        if let latestAttempt = attempts.first,
           !latestAttempt.isCorrect,
           isRecent(latestAttempt.studiedAt, now: now, days: configuration.recentMistakeDays) {
            let daysAgo = wholeDays(from: latestAttempt.studiedAt, to: now)
            components.append(
                StudyRecommendationScoreComponent(
                    kind: .recentMistake,
                    points: 700 + max(0, configuration.recentMistakeDays - daysAgo) * 3,
                    detail: daysAgo == 0 ? "直近の回答が不正解" : "\(daysAgo)日前の回答が不正解"
                )
            )
        } else if attempts.isEmpty,
                  let progress,
                  progress.lastWasCorrect == false,
                  let lastStudiedAt = progress.lastStudiedAt,
                  isRecent(lastStudiedAt, now: now, days: configuration.recentMistakeDays) {
            let daysAgo = wholeDays(from: lastStudiedAt, to: now)
            components.append(
                StudyRecommendationScoreComponent(
                    kind: .recentMistake,
                    points: 700 + max(0, configuration.recentMistakeDays - daysAgo) * 3,
                    detail: daysAgo == 0 ? "直近の回答が不正解" : "\(daysAgo)日前の回答が不正解"
                )
            )
        }

        if isRelatedToWeakGlossaryTerm {
            components.append(
                StudyRecommendationScoreComponent(
                    kind: .glossaryWeakness,
                    points: 650,
                    detail: "「もう一度」と記録した用語の関連問題"
                )
            )
        }

        let questionAreas = StudyStatisticsService.values(
            for: .knowledgeArea,
            question: question
        )
        let weakestArea = questionAreas
            .compactMap { weakAreas[$0] }
            .sorted { weaknessPrecedes($0, $1) }
            .first
        if let weakestArea, let accuracy = weakestArea.accuracy {
            let gap = max(0, configuration.weaknessAccuracyThreshold - accuracy)
            components.append(
                StudyRecommendationScoreComponent(
                    kind: .weakness,
                    points: 450 + Int((gap * 200).rounded()),
                    detail: "\(weakestArea.value) 正答率\(percent(accuracy))（\(weakestArea.attemptCount)回）"
                )
            )
        }

        let recordedAttemptCount = max(progress?.attemptCount ?? 0, attempts.count)
        if recordedAttemptCount == 0 {
            components.append(
                StudyRecommendationScoreComponent(
                    kind: .unstudied,
                    points: 250,
                    detail: "まだ学習していない問題"
                )
            )
        }

        if underrepresentedOutcomes.contains(question.learningOutcome) {
            components.append(
                StudyRecommendationScoreComponent(
                    kind: .learningOutcomeBalance,
                    points: 125,
                    detail: "\(learningOutcomeLabel(question.learningOutcome))の学習量を補正"
                )
            )
        }

        if components.isEmpty {
            components.append(
                StudyRecommendationScoreComponent(
                    kind: .mixedReview,
                    points: 25,
                    detail: "学習範囲の定着確認"
                )
            )
        }
        components.sort { lhs, rhs in
            if lhs.kind.priority != rhs.kind.priority {
                return lhs.kind.priority > rhs.kind.priority
            }
            if lhs.points != rhs.points { return lhs.points > rhs.points }
            return lhs.detail < rhs.detail
        }
        return Candidate(
            question: question,
            components: components,
            score: components.reduce(0) { $0 + $1.points },
            primaryPriority: components.map(\.kind.priority).max() ?? 0,
            lastStudiedAt: progress?.lastStudiedAt ?? attempts.first?.studiedAt
        )
    }

    private static func weakKnowledgeAreas(
        questions: [StudyAnalyticsQuestion],
        progressRecords: [StudyAnalyticsProgress],
        attempts: [StudyAnalyticsAttempt],
        configuration: StudyRecommendationConfiguration,
        now: Date
    ) -> [String: StudyStatistic] {
        let statistics = StudyStatisticsService.statistics(
            for: .knowledgeArea,
            questions: questions,
            progressRecords: progressRecords,
            attempts: attempts,
            now: now,
            minimumSampleSize: configuration.minimumWeaknessAttempts
        )
        return Dictionary(
            uniqueKeysWithValues: StudyStatisticsService
                .weakest(statistics, below: configuration.weaknessAccuracyThreshold)
                .map { ($0.value, $0) }
        )
    }

    private static func underrepresentedLearningOutcomes(
        questions: [StudyAnalyticsQuestion],
        progressRecords: [StudyAnalyticsProgress],
        attempts: [StudyAnalyticsAttempt],
        now: Date
    ) -> Set<String> {
        let statistics = StudyStatisticsService.statistics(
            for: .learningOutcome,
            questions: questions,
            progressRecords: progressRecords,
            attempts: attempts,
            now: now,
            minimumSampleSize: 1
        )
        guard let minimumCoverage = statistics.compactMap(\.coverage).min() else { return [] }
        return Set(
            statistics
                .filter { abs(($0.coverage ?? 1) - minimumCoverage) < 0.000_001 }
                .map(\.value)
        )
    }

    private static func candidatePrecedes(
        _ lhs: Candidate,
        _ rhs: Candidate,
        selectedByOutcome: [String: Int],
        diversityPenalty: Int
    ) -> Bool {
        if lhs.primaryPriority != rhs.primaryPriority {
            return lhs.primaryPriority > rhs.primaryPriority
        }
        let lhsAdjustedScore = lhs.score
            - selectedByOutcome[lhs.question.learningOutcome, default: 0] * diversityPenalty
        let rhsAdjustedScore = rhs.score
            - selectedByOutcome[rhs.question.learningOutcome, default: 0] * diversityPenalty
        if lhsAdjustedScore != rhsAdjustedScore { return lhsAdjustedScore > rhsAdjustedScore }
        let lhsDate = lhs.lastStudiedAt ?? .distantPast
        let rhsDate = rhs.lastStudiedAt ?? .distantPast
        if lhsDate != rhsDate { return lhsDate < rhsDate }
        return lhs.question.id < rhs.question.id
    }

    private static func weaknessPrecedes(_ lhs: StudyStatistic, _ rhs: StudyStatistic) -> Bool {
        let lhsAccuracy = lhs.accuracy ?? 1
        let rhsAccuracy = rhs.accuracy ?? 1
        if lhsAccuracy != rhsAccuracy { return lhsAccuracy < rhsAccuracy }
        if lhs.attemptCount != rhs.attemptCount { return lhs.attemptCount > rhs.attemptCount }
        return lhs.value < rhs.value
    }

    private static func preferredProgressByID(
        _ records: [StudyAnalyticsProgress]
    ) -> [String: StudyAnalyticsProgress] {
        var result: [String: StudyAnalyticsProgress] = [:]
        for record in records {
            guard let existing = result[record.questionID] else {
                result[record.questionID] = record
                continue
            }
            if record.attemptCount > existing.attemptCount
                || (record.attemptCount == existing.attemptCount
                    && (record.lastStudiedAt ?? .distantPast) > (existing.lastStudiedAt ?? .distantPast)) {
                result[record.questionID] = record
            }
        }
        return result
    }

    private static func uniqueQuestionsByID(
        _ questions: [StudyAnalyticsQuestion]
    ) -> [StudyAnalyticsQuestion] {
        var seen: Set<String> = []
        return questions
            .sorted { $0.id < $1.id }
            .filter { seen.insert($0.id).inserted }
    }

    private static func recentAttemptPrecedes(
        _ lhs: StudyAnalyticsAttempt,
        _ rhs: StudyAnalyticsAttempt
    ) -> Bool {
        if lhs.studiedAt != rhs.studiedAt { return lhs.studiedAt > rhs.studiedAt }
        return lhs.id < rhs.id
    }

    private static func isRecent(_ date: Date, now: Date, days: Int) -> Bool {
        guard date <= now else { return true }
        return now.timeIntervalSince(date) <= Double(days) * 86_400
    }

    private static func wholeDays(from start: Date, to end: Date) -> Int {
        max(0, Int(end.timeIntervalSince(start) / 86_400))
    }

    private static func percent(_ value: Double) -> String {
        value.formatted(.percent.precision(.fractionLength(0)))
    }

    private static func learningOutcomeLabel(_ value: String) -> String {
        LearningOutcome(rawValue: value)?.shortLabel ?? value
    }
}
