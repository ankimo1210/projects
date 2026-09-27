// Run an accepted section's browser verifier unmodified except for declared text renames,
// with its project root redirected to an overlay so captures never touch accepted evidence.
// Usage: node run_browser_verifier.cjs <config.json> <section-id> <project-root> <overlay-root>
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const Module = require('node:module');

const [configPath, sectionId, projectRoot, overlayRoot] = process.argv.slice(2);
if (!overlayRoot) throw new Error('usage: run_browser_verifier.cjs <config> <section> <project> <overlay>');
const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
const spec = config.sections[sectionId];
if (!spec) throw new Error(`section ${sectionId} has no dependency declaration`);
const digest = text => crypto.createHash('sha256').update(text).digest('hex');

const original = fs.readFileSync(path.join(projectRoot, spec.verifier), 'utf8');
let executed = original;
const renames = [];
for (const [from, to] of Object.entries(spec.verifier_text_renames || {})) {
  const count = executed.split(from).length - 1;
  if (count !== 1) throw new Error(`rename ${from} matched ${count} times (expected 1)`);
  executed = executed.replace(from, to);
  renames.push({ from, to });
}
console.log(JSON.stringify({ wrapper: {
  verifier: spec.verifier, original_sha256: digest(original), executed_sha256: digest(executed),
  wrapper_sha256: digest(fs.readFileSync(__filename)), renames,
  overlay_root_redirect: true } }));

const filename = path.join(overlayRoot, spec.verifier);
const compiled = new Module(filename, module);
compiled.filename = filename;
compiled.paths = Module._nodeModulePaths(path.dirname(filename));
compiled._compile(executed, filename);
