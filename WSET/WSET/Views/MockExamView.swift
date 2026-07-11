import SwiftData
import SwiftUI

struct MockExamView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var modelContext
    let questions: [StudyQuestion]
    @State private var currentIndex = 0
    @State private var answers: [String: Int] = [:]
    @State private var isSubmitted = false
    @State private var showingSubmitConfirmation = false

    private var question: StudyQuestion { questions[currentIndex] }
    private var correctQuestions: [StudyQuestion] {
        questions.filter { answers[$0.id] == $0.correctAnswerIndex }
    }
    private var incorrectQuestions: [StudyQuestion] {
        questions.filter { answers[$0.id] != $0.correctAnswerIndex }
    }

    var body: some View {
        Group {
            if isSubmitted {
                resultsView
            } else {
                examView
            }
        }
        .navigationTitle(
            isSubmitted ? "模擬試験結果" : "模擬試験"
        )
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            if !isSubmitted {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Submit") { showingSubmitConfirmation = true }
                }
            }
        }
        .alert("Submit mock exam?", isPresented: $showingSubmitConfirmation) {
            Button("Cancel", role: .cancel) {}
            Button("Submit") { submit() }
        } message: {
            Text("\(questions.count - answers.count) questions are unanswered. Answers cannot be changed after submission.")
        }
    }

    private var examView: some View {
        VStack(spacing: 0) {
            ScrollView {
                VStack(alignment: .leading, spacing: 22) {
                    HStack {
                        Text("Question \(currentIndex + 1) of \(questions.count)")
                            .font(.headline)
                        Spacer()
                        Text("\(answers.count) answered")
                            .foregroundStyle(.secondary)
                    }

                    ProgressView(value: Double(currentIndex + 1), total: Double(questions.count))
                        .tint(AppTheme.wine)

                    MetadataPill(text: question.learningOutcomeLabel)

                    Text(question.displayPrompt)
                        .font(.title2.bold())
                        .frame(maxWidth: .infinity, alignment: .leading)

                    VStack(spacing: 10) {
                        ForEach(Array(question.displayChoices.enumerated()), id: \.offset) { index, choice in
                            Button {
                                answers[question.id] = index
                            } label: {
                                HStack(alignment: .top) {
                                    Text(String(UnicodeScalar(65 + index)!))
                                        .font(.caption.bold())
                                        .frame(width: 25, height: 25)
                                        .background(.white.opacity(0.8), in: Circle())
                                    Text(choice)
                                        .multilineTextAlignment(.leading)
                                    Spacer()
                                    if answers[question.id] == index {
                                        Image(systemName: "checkmark.circle.fill")
                                    }
                                }
                                .padding()
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .background(
                                    answers[question.id] == index
                                        ? AppTheme.wineSoft
                                        : Color(.secondarySystemGroupedBackground),
                                    in: RoundedRectangle(cornerRadius: 14)
                                )
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
                .padding()
            }

            Divider()
            HStack {
                Button("Previous") {
                    currentIndex = max(0, currentIndex - 1)
                }
                .disabled(currentIndex == 0)

                Spacer()

                if currentIndex + 1 == questions.count {
                    Button("Submit") { showingSubmitConfirmation = true }
                        .buttonStyle(.borderedProminent)
                        .tint(AppTheme.wine)
                } else {
                    Button("Next") {
                        currentIndex += 1
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(AppTheme.wine)
                }
            }
            .padding()
            .background(.bar)
        }
    }

    private var resultsView: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                VStack(spacing: 8) {
                    Text("\(correctQuestions.count) / \(questions.count)")
                        .font(.system(size: 48, weight: .bold, design: .rounded))
                        .foregroundStyle(AppTheme.wine)
                    Text("Practice score")
                        .foregroundStyle(.secondary)
                    ProgressView(
                        value: Double(correctQuestions.count),
                        total: Double(questions.count)
                    )
                    .tint(AppTheme.wine)
                }
                .frame(maxWidth: .infinity)
                .padding()
                .background(AppTheme.wineSoft, in: RoundedRectangle(cornerRadius: 18))

                VStack(alignment: .leading, spacing: 14) {
                    Text("By learning outcome")
                        .font(.headline)
                    ForEach(LearningOutcome.allCases.filter { $0 != .all }) { outcome in
                        let outcomeQuestions = questions.filter {
                            $0.learningOutcome == outcome.rawValue
                        }
                        if !outcomeQuestions.isEmpty {
                            let correct = outcomeQuestions.count {
                                answers[$0.id] == $0.correctAnswerIndex
                            }
                            HStack {
                                Text(outcome.shortLabel)
                                Spacer()
                                Text("\(correct)/\(outcomeQuestions.count)")
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                }

                if !incorrectQuestions.isEmpty {
                    VStack(alignment: .leading, spacing: 14) {
                        Text("Review missed questions")
                            .font(.headline)
                        ForEach(incorrectQuestions) { missed in
                            VStack(alignment: .leading, spacing: 8) {
                                Text(missed.displayPrompt)
                                    .font(.body.weight(.medium))
                                Text("Correct: \(missed.displayAnswer)")
                                    .foregroundStyle(.green)
                                if answers[missed.id] == nil {
                                    Text("Unanswered")
                                        .foregroundStyle(.orange)
                                }
                                ChoiceExplanationsView(
                                    question: missed,
                                    selectedChoice: answers[missed.id]
                                )
                            }
                            .padding()
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 14))
                        }
                    }
                }

                Button("Done") { dismiss() }
                    .buttonStyle(.borderedProminent)
                    .tint(AppTheme.wine)
                    .frame(maxWidth: .infinity)
            }
            .padding()
        }
    }

    private func submit() {
        guard !isSubmitted else { return }
        for question in questions {
            let isCorrect = answers[question.id] == question.correctAnswerIndex
            let existingProgress = progressRecord(for: question.id)
            let progress = existingProgress ?? QuestionProgress(questionID: question.id)
            if existingProgress == nil {
                modelContext.insert(progress)
            }
            progress.record(isCorrect: isCorrect, rating: isCorrect ? 3 : 0)
            modelContext.insert(
                StudyAttempt(questionID: question.id, isCorrect: isCorrect, rating: isCorrect ? 3 : 0)
            )
        }
        var outcomeResults: [String: MockOutcomeResult] = [:]
        for outcome in LearningOutcome.allCases where outcome != .all {
            let outcomeQuestions = questions.filter { $0.learningOutcome == outcome.rawValue }
            guard !outcomeQuestions.isEmpty else { continue }
            outcomeResults[outcome.rawValue] = MockOutcomeResult(
                correct: outcomeQuestions.count {
                    answers[$0.id] == $0.correctAnswerIndex
                },
                total: outcomeQuestions.count
            )
        }
        modelContext.insert(
            MockExamSession(
                correctCount: correctQuestions.count,
                questionCount: questions.count,
                outcomeResults: outcomeResults,
                missedQuestionIDs: incorrectQuestions.map(\.id)
            )
        )
        try? modelContext.save()
        Task { await ReviewNotificationService.refreshIfEnabled(in: modelContext) }
        isSubmitted = true
    }

    private func progressRecord(for questionID: String) -> QuestionProgress? {
        let descriptor = FetchDescriptor<QuestionProgress>(
            predicate: #Predicate { $0.questionID == questionID }
        )
        return try? modelContext.fetch(descriptor).first
    }
}
