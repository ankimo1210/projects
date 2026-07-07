import Foundation
import AVFoundation
import UIKit

/// クイズ回答時のフィードバック（効果音＋触覚）をまとめて扱うサービス。
///
/// 注: SpeechService と同様、あえて AVAudioSession のカテゴリ設定は行いません。
/// 既定の ambient セッションで再生するため、本体のマナースイッチ（消音モード）が
/// 尊重され、消音時は効果音が鳴りません（仕様）。触覚フィードバックは消音時でも働きます。
final class FeedbackService {
    static let shared = FeedbackService()

    private let correctPlayer: AVAudioPlayer?
    private let incorrectPlayer: AVAudioPlayer?
    private let notification = UINotificationFeedbackGenerator()

    private init() {
        correctPlayer = Self.makePlayer(named: "correct")
        incorrectPlayer = Self.makePlayer(named: "incorrect")
    }

    private static func makePlayer(named name: String) -> AVAudioPlayer? {
        guard let url = Bundle.main.url(forResource: name, withExtension: "wav") else {
            return nil
        }
        let player = try? AVAudioPlayer(contentsOf: url)
        player?.prepareToPlay()
        return player
    }

    func correct() {
        notification.notificationOccurred(.success)
        correctPlayer?.currentTime = 0
        correctPlayer?.play()
    }

    func incorrect() {
        notification.notificationOccurred(.error)
        incorrectPlayer?.currentTime = 0
        incorrectPlayer?.play()
    }
}
