import SwiftUI

struct ConversationSummaryView: View {
    @Environment(\.dismiss) private var dismiss

    let archive: ConversationArchive
    let savedReviewWordCount: Int
    let persistenceError: String?

    var body: some View {
        ScrollView {
            VStack(spacing: 18) {
                ConversationSummaryContent(
                    archive: archive,
                    savedReviewWordCount: savedReviewWordCount,
                    persistenceError: persistenceError
                )

                NavigationLink {
                    ConversationSessionView(configuration: archive.configuration)
                } label: {
                    Label("同じ場面でもう一度", systemImage: "arrow.counterclockwise")
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                }
                .buttonStyle(.borderedProminent)

                Button("場面選択へ戻る") { dismiss() }
                    .buttonStyle(.bordered)
            }
            .padding()
        }
        .navigationTitle("会話の振り返り")
        .navigationBarBackButtonHidden(true)
    }
}

struct ConversationHistoryDetailView: View {
    let record: ConversationSessionRecord

    var body: some View {
        Group {
            if let archive = record.archive {
                ScrollView {
                    ConversationSummaryContent(
                        archive: archive,
                        savedReviewWordCount: 0,
                        persistenceError: nil,
                        isHistory: true
                    )
                    .padding()
                }
            } else {
                ContentUnavailableView(
                    "履歴を開けません",
                    systemImage: "exclamationmark.triangle",
                    description: Text("保存した会話データを読み込めませんでした。")
                )
            }
        }
        .navigationTitle(record.scenario?.title ?? "会話履歴")
        .navigationBarTitleDisplayMode(.inline)
    }
}

private struct ConversationSummaryContent: View {
    let archive: ConversationArchive
    let savedReviewWordCount: Int
    let persistenceError: String?
    var isHistory = false

    @State private var showsDialogue = false

    private var learnerTurnCount: Int {
        archive.messages.filter { $0.role == .learner }.count
    }

    private var durationLabel: String {
        let minutes = archive.durationSeconds / 60
        let seconds = archive.durationSeconds % 60
        return String(format: "%d:%02d", minutes, seconds)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            VStack(spacing: 10) {
                Image(systemName: "checkmark.seal.fill")
                    .font(.system(size: 46))
                    .foregroundStyle(.green)
                Text("会話完了")
                    .font(.title2.bold())
                Text(archive.feedback.positiveNoteJapanese)
                    .font(.body)
                    .multilineTextAlignment(.center)
                    .foregroundStyle(.secondary)
            }
            .frame(maxWidth: .infinity)
            .padding()
            .background(.green.opacity(0.08), in: RoundedRectangle(cornerRadius: 18))

            HStack(spacing: 10) {
                metric(value: "\(learnerTurnCount)", label: "往復")
                metric(value: durationLabel, label: "会話時間")
                metric(value: archive.configuration.level.rawValue, label: "HSK")
            }

            VStack(alignment: .leading, spacing: 10) {
                Label("重要な直し", systemImage: "checkmark.bubble.fill")
                    .font(.headline)
                if archive.feedback.corrections.isEmpty {
                    Text("今回、優先して直す表現はありません。会話で使った文をもう一度声に出して定着させましょう。")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .padding()
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(.secondary.opacity(0.07), in: RoundedRectangle(cornerRadius: 13))
                } else {
                    ForEach(archive.feedback.corrections) { correction in
                        VStack(alignment: .leading, spacing: 7) {
                            Label(correction.originalChinese, systemImage: "xmark.circle")
                                .foregroundStyle(.red)
                            Label(correction.correctedChinese, systemImage: "checkmark.circle")
                                .fontWeight(.semibold)
                                .foregroundStyle(.green)
                            Text(correction.explanationJapanese)
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                        .padding()
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(.secondary.opacity(0.07), in: RoundedRectangle(cornerRadius: 13))
                    }
                }
            }

            if !archive.feedback.reviewWords.isEmpty {
                VStack(alignment: .leading, spacing: 10) {
                    Label("復習する語", systemImage: "rectangle.stack.badge.plus")
                        .font(.headline)
                    ConversationFlowLayout(spacing: 7) {
                        ForEach(archive.feedback.reviewWords, id: \.self) { word in
                            Text(word)
                                .font(.subheadline.bold())
                                .padding(.horizontal, 11)
                                .padding(.vertical, 7)
                                .background(.orange.opacity(0.12), in: Capsule())
                        }
                    }
                    if isHistory {
                        Text("会話終了時に、収録語彙と一致した語を復習対象にしています。")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    } else {
                        Text("収録語彙と一致した\(savedReviewWordCount)語を、単語の復習対象に追加しました。")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }

            DisclosureGroup("会話全文", isExpanded: $showsDialogue) {
                VStack(alignment: .leading, spacing: 12) {
                    ForEach(archive.messages) { message in
                        VStack(alignment: .leading, spacing: 3) {
                            Text(message.role == .learner ? "あなた" : "会話相手")
                                .font(.caption2.bold())
                                .foregroundStyle(.secondary)
                            Text(message.chinese)
                            if message.role == .partner, let pinyin = message.pinyin {
                                Text(pinyin)
                                    .font(.caption)
                                    .foregroundStyle(.indigo)
                            }
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
                .padding(.top, 10)
            }
            .padding()
            .background(.secondary.opacity(0.07), in: RoundedRectangle(cornerRadius: 13))

            HStack {
                Label(archive.provider.displayName, systemImage: "iphone.gen3")
                Spacer()
                Text(archive.endedAt, format: .dateTime.year().month().day().hour().minute())
            }
            .font(.caption)
            .foregroundStyle(.secondary)

            if let persistenceError {
                Label(persistenceError, systemImage: "exclamationmark.triangle.fill")
                    .font(.footnote)
                    .foregroundStyle(.red)
            }
        }
    }

    private func metric(value: String, label: String) -> some View {
        VStack(spacing: 3) {
            Text(value)
                .font(.title3.bold())
                .lineLimit(1)
                .minimumScaleFactor(0.7)
            Text(label)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(11)
        .frame(maxWidth: .infinity)
        .background(.secondary.opacity(0.07), in: RoundedRectangle(cornerRadius: 13))
    }
}
