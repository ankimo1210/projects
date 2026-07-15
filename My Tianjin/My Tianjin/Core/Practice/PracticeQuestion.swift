import Foundation

public struct PracticeAnswerOption: Identifiable, Codable, Hashable, Sendable {
    public var id: String
    public var content: PracticeText

    public init(id: String, content: PracticeText) {
        self.id = id
        self.content = content
    }
}

public enum PracticeSelectionMode: String, Codable, CaseIterable, Hashable, Sendable {
    case single
    case multiple
}

public struct PracticeChoiceSet: Codable, Hashable, Sendable {
    public var options: [PracticeAnswerOption]
    public var correctOptionIDs: [String]
    public var mode: PracticeSelectionMode

    public init(
        options: [PracticeAnswerOption],
        correctOptionIDs: [String],
        mode: PracticeSelectionMode = .single
    ) {
        self.options = options
        self.correctOptionIDs = correctOptionIDs
        self.mode = mode
    }
}

public struct PracticeVocabularyChoiceQuestion: Codable, Hashable, Sendable {
    public var vocabularyID: String
    public var prompt: PracticePrompt
    public var answers: PracticeChoiceSet

    public init(vocabularyID: String, prompt: PracticePrompt, answers: PracticeChoiceSet) {
        self.vocabularyID = vocabularyID
        self.prompt = prompt
        self.answers = answers
    }
}

public struct PracticeAudioChoiceQuestion: Codable, Hashable, Sendable {
    public var audio: PracticeText
    public var prompt: PracticePrompt
    public var answers: PracticeChoiceSet

    public init(audio: PracticeText, prompt: PracticePrompt, answers: PracticeChoiceSet) {
        self.audio = audio
        self.prompt = prompt
        self.answers = answers
    }
}

public struct PracticeClozeQuestion: Codable, Hashable, Sendable {
    public var prompt: PracticePrompt
    public var sentence: PracticeText
    public var placeholder: String
    public var answers: PracticeChoiceSet

    public init(
        prompt: PracticePrompt,
        sentence: PracticeText,
        placeholder: String = "{{blank}}",
        answers: PracticeChoiceSet
    ) {
        self.prompt = prompt
        self.sentence = sentence
        self.placeholder = placeholder
        self.answers = answers
    }
}

public struct PracticeOrderingToken: Identifiable, Codable, Hashable, Sendable {
    public var id: String
    public var content: PracticeText

    public init(id: String, content: PracticeText) {
        self.id = id
        self.content = content
    }
}

public struct PracticeOrderingQuestion: Codable, Hashable, Sendable {
    public var prompt: PracticePrompt
    public var tokens: [PracticeOrderingToken]
    /// Every inner array is a valid complete ordering of token IDs.
    public var acceptedTokenOrders: [[String]]

    public init(
        prompt: PracticePrompt,
        tokens: [PracticeOrderingToken],
        acceptedTokenOrders: [[String]]
    ) {
        self.prompt = prompt
        self.tokens = tokens
        self.acceptedTokenOrders = acceptedTokenOrders
    }
}

public struct PracticeReadingQuestion: Codable, Hashable, Sendable {
    public var passageID: String
    public var prompt: PracticePrompt
    public var answers: PracticeChoiceSet

    public init(passageID: String, prompt: PracticePrompt, answers: PracticeChoiceSet) {
        self.passageID = passageID
        self.prompt = prompt
        self.answers = answers
    }
}

public struct PracticeIncorrectSentenceQuestion: Codable, Hashable, Sendable {
    public var prompt: PracticePrompt
    /// The options are candidate sentences; the correct IDs identify the
    /// grammatically or contextually incorrect sentence(s).
    public var answers: PracticeChoiceSet
    /// Natural corrected sentences accepted after the learner identifies the error.
    public var acceptedCorrections: [String]

    public init(
        prompt: PracticePrompt,
        answers: PracticeChoiceSet,
        acceptedCorrections: [String] = []
    ) {
        self.prompt = prompt
        self.answers = answers
        self.acceptedCorrections = acceptedCorrections
    }
}

