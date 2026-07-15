import Foundation

nonisolated enum HSKSyllabusVersion: String, Codable, CaseIterable, Identifiable, Sendable {
    case hsk2 = "hsk2.0"
    case hsk3 = "hsk3.0"

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .hsk2: "HSK 2.0"
        case .hsk3: "HSK 3.0"
        }
    }

    func supports(_ level: HSKLevel) -> Bool {
        switch (self, level) {
        case (.hsk2, .advanced): false
        default: true
        }
    }
}

nonisolated enum HSKLevel: String, Codable, CaseIterable, Identifiable, Comparable, Sendable {
    case level1 = "1"
    case level2 = "2"
    case level3 = "3"
    case level4 = "4"
    case level5 = "5"
    case level6 = "6"
    case advanced = "7-9"

    var id: String { rawValue }

    var displayName: String {
        self == .advanced ? "HSK 7–9" : "HSK \(rawValue)"
    }

    var sortOrder: Int {
        switch self {
        case .level1: 1
        case .level2: 2
        case .level3: 3
        case .level4: 4
        case .level5: 5
        case .level6: 6
        case .advanced: 7
        }
    }

    var levelsThroughSelf: [HSKLevel] {
        Self.allCases.filter { $0 <= self }
    }

    static func < (lhs: HSKLevel, rhs: HSKLevel) -> Bool {
        lhs.sortOrder < rhs.sortOrder
    }
}

nonisolated struct SyllabusMapping: Codable, Hashable, Sendable {
    let syllabusVersion: HSKSyllabusVersion
    let level: HSKLevel
}

nonisolated enum LearningSkill: String, Codable, CaseIterable, Identifiable, Sendable {
    case vocabulary
    case pronunciation
    case listening
    case reading
    case grammar
    case writing
    case speaking
    case translation

    var id: String { rawValue }
}

nonisolated struct ContentSource: Codable, Hashable, Sendable {
    let title: String
    let url: String
    let license: String?
}

nonisolated struct ContentPackDescriptor: Codable, Hashable, Identifiable, Sendable {
    let id: String
    let syllabusVersion: HSKSyllabusVersion
    let level: HSKLevel
    let resource: String
    let expectedVocabularyCount: Int

    var mapping: SyllabusMapping {
        SyllabusMapping(syllabusVersion: syllabusVersion, level: level)
    }
}

nonisolated struct ContentManifest: Codable, Hashable, Sendable {
    static let supportedSchemaVersion = 1

    let schemaVersion: Int
    let contentVersion: String
    let packs: [ContentPackDescriptor]

    func descriptors(
        for syllabusVersion: HSKSyllabusVersion,
        levels: Set<HSKLevel>
    ) -> [ContentPackDescriptor] {
        packs
            .filter {
                $0.syllabusVersion == syllabusVersion && levels.contains($0.level)
            }
            .sorted { $0.level < $1.level }
    }
}

nonisolated struct ExampleSentence: Codable, Hashable, Identifiable, Sendable {
    let id: String
    let hanzi: String
    let pinyin: String
    let japanese: String
}

nonisolated struct VocabularyItem: Codable, Hashable, Identifiable, Sendable {
    let id: String
    let officialIndex: Int
    let hanzi: String
    let traditional: String?
    let pinyin: String
    let partOfSpeech: String?
    let japanese: [String]
    let examples: [ExampleSentence]
    let tags: [String]

    init(
        id: String,
        officialIndex: Int,
        hanzi: String,
        traditional: String? = nil,
        pinyin: String,
        partOfSpeech: String? = nil,
        japanese: [String] = [],
        examples: [ExampleSentence] = [],
        tags: [String] = []
    ) {
        self.id = id
        self.officialIndex = officialIndex
        self.hanzi = hanzi
        self.traditional = traditional
        self.pinyin = pinyin
        self.partOfSpeech = partOfSpeech
        self.japanese = japanese
        self.examples = examples
        self.tags = tags
    }

    private enum CodingKeys: String, CodingKey {
        case id
        case officialIndex
        case hanzi
        case traditional
        case pinyin
        case partOfSpeech
        case japanese
        case examples
        case tags
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        officialIndex = try container.decode(Int.self, forKey: .officialIndex)
        hanzi = try container.decode(String.self, forKey: .hanzi)
        traditional = try container.decodeIfPresent(String.self, forKey: .traditional)
        pinyin = try container.decode(String.self, forKey: .pinyin)
        partOfSpeech = try container.decodeIfPresent(String.self, forKey: .partOfSpeech)
        japanese = try container.decodeIfPresent([String].self, forKey: .japanese) ?? []
        examples = try container.decodeIfPresent([ExampleSentence].self, forKey: .examples) ?? []
        tags = try container.decodeIfPresent([String].self, forKey: .tags) ?? []
    }
}

nonisolated struct LevelContentPack: Codable, Hashable, Identifiable, Sendable {
    static let supportedSchemaVersion = 1

    let schemaVersion: Int
    let id: String
    let contentVersion: String
    let syllabusVersion: HSKSyllabusVersion
    let level: HSKLevel
    let source: ContentSource
    let skills: [LearningSkill]
    let vocabulary: [VocabularyItem]

    var mapping: SyllabusMapping {
        SyllabusMapping(syllabusVersion: syllabusVersion, level: level)
    }

    init(
        schemaVersion: Int = Self.supportedSchemaVersion,
        id: String,
        contentVersion: String,
        syllabusVersion: HSKSyllabusVersion,
        level: HSKLevel,
        source: ContentSource,
        skills: [LearningSkill] = [.vocabulary],
        vocabulary: [VocabularyItem]
    ) {
        self.schemaVersion = schemaVersion
        self.id = id
        self.contentVersion = contentVersion
        self.syllabusVersion = syllabusVersion
        self.level = level
        self.source = source
        self.skills = skills
        self.vocabulary = vocabulary
    }

    private enum CodingKeys: String, CodingKey {
        case schemaVersion
        case id
        case contentVersion
        case syllabusVersion
        case level
        case source
        case skills
        case vocabulary
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        schemaVersion = try container.decode(Int.self, forKey: .schemaVersion)
        id = try container.decode(String.self, forKey: .id)
        contentVersion = try container.decode(String.self, forKey: .contentVersion)
        syllabusVersion = try container.decode(HSKSyllabusVersion.self, forKey: .syllabusVersion)
        level = try container.decode(HSKLevel.self, forKey: .level)
        source = try container.decode(ContentSource.self, forKey: .source)
        skills = try container.decodeIfPresent([LearningSkill].self, forKey: .skills) ?? [.vocabulary]
        vocabulary = try container.decode([VocabularyItem].self, forKey: .vocabulary)
    }
}

nonisolated struct ContentCatalog: Sendable {
    let manifest: ContentManifest
    let packs: [LevelContentPack]
    let validationReport: ContentValidationReport

    var vocabulary: [VocabularyItem] {
        packs.flatMap(\.vocabulary)
    }
}
