import Foundation

enum TastingField: String, Codable, CaseIterable, Hashable {
    case wineName
    case appearanceClarity
    case appearanceIntensity
    case appearanceColour
    case noseCondition
    case noseIntensity
    case noseDevelopment
    case aromaNotes
    case sweetness
    case acidity
    case tannin
    case alcohol
    case body
    case flavourIntensity
    case finish
    case flavourNotes
    case quality
    case readiness
    case conclusion

    static let assessedFields = allCases.filter { $0 != .wineName }

    var requiresText: Bool {
        switch self {
        case .wineName, .appearanceColour, .aromaNotes, .flavourNotes, .conclusion:
            true
        default:
            false
        }
    }

    var displayLabel: String {
        switch self {
        case .wineName: "ワイン名・正体"
        case .appearanceClarity: "清澄度"
        case .appearanceIntensity: "濃淡"
        case .appearanceColour: "色"
        case .noseCondition: "香りの状態"
        case .noseIntensity: "香りの強さ"
        case .noseDevelopment: "熟成度"
        case .aromaNotes: "香りの特徴"
        case .sweetness: "甘辛度"
        case .acidity: "酸味"
        case .tannin: "タンニン"
        case .alcohol: "アルコール"
        case .body: "ボディ"
        case .flavourIntensity: "風味の強さ"
        case .finish: "余韻"
        case .flavourNotes: "風味の特徴"
        case .quality: "品質"
        case .readiness: "飲み頃"
        case .conclusion: "結論の根拠"
        }
    }
}

struct TastingExamWineState: Codable, Equatable {
    var draft = TastingDraft()
    var completedFields: Set<TastingField> = []

    var completedFieldCount: Int {
        completedFields.intersection(Set(TastingField.assessedFields)).count
    }

    var totalFieldCount: Int { TastingField.assessedFields.count }

    var completionPercent: Double {
        guard totalFieldCount > 0 else { return 0 }
        return Double(completedFieldCount) / Double(totalFieldCount)
    }

    var hasInput: Bool {
        !completedFields.isEmpty || draft.isMeaningful
    }

    mutating func recordEdit(_ field: TastingField) {
        if field.requiresText
            && draft.value(for: field).trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            completedFields.remove(field)
        } else {
            completedFields.insert(field)
        }
    }
}

extension TastingDraft {
    func changedFields(comparedTo previous: TastingDraft) -> [TastingField] {
        TastingField.allCases.filter { value(for: $0) != previous.value(for: $0) }
    }

    func value(for field: TastingField) -> String {
        switch field {
        case .wineName: wineName
        case .appearanceClarity: appearanceClarity
        case .appearanceIntensity: appearanceIntensity
        case .appearanceColour: appearanceColour
        case .noseCondition: noseCondition
        case .noseIntensity: noseIntensity
        case .noseDevelopment: noseDevelopment
        case .aromaNotes: aromaNotes
        case .sweetness: sweetness
        case .acidity: acidity
        case .tannin: tannin
        case .alcohol: alcohol
        case .body: body
        case .flavourIntensity: flavourIntensity
        case .finish: finish
        case .flavourNotes: flavourNotes
        case .quality: quality
        case .readiness: readiness
        case .conclusion: conclusion
        }
    }
}

struct TastingExamSnapshot: Codable, Equatable {
    static let currentSchemaVersion = 1
    static let standardDurationSeconds = 30 * 60

    let schemaVersion: Int
    let sessionID: UUID
    let startedAt: Date
    let durationSeconds: Int
    var wineOne: TastingExamWineState
    var wineTwo: TastingExamWineState

    init(
        sessionID: UUID = UUID(),
        startedAt: Date = .now,
        durationSeconds: Int = standardDurationSeconds,
        wineOne: TastingExamWineState = TastingExamWineState(),
        wineTwo: TastingExamWineState = TastingExamWineState()
    ) {
        schemaVersion = Self.currentSchemaVersion
        self.sessionID = sessionID
        self.startedAt = startedAt
        self.durationSeconds = durationSeconds
        self.wineOne = wineOne
        self.wineTwo = wineTwo
    }

    func remainingSeconds(at date: Date = .now) -> Int {
        TastingExamClock.remainingSeconds(
            startedAt: startedAt,
            durationSeconds: durationSeconds,
            at: date
        )
    }

    func isExpired(at date: Date = .now) -> Bool {
        remainingSeconds(at: date) == 0
    }
}

