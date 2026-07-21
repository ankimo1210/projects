import SwiftData
import SwiftUI

struct TheoryExamDashboardView: View {
    @Environment(\.modelContext) private var modelContext
    @Environment(EntitlementStore.self) private var entitlementStore
    @Query(sort: \TheoryExamSession.startedAt, order: .reverse)
    private var sessions: [TheoryExamSession]
    @Query private var questions: [StudyQuestion]
    @State private var selectedSession: TheoryExamSession?
    @State private var showingExam = false
    @State private var errorMessage: String?

    private var questionsByID: [String: StudyQuestion] {
        Dictionary(uniqueKeysWithValues: questions.map { ($0.id, $0) })
    }

    private var resumableSession: TheoryExamSession? {
        sessions.first { $0.status != .completed }
    }

    private var completedSessions: [TheoryExamSession] {
        sessions.filter { $0.status == .completed }
    }

    private var theoryCandidateQuestions: [StudyQuestion] {
        StudyQuestionQuery.theoryCandidates(in: questions)
    }

    private var multipleChoiceCount: Int {
        StudyQuestionQuery.multipleChoice(in: theoryCandidateQuestions).count
    }

    private var writtenCount: Int {
        StudyQuestionQuery.written(
            in: theoryCandidateQuestions,
            requiringRubric: true
        ).count
    }

    private var canStartNewExam: Bool {
        multipleChoiceCount >= TheoryExamBuilder.multipleChoiceCount
            && writtenCount >= TheoryExamBuilder.writtenCount
    }

    var body: some View {
        if !entitlementStore.policy.canAccess(.theoryExam), !completedSessions.isEmpty {
            historyOnlyContent
        } else if canStartNewExam || resumableSession != nil {
            PremiumFeatureGate(feature: .theoryExam) {
                dashboardContent
            }
        } else {
            unavailableContent
        }
    }

    private var historyOnlyContent: some View {
        List {
            Section {
                Text("購入状態が変わっても、完了済みの試験結果は引き続き確認できます。新しい試験と中断中の試験はPro対象です。")
                    .foregroundStyle(.secondary)
                NavigationLink {
                    PaywallView(triggerFeature: .theoryExam)
                } label: {
                    Label("理論模擬試験を利用する", systemImage: "lock.open")
                }
            }
            completedHistorySection
        }
        .navigationTitle("理論模擬試験")
        .navigationDestination(isPresented: $showingExam) {
            if let selectedSession {
                TheoryExamView(session: selectedSession, questions: questions)
            }
        }
    }

    private var unavailableContent: some View {
        List {
            Section {
                ContentUnavailableView(
                    "理論模擬試験は公開準備中です",
                    systemImage: "checkmark.seal",
                    description: Text(
                        "四択50問・記述4問が利用可能になると開始できます。"
                    )
                )
            }

            Section("現在の問題") {
                LabeledContent("四択", value: multipleChoiceCount.formatted())
                LabeledContent("記述式", value: writtenCount.formatted())
            }
        }
        .navigationTitle("理論模擬試験")
    }

