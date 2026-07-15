import Foundation
import XCTest
@testable import My_Tianjin

@MainActor
final class BundledContentTests: XCTestCase {
    private let expectedCounts: [HSKLevel: Int] = [
        .level1: 300,
        .level2: 200,
        .level3: 500,
        .level4: 1_000,
        .level5: 1_600,
        .level6: 1_800,
        .advanced: 5_600,
    ]

    func testBundledManifestAndPacksMatchOfficialHSKContentContract() throws {
        let manifestURL = try XCTUnwrap(
            bundledResourceURL(named: "content-manifest.json"),
            "Bundle.main must contain content-manifest.json"
        )
        let decoder = JSONDecoder()
        let manifest = try decoder.decode(
            ContentManifest.self,
            from: Data(contentsOf: manifestURL, options: .mappedIfSafe)
        )
        var issues: [String] = []

        record(
            manifest.schemaVersion == ContentManifest.supportedSchemaVersion,
            "manifest schemaVersion is unsupported",
            into: &issues
        )
        record(!manifest.contentVersion.trimmed.isEmpty, "manifest contentVersion is empty", into: &issues)
        record(manifest.packs.count == 7, "manifest must contain exactly 7 packs", into: &issues)
        record(
            manifest.packs.allSatisfy { !$0.id.trimmed.isEmpty },
            "manifest pack IDs must be non-empty",
            into: &issues
        )
        record(
            manifest.packs.allSatisfy { !$0.resource.trimmed.isEmpty },
            "manifest resources must be non-empty",
            into: &issues
        )
        record(Set(manifest.packs.map(\.id)).count == 7, "manifest pack IDs must be unique", into: &issues)
        record(Set(manifest.packs.map(\.resource)).count == 7, "manifest resources must be unique", into: &issues)

        var allItems: [VocabularyItem] = []
        var level1Items: [VocabularyItem] = []

        for (level, expectedCount) in expectedCounts {
            let descriptors = manifest.packs.filter { descriptor in
                descriptor.syllabusVersion == .hsk3 && descriptor.level == level
            }
            record(
                descriptors.count == 1,
                "manifest must contain one hsk3.0 descriptor for level \(level.rawValue)",
                into: &issues
            )
            guard let descriptor = descriptors.first else { continue }
            record(
                descriptor.expectedVocabularyCount == expectedCount,
                "level \(level.rawValue) descriptor count must be \(expectedCount)",
                into: &issues
            )

            let packURL = try XCTUnwrap(
                bundledResourceURL(named: descriptor.resource, adjacentTo: manifestURL),
                "Bundle.main is missing \(descriptor.resource)"
            )
            let pack = try decoder.decode(
                LevelContentPack.self,
                from: Data(contentsOf: packURL, options: .mappedIfSafe)
            )
            validate(
                pack: pack,
                descriptor: descriptor,
                manifest: manifest,
                expectedCount: expectedCount,
                issues: &issues
            )
            allItems.append(contentsOf: pack.vocabulary)
            if level == .level1 {
                level1Items = pack.vocabulary
            }
        }

        record(allItems.count == 11_000, "bundled packs must contain 11,000 items", into: &issues)
        record(
            Set(allItems.map(\.id)).count == 11_000,
            "vocabulary IDs must be globally unique",
            into: &issues
        )
        record(
            allItems.map(\.officialIndex).sorted() == Array(1 ... 11_000),
            "officialIndex must be unique and continuous from 1 through 11,000",
            into: &issues
        )

        validateVocabulary(allItems, issues: &issues)
        validateLevel1Examples(level1Items, issues: &issues)
        validateGeneratedPractice(level1Items, issues: &issues)

        XCTAssertTrue(
            issues.isEmpty,
            (["Bundled content contract failed with \(issues.count) issue(s):"]
                + Array(issues.prefix(100))
                + (issues.count > 100 ? ["... \(issues.count - 100) more issue(s)"] : []))
                .joined(separator: "\n")
        )
    }

