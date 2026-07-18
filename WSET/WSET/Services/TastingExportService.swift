import Foundation
import SwiftUI
import UniformTypeIdentifiers

enum TastingExportFormat: String, CaseIterable, Identifiable {
    case json
    case csv

    var id: String { rawValue }

    var label: String { rawValue.uppercased() }

    var contentType: UTType {
        switch self {
        case .json: .json
        case .csv: .commaSeparatedText
        }
    }
}

struct TastingNoteExportSnapshot: Codable, Equatable {
    let schemaVersion: Int
    let id: UUID
    let sessionID: UUID?
    let sampleLabel: String
    let tastedAt: Date
    let wineName: String
    let appearanceClarity: String
    let appearanceIntensity: String
    let appearanceColour: String
    let noseCondition: String
    let noseIntensity: String
    let noseDevelopment: String
    let aromaNotes: String
    let sweetness: String
    let acidity: String
    let tannin: String
    let alcohol: String
    let body: String
    let flavourIntensity: String
    let finish: String
    let flavourNotes: String
    let quality: String
    let readiness: String
    let conclusion: String
    let examStartedAt: Date?
    let examSubmittedAt: Date?
    let examDurationSeconds: Int?
    let examWasTimeExpired: Bool?
    let examCompletionPercent: Double?

    init(note: TastingNote) {
        schemaVersion = 1
        id = note.id
        sessionID = note.sessionID
        sampleLabel = note.sampleLabel
        tastedAt = note.tastedAt
        wineName = note.wineName
        appearanceClarity = note.appearanceClarity
        appearanceIntensity = note.appearanceIntensity
        appearanceColour = note.appearanceColour
        noseCondition = note.noseCondition
        noseIntensity = note.noseIntensity
        noseDevelopment = note.noseDevelopment
        aromaNotes = note.aromaNotes
        sweetness = note.sweetness
        acidity = note.acidity
        tannin = note.tannin
        alcohol = note.alcohol
        body = note.body
        flavourIntensity = note.flavourIntensity
        finish = note.finish
        flavourNotes = note.flavourNotes
        quality = note.quality
        readiness = note.readiness
        conclusion = note.conclusion
        examStartedAt = note.examStartedAt
        examSubmittedAt = note.examSubmittedAt
        examDurationSeconds = note.examDurationSeconds
        examWasTimeExpired = note.examWasTimeExpired
        examCompletionPercent = note.examCompletionPercent
    }
}

enum TastingExportService {
    static func data(
        for snapshot: TastingNoteExportSnapshot,
        format: TastingExportFormat
    ) throws -> Data {
        switch format {
        case .json:
            return try jsonEncoder.encode(snapshot)
        case .csv:
            let headers = csvColumns.map(\.header)
            let values = csvColumns.map { $0.value(snapshot) }
            let body = [headers, values]
                .map { row in
                    row.map { csvEscape($0) }.joined(separator: ",")
                }
                .joined(separator: "\r\n")
            return Data(("\u{FEFF}" + body + "\r\n").utf8)
        }
    }

    static func safeFilename(for snapshot: TastingNoteExportSnapshot) -> String {
        let source = snapshot.wineName.isEmpty
            ? SATDisplayText.japanese(snapshot.sampleLabel)
            : snapshot.wineName
        let invalid = CharacterSet.alphanumerics
            .union(CharacterSet(charactersIn: "-_"))
            .inverted
        let sanitized = source
            .components(separatedBy: invalid)
            .filter { !$0.isEmpty }
            .joined(separator: "-")
        let date = filenameDateFormatter.string(from: snapshot.tastedAt)
        return "WSET-Tasting-\(sanitized.isEmpty ? "Note" : sanitized)-\(date)"
    }

    private static let jsonEncoder: JSONEncoder = {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        return encoder
    }()

