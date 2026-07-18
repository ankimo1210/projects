import SwiftData
import XCTest
@testable import WSET

@MainActor
final class WrittenTheoryPersistenceTests: XCTestCase {
    func testWrittenPracticeElapsedTimeUsesInjectedCurrentTimeAndFreezesOnSubmission() {
        let startedAt = Date(timeIntervalSince1970: 1_700_000_000)
        let now = startedAt.addingTimeInterval(125)

        XCTAssertEqual(
            WrittenPracticeTiming.elapsedSeconds(
                startedAt: startedAt,
                submittedAt: nil,
                now: now
            ),
            125
        )
        XCTAssertEqual(WrittenPracticeTiming.durationText(125), "2分5秒")
        XCTAssertEqual(
            WrittenPracticeTiming.elapsedSeconds(
                startedAt: startedAt,
                submittedAt: startedAt.addingTimeInterval(90),
                now: now
            ),
            90
        )
        XCTAssertEqual(
            WrittenPracticeTiming.elapsedSeconds(
                startedAt: now,
                submittedAt: nil,
                now: startedAt
            ),
            0
        )
    }

    func testTheorySessionPersistsAnswersFlagsRubricsAndDeadline() {
        let start = Date(timeIntervalSince1970: 1_700_000_000)
        let session = TheoryExamSession(
            startedAt: start,
            durationMinutes: 120,
            multipleChoiceQuestionIDs: ["MCQ-1", "MCQ-2"],
            writtenQuestionIDs: ["SAQ-1"]
        )

        session.selectAnswer(2, for: "MCQ-1")
        session.setWrittenResponse("冷気の滞留を避ける。", for: "SAQ-1")
        session.toggleFlag(for: "MCQ-2")
        session.toggleRubricItem("R1", for: "SAQ-1")

        XCTAssertEqual(session.deadline.timeIntervalSince(start), 120 * 60, accuracy: 1)
        XCTAssertEqual(session.remainingSeconds(at: start.addingTimeInterval(60)), 7_140)
        XCTAssertEqual(session.selectedAnswers["MCQ-1"], 2)
        XCTAssertEqual(session.writtenResponses["SAQ-1"], "冷気の滞留を避ける。")
        XCTAssertTrue(session.flaggedQuestionIDs.contains("MCQ-2"))
        XCTAssertEqual(session.rubricSelections["SAQ-1"], ["R1"])
        XCTAssertEqual(session.answeredQuestionIDs, ["MCQ-1", "SAQ-1"])
    }

    func testTheorySessionRequiresSelfAssessmentBeforeCompletion() {
        let submittedAt = Date(timeIntervalSince1970: 1_700_000_100)
        let session = TheoryExamSession(
            startedAt: submittedAt.addingTimeInterval(-60),
            multipleChoiceQuestionIDs: ["MCQ-1"],
            writtenQuestionIDs: ["SAQ-1"]
        )

        session.complete(writtenAwardedMarks: 3, writtenMaximumMarks: 5)
        XCTAssertEqual(session.status, .inProgress)

        session.beginSelfAssessment(
            multipleChoiceCorrectCount: 1,
            submissionReason: .manual,
            at: submittedAt
        )
        XCTAssertEqual(session.status, .awaitingSelfAssessment)
        XCTAssertEqual(session.submissionReason, .manual)
        XCTAssertEqual(session.submittedAt, submittedAt)
        session.complete(writtenAwardedMarks: 3, writtenMaximumMarks: 5)

        XCTAssertEqual(session.status, .completed)
        XCTAssertEqual(session.totalScore, 4)
        XCTAssertEqual(session.maximumScore, 6)
        XCTAssertNotNil(session.completedAt)
    }

