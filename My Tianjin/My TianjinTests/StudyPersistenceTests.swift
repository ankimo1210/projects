import SwiftData
import XCTest
@testable import My_Tianjin

@MainActor
final class StudyPersistenceTests: XCTestCase {
    private func makeContext() throws -> ModelContext {
        let configuration = ModelConfiguration(isStoredInMemoryOnly: true)
        let container = try ModelContainer(
            for: StudyProgressRecord.self,
            StudySessionRecord.self,
            configurations: configuration
        )
        return ModelContext(container)
    }

    func testAnswerProgressReviewMarkAndSessionRoundTrip() throws {
        let context = try makeContext()
        let now = Date(timeIntervalSince1970: 1_000)
        let progress = try StudyPersistence.recordAnswer(
            itemID: "v1",
            skill: .vocabulary,
            isCorrect: true,
            reviewedAt: now,
            in: context
        )
        XCTAssertEqual(progress.attemptCount, 1)
        XCTAssertEqual(progress.correctCount, 1)

        _ = try StudyPersistence.recordAnswer(
            itemID: "writing-1",
            skill: .writing,
            isCorrect: true,
            reviewedAt: now,
            in: context,
            rubricScore: 7,
            rubricMaximumScore: 10
        )
        let rubricKey = StudyProgressRecord.makeKey(
            itemID: "writing-1",
            skillRawValue: LearningSkill.writing.rawValue
        )
        let rubricRecord = try XCTUnwrap(
            context.fetch(FetchDescriptor<StudyProgressRecord>(
                predicate: #Predicate { $0.key == rubricKey }
            )).first
        )
        XCTAssertEqual(rubricRecord.latestRubricScore, 7)
        XCTAssertEqual(rubricRecord.latestRubricMaximumScore, 10)
        XCTAssertEqual(rubricRecord.latestRubricAt, now)

        try StudyPersistence.markForReview(
            itemID: "v1",
            skill: .vocabulary,
            dueAt: now,
            in: context
        )
        XCTAssertEqual(try StudyPersistence.progressMap(in: context, skill: .vocabulary)["v1"]?.nextReviewAt, now)

        let session = try StudySessionEngine.makeSession(
            items: [
                StudySessionItem(id: "v1", correctOptionID: "v1", distractorOptionIDs: ["v2", "v3", "v4"])
            ],
            configuration: StudySessionConfiguration(mode: .sequential, seed: 1)
        )
        try StudyPersistence.saveSession(session, scopeKey: "test", in: context)
        XCTAssertEqual(try StudyPersistence.loadSession(scopeKey: "test", in: context), session)
        try StudyPersistence.removeSession(scopeKey: "test", in: context)
        XCTAssertNil(try StudyPersistence.loadSession(scopeKey: "test", in: context))
    }

    func testLegacyLearnedIDMigrationRunsOnce() throws {
        let context = try makeContext()
        let suiteName = "StudyPersistenceTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suiteName))
        defer { defaults.removePersistentDomain(forName: suiteName) }
        defaults.set("1,3", forKey: "learnedVocabularyIDs")

        let vocabulary = [
            VocabularyItem(
                id: "official-1",
                officialIndex: 1,
                hanzi: "爱",
                pinyin: "ài",
                japanese: ["愛する"],
                tags: ["legacy-id:1"]
            ),
            VocabularyItem(
                id: "official-2",
                officialIndex: 2,
                hanzi: "八",
                pinyin: "bā",
                japanese: ["八"],
                tags: ["legacy-id:2"]
            )
        ]
        try StudyPersistence.migrateLegacyLearnedIDsIfNeeded(
            vocabulary: vocabulary,
            defaults: defaults,
            in: context
        )
        let map = try StudyPersistence.progressMap(in: context, skill: .vocabulary)
        XCTAssertNotNil(map["official-1"])
        XCTAssertNil(map["official-2"])
        XCTAssertTrue(defaults.bool(forKey: "didMigrateLegacyVocabularyProgressV1"))
    }
}
