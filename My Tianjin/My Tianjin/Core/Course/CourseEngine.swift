import Foundation

nonisolated enum CourseEngineError: Error, Equatable, LocalizedError, Sendable {
    case sessionNotFound
    case sessionAlreadyCompleted
    case noCurrentQuestion
    case optionNotFound
    case currentQuestionAlreadyAnswered
    case conflictingAttemptID
    case currentQuestionNotAnswered

    var errorDescription: String? {
        switch self {
        case .sessionNotFound: "学習セッションが見つかりません。"
        case .sessionAlreadyCompleted: "この学習セッションは完了しています。"
        case .noCurrentQuestion: "現在の問題が見つかりません。"
        case .optionNotFound: "選択肢が見つかりません。"
        case .currentQuestionAlreadyAnswered: "この問題にはすでに回答しています。"
        case .conflictingAttemptID: "回答の再試行内容が以前と一致しません。"
        case .currentQuestionNotAnswered: "回答を保存してから次へ進んでください。"
        }
    }
}

nonisolated enum CourseEngine {
    static func makeSession(
        lesson: CourseLesson,
        progress: [String: StudyItemProgress],
        minutes: Int,
        reviewOnly: Bool,
        now: Date
    ) -> CourseSession? {
        guard minutes > 0 else { return nil }
        let limit = minutes >= 10 ? 10 : 3
        let sourceIndices = Dictionary(
            lesson.questions.enumerated().map { ($0.element.id, $0.offset) },
            uniquingKeysWith: { min($0, $1) }
        )
        let dueIDs = lesson.questions
            .filter { progress[$0.id]?.isDue(at: now) == true }
            .map(\.id)
            .sorted {
                let leftDate = progress[$0]?.nextReviewAt ?? .distantFuture
                let rightDate = progress[$1]?.nextReviewAt ?? .distantFuture
                if leftDate != rightDate { return leftDate < rightDate }
                return (sourceIndices[$0] ?? .max) < (sourceIndices[$1] ?? .max)
            }

        var eligibleIDs = dueIDs
        if !reviewOnly {
            let dueSet = Set(dueIDs)
            eligibleIDs.append(contentsOf: lesson.questions.lazy
                .map(\.id)
                .filter { id in
                    guard !dueSet.contains(id) else { return false }
                    guard let itemProgress = progress[id] else { return true }
                    return itemProgress.attemptCount == 0 && itemProgress.nextReviewAt == nil
                })
        }
        let selectedIDs = Array(eligibleIDs.prefix(limit))
        guard !selectedIDs.isEmpty else { return nil }
        return CourseSession(questionIDs: selectedIDs, startedAt: now)
    }

    static func submit(
        snapshot: CourseSnapshot,
        lesson: CourseLesson,
        sessionID: UUID,
        attemptID: UUID,
        optionID: String,
        now: Date
    ) throws -> CourseSnapshot {
        try snapshot.validate(against: lesson)
        guard let sessionIndex = snapshot.sessions.firstIndex(where: { $0.id == sessionID }) else {
            throw CourseEngineError.sessionNotFound
        }
        let session = snapshot.sessions[sessionIndex]

        if let existing = snapshot.attempts.first(where: { $0.id == attemptID }) {
            guard session.currentQuestionID == existing.questionID,
                  existing.sessionID == sessionID,
                  existing.selectedOptionID == optionID,
                  existing.answeredAt == now,
                  let question = lesson.question(id: existing.questionID),
                  existing.isCorrect == (question.correctOptionID == optionID) else {
                throw CourseEngineError.conflictingAttemptID
            }
            return snapshot
        }

        guard session.completedAt == nil else {
            throw CourseEngineError.sessionAlreadyCompleted
        }
        guard let questionID = session.currentQuestionID,
              let question = lesson.question(id: questionID) else {
            throw CourseEngineError.noCurrentQuestion
        }
        guard session.currentAttempt == nil else {
            throw CourseEngineError.currentQuestionAlreadyAnswered
        }
        guard let option = question.options.first(where: { $0.id == optionID }) else {
            throw CourseEngineError.optionNotFound
        }

        let isCorrect = option.id == question.correctOptionID
        let attempt = CourseAttempt(
            id: attemptID,
            sessionID: sessionID,
            questionID: questionID,
            selectedOptionID: optionID,
            isCorrect: isCorrect,
            answeredAt: now,
            isReview: snapshot.progress[questionID]?.isDue(at: now) == true
        )
        let scheduler = ReviewScheduler()
        let updatedProgress = scheduler.updatedProgress(
            itemID: questionID,
            previous: snapshot.progress[questionID],
            result: isCorrect ? .correct : .incorrect,
            reviewedAt: now
        )

        var candidate = snapshot
        candidate.progress[questionID] = updatedProgress
        candidate.attempts.append(attempt)
        candidate.sessions[sessionIndex].attempts.append(attempt)
        try candidate.validate(against: lesson)
        return candidate
    }

    static func advance(
        snapshot: CourseSnapshot,
        sessionID: UUID,
        now: Date
    ) throws -> CourseSnapshot {
        guard let sessionIndex = snapshot.sessions.firstIndex(where: { $0.id == sessionID }) else {
            throw CourseEngineError.sessionNotFound
        }
        let session = snapshot.sessions[sessionIndex]
        guard session.completedAt == nil else {
            throw CourseEngineError.sessionAlreadyCompleted
        }
        guard session.currentQuestionID != nil else {
            throw CourseEngineError.noCurrentQuestion
        }
        guard session.currentAttempt != nil else {
            throw CourseEngineError.currentQuestionNotAnswered
        }

        var candidate = snapshot
        candidate.sessions[sessionIndex].currentIndex += 1
        if candidate.sessions[sessionIndex].currentIndex == session.questionIDs.count {
            candidate.sessions[sessionIndex].completedAt = now
        }
        return candidate
    }
}
