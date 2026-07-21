import SwiftUI

struct PremiumFeatureGate<Content: View>: View {
    @Environment(EntitlementStore.self) private var entitlementStore
    let feature: PremiumFeature
    @ViewBuilder let content: () -> Content

    var body: some View {
        if entitlementStore.policy.canAccess(feature) {
            content()
        } else {
            PaywallView(triggerFeature: feature)
        }
    }
}

struct PaywallView: View {
    @Environment(EntitlementStore.self) private var entitlementStore
    let triggerFeature: PremiumFeature?
    @State private var isProcessing = false
    @State private var message: String?

    init(triggerFeature: PremiumFeature? = nil) {
        self.triggerFeature = triggerFeature
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                VStack(spacing: 12) {
                    Image(systemName: "graduationcap.fill")
                        .font(.system(size: 48))
                        .foregroundStyle(AppTheme.wine)
                    Text("CruNote Pro")
                        .font(.largeTitle.bold())
                    Text("一度だけの支払いで、収録済みのPro対象機能を解放します。")
                        .multilineTextAlignment(.center)
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity)

                if let triggerFeature {
                    Label(
                        "「\(triggerFeature.displayName)」はProで利用できます",
                        systemImage: "lock.fill"
                    )
                    .padding()
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(AppTheme.wineSoft, in: RoundedRectangle(cornerRadius: 14))
                }

                VStack(alignment: .leading, spacing: 14) {
                    featureRow("今日の重点学習・詳細弱点分析")
                    featureRow("産地比較")
                    featureRow("全用語・用語SRS")
                    featureRow("テイスティング記録無制限")
                }

                Button {
                    Task { await purchase() }
                } label: {
                    HStack {
                        if isProcessing { ProgressView().tint(.white) }
                        Text(purchaseLabel)
                            .frame(maxWidth: .infinity)
                    }
                }
                .buttonStyle(.borderedProminent)
                .tint(AppTheme.wine)
                .disabled(isProcessing || entitlementStore.product == nil)
                .accessibilityIdentifier("paywall.purchase")

                if entitlementStore.product == nil, productLoadFailed {
                    Button("価格を再読み込み") {
                        Task { await reloadPrice() }
                    }
                    .frame(maxWidth: .infinity)
                    .disabled(isProcessing)
                    .accessibilityIdentifier("paywall.reloadPrice")
                }

                Button("購入を復元") {
                    Task { await restore() }
                }
                .frame(maxWidth: .infinity)
                .disabled(isProcessing)
                .accessibilityIdentifier("paywall.restore")

                if let message {
                    Text(message)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity, alignment: .center)
                }

                Text("本アプリはWSET（Wine & Spirit Education Trust）と提携・承認された公式アプリではありません。購入前にApp Storeの価格と条件をご確認ください。")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
            .padding()
        }
        .navigationTitle("Proを解放")
        .task { await entitlementStore.prepare() }
    }

    private var purchaseLabel: String {
        if entitlementStore.hasProAccess { return "購入済み" }
        if let price = entitlementStore.displayPrice {
            return "\(price)で買い切り"
        }
        if productLoadFailed { return "価格を取得できません" }
        return "価格を読み込み中"
    }

    private var productLoadFailed: Bool {
        entitlementStore.productLoadStatus == .unavailable
    }

    private func featureRow(_ text: String) -> some View {
        Label(text, systemImage: "checkmark.circle.fill")
            .foregroundStyle(.primary, AppTheme.wine)
    }

    private func purchase() async {
        isProcessing = true
        defer { isProcessing = false }
        do {
            switch try await entitlementStore.purchase() {
            case .purchased: message = "購入が完了しました。Pro対象機能を利用できます。"
            case .pending: message = "購入は承認待ちです。承認後に自動で反映されます。"
            case .cancelled: message = "購入はキャンセルされました。"
            }
        } catch {
            message = error.localizedDescription
        }
    }

    private func reloadPrice() async {
        isProcessing = true
        defer { isProcessing = false }
        await entitlementStore.reloadProduct()
        message = entitlementStore.product == nil
            ? "価格を取得できませんでした。しばらくしてからもう一度お試しください。"
            : nil
    }

    private func restore() async {
        isProcessing = true
        defer { isProcessing = false }
        do {
            message = try await entitlementStore.restorePurchases()
                ? "購入を復元しました。"
                : "復元できる購入は見つかりませんでした。"
        } catch {
            message = "購入を復元できませんでした。通信状態を確認してください。"
        }
    }
}
