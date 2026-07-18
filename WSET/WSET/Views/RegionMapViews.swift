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
    @Environment(EntitlementStore.self) private var entitlementStore
    @Query private var questions: [StudyQuestion]
    @Query private var progressRecords: [QuestionProgress]
    @Query private var attempts: [StudyAttempt]
    @State private var selectedRegionID: String?
    @State private var showingSelectedRegion = false

    let document: RegionMapDocument
    let store: RegionMapStore

    init(document: RegionMapDocument, store: RegionMapStore = .shared) {
        self.document = document
        self.store = store
        _selectedRegionID = State(initialValue: document.regions.first?.id)
    }

    private var selectedRegion: MapRegion? {
        guard let selectedRegionID else { return nil }
        return document.regions.first { $0.id == selectedRegionID }
    }

    private var countryStatistics: RegionStudyStatistics {
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

    var body: some View {
        if entitlementStore.policy.canAccessRegionMap(country: document.country) {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                countrySummary

                RegionMapCanvasView(
                    document: document,
                    selectedRegionID: selectedRegionID,
                    statistics: regionStatistics,
                    onSelect: { region in
                        selectedRegionID = region.id
                        showingSelectedRegion = true
                    }
                )
                .frame(maxWidth: 520)
                .frame(maxWidth: .infinity)
                .aspectRatio(document.aspectRatio, contentMode: .fit)

                Label(
                    "産地マーカーは学習用の概略位置です。法的境界や正確な縮尺を表しません。",
                    systemImage: "info.circle"
                )
                .font(.footnote)
                .foregroundStyle(.secondary)

                VStack(alignment: .leading, spacing: 10) {
                    Text("産地一覧")
                        .font(.headline)
                    ForEach(document.regions) { region in
                        NavigationLink {
                            RegionDetailView(region: region, country: document.country)
                        } label: {
                            RegionListRow(
                                region: region,
                                statistics: regionStatistics(region),
                                isSelected: selectedRegionID == region.id
                            )
                        }
                        .buttonStyle(.plain)
                        .simultaneousGesture(
                            TapGesture().onEnded { selectedRegionID = region.id }
                        )
                        .accessibilityIdentifier("regionMap.list.\(region.id)")
                    }
                }

                sourceDisclosure
                }
                .padding()
            }
            .navigationTitle(document.nameJapanese)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                if document.regions.count >= 2 {
                    ToolbarItem(placement: .topBarTrailing) {
                        NavigationLink {
                            RegionComparisonView(document: document)
                        } label: {
                            Label("比較", systemImage: "rectangle.split.2x1")
                        }
                    }
                }
            }
            .navigationDestination(isPresented: $showingSelectedRegion) {
                if let selectedRegion {
                    RegionDetailView(region: selectedRegion, country: document.country)
                }
            }
        } else {
            PaywallView(triggerFeature: .fullRegionMaps)
        }
    }

    private var countrySummary: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .firstTextBaseline) {
                VStack(alignment: .leading) {
                    Text(document.nameJapanese)
                        .font(.title2.bold())
                    Text(document.nameOriginal)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                RegionProgressBadge(statistics: countryStatistics)
            }
            HStack(spacing: 18) {
                MetricLabel(title: "関連問題", value: "\(countryStatistics.questionCount)問")
                MetricLabel(
                    title: "学習済み",
                    value: "\(countryStatistics.studiedQuestionCount)問"
                )
                MetricLabel(title: "正答率", value: percentage(countryStatistics.accuracy))
            }
        }
        .padding()
        .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 16))
    }

    private var sourceDisclosure: some View {
        DisclosureGroup("地図の出典と注意事項") {
            VStack(alignment: .leading, spacing: 10) {
                ForEach(document.sourceIDs.compactMap(store.source)) { source in
                    Text(source.name)
                        .font(.subheadline.weight(.semibold))
                    LabeledContent("権利", value: source.license)
                        .font(.caption)
                    LabeledContent("確認日", value: source.checkedAt)
                        .font(.caption)
                    Text(source.note)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    if let rawURL = source.url, let url = URL(string: rawURL) {
                        Link("参照ページを開く", destination: url)
                    }
                }
            }
            .padding(.top, 8)
        }
        .font(.footnote)
    }

    private func regionStatistics(_ region: MapRegion) -> RegionStudyStatistics {
        RegionStudyQuery.statistics(
            region: region,
            questions: accessibleQuestions,
            progress: progressRecords,
            attempts: attempts
        )
    }
}

struct RegionMapCanvasView: View {
    let document: RegionMapDocument
    let selectedRegionID: String?
    let statistics: (MapRegion) -> RegionStudyStatistics
    let onSelect: (MapRegion) -> Void

    var body: some View {
        ZStack {
            Image(document.assetName)
                .resizable()
                .scaledToFit()
                .accessibilityHidden(true)

            GeometryReader { proxy in
                ForEach(document.regions) { region in
                    RegionMarkerButton(
                        region: region,
                        statistics: statistics(region),
                        isSelected: selectedRegionID == region.id,
                        canvasSize: proxy.size,
                        onSelect: { onSelect(region) }
                    )
                    .position(
                        x: region.position.x * proxy.size.width,
                        y: region.position.y * proxy.size.height
                    )
                }
            }
        }
    }
}

private struct RegionMarkerButton: View {
    let region: MapRegion
    let statistics: RegionStudyStatistics
    let isSelected: Bool
    let canvasSize: CGSize
    let onSelect: () -> Void

