import Foundation

// Vocabulary source: Chinese Proficiency Test Syllabus (published 2025-11,
// effective 2026-07), HSK Level 1 vocabulary items 1–300.
// https://www.chinesetest.cn/syllabus
// This seed reorders 100 official items for practical daily study.

enum VocabularyUnit: String, CaseIterable, Identifiable, Hashable {
    case greetings = "あいさつ"
    case basics = "基本文"
    case people = "人・自己紹介"
    case numbers = "数字"
    case time = "時間"
    case actions = "動作"
    case food = "食事"
    case places = "場所・移動"
    case descriptions = "表現"
    case practical = "実用会話"

    var id: Self { self }

    var icon: String {
        switch self {
        case .greetings: "hand.wave"
        case .basics: "text.bubble"
        case .people: "person.2"
        case .numbers: "number"
        case .time: "clock"
        case .actions: "figure.walk"
        case .food: "fork.knife"
        case .places: "map"
        case .descriptions: "slider.horizontal.3"
        case .practical: "bubble.left.and.bubble.right"
        }
    }
}

struct VocabularyEntry: Identifiable, Hashable {
    let id: Int
    let officialIndex: Int
    let hanzi: String
    let pinyin: String
    let japanese: String
    let partOfSpeech: String
    let unit: VocabularyUnit
    let example: String
    let examplePinyin: String
    let exampleJapanese: String

    var syllabusLabel: String {
        "新版HSK 1 #\(officialIndex)"
    }
}

