import XCTest
@testable import WSET

final class FeatureAccessPolicyTests: XCTestCase {
    func testSafetyAndPortabilityFeaturesAreNeverPaywalled() {
        let policy = FeatureAccessPolicy(hasProAccess: false)
        XCTAssertTrue(policy.canAccess(.backupAndRestore))
        XCTAssertTrue(policy.canAccess(.purchaseRestore))
    }

    func testPremiumSurfacesRequireEntitlement() {
        let free = FeatureAccessPolicy(hasProAccess: false)
        let pro = FeatureAccessPolicy(hasProAccess: true)

        for feature in PremiumFeature.allCases
            where ![.backupAndRestore, .purchaseRestore].contains(feature) {
            XCTAssertFalse(free.canAccess(feature), "\(feature) should be locked")
            XCTAssertTrue(pro.canAccess(feature), "\(feature) should be unlocked")
        }
    }

    func testFreeContentUsesStableManifestIdentifiers() throws {
        let manifest = FreeContentManifest(
            schemaVersion: 1,
            selectionVersion: "test",
            multipleChoiceQuestionIDs: ["free-mcq"],
            writtenQuestionIDs: ["free-written"],
            glossaryTermIDs: ["free-term"],
            mapCountries: ["フランス"]
        )
        let policy = FeatureAccessPolicy(hasProAccess: false, freeContentManifest: manifest)
        XCTAssertTrue(policy.canAccessQuestion(id: "free-mcq", studyMode: "multiple_choice"))
        XCTAssertFalse(policy.canAccessQuestion(id: "paid-mcq", studyMode: "multiple_choice"))
        XCTAssertTrue(policy.canAccessQuestion(id: "free-written", studyMode: "written_answer"))
        XCTAssertFalse(policy.canAccessQuestion(id: "paid-written", studyMode: "written_answer"))
        XCTAssertTrue(policy.canAccessGlossaryTerm(id: "free-term"))
        XCTAssertFalse(policy.canAccessGlossaryTerm(id: "paid-term"))
        XCTAssertTrue(policy.canCreateTastingNote(existingCount: 2))
        XCTAssertFalse(policy.canCreateTastingNote(existingCount: 3))
    }

    func testBundledFreeManifestHasExpectedStableCounts() throws {
        let manifest = try FreeContentManifest.load()
        XCTAssertEqual(manifest.multipleChoiceQuestionIDs.count, 100)
        XCTAssertEqual(manifest.writtenQuestionIDs.count, 1)
        XCTAssertEqual(manifest.glossaryTermIDs.count, 60)
        XCTAssertEqual(manifest.selectionVersion, "2026-07-19")
    }

    func testFranceMapIsTheFreeMapExperience() {
        let free = FeatureAccessPolicy(hasProAccess: false)
        XCTAssertTrue(free.canAccessRegionMap(country: "France"))
        XCTAssertTrue(free.canAccessRegionMap(country: "フランス"))
        XCTAssertFalse(free.canAccessRegionMap(country: "イタリア"))
        XCTAssertTrue(FeatureAccessPolicy(hasProAccess: true).canAccessRegionMap(country: "イタリア"))
    }

    func testMiniMockQuestionCountMatchesEntitlement() {
        XCTAssertEqual(
            FeatureAccessPolicy(hasProAccess: false).miniMockQuestionCount,
            FeatureAccessPolicy.freeMiniMockQuestionCount
        )
        XCTAssertEqual(FeatureAccessPolicy.freeMiniMockQuestionCount, 20)
        XCTAssertEqual(
            FeatureAccessPolicy(hasProAccess: true).miniMockQuestionCount,
            FeatureAccessPolicy.proMiniMockQuestionCount
        )
        XCTAssertEqual(FeatureAccessPolicy.proMiniMockQuestionCount, 50)
    }

    func testRecordedHistoryRemainsReadableWithoutUnlockingUnrecordedPaidContent() {
        let recordedIDs: Set<String> = ["paid-question-with-history"]

        XCTAssertTrue(
            FeatureAccessPolicy.canReadHistoricalQuestion(
                id: "paid-question-with-history",
                recordedQuestionIDs: recordedIDs
            )
        )
        XCTAssertFalse(
            FeatureAccessPolicy.canReadHistoricalQuestion(
                id: "unrecorded-paid-question",
                recordedQuestionIDs: recordedIDs
            )
        )
    }

    func testCompletedTheoryExamRemainsReadableAfterEntitlementLoss() {
        let free = FeatureAccessPolicy(hasProAccess: false)
        XCTAssertTrue(free.canOpenTheoryExam(status: .completed))
        XCTAssertFalse(free.canOpenTheoryExam(status: .inProgress))
        XCTAssertFalse(free.canOpenTheoryExam(status: .awaitingSelfAssessment))

        let pro = FeatureAccessPolicy(hasProAccess: true)
        XCTAssertTrue(pro.canOpenTheoryExam(status: .inProgress))
        XCTAssertTrue(pro.canOpenTheoryExam(status: .awaitingSelfAssessment))
    }
}
