import Foundation

nonisolated enum GeographyNormalizer {
    static let countryOrder = [
        "フランス", "イタリア", "スペイン", "ポルトガル", "ドイツ", "オーストリア",
        "米国", "オーストラリア", "ニュージーランド", "南アフリカ", "チリ",
        "アルゼンチン", "カナダ", "ハンガリー", "ギリシャ", "英国",
    ]
    private static let knownCountries = Set(countryOrder)

    private static let countryAliases: [String: String] = [
        "アメリカ": "米国",
        "アメリカ合衆国": "米国",
        "United States": "米国",
        "United States of America": "米国",
        "US": "米国",
        "USA": "米国",
        "イギリス": "英国",
        "United Kingdom": "英国",
        "Great Britain": "英国",
        "UK": "英国",
        "南ア": "南アフリカ",
        "南ア共和国": "南アフリカ",
        "South Africa": "南アフリカ",
        "New Zealand": "ニュージーランド",
        "Australia": "オーストラリア",
        "Argentina": "アルゼンチン",
        "Austria": "オーストリア",
        "Canada": "カナダ",
        "Chile": "チリ",
        "France": "フランス",
        "Germany": "ドイツ",
        "Greece": "ギリシャ",
        "Hungary": "ハンガリー",
        "Italy": "イタリア",
        "Portugal": "ポルトガル",
        "Spain": "スペイン",
    ]

    private static let regionAliases: [String: String] = [
        "サンルーカル": "サンルーカル・デ・バラメダ",
        "サンルーカル・デ・バラメーダ": "サンルーカル・デ・バラメダ",
        "サン・テミリオン": "サンテミリオン",
        "ミュスカ・ドゥ・ボーム・ドゥ・ヴニーズ": "ミュスカ・ド・ボーム・ド・ヴニーズ",
        "ミュスカ・ド・ボーム・ドゥ・ヴニーズ": "ミュスカ・ド・ボーム・ド・ヴニーズ",
        "ヴァレ・ドゥ・ラ・マルヌ": "ヴァレ・ド・ラ・マルヌ",
        "コート・ドゥ・ボーヌ": "コート・ド・ボーヌ",
        "コート・ドゥ・ニュイ": "コート・ド・ニュイ",
        "リベラ・デル・デュエロ": "リベラ・デル・ドゥエロ",
        "ウィラメット・バレー": "ウィラメット・ヴァレー",
        "ナパ・バレー": "ナパ・ヴァレー",
        "バロッサ・バレー": "バロッサ・ヴァレー",
        "ハンター・バレー": "ハンター・ヴァレー",
        "クレア・バレー": "クレア・ヴァレー",
        "イーデン・バレー": "イーデン・ヴァレー",
        "ウコ・バレー": "ウコ・ヴァレー",
        "オカナガン・バレー": "オカナガン・ヴァレー",
    ]

    /// Compatibility entry point used by region-map data.
    static func canonical(_ value: String) -> String {
        normalize(value)
    }

    /// Compatibility entry point used by region-map data.
    static func canonicalValues(_ values: [String]) -> [String] {
        unique(values.map { canonical($0) }.filter { !$0.isEmpty })
    }

    static func normalizeCountry(_ value: String) -> String {
        let normalized = cleaned(value)
        guard !normalized.isEmpty else { return "" }
        return countryAliases[normalized] ?? normalized
    }

    static func normalizeRegion(_ value: String) -> String {
        let normalized = cleaned(value)
        guard !normalized.isEmpty else { return "" }
        return regionAliases[normalized] ?? normalized
    }

    static func normalize(_ value: String) -> String {
        let country = normalizeCountry(value)
        if isKnownCountry(country) {
            return country
        }
        return normalizeRegion(value)
    }

    static func isKnownCountry(_ value: String) -> Bool {
        knownCountries.contains(normalizeCountry(value))
    }

    static func countries(explicit: [String]?, fallbackGeography: [String]) -> [String] {
        if let explicit, !explicit.isEmpty {
            return unique(explicit.map { normalizeCountry($0) }.filter { !$0.isEmpty })
        }
        return unique(
            fallbackGeography
                .map { normalizeCountry($0) }
                .filter { !$0.isEmpty && isKnownCountry($0) }
        )
    }

    static func regions(explicit: [String]?, fallbackGeography: [String]) -> [String] {
        let source = explicit?.isEmpty == false ? explicit ?? [] : fallbackGeography
        return unique(
            source.compactMap { value in
                let country = normalizeCountry(value)
                guard !isKnownCountry(country) else { return nil }
                let region = normalizeRegion(value)
                return region.isEmpty ? nil : region
            }
        )
    }

    private static func cleaned(_ value: String) -> String {
        value
            .precomposedStringWithCompatibilityMapping
            .replacingOccurrences(of: "\u{3000}", with: " ")
            .split(whereSeparator: { $0.isWhitespace })
            .joined(separator: " ")
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private static func unique(_ values: [String]) -> [String] {
        var seen: Set<String> = []
        return values.filter { seen.insert($0).inserted }
    }
}
