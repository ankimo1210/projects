import Foundation

enum StudyFocusDimension: String, CaseIterable, Identifiable {
    case geography
    case grapeVariety
    case wineType
    case knowledgeArea
    case difficulty
    case cognitiveSkill

    var id: String { rawValue }

    var label: String {
        switch self {
        case .geography: "国・産地"
        case .grapeVariety: "主要品種"
        case .wineType: "ワイン区分"
        case .knowledgeArea: "知識領域"
        case .difficulty: "難易度"
        case .cognitiveSkill: "思考スキル"
        }
    }

    var minimumOptionCount: Int {
        switch self {
        case .geography, .grapeVariety, .knowledgeArea: 2
        case .wineType, .difficulty, .cognitiveSkill: 1
        }
    }
}

struct StudyFocusItem: Identifiable, Hashable {
    let questionID: String
    let geography: [String]
    let grapeVarieties: [String]
    let wineType: String?
    let category: String
    let difficulty: String?
    let cognitiveSkill: String?

    var id: String { questionID }

    init(
        questionID: String,
        geography: [String],
        grapeVarieties: [String],
        wineType: String?,
        category: String,
        difficulty: String?,
        cognitiveSkill: String?
    ) {
        self.questionID = questionID
        self.geography = geography
        self.grapeVarieties = grapeVarieties
        self.wineType = wineType
        self.category = category
        self.difficulty = difficulty
        self.cognitiveSkill = cognitiveSkill
    }
}

struct StudyFocusOption: Identifiable, Hashable {
    let value: String
    let questionCount: Int

    var id: String { value }
}

enum StudyFocusCatalog {
    private static let japaneseLocale = Locale(identifier: "ja_JP")

    static func options(
        for dimension: StudyFocusDimension,
        in items: [StudyFocusItem]
    ) -> [StudyFocusOption] {
        var counts: [String: Int] = [:]
        for item in items {
            for value in normalizedValues(for: dimension, in: item) {
                counts[value, default: 0] += 1
            }
        }

        return counts
            .compactMap { value, count in
                guard count >= dimension.minimumOptionCount else { return nil }
                return StudyFocusOption(value: value, questionCount: count)
            }
            .sorted { lhs, rhs in
                if lhs.questionCount != rhs.questionCount {
                    return lhs.questionCount > rhs.questionCount
                }
                let localizedOrder = lhs.value.compare(
                    rhs.value,
                    options: [.caseInsensitive, .numeric],
                    range: nil,
                    locale: japaneseLocale
                )
                if localizedOrder != .orderedSame {
                    return localizedOrder == .orderedAscending
                }
                return lhs.value < rhs.value
            }
    }

    static func matches(
        _ item: StudyFocusItem,
        dimension: StudyFocusDimension,
        value: String
    ) -> Bool {
        let normalizedValue = normalize(value, for: dimension)
        guard !normalizedValue.isEmpty else { return false }
        return normalizedValues(for: dimension, in: item).contains(normalizedValue)
    }

    static func matchingQuestionIDs(
        for dimension: StudyFocusDimension,
        value: String,
        in items: [StudyFocusItem]
    ) -> Set<String> {
        Set(
            items.lazy
                .filter { matches($0, dimension: dimension, value: value) }
                .map(\.questionID)
        )
    }

    private static func normalizedValues(
        for dimension: StudyFocusDimension,
        in item: StudyFocusItem
    ) -> Set<String> {
        let rawValues: [String]
        switch dimension {
        case .geography:
            rawValues = item.geography
        case .grapeVariety:
            rawValues = item.grapeVarieties
        case .wineType:
            rawValues = [item.wineType].compactMap { $0 }
        case .knowledgeArea:
            rawValues = [item.category]
        case .difficulty:
            rawValues = [item.difficulty].compactMap { $0 }
        case .cognitiveSkill:
            rawValues = [item.cognitiveSkill].compactMap { $0 }
        }

        return Set(
            rawValues
                .map { normalize($0, for: dimension) }
                .filter { !$0.isEmpty }
        )
    }

    private static func normalize(_ value: String, for dimension: StudyFocusDimension) -> String {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard dimension == .wineType else { return trimmed }
        guard !trimmed.isEmpty else { return "" }

        if trimmed == "全般" || trimmed.contains("全般") || trimmed == "甘口ワイン" {
            return "共通・横断"
        }
        if trimmed.contains("酒精強化") {
            return "酒精強化ワイン"
        }
        if trimmed.contains("非発泡性") {
            return "非発泡性ワイン"
        }
        if trimmed.contains("発泡性") {
            return "発泡性ワイン"
        }
        return "非発泡性ワイン"
    }
}
