#!/usr/bin/env node

import { readFile, writeFile, mkdir } from "node:fs/promises";
import path from "node:path";

const CONTENT_VERSION = "2026.07.14";
const EXPECTED_BY_LEVEL = {
  "1": 300,
  "2": 200,
  "3": 500,
  "4": 1000,
  "5": 1600,
  "6": 1800,
  "7-9": 5600,
};
const REVIEWED_GLOSS_OVERRIDES = new Map([
  [4, "〜しよう・〜してください・〜でしょう・〜だよね"],
  [6, "百・100"],
  [10, "〜冊（書籍を数える量詞）"],
  [11, "側・端・辺り・〜側・〜の方"],
  [14, "どういたしまして・遠慮しないで"],
  [15, "〜しないで・〜してはいけない"],
  [16, "野菜・料理・おかず"],
  [20, "車・乗り物"],
  [23, "着る・履く（衣類や靴を身につける）"],
  [26, "みんな・皆さん"],
  [29, "着く・到着する・〜まで"],
  [31, "第〜（序数を作る接頭辞）"],
  [33, "時・点・少し（時刻や量）"],
  [35, "電話"],
  [40, "物・もの"],
  [41, "みな・すべて・もう（都…了）"],
  [51, "レストラン・ホテル（地域や名称による）"],
  [55, "分ける・分（時間）・点（得点）・分（1/100元）"],
  [58, "歌"],
  [61, "与える・〜に・〜のために"],
  [65, "（値段が）高い"],
  [67, "まだ・さらに・そのうえ・〜も"],
  [73, "見た目がよい・本や映画などが面白い"],
  [78, "〜と・〜と一緒に"],
  [80, "後ろ・あと・〜後"],
  [81, "帰る・戻る・〜回（動作の回数）"],
  [82, "〜できる・〜するだろう"],
  [85, "いくつ・いくらか・数〜"],
  [86, "家・家庭・家族・〜軒・〜社・〜家（専門家）"],
  [88, "見る・会う"],
  [89, "〜着・〜件・〜点（衣類や事柄などの量詞）"],
  [91, "呼ぶ・〜という名前である・〜に…させる"],
  [93, "今年"],
  [103, "授業・科目"],
  [104, "口・〜人（家族）・〜口（井戸など）の量詞"],
  [111, "二・二つ"],
  [112, "ゼロ・零・端数"],
  [117, "売る"],
  [118, "忙しい"],
  [134, "どこ"],
  [135, "どの〜・どれ（複数）"],
  [136, "あれ・それ・その〜・では・それなら"],
  [138, "あれ・それ・あの〜"],
  [144, "〜は？・〜している・〜なの？"],
  [152, "女・女性・女性の"],
  [155, "女性・〜さん（女性への敬称）"],
  [157, "（値段が）安い・手頃な"],
  [162, "千・1000"],
  [163, "前・前方・以前・〜の前"],
  [166, "すみません、お尋ねします・お聞きします"],
  [169, "（物が）熱い・（天気が）暑い"],
  [175, "上・上方・上がる・登る・乗る・授業などに出る"],
  [190, "本・書籍"],
  [194, "眠る・寝る"],
  [201, "それ（動物や物を指す）"],
  [205, "彼女たち"],
  [210, "聞こえる・耳にする"],
  [211, "クラスメート・同じ学校の学生"],
  [213, "外・外側"],
  [214, "遊ぶ・楽しむ"],
  [218, "もしもし・ねえ（呼びかけ）"],
  [226, "下・下方・下りる・降りる・乗り物から降りる"],
  [231, "〜さん・〜氏（男性への敬称）・夫・ご主人"],
  [247, "学ぶ・習う"],
  [252, "欲しい・〜したい・必要だ・〜しなければならない"],
  [259, "一度・ちょっと・短時間・語気を和らげる表現"],
  [264, "ある人・あるもの・一部の〜"],
  [265, "少し・ちょっと（多くは好ましくない評価）"],
  [268, "元（中国の通貨単位）"],
  [271, "いる・ある・〜に・〜で・〜しているところ"],
  [275, "朝・朝方"],
  [278, "探す・見つける・お釣りを返す"],
  [285, "本当に・実に・本当の・本物の"],
  [288, "知っている・分かっている"],
  [292, "中等学校（中国では初級中学・高級中学を含む）"],
  [293, "中等学校の生徒（中学生・高校生に相当）"],
  [298, "座る・乗り物に乗る"],
  [299, "する・作る"],
  [301, "ああ・えっ・〜ね・〜よ（感嘆や語気）"],
  [302, "趣味・好む・趣味とする"],
  [304, "クラス・班・〜便（交通機関の量詞）"],
  [305, "助ける・手伝う"],
  [307, "包む・覆う・かばん・包み・〜包み・〜袋"],
  [310, "ペン・筆・〜本（筆記具の量詞）"],
  [311, "〜するな・〜しないで"],
  [313, "すみません・申し訳ない・恥ずかしい・気まずい"],
  [314, "長い（時間・距離・長さ）"],
  [316, "出る・出す・現れる・生じる"],
  [319, "出かける・外出する"],
  [322, "単語・語"],
  [323, "〜回・〜度（回数）・次の・劣った"],
  [324, "〜から（場所や時間などの起点）"],
  [326, "間違った・誤っている"],
  [327, "打つ・（電話などを）する"],
  [328, "タクシーを拾う・タクシーに乗る"],
  [329, "開ける・開く・（電源などを）つける"],
  [332, "動詞の後で程度や結果の補語を導く"],
  [334, "待つ"],
  [338, "動く・動かす"],
  [341, "高い・背が高い"],
  [344, "背丈・身長・体つき"],
  [345, "〜と・〜に・ついて行く"],
  [350, "通り過ぎる・過ぎ去る"],
  [352, "やはり・それでも・それとも（選択疑問）"],
  [357, "（時間・お金を）使う"],
  [358, "花・花模様の"],
  [369, "紹介する"],
  [370, "入る・進む"],
  [375, "ホテル"],
  [376, "すぐに・もう・すると・〜なら・ただ〜だけ"],
  [384, "速い・早く・もうすぐ"],
  [395, "緑茶"],
  [403, "面・側・表面・〜の方・〜側・〜面（物事を数える）"],
  [404, "名前・名声・〜名・〜人（人の量詞）"],
  [406, "それほど・そんなに・そのように・では・それなら"],
  [409, "祖母・おばあさん（父方）・年配女性への呼びかけ"],
  [418, "起きる・立ち上がる・〜し始める・〜してみると"],
  [422, "〜させる・許す・譲る・〜に…される（受け身）"],
  [423, "肉・果肉"],
  [425, "上ってくる・上がってくる"],
  [428, "インターネットに接続する・ネットを使う"],
  [431, "時・時間・〜の時・〜時間（時間の単位）"],
  [433, "手・腕前・手段"],
  [437, "贈る・あげる・届ける・送っていく"],
  [439, "だから・そのため"],
  [441, "蹴る"],
  [445, "頭・先・端・〜頭（動物の量詞）"],
  [448, "終える・終わる・〜し終わる"],
  [450, "〜へ・〜の方へ・向かう"],
  [453, "〜名・〜人（人を丁寧に数える量詞）"],
  [459, "下・下側・次・以下"],
  [464, "姓・名字・姓が〜である"],
  [468, "薬"],
  [473, "一緒に・共に"],
  [474, "意味・考え・意図・面白み"],
  [475, "（天気が）曇っている・陰の"],
  [481, "右・右側"],
  [485, "運動する・運動・スポーツ"],
  [486, "駅・停留所"],
  [488, "こんなに・このように"],
  [490, "〜ている・〜たまま（動作や状態の持続）"],
  [491, "ちょうど・まさに・〜しているところ・正しい・まっすぐな"],
  [492, "週・一週間・周囲・一周"],
  [493, "準備する・用意する・〜するつもりだ"],
  [495, "歩く・行く・立ち去る"],
  [506, "〜を（把構文）・〜本／〜束（物を数える）・握る・持つ"],
  [507, "運ぶ・移す・引っ越す"],
  [520, "ノート・メモ・筆記"],
  [521, "比較する・〜と比べて・比較的・わりに"],
  [522, "ノート・ノートパソコン"],
  [524, "試合・競技・競う"],
  [544, "やっと・〜して初めて"],
  [572, "〜するつもりだ・計画する・計画"],
  [578, "持つ・持っていく・連れる・身につける・帯・地域"],
  [593, "電気・電流・感電させる・電話や電報を送る"],
  [594, "エレベーター"],
  [609, "対話する・話し合う"],
  [615, "熱を出す・発熱する"],
  [630, "〜通（手紙などの量詞）・封をする・封鎖する"],
  [635, "〜すべきだ・〜の番だ"],
  [639, "風邪・風邪をひく"],
  [640, "する・働く・担当する"],
  [641, "たった今・〜したばかり・ちょうど"],
  [659, "祝日・祭日を祝う"],
  [660, "過去・以前"],
  [667, "川・河川"],
  [673, "あさって・後天的な"],
  [683, "会議・集まり"],
  [690, "非常に・極めて"],
  [692, "記録する・覚える"],
  [700, "切符を確認する・改札する"],
  [704, "角（1元の10分の1）・角・隅"],
  [708, "節・区切り・〜節（区切りを数える）・祝祭日・節約する"],
  [722, "〜文・〜句（発言や文などの量詞）"],
  [723, "文・一つの文"],
  [725, "カード・カロリー（略）"],
  [731, "〜できる・〜してよい・しかし・本当に（強調）"],
  [745, "年を取った・古い・いつも・老〜（接頭辞）"],
  [753, "涼しい・心地よく涼しい"],
  [755, "話す・おしゃべりする"],
  [761, "階段"],
  [764, "馬"],
  [768, "毛（1元の10分の1）・毛・羽毛"],
  [782, "聞き苦しい・耳障りな・下品な"],
  [790, "恐れる・心配する・おそらく"],
  [804, "鉛筆"],
  [805, "一昨年"],
  [806, "一昨日・おととい"],
  [809, "客を招く・人にごちそうする"],
  [815, "見分けがつく・見覚えがある・知っている"],
  [822, "ソファ"],
  [830, "怒る・腹を立てる"],
  [832, "市・都市"],
  [842, "木・樹木"],
  [846, "水準・レベル・水平"],
  [864, "脚"],
  [870, "遅れる・定刻より遅い"],
  [872, "テニス・テニスボール"],
  [896, "カメラ"],
  [908, "大丈夫だ・よい・できる・行う・進む"],
  [914, "選ぶ・選択する"],
  [924, "一緒に・同じ場所で"],
  [946, "〜に関係する・〜について"],
  [947, "有名な"],
  [958, "〜すればするほど・ますます"],
  [966, "立つ・立ち止まる"],
  [968, "成長する・育つ・〜長（責任者）"],
  [980, "〜しかない・〜だけが・〜して初めて"],
  [991, "自転車"],
  [993, "総じて・いつも・結局"],
  [996, "最もよい・〜したほうがよい"],
  [1009, "白酒（穀物を原料とする中国の蒸留酒）"],
  [1016, "抱く・抱える・抱きしめる"],
  [1024, "大学本科課程・学士課程"],
  [1039, "合わせる・そして・さらに・否定文で決して〜ない"],
  [1042, "博士・博士号取得者"],
  [1050, "部・部門・〜部（書籍や映画や機械などを数える）"],
  [1055, "〜だけでなく・〜のみならず"],
  [1058, "〜ほどよくない・〜に及ばない"],
  [1073, "〜回（試合・催し・試験などを数える）"],
  [1076, "駐車スペース・駐車区画"],
  [1078, "乗る・利用する"],
  [1086, "再び・もう一度・重ねて"],
  [1095, "窓"],
  [1131, "とどまる・滞在する"],
  [1132, "身につける・かぶる・掛ける（装身具など）"],
  [1135, "〜になる・〜を務める・〜の時・〜に際して"],
  [1137, "刀・刃物"],
  [1140, "道・方法・道理・〜本／〜問／〜品などを数える"],
  [1145, "得意げな・誇らしげな・満足している"],
  [1147, "〜など・等級"],
  [1154, "下・下側・〜の下"],
  [1162, "調査する・調べる・アンケートを取る"],
  [1174, "相手・相手方"],
  [1179, "〜回・〜度（食事や叱責などを数える）"],
  [1195, "家主・家の大家"],
  [1203, "〜部・〜通（書類や贈り物などを数える）"],
  [1207, "〜枚（絵や布などを数える）"],
  [1209, "支払う・渡す"],
  [1211, "父と娘"],
  [1224, "〜感（感覚や印象を表す接尾辞）"],
  [1258, "合わせて・全部で・共に"],
  [1268, "掛ける・吊るす・電話を切る・登録する"],
  [1274, "光・明るい・〜だけ・使い果たす・むき出しの"],
  [1291, "きちんと・よく・十分に"],
  [1307, "返事をする・返信する・回復する"],
  [1311, "生きる・生きている・仕事・作業"],
  [1314, "火・火事・人気のある・売れている"],
  [1327, "すでに・〜である以上・〜でもあり…でもある"],
  [1342, "給油する・頑張れ・頑張る"],
  [1345, "偽の・にせの・仮の"],
  [1356, "〜するだろう・〜を（目的語を導く）"],
  [1372, "交通・交通機関・輸送"],
  [1389, "〜にもかかわらず・〜ではあるが・遠慮なく"],
  [1393, "行う・実施する・進める"],
  [1396, "経済・経済的な・費用が少なくて済む"],
  [1407, "いったい・結局のところ"],
  [1430, "グラム（重さの単位）"],
  [1445, "眠い・苦しむ・困窮する・閉じ込める"],
  [1469, "つなぐ・連なる・〜さえ・〜を含めて"],
  [1473, "両（重さの単位）"],
  [1527, "男性・男"],
  [1542, "たたく・拍手する・写真を撮る・撮影する"],
  [1544, "看板・札・ブランド・カード・牌"],
  [1555, "薄片・一切れ・〜枚・〜本（映画などを数える）"],
  [1564, "期・期間・〜期（雑誌や講座などを数える）"],
  [1575, "ぜひ・くれぐれも・決して〜ない"],
  [1578, "前後・前と後・〜ごろ・約〜"],
  [1647, "生の・未熟な・不慣れな・無理に・強引に"],
  [1650, "省・省級行政区"],
  [1667, "大使館・在外公館"],
  [1681, "〜首（詩や歌を数える）"],
  [1688, "熟した・十分に火が通った・慣れている"],
  [1695, "かっこいい・ハンサムな・粋な"],
  [1696, "ついでに・その機会に"],
  [1699, "言い方・表現・見方・説"],
  [1706, "酸っぱい・（体が）だるく痛む"],
  [1712, "孫息子・男の孫"],
  [1713, "すべての・所有する・持っている"],
  [1722, "〜回（往復や移動の回数を数える）"],
  [1731, "思い出させる・注意を促す"],
  [1757, "売り出す・発表する・打ち出す"],
  [1769, "ウェブアドレス・URL"],
  [1776, "においを嗅ぐ・耳にする・聞く"],
  [1823, "情報・知らせ・メッセージ"],
  [1826, "星"],
  [1828, "〜性・〜性質（性質や傾向を表す接尾辞）"],
  [1876, "求人に応募する・採用面接を受ける"],
  [1900, "もともと・以前は・なるほど・実は"],
  [1915, "もう一度言う・後で話す・それに・そのうえ"],
  [1928, "整った・きちんとした・丸ごとの・ちょうど"],
  [1948, "直接の・直接に・まっすぐに"],
  [1975, "正確な・確かな・きっと・必ず・〜してよい"],
  [1980, "〜から・〜より（起点を表す）"],
  [2030, "出勤や到着を届け出る・受付を済ませる"],
  [2040, "本来・もともと・この・当該の"],
  [2056, "すると・そこで・その場合は"],
  [2083, "才能・能力・才能のある人"],
  [2121, "〜に向かって・〜の方へ・向く"],
  [2143, "成人する・大人になる"],
  [2179, "住む・身を置く・付き合う・処置する"],
  [2226, "高層ビル・大きな建物"],
  [2231, "〜より大きい（等号を含まない）"],
  [2244, "薄い・淡い・味が薄い"],
  [2250, "〜と見なす・〜として扱う・質に入れる"],
  [2284, "移す・異動させる・取り寄せる・調べる"],
  [2289, "穴・洞窟"],
  [2293, "豆腐"],
  [2305, "比較する・対照する・比較・対比"],
  [2313, "子ども・息子と娘"],
  [2314, "中古の・二次的な情報の"],
  [2361, "風習・習慣"],
  [2369, "〜組・〜そろい（対の物などを数える）"],
  [2403, "根・根本・〜本（細長い物を数える）"],
  [2459, "ハハッ・あっ（笑いや気づきの声）"],
  [2496, "こぐ・引っかく・傷をつける・割に合う"],
  [2514, "〜組・〜団（人の集団を数える）"],
  [2516, "火鍋・中国式の鍋料理"],
  [2525, "および・ならびに"],
  [2540, "四半期（3か月）"],
  [2542, "記録・最高記録"],
  [2548, "コンピューター・電子計算機"],
  [2589, "付き合う・交流する・交際する"],
  [2657, "見守る・世話をする・番をする"],
  [2763, "道に迷う"],
  [2767, "小麦粉・麺類"],
  [2787, "木材・木・木切れ"],
  [2793, "騒ぐ・騒がせる・もめる・起こす"],
  [2814, "陸上競技のトラック・滑走路"],
  [2822, "たらい・鉢・盆"],
  [2829, "だます・欺く"],
  [2830, "組み合わせる・全力を尽くす・つづる"],
  [2832, "〜品・〜種・味わう・品評する"],
  [2849, "普及させる・広く行き渡らせる"],
  [2851, "期間・〜の間"],
  [2853, "その・それの・彼や彼女らの"],
  [2864, "こちらへ来る・やって来る"],
  [2869, "壁・塀"],
  [2876, "静かに・こっそり・ひそかに"],
  [2899, "権利"],
  [2900, "全力・力の限り"],
  [2921, "人類・人間"],
  [2989, "上がる・昇る・昇進する"],
  [2996, "十二支・生まれ年の動物"],
  [2998, "節約する・省く・省略する"],
  [3000, "省都・省の行政中心地"],
  [3039, "試験する・実験する"],
  [3041, "試用する・試しに使う"],
  [3098, "場所・施設・〜軒／〜校などを数える"],
  [3149, "名詞を作る接尾辞（石头・里头など）"],
  [3184, "〜として・〜に（受け身の動作主）"],
  [3190, "修理する・保守点検する"],
  [3195, "餌をやる・食べさせる"],
  [3214, "色とりどりの・カラフルな"],
  [3248, "農村・田舎"],
  [3266, "販売量・売れた数量"],
  [3315, "アイスクリーム・アイスキャンディー"],
  [3321, "保証金・敷金・デポジット"],
  [3323, "アヒル"],
  [3333, "ベランダ・バルコニー"],
  [3338, "さもなければ・または・〜したらどう？"],
  [3377, "〜すべきだ・〜するのが当然だ"],
  [3402, "これによって・ここから・したがって"],
  [3407, "油条・中国式の揚げパン"],
  [3469, "駅のホーム・プラットホーム"],
  [3475, "アカウント・口座番号"],
  [3481, "誠実な・心からの"],
  [3499, "〜本・〜丁・〜曲などを数える"],
  [3503, "職場・仕事の世界・キャリアの場"],
  [3513, "知恵・英知・知性"],
  [3523, "仲介者・仲介業者・仲介機関"],
  [3539, "竹"],
  [3544, "主人・持ち主・客を迎える側"],
  [3561, "内装する・改装する"],
  [3577, "アルファベットの文字・字母"],
  [3598, "尊敬する・敬う・敬意のある"],
  [3612, "抜け出す・振り払う・脱する"],
  [3614, "訪問する・表敬訪問する"],
  [3622, "保管する・管理する"],
  [3679, "不安な・心配な"],
  [3681, "うまくいかない・だめだ・まさか〜ではないだろうか"],
  [3711, "側・わき・横"],
  [3726, "通常の決まり・慣例・通常の"],
  [3750, "重い・重苦しい・深刻な"],
  [3756, "1割・10分の1（割合を表す）"],
  [3758, "盛る・入れる・容器に入る"],
  [3767, "成語・慣用句（四字とは限らない）"],
  [3771, "尺（約33cm）・物差し"],
  [3779, "〜に向かって・〜に対して"],
  [3809, "串・ひとつながり・〜串／〜組（食べ物などを数える）"],
  [3831, "寸（約3.3cm）・わずかな長さ"],
  [3904, "つるす・持ち上げる・弔う"],
  [3908, "頂・最上部・支える・押し返す・〜頂（物を数える）"],
  [3927, "両手で水平に持つ・差し出す"],
  [3990, "怒った・憤慨した"],
  [3998, "従う・服する・納得する"],
  [4013, "その・当該の・前述の"],
  [4017, "肝臓"],
  [4026, "感想・所感"],
  [4072, "構成する・組み立てる・構造"],
  [4127, "航空・航空輸送"],
  [4156, "後者・後に挙げた方"],
  [4158, "壺・やかん・ポット"],
  [4172, "抱く・思いを抱く・懐に入れる・胸"],
  [4211, "機械・機械装置・機械的な"],
  [4234, "家族・扶養家族"],
  [4235, "〜を…する・〜に処置などを加える"],
  [4239, "（女性が）嫁ぐ・（娘を）嫁がせる"],
  [4253, "概要・簡単な紹介・簡潔に紹介する"],
  [4282, "実を結ぶ・結実する"],
  [4305, "金・黄金"],
  [4310, "近ごろ・最近"],
  [4311, "近視・近視の"],
  [4322, "井戸"],
  [4341, "〜局・〜セット・〜回（試合などを数える）"],
  [4426, "老婦人・おばあさん（敬称）"],
  [4432, "理科・自然科学系"],
  [4444, "ネットワークにつなぐ・オンライン接続する"],
  [4450, "材料・原料・飼料"],
  [4463, "現す・露出する・書き言葉で明らかにする"],
  [4570, "〜皿・〜局・〜巻き（物を数える）・巻く・点検する"],
  [4599, "平方・二乗・平方〜（面積単位）"],
  [4691, "給湯器・湯沸かし器"],
  [4699, "人事・人事業務・世間の出来事"],
  [4704, "認定する・確認する・断定する"],
  [4726, "ばらばらの・散らばった・ほどける"],
  [4727, "散文・散文作品"],
  [4740, "ひらりとよける・きらめく・腰などをひねる"],
  [4747, "だまされる・わなにかかる"],
  [4769, "リットル（容量の単位）"],
  [4827, "樹立する・打ち立てる（模範や権威など）"],
  [4842, "ゆるい・ゆるむ・ゆるめる"],
  [4854, "〜するもの・〜されるもの（動詞句を名詞化）"],
  [4858, "ビリヤード"],
  [4866, "タンユエン（もち米粉の団子）"],
  [4880, "わざわざ・特にそのために"],
  [4890, "天然の・自然由来の・生まれつきの"],
  [4894, "無邪気な・世間知らずの"],
  [4895, "田・畑・田んぼ"],
  [4896, "陸上競技（トラック＆フィールド）"],
  [4898, "飛び込む・飛び込み・価格などが急落する"],
  [4908, "共通して使える・汎用の"],
  [4911, "同業者・同じ業界の人"],
  [4942, "税金を還付する・税金の還付"],
  [4946, "託送する・荷物を預け入れる"],
  [4954, "外科・外科診療"],
  [4956, "姉妹の息子（甥）"],
  [4975, "悔しい・不当な扱いに苦しむ・つらい思いをさせる"],
  [4994, "カメ・リクガメ"],
  [5003, "嫁・息子の妻・くだけた表現で妻"],
  [5017, "オフラインになる・製品がラインオフする"],
  [5020, "以前・先ほど"],
  [5060, "最愛の・大切な"],
  [5083, "袖"],
  [5089, "学会・学術団体"],
  [5090, "学位"],
  [5093, "血管"],
  [5096, "血液"],
  [5109, "炎暑の・焼けつくように暑い"],
  [5111, "研究討議する・検討する"],
  [5116, "まもなく・今にも・成り行きを見守る"],
  [5140, "医薬・医療と薬品"],
  [5157, "ひとしきり・しばらく・一陣・ひと続き"],
  [5164, "順風満帆・物事が順調に進む"],
  [5180, "導く・案内する・指導する"],
  [5224, "元宵節・タンユエン（もち米粉の団子）"],
  [5253, "〜なら・それなら・一方で・すなわち"],
  [5276, "針・注射針・〜針（縫い目を数える）"],
  [5280, "町・鎮・鎮める・抑える"],
  [5301, "職位・役職・ポスト"],
  [5305, "兄弟の息子（甥）"],
  [5341, "〜本・〜株（植物を数える）"],
  [5354, "助手・補助者"],
  [5356, "住宅・住居"],
  [5373, "追及する・詳しく調べる・責任を問う"],
  [5374, "捕まえる・つかむ"],
  [5383, "独り言を言う・ひとりでつぶやく"],
  [5399, "穴を開ける・潜り込む・深く研究する"],
  [5407, "とても気に入り手放せない"],
  [5443, "弱み・付け込む材料"],
  [5455, "あらゆる方法で・何とかして"],
  [5569, "ぴんと張る・張り詰める"],
  [5631, "印を付ける・示す"],
  [5641, "きれいな・器量がよい"],
  [5811, "こする・便乗する・ただで利用する"],
  [5830, "食べたがる・食いしん坊である"],
  [5883, "機会を捉えて・機に乗じて"],
  [5894, "一年中ずっと・一年を通して"],
  [6035, "創始する・創造する"],
  [6080, "寄せ集める・数をそろえる・近づく"],
  [6090, "逃げ回る・（文章を）改ざんする"],
  [6114, "〜から・〜以来"],
  [6246, "抵触する・矛盾する"],
  [6258, "地下道・トンネル"],
  [6292, "彫る・彫刻する"],
  [6298, "調子・音調・曲調・アクセント"],
  [6445, "発芽する・芽を出す"],
  [6460, "帆"],
  [6526, "空飛ぶ円盤・フリスビー"],
  [6568, "春雨・でんぷん麺"],
  [6569, "ファン・愛好者"],
  [6622, "仏・仏陀"],
  [6690, "棒・さお・〜本（細長い物を数える）"],
  [6706, "港湾・港となる湾"],
  [6849, "わざと・ゆえに・したがって"],
  [6850, "雇う・借り上げる"],
  [6915, "カメ"],
  [7015, "息を吐く・叱る"],
  [7018, "穏やかな・調和のとれた"],
  [7136, "化学検査・臨床検査をする"],
  [7148, "遅らせる・和らげる・回復させる"],
  [7157, "荒らす・放置する・おろそかにする"],
  [7191, "壊す・破壊する・中傷する"],
  [7296, "続いて・その後"],
  [7341, "運転する・操縦する・〜台（車などを数える）"],
  [7401, "踏みにじる・蹂躙する"],
  [7458, "乗用車・セダン"],
  [7778, "恐ろしい・怖い"],
  [7897, "とても・非常に・最年長者"],
  [7917, "人気のない分野・番狂わせ"],
  [7985, "とても・かなり"],
  [8081, "露・しずく"],
  [8090, "〜筋・〜条（煙や糸などを数える）"],
  [8119, "しびれた・感覚が麻痺した・ざらついた"],
  [8126, "ヤード（長さの単位）"],
  [8127, "積み上げる・きちんと並べる"],
  [8150, "攻撃・批判の矛先"],
  [8179, "だます・当てずっぽうで答える・気を失う"],
  [8180, "覆う・被る・だます"],
  [8183, "芽生える・発芽する・芽生え"],
  [8252, "命じる・任命する"],
  [8290, "〜幕・〜場面（劇などを数える）"],
  [8327, "掻く・妨げる・くじく"],
  [8400, "うつ伏せになる・身を乗り出す"],
  [8602, "くじ・札・タグ"],
  [8822, "任命する・たとえ〜でも・〜に任せて"],
  [8896, "サロン・談話会・交流会"],
  [8909, "善良な・得意な"],
  [8932, "内熱がこもる・のぼせる・腹を立てる"],
  [9148, "身に余る好意に恐縮する"],
  [9201, "率いる・指揮する"],
  [9341, "祭壇・壇・〜界"],
  [9342, "痰"],
  [9360, "広間・〜回／〜コマ（授業などを数える）"],
  [9432, "好みがうるさい・あら探しする"],
  [9486, "筒・円筒"],
  [9593, "団子・つみれ・丸薬"],
  [9594, "引く・引き止める・取り戻そうとする"],
  [9828, "タンチョウ・丹頂鶴"],
  [9852, "陥る・沈む・罠にはめる"],
  [9980, "オランウータン"],
  [10017, "ショック状態・ショック状態に陥る"],
  [10032, "〜しなければならない・〜する必要がある"],
  [10106, "拘留する・護送する・質に入れる"],
  [10117, "苗を無理に伸ばす・性急に事を進めて逆効果になる"],
]);

