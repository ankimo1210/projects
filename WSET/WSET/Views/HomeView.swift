import SwiftUI

struct HomeView: View {
    private let store: RegionMapStore = {
#if DEBUG
        if ProcessInfo.processInfo.arguments.contains("-UITestRegionMapLoadFailure") {
            return RegionMapStore(data: nil)
        }
#endif
        return .shared
    }()

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 24) {
                    Text("地図から、ワインを知る。")
                        .font(.title3).foregroundStyle(AppTheme.forest)
                    if let error = store.loadError {
                        ContentUnavailableView("産地マップを利用できません", systemImage: "map",
                                               description: Text(error))
                            .accessibilityIdentifier("regionMap.loadError")
                    } else if let france = store.map(id: "france") {
                        AtlasExplorerContent(document: france, store: store)
                    } else {
                        ContentUnavailableView("収録マップがありません", systemImage: "map")
                    }
                }
                .padding()
            }
            .background(AppTheme.paper)
            .navigationTitle("CruNote")
        }
    }
}
