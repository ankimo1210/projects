import Foundation

public struct PracticePassage: Identifiable, Codable, Hashable, Sendable {
    public var id: String
    public var title: String?
    public var level: PracticeHSKLevel
    public var genre: Genre
    public var segments: [Segment]
    public var estimatedReadingSeconds: Int?
    public var source: Source?

    public init(
        id: String,
        title: String? = nil,
        level: PracticeHSKLevel,
        genre: Genre,
        segments: [Segment],
        estimatedReadingSeconds: Int? = nil,
        source: Source? = nil
    ) {
        self.id = id
        self.title = title
        self.level = level
        self.genre = genre
        self.segments = segments
        self.estimatedReadingSeconds = estimatedReadingSeconds
        self.source = source
    }

    public var fullText: String {
        segments.map(\.content.text).joined(separator: "\n")
    }
}

public extension PracticePassage {
    enum Genre: String, Codable, CaseIterable, Hashable, Sendable {
        case dialogue
        case narrative
        case informational
        case news
        case scientific
        case academic
        case cultural
        case opinion
    }

    struct Segment: Identifiable, Codable, Hashable, Sendable {
        public var id: String
        public var content: PracticeText

        public init(id: String, content: PracticeText) {
            self.id = id
            self.content = content
        }
    }

    struct Source: Codable, Hashable, Sendable {
        public var kind: Kind
        public var title: String?
        public var attribution: String?
        public var licenseIdentifier: String?
        public var sourceURL: String?

        public init(
            kind: Kind,
            title: String? = nil,
            attribution: String? = nil,
            licenseIdentifier: String? = nil,
            sourceURL: String? = nil
        ) {
            self.kind = kind
            self.title = title
            self.attribution = attribution
            self.licenseIdentifier = licenseIdentifier
            self.sourceURL = sourceURL
        }

        public enum Kind: String, Codable, CaseIterable, Hashable, Sendable {
            case original
            case licensed
            case publicDomain
            case userProvided
        }
    }
}
