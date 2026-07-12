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
        let valuePicker = app.buttons["study.focus.value"]
        XCTAssertTrue(valuePicker.exists)
        XCTAssertTrue(valuePicker.label.contains("フランス（"))
        let availableCount = app.descendants(matching: .any)["study.focus.availableCount"]
        XCTAssertTrue(availableCount.exists)
        XCTAssertTrue(app.descendants(matching: .any)["study.focus.plannedCount"].exists)
        XCTAssertTrue(startButton.isEnabled)

        valuePicker.tap()
        let bordeaux = app.buttons.matching(
            NSPredicate(format: "label CONTAINS %@", "ボルドー（")
        ).firstMatch
        let burgundy = app.buttons.matching(
            NSPredicate(format: "label CONTAINS %@", "ブルゴーニュ（")
        ).firstMatch
        XCTAssertTrue(bordeaux.waitForExistence(timeout: 5))
        XCTAssertTrue(burgundy.exists)
        app.buttons.matching(
            NSPredicate(format: "label BEGINSWITH %@", "フランス（")
        ).firstMatch.tap()

        dimensionPicker.tap()
        let grapeVariety = app.buttons["主要品種"]
        XCTAssertTrue(grapeVariety.waitForExistence(timeout: 5))
        grapeVariety.tap()

        let cabernetSelected = NSPredicate(
            format: "label CONTAINS %@", "カベルネ・ソーヴィニヨン（"
        )
        expectation(for: cabernetSelected, evaluatedWith: valuePicker)
        waitForExpectations(timeout: 5)

        valuePicker.tap()
        XCTAssertTrue(app.staticTexts["国際品種"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["準国際品種"].exists)
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

    func testGlossaryAndClassificationReferencesAreReachable() {
        let app = XCUIApplication()
        app.launch()

        XCTAssertTrue(app.tabBars.buttons["問題集"].waitForExistence(timeout: 20))
        app.tabBars.buttons["問題集"].tap()

        let glossaryLink = app.descendants(matching: .any)["reference.glossary.link"]
        XCTAssertTrue(glossaryLink.waitForExistence(timeout: 5))
        glossaryLink.tap()
        XCTAssertTrue(app.navigationBars["用語辞書"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts.matching(
            NSPredicate(format: "label CONTAINS %@", "用語（680件）")
        ).firstMatch.exists)

        app.navigationBars["用語辞書"].buttons.firstMatch.tap()
        let classificationLink = app.descendants(matching: .any)["reference.classification.link"]
        XCTAssertTrue(classificationLink.waitForExistence(timeout: 5))
        classificationLink.tap()
        XCTAssertTrue(app.navigationBars["格付け一覧"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.buttons["ボルドー"].exists)
        XCTAssertTrue(app.buttons["ブルゴーニュ"].exists)
        XCTAssertTrue(app.buttons["シャンパーニュ"].exists)
    }
}
