import Foundation
import SwiftData

nonisolated struct MockOutcomeResult: Codable, Hashable {
    let correct: Int
    let total: Int
}

@Model
final class MockExamSession {
    @Attribute(.unique) var id: UUID
    var completedAt: Date
    var correctCount: Int
    var questionCount: Int
    var outcomeResultsData: Data
    var missedQuestionIDsData: Data

    init(
        id: UUID = UUID(),
        completedAt: Date = .now,
        correctCount: Int,
        questionCount: Int,
        outcomeResults: [String: MockOutcomeResult],
        missedQuestionIDs: [String]
    ) {
        self.id = id
        self.completedAt = completedAt
        self.correctCount = correctCount
        self.questionCount = questionCount
        outcomeResultsData = (try? JSONEncoder().encode(outcomeResults)) ?? Data("{}".utf8)
        missedQuestionIDsData = (try? JSONEncoder().encode(missedQuestionIDs)) ?? Data("[]".utf8)
    }

    var score: Double {
        guard questionCount > 0 else { return 0 }
        return Double(correctCount) / Double(questionCount)
    }

    var outcomeResults: [String: MockOutcomeResult] {
        (try? JSONDecoder().decode([String: MockOutcomeResult].self, from: outcomeResultsData)) ?? [:]
    }

    var missedQuestionIDs: [String] {
        (try? JSONDecoder().decode([String].self, from: missedQuestionIDsData)) ?? []
    }
}
