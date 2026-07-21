import Foundation
import SwiftData
import SwiftUI
import UniformTypeIdentifiers

nonisolated struct StudyBackup: Codable {
    let schemaVersion: Int
    let createdAt: Date
    let progress: [ProgressBackup]
    let attempts: [AttemptBackup]
    let writtenDrafts: [WrittenAnswerDraftBackup]?
    let tastingNotes: [TastingBackup]
    let mockExams: [MockExamBackup]
    let termProgress: [ReferenceTermProgressBackup]?
    let theoryExams: [TheoryExamBackup]?
}

nonisolated struct ProgressBackup: Codable {
    let questionID: String
    let isBookmarked: Bool
    let attemptCount: Int
    let correctCount: Int
    let intervalDays: Int
    let dueDate: Date
    let lastStudiedAt: Date?
    let lastWasCorrect: Bool?
}

nonisolated struct AttemptBackup: Codable {
    let id: UUID
    let questionID: String
    let isCorrect: Bool
    let rating: Int
    let studiedAt: Date
    let responseText: String?
    let awardedMarks: Int?
    let maximumMarks: Int?
    let rubricSelections: [String]?
    let durationSeconds: Int?
}

nonisolated struct WrittenAnswerDraftBackup: Codable {
    let questionID: String
    let responseText: String
    let rubricSelections: [String]
    let startedAt: Date
    let submittedAt: Date?
    let updatedAt: Date
}

nonisolated struct TastingBackup: Codable {
    let id: UUID
    let sessionID: UUID?
    let sampleLabel: String
    let tastedAt: Date
    let wineName: String
    let appearanceClarity: String
    let appearanceIntensity: String
    let appearanceColour: String
    let noseCondition: String
    let noseIntensity: String
    let noseDevelopment: String
    let aromaNotes: String
    let sweetness: String
    let acidity: String
    let tannin: String
    let alcohol: String
    let body: String
    let flavourIntensity: String
    let finish: String
    let flavourNotes: String
    let quality: String
    let readiness: String
    let conclusion: String
    let examStartedAt: Date?
    let examSubmittedAt: Date?
    let examDurationSeconds: Int?
    let examWasTimeExpired: Bool?
    let examCompletionPercent: Double?

    var draft: TastingDraft {
        var draft = TastingDraft()
        draft.wineName = wineName
        draft.appearanceClarity = appearanceClarity
        draft.appearanceIntensity = appearanceIntensity
        draft.appearanceColour = appearanceColour
        draft.noseCondition = noseCondition
        draft.noseIntensity = noseIntensity
        draft.noseDevelopment = noseDevelopment
        draft.aromaNotes = aromaNotes
        draft.sweetness = sweetness
        draft.acidity = acidity
        draft.tannin = tannin
        draft.alcohol = alcohol
        draft.body = body
        draft.flavourIntensity = flavourIntensity
        draft.finish = finish
        draft.flavourNotes = flavourNotes
        draft.quality = quality
        draft.readiness = readiness
        draft.conclusion = conclusion
        return draft
    }
}

nonisolated struct MockExamBackup: Codable {
    let id: UUID
    let completedAt: Date
    let correctCount: Int
    let questionCount: Int
    let outcomeResults: [String: MockOutcomeResult]
    let missedQuestionIDs: [String]
}

nonisolated struct TheoryExamBackup: Codable {
    let id: UUID
    let startedAt: Date
    let deadline: Date
    let submittedAt: Date?
    let completedAt: Date?
    let statusRawValue: String
    let submissionReasonRawValue: String?
    let currentIndex: Int
    let multipleChoiceQuestionIDs: [String]
    let writtenQuestionIDs: [String]
    let selectedAnswers: [String: Int]
    let writtenResponses: [String: String]
    let flaggedQuestionIDs: [String]
    let rubricSelections: [String: [String]]
    let multipleChoiceCorrectCount: Int
    let writtenAwardedMarks: Int
    let writtenMaximumMarks: Int
    let completionRecorded: Bool
}

nonisolated struct BackupRestoreResult {
    let progressCount: Int
    let attemptCount: Int
    let writtenDraftCount: Int
    let tastingCount: Int
    let mockExamCount: Int
    let termProgressCount: Int
    let theoryExamCount: Int

    var summary: String {
        "進捗\(progressCount)件、学習回答\(attemptCount)件、記述下書き\(writtenDraftCount)件、用語\(termProgressCount)件、テイスティング\(tastingCount)件、ミニ模試\(mockExamCount)件、理論模試\(theoryExamCount)件を復元しました。"
    }
}

