import Foundation

public enum StudySessionMode: String, Codable, CaseIterable, Sendable {
    case sequential
    case shuffle
    case dueReview
    case weak
}

public struct StudySessionConfiguration: Codable, Hashable, Sendable {
    public let mode: StudySessionMode
    public let seed: UInt64
    public let optionCount: Int
    public let maximumItemCount: Int?
    public let includeUnseenInDueReview: Bool
    public let minimumAttemptsForWeakMode: Int

    public init(
        mode: StudySessionMode,
        seed: UInt64,
        optionCount: Int = 4,
        maximumItemCount: Int? = nil,
        includeUnseenInDueReview: Bool = false,
        minimumAttemptsForWeakMode: Int = 1
    ) {
        self.mode = mode
        self.seed = seed
        self.optionCount = optionCount
        self.maximumItemCount = maximumItemCount
        self.includeUnseenInDueReview = includeUnseenInDueReview
        self.minimumAttemptsForWeakMode = minimumAttemptsForWeakMode
    }
}

/// Input used to build a frozen question snapshot.
public struct StudySessionItem: Codable, Hashable, Identifiable, Sendable {
    public let id: String
    public let correctOptionID: String
    public let distractorOptionIDs: [String]

    public init(
        id: String,
        correctOptionID: String,
        distractorOptionIDs: [String]
    ) {
        self.id = id
        self.correctOptionID = correctOptionID
        self.distractorOptionIDs = distractorOptionIDs
    }
}

public struct StudySessionQuestionState: Codable, Hashable, Identifiable, Sendable {
    public let id: String
    public let correctOptionID: String
    /// This order is generated once and persisted for the lifetime of a session.
    public let optionIDs: [String]
    public private(set) var selectedOptionID: String?
    public private(set) var answeredAt: Date?

    public init(
        id: String,
        correctOptionID: String,
        optionIDs: [String],
        selectedOptionID: String? = nil,
        answeredAt: Date? = nil
    ) {
        self.id = id
        self.correctOptionID = correctOptionID
        self.optionIDs = optionIDs
        self.selectedOptionID = selectedOptionID
        self.answeredAt = answeredAt
    }

    public var isAnswered: Bool {
        selectedOptionID != nil
    }

    public var isCorrect: Bool? {
        guard let selectedOptionID else { return nil }
        return selectedOptionID == correctOptionID
    }

    mutating func recordSelection(_ optionID: String, at date: Date) {
        selectedOptionID = optionID
        answeredAt = date
    }
}

public struct StudySessionAnswer: Codable, Hashable, Identifiable, Sendable {
    public let sequence: Int
    public let itemID: String
    public let selectedOptionID: String
    public let correctOptionID: String
    public let isCorrect: Bool
    public let answeredAt: Date

    public init(
        sequence: Int,
        itemID: String,
        selectedOptionID: String,
        correctOptionID: String,
        isCorrect: Bool,
        answeredAt: Date
    ) {
        self.sequence = sequence
        self.itemID = itemID
        self.selectedOptionID = selectedOptionID
        self.correctOptionID = correctOptionID
        self.isCorrect = isCorrect
        self.answeredAt = answeredAt
    }

    public var id: Int { sequence }
}

public enum StudySessionNavigationResult: Equatable, Sendable {
    case moved(toIndex: Int)
    case completed
}

public enum StudySessionStateError: Error, Equatable, LocalizedError {
    case invalidState(String)
    case sessionCompleted
    case currentQuestionAlreadyAnswered
    case currentQuestionNotAnswered
    case optionNotInCurrentQuestion(String)

    public var errorDescription: String? {
        switch self {
        case let .invalidState(reason):
            return "Invalid study session state: \(reason)"
        case .sessionCompleted:
            return "The study session is already complete."
        case .currentQuestionAlreadyAnswered:
            return "The current question has already been answered."
        case .currentQuestionNotAnswered:
            return "Answer the current question before continuing."
        case let .optionNotInCurrentQuestion(optionID):
            return "Option '\(optionID)' does not belong to the current question."
        }
    }
}

/// Complete, Codable session state. Persisting this value preserves the exact
/// question order, option order, current position, and answer history.
public struct StudySessionState: Codable, Hashable, Sendable {
    public static let currentSchemaVersion = 1

