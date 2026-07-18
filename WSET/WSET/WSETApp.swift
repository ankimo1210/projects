import SwiftData
import SwiftUI

@main
struct WSETApp: App {
    private let modelContainer: ModelContainer
    @State private var entitlementStore = EntitlementStore()

    init() {
        do {
            let modelConfiguration = ModelConfiguration(
                isStoredInMemoryOnly: ProcessInfo.processInfo.arguments.contains(
                    "-UITestInMemoryStore"
                )
            )
            modelContainer = try ModelContainer(
                for: StudyQuestion.self,
                QuestionProgress.self,
                StudyAttempt.self,
                WrittenAnswerDraft.self,
                TastingNote.self,
                MockExamSession.self,
                TheoryExamSession.self,
                ReferenceTermProgress.self,
                configurations: modelConfiguration
            )
        } catch {
            fatalError("Unable to create the local study database: \(error)")
        }
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(entitlementStore)
                .task { await entitlementStore.prepare() }
        }
        .modelContainer(modelContainer)
    }
}
