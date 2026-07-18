import Foundation

struct RegionMapPack: Decodable, Hashable, Sendable {
    let schemaVersion: Int
    let sourceHash: String
    let questionPackSourceHash: String
    let referencePackSourceHash: String
    let mapCount: Int
    let maps: [RegionMapDocument]
    let sources: [RegionMapSource]
}

enum RegionMapLevel: String, Decodable, Hashable, Sendable {
    case country
    case subregion
}

struct RegionMapDocument: Decodable, Identifiable, Hashable, Sendable {
    let id: String
    let level: RegionMapLevel
    let country: String
    let nameJapanese: String
    let nameOriginal: String
    let assetName: String
    let aspectRatio: Double
    let sourceIDs: [String]
    let regions: [MapRegion]
}

struct MapRegion: Decodable, Identifiable, Hashable, Sendable {
    let id: String
    let nameJapanese: String
    let nameOriginal: String
    let focusValues: [String]
    let position: NormalizedPoint
    let labelOffset: NormalizedPoint
    let termIDs: [String]
    let childMapID: String?
    let polygons: [NormalizedPolygon]
    let comparison: RegionComparisonProfile
}

enum RegionComparisonAxis: String, CaseIterable, Identifiable, Hashable, Sendable {
    case climateInfluence
    case temperatureRainfallRisks
    case soils
    case grapeVarieties
    case viticulture
    case winemakingMaturation
    case wineStyles
    case qualityPriceFactors
    case lawLabels

    var id: String { rawValue }

    var title: String {
        switch self {
        case .climateInfluence: "緯度・気候影響"
        case .temperatureRainfallRisks: "気温・降雨・主要リスク"
        case .soils: "土壌"
        case .grapeVarieties: "主要品種"
        case .viticulture: "栽培判断"
        case .winemakingMaturation: "醸造・熟成"
        case .wineStyles: "代表スタイル"
        case .qualityPriceFactors: "品質・価格要因"
        case .lawLabels: "法律・表示"
        }
    }
}

struct RegionComparisonFact: Decodable, Hashable, Sendable {
    let summary: String
    let keywords: [String]
    let sourceIDs: [String]
    let checkedAt: String
    let effectiveDate: String

    func keywordsCompared(to other: RegionComparisonFact) -> RegionComparisonKeywords {
        let own = Set(keywords)
        let theirs = Set(other.keywords)
        return RegionComparisonKeywords(
            common: keywords.filter(theirs.contains),
            firstOnly: keywords.filter { !theirs.contains($0) },
            secondOnly: other.keywords.filter { !own.contains($0) }
        )
    }
}

struct RegionComparisonKeywords: Equatable, Hashable, Sendable {
    let common: [String]
    let firstOnly: [String]
    let secondOnly: [String]
}

struct RegionComparisonProfile: Decodable, Hashable, Sendable {
    let climateInfluence: RegionComparisonFact
    let temperatureRainfallRisks: RegionComparisonFact
    let soils: RegionComparisonFact
    let grapeVarieties: RegionComparisonFact
    let viticulture: RegionComparisonFact
    let winemakingMaturation: RegionComparisonFact
    let wineStyles: RegionComparisonFact
    let qualityPriceFactors: RegionComparisonFact
    let lawLabels: RegionComparisonFact

    func fact(for axis: RegionComparisonAxis) -> RegionComparisonFact {
        switch axis {
        case .climateInfluence: climateInfluence
        case .temperatureRainfallRisks: temperatureRainfallRisks
        case .soils: soils
        case .grapeVarieties: grapeVarieties
        case .viticulture: viticulture
        case .winemakingMaturation: winemakingMaturation
        case .wineStyles: wineStyles
        case .qualityPriceFactors: qualityPriceFactors
        case .lawLabels: lawLabels
        }
    }
}

struct NormalizedPoint: Decodable, Hashable, Sendable {
    let x: Double
    let y: Double
}

struct NormalizedPolygon: Decodable, Hashable, Sendable {
    let points: [NormalizedPoint]

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        points = try container.decode([NormalizedPoint].self)
    }
}

struct RegionMapSource: Decodable, Identifiable, Hashable, Sendable {
    let id: String
    let name: String
    let url: String?
    let license: String
    let checkedAt: String
    let note: String
}
