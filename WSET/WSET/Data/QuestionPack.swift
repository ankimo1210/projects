import Foundation

nonisolated struct WrittenRubricItem: Codable, Identifiable, Hashable {
    let id: String
    let criterion: String
    let marks: Int
    let knowledgeTags: [String]
    let relatedTermIDs: [String]
}

nonisolated struct WrittenContentMetadata: Codable, Hashable {
    let authoringMethod: String
    let externalReviewRequired: Bool
    let reviewNotes: String
}

struct QuestionPack: Decodable {
    let schemaVersion: Int
    let generatedAt: String
    let sourceHash: String
    let questionCount: Int
    let questions: [PackedQuestion]
    var distributionStatus: String? = nil
    var referencePackSourceHash: String? = nil
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
    var countries: [String]? = nil
    var regions: [String]? = nil
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
    var suggestedMinutes: Int? = nil
    var rubricItems: [WrittenRubricItem]? = nil
    var reviewer: String? = nil
    var reviewedAt: String? = nil
    var contentMetadata: WrittenContentMetadata? = nil
}

struct PackedTranslationContent: Codable {
    let prompt: String
    let answer: String?
    let explanation: String?
    let choices: [String]
}
