import Foundation
import SwiftData

@Model
final class StudyProgressRecord {
    @Attribute(.unique) var key: String
    var itemID: String
    var skillRawValue: String
    var attemptCount: Int
    var correctCount: Int
    var incorrectCount: Int
    var currentStreak: Int
    var reviewStage: Int
    var lastReviewedAt: Date?
    var nextReviewAt: Date?
    var latestRubricScore: Int?
    var latestRubricMaximumScore: Int?
    var latestRubricAt: Date?

    init(
        itemID: String,
        skillRawValue: String,
        attemptCount: Int = 0,
        correctCount: Int = 0,
        incorrectCount: Int = 0,
        currentStreak: Int = 0,
        reviewStage: Int = 0,
        lastReviewedAt: Date? = nil,
        nextReviewAt: Date? = nil,
        latestRubricScore: Int? = nil,
        latestRubricMaximumScore: Int? = nil,
        latestRubricAt: Date? = nil
    ) {
        key = Self.makeKey(itemID: itemID, skillRawValue: skillRawValue)
        self.itemID = itemID
        self.skillRawValue = skillRawValue
        self.attemptCount = attemptCount
        self.correctCount = correctCount
        self.incorrectCount = incorrectCount
        self.currentStreak = currentStreak
        self.reviewStage = reviewStage
        self.lastReviewedAt = lastReviewedAt
        self.nextReviewAt = nextReviewAt
        self.latestRubricScore = latestRubricScore
        self.latestRubricMaximumScore = latestRubricMaximumScore
        self.latestRubricAt = latestRubricAt
    }

    var coreValue: StudyItemProgress {
        StudyItemProgress(
            itemID: itemID,
            attemptCount: attemptCount,
            correctCount: correctCount,
            incorrectCount: incorrectCount,
            currentStreak: currentStreak,
            reviewStage: reviewStage,
            lastReviewedAt: lastReviewedAt,
            nextReviewAt: nextReviewAt
        )
    }

    func apply(_ progress: StudyItemProgress) {
        attemptCount = progress.attemptCount
        correctCount = progress.correctCount
        incorrectCount = progress.incorrectCount
        currentStreak = progress.currentStreak
        reviewStage = progress.reviewStage
        lastReviewedAt = progress.lastReviewedAt
        nextReviewAt = progress.nextReviewAt
    }

    static func makeKey(itemID: String, skillRawValue: String) -> String {
        "\(skillRawValue)::\(itemID)"
    }
}

@Model
final class StudySessionRecord {
    @Attribute(.unique) var scopeKey: String
    var payload: Data
    var updatedAt: Date

    init(scopeKey: String, payload: Data, updatedAt: Date = Date()) {
        self.scopeKey = scopeKey
        self.payload = payload
        self.updatedAt = updatedAt
    }
}

@MainActor
enum StudyPersistence {
    static func progressMap(
        in context: ModelContext,
        skill: LearningSkill
    ) throws -> [String: StudyItemProgress] {
        let skillRawValue = skill.rawValue
        let descriptor = FetchDescriptor<StudyProgressRecord>(
            predicate: #Predicate { $0.skillRawValue == skillRawValue }
        )
        return Dictionary(
            uniqueKeysWithValues: try context.fetch(descriptor).map { ($0.itemID, $0.coreValue) }
        )
    }

    @discardableResult
    static func recordAnswer(
        itemID: String,
        skill: LearningSkill,
        isCorrect: Bool,
        reviewedAt: Date = Date(),
        in context: ModelContext,
        scheduler: ReviewScheduler? = nil,
        rubricScore: Int? = nil,
        rubricMaximumScore: Int? = nil
    ) throws -> StudyItemProgress {
        let key = StudyProgressRecord.makeKey(itemID: itemID, skillRawValue: skill.rawValue)
        let descriptor = FetchDescriptor<StudyProgressRecord>(
            predicate: #Predicate { $0.key == key }
        )
        let existing = try context.fetch(descriptor).first
        let scheduler = scheduler ?? ReviewScheduler()
        let updated = scheduler.updatedProgress(
            itemID: itemID,
            previous: existing?.coreValue,
            result: isCorrect ? .correct : .incorrect,
            reviewedAt: reviewedAt
        )
        let record: StudyProgressRecord
        if let existing {
            record = existing
        } else {
            record = StudyProgressRecord(itemID: itemID, skillRawValue: skill.rawValue)
            context.insert(record)
        }
        record.apply(updated)
        if let rubricScore, let rubricMaximumScore, rubricMaximumScore > 0 {
            record.latestRubricScore = min(max(rubricScore, 0), rubricMaximumScore)
            record.latestRubricMaximumScore = rubricMaximumScore
            record.latestRubricAt = reviewedAt
        }
        try context.save()
        return updated
    }

