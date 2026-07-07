import Foundation
import SwiftData

/// words.json をデコードするためのDTO
private struct WordSeed: Codable {
    let id: String
    let headword: String
    let meaning: String
    let category: String
    let exampleSentence: String
}

enum DataSeeder {
    /// アプリの初回起動時など、まだ単語が1件も無い場合にのみ words.json から投入する
    static func seedIfNeeded(context: ModelContext) {
        let descriptor = FetchDescriptor<Word>()
        let existingCount = (try? context.fetchCount(descriptor)) ?? 0
        guard existingCount == 0 else { return }

        guard let url = Bundle.main.url(forResource: "words", withExtension: "json") else {
            assertionFailure("words.json がアプリバンドルに見つかりません。Build Phases > Copy Bundle Resources を確認してください。")
            return
        }

        do {
            let data = try Data(contentsOf: url)
            let seeds = try JSONDecoder().decode([WordSeed].self, from: data)

            for seed in seeds {
                let category = WordCategory(rawValue: seed.category) ?? .daily
                let word = Word(
                    id: seed.id,
                    headword: seed.headword,
                    meaning: seed.meaning,
                    category: category,
                    exampleSentence: seed.exampleSentence
                )
                context.insert(word)
            }
            try context.save()
        } catch {
            assertionFailure("単語データの読み込みに失敗しました: \(error)")
        }
    }
}
