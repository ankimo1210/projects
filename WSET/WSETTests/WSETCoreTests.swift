import SwiftData
import XCTest
@testable import WSET

@MainActor
final class WSETCoreTests: XCTestCase {
    func testSpacedRepetitionAgainAndGoodIntervals() {
        let start = Date(timeIntervalSince1970: 1_700_000_000)
        let progress = QuestionProgress(questionID: "q1")

        progress.record(isCorrect: false, rating: 0, at: start)
        XCTAssertEqual(progress.attemptCount, 1)
        XCTAssertEqual(progress.correctCount, 0)
        XCTAssertEqual(progress.intervalDays, 0)
        XCTAssertEqual(progress.dueDate.timeIntervalSince(start), 10 * 60, accuracy: 1)

        progress.record(isCorrect: true, rating: 3, at: start)
        XCTAssertEqual(progress.attemptCount, 2)
        XCTAssertEqual(progress.correctCount, 1)
        XCTAssertEqual(progress.intervalDays, 1)
        XCTAssertEqual(progress.dueDate.timeIntervalSince(start), 24 * 60 * 60, accuracy: 1)
    }

    func testTastingDraftUpdatesExistingNote() {
        var draft = TastingDraft()
        draft.wineName = "Wine A"
        draft.appearanceColour = "Lemon"
        let note = TastingNote(draft: draft)

        var edited = TastingDraft(note: note)
        edited.wineName = "Wine B"
        edited.quality = "Very good"
        note.update(from: edited)

        XCTAssertEqual(note.wineName, "Wine B")
        XCTAssertEqual(note.appearanceColour, "Lemon")
        XCTAssertEqual(note.quality, "Very good")
    }

    func testStoredEnglishSATValuesUseJapaneseDisplayText() {
        let expected = [
            "Wine": "ワイン",
            "Wine 1": "ワイン1",
            "Wine 2": "ワイン2",
            "Clear": "澄んでいる",
            "Good": "良い",
            "Very good": "非常に良い",
            "Can drink now, suitable for ageing": "今飲めるが熟成にも向く",
        ]

        for (storedValue, displayValue) in expected {
            XCTAssertEqual(SATDisplayText.japanese(storedValue), displayValue)
        }
        XCTAssertEqual(SATDisplayText.japanese("WSET Level 3 SAT"), "WSET Level 3 SAT")
        XCTAssertEqual(SATDisplayText.japanese("甲州"), "甲州")
    }

    func testUserFacingErrorsAreJapaneseAndMalformedBackupIsWrapped() {
        XCTAssertEqual(
            QuestionImporterError.packMissing.errorDescription,
            "問題データがこのビルドに含まれていません。"
        )
        XCTAssertEqual(
            QuestionImporterError.developmentContentUnavailable.errorDescription,
            "Release用の問題データがこのビルドに含まれていません。"
        )
        XCTAssertEqual(
            ReviewNotificationError.permissionDenied.errorDescription,
            "CruNoteの通知が無効です。復習通知を受け取るにはiOSの設定で通知を許可してください。"
        )
        XCTAssertEqual(
            BackupError.unsupportedSchema(2).errorDescription,
            "バックアップ形式（バージョン2）には対応していません。"
        )
        XCTAssertEqual(
            BackupError.userFacingMessage(
                for: CocoaError(.fileReadUnknown),
                fallback: "バックアップの読み込みに失敗しました。"
            ),
            "バックアップの読み込みに失敗しました。"
        )

        XCTAssertThrowsError(try StudyBackupDocument.decode(Data("not-json".utf8))) { error in
            guard let backupError = error as? BackupError else {
                return XCTFail("BackupError.invalidFile へ変換されていません。")
            }
            guard case .invalidFile = backupError else {
                return XCTFail("BackupError.invalidFile ではありません。")
            }
            XCTAssertEqual(
                backupError.errorDescription,
                "選択したファイルはCruNoteのバックアップではありません。"
            )
        }
    }