function usage() {
  throw new Error(
    "Usage: node Tools/generate_content_packs.mjs <official.json> <cc-cedict-all.js> <Vocabulary.swift> <output-directory> [checkpoint.json]"
  );
}

function decodeSwiftString(value) {
  return JSON.parse(value);
}

function parseLegacyVocabulary(source) {
  const pattern = /v\(\s*(\d+)\s*,\s*(\d+)\s*,\s*("(?:\\.|[^"\\])*")\s*,\s*("(?:\\.|[^"\\])*")\s*,\s*("(?:\\.|[^"\\])*")\s*,\s*("(?:\\.|[^"\\])*")\s*,\s*\.([A-Za-z]+)\s*,\s*("(?:\\.|[^"\\])*")\s*,\s*("(?:\\.|[^"\\])*")\s*,\s*("(?:\\.|[^"\\])*")\s*\)/g;
  const entries = new Map();
  for (const match of source.matchAll(pattern)) {
    const officialIndex = Number(match[2]);
    entries.set(officialIndex, {
      legacyID: Number(match[1]),
      officialIndex,
      hanzi: decodeSwiftString(match[3]),
      pinyin: decodeSwiftString(match[4]),
      japanese: decodeSwiftString(match[5]),
      partOfSpeech: decodeSwiftString(match[6]),
      unit: match[7],
      example: decodeSwiftString(match[8]),
      examplePinyin: decodeSwiftString(match[9]),
      exampleJapanese: decodeSwiftString(match[10]),
    });
  }
  if (entries.size !== 100) {
    throw new Error(`Expected 100 curated legacy entries, found ${entries.size}`);
  }
  return entries;
}

