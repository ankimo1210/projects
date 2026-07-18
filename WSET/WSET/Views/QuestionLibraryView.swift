import SwiftData
import SwiftUI

struct QuestionLibraryView: View {
    @Environment(EntitlementStore.self) private var entitlementStore
    @Query(sort: \StudyQuestion.prompt) private var questions: [StudyQuestion]
    @State private var searchText = ""
    @State private var selectedOutcome = LearningOutcome.all

    private var filteredQuestions: [StudyQuestion] {
        questions.filter { question in
            let canAccess = entitlementStore.policy.canAccessQuestion(
                id: question.id,
                studyMode: question.studyMode
            )
            let matchesSearch = searchText.isEmpty
                || question.searchableText.localizedCaseInsensitiveContains(searchText)
            let matchesOutcome = selectedOutcome == .all
                || question.learningOutcome == selectedOutcome.rawValue
            return canAccess && matchesSearch && matchesOutcome
        }
    }

    var body: some View {
        NavigationStack {
            List {
                Section("学習資料") {
                    NavigationLink {
                        GlossaryView()
                    } label: {
                        Label("用語辞書", systemImage: "character.book.closed")
                    }
                    .accessibilityIdentifier("reference.glossary.link")

                    NavigationLink {
                        ClassificationHubView()
                    } label: {
                        Label("格付け一覧", systemImage: "list.bullet.rectangle")
                    }
                    .accessibilityIdentifier("reference.classification.link")

                    NavigationLink {
                        RegionMapHubView()
                    } label: {
                        Label("産地マップ", systemImage: "map")
                    }
                    .accessibilityIdentifier("regionMap.hub.link")
                }

                Section {
                    Picker("学習成果", selection: $selectedOutcome) {
                        ForEach(LearningOutcome.allCases) { outcome in
                            Text(outcome.shortLabel).tag(outcome)
                        }
                    }
                }

                Section("\(filteredQuestions.count.formatted())問") {
                    ForEach(filteredQuestions) { question in
                        NavigationLink {
                            QuestionDetailView(question: question)
                        } label: {
                            QuestionRow(question: question)
                        }
                    }
                }

                if !entitlementStore.hasProAccess {
                    Section {
                        NavigationLink {
                            PaywallView(triggerFeature: .fullQuestionBank)
                        } label: {
                            Label("Proの問題集を見る", systemImage: "lock.fill")
                        }
                    } footer: {
                        Text("無料版では公開済みの無料問題だけを表示します。")
                    }
                }
            }
            .searchable(text: $searchText, prompt: "問題、解答、トピックで検索")
            .navigationTitle("問題集")
        }
    }
}
