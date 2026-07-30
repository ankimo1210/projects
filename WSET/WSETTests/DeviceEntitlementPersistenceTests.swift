import StoreKit
import StoreKitTest
import SwiftData
import XCTest
@testable import WSET

/// Device-only counterparts to the mocked entitlement tests: these use the real
/// Keychain, a real StoreKit purchase and an on-disk SwiftData store, so they cover the
/// parts that in-memory doubles cannot (hardware Keychain access, file persistence).
@MainActor
final class DeviceEntitlementPersistenceTests: XCTestCase {
    private var session: SKTestSession!

    override func setUpWithError() throws {
        continueAfterFailure = false
        #if targetEnvironment(simulator)
        throw XCTSkip("SKTestSessionはSimulatorで動作しないため実機のみで実行する")
        #endif
        session = try SKTestSession(configurationFileNamed: "Configuration")
        session.resetToDefaultState()
        session.clearTransactions()
        session.disableDialogs = true
    }

    override func tearDown() {
        session?.clearTransactions()
        session = nil
        // Never leave a synthetic Pro right behind on the developer's own device.
        KeychainProEntitlementCache().save(false)
    }

    /// Offline launch: the app must keep a previously verified right when StoreKit
    /// cannot be reached, and that right has to survive in the device Keychain.
    func testVerifiedRightSurvivesInKeychainAndUnlocksProOffline() async throws {
        let cache = KeychainProEntitlementCache()
        cache.save(false)
        XCTAssertFalse(cache.load())

        let store = EntitlementStore(
            commerce: StoreKitEntitlementCommerce(),
            cache: cache,
            processArguments: []
        )
        await store.prepare()
        let purchased = try await store.purchase()
        XCTAssertEqual(purchased, .purchased)
        XCTAssertTrue(cache.load(), "検証済み権利が実機Keychainに永続すること")

        // A fresh store reading the same Keychain models the next launch with no network.
        let offline = EntitlementStore(
            commerce: UnreachableStoreCommerce(),
            cache: KeychainProEntitlementCache(),
            processArguments: []
        )
        XCTAssertEqual(offline.status, .proCached, "起動直後からキャッシュ済み権利を認めること")

        await offline.prepare()

        XCTAssertEqual(offline.status, .proCached)
        XCTAssertTrue(offline.hasProAccess)
        XCTAssertEqual(offline.productLoadStatus, .unavailable)
    }

    /// Offline launch without a prior purchase must not invent a right.
    func testOfflineLaunchWithoutPriorPurchaseStaysLocked() async {
        KeychainProEntitlementCache().save(false)

        let offline = EntitlementStore(
            commerce: UnreachableStoreCommerce(),
            cache: KeychainProEntitlementCache(),
            processArguments: []
        )
        await offline.prepare()

        XCTAssertFalse(offline.hasProAccess)
        XCTAssertEqual(offline.status, .unavailable("購入権利を確認できません。"))
    }

    /// Free-tier progress written to disk must still be there after a real purchase.
    func testFreeUserProgressOnDiskSurvivesRealPurchase() async throws {
        let storeURL = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent("progress-\(UUID().uuidString).store")
        addTeardownBlock { try? FileManager.default.removeItem(at: storeURL) }

        let studiedAt = Date(timeIntervalSince1970: 1_700_000_000)
        let container = try ModelContainer(
            for: QuestionProgress.self,
            configurations: ModelConfiguration(url: storeURL)
        )
        let progress = QuestionProgress(questionID: "free-question")
        progress.isBookmarked = true
        progress.record(isCorrect: true, rating: 3, at: studiedAt)
        container.mainContext.insert(progress)
        try container.mainContext.save()

        let entitlements = EntitlementStore(
            commerce: StoreKitEntitlementCommerce(),
            cache: KeychainProEntitlementCache(),
            processArguments: []
        )
        await entitlements.prepare()
        let purchased = try await entitlements.purchase()
        XCTAssertEqual(purchased, .purchased)
        XCTAssertTrue(entitlements.hasProAccess)

        // Reopen from disk so the assertion cannot pass on in-memory state alone.
        let reopened = try ModelContainer(
            for: QuestionProgress.self,
            configurations: ModelConfiguration(url: storeURL)
        )
        let restored = try XCTUnwrap(
            reopened.mainContext.fetch(FetchDescriptor<QuestionProgress>()).first
        )
        XCTAssertEqual(restored.questionID, "free-question")
        XCTAssertTrue(restored.isBookmarked)
        XCTAssertEqual(restored.attemptCount, 1)
        XCTAssertEqual(restored.correctCount, 1)
        XCTAssertEqual(restored.lastStudiedAt, studiedAt)
    }
}

/// Stands in for a device that cannot reach the App Store at launch.
@MainActor
private final class UnreachableStoreCommerce: EntitlementCommerce {
    struct Offline: Error {}

    func loadProduct(id: String) async throws -> StoreProductDetails? { throw Offline() }
    func purchase(id: String) async throws -> PurchaseOutcome { throw Offline() }
    func restore(id: String) async throws -> Bool { throw Offline() }
    func currentEntitlement(id: String) async throws -> Bool { throw Offline() }
    func entitlementUpdates(id: String) -> AsyncStream<Bool> { AsyncStream { _ in } }
}
