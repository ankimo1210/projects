import test from 'node:test';
import assert from 'node:assert/strict';
import { validateLesson } from './validate_first_lesson.mjs';

function fixture() {
  return {
    schemaVersion: 1, id: 'hsk3-first-lesson', contentVersion: 'test-draft',
    title: '時間・場所の語順', subtitle: '1単元', reviewStatus: 'draft',
    examProfile: { id: 'hsk3-prototype-unconfirmed', targetLevel: 3,
      syllabusStatus: 'unconfirmed', note: '試験形式との対応は確認中' },
    questions: [{ id: 'q1', topic: 'time', prompt: '文を選びましょう。',
      options: [
        { id: 'a', text: '我明天去。', explanation: '時間語は動詞の前です。' },
        { id: 'b', text: '我去明天。', explanation: '時間語が動詞の後ろです。' },
        { id: 'c', text: '我明天的去。', explanation: 'ここでは「的」を入れません。' }
      ], correctOptionID: 'a', explanation: '主語＋時間＋動詞。',
      example: { hanzi: '我明天去。', pinyin: 'Wǒ míngtiān qù.', japanese: '私は明日行きます。' }
    }]
  };
}

test('a structurally complete draft can be loaded', () => {
  assert.deepEqual(validateLesson(fixture()), []);
});

test('a missing answer target is rejected before learners see it', () => {
  const value = fixture(); value.questions[0].correctOptionID = 'missing';
  assert.ok(validateLesson(value).some(x => x.includes('correctOptionID')));
});

test('duplicate question IDs cannot overwrite stored progress', () => {
  const value = fixture(); value.questions.push(structuredClone(value.questions[0]));
  assert.ok(validateLesson(value).some(x => x.includes('duplicate question')));
});

test('duplicate option IDs or text cannot produce indistinguishable answers', () => {
  for (const field of ['id', 'text']) {
    const value = fixture(); value.questions[0].options[1][field] = value.questions[0].options[0][field];
    assert.ok(validateLesson(value).some(x => x.includes(`duplicate option ${field}`)));
  }
});

test('each wrong answer needs its own nonempty explanation', () => {
  const value = fixture(); value.questions[0].options[1].explanation = '  ';
  assert.ok(validateLesson(value).some(x => x.includes('explanation')));
});

test('unconfirmed prototype cannot silently become a reviewed official course', () => {
  for (const update of [
    x => { x.reviewStatus = 'reviewed'; },
    x => { x.examProfile.syllabusStatus = 'confirmed'; },
    x => { x.examProfile.targetLevel = 4; },
    x => { x.schemaVersion = 2; }
  ]) {
    const value = fixture(); update(value);
    assert.notEqual(validateLesson(value).length, 0);
  }
});

test('truncated or wrong-shaped payloads report errors instead of crashing', () => {
  for (const value of [null, {}, [], { ...fixture(), questions: null },
    { ...fixture(), questions: [null] },
    { ...fixture(), questions: [{ ...fixture().questions[0], options: [null] }] }]) {
    assert.notEqual(validateLesson(value).length, 0);
  }
});

test('missing Chinese, pinyin or Japanese example text prevents loading', () => {
  for (const field of ['hanzi', 'pinyin', 'japanese']) {
    const value = fixture(); delete value.questions[0].example[field];
    assert.ok(validateLesson(value).some(x => x.includes(`example.${field}`)));
  }
});
