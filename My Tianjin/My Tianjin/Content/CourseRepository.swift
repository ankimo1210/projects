import Foundation

nonisolated enum CourseRepositoryError: Error, LocalizedError {
    case resourceNotFound(String)
    case unreadableResource(resource: String, reason: String)
    case decodingFailed(reason: String)
    case validationFailed(CourseValidationError)

    var errorDescription: String? {
        switch self {
        case let .resourceNotFound(resource):
            "コース教材が見つかりません: \(resource)"
        case let .unreadableResource(resource, reason):
            "コース教材を読み込めません: \(resource)（\(reason)）"
        case let .decodingFailed(reason):
            "コース教材のJSONを解析できません（\(reason)）"
        case let .validationFailed(error):
            error.localizedDescription
        }
    }
}

nonisolated struct CourseRepository: Sendable {
    static let defaultResource = "hsk3-first-lesson.json"

    private let dataLoader: @Sendable () throws -> Data

    init(bundle: Bundle = .main) {
        dataLoader = {
            let resourceName = "hsk3-first-lesson"
            let candidates = ["Resources/Content", "Content"]
                .compactMap { bundle.url(forResource: resourceName, withExtension: "json", subdirectory: $0) }
                + [bundle.url(forResource: resourceName, withExtension: "json")].compactMap { $0 }
            guard let url = candidates.first else {
                throw CourseRepositoryError.resourceNotFound(Self.defaultResource)
            }
            do {
                return try Data(contentsOf: url, options: .mappedIfSafe)
            } catch {
                throw CourseRepositoryError.unreadableResource(
                    resource: Self.defaultResource,
                    reason: error.localizedDescription
                )
            }
        }
    }

    init(dataLoader: @escaping @Sendable () throws -> Data) {
        self.dataLoader = dataLoader
    }

    func loadLesson() throws -> CourseLesson {
        let data = try dataLoader()
        let lesson: CourseLesson
        do {
            lesson = try JSONDecoder().decode(CourseLesson.self, from: data)
        } catch {
            throw CourseRepositoryError.decodingFailed(reason: error.localizedDescription)
        }
        do {
            try lesson.validate()
        } catch let error as CourseValidationError {
            throw CourseRepositoryError.validationFailed(error)
        }
        return lesson
    }
}