    private var dashboardContent: some View {
        List {
            Section {
                LabeledContent("試験時間", value: "120分")
                LabeledContent("四択", value: "50問")
                LabeledContent("記述式", value: "4問")
            } header: {
                Text("本番形式")
            } footer: {
                Text("解答は自動保存され、途中で閉じても再開できます。記述式は提出後に採点基準で自己採点します。")
            }

            if let resumableSession {
                Section("進行中") {
                    Button {
                        selectedSession = resumableSession
                        showingExam = true
                    } label: {
                        HStack {
                            Label(
                                resumableSession.status == .inProgress ? "試験を再開" : "自己採点を続ける",
                                systemImage: "arrow.clockwise.circle.fill"
                            )
                            Spacer()
                            Text("\(resumableSession.answeredQuestionIDs.count)/\(resumableSession.totalQuestionCount)")
                                .foregroundStyle(.secondary)
                        }
                    }
                    .accessibilityIdentifier("theoryExam.resume")
                }
            } else {
                Section {
                    LabeledContent("利用可能な四択", value: multipleChoiceCount.formatted())
                    LabeledContent("利用可能な記述式", value: writtenCount.formatted())
                    Button {
                        startExam()
                    } label: {
                        Label("120分模擬試験を開始", systemImage: "timer")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(AppTheme.wine)
                    .disabled(!canStartNewExam)
                    .accessibilityIdentifier("theoryExam.start")
                } header: {
                    Text("新しい試験")
                }
            }

            if !completedSessions.isEmpty {
                completedHistorySection
            }
        }
        .navigationTitle("理論模擬試験")
        .navigationDestination(isPresented: $showingExam) {
            if let selectedSession {
                TheoryExamView(session: selectedSession, questions: questions)
            }
        }
        .alert("試験を開始できません", isPresented: Binding(
            get: { errorMessage != nil },
            set: { if !$0 { errorMessage = nil } }
        )) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(errorMessage ?? "")
        }
        .task {
            reconcileExpiredSessions(at: .now)
        }
    }

    private var completedHistorySection: some View {
        Section("試験履歴") {
            ForEach(completedSessions) { session in
                Button {
                    selectedSession = session
                    showingExam = true
                } label: {
                    HStack {
                        VStack(alignment: .leading) {
                            Text((session.completedAt ?? session.startedAt).formatted(
                                date: .abbreviated,
                                time: .shortened
                            ))
                            Text("四択 \(session.multipleChoiceCorrectCount)/\(session.multipleChoiceQuestionIDs.count) · 記述 \(session.writtenAwardedMarks)/\(session.writtenMaximumMarks)")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            Text("提出：\(session.submissionReason?.label ?? "記録なし")")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            ForEach(theoryExamOutcomeScores(
                                session: session,
                                questionsByID: questionsByID
                            )) { score in
                                Text("\(theoryExamOutcomeLabel(score.learningOutcome)) \(score.totalAwarded)/\(score.totalMaximum)")
                                    .font(.caption2.monospacedDigit())
                                    .foregroundStyle(.secondary)
                                }
                        }
                        Spacer()
                        Text("\(session.totalScore)/\(session.maximumScore)")
                            .font(.headline.monospacedDigit())
                    }
                }
                .buttonStyle(.plain)
            }
        }
    }

