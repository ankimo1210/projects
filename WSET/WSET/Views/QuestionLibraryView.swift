import SwiftData
import SwiftUI

struct QuestionLibraryView: View {
    @Query(sort: \StudyQuestion.prompt) private var questions: [StudyQuestion]
    @State private var searchText = ""
    @State private var selectedOutcome = LearningOutcome.all

    private var filteredQuestions: [StudyQuestion] {
        questions.filter { question in
            let matchesSearch = searchText.isEmpty
                || question.searchableText.localizedCaseInsensitiveContains(searchText)
            let matchesOutcome = selectedOutcome == .all
                || question.learningOutcome == selectedOutcome.rawValue
            return matchesSearch && matchesOutcome
        }
    }

    var body: some View {
        NavigationStack {
            List {
                Section {
                    Picker("Learning outcome", selection: $selectedOutcome) {
                        ForEach(LearningOutcome.allCases) { outcome in
                            Text(outcome.shortLabel).tag(outcome)
                        }
                    }
                }

                Section("\(filteredQuestions.count.formatted()) questions") {
                    ForEach(filteredQuestions) { question in
                        NavigationLink {
                            QuestionDetailView(question: question)
                        } label: {
                            QuestionRow(question: question)
                        }
                    }
                }
            }
            .searchable(text: $searchText, prompt: "Question, answer, or topic")
            .navigationTitle("Library")
        }
    }
}
