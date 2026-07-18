import XCTest
@testable import WSET

final class StudyAnalyticsTests: XCTestCase {
    private let now = Date(timeIntervalSince1970: 2_000_000_000)

    func testGeographyNormalizerCanonicalizesAliasesAndUsesFallbacks() {
        XCTAssertEqual(GeographyNormalizer.normalizeCountry("  USA　"), "米国")
        XCTAssertEqual(GeographyNormalizer.normalizeCountry("イギリス"), "英国")
        XCTAssertEqual(
            GeographyNormalizer.normalizeRegion("ヴァレ・ドゥ・ラ・マルヌ"),
            "ヴァレ・ド・ラ・マルヌ"
        )
        XCTAssertEqual(
            GeographyNormalizer.normalizeRegion("サンルーカル"),
            "サンルーカル・デ・バラメダ"
        )
        XCTAssertEqual(
            GeographyNormalizer.countries(
                explicit: [],
                fallbackGeography: ["France", "ボルドー", "France"]
            ),
            ["フランス"]
        )
        XCTAssertEqual(
            GeographyNormalizer.regions(
                explicit: nil,
                fallbackGeography: ["フランス", "サンルーカル"]
            ),
            ["サンルーカル・デ・バラメダ"]
        )
        XCTAssertEqual(
            GeographyNormalizer.countries(
                explicit: ["日本"],
                fallbackGeography: []
            ),
            ["日本"]
        )
    }

    func testStudyFocusUsesSharedGeographyNormalization() {
        let items = [
            focusItem(id: "a", country: "USA", region: "サンルーカル"),
            focusItem(id: "b", country: "米国", region: "サンルーカル・デ・バラメダ"),
        ]

        let options = StudyFocusCatalog.options(for: .geography, in: items)

        XCTAssertEqual(options.map(\.value), ["米国", "サンルーカル・デ・バラメダ"])
        XCTAssertEqual(options.map(\.questionCount), [2, 2])
        XCTAssertEqual(
            StudyFocusCatalog.matchingQuestionIDs(
                for: .geography,
                value: "サンルーカル",
                in: items
            ),
            Set(["a", "b"])
        )
    }

    func testStatisticsAggregateUniqueQuestionsAcrossEveryDimension() {
        let questions = analyticsQuestions()
        let progress = [
            analyticsProgress(
                id: "q1",
                attempts: 3,
                correct: 1,
                dueDate: now.addingTimeInterval(-3_600)
            ),
            analyticsProgress(
                id: "q2",
                attempts: 2,
                correct: 2,
                dueDate: now.addingTimeInterval(86_400)
            ),
        ]
        let attempts = [
            analyticsAttempt(id: "a1", questionID: "q1", correct: false, secondsAgo: 100),
            analyticsAttempt(id: "a2", questionID: "q1", correct: false, secondsAgo: 200),
            analyticsAttempt(id: "a3", questionID: "q1", correct: true, secondsAgo: 300),
            analyticsAttempt(id: "a4", questionID: "q2", correct: true, secondsAgo: 400),
            analyticsAttempt(id: "a5", questionID: "q2", correct: true, secondsAgo: 500),
        ]

        let countries = StudyStatisticsService.statistics(
            for: .country,
            questions: questions,
            progressRecords: progress,
            attempts: attempts,
            now: now
        )
        let france = tryUnwrap(countries.first { $0.value == "フランス" })
        XCTAssertEqual(france.questionCount, 2)
        XCTAssertEqual(france.studiedQuestionCount, 2)
        XCTAssertEqual(france.attemptCount, 5)
        XCTAssertEqual(france.correctCount, 3)
        XCTAssertEqual(france.accuracy ?? -1, 0.6, accuracy: 0.000_001)
        XCTAssertEqual(france.recentAccuracy ?? -1, 0.6, accuracy: 0.000_001)
        XCTAssertEqual(france.dueCount, 1)
        XCTAssertEqual(france.sampleState, .sufficient)

        let regions = StudyStatisticsService.statistics(
            for: .region,
            questions: questions,
            progressRecords: progress,
            attempts: attempts,
            now: now
        )
        XCTAssertEqual(regions.first { $0.value == "ボルドー" }?.questionCount, 2)

        let grapes = StudyStatisticsService.statistics(
            for: .grapeVariety,
            questions: questions,
            progressRecords: progress,
            attempts: attempts,
            now: now
        )
        XCTAssertEqual(grapes.first { $0.value == "シラー／シラーズ" }?.questionCount, 2)

        let expectedValues: [(StudyStatisticsDimension, String)] = [
            (.learningOutcome, "u1_lo1"),
            (.wineType, "非発泡性ワイン"),
            (.knowledgeArea, "自然要因"),
            (.difficulty, "D2"),
            (.cognitiveSkill, "因果説明"),
        ]
        for (dimension, value) in expectedValues {
            let statistics = StudyStatisticsService.statistics(
                for: dimension,
                questions: questions,
                progressRecords: progress,
                attempts: attempts,
                now: now
            )
            XCTAssertNotNil(statistics.first { $0.value == value }, "Missing \(dimension): \(value)")
        }

        let italy = tryUnwrap(countries.first { $0.value == "イタリア" })
        XCTAssertEqual(italy.questionCount, 1)
        XCTAssertNil(italy.accuracy)
        XCTAssertEqual(italy.sampleState, .noData)
    }

