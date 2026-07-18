import XCTest

final class R1WrittenPracticeUITests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testWrittenDraftResumesAndCompletedAnswerAppearsInHistory() {
        let app = XCUIApplication()
        app.launchArguments = [
            "-UITestFreeEntitlement",
            "-UITestResetStudyHistory",
        ]
        app.launch()

        openFreeWrittenPractice(in: app)
        XCTAssertTrue(
            app.descendants(matching: .any)["written.answer.commandVerb"].exists
        )
        XCTAssertTrue(
            app.descendants(matching: .any)["written.answer.maximumMarks"].exists
        )
        XCTAssertTrue(
            app.descendants(matching: .any)["written.answer.elapsedTime"].exists
        )
        let editor = app.textViews["written.answer.editor"]
        XCTAssertTrue(editor.waitForExistence(timeout: 5))
        editor.tap()
        editor.typeText("冷気が低地に滞留するため、萌芽後の芽を損傷する。")
        app.navigationBars["1 / 1 問"].buttons.firstMatch.tap()

        app.terminate()
        app.launchArguments = ["-UITestFreeEntitlement"]
        app.launch()
        XCTAssertTrue(app.tabBars.buttons["学習"].waitForExistence(timeout: 20))
        app.tabBars.buttons["学習"].tap()

        let resume = app.buttons["study.written.resumeDrafts"]
        for _ in 0..<6 where !resume.exists { app.swipeUp() }
        XCTAssertTrue(resume.exists)
        resume.tap()

        let restoredEditor = app.textViews["written.answer.editor"]
        XCTAssertTrue(restoredEditor.waitForExistence(timeout: 5))
        XCTAssertTrue(
            (restoredEditor.value as? String)?.contains("冷気が低地に滞留") == true
        )

        app.buttons["模範解答と比較"].tap()
        let firstRubric = app.buttons["written.rubric.SAQ-LO1-001-R1"]
        for _ in 0..<8 where !firstRubric.exists { app.swipeUp() }
        XCTAssertTrue(firstRubric.exists)
        firstRubric.tap()
        XCTAssertTrue(
            app.descendants(matching: .any)["written.rubric.reviewLinks"].exists
        )

        let record = app.buttons["自己採点を記録して次へ"]
        for _ in 0..<8 where !record.isHittable { app.swipeUp() }
        XCTAssertTrue(record.isHittable)
        record.tap()
        XCTAssertTrue(app.navigationBars["完了"].waitForExistence(timeout: 5))
        app.navigationBars["完了"].buttons.firstMatch.tap()

        let history = app.descendants(matching: .any)["study.written.history"]
        for _ in 0..<6 where !history.exists { app.swipeUp() }
        XCTAssertTrue(history.exists)
        history.tap()
        XCTAssertTrue(app.navigationBars["記述式の過去回答"].waitForExistence(timeout: 5))

        let questionHistory = app.descendants(matching: .any)[
            "written.history.question.SAQ-LO1-001"
        ]
        XCTAssertTrue(questionHistory.waitForExistence(timeout: 5))
        questionHistory.tap()
        XCTAssertTrue(
            app.descendants(matching: .any)["written.history.scoreTrend"]
                .waitForExistence(timeout: 5)
        )
    }

    private func openFreeWrittenPractice(in app: XCUIApplication) {
        XCTAssertTrue(app.tabBars.buttons["学習"].waitForExistence(timeout: 20))
        app.tabBars.buttons["学習"].tap()
        let start = app.buttons["study.written.startButton"]
        for _ in 0..<6 where !start.exists { app.swipeUp() }
        XCTAssertTrue(start.exists)
        start.tap()
        XCTAssertTrue(app.navigationBars["1 / 1 問"].waitForExistence(timeout: 5))
    }
}
