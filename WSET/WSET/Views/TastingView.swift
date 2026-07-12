import SwiftData
import SwiftUI

struct TastingView: View {
    @Environment(\.modelContext) private var modelContext
    @Query(sort: \TastingNote.tastedAt, order: .reverse) private var notes: [TastingNote]

    var body: some View {
        NavigationStack {
            List {
                Section("Practice") {
                    NavigationLink {
                        TastingEditorView()
                    } label: {
                        Label("New tasting note", systemImage: "square.and.pencil")
                    }

                    NavigationLink {
                        TwoWineTastingView()
                    } label: {
                        Label("Two-wine blind practice", systemImage: "wineglass.fill")
                    }
                }

                Section("Journal") {
                    if notes.isEmpty {
                        ContentUnavailableView(
                            "No tasting notes yet",
                            systemImage: "wineglass",
                            description: Text("Use the WSET Level 3 SAT structure to record your first wine.")
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
            .navigationTitle("Tasting")
        }
    }

    private func deleteNotes(at offsets: IndexSet) {
        for offset in offsets {
            modelContext.delete(notes[offset])
        }
        try? modelContext.save()
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
            }
            .font(.caption)
            .foregroundStyle(.secondary)
        }
        .padding(.vertical, 3)
    }
}

private struct TastingEditorView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var modelContext
    let note: TastingNote?
    @State private var draft: TastingDraft

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
                Text("Add a colour, aroma, flavour, or conclusion before saving.")
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
                Picker("Sample", selection: $selectedSample) {
                    Text("ワイン1").tag(0)
                    Text("ワイン2").tag(1)
                }
                .pickerStyle(.segmented)
            } footer: {
                Text("Assess both wines independently before revealing their identities.")
            }

            if selectedSample == 0 {
                TastingFormSections(draft: $wineOne)
            } else {
                TastingFormSections(draft: $wineTwo)
            }

            Section {
                Button("Save both wines") {
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
                Text("Complete a meaningful note for each wine before saving the pair.")
            }
        }
        .navigationTitle("Two-wine practice")
        .navigationBarTitleDisplayMode(.inline)
    }
}

private struct TastingFormSections: View {
    @Binding var draft: TastingDraft

    private let appearanceIntensity = ["Pale", "Medium", "Deep"]
    private let intensity = ["Light", "Medium(-)", "Medium", "Medium(+)", "Pronounced"]
    private let structure = ["Low", "Medium(-)", "Medium", "Medium(+)", "High"]

