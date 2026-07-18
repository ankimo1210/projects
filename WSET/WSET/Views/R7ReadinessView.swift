import SwiftUI

struct R7ReadinessView: View {
#if DEBUG
    @AppStorage("r7.aiReview.developerBackendEndpoint")
    private var developerBackendEndpoint = ""
#endif

    @State private var iCloudDiagnostic: ICloudAvailabilityDiagnostic?
    @State private var isDiagnosingICloud = false
    @State private var hasAIConsent = false
    @State private var consentMessage: String?

    private let iCloudService: ICloudManualTransferService
    private let consentStore: UserDefaultsAIReviewConsentStore
    private let onOpenManualICloudTransfer: (() -> Void)?
    private let onOpenAIReview: (() -> Void)?
    private let operatorManagedBackendEndpoint: String?
    private let isProductionAIReviewEnabled: Bool

    init(
        iCloudService: ICloudManualTransferService = ICloudManualTransferService(),
        consentStore: UserDefaultsAIReviewConsentStore = UserDefaultsAIReviewConsentStore(),
        onOpenManualICloudTransfer: (() -> Void)? = nil,
        onOpenAIReview: (() -> Void)? = nil,
        operatorManagedBackendEndpoint: String? = AIReviewBackendProvisioning
            .operatorManagedEndpointText(),
        isProductionAIReviewEnabled: Bool = AIReviewBackendProvisioning.isProductionEnabled()
    ) {
        self.iCloudService = iCloudService
        self.consentStore = consentStore
        self.onOpenManualICloudTransfer = onOpenManualICloudTransfer
        self.onOpenAIReview = onOpenAIReview
        self.operatorManagedBackendEndpoint = operatorManagedBackendEndpoint
        self.isProductionAIReviewEnabled = isProductionAIReviewEnabled
    }

