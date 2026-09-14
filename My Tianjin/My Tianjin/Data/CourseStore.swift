import Combine
import Foundation
import SwiftData

@MainActor
final class CourseStore: ObservableObject {
    static let scopeKey = "course::hsk3-first-lesson"

    @Published private(set) var lesson: CourseLesson?
    @Published private(set) var snapshot: CourseSnapshot?
    @Published private(set) var errorMessage: String?

    typealias SaveAction = @MainActor (ModelContext) throws -> Void

    private let repository: CourseRepository
    private let saveAction: SaveAction
    private var context: ModelContext?
    private var pendingSubmission: PendingSubmission?

    init(
        repository: CourseRepository = CourseRepository(),
        saveAction: @escaping SaveAction = { try $0.save() }
    ) {
        self.repository = repository
        self.saveAction = saveAction
    }

    @discardableResult
    func load(in container: ModelContainer) -> Bool {
        let candidateContext = ModelContext(container)
        candidateContext.autosaveEnabled = false
        do {
            let candidateLesson = try repository.loadLesson()
            let scopeKey = Self.scopeKey
            let descriptor = FetchDescriptor<StudySessionRecord>(
                predicate: #Predicate { $0.scopeKey == scopeKey }
            )
            let candidateSnapshot: CourseSnapshot
            if let record = try candidateContext.fetch(descriptor).first {
                candidateSnapshot = try JSONDecoder().decode(CourseSnapshot.self, from: record.payload)
                try candidateSnapshot.validate(against: candidateLesson)
            } else {
                candidateSnapshot = CourseSnapshot(lesson: candidateLesson)
            }

            context = candidateContext
            lesson = candidateLesson
            snapshot = candidateSnapshot
            pendingSubmission = nil
            errorMessage = nil
            return true
        } catch {
            candidateContext.rollback()
            // A failed reload must not leave an older context writable. The
            // rejected payload stays untouched until a valid load succeeds.
            context = nil
            lesson = nil
            snapshot = nil
            pendingSubmission = nil
            errorMessage = "コースを読み込めませんでした。\(error.localizedDescription)"
            return false
        }
    }

    @discardableResult
    func start(minutes: Int, reviewOnly: Bool = false) -> Bool {
        guard let lesson, var candidate = snapshot else {
            errorMessage = "コースの読み込みが完了していません。"
            return false
        }
        guard candidate.activeSession == nil else {
            errorMessage = "進行中の学習があります。続きから再開してください。"
            return false
        }
        guard let session = CourseEngine.makeSession(
            lesson: lesson,
            progress: candidate.progress,
            minutes: minutes,
            reviewOnly: reviewOnly,
            now: Date()
        ) else {
            errorMessage = reviewOnly
                ? "期限の来た復習問題はありません。"
                : "今取り組める問題はありません。"
            return false
        }
        candidate.sessions.append(session)
        let saved = persist(candidate, lesson: lesson)
        if saved { pendingSubmission = nil }
        return saved
    }

    @discardableResult
    func submit(optionID: String) -> Bool {
        guard let lesson,
              let snapshot,
              let session = snapshot.activeSession,
              let questionID = session.currentQuestionID else {
            errorMessage = "回答できる問題がありません。"
            return false
        }

        let submission: PendingSubmission
        if let pendingSubmission {
            guard pendingSubmission.sessionID == session.id,
                  pendingSubmission.questionID == questionID,
                  pendingSubmission.optionID == optionID else {
                errorMessage = "保存に失敗した回答と同じ選択肢でもう一度お試しください。"
                return false
            }
            submission = pendingSubmission
        } else {
            submission = PendingSubmission(
                attemptID: UUID(),
                sessionID: session.id,
                questionID: questionID,
                optionID: optionID,
                answeredAt: Date()
            )
        }

        do {
            let candidate = try CourseEngine.submit(
                snapshot: snapshot,
                lesson: lesson,
                sessionID: session.id,
                attemptID: submission.attemptID,
                optionID: optionID,
                now: submission.answeredAt
            )
            guard persist(candidate, lesson: lesson) else {
                pendingSubmission = submission
                return false
            }
            pendingSubmission = nil
            return true
        } catch {
            errorMessage = "回答を保存できませんでした。\(error.localizedDescription)"
            return false
        }
    }

    @discardableResult
    func advance() -> Bool {
        guard let lesson,
              let snapshot,
              let session = snapshot.activeSession else {
            errorMessage = "進行中の学習がありません。"
            return false
        }
        do {
            let candidate = try CourseEngine.advance(
                snapshot: snapshot,
                sessionID: session.id,
                now: Date()
            )
            return persist(candidate, lesson: lesson)
        } catch {
            errorMessage = "次の問題へ進めませんでした。\(error.localizedDescription)"
            return false
        }
    }

    func clearError() {
        errorMessage = nil
    }

    private func persist(_ candidate: CourseSnapshot, lesson: CourseLesson) -> Bool {
        guard let context else {
            errorMessage = "保存先が準備されていません。"
            return false
        }
        do {
            try candidate.validate(against: lesson)
            let payload = try JSONEncoder().encode(candidate)
            let scopeKey = Self.scopeKey
            let descriptor = FetchDescriptor<StudySessionRecord>(
                predicate: #Predicate { $0.scopeKey == scopeKey }
            )
            if let existing = try context.fetch(descriptor).first {
                existing.payload = payload
                existing.updatedAt = Date()
            } else {
                context.insert(StudySessionRecord(scopeKey: scopeKey, payload: payload))
            }
            try saveAction(context)
            snapshot = candidate
            errorMessage = nil
            return true
        } catch {
            context.rollback()
            errorMessage = "学習内容を保存できませんでした。\(error.localizedDescription)"
            return false
        }
    }
}

nonisolated private struct PendingSubmission: Sendable {
    let attemptID: UUID
    let sessionID: UUID
    let questionID: String
    let optionID: String
    let answeredAt: Date
}
