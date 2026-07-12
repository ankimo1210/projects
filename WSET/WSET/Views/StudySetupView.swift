import SwiftData
import SwiftUI

struct StudySetupView: View {
    @Query private var questions: [StudyQuestion]
    @Query private var progressRecords: [QuestionProgress]
    @State private var selectedOutcome = LearningOutcome.all
    @State private var sessionSize = 20
    @State private var focusSessionSize = 20
    @State private var selectedFocusDimension = StudyFocusDimension.geography
    @State private var selectedFocusValue: String?
    @State private var sessionQuestions: [StudyQuestion] = []
    @State private var mockQuestions: [StudyQuestion] = []
    @State private var showingSession = false
    @State private var showingMockExam = false

    private var eligibleQuestions: [StudyQuestion] {
        questions.filter { question in
            question.studyMode == "multiple_choice"
                && question.correctAnswerIndex != nil
                && (selectedOutcome == .all || question.learningOutcome == selectedOutcome.rawValue)
        }
    }

    private var mcqQuestions: [StudyQuestion] {
        questions.filter {
            $0.studyMode == "multiple_choice"
                && $0.correctAnswerIndex != nil
        }
    }

    private var focusItems: [StudyFocusItem] {
        mcqQuestions.map { question in
            StudyFocusItem(
                questionID: question.id,
                geography: question.geography,
                countries: question.countries,
                regions: question.regions,
                grapeVarieties: question.grapeVarieties,
                wineType: question.wineType,
                category: question.category,
                difficulty: question.difficulty,
                cognitiveSkill: question.cognitiveSkill
            )
        }
    }

    private var focusOptions: [StudyFocusOption] {
        StudyFocusCatalog.options(for: selectedFocusDimension, in: focusItems)
    }

    private var focusOptionGroups: [StudyFocusOptionGroup] {
        StudyFocusCatalog.optionGroups(
            for: selectedFocusDimension,
            options: focusOptions
        )
    }

    private var selectedFocusOption: StudyFocusOption? {
        if let selectedFocusValue,
           let selected = focusOptions.first(where: { $0.value == selectedFocusValue }) {
            return selected
        }
        return focusOptions.first
    }

    private var focusValueSelection: Binding<String> {
        Binding(
            get: { selectedFocusOption?.value ?? "" },
            set: { selectedFocusValue = $0.isEmpty ? nil : $0 }
        )
    }

    private var focusedQuestions: [StudyQuestion] {
        guard let value = selectedFocusOption?.value else { return [] }
        let questionIDs = StudyFocusCatalog.matchingQuestionIDs(
            for: selectedFocusDimension,
            value: value,
            in: focusItems
        )
        return mcqQuestions.filter { questionIDs.contains($0.id) }
    }

    private var progressByID: [String: QuestionProgress] {
        Dictionary(uniqueKeysWithValues: progressRecords.map { ($0.questionID, $0) })
    }

    private var mistakeQuestions: [StudyQuestion] {
        questions.filter {
            progressByID[$0.id]?.lastWasCorrect == false
        }
    }

    private var dueQuestions: [StudyQuestion] {
        questions.filter {
            guard let progress = progressByID[$0.id] else { return false }
            return progress.attemptCount > 0 && progress.dueDate <= .now
        }
    }

