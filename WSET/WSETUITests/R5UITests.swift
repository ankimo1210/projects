import XCTest

final class R5UITests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testGlossaryTodayReviewCardIsReachable() {
        let app = XCUIApplication()
        app.launchArguments.append("-UITestProEntitlement")
        app.launch()

        XCTAssertTrue(app.tabBars.buttons["問題集"].waitForExistence(timeout: 20))
        app.tabBars.buttons["問題集"].tap()
        let glossaryLink = app.descendants(matching: .any)["reference.glossary.link"]
        XCTAssertTrue(glossaryLink.waitForExistence(timeout: 5))
        glossaryLink.tap()

        let reviewLink = app.descendants(matching: .any)["glossary.review.today"]
        XCTAssertTrue(reviewLink.waitForExistence(timeout: 5))
        reviewLink.tap()
        XCTAssertTrue(app.navigationBars["今日の用語復習"].waitForExistence(timeout: 5))
        XCTAssertTrue(
            app.descendants(matching: .any)["glossary.review.card"]
                .waitForExistence(timeout: 5)
        )
        XCTAssertTrue(app.buttons["glossary.review.reveal"].exists)
    }

    func testThirtyMinuteTastingExamShowsTimerAndTwoWineProgress() {
        let app = XCUIApplication()
        app.launchArguments.append("-UITestProEntitlement")
        app.launch()

        XCTAssertTrue(app.tabBars.buttons["テイスティング"].waitForExistence(timeout: 20))
        app.tabBars.buttons["テイスティング"].tap()
        let examEntry = app.descendants(matching: .any)["tasting.exam.entry"]
        XCTAssertTrue(examEntry.waitForExistence(timeout: 5))
        examEntry.tap()

        XCTAssertTrue(app.navigationBars["30分テイスティング試験"].waitForExistence(timeout: 5))
        XCTAssertTrue(
            app.descendants(matching: .any)["tasting.exam.timer"]
                .waitForExistence(timeout: 5)
        )
        XCTAssertTrue(app.buttons["ワイン1"].exists)
        XCTAssertTrue(app.buttons["ワイン2"].exists)
        XCTAssertTrue(
            app.descendants(matching: .any)["tasting.exam.progress.wine1"].exists
        )
        XCTAssertTrue(
            app.descendants(matching: .any)["tasting.exam.progress.wine2"].exists
        )
    }

    func testTastingVocabularyCanBeSearchedAndSelectedWithKeyboardInput() {
        let app = XCUIApplication()
        app.launchArguments += ["-UITestProEntitlement", "-UITestInMemoryStore"]
        app.launch()

        XCTAssertTrue(app.tabBars.buttons["テイスティング"].waitForExistence(timeout: 20))
        app.tabBars.buttons["テイスティング"].tap()
        app.buttons["テイスティング記録を作成"].tap()

        let vocabulary = app.descendants(matching: .any)["tasting.vocabulary.aroma"]
        XCTAssertTrue(vocabulary.waitForExistence(timeout: 5))
        let form = app.collectionViews.firstMatch
        XCTAssertTrue(form.waitForExistence(timeout: 5))
        let safeMinimumY: CGFloat = 140
        let safeMaximumY = app.frame.maxY - 160
        for _ in 0..<12 {
            let frame = vocabulary.frame
            if frame.minY >= safeMinimumY && frame.maxY <= safeMaximumY { break }

            let startY: CGFloat = frame.maxY > safeMaximumY ? 0.72 : 0.35
            let endY: CGFloat = frame.maxY > safeMaximumY ? 0.52 : 0.55
            form.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: startY))
                .press(
                    forDuration: 0.1,
                    thenDragTo: form.coordinate(
                        withNormalizedOffset: CGVector(dx: 0.5, dy: endY)
                    )
                )
        }
        XCTAssertGreaterThanOrEqual(vocabulary.frame.minY, safeMinimumY)
        XCTAssertLessThanOrEqual(vocabulary.frame.maxY, safeMaximumY)
        vocabulary.tap()

        XCTAssertTrue(app.buttons["完了"].waitForExistence(timeout: 5))
        app.swipeDown()

        let search = app.searchFields.firstMatch
        XCTAssertTrue(search.waitForExistence(timeout: 5))
        search.tap()
        search.typeText("レモ")

        let searchKey = app.keyboards.buttons["Search"]
        XCTAssertTrue(searchKey.waitForExistence(timeout: 5))
        searchKey.tap()
        XCTAssertTrue(app.keyboards.firstMatch.waitForNonExistence(timeout: 5))

        let lemon = app.buttons["tasting.vocabulary.candidate.レモン"]
        XCTAssertTrue(lemon.waitForExistence(timeout: 5))
        lemon.tap()
        let confirmation = app.staticTexts["tasting.vocabulary.confirmation"]
        XCTAssertTrue(confirmation.waitForExistence(timeout: 5))
        XCTAssertEqual(confirmation.label, "「レモン」を追加しました")
    }

    func testDailyStudyCombinesQuestionAndTermRecommendations() {
        let app = XCUIApplication()
        app.launchArguments.append("-UITestProEntitlement")
        app.launch()

        XCTAssertTrue(app.tabBars.buttons["学習"].waitForExistence(timeout: 20))
        app.tabBars.buttons["学習"].tap()
        let dailyEntry = app.descendants(matching: .any)["study.daily.open"]
        for _ in 0..<6 where !dailyEntry.exists { app.swipeUp() }
        XCTAssertTrue(dailyEntry.waitForExistence(timeout: 5))
        dailyEntry.tap()

        XCTAssertTrue(app.navigationBars["今日の学習"].waitForExistence(timeout: 5))
        XCTAssertTrue(
            app.descendants(matching: .any)["study.daily.summary"]
                .waitForExistence(timeout: 5)
        )
        let termSummary = app.descendants(matching: .any)["study.daily.termSummary"]
        for _ in 0..<5 where !termSummary.exists { app.swipeUp() }
        XCTAssertTrue(termSummary.waitForExistence(timeout: 5))
        let termStart = app.descendants(matching: .any)["study.daily.termStartButton"]
        for _ in 0..<5 where !termStart.exists { app.swipeUp() }
        XCTAssertTrue(termStart.waitForExistence(timeout: 5))
    }

    func testPastTastingNotesCanBeSelectedAndCompared() {
        let app = XCUIApplication()
        app.launchArguments += [
            "-UITestProEntitlement",
            "-UITestInMemoryStore",
            "-UITestSeedTastingComparison",
        ]
        app.launch()

        XCTAssertTrue(app.tabBars.buttons["テイスティング"].waitForExistence(timeout: 20))
        app.tabBars.buttons["テイスティング"].tap()
        let entry = app.descendants(matching: .any)["tasting.compare.entry"]
        XCTAssertTrue(entry.waitForExistence(timeout: 5))
        XCTAssertTrue(entry.isEnabled)
        entry.tap()

        XCTAssertTrue(app.navigationBars["比較する記録を選択"].waitForExistence(timeout: 5))
        let noteButtons = app.buttons.matching(
            NSPredicate(format: "identifier BEGINSWITH %@", "tasting.compare.note.")
        )
        XCTAssertGreaterThanOrEqual(noteButtons.count, 2)
        noteButtons.element(boundBy: 0).tap()
        noteButtons.element(boundBy: 1).tap()

        let start = app.descendants(matching: .any)["tasting.compare.start"]
        XCTAssertTrue(start.waitForExistence(timeout: 5))
        start.tap()
        XCTAssertTrue(app.navigationBars["SAT記録比較"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.descendants(matching: .any)["tasting.compare.screen"].exists)
        XCTAssertTrue(app.staticTexts["外観"].exists)
        for _ in 0..<4 where !app.staticTexts["味わい"].exists { app.swipeUp() }
        XCTAssertTrue(app.staticTexts["味わい"].exists)
    }
}
