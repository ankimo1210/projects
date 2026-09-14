import Foundation
import XCTest
@testable import My_Tianjin

final class CourseEngineTests: XCTestCase {
    private let now = Date(timeIntervalSince1970: 2_000_000_000)

    func testDueQuestionsComeBeforeNewQuestionsAndRespectThreeQuestionCap() throws {
        let lesson = makeLesson(count: 5)
        let progress = [
            "q-3": StudyItemProgress(itemID: "q-3", attemptCount: 1, correctCount: 1, nextReviewAt: now.addingTimeInterval(-10)),
            "q-2": StudyItemProgress(itemID: "q-2", attemptCount: 1, incorrectCount: 1, nextReviewAt: now.addingTimeInterval(-20))
        ]

        let session = try XCTUnwrap(CourseEngine.makeSession(
            lesson: lesson,
            progress: progress,
            minutes: 3,
            reviewOnly: false,
            now: now
        ))

        XCTAssertEqual(session.questionIDs, ["q-2", "q-3", "q-1"])
    }

    func testFutureDueAnsweredQuestionsDoNotPadSession() throws {
        let lesson = makeLesson(count: 3)
        let progress = [
            "q-1": StudyItemProgress(itemID: "q-1", attemptCount: 1, correctCount: 1, nextReviewAt: now.addingTimeInterval(60)),
            "q-2": StudyItemProgress(itemID: "q-2", attemptCount: 1, correctCount: 1, nextReviewAt: now.addingTimeInterval(-1))
        ]

        let session = try XCTUnwrap(CourseEngine.makeSession(
            lesson: lesson,
            progress: progress,
            minutes: 3,
            reviewOnly: false,
            now: now
        ))

        XCTAssertEqual(session.questionIDs, ["q-2", "q-3"])
    }

    func testSelectionIgnoresUnrelatedProgressAndIsDeterministic() throws {
        let lesson = makeLesson(count: 4)
        let progress = [
            "outside": StudyItemProgress(itemID: "outside", nextReviewAt: now.addingTimeInterval(-100)),
            "q-4": StudyItemProgress(itemID: "q-4", attemptCount: 1, incorrectCount: 1, nextReviewAt: now.addingTimeInterval(-1))
        ]

        let first = CourseEngine.makeSession(lesson: lesson, progress: progress, minutes: 10, reviewOnly: false, now: now)
        let second = CourseEngine.makeSession(lesson: lesson, progress: progress, minutes: 10, reviewOnly: false, now: now)

        XCTAssertEqual(first?.questionIDs, ["q-4", "q-1", "q-2", "q-3"])
        XCTAssertEqual(second?.questionIDs, first?.questionIDs)
    }

    func testReviewOnlyReturnsNilWhenNothingIsDue() {
        let lesson = makeLesson(count: 2)
        let progress = [
            "q-1": StudyItemProgress(itemID: "q-1", attemptCount: 1, correctCount: 1, nextReviewAt: now.addingTimeInterval(1))
        ]

        XCTAssertNil(CourseEngine.makeSession(
            lesson: lesson,
            progress: progress,
            minutes: 3,
            reviewOnly: true,
            now: now
        ))
    }

    func testWrongAndCorrectAnswersUseExistingReviewSchedulerIntervals() throws {
        let lesson = makeLesson(count: 2)
        let firstSession = try XCTUnwrap(CourseEngine.makeSession(
            lesson: lesson, progress: [:], minutes: 3, reviewOnly: false, now: now
        ))
        var snapshot = CourseSnapshot(lesson: lesson, sessions: [firstSession])

        snapshot = try CourseEngine.submit(
            snapshot: snapshot,
            lesson: lesson,
            sessionID: firstSession.id,
            attemptID: UUID(),
            optionID: "q-1-wrong-a",
            now: now
        )
        XCTAssertEqual(snapshot.progress["q-1"]?.nextReviewAt, now.addingTimeInterval(10 * 60))

        snapshot = try CourseEngine.advance(snapshot: snapshot, sessionID: firstSession.id, now: now)
        snapshot = try CourseEngine.submit(
            snapshot: snapshot,
            lesson: lesson,
            sessionID: firstSession.id,
            attemptID: UUID(),
            optionID: "q-2-correct",
            now: now
        )
        XCTAssertEqual(snapshot.progress["q-2"]?.nextReviewAt, now.addingTimeInterval(86_400))
    }