@MainActor
enum BackupService {
    static func makeBackup(in context: ModelContext) throws -> StudyBackup {
        let progress = try context.fetch(FetchDescriptor<QuestionProgress>()).map {
            ProgressBackup(
                questionID: $0.questionID,
                isBookmarked: $0.isBookmarked,
                attemptCount: $0.attemptCount,
                correctCount: $0.correctCount,
                intervalDays: $0.intervalDays,
                dueDate: $0.dueDate,
                lastStudiedAt: $0.lastStudiedAt,
                lastWasCorrect: $0.lastWasCorrect
            )
        }
        let attempts = try context.fetch(FetchDescriptor<StudyAttempt>()).map {
            AttemptBackup(
                id: $0.id,
                questionID: $0.questionID,
                isCorrect: $0.isCorrect,
                rating: $0.rating,
                studiedAt: $0.studiedAt,
                responseText: $0.responseText,
                awardedMarks: $0.awardedMarks,
                maximumMarks: $0.maximumMarks,
                rubricSelections: $0.rubricSelections,
                durationSeconds: $0.durationSeconds
            )
        }
        let writtenDrafts = try context.fetch(FetchDescriptor<WrittenAnswerDraft>()).map {
            WrittenAnswerDraftBackup(
                questionID: $0.questionID,
                responseText: $0.responseText,
                rubricSelections: $0.rubricSelections,
                startedAt: $0.startedAt,
                submittedAt: $0.submittedAt,
                updatedAt: $0.updatedAt
            )
        }
        let tastings = try context.fetch(FetchDescriptor<TastingNote>()).map {
            TastingBackup(
                id: $0.id,
                sessionID: $0.sessionID,
                sampleLabel: $0.sampleLabel,
                tastedAt: $0.tastedAt,
                wineName: $0.wineName,
                appearanceClarity: $0.appearanceClarity,
                appearanceIntensity: $0.appearanceIntensity,
                appearanceColour: $0.appearanceColour,
                noseCondition: $0.noseCondition,
                noseIntensity: $0.noseIntensity,
                noseDevelopment: $0.noseDevelopment,
                aromaNotes: $0.aromaNotes,
                sweetness: $0.sweetness,
                acidity: $0.acidity,
                tannin: $0.tannin,
                alcohol: $0.alcohol,
                body: $0.body,
                flavourIntensity: $0.flavourIntensity,
                finish: $0.finish,
                flavourNotes: $0.flavourNotes,
                quality: $0.quality,
                readiness: $0.readiness,
                conclusion: $0.conclusion,
                examStartedAt: $0.examStartedAt,
                examSubmittedAt: $0.examSubmittedAt,
                examDurationSeconds: $0.examDurationSeconds,
                examWasTimeExpired: $0.examWasTimeExpired,
                examCompletionPercent: $0.examCompletionPercent
            )
        }
        let exams = try context.fetch(FetchDescriptor<MockExamSession>()).map {
            MockExamBackup(
                id: $0.id,
                completedAt: $0.completedAt,
                correctCount: $0.correctCount,
                questionCount: $0.questionCount,
                outcomeResults: $0.outcomeResults,
                missedQuestionIDs: $0.missedQuestionIDs
            )
        }
        let theoryExams = try context.fetch(FetchDescriptor<TheoryExamSession>()).map {
            TheoryExamBackup(
                id: $0.id,
                startedAt: $0.startedAt,
                deadline: $0.deadline,
                submittedAt: $0.submittedAt,
                completedAt: $0.completedAt,
                statusRawValue: $0.statusRawValue,
                submissionReasonRawValue: $0.submissionReasonRawValue,
                currentIndex: $0.currentIndex,
                multipleChoiceQuestionIDs: $0.multipleChoiceQuestionIDs,
                writtenQuestionIDs: $0.writtenQuestionIDs,
                selectedAnswers: $0.selectedAnswers,
                writtenResponses: $0.writtenResponses,
                flaggedQuestionIDs: Array($0.flaggedQuestionIDs).sorted(),
                rubricSelections: $0.rubricSelections,
                multipleChoiceCorrectCount: $0.multipleChoiceCorrectCount,
                writtenAwardedMarks: $0.writtenAwardedMarks,
                writtenMaximumMarks: $0.writtenMaximumMarks,
                completionRecorded: $0.completionRecorded
            )
        }
        return StudyBackup(
            schemaVersion: 1,
            createdAt: .now,
            progress: progress,
            attempts: attempts,
            writtenDrafts: writtenDrafts,
            tastingNotes: tastings,
            mockExams: exams,
            termProgress: R5BackupSupport.snapshots(
                in: context,
                termIDMigrations: ReferenceStore.shared.termIDMigrations
            ),
            theoryExams: theoryExams
        )
    }