    private var bookmarkedQuestions: [StudyQuestion] {
        questions.filter {
            progressByID[$0.id]?.isBookmarked == true
        }
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Quick study") {
                    Picker("Learning outcome", selection: $selectedOutcome) {
                        ForEach(LearningOutcome.allCases) { outcome in
                            Text(outcome.shortLabel).tag(outcome)
                        }
                    }

                    Picker("Questions", selection: $sessionSize) {
                        Text("10").tag(10)
                        Text("20").tag(20)
                        Text("50").tag(50)
                    }
                    .pickerStyle(.segmented)
                    .accessibilityIdentifier("study.quick.sessionSize")

                    LabeledContent("Available", value: eligibleQuestions.count.formatted())

                    Button {
                        startSession(with: eligibleQuestions, count: sessionSize)
                    } label: {
                        Label("Start mixed study session", systemImage: "play.fill")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(AppTheme.wine)
                    .disabled(eligibleQuestions.isEmpty)
                }

                Section {
                    Picker("切り口", selection: $selectedFocusDimension) {
                        ForEach(StudyFocusDimension.allCases) { dimension in
                            Text(dimension.label).tag(dimension)
                        }
                    }
                    .accessibilityIdentifier("study.focus.dimension")

                    Picker("対象", selection: focusValueSelection) {
                        if focusOptions.isEmpty {
                            Text("候補がありません").tag("")
                        } else if selectedFocusDimension == .grapeVariety {
                            ForEach(focusOptionGroups) { group in
                                Section(group.title) {
                                    ForEach(group.options) { option in
                                        Text(
                                            "\(StudyFocusCatalog.displayValue(for: option, dimension: selectedFocusDimension))（\(option.questionCount)問）"
                                        )
                                        .tag(option.value)
                                    }
                                }
                            }
                        } else {
                            ForEach(focusOptions) { option in
                                Text(
                                    "\(StudyFocusCatalog.displayValue(for: option, dimension: selectedFocusDimension))（\(option.questionCount)問）"
                                )
                                    .tag(option.value)
                            }
                        }
                    }
                    .disabled(focusOptions.isEmpty)
                    .accessibilityIdentifier("study.focus.value")

                    Picker("最大出題数", selection: $focusSessionSize) {
                        Text("10").tag(10)
                        Text("20").tag(20)
                        Text("50").tag(50)
                    }
                    .pickerStyle(.segmented)
                    .accessibilityIdentifier("study.focus.sessionSize")

                    LabeledContent("該当問題数", value: "\(focusedQuestions.count)問")
                        .accessibilityIdentifier("study.focus.availableCount")

                    LabeledContent(
                        "出題予定数",
                        value: "\(min(focusSessionSize, focusedQuestions.count))問"
                    )
                    .accessibilityIdentifier("study.focus.plannedCount")

                    Button {
                        startSession(with: focusedQuestions, count: focusSessionSize)
                    } label: {
                        Label("重点学習を開始", systemImage: "scope")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(AppTheme.wine)
                    .disabled(focusedQuestions.isEmpty)
                    .accessibilityIdentifier("study.focus.startButton")
                } header: {
                    Text("重点学習")
                } footer: {
                    Text(
                        "\(StudyFocusCatalog.guidance(for: selectedFocusDimension)) 該当数が最大出題数未満の場合は全問を出題します。"
                    )
                }

                Section("Focused review") {
                    reviewButton("間違えた問題を復習", systemImage: "xmark.circle", questions: mistakeQuestions)
                    reviewButton("期限の来た問題を学習", systemImage: "calendar", questions: dueQuestions)
                    reviewButton("ブックマークを学習", systemImage: "bookmark", questions: bookmarkedQuestions)
                }

                Section {
                    LabeledContent("Question bank", value: mcqQuestions.count.formatted())
                    Button {
                        mockQuestions = Array(mcqQuestions.shuffled().prefix(50))
                        showingMockExam = mockQuestions.count == 50
                    } label: {
                        Label("Start 50-question mock exam", systemImage: "timer")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(AppTheme.wine)
                    .disabled(mcqQuestions.count < 50)
                } header: {
                    Text("Mock examination")
                } footer: {
                    Text("Answers remain hidden until submission. The result is saved to your progress history.")
                }

            }
            .onAppear { reconcileFocusSelection() }
            .onChange(of: selectedFocusDimension) { _, _ in
                selectedFocusValue = nil
                reconcileFocusSelection()
            }
            .onChange(of: focusOptions) { _, _ in
                reconcileFocusSelection()
            }
            .navigationTitle("Study")
            .navigationDestination(isPresented: $showingSession) {
                StudySessionView(questions: sessionQuestions)
            }
            .navigationDestination(isPresented: $showingMockExam) {
                MockExamView(questions: mockQuestions)
            }
        }
    }

    private func reviewButton(
        _ label: String,
        systemImage: String,
        questions: [StudyQuestion]
    ) -> some View {
        Button {
            startSession(with: questions, count: min(20, questions.count))
        } label: {
            HStack {
                Label(label, systemImage: systemImage)
                Spacer()
                Text(questions.count.formatted())
                    .foregroundStyle(.secondary)
            }
        }
        .disabled(questions.isEmpty)
    }

    private func startSession(with questions: [StudyQuestion], count: Int) {
        sessionQuestions = Array(questions.shuffled().prefix(count))
        showingSession = !sessionQuestions.isEmpty
    }

    private func reconcileFocusSelection() {
        guard !focusOptions.isEmpty else {
            selectedFocusValue = nil
            return
        }
        guard let selectedFocusValue,
              focusOptions.contains(where: { $0.value == selectedFocusValue }) else {
            self.selectedFocusValue = focusOptions.first?.value
            return
        }
    }
}