function parseCedict(source) {
  const json = source
    .replace(/^\s*export\s+default\s+/, "")
    .replace(/;?\s*$/, "");
  const all = JSON.parse(json).all;
  const bySimplified = new Map();
  for (const entry of all) {
    const [traditional, simplified, pinyin, english] = entry;
    const definitions = Array.isArray(english) ? english : [english];
    const useful = definitions
      .filter((value) => typeof value === "string" && value.trim())
      .slice(0, 8);
    if (!useful.length) continue;
    const candidate = { traditional, pinyin, definitions: useful };
    const existing = bySimplified.get(simplified) ?? [];
    existing.push(candidate);
    bySimplified.set(simplified, existing);
  }
  return bySimplified;
}

function learnerHanzi(row) {
  return row.hanzi.replace(/[0-9]+$/, "");
}

const PINYIN_TONE_MARKS = new Map(Object.entries({
  ā: ["a", "1"], á: ["a", "2"], ǎ: ["a", "3"], à: ["a", "4"],
  ē: ["e", "1"], é: ["e", "2"], ě: ["e", "3"], è: ["e", "4"],
  ī: ["i", "1"], í: ["i", "2"], ǐ: ["i", "3"], ì: ["i", "4"],
  ō: ["o", "1"], ó: ["o", "2"], ǒ: ["o", "3"], ò: ["o", "4"],
  ū: ["u", "1"], ú: ["u", "2"], ǔ: ["u", "3"], ù: ["u", "4"],
  ǖ: ["v", "1"], ǘ: ["v", "2"], ǚ: ["v", "3"], ǜ: ["v", "4"],
}));

