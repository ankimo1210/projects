import XCTest
@testable import WSET

@MainActor
final class RegionMapTests: XCTestCase {
    func testStoreLoadsValidPackAndIndexesMapsAndRegions() throws {
        let store = RegionMapStore(data: try validPackData())

        XCTAssertNil(store.loadError)
        XCTAssertEqual(store.maps.map(\.id), ["france"])
        XCTAssertEqual(store.map(id: "france")?.nameJapanese, "フランス")
        XCTAssertEqual(store.region(id: "france_bordeaux")?.nameJapanese, "ボルドー")
        XCTAssertEqual(store.source(id: "self_made")?.license, "プロジェクト自作")
        XCTAssertEqual(
            store.region(id: "france_bordeaux")?.comparison.climateInfluence.summary,
            "緯度と気候"
        )
    }

    func testStoreRejectsMissingAndUnsupportedData() throws {
        XCTAssertNotNil(RegionMapStore(data: nil).loadError)

        var payload = try JSONSerialization.jsonObject(with: validPackData()) as! [String: Any]
        payload["schemaVersion"] = 99
        let invalidData = try JSONSerialization.data(withJSONObject: payload)
        let store = RegionMapStore(data: invalidData)

        XCTAssertNil(store.pack)
        XCTAssertEqual(store.loadError, "産地マップデータを読み込めませんでした。")
    }

    func testStoreRejectsMissingDependencyHashes() throws {
        for key in ["sourceHash", "questionPackSourceHash", "referencePackSourceHash"] {
            var payload = try JSONSerialization.jsonObject(
                with: validPackData()
            ) as! [String: Any]
            payload[key] = ""
            let store = RegionMapStore(
                data: try JSONSerialization.data(withJSONObject: payload)
            )

            XCTAssertNil(store.pack, "\(key) must be present")
            XCTAssertEqual(
                store.loadError,
                "産地マップデータを読み込めませんでした。"
            )
        }
    }

    func testStoreRejectsBrokenComparisonSourceAndDate() throws {
        var payload = try JSONSerialization.jsonObject(with: validPackData()) as! [String: Any]
        var maps = payload["maps"] as! [[String: Any]]
        var regions = maps[0]["regions"] as! [[String: Any]]
        var comparison = regions[0]["comparison"] as! [String: Any]
        var climate = comparison["climateInfluence"] as! [String: Any]
        climate["sourceIDs"] = ["missing"]
        comparison["climateInfluence"] = climate
        regions[0]["comparison"] = comparison
        maps[0]["regions"] = regions
        payload["maps"] = maps

        XCTAssertNotNil(
            RegionMapStore(
                data: try JSONSerialization.data(withJSONObject: payload)
            ).loadError
        )

        climate["sourceIDs"] = ["self_made"]
        climate["checkedAt"] = "2026/07/19"
        comparison["climateInfluence"] = climate
        regions[0]["comparison"] = comparison
        maps[0]["regions"] = regions
        payload["maps"] = maps
        XCTAssertNotNil(
            RegionMapStore(
                data: try JSONSerialization.data(withJSONObject: payload)
            ).loadError
        )
    }

    func testComparisonKeywordsPreserveOrderAndSeparateCommonAndDifferences() throws {
        let first = try comparisonFact(keywords: ["AOP", "石灰岩", "ピノ・ノワール"])
        let second = try comparisonFact(keywords: ["AOP", "白亜", "ピノ・ノワール"])

        XCTAssertEqual(
            first.keywordsCompared(to: second),
            RegionComparisonKeywords(
                common: ["AOP", "ピノ・ノワール"],
                firstOnly: ["石灰岩"],
                secondOnly: ["白亜"]
            )
        )
    }

