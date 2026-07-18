import XCTest

final class R6UITests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testTheoryExamShowsPaywallForFreeUser() {
        let app = XCUIApplication()
        app.launchArguments.append(contentsOf: [
            "-UITestFreeEntitlement", "-UITestInMemoryStore",
        ])
        app.launch()

        XCTAssertTrue(app.tabBars.buttons["学習"].waitForExistence(timeout: 20))
        app.tabBars.buttons["学習"].tap()
        let link = app.descendants(matching: .any)["study.theoryExam.open"]
        for _ in 0..<8 where !link.exists { app.swipeUp() }
        XCTAssertTrue(link.exists)
        link.tap()

        XCTAssertTrue(app.navigationBars["Proを解放"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.buttons["paywall.restore"].exists)
        XCTAssertTrue(app.staticTexts.matching(
            NSPredicate(format: "label CONTAINS %@", "理論模擬試験")
        ).firstMatch.exists)
    }

    func testTheoryExamDashboardOpensForProUser() {
        let app = XCUIApplication()
        app.launchArguments.append("-UITestProEntitlement")
        app.launch()

        XCTAssertTrue(app.tabBars.buttons["学習"].waitForExistence(timeout: 20))
        app.tabBars.buttons["学習"].tap()
        let link = app.descendants(matching: .any)["study.theoryExam.open"]
        for _ in 0..<8 where !link.exists { app.swipeUp() }
        XCTAssertTrue(link.exists)
        link.tap()

        XCTAssertTrue(app.navigationBars["理論模擬試験"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.descendants(matching: .any)["theoryExam.start"].exists)
    }

    func testPendingPurchaseShowsNonEntitledState() {
        let app = launchPaywall(arguments: [
            "-UITestFreeEntitlement",
            "-UITestStorePurchasePending",
        ])
        let purchase = app.buttons["paywall.purchase"]
        XCTAssertTrue(purchase.waitForExistence(timeout: 5))
        XCTAssertTrue(purchase.isEnabled)

        purchase.tap()

        XCTAssertTrue(app.staticTexts["購入は承認待ちです。承認後に自動で反映されます。"]
            .waitForExistence(timeout: 5))
        XCTAssertFalse(app.staticTexts["購入済み"].exists)
    }

    func testCancelledPurchaseKeepsFreeAccessAndExplainsOutcome() {
        let app = launchPaywall(arguments: [
            "-UITestFreeEntitlement",
            "-UITestStorePurchaseCancelled",
        ])
        let purchase = app.buttons["paywall.purchase"]
        XCTAssertTrue(purchase.waitForExistence(timeout: 5))

        purchase.tap()

        XCTAssertTrue(app.staticTexts["購入はキャンセルされました。"]
            .waitForExistence(timeout: 5))
        XCTAssertTrue(app.navigationBars["Proを解放"].exists)
        XCTAssertFalse(app.staticTexts["購入済み"].exists)
    }

    func testVerifiedPurchaseUnlocksProFromPaywall() {
        let app = launchPaywall(arguments: [
            "-UITestFreeEntitlement",
            "-UITestStorePurchaseSuccess",
        ])
        let purchase = app.buttons["paywall.purchase"]
        XCTAssertTrue(purchase.waitForExistence(timeout: 5))

        purchase.tap()

        XCTAssertTrue(app.navigationBars["今日の学習"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.descendants(matching: .any)["study.daily.sessionSize"].exists)
    }

    func testPurchaseRestoreUnlocksProFromPaywall() {
        let app = launchPaywall(arguments: [
            "-UITestFreeEntitlement",
            "-UITestStoreRestoreSuccess",
        ])
        let restore = app.buttons["paywall.restore"]
        XCTAssertTrue(restore.waitForExistence(timeout: 5))

        restore.tap()

        XCTAssertTrue(app.navigationBars["今日の学習"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.descendants(matching: .any)["study.daily.sessionSize"].exists)
    }

    func testFreeUserCanStartOneWrittenQuestionAndGetsTwentyQuestionMiniMock() {
        let app = XCUIApplication()
        app.launchArguments.append("-UITestFreeEntitlement")
        app.launch()

        XCTAssertTrue(app.tabBars.buttons["学習"].waitForExistence(timeout: 20))
        app.tabBars.buttons["学習"].tap()

        let writtenStart = app.buttons["study.written.startButton"]
        for _ in 0..<5 where !writtenStart.exists { app.swipeUp() }
        XCTAssertTrue(writtenStart.exists)
        XCTAssertEqual(writtenStart.label, "記述式1問を練習")
        XCTAssertTrue(writtenStart.isEnabled)
        writtenStart.tap()

        XCTAssertTrue(app.navigationBars["1 / 1 問"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["あなたの解答"].exists)
        app.navigationBars["1 / 1 問"].buttons.firstMatch.tap()

        let miniMockStart = app.buttons["study.miniMock.startButton"]
        for _ in 0..<10 where !miniMockStart.exists { app.swipeUp() }
        XCTAssertTrue(miniMockStart.exists)
        XCTAssertEqual(miniMockStart.label, "20問ミニ模試を開始")
        XCTAssertTrue(miniMockStart.isEnabled)
        miniMockStart.tap()
        XCTAssertTrue(app.staticTexts["問題 1 / 20"].waitForExistence(timeout: 5))
    }

    func testProUserGetsAvailableWrittenQuestionsAndFiftyQuestionMiniMock() {
        let app = XCUIApplication()
        app.launchArguments.append("-UITestProEntitlement")
        app.launch()

        XCTAssertTrue(app.tabBars.buttons["学習"].waitForExistence(timeout: 20))
        app.tabBars.buttons["学習"].tap()

        let writtenStart = app.buttons["study.written.startButton"]
        for _ in 0..<5 where !writtenStart.exists { app.swipeUp() }
        XCTAssertTrue(writtenStart.exists)
        XCTAssertEqual(writtenStart.label, "記述式10問を練習")
        XCTAssertTrue(writtenStart.isEnabled)

        let miniMockStart = app.buttons["study.miniMock.startButton"]
        for _ in 0..<10 where !miniMockStart.exists { app.swipeUp() }
        XCTAssertTrue(miniMockStart.exists)
        XCTAssertEqual(miniMockStart.label, "50問ミニ模試を開始")
        XCTAssertTrue(miniMockStart.isEnabled)
        miniMockStart.tap()
        XCTAssertTrue(app.staticTexts["問題 1 / 50"].waitForExistence(timeout: 5))
    }

    func testFreeSearchDoesNotRevealPaidQuestionOrGlossaryContent() {
        let app = XCUIApplication()
        app.launchArguments.append("-UITestFreeEntitlement")
        app.launch()

        XCTAssertTrue(app.tabBars.buttons["問題集"].waitForExistence(timeout: 20))
        app.tabBars.buttons["問題集"].tap()

        let questionSearch = app.searchFields.firstMatch
        XCTAssertTrue(questionSearch.waitForExistence(timeout: 5))
        questionSearch.tap()
        questionSearch.typeText("特定のブドウ品種から一つのクローンを選んで植える")
        XCTAssertTrue(app.staticTexts["0問"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.staticTexts.matching(
            NSPredicate(format: "label CONTAINS %@", "一つのクローンを選んで植える主な利点")
        ).firstMatch.exists)

        app.terminate()

        let glossaryApp = XCUIApplication()
        glossaryApp.launchArguments.append("-UITestFreeEntitlement")
        glossaryApp.launch()
        XCTAssertTrue(glossaryApp.tabBars.buttons["問題集"].waitForExistence(timeout: 20))
        glossaryApp.tabBars.buttons["問題集"].tap()

        let glossaryLink = glossaryApp.descendants(matching: .any)["reference.glossary.link"]
        XCTAssertTrue(glossaryLink.exists)
        glossaryLink.tap()

        let glossarySearch = glossaryApp.searchFields.firstMatch
        for _ in 0..<2 where !glossarySearch.exists { glossaryApp.swipeDown() }
        XCTAssertTrue(glossarySearch.waitForExistence(timeout: 5))
        glossarySearch.tap()
        glossarySearch.typeText("アイレン")
        XCTAssertFalse(glossaryApp.staticTexts["アイレン"].waitForExistence(timeout: 2))
    }

    private func launchPaywall(arguments: [String]) -> XCUIApplication {
        let app = XCUIApplication()
        app.launchArguments.append(contentsOf: arguments)
        app.launch()

        XCTAssertTrue(app.tabBars.buttons["学習"].waitForExistence(timeout: 20))
        app.tabBars.buttons["学習"].tap()
        let link = app.descendants(matching: .any)["study.daily.open"]
        for _ in 0..<8 where !link.exists { app.swipeUp() }
        XCTAssertTrue(link.exists)
        link.tap()
        XCTAssertTrue(app.navigationBars["Proを解放"].waitForExistence(timeout: 5))
        return app
    }
}
