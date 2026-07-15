import Foundation

/// A lightweight annotation used by reading screens for tap-to-inspect words.
public struct PracticeVocabularyAnnotation: Identifiable, Codable, Hashable, Sendable {
    public var id: String
    public var hanzi: String
    public var pinyin: String
    public var japanese: String

    public init(id: String, hanzi: String, pinyin: String, japanese: String) {
        self.id = id
        self.hanzi = hanzi
        self.pinyin = pinyin
        self.japanese = japanese
    }
}

/// One original passage together with its questions and tappable vocabulary.
public struct PracticeReadingSeed: Identifiable, Codable, Hashable, Sendable {
    public var id: String { passage.id }
    public var passage: PracticePassage
    public var questions: [PracticeQuestion]
    public var vocabularyAnnotations: [PracticeVocabularyAnnotation]

    public init(
        passage: PracticePassage,
        questions: [PracticeQuestion],
        vocabularyAnnotations: [PracticeVocabularyAnnotation]
    ) {
        self.passage = passage
        self.questions = questions
        self.vocabularyAnnotations = vocabularyAnnotations
    }
}

/// Original, app-owned seed material. None of the sentences or passages below
/// are copied from an official examination paper.
public enum PracticeSeedContent {
    public static let orderingQuestions: [PracticeQuestion] = orderingSeeds.map {
        makeOrderingQuestion(from: $0)
    }

    public static let beginnerReadingSeeds: [PracticeReadingSeed] = readingSeeds.map {
        makeReadingSeed(from: $0)
    }

    public static let passages: [PracticePassage] = beginnerReadingSeeds.map(\.passage)
    public static let readingQuestions: [PracticeQuestion] = beginnerReadingSeeds.flatMap(\.questions)

    /// Backward-friendly descriptive alias for callers that prefer a longer name.
    public static let sentenceOrderingQuestions = orderingQuestions

    public static let writtenRubric = PracticeFreeResponseRubric(
        id: "rubric-written-general",
        title: "記述課題（20点）",
        criteria: [
            rubricCriterion(
                id: "content",
                title: "内容",
                description: "問いに答え、必要な情報と根拠を含めている。",
                maximumPoints: 8
            ),
            rubricCriterion(
                id: "organization",
                title: "構成",
                description: "情報の順序が明確で、接続表現が適切である。",
                maximumPoints: 4
            ),
            rubricCriterion(
                id: "language",
                title: "語彙・文法",
                description: "課題に合う語彙を用い、意味を妨げる誤りが少ない。",
                maximumPoints: 8
            )
        ],
        passingPoints: 12
    )

    public static let translationRubric = PracticeFreeResponseRubric(
        id: "rubric-translation-general",
        title: "翻訳課題（20点）",
        criteria: [
            rubricCriterion(
                id: "accuracy",
                title: "意味の正確さ",
                description: "原文の事実関係、論理、語調を過不足なく伝えている。",
                maximumPoints: 10
            ),
            rubricCriterion(
                id: "naturalness",
                title: "自然さ",
                description: "訳文として自然で、対象言語の慣用に沿っている。",
                maximumPoints: 6
            ),
            rubricCriterion(
                id: "terminology",
                title: "語彙選択",
                description: "文脈に合う語と表現を一貫して選んでいる。",
                maximumPoints: 4
            )
        ],
        passingPoints: 12
    )

    public static let spokenRubric = PracticeFreeResponseRubric(
        id: "rubric-spoken-general",
        title: "口頭課題（20点）",
        criteria: [
            rubricCriterion(
                id: "task",
                title: "課題達成",
                description: "質問に直接答え、理由または具体例を述べている。",
                maximumPoints: 8
            ),
            rubricCriterion(
                id: "fluency",
                title: "流暢さ",
                description: "不自然に長い停止が少なく、まとまりを保って話す。",
                maximumPoints: 6
            ),
            rubricCriterion(
                id: "pronunciation",
                title: "発音",
                description: "声調、子音、リズムが意味理解を妨げない。",
                maximumPoints: 6
            )
        ],
        passingPoints: 12
    )

    // MARK: - Ordering

    private struct OrderingSeed {
        var id: String
        var level: PracticeHSKLevel
        var parts: [String]
        var pinyin: String
        var japanese: String
    }

    private static let orderingSeeds: [OrderingSeed] = [
        .init(id: "order-001", level: .level1, parts: ["我", "每天", "七点", "起床"], pinyin: "Wǒ měitiān qī diǎn qǐchuáng.", japanese: "私は毎日7時に起きます。"),
        .init(id: "order-002", level: .level1, parts: ["她", "是", "我的", "汉语老师"], pinyin: "Tā shì wǒ de Hànyǔ lǎoshī.", japanese: "彼女は私の中国語の先生です。"),
        .init(id: "order-003", level: .level1, parts: ["桌子上", "有", "一本", "书"], pinyin: "Zhuōzi shàng yǒu yì běn shū.", japanese: "机の上に本が1冊あります。"),
        .init(id: "order-004", level: .level1, parts: ["你", "想喝", "茶", "还是咖啡"], pinyin: "Nǐ xiǎng hē chá háishi kāfēi?", japanese: "お茶とコーヒーのどちらを飲みたいですか。"),
        .init(id: "order-005", level: .level1, parts: ["今天", "比昨天", "暖和"], pinyin: "Jīntiān bǐ zuótiān nuǎnhuo.", japanese: "今日は昨日より暖かいです。"),
        .init(id: "order-006", level: .level1, parts: ["弟弟", "正在", "房间里", "看书"], pinyin: "Dìdi zhèngzài fángjiān lǐ kàn shū.", japanese: "弟は部屋で本を読んでいるところです。"),
        .init(id: "order-007", level: .level1, parts: ["请", "把门", "关上"], pinyin: "Qǐng bǎ mén guān shàng.", japanese: "ドアを閉めてください。"),
        .init(id: "order-008", level: .level1, parts: ["从我家", "到学校", "要", "二十分钟"], pinyin: "Cóng wǒ jiā dào xuéxiào yào èrshí fēnzhōng.", japanese: "家から学校まで20分かかります。"),
        .init(id: "order-009", level: .level1, parts: ["这个苹果", "又大", "又甜"], pinyin: "Zhège píngguǒ yòu dà yòu tián.", japanese: "このリンゴは大きくて甘いです。"),
        .init(id: "order-010", level: .level1, parts: ["明天", "我们", "一起", "去公园吧"], pinyin: "Míngtiān wǒmen yìqǐ qù gōngyuán ba.", japanese: "明日一緒に公園へ行きましょう。"),
        .init(id: "order-011", level: .level2, parts: ["因为下雨", "所以比赛", "取消了"], pinyin: "Yīnwèi xiàyǔ, suǒyǐ bǐsài qǔxiāo le.", japanese: "雨のため試合は中止になりました。"),
        .init(id: "order-012", level: .level2, parts: ["他", "已经", "在北京", "住了三年"], pinyin: "Tā yǐjīng zài Běijīng zhù le sān nián.", japanese: "彼はすでに北京に3年住んでいます。"),
        .init(id: "order-013", level: .level2, parts: ["虽然很累", "但是她", "还在", "认真工作"], pinyin: "Suīrán hěn lèi, dànshì tā hái zài rènzhēn gōngzuò.", japanese: "とても疲れていますが、彼女はまだ真面目に働いています。"),
        .init(id: "order-014", level: .level2, parts: ["这件衣服", "看起来", "很适合你"], pinyin: "Zhè jiàn yīfu kàn qǐlái hěn shìhé nǐ.", japanese: "この服はあなたによく似合いそうです。"),
        .init(id: "order-015", level: .level2, parts: ["我", "忘了", "带", "手机"], pinyin: "Wǒ wàng le dài shǒujī.", japanese: "携帯電話を持ってくるのを忘れました。"),
        .init(id: "order-016", level: .level2, parts: ["请你", "再说", "一遍"], pinyin: "Qǐng nǐ zài shuō yí biàn.", japanese: "もう一度言ってください。"),
        .init(id: "order-017", level: .level2, parts: ["这家饭店", "不但便宜", "而且", "服务很好"], pinyin: "Zhè jiā fàndiàn búdàn piányi, érqiě fúwù hěn hǎo.", japanese: "この店は安いだけでなく、サービスもとても良いです。"),
        .init(id: "order-018", level: .level2, parts: ["你", "是什么时候", "开始学中文的"], pinyin: "Nǐ shì shénme shíhou kāishǐ xué Zhōngwén de?", japanese: "あなたはいつ中国語を学び始めたのですか。"),
        .init(id: "order-019", level: .level2, parts: ["我对", "中国历史", "越来越", "感兴趣"], pinyin: "Wǒ duì Zhōngguó lìshǐ yuèláiyuè gǎn xìngqù.", japanese: "私は中国の歴史にますます興味を持っています。"),
        .init(id: "order-020", level: .level2, parts: ["只要有时间", "我就", "去游泳"], pinyin: "Zhǐyào yǒu shíjiān, wǒ jiù qù yóuyǒng.", japanese: "時間さえあれば、私は泳ぎに行きます。"),
        .init(id: "order-021", level: .level3, parts: ["经理", "让我们", "下班前", "完成报告"], pinyin: "Jīnglǐ ràng wǒmen xiàbān qián wánchéng bàogào.", japanese: "マネージャーは退勤前に報告書を仕上げるよう私たちに言いました。"),
        .init(id: "order-022", level: .level3, parts: ["这个问题", "值得", "大家", "认真考虑"], pinyin: "Zhège wèntí zhíde dàjiā rènzhēn kǎolǜ.", japanese: "この問題は皆が真剣に検討する価値があります。"),
        .init(id: "order-023", level: .level3, parts: ["为了保护环境", "越来越多的人", "选择", "坐公共汽车"], pinyin: "Wèile bǎohù huánjìng, yuèláiyuè duō de rén xuǎnzé zuò gōnggòng qìchē.", japanese: "環境保護のため、バスを選ぶ人が増えています。"),
        .init(id: "order-024", level: .level3, parts: ["无论遇到什么困难", "他都", "不会", "轻易放弃"], pinyin: "Wúlùn yùdào shénme kùnnan, tā dōu bú huì qīngyì fàngqì.", japanese: "どんな困難に遭っても、彼は簡単には諦めません。"),
        .init(id: "order-025", level: .level3, parts: ["这次活动", "给我", "留下了", "深刻的印象"], pinyin: "Zhè cì huódòng gěi wǒ liúxià le shēnkè de yìnxiàng.", japanese: "今回の活動は私に深い印象を残しました。"),
        .init(id: "order-026", level: .level3, parts: ["经过讨论", "我们终于", "找到了解决办法"], pinyin: "Jīngguò tǎolùn, wǒmen zhōngyú zhǎodào le jiějué bànfǎ.", japanese: "話し合いを経て、私たちはついに解決方法を見つけました。"),
        .init(id: "order-027", level: .level3, parts: ["与其在家等", "不如", "主动联系他"], pinyin: "Yǔqí zài jiā děng, bùrú zhǔdòng liánxì tā.", japanese: "家で待つより、自分から彼に連絡したほうがよいです。"),
        .init(id: "order-028", level: .level3, parts: ["这座城市", "以", "丰富的美食", "而闻名"], pinyin: "Zhè zuò chéngshì yǐ fēngfù de měishí ér wénmíng.", japanese: "この都市は豊富なグルメで有名です。"),
        .init(id: "order-029", level: .level3, parts: ["随着科技的发展", "人们的生活", "变得", "更加方便"], pinyin: "Suízhe kējì de fāzhǎn, rénmen de shēnghuó biànde gèngjiā fāngbiàn.", japanese: "科学技術の発展につれて、生活はより便利になっています。"),
        .init(id: "order-030", level: .level3, parts: ["如果提前准备", "考试时", "就不会", "那么紧张"], pinyin: "Rúguǒ tíqián zhǔnbèi, kǎoshì shí jiù bú huì nàme jǐnzhāng.", japanese: "早めに準備すれば、試験のときそれほど緊張しません。")
    ]

