import SwiftData
import SwiftUI
import UIKit

struct VocabularyStudyView: View {
    let level: HSKLevel
    let cumulative: Bool
    let mode: StudySessionMode
    let maximumItemCount: Int

    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var modelContext
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize
    @EnvironmentObject private var contentStore: LearningContentStore
    @EnvironmentObject private var speech: SpeechService
    @AppStorage("autoSpeakCorrectAnswer") private var autoSpeakCorrectAnswer = true
    @AppStorage("speechSpeedRawValue") private var speechSpeedRawValue = SpeechSpeed.normal.rawValue
    @State private var session: StudySessionState?
    @State private var itemsByID: [String: VocabularyItem] = [:]
    @State private var errorMessage: String?
    @State private var persistenceError: String?
    @State private var detailItem: VocabularyItem?
    @ScaledMetric(relativeTo: .largeTitle) private var hanziFontSize: CGFloat = 45

    private var speed: SpeechSpeed {
        SpeechSpeed(rawValue: speechSpeedRawValue) ?? .normal
    }

    private var usesFlexibleLayout: Bool {
        dynamicTypeSize.isAccessibilitySize
    }

    private var scopeKey: String {
        "vocabulary.hsk3.\(level.rawValue).\(cumulative ? "cumulative" : "level").\(mode.rawValue).count-\(maximumItemCount)"
    }

