import SwiftUI
import SwiftData

struct QuizView: View {
    let words: [Word]
    let title: String

    @Environment(\.modelContext) private var modelContext

    /// 誤答選択肢（ダミー）を作るための全単語プール。
    /// 復習モードなど session が数語しかない場合でも4択を必ず埋められるように、
    /// 出題対象(words)とは別に全単語から選ぶ。
    @Query private var allWords: [Word]

    @State private var session: [Word] = []
    @State private var currentIndex = 0
    @State private var choices: [Word] = []
    @State private var selectedChoiceID: String?
    @State private var isAnswered = false
    @State private var lastAnswerWasCorrect = false
    @State private var correctInSession = 0
    @State private var missedWords: [Word] = []
    @State private var advanceTask: Task<Void, Never>?

    private let sessionSize = 10
    /// 正解時に自動で次の問題へ進むまでの待ち時間（例文を一瞬確認できる程度）
    private let autoAdvanceDelay: Duration = .seconds(1.4)

    var body: some View {
        Group {
            if words.isEmpty {
                emptyState
            } else if session.isEmpty {
                ProgressView()
            } else if currentIndex < session.count {
                quizContent
            } else {
                resultSummary
            }
        }
        .padding()
        .navigationTitle(title)
        .navigationBarTitleDisplayMode(.inline)
        .onAppear(perform: startSessionIfNeeded)
        .onDisappear { advanceTask?.cancel() }
    }

    // MARK: - Empty state

    private var emptyState: some View {
        ContentUnavailableView(
            "単語がありません",
            systemImage: "text.book.closed",
            description: Text("このカテゴリにはまだ単語がありません。")
        )
    }

    // MARK: - Quiz content

    private var quizContent: some View {
        let word = session[currentIndex]

        return VStack(spacing: 20) {
            progressHeader

            VStack(spacing: 12) {
                Text(word.headword)
                    .font(.system(size: 34, weight: .bold))
                    .multilineTextAlignment(.center)

                Button {
                    SpeechService.shared.speak(word.headword)
                } label: {
                    Label("発音を聞く", systemImage: "speaker.wave.2.fill")
                }
                .buttonStyle(.bordered)
            }
            .padding(.vertical, 16)

            VStack(spacing: 12) {
                ForEach(choices, id: \.id) { choice in
                    choiceButton(choice, correctWord: word)
                }
            }

            if isAnswered {
                feedbackBanner(correctWord: word)
                exampleCard(word)

                if lastAnswerWasCorrect {
                    Label("まもなく次の問題へ…", systemImage: "arrow.right.circle")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                } else {
                    Button("次へ") {
                        goToNext()
                    }
                    .buttonStyle(.borderedProminent)
                    .frame(maxWidth: .infinity)
                }
            }

            Spacer()
        }
    }

