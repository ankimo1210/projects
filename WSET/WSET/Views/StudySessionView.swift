import SwiftData
import SwiftUI

struct StudySessionView: View {
    @Environment(\.modelContext) private var modelContext
    let questions: [StudyQuestion]
    @State private var currentIndex = 0
    @State private var isRevealed = false
    @State private var selectedChoice: Int?
    @State private var correctCount = 0
    @State private var isFinished = false
    @State private var writtenResponse = ""

    private var question: StudyQuestion { questions[currentIndex] }

    var body: some View {
        Group {
            if isFinished {
                completionView
            } else {
                questionView
            }
        }
        .navigationTitle(
            isFinished ? "完了" : "\(currentIndex + 1) / \(questions.count) 問"
        )
        .navigationBarTitleDisplayMode(.inline)
        .interactiveDismissDisabled(!isFinished && currentIndex > 0)
    }

    private var questionView: some View {
        ScrollViewReader { proxy in
            ScrollView {
                VStack(alignment: .leading, spacing: 22) {
                    ProgressView(value: Double(currentIndex), total: Double(questions.count))
                        .tint(AppTheme.wine)

                    HStack {
                        MetadataPill(text: question.learningOutcomeLabel)
                        MetadataPill(text: question.modeLabel)
                    }

                    Text(question.displayPrompt)
                        .font(.title2.bold())
                        .frame(maxWidth: .infinity, alignment: .leading)

                    if question.studyMode == "multiple_choice" {
                        choiceButtons
                    } else if question.studyMode == "written_answer" && !isRevealed {
                        writtenAnswerEditor
                    } else if !isRevealed {
                        Button("Reveal answer") {
                            withAnimation { isRevealed = true }
                        }
                        .buttonStyle(.borderedProminent)
                        .tint(AppTheme.wine)
                        .frame(maxWidth: .infinity)
                    }

                    if isRevealed {
                        answerCard
                            .id("answer-card")
                        ratingButtons
                    }
                }
                .padding()
            }
            .onChange(of: isRevealed) { _, revealed in
                guard revealed else { return }
                DispatchQueue.main.async {
                    withAnimation {
                        proxy.scrollTo("answer-card", anchor: .center)
                    }
                }
            }
        }
    }

    private var writtenAnswerEditor: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Your answer")
                .font(.headline)
            TextEditor(text: $writtenResponse)
                .frame(minHeight: 180)
                .padding(8)
                .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 12))
            Button(question.hasAnswer ? "模範解答と比較" : "回答を完了") {
                withAnimation { isRevealed = true }
            }
            .buttonStyle(.borderedProminent)
            .tint(AppTheme.wine)
            .disabled(writtenResponse.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
        }
    }

    private var choiceButtons: some View {
        VStack(spacing: 10) {
            ForEach(Array(question.displayChoices.enumerated()), id: \.offset) { index, choice in
                Button {
                    guard selectedChoice == nil else { return }
                    selectedChoice = index
                    isRevealed = true
                } label: {
                    HStack(alignment: .top) {
                        Text(String(UnicodeScalar(65 + index)!))
                            .font(.caption.bold())
                            .frame(width: 25, height: 25)
                            .background(.white.opacity(0.8), in: Circle())
                        Text(choice)
                            .multilineTextAlignment(.leading)
                        Spacer()
                        if isRevealed && index == question.correctAnswerIndex {
                            Image(systemName: "checkmark.circle.fill")
                                .foregroundStyle(.green)
                        } else if isRevealed && index == selectedChoice {
                            Image(systemName: "xmark.circle.fill")
                                .foregroundStyle(.red)
                        }
                    }
                    .padding()
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(choiceBackground(index), in: RoundedRectangle(cornerRadius: 14))
                }
                .buttonStyle(.plain)
            }
        }
    }

    private var answerCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Answer")
                .font(.headline)
            Text(question.displayAnswer)
            if let explanation = question.displayExplanation, !explanation.isEmpty {
                Divider()
                Text(explanation)
                    .foregroundStyle(.secondary)
            }
            if !question.choiceExplanations.isEmpty {
                Divider()
                ChoiceExplanationsView(question: question, selectedChoice: selectedChoice)
            }
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(AppTheme.wineSoft, in: RoundedRectangle(cornerRadius: 16))
    }

    private var ratingButtons: some View {
        HStack(spacing: 12) {
            Button("Again") { recordAndAdvance(rating: 0) }
                .buttonStyle(.bordered)
                .tint(.red)
                .frame(maxWidth: .infinity)
            Button("Good") { recordAndAdvance(rating: 3) }
                .buttonStyle(.borderedProminent)
                .tint(AppTheme.wine)
                .frame(maxWidth: .infinity)
        }
    }

    private var completionView: some View {
        ContentUnavailableView {
            Label("Session complete", systemImage: "checkmark.seal.fill")
        } description: {
            Text("\(correctCount) of \(questions.count) marked correct")
        }
    }

    private func choiceBackground(_ index: Int) -> Color {
        guard isRevealed else { return Color(.secondarySystemGroupedBackground) }
        if index == question.correctAnswerIndex { return .green.opacity(0.15) }
        if index == selectedChoice { return .red.opacity(0.12) }
        return Color(.secondarySystemGroupedBackground)
    }

    private func recordAndAdvance(rating: Int) {
        let isCorrect: Bool
        if question.studyMode == "multiple_choice" {
            isCorrect = selectedChoice == question.correctAnswerIndex
        } else {
            isCorrect = rating > 0
        }
        correctCount += isCorrect ? 1 : 0
        let existingProgress = progressRecord(for: question.id)
        let progress = existingProgress ?? QuestionProgress(questionID: question.id)
        if existingProgress == nil {
            modelContext.insert(progress)
        }
        progress.record(isCorrect: isCorrect, rating: rating)
        modelContext.insert(
            StudyAttempt(
                questionID: question.id,
                isCorrect: isCorrect,
                rating: rating,
                responseText: writtenResponse.isEmpty ? nil : writtenResponse
            )
        )
        try? modelContext.save()
        Task { await ReviewNotificationService.refreshIfEnabled(in: modelContext) }

        if currentIndex + 1 == questions.count {
            isFinished = true
        } else {
            currentIndex += 1
            selectedChoice = nil
            isRevealed = false
            writtenResponse = ""
        }
    }

    private func progressRecord(for questionID: String) -> QuestionProgress? {
        let descriptor = FetchDescriptor<QuestionProgress>(
            predicate: #Predicate { $0.questionID == questionID }
        )
        return try? modelContext.fetch(descriptor).first
    }
}
