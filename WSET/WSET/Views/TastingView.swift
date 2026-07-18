import SwiftData
import SwiftUI

struct TastingView: View {
    @Environment(\.modelContext) private var modelContext
    @Environment(EntitlementStore.self) private var entitlementStore
    @Query(sort: \TastingNote.tastedAt, order: .reverse) private var notes: [TastingNote]
    @State private var activeExam: TastingExamSnapshot?
    @State private var didSeedUITestNotes = false

    var body: some View {
        NavigationStack {
            List {
                Section("練習") {
                    NavigationLink {
                        if entitlementStore.policy.canCreateTastingNote(existingCount: notes.count) {
                            TastingEditorView()
                        } else {
                            PaywallView(triggerFeature: .unlimitedTastingNotes)
                        }
                    } label: {
                        Label("テイスティング記録を作成", systemImage: "square.and.pencil")
                    }

                    NavigationLink {
                        if entitlementStore.policy.canCreateTastingNote(existingCount: notes.count + 1) {
                            TwoWineTastingView()
                        } else {
                            PaywallView(triggerFeature: .unlimitedTastingNotes)
                        }
                    } label: {
                        Label("2本比較ブラインド練習", systemImage: "wineglass.fill")
                    }

                    NavigationLink {
                        if entitlementStore.policy.canCreateTastingNote(existingCount: notes.count + 1) {
                            TastingExamView()
                        } else {
                            PaywallView(triggerFeature: .unlimitedTastingNotes)
                        }
                    } label: {
                        Label(
                            activeExam == nil ? "30分テイスティング試験" : "30分試験を再開",
                            systemImage: activeExam == nil ? "timer" : "arrow.clockwise.circle.fill"
                        )
                    }
                    .accessibilityIdentifier("tasting.exam.entry")
                }

                Section {
                    NavigationLink {
                        TastingComparisonSelectionView(notes: notes)
                    } label: {
                        Label {
                            VStack(alignment: .leading, spacing: 3) {
                                Text("2件を選んでSAT比較")
                                Text("保存済み\(notes.count)件")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        } icon: {
                            Image(systemName: "rectangle.split.2x1")
                        }
                    }
                    .disabled(notes.count < 2)
                    .accessibilityIdentifier("tasting.compare.entry")
                } header: {
                    Text("過去記録の比較")
                } footer: {
                    Text(
                        notes.count < 2
                            ? "比較にはテイスティング記録が2件以上必要です。"
                            : "2件の外観、香り、味わい、結論を横並びで確認できます。"
                    )
                }

                Section("記録") {
                    if notes.isEmpty {
                        ContentUnavailableView(
                            "テイスティング記録はまだありません",
                            systemImage: "wineglass",
                            description: Text("WSET Level 3 SATの構成で最初のワインを記録しましょう。")
                        )
                    } else {
                        ForEach(notes) { note in
                            NavigationLink {
                                TastingNoteDetailView(note: note)
                            } label: {
                                TastingNoteRow(note: note)
                            }
                        }
                        .onDelete(perform: deleteNotes)
                    }
                }
            }
            .navigationTitle("テイスティング")
            .onAppear {
                seedTastingNotesForUITestIfNeeded()
                activeExam = TastingExamDraftStore.shared.load()
            }
        }
    }

    private func deleteNotes(at offsets: IndexSet) {
        for offset in offsets {
            modelContext.delete(notes[offset])
        }
        try? modelContext.save()
    }

    private func seedTastingNotesForUITestIfNeeded() {
#if DEBUG
        guard !didSeedUITestNotes,
              ProcessInfo.processInfo.arguments.contains("-UITestSeedTastingComparison")
        else { return }
        didSeedUITestNotes = true
        guard notes.count < 2 else { return }

        var first = TastingDraft()
        first.wineName = "比較用ワインA"
        first.appearanceColour = "ルビー"
        first.aromaNotes = "赤系果実"
        var second = TastingDraft()
        second.wineName = "比較用ワインB"
        second.appearanceColour = "レモン"
        second.aromaNotes = "柑橘"
        modelContext.insert(TastingNote(draft: first))
        modelContext.insert(TastingNote(draft: second))
        try? modelContext.save()
#endif
    }
}

private struct TastingNoteRow: View {
    let note: TastingNote

    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            Text(note.wineName.isEmpty ? SATDisplayText.japanese(note.sampleLabel) : note.wineName)
                .font(.headline)
            HStack(spacing: 8) {
                Text(note.tastedAt, format: .dateTime.year().month().day())
                Text(SATDisplayText.japanese(note.quality))
                if note.sessionID != nil {
                    Label(SATDisplayText.japanese(note.sampleLabel), systemImage: "rectangle.2.swap")
                }
                if note.examStartedAt != nil {
                    Label(
                        note.examWasTimeExpired == true ? "時間切れ" : "30分試験",
                        systemImage: "timer"
                    )
                }
            }
            .font(.caption)
            .foregroundStyle(.secondary)
        }
        .padding(.vertical, 3)
    }
}

