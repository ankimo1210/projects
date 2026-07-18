import Foundation

enum StudyStatisticsDimension: String, CaseIterable, Identifiable, Hashable {
    case learningOutcome
    case country
    case region
    case grapeVariety
    case wineType
    case knowledgeArea
    case difficulty
    case cognitiveSkill

    var id: String { rawValue }

    var label: String {
        switch self {
        case .learningOutcome: "学習成果（LO）"
        case .country: "国"
        case .region: "産地"
        case .grapeVariety: "品種"
        case .wineType: "ワイン区分"
        case .knowledgeArea: "知識領域"
        case .difficulty: "難易度"
        case .cognitiveSkill: "思考スキル"
        }
    }
}

enum StudyStatisticsSampleState: String, Hashable {
    case noData
    case insufficient
    case sufficient

    var label: String {
        switch self {
        case .noData: "未学習"
        case .insufficient: "データ不足"
        case .sufficient: "集計可能"
        }
    }
}

struct StudyStatistic: Identifiable, Hashable {
    let dimension: StudyStatisticsDimension
    let value: String
    let questionCount: Int
    let studiedQuestionCount: Int
    let attemptCount: Int
    let correctCount: Int
    let recentAttemptCount: Int
    let recentCorrectCount: Int
    let dueCount: Int
    let sampleState: StudyStatisticsSampleState

    var id: String { "\(dimension.rawValue)|\(value)" }

    var coverage: Double? {
        guard questionCount > 0 else { return nil }
        return Double(studiedQuestionCount) / Double(questionCount)
    }

    var accuracy: Double? {
        guard attemptCount > 0 else { return nil }
        return Double(correctCount) / Double(attemptCount)
    }

    var recentAccuracy: Double? {
        guard recentAttemptCount > 0 else { return nil }
        return Double(recentCorrectCount) / Double(recentAttemptCount)
    }

    func isWeak(below threshold: Double = 0.7) -> Bool {
        guard sampleState == .sufficient, let accuracy else { return false }
        return accuracy < threshold
    }
}

/// Immutable inputs keep the aggregation logic independent from SwiftData and easy to test.
struct StudyAnalyticsQuestion: Hashable {
    let id: String
    let learningOutcome: String
    let geography: [String]
    let countries: [String]
    let regions: [String]
    let grapeVarieties: [String]
    let wineType: String?
    let category: String
    let difficulty: String?
    let cognitiveSkill: String?

    init(
        id: String,
        learningOutcome: String,
        geography: [String] = [],
        countries: [String] = [],
        regions: [String] = [],
        grapeVarieties: [String] = [],
        wineType: String? = nil,
        category: String,
        difficulty: String? = nil,
        cognitiveSkill: String? = nil
    ) {
        self.id = id
        self.learningOutcome = learningOutcome
        self.geography = geography
        self.countries = countries
        self.regions = regions
        self.grapeVarieties = grapeVarieties
        self.wineType = wineType
        self.category = category
        self.difficulty = difficulty
        self.cognitiveSkill = cognitiveSkill
    }

    init(question: StudyQuestion) {
        self.init(
            id: question.id,
            learningOutcome: question.learningOutcome,
            geography: question.geography,
            countries: question.countries,
            regions: question.regions,
            grapeVarieties: question.grapeVarieties,
            wineType: question.wineType,
            category: question.category,
            difficulty: question.difficulty,
            cognitiveSkill: question.cognitiveSkill
        )
    }

    var focusItem: StudyFocusItem {
        StudyFocusItem(
            questionID: id,
            geography: geography,
            countries: countries,
            regions: regions,
            grapeVarieties: grapeVarieties,
            wineType: wineType,
            category: category,
            difficulty: difficulty,
            cognitiveSkill: cognitiveSkill
        )
    }
}

struct StudyAnalyticsProgress: Hashable {
    let questionID: String
    let attemptCount: Int
    let correctCount: Int
    let dueDate: Date
    let lastStudiedAt: Date?
    let lastWasCorrect: Bool?

    init(
        questionID: String,
        attemptCount: Int,
        correctCount: Int,
        dueDate: Date,
        lastStudiedAt: Date? = nil,
        lastWasCorrect: Bool? = nil
    ) {
        self.questionID = questionID
        self.attemptCount = max(0, attemptCount)
        self.correctCount = min(max(0, correctCount), max(0, attemptCount))
        self.dueDate = dueDate
        self.lastStudiedAt = lastStudiedAt
        self.lastWasCorrect = lastWasCorrect
    }

    init(progress: QuestionProgress) {
        self.init(
            questionID: progress.questionID,
            attemptCount: progress.attemptCount,
            correctCount: progress.correctCount,
            dueDate: progress.dueDate,
            lastStudiedAt: progress.lastStudiedAt,
            lastWasCorrect: progress.lastWasCorrect
        )
    }
}

struct StudyAnalyticsAttempt: Hashable {
    let id: String
    let questionID: String
    let isCorrect: Bool
    let studiedAt: Date

