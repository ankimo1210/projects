import SwiftUI
import UIKit

struct RegionPhotoView: View {
    let regionID: String
    var height: CGFloat = 210

    var body: some View {
        Group {
            if let photo = AtlasMediaStore.shared.photo(for: regionID),
               let image = UIImage(named: photo.assetName) {
                GeometryReader { proxy in
                    Image(uiImage: image)
                        .resizable()
                        .scaledToFill()
                        .frame(width: proxy.size.width, height: height)
                        .clipped()
                }
                    .frame(height: height)
                    .accessibilityElement(children: .ignore)
                    .accessibilityLabel(photo.altText)
                    .accessibilityIdentifier("atlas.photo.\(regionID)")
            } else {
                VStack(spacing: 10) {
                    Image(systemName: "photo")
                        .font(.title)
                        .accessibilityHidden(true)
                    Text("産地の風景")
                        .font(.headline)
                    Text("写真は現在表示できません")
                        .font(.caption)
                }
                .foregroundStyle(AppTheme.forest)
                .frame(maxWidth: .infinity, minHeight: height)
                .background(AppTheme.forestSoft)
                .accessibilityElement(children: .combine)
                .accessibilityIdentifier("atlas.photo.placeholder.\(regionID)")
            }
        }
        .frame(maxWidth: .infinity)
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }
}

struct AtlasPhotoCreditsView: View {
    @Environment(\.dismiss) private var dismiss
    let photo: AtlasPhoto

    var body: some View {
        NavigationStack {
            List {
                Section("写真") {
                    Text(photo.title).font(.headline)
                    LabeledContent("作者", value: photo.author)
                    Text(photo.altText)
                }
                Section("利用条件") {
                    Text(photo.license)
                    Text("加工内容：\(photo.changes)")
                    Text("確認日：\(photo.checkedAt)")
                    if let url = URL(string: photo.sourceURL) {
                        Link("原典の写真を開く", destination: url)
                            .frame(minHeight: 44)
                            .accessibilityIdentifier("atlas.photo.source")
                    }
                    if let url = URL(string: photo.licenseURL) {
                        Link("ライセンスを開く", destination: url)
                            .frame(minHeight: 44)
                            .accessibilityIdentifier("atlas.photo.license")
                    }
                }
            }
            .navigationTitle("写真の出典")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) { Button("閉じる") { dismiss() } }
            }
        }
    }
}

/// Shared by the home atlas and country map. Question returns use read-only navigation.
struct AtlasExplorerContent: View {
    @Environment(EntitlementStore.self) private var entitlementStore
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize
    @State private var displayMode = 0
    @State private var selectedRegionID: String?
    let document: RegionMapDocument
    let store: RegionMapStore
    let allowsRegionNavigation: Bool

    init(document: RegionMapDocument, store: RegionMapStore = .shared,
         initialSelectedRegionID: String? = nil, allowsRegionNavigation: Bool = true) {
        self.document = document
        self.store = store
        self.allowsRegionNavigation = allowsRegionNavigation
        _selectedRegionID = State(initialValue:
            document.regions.first { $0.id == initialSelectedRegionID }?.id ?? document.regions.first?.id)
    }

    private var selectedRegion: MapRegion? {
        document.regions.first { $0.id == selectedRegionID }
    }

