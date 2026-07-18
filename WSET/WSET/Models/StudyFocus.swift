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
        case .geography, .knowledgeArea, .wineType, .difficulty, .cognitiveSkill: 1
        case .grapeVariety: 2
        }
    }
}

struct StudyFocusItem: Identifiable, Hashable {
    let questionID: String
    let geography: [String]
    let countries: [String]?
    let regions: [String]?
    let grapeVarieties: [String]
    let wineType: String?
    let category: String
    let difficulty: String?
    let cognitiveSkill: String?

    var id: String { questionID }

    init(
        questionID: String,
        geography: [String],
        countries: [String]? = nil,
        regions: [String]? = nil,
        grapeVarieties: [String],
        wineType: String?,
        category: String,
        difficulty: String?,
        cognitiveSkill: String?
    ) {
        self.questionID = questionID
        self.geography = geography
        self.countries = countries
        self.regions = regions
        self.grapeVarieties = grapeVarieties
        self.wineType = wineType
        self.category = category
        self.difficulty = difficulty
        self.cognitiveSkill = cognitiveSkill
    }
}

enum StudyFocusOptionKind: String, Hashable {
    case standard
    case country
    case region
}

struct StudyFocusOption: Identifiable, Hashable {
    let value: String
    let questionCount: Int
    let kind: StudyFocusOptionKind
    let groupTitle: String?

    init(
        value: String,
        questionCount: Int,
        kind: StudyFocusOptionKind = .standard,
        groupTitle: String? = nil
    ) {
        self.value = value
        self.questionCount = questionCount
        self.kind = kind
        self.groupTitle = groupTitle
    }

    var id: String { "\(kind.rawValue)|\(groupTitle ?? "")|\(value)" }

    var displayValue: String {
        kind == .region ? "\u{3000}\u{3000}\(value)" : value
    }
}

struct StudyFocusOptionGroup: Identifiable, Hashable {
    let title: String
    let options: [StudyFocusOption]

    var id: String { title }
}

/// Shared, side-effect-free question classification and review queries.
///
/// Views provide the current entitlement and time, while this layer owns the
/// rules for deciding which questions belong to each study workflow. Keeping
/// `now` explicit makes due-date behavior deterministic in unit tests.
enum StudyQuestionQuery {
    static func accessible(
        _ questions: [StudyQuestion],
        policy: FeatureAccessPolicy
    ) -> [StudyQuestion] {
        questions.filter {
            policy.canAccessQuestion(id: $0.id, studyMode: $0.studyMode)
        }
    }

    static func multipleChoice(
        in questions: [StudyQuestion],
        learningOutcome: String? = nil
    ) -> [StudyQuestion] {
        questions.filter { question in
            question.studyMode == "multiple_choice"
                && question.correctAnswerIndex != nil
                && (learningOutcome == nil || question.learningOutcome == learningOutcome)
        }
    }

    static func written(
        in questions: [StudyQuestion],
        requiringRubric: Bool = false
    ) -> [StudyQuestion] {
        questions.filter {
            $0.studyMode == "written_answer"
                && (!requiringRubric || !$0.rubricItems.isEmpty)
        }
    }

    static func theoryCandidates(in questions: [StudyQuestion]) -> [StudyQuestion] {
        multipleChoice(in: questions) + written(in: questions, requiringRubric: true)
    }

    static func mistakes(
        in questions: [StudyQuestion],
        progressByID: [String: QuestionProgress]
    ) -> [StudyQuestion] {
        questions.filter { progressByID[$0.id]?.lastWasCorrect == false }
    }

    static func due(
        in questions: [StudyQuestion],
        progressByID: [String: QuestionProgress],
        now: Date
    ) -> [StudyQuestion] {
        questions.filter {
            guard let progress = progressByID[$0.id] else { return false }
            return progress.attemptCount > 0 && progress.dueDate <= now
        }
    }

    static func bookmarked(
        in questions: [StudyQuestion],
        progressByID: [String: QuestionProgress]
    ) -> [StudyQuestion] {
        questions.filter { progressByID[$0.id]?.isBookmarked == true }
    }
}

enum StudyFocusCatalog {
    private static let japaneseLocale = Locale(identifier: "ja_JP")

    private static let countryOrder = GeographyNormalizer.countryOrder

