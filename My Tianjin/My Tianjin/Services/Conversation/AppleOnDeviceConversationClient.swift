import Foundation
import FoundationModels

nonisolated enum AppleConversationAvailability: Equatable, Sendable {
    case available
    case deviceNotEligible
    case appleIntelligenceDisabled
    case modelPreparing
    case chineseUnavailable

    var canUseAppleModel: Bool { self == .available }

    var title: String {
        switch self {
        case .available: "Apple端末内AIを使用"
        case .deviceNotEligible: "端末内シナリオで練習"
        case .appleIntelligenceDisabled: "Apple Intelligenceがオフです"
        case .modelPreparing: "端末内モデルを準備中です"
        case .chineseUnavailable: "中国語モデルを利用できません"
        }
    }

    var detail: String {
        switch self {
        case .available:
            "会話の生成は端末内で完結し、API料金はかかりません。"
        case .deviceNotEligible:
            "この端末ではApple Intelligenceを使えないため、内蔵シナリオが応答します。"
        case .appleIntelligenceDisabled:
            "設定でApple Intelligenceを有効にするまでは、内蔵シナリオが応答します。"
        case .modelPreparing:
            "モデルの準備が完了するまでは、内蔵シナリオが応答します。"
        case .chineseUnavailable:
            "現在の言語構成では中国語生成を使えないため、内蔵シナリオが応答します。"
        }
    }
}

@MainActor
enum ConversationClientFactory {
    static func appleAvailability() -> AppleConversationAvailability {
        let model = SystemLanguageModel.default
        switch model.availability {
        case .available:
            return model.supportsLocale(Locale(identifier: "zh-Hans-CN"))
                ? .available
                : .chineseUnavailable
        case let .unavailable(reason):
            switch reason {
            case .deviceNotEligible: return .deviceNotEligible
            case .appleIntelligenceNotEnabled: return .appleIntelligenceDisabled
            case .modelNotReady: return .modelPreparing
            @unknown default: return .modelPreparing
            }
        }
    }

    static func make(configuration: ConversationConfiguration) -> any ConversationClient {
        if appleAvailability().canUseAppleModel {
            return AppleOnDeviceConversationClient(configuration: configuration)
        }
        return ScriptedConversationClient(configuration: configuration)
    }
}

@MainActor
final class AppleOnDeviceConversationClient: ConversationClient {
    let provider = ConversationProvider.appleOnDevice

    private let configuration: ConversationConfiguration
    private let session: LanguageModelSession
    private var isFirstTurn = true

    init(configuration: ConversationConfiguration) {
        self.configuration = configuration
        session = LanguageModelSession(
            model: .default,
            instructions: ConversationPromptBuilder.instructions(for: configuration)
        )
        session.prewarm()
    }

    func openingReply() -> ConversationReply {
        configuration.scenario.openingReply
    }

    func reply(to learnerText: String) async throws -> ConversationReply {
        let prompt = ConversationPromptBuilder.replyPrompt(
            learnerText: learnerText,
            openingText: configuration.scenario.openingReply.chinese,
            isFirstTurn: isFirstTurn
        )
        let response = try await session.respond(to: prompt + Self.replyJSONInstruction)
        isFirstTurn = false
        let generated = try Self.decodeJSON(
            GeneratedConversationReply.self,
            from: response.content
        )
        let chinese = generated.chinese.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !chinese.isEmpty else { throw ConversationClientError.emptyResponse }

        return ConversationReply(
            chinese: chinese,
            pinyin: generated.pinyin.trimmingCharacters(in: .whitespacesAndNewlines),
            japanese: generated.japanese.trimmingCharacters(in: .whitespacesAndNewlines),
            suggestedReplies: [
                generated.suggestedReply1,
                generated.suggestedReply2,
                generated.suggestedReply3
            ].map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
                .filter { !$0.isEmpty },
            hintJapanese: generated.hintJapanese.trimmingCharacters(in: .whitespacesAndNewlines)
        )
    }

    func feedback(for messages: [ConversationMessage]) async throws -> ConversationFeedback {
        let feedbackSession = LanguageModelSession(
            model: .default,
            instructions: "You are a concise Mandarin tutor for native Japanese learners. Feedback and explanations must be in Japanese."
        )
        let prompt = ConversationPromptBuilder.feedbackPrompt(
            configuration: configuration,
            messages: messages
        )
        let response = try await feedbackSession.respond(
            to: prompt + Self.feedbackJSONInstruction
        )
        let generated = try Self.decodeJSON(
            GeneratedConversationFeedback.self,
            from: response.content
        )
        return ConversationFeedback(
            positiveNoteJapanese: generated.positiveNoteJapanese
                .trimmingCharacters(in: .whitespacesAndNewlines),
            corrections: generated.corrections.prefix(3).map {
                ConversationCorrection(
                    originalChinese: $0.originalChinese.trimmingCharacters(in: .whitespacesAndNewlines),
                    correctedChinese: $0.correctedChinese.trimmingCharacters(in: .whitespacesAndNewlines),
                    explanationJapanese: $0.explanationJapanese
                        .trimmingCharacters(in: .whitespacesAndNewlines)
                )
            },
            reviewWords: Array(
                Set(generated.reviewWords.map {
                    $0.trimmingCharacters(in: .whitespacesAndNewlines)
                }.filter { !$0.isEmpty })
            ).sorted().prefix(5).map { $0 }
        )
    }

    private static let replyJSONInstruction = """

    Return only one valid JSON object with exactly these string keys:
    {"chinese":"...","pinyin":"...","japanese":"...","suggestedReply1":"...","suggestedReply2":"...","suggestedReply3":"...","hintJapanese":"..."}
    Do not use Markdown or code fences.
    """

    private static let feedbackJSONInstruction = """

    Return only one valid JSON object in this exact shape:
    {"positiveNoteJapanese":"...","corrections":[{"originalChinese":"...","correctedChinese":"...","explanationJapanese":"..."}],"reviewWords":["..."]}
    corrections must contain at most 3 items and reviewWords at most 5 items. Do not use Markdown or code fences.
    """

    private static func decodeJSON<Value: Decodable>(
        _ type: Value.Type,
        from rawText: String
    ) throws -> Value {
        let text = rawText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let start = text.firstIndex(of: "{"),
              let end = text.lastIndex(of: "}"),
              start <= end else {
            throw ConversationClientError.emptyResponse
        }
        let json = String(text[start...end])
        return try JSONDecoder().decode(Value.self, from: Data(json.utf8))
    }
}

private struct GeneratedConversationReply: Decodable {
    let chinese: String
    let pinyin: String
    let japanese: String
    let suggestedReply1: String
    let suggestedReply2: String
    let suggestedReply3: String
    let hintJapanese: String
}

private struct GeneratedConversationCorrection: Decodable {
    let originalChinese: String
    let correctedChinese: String
    let explanationJapanese: String
}

private struct GeneratedConversationFeedback: Decodable {
    let positiveNoteJapanese: String
    let corrections: [GeneratedConversationCorrection]
    let reviewWords: [String]
}
