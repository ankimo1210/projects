import SwiftData
import SwiftUI
import UIKit

struct ChoicePracticeView: View {
    let title: String
    let questions: [PracticeQuestion]

    @EnvironmentObject private var speech: SpeechService
    @Environment(\.modelContext) private var modelContext
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize
    @AppStorage("speechSpeedRawValue") private var speechSpeedRawValue = SpeechSpeed.normal.rawValue
    @State private var index = 0
    @State private var selectedOptionID: String?
    @State private var result: PracticeGradingResult?
    @State private var correctionText = ""
    @State private var correctionSubmitted = false
    @State private var correctionIsCorrect: Bool?
    @State private var persistenceError: String?

    private var speed: SpeechSpeed {
        SpeechSpeed(rawValue: speechSpeedRawValue) ?? .normal
    }

    var body: some View {
        Group {
            if questions.isEmpty {
                ContentUnavailableView("問題がありません", systemImage: "square.and.pencil")
            } else if index >= questions.count {
                VStack(spacing: 16) {
                    Image(systemName: "checkmark.seal.fill")
                        .font(.system(size: 56))
                        .foregroundStyle(.green)
                    Text("練習完了").font(.title.bold())
                    Text("\(questions.count)問に取り組みました。")
                    Button("もう一度") {
                        index = 0
                        resetAnswer()
                    }
                    .buttonStyle(.borderedProminent)
                }
            } else {
                questionBody(questions[index])
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

    private func questionBody(_ question: PracticeQuestion) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                HStack {
                    Text("\(index + 1) / \(questions.count)")
                        .font(.subheadline.monospacedDigit())
                    ProgressView(value: Double(index + 1), total: Double(questions.count))
                }

                promptView(question)
                    .frame(maxWidth: .infinity, minHeight: 132)
                    .padding()
                    .background(.purple.opacity(0.08), in: RoundedRectangle(cornerRadius: 18))

                ForEach(options(for: question)) { option in
                    optionButton(option, question: question)
                }

                correctionSection(for: question)

                VStack(alignment: .leading, spacing: 8) {
                    if let outcome = displayedOutcome(for: question) {
                        Label(
                            outcome == .correct ? "正解" : "不正解",
                            systemImage: outcome == .correct
                                ? "checkmark.circle.fill" : "xmark.circle.fill"
                        )
                        .font(.headline)
                        .foregroundStyle(outcome == .correct ? .green : .red)
                    } else if result?.outcome == .correct, requiresCorrection(question) {
                        Label("誤文を特定しました", systemImage: "pencil.circle.fill")
                            .font(.headline)
                            .foregroundStyle(.orange)
                    } else {
                        Text("選択肢から回答してください。")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                    if let explanation = question.explanation {
                        Text(showsExplanation(for: question) ? explanation.summary : " \n ")
                            .font(.subheadline)
                            .lineLimit(dynamicTypeSize.isAccessibilitySize ? nil : 2)
                            .accessibilityHidden(!showsExplanation(for: question))
                    }
                }
                .padding()
                .frame(
                    maxWidth: .infinity,
                    minHeight: 112,
                    maxHeight: dynamicTypeSize.isAccessibilitySize ? nil : 112,
                    alignment: .leading
                )
                .background(.secondary.opacity(0.08), in: RoundedRectangle(cornerRadius: 14))

                Button {
                    index += 1
                    resetAnswer()
                } label: {
                    Label("次へ", systemImage: "arrow.right")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .accessibilityLabel("次の問題へ")
                .disabled(
                    result == nil
                        || requiresPendingCorrection(question)
                )
            }
            .padding()
        }
    }

    @ViewBuilder
    private func promptView(_ question: PracticeQuestion) -> some View {
        switch question.content {
        case let .sentenceCloze(payload):
            VStack(spacing: 10) {
                Text(payload.prompt.instruction).font(.subheadline).foregroundStyle(.secondary)
                Text(payload.sentence.text.replacingOccurrences(of: payload.placeholder, with: "＿＿＿"))
                    .font(.title2.bold())
                    .multilineTextAlignment(.center)
                if let japanese = payload.sentence.japanese {
                    Text(result == nil ? " " : japanese)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                        .accessibilityHidden(result == nil)
                }
                Button {
                    speech.speak(payload.sentence.speechText ?? payload.sentence.text, speed: speed)
                } label: {
                    Label(
                        result == nil ? "回答後に文を聞く" : "文を聞く",
                        systemImage: "speaker.wave.2.fill"
                    )
                }
                .buttonStyle(.bordered)
                .controlSize(.small)
                .disabled(result == nil)
            }
            .frame(maxWidth: .infinity)

        case let .audioToMeaning(payload):
            VStack(spacing: 12) {
                Text(payload.prompt.instruction).font(.subheadline).foregroundStyle(.secondary)
                Button {
                    speech.speak(payload.audio.speechText ?? payload.audio.text, speed: speed)
                } label: {
                    Image(systemName: "speaker.wave.3.fill")
                        .font(.system(size: 38))
                        .frame(width: 82, height: 58)
                }
                .buttonStyle(.borderedProminent)
                if result != nil {
                    Text("\(payload.audio.text)  \(payload.audio.pinyin ?? "")")
                        .font(.headline)
                }
            }
            .frame(maxWidth: .infinity)

        case let .incorrectSentence(payload):
            Text(payload.prompt.instruction)
                .font(.title3.bold())
                .frame(maxWidth: .infinity, alignment: .center)

        case let .readingComprehension(payload):
            VStack(alignment: .leading, spacing: 8) {
                if let passage = PracticeSeedContent.passage(id: payload.passageID) {
                    Text(passage.fullText)
                        .font(.body)
                    Button("本文を聞く", systemImage: "speaker.wave.2.fill") {
                        speech.speak(passage.fullText, speed: speed)
                    }
                    .buttonStyle(.bordered)
                    Divider()
                }
                Text(payload.prompt.instruction).font(.title3.bold())
                if let stimulus = payload.prompt.stimulus {
                    Text(stimulus.text)
                }
            }
            .frame(maxWidth: .infinity)

        default:
            Text("選択式問題")
                .font(.title3.bold())
                .frame(maxWidth: .infinity, alignment: .center)
        }
    }

    private func options(for question: PracticeQuestion) -> [PracticeAnswerOption] {
        switch question.content {
        case let .vocabularyMultipleChoice(payload): payload.answers.options
        case let .audioToMeaning(payload): payload.answers.options
        case let .sentenceCloze(payload): payload.answers.options
        case let .readingComprehension(payload): payload.answers.options
        case let .incorrectSentence(payload): payload.answers.options
        default: []
        }
    }

    private func optionButton(
        _ option: PracticeAnswerOption,
        question: PracticeQuestion
    ) -> some View {
        let expected = expectedOptionIDs(for: question)
        let isCorrect = expected.contains(option.id)
        let isSelected = selectedOptionID == option.id
        return Button {
            guard result == nil else { return }
            selectedOptionID = option.id
            let grading = PracticeGrader.grade(
                question: question,
                response: .choice(optionIDs: [option.id])
            )
            result = grading
            UIAccessibility.post(
                notification: .announcement,
                argument: requiresCorrection(question) && grading.outcome == .correct
                    ? "誤文を特定しました。訂正文を入力してください"
                    : grading.outcome == .correct ? "正解" : "不正解"
            )
            if !requiresCorrection(question) || grading.outcome != .correct {
                recordProgress(
                    for: question,
                    isCorrect: grading.outcome == .correct
                )
            }
        } label: {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text(option.content.text).font(.body.weight(.medium)).foregroundStyle(.primary)
                    if hasSupplementaryText(option) {
                        Text(result == nil ? " " : option.content.pinyin ?? " ")
                            .font(.caption)
                            .foregroundStyle(.orange)
                            .lineLimit(1)
                            .minimumScaleFactor(0.75)
                        Text(result == nil ? " " : supplementaryMeaning(option) ?? " ")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .lineLimit(1)
                            .minimumScaleFactor(0.75)
                    }
                }
                Spacer()
                if result != nil, isCorrect {
                    Image(systemName: "checkmark.circle.fill").foregroundStyle(.green)
                } else if isSelected {
                    Image(systemName: "xmark.circle.fill").foregroundStyle(.red)
                }
            }
            .padding(.horizontal, 14)
            .frame(maxWidth: .infinity, minHeight: 60)
            .background(
                result != nil && isCorrect ? Color.green.opacity(0.12)
                    : isSelected && result != nil ? Color.red.opacity(0.1)
                    : Color.secondary.opacity(0.07),
                in: RoundedRectangle(cornerRadius: 14)
            )
        }
        .buttonStyle(.plain)
        .allowsHitTesting(result == nil)
        .accessibilityLabel(accessibilityLabel(for: option))
        .accessibilityValue(accessibilityValue(
            isCorrect: isCorrect,
            isSelected: isSelected
        ))
    }