    private func startExam() {
        do {
            let candidates = theoryCandidateQuestions.map { question in
                TheoryExamCandidate(
                    id: question.id,
                    learningOutcome: question.learningOutcome,
                    studyMode: question.studyMode
                )
            }
            let blueprint = try TheoryExamBuilder.build(from: candidates)
            let session = TheoryExamSession(
                durationMinutes: blueprint.durationMinutes,
                multipleChoiceQuestionIDs: blueprint.multipleChoiceQuestionIDs,
                writtenQuestionIDs: blueprint.writtenQuestionIDs
            )
            modelContext.insert(session)
            try modelContext.save()
            selectedSession = session
            showingExam = true
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func reconcileExpiredSessions(at now: Date) {
        var didChange = false
        for session in sessions where session.status == .inProgress {
            guard let transition = TheoryExamLifecycle.transition(
                status: session.status,
                deadline: session.deadline,
                now: now,
                trigger: .resume
            ) else { continue }
            let correct = correctMultipleChoiceCount(
                for: session,
                questionsByID: questionsByID
            )
            didChange = session.applySubmission(
                transition,
                multipleChoiceCorrectCount: correct
            ) || didChange
        }
        if didChange {
            try? modelContext.save()
        }
    }
}

struct TheoryExamView: View {
    @Environment(\.modelContext) private var modelContext
    @Environment(\.scenePhase) private var scenePhase
    @Environment(EntitlementStore.self) private var entitlementStore
    let session: TheoryExamSession
    let questions: [StudyQuestion]
    private let nowProvider: () -> Date
    @State private var now: Date
    @State private var showingNavigator = false
    @State private var showingSubmitConfirmation = false

    init(
        session: TheoryExamSession,
        questions: [StudyQuestion],
        nowProvider: @escaping () -> Date = { .now }
    ) {
        self.session = session
        self.questions = questions
        self.nowProvider = nowProvider
        _now = State(initialValue: nowProvider())
    }

    private var questionsByID: [String: StudyQuestion] {
        Dictionary(uniqueKeysWithValues: questions.map { ($0.id, $0) })
    }

    private var orderedQuestions: [StudyQuestion] {
        session.questionIDs.compactMap { questionsByID[$0] }
    }

    private var currentQuestion: StudyQuestion? {
        guard orderedQuestions.indices.contains(session.currentIndex) else { return nil }
        return orderedQuestions[session.currentIndex]
    }

    var body: some View {
        if entitlementStore.policy.canOpenTheoryExam(status: session.status) {
            examContent
        } else {
            PaywallView(triggerFeature: .theoryExam)
        }
    }

    private var examContent: some View {
        Group {
            switch session.status {
            case .inProgress:
                examinationView
            case .awaitingSelfAssessment:
                selfAssessmentView
            case .completed:
                resultView
            }
        }
        .navigationTitle(navigationTitle)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            if session.status == .inProgress {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("提出") { showingSubmitConfirmation = true }
                }
            }
        }
        .sheet(isPresented: $showingNavigator) {
            questionNavigator
                .presentationDetents([.medium, .large])
        }
        .alert("試験を提出しますか？", isPresented: $showingSubmitConfirmation) {
            Button("キャンセル", role: .cancel) {}
            Button("提出") { submitExam(trigger: .manual, at: nowProvider()) }
        } message: {
            Text("未解答は\(max(0, session.totalQuestionCount - session.answeredQuestionIDs.count))問です。提出後、四択の解答は変更できません。")
        }
        .task(id: session.statusRawValue) {
            let resumedAt = nowProvider()
            now = resumedAt
            if submitExam(trigger: .resume, at: resumedAt) {
                return
            }
            while !Task.isCancelled, session.status == .inProgress {
                let tick = nowProvider()
                now = tick
                if submitExam(trigger: .timerTick, at: tick) {
                    break
                }
                try? await Task.sleep(for: .seconds(1))
            }
        }
        .onChange(of: scenePhase) { _, phase in
            if phase == .active {
                let resumedAt = nowProvider()
                now = resumedAt
                _ = submitExam(trigger: .resume, at: resumedAt)
            } else {
                save()
            }
        }
        .onDisappear { try? modelContext.save() }
    }

    private var navigationTitle: String {
        switch session.status {
        case .inProgress: "理論模擬試験"
        case .awaitingSelfAssessment: "記述式の自己採点"
        case .completed: "試験結果"
        }
    }

