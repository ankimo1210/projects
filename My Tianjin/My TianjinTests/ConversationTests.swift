import SwiftData
import XCTest
@testable import My_Tianjin

@MainActor
final class ConversationTests: XCTestCase {
    func testPromptAndArchiveRoundTripPreserveConversationConfiguration() throws {
        let configuration = ConversationConfiguration(
            level: .level3,
            scenario: .restaurant
        )
        let instructions = ConversationPromptBuilder.instructions(for: configuration)
        XCTAssertTrue(instructions.contains("HSK 3"))
        XCTAssertTrue(instructions.contains("レストラン"))

        let feedback = ConversationFeedback(
            positiveNoteJapanese: "よく続けられました。",
            corrections: [],
            reviewWords: ["点菜"]
        )
        let archive = ConversationArchive(
            id: UUID(),
            configuration: configuration,
            provider: .scriptedFallback,
            startedAt: Date(timeIntervalSince1970: 100),
            endedAt: Date(timeIntervalSince1970: 160),
            messages: [.partner(configuration.scenario.openingReply)],
            feedback: feedback
        )

        let data = try JSONEncoder().encode(archive)
        let restored = try JSONDecoder().decode(ConversationArchive.self, from: data)
        XCTAssertEqual(restored, archive)
        XCTAssertEqual(restored.durationSeconds, 60)
    }

    func testScriptedClientProvidesReplyAndConcreteCorrection() async throws {
        let configuration = ConversationConfiguration(
            level: .level1,
            scenario: .selfIntroduction
        )
        let client = ScriptedConversationClient(configuration: configuration)
        XCTAssertFalse(client.openingReply().suggestedReplies.isEmpty)

        let reply = try await client.reply(to: "我叫是小林。")
        XCTAssertFalse(reply.chinese.isEmpty)
        XCTAssertEqual(reply.suggestedReplies.count, 3)

        let feedback = try await client.feedback(for: [
            ConversationMessage(role: .learner, chinese: "我叫是小林。")
        ])
        XCTAssertEqual(feedback.corrections.count, 1)
        XCTAssertEqual(feedback.corrections.first?.correctedChinese, "我叫小林。")
    }

    func testViewModelCompletesAtMaximumTurns() async {
        let configuration = ConversationConfiguration(
            level: .level1,
            scenario: .dailyLife,
            maximumLearnerTurns: 1,
            timeLimitSeconds: 30
        )
        let client = ScriptedConversationClient(configuration: configuration)
        let viewModel = ConversationViewModel(
            configuration: configuration,
            client: client
        )

        viewModel.start()
        XCTAssertEqual(viewModel.phase, .active)
        _ = await viewModel.send("今天很好。")

        XCTAssertEqual(viewModel.phase, .completed)
        XCTAssertEqual(viewModel.learnerTurnCount, 1)
        XCTAssertNotNil(viewModel.feedback)
        XCTAssertEqual(viewModel.archive?.id, viewModel.sessionID)
    }

    func testFinishWhileWaitingIsSerializedAfterReply() async {
        let configuration = ConversationConfiguration(
            level: .level1,
            scenario: .dailyLife,
            maximumLearnerTurns: 12,
            timeLimitSeconds: 30
        )
        let client = SlowConversationClient(configuration: configuration)
        let viewModel = ConversationViewModel(
            configuration: configuration,
            client: client
        )
        viewModel.start()

        let sendTask = Task { await viewModel.send("今天很好。") }
        await Task.yield()
        XCTAssertEqual(viewModel.phase, .waitingForPartner)

        await viewModel.finish()
        XCTAssertEqual(viewModel.phase, .waitingForPartner)
        _ = await sendTask.value

        XCTAssertEqual(viewModel.phase, .completed)
        XCTAssertNotNil(viewModel.feedback)
        XCTAssertEqual(client.maximumConcurrentCalls, 1)
    }

    func testConversationPersistenceAndReviewWordMapping() throws {
        let configuration = ModelConfiguration(isStoredInMemoryOnly: true)
        let container = try ModelContainer(
            for: StudyProgressRecord.self,
            StudySessionRecord.self,
            ConversationSessionRecord.self,
            configurations: configuration
        )
        let context = ModelContext(container)
        let conversationConfiguration = ConversationConfiguration(
            level: .level1,
            scenario: .studyAndWork
        )
        let archive = ConversationArchive(
            id: UUID(),
            configuration: conversationConfiguration,
            provider: .scriptedFallback,
            startedAt: Date(timeIntervalSince1970: 100),
            endedAt: Date(timeIntervalSince1970: 140),
            messages: [
                .partner(conversationConfiguration.scenario.openingReply),
                ConversationMessage(role: .learner, chinese: "我在学习中文。")
            ],
            feedback: ConversationFeedback(
                positiveNoteJapanese: "よくできました。",
                corrections: [],
                reviewWords: ["学习", "未収録"]
            )
        )

        try ConversationPersistence.save(archive, in: context)
        let records = try context.fetch(FetchDescriptor<ConversationSessionRecord>())
        XCTAssertEqual(records.count, 1)
        XCTAssertEqual(records.first?.archive, archive)

        let vocabulary = [
            VocabularyItem(
                id: "v-study",
                officialIndex: 1,
                hanzi: "学习",
                pinyin: "xuéxí",
                japanese: ["学ぶ"]
            )
        ]
        let markedCount = try ConversationPersistence.markReviewWords(
            archive.feedback.reviewWords,
            vocabulary: vocabulary,
            in: context
        )
        XCTAssertEqual(markedCount, 1)
        XCTAssertNotNil(
            try StudyPersistence.progressMap(in: context, skill: .vocabulary)["v-study"]?.nextReviewAt
        )
    }
}

@MainActor
private final class SlowConversationClient: ConversationClient {
    let provider = ConversationProvider.scriptedFallback
    private let configuration: ConversationConfiguration
    private(set) var maximumConcurrentCalls = 0
    private var activeCallCount = 0

    init(configuration: ConversationConfiguration) {
        self.configuration = configuration
    }

    func openingReply() -> ConversationReply {
        configuration.scenario.openingReply
    }

    func reply(to learnerText: String) async throws -> ConversationReply {
        activeCallCount += 1
        maximumConcurrentCalls = max(maximumConcurrentCalls, activeCallCount)
        try? await Task.sleep(for: .milliseconds(50))
        activeCallCount -= 1
        return configuration.scenario.openingReply
    }

    func feedback(for messages: [ConversationMessage]) async throws -> ConversationFeedback {
        activeCallCount += 1
        maximumConcurrentCalls = max(maximumConcurrentCalls, activeCallCount)
        activeCallCount -= 1
        return ConversationFeedback(
            positiveNoteJapanese: "完了",
            corrections: [],
            reviewWords: []
        )
    }
}
