import SwiftData
import XCTest
@testable import WSET

@MainActor
final class BackupContractTests: XCTestCase {
    func testEmptyBackupRoundTripsWithoutCommercialEntitlement() throws {
        let container = try makeContainer()
        let backup = try BackupService.makeBackup(in: container.mainContext)
        let data = try StudyBackupDocument.encoder.encode(backup)
        let json = try XCTUnwrap(
            JSONSerialization.jsonObject(with: data) as? [String: Any]
        )

        XCTAssertEqual(json["schemaVersion"] as? Int, 1)
        XCTAssertEqual((json["progress"] as? [Any])?.count, 0)
        XCTAssertNil(json["entitlement"])
        XCTAssertNil(json["hasProAccess"])
        XCTAssertFalse(String(decoding: data, as: UTF8.self).contains("pro_lifetime"))

        let decoded = try StudyBackupDocument.decode(data)
        let result = try BackupService.restore(decoded, into: container.mainContext)
        XCTAssertEqual(result.progressCount, 0)
        XCTAssertEqual(result.attemptCount, 0)
        XCTAssertEqual(result.writtenDraftCount, 0)
        XCTAssertEqual(result.tastingCount, 0)
        XCTAssertEqual(result.mockExamCount, 0)
        XCTAssertEqual(result.termProgressCount, 0)
        XCTAssertEqual(result.theoryExamCount, 0)
    }

    func testUnknownBackupSchemaIsRejectedBeforeMutation() throws {
        let container = try makeContainer()
        let unsupported = StudyBackup(
            schemaVersion: 99,
            createdAt: .now,
            progress: [],
            attempts: [],
            writtenDrafts: [],
            tastingNotes: [],
            mockExams: [],
            termProgress: [],
            theoryExams: []
        )

        XCTAssertThrowsError(
            try BackupService.restore(unsupported, into: container.mainContext)
        ) { error in
            guard let backupError = error as? BackupError,
                  case let .unsupportedSchema(version) = backupError
            else {
                return XCTFail("Unexpected error: \(error)")
            }
            XCTAssertEqual(version, 99)
        }
        XCTAssertEqual(
            try container.mainContext.fetchCount(FetchDescriptor<QuestionProgress>()),
            0
        )
    }

    func testLegacyBackupRestoresIntoCurrentFullModelContainer() throws {
        let legacyJSON = """
        {
          "schemaVersion": 1,
          "createdAt": "2026-07-18T00:00:00Z",
          "progress": [{
            "questionID": "legacy-question",
            "isBookmarked": true,
            "attemptCount": 2,
            "correctCount": 1,
            "intervalDays": 1,
            "dueDate": "2026-07-19T00:00:00Z",
            "lastStudiedAt": "2026-07-18T01:00:00Z",
            "lastWasCorrect": false
          }],
          "attempts": [{
            "id": "00000000-0000-0000-0000-000000000002",
            "questionID": "legacy-question",
            "isCorrect": false,
            "rating": 0,
            "studiedAt": "2026-07-18T01:00:00Z"
          }],
          "tastingNotes": [{
            "id": "00000000-0000-0000-0000-000000000001",
            "sampleLabel": "Wine",
            "tastedAt": "2026-07-18T00:00:00Z",
            "wineName": "Legacy",
            "appearanceClarity": "Clear",
            "appearanceIntensity": "Medium",
            "appearanceColour": "Ruby",
            "noseCondition": "Clean",
            "noseIntensity": "Medium",
            "noseDevelopment": "Youthful",
            "aromaNotes": "Cherry",
            "sweetness": "Dry",
            "acidity": "Medium",
            "tannin": "Medium",
            "alcohol": "Medium",
            "body": "Medium",
            "flavourIntensity": "Medium",
            "finish": "Medium",
            "flavourNotes": "Cherry",
            "quality": "Good",
            "readiness": "Can drink now, suitable for ageing",
            "conclusion": "Balanced"
          }],
          "mockExams": []
        }
        """
        let container = try makeContainer()
        let backup = try StudyBackupDocument.decode(Data(legacyJSON.utf8))

        XCTAssertNil(backup.writtenDrafts)
        XCTAssertNil(backup.termProgress)
        XCTAssertNil(backup.theoryExams)

        let result = try BackupService.restore(backup, into: container.mainContext)

        XCTAssertEqual(result.progressCount, 1)
        XCTAssertEqual(result.attemptCount, 1)
        XCTAssertEqual(result.tastingCount, 1)
        XCTAssertEqual(result.writtenDraftCount, 0)
        XCTAssertEqual(result.termProgressCount, 0)
        XCTAssertEqual(result.theoryExamCount, 0)

        let progress = try XCTUnwrap(
            container.mainContext.fetch(FetchDescriptor<QuestionProgress>()).first
        )
        XCTAssertEqual(progress.questionID, "legacy-question")
        XCTAssertTrue(progress.isBookmarked)
        XCTAssertEqual(progress.attemptCount, 2)

        let tasting = try XCTUnwrap(
            container.mainContext.fetch(FetchDescriptor<TastingNote>()).first
        )
        XCTAssertEqual(tasting.id.uuidString, "00000000-0000-0000-0000-000000000001")
        XCTAssertEqual(tasting.wineName, "Legacy")
        XCTAssertNil(tasting.sessionID)
        XCTAssertNil(tasting.examStartedAt)
        XCTAssertNil(tasting.examWasTimeExpired)
    }

    private func makeContainer() throws -> ModelContainer {
        let configuration = ModelConfiguration(isStoredInMemoryOnly: true)
        return try ModelContainer(
            for: StudyQuestion.self,
            QuestionProgress.self,
            StudyAttempt.self,
            WrittenAnswerDraft.self,
            TastingNote.self,
            MockExamSession.self,
            TheoryExamSession.self,
            ReferenceTermProgress.self,
            configurations: configuration
        )
    }
}
