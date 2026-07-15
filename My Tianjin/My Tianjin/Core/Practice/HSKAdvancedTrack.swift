import Foundation

public enum HSKAdvancedTrackDomain: String, Codable, CaseIterable, Hashable, Sendable {
    case listening
    case reading
    case writing
    case translation
    case speaking
}

public enum HSKAdvancedLevel: Int, Codable, CaseIterable, Comparable, Hashable, Sendable {
    case level7 = 7
    case level8 = 8
    case level9 = 9

    public static func < (lhs: HSKAdvancedLevel, rhs: HSKAdvancedLevel) -> Bool {
        lhs.rawValue < rhs.rawValue
    }

    public var practiceLevel: PracticeHSKLevel {
        switch self {
        case .level7:
            return .level7
        case .level8:
            return .level8
        case .level9:
            return .level9
        }
    }
}

/// HSK 7-9 activities are modeled as a separate track because they include
/// academic reading, extended production, translation, and spoken tasks rather
/// than only larger vocabulary decks.
public enum HSKAdvancedTaskKind: String, Codable, CaseIterable, Hashable, Sendable {
    case extendedListeningComprehension
    case extendedReadingComprehension
    case chartDescription
    case argumentativeWriting
    case writtenTranslationIntoChinese
    case writtenTranslationFromChinese
    case oralTranslationIntoChinese
    case oralTranslationFromChinese
    case oralParaphrase
    case oralOpinion

    public var domain: HSKAdvancedTrackDomain {
        switch self {
        case .extendedListeningComprehension:
            return .listening
        case .extendedReadingComprehension:
            return .reading
        case .chartDescription, .argumentativeWriting:
            return .writing
        case .writtenTranslationIntoChinese,
             .writtenTranslationFromChinese,
             .oralTranslationIntoChinese,
             .oralTranslationFromChinese:
            return .translation
        case .oralParaphrase, .oralOpinion:
            return .speaking
        }
    }

    public var responseMode: PracticeFreeResponseMode? {
        switch self {
        case .extendedListeningComprehension, .extendedReadingComprehension:
            return nil
        case .chartDescription,
             .argumentativeWriting,
             .writtenTranslationIntoChinese,
             .writtenTranslationFromChinese:
            return .written
        case .oralTranslationIntoChinese,
             .oralTranslationFromChinese,
             .oralParaphrase,
             .oralOpinion:
            return .spoken
        }
    }
}

public struct HSKAdvancedTrackTask: Identifiable, Codable, Hashable, Sendable {
    public var id: String
    public var kind: HSKAdvancedTaskKind
    public var supportedLevels: [HSKAdvancedLevel]
    public var title: String
    public var instructions: String
    public var questionIDs: [String]
    public var recommendedDurationSeconds: Int?

    public init(
        id: String,
        kind: HSKAdvancedTaskKind,
        supportedLevels: [HSKAdvancedLevel] = [.level7, .level8, .level9],
        title: String,
        instructions: String,
        questionIDs: [String],
        recommendedDurationSeconds: Int? = nil
    ) {
        self.id = id
        self.kind = kind
        self.supportedLevels = supportedLevels
        self.title = title
        self.instructions = instructions
        self.questionIDs = questionIDs
        self.recommendedDurationSeconds = recommendedDurationSeconds
    }
}
