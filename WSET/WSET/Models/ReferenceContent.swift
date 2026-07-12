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

    let pack: ReferencePack?
    let loadError: String?

    private let termsByID: [String: ReferenceTerm]
    private let termsByQuestionID: [String: [ReferenceTerm]]
    private let systemsByID: [String: WineClassificationSystem]
    private let sourcesByID: [String: ReferenceSource]

    init(bundle: Bundle = .main) {
        do {
            guard let url = bundle.url(forResource: "reference_pack", withExtension: "json")
                ?? bundle.url(
                    forResource: "reference_pack",
                    withExtension: "json",
                    subdirectory: "ReferenceData"
                )
            else {
                throw CocoaError(.fileNoSuchFile)
            }
            let decoded = try JSONDecoder().decode(
                ReferencePack.self,
                from: Data(contentsOf: url)
            )
            guard decoded.schemaVersion == 1,
                  decoded.termCount == decoded.terms.count,
                  decoded.classificationEntryCount == decoded.classificationEntries.count
            else {
                throw CocoaError(.fileReadCorruptFile)
            }
            pack = decoded
            loadError = nil
            termsByID = Dictionary(uniqueKeysWithValues: decoded.terms.map { ($0.id, $0) })
            systemsByID = Dictionary(
                uniqueKeysWithValues: decoded.classificationSystems.map { ($0.id, $0) }
            )
            sourcesByID = Dictionary(uniqueKeysWithValues: decoded.sources.map { ($0.id, $0) })
            var grouped: [String: [ReferenceTerm]] = [:]
            for term in decoded.terms {
                for questionID in term.questionIDs {
                    grouped[questionID, default: []].append(term)
                }
            }
            termsByQuestionID = grouped.mapValues {
                $0.sorted {
                    if $0.category != $1.category { return $0.category < $1.category }
                    return $0.nameJapanese.localizedStandardCompare($1.nameJapanese)
                        == .orderedAscending
                }
            }
        } catch {
            pack = nil
            loadError = "用語辞書データを読み込めませんでした。"
            termsByID = [:]
            termsByQuestionID = [:]
            systemsByID = [:]
            sourcesByID = [:]
        }
    }

    var terms: [ReferenceTerm] { pack?.terms ?? [] }
    var classificationSystems: [WineClassificationSystem] {
        pack?.classificationSystems ?? []
    }
    var classificationEntries: [WineClassificationEntry] {
        pack?.classificationEntries ?? []
    }

    func term(id: String) -> ReferenceTerm? { termsByID[id] }
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

    init(termID: String) {
        self.termID = termID
        isBookmarked = false
        lastViewedAt = nil
        viewCount = 0
    }

    func recordView(at date: Date = .now) {
        lastViewedAt = date
        viewCount += 1
    }
}
