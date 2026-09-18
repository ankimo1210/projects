import SwiftData
import SwiftUI

struct RegionMapHubView: View {
    @Environment(EntitlementStore.self) private var entitlementStore
    @Query private var questions: [StudyQuestion]
    @Query private var progressRecords: [QuestionProgress]
    @Query private var attempts: [StudyAttempt]

    private let store: RegionMapStore

    init(store: RegionMapStore? = nil) {
#if DEBUG
        if ProcessInfo.processInfo.arguments.contains("-UITestRegionMapLoadFailure") {
            self.store = RegionMapStore(data: nil)
        } else {
            self.store = store ?? .shared
        }
#else
        self.store = store ?? .shared
#endif
    }

    var body: some View {
        List {
            if store.loadError == nil {
                Section {
                    ForEach(store.maps) { document in
                        NavigationLink {
                            if entitlementStore.policy.canAccessRegionMap(
                                country: document.country
                            ) {
                                CountryRegionMapView(document: document, store: store)
                            } else {
                                PaywallView(triggerFeature: .fullRegionMaps)
                            }
                        } label: {
                            RegionMapCountryRow(
                                document: document,
                                statistics: countryStatistics(document)
                            )
                        }
                        .accessibilityIdentifier("regionMap.country.\(document.id)")
                    }
                } header: {
                    Text("国別マップ")
                } footer: {
                    Text("地図、問題、用語、学習進捗はすべて端末内のデータを使用します。")
                }

                if let document = store.maps.first, document.regions.count >= 2 {
                    Section("比較学習") {
                        NavigationLink {
                            RegionComparisonView(document: document, store: store)
                        } label: {
                            Label("2つの産地を比較", systemImage: "rectangle.split.2x1")
                        }
                        .accessibilityIdentifier("regionMap.comparison.link")
                    }
                }
            }
        }
        .navigationTitle("産地マップ")
        .overlay {
            if let loadError = store.loadError {
                ContentUnavailableView(
                    "産地マップを利用できません",
                    systemImage: "map.fill",
                    description: Text(loadError)
                )
                .accessibilityIdentifier("regionMap.loadError")
            } else if store.maps.isEmpty {
                ContentUnavailableView(
                    "収録マップがありません",
                    systemImage: "map",
                    description: Text("次のアプリ更新をお待ちください。")
                )
            }
        }
    }

    private func countryStatistics(_ document: RegionMapDocument) -> RegionStudyStatistics {
        RegionStudyQuery.statistics(
            focusValues: [document.country],
            questions: accessibleQuestions,
            progress: progressRecords,
            attempts: attempts
        )
    }

    private var accessibleQuestions: [StudyQuestion] {
        questions.filter {
            entitlementStore.policy.canAccessQuestion(id: $0.id, studyMode: $0.studyMode)
        }
    }
}

private struct RegionMapCountryRow: View {
    let document: RegionMapDocument
    let statistics: RegionStudyStatistics

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .firstTextBaseline) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(document.nameJapanese)
                        .font(.headline)
                    Text(document.nameOriginal)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Text("\(document.regions.count)産地")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(AppTheme.wine)
            }
            ProgressView(
                value: Double(statistics.studiedQuestionCount),
                total: Double(max(statistics.questionCount, 1))
            )
            .tint(AppTheme.wine)
            Text("関連\(statistics.questionCount)問・学習済み\(statistics.studiedQuestionCount)問")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(.vertical, 3)
    }
}

struct CountryRegionMapView: View {
    let document: RegionMapDocument
    let store: RegionMapStore
    let initialSelectedRegionID: String?
    let allowsRegionNavigation: Bool

    init(document: RegionMapDocument, store: RegionMapStore = .shared,
         initialSelectedRegionID: String? = nil, allowsRegionNavigation: Bool = true) {
        self.document = document
        self.store = store
        self.initialSelectedRegionID = initialSelectedRegionID
        self.allowsRegionNavigation = allowsRegionNavigation
    }