    private func hasSupplementaryText(_ option: PracticeAnswerOption) -> Bool {
        option.content.pinyin != nil || supplementaryMeaning(option) != nil
    }

    private func supplementaryMeaning(_ option: PracticeAnswerOption) -> String? {
        guard let japanese = option.content.japanese,
              japanese != option.content.text else { return nil }
        return japanese
    }

    private func accessibilityLabel(for option: PracticeAnswerOption) -> String {
        var components = [option.content.text]
        if result != nil, let pinyin = option.content.pinyin {
            components.append(pinyin)
        }
        if result != nil, let meaning = supplementaryMeaning(option) {
            components.append(meaning)
        }
        return components.joined(separator: "、")
    }

    private func accessibilityValue(isCorrect: Bool, isSelected: Bool) -> String {
        guard result != nil else { return "" }
        if isCorrect { return "正解" }
        if isSelected { return "選択した不正解" }
        return "不正解の選択肢"
    }

    private func expectedOptionIDs(for question: PracticeQuestion) -> [String] {
        switch question.content {
        case let .vocabularyMultipleChoice(payload): payload.answers.correctOptionIDs
        case let .audioToMeaning(payload): payload.answers.correctOptionIDs
        case let .sentenceCloze(payload): payload.answers.correctOptionIDs
        case let .readingComprehension(payload): payload.answers.correctOptionIDs
        case let .incorrectSentence(payload): payload.answers.correctOptionIDs
        default: []
        }
    }

