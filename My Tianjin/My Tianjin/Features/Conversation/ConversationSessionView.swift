import SwiftData
import SwiftUI

struct ConversationSessionView: View {
    @Environment(\.modelContext) private var modelContext
    @EnvironmentObject private var contentStore: LearningContentStore
    @EnvironmentObject private var speech: SpeechService

    @StateObject private var viewModel: ConversationViewModel
    @StateObject private var recognizer = ConversationSpeechRecognizer()

    @AppStorage("conversationShowsPinyin") private var showsPinyin = true
    @AppStorage("conversationShowsJapanese") private var showsJapanese = false
    @AppStorage("conversationAutoSpeak") private var autoSpeak = true
    @AppStorage("speechSpeedRawValue") private var speechSpeedRawValue = SpeechSpeed.normal.rawValue

    @State private var inputText = ""
    @State private var showsLatestHint = false
    @State private var speechError: String?
    @State private var didPersist = false
    @State private var savedReviewWordCount = 0
    @State private var persistenceError: String?

    init(configuration: ConversationConfiguration) {
        _viewModel = StateObject(
            wrappedValue: ConversationViewModel(configuration: configuration)
        )
    }

    private var speed: SpeechSpeed {
        SpeechSpeed(rawValue: speechSpeedRawValue) ?? .normal
    }