    public let schemaVersion: Int
    public let configuration: StudySessionConfiguration
    public let startedAt: Date
    public private(set) var updatedAt: Date
    public private(set) var questions: [StudySessionQuestionState]
    public private(set) var currentIndex: Int
    public private(set) var answerHistory: [StudySessionAnswer]
    public private(set) var completedAt: Date?

    public init(
        configuration: StudySessionConfiguration,
        startedAt: Date,
        questions: [StudySessionQuestionState]
    ) throws {
        schemaVersion = Self.currentSchemaVersion
        self.configuration = configuration
        self.startedAt = startedAt
        updatedAt = startedAt
        self.questions = questions
        currentIndex = 0
        answerHistory = []
        completedAt = nil
        try validate()
    }

    public var isComplete: Bool {
        completedAt != nil
    }

    public var currentQuestion: StudySessionQuestionState? {
        guard !isComplete, questions.indices.contains(currentIndex) else {
            return nil
        }
        return questions[currentIndex]
    }

    public var answeredCount: Int {
        questions.lazy.filter(\.isAnswered).count
    }

    public var correctCount: Int {
        answerHistory.lazy.filter(\.isCorrect).count
    }

    public var canGoBack: Bool {
        isComplete || currentIndex > 0
    }

    public var canAdvance: Bool {
        !isComplete && currentQuestion?.isAnswered == true
    }

    @discardableResult
    public mutating func recordAnswer(
        optionID: String,
        at date: Date = Date()
    ) throws -> StudySessionAnswer {
        guard !isComplete else {
            throw StudySessionStateError.sessionCompleted
        }
        guard questions.indices.contains(currentIndex) else {
            throw StudySessionStateError.invalidState("currentIndex is out of range")
        }
        guard !questions[currentIndex].isAnswered else {
            throw StudySessionStateError.currentQuestionAlreadyAnswered
        }
        guard questions[currentIndex].optionIDs.contains(optionID) else {
            throw StudySessionStateError.optionNotInCurrentQuestion(optionID)
        }

        questions[currentIndex].recordSelection(optionID, at: date)
        let question = questions[currentIndex]
        let answer = StudySessionAnswer(
            sequence: answerHistory.count + 1,
            itemID: question.id,
            selectedOptionID: optionID,
            correctOptionID: question.correctOptionID,
            isCorrect: optionID == question.correctOptionID,
            answeredAt: date
        )
        answerHistory.append(answer)
        updatedAt = date
        return answer
    }

    @discardableResult
    public mutating func advance(
        at date: Date = Date()
    ) throws -> StudySessionNavigationResult {
        guard !isComplete else {
            throw StudySessionStateError.sessionCompleted
        }
        guard currentQuestion?.isAnswered == true else {
            throw StudySessionStateError.currentQuestionNotAnswered
        }

        updatedAt = date
        if currentIndex == questions.count - 1 {
            completedAt = date
            return .completed
        }

        currentIndex += 1
        return .moved(toIndex: currentIndex)
    }

    /// From the completion screen this reopens the final question; otherwise it
    /// moves to the preceding question while preserving its previous answer.
    @discardableResult
    public mutating func goBack(at date: Date = Date()) -> Bool {
        if isComplete {
            completedAt = nil
            updatedAt = date
            return true
        }

        guard currentIndex > 0 else { return false }
        currentIndex -= 1
        updatedAt = date
        return true
    }

    public func encoded(using encoder: JSONEncoder = JSONEncoder()) throws -> Data {
        try encoder.encode(self)
    }

    public static func restore(
        from data: Data,
        using decoder: JSONDecoder = JSONDecoder()
    ) throws -> StudySessionState {
        try decoder.decode(StudySessionState.self, from: data)
    }

