import Foundation
import SwiftData
import SwiftUI

struct CourseSessionView: View {
    @ObservedObject var courseStore: CourseStore
    let sessionID: UUID

    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var modelContext
    @EnvironmentObject private var speech: SpeechService
    @State private var selectedOptionID: String?
    @State private var displayedQuestionID: String?
    @State private var selectionIsLocked = false
    @State private var retryOperation: RetryOperation?
    @State private var isWorking = false

    private enum RetryOperation: Equatable {
        case submit
        case advance
    }

    private var session: CourseSession? {
        courseStore.snapshot?.sessions.first { $0.id == sessionID }
    }

    private var currentQuestionID: String? {
        session?.currentQuestionID
    }

    var body: some View {
        Group {
            if courseStore.lesson == nil || courseStore.snapshot == nil {
                unavailableCourseView
            } else if let lesson = courseStore.lesson,
                      let session {
                if session.questionIDs.isEmpty {
                    emptySessionView
                } else if session.completedAt != nil {
                    completionView(lesson: lesson, session: session)
                } else if let questionID = session.currentQuestionID,
                          let question = lesson.question(id: questionID) {
                    questionView(question, session: session)
                } else {
                    missingQuestionView
                }
            } else {
                missingSessionView
            }
        }
        .navigationTitle("時間・場所の語順")
        .navigationBarTitleDisplayMode(.inline)
        .onAppear(perform: synchronizeQuestionState)
        .onChange(of: currentQuestionID) { _, _ in
            speech.stop()
            synchronizeQuestionState()
        }
        .onDisappear {
            speech.stop()
        }
    }

