import XCTest
@testable import WSET

final class TheoryExamBuilderTests: XCTestCase {
    func testBuildsOfficialTheoryFormat() throws {
        let candidates = makeCandidates(mcq: 75, written: 8)

        let blueprint = try TheoryExamBuilder.build(from: candidates, seed: 42)

        XCTAssertEqual(blueprint.multipleChoiceQuestionIDs.count, 50)
        XCTAssertEqual(blueprint.writtenQuestionIDs.count, 4)
        XCTAssertEqual(blueprint.durationMinutes, 120)
        XCTAssertEqual(Set(blueprint.multipleChoiceQuestionIDs).count, 50)
        XCTAssertEqual(Set(blueprint.writtenQuestionIDs).count, 4)
    }

    func testSelectionIsDeterministicForSeed() throws {
        let candidates = makeCandidates(mcq: 75, written: 8)
        XCTAssertEqual(
            try TheoryExamBuilder.build(from: candidates, seed: 7),
            try TheoryExamBuilder.build(from: Array(candidates.reversed()), seed: 7)
        )
    }

    func testBalancesLearningOutcomes() throws {
        let candidates = makeCandidates(mcq: 75, written: 8)
        let blueprint = try TheoryExamBuilder.build(from: candidates, seed: 1)
        let lookup = Dictionary(uniqueKeysWithValues: candidates.map { ($0.id, $0) })
        let counts = Dictionary(grouping: blueprint.multipleChoiceQuestionIDs) {
            lookup[$0]?.learningOutcome ?? ""
        }.mapValues(\.count)

        XCTAssertEqual(Set(counts.values), [10])
    }

    func testRejectsInsufficientQuestionBanks() {
        XCTAssertThrowsError(try TheoryExamBuilder.build(
            from: makeCandidates(mcq: 49, written: 4),
            seed: 1
        )) { error in
            XCTAssertEqual(
                error as? TheoryExamBuilderError,
                .insufficientMultipleChoice(required: 50, available: 49)
            )
        }

        XCTAssertThrowsError(try TheoryExamBuilder.build(
            from: makeCandidates(mcq: 50, written: 3),
            seed: 1
        )) { error in
            XCTAssertEqual(
                error as? TheoryExamBuilderError,
                .insufficientWritten(required: 4, available: 3)
            )
        }
    }

    func testLifecycleCreatesManualSubmissionBeforeDeadline() throws {
        let deadline = Date(timeIntervalSince1970: 10_000)
        let now = deadline.addingTimeInterval(-1)

        let transition = try XCTUnwrap(TheoryExamLifecycle.transition(
            status: .inProgress,
            deadline: deadline,
            now: now,
            trigger: .manual
        ))

        XCTAssertEqual(transition.fromStatus, .inProgress)
        XCTAssertEqual(transition.toStatus, .awaitingSelfAssessment)
        XCTAssertEqual(transition.submissionReason, .manual)
        XCTAssertEqual(transition.submittedAt, now)
    }

    func testLifecycleUsesTimeExpiredAtDeadlineForTimerResumeAndManual() throws {
        let deadline = Date(timeIntervalSince1970: 10_000)
        XCTAssertNil(TheoryExamLifecycle.transition(
            status: .inProgress,
            deadline: deadline,
            now: deadline.addingTimeInterval(-1),
            trigger: .resume
        ))

        for trigger in [
            TheoryExamSubmissionTrigger.timerTick,
            .resume,
            .manual,
        ] {
            let transition = try XCTUnwrap(TheoryExamLifecycle.transition(
                status: .inProgress,
                deadline: deadline,
                now: deadline,
                trigger: trigger
            ))
            XCTAssertEqual(transition.submissionReason, .timeExpired)
            XCTAssertEqual(transition.toStatus, .awaitingSelfAssessment)
        }
    }

    func testLifecycleDoesNotResubmitAfterStateHasAdvanced() {
        let deadline = Date(timeIntervalSince1970: 10_000)
        for status in [TheoryExamStatus.awaitingSelfAssessment, .completed] {
            XCTAssertNil(TheoryExamLifecycle.transition(
                status: status,
                deadline: deadline,
                now: deadline.addingTimeInterval(1),
                trigger: .resume
            ))
        }
    }

    func testLearningOutcomeScoresCombineMultipleChoiceAndWrittenRubrics() {
        let questions = [
            TheoryExamScoringQuestion(
                id: "MCQ-1",
                learningOutcome: "u1_lo1",
                studyMode: "multiple_choice",
                correctAnswerIndex: 1,
                rubricMarksByID: [:]
            ),
            TheoryExamScoringQuestion(
                id: "MCQ-2",
                learningOutcome: "u1_lo1",
                studyMode: "multiple_choice",
                correctAnswerIndex: 0,
                rubricMarksByID: [:]
            ),
            TheoryExamScoringQuestion(
                id: "SAQ-1",
                learningOutcome: "u1_lo1",
                studyMode: "written_answer",
                correctAnswerIndex: nil,
                rubricMarksByID: ["R1": 2, "R2": 3]
            ),
            TheoryExamScoringQuestion(
                id: "MCQ-3",
                learningOutcome: "u1_lo2",
                studyMode: "multiple_choice",
                correctAnswerIndex: 2,
                rubricMarksByID: [:]
            ),
            TheoryExamScoringQuestion(
                id: "SAQ-2",
                learningOutcome: "u1_lo2",
                studyMode: "written_answer",
                correctAnswerIndex: nil,
                rubricMarksByID: ["R3": 4]
            ),
        ]

        let scores = TheoryExamScoreCalculator.learningOutcomeScores(
            questions: questions,
            selectedAnswers: ["MCQ-1": 1, "MCQ-2": 2],
            rubricSelections: ["SAQ-1": ["R1", "unknown"]]
        )

        XCTAssertEqual(scores, [
            TheoryExamLearningOutcomeScore(
                learningOutcome: "u1_lo1",
                multipleChoiceAwarded: 1,
                multipleChoiceMaximum: 2,
                writtenAwarded: 2,
                writtenMaximum: 5
            ),
            TheoryExamLearningOutcomeScore(
                learningOutcome: "u1_lo2",
                multipleChoiceAwarded: 0,
                multipleChoiceMaximum: 1,
                writtenAwarded: 0,
                writtenMaximum: 4
            ),
        ])
        XCTAssertEqual(scores[0].totalAwarded, 3)
        XCTAssertEqual(scores[0].totalMaximum, 7)
    }

    private func makeCandidates(mcq: Int, written: Int) -> [TheoryExamCandidate] {
        let outcomes = ["u1_lo1", "u1_lo2", "u1_lo3", "u1_lo4", "u1_lo5"]
        let multipleChoice = (0..<mcq).map { index in
            TheoryExamCandidate(
                id: "MCQ-\(index)",
                learningOutcome: outcomes[index % outcomes.count],
                studyMode: "multiple_choice"
            )
        }
        let writtenQuestions = (0..<written).map { index in
            TheoryExamCandidate(
                id: "SAQ-\(index)",
                learningOutcome: outcomes[index % outcomes.count],
                studyMode: "written_answer"
            )
        }
        return multipleChoice + writtenQuestions
    }
}
