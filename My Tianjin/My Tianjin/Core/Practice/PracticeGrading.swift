import Foundation

public enum PracticeResponse: Codable, Hashable, Sendable {
    case choice(optionIDs: [String])
    case ordering(tokenIDs: [String])
    case text(String)
    case spoken(transcript: String?, recordingAssetID: String?)
}

public enum PracticeGradingOutcome: String, Codable, CaseIterable, Hashable, Sendable {
    case correct
    case incorrect
    case requiresRubricReview
    case invalid
}

public enum PracticeGradingIssue: Codable, Hashable, Sendable {
    case responseTypeMismatch(expected: String)
    case emptyResponse
    case invalidQuestionData(reason: String)
    case duplicateIdentifiers([String])
    case unknownIdentifiers([String])
    case incompleteSelection
    case incompleteOrdering
}

public enum PracticeGradingDetails: Codable, Hashable, Sendable {
    case selection(submittedOptionIDs: [String], expectedOptionIDs: [String])
    case ordering(submittedTokenIDs: [String], matchedAcceptedOrderIndex: Int?)
    case freeResponse(rubricID: String)
    case invalid(issue: PracticeGradingIssue)
}

public struct PracticeGradingResult: Codable, Hashable, Sendable {
    public var questionID: String
    public var outcome: PracticeGradingOutcome
    /// Deterministic questions produce 0 or `maximumPoints`. Free responses
    /// leave this nil until a rubric evaluation is attached.
    public var earnedPoints: Int?
    public var maximumPoints: Int
    public var details: PracticeGradingDetails

    public init(
        questionID: String,
        outcome: PracticeGradingOutcome,
        earnedPoints: Int?,
        maximumPoints: Int,
        details: PracticeGradingDetails
    ) {
        self.questionID = questionID
        self.outcome = outcome
        self.earnedPoints = earnedPoints
        self.maximumPoints = maximumPoints
        self.details = details
    }
}

/// Pure, deterministic grading. It never reads the clock, random state, storage,
/// locale, or network, so the same question and response always yield the same result.
public enum PracticeGrader {
    public static func grade(
        question: PracticeQuestion,
        response: PracticeResponse
    ) -> PracticeGradingResult {
        switch question.content {
        case let .vocabularyMultipleChoice(payload):
            return gradeChoice(questionID: question.id, answers: payload.answers, response: response)
        case let .audioToMeaning(payload):
            return gradeChoice(questionID: question.id, answers: payload.answers, response: response)
        case let .sentenceCloze(payload):
            return gradeChoice(questionID: question.id, answers: payload.answers, response: response)
        case let .sentenceOrdering(payload):
            return gradeOrdering(questionID: question.id, question: payload, response: response)
        case let .readingComprehension(payload):
            return gradeChoice(questionID: question.id, answers: payload.answers, response: response)
        case let .incorrectSentence(payload):
            return gradeChoice(questionID: question.id, answers: payload.answers, response: response)
        case let .summary(payload), let .essay(payload), let .oralOpinion(payload):
            return gradeFreeResponse(questionID: question.id, question: payload, response: response)
        case let .translation(payload):
            return gradeFreeResponse(questionID: question.id, question: payload.response, response: response)
        }
    }

    public static func gradeChoice(
        questionID: String,
        answers: PracticeChoiceSet,
        response: PracticeResponse
    ) -> PracticeGradingResult {
        guard case let .choice(selectedIDs) = response else {
            return invalid(questionID: questionID, issue: .responseTypeMismatch(expected: "choice"))
        }

        let optionIDs = answers.options.map(\.id)
        if let duplicateIDs = duplicates(in: optionIDs), !duplicateIDs.isEmpty {
            return invalid(questionID: questionID, issue: .invalidQuestionData(
                reason: "Duplicate option IDs: \(duplicateIDs.joined(separator: ", "))"
            ))
        }
        if answers.correctOptionIDs.isEmpty {
            return invalid(questionID: questionID, issue: .invalidQuestionData(
                reason: "At least one correct option is required."
            ))
        }
        if let duplicateCorrectIDs = duplicates(in: answers.correctOptionIDs), !duplicateCorrectIDs.isEmpty {
            return invalid(questionID: questionID, issue: .invalidQuestionData(
                reason: "Duplicate correct option IDs: \(duplicateCorrectIDs.joined(separator: ", "))"
            ))
        }

        let available = Set(optionIDs)
        let unknownCorrectIDs = Set(answers.correctOptionIDs).subtracting(available).sorted()
        if !unknownCorrectIDs.isEmpty {
            return invalid(questionID: questionID, issue: .invalidQuestionData(
                reason: "Unknown correct option IDs: \(unknownCorrectIDs.joined(separator: ", "))"
            ))
        }
        if answers.mode == .single, answers.correctOptionIDs.count != 1 {
            return invalid(questionID: questionID, issue: .invalidQuestionData(
                reason: "Single-selection questions require exactly one correct option."
            ))
        }
        if selectedIDs.isEmpty {
            return invalid(questionID: questionID, issue: .incompleteSelection)
        }
        if let duplicateSelectedIDs = duplicates(in: selectedIDs), !duplicateSelectedIDs.isEmpty {
            return invalid(questionID: questionID, issue: .duplicateIdentifiers(duplicateSelectedIDs))
        }
        let unknownSelectedIDs = Set(selectedIDs).subtracting(available).sorted()
        if !unknownSelectedIDs.isEmpty {
            return invalid(questionID: questionID, issue: .unknownIdentifiers(unknownSelectedIDs))
        }
        if answers.mode == .single, selectedIDs.count != 1 {
            return invalid(questionID: questionID, issue: .incompleteSelection)
        }

        let isCorrect = Set(selectedIDs) == Set(answers.correctOptionIDs)
        return PracticeGradingResult(
            questionID: questionID,
            outcome: isCorrect ? .correct : .incorrect,
            earnedPoints: isCorrect ? 1 : 0,
            maximumPoints: 1,
            details: .selection(
                submittedOptionIDs: selectedIDs,
                expectedOptionIDs: answers.correctOptionIDs
            )
        )
    }