    var body: some View {
        Group {
            if let session, session.isComplete {
                completionView(session)
            } else if let session, let question = session.currentQuestion,
                      let item = itemsByID[question.id] {
                questionView(session: session, question: question, item: item)
            } else if let errorMessage {
                ContentUnavailableView(
                    "開始できません",
                    systemImage: "exclamationmark.triangle",
                    description: Text(errorMessage)
                )
            } else {
                ProgressView("問題を準備中…")
            }
        }
        .navigationTitle(level.displayName)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Menu {
                    Button("新しい順番でやり直す", systemImage: "arrow.clockwise") {
                        restart()
                    }
                    Button("終了", systemImage: "xmark") { dismiss() }
                } label: {
                    Image(systemName: "ellipsis.circle")
                }
            }
        }
        .sheet(item: $detailItem) { item in
            NavigationStack { VocabularyDetailView(item: item) }
        }
        .task { await startOrResume() }
        .onDisappear { speech.stop() }
        .alert("学習記録を保存できません", isPresented: persistenceErrorBinding) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(persistenceError ?? "不明なエラー")
        }
    }

    @ViewBuilder
    private func questionView(
        session: StudySessionState,
        question: StudySessionQuestionState,
        item: VocabularyItem
    ) -> some View {
        ScrollView {
            VStack(spacing: 12) {
                HStack {
                    Text("\(session.currentIndex + 1) / \(session.questions.count)")
                        .font(.subheadline.monospacedDigit())
                    ProgressView(
                        value: Double(session.currentIndex + (question.isAnswered ? 1 : 0)),
                        total: Double(session.questions.count)
                    )
                    Button {
                        speechSpeedRawValue = speed.next.rawValue
                    } label: {
                        Label(speed.label, systemImage: "speedometer")
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.small)
                    .frame(minHeight: 44)
                }

                VStack(spacing: 8) {
                    Text(item.hanzi)
                        .font(.system(size: hanziFontSize, weight: .bold, design: .rounded))
                        .environment(\.locale, Locale(identifier: "zh-CN"))
                    HStack(spacing: 6) {
                        Text(item.pinyin)
                            .font(.title3.weight(.medium))
                            .foregroundStyle(.orange)
                        if let partOfSpeech = item.displayPartOfSpeech {
                            Text(partOfSpeech)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        if item.isMachineTranslated {
                            Text("仮訳")
                                .font(.caption2.bold())
                                .foregroundStyle(.orange)
                                .padding(.horizontal, 5)
                                .background(.orange.opacity(0.12), in: Capsule())
                        }
                    }
                    Button {
                        speech.speak(item.hanzi, speed: speed)
                    } label: {
                        Label("発音", systemImage: "speaker.wave.2.fill")
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.small)
                }
                .frame(
                    maxWidth: .infinity,
                    minHeight: 124,
                    maxHeight: usesFlexibleLayout ? nil : 124
                )
                .background(.blue.opacity(0.08), in: RoundedRectangle(cornerRadius: 18))

                VStack(spacing: 8) {
                    ForEach(question.optionIDs, id: \.self) { optionID in
                        if let option = itemsByID[optionID] {
                            choiceButton(option, question: question)
                        }
                    }
                }
                .frame(
                    maxWidth: .infinity,
                    minHeight: usesFlexibleLayout ? nil : 272,
                    maxHeight: usesFlexibleLayout ? nil : 272,
                    alignment: .top
                )

                feedbackPanel(item: item, question: question)
                    .frame(
                        maxWidth: .infinity,
                        minHeight: 126,
                        maxHeight: usesFlexibleLayout ? nil : 126
                    )

                let controlsLayout = usesFlexibleLayout
                    ? AnyLayout(VStackLayout(spacing: 10))
                    : AnyLayout(HStackLayout(spacing: 10))
                controlsLayout {
                    Button {
                        goBack()
                    } label: {
                        Label("戻る", systemImage: "arrow.left")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.bordered)
                    .disabled(!session.canGoBack)

                    Button {
                        detailItem = item
                    } label: {
                        Label("詳細", systemImage: "info.circle")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.bordered)

                    Button {
                        advance()
                    } label: {
                        Label("次へ", systemImage: "arrow.right")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(!session.canAdvance)
                }
                .frame(height: usesFlexibleLayout ? nil : 46)
            }
            .padding()
        }
    }

    private func choiceButton(
        _ option: VocabularyItem,
        question: StudySessionQuestionState
    ) -> some View {
        let selected = question.selectedOptionID == option.id
        let correct = question.correctOptionID == option.id
        return Button {
            if question.isAnswered {
                speech.speak(option.hanzi, speed: speed)
            } else {
                answer(optionID: option.id)
            }
        } label: {
            HStack(spacing: 10) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(option.primaryJapanese)
                        .font(.body.weight(.medium))
                        .foregroundStyle(.primary)
                        .lineLimit(usesFlexibleLayout ? 3 : 1)
                        .minimumScaleFactor(0.75)
                    if question.isAnswered {
                        HStack(spacing: 8) {
                            Text(option.hanzi).font(.subheadline.weight(.semibold))
                            Text(option.pinyin).font(.caption).foregroundStyle(.orange)
                        }
                        .lineLimit(usesFlexibleLayout ? 2 : 1)
                    } else {
                        Text(" ").font(.caption)
                    }
                }
                Spacer()
                ZStack(alignment: .bottomTrailing) {
                    Image(systemName: "speaker.wave.2.fill")
                        .foregroundStyle(.blue)
                    if correct {
                        Image(systemName: "checkmark.circle.fill")
                            .font(.caption)
                            .foregroundStyle(.green)
                    } else if selected {
                        Image(systemName: "xmark.circle.fill")
                            .font(.caption)
                            .foregroundStyle(.red)
                    }
                }
                .frame(width: 32, height: 32)
                .opacity(question.isAnswered ? 1 : 0)
                .accessibilityHidden(true)
            }
            .padding(.horizontal, 14)
            .frame(
                maxWidth: .infinity,
                minHeight: 62,
                maxHeight: usesFlexibleLayout ? nil : 62
            )
            .background(choiceBackground(selected: selected, correct: correct, answered: question.isAnswered))
            .clipShape(RoundedRectangle(cornerRadius: 14))
            .overlay {
                RoundedRectangle(cornerRadius: 14)
                    .stroke(choiceBorder(selected: selected, correct: correct, answered: question.isAnswered), lineWidth: 1.5)
            }
        }
        .buttonStyle(.plain)
        .accessibilityLabel(
            question.isAnswered
                ? "選択肢、\(option.primaryJapanese)、\(option.hanzi)、\(option.pinyin)"
                : "選択肢、\(option.primaryJapanese)"
        )
        .accessibilityValue(choiceAccessibilityValue(
            selected: selected,
            correct: correct,
            answered: question.isAnswered
        ))
        .accessibilityHint(
            question.isAnswered
                ? "タップすると中国語の発音を再生します"
                : "タップして回答します"
        )
    }

    @ViewBuilder
    private func feedbackPanel(
        item: VocabularyItem,
        question: StudySessionQuestionState
    ) -> some View {
        if question.isAnswered {
            VStack(alignment: .leading, spacing: 7) {
                Label(
                    question.isCorrect == true ? "正解" : "不正解 — 正解は「\(item.primaryJapanese)」",
                    systemImage: question.isCorrect == true ? "checkmark.circle.fill" : "xmark.circle.fill"
                )
                .font(.subheadline.bold())
                .foregroundStyle(question.isCorrect == true ? .green : .red)

                if let example = item.examples.first {
                    HStack(alignment: .top) {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(example.hanzi).font(.subheadline.weight(.semibold))
                            Text(example.pinyin).font(.caption).foregroundStyle(.orange)
                            Text(example.japanese).font(.caption).foregroundStyle(.secondary)
                        }
                        Spacer()
                        Button {
                            speech.speak(example.hanzi, speed: speed)
                        } label: {
                            Image(systemName: "speaker.wave.2.fill")
                        }
                        .buttonStyle(.bordered)
                        .controlSize(.small)
                        .frame(minWidth: 44, minHeight: 44)
                        .accessibilityLabel("例文を発音")
                    }
                } else {
                    Text("例文は順次追加予定です。単語詳細から復習対象に追加できます。")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .padding(12)
            .background(.secondary.opacity(0.08), in: RoundedRectangle(cornerRadius: 14))
        } else {
            Label("意味を選んでください", systemImage: "hand.tap")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .center)
                .background(.secondary.opacity(0.08), in: RoundedRectangle(cornerRadius: 14))
        }
    }

    private func completionView(_ session: StudySessionState) -> some View {
        VStack(spacing: 18) {
            Image(systemName: "checkmark.seal.fill")
                .font(.system(size: 58))
                .foregroundStyle(.green)
            Text("セッション完了")
                .font(.title.bold())
            Text("\(session.questions.count)問中 \(session.correctCount)問正解")
                .font(.title3.monospacedDigit())
            ProgressView(value: Double(session.correctCount), total: Double(session.questions.count))
                .tint(.green)
                .padding(.horizontal, 40)

            Button("もう一度", systemImage: "arrow.clockwise") { restart() }
                .buttonStyle(.borderedProminent)
            Button("最後の問題に戻る", systemImage: "arrow.left") { goBack() }
                .buttonStyle(.bordered)
            Button("単語メニューへ戻る") { dismiss() }
        }
        .padding()
    }

    private func startOrResume(resume: Bool = true) async {
        do {
            try await contentStore.ensureLoaded(for: level, cumulative: cumulative)
            let vocabulary = contentStore.vocabulary(for: level, cumulative: cumulative)
            guard vocabulary.count >= 4 else {
                throw StudySessionEngineError.noItems
            }
            itemsByID = Dictionary(uniqueKeysWithValues: vocabulary.map { ($0.id, $0) })

            if resume,
               let saved = try StudyPersistence.loadSession(scopeKey: scopeKey, in: modelContext),
               saved.questions.allSatisfy({ itemsByID[$0.id] != nil }) {
                session = saved
                errorMessage = nil
                return
            }

            let progress = try StudyPersistence.progressMap(in: modelContext, skill: .vocabulary)
            let configuration = StudySessionConfiguration(
                mode: mode,
                seed: UInt64.random(in: 1...UInt64.max),
                optionCount: 4,
                maximumItemCount: maximumItemCount,
                includeUnseenInDueReview: false,
                minimumAttemptsForWeakMode: 1
            )
            let newSession = try StudySessionEngine.makeSession(
                items: VocabularySessionFactory.studyItems(from: vocabulary),
                progressByItemID: progress,
                configuration: configuration
            )
            session = newSession
            try StudyPersistence.saveSession(newSession, scopeKey: scopeKey, in: modelContext)
            errorMessage = nil
        } catch StudySessionEngineError.noEligibleItems(.dueReview) {
            errorMessage = "今日の復習対象はありません。出題順を「順番」か「シャッフル」に変更してください。"
        } catch StudySessionEngineError.noEligibleItems(.weak) {
            errorMessage = "苦手データがまだありません。まず通常の問題に回答してください。"
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func answer(optionID: String) {
        guard var updated = session, let current = updated.currentQuestion else { return }
        do {
            let answer = try updated.recordAnswer(optionID: optionID)
            session = updated
            if UIAccessibility.isVoiceOverRunning {
                UIAccessibility.post(
                    notification: .announcement,
                    argument: answer.isCorrect ? "正解" : "不正解"
                )
            }
            _ = try StudyPersistence.recordAnswer(
                itemID: answer.itemID,
                skill: .vocabulary,
                isCorrect: answer.isCorrect,
                in: modelContext
            )
            try StudyPersistence.saveSession(updated, scopeKey: scopeKey, in: modelContext)
            if autoSpeakCorrectAnswer, let item = itemsByID[current.correctOptionID] {
                speech.speak(item.hanzi, speed: speed)
            }
        } catch {
            persistenceError = error.localizedDescription
        }
    }

    private func advance() {
        guard var updated = session else { return }
        do {
            let result = try updated.advance()
            session = updated
            if result == .completed {
                try StudyPersistence.removeSession(scopeKey: scopeKey, in: modelContext)
            } else {
                try StudyPersistence.saveSession(updated, scopeKey: scopeKey, in: modelContext)
            }
        } catch {
            persistenceError = error.localizedDescription
        }
    }

    private func goBack() {
        guard var updated = session, updated.goBack() else { return }
        session = updated
        try? StudyPersistence.saveSession(updated, scopeKey: scopeKey, in: modelContext)
    }

    private func restart() {
        try? StudyPersistence.removeSession(scopeKey: scopeKey, in: modelContext)
        session = nil
        errorMessage = nil
        Task { await startOrResume(resume: false) }
    }

    private func choiceBackground(selected: Bool, correct: Bool, answered: Bool) -> Color {
        guard answered else { return Color.secondary.opacity(0.07) }
        if correct { return Color.green.opacity(0.13) }
        if selected { return Color.red.opacity(0.12) }
        return Color.secondary.opacity(0.07)
    }

    private func choiceBorder(selected: Bool, correct: Bool, answered: Bool) -> Color {
        guard answered else { return Color.secondary.opacity(0.2) }
        if correct { return .green }
        if selected { return .red }
        return Color.secondary.opacity(0.2)
    }

    private func choiceAccessibilityValue(
        selected: Bool,
        correct: Bool,
        answered: Bool
    ) -> String {
        guard answered else { return "" }
        if correct { return "正解" }
        if selected { return "選択した不正解" }
        return "不正解の選択肢"
    }

    private var persistenceErrorBinding: Binding<Bool> {
        Binding(
            get: { persistenceError != nil },
            set: { if !$0 { persistenceError = nil } }
        )
    }
}
