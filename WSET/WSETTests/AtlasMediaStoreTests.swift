import XCTest
@testable import WSET

final class AtlasMediaStoreTests: XCTestCase {
    func testLoadsPhotoAndPreservesAttribution() throws {
        let store = AtlasMediaStore(data: try data())
        XCTAssertNil(store.loadError)
        XCTAssertEqual(store.photo(for: "france_bordeaux")?.altText, "ブドウ畑の風景")
        XCTAssertEqual(store.photo(for: "france_bordeaux")?.author, "Photographer")
        XCTAssertNil(store.photo(for: "unknown"))
    }

    func testMissingOrMalformedDataFailsSafely() {
        for data in [nil, Data("invalid".utf8)] as [Data?] {
            let store = AtlasMediaStore(data: data)
            XCTAssertNotNil(store.loadError)
            XCTAssertNil(store.photo(for: "france_bordeaux"))
        }
    }

    func testDuplicateRegionIDsRejectWholeCatalog() throws {
        let store = AtlasMediaStore(data: try data(photos: [photo, photo]))
        XCTAssertNotNil(store.loadError)
        XCTAssertNil(store.photo(for: "france_bordeaux"))
    }

    func testInvalidURLsRejectWholeCatalog() throws {
        for key in ["sourceURL", "licenseURL"] {
            for url in ["http://example.com/photo", "javascript:alert(1)", "https:///", "https://user:password@example.com"] {
                var invalid = photo
                invalid[key] = url
                let store = AtlasMediaStore(data: try data(photos: [invalid]))
                XCTAssertNotNil(store.loadError, "\(key): \(url)")
                XCTAssertNil(store.photo(for: "france_bordeaux"))
            }
        }
    }

    func testUnsupportedSchemaAndMissingMetadataFailSafely() throws {
        XCTAssertNotNil(AtlasMediaStore(data: try data(schema: 2)).loadError)
        for key in ["altText", "author", "license", "sha256", "assetName", "checkedAt"] {
            var invalid = photo
            invalid[key] = ""
            XCTAssertNotNil(AtlasMediaStore(data: try data(photos: [invalid])).loadError)
        }
        var invalid = photo
        invalid["width"] = 0
        XCTAssertNotNil(AtlasMediaStore(data: try data(photos: [invalid])).loadError)
    }

    private var photo: [String: Any] {
        ["regionID": "france_bordeaux", "assetName": "atlas_france_bordeaux",
         "filename": "bordeaux.jpg", "title": "Vineyard", "altText": "ブドウ畑の風景",
         "author": "Photographer", "sourceURL": "https://example.com/photo",
         "license": "CC BY 4.0", "licenseURL": "https://creativecommons.org/licenses/by/4.0/",
         "changes": "トリミング", "checkedAt": "2026-09-15",
         "sha256": String(repeating: "a", count: 64), "width": 1200, "height": 800]
    }

    private func data(photos: [[String: Any]]? = nil, schema: Int = 1) throws -> Data {
        try JSONSerialization.data(withJSONObject: [
            "schemaVersion": schema, "sourceHash": String(repeating: "b", count: 64),
            "photos": photos ?? [photo],
        ])
    }
}
