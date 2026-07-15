import SwiftData
import SwiftUI

struct ReadingLibraryView: View {
    @State private var maximumLevelRaw = PracticeHSKLevel.level3.rawValue

    private var maximumLevel: PracticeHSKLevel {
        PracticeHSKLevel(rawValue: maximumLevelRaw) ?? .level3
    }

    private var seeds: [PracticeReadingSeed] {
        PracticeSeedContent.beginnerReadingSeeds.filter { $0.passage.level <= maximumLevel }
    }

    var body: some View {
        List {
            Section {
                Picker("レベル", selection: $maximumLevelRaw) {
                    Text("HSK 1").tag(PracticeHSKLevel.level1.rawValue)
                    Text("HSK 2").tag(PracticeHSKLevel.level2.rawValue)
                    Text("HSK 3").tag(PracticeHSKLevel.level3.rawValue)
                }
                .pickerStyle(.segmented)
            } footer: {
                Text("選んだレベルまでのオリジナル短文を表示します。")
            }

            Section("短文（\(seeds.count)本）") {
                ForEach(seeds) { seed in
                    NavigationLink {
                        ReadingDetailView(seed: seed)
                    } label: {
                        VStack(alignment: .leading, spacing: 5) {
                            HStack {
                                Text(seed.passage.title ?? "短文読解").font(.headline)
                                Spacer()
                                Text("HSK \(seed.passage.level.rawValue)")
                                    .font(.caption.bold())
                                    .foregroundStyle(.teal)
                            }
                            Text(seed.passage.fullText)
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                                .lineLimit(2)
                            HStack {
                                Label("\(seed.questions.count)問", systemImage: "questionmark.circle")
                                Label("\(seed.vocabularyAnnotations.count)語", systemImage: "textformat")
                            }
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        }
                        .padding(.vertical, 3)
                    }
                }
            }

            Section("応用読解") {
                ForEach(PracticeSeedContent.upperIntermediatePassages) { passage in
                    NavigationLink {
                        StandaloneReadingView(
                            passage: passage,
                            questions: questions(for: passage)
                        )
                    } label: {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(passage.title ?? "応用文章").font(.headline)
                            Text(passage.fullText).lineLimit(2).foregroundStyle(.secondary)
                            Text("HSK \(passage.level.rawValue)")
                                .font(.caption).foregroundStyle(.purple)
                        }
                    }
                }
            }
        }
        .navigationTitle("読解")
    }

    private func questions(for passage: PracticePassage) -> [PracticeQuestion] {
        PracticeSeedContent.upperIntermediateQuestions.filter { question in
            switch question.content {
            case let .readingComprehension(value):
                value.passageID == passage.id
            case let .summary(value), let .essay(value), let .oralOpinion(value):
                value.passageID == passage.id
            case let .translation(value):
                value.response.passageID == passage.id
            default:
                false
            }
        }
    }
}

private struct StandaloneReadingView: View {
    let passage: PracticePassage
    let questions: [PracticeQuestion]

    @Environment(\.modelContext) private var modelContext
    @EnvironmentObject private var speech: SpeechService
    @AppStorage("speechSpeedRawValue") private var speechSpeedRawValue = SpeechSpeed.normal.rawValue
    @AppStorage("readingShowsPinyin") private var showsPinyin = true
    @AppStorage("readingShowsJapanese") private var showsJapanese = false
    @State private var completionMessage: String?

