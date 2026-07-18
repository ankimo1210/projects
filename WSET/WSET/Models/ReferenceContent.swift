import Foundation
import SwiftData

struct ReferencePack: Decodable {
    let schemaVersion: Int
    let sourceHash: String
    let questionPackSourceHash: String
    let termCount: Int
    let classificationEntryCount: Int
    let terms: [ReferenceTerm]
    let classificationSystems: [WineClassificationSystem]
    let classificationEntries: [WineClassificationEntry]
    let sources: [ReferenceSource]
    let termIDMigrations: [String: String]?
}

struct ReferenceTerm: Decodable, Identifiable, Hashable {
    let id: String
    let nameJapanese: String
    let nameEnglish: String?
    let nameFrench: String?
    let reading: String?
    let category: String
    let summary: String
    let description: String
    let country: String?
    let region: String?
    let labels: [String]
    let relatedTermIDs: [String]
    let aliases: [String]
    let questionIDs: [String]
    let sourceID: String
    let checkedAt: String

    var searchText: String {
        [
            nameJapanese,
            nameEnglish,
            nameFrench,
            reading,
            summary,
            description,
            country,
            region,
            labels.joined(separator: " "),
            aliases.joined(separator: " "),
        ]
        .compactMap { $0 }
        .joined(separator: "\n")
    }

    func matches(_ query: String) -> Bool {
        let normalizedQuery = ReferenceSearch.normalize(query)
        return normalizedQuery.isEmpty
            || ReferenceSearch.normalize(searchText).contains(normalizedQuery)
    }
}

struct WineClassificationSystem: Decodable, Identifiable, Hashable {
    let id: String
    let region: String
    let nameJapanese: String
    let nameEnglish: String?
    let nameFrench: String?
    let summary: String
    let effectiveDate: String
    let sourceID: String
}

struct WineClassificationEntry: Decodable, Identifiable, Hashable {
    let id: String
    let systemID: String
    let nameJapanese: String
    let nameOriginal: String
    let tier: String
    let village: String
    let subregion: String
    let entryType: String
    let termID: String
    let notes: String?
    let sourceID: String

    var searchText: String {
        [nameJapanese, nameOriginal, tier, village, subregion, entryType, notes]
            .compactMap { $0 }
            .joined(separator: "\n")
    }

    func matches(_ query: String) -> Bool {
        let normalizedQuery = ReferenceSearch.normalize(query)
        return normalizedQuery.isEmpty
            || ReferenceSearch.normalize(searchText).contains(normalizedQuery)
    }
}

struct ReferenceSource: Decodable, Identifiable, Hashable {
    let id: String
    let name: String
    let url: String
    let effectiveDate: String
    let checkedAt: String
}

enum ReferenceSearch {
    static func normalize(_ value: String) -> String {
        value
            .folding(
                options: [.caseInsensitive, .diacriticInsensitive, .widthInsensitive],
                locale: Locale(identifier: "ja_JP")
            )
            .replacingOccurrences(of: "・", with: "")
            .replacingOccurrences(of: " ", with: "")
            .replacingOccurrences(of: "　", with: "")
            .lowercased()
    }
}

final class ReferenceStore {
    static let shared = ReferenceStore()

    private struct LoadedContent {
        let pack: ReferencePack
        let termsByID: [String: ReferenceTerm]
        let termsByQuestionID: [String: [ReferenceTerm]]
        let systemsByID: [String: WineClassificationSystem]
        let sourcesByID: [String: ReferenceSource]
    }

    let pack: ReferencePack?
    let loadError: String?

    private let termsByID: [String: ReferenceTerm]
    private let termsByQuestionID: [String: [ReferenceTerm]]
    private let systemsByID: [String: WineClassificationSystem]
    private let sourcesByID: [String: ReferenceSource]
    let termIDMigrations: [String: String]

    convenience init(bundle: Bundle = .main) {
        self.init(
            result: Result {
                guard let url = bundle.url(
                    forResource: "reference_pack",
                    withExtension: "json"
                ) ?? bundle.url(
                    forResource: "reference_pack",
                    withExtension: "json",
                    subdirectory: "ReferenceData"
                ) else {
                    throw CocoaError(.fileNoSuchFile)
                }
                return try Self.load(Data(contentsOf: url))
            }
        )
    }

    convenience init(data: Data) {
        self.init(result: Result { try Self.load(data) })
    }

    private init(result: Result<LoadedContent, Error>) {
        switch result {
        case let .success(content):
            pack = content.pack
            loadError = nil
            termsByID = content.termsByID
            termsByQuestionID = content.termsByQuestionID
            systemsByID = content.systemsByID
            sourcesByID = content.sourcesByID
            termIDMigrations = content.pack.termIDMigrations ?? [:]
        case .failure:
            pack = nil
            loadError = "用語辞書データを読み込めませんでした。"
            termsByID = [:]
            termsByQuestionID = [:]
            systemsByID = [:]
            sourcesByID = [:]
            termIDMigrations = [:]
        }
    }