    func testFocusOptionsDeduplicateTrimAndSuppressSparseGrapesAndRegions() {
        let items = [
            StudyFocusItem(
                questionID: "q1",
                geography: [" フランス ", "ボルドー", "フランス", "", "\n"],
                grapeVarieties: ["メルロ", "メルロ", ""],
                wineType: "非発泡性赤ワイン",
                category: "自然要因",
                difficulty: "D2",
                cognitiveSkill: "因果説明"
            ),
            StudyFocusItem(
                questionID: "q2",
                geography: ["フランス", "アルザス"],
                grapeVarieties: ["メルロ"],
                wineType: "白非発泡性ワイン",
                category: "自然要因",
                difficulty: "D2",
                cognitiveSkill: "因果説明"
            ),
            StudyFocusItem(
                questionID: "q3",
                geography: ["日本"],
                grapeVarieties: ["甲州"],
                wineType: "全般",
                category: "サービス",
                difficulty: "D1",
                cognitiveSkill: "知識確認"
            ),
        ]

        XCTAssertEqual(
            StudyFocusCatalog.options(for: .geography, in: items),
            [StudyFocusOption(value: "フランス", questionCount: 2, kind: .country)]
        )
        XCTAssertEqual(
            StudyFocusCatalog.options(for: .grapeVariety, in: items),
            [StudyFocusOption(value: "メルロ", questionCount: 2, groupTitle: "国際品種")]
        )
        XCTAssertEqual(
            StudyFocusCatalog.options(for: .knowledgeArea, in: items),
            [
                StudyFocusOption(value: "自然要因", questionCount: 2),
                StudyFocusOption(value: "サービス", questionCount: 1),
            ]
        )
    }

    func testFocusGeographyOrdersMajorCountriesAndIndentsRegions() {
        let regionNames = [
            "ボルドー", "ボルドー",
            "ブルゴーニュ", "ブルゴーニュ",
            "シャンパーニュ", "シャンパーニュ", "シャンパーニュ",
        ]
        var items = regionNames.enumerated().map { index, region in
            StudyFocusItem(
                questionID: "fr-\(index)",
                geography: ["フランス", region],
                countries: ["フランス"],
                regions: [region],
                grapeVarieties: [],
                wineType: nil,
                category: "産地",
                difficulty: "D2",
                cognitiveSkill: "知識確認"
            )
        }
        items.append(
            StudyFocusItem(
                questionID: "it-1",
                geography: ["イタリア", "ピエモンテ"],
                countries: ["イタリア"],
                regions: ["ピエモンテ"],
                grapeVarieties: [],
                wineType: nil,
                category: "産地",
                difficulty: "D2",
                cognitiveSkill: "知識確認"
            )
        )

        let options = StudyFocusCatalog.options(for: .geography, in: items)

        XCTAssertEqual(options.map(\.value), ["フランス", "ボルドー", "ブルゴーニュ", "シャンパーニュ", "イタリア"])
        XCTAssertEqual(options[0].kind, .country)
        XCTAssertEqual(options[1].kind, .region)
        XCTAssertTrue(options[1].displayValue.hasPrefix("\u{3000}\u{3000}"))
    }

    func testFocusGrapesUsePriorityGroupsAndMergeAliases() {
        let grapeValues = [
            "シラー", "シラーズ", "カベルネ・ソーヴィニヨン",
            "グルナッシュ", "ガルナッチャ", "パロミノ", "パロミノ",
            "ポート主要黒ブドウ", "ポート主要黒ブドウ",
        ]
        let items = grapeValues.enumerated().map { index, grape in
            StudyFocusItem(
                questionID: "g-\(index)",
                geography: [],
                grapeVarieties: [grape],
                wineType: nil,
                category: "品種",
                difficulty: "D2",
                cognitiveSkill: "知識確認"
            )
        }

        let options = StudyFocusCatalog.options(for: .grapeVariety, in: items)
        let groups = StudyFocusCatalog.optionGroups(for: .grapeVariety, options: options)

        XCTAssertEqual(
            options.map(\.value),
            [
                "カベルネ・ソーヴィニヨン", "シラー／シラーズ",
                "グルナッシュ／ガルナッチャ", "パロミノ", "ポート主要黒ブドウ",
            ]
        )
        XCTAssertEqual(groups.map(\.title), ["国際品種", "準国際品種", "地域・固有品種", "品種グループ"])
        XCTAssertEqual(options.first { $0.value == "シラー／シラーズ" }?.questionCount, 2)
    }

