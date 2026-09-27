import { readFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';

const isObject = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const nonempty = value => typeof value === 'string' && value.trim().length > 0;

// Structural checks only. Grammar, uniqueness of the correct interpretation,
// pronunciation and suitability for an exam require human editorial review.
export function validateLesson(lesson) {
  const errors = [];
  const requireText = (value, path) => {
    if (!nonempty(value)) errors.push(`${path}: nonempty text required`);
  };
  if (!isObject(lesson)) return ['lesson: object required'];
  if (lesson.schemaVersion !== 1) errors.push('schemaVersion: unsupported');
  if (lesson.id !== 'hsk3-first-lesson') errors.push('id: unsupported course');
  for (const field of ['contentVersion', 'title', 'subtitle']) requireText(lesson[field], field);
  if (lesson.reviewStatus !== 'draft') errors.push('reviewStatus: draft required for this prototype');
  const profile = lesson.examProfile;
  if (!isObject(profile)) errors.push('examProfile: object required');
  else {
    if (profile.id !== 'hsk3-prototype-unconfirmed') errors.push('examProfile.id: unsupported');
    if (profile.targetLevel !== 3) errors.push('examProfile.targetLevel: unsupported');
    if (profile.syllabusStatus !== 'unconfirmed') errors.push('examProfile.syllabusStatus: unconfirmed required');
    requireText(profile.note, 'examProfile.note');
  }
  if (!Array.isArray(lesson.questions) || lesson.questions.length === 0) {
    errors.push('questions: nonempty array required');
    return errors;
  }
  const questionIDs = new Set();
  lesson.questions.forEach((question, index) => {
    const path = `questions[${index}]`;
    if (!isObject(question)) { errors.push(`${path}: object required`); return; }
    for (const field of ['id', 'prompt', 'explanation', 'correctOptionID']) {
      requireText(question[field], `${path}.${field}`);
    }
    if (questionIDs.has(question.id)) errors.push(`${path}: duplicate question id`);
    questionIDs.add(question.id);
    if (!['time', 'place'].includes(question.topic)) errors.push(`${path}.topic: unsupported`);
    if (!Array.isArray(question.options) || question.options.length !== 3) {
      errors.push(`${path}.options: exactly three required`);
    }
    const optionIDs = new Set(), optionTexts = new Set();
    for (const [optionIndex, option] of (Array.isArray(question.options) ? question.options : []).entries()) {
      const optionPath = `${path}.options[${optionIndex}]`;
      if (!isObject(option)) { errors.push(`${optionPath}: object required`); continue; }
      for (const field of ['id', 'text', 'explanation']) requireText(option[field], `${optionPath}.${field}`);
      if (optionIDs.has(option.id)) errors.push(`${optionPath}: duplicate option id`);
      const text = typeof option.text === 'string' ? option.text.trim().normalize('NFC') : option.text;
      if (optionTexts.has(text)) errors.push(`${optionPath}: duplicate option text`);
      optionIDs.add(option.id); optionTexts.add(text);
    }
    if (!optionIDs.has(question.correctOptionID)) errors.push(`${path}.correctOptionID: missing target`);
    for (const field of ['hanzi', 'pinyin', 'japanese']) {
      requireText(question.example?.[field], `${path}.example.${field}`);
    }
  });
  return errors;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const url = process.argv[2]
    ? pathToFileURL(process.argv[2])
    : new URL('../My Tianjin/Resources/Content/hsk3-first-lesson.json', import.meta.url);
  try {
    const lesson = JSON.parse(await readFile(url, 'utf8'));
    const errors = validateLesson(lesson);
    if (errors.length) {
      console.error(errors.join('\n')); process.exitCode = 1;
    } else {
      console.log(`Lesson validation passed: ${lesson.questions.length} questions, draft / unconfirmed.`);
      console.log('Editorial correctness and exam alignment require human review.');
    }
  } catch (error) {
    console.error(`Lesson validation failed: ${error.message}`); process.exitCode = 1;
  }
}
