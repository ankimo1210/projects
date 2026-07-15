import Foundation

public enum PracticeFreeResponseMode: String, Codable, CaseIterable, Hashable, Sendable {
    case written
    case spoken
}

public struct PracticeFreeResponseRubric: Identifiable, Codable, Hashable, Sendable {
    public var id: String
    public var title: String
    public var criteria: [Criterion]
    public var passingPoints: Int?

    public init(
        id: String,
        title: String,
        criteria: [Criterion],
        passingPoints: Int? = nil
    ) {
        self.id = id
        self.title = title
        self.criteria = criteria
        self.passingPoints = passingPoints
    }

    public var maximumPoints: Int {
        criteria.reduce(0) { $0 + $1.maximumPoints }
    }
}

public extension PracticeFreeResponseRubric {
    struct Criterion: Identifiable, Codable, Hashable, Sendable {
        public var id: String
        public var title: String
        public var description: String
        public var maximumPoints: Int
        public var performanceLevels: [PerformanceLevel]

        public init(
            id: String,
            title: String,
            description: String,
            maximumPoints: Int,
            performanceLevels: [PerformanceLevel]
        ) {
            self.id = id
            self.title = title
            self.description = description
            self.maximumPoints = maximumPoints
            self.performanceLevels = performanceLevels
        }
    }

    struct PerformanceLevel: Codable, Hashable, Sendable {
        public var points: Int
        public var label: String
        public var descriptor: String

        public init(points: Int, label: String, descriptor: String) {
            self.points = points
            self.label = label
            self.descriptor = descriptor
        }
    }
}

public struct PracticeRubricEvaluation: Codable, Hashable, Sendable {
    public var rubricID: String
    public var criterionScores: [CriterionScore]
    public var overallFeedback: String?

    public init(
        rubricID: String,
        criterionScores: [CriterionScore],
        overallFeedback: String? = nil
    ) {
        self.rubricID = rubricID
        self.criterionScores = criterionScores
        self.overallFeedback = overallFeedback
    }

    public var earnedPoints: Int {
        criterionScores.reduce(0) { $0 + $1.points }
    }
}

public extension PracticeRubricEvaluation {
    struct CriterionScore: Codable, Hashable, Sendable {
        public var criterionID: String
        public var points: Int
        public var feedback: String?

        public init(criterionID: String, points: Int, feedback: String? = nil) {
            self.criterionID = criterionID
            self.points = points
            self.feedback = feedback
        }
    }
}
