import SwiftUI
import SwiftData

struct ContentView: View {
    var body: some View {
        TabView {
            CategorySelectionView()
                .tabItem {
                    Label("学習", systemImage: "book.fill")
                }

            StatsView()
                .tabItem {
                    Label("統計", systemImage: "chart.bar.fill")
                }
        }
    }
}

#Preview {
    ContentView()
        .modelContainer(for: Word.self, inMemory: true)
}
