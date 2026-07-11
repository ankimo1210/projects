import SwiftData
import SwiftUI

struct QuestionDetailView: View {
    @Environment(\.modelContext) private var modelContext
    let question: StudyQuestion
    @State private var showAnswer = false
    @State private var isBookmarked = false

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                VStack(alignment: .leading, spacing: 22) {
                HStack {
                    MetadataPill(text: question.learningOutcomeLabel)
                    MetadataPill(text: question.modeLabel)
                    Spacer()
                    Button {
                        toggleBookmark()
                    } label: {
                        Image(systemName: isBookmarked ? "bookmark.fill" : "bookmark")
                            .font(.title3)
                    }
                    .accessibilityLabel(isBookmarked ? "ブックマークを解除" : "ブックマークに追加")
                }

                Text(question.displayPrompt)
                    .font(.title2.bold())
                    .textSelection(.enabled)

                if !question.displayChoices.isEmpty {
                    VStack(spacing: 10) {
                        ForEach(Array(question.displayChoices.enumerated()), id: \.offset) { index, choice in
                            HStack(alignment: .top) {
                                Text(String(UnicodeScalar(65 + index)!))
                                    .font(.caption.bold())
                                    .frame(width: 24, height: 24)
                                    .background(AppTheme.wineSoft, in: Circle())
                                Text(choice)
                                Spacer()
                                if showAnswer && index == question.correctAnswerIndex {
                                    Image(systemName: "checkmark.circle.fill")
                                        .foregroundStyle(.green)
                                }
                            }
                            .padding()
                            .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 12))
                        }
                    }
                }

                if showAnswer {
                    VStack(alignment: .leading, spacing: 10) {
                        Text("Answer")
                            .font(.headline)
                        Text(question.displayAnswer)
                            .textSelection(.enabled)
                        if let explanation = question.displayExplanation, !explanation.isEmpty {
                            Divider()
                            Text("Explanation")
                                .font(.headline)
                            Text(explanation)
                                .textSelection(.enabled)
                        }
                        if !question.choiceExplanations.isEmpty {
                            Divider()
                            ChoiceExplanationsView(question: question)
                        }
                    }
                    .padding()
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(AppTheme.wineSoft, in: RoundedRectangle(cornerRadius: 16))
                    .id("question-answer")
                } else {
                    Button("Reveal answer") {
                        withAnimation { showAnswer = true }
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(AppTheme.wine)
                }

                VStack(alignment: .leading, spacing: 8) {
                    Text("問題情報")
                        .font(.headline)
                    LabeledContent("トピック", value: question.topic)
                    if let name = question.learningOutcomeName, !name.isEmpty {
                        LabeledContent("学習成果", value: name)
                    }
                    if let subcategory = question.subcategory, !subcategory.isEmpty {
                        LabeledContent("小分類", value: subcategory)
                    }
                    if let wineType = question.wineType, !wineType.isEmpty {
                        LabeledContent("ワイン区分", value: wineType)
                    }
                    if let difficulty = question.difficulty, !difficulty.isEmpty {
                        LabeledContent("難易度", value: difficulty)
                    }
                    if let skill = question.cognitiveSkill, !skill.isEmpty {
                        LabeledContent("思考スキル", value: skill)
                    }
                    if !question.geography.isEmpty {
                        LabeledContent("国・産地", value: question.geography.joined(separator: "・"))
                    }
                    if !question.grapeVarieties.isEmpty {
                        LabeledContent("主要品種", value: question.grapeVarieties.joined(separator: "・"))
                    }
                }
                .font(.subheadline)
            }
                .padding()
            }
            .onChange(of: showAnswer) { _, revealed in
                guard revealed else { return }
                DispatchQueue.main.async {
                    withAnimation {
                        proxy.scrollTo("question-answer", anchor: .center)
                    }
                }
            }
        }
        .navigationTitle("問題")
        .navigationBarTitleDisplayMode(.inline)
        .onAppear { loadBookmark() }
    }

    private func progressRecord() -> QuestionProgress? {
        let questionID = question.id
        let descriptor = FetchDescriptor<QuestionProgress>(
            predicate: #Predicate { $0.questionID == questionID }
        )
        return try? modelContext.fetch(descriptor).first
    }

    private func loadBookmark() {
        isBookmarked = progressRecord()?.isBookmarked ?? false
    }

    private func toggleBookmark() {
        let record: QuestionProgress
        if let existing = progressRecord() {
            record = existing
        } else {
            record = QuestionProgress(questionID: question.id)
            modelContext.insert(record)
        }
        record.isBookmarked.toggle()
        isBookmarked = record.isBookmarked
        try? modelContext.save()
    }
}
