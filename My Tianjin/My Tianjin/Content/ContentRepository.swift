import Foundation

nonisolated enum ContentRepositoryError: Error, LocalizedError {
    case invalidResourcePath(String)
    case resourceNotFound(String)
    case unreadableResource(resource: String, reason: String)
    case decodingFailed(resource: String, reason: String)
    case noMatchingPacks(syllabusVersion: HSKSyllabusVersion, levels: [HSKLevel])
    case validationFailed([ContentValidationIssue])

    var errorDescription: String? {
        switch self {
        case let .invalidResourcePath(resource):
            "不正なコンテンツリソースパスです: \(resource)"
        case let .resourceNotFound(resource):
            "コンテンツリソースが見つかりません: \(resource)"
        case let .unreadableResource(resource, reason):
            "コンテンツリソースを読み込めません: \(resource)（\(reason)）"
        case let .decodingFailed(resource, reason):
            "コンテンツJSONを解析できません: \(resource)（\(reason)）"
        case let .noMatchingPacks(syllabusVersion, levels):
            "\(syllabusVersion.displayName)の対象レベル（\(levels.map(\.rawValue).joined(separator: ", "))）がmanifestにありません。"
        case let .validationFailed(issues):
            "コンテンツ検証に失敗しました（\(issues.count)件）。"
        }
    }
}

nonisolated struct ContentRepository: Sendable {
    static let defaultManifestResource = "content-manifest.json"

    private let dataLoader: @Sendable (String) throws -> Data

    init(bundle: Bundle = .main) {
        dataLoader = { resource in
            guard Self.isSafeRelativeResource(resource) else {
                throw ContentRepositoryError.invalidResourcePath(resource)
            }
            guard let url = Self.resourceURL(named: resource, in: bundle) else {
                throw ContentRepositoryError.resourceNotFound(resource)
            }
            do {
                return try Data(contentsOf: url, options: .mappedIfSafe)
            } catch {
                throw ContentRepositoryError.unreadableResource(
                    resource: resource,
                    reason: error.localizedDescription
                )
            }
        }
    }

    init(directoryURL: URL) {
        let rootURL = directoryURL.standardizedFileURL
        dataLoader = { resource in
            guard Self.isSafeRelativeResource(resource) else {
                throw ContentRepositoryError.invalidResourcePath(resource)
            }
            let resourceURL = rootURL.appendingPathComponent(resource).standardizedFileURL
            let isInsideRoot = resourceURL.path == rootURL.path
                || resourceURL.path.hasPrefix(rootURL.path + "/")
            guard isInsideRoot else {
                throw ContentRepositoryError.invalidResourcePath(resource)
            }
            guard FileManager.default.fileExists(atPath: resourceURL.path) else {
                throw ContentRepositoryError.resourceNotFound(resource)
            }
            do {
                return try Data(contentsOf: resourceURL, options: .mappedIfSafe)
            } catch {
                throw ContentRepositoryError.unreadableResource(
                    resource: resource,
                    reason: error.localizedDescription
                )
            }
        }
    }

    func loadManifest(
        named resource: String = Self.defaultManifestResource
    ) throws -> ContentManifest {
        try decode(ContentManifest.self, resource: resource)
    }

    func loadPack(_ descriptor: ContentPackDescriptor) throws -> LevelContentPack {
        let pack = try decode(LevelContentPack.self, resource: descriptor.resource)
        let report = ContentValidator.validate(pack: pack, against: descriptor)
        if !report.isValid {
            throw ContentRepositoryError.validationFailed(report.errors)
        }
        return pack
    }

    func loadCatalog(
        manifestNamed manifestResource: String = Self.defaultManifestResource,
        syllabusVersion: HSKSyllabusVersion,
        levels: Set<HSKLevel>
    ) throws -> ContentCatalog {
        let manifest = try loadManifest(named: manifestResource)
        let manifestReport = ContentValidator.validate(manifest: manifest)
        if !manifestReport.isValid {
            throw ContentRepositoryError.validationFailed(manifestReport.errors)
        }

        let requestedLevels = levels.sorted()
        guard !requestedLevels.isEmpty else {
            throw ContentRepositoryError.noMatchingPacks(
                syllabusVersion: syllabusVersion,
                levels: []
            )
        }
        guard requestedLevels.allSatisfy(syllabusVersion.supports) else {
            let issue = ContentValidationIssue(
                severity: .error,
                code: .unsupportedLevel,
                path: "catalog.levels",
                message: "\(syllabusVersion.displayName)で利用できないレベルが含まれています。"
            )
            throw ContentRepositoryError.validationFailed([issue])
        }

        let descriptors = manifest.descriptors(
            for: syllabusVersion,
            levels: levels
        )
        guard descriptors.count == levels.count else {
            throw ContentRepositoryError.noMatchingPacks(
                syllabusVersion: syllabusVersion,
                levels: requestedLevels
            )
        }

        var packs: [LevelContentPack] = []
        var report = manifestReport
        for descriptor in descriptors {
            let pack = try decode(LevelContentPack.self, resource: descriptor.resource)
            let packReport = ContentValidator.validate(pack: pack, against: descriptor)
            report = report.merging(packReport)
            packs.append(pack)
        }

        let provisionalCatalog = ContentCatalog(
            manifest: manifest,
            packs: packs,
            validationReport: report
        )
        let catalogReport = ContentValidator.validate(catalog: provisionalCatalog)
        if !catalogReport.isValid {
            throw ContentRepositoryError.validationFailed(catalogReport.errors)
        }

        return ContentCatalog(
            manifest: manifest,
            packs: packs,
            validationReport: catalogReport
        )
    }

    func loadCatalog(
        manifestNamed manifestResource: String = Self.defaultManifestResource,
        syllabusVersion: HSKSyllabusVersion,
        through level: HSKLevel
    ) throws -> ContentCatalog {
        try loadCatalog(
            manifestNamed: manifestResource,
            syllabusVersion: syllabusVersion,
            levels: Set(level.levelsThroughSelf)
        )
    }

    private func decode<Value: Decodable>(
        _ type: Value.Type,
        resource: String
    ) throws -> Value {
        let data = try dataLoader(resource)
        do {
            return try JSONDecoder().decode(type, from: data)
        } catch {
            throw ContentRepositoryError.decodingFailed(
                resource: resource,
                reason: error.localizedDescription
            )
        }
    }

    private static func isSafeRelativeResource(_ resource: String) -> Bool {
        guard !resource.isEmpty, !resource.hasPrefix("/") else { return false }
        let components = resource.split(separator: "/", omittingEmptySubsequences: false)
        return !components.contains("..") && !components.contains("")
    }

    private static func resourceURL(named resource: String, in bundle: Bundle) -> URL? {
        let path = resource as NSString
        let pathExtension = path.pathExtension.isEmpty ? "json" : path.pathExtension
        let pathWithoutExtension = path.deletingPathExtension as NSString
        let resourceName = pathWithoutExtension.lastPathComponent
        let directory = pathWithoutExtension.deletingLastPathComponent
        let subdirectory = directory.isEmpty ? nil : directory

        return bundle.url(
            forResource: resourceName,
            withExtension: pathExtension,
            subdirectory: subdirectory
        ) ?? bundle.url(
            forResource: resourceName,
            withExtension: pathExtension
        )
    }
}