    private static let regionOrderByCountry: [String: [String]] = [
        "フランス": [
            "ボルドー", "ブルゴーニュ", "シャンパーニュ", "ロワール", "アルザス",
            "北部ローヌ", "プロヴァンス", "ボージョレ", "リムー", "ルーション",
        ],
        "イタリア": [
            "ピエモンテ", "トスカーナ", "ヴェネト", "ソアーヴェ・クラッシコ",
            "ヴァルポリチェッラ", "プロセッコ", "アスティ", "フランチャコルタ",
            "トレントDOC",
        ],
        "スペイン": [
            "リオハ", "リベラ・デル・ドゥエロ", "プリオラート", "ヘレス", "カバ",
            "リアス・バイシャス", "ルエダ", "ビエルソ", "トロ", "ナバーラ",
        ],
        "ポルトガル": [
            "ドウロ", "ポート", "ヴィーニョ・ヴェルデ", "ダン", "アレンテージョ",
            "バイラーダ",
        ],
        "ドイツ": ["モーゼル", "ラインガウ", "ファルツ", "ラインヘッセン", "ナーエ", "バーデン"],
        "オーストリア": ["ヴァッハウ", "カンプタール", "クレムスタール", "ブルゲンラント"],
        "米国": [
            "カリフォルニア", "ナパ・ヴァレー", "ソノマ", "ウィラメット・ヴァレー",
            "ワシントン", "フィンガー・レイクス",
        ],
        "オーストラリア": [
            "バロッサ・ヴァレー", "ハンター・ヴァレー", "マーガレット・リヴァー",
            "クナワラ", "マクラーレン・ヴェイル", "アデレード・ヒルズ",
            "クレア・ヴァレー", "イーデン・ヴァレー", "ヤラ・ヴァレー", "タスマニア",
            "ラザグレン",
        ],
        "ニュージーランド": ["マールボロ", "セントラル・オタゴ", "ホークス・ベイ"],
        "南アフリカ": [
            "ステレンボッシュ", "スワートランド", "ウォーカー・ベイ", "コンスタンシア",
            "エルギン", "パール", "キャップ・クラシック",
        ],
        "チリ": [
            "マイポ・ヴァレー", "コルチャグア・ヴァレー", "カサブランカ・ヴァレー",
            "サン・アントニオ・ヴァレー", "アコンカグア・ヴァレー", "リマリ・ヴァレー",
        ],
        "アルゼンチン": [
            "メンドーサ", "ウコ・ヴァレー", "ルハン・デ・クージョ", "サルタ",
            "カファジャテ", "パタゴニア",
        ],
        "カナダ": ["オンタリオ", "ナイアガラ半島", "ブリティッシュ・コロンビア", "オカナガン・ヴァレー"],
        "ハンガリー": ["トカイ"],
        "ギリシャ": ["サントリーニ", "ナウサ"],
        "英国": ["イングランド南部"],
    ]

    private static let internationalGrapes = [
        "カベルネ・ソーヴィニヨン", "メルロ", "ピノ・ノワール", "シラー／シラーズ",
        "シャルドネ", "ソーヴィニヨン・ブラン", "リースリング",
    ]

    private static let semiInternationalGrapes = [
        "カベルネ・フラン", "グルナッシュ／ガルナッチャ", "マルベック", "カルメネール",
        "ジンファンデル／プリミティーヴォ", "サンジョヴェーゼ", "ネッビオーロ",
        "テンプラニーリョ", "シュナン・ブラン", "セミヨン", "ヴィオニエ",
        "ピノ・グリ／グリージョ", "ゲヴュルツトラミネール", "マスカット系", "ガメイ",
        "ムーニエ",
    ]

    private static let grapeGroupOrder = [
        "国際品種", "準国際品種", "地域・固有品種", "品種グループ",
    ]

    private static let wineTypeOrder = [
        "非発泡性ワイン", "発泡性ワイン", "酒精強化ワイン", "共通・横断",
    ]

    private static let knowledgeAreaOrder = [
        "自然要因", "栽培・ブドウ樹", "醸造・製法", "熟成・ブレンド", "品種",
        "産地・スタイル", "法律・表示", "商業・価格・品質", "保管・包装", "サービス",
        "欠陥", "料理との組み合わせ", "情報提供・推奨", "責任ある飲酒",
    ]

    private static let difficultyOrder = ["D1", "D2", "D3"]
    private static let cognitiveSkillOrder = [
        "知識確認", "因果説明", "適用", "比較", "判断", "統合判断",
    ]

