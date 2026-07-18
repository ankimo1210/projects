import SwiftData
import XCTest
@testable import WSET

@MainActor
final class R5FeatureTests: XCTestCase {
    func testReferenceReviewAgainAndGoodIntervals() {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(secondsFromGMT: 0)!
        let start = Date(timeIntervalSince1970: 1_700_000_000)
        let progress = ReferenceTermProgress(termID: "term-1")

        progress.recordReview(isCorrect: false, at: start, calendar: calendar)
        XCTAssertEqual(progress.reviewAttemptCount, 1)
        XCTAssertEqual(progress.reviewCorrectCount, 0)
        XCTAssertEqual(progress.reviewIntervalDays, 0)
        XCTAssertEqual(
            progress.reviewDueDate?.timeIntervalSince(start) ?? -1,
            10 * 60,
            accuracy: 1
        )
        XCTAssertFalse(progress.isReviewDue(at: start))

        progress.recordReview(isCorrect: true, at: start, calendar: calendar)
        XCTAssertEqual(progress.reviewAttemptCount, 2)
        XCTAssertEqual(progress.reviewCorrectCount, 1)
        XCTAssertEqual(progress.reviewIntervalDays, 1)
        XCTAssertEqual(
            progress.reviewDueDate?.timeIntervalSince(start) ?? -1,
            24 * 60 * 60,
            accuracy: 1
        )
        XCTAssertEqual(progress.reviewAccuracy, 0.5)

        let dayLater = calendar.date(byAdding: .day, value: 1, to: start)!
        progress.recordReview(isCorrect: true, at: dayLater, calendar: calendar)
        XCTAssertEqual(progress.reviewIntervalDays, 2)
    }

    func testTodayReviewPrioritisesDueThenAddsUnseen() {
        let now = Date(timeIntervalSince1970: 1_700_000_000)
        let due = ReferenceTermProgress(termID: "due")
        due.reviewAttemptCount = 1
        due.reviewDueDate = now.addingTimeInterval(-60)
        due.lastReviewedAt = now.addingTimeInterval(-1_000)

        let future = ReferenceTermProgress(termID: "future")
        future.reviewAttemptCount = 1
        future.reviewDueDate = now.addingTimeInterval(60 * 60)
        future.lastReviewedAt = now

        let terms = [
            makeTerm(id: "future", japanese: "未来"),
            makeTerm(id: "new", japanese: "新規"),
            makeTerm(id: "due", japanese: "期限"),
        ]
        let selected = ReferenceReviewScheduler.terms(
            for: .today,
            allTerms: terms,
            progressRecords: [future, due],
            at: now,
            limit: 2
        )

        XCTAssertEqual(selected.map(\.id), ["due", "new"])
    }

    func testAgainReviewRemainsInNextRecommendationBeforeDueDate() {
        let now = Date(timeIntervalSince1970: 1_700_000_000)
        let weak = ReferenceTermProgress(termID: "weak")
        weak.recordReview(isCorrect: false, at: now)
        XCTAssertFalse(weak.isReviewDue(at: now.addingTimeInterval(60)))

        let plan = ReferenceReviewScheduler.plan(
            for: .today,
            allTerms: [makeTerm(id: "new", japanese: "新規"), makeTerm(id: "weak", japanese: "弱点")],
            progressRecords: [weak],
            at: now.addingTimeInterval(60),
            limit: 2
        )

        XCTAssertEqual(plan.termIDs, ["weak", "new"])
        XCTAssertEqual(plan.recommendations.first?.reason, .again)
        XCTAssertEqual(plan.reasonCounts[.again], 1)
        XCTAssertEqual(plan.reasonCounts[.unseen], 1)
        XCTAssertEqual(plan.summaryText, "もう一度・弱点 1語・未学習 1語")
    }