    func testStatisticsDoNotClassifySmallSamplesAsWeak() {
        let question = StudyAnalyticsQuestion(
            id: "limited",
            learningOutcome: "u1_lo1",
            category: "法律・表示"
        )
        let statistic = tryUnwrap(
            StudyStatisticsService.statistics(
                for: .knowledgeArea,
                questions: [question],
                progressRecords: [
                    analyticsProgress(
                        id: "limited",
                        attempts: 2,
                        correct: 0,
                        dueDate: now.addingTimeInterval(1)
                    ),
                ],
                attempts: [],
                now: now,
                minimumSampleSize: 5
            ).first
        )

        XCTAssertEqual(statistic.accuracy, 0)
        XCTAssertEqual(statistic.sampleState, .insufficient)
        XCTAssertFalse(statistic.isWeak())
        XCTAssertTrue(StudyStatisticsService.weakest([statistic]).isEmpty)
    }

    func testStatisticsMatchingUsesCanonicalAliases() {
        let questions = analyticsQuestions()

        XCTAssertEqual(
            StudyStatisticsService.matchingQuestionIDs(
                for: .grapeVariety,
                value: "シラーズ",
                questions: questions
            ),
            Set(["q1", "q2"])
        )
        XCTAssertEqual(
            StudyStatisticsService.matchingQuestionIDs(
                for: .country,
                value: "France",
                questions: questions
            ),
            Set(["q1", "q2"])
        )
    }

    func testRecommendationIsDeterministicExplainableAndPrioritizesDueQuestions() {
        let questions = recommendationQuestions()
        let progress = recommendationProgress()
        let attempts = [
            analyticsAttempt(
                id: "mistake",
                questionID: "mistake",
                correct: false,
                secondsAgo: 3_600
            ),
        ]
        let configuration = StudyRecommendationConfiguration(
            count: 4,
            minimumWeaknessAttempts: 5
        )

        let first = StudyRecommendationEngine.recommend(
            questions: questions,
            progressRecords: progress,
            attempts: attempts,
            configuration: configuration,
            now: now
        )
        let second = StudyRecommendationEngine.recommend(
            questions: Array(questions.reversed()),
            progressRecords: Array(progress.reversed()),
            attempts: Array(attempts.reversed()),
            configuration: configuration,
            now: now
        )

        XCTAssertEqual(first, second)
        XCTAssertEqual(Array(first.questionIDs.prefix(3)), ["due", "mistake", "weak"])
        XCTAssertEqual(first.recommendations[0].primaryReason.kind, .due)
        XCTAssertEqual(first.recommendations[1].primaryReason.kind, .recentMistake)
        XCTAssertEqual(first.recommendations[2].primaryReason.kind, .weakness)
        XCTAssertFalse(first.recommendations.flatMap(\.scoreBreakdown).contains { $0.detail.isEmpty })
        XCTAssertEqual(
            first.primaryReasonCounts.values.reduce(0, +),
            first.recommendations.count
        )
    }

