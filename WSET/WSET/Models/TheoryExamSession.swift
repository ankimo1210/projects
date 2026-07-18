import Foundation
import SwiftData

enum TheoryExamStatus: String, Codable {
    case inProgress = "in_progress"
    case awaitingSelfAssessment = "awaiting_self_assessment"
    case completed
}

enum TheoryExamSubmissionReason: String, Codable, Equatable {
    case manual
    case timeExpired = "time_expired"

    var label: String {
        switch self {
        case .manual: "手動提出"
        case .timeExpired: "時間切れ"
        }
    }
}

@Model
final class TheoryExamSession {
    @Attribute(.unique) var id: UUID
    var startedAt: Date
    var deadline: Date
    var submittedAt: Date?
    var completedAt: Date?
    var statusRawValue: String
    var submissionReasonRawValue: String?
    var currentIndex: Int
    var multipleChoiceQuestionIDsData: Data
    var writtenQuestionIDsData: Data
    var selectedAnswersData: Data
    var writtenResponsesData: Data
    var flaggedQuestionIDsData: Data
    var rubricSelectionsData: Data
    var multipleChoiceCorrectCount: Int
    var writtenAwardedMarks: Int
    var writtenMaximumMarks: Int
    var completionRecorded: Bool

    init(
        id: UUID = UUID(),
        startedAt: Date = .now,
        durationMinutes: Int = 120,
        multipleChoiceQuestionIDs: [String],
        writtenQuestionIDs: [String]
    ) {
        self.id = id
        self.startedAt = startedAt
        deadline = startedAt.addingTimeInterval(TimeInterval(max(1, durationMinutes) * 60))
        submittedAt = nil
        completedAt = nil
        statusRawValue = TheoryExamStatus.inProgress.rawValue
        submissionReasonRawValue = nil
        currentIndex = 0
        multipleChoiceQuestionIDsData = Self.encode(multipleChoiceQuestionIDs)
        writtenQuestionIDsData = Self.encode(writtenQuestionIDs)
        selectedAnswersData = Self.encode([String: Int]())
        writtenResponsesData = Self.encode([String: String]())
        flaggedQuestionIDsData = Self.encode([String]())
        rubricSelectionsData = Self.encode([String: [String]]())
        multipleChoiceCorrectCount = 0
        writtenAwardedMarks = 0
        writtenMaximumMarks = 0
        completionRecorded = false
    }

    var status: TheoryExamStatus {
        get { TheoryExamStatus(rawValue: statusRawValue) ?? .inProgress }
        set { statusRawValue = newValue.rawValue }
    }

    var submissionReason: TheoryExamSubmissionReason? {
        get { submissionReasonRawValue.flatMap(TheoryExamSubmissionReason.init(rawValue:)) }
        set { submissionReasonRawValue = newValue?.rawValue }
    }

    var multipleChoiceQuestionIDs: [String] {
        Self.decode([String].self, from: multipleChoiceQuestionIDsData, fallback: [])
    }

    var writtenQuestionIDs: [String] {
        Self.decode([String].self, from: writtenQuestionIDsData, fallback: [])
    }

    var questionIDs: [String] {
        multipleChoiceQuestionIDs + writtenQuestionIDs
    }

    var selectedAnswers: [String: Int] {
        Self.decode([String: Int].self, from: selectedAnswersData, fallback: [:])
    }

    var writtenResponses: [String: String] {
        Self.decode([String: String].self, from: writtenResponsesData, fallback: [:])
    }

    var flaggedQuestionIDs: Set<String> {
        Set(Self.decode([String].self, from: flaggedQuestionIDsData, fallback: []))
    }

    var rubricSelections: [String: [String]] {
        Self.decode([String: [String]].self, from: rubricSelectionsData, fallback: [:])
    }

    var answeredQuestionIDs: Set<String> {
        Set(selectedAnswers.keys).union(
            writtenResponses.compactMap { key, value in
                value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? nil : key
            }
        )
    }

    var totalQuestionCount: Int { questionIDs.count }

    var totalScore: Int { multipleChoiceCorrectCount + writtenAwardedMarks }

    var maximumScore: Int { multipleChoiceQuestionIDs.count + writtenMaximumMarks }

    func remainingSeconds(at date: Date = .now) -> Int {
        guard status == .inProgress else { return 0 }
        return max(0, Int(deadline.timeIntervalSince(date).rounded(.up)))
    }

    func selectAnswer(_ choice: Int, for questionID: String) {
        var values = selectedAnswers
        values[questionID] = choice
        selectedAnswersData = Self.encode(values)
    }

    func setWrittenResponse(_ response: String, for questionID: String) {
        var values = writtenResponses
        values[questionID] = response
        writtenResponsesData = Self.encode(values)
    }

    func toggleFlag(for questionID: String) {
        var values = flaggedQuestionIDs
        if values.contains(questionID) {
            values.remove(questionID)
        } else {
            values.insert(questionID)
        }
        flaggedQuestionIDsData = Self.encode(Array(values).sorted())
    }

    func toggleRubricItem(_ itemID: String, for questionID: String) {
        var values = rubricSelections
        var selected = Set(values[questionID] ?? [])
        if selected.contains(itemID) {
            selected.remove(itemID)
        } else {
            selected.insert(itemID)
        }
        values[questionID] = Array(selected).sorted()
        rubricSelectionsData = Self.encode(values)
    }

    @discardableResult
    func applySubmission(
        _ transition: TheoryExamLifecycleTransition,
        multipleChoiceCorrectCount: Int
    ) -> Bool {
        guard status == .inProgress,
              transition.fromStatus == .inProgress,
              transition.toStatus == .awaitingSelfAssessment else { return false }
        self.multipleChoiceCorrectCount = multipleChoiceCorrectCount
        submittedAt = transition.submittedAt
        submissionReason = transition.submissionReason
        status = transition.toStatus
        currentIndex = min(currentIndex, max(0, writtenQuestionIDs.count - 1))
        return true
    }

    func beginSelfAssessment(
        multipleChoiceCorrectCount: Int,
        submissionReason: TheoryExamSubmissionReason = .manual,
        at date: Date = .now
    ) {
        let trigger: TheoryExamSubmissionTrigger = submissionReason == .manual
            ? .manual
            : .resume
        guard let transition = TheoryExamLifecycle.transition(
            status: status,
            deadline: deadline,
            now: date,
            trigger: trigger
        ), transition.submissionReason == submissionReason else { return }
        _ = applySubmission(transition, multipleChoiceCorrectCount: multipleChoiceCorrectCount)
    }

    func complete(writtenAwardedMarks: Int, writtenMaximumMarks: Int, at date: Date = .now) {
        guard status == .awaitingSelfAssessment else { return }
        self.writtenAwardedMarks = writtenAwardedMarks
        self.writtenMaximumMarks = writtenMaximumMarks
        completedAt = date
        status = .completed
    }

    private static func encode<T: Encodable>(_ value: T) -> Data {
        (try? JSONEncoder().encode(value)) ?? Data()
    }

    private static func decode<T: Decodable>(
        _ type: T.Type,
        from data: Data,
        fallback: T
    ) -> T {
        (try? JSONDecoder().decode(type, from: data)) ?? fallback
    }
}