    var body: some View {
        ScrollView {
            AtlasExplorerContent(document: document, store: store,
                initialSelectedRegionID: initialSelectedRegionID,
                allowsRegionNavigation: allowsRegionNavigation)
                .padding()
        }
        .background(AppTheme.paper)
        .navigationTitle(document.nameJapanese)
        .navigationBarTitleDisplayMode(.inline)
    }
}

struct RegionMapCanvasView: View {
    let document: RegionMapDocument
    let selectedRegionID: String?
    let onSelect: (MapRegion) -> Void

    var body: some View {
        GeometryReader { proxy in
            ZStack {
                Image(document.assetName)
                    .resizable()
                    .scaledToFit()
                    .accessibilityHidden(true)
                // Dots stay on the exact projected representative positions, even in a cluster.
                ForEach(document.regions) { region in
                    Circle()
                        .fill(region.id == selectedRegionID ? AppTheme.wine : AppTheme.forest)
                        .frame(width: region.id == selectedRegionID ? 14 : 7,
                               height: region.id == selectedRegionID ? 14 : 7)
                        .overlay { Circle().stroke(AppTheme.surface, lineWidth: 2) }
                        .position(point(region, size: proxy.size))
                        .accessibilityHidden(true)
                }
                ForEach(clusters(size: proxy.size)) { cluster in
                    if cluster.regions.count == 1, let region = cluster.regions.first {
                        Button { onSelect(region) } label: {
                            Image(systemName: region.id == selectedRegionID ? "mappin.circle.fill" : "mappin.circle")
                                .font(.system(size: 26))
                                .foregroundStyle(AppTheme.forest)
                                .frame(width: 44, height: 44)
                                .background(AppTheme.surface.opacity(0.9), in: Circle())
                                .contentShape(Circle())
                        }
                        .buttonStyle(.plain)
                        .accessibilityLabel(region.nameJapanese)
                        .accessibilityValue(region.id == selectedRegionID ? "選択中" : "")
                        .accessibilityHint("産地の写真と概要を表示します")
                        .accessibilityIdentifier("regionMap.marker.\(region.id)")
                        .position(cluster.center)
                    } else {
                        Menu {
                            ForEach(cluster.regions) { region in
                                Button(region.nameJapanese) { onSelect(region) }
                                    .accessibilityIdentifier("regionMap.marker.\(region.id)")
                            }
                        } label: {
                            Image(systemName: "\(cluster.regions.count).circle.fill")
                                .font(.system(size: 30))
                                .foregroundStyle(AppTheme.forest)
                                .frame(width: 44, height: 44)
                                .background(AppTheme.surface, in: Circle())
                                .overlay { Circle().stroke(AppTheme.forest, lineWidth: 2) }
                        }
                        .accessibilityLabel("近接する\(cluster.regions.count)産地：\(cluster.regions.map(\.nameJapanese).joined(separator: "、"))")
                        .accessibilityHint("産地名を選択してください")
                        .accessibilityIdentifier("regionMap.cluster.\(cluster.id)")
                        .position(cluster.center)
                    }
                }
            }
        }
    }

    private struct Cluster: Identifiable {
        let regions: [MapRegion]
        let center: CGPoint
        var id: String { regions.map(\.id).joined(separator: ".") }
    }

    private func point(_ region: MapRegion, size: CGSize) -> CGPoint {
        CGPoint(x: region.position.x * size.width, y: region.position.y * size.height)
    }

    /// Repeatedly merge intersecting 44pt controls. No hidden overlapping hit rectangles.
    private func clusters(size: CGSize) -> [Cluster] {
        var groups = document.regions.map { [$0] }
        func center(_ group: [MapRegion]) -> CGPoint {
            let count = Double(group.count)
            let x = group.reduce(0.0) { $0 + $1.position.x } / count * size.width
            let y = group.reduce(0.0) { $0 + $1.position.y } / count * size.height
            return CGPoint(x: min(max(x, 22), max(22, size.width - 22)),
                           y: min(max(y, 22), max(22, size.height - 22)))
        }
        var didMerge = true
        while didMerge {
            didMerge = false
            outer: for i in groups.indices {
                for j in groups.indices where j > i {
                    let a = center(groups[i]), b = center(groups[j])
                    if abs(a.x - b.x) < 48 && abs(a.y - b.y) < 48 {
                        groups[i].append(contentsOf: groups[j])
                        groups.remove(at: j)
                        didMerge = true
                        break outer
                    }
                }
            }
        }
        return groups.map { Cluster(regions: $0, center: center($0)) }
    }
}