    func testDuplicateAttemptIDIsIdempotentButConflictingRetryIsRejected() throws {
        let lesson = makeLesson(count: 1)
        let session = try XCTUnwrap(CourseEngine.makeSession(
            lesson: lesson, progress: [:], minutes: 3, reviewOnly: false, now: now
        ))
        let attemptID = UUID()
        let initial = CourseSnapshot(lesson: lesson, sessions: [session])
        let submitted = try CourseEngine.submit(
            snapshot: initial,
            lesson: lesson,
            sessionID: session.id,
            attemptID: attemptID,
            optionID: "q-1-correct",
            now: now
        )

        let retried = try CourseEngine.submit(
            snapshot: submitted,
            lesson: lesson,
            sessionID: session.id,
            attemptID: attemptID,
            optionID: "q-1-correct",
            now: now
        )

        XCTAssertEqual(retried, submitted)
        XCTAssertEqual(retried.progress["q-1"]?.attemptCount, 1)
        XCTAssertThrowsError(try CourseEngine.submit(
            snapshot: submitted,
            lesson: lesson,
            sessionID: session.id,
            attemptID: attemptID,
            optionID: "q-1-correct",
            now: now.addingTimeInterval(30)
        ))
        XCTAssertThrowsError(try CourseEngine.submit(
            snapshot: submitted,
            lesson: lesson,
            sessionID: session.id,
            attemptID: attemptID,
            optionID: "q-1-wrong-a",
            now: now
        ))
    }

    func testDifferentAttemptCannotReplaceSubmittedAnswer() throws {
        let lesson = makeLesson(count: 1)
        let session = try XCTUnwrap(CourseEngine.makeSession(
            lesson: lesson, progress: [:], minutes: 3, reviewOnly: false, now: now
        ))
        let submitted = try CourseEngine.submit(
            snapshot: CourseSnapshot(lesson: lesson, sessions: [session]),
            lesson: lesson,
            sessionID: session.id,
            attemptID: UUID(),
            optionID: "q-1-correct",
            now: now
        )

        XCTAssertThrowsError(try CourseEngine.submit(
            snapshot: submitted,
            lesson: lesson,
            sessionID: session.id,
            attemptID: UUID(),
            optionID: "q-1-wrong-a",
            now: now
        )) { error in
            XCTAssertEqual(error as? CourseEngineError, .currentQuestionAlreadyAnswered)
        }
    }

    func testPastAttemptIDCannotBeReusedForNextQuestion() throws {
        let lesson = makeLesson(count: 2)
        let session = try XCTUnwrap(CourseEngine.makeSession(
            lesson: lesson, progress: [:], minutes: 3, reviewOnly: false, now: now
        ))
        let attemptID = UUID()
        var snapshot = try CourseEngine.submit(
            snapshot: CourseSnapshot(lesson: lesson, sessions: [session]),
            lesson: lesson,
            sessionID: session.id,
            attemptID: attemptID,
            optionID: "q-1-correct",
            now: now
        )
        snapshot = try CourseEngine.advance(
            snapshot: snapshot,
            sessionID: session.id,
            now: now
        )

        XCTAssertThrowsError(try CourseEngine.submit(
            snapshot: snapshot,
            lesson: lesson,
            sessionID: session.id,
            attemptID: attemptID,
            optionID: "q-2-correct",
            now: now
        )) { error in
            XCTAssertEqual(error as? CourseEngineError, .conflictingAttemptID)
        }
    }