    private var speed: SpeechSpeed {
        SpeechSpeed(rawValue: speechSpeedRawValue) ?? .normal
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                HStack {
                    Label("HSK \(passage.level.rawValue)", systemImage: "chart.bar")
                    if let seconds = passage.estimatedReadingSeconds {
                        Label("約\(seconds)秒", systemImage: "timer")
                    }
                    Spacer()
                    Button("全文", systemImage: "speaker.wave.2.fill") {
                        speech.speak(passage.fullText, speed: speed)
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.small)
                }
                .font(.caption)

                HStack {
                    Toggle("ピンイン", isOn: $showsPinyin)
                    Toggle("日本語", isOn: $showsJapanese)
                }
                .toggleStyle(.button)
                .buttonStyle(.bordered)
                .controlSize(.small)

                ForEach(passage.segments) { segment in
                    HStack(alignment: .top, spacing: 12) {
                        VStack(alignment: .leading, spacing: 6) {
                            Text(segment.content.text).font(.title3.weight(.medium))
                            if showsPinyin, let pinyin = segment.content.pinyin {
                                Text(pinyin).font(.subheadline).foregroundStyle(.orange)
                            }
                            if showsJapanese, let japanese = segment.content.japanese {
                                Text(japanese).font(.subheadline).foregroundStyle(.secondary)
                            }
                        }
                        Spacer()
                        Button {
                            speech.speak(
                                segment.content.speechText ?? segment.content.text,
                                speed: speed
                            )
                        } label: {
                            Image(systemName: "speaker.wave.2.fill")
                        }
                        .buttonStyle(.bordered)
                        .controlSize(.small)
                        .frame(minWidth: 44, minHeight: 44)
                        .accessibilityLabel("この文を発音")
                    }
                    .padding()
                    .background(.purple.opacity(0.07), in: RoundedRectangle(cornerRadius: 15))
                }

                if !questions.isEmpty {
                    NavigationLink {
                        PracticeQuestionListView(
                            title: passage.title ?? "応用問題",
                            questions: questions
                        )
                    } label: {
                        Label("関連課題に進む（\(questions.count)問）", systemImage: "pencil.and.list.clipboard")
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 10)
                    }
                    .buttonStyle(.borderedProminent)
                }

                Button {
                    do {
                        _ = try StudyPersistence.recordAnswer(
                            itemID: passage.id,
                            skill: .reading,
                            isCorrect: true,
                            in: modelContext
                        )
                        completionMessage = "読了を記録しました"
                    } catch {
                        completionMessage = error.localizedDescription
                    }
                } label: {
                    Label("読了として記録", systemImage: "checkmark.circle")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)

                if let completionMessage {
                    Text(completionMessage)
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity, alignment: .center)
                }
            }
            .padding()
        }
        .navigationTitle(passage.title ?? "応用読解")
        .navigationBarTitleDisplayMode(.inline)
        .onDisappear { speech.stop() }
    }
}

private struct ReadingDetailView: View {
    let seed: PracticeReadingSeed

    @Environment(\.modelContext) private var modelContext
    @EnvironmentObject private var contentStore: LearningContentStore
    @EnvironmentObject private var speech: SpeechService
    @AppStorage("speechSpeedRawValue") private var speechSpeedRawValue = SpeechSpeed.normal.rawValue
    @AppStorage("readingShowsPinyin") private var showsPinyin = true
    @AppStorage("readingShowsJapanese") private var showsJapanese = false
    @State private var selectedAnnotation: PracticeVocabularyAnnotation?
    @State private var completionMessage: String?

    private var speed: SpeechSpeed {
        SpeechSpeed(rawValue: speechSpeedRawValue) ?? .normal
    }

    private var referenceVocabulary: [VocabularyItem] {
        contentStore.vocabulary(for: .level3, cumulative: true)
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                HStack {
                    Label("HSK \(seed.passage.level.rawValue)", systemImage: "chart.bar")
                    if let seconds = seed.passage.estimatedReadingSeconds {
                        Label("約\(seconds)秒", systemImage: "timer")
                    }
                    Spacer()
                    Button {
                        speech.speak(seed.passage.fullText, speed: speed)
                    } label: {
                        Label("全文", systemImage: "speaker.wave.2.fill")
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.small)
                }
                .font(.caption)

                HStack {
                    Toggle("ピンイン", isOn: $showsPinyin)
                    Toggle("日本語", isOn: $showsJapanese)
                }
                .toggleStyle(.button)
                .buttonStyle(.bordered)
                .controlSize(.small)

                ForEach(seed.passage.segments) { segment in
                    HStack(alignment: .top, spacing: 12) {
                        VStack(alignment: .leading, spacing: 6) {
                            Text(segment.content.text)
                                .font(.title3.weight(.medium))
                            if showsPinyin, let pinyin = segment.content.pinyin {
                                Text(pinyin)
                                    .font(.subheadline)
                                    .foregroundStyle(.orange)
                            }
                            if showsJapanese, let japanese = segment.content.japanese {
                                Text(japanese)
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)
                            }
                        }
                        Spacer()
                        Button {
                            speech.speak(
                                segment.content.speechText ?? segment.content.text,
                                speed: speed
                            )
                        } label: {
                            Image(systemName: "speaker.wave.2.fill")
                        }
                        .buttonStyle(.bordered)
                        .controlSize(.small)
                        .frame(minWidth: 44, minHeight: 44)
                        .accessibilityLabel("この文を発音")
                    }
                    .padding()
                    .background(.teal.opacity(0.07), in: RoundedRectangle(cornerRadius: 15))
                }