struct RegionDetailView: View {
    @Environment(EntitlementStore.self) private var entitlementStore
    @Query private var questions: [StudyQuestion]
    @Query private var progressRecords: [QuestionProgress]
    @Query private var attempts: [StudyAttempt]
    @State private var sessionQuestions: [StudyQuestion] = []
    @State private var showingSession = false

    let region: MapRegion
    let country: String
    private let referenceStore = ReferenceStore.shared

    private var relatedQuestions: [StudyQuestion] {
        RegionStudyQuery.matchingQuestions(region: region, questions: accessibleQuestions)
    }

    private var statistics: RegionStudyStatistics {
        RegionStudyQuery.statistics(
            region: region,
            questions: accessibleQuestions,
            progress: progressRecords,
            attempts: attempts
        )
    }

    private var relatedTerms: [ReferenceTerm] {
        RegionStudyQuery.relatedTerms(region: region, terms: referenceStore.terms)
            .filter { entitlementStore.policy.canAccessGlossaryTerm(id: $0.id) }
    }

    private var accessibleQuestions: [StudyQuestion] {
        questions.filter {
            entitlementStore.policy.canAccessQuestion(id: $0.id, studyMode: $0.studyMode)
        }
    }

    @Environment(\.dynamicTypeSize) private var dynamicTypeSize
    @State private var selectedAxis = RegionComparisonAxis.climateInfluence
    @State private var showingPhotoCredits = false

    private let mainAxes: [RegionComparisonAxis] = [.climateInfluence, .grapeVarieties, .wineStyles]