    private static func makeOrderingQuestion(from seed: OrderingSeed) -> PracticeQuestion {
        let orderedTokens = seed.parts.enumerated().map { index, text in
            PracticeOrderingToken(
                id: "\(seed.id)-token-\(index + 1)",
                content: PracticeText(text: text)
            )
        }
        let displayedTokens = Array(orderedTokens.dropFirst()) + Array(orderedTokens.prefix(1))

        return PracticeQuestion(
            id: seed.id,
            content: .sentenceOrdering(
                PracticeOrderingQuestion(
                    prompt: PracticePrompt(instruction: "語句を自然な中国語の文に並べ替えてください。"),
                    tokens: displayedTokens,
                    acceptedTokenOrders: [orderedTokens.map(\.id)]
                )
            ),
            metadata: PracticeQuestionMetadata(
                level: seed.level,
                skills: [.wordOrder, .grammar],
                tags: ["original", "sentence-order"],
                recommendedDurationSeconds: 30
            ),
            explanation: PracticeAnswerExplanation(
                summary: "正解：\(seed.parts.joined())。",
                details: "\(seed.pinyin)\n\(seed.japanese)"
            )
        )
    }

    // MARK: - Beginner reading

    private struct TextSeed {
        var chinese: String
        var pinyin: String
        var japanese: String
    }

    private struct ChoiceQuestionSeed {
        var instruction: String
        var options: [String]
        var correctIndex: Int
        var explanation: String
    }

    private struct AnnotationSeed {
        var hanzi: String
        var pinyin: String
        var japanese: String
    }

    private struct ReadingSeedSource {
        var id: String
        var title: String
        var level: PracticeHSKLevel
        var genre: PracticePassage.Genre
        var segments: [TextSeed]
        var questions: [ChoiceQuestionSeed]
        var annotations: [AnnotationSeed]
    }