    func testCumulativeAdvancedContentLoadsResponsivelyWithinBudget() async throws {
        let store = LearningContentStore()
        store.prepare()
        XCTAssertFalse(store.isUsingFallback)

        var mainActorHeartbeat = false
        Task { @MainActor in
            mainActorHeartbeat = true
        }

        let startedAt = Date()
        try await store.ensureLoaded(for: .advanced, cumulative: true)
        let elapsed = Date().timeIntervalSince(startedAt)

        XCTAssertTrue(
            mainActorHeartbeat,
            "The main actor must remain schedulable while cumulative packs decode."
        )
        XCTAssertEqual(store.vocabulary(for: .advanced, cumulative: true).count, 11_000)
        XCTAssertNil(store.loadError)
        XCTAssertLessThan(elapsed, 3, "Cumulative HSK 1-9 loading exceeded the 3-second budget.")
    }

    private func validate(
        pack: LevelContentPack,
        descriptor: ContentPackDescriptor,
        manifest: ContentManifest,
        expectedCount: Int,
        issues: inout [String]
    ) {
        let location = "pack[\(descriptor.resource)]"
        record(
            pack.schemaVersion == LevelContentPack.supportedSchemaVersion,
            "\(location) schemaVersion is unsupported",
            into: &issues
        )
        record(pack.id == descriptor.id, "\(location) id does not match manifest", into: &issues)
        record(
            pack.contentVersion == manifest.contentVersion,
            "\(location) contentVersion does not match manifest",
            into: &issues
        )
        record(
            pack.syllabusVersion == descriptor.syllabusVersion && pack.level == descriptor.level,
            "\(location) syllabus mapping does not match manifest",
            into: &issues
        )
        record(pack.vocabulary.count == expectedCount, "\(location) must contain \(expectedCount) items", into: &issues)
        record(!pack.source.title.trimmed.isEmpty, "\(location) source title is empty", into: &issues)
        record(pack.source.title.localizedCaseInsensitiveContains("HSK"), "\(location) source title must identify HSK", into: &issues)
        record(
            URL(string: pack.source.url)?.scheme == "https",
            "\(location) source URL must be valid HTTPS",
            into: &issues
        )
        let license = pack.source.license ?? ""
        record(
            license.localizedCaseInsensitiveContains("CC-CEDICT"),
            "\(location) source license must attribute CC-CEDICT",
            into: &issues
        )
        record(
            license.localizedCaseInsensitiveContains("CC BY-SA 4.0"),
            "\(location) source license must state CC BY-SA 4.0",
            into: &issues
        )
    }

