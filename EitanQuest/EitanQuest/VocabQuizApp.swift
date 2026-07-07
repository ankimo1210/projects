import SwiftUI
import SwiftData

@main
struct VocabQuizApp: App {
    let sharedModelContainer: ModelContainer = {
        let schema = Schema([Word.self])
        let configuration = ModelConfiguration(schema: schema, isStoredInMemoryOnly: false)
        do {
            return try ModelContainer(for: schema, configurations: [configuration])
        } catch {
            fatalError("ModelContainerの作成に失敗しました: \(error)")
        }
    }()

    init() {
        NotificationService.requestAuthorization()
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .task {
                    DataSeeder.seedIfNeeded(context: sharedModelContainer.mainContext)
                    NotificationService.scheduleDailyReminder()
                }
        }
        .modelContainer(sharedModelContainer)
    }
}