private struct TastingComparisonSelectionView: View {
    let notes: [TastingNote]
    @State private var selectedIDs: [UUID] = []

    private var selectedNotes: [TastingNote] {
        selectedIDs.compactMap { id in notes.first { $0.id == id } }
    }

    var body: some View {
        List {
            Section {
                Text("比較したい記録を2件選択してください（\(selectedIDs.count) / 2件）。")
                    .foregroundStyle(.secondary)
            }

            Section("テイスティング記録") {
                ForEach(notes) { note in
                    Button {
                        toggle(note.id)
                    } label: {
                        HStack(spacing: 12) {
                            Image(systemName: selectedIDs.contains(note.id) ? "checkmark.circle.fill" : "circle")
                                .foregroundStyle(
                                    selectedIDs.contains(note.id) ? AppTheme.wine : Color.secondary
                                )
                            TastingNoteRow(note: note)
                            Spacer()
                        }
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    .accessibilityIdentifier("tasting.compare.note.\(note.id.uuidString)")
                }
            }

            if selectedNotes.count == 2 {
                Section {
                    NavigationLink {
                        TastingSATComparisonView(
                            first: selectedNotes[0],
                            second: selectedNotes[1]
                        )
                    } label: {
                        Label("SAT比較を表示", systemImage: "rectangle.split.2x1.fill")
                    }
                    .accessibilityIdentifier("tasting.compare.start")
                }
            }
        }
        .navigationTitle("比較する記録を選択")
        .navigationBarTitleDisplayMode(.inline)
        .accessibilityIdentifier("tasting.compare.selection")
    }

    private func toggle(_ id: UUID) {
        if let index = selectedIDs.firstIndex(of: id) {
            selectedIDs.remove(at: index)
        } else if selectedIDs.count < 2 {
            selectedIDs.append(id)
        }
    }
}

private struct TastingSATComparisonView: View {
    let first: TastingNote
    let second: TastingNote

    private var sections: [TastingComparisonSection] {
        TastingComparisonService.sections(first: first, second: second)
    }

    var body: some View {
        List {
            Section {
                HStack(alignment: .top, spacing: 12) {
                    comparisonHeading(TastingComparisonService.displayName(for: first))
                    comparisonHeading(TastingComparisonService.displayName(for: second))
                }
            } footer: {
                Text("保存済みのSAT主要項目を比較しています。記録の値は変更されません。")
            }

            ForEach(sections.filter { $0.id != "wine" }) { section in
                Section(section.title) {
                    ForEach(section.fields) { field in
                        VStack(alignment: .leading, spacing: 8) {
                            Text(field.label)
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(.secondary)
                            HStack(alignment: .top, spacing: 12) {
                                comparisonValue(field.firstValue)
                                comparisonValue(field.secondValue)
                            }
                        }
                        .padding(.vertical, 3)
                    }
                }
            }
        }
        .navigationTitle("SAT記録比較")
        .navigationBarTitleDisplayMode(.inline)
        .accessibilityIdentifier("tasting.compare.screen")
    }

    private func comparisonHeading(_ value: String) -> some View {
        Text(value)
            .font(.headline)
            .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func comparisonValue(_ value: String) -> some View {
        Text(value)
            .font(.subheadline)
            .frame(maxWidth: .infinity, alignment: .leading)
    }
}

private struct TastingEditorView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var modelContext
    let note: TastingNote?
    @State private var draft: TastingDraft

    @MainActor
    init(note: TastingNote? = nil) {
        self.note = note
        _draft = State(initialValue: note.map(TastingDraft.init(note:)) ?? TastingDraft())
    }