    private static let readingSeeds: [ReadingSeedSource] = [
        .init(
            id: "reading-001", title: "朝の習慣", level: .level1, genre: .narrative,
            segments: [
                .init(chinese: "王明每天六点半起床。", pinyin: "Wáng Míng měitiān liù diǎn bàn qǐchuáng.", japanese: "王明は毎朝6時半に起きます。"),
                .init(chinese: "他先喝一杯水，再去公园跑步。", pinyin: "Tā xiān hē yì bēi shuǐ, zài qù gōngyuán pǎobù.", japanese: "彼はまず水を一杯飲み、それから公園へ走りに行きます。"),
                .init(chinese: "七点半，他回家吃早饭。", pinyin: "Qī diǎn bàn, tā huí jiā chī zǎofàn.", japanese: "7時半に家へ戻って朝食を食べます。")
            ],
            questions: [
                .init(instruction: "王明は何時に起きますか。", options: ["六点", "六点半", "七点半"], correctIndex: 1, explanation: "第1文の「六点半」が答えです。"),
                .init(instruction: "水を飲んだ後、何をしますか。", options: ["跑步", "吃早饭", "看书"], correctIndex: 0, explanation: "「再去公园跑步」とあります。")
            ],
            annotations: [
                .init(hanzi: "起床", pinyin: "qǐchuáng", japanese: "起きる"),
                .init(hanzi: "先", pinyin: "xiān", japanese: "まず"),
                .init(hanzi: "跑步", pinyin: "pǎobù", japanese: "走る、ジョギングする")
            ]
        ),
        .init(
            id: "reading-002", title: "カフェで", level: .level1, genre: .dialogue,
            segments: [
                .init(chinese: "小李问：“你想喝什么？”", pinyin: "Xiǎo Lǐ wèn: “Nǐ xiǎng hē shénme?”", japanese: "李さんは「何を飲みたい？」と聞きます。"),
                .init(chinese: "安娜说：“我要一杯热茶，不要糖。”", pinyin: "Ānnà shuō: “Wǒ yào yì bēi rè chá, bú yào táng.”", japanese: "アンナは「温かいお茶を一杯、砂糖は要りません」と言います。"),
                .init(chinese: "小李要了一杯咖啡。", pinyin: "Xiǎo Lǐ yào le yì bēi kāfēi.", japanese: "李さんはコーヒーを一杯頼みました。")
            ],
            questions: [
                .init(instruction: "安娜は何を飲みますか。", options: ["热茶", "咖啡", "牛奶"], correctIndex: 0, explanation: "安娜は「一杯热茶」と注文しました。"),
                .init(instruction: "安娜が入れないものは何ですか。", options: ["水", "糖", "茶"], correctIndex: 1, explanation: "「不要糖」は砂糖不要という意味です。")
            ],
            annotations: [
                .init(hanzi: "热茶", pinyin: "rè chá", japanese: "温かいお茶"),
                .init(hanzi: "糖", pinyin: "táng", japanese: "砂糖"),
                .init(hanzi: "咖啡", pinyin: "kāfēi", japanese: "コーヒー")
            ]
        ),
        .init(
            id: "reading-003", title: "家族の週末", level: .level1, genre: .narrative,
            segments: [
                .init(chinese: "星期六，爸爸和妈妈去超市。", pinyin: "Xīngqīliù, bàba hé māma qù chāoshì.", japanese: "土曜日、父と母はスーパーへ行きます。"),
                .init(chinese: "我在家做作业，妹妹看电视。", pinyin: "Wǒ zài jiā zuò zuòyè, mèimei kàn diànshì.", japanese: "私は家で宿題をし、妹はテレビを見ます。"),
                .init(chinese: "中午，我们一起吃妈妈做的面条。", pinyin: "Zhōngwǔ, wǒmen yìqǐ chī māma zuò de miàntiáo.", japanese: "昼に、みんなで母が作った麺を食べます。")
            ],
            questions: [
                .init(instruction: "妹は何をしますか。", options: ["做作业", "看电视", "去超市"], correctIndex: 1, explanation: "第2文に「妹妹看电视」とあります。"),
                .init(instruction: "昼食は何ですか。", options: ["米饭", "面条", "饺子"], correctIndex: 1, explanation: "母が作った麺を食べます。")
            ],
            annotations: [
                .init(hanzi: "超市", pinyin: "chāoshì", japanese: "スーパー"),
                .init(hanzi: "作业", pinyin: "zuòyè", japanese: "宿題"),
                .init(hanzi: "面条", pinyin: "miàntiáo", japanese: "麺")
            ]
        ),
        .init(
            id: "reading-004", title: "バス", level: .level1, genre: .dialogue,
            segments: [
                .init(chinese: "我问司机：“这辆车去火车站吗？”", pinyin: "Wǒ wèn sījī: “Zhè liàng chē qù huǒchēzhàn ma?”", japanese: "私は運転手に「このバスは駅へ行きますか」と聞きます。"),
                .init(chinese: "司机说：“去，但是你要在第三站下车。”", pinyin: "Sījī shuō: “Qù, dànshì nǐ yào zài dì sān zhàn xià chē.”", japanese: "運転手は「行きますが、3つ目の停留所で降りてください」と言います。"),
                .init(chinese: "我说：“谢谢，我知道了。”", pinyin: "Wǒ shuō: “Xièxie, wǒ zhīdào le.”", japanese: "私は「ありがとう、分かりました」と言います。")
            ],
            questions: [
                .init(instruction: "「我」はどこへ行きたいですか。", options: ["机场", "火车站", "学校"], correctIndex: 1, explanation: "最初の質問に目的地が示されています。"),
                .init(instruction: "何番目の停留所で降りますか。", options: ["第二站", "第三站", "第四站"], correctIndex: 1, explanation: "運転手は「第三站」と案内しました。")
            ],
            annotations: [
                .init(hanzi: "司机", pinyin: "sījī", japanese: "運転手"),
                .init(hanzi: "火车站", pinyin: "huǒchēzhàn", japanese: "鉄道駅"),
                .init(hanzi: "下车", pinyin: "xià chē", japanese: "乗り物を降りる")
            ]
        ),
        .init(
            id: "reading-005", title: "今日の天気", level: .level1, genre: .informational,
            segments: [
                .init(chinese: "今天上午有点儿冷，下午会暖和一些。", pinyin: "Jīntiān shàngwǔ yǒudiǎnr lěng, xiàwǔ huì nuǎnhuo yìxiē.", japanese: "今朝は少し寒いですが、午後はやや暖かくなります。"),
                .init(chinese: "晚上可能下雨，出门要带伞。", pinyin: "Wǎnshang kěnéng xiàyǔ, chūmén yào dài sǎn.", japanese: "夜は雨の可能性があるので、外出時は傘を持ってください。"),
                .init(chinese: "明天是晴天。", pinyin: "Míngtiān shì qíngtiān.", japanese: "明日は晴れです。")
            ],
            questions: [
                .init(instruction: "いつ雨が降る可能性がありますか。", options: ["上午", "下午", "晚上"], correctIndex: 2, explanation: "「晚上可能下雨」とあります。"),
                .init(instruction: "明日の天気は何ですか。", options: ["晴天", "雨天", "雪天"], correctIndex: 0, explanation: "最後の文に「明天是晴天」とあります。")
            ],
            annotations: [
                .init(hanzi: "暖和", pinyin: "nuǎnhuo", japanese: "暖かい"),
                .init(hanzi: "可能", pinyin: "kěnéng", japanese: "〜かもしれない"),
                .init(hanzi: "伞", pinyin: "sǎn", japanese: "傘")
            ]
        ),
        .init(
            id: "reading-006", title: "新しい友達", level: .level1, genre: .narrative,
            segments: [
                .init(chinese: "班里来了一位新同学，她叫林月。", pinyin: "Bān lǐ lái le yí wèi xīn tóngxué, tā jiào Lín Yuè.", japanese: "クラスに林月という新しい生徒が来ました。"),
                .init(chinese: "她喜欢唱歌，也喜欢打篮球。", pinyin: "Tā xǐhuan chànggē, yě xǐhuan dǎ lánqiú.", japanese: "彼女は歌うこととバスケットボールが好きです。"),
                .init(chinese: "放学后，我和她一起去体育馆。", pinyin: "Fàngxué hòu, wǒ hé tā yìqǐ qù tǐyùguǎn.", japanese: "放課後、私は彼女と体育館へ行きます。")
            ],
            questions: [
                .init(instruction: "新しい生徒の名前は何ですか。", options: ["林月", "王明", "安娜"], correctIndex: 0, explanation: "第1文で名前が紹介されています。"),
                .init(instruction: "放課後、二人はどこへ行きますか。", options: ["图书馆", "体育馆", "饭店"], correctIndex: 1, explanation: "最後の文に「去体育馆」とあります。")
            ],
            annotations: [
                .init(hanzi: "同学", pinyin: "tóngxué", japanese: "同級生、生徒"),
                .init(hanzi: "篮球", pinyin: "lánqiú", japanese: "バスケットボール"),
                .init(hanzi: "体育馆", pinyin: "tǐyùguǎn", japanese: "体育館")
            ]
        ),
        .init(
            id: "reading-007", title: "誕生日プレゼント", level: .level1, genre: .narrative,
            segments: [
                .init(chinese: "今天是奶奶的生日。", pinyin: "Jīntiān shì nǎinai de shēngrì.", japanese: "今日は祖母の誕生日です。"),
                .init(chinese: "妈妈买了一个蛋糕，我画了一张画。", pinyin: "Māma mǎi le yí ge dàngāo, wǒ huà le yì zhāng huà.", japanese: "母はケーキを買い、私は絵を1枚描きました。"),
                .init(chinese: "奶奶看到礼物，非常高兴。", pinyin: "Nǎinai kàndào lǐwù, fēicháng gāoxìng.", japanese: "祖母はプレゼントを見てとても喜びました。")
            ],
            questions: [
                .init(instruction: "母は何を買いましたか。", options: ["花", "蛋糕", "书"], correctIndex: 1, explanation: "母はケーキを買いました。"),
                .init(instruction: "「我」は何を贈りましたか。", options: ["一张画", "一件衣服", "一杯茶"], correctIndex: 0, explanation: "「我画了一张画」とあります。")
            ],
            annotations: [
                .init(hanzi: "生日", pinyin: "shēngrì", japanese: "誕生日"),
                .init(hanzi: "蛋糕", pinyin: "dàngāo", japanese: "ケーキ"),
                .init(hanzi: "礼物", pinyin: "lǐwù", japanese: "プレゼント")
            ]
        ),
        .init(
            id: "reading-008", title: "病院で", level: .level2, genre: .dialogue,
            segments: [
                .init(chinese: "医生问：“你哪儿不舒服？”", pinyin: "Yīshēng wèn: “Nǐ nǎr bù shūfu?”", japanese: "医師は「どこが具合悪いですか」と尋ねます。"),
                .init(chinese: "小周说：“我头疼，还有一点儿发烧。”", pinyin: "Xiǎo Zhōu shuō: “Wǒ tóuténg, hái yǒu yìdiǎnr fāshāo.”", japanese: "周さんは「頭が痛く、少し熱もあります」と言います。"),
                .init(chinese: "医生让他多喝水，今天别去上班。", pinyin: "Yīshēng ràng tā duō hē shuǐ, jīntiān bié qù shàngbān.", japanese: "医師は水を多く飲み、今日は出勤しないよう言いました。")
            ],
            questions: [
                .init(instruction: "小周の症状は何ですか。", options: ["肚子疼", "头疼和发烧", "眼睛疼"], correctIndex: 1, explanation: "頭痛と発熱の2つを述べています。"),
                .init(instruction: "医師は今日どうするよう言いましたか。", options: ["去运动", "去上班", "别去上班"], correctIndex: 2, explanation: "「今天别去上班」とあります。")
            ],
            annotations: [
                .init(hanzi: "舒服", pinyin: "shūfu", japanese: "心地よい、具合がよい"),
                .init(hanzi: "头疼", pinyin: "tóuténg", japanese: "頭が痛い"),
                .init(hanzi: "发烧", pinyin: "fāshāo", japanese: "発熱する")
            ]
        ),
        .init(
            id: "reading-009", title: "新しい部屋", level: .level2, genre: .narrative,
            segments: [
                .init(chinese: "我上个月搬到了一个新房间。", pinyin: "Wǒ shàng ge yuè bān dào le yí ge xīn fángjiān.", japanese: "私は先月、新しい部屋へ引っ越しました。"),
                .init(chinese: "房间不大，但是离公司很近。", pinyin: "Fángjiān bú dà, dànshì lí gōngsī hěn jìn.", japanese: "部屋は広くありませんが、会社にとても近いです。"),
                .init(chinese: "楼下有一家小超市，买东西很方便。", pinyin: "Lóuxià yǒu yì jiā xiǎo chāoshì, mǎi dōngxi hěn fāngbiàn.", japanese: "階下に小さなスーパーがあり、買い物に便利です。")
            ],
            questions: [
                .init(instruction: "新しい部屋の良い点は何ですか。", options: ["很大", "离公司近", "很便宜"], correctIndex: 1, explanation: "会社に近いことが本文に書かれています。"),
                .init(instruction: "階下には何がありますか。", options: ["超市", "公司", "医院"], correctIndex: 0, explanation: "「楼下有一家小超市」とあります。")
            ],
            annotations: [
                .init(hanzi: "搬", pinyin: "bān", japanese: "引っ越す、運ぶ"),
                .init(hanzi: "离", pinyin: "lí", japanese: "〜から（距離が）"),
                .init(hanzi: "方便", pinyin: "fāngbiàn", japanese: "便利だ")
            ]
        ),
        .init(
            id: "reading-010", title: "忘れた傘", level: .level2, genre: .narrative,
            segments: [
                .init(chinese: "早上出门时，天气很好。", pinyin: "Zǎoshang chūmén shí, tiānqì hěn hǎo.", japanese: "朝、家を出るとき天気はとてもよかったです。"),
                .init(chinese: "下午突然下起了大雨，我没带伞。", pinyin: "Xiàwǔ tūrán xià qǐ le dàyǔ, wǒ méi dài sǎn.", japanese: "午後、突然大雨が降り出しましたが、私は傘を持っていませんでした。"),
                .init(chinese: "同事借给我一把伞，所以我没有淋湿。", pinyin: "Tóngshì jiè gěi wǒ yì bǎ sǎn, suǒyǐ wǒ méiyǒu línshī.", japanese: "同僚が傘を貸してくれたので、濡れませんでした。")
            ],
            questions: [
                .init(instruction: "午後の天気はどうなりましたか。", options: ["下大雨", "下雪", "刮大风"], correctIndex: 0, explanation: "午後に突然大雨が降りました。"),
                .init(instruction: "なぜ「我」は濡れませんでしたか。", options: ["坐出租车", "同事借了伞", "雨停了"], correctIndex: 1, explanation: "同僚が傘を貸したからです。")
            ],
            annotations: [
                .init(hanzi: "突然", pinyin: "tūrán", japanese: "突然"),
                .init(hanzi: "借给", pinyin: "jiè gěi", japanese: "〜に貸す"),
                .init(hanzi: "淋湿", pinyin: "línshī", japanese: "雨などで濡れる")
            ]
        ),
        .init(
            id: "reading-011", title: "運動の計画", level: .level2, genre: .dialogue,
            segments: [
                .init(chinese: "小陈最近工作很忙，常常觉得累。", pinyin: "Xiǎo Chén zuìjìn gōngzuò hěn máng, chángcháng juéde lèi.", japanese: "陳さんは最近仕事が忙しく、よく疲れを感じます。"),
                .init(chinese: "朋友建议他每周运动三次。", pinyin: "Péngyou jiànyì tā měi zhōu yùndòng sān cì.", japanese: "友人は週3回運動するよう勧めました。"),
                .init(chinese: "他决定星期一游泳，星期三和星期五跑步。", pinyin: "Tā juédìng xīngqīyī yóuyǒng, xīngqīsān hé xīngqīwǔ pǎobù.", japanese: "彼は月曜に泳ぎ、水曜と金曜に走ることにしました。")
            ],
            questions: [
                .init(instruction: "友人は週に何回運動するよう勧めましたか。", options: ["一次", "两次", "三次"], correctIndex: 2, explanation: "「每周运动三次」とあります。"),
                .init(instruction: "月曜日には何をしますか。", options: ["跑步", "游泳", "休息"], correctIndex: 1, explanation: "月曜日は水泳の予定です。")
            ],
            annotations: [
                .init(hanzi: "建议", pinyin: "jiànyì", japanese: "提案する、勧める"),
                .init(hanzi: "决定", pinyin: "juédìng", japanese: "決める"),
                .init(hanzi: "每周", pinyin: "měi zhōu", japanese: "毎週")
            ]
        ),
        .init(
            id: "reading-012", title: "列車の予約", level: .level2, genre: .dialogue,
            segments: [
                .init(chinese: "我想买星期五去上海的火车票。", pinyin: "Wǒ xiǎng mǎi xīngqīwǔ qù Shànghǎi de huǒchēpiào.", japanese: "私は金曜日の上海行きの列車チケットを買いたいです。"),
                .init(chinese: "上午的票卖完了，只有下午两点的。", pinyin: "Shàngwǔ de piào mài wán le, zhǐyǒu xiàwǔ liǎng diǎn de.", japanese: "午前の券は売り切れで、午後2時のものだけあります。"),
                .init(chinese: "我买了一张下午的票，还选了靠窗的座位。", pinyin: "Wǒ mǎi le yì zhāng xiàwǔ de piào, hái xuǎn le kàochuāng de zuòwèi.", japanese: "私は午後の券を1枚買い、窓側の席も選びました。")
            ],
            questions: [
                .init(instruction: "午前のチケットはどうなりましたか。", options: ["很便宜", "卖完了", "改时间了"], correctIndex: 1, explanation: "「上午的票卖完了」とあります。"),
                .init(instruction: "どの席を選びましたか。", options: ["靠门", "中间", "靠窗"], correctIndex: 2, explanation: "窓側の座席を選びました。")
            ],
            annotations: [
                .init(hanzi: "卖完", pinyin: "mài wán", japanese: "売り切る"),
                .init(hanzi: "靠窗", pinyin: "kào chuāng", japanese: "窓側の"),
                .init(hanzi: "座位", pinyin: "zuòwèi", japanese: "座席")
            ]
        ),
        .init(
            id: "reading-013", title: "スーパーの割引", level: .level2, genre: .informational,
            segments: [
                .init(chinese: "这家超市周末有活动。", pinyin: "Zhè jiā chāoshì zhōumò yǒu huódòng.", japanese: "このスーパーでは週末にキャンペーンがあります。"),
                .init(chinese: "买两公斤水果可以便宜十块钱。", pinyin: "Mǎi liǎng gōngjīn shuǐguǒ kěyǐ piányi shí kuài qián.", japanese: "果物を2キロ買うと10元安くなります。"),
                .init(chinese: "活动只到星期日晚上八点。", pinyin: "Huódòng zhǐ dào xīngqīrì wǎnshang bā diǎn.", japanese: "キャンペーンは日曜の夜8時までです。")
            ],
            questions: [
                .init(instruction: "何を2キロ買うと安くなりますか。", options: ["水果", "蔬菜", "米"], correctIndex: 0, explanation: "割引対象は果物です。"),
                .init(instruction: "キャンペーンはいつ終わりますか。", options: ["星期六晚上", "星期日八点", "星期一早上"], correctIndex: 1, explanation: "日曜日の夜8時までです。")
            ],
            annotations: [
                .init(hanzi: "活动", pinyin: "huódòng", japanese: "行事、キャンペーン"),
                .init(hanzi: "公斤", pinyin: "gōngjīn", japanese: "キログラム"),
                .init(hanzi: "便宜", pinyin: "piányi", japanese: "安い、安くする")
            ]
        ),
        .init(
            id: "reading-014", title: "図書館の案内", level: .level2, genre: .informational,
            segments: [
                .init(chinese: "学校图书馆从早上八点开到晚上九点。", pinyin: "Xuéxiào túshūguǎn cóng zǎoshang bā diǎn kāi dào wǎnshang jiǔ diǎn.", japanese: "学校図書館は朝8時から夜9時まで開いています。"),
                .init(chinese: "学生一次可以借五本书，借书时间是两个星期。", pinyin: "Xuéshēng yí cì kěyǐ jiè wǔ běn shū, jiè shū shíjiān shì liǎng ge xīngqī.", japanese: "学生は一度に5冊、2週間借りられます。"),
                .init(chinese: "图书馆里不能吃东西。", pinyin: "Túshūguǎn lǐ bù néng chī dōngxi.", japanese: "図書館内では食事できません。")
            ],
            questions: [
                .init(instruction: "一度に何冊借りられますか。", options: ["两本", "五本", "九本"], correctIndex: 1, explanation: "学生は一度に5冊借りられます。"),
                .init(instruction: "図書館でしてはいけないことは何ですか。", options: ["看书", "学习", "吃东西"], correctIndex: 2, explanation: "最後の文に飲食禁止とあります。")
            ],
            annotations: [
                .init(hanzi: "图书馆", pinyin: "túshūguǎn", japanese: "図書館"),
                .init(hanzi: "借", pinyin: "jiè", japanese: "借りる"),
                .init(hanzi: "一次", pinyin: "yí cì", japanese: "一度に、一回")
            ]
        ),
        .init(
            id: "reading-015", title: "猫を探す", level: .level2, genre: .narrative,
            segments: [
                .init(chinese: "我的小猫昨天晚上不见了。", pinyin: "Wǒ de xiǎomāo zuótiān wǎnshang bú jiàn le.", japanese: "私の子猫が昨夜いなくなりました。"),
                .init(chinese: "我在小区里找了一个小时，也问了邻居。", pinyin: "Wǒ zài xiǎoqū lǐ zhǎo le yí ge xiǎoshí, yě wèn le línjū.", japanese: "団地内を1時間探し、隣人にも聞きました。"),
                .init(chinese: "最后，邻居在他的车下面找到了它。", pinyin: "Zuìhòu, línjū zài tā de chē xiàmian zhǎodào le tā.", japanese: "最後に、隣人が自分の車の下で猫を見つけました。")
            ],
            questions: [
                .init(instruction: "猫はいついなくなりましたか。", options: ["昨天早上", "昨天晚上", "今天晚上"], correctIndex: 1, explanation: "第1文に「昨天晚上」とあります。"),
                .init(instruction: "猫はどこで見つかりましたか。", options: ["树上", "房间里", "车下面"], correctIndex: 2, explanation: "車の下で見つかりました。")
            ],
            annotations: [
                .init(hanzi: "不见", pinyin: "bú jiàn", japanese: "見当たらない、いなくなる"),
                .init(hanzi: "小区", pinyin: "xiǎoqū", japanese: "住宅団地、住宅区"),
                .init(hanzi: "邻居", pinyin: "línjū", japanese: "隣人")
            ]
        ),
        .init(
            id: "reading-016", title: "地域の清掃活動", level: .level3, genre: .news,
            segments: [
                .init(chinese: "上周六，社区组织了一次公园清扫活动。", pinyin: "Shàng zhōuliù, shèqū zǔzhī le yí cì gōngyuán qīngsǎo huódòng.", japanese: "先週土曜日、地域が公園清掃を企画しました。"),
                .init(chinese: "三十多位居民参加，有人捡垃圾，有人给小树浇水。", pinyin: "Sānshí duō wèi jūmín cānjiā, yǒurén jiǎn lājī, yǒurén gěi xiǎoshù jiāo shuǐ.", japanese: "30人余りの住民が参加し、ごみを拾う人や木に水をやる人がいました。"),
                .init(chinese: "活动结束后，公园变得更干净了，大家也认识了新邻居。", pinyin: "Huódòng jiéshù hòu, gōngyuán biànde gèng gānjìng le, dàjiā yě rènshi le xīn línjū.", japanese: "活動後、公園はきれいになり、皆は新しい隣人とも知り合いました。")
            ],
            questions: [
                .init(instruction: "活動を企画したのは誰ですか。", options: ["学校", "社区", "公司"], correctIndex: 1, explanation: "地域（社区）が企画しました。"),
                .init(instruction: "活動の結果として本文にないものはどれですか。", options: ["公园更干净", "认识新邻居", "种了一百棵树"], correctIndex: 2, explanation: "100本の植樹については書かれていません。")
            ],
            annotations: [
                .init(hanzi: "社区", pinyin: "shèqū", japanese: "地域コミュニティ"),
                .init(hanzi: "居民", pinyin: "jūmín", japanese: "住民"),
                .init(hanzi: "捡垃圾", pinyin: "jiǎn lājī", japanese: "ごみを拾う")
            ]
        ),
        .init(
            id: "reading-017", title: "在宅勤務の日", level: .level3, genre: .narrative,
            segments: [
                .init(chinese: "公司允许员工每周在家工作两天。", pinyin: "Gōngsī yǔnxǔ yuángōng měi zhōu zài jiā gōngzuò liǎng tiān.", japanese: "会社は社員に週2日の在宅勤務を認めています。"),
                .init(chinese: "我选择星期二和星期四，因为这两天会议比较少。", pinyin: "Wǒ xuǎnzé xīngqī'èr hé xīngqīsì, yīnwèi zhè liǎng tiān huìyì bǐjiào shǎo.", japanese: "私は会議が少ない火曜と木曜を選びます。"),
                .init(chinese: "在家工作省下了路上的时间，但我会特别安排午休。", pinyin: "Zài jiā gōngzuò shěngxià le lùshang de shíjiān, dàn wǒ huì tèbié ānpái wǔxiū.", japanese: "在宅勤務で移動時間を節約できますが、昼休みは意識して取ります。")
            ],
            questions: [
                .init(instruction: "在宅勤務は週に何日できますか。", options: ["一天", "两天", "四天"], correctIndex: 1, explanation: "会社は週2日認めています。"),
                .init(instruction: "火曜と木曜を選ぶ理由は何ですか。", options: ["会议少", "天气好", "同事少"], correctIndex: 0, explanation: "その2日は会議が比較的少ないからです。")
            ],
            annotations: [
                .init(hanzi: "允许", pinyin: "yǔnxǔ", japanese: "許可する"),
                .init(hanzi: "省下", pinyin: "shěngxià", japanese: "節約して残す"),
                .init(hanzi: "午休", pinyin: "wǔxiū", japanese: "昼休み")
            ]
        ),
        .init(
            id: "reading-018", title: "お茶の入れ方", level: .level3, genre: .cultural,
            segments: [
                .init(chinese: "泡绿茶时，水温不应该太高。", pinyin: "Pào lǜchá shí, shuǐwēn bù yīnggāi tài gāo.", japanese: "緑茶をいれるとき、お湯の温度は高すぎないほうがよいです。"),
                .init(chinese: "先把热水放一会儿，再倒进杯子里，茶的味道会更柔和。", pinyin: "Xiān bǎ rèshuǐ fàng yíhuìr, zài dào jìn bēizi lǐ, chá de wèidào huì gèng róuhé.", japanese: "湯を少し置いてから杯に注ぐと、お茶の味がよりまろやかになります。"),
                .init(chinese: "不同的茶需要不同的水温和时间。", pinyin: "Bùtóng de chá xūyào bùtóng de shuǐwēn hé shíjiān.", japanese: "茶の種類によって必要な湯温と時間は異なります。")
            ],
            questions: [
                .init(instruction: "緑茶をいれるとき避けるべきことは何ですか。", options: ["水温太高", "使用杯子", "等一会儿"], correctIndex: 0, explanation: "水温を高くしすぎないよう述べています。"),
                .init(instruction: "湯を少し置くとどうなりますか。", options: ["茶更甜", "味道更柔和", "颜色更深"], correctIndex: 1, explanation: "味がよりまろやかになります。")
            ],
            annotations: [
                .init(hanzi: "泡茶", pinyin: "pào chá", japanese: "茶をいれる"),
                .init(hanzi: "水温", pinyin: "shuǐwēn", japanese: "水・湯の温度"),
                .init(hanzi: "柔和", pinyin: "róuhé", japanese: "穏やかだ、まろやかだ")
            ]
        ),
        .init(
            id: "reading-019", title: "変更された旅行計画", level: .level3, genre: .narrative,
            segments: [
                .init(chinese: "我们原来计划周末去爬山。", pinyin: "Wǒmen yuánlái jìhuà zhōumò qù páshān.", japanese: "私たちは当初、週末に山登りへ行く予定でした。"),
                .init(chinese: "天气预报说山区会下大雨，所以大家决定改变计划。", pinyin: "Tiānqì yùbào shuō shānqū huì xià dàyǔ, suǒyǐ dàjiā juédìng gǎibiàn jìhuà.", japanese: "山間部は大雨との予報だったので、皆で予定を変えました。"),
                .init(chinese: "我们改去市里的博物馆，下午还看了一场电影。", pinyin: "Wǒmen gǎi qù shì lǐ de bówùguǎn, xiàwǔ hái kàn le yì chǎng diànyǐng.", japanese: "市内の博物館へ行き、午後は映画も見ました。")
            ],
            questions: [
                .init(instruction: "予定を変えた理由は何ですか。", options: ["有人生病", "山区会下雨", "博物馆免费"], correctIndex: 1, explanation: "山間部の大雨予報が理由です。"),
                .init(instruction: "実際にはどこへ行きましたか。", options: ["博物馆", "山区", "体育馆"], correctIndex: 0, explanation: "市内の博物館へ行きました。")
            ],
            annotations: [
                .init(hanzi: "原来", pinyin: "yuánlái", japanese: "もともと、当初"),
                .init(hanzi: "天气预报", pinyin: "tiānqì yùbào", japanese: "天気予報"),
                .init(hanzi: "改变", pinyin: "gǎibiàn", japanese: "変更する")
            ]
        ),
        .init(
            id: "reading-020", title: "自転車通勤", level: .level3, genre: .opinion,
            segments: [
                .init(chinese: "两个月前，我开始骑自行车上班。", pinyin: "Liǎng ge yuè qián, wǒ kāishǐ qí zìxíngchē shàngbān.", japanese: "2か月前、私は自転車通勤を始めました。"),
                .init(chinese: "虽然路上要多花十分钟，但是每天都有了运动的机会。", pinyin: "Suīrán lùshang yào duō huā shí fēnzhōng, dànshì měitiān dōu yǒu le yùndòng de jīhuì.", japanese: "移動に10分余計にかかりますが、毎日運動する機会ができました。"),
                .init(chinese: "天气不好时我坐地铁，其他时候尽量骑车。", pinyin: "Tiānqì bù hǎo shí wǒ zuò dìtiě, qítā shíhou jǐnliàng qí chē.", japanese: "天気が悪いときは地下鉄に乗り、それ以外はなるべく自転車に乗ります。")
            ],
            questions: [
                .init(instruction: "自転車通勤の利点は何ですか。", options: ["时间更短", "每天能运动", "不用工作"], correctIndex: 1, explanation: "毎日運動する機会が得られる点です。"),
                .init(instruction: "天気が悪いときは何で通勤しますか。", options: ["地铁", "公交车", "出租车"], correctIndex: 0, explanation: "悪天候時は地下鉄に乗ります。")
            ],
            annotations: [
                .init(hanzi: "骑", pinyin: "qí", japanese: "（自転車などに）乗る"),
                .init(hanzi: "机会", pinyin: "jīhuì", japanese: "機会"),
                .init(hanzi: "尽量", pinyin: "jǐnliàng", japanese: "できるだけ")
            ]
        )
    ]