    private func validateVocabulary(_ items: [VocabularyItem], issues: inout [String]) {
        let acceptedProvenance = Set(["curated", "human-reviewed", "machine-translated-cc-cedict"])

        for item in items {
            let location = "vocabulary[\(item.officialIndex)]"
            record(!item.id.trimmed.isEmpty, "\(location) id is empty", into: &issues)
            record(!item.hanzi.trimmed.isEmpty, "\(location) hanzi is empty", into: &issues)
            record(
                item.hanzi.range(of: #"[0-9]+$"#, options: .regularExpression) == nil,
                "\(location) display hanzi ends in an Arabic sense number",
                into: &issues
            )
            record(!item.pinyin.trimmed.isEmpty, "\(location) pinyin is empty", into: &issues)
            record(
                !item.japanese.isEmpty && item.japanese.allSatisfy { !$0.trimmed.isEmpty },
                "\(location) Japanese gloss is empty",
                into: &issues
            )
            for gloss in item.japanese {
                record(
                    gloss.range(
                        of: #"（[ぁ-んァ-ヶー・\s]+）"#,
                        options: .regularExpression
                    ) == nil,
                    "\(location) Japanese gloss includes a parenthesized reading",
                    into: &issues
                )
                record(
                    gloss.range(
                        of: #"[（(](?:[一-龯々]{1,8}(?:詞|語)|動|名|形|副)(?:[・/／,，\s]*(?:[一-龯々]{1,8}(?:詞|語)|動|名|形|副))*[）)]"#,
                        options: .regularExpression
                    ) == nil,
                    "\(location) Japanese gloss includes a grammatical label",
                    into: &issues
                )
                let senses = gloss.split(separator: "・").map(String.init)
                record(gloss.count <= 48, "\(location) Japanese gloss exceeds 48 characters", into: &issues)
                record(senses.count <= 6, "\(location) Japanese gloss has more than 6 senses", into: &issues)
                record(Set(senses).count == senses.count, "\(location) Japanese gloss repeats a sense", into: &issues)
                record(
                    gloss.unicodeScalars.allSatisfy { $0.properties.generalCategory != .control },
                    "\(location) Japanese gloss includes a control character",
                    into: &issues
                )
                record(
                    gloss.range(of: #"[\uAC00-\uD7AF]"#, options: .regularExpression) == nil,
                    "\(location) Japanese gloss includes Hangul",
                    into: &issues
                )
                record(
                    gloss.range(of: #"<0x[0-9A-Fa-f]+>"#, options: .regularExpression) == nil,
                    "\(location) Japanese gloss includes a byte escape marker",
                    into: &issues
                )
                record(
                    !containsUnexpectedEnglishWord(gloss),
                    "\(location) Japanese gloss includes an unexpected English word",
                    into: &issues
                )
                record(!gloss.contains("～"), "\(location) Japanese gloss uses inconsistent tilde", into: &issues)
                record(
                    gloss.range(
                        of: #"[（(][^）)]*[）)]\s*〜"#,
                        options: .regularExpression
                    ) == nil,
                    "\(location) Japanese gloss includes an unfinished placeholder",
                    into: &issues
                )
            }
            record(
                Set(item.tags).intersection(acceptedProvenance).count == 1,
                "\(location) must have exactly one translation provenance tag",
                into: &issues
            )
        }
    }

    private func validateLevel1Examples(_ items: [VocabularyItem], issues: inout [String]) {
        record(items.count == 300, "HSK 1 must contain 300 items", into: &issues)
        record(
            items.reduce(0) { $0 + $1.examples.count } >= 300,
            "HSK 1 must contain examples for all 300 items",
            into: &issues
        )

        for item in items {
            let location = "hsk1[\(item.officialIndex)]"
            record(!item.examples.isEmpty, "\(location) is missing an example", into: &issues)
            for example in item.examples {
                record(!example.hanzi.trimmed.isEmpty, "\(location) example hanzi is empty", into: &issues)
                record(!example.pinyin.trimmed.isEmpty, "\(location) example pinyin is empty", into: &issues)
                record(!example.japanese.trimmed.isEmpty, "\(location) example Japanese is empty", into: &issues)
                record(
                    example.hanzi.contains(item.hanzi),
                    "\(location) example does not contain target hanzi \(item.hanzi)",
                    into: &issues
                )
            }
        }
    }

    private func validateGeneratedPractice(
        _ items: [VocabularyItem],
        issues: inout [String]
    ) {
        let clozeQuestions = GeneratedPracticeContent.clozeQuestions(vocabulary: items)
        let audioQuestions = GeneratedPracticeContent.audioQuestions(vocabulary: items)
        record(clozeQuestions.count == 30, "HSK 1 must generate 30 cloze questions", into: &issues)
        record(audioQuestions.count == 30, "HSK 1 must generate 30 audio questions", into: &issues)

        for question in clozeQuestions {
            guard case let .sentenceCloze(payload) = question.content else {
                issues.append("generated cloze question has the wrong content type")
                continue
            }
            record(payload.sentence.text.contains(payload.placeholder), "cloze sentence is missing its placeholder", into: &issues)
            record(payload.answers.options.count == 4, "cloze question must have 4 options", into: &issues)
            record(
                Set(payload.answers.options.map(\.content.text)).count == 4,
                "cloze question must have 4 distinct visible options",
                into: &issues
            )
            record(payload.answers.correctOptionIDs.count == 1, "cloze question must have one answer", into: &issues)
            record(
                payload.answers.options.contains { payload.answers.correctOptionIDs.contains($0.id) },
                "cloze answer is missing from its options",
                into: &issues
            )
        }

        for question in audioQuestions {
            guard case let .audioToMeaning(payload) = question.content else {
                issues.append("generated audio question has the wrong content type")
                continue
            }
            record(!payload.audio.text.trimmed.isEmpty, "audio question has empty speech text", into: &issues)
            record(payload.answers.options.count == 4, "audio question must have 4 options", into: &issues)
            record(
                Set(payload.answers.options.map(\.content.text)).count == 4,
                "audio question must have 4 distinct visible options",
                into: &issues
            )
            record(payload.answers.correctOptionIDs.count == 1, "audio question must have one answer", into: &issues)
        }

        let studyItems = VocabularySessionFactory.studyItems(from: items)
        record(studyItems.count == 300, "HSK 1 must generate 300 flashcard study items", into: &issues)
        let vocabularyByID = Dictionary(uniqueKeysWithValues: items.map { ($0.id, $0) })
        for item in studyItems {
            record(item.distractorOptionIDs.count >= 3, "flashcard item lacks distractors", into: &issues)
            record(!item.distractorOptionIDs.contains(item.correctOptionID), "flashcard distractors include the answer", into: &issues)
            let visibleOptionIDs = [item.correctOptionID] + Array(item.distractorOptionIDs.prefix(3))
            let visibleMeanings = visibleOptionIDs.compactMap { vocabularyByID[$0]?.primaryJapanese }
            record(
                visibleMeanings.count == 4 && Set(visibleMeanings).count == 4,
                "flashcard item has duplicate visible meanings",
                into: &issues
            )
        }
    }

    private func bundledResourceURL(named resource: String, adjacentTo baseURL: URL? = nil) -> URL? {
        if let baseURL {
            let adjacentURL = baseURL.deletingLastPathComponent().appendingPathComponent(resource)
            if FileManager.default.fileExists(atPath: adjacentURL.path) {
                return adjacentURL
            }
        }

        let resourcePath = resource as NSString
        let fileExtension = resourcePath.pathExtension.isEmpty ? "json" : resourcePath.pathExtension
        let pathWithoutExtension = resourcePath.deletingPathExtension as NSString
        let name = pathWithoutExtension.lastPathComponent
        let directory = pathWithoutExtension.deletingLastPathComponent
        let candidates: [String?] = [
            directory.isEmpty ? nil : directory,
            "Content",
            "Resources/Content",
            nil,
        ]
        for subdirectory in candidates {
            if let url = Bundle.main.url(
                forResource: name,
                withExtension: fileExtension,
                subdirectory: subdirectory
            ) {
                return url
            }
        }
        return nil
    }

    private func record(_ condition: Bool, _ message: String, into issues: inout [String]) {
        if !condition {
            issues.append(message)
        }
    }

    private func containsUnexpectedEnglishWord(_ value: String) -> Bool {
        let allowed = Set([
            "app", "bluetooth", "cm", "dm", "kg", "km", "mm", "ml", "web", "wifi",
        ])
        guard let expression = try? NSRegularExpression(pattern: #"[A-Za-z]{2,}"#) else {
            return true
        }
        let range = NSRange(value.startIndex..<value.endIndex, in: value)
        return expression.matches(in: value, range: range).contains { match in
            guard let tokenRange = Range(match.range, in: value) else { return true }
            let token = String(value[tokenRange])
            return token != token.uppercased() && !allowed.contains(token.lowercased())
        }
    }
}

private extension String {
    var trimmed: String {
        trimmingCharacters(in: .whitespacesAndNewlines)
    }
}