    var body: some View {
        Form {
            TastingFormSections(draft: $draft)

            Section {
                Button(note == nil ? "テイスティング記録を保存" : "変更を保存") {
                    if let note {
                        note.update(from: draft)
                    } else {
                        modelContext.insert(TastingNote(draft: draft))
                    }
                    try? modelContext.save()
                    dismiss()
                }
                .frame(maxWidth: .infinity)
                .disabled(!draft.isMeaningful)
            } footer: {
                Text("保存する前に、色、香り、風味、結論のいずれかを入力してください。")
            }
        }
        .navigationTitle(note == nil ? "新規テイスティング" : "テイスティングを編集")
        .navigationBarTitleDisplayMode(.inline)
    }
}

private struct TwoWineTastingView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var modelContext
    @State private var selectedSample = 0
    @State private var wineOne = TastingDraft()
    @State private var wineTwo = TastingDraft()

    var body: some View {
        Form {
            Section {
                Picker("サンプル", selection: $selectedSample) {
                    Text("ワイン1").tag(0)
                    Text("ワイン2").tag(1)
                }
                .pickerStyle(.segmented)
            } footer: {
                Text("正体を確認する前に、2本をそれぞれ独立して評価してください。")
            }

            if selectedSample == 0 {
                TastingFormSections(draft: $wineOne)
            } else {
                TastingFormSections(draft: $wineTwo)
            }

            Section {
                Button("2本の記録を保存") {
                    let sessionID = UUID()
                    modelContext.insert(
                        TastingNote(draft: wineOne, sessionID: sessionID, sampleLabel: "Wine 1")
                    )
                    modelContext.insert(
                        TastingNote(draft: wineTwo, sessionID: sessionID, sampleLabel: "Wine 2")
                    )
                    try? modelContext.save()
                    dismiss()
                }
                .frame(maxWidth: .infinity)
                .disabled(!wineOne.isMeaningful || !wineTwo.isMeaningful)
            } footer: {
                Text("保存する前に、2本それぞれの色、香り、風味、結論のいずれかを入力してください。")
            }
        }
        .navigationTitle("2本比較ブラインド練習")
        .navigationBarTitleDisplayMode(.inline)
    }
}

