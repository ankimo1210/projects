import XCTest

/// カテゴリ選択 → クイズ → 統計 の基本導線が動くことを確認するスモークテスト
final class SmokeUITests: XCTestCase {

    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    private func dismissNotificationPromptIfNeeded(_ app: XCUIApplication) {
        let springboard = XCUIApplication(bundleIdentifier: "com.apple.springboard")
        let allowButton = springboard.buttons["許可"]
        if allowButton.waitForExistence(timeout: 3) {
            allowButton.tap()
        }
    }

    @MainActor
    func testCategoryToQuizToStatsFlow() throws {
        let app = XCUIApplication()
        app.launch()
        dismissNotificationPromptIfNeeded(app)

        // カテゴリ選択画面
        let dailyRow = app.staticTexts["日常会話"]
        XCTAssertTrue(dailyRow.waitForExistence(timeout: 5), "カテゴリ一覧に「日常会話」が表示されること")
        XCTAssertTrue(app.staticTexts["TOEIC・ビジネス英語"].exists)
        XCTAssertTrue(app.staticTexts["大学受験・英検"].exists)
        dailyRow.tap()

        // クイズ画面: 問題番号・発音ボタン・4択が表示される
        let speakButton = app.buttons["発音を聞く"]
        XCTAssertTrue(speakButton.waitForExistence(timeout: 5), "クイズ画面に「発音を聞く」ボタンが出ること")
        XCTAssertTrue(app.staticTexts["1 / 10"].exists, "問題番号 1 / 10 が表示されること")

        let knownLabels = ["発音を聞く", "次へ", "学習", "統計", "カテゴリを選択", "Back"]
        let choicePredicate = NSPredicate(format: "NOT (label IN %@)", knownLabels)
        var sawWrongAnswer = false

        // 10問すべて回答し、結果画面まで進める
        for _ in 0..<10 {
            let choice = app.buttons.matching(choicePredicate).firstMatch
            XCTAssertTrue(choice.waitForExistence(timeout: 3), "4択の選択肢が表示されること")
            choice.tap()

            let correctBanner = app.staticTexts["正解！"]
            let wrongBanner = app.staticTexts["おしい！"]
            let bannerShown = correctBanner.waitForExistence(timeout: 3) || wrongBanner.exists
            XCTAssertTrue(bannerShown, "回答後に正誤フィードバックバナーが出ること")
            XCTAssertTrue(app.staticTexts["例文"].exists, "回答後に例文カードが表示されること")

            if wrongBanner.exists {
                sawWrongAnswer = true
                let nextButton = app.buttons["次へ"]
                XCTAssertTrue(nextButton.waitForExistence(timeout: 3), "不正解時に「次へ」ボタンが出ること")
                nextButton.tap()
            } else {
                // 正解時は自動遷移を待つ
                sleep(2)
            }
        }

        // 結果画面
        XCTAssertTrue(app.staticTexts["お疲れさまでした！"].waitForExistence(timeout: 5), "結果画面が表示されること")
        if sawWrongAnswer {
            let retryMissedPredicate = NSPredicate(format: "label BEGINSWITH '間違えた単語だけ'")
            XCTAssertTrue(app.buttons.matching(retryMissedPredicate).firstMatch.exists, "間違いがあった場合は「間違えた単語だけもう一度」ボタンが出ること")
        }

        // 統計タブへ切り替え
        app.tabBars.buttons["統計"].tap()
        XCTAssertTrue(app.navigationBars["学習統計"].waitForExistence(timeout: 5), "統計画面が表示されること")
        XCTAssertTrue(app.staticTexts["学習済み単語数"].exists)
        XCTAssertTrue(app.staticTexts["正答率"].exists)
    }

    @MainActor
    func testSettingsToggle() throws {
        let app = XCUIApplication()
        app.launch()
        dismissNotificationPromptIfNeeded(app)

        XCTAssertTrue(app.staticTexts["日常会話"].waitForExistence(timeout: 5))

        app.buttons["settingsButton"].tap()
        let toggle = app.switches["autoPronounceToggle"]
        XCTAssertTrue(toggle.waitForExistence(timeout: 5), "設定シートに自動発音トグルが表示されること")

        let initialValue = toggle.value as? String
        // Toggle の accessibilityIdentifier は行全体のラッパーに付くため、
        // 実際にヒットテスト可能なスイッチ本体（子要素）をタップする
        toggle.switches.firstMatch.tap()
        let toggledValue = app.switches["autoPronounceToggle"].value as? String
        XCTAssertNotEqual(initialValue, toggledValue, "トグルをタップすると値が切り替わること")

        app.buttons["閉じる"].tap()
        XCTAssertTrue(app.staticTexts["日常会話"].waitForExistence(timeout: 5), "設定を閉じるとカテゴリ選択画面に戻ること")
    }

    @MainActor
    func testWordBrowseViaSwipe() throws {
        let app = XCUIApplication()
        app.launch()
        dismissNotificationPromptIfNeeded(app)

        let dailyRow = app.staticTexts["日常会話"]
        XCTAssertTrue(dailyRow.waitForExistence(timeout: 5))
        dailyRow.swipeLeft()

        let browseButton = app.buttons["単語一覧"]
        XCTAssertTrue(browseButton.waitForExistence(timeout: 3), "スワイプで単語一覧ボタンが出ること")
        browseButton.tap()

        XCTAssertTrue(app.navigationBars["日常会話 一覧"].waitForExistence(timeout: 5), "単語一覧画面が開くこと")
        XCTAssertTrue(app.staticTexts["appointment"].waitForExistence(timeout: 3), "一覧に単語が表示されること")
    }
}
