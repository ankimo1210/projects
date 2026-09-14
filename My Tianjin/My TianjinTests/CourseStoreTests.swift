import Foundation
import SwiftData
import XCTest
@testable import My_Tianjin

@MainActor
final class CourseStoreTests: XCTestCase {
    func testSameVersionSnapshotResumesFromRealInMemoryStore() throws {
        let container = try makeContainer()
        let repository = try makeRepository()
        let first = CourseStore(repository: repository)
        XCTAssertTrue(first.load(in: container))
        XCTAssertTrue(first.start(minutes: 3))
        XCTAssertTrue(first.submit(optionID: "q-1-wrong-a"))

        let restored = CourseStore(repository: repository)
        XCTAssertTrue(restored.load(in: container))

        XCTAssertEqual(restored.snapshot, first.snapshot)
        XCTAssertEqual(restored.snapshot?.activeSession?.currentQuestionID, "q-1")
        XCTAssertEqual(restored.snapshot?.activeSession?.currentAttempt?.selectedOptionID, "q-1-wrong-a")
    }

    func testIncompatibleSnapshotIsRejectedWithoutOverwritingPayload() throws {
        let container = try makeContainer()
        let context = ModelContext(container)
        context.autosaveEnabled = false
        let lesson = makeLesson()
        let incompatible = CourseSnapshot(
            schemaVersion: CourseSnapshot.supportedSchemaVersion,
            courseID: lesson.id,
            contentVersion: "older-content",
            progress: [:], attempts: [], sessions: []
        )
        let originalPayload = try JSONEncoder().encode(incompatible)
        context.insert(StudySessionRecord(scopeKey: CourseStore.scopeKey, payload: originalPayload))
        try context.save()

        let store = CourseStore(repository: try makeRepository())
        XCTAssertFalse(store.load(in: container))
        XCTAssertNil(store.snapshot)
        XCTAssertNotNil(store.errorMessage)

        let scopeKey = CourseStore.scopeKey
        let descriptor = FetchDescriptor<StudySessionRecord>(
            predicate: #Predicate { $0.scopeKey == scopeKey }
        )
        XCTAssertEqual(try context.fetch(descriptor).first?.payload, originalPayload)
    }

    func testSaveFailureRollsBackAndRetryDoesNotDuplicateProgress() throws {
        let container = try makeContainer()
        let saveGate = SaveGate(failOnCall: 2)
        let store = CourseStore(
            repository: try makeRepository(),
            saveAction: saveGate.save
        )
        XCTAssertTrue(store.load(in: container))
        XCTAssertTrue(store.start(minutes: 3))

        XCTAssertFalse(store.submit(optionID: "q-1-wrong-a"))
        XCTAssertEqual(store.snapshot?.progress["q-1"]?.attemptCount, nil)
        XCTAssertEqual(store.snapshot?.activeSession?.currentAttempt, nil)
        XCTAssertNotNil(store.errorMessage)

        XCTAssertTrue(store.submit(optionID: "q-1-wrong-a"))
        XCTAssertEqual(store.snapshot?.progress["q-1"]?.attemptCount, 1)
        XCTAssertEqual(store.snapshot?.attempts.count, 1)
        XCTAssertEqual(store.snapshot?.activeSession?.attempts.count, 1)

        let restored = CourseStore(repository: try makeRepository())
        XCTAssertTrue(restored.load(in: container))
        XCTAssertEqual(restored.snapshot?.progress["q-1"]?.attemptCount, 1)
        XCTAssertEqual(restored.snapshot?.attempts.count, 1)
    }

    func testCorruptSavedPayloadIsRejectedWithoutReplacement() throws {
        let container = try makeContainer()
        let context = ModelContext(container)
        context.autosaveEnabled = false
        let corruptPayload = Data("{not-json".utf8)
        context.insert(StudySessionRecord(scopeKey: CourseStore.scopeKey, payload: corruptPayload))
        try context.save()

        let store = CourseStore(repository: try makeRepository())
        XCTAssertFalse(store.load(in: container))
        XCTAssertNil(store.snapshot)

        let scopeKey = CourseStore.scopeKey
        let descriptor = FetchDescriptor<StudySessionRecord>(
            predicate: #Predicate { $0.scopeKey == scopeKey }
        )
        XCTAssertEqual(try context.fetch(descriptor).first?.payload, corruptPayload)
    }

    func testAdvancePersistsCompletedSessionBeforePublishing() throws {
        let container = try makeContainer()
        let store = CourseStore(repository: try makeRepository())
        XCTAssertTrue(store.load(in: container))
        XCTAssertTrue(store.start(minutes: 3))

        for index in 1...3 {
            XCTAssertTrue(store.submit(optionID: "q-\(index)-correct"))
            XCTAssertTrue(store.advance())
        }

        XCTAssertNil(store.snapshot?.activeSession)
        XCTAssertNotNil(store.snapshot?.sessions.last?.completedAt)
        XCTAssertEqual(store.snapshot?.sessions.last?.correctCount, 3)
    }

    private func makeContainer() throws -> ModelContainer {
        try ModelContainer(
            for: StudyProgressRecord.self,
            StudySessionRecord.self,
            configurations: ModelConfiguration(isStoredInMemoryOnly: true)
        )
    }

    private func makeRepository() throws -> CourseRepository {
        let data = try JSONEncoder().encode(makeLesson())
        return CourseRepository(dataLoader: { data })
    }
}

@MainActor
private final class SaveGate {
    private let failOnCall: Int
    private var callCount = 0

    init(failOnCall: Int) {
        self.failOnCall = failOnCall
    }

    func save(_ context: ModelContext) throws {
        callCount += 1
        if callCount == failOnCall {
            throw SaveFailure.expected
        }
        try context.save()
    }

    private enum SaveFailure: Error {
        case expected
    }
}