function canonicalPinyin(value) {
  const input = value.toLowerCase().replaceAll("u:", "v").replaceAll("ü", "v");
  let letters = "";
  const tones = [];
  for (const character of input) {
    const marked = PINYIN_TONE_MARKS.get(character);
    if (marked) {
      letters += marked[0];
      tones.push(marked[1]);
    } else if (/[a-zv]/.test(character)) {
      letters += character;
    } else if (/[1-4]/.test(character)) {
      tones.push(character);
    }
  }
  return `${letters}|${tones.join("")}`;
}

function partOfSpeechGuidance(value = "") {
  const mappings = [
    ["名", "noun"],
    ["动", "verb"],
    ["形", "adjective"],
    ["副", "adverb"],
    ["量", "classifier"],
    ["代", "pronoun"],
    ["介", "preposition"],
    ["连", "conjunction"],
    ["助", "particle"],
    ["叹", "interjection"],
    ["数", "numeral"],
    ["拟声", "onomatopoeia"],
    ["后缀", "suffix"],
  ];
  return mappings
    .filter(([marker]) => value.includes(marker))
    .map(([, label]) => label)
    .join(" / ");
}

function englishContext(row, cedict) {
  const entries = cedict.get(learnerHanzi(row)) ?? [];
  const targetPinyin = canonicalPinyin(row.pinyin);
  const pronunciationMatches = entries.filter(
    (entry) => canonicalPinyin(entry.pinyin) === targetPinyin
  );
  const matchedOrFallback = pronunciationMatches.length ? pronunciationMatches : entries;
  const nonProperNameEntries = matchedOrFallback.filter(
    (entry) => entry.pinyin[0] === entry.pinyin[0]?.toLowerCase()
  );
  const selectedEntries = nonProperNameEntries.length ? nonProperNameEntries : matchedOrFallback;
  const definitions = [];
  for (const entry of selectedEntries) {
    for (const definition of entry.definitions) {
      if (/^(?:surname|old variant of|variant of)\b/i.test(definition)) continue;
      if (!definitions.includes(definition)) definitions.push(definition);
      if (definitions.length >= 6) break;
    }
    if (definitions.length >= 6) break;
  }
  return definitions.join("; ").slice(0, 900);
}