    var body: some View {
        if entitlementStore.policy.canAccessRegionMap(country: country) {
            ScrollView {
                VStack(alignment: .leading, spacing: 24) {
                    RegionPhotoView(regionID: region.id, height: 240)
                    VStack(alignment: .leading, spacing: 8) {
                        Text(country).font(.subheadline).foregroundStyle(AppTheme.forest)
                        Text(region.nameJapanese).font(.largeTitle.bold())
                        Text(region.nameOriginal).font(.title3).foregroundStyle(AppTheme.forest)
                        if AtlasMediaStore.shared.photo(for: region.id) != nil {
                            Button { showingPhotoCredits = true } label: {
                                Label("写真の出典", systemImage: "info.circle")
                                    .font(.footnote).frame(minHeight: 44)
                            }
                            .accessibilityIdentifier("atlas.photo.credits")
                        }
                    }
                    VStack(alignment: .leading, spacing: 16) {
                        if dynamicTypeSize.isAccessibilitySize {
                            knowledgePicker.pickerStyle(.menu)
                        } else {
                            knowledgePicker.pickerStyle(.segmented)
                        }
                        factContent(selectedAxis)
                    }
                    .padding(16)
                    .background(AppTheme.surface, in: RoundedRectangle(cornerRadius: 20))

                    VStack(alignment: .leading, spacing: 12) {
                        Text("この産地を学ぶ").font(.title2.bold())
                        Text("読んだ知識を、問題で確かめましょう。")
                            .foregroundStyle(.secondary)
                        studyButton(count: 10)
                        studyButton(count: 20)
                        Text("該当問題が指定数より少ない場合は、該当する全問題を出題します。")
                            .font(.footnote).foregroundStyle(.secondary)
                    }

                    DisclosureGroup("土壌・栽培・醸造と、ワインを形づくる要因") {
                        VStack(alignment: .leading, spacing: 24) {
                            ForEach(RegionComparisonAxis.allCases.filter { !mainAxes.contains($0) }) { axis in
                                factContent(axis)
                            }
                        }
                        .padding(.top, 16)
                    }
                    if let document = RegionMapStore.shared.maps.first(where: { $0.country == country }) {
                        NavigationLink {
                            RegionComparisonView(document: document)
                        } label: {
                            Label("ほかの産地と比較する", systemImage: "rectangle.split.2x1")
                                .frame(minHeight: 44)
                        }
                    }
                    DisclosureGroup("学習状況") {
                        VStack(spacing: 12) {
                            LabeledContent("関連問題", value: "\(statistics.questionCount)問")
                            LabeledContent("学習済み", value: "\(statistics.studiedQuestionCount)問")
                            LabeledContent("カバー率", value: percentage(statistics.coverage))
                            LabeledContent("正答率", value: percentage(statistics.accuracy))
                            LabeledContent("復習期限", value: "\(statistics.dueQuestionCount)問")
                        }.padding(.top, 12)
                    }
                    if !relatedTerms.isEmpty {
                        DisclosureGroup("関連用語（\(relatedTerms.count)件）") {
                            VStack(alignment: .leading, spacing: 16) {
                                ForEach(relatedTerms.prefix(20)) { term in
                                    NavigationLink {
                                        GlossaryTermDetailView(term: term)
                                    } label: {
                                        VStack(alignment: .leading, spacing: 6) {
                                            Text(term.nameJapanese).font(.headline)
                                            Text(term.summary).font(.subheadline).foregroundStyle(.secondary)
                                        }.frame(minHeight: 44)
                                    }
                                }
                            }.padding(.top, 12)
                        }
                    }
                    if !relatedQuestions.isEmpty {
                        DisclosureGroup("関連問題（\(relatedQuestions.count)問）") {
                            VStack(alignment: .leading, spacing: 16) {
                                ForEach(relatedQuestions.prefix(20)) { question in
                                    NavigationLink {
                                        QuestionDetailView(question: question)
                                    } label: {
                                        Text(question.displayPrompt).frame(minHeight: 44)
                                    }
                                    .accessibilityIdentifier("atlas.relatedQuestion.\(question.id)")
                                }
                            }.padding(.top, 12)
                        }
                        .accessibilityIdentifier("atlas.relatedQuestions")
                    }
                }
                .padding()
            }
            .background(AppTheme.paper)
            .navigationTitle("産地詳細")
            .navigationBarTitleDisplayMode(.inline)
            .accessibilityIdentifier("regionMap.detail.\(region.id)")
            .navigationDestination(isPresented: $showingSession) {
                StudySessionView(questions: sessionQuestions)
            }
            .sheet(isPresented: $showingPhotoCredits) {
                if let photo = AtlasMediaStore.shared.photo(for: region.id) {
                    AtlasPhotoCreditsView(photo: photo)
                }
            }
        } else {
            PaywallView(triggerFeature: .fullRegionMaps)
        }
    }

    private var knowledgePicker: some View {
        Picker("産地の特徴", selection: $selectedAxis) {
            Text("気候").tag(RegionComparisonAxis.climateInfluence)
            Text("品種").tag(RegionComparisonAxis.grapeVarieties)
            Text("スタイル").tag(RegionComparisonAxis.wineStyles)
        }
        .frame(minHeight: 44)
        .accessibilityIdentifier("atlas.detail.topic")
    }

    private func factContent(_ axis: RegionComparisonAxis) -> some View {
        let fact = region.comparison.fact(for: axis)
        return VStack(alignment: .leading, spacing: 12) {
            Text(axis.title).font(.headline).foregroundStyle(AppTheme.forest)
            Text(fact.summary).font(.body).fixedSize(horizontal: false, vertical: true)
            Text(fact.keywords.joined(separator: "・"))
                .font(.subheadline).foregroundStyle(.secondary)
            DisclosureGroup("解説の出典・確認日") {
                VStack(alignment: .leading, spacing: 8) {
                    ForEach(fact.sourceIDs, id: \.self) { id in
                        if let source = RegionMapStore.shared.source(id: id) {
                            Text(source.name)
                            if let rawURL = source.url, let url = URL(string: rawURL) {
                                Link("参照ページを開く", destination: url).frame(minHeight: 44)
                            }
                        }
                    }
                    Text("確認日：\(fact.checkedAt)・情報基準日：\(fact.effectiveDate)")
                }.padding(.top, 8)
            }
            .font(.footnote)
        }
    }