    func testAgainGlossaryTermBoostsItsRelatedQuestion() {
        let questions = [
            StudyAnalyticsQuestion(
                id: "ordinary",
                learningOutcome: "u1_lo1",
                category: "産地"
            ),
            StudyAnalyticsQuestion(
                id: "term-related",
                learningOutcome: "u1_lo1",
                category: "産地"
            ),
        ]

        let result = StudyRecommendationEngine.recommend(
            questions: questions,
            progressRecords: [],
            attempts: [],
            weakGlossaryQuestionIDs: ["term-related"],
            configuration: StudyRecommendationConfiguration(count: 2),
            now: Date(timeIntervalSince1970: 1_700_000_000)
        )

        XCTAssertEqual(result.questionIDs.first, "term-related")
        XCTAssertEqual(result.recommendations.first?.primaryReason.kind, .glossaryWeakness)
        XCTAssertTrue(
            result.recommendations.first?.primaryReason.detail.contains("もう一度") == true
        )
    }

    func testBookmarkReviewAndCardDirections() {
        let withOriginal = makeTerm(
            id: "mlf",
            japanese: "マロラクティック発酵",
            english: "malolactic fermentation",
            french: "fermentation malolactique"
        )
        let withoutOriginal = makeTerm(id: "plain", japanese: "用語")
        let bookmarked = ReferenceTermProgress(termID: withOriginal.id)
        bookmarked.isBookmarked = true

        XCTAssertEqual(
            ReferenceReviewScheduler.terms(
                for: .bookmarks,
                allTerms: [withoutOriginal, withOriginal],
                progressRecords: [bookmarked]
            ).map(\.id),
            [withOriginal.id]
        )
        XCTAssertEqual(withOriginal.originalDisplayName, "fermentation malolactique")
        XCTAssertEqual(
            ReferenceReviewScheduler.direction(
                for: withOriginal,
                index: 1,
                mode: .mixed
            ),
            .originalToJapanese
        )
        XCTAssertEqual(
            ReferenceReviewScheduler.direction(
                for: withoutOriginal,
                index: 0,
                mode: .originalToJapanese
            ),
            .japaneseToOriginal
        )
    }

    func testSummaryAndRegionCardDirections() {
        let term = makeTerm(
            id: "champagne",
            japanese: "シャンパーニュ",
            english: "Champagne",
            summary: "瓶内二次発酵で造る発泡性ワイン",
            country: "フランス",
            region: "シャンパーニュ"
        )

        XCTAssertEqual(
            ReferenceReviewScheduler.direction(for: term, index: 0, mode: .summaryToTerm),
            .summaryToTerm
        )
        XCTAssertEqual(
            ReferenceReviewScheduler.direction(for: term, index: 0, mode: .regionToTerm),
            .regionToTerm
        )
        XCTAssertEqual(term.regionDisplayName, "フランス・シャンパーニュ")
        XCTAssertEqual(
            ReferenceReviewScheduler.direction(for: term, index: 2, mode: .mixed),
            .summaryToTerm
        )
        XCTAssertEqual(
            ReferenceReviewScheduler.direction(for: term, index: 3, mode: .mixed),
            .regionToTerm
        )
    }

    func testTastingExamClockUsesOriginalStartAcrossResume() {
        let start = Date(timeIntervalSince1970: 1_700_000_000)
        let snapshot = TastingExamSnapshot(startedAt: start)

        XCTAssertEqual(snapshot.remainingSeconds(at: start), 30 * 60)
        XCTAssertEqual(snapshot.remainingSeconds(at: start.addingTimeInterval(5 * 60)), 25 * 60)
        XCTAssertEqual(snapshot.remainingSeconds(at: start.addingTimeInterval(31 * 60)), 0)
        XCTAssertTrue(snapshot.isExpired(at: start.addingTimeInterval(31 * 60)))
        XCTAssertEqual(TastingExamClock.displayText(seconds: 65), "01:05")
    }

    func testTastingExamProgressTracksEditsAndRemovesEmptyText() {
        var state = TastingExamWineState()
        state.recordEdit(.appearanceClarity)
        XCTAssertEqual(state.completedFieldCount, 1)

        state.draft.appearanceColour = "レモン"
        state.recordEdit(.appearanceColour)
        XCTAssertEqual(state.completedFieldCount, 2)

        state.draft.appearanceColour = "  "
        state.recordEdit(.appearanceColour)
        XCTAssertEqual(state.completedFieldCount, 1)
        XCTAssertGreaterThan(state.completionPercent, 0)
        XCTAssertLessThan(state.completionPercent, 1)
    }

