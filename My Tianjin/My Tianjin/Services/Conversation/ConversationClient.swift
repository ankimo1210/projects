import Foundation

@MainActor
protocol ConversationClient: AnyObject {
    var provider: ConversationProvider { get }

    func openingReply() -> ConversationReply
    func reply(to learnerText: String) async throws -> ConversationReply
    func feedback(for messages: [ConversationMessage]) async throws -> ConversationFeedback
}
nonisolated enum ConversationClientError: LocalizedError, Sendable {
    case emptyResponse
    case modelUnavailable(String)
    case speechUnavailable(String)
    case permissionDenied(String)
    case noSpeechDetected

    var errorDescription: String? {
        switch self {
        case .emptyResponse:
            "返答を生成できませんでした。もう一度お試しください。"
        case let .modelUnavailable(reason):
            reason
        case let .speechUnavailable(reason):
            reason
        case let .permissionDenied(reason):
            reason
        case .noSpeechDetected:
            "音声を認識できませんでした。もう一度話すか、文字で入力してください。"
        }
    }
}