    private func studyButton(count: Int) -> some View {
        Button {
            sessionQuestions = Array(relatedQuestions.shuffled().prefix(count))
            showingSession = !sessionQuestions.isEmpty
        } label: {
            Label("\(min(count, relatedQuestions.count))問", systemImage: "scope")
                .frame(maxWidth: .infinity, minHeight: 44)
        }
        .buttonStyle(.borderedProminent)
        .tint(AppTheme.wineAction)
        .disabled(relatedQuestions.isEmpty)
        .accessibilityLabel("\(region.nameJapanese)を最大\(count)問学習")
        .accessibilityIdentifier("regionMap.study.\(count)")
    }
}

struct RegionComparisonView: View {
    @Query private var questions: [StudyQuestion]
    @Query private var progressRecords: [QuestionProgress]
    @Query private var attempts: [StudyAttempt]
    @State private var firstRegionID: String
    @State private var secondRegionID: String
    @State private var sessionQuestions: [StudyQuestion] = []
    @State private var showingSession = false

    let document: RegionMapDocument
    private let store: RegionMapStore

    init(document: RegionMapDocument, store: RegionMapStore = .shared) {
        self.document = document
        self.store = store
        _firstRegionID = State(initialValue: document.regions.first?.id ?? "")
        _secondRegionID = State(initialValue: document.regions.dropFirst().first?.id ?? "")
    }

    private var firstRegion: MapRegion? {
        document.regions.first { $0.id == firstRegionID }
    }

    private var secondRegion: MapRegion? {
        document.regions.first { $0.id == secondRegionID }
    }

    private var comparisonQuestions: [StudyQuestion] {
        guard let firstRegion, let secondRegion else { return [] }
        return RegionStudyQuery.matchingQuestions(
            focusValues: firstRegion.focusValues + secondRegion.focusValues,
            questions: questions
        )
    }

    private var writtenComparisonQuestions: [StudyQuestion] {
        guard let firstRegion, let secondRegion else { return [] }
        return RegionStudyQuery.matchingWrittenQuestions(
            focusValues: firstRegion.focusValues + secondRegion.focusValues,
            questions: questions
        )
    }

    var body: some View {
        PremiumFeatureGate(feature: .regionComparison) {
            comparisonContent
        }
    }