    var body: some View {
        Button(action: onSelect) {
            ZStack {
                Circle()
                    .fill(isSelected ? AppTheme.wine : Color.white)
                    .frame(width: 20, height: 20)
                    .overlay {
                        Circle()
                            .stroke(AppTheme.wine, lineWidth: isSelected ? 4 : 3)
                    }
                    .shadow(radius: 1)

                Text(region.nameJapanese)
                    .font(.caption2.weight(.bold))
                    .lineLimit(1)
                    .minimumScaleFactor(0.65)
                    .padding(.horizontal, 5)
                    .padding(.vertical, 3)
                    .foregroundStyle(AppTheme.wine)
                    .background(.regularMaterial, in: Capsule())
                    .offset(
                        x: region.labelOffset.x * canvasSize.width,
                        y: region.labelOffset.y * canvasSize.height
                    )
            }
            .frame(width: 112, height: 52)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityLabel(region.nameJapanese)
        .accessibilityValue(
            "関連\(statistics.questionCount)問、正答率\(percentage(statistics.accuracy))"
        )
        .accessibilityHint("産地の詳細を開きます")
        .accessibilityIdentifier("regionMap.marker.\(region.id)")
    }
}

private struct RegionListRow: View {
    let region: MapRegion
    let statistics: RegionStudyStatistics
    let isSelected: Bool

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: isSelected ? "mappin.circle.fill" : "mappin.circle")
                .font(.title3)
                .foregroundStyle(AppTheme.wine)
                .accessibilityHidden(true)
            VStack(alignment: .leading, spacing: 3) {
                Text(region.nameJapanese)
                    .font(.body.weight(.semibold))
                Text(region.nameOriginal)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            VStack(alignment: .trailing, spacing: 3) {
                Text("\(statistics.questionCount)問")
                    .font(.subheadline.weight(.semibold))
                Text(statistics.attemptCount == 0 ? "未学習" : "正答率 \(percentage(statistics.accuracy))")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Image(systemName: "chevron.right")
                .font(.caption.bold())
                .foregroundStyle(.tertiary)
        }
        .padding(12)
        .background(
            isSelected ? AppTheme.wineSoft : Color(.secondarySystemGroupedBackground),
            in: RoundedRectangle(cornerRadius: 13)
        )
        .overlay {
            RoundedRectangle(cornerRadius: 13)
                .stroke(isSelected ? AppTheme.wine : .clear, lineWidth: 2)
        }
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

    private var grapeVarieties: [GrapeVarietyFrequency] {
        Array(
            RegionStudyQuery.relatedGrapeVarieties(
                region: region,
                questions: accessibleQuestions
            ).prefix(8)
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

    var body: some View {
        if entitlementStore.policy.canAccessRegionMap(country: country) {
            List {
            Section {
                VStack(alignment: .leading, spacing: 6) {
                    Text(region.nameJapanese)
                        .font(.title2.bold())
                    Text(region.nameOriginal)
                        .foregroundStyle(AppTheme.wine)
                    Text(country)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .padding(.vertical, 4)
            }

            Section("学習状況") {
                LabeledContent("関連問題", value: "\(statistics.questionCount)問")
                LabeledContent("学習済み", value: "\(statistics.studiedQuestionCount)問")
                LabeledContent("カバー率", value: percentage(statistics.coverage))
                LabeledContent("正答率", value: percentage(statistics.accuracy))
                LabeledContent("復習期限", value: "\(statistics.dueQuestionCount)問")
            }

            Section {
                HStack(spacing: 12) {
                    studyButton(count: 10)
                    studyButton(count: 20)
                }
            } header: {
                Text("重点学習")
            } footer: {
                Text("該当問題が指定数より少ない場合は、該当する全問題を出題します。")
            }

            if !grapeVarieties.isEmpty {
                Section("主要品種") {
                    ForEach(grapeVarieties) { grape in
                        LabeledContent(grape.name, value: "\(grape.questionCount)問")
                    }
                }
            }

            if !relatedTerms.isEmpty {
                Section("関連用語（\(relatedTerms.count)件）") {
                    ForEach(relatedTerms.prefix(20)) { term in
                        NavigationLink {
                            GlossaryTermDetailView(term: term)
                        } label: {
                            VStack(alignment: .leading, spacing: 3) {
                                Text(term.nameJapanese)
                                Text(term.summary)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                    .lineLimit(2)
                            }
                        }
                    }
                }
            }

            if !relatedQuestions.isEmpty {
                Section("関連問題（\(relatedQuestions.count)問）") {
                    ForEach(relatedQuestions.prefix(20)) { question in
                        NavigationLink {
                            QuestionDetailView(question: question)
                        } label: {
                            Text(question.displayPrompt)
                                .lineLimit(2)
                        }
                    }
                }
            }
            }
            .navigationTitle("産地詳細")
            .navigationBarTitleDisplayMode(.inline)
            .accessibilityIdentifier("regionMap.detail.\(region.id)")
            .navigationDestination(isPresented: $showingSession) {
                StudySessionView(questions: sessionQuestions)
            }
        } else {
            PaywallView(triggerFeature: .fullRegionMaps)
        }
    }

    private func studyButton(count: Int) -> some View {
        Button {
            sessionQuestions = Array(relatedQuestions.shuffled().prefix(count))
            showingSession = !sessionQuestions.isEmpty
        } label: {
            Label("\(min(count, relatedQuestions.count))問", systemImage: "scope")
                .frame(maxWidth: .infinity)
        }
        .buttonStyle(.borderedProminent)
        .tint(AppTheme.wine)
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
                    .tint(AppTheme.wine)
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