async function loadCheckpoint(checkpointPath, curated) {
  let values = {};
  try {
    values = JSON.parse(await readFile(checkpointPath, "utf8"));
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }
  for (const [officialIndex, entry] of curated) {
    values[String(officialIndex)] = {
      japanese: entry.japanese,
      provenance: "curated",
    };
  }
  for (const [officialIndex, japanese] of REVIEWED_GLOSS_OVERRIDES) {
    values[String(officialIndex)] = {
      japanese,
      provenance: "human-reviewed",
    };
  }
  return values;
}

async function saveCheckpoint(checkpointPath, values) {
  await mkdir(path.dirname(checkpointPath), { recursive: true });
  await writeFile(checkpointPath, JSON.stringify(values, null, 2) + "\n");
}

function cleanGloss(row, value) {
  let result = value
    .trim()
    .replace(/[\r\n]+/g, "・")
    .replaceAll("～", "〜")
    .replace(/^(?:[一-龯々]{1,8}(?:詞|語)|動|名|形|副)[：:]\s*/u, "")
    .replace(/[。．]+$/, "");
  result = result
    .replace(/（[ぁ-んァ-ヶー・\s]+）/gu, "")
    .replace(/\s*[（(](?:[一-龯々]{1,8}(?:詞|語)|動|名|形|副)(?:[・/／,，\s]*(?:[一-龯々]{1,8}(?:詞|語)|動|名|形|副))*[）)]/gu, "")
    .trim();
  for (const separator of ["：", ":"]) {
    const prefix = `${learnerHanzi(row)}${separator}`;
    if (result.startsWith(prefix)) {
      result = result.slice(prefix.length).trim();
    }
  }
  return [...new Set(result.split("・").map((part) => part.trim()).filter(Boolean))]
    .join("・")
    .trim();
}

