import XCTest
@testable import My_Tianjin

final class PracticeSeedContentTests: XCTestCase {
    func testSeedCountsAndIdentifiers() throws {
        XCTAssertEqual(PracticeSeedContent.orderingQuestions.count, 30)
        XCTAssertEqual(PracticeSeedContent.beginnerReadingSeeds.count, 20)
        XCTAssertEqual(PracticeSeedContent.readingQuestions.count, 40)
        XCTAssertEqual(PracticeSeedContent.upperIntermediateQuestions.count, 6)
        XCTAssertEqual(PracticeSeedContent.advancedQuestions.count, 10)
        XCTAssertEqual(PracticeSeedContent.advancedTasks.count, 10)

        let allQuestions = PracticeSeedContent.orderingQuestions
            + PracticeSeedContent.readingQuestions
            + PracticeSeedContent.upperIntermediateQuestions
            + PracticeSeedContent.advancedQuestions
        XCTAssertEqual(Set(allQuestions.map(\.id)).count, allQuestions.count)
    }

    func testReadingSeedsHavePassagesQuestionsAndAnnotations() {
        for seed in PracticeSeedContent.beginnerReadingSeeds {
            XCTAssertTrue((2...4).contains(seed.passage.segments.count), seed.id)
            XCTAssertTrue((1...3).contains(seed.questions.count), seed.id)
            XCTAssertFalse(seed.vocabularyAnnotations.isEmpty, seed.id)
            XCTAssertTrue(seed.questions.allSatisfy { question in
                guard case let .readingComprehension(payload) = question.content else { return false }
                return payload.passageID == seed.passage.id
            })
        }
    }

    func testEveryAdvancedTaskKindAndQuestionReferenceIsCovered() {
        XCTAssertEqual(
            Set(PracticeSeedContent.advancedTasks.map(\.kind)),
            Set(HSKAdvancedTaskKind.allCases)
        )
        let questionIDs = Set(PracticeSeedContent.advancedQuestions.map(\.id))
        for task in PracticeSeedContent.advancedTasks {
            XCTAssertFalse(task.questionIDs.isEmpty, task.id)
            XCTAssertTrue(task.questionIDs.allSatisfy(questionIDs.contains), task.id)
        }
    }

    func testIncorrectSentenceTaskRequiresAProducedCorrection() throws {
        let question = try XCTUnwrap(
            PracticeSeedContent.upperIntermediateQuestions.first {
                $0.kind == .incorrectSentence
            }
        )
        guard case let .incorrectSentence(payload) = question.content else {
            return XCTFail("Expected an incorrect-sentence question")
        }
        XCTAssertGreaterThanOrEqual(payload.acceptedCorrections.count, 2)
        XCTAssertTrue(payload.acceptedCorrections.allSatisfy { !$0.isEmpty })
    }

    func testSeedContentRoundTripsThroughCodable() throws {
        let questions = PracticeSeedContent.orderingQuestions
            + PracticeSeedContent.readingQuestions
            + PracticeSeedContent.upperIntermediateQuestions
            + PracticeSeedContent.advancedQuestions
        let data = try JSONEncoder().encode(questions)
        XCTAssertEqual(try JSONDecoder().decode([PracticeQuestion].self, from: data), questions)

        let passages = PracticeSeedContent.allPassages
        let passageData = try JSONEncoder().encode(passages)
        XCTAssertEqual(try JSONDecoder().decode([PracticePassage].self, from: passageData), passages)
    }
}
