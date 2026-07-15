import SwiftUI

struct PracticeHubView: View {
    @EnvironmentObject private var contentStore: LearningContentStore

    private var hsk1Vocabulary: [VocabularyItem] {
        contentStore.vocabulary(for: .level1, cumulative: false)
    }

    private var clozeQuestions: [PracticeQuestion] {
        GeneratedPracticeContent.clozeQuestions(vocabulary: hsk1Vocabulary)
    }

    private var audioQuestions: [PracticeQuestion] {
        GeneratedPracticeContent.audioQuestions(vocabulary: hsk1Vocabulary)
    }

    var body: some View {
        List {
            Section("基礎〜中級") {
                NavigationLink {
                    ChoicePracticeView(title: "単語穴埋め", questions: clozeQuestions)
                } label: {
                    practiceRow(
                        title: "単語穴埋め",
                        subtitle: "例文の空欄に合う語を選ぶ・\(clozeQuestions.count)問",
                        icon: "text.badge.checkmark",
                        color: .blue
                    )
                }

                NavigationLink {
                    ChoicePracticeView(title: "聞き取り", questions: audioQuestions)
                } label: {
                    practiceRow(
                        title: "音声 → 意味",
                        subtitle: "単語を聞いて日本語を選ぶ・\(audioQuestions.count)問",
                        icon: "ear.fill",
                        color: .orange
                    )
                }

                NavigationLink {
                    OrderingPracticeView(questions: PracticeSeedContent.orderingQuestions)
                } label: {
                    practiceRow(
                        title: "語順整序",
                        subtitle: "HSK 1〜3・\(PracticeSeedContent.orderingQuestions.count)問",
                        icon: "arrow.left.arrow.right",
                        color: .purple
                    )
                }
            }

            Section("HSK 5〜6") {
                NavigationLink {
                    PracticeQuestionListView(
                        title: "HSK 5〜6 応用",
                        questions: PracticeSeedContent.upperIntermediateQuestions
                    )
                } label: {
                    practiceRow(
                        title: "応用技能",
                        subtitle: "誤文・要約・作文・翻訳・口頭意見",
                        icon: "doc.text.magnifyingglass",
                        color: .teal
                    )
                }
            }

            Section("HSK 7〜9") {
                NavigationLink {
                    AdvancedTrackView()
                } label: {
                    practiceRow(
                        title: "上級専用トラック",
                        subtitle: "長文・論説・翻訳・通訳・スピーキング",
                        icon: "graduationcap.fill",
                        color: .indigo
                    )
                }
            }
        }
        .navigationTitle("文章練習")
        .onAppear { contentStore.prepare() }
    }

    private func practiceRow(
        title: String,
        subtitle: String,
        icon: String,
        color: Color
    ) -> some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .foregroundStyle(.white)
                .frame(width: 40, height: 40)
                .background(color, in: RoundedRectangle(cornerRadius: 11))
            VStack(alignment: .leading, spacing: 3) {
                Text(title).font(.headline)
                Text(subtitle).font(.caption).foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 4)
    }
}
