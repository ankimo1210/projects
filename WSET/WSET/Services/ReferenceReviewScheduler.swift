import Foundation

enum GlossaryReviewSource: Equatable {
    case today
    case bookmarks
    case selected([String])

    var title: String {
        switch self {
        case .today:
            "今日の用語復習"
        case .bookmarks:
            "ブックマーク復習"
        case .selected:
            "用語カード"
        }
    }
}

enum GlossaryCardDirectionMode: String, CaseIterable, Identifiable {
    case mixed
    case japaneseToOriginal
    case originalToJapanese
    case summaryToTerm
    case regionToTerm

    var id: String { rawValue }

    var label: String {
        switch self {
        case .mixed: "ミックス"
        case .japaneseToOriginal: "日本語→原語"
        case .originalToJapanese: "原語→日本語"
        case .summaryToTerm: "概要→用語"
        case .regionToTerm: "産地→用語"
        }
    }
}

enum GlossaryCardDirection: Equatable {
    case japaneseToOriginal
    case originalToJapanese
    case summaryToTerm
    case regionToTerm
}

enum ReferenceReviewReason: String, CaseIterable, Identifiable, Hashable {
    case again
    case due
    case unseen

    var id: String { rawValue }

    var label: String {
        switch self {
        case .again: "もう一度・弱点"
        case .due: "復習期限"
        case .unseen: "未学習"
        }
    }
}

struct ReferenceReviewRecommendation: Identifiable, Hashable {
    let termID: String
    let reason: ReferenceReviewReason

    var id: String { termID }
}

struct ReferenceReviewPlan: Hashable {
    let recommendations: [ReferenceReviewRecommendation]

    var termIDs: [String] { recommendations.map(\.termID) }

    var reasonCounts: [ReferenceReviewReason: Int] {
        Dictionary(grouping: recommendations, by: \.reason)
            .mapValues(\.count)
    }

    var summaryText: String {
        ReferenceReviewReason.allCases.compactMap { reason in
            guard let count = reasonCounts[reason], count > 0 else { return nil }
            return "\(reason.label) \(count)語"
        }
        .joined(separator: "・")
    }
}

enum ReferenceReviewScheduler {
    static let defaultSessionLimit = 20

    static func terms(
        for source: GlossaryReviewSource,
        allTerms: [ReferenceTerm],
        progressRecords: [ReferenceTermProgress],
        at date: Date = .now,
        limit: Int = defaultSessionLimit
    ) -> [ReferenceTerm] {
        let termsByID = Dictionary(uniqueKeysWithValues: allTerms.map { ($0.id, $0) })
        return plan(
            for: source,
            allTerms: allTerms,
            progressRecords: progressRecords,
            at: date,
            limit: limit
        ).termIDs.compactMap { termsByID[$0] }
    }

    static func plan(
        for source: GlossaryReviewSource,
        allTerms: [ReferenceTerm],
        progressRecords: [ReferenceTermProgress],
        at date: Date = .now,
        limit: Int = defaultSessionLimit
    ) -> ReferenceReviewPlan {
        let progressByID = Dictionary(
            uniqueKeysWithValues: progressRecords.map { ($0.termID, $0) }
        )
        let termsByID = Dictionary(uniqueKeysWithValues: allTerms.map { ($0.id, $0) })
        let safeLimit = max(0, limit)

        switch source {
        case .today:
            // 「もう一度」は10分後を期限にするが、次に今日の学習を開いた時点から
            // 弱点として推薦し続ける。正答を記録するとこの優先枠から外れる。
            let weak = progressRecords
                .filter { $0.reviewAttemptCount > 0 && $0.lastReviewWasCorrect == false }
                .sorted { weakOrder($0, $1) }
                .compactMap { progress in
                    termsByID[progress.termID].map {
                        ReferenceReviewRecommendation(termID: $0.id, reason: .again)
                    }
                }
            let weakIDs = Set(weak.map(\.termID))
            let reviewedDue = progressRecords
                .filter {
                    $0.reviewAttemptCount > 0
                        && $0.isReviewDue(at: date)
                        && !weakIDs.contains($0.termID)
                }
                .sorted { dueOrder($0, $1) }
                .compactMap { progress in
                    termsByID[progress.termID].map {
                        ReferenceReviewRecommendation(termID: $0.id, reason: .due)
                    }
                }
            let unseen = allTerms
                .filter { progressByID[$0.id]?.reviewAttemptCount ?? 0 == 0 }
                .sorted { termOrder($0, $1) }
                .map { ReferenceReviewRecommendation(termID: $0.id, reason: .unseen) }
            return ReferenceReviewPlan(
                recommendations: Array((weak + reviewedDue + unseen).prefix(safeLimit))
            )

        case .bookmarks:
            let recommendations = allTerms
                .filter { progressByID[$0.id]?.isBookmarked == true }
                .sorted { lhs, rhs in
                    let lhsProgress = progressByID[lhs.id]
                    let rhsProgress = progressByID[rhs.id]
                    let lhsDue = lhsProgress?.isReviewDue(at: date) ?? true
                    let rhsDue = rhsProgress?.isReviewDue(at: date) ?? true
                    if lhsDue != rhsDue { return lhsDue }
                    return termOrder(lhs, rhs)
                }
                .prefix(safeLimit)
                .map { term in
                    let progress = progressByID[term.id]
                    let reason: ReferenceReviewReason
                    if progress?.lastReviewWasCorrect == false {
                        reason = .again
                    } else if progress?.isReviewDue(at: date) ?? true {
                        reason = .due
                    } else {
                        reason = .unseen
                    }
                    return ReferenceReviewRecommendation(termID: term.id, reason: reason)
                }
            return ReferenceReviewPlan(recommendations: recommendations)

        case let .selected(ids):
            return ReferenceReviewPlan(
                recommendations: ids
                    .prefix(safeLimit)
                    .compactMap { id in
                        termsByID[id].map {
                            ReferenceReviewRecommendation(termID: $0.id, reason: .due)
                        }
                    }
            )
        }
    }