    private var examinationView: some View {
        VStack(spacing: 0) {
            HStack(spacing: 12) {
                Label(formattedRemainingTime, systemImage: "timer")
                    .font(.headline.monospacedDigit())
                    .foregroundStyle(session.remainingSeconds(at: now) < 600 ? .red : .primary)
                    .accessibilityIdentifier("theoryExam.timer")
                Spacer()
                Button {
                    showingNavigator = true
                } label: {
                    Label(
                        "\(session.answeredQuestionIDs.count)/\(session.totalQuestionCount)",
                        systemImage: "square.grid.3x3"
                    )
                }
                .accessibilityIdentifier("theoryExam.navigator")
            }
            .padding()
            .background(.bar)

            if let currentQuestion {
                ScrollView {
                    VStack(alignment: .leading, spacing: 20) {
                        HStack {
                            Text("第\(session.currentIndex + 1)問 / \(session.totalQuestionCount)問")
                                .font(.headline)
                            Spacer()
                            Button {
                                session.toggleFlag(for: currentQuestion.id)
                                save()
                            } label: {
                                Label(
                                    session.flaggedQuestionIDs.contains(currentQuestion.id)
                                        ? "見直し解除"
                                        : "見直す",
                                    systemImage: session.flaggedQuestionIDs.contains(currentQuestion.id)
                                        ? "flag.fill"
                                        : "flag"
                                )
                            }
                            .tint(.orange)
                            .accessibilityIdentifier("theoryExam.flag")
                        }

                        HStack {
                            MetadataPill(text: currentQuestion.modeLabel)
                            MetadataPill(text: currentQuestion.learningOutcomeLabel)
                        }

                        Text(currentQuestion.displayPrompt)
                            .font(.title2.bold())
                            .frame(maxWidth: .infinity, alignment: .leading)

                        if currentQuestion.studyMode == "multiple_choice" {
                            multipleChoiceAnswers(for: currentQuestion)
                        } else {
                            writtenResponseEditor(for: currentQuestion)
                        }
                    }
                    .padding()
                }
            } else {
                ContentUnavailableView(
                    "問題を読み込めません",
                    systemImage: "exclamationmark.triangle",
                    description: Text("問題データを再読み込みしてください。")
                )
            }

            Divider()
            HStack {
                Button("前へ") { move(to: session.currentIndex - 1) }
                    .disabled(session.currentIndex == 0)
                Spacer()
                if session.currentIndex + 1 >= session.totalQuestionCount {
                    Button("提出") { showingSubmitConfirmation = true }
                        .buttonStyle(.borderedProminent)
                        .tint(AppTheme.wine)
                } else {
                    Button("次へ") { move(to: session.currentIndex + 1) }
                        .buttonStyle(.borderedProminent)
                        .tint(AppTheme.wine)
                }
            }
            .padding()
            .background(.bar)
        }
    }

    private func multipleChoiceAnswers(for question: StudyQuestion) -> some View {
        VStack(spacing: 10) {
            ForEach(Array(question.displayChoices.enumerated()), id: \.offset) { index, choice in
                Button {
                    session.selectAnswer(index, for: question.id)
                    save()
                } label: {
                    HStack(alignment: .top) {
                        Text(String(UnicodeScalar(65 + index)!))
                            .font(.caption.bold())
                            .frame(width: 25, height: 25)
                            .background(.white.opacity(0.8), in: Circle())
                        Text(choice)
                            .multilineTextAlignment(.leading)
                        Spacer()
                        if session.selectedAnswers[question.id] == index {
                            Image(systemName: "checkmark.circle.fill")
                        }
                    }
                    .padding()
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(
                        session.selectedAnswers[question.id] == index
                            ? AppTheme.wineSoft
                            : Color(.secondarySystemGroupedBackground),
                        in: RoundedRectangle(cornerRadius: 14)
                    )
                }
                .buttonStyle(.plain)
            }
        }
    }