    func testParentRegionMatchingUnionsAliasesAndDeduplicatesQuestions() {
        let items = [
            focusItem(id: "bordeaux", regions: ["ボルドー"]),
            focusItem(id: "medoc", regions: ["メドック", "ボルドー"]),
            focusItem(id: "marne-old", regions: ["ヴァレ・ドゥ・ラ・マルヌ"]),
            focusItem(id: "other", regions: ["ブルゴーニュ"]),
        ]

        XCTAssertEqual(
            RegionStudyQuery.matchingQuestionIDs(
                focusValues: ["ボルドー", "メドック"],
                items: items
            ),
            Set(["bordeaux", "medoc"])
        )
        XCTAssertEqual(
            RegionStudyQuery.matchingQuestionIDs(
                focusValues: ["ヴァレ・ド・ラ・マルヌ"],
                items: items
            ),
            Set(["marne-old"])
        )
    }

    func testStatisticsUseUniqueQuestionsAndAttemptAccuracy() throws {
        let region = try makeRegion(
            id: "france_bordeaux",
            focusValues: ["ボルドー", "メドック"]
        )
        let questions = [
            try makeQuestion(id: "q1", regions: ["ボルドー"], grapes: ["メルロ"]),
            try makeQuestion(
                id: "q2",
                regions: ["ボルドー", "メドック"],
                grapes: ["メルロ", "カベルネ・ソーヴィニヨン"]
            ),
            try makeQuestion(id: "q3", regions: ["ブルゴーニュ"], grapes: ["ピノ・ノワール"]),
        ]
        let now = Date(timeIntervalSince1970: 1_800_000_000)
        let progress = QuestionProgress(questionID: "q1")
        progress.attemptCount = 2
        progress.correctCount = 1
        progress.dueDate = now.addingTimeInterval(-60)
        let attempts = [
            StudyAttempt(questionID: "q1", isCorrect: true, rating: 3, studiedAt: now),
            StudyAttempt(questionID: "q1", isCorrect: false, rating: 0, studiedAt: now),
            StudyAttempt(questionID: "q3", isCorrect: true, rating: 3, studiedAt: now),
        ]

        let statistics = RegionStudyQuery.statistics(
            region: region,
            questions: questions,
            progress: [progress],
            attempts: attempts,
            now: now
        )

        XCTAssertEqual(statistics.questionCount, 2)
        XCTAssertEqual(statistics.studiedQuestionCount, 1)
        XCTAssertEqual(statistics.coverage, 0.5)
        XCTAssertEqual(statistics.attemptCount, 2)
        XCTAssertEqual(statistics.correctCount, 1)
        XCTAssertEqual(statistics.accuracy, 0.5)
        XCTAssertEqual(statistics.dueQuestionCount, 1)
    }

    func testStatisticsReflectUpdatedProgressInput() throws {
        let region = try makeRegion(
            id: "france_bordeaux",
            focusValues: ["ボルドー"]
        )
        let question = try makeQuestion(
            id: "q1",
            regions: ["ボルドー"],
            grapes: []
        )
        let before = RegionStudyQuery.statistics(
            region: region,
            questions: [question],
            progress: [],
            attempts: []
        )
        let progress = QuestionProgress(questionID: question.id)
        progress.attemptCount = 1
        progress.correctCount = 1
        progress.dueDate = .distantFuture
        let after = RegionStudyQuery.statistics(
            region: region,
            questions: [question],
            progress: [progress],
            attempts: []
        )

        XCTAssertEqual(before.studiedQuestionCount, 0)
        XCTAssertNil(before.accuracy)
        XCTAssertEqual(after.studiedQuestionCount, 1)
        XCTAssertEqual(after.accuracy, 1)
    }

