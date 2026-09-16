import XCTest

final class TastingExamLifecycleUITests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testDiscardedDraftStartsWithEmptyFieldsAndFullTimeIncludingAfterRelaunch() throws {
        let app = launchWithOldDraft()
        openExam(in: app)
        XCTAssertEqual(wineName(in: app).value as? String, "破棄前のワイン")
        XCTAssertLessThanOrEqual(try remainingSeconds(in: app), 1500)

        app.buttons["試験を破棄"].tap()
        let discard = app.buttons["下書きを破棄"]
        XCTAssertTrue(discard.waitForExistence(timeout: 5))
        discard.tap()
        XCTAssertTrue(app.navigationBars["テイスティング"].waitForExistence(timeout: 5))

        openExam(in: app)
        try assertFreshExam(in: app)

        // Discard once more, then verify the deleted draft cannot return at launch.
        app.buttons["試験を破棄"].tap()
        XCTAssertTrue(discard.waitForExistence(timeout: 5))
        discard.tap()
        XCTAssertTrue(app.navigationBars["テイスティング"].waitForExistence(timeout: 5))
        relaunchWithoutSeeding(app)
        openExam(in: app)
        try assertFreshExam(in: app)
    }

    func testOrdinaryBackAndRelaunchPreserveDraftAndOriginalDeadline() throws {
        let app = launchWithOldDraft()
        openExam(in: app)
        let initialRemaining = try remainingSeconds(in: app)
        XCTAssertEqual(wineName(in: app).value as? String, "破棄前のワイン")
        app.navigationBars["30分テイスティング試験"].buttons.firstMatch.tap()
        XCTAssertTrue(app.navigationBars["テイスティング"].waitForExistence(timeout: 5))

        openExam(in: app)
        XCTAssertEqual(wineName(in: app).value as? String, "破棄前のワイン")
        XCTAssertLessThanOrEqual(try remainingSeconds(in: app), initialRemaining)
        relaunchWithoutSeeding(app)
        openExam(in: app)
        XCTAssertEqual(wineName(in: app).value as? String, "破棄前のワイン")
        XCTAssertLessThanOrEqual(try remainingSeconds(in: app), initialRemaining)
        XCTAssertGreaterThan(try remainingSeconds(in: app), 0)
    }

    private func launchWithOldDraft() -> XCUIApplication {
        let app = XCUIApplication()
        app.launchArguments = [
            "-UITestProEntitlement", "-UITestInMemoryStore", "-UITestSeedTastingExamDraft",
        ]
        app.launch()
        openTastingTab(in: app)
        return app
    }

    private func relaunchWithoutSeeding(_ app: XCUIApplication) {
        app.terminate()
        app.launchArguments.removeAll { $0 == "-UITestSeedTastingExamDraft" }
        app.launch()
        openTastingTab(in: app)
    }

    private func openTastingTab(in app: XCUIApplication) {
        let tab = app.tabBars.buttons["テイスティング"]
        XCTAssertTrue(tab.waitForExistence(timeout: 20))
        tab.tap()
    }

    private func openExam(in app: XCUIApplication) {
        let entry = app.buttons["tasting.exam.entry"]
        XCTAssertTrue(entry.waitForExistence(timeout: 5))
        entry.tap()
        XCTAssertTrue(app.navigationBars["30分テイスティング試験"].waitForExistence(timeout: 5))
    }

    private func wineName(in app: XCUIApplication) -> XCUIElement {
        let field = app.textFields["ワイン名・正体（任意）"]
        XCTAssertTrue(field.waitForExistence(timeout: 5))
        return field
    }

    private func remainingSeconds(in app: XCUIApplication) throws -> Int {
        let timer = app.staticTexts["tasting.exam.timer"]
        XCTAssertTrue(timer.waitForExistence(timeout: 5))
        let components = timer.label.split(separator: ":")
        XCTAssertEqual(components.count, 2)
        guard components.count == 2 else { return -1 }
        return try XCTUnwrap(Int(components[0])) * 60 + XCTUnwrap(Int(components[1]))
    }

    private func assertFreshExam(in app: XCUIApplication) throws {
        XCTAssertGreaterThanOrEqual(try remainingSeconds(in: app), 1740)
        let value = wineName(in: app).value as? String
        XCTAssertTrue(value == "" || value == "ワイン名・正体（任意）")
    }
}
