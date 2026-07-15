#!/usr/bin/env node

import { readFile, writeFile, mkdir } from "node:fs/promises";
import path from "node:path";

const REVIEWED_EXAMPLE_OVERRIDES = new Map([
  ["hsk3-v00007", { hanzi: "我只喝半杯水。", pinyin: "Wǒ zhǐ hē bàn bēi shuǐ.", japanese: "私はコップ半分の水だけ飲みます。" }],
  ["hsk3-v00010", { hanzi: "这本书是我的。", pinyin: "Zhè běn shū shì wǒ de.", japanese: "この本は私のものです。" }],
  ["hsk3-v00011", { hanzi: "你从这边走吧。", pinyin: "Nǐ cóng zhèbiān zǒu ba.", japanese: "こちら側から行ってください。" }],
  ["hsk3-v00012", { hanzi: "他的病好了。", pinyin: "Tā de bìng hǎo le.", japanese: "彼の病気は治りました。" }],
  ["hsk3-v00018", { hanzi: "他会唱歌，但是唱得不太好。", pinyin: "Tā huì chàng gē, dànshì chàng de bú tài hǎo.", japanese: "彼は歌えますが、あまり上手ではありません。" }],
  ["hsk3-v00020", { hanzi: "那辆车是我哥哥的。", pinyin: "Nà liàng chē shì wǒ gēge de.", japanese: "あの車は私の兄のものです。" }],
  ["hsk3-v00040", { hanzi: "你买什么东西？", pinyin: "Nǐ mǎi shénme dōngxi?", japanese: "何を買いますか？" }],
  ["hsk3-v00057", { hanzi: "听到这个消息，她非常高兴。", pinyin: "Tīng dào zhège xiāoxi, tā fēicháng gāoxìng.", japanese: "この知らせを聞いて、彼女はとても喜んでいます。" }],
  ["hsk3-v00060", { hanzi: "请买一个苹果。", pinyin: "Qǐng mǎi yī ge píngguǒ.", japanese: "リンゴを一つ買ってください。" }],
  ["hsk3-v00067", { hanzi: "你还想喝点水吗？", pinyin: "Nǐ hái xiǎng hē diǎn shuǐ ma?", japanese: "もう少し水を飲みたいですか？" }],
  ["hsk3-v00103", { hanzi: "我们明天有汉语课。", pinyin: "Wǒmen míngtiān yǒu Hànyǔ kè.", japanese: "私たちは明日、中国語の授業を受けます。" }],
  ["hsk3-v00104", { hanzi: "我家有三口人。", pinyin: "Wǒ jiā yǒu sān kǒu rén.", japanese: "私の家は3人家族です。" }],
  ["hsk3-v00110", { hanzi: "请你往里走。", pinyin: "Qǐng nǐ wǎng lǐ zǒu.", japanese: "中へお進みください。" }],
  ["hsk3-v00112", { hanzi: "这个电话号码是零七八。", pinyin: "Zhège diànhuà hàomǎ shì líng qī bā.", japanese: "この電話番号は078です。" }],
  ["hsk3-v00124", { hanzi: "学生们都在教室里。", pinyin: "Xuéshengmen dōu zài jiàoshì lǐ.", japanese: "学生たちはみんな教室にいます。" }],
  ["hsk3-v00126", { hanzi: "你饿了吗？吃点面包吧。", pinyin: "Nǐ èle ma? Chī diǎn miànbāo ba.", japanese: "お腹が空いた？少しパンを食べたら？" }],
  ["hsk3-v00132", { hanzi: "哪个是你的书包？", pinyin: "Nǎge shì nǐ de shūbāo?", japanese: "どれがあなたのかばんですか？" }],
  ["hsk3-v00134", { hanzi: "请问，图书馆在哪儿？", pinyin: "Qǐngwèn, túshūguǎn zài nǎr?", japanese: "すみません、図書館はどこですか？" }],
  ["hsk3-v00135", { hanzi: "你知道哪些国家在亚洲吗？", pinyin: "Nǐ zhīdào nǎxiē guójiā zài Yàzhōu ma?", japanese: "どの国がアジアにあるか知っていますか？" }],
  ["hsk3-v00138", { hanzi: "那个是你的书包吗？", pinyin: "Nàge shì nǐ de shūbāo ma?", japanese: "あれはあなたのかばんですか？" }],
  ["hsk3-v00139", { hanzi: "你喜欢去那里玩吗？", pinyin: "Nǐ xǐhuān qù nàlǐ wán ma?", japanese: "あなたはあそこへ遊びに行くのが好きですか？" }],
  ["hsk3-v00140", { hanzi: "请到那儿等我。", pinyin: "Qǐng dào nàr děng wǒ.", japanese: "そこへ行って私を待っていてください。" }],
  ["hsk3-v00141", { hanzi: "那些衣服很漂亮。", pinyin: "Nàxiē yīfu hěn piàoliang.", japanese: "あちらの服はどれもとてもきれいです。" }],
  ["hsk3-v00157", { hanzi: "这个苹果很便宜，你买吧。", pinyin: "Zhège píngguǒ hěn piányi, nǐ mǎi ba.", japanese: "このリンゴはとても安いので、買ったらどうですか。" }],
  ["hsk3-v00161", { hanzi: "我每天早上七点起床，然后洗脸。", pinyin: "Wǒ měitiān zǎoshang qī diǎn qǐchuáng, ránhòu xǐliǎn.", japanese: "私は毎朝7時に起きて、それから顔を洗います。" }],
  ["hsk3-v00162", { hanzi: "这件衣服一千块钱。", pinyin: "Zhè jiàn yīfu yī qiān kuài qián.", japanese: "この服は1000元です。" }],
  ["hsk3-v00169", { hanzi: "今天天气很热，不要忘记带水。", pinyin: "Jīntiān tiānqì hěn rè, bùyào wàngjì dài shuǐ.", japanese: "今日はとても暑いので、水を持っていくのを忘れないでください。" }],
  ["hsk3-v00172", { hanzi: "今天是五月十日。", pinyin: "Jīntiān shì wǔ yuè shí rì.", japanese: "今日は5月10日です。" }],
  ["hsk3-v00177", { hanzi: "你今天下午三点上课吗？", pinyin: "Nǐ jīntiān xiàwǔ sān diǎn shàngkè ma?", japanese: "今日の午後3時に授業がありますか？" }],
  ["hsk3-v00185", { hanzi: "你什么时候有空？我们一起去吃饭吧。", pinyin: "Nǐ shénme shíhou yǒu kòng? Wǒmen yīqǐ qù chīfàn ba.", japanese: "いつ時間がありますか？一緒にご飯を食べに行きましょう。" }],
  ["hsk3-v00189", { hanzi: "我的手机没电了，可以借一下吗？", pinyin: "Wǒ de shǒujī méi diàn le, kěyǐ jiè yīxià ma?", japanese: "私のスマホの充電が切れました。少し貸してもらえますか？" }],
  ["hsk3-v00190", { hanzi: "我买了一本新书。", pinyin: "Wǒ mǎi le yī běn xīn shū.", japanese: "新しい本を1冊買いました。" }],
  ["hsk3-v00203", { hanzi: "他们都是我的好朋友。", pinyin: "Tāmen dōu shì wǒ de hǎo péngyou.", japanese: "彼らはみんな私の仲のよい友達です。" }],
  ["hsk3-v00204", { hanzi: "我家有两只猫，它们都很可爱。", pinyin: "Wǒ jiā yǒu liǎng zhī māo, tāmen dōu hěn kě'ài.", japanese: "私の家には猫が2匹いて、どちらもとてもかわいいです。" }],
  ["hsk3-v00207", { hanzi: "我在北京住了三天。", pinyin: "Wǒ zài Běijīng zhù le sān tiān.", japanese: "私は北京に3日間滞在しました。" }],
  ["hsk3-v00212", { hanzi: "门外有人在等你。", pinyin: "Mén wài yǒu rén zài děng nǐ.", japanese: "ドアの外で誰かがあなたを待っています。" }],
  ["hsk3-v00215", { hanzi: "我今天来晚了一点儿，抱歉。", pinyin: "Wǒ jīntiān lái wǎn le yìdiǎnr, bàoqiàn.", japanese: "今日は少し遅れてしまって、ごめんなさい。" }],
  ["hsk3-v00217", { hanzi: "晚上我们一起去公园玩吧。", pinyin: "Wǎnshang wǒmen yīqǐ qù gōngyuán wán ba.", japanese: "今晩、一緒に公園へ遊びに行きましょう。" }],
  ["hsk3-v00220", { hanzi: "你有什么问题都可以问我。", pinyin: "Nǐ yǒu shénme wèntí dōu kěyǐ wèn wǒ.", japanese: "何か質問があれば、何でも私に聞いてください。" }],
  ["hsk3-v00224", { hanzi: "我们午饭吃什么呢？", pinyin: "Wǒmen wǔfàn chī shénme ne?", japanese: "お昼ご飯は何を食べましょうか？" }],
  ["hsk3-v00235", { hanzi: "那个小朋友很可爱。", pinyin: "Nàge xiǎopéngyǒu hěn kě'ài.", japanese: "あの子供はとてもかわいいです。" }],
  ["hsk3-v00236", { hanzi: "从我家到学校要一个小时。", pinyin: "Cóng wǒ jiā dào xuéxiào yào yí ge xiǎoshí.", japanese: "家から学校まで1時間かかります。" }],
  ["hsk3-v00256", { hanzi: "如果生病了，请去看医生。", pinyin: "Rúguǒ shēngbìng le, qǐng qù kàn yīshēng.", japanese: "病気になったら、医者に診てもらってください。" }],
  ["hsk3-v00258", { hanzi: "我吃了这个苹果的一半。", pinyin: "Wǒ chī le zhège píngguǒ de yíbàn.", japanese: "私はこのリンゴの半分を食べました。" }],
  ["hsk3-v00265", { hanzi: "我有点儿累，想休息一下。", pinyin: "Wǒ yǒudiǎnr lèi, xiǎng xiūxi yíxià.", japanese: "少し疲れたので、休みたいです。" }],
  ["hsk3-v00270", { hanzi: "你明天再来我家玩吧。", pinyin: "Nǐ míngtiān zài lái wǒ jiā wán ba.", japanese: "明日また私の家に遊びに来てください。" }],
  ["hsk3-v00275", { hanzi: "我每天早上七点起床。", pinyin: "Wǒ měitiān zǎoshang qī diǎn qǐchuáng.", japanese: "私は毎朝7時に起きます。" }],
  ["hsk3-v00280", { hanzi: "请问，洗手间在这边吗？", pinyin: "Qǐngwèn, xǐshǒujiān zài zhèbiān ma?", japanese: "すみません、お手洗いはこちらですか？" }],
  ["hsk3-v00284", { hanzi: "这些苹果都很新鲜。", pinyin: "Zhèxiē píngguǒ dōu hěn xīnxiān.", japanese: "これらのリンゴはどれも新鮮です。" }],
  ["hsk3-v00285", { hanzi: "这件衣服真好看。", pinyin: "Zhè jiàn yīfu zhēn hǎokàn.", japanese: "この服は本当にきれいです。" }],
  ["hsk3-v00287", { hanzi: "我家有一只小猫。", pinyin: "Wǒ jiā yǒu yì zhī xiǎo māo.", japanese: "私の家には子猫が1匹います。" }],
  ["hsk3-v00292", { hanzi: "他在中学学习汉语。", pinyin: "Tā zài zhōngxué xuéxí Hànyǔ.", japanese: "彼は中等学校で中国語を勉強しています。" }],
  ["hsk3-v00293", { hanzi: "中学生要多练习写字。", pinyin: "Zhōngxuéshēng yào duō liànxí xiězì.", japanese: "中等学校の生徒は、字を書く練習をたくさんする必要があります。" }],
]);

