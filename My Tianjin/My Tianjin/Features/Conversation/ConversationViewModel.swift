import Combine
import Foundation

nonisolated enum ConversationPhase: Equatable, Sendable {
    case preparing
    case active
    case waitingForPartner
    case reviewing
    case completed
}

@MainActor
final class ConversationViewModel: ObservableObject {
    @Published private(set) var messages: [ConversationMessage] = []
    @Published private(set) var phase = ConversationPhase.preparing
    @Published private(set) var secondsRemaining: Int
    @Published private(set) var learnerTurnCount = 0
    @Published private(set) var provider: ConversationProvider
    @Published private(set) var feedback: ConversationFeedback?
    @Published var errorMessage: String?
    @Published private(set) var providerNotice: String?

    let configuration: ConversationConfiguration
    let sessionID = UUID()
    private(set) var startedAt = Date()
    private(set) var endedAt: Date?

    private var client: any ConversationClient
    private var timerTask: Task<Void, Never>?
    private var finishRequested = false

    init(
        configuration: ConversationConfiguration,
        client: (any ConversationClient)? = nil
    ) {
        self.configuration = configuration
        secondsRemaining = configuration.timeLimitSeconds
        let selectedClient = client ?? ConversationClientFactory.make(configuration: configuration)
        self.client = selectedClient
        provider = selectedClient.provider
    }

    var canSend: Bool {
        phase == .active && learnerTurnCount < configuration.maximumLearnerTurns
    }

    var progressLabel: String {
        "\(learnerTurnCount) / \(configuration.maximumLearnerTurns)往復"
    }

    var timeLabel: String {
        String(format: "%d:%02d", secondsRemaining / 60, secondsRemaining % 60)
    }

    var latestPartnerMessage: ConversationMessage? {
        messages.last { $0.role == .partner }
    }

    var archive: ConversationArchive? {
        guard let feedback, let endedAt else { return nil }
        return ConversationArchive(
            id: sessionID,
            configuration: configuration,
            provider: provider,
            startedAt: startedAt,
            endedAt: endedAt,
            messages: messages,
            feedback: feedback
        )
    }

    func start() {
        guard phase == .preparing else { return }
        startedAt = Date()
        messages = [.partner(client.openingReply())]
        phase = .active
        startTimer()
    }

    func send(_ rawText: String) async -> ConversationMessage? {
        let text = rawText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard canSend, !text.isEmpty else { return nil }

        errorMessage = nil
        messages.append(ConversationMessage(role: .learner, chinese: text))
        learnerTurnCount += 1
        phase = .waitingForPartner

        do {
            let reply: ConversationReply
            do {
                reply = try await client.reply(to: text)
            } catch {
                guard provider == .appleOnDevice else { throw error }
                switchToFallback(reason: error)
                reply = try await client.reply(to: text)
            }
            let message = ConversationMessage.partner(reply)
            messages.append(message)

            if finishRequested || learnerTurnCount >= configuration.maximumLearnerTurns {
                phase = .active
                await finish()
            } else {
                phase = .active
            }
            return message
        } catch {
            errorMessage = error.localizedDescription
            if finishRequested {
                phase = .active
                await finish()
            } else {
                phase = .active
            }
            return nil
        }
    }

    func finish() async {
        guard phase != .completed, phase != .reviewing else { return }
        if phase == .waitingForPartner {
            finishRequested = true
            timerTask?.cancel()
            timerTask = nil
            return
        }
        finishRequested = false
        timerTask?.cancel()
        timerTask = nil
        phase = .reviewing

        do {
            do {
                feedback = try await client.feedback(for: messages)
            } catch {
                guard provider == .appleOnDevice else { throw error }
                switchToFallback(reason: error)
                feedback = try await client.feedback(for: messages)
            }
        } catch {
            errorMessage = "振り返りの生成に失敗しました。\(error.localizedDescription)"
            feedback = ConversationFeedback(
                positiveNoteJapanese: "中国語で会話を続けたこと自体が大切な練習です。今回の表現をもう一度声に出して復習しましょう。",
                corrections: [],
                reviewWords: []
            )
        }
        endedAt = Date()
        phase = .completed
    }

    func cancelTimer() {
        timerTask?.cancel()
        timerTask = nil
    }

    private func startTimer() {
        timerTask?.cancel()
        timerTask = Task { [weak self] in
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(1))
                guard !Task.isCancelled, let self else { return }
                secondsRemaining = max(0, secondsRemaining - 1)
                if secondsRemaining == 0 {
                    await finish()
                    return
                }
            }
        }
    }

    private func switchToFallback(reason: Error) {
        client = ScriptedConversationClient(configuration: configuration)
        provider = .scriptedFallback
        providerNotice = "Apple端末内AIの応答を続けられなかったため、内蔵シナリオに切り替えました。"
#if DEBUG
        print("Conversation model fallback: \(reason.localizedDescription)")
#endif
    }
}
