import Foundation

nonisolated enum ContentValidationSeverity: String, Codable, Sendable {
    case warning
    case error
}

nonisolated enum ContentValidationCode: String, Codable, Sendable {
    case unsupportedSchemaVersion
    case unsupportedLevel
    case emptyRequiredValue
    case emptyManifest
    case duplicatePackID
    case duplicateResource
    case invalidExpectedCount
    case descriptorMismatch
    case vocabularyCountMismatch
    case duplicateVocabularyID
    case duplicateOfficialIndex
    case invalidOfficialIndex
    case duplicateExampleID
    case duplicateTag
    case missingSupplementalData
}

nonisolated struct ContentValidationIssue: Identifiable, Hashable, Sendable {
    let severity: ContentValidationSeverity
    let code: ContentValidationCode
    let path: String
    let message: String

    var id: String {
        "\(severity.rawValue):\(code.rawValue):\(path):\(message)"
    }
}

nonisolated struct ContentValidationReport: Sendable {
    let issues: [ContentValidationIssue]

    var errors: [ContentValidationIssue] {
        issues.filter { $0.severity == .error }
    }

    var warnings: [ContentValidationIssue] {
        issues.filter { $0.severity == .warning }
    }

    var isValid: Bool { errors.isEmpty }

    init(issues: [ContentValidationIssue] = []) {
        self.issues = issues
    }

    func merging(_ other: ContentValidationReport) -> ContentValidationReport {
        ContentValidationReport(issues: issues + other.issues)
    }
}

