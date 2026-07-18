import Foundation

nonisolated enum WrittenPracticeTiming {
    static func elapsedSeconds(
        startedAt: Date,
        submittedAt: Date?,
        now: Date
    ) -> Int {
        max(0, Int((submittedAt ?? now).timeIntervalSince(startedAt)))
    }

    static func durationText(_ seconds: Int) -> String {
        let clamped = max(0, seconds)
        return "\(clamped / 60)分\(clamped % 60)秒"
    }
}

nonisolated struct WrittenReviewRubricCriterion: Codable, Equatable, Hashable, Identifiable {
    let id: String
    let criterion: String
    let maximumMarks: Int
    let knowledgeTags: [String]

    @MainActor
    init(item: WrittenRubricItem) {
        id = item.id
        criterion = item.criterion
        maximumMarks = item.marks
        knowledgeTags = item.knowledgeTags
    }

    init(id: String, criterion: String, maximumMarks: Int, knowledgeTags: [String] = []) {
        self.id = id
        self.criterion = criterion
        self.maximumMarks = maximumMarks
        self.knowledgeTags = knowledgeTags
    }
}

nonisolated struct WrittenAnswerReviewRequest: Codable, Equatable {
    static let schemaVersion = 1

    let schemaVersion: Int
    let questionID: String
    let prompt: String
    let candidateAnswer: String
    let modelAnswer: String?
    let rubric: [WrittenReviewRubricCriterion]
    let selfAssessedCriterionIDs: [String]

    init(
        questionID: String,
        prompt: String,
        candidateAnswer: String,
        modelAnswer: String? = nil,
        rubric: [WrittenReviewRubricCriterion],
        selfAssessedCriterionIDs: [String] = []
    ) {
        schemaVersion = Self.schemaVersion
        self.questionID = questionID
        self.prompt = prompt
        self.candidateAnswer = candidateAnswer
        self.modelAnswer = modelAnswer
        self.rubric = rubric
        self.selfAssessedCriterionIDs = selfAssessedCriterionIDs
    }

    var maximumMarks: Int {
        rubric.reduce(0) { $0 + $1.maximumMarks }
    }
}

nonisolated struct WrittenCriterionReview: Codable, Equatable, Identifiable {
    let id: String
    let awardedMarks: Int
    let maximumMarks: Int
    let feedback: String
}

nonisolated enum WrittenReviewMethod: String, Codable, Equatable {
    case localSelfAssessment
    case remoteAI
}

nonisolated struct WrittenAnswerReviewResult: Codable, Equatable {
    let schemaVersion: Int
    let questionID: String
    let method: WrittenReviewMethod
    let awardedMarks: Int
    let maximumMarks: Int
    let criterionReviews: [WrittenCriterionReview]
    let overallFeedback: String
}

nonisolated protocol WrittenAnswerReviewing {
    func review(_ request: WrittenAnswerReviewRequest) async throws -> WrittenAnswerReviewResult
}

nonisolated enum WrittenAnswerReviewError: LocalizedError, Equatable {
    case invalidRequest(String)
    case explicitConsentRequired
    case insecureBackend
    case unsafeRedirect
    case serverRejected(Int)
    case oversizedResponse
    case invalidResponse

    var errorDescription: String? {
        switch self {
        case .invalidRequest(let reason):
            "添削リクエストが不正です（\(reason)）。"
        case .explicitConsentRequired:
            "回答を外部送信するには、送信先を確認して明示的に同意してください。"
        case .insecureBackend:
            "AI添削の送信先には、HTTPSのバックエンドURLだけを指定できます。"
        case .unsafeRedirect:
            "添削リクエストが未承認の送信先へ転送されたため中止しました。"
        case .serverRejected(let status):
            "AI添削バックエンドがリクエストを受け付けませんでした（HTTP \(status)）。"
        case .oversizedResponse:
            "AI添削バックエンドからの応答が大きすぎます。"
        case .invalidResponse:
            "AI添削バックエンドの応答形式を確認できませんでした。"
        }
    }
}