    func testExpiredResumeTransitionIsAppliedOnceAndPreservesAnswers() throws {
        let start = Date(timeIntervalSince1970: 1_700_000_000)
        let session = TheoryExamSession(
            startedAt: start,
            durationMinutes: 120,
            multipleChoiceQuestionIDs: ["MCQ-1"],
            writtenQuestionIDs: ["SAQ-1"]
        )
        session.selectAnswer(2, for: "MCQ-1")
        session.setWrittenResponse("保存済みの解答", for: "SAQ-1")
        let resumedAt = session.deadline.addingTimeInterval(30)
        let transition = try XCTUnwrap(TheoryExamLifecycle.transition(
            status: session.status,
            deadline: session.deadline,
            now: resumedAt,
            trigger: .resume
        ))

        XCTAssertTrue(session.applySubmission(
            transition,
            multipleChoiceCorrectCount: 1
        ))
        XCTAssertEqual(session.status, .awaitingSelfAssessment)
        XCTAssertEqual(session.submissionReason, .timeExpired)
        XCTAssertEqual(session.submittedAt, resumedAt)
        XCTAssertEqual(session.selectedAnswers["MCQ-1"], 2)
        XCTAssertEqual(session.writtenResponses["SAQ-1"], "保存済みの解答")
        XCTAssertFalse(session.applySubmission(
            transition,
            multipleChoiceCorrectCount: 0
        ))

        XCTAssertNil(TheoryExamLifecycle.transition(
            status: session.status,
            deadline: session.deadline,
            now: resumedAt.addingTimeInterval(10),
            trigger: .resume
        ))
    }

    func testAutosavedSessionResumesAndExpiredStatePersists() throws {
        let container = try makeContainer()
        let context = container.mainContext
        let start = Date(timeIntervalSince1970: 1_700_000_000)
        let session = TheoryExamSession(
            startedAt: start,
            durationMinutes: 120,
            multipleChoiceQuestionIDs: ["MCQ-1"],
            writtenQuestionIDs: ["SAQ-1"]
        )
        context.insert(session)
        session.currentIndex = 1
        session.selectAnswer(3, for: "MCQ-1")
        session.setWrittenResponse("途中保存した解答", for: "SAQ-1")
        session.toggleFlag(for: "SAQ-1")
        try context.save()

        let resumedContext = ModelContext(container)
        let resumed = try XCTUnwrap(
            resumedContext.fetch(FetchDescriptor<TheoryExamSession>()).first
        )
        XCTAssertEqual(resumed.status, .inProgress)
        XCTAssertEqual(resumed.currentIndex, 1)
        XCTAssertEqual(resumed.selectedAnswers["MCQ-1"], 3)
        XCTAssertEqual(resumed.writtenResponses["SAQ-1"], "途中保存した解答")
        XCTAssertTrue(resumed.flaggedQuestionIDs.contains("SAQ-1"))

        let resumedAt = resumed.deadline.addingTimeInterval(1)
        let transition = try XCTUnwrap(TheoryExamLifecycle.transition(
            status: resumed.status,
            deadline: resumed.deadline,
            now: resumedAt,
            trigger: .resume
        ))
        XCTAssertTrue(resumed.applySubmission(
            transition,
            multipleChoiceCorrectCount: 0
        ))
        try resumedContext.save()

        let resultContext = ModelContext(container)
        let persisted = try XCTUnwrap(
            resultContext.fetch(FetchDescriptor<TheoryExamSession>()).first
        )
        XCTAssertEqual(persisted.status, .awaitingSelfAssessment)
        XCTAssertEqual(persisted.submissionReason, .timeExpired)
        XCTAssertEqual(persisted.submittedAt, resumedAt)
    }

