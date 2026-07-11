import Foundation
import SwiftData
import SwiftUI
import UniformTypeIdentifiers

struct StudyBackup: Codable {
    let schemaVersion: Int
    let createdAt: Date
    let progress: [ProgressBackup]
    let attempts: [AttemptBackup]
    let tastingNotes: [TastingBackup]
    let mockExams: [MockExamBackup]
}

struct ProgressBackup: Codable {
    let questionID: String
    let isBookmarked: Bool
    let attemptCount: Int
    let correctCount: Int
    let intervalDays: Int
    let dueDate: Date
    let lastStudiedAt: Date?
    let lastWasCorrect: Bool?
}

struct AttemptBackup: Codable {
    let id: UUID
    let questionID: String
    let isCorrect: Bool
    let rating: Int
    let studiedAt: Date
    let responseText: String?
}

struct TastingBackup: Codable {
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

struct MockExamBackup: Codable {
    let id: UUID
    let completedAt: Date
    let correctCount: Int
    let questionCount: Int
    let outcomeResults: [String: MockOutcomeResult]
    let missedQuestionIDs: [String]
}

struct BackupRestoreResult {
    let progressCount: Int
    let attemptCount: Int
    let tastingCount: Int
    let mockExamCount: Int

    var summary: String {
        "進捗\(progressCount)件、学習回答\(attemptCount)件、テイスティング\(tastingCount)件、模擬試験\(mockExamCount)件を復元しました。"
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
                responseText: $0.responseText
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
                conclusion: $0.conclusion
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
        return StudyBackup(
            schemaVersion: 1,
            createdAt: .now,
            progress: progress,
            attempts: attempts,
            tastingNotes: tastings,
            mockExams: exams
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
                studiedAt: snapshot.studiedAt
            )
            attempt.id = snapshot.id
            context.insert(attempt)
            attemptIDs.insert(snapshot.id)
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

        try context.save()
        return BackupRestoreResult(
            progressCount: backup.progress.count,
            attemptCount: backup.attempts.count,
            tastingCount: backup.tastingNotes.count,
            mockExamCount: backup.mockExams.count
        )
    }
}

struct StudyBackupDocument: FileDocument {
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
            "選択したファイルはWSET学習のバックアップではありません。"
        case let .unsupportedSchema(version):
            "バックアップ形式（バージョン\(version)）には対応していません。"
        }
    }

    static func userFacingMessage(for error: Error, fallback: String) -> String {
        guard let backupError = error as? BackupError else { return fallback }
        return backupError.errorDescription ?? fallback
    }
}