nonisolated struct LocalRubricWrittenAnswerReviewer: WrittenAnswerReviewing {
    func review(_ request: WrittenAnswerReviewRequest) async throws -> WrittenAnswerReviewResult {
        try ReviewValidation.validate(request)
        let selected = Set(request.selfAssessedCriterionIDs)
        let criterionReviews = request.rubric.map { item in
            let isSelected = selected.contains(item.id)
            return WrittenCriterionReview(
                id: item.id,
                awardedMarks: isSelected ? item.maximumMarks : 0,
                maximumMarks: item.maximumMarks,
                feedback: isSelected
                    ? "自己評価で「\(item.criterion)」を満たすと確認しました。"
                    : "モデル解答と照合し、「\(item.criterion)」を回答に明示できるか確認してください。"
            )
        }
        let awardedMarks = criterionReviews.reduce(0) { $0 + $1.awardedMarks }
        return WrittenAnswerReviewResult(
            schemaVersion: WrittenAnswerReviewRequest.schemaVersion,
            questionID: request.questionID,
            method: .localSelfAssessment,
            awardedMarks: awardedMarks,
            maximumMarks: request.maximumMarks,
            criterionReviews: criterionReviews,
            overallFeedback: "これはAIによる意味判定ではなく、rubricに基づく自己評価です。モデル解答と各観点を照合してください。"
        )
    }
}

nonisolated struct AIReviewBackendConfiguration: Codable, Equatable {
    let endpoint: URL

    init(endpoint: URL) throws {
        guard endpoint.scheme?.lowercased() == "https",
              endpoint.host?.isEmpty == false,
              endpoint.user == nil,
              endpoint.password == nil,
              endpoint.query == nil,
              endpoint.fragment == nil
        else {
            throw WrittenAnswerReviewError.insecureBackend
        }
        self.endpoint = endpoint
    }

    init(endpointText: String) throws {
        guard let endpoint = URL(string: endpointText.trimmingCharacters(in: .whitespacesAndNewlines)) else {
            throw WrittenAnswerReviewError.insecureBackend
        }
        try self.init(endpoint: endpoint)
    }

    var consentScope: String {
        endpoint.absoluteString
    }
}

/// Selects an AI review destination without allowing a Release user to supply one.
///
/// Production builds obtain the operator-managed destination from the generated
/// Info.plist. A developer override is accepted only when the caller explicitly
/// enables it (the settings UI does so only under `DEBUG`).
nonisolated enum AIReviewBackendProvisioning {
    static let infoPlistKey = "WSETAIReviewBackendEndpoint"
    static let productionEnabledInfoPlistKey = "WSETAIReviewProductionEnabled"

    static func operatorManagedEndpointText(in bundle: Bundle = .main) -> String? {
        bundle.object(forInfoDictionaryKey: infoPlistKey) as? String
    }

    static func isProductionEnabled(in bundle: Bundle = .main) -> Bool {
        bundle.object(forInfoDictionaryKey: productionEnabledInfoPlistKey) as? Bool == true
    }

    static func configuration(
        operatorManagedEndpointText: String?,
        developerOverrideEndpointText: String?,
        allowsDeveloperOverride: Bool
    ) -> AIReviewBackendConfiguration? {
        let operatorEndpoint = normalized(operatorManagedEndpointText)
        let developerEndpoint = normalized(developerOverrideEndpointText)
        let selectedEndpoint: String?

        if allowsDeveloperOverride, let developerEndpoint {
            selectedEndpoint = developerEndpoint
        } else {
            selectedEndpoint = operatorEndpoint
        }

        guard let selectedEndpoint else { return nil }
        return try? AIReviewBackendConfiguration(endpointText: selectedEndpoint)
    }

    /// Release provisioning fails closed unless the operator separately confirms
    /// that privacy, retention, deletion and security gates have all passed.
    static func releaseConfiguration(
        operatorManagedEndpointText: String?,
        isProductionEnabled: Bool
    ) -> AIReviewBackendConfiguration? {
        guard isProductionEnabled else { return nil }
        return configuration(
            operatorManagedEndpointText: operatorManagedEndpointText,
            developerOverrideEndpointText: nil,
            allowsDeveloperOverride: false
        )
    }

    private static func normalized(_ value: String?) -> String? {
        guard let value else { return nil }
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? nil : trimmed
    }
}

