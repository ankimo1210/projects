import Foundation
import SwiftData

/// words.json をデコードするためのDTO
private struct WordSeed: Codable {
    let id: String
    let headword: String
    let meaning: String
    let category: String
    let exampleSentence: String
    let phonetic: String
    let exampleSentenceJa: String
    let partOfSpeech: String
    let theme: String
}

enum DataSeeder {
    /// words.json の内容バージョン。単語データを更新したらインクリメントすると、
    /// 既存ユーザーのDBにも次回起動時に反映される（学習進捗は保持）。
    static let seedDataVersion = 4
    private static let versionKey = "seedDataVersion"

    /// DBが空なら全件投入、バージョンが古ければ単語コンテンツのみ更新する
    static func seedIfNeeded(context: ModelContext) {
        let descriptor = FetchDescriptor<Word>()
        let existingCount = (try? context.fetchCount(descriptor)) ?? 0
        let storedVersion = UserDefaults.standard.integer(forKey: versionKey)
        guard existingCount == 0 || storedVersion < seedDataVersion else { return }

        guard let url = Bundle.main.url(forResource: "words", withExtension: "json") else {
            assertionFailure("words.json がアプリバンドルに見つかりません。Build Phases > Copy Bundle Resources を確認してください。")
            return
        }

        do {
            let data = try Data(contentsOf: url)
            let seeds = try JSONDecoder().decode([WordSeed].self, from: data)
            let existingWords = (try? context.fetch(descriptor)) ?? []
            let wordsByID = Dictionary(uniqueKeysWithValues: existingWords.map { ($0.id, $0) })

            for seed in seeds {
                let category = WordCategory(rawValue: seed.category) ?? .daily
                if let word = wordsByID[seed.id] {
                    // 既存レコードは単語コンテンツのみ更新（correctCount等の進捗は保持）
                    word.headword = seed.headword
                    word.meaning = seed.meaning
                    word.categoryRaw = category.rawValue
                    word.exampleSentence = seed.exampleSentence
                    word.phonetic = seed.phonetic
                    word.exampleSentenceJa = seed.exampleSentenceJa
                    word.partOfSpeech = seed.partOfSpeech
                    word.themeRaw = seed.theme
                } else {
                    let word = Word(
                        id: seed.id,
                        headword: seed.headword,
                        meaning: seed.meaning,
                        category: category,
                        exampleSentence: seed.exampleSentence,
                        phonetic: seed.phonetic,
                        exampleSentenceJa: seed.exampleSentenceJa,
                        partOfSpeech: seed.partOfSpeech,
                        themeRaw: seed.theme
                    )
                    context.insert(word)
                }
            }
            try context.save()
            UserDefaults.standard.set(seedDataVersion, forKey: versionKey)
        } catch {
            assertionFailure("単語データの読み込みに失敗しました: \(error)")
        }
    }
}
