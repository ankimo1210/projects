import Foundation

struct PracticeProgressDescriptor: Hashable {
    let itemID: String
    let skill: LearningSkill
}

enum PracticeProgressMapping {
    static func descriptors(for question: PracticeQuestion) -> [PracticeProgressDescriptor] {
        let declaredSkills = question.metadata.skills.isEmpty
            ? [fallbackSkill(for: question)]
            : question.metadata.skills
        var seen = Set<PracticeProgressDescriptor>()
        return declaredSkills.compactMap { practiceSkill in
            let skill = learningSkill(for: practiceSkill)
            let descriptor = PracticeProgressDescriptor(
                itemID: itemID(for: question, skill: skill),
                skill: skill
            )
            return seen.insert(descriptor).inserted ? descriptor : nil
        }
    }

    private static func itemID(
        for question: PracticeQuestion,
        skill: LearningSkill
    ) -> String {
        guard skill == .vocabulary else { return question.id }
        switch question.content {
        case let .vocabularyMultipleChoice(payload):
            return payload.vocabularyID
        case let .audioToMeaning(payload):
            return payload.answers.correctOptionIDs.first ?? question.id
        case let .sentenceCloze(payload):
            return payload.answers.correctOptionIDs.first ?? question.id
        default:
            return question.id
        }
    }

    private static func learningSkill(for skill: PracticeSkill) -> LearningSkill {
        switch skill {
        case .vocabulary: .vocabulary
        case .listening: .listening
        case .reading: .reading
        case .grammar, .wordOrder: .grammar
        case .writing, .characterWriting: .writing
        case .translation: .translation
        case .speaking: .speaking
        case .pronunciation: .pronunciation
        }
    }

    private static func fallbackSkill(for question: PracticeQuestion) -> PracticeSkill {
        switch question.content {
        case .vocabularyMultipleChoice: .vocabulary
        case .audioToMeaning: .listening
        case .sentenceCloze, .sentenceOrdering, .incorrectSentence: .grammar
        case .readingComprehension: .reading
        case .summary, .essay: .writing
        case .translation: .translation
        case .oralOpinion: .speaking
        }
    }
}
