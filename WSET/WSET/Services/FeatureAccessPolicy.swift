import Foundation

enum PremiumFeature: String, CaseIterable, Identifiable {
    case fullQuestionBank
    case fullWrittenPractice
    case theoryExam
    case adaptiveStudy
    case detailedStatistics
    case fullRegionMaps
    case regionComparison
    case fullGlossary
    case glossarySRS
    case unlimitedTastingNotes
    case backupAndRestore
    case purchaseRestore

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .fullQuestionBank: "追加の四択問題"
        case .fullWrittenPractice: "追加の記述式練習"
        case .theoryExam: "理論模擬試験"
        case .adaptiveStudy: "今日の重点学習"
        case .detailedStatistics: "詳細弱点分析"
        case .fullRegionMaps: "追加産地マップ（収録時）"
        case .regionComparison: "産地比較"
        case .fullGlossary: "全用語"
        case .glossarySRS: "用語の期限復習"
        case .unlimitedTastingNotes: "テイスティング記録無制限"
        case .backupAndRestore: "バックアップ・復元"
        case .purchaseRestore: "購入の復元"
        }
    }
}

struct FeatureAccessPolicy: Equatable {
    static let freeMultipleChoiceLimit = 100
    static let freeGlossaryLimit = 60
    static let freeWrittenLimit = 1
    static let freeTastingNoteLimit = 3
    static let freeMiniMockQuestionCount = 20
    static let proMiniMockQuestionCount = 50

    let hasProAccess: Bool
    var freeContentManifest: FreeContentManifest = .shared

    var miniMockQuestionCount: Int {
        hasProAccess ? Self.proMiniMockQuestionCount : Self.freeMiniMockQuestionCount
    }

    func canAccess(_ feature: PremiumFeature) -> Bool {
        switch feature {
        case .backupAndRestore, .purchaseRestore:
            true
        default:
            hasProAccess
        }
    }

    func canAccessQuestion(id: String, studyMode: String) -> Bool {
        hasProAccess || freeContentManifest.containsQuestion(id: id, studyMode: studyMode)
    }

    func canAccessGlossaryTerm(id: String) -> Bool {
        hasProAccess || freeContentManifest.glossaryTermIDSet.contains(id)
    }

    func canCreateTastingNote(existingCount: Int) -> Bool {
        return hasProAccess || existingCount < Self.freeTastingNoteLimit
    }

    func canAccessRegionMap(country: String) -> Bool {
        return hasProAccess
            || freeContentManifest.normalizedMapCountries.contains(
                GeographyNormalizer.normalizeCountry(country)
            )
    }

    /// Paid content cannot be started after entitlement loss, but a question that
    /// belongs to the user's own recorded history remains readable.
    static func canReadHistoricalQuestion(
        id: String,
        recordedQuestionIDs: Set<String>
    ) -> Bool {
        recordedQuestionIDs.contains(id)
    }

    /// Completed exam results are user data. In-progress exam work still requires
    /// Pro because opening it continues the paid learning activity.
    func canOpenTheoryExam(status: TheoryExamStatus) -> Bool {
        hasProAccess || status == .completed
    }
}
