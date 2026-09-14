import Foundation

nonisolated enum CourseValidationError: Error, Equatable, LocalizedError, Sendable {
    case unsupportedSchemaVersion(Int)
    case unsupportedCourseID(String)
    case unsupportedReviewStatus(String)
    case unsupportedExamProfile(String)
    case invalidValue(path: String, reason: String)
    case incompatibleSnapshot(reason: String)

    var errorDescription: String? {
        switch self {
        case let .unsupportedSchemaVersion(version):
            "未対応のコーススキーマです: \(version)"
        case let .unsupportedCourseID(id):
            "未対応のコースです: \(id)"
        case let .unsupportedReviewStatus(status):
            "未対応の監修状態です: \(status)"
        case let .unsupportedExamProfile(profile):
            "未対応の試験プロファイルです: \(profile)"
        case let .invalidValue(path, reason):
            "コース内容が不正です（\(path): \(reason)）"
        case let .incompatibleSnapshot(reason):
            "保存済みコースを再開できません（\(reason)）"
        }
    }
}

nonisolated struct CourseExamProfile: Codable, Equatable, Sendable {
    let id: String
    let targetLevel: Int
    let syllabusStatus: String
    let note: String
}

nonisolated struct CourseExample: Codable, Equatable, Sendable {
    let hanzi: String
    let pinyin: String
    let japanese: String
}

nonisolated struct CourseOption: Codable, Equatable, Identifiable, Sendable {
    let id: String
    let text: String
    let explanation: String
}

nonisolated struct CourseQuestion: Codable, Equatable, Identifiable, Sendable {
    let id: String
    let topic: String
    let prompt: String
    let options: [CourseOption]
    let correctOptionID: String
    let explanation: String
    let example: CourseExample
}

nonisolated struct CourseLesson: Codable, Equatable, Identifiable, Sendable {
    static let supportedSchemaVersion = 1
    static let supportedID = "hsk3-first-lesson"
    static let supportedReviewStatus = "draft"
    static let supportedExamProfileID = "hsk3-prototype-unconfirmed"

    let schemaVersion: Int
    let id: String
    let contentVersion: String
    let title: String
    let subtitle: String
    let reviewStatus: String
    let examProfile: CourseExamProfile
    let questions: [CourseQuestion]

    func question(id: String) -> CourseQuestion? {
        questions.first { $0.id == id }
    }

    func validate() throws {
        guard schemaVersion == Self.supportedSchemaVersion else {
            throw CourseValidationError.unsupportedSchemaVersion(schemaVersion)
        }
        guard id == Self.supportedID else {
            throw CourseValidationError.unsupportedCourseID(id)
        }
        guard reviewStatus == Self.supportedReviewStatus else {
            throw CourseValidationError.unsupportedReviewStatus(reviewStatus)
        }
        guard examProfile.id == Self.supportedExamProfileID,
              examProfile.targetLevel == 3,
              examProfile.syllabusStatus == "unconfirmed" else {
            throw CourseValidationError.unsupportedExamProfile(examProfile.id)
        }

        try requireText(contentVersion, path: "contentVersion")
        try requireText(title, path: "title")
        try requireText(subtitle, path: "subtitle")
        try requireText(examProfile.note, path: "examProfile.note")
        guard !questions.isEmpty else {
            throw CourseValidationError.invalidValue(
                path: "questions",
                reason: "1問以上必要です"
            )
        }

        var questionIDs = Set<String>()
        for (questionIndex, question) in questions.enumerated() {
            let path = "questions[\(questionIndex)]"
            try requireText(question.id, path: "\(path).id")
            guard questionIDs.insert(question.id).inserted else {
                throw CourseValidationError.invalidValue(
                    path: "\(path).id",
                    reason: "問題IDが重複しています"
                )
            }
            guard question.topic == "time" || question.topic == "place" else {
                throw CourseValidationError.invalidValue(
                    path: "\(path).topic",
                    reason: "time または place が必要です"
                )
            }
            try requireText(question.prompt, path: "\(path).prompt")
            try requireText(question.correctOptionID, path: "\(path).correctOptionID")
            try requireText(question.explanation, path: "\(path).explanation")
            try requireText(question.example.hanzi, path: "\(path).example.hanzi")
            try requireText(question.example.pinyin, path: "\(path).example.pinyin")
            try requireText(question.example.japanese, path: "\(path).example.japanese")

            guard question.options.count == 3 else {
                throw CourseValidationError.invalidValue(
                    path: "\(path).options",
                    reason: "選択肢は3件必要です"
                )
            }
            var localOptionIDs = Set<String>()
            var optionTexts = Set<String>()
            for (optionIndex, option) in question.options.enumerated() {
                let optionPath = "\(path).options[\(optionIndex)]"
                try requireText(option.id, path: "\(optionPath).id")
                try requireText(option.text, path: "\(optionPath).text")
                try requireText(option.explanation, path: "\(optionPath).explanation")
                guard localOptionIDs.insert(option.id).inserted else {
                    throw CourseValidationError.invalidValue(
                        path: "\(optionPath).id",
                        reason: "選択肢IDが重複しています"
                    )
                }
                guard optionTexts.insert(option.text).inserted else {
                    throw CourseValidationError.invalidValue(
                        path: "\(optionPath).text",
                        reason: "選択肢の文が重複しています"
                    )
                }
            }
            guard localOptionIDs.contains(question.correctOptionID) else {
                throw CourseValidationError.invalidValue(
                    path: "\(path).correctOptionID",
                    reason: "正答IDに対応する選択肢がありません"
                )
            }
        }
    }
}