function generatedGlossIssue(gloss) {
  if (!gloss) return "empty gloss";
  if ([...gloss].length > 48) return `gloss is too long (${[...gloss].length} characters)`;
  if (gloss.split("・").length > 6) return "gloss contains more than 6 senses";
  if (/[（(][^）)]*[）)]\s*〜/u.test(gloss)) return "gloss contains an unfinished placeholder";
  if (/[\u0000-\u001f\u007f]/u.test(gloss)) return "gloss contains a control character";
  if (/[\uac00-\ud7af]/u.test(gloss)) return "gloss contains Hangul";
  if (/<0x[0-9a-f]+>/iu.test(gloss)) return "gloss contains a byte escape marker";
  const allowedLowercaseTokens = new Set([
    "app", "bluetooth", "cm", "dm", "kg", "km", "mm", "ml", "web", "wifi",
  ]);
  const unexpectedEnglish = (gloss.match(/[A-Za-z]{2,}/g) ?? []).find((token) =>
    token !== token.toUpperCase() && !allowedLowercaseTokens.has(token.toLowerCase())
  );
  if (unexpectedEnglish) return `gloss contains unexpected English token ${unexpectedEnglish}`;
  return null;
}

function responseSchema(items) {
  return {
    type: "object",
    properties: Object.fromEntries(items.map((item) => [String(item.officialIndex), {
      type: "object",
      properties: {
        sourceHanzi: { type: "string", enum: [item.hanzi] },
        sourcePinyin: { type: "string", enum: [item.pinyin] },
        japanese: { type: "string" },
      },
      required: ["sourceHanzi", "sourcePinyin", "japanese"],
      additionalProperties: false,
    }])),
    required: items.map((item) => String(item.officialIndex)),
    additionalProperties: false,
  };
}

