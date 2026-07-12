import SwiftData
import SwiftUI

@main
struct WSETApp: App {
    private let modelContainer: ModelContainer

    init() {
        do {
            modelContainer = try ModelContainer(
                for: StudyQuestion.self,
                QuestionProgress.self,
                StudyAttempt.self,
                TastingNote.self,
                MockExamSession.self,
                ReferenceTermProgress.self
            )
        } catch {
            fatalError("Unable to create the local study database: \(error)")
        }
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .modelContainer(modelContainer)
    }
}