private struct TastingExamView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var modelContext
    @Environment(\.scenePhase) private var scenePhase

    @State private var snapshot: TastingExamSnapshot
    @State private var selectedSample = 0
    @State private var isSubmitted = false
    @State private var showingAbandonConfirmation = false
    @State private var saveError: String?

    private let store: TastingExamDraftStore

    init(
        store: TastingExamDraftStore = .shared,
        now: Date = .now
    ) {
        self.store = store
        _snapshot = State(initialValue: store.load() ?? TastingExamSnapshot(startedAt: now))
    }

    var body: some View {
        Group {
            if isSubmitted {
                completionView
            } else {
                TimelineView(.periodic(from: .now, by: 1)) { context in
                    examForm(at: context.date)
                }
            }
        }
        .navigationTitle("30分テイスティング試験")
        .navigationBarTitleDisplayMode(.inline)
        .accessibilityIdentifier("tasting.exam.screen")
        .toolbar {
            if !isSubmitted {
                ToolbarItem(placement: .topBarTrailing) {
                    Button(role: .destructive) {
                        showingAbandonConfirmation = true
                    } label: {
                        Image(systemName: "xmark.circle")
                    }
                    .accessibilityLabel("試験を破棄")
                }
            }
        }
        .confirmationDialog(
            "試験を破棄しますか？",
            isPresented: $showingAbandonConfirmation,
            titleVisibility: .visible
        ) {
            Button("下書きを破棄", role: .destructive) {
                store.clear()
                dismiss()
            }
            Button("キャンセル", role: .cancel) {}
        } message: {
            Text("2本の入力内容と残り時間は復元できなくなります。")
        }
        .alert(
            "テイスティング記録を保存できませんでした",
            isPresented: Binding(
                get: { saveError != nil },
                set: { if !$0 { saveError = nil } }
            )
        ) {
            Button("閉じる", role: .cancel) {}
        } message: {
            Text(saveError ?? "もう一度お試しください。")
        }
        .onAppear {
            store.save(snapshot)
        }
        .onChange(of: snapshot) { _, updated in
            guard !isSubmitted else { return }
            store.save(updated)
        }
        .onChange(of: scenePhase) { _, phase in
            if phase != .active && !isSubmitted {
                store.save(snapshot)
            }
        }
        .onDisappear {
            if !isSubmitted { store.save(snapshot) }
        }
    }

    private func examForm(at date: Date) -> some View {
        let remaining = snapshot.remainingSeconds(at: date)
        let expired = remaining == 0

        return Form {
            Section {
                HStack {
                    Label("残り時間", systemImage: "timer")
                    Spacer()
                    Text(TastingExamClock.displayText(seconds: remaining))
                        .font(.title2.monospacedDigit().bold())
                        .foregroundStyle(timerColour(remainingSeconds: remaining))
                        .accessibilityIdentifier("tasting.exam.timer")
                }

                wineProgressRow(
                    label: "ワイン1",
                    state: snapshot.wineOne
                )
                wineProgressRow(
                    label: "ワイン2",
                    state: snapshot.wineTwo
                )
            } footer: {
                Text("中断しても開始時刻から残り時間を再計算します。")
            }

            if expired {
                Section {
                    Label("時間切れです。入力をロックしました。", systemImage: "exclamationmark.triangle.fill")
                        .foregroundStyle(AppTheme.error)
                }
            } else if remaining <= 5 * 60 {
                Section {
                    Label("残り5分以内です。結論と未入力項目を確認してください。", systemImage: "exclamationmark.triangle")
                        .foregroundStyle(remaining <= 60 ? .red : .orange)
                }
            }

            Section {
                Picker("サンプル", selection: $selectedSample) {
                    Text("ワイン1").tag(0)
                    Text("ワイン2").tag(1)
                }
                .pickerStyle(.segmented)
                .accessibilityIdentifier("tasting.exam.sample")
            } footer: {
                Text("2本を切り替えながら、それぞれ独立して評価します。")
            }

            if selectedSample == 0 {
                TastingFormSections(draft: $snapshot.wineOne.draft) { field in
                    snapshot.wineOne.recordEdit(field)
                }
                .disabled(expired)
            } else {
                TastingFormSections(draft: $snapshot.wineTwo.draft) { field in
                    snapshot.wineTwo.recordEdit(field)
                }
                .disabled(expired)
            }

            Section {
                Button(expired ? "時間切れの記録を提出" : "2本を提出して保存") {
                    submit(at: date, wasExpired: expired)
                }
                .frame(maxWidth: .infinity)
                .disabled(!snapshot.wineOne.hasInput && !snapshot.wineTwo.hasInput)
                .accessibilityIdentifier("tasting.exam.submit")
            } footer: {
                Text("提出すると2本を同じ試験セッションとして記録帳へ保存します。")
            }
        }
    }

    private var completionView: some View {
        List {
            Section {
                Label("テイスティング試験を保存しました", systemImage: "checkmark.seal.fill")
                    .font(.headline)
                    .foregroundStyle(AppTheme.success)
                LabeledContent(
                    "ワイン1の入力進捗",
                    value: percentText(snapshot.wineOne.completionPercent)
                )
                LabeledContent(
                    "ワイン2の入力進捗",
                    value: percentText(snapshot.wineTwo.completionPercent)
                )
            }

            Section {
                Picker("確認するサンプル", selection: $selectedSample) {
                    Text("ワイン1").tag(0)
                    Text("ワイン2").tag(1)
                }
                .pickerStyle(.segmented)

                let draft = selectedSample == 0
                    ? snapshot.wineOne.draft
                    : snapshot.wineTwo.draft
                ForEach(TastingField.allCases, id: \.self) { field in
                    LabeledContent(field.displayLabel) {
                        Text(submittedDisplayValue(for: field, in: draft))
                            .multilineTextAlignment(.trailing)
                            .foregroundStyle(.secondary)
                    }
                }
            } header: {
                Text("提出後の全項目")
            } footer: {
                Text("提出前の入力内容を読み取り専用で表示しています。")
            }

            Section {
                Button("記録帳へ戻る") { dismiss() }
                    .frame(maxWidth: .infinity)
            }
        }
        .accessibilityIdentifier("tasting.exam.submitted.summary")
    }

    private func wineProgressRow(
        label: String,
        state: TastingExamWineState
    ) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(label)
                Spacer()
                Text("\(state.completedFieldCount) / \(state.totalFieldCount)項目")
                    .font(.caption.monospacedDigit())
                    .foregroundStyle(.secondary)
            }
            ProgressView(value: state.completionPercent)
                .tint(AppTheme.wine)
        }
        .accessibilityElement(children: .combine)
        .accessibilityIdentifier(
            label == "ワイン1" ? "tasting.exam.progress.wine1" : "tasting.exam.progress.wine2"
        )
    }

    private func timerColour(remainingSeconds: Int) -> Color {
        if remainingSeconds <= 60 { return AppTheme.error }
        if remainingSeconds <= 5 * 60 { return AppTheme.warning }
        return .primary
    }

    private func submit(at date: Date, wasExpired: Bool) {
        let first = makeNote(
            draft: snapshot.wineOne.draft,
            sampleLabel: "Wine 1",
            completionPercent: snapshot.wineOne.completionPercent,
            submittedAt: date,
            wasExpired: wasExpired
        )
        let second = makeNote(
            draft: snapshot.wineTwo.draft,
            sampleLabel: "Wine 2",
            completionPercent: snapshot.wineTwo.completionPercent,
            submittedAt: date,
            wasExpired: wasExpired
        )
        first.tastedAt = date
        second.tastedAt = date
        modelContext.insert(first)
        modelContext.insert(second)

        do {
            try modelContext.save()
            store.clear()
            isSubmitted = true
        } catch {
            modelContext.delete(first)
            modelContext.delete(second)
            saveError = "入力内容は端末内の下書きに保持されています。"
        }
    }

    private func makeNote(
        draft: TastingDraft,
        sampleLabel: String,
        completionPercent: Double,
        submittedAt: Date,
        wasExpired: Bool
    ) -> TastingNote {
        TastingNote(
            draft: draft,
            sessionID: snapshot.sessionID,
            sampleLabel: sampleLabel,
            examStartedAt: snapshot.startedAt,
            examSubmittedAt: submittedAt,
            examDurationSeconds: snapshot.durationSeconds,
            examWasTimeExpired: wasExpired,
            examCompletionPercent: completionPercent
        )
    }

    private func percentText(_ value: Double) -> String {
        value.formatted(.percent.precision(.fractionLength(0)))
    }

    private func submittedDisplayValue(
        for field: TastingField,
        in draft: TastingDraft
    ) -> String {
        let rawValue = draft.value(for: field)
            .trimmingCharacters(in: .whitespacesAndNewlines)
        guard !rawValue.isEmpty else { return "未入力" }
        return field.requiresText ? rawValue : SATDisplayText.japanese(rawValue)
    }
}