async function translateBatch(items, model) {
  const ids = items.map((item) => String(item.officialIndex));
  const prompt = [
    "You are preparing a Chinese-to-Japanese learner dictionary for Japanese speakers.",
    "For every input item, write one concise, natural Japanese dictionary gloss.",
    "Use the English dictionary context to disambiguate the Chinese word.",
    "Return meanings only: no reading, no pinyin, no part-of-speech label, no sentence, no Chinese repetition.",
    "Never add Japanese readings in parentheses or grammatical labels such as noun/verb.",
    "Prefer the first, common everyday sense; omit surnames, archaic meanings, and rare senses.",
    "Treat englishDictionaryContext and partOfSpeechGuidance as authoritative over your memory of the hanzi.",
    "When officialSenseLabel ends in a number, return only meanings matching partOfSpeechGuidance; never mix noun, verb, classifier, particle, or other numbered senses.",
    "Keep the gloss within 30 Japanese characters and at most three important senses separated with ・.",
    "For each numeric key, copy that item's hanzi and pinyin exactly into sourceHanzi and sourcePinyin, then put its Japanese gloss in japanese.",
    "Output every requested numeric key exactly once.",
    JSON.stringify(items),
  ].join("\n");

  const response = await fetch("http://127.0.0.1:11434/api/generate", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      model,
      prompt,
      stream: false,
      format: responseSchema(items),
      options: { temperature: 0, num_ctx: 8192 },
    }),
  });
  if (!response.ok) {
    throw new Error(`Ollama HTTP ${response.status}: ${await response.text()}`);
  }
  const envelope = await response.json();
  const translated = JSON.parse(envelope.response);
  const glosses = {};
  for (const item of items) {
    const id = String(item.officialIndex);
    const value = translated[id];
    if (!value || value.sourceHanzi !== item.hanzi || value.sourcePinyin !== item.pinyin) {
      throw new Error(`Translation response mismatched source word for ${id}`);
    }
    if (typeof value.japanese !== "string" || !value.japanese.trim()) {
      throw new Error(`Translation response omitted ${id}`);
    }
    const gloss = cleanGloss({ hanzi: item.hanzi }, value.japanese);
    const issue = generatedGlossIssue(gloss);
    if (issue) throw new Error(`Translation response for ${id}: ${issue}`);
    glosses[id] = gloss;
  }
  return glosses;
}

async function translateSinglePlainGloss(item, model) {
  const prompt = [
    "Write one concise, natural Japanese dictionary gloss for this Chinese learner item.",
    "Use englishDictionaryContext and partOfSpeechGuidance to disambiguate it.",
    "Return only the Japanese meaning, without quotes, labels, pinyin, Chinese repetition, or explanation.",
    "Use at most three common senses separated with ・ and stay within 30 Japanese characters.",
    JSON.stringify(item),
  ].join("\n");

  const response = await fetch("http://127.0.0.1:11434/api/generate", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      model,
      prompt,
      stream: false,
      options: { temperature: 0, num_ctx: 4096, num_predict: 128 },
    }),
  });
  if (!response.ok) {
    throw new Error(`Ollama HTTP ${response.status}: ${await response.text()}`);
  }

  const envelope = await response.json();
  const firstLine = String(envelope.response ?? "")
    .trim()
    .replace(/^```(?:text)?\s*/u, "")
    .replace(/\s*```$/u, "")
    .split(/\r?\n/u)
    .find((line) => line.trim())
    ?.trim() ?? "";
  const unlabelled = firstLine
    .replace(/^(?:日本語(?:訳|語義)|訳|意味)[：:]\s*/u, "")
    .replace(/^["「『](.*)["」』]$/u, "$1");
  const gloss = cleanGloss({ hanzi: item.hanzi }, unlabelled);
  const issue = generatedGlossIssue(gloss);
  if (issue) throw new Error(`Plain translation for ${item.officialIndex}: ${issue}`);
  return { [String(item.officialIndex)]: gloss };
}

async function translateBatchWithFallback(items, model, label) {
  let lastError;
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    try {
      return await translateBatch(items, model);
    } catch (error) {
      lastError = error;
      console.warn(`${label}, attempt ${attempt} failed: ${error.message}`);
    }
  }

  if (items.length === 1) {
    for (let attempt = 1; attempt <= 3; attempt += 1) {
      try {
        console.warn(`${label}: trying plain-text fallback for one item`);
        return await translateSinglePlainGloss(items[0], model);
      } catch (error) {
        lastError = error;
        console.warn(`${label}, plain-text attempt ${attempt} failed: ${error.message}`);
      }
    }
    throw lastError;
  }
  const midpoint = Math.ceil(items.length / 2);
  console.warn(`${label}: splitting ${items.length} items after repeated failures`);
  const left = await translateBatchWithFallback(items.slice(0, midpoint), model, `${label}a`);
  const right = await translateBatchWithFallback(items.slice(midpoint), model, `${label}b`);
  return { ...left, ...right };
}

