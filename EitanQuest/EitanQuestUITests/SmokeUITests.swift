import XCTest

/// カテゴリ選択 → クイズ → 統計 の基本導線が動くことを確認するスモークテスト
final class SmokeUITests: XCTestCase {

    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    @MainActor
    func testCategoryToQuizToStatsFlow() throws {
        let app = XCUIApplication()
        app.launch()

        // 初回起動時の通知許可ダイアログ（SpringBoard側）を閉じる
        let springboard = XCUIApplication(bundleIdentifier: "com.apple.springboard")
        let allowButton = springboard.buttons["許可"]
        if allowButton.waitForExistence(timeout: 3) {
            allowButton.tap()
        }

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

        // 選択肢（既知のボタン以外）を1つタップ
        let knownLabels = ["発音を聞く", "次へ", "学習", "統計", "カテゴリを選択", "Back"]
        let predicate = NSPredicate(format: "NOT (label IN %@)", knownLabels)
        let choice = app.buttons.matching(predicate).firstMatch
        XCTAssertTrue(choice.waitForExistence(timeout: 3), "4択の選択肢が表示されること")
        choice.tap()

        // 回答後: 正誤バナーと例文カードが出る
        let correctBanner = app.staticTexts["正解！"]
        let wrongBanner = app.staticTexts["おしい！"]
        let bannerShown = correctBanner.waitForExistence(timeout: 3) || wrongBanner.exists
        XCTAssertTrue(bannerShown, "回答後に正誤フィードバックバナーが出ること")
        XCTAssertTrue(app.staticTexts["例文"].exists, "回答後に例文カードが表示されること")

        // 正解時は自動遷移、不正解時は「次へ」で進む
        if wrongBanner.exists {
            let nextButton = app.buttons["次へ"]
            XCTAssertTrue(nextButton.waitForExistence(timeout: 3), "不正解時に「次へ」ボタンが出ること")
            nextButton.tap()
        }
        XCTAssertTrue(app.staticTexts["2 / 10"].waitForExistence(timeout: 5), "次の問題 2 / 10 に進むこと")

        // 統計タブへ切り替え
        app.tabBars.buttons["統計"].tap()
        XCTAssertTrue(app.navigationBars["学習統計"].waitForExistence(timeout: 5), "統計画面が表示されること")
        XCTAssertTrue(app.staticTexts["学習済み単語数"].exists)
        XCTAssertTrue(app.staticTexts["正答率"].exists)
    }
}
