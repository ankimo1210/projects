import SwiftData
import SwiftUI

struct StudySessionView: View {
    @Environment(\.modelContext) private var modelContext
    @Environment(EntitlementStore.self) private var entitlementStore
    let questions: [StudyQuestion]
    @State private var currentIndex = 0
    @State private var isRevealed = false
    @State private var selectedChoice: Int?
    @State private var correctCount = 0
    @State private var isFinished = false
    @State private var writtenResponse = ""
    @State private var selectedRubricIDs: Set<String> = []
    @State private var questionStartedAt = Date.now
    @State private var answerSubmittedAt: Date?

    private var question: StudyQuestion { questions[currentIndex] }

    private var inaccessibleQuestion: StudyQuestion? {
        questions.first {
            !entitlementStore.policy.canAccessQuestion(id: $0.id, studyMode: $0.studyMode)
        }
    }

    var body: some View {
        Group {
            if questions.isEmpty {
                ContentUnavailableView(
                    "学習する問題がありません",
                    systemImage: "questionmark.folder",
                    description: Text("条件を変更して、もう一度お試しください。")
                )
            } else if let inaccessibleQuestion {
                PaywallView(
                    triggerFeature: inaccessibleQuestion.studyMode == "written_answer"
                        ? .fullWrittenPractice
                        : .fullQuestionBank
                )
            } else if isFinished {
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
        .onAppear {
            guard !questions.isEmpty, inaccessibleQuestion == nil else { return }
            prepareCurrentQuestion()
        }
    }

    private var questionView: some View {
        ScrollViewReader { proxy in
            ScrollView {
                VStack(alignment: .leading, spacing: 22) {
                    ProgressView(value: Double(currentIndex), total: Double(questions.count))
                        .tint(AppTheme.wine)

                    ScrollView(.horizontal) {
                        HStack {
                            MetadataPill(text: question.learningOutcomeLabel)
                            MetadataPill(text: question.modeLabel)
                            if question.studyMode == "written_answer" {
                                if let commandVerb = question.commandVerb, !commandVerb.isEmpty {
                                    MetadataPill(text: "指示語：\(commandVerb)")
                                        .accessibilityIdentifier("written.answer.commandVerb")
                                }
                                MetadataPill(text: "配点：\(maximumRubricMarks)点")
                                    .accessibilityIdentifier("written.answer.maximumMarks")
                            }
                            if let minutes = question.suggestedMinutes {
                                MetadataPill(text: "目安 \(minutes)分")
                            }
                        }
                    }
                    .scrollIndicators(.hidden)

                    Text(question.displayPrompt)
                        .font(.title2.bold())
                        .frame(maxWidth: .infinity, alignment: .leading)

                    if question.studyMode == "multiple_choice" {
                        choiceButtons
                    } else if question.studyMode == "written_answer" && !isRevealed {
                        writtenAnswerEditor
                    } else if !isRevealed {
                        Button("解答を見る") {
                            revealAnswer()
                        }
                        .buttonStyle(.borderedProminent)
                        .tint(AppTheme.wine)
                        .frame(maxWidth: .infinity)
                    }

                    if isRevealed {
                        answerCard
                            .id("answer-card")
                        TermAnnotationsView(questionID: question.id)
                        if question.studyMode == "written_answer", !question.rubricItems.isEmpty {
                            writtenRubricScoring
                        } else {
                            ratingButtons
                        }
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
            HStack {
                Text("あなたの解答")
                    .font(.headline)
                Spacer()
                TimelineView(.periodic(from: questionStartedAt, by: 1)) { context in
                    let elapsedSeconds = WrittenPracticeTiming.elapsedSeconds(
                        startedAt: questionStartedAt,
                        submittedAt: answerSubmittedAt,
                        now: context.date
                    )
                    Label(
                        "経過 \(WrittenPracticeTiming.durationText(elapsedSeconds))",
                        systemImage: "stopwatch"
                    )
                    .font(.subheadline.monospacedDigit())
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("written.answer.elapsedTime")
                }
            }
            TextEditor(text: writtenResponseBinding)
                .frame(minHeight: 180)
                .padding(8)
                .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 12))
                .accessibilityIdentifier("written.answer.editor")
            if hasWrittenHistory {
                NavigationLink {
                    WrittenAnswerHistoryView(question: question)
                } label: {
                    Label("この問題の過去回答と得点推移", systemImage: "chart.xyaxis.line")
                }
                .accessibilityIdentifier("written.history.open")
            }
            Button(question.hasAnswer ? "模範解答と比較" : "回答を完了") {
                revealAnswer()
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
                    revealAnswer()
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
                .accessibilityIdentifier("study.session.choice.\(index)")
            }
        }
    }

    private var answerCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("解答")
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
            Button("もう一度") { recordAndAdvance(rating: 0) }
                .buttonStyle(.bordered)
                .tint(.red)
                .frame(maxWidth: .infinity)
            Button("理解できた") { recordAndAdvance(rating: 3) }
                .buttonStyle(.borderedProminent)
                .tint(AppTheme.wine)
                .frame(maxWidth: .infinity)
        }
    }

    private var writtenRubricScoring: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("自己採点")
                    .font(.headline)
                Spacer()
                Text("\(awardedRubricMarks) / \(maximumRubricMarks) 点")
                    .font(.headline.monospacedDigit())
                    .foregroundStyle(AppTheme.wine)
            }
            Text("自分の解答に含められた要点を選択してください。")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            ForEach(question.rubricItems) { item in
                Button {
                    if selectedRubricIDs.contains(item.id) {
                        selectedRubricIDs.remove(item.id)
                    } else {
                        selectedRubricIDs.insert(item.id)
                    }
                    persistWrittenDraft(for: question.id)
                } label: {
                    HStack(alignment: .top, spacing: 12) {
                        Image(systemName: selectedRubricIDs.contains(item.id)
                              ? "checkmark.square.fill"
                              : "square")
                            .foregroundStyle(AppTheme.wine)
                        Text(item.criterion)
                            .multilineTextAlignment(.leading)
                        Spacer(minLength: 8)
                        Text("\(item.marks)点")
                            .font(.subheadline.bold())
                    }
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .accessibilityIdentifier("written.rubric.\(item.id)")
                if item.id != question.rubricItems.last?.id {
                    Divider()
                }
            }

            let relatedTermIDs = WrittenPracticeInsights.relatedTermIDs(
                for: question,
                selectedRubricIDs: selectedRubricIDs
            )
            if !relatedTermIDs.isEmpty {
                WrittenRubricReviewLinks(termIDs: relatedTermIDs)
                    .accessibilityIdentifier("written.rubric.reviewLinks")
            }

            Button("自己採点を記録して次へ") {
                recordWrittenAndAdvance()
            }
            .buttonStyle(.borderedProminent)
            .tint(AppTheme.wine)
            .frame(maxWidth: .infinity)
        }
        .padding()
        .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 16))
    }

    private var completionView: some View {
        ContentUnavailableView {
            Label("学習完了", systemImage: "checkmark.seal.fill")
        } description: {
            Text("\(questions.count)問中\(correctCount)問を正解として記録しました")
        } actions: {
            if !entitlementStore.hasProAccess, questions.count >= 20 {
                NavigationLink {
                    PaywallView()
                } label: {
                    Label("Pro機能を見る", systemImage: "graduationcap.fill")
                }
                .buttonStyle(.borderedProminent)
                .tint(AppTheme.wine)
                .accessibilityIdentifier("paywall.afterStudy")
            }
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
                responseText: writtenResponse.isEmpty ? nil : writtenResponse,
                durationSeconds: responseDurationSeconds
            )
        )
        deleteWrittenDraft(for: question.id)
        finishCurrentQuestion()
    }

    private func recordWrittenAndAdvance() {
        let maximumMarks = maximumRubricMarks
        let awardedMarks = awardedRubricMarks
        let ratio = maximumMarks > 0 ? Double(awardedMarks) / Double(maximumMarks) : 0
        let isCorrect = ratio >= 0.6
        let rating = isCorrect ? 3 : 0
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
                responseText: writtenResponse,
                awardedMarks: awardedMarks,
                maximumMarks: maximumMarks,
                rubricSelections: Array(selectedRubricIDs).sorted(),
                durationSeconds: responseDurationSeconds
            )
        )
        deleteWrittenDraft(for: question.id)
        finishCurrentQuestion()
    }

    private func finishCurrentQuestion() {
        try? modelContext.save()
        Task { await ReviewNotificationService.refreshIfEnabled(in: modelContext) }

        if currentIndex + 1 == questions.count {
            isFinished = true
        } else {
            currentIndex += 1
            selectedChoice = nil
            prepareCurrentQuestion()
        }
    }

    private func revealAnswer() {
        answerSubmittedAt = answerSubmittedAt ?? .now
        if question.studyMode == "written_answer" {
            persistWrittenDraft(for: question.id)
        }
        withAnimation { isRevealed = true }
    }

    private var writtenResponseBinding: Binding<String> {
        Binding(
            get: { writtenResponse },
            set: { newValue in
                writtenResponse = newValue
                persistWrittenDraft(for: question.id)
            }
        )
    }

    private var hasWrittenHistory: Bool {
        let questionID = question.id
        let descriptor = FetchDescriptor<StudyAttempt>(
            predicate: #Predicate {
                $0.questionID == questionID && $0.awardedMarks != nil
            }
        )
        return ((try? modelContext.fetchCount(descriptor)) ?? 0) > 0
    }

    private func prepareCurrentQuestion() {
        isRevealed = false
        writtenResponse = ""
        selectedRubricIDs = []
        questionStartedAt = .now
        answerSubmittedAt = nil

        guard question.studyMode == "written_answer",
              let draft = writtenDraft(for: question.id)
        else { return }
        writtenResponse = draft.responseText
        selectedRubricIDs = Set(draft.rubricSelections)
        questionStartedAt = draft.startedAt
        answerSubmittedAt = draft.submittedAt
        isRevealed = draft.submittedAt != nil
    }

    private func persistWrittenDraft(for questionID: String) {
        guard question.studyMode == "written_answer", question.id == questionID else { return }
        let trimmedResponse = writtenResponse.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmedResponse.isEmpty, selectedRubricIDs.isEmpty, answerSubmittedAt == nil {
            deleteWrittenDraft(for: questionID)
            try? modelContext.save()
            return
        }

        let existing = writtenDraft(for: questionID)
        let draft = existing ?? WrittenAnswerDraft(
            questionID: questionID,
            startedAt: questionStartedAt
        )
        if existing == nil { modelContext.insert(draft) }
        draft.update(
            responseText: writtenResponse,
            rubricSelections: Array(selectedRubricIDs).sorted(),
            submittedAt: answerSubmittedAt
        )
        try? modelContext.save()
    }

    private func writtenDraft(for questionID: String) -> WrittenAnswerDraft? {
        let descriptor = FetchDescriptor<WrittenAnswerDraft>(
            predicate: #Predicate { $0.questionID == questionID }
        )
        return try? modelContext.fetch(descriptor).first
    }

    private func deleteWrittenDraft(for questionID: String) {
        guard let draft = writtenDraft(for: questionID) else { return }
        modelContext.delete(draft)
    }

    private var maximumRubricMarks: Int {
        let rubricTotal = question.rubricItems.reduce(0) { $0 + $1.marks }
        if rubricTotal > 0 { return rubricTotal }
        return Int(question.markAllocation ?? 0)
    }

    private var awardedRubricMarks: Int {
        question.rubricItems
            .filter { selectedRubricIDs.contains($0.id) }
            .reduce(0) { $0 + $1.marks }
    }

    private var responseDurationSeconds: Int {
        WrittenPracticeTiming.elapsedSeconds(
            startedAt: questionStartedAt,
            submittedAt: answerSubmittedAt,
            now: .now
        )
    }

    private func progressRecord(for questionID: String) -> QuestionProgress? {
        let descriptor = FetchDescriptor<QuestionProgress>(
            predicate: #Predicate { $0.questionID == questionID }
        )
        return try? modelContext.fetch(descriptor).first
    }
}
