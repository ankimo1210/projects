import Foundation
import SwiftData

@Model
final class StudyQuestion {
    @Attribute(.unique) var id: String
    var prompt: String
    var answer: String?
    var explanation: String?
    var choicesData: Data
    var correctAnswerIndex: Int?
    var studyMode: String
    var originalFormat: String
    var unit: String
    var learningOutcome: String
    var category: String
    var topic: String
    var cognitiveSkill: String?
    var commandVerb: String?
    var language: String
    var geographyData: Data
    var grapeVarietiesData: Data
    var markAllocation: Double?
    var sourceID: String
    var sourceURL: String
    var qualityScore: Double?
    var reviewStatus: String
    var choiceExplanationsData: Data? = nil
    var learningOutcomeName: String? = nil
    var subcategory: String? = nil
    var wineType: String? = nil
    var difficulty: String? = nil
    var misconceptionTagsData: Data? = nil
    var needsReview: Bool = false
    var reviewReason: String? = nil
    var creationType: String? = nil
    var creationBasis: String? = nil
    var promptEnglish: String?
    var promptJapanese: String?
    var answerEnglish: String?
    var answerJapanese: String?
    var explanationEnglish: String?
    var explanationJapanese: String?
    var choicesEnglishData: Data?
    var choicesJapaneseData: Data?
    var translationStatus: String?
    var translationModel: String?

    init(packed: PackedQuestion) {
        id = packed.id
        prompt = packed.prompt
        answer = packed.answer
        explanation = packed.explanation
        choicesData = Self.encode(packed.choices)
        correctAnswerIndex = packed.correctAnswerIndex
        studyMode = packed.studyMode
        originalFormat = packed.originalFormat
        unit = packed.unit
        learningOutcome = packed.learningOutcome
        category = packed.category
        topic = packed.topic
        cognitiveSkill = packed.cognitiveSkill
        commandVerb = packed.commandVerb
        language = packed.language
        geographyData = Self.encode(packed.geography)
        grapeVarietiesData = Self.encode(packed.grapeVarieties)
        markAllocation = packed.markAllocation
        sourceID = packed.sourceID
        sourceURL = packed.sourceURL
        qualityScore = packed.qualityScore
        reviewStatus = packed.reviewStatus
        choiceExplanationsData = Self.encode(packed.choiceExplanations ?? [])
        learningOutcomeName = packed.learningOutcomeName
        subcategory = packed.subcategory
        wineType = packed.wineType
        difficulty = packed.difficulty
        misconceptionTagsData = Self.encode(packed.misconceptionTags ?? [])
        needsReview = packed.needsReview ?? false
        reviewReason = packed.reviewReason
        creationType = packed.creationType
        creationBasis = packed.creationBasis
        let english = packed.translations?["en"]
        let japanese = packed.translations?["ja"]
        promptEnglish = english?.prompt ?? (packed.language == "en" ? packed.prompt : nil)
        promptJapanese = japanese?.prompt ?? (packed.language == "ja" ? packed.prompt : nil)
        answerEnglish = english?.answer ?? (packed.language == "en" ? packed.answer : nil)
        answerJapanese = japanese?.answer ?? (packed.language == "ja" ? packed.answer : nil)
        explanationEnglish = english?.explanation
            ?? (packed.language == "en" ? packed.explanation : nil)
        explanationJapanese = japanese?.explanation
            ?? (packed.language == "ja" ? packed.explanation : nil)
        choicesEnglishData = english.map { Self.encode($0.choices) }
        choicesJapaneseData = japanese.map { Self.encode($0.choices) }
        translationStatus = packed.translationStatus
        translationModel = packed.translationModel
    }

    var choices: [String] { Self.decode(choicesData) }
    var choiceExplanations: [String] {
        guard let choiceExplanationsData else { return [] }
        return Self.decode(choiceExplanationsData)
    }
    var misconceptionTags: [String] {
        guard let misconceptionTagsData else { return [] }
        return Self.decode(misconceptionTagsData)
    }
    var displayPrompt: String {
        localizedValue(english: promptEnglish, japanese: promptJapanese) ?? prompt
    }
    var displayChoices: [String] {
        let localizedData = AppLanguage.isJapanese ? choicesJapaneseData : choicesEnglishData
        guard let localizedData else { return choices }
        return Self.decode(localizedData)
    }
    var displayExplanation: String? {
        localizedValue(english: explanationEnglish, japanese: explanationJapanese)
            ?? explanation
    }
    var geography: [String] { Self.decode(geographyData) }
    var grapeVarieties: [String] { Self.decode(grapeVarietiesData) }
    var hasAnswer: Bool { visibleAnswer != nil }