    private static func makeReadingSeed(from seed: ReadingSeedSource) -> PracticeReadingSeed {
        let source = PracticePassage.Source(
            kind: .original,
            title: "My Tianjin オリジナル教材",
            attribution: "My Tianjin"
        )
        let passage = PracticePassage(
            id: seed.id,
            title: seed.title,
            level: seed.level,
            genre: seed.genre,
            segments: seed.segments.enumerated().map { index, segment in
                PracticePassage.Segment(
                    id: "\(seed.id)-segment-\(index + 1)",
                    content: PracticeText(
                        text: segment.chinese,
                        pinyin: segment.pinyin,
                        japanese: segment.japanese
                    )
                )
            },
            estimatedReadingSeconds: max(25, seed.segments.count * 15),
            source: source
        )
        let questions = seed.questions.enumerated().map { questionIndex, question in
            let questionID = "\(seed.id)-question-\(questionIndex + 1)"
            let options = question.options.enumerated().map { optionIndex, text in
                PracticeAnswerOption(
                    id: "\(questionID)-option-\(optionIndex + 1)",
                    content: PracticeText(text: text)
                )
            }
            return PracticeQuestion(
                id: questionID,
                content: .readingComprehension(
                    PracticeReadingQuestion(
                        passageID: seed.id,
                        prompt: PracticePrompt(instruction: question.instruction),
                        answers: PracticeChoiceSet(
                            options: options,
                            correctOptionIDs: [options[question.correctIndex].id]
                        )
                    )
                ),
                metadata: PracticeQuestionMetadata(
                    level: seed.level,
                    skills: [.reading],
                    tags: ["original", "micro-reading"],
                    recommendedDurationSeconds: 35
                ),
                explanation: PracticeAnswerExplanation(summary: question.explanation)
            )
        }
        let annotations = seed.annotations.enumerated().map { index, annotation in
            PracticeVocabularyAnnotation(
                id: "\(seed.id)-word-\(index + 1)",
                hanzi: annotation.hanzi,
                pinyin: annotation.pinyin,
                japanese: annotation.japanese
            )
        }

        return PracticeReadingSeed(
            passage: passage,
            questions: questions,
            vocabularyAnnotations: annotations
        )
    }

