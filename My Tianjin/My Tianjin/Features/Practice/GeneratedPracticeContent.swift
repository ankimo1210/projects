import Foundation

enum GeneratedPracticeContent {
    static func clozeQuestions(
        vocabulary: [VocabularyItem],
        limit: Int = 30
    ) -> [PracticeQuestion] {
        vocabulary
            .filter { item in
                item.examples.first.map { $0.hanzi.contains(item.hanzi) } == true
            }
            .prefix(limit)
            .enumerated()
            .map { offset, item in
                let example = item.examples[0]
                let options = choiceOptions(
                    for: item,
                    in: vocabulary,
                    seed: UInt64(offset + 101),
                    uniqueBy: .hanzi
                )
                let sentence = example.hanzi.replacingOccurrences(of: item.hanzi, with: "{{blank}}")
                return PracticeQuestion(
                    id: "generated-cloze-\(item.id)",
                    content: .sentenceCloze(PracticeClozeQuestion(
                        prompt: PracticePrompt(instruction: "文に入る最も自然な語を選んでください。"),
                        sentence: PracticeText(
                            text: sentence,
                            japanese: example.japanese,
                            speechText: example.hanzi
                        ),
                        answers: PracticeChoiceSet(
                            options: options,
                            correctOptionIDs: [item.id]
                        )
                    )),
                    metadata: PracticeQuestionMetadata(
                        level: .level1,
                        skills: [.vocabulary, .grammar],
                        tags: ["generated", "cloze"]
                    ),
                    explanation: PracticeAnswerExplanation(
                        summary: "正解：\(item.hanzi)（\(item.pinyin)）\(item.primaryJapanese)"
                    )
                )
            }
    }

    static func audioQuestions(
        vocabulary: [VocabularyItem],
        limit: Int = 30
    ) -> [PracticeQuestion] {
        vocabulary.prefix(limit).enumerated().map { offset, item in
            let options = choiceOptions(
                for: item,
                in: vocabulary,
                seed: UInt64(offset + 701),
                uniqueBy: .japanese
            )
                .map { option in
                    PracticeAnswerOption(
                        id: option.id,
                        content: PracticeText(
                            text: option.content.japanese ?? option.content.text,
                            pinyin: option.content.pinyin,
                            japanese: option.content.text
                        )
                    )
                }
            return PracticeQuestion(
                id: "generated-audio-\(item.id)",
                content: .audioToMeaning(PracticeAudioChoiceQuestion(
                    audio: PracticeText(text: item.hanzi, pinyin: item.pinyin, speechText: item.hanzi),
                    prompt: PracticePrompt(instruction: "音声を聞いて意味を選んでください。"),
                    answers: PracticeChoiceSet(options: options, correctOptionIDs: [item.id])
                )),
                metadata: PracticeQuestionMetadata(
                    level: .level1,
                    skills: [.listening, .vocabulary],
                    tags: ["generated", "audio"]
                ),
                explanation: PracticeAnswerExplanation(
                    summary: "\(item.hanzi)（\(item.pinyin)）：\(item.primaryJapanese)"
                )
            )
        }
    }

    private static func choiceOptions(
        for item: VocabularyItem,
        in vocabulary: [VocabularyItem],
        seed: UInt64,
        uniqueBy displayKey: ChoiceDisplayKey
    ) -> [PracticeAnswerOption] {
        let samePartOfSpeech = vocabulary.filter {
            $0.id != item.id && $0.partOfSpeech == item.partOfSpeech
        }
        let fallback = vocabulary.filter { $0.id != item.id }
        let orderedCandidates = DeterministicShuffle.shuffled(samePartOfSpeech, seed: seed)
            + DeterministicShuffle.shuffled(fallback, seed: seed ^ 0xD15A_C70A)
        var seenIDs = Set([item.id])
        var seenLabels = Set([displayKey.value(for: item)])
        var distractors: [VocabularyItem] = []
        for candidate in orderedCandidates where distractors.count < 3 {
            guard seenIDs.insert(candidate.id).inserted,
                  seenLabels.insert(displayKey.value(for: candidate)).inserted else { continue }
            distractors.append(candidate)
        }
        let selected = [item] + distractors
        return DeterministicShuffle.shuffled(selected, seed: seed ^ 0xA11C_E55).map {
            PracticeAnswerOption(
                id: $0.id,
                content: PracticeText(
                    text: $0.hanzi,
                    pinyin: $0.pinyin,
                    japanese: $0.primaryJapanese,
                    speechText: $0.hanzi
                )
            )
        }
    }

    private enum ChoiceDisplayKey {
        case hanzi
        case japanese

        func value(for item: VocabularyItem) -> String {
            switch self {
            case .hanzi: item.hanzi
            case .japanese: item.primaryJapanese
            }
        }
    }
}
