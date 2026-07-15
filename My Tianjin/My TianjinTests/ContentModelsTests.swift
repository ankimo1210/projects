import Foundation
import XCTest
@testable import My_Tianjin

final class ContentModelsTests: XCTestCase {
    func testManifestAndPackJSONRoundTrip() throws {
        let descriptor = makeDescriptor(expectedVocabularyCount: 1)
        let manifest = ContentManifest(
            schemaVersion: ContentManifest.supportedSchemaVersion,
            contentVersion: "2026.07",
            packs: [descriptor]
        )
        let pack = makePack(vocabulary: [makeVocabularyItem()])

        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        let decoder = JSONDecoder()

        let restoredManifest = try decoder.decode(
            ContentManifest.self,
            from: encoder.encode(manifest)
        )
        let restoredPack = try decoder.decode(
            LevelContentPack.self,
            from: encoder.encode(pack)
        )

        XCTAssertEqual(restoredManifest, manifest)
        XCTAssertEqual(restoredPack, pack)
    }

    func testOptionalVocabularyFieldsDefaultToEmptyCollections() throws {
        let json = #"""
        {
          "id": "hsk3-1",
          "officialIndex": 1,
          "hanzi": "爱",
          "pinyin": "ài"
        }
        """#.data(using: .utf8)!

        let item = try JSONDecoder().decode(VocabularyItem.self, from: json)

        XCTAssertNil(item.traditional)
        XCTAssertNil(item.partOfSpeech)
        XCTAssertEqual(item.japanese, [])
        XCTAssertEqual(item.examples, [])
        XCTAssertEqual(item.tags, [])
    }

    func testValidManifestAndPackHaveNoValidationErrors() {
        let descriptor = makeDescriptor(expectedVocabularyCount: 1)
        let manifest = ContentManifest(
            schemaVersion: ContentManifest.supportedSchemaVersion,
            contentVersion: "2026.07",
            packs: [descriptor]
        )
        let pack = makePack(vocabulary: [makeVocabularyItem()])

        XCTAssertTrue(ContentValidator.validate(manifest: manifest).isValid)
        XCTAssertTrue(ContentValidator.validate(pack: pack, against: descriptor).isValid)
    }

    func testValidationReportsStructuralContentErrors() {
        let sharedExample = ExampleSentence(
            id: "duplicate-example",
            hanzi: "我爱中国。",
            pinyin: "Wǒ ài Zhōngguó.",
            japanese: "私は中国が好きです。"
        )
        let first = VocabularyItem(
            id: "duplicate-word",
            officialIndex: 1,
            hanzi: "爱",
            pinyin: "ài",
            partOfSpeech: "verb",
            japanese: ["愛する"],
            examples: [sharedExample],
            tags: ["hsk", "hsk"]
        )
        let second = VocabularyItem(
            id: "duplicate-word",
            officialIndex: 1,
            hanzi: "人",
            pinyin: "",
            partOfSpeech: "noun",
            japanese: ["人"],
            examples: [sharedExample]
        )
        let descriptor = makeDescriptor(expectedVocabularyCount: 3)
        let report = ContentValidator.validate(
            pack: makePack(vocabulary: [first, second]),
            against: descriptor
        )
        let codes = Set(report.errors.map(\.code))

        XCTAssertFalse(report.isValid)
        XCTAssertTrue(codes.contains(.vocabularyCountMismatch))
        XCTAssertTrue(codes.contains(.duplicateVocabularyID))
        XCTAssertTrue(codes.contains(.duplicateOfficialIndex))
        XCTAssertTrue(codes.contains(.duplicateExampleID))
        XCTAssertTrue(codes.contains(.duplicateTag))
        XCTAssertTrue(codes.contains(.emptyRequiredValue))
    }

    func testRepositoryRejectsUnsafeRelativeResourcePath() {
        let repository = ContentRepository(
            directoryURL: FileManager.default.temporaryDirectory
        )
        let descriptor = ContentPackDescriptor(
            id: "unsafe-pack",
            syllabusVersion: .hsk3,
            level: .level1,
            resource: "../outside.json",
            expectedVocabularyCount: 1
        )

        XCTAssertThrowsError(try repository.loadPack(descriptor)) { error in
            guard case ContentRepositoryError.invalidResourcePath("../outside.json") = error else {
                return XCTFail("Unexpected error: \(error)")
            }
        }
    }

    func testContentStoreFallsBackToCuratedLevelOneWhenManifestIsMissing() {
        let missingDirectory = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString, isDirectory: true)
        let store = LearningContentStore(
            repository: ContentRepository(directoryURL: missingDirectory)
        )

        store.prepare()

        XCTAssertTrue(store.isUsingFallback)
        XCTAssertNotNil(store.loadError)
        XCTAssertEqual(store.availableLevels, [.level1])
        XCTAssertEqual(store.vocabulary(for: .level1, cumulative: false).count, 100)
    }

    private func makeDescriptor(expectedVocabularyCount: Int) -> ContentPackDescriptor {
        ContentPackDescriptor(
            id: "hsk3-level1",
            syllabusVersion: .hsk3,
            level: .level1,
            resource: "hsk3-level1.json",
            expectedVocabularyCount: expectedVocabularyCount
        )
    }

    private func makePack(vocabulary: [VocabularyItem]) -> LevelContentPack {
        LevelContentPack(
            id: "hsk3-level1",
            contentVersion: "2026.07",
            syllabusVersion: .hsk3,
            level: .level1,
            source: ContentSource(
                title: "Test fixture",
                url: "https://example.com/content",
                license: "Test-only"
            ),
            skills: [.vocabulary, .reading],
            vocabulary: vocabulary
        )
    }

    private func makeVocabularyItem() -> VocabularyItem {
        VocabularyItem(
            id: "hsk3-1",
            officialIndex: 1,
            hanzi: "爱",
            traditional: "愛",
            pinyin: "ài",
            partOfSpeech: "verb",
            japanese: ["愛する", "好きである"],
            examples: [
                ExampleSentence(
                    id: "hsk3-1-example-1",
                    hanzi: "我爱中国。",
                    pinyin: "Wǒ ài Zhōngguó.",
                    japanese: "私は中国が好きです。"
                )
            ],
            tags: ["core"]
        )
    }
}
