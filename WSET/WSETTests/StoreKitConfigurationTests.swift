import SwiftData
import XCTest
@testable import WSET

@MainActor
final class StoreKitConfigurationTests: XCTestCase {
    func testLifetimeProductConfigurationIsBundledAndNonConsumable() throws {
        let url = try XCTUnwrap(
            Bundle.main.url(forResource: "Configuration", withExtension: "storekit")
        )
        let object = try XCTUnwrap(
            JSONSerialization.jsonObject(with: Data(contentsOf: url)) as? [String: Any]
        )
        let products = try XCTUnwrap(object["products"] as? [[String: Any]])
        let product = try XCTUnwrap(products.first)

        XCTAssertEqual(products.count, 1)
        XCTAssertEqual(product["productID"] as? String, EntitlementStore.proProductID)
        XCTAssertEqual(product["type"] as? String, "NonConsumable")
        XCTAssertEqual(product["displayPrice"] as? String, "1500")

        let localizations = try XCTUnwrap(product["localizations"] as? [[String: Any]])
        let japanese = try XCTUnwrap(
            localizations.first { $0["locale"] as? String == "ja_JP" }
        )
        let description = try XCTUnwrap(japanese["description"] as? String)
        XCTAssertFalse(description.contains("全問題"))
        XCTAssertFalse(description.contains("本番形式模試"))
        XCTAssertFalse(description.contains("記述式"))
    }

    func testPurchaseOutcomesAndVerifiedCacheAreHandled() async throws {
        for outcome in [PurchaseOutcome.pending, .cancelled, .purchased] {
            let commerce = MockEntitlementCommerce(purchaseOutcome: outcome)
            let cache = MemoryEntitlementCache()
            let store = EntitlementStore(
                commerce: commerce,
                cache: cache,
                processArguments: []
            )
            await store.prepare()

            let result = try await store.purchase()

            XCTAssertEqual(result, outcome)
            XCTAssertEqual(store.hasProAccess, outcome == .purchased)
            XCTAssertEqual(cache.load(), outcome == .purchased)
        }
    }

    func testRestoreSetsAndClearsAuthoritativeEntitlement() async throws {
        let commerce = MockEntitlementCommerce(restoreResult: true)
        let cache = MemoryEntitlementCache()
        let store = EntitlementStore(
            commerce: commerce,
            cache: cache,
            processArguments: []
        )
        await store.prepare()

        let restored = try await store.restorePurchases()
        XCTAssertTrue(restored)
        XCTAssertTrue(store.hasProAccess)
        XCTAssertTrue(cache.load())

        commerce.restoreResult = false
        let missing = try await store.restorePurchases()
        XCTAssertFalse(missing)
        XCTAssertFalse(store.hasProAccess)
        XCTAssertFalse(cache.load())
    }

    func testOfflinePreparationKeepsOnlyPreviouslyVerifiedCachedRight() async {
        let cachedCommerce = MockEntitlementCommerce()
        cachedCommerce.loadError = MockCommerceError.offline
        cachedCommerce.entitlementError = MockCommerceError.offline
        let verifiedCache = MemoryEntitlementCache(enabled: true)
        let cachedStore = EntitlementStore(
            commerce: cachedCommerce,
            cache: verifiedCache,
            processArguments: []
        )

        await cachedStore.prepare()

        XCTAssertEqual(cachedStore.status, .proCached)
        XCTAssertTrue(cachedStore.hasProAccess)
        XCTAssertTrue(verifiedCache.load())

        let freshCommerce = MockEntitlementCommerce()
        freshCommerce.loadError = MockCommerceError.offline
        freshCommerce.entitlementError = MockCommerceError.offline
        let freshStore = EntitlementStore(
            commerce: freshCommerce,
            cache: MemoryEntitlementCache(enabled: false),
            processArguments: []
        )

        await freshStore.prepare()

        XCTAssertFalse(freshStore.hasProAccess)
        guard case .unavailable = freshStore.status else {
            return XCTFail("An unverified offline install must remain unavailable")
        }
    }

    func testSuccessfulNegativeEntitlementQueryClearsStaleCachedRight() async {
        let commerce = MockEntitlementCommerce()
        commerce.currentEntitlementResult = false
        let cache = MemoryEntitlementCache(enabled: true)
        let store = EntitlementStore(
            commerce: commerce,
            cache: cache,
            processArguments: []
        )

        XCTAssertEqual(store.status, .proCached)
        await store.prepare()

        XCTAssertEqual(store.status, .free)
        XCTAssertFalse(store.hasProAccess)
        XCTAssertFalse(cache.load())
    }