    // MARK: - HSK 5-6 production practice

    public static let upperIntermediatePassages: [PracticePassage] = [
        originalPassage(
            id: "hsk5-6-passage-work-hours",
            title: "勤務時間を選べる制度",
            level: .level5,
            genre: .informational,
            segments: [
                PracticeText(
                    text: "一家科技公司去年开始实行弹性工作制，员工可以在早上七点到十点之间选择上班时间。",
                    pinyin: "Yì jiā kējì gōngsī qùnián kāishǐ shíxíng tánxìng gōngzuòzhì, yuángōng kěyǐ zài zǎoshang qī diǎn dào shí diǎn zhījiān xuǎnzé shàngbān shíjiān.",
                    japanese: "あるIT企業は昨年フレックスタイム制を導入し、社員は朝7時から10時の間で始業時刻を選べます。"
                ),
                PracticeText(
                    text: "公司调查发现，大多数员工认为通勤压力减少了，工作效率也有所提高。",
                    pinyin: "Gōngsī diàochá fāxiàn, dàduōshù yuángōng rènwéi tōngqín yālì jiǎnshǎo le, gōngzuò xiàolǜ yě yǒusuǒ tígāo.",
                    japanese: "会社の調査では、多くの社員が通勤ストレスの減少と仕事効率の向上を感じていました。"
                ),
                PracticeText(
                    text: "不过，一些团队也遇到了沟通时间难以统一的问题，因此增加了每天固定的共同办公时段。",
                    pinyin: "Búguò, yìxiē tuánduì yě yùdào le gōutōng shíjiān nányǐ tǒngyī de wèntí, yīncǐ zēngjiā le měitiān gùdìng de gòngtóng bàngōng shíduàn.",
                    japanese: "一方で連絡時間を合わせにくいチームもあり、毎日固定の共通勤務時間を設けました。"
                )
            ]
        )
    ]

