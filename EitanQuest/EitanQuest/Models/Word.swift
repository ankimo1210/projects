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
    /// 発音記号（IPA、第一アクセント記号付き）。旧データからの軽量マイグレーションのため既定値あり
    var phonetic: String = ""
    /// 例文の日本語訳。旧データからの軽量マイグレーションのため既定値あり
    var exampleSentenceJa: String = ""
    /// 品詞（noun / verb / adjective）。同品詞の「惜しい」ハズレ選択肢を選ぶのに使う
    var partOfSpeech: String = ""
    /// 意味テーマ（emotion / money / …）。同テーマの引っ掛け選択肢とテーマ別出題に使う
    var themeRaw: String = ""

    // MARK: - 学習進捗
    var correctCount: Int
    var incorrectCount: Int
    /// 直近で不正解になり、優先的に再出題すべき単語かどうか
    var needsReview: Bool
    var lastAnsweredAt: Date?

    var category: WordCategory {
        WordCategory(rawValue: categoryRaw) ?? .daily
    }

    var theme: WordTheme? {
        WordTheme(rawValue: themeRaw)
    }

    var isLearned: Bool {
        correctCount + incorrectCount > 0
    }

    init(
        id: String,
        headword: String,
        meaning: String,
        category: WordCategory,
        exampleSentence: String,
        phonetic: String = "",
        exampleSentenceJa: String = "",
        partOfSpeech: String = "",
        themeRaw: String = ""
    ) {
        self.id = id
        self.headword = headword
        self.meaning = meaning
        self.categoryRaw = category.rawValue
        self.exampleSentence = exampleSentence
        self.phonetic = phonetic
        self.exampleSentenceJa = exampleSentenceJa
        self.partOfSpeech = partOfSpeech
        self.themeRaw = themeRaw
        self.correctCount = 0
        self.incorrectCount = 0
        self.needsReview = false
        self.lastAnsweredAt = nil
    }
}
