import CryptoKit
import Foundation

nonisolated enum ICloudAvailabilityStatus: String, Codable, Equatable {
    case available
    case signedOut
    case containerUnavailable
}

nonisolated struct ICloudAvailabilityDiagnostic: Equatable {
    let status: ICloudAvailabilityStatus
    let checkedAt: Date
    let containerName: String?

    var isReadyForManualTransfer: Bool {
        status == .available
    }

    var message: String {
        switch status {
        case .available:
            "iCloudコンテナを利用できます。転送は手動操作を行うまで開始されません。"
        case .signedOut:
            "iCloudにサインインしていないため、端末内のデータを引き続き使用します。"
        case .containerUnavailable:
            "このビルドではiCloudコンテナを利用できません。端末内のデータを引き続き使用します。"
        }
    }
}

nonisolated struct ICloudTransferReceipt: Equatable {
    let fileName: String
    let byteCount: Int
    let sha256: String
    let transferredAt: Date
}

nonisolated protocol UbiquityContainerLocating {
    var hasUbiquityIdentity: Bool { get }
    func containerURL(identifier: String?) -> URL?
}

nonisolated struct SystemUbiquityContainerLocator: UbiquityContainerLocating {
    private let fileManager: FileManager

    init(fileManager: FileManager = .default) {
        self.fileManager = fileManager
    }

    var hasUbiquityIdentity: Bool {
        fileManager.ubiquityIdentityToken != nil
    }

    func containerURL(identifier: String?) -> URL? {
        fileManager.url(forUbiquityContainerIdentifier: identifier)
    }
}

nonisolated enum ICloudManualTransferError: LocalizedError, Equatable {
    case signedOut
    case containerUnavailable
    case invalidFileName
    case fileMissing
    case coordinatedAccessFailed

    var errorDescription: String? {
        switch self {
        case .signedOut:
            "iCloudにサインインしていません。端末内のデータは変更されていません。"
        case .containerUnavailable:
            "iCloudコンテナを利用できません。端末内のデータは変更されていません。"
        case .invalidFileName:
            "転送ファイル名が不正です。フォルダを含まないファイル名を指定してください。"
        case .fileMissing:
            "iCloud上に指定したバックアップがありません。"
        case .coordinatedAccessFailed:
            "iCloudファイルへの安全なアクセスを完了できませんでした。"
        }
    }
}

/// iCloudへの書き込みは `upload` が明示的に呼ばれた時だけ行う。
/// 診断と取得の失敗はローカルデータを変更しない。
actor ICloudManualTransferService {
    private let containerIdentifier: String?
    private let locator: any UbiquityContainerLocating
    private let fileManager: FileManager
    private let usesFileCoordination: Bool

    init(
        containerIdentifier: String? = nil,
        locator: any UbiquityContainerLocating = SystemUbiquityContainerLocator(),
        fileManager: FileManager = .default,
        usesFileCoordination: Bool = true
    ) {
        self.containerIdentifier = containerIdentifier
        self.locator = locator
        self.fileManager = fileManager
        self.usesFileCoordination = usesFileCoordination
    }

    func diagnose(at date: Date = .now) -> ICloudAvailabilityDiagnostic {
        guard locator.hasUbiquityIdentity else {
            return ICloudAvailabilityDiagnostic(
                status: .signedOut,
                checkedAt: date,
                containerName: nil
            )
        }
        guard let containerURL = locator.containerURL(identifier: containerIdentifier) else {
            return ICloudAvailabilityDiagnostic(
                status: .containerUnavailable,
                checkedAt: date,
                containerName: nil
            )
        }
        return ICloudAvailabilityDiagnostic(
            status: .available,
            checkedAt: date,
            containerName: containerURL.lastPathComponent
        )
    }

    @discardableResult
    func upload(
        _ data: Data,
        fileName: String,
        at date: Date = .now
    ) throws -> ICloudTransferReceipt {
        let destination = try transferURL(fileName: fileName)
        let directory = destination.deletingLastPathComponent()
        try fileManager.createDirectory(at: directory, withIntermediateDirectories: true)

        if usesFileCoordination {
            try coordinateWrite(data, to: destination)
        } else {
            try data.write(to: destination, options: .atomic)
        }

        return receipt(for: data, fileName: fileName, at: date)
    }

    func download(
        fileName: String,
        at date: Date = .now
    ) throws -> (data: Data, receipt: ICloudTransferReceipt) {
        let source = try transferURL(fileName: fileName)
        guard fileManager.fileExists(atPath: source.path) else {
            throw ICloudManualTransferError.fileMissing
        }

        let data: Data
        if usesFileCoordination {
            data = try coordinateRead(from: source)
        } else {
            data = try Data(contentsOf: source)
        }
        return (data, receipt(for: data, fileName: fileName, at: date))
    }

    private func transferURL(fileName: String) throws -> URL {
        guard isSafeFileName(fileName) else {
            throw ICloudManualTransferError.invalidFileName
        }
        guard locator.hasUbiquityIdentity else {
            throw ICloudManualTransferError.signedOut
        }
        guard let containerURL = locator.containerURL(identifier: containerIdentifier) else {
            throw ICloudManualTransferError.containerUnavailable
        }
        return containerURL
            .appendingPathComponent("Documents", isDirectory: true)
            .appendingPathComponent(fileName, isDirectory: false)
    }

    private func isSafeFileName(_ fileName: String) -> Bool {
        guard !fileName.isEmpty,
              fileName != ".",
              fileName != "..",
              !fileName.contains("/"),
              !fileName.contains("\\"),
              !fileName.contains("\0")
        else { return false }
        return URL(fileURLWithPath: fileName).lastPathComponent == fileName
    }

    private func coordinateWrite(_ data: Data, to destination: URL) throws {
        let coordinator = NSFileCoordinator()
        var coordinationError: NSError?
        var writeError: Error?
        coordinator.coordinate(
            writingItemAt: destination,
            options: .forReplacing,
            error: &coordinationError
        ) { coordinatedURL in
            do {
                try data.write(to: coordinatedURL, options: .atomic)
            } catch {
                writeError = error
            }
        }
        if let writeError { throw writeError }
        if coordinationError != nil {
            throw ICloudManualTransferError.coordinatedAccessFailed
        }
    }

    private func coordinateRead(from source: URL) throws -> Data {
        let coordinator = NSFileCoordinator()
        var coordinationError: NSError?
        var readResult: Result<Data, Error>?
        coordinator.coordinate(
            readingItemAt: source,
            options: .withoutChanges,
            error: &coordinationError
        ) { coordinatedURL in
            readResult = Result { try Data(contentsOf: coordinatedURL) }
        }
        if let readResult { return try readResult.get() }
        if coordinationError != nil {
            throw ICloudManualTransferError.coordinatedAccessFailed
        }
        throw ICloudManualTransferError.fileMissing
    }

    private func receipt(for data: Data, fileName: String, at date: Date) -> ICloudTransferReceipt {
        let digest = SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
        return ICloudTransferReceipt(
            fileName: fileName,
            byteCount: data.count,
            sha256: digest,
            transferredAt: date
        )
    }
}
