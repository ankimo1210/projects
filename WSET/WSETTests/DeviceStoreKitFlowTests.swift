import StoreKit
import StoreKitTest
import XCTest
@testable import WSET

/// Exercises the real `StoreKitEntitlementCommerce` against the project's StoreKit
/// Configuration file. `SKTestSession` only works on a physical device with this
/// toolchain — on the iOS 26.5 Simulator every mutating call fails with
/// `SKInternalErrorDomain Code=3`, so these tests are device-only by necessity.
@MainActor
final class DeviceStoreKitFlowTests: XCTestCase {
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
        session.askToBuyEnabled = false
    }

    override func tearDown() {
        session?.clearTransactions()
        session = nil
    }

    /// A volatile cache keeps each case from leaking Pro state into the real Keychain,
    /// and empty arguments force the production commerce rather than the UI-test stub.
    private func makeStore() -> EntitlementStore {
        EntitlementStore(
            commerce: StoreKitEntitlementCommerce(),
            cache: VolatileProEntitlementCache(),
            processArguments: []
        )
    }

    private func waitUntil(
        timeout: TimeInterval = 10,
        _ condition: @MainActor () -> Bool
    ) async -> Bool {
        let deadline = Date().addingTimeInterval(timeout)
        while Date() < deadline {
            if condition() { return true }
            try? await Task.sleep(nanoseconds: 200_000_000)
        }
        return condition()
    }

    func testConfigurationPriceReachesTheStore() async throws {
        let store = makeStore()
        await store.prepare()
        XCTAssertEqual(store.productLoadStatus, .loaded)
        XCTAssertEqual(store.displayPrice, "¥1,500")
    }

    func testPurchaseSucceedsAndGrantsPro() async throws {
        let store = makeStore()
        await store.prepare()
        XCTAssertFalse(store.hasProAccess)

        let outcome = try await store.purchase()

        XCTAssertEqual(outcome, .purchased)
        XCTAssertEqual(store.status, .proVerified)
        XCTAssertTrue(store.hasProAccess)
        XCTAssertEqual(session.allTransactions().count, 1)
    }

    func testCancelledPurchaseLeavesUserFree() async throws {
        let store = makeStore()
        await store.prepare()
        try await session.setSimulatedError(
            SKTestFailures.Purchase.generic(.userCancelled),
            forAPI: .purchase
        )

        let outcome = try await store.purchase()

        XCTAssertEqual(outcome, .cancelled)
        XCTAssertFalse(store.hasProAccess)
        // StoreKit Test still records the attempt, so assert on the entitlement itself.
        let entitled = try await StoreKitEntitlementCommerce()
            .currentEntitlement(id: EntitlementStore.proProductID)
        XCTAssertFalse(entitled, "キャンセル後に有効な権利が残らないこと")
    }

    func testAskToBuyPurchaseStaysPendingWithoutGrantingPro() async throws {
        session.askToBuyEnabled = true
        let store = makeStore()
        await store.prepare()

        let outcome = try await store.purchase()

        XCTAssertEqual(outcome, .pending)
        XCTAssertFalse(store.hasProAccess)
    }

    func testApprovedAskToBuyPurchaseGrantsProViaTransactionUpdates() async throws {
        session.askToBuyEnabled = true
        let store = makeStore()
        await store.prepare()
        let pendingOutcome = try await store.purchase()
        XCTAssertEqual(pendingOutcome, .pending)

        let pending = try XCTUnwrap(session.allTransactions().first)
        try session.approveAskToBuyTransaction(identifier: pending.identifier)

        let granted = await waitUntil { store.hasProAccess }
        XCTAssertTrue(granted, "承認後にTransaction.updates経由でProが付与されること")
    }

    func testRestoreRecoversPurchaseMadeOutsideTheApp() async throws {
        _ = try await session.buyProduct(identifier: EntitlementStore.proProductID)
        let store = makeStore()

        let restored = try await store.restorePurchases()

        XCTAssertTrue(restored)
        XCTAssertTrue(store.hasProAccess)
    }

    func testRestoreReportsNothingWhenNoPurchaseExists() async throws {
        let store = makeStore()

        let restored = try await store.restorePurchases()

        XCTAssertFalse(restored)
        XCTAssertEqual(store.status, .free)
    }

    /// A fresh store with an empty cache is the reinstalled-app case: the entitlement
    /// has to come back from `Transaction.currentEntitlements`, not from local state.
    func testEntitlementReturnsAfterReinstall() async throws {
        _ = try await session.buyProduct(identifier: EntitlementStore.proProductID)

        let reinstalled = makeStore()
        await reinstalled.prepare()

        XCTAssertEqual(reinstalled.status, .proVerified)
        XCTAssertTrue(reinstalled.hasProAccess)
    }

    func testRefundedPurchaseRevokesProAccess() async throws {
        let store = makeStore()
        await store.prepare()
        let purchased = try await store.purchase()
        XCTAssertEqual(purchased, .purchased)
        XCTAssertTrue(store.hasProAccess)

        let transaction = try XCTUnwrap(session.allTransactions().first)
        try session.refundTransaction(identifier: transaction.identifier)

        let revoked = await waitUntil { !store.hasProAccess }
        XCTAssertTrue(revoked, "返金・取消後にPro権利が失効すること")
        XCTAssertEqual(store.status, .free)
    }

    func testRefundedPurchaseIsNotRestorable() async throws {
        let store = makeStore()
        await store.prepare()
        let purchased = try await store.purchase()
        XCTAssertEqual(purchased, .purchased)
        let transaction = try XCTUnwrap(session.allTransactions().first)
        try session.refundTransaction(identifier: transaction.identifier)

        let reinstalled = makeStore()
        let restored = try await reinstalled.restorePurchases()

        XCTAssertFalse(restored, "返金済みの取引は復元対象にならないこと")
        XCTAssertFalse(reinstalled.hasProAccess)
    }
}
