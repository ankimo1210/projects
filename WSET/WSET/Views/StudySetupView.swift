import SwiftData
import SwiftUI

struct StudySetupView: View {
    @Query private var questions: [StudyQuestion]
    @Query private var progressRecords: [QuestionProgress]
    @State private var selectedOutcome = LearningOutcome.all
    @State private var sessionSize = 20
    @State private var sessionQuestions: [StudyQuestion] = []
    @State private var mockQuestions: [StudyQuestion] = []
    @State private var showingSession = false
    @State private var showingMockExam = false

    private var eligibleQuestions: [StudyQuestion] {
        questions.filter { question in
            question.studyMode == "multiple_choice"
                && question.correctAnswerIndex != nil
                && (selectedOutcome == .all || question.learningOutcome == selectedOutcome.rawValue)
        }
    }

    private var mcqQuestions: [StudyQuestion] {
        questions.filter {
            $0.studyMode == "multiple_choice"
                && $0.correctAnswerIndex != nil
        }
    }

    private var progressByID: [String: QuestionProgress] {
        Dictionary(uniqueKeysWithValues: progressRecords.map { ($0.questionID, $0) })
    }

    private var mistakeQuestions: [StudyQuestion] {
        questions.filter {
            progressByID[$0.id]?.lastWasCorrect == false
        }
    }

    private var dueQuestions: [StudyQuestion] {
        questions.filter {
            guard let progress = progressByID[$0.id] else { return false }
            return progress.attemptCount > 0 && progress.dueDate <= .now
        }
    }

    private var bookmarkedQuestions: [StudyQuestion] {
        questions.filter {
            progressByID[$0.id]?.isBookmarked == true
        }
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Quick study") {
                    Picker("Learning outcome", selection: $selectedOutcome) {
                        ForEach(LearningOutcome.allCases) { outcome in
                            Text(outcome.shortLabel).tag(outcome)
                        }
                    }

                    Picker("Questions", selection: $sessionSize) {
                        Text("10").tag(10)
                        Text("20").tag(20)
                        Text("50").tag(50)
                    }
                    .pickerStyle(.segmented)

                    LabeledContent("Available", value: eligibleQuestions.count.formatted())

                    Button {
                        startSession(with: eligibleQuestions, count: sessionSize)
                    } label: {
                        Label("Start mixed study session", systemImage: "play.fill")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(AppTheme.wine)
                    .disabled(eligibleQuestions.isEmpty)
                }

                Section("Focused review") {
                    reviewButton("間違えた問題を復習", systemImage: "xmark.circle", questions: mistakeQuestions)
                    reviewButton("期限の来た問題を学習", systemImage: "calendar", questions: dueQuestions)
                    reviewButton("ブックマークを学習", systemImage: "bookmark", questions: bookmarkedQuestions)
                }

                Section {
                    LabeledContent("Question bank", value: mcqQuestions.count.formatted())
                    Button {
                        mockQuestions = Array(mcqQuestions.shuffled().prefix(50))
                        showingMockExam = mockQuestions.count == 50
                    } label: {
                        Label("Start 50-question mock exam", systemImage: "timer")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(AppTheme.wine)
                    .disabled(mcqQuestions.count < 50)
                } header: {
                    Text("Mock examination")
                } footer: {
                    Text("Answers remain hidden until submission. The result is saved to your progress history.")
                }

            }
            .navigationTitle("Study")
            .navigationDestination(isPresented: $showingSession) {
                StudySessionView(questions: sessionQuestions)
            }
            .navigationDestination(isPresented: $showingMockExam) {
                MockExamView(questions: mockQuestions)
            }
        }
    }

    private func reviewButton(
        _ label: String,
        systemImage: String,
        questions: [StudyQuestion]
    ) -> some View {
        Button {
            startSession(with: questions, count: min(20, questions.count))
        } label: {
            HStack {
                Label(label, systemImage: systemImage)
                Spacer()
                Text(questions.count.formatted())
                    .foregroundStyle(.secondary)
            }
        }
        .disabled(questions.isEmpty)
    }

    private func startSession(with questions: [StudyQuestion], count: Int) {
        sessionQuestions = Array(questions.shuffled().prefix(count))
        showingSession = !sessionQuestions.isEmpty
    }
}