    var body: some View {
        Section("Wine") {
            TextField("Wine name / identity (optional)", text: $draft.wineName)
        }

        Section("Appearance") {
            CompactPicker("Clarity", selection: $draft.appearanceClarity, options: ["Clear", "Hazy"])
            CompactPicker("Intensity", selection: $draft.appearanceIntensity, options: appearanceIntensity)
            TextField("Colour", text: $draft.appearanceColour)
        }

        Section("Nose") {
            CompactPicker("Condition", selection: $draft.noseCondition, options: ["Clean", "Unclean"])
            CompactPicker("Intensity", selection: $draft.noseIntensity, options: intensity)
            CompactPicker(
                "Development",
                selection: $draft.noseDevelopment,
                options: ["Youthful", "Developing", "Fully developed", "Tired / past its best"]
            )
            TextField("Aroma characteristics", text: $draft.aromaNotes, axis: .vertical)
                .lineLimit(3...7)
        }

        Section("Palate") {
            CompactPicker(
                "Sweetness",
                selection: $draft.sweetness,
                options: ["Dry", "Off-dry", "Medium-dry", "Medium-sweet", "Sweet", "Luscious"]
            )
            CompactPicker("Acidity", selection: $draft.acidity, options: structure)
            CompactPicker("Tannin", selection: $draft.tannin, options: structure)
            CompactPicker("Alcohol", selection: $draft.alcohol, options: structure)
            CompactPicker(
                "Body",
                selection: $draft.body,
                options: ["Light", "Medium(-)", "Medium", "Medium(+)", "Full"]
            )
            CompactPicker("Flavour intensity", selection: $draft.flavourIntensity, options: intensity)
            CompactPicker(
                "Finish",
                selection: $draft.finish,
                options: ["Short", "Medium(-)", "Medium", "Medium(+)", "Long"]
            )
            TextField("Flavour characteristics", text: $draft.flavourNotes, axis: .vertical)
                .lineLimit(3...7)
        }

        Section("Conclusions") {
            CompactPicker(
                "Quality",
                selection: $draft.quality,
                options: ["Faulty", "Poor", "Acceptable", "Good", "Very good", "Outstanding"]
            )
            CompactPicker(
                "Readiness",
                selection: $draft.readiness,
                options: [
                    "Too young",
                    "Can drink now, suitable for ageing",
                    "Can drink now, not suitable for ageing",
                    "Too old"
                ]
            )
            TextField("Supporting conclusion", text: $draft.conclusion, axis: .vertical)
                .lineLimit(3...7)
        }
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

    var body: some View {
        List {
            Section("Wine") {
                DetailRow(label: "Sample", value: note.sampleLabel, translatesSATValue: true)
                DetailRow(label: "Identity", value: note.wineName, hideWhenEmpty: true)
                DetailRow(
                    label: "Date",
                    value: note.tastedAt.formatted(
                        Date.FormatStyle(
                            date: .long,
                            time: .shortened,
                            locale: AppLanguage.locale
                        )
                    )
                )
            }

            Section("Appearance") {
                DetailRow(label: "Clarity", value: note.appearanceClarity, translatesSATValue: true)
                DetailRow(label: "Intensity", value: note.appearanceIntensity, translatesSATValue: true)
                DetailRow(label: "Colour", value: note.appearanceColour, hideWhenEmpty: true)
            }

            Section("Nose") {
                DetailRow(label: "Condition", value: note.noseCondition, translatesSATValue: true)
                DetailRow(label: "Intensity", value: note.noseIntensity, translatesSATValue: true)
                DetailRow(label: "Development", value: note.noseDevelopment, translatesSATValue: true)
                DetailRow(label: "Aromas", value: note.aromaNotes, hideWhenEmpty: true)
            }

            Section("Palate") {
                DetailRow(label: "Sweetness", value: note.sweetness, translatesSATValue: true)
                DetailRow(label: "Acidity", value: note.acidity, translatesSATValue: true)
                DetailRow(label: "Tannin", value: note.tannin, translatesSATValue: true)
                DetailRow(label: "Alcohol", value: note.alcohol, translatesSATValue: true)
                DetailRow(label: "Body", value: note.body, translatesSATValue: true)
                DetailRow(label: "Flavour intensity", value: note.flavourIntensity, translatesSATValue: true)
                DetailRow(label: "Finish", value: note.finish, translatesSATValue: true)
                DetailRow(label: "Flavours", value: note.flavourNotes, hideWhenEmpty: true)
            }

            Section("Conclusions") {
                DetailRow(label: "Quality", value: note.quality, translatesSATValue: true)
                DetailRow(label: "Readiness", value: note.readiness, translatesSATValue: true)
                DetailRow(label: "Support", value: note.conclusion, hideWhenEmpty: true)
            }
        }
        .navigationTitle(
            note.wineName.isEmpty ? SATDisplayText.japanese(note.sampleLabel) : note.wineName
        )
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItemGroup(placement: .topBarTrailing) {
                NavigationLink {
                    TastingEditorView(note: note)
                } label: {
                    Text("Edit")
                }
                Button(role: .destructive) {
                    showingDeleteConfirmation = true
                } label: {
                    Image(systemName: "trash")
                }
                .accessibilityLabel("Delete tasting note")
            }
        }
        .alert("Delete tasting note?", isPresented: $showingDeleteConfirmation) {
            Button("Cancel", role: .cancel) {}
            Button("Delete", role: .destructive) {
                modelContext.delete(note)
                try? modelContext.save()
                dismiss()
            }
        } message: {
            Text("This removes the note from this device. Export a backup first if you may need it later.")
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