nonisolated struct CourseAttempt: Codable, Equatable, Identifiable, Sendable {
    let id: UUID
    let sessionID: UUID
    let questionID: String
    let selectedOptionID: String
    let isCorrect: Bool
    let answeredAt: Date
    let isReview: Bool
}

nonisolated struct CourseSession: Codable, Equatable, Identifiable, Sendable {
    let id: UUID
    let questionIDs: [String]
    var currentIndex: Int
    let startedAt: Date
    var completedAt: Date?
    var attempts: [CourseAttempt]

    init(
        id: UUID = UUID(),
        questionIDs: [String],
        currentIndex: Int = 0,
        startedAt: Date,
        completedAt: Date? = nil,
        attempts: [CourseAttempt] = []
    ) {
        self.id = id
        self.questionIDs = questionIDs
        self.currentIndex = currentIndex
        self.startedAt = startedAt
        self.completedAt = completedAt
        self.attempts = attempts
    }

    var currentQuestionID: String? {
        guard completedAt == nil, questionIDs.indices.contains(currentIndex) else { return nil }
        return questionIDs[currentIndex]
    }

    var currentAttempt: CourseAttempt? {
        guard let currentQuestionID else { return nil }
        return attempts.first { $0.questionID == currentQuestionID }
    }

    var correctCount: Int {
        attempts.lazy.filter(\.isCorrect).count
    }
}