async function generateGlosses(rows, cedict, curated, checkpointPath) {
  const model = process.env.HSK_TRANSLATION_MODEL ?? "gemma4:latest";
  const requestedBatchSize = Number(process.env.HSK_TRANSLATION_BATCH_SIZE ?? 10);
  const batchSize = Math.min(Math.max(requestedBatchSize, 1), 10);
  const values = await loadCheckpoint(checkpointPath, curated);
  for (const row of rows) {
    const existing = values[String(row.officialIndex)];
    if (existing?.provenance === "machine-translated-cc-cedict") {
      const normalizedHanzi = learnerHanzi(row);
      const normalizedPinyin = canonicalPinyin(row.pinyin);
      const dictionaryEntries = cedict.get(normalizedHanzi) ?? [];
      const pronunciationCount = new Set(
        dictionaryEntries.map((entry) => canonicalPinyin(entry.pinyin))
      ).size;
      const hasProperNameVariant = dictionaryEntries.some(
        (entry) => entry.pinyin[0] !== entry.pinyin[0]?.toLowerCase()
      ) && dictionaryEntries.some(
        (entry) => entry.pinyin[0] === entry.pinyin[0]?.toLowerCase()
      );
      const needsPronunciationRefresh = (pronunciationCount > 1 || hasProperNameVariant)
        && (existing.dictionaryContextVersion !== 4 || existing.inputPinyin !== normalizedPinyin);
      const needsNumberedSenseRefresh = normalizedHanzi !== row.hanzi
        && existing.dictionaryContextVersion !== 4;
      if ((normalizedHanzi !== row.hanzi && existing.inputHanzi !== normalizedHanzi)
          || needsPronunciationRefresh
          || needsNumberedSenseRefresh) {
        delete values[String(row.officialIndex)];
      } else {
        existing.japanese = cleanGloss(row, existing.japanese);
        existing.inputHanzi = normalizedHanzi;
        existing.inputPinyin = normalizedPinyin;
        if (generatedGlossIssue(existing.japanese)) {
          delete values[String(row.officialIndex)];
        }
      }
    }
  }
  const pending = rows.filter((row) => !values[String(row.officialIndex)]);
  console.log(`Japanese glosses: ${rows.length - pending.length} ready, ${pending.length} pending`);

  for (let offset = 0; offset < pending.length; offset += batchSize) {
    const batchRows = pending.slice(offset, offset + batchSize);
    const requestItems = batchRows.map((row) => ({
      officialIndex: row.officialIndex,
      hanzi: learnerHanzi(row),
      officialSenseLabel: row.hanzi,
      pinyin: row.pinyin,
      partOfSpeech: row.partOfSpeech ?? "",
      partOfSpeechGuidance: partOfSpeechGuidance(row.partOfSpeech),
      englishDictionaryContext: englishContext(row, cedict),
    }));

    const translated = await translateBatchWithFallback(
      requestItems,
      model,
      `Batch ${offset + 1}-${offset + batchRows.length}`
    );

    for (const row of batchRows) {
      const id = String(row.officialIndex);
      values[id] = {
        japanese: cleanGloss(row, translated[id]),
        provenance: "machine-translated-cc-cedict",
        inputHanzi: learnerHanzi(row),
        inputPinyin: canonicalPinyin(row.pinyin),
        dictionaryContextVersion: 4,
      };
    }
    await saveCheckpoint(checkpointPath, values);
    console.log(`Translated ${Math.min(offset + batchRows.length, pending.length)} / ${pending.length} pending entries`);
  }
  return values;
}

function makeVocabularyItem(row, gloss, curatedEntry) {
  const tags = ["official-hsk", gloss.provenance];
  const hanzi = learnerHanzi(row);
  if (hanzi !== row.hanzi) tags.push(`official-sense-label:${row.hanzi}`);
  const item = {
    id: row.id,
    officialIndex: row.officialIndex,
    hanzi,
    pinyin: row.pinyin,
    japanese: [gloss.japanese],
    tags,
  };
  if (row.partOfSpeech) item.partOfSpeech = row.partOfSpeech;
  if (curatedEntry) {
    item.partOfSpeech = curatedEntry.partOfSpeech;
    item.examples = [{
      id: `${row.id}-example-1`,
      hanzi: curatedEntry.example,
      pinyin: curatedEntry.examplePinyin,
      japanese: curatedEntry.exampleJapanese,
    }];
    item.tags.push(`unit:${curatedEntry.unit}`, `legacy-id:${curatedEntry.legacyID}`);
  }
  return item;
}

async function writePacks(rows, glosses, curated, outputDirectory) {
  await mkdir(outputDirectory, { recursive: true });
  const descriptors = [];
  for (const [level, expectedCount] of Object.entries(EXPECTED_BY_LEVEL)) {
    const levelRows = rows.filter((row) => row.level === level);
    if (levelRows.length !== expectedCount) {
      throw new Error(`Level ${level}: expected ${expectedCount}, found ${levelRows.length}`);
    }
    const id = `hsk3-2025-level-${level}`;
    const resource = `hsk3-2025-level-${level.replace("-", "_")}.json`;
    const pack = {
      schemaVersion: 1,
      id,
      contentVersion: CONTENT_VERSION,
      syllabusVersion: "hsk3.0",
      level,
      source: {
        title: "新版HSK考试大纲（2025）＋CC-CEDICT補助による日本語仮訳",
        url: "https://hsk.cn-bj.ufileos.com/3.0/%E6%96%B0%E7%89%88HSK%E8%80%83%E8%AF%95%E5%A4%A7%E7%BA%B21219.pdf",
        license: "HSK vocabulary indices from the official syllabus. English gloss context from CC-CEDICT (https://www.mdbg.net/chinese/dictionary?page=cc-cedict), CC BY-SA 4.0. Japanese machine translations are marked in item tags.",
      },
      skills: ["vocabulary", "pronunciation", "listening", "reading"],
      vocabulary: levelRows.map((row) => makeVocabularyItem(
        row,
        glosses[String(row.officialIndex)],
        curated.get(row.officialIndex)
      )),
    };
    await writeFile(path.join(outputDirectory, resource), JSON.stringify(pack) + "\n");
    descriptors.push({
      id,
      syllabusVersion: "hsk3.0",
      level,
      resource,
      expectedVocabularyCount: expectedCount,
    });
  }

  const manifest = {
    schemaVersion: 1,
    contentVersion: CONTENT_VERSION,
    packs: descriptors,
  };
  await writeFile(
    path.join(outputDirectory, "content-manifest.json"),
    JSON.stringify(manifest, null, 2) + "\n"
  );
}

async function main() {
  if (process.argv.length < 6 || process.argv.length > 7) usage();
  const [, , officialPath, cedictPath, legacyPath, outputDirectory, checkpointArgument] = process.argv;
  const checkpointPath = checkpointArgument ?? "/tmp/my-tianjin-hsk-japanese-glosses.json";

  const rows = JSON.parse(await readFile(officialPath, "utf8"));
  if (rows.length !== 11_000) throw new Error(`Expected 11000 official rows, found ${rows.length}`);
  const cedict = parseCedict(await readFile(cedictPath, "utf8"));
  const curated = parseLegacyVocabulary(await readFile(legacyPath, "utf8"));
  const glosses = await generateGlosses(rows, cedict, curated, checkpointPath);
  await writePacks(rows, glosses, curated, outputDirectory);
  console.log(`Wrote content packs to ${outputDirectory}`);
}

main().catch((error) => {
  console.error(error.stack ?? error.message);
  process.exitCode = 1;
});
