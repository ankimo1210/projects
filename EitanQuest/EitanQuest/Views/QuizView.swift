import SwiftUI
import SwiftData

struct QuizView: View {
    let words: [Word]
    let title: String

    @Environment(\.modelContext) private var modelContext
    @Environment(\.dismiss) private var dismiss

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
    /// 正解後の自動遷移を例文タップで一時停止したかどうか
    @State private var autoAdvancePaused = false

    @AppStorage("autoPronounceEnabled") private var autoPronounceEnabled = true

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

        return ScrollView {
            VStack(spacing: 20) {
                progressHeader
                questionBody(word)
                    .id(word.id)
                    .transition(
                        .asymmetric(
                            insertion: .move(edge: .trailing),
                            removal: .move(edge: .leading)
                        )
                        .combined(with: .opacity)
                    )
            }
        }
        .scrollBounceBehavior(.basedOnSize)
        // 正解後は画面のどこをタップしても即座に次へ進める
        .contentShape(Rectangle())
        .onTapGesture {
            if isAnswered && lastAnswerWasCorrect && !autoAdvancePaused {
                goToNextAnimated()
            }
        }
        .safeAreaInset(edge: .bottom) {
            // コンテンツ量に関わらず必ず押せるよう、「次へ」は画面下部に固定する
            if isAnswered && (!lastAnswerWasCorrect || autoAdvancePaused) {
                Button {
                    goToNextAnimated()
                } label: {
                    Text("次へ")
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 6)
                }
                .buttonStyle(.borderedProminent)
                .padding(.top, 8)
                .background(.bar)
            }
        }
    }

    private func questionBody(_ word: Word) -> some View {
        VStack(spacing: 20) {
            VStack(spacing: 12) {
                Text(word.headword)
                    .font(.system(size: 34, weight: .bold))
                    .multilineTextAlignment(.center)

                if !word.phonetic.isEmpty {
                    Text(word.phonetic)
                        .font(.title3)
                        .foregroundStyle(.secondary)
                }

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
                Group {
                    feedbackBanner(correctWord: word)
                    exampleCard(word)
                }
                .transition(.opacity.combined(with: .scale(scale: 0.97)))

                if lastAnswerWasCorrect && !autoAdvancePaused {
                    Label("タップで次へ", systemImage: "hand.tap")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            }
        }
    }

    private var progressHeader: some View {
        // 回答した瞬間にバーが進むよう、回答済みなら現在の問題も完了扱いにする
        let completed = min(currentIndex + (isAnswered ? 1 : 0), session.count)
        return VStack(spacing: 6) {
            ProgressView(value: Double(completed), total: Double(session.count))
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

        // 回答後は誤答選択肢にも対応する英単語を出し、ダミーからも学べるようにする。
        // 縦に伸びて画面からはみ出さないよう、意味の下に積まず同じ行の右側にインライン表示する。
        let label = HStack(spacing: 8) {
            Text(choice.meaning)
                .lineLimit(2)
            if isAnswered {
                Text(choice.headword)
                    .font(.caption)
                    .opacity(0.85)
                    .lineLimit(1)
            }
            Spacer(minLength: 4)
            if isAnswered && isCorrectChoice {
                Image(systemName: "checkmark.circle.fill")
            } else if isAnswered && isSelectedChoice {
                Image(systemName: "xmark.circle.fill")
            }
        }
        .padding(.vertical, 4)

        // .disabled() は回答後の正誤カラーまでグレーアウトしてしまうため使わない。
        // 多重回答は select() 冒頭の guard で防ぐ。
        let button = Button {
            select(choice, correctWord: correctWord)
        } label: {
            label.frame(maxWidth: .infinity).padding(.vertical, 6)
        }

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
            if !word.exampleSentenceJa.isEmpty {
                Text(word.exampleSentenceJa)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
        .padding()
        .background(Color(.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .contentShape(Rectangle())
        // 例文を読みたい人向け: カードをタップすると自動遷移を止めて「次へ」に切り替える
        .onTapGesture {
            if isAnswered && lastAnswerWasCorrect && !autoAdvancePaused {
                pauseAutoAdvance()
            }
        }
    }

    // MARK: - Result summary

    private var resultSummary: some View {
        ScrollView {
            VStack(spacing: 20) {
                Text("お疲れさまでした！")
                    .font(.title2.bold())

                AccuracyRing(accuracy: session.isEmpty ? 0 : Double(correctInSession) / Double(session.count))

                Text("正解 \(correctInSession) / \(session.count)")
                    .font(.title3)
                    .foregroundStyle(.secondary)

                if missedWords.isEmpty {
                    Label("全問正解！素晴らしい🎉", systemImage: "star.fill")
                        .foregroundStyle(.orange)
                } else {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("間違えた単語（復習リストに追加）")
                            .font(.headline)
                        ForEach(missedWords, id: \.id) { word in
                            missedWordRow(word)
                            Divider()
                        }
                    }
                    .padding()
                    .background(Color(.secondarySystemBackground))
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                }

                VStack(spacing: 10) {
                    if !missedWords.isEmpty {
                        Button("間違えた単語だけもう一度（\(missedWords.count)語）") {
                            startSession(pool: missedWords)
                        }
                        .buttonStyle(.borderedProminent)

                        Button("新しいセッションを始める（\(min(words.count, sessionSize))語）") {
                            startSession()
                        }
                        .buttonStyle(.bordered)
                    } else {
                        Button("もう一度") {
                            startSession()
                        }
                        .buttonStyle(.borderedProminent)
                    }

                    Button("終了") {
                        dismiss()
                    }
                    .buttonStyle(.bordered)
                    .tint(.secondary)
                }
            }
            .padding(.top, 24)
        }
        .onAppear(perform: requestNotificationPermissionIfNeeded)
    }

    private func missedWordRow(_ word: Word) -> some View {
        HStack(alignment: .firstTextBaseline) {
            VStack(alignment: .leading, spacing: 2) {
                Text(word.headword)
                    .fontWeight(.semibold)
                if !word.phonetic.isEmpty {
                    Text(word.phonetic)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            Spacer()
            Text(word.meaning)
                .foregroundStyle(.secondary)
            Button {
                SpeechService.shared.speak(word.headword)
            } label: {
                Image(systemName: "speaker.wave.2.fill")
            }
            .buttonStyle(.borderless)
        }
        .font(.subheadline)
    }

    /// 初回のクイズ完了時にだけ通知許可を求める。
    /// 起動直後に権限ダイアログを出すより、アプリの価値を体験した後の方が文脈が伝わる。
    private func requestNotificationPermissionIfNeeded() {
        let key = "didRequestNotificationAuth"
        guard !UserDefaults.standard.bool(forKey: key) else { return }
        UserDefaults.standard.set(true, forKey: key)
        NotificationService.requestAuthorization { granted in
            if granted {
                NotificationService.scheduleDailyReminder()
            }
        }
    }

    // MARK: - Session logic

    private func startSessionIfNeeded() {
        guard session.isEmpty else { return }
        startSession()
    }

    /// - Parameter pool: 出題する単語を明示的に指定する場合に使う（例: 間違えた単語だけの再挑戦）。
    ///   nil の場合は `words` から復習優先＋重み付きランダムでセッションを組み立てる。
    private func startSession(pool: [Word]? = nil) {
        advanceTask?.cancel()
        currentIndex = 0
        correctInSession = 0
        isAnswered = false
        missedWords = []

        if let pool {
            session = Array(pool.shuffled().prefix(sessionSize))
        } else {
            let reviewWords = words.filter(\.needsReview).shuffled()
            let remainingSlots = max(0, sessionSize - reviewWords.count)
            let candidates = words.filter { !$0.needsReview }
            let otherWords = weightedSample(candidates, count: remainingSlots, weight: reviewPriorityWeight)
            session = Array((reviewWords + otherWords).prefix(sessionSize))
        }
        prepareChoices()
    }

    /// 未学習の単語や間違いが多い単語ほど出やすくなる重み。
    /// 本格的なSRSではなく、復習優先度に軽く傾ける程度の簡易ロジック。
    private func reviewPriorityWeight(_ word: Word) -> Double {
        guard word.isLearned else { return 1.4 }
        return max(0.3, 1.0 + Double(word.incorrectCount) - Double(word.correctCount) * 0.25)
    }

    /// 重みに応じた復元抽出なしのランダムサンプリング（ルーレット選択）
    private func weightedSample(_ items: [Word], count: Int, weight: (Word) -> Double) -> [Word] {
        guard count > 0, !items.isEmpty else { return [] }
        var pool = items
        var weights = items.map { max(weight($0), 0.01) }
        var result: [Word] = []

        for _ in 0..<min(count, pool.count) {
            let total = weights.reduce(0, +)
            var r = Double.random(in: 0..<total)
            var pickedIndex = weights.count - 1
            for (i, w) in weights.enumerated() {
                if r < w {
                    pickedIndex = i
                    break
                }
                r -= w
            }
            result.append(pool.remove(at: pickedIndex))
            weights.remove(at: pickedIndex)
        }
        return result
    }

    private func prepareChoices() {
        guard currentIndex < session.count else { return }
        let correctWord = session[currentIndex]

        let others = allWords.filter { $0.id != correctWord.id }
        let wrongChoices = pickDistractors(for: correctWord, from: others, count: 3)

        choices = (wrongChoices + [correctWord]).shuffled()
        isAnswered = false
        selectedChoiceID = nil
        autoAdvancePaused = false

        // 回答時の触覚フィードバックの遅延を減らすため事前起動しておく
        FeedbackService.shared.prepare()

        if autoPronounceEnabled {
            SpeechService.shared.speak(correctWord.headword)
        }
    }

    /// 「惜しい」ハズレ選択肢を選ぶ。同品詞×同テーマ → 同品詞×同カテゴリ → 同品詞 → 残り
    /// の順で優先し、消去法で解けないようにする。各段階でシャッフルするので毎回並びも顔ぶれも変わる。
    /// テーマ/品詞が薄い場合でも段階的フォールバックで必ず count 件を確保する。
    private func pickDistractors(for correct: Word, from pool: [Word], count: Int) -> [Word] {
        let samePOS = pool.filter { !$0.partOfSpeech.isEmpty && $0.partOfSpeech == correct.partOfSpeech }
        let hasTheme = !correct.themeRaw.isEmpty

        // 同品詞・同テーマ（最も紛らわしい）
        let tier1 = hasTheme ? samePOS.filter { $0.themeRaw == correct.themeRaw } : []
        // 同品詞・同カテゴリ（テーマは違う）
        let tier2 = samePOS.filter { $0.themeRaw != correct.themeRaw && $0.category == correct.category }
        // 同品詞・その他
        let tier3 = samePOS.filter { $0.themeRaw != correct.themeRaw && $0.category != correct.category }
        // 品詞違い（最後の穴埋め）
        let tier4 = pool.filter { $0.partOfSpeech != correct.partOfSpeech }

        var result: [Word] = []
        var seen = Set<String>()
        for tier in [tier1, tier2, tier3, tier4] {
            for word in tier.shuffled() where result.count < count {
                if seen.insert(word.id).inserted {
                    result.append(word)
                }
            }
            if result.count >= count { break }
        }
        return result
    }

    private func select(_ choice: Word, correctWord: Word) {
        guard !isAnswered else { return }

        let isCorrect = choice.id == correctWord.id
        withAnimation(.snappy) {
            selectedChoiceID = choice.id
            isAnswered = true
            lastAnswerWasCorrect = isCorrect
        }

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
                goToNextAnimated()
            }
        }
    }

    private func pauseAutoAdvance() {
        advanceTask?.cancel()
        advanceTask = nil
        withAnimation(.snappy) {
            autoAdvancePaused = true
        }
    }

    private func goToNextAnimated() {
        withAnimation(.snappy) {
            goToNext()
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

/// セッション正答率を示すリング。表示時に0から実際の値までアニメーションする。
private struct AccuracyRing: View {
    let accuracy: Double

    @State private var animatedProgress: Double = 0

    private var ringColor: Color {
        if accuracy >= 0.8 { return .green }
        if accuracy >= 0.5 { return .orange }
        return .gray
    }

    var body: some View {
        ZStack {
            Circle()
                .stroke(Color(.systemGray5), lineWidth: 12)
            Circle()
                .trim(from: 0, to: animatedProgress)
                .stroke(ringColor, style: StrokeStyle(lineWidth: 12, lineCap: .round))
                .rotationEffect(.degrees(-90))
            VStack(spacing: 2) {
                Text("\(Int((accuracy * 100).rounded()))%")
                    .font(.title.bold())
                Text("正答率")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .frame(width: 132, height: 132)
        .onAppear {
            withAnimation(.easeOut(duration: 0.8)) {
                animatedProgress = accuracy
            }
        }
    }
}

#Preview {
    NavigationStack {
        QuizView(words: [], title: "プレビュー")
    }
}
