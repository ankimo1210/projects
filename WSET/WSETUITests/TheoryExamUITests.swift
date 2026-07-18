import XCTest

final class TheoryExamUITests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testManualSubmissionShowsReasonAndLearningOutcomeResults() {
        let app = XCUIApplication()
        app.launchArguments += ["-UITestProEntitlement", "-UITestInMemoryStore"]
        app.launch()

        XCTAssertTrue(app.tabBars.buttons["学習"].waitForExistence(timeout: 20))
        app.tabBars.buttons["学習"].tap()
        let entry = app.descendants(matching: .any)["study.theoryExam.open"]
        for _ in 0..<8 where !entry.exists { app.swipeUp() }
        XCTAssertTrue(entry.exists)
        entry.tap()

        let start = app.descendants(matching: .any)["theoryExam.start"]
        XCTAssertTrue(start.waitForExistence(timeout: 10))
        start.tap()

        XCTAssertTrue(app.navigationBars["理論模擬試験"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.descendants(matching: .any)["theoryExam.timer"].exists)

        app.descendants(matching: .any)["theoryExam.navigator"].tap()
        let secondQuestion = app.buttons["theoryExam.navigator.question.2"]
        XCTAssertTrue(secondQuestion.waitForExistence(timeout: 3))
        secondQuestion.tap()
        XCTAssertTrue(app.staticTexts["第2問 / 54問"].waitForExistence(timeout: 3))

        app.navigationBars["理論模擬試験"].buttons["提出"].tap()
        XCTAssertTrue(app.alerts["試験を提出しますか？"].waitForExistence(timeout: 3))
        app.alerts["試験を提出しますか？"].buttons["提出"].tap()

        let reason = app.descendants(matching: .any)[
            "theoryExam.selfAssessment.submissionReason"
        ]
        XCTAssertTrue(reason.waitForExistence(timeout: 5))
        XCTAssertTrue(reason.label.contains("手動"))

        let finalize = app.buttons["theoryExam.finalize"]
        for _ in 0..<20 where !finalize.isHittable { app.swipeUp() }
        XCTAssertTrue(finalize.isHittable)
        finalize.tap()

        XCTAssertTrue(app.navigationBars["試験結果"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.descendants(matching: .any)[
            "theoryExam.result.submissionReason"
        ].label.contains("手動提出"))
        XCTAssertTrue(app.descendants(matching: .any)[
            "theoryExam.result.learningOutcome.u1_lo1"
        ].exists)
    }
}