    func testUnstudiedStatisticsAndGrapeRankingAreDeterministic() throws {
        let region = try makeRegion(id: "france_bordeaux", focusValues: ["ボルドー"])
        let questions = [
            try makeQuestion(id: "q2", regions: ["ボルドー"], grapes: ["メルロ", "カベルネ・フラン"]),
            try makeQuestion(id: "q1", regions: ["ボルドー"], grapes: ["メルロ", "メルロ"]),
        ]

        let statistics = RegionStudyQuery.statistics(
            region: region,
            questions: questions,
            progress: [],
            attempts: []
        )
        let grapes = RegionStudyQuery.relatedGrapeVarieties(region: region, questions: questions)

        XCTAssertNil(statistics.accuracy)
        XCTAssertEqual(statistics.studiedQuestionCount, 0)
        XCTAssertEqual(
            grapes,
            [
                GrapeVarietyFrequency(name: "メルロ", questionCount: 2),
                GrapeVarietyFrequency(name: "カベルネ・フラン", questionCount: 1),
            ]
        )
    }

    func testWrittenQuestionMatchingDoesNotGetDroppedByMultipleChoiceFilter() throws {
        let questions = [
            try makeQuestion(id: "mcq", regions: ["ボルドー"], grapes: []),
            try makeQuestion(
                id: "written-bordeaux",
                regions: ["ボルドー"],
                grapes: [],
                studyMode: "written_answer"
            ),
            try makeQuestion(
                id: "written-burgundy",
                regions: ["ブルゴーニュ"],
                grapes: [],
                studyMode: "written_answer"
            ),
        ]

        XCTAssertEqual(
            RegionStudyQuery.matchingQuestions(
                focusValues: ["ボルドー", "ブルゴーニュ"],
                questions: questions
            ).map(\.id),
            ["mcq"]
        )
        XCTAssertEqual(
            RegionStudyQuery.matchingWrittenQuestions(
                focusValues: ["ボルドー", "ブルゴーニュ"],
                questions: questions
            ).map(\.id),
            ["written-bordeaux", "written-burgundy"]
        )
    }

    func testRelatedTermsIncludeExplicitAndChildRegionTermsWithoutDuplicates() throws {
        let region = try makeRegion(
            id: "france_bordeaux",
            focusValues: ["ボルドー", "メドック"],
            termIDs: ["main"]
        )
        let terms = [
            makeTerm(id: "main", name: "ボルドー", region: "ボルドー"),
            makeTerm(id: "child", name: "メドック", region: "メドック"),
            makeTerm(id: "other", name: "シャブリ", region: "シャブリ"),
        ]

        XCTAssertEqual(
            RegionStudyQuery.relatedTerms(region: region, terms: terms).map(\.id),
            ["main", "child"]
        )
    }

    private func focusItem(id: String, regions: [String]) -> StudyFocusItem {
        StudyFocusItem(
            questionID: id,
            geography: ["フランス"] + regions,
            countries: ["フランス"],
            regions: regions,
            grapeVarieties: [],
            wineType: nil,
            category: "産地",
            difficulty: "D1",
            cognitiveSkill: "知識確認"
        )
    }

    private func makeRegion(
        id: String,
        focusValues: [String],
        termIDs: [String] = []
    ) throws -> MapRegion {
        let payload: [String: Any] = [
            "id": id,
            "nameJapanese": "テスト産地",
            "nameOriginal": "Test Region",
            "focusValues": focusValues,
            "position": ["x": 0.5, "y": 0.5],
            "labelOffset": ["x": 0.0, "y": 0.0],
            "termIDs": termIDs,
            "childMapID": NSNull(),
            "polygons": [],
            "comparison": comparisonPayload(),
        ]
        return try JSONDecoder().decode(
            MapRegion.self,
            from: JSONSerialization.data(withJSONObject: payload)
        )
    }