private struct TastingFormSections: View {
    @Binding var draft: TastingDraft
    var onFieldEdited: (TastingField) -> Void = { _ in }
    @State private var isAromaVocabularyPresented = false
    @State private var isFlavourVocabularyPresented = false

    private let appearanceIntensity = ["Pale", "Medium", "Deep"]
    private let intensity = ["Light", "Medium(-)", "Medium", "Medium(+)", "Pronounced"]
    private let structure = ["Low", "Medium(-)", "Medium", "Medium(+)", "High"]

    var body: some View {
        Group {
            Section("ワイン") {
                TextField("ワイン名・正体（任意）", text: $draft.wineName)
            }

            Section("外観") {
                CompactPicker("清澄度", selection: $draft.appearanceClarity, options: ["Clear", "Hazy"])
                CompactPicker("濃淡", selection: $draft.appearanceIntensity, options: appearanceIntensity)
                TextField("色", text: $draft.appearanceColour)
            }

            Section("香り") {
                CompactPicker("状態", selection: $draft.noseCondition, options: ["Clean", "Unclean"])
                CompactPicker("強さ", selection: $draft.noseIntensity, options: intensity)
                CompactPicker(
                    "熟成度",
                    selection: $draft.noseDevelopment,
                    options: ["Youthful", "Developing", "Fully developed", "Tired / past its best"]
                )
                TextField("香りの特徴", text: $draft.aromaNotes, axis: .vertical)
                    .lineLimit(3...7)
                Button {
                    isAromaVocabularyPresented = true
                } label: {
                    Label("香りの語彙候補から追加", systemImage: "text.badge.plus")
                }
                .accessibilityIdentifier("tasting.vocabulary.aroma")
                .sheet(isPresented: $isAromaVocabularyPresented) {
                    NavigationStack {
                        TastingVocabularyPicker(target: .aroma) { value in
                            appendVocabulary(value, to: .aroma)
                        }
                    }
                }
            }

            Section("味わい") {
                CompactPicker(
                    "甘辛度",
                    selection: $draft.sweetness,
                    options: ["Dry", "Off-dry", "Medium-dry", "Medium-sweet", "Sweet", "Luscious"]
                )
                CompactPicker("酸味", selection: $draft.acidity, options: structure)
                CompactPicker("タンニン", selection: $draft.tannin, options: structure)
                CompactPicker("アルコール", selection: $draft.alcohol, options: structure)
                CompactPicker(
                    "ボディ",
                    selection: $draft.body,
                    options: ["Light", "Medium(-)", "Medium", "Medium(+)", "Full"]
                )
                CompactPicker("風味の強さ", selection: $draft.flavourIntensity, options: intensity)
                CompactPicker(
                    "余韻",
                    selection: $draft.finish,
                    options: ["Short", "Medium(-)", "Medium", "Medium(+)", "Long"]
                )
                TextField("風味の特徴", text: $draft.flavourNotes, axis: .vertical)
                    .lineLimit(3...7)
                Button {
                    isFlavourVocabularyPresented = true
                } label: {
                    Label("風味の語彙候補から追加", systemImage: "text.badge.plus")
                }
                .accessibilityIdentifier("tasting.vocabulary.flavour")
                .sheet(isPresented: $isFlavourVocabularyPresented) {
                    NavigationStack {
                        TastingVocabularyPicker(target: .flavour) { value in
                            appendVocabulary(value, to: .flavour)
                        }
                    }
                }
            }

            Section("結論") {
                CompactPicker(
                    "品質",
                    selection: $draft.quality,
                    options: ["Faulty", "Poor", "Acceptable", "Good", "Very good", "Outstanding"]
                )
                CompactPicker(
                    "飲み頃",
                    selection: $draft.readiness,
                    options: [
                        "Too young",
                        "Can drink now, suitable for ageing",
                        "Can drink now, not suitable for ageing",
                        "Too old"
                    ]
                )
                TextField("結論の根拠", text: $draft.conclusion, axis: .vertical)
                    .lineLimit(3...7)
            }
        }
        .onChange(of: draft) { previous, updated in
            for field in updated.changedFields(comparedTo: previous) {
                onFieldEdited(field)
            }
        }
    }

