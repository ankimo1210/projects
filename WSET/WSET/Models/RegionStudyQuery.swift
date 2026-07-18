import Foundation

struct RegionStudyStatistics: Equatable, Sendable {
    let questionCount: Int
    let studiedQuestionCount: Int
    let attemptCount: Int
    let correctCount: Int
    let dueQuestionCount: Int

    var coverage: Double? {
        guard questionCount > 0 else { return nil }
        return Double(studiedQuestionCount) / Double(questionCount)
    }

    var accuracy: Double? {
        guard attemptCount > 0 else { return nil }
        return Double(correctCount) / Double(attemptCount)
    }
}

struct GrapeVarietyFrequency: Identifiable, Equatable, Sendable {
    let name: String
    let questionCount: Int

    var id: String { name }
}

enum RegionStudyQuery {
    static func matchingQuestionIDs(
        focusValues: [String],
        items: [StudyFocusItem]
    ) -> Set<String> {
        let normalizedItems = items.map { item in
            StudyFocusItem(
                questionID: item.questionID,
                geography: GeographyNormalizer.canonicalValues(item.geography),
                countries: item.countries.map { GeographyNormalizer.canonicalValues($0) },
                regions: item.regions.map { GeographyNormalizer.canonicalValues($0) },
                grapeVarieties: item.grapeVarieties,
                wineType: item.wineType,
                category: item.category,
                difficulty: item.difficulty,
                cognitiveSkill: item.cognitiveSkill
            )
        }

        return GeographyNormalizer.canonicalValues(focusValues).reduce(into: Set<String>()) {
            result, value in
            result.formUnion(
                StudyFocusCatalog.matchingQuestionIDs(
                    for: .geography,
                    value: value,
                    in: normalizedItems
                )
            )
        }
    }

    static func matchingQuestions(
        region: MapRegion,
        questions: [StudyQuestion]
    ) -> [StudyQuestion] {
        matchingQuestions(focusValues: region.focusValues, questions: questions)
    }

    static func matchingQuestions(
        focusValues: [String],
        questions: [StudyQuestion]
    ) -> [StudyQuestion] {
        let eligibleQuestions = questions.filter {
            $0.studyMode == "multiple_choice" && $0.correctAnswerIndex != nil
        }
        return matchedQuestions(
            focusValues: focusValues,
            eligibleQuestions: eligibleQuestions
        )
    }

    static func matchingWrittenQuestions(
        focusValues: [String],
        questions: [StudyQuestion]
    ) -> [StudyQuestion] {
        matchedQuestions(
            focusValues: focusValues,
            eligibleQuestions: questions.filter { $0.studyMode == "written_answer" }
        )
    }

    private static func matchedQuestions(
        focusValues: [String],
        eligibleQuestions: [StudyQuestion]
    ) -> [StudyQuestion] {
        let items = eligibleQuestions.map { focusItem(question: $0) }
        let identifiers = matchingQuestionIDs(focusValues: focusValues, items: items)
        return eligibleQuestions
            .filter { identifiers.contains($0.id) }
            .sorted { $0.id < $1.id }
    }

    static func relatedGrapeVarieties(
        region: MapRegion,
        questions: [StudyQuestion]
    ) -> [GrapeVarietyFrequency] {
        relatedGrapeVarieties(in: matchingQuestions(region: region, questions: questions))
    }

    static func relatedGrapeVarieties(
        in questions: [StudyQuestion]
    ) -> [GrapeVarietyFrequency] {
        var counts: [String: Int] = [:]
        for question in questions {
            for grape in Set(question.grapeVarieties.map {
                $0.trimmingCharacters(in: .whitespacesAndNewlines)
            }).filter({ !$0.isEmpty }) {
                counts[grape, default: 0] += 1
            }
        }
        return counts.map { GrapeVarietyFrequency(name: $0.key, questionCount: $0.value) }
            .sorted {
                if $0.questionCount != $1.questionCount {
                    return $0.questionCount > $1.questionCount
                }
                return $0.name.localizedStandardCompare($1.name) == .orderedAscending
            }
    }

    static func statistics(
        region: MapRegion,
        questions: [StudyQuestion],
        progress: [QuestionProgress],
        attempts: [StudyAttempt],
        now: Date = .now
    ) -> RegionStudyStatistics {
        statistics(
            focusValues: region.focusValues,
            questions: questions,
            progress: progress,
            attempts: attempts,
            now: now
        )
    }

    static func statistics(
        focusValues: [String],
        questions: [StudyQuestion],
        progress: [QuestionProgress],
        attempts: [StudyAttempt],
        now: Date = .now
    ) -> RegionStudyStatistics {
        let matching = matchingQuestions(focusValues: focusValues, questions: questions)
        let identifiers = Set(matching.map(\.id))
        var progressByID: [String: QuestionProgress] = [:]
        for record in progress where identifiers.contains(record.questionID) {
            progressByID[record.questionID] = record
        }
        let studied = progressByID.values.filter { $0.attemptCount > 0 }.count
        let due = progressByID.values.filter {
            $0.attemptCount > 0 && $0.dueDate <= now
        }.count
        let relatedAttempts = attempts.filter { identifiers.contains($0.questionID) }
        let attemptCount: Int
        let correctCount: Int
        if relatedAttempts.isEmpty {
            attemptCount = progressByID.values.reduce(0) { $0 + $1.attemptCount }
            correctCount = progressByID.values.reduce(0) { $0 + $1.correctCount }
        } else {
            attemptCount = relatedAttempts.count
            correctCount = relatedAttempts.filter(\.isCorrect).count
        }
        return RegionStudyStatistics(
            questionCount: matching.count,
            studiedQuestionCount: studied,
            attemptCount: attemptCount,
            correctCount: correctCount,
            dueQuestionCount: due
        )
    }

    static func relatedTerms(
        region: MapRegion,
        terms: [ReferenceTerm]
    ) -> [ReferenceTerm] {
        let explicitOrder = Dictionary(
            uniqueKeysWithValues: region.termIDs.enumerated().map { ($1, $0) }
        )
        let focusValues = Set(GeographyNormalizer.canonicalValues(region.focusValues))
        var selected: [String: ReferenceTerm] = [:]
        for term in terms where region.termIDs.contains(term.id) {
            selected[term.id] = term
        }
        for term in terms {
            guard let termRegion = term.region else { continue }
            if focusValues.contains(GeographyNormalizer.canonical(termRegion)) {
                selected[term.id] = term
            }
        }
        return selected.values.sorted { lhs, rhs in
            let lhsRank = explicitOrder[lhs.id] ?? .max
            let rhsRank = explicitOrder[rhs.id] ?? .max
            if lhsRank != rhsRank { return lhsRank < rhsRank }
            return lhs.nameJapanese.localizedStandardCompare(rhs.nameJapanese) == .orderedAscending
        }
    }

    private static func focusItem(question: StudyQuestion) -> StudyFocusItem {
        let countries = question.countries
        let regions = question.regions
        return StudyFocusItem(
            questionID: question.id,
            geography: question.geography,
            countries: countries.isEmpty ? nil : countries,
            regions: regions.isEmpty ? nil : regions,
            grapeVarieties: question.grapeVarieties,
            wineType: question.wineType,
            category: question.category,
            difficulty: question.difficulty,
            cognitiveSkill: question.cognitiveSkill
        )
    }
}