    public static func gradeOrdering(
        questionID: String,
        question: PracticeOrderingQuestion,
        response: PracticeResponse
    ) -> PracticeGradingResult {
        guard case let .ordering(submittedIDs) = response else {
            return invalid(questionID: questionID, issue: .responseTypeMismatch(expected: "ordering"))
        }

        let tokenIDs = question.tokens.map(\.id)
        if tokenIDs.isEmpty {
            return invalid(questionID: questionID, issue: .invalidQuestionData(
                reason: "At least one ordering token is required."
            ))
        }
        if let duplicateTokenIDs = duplicates(in: tokenIDs), !duplicateTokenIDs.isEmpty {
            return invalid(questionID: questionID, issue: .invalidQuestionData(
                reason: "Duplicate token IDs: \(duplicateTokenIDs.joined(separator: ", "))"
            ))
        }
        if question.acceptedTokenOrders.isEmpty {
            return invalid(questionID: questionID, issue: .invalidQuestionData(
                reason: "At least one accepted token order is required."
            ))
        }

        let expectedTokenSet = Set(tokenIDs)
        for order in question.acceptedTokenOrders {
            guard order.count == tokenIDs.count,
                  Set(order) == expectedTokenSet,
                  duplicates(in: order)?.isEmpty != false else {
                return invalid(questionID: questionID, issue: .invalidQuestionData(
                    reason: "Every accepted order must use each token exactly once."
                ))
            }
        }

        if submittedIDs.count != tokenIDs.count {
            return invalid(questionID: questionID, issue: .incompleteOrdering)
        }
        if let duplicateSubmittedIDs = duplicates(in: submittedIDs), !duplicateSubmittedIDs.isEmpty {
            return invalid(questionID: questionID, issue: .duplicateIdentifiers(duplicateSubmittedIDs))
        }
        let unknownSubmittedIDs = Set(submittedIDs).subtracting(expectedTokenSet).sorted()
        if !unknownSubmittedIDs.isEmpty {
            return invalid(questionID: questionID, issue: .unknownIdentifiers(unknownSubmittedIDs))
        }
        if Set(submittedIDs) != expectedTokenSet {
            return invalid(questionID: questionID, issue: .incompleteOrdering)
        }

        let matchedIndex = question.acceptedTokenOrders.firstIndex(of: submittedIDs)
        return PracticeGradingResult(
            questionID: questionID,
            outcome: matchedIndex == nil ? .incorrect : .correct,
            earnedPoints: matchedIndex == nil ? 0 : 1,
            maximumPoints: 1,
            details: .ordering(
                submittedTokenIDs: submittedIDs,
                matchedAcceptedOrderIndex: matchedIndex
            )
        )
    }

    public static func gradeFreeResponse(
        questionID: String,
        question: PracticeFreeResponseQuestion,
        response: PracticeResponse
    ) -> PracticeGradingResult {
        switch (question.responseMode, response) {
        case let (.written, .text(text)):
            guard !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
                return invalid(questionID: questionID, issue: .emptyResponse)
            }
        case let (.spoken, .spoken(transcript, recordingAssetID)):
            let hasTranscript = !(transcript?.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ?? true)
            let hasRecording = !(recordingAssetID?.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ?? true)
            guard hasTranscript || hasRecording else {
                return invalid(questionID: questionID, issue: .emptyResponse)
            }
        case (.written, _):
            return invalid(questionID: questionID, issue: .responseTypeMismatch(expected: "text"))
        case (.spoken, _):
            return invalid(questionID: questionID, issue: .responseTypeMismatch(expected: "spoken"))
        }

        return PracticeGradingResult(
            questionID: questionID,
            outcome: .requiresRubricReview,
            earnedPoints: nil,
            maximumPoints: question.rubric.maximumPoints,
            details: .freeResponse(rubricID: question.rubric.id)
        )
    }

    private static func invalid(
        questionID: String,
        issue: PracticeGradingIssue
    ) -> PracticeGradingResult {
        PracticeGradingResult(
            questionID: questionID,
            outcome: .invalid,
            earnedPoints: nil,
            maximumPoints: 1,
            details: .invalid(issue: issue)
        )
    }

    /// Returns sorted duplicate values, or nil when the input is empty.
    private static func duplicates(in values: [String]) -> [String]? {
        guard !values.isEmpty else { return nil }
        var seen = Set<String>()
        var duplicates = Set<String>()
        for value in values where !seen.insert(value).inserted {
            duplicates.insert(value)
        }
        return duplicates.sorted()
    }
}
