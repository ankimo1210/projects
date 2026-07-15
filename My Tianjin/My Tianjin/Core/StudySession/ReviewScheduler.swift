import Foundation

public enum StudyReviewResult: String, Codable, CaseIterable, Sendable {
    case incorrect
    case correct
}

/// Persistence-neutral progress for one content item and one learning skill.
/// A SwiftData model can map to and from this value without coupling the core
/// scheduling logic to a storage framework.
public struct StudyItemProgress: Codable, Hashable, Sendable {
    public let itemID: String
    public var attemptCount: Int
    public var correctCount: Int
    public var incorrectCount: Int
    public var currentStreak: Int
    public var reviewStage: Int
    public var lastReviewedAt: Date?
    public var nextReviewAt: Date?

    public init(
        itemID: String,
        attemptCount: Int = 0,
        correctCount: Int = 0,
        incorrectCount: Int = 0,
        currentStreak: Int = 0,
        reviewStage: Int = 0,
        lastReviewedAt: Date? = nil,
        nextReviewAt: Date? = nil
    ) {
        self.itemID = itemID
        self.attemptCount = max(0, attemptCount)
        self.correctCount = max(0, correctCount)
        self.incorrectCount = max(0, incorrectCount)
        self.currentStreak = max(0, currentStreak)
        self.reviewStage = max(0, reviewStage)
        self.lastReviewedAt = lastReviewedAt
        self.nextReviewAt = nextReviewAt
    }

    public var accuracy: Double? {
        guard attemptCount > 0 else { return nil }
        return Double(correctCount) / Double(attemptCount)
    }

    public var weaknessScore: Double {
        guard attemptCount > 0 else { return 0 }
        return Double(incorrectCount) / Double(attemptCount)
    }

    public func isDue(at date: Date) -> Bool {
        guard let nextReviewAt else { return false }
        return nextReviewAt <= date
    }
}

public struct ReviewSchedulerConfiguration: Codable, Hashable, Sendable {
    /// Intervals used after consecutive correct answers.
    public let correctIntervals: [TimeInterval]
    /// Delay before an incorrectly answered item becomes due again.
    public let incorrectRetryInterval: TimeInterval

    public init(
        correctIntervals: [TimeInterval] = [
            86_400,
            3 * 86_400,
            7 * 86_400,
            14 * 86_400,
            30 * 86_400,
            90 * 86_400
        ],
        incorrectRetryInterval: TimeInterval = 10 * 60
    ) {
        precondition(
            !correctIntervals.isEmpty && correctIntervals.allSatisfy { $0 > 0 },
            "correctIntervals must contain positive values"
        )
        precondition(
            incorrectRetryInterval > 0,
            "incorrectRetryInterval must be positive"
        )

        self.correctIntervals = correctIntervals
        self.incorrectRetryInterval = incorrectRetryInterval
    }
}

public protocol ReviewScheduling: Sendable {
    func updatedProgress(
        itemID: String,
        previous: StudyItemProgress?,
        result: StudyReviewResult,
        reviewedAt: Date
    ) -> StudyItemProgress
}

/// A deliberately simple fixed-interval scheduler. Its API is replaceable by a
/// more advanced spaced-repetition algorithm without changing session state.
public struct ReviewScheduler: ReviewScheduling, Sendable {
    public let configuration: ReviewSchedulerConfiguration

    public init(configuration: ReviewSchedulerConfiguration = .init()) {
        self.configuration = configuration
    }

    public func updatedProgress(
        itemID: String,
        previous: StudyItemProgress? = nil,
        result: StudyReviewResult,
        reviewedAt: Date = Date()
    ) -> StudyItemProgress {
        var progress = previous ?? StudyItemProgress(itemID: itemID)

        // Protect against accidentally applying another item's progress.
        if progress.itemID != itemID {
            progress = StudyItemProgress(itemID: itemID)
        }

        progress.attemptCount += 1
        progress.lastReviewedAt = reviewedAt

        switch result {
        case .correct:
            progress.correctCount += 1
            progress.currentStreak += 1

            let intervalIndex = min(
                progress.reviewStage,
                configuration.correctIntervals.count - 1
            )
            let interval = configuration.correctIntervals[intervalIndex]
            progress.nextReviewAt = reviewedAt.addingTimeInterval(interval)
            progress.reviewStage = min(
                progress.reviewStage + 1,
                configuration.correctIntervals.count
            )

        case .incorrect:
            progress.incorrectCount += 1
            progress.currentStreak = 0
            progress.reviewStage = 0
            progress.nextReviewAt = reviewedAt.addingTimeInterval(
                configuration.incorrectRetryInterval
            )
        }

        return progress
    }
}
