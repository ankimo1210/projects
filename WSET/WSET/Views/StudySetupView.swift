import SwiftData
import SwiftUI

struct StudySetupView: View {
    @Environment(EntitlementStore.self) private var entitlementStore
    @Query private var questions: [StudyQuestion]
    @Query private var progressRecords: [QuestionProgress]
    @Query(sort: \WrittenAnswerDraft.updatedAt, order: .reverse)
    private var writtenDrafts: [WrittenAnswerDraft]
    @Query private var attempts: [StudyAttempt]
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
        StudyQuestionQuery.multipleChoice(
            in: accessibleQuestions,
            learningOutcome: selectedOutcome == .all ? nil : selectedOutcome.rawValue
        )
    }

    private var mcqQuestions: [StudyQuestion] {
        StudyQuestionQuery.multipleChoice(in: accessibleQuestions)
    }

    private var writtenQuestions: [StudyQuestion] {
        StudyQuestionQuery.written(in: accessibleQuestions)
            .sorted { $0.id < $1.id }
    }

    private var writtenPracticeButtonTitle: String {
        switch writtenQuestions.count {
        case 0: "記述式問題はありません"
        case 1: "記述式1問を練習"
        default: "記述式\(writtenQuestions.count)問を練習"
        }
    }

    private var theoryExamMultipleChoiceCount: Int {
        StudyQuestionQuery.multipleChoice(in: questions).count
    }

    private var theoryExamWrittenQuestions: [StudyQuestion] {
        StudyQuestionQuery.written(in: questions, requiringRubric: true)
    }

    private var canStartTheoryExam: Bool {
        theoryExamMultipleChoiceCount >= TheoryExamBuilder.multipleChoiceCount
            && theoryExamWrittenQuestions.count >= TheoryExamBuilder.writtenCount
    }

    private var theoryExamEntryTitle: String {
        if !canStartTheoryExam { return "理論模擬試験（公開準備中）" }
        return "120分理論模擬試験"
    }

    private var writtenDraftQuestions: [StudyQuestion] {
        let questionsByID = Dictionary(uniqueKeysWithValues: writtenQuestions.map { ($0.id, $0) })
        return writtenDrafts.compactMap { questionsByID[$0.questionID] }
    }

    private var hasWrittenHistory: Bool {
        attempts.contains { $0.awardedMarks != nil && $0.responseText != nil }
    }

    private var miniMockQuestionCount: Int {
        entitlementStore.policy.miniMockQuestionCount
    }

    private var accessibleQuestions: [StudyQuestion] {
        StudyQuestionQuery.accessible(questions, policy: entitlementStore.policy)
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
        StudyQuestionQuery.mistakes(
            in: accessibleQuestions,
            progressByID: progressByID
        )
    }

    private var dueQuestions: [StudyQuestion] {
        StudyQuestionQuery.due(
            in: accessibleQuestions,
            progressByID: progressByID,
            now: .now
        )
    }

    private var bookmarkedQuestions: [StudyQuestion] {
        StudyQuestionQuery.bookmarked(
            in: accessibleQuestions,
            progressByID: progressByID
        )
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("クイック学習") {
                    Picker("学習成果", selection: $selectedOutcome) {
                        ForEach(LearningOutcome.allCases) { outcome in
                            Text(outcome.shortLabel).tag(outcome)
                        }
                    }

                    Picker("出題数", selection: $sessionSize) {
                        Text("10").tag(10)
                        Text("20").tag(20)
                        Text("50").tag(50)
                    }
                    .pickerStyle(.segmented)
                    .accessibilityIdentifier("study.quick.sessionSize")

                    LabeledContent("対象問題数", value: eligibleQuestions.count.formatted())

                    Button {
                        startSession(with: eligibleQuestions, count: sessionSize)
                    } label: {
                        Label("混合学習を開始", systemImage: "play.fill")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(AppTheme.wine)
                    .disabled(eligibleQuestions.isEmpty)
                }

                Section {
                    LabeledContent("利用可能な問題", value: "\(writtenQuestions.count)問")
                        .accessibilityIdentifier("study.written.availableCount")

                    if !writtenDraftQuestions.isEmpty {
                        Button {
                            sessionQuestions = writtenDraftQuestions
                            showingSession = true
                        } label: {
                            Label(
                                "入力中の下書きを再開（\(writtenDraftQuestions.count)問）",
                                systemImage: "square.and.pencil.circle"
                            )
                        }
                        .accessibilityIdentifier("study.written.resumeDrafts")
                    }

                    if hasWrittenHistory {
                        NavigationLink {
                            WrittenPracticeHistoryListView()
                        } label: {
                            Label("過去回答と得点推移", systemImage: "chart.xyaxis.line")
                        }
                        .accessibilityIdentifier("study.written.history")
                    }

                    Button {
                        startSession(with: writtenQuestions, count: writtenQuestions.count)
                    } label: {
                        Label(
                            writtenPracticeButtonTitle,
                            systemImage: "square.and.pencil"
                        )
                        .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(AppTheme.wine)
                    .disabled(writtenQuestions.isEmpty)
                    .accessibilityIdentifier("study.written.startButton")
                } header: {
                    Text("記述式練習")
                } footer: {
                    if writtenQuestions.isEmpty {
                        Text("利用可能な記述式問題がありません。")
                    } else {
                        Text("利用可能な\(writtenQuestions.count)問を、模範解答と採点基準で自己採点します。")
                    }
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

                Section("今日の学習") {
                    NavigationLink {
                        DailyStudyView()
                    } label: {
                        Label("おすすめ問題を学習", systemImage: "sparkles")
                    }
                    .accessibilityIdentifier("study.daily.open")

                    NavigationLink {
                        WeaknessDashboardView()
                    } label: {
                        Label("弱点を確認", systemImage: "chart.bar.xaxis")
                    }
                    .accessibilityIdentifier("study.weakness.open")
                }

                Section("集中復習") {
                    reviewButton("間違えた問題を復習", systemImage: "xmark.circle", questions: mistakeQuestions)
                    reviewButton("期限の来た問題を学習", systemImage: "calendar", questions: dueQuestions)
                    reviewButton("ブックマークを学習", systemImage: "bookmark", questions: bookmarkedQuestions)
                }

                Section {
                    NavigationLink {
                        TheoryExamDashboardView()
                    } label: {
                        Label(theoryExamEntryTitle, systemImage: "doc.text.magnifyingglass")
                    }
                    .accessibilityIdentifier("study.theoryExam.open")

                    LabeledContent("四択問題数", value: mcqQuestions.count.formatted())
                    LabeledContent("ミニ模試の出題数", value: "\(miniMockQuestionCount)問")
                        .accessibilityIdentifier("study.miniMock.questionCount")
                    Button {
                        mockQuestions = Array(
                            mcqQuestions.shuffled().prefix(miniMockQuestionCount)
                        )
                        showingMockExam = mockQuestions.count == miniMockQuestionCount
                    } label: {
                        Label("\(miniMockQuestionCount)問ミニ模試を開始", systemImage: "timer")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(AppTheme.wine)
                    .disabled(mcqQuestions.count < miniMockQuestionCount)
                    .accessibilityIdentifier("study.miniMock.startButton")
                } header: {
                    Text("本番形式")
                } footer: {
                    if !canStartTheoryExam {
                        Text("理論模擬試験は、四択50問・記述4問が利用可能になるまで開始できません。")
                    } else {
                        Text("120分模試は四択50問と記述4問です。")
                    }
                    Text("ミニ模試は四択\(miniMockQuestionCount)問で、提出まで正答を表示しません。")
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
            .navigationTitle("学習")
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