    static func saveSession(
        _ session: StudySessionState,
        scopeKey: String,
        in context: ModelContext
    ) throws {
        let payload = try session.encoded()
        let descriptor = FetchDescriptor<StudySessionRecord>(
            predicate: #Predicate { $0.scopeKey == scopeKey }
        )
        if let existing = try context.fetch(descriptor).first {
            existing.payload = payload
            existing.updatedAt = Date()
        } else {
            context.insert(StudySessionRecord(scopeKey: scopeKey, payload: payload))
        }
        try context.save()
    }

    static func loadSession(
        scopeKey: String,
        in context: ModelContext
    ) throws -> StudySessionState? {
        let descriptor = FetchDescriptor<StudySessionRecord>(
            predicate: #Predicate { $0.scopeKey == scopeKey }
        )
        guard let record = try context.fetch(descriptor).first else { return nil }
        return try StudySessionState.restore(from: record.payload)
    }

    static func removeSession(scopeKey: String, in context: ModelContext) throws {
        let descriptor = FetchDescriptor<StudySessionRecord>(
            predicate: #Predicate { $0.scopeKey == scopeKey }
        )
        for record in try context.fetch(descriptor) {
            context.delete(record)
        }
        try context.save()
    }

    static func markForReview(
        itemID: String,
        skill: LearningSkill,
        dueAt: Date = Date(),
        in context: ModelContext
    ) throws {
        let key = StudyProgressRecord.makeKey(itemID: itemID, skillRawValue: skill.rawValue)
        let descriptor = FetchDescriptor<StudyProgressRecord>(
            predicate: #Predicate { $0.key == key }
        )
        if let existing = try context.fetch(descriptor).first {
            if existing.nextReviewAt == nil || existing.nextReviewAt! > dueAt {
                existing.nextReviewAt = dueAt
            }
        } else {
            context.insert(StudyProgressRecord(
                itemID: itemID,
                skillRawValue: skill.rawValue,
                nextReviewAt: dueAt
            ))
        }
        try context.save()
    }

    static func migrateLegacyLearnedIDsIfNeeded(
        vocabulary: [VocabularyItem],
        defaults: UserDefaults = .standard,
        in context: ModelContext
    ) throws {
        let migrationKey = "didMigrateLegacyVocabularyProgressV1"
        guard !defaults.bool(forKey: migrationKey) else { return }
        let rawValue = defaults.string(forKey: "learnedVocabularyIDs") ?? ""
        let legacyIDs = Set(rawValue.split(separator: ",").compactMap { Int($0) })
        guard !legacyIDs.isEmpty else {
            defaults.set(true, forKey: migrationKey)
            return
        }

        for item in vocabulary {
            let legacyID = item.tags
                .first(where: { $0.hasPrefix("legacy-id:") })
                .flatMap { Int($0.dropFirst("legacy-id:".count)) }
            guard let legacyID, legacyIDs.contains(legacyID) else { continue }
            let key = StudyProgressRecord.makeKey(
                itemID: item.id,
                skillRawValue: LearningSkill.vocabulary.rawValue
            )
            let descriptor = FetchDescriptor<StudyProgressRecord>(
                predicate: #Predicate { $0.key == key }
            )
            if try context.fetch(descriptor).isEmpty {
                context.insert(StudyProgressRecord(
                    itemID: item.id,
                    skillRawValue: LearningSkill.vocabulary.rawValue,
                    attemptCount: 1,
                    correctCount: 1,
                    currentStreak: 1,
                    reviewStage: 1,
                    lastReviewedAt: Date(),
                    nextReviewAt: Date().addingTimeInterval(86_400)
                ))
            }
        }
        try context.save()
        defaults.set(true, forKey: migrationKey)
    }
}