    private func makeQuestion(
        id: String,
        regions: [String],
        grapes: [String],
        studyMode: String = "multiple_choice"
    ) throws -> StudyQuestion {
        let isMultipleChoice = studyMode == "multiple_choice"
        let payload: [String: Any] = [
            "id": id,
            "prompt": "\(id)の問題",
            "answer": "正解",
            "explanation": "解説",
            "choices": isMultipleChoice ? ["正解", "誤答1", "誤答2", "誤答3"] : [],
            "correctAnswerIndex": isMultipleChoice ? 0 : NSNull(),
            "studyMode": studyMode,
            "originalFormat": studyMode,
            "unit": "unit1",
            "learningOutcome": "u1_lo2",
            "category": "産地",
            "topic": "テスト",
            "cognitiveSkill": "知識確認",
            "commandVerb": NSNull(),
            "language": "ja",
            "geography": ["フランス"] + regions,
            "countries": ["フランス"],
            "regions": regions,
            "grapeVarieties": grapes,
            "markAllocation": NSNull(),
            "sourceID": "test",
            "sourceURL": "",
            "qualityScore": 1.0,
            "reviewStatus": "approved",
        ]
        let packed = try JSONDecoder().decode(
            PackedQuestion.self,
            from: JSONSerialization.data(withJSONObject: payload)
        )
        return StudyQuestion(packed: packed)
    }

    private func makeTerm(
        id: String,
        name: String,
        region: String
    ) -> ReferenceTerm {
        ReferenceTerm(
            id: id,
            nameJapanese: name,
            nameEnglish: nil,
            nameFrench: nil,
            reading: nil,
            category: "産地・地名",
            summary: "概要",
            description: "詳細",
            country: "フランス",
            region: region,
            labels: [],
            relatedTermIDs: [],
            aliases: [],
            questionIDs: [],
            sourceID: "source",
            checkedAt: "2026-07-19"
        )
    }

    private func validPackData() throws -> Data {
        let payload: [String: Any] = [
            "schemaVersion": 2,
            "sourceHash": "source-hash",
            "questionPackSourceHash": "question-hash",
            "referencePackSourceHash": "reference-hash",
            "mapCount": 1,
            "maps": [[
                "id": "france",
                "level": "country",
                "country": "フランス",
                "nameJapanese": "フランス",
                "nameOriginal": "France",
                "assetName": "map_france",
                "aspectRatio": 0.82,
                "sourceIDs": ["self_made"],
                "regions": [[
                    "id": "france_bordeaux",
                    "nameJapanese": "ボルドー",
                    "nameOriginal": "Bordeaux",
                    "focusValues": ["ボルドー"],
                    "position": ["x": 0.2, "y": 0.6],
                    "labelOffset": ["x": 0.1, "y": 0.0],
                    "termIDs": [],
                    "childMapID": NSNull(),
                    "polygons": [],
                    "comparison": comparisonPayload(),
                ]],
            ]],
            "sources": [[
                "id": "self_made",
                "name": "自作概略図",
                "url": NSNull(),
                "license": "プロジェクト自作",
                "checkedAt": "2026-07-19",
                "note": "概略位置",
            ]],
        ]
        return try JSONSerialization.data(withJSONObject: payload)
    }

    private func comparisonPayload(sourceID: String = "self_made") -> [String: Any] {
        Dictionary(
            uniqueKeysWithValues: RegionComparisonAxis.allCases.map { axis in
                (
                    axis.rawValue,
                    [
                        "summary": axis == .climateInfluence ? "緯度と気候" : axis.title,
                        "keywords": [axis.title],
                        "sourceIDs": [sourceID],
                        "checkedAt": "2026-07-19",
                        "effectiveDate": "2026-07-19",
                    ] as [String: Any]
                )
            }
        )
    }

    private func comparisonFact(keywords: [String]) throws -> RegionComparisonFact {
        try JSONDecoder().decode(
            RegionComparisonFact.self,
            from: JSONSerialization.data(
                withJSONObject: [
                    "summary": "比較",
                    "keywords": keywords,
                    "sourceIDs": ["self_made"],
                    "checkedAt": "2026-07-19",
                    "effectiveDate": "2026-07-19",
                ]
            )
        )
    }
}
