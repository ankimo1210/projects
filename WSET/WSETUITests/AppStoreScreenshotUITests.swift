import XCTest

final class AppStoreScreenshotUITests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testCaptureProductScreens() {
        let app = XCUIApplication()
        app.launchArguments += [
            "-UITestProEntitlement",
            "-UITestInMemoryStore",
            "-UITestSeedTastingComparison",
        ]
        app.launch()

        XCTAssertTrue(app.navigationBars["CruNote"].waitForExistence(timeout: 20))
        capture("01-home")

        tab("学習", in: app).tap()
        XCTAssertTrue(app.navigationBars["学習"].waitForExistence(timeout: 10))
        capture("02-study")

        tab("問題集", in: app).tap()
        XCTAssertTrue(app.navigationBars["問題集"].waitForExistence(timeout: 10))
        app.descendants(matching: .any)["regionMap.hub.link"].tap()
        XCTAssertTrue(app.navigationBars["産地マップ"].waitForExistence(timeout: 10))
        app.descendants(matching: .any)["regionMap.country.france"].tap()
        XCTAssertTrue(app.navigationBars["フランス"].waitForExistence(timeout: 10))
        capture("03-region-map")

        tab("テイスティング", in: app).tap()
        XCTAssertTrue(app.navigationBars["テイスティング"].waitForExistence(timeout: 10))
        capture("04-tasting")

        app.descendants(matching: .any)["tasting.exam.entry"].tap()
        XCTAssertTrue(
            app.navigationBars["30分テイスティング試験"].waitForExistence(timeout: 10)
        )
        capture("05-tasting-exam")
    }

    func testCaptureInAppPurchaseReviewScreen() {
        let app = XCUIApplication()
        app.launchArguments += [
            "-UITestFreeEntitlement",
            "-UITestInMemoryStore",
            "-UITestStorePurchaseSuccess",
        ]
        app.launch()

        let progressTab = tab("進捗", in: app)
        XCTAssertTrue(progressTab.waitForExistence(timeout: 20))
        progressTab.tap()
        app.buttons["設定"].tap()
        XCTAssertTrue(app.navigationBars["設定"].waitForExistence(timeout: 10))
        app.buttons["Proの機能を見る"].tap()
        XCTAssertTrue(app.navigationBars["Proを解放"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.buttons["paywall.purchase"].waitForExistence(timeout: 10))
        XCTAssertEqual(app.buttons["paywall.purchase"].label, "¥1,500で買い切り")
        capture("iap-review-paywall")
    }

    private func capture(_ name: String) {
        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    private func tab(_ label: String, in app: XCUIApplication) -> XCUIElement {
        app.descendants(matching: .any).matching(
            NSPredicate(format: "label == %@", label)
        ).firstMatch
    }
}
