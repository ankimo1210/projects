import Foundation

struct TheoryExamCandidate: Hashable {
    let id: String
    let learningOutcome: String
    let studyMode: String
}

struct TheoryExamBlueprint: Equatable {
    let multipleChoiceQuestionIDs: [String]
    let writtenQuestionIDs: [String]
    let durationMinutes: Int
}

enum TheoryExamSubmissionTrigger: Equatable {
    case manual
    case timerTick
    case resume
}

struct TheoryExamLifecycleTransition: Equatable {
    let fromStatus: TheoryExamStatus
    let toStatus: TheoryExamStatus
    let submissionReason: TheoryExamSubmissionReason
    let submittedAt: Date
}

enum TheoryExamLifecycle {
    /// Returns the only valid submission transition without mutating persisted state.
    /// Passing `now` makes timer and resume behavior deterministic in tests.
    static func transition(
        status: TheoryExamStatus,
        deadline: Date,
        now: Date,
        trigger: TheoryExamSubmissionTrigger
    ) -> TheoryExamLifecycleTransition? {
        guard status == .inProgress else { return nil }

        let reason: TheoryExamSubmissionReason
        if now >= deadline {
            reason = .timeExpired
        } else if trigger == .manual {
            reason = .manual
        } else {
            return nil
        }

        return TheoryExamLifecycleTransition(
            fromStatus: .inProgress,
            toStatus: .awaitingSelfAssessment,
            submissionReason: reason,
            submittedAt: now
        )
    }
}

struct TheoryExamScoringQuestion: Equatable {
    let id: String
    let learningOutcome: String
    let studyMode: String
    let correctAnswerIndex: Int?
    let rubricMarksByID: [String: Int]
}

struct TheoryExamLearningOutcomeScore: Identifiable, Equatable {
    var id: String { learningOutcome }
    let learningOutcome: String
    let multipleChoiceAwarded: Int
    let multipleChoiceMaximum: Int
    let writtenAwarded: Int
    let writtenMaximum: Int

    var totalAwarded: Int { multipleChoiceAwarded + writtenAwarded }
    var totalMaximum: Int { multipleChoiceMaximum + writtenMaximum }
}

enum TheoryExamScoreCalculator {
    static func learningOutcomeScores(
        questions: [TheoryExamScoringQuestion],
        selectedAnswers: [String: Int],
        rubricSelections: [String: [String]]
    ) -> [TheoryExamLearningOutcomeScore] {
        struct MutableScore {
            var multipleChoiceAwarded = 0
            var multipleChoiceMaximum = 0
            var writtenAwarded = 0
            var writtenMaximum = 0
        }

        var values: [String: MutableScore] = [:]
        for question in questions {
            var score = values[question.learningOutcome, default: MutableScore()]
            if question.studyMode == "multiple_choice" {
                score.multipleChoiceMaximum += 1
                if selectedAnswers[question.id] == question.correctAnswerIndex,
                   question.correctAnswerIndex != nil {
                    score.multipleChoiceAwarded += 1
                }
            } else if question.studyMode == "written_answer" {
                let selected = Set(rubricSelections[question.id] ?? [])
                score.writtenMaximum += question.rubricMarksByID.values.reduce(0, +)
                score.writtenAwarded += question.rubricMarksByID.reduce(into: 0) { result, item in
                    if selected.contains(item.key) {
                        result += item.value
                    }
                }
            }
            values[question.learningOutcome] = score
        }

        return values.keys.sorted().compactMap { learningOutcome in
            guard let score = values[learningOutcome] else { return nil }
            return TheoryExamLearningOutcomeScore(
                learningOutcome: learningOutcome,
                multipleChoiceAwarded: score.multipleChoiceAwarded,
                multipleChoiceMaximum: score.multipleChoiceMaximum,
                writtenAwarded: score.writtenAwarded,
                writtenMaximum: score.writtenMaximum
            )
        }
    }
}

enum TheoryExamBuilderError: LocalizedError, Equatable {
    case insufficientMultipleChoice(required: Int, available: Int)
    case insufficientWritten(required: Int, available: Int)

    var errorDescription: String? {
        switch self {
        case let .insufficientMultipleChoice(required, available):
            "四択問題が不足しています（必要：\(required)、利用可能：\(available)）。"
        case let .insufficientWritten(required, available):
            "記述式問題が不足しています（必要：\(required)、利用可能：\(available)）。"
        }
    }
}

enum TheoryExamBuilder {
    static let multipleChoiceCount = 50
    static let writtenCount = 4
    static let durationMinutes = 120

    static func build(
        from candidates: [TheoryExamCandidate],
        seed: UInt64 = UInt64(Date.now.timeIntervalSince1970)
    ) throws -> TheoryExamBlueprint {
        let uniqueCandidates = Dictionary(
            candidates.map { ($0.id, $0) },
            uniquingKeysWith: { first, _ in first }
        ).values
        let multipleChoice = uniqueCandidates.filter { $0.studyMode == "multiple_choice" }
        let written = uniqueCandidates.filter { $0.studyMode == "written_answer" }

        guard multipleChoice.count >= multipleChoiceCount else {
            throw TheoryExamBuilderError.insufficientMultipleChoice(
                required: multipleChoiceCount,
                available: multipleChoice.count
            )
        }
        guard written.count >= writtenCount else {
            throw TheoryExamBuilderError.insufficientWritten(
                required: writtenCount,
                available: written.count
            )
        }

        return TheoryExamBlueprint(
            multipleChoiceQuestionIDs: balancedSelection(
                Array(multipleChoice),
                count: multipleChoiceCount,
                seed: seed
            ).map(\.id),
            writtenQuestionIDs: balancedSelection(
                Array(written),
                count: writtenCount,
                seed: seed &+ 1
            ).map(\.id),
            durationMinutes: durationMinutes
        )
    }

    private static func balancedSelection(
        _ candidates: [TheoryExamCandidate],
        count: Int,
        seed: UInt64
    ) -> [TheoryExamCandidate] {
        var grouped = Dictionary(grouping: candidates, by: \.learningOutcome)
            .mapValues { group in
                group.sorted { stableRank($0.id, seed: seed) < stableRank($1.id, seed: seed) }
            }
        let keys = grouped.keys.sorted()
        var selected: [TheoryExamCandidate] = []

        while selected.count < count {
            var addedInRound = false
            for key in keys where selected.count < count {
                guard var group = grouped[key], !group.isEmpty else { continue }
                selected.append(group.removeFirst())
                grouped[key] = group
                addedInRound = true
            }
            if !addedInRound { break }
        }
        return selected
    }

    private static func stableRank(_ value: String, seed: UInt64) -> UInt64 {
        var hash = UInt64(14_695_981_039_346_656_037) ^ seed
        for byte in value.utf8 {
            hash ^= UInt64(byte)
            hash &*= 1_099_511_628_211
        }
        return hash
    }
}