    func testWrittenAnswerDraftPersistsResponseSubmissionAndRubrics() throws {
        let container = try makeContainer()
        let context = container.mainContext
        let startedAt = Date(timeIntervalSince1970: 1_700_000_000)
        let submittedAt = startedAt.addingTimeInterval(240)
        let draft = WrittenAnswerDraft(
            questionID: "SAQ-1",
            responseText: "入力途中",
            startedAt: startedAt
        )
        context.insert(draft)
        draft.update(
            responseText: "確定前の解答",
            rubricSelections: ["R1", "R3"],
            submittedAt: submittedAt,
            at: submittedAt
        )
        try context.save()

        let restored = try XCTUnwrap(
            context.fetch(FetchDescriptor<WrittenAnswerDraft>()).first
        )
        XCTAssertEqual(restored.questionID, "SAQ-1")
        XCTAssertEqual(restored.responseText, "確定前の解答")
        XCTAssertEqual(restored.rubricSelections, ["R1", "R3"])
        XCTAssertEqual(restored.startedAt, startedAt)
        XCTAssertEqual(restored.submittedAt, submittedAt)
        XCTAssertEqual(restored.updatedAt, submittedAt)
    }

    func testWrittenScoreTrendAndMissingTermIDsAreDeterministic() {
        let older = StudyAttempt(
            questionID: "SAQ-1",
            isCorrect: false,
            rating: 0,
            awardedMarks: 2,
            maximumMarks: 4,
            studiedAt: Date(timeIntervalSince1970: 100)
        )
        let newer = StudyAttempt(
            questionID: "SAQ-1",
            isCorrect: true,
            rating: 3,
            awardedMarks: 3,
            maximumMarks: 4,
            studiedAt: Date(timeIntervalSince1970: 200)
        )
        let points = WrittenPracticeInsights.scorePoints(from: [newer, older])
        XCTAssertEqual(points.map(\.attemptNumber), [1, 2])
        XCTAssertEqual(points.map(\.scorePercent), [50, 75])

        let question = makeWrittenQuestion()
        XCTAssertEqual(
            WrittenPracticeInsights.relatedTermIDs(
                for: question,
                selectedRubricIDs: ["R1"]
            ),
            ["term-b", "term-c"]
        )
    }

    func testBackupRoundTripsWrittenMarksAndTheoryExam() throws {
        let source = try makeContainer()
        let sourceContext = source.mainContext
        let attempt = StudyAttempt(
            questionID: "SAQ-1",
            isCorrect: true,
            rating: 3,
            responseText: "防霜ファンを用いる。",
            awardedMarks: 4,
            maximumMarks: 5,
            rubricSelections: ["R1", "R2"],
            durationSeconds: 180
        )
        sourceContext.insert(attempt)
        let draft = WrittenAnswerDraft(
            questionID: "SAQ-2",
            responseText: "下書きの解答",
            rubricSelections: ["R1"],
            startedAt: Date(timeIntervalSince1970: 1_700_000_000),
            submittedAt: nil,
            updatedAt: Date(timeIntervalSince1970: 1_700_000_100)
        )
        sourceContext.insert(draft)
        let submittedAt = Date(timeIntervalSince1970: 1_700_000_200)
        let theory = TheoryExamSession(
            startedAt: submittedAt.addingTimeInterval(-(120 * 60 + 1)),
            durationMinutes: 120,
            multipleChoiceQuestionIDs: ["MCQ-1"],
            writtenQuestionIDs: ["SAQ-1"]
        )
        theory.selectAnswer(1, for: "MCQ-1")
        theory.setWrittenResponse("防霜ファンを用いる。", for: "SAQ-1")
        theory.toggleFlag(for: "SAQ-1")
        theory.toggleRubricItem("R1", for: "SAQ-1")
        let transition = try XCTUnwrap(TheoryExamLifecycle.transition(
            status: theory.status,
            deadline: theory.deadline,
            now: submittedAt,
            trigger: .resume
        ))
        XCTAssertTrue(theory.applySubmission(
            transition,
            multipleChoiceCorrectCount: 1
        ))
        theory.complete(writtenAwardedMarks: 4, writtenMaximumMarks: 5)
        sourceContext.insert(theory)
        try sourceContext.save()

        let backup = try BackupService.makeBackup(in: sourceContext)
        XCTAssertEqual(backup.theoryExams?.count, 1)
        XCTAssertEqual(backup.attempts.first?.awardedMarks, 4)
        XCTAssertEqual(backup.writtenDrafts?.first?.responseText, "下書きの解答")

        let destination = try makeContainer()
        let result = try BackupService.restore(backup, into: destination.mainContext)
        XCTAssertEqual(result.theoryExamCount, 1)
        XCTAssertEqual(result.writtenDraftCount, 1)

        let restoredAttempt = try XCTUnwrap(
            destination.mainContext.fetch(FetchDescriptor<StudyAttempt>()).first
        )
        XCTAssertEqual(restoredAttempt.responseText, "防霜ファンを用いる。")
        XCTAssertEqual(restoredAttempt.awardedMarks, 4)
        XCTAssertEqual(restoredAttempt.maximumMarks, 5)
        XCTAssertEqual(restoredAttempt.rubricSelections, ["R1", "R2"])
        XCTAssertEqual(restoredAttempt.durationSeconds, 180)

        let restoredDraft = try XCTUnwrap(
            destination.mainContext.fetch(FetchDescriptor<WrittenAnswerDraft>()).first
        )
        XCTAssertEqual(restoredDraft.questionID, "SAQ-2")
        XCTAssertEqual(restoredDraft.responseText, "下書きの解答")
        XCTAssertEqual(restoredDraft.rubricSelections, ["R1"])

        let restoredTheory = try XCTUnwrap(
            destination.mainContext.fetch(FetchDescriptor<TheoryExamSession>()).first
        )
        XCTAssertEqual(restoredTheory.status, .completed)
        XCTAssertEqual(restoredTheory.selectedAnswers["MCQ-1"], 1)
        XCTAssertEqual(restoredTheory.writtenResponses["SAQ-1"], "防霜ファンを用いる。")
        XCTAssertTrue(restoredTheory.flaggedQuestionIDs.contains("SAQ-1"))
        XCTAssertEqual(restoredTheory.rubricSelections["SAQ-1"], ["R1"])
        XCTAssertEqual(restoredTheory.writtenAwardedMarks, 4)
        XCTAssertEqual(restoredTheory.submissionReason, .timeExpired)
        XCTAssertEqual(restoredTheory.submittedAt, submittedAt)
    }

