import Foundation

@MainActor
final class ScriptedConversationClient: ConversationClient {
    let provider = ConversationProvider.scriptedFallback

    private let configuration: ConversationConfiguration
    private var turnIndex = 0

    init(configuration: ConversationConfiguration) {
        self.configuration = configuration
    }

    func openingReply() -> ConversationReply {
        configuration.scenario.openingReply
    }

    func reply(to learnerText: String) async throws -> ConversationReply {
        let replies = Self.replies(for: configuration.scenario)
        let selected = replies[turnIndex % replies.count]
        turnIndex += 1

        if learnerText.contains("谢谢") || learnerText.contains("谢谢您") {
            return ConversationReply(
                chinese: "不客气！还有什么想说的吗？",
                pinyin: "Bú kèqi! Hái yǒu shénme xiǎng shuō de ma?",
                japanese: "どういたしまして。ほかに何か話したいことはありますか？",
                suggestedReplies: selected.suggestedReplies,
                hintJapanese: selected.hintJapanese
            )
        }
        return selected
    }

    func feedback(for messages: [ConversationMessage]) async throws -> ConversationFeedback {
        let learnerMessages = messages.filter { $0.role == .learner }
        var corrections: [ConversationCorrection] = []

        for message in learnerMessages where corrections.count < 3 {
            if message.chinese.contains("我叫是") {
                corrections.append(ConversationCorrection(
                    originalChinese: message.chinese,
                    correctedChinese: message.chinese.replacingOccurrences(of: "我叫是", with: "我叫"),
                    explanationJapanese: "名前を言う「我叫」の後に「是」は置きません。"
                ))
            } else if message.chinese.contains("我很喜欢非常") {
                corrections.append(ConversationCorrection(
                    originalChinese: message.chinese,
                    correctedChinese: message.chinese.replacingOccurrences(of: "很喜欢非常", with: "非常喜欢"),
                    explanationJapanese: "程度副詞は通常「非常喜欢」の順に置きます。"
                ))
            } else if message.chinese.contains("去在") {
                corrections.append(ConversationCorrection(
                    originalChinese: message.chinese,
                    correctedChinese: message.chinese.replacingOccurrences(of: "去在", with: "在"),
                    explanationJapanese: "場所で行う動作は「在＋場所＋動詞」の語順が基本です。"
                ))
            }
        }

        let positive = learnerMessages.isEmpty
            ? "まずは候補文を声に出して、会話のリズムに慣れていきましょう。"
            : "中国語で会話を最後まで続けられました。短い文でも、相手に返した回数が大きな前進です。"

        return ConversationFeedback(
            positiveNoteJapanese: positive,
            corrections: corrections,
            reviewWords: Self.reviewWords(for: configuration.scenario)
        )
    }

