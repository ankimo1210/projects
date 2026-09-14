import Foundation
import XCTest
@testable import My_Tianjin

final class CourseContentTests: XCTestCase {
    func testBundledLessonHasTwentyValidatedQuestions() throws {
        let lesson = try CourseRepository(bundle: .main).loadLesson()

        XCTAssertEqual(lesson.id, "hsk3-first-lesson")
        XCTAssertEqual(lesson.contentVersion, "2026-09-15-draft1")
        XCTAssertEqual(lesson.questions.count, 20)

        let session = try XCTUnwrap(CourseEngine.makeSession(
            lesson: lesson,
            progress: [:],
            minutes: 3,
            reviewOnly: false,
            now: Date(timeIntervalSince1970: 2_000_000_000)
        ))
        let question = try XCTUnwrap(lesson.question(id: session.currentQuestionID ?? ""))
        let submitted = try CourseEngine.submit(
            snapshot: CourseSnapshot(lesson: lesson, sessions: [session]),
            lesson: lesson,
            sessionID: session.id,
            attemptID: UUID(),
            optionID: question.correctOptionID,
            now: Date(timeIntervalSince1970: 2_000_000_000)
        )
        XCTAssertEqual(submitted.activeSession?.currentAttempt?.questionID, question.id)
        XCTAssertEqual(submitted.activeSession?.currentAttempt?.isCorrect, true)
    }

    func testRepositoryLoadsAndValidatesLesson() throws {
        let expected = makeLesson()
        let data = try JSONEncoder().encode(expected)
        let repository = CourseRepository(dataLoader: { data })

        XCTAssertEqual(try repository.loadLesson(), expected)
    }

    func testRepositoryRejectsCorruptJSON() {
        let repository = CourseRepository(dataLoader: { Data("{".utf8) })

        XCTAssertThrowsError(try repository.loadLesson()) { error in
            guard case CourseRepositoryError.decodingFailed = error else {
                return XCTFail("Unexpected error: \(error)")
            }
        }
    }

    func testRepositoryRejectsInvalidCorrectAnswerReference() throws {
        let valid = makeLesson()
        var questions = valid.questions
        let first = questions[0]
        questions[0] = CourseQuestion(
            id: first.id,
            topic: first.topic,
            prompt: first.prompt,
            options: first.options,
            correctOptionID: "missing-option",
            explanation: first.explanation,
            example: first.example
        )
        let invalid = CourseLesson(
            schemaVersion: valid.schemaVersion,
            id: valid.id,
            contentVersion: valid.contentVersion,
            title: valid.title,
            subtitle: valid.subtitle,
            reviewStatus: valid.reviewStatus,
            examProfile: valid.examProfile,
            questions: questions
        )
        let data = try JSONEncoder().encode(invalid)
        let repository = CourseRepository(dataLoader: { data })

        XCTAssertThrowsError(try repository.loadLesson()) { error in
            guard case CourseRepositoryError.validationFailed = error else {
                return XCTFail("Unexpected error: \(error)")
            }
        }
    }

    func testRepositoryRejectsUnsupportedDraftProfile() throws {
        let valid = makeLesson()
        let invalid = CourseLesson(
            schemaVersion: valid.schemaVersion,
            id: valid.id,
            contentVersion: valid.contentVersion,
            title: valid.title,
            subtitle: valid.subtitle,
            reviewStatus: valid.reviewStatus,
            examProfile: CourseExamProfile(
                id: "official-exam",
                targetLevel: 3,
                syllabusStatus: "confirmed",
                note: "不正な試験プロファイル"
            ),
            questions: valid.questions
        )
        let data = try JSONEncoder().encode(invalid)
        let repository = CourseRepository(dataLoader: { data })

        XCTAssertThrowsError(try repository.loadLesson()) { error in
            guard case let CourseRepositoryError.validationFailed(validationError) = error else {
                return XCTFail("Unexpected error: \(error)")
            }
            XCTAssertEqual(validationError, .unsupportedExamProfile("official-exam"))
        }
    }
}