enum VocabularySeed {
    static let all: [VocabularyEntry] = {
        func v(
            _ id: Int,
            _ officialIndex: Int,
            _ hanzi: String,
            _ pinyin: String,
            _ japanese: String,
            _ partOfSpeech: String,
            _ unit: VocabularyUnit,
            _ example: String,
            _ examplePinyin: String,
            _ exampleJapanese: String
        ) -> VocabularyEntry {
            VocabularyEntry(
                id: id,
                officialIndex: officialIndex,
                hanzi: hanzi,
                pinyin: pinyin,
                japanese: japanese,
                partOfSpeech: partOfSpeech,
                unit: unit,
                example: example,
                examplePinyin: examplePinyin,
                exampleJapanese: exampleJapanese
            )
        }

        let entries = [
            v(1, 146, "你", "nǐ", "あなた", "代名詞", .greetings, "你好吗？", "Nǐ hǎo ma?", "元気ですか？"),
            v(2, 150, "您", "nín", "あなた（敬称）", "代名詞", .greetings, "您好，老师。", "Nín hǎo, lǎoshī.", "こんにちは、先生。"),
            v(3, 221, "我", "wǒ", "私", "代名詞", .greetings, "我是学生。", "Wǒ shì xuésheng.", "私は学生です。"),
            v(4, 222, "我们", "wǒmen", "私たち", "代名詞", .greetings, "我们学习汉语。", "Wǒmen xuéxí Hànyǔ.", "私たちは中国語を勉強します。"),
            v(5, 148, "你们", "nǐmen", "あなたたち", "代名詞", .greetings, "你们是学生吗？", "Nǐmen shì xuésheng ma?", "あなたたちは学生ですか？"),
            v(6, 200, "他", "tā", "彼", "代名詞", .greetings, "他是老师。", "Tā shì lǎoshī.", "彼は先生です。"),
            v(7, 202, "她", "tā", "彼女", "代名詞", .greetings, "她是我的朋友。", "Tā shì wǒ de péngyou.", "彼女は私の友達です。"),
            v(8, 147, "你好", "nǐhǎo", "こんにちは", "定型表現", .greetings, "你好，我叫小林。", "Nǐhǎo, wǒ jiào Xiǎolín.", "こんにちは、私は小林です。"),
            v(9, 241, "谢谢", "xièxie", "ありがとう", "動詞", .greetings, "谢谢你。", "Xièxie nǐ.", "ありがとう。"),
            v(10, 272, "再见", "zàijiàn", "さようなら", "定型表現", .greetings, "老师，再见。", "Lǎoshī, zàijiàn.", "先生、さようなら。"),

            v(11, 188, "是", "shì", "〜である", "動詞", .basics, "这是茶。", "Zhè shì chá.", "これはお茶です。"),
            v(12, 13, "不", "bù", "〜ない", "副詞", .basics, "我不喝茶。", "Wǒ bù hē chá.", "私はお茶を飲みません。"),
            v(13, 115, "吗", "ma", "〜ですか", "助詞", .basics, "你是学生吗？", "Nǐ shì xuésheng ma?", "あなたは学生ですか？"),
            v(14, 144, "呢", "ne", "〜は？", "助詞", .basics, "我很好，你呢？", "Wǒ hěn hǎo, nǐ ne?", "私は元気です。あなたは？"),
            v(15, 30, "的", "de", "〜の", "助詞", .basics, "这是我的书。", "Zhè shì wǒ de shū.", "これは私の本です。"),
            v(16, 263, "有", "yǒu", "ある・持っている", "動詞", .basics, "我有一本书。", "Wǒ yǒu yì běn shū.", "私は本を一冊持っています。"),
            v(17, 122, "没有", "méiyǒu", "ない・持っていない", "動詞・副詞", .basics, "我没有钱。", "Wǒ méiyǒu qián.", "私はお金を持っていません。"),
            v(18, 279, "这", "zhè", "これ・この", "代名詞", .basics, "这是我的手机。", "Zhè shì wǒ de shǒujī.", "これは私の携帯電話です。"),
            v(19, 136, "那", "nà", "あれ・その", "代名詞", .basics, "那是学校。", "Nà shì xuéxiào.", "あれは学校です。"),
            v(20, 182, "什么", "shénme", "何", "代名詞", .basics, "你想吃什么？", "Nǐ xiǎng chī shénme?", "何を食べたいですか？"),

            v(21, 170, "人", "rén", "人", "名詞", .people, "他是中国人。", "Tā shì Zhōngguó rén.", "彼は中国人です。"),
            v(22, 130, "名字", "míngzi", "名前", "名詞", .people, "你的名字是什么？", "Nǐ de míngzi shì shénme?", "あなたの名前は何ですか？"),
            v(23, 91, "叫", "jiào", "〜という名前である", "動詞", .people, "我叫田中。", "Wǒ jiào Tiánzhōng.", "私は田中といいます。"),
            v(24, 171, "认识", "rènshi", "知り合う・知っている", "動詞", .people, "很高兴认识你。", "Hěn gāoxìng rènshi nǐ.", "お会いできてうれしいです。"),
            v(25, 156, "朋友", "péngyou", "友達", "名詞", .people, "他是我的朋友。", "Tā shì wǒ de péngyou.", "彼は私の友達です。"),
            v(26, 87, "家人", "jiārén", "家族", "名詞", .people, "我的家人在中国。", "Wǒ de jiārén zài Zhōngguó.", "私の家族は中国にいます。"),
            v(27, 3, "爸爸", "bàba", "お父さん", "名詞", .people, "我爸爸在家。", "Wǒ bàba zài jiā.", "父は家にいます。"),
            v(28, 114, "妈妈", "māma", "お母さん", "名詞", .people, "我妈妈在公司工作。", "Wǒ māma zài gōngsī gōngzuò.", "母は会社で働いています。"),
            v(29, 107, "老师", "lǎoshī", "先生", "名詞", .people, "她是汉语老师。", "Tā shì Hànyǔ lǎoshī.", "彼女は中国語の先生です。"),
            v(30, 248, "学生", "xuésheng", "学生", "名詞", .people, "我是大学生。", "Wǒ shì dàxuéshēng.", "私は大学生です。"),

            v(31, 254, "一", "yī", "一・1", "数詞", .numbers, "这里有一个人。", "Zhèlǐ yǒu yí ge rén.", "ここに一人います。"),
            v(32, 49, "二", "èr", "二・2", "数詞", .numbers, "二月很冷。", "Èryuè hěn lěng.", "2月は寒いです。"),
            v(33, 173, "三", "sān", "三・3", "数詞", .numbers, "我买三个苹果。", "Wǒ mǎi sān ge píngguǒ.", "リンゴを三つ買います。"),
            v(34, 198, "四", "sì", "四・4", "数詞", .numbers, "我要四杯茶。", "Wǒ yào sì bēi chá.", "お茶を四杯ください。"),
            v(35, 223, "五", "wǔ", "五・5", "数詞", .numbers, "今天星期五。", "Jīntiān xīngqīwǔ.", "今日は金曜日です。"),
            v(36, 113, "六", "liù", "六・6", "数詞", .numbers, "我六点起床。", "Wǒ liù diǎn qǐchuáng.", "私は6時に起きます。"),
            v(37, 160, "七", "qī", "七・7", "数詞", .numbers, "七月很热。", "Qīyuè hěn rè.", "7月は暑いです。"),
            v(38, 2, "八", "bā", "八・8", "数詞", .numbers, "现在八点。", "Xiànzài bā diǎn.", "今は8時です。"),
            v(39, 95, "九", "jiǔ", "九・9", "数詞", .numbers, "我九点上班。", "Wǒ jiǔ diǎn shàngbān.", "私は9時に出勤します。"),
            v(40, 184, "十", "shí", "十・10", "数詞", .numbers, "这个十元。", "Zhège shí yuán.", "これは10元です。"),

            v(41, 94, "今天", "jīntiān", "今日", "名詞", .time, "今天星期一。", "Jīntiān xīngqīyī.", "今日は月曜日です。"),
            v(42, 129, "明天", "míngtiān", "明日", "名詞", .time, "明天见。", "Míngtiān jiàn.", "また明日。"),
            v(43, 297, "昨天", "zuótiān", "昨日", "名詞", .time, "我昨天去学校。", "Wǒ zuótiān qù xuéxiào.", "私は昨日学校へ行きました。"),
            v(44, 232, "现在", "xiànzài", "今・現在", "名詞", .time, "现在几点？", "Xiànzài jǐ diǎn?", "今、何時ですか？"),
            v(45, 149, "年", "nián", "年", "名詞・量詞", .time, "我学习汉语一年了。", "Wǒ xuéxí Hànyǔ yì nián le.", "中国語を勉強して1年です。"),
            v(46, 269, "月", "yuè", "月", "名詞", .time, "我七月去中国。", "Wǒ qīyuè qù Zhōngguó.", "私は7月に中国へ行きます。"),
            v(47, 76, "号", "hào", "日・号", "名詞・量詞", .time, "今天是八号。", "Jīntiān shì bā hào.", "今日は8日です。"),
            v(48, 243, "星期", "xīngqī", "週・曜日", "名詞", .time, "今天星期几？", "Jīntiān xīngqī jǐ?", "今日は何曜日ですか？"),
            v(49, 178, "上午", "shàngwǔ", "午前", "名詞", .time, "我上午九点上课。", "Wǒ shàngwǔ jiǔ diǎn shàngkè.", "私は午前9時に授業があります。"),
            v(50, 230, "下午", "xiàwǔ", "午後", "名詞", .time, "我们下午三点见。", "Wǒmen xiàwǔ sān diǎn jiàn.", "午後3時に会いましょう。"),

            v(51, 106, "来", "lái", "来る", "動詞", .actions, "他明天来。", "Tā míngtiān lái.", "彼は明日来ます。"),
            v(52, 167, "去", "qù", "行く", "動詞", .actions, "我去学校。", "Wǒ qù xuéxiào.", "私は学校へ行きます。"),
            v(53, 81, "回", "huí", "帰る・戻る", "動詞", .actions, "我下午回家。", "Wǒ xiàwǔ huí jiā.", "私は午後、家に帰ります。"),
            v(54, 99, "看", "kàn", "見る・読む", "動詞", .actions, "我们看电影。", "Wǒmen kàn diànyǐng.", "私たちは映画を見ます。"),
            v(55, 209, "听", "tīng", "聞く", "動詞", .actions, "我听中文歌。", "Wǒ tīng Zhōngwén gē.", "私は中国語の歌を聞きます。"),
            v(56, 196, "说", "shuō", "話す・言う", "動詞", .actions, "我会说汉语。", "Wǒ huì shuō Hànyǔ.", "私は中国語を話せます。"),
            v(57, 42, "读", "dú", "音読する・読む", "動詞", .actions, "请读这个字。", "Qǐng dú zhège zì.", "この字を読んでください。"),
            v(58, 240, "写", "xiě", "書く", "動詞", .actions, "我写汉字。", "Wǒ xiě Hànzì.", "私は漢字を書きます。"),
            v(59, 249, "学习", "xuéxí", "勉強する", "動詞", .actions, "我学习中文。", "Wǒ xuéxí Zhōngwén.", "私は中国語を勉強します。"),
            v(60, 63, "工作", "gōngzuò", "働く・仕事", "動詞・名詞", .actions, "我在公司工作。", "Wǒ zài gōngsī gōngzuò.", "私は会社で働いています。"),

            v(61, 21, "吃", "chī", "食べる", "動詞", .food, "我吃米饭。", "Wǒ chī mǐfàn.", "私はご飯を食べます。"),
            v(62, 77, "喝", "hē", "飲む", "動詞", .food, "我喝茶。", "Wǒ hē chá.", "私はお茶を飲みます。"),
            v(63, 192, "水", "shuǐ", "水", "名詞", .food, "请喝水。", "Qǐng hē shuǐ.", "水をどうぞ。"),
            v(64, 17, "茶", "chá", "お茶", "名詞", .food, "我喜欢喝茶。", "Wǒ xǐhuan hē chá.", "私はお茶を飲むのが好きです。"),
            v(65, 125, "米饭", "mǐfàn", "ご飯", "名詞", .food, "米饭很好吃。", "Mǐfàn hěn hǎochī.", "ご飯はおいしいです。"),
            v(66, 127, "面条儿", "miàntiáor", "麺類", "名詞", .food, "我想吃面条儿。", "Wǒ xiǎng chī miàntiáor.", "麺を食べたいです。"),
            v(67, 90, "饺子", "jiǎozi", "ギョーザ", "名詞", .food, "我们吃饺子。", "Wǒmen chī jiǎozi.", "私たちはギョーザを食べます。"),
            v(68, 8, "包子", "bāozi", "中華まん", "名詞", .food, "这个包子很好吃。", "Zhège bāozi hěn hǎochī.", "この中華まんはおいしいです。"),
            v(69, 159, "苹果", "píngguǒ", "リンゴ", "名詞", .food, "我买三个苹果。", "Wǒ mǎi sān ge píngguǒ.", "リンゴを三つ買います。"),
            v(70, 151, "牛奶", "niúnǎi", "牛乳", "名詞", .food, "我早上喝牛奶。", "Wǒ zǎoshang hē niúnǎi.", "私は朝、牛乳を飲みます。"),

            v(71, 289, "中国", "Zhōngguó", "中国", "固有名詞", .places, "我想去中国。", "Wǒ xiǎng qù Zhōngguó.", "私は中国へ行きたいです。"),
            v(72, 27, "大学", "dàxué", "大学", "名詞", .places, "这是我的大学。", "Zhè shì wǒ de dàxué.", "ここは私の大学です。"),
            v(73, 250, "学校", "xuéxiào", "学校", "名詞", .places, "学校在那边。", "Xuéxiào zài nàbiān.", "学校はあちらです。"),
            v(74, 62, "公司", "gōngsī", "会社", "名詞", .places, "我妈妈在公司。", "Wǒ māma zài gōngsī.", "母は会社にいます。"),
            v(75, 174, "商店", "shāngdiàn", "商店", "名詞", .places, "我去商店买水。", "Wǒ qù shāngdiàn mǎi shuǐ.", "店へ水を買いに行きます。"),
            v(76, 19, "超市", "chāoshì", "スーパー", "名詞", .places, "超市在哪里？", "Chāoshì zài nǎlǐ?", "スーパーはどこですか？"),
            v(77, 51, "饭店", "fàndiàn", "レストラン", "名詞", .places, "我们在饭店吃饭。", "Wǒmen zài fàndiàn chīfàn.", "私たちはレストランで食事をします。"),
            v(78, 257, "医院", "yīyuàn", "病院", "名詞", .places, "医院在这边。", "Yīyuàn zài zhèbiān.", "病院はこちらです。"),
            v(79, 83, "火车", "huǒchē", "列車", "名詞", .places, "我坐火车去。", "Wǒ zuò huǒchē qù.", "私は列車で行きます。"),
            v(80, 22, "出租车", "chūzūchē", "タクシー", "名詞", .places, "我们坐出租车。", "Wǒmen zuò chūzūchē.", "私たちはタクシーに乗ります。"),

            v(81, 71, "好", "hǎo", "よい", "形容詞", .descriptions, "今天天气很好。", "Jīntiān tiānqì hěn hǎo.", "今日は天気がよいです。"),
            v(82, 25, "大", "dà", "大きい", "形容詞", .descriptions, "这个学校很大。", "Zhège xuéxiào hěn dà.", "この学校は大きいです。"),
            v(83, 234, "小", "xiǎo", "小さい", "形容詞", .descriptions, "这个苹果很小。", "Zhège píngguǒ hěn xiǎo.", "このリンゴは小さいです。"),
            v(84, 46, "多", "duō", "多い", "形容詞・代名詞", .descriptions, "这里人很多。", "Zhèlǐ rén hěn duō.", "ここは人が多いです。"),
            v(85, 180, "少", "shǎo", "少ない", "形容詞", .descriptions, "今天人很少。", "Jīntiān rén hěn shǎo.", "今日は人が少ないです。"),
            v(86, 79, "很", "hěn", "とても", "副詞", .descriptions, "我很好。", "Wǒ hěn hǎo.", "私は元気です。"),
            v(87, 206, "太", "tài", "あまりに・とても", "副詞", .descriptions, "这个太贵了。", "Zhège tài guì le.", "これは高すぎます。"),
            v(88, 225, "喜欢", "xǐhuan", "好きである", "動詞", .descriptions, "我喜欢中文。", "Wǒ xǐhuan Zhōngwén.", "私は中国語が好きです。"),
            v(89, 233, "想", "xiǎng", "〜したい・思う", "動詞", .descriptions, "我想喝茶。", "Wǒ xiǎng hē chá.", "私はお茶を飲みたいです。"),
            v(90, 252, "要", "yào", "欲しい・必要である", "動詞", .descriptions, "我要这个。", "Wǒ yào zhège.", "これをください。"),

            v(91, 165, "请", "qǐng", "どうぞ・〜してください", "動詞", .practical, "请坐。", "Qǐng zuò.", "どうぞお座りください。"),
            v(92, 166, "请问", "qǐngwèn", "お尋ねします", "動詞", .practical, "请问，医院在哪里？", "Qǐngwèn, yīyuàn zài nǎlǐ?", "すみません、病院はどこですか？"),
            v(93, 45, "对不起", "duìbuqǐ", "ごめんなさい", "定型表現", .practical, "对不起，我不知道。", "Duìbuqǐ, wǒ bù zhīdào.", "すみません、分かりません。"),
            v(94, 120, "没关系", "méi guānxi", "大丈夫です", "定型表現", .practical, "没关系。", "Méi guānxi.", "大丈夫です。"),
            v(95, 102, "可以", "kěyǐ", "〜してよい・できる", "助動詞", .practical, "可以吗？", "Kěyǐ ma?", "いいですか？"),
            v(96, 47, "多少", "duōshao", "いくつ・いくら", "代名詞", .practical, "这个多少钱？", "Zhège duōshao qián?", "これはいくらですか？"),
            v(97, 164, "钱", "qián", "お金", "名詞", .practical, "我没有钱。", "Wǒ méiyǒu qián.", "私はお金を持っていません。"),
            v(98, 116, "买", "mǎi", "買う", "動詞", .practical, "我想买茶。", "Wǒ xiǎng mǎi chá.", "お茶を買いたいです。"),
            v(99, 282, "这里", "zhèlǐ", "ここ", "代名詞", .practical, "我在这里。", "Wǒ zài zhèlǐ.", "私はここにいます。"),
            v(100, 133, "哪里", "nǎlǐ", "どこ", "代名詞", .practical, "学校在哪里？", "Xuéxiào zài nǎlǐ?", "学校はどこですか？")
        ]

        precondition(entries.count == 100, "The initial vocabulary set must contain 100 entries.")
        precondition(Set(entries.map(\.id)).count == entries.count, "Vocabulary IDs must be unique.")
        precondition(Set(entries.map(\.officialIndex)).count == entries.count, "HSK indices must be unique.")
        precondition(VocabularyUnit.allCases.allSatisfy { unit in
            entries.filter { $0.unit == unit }.count == 10
        }, "Each unit must contain exactly 10 entries.")

        return entries
    }()
}
