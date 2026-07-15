import SwiftData
import SwiftUI

struct GlossaryView: View {
    @Query(sort: \ReferenceTermProgress.lastViewedAt, order: .reverse)
    private var progressRecords: [ReferenceTermProgress]
    @State private var searchText = ""
    @State private var selectedCategory = "すべて"

    private let store = ReferenceStore.shared

    private var categories: [String] {
        ["すべて"] + Set(store.terms.map(\.category)).sorted()
    }

    private var filteredTerms: [ReferenceTerm] {
        store.terms.filter { term in
            (selectedCategory == "すべて" || term.category == selectedCategory)
                && term.matches(searchText)
        }
    }

    private var progressByID: [String: ReferenceTermProgress] {
        Dictionary(uniqueKeysWithValues: progressRecords.map { ($0.termID, $0) })
    }

    private var bookmarkedTerms: [ReferenceTerm] {
        store.terms.filter { progressByID[$0.id]?.isBookmarked == true }
    }

    private var recentTerms: [ReferenceTerm] {
        progressRecords
            .filter { $0.lastViewedAt != nil }
            .prefix(8)
            .compactMap { store.term(id: $0.termID) }
    }

    var body: some View {
        List {
            Section {
                Picker("種別", selection: $selectedCategory) {
                    ForEach(categories, id: \.self) { category in
                        Text(category).tag(category)
                    }
                }
            }

            if searchText.isEmpty && selectedCategory == "すべて" {
                if !bookmarkedTerms.isEmpty {
                    Section("ブックマーク") {
                        ForEach(bookmarkedTerms) { term in
                            termLink(term)
                        }
                    }
                }
                if !recentTerms.isEmpty {
                    Section("最近見た用語") {
                        ForEach(recentTerms) { term in
                            termLink(term)
                        }
                    }
                }
            }

            Section("用語（\(filteredTerms.count)件）") {
                ForEach(filteredTerms) { term in
                    termLink(term)
                }
            }
        }
        .searchable(
            text: $searchText,
            prompt: "用語、意味、原語、産地、ラベルで検索"
        )
        .navigationTitle("用語辞書")
        .overlay {
            if let error = store.loadError {
                ContentUnavailableView(
                    "用語辞書を利用できません",
                    systemImage: "exclamationmark.triangle",
                    description: Text(error)
                )
            } else if filteredTerms.isEmpty {
                ContentUnavailableView.search(text: searchText)
            }
        }
    }

    private func termLink(_ term: ReferenceTerm) -> some View {
        NavigationLink {
            GlossaryTermDetailView(term: term)
        } label: {
            ReferenceTermRow(term: term)
        }
    }
}

private struct ReferenceTermRow: View {
    let term: ReferenceTerm

    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            HStack(alignment: .firstTextBaseline) {
                Text(term.nameJapanese)
                    .font(.body.weight(.semibold))
                Spacer()
                Text(term.category)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            if let original = term.nameFrench ?? term.nameEnglish,
               original != term.nameJapanese {
                Text(original)
                    .font(.caption)
                    .foregroundStyle(AppTheme.wine)
            }
            Text(term.summary)
                .font(.caption)
                .foregroundStyle(.secondary)
                .lineLimit(2)
        }
        .padding(.vertical, 3)
    }
}

struct GlossaryTermDetailView: View {
    @Environment(\.modelContext) private var modelContext
    @Query private var questions: [StudyQuestion]
    @Query private var progressRecords: [ReferenceTermProgress]
    @State private var hasRecordedView = false

    let term: ReferenceTerm
    private let store = ReferenceStore.shared

    private var progress: ReferenceTermProgress? {
        progressRecords.first { $0.termID == term.id }
    }

    private var relatedQuestions: [StudyQuestion] {
        let identifiers = Set(term.questionIDs)
        return questions
            .filter { identifiers.contains($0.id) }
            .sorted { $0.id < $1.id }
    }

    private var relatedTerms: [ReferenceTerm] {
        term.relatedTermIDs.compactMap { store.term(id: $0) }
    }

