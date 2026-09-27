const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const { resolveFonts, digestScripts } = require('../../scripts/probe_render_runtime.cjs');

test('the observed PostScript face hashes the exact font bytes', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'd1-font-'));
  try {
    const regular = path.join(dir, 'regular.ttf');
    const bold = path.join(dir, 'bold.ttf');
    fs.writeFileSync(regular, 'regular');
    fs.writeFileSync(bold, 'bold A');
    const catalog = [
      { family: 'Liberation Sans', postscript: 'LiberationSans', file: regular },
      { family: 'Liberation Sans', postscript: 'LiberationSans-Bold', file: bold },
    ];
    const observed = [{ familyName: 'Liberation Sans', postScriptName: 'LiberationSans-Bold', isCustomFont: false }];
    const first = resolveFonts(observed, catalog);
    assert.equal(first[0].file, 'bold.ttf');
    fs.writeFileSync(bold, 'bold B');
    const second = resolveFonts(observed, catalog);
    assert.notEqual(first[0].sha256, second[0].sha256);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('unmapped and ambiguous font faces fail closed', () => {
  const observed = [{ familyName: 'Liberation Sans', isCustomFont: false }];
  assert.throws(() => resolveFonts(observed, []), /cannot map/);
  assert.throws(() => resolveFonts(observed, [
    { family: 'Liberation Sans', postscript: 'Regular', file: '/a.ttf' },
    { family: 'Liberation Sans', postscript: 'Bold', file: '/b.ttf' },
  ]), /cannot map/);
  assert.throws(() => resolveFonts([{ ...observed[0], isCustomFont: true }], []), /custom font/);
});

test('MathJax digests use the response body and require a nonempty script', () => {
  const url = 'https://cdn.example/mathjax/tex-mml-chtml.js';
  const first = digestScripts([{ url, body: Buffer.from('MathJax A') }]);
  const second = digestScripts([{ url, body: Buffer.from('MathJax B') }]);
  assert.notEqual(first[0].sha256, second[0].sha256);
  assert.throws(() => digestScripts([]), /MathJax script/);
  assert.throws(() => digestScripts([{ url, body: Buffer.alloc(0) }]), /MathJax script/);
});
