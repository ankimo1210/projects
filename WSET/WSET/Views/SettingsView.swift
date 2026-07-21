import SwiftData
import SwiftUI
import UniformTypeIdentifiers

struct SettingsView: View {
    @Environment(\.modelContext) private var modelContext
    @Environment(EntitlementStore.self) private var entitlementStore
    @Query private var progressRecords: [QuestionProgress]
    @Query private var attempts: [StudyAttempt]
    @Query private var tastingNotes: [TastingNote]
    @Query private var mockExams: [MockExamSession]
    @Query private var theoryExams: [TheoryExamSession]
    @AppStorage(ReviewNotificationService.enabledKey) private var notificationsEnabled = false
    @State private var backupDocument: StudyBackupDocument?
    @State private var showingExporter = false
    @State private var showingImporter = false
    @State private var statusMessage: String?
    @State private var isRestoringPurchase = false

    var body: some View {
        Form {
            Section("Pro") {
                LabeledContent(
                    "利用状態",
                    value: entitlementStore.hasProAccess ? "購入済み" : "無料版"
                )
                if !entitlementStore.hasProAccess {
                    NavigationLink {
                        PaywallView()
                    } label: {
                        Label("Proの機能を見る", systemImage: "graduationcap.fill")
                    }
                }
                Button {
                    restorePurchase()
                } label: {
                    HStack {
                        Label("購入を復元", systemImage: "arrow.clockwise")
                        if isRestoringPurchase {
                            Spacer()
                            ProgressView()
                        }
                    }
                }
                .disabled(isRestoringPurchase)
            }

            Section("復習通知") {
                Toggle(
                    "毎日と次回期限の通知",
                    isOn: Binding(
                        get: { notificationsEnabled },
                        set: { updateNotifications(enabled: $0) }
                    )
                )
                Text("毎日9:00の通知に加え、次に復習期限を迎える問題を1件通知します。")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Section {
                LabeledContent("進捗記録", value: progressRecords.count.formatted())
                LabeledContent("学習履歴", value: attempts.count.formatted())
                LabeledContent("テイスティング記録", value: tastingNotes.count.formatted())
                LabeledContent("ミニ模試", value: mockExams.count.formatted())
                LabeledContent("理論模試", value: theoryExams.count.formatted())

                Button {
                    exportBackup()
                } label: {
                    Label("バックアップを書き出す", systemImage: "square.and.arrow.up")
                }

                Button {
                    showingImporter = true
                } label: {
                    Label("バックアップから復元", systemImage: "square.and.arrow.down")
                }
            } header: {
                Text("バックアップ")
            } footer: {
                Text("問題集本体を除く、進捗・学習履歴・テイスティング・模試・用語復習を保存します。復元はIDごとに統合し、新しい端末内履歴を削除しません。")
            }

            Section("情報") {
                NavigationLink("プライバシーとデータ") {
                    PrivacyInformationView()
                }
#if DEBUG
                NavigationLink("任意オンライン機能の準備") {
                    R7ReadinessView()
                }
#endif
                NavigationLink("本アプリについて") {
                    LegalInformationView()
                }
            }
        }
        .navigationTitle("設定")
        .navigationBarTitleDisplayMode(.inline)
        .fileExporter(
            isPresented: $showingExporter,
            document: backupDocument,
            contentType: .json,
            defaultFilename: backupFilename
        ) { result in
            if case let .failure(error) = result {
                statusMessage = BackupError.userFacingMessage(
                    for: error,
                    fallback: "バックアップの書き出しに失敗しました。"
                )
            }
        }
        .fileImporter(isPresented: $showingImporter, allowedContentTypes: [.json]) { result in
            importBackup(result)
        }
        .alert("CruNote", isPresented: Binding(
            get: { statusMessage != nil },
            set: { if !$0 { statusMessage = nil } }
        )) {
            Button("閉じる") { statusMessage = nil }
        } message: {
            Text(statusMessage ?? "")
        }
    }

    private func restorePurchase() {
        isRestoringPurchase = true
        Task {
            defer { isRestoringPurchase = false }
            do {
                statusMessage = try await entitlementStore.restorePurchases()
                    ? "購入を復元しました。"
                    : "復元できる購入は見つかりませんでした。"
            } catch {
                statusMessage = "購入を復元できませんでした。通信状態を確認してください。"
            }
        }
    }

    private var backupFilename: String {
        let date = Date.now.formatted(.iso8601.year().month().day())
        return "CruNote-Backup-\(date)"
    }

    private func updateNotifications(enabled: Bool) {
        if enabled {
            Task {
                do {
                    try await ReviewNotificationService.requestAndSchedule(
                        progressRecords: progressRecords
                    )
                    notificationsEnabled = true
                } catch {
                    notificationsEnabled = false
                    statusMessage = (error as? ReviewNotificationError)?.errorDescription
                        ?? "通知を設定できませんでした。iOSの設定を確認してください。"
                }
            }
        } else {
            notificationsEnabled = false
            Task { await ReviewNotificationService.disable() }
        }
    }

    private func exportBackup() {
        do {
            backupDocument = StudyBackupDocument(backup: try BackupService.makeBackup(in: modelContext))
            showingExporter = true
        } catch {
            statusMessage = BackupError.userFacingMessage(
                for: error,
                fallback: "バックアップの書き出しに失敗しました。"
            )
        }
    }

    private func importBackup(_ result: Result<URL, Error>) {
        do {
            let url = try result.get()
            let hasAccess = url.startAccessingSecurityScopedResource()
            defer { if hasAccess { url.stopAccessingSecurityScopedResource() } }
            let backup = try StudyBackupDocument.decode(Data(contentsOf: url))
            let restored = try BackupService.restore(backup, into: modelContext)
            statusMessage = restored.summary
            Task { await ReviewNotificationService.refreshIfEnabled(in: modelContext) }
        } catch {
            statusMessage = BackupError.userFacingMessage(
                for: error,
                fallback: "バックアップの読み込みに失敗しました。"
            )
        }
    }
}