    func testFocusKnowledgeAreasUseBroadLearningOrder() {
        let categories = [
            "法律面・サービス",
            "発泡性ワイン製法・産地",
            "自然要因・産地",
            "推奨・フードペアリング",
        ]
        let items = categories.enumerated().map { index, category in
            StudyFocusItem(
                questionID: "k-\(index)",
                geography: [],
                grapeVarieties: [],
                wineType: nil,
                category: category,
                difficulty: "D2",
                cognitiveSkill: "知識確認"
            )
        }

        let options = StudyFocusCatalog.options(for: .knowledgeArea, in: items)

        XCTAssertEqual(
            options.map(\.value),
            [
                "自然要因", "醸造・製法", "産地・スタイル", "法律・表示", "サービス",
                "料理との組み合わせ", "情報提供・推奨",
            ]
        )
        XCTAssertEqual(
            StudyFocusCatalog.matchingQuestionIDs(
                for: .knowledgeArea,
                value: "産地・スタイル",
                in: items
            ),
            Set(["k-1", "k-2"])
        )
    }

    func testFocusWineTypesUseFourStableGroups() {
        let rawTypes = [
            "赤非発泡性ワイン",
            "非発泡性白ワイン",
            "甘口非発泡性ワイン",
            "発泡性ワイン",
            "甘口発泡性ワイン",
            "甘口酒精強化ワイン",
            "全般",
            "甘口ワイン",
            "赤ワイン",
            "白ワイン",
            "赤・白ワイン",
            "甘口白ワイン",
            "ロゼワイン",
        ]
        let items = rawTypes.enumerated().map { index, wineType in
            StudyFocusItem(
                questionID: "q\(index)",
                geography: [],
                grapeVarieties: [],
                wineType: wineType,
                category: "分類",
                difficulty: "D1",
                cognitiveSkill: "知識確認"
            )
        }
        let options = StudyFocusCatalog.options(for: .wineType, in: items)
        let counts = Dictionary(uniqueKeysWithValues: options.map { ($0.value, $0.questionCount) })

        XCTAssertEqual(counts["共通・横断"], 2)
        XCTAssertEqual(counts["非発泡性ワイン"], 8)
        XCTAssertEqual(counts["発泡性ワイン"], 2)
        XCTAssertEqual(counts["酒精強化ワイン"], 1)
        XCTAssertEqual(
            StudyFocusCatalog.matchingQuestionIDs(
                for: .wineType,
                value: "非発泡性ワイン",
                in: items
            ),
            Set(["q0", "q1", "q2", "q8", "q9", "q10", "q11", "q12"])
        )
    }

    func testFocusMatchingIsExactAndDifficultyUsesLearningOrder() {
        let items = [
            StudyFocusItem(
                questionID: "france",
                geography: ["フランス"],
                grapeVarieties: [],
                wineType: nil,
                category: "分類",
                difficulty: "D2",
                cognitiveSkill: nil
            ),
            StudyFocusItem(
                questionID: "south-france",
                geography: ["南フランス"],
                grapeVarieties: [],
                wineType: nil,
                category: "分類",
                difficulty: "D2",
                cognitiveSkill: nil
            ),
            StudyFocusItem(
                questionID: "other",
                geography: [],
                grapeVarieties: [],
                wineType: nil,
                category: "別分類",
                difficulty: "D1",
                cognitiveSkill: nil
            ),
        ]

        XCTAssertTrue(StudyFocusCatalog.matches(items[0], dimension: .geography, value: "フランス"))
        XCTAssertFalse(StudyFocusCatalog.matches(items[1], dimension: .geography, value: "フランス"))
        XCTAssertEqual(
            StudyFocusCatalog.options(for: .difficulty, in: items),
            [
                StudyFocusOption(value: "D1", questionCount: 1),
                StudyFocusOption(value: "D2", questionCount: 2),
            ]
        )
    }

    func testMockExamSessionRoundTripsStoredResults() {
        let session = MockExamSession(
            correctCount: 42,
            questionCount: 50,
            outcomeResults: ["u1_lo5": MockOutcomeResult(correct: 8, total: 10)],
            missedQuestionIDs: ["q1", "q2"]
        )

        XCTAssertEqual(session.score, 0.84, accuracy: 0.0001)
        XCTAssertEqual(session.outcomeResults["u1_lo5"], MockOutcomeResult(correct: 8, total: 10))
        XCTAssertEqual(session.missedQuestionIDs, ["q1", "q2"])
    }