const MACHINE_EXAMPLE_TAG = "machine-generated-example";
const REVIEWED_EXAMPLE_TAG = "human-reviewed-example";
const EXAMPLE_LICENSE_NOTE =
  "HSK 1 examples tagged machine-generated-example are provisional app-owned drafts.";

function usage() {
  throw new Error(
    "Usage: node Tools/enrich_hsk1_examples.mjs <hsk1-pack.json> [checkpoint.json]"
  );
}

function responseSchema(ids) {
  const example = {
    type: "object",
    properties: {
      hanzi: { type: "string" },
      pinyin: { type: "string" },
      japanese: { type: "string" },
    },
    required: ["hanzi", "pinyin", "japanese"],
    additionalProperties: false,
  };
  return {
    type: "object",
    properties: Object.fromEntries(ids.map((id) => [id, example])),
    required: ids,
    additionalProperties: false,
  };
}

async function loadJSON(filePath, fallback = {}) {
  try {
    return JSON.parse(await readFile(filePath, "utf8"));
  } catch (error) {
    if (error.code === "ENOENT") return fallback;
    throw error;
  }
}

async function saveJSON(filePath, value) {
  await mkdir(path.dirname(filePath), { recursive: true });
  await writeFile(filePath, JSON.stringify(value, null, 2) + "\n");
}

