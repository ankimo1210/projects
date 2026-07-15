import Foundation
import PDFKit

private struct OfficialVocabularyRow: Codable {
    let id: String
    let officialIndex: Int
    let level: String
    let levelAnnotations: String
    let hanzi: String
    let pinyin: String
    let partOfSpeech: String?
}

private enum ExtractionError: Error, CustomStringConvertible {
    case usage
    case unreadablePDF(String)
    case incomplete(expected: Int, actual: Int, missing: [Int])

    var description: String {
        switch self {
        case .usage:
            return "Usage: xcrun swift Tools/extract_hsk_vocabulary.swift <syllabus.pdf> <output.json>"
        case let .unreadablePDF(path):
            return "Could not open PDF: \(path)"
        case let .incomplete(expected, actual, missing):
            return "Expected \(expected) rows, extracted \(actual). Missing indices: \(missing.prefix(30))"
        }
    }
}

private let rowStartPattern = try! NSRegularExpression(
    pattern: #"(?<![0-9])([0-9]{1,5})\s+(?:[1-6]|7-9)(?:（[^）]+）)*\s+"#
)

private func containsCJK(_ value: Substring) -> Bool {
    value.unicodeScalars.contains { scalar in
        switch scalar.value {
        case 0x3400...0x4DBF, 0x4E00...0x9FFF, 0xF900...0xFAFF:
            return true
        default:
            return false
        }
    }
}

private func cleanedLine(_ rawLine: Substring) -> String? {
    var line = String(rawLine)
        .replacingOccurrences(of: "汉考国际", with: "")
        .trimmingCharacters(in: .whitespacesAndNewlines)

    guard !line.isEmpty else { return nil }
    let range = NSRange(line.startIndex..<line.endIndex, in: line)
    guard let match = rowStartPattern.firstMatch(in: line, range: range),
          let swiftRange = Range(match.range, in: line)
    else { return nil }

    line = String(line[swiftRange.lowerBound...])
    return line
}

private func parse(_ line: String) -> OfficialVocabularyRow? {
    let tokens = line.split(whereSeparator: { $0.isWhitespace })
    guard tokens.count >= 4,
          let officialIndex = Int(tokens[0]),
          (1...11_000).contains(officialIndex)
    else { return nil }

    let rawLevel = String(tokens[1])
    let level: String
    if rawLevel.hasPrefix("7-9") {
        level = "7-9"
    } else if let first = rawLevel.first, "123456".contains(first) {
        level = String(first)
    } else {
        return nil
    }

    let hanzi = String(tokens[2])
    let remainder = Array(tokens.dropFirst(3))
    guard !hanzi.isEmpty, !remainder.isEmpty else { return nil }

    let partOfSpeechStart = remainder.firstIndex(where: containsCJK)
    let pinyinTokens = partOfSpeechStart.map { remainder[..<$0] } ?? remainder[...]
    let pinyin = pinyinTokens.map(String.init).joined(separator: " ")
    guard !pinyin.isEmpty else { return nil }

    let partOfSpeech: String?
    if let partOfSpeechStart {
        let value = remainder[partOfSpeechStart...].map(String.init).joined(separator: "")
        partOfSpeech = value.isEmpty ? nil : value
    } else {
        partOfSpeech = nil
    }

    return OfficialVocabularyRow(
        id: String(format: "hsk3-v%05d", officialIndex),
        officialIndex: officialIndex,
        level: level,
        levelAnnotations: rawLevel,
        hanzi: hanzi,
        pinyin: pinyin,
        partOfSpeech: partOfSpeech
    )
}

private func run() throws {
    guard CommandLine.arguments.count == 3 else { throw ExtractionError.usage }
    let inputPath = CommandLine.arguments[1]
    let outputPath = CommandLine.arguments[2]
    guard let document = PDFDocument(url: URL(fileURLWithPath: inputPath)) else {
        throw ExtractionError.unreadablePDF(inputPath)
    }

    var rowsByIndex: [Int: OfficialVocabularyRow] = [:]
    for pageIndex in 0..<document.pageCount {
        guard let text = document.page(at: pageIndex)?.string else { continue }
        for rawLine in text.split(separator: "\n", omittingEmptySubsequences: true) {
            guard let line = cleanedLine(rawLine), let row = parse(line) else { continue }
            rowsByIndex[row.officialIndex] = row
        }
    }

    let missing = (1...11_000).filter { rowsByIndex[$0] == nil }
    guard missing.isEmpty, rowsByIndex.count == 11_000 else {
        throw ExtractionError.incomplete(expected: 11_000, actual: rowsByIndex.count, missing: missing)
    }

    let rows = rowsByIndex.values.sorted { $0.officialIndex < $1.officialIndex }
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]
    let data = try encoder.encode(rows)
    let outputURL = URL(fileURLWithPath: outputPath)
    try FileManager.default.createDirectory(
        at: outputURL.deletingLastPathComponent(),
        withIntermediateDirectories: true
    )
    try data.write(to: outputURL, options: .atomic)
    print("Extracted \(rows.count) vocabulary rows to \(outputURL.path)")
}

do {
    try run()
} catch {
    FileHandle.standardError.write(Data("\(error)\n".utf8))
    exit(1)
}
