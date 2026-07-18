import Foundation
import SwiftData

struct ReferenceTermProgressBackup: Codable, Equatable {
    let termID: String
    let isBookmarked: Bool
    let lastViewedAt: Date?
    let viewCount: Int
    let reviewDueDate: Date?
    let reviewIntervalDays: Int
    let reviewAttemptCount: Int
    let reviewCorrectCount: Int
    let lastReviewedAt: Date?
    let lastReviewWasCorrect: Bool?

    init(
        termID: String,
        isBookmarked: Bool,
        lastViewedAt: Date?,
        viewCount: Int,
        reviewDueDate: Date?,
        reviewIntervalDays: Int,
        reviewAttemptCount: Int,
        reviewCorrectCount: Int,
        lastReviewedAt: Date?,
        lastReviewWasCorrect: Bool?
    ) {
        self.termID = termID
        self.isBookmarked = isBookmarked
        self.lastViewedAt = lastViewedAt
        self.viewCount = viewCount
        self.reviewDueDate = reviewDueDate
        self.reviewIntervalDays = reviewIntervalDays
        self.reviewAttemptCount = reviewAttemptCount
        self.reviewCorrectCount = reviewCorrectCount
        self.lastReviewedAt = lastReviewedAt
        self.lastReviewWasCorrect = lastReviewWasCorrect
    }

    init(progress: ReferenceTermProgress) {
        termID = progress.termID
        isBookmarked = progress.isBookmarked
        lastViewedAt = progress.lastViewedAt
        viewCount = progress.viewCount
        reviewDueDate = progress.reviewDueDate
        reviewIntervalDays = progress.reviewIntervalDays
        reviewAttemptCount = progress.reviewAttemptCount
        reviewCorrectCount = progress.reviewCorrectCount
        lastReviewedAt = progress.lastReviewedAt
        lastReviewWasCorrect = progress.lastReviewWasCorrect
    }
}

@MainActor
enum R5BackupSupport {
    static func snapshots(
        in context: ModelContext,
        termIDMigrations: [String: String] = [:]
    ) -> [ReferenceTermProgressBackup] {
        guard let records = try? context.fetch(FetchDescriptor<ReferenceTermProgress>()) else {
            return []
        }
        guard isValid(termIDMigrations) else { return [] }
        return consolidated(
            records.map(ReferenceTermProgressBackup.init(progress:)),
            termIDMigrations: termIDMigrations
        )
    }

    @discardableResult
    static func migrateTermIDs(
        _ migrations: [String: String],
        in context: ModelContext
    ) throws -> Int {
        guard !migrations.isEmpty else { return 0 }
        guard isValid(migrations) else {
            throw CocoaError(.fileReadCorruptFile)
        }

        var progressByID = Dictionary(
            uniqueKeysWithValues: try context.fetch(FetchDescriptor<ReferenceTermProgress>()).map {
                ($0.termID, $0)
            }
        )
        var migratedCount = 0
        for retiredID in migrations.keys.sorted() {
            guard let progress = progressByID[retiredID],
                  let canonicalID = migrations[retiredID]
            else { continue }

            if let canonical = progressByID[canonicalID] {
                merge(progress, into: canonical)
                context.delete(progress)
            } else {
                progress.termID = canonicalID
                progressByID[canonicalID] = progress
            }
            progressByID.removeValue(forKey: retiredID)
            migratedCount += 1
        }
        return migratedCount
    }

    @discardableResult
    static func restore(
        _ snapshots: [ReferenceTermProgressBackup],
        into context: ModelContext,
        termIDMigrations: [String: String] = [:]
    ) throws -> Int {
        guard isValid(termIDMigrations) else {
            throw CocoaError(.fileReadCorruptFile)
        }
        _ = try migrateTermIDs(termIDMigrations, in: context)
        let canonicalSnapshots = consolidated(
            snapshots,
            termIDMigrations: termIDMigrations
        )
        guard !canonicalSnapshots.isEmpty else { return 0 }
        var progressByID = Dictionary(
            uniqueKeysWithValues: try context.fetch(FetchDescriptor<ReferenceTermProgress>()).map {
                ($0.termID, $0)
            }
        )

        for snapshot in canonicalSnapshots {
            let existing = progressByID[snapshot.termID]
            let progress = existing ?? ReferenceTermProgress(termID: snapshot.termID)
            if existing == nil {
                context.insert(progress)
                progressByID[snapshot.termID] = progress
            }

            progress.isBookmarked = progress.isBookmarked || snapshot.isBookmarked
            let snapshotViewedAt = snapshot.lastViewedAt ?? .distantPast
            let localViewedAt = progress.lastViewedAt ?? .distantPast
            if snapshotViewedAt >= localViewedAt {
                progress.lastViewedAt = snapshot.lastViewedAt
                progress.viewCount = snapshot.viewCount
            }

            let snapshotReviewedAt = snapshot.lastReviewedAt ?? .distantPast
            let localReviewedAt = progress.lastReviewedAt ?? .distantPast
            if snapshotReviewedAt >= localReviewedAt {
                progress.reviewDueDate = snapshot.reviewDueDate
                progress.reviewIntervalDays = snapshot.reviewIntervalDays
                progress.reviewAttemptCount = snapshot.reviewAttemptCount
                progress.reviewCorrectCount = snapshot.reviewCorrectCount
                progress.lastReviewedAt = snapshot.lastReviewedAt
                progress.lastReviewWasCorrect = snapshot.lastReviewWasCorrect
            }
        }

        return canonicalSnapshots.count
    }