    private func writtenResponseEditor(for question: StudyQuestion) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("解答")
                .font(.headline)
            TextEditor(text: Binding(
                get: { session.writtenResponses[question.id] ?? "" },
                set: {
                    session.setWrittenResponse($0, for: question.id)
                    save()
                }
            ))
            .frame(minHeight: 260)
            .padding(8)
            .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 12))
            if let minutes = question.suggestedMinutes {
                Text("目安：\(minutes)分")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }

    private var questionNavigator: some View {
        NavigationStack {
            ScrollView {
                LazyVGrid(columns: Array(repeating: GridItem(.flexible()), count: 6), spacing: 12) {
                    ForEach(Array(session.questionIDs.enumerated()), id: \.element) { index, id in
                        Button {
                            move(to: index)
                            showingNavigator = false
                        } label: {
                            ZStack(alignment: .topTrailing) {
                                Text("\(index + 1)")
                                    .font(.subheadline.bold())
                                    .frame(maxWidth: .infinity, minHeight: 44)
                                    .background(
                                        session.answeredQuestionIDs.contains(id)
                                            ? AppTheme.wineSoft
                                            : Color(.secondarySystemGroupedBackground),
                                        in: RoundedRectangle(cornerRadius: 10)
                                    )
                                    .overlay {
                                        if index == session.currentIndex {
                                            RoundedRectangle(cornerRadius: 10)
                                                .stroke(AppTheme.wine, lineWidth: 2)
                                        }
                                    }
                                if session.answeredQuestionIDs.contains(id) {
                                    Image(systemName: "checkmark.circle.fill")
                                        .font(.caption2)
                                        .foregroundStyle(AppTheme.success)
                                        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .bottomLeading)
                                        .offset(x: -3, y: 3)
                                }
                                if session.flaggedQuestionIDs.contains(id) {
                                    Image(systemName: "flag.fill")
                                        .font(.caption2)
                                        .foregroundStyle(.orange)
                                        .offset(x: 3, y: -3)
                                }
                            }
                        }
                        .buttonStyle(.plain)
                        .accessibilityLabel(
                            "第\(index + 1)問、\(session.answeredQuestionIDs.contains(id) ? "回答済み" : "未回答")\(session.flaggedQuestionIDs.contains(id) ? "、見直しフラグあり" : "")"
                        )
                        .accessibilityIdentifier("theoryExam.navigator.question.\(index + 1)")
                    }
                }
                .padding()

                HStack(spacing: 18) {
                    Label("回答済み", systemImage: "checkmark.circle.fill")
                        .foregroundStyle(AppTheme.success)
                    Label("未回答", systemImage: "square")
                        .foregroundStyle(.secondary)
                    Label("見直し", systemImage: "flag.fill")
                        .foregroundStyle(.orange)
                }
                .font(.caption)
                .padding(.horizontal)
                .padding(.bottom)
            }
            .navigationTitle("問題一覧")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("閉じる") { showingNavigator = false }
                }
            }
        }
    }

    private var selfAssessmentView: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                if let submissionReason = session.submissionReason {
                    Label(
                        submissionReason == .timeExpired
                            ? "時間切れで提出されました。記述式を自己採点してください。"
                            : "手動で提出しました。記述式を自己採点してください。",
                        systemImage: submissionReason == .timeExpired
                            ? "clock.badge.exclamationmark"
                            : "checkmark.circle"
                    )
                    .foregroundStyle(submissionReason == .timeExpired ? .orange : .secondary)
                    .accessibilityIdentifier("theoryExam.selfAssessment.submissionReason")
                }
                Text("自分の解答に含められた要点を選び、得点を記録してください。")
                    .foregroundStyle(.secondary)

                ForEach(writtenQuestions) { question in
                    VStack(alignment: .leading, spacing: 12) {
                        Text(question.displayPrompt)
                            .font(.headline)
                        GroupBox("あなたの解答") {
                            Text(session.writtenResponses[question.id] ?? "未解答")
                                .frame(maxWidth: .infinity, alignment: .leading)
                        }
                        GroupBox("模範解答") {
                            Text(question.displayAnswer)
                                .frame(maxWidth: .infinity, alignment: .leading)
                        }

                        HStack {
                            Text("採点基準")
                                .font(.headline)
                            Spacer()
                            Text("\(writtenScore(for: question))/\(maximumWrittenScore(for: question))点")
                                .font(.headline.monospacedDigit())
                                .foregroundStyle(AppTheme.wine)
                        }
                        ForEach(question.rubricItems) { item in
                            Button {
                                session.toggleRubricItem(item.id, for: question.id)
                                save()
                            } label: {
                                HStack(alignment: .top) {
                                    Image(systemName: selectedRubricIDs(for: question).contains(item.id)
                                          ? "checkmark.square.fill"
                                          : "square")
                                        .foregroundStyle(AppTheme.wine)
                                    Text(item.criterion)
                                        .multilineTextAlignment(.leading)
                                    Spacer()
                                    Text("\(item.marks)点")
                                }
                            }
                            .buttonStyle(.plain)
                        }
                    }
                    .padding()
                    .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 16))
                }

                Button("自己採点を確定") { finalizeExam() }
                    .buttonStyle(.borderedProminent)
                    .tint(AppTheme.wine)
                    .frame(maxWidth: .infinity)
                    .accessibilityIdentifier("theoryExam.finalize")
            }
            .padding()
        }
    }

    private var resultView: some View {
        ScrollView {
            VStack(spacing: 24) {
                VStack(spacing: 8) {
                    Text("\(session.totalScore) / \(session.maximumScore)")
                        .font(.system(size: 48, weight: .bold, design: .rounded))
                        .foregroundStyle(AppTheme.wine)
                    Text("総合得点")
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity)
                .padding()
                .background(AppTheme.wineSoft, in: RoundedRectangle(cornerRadius: 18))

                GroupBox("内訳") {
                    VStack(spacing: 12) {
                        LabeledContent("四択", value: "\(session.multipleChoiceCorrectCount) / \(session.multipleChoiceQuestionIDs.count)")
                        LabeledContent("記述式", value: "\(session.writtenAwardedMarks) / \(session.writtenMaximumMarks)")
                        LabeledContent(
                            "提出種別",
                            value: session.submissionReason?.label ?? "記録なし"
                        )
                        .accessibilityIdentifier("theoryExam.result.submissionReason")
                        LabeledContent(
                            "見直しフラグ",
                            value: "\(session.flaggedQuestionIDs.count)問"
                        )
                    }
                }

                GroupBox("学習成果（LO）別") {
                    VStack(spacing: 14) {
                        ForEach(learningOutcomeScores) { score in
                            VStack(alignment: .leading, spacing: 4) {
                                LabeledContent(
                                    theoryExamOutcomeLabel(score.learningOutcome),
                                    value: "\(score.totalAwarded) / \(score.totalMaximum)"
                                )
                                Text("四択 \(score.multipleChoiceAwarded)/\(score.multipleChoiceMaximum) · 記述 \(score.writtenAwarded)/\(score.writtenMaximum)")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            .accessibilityIdentifier(
                                "theoryExam.result.learningOutcome.\(score.learningOutcome)"
                            )
                        }
                    }
                }
            }
            .padding()
        }
    }

    private var writtenQuestions: [StudyQuestion] {
        session.writtenQuestionIDs.compactMap { questionsByID[$0] }
    }

    private var learningOutcomeScores: [TheoryExamLearningOutcomeScore] {
        theoryExamOutcomeScores(session: session, questionsByID: questionsByID)
    }

    private var formattedRemainingTime: String {
        let remaining = session.remainingSeconds(at: now)
        return String(format: "%02d:%02d:%02d", remaining / 3600, (remaining % 3600) / 60, remaining % 60)
    }

    private func move(to index: Int) {
        guard session.questionIDs.indices.contains(index) else { return }
        session.currentIndex = index
        save()
    }

    @discardableResult
    private func submitExam(
        trigger: TheoryExamSubmissionTrigger,
        at date: Date
    ) -> Bool {
        guard let transition = TheoryExamLifecycle.transition(
            status: session.status,
            deadline: session.deadline,
            now: date,
            trigger: trigger
        ) else { return false }
        let correct = correctMultipleChoiceCount(
            for: session,
            questionsByID: questionsByID
        )
        guard session.applySubmission(
            transition,
            multipleChoiceCorrectCount: correct
        ) else { return false }
        save()
        return true
    }

    private func selectedRubricIDs(for question: StudyQuestion) -> Set<String> {
        Set(session.rubricSelections[question.id] ?? [])
    }

    private func writtenScore(for question: StudyQuestion) -> Int {
        let selected = selectedRubricIDs(for: question)
        return question.rubricItems
            .filter { selected.contains($0.id) }
            .reduce(0) { $0 + $1.marks }
    }

    private func maximumWrittenScore(for question: StudyQuestion) -> Int {
        question.rubricItems.reduce(0) { $0 + $1.marks }
    }

    private func finalizeExam() {
        guard session.status == .awaitingSelfAssessment else { return }
        let awarded = writtenQuestions.reduce(0) { $0 + writtenScore(for: $1) }
        let maximum = writtenQuestions.reduce(0) { $0 + maximumWrittenScore(for: $1) }
        session.complete(writtenAwardedMarks: awarded, writtenMaximumMarks: maximum)
        recordProgressIfNeeded()
        save()
        Task { await ReviewNotificationService.refreshIfEnabled(in: modelContext) }
    }

    private func recordProgressIfNeeded() {
        guard !session.completionRecorded else { return }
        for question in orderedQuestions {
            let isCorrect: Bool
            let rating: Int
            let awardedMarks: Int?
            let maximumMarks: Int?
            let selections: [String]
            let response: String?

            if question.studyMode == "multiple_choice" {
                isCorrect = session.selectedAnswers[question.id] == question.correctAnswerIndex
                rating = isCorrect ? 3 : 0
                awardedMarks = nil
                maximumMarks = nil
                selections = []
                response = nil
            } else {
                let awarded = writtenScore(for: question)
                let maximum = maximumWrittenScore(for: question)
                isCorrect = maximum > 0 && Double(awarded) / Double(maximum) >= 0.6
                rating = isCorrect ? 3 : 0
                awardedMarks = awarded
                maximumMarks = maximum
                selections = Array(selectedRubricIDs(for: question)).sorted()
                response = session.writtenResponses[question.id]
            }

            let existingProgress = progressRecord(for: question.id)
            let progress = existingProgress ?? QuestionProgress(questionID: question.id)
            if existingProgress == nil {
                modelContext.insert(progress)
            }
            progress.record(isCorrect: isCorrect, rating: rating)
            modelContext.insert(StudyAttempt(
                questionID: question.id,
                isCorrect: isCorrect,
                rating: rating,
                responseText: response,
                awardedMarks: awardedMarks,
                maximumMarks: maximumMarks,
                rubricSelections: selections
            ))
        }
        session.completionRecorded = true
    }

    private func progressRecord(for questionID: String) -> QuestionProgress? {
        let descriptor = FetchDescriptor<QuestionProgress>(
            predicate: #Predicate { $0.questionID == questionID }
        )
        return try? modelContext.fetch(descriptor).first
    }

    private func save() {
        try? modelContext.save()
    }
}

