import SwiftData
import SwiftUI

struct ConversationHubView: View {
    @EnvironmentObject private var contentStore: LearningContentStore
    @Query(sort: \ConversationSessionRecord.endedAt, order: .reverse)
    private var history: [ConversationSessionRecord]

    @State private var selectedLevel = HSKLevel.level1
    @State private var selectedScenario = ConversationScenario.selfIntroduction
    @State private var contentLoadMessage: String?

    private var appleAvailability: AppleConversationAvailability {
        ConversationClientFactory.appleAvailability()
    }

    private var configuration: ConversationConfiguration {
        ConversationConfiguration(level: selectedLevel, scenario: selectedScenario)
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                introCard
                levelSection
                scenarioSection

                if let contentLoadMessage {
                    Label(contentLoadMessage, systemImage: "exclamationmark.triangle.fill")
                        .font(.footnote)
                        .foregroundStyle(.orange)
                }

                NavigationLink {
                    ConversationSessionView(configuration: configuration)
                } label: {
                    Label("5分会話を始める", systemImage: "waveform.and.mic")
                        .font(.headline)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 14)
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.large)

                privacyNote
                historySection
            }
            .padding()
        }
        .navigationTitle("AI自由会話")
        .navigationBarTitleDisplayMode(.inline)
        .task(id: selectedLevel) {
            do {
                try await contentStore.ensureLoaded(for: selectedLevel, cumulative: true)
                contentLoadMessage = nil
            } catch {
                contentLoadMessage = "復習語彙の読み込みに失敗しました。会話練習はそのまま利用できます。"
            }
        }
    }

    private var introCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .top, spacing: 12) {
                Image(systemName: appleAvailability.canUseAppleModel ? "apple.intelligence" : "bubble.left.and.bubble.right.fill")
                    .font(.title2)
                    .foregroundStyle(.white)
                    .frame(width: 46, height: 46)
                    .background(.indigo, in: RoundedRectangle(cornerRadius: 13))
                VStack(alignment: .leading, spacing: 4) {
                    Text(appleAvailability.title)
                        .font(.headline)
                    Text(appleAvailability.detail)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
            }
            Divider()
            Label("5分または最大12往復・途中終了も可能", systemImage: "timer")
                .font(.footnote)
                .foregroundStyle(.secondary)
            Label("音声と文字入力のどちらでも回答可能", systemImage: "keyboard")
                .font(.footnote)
                .foregroundStyle(.secondary)
        }
        .padding()
        .background(.indigo.opacity(0.08), in: RoundedRectangle(cornerRadius: 18))
    }

    private var levelSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("会話レベル")
                .font(.title3.bold())
            Picker("会話レベル", selection: $selectedLevel) {
                ForEach(contentStore.availableLevels) { level in
                    Text(level.displayName).tag(level)
                }
            }
            .pickerStyle(.menu)
            .padding(.horizontal, 12)
            .padding(.vertical, 9)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(.secondary.opacity(0.08), in: RoundedRectangle(cornerRadius: 12))
            Text("語彙と文の長さを選択レベルに合わせます。")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }

    private var scenarioSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("場面")
                .font(.title3.bold())
            ForEach(ConversationScenario.allCases) { scenario in
                scenarioButton(scenario)
            }
        }
    }

    private func scenarioButton(_ scenario: ConversationScenario) -> some View {
        let isSelected = selectedScenario == scenario
        let iconForeground = isSelected ? Color.white : Color.indigo
        let iconBackground = isSelected ? Color.indigo : Color.indigo.opacity(0.1)
        let borderColor = isSelected ? Color.indigo : Color.secondary.opacity(0.18)
        let selectionColor = isSelected ? Color.indigo : Color.secondary.opacity(0.45)

        return Button {
            selectedScenario = scenario
        } label: {
            HStack(spacing: 13) {
                Image(systemName: scenario.icon)
                    .foregroundStyle(iconForeground)
                    .frame(width: 42, height: 42)
                    .background(iconBackground, in: RoundedRectangle(cornerRadius: 11))
                VStack(alignment: .leading, spacing: 3) {
                    Text(scenario.title)
                        .font(.headline)
                        .foregroundStyle(.primary)
                    Text(scenario.subtitle)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Image(systemName: isSelected ? "checkmark.circle.fill" : "circle")
                    .foregroundStyle(selectionColor)
            }
            .padding(12)
            .background(.background, in: RoundedRectangle(cornerRadius: 15))
            .overlay {
                RoundedRectangle(cornerRadius: 15)
                    .stroke(borderColor, lineWidth: 1.5)
            }
        }
        .buttonStyle(.plain)
    }

    private var privacyNote: some View {
        Label {
            Text("会話生成・音声認識・読み上げはAppleの端末内機能を使用します。録音は文字起こし後に削除し、会話履歴だけをこの端末に保存します。")
        } icon: {
            Image(systemName: "lock.shield.fill")
                .foregroundStyle(.green)
        }
        .font(.footnote)
        .foregroundStyle(.secondary)
        .padding()
        .background(.green.opacity(0.08), in: RoundedRectangle(cornerRadius: 15))
    }

    @ViewBuilder
    private var historySection: some View {
        if !history.isEmpty {
            VStack(alignment: .leading, spacing: 10) {
                HStack {
                    Text("最近の会話")
                        .font(.title3.bold())
                    Spacer()
                    Text("\(history.count)回")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                ForEach(history.prefix(5)) { record in
                    NavigationLink {
                        ConversationHistoryDetailView(record: record)
                    } label: {
                        HStack(spacing: 12) {
                            Image(systemName: record.scenario?.icon ?? "bubble.left.fill")
                                .foregroundStyle(.indigo)
                                .frame(width: 34, height: 34)
                                .background(.indigo.opacity(0.1), in: RoundedRectangle(cornerRadius: 9))
                            VStack(alignment: .leading, spacing: 2) {
                                Text(record.scenario?.title ?? "会話練習")
                                    .font(.subheadline.bold())
                                Text("\(record.level?.displayName ?? "HSK")・\(record.learnerTurnCount)往復")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            Spacer()
                            Text(record.endedAt, format: .dateTime.month().day())
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            Image(systemName: "chevron.right")
                                .font(.caption)
                                .foregroundStyle(.tertiary)
                        }
                        .padding(12)
                        .background(.secondary.opacity(0.06), in: RoundedRectangle(cornerRadius: 13))
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }
}