    public static var upperIntermediateQuestions: [PracticeQuestion] {
        let errorChoice = choiceSet(
            id: "hsk5-error-001",
            texts: [
                "由于提前做好了准备，我们按时完成了项目。",
                "他不但会说中文，而且对中国历史也很了解。",
                "通过这次志愿活动，使我认识了许多新朋友。",
                "即使明天下雨，活动也会按原计划进行。"
            ],
            correctIndex: 2
        )

        let summaryResponse = PracticeFreeResponseQuestion(
            prompt: PracticePrompt(
                instruction: "本文の要点を中国語80〜120字でまとめてください。利点と課題の両方を含めます。"
            ),
            passageID: "hsk5-6-passage-work-hours",
            responseMode: .written,
            constraints: PracticeResponseConstraints(minimumCharacters: 80, maximumCharacters: 120),
            rubric: writtenRubric,
            referenceAnswer: PracticeText(
                text: "这家公司实行弹性工作制后，员工可以选择上班时间，通勤压力减轻，效率也有所提高。但团队沟通时间不容易统一，因此公司设置了固定的共同办公时段。",
                japanese: "制度の利点、課題、対応策を過不足なくまとめた例。"
            )
        )

        let essayResponse = PracticeFreeResponseQuestion(
            prompt: PracticePrompt(
                instruction: "「オンラインで学ぶことと教室で学ぶこと」を比較し、あなたに合う方法と理由を中国語で述べてください。",
                stimulus: PracticeText(text: "在线学习和课堂学习各有优点。你更适合哪一种？")
            ),
            responseMode: .written,
            constraints: PracticeResponseConstraints(minimumCharacters: 180, maximumCharacters: 260),
            rubric: writtenRubric
        )

        let translationIntoChinese = PracticeFreeResponseQuestion(
            prompt: PracticePrompt(
                instruction: "次の日本語を自然な中国語に訳してください。",
                stimulus: PracticeText(text: "新しい制度が成功するかどうかは、社員が目的を理解し、意見を率直に伝えられるかにかかっている。")
            ),
            responseMode: .written,
            constraints: PracticeResponseConstraints(minimumCharacters: 30, maximumCharacters: 80),
            rubric: translationRubric,
            referenceAnswer: PracticeText(
                text: "新制度能否成功，取决于员工是否理解其目的，并能坦率地表达自己的意见。",
                pinyin: "Xīn zhìdù néngfǒu chénggōng, qǔjué yú yuángōng shìfǒu lǐjiě qí mùdì, bìng néng tǎnshuài de biǎodá zìjǐ de yìjiàn."
            )
        )

        let translationFromChinese = PracticeFreeResponseQuestion(
            prompt: PracticePrompt(
                instruction: "次の中国語を自然な日本語に訳してください。",
                stimulus: PracticeText(text: "与其追求短期的结果，不如建立一个能够长期坚持的学习习惯。")
            ),
            responseMode: .written,
            constraints: PracticeResponseConstraints(minimumCharacters: 25, maximumCharacters: 90),
            rubric: translationRubric,
            referenceAnswer: PracticeText(text: "短期的な成果を求めるよりも、長く続けられる学習習慣を築くほうがよい。")
        )

        let oralResponse = PracticeFreeResponseQuestion(
            prompt: PracticePrompt(
                instruction: "あなたの町で改善してほしい公共サービスを一つ挙げ、理由と具体的な提案を中国語で話してください。"
            ),
            responseMode: .spoken,
            constraints: PracticeResponseConstraints(minimumDurationSeconds: 60, maximumDurationSeconds: 90),
            rubric: spokenRubric
        )

        return [
            PracticeQuestion(
                id: "hsk5-error-001",
                content: .incorrectSentence(
                    PracticeIncorrectSentenceQuestion(
                        prompt: PracticePrompt(instruction: "文法的に不自然な文を一つ選び、自然な形に直してください。"),
                        answers: errorChoice,
                        acceptedCorrections: [
                            "通过这次志愿活动，我认识了许多新朋友。",
                            "这次志愿活动使我认识了许多新朋友。"
                        ]
                    )
                ),
                metadata: PracticeQuestionMetadata(
                    level: .level5,
                    skills: [.grammar, .reading],
                    tags: ["original", "error-correction"],
                    recommendedDurationSeconds: 60
                ),
                explanation: PracticeAnswerExplanation(
                    summary: "誤文：通过这次志愿活动，使我认识了许多新朋友。",
                    details: "「通过」と「使」を同時に使うと主語が欠けます。「通过这次志愿活动，我认识了许多新朋友」または「这次志愿活动使我认识了许多新朋友」とします。"
                )
            ),
            PracticeQuestion(
                id: "hsk5-summary-001",
                content: .summary(summaryResponse),
                metadata: PracticeQuestionMetadata(
                    level: .level5,
                    skills: [.reading, .writing],
                    tags: ["original", "summary"],
                    recommendedDurationSeconds: 480
                )
            ),
            PracticeQuestion(
                id: "hsk5-essay-001",
                content: .essay(essayResponse),
                metadata: PracticeQuestionMetadata(
                    level: .level5,
                    skills: [.writing],
                    tags: ["original", "comparison-essay"],
                    recommendedDurationSeconds: 900
                )
            ),
            PracticeQuestion(
                id: "hsk6-translation-into-001",
                content: .translation(
                    PracticeTranslationQuestion(direction: .intoChinese, response: translationIntoChinese)
                ),
                metadata: PracticeQuestionMetadata(
                    level: .level6,
                    skills: [.translation, .writing],
                    tags: ["original", "japanese-to-chinese"],
                    recommendedDurationSeconds: 300
                )
            ),
            PracticeQuestion(
                id: "hsk6-translation-from-001",
                content: .translation(
                    PracticeTranslationQuestion(direction: .fromChinese, response: translationFromChinese)
                ),
                metadata: PracticeQuestionMetadata(
                    level: .level6,
                    skills: [.translation, .writing],
                    tags: ["original", "chinese-to-japanese"],
                    recommendedDurationSeconds: 300
                )
            ),
            PracticeQuestion(
                id: "hsk6-oral-opinion-001",
                content: .oralOpinion(oralResponse),
                metadata: PracticeQuestionMetadata(
                    level: .level6,
                    skills: [.speaking],
                    tags: ["original", "oral-opinion"],
                    recommendedDurationSeconds: 180
                )
            )
        ]
    }

