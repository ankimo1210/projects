// Synchronize the self-contained report from the canonical script and HTML source.
const fs = require('node:fs');
const path = require('node:path');
const project = path.resolve(__dirname, '..');
const sourceDir = path.join(project, 'current/source');
const script = fs.readFileSync(path.join(sourceDir, 'extracted_scripts.js'), 'utf8');
const blocks = script.split(/\/\/ ===== script block \d+ =====/).slice(1).map(s => s.trim());
if (blocks.length !== 5) throw new Error('Expected five JavaScript blocks');
let html = fs.readFileSync(path.join(sourceDir, 'full_source.html'), 'utf8');
let index = 0;
html = html.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, () => {
  if (index >= blocks.length) throw new Error('Too many inline script tags');
  return '<script>\n' + blocks[index++] + '\n</script>';
});
if (index !== blocks.length) throw new Error('Missing inline script tags');
const escape = text => text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
if ((html.match(/<pre class="code">/g) || []).length !== 1) throw new Error('Expected one model-code excerpt');
html = html.replace(/<pre class="code">[\s\S]*?<\/pre>/, '<pre class="code">' + escape(blocks.slice(0, 2).join('\n\n')) + '</pre>');
fs.writeFileSync(path.join(sourceDir, 'full_source.html'), html);
fs.writeFileSync(path.join(project, 'current/report/housing_rent_corporate_buy_report_v2.html'), html);
console.log('Built self-contained v2.2 report; embedded scripts and model excerpt synchronized.');
