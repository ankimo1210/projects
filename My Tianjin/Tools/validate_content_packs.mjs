#!/usr/bin/env node

import { mkdtemp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SUPPORTED_SCHEMA_VERSION = 1;
const EXPECTED_BY_LEVEL = new Map([
  ["1", 300],
  ["2", 200],
  ["3", 500],
  ["4", 1_000],
  ["5", 1_600],
  ["6", 1_800],
  ["7-9", 5_600],
]);
const EXPECTED_TOTAL = 11_000;
const PROVENANCE_TAGS = new Set(["curated", "human-reviewed", "machine-translated-cc-cedict"]);
const ALLOWED_LOWERCASE_TOKENS = new Set([
  "app", "bluetooth", "cm", "dm", "kg", "km", "mm", "ml", "web", "wifi",
]);

function unexpectedEnglishToken(value) {
  return (value.match(/[A-Za-z]{2,}/g) ?? []).find((token) =>
    token !== token.toUpperCase() && !ALLOWED_LOWERCASE_TOKENS.has(token.toLowerCase())
  );
}

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isNonEmptyString(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function isSafeRelativeJSONResource(resource) {
  return isNonEmptyString(resource)
    && resource.endsWith(".json")
    && !path.isAbsolute(resource)
    && !resource.split("/").includes("..")
    && !resource.split("/").includes("");
}

function addIssue(issues, condition, location, message) {
  if (!condition) issues.push(`${location}: ${message}`);
}

function validateSource(source, location, issues) {
  addIssue(issues, isObject(source), location, "source must be an object");
  if (!isObject(source)) return;

  addIssue(issues, isNonEmptyString(source.title), `${location}.title`, "must be non-empty");
  addIssue(issues, isNonEmptyString(source.url), `${location}.url`, "must be non-empty");
  addIssue(issues, isNonEmptyString(source.license), `${location}.license`, "must be non-empty");

  if (isNonEmptyString(source.title)) {
    addIssue(issues, /HSK/i.test(source.title), `${location}.title`, "must identify the HSK source");
  }
  if (isNonEmptyString(source.url)) {
    let parsedURL;
    try {
      parsedURL = new URL(source.url);
    } catch {
      parsedURL = undefined;
    }
    addIssue(issues, parsedURL?.protocol === "https:", `${location}.url`, "must be a valid HTTPS URL");
  }
  if (isNonEmptyString(source.license)) {
    addIssue(issues, /CC-CEDICT/i.test(source.license), `${location}.license`, "must attribute CC-CEDICT");
    addIssue(issues, /CC BY-SA 4\.0/i.test(source.license), `${location}.license`, "must state CC BY-SA 4.0");
  }
}

function validateManifestShape(manifest, issues) {
  addIssue(issues, isObject(manifest), "manifest", "must be a JSON object");
  if (!isObject(manifest)) return;

  addIssue(
    issues,
    manifest.schemaVersion === SUPPORTED_SCHEMA_VERSION,
    "manifest.schemaVersion",
    `must equal ${SUPPORTED_SCHEMA_VERSION}`
  );
  addIssue(issues, isNonEmptyString(manifest.contentVersion), "manifest.contentVersion", "must be non-empty");
  addIssue(issues, Array.isArray(manifest.packs), "manifest.packs", "must be an array");
}

export function validateContentObjects(manifest, packsByResource) {
  const issues = [];
  validateManifestShape(manifest, issues);
  if (!isObject(manifest) || !Array.isArray(manifest.packs)) return issues;

  addIssue(issues, manifest.packs.length === EXPECTED_BY_LEVEL.size, "manifest.packs", "must contain exactly 7 packs");

  const descriptorIDs = new Set();
  const resources = new Set();
  const descriptorLevels = new Set();
  const allVocabulary = [];
  let hsk1ExampleCount = 0;

  for (const [descriptorIndex, descriptor] of manifest.packs.entries()) {
    const descriptorPath = `manifest.packs[${descriptorIndex}]`;
    addIssue(issues, isObject(descriptor), descriptorPath, "must be an object");
    if (!isObject(descriptor)) continue;

    addIssue(issues, isNonEmptyString(descriptor.id), `${descriptorPath}.id`, "must be non-empty");
    addIssue(issues, descriptor.syllabusVersion === "hsk3.0", `${descriptorPath}.syllabusVersion`, "must equal hsk3.0");
    addIssue(issues, EXPECTED_BY_LEVEL.has(descriptor.level), `${descriptorPath}.level`, "is not a supported HSK level");
    addIssue(issues, isNonEmptyString(descriptor.resource), `${descriptorPath}.resource`, "must be non-empty");

    if (isNonEmptyString(descriptor.id)) {
      addIssue(issues, !descriptorIDs.has(descriptor.id), `${descriptorPath}.id`, `duplicate id ${descriptor.id}`);
      descriptorIDs.add(descriptor.id);
    }
    if (isNonEmptyString(descriptor.resource)) {
      addIssue(issues, !resources.has(descriptor.resource), `${descriptorPath}.resource`, `duplicate resource ${descriptor.resource}`);
      addIssue(
        issues,
        isSafeRelativeJSONResource(descriptor.resource),
        `${descriptorPath}.resource`,
        "must be a safe relative JSON path"
      );
      resources.add(descriptor.resource);
    }
    if (EXPECTED_BY_LEVEL.has(descriptor.level)) {
      addIssue(issues, !descriptorLevels.has(descriptor.level), `${descriptorPath}.level`, `duplicate level ${descriptor.level}`);
      descriptorLevels.add(descriptor.level);
      addIssue(
        issues,
        descriptor.expectedVocabularyCount === EXPECTED_BY_LEVEL.get(descriptor.level),
        `${descriptorPath}.expectedVocabularyCount`,
        `must equal ${EXPECTED_BY_LEVEL.get(descriptor.level)}`
      );
    }

    const pack = packsByResource.get(descriptor.resource);
    addIssue(issues, isObject(pack), descriptor.resource || descriptorPath, "referenced pack is missing or invalid");
    if (!isObject(pack)) continue;

    const packPath = `pack[${descriptor.resource}]`;
    addIssue(issues, pack.schemaVersion === SUPPORTED_SCHEMA_VERSION, `${packPath}.schemaVersion`, `must equal ${SUPPORTED_SCHEMA_VERSION}`);
    addIssue(issues, pack.id === descriptor.id, `${packPath}.id`, "must match its manifest descriptor");
    addIssue(issues, pack.contentVersion === manifest.contentVersion, `${packPath}.contentVersion`, "must match manifest.contentVersion");
    addIssue(issues, pack.syllabusVersion === descriptor.syllabusVersion, `${packPath}.syllabusVersion`, "must match its manifest descriptor");
    addIssue(issues, pack.level === descriptor.level, `${packPath}.level`, "must match its manifest descriptor");
    validateSource(pack.source, `${packPath}.source`, issues);
    addIssue(issues, Array.isArray(pack.vocabulary), `${packPath}.vocabulary`, "must be an array");
    if (!Array.isArray(pack.vocabulary)) continue;

    addIssue(
      issues,
      pack.vocabulary.length === EXPECTED_BY_LEVEL.get(descriptor.level),
      `${packPath}.vocabulary`,
      `must contain ${EXPECTED_BY_LEVEL.get(descriptor.level)} incremental items`
    );

    for (const [itemIndex, item] of pack.vocabulary.entries()) {
      const itemPath = `${packPath}.vocabulary[${itemIndex}]`;
      addIssue(issues, isObject(item), itemPath, "must be an object");
      if (!isObject(item)) continue;

      allVocabulary.push({ item, path: itemPath, level: descriptor.level });
      addIssue(issues, isNonEmptyString(item.id), `${itemPath}.id`, "must be non-empty");
      addIssue(
        issues,
        Number.isInteger(item.officialIndex) && item.officialIndex >= 1 && item.officialIndex <= EXPECTED_TOTAL,
        `${itemPath}.officialIndex`,
        `must be an integer in 1...${EXPECTED_TOTAL}`
      );
      addIssue(issues, isNonEmptyString(item.hanzi), `${itemPath}.hanzi`, "must be non-empty");
      if (isNonEmptyString(item.hanzi)) {
        addIssue(issues, !/[0-9]$/u.test(item.hanzi), `${itemPath}.hanzi`, "display hanzi must not end in a numeric sense label");
      }
      addIssue(issues, isNonEmptyString(item.pinyin), `${itemPath}.pinyin`, "must be non-empty");
      addIssue(
        issues,
        Array.isArray(item.japanese) && item.japanese.length > 0 && item.japanese.every(isNonEmptyString),
        `${itemPath}.japanese`,
        "must contain at least one non-empty Japanese gloss"
      );
      if (Array.isArray(item.japanese)) {
        for (const [glossIndex, gloss] of item.japanese.entries()) {
          if (!isNonEmptyString(gloss)) continue;
          addIssue(
            issues,
            !/（[ぁ-んァ-ヶー・\s]+）/u.test(gloss),
            `${itemPath}.japanese[${glossIndex}]`,
            "must not include a parenthesized Japanese reading"
          );
          addIssue(
            issues,
            !/[（(](?:[一-龯々]{1,8}(?:詞|語)|動|名|形|副)(?:[・/／,，\s]*(?:[一-龯々]{1,8}(?:詞|語)|動|名|形|副))*[）)]/u.test(gloss),
            `${itemPath}.japanese[${glossIndex}]`,
            "must not include a grammatical label"
          );
          const senses = gloss.split("・").map((value) => value.trim()).filter(Boolean);
          addIssue(issues, [...gloss].length <= 48, `${itemPath}.japanese[${glossIndex}]`, "must be 48 characters or fewer");
          addIssue(issues, senses.length <= 6, `${itemPath}.japanese[${glossIndex}]`, "must contain at most 6 senses");
          addIssue(issues, new Set(senses).size === senses.length, `${itemPath}.japanese[${glossIndex}]`, "must not repeat adjacent senses");
          addIssue(issues, !/[\u0000-\u001f\u007f]/u.test(gloss), `${itemPath}.japanese[${glossIndex}]`, "must not contain control characters");
          addIssue(issues, !/[\uac00-\ud7af]/u.test(gloss), `${itemPath}.japanese[${glossIndex}]`, "must not contain Hangul");
          addIssue(issues, !/<0x[0-9a-f]+>/iu.test(gloss), `${itemPath}.japanese[${glossIndex}]`, "must not contain byte escape markers");
          addIssue(
            issues,
            unexpectedEnglishToken(gloss) === undefined,
            `${itemPath}.japanese[${glossIndex}]`,
            "must not contain unexpected English words"
          );
          addIssue(issues, !gloss.includes("～"), `${itemPath}.japanese[${glossIndex}]`, "must use 〜 consistently");
          addIssue(
            issues,
            !/[（(][^）)]*[）)]\s*〜/u.test(gloss),
            `${itemPath}.japanese[${glossIndex}]`,
            "must not contain an unfinished placeholder"
          );
        }
      }
      addIssue(issues, Array.isArray(item.tags), `${itemPath}.tags`, "must be an array");
      if (Array.isArray(item.tags)) {
        const provenance = new Set(item.tags.filter((tag) => PROVENANCE_TAGS.has(tag)));
        addIssue(
          issues,
          provenance.size === 1,
          `${itemPath}.tags`,
          "must contain exactly one translation provenance tag"
        );
      }

      if (descriptor.level === "1") {
        addIssue(
          issues,
          Array.isArray(item.examples) && item.examples.length > 0,
          `${itemPath}.examples`,
          "every HSK 1 item must have at least one example"
        );
        if (Array.isArray(item.examples)) {
          hsk1ExampleCount += item.examples.length;
          for (const [exampleIndex, example] of item.examples.entries()) {
            const examplePath = `${itemPath}.examples[${exampleIndex}]`;
            addIssue(issues, isObject(example), examplePath, "must be an object");
            if (!isObject(example)) continue;
            addIssue(issues, isNonEmptyString(example.hanzi), `${examplePath}.hanzi`, "must be non-empty");
            addIssue(issues, isNonEmptyString(example.pinyin), `${examplePath}.pinyin`, "must be non-empty");
            addIssue(issues, isNonEmptyString(example.japanese), `${examplePath}.japanese`, "must be non-empty");
            if (isNonEmptyString(item.hanzi) && isNonEmptyString(example.hanzi)) {
              addIssue(issues, example.hanzi.includes(item.hanzi), `${examplePath}.hanzi`, "must contain the target hanzi");
            }
          }
        }
      }
    }
  }

  for (const level of EXPECTED_BY_LEVEL.keys()) {
    addIssue(issues, descriptorLevels.has(level), "manifest.packs", `missing level ${level}`);
  }
  addIssue(issues, allVocabulary.length === EXPECTED_TOTAL, "vocabulary", `must contain ${EXPECTED_TOTAL} items in total`);
  addIssue(issues, hsk1ExampleCount >= 300, "hsk1.examples", "must contain examples for all 300 HSK 1 items");

  const ids = allVocabulary.map(({ item }) => item.id);
  addIssue(issues, new Set(ids).size === EXPECTED_TOTAL, "vocabulary.id", "must be globally unique across all packs");
  const indices = allVocabulary.map(({ item }) => item.officialIndex);
  addIssue(issues, new Set(indices).size === EXPECTED_TOTAL, "vocabulary.officialIndex", "must be globally unique across all packs");
  const sortedIndices = [...indices].sort((left, right) => left - right);
  const indicesAreContinuous = sortedIndices.length === EXPECTED_TOTAL
    && sortedIndices.every((value, index) => value === index + 1);
  addIssue(issues, indicesAreContinuous, "vocabulary.officialIndex", `must cover every index from 1 through ${EXPECTED_TOTAL}`);

  return issues;
}

async function parseJSON(filePath) {
  return JSON.parse(await readFile(filePath, "utf8"));
}

export async function validateContentDirectory(contentDirectory) {
  const manifestPath = path.join(contentDirectory, "content-manifest.json");
  const manifest = await parseJSON(manifestPath);
  const resources = Array.isArray(manifest?.packs)
    ? manifest.packs.map((descriptor) => descriptor?.resource).filter(isNonEmptyString)
    : [];
  const packsByResource = new Map();

  for (const resource of new Set(resources)) {
    if (!isSafeRelativeJSONResource(resource)) {
      packsByResource.set(resource, undefined);
      continue;
    }
    try {
      packsByResource.set(resource, await parseJSON(path.join(contentDirectory, resource)));
    } catch (error) {
      packsByResource.set(resource, undefined);
      packsByResource.set(`${resource}:read-error`, error.message);
    }
  }
  const issues = validateContentObjects(manifest, packsByResource);
  for (const [key, message] of packsByResource) {
    if (key.endsWith(":read-error")) issues.unshift(`${key.slice(0, -11)}: ${message}`);
  }
  return issues;
}

function makeFixture() {
  const manifest = {
    schemaVersion: SUPPORTED_SCHEMA_VERSION,
    contentVersion: "fixture-1",
    packs: [],
  };
  const packs = new Map();
  let officialIndex = 1;

  for (const [level, count] of EXPECTED_BY_LEVEL) {
    const id = `fixture-hsk3-level-${level}`;
    const resource = `fixture-hsk3-level-${level.replace("-", "_")}.json`;
    const vocabulary = [];
    for (let offset = 0; offset < count; offset += 1) {
      const item = {
        id: `fixture-${officialIndex}`,
        officialIndex,
        hanzi: "词",
        pinyin: "cí",
        japanese: ["語"],
        tags: [level === "1" ? "curated" : "machine-translated-cc-cedict"],
      };
      if (level === "1") {
        item.examples = [{
          id: `fixture-${officialIndex}-example-1`,
          hanzi: "这个词很常用。",
          pinyin: "Zhège cí hěn chángyòng.",
          japanese: "この語はよく使われます。",
        }];
      }
      vocabulary.push(item);
      officialIndex += 1;
    }

    manifest.packs.push({
      id,
      syllabusVersion: "hsk3.0",
      level,
      resource,
      expectedVocabularyCount: count,
    });
    packs.set(resource, {
      schemaVersion: SUPPORTED_SCHEMA_VERSION,
      id,
      contentVersion: manifest.contentVersion,
      syllabusVersion: "hsk3.0",
      level,
      source: {
        title: "HSK fixture with CC-CEDICT attribution",
        url: "https://example.com/hsk-fixture",
        license: "HSK fixture. CC-CEDICT, CC BY-SA 4.0.",
      },
      skills: ["vocabulary"],
      vocabulary,
    });
  }
  return { manifest, packs };
}

async function writeFixture(directory, fixture) {
  await mkdir(directory, { recursive: true });
  await writeFile(path.join(directory, "content-manifest.json"), JSON.stringify(fixture.manifest));
  for (const [resource, pack] of fixture.packs) {
    await writeFile(path.join(directory, resource), JSON.stringify(pack));
  }
}

async function runSelfTest() {
  const fixtureRoot = await mkdtemp(path.join(os.tmpdir(), "my-tianjin-content-validator-"));
  try {
    const fixture = makeFixture();
    await writeFixture(fixtureRoot, fixture);
    const validIssues = await validateContentDirectory(fixtureRoot);
    if (validIssues.length > 0) {
      throw new Error(`valid fixture failed:\n${validIssues.join("\n")}`);
    }

    const firstPack = fixture.packs.values().next().value;
    firstPack.vocabulary[0].hanzi = "词1";
    firstPack.vocabulary[1].japanese = ["発芽싹"];
    firstPack.vocabulary[2].japanese = ["蹂<0xAA>する"];
    firstPack.vocabulary[3].japanese = ["ruinする"];
    const invalidIssues = validateContentObjects(fixture.manifest, fixture.packs);
    if (!invalidIssues.some((issue) => issue.includes("must not end in a numeric sense label"))) {
      throw new Error("negative fixture did not detect a trailing numeric sense label");
    }
    for (const expected of ["must not contain Hangul", "must not contain byte escape markers", "must not contain unexpected English words"]) {
      if (!invalidIssues.some((issue) => issue.includes(expected))) {
        throw new Error(`negative fixture did not detect: ${expected}`);
      }
    }
    console.log("Self-test passed (11,000-item valid fixture and negative fixture).");
  } finally {
    await rm(fixtureRoot, { recursive: true, force: true });
  }
}

function printIssues(issues) {
  const DISPLAY_LIMIT = 100;
  for (const issue of issues.slice(0, DISPLAY_LIMIT)) console.error(`- ${issue}`);
  if (issues.length > DISPLAY_LIMIT) {
    console.error(`- ... ${issues.length - DISPLAY_LIMIT} more issue(s)`);
  }
}

async function main() {
  const args = process.argv.slice(2);
  if (args.length === 1 && args[0] === "--self-test") {
    await runSelfTest();
    return;
  }
  if (args.length > 1 || args[0] === "--help") {
    console.log("Usage: node Tools/validate_content_packs.mjs [content-directory]\n       node Tools/validate_content_packs.mjs --self-test");
    return;
  }

  const contentDirectory = path.resolve(args[0] ?? "My Tianjin/Resources/Content");
  const issues = await validateContentDirectory(contentDirectory);
  if (issues.length > 0) {
    console.error(`Content validation failed with ${issues.length} issue(s):`);
    printIssues(issues);
    process.exitCode = 1;
    return;
  }
  console.log(`Content validation passed: 7 packs, ${EXPECTED_TOTAL} vocabulary items, complete HSK 1 examples.`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((error) => {
    console.error(error.stack ?? error.message);
    process.exitCode = 1;
  });
}
