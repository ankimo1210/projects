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
                        .tabItem { Label("ホーム", systemImage: "house") }

                    StudySetupView()
                        .tabItem { Label("学習", systemImage: "rectangle.stack") }

                    QuestionLibraryView()
                        .tabItem { Label("問題集", systemImage: "books.vertical") }

                    TastingView()
                        .tabItem { Label("テイスティング", systemImage: "wineglass") }

                    StudyProgressView()
                        .tabItem { Label("進捗", systemImage: "chart.bar") }
                }
                .tint(AppTheme.wine)
            }
        }
        .environment(\.locale, AppLanguage.locale)
        .task {
            guard !hasStartedImport else { return }
            hasStartedImport = true
            do {
                try QuestionImporter.importIfNeeded(into: modelContext)
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
        .modelContainer(
            for: [
                StudyQuestion.self,
                QuestionProgress.self,
                StudyAttempt.self,
                TastingNote.self,
                MockExamSession.self
            ],
            inMemory: true
        )
}