nonisolated struct AIReviewConsentRecord: Codable, Equatable {
    static let currentPolicyVersion = 1

    let policyVersion: Int
    let endpointScope: String
    let grantedAt: Date
}

nonisolated protocol AIReviewConsentProviding {
    func hasValidConsent(for configuration: AIReviewBackendConfiguration) async -> Bool
}

actor UserDefaultsAIReviewConsentStore: AIReviewConsentProviding {
    nonisolated static let storageKey = "r7.aiReview.explicitConsent"

    private let defaults: UserDefaults
    private let storageKey: String

    init(
        defaults: UserDefaults = .standard,
        storageKey: String = UserDefaultsAIReviewConsentStore.storageKey
    ) {
        self.defaults = defaults
        self.storageKey = storageKey
    }

    func grant(for configuration: AIReviewBackendConfiguration, at date: Date = .now) throws {
        let record = AIReviewConsentRecord(
            policyVersion: AIReviewConsentRecord.currentPolicyVersion,
            endpointScope: configuration.consentScope,
            grantedAt: date
        )
        defaults.set(try JSONEncoder().encode(record), forKey: storageKey)
    }

    func revoke() {
        defaults.removeObject(forKey: storageKey)
    }

    func hasValidConsent(for configuration: AIReviewBackendConfiguration) -> Bool {
        guard let data = defaults.data(forKey: storageKey),
              let record = try? JSONDecoder().decode(AIReviewConsentRecord.self, from: data)
        else { return false }
        return record.policyVersion == AIReviewConsentRecord.currentPolicyVersion
            && record.endpointScope == configuration.consentScope
    }
}

nonisolated protocol AIReviewHTTPDataLoading {
    func data(for request: URLRequest) async throws -> (Data, URLResponse)
}

nonisolated final class RejectingAIReviewRedirectDelegate: NSObject, URLSessionTaskDelegate,
    @unchecked Sendable
{
    func urlSession(
        _ session: URLSession,
        task: URLSessionTask,
        willPerformHTTPRedirection response: HTTPURLResponse,
        newRequest request: URLRequest,
        completionHandler: @escaping (URLRequest?) -> Void
    ) {
        // Never resend a candidate answer to a location outside the consented endpoint.
        completionHandler(nil)
    }
}

nonisolated final class EphemeralAIReviewHTTPClient: AIReviewHTTPDataLoading {
    private let session: URLSession

    init() {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.urlCache = nil
        configuration.httpCookieStorage = nil
        configuration.requestCachePolicy = .reloadIgnoringLocalAndRemoteCacheData
        session = URLSession(
            configuration: configuration,
            delegate: RejectingAIReviewRedirectDelegate(),
            delegateQueue: nil
        )
    }

    func data(for request: URLRequest) async throws -> (Data, URLResponse) {
        try await session.data(for: request)
    }
}

