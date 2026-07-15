import XCTest
@testable import My_Tianjin

final class PracticeGraderTests: XCTestCase {
    func testChoiceGradingHandlesCorrectAndIncorrectResponses() {
        let answers = makeChoiceSet(correctOptionIDs: ["a"])

        let correct = PracticeGrader.gradeChoice(
            questionID: "choice-1",
            answers: answers,
            response: .choice(optionIDs: ["a"])
        )
        let incorrect = PracticeGrader.gradeChoice(
            questionID: "choice-1",
            answers: answers,
            response: .choice(optionIDs: ["b"])
        )

        XCTAssertEqual(correct.outcome, .correct)
        XCTAssertEqual(correct.earnedPoints, 1)
        XCTAssertEqual(incorrect.outcome, .incorrect)
        XCTAssertEqual(incorrect.earnedPoints, 0)
    }

    func testOrderingGradingAcceptsOnlyConfiguredCompleteOrders() {
        let ordering = PracticeOrderingQuestion(
            prompt: PracticePrompt(instruction: "文を並べ替えてください。"),
            tokens: [
                PracticeOrderingToken(id: "wo", content: PracticeText(text: "我")),
                PracticeOrderingToken(id: "ai", content: PracticeText(text: "爱")),
                PracticeOrderingToken(id: "ni", content: PracticeText(text: "你"))
            ],
            acceptedTokenOrders: [["wo", "ai", "ni"]]
        )

        let correct = PracticeGrader.gradeOrdering(
            questionID: "order-1",
            question: ordering,
            response: .ordering(tokenIDs: ["wo", "ai", "ni"])
        )
        let incorrect = PracticeGrader.gradeOrdering(
            questionID: "order-1",
            question: ordering,
            response: .ordering(tokenIDs: ["ni", "ai", "wo"])
        )

        XCTAssertEqual(correct.outcome, .correct)
        XCTAssertEqual(incorrect.outcome, .incorrect)
    }

    func testIncorrectSentenceQuestionUsesChoiceGrading() {
        let question = PracticeQuestion(
            id: "error-1",
            content: .incorrectSentence(
                PracticeIncorrectSentenceQuestion(
                    prompt: PracticePrompt(instruction: "誤りのある文を選んでください。"),
                    answers: makeChoiceSet(correctOptionIDs: ["b"])
                )
            ),
            metadata: PracticeQuestionMetadata(level: .level5, skills: [.grammar])
        )

        let result = PracticeGrader.grade(
            question: question,
            response: .choice(optionIDs: ["b"])
        )

        XCTAssertEqual(result.outcome, .correct)
        XCTAssertEqual(result.maximumPoints, 1)
    }

    func testFreeResponseRequiresRubricReviewAndRubricTotalsPoints() {
        let rubric = makeRubric()
        let freeResponse = PracticeFreeResponseQuestion(
            prompt: PracticePrompt(instruction: "意見を書いてください。"),
            responseMode: .written,
            rubric: rubric
        )
        let question = PracticeQuestion(
            id: "essay-1",
            content: .essay(freeResponse),
            metadata: PracticeQuestionMetadata(level: .level7, skills: [.writing])
        )
        let evaluation = PracticeRubricEvaluation(
            rubricID: rubric.id,
            criterionScores: [
                .init(criterionID: "content", points: 2),
                .init(criterionID: "language", points: 2)
            ]
        )

        let result = PracticeGrader.grade(
            question: question,
            response: .text("私はこの提案に賛成です。")
        )

        XCTAssertEqual(rubric.maximumPoints, 5)
        XCTAssertEqual(evaluation.earnedPoints, 4)
        XCTAssertEqual(result.outcome, .requiresRubricReview)
        XCTAssertNil(result.earnedPoints)
        XCTAssertEqual(result.maximumPoints, 5)
        XCTAssertEqual(
            result.details,
            .freeResponse(rubricID: rubric.id)
        )
    }

    func testBlankFreeResponseIsInvalid() {
        let result = PracticeGrader.gradeFreeResponse(
            questionID: "essay-blank",
            question: PracticeFreeResponseQuestion(
                prompt: PracticePrompt(instruction: "意見を書いてください。"),
                responseMode: .written,
                rubric: makeRubric()
            ),
            response: .text("   \n")
        )

        XCTAssertEqual(result.outcome, .invalid)
        XCTAssertEqual(result.details, .invalid(issue: .emptyResponse))
    }

    func testProgressMappingRecordsEveryDeclaredSkillAndUsesVocabularyID() {
        let question = PracticeQuestion(
            id: "audio-v1",
            content: .audioToMeaning(PracticeAudioChoiceQuestion(
                audio: PracticeText(text: "爱"),
                prompt: PracticePrompt(instruction: "意味を選んでください。"),
                answers: makeChoiceSet(correctOptionIDs: ["a"])
            )),
            metadata: PracticeQuestionMetadata(
                level: .level1,
                skills: [.listening, .vocabulary]
            )
        )

        XCTAssertEqual(
            Set(PracticeProgressMapping.descriptors(for: question)),
            Set([
                PracticeProgressDescriptor(itemID: "audio-v1", skill: .listening),
                PracticeProgressDescriptor(itemID: "a", skill: .vocabulary)
            ])
        )
    }

    private func makeChoiceSet(correctOptionIDs: [String]) -> PracticeChoiceSet {
        PracticeChoiceSet(
            options: [
                PracticeAnswerOption(id: "a", content: PracticeText(text: "第一")),
                PracticeAnswerOption(id: "b", content: PracticeText(text: "第二")),
                PracticeAnswerOption(id: "c", content: PracticeText(text: "第三"))
            ],
            correctOptionIDs: correctOptionIDs
        )
    }

    private func makeRubric() -> PracticeFreeResponseRubric {
        PracticeFreeResponseRubric(
            id: "essay-rubric",
            title: "作文評価",
            criteria: [
                .init(
                    id: "content",
                    title: "内容",
                    description: "問いに答えている。",
                    maximumPoints: 2,
                    performanceLevels: [
                        .init(points: 0, label: "不足", descriptor: "答えていない。"),
                        .init(points: 2, label: "達成", descriptor: "十分に答えている。")
                    ]
                ),
                .init(
                    id: "language",
                    title: "言語",
                    description: "適切な中国語を使っている。",
                    maximumPoints: 3,
                    performanceLevels: [
                        .init(points: 0, label: "不足", descriptor: "理解が難しい。"),
                        .init(points: 3, label: "達成", descriptor: "明確で自然である。")
                    ]
                )
            ],
            passingPoints: 3
        )
    }
}