    static func restore(_ backup: StudyBackup, into context: ModelContext) throws -> BackupRestoreResult {
        guard backup.schemaVersion == 1 else {
            throw BackupError.unsupportedSchema(backup.schemaVersion)
        }

        var progressByID = Dictionary(
            uniqueKeysWithValues: try context.fetch(FetchDescriptor<QuestionProgress>()).map {
                ($0.questionID, $0)
            }
        )
        for snapshot in backup.progress {
            let existing = progressByID[snapshot.questionID]
            let record = existing ?? QuestionProgress(questionID: snapshot.questionID)
            if existing == nil {
                context.insert(record)
                progressByID[snapshot.questionID] = record
            }
            record.isBookmarked = record.isBookmarked || snapshot.isBookmarked
            let localDate = record.lastStudiedAt ?? .distantPast
            let backupDate = snapshot.lastStudiedAt ?? .distantPast
            if existing == nil || backupDate >= localDate {
                record.attemptCount = snapshot.attemptCount
                record.correctCount = snapshot.correctCount
                record.intervalDays = snapshot.intervalDays
                record.dueDate = snapshot.dueDate
                record.lastStudiedAt = snapshot.lastStudiedAt
                record.lastWasCorrect = snapshot.lastWasCorrect
            }
        }

        var attemptIDs = Set(try context.fetch(FetchDescriptor<StudyAttempt>()).map(\.id))
        for snapshot in backup.attempts where !attemptIDs.contains(snapshot.id) {
            let attempt = StudyAttempt(
                questionID: snapshot.questionID,
                isCorrect: snapshot.isCorrect,
                rating: snapshot.rating,
                responseText: snapshot.responseText,
                awardedMarks: snapshot.awardedMarks,
                maximumMarks: snapshot.maximumMarks,
                rubricSelections: snapshot.rubricSelections ?? [],
                durationSeconds: snapshot.durationSeconds,
                studiedAt: snapshot.studiedAt
            )
            attempt.id = snapshot.id
            context.insert(attempt)
            attemptIDs.insert(snapshot.id)
        }

        var writtenDraftsByQuestionID = Dictionary(
            uniqueKeysWithValues: try context.fetch(FetchDescriptor<WrittenAnswerDraft>()).map {
                ($0.questionID, $0)
            }
        )
        for snapshot in backup.writtenDrafts ?? [] {
            let existing = writtenDraftsByQuestionID[snapshot.questionID]
            if let existing, snapshot.updatedAt < existing.updatedAt { continue }
            let draft = existing ?? WrittenAnswerDraft(
                questionID: snapshot.questionID,
                startedAt: snapshot.startedAt
            )
            if existing == nil {
                context.insert(draft)
                writtenDraftsByQuestionID[snapshot.questionID] = draft
            }
            draft.startedAt = snapshot.startedAt
            draft.update(
                responseText: snapshot.responseText,
                rubricSelections: snapshot.rubricSelections,
                submittedAt: snapshot.submittedAt,
                at: snapshot.updatedAt
            )
        }

        var tastingByID = Dictionary(
            uniqueKeysWithValues: try context.fetch(FetchDescriptor<TastingNote>()).map { ($0.id, $0) }
        )
        for snapshot in backup.tastingNotes {
            let note = tastingByID[snapshot.id]
                ?? TastingNote(
                    draft: snapshot.draft,
                    sessionID: snapshot.sessionID,
                    sampleLabel: snapshot.sampleLabel
                )
            if tastingByID[snapshot.id] == nil {
                note.id = snapshot.id
                context.insert(note)
                tastingByID[snapshot.id] = note
            }
            note.sessionID = snapshot.sessionID
            note.sampleLabel = snapshot.sampleLabel
            note.tastedAt = snapshot.tastedAt
            note.update(from: snapshot.draft)
            note.examStartedAt = snapshot.examStartedAt
            note.examSubmittedAt = snapshot.examSubmittedAt
            note.examDurationSeconds = snapshot.examDurationSeconds
            note.examWasTimeExpired = snapshot.examWasTimeExpired
            note.examCompletionPercent = snapshot.examCompletionPercent
        }

        var mockIDs = Set(try context.fetch(FetchDescriptor<MockExamSession>()).map(\.id))
        for snapshot in backup.mockExams where !mockIDs.contains(snapshot.id) {
            context.insert(
                MockExamSession(
                    id: snapshot.id,
                    completedAt: snapshot.completedAt,
                    correctCount: snapshot.correctCount,
                    questionCount: snapshot.questionCount,
                    outcomeResults: snapshot.outcomeResults,
                    missedQuestionIDs: snapshot.missedQuestionIDs
                )
            )
            mockIDs.insert(snapshot.id)
        }

        let termProgressCount = try R5BackupSupport.restore(
            backup.termProgress ?? [],
            into: context,
            termIDMigrations: ReferenceStore.shared.termIDMigrations
        )

        var theoryByID = Dictionary(
            uniqueKeysWithValues: try context.fetch(FetchDescriptor<TheoryExamSession>()).map {
                ($0.id, $0)
            }
        )
        for snapshot in backup.theoryExams ?? [] {
            let existing = theoryByID[snapshot.id]
            let session = existing ?? TheoryExamSession(
                id: snapshot.id,
                startedAt: snapshot.startedAt,
                durationMinutes: max(1, Int(snapshot.deadline.timeIntervalSince(snapshot.startedAt) / 60)),
                multipleChoiceQuestionIDs: snapshot.multipleChoiceQuestionIDs,
                writtenQuestionIDs: snapshot.writtenQuestionIDs
            )
            if existing == nil {
                context.insert(session)
                theoryByID[snapshot.id] = session
            }
            guard shouldApply(snapshot, over: existing) else { continue }
            session.startedAt = snapshot.startedAt
            session.deadline = snapshot.deadline
            session.submittedAt = snapshot.submittedAt
            session.completedAt = snapshot.completedAt
            session.statusRawValue = snapshot.statusRawValue
            session.submissionReasonRawValue = snapshot.submissionReasonRawValue
            session.currentIndex = snapshot.currentIndex
            session.multipleChoiceQuestionIDsData = encode(snapshot.multipleChoiceQuestionIDs)
            session.writtenQuestionIDsData = encode(snapshot.writtenQuestionIDs)
            session.selectedAnswersData = encode(snapshot.selectedAnswers)
            session.writtenResponsesData = encode(snapshot.writtenResponses)
            session.flaggedQuestionIDsData = encode(snapshot.flaggedQuestionIDs)
            session.rubricSelectionsData = encode(snapshot.rubricSelections)
            session.multipleChoiceCorrectCount = snapshot.multipleChoiceCorrectCount
            session.writtenAwardedMarks = snapshot.writtenAwardedMarks
            session.writtenMaximumMarks = snapshot.writtenMaximumMarks
            session.completionRecorded = snapshot.completionRecorded
        }

        try context.save()
        return BackupRestoreResult(
            progressCount: backup.progress.count,
            attemptCount: backup.attempts.count,
            writtenDraftCount: backup.writtenDrafts?.count ?? 0,
            tastingCount: backup.tastingNotes.count,
            mockExamCount: backup.mockExams.count,
            termProgressCount: termProgressCount,
            theoryExamCount: backup.theoryExams?.count ?? 0
        )
    }

