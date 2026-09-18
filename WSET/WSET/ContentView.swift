import SwiftData
import SwiftUI

struct ContentView: View {
    @Environment(\.modelContext) private var modelContext
    @Query private var questions: [StudyQuestion]
    @State private var hasStartedImport = false
    @State private var importError: String?

    var body: some View {
        Group {
            if let importError {
                ContentUnavailableView(
                    "問題集を利用できません",
                    systemImage: "exclamationmark.triangle",
                    description: Text(importError)
                )
            } else if questions.isEmpty {
                VStack(spacing: 18) {
                    ProgressView()
                    Text("問題集を準備しています…")
                        .foregroundStyle(.secondary)
                }
            } else {
                TabView {
                    HomeView()
                        .tabItem { Label("探索", systemImage: "map") }

                    StudySetupView()
                        .tabItem { Label("学ぶ", systemImage: "rectangle.stack") }

                    QuestionLibraryView()
                        .tabItem { Label("図鑑", systemImage: "books.vertical") }

                    TastingView()
                        .tabItem { Label("ノート", systemImage: "wineglass") }

                    StudyProgressView()
                        .tabItem { Label("記録", systemImage: "chart.bar") }
                }
                .tint(AppTheme.wine)
            }
        }
        .environment(\.locale, AppLanguage.locale)
        .task {
            guard !hasStartedImport else { return }
            hasStartedImport = true
            do {
                let migratedTermCount = try R5BackupSupport.migrateTermIDs(
                    ReferenceStore.shared.termIDMigrations,
                    in: modelContext
                )
                if migratedTermCount > 0 {
                    try modelContext.save()
                }
                try QuestionImporter.importIfNeeded(into: modelContext)
#if DEBUG
                if ProcessInfo.processInfo.arguments.contains("-UITestResetStudyHistory") {
                    try QuestionImporter.resetQuestionStudyHistory(in: modelContext)
                }
#endif
                await ReviewNotificationService.refreshIfEnabled(in: modelContext)
            } catch {
                importError = (error as? QuestionImporterError)?.errorDescription
                    ?? "問題集の準備に失敗しました。アプリを再起動してください。"
            }
        }
    }
}

#Preview {
    ContentView()
        .environment(EntitlementStore())
        .modelContainer(
            for: [
                StudyQuestion.self,
                QuestionProgress.self,
                StudyAttempt.self,
                WrittenAnswerDraft.self,
                TastingNote.self,
                MockExamSession.self,
                TheoryExamSession.self,
                ReferenceTermProgress.self
            ],
            inMemory: true
        )
}
