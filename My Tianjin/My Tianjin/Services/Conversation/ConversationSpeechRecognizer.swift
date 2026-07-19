import AVFoundation
import Combine
import Foundation
import Speech

nonisolated enum ConversationRecordingState: Equatable, Sendable {
    case idle
    case recording
    case transcribing
}

@MainActor
final class ConversationSpeechRecognizer: ObservableObject {
    @Published private(set) var state = ConversationRecordingState.idle
    @Published private(set) var statusText = ""

    private var recorder: AVAudioRecorder?
    private var recordingURL: URL?

    init() {
        removeStaleRecordings()
    }

    var isRecording: Bool { state == .recording }
    var isTranscribing: Bool { state == .transcribing }

    func startRecording() async throws {
        guard state == .idle else { return }
        guard await requestMicrophonePermission() else {
            throw ConversationClientError.permissionDenied(
                "マイクへのアクセスが必要です。設定アプリでMy Tianjinのマイクを許可してください。"
            )
        }
        guard await requestSpeechPermission() else {
            throw ConversationClientError.permissionDenied(
                "音声認識へのアクセスが必要です。設定アプリでMy Tianjinの音声認識を許可してください。"
            )
        }
        guard SpeechTranscriber.isAvailable else {
            throw ConversationClientError.speechUnavailable(
                "この端末ではAppleの端末内音声認識を利用できません。文字入力をお使いください。"
            )
        }
        guard await SpeechTranscriber.supportedLocale(
            equivalentTo: Locale(identifier: "zh-Hans-CN")
        ) != nil else {
            throw ConversationClientError.speechUnavailable(
                "この端末では中国語の端末内音声認識を利用できません。文字入力をお使いください。"
            )
        }

        let session = AVAudioSession.sharedInstance()
        try session.setCategory(.playAndRecord, mode: .measurement, options: [.duckOthers])
        try session.setActive(true)

        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("my-tianjin-conversation-\(UUID().uuidString).m4a")
        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
            AVSampleRateKey: 44_100,
            AVNumberOfChannelsKey: 1,
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue
        ]
        let recorder: AVAudioRecorder
        do {
            recorder = try AVAudioRecorder(url: url, settings: settings)
            recorder.prepareToRecord()
        } catch {
            try? FileManager.default.removeItem(at: url)
            try? session.setActive(false, options: .notifyOthersOnDeactivation)
            throw error
        }
        guard recorder.record() else {
            try? FileManager.default.removeItem(at: url)
            try? session.setActive(false, options: .notifyOthersOnDeactivation)
            throw ConversationClientError.speechUnavailable("録音を開始できませんでした。")
        }

        self.recorder = recorder
        recordingURL = url
        statusText = "録音中…もう一度押すと送信"
        state = .recording
    }

    func stopRecordingAndTranscribe() async throws -> String {
        guard state == .recording, let recordingURL else {
            throw ConversationClientError.noSpeechDetected
        }

        recorder?.stop()
        recorder = nil
        state = .transcribing
        statusText = "端末内で文字にしています…"
        try? AVAudioSession.sharedInstance().setActive(
            false,
            options: .notifyOthersOnDeactivation
        )

        defer {
            try? FileManager.default.removeItem(at: recordingURL)
            self.recordingURL = nil
            state = .idle
            statusText = ""
        }

        let text = try await transcribe(recordingURL)
            .trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { throw ConversationClientError.noSpeechDetected }
        return text
    }

    func cancel() {
        recorder?.stop()
        recorder = nil
        if let recordingURL {
            try? FileManager.default.removeItem(at: recordingURL)
        }
        recordingURL = nil
        state = .idle
        statusText = ""
        try? AVAudioSession.sharedInstance().setActive(
            false,
            options: .notifyOthersOnDeactivation
        )
    }

    private func transcribe(_ url: URL) async throws -> String {
        guard let locale = await SpeechTranscriber.supportedLocale(
            equivalentTo: Locale(identifier: "zh-Hans-CN")
        ) else {
            throw ConversationClientError.speechUnavailable(
                "中国語の端末内音声認識を利用できません。"
            )
        }

        let transcriber = SpeechTranscriber(locale: locale, preset: .transcription)
        let modules: [any SpeechModule] = [transcriber]
        try await prepareAssets(for: modules, locale: locale)

        let audioFile = try AVAudioFile(forReading: url)
        let analyzer = SpeechAnalyzer(modules: modules)
        let resultsTask = Task<String, Error> {
            var finalizedParts: [String] = []
            var latestText = ""
            for try await result in transcriber.results {
                let text = String(result.text.characters)
                    .trimmingCharacters(in: .whitespacesAndNewlines)
                guard !text.isEmpty else { continue }
                latestText = text
                if result.isFinal {
                    finalizedParts.append(text)
                }
            }
            return finalizedParts.isEmpty ? latestText : finalizedParts.joined()
        }

        do {
            try await analyzer.start(inputAudioFile: audioFile, finishAfterFile: true)
            return try await resultsTask.value
        } catch {
            resultsTask.cancel()
            await analyzer.cancelAndFinishNow()
            throw error
        }
    }

    private func prepareAssets(
        for modules: [any SpeechModule],
        locale: Locale
    ) async throws {
        _ = try? await AssetInventory.reserve(locale: locale)
        switch await AssetInventory.status(forModules: modules) {
        case .installed:
            return
        case .unsupported:
            throw ConversationClientError.speechUnavailable(
                "中国語の音声認識モデルはこの端末に対応していません。"
            )
        case .supported, .downloading:
            statusText = "中国語の音声認識モデルを準備しています…"
            if let request = try await AssetInventory.assetInstallationRequest(supporting: modules) {
                try await request.downloadAndInstall()
            }
            guard await AssetInventory.status(forModules: modules) == .installed else {
                throw ConversationClientError.speechUnavailable(
                    "音声認識モデルを準備中です。しばらくしてから再度お試しください。"
                )
            }
        @unknown default:
            throw ConversationClientError.speechUnavailable(
                "音声認識モデルの状態を確認できませんでした。"
            )
        }
    }

    private func requestMicrophonePermission() async -> Bool {
        switch AVAudioApplication.shared.recordPermission {
        case .granted:
            true
        case .denied:
            false
        case .undetermined:
            await withCheckedContinuation { continuation in
                AVAudioApplication.requestRecordPermission { granted in
                    continuation.resume(returning: granted)
                }
            }
        @unknown default:
            false
        }
    }

    private func requestSpeechPermission() async -> Bool {
        switch SFSpeechRecognizer.authorizationStatus() {
        case .authorized:
            true
        case .denied, .restricted:
            false
        case .notDetermined:
            await withCheckedContinuation { continuation in
                SFSpeechRecognizer.requestAuthorization { status in
                    continuation.resume(returning: status == .authorized)
                }
            }
        @unknown default:
            false
        }
    }

    private func removeStaleRecordings() {
        let temporaryDirectory = FileManager.default.temporaryDirectory
        guard let urls = try? FileManager.default.contentsOfDirectory(
            at: temporaryDirectory,
            includingPropertiesForKeys: nil
        ) else { return }
        for url in urls where url.lastPathComponent.hasPrefix("my-tianjin-conversation-") {
            try? FileManager.default.removeItem(at: url)
        }
    }
}