public struct PracticeResponseConstraints: Codable, Hashable, Sendable {
    public var minimumCharacters: Int?
    public var maximumCharacters: Int?
    public var minimumDurationSeconds: Int?
    public var maximumDurationSeconds: Int?

    public init(
        minimumCharacters: Int? = nil,
        maximumCharacters: Int? = nil,
        minimumDurationSeconds: Int? = nil,
        maximumDurationSeconds: Int? = nil
    ) {
        self.minimumCharacters = minimumCharacters
        self.maximumCharacters = maximumCharacters
        self.minimumDurationSeconds = minimumDurationSeconds
        self.maximumDurationSeconds = maximumDurationSeconds
    }
}

public struct PracticeFreeResponseQuestion: Codable, Hashable, Sendable {
    public var prompt: PracticePrompt
    public var passageID: String?
    public var responseMode: PracticeFreeResponseMode
    public var constraints: PracticeResponseConstraints
    public var rubric: PracticeFreeResponseRubric
    public var referenceAnswer: PracticeText?

    public init(
        prompt: PracticePrompt,
        passageID: String? = nil,
        responseMode: PracticeFreeResponseMode,
        constraints: PracticeResponseConstraints = PracticeResponseConstraints(),
        rubric: PracticeFreeResponseRubric,
        referenceAnswer: PracticeText? = nil
    ) {
        self.prompt = prompt
        self.passageID = passageID
        self.responseMode = responseMode
        self.constraints = constraints
        self.rubric = rubric
        self.referenceAnswer = referenceAnswer
    }
}

public enum PracticeTranslationDirection: String, Codable, CaseIterable, Hashable, Sendable {
    case intoChinese
    case fromChinese
}

public struct PracticeTranslationQuestion: Codable, Hashable, Sendable {
    public var direction: PracticeTranslationDirection
    public var response: PracticeFreeResponseQuestion

    public init(
        direction: PracticeTranslationDirection,
        response: PracticeFreeResponseQuestion
    ) {
        self.direction = direction
        self.response = response
    }
}

public enum PracticeQuestionContent: Codable, Hashable, Sendable {
    case vocabularyMultipleChoice(PracticeVocabularyChoiceQuestion)
    case audioToMeaning(PracticeAudioChoiceQuestion)
    case sentenceCloze(PracticeClozeQuestion)
    case sentenceOrdering(PracticeOrderingQuestion)
    case readingComprehension(PracticeReadingQuestion)
    case incorrectSentence(PracticeIncorrectSentenceQuestion)
    case summary(PracticeFreeResponseQuestion)
    case essay(PracticeFreeResponseQuestion)
    case translation(PracticeTranslationQuestion)
    case oralOpinion(PracticeFreeResponseQuestion)

    public var kind: PracticeQuestionKind {
        switch self {
        case .vocabularyMultipleChoice:
            return .vocabularyMultipleChoice
        case .audioToMeaning:
            return .audioToMeaning
        case .sentenceCloze:
            return .sentenceCloze
        case .sentenceOrdering:
            return .sentenceOrdering
        case .readingComprehension:
            return .readingComprehension
        case .incorrectSentence:
            return .incorrectSentence
        case .summary:
            return .summary
        case .essay:
            return .essay
        case .translation:
            return .translation
        case .oralOpinion:
            return .oralOpinion
        }
    }
}

public struct PracticeQuestion: Identifiable, Codable, Hashable, Sendable {
    public var id: String
    public var content: PracticeQuestionContent
    public var metadata: PracticeQuestionMetadata
    public var explanation: PracticeAnswerExplanation?

    public init(
        id: String,
        content: PracticeQuestionContent,
        metadata: PracticeQuestionMetadata,
        explanation: PracticeAnswerExplanation? = nil
    ) {
        self.id = id
        self.content = content
        self.metadata = metadata
        self.explanation = explanation
    }

    public var kind: PracticeQuestionKind {
        content.kind
    }
}
