import SwiftData
import SwiftUI
import UniformTypeIdentifiers

struct SettingsView: View {
    @Environment(\.modelContext) private var modelContext
    @Query private var progressRecords: [QuestionProgress]
    @Query private var attempts: [StudyAttempt]
    @Query private var tastingNotes: [TastingNote]
    @Query private var mockExams: [MockExamSession]
    @AppStorage(ReviewNotificationService.enabledKey) private var notificationsEnabled = false
    @State private var backupDocument: StudyBackupDocument?
    @State private var showingExporter = false
    @State private var showingImporter = false
    @State private var statusMessage: String?

    var body: some View {
        Form {
            Section("Review reminders") {
                Toggle(
                    "Daily and next-due notifications",
                    isOn: Binding(
                        get: { notificationsEnabled },
                        set: { updateNotifications(enabled: $0) }
                    )
                )
                Text("A daily reminder is scheduled for 09:00, plus one notification for the next due review.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Section {
                LabeledContent("Progress records", value: progressRecords.count.formatted())
                LabeledContent("Study attempts", value: attempts.count.formatted())
                LabeledContent("Tasting notes", value: tastingNotes.count.formatted())
                LabeledContent("Mock exams", value: mockExams.count.formatted())

                Button {
                    exportBackup()
                } label: {
                    Label("Export backup", systemImage: "square.and.arrow.up")
                }

                Button {
                    showingImporter = true
                } label: {
                    Label("Restore from backup", systemImage: "square.and.arrow.down")
                }
            } header: {
                Text("Backup")
            } footer: {
                Text("Backups contain progress, study attempts, tasting notes, and mock exams, but not the question library. Restore merges records by ID and does not delete newer local attempts.")
            }
        }
        .navigationTitle("Settings")
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
        .alert("WSET Study", isPresented: Binding(
            get: { statusMessage != nil },
            set: { if !$0 { statusMessage = nil } }
        )) {
            Button("閉じる") { statusMessage = nil }
        } message: {
            Text(statusMessage ?? "")
        }
    }

    private var backupFilename: String {
        let date = Date.now.formatted(.iso8601.year().month().day())
        return "WSET-Study-Backup-\(date)"
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
