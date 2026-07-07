import Foundation
import AVFoundation

/// 英単語の発音をオフラインで読み上げるサービス。
///
/// 注: あえて AVAudioSession のカテゴリ設定は行っていません。
/// これにより本体のマナースイッチ（消音モード）が尊重され、消音時は読み上げ音も鳴りません（仕様）。
/// 消音時でも鳴らしたくなった場合は、ここで AVAudioSession を .playback に設定してください。
final class SpeechService {
    static let shared = SpeechService()

    private let synthesizer = AVSpeechSynthesizer()

    private init() {}

    func speak(_ text: String) {
        synthesizer.stopSpeaking(at: .immediate)

        let utterance = AVSpeechUtterance(string: text)
        utterance.voice = AVSpeechSynthesisVoice(language: "en-US")
        utterance.rate = AVSpeechUtteranceDefaultSpeechRate * 0.9
        synthesizer.speak(utterance)
    }
}
