import Foundation

struct AtlasPhoto: Decodable, Identifiable {
    let regionID: String
    let assetName: String
    let filename: String
    let title: String
    let altText: String
    let author: String
    let sourceURL: String
    let license: String
    let licenseURL: String
    let changes: String
    let checkedAt: String
    let sha256: String
    let width: Int
    let height: Int

    var id: String { regionID }
}

/// Bundled metadata only. Missing or malformed data never prevents studying.
final class AtlasMediaStore {
    static let shared = AtlasMediaStore()
    let loadError: String?
    private let photosByRegion: [String: AtlasPhoto]

    convenience init(bundle: Bundle = .main) {
#if DEBUG
        if ProcessInfo.processInfo.arguments.contains("-UITestAtlasMediaLoadFailure") {
            self.init(data: nil)
            return
        }
#endif
        let url = bundle.url(forResource: "atlas_media", withExtension: "json")
            ?? bundle.url(forResource: "atlas_media", withExtension: "json", subdirectory: "AtlasData")
        self.init(data: url.flatMap { try? Data(contentsOf: $0) })
    }

    init(data: Data?) {
        if let data,
           let catalog = try? JSONDecoder().decode(Catalog.self, from: data),
           Self.isValid(catalog) {
            photosByRegion = Dictionary(uniqueKeysWithValues: catalog.photos.map { ($0.regionID, $0) })
            loadError = nil
        } else {
            photosByRegion = [:]
            loadError = "産地写真を読み込めませんでした。本文と学習は引き続き利用できます。"
        }
    }

    func photo(for regionID: String) -> AtlasPhoto? { photosByRegion[regionID] }

    private struct Catalog: Decodable {
        let schemaVersion: Int
        let sourceHash: String
        let photos: [AtlasPhoto]
    }

    private static func isValid(_ catalog: Catalog) -> Bool {
        guard catalog.schemaVersion == 1, isHash(catalog.sourceHash),
              !catalog.photos.isEmpty,
              Set(catalog.photos.map(\.regionID)).count == catalog.photos.count else { return false }
        return catalog.photos.allSatisfy { photo in
            let required = [photo.regionID, photo.assetName, photo.filename, photo.title,
                            photo.altText, photo.author, photo.license, photo.changes, photo.checkedAt]
            return required.allSatisfy { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
                && photo.assetName == "atlas_\(photo.regionID)"
                && photo.width > 0 && photo.height > 0 && isHash(photo.sha256)
                && isHTTPS(photo.sourceURL) && isHTTPS(photo.licenseURL)
        }
    }

    private static func isHash(_ value: String) -> Bool {
        value.count == 64 && value.unicodeScalars.allSatisfy {
            (48...57).contains($0.value) || (65...70).contains($0.value) || (97...102).contains($0.value)
        }
    }

    private static func isHTTPS(_ value: String) -> Bool {
        guard let url = URLComponents(string: value), url.scheme?.lowercased() == "https",
              let host = url.host, !host.isEmpty,
              url.user == nil, url.password == nil else { return false }
        return url.url != nil
    }
}
