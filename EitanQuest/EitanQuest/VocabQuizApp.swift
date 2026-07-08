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

    // 通知の許可リクエストは起動直後ではなく、初回クイズ完了時に行う
    // （QuizView.requestNotificationPermissionIfNeeded を参照）

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