    func testRecommendationHonorsExclusions() {
        let result = StudyRecommendationEngine.recommend(
            questions: recommendationQuestions(),
            progressRecords: recommendationProgress(),
            attempts: [
                analyticsAttempt(
                    id: "mistake",
                    questionID: "mistake",
                    correct: false,
                    secondsAgo: 3_600
                ),
            ],
            configuration: StudyRecommendationConfiguration(
                count: 2,
                excludedQuestionIDs: ["due"]
            ),
            now: now
        )

        XCTAssertFalse(result.questionIDs.contains("due"))
        XCTAssertEqual(result.questionIDs.first, "mistake")
    }

    func testRecommendationBalancesLearningOutcomesForEquivalentCandidates() {
        let questions = [
            StudyAnalyticsQuestion(id: "a1", learningOutcome: "u1_lo1", category: "品種"),
            StudyAnalyticsQuestion(id: "a2", learningOutcome: "u1_lo1", category: "品種"),
            StudyAnalyticsQuestion(id: "b1", learningOutcome: "u1_lo2", category: "品種"),
            StudyAnalyticsQuestion(id: "b2", learningOutcome: "u1_lo2", category: "品種"),
        ]

        let result = StudyRecommendationEngine.recommend(
            questions: questions,
            progressRecords: [],
            attempts: [],
            configuration: StudyRecommendationConfiguration(count: 4),
            now: now
        )

        XCTAssertEqual(Array(result.questionIDs.prefix(2)), ["a1", "b1"])
        XCTAssertTrue(
            result.recommendations.allSatisfy {
                $0.scoreBreakdown.contains { $0.kind == .learningOutcomeBalance }
            }
        )
    }

    func testRecommendationExplainsUnstudiedAndLearningOutcomeBalance() {
        let questions = [
            StudyAnalyticsQuestion(
                id: "studied-lo1",
                learningOutcome: "u1_lo1",
                category: "栽培"
            ),
            StudyAnalyticsQuestion(
                id: "unstudied-lo2",
                learningOutcome: "u1_lo2",
                category: "醸造"
            ),
        ]
        let progress = [
            StudyAnalyticsProgress(
                questionID: "studied-lo1",
                attemptCount: 1,
                correctCount: 1,
                dueDate: now.addingTimeInterval(86_400),
                lastStudiedAt: now,
                lastWasCorrect: true
            ),
        ]

        let result = StudyRecommendationEngine.recommend(
            questions: questions,
            progressRecords: progress,
            attempts: [],
            configuration: StudyRecommendationConfiguration(count: 2),
            now: now
        )
        let recommendation = result.recommendations.first {
            $0.questionID == "unstudied-lo2"
        }

        XCTAssertEqual(recommendation?.primaryReason.kind, .unstudied)
        XCTAssertTrue(
            recommendation?.scoreBreakdown.contains {
                $0.kind == .learningOutcomeBalance && $0.detail.contains("学習量を補正")
            } == true
        )
    }

    private func focusItem(id: String, country: String, region: String) -> StudyFocusItem {
        StudyFocusItem(
            questionID: id,
            geography: [country, region],
            countries: [country],
            regions: [region],
            grapeVarieties: [],
            wineType: nil,
            category: "産地",
            difficulty: "D1",
            cognitiveSkill: "知識確認"
        )
    }

