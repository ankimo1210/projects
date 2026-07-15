import Foundation
import XCTest
@testable import My_Tianjin

final class ReviewSchedulerTests: XCTestCase {
    func testCorrectAnswersAdvanceIntervalsAndDueDate() {
        let now = Date(timeIntervalSince1970: 1_700_000_000)
        let scheduler = ReviewScheduler(
            configuration: ReviewSchedulerConfiguration(
                correctIntervals: [100, 300],
                incorrectRetryInterval: 10
            )
        )

        let first = scheduler.updatedProgress(
            itemID: "word-1",
            result: .correct,
            reviewedAt: now
        )
        let second = scheduler.updatedProgress(
            itemID: "word-1",
            previous: first,
            result: .correct,
            reviewedAt: now.addingTimeInterval(100)
        )

        XCTAssertEqual(first.attemptCount, 1)
        XCTAssertEqual(first.correctCount, 1)
        XCTAssertEqual(first.reviewStage, 1)
        XCTAssertEqual(first.nextReviewAt, now.addingTimeInterval(100))
        XCTAssertFalse(first.isDue(at: now.addingTimeInterval(99)))
        XCTAssertTrue(first.isDue(at: now.addingTimeInterval(100)))

        XCTAssertEqual(second.currentStreak, 2)
        XCTAssertEqual(second.reviewStage, 2)
        XCTAssertEqual(second.nextReviewAt, now.addingTimeInterval(400))
    }

    func testIncorrectAnswerResetsStageAndSchedulesQuickRetry() {
        let now = Date(timeIntervalSince1970: 1_700_000_000)
        let scheduler = ReviewScheduler(
            configuration: ReviewSchedulerConfiguration(
                correctIntervals: [100, 300],
                incorrectRetryInterval: 10
            )
        )
        let previous = StudyItemProgress(
            itemID: "word-1",
            attemptCount: 3,
            correctCount: 3,
            currentStreak: 3,
            reviewStage: 2
        )

        let updated = scheduler.updatedProgress(
            itemID: "word-1",
            previous: previous,
            result: .incorrect,
            reviewedAt: now
        )

        XCTAssertEqual(updated.attemptCount, 4)
        XCTAssertEqual(updated.incorrectCount, 1)
        XCTAssertEqual(updated.currentStreak, 0)
        XCTAssertEqual(updated.reviewStage, 0)
        XCTAssertEqual(updated.nextReviewAt, now.addingTimeInterval(10))
    }
}
