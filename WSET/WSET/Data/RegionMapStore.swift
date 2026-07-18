import Foundation

enum RegionMapStoreError: Error, Equatable {
    case missingFile
    case unsupportedSchema(Int)
    case invalidCount
    case duplicateIdentifier(String)
    case invalidPoint(String)
    case brokenReference(String)
    case invalidComparison(String)
}

final class RegionMapStore {
    static let shared = RegionMapStore()

    let pack: RegionMapPack?
    let loadError: String?

    private let mapsByID: [String: RegionMapDocument]
    private let regionsByID: [String: MapRegion]
    private let sourcesByID: [String: RegionMapSource]

    convenience init(bundle: Bundle = .main) {
        let url = bundle.url(forResource: "region_map_pack", withExtension: "json")
            ?? bundle.url(
                forResource: "region_map_pack",
                withExtension: "json",
                subdirectory: "MapData"
            )
        let result: Result<Data, Error>
        if let url {
            result = Result { try Data(contentsOf: url) }
        } else {
            result = .failure(RegionMapStoreError.missingFile)
        }
        self.init(dataResult: result)
    }

    convenience init(data: Data?) {
        let result: Result<Data, Error> = data.map { .success($0) }
            ?? .failure(RegionMapStoreError.missingFile)
        self.init(dataResult: result)
    }

    private init(dataResult: Result<Data, Error>) {
        do {
            let data = try dataResult.get()
            let decoded = try JSONDecoder().decode(RegionMapPack.self, from: data)
            try Self.validate(decoded)
            pack = decoded
            loadError = nil
            mapsByID = Dictionary(uniqueKeysWithValues: decoded.maps.map { ($0.id, $0) })
            regionsByID = Dictionary(
                uniqueKeysWithValues: decoded.maps.flatMap(\.regions).map { ($0.id, $0) }
            )
            sourcesByID = Dictionary(uniqueKeysWithValues: decoded.sources.map { ($0.id, $0) })
        } catch {
            pack = nil
            loadError = "産地マップデータを読み込めませんでした。"
            mapsByID = [:]
            regionsByID = [:]
            sourcesByID = [:]
        }
    }

    var maps: [RegionMapDocument] { pack?.maps ?? [] }

    func map(id: String) -> RegionMapDocument? { mapsByID[id] }
    func region(id: String) -> MapRegion? { regionsByID[id] }
    func source(id: String) -> RegionMapSource? { sourcesByID[id] }

    private static func validate(_ pack: RegionMapPack) throws {
        guard pack.schemaVersion == 2 else {
            throw RegionMapStoreError.unsupportedSchema(pack.schemaVersion)
        }
        guard pack.mapCount == pack.maps.count,
              !pack.sourceHash.isEmpty,
              !pack.questionPackSourceHash.isEmpty,
              !pack.referencePackSourceHash.isEmpty
        else {
            throw RegionMapStoreError.invalidCount
        }
        let mapIDs = try uniqueIDs(pack.maps.map(\.id))
        let sourceIDs = try uniqueIDs(pack.sources.map(\.id))
        var regionIDs: Set<String> = []
        for map in pack.maps {
            guard map.aspectRatio > 0, !map.regions.isEmpty else {
                throw RegionMapStoreError.invalidCount
            }
            guard Set(map.sourceIDs).isSubset(of: sourceIDs) else {
                throw RegionMapStoreError.brokenReference(map.id)
            }
            for region in map.regions {
                guard regionIDs.insert(region.id).inserted else {
                    throw RegionMapStoreError.duplicateIdentifier(region.id)
                }
                guard (0...1).contains(region.position.x),
                      (0...1).contains(region.position.y),
                      (-1...1).contains(region.labelOffset.x),
                      (-1...1).contains(region.labelOffset.y)
                else {
                    throw RegionMapStoreError.invalidPoint(region.id)
                }
                guard Set(region.focusValues).count == region.focusValues.count,
                      Set(region.termIDs).count == region.termIDs.count
                else {
                    throw RegionMapStoreError.duplicateIdentifier(region.id)
                }
                if let childMapID = region.childMapID, !mapIDs.contains(childMapID) {
                    throw RegionMapStoreError.brokenReference(region.id)
                }
                for axis in RegionComparisonAxis.allCases {
                    let fact = region.comparison.fact(for: axis)
                    guard !fact.summary.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
                          !fact.keywords.isEmpty,
                          !fact.sourceIDs.isEmpty,
                          Set(fact.keywords).count == fact.keywords.count,
                          Set(fact.sourceIDs).count == fact.sourceIDs.count,
                          Set(fact.sourceIDs).isSubset(of: sourceIDs),
                          isISODate(fact.checkedAt),
                          isISODate(fact.effectiveDate)
                    else {
                        throw RegionMapStoreError.invalidComparison(
                            "\(region.id).\(axis.rawValue)"
                        )
                    }
                }
                for polygon in region.polygons {
                    guard polygon.points.count >= 3,
                          polygon.points.allSatisfy({
                              (0...1).contains($0.x) && (0...1).contains($0.y)
                          })
                    else {
                        throw RegionMapStoreError.invalidPoint(region.id)
                    }
                }
            }
        }
    }

    private static func uniqueIDs(_ identifiers: [String]) throws -> Set<String> {
        var result: Set<String> = []
        for identifier in identifiers {
            guard !identifier.isEmpty, result.insert(identifier).inserted else {
                throw RegionMapStoreError.duplicateIdentifier(identifier)
            }
        }
        return result
    }

    private static func isISODate(_ value: String) -> Bool {
        guard value.range(
            of: #"^\d{4}-\d{2}-\d{2}$"#,
            options: .regularExpression
        ) != nil else { return false }
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        formatter.dateFormat = "yyyy-MM-dd"
        formatter.isLenient = false
        return formatter.date(from: value) != nil
    }
}
