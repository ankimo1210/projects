import Foundation

struct FreeContentManifest: Codable, Equatable {
    static let supportedSchemaVersion = 1

    let schemaVersion: Int
    let selectionVersion: String
    let multipleChoiceQuestionIDs: [String]
    let writtenQuestionIDs: [String]
    let glossaryTermIDs: [String]
    let mapCountries: [String]

    static let shared: FreeContentManifest = {
        (try? load()) ?? FreeContentManifest(
            schemaVersion: supportedSchemaVersion,
            selectionVersion: "unavailable",
            multipleChoiceQuestionIDs: [],
            writtenQuestionIDs: [],
            glossaryTermIDs: [],
            mapCountries: []
        )
    }()

    var multipleChoiceQuestionIDSet: Set<String> { Set(multipleChoiceQuestionIDs) }
    var writtenQuestionIDSet: Set<String> { Set(writtenQuestionIDs) }
    var glossaryTermIDSet: Set<String> { Set(glossaryTermIDs) }
    var normalizedMapCountries: Set<String> {
        Set(mapCountries.map(GeographyNormalizer.normalizeCountry))
    }

    func containsQuestion(id: String, studyMode: String) -> Bool {
        if studyMode == "written_answer" {
            return writtenQuestionIDSet.contains(id)
        }
        return multipleChoiceQuestionIDSet.contains(id)
    }

    static func load(bundle: Bundle = .main) throws -> FreeContentManifest {
        guard let url = bundle.url(forResource: "FreeContentManifest", withExtension: "json")
        else { throw CocoaError(.fileNoSuchFile) }
        let manifest = try JSONDecoder().decode(
            FreeContentManifest.self,
            from: Data(contentsOf: url)
        )
        guard manifest.schemaVersion == supportedSchemaVersion,
              manifest.multipleChoiceQuestionIDs.count == FeatureAccessPolicy.freeMultipleChoiceLimit,
              manifest.writtenQuestionIDs.count == FeatureAccessPolicy.freeWrittenLimit,
              manifest.glossaryTermIDs.count == FeatureAccessPolicy.freeGlossaryLimit,
              Set(manifest.multipleChoiceQuestionIDs).count == manifest.multipleChoiceQuestionIDs.count,
              Set(manifest.writtenQuestionIDs).count == manifest.writtenQuestionIDs.count,
              Set(manifest.glossaryTermIDs).count == manifest.glossaryTermIDs.count
        else { throw CocoaError(.fileReadCorruptFile) }
        return manifest
    }
}