    func testHTMLOnlyFlashcardAnswerIsTreatedAsMissing() {
        let packed = PackedQuestion(
            id: "empty-answer",
            prompt: "Prompt",
            answer: "<br>\u{200B}",
            explanation: nil,
            choices: [],
            correctAnswerIndex: nil,
            studyMode: "flashcard",
            originalFormat: "identification",
            unit: "unit_1",
            learningOutcome: "u1_lo1",
            category: "Production factors",
            topic: "winemaking",
            cognitiveSkill: nil,
            commandVerb: nil,
            language: "en",
            geography: [],
            grapeVarieties: [],
            markAllocation: nil,
            sourceID: "test",
            sourceURL: "",
            qualityScore: nil,
            reviewStatus: "machine_screened"
        )
        let question = StudyQuestion(packed: packed)

        XCTAssertFalse(question.hasAnswer)
        XCTAssertFalse(question.displayAnswer.isEmpty)
    }

    func testJapaneseQuestionContentIsUsedEvenWithLegacyEnglishPreference() {
        let packed = PackedQuestion(
            id: "bilingual",
            prompt: "Original",
            answer: "Original answer",
            explanation: nil,
            choices: [],
            correctAnswerIndex: nil,
            studyMode: "flashcard",
            originalFormat: "identification",
            unit: "unit_1",
            learningOutcome: "u1_lo3",
            category: "Sparkling wines",
            topic: "sparkling_wines",
            cognitiveSkill: nil,
            commandVerb: nil,
            language: "en",
            geography: [],
            grapeVarieties: [],
            markAllocation: nil,
            sourceID: "test",
            sourceURL: "",
            qualityScore: nil,
            reviewStatus: "machine_screened",
            translations: [
                "en": PackedTranslationContent(
                    prompt: "How is Champagne made?",
                    answer: "By the traditional method.",
                    explanation: "A second fermentation takes place in bottle.",
                    choices: []
                ),
                "ja": PackedTranslationContent(
                    prompt: "シャンパーニュはどのように造られるか？",
                    answer: "トラディショナル方式で造られる。",
                    explanation: "瓶内で二次発酵を行う。",
                    choices: []
                ),
            ],
            translationStatus: "machine_translated",
            translationModel: "test"
        )
        let question = StudyQuestion(packed: packed)

        UserDefaults.standard.set("en", forKey: "questionLanguagePreference")
        XCTAssertEqual(question.displayPrompt, "シャンパーニュはどのように造られるか？")
        XCTAssertEqual(question.displayAnswer, "トラディショナル方式で造られる。")
        XCTAssertEqual(
            question.displayExplanation,
            "瓶内で二次発酵を行う。"
        )
        UserDefaults.standard.removeObject(forKey: "questionLanguagePreference")
    }

    func testChoiceExplanationsAndOriginalMetadataRoundTrip() {
        let packed = PackedQuestion(
            id: "LO1-001",
            prompt: "問題文",
            answer: "正答",
            explanation: "正答解説",
            choices: ["正答", "誤答1", "誤答2", "誤答3"],
            correctAnswerIndex: 0,
            studyMode: "multiple_choice",
            originalFormat: "original_mcq",
            unit: "unit_1",
            learningOutcome: "u1_lo1",
            category: "自然要因",
            topic: "気候と成熟",
            cognitiveSkill: "因果説明",
            commandVerb: nil,
            language: "ja",
            geography: ["日本", "山梨"],
            grapeVarieties: ["甲州"],
            markAllocation: nil,
            sourceID: "wset_level3_original_1100_v7",
            sourceURL: "",
            qualityScore: nil,
            reviewStatus: "未レビュー",
            choiceExplanations: ["正しい。", "誤り1。", "誤り2。", "誤り3。"],
            learningOutcomeName: "自然要因と人的要因",
            subcategory: "気候",
            wineType: "非発泡性ワイン",
            difficulty: "D2",
            misconceptionTags: ["冷涼気候=低収量"],
            needsReview: true,
            reviewReason: "要確認",
            creationType: "オリジナル",
            creationBasis: "自作"
        )

        let question = StudyQuestion(packed: packed)

        XCTAssertEqual(question.choiceExplanations.count, 4)
        XCTAssertEqual(question.choiceExplanations[1], "誤り1。")
        XCTAssertEqual(question.difficulty, "D2")
        XCTAssertEqual(question.geography, ["日本", "山梨"])
        XCTAssertEqual(question.misconceptionTags, ["冷涼気候=低収量"])
        XCTAssertTrue(question.needsReview)
    }