nonisolated struct RemoteWrittenAnswerReviewer: WrittenAnswerReviewing {
    static let maximumResponseBytes = 1_000_000

    let configuration: AIReviewBackendConfiguration
    let consentProvider: any AIReviewConsentProviding
    let httpClient: any AIReviewHTTPDataLoading

    init(
        configuration: AIReviewBackendConfiguration,
        consentProvider: any AIReviewConsentProviding,
        httpClient: any AIReviewHTTPDataLoading = EphemeralAIReviewHTTPClient()
    ) {
        self.configuration = configuration
        self.consentProvider = consentProvider
        self.httpClient = httpClient
    }

    func review(_ reviewRequest: WrittenAnswerReviewRequest) async throws -> WrittenAnswerReviewResult {
        try ReviewValidation.validate(reviewRequest)
        guard await consentProvider.hasValidConsent(for: configuration) else {
            throw WrittenAnswerReviewError.explicitConsentRequired
        }

        var request = URLRequest(url: configuration.endpoint)
        request.httpMethod = "POST"
        request.timeoutInterval = 30
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue(String(WrittenAnswerReviewRequest.schemaVersion), forHTTPHeaderField: "X-WSET-Review-Schema")
        request.httpBody = try JSONEncoder().encode(reviewRequest)

        let (data, response) = try await httpClient.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw WrittenAnswerReviewError.invalidResponse
        }
        guard httpResponse.url == configuration.endpoint else {
            throw WrittenAnswerReviewError.unsafeRedirect
        }
        guard !(300..<400).contains(httpResponse.statusCode) else {
            throw WrittenAnswerReviewError.unsafeRedirect
        }
        guard (200..<300).contains(httpResponse.statusCode) else {
            throw WrittenAnswerReviewError.serverRejected(httpResponse.statusCode)
        }
        guard data.count <= Self.maximumResponseBytes else {
            throw WrittenAnswerReviewError.oversizedResponse
        }
        guard let decoded = try? JSONDecoder().decode(WrittenAnswerReviewResult.self, from: data),
              ReviewValidation.isValid(decoded, for: reviewRequest)
        else {
            throw WrittenAnswerReviewError.invalidResponse
        }
        return WrittenAnswerReviewResult(
            schemaVersion: decoded.schemaVersion,
            questionID: decoded.questionID,
            method: .remoteAI,
            awardedMarks: decoded.awardedMarks,
            maximumMarks: decoded.maximumMarks,
            criterionReviews: decoded.criterionReviews,
            overallFeedback: decoded.overallFeedback
        )
    }
}

nonisolated private enum ReviewValidation {
    static func validate(_ request: WrittenAnswerReviewRequest) throws {
        guard request.schemaVersion == WrittenAnswerReviewRequest.schemaVersion,
              !request.questionID.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
              !request.prompt.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
              !request.candidateAnswer.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
              request.candidateAnswer.count <= 20_000,
              !request.rubric.isEmpty
        else {
            throw WrittenAnswerReviewError.invalidRequest("必須項目")
        }

        let rubricIDs = request.rubric.map(\.id)
        guard Set(rubricIDs).count == rubricIDs.count,
              request.rubric.allSatisfy({
                  !$0.id.isEmpty && !$0.criterion.isEmpty && $0.maximumMarks > 0
              }),
              Set(request.selfAssessedCriterionIDs).isSubset(of: Set(rubricIDs))
        else {
            throw WrittenAnswerReviewError.invalidRequest("rubric")
        }
    }

    static func isValid(
        _ result: WrittenAnswerReviewResult,
        for request: WrittenAnswerReviewRequest
    ) -> Bool {
        guard result.schemaVersion == WrittenAnswerReviewRequest.schemaVersion,
              result.questionID == request.questionID,
              result.maximumMarks == request.maximumMarks,
              result.awardedMarks >= 0,
              result.awardedMarks <= result.maximumMarks,
              result.criterionReviews.count == request.rubric.count,
              !result.overallFeedback.isEmpty
        else { return false }

        let rubricByID = Dictionary(uniqueKeysWithValues: request.rubric.map { ($0.id, $0) })
        let reviewIDs = result.criterionReviews.map(\.id)
        guard Set(reviewIDs).count == reviewIDs.count,
              Set(reviewIDs) == Set(rubricByID.keys)
        else { return false }

        let calculatedTotal = result.criterionReviews.reduce(0) { total, item in
            total + item.awardedMarks
        }
        return calculatedTotal == result.awardedMarks
            && result.criterionReviews.allSatisfy { item in
                guard let rubric = rubricByID[item.id] else { return false }
                return item.maximumMarks == rubric.maximumMarks
                    && item.awardedMarks >= 0
                    && item.awardedMarks <= item.maximumMarks
                    && !item.feedback.isEmpty
            }
    }
}