    var body: some View {
        List {
            Section {
                VStack(alignment: .leading, spacing: 8) {
                    Text(term.nameJapanese)
                        .font(.title2.bold())
                    if let reading = term.reading, !reading.isEmpty {
                        Text(reading)
                            .foregroundStyle(.secondary)
                    }
                    Text(term.category)
                        .font(.caption.weight(.semibold))
                        .padding(.horizontal, 9)
                        .padding(.vertical, 5)
                        .background(AppTheme.wineSoft, in: Capsule())
                        .foregroundStyle(AppTheme.wine)
                }
                .padding(.vertical, 4)
            }

            if term.nameEnglish != nil || term.nameFrench != nil || !term.aliases.isEmpty {
                Section("原語・別名") {
                    if let english = term.nameEnglish {
                        LabeledContent("英語", value: english)
                    }
                    if let french = term.nameFrench {
                        LabeledContent("フランス語", value: french)
                    }
                    if !term.aliases.isEmpty {
                        LabeledContent("別名", value: term.aliases.joined(separator: "・"))
                    }
                }
            }

            Section("意味") {
                Text(term.description)
                    .textSelection(.enabled)
            }

            if term.country != nil || term.region != nil || !term.labels.isEmpty {
                Section("ラベル") {
                    if let country = term.country {
                        LabeledContent("国", value: country)
                    }
                    if let region = term.region {
                        LabeledContent("産地・村", value: region)
                    }
                    if !term.labels.isEmpty {
                        Text(term.labels.joined(separator: " ・ "))
                            .foregroundStyle(.secondary)
                    }
                }
            }

            if !relatedTerms.isEmpty {
                Section("関連用語") {
                    ForEach(relatedTerms) { related in
                        NavigationLink(related.nameJapanese) {
                            GlossaryTermDetailView(term: related)
                        }
                    }
                }
            }

            if !relatedQuestions.isEmpty {
                Section("関連問題（\(relatedQuestions.count)問）") {
                    NavigationLink {
                        StudySessionView(questions: Array(relatedQuestions.prefix(20)))
                    } label: {
                        Label("この用語を重点学習", systemImage: "scope")
                    }
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

            if let source = store.source(id: term.sourceID) {
                Section("情報源") {
                    Text(source.name)
                    LabeledContent("基準日", value: source.effectiveDate)
                    LabeledContent("確認日", value: source.checkedAt)
                    if let url = URL(string: source.url), !source.url.isEmpty {
                        Link("参照ページを開く", destination: url)
                    }
                }
            }
        }
        .navigationTitle("用語")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    toggleBookmark()
                } label: {
                    Image(systemName: progress?.isBookmarked == true ? "bookmark.fill" : "bookmark")
                }
                .accessibilityLabel(
                    progress?.isBookmarked == true ? "用語のブックマークを解除" : "用語をブックマーク"
                )
            }
        }
        .onAppear { recordViewIfNeeded() }
    }

    private func currentProgress() -> ReferenceTermProgress {
        if let progress { return progress }
        let created = ReferenceTermProgress(termID: term.id)
        modelContext.insert(created)
        return created
    }

    private func recordViewIfNeeded() {
        guard !hasRecordedView else { return }
        hasRecordedView = true
        currentProgress().recordView()
        try? modelContext.save()
    }

    private func toggleBookmark() {
        let record = currentProgress()
        record.isBookmarked.toggle()
        try? modelContext.save()
    }
}

struct TermAnnotationsView: View {
    let questionID: String
    private let store = ReferenceStore.shared

    private var terms: [ReferenceTerm] {
        store.terms(forQuestionID: questionID)
    }

