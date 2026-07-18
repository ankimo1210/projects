import XCTest

final class R3UITests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testCompletedDailyStudyUpdatesWeaknessAttemptCounts() {
        let app = XCUIApplication()
        app.launchArguments.append(contentsOf: [
            "-UITestProEntitlement",
            "-UITestInMemoryStore",
            "-UITestResetStudyHistory",
        ])
        app.launch()

        XCTAssertTrue(app.tabBars.buttons["学習"].waitForExistence(timeout: 20))
        app.tabBars.buttons["学習"].tap()

        let dailyEntry = app.descendants(matching: .any)["study.daily.open"]
        for _ in 0..<8 where !dailyEntry.exists { app.swipeUp() }
        XCTAssertTrue(dailyEntry.exists)
        dailyEntry.tap()

        let sizePicker = app.segmentedControls["study.daily.sessionSize"]
        XCTAssertTrue(sizePicker.waitForExistence(timeout: 5))
        sizePicker.buttons["10問"].tap()

        let start = app.buttons["study.daily.startButton"]
        for _ in 0..<8 where !start.exists { app.swipeUp() }
        XCTAssertTrue(start.waitForExistence(timeout: 5))
        start.tap()

        for _ in 0..<10 {
            let choice = app.buttons["study.session.choice.0"]
            XCTAssertTrue(choice.waitForExistence(timeout: 5))
            choice.tap()

            let record = app.buttons["理解できた"]
            XCTAssertTrue(record.waitForExistence(timeout: 5))
            record.tap()
        }

        XCTAssertTrue(app.staticTexts["学習完了"].waitForExistence(timeout: 5))
        app.navigationBars["完了"].buttons.firstMatch.tap()
        app.navigationBars["今日の学習"].buttons.firstMatch.tap()

        let weaknessEntry = app.descendants(matching: .any)["study.weakness.open"]
        for _ in 0..<8 where !weaknessEntry.exists { app.swipeUp() }
        XCTAssertTrue(weaknessEntry.exists)
        weaknessEntry.tap()

        XCTAssertTrue(app.navigationBars["弱点分析"].waitForExistence(timeout: 5))
        XCTAssertTrue(
            app.staticTexts.matching(
                NSPredicate(format: "label MATCHES %@", "試行 [1-9][0-9]*回")
            ).firstMatch.waitForExistence(timeout: 5)
        )
    }
}
