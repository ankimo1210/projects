import SwiftUI

struct PracticeQuestionListView: View {
    let title: String
    let questions: [PracticeQuestion]

    var body: some View {
        List(questions) { question in
            NavigationLink {
                destination(for: question)
            } label: {
                VStack(alignment: .leading, spacing: 4) {
                    Text(displayName(question.kind)).font(.headline)
                    Text(questionPrompt(question))
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                    Text("HSK \(question.metadata.level.rawValue)")
                        .font(.caption)
                        .foregroundStyle(.purple)
                }
            }
        }
        .navigationTitle(title)
    }

    @ViewBuilder
    private func destination(for question: PracticeQuestion) -> some View {
        switch question.content {
        case .sentenceOrdering:
            OrderingPracticeView(questions: [question])
        case .vocabularyMultipleChoice, .audioToMeaning, .sentenceCloze,
             .readingComprehension, .incorrectSentence:
            ChoicePracticeView(title: displayName(question.kind), questions: [question])
        case .summary, .essay, .translation, .oralOpinion:
            FreeResponsePracticeView(title: displayName(question.kind), questions: [question])
        }
    }

    private func questionPrompt(_ question: PracticeQuestion) -> String {
        switch question.content {
        case let .vocabularyMultipleChoice(value): value.prompt.instruction
        case let .audioToMeaning(value): value.prompt.instruction
        case let .sentenceCloze(value): value.prompt.instruction
        case let .sentenceOrdering(value): value.prompt.instruction
        case let .readingComprehension(value): value.prompt.instruction
        case let .incorrectSentence(value): value.prompt.instruction
        case let .summary(value), let .essay(value), let .oralOpinion(value): value.prompt.instruction
        case let .translation(value): value.response.prompt.instruction
        }
    }

    private func displayName(_ kind: PracticeQuestionKind) -> String {
        switch kind {
        case .vocabularyMultipleChoice: "単語選択"
        case .audioToMeaning: "聞き取り"
        case .sentenceCloze: "穴埋め"
        case .sentenceOrdering: "語順整序"
        case .readingComprehension: "読解"
        case .incorrectSentence: "誤文訂正"
        case .summary: "要約"
        case .essay: "作文"
        case .translation: "翻訳"
        case .oralOpinion: "口頭意見"
        }
    }
}
