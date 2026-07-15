import Foundation

public enum StudySessionEngineError: Error, Equatable, LocalizedError {
    case noItems
    case noEligibleItems(StudySessionMode)
    case duplicateItemID(String)
    case emptyItemID
    case emptyCorrectOptionID(String)
    case invalidOptionCount(Int)
    case invalidMaximumItemCount(Int)
    case invalidMinimumAttemptsForWeakMode(Int)
    case insufficientOptions(itemID: String, required: Int, available: Int)

    public var errorDescription: String? {
        switch self {
        case .noItems:
            return "At least one study item is required."
        case let .noEligibleItems(mode):
            return "No items are eligible for the \(mode.rawValue) session mode."
        case let .duplicateItemID(itemID):
            return "Duplicate study item ID: \(itemID)"
        case .emptyItemID:
            return "Study item IDs must not be empty."
        case let .emptyCorrectOptionID(itemID):
            return "The correct option ID is empty for item \(itemID)."
        case let .invalidOptionCount(count):
            return "optionCount must be at least 2; received \(count)."
        case let .invalidMaximumItemCount(count):
            return "maximumItemCount must be positive; received \(count)."
        case let .invalidMinimumAttemptsForWeakMode(count):
            return "minimumAttemptsForWeakMode must be at least 1; received \(count)."
        case let .insufficientOptions(itemID, required, available):
            return "Item \(itemID) needs \(required) options but only \(available) are available."
        }
    }
}

public enum StudySessionEngine {
    private static let questionOrderSalt: UInt64 = 0x51E5_5100_0000_0001
    private static let distractorSalt: UInt64 = 0x51E5_5100_0000_0002
    private static let optionOrderSalt: UInt64 = 0x51E5_5100_0000_0003

    public static func makeSession(
        items: [StudySessionItem],
        progressByItemID: [String: StudyItemProgress] = [:],
        configuration: StudySessionConfiguration,
        startedAt: Date = Date()
    ) throws -> StudySessionState {
        try validate(items: items, configuration: configuration)

        let indexedItems = items.enumerated().map { IndexedItem(index: $0, item: $1) }
        var eligibleItems = selectItems(
            indexedItems,
            progressByItemID: progressByItemID,
            configuration: configuration,
            startedAt: startedAt
        )

        guard !eligibleItems.isEmpty else {
            throw StudySessionEngineError.noEligibleItems(configuration.mode)
        }

        if let maximumItemCount = configuration.maximumItemCount {
            eligibleItems = Array(eligibleItems.prefix(maximumItemCount))
        }

        let questions = try eligibleItems.map { indexedItem in
            try makeQuestion(from: indexedItem.item, configuration: configuration)
        }

        return try StudySessionState(
            configuration: configuration,
            startedAt: startedAt,
            questions: questions
        )
    }

    private static func validate(
        items: [StudySessionItem],
        configuration: StudySessionConfiguration
    ) throws {
        guard !items.isEmpty else {
            throw StudySessionEngineError.noItems
        }
        guard configuration.optionCount >= 2 else {
            throw StudySessionEngineError.invalidOptionCount(configuration.optionCount)
        }
        if let maximumItemCount = configuration.maximumItemCount,
           maximumItemCount <= 0 {
            throw StudySessionEngineError.invalidMaximumItemCount(maximumItemCount)
        }
        guard configuration.minimumAttemptsForWeakMode >= 1 else {
            throw StudySessionEngineError.invalidMinimumAttemptsForWeakMode(
                configuration.minimumAttemptsForWeakMode
            )
        }

        var seenIDs = Set<String>()
        for item in items {
            guard !item.id.isEmpty else {
                throw StudySessionEngineError.emptyItemID
            }
            guard seenIDs.insert(item.id).inserted else {
                throw StudySessionEngineError.duplicateItemID(item.id)
            }
            guard !item.correctOptionID.isEmpty else {
                throw StudySessionEngineError.emptyCorrectOptionID(item.id)
            }
        }
    }

    private static func selectItems(
        _ items: [IndexedItem],
        progressByItemID: [String: StudyItemProgress],
        configuration: StudySessionConfiguration,
        startedAt: Date
    ) -> [IndexedItem] {
        switch configuration.mode {
        case .sequential:
            return items

        case .shuffle:
            return DeterministicShuffle.shuffled(
                items,
                seed: configuration.seed ^ questionOrderSalt
            )

        case .dueReview:
            return items
                .filter { indexedItem in
                    guard let progress = progressByItemID[indexedItem.item.id] else {
                        return configuration.includeUnseenInDueReview
                    }
                    return progress.isDue(at: startedAt)
                }
                .sorted { lhs, rhs in
                    let lhsDate = progressByItemID[lhs.item.id]?.nextReviewAt
                    let rhsDate = progressByItemID[rhs.item.id]?.nextReviewAt

                    switch (lhsDate, rhsDate) {
                    case let (left?, right?) where left != right:
                        return left < right
                    case (_?, nil):
                        return true
                    case (nil, _?):
                        return false
                    default:
                        return lhs.index < rhs.index
                    }
                }

        case .weak:
            let minimumAttempts = max(1, configuration.minimumAttemptsForWeakMode)
            return items
                .filter { indexedItem in
                    guard let progress = progressByItemID[indexedItem.item.id] else {
                        return false
                    }
                    return progress.attemptCount >= minimumAttempts
                        && progress.incorrectCount > 0
                }
                .sorted { lhs, rhs in
                    guard
                        let left = progressByItemID[lhs.item.id],
                        let right = progressByItemID[rhs.item.id]
                    else {
                        return lhs.index < rhs.index
                    }

                    if left.weaknessScore != right.weaknessScore {
                        return left.weaknessScore > right.weaknessScore
                    }
                    if left.incorrectCount != right.incorrectCount {
                        return left.incorrectCount > right.incorrectCount
                    }
                    if left.currentStreak != right.currentStreak {
                        return left.currentStreak < right.currentStreak
                    }
                    return lhs.index < rhs.index
                }
        }
    }

    private static func makeQuestion(
        from item: StudySessionItem,
        configuration: StudySessionConfiguration
    ) throws -> StudySessionQuestionState {
        var seenOptionIDs: Set<String> = [item.correctOptionID]
        let distinctDistractors = item.distractorOptionIDs.filter { optionID in
            guard !optionID.isEmpty else { return false }
            return seenOptionIDs.insert(optionID).inserted
        }

        let requiredDistractorCount = configuration.optionCount - 1
        guard distinctDistractors.count >= requiredDistractorCount else {
            throw StudySessionEngineError.insufficientOptions(
                itemID: item.id,
                required: configuration.optionCount,
                available: distinctDistractors.count + 1
            )
        }

        let distractorSeed = DeterministicShuffle.derivedSeed(
            sessionSeed: configuration.seed,
            identifier: item.id,
            salt: distractorSalt
        )
        let chosenDistractors = DeterministicShuffle
            .shuffled(distinctDistractors, seed: distractorSeed)
            .prefix(requiredDistractorCount)

        let optionSeed = DeterministicShuffle.derivedSeed(
            sessionSeed: configuration.seed,
            identifier: item.id,
            salt: optionOrderSalt
        )
        let optionIDs = DeterministicShuffle.shuffled(
            [item.correctOptionID] + chosenDistractors,
            seed: optionSeed
        )

        return StudySessionQuestionState(
            id: item.id,
            correctOptionID: item.correctOptionID,
            optionIDs: optionIDs
        )
    }

    private struct IndexedItem {
        let index: Int
        let item: StudySessionItem
    }
}