    private var progressHeader: some View {
        VStack(spacing: 6) {
            ProgressView(value: Double(currentIndex), total: Double(session.count))
                .tint(.accentColor)
            Text("\(currentIndex + 1) / \(session.count)")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }

    @ViewBuilder
    private func choiceButton(_ choice: Word, correctWord: Word) -> some View {
        let isCorrectChoice = choice.id == correctWord.id
        let isSelectedChoice = choice.id == selectedChoiceID

        let label = HStack {
            Text(choice.meaning)
                .frame(maxWidth: .infinity, alignment: .leading)
            if isAnswered && isCorrectChoice {
                Image(systemName: "checkmark.circle.fill")
            } else if isAnswered && isSelectedChoice {
                Image(systemName: "xmark.circle.fill")
            }
        }
        .padding(.vertical, 4)

        let button = Button {
            select(choice, correctWord: correctWord)
        } label: {
            label.frame(maxWidth: .infinity).padding(.vertical, 6)
        }
        .disabled(isAnswered)

        if !isAnswered {
            button.buttonStyle(.bordered).tint(.accentColor)
        } else if isCorrectChoice {
            button.buttonStyle(.borderedProminent).tint(.green)
        } else if isSelectedChoice {
            button.buttonStyle(.borderedProminent).tint(.red)
        } else {
            button.buttonStyle(.bordered).tint(.gray)
        }
    }

    private func feedbackBanner(correctWord: Word) -> some View {
        HStack(spacing: 10) {
            Image(systemName: lastAnswerWasCorrect ? "checkmark.circle.fill" : "xmark.circle.fill")
                .font(.title3)
            VStack(alignment: .leading, spacing: 2) {
                Text(lastAnswerWasCorrect ? "正解！" : "おしい！")
                    .font(.headline)
                if !lastAnswerWasCorrect {
                    Text("正解: \(correctWord.meaning)")
                        .font(.subheadline)
                }
            }
            Spacer()
        }
        .foregroundStyle(.white)
        .padding()
        .background(lastAnswerWasCorrect ? Color.green : Color.red)
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private func exampleCard(_ word: Word) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Label("例文", systemImage: "text.quote")
                .font(.caption)
                .foregroundStyle(.secondary)
            Text(word.exampleSentence)
                .font(.callout)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding()
        .background(Color(.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    // MARK: - Result summary

    private var resultSummary: some View {
        ScrollView {
            VStack(spacing: 16) {
                Text("お疲れさまでした！")
                    .font(.title2.bold())
                Text("正解 \(correctInSession) / \(session.count)")
                    .font(.title3)
                    .foregroundStyle(.secondary)

                if missedWords.isEmpty {
                    Label("全問正解！素晴らしい🎉", systemImage: "star.fill")
                        .foregroundStyle(.orange)
                        .padding(.top, 4)
                } else {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("間違えた単語（復習リストに追加）")
                            .font(.headline)
                        ForEach(missedWords, id: \.id) { word in
                            HStack {
                                Text(word.headword)
                                    .fontWeight(.semibold)
                                Spacer()
                                Text(word.meaning)
                                    .foregroundStyle(.secondary)
                            }
                            .font(.subheadline)
                            Divider()
                        }
                    }
                    .padding()
                    .background(Color(.secondarySystemBackground))
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                }

                Button("もう一度") {
                    startSession()
                }
                .buttonStyle(.borderedProminent)
            }
            .padding(.top, 24)
        }
    }

    // MARK: - Session logic

    private func startSessionIfNeeded() {
        guard session.isEmpty else { return }
        startSession()
    }

    private func startSession() {
        advanceTask?.cancel()
        currentIndex = 0
        correctInSession = 0
        isAnswered = false
        missedWords = []

        let reviewWords = words.filter(\.needsReview).shuffled()
        let otherWords = words.filter { !$0.needsReview }.shuffled()
        let pool = reviewWords + otherWords

        session = Array(pool.prefix(sessionSize))
        prepareChoices()
    }

    private func prepareChoices() {
        guard currentIndex < session.count else { return }
        let correctWord = session[currentIndex]

        // 正解以外の全単語からランダムに3つ選ぶ（全100語プールから）
        let wrongPool = allWords.filter { $0.id != correctWord.id }.shuffled()
        let wrongChoices = Array(wrongPool.prefix(3))

        choices = (wrongChoices + [correctWord]).shuffled()
        isAnswered = false
        selectedChoiceID = nil
    }

    private func select(_ choice: Word, correctWord: Word) {
        guard !isAnswered else { return }
        selectedChoiceID = choice.id
        isAnswered = true

        let isCorrect = choice.id == correctWord.id
        lastAnswerWasCorrect = isCorrect
        if isCorrect {
            correctWord.correctCount += 1
            correctWord.needsReview = false
            correctInSession += 1
            FeedbackService.shared.correct()
        } else {
            correctWord.incorrectCount += 1
            correctWord.needsReview = true
            missedWords.append(correctWord)
            FeedbackService.shared.incorrect()
        }
        correctWord.lastAnsweredAt = Date()
        try? modelContext.save()

        if isCorrect {
            advanceTask?.cancel()
            advanceTask = Task {
                try? await Task.sleep(for: autoAdvanceDelay)
                guard !Task.isCancelled else { return }
                goToNext()
            }
        }
    }

    private func goToNext() {
        advanceTask?.cancel()
        advanceTask = nil
        currentIndex += 1
        if currentIndex < session.count {
            prepareChoices()
        }
    }
}

#Preview {
    NavigationStack {
        QuizView(words: [], title: "プレビュー")
    }
}