    private var unavailableCourseView: some View {
        Group {
            if let errorMessage = courseStore.errorMessage {
                ContentUnavailableView {
                    Label("学習内容を読み込めません", systemImage: "exclamationmark.triangle")
                } description: {
                    Text(errorMessage)
                } actions: {
                    Button("もう一度読み込む") {
                        _ = courseStore.load(in: modelContext.container)
                    }
                }
            } else {
                ProgressView("学習内容を確認しています…")
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
    }

    private var emptySessionView: some View {
        ContentUnavailableView {
            Label("この学習には問題がありません", systemImage: "doc.questionmark")
        } description: {
            Text("今日の画面へ戻り、学習内容を読み込み直してください。")
        } actions: {
            Button("今日へ戻る") { dismiss() }
        }
    }

    private var missingSessionView: some View {
        ContentUnavailableView {
            Label("学習記録が見つかりません", systemImage: "clock.badge.questionmark")
        } description: {
            Text("この学習セッションを表示できませんでした。")
        } actions: {
            Button("今日へ戻る") { dismiss() }
        }
    }

    private var missingQuestionView: some View {
        ContentUnavailableView {
            Label("問題を表示できません", systemImage: "doc.questionmark")
        } description: {
            Text("保存済みの学習位置と教材が一致しません。")
        } actions: {
            Button("今日へ戻る") { dismiss() }
        }
    }

    private func questionView(
        _ question: CourseQuestion,
        session: CourseSession
    ) -> some View {
        let attempt = session.currentAttempt
        let submitted = attempt != nil

        return ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                progressHeader(session: session)

                VStack(alignment: .leading, spacing: 10) {
                    Text(question.topic == "time" ? "時間の語順" : "場所の語順")
                        .font(.caption.bold())
                        .foregroundStyle(.teal)
                    Text(question.prompt)
                        .font(.title2.bold())
                        .fixedSize(horizontal: false, vertical: true)
                }
                .courseSessionCard()

                VStack(alignment: .leading, spacing: 12) {
                    Text("答えを選ぶ")
                        .font(.headline)

                    ForEach(question.options) { option in
                        optionButton(
                            option,
                            question: question,
                            attempt: attempt
                        )
                    }
                }

                if submitted, let attempt {
                    explanationView(question: question, attempt: attempt)
                } else {
                    confirmationView
                }

                if let errorMessage = courseStore.errorMessage {
                    errorView(message: errorMessage)
                }

                if submitted {
                    Button(action: advance) {
                        Label(
                            session.currentIndex == session.questionIDs.count - 1
                                ? "結果を見る" : "次の問題へ",
                            systemImage: "arrow.right"
                        )
                        .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(.teal)
                    .controlSize(.large)
                    .disabled(isWorking)
                    .accessibilityLabel(
                        session.currentIndex == session.questionIDs.count - 1
                            ? "回答を保存して結果を見る" : "回答を保存して次の問題へ進む"
                    )
                }
            }
            .padding()
        }
        .id(question.id)
    }

    private func progressHeader(session: CourseSession) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("問題 \(session.currentIndex + 1) / \(session.questionIDs.count)")
                    .font(.subheadline.monospacedDigit())
                Spacer()
                Text("全\(session.questionIDs.count)問")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            ProgressView(
                value: Double(session.currentIndex + 1),
                total: Double(session.questionIDs.count)
            )
            .tint(.teal)
            .accessibilityLabel("この学習の進捗")
            .accessibilityValue("\(session.questionIDs.count)問中\(session.currentIndex + 1)問目")
        }
    }

    private func optionButton(
        _ option: CourseOption,
        question: CourseQuestion,
        attempt: CourseAttempt?
    ) -> some View {
        let isSelected = selectedOptionID == option.id
        let isCorrectOption = option.id == question.correctOptionID
        let optionStatus: OptionStatus? = {
            guard attempt != nil else { return nil }
            if isCorrectOption { return .correct }
            if isSelected { return .selectedIncorrect }
            return nil
        }()

        return Button {
            guard !selectionIsLocked, attempt == nil else { return }
            selectedOptionID = option.id
        } label: {
            HStack(alignment: .top, spacing: 12) {
                Image(systemName: isSelected ? "largecircle.fill.circle" : "circle")
                    .foregroundStyle(isSelected ? Color.teal : Color.secondary)
                    .padding(.top, 2)

                Text(option.text)
                    .font(.body)
                    .foregroundStyle(.primary)
                    .multilineTextAlignment(.leading)
                    .fixedSize(horizontal: false, vertical: true)

                Spacer(minLength: 8)

                if let optionStatus {
                    Label(optionStatus.label, systemImage: optionStatus.icon)
                        .font(.caption.bold())
                        .foregroundStyle(optionStatus.color)
                        .labelStyle(.titleAndIcon)
                }
            }
            .padding(16)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                isSelected ? Color.teal.opacity(0.12) : Color.secondary.opacity(0.08),
                in: RoundedRectangle(cornerRadius: 14)
            )
            .overlay {
                RoundedRectangle(cornerRadius: 14)
                    .stroke(isSelected ? Color.teal : Color.clear, lineWidth: 2)
            }
            .contentShape(RoundedRectangle(cornerRadius: 14))
        }
        .buttonStyle(.plain)
        .disabled(selectionIsLocked || attempt != nil)
        .accessibilityLabel(optionAccessibilityLabel(option, status: optionStatus))
        .accessibilityAddTraits(isSelected ? .isSelected : [])
    }

    private var confirmationView: some View {
        VStack(alignment: .leading, spacing: 10) {
            if selectionIsLocked {
                Label(
                    "選んだ答えを保存できていません。同じ答えで再試行してください。",
                    systemImage: "lock.fill"
                )
                .font(.subheadline)
                .foregroundStyle(.secondary)
            }

            Button(action: submitSelection) {
                Label(
                    selectionIsLocked ? "同じ回答を保存し直す" : "この回答で決定",
                    systemImage: selectionIsLocked ? "arrow.clockwise" : "checkmark"
                )
                .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .tint(.teal)
            .controlSize(.large)
            .disabled(selectedOptionID == nil || isWorking)
        }
    }

    private func explanationView(
        question: CourseQuestion,
        attempt: CourseAttempt
    ) -> some View {
        let selectedOption = question.options.first { $0.id == attempt.selectedOptionID }

        return VStack(alignment: .leading, spacing: 18) {
            Label(
                attempt.isCorrect ? "正解" : "不正解",
                systemImage: attempt.isCorrect ? "checkmark.circle.fill" : "xmark.circle.fill"
            )
            .font(.title3.bold())
            .foregroundStyle(attempt.isCorrect ? Color.green : Color.red)

            if let selectedOption,
               selectedOption.explanation != question.explanation {
                VStack(alignment: .leading, spacing: 6) {
                    Text("選んだ答えについて")
                        .font(.headline)
                    Text(selectedOption.explanation)
                        .font(.body)
                }
            }

            VStack(alignment: .leading, spacing: 6) {
                Text("基本ルール")
                    .font(.headline)
                Text(question.explanation)
                    .font(.body)
            }

            Divider()

            VStack(alignment: .leading, spacing: 8) {
                Text("正しい文")
                    .font(.headline)
                Text(question.example.hanzi)
                    .font(.title2.bold())
                    .fixedSize(horizontal: false, vertical: true)
                    .accessibilityLabel("中国語：\(question.example.hanzi)")
                Text(question.example.pinyin)
                    .font(.body)
                    .foregroundStyle(.secondary)
                    .accessibilityLabel("ピンイン：\(question.example.pinyin)")
                Text(question.example.japanese)
                    .font(.body)
                    .accessibilityLabel("日本語訳：\(question.example.japanese)")
            }

            ViewThatFits(in: .horizontal) {
                HStack(spacing: 10) {
                    speechButton(title: "標準で聞く", speed: .normal, text: question.example.hanzi)
                    speechButton(title: "ゆっくり聞く", speed: .slow, text: question.example.hanzi)
                }
                VStack(alignment: .leading, spacing: 10) {
                    speechButton(title: "標準で聞く", speed: .normal, text: question.example.hanzi)
                    speechButton(title: "ゆっくり聞く", speed: .slow, text: question.example.hanzi)
                }
            }
        }
        .courseSessionCard()
    }

    private func speechButton(
        title: String,
        speed: SpeechSpeed,
        text: String
    ) -> some View {
        Button {
            speech.speak(
                cleanedChineseSpeech(text),
                language: .mandarin,
                speed: speed
            )
        } label: {
            Label(title, systemImage: "speaker.wave.2.fill")
                .frame(maxWidth: .infinity)
        }
        .buttonStyle(.bordered)
        .tint(.teal)
        .accessibilityHint("端末の中国語音声で例文を再生します")
    }

    private func errorView(message: String) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Label(message, systemImage: "exclamationmark.triangle.fill")
                .font(.subheadline)

            if let retryOperation {
                Button(retryOperation == .submit ? "同じ回答で再試行" : "次へ進む操作を再試行") {
                    switch retryOperation {
                    case .submit:
                        submitSelection()
                    case .advance:
                        advance()
                    }
                }
                .buttonStyle(.bordered)
                .disabled(isWorking)
            } else {
                Button("閉じる") {
                    courseStore.clearError()
                }
                .buttonStyle(.bordered)
            }
        }
        .foregroundStyle(.red)
        .courseSessionCard()
    }

    private func completionView(
        lesson: CourseLesson,
        session: CourseSession
    ) -> some View {
        let attemptedCount = session.attempts.count
        let futureReviews = session.questionIDs.compactMap {
            courseStore.snapshot?.progress[$0]?.nextReviewAt
        }
        let dueCount = futureReviews.filter { $0 <= Date() }.count
        let nextReview = futureReviews.filter { $0 > Date() }.min()

        return ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                VStack(alignment: .leading, spacing: 10) {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.system(.largeTitle, design: .rounded).bold())
                        .foregroundStyle(.teal)
                    Text("今回の学習を終えました")
                        .font(.largeTitle.bold())
                    Text("\(lesson.title)の回答を保存しました。")
                        .foregroundStyle(.secondary)
                }

                VStack(alignment: .leading, spacing: 14) {
                    Text("今回の結果")
                        .font(.headline)
                    HStack(alignment: .firstTextBaseline) {
                        Text("正解")
                        Spacer()
                        Text("\(session.correctCount) / \(attemptedCount)問")
                            .font(.title2.bold().monospacedDigit())
                            .foregroundStyle(.teal)
                    }
                    Text("この結果は今回の回答記録です。習得度や試験結果を示すものではありません。")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
                .courseSessionCard()

                VStack(alignment: .leading, spacing: 10) {
                    Label("これからの復習", systemImage: "clock.arrow.circlepath")
                        .font(.headline)
                    if dueCount > 0 {
                        Text("期限の来た問題が\(dueCount)問あります。今日の画面から復習できます。")
                            .font(.subheadline)
                    } else if let nextReview {
                        Text("次の復習予定：\(nextReview.formatted(.dateTime.month().day().hour().minute()))")
                            .font(.subheadline)
                    } else {
                        Text("現在、復習予定はありません。")
                            .font(.subheadline)
                    }
                }
                .courseSessionCard()

                Button("今日へ戻る") {
                    speech.stop()
                    dismiss()
                }
                .buttonStyle(.borderedProminent)
                .tint(.teal)
                .controlSize(.large)
                .frame(maxWidth: .infinity)
            }
            .padding()
        }
    }

    private func submitSelection() {
        guard let selectedOptionID else { return }
        isWorking = true
        selectionIsLocked = true
        courseStore.clearError()
        if courseStore.submit(optionID: selectedOptionID) {
            retryOperation = nil
        } else {
            retryOperation = .submit
        }
        isWorking = false
    }

    private func advance() {
        isWorking = true
        speech.stop()
        courseStore.clearError()
        if courseStore.advance() {
            retryOperation = nil
            synchronizeQuestionState()
        } else {
            retryOperation = .advance
        }
        isWorking = false
    }

    private func synchronizeQuestionState() {
        guard let session,
              let questionID = session.currentQuestionID else {
            displayedQuestionID = nil
            selectedOptionID = nil
            selectionIsLocked = false
            retryOperation = nil
            return
        }

        if displayedQuestionID != questionID {
            let submittedOptionID = session.currentAttempt?.selectedOptionID
            let pendingOptionID = courseStore.pendingOptionID
            displayedQuestionID = questionID
            selectedOptionID = submittedOptionID ?? pendingOptionID
            selectionIsLocked = submittedOptionID != nil || pendingOptionID != nil
            retryOperation = submittedOptionID == nil && pendingOptionID != nil ? .submit : nil
        } else if let attempt = session.currentAttempt {
            selectedOptionID = attempt.selectedOptionID
            selectionIsLocked = true
            retryOperation = nil
        } else if let pendingOptionID = courseStore.pendingOptionID {
            selectedOptionID = pendingOptionID
            selectionIsLocked = true
            retryOperation = .submit
        }
    }

    private func cleanedChineseSpeech(_ text: String) -> String {
        text
            .replacingOccurrences(of: "「", with: "")
            .replacingOccurrences(of: "」", with: "")
            .split(whereSeparator: \.isWhitespace)
            .joined(separator: " ")
    }

    private func optionAccessibilityLabel(
        _ option: CourseOption,
        status: OptionStatus?
    ) -> String {
        guard let status else { return option.text }
        return "\(option.text)、\(status.label)"
    }
}

private enum OptionStatus {
    case correct
    case selectedIncorrect

    var label: String {
        switch self {
        case .correct: "正解"
        case .selectedIncorrect: "選択・不正解"
        }
    }

    var icon: String {
        switch self {
        case .correct: "checkmark.circle.fill"
        case .selectedIncorrect: "xmark.circle.fill"
        }
    }

    var color: Color {
        switch self {
        case .correct: .green
        case .selectedIncorrect: .red
        }
    }
}

private extension View {
    func courseSessionCard() -> some View {
        padding(16)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(.secondary.opacity(0.08), in: RoundedRectangle(cornerRadius: 16))
    }
}