function validateExample(item, example) {
  const targetHanzi = item.hanzi ?? item.targetHanzi;
  if (!example || typeof example !== "object") return "missing object";
  if (typeof example.hanzi !== "string" || !example.hanzi.includes(targetHanzi)) {
    return `sentence does not include ${targetHanzi}`;
  }
  if (example.hanzi.length < 4 || example.hanzi.length > 36) {
    return `sentence length ${example.hanzi.length} is outside 4-36`;
  }
  if (typeof example.pinyin !== "string" || example.pinyin.trim().length < 3) {
    return "missing pinyin";
  }
  if (typeof example.japanese !== "string" || example.japanese.trim().length < 2) {
    return "missing Japanese";
  }
  return null;
}

async function requestExamples(items, model) {
  const ids = items.map((item) => item.id);
  const prompt = [
    "You create beginner Chinese example sentences for Japanese learners.",
    "For each item, write exactly one short, natural Mandarin sentence that contains targetHanzi unchanged.",
    "Prefer HSK 1 vocabulary and a useful everyday context. Do not explain anything.",
    "hanzi: simplified Chinese sentence, about 6-18 Chinese characters.",
    "pinyin: full sentence in Hanyu Pinyin with tone marks and punctuation.",
    "japanese: concise natural Japanese translation.",
    "Return every requested ID exactly once in the required JSON structure.",
    JSON.stringify(items),
  ].join("\n");

  const response = await fetch("http://127.0.0.1:11434/api/generate", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      model,
      prompt,
      stream: false,
      format: responseSchema(ids),
      options: { temperature: 0, num_ctx: 8192 },
    }),
  });
  if (!response.ok) throw new Error(`Ollama HTTP ${response.status}: ${await response.text()}`);
  return JSON.parse((await response.json()).response);
}

