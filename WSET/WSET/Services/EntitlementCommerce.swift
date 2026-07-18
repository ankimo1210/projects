import Foundation
import StoreKit

struct StoreProductDetails: Equatable {
    let id: String
    let displayPrice: String
}

@MainActor
protocol EntitlementCommerce: AnyObject {
    func loadProduct(id: String) async throws -> StoreProductDetails?
    func purchase(id: String) async throws -> PurchaseOutcome
    func restore(id: String) async throws -> Bool
    func currentEntitlement(id: String) async throws -> Bool
    func entitlementUpdates(id: String) -> AsyncStream<Bool>
}

@MainActor
final class StoreKitEntitlementCommerce: EntitlementCommerce {
    private var productsByID: [String: Product] = [:]

    func loadProduct(id: String) async throws -> StoreProductDetails? {
        guard let product = try await Product.products(for: [id]).first else { return nil }
        productsByID[id] = product
        return StoreProductDetails(id: product.id, displayPrice: product.displayPrice)
    }

    func purchase(id: String) async throws -> PurchaseOutcome {
        if productsByID[id] == nil {
            _ = try await loadProduct(id: id)
        }
        guard let product = productsByID[id] else {
            throw EntitlementStoreError.productUnavailable
        }

        do {
            switch try await product.purchase() {
            case let .success(result):
                let transaction = try Self.verified(result)
                guard transaction.productID == id else {
                    throw EntitlementStoreError.failedVerification
                }
                await transaction.finish()
                return .purchased
            case .pending:
                return .pending
            case .userCancelled:
                return .cancelled
            @unknown default:
                return .cancelled
            }
        } catch StoreKitError.userCancelled {
            return .cancelled
        }
    }

    func restore(id: String) async throws -> Bool {
        try await AppStore.sync()
        return try await currentEntitlement(id: id)
    }

    func currentEntitlement(id: String) async throws -> Bool {
        for await result in Transaction.currentEntitlements {
            guard case let .verified(transaction) = result,
                  transaction.productID == id
            else { continue }
            if transaction.revocationDate == nil { return true }
        }
        return false
    }

    func entitlementUpdates(id: String) -> AsyncStream<Bool> {
        AsyncStream(bufferingPolicy: .bufferingNewest(1)) { continuation in
            let task = Task {
                for await result in Transaction.updates {
                    guard !Task.isCancelled else { break }
                    guard case let .verified(transaction) = result,
                          transaction.productID == id
                    else { continue }
                    await transaction.finish()
                    continuation.yield(transaction.revocationDate == nil)
                }
                continuation.finish()
            }
            continuation.onTermination = { _ in task.cancel() }
        }
    }

    nonisolated private static func verified<T>(
        _ result: VerificationResult<T>
    ) throws -> T {
        switch result {
        case let .verified(value): value
        case .unverified: throw EntitlementStoreError.failedVerification
        }
    }
}

@MainActor
protocol ProEntitlementCaching {
    func load() -> Bool
    func save(_ enabled: Bool)
}

#if DEBUG
@MainActor
final class UITestEntitlementCommerce: EntitlementCommerce {
    private let purchaseOutcome: PurchaseOutcome
    private let restoreResult: Bool

    init?(arguments: [String]) {
        if arguments.contains("-UITestStorePurchaseSuccess") {
            purchaseOutcome = .purchased
        } else if arguments.contains("-UITestStorePurchasePending") {
            purchaseOutcome = .pending
        } else if arguments.contains("-UITestStorePurchaseCancelled") {
            purchaseOutcome = .cancelled
        } else if arguments.contains("-UITestStoreRestoreSuccess") {
            purchaseOutcome = .cancelled
        } else {
            return nil
        }
        restoreResult = arguments.contains("-UITestStoreRestoreSuccess")
    }

    func loadProduct(id: String) async throws -> StoreProductDetails? {
        StoreProductDetails(id: id, displayPrice: "¥1,980")
    }

    func purchase(id: String) async throws -> PurchaseOutcome { purchaseOutcome }
    func restore(id: String) async throws -> Bool { restoreResult }
    func currentEntitlement(id: String) async throws -> Bool { false }
    func entitlementUpdates(id: String) -> AsyncStream<Bool> { AsyncStream { _ in } }
}

@MainActor
final class VolatileProEntitlementCache: ProEntitlementCaching {
    private var enabled = false
    func load() -> Bool { enabled }
    func save(_ enabled: Bool) { self.enabled = enabled }
}
#endif