    var body: some View {
        if !terms.isEmpty {
            DisclosureGroup("用語注釈（\(terms.count)語）") {
                VStack(alignment: .leading, spacing: 10) {
                    ForEach(terms) { term in
                        NavigationLink {
                            GlossaryTermDetailView(term: term)
                        } label: {
                            VStack(alignment: .leading, spacing: 3) {
                                Text(term.nameJapanese)
                                    .font(.subheadline.weight(.semibold))
                                Text(term.summary)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                    .lineLimit(2)
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(.top, 8)
            }
            .padding()
            .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 14))
        }
    }
}

struct ClassificationHubView: View {
    @State private var selectedRegion = "ボルドー"
    @State private var searchText = ""

    private let store = ReferenceStore.shared
    private let regions = ["ボルドー", "ブルゴーニュ", "シャンパーニュ"]

    private var systems: [WineClassificationSystem] {
        store.classificationSystems.filter { $0.region == selectedRegion }
    }

    private func entries(for system: WineClassificationSystem) -> [WineClassificationEntry] {
        store.classificationEntries
            .filter { $0.systemID == system.id && $0.matches(searchText) }
            .sorted {
                let lhsRank = ClassificationSort.rank($0.tier)
                let rhsRank = ClassificationSort.rank($1.tier)
                if lhsRank != rhsRank { return lhsRank < rhsRank }
                if $0.village != $1.village {
                    return $0.village.localizedStandardCompare($1.village) == .orderedAscending
                }
                return $0.nameOriginal.localizedStandardCompare($1.nameOriginal) == .orderedAscending
            }
    }

    var body: some View {
        List {
            Section {
                Picker("地域", selection: $selectedRegion) {
                    ForEach(regions, id: \.self) { region in
                        Text(region).tag(region)
                    }
                }
                .pickerStyle(.segmented)
            }

            ForEach(systems) { system in
                let filtered = entries(for: system)
                if !filtered.isEmpty {
                    Section {
                        ForEach(filtered) { entry in
                            NavigationLink {
                                ClassificationEntryDetailView(entry: entry, system: system)
                            } label: {
                                ClassificationEntryRow(entry: entry)
                            }
                        }
                    } header: {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(system.nameJapanese)
                            Text("\(filtered.count)件 ・ 基準 \(system.effectiveDate)")
                                .font(.caption2)
                        }
                    } footer: {
                        Text(system.summary)
                    }
                }
            }
        }
        .searchable(text: $searchText, prompt: "名前、階級、村で検索")
        .navigationTitle("格付け一覧")
    }
}

private enum ClassificationSort {
    private static let order = [
        "特別第1級", "第1級", "第2級", "第3級", "第4級", "第5級",
        "Premier Grand Cru Classé A", "Premier Grand Cru Classé B",
        "Grand Cru Classé", "Cru Classé de Graves", "Grand Cru", "Premier Cru",
    ]

    static func rank(_ value: String) -> Int {
        order.firstIndex(of: value) ?? .max
    }
}

private struct ClassificationEntryRow: View {
    let entry: WineClassificationEntry

    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            Text(entry.nameJapanese)
                .font(.body.weight(.semibold))
            if entry.nameOriginal != entry.nameJapanese {
                Text(entry.nameOriginal)
                    .font(.caption)
                    .foregroundStyle(AppTheme.wine)
            }
            HStack {
                Text(entry.tier)
                    .foregroundStyle(AppTheme.wine)
                Text(entry.village)
                    .foregroundStyle(.secondary)
            }
            .font(.caption)
        }
        .padding(.vertical, 3)
    }
}

private struct ClassificationEntryDetailView: View {
    let entry: WineClassificationEntry
    let system: WineClassificationSystem
    private let store = ReferenceStore.shared

    var body: some View {
        List {
            Section {
                Text(entry.nameJapanese)
                    .font(.title3.bold())
                if entry.nameOriginal != entry.nameJapanese {
                    Text(entry.nameOriginal)
                        .foregroundStyle(AppTheme.wine)
                }
            }
            Section("格付け") {
                LabeledContent("制度", value: system.nameJapanese)
                LabeledContent("階級", value: entry.tier)
                LabeledContent("村・アペラシオン", value: entry.village)
                LabeledContent("サブリージョン", value: entry.subregion)
                LabeledContent("対象", value: entry.entryType)
                if let notes = entry.notes {
                    Text(notes)
                        .foregroundStyle(.secondary)
                }
            }
            if let term = store.term(id: entry.termID) {
                Section {
                    NavigationLink("辞書で詳しく見る") {
                        GlossaryTermDetailView(term: term)
                    }
                }
            }
            if let source = store.source(id: entry.sourceID) {
                Section("情報源") {
                    Text(source.name)
                    LabeledContent("基準日", value: source.effectiveDate)
                    LabeledContent("確認日", value: source.checkedAt)
                    if let url = URL(string: source.url), !source.url.isEmpty {
                        Link("参照ページを開く", destination: url)
                    }
                }
            }
        }
        .navigationTitle("格付け詳細")
        .navigationBarTitleDisplayMode(.inline)
    }
}