    private static func shouldApply(
        _ snapshot: TheoryExamBackup,
        over existing: TheoryExamSession?
    ) -> Bool {
        guard let existing else { return true }
        if existing.status == .completed, snapshot.statusRawValue != TheoryExamStatus.completed.rawValue {
            return false
        }
        if snapshot.statusRawValue == TheoryExamStatus.completed.rawValue,
           existing.status != .completed {
            return true
        }
        return (snapshot.completedAt ?? snapshot.submittedAt ?? snapshot.startedAt)
            >= (existing.completedAt ?? existing.submittedAt ?? existing.startedAt)
    }

    private static func encode<T: Encodable>(_ value: T) -> Data {
        (try? JSONEncoder().encode(value)) ?? Data()
    }
}

nonisolated struct StudyBackupDocument: FileDocument {
    static var readableContentTypes: [UTType] { [.json] }
    var backup: StudyBackup

    init(backup: StudyBackup) {
        self.backup = backup
    }

    init(configuration: ReadConfiguration) throws {
        guard let data = configuration.file.regularFileContents else {
            throw BackupError.invalidFile
        }
        backup = try Self.decode(data)
    }

    func fileWrapper(configuration: WriteConfiguration) throws -> FileWrapper {
        FileWrapper(regularFileWithContents: try Self.encoder.encode(backup))
    }

    static let encoder: JSONEncoder = {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        return encoder
    }()

    static let decoder: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return decoder
    }()

    static func decode(_ data: Data) throws -> StudyBackup {
        do {
            return try decoder.decode(StudyBackup.self, from: data)
        } catch {
            throw BackupError.invalidFile
        }
    }
}

enum BackupError: LocalizedError {
    case invalidFile
    case unsupportedSchema(Int)

    var errorDescription: String? {
        switch self {
        case .invalidFile:
            "選択したファイルはCruNoteのバックアップではありません。"
        case let .unsupportedSchema(version):
            "バックアップ形式（バージョン\(version)）には対応していません。"
        }
    }

    static func userFacingMessage(for error: Error, fallback: String) -> String {
        guard let backupError = error as? BackupError else { return fallback }
        return backupError.errorDescription ?? fallback
    }
}
