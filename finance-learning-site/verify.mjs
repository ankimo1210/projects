import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const html = readFileSync('index.html', 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
new vm.Script(script);
const model = script.slice(script.indexOf('const compoundValue='), script.indexOf('function progress()'));
const context = vm.createContext({});
vm.runInContext(model + '\nthis.model = {compoundValue, portfolioRisk, optionPayoff};', context);
const { compoundValue, portfolioRisk, optionPayoff } = context.model;
const close = (actual, expected) => assert.ok(Math.abs(actual - expected) < 1e-9, `${actual} != ${expected}`);
close(compoundValue(100, 3, 2), 106.09);
close(compoundValue(100, 0, 30), 100);
close(compoundValue(100, 3, 0), 100);
close(portfolioRisk(0, -1), 20);
close(portfolioRisk(1, 0), 20);
close(portfolioRisk(0.35, 1), 20);
close(portfolioRisk(0.5, 0), 14.142135623730951);
close(portfolioRisk(0.5, -1), 0);
close(optionPayoff('call', 1050, 1000) - 100, -50);
close(optionPayoff('call', 1100, 1000) - 100, 0);
close(optionPayoff('call', 0, 1000) - 100, -100);
close(optionPayoff('put', 900, 1000) - 100, 0);
close(optionPayoff('put', 0, 1000) - 100, 900);
close(optionPayoff('put', 2000, 1000) - 100, -100);
const handlers = {};
const resetState = { completed: ['compound'], answers: { compound: 1 } };
const fakeDialog = { open: false, showModal() { this.open = true; }, close() { this.open = false; } };
const resetContext = vm.createContext({
  state: resetState,
  $: selector => selector === '#reset-dialog' ? fakeDialog : { addEventListener(event, handler) { handlers[selector] = handler; } },
  saveProgress() {}, render() {},
});
vm.runInContext(script.slice(script.indexOf('function resetProgress()'), script.indexOf("$('#theme').addEventListener")), resetContext);
handlers['#reset']();
assert.equal(fakeDialog.open, true);
handlers['#cancel-reset']();
assert.equal(fakeDialog.open, false);
assert.equal(resetState.completed.length, 1);
handlers['#reset-bottom']();
handlers['#confirm-reset']();
assert.equal(fakeDialog.open, false);
assert.equal(resetState.completed.length, 0);
assert.equal(Object.keys(resetState.answers).length, 0);
handlers['#reset']();
assert.equal(fakeDialog.open, false);
assert.ok(!html.includes('WORKSPACE_TOKENS'));
assert.ok(html.includes('lang="ja"'));
assert.ok(Buffer.byteLength(html) < 256 * 1024);
assert.equal(readFileSync('dist/index.html', 'utf8'), html);
console.log('PASS: JavaScript syntax, 14 model checks, reset open/cancel/confirm logic, Japanese markup, static output integrity');
