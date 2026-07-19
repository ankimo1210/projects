import Foundation

nonisolated enum ConversationPromptBuilder {
    static func instructions(for configuration: ConversationConfiguration) -> String {
        """
        You are a patient Mandarin conversation partner for a native Japanese learner.
        Role-play as: \(configuration.scenario.partnerRole).
        Scenario: \(configuration.scenario.title) — \(configuration.scenario.subtitle).
        Target level: \(levelGuidance(configuration.level)).

        Rules:
        - Continue the role-play naturally in Simplified Chinese.
        - Use one or two short sentences and ask at most one question per turn.
        - Never leave the selected scenario.
        - Do not lecture or grade during the conversation.
        - If the learner makes a mistake, infer the meaning and continue naturally.
        - Supply accurate tone-marked Hanyu Pinyin and a concise Japanese translation.
        - Suggestions must be short replies the learner can say next.
        """
    }

    static func replyPrompt(
        learnerText: String,
        openingText: String,
        isFirstTurn: Bool
    ) -> String {
        let context = isFirstTurn
            ? "The partner opened with: \(openingText)\n"
            : ""
        return """
        \(context)The learner said: \(learnerText)
        Continue the role-play. Keep the Chinese response brief and level-appropriate.
        """
    }

    static func feedbackPrompt(
        configuration: ConversationConfiguration,
        messages: [ConversationMessage]
    ) -> String {
        let transcript = messages.map { message in
            let speaker = message.role == .learner ? "Learner" : "Partner"
            return "\(speaker): \(message.chinese)"
        }.joined(separator: "\n")

        return """
        Review this \(configuration.scenario.title) Mandarin role-play for a Japanese learner at \(configuration.level.displayName).
        Give one encouraging Japanese note. Return only important, concrete corrections, with at most three.
        If an utterance is already natural, do not invent a correction.
        Select at most five useful Chinese words from the actual dialogue for spaced repetition.

        Dialogue:
        \(transcript)
        """
    }

    static func levelGuidance(_ level: HSKLevel) -> String {
        switch level {
        case .level1:
            "HSK 1. Use very common words, basic word order, and sentences under about 12 Chinese characters."
        case .level2:
            "HSK 2. Use common daily vocabulary and short compound sentences."
        case .level3:
            "HSK 3. Use everyday explanations and simple reasons, while keeping turns concise."
        case .level4:
            "HSK 4. Use natural daily Mandarin, comparisons, reasons, and follow-up questions."
        case .level5:
            "HSK 5. Use moderately nuanced vocabulary and natural conversational connectors."
        case .level6:
            "HSK 6. Use fluent, idiomatic discussion while avoiding unnecessarily rare words."
        case .advanced:
            "HSK 7–9. Use sophisticated, idiomatic Mandarin and invite nuanced opinions."
        }
    }
}