    func testRevocationUpdateClearsVerifiedRightAndCache() async {
        let commerce = MockEntitlementCommerce()
        commerce.currentEntitlementResult = true
        let cache = MemoryEntitlementCache()
        let store = EntitlementStore(
            commerce: commerce,
            cache: cache,
            processArguments: []
        )
        await store.prepare()
        XCTAssertEqual(store.status, .proVerified)
        XCTAssertTrue(cache.load())

        commerce.sendEntitlementUpdate(false)
        for _ in 0..<20 where store.hasProAccess {
            await Task.yield()
        }

        XCTAssertEqual(store.status, .free)
        XCTAssertFalse(cache.load())
    }

    func testPurchasingProDoesNotReplaceExistingFreeUserProgress() async throws {
        let container = try ModelContainer(
            for: QuestionProgress.self,
            configurations: ModelConfiguration(isStoredInMemoryOnly: true)
        )
        let studiedAt = Date(timeIntervalSince1970: 1_700_000_000)
        let progress = QuestionProgress(questionID: "free-question")
        progress.isBookmarked = true
        progress.record(isCorrect: true, rating: 3, at: studiedAt)
        container.mainContext.insert(progress)
        try container.mainContext.save()

        let store = EntitlementStore(
            commerce: MockEntitlementCommerce(purchaseOutcome: .purchased),
            cache: MemoryEntitlementCache(),
            processArguments: []
        )
        await store.prepare()
        let outcome = try await store.purchase()
        XCTAssertEqual(outcome, .purchased)

        let restored = try XCTUnwrap(
            container.mainContext.fetch(FetchDescriptor<QuestionProgress>()).first
        )
        XCTAssertEqual(restored.questionID, "free-question")
        XCTAssertTrue(restored.isBookmarked)
        XCTAssertEqual(restored.attemptCount, 1)
        XCTAssertEqual(restored.correctCount, 1)
        XCTAssertEqual(restored.lastStudiedAt, studiedAt)
    }

    func testDebugEntitlementOverrideDoesNotCallCommerce() async {
        let commerce = MockEntitlementCommerce()
        let store = EntitlementStore(
            commerce: commerce,
            cache: MemoryEntitlementCache(),
            processArguments: ["-UITestProEntitlement"]
        )

        await store.prepare()

        XCTAssertTrue(store.hasProAccess)
        XCTAssertEqual(commerce.loadCallCount, 0)
        XCTAssertEqual(commerce.entitlementCallCount, 0)
    }

    func testProductCanBeReloadedAfterInitialFailure() async {
        let commerce = MockEntitlementCommerce()
        commerce.product = nil
        let store = EntitlementStore(
            commerce: commerce,
            cache: MemoryEntitlementCache(),
            processArguments: []
        )

        await store.prepare()

        XCTAssertNil(store.product)
        XCTAssertEqual(store.productLoadStatus, .unavailable)

        commerce.product = StoreProductDetails(
            id: EntitlementStore.proProductID,
            displayPrice: "¥1,500"
        )
        await store.reloadProduct()

        XCTAssertEqual(store.displayPrice, "¥1,500")
        XCTAssertEqual(store.productLoadStatus, .loaded)
        XCTAssertEqual(store.status, .free)
        XCTAssertEqual(commerce.loadCallCount, 2)
    }
}

@MainActor
private final class MockEntitlementCommerce: EntitlementCommerce {
    var product: StoreProductDetails? = StoreProductDetails(
        id: EntitlementStore.proProductID,
        displayPrice: "¥1,500"
    )
    var purchaseOutcome: PurchaseOutcome
    var restoreResult: Bool
    var currentEntitlementResult = false
    var loadError: Error?
    var entitlementError: Error?
    private(set) var loadCallCount = 0
    private(set) var entitlementCallCount = 0
    private var entitlementContinuation: AsyncStream<Bool>.Continuation?

    init(
        purchaseOutcome: PurchaseOutcome = .purchased,
        restoreResult: Bool = false
    ) {
        self.purchaseOutcome = purchaseOutcome
        self.restoreResult = restoreResult
    }

    func loadProduct(id: String) async throws -> StoreProductDetails? {
        loadCallCount += 1
        if let loadError { throw loadError }
        return product
    }

    func purchase(id: String) async throws -> PurchaseOutcome {
        purchaseOutcome
    }

    func restore(id: String) async throws -> Bool {
        restoreResult
    }

    func currentEntitlement(id: String) async throws -> Bool {
        entitlementCallCount += 1
        if let entitlementError { throw entitlementError }
        return currentEntitlementResult
    }

    func entitlementUpdates(id: String) -> AsyncStream<Bool> {
        AsyncStream { continuation in
            entitlementContinuation = continuation
        }
    }

    func sendEntitlementUpdate(_ isEntitled: Bool) {
        entitlementContinuation?.yield(isEntitled)
    }
}

@MainActor
private final class MemoryEntitlementCache: ProEntitlementCaching {
    private var enabled: Bool

    init(enabled: Bool = false) {
        self.enabled = enabled
    }

    func load() -> Bool { enabled }
    func save(_ enabled: Bool) { self.enabled = enabled }
}

private enum MockCommerceError: Error {
    case offline
}
