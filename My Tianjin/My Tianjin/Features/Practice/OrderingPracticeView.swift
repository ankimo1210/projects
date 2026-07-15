import SwiftData
import SwiftUI

struct OrderingPracticeView: View {
    let questions: [PracticeQuestion]

    @EnvironmentObject private var speech: SpeechService
    @Environment(\.modelContext) private var modelContext
    @AppStorage("speechSpeedRawValue") private var speechSpeedRawValue = SpeechSpeed.normal.rawValue
    @State private var index = 0
    @State private var availableTokens: [PracticeOrderingToken] = []
    @State private var selectedTokenIDs: [String] = []
    @State private var result: PracticeGradingResult?
    @State private var persistenceError: String?

    private var speed: SpeechSpeed {
        SpeechSpeed(rawValue: speechSpeedRawValue) ?? .normal
    }

    var body: some View {
        Group {
            if questions.isEmpty {
                ContentUnavailableView("語順問題がありません", systemImage: "arrow.left.arrow.right")
            } else if index >= questions.count {
                VStack(spacing: 16) {
                    Image(systemName: "checkmark.seal.fill")
                        .font(.system(size: 56)).foregroundStyle(.green)
                    Text("語順練習完了").font(.title.bold())
                    Button("もう一度") {
                        index = 0
                        prepareQuestion()
                    }
                    .buttonStyle(.borderedProminent)
                }
            } else if let payload = orderingPayload {
                ScrollView {
                    VStack(alignment: .leading, spacing: 18) {
                        HStack {
                            Text("\(index + 1) / \(questions.count)")
                            ProgressView(value: Double(index + 1), total: Double(questions.count))
                        }
                        Text(payload.prompt.instruction)
                            .font(.headline)

                        VStack(alignment: .leading, spacing: 8) {
                            Text("あなたの文").font(.caption).foregroundStyle(.secondary)
                            ScrollView(.horizontal, showsIndicators: false) {
                                HStack(spacing: 6) {
                                    if selectedTokenIDs.isEmpty {
                                        Text("下の語句を順番にタップ")
                                            .foregroundStyle(.tertiary)
                                    }
                                    ForEach(selectedTokens) { token in
                                        Button(token.content.text) { remove(token) }
                                            .buttonStyle(.borderedProminent)
                                            .tint(.blue)
                                            .disabled(result != nil)
                                            .accessibilityLabel("\(token.content.text)を文から外す")
                                    }
                                }
                            }
                            .frame(maxWidth: .infinity, minHeight: 82, alignment: .leading)
                        }
                        .padding()
                        .background(.blue.opacity(0.07), in: RoundedRectangle(cornerRadius: 16))

                        Text("語句").font(.caption).foregroundStyle(.secondary)
                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack(spacing: 8) {
                                ForEach(availableTokens) { token in
                                    Button(token.content.text) { select(token) }
                                        .buttonStyle(.bordered)
                                        .disabled(result != nil)
                                        .accessibilityLabel("\(token.content.text)を文に追加")
                                }
                            }
                        }

                        HStack {
                            Button("リセット", systemImage: "arrow.counterclockwise") { prepareQuestion() }
                                .buttonStyle(.bordered)
                            Button("回答する", systemImage: "checkmark") { grade() }
                                .buttonStyle(.borderedProminent)
                                .disabled(selectedTokenIDs.count != payload.tokens.count || result != nil)
                        }
                        .frame(maxWidth: .infinity)

                        VStack(alignment: .leading, spacing: 8) {
                            if let result {
                                Label(
                                    result.outcome == .correct ? "正解" : "不正解",
                                    systemImage: result.outcome == .correct
                                        ? "checkmark.circle.fill" : "xmark.circle.fill"
                                )
                                .font(.headline)
                                .foregroundStyle(result.outcome == .correct ? .green : .red)
                                Text("正解：\(correctSentence(payload))")
                                    .font(.headline)
                                Button("正解を聞く", systemImage: "speaker.wave.2.fill") {
                                    speech.speak(correctSentence(payload), speed: speed)
                                }
                                .buttonStyle(.bordered)
                            } else {
                                Text("すべての語句を並べてください。")
                                    .foregroundStyle(.secondary)
                            }
                        }
                        .padding()
                        .frame(maxWidth: .infinity, minHeight: 112, alignment: .leading)
                        .background(.secondary.opacity(0.08), in: RoundedRectangle(cornerRadius: 14))

                        Button("次へ", systemImage: "arrow.right") {
                            index += 1
                            prepareQuestion()
                        }
                        .buttonStyle(.borderedProminent)
                        .frame(maxWidth: .infinity)
                        .disabled(result == nil)
                    }
                    .padding()
                }
            }
        }
        .navigationTitle("語順整序")
        .navigationBarTitleDisplayMode(.inline)
        .onAppear { prepareQuestion() }
        .onDisappear { speech.stop() }
        .alert("学習記録を保存できません", isPresented: persistenceErrorBinding) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(persistenceError ?? "不明なエラー")
        }
    }

    private var orderingPayload: PracticeOrderingQuestion? {
        guard questions.indices.contains(index),
              case let .sentenceOrdering(payload) = questions[index].content else { return nil }
        return payload
    }

    private var selectedTokens: [PracticeOrderingToken] {
        guard let payload = orderingPayload else { return [] }
        let byID = Dictionary(uniqueKeysWithValues: payload.tokens.map { ($0.id, $0) })
        return selectedTokenIDs.compactMap { byID[$0] }
    }

    private func prepareQuestion() {
        guard let payload = orderingPayload else {
            availableTokens = []
            return
        }
        availableTokens = DeterministicShuffle.shuffled(
            payload.tokens,
            seed: DeterministicShuffle.stableHash(questions[index].id)
        )
        selectedTokenIDs = []
        result = nil
    }

    private func select(_ token: PracticeOrderingToken) {
        guard result == nil else { return }
        availableTokens.removeAll { $0.id == token.id }
        selectedTokenIDs.append(token.id)
    }

    private func remove(_ token: PracticeOrderingToken) {
        guard result == nil else { return }
        selectedTokenIDs.removeAll { $0 == token.id }
        availableTokens.append(token)
    }

    private func grade() {
        guard questions.indices.contains(index) else { return }
        let grading = PracticeGrader.grade(
            question: questions[index],
            response: .ordering(tokenIDs: selectedTokenIDs)
        )
        result = grading
        do {
            for progress in PracticeProgressMapping.descriptors(for: questions[index]) {
                _ = try StudyPersistence.recordAnswer(
                    itemID: progress.itemID,
                    skill: progress.skill,
                    isCorrect: grading.outcome == .correct,
                    in: modelContext
                )
            }
        } catch {
            persistenceError = error.localizedDescription
        }
    }

    private func correctSentence(_ payload: PracticeOrderingQuestion) -> String {
        guard let order = payload.acceptedTokenOrders.first else { return "" }
        let byID = Dictionary(uniqueKeysWithValues: payload.tokens.map { ($0.id, $0.content.text) })
        return order.compactMap { byID[$0] }.joined()
    }

    private var persistenceErrorBinding: Binding<Bool> {
        Binding(
            get: { persistenceError != nil },
            set: { if !$0 { persistenceError = nil } }
        )
    }
}