    var body: some View {
        Group {
            if viewModel.phase == .completed, let archive = viewModel.archive {
                ConversationSummaryView(
                    archive: archive,
                    savedReviewWordCount: savedReviewWordCount,
                    persistenceError: persistenceError
                )
            } else {
                sessionBody
            }
        }
        .navigationTitle(viewModel.configuration.scenario.title)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            if viewModel.phase != .completed {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("終了") {
                        recognizer.cancel()
                        Task { await viewModel.finish() }
                    }
                    .disabled(viewModel.phase == .reviewing)
                }
            }
        }
        .task {
            viewModel.start()
            if autoSpeak, let opening = viewModel.latestPartnerMessage {
                speech.speak(opening.chinese, speed: speed)
            }
        }
        .onChange(of: viewModel.phase) { _, phase in
            if phase == .completed {
                persistCompletedSession()
            }
        }
        .onDisappear {
            recognizer.cancel()
            speech.stop()
            viewModel.cancelTimer()
        }
    }

    private var sessionBody: some View {
        VStack(spacing: 0) {
            sessionHeader
            Divider()
            transcript

            if let providerNotice = viewModel.providerNotice {
                Label(providerNotice, systemImage: "arrow.triangle.2.circlepath")
                    .font(.caption)
                    .foregroundStyle(.orange)
                    .padding(.horizontal)
                    .padding(.top, 8)
            }

            if let errorMessage = viewModel.errorMessage {
                Label(errorMessage, systemImage: "exclamationmark.triangle.fill")
                    .font(.caption)
                    .foregroundStyle(.red)
                    .padding(.horizontal)
                    .padding(.top, 8)
            }

            if viewModel.phase == .reviewing {
                HStack(spacing: 10) {
                    ProgressView()
                    Text("会話を端末内で振り返っています…")
                        .font(.subheadline)
                }
                .padding()
            } else {
                composer
            }
        }
    }

    private var sessionHeader: some View {
        HStack(spacing: 10) {
            Label(viewModel.timeLabel, systemImage: "timer")
                .font(.subheadline.monospacedDigit().bold())
            Spacer()
            Text(viewModel.progressLabel)
                .font(.caption)
                .foregroundStyle(.secondary)
            Text(viewModel.provider.displayName)
                .font(.caption2.bold())
                .foregroundStyle(viewModel.provider == .appleOnDevice ? .indigo : .orange)
                .padding(.horizontal, 8)
                .padding(.vertical, 5)
                .background(
                    (viewModel.provider == .appleOnDevice ? Color.indigo : Color.orange).opacity(0.1),
                    in: Capsule()
                )
        }
        .padding(.horizontal)
        .padding(.vertical, 9)
    }

    private var transcript: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(spacing: 14) {
                    ForEach(viewModel.messages) { message in
                        messageBubble(message)
                            .id(message.id)
                    }

                    if viewModel.phase == .waitingForPartner {
                        HStack(spacing: 9) {
                            ProgressView()
                            Text("返答を考えています…")
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                            Spacer()
                        }
                        .padding(.horizontal)
                    }
                }
                .padding(.vertical, 14)
            }
            .onChange(of: viewModel.messages.count) { _, _ in
                guard let lastID = viewModel.messages.last?.id else { return }
                withAnimation { proxy.scrollTo(lastID, anchor: .bottom) }
            }
        }
    }

    private func messageBubble(_ message: ConversationMessage) -> some View {
        let isLearner = message.role == .learner
        let isLatestPartner = message.id == viewModel.latestPartnerMessage?.id

        return HStack(alignment: .bottom) {
            if isLearner { Spacer(minLength: 42) }
            VStack(alignment: .leading, spacing: 7) {
                HStack(alignment: .firstTextBaseline) {
                    Text(isLearner ? "あなた" : "会話相手")
                        .font(.caption2.bold())
                        .foregroundStyle(.secondary)
                    if !isLearner {
                        Spacer()
                        Button {
                            speech.speak(message.chinese, speed: speed)
                        } label: {
                            Image(systemName: "speaker.wave.2.fill")
                        }
                        .buttonStyle(.plain)
                        .accessibilityLabel("この返答を再生")
                    }
                }

                Text(message.chinese)
                    .font(.body.weight(.medium))
                    .textSelection(.enabled)

                if !isLearner, showsPinyin, let pinyin = message.pinyin {
                    Text(pinyin)
                        .font(.subheadline)
                        .foregroundStyle(.indigo)
                        .textSelection(.enabled)
                }

                if !isLearner, showsJapanese, let japanese = message.japanese {
                    Text(japanese)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }

                if isLatestPartner, !message.suggestedReplies.isEmpty {
                    Divider()
                    Text("返答候補")
                        .font(.caption.bold())
                        .foregroundStyle(.secondary)
                    ConversationFlowLayout(spacing: 7) {
                        ForEach(message.suggestedReplies, id: \.self) { suggestion in
                            Button(suggestion) {
                                inputText = suggestion
                            }
                            .buttonStyle(.bordered)
                            .controlSize(.small)
                        }
                    }

                    if let hint = message.hintJapanese {
                        Button {
                            showsLatestHint.toggle()
                        } label: {
                            Label(showsLatestHint ? "ヒントを隠す" : "ヒントを見る", systemImage: "lightbulb")
                                .font(.caption)
                        }
                        .buttonStyle(.plain)
                        .foregroundStyle(.orange)
                        if showsLatestHint {
                            Text(hint)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
            }
            .padding(12)
            .frame(maxWidth: 520, alignment: .leading)
            .background(
                isLearner ? Color.blue.opacity(0.13) : Color.secondary.opacity(0.08),
                in: RoundedRectangle(cornerRadius: 16)
            )
            if !isLearner { Spacer(minLength: 42) }
        }
        .padding(.horizontal)
    }

    private var composer: some View {
        VStack(spacing: 9) {
            if !recognizer.statusText.isEmpty {
                Text(recognizer.statusText)
                    .font(.caption)
                    .foregroundStyle(recognizer.isRecording ? .red : .secondary)
            }
            if let speechError {
                Text(speechError)
                    .font(.caption)
                    .foregroundStyle(.red)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }

            HStack(alignment: .bottom, spacing: 9) {
                Button {
                    toggleRecording()
                } label: {
                    Image(systemName: recognizer.isRecording ? "stop.fill" : "mic.fill")
                        .font(.title3)
                        .foregroundStyle(.white)
                        .frame(width: 44, height: 44)
                        .background(recognizer.isRecording ? .red : .indigo, in: Circle())
                }
                .disabled(!viewModel.canSend || recognizer.isTranscribing)
                .accessibilityLabel(recognizer.isRecording ? "録音を停止して送信" : "録音を開始")

                TextField("中国語で入力", text: $inputText, axis: .vertical)
                    .lineLimit(1...4)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .padding(.horizontal, 12)
                    .padding(.vertical, 10)
                    .background(.secondary.opacity(0.08), in: RoundedRectangle(cornerRadius: 13))
                    .disabled(!viewModel.canSend || recognizer.isRecording || recognizer.isTranscribing)
                    .onSubmit { sendTypedText() }

                Button {
                    sendTypedText()
                } label: {
                    Image(systemName: "arrow.up.circle.fill")
                        .font(.system(size: 38))
                }
                .disabled(
                    inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                        || !viewModel.canSend
                        || recognizer.isRecording
                        || recognizer.isTranscribing
                )
                .accessibilityLabel("送信")
            }

            HStack {
                Label("マイクは2回押して送信", systemImage: "hand.tap")
                Spacer()
                Button(speed.label) {
                    let next = speed.next
                    speechSpeedRawValue = next.rawValue
                }
            }
            .font(.caption)
            .foregroundStyle(.secondary)
        }
        .padding(.horizontal)
        .padding(.top, 10)
        .padding(.bottom, 8)
        .background(.bar)
    }

    private func sendTypedText() {
        let text = inputText
        inputText = ""
        showsLatestHint = false
        speechError = nil
        Task {
            if let reply = await viewModel.send(text), autoSpeak {
                speech.speak(reply.chinese, speed: speed)
            }
        }
    }

    private func toggleRecording() {
        speechError = nil
        Task {
            do {
                if recognizer.isRecording {
                    let recognizedText = try await recognizer.stopRecordingAndTranscribe()
                    inputText = recognizedText
                    sendTypedText()
                } else {
                    speech.stop()
                    try await recognizer.startRecording()
                }
            } catch {
                recognizer.cancel()
                speechError = error.localizedDescription
            }
        }
    }

    private func persistCompletedSession() {
        guard !didPersist, let archive = viewModel.archive else { return }
        didPersist = true
        do {
            try ConversationPersistence.save(archive, in: modelContext)
            let vocabulary = contentStore.vocabulary(
                for: archive.configuration.level,
                cumulative: true
            )
            savedReviewWordCount = try ConversationPersistence.markReviewWords(
                archive.feedback.reviewWords,
                vocabulary: vocabulary,
                in: modelContext
            )
        } catch {
            persistenceError = "履歴または復習語の保存に失敗しました。\(error.localizedDescription)"
        }
    }
}