    func testQuestionPackMigrationResetsOnlyQuestionStudyHistory() throws {
        let configuration = ModelConfiguration(isStoredInMemoryOnly: true)
        let container = try ModelContainer(
            for: QuestionProgress.self,
            StudyAttempt.self,
            WrittenAnswerDraft.self,
            TastingNote.self,
            MockExamSession.self,
            configurations: configuration
        )
        let context = container.mainContext
        context.insert(QuestionProgress(questionID: "old-question"))
        context.insert(StudyAttempt(questionID: "old-question", isCorrect: true, rating: 3))
        context.insert(WrittenAnswerDraft(questionID: "old-question", responseText: "下書き"))
        context.insert(
            MockExamSession(
                correctCount: 1,
                questionCount: 1,
                outcomeResults: [:],
                missedQuestionIDs: ["old-question"]
            )
        )
        var draft = TastingDraft()
        draft.appearanceColour = "Ruby"
        context.insert(TastingNote(draft: draft))
        try context.save()

        try QuestionImporter.resetQuestionStudyHistory(in: context)

        XCTAssertEqual(try context.fetchCount(FetchDescriptor<QuestionProgress>()), 0)
        XCTAssertEqual(try context.fetchCount(FetchDescriptor<StudyAttempt>()), 0)
        XCTAssertEqual(try context.fetchCount(FetchDescriptor<WrittenAnswerDraft>()), 0)
        XCTAssertEqual(try context.fetchCount(FetchDescriptor<MockExamSession>()), 0)
        XCTAssertEqual(try context.fetchCount(FetchDescriptor<TastingNote>()), 1)
    }

    func testAdditiveQuestionPackMigrationPreservesStudyHistory() {
        XCTAssertFalse(
            QuestionImporter.shouldResetStudyHistory(
                existingQuestionIDs: ["LO1-001", "LO2-180"],
                newQuestionIDs: ["LO1-001", "LO2-180", "LO2-181"],
                hasImportedHash: true
            )
        )
        XCTAssertTrue(
            QuestionImporter.shouldResetStudyHistory(
                existingQuestionIDs: ["LO1-001", "removed-question"],
                newQuestionIDs: ["LO1-001", "LO2-181"],
                hasImportedHash: true
            )
        )
        XCTAssertFalse(
            QuestionImporter.shouldResetStudyHistory(
                existingQuestionIDs: ["LO1-001", "SAQ-PENDING"],
                newQuestionIDs: ["LO1-001"],
                hasImportedHash: true,
                ignoredContentIDs: ["SAQ-PENDING"]
            )
        )
    }

    func testDevelopmentOnlyWrittenPackIsRejectedOutsideDebugDistribution() throws {
        let data = Data(
            """
            {
              "schemaVersion": 1,
              "generatedAt": "2026-07-19T00:00:00Z",
              "sourceHash": "test",
              "questionCount": 0,
              "questions": [],
              "distributionStatus": "development_only",
              "referencePackSourceHash": "4ca34c3c662f1474f66e5b23c85db817b0a6671a6155b92aa5f237f9bb586235"
            }
            """.utf8
        )
        let pack = try JSONDecoder().decode(QuestionPack.self, from: data)
        XCTAssertEqual(
            pack.referencePackSourceHash,
            "4ca34c3c662f1474f66e5b23c85db817b0a6671a6155b92aa5f237f9bb586235"
        )

        XCTAssertTrue(
            QuestionImporter.shouldImport(pack, allowsDevelopmentContent: true)
        )
        XCTAssertFalse(
            QuestionImporter.shouldImport(pack, allowsDevelopmentContent: false)
        )
    }

    func testBundledQuestionPacksAreReleaseReadyAndContainAllQuestions() throws {
        let primaryURL = try XCTUnwrap(
            Bundle.main.url(forResource: "question_pack", withExtension: "json")
                ?? Bundle.main.url(
                    forResource: "question_pack",
                    withExtension: "json",
                    subdirectory: "QuestionData"
                )
        )
        let writtenURL = try XCTUnwrap(
            Bundle.main.url(forResource: "written_question_pack", withExtension: "json")
                ?? Bundle.main.url(
                    forResource: "written_question_pack",
                    withExtension: "json",
                    subdirectory: "QuestionData"
                )
        )
        let decoder = JSONDecoder()
        let primary = try decoder.decode(QuestionPack.self, from: Data(contentsOf: primaryURL))
        let written = try decoder.decode(QuestionPack.self, from: Data(contentsOf: writtenURL))

        XCTAssertEqual(primary.distributionStatus, "release")
        XCTAssertEqual(primary.questionCount, 1_100)
        XCTAssertEqual(written.distributionStatus, "release")
        XCTAssertEqual(written.questionCount, 10)
        XCTAssertTrue(QuestionImporter.shouldImport(primary, allowsDevelopmentContent: false))
        XCTAssertTrue(QuestionImporter.shouldImport(written, allowsDevelopmentContent: false))

        let (questions, _) = try QuestionImporter.validateAndCombine([primary, written])
        XCTAssertEqual(questions.count, 1_110)
    }

