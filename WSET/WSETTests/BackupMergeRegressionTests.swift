import SwiftData
import XCTest
@testable import WSET

@MainActor
final class BackupMergeRegressionTests: XCTestCase {
    func testOlderBackupPreservesNewerAnswersClearsFlagsAndPosition() throws {
        let container = try makeContainer()
        let context = container.mainContext
        let session = makeSession(in: context)
        session.selectAnswer(0, for: "MCQ-1")
        session.setWrittenResponse("以前の回答", for: "SAQ-1")
        session.toggleFlag(for: "MCQ-1")
        try context.save()
        let backup = try BackupService.makeBackup(in: context)

        session.selectAnswer(1, for: "MCQ-1")
        session.selectAnswer(2, for: "MCQ-2")
        session.setWrittenResponse("", for: "SAQ-1")
        session.setWrittenResponse("追加した回答", for: "SAQ-2")
        session.toggleFlag(for: "MCQ-1")
        session.toggleFlag(for: "MCQ-2")
        session.currentIndex = 1
        try context.save()

        // Repeating the restore must not roll back edits or re-add removed flags.
        for _ in 0..<2 {
            _ = try BackupService.restore(backup, into: context)
            XCTAssertEqual(session.selectedAnswers, ["MCQ-1": 1, "MCQ-2": 2])
            XCTAssertEqual(session.writtenResponses, ["SAQ-1": "", "SAQ-2": "追加した回答"])
            XCTAssertEqual(session.flaggedQuestionIDs, ["MCQ-2"])
            XCTAssertEqual(session.currentIndex, 1)
        }
    }

    func testSamePhaseBackupFillsMissingAnswersWithoutReplacingLocalConflicts() throws {
        let source = try makeContainer()
        let remote = makeSession(in: source.mainContext)
        remote.selectAnswer(0, for: "MCQ-1")
        remote.selectAnswer(2, for: "MCQ-2")
        remote.setWrittenResponse("バックアップの回答", for: "SAQ-1")
        remote.setWrittenResponse("端末にない回答", for: "SAQ-2")
        try source.mainContext.save()
        // JSON backups round fractional dates to whole seconds. They still refer
        // to the same session, and must still fill missing local answers.
        let backup = try StudyBackupDocument.decode(
            StudyBackupDocument.encoder.encode(BackupService.makeBackup(in: source.mainContext))
        )

        let destination = try makeContainer()
        let local = makeSession(in: destination.mainContext, id: remote.id)
        local.selectAnswer(1, for: "MCQ-1")
        local.setWrittenResponse("端末の回答", for: "SAQ-1")
        try destination.mainContext.save()

        _ = try BackupService.restore(backup, into: destination.mainContext)

        XCTAssertEqual(local.selectedAnswers, ["MCQ-1": 1, "MCQ-2": 2])
        XCTAssertEqual(local.writtenResponses, ["SAQ-1": "端末の回答", "SAQ-2": "端末にない回答"])
    }

    func testOlderSelfAssessmentBackupDoesNotUndoRubricDeselection() throws {
        let container = try makeContainer()
        let session = makeSession(in: container.mainContext)
        session.beginSelfAssessment(
            multipleChoiceCorrectCount: 1,
            at: session.startedAt.addingTimeInterval(60)
        )
        session.toggleRubricItem("R1", for: "SAQ-1")
        try container.mainContext.save()
        let backup = try BackupService.makeBackup(in: container.mainContext)
        session.toggleRubricItem("R1", for: "SAQ-1")
        session.toggleRubricItem("R2", for: "SAQ-2")
        try container.mainContext.save()

        _ = try BackupService.restore(backup, into: container.mainContext)

        XCTAssertEqual(session.status, .awaitingSelfAssessment)
        XCTAssertEqual(session.rubricSelections, ["SAQ-1": [], "SAQ-2": ["R2"]])
    }

