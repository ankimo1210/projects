import XCTest

final class RegionMapUITests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testFranceMapRegionDetailAndComparisonAreReachable() {
        let app = XCUIApplication()
        app.launchArguments.append("-UITestProEntitlement")
        app.launch()

        XCTAssertTrue(app.tabBars.buttons["問題集"].waitForExistence(timeout: 20))
        app.tabBars.buttons["問題集"].tap()

        let hubLink = app.descendants(matching: .any)["regionMap.hub.link"]
        XCTAssertTrue(hubLink.waitForExistence(timeout: 5))
        hubLink.tap()
        XCTAssertTrue(app.navigationBars["産地マップ"].waitForExistence(timeout: 5))

        let france = app.descendants(matching: .any)["regionMap.country.france"]
        XCTAssertTrue(france.waitForExistence(timeout: 5))
        france.tap()
        XCTAssertTrue(app.navigationBars["フランス"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["産地一覧"].exists)

        let bordeaux = app.descendants(matching: .any)["regionMap.list.france_bordeaux"]
        XCTAssertTrue(bordeaux.waitForExistence(timeout: 5))
        bordeaux.tap()
        XCTAssertTrue(app.navigationBars["産地詳細"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["ボルドー"].exists)
        XCTAssertTrue(app.descendants(matching: .any)["regionMap.study.10"].isEnabled)

        app.navigationBars["産地詳細"].buttons.firstMatch.tap()
        app.navigationBars["フランス"].buttons.firstMatch.tap()
        let comparison = app.descendants(matching: .any)["regionMap.comparison.link"]
        XCTAssertTrue(comparison.waitForExistence(timeout: 5))
        comparison.tap()
        XCTAssertTrue(app.navigationBars["産地比較"].waitForExistence(timeout: 5))
        XCTAssertTrue(
            app.descendants(matching: .any)[
                "regionMap.comparison.axis.climateInfluence"
            ].waitForExistence(timeout: 5)
        )
        let comparisonStudy = app.descendants(matching: .any)["regionMap.comparison.study"]
        let writtenQuestion = app.descendants(matching: .any)[
            "regionMap.comparison.written.link"
        ]
        for _ in 0..<20 where !writtenQuestion.exists { app.swipeUp() }
        XCTAssertTrue(writtenQuestion.waitForExistence(timeout: 5))
        for _ in 0..<10 where !comparisonStudy.exists { app.swipeUp() }
        XCTAssertTrue(comparisonStudy.waitForExistence(timeout: 5))
        XCTAssertTrue(comparisonStudy.isEnabled)
    }

    func testMapMarkerOpensDetailAndStartsRegionalSession() {
        let app = XCUIApplication()
        app.launchArguments += ["-UITestProEntitlement", "-UITestInMemoryStore"]
        app.launch()

        XCTAssertTrue(app.tabBars.buttons["問題集"].waitForExistence(timeout: 20))
        app.tabBars.buttons["問題集"].tap()
        app.descendants(matching: .any)["regionMap.hub.link"].tap()
        app.descendants(matching: .any)["regionMap.country.france"].tap()

        let regionIDs = [
            "france_bordeaux",
            "france_burgundy",
            "france_champagne",
            "france_loire",
            "france_alsace",
            "france_northern_rhone",
            "france_southern_rhone",
            "france_provence",
            "france_beaujolais",
            "france_languedoc_roussillon",
        ]
        for regionID in regionIDs {
            XCTAssertTrue(app.buttons["regionMap.marker.\(regionID)"].exists)
            XCTAssertTrue(app.buttons["regionMap.list.\(regionID)"].exists)
        }

        let marker = app.descendants(matching: .any)["regionMap.marker.france_bordeaux"]
        XCTAssertTrue(marker.waitForExistence(timeout: 5))
        marker.tap()
        XCTAssertTrue(app.navigationBars["産地詳細"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["ボルドー"].exists)

        let study = app.descendants(matching: .any)["regionMap.study.10"]
        XCTAssertTrue(study.waitForExistence(timeout: 5))
        XCTAssertTrue(study.isEnabled)
        study.tap()
        XCTAssertTrue(app.navigationBars["1 / 10 問"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.buttons["study.session.choice.0"].waitForExistence(timeout: 5))
    }

    func testMapLoadFailureFixtureShowsJapaneseErrorInsteadOfCrashing() {
        let app = XCUIApplication()
        app.launchArguments += ["-UITestInMemoryStore", "-UITestRegionMapLoadFailure"]
        app.launch()

        XCTAssertTrue(app.tabBars.buttons["問題集"].waitForExistence(timeout: 20))
        app.tabBars.buttons["問題集"].tap()
        app.descendants(matching: .any)["regionMap.hub.link"].tap()

        let error = app.descendants(matching: .any)["regionMap.loadError"]
        XCTAssertTrue(error.waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["産地マップを利用できません"].exists)
        XCTAssertTrue(app.staticTexts["産地マップデータを読み込めませんでした。"].exists)
    }

    func testMapLabelsRemainJapaneseWhenDeviceLanguageIsEnglish() {
        let app = XCUIApplication()
        app.launchArguments += ["-AppleLanguages", "(en)", "-AppleLocale", "en_US"]
        app.launch()

        XCTAssertTrue(app.tabBars.buttons["問題集"].waitForExistence(timeout: 20))
        app.tabBars.buttons["問題集"].tap()
        app.descendants(matching: .any)["regionMap.hub.link"].tap()

        XCTAssertTrue(app.navigationBars["産地マップ"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["国別マップ"].exists)
        XCTAssertFalse(app.navigationBars["Region Maps"].exists)
    }
}