    var body: some View {
        Form {
            Section("端末内機能") {
                Label("採点基準による自己評価はオフラインで利用可能", systemImage: "checkmark.shield.fill")
                    .foregroundStyle(AppTheme.success)
                Text("ローカル評価は回答の意味をAI判定せず、選択した採点項目だけを採点します。")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            Section {
                if let iCloudDiagnostic {
                    Label(
                        iCloudDiagnostic.message,
                        systemImage: iCloudDiagnostic.isReadyForManualTransfer
                            ? "checkmark.icloud.fill"
                            : "icloud.slash"
                    )
                    .foregroundStyle(
                        iCloudDiagnostic.isReadyForManualTransfer
                            ? AppTheme.success
                            : Color.secondary
                    )
                } else {
                    Text("まだ診断していません。診断だけではiCloudへ書き込みません。")
                        .foregroundStyle(.secondary)
                }

                Button {
                    Task { await diagnoseICloud() }
                } label: {
                    if isDiagnosingICloud {
                        ProgressView()
                    } else {
                        Text("iCloudの可用性を診断")
                    }
                }
                .disabled(isDiagnosingICloud)
                .accessibilityIdentifier("r7.icloud.diagnose")

                Button("バックアップを手動転送") {
                    onOpenManualICloudTransfer?()
                }
                .disabled(
                    iCloudDiagnostic?.isReadyForManualTransfer != true
                        || onOpenManualICloudTransfer == nil
                )
                .accessibilityIdentifier("r7.icloud.manualTransfer")
            } header: {
                Text("iCloud手動転送")
            } footer: {
                Text("アップロードは手動転送を確定した時だけ実行します。失敗しても端末内データを継続利用できます。")
            }

            Section {
#if DEBUG
                TextField(
                    "https://example.com/api/written-review",
                    text: $developerBackendEndpoint
                )
                    .keyboardType(.URL)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .accessibilityIdentifier("r7.ai.endpoint")

                if developerBackendEndpoint.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                    Label("開発用HTTPSバックエンドが未設定です", systemImage: "exclamationmark.triangle")
                        .foregroundStyle(.secondary)
                } else if backendConfiguration == nil {
                    Label("URLはHTTPSで、認証情報・クエリ・フラグメントを含めないでください", systemImage: "xmark.shield")
                        .foregroundStyle(AppTheme.error)
                } else {
                    Label("開発用HTTPSバックエンド形式を確認しました", systemImage: "hammer.fill")
                        .foregroundStyle(AppTheme.success)
                }

                Text("この入力欄はDebugビルド限定です。Releaseビルドはこの値を読み込みません。")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
#else
                if let backendConfiguration {
                    Label("運営者管理バックエンドを確認しました", systemImage: "lock.shield")
                        .foregroundStyle(AppTheme.success)
                    LabeledContent("送信先", value: backendConfiguration.endpoint.absoluteString)
                } else {
                    Label(
                        operatorManagedBackendEndpoint == nil
                            ? "運営者管理バックエンドは未設定です"
                            : "本番安全審査が未完了のため無効です",
                        systemImage: "exclamationmark.triangle"
                    )
                        .foregroundStyle(.secondary)
                    Text("Releaseビルドでは利用者が送信先を入力できません。送信先設定に加え、本番安全審査の完了フラグが揃うまでAI添削は無効です。")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
#endif

                Text("送信対象：設問、入力した回答、模範解答、採点基準。学習履歴や端末識別子は送信しません。")
                    .font(.footnote)
                    .foregroundStyle(.secondary)

                Text("現在は技術検証です。本番提供時は回答を保存しない構成を原則とし、一時保持する場合も30日以内の上限と削除方法を公開します。")
                    .font(.footnote)
                    .foregroundStyle(.secondary)

                if hasAIConsent {
                    Label("この送信先への明示同意あり", systemImage: "checkmark.circle.fill")
                        .foregroundStyle(AppTheme.success)
                    Button("同意を取り消す", role: .destructive) {
                        Task { await revokeConsent() }
                    }
                } else {
                    Button("送信内容を確認して同意") {
                        Task { await grantConsent() }
                    }
                    .disabled(backendConfiguration == nil)
                    .accessibilityIdentifier("r7.ai.consent")
                }

                Button("AI記述添削を開く") {
                    onOpenAIReview?()
                }
                .disabled(!isRemoteAIReady || onOpenAIReview == nil)
                .accessibilityIdentifier("r7.ai.openReview")

                if let consentMessage {
                    Text(consentMessage)
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            } header: {
                Text("AI記述添削（技術検証）")
            } footer: {
#if DEBUG
                Text("APIキーはアプリに保存しません。開発用URLはローカル検証専用です。本番送信先は運営者が管理し、変更時は再同意が必要です。")
#else
                Text("APIキーはアプリに保存しません。本番送信先は運営者が管理し、変更時は再同意が必要です。")
#endif
            }
        }
        .navigationTitle("オンライン機能の準備")
        .task { await refreshConsent() }
#if DEBUG
        .onChange(of: developerBackendEndpoint) { _, _ in
            Task { await refreshConsent() }
        }
#endif
    }

    private var backendConfiguration: AIReviewBackendConfiguration? {
#if DEBUG
        AIReviewBackendProvisioning.configuration(
            operatorManagedEndpointText: operatorManagedBackendEndpoint,
            developerOverrideEndpointText: developerBackendEndpoint,
            allowsDeveloperOverride: true
        )
#else
        AIReviewBackendProvisioning.releaseConfiguration(
            operatorManagedEndpointText: operatorManagedBackendEndpoint,
            isProductionEnabled: isProductionAIReviewEnabled
        )
#endif
    }

    private var isRemoteAIReady: Bool {
        backendConfiguration != nil && hasAIConsent
    }

    @MainActor
    private func diagnoseICloud() async {
        isDiagnosingICloud = true
        iCloudDiagnostic = await iCloudService.diagnose()
        isDiagnosingICloud = false
    }

    @MainActor
    private func refreshConsent() async {
        guard let backendConfiguration else {
            hasAIConsent = false
            return
        }
        hasAIConsent = await consentStore.hasValidConsent(for: backendConfiguration)
    }

    @MainActor
    private func grantConsent() async {
        guard let backendConfiguration else { return }
        do {
            try await consentStore.grant(for: backendConfiguration)
            hasAIConsent = true
            consentMessage = "このURLへの送信に同意しました。"
        } catch {
            hasAIConsent = false
            consentMessage = "同意状態を保存できませんでした。"
        }
    }

    @MainActor
    private func revokeConsent() async {
        await consentStore.revoke()
        hasAIConsent = false
        consentMessage = "同意を取り消しました。外部送信は行いません。"
    }
}
