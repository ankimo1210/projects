import Foundation
import SwiftData
import SwiftUI

struct FreeResponsePracticeView: View {
    let title: String
    let questions: [PracticeQuestion]

    @EnvironmentObject private var speech: SpeechService
    @Environment(\.modelContext) private var modelContext
    @AppStorage("speechSpeedRawValue") private var speechSpeedRawValue = SpeechSpeed.normal.rawValue
    @State private var index = 0
    @State private var responseText = ""
    @State private var submitted = false
    @State private var criterionScores: [String: Int] = [:]
    @State private var speakingStartedAt: Date?
    @State private var spokenDuration: TimeInterval?
    @State private var persistenceError: String?

    private var speed: SpeechSpeed {
        SpeechSpeed(rawValue: speechSpeedRawValue) ?? .normal
    }

    var body: some View {
        Group {
            if questions.isEmpty {
                ContentUnavailableView("課題がありません", systemImage: "pencil.and.outline")
            } else if index >= questions.count {
                VStack(spacing: 16) {
                    Image(systemName: "checkmark.seal.fill")
                        .font(.system(size: 56)).foregroundStyle(.green)
                    Text("課題完了").font(.title.bold())
                    Button("もう一度") {
                        index = 0
                        reset()
                    }
                    .buttonStyle(.borderedProminent)
                }
            } else if let payload = freeResponsePayload(questions[index]) {
                responseBody(question: questions[index], payload: payload)
            }
        }
        .navigationTitle(title)
        .navigationBarTitleDisplayMode(.inline)
        .onDisappear { speech.stop() }
        .alert("学習記録を保存できません", isPresented: persistenceErrorBinding) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(persistenceError ?? "不明なエラー")
        }
    }

    private func responseBody(
        question: PracticeQuestion,
        payload: PracticeFreeResponseQuestion
    ) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                HStack {
                    Text("\(index + 1) / \(questions.count)")
                        .font(.subheadline.monospacedDigit())
                    ProgressView(value: Double(index + 1), total: Double(questions.count))
                }

                VStack(alignment: .leading, spacing: 10) {
                    Text(kindLabel(question.kind))
                        .font(.caption.bold())
                        .foregroundStyle(.purple)
                    Text(payload.prompt.instruction)
                        .font(.title3.bold())
                    if let stimulus = payload.prompt.stimulus {
                        Text(stimulus.text)
                            .font(.body)
                        if let pinyin = stimulus.pinyin {
                            Text(pinyin).font(.caption).foregroundStyle(.orange)
                        }
                        Button("課題文を聞く", systemImage: "speaker.wave.2.fill") {
                            speech.speak(
                                stimulus.speechText ?? stimulus.text,
                                language: promptLanguage(for: question),
                                speed: speed
                            )
                        }
                        .buttonStyle(.bordered)
                    }
                    if let passage = PracticeSeedContent.passage(id: payload.passageID) {
                        Divider()
                        Text(passage.fullText)
                            .font(.body)
                        Button("本文を聞く", systemImage: "speaker.wave.2.fill") {
                            speech.speak(passage.fullText, speed: speed)
                        }
                        .buttonStyle(.bordered)
                    }
                    constraintLabel(payload.constraints)
                }
                .padding()
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(.purple.opacity(0.08), in: RoundedRectangle(cornerRadius: 16))

                if payload.responseMode == .spoken {
                    spokenTimer(payload.constraints)
                    Text("話した内容のメモ（任意）")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                } else {
                    Text("回答")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                TextEditor(text: $responseText)
                    .frame(minHeight: payload.responseMode == .spoken ? 100 : 220)
                    .padding(8)
                    .background(.secondary.opacity(0.07), in: RoundedRectangle(cornerRadius: 14))
                    .disabled(submitted)
                    .accessibilityLabel(
                        payload.responseMode == .spoken ? "話した内容のメモ" : "回答"
                    )

                HStack {
                    Text("\(responseText.count)字")
                        .font(.caption.monospacedDigit())
                        .foregroundStyle(responseLengthIsValid(payload) ? Color.secondary : Color.orange)
                    Spacer()
                }

                if !submitted {
                    Button("自己評価へ", systemImage: "checkmark.circle") {
                        submitted = true
                        initializeScores(payload.rubric)
                    }
                    .buttonStyle(.borderedProminent)
                    .frame(maxWidth: .infinity)
                    .disabled(!responseIsReady(payload))
                } else {
                    rubricView(payload.rubric)

                    if let reference = payload.referenceAnswer {
                        VStack(alignment: .leading, spacing: 6) {
                            Text("参考回答").font(.headline)
                            Text(reference.text)
                            if let japanese = reference.japanese {
                                Text(japanese).font(.subheadline).foregroundStyle(.secondary)
                            }
                            Button("参考回答を聞く", systemImage: "speaker.wave.2.fill") {
                                speech.speak(
                                    reference.speechText ?? reference.text,
                                    language: referenceLanguage(for: question),
                                    speed: speed
                                )
                            }
                            .buttonStyle(.bordered)
                        }
                        .padding()
                        .background(.green.opacity(0.08), in: RoundedRectangle(cornerRadius: 14))
                    }

                    Button("次へ", systemImage: "arrow.right") {
                        recordSelfAssessment(question: question, payload: payload)
                        index += 1
                        reset()
                    }
                    .buttonStyle(.borderedProminent)
                    .frame(maxWidth: .infinity)
                }
            }
            .padding()
        }
    }

    private func spokenTimer(_ constraints: PracticeResponseConstraints) -> some View {
        HStack {
            if let speakingStartedAt {
                TimelineView(.periodic(from: .now, by: 1)) { context in
                    Text(context.date.timeIntervalSince(speakingStartedAt).formattedDuration)
                        .font(.title2.monospacedDigit())
                }
                Spacer()
                Button("終了") {
                    spokenDuration = Date().timeIntervalSince(speakingStartedAt)
                    self.speakingStartedAt = nil
                }
                    .buttonStyle(.bordered)
            } else {
                VStack(alignment: .leading, spacing: 2) {
                    Label("声に出して回答してください", systemImage: "mic.fill")
                    if let spokenDuration {
                        Text("計測：\(spokenDuration.formattedDuration)")
                            .font(.caption.monospacedDigit())
                            .foregroundStyle(
                                spokenDurationIsValid(spokenDuration, constraints: constraints)
                                    ? Color.green : Color.orange
                            )
                    }
                }
                Spacer()
                Button(spokenDuration == nil ? "計測開始" : "やり直す") {
                    spokenDuration = nil
                    speakingStartedAt = Date()
                }
                    .buttonStyle(.borderedProminent)
            }
        }
        .padding()
        .background(.orange.opacity(0.09), in: RoundedRectangle(cornerRadius: 14))
    }

    private func rubricView(_ rubric: PracticeFreeResponseRubric) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                VStack(alignment: .leading) {
                    Text("自己評価：\(rubric.title)").font(.headline)
                    Text("合計 \(totalScore) / \(rubric.maximumPoints)点")
                        .font(.subheadline.monospacedDigit())
                }
                Spacer()
            }
            ForEach(rubric.criteria) { criterion in
                VStack(alignment: .leading, spacing: 5) {
                    HStack {
                        Text(criterion.title).font(.subheadline.bold())
                        Spacer()
                        Picker(
                            criterion.title,
                            selection: Binding(
                                get: { criterionScores[criterion.id] ?? 0 },
                                set: { criterionScores[criterion.id] = $0 }
                            )
                        ) {
                            ForEach(0...criterion.maximumPoints, id: \.self) { score in
                                Text("\(score)").tag(score)
                            }
                        }
                        .pickerStyle(.menu)
                    }
                    Text(criterion.description)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            Text("この採点は自己評価です。公式試験の得点を保証するものではありません。")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding()
        .background(.secondary.opacity(0.08), in: RoundedRectangle(cornerRadius: 14))
    }

    @ViewBuilder
    private func constraintLabel(_ constraints: PracticeResponseConstraints) -> some View {
        let parts = [
            constraints.minimumCharacters.map { "\($0)字以上" },
            constraints.maximumCharacters.map { "\($0)字以内" },
            constraints.minimumDurationSeconds.map { "\($0)秒以上" },
            constraints.maximumDurationSeconds.map { "\($0)秒以内" }
        ].compactMap { $0 }
        if !parts.isEmpty {
            Label(parts.joined(separator: "・"), systemImage: "timer")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }

    private var totalScore: Int {
        criterionScores.values.reduce(0, +)
    }

    private func initializeScores(_ rubric: PracticeFreeResponseRubric) {
        for criterion in rubric.criteria where criterionScores[criterion.id] == nil {
            criterionScores[criterion.id] = 0
        }
    }

    private func freeResponsePayload(_ question: PracticeQuestion) -> PracticeFreeResponseQuestion? {
        switch question.content {
        case let .summary(payload): payload
        case let .essay(payload): payload
        case let .translation(payload): payload.response
        case let .oralOpinion(payload): payload
        default: nil
        }
    }

    private func kindLabel(_ kind: PracticeQuestionKind) -> String {
        switch kind {
        case .summary: "要約"
        case .essay: "作文"
        case .translation: "翻訳"
        case .oralOpinion: "口頭意見"
        default: "自由回答"
        }
    }

    private func promptLanguage(for question: PracticeQuestion) -> SpeechLanguage {
        guard case let .translation(payload) = question.content else { return .mandarin }
        return payload.direction == .intoChinese ? .japanese : .mandarin
    }

    private func referenceLanguage(for question: PracticeQuestion) -> SpeechLanguage {
        guard case let .translation(payload) = question.content else { return .mandarin }
        return payload.direction == .intoChinese ? .mandarin : .japanese
    }

    private func responseIsReady(_ payload: PracticeFreeResponseQuestion) -> Bool {
        if payload.responseMode == .spoken {
            guard speakingStartedAt == nil, let spokenDuration else { return false }
            return spokenDurationIsValid(spokenDuration, constraints: payload.constraints)
        }
        return !responseText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            && responseLengthIsValid(payload)
    }

    private func spokenDurationIsValid(
        _ duration: TimeInterval,
        constraints: PracticeResponseConstraints
    ) -> Bool {
        if let minimum = constraints.minimumDurationSeconds,
           duration < Double(minimum) { return false }
        if let maximum = constraints.maximumDurationSeconds,
           duration > Double(maximum) { return false }
        return duration > 0
    }

    private func responseLengthIsValid(_ payload: PracticeFreeResponseQuestion) -> Bool {
        if let minimum = payload.constraints.minimumCharacters,
           responseText.count < minimum { return false }
        if let maximum = payload.constraints.maximumCharacters,
           responseText.count > maximum { return false }
        return true
    }

    private func reset() {
        responseText = ""
        submitted = false
        criterionScores = [:]
        speakingStartedAt = nil
        spokenDuration = nil
    }

    private func recordSelfAssessment(
        question: PracticeQuestion,
        payload: PracticeFreeResponseQuestion
    ) {
        let passingPoints = payload.rubric.passingPoints
            ?? Int(ceil(Double(payload.rubric.maximumPoints) * 0.6))
        do {
            for progress in PracticeProgressMapping.descriptors(for: question) {
                _ = try StudyPersistence.recordAnswer(
                    itemID: progress.itemID,
                    skill: progress.skill,
                    isCorrect: totalScore >= passingPoints,
                    in: modelContext,
                    rubricScore: totalScore,
                    rubricMaximumScore: payload.rubric.maximumPoints
                )
            }
        } catch {
            persistenceError = error.localizedDescription
        }
    }

    private var persistenceErrorBinding: Binding<Bool> {
        Binding(
            get: { persistenceError != nil },
            set: { if !$0 { persistenceError = nil } }
        )
    }
}

private extension TimeInterval {
    var formattedDuration: String {
        let seconds = max(0, Int(self))
        return String(format: "%02d:%02d", seconds / 60, seconds % 60)
    }
}
