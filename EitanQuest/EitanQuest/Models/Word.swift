import Foundation
import SwiftData

/// 学習対象の英単語1件を表すSwiftDataモデル
@Model
final class Word {
    @Attribute(.unique) var id: String
    var headword: String
    var meaning: String
    var categoryRaw: String
    var exampleSentence: String

    // MARK: - 学習進捗
    var correctCount: Int
    var incorrectCount: Int
    /// 直近で不正解になり、優先的に再出題すべき単語かどうか
    var needsReview: Bool
    var lastAnsweredAt: Date?

    var category: WordCategory {
        WordCategory(rawValue: categoryRaw) ?? .daily
    }

    var isLearned: Bool {
        correctCount + incorrectCount > 0
    }

    init(
        id: String,
        headword: String,
        meaning: String,
        category: WordCategory,
        exampleSentence: String
    ) {
        self.id = id
        self.headword = headword
        self.meaning = meaning
        self.categoryRaw = category.rawValue
        self.exampleSentence = exampleSentence
        self.correctCount = 0
        self.incorrectCount = 0
        self.needsReview = false
        self.lastAnsweredAt = nil
    }
}
