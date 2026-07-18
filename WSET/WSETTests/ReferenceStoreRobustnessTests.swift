import Foundation
import XCTest
@testable import WSET

@MainActor
final class ReferenceStoreRobustnessTests: XCTestCase {
    func testValidReferenceDataBuildsLookupIndexes() throws {
        let store = ReferenceStore(data: try makePackData())

        XCTAssertNil(store.loadError)
        XCTAssertEqual(store.term(id: "term-1")?.nameJapanese, "用語")
        XCTAssertEqual(store.system(id: "system-1")?.nameJapanese, "分類")
        XCTAssertEqual(store.source(id: "source-1")?.name, "出典")
        XCTAssertEqual(store.terms(forQuestionID: "question-1").map(\.id), ["term-1"])
    }

    func testDuplicateIDsInEachReferenceCollectionAreRejectedWithoutCrash() throws {
        for collection in DuplicateCollection.allCases {
            let store = ReferenceStore(data: try makePackData(duplicate: collection))

            XCTAssertNil(store.pack, "\(collection.rawValue) の重複を受理しています")
            XCTAssertNotNil(store.loadError)
            XCTAssertTrue(store.terms.isEmpty)
            XCTAssertNil(store.term(id: "term-1"))
        }
    }

    func testApprovedRetiredTermIDResolvesToCanonicalTerm() throws {
        let store = ReferenceStore(
            data: try makePackData(termIDMigrations: ["term-retired": "term-1"])
        )

        XCTAssertNil(store.loadError)
        XCTAssertEqual(store.canonicalTermID(for: "term-retired"), "term-1")
        XCTAssertEqual(store.term(id: "term-retired")?.id, "term-1")
    }

    func testBrokenTermIDMigrationIsRejected() throws {
        for migrations in [
            ["term-retired": "missing"],
            ["term-1": "term-1"],
            ["term-a": "term-b", "term-b": "term-1"],
        ] {
            let store = ReferenceStore(data: try makePackData(termIDMigrations: migrations))

            XCTAssertNil(store.pack)
            XCTAssertNotNil(store.loadError)
        }
    }

    private enum DuplicateCollection: String, CaseIterable {
        case terms
        case classificationSystems
        case classificationEntries
        case sources
    }

    private func makePackData(
        duplicate: DuplicateCollection? = nil,
        termIDMigrations: [String: String]? = nil
    ) throws -> Data {
        var terms = [term(id: "term-1")]
        var systems = [system(id: "system-1")]
        var entries = [entry(id: "entry-1")]
        var sources = [source(id: "source-1")]

        switch duplicate {
        case .terms:
            terms.append(term(id: "term-1"))
        case .classificationSystems:
            systems.append(system(id: "system-1"))
        case .classificationEntries:
            entries.append(entry(id: "entry-1"))
        case .sources:
            sources.append(source(id: "source-1"))
        case nil:
            break
        }

        var payload: [String: Any] = [
            "schemaVersion": 1,
            "sourceHash": "test-source-hash",
            "questionPackSourceHash": "test-question-hash",
            "termCount": terms.count,
            "classificationEntryCount": entries.count,
            "terms": terms,
            "classificationSystems": systems,
            "classificationEntries": entries,
            "sources": sources,
        ]
        if let termIDMigrations {
            payload["termIDMigrations"] = termIDMigrations
        }
        return try JSONSerialization.data(withJSONObject: payload)
    }

    private func term(id: String) -> [String: Any] {
        [
            "id": id,
            "nameJapanese": "用語",
            "category": "栽培",
            "summary": "概要",
            "description": "説明",
            "labels": [],
            "relatedTermIDs": [],
            "aliases": [],
            "questionIDs": ["question-1"],
            "sourceID": "source-1",
            "checkedAt": "2026-07-19",
        ]
    }

    private func system(id: String) -> [String: Any] {
        [
            "id": id,
            "region": "フランス",
            "nameJapanese": "分類",
            "summary": "概要",
            "effectiveDate": "2026-07-19",
            "sourceID": "source-1",
        ]
    }

    private func entry(id: String) -> [String: Any] {
        [
            "id": id,
            "systemID": "system-1",
            "nameJapanese": "項目",
            "nameOriginal": "Entry",
            "tier": "Tier",
            "village": "Village",
            "subregion": "Subregion",
            "entryType": "wine",
            "termID": "term-1",
            "sourceID": "source-1",
        ]
    }

    private func source(id: String) -> [String: Any] {
        [
            "id": id,
            "name": "出典",
            "url": "https://example.com/source",
            "effectiveDate": "2026-07-19",
            "checkedAt": "2026-07-19",
        ]
    }
}
