import SwiftData
import SwiftUI

struct MockExamView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var modelContext
    @Environment(EntitlementStore.self) private var entitlementStore
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
    private var inaccessibleQuestion: StudyQuestion? {
        questions.first {
            !entitlementStore.policy.canAccessQuestion(id: $0.id, studyMode: $0.studyMode)
        }
    }

    var body: some View {
        if questions.isEmpty {
            ContentUnavailableView(
                "模擬試験の問題がありません",
                systemImage: "questionmark.folder",
                description: Text("問題データを確認してください。")
            )
        } else if let inaccessibleQuestion {
            PaywallView(
                triggerFeature: inaccessibleQuestion.studyMode == "written_answer"
                    ? .fullWrittenPractice
                    : .fullQuestionBank
            )
        } else {
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
                        Button("提出") { showingSubmitConfirmation = true }
                    }
                }
            }
            .alert("模擬試験を提出しますか？", isPresented: $showingSubmitConfirmation) {
                Button("キャンセル", role: .cancel) {}
                Button("提出") { submit() }
            } message: {
                Text("未回答が\(questions.count - answers.count)問あります。提出後は回答を変更できません。")
            }
        }
    }

    private var examView: some View {
        VStack(spacing: 0) {
            ScrollView {
                VStack(alignment: .leading, spacing: 22) {
                    HStack {
                        Text("問題 \(currentIndex + 1) / \(questions.count)")
                            .font(.headline)
                        Spacer()
                        Text("\(answers.count)問回答済み")
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
                Button("前へ") {
                    currentIndex = max(0, currentIndex - 1)
                }
                .disabled(currentIndex == 0)

                Spacer()

                if currentIndex + 1 == questions.count {
                    Button("提出") { showingSubmitConfirmation = true }
                        .buttonStyle(.borderedProminent)
                        .tint(AppTheme.wine)
                } else {
                    Button("次へ") {
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
                    Text("練習スコア")
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
                    Text("学習成果別")
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
                        Text("間違えた問題を確認")
                            .font(.headline)
                        ForEach(incorrectQuestions) { missed in
                            VStack(alignment: .leading, spacing: 8) {
                                Text(missed.displayPrompt)
                                    .font(.body.weight(.medium))
                                Text("正解：\(missed.displayAnswer)")
                                    .foregroundStyle(AppTheme.success)
                                if answers[missed.id] == nil {
                                    Text("未回答")
                                        .foregroundStyle(AppTheme.warning)
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

                Button("完了") { dismiss() }
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
