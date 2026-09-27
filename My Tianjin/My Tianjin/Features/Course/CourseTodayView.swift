import Foundation
import SwiftData
import SwiftUI

struct CourseTodayView: View {
    @Binding var selectedTab: Int

    @Environment(\.modelContext) private var modelContext
    @Environment(\.scenePhase) private var scenePhase
    @StateObject private var courseStore = CourseStore()
    @State private var loadState = LoadState.loading
    @State private var selectedMinutes = 3
    @State private var referenceDate = Date()
    @State private var destinationSessionID: UUID?
    @State private var lastStartWasReview = false

    private enum LoadState: Equatable {
        case loading
        case loaded
        case failed
    }

    var body: some View {
        Group {
            switch loadState {
            case .loading:
                ProgressView("コースを読み込んでいます…")
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            case .failed:
                loadFailureView
            case .loaded:
                loadedView
            }
        }
        .navigationTitle("今日")
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                NavigationLink {
                    HomeView(selectedTab: $selectedTab)
                } label: {
                    Label("学習メニュー", systemImage: "square.grid.2x2")
                }
                .tint(.teal)
            }
        }
        .navigationDestination(item: $destinationSessionID) { sessionID in
            CourseSessionView(courseStore: courseStore, sessionID: sessionID)
        }
        .task {
            if loadState == .loading {
                reloadCourse()
            }
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 60_000_000_000)
                guard !Task.isCancelled else { return }
                referenceDate = Date()
            }
        }
        .onChange(of: scenePhase) { _, phase in
            if phase == .active {
                referenceDate = Date()
            }
        }
        .onAppear {
            referenceDate = Date()
        }
    }

    @ViewBuilder
    private var loadedView: some View {
        if let lesson = courseStore.lesson,
           let snapshot = courseStore.snapshot {
            if lesson.questions.isEmpty {
                ContentUnavailableView {
                    Label("この単元には問題がありません", systemImage: "doc.questionmark")
                } description: {
                    Text("教材データを確認して、もう一度読み込んでください。")
                } actions: {
                    Button("もう一度読み込む", action: reloadCourse)
                }
            } else {
                todayContent(lesson: lesson, snapshot: snapshot)
            }
        } else {
            ContentUnavailableView {
                Label("コースデータが見つかりません", systemImage: "exclamationmark.triangle")
            } description: {
                Text("同梱されている教材と保存済みの学習記録を確認できませんでした。")
            } actions: {
                Button("もう一度読み込む", action: reloadCourse)
            }
        }
    }

    private var loadFailureView: some View {
        ContentUnavailableView {
            Label("コースを読み込めませんでした", systemImage: "exclamationmark.triangle")
        } description: {
            Text(courseStore.errorMessage ?? "教材または学習記録を確認できませんでした。")
        } actions: {
            Button("再試行", action: reloadCourse)
                .buttonStyle(.borderedProminent)
                .tint(.teal)
        }
    }

    private func todayContent(
        lesson: CourseLesson,
        snapshot: CourseSnapshot
    ) -> some View {
        let learnedCount = learnedQuestionCount(lesson: lesson, snapshot: snapshot)
        let dueCount = dueQuestionCount(lesson: lesson, snapshot: snapshot, at: referenceDate)
        let plannedCount = plannedQuestionCount(
            lesson: lesson,
            snapshot: snapshot,
            minutes: selectedMinutes,
            at: referenceDate
        )
        let activeSession = snapshot.activeSession

        return ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                VStack(alignment: .leading, spacing: 10) {
                    Text("HSK 3級を目指す")
                        .font(.largeTitle.bold())

                    Text("先行体験")
                        .font(.caption.bold())
                        .foregroundStyle(.teal)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 5)
                        .background(.teal.opacity(0.12), in: Capsule())

                    Text(lesson.title)
                        .font(.title2.bold())
                    Text(lesson.subtitle)
                        .font(.body)
                        .foregroundStyle(.secondary)
                    Label(lesson.examProfile.note, systemImage: "doc.badge.clock")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }

                learningSection(
                    activeSession: activeSession,
                    plannedCount: plannedCount
                )

                VStack(alignment: .leading, spacing: 12) {
                    HStack(alignment: .firstTextBaseline) {
                        Text("この単元の進み具合")
                            .font(.headline)
                        Spacer()
                        Text("\(learnedCount) / \(lesson.questions.count)問")
                            .font(.headline.monospacedDigit())
                            .foregroundStyle(.teal)
                    }
                    ProgressView(value: Double(learnedCount), total: Double(lesson.questions.count))
                        .tint(.teal)
                        .accessibilityLabel("この単元の学習進捗")
                        .accessibilityValue("\(lesson.questions.count)問中\(learnedCount)問に回答")

                    if learnedCount == 0 {
                        Text("最初の問題から始められます。回答数は習得度を表すものではありません。")
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    } else if learnedCount == lesson.questions.count {
                        Label(
                            "この単元の全\(lesson.questions.count)問に取り組みました",
                            systemImage: "checkmark.circle"
                        )
                            .font(.subheadline)
                    } else {
                        Text("回答した問題数を表示しています。")
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }
                }
                .courseCard()

                reviewSection(
                    lesson: lesson,
                    snapshot: snapshot,
                    learnedCount: learnedCount,
                    dueCount: dueCount,
                    activeSession: activeSession
                )

                if let errorMessage = courseStore.errorMessage {
                    VStack(alignment: .leading, spacing: 10) {
                        Label(errorMessage, systemImage: "exclamationmark.triangle.fill")
                            .font(.subheadline)
                        Button("もう一度試す") {
                            openSession(reviewOnly: lastStartWasReview)
                        }
                        .buttonStyle(.bordered)
                    }
                    .foregroundStyle(.red)
                    .courseCard()
                }
            }
            .padding()
        }
    }

    private func learningSection(
        activeSession: CourseSession?,
        plannedCount: Int
    ) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            Text(activeSession == nil ? "学習時間" : "進行中の学習")
                .font(.headline)

            if let activeSession {
                let remainingCount = activeSession.questionIDs.count - activeSession.currentIndex
                Text(
                    "残り\(remainingCount)問・目安\(remainingCount)分（全\(activeSession.questionIDs.count)問）"
                )
                .font(.subheadline)
                .foregroundStyle(.secondary)
            } else {
                Picker("学習時間の目安", selection: $selectedMinutes) {
                    Text("3分").tag(3)
                    Text("10分").tag(10)
                }
                .pickerStyle(.segmented)
                .accessibilityHint("学習する問題数の目安を選びます")

                Text("目安\(selectedMinutes)分・\(plannedCount)問")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            Button {
                openSession(reviewOnly: false)
            } label: {
                Label(
                    activeSession == nil ? "今日の学習" : "続きから",
                    systemImage: activeSession == nil ? "play.fill" : "arrow.right.circle.fill"
                )
                .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .tint(.teal)
            .controlSize(.large)
            .disabled(activeSession == nil && plannedCount == 0)
        }
    }

    private func reviewSection(
        lesson: CourseLesson,
        snapshot: CourseSnapshot,
        learnedCount: Int,
        dueCount: Int,
        activeSession: CourseSession?
    ) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Label("復習", systemImage: "clock.arrow.circlepath")
                    .font(.headline)
                Spacer()
                Text("期限到来 \(dueCount)問")
                    .font(.subheadline.monospacedDigit())
                    .foregroundStyle(dueCount > 0 ? Color.teal : Color.secondary)
            }

            if dueCount > 0 {
                Text("期限の来た問題だけを、期限が古い順に復習します。")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            } else if learnedCount == 0 {
                Text("復習は学習後に表示されます。まずは今日の学習から始めましょう。")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            } else if let nextReview = nextReviewDate(lesson: lesson, snapshot: snapshot) {
                Text("次の復習予定：\(nextReview.formatted(.dateTime.month().day().hour().minute()))")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            } else if learnedCount == lesson.questions.count {
                Text("この単元の学習は完了しています。新しい復習予定はありません。")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            } else {
                Text("今は期限の来た問題がありません。")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            Button {
                openSession(reviewOnly: true)
            } label: {
                Label("期限の来た問題を復習", systemImage: "arrow.clockwise")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.bordered)
            .tint(.teal)
            .controlSize(.large)
            .disabled(dueCount == 0 || activeSession != nil)
        }
        .courseCard()
    }

    private func reloadCourse() {
        loadState = .loading
        referenceDate = Date()
        loadState = courseStore.load(in: modelContext.container) ? .loaded : .failed
    }

    private func openSession(reviewOnly: Bool) {
        lastStartWasReview = reviewOnly
        courseStore.clearError()

        if let activeSession = courseStore.snapshot?.activeSession {
            destinationSessionID = activeSession.id
            return
        }

        guard courseStore.start(minutes: selectedMinutes, reviewOnly: reviewOnly),
              let sessionID = courseStore.snapshot?.activeSession?.id else {
            return
        }
        destinationSessionID = sessionID
    }

    private func learnedQuestionCount(
        lesson: CourseLesson,
        snapshot: CourseSnapshot
    ) -> Int {
        lesson.questions.lazy.filter {
            (snapshot.progress[$0.id]?.attemptCount ?? 0) > 0
        }.count
    }

    private func dueQuestionCount(
        lesson: CourseLesson,
        snapshot: CourseSnapshot,
        at date: Date
    ) -> Int {
        lesson.questions.lazy.filter {
            snapshot.progress[$0.id]?.isDue(at: date) == true
        }.count
    }

    private func plannedQuestionCount(
        lesson: CourseLesson,
        snapshot: CourseSnapshot,
        minutes: Int,
        at date: Date
    ) -> Int {
        let eligibleCount = lesson.questions.lazy.filter { question in
            if snapshot.progress[question.id]?.isDue(at: date) == true {
                return true
            }
            guard let progress = snapshot.progress[question.id] else {
                return true
            }
            return progress.attemptCount == 0 && progress.nextReviewAt == nil
        }.count
        return min(minutes >= 10 ? 10 : 3, eligibleCount)
    }

    private func nextReviewDate(
        lesson: CourseLesson,
        snapshot: CourseSnapshot
    ) -> Date? {
        lesson.questions.compactMap {
            snapshot.progress[$0.id]?.nextReviewAt
        }.min()
    }
}

private extension View {
    func courseCard() -> some View {
        padding(16)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(.secondary.opacity(0.08), in: RoundedRectangle(cornerRadius: 16))
    }
}
