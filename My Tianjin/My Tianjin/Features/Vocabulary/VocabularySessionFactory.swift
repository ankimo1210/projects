import Foundation

enum VocabularySessionFactory {
    static func studyItems(from vocabulary: [VocabularyItem]) -> [StudySessionItem] {
        guard vocabulary.count >= 4 else { return [] }

        let allIDs = vocabulary.map(\.id)
        let meaningByID = Dictionary(
            uniqueKeysWithValues: vocabulary.map { ($0.id, $0.primaryJapanese) }
        )
        let groupedItems = Dictionary(grouping: vocabulary) { item in
            guard let partOfSpeech = item.partOfSpeech, !partOfSpeech.isEmpty else {
                return "未分類"
            }
            return partOfSpeech
        }
        let groupIDsByKey = groupedItems.mapValues { items in
            uniqueMeaningIDs(in: items.sorted { $0.officialIndex < $1.officialIndex })
        }
        let globalUniqueIDs = uniqueMeaningIDs(in: vocabulary)

        return vocabulary.map { item in
            var distractors: [String] = []
            var seenMeanings = Set([item.primaryJapanese])

            appendCandidates(
                from: groupIDsByKey[groupKey(item)] ?? allIDs,
                startingAt: item.officialIndex,
                excluding: item.id,
                meaningByID: meaningByID,
                seenMeanings: &seenMeanings,
                result: &distractors
            )
            if distractors.count < 8 {
                appendCandidates(
                    from: globalUniqueIDs,
                    startingAt: item.officialIndex,
                    excluding: item.id,
                    meaningByID: meaningByID,
                    seenMeanings: &seenMeanings,
                    result: &distractors
                )
            }

            return StudySessionItem(
                id: item.id,
                correctOptionID: item.id,
                distractorOptionIDs: distractors
            )
        }
    }

    private static func groupKey(_ item: VocabularyItem) -> String {
        guard let partOfSpeech = item.partOfSpeech, !partOfSpeech.isEmpty else {
            return "未分類"
        }
        return partOfSpeech
    }

    private static func uniqueMeaningIDs(in items: [VocabularyItem]) -> [String] {
        var meanings = Set<String>()
        return items.compactMap { item in
            meanings.insert(item.primaryJapanese).inserted ? item.id : nil
        }
    }

    private static func appendCandidates(
        from candidateIDs: [String],
        startingAt seed: Int,
        excluding itemID: String,
        meaningByID: [String: String],
        seenMeanings: inout Set<String>,
        result: inout [String]
    ) {
        guard !candidateIDs.isEmpty, result.count < 8 else { return }
        let start = abs(seed) % candidateIDs.count
        for offset in 0..<candidateIDs.count where result.count < 8 {
            let candidateID = candidateIDs[(start + offset) % candidateIDs.count]
            guard candidateID != itemID,
                  !result.contains(candidateID),
                  let meaning = meaningByID[candidateID],
                  seenMeanings.insert(meaning).inserted else { continue }
            result.append(candidateID)
        }
    }
}
