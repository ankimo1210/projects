import Foundation
import SwiftData

enum QuestionImporterError: LocalizedError {
    case packMissing
    case developmentContentUnavailable
    case unsupportedSchema(Int)
    case countMismatch(expected: Int, actual: Int)
    case duplicateQuestionID(String)

    var errorDescription: String? {
        switch self {
        case .packMissing:
            "問題データがこのビルドに含まれていません。"
        case .developmentContentUnavailable:
            "公開レビュー済みの問題データがこのビルドに含まれていません。"
        case let .unsupportedSchema(version):
            "問題データの形式 v\(version) には対応していません。"
        case let .countMismatch(expected, actual):
            "問題数が一致しません（想定：\(expected)、実際：\(actual)）。"
        case let .duplicateQuestionID(id):
            "問題IDが重複しています（\(id)）。"
        }
    }
}

@MainActor
enum QuestionImporter {
    static func importIfNeeded(into context: ModelContext) throws {
        guard let primaryPack = try loadBundledPack(named: "question_pack") else {
            throw QuestionImporterError.packMissing
        }
        guard shouldImport(
            primaryPack,
            allowsDevelopmentContent: allowsDevelopmentContent
        ) else {
            throw QuestionImporterError.developmentContentUnavailable
        }
        var packs = [primaryPack]
        var ignoredDevelopmentQuestionIDs: Set<String> = []
        if let writtenPack = try loadBundledPack(named: "written_question_pack") {
            if shouldImport(
                writtenPack,
                allowsDevelopmentContent: allowsDevelopmentContent
            ) {
                packs.append(writtenPack)
            } else if writtenPack.distributionStatus == "development_only" {
                ignoredDevelopmentQuestionIDs = Set(writtenPack.questions.map(\.id))
            }
        }
        let (packedQuestions, combinedSourceHash) = try validateAndCombine(packs)

        let defaults = UserDefaults.standard
        let importedHash = defaults.string(forKey: "questionPackSourceHash")
        let existingQuestions = try context.fetch(FetchDescriptor<StudyQuestion>())
        let existingCount = existingQuestions.count
        if existingCount > 0 && importedHash == combinedSourceHash {
            return
        }
        let existingQuestionIDs = Set(existingQuestions.map(\.id))
        let newQuestionIDs = Set(packedQuestions.map(\.id))
        if shouldResetStudyHistory(
            existingQuestionIDs: existingQuestionIDs,
            newQuestionIDs: newQuestionIDs,
            hasImportedHash: importedHash != nil,
            ignoredContentIDs: ignoredDevelopmentQuestionIDs
        ) {
            try resetQuestionStudyHistory(in: context)
        }
        if existingCount > 0 {
            for question in existingQuestions {
                context.delete(question)
            }
            try context.save()
        }

        for (index, packed) in packedQuestions.enumerated() {
            context.insert(StudyQuestion(packed: packed))
            if index.isMultiple(of: 500) {
                try context.save()
            }
        }
        try context.save()
        defaults.set(combinedSourceHash, forKey: "questionPackSourceHash")
    }

    static func validateAndCombine(_ packs: [QuestionPack]) throws -> ([PackedQuestion], String) {
        var questions: [PackedQuestion] = []
        var seenIDs: Set<String> = []
        for pack in packs {
            guard [1, 2, 3, 4].contains(pack.schemaVersion) else {
                throw QuestionImporterError.unsupportedSchema(pack.schemaVersion)
            }
            guard pack.questionCount == pack.questions.count else {
                throw QuestionImporterError.countMismatch(
                    expected: pack.questionCount,
                    actual: pack.questions.count
                )
            }
            for question in pack.questions {
                guard seenIDs.insert(question.id).inserted else {
                    throw QuestionImporterError.duplicateQuestionID(question.id)
                }
                questions.append(question)
            }
        }
        return (questions, packs.map(\.sourceHash).joined(separator: ":"))
    }

    static func shouldImport(
        _ pack: QuestionPack,
        allowsDevelopmentContent: Bool
    ) -> Bool {
        switch pack.distributionStatus {
        case nil, "release":
            true
        case "development_only":
            allowsDevelopmentContent
        default:
            false
        }
    }

    private static var allowsDevelopmentContent: Bool {
#if DEBUG
        true
#else
        false
#endif
    }

    private static func loadBundledPack(named name: String) throws -> QuestionPack? {
        guard let url = Bundle.main.url(forResource: name, withExtension: "json")
            ?? Bundle.main.url(
                forResource: name,
                withExtension: "json",
                subdirectory: "QuestionData"
            )
        else { return nil }
        return try JSONDecoder().decode(QuestionPack.self, from: Data(contentsOf: url))
    }

    static func shouldResetStudyHistory(
        existingQuestionIDs: Set<String>,
        newQuestionIDs: Set<String>,
        hasImportedHash: Bool,
        ignoredContentIDs: Set<String> = []
    ) -> Bool {
        let relevantExistingQuestionIDs = existingQuestionIDs.subtracting(ignoredContentIDs)
        if relevantExistingQuestionIDs.isEmpty {
            return existingQuestionIDs.isEmpty && hasImportedHash
        }
        return !relevantExistingQuestionIDs.isSubset(of: newQuestionIDs)
    }

    static func resetQuestionStudyHistory(in context: ModelContext) throws {
        for progress in try context.fetch(FetchDescriptor<QuestionProgress>()) {
            context.delete(progress)
        }
        for attempt in try context.fetch(FetchDescriptor<StudyAttempt>()) {
            context.delete(attempt)
        }
        for draft in try context.fetch(FetchDescriptor<WrittenAnswerDraft>()) {
            context.delete(draft)
        }
        for exam in try context.fetch(FetchDescriptor<MockExamSession>()) {
            context.delete(exam)
        }
        for exam in try context.fetch(FetchDescriptor<TheoryExamSession>()) {
            context.delete(exam)
        }
        try context.save()
    }
}