    init(id: String, questionID: String, isCorrect: Bool, studiedAt: Date) {
        self.id = id
        self.questionID = questionID
        self.isCorrect = isCorrect
        self.studiedAt = studiedAt
    }

    init(attempt: StudyAttempt) {
        self.init(
            id: attempt.id.uuidString,
            questionID: attempt.questionID,
            isCorrect: attempt.isCorrect,
            studiedAt: attempt.studiedAt
        )
    }
}

enum StudyStatisticsService {
    static let defaultMinimumSampleSize = 5
    static let defaultRecentAttemptLimit = 20

    static func statistics(
        for dimension: StudyStatisticsDimension,
        questions: [StudyQuestion],
        progressRecords: [QuestionProgress],
        attempts: [StudyAttempt],
        now: Date = .now,
        minimumSampleSize: Int = defaultMinimumSampleSize,
        recentAttemptLimit: Int = defaultRecentAttemptLimit
    ) -> [StudyStatistic] {
        statistics(
            for: dimension,
            questions: questions.map { StudyAnalyticsQuestion(question: $0) },
            progressRecords: progressRecords.map { StudyAnalyticsProgress(progress: $0) },
            attempts: attempts.map { StudyAnalyticsAttempt(attempt: $0) },
            now: now,
            minimumSampleSize: minimumSampleSize,
            recentAttemptLimit: recentAttemptLimit
        )
    }

    static func statistics(
        for dimension: StudyStatisticsDimension,
        questions: [StudyAnalyticsQuestion],
        progressRecords: [StudyAnalyticsProgress],
        attempts: [StudyAnalyticsAttempt],
        now: Date,
        minimumSampleSize: Int = defaultMinimumSampleSize,
        recentAttemptLimit: Int = defaultRecentAttemptLimit
    ) -> [StudyStatistic] {
        let minimumSampleSize = max(1, minimumSampleSize)
        let recentAttemptLimit = max(1, recentAttemptLimit)
        let uniqueQuestions = uniqueQuestionsByID(questions)
        let progressByID = preferredProgressByID(progressRecords)
        let attemptsByID = Dictionary(grouping: attempts, by: \StudyAnalyticsAttempt.questionID)

        var questionIDsByValue: [String: Set<String>] = [:]
        for question in uniqueQuestions {
            for value in values(for: dimension, question: question) where !value.isEmpty {
                questionIDsByValue[value, default: []].insert(question.id)
            }
        }

        let result = questionIDsByValue.map { value, questionIDs in
            var studiedQuestionCount = 0
            var attemptCount = 0
            var correctCount = 0
            var dueCount = 0

            for questionID in questionIDs {
                let progress = progressByID[questionID]
                let recordedAttempts = attemptsByID[questionID] ?? []
                let totalAttempts: Int
                let totalCorrect: Int
                if let progress, progress.attemptCount > 0 {
                    totalAttempts = progress.attemptCount
                    totalCorrect = progress.correctCount
                } else {
                    totalAttempts = recordedAttempts.count
                    totalCorrect = recordedAttempts.count(where: \StudyAnalyticsAttempt.isCorrect)
                }

                if totalAttempts > 0 {
                    studiedQuestionCount += 1
                }
                attemptCount += totalAttempts
                correctCount += totalCorrect
                if let progress, progress.attemptCount > 0, progress.dueDate <= now {
                    dueCount += 1
                }
            }

            let recentAttempts = questionIDs
                .flatMap { attemptsByID[$0] ?? [] }
                .sorted { recentAttemptPrecedes($0, $1) }
                .prefix(recentAttemptLimit)
            let recentCorrectCount = recentAttempts.count(where: \StudyAnalyticsAttempt.isCorrect)
            let sampleState: StudyStatisticsSampleState
            if attemptCount == 0 {
                sampleState = .noData
            } else if attemptCount < minimumSampleSize {
                sampleState = .insufficient
            } else {
                sampleState = .sufficient
            }

            return StudyStatistic(
                dimension: dimension,
                value: value,
                questionCount: questionIDs.count,
                studiedQuestionCount: studiedQuestionCount,
                attemptCount: attemptCount,
                correctCount: correctCount,
                recentAttemptCount: recentAttempts.count,
                recentCorrectCount: recentCorrectCount,
                dueCount: dueCount,
                sampleState: sampleState
            )
        }

        return result.sorted { statisticPrecedes($0, $1) }
    }

    static func matchingQuestionIDs(
        for dimension: StudyStatisticsDimension,
        value: String,
        questions: [StudyQuestion]
    ) -> Set<String> {
        matchingQuestionIDs(
            for: dimension,
            value: value,
            questions: questions.map { StudyAnalyticsQuestion(question: $0) }
        )
    }

    static func matchingQuestionIDs(
        for dimension: StudyStatisticsDimension,
        value: String,
        questions: [StudyAnalyticsQuestion]
    ) -> Set<String> {
        let normalizedTarget = normalized(value, for: dimension)
        guard !normalizedTarget.isEmpty else { return [] }
        return Set(
            uniqueQuestionsByID(questions)
                .filter { values(for: dimension, question: $0).contains(normalizedTarget) }
                .map(\.id)
        )
    }