    private func appendVocabulary(_ value: String, to target: TastingVocabularyTarget) {
        let existing = target == .aroma ? draft.aromaNotes : draft.flavourNotes
        let components = existing
            .split(separator: "、")
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
        guard !components.contains(value) else { return }
        let updated = existing.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            ? value
            : existing + "、" + value
        if target == .aroma {
            draft.aromaNotes = updated
        } else {
            draft.flavourNotes = updated
        }
    }
}

private enum TastingVocabularyTarget: String, Identifiable {
    case aroma
    case flavour

    var id: String { rawValue }

    var title: String {
        switch self {
        case .aroma: "香りの語彙"
        case .flavour: "風味の語彙"
        }
    }
}

private enum TastingVocabularySource: String, CaseIterable, Identifiable {
    case fixed
    case reference

    var id: String { rawValue }

    var label: String {
        switch self {
        case .fixed: "テイスティング語彙"
        case .reference: "用語辞書"
        }
    }
}

private struct TastingVocabularyPicker: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(EntitlementStore.self) private var entitlementStore
    @Query(sort: \TastingNote.tastedAt, order: .reverse) private var tastingNotes: [TastingNote]
    let target: TastingVocabularyTarget
    let onSelect: (String) -> Void

    @State private var source = TastingVocabularySource.fixed
    @State private var searchText = ""
    @State private var lastAdded: String?

    private let referenceStore = ReferenceStore.shared
    private let suggestedReferenceCategories = Set([
        "品種", "醸造・製法", "熟成", "栽培", "自然要因", "発泡性ワイン",
        "甘口ワイン", "酒精強化ワイン"
    ])

    private var fixedGroups: [TastingVocabularyGroup] {
        TastingVocabularyCatalog.groups(matching: searchText)
    }

    private var frequentlyUsedValues: [String] {
        let entries = tastingNotes.map {
            target == .aroma ? $0.aromaNotes : $0.flavourNotes
        }
        return TastingVocabularyCatalog.frequentlyUsedValues(
            in: entries,
            matching: searchText
        )
    }

    private var referenceTerms: [ReferenceTerm] {
        referenceStore.terms
            .filter { term in
                let isSuggested = suggestedReferenceCategories.contains(term.category)
                return entitlementStore.policy.canAccessGlossaryTerm(id: term.id)
                    && (searchText.isEmpty ? isSuggested : term.matches(searchText))
            }
            .sorted {
                if $0.category != $1.category { return $0.category < $1.category }
                return $0.nameJapanese.localizedStandardCompare($1.nameJapanese) == .orderedAscending
            }
    }

    var body: some View {
        List {
            Section {
                Picker("語彙の出典", selection: $source) {
                    ForEach(TastingVocabularySource.allCases) { item in
                        Text(item.label).tag(item)
                    }
                }
                .pickerStyle(.segmented)
            }

            if source == .fixed {
                if !frequentlyUsedValues.isEmpty {
                    Section("よく使う語彙") {
                        ForEach(frequentlyUsedValues, id: \.self) { value in
                            candidateButton(value)
                        }
                    }
                }
                ForEach(fixedGroups) { group in
                    Section(group.name) {
                        ForEach(group.values, id: \.self) { value in
                            candidateButton(value)
                        }
                    }
                }
            } else {
                Section {
                    ForEach(referenceTerms) { term in
                        HStack(spacing: 10) {
                            Button {
                                add(term.nameJapanese)
                            } label: {
                                VStack(alignment: .leading, spacing: 3) {
                                    Text(term.nameJapanese)
                                    Text(term.category)
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                                .frame(maxWidth: .infinity, alignment: .leading)
                            }
                            .buttonStyle(.plain)

                            NavigationLink {
                                GlossaryTermDetailView(term: term)
                            } label: {
                                Image(systemName: "info.circle")
                            }
                            .accessibilityLabel("\(term.nameJapanese)の用語詳細")
                        }
                    }
                } footer: {
                    Text("品種・醸造・熟成など、現在利用できる用語から検索できます。")
                }
            }
        }
        .searchable(text: $searchText, prompt: "語彙を検索")
        .navigationTitle(target.title)
        .navigationBarTitleDisplayMode(.inline)
        .accessibilityIdentifier("tasting.vocabulary.picker")
        .toolbar {
            ToolbarItem(placement: .confirmationAction) {
                Button("完了") { dismiss() }
            }
        }
        .overlay(alignment: .bottom) {
            if let lastAdded {
                Text("「\(lastAdded)」を追加しました")
                    .font(.caption.weight(.semibold))
                    .padding(.horizontal, 14)
                    .padding(.vertical, 8)
                    .background(.ultraThinMaterial, in: Capsule())
                    .padding(.bottom, 10)
            }
        }
    }

    private func candidateButton(_ value: String) -> some View {
        Button {
            add(value)
        } label: {
            HStack {
                Text(value)
                Spacer()
                Image(systemName: "plus.circle")
                    .foregroundStyle(AppTheme.wine)
            }
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier("tasting.vocabulary.candidate.\(value)")
    }

    private func add(_ value: String) {
        onSelect(value)
        lastAdded = value
    }
}

private struct CompactPicker: View {
    let title: String
    @Binding var selection: String
    let options: [String]

    init(_ title: String, selection: Binding<String>, options: [String]) {
        self.title = title
        _selection = selection
        self.options = options
    }

    var body: some View {
        Picker(selection: $selection) {
            ForEach(options, id: \.self) { option in
                Text(SATDisplayText.japanese(option)).tag(option)
            }
        } label: {
            Text(LocalizedStringKey(title))
        }
    }
}

private struct TastingNoteDetailView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var modelContext
    let note: TastingNote
    @State private var showingDeleteConfirmation = false
    @State private var showingExportFormat = false
    @State private var showingExporter = false
    @State private var exportDocument: TastingExportDocument?
    @State private var exportFormat = TastingExportFormat.json
    @State private var exportError: String?

    var body: some View {
        List {
            Section("ワイン") {
                DetailRow(label: "サンプル", value: note.sampleLabel, translatesSATValue: true)
                DetailRow(label: "ワイン名・正体", value: note.wineName, hideWhenEmpty: true)
                DetailRow(
                    label: "記録日時",
                    value: note.tastedAt.formatted(
                        Date.FormatStyle(
                            date: .long,
                            time: .shortened,
                            locale: AppLanguage.locale
                        )
                    )
                )
            }

            if note.examStartedAt != nil {
                Section("30分試験") {
                    if let duration = note.examDurationSeconds {
                        LabeledContent(
                            "制限時間",
                            value: TastingExamClock.displayText(seconds: duration)
                        )
                    }
                    if let completion = note.examCompletionPercent {
                        LabeledContent(
                            "入力進捗",
                            value: completion.formatted(
                                .percent.precision(.fractionLength(0))
                            )
                        )
                    }
                    LabeledContent(
                        "提出状態",
                        value: note.examWasTimeExpired == true ? "時間切れ後に提出" : "制限時間内に提出"
                    )
                }
            }

            Section("外観") {
                DetailRow(label: "清澄度", value: note.appearanceClarity, translatesSATValue: true)
                DetailRow(label: "濃淡", value: note.appearanceIntensity, translatesSATValue: true)
                DetailRow(label: "色", value: note.appearanceColour, hideWhenEmpty: true)
            }

            Section("香り") {
                DetailRow(label: "状態", value: note.noseCondition, translatesSATValue: true)
                DetailRow(label: "強さ", value: note.noseIntensity, translatesSATValue: true)
                DetailRow(label: "熟成度", value: note.noseDevelopment, translatesSATValue: true)
                DetailRow(label: "香りの特徴", value: note.aromaNotes, hideWhenEmpty: true)
            }

            Section("味わい") {
                DetailRow(label: "甘辛度", value: note.sweetness, translatesSATValue: true)
                DetailRow(label: "酸味", value: note.acidity, translatesSATValue: true)
                DetailRow(label: "タンニン", value: note.tannin, translatesSATValue: true)
                DetailRow(label: "アルコール", value: note.alcohol, translatesSATValue: true)
                DetailRow(label: "ボディ", value: note.body, translatesSATValue: true)
                DetailRow(label: "風味の強さ", value: note.flavourIntensity, translatesSATValue: true)
                DetailRow(label: "余韻", value: note.finish, translatesSATValue: true)
                DetailRow(label: "風味の特徴", value: note.flavourNotes, hideWhenEmpty: true)
            }

            Section("結論") {
                DetailRow(label: "品質", value: note.quality, translatesSATValue: true)
                DetailRow(label: "飲み頃", value: note.readiness, translatesSATValue: true)
                DetailRow(label: "根拠", value: note.conclusion, hideWhenEmpty: true)
            }
        }
        .navigationTitle(
            note.wineName.isEmpty ? SATDisplayText.japanese(note.sampleLabel) : note.wineName
        )
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItemGroup(placement: .topBarTrailing) {
                Button {
                    showingExportFormat = true
                } label: {
                    Image(systemName: "square.and.arrow.up")
                }
                .accessibilityLabel("テイスティング記録を書き出す")
                NavigationLink {
                    TastingEditorView(note: note)
                } label: {
                    Text("編集")
                }
                Button(role: .destructive) {
                    showingDeleteConfirmation = true
                } label: {
                    Image(systemName: "trash")
                }
                .accessibilityLabel("テイスティング記録を削除")
            }
        }
        .alert("テイスティング記録を削除しますか？", isPresented: $showingDeleteConfirmation) {
            Button("キャンセル", role: .cancel) {}
            Button("削除", role: .destructive) {
                modelContext.delete(note)
                try? modelContext.save()
                dismiss()
            }
        } message: {
            Text("この端末から記録を削除します。後で必要になる場合は、先に書き出してください。")
        }
        .confirmationDialog(
            "書き出し形式を選択",
            isPresented: $showingExportFormat,
            titleVisibility: .visible
        ) {
            ForEach(TastingExportFormat.allCases) { format in
                Button(format.label) { prepareExport(format: format) }
            }
            Button("キャンセル", role: .cancel) {}
        } message: {
            Text("このテイスティング記録だけを書き出します。")
        }
        .fileExporter(
            isPresented: $showingExporter,
            document: exportDocument,
            contentType: exportFormat.contentType,
            defaultFilename: exportFilename
        ) { result in
            if case let .failure(error) = result {
                exportError = error.localizedDescription
            }
            exportDocument = nil
        }
        .alert(
            "書き出しに失敗しました",
            isPresented: Binding(
                get: { exportError != nil },
                set: { if !$0 { exportError = nil } }
            )
        ) {
            Button("閉じる", role: .cancel) {}
        } message: {
            Text(exportError ?? "もう一度お試しください。")
        }
    }

    private var exportFilename: String {
        TastingExportService.safeFilename(for: TastingNoteExportSnapshot(note: note))
    }

    private func prepareExport(format: TastingExportFormat) {
        do {
            let snapshot = TastingNoteExportSnapshot(note: note)
            exportFormat = format
            exportDocument = TastingExportDocument(
                data: try TastingExportService.data(for: snapshot, format: format)
            )
            showingExporter = true
        } catch {
            exportError = error.localizedDescription
        }
    }
}

private struct DetailRow: View {
    let label: String
    let value: String
    var hideWhenEmpty = false
    var translatesSATValue = false

    var body: some View {
        if !hideWhenEmpty || !value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            LabeledContent {
                Text(translatesSATValue ? SATDisplayText.japanese(value) : value)
                    .multilineTextAlignment(.trailing)
                    .foregroundStyle(.secondary)
            } label: {
                Text(LocalizedStringKey(label))
            }
        }
    }
}