    private static func load(_ data: Data) throws -> LoadedContent {
        let decoded = try JSONDecoder().decode(ReferencePack.self, from: data)
        let termIDs = Set(decoded.terms.map(\.id))
        let migrations = decoded.termIDMigrations ?? [:]
        guard decoded.schemaVersion == 1,
              decoded.termCount == decoded.terms.count,
              decoded.classificationEntryCount == decoded.classificationEntries.count,
              hasUniqueIDs(decoded.terms.map(\.id)),
              hasUniqueIDs(decoded.classificationSystems.map(\.id)),
              hasUniqueIDs(decoded.classificationEntries.map(\.id)),
              hasUniqueIDs(decoded.sources.map(\.id)),
              Set(migrations.keys).isDisjoint(with: termIDs),
              Set(migrations.values).isSubset(of: termIDs),
              Set(migrations.keys).isDisjoint(with: Set(migrations.values)),
              migrations.allSatisfy({ !$0.key.isEmpty && !$0.value.isEmpty })
        else {
            throw CocoaError(.fileReadCorruptFile)
        }

        let termsByID = Dictionary(
            decoded.terms.map { ($0.id, $0) },
            uniquingKeysWith: { first, _ in first }
        )
        let systemsByID = Dictionary(
            decoded.classificationSystems.map { ($0.id, $0) },
            uniquingKeysWith: { first, _ in first }
        )
        let sourcesByID = Dictionary(
            decoded.sources.map { ($0.id, $0) },
            uniquingKeysWith: { first, _ in first }
        )
        var grouped: [String: [ReferenceTerm]] = [:]
        for term in decoded.terms {
            for questionID in term.questionIDs {
                grouped[questionID, default: []].append(term)
            }
        }
        let termsByQuestionID = grouped.mapValues {
            $0.sorted {
                if $0.category != $1.category { return $0.category < $1.category }
                return $0.nameJapanese.localizedStandardCompare($1.nameJapanese)
                    == .orderedAscending
            }
        }
        return LoadedContent(
            pack: decoded,
            termsByID: termsByID,
            termsByQuestionID: termsByQuestionID,
            systemsByID: systemsByID,
            sourcesByID: sourcesByID
        )
    }

    private static func hasUniqueIDs(_ ids: [String]) -> Bool {
        Set(ids).count == ids.count
    }

    var terms: [ReferenceTerm] { pack?.terms ?? [] }
    var classificationSystems: [WineClassificationSystem] {
        pack?.classificationSystems ?? []
    }
    var classificationEntries: [WineClassificationEntry] {
        pack?.classificationEntries ?? []
    }

    func canonicalTermID(for id: String) -> String {
        termIDMigrations[id] ?? id
    }

    func term(id: String) -> ReferenceTerm? {
        termsByID[canonicalTermID(for: id)]
    }
    func terms(forQuestionID questionID: String) -> [ReferenceTerm] {
        termsByQuestionID[questionID] ?? []
    }
    func system(id: String) -> WineClassificationSystem? { systemsByID[id] }
    func source(id: String) -> ReferenceSource? { sourcesByID[id] }
}

@Model
final class ReferenceTermProgress {
    @Attribute(.unique) var termID: String
    var isBookmarked: Bool
    var lastViewedAt: Date?
    var viewCount: Int
    var reviewDueDate: Date? = nil
    var reviewIntervalDays: Int = 0
    var reviewAttemptCount: Int = 0
    var reviewCorrectCount: Int = 0
    var lastReviewedAt: Date? = nil
    var lastReviewWasCorrect: Bool? = nil

    init(termID: String) {
        self.termID = termID
        isBookmarked = false
        lastViewedAt = nil
        viewCount = 0
        reviewDueDate = nil
        reviewIntervalDays = 0
        reviewAttemptCount = 0
        reviewCorrectCount = 0
        lastReviewedAt = nil
        lastReviewWasCorrect = nil
    }

    func recordView(at date: Date = .now) {
        lastViewedAt = date
        viewCount += 1
    }

    var reviewAccuracy: Double? {
        guard reviewAttemptCount > 0 else { return nil }
        return Double(reviewCorrectCount) / Double(reviewAttemptCount)
    }

    func isReviewDue(at date: Date = .now) -> Bool {
        guard let reviewDueDate else { return true }
        return reviewDueDate <= date
    }

    func recordReview(
        isCorrect: Bool,
        at date: Date = .now,
        calendar: Calendar = .current
    ) {
        reviewAttemptCount += 1
        reviewCorrectCount += isCorrect ? 1 : 0
        lastReviewedAt = date
        lastReviewWasCorrect = isCorrect

        if isCorrect {
            reviewIntervalDays = max(
                1,
                reviewIntervalDays == 0 ? 1 : min(reviewIntervalDays * 2, 60)
            )
            reviewDueDate = calendar.date(
                byAdding: .day,
                value: reviewIntervalDays,
                to: date
            ) ?? date
        } else {
            reviewIntervalDays = 0
            reviewDueDate = calendar.date(byAdding: .minute, value: 10, to: date) ?? date
        }
    }
}
