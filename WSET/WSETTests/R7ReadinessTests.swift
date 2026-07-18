import Foundation
import XCTest
@testable import WSET

final class R7ReadinessTests: XCTestCase {
    func testCurrentAppBuildKeepsProductionAIReviewDisabled() {
        XCTAssertNil(AIReviewBackendProvisioning.operatorManagedEndpointText())
        XCTAssertFalse(AIReviewBackendProvisioning.isProductionEnabled())
    }

    func testICloudDiagnosisDoesNotCreateDocumentsDirectory() async throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("wset-r7-\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let service = ICloudManualTransferService(
            locator: TestUbiquityLocator(hasIdentity: true, url: root),
            usesFileCoordination: false
        )
        let diagnostic = await service.diagnose(at: Date(timeIntervalSince1970: 1_700_000_000))

        XCTAssertEqual(diagnostic.status, .available)
        XCTAssertFalse(
            FileManager.default.fileExists(
                atPath: root.appendingPathComponent("Documents", isDirectory: true).path
            )
        )
    }

    func testICloudUploadAndDownloadRequireExplicitMethodsAndPreserveDigest() async throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("wset-r7-\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let service = ICloudManualTransferService(
            locator: TestUbiquityLocator(hasIdentity: true, url: root),
            usesFileCoordination: false
        )
        let source = Data("offline backup".utf8)
        let uploaded = try await service.upload(source, fileName: "wset-backup.json")
        let downloaded = try await service.download(fileName: "wset-backup.json")

        XCTAssertEqual(downloaded.data, source)
        XCTAssertEqual(downloaded.receipt.sha256, uploaded.sha256)
        XCTAssertEqual(uploaded.byteCount, source.count)
    }

    func testICloudTransferRejectsPathTraversalAndSignedOutState() async throws {
        let root = FileManager.default.temporaryDirectory
        let available = ICloudManualTransferService(
            locator: TestUbiquityLocator(hasIdentity: true, url: root),
            usesFileCoordination: false
        )
        do {
            _ = try await available.upload(Data(), fileName: "../outside.json")
            XCTFail("Path traversal must be rejected")
        } catch {
            XCTAssertEqual(error as? ICloudManualTransferError, .invalidFileName)
        }

        let signedOut = ICloudManualTransferService(
            locator: TestUbiquityLocator(hasIdentity: false, url: root),
            usesFileCoordination: false
        )
        let diagnostic = await signedOut.diagnose()
        XCTAssertEqual(diagnostic.status, .signedOut)
        do {
            _ = try await signedOut.download(fileName: "backup.json")
            XCTFail("Signed-out download must fail locally")
        } catch {
            XCTAssertEqual(error as? ICloudManualTransferError, .signedOut)
        }
    }

    func testLocalReviewerAwardsOnlySelfAssessedRubricMarks() async throws {
        let request = makeRequest(selected: ["r1"])
        let result = try await LocalRubricWrittenAnswerReviewer().review(request)

        XCTAssertEqual(result.method, .localSelfAssessment)
        XCTAssertEqual(result.awardedMarks, 2)
        XCTAssertEqual(result.maximumMarks, 3)
        XCTAssertEqual(result.criterionReviews.map(\.awardedMarks), [2, 0])
        XCTAssertTrue(result.overallFeedback.contains("自己評価"))
    }

    func testRemoteReviewerDoesNotTouchNetworkWithoutEndpointScopedConsent() async throws {
        let configuration = try AIReviewBackendConfiguration(
            endpointText: "https://review.example.test/v1/written"
        )
        let client = SpyAIReviewHTTPClient()
        let reviewer = RemoteWrittenAnswerReviewer(
            configuration: configuration,
            consentProvider: FixedConsentProvider(isGranted: false),
            httpClient: client
        )

        do {
            _ = try await reviewer.review(makeRequest(selected: []))
            XCTFail("Consent gate must fail before networking")
        } catch {
            XCTAssertEqual(error as? WrittenAnswerReviewError, .explicitConsentRequired)
        }
        let deniedCallCount = await client.callCount
        XCTAssertEqual(deniedCallCount, 0)
    }

    func testStoredConsentIsBoundToTheExactConfiguredEndpoint() async throws {
        let suiteName = "R7ReadinessTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suiteName))
        defer { defaults.removePersistentDomain(forName: suiteName) }
        let store = UserDefaultsAIReviewConsentStore(
            defaults: defaults,
            storageKey: "consent"
        )
        let consentedEndpoint = try AIReviewBackendConfiguration(
            endpointText: "https://review.example.test/v1/written"
        )
        let differentEndpoint = try AIReviewBackendConfiguration(
            endpointText: "https://other.example.test/v1/written"
        )

        try await store.grant(for: consentedEndpoint)

        let consentedEndpointIsValid = await store.hasValidConsent(for: consentedEndpoint)
        let differentEndpointIsValid = await store.hasValidConsent(for: differentEndpoint)
        XCTAssertTrue(consentedEndpointIsValid)
        XCTAssertFalse(differentEndpointIsValid)
        await store.revoke()
        let revokedEndpointIsValid = await store.hasValidConsent(for: consentedEndpoint)
        XCTAssertFalse(revokedEndpointIsValid)
    }

    func testRemoteReviewerAcceptsValidatedRubricResponseAfterConsent() async throws {
        let configuration = try AIReviewBackendConfiguration(
            endpointText: "https://review.example.test/v1/written"
        )
        let response = WrittenAnswerReviewResult(
            schemaVersion: 1,
            questionID: "SAQ-TEST",
            method: .remoteAI,
            awardedMarks: 2,
            maximumMarks: 3,
            criterionReviews: [
                WrittenCriterionReview(id: "r1", awardedMarks: 2, maximumMarks: 2, feedback: "根拠あり"),
                WrittenCriterionReview(id: "r2", awardedMarks: 0, maximumMarks: 1, feedback: "比較を追加"),
            ],
            overallFeedback: "rubricの2点を満たしています。"
        )
        let client = SpyAIReviewHTTPClient(
            data: try JSONEncoder().encode(response),
            response: HTTPURLResponse(
                url: configuration.endpoint,
                statusCode: 200,
                httpVersion: nil,
                headerFields: ["Content-Type": "application/json"]
            )!
        )
        let reviewer = RemoteWrittenAnswerReviewer(
            configuration: configuration,
            consentProvider: FixedConsentProvider(isGranted: true),
            httpClient: client
        )

        let result = try await reviewer.review(makeRequest(selected: []))

        XCTAssertEqual(result.method, .remoteAI)
        XCTAssertEqual(result.awardedMarks, 2)
        let acceptedCallCount = await client.callCount
        XCTAssertEqual(acceptedCallCount, 1)
        let sentRequest = await client.lastRequest
        XCTAssertEqual(sentRequest?.url, configuration.endpoint)
        XCTAssertNil(sentRequest?.value(forHTTPHeaderField: "Authorization"))
        XCTAssertEqual(sentRequest?.timeoutInterval, 30)
        let requestBody = try XCTUnwrap(sentRequest?.httpBody)
        let requestObject = try XCTUnwrap(
            JSONSerialization.jsonObject(with: requestBody) as? [String: Any]
        )
        XCTAssertEqual(
            Set(requestObject.keys),
            [
                "schemaVersion", "questionID", "prompt", "candidateAnswer",
                "modelAnswer", "rubric", "selfAssessedCriterionIDs",
            ]
        )
        XCTAssertNil(requestObject["studyHistory"])
        XCTAssertNil(requestObject["deviceIdentifier"])
        XCTAssertNil(requestObject["userIdentifier"])
    }

    func testRemoteReviewerRejectsResponseAboveOneMegabyte() async throws {
        let configuration = try AIReviewBackendConfiguration(
            endpointText: "https://review.example.test/v1/written"
        )
        let client = SpyAIReviewHTTPClient(
            data: Data(repeating: 0, count: RemoteWrittenAnswerReviewer.maximumResponseBytes + 1),
            response: try XCTUnwrap(
                HTTPURLResponse(
                    url: configuration.endpoint,
                    statusCode: 200,
                    httpVersion: nil,
                    headerFields: ["Content-Type": "application/json"]
                )
            )
        )
        let reviewer = RemoteWrittenAnswerReviewer(
            configuration: configuration,
            consentProvider: FixedConsentProvider(isGranted: true),
            httpClient: client
        )

        do {
            _ = try await reviewer.review(makeRequest(selected: []))
            XCTFail("Responses above the documented limit must be rejected")
        } catch {
            XCTAssertEqual(error as? WrittenAnswerReviewError, .oversizedResponse)
        }
    }

    func testRemoteReviewerRejectsMalformedRubricResult() async throws {
        let configuration = try AIReviewBackendConfiguration(
            endpointText: "https://review.example.test/v1/written"
        )
        let client = SpyAIReviewHTTPClient(
            data: Data("{\"schemaVersion\":1,\"questionID\":\"wrong\"}".utf8),
            response: try XCTUnwrap(
                HTTPURLResponse(
                    url: configuration.endpoint,
                    statusCode: 200,
                    httpVersion: nil,
                    headerFields: ["Content-Type": "application/json"]
                )
            )
        )
        let reviewer = RemoteWrittenAnswerReviewer(
            configuration: configuration,
            consentProvider: FixedConsentProvider(isGranted: true),
            httpClient: client
        )

        do {
            _ = try await reviewer.review(makeRequest(selected: []))
            XCTFail("Malformed rubric results must not be displayed")
        } catch {
            XCTAssertEqual(error as? WrittenAnswerReviewError, .invalidResponse)
        }
    }

    func testRemoteReviewerRejectsAResponseFromRedirectedURL() async throws {
        let configuration = try AIReviewBackendConfiguration(
            endpointText: "https://review.example.test/v1/written"
        )
        let result = WrittenAnswerReviewResult(
            schemaVersion: 1,
            questionID: "SAQ-TEST",
            method: .remoteAI,
            awardedMarks: 0,
            maximumMarks: 3,
            criterionReviews: [
                WrittenCriterionReview(id: "r1", awardedMarks: 0, maximumMarks: 2, feedback: "不足"),
                WrittenCriterionReview(id: "r2", awardedMarks: 0, maximumMarks: 1, feedback: "不足"),
            ],
            overallFeedback: "改善してください。"
        )
        let redirectedURL = try XCTUnwrap(URL(string: "https://review.example.test/redirected"))
        let client = SpyAIReviewHTTPClient(
            data: try JSONEncoder().encode(result),
            response: try XCTUnwrap(
                HTTPURLResponse(
                    url: redirectedURL,
                    statusCode: 200,
                    httpVersion: nil,
                    headerFields: nil
                )
            )
        )
        let reviewer = RemoteWrittenAnswerReviewer(
            configuration: configuration,
            consentProvider: FixedConsentProvider(isGranted: true),
            httpClient: client
        )

        do {
            _ = try await reviewer.review(makeRequest(selected: []))
            XCTFail("Redirected destinations must not receive review data")
        } catch {
            XCTAssertEqual(error as? WrittenAnswerReviewError, .unsafeRedirect)
        }
    }

    func testHTTPClientDelegateStopsRedirectBeforeAnswerIsResent() throws {
        let originalURL = try XCTUnwrap(URL(string: "https://review.example.test/v1/written"))
        let redirectedURL = try XCTUnwrap(URL(string: "https://other.example.test/collect"))
        let response = try XCTUnwrap(
            HTTPURLResponse(
                url: originalURL,
                statusCode: 307,
                httpVersion: nil,
                headerFields: ["Location": redirectedURL.absoluteString]
            )
        )
        let redirectedRequest = URLRequest(url: redirectedURL)
        let task = URLSession.shared.dataTask(with: originalURL)
        let delegate = RejectingAIReviewRedirectDelegate()
        let expectation = expectation(description: "redirect decision")

        delegate.urlSession(
            URLSession.shared,
            task: task,
            willPerformHTTPRedirection: response,
            newRequest: redirectedRequest
        ) { acceptedRequest in
            XCTAssertNil(acceptedRequest)
            expectation.fulfill()
        }

        wait(for: [expectation], timeout: 1)
    }

    func testRemoteReviewerClassifiesBlockedRedirectResponseAsUnsafe() async throws {
        let configuration = try AIReviewBackendConfiguration(
            endpointText: "https://review.example.test/v1/written"
        )
        let client = SpyAIReviewHTTPClient(
            response: try XCTUnwrap(
                HTTPURLResponse(
                    url: configuration.endpoint,
                    statusCode: 307,
                    httpVersion: nil,
                    headerFields: ["Location": "https://other.example.test/collect"]
                )
            )
        )
        let reviewer = RemoteWrittenAnswerReviewer(
            configuration: configuration,
            consentProvider: FixedConsentProvider(isGranted: true),
            httpClient: client
        )

        do {
            _ = try await reviewer.review(makeRequest(selected: []))
            XCTFail("Redirect responses must remain at the consented endpoint")
        } catch {
            XCTAssertEqual(error as? WrittenAnswerReviewError, .unsafeRedirect)
        }
    }

    func testBackendRequiresHTTPSAndRejectsCredentialsOrQuerySecrets() {
        XCTAssertThrowsError(try AIReviewBackendConfiguration(endpointText: "http://example.test/review"))
        XCTAssertThrowsError(try AIReviewBackendConfiguration(endpointText: "https://user:secret@example.test/review"))
        XCTAssertThrowsError(try AIReviewBackendConfiguration(endpointText: "https://example.test/review?api_key=secret"))
        XCTAssertNoThrow(try AIReviewBackendConfiguration(endpointText: "https://example.test/review"))
    }

    func testReleaseProvisioningIgnoresDeveloperEnteredEndpoint() throws {
        let withoutOperatorEndpoint = AIReviewBackendProvisioning.configuration(
            operatorManagedEndpointText: nil,
            developerOverrideEndpointText: "https://untrusted.example.test/review",
            allowsDeveloperOverride: false
        )
        XCTAssertNil(withoutOperatorEndpoint)

        let operatorEndpoint = AIReviewBackendProvisioning.configuration(
            operatorManagedEndpointText: "https://operator.example.test/v1/written",
            developerOverrideEndpointText: "https://untrusted.example.test/review",
            allowsDeveloperOverride: false
        )
        XCTAssertEqual(
            try XCTUnwrap(operatorEndpoint).endpoint.absoluteString,
            "https://operator.example.test/v1/written"
        )
    }

    func testReleaseBackendFailsClosedUntilProductionReadinessIsExplicitlyEnabled() throws {
        let endpoint = "https://operator.example.test/v1/written"

        XCTAssertNil(
            AIReviewBackendProvisioning.releaseConfiguration(
                operatorManagedEndpointText: endpoint,
                isProductionEnabled: false
            )
        )
        XCTAssertEqual(
            try XCTUnwrap(
                AIReviewBackendProvisioning.releaseConfiguration(
                    operatorManagedEndpointText: endpoint,
                    isProductionEnabled: true
                )
            ).endpoint.absoluteString,
            endpoint
        )
        XCTAssertNil(
            AIReviewBackendProvisioning.releaseConfiguration(
                operatorManagedEndpointText: "http://operator.example.test/review",
                isProductionEnabled: true
            )
        )
    }

    func testDeveloperOverrideIsAvailableOnlyWhenExplicitlyEnabled() throws {
        let configuration = AIReviewBackendProvisioning.configuration(
            operatorManagedEndpointText: "https://operator.example.test/v1/written",
            developerOverrideEndpointText: "https://developer.example.test/mock",
            allowsDeveloperOverride: true
        )

        XCTAssertEqual(
            try XCTUnwrap(configuration).endpoint.absoluteString,
            "https://developer.example.test/mock"
        )
    }

    private func makeRequest(selected: [String]) -> WrittenAnswerReviewRequest {
        WrittenAnswerReviewRequest(
            questionID: "SAQ-TEST",
            prompt: "自然条件とスタイルの関係を説明してください。",
            candidateAnswer: "冷涼な気候は酸を保つ。",
            modelAnswer: "冷涼な気候では酸が保持されやすい。",
            rubric: [
                WrittenReviewRubricCriterion(id: "r1", criterion: "酸の保持を説明", maximumMarks: 2),
                WrittenReviewRubricCriterion(id: "r2", criterion: "香りを比較", maximumMarks: 1),
            ],
            selfAssessedCriterionIDs: selected
        )
    }
}

private struct TestUbiquityLocator: UbiquityContainerLocating {
    let hasIdentity: Bool
    let url: URL?

    var hasUbiquityIdentity: Bool { hasIdentity }

    func containerURL(identifier: String?) -> URL? {
        url
    }
}

private struct FixedConsentProvider: AIReviewConsentProviding {
    let isGranted: Bool

    func hasValidConsent(for configuration: AIReviewBackendConfiguration) async -> Bool {
        isGranted
    }
}

private actor SpyAIReviewHTTPClient: AIReviewHTTPDataLoading {
    private(set) var callCount = 0
    private(set) var lastRequest: URLRequest?
    let data: Data
    let response: URLResponse

    init(
        data: Data = Data(),
        response: URLResponse = URLResponse(
            url: URL(string: "https://review.example.test/v1/written")!,
            mimeType: "application/json",
            expectedContentLength: 0,
            textEncodingName: nil
        )
    ) {
        self.data = data
        self.response = response
    }

    func data(for request: URLRequest) async throws -> (Data, URLResponse) {
        callCount += 1
        lastRequest = request
        return (data, response)
    }
}