    func testBackupEncodingAndMergeRestore() throws {
        let configuration = ModelConfiguration(isStoredInMemoryOnly: true)
        let container = try ModelContainer(
            for: StudyQuestion.self,
            QuestionProgress.self,
            StudyAttempt.self,
            WrittenAnswerDraft.self,
            TastingNote.self,
            MockExamSession.self,
            TheoryExamSession.self,
            ReferenceTermProgress.self,
            configurations: configuration
        )
        let context = container.mainContext
        let progress = QuestionProgress(questionID: "q1")
        progress.record(isCorrect: true, rating: 3)
        context.insert(progress)
        context.insert(StudyAttempt(questionID: "q1", isCorrect: true, rating: 3))
        var draft = TastingDraft()
        draft.appearanceColour = "Ruby"
        context.insert(TastingNote(draft: draft))
        try context.save()

        let backup = try BackupService.makeBackup(in: context)
        let encoded = try StudyBackupDocument.encoder.encode(backup)
        let decoded = try StudyBackupDocument.decode(encoded)
        let result = try BackupService.restore(decoded, into: context)

        XCTAssertEqual(result.progressCount, 1)
        XCTAssertEqual(result.attemptCount, 1)
        XCTAssertEqual(result.tastingCount, 1)
        XCTAssertEqual(try context.fetchCount(FetchDescriptor<StudyAttempt>()), 1)
        XCTAssertEqual(try context.fetchCount(FetchDescriptor<TastingNote>()), 1)
    }

    func testReferencePackLoadsExpectedTermsAndClassifications() throws {
        let store = ReferenceStore.shared
        XCTAssertNil(store.loadError)
        XCTAssertEqual(store.terms.count, 680)
        XCTAssertEqual(store.classificationEntries.count, 279)
        XCTAssertEqual(store.classificationSystems.count, 6)

        let malolactic = try XCTUnwrap(
            store.terms.first { $0.nameJapanese == "マロラクティック発酵" }
        )
        XCTAssertEqual(malolactic.nameEnglish, "malolactic fermentation")
        XCTAssertEqual(malolactic.nameFrench, "fermentation malolactique")
        XCTAssertTrue(malolactic.matches("malolactique"))
        XCTAssertTrue(malolactic.matches("ＭＬＦ"))
        XCTAssertFalse(malolactic.questionIDs.isEmpty)
    }

    func testReferencePackPreservesRegionalClassificationCounts() {
        let entries = ReferenceStore.shared.classificationEntries
        let counts = Dictionary(grouping: entries, by: \.systemID).mapValues(\.count)

        XCTAssertEqual(counts["bordeaux_1855_medoc"], 61)
        XCTAssertEqual(counts["bordeaux_1855_sauternes"], 27)
        XCTAssertEqual(counts["bordeaux_graves"], 14)
        XCTAssertEqual(counts["bordeaux_saint_emilion_2022"], 85)
        XCTAssertEqual(counts["burgundy_grand_cru"], 33)
        XCTAssertEqual(counts["champagne_cru_2025"], 59)
    }

    func testReferenceTermProgressRecordsViewsAndBookmark() {
        let progress = ReferenceTermProgress(termID: "term-test")
        let viewedAt = Date(timeIntervalSince1970: 1_700_000_000)

        progress.recordView(at: viewedAt)
        progress.isBookmarked = true

        XCTAssertEqual(progress.lastViewedAt, viewedAt)
        XCTAssertEqual(progress.viewCount, 1)
        XCTAssertTrue(progress.isBookmarked)
    }