    private func analyticsQuestions() -> [StudyAnalyticsQuestion] {
        [
            StudyAnalyticsQuestion(
                id: "q1",
                learningOutcome: "u1_lo1",
                geography: ["France", "ボルドー"],
                countries: ["France"],
                regions: ["ボルドー"],
                grapeVarieties: ["シラー"],
                wineType: "赤非発泡性ワイン",
                category: "自然要因・産地",
                difficulty: "D2",
                cognitiveSkill: "因果説明"
            ),
            StudyAnalyticsQuestion(
                id: "q2",
                learningOutcome: "u1_lo2",
                geography: ["フランス", "ボルドー"],
                countries: ["フランス"],
                regions: ["ボルドー"],
                grapeVarieties: ["シラーズ"],
                wineType: "非発泡性ワイン",
                category: "自然要因",
                difficulty: "D2",
                cognitiveSkill: "因果説明"
            ),
            StudyAnalyticsQuestion(
                id: "q3",
                learningOutcome: "u1_lo3",
                geography: ["イタリア", "ピエモンテ"],
                countries: ["イタリア"],
                regions: ["ピエモンテ"],
                grapeVarieties: ["ネッビオーロ"],
                wineType: "赤ワイン",
                category: "法律・表示",
                difficulty: "D1",
                cognitiveSkill: "知識確認"
            ),
        ]
    }

    private func recommendationQuestions() -> [StudyAnalyticsQuestion] {
        [
            StudyAnalyticsQuestion(
                id: "due",
                learningOutcome: "u1_lo1",
                category: "自然要因"
            ),
            StudyAnalyticsQuestion(
                id: "mistake",
                learningOutcome: "u1_lo1",
                category: "品種"
            ),
            StudyAnalyticsQuestion(
                id: "weak",
                learningOutcome: "u1_lo2",
                category: "法律・表示"
            ),
            StudyAnalyticsQuestion(
                id: "new-a",
                learningOutcome: "u1_lo3",
                category: "産地"
            ),
            StudyAnalyticsQuestion(
                id: "new-b",
                learningOutcome: "u1_lo4",
                category: "サービス"
            ),
        ]
    }

    private func recommendationProgress() -> [StudyAnalyticsProgress] {
        [
            analyticsProgress(
                id: "due",
                attempts: 3,
                correct: 3,
                dueDate: now.addingTimeInterval(-86_400)
            ),
            analyticsProgress(
                id: "mistake",
                attempts: 1,
                correct: 0,
                dueDate: now.addingTimeInterval(86_400),
                lastWasCorrect: false
            ),
            analyticsProgress(
                id: "weak",
                attempts: 5,
                correct: 1,
                dueDate: now.addingTimeInterval(86_400),
                lastWasCorrect: true
            ),
        ]
    }

    private func analyticsProgress(
        id: String,
        attempts: Int,
        correct: Int,
        dueDate: Date,
        lastWasCorrect: Bool? = nil
    ) -> StudyAnalyticsProgress {
        StudyAnalyticsProgress(
            questionID: id,
            attemptCount: attempts,
            correctCount: correct,
            dueDate: dueDate,
            lastStudiedAt: now.addingTimeInterval(-3_600),
            lastWasCorrect: lastWasCorrect
        )
    }

    private func analyticsAttempt(
        id: String,
        questionID: String,
        correct: Bool,
        secondsAgo: TimeInterval
    ) -> StudyAnalyticsAttempt {
        StudyAnalyticsAttempt(
            id: id,
            questionID: questionID,
            isCorrect: correct,
            studiedAt: now.addingTimeInterval(-secondsAgo)
        )
    }

    private func tryUnwrap<T>(
        _ value: T?,
        file: StaticString = #filePath,
        line: UInt = #line
    ) -> T {
        guard let value else {
            XCTFail("Expected a value", file: file, line: line)
            fatalError("Expected a value")
        }
        return value
    }
}
