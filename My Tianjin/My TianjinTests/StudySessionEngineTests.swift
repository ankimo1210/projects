import Foundation
import XCTest
@testable import My_Tianjin

final class StudySessionEngineTests: XCTestCase {
    func testSameSeedProducesSameQuestionAndOptionOrder() throws {
        let configuration = makeConfiguration(mode: .shuffle, seed: 42)

        let first = try StudySessionEngine.makeSession(
            items: makeItems(),
            configuration: configuration,
            startedAt: referenceDate
        )
        let second = try StudySessionEngine.makeSession(
            items: makeItems(),
            configuration: configuration,
            startedAt: referenceDate
        )

        XCTAssertEqual(first.questions, second.questions)
    }

    func testDifferentSeedChangesFrozenSessionOrder() throws {
        let first = try StudySessionEngine.makeSession(
            items: makeItems(),
            configuration: makeConfiguration(mode: .shuffle, seed: 1),
            startedAt: referenceDate
        )
        let second = try StudySessionEngine.makeSession(
            items: makeItems(),
            configuration: makeConfiguration(mode: .shuffle, seed: 9_999),
            startedAt: referenceDate
        )

        XCTAssertNotEqual(first.questions, second.questions)
    }

    func testSessionHasNoRepeatedQuestionsOrOptions() throws {
        let state = try StudySessionEngine.makeSession(
            items: makeItems(),
            configuration: makeConfiguration(mode: .shuffle, seed: 123),
            startedAt: referenceDate
        )

        XCTAssertEqual(Set(state.questions.map(\.id)).count, state.questions.count)
        for question in state.questions {
            XCTAssertEqual(Set(question.optionIDs).count, question.optionIDs.count)
            XCTAssertTrue(question.optionIDs.contains(question.correctOptionID))
        }
    }

    func testBackPreservesPreviouslyRecordedAnswers() throws {
        var state = try StudySessionEngine.makeSession(
            items: makeItems(),
            configuration: makeConfiguration(mode: .sequential, seed: 7),
            startedAt: referenceDate
        )
        let firstQuestion = try XCTUnwrap(state.currentQuestion)
        try state.recordAnswer(optionID: firstQuestion.correctOptionID, at: referenceDate)
        XCTAssertEqual(try state.advance(at: referenceDate), .moved(toIndex: 1))

        let secondQuestion = try XCTUnwrap(state.currentQuestion)
        let wrongOption = try XCTUnwrap(
            secondQuestion.optionIDs.first { $0 != secondQuestion.correctOptionID }
        )
        try state.recordAnswer(optionID: wrongOption, at: referenceDate.addingTimeInterval(1))
        XCTAssertEqual(try state.advance(at: referenceDate.addingTimeInterval(1)), .moved(toIndex: 2))

        XCTAssertTrue(state.goBack(at: referenceDate.addingTimeInterval(2)))
        XCTAssertEqual(state.currentIndex, 1)
        XCTAssertEqual(state.currentQuestion?.selectedOptionID, wrongOption)
        XCTAssertEqual(state.answerHistory.count, 2)

        XCTAssertTrue(state.goBack(at: referenceDate.addingTimeInterval(3)))
        XCTAssertEqual(state.currentIndex, 0)
        XCTAssertEqual(state.currentQuestion?.selectedOptionID, firstQuestion.correctOptionID)
    }

    func testEncodingAndRestorePreserveExactSessionSnapshot() throws {
        var state = try StudySessionEngine.makeSession(
            items: makeItems(),
            configuration: makeConfiguration(mode: .shuffle, seed: 88),
            startedAt: referenceDate
        )
        let question = try XCTUnwrap(state.currentQuestion)
        try state.recordAnswer(
            optionID: question.correctOptionID,
            at: referenceDate.addingTimeInterval(10)
        )
        _ = try state.advance(at: referenceDate.addingTimeInterval(11))

        let restored = try StudySessionState.restore(from: state.encoded())

        XCTAssertEqual(restored, state)
        XCTAssertEqual(restored.currentQuestion?.optionIDs, state.currentQuestion?.optionIDs)
        XCTAssertEqual(restored.answerHistory, state.answerHistory)
    }

    func testDueReviewIncludesOnlyDueItemsAndSortsOldestFirst() throws {
        let items = makeItems()
        let progress = [
            items[0].id: StudyItemProgress(
                itemID: items[0].id,
                nextReviewAt: referenceDate.addingTimeInterval(-60)
            ),
            items[1].id: StudyItemProgress(
                itemID: items[1].id,
                nextReviewAt: referenceDate.addingTimeInterval(-120)
            ),
            items[2].id: StudyItemProgress(
                itemID: items[2].id,
                nextReviewAt: referenceDate.addingTimeInterval(60)
            )
        ]
        let configuration = StudySessionConfiguration(
            mode: .dueReview,
            seed: 1,
            optionCount: 4,
            includeUnseenInDueReview: false
        )

        let state = try StudySessionEngine.makeSession(
            items: items,
            progressByItemID: progress,
            configuration: configuration,
            startedAt: referenceDate
        )

        XCTAssertEqual(state.questions.map(\.id), [items[1].id, items[0].id])
    }

    func testWeakModeFiltersAndOrdersByWeakness() throws {
        let items = makeItems()
        let progress = [
            items[0].id: StudyItemProgress(
                itemID: items[0].id,
                attemptCount: 4,
                correctCount: 1,
                incorrectCount: 3
            ),
            items[1].id: StudyItemProgress(
                itemID: items[1].id,
                attemptCount: 4,
                correctCount: 3,
                incorrectCount: 1
            ),
            items[2].id: StudyItemProgress(
                itemID: items[2].id,
                attemptCount: 1,
                incorrectCount: 1
            )
        ]
        let configuration = StudySessionConfiguration(
            mode: .weak,
            seed: 1,
            optionCount: 4,
            minimumAttemptsForWeakMode: 2
        )

        let state = try StudySessionEngine.makeSession(
            items: items,
            progressByItemID: progress,
            configuration: configuration,
            startedAt: referenceDate
        )

        XCTAssertEqual(state.questions.map(\.id), [items[0].id, items[1].id])
    }

    private let referenceDate = Date(timeIntervalSince1970: 1_700_000_000)

    private func makeConfiguration(mode: StudySessionMode, seed: UInt64) -> StudySessionConfiguration {
        StudySessionConfiguration(mode: mode, seed: seed, optionCount: 4)
    }

    private func makeItems() -> [StudySessionItem] {
        let answerIDs = (0..<8).map { "answer-\($0)" }
        return answerIDs.enumerated().map { index, answerID in
            StudySessionItem(
                id: "item-\(index)",
                correctOptionID: answerID,
                distractorOptionIDs: answerIDs.filter { $0 != answerID }
            )
        }
    }
}