    // MARK: - Separate HSK 7-9 track

    public static let advancedPassages: [PracticePassage] = [
        originalPassage(
            id: "hsk7-9-passage-public-services",
            title: "デジタル行政と利用格差",
            level: .level7,
            genre: .academic,
            segments: [
                PracticeText(
                    text: "近年来，不少城市把申请证明、预约办事等公共服务转移到了线上平台。",
                    pinyin: "Jìnniánlái, bùshǎo chéngshì bǎ shēnqǐng zhèngmíng, yùyuē bànshì děng gōnggòng fúwù zhuǎnyí dào le xiànshàng píngtái.",
                    japanese: "近年、多くの都市が証明書申請や手続き予約などの公共サービスをオンラインへ移しています。"
                ),
                PracticeText(
                    text: "这种变化缩短了办理时间，也便于政府分析需求并调整资源。",
                    pinyin: "Zhè zhǒng biànhuà suōduǎn le bànlǐ shíjiān, yě biànyú zhèngfǔ fēnxī xūqiú bìng tiáozhěng zīyuán.",
                    japanese: "この変化は処理時間を短縮し、行政が需要を分析して資源を調整しやすくします。"
                ),
                PracticeText(
                    text: "然而，对不熟悉智能设备的人来说，纯线上流程可能形成新的障碍。",
                    pinyin: "Rán'ér, duì bù shúxī zhìnéng shèbèi de rén láishuō, chún xiànshàng liúchéng kěnéng xíngchéng xīn de zhàng'ài.",
                    japanese: "しかしスマート機器に不慣れな人には、完全オンラインの手続きが新たな障壁となり得ます。"
                ),
                PracticeText(
                    text: "因此，提高效率不应等于取消线下渠道，而应让不同群体都能选择适合自己的方式。",
                    pinyin: "Yīncǐ, tígāo xiàolǜ bù yīng děngyú qǔxiāo xiànxià qúdào, ér yīng ràng bùtóng qúntǐ dōu néng xuǎnzé shìhé zìjǐ de fāngshì.",
                    japanese: "したがって効率化は窓口廃止を意味せず、各層が自分に合う方法を選べるようにすべきです。"
                )
            ]
        )
    ]

    public static var advancedQuestions: [PracticeQuestion] {
        let listeningChoice = choiceSet(
            id: "advanced-listening-001",
            texts: [
                "增加树荫和开放公共室内空间可以共同降低高温风险。",
                "居民只需要在家安装空调，不必使用公共设施。",
                "高温天气只影响住在市中心的年轻人。"
            ],
            correctIndex: 0
        )
        let readingChoice = choiceSet(
            id: "advanced-reading-001",
            texts: [
                "所有公共服务都应立即改为纯线上办理。",
                "数字化有效率优势，但还需要保留可选择的线下渠道。",
                "线上平台的主要目的只是收集居民数据。"
            ],
            correctIndex: 1
        )

        let chartResponse = PracticeFreeResponseQuestion(
            prompt: PracticePrompt(
                instruction: "次のデータの主な変化を説明し、考えられる理由を一つ述べてください。",
                stimulus: PracticeText(
                    text: "某市公共交通出行比例：2022年 31%；2023年 36%；2024年 43%。同期私家车出行比例：48%、44%、38%。",
                    japanese: "ある市の公共交通・自家用車の利用比率（2022〜2024年）"
                )
            ),
            responseMode: .written,
            constraints: PracticeResponseConstraints(minimumCharacters: 180, maximumCharacters: 260),
            rubric: writtenRubric
        )
        let argumentResponse = PracticeFreeResponseQuestion(
            prompt: PracticePrompt(
                instruction: "「生成AIを大学教育でどのように扱うべきか」について、立場を明確にし、反対意見にも触れながら論じてください。"
            ),
            responseMode: .written,
            constraints: PracticeResponseConstraints(minimumCharacters: 400, maximumCharacters: 600),
            rubric: writtenRubric
        )
        let writtenInto = translationResponse(
            instruction: "次の日本語を、論説文として自然な中国語に訳してください。",
            stimulus: "効率だけを基準に制度を評価すると、数字には表れにくい負担や、支援を必要とする人々の声を見落とすおそれがある。",
            mode: .written,
            reference: "如果仅以效率为标准评价一项制度，就可能忽视那些难以体现在数字中的负担，以及需要帮助的群体的声音。"
        )
        let writtenFrom = translationResponse(
            instruction: "次の中国語を、論説文として自然な日本語に訳してください。",
            stimulus: "一项政策能否持续，不仅取决于最初的设计是否合理，还取决于执行过程中能否根据反馈及时调整。",
            mode: .written,
            reference: "政策が持続できるかは、当初の設計の妥当性だけでなく、実施中に意見を踏まえて適時に調整できるかにも左右される。"
        )
        let oralInto = translationResponse(
            instruction: "次の日本語を30秒以内で中国語に通訳してください。準備時間は20秒です。",
            stimulus: "本日の会議では結論を急がず、まず各地域で行った試験運用の結果を比較したいと思います。",
            mode: .spoken,
            reference: "在今天的会议上，我们不想急于得出结论，而是希望先比较各地区试点运行的结果。"
        )
        let oralFrom = translationResponse(
            instruction: "次の中国語を30秒以内で日本語に通訳してください。準備時間は20秒です。",
            stimulus: "由于现场人数超过预期，主办方临时开放了另一个会场，并通过网络同步直播。",
            mode: .spoken,
            reference: "会場の人数が予想を上回ったため、主催者は急きょ別会場を開放し、オンラインでも同時配信しました。"
        )
        let paraphraseResponse = PracticeFreeResponseQuestion(
            prompt: PracticePrompt(
                instruction: "内容を保ったまま、より平易な中国語で45〜60秒に言い換えてください。",
                stimulus: PracticeText(text: "技术本身并不会自动带来公平；只有在设计、使用和评估的每个阶段都考虑不同群体的处境，技术进步才可能转化为共同受益。")
            ),
            responseMode: .spoken,
            constraints: PracticeResponseConstraints(minimumDurationSeconds: 45, maximumDurationSeconds: 60),
            rubric: spokenRubric,
            referenceAnswer: PracticeText(text: "新技术不一定让每个人都得到同样的好处。设计和使用技术时，如果能了解不同人的困难，并不断检查结果，更多人才能真正受益。")
        )
        let opinionResponse = PracticeFreeResponseQuestion(
            prompt: PracticePrompt(
                instruction: "都市中心部への自家用車乗り入れに追加料金を課す案について、賛否と条件を2分以内で述べてください。"
            ),
            responseMode: .spoken,
            constraints: PracticeResponseConstraints(minimumDurationSeconds: 90, maximumDurationSeconds: 120),
            rubric: spokenRubric
        )

        return [
            PracticeQuestion(
                id: "advanced-listening-001",
                content: .audioToMeaning(
                    PracticeAudioChoiceQuestion(
                        audio: PracticeText(
                            text: "面对越来越频繁的高温天气，有些城市把重点放在增加绿地和树荫上。研究发现，树木不仅能降低街道表面温度，还能让步行者愿意在户外停留。不过，绿化需要时间才能发挥作用，因此城市还开放了图书馆、社区中心等室内空间，供没有空调的居民临时避暑。",
                            speechText: "面对越来越频繁的高温天气，有些城市把重点放在增加绿地和树荫上。研究发现，树木不仅能降低街道表面温度，还能让步行者愿意在户外停留。不过，绿化需要时间才能发挥作用，因此城市还开放了图书馆、社区中心等室内空间，供没有空调的居民临时避暑。"
                        ),
                        prompt: PracticePrompt(instruction: "音声の主旨として最も適切なものを選んでください。"),
                        answers: listeningChoice
                    )
                ),
                metadata: PracticeQuestionMetadata(
                    level: .level7,
                    skills: [.listening],
                    tags: ["original", "advanced-track", "extended-listening"],
                    recommendedDurationSeconds: 180
                ),
                explanation: PracticeAnswerExplanation(summary: "長期的な緑化と、すぐ使える屋内避暑場所を組み合わせる必要性が主旨です。")
            ),
            PracticeQuestion(
                id: "advanced-reading-001",
                content: .readingComprehension(
                    PracticeReadingQuestion(
                        passageID: "hsk7-9-passage-public-services",
                        prompt: PracticePrompt(instruction: "筆者の立場として最も適切なものを選んでください。"),
                        answers: readingChoice
                    )
                ),
                metadata: PracticeQuestionMetadata(
                    level: .level7,
                    skills: [.reading],
                    tags: ["original", "advanced-track", "extended-reading"],
                    recommendedDurationSeconds: 240
                ),
                explanation: PracticeAnswerExplanation(summary: "効率化を評価しつつ、利用格差を避ける選択肢の確保を主張しています。")
            ),
            PracticeQuestion(
                id: "advanced-chart-001",
                content: .essay(chartResponse),
                metadata: PracticeQuestionMetadata(level: .level7, skills: [.writing], tags: ["original", "advanced-track", "chart-description"], recommendedDurationSeconds: 600)
            ),
            PracticeQuestion(
                id: "advanced-argument-001",
                content: .essay(argumentResponse),
                metadata: PracticeQuestionMetadata(level: .level8, skills: [.writing], tags: ["original", "advanced-track", "argumentative-writing"], recommendedDurationSeconds: 1_800)
            ),
            PracticeQuestion(
                id: "advanced-written-into-001",
                content: .translation(PracticeTranslationQuestion(direction: .intoChinese, response: writtenInto)),
                metadata: PracticeQuestionMetadata(level: .level8, skills: [.translation, .writing], tags: ["original", "advanced-track", "written-translation"], recommendedDurationSeconds: 600)
            ),
            PracticeQuestion(
                id: "advanced-written-from-001",
                content: .translation(PracticeTranslationQuestion(direction: .fromChinese, response: writtenFrom)),
                metadata: PracticeQuestionMetadata(level: .level8, skills: [.translation, .writing], tags: ["original", "advanced-track", "written-translation"], recommendedDurationSeconds: 600)
            ),
            PracticeQuestion(
                id: "advanced-oral-into-001",
                content: .translation(PracticeTranslationQuestion(direction: .intoChinese, response: oralInto)),
                metadata: PracticeQuestionMetadata(level: .level8, skills: [.translation, .speaking], tags: ["original", "advanced-track", "oral-translation"], recommendedDurationSeconds: 90)
            ),
            PracticeQuestion(
                id: "advanced-oral-from-001",
                content: .translation(PracticeTranslationQuestion(direction: .fromChinese, response: oralFrom)),
                metadata: PracticeQuestionMetadata(level: .level8, skills: [.translation, .speaking], tags: ["original", "advanced-track", "oral-translation"], recommendedDurationSeconds: 90)
            ),
            PracticeQuestion(
                id: "advanced-paraphrase-001",
                content: .oralOpinion(paraphraseResponse),
                metadata: PracticeQuestionMetadata(level: .level9, skills: [.reading, .speaking], tags: ["original", "advanced-track", "oral-paraphrase"], recommendedDurationSeconds: 150)
            ),
            PracticeQuestion(
                id: "advanced-opinion-001",
                content: .oralOpinion(opinionResponse),
                metadata: PracticeQuestionMetadata(level: .level9, skills: [.speaking], tags: ["original", "advanced-track", "oral-opinion"], recommendedDurationSeconds: 240)
            )
        ]
    }