    func testStudyQuestionQueryClassifiesAndUsesInjectedCurrentTime() {
        let multipleChoice = makeQueryQuestion(
            id: "mcq",
            studyMode: "multiple_choice",
            learningOutcome: "u1_lo1",
            correctAnswerIndex: 0
        )
        let incompleteMultipleChoice = makeQueryQuestion(
            id: "mcq-incomplete",
            studyMode: "multiple_choice",
            learningOutcome: "u1_lo2",
            correctAnswerIndex: nil
        )
        let written = makeQueryQuestion(
            id: "written",
            studyMode: "written_answer",
            learningOutcome: "u1_lo2",
            correctAnswerIndex: nil,
            rubricItems: [
                WrittenRubricItem(
                    id: "written-r1",
                    criterion: "根拠を説明する",
                    marks: 2,
                    knowledgeTags: ["自然要因"],
                    relatedTermIDs: []
                ),
            ]
        )
        let incompleteWritten = makeQueryQuestion(
            id: "written-incomplete",
            studyMode: "written_answer",
            learningOutcome: "u1_lo3",
            correctAnswerIndex: nil
        )
        let questions = [
            multipleChoice,
            incompleteMultipleChoice,
            written,
            incompleteWritten,
        ]

        XCTAssertEqual(
            StudyQuestionQuery.multipleChoice(in: questions).map(\.id),
            ["mcq"]
        )
        XCTAssertEqual(
            StudyQuestionQuery.multipleChoice(
                in: questions,
                learningOutcome: "u1_lo2"
            ).map(\.id),
            []
        )
        XCTAssertEqual(
            StudyQuestionQuery.written(in: questions).map(\.id),
            ["written", "written-incomplete"]
        )
        XCTAssertEqual(
            StudyQuestionQuery.written(
                in: questions,
                requiringRubric: true
            ).map(\.id),
            ["written"]
        )
        XCTAssertEqual(
            StudyQuestionQuery.theoryCandidates(in: questions).map(\.id),
            ["mcq", "written"]
        )

        let manifest = FreeContentManifest(
            schemaVersion: 1,
            selectionVersion: "test",
            multipleChoiceQuestionIDs: ["mcq"],
            writtenQuestionIDs: ["written"],
            glossaryTermIDs: [],
            mapCountries: []
        )
        let freePolicy = FeatureAccessPolicy(
            hasProAccess: false,
            freeContentManifest: manifest
        )
        XCTAssertEqual(
            StudyQuestionQuery.accessible(questions, policy: freePolicy).map(\.id),
            ["mcq", "written"]
        )

        let now = Date(timeIntervalSince1970: 1_700_000_000)
        let progress = QuestionProgress(questionID: "mcq")
        progress.attemptCount = 1
        progress.lastWasCorrect = false
        progress.isBookmarked = true
        progress.dueDate = now
        let progressByID = [progress.questionID: progress]

        XCTAssertEqual(
            StudyQuestionQuery.mistakes(
                in: questions,
                progressByID: progressByID
            ).map(\.id),
            ["mcq"]
        )
        XCTAssertEqual(
            StudyQuestionQuery.bookmarked(
                in: questions,
                progressByID: progressByID
            ).map(\.id),
            ["mcq"]
        )
        XCTAssertEqual(
            StudyQuestionQuery.due(
                in: questions,
                progressByID: progressByID,
                now: now.addingTimeInterval(-1)
            ).map(\.id),
            []
        )
        XCTAssertEqual(
            StudyQuestionQuery.due(
                in: questions,
                progressByID: progressByID,
                now: now
            ).map(\.id),
            ["mcq"]
        )
    }

    private func makeQueryQuestion(
        id: String,
        studyMode: String,
        learningOutcome: String,
        correctAnswerIndex: Int?,
        rubricItems: [WrittenRubricItem] = []
    ) -> StudyQuestion {
        StudyQuestion(
            packed: PackedQuestion(
                id: id,
                prompt: "問題",
                answer: "解答",
                explanation: nil,
                choices: studyMode == "multiple_choice" ? ["正答", "誤答"] : [],
                correctAnswerIndex: correctAnswerIndex,
                studyMode: studyMode,
                originalFormat: studyMode,
                unit: "unit_1",
                learningOutcome: learningOutcome,
                category: "自然要因",
                topic: "気候",
                cognitiveSkill: "因果説明",
                commandVerb: studyMode == "written_answer" ? "説明する" : nil,
                language: "ja",
                geography: [],
                grapeVarieties: [],
                markAllocation: rubricItems.isEmpty
                    ? nil
                    : Double(rubricItems.reduce(0) { $0 + $1.marks }),
                sourceID: "query-test",
                sourceURL: "",
                qualityScore: 1,
                reviewStatus: "published",
                rubricItems: rubricItems
            )
        )
    }
}