    var searchableText: String {
        [
            prompt,
            answer,
            promptEnglish,
            answerEnglish,
            promptJapanese,
            answerJapanese,
            topic,
        ]
        .compactMap { $0 }
        .joined(separator: "\n")
    }

    var displayAnswer: String {
        visibleAnswer ?? "この問題には表示できる回答がありません。"
    }

    private var visibleAnswer: String? {
        guard let answer = localizedValue(
            english: answerEnglish,
            japanese: answerJapanese
        ) ?? answer else { return nil }
        let withoutHTML = answer.replacingOccurrences(
            of: "<[^>]+>",
            with: "",
            options: .regularExpression
        )
        let invisible = CharacterSet.whitespacesAndNewlines
            .union(.controlCharacters)
            .union(CharacterSet(charactersIn: "\u{200B}\u{200C}\u{200D}\u{FEFF}"))
        guard withoutHTML.unicodeScalars.contains(where: { !invisible.contains($0) }) else {
            return nil
        }
        return answer
    }

    private func localizedValue(english: String?, japanese: String?) -> String? {
        AppLanguage.isJapanese ? (japanese ?? english) : (english ?? japanese)
    }

    var modeLabel: String {
        switch studyMode {
        case "multiple_choice": "四択"
        case "written_answer": "記述式"
        default: "フラッシュカード"
        }
    }

    var learningOutcomeLabel: String {
        LearningOutcome(rawValue: learningOutcome)?.shortLabel ?? learningOutcome
    }

    private static func encode(_ values: [String]) -> Data {
        (try? JSONEncoder().encode(values)) ?? Data("[]".utf8)
    }

    private static func decode(_ data: Data) -> [String] {
        (try? JSONDecoder().decode([String].self, from: data)) ?? []
    }
}

@Model
final class QuestionProgress {
    @Attribute(.unique) var questionID: String
    var isBookmarked: Bool
    var attemptCount: Int
    var correctCount: Int
    var intervalDays: Int
    var dueDate: Date
    var lastStudiedAt: Date?
    var lastWasCorrect: Bool?

    init(questionID: String) {
        self.questionID = questionID
        isBookmarked = false
        attemptCount = 0
        correctCount = 0
        intervalDays = 0
        dueDate = .now
        lastWasCorrect = nil
    }

    func record(isCorrect: Bool, rating: Int, at date: Date = .now) {
        attemptCount += 1
        correctCount += isCorrect ? 1 : 0
        lastStudiedAt = date
        lastWasCorrect = isCorrect
        if rating == 0 {
            intervalDays = 0
            dueDate = Calendar.current.date(byAdding: .minute, value: 10, to: date) ?? date
        } else {
            intervalDays = max(1, intervalDays == 0 ? 1 : intervalDays * 2)
            dueDate = Calendar.current.date(byAdding: .day, value: intervalDays, to: date) ?? date
        }
    }
}

@Model
final class StudyAttempt {
    @Attribute(.unique) var id: UUID
    var questionID: String
    var isCorrect: Bool
    var rating: Int
    var studiedAt: Date
    var responseText: String?

    init(
        questionID: String,
        isCorrect: Bool,
        rating: Int,
        responseText: String? = nil,
        studiedAt: Date = .now
    ) {
        id = UUID()
        self.questionID = questionID
        self.isCorrect = isCorrect
        self.rating = rating
        self.studiedAt = studiedAt
        self.responseText = responseText
    }
}

enum LearningOutcome: String, CaseIterable, Identifiable {
    case all
    case u1Lo1 = "u1_lo1"
    case u1Lo2 = "u1_lo2"
    case u1Lo3 = "u1_lo3"
    case u1Lo4 = "u1_lo4"
    case u1Lo5 = "u1_lo5"

    var id: String { rawValue }

    var shortLabel: String {
        switch self {
        case .all: "すべての学習成果"
        case .u1Lo1: "U1 LO1 · 生産"
        case .u1Lo2: "U1 LO2 · スティルワイン"
        case .u1Lo3: "U1 LO3 · スパークリング"
        case .u1Lo4: "U1 LO4 · 酒精強化"
        case .u1Lo5: "U1 LO5 · 提案とサービス"
        }
    }
}
