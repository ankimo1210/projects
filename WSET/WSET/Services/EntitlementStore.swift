import Foundation
import Observation
import Security

enum EntitlementStatus: Equatable {
    case checking
    case free
    case proVerified
    case proCached
    case unavailable(String)
}

enum PurchaseOutcome: Equatable {
    case purchased
    case pending
    case cancelled
}

enum EntitlementStoreError: LocalizedError {
    case productUnavailable
    case failedVerification

    var errorDescription: String? {
        switch self {
        case .productUnavailable:
            "購入情報を取得できません。通信状態を確認して、もう一度お試しください。"
        case .failedVerification:
            "購入情報を検証できませんでした。購入は反映されていません。"
        }
    }
}

@MainActor
@Observable
final class EntitlementStore {
    static let proProductID = "pro_lifetime"

    private(set) var status: EntitlementStatus
    private(set) var product: StoreProductDetails?
    private(set) var isPrepared = false
    @ObservationIgnored private var updatesTask: Task<Void, Never>?
    @ObservationIgnored private let commerce: any EntitlementCommerce
    @ObservationIgnored private let cache: any ProEntitlementCaching
    @ObservationIgnored private let debugProOverride: Bool
    @ObservationIgnored private let debugFreeOverride: Bool
    @ObservationIgnored private let usesDebugCommerce: Bool

    init(
        commerce: (any EntitlementCommerce)? = nil,
        cache: (any ProEntitlementCaching)? = nil,
        processArguments: [String] = ProcessInfo.processInfo.arguments
    ) {
        #if DEBUG
        if commerce == nil,
           let debugCommerce = UITestEntitlementCommerce(arguments: processArguments) {
            self.commerce = debugCommerce
            self.cache = VolatileProEntitlementCache()
            usesDebugCommerce = true
        } else {
            self.commerce = commerce ?? StoreKitEntitlementCommerce()
            self.cache = cache ?? KeychainProEntitlementCache()
            usesDebugCommerce = false
        }
        debugProOverride = processArguments.contains("-UITestProEntitlement")
        debugFreeOverride = processArguments.contains("-UITestFreeEntitlement")
        #else
        self.commerce = commerce ?? StoreKitEntitlementCommerce()
        self.cache = cache ?? KeychainProEntitlementCache()
        usesDebugCommerce = false
        debugProOverride = false
        debugFreeOverride = false
        #endif
        if debugProOverride {
            status = .proVerified
        } else if debugFreeOverride {
            status = .free
        } else {
            status = self.cache.load() ? .proCached : .checking
        }
    }

    var hasProAccess: Bool {
        switch status {
        case .proVerified, .proCached: true
        default: false
        }
    }

    var displayPrice: String? { product?.displayPrice }

    var policy: FeatureAccessPolicy {
        FeatureAccessPolicy(hasProAccess: hasProAccess)
    }

    func prepare() async {
        guard !isPrepared else { return }
        isPrepared = true
        if debugProOverride || (debugFreeOverride && !usesDebugCommerce) { return }
        startObservingTransactions()
        await loadProduct()
        await refreshEntitlement()
    }

    func purchase() async throws -> PurchaseOutcome {
        if product == nil {
            await loadProduct()
        }
        guard product != nil else { throw EntitlementStoreError.productUnavailable }

        let outcome = try await commerce.purchase(id: Self.proProductID)
        if outcome == .purchased {
            cache.save(true)
            status = .proVerified
        }
        return outcome
    }

    func restorePurchases() async throws -> Bool {
        let restored = try await commerce.restore(id: Self.proProductID)
        cache.save(restored)
        status = restored ? .proVerified : .free
        return restored
    }

    func refreshEntitlement() async {
        do {
            if try await commerce.currentEntitlement(id: Self.proProductID) {
                cache.save(true)
                status = .proVerified
            } else {
                cache.save(false)
                status = .free
            }
        } catch {
            status = cache.load()
                ? .proCached
                : .unavailable("購入権利を確認できません。")
        }
    }

    private func loadProduct() async {
        do {
            product = try await commerce.loadProduct(id: Self.proProductID)
            if product == nil, !hasProAccess {
                status = .unavailable("商品情報を取得できません。")
            }
        } catch {
            product = nil
            if !hasProAccess {
                status = .unavailable("商品情報を取得できません。")
            }
        }
    }

    private func startObservingTransactions() {
        guard updatesTask == nil else { return }
        let updates = commerce.entitlementUpdates(id: Self.proProductID)
        updatesTask = Task { [weak self] in
            for await isEntitled in updates {
                guard !Task.isCancelled else { return }
                guard let self else { return }
                self.cache.save(isEntitled)
                self.status = isEntitled ? .proVerified : .free
            }
        }
    }
}

struct KeychainProEntitlementCache: ProEntitlementCaching {
    private static let service = "com.ankimo.WSET.entitlement"
    private static let account = "pro_lifetime"

    func load() -> Bool {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: Self.service,
            kSecAttrAccount as String: Self.account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne,
        ]
        var item: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &item) == errSecSuccess,
              let data = item as? Data else { return false }
        return data == Data([1])
    }

    func save(_ enabled: Bool) {
        let lookup: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: Self.service,
            kSecAttrAccount as String: Self.account,
        ]
        if enabled {
            let attributes: [String: Any] = [kSecValueData as String: Data([1])]
            let status = SecItemUpdate(lookup as CFDictionary, attributes as CFDictionary)
            if status == errSecItemNotFound {
                var insert = lookup
                insert[kSecValueData as String] = Data([1])
                SecItemAdd(insert as CFDictionary, nil)
            }
        } else {
            SecItemDelete(lookup as CFDictionary)
        }
    }
}
