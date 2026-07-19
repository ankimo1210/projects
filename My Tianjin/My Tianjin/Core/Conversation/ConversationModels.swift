import Foundation

nonisolated enum ConversationScenario: String, Codable, CaseIterable, Identifiable, Sendable {
    case selfIntroduction
    case restaurant
    case shopping
    case directions
    case dailyLife
    case studyAndWork

    var id: String { rawValue }

    var title: String {
        switch self {
        case .selfIntroduction: "自己紹介"
        case .restaurant: "レストラン"
        case .shopping: "買い物"
        case .directions: "道を尋ねる"
        case .dailyLife: "日常会話"
        case .studyAndWork: "勉強・仕事"
        }
    }

    var subtitle: String {
        switch self {
        case .selfIntroduction: "名前・出身・趣味を話す"
        case .restaurant: "人数・注文・会計を伝える"
        case .shopping: "商品・色・値段について聞く"
        case .directions: "目的地と行き方を確認する"
        case .dailyLife: "今日の出来事や予定を話す"
        case .studyAndWork: "学習内容や仕事について話す"
        }
    }

    var icon: String {
        switch self {
        case .selfIntroduction: "person.wave.2.fill"
        case .restaurant: "fork.knife"
        case .shopping: "bag.fill"
        case .directions: "map.fill"
        case .dailyLife: "sun.max.fill"
        case .studyAndWork: "books.vertical.fill"
        }
    }

    var partnerRole: String {
        switch self {
        case .selfIntroduction: "初めて会った中国語話者"
        case .restaurant: "レストランの店員"
        case .shopping: "店員"
        case .directions: "親切な地元の人"
        case .dailyLife: "中国語を話す友人"
        case .studyAndWork: "同僚またはクラスメート"
        }
    }

    var openingReply: ConversationReply {
        switch self {
        case .selfIntroduction:
            ConversationReply(
                chinese: "你好！很高兴认识你。你叫什么名字？",
                pinyin: "Nǐ hǎo! Hěn gāoxìng rènshi nǐ. Nǐ jiào shénme míngzi?",
                japanese: "こんにちは！お会いできてうれしいです。お名前は何ですか？",
                suggestedReplies: ["我叫……。", "你好，我是……。", "我叫……，来自日本。"],
                hintJapanese: "「私は〜といいます」は「我叫〜」です。"
            )
        case .restaurant:
            ConversationReply(
                chinese: "欢迎光临！请问几位？",
                pinyin: "Huānyíng guānglín! Qǐngwèn jǐ wèi?",
                japanese: "いらっしゃいませ。何名様ですか？",
                suggestedReplies: ["一位。", "我们两位。", "三位，谢谢。"],
                hintJapanese: "人数は「数字＋位」で丁寧に答えられます。"
            )
        case .shopping:
            ConversationReply(
                chinese: "您好，您想买什么？",
                pinyin: "Nín hǎo, nín xiǎng mǎi shénme?",
                japanese: "こんにちは。何をお探しですか？",
                suggestedReplies: ["我想买一件衣服。", "我想看看这个。", "我先看看，谢谢。"],
                hintJapanese: "「〜を買いたい」は「我想买〜」です。"
            )
        case .directions:
            ConversationReply(
                chinese: "你好，需要我帮你指路吗？",
                pinyin: "Nǐ hǎo, xūyào wǒ bāng nǐ zhǐlù ma?",
                japanese: "こんにちは。道案内をしましょうか？",
                suggestedReplies: ["请问，车站在哪儿？", "我想去博物馆。", "请问怎么去这里？"],
                hintJapanese: "場所は「〜在哪儿？」、行き方は「怎么去〜？」で聞けます。"
            )
        case .dailyLife:
            ConversationReply(
                chinese: "你好！你今天过得怎么样？",
                pinyin: "Nǐ hǎo! Nǐ jīntiān guò de zěnmeyàng?",
                japanese: "こんにちは！今日はどんな一日でしたか？",
                suggestedReplies: ["今天很好。", "我有一点儿忙。", "我今天去上班了。"],
                hintJapanese: "まず「今天〜」で今日の状態や行動を話してみましょう。"
            )
        case .studyAndWork:
            ConversationReply(
                chinese: "你好！你最近在学习什么？",
                pinyin: "Nǐ hǎo! Nǐ zuìjìn zài xuéxí shénme?",
                japanese: "こんにちは！最近は何を勉強していますか？",
                suggestedReplies: ["我在学习中文。", "我在学习编程。", "最近我在准备考试。"],
                hintJapanese: "進行中の学習は「我在学习〜」と表せます。"
            )
        }
    }
}

