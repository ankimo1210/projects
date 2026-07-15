import SwiftUI

struct AdvancedTrackView: View {
    @State private var selectedLevelRaw = HSKAdvancedLevel.level7.rawValue

    private var selectedLevel: HSKAdvancedLevel {
        HSKAdvancedLevel(rawValue: selectedLevelRaw) ?? .level7
    }

    private var tasks: [HSKAdvancedTrackTask] {
        PracticeSeedContent.advancedTasks.filter { $0.supportedLevels.contains(selectedLevel) }
    }

    var body: some View {
        List {
            Section {
                Picker("級", selection: $selectedLevelRaw) {
                    ForEach(HSKAdvancedLevel.allCases, id: \.rawValue) { level in
                        Text("HSK \(level.rawValue)").tag(level.rawValue)
                    }
                }
                .pickerStyle(.segmented)
            } footer: {
                Text("7〜9級は単語数だけでなく、長文理解・産出・翻訳・口頭課題を独立して練習します。")
            }

            ForEach(HSKAdvancedTrackDomain.allCases, id: \.rawValue) { domain in
                let domainTasks = tasks.filter { $0.kind.domain == domain }
                if !domainTasks.isEmpty {
                    Section(domainName(domain)) {
                        ForEach(domainTasks) { task in
                            NavigationLink {
                                AdvancedTaskDetailView(task: task)
                            } label: {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(task.title).font(.headline)
                                    Text(task.instructions)
                                        .font(.subheadline)
                                        .foregroundStyle(.secondary)
                                    if let duration = task.recommendedDurationSeconds {
                                        Label("目安 \(durationLabel(duration))", systemImage: "timer")
                                            .font(.caption)
                                            .foregroundStyle(.purple)
                                    }
                                }
                                .padding(.vertical, 3)
                            }
                        }
                    }
                }
            }

            Section {
                Text("自由回答はルーブリックによる自己評価です。選択式問題のみ自動採点します。")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
        }
        .navigationTitle("HSK 7–9")
    }

    private func domainName(_ domain: HSKAdvancedTrackDomain) -> String {
        switch domain {
        case .listening: "聴解"
        case .reading: "読解"
        case .writing: "作文"
        case .translation: "翻訳・通訳"
        case .speaking: "スピーキング"
        }
    }

    private func durationLabel(_ seconds: Int) -> String {
        if seconds < 60 { return "\(seconds)秒" }
        return "\(seconds / 60)分"
    }
}

private struct AdvancedTaskDetailView: View {
    let task: HSKAdvancedTrackTask

    private var questions: [PracticeQuestion] {
        let ids = Set(task.questionIDs)
        return PracticeSeedContent.advancedQuestions.filter { ids.contains($0.id) }
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                Image(systemName: iconName)
                    .font(.system(size: 44))
                    .foregroundStyle(.indigo)
                Text(task.title).font(.largeTitle.bold())
                Text(task.instructions).foregroundStyle(.secondary)

                HStack {
                    Label(levelsLabel, systemImage: "chart.bar.fill")
                    if let duration = task.recommendedDurationSeconds {
                        Label(duration < 60 ? "\(duration)秒" : "\(duration / 60)分", systemImage: "timer")
                    }
                }
                .font(.subheadline)

                NavigationLink {
                    PracticeQuestionListView(title: task.title, questions: questions)
                } label: {
                    Label("課題を始める", systemImage: "play.fill")
                        .font(.headline)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                }
                .buttonStyle(.borderedProminent)
                .disabled(questions.isEmpty)

                Text("評価方法")
                    .font(.headline)
                Text(task.kind.responseMode == nil
                     ? "選択肢を自動採点し、解説を表示します。"
                     : "回答後に内容・構成・語彙・流暢さなどを基準別に自己評価します。")
                    .foregroundStyle(.secondary)
            }
            .padding()
        }
        .navigationTitle(task.title)
        .navigationBarTitleDisplayMode(.inline)
    }

    private var levelsLabel: String {
        task.supportedLevels.map { "HSK \($0.rawValue)" }.joined(separator: "・")
    }

    private var iconName: String {
        switch task.kind.domain {
        case .listening: "ear.fill"
        case .reading: "text.book.closed.fill"
        case .writing: "pencil.and.outline"
        case .translation: "character.book.closed.fill"
        case .speaking: "waveform.and.mic"
        }
    }
}
