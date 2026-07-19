import SwiftData
import SwiftUI

struct HomeView: View {
    @Binding var selectedTab: Int
    @Query private var progress: [StudyProgressRecord]
    @Query(sort: \ConversationSessionRecord.endedAt, order: .reverse)
    private var conversationHistory: [ConversationSessionRecord]
    @EnvironmentObject private var contentStore: LearningContentStore
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize

    private var vocabularyProgress: [StudyProgressRecord] {
        progress.filter { $0.skillRawValue == LearningSkill.vocabulary.rawValue }
    }

    private var dueCount: Int {
        vocabularyProgress.filter { ($0.nextReviewAt ?? .distantFuture) <= Date() }.count
    }

    private var masteredCount: Int {
        vocabularyProgress.filter { $0.reviewStage >= 3 }.count
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("你好！")
                        .font(.largeTitle.bold())
                    Text("今日は短くても、声に出して続けよう。")
                        .foregroundStyle(.secondary)
                }

                let metricLayout = dynamicTypeSize.isAccessibilitySize
                    ? AnyLayout(VStackLayout(spacing: 12))
                    : AnyLayout(HStackLayout(spacing: 12))
                metricLayout {
                    metricCard(value: "\(dueCount)", label: "今日の復習", color: .orange)
                    metricCard(value: "\(masteredCount)", label: "定着した語", color: .green)
                    metricCard(value: "\(vocabularyProgress.count)", label: "学習した語", color: .blue)
                }

                VStack(alignment: .leading, spacing: 10) {
                    Text("技能別の記録")
                        .font(.headline)
                    LazyVGrid(
                        columns: dynamicTypeSize.isAccessibilitySize
                            ? [GridItem(.flexible())]
                            : [GridItem(.flexible()), GridItem(.flexible())],
                        spacing: 10
                    ) {
                        skillCard(.listening, label: "聞く", icon: "ear")
                        skillCard(.reading, label: "読む", icon: "text.book.closed")
                        skillCard(.grammar, label: "文法・語順", icon: "textformat.abc")
                        skillCard(.writing, label: "書く", icon: "pencil")
                        skillCard(.speaking, label: "話す", icon: "waveform.and.mic")
                        skillCard(.translation, label: "翻訳", icon: "character.book.closed")
                    }
                }

                if let error = contentStore.loadError {
                    Label(error, systemImage: "exclamationmark.triangle.fill")
                        .font(.footnote)
                        .foregroundStyle(.orange)
                        .padding()
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(.orange.opacity(0.1), in: RoundedRectangle(cornerRadius: 14))
                }

                Text("学習メニュー")
                    .font(.title2.bold())

                featureButton(
                    title: "単語フラッシュカード",
                    subtitle: "HSK 1〜9・順番／シャッフル／復習",
                    icon: "rectangle.stack.fill",
                    color: .blue,
                    tab: 1
                )
                featureButton(
                    title: "文章トレーニング",
                    subtitle: "穴埋め・聞き取り・語順整序",
                    icon: "square.and.pencil",
                    color: .purple,
                    tab: 2
                )
                featureButton(
                    title: "短文読解",
                    subtitle: "音声・ピンイン・日本語を切り替え",
                    icon: "text.book.closed.fill",
                    color: .teal,
                    tab: 3
                )
                NavigationLink {
                    ConversationHubView()
                } label: {
                    HStack(spacing: 14) {
                        Image(systemName: "waveform.and.mic")
                            .font(.title2)
                            .foregroundStyle(.white)
                            .frame(width: 48, height: 48)
                            .background(.indigo, in: RoundedRectangle(cornerRadius: 13))
                        VStack(alignment: .leading, spacing: 3) {
                            Text("AI自由会話")
                                .font(.headline)
                                .foregroundStyle(.primary)
                            Text("端末内AI・音声入力・会話後の復習")
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                        Spacer()
                        Image(systemName: "chevron.right")
                            .foregroundStyle(.tertiary)
                    }
                    .padding()
                    .background(.background, in: RoundedRectangle(cornerRadius: 16))
                    .overlay { RoundedRectangle(cornerRadius: 16).stroke(.quaternary) }
                }
                .buttonStyle(.plain)
            }
            .padding()
        }
        .navigationTitle("My Tianjin")
    }

    private func metricCard(value: String, label: String, color: Color) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(value)
                .font(.title2.bold())
                .foregroundStyle(color)
            Text(label)
                .font(.caption)
                .foregroundStyle(.secondary)
                .lineLimit(1)
                .minimumScaleFactor(0.75)
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.secondary.opacity(0.08), in: RoundedRectangle(cornerRadius: 14))
    }

    private func featureButton(
        title: String,
        subtitle: String,
        icon: String,
        color: Color,
        tab: Int
    ) -> some View {
        Button { selectedTab = tab } label: {
            HStack(spacing: 14) {
                Image(systemName: icon)
                    .font(.title2)
                    .foregroundStyle(.white)
                    .frame(width: 48, height: 48)
                    .background(color, in: RoundedRectangle(cornerRadius: 13))
                VStack(alignment: .leading, spacing: 3) {
                    Text(title).font(.headline).foregroundStyle(.primary)
                    Text(subtitle).font(.subheadline).foregroundStyle(.secondary)
                }
                Spacer()
                Image(systemName: "chevron.right").foregroundStyle(.tertiary)
            }
            .padding()
            .background(.background, in: RoundedRectangle(cornerRadius: 16))
            .overlay { RoundedRectangle(cornerRadius: 16).stroke(.quaternary) }
        }
        .buttonStyle(.plain)
    }

    private func skillCard(
        _ skill: LearningSkill,
        label: String,
        icon: String
    ) -> some View {
        let records = progress.filter { $0.skillRawValue == skill.rawValue && $0.attemptCount > 0 }
        let attempts = records.reduce(0) { $0 + $1.attemptCount }
        let correct = records.reduce(0) { $0 + $1.correctCount }
        let accuracy = attempts > 0 ? Int((Double(correct) / Double(attempts) * 100).rounded()) : 0
        let activityLabel: String
        if skill == .speaking, !conversationHistory.isEmpty {
            activityLabel = attempts > 0
                ? "\(conversationHistory.count)会話・\(attempts)練習"
                : "\(conversationHistory.count)会話"
        } else {
            activityLabel = attempts == 0 ? "未学習" : "\(attempts)回・正答\(accuracy)%"
        }
        return HStack {
            Image(systemName: icon).foregroundStyle(.blue)
            VStack(alignment: .leading, spacing: 2) {
                Text(label).font(.subheadline.bold())
                Text(activityLabel)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
        }
        .padding(10)
        .background(.secondary.opacity(0.07), in: RoundedRectangle(cornerRadius: 12))
    }
}