    func testTastingExamSubmittedSummaryHasALabelForEverySATField() {
        XCTAssertEqual(TastingField.allCases.count, 19)
        XCTAssertEqual(Set(TastingField.allCases.map(\.displayLabel)).count, 19)
        XCTAssertEqual(TastingField.appearanceClarity.displayLabel, "清澄度")
        XCTAssertEqual(TastingField.conclusion.displayLabel, "結論の根拠")
    }

    func testTastingVocabularySearchAndFrequentlyUsedRankingAreDeterministic() {
        XCTAssertEqual(
            TastingVocabularyCatalog.groups(matching: "レモ").flatMap(\.values),
            ["レモン"]
        )
        XCTAssertEqual(
            TastingVocabularyCatalog.frequentlyUsedValues(
                in: [
                    "レモン、白い花",
                    "白い花, レモン; 石灰",
                    "カシス／レモン",
                    "レモン、レモン",
                ],
                limit: 3
            ),
            ["レモン", "白い花", "カシス"]
        )
        XCTAssertEqual(
            TastingVocabularyCatalog.frequentlyUsedValues(
                in: ["レモン、白い花", "ライム"],
                matching: "ライ"
            ),
            ["ライム"]
        )
    }

    func testTastingExamDraftStoreRoundTripsBothWines() throws {
        let suiteName = "R5FeatureTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suiteName))
        defer { defaults.removePersistentDomain(forName: suiteName) }
        let store = TastingExamDraftStore(defaults: defaults)
        var snapshot = TastingExamSnapshot(
            startedAt: Date(timeIntervalSince1970: 1_700_000_000)
        )
        snapshot.wineOne.draft.aromaNotes = "レモン"
        snapshot.wineOne.recordEdit(.aromaNotes)
        snapshot.wineTwo.draft.flavourNotes = "カシス"
        snapshot.wineTwo.recordEdit(.flavourNotes)

        store.save(snapshot)
        XCTAssertEqual(store.load(), snapshot)
        store.clear()
        XCTAssertNil(store.load())
    }

    func testLegacyBackupWithoutR5FieldsStillDecodes() throws {
        let json = """
        {
          "schemaVersion": 1,
          "createdAt": "2026-07-18T00:00:00Z",
          "progress": [],
          "attempts": [],
          "tastingNotes": [{
            "id": "00000000-0000-0000-0000-000000000001",
            "sampleLabel": "Wine",
            "tastedAt": "2026-07-18T00:00:00Z",
            "wineName": "Legacy",
            "appearanceClarity": "Clear",
            "appearanceIntensity": "Medium",
            "appearanceColour": "Ruby",
            "noseCondition": "Clean",
            "noseIntensity": "Medium",
            "noseDevelopment": "Youthful",
            "aromaNotes": "Cherry",
            "sweetness": "Dry",
            "acidity": "Medium",
            "tannin": "Medium",
            "alcohol": "Medium",
            "body": "Medium",
            "flavourIntensity": "Medium",
            "finish": "Medium",
            "flavourNotes": "Cherry",
            "quality": "Good",
            "readiness": "Can drink now, suitable for ageing",
            "conclusion": "Balanced"
          }],
          "mockExams": []
        }
        """

        let backup = try StudyBackupDocument.decode(Data(json.utf8))
        XCTAssertNil(backup.termProgress)
        let tasting = try XCTUnwrap(backup.tastingNotes.first)
        XCTAssertNil(tasting.examStartedAt)
        XCTAssertNil(tasting.examWasTimeExpired)
        XCTAssertEqual(tasting.wineName, "Legacy")
    }

    func testReferenceProgressBackupRoundTrip() throws {
        let configuration = ModelConfiguration(isStoredInMemoryOnly: true)
        let container = try ModelContainer(
            for: ReferenceTermProgress.self,
            configurations: configuration
        )
        let context = container.mainContext
        let progress = ReferenceTermProgress(termID: "term-backup")
        progress.isBookmarked = true
        progress.recordReview(
            isCorrect: true,
            at: Date(timeIntervalSince1970: 1_700_000_000)
        )
        context.insert(progress)
        try context.save()

        let snapshots = R5BackupSupport.snapshots(in: context)
        XCTAssertEqual(snapshots.count, 1)
        context.delete(progress)
        try context.save()
        XCTAssertEqual(try R5BackupSupport.restore(snapshots, into: context), 1)
        try context.save()

        let restored = try XCTUnwrap(
            context.fetch(FetchDescriptor<ReferenceTermProgress>()).first
        )
        XCTAssertTrue(restored.isBookmarked)
        XCTAssertEqual(restored.reviewAttemptCount, 1)
        XCTAssertEqual(restored.reviewCorrectCount, 1)
    }

