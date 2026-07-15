import AVFoundation
import Combine
import Foundation

enum SpeechSpeed: Int, CaseIterable, Identifiable {
    case slow
    case normal
    case fast

    var id: Int { rawValue }

    var label: String {
        switch self {
        case .slow: "0.8×"
        case .normal: "1.0×"
        case .fast: "1.2×"
        }
    }

    var utteranceRate: Float {
        switch self {
        case .slow: 0.39
        case .normal: 0.47
        case .fast: 0.55
        }
    }

    var next: SpeechSpeed {
        let values = Self.allCases
        return values[(rawValue + 1) % values.count]
    }
}

enum SpeechLanguage {
    case mandarin
    case japanese

    var languageCode: String {
        switch self {
        case .mandarin: "zh-CN"
        case .japanese: "ja-JP"
        }
    }
}

@MainActor
final class SpeechService: NSObject, ObservableObject {
    private let synthesizer = AVSpeechSynthesizer()

    @Published private(set) var isSpeaking = false

    override init() {
        super.init()
        synthesizer.delegate = self
    }

    var voiceDescription: String {
        guard let voice = Self.preferredVoice(for: .mandarin) else {
            return "中国語（標準音声）"
        }
        switch voice.quality {
        case .premium: return "中国語（プレミアム音声）"
        case .enhanced: return "中国語（拡張音声）"
        default: return "中国語（標準音声）"
        }
    }

    func speak(
        _ text: String,
        language: SpeechLanguage = .mandarin,
        speed: SpeechSpeed
    ) {
        let cleanText = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !cleanText.isEmpty else { return }

        if synthesizer.isSpeaking {
            synthesizer.stopSpeaking(at: .immediate)
        }

        let utterance = AVSpeechUtterance(string: cleanText)
        utterance.voice = Self.preferredVoice(for: language)
            ?? AVSpeechSynthesisVoice(language: language.languageCode)
        utterance.rate = speed.utteranceRate
        utterance.pitchMultiplier = 1
        utterance.preUtteranceDelay = 0.04
        utterance.postUtteranceDelay = 0.03

        try? AVAudioSession.sharedInstance().setCategory(
            .playback,
            mode: .spokenAudio,
            options: [.duckOthers]
        )
        try? AVAudioSession.sharedInstance().setActive(true)
        synthesizer.speak(utterance)
    }

    func stop() {
        if synthesizer.isSpeaking {
            synthesizer.stopSpeaking(at: .immediate)
        } else {
            deactivateAudioSession()
        }
    }

    private static func preferredVoice(for language: SpeechLanguage) -> AVSpeechSynthesisVoice? {
        AVSpeechSynthesisVoice.speechVoices()
            .filter { $0.language == language.languageCode }
            .sorted { $0.quality.rawValue > $1.quality.rawValue }
            .first
    }

    private func deactivateAudioSession() {
        try? AVAudioSession.sharedInstance().setActive(
            false,
            options: .notifyOthersOnDeactivation
        )
    }
}

extension SpeechService: AVSpeechSynthesizerDelegate {
    nonisolated func speechSynthesizer(
        _ synthesizer: AVSpeechSynthesizer,
        didStart utterance: AVSpeechUtterance
    ) {
        Task { @MainActor in isSpeaking = true }
    }

    nonisolated func speechSynthesizer(
        _ synthesizer: AVSpeechSynthesizer,
        didFinish utterance: AVSpeechUtterance
    ) {
        Task { @MainActor in
            isSpeaking = self.synthesizer.isSpeaking
            if !isSpeaking { self.deactivateAudioSession() }
        }
    }

    nonisolated func speechSynthesizer(
        _ synthesizer: AVSpeechSynthesizer,
        didCancel utterance: AVSpeechUtterance
    ) {
        Task { @MainActor in
            isSpeaking = self.synthesizer.isSpeaking
            if !isSpeaking { self.deactivateAudioSession() }
        }
    }
}