enum TastingExamClock {
    static func remainingSeconds(
        startedAt: Date,
        durationSeconds: Int,
        at date: Date
    ) -> Int {
        let elapsed = max(0, Int(date.timeIntervalSince(startedAt).rounded(.down)))
        return max(0, durationSeconds - elapsed)
    }

    static func displayText(seconds: Int) -> String {
        let clamped = max(0, seconds)
        return String(format: "%02d:%02d", clamped / 60, clamped % 60)
    }
}

struct TastingExamDraftStore {
    static let shared = TastingExamDraftStore(defaults: .standard)
    static let storageKey = "tasting.exam.active.v1"

    let defaults: UserDefaults

    func load() -> TastingExamSnapshot? {
        guard let data = defaults.data(forKey: Self.storageKey),
              let snapshot = try? Self.decoder.decode(TastingExamSnapshot.self, from: data),
              snapshot.schemaVersion == TastingExamSnapshot.currentSchemaVersion
        else { return nil }
        return snapshot
    }

    func save(_ snapshot: TastingExamSnapshot) {
        guard let data = try? Self.encoder.encode(snapshot) else { return }
        defaults.set(data, forKey: Self.storageKey)
    }

    func clear() {
        defaults.removeObject(forKey: Self.storageKey)
    }

    private static let encoder = JSONEncoder()
    private static let decoder = JSONDecoder()
}

struct TastingVocabularyGroup: Identifiable, Hashable {
    let name: String
    let values: [String]

    var id: String { name }
}

enum TastingVocabularyCatalog {
    static let groups: [TastingVocabularyGroup] = [
        TastingVocabularyGroup(
            name: "果実",
            values: [
                "レモン", "ライム", "グレープフルーツ", "オレンジ", "青リンゴ", "赤リンゴ",
                "洋梨", "桃", "アプリコット", "メロン", "バナナ", "ライチ", "イチゴ",
                "ラズベリー", "チェリー", "プラム", "ブラックベリー", "カシス", "干しブドウ",
                "プルーン"
            ]
        ),
        TastingVocabularyGroup(
            name: "花・植物",
            values: [
                "白い花", "バラ", "スミレ", "青草", "ピーマン", "ミント", "ユーカリ",
                "トマトの葉", "紅茶", "タバコ"
            ]
        ),
        TastingVocabularyGroup(
            name: "スパイス・樽",
            values: [
                "黒コショウ", "白コショウ", "クローヴ", "シナモン", "ナツメグ", "バニラ",
                "トースト", "コーヒー", "チョコレート", "ココナッツ", "スモーク", "杉"
            ]
        ),
        TastingVocabularyGroup(
            name: "醸造・熟成・その他",
            values: [
                "パン生地", "ビスケット", "バター", "クリーム", "ヨーグルト", "蜂蜜",
                "キノコ", "土", "革", "肉", "ナッツ", "アーモンド", "マーマレード",
                "石灰", "火打石", "濡れた石"
            ]
        ),
    ]

    static var allValues: [String] {
        groups.flatMap(\.values)
    }

    static func groups(matching searchText: String) -> [TastingVocabularyGroup] {
        let query = ReferenceSearch.normalize(searchText)
        guard !query.isEmpty else { return groups }
        return groups.compactMap { group in
            let values = group.values.filter {
                ReferenceSearch.normalize($0).contains(query)
            }
            return values.isEmpty
                ? nil
                : TastingVocabularyGroup(name: group.name, values: values)
        }
    }

    static func frequentlyUsedValues(
        in entries: [String],
        matching searchText: String = "",
        limit: Int = 8
    ) -> [String] {
        let query = ReferenceSearch.normalize(searchText)
        var counts: [String: Int] = [:]
        for entry in entries {
            let values = entry
                .components(
                    separatedBy: CharacterSet(charactersIn: "、，,;/／\n")
                )
                .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
                .filter { !$0.isEmpty && $0.count <= 40 }
            for value in Set(values) where
                query.isEmpty || ReferenceSearch.normalize(value).contains(query) {
                counts[value, default: 0] += 1
            }
        }
        return counts.keys.sorted { lhs, rhs in
            if counts[lhs] != counts[rhs] {
                return counts[lhs, default: 0] > counts[rhs, default: 0]
            }
            return lhs.localizedStandardCompare(rhs) == .orderedAscending
        }
        .prefix(max(0, limit))
        .map { $0 }
    }
}