    private static func isValid(_ migrations: [String: String]) -> Bool {
        let sources = Set(migrations.keys)
        return migrations.allSatisfy { !$0.key.isEmpty && !$0.value.isEmpty && $0.key != $0.value }
            && sources.isDisjoint(with: Set(migrations.values))
    }

    private static func merge(
        _ retired: ReferenceTermProgress,
        into canonical: ReferenceTermProgress
    ) {
        canonical.isBookmarked = canonical.isBookmarked || retired.isBookmarked
        canonical.viewCount += retired.viewCount
        if (retired.lastViewedAt ?? .distantPast) > (canonical.lastViewedAt ?? .distantPast) {
            canonical.lastViewedAt = retired.lastViewedAt
        }

        canonical.reviewAttemptCount += retired.reviewAttemptCount
        canonical.reviewCorrectCount += retired.reviewCorrectCount
        if (retired.lastReviewedAt ?? .distantPast) > (canonical.lastReviewedAt ?? .distantPast) {
            canonical.reviewDueDate = retired.reviewDueDate
            canonical.reviewIntervalDays = retired.reviewIntervalDays
            canonical.lastReviewedAt = retired.lastReviewedAt
            canonical.lastReviewWasCorrect = retired.lastReviewWasCorrect
        }
    }

    private static func consolidated(
        _ snapshots: [ReferenceTermProgressBackup],
        termIDMigrations: [String: String]
    ) -> [ReferenceTermProgressBackup] {
        var latestByOriginalID: [String: ReferenceTermProgressBackup] = [:]
        for snapshot in snapshots {
            if let existing = latestByOriginalID[snapshot.termID] {
                latestByOriginalID[snapshot.termID] = preferred(snapshot, over: existing)
            } else {
                latestByOriginalID[snapshot.termID] = snapshot
            }
        }

        let grouped = Dictionary(grouping: latestByOriginalID.values) { snapshot in
            termIDMigrations[snapshot.termID] ?? snapshot.termID
        }
        return grouped.map { canonicalID, values in
            values.reduce(nil as ReferenceTermProgressBackup?) { result, snapshot in
                guard let result else {
                    return replacingTermID(of: snapshot, with: canonicalID)
                }
                return merging(snapshot, into: result, canonicalID: canonicalID)
            }!
        }
        .sorted { $0.termID < $1.termID }
    }

    private static func preferred(
        _ candidate: ReferenceTermProgressBackup,
        over existing: ReferenceTermProgressBackup
    ) -> ReferenceTermProgressBackup {
        let candidateDate = max(
            candidate.lastReviewedAt ?? .distantPast,
            candidate.lastViewedAt ?? .distantPast
        )
        let existingDate = max(
            existing.lastReviewedAt ?? .distantPast,
            existing.lastViewedAt ?? .distantPast
        )
        return candidateDate >= existingDate ? candidate : existing
    }

    private static func replacingTermID(
        of snapshot: ReferenceTermProgressBackup,
        with termID: String
    ) -> ReferenceTermProgressBackup {
        ReferenceTermProgressBackup(
            termID: termID,
            isBookmarked: snapshot.isBookmarked,
            lastViewedAt: snapshot.lastViewedAt,
            viewCount: snapshot.viewCount,
            reviewDueDate: snapshot.reviewDueDate,
            reviewIntervalDays: snapshot.reviewIntervalDays,
            reviewAttemptCount: snapshot.reviewAttemptCount,
            reviewCorrectCount: snapshot.reviewCorrectCount,
            lastReviewedAt: snapshot.lastReviewedAt,
            lastReviewWasCorrect: snapshot.lastReviewWasCorrect
        )
    }

    private static func merging(
        _ source: ReferenceTermProgressBackup,
        into target: ReferenceTermProgressBackup,
        canonicalID: String
    ) -> ReferenceTermProgressBackup {
        let sourceHasNewerReview = (source.lastReviewedAt ?? .distantPast)
            > (target.lastReviewedAt ?? .distantPast)
        let schedule = sourceHasNewerReview ? source : target
        let lastViewedAt = max(
            source.lastViewedAt ?? .distantPast,
            target.lastViewedAt ?? .distantPast
        )
        return ReferenceTermProgressBackup(
            termID: canonicalID,
            isBookmarked: source.isBookmarked || target.isBookmarked,
            lastViewedAt: lastViewedAt == .distantPast ? nil : lastViewedAt,
            viewCount: source.viewCount + target.viewCount,
            reviewDueDate: schedule.reviewDueDate,
            reviewIntervalDays: schedule.reviewIntervalDays,
            reviewAttemptCount: source.reviewAttemptCount + target.reviewAttemptCount,
            reviewCorrectCount: source.reviewCorrectCount + target.reviewCorrectCount,
            lastReviewedAt: schedule.lastReviewedAt,
            lastReviewWasCorrect: schedule.lastReviewWasCorrect
        )
    }
}