    func testSameCompletedBackupDoesNotResetCompletionRecorded() throws {
        let container = try makeContainer()
        let session = makeSession(in: container.mainContext)
        complete(session)
        try container.mainContext.save()
        let backup = try BackupService.makeBackup(in: container.mainContext)
        session.completionRecorded = true
        try container.mainContext.save()

        _ = try BackupService.restore(backup, into: container.mainContext)

        XCTAssertEqual(session.status, .completed)
        XCTAssertTrue(session.completionRecorded)
    }

    func testSubmittedAnswersStayConsistentWithTheirLocalScore() throws {
        let source = try makeContainer()
        let remote = makeSession(in: source.mainContext)
        remote.selectAnswer(0, for: "MCQ-1")
        remote.setWrittenResponse("別端末の提出済み回答", for: "SAQ-1")
        remote.beginSelfAssessment(
            multipleChoiceCorrectCount: 1,
            at: remote.startedAt.addingTimeInterval(120)
        )
        remote.toggleRubricItem("R1", for: "SAQ-1")
        try source.mainContext.save()
        let backup = try BackupService.makeBackup(in: source.mainContext)

        let destination = try makeContainer()
        let local = makeSession(in: destination.mainContext, id: remote.id)
        local.selectAnswer(2, for: "MCQ-2")
        local.setWrittenResponse("端末の提出済み回答", for: "SAQ-2")
        local.beginSelfAssessment(
            multipleChoiceCorrectCount: 0,
            at: local.startedAt.addingTimeInterval(60)
        )
        try destination.mainContext.save()

        _ = try BackupService.restore(backup, into: destination.mainContext)

        XCTAssertEqual(local.selectedAnswers, ["MCQ-2": 2])
        XCTAssertEqual(local.writtenResponses, ["SAQ-2": "端末の提出済み回答"])
        XCTAssertEqual(local.multipleChoiceCorrectCount, 0)
        XCTAssertTrue(local.rubricSelections.isEmpty)
    }

    func testCompletedBackupStillAdvancesAnUnfinishedLocalSession() throws {
        let source = try makeContainer()
        let remote = makeSession(in: source.mainContext)
        remote.selectAnswer(2, for: "MCQ-2")
        complete(remote)
        try source.mainContext.save()
        let backup = try BackupService.makeBackup(in: source.mainContext)
        let destination = try makeContainer()
        let local = makeSession(in: destination.mainContext, id: remote.id)
        try destination.mainContext.save()

        _ = try BackupService.restore(backup, into: destination.mainContext)

        XCTAssertEqual(local.status, .completed)
        XCTAssertEqual(local.selectedAnswers["MCQ-2"], 2)
        XCTAssertEqual(local.writtenAwardedMarks, 3)
        XCTAssertEqual(local.completedAt, remote.completedAt)
    }

    private func complete(_ session: TheoryExamSession) {
        session.beginSelfAssessment(
            multipleChoiceCorrectCount: 1,
            at: session.startedAt.addingTimeInterval(60)
        )
        session.complete(
            writtenAwardedMarks: 3,
            writtenMaximumMarks: 5,
            at: session.startedAt.addingTimeInterval(120)
        )
    }

    private func makeSession(in context: ModelContext, id: UUID = UUID()) -> TheoryExamSession {
        let session = TheoryExamSession(
            id: id,
            startedAt: Date(timeIntervalSince1970: 1_700_000_000.25),
            multipleChoiceQuestionIDs: ["MCQ-1", "MCQ-2"],
            writtenQuestionIDs: ["SAQ-1", "SAQ-2"]
        )
        context.insert(session)
        return session
    }

    private func makeContainer() throws -> ModelContainer {
        try ModelContainer(
            for: StudyQuestion.self, QuestionProgress.self, StudyAttempt.self,
            WrittenAnswerDraft.self, TastingNote.self, MockExamSession.self,
            TheoryExamSession.self, ReferenceTermProgress.self,
            configurations: ModelConfiguration(isStoredInMemoryOnly: true)
        )
    }
}
