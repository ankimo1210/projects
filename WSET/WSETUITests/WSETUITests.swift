import XCTest

final class WSETUITests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testMainTabsAndTastingEntryAreReachable() {
        let app = XCUIApplication()
        app.launch()

        XCTAssertTrue(app.tabBars.buttons["ホーム"].waitForExistence(timeout: 20))
        XCTAssertTrue(app.tabBars.buttons["学習"].exists)
        XCTAssertTrue(app.tabBars.buttons["問題集"].exists)
        XCTAssertTrue(app.tabBars.buttons["テイスティング"].exists)
        XCTAssertTrue(app.tabBars.buttons["進捗"].exists)

        app.tabBars.buttons["テイスティング"].tap()
        XCTAssertTrue(app.buttons["テイスティング記録を作成"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.buttons["2本比較ブラインド練習"].exists)

        app.buttons["2本比較ブラインド練習"].tap()
        XCTAssertTrue(app.buttons["ワイン1"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.buttons["ワイン2"].exists)
        XCTAssertFalse(app.buttons["Wine 1"].exists)
        XCTAssertFalse(app.buttons["Wine 2"].exists)
    }

    func testSettingsAreReachableFromProgress() {
        let app = XCUIApplication()
        app.launch()
        XCTAssertTrue(app.tabBars.buttons["進捗"].waitForExistence(timeout: 20))
        app.tabBars.buttons["進捗"].tap()
        app.buttons["設定"].tap()

        XCTAssertTrue(app.navigationBars["設定"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.staticTexts["アプリと問題の言語"].exists)
        XCTAssertTrue(app.buttons["バックアップを書き出す"].exists)
        XCTAssertTrue(app.buttons["バックアップから復元"].exists)
    }

    func testFocusedStudyControlsAreReachable() {
        let app = XCUIApplication()
        app.launch()

        XCTAssertTrue(app.tabBars.buttons["学習"].waitForExistence(timeout: 20))
        app.tabBars.buttons["学習"].tap()

        let startButton = app.buttons["study.focus.startButton"]
        for _ in 0..<5 where !startButton.exists {
            app.swipeUp()
        }
        XCTAssertTrue(app.staticTexts["重点学習"].exists)
        let dimensionPicker = app.buttons["study.focus.dimension"]
        XCTAssertTrue(dimensionPicker.exists)
        XCTAssertTrue(app.buttons["study.focus.value"].exists)
        let availableCount = app.descendants(matching: .any)["study.focus.availableCount"]
        XCTAssertTrue(availableCount.exists)
        XCTAssertTrue(app.descendants(matching: .any)["study.focus.plannedCount"].exists)
        XCTAssertTrue(startButton.isEnabled)

        dimensionPicker.tap()
        let wineType = app.buttons["ワイン区分"]
        XCTAssertTrue(wineType.waitForExistence(timeout: 5))
        wineType.tap()

        let wineTypeCount = NSPredicate(format: "label CONTAINS %@", "241問")
        expectation(for: wineTypeCount, evaluatedWith: availableCount)
        waitForExpectations(timeout: 5)
    }

    func testInterfaceRemainsJapaneseWhenDeviceLanguageIsEnglish() {
        let app = XCUIApplication()
        app.launchArguments += ["-AppleLanguages", "(en)", "-AppleLocale", "en_US"]
        app.launch()

        XCTAssertTrue(app.tabBars.buttons["ホーム"].waitForExistence(timeout: 20))
        XCTAssertTrue(app.tabBars.buttons["学習"].exists)
        XCTAssertTrue(app.tabBars.buttons["問題集"].exists)
        XCTAssertFalse(app.tabBars.buttons["Home"].exists)

        app.tabBars.buttons["学習"].tap()
        XCTAssertTrue(app.navigationBars["学習"].exists)
        XCTAssertFalse(app.staticTexts["アプリと問題の言語"].exists)
    }
}