    static func weakest(
        _ statistics: [StudyStatistic],
        below threshold: Double = 0.7,
        limit: Int? = nil
    ) -> [StudyStatistic] {
        let sorted = statistics
            .filter { $0.isWeak(below: threshold) }
            .sorted { lhs, rhs in
                let lhsAccuracy = lhs.accuracy ?? 1
                let rhsAccuracy = rhs.accuracy ?? 1
                if lhsAccuracy != rhsAccuracy { return lhsAccuracy < rhsAccuracy }
                if lhs.attemptCount != rhs.attemptCount { return lhs.attemptCount > rhs.attemptCount }
                return statisticPrecedes(lhs, rhs)
            }
        guard let limit else { return sorted }
        return Array(sorted.prefix(max(0, limit)))
    }

    static func values(
        for dimension: StudyStatisticsDimension,
        question: StudyAnalyticsQuestion
    ) -> Set<String> {
        switch dimension {
        case .learningOutcome:
            let value = question.learningOutcome.trimmingCharacters(in: .whitespacesAndNewlines)
            return value.isEmpty || value == LearningOutcome.all.rawValue ? [] : [value]
        case .country:
            return Set(
                GeographyNormalizer.countries(
                    explicit: question.countries,
                    fallbackGeography: question.geography
                )
            )
        case .region:
            return Set(
                GeographyNormalizer.regions(
                    explicit: question.regions,
                    fallbackGeography: question.geography
                )
            )
        case .grapeVariety:
            return StudyFocusCatalog.normalizedValues(for: .grapeVariety, in: question.focusItem)
        case .wineType:
            return StudyFocusCatalog.normalizedValues(for: .wineType, in: question.focusItem)
        case .knowledgeArea:
            return StudyFocusCatalog.normalizedValues(for: .knowledgeArea, in: question.focusItem)
        case .difficulty:
            return StudyFocusCatalog.normalizedValues(for: .difficulty, in: question.focusItem)
        case .cognitiveSkill:
            return StudyFocusCatalog.normalizedValues(for: .cognitiveSkill, in: question.focusItem)
        }
    }

    private static func normalized(
        _ value: String,
        for dimension: StudyStatisticsDimension
    ) -> String {
        let placeholder = StudyAnalyticsQuestion(
            id: "normalization",
            learningOutcome: dimension == .learningOutcome ? value : "",
            geography: dimension == .country || dimension == .region ? [value] : [],
            countries: dimension == .country ? [value] : [],
            regions: dimension == .region ? [value] : [],
            grapeVarieties: dimension == .grapeVariety ? [value] : [],
            wineType: dimension == .wineType ? value : nil,
            category: dimension == .knowledgeArea ? value : "",
            difficulty: dimension == .difficulty ? value : nil,
            cognitiveSkill: dimension == .cognitiveSkill ? value : nil
        )
        return values(for: dimension, question: placeholder).first ?? ""
    }

    private static func uniqueQuestionsByID(
        _ questions: [StudyAnalyticsQuestion]
    ) -> [StudyAnalyticsQuestion] {
        var byID: [String: StudyAnalyticsQuestion] = [:]
        for question in questions.sorted(by: { $0.id < $1.id }) where byID[question.id] == nil {
            byID[question.id] = question
        }
        return byID.values.sorted { $0.id < $1.id }
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

    private static func recentAttemptPrecedes(
        _ lhs: StudyAnalyticsAttempt,
        _ rhs: StudyAnalyticsAttempt
    ) -> Bool {
        if lhs.studiedAt != rhs.studiedAt { return lhs.studiedAt > rhs.studiedAt }
        if lhs.questionID != rhs.questionID { return lhs.questionID < rhs.questionID }
        return lhs.id < rhs.id
    }

    private static func statisticPrecedes(_ lhs: StudyStatistic, _ rhs: StudyStatistic) -> Bool {
        let lhsRank = rank(lhs.value, dimension: lhs.dimension)
        let rhsRank = rank(rhs.value, dimension: rhs.dimension)
        if lhsRank != rhsRank { return lhsRank < rhsRank }
        return lhs.value.localizedStandardCompare(rhs.value) == .orderedAscending
    }

    private static func rank(_ value: String, dimension: StudyStatisticsDimension) -> Int {
        let order: [String]
        switch dimension {
        case .learningOutcome:
            order = LearningOutcome.allCases.filter { $0 != .all }.map(\.rawValue)
        case .country:
            order = GeographyNormalizer.countryOrder
        case .difficulty:
            order = ["D1", "D2", "D3"]
        case .wineType:
            order = ["非発泡性ワイン", "発泡性ワイン", "酒精強化ワイン", "共通・横断"]
        case .region, .grapeVariety, .knowledgeArea, .cognitiveSkill:
            order = []
        }
        return order.firstIndex(of: value) ?? .max
    }
}