    static func options(
        for dimension: StudyFocusDimension,
        in items: [StudyFocusItem]
    ) -> [StudyFocusOption] {
        if dimension == .geography {
            return geographyOptions(in: items)
        }

        var counts: [String: Int] = [:]
        for item in items {
            for value in normalizedValues(for: dimension, in: item) {
                counts[value, default: 0] += 1
            }
        }

        return counts
            .compactMap { value, count in
                let groupTitle = dimension == .grapeVariety ? grapeGroup(for: value) : nil
                let alwaysShow = groupTitle == "国際品種" || groupTitle == "準国際品種"
                guard alwaysShow || count >= dimension.minimumOptionCount else { return nil }
                return StudyFocusOption(
                    value: value,
                    questionCount: count,
                    groupTitle: groupTitle
                )
            }
            .sorted { optionPrecedes($0, $1, dimension: dimension) }
    }

    static func optionGroups(
        for dimension: StudyFocusDimension,
        options: [StudyFocusOption]
    ) -> [StudyFocusOptionGroup] {
        guard dimension == .grapeVariety else { return [] }
        return grapeGroupOrder.compactMap { title in
            let grouped = options.filter { $0.groupTitle == title }
            return grouped.isEmpty ? nil : StudyFocusOptionGroup(title: title, options: grouped)
        }
    }

    static func displayValue(for option: StudyFocusOption, dimension: StudyFocusDimension) -> String {
        switch dimension {
        case .difficulty:
            switch option.value {
            case "D1": "D1 · 基礎知識"
            case "D2": "D2 · 理解と適用"
            case "D3": "D3 · 比較と統合"
            default: option.value
            }
        default:
            option.displayValue
        }
    }

