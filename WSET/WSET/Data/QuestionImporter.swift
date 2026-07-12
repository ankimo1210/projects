import Foundation
import SwiftData

enum QuestionImporterError: LocalizedError {
    case packMissing
    case unsupportedSchema(Int)
    case countMismatch(expected: Int, actual: Int)

    var errorDescription: String? {
        switch self {
        case .packMissing:
            "問題データがこのビルドに含まれていません。"
        case let .unsupportedSchema(version):
            "問題データの形式 v\(version) には対応していません。"
        case let .countMismatch(expected, actual):
            "問題数が一致しません（想定：\(expected)、実際：\(actual)）。"
        }
    }
}

@MainActor
enum QuestionImporter {
    static func importIfNeeded(into context: ModelContext) throws {
        guard let url = Bundle.main.url(forResource: "question_pack", withExtension: "json")
            ?? Bundle.main.url(
                forResource: "question_pack",
                withExtension: "json",
                subdirectory: "QuestionData"
            )
        else {
            throw QuestionImporterError.packMissing
        }

        let pack = try JSONDecoder().decode(QuestionPack.self, from: Data(contentsOf: url))
        guard [1, 2, 3, 4].contains(pack.schemaVersion) else {
            throw QuestionImporterError.unsupportedSchema(pack.schemaVersion)
        }
        guard pack.questionCount == pack.questions.count else {
            throw QuestionImporterError.countMismatch(
                expected: pack.questionCount,
                actual: pack.questions.count
            )
        }

        let defaults = UserDefaults.standard
        let importedHash = defaults.string(forKey: "questionPackSourceHash")
        let existingQuestions = try context.fetch(FetchDescriptor<StudyQuestion>())
        let existingCount = existingQuestions.count
        if existingCount > 0 && importedHash == pack.sourceHash {
            return
        }
        let existingQuestionIDs = Set(existingQuestions.map(\.id))
        let newQuestionIDs = Set(pack.questions.map(\.id))
        if shouldResetStudyHistory(
            existingQuestionIDs: existingQuestionIDs,
            newQuestionIDs: newQuestionIDs,
            hasImportedHash: importedHash != nil
        ) {
            try resetQuestionStudyHistory(in: context)
        }
        if existingCount > 0 {
            for question in existingQuestions {
                context.delete(question)
            }
            try context.save()
        }

        for (index, packed) in pack.questions.enumerated() {
            context.insert(StudyQuestion(packed: packed))
            if index.isMultiple(of: 500) {
                try context.save()
            }
        }
        try context.save()
        defaults.set(pack.sourceHash, forKey: "questionPackSourceHash")
    }

    static func shouldResetStudyHistory(
        existingQuestionIDs: Set<String>,
        newQuestionIDs: Set<String>,
        hasImportedHash: Bool
    ) -> Bool {
        if existingQuestionIDs.isEmpty {
            return hasImportedHash
        }
        return !existingQuestionIDs.isSubset(of: newQuestionIDs)
    }

    static func resetQuestionStudyHistory(in context: ModelContext) throws {
        for progress in try context.fetch(FetchDescriptor<QuestionProgress>()) {
            context.delete(progress)
        }
        for attempt in try context.fetch(FetchDescriptor<StudyAttempt>()) {
            context.delete(attempt)
        }
        for exam in try context.fetch(FetchDescriptor<MockExamSession>()) {
            context.delete(exam)
        }
        try context.save()
    }
}
