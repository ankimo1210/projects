import Combine
import Foundation

@MainActor
final class LearningContentStore: ObservableObject {
    @Published private(set) var manifest: ContentManifest?
    @Published private(set) var packsByLevel: [HSKLevel: LevelContentPack] = [:]
    @Published private(set) var isLoading = false
    @Published private(set) var loadError: String?
    @Published private(set) var isUsingFallback = false

    private let repository: ContentRepository
    private var activeLoadCount = 0
    private var latestLoadRequestID = UUID()

    init(repository: ContentRepository? = nil) {
        self.repository = repository ?? ContentRepository()
    }

    var availableLevels: [HSKLevel] {
        manifest?.packs
            .filter { $0.syllabusVersion == .hsk3 }
            .map(\.level)
            .sorted() ?? [.level1]
    }

    func prepare() {
        guard manifest == nil, !isLoading else { return }
        isLoading = true
        defer { isLoading = false }

        do {
            manifest = try repository.loadManifest()
            try load(level: .level1)
            isUsingFallback = false
            loadError = nil
        } catch {
            installCuratedFallback()
            isUsingFallback = true
            loadError = "公式コンテンツを読み込めなかったため、内蔵100語を表示しています。\n\(error.localizedDescription)"
        }
    }

    func load(level: HSKLevel) throws {
        guard packsByLevel[level] == nil || (isUsingFallback && level == .level1) else { return }
        if manifest == nil {
            manifest = try repository.loadManifest()
        }
        guard let descriptor = manifest?.packs.first(where: {
            $0.syllabusVersion == .hsk3 && $0.level == level
        }) else {
            throw ContentRepositoryError.noMatchingPacks(
                syllabusVersion: .hsk3,
                levels: [level]
            )
        }
        packsByLevel[level] = try repository.loadPack(descriptor)
        if level == .level1 { isUsingFallback = false }
    }

    func ensureLoaded(for level: HSKLevel, cumulative: Bool) async throws {
        let levels = cumulative ? level.levelsThroughSelf : [level]
        let levelsToLoad = levels.filter {
            packsByLevel[$0] == nil || (isUsingFallback && $0 == .level1)
        }
        guard !levelsToLoad.isEmpty else {
            if !(isUsingFallback && levels.contains(.level1)) { loadError = nil }
            return
        }

        let requestID = UUID()
        latestLoadRequestID = requestID
        activeLoadCount += 1
        isLoading = true
        defer {
            activeLoadCount -= 1
            isLoading = activeLoadCount > 0
        }

        let currentManifest = manifest
        let repository = repository
        do {
            let loaded = try await Task.detached(priority: .userInitiated) {
                let loadedManifest: ContentManifest
                if let currentManifest {
                    loadedManifest = currentManifest
                } else {
                    loadedManifest = try repository.loadManifest()
                }
                var packs: [HSKLevel: LevelContentPack] = [:]
                for requiredLevel in levelsToLoad {
                    guard let descriptor = loadedManifest.packs.first(where: {
                        $0.syllabusVersion == .hsk3 && $0.level == requiredLevel
                    }) else {
                        throw ContentRepositoryError.noMatchingPacks(
                            syllabusVersion: .hsk3,
                            levels: [requiredLevel]
                        )
                    }
                    packs[requiredLevel] = try repository.loadPack(descriptor)
                }
                return LoadedContentBatch(manifest: loadedManifest, packs: packs)
            }.value

            manifest = loaded.manifest
            for (loadedLevel, pack) in loaded.packs {
                packsByLevel[loadedLevel] = pack
            }
            if loaded.packs[.level1] != nil { isUsingFallback = false }
            if latestLoadRequestID == requestID { loadError = nil }
        } catch {
            if latestLoadRequestID == requestID {
                loadError = error.localizedDescription
            }
            throw error
        }
    }

    func vocabulary(for level: HSKLevel, cumulative: Bool) -> [VocabularyItem] {
        let levels = cumulative ? level.levelsThroughSelf : [level]
        return levels
            .compactMap { packsByLevel[$0] }
            .flatMap(\.vocabulary)
            .sorted { $0.officialIndex < $1.officialIndex }
    }

    func item(id: String) -> VocabularyItem? {
        packsByLevel.values
            .lazy
            .flatMap(\.vocabulary)
            .first { $0.id == id }
    }

    private func installCuratedFallback() {
        let items = VocabularySeed.all.map { entry in
            VocabularyItem(
                id: "hsk3-vocab-\(entry.officialIndex)",
                officialIndex: entry.officialIndex,
                hanzi: entry.hanzi,
                pinyin: entry.pinyin,
                partOfSpeech: entry.partOfSpeech,
                japanese: [entry.japanese],
                examples: [
                    ExampleSentence(
                        id: "hsk3-vocab-\(entry.officialIndex)-example-1",
                        hanzi: entry.example,
                        pinyin: entry.examplePinyin,
                        japanese: entry.exampleJapanese
                    )
                ],
                tags: ["curated", "legacy-id:\(entry.id)"]
            )
        }
        packsByLevel[.level1] = LevelContentPack(
            id: "curated-fallback-hsk1",
            contentVersion: "fallback-1",
            syllabusVersion: .hsk3,
            level: .level1,
            source: ContentSource(
                title: "内蔵初級語彙",
                url: "https://www.chinesetest.cn/syllabus",
                license: nil
            ),
            vocabulary: items
        )
    }
}

private struct LoadedContentBatch: Sendable {
    let manifest: ContentManifest
    let packs: [HSKLevel: LevelContentPack]
}

extension VocabularyItem {
    var primaryJapanese: String {
        japanese.first ?? "意味未確認"
    }

    var isMachineTranslated: Bool {
        tags.contains("machine-translated-cc-cedict")
    }

    var displayPartOfSpeech: String? {
        guard let value = partOfSpeech, !value.isEmpty else { return nil }
        if value.contains("詞") || value.contains("接尾辞") || value.contains("接頭辞") {
            return value
        }
        let mappings: [(String, String)] = [
            ("后缀", "接尾辞"), ("前缀", "接頭辞"),
            ("拟声", "擬声語"),
            ("代", "代名詞"), ("名", "名詞"), ("动", "動詞"),
            ("形", "形容詞"), ("副", "副詞"), ("量", "量詞"),
            ("介", "前置詞"), ("连", "接続詞"), ("助", "助詞"),
            ("叹", "感嘆詞"), ("数", "数詞")
        ]
        var labels: [String] = []
        for (marker, label) in mappings where value.contains(marker) && !labels.contains(label) {
            labels.append(label)
        }
        return labels.isEmpty ? value : labels.joined(separator: "・")
    }
}