    static func guidance(for dimension: StudyFocusDimension) -> String {
        switch dimension {
        case .geography:
            "主要国の下に関連産地を字下げして表示します。産地は2問以上あるものを表示します。"
        case .grapeVariety:
            "国際品種、準国際品種、地域・固有品種の順に表示し、別名は同じ品種へまとめます。"
        case .wineType:
            "非発泡性、発泡性、酒精強化、共通・横断の順に表示します。"
        case .knowledgeArea:
            "細かい複合タグを、学習しやすい14の知識領域へまとめています。"
        case .difficulty:
            "D1の基礎知識からD3の比較・統合へ、段階順に表示します。"
        case .cognitiveSkill:
            "知識確認から統合判断へ、思考の進行順に表示します。"
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

    private static func geographyOptions(in items: [StudyFocusItem]) -> [StudyFocusOption] {
        var countryCounts: [String: Int] = [:]
        var regionCounts: [String: Int] = [:]
        var parentScores: [String: [String: Int]] = [:]

        for item in items {
            let countries = countryValues(in: item)
            let regions = regionValues(in: item)
            for country in countries {
                countryCounts[country, default: 0] += 1
            }
            for region in regions {
                regionCounts[region, default: 0] += 1
                for country in countries where region != country {
                    parentScores[region, default: [:]][country, default: 0] += 1
                }
            }
        }

        let countries = countryCounts.keys.sorted { lhs, rhs in
            let lhsRank = rank(lhs, in: countryOrder)
            let rhsRank = rank(rhs, in: countryOrder)
            if lhsRank != rhsRank { return lhsRank < rhsRank }
            if countryCounts[lhs] != countryCounts[rhs] {
                return countryCounts[lhs, default: 0] > countryCounts[rhs, default: 0]
            }
            return japaneseAscending(lhs, rhs)
        }

        var parentByRegion: [String: String] = [:]
        for (region, scores) in parentScores {
            parentByRegion[region] = scores.keys.sorted { lhs, rhs in
                if scores[lhs] != scores[rhs] {
                    return scores[lhs, default: 0] > scores[rhs, default: 0]
                }
                return rank(lhs, in: countryOrder) < rank(rhs, in: countryOrder)
            }.first
        }

        var result: [StudyFocusOption] = []
        for country in countries {
            result.append(
                StudyFocusOption(
                    value: country,
                    questionCount: countryCounts[country, default: 0],
                    kind: .country
                )
            )
            let regions = regionCounts.keys
                .filter {
                    parentByRegion[$0] == country
                        && $0 != country
                        && regionCounts[$0, default: 0] >= 2
                }
                .sorted { lhs, rhs in
                    let lhsRank = rank(lhs, in: regionOrderByCountry[country] ?? [])
                    let rhsRank = rank(rhs, in: regionOrderByCountry[country] ?? [])
                    if lhsRank != rhsRank { return lhsRank < rhsRank }
                    if regionCounts[lhs] != regionCounts[rhs] {
                        return regionCounts[lhs, default: 0] > regionCounts[rhs, default: 0]
                    }
                    return japaneseAscending(lhs, rhs)
                }
            result.append(
                contentsOf: regions.map {
                    StudyFocusOption(
                        value: $0,
                        questionCount: regionCounts[$0, default: 0],
                        kind: .region
                    )
                }
            )
        }

        let orphanRegions = regionCounts.keys
            .filter { parentByRegion[$0] == nil && regionCounts[$0, default: 0] >= 2 }
            .sorted { lhs, rhs in
                if regionCounts[lhs] != regionCounts[rhs] {
                    return regionCounts[lhs, default: 0] > regionCounts[rhs, default: 0]
                }
                return japaneseAscending(lhs, rhs)
            }
        result.append(
            contentsOf: orphanRegions.map {
                StudyFocusOption(value: $0, questionCount: regionCounts[$0, default: 0])
            }
        )
        return result
    }

    static func normalizedValues(
        for dimension: StudyFocusDimension,
        in item: StudyFocusItem
    ) -> Set<String> {
        switch dimension {
        case .geography:
            return Set(countryValues(in: item) + regionValues(in: item))
        case .grapeVariety:
            return Set(item.grapeVarieties.map { normalize($0, for: dimension) }.filter { !$0.isEmpty })
        case .wineType:
            return Set([item.wineType].compactMap { $0 }.map { normalize($0, for: dimension) }.filter { !$0.isEmpty })
        case .knowledgeArea:
            return knowledgeAreaValues(item.category)
        case .difficulty:
            return Set([item.difficulty].compactMap { $0 }.map { normalize($0, for: dimension) }.filter { !$0.isEmpty })
        case .cognitiveSkill:
            return Set([item.cognitiveSkill].compactMap { $0 }.map { normalize($0, for: dimension) }.filter { !$0.isEmpty })
        }
    }

    private static func countryValues(in item: StudyFocusItem) -> [String] {
        GeographyNormalizer.countries(
            explicit: item.countries,
            fallbackGeography: item.geography
        )
    }

    private static func regionValues(in item: StudyFocusItem) -> [String] {
        GeographyNormalizer.regions(
            explicit: item.regions,
            fallbackGeography: item.geography
        )
    }

    private static func knowledgeAreaValues(_ rawValue: String) -> Set<String> {
        let value = trimmed(rawValue)
        var result: Set<String> = []

        if value.contains("自然") { result.insert("自然要因") }
        if value.contains("畑") || value.contains("栽培") || value.contains("ブドウ樹") {
            result.insert("栽培・ブドウ樹")
        }
        if value.contains("ワイナリー") || value.contains("醸造") || value.contains("製法") {
            result.insert("醸造・製法")
        }
        if value.contains("熟成") || value.contains("ブレンド") {
            result.insert("熟成・ブレンド")
        }
        if value.contains("品種") { result.insert("品種") }
        if value.contains("産地") || value.contains("スタイル") {
            result.insert("産地・スタイル")
        }
        if value.contains("法律") || value.contains("表示") { result.insert("法律・表示") }
        if value.contains("商業") || value.contains("価格") || value.contains("品質") {
            result.insert("商業・価格・品質")
        }
        if value.contains("保管") || value.contains("包装") { result.insert("保管・包装") }
        if value.contains("サービス") { result.insert("サービス") }
        if value.contains("欠陥") { result.insert("欠陥") }
        if value.contains("料理") || value.contains("フードペアリング") {
            result.insert("料理との組み合わせ")
        }
        if value.contains("推奨") || value.contains("助言") || value.contains("情報提供") {
            result.insert("情報提供・推奨")
        }
        if value.contains("社会") || value.contains("健康") || value.contains("責任ある飲酒") {
            result.insert("責任ある飲酒")
        }
        if value == "人的要因" || value.contains("自然・人的要因") {
            result.insert("栽培・ブドウ樹")
            result.insert("醸造・製法")
        }
        return result.isEmpty ? Set([value]) : result
    }

    private static func optionPrecedes(
        _ lhs: StudyFocusOption,
        _ rhs: StudyFocusOption,
        dimension: StudyFocusDimension
    ) -> Bool {
        let lhsRank: Int
        let rhsRank: Int
        switch dimension {
        case .grapeVariety:
            let lhsGroup = lhs.groupTitle ?? "地域・固有品種"
            let rhsGroup = rhs.groupTitle ?? "地域・固有品種"
            let lhsGroupRank = rank(lhsGroup, in: grapeGroupOrder)
            let rhsGroupRank = rank(rhsGroup, in: grapeGroupOrder)
            if lhsGroupRank != rhsGroupRank { return lhsGroupRank < rhsGroupRank }
            let order = lhsGroup == "国際品種" ? internationalGrapes : semiInternationalGrapes
            lhsRank = rank(lhs.value, in: order)
            rhsRank = rank(rhs.value, in: order)
        case .wineType:
            lhsRank = rank(lhs.value, in: wineTypeOrder)
            rhsRank = rank(rhs.value, in: wineTypeOrder)
        case .knowledgeArea:
            lhsRank = rank(lhs.value, in: knowledgeAreaOrder)
            rhsRank = rank(rhs.value, in: knowledgeAreaOrder)
        case .difficulty:
            lhsRank = rank(lhs.value, in: difficultyOrder)
            rhsRank = rank(rhs.value, in: difficultyOrder)
        case .cognitiveSkill:
            lhsRank = rank(lhs.value, in: cognitiveSkillOrder)
            rhsRank = rank(rhs.value, in: cognitiveSkillOrder)
        case .geography:
            lhsRank = .max
            rhsRank = .max
        }
        if lhsRank != rhsRank { return lhsRank < rhsRank }
        if lhs.questionCount != rhs.questionCount { return lhs.questionCount > rhs.questionCount }
        return japaneseAscending(lhs.value, rhs.value)
    }

    private static func grapeGroup(for value: String) -> String {
        if internationalGrapes.contains(value) { return "国際品種" }
        if semiInternationalGrapes.contains(value) { return "準国際品種" }
        if value.contains("品種") || value.contains("主要黒ブドウ") { return "品種グループ" }
        return "地域・固有品種"
    }

    private static func normalize(_ value: String, for dimension: StudyFocusDimension) -> String {
        let value = dimension == .geography
            ? GeographyNormalizer.normalize(value)
            : trimmed(value)
        guard !value.isEmpty else { return "" }

        if dimension == .grapeVariety {
            switch value {
            case "シラー", "シラーズ": return "シラー／シラーズ"
            case "グルナッシュ", "ガルナッチャ": return "グルナッシュ／ガルナッチャ"
            case "グレーラ", "グレラ": return "グレーラ"
            case "ムーニエ", "ムニエ": return "ムーニエ"
            case "ピノ・グリ", "ピノ・グリージョ": return "ピノ・グリ／グリージョ"
            case "ジンファンデル", "プリミティーヴォ": return "ジンファンデル／プリミティーヴォ"
            case "シュペートブルグンダー", "ピノ・ネロ": return "ピノ・ノワール"
            case "ティンタ・デ・トロ", "ティンタ・ロリス", "アラゴネス": return "テンプラニーリョ"
            case "アルバリーニョ", "アルヴァリーニョ": return "アルバリーニョ／アルヴァリーニョ"
            case "カリニャン", "カリニェナ": return "カリニャン／カリニェナ"
            case "トウリガ・ナシオナル", "トウリガ・ナシオナルほか", "トゥリガ・ナショナルほか":
                return "トウリガ・ナシオナル"
            case "ヴェルシュリースリングほか": return "ヴェルシュリースリング"
            case "トリンカデイラほか": return "トリンカデイラ"
            case "マスカット", "モスカート・ビアンコ", "モスカテル",
                 "ミュスカ・ブラン・ア・プティ・グラン",
                 "マスカット・ブラン・ア・プティ・グラン",
                 "マスカット・ア・プティ・グラン・ルージュ":
                return "マスカット系"
            default: return value
            }
        }

        guard dimension == .wineType else { return value }
        if value == "全般" || value.contains("全般") || value == "甘口ワイン" {
            return "共通・横断"
        }
        if value.contains("酒精強化") { return "酒精強化ワイン" }
        if value.contains("非発泡性") { return "非発泡性ワイン" }
        if value.contains("発泡性") { return "発泡性ワイン" }
        return "非発泡性ワイン"
    }

    private static func trimmed(_ value: String) -> String {
        value.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private static func rank(_ value: String, in order: [String]) -> Int {
        order.firstIndex(of: value) ?? .max
    }

    private static func japaneseAscending(_ lhs: String, _ rhs: String) -> Bool {
        let order = lhs.compare(
            rhs,
            options: [.caseInsensitive, .numeric],
            range: nil,
            locale: japaneseLocale
        )
        return order == .orderedSame ? lhs < rhs : order == .orderedAscending
    }
}