    private var comparisonContent: some View {
        Form {
            Section("比較する産地") {
                Picker("産地1", selection: $firstRegionID) {
                    ForEach(document.regions) { region in
                        Text(region.nameJapanese).tag(region.id)
                    }
                }
                Picker("産地2", selection: $secondRegionID) {
                    ForEach(document.regions) { region in
                        Text(region.nameJapanese).tag(region.id)
                    }
                }
            }

            if firstRegionID == secondRegionID {
                Section {
                    Label("異なる2産地を選択してください。", systemImage: "exclamationmark.triangle")
                        .foregroundStyle(.secondary)
                }
            } else if let firstRegion, let secondRegion {
                Section {
                    ComparisonHeader(first: firstRegion, second: secondRegion)
                    ForEach(RegionComparisonAxis.allCases) { axis in
                        RegionComparisonAxisRow(
                            axis: axis,
                            firstRegion: firstRegion,
                            secondRegion: secondRegion,
                            sourceNames: sourceNames
                        )
                        .accessibilityIdentifier(
                            "regionMap.comparison.axis.\(axis.rawValue)"
                        )
                    }
                } header: {
                    Text("産地知識の比較")
                } footer: {
                    Text("同じ比較キーワードを共通点、片方だけのキーワードを相違点として表示します。説明と出典も軸ごとに確認できます。")
                }

                Section("学習状況の比較") {
                    ComparisonHeader(first: firstRegion, second: secondRegion)
                    ComparisonMetricRow(
                        title: "関連問題",
                        first: "\(statistics(firstRegion).questionCount)問",
                        second: "\(statistics(secondRegion).questionCount)問"
                    )
                    ComparisonMetricRow(
                        title: "カバー率",
                        first: percentage(statistics(firstRegion).coverage),
                        second: percentage(statistics(secondRegion).coverage)
                    )
                    ComparisonMetricRow(
                        title: "正答率",
                        first: percentage(statistics(firstRegion).accuracy),
                        second: percentage(statistics(secondRegion).accuracy)
                    )
                    ComparisonMetricRow(
                        title: "主要品種",
                        first: grapeSummary(firstRegion),
                        second: grapeSummary(secondRegion)
                    )
                }

                if !writtenComparisonQuestions.isEmpty {
                    Section {
                        ForEach(writtenComparisonQuestions) { question in
                            NavigationLink {
                                QuestionDetailView(question: question)
                            } label: {
                                VStack(alignment: .leading, spacing: 4) {
                                    Label("記述式", systemImage: "square.and.pencil")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(AppTheme.wine)
                                    Text(question.displayPrompt)
                                        .lineLimit(3)
                                }
                            }
                            .accessibilityIdentifier("regionMap.comparison.written.link")
                        }
                    } header: {
                        Text("関連する記述式問題")
                    } footer: {
                        Text("選択中のどちらかの産地タグに一致する記述式問題です。")
                    }
                }

                Section {
                    Button {
                        sessionQuestions = Array(comparisonQuestions.shuffled().prefix(20))
                        showingSession = !sessionQuestions.isEmpty
                    } label: {
                        Label(
                            "2産地をまとめて学習（最大20問）",
                            systemImage: "rectangle.split.2x1"
                        )
                        .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(AppTheme.wineAction)
                    .disabled(comparisonQuestions.isEmpty)
                    .accessibilityIdentifier("regionMap.comparison.study")
                } footer: {
                    Text("両方の産地タグに一致する問題を重複なく出題します。")
                }
            }
        }
        .navigationTitle("産地比較")
        .navigationBarTitleDisplayMode(.inline)
        .accessibilityIdentifier("regionMap.comparison")
        .navigationDestination(isPresented: $showingSession) {
            StudySessionView(questions: sessionQuestions)
        }
    }

    private func statistics(_ region: MapRegion) -> RegionStudyStatistics {
        RegionStudyQuery.statistics(
            region: region,
            questions: questions,
            progress: progressRecords,
            attempts: attempts
        )
    }

    private func grapeSummary(_ region: MapRegion) -> String {
        let grapes = RegionStudyQuery.relatedGrapeVarieties(region: region, questions: questions)
            .prefix(3)
            .map(\.name)
        return grapes.isEmpty ? "—" : grapes.joined(separator: "・")
    }

    private func sourceNames(_ identifiers: [String]) -> String {
        let names = identifiers.reduce(into: [String]()) { result, identifier in
            guard let name = store.source(id: identifier)?.name,
                  !result.contains(name)
            else { return }
            result.append(name)
        }
        return names.isEmpty ? "出典情報なし" : names.joined(separator: "、")
    }
}

private struct ComparisonHeader: View {
    let first: MapRegion
    let second: MapRegion

    var body: some View {
        HStack {
            Text(first.nameJapanese)
                .frame(maxWidth: .infinity)
            Image(systemName: "arrow.left.arrow.right")
                .foregroundStyle(AppTheme.wine)
                .accessibilityHidden(true)
            Text(second.nameJapanese)
                .frame(maxWidth: .infinity)
        }
        .font(.headline)
    }
}

private struct ComparisonMetricRow: View {
    let title: String
    let first: String
    let second: String

