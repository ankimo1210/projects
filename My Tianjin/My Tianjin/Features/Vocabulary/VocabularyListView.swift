import SwiftData
import SwiftUI

struct VocabularyListView: View {
    let level: HSKLevel
    let cumulative: Bool

    @EnvironmentObject private var contentStore: LearningContentStore
    @EnvironmentObject private var speech: SpeechService
    @AppStorage("speechSpeedRawValue") private var speechSpeedRawValue = SpeechSpeed.normal.rawValue
    @State private var query = ""

    private var speed: SpeechSpeed {
        SpeechSpeed(rawValue: speechSpeedRawValue) ?? .normal
    }

    private var vocabulary: [VocabularyItem] {
        contentStore.vocabulary(for: level, cumulative: cumulative)
    }

    private var filteredVocabulary: [VocabularyItem] {
        let clean = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !clean.isEmpty else { return vocabulary }
        return vocabulary.filter {
            $0.hanzi.localizedCaseInsensitiveContains(clean)
                || $0.pinyin.localizedCaseInsensitiveContains(clean)
                || $0.japanese.contains(where: { $0.localizedCaseInsensitiveContains(clean) })
        }
    }

    var body: some View {
        List(filteredVocabulary) { item in
            HStack(spacing: 10) {
                NavigationLink {
                    VocabularyDetailView(item: item)
                } label: {
                    VStack(alignment: .leading, spacing: 3) {
                        HStack(spacing: 8) {
                            Text(item.hanzi).font(.headline)
                            Text(item.pinyin).font(.caption).foregroundStyle(.orange)
                            if item.isMachineTranslated {
                                Text("仮訳")
                                    .font(.caption2.bold())
                                    .foregroundStyle(.orange)
                                    .padding(.horizontal, 5)
                                    .background(.orange.opacity(0.12), in: Capsule())
                            }
                        }
                        Text(item.primaryJapanese)
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                }
                Button {
                    speech.speak(item.hanzi, speed: speed)
                } label: {
                    Image(systemName: "speaker.wave.2.fill")
                }
                .buttonStyle(.borderless)
                .frame(minWidth: 44, minHeight: 44)
                .accessibilityLabel("\(item.hanzi)を発音")
            }
        }
        .searchable(text: $query, prompt: "漢字・ピンイン・日本語")
        .navigationTitle("単語一覧（\(filteredVocabulary.count)）")
        .overlay {
            if vocabulary.isEmpty {
                if contentStore.isLoading {
                    ProgressView("単語を読み込み中…")
                } else if let loadError = contentStore.loadError {
                    ContentUnavailableView {
                        Label("単語を読み込めません", systemImage: "exclamationmark.triangle")
                    } description: {
                        Text(loadError)
                    } actions: {
                        Button("再試行", systemImage: "arrow.clockwise") {
                            loadContent()
                        }
                        .buttonStyle(.borderedProminent)
                    }
                }
            } else if filteredVocabulary.isEmpty {
                ContentUnavailableView.search(text: query)
            }
        }
        .onAppear {
            loadContent()
        }
        .onDisappear { speech.stop() }
    }

    private func loadContent() {
        Task {
            try? await contentStore.ensureLoaded(for: level, cumulative: cumulative)
        }
    }
}

struct VocabularyDetailView: View {
    let item: VocabularyItem

    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var modelContext
    @EnvironmentObject private var speech: SpeechService
    @AppStorage("speechSpeedRawValue") private var speechSpeedRawValue = SpeechSpeed.normal.rawValue
    @State private var reviewMessage: String?

    private var speed: SpeechSpeed {
        SpeechSpeed(rawValue: speechSpeedRawValue) ?? .normal
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                VStack(spacing: 8) {
                    Text(item.hanzi)
                        .font(.system(size: 54, weight: .bold, design: .rounded))
                    if let traditional = item.traditional, traditional != item.hanzi {
                        Text("繁体字：\(traditional)").foregroundStyle(.secondary)
                    }
                    Text(item.pinyin)
                        .font(.title2.weight(.medium))
                        .foregroundStyle(.orange)
                    Text(item.japanese.joined(separator: "／"))
                        .font(.title3)
                    Button {
                        speech.speak(item.hanzi, speed: speed)
                    } label: {
                        Label("単語を発音（\(speed.label)）", systemImage: "speaker.wave.2.fill")
                    }
                    .buttonStyle(.borderedProminent)
                }
                .frame(maxWidth: .infinity)

                HStack {
                    Label("新版HSK #\(item.officialIndex)", systemImage: "checkmark.seal")
                    if let partOfSpeech = item.displayPartOfSpeech {
                        Text(partOfSpeech)
                    }
                    if item.isMachineTranslated {
                        Text("日本語は仮訳")
                            .foregroundStyle(.orange)
                    }
                }
                .font(.caption)

                Divider()
                Text("例文").font(.title3.bold())
                if item.examples.isEmpty {
                    ContentUnavailableView(
                        "例文は準備中です",
                        systemImage: "text.badge.plus",
                        description: Text("単語の音声と復習機能は利用できます。")
                    )
                    .frame(minHeight: 150)
                } else {
                    ForEach(item.examples) { example in
                        HStack(alignment: .top) {
                            VStack(alignment: .leading, spacing: 5) {
                                Text(example.hanzi).font(.headline)
                                Text(example.pinyin).foregroundStyle(.orange)
                                Text(example.japanese).foregroundStyle(.secondary)
                            }
                            Spacer()
                            Button {
                                speech.speak(example.hanzi, speed: speed)
                            } label: {
                                Image(systemName: "speaker.wave.2.fill")
                            }
                            .buttonStyle(.bordered)
                            .frame(minWidth: 44, minHeight: 44)
                            .accessibilityLabel("例文を発音")
                        }
                        .padding()
                        .background(.secondary.opacity(0.08), in: RoundedRectangle(cornerRadius: 14))
                    }
                }

                Button {
                    do {
                        try StudyPersistence.markForReview(
                            itemID: item.id,
                            skill: .vocabulary,
                            in: modelContext
                        )
                        reviewMessage = "今日の復習に追加しました"
                    } catch {
                        reviewMessage = error.localizedDescription
                    }
                } label: {
                    Label("今日の復習に追加", systemImage: "plus.circle.fill")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)

                if let reviewMessage {
                    Text(reviewMessage)
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity, alignment: .center)
                }
            }
            .padding()
        }
        .navigationTitle("単語詳細")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button("閉じる") { dismiss() }
            }
        }
        .onDisappear { speech.stop() }
    }
}
