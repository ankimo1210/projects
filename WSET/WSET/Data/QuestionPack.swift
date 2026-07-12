import Foundation

struct QuestionPack: Decodable {
    let schemaVersion: Int
    let generatedAt: String
    let sourceHash: String
    let questionCount: Int
    let questions: [PackedQuestion]
}

struct PackedQuestion: Decodable {
    let id: String
    let prompt: String
    let answer: String?
    let explanation: String?
    let choices: [String]
    let correctAnswerIndex: Int?
    let studyMode: String
    let originalFormat: String
    let unit: String
    let learningOutcome: String
    let category: String
    let topic: String
    let cognitiveSkill: String?
    let commandVerb: String?
    let language: String
    let geography: [String]
    let grapeVarieties: [String]
    let markAllocation: Double?
    let sourceID: String
    let sourceURL: String
    let qualityScore: Double?
    let reviewStatus: String
    var choiceExplanations: [String]? = nil
    var learningOutcomeName: String? = nil
    var subcategory: String? = nil
    var wineType: String? = nil
    var difficulty: String? = nil
    var misconceptionTags: [String]? = nil
    var needsReview: Bool? = nil
    var reviewReason: String? = nil
    var creationType: String? = nil
    var creationBasis: String? = nil
    var translations: [String: PackedTranslationContent]? = nil
    var translationStatus: String? = nil
    var translationModel: String? = nil
}

struct PackedTranslationContent: Codable {
    let prompt: String
    let answer: String?
    let explanation: String?
    let choices: [String]
}
