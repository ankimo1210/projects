import Foundation

struct TastingComparisonField: Identifiable, Equatable {
    let id: String
    let label: String
    let firstValue: String
    let secondValue: String
}

struct TastingComparisonSection: Identifiable, Equatable {
    let id: String
    let title: String
    let fields: [TastingComparisonField]
}

enum TastingComparisonService {
    static func displayName(for note: TastingNote) -> String {
        let name = note.wineName.trimmingCharacters(in: .whitespacesAndNewlines)
        return name.isEmpty ? SATDisplayText.japanese(note.sampleLabel) : name
    }

    static func sections(
        first: TastingNote,
        second: TastingNote
    ) -> [TastingComparisonSection] {
        [
            section(
                id: "wine",
                title: "ワイン",
                first: first,
                second: second,
                fields: [
                    ("identity", "ワイン名・正体", { displayName(for: $0) }, false),
                ]
            ),
            section(
                id: "appearance",
                title: "外観",
                first: first,
                second: second,
                fields: [
                    ("clarity", "清澄度", { $0.appearanceClarity }, true),
                    ("intensity", "濃淡", { $0.appearanceIntensity }, true),
                    ("colour", "色", { $0.appearanceColour }, false),
                ]
            ),
            section(
                id: "nose",
                title: "香り",
                first: first,
                second: second,
                fields: [
                    ("condition", "状態", { $0.noseCondition }, true),
                    ("intensity", "強さ", { $0.noseIntensity }, true),
                    ("development", "熟成度", { $0.noseDevelopment }, true),
                    ("aromas", "特徴", { $0.aromaNotes }, false),
                ]
            ),
            section(
                id: "palate",
                title: "味わい",
                first: first,
                second: second,
                fields: [
                    ("sweetness", "甘辛度", { $0.sweetness }, true),
                    ("acidity", "酸味", { $0.acidity }, true),
                    ("tannin", "タンニン", { $0.tannin }, true),
                    ("alcohol", "アルコール", { $0.alcohol }, true),
                    ("body", "ボディ", { $0.body }, true),
                    ("flavour-intensity", "風味の強さ", { $0.flavourIntensity }, true),
                    ("finish", "余韻", { $0.finish }, true),
                    ("flavours", "風味の特徴", { $0.flavourNotes }, false),
                ]
            ),
            section(
                id: "conclusions",
                title: "結論",
                first: first,
                second: second,
                fields: [
                    ("quality", "品質", { $0.quality }, true),
                    ("readiness", "飲み頃", { $0.readiness }, true),
                    ("support", "根拠", { $0.conclusion }, false),
                ]
            ),
        ]
    }

    private typealias FieldDefinition = (
        id: String,
        label: String,
        value: (TastingNote) -> String,
        translatesSATValue: Bool
    )

    private static func section(
        id: String,
        title: String,
        first: TastingNote,
        second: TastingNote,
        fields: [FieldDefinition]
    ) -> TastingComparisonSection {
        TastingComparisonSection(
            id: id,
            title: title,
            fields: fields.map { definition in
                TastingComparisonField(
                    id: "\(id).\(definition.id)",
                    label: definition.label,
                    firstValue: display(
                        definition.value(first),
                        translatesSATValue: definition.translatesSATValue
                    ),
                    secondValue: display(
                        definition.value(second),
                        translatesSATValue: definition.translatesSATValue
                    )
                )
            }
        )
    }

    private static func display(_ value: String, translatesSATValue: Bool) -> String {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return "未入力" }
        return translatesSATValue ? SATDisplayText.japanese(trimmed) : trimmed
    }
}