    public func validate() throws {
        guard schemaVersion == Self.currentSchemaVersion else {
            throw StudySessionStateError.invalidState(
                "unsupported schema version \(schemaVersion)"
            )
        }
        guard !questions.isEmpty else {
            throw StudySessionStateError.invalidState("questions must not be empty")
        }
        guard questions.indices.contains(currentIndex) else {
            throw StudySessionStateError.invalidState("currentIndex is out of range")
        }
        guard configuration.optionCount >= 2 else {
            throw StudySessionStateError.invalidState("optionCount must be at least 2")
        }
        if let maximumItemCount = configuration.maximumItemCount,
           maximumItemCount <= 0 {
            throw StudySessionStateError.invalidState(
                "maximumItemCount must be positive"
            )
        }
        guard configuration.minimumAttemptsForWeakMode >= 1 else {
            throw StudySessionStateError.invalidState(
                "minimumAttemptsForWeakMode must be at least 1"
            )
        }

        var seenQuestionIDs = Set<String>()
        for question in questions {
            guard !question.id.isEmpty else {
                throw StudySessionStateError.invalidState("question ID must not be empty")
            }
            guard seenQuestionIDs.insert(question.id).inserted else {
                throw StudySessionStateError.invalidState(
                    "duplicate question ID: \(question.id)"
                )
            }
            guard question.optionIDs.contains(question.correctOptionID) else {
                throw StudySessionStateError.invalidState(
                    "correct option is missing for \(question.id)"
                )
            }
            guard Set(question.optionIDs).count == question.optionIDs.count else {
                throw StudySessionStateError.invalidState(
                    "duplicate options for \(question.id)"
                )
            }
            guard question.optionIDs.count == configuration.optionCount else {
                throw StudySessionStateError.invalidState(
                    "unexpected option count for \(question.id)"
                )
            }
            guard question.isAnswered == (question.answeredAt != nil) else {
                throw StudySessionStateError.invalidState(
                    "answer and timestamp disagree for \(question.id)"
                )
            }
            if let selectedOptionID = question.selectedOptionID,
               !question.optionIDs.contains(selectedOptionID) {
                throw StudySessionStateError.invalidState(
                    "selected option is invalid for \(question.id)"
                )
            }
        }

        guard answerHistory.count == answeredCount else {
            throw StudySessionStateError.invalidState(
                "answer history does not match answered questions"
            )
        }

        let questionByID = Dictionary(
            uniqueKeysWithValues: questions.map { ($0.id, $0) }
        )
        var answeredItemIDs = Set<String>()
        for (offset, answer) in answerHistory.enumerated() {
            guard answer.sequence == offset + 1 else {
                throw StudySessionStateError.invalidState(
                    "answer history sequence is not contiguous"
                )
            }
            guard answeredItemIDs.insert(answer.itemID).inserted else {
                throw StudySessionStateError.invalidState(
                    "duplicate answer history for \(answer.itemID)"
                )
            }
            guard let question = questionByID[answer.itemID],
                  question.selectedOptionID == answer.selectedOptionID,
                  question.correctOptionID == answer.correctOptionID,
                  question.isCorrect == answer.isCorrect,
                  question.answeredAt == answer.answeredAt else {
                throw StudySessionStateError.invalidState(
                    "answer history is inconsistent for \(answer.itemID)"
                )
            }
        }

        if completedAt != nil,
           questions.contains(where: { !$0.isAnswered }) {
            throw StudySessionStateError.invalidState(
                "a completed session contains unanswered questions"
            )
        }
        if completedAt != nil, currentIndex != questions.count - 1 {
            throw StudySessionStateError.invalidState(
                "a completed session is not positioned at the final question"
            )
        }
    }

    private enum CodingKeys: String, CodingKey {
        case schemaVersion
        case configuration
        case startedAt
        case updatedAt
        case questions
        case currentIndex
        case answerHistory
        case completedAt
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        schemaVersion = try container.decode(Int.self, forKey: .schemaVersion)
        configuration = try container.decode(
            StudySessionConfiguration.self,
            forKey: .configuration
        )
        startedAt = try container.decode(Date.self, forKey: .startedAt)
        updatedAt = try container.decode(Date.self, forKey: .updatedAt)
        questions = try container.decode(
            [StudySessionQuestionState].self,
            forKey: .questions
        )
        currentIndex = try container.decode(Int.self, forKey: .currentIndex)
        answerHistory = try container.decode(
            [StudySessionAnswer].self,
            forKey: .answerHistory
        )
        completedAt = try container.decodeIfPresent(Date.self, forKey: .completedAt)
        try validate()
    }
}