private func correctMultipleChoiceCount(
    for session: TheoryExamSession,
    questionsByID: [String: StudyQuestion]
) -> Int {
    session.multipleChoiceQuestionIDs.reduce(into: 0) { result, id in
        guard let question = questionsByID[id],
              session.selectedAnswers[id] == question.correctAnswerIndex,
              question.correctAnswerIndex != nil else { return }
        result += 1
    }
}

private func theoryExamOutcomeScores(
    session: TheoryExamSession,
    questionsByID: [String: StudyQuestion]
) -> [TheoryExamLearningOutcomeScore] {
    let scoringQuestions = session.questionIDs.compactMap { id -> TheoryExamScoringQuestion? in
        guard let question = questionsByID[id] else { return nil }
        return TheoryExamScoringQuestion(
            id: question.id,
            learningOutcome: question.learningOutcome,
            studyMode: question.studyMode,
            correctAnswerIndex: question.correctAnswerIndex,
            rubricMarksByID: Dictionary(
                question.rubricItems.map { ($0.id, $0.marks) },
                uniquingKeysWith: { first, _ in first }
            )
        )
    }
    return TheoryExamScoreCalculator.learningOutcomeScores(
        questions: scoringQuestions,
        selectedAnswers: session.selectedAnswers,
        rubricSelections: session.rubricSelections
    )
}

private func theoryExamOutcomeLabel(_ rawValue: String) -> String {
    LearningOutcome(rawValue: rawValue)?.shortLabel ?? rawValue
}