    @ViewBuilder
    private func correctionSection(for question: PracticeQuestion) -> some View {
        if case let .incorrectSentence(payload) = question.content,
           !payload.acceptedCorrections.isEmpty,
           result?.outcome == .correct {
            VStack(alignment: .leading, spacing: 8) {
                Text("訂正文を入力")
                    .font(.headline)
                TextEditor(text: $correctionText)
                    .frame(minHeight: 88)
                    .padding(8)
                    .background(.secondary.opacity(0.07), in: RoundedRectangle(cornerRadius: 12))
                    .disabled(correctionSubmitted)
                    .accessibilityLabel("自然な形に直した文")

                if let correctionIsCorrect {
                    Label(
                        correctionIsCorrect ? "訂正も正解です" : "訂正例を確認してください",
                        systemImage: correctionIsCorrect
                            ? "checkmark.circle.fill" : "exclamationmark.circle.fill"
                    )
                    .foregroundStyle(correctionIsCorrect ? .green : .orange)
                    if !correctionIsCorrect, let example = payload.acceptedCorrections.first {
                        Text("訂正例：\(example)")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                } else {
                    Button("訂正を採点", systemImage: "checkmark.circle") {
                        submitCorrection(question: question, payload: payload)
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(
                        correctionText.trimmingCharacters(
                            in: .whitespacesAndNewlines
                        ).isEmpty
                    )
                }
            }
            .padding()
            .background(.orange.opacity(0.08), in: RoundedRectangle(cornerRadius: 14))
        }
    }

    private func submitCorrection(
        question: PracticeQuestion,
        payload: PracticeIncorrectSentenceQuestion
    ) {
        guard let result, result.outcome == .correct else { return }
        let response = normalizedCorrection(correctionText)
        let isCorrectionCorrect = payload.acceptedCorrections.contains {
            normalizedCorrection($0) == response
        }
        correctionSubmitted = true
        correctionIsCorrect = isCorrectionCorrect
        recordProgress(
            for: question,
            isCorrect: result.outcome == .correct && isCorrectionCorrect
        )
        UIAccessibility.post(
            notification: .announcement,
            argument: isCorrectionCorrect ? "訂正も正解です" : "訂正例を確認してください"
        )
    }

    private func normalizedCorrection(_ value: String) -> String {
        let ignored = CharacterSet.whitespacesAndNewlines
            .union(.punctuationCharacters)
        return String(value.unicodeScalars.filter { !ignored.contains($0) })
    }

    private func requiresCorrection(_ question: PracticeQuestion) -> Bool {
        guard case let .incorrectSentence(payload) = question.content else {
            return false
        }
        return !payload.acceptedCorrections.isEmpty
    }

    private func requiresPendingCorrection(_ question: PracticeQuestion) -> Bool {
        requiresCorrection(question)
            && result?.outcome == .correct
            && !correctionSubmitted
    }

    private func displayedOutcome(
        for question: PracticeQuestion
    ) -> PracticeGradingOutcome? {
        guard let result else { return nil }
        guard requiresCorrection(question), result.outcome == .correct else {
            return result.outcome
        }
        guard correctionSubmitted else { return nil }
        return correctionIsCorrect == true ? .correct : .incorrect
    }

    private func showsExplanation(for question: PracticeQuestion) -> Bool {
        guard let result else { return false }
        return !requiresCorrection(question)
            || result.outcome != .correct
            || correctionSubmitted
    }

    private func recordProgress(for question: PracticeQuestion, isCorrect: Bool) {
        do {
            for progress in PracticeProgressMapping.descriptors(for: question) {
                _ = try StudyPersistence.recordAnswer(
                    itemID: progress.itemID,
                    skill: progress.skill,
                    isCorrect: isCorrect,
                    in: modelContext
                )
            }
        } catch {
            persistenceError = error.localizedDescription
        }
    }

    private func resetAnswer() {
        selectedOptionID = nil
        result = nil
        correctionText = ""
        correctionSubmitted = false
        correctionIsCorrect = nil
    }

    private var persistenceErrorBinding: Binding<Bool> {
        Binding(
            get: { persistenceError != nil },
            set: { if !$0 { persistenceError = nil } }
        )
    }
}