    private func makeWrittenQuestion() -> StudyQuestion {
        StudyQuestion(
            packed: PackedQuestion(
                id: "SAQ-1",
                prompt: "問題",
                answer: "解答",
                explanation: nil,
                choices: [],
                correctAnswerIndex: nil,
                studyMode: "written_answer",
                originalFormat: "short_answer",
                unit: "Theory",
                learningOutcome: "u1_lo1",
                category: "栽培",
                topic: "霜",
                cognitiveSkill: "説明",
                commandVerb: "説明する",
                language: "ja",
                geography: [],
                grapeVarieties: [],
                markAllocation: 4,
                sourceID: "test",
                sourceURL: "",
                qualityScore: 1,
                reviewStatus: "published",
                rubricItems: [
                    WrittenRubricItem(
                        id: "R1",
                        criterion: "要点1",
                        marks: 2,
                        knowledgeTags: ["栽培"],
                        relatedTermIDs: ["term-a"]
                    ),
                    WrittenRubricItem(
                        id: "R2",
                        criterion: "要点2",
                        marks: 1,
                        knowledgeTags: ["栽培"],
                        relatedTermIDs: ["term-b", "term-c"]
                    ),
                    WrittenRubricItem(
                        id: "R3",
                        criterion: "要点3",
                        marks: 1,
                        knowledgeTags: ["栽培"],
                        relatedTermIDs: ["term-b"]
                    ),
                ]
            )
        )
    }

    private func makeContainer() throws -> ModelContainer {
        let configuration = ModelConfiguration(isStoredInMemoryOnly: true)
        return try ModelContainer(
            for: QuestionProgress.self,
            StudyAttempt.self,
            WrittenAnswerDraft.self,
            TastingNote.self,
            MockExamSession.self,
            ReferenceTermProgress.self,
            TheoryExamSession.self,
            configurations: configuration
        )
    }
}
