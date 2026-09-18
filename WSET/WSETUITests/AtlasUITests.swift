import XCTest

final class AtlasUITests: XCTestCase {
    override func setUpWithError() throws { continueAfterFailure = false }

    func testExploreMapListAndPhotoCredits() {
        let app = launch()
        XCTAssertTrue(app.staticTexts["地図から、ワインを知る。"].exists)
        XCTAssertTrue(app.descendants(matching: .any)["atlas.map"].exists)
        app.segmentedControls["atlas.displayMode"].buttons["一覧"].tap()
        openBordeaux(in: app)
        tap("atlas.photo.credits", in: app)
        XCTAssertTrue(app.navigationBars["写真の出典"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.descendants(matching: .any)["atlas.photo.source"].exists)
        XCTAssertTrue(app.descendants(matching: .any)["atlas.photo.license"].exists)
        app.buttons["閉じる"].tap()
        XCTAssertTrue(app.navigationBars["産地詳細"].exists)
    }

    func testMapSelectsNonInitialRegionBeforeOpeningItsDetail() {
        let app = launch()
        XCTAssertTrue(app.descendants(matching: .any)["atlas.map"].exists)
        XCTAssertTrue(app.descendants(matching: .any)["atlas.selected.france_bordeaux"].exists)

        let regionID = "france_burgundy"
        let markerID = "regionMap.marker.\(regionID)"
        let marker = app.descendants(matching: .any)[markerID].firstMatch
        if marker.exists {
            tap(markerID, in: app)
        } else {
            // Cluster membership changes with available map width, so discover it by region ID.
            let cluster = app.descendants(matching: .any).matching(NSPredicate(
                format: "identifier BEGINSWITH %@ AND identifier CONTAINS %@",
                "regionMap.cluster.", regionID
            )).firstMatch
            XCTAssertTrue(cluster.waitForExistence(timeout: 5))
            for _ in 0..<10 where !cluster.isHittable { app.swipeUp() }
            XCTAssertTrue(cluster.isHittable)
            cluster.tap()
            XCTAssertTrue(marker.waitForExistence(timeout: 5))
            XCTAssertTrue(marker.isHittable)
            marker.tap()
        }

        let preview = app.descendants(matching: .any)["atlas.selected.\(regionID)"]
        XCTAssertTrue(preview.waitForExistence(timeout: 5))
        XCTAssertFalse(app.descendants(matching: .any)["atlas.selected.france_bordeaux"].exists)
        XCTAssertTrue(app.navigationBars["CruNote"].exists)
        XCTAssertFalse(app.navigationBars["産地詳細"].exists)

        tap("atlas.detail.open", in: app)
        XCTAssertTrue(app.navigationBars["産地詳細"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.descendants(matching: .any)["regionMap.detail.\(regionID)"].exists)
        XCTAssertTrue(app.staticTexts["ブルゴーニュ"].exists)
    }

    func testAnswerToMapAndBackPreservesRevealedAnswer() {
        let app = launch()
        app.segmentedControls["atlas.displayMode"].buttons["一覧"].tap()
        openBordeaux(in: app)
        tap("regionMap.study.10", in: app)
        XCTAssertTrue(app.buttons["study.session.choice.0"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.descendants(matching: .any)["question.regions"].exists)
        app.buttons["study.session.choice.0"].tap()
        tap("question.region.france_bordeaux", in: app)
        XCTAssertTrue(app.navigationBars["フランス"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.descendants(matching: .any)["atlas.selected.france_bordeaux"].exists)
        app.navigationBars["フランス"].buttons.firstMatch.tap()
        XCTAssertTrue(app.navigationBars["1 / 10 問"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["解答"].exists)
        XCTAssertTrue(app.descendants(matching: .any)["question.regions"].exists)
        let rating = app.buttons["理解できた"]
        for _ in 0..<15 where !rating.isHittable { app.swipeUp() }
        rating.tap()
        XCTAssertTrue(app.navigationBars["2 / 10 問"].waitForExistence(timeout: 5))
    }

    func testMissingPhotoKeepsRegionTextAndStudyAvailable() {
        let app = launch(extra: ["-UITestAtlasMediaLoadFailure"])
        app.segmentedControls["atlas.displayMode"].buttons["一覧"].tap()
        openBordeaux(in: app)
        XCTAssertTrue(app.descendants(matching: .any)["atlas.photo.placeholder.france_bordeaux"].exists)
        XCTAssertTrue(app.staticTexts["ボルドー"].exists)
        tap("regionMap.study.10", in: app)
        XCTAssertTrue(app.buttons["study.session.choice.0"].waitForExistence(timeout: 5))
    }

    func testExploreMapFailureShowsJapaneseError() {
        let app = launch(extra: ["-UITestRegionMapLoadFailure"])
        XCTAssertTrue(app.descendants(matching: .any)["regionMap.loadError"].exists)
        XCTAssertTrue(app.staticTexts["産地マップを利用できません"].exists)
    }

    func testQuestionDetailShowsMapLinkOnlyAfterReveal() {
        let app = launch()
        app.segmentedControls["atlas.displayMode"].buttons["一覧"].tap()
        openBordeaux(in: app)
        tap("atlas.relatedQuestions", in: app)
        let question = app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@", "atlas.relatedQuestion.")).firstMatch
        for _ in 0..<10 where !question.isHittable { app.swipeUp() }
        XCTAssertTrue(question.exists)
        question.tap()
        XCTAssertTrue(app.navigationBars["問題"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.descendants(matching: .any)["question.regions"].exists)
        let reveal = app.buttons["解答を見る"]
        for _ in 0..<15 where !reveal.isHittable { app.swipeUp() }
        reveal.tap()
        tap("question.region.france_bordeaux", in: app)
        XCTAssertTrue(app.navigationBars["フランス"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.buttons["atlas.detail.open"].exists)
        app.navigationBars["フランス"].buttons.firstMatch.tap()
        XCTAssertTrue(app.navigationBars["問題"].exists)
        XCTAssertFalse(app.buttons["解答を見る"].exists)
    }

    func testFranceExplorationRemainsAvailableWithoutPro() {
        let app = launch(extra: ["-UITestFreeEntitlement"], pro: false)
        XCTAssertTrue(app.descendants(matching: .any)["atlas.map"].exists)
        app.segmentedControls["atlas.displayMode"].buttons["一覧"].tap()
        openBordeaux(in: app)
        XCTAssertTrue(app.staticTexts["ボルドー"].exists)
        XCTAssertFalse(app.buttons["paywall.purchase"].exists)
    }

    private func launch(extra: [String] = [], pro: Bool = true) -> XCUIApplication {
        let app = XCUIApplication()
        app.launchArguments = ["-UITestInMemoryStore"] + (pro ? ["-UITestProEntitlement"] : []) + extra
        app.launch()
        XCTAssertTrue(app.tabBars.buttons["探索"].waitForExistence(timeout: 20))
        return app
    }

    private func openBordeaux(in app: XCUIApplication) {
        tap("regionMap.list.france_bordeaux", in: app)
        XCTAssertTrue(app.navigationBars["産地詳細"].waitForExistence(timeout: 5))
    }

    private func tap(_ identifier: String, in app: XCUIApplication) {
        let element = app.descendants(matching: .any)[identifier].firstMatch
        for _ in 0..<15 where !element.isHittable { app.swipeUp() }
        XCTAssertTrue(element.waitForExistence(timeout: 5), identifier)
        XCTAssertTrue(element.isHittable, identifier)
        element.tap()
    }
}
