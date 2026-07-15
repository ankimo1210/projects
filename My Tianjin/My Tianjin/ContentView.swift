import SwiftData
import SwiftUI

struct ContentView: View {
    @Environment(\.modelContext) private var modelContext
    @EnvironmentObject private var contentStore: LearningContentStore
    @State private var selectedTab = 0

    var body: some View {
        TabView(selection: $selectedTab) {
            NavigationStack {
                HomeView(selectedTab: $selectedTab)
            }
            .tabItem { Label("ホーム", systemImage: "house.fill") }
            .tag(0)

            NavigationStack {
                VocabularyHubView()
            }
            .tabItem { Label("単語", systemImage: "rectangle.stack.fill") }
            .tag(1)

            NavigationStack {
                PracticeHubView()
            }
            .tabItem { Label("練習", systemImage: "square.and.pencil") }
            .tag(2)

            NavigationStack {
                ReadingLibraryView()
            }
            .tabItem { Label("読解", systemImage: "text.book.closed.fill") }
            .tag(3)

            NavigationStack {
                SettingsView()
            }
            .tabItem { Label("設定", systemImage: "gearshape.fill") }
            .tag(4)
        }
        .task {
            contentStore.prepare()
            let initialVocabulary = contentStore.vocabulary(for: .level1, cumulative: false)
            try? StudyPersistence.migrateLegacyLearnedIDsIfNeeded(
                vocabulary: initialVocabulary,
                in: modelContext
            )
        }
    }
}