    func testApprovedTermIDMigrationMergesSwiftDataHistoryWithoutLoss() throws {
        let container = try ModelContainer(
            for: ReferenceTermProgress.self,
            configurations: ModelConfiguration(isStoredInMemoryOnly: true)
        )
        let context = container.mainContext
        let canonical = ReferenceTermProgress(termID: "term-canonical")
        canonical.viewCount = 2
        canonical.reviewAttemptCount = 3
        canonical.reviewCorrectCount = 2
        canonical.lastReviewedAt = Date(timeIntervalSince1970: 100)
        canonical.reviewDueDate = Date(timeIntervalSince1970: 200)
        canonical.reviewIntervalDays = 2
        canonical.lastReviewWasCorrect = true
        let retired = ReferenceTermProgress(termID: "term-retired")
        retired.isBookmarked = true
        retired.viewCount = 4
        retired.lastViewedAt = Date(timeIntervalSince1970: 500)
        retired.reviewAttemptCount = 2
        retired.reviewCorrectCount = 1
        retired.lastReviewedAt = Date(timeIntervalSince1970: 300)
        retired.reviewDueDate = Date(timeIntervalSince1970: 600)
        retired.reviewIntervalDays = 4
        retired.lastReviewWasCorrect = false
        context.insert(canonical)
        context.insert(retired)
        try context.save()

        XCTAssertEqual(
            try R5BackupSupport.migrateTermIDs(
                ["term-retired": "term-canonical"],
                in: context
            ),
            1
        )
        try context.save()

        let records = try context.fetch(FetchDescriptor<ReferenceTermProgress>())
        let merged = try XCTUnwrap(records.first)
        XCTAssertEqual(records.count, 1)
        XCTAssertEqual(merged.termID, "term-canonical")
        XCTAssertTrue(merged.isBookmarked)
        XCTAssertEqual(merged.viewCount, 6)
        XCTAssertEqual(merged.lastViewedAt, Date(timeIntervalSince1970: 500))
        XCTAssertEqual(merged.reviewAttemptCount, 5)
        XCTAssertEqual(merged.reviewCorrectCount, 3)
        XCTAssertEqual(merged.lastReviewedAt, Date(timeIntervalSince1970: 300))
        XCTAssertEqual(merged.reviewDueDate, Date(timeIntervalSince1970: 600))
        XCTAssertEqual(merged.reviewIntervalDays, 4)
        XCTAssertEqual(merged.lastReviewWasCorrect, false)
    }

    func testLegacyBackupTermIDsConsolidateIntoCanonicalHistory() throws {
        let container = try ModelContainer(
            for: ReferenceTermProgress.self,
            configurations: ModelConfiguration(isStoredInMemoryOnly: true)
        )
        let context = container.mainContext
        let olderCanonical = ReferenceTermProgressBackup(
            termID: "term-canonical",
            isBookmarked: false,
            lastViewedAt: Date(timeIntervalSince1970: 100),
            viewCount: 2,
            reviewDueDate: Date(timeIntervalSince1970: 200),
            reviewIntervalDays: 2,
            reviewAttemptCount: 3,
            reviewCorrectCount: 2,
            lastReviewedAt: Date(timeIntervalSince1970: 100),
            lastReviewWasCorrect: true
        )
        let newerRetired = ReferenceTermProgressBackup(
            termID: "term-retired",
            isBookmarked: true,
            lastViewedAt: Date(timeIntervalSince1970: 400),
            viewCount: 4,
            reviewDueDate: Date(timeIntervalSince1970: 500),
            reviewIntervalDays: 4,
            reviewAttemptCount: 2,
            reviewCorrectCount: 1,
            lastReviewedAt: Date(timeIntervalSince1970: 300),
            lastReviewWasCorrect: false
        )

        XCTAssertEqual(
            try R5BackupSupport.restore(
                [olderCanonical, newerRetired],
                into: context,
                termIDMigrations: ["term-retired": "term-canonical"]
            ),
            1
        )
        try context.save()

        let records = try context.fetch(FetchDescriptor<ReferenceTermProgress>())
        let restored = try XCTUnwrap(records.first)
        XCTAssertEqual(records.count, 1)
        XCTAssertEqual(restored.termID, "term-canonical")
        XCTAssertTrue(restored.isBookmarked)
        XCTAssertEqual(restored.viewCount, 6)
        XCTAssertEqual(restored.reviewAttemptCount, 5)
        XCTAssertEqual(restored.reviewCorrectCount, 3)
        XCTAssertEqual(restored.reviewDueDate, Date(timeIntervalSince1970: 500))
        XCTAssertEqual(restored.lastReviewWasCorrect, false)
    }

