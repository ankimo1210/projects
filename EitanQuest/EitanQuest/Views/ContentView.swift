import SwiftUI
import SwiftData

struct ContentView: View {
    var body: some View {
        TabView {
            CategorySelectionView()
                .tabItem {
                    Label("学習", systemImage: "book.fill")
                }

            ThemeSelectionView()
                .tabItem {
                    Label("テーマ", systemImage: "square.grid.2x2.fill")
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