nonisolated struct ConversationConfiguration: Codable, Hashable, Sendable {
    var level: HSKLevel
    var scenario: ConversationScenario
    var maximumLearnerTurns: Int
    var timeLimitSeconds: Int

    init(
        level: HSKLevel,
        scenario: ConversationScenario,
        maximumLearnerTurns: Int = 12,
        timeLimitSeconds: Int = 300
    ) {
        self.level = level
        self.scenario = scenario
        self.maximumLearnerTurns = maximumLearnerTurns
        self.timeLimitSeconds = timeLimitSeconds
    }
}

nonisolated enum ConversationRole: String, Codable, Sendable {
    case learner
    case partner
}

nonisolated struct ConversationMessage: Codable, Hashable, Identifiable, Sendable {
    let id: UUID
    let role: ConversationRole
    let chinese: String
    let pinyin: String?
    let japanese: String?
    let suggestedReplies: [String]
    let hintJapanese: String?
    let createdAt: Date

    init(
        id: UUID = UUID(),
        role: ConversationRole,
        chinese: String,
        pinyin: String? = nil,
        japanese: String? = nil,
        suggestedReplies: [String] = [],
        hintJapanese: String? = nil,
        createdAt: Date = Date()
    ) {
        self.id = id
        self.role = role
        self.chinese = chinese
        self.pinyin = pinyin
        self.japanese = japanese
        self.suggestedReplies = suggestedReplies
        self.hintJapanese = hintJapanese
        self.createdAt = createdAt
    }

    static func partner(_ reply: ConversationReply) -> ConversationMessage {
        ConversationMessage(
            role: .partner,
            chinese: reply.chinese,
            pinyin: reply.pinyin,
            japanese: reply.japanese,
            suggestedReplies: reply.suggestedReplies,
            hintJapanese: reply.hintJapanese
        )
    }
}

nonisolated struct ConversationReply: Codable, Hashable, Sendable {
    let chinese: String
    let pinyin: String
    let japanese: String
    let suggestedReplies: [String]
    let hintJapanese: String
}

nonisolated struct ConversationCorrection: Codable, Hashable, Identifiable, Sendable {
    let id: UUID
    let originalChinese: String
    let correctedChinese: String
    let explanationJapanese: String

    init(
        id: UUID = UUID(),
        originalChinese: String,
        correctedChinese: String,
        explanationJapanese: String
    ) {
        self.id = id
        self.originalChinese = originalChinese
        self.correctedChinese = correctedChinese
        self.explanationJapanese = explanationJapanese
    }
}

nonisolated struct ConversationFeedback: Codable, Hashable, Sendable {
    let positiveNoteJapanese: String
    let corrections: [ConversationCorrection]
    let reviewWords: [String]
}

nonisolated enum ConversationProvider: String, Codable, Sendable {
    case appleOnDevice
    case scriptedFallback

    var displayName: String {
        switch self {
        case .appleOnDevice: "Apple端末内AI"
        case .scriptedFallback: "端末内シナリオ"
        }
    }
}

nonisolated struct ConversationArchive: Codable, Hashable, Identifiable, Sendable {
    let id: UUID
    let configuration: ConversationConfiguration
    let provider: ConversationProvider
    let startedAt: Date
    let endedAt: Date
    let messages: [ConversationMessage]
    let feedback: ConversationFeedback

    var durationSeconds: Int {
        max(0, Int(endedAt.timeIntervalSince(startedAt)))
    }
}