    static func direction(
        for term: ReferenceTerm,
        index: Int,
        mode: GlossaryCardDirectionMode
    ) -> GlossaryCardDirection {
        switch mode {
        case .japaneseToOriginal:
            return .japaneseToOriginal
        case .originalToJapanese:
            return term.originalDisplayName == nil ? .japaneseToOriginal : .originalToJapanese
        case .summaryToTerm:
            return term.summary.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                ? .japaneseToOriginal
                : .summaryToTerm
        case .regionToTerm:
            return term.regionDisplayName == nil ? .japaneseToOriginal : .regionToTerm
        case .mixed:
            var available: [GlossaryCardDirection] = [.japaneseToOriginal]
            if term.originalDisplayName != nil { available.append(.originalToJapanese) }
            if !term.summary.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                available.append(.summaryToTerm)
            }
            if term.regionDisplayName != nil { available.append(.regionToTerm) }
            return available[index % available.count]
        }
    }

    private static func weakOrder(
        _ lhs: ReferenceTermProgress,
        _ rhs: ReferenceTermProgress
    ) -> Bool {
        let lhsAccuracy = lhs.reviewAccuracy ?? 1
        let rhsAccuracy = rhs.reviewAccuracy ?? 1
        if lhsAccuracy != rhsAccuracy { return lhsAccuracy < rhsAccuracy }
        let lhsReviewed = lhs.lastReviewedAt ?? .distantPast
        let rhsReviewed = rhs.lastReviewedAt ?? .distantPast
        if lhsReviewed != rhsReviewed { return lhsReviewed < rhsReviewed }
        return lhs.termID < rhs.termID
    }

    private static func dueOrder(
        _ lhs: ReferenceTermProgress,
        _ rhs: ReferenceTermProgress
    ) -> Bool {
        let lhsDue = lhs.reviewDueDate ?? .distantPast
        let rhsDue = rhs.reviewDueDate ?? .distantPast
        if lhsDue != rhsDue { return lhsDue < rhsDue }
        return lhs.termID < rhs.termID
    }

    private static func termOrder(_ lhs: ReferenceTerm, _ rhs: ReferenceTerm) -> Bool {
        lhs.nameJapanese.localizedStandardCompare(rhs.nameJapanese) == .orderedAscending
    }
}

extension ReferenceTerm {
    var originalNames: [String] {
        var values: [String] = []
        for candidate in [nameFrench, nameEnglish] + aliases.map(Optional.some) {
            guard let candidate,
                  !candidate.isEmpty,
                  candidate != nameJapanese,
                  !values.contains(candidate)
            else { continue }
            values.append(candidate)
        }
        return values
    }

    var originalDisplayName: String? {
        originalNames.first
    }

    var regionDisplayName: String? {
        let values = [country, region]
            .compactMap { value -> String? in
                guard let value = value?.trimmingCharacters(in: .whitespacesAndNewlines),
                      !value.isEmpty
                else { return nil }
                return value
            }
        guard !values.isEmpty else { return nil }
        return values.joined(separator: "・")
    }
}
