import SwiftData
import SwiftUI

struct VocabularyHubView: View {
    @EnvironmentObject private var contentStore: LearningContentStore
    @Query private var progress: [StudyProgressRecord]
    @State private var selectedLevelRaw = HSKLevel.level1.rawValue
    @State private var modeRaw = StudySessionMode.shuffle.rawValue
    @AppStorage("vocabularyCumulativeLevels") private var cumulative = true
    @AppStorage("vocabularySessionLength") private var sessionLength = 20

    private var selectedLevel: HSKLevel {
        HSKLevel(rawValue: selectedLevelRaw) ?? .level1
    }

    private var selectedMode: StudySessionMode {
        StudySessionMode(rawValue: modeRaw) ?? .shuffle
    }

    private var vocabulary: [VocabularyItem] {
        contentStore.vocabulary(for: selectedLevel, cumulative: cumulative)
    }

    private var vocabularyProgress: [StudyProgressRecord] {
        progress.filter { $0.skillRawValue == LearningSkill.vocabulary.rawValue }
    }

    private var dueCount: Int {
        let visibleItemIDs = Set(vocabulary.map(\.id))
        return vocabularyProgress.filter {
            visibleItemIDs.contains($0.itemID)
                && ($0.nextReviewAt ?? .distantFuture) <= Date()
        }.count
    }

    private var canUseSelectedContent: Bool {
        guard !contentStore.isLoading, vocabulary.count >= 4 else { return false }
        return contentStore.loadError == nil
            || (contentStore.isUsingFallback && selectedLevel == .level1)
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("HSKレベル")
                        .font(.headline)
                    Picker("HSKレベル", selection: $selectedLevelRaw) {
                        ForEach(contentStore.availableLevels) { level in
                            Text(level.displayName)
                                .tag(level.rawValue)
                        }
                    }
                    .pickerStyle(.menu)
                    .onChange(of: selectedLevelRaw) { _, _ in
                        ensureContentLoaded()
                    }

                    Toggle("選択レベルまでの語彙を含める", isOn: $cumulative)
                        .font(.subheadline)
                        .onChange(of: cumulative) { _, _ in
                            ensureContentLoaded()
                        }
                    Text("対象：\(vocabulary.count.formatted())語")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    if contentStore.isLoading {
                        ProgressView("単語を読み込み中…")
                            .font(.caption)
                    }
                    if let loadError = contentStore.loadError {
                        VStack(alignment: .leading, spacing: 6) {
                            Label(loadError, systemImage: "exclamationmark.triangle.fill")
                                .font(.caption)
                                .foregroundStyle(.orange)
                            Button("再試行", systemImage: "arrow.clockwise") {
                                ensureContentLoaded()
                            }
                            .buttonStyle(.bordered)
                            .controlSize(.small)
                        }
                    }
                }
                .padding()
                .background(.secondary.opacity(0.08), in: RoundedRectangle(cornerRadius: 16))

                VStack(alignment: .leading, spacing: 10) {
                    Text("出題順")
                        .font(.headline)
                    Picker("出題順", selection: $modeRaw) {
                        Text("順番").tag(StudySessionMode.sequential.rawValue)
                        Text("シャッフル").tag(StudySessionMode.shuffle.rawValue)
                        Text("今日の復習").tag(StudySessionMode.dueReview.rawValue)
                        Text("苦手").tag(StudySessionMode.weak.rawValue)
                    }
                    .pickerStyle(.menu)

                    HStack {
                        Text("1回の問題数")
                        Spacer()
                        Stepper("\(sessionLength)問", value: $sessionLength, in: 10...100, step: 10)
                            .labelsHidden()
                        Text("\(sessionLength)問")
                            .font(.subheadline.monospacedDigit())
                            .frame(width: 48, alignment: .trailing)
                    }
                    if selectedMode == .dueReview {
                        Label("現在 \(dueCount)語が復習対象です", systemImage: "clock.arrow.circlepath")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
                .padding()
                .background(.secondary.opacity(0.08), in: RoundedRectangle(cornerRadius: 16))

                NavigationLink {
                    VocabularyStudyView(
                        level: selectedLevel,
                        cumulative: cumulative,
                        mode: selectedMode,
                        maximumItemCount: sessionLength
                    )
                } label: {
                    Label("フラッシュカードを始める", systemImage: "play.fill")
                        .font(.headline)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 14)
                }
                .buttonStyle(.borderedProminent)
                .disabled(!canUseSelectedContent)

                NavigationLink {
                    VocabularyListView(level: selectedLevel, cumulative: cumulative)
                } label: {
                    Label("単語一覧を見る", systemImage: "list.bullet")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
                .disabled(!canUseSelectedContent)

                if selectedLevel == .advanced {
                    NavigationLink {
                        AdvancedTrackView()
                    } label: {
                        Label("HSK 7–9 専用トラック", systemImage: "graduationcap.fill")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.bordered)
                }

                Text("HSK 7–9の単語は7〜9級共通の公式語彙群です。技能別課題は専用トラックで学習します。")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
            .padding()
        }
        .navigationTitle("単語")
        .onAppear {
            contentStore.prepare()
            ensureContentLoaded()
        }
    }

    private func ensureContentLoaded() {
        Task {
            try? await contentStore.ensureLoaded(
                for: selectedLevel,
                cumulative: cumulative
            )
        }
    }
}