nonisolated struct CourseSnapshot: Codable, Equatable, Sendable {
    static let supportedSchemaVersion = 1

    let schemaVersion: Int
    let courseID: String
    let contentVersion: String
    var progress: [String: StudyItemProgress]
    var attempts: [CourseAttempt]
    var sessions: [CourseSession]

    init(
        schemaVersion: Int = Self.supportedSchemaVersion,
        courseID: String,
        contentVersion: String,
        progress: [String: StudyItemProgress] = [:],
        attempts: [CourseAttempt] = [],
        sessions: [CourseSession] = []
    ) {
        self.schemaVersion = schemaVersion
        self.courseID = courseID
        self.contentVersion = contentVersion
        self.progress = progress
        self.attempts = attempts
        self.sessions = sessions
    }

    init(
        lesson: CourseLesson,
        progress: [String: StudyItemProgress] = [:],
        attempts: [CourseAttempt] = [],
        sessions: [CourseSession] = []
    ) {
        self.init(
            courseID: lesson.id,
            contentVersion: lesson.contentVersion,
            progress: progress,
            attempts: attempts,
            sessions: sessions
        )
    }

    var activeSession: CourseSession? {
        sessions.last { $0.completedAt == nil }
    }

    func validate(against lesson: CourseLesson) throws {
        guard schemaVersion == Self.supportedSchemaVersion else {
            throw CourseValidationError.incompatibleSnapshot(reason: "スキーマの版が異なります")
        }
        guard courseID == lesson.id else {
            throw CourseValidationError.incompatibleSnapshot(reason: "コースIDが異なります")
        }
        guard contentVersion == lesson.contentVersion else {
            throw CourseValidationError.incompatibleSnapshot(reason: "教材の版が異なります")
        }

        let lessonQuestionIDs = Set(lesson.questions.map(\.id))
        for (key, value) in progress {
            guard lessonQuestionIDs.contains(key), value.itemID == key else {
                throw CourseValidationError.incompatibleSnapshot(reason: "進捗に対象外の問題があります")
            }
            guard value.attemptCount >= 0,
                  value.correctCount >= 0,
                  value.incorrectCount >= 0,
                  value.currentStreak >= 0,
                  value.reviewStage >= 0,
                  value.attemptCount == value.correctCount + value.incorrectCount else {
                throw CourseValidationError.incompatibleSnapshot(reason: "進捗の集計が不正です")
            }
        }

        let sessionIDs = sessions.map(\.id)
        guard Set(sessionIDs).count == sessionIDs.count else {
            throw CourseValidationError.incompatibleSnapshot(reason: "セッションIDが重複しています")
        }
        guard sessions.filter({ $0.completedAt == nil }).count <= 1 else {
            throw CourseValidationError.incompatibleSnapshot(reason: "進行中のセッションが複数あります")
        }

        var flattenedAttempts: [CourseAttempt] = []
        for session in sessions {
            guard !session.questionIDs.isEmpty,
                  session.questionIDs.count <= 10,
                  Set(session.questionIDs).count == session.questionIDs.count,
                  session.questionIDs.allSatisfy({ lessonQuestionIDs.contains($0) }) else {
                throw CourseValidationError.incompatibleSnapshot(reason: "セッションの問題一覧が不正です")
            }
            guard (0...session.questionIDs.count).contains(session.currentIndex) else {
                throw CourseValidationError.incompatibleSnapshot(reason: "現在位置が範囲外です")
            }
            if session.completedAt == nil {
                guard session.currentIndex < session.questionIDs.count,
                      session.attempts.count == session.currentIndex
                        || session.attempts.count == session.currentIndex + 1 else {
                    throw CourseValidationError.incompatibleSnapshot(reason: "進行中セッションの回答数が不正です")
                }
            } else {
                guard session.currentIndex == session.questionIDs.count,
                      session.attempts.count == session.questionIDs.count else {
                    throw CourseValidationError.incompatibleSnapshot(reason: "完了セッションの回答数が不正です")
                }
            }

            for (index, attempt) in session.attempts.enumerated() {
                guard attempt.sessionID == session.id,
                      index < session.questionIDs.count,
                      attempt.questionID == session.questionIDs[index],
                      let question = lesson.question(id: attempt.questionID),
                      let option = question.options.first(where: { $0.id == attempt.selectedOptionID }),
                      attempt.isCorrect == (option.id == question.correctOptionID) else {
                    throw CourseValidationError.incompatibleSnapshot(reason: "回答データが問題と一致しません")
                }
            }
            flattenedAttempts.append(contentsOf: session.attempts)
        }

        let attemptIDs = attempts.map(\.id)
        guard Set(attemptIDs).count == attemptIDs.count,
              attempts == flattenedAttempts else {
            throw CourseValidationError.incompatibleSnapshot(reason: "回答履歴が一致しません")
        }
    }
}

nonisolated private func requireText(_ value: String, path: String) throws {
    guard !value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
        throw CourseValidationError.invalidValue(path: path, reason: "空文字は使用できません")
    }
}