    private static func replies(for scenario: ConversationScenario) -> [ConversationReply] {
        switch scenario {
        case .selfIntroduction:
            [
                reply("认识你很高兴！你从哪儿来？", "Rènshi nǐ hěn gāoxìng! Nǐ cóng nǎr lái?", "お会いできてうれしいです。どちらから来ましたか？", ["我来自日本。", "我是日本人。", "我从东京来。"], "出身は「我来自〜」で言えます。"),
                reply("原来如此。你有什么爱好？", "Yuánlái rúcǐ. Nǐ yǒu shénme àihào?", "そうなんですね。趣味は何ですか？", ["我喜欢看电影。", "我的爱好是旅行。", "我喜欢做饭。"], "趣味は「我喜欢〜」または「我的爱好是〜」です。"),
                reply("听起来很有意思！你为什么学中文？", "Tīng qǐlái hěn yǒuyìsi! Nǐ wèishénme xué Zhōngwén?", "面白そうですね。なぜ中国語を勉強していますか？", ["因为我喜欢中国文化。", "我想去中国旅行。", "工作需要中文。"], "理由は「因为〜」から始められます。"),
                reply("很好！希望你学得越来越好。", "Hěn hǎo! Xīwàng nǐ xué de yuèláiyuè hǎo.", "いいですね。ますます上達することを願っています。", ["谢谢！", "我会继续努力。", "我也很高兴认识你。"], "締めくくりにお礼や意欲を伝えましょう。")
            ]
        case .restaurant:
            [
                reply("好的，请坐。您想喝点儿什么？", "Hǎo de, qǐng zuò. Nín xiǎng hē diǎnr shénme?", "かしこまりました。お掛けください。お飲み物は何にしますか？", ["我要一杯茶。", "请给我水。", "我不喝饮料。"], "注文には「我要〜」や「请给我〜」が使えます。"),
                reply("好的。现在可以点菜吗？", "Hǎo de. Xiànzài kěyǐ diǎn cài ma?", "かしこまりました。今ご注文されますか？", ["可以，我要这个。", "请推荐一下。", "请再等一会儿。"], "「おすすめしてください」は「请推荐一下」です。"),
                reply("您喜欢吃辣的吗？", "Nín xǐhuan chī là de ma?", "辛いものはお好きですか？", ["我喜欢吃辣的。", "请不要太辣。", "我不能吃辣。"], "辛さを控えるなら「不要太辣」と言えます。"),
                reply("好的。还需要别的吗？", "Hǎo de. Hái xūyào bié de ma?", "かしこまりました。ほかに必要なものはありますか？", ["不用了，谢谢。", "请给我一双筷子。", "我要买单。"], "会計は「我要买单」または「结账」です。")
            ]
        case .shopping:
            [
                reply("好的。您喜欢什么颜色？", "Hǎo de. Nín xǐhuan shénme yánsè?", "かしこまりました。何色がお好きですか？", ["我喜欢蓝色。", "有黑色的吗？", "什么颜色都可以。"], "色の在庫は「有〜色的吗？」で聞けます。"),
                reply("有的。您要多大号？", "Yǒu de. Nín yào duō dà hào?", "ございます。サイズはいくつですか？", ["我要中号。", "有小一点儿的吗？", "我可以试一下吗？"], "試着は「我可以试一下吗？」です。"),
                reply("当然可以。这个很适合您。", "Dāngrán kěyǐ. Zhège hěn shìhé nín.", "もちろんです。こちらはとてもお似合いです。", ["这个多少钱？", "有点儿贵。", "我很喜欢。"], "値段は「这个多少钱？」で確認します。"),
                reply("今天有九折优惠。您要买吗？", "Jīntiān yǒu jiǔ zhé yōuhuì. Nín yào mǎi ma?", "今日は1割引です。購入しますか？", ["好，我买了。", "我再考虑一下。", "可以刷卡吗？"], "カード払いは「可以刷卡吗？」です。")
            ]
        case .directions:
            [
                reply("从这里一直往前走。", "Cóng zhèlǐ yìzhí wǎng qián zǒu.", "ここからまっすぐ進んでください。", ["然后呢？", "远不远？", "要走多长时间？"], "所要時間は「要走多长时间？」で聞けます。"),
                reply("到第二个路口向左转。", "Dào dì-èr ge lùkǒu xiàng zuǒ zhuǎn.", "2つ目の交差点で左に曲がってください。", ["向左转，对吗？", "附近有地铁站吗？", "我可以坐公交车吗？"], "確認は文末に「对吗？」を置けます。"),
                reply("走路大约十分钟，也可以坐公交车。", "Zǒulù dàyuē shí fēnzhōng, yě kěyǐ zuò gōngjiāochē.", "徒歩で約10分、バスでも行けます。", ["坐几路车？", "在哪儿上车？", "走路比较方便。"], "バスの路線番号は「坐几路车？」です。"),
                reply("不客气，祝你一路顺利！", "Bú kèqi, zhù nǐ yílù shùnlì!", "どういたしまして。お気をつけて！", ["谢谢您的帮助！", "我明白了。", "再见！"], "案内を理解したら「我明白了」と返せます。")
            ]
        case .dailyLife:
            [
                reply("辛苦了。你下班以后做什么？", "Xīnkǔ le. Nǐ xiàbān yǐhòu zuò shénme?", "お疲れさまです。仕事の後は何をしますか？", ["我回家休息。", "我要去健身房。", "我和朋友吃饭。"], "予定は「我要〜」や「我和〜」で話せます。"),
                reply("听起来不错。你一般几点睡觉？", "Tīng qǐlái búcuò. Nǐ yìbān jǐ diǎn shuìjiào?", "よさそうですね。普段は何時に寝ますか？", ["我十一点睡觉。", "我睡得比较晚。", "我没有固定时间。"], "時刻は「数字＋点」で表します。"),
                reply("明天有什么计划？", "Míngtiān yǒu shénme jìhuà?", "明日は何か予定がありますか？", ["明天我要工作。", "我打算去买东西。", "还没有计划。"], "計画には「打算＋動詞」も使えます。"),
                reply("希望你明天也过得开心！", "Xīwàng nǐ míngtiān yě guò de kāixīn!", "明日も楽しい一日になりますように！", ["谢谢，你也是！", "明天见！", "我也希望如此。"], "「あなたも」は「你也是」です。")
            ]
        case .studyAndWork:
            [
                reply("很棒！你每天学习多长时间？", "Hěn bàng! Nǐ měitiān xuéxí duō cháng shíjiān?", "素晴らしいですね。毎日どのくらい勉強しますか？", ["我每天学习三十分钟。", "周末学得比较多。", "我每天都复习。"], "時間量は「動詞＋時間」の順で言えます。"),
                reply("你觉得哪一部分最难？", "Nǐ juéde nǎ yí bùfen zuì nán?", "どの部分が一番難しいと思いますか？", ["我觉得发音最难。", "语法有一点儿难。", "我需要多练习听力。"], "意見は「我觉得〜」で始められます。"),
                reply("你平时怎么练习？", "Nǐ píngshí zěnme liànxí?", "普段はどのように練習していますか？", ["我用手机学习。", "我和老师练习会话。", "我每天听中文。"], "手段は「用＋道具＋動詞」で説明できます。"),
                reply("这个方法很好。一起加油吧！", "Zhège fāngfǎ hěn hǎo. Yìqǐ jiāyóu ba!", "その方法はいいですね。一緒に頑張りましょう！", ["好，一起加油！", "谢谢你的建议。", "我会继续练习。"], "継続の意志は「我会继续〜」で言えます。")
            ]
        }
    }

    private static func reply(
        _ chinese: String,
        _ pinyin: String,
        _ japanese: String,
        _ suggestions: [String],
        _ hint: String
    ) -> ConversationReply {
        ConversationReply(
            chinese: chinese,
            pinyin: pinyin,
            japanese: japanese,
            suggestedReplies: suggestions,
            hintJapanese: hint
        )
    }

    private static func reviewWords(for scenario: ConversationScenario) -> [String] {
        switch scenario {
        case .selfIntroduction: ["认识", "名字", "爱好", "学习"]
        case .restaurant: ["几位", "点菜", "推荐", "买单"]
        case .shopping: ["颜色", "试", "便宜", "刷卡"]
        case .directions: ["路口", "左转", "附近", "公交车"]
        case .dailyLife: ["今天", "下班", "计划", "休息"]
        case .studyAndWork: ["最近", "练习", "发音", "继续"]
        }
    }
}