    private static func csvEscape(_ value: String) -> String {
        guard value.contains(",") || value.contains("\"")
            || value.contains("\n") || value.contains("\r")
        else { return value }
        return "\"\(value.replacingOccurrences(of: "\"", with: "\"\""))\""
    }

    private struct CSVColumn {
        let header: String
        let value: (TastingNoteExportSnapshot) -> String
    }

    private static let csvColumns: [CSVColumn] = [
        CSVColumn(header: "id", value: { $0.id.uuidString }),
        CSVColumn(header: "session_id", value: { $0.sessionID?.uuidString ?? "" }),
        CSVColumn(header: "sample", value: { SATDisplayText.japanese($0.sampleLabel) }),
        CSVColumn(header: "tasted_at", value: { iso8601.string(from: $0.tastedAt) }),
        CSVColumn(header: "wine_name", value: { $0.wineName }),
        CSVColumn(header: "appearance_clarity", value: { SATDisplayText.japanese($0.appearanceClarity) }),
        CSVColumn(header: "appearance_intensity", value: { SATDisplayText.japanese($0.appearanceIntensity) }),
        CSVColumn(header: "appearance_colour", value: { $0.appearanceColour }),
        CSVColumn(header: "nose_condition", value: { SATDisplayText.japanese($0.noseCondition) }),
        CSVColumn(header: "nose_intensity", value: { SATDisplayText.japanese($0.noseIntensity) }),
        CSVColumn(header: "nose_development", value: { SATDisplayText.japanese($0.noseDevelopment) }),
        CSVColumn(header: "aroma_notes", value: { $0.aromaNotes }),
        CSVColumn(header: "sweetness", value: { SATDisplayText.japanese($0.sweetness) }),
        CSVColumn(header: "acidity", value: { SATDisplayText.japanese($0.acidity) }),
        CSVColumn(header: "tannin", value: { SATDisplayText.japanese($0.tannin) }),
        CSVColumn(header: "alcohol", value: { SATDisplayText.japanese($0.alcohol) }),
        CSVColumn(header: "body", value: { SATDisplayText.japanese($0.body) }),
        CSVColumn(header: "flavour_intensity", value: { SATDisplayText.japanese($0.flavourIntensity) }),
        CSVColumn(header: "finish", value: { SATDisplayText.japanese($0.finish) }),
        CSVColumn(header: "flavour_notes", value: { $0.flavourNotes }),
        CSVColumn(header: "quality", value: { SATDisplayText.japanese($0.quality) }),
        CSVColumn(header: "readiness", value: { SATDisplayText.japanese($0.readiness) }),
        CSVColumn(header: "conclusion", value: { $0.conclusion }),
        CSVColumn(
            header: "exam_started_at",
            value: { $0.examStartedAt.map { iso8601.string(from: $0) } ?? "" }
        ),
        CSVColumn(
            header: "exam_submitted_at",
            value: { $0.examSubmittedAt.map { iso8601.string(from: $0) } ?? "" }
        ),
        CSVColumn(header: "exam_duration_seconds", value: { $0.examDurationSeconds.map(String.init) ?? "" }),
        CSVColumn(header: "exam_time_expired", value: { $0.examWasTimeExpired.map(String.init) ?? "" }),
        CSVColumn(
            header: "exam_completion_percent",
            value: { $0.examCompletionPercent.map { String(format: "%.0f", $0 * 100) } ?? "" }
        ),
    ]

    private static let iso8601 = ISO8601DateFormatter()
    private static let filenameDateFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = .current
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter
    }()
}

struct TastingExportDocument: FileDocument {
    static var readableContentTypes: [UTType] { [.json, .commaSeparatedText] }

    let data: Data

    init(data: Data) {
        self.data = data
    }

    init(configuration: ReadConfiguration) throws {
        guard let data = configuration.file.regularFileContents else {
            throw CocoaError(.fileReadCorruptFile)
        }
        self.data = data
    }

    func fileWrapper(configuration: WriteConfiguration) throws -> FileWrapper {
        FileWrapper(regularFileWithContents: data)
    }
}
