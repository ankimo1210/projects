import Foundation
import SwiftData

enum SATDisplayText {
    static func japanese(_ value: String) -> String {
        switch value {
        case "Wine": "ワイン"
        case "Wine 1": "ワイン1"
        case "Wine 2": "ワイン2"
        case "Clear": "澄んでいる"
        case "Hazy": "濁っている"
        case "Pale": "淡い"
        case "Medium": "中程度"
        case "Deep": "濃い"
        case "Clean": "健全"
        case "Unclean": "不健全"
        case "Light": "弱い／軽い"
        case "Medium(-)": "中程度(-)"
        case "Medium(+)": "中程度(+)"
        case "Pronounced": "強い"
        case "Youthful": "若い"
        case "Developing": "熟成中"
        case "Fully developed": "十分に熟成"
        case "Tired / past its best": "衰退／最盛期を過ぎた"
        case "Dry": "辛口"
        case "Off-dry": "やや辛口"
        case "Medium-dry": "中辛口"
        case "Medium-sweet": "中甘口"
        case "Sweet": "甘口"
        case "Luscious": "極甘口"
        case "Low": "低い"
        case "High": "高い"
        case "Full": "フル"
        case "Short": "短い"
        case "Long": "長い"
        case "Faulty": "欠陥あり"
        case "Poor": "劣る"
        case "Acceptable": "可"
        case "Good": "良い"
        case "Very good": "非常に良い"
        case "Outstanding": "卓越"
        case "Too young": "若すぎる"
        case "Can drink now, suitable for ageing": "今飲めるが熟成にも向く"
        case "Can drink now, not suitable for ageing": "今が飲み頃で熟成には向かない"
        case "Too old": "古すぎる"
        default: value
        }
    }
}

@Model
final class TastingNote {
    @Attribute(.unique) var id: UUID
    var sessionID: UUID?
    var sampleLabel: String
    var tastedAt: Date
    var wineName: String
    var appearanceClarity: String
    var appearanceIntensity: String
    var appearanceColour: String
    var noseCondition: String
    var noseIntensity: String
    var noseDevelopment: String
    var aromaNotes: String
    var sweetness: String
    var acidity: String
    var tannin: String
    var alcohol: String
    var body: String
    var flavourIntensity: String
    var finish: String
    var flavourNotes: String
    var quality: String
    var readiness: String
    var conclusion: String
    var examStartedAt: Date? = nil
    var examSubmittedAt: Date? = nil
    var examDurationSeconds: Int? = nil
    var examWasTimeExpired: Bool? = nil
    var examCompletionPercent: Double? = nil

    init(
        draft: TastingDraft,
        sessionID: UUID? = nil,
        sampleLabel: String = "Wine",
        examStartedAt: Date? = nil,
        examSubmittedAt: Date? = nil,
        examDurationSeconds: Int? = nil,
        examWasTimeExpired: Bool? = nil,
        examCompletionPercent: Double? = nil
    ) {
        id = UUID()
        self.sessionID = sessionID
        self.sampleLabel = sampleLabel
        tastedAt = .now
        wineName = draft.wineName
        appearanceClarity = draft.appearanceClarity
        appearanceIntensity = draft.appearanceIntensity
        appearanceColour = draft.appearanceColour
        noseCondition = draft.noseCondition
        noseIntensity = draft.noseIntensity
        noseDevelopment = draft.noseDevelopment
        aromaNotes = draft.aromaNotes
        sweetness = draft.sweetness
        acidity = draft.acidity
        tannin = draft.tannin
        alcohol = draft.alcohol
        body = draft.body
        flavourIntensity = draft.flavourIntensity
        finish = draft.finish
        flavourNotes = draft.flavourNotes
        quality = draft.quality
        readiness = draft.readiness
        conclusion = draft.conclusion
        self.examStartedAt = examStartedAt
        self.examSubmittedAt = examSubmittedAt
        self.examDurationSeconds = examDurationSeconds
        self.examWasTimeExpired = examWasTimeExpired
        self.examCompletionPercent = examCompletionPercent
    }

    func update(from draft: TastingDraft) {
        wineName = draft.wineName
        appearanceClarity = draft.appearanceClarity
        appearanceIntensity = draft.appearanceIntensity
        appearanceColour = draft.appearanceColour
        noseCondition = draft.noseCondition
        noseIntensity = draft.noseIntensity
        noseDevelopment = draft.noseDevelopment
        aromaNotes = draft.aromaNotes
        sweetness = draft.sweetness
        acidity = draft.acidity
        tannin = draft.tannin
        alcohol = draft.alcohol
        body = draft.body
        flavourIntensity = draft.flavourIntensity
        finish = draft.finish
        flavourNotes = draft.flavourNotes
        quality = draft.quality
        readiness = draft.readiness
        conclusion = draft.conclusion
    }
}

nonisolated struct TastingDraft: Codable, Equatable {
    var wineName = ""
    var appearanceClarity = "Clear"
    var appearanceIntensity = "Medium"
    var appearanceColour = ""
    var noseCondition = "Clean"
    var noseIntensity = "Medium"
    var noseDevelopment = "Youthful"
    var aromaNotes = ""
    var sweetness = "Dry"
    var acidity = "Medium"
    var tannin = "Medium"
    var alcohol = "Medium"
    var body = "Medium"
    var flavourIntensity = "Medium"
    var finish = "Medium"
    var flavourNotes = ""
    var quality = "Good"
    var readiness = "Can drink now, suitable for ageing"
    var conclusion = ""

    init() {}

    @MainActor
    init(note: TastingNote) {
        wineName = note.wineName
        appearanceClarity = note.appearanceClarity
        appearanceIntensity = note.appearanceIntensity
        appearanceColour = note.appearanceColour
        noseCondition = note.noseCondition
        noseIntensity = note.noseIntensity
        noseDevelopment = note.noseDevelopment
        aromaNotes = note.aromaNotes
        sweetness = note.sweetness
        acidity = note.acidity
        tannin = note.tannin
        alcohol = note.alcohol
        body = note.body
        flavourIntensity = note.flavourIntensity
        finish = note.finish
        flavourNotes = note.flavourNotes
        quality = note.quality
        readiness = note.readiness
        conclusion = note.conclusion
    }

    var isMeaningful: Bool {
        !appearanceColour.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            || !aromaNotes.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            || !flavourNotes.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            || !conclusion.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }
}