async function requestExamplesWithFallback(items, model, label) {
  let lastError;
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    try {
      const output = await requestExamples(items, model);
      for (const item of items) {
        const issue = validateExample(item, output[item.id]);
        if (issue) throw new Error(`${item.id}: ${issue}`);
      }
      return output;
    } catch (error) {
      lastError = error;
      console.warn(`${label}, attempt ${attempt}: ${error.message}`);
    }
  }

  if (items.length === 1) throw lastError;
  const midpoint = Math.ceil(items.length / 2);
  console.warn(`${label}: splitting ${items.length} items after repeated failures`);
  const left = await requestExamplesWithFallback(items.slice(0, midpoint), model, `${label}a`);
  const right = await requestExamplesWithFallback(items.slice(midpoint), model, `${label}b`);
  return { ...left, ...right };
}

async function generateMissing(items, checkpoint, checkpointPath, model, batchSize) {
  const pending = items.filter((item) => !checkpoint[item.id]);
  console.log(`HSK1 examples: ${items.length - pending.length} ready, ${pending.length} pending`);

  for (let offset = 0; offset < pending.length; offset += batchSize) {
    const batch = pending.slice(offset, offset + batchSize);
    const inputs = batch.map((item) => ({
      id: item.id,
      targetHanzi: item.hanzi,
      pinyin: item.pinyin,
      japaneseMeaning: item.japanese[0] ?? "",
      partOfSpeech: item.partOfSpeech ?? "",
    }));

    const output = await requestExamplesWithFallback(
      inputs,
      model,
      `Example batch ${offset + 1}-${offset + batch.length}`
    );

    for (const item of batch) {
      const value = output[item.id];
      checkpoint[item.id] = {
        hanzi: value.hanzi.trim(),
        pinyin: value.pinyin.trim(),
        japanese: value.japanese.trim(),
      };
    }
    await saveJSON(checkpointPath, checkpoint);
    console.log(`Generated ${Math.min(offset + batch.length, pending.length)} / ${pending.length} missing examples`);
  }
}

