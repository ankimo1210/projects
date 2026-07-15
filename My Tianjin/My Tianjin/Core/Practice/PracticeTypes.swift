import Foundation

public enum PracticeHSKLevel: Int, Codable, CaseIterable, Comparable, Hashable, Sendable {
    case level1 = 1
    case level2 = 2
    case level3 = 3
    case level4 = 4
    case level5 = 5
    case level6 = 6
    case level7 = 7
    case level8 = 8
    case level9 = 9

    public static func < (lhs: PracticeHSKLevel, rhs: PracticeHSKLevel) -> Bool {
        lhs.rawValue < rhs.rawValue
    }
}

public enum PracticeSkill: String, Codable, CaseIterable, Hashable, Sendable {
    case vocabulary
    case listening
    case reading
    case grammar
    case wordOrder
    case writing
    case translation
    case speaking
    case pronunciation
    case characterWriting
}

public enum PracticeQuestionKind: String, Codable, CaseIterable, Hashable, Sendable {
    case vocabularyMultipleChoice
    case audioToMeaning
    case sentenceCloze
    case sentenceOrdering
    case readingComprehension
    case incorrectSentence
    case summary
    case essay
    case translation
    case oralOpinion
}

/// Chinese text together with optional learner aids. `speechText` can differ from
/// the displayed text when punctuation or annotations should not be pronounced.
public struct PracticeText: Codable, Hashable, Sendable {
    public var text: String
    public var pinyin: String?
    public var japanese: String?
    public var speechText: String?

    public init(
        text: String,
        pinyin: String? = nil,
        japanese: String? = nil,
        speechText: String? = nil
    ) {
        self.text = text
        self.pinyin = pinyin
        self.japanese = japanese
        self.speechText = speechText
    }
}

public struct PracticePrompt: Codable, Hashable, Sendable {
    public var instruction: String
    public var stimulus: PracticeText?

    public init(instruction: String, stimulus: PracticeText? = nil) {
        self.instruction = instruction
        self.stimulus = stimulus
    }
}

public struct PracticeQuestionMetadata: Codable, Hashable, Sendable {
    public var level: PracticeHSKLevel
    public var skills: [PracticeSkill]
    public var tags: [String]
    public var recommendedDurationSeconds: Int?

    public init(
        level: PracticeHSKLevel,
        skills: [PracticeSkill],
        tags: [String] = [],
        recommendedDurationSeconds: Int? = nil
    ) {
        self.level = level
        self.skills = skills
        self.tags = tags
        self.recommendedDurationSeconds = recommendedDurationSeconds
    }
}

public struct PracticeAnswerExplanation: Codable, Hashable, Sendable {
    public var summary: String
    public var details: String?
    public var relatedGrammarIDs: [String]

    public init(
        summary: String,
        details: String? = nil,
        relatedGrammarIDs: [String] = []
    ) {
        self.summary = summary
        self.details = details
        self.relatedGrammarIDs = relatedGrammarIDs
    }
}
