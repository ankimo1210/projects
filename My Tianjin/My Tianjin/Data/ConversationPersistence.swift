import Foundation
import SwiftData

@Model
final class ConversationSessionRecord {
    @Attribute(.unique) var id: String
    var startedAt: Date
    var endedAt: Date
    var levelRawValue: String
    var scenarioRawValue: String
    var providerRawValue: String
    var learnerTurnCount: Int
    var durationSeconds: Int
    var payload: Data

    init(archive: ConversationArchive, payload: Data) {
        id = archive.id.uuidString
        startedAt = archive.startedAt
        endedAt = archive.endedAt
        levelRawValue = archive.configuration.level.rawValue
        scenarioRawValue = archive.configuration.scenario.rawValue
        providerRawValue = archive.provider.rawValue
        learnerTurnCount = archive.messages.filter { $0.role == .learner }.count
        durationSeconds = archive.durationSeconds
        self.payload = payload
    }

    var archive: ConversationArchive? {
        try? JSONDecoder().decode(ConversationArchive.self, from: payload)
    }

    var level: HSKLevel? { HSKLevel(rawValue: levelRawValue) }
    var scenario: ConversationScenario? { ConversationScenario(rawValue: scenarioRawValue) }
    var provider: ConversationProvider? { ConversationProvider(rawValue: providerRawValue) }
}

@MainActor
enum ConversationPersistence {
    static func save(
        _ archive: ConversationArchive,
        in context: ModelContext
    ) throws {
        let id = archive.id.uuidString
        let payload = try JSONEncoder().encode(archive)
        let descriptor = FetchDescriptor<ConversationSessionRecord>(
            predicate: #Predicate { $0.id == id }
        )
        if let existing = try context.fetch(descriptor).first {
            existing.startedAt = archive.startedAt
            existing.endedAt = archive.endedAt
            existing.levelRawValue = archive.configuration.level.rawValue
            existing.scenarioRawValue = archive.configuration.scenario.rawValue
            existing.providerRawValue = archive.provider.rawValue
            existing.learnerTurnCount = archive.messages.filter { $0.role == .learner }.count
            existing.durationSeconds = archive.durationSeconds
            existing.payload = payload
        } else {
            context.insert(ConversationSessionRecord(archive: archive, payload: payload))
        }
        try context.save()
    }

    @discardableResult
    static func markReviewWords(
        _ words: [String],
        vocabulary: [VocabularyItem],
        in context: ModelContext
    ) throws -> Int {
        let normalizedWords = Set(words.map(normalize).filter { !$0.isEmpty })
        let matchedItems = vocabulary.filter { item in
            normalizedWords.contains(normalize(item.hanzi))
                || item.traditional.map { normalizedWords.contains(normalize($0)) } == true
        }

        for item in Dictionary(grouping: matchedItems, by: \VocabularyItem.id).compactMap(\.value.first) {
            try StudyPersistence.markForReview(
                itemID: item.id,
                skill: .vocabulary,
                in: context
            )
        }
        return Set(matchedItems.map(\.id)).count
    }

    private static func normalize(_ value: String) -> String {
        value
            .trimmingCharacters(in: .whitespacesAndNewlines.union(.punctuationCharacters))
            .replacingOccurrences(of: " ", with: "")
    }
}