                VStack(alignment: .leading, spacing: 10) {
                    Text("文章内の単語（タップで詳細）")
                        .font(.headline)
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 8) {
                            ForEach(seed.vocabularyAnnotations) { annotation in
                                Button {
                                    selectedAnnotation = annotation
                                } label: {
                                    VStack(spacing: 2) {
                                        Text(annotation.hanzi).font(.headline)
                                        Text(annotation.pinyin).font(.caption).foregroundStyle(.orange)
                                    }
                                    .padding(.horizontal, 12)
                                    .padding(.vertical, 8)
                                }
                                .buttonStyle(.bordered)
                            }
                        }
                    }
                }

                NavigationLink {
                    ChoicePracticeView(
                        title: seed.passage.title ?? "読解問題",
                        questions: seed.questions
                    )
                } label: {
                    Label("設問に答える（\(seed.questions.count)問）", systemImage: "questionmark.circle.fill")
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 10)
                }
                .buttonStyle(.borderedProminent)

                Button {
                    do {
                        _ = try StudyPersistence.recordAnswer(
                            itemID: seed.passage.id,
                            skill: .reading,
                            isCorrect: true,
                            in: modelContext
                        )
                        completionMessage = "読了を記録しました"
                    } catch {
                        completionMessage = error.localizedDescription
                    }
                } label: {
                    Label("読了として記録", systemImage: "checkmark.circle")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)

                if let completionMessage {
                    Text(completionMessage)
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity, alignment: .center)
                }
            }
            .padding()
        }
        .navigationTitle(seed.passage.title ?? "短文読解")
        .navigationBarTitleDisplayMode(.inline)
        .sheet(item: $selectedAnnotation) { annotation in
            if let item = vocabularyItem(for: annotation) {
                NavigationStack { VocabularyDetailView(item: item) }
            } else {
                NavigationStack {
                    ReadingAnnotationView(annotation: annotation)
                }
            }
        }
        .task {
            try? await contentStore.ensureLoaded(for: .level3, cumulative: true)
        }
        .onDisappear { speech.stop() }
    }

    private func vocabularyItem(for annotation: PracticeVocabularyAnnotation) -> VocabularyItem? {
        referenceVocabulary.first { $0.hanzi == annotation.hanzi }
    }
}

private struct ReadingAnnotationView: View {
    let annotation: PracticeVocabularyAnnotation

    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var speech: SpeechService
    @AppStorage("speechSpeedRawValue") private var speechSpeedRawValue = SpeechSpeed.normal.rawValue

    private var speed: SpeechSpeed {
        SpeechSpeed(rawValue: speechSpeedRawValue) ?? .normal
    }

    var body: some View {
        VStack(spacing: 14) {
            Text(annotation.hanzi).font(.system(size: 52, weight: .bold))
            Text(annotation.pinyin).font(.title2).foregroundStyle(.orange)
            Text(annotation.japanese).font(.title3)
            Button("発音", systemImage: "speaker.wave.2.fill") {
                speech.speak(annotation.hanzi, speed: speed)
            }
            .buttonStyle(.borderedProminent)
            Text("この注釈語は現在の公式単語データと完全一致しないため、単語復習への追加はできません。")
                .font(.footnote)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding()
        .navigationTitle("単語注釈")
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button("閉じる") { dismiss() }
            }
        }
        .onDisappear { speech.stop() }
    }
}
