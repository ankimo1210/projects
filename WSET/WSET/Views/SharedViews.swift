import SwiftUI

struct StatCard: View {
    let title: String
    let value: String
    let systemImage: String

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label {
                Text(LocalizedStringKey(title))
            } icon: {
                Image(systemName: systemImage)
            }
                .font(.caption)
                .foregroundStyle(.secondary)
            Text(value)
                .font(.title.bold())
                .foregroundStyle(AppTheme.wine)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(.background, in: RoundedRectangle(cornerRadius: 16))
        .shadow(color: .black.opacity(0.06), radius: 8, y: 3)
    }
}

struct MetadataPill: View {
    let text: String

    var body: some View {
        Text(LocalizedStringKey(text))
            .font(.caption.weight(.medium))
            .padding(.horizontal, 9)
            .padding(.vertical, 5)
            .background(AppTheme.wineSoft, in: Capsule())
            .foregroundStyle(AppTheme.wine)
    }
}

struct QuestionRow: View {
    let question: StudyQuestion

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(question.displayPrompt)
                .font(.body.weight(.medium))
                .lineLimit(3)
            HStack {
                MetadataPill(text: question.learningOutcomeLabel)
                MetadataPill(text: question.modeLabel)
            }
        }
        .padding(.vertical, 4)
    }
}

struct ChoiceExplanationsView: View {
    let question: StudyQuestion
    var selectedChoice: Int? = nil

    var body: some View {
        if !question.choiceExplanations.isEmpty {
            VStack(alignment: .leading, spacing: 10) {
                Text("選択肢ごとの解説")
                    .font(.headline)

                ForEach(Array(question.choiceExplanations.enumerated()), id: \.offset) {
                    index, explanation in
                    if !explanation.isEmpty {
                        HStack(alignment: .top, spacing: 10) {
                            Text(String(UnicodeScalar(65 + index)!))
                                .font(.caption.bold())
                                .frame(width: 24, height: 24)
                                .background(choiceColour(index).opacity(0.16), in: Circle())
                            Text(explanation)
                                .foregroundStyle(.secondary)
                                .frame(maxWidth: .infinity, alignment: .leading)
                        }
                    }
                }
            }
        }
    }

    private func choiceColour(_ index: Int) -> Color {
        if index == question.correctAnswerIndex { return .green }
        if index == selectedChoice { return .red }
        return AppTheme.wine
    }
}