async function main() {
  if (process.argv.length < 3 || process.argv.length > 4) usage();
  const [, , packPath, checkpointArgument] = process.argv;
  const checkpointPath = checkpointArgument ?? "/tmp/my-tianjin-hsk1-examples.json";
  const model = process.env.HSK_EXAMPLE_MODEL ?? "gemma4:latest";
  const batchSize = Number(process.env.HSK_EXAMPLE_BATCH_SIZE ?? 10);
  const pack = await loadJSON(packPath);
  if (pack.level !== "1" || !Array.isArray(pack.vocabulary) || pack.vocabulary.length !== 300) {
    throw new Error("Expected an HSK 1 pack with exactly 300 vocabulary items");
  }

  const checkpoint = await loadJSON(checkpointPath, {});
  for (const [itemID, example] of REVIEWED_EXAMPLE_OVERRIDES) {
    checkpoint[itemID] = example;
  }
  await saveJSON(checkpointPath, checkpoint);
  const missing = pack.vocabulary.filter((item) => !item.examples?.length);
  await generateMissing(missing, checkpoint, checkpointPath, model, batchSize);

  for (const item of pack.vocabulary) {
    const example = checkpoint[item.id];
    if (!example) continue;
    const issue = validateExample(item, example);
    if (issue) throw new Error(`${item.id}: ${issue}`);
    item.examples = [{
      id: `${item.id}-example-1`,
      hanzi: example.hanzi,
      pinyin: example.pinyin,
      japanese: example.japanese,
    }];
    const tags = (item.tags ?? []).filter(
      (tag) => tag !== MACHINE_EXAMPLE_TAG && tag !== REVIEWED_EXAMPLE_TAG
    );
    tags.push(REVIEWED_EXAMPLE_OVERRIDES.has(item.id)
      ? REVIEWED_EXAMPLE_TAG
      : MACHINE_EXAMPLE_TAG);
    item.tags = [...new Set(tags)];
  }
  for (const item of pack.vocabulary) {
    if (!item.examples?.length) throw new Error(`${item.id}: missing example after enrichment`);
  }
  const licenseParts = (pack.source.license ?? "").split(/\s+/).filter(Boolean);
  const license = licenseParts.join(" ");
  pack.source.license = license.includes(EXAMPLE_LICENSE_NOTE)
    ? license
    : `${license} ${EXAMPLE_LICENSE_NOTE}`.trim();
  await writeFile(packPath, JSON.stringify(pack) + "\n");
  console.log(`Enriched ${packPath}; every HSK1 item now has an example`);
}

main().catch((error) => {
  console.error(error.stack ?? error.message);
  process.exitCode = 1;
});