    func testTastingJSONAndCSVIndividualExports() throws {
        var draft = TastingDraft()
        draft.wineName = "甲州 2025"
        draft.appearanceColour = "淡いレモン"
        draft.aromaNotes = "柑橘, 花"
        let note = TastingNote(draft: draft)
        let snapshot = TastingNoteExportSnapshot(note: note)

        let jsonData = try TastingExportService.data(for: snapshot, format: .json)
        let decoded = try JSONDecoder.withISO8601.decode(
            TastingNoteExportSnapshot.self,
            from: jsonData
        )
        XCTAssertEqual(decoded.wineName, "甲州 2025")

        let csvData = try TastingExportService.data(for: snapshot, format: .csv)
        let csv = try XCTUnwrap(String(data: csvData, encoding: .utf8))
        XCTAssertEqual(Array(csvData.prefix(3)), [0xEF, 0xBB, 0xBF])
        XCTAssertTrue(csv.contains("\"柑橘, 花\""))
        XCTAssertTrue(csv.contains("wine_name"))
    }

    func testTastingComparisonBuildsJapaneseSATRowsWithoutChangingRawValues() throws {
        var firstDraft = TastingDraft()
        firstDraft.wineName = "ワインA"
        firstDraft.appearanceColour = "ルビー"
        firstDraft.acidity = "High"
        firstDraft.quality = "Very good"
        var secondDraft = TastingDraft()
        secondDraft.wineName = "ワインB"
        secondDraft.appearanceColour = "レモン"
        secondDraft.acidity = "Low"
        secondDraft.quality = "Good"
        let first = TastingNote(draft: firstDraft)
        let second = TastingNote(draft: secondDraft)

        let sections = TastingComparisonService.sections(first: first, second: second)
        XCTAssertEqual(sections.map(\.title), ["ワイン", "外観", "香り", "味わい", "結論"])
        let palate = try XCTUnwrap(sections.first { $0.id == "palate" })
        let acidity = try XCTUnwrap(palate.fields.first { $0.id == "palate.acidity" })
        XCTAssertEqual(acidity.firstValue, "高い")
        XCTAssertEqual(acidity.secondValue, "低い")
        let conclusion = try XCTUnwrap(sections.first { $0.id == "conclusions" })
        let quality = try XCTUnwrap(conclusion.fields.first { $0.id == "conclusions.quality" })
        XCTAssertEqual(quality.firstValue, "非常に良い")
        XCTAssertEqual(quality.secondValue, "良い")
        XCTAssertEqual(first.acidity, "High")
        XCTAssertEqual(second.acidity, "Low")
    }

    private func makeTerm(
        id: String,
        japanese: String,
        english: String? = nil,
        french: String? = nil,
        summary: String = "概要",
        country: String? = nil,
        region: String? = nil
    ) -> ReferenceTerm {
        ReferenceTerm(
            id: id,
            nameJapanese: japanese,
            nameEnglish: english,
            nameFrench: french,
            reading: nil,
            category: "概念",
            summary: summary,
            description: "説明",
            country: country,
            region: region,
            labels: [],
            relatedTermIDs: [],
            aliases: [],
            questionIDs: [],
            sourceID: "test",
            checkedAt: "2026-07-19"
        )
    }
}

private extension JSONDecoder {
    static var withISO8601: JSONDecoder {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return decoder
    }
}