    public static let advancedTasks: [HSKAdvancedTrackTask] = [
        .init(id: "task-advanced-listening", kind: .extendedListeningComprehension, title: "長文聴解", instructions: "一度通して聞いた後、主旨を選びます。", questionIDs: ["advanced-listening-001"], recommendedDurationSeconds: 180),
        .init(id: "task-advanced-reading", kind: .extendedReadingComprehension, title: "長文読解", instructions: "論旨と筆者の立場を整理して答えます。", questionIDs: ["advanced-reading-001"], recommendedDurationSeconds: 240),
        .init(id: "task-advanced-chart", kind: .chartDescription, title: "図表説明", instructions: "数値の変化と理由を簡潔に記述します。", questionIDs: ["advanced-chart-001"], recommendedDurationSeconds: 600),
        .init(id: "task-advanced-argument", kind: .argumentativeWriting, supportedLevels: [.level8, .level9], title: "論説作文", instructions: "立場、根拠、反対意見への応答を含めます。", questionIDs: ["advanced-argument-001"], recommendedDurationSeconds: 1_800),
        .init(id: "task-advanced-written-into", kind: .writtenTranslationIntoChinese, supportedLevels: [.level8, .level9], title: "筆記翻訳（日→中）", instructions: "意味と論調を保って中国語に訳します。", questionIDs: ["advanced-written-into-001"], recommendedDurationSeconds: 600),
        .init(id: "task-advanced-written-from", kind: .writtenTranslationFromChinese, supportedLevels: [.level8, .level9], title: "筆記翻訳（中→日）", instructions: "文脈に合う自然な日本語に訳します。", questionIDs: ["advanced-written-from-001"], recommendedDurationSeconds: 600),
        .init(id: "task-advanced-oral-into", kind: .oralTranslationIntoChinese, supportedLevels: [.level8, .level9], title: "口頭通訳（日→中）", instructions: "短い準備時間の後、中国語で伝えます。", questionIDs: ["advanced-oral-into-001"], recommendedDurationSeconds: 90),
        .init(id: "task-advanced-oral-from", kind: .oralTranslationFromChinese, supportedLevels: [.level8, .level9], title: "口頭通訳（中→日）", instructions: "短い準備時間の後、日本語で伝えます。", questionIDs: ["advanced-oral-from-001"], recommendedDurationSeconds: 90),
        .init(id: "task-advanced-paraphrase", kind: .oralParaphrase, supportedLevels: [.level9], title: "口頭言い換え", instructions: "要点を失わず、平易な表現で言い換えます。", questionIDs: ["advanced-paraphrase-001"], recommendedDurationSeconds: 150),
        .init(id: "task-advanced-opinion", kind: .oralOpinion, supportedLevels: [.level9], title: "口頭意見", instructions: "立場、理由、条件を筋道立てて述べます。", questionIDs: ["advanced-opinion-001"], recommendedDurationSeconds: 240)
    ]

    private static func originalPassage(
        id: String,
        title: String,
        level: PracticeHSKLevel,
        genre: PracticePassage.Genre,
        segments: [PracticeText]
    ) -> PracticePassage {
        PracticePassage(
            id: id,
            title: title,
            level: level,
            genre: genre,
            segments: segments.enumerated().map { index, text in
                PracticePassage.Segment(id: "\(id)-segment-\(index + 1)", content: text)
            },
            source: PracticePassage.Source(
                kind: .original,
                title: "My Tianjin オリジナル教材",
                attribution: "My Tianjin"
            )
        )
    }

    private static func choiceSet(id: String, texts: [String], correctIndex: Int) -> PracticeChoiceSet {
        let options = texts.enumerated().map { index, text in
            PracticeAnswerOption(id: "\(id)-option-\(index + 1)", content: PracticeText(text: text))
        }
        return PracticeChoiceSet(options: options, correctOptionIDs: [options[correctIndex].id])
    }

    private static func translationResponse(
        instruction: String,
        stimulus: String,
        mode: PracticeFreeResponseMode,
        reference: String
    ) -> PracticeFreeResponseQuestion {
        let isSpoken = mode == .spoken
        return PracticeFreeResponseQuestion(
            prompt: PracticePrompt(instruction: instruction, stimulus: PracticeText(text: stimulus)),
            responseMode: mode,
            constraints: PracticeResponseConstraints(
                minimumCharacters: isSpoken ? nil : 30,
                maximumCharacters: isSpoken ? nil : 160,
                minimumDurationSeconds: isSpoken ? 15 : nil,
                maximumDurationSeconds: isSpoken ? 30 : nil
            ),
            rubric: mode == .spoken ? spokenRubric : translationRubric,
            referenceAnswer: PracticeText(text: reference)
        )
    }

    private static func rubricCriterion(
        id: String,
        title: String,
        description: String,
        maximumPoints: Int
    ) -> PracticeFreeResponseRubric.Criterion {
        PracticeFreeResponseRubric.Criterion(
            id: id,
            title: title,
            description: description,
            maximumPoints: maximumPoints,
            performanceLevels: [
                .init(points: maximumPoints, label: "達成", descriptor: "基準を一貫して満たしている。"),
                .init(points: maximumPoints / 2, label: "一部達成", descriptor: "基準を部分的に満たすが改善余地がある。"),
                .init(points: 0, label: "要練習", descriptor: "基準を満たす情報がまだ不足している。")
            ]
        )
    }
}