    var body: some View {
        if entitlementStore.policy.canAccessRegionMap(country: document.country) {
            VStack(alignment: .leading, spacing: 20) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(document.nameJapanese).font(.largeTitle.bold())
                    Text("\(document.nameOriginal) · \(document.regions.count)の産地")
                        .font(.subheadline).foregroundStyle(.secondary)
                }
                if dynamicTypeSize.isAccessibilitySize {
                    modePicker.pickerStyle(.menu)
                } else {
                    modePicker.pickerStyle(.segmented)
                }

                if displayMode == 0 {
                    RegionMapCanvasView(document: document, selectedRegionID: selectedRegionID) {
                        selectedRegionID = $0.id
                    }
                    .aspectRatio(document.aspectRatio, contentMode: .fit)
                    .frame(maxWidth: 520)
                    .frame(maxWidth: .infinity)
                    .accessibilityIdentifier("atlas.map")

                    Text("丸印は産地の代表位置です。数字の集合マーカーから産地を選べます。境界線は産地の法的範囲を示しません。")
                        .font(.footnote).foregroundStyle(.secondary)
                    if let selectedRegion {
                        VStack(alignment: .leading, spacing: 14) {
                            AtlasRegionSummary(region: selectedRegion, photoHeight: 150)
                            if allowsRegionNavigation {
                                NavigationLink {
                                    RegionDetailView(region: selectedRegion, country: document.country)
                                } label: {
                                    Label("\(selectedRegion.nameJapanese)を知る", systemImage: "arrow.right")
                                        .frame(maxWidth: .infinity, minHeight: 44)
                                }
                                .buttonStyle(.bordered)
                                .tint(AppTheme.forest)
                                .accessibilityIdentifier("atlas.detail.open")
                            }
                        }
                        .padding(16)
                        .background(AppTheme.surface, in: RoundedRectangle(cornerRadius: 20))
                        .accessibilityIdentifier("atlas.selected.\(selectedRegion.id)")
                    }
                } else {
                    Text("産地一覧").font(.headline)
                    ForEach(document.regions) { region in
                        if allowsRegionNavigation {
                            NavigationLink {
                                RegionDetailView(region: region, country: document.country)
                            } label: {
                                AtlasRegionSummary(region: region, photoHeight: 140)
                                    .padding(16)
                                    .background(AppTheme.surface, in: RoundedRectangle(cornerRadius: 20))
                            }
                            .buttonStyle(.plain)
                            .accessibilityIdentifier("regionMap.list.\(region.id)")
                        } else {
                            Button {
                                selectedRegionID = region.id
                                displayMode = 0
                            } label: {
                                AtlasRegionSummary(region: region, photoHeight: 140)
                                    .padding(16)
                                    .background(AppTheme.surface, in: RoundedRectangle(cornerRadius: 20))
                            }
                            .buttonStyle(.plain)
                            .accessibilityIdentifier("regionMap.list.\(region.id)")
                        }
                    }
                }
                if allowsRegionNavigation, document.regions.count >= 2 {
                    NavigationLink {
                        RegionComparisonView(document: document, store: store)
                    } label: {
                        Label("2つの産地を比較", systemImage: "rectangle.split.2x1")
                            .frame(minHeight: 44)
                    }
                    .accessibilityIdentifier("regionMap.comparison.link")
                }
                DisclosureGroup("地図の出典と注意事項") {
                    VStack(alignment: .leading, spacing: 12) {
                        ForEach(document.sourceIDs.compactMap(store.source)) { source in
                            Text(source.name).font(.headline)
                            Text(source.license)
                            Text(source.note)
                            Text("確認日：\(source.checkedAt)")
                            if let rawURL = source.url, let url = URL(string: rawURL) {
                                Link("参照ページを開く", destination: url).frame(minHeight: 44)
                            }
                        }
                    }
                    .font(.footnote)
                }
            }
        } else {
            PaywallView(triggerFeature: .fullRegionMaps)
        }
    }

    private var modePicker: some View {
        Picker("表示方法", selection: $displayMode) {
            Text("地図").tag(0)
            Text("一覧").tag(1)
        }
        .frame(minHeight: 44)
        .accessibilityIdentifier("atlas.displayMode")
    }
}

struct AtlasRegionSummary: View {
    let region: MapRegion
    var photoHeight: CGFloat = 150

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            RegionPhotoView(regionID: region.id, height: photoHeight)
            Text(region.nameJapanese).font(.title2.bold()).foregroundStyle(.primary)
            Text(region.nameOriginal).font(.subheadline).foregroundStyle(AppTheme.forest)
            Text(region.comparison.wineStyles.summary)
                .font(.subheadline).foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

struct QuestionRegionLinksView: View {
    @Environment(EntitlementStore.self) private var entitlementStore
    let question: StudyQuestion
    private let store: RegionMapStore = {
#if DEBUG
        if ProcessInfo.processInfo.arguments.contains("-UITestRegionMapLoadFailure") {
            return RegionMapStore(data: nil)
        }
#endif
        return .shared
    }()

    var body: some View {
        if entitlementStore.policy.canAccessQuestion(id: question.id, studyMode: question.studyMode) {
            if let error = store.loadError {
                Text(error).font(.footnote).foregroundStyle(.secondary)
            } else {
                let matches = matchingRegions
                if !matches.isEmpty {
                    VStack(alignment: .leading, spacing: 12) {
                        Label("解説の産地を地図で見る", systemImage: "map")
                            .font(.headline)
                        ForEach(matches) { match in
                            NavigationLink {
                                CountryRegionMapView(document: match.document, store: store,
                                    initialSelectedRegionID: match.region.id, allowsRegionNavigation: false)
                            } label: {
                                VStack(alignment: .leading, spacing: 8) {
                                    RegionPhotoView(regionID: match.region.id, height: 100)
                                    Label(match.region.nameJapanese, systemImage: "mappin.and.ellipse")
                                        .frame(minHeight: 44)
                                }
                            }
                            .accessibilityIdentifier("question.region.\(match.region.id)")
                        }
                    }
                    .accessibilityIdentifier("question.regions")
                }
            }
        }
    }

    private struct RegionMatch: Identifiable {
        let document: RegionMapDocument
        let region: MapRegion
        var id: String { region.id }
    }

    private var matchingRegions: [RegionMatch] {
        let item = StudyFocusItem(questionID: question.id, geography: question.geography,
            countries: question.countries.isEmpty ? nil : question.countries,
            regions: question.regions.isEmpty ? nil : question.regions,
            grapeVarieties: question.grapeVarieties, wineType: question.wineType,
            category: question.category, difficulty: question.difficulty,
            cognitiveSkill: question.cognitiveSkill)
        return store.maps.filter { entitlementStore.policy.canAccessRegionMap(country: $0.country) }
            .flatMap { document in
                document.regions.filter { region in
                    RegionStudyQuery.matchingQuestionIDs(focusValues: region.focusValues, items: [item])
                        .contains(question.id)
                }.map { RegionMatch(document: document, region: $0) }
            }
    }
}