    var body: some View {
        VStack(spacing: 6) {
            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)
            HStack(alignment: .top) {
                Text(first)
                    .frame(maxWidth: .infinity)
                Divider()
                Text(second)
                    .frame(maxWidth: .infinity)
            }
            .multilineTextAlignment(.center)
        }
        .padding(.vertical, 3)
    }
}

private struct RegionComparisonAxisRow: View {
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize

    let axis: RegionComparisonAxis
    let firstRegion: MapRegion
    let secondRegion: MapRegion
    let sourceNames: ([String]) -> String

    private var firstFact: RegionComparisonFact {
        firstRegion.comparison.fact(for: axis)
    }

    private var secondFact: RegionComparisonFact {
        secondRegion.comparison.fact(for: axis)
    }

    private var commonKeywords: [String] {
        keywordComparison.common
    }

    private var firstOnlyKeywords: [String] {
        keywordComparison.firstOnly
    }

    private var secondOnlyKeywords: [String] {
        keywordComparison.secondOnly
    }

    private var keywordComparison: RegionComparisonKeywords {
        firstFact.keywordsCompared(to: secondFact)
    }

    private var comparisonLayout: AnyLayout {
        dynamicTypeSize.isAccessibilitySize
            ? AnyLayout(VStackLayout(alignment: .leading, spacing: 12))
            : AnyLayout(HStackLayout(alignment: .top, spacing: 12))
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(axis.title)
                .font(.headline)

            comparisonLayout {
                factCell(region: firstRegion, fact: firstFact)
                factCell(region: secondRegion, fact: secondFact)
            }

            VStack(alignment: .leading, spacing: 5) {
                Label(
                    commonKeywords.isEmpty
                        ? "共通点：比較キーワードの明示的一致なし"
                        : "共通点：\(commonKeywords.joined(separator: "・"))",
                    systemImage: "equal.circle"
                )
                .foregroundStyle(.secondary)

                Label(
                    "相違点：\(firstRegion.nameJapanese) — \(keywordSummary(firstOnlyKeywords))",
                    systemImage: "arrow.left"
                )
                Label(
                    "相違点：\(secondRegion.nameJapanese) — \(keywordSummary(secondOnlyKeywords))",
                    systemImage: "arrow.right"
                )
            }
            .font(.caption)

            DisclosureGroup("出典・確認日") {
                sourceRow(region: firstRegion, fact: firstFact)
                sourceRow(region: secondRegion, fact: secondFact)
            }
            .font(.caption)
        }
        .padding(.vertical, 5)
    }

    private func factCell(
        region: MapRegion,
        fact: RegionComparisonFact
    ) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(region.nameJapanese)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(AppTheme.wine)
            Text(fact.summary)
                .font(.subheadline)
            Text(fact.keywords.joined(separator: "・"))
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func sourceRow(
        region: MapRegion,
        fact: RegionComparisonFact
    ) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(region.nameJapanese)
                .fontWeight(.semibold)
            Text(sourceNames(fact.sourceIDs))
            Text("確認日：\(fact.checkedAt)・情報基準日：\(fact.effectiveDate)")
                .foregroundStyle(.secondary)
        }
        .padding(.vertical, 3)
    }

    private func keywordSummary(_ values: [String]) -> String {
        values.isEmpty ? "追加差分なし" : values.joined(separator: "・")
    }
}

private struct RegionProgressBadge: View {
    let statistics: RegionStudyStatistics

    var body: some View {
        Text(statistics.attemptCount == 0 ? "未学習" : percentage(statistics.accuracy))
            .font(.caption.weight(.bold))
            .padding(.horizontal, 9)
            .padding(.vertical, 5)
            .foregroundStyle(AppTheme.wine)
            .background(AppTheme.wineSoft, in: Capsule())
    }
}

private struct MetricLabel: View {
    let title: String
    let value: String

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(value)
                .font(.subheadline.weight(.semibold))
            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }
}

private func percentage(_ value: Double?) -> String {
    guard let value else { return "未学習" }
    return value.formatted(.percent.precision(.fractionLength(0)))
}