nonisolated enum ContentValidator {
    static func validate(manifest: ContentManifest) -> ContentValidationReport {
        var issues: [ContentValidationIssue] = []

        if manifest.schemaVersion != ContentManifest.supportedSchemaVersion {
            issues.append(error(
                .unsupportedSchemaVersion,
                path: "manifest.schemaVersion",
                "対応外のmanifest schemaVersionです: \(manifest.schemaVersion)"
            ))
        }

        if manifest.contentVersion.isBlank {
            issues.append(error(
                .emptyRequiredValue,
                path: "manifest.contentVersion",
                "contentVersionは必須です。"
            ))
        }

        if manifest.packs.isEmpty {
            issues.append(error(
                .emptyManifest,
                path: "manifest.packs",
                "少なくとも1つのコンテンツパックが必要です。"
            ))
        }

        appendDuplicateIssues(
            values: manifest.packs.map(\.id),
            code: .duplicatePackID,
            path: "manifest.packs",
            label: "pack id",
            to: &issues
        )
        appendDuplicateIssues(
            values: manifest.packs.map(\.resource),
            code: .duplicateResource,
            path: "manifest.packs",
            label: "resource",
            to: &issues
        )

        for (index, descriptor) in manifest.packs.enumerated() {
            let path = "manifest.packs[\(index)]"

            if descriptor.id.isBlank {
                issues.append(error(.emptyRequiredValue, path: "\(path).id", "idは必須です。"))
            }
            if descriptor.resource.isBlank {
                issues.append(error(
                    .emptyRequiredValue,
                    path: "\(path).resource",
                    "resourceは必須です。"
                ))
            }
            if descriptor.expectedVocabularyCount < 0 {
                issues.append(error(
                    .invalidExpectedCount,
                    path: "\(path).expectedVocabularyCount",
                    "expectedVocabularyCountは0以上である必要があります。"
                ))
            }
            if !descriptor.syllabusVersion.supports(descriptor.level) {
                issues.append(error(
                    .unsupportedLevel,
                    path: "\(path).level",
                    "\(descriptor.syllabusVersion.displayName)は\(descriptor.level.displayName)をサポートしません。"
                ))
            }
        }

        return ContentValidationReport(issues: issues)
    }

    static func validate(
        pack: LevelContentPack,
        against descriptor: ContentPackDescriptor? = nil
    ) -> ContentValidationReport {
        var issues: [ContentValidationIssue] = []
        let root = "pack[\(pack.id)]"

        if pack.schemaVersion != LevelContentPack.supportedSchemaVersion {
            issues.append(error(
                .unsupportedSchemaVersion,
                path: "\(root).schemaVersion",
                "対応外のpack schemaVersionです: \(pack.schemaVersion)"
            ))
        }
        if pack.id.isBlank {
            issues.append(error(.emptyRequiredValue, path: "\(root).id", "idは必須です。"))
        }
        if pack.contentVersion.isBlank {
            issues.append(error(
                .emptyRequiredValue,
                path: "\(root).contentVersion",
                "contentVersionは必須です。"
            ))
        }
        if !pack.syllabusVersion.supports(pack.level) {
            issues.append(error(
                .unsupportedLevel,
                path: "\(root).level",
                "\(pack.syllabusVersion.displayName)は\(pack.level.displayName)をサポートしません。"
            ))
        }
        if pack.source.title.isBlank {
            issues.append(error(
                .emptyRequiredValue,
                path: "\(root).source.title",
                "source.titleは必須です。"
            ))
        }
        if pack.source.url.isBlank {
            issues.append(error(
                .emptyRequiredValue,
                path: "\(root).source.url",
                "source.urlは必須です。"
            ))
        }

        if let descriptor {
            if descriptor.id != pack.id {
                issues.append(error(
                    .descriptorMismatch,
                    path: "\(root).id",
                    "manifestのid（\(descriptor.id)）と一致しません。"
                ))
            }
            if descriptor.mapping != pack.mapping {
                issues.append(error(
                    .descriptorMismatch,
                    path: "\(root).mapping",
                    "manifestのシラバス版またはレベルと一致しません。"
                ))
            }
            if descriptor.expectedVocabularyCount != pack.vocabulary.count {
                issues.append(error(
                    .vocabularyCountMismatch,
                    path: "\(root).vocabulary",
                    "語彙数がmanifestの期待値\(descriptor.expectedVocabularyCount)件と一致しません（実際: \(pack.vocabulary.count)件）。"
                ))
            }
        }

        appendDuplicateIssues(
            values: pack.vocabulary.map(\.id),
            code: .duplicateVocabularyID,
            path: "\(root).vocabulary",
            label: "vocabulary id",
            to: &issues
        )
        appendDuplicateIssues(
            values: pack.vocabulary.map(\.officialIndex),
            code: .duplicateOfficialIndex,
            path: "\(root).vocabulary",
            label: "officialIndex",
            to: &issues
        )

        let allExampleIDs = pack.vocabulary.flatMap { $0.examples.map(\.id) }
        appendDuplicateIssues(
            values: allExampleIDs,
            code: .duplicateExampleID,
            path: "\(root).vocabulary.examples",
            label: "example id",
            to: &issues
        )

        var missingPartOfSpeech = 0
        var missingJapanese = 0
        var missingExamples = 0

        for (index, item) in pack.vocabulary.enumerated() {
            let path = "\(root).vocabulary[\(index)]"

            if item.id.isBlank {
                issues.append(error(.emptyRequiredValue, path: "\(path).id", "idは必須です。"))
            }
            if item.officialIndex <= 0 {
                issues.append(error(
                    .invalidOfficialIndex,
                    path: "\(path).officialIndex",
                    "officialIndexは1以上である必要があります。"
                ))
            }
            if item.hanzi.isBlank {
                issues.append(error(.emptyRequiredValue, path: "\(path).hanzi", "hanziは必須です。"))
            }
            if item.pinyin.isBlank {
                issues.append(error(.emptyRequiredValue, path: "\(path).pinyin", "pinyinは必須です。"))
            }

            if item.partOfSpeech?.isBlank != false { missingPartOfSpeech += 1 }
            if item.japanese.isEmpty { missingJapanese += 1 }
            if item.examples.isEmpty { missingExamples += 1 }

            appendDuplicateIssues(
                values: item.tags,
                code: .duplicateTag,
                path: "\(path).tags",
                label: "tag",
                to: &issues
            )

            for (exampleIndex, example) in item.examples.enumerated() {
                let examplePath = "\(path).examples[\(exampleIndex)]"
                if example.id.isBlank {
                    issues.append(error(
                        .emptyRequiredValue,
                        path: "\(examplePath).id",
                        "idは必須です。"
                    ))
                }
                if example.hanzi.isBlank {
                    issues.append(error(
                        .emptyRequiredValue,
                        path: "\(examplePath).hanzi",
                        "hanziは必須です。"
                    ))
                }
                if example.pinyin.isBlank {
                    issues.append(error(
                        .emptyRequiredValue,
                        path: "\(examplePath).pinyin",
                        "pinyinは必須です。"
                    ))
                }
                if example.japanese.isBlank {
                    issues.append(error(
                        .emptyRequiredValue,
                        path: "\(examplePath).japanese",
                        "japaneseは必須です。"
                    ))
                }
            }
        }

        appendSupplementalWarning(
            count: missingPartOfSpeech,
            field: "partOfSpeech",
            root: root,
            to: &issues
        )
        appendSupplementalWarning(
            count: missingJapanese,
            field: "japanese",
            root: root,
            to: &issues
        )
        appendSupplementalWarning(
            count: missingExamples,
            field: "examples",
            root: root,
            to: &issues
        )

        return ContentValidationReport(issues: issues)
    }

    static func validate(catalog: ContentCatalog) -> ContentValidationReport {
        var report = validate(manifest: catalog.manifest)
        let descriptors = Dictionary(
            catalog.manifest.packs.map { ($0.id, $0) },
            uniquingKeysWith: { first, _ in first }
        )

        for pack in catalog.packs {
            report = report.merging(validate(pack: pack, against: descriptors[pack.id]))
        }

        var crossPackIssues: [ContentValidationIssue] = []
        appendDuplicateIssues(
            values: catalog.vocabulary.map(\.id),
            code: .duplicateVocabularyID,
            path: "catalog.vocabulary",
            label: "vocabulary id",
            to: &crossPackIssues
        )
        return report.merging(ContentValidationReport(issues: crossPackIssues))
    }

    private static func appendSupplementalWarning(
        count: Int,
        field: String,
        root: String,
        to issues: inout [ContentValidationIssue]
    ) {
        guard count > 0 else { return }
        issues.append(warning(
            .missingSupplementalData,
            path: "\(root).vocabulary.\(field)",
            "\(field)が未整備の語彙が\(count)件あります。"
        ))
    }

    private static func appendDuplicateIssues<Value: Hashable>(
        values: [Value],
        code: ContentValidationCode,
        path: String,
        label: String,
        to issues: inout [ContentValidationIssue]
    ) {
        var seen: Set<Value> = []
        var reported: Set<Value> = []

        for value in values where !seen.insert(value).inserted && reported.insert(value).inserted {
            issues.append(error(code, path: path, "重複した\(label)があります: \(value)"))
        }
    }

    private static func error(
        _ code: ContentValidationCode,
        path: String,
        _ message: String
    ) -> ContentValidationIssue {
        ContentValidationIssue(severity: .error, code: code, path: path, message: message)
    }

    private static func warning(
        _ code: ContentValidationCode,
        path: String,
        _ message: String
    ) -> ContentValidationIssue {
        ContentValidationIssue(severity: .warning, code: code, path: path, message: message)
    }
}

private extension String {
    nonisolated var isBlank: Bool {
        trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }
}