    func testCannotAdvanceBeforeCurrentQuestionIsAnswered() throws {
        let lesson = makeLesson(count: 1)
        let session = try XCTUnwrap(CourseEngine.makeSession(
            lesson: lesson, progress: [:], minutes: 3, reviewOnly: false, now: now
        ))

        XCTAssertThrowsError(try CourseEngine.advance(
            snapshot: CourseSnapshot(lesson: lesson, sessions: [session]),
            sessionID: session.id,
            now: now
        ))
    }

    func testCompletedAndSubmittedActiveSessionsRoundTripWithExplanationLookup() throws {
        let lesson = makeLesson(count: 2)
        let completedID = UUID()
        let completedAttempt = CourseAttempt(
            id: UUID(), sessionID: completedID, questionID: "q-1",
            selectedOptionID: "q-1-correct", isCorrect: true, answeredAt: now, isReview: false
        )
        let completed = CourseSession(
            id: completedID, questionIDs: ["q-1"], currentIndex: 1,
            startedAt: now, completedAt: now, attempts: [completedAttempt]
        )
        let activeID = UUID()
        let activeAttempt = CourseAttempt(
            id: UUID(), sessionID: activeID, questionID: "q-2",
            selectedOptionID: "q-2-wrong-a", isCorrect: false, answeredAt: now, isReview: false
        )
        let active = CourseSession(
            id: activeID, questionIDs: ["q-2"], currentIndex: 0,
            startedAt: now, attempts: [activeAttempt]
        )
        let snapshot = CourseSnapshot(
            lesson: lesson,
            progress: [
                "q-1": StudyItemProgress(itemID: "q-1", attemptCount: 1, correctCount: 1),
                "q-2": StudyItemProgress(itemID: "q-2", attemptCount: 1, incorrectCount: 1)
            ],
            attempts: [completedAttempt, activeAttempt],
            sessions: [completed, active]
        )

        let restored = try JSONDecoder().decode(
            CourseSnapshot.self,
            from: JSONEncoder().encode(snapshot)
        )

        XCTAssertEqual(restored, snapshot)
        XCTAssertEqual(restored.sessions.first?.correctCount, 1)
        XCTAssertEqual(restored.activeSession?.currentAttempt, activeAttempt)
        let question = try XCTUnwrap(lesson.question(id: restored.activeSession?.currentQuestionID ?? ""))
        XCTAssertEqual(question.options.first(where: { $0.id == activeAttempt.selectedOptionID })?.explanation, "誤答Aの説明")
    }
}

func makeLesson(count: Int = 20) -> CourseLesson {
    CourseLesson(
        schemaVersion: 1,
        id: "hsk3-first-lesson",
        contentVersion: "2026-09-15-draft1",
        title: "時間・場所の語順",
        subtitle: "テスト用",
        reviewStatus: "draft",
        examProfile: CourseExamProfile(
            id: "hsk3-prototype-unconfirmed",
            targetLevel: 3,
            syllabusStatus: "unconfirmed",
            note: "試験形式との対応は確認中"
        ),
        questions: (1...count).map { index in
            let id = "q-\(index)"
            return CourseQuestion(
                id: id,
                topic: index.isMultiple(of: 2) ? "place" : "time",
                prompt: "問題\(index)",
                options: [
                    CourseOption(id: "\(id)-correct", text: "正答", explanation: "正答の説明"),
                    CourseOption(id: "\(id)-wrong-a", text: "誤答A", explanation: "誤答Aの説明"),
                    CourseOption(id: "\(id)-wrong-b", text: "誤答B", explanation: "誤答Bの説明")
                ],
                correctOptionID: "\(id)-correct",
                explanation: "語順の説明",
                example: CourseExample(hanzi: "我今天学习。", pinyin: "Wǒ jīntiān xuéxí.", japanese: "私は今日勉強します。")
            )
        }
    )
}
