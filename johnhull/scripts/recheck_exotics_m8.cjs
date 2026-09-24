// Run the accepted exotics verifiers on M8 builds without replacing historical evidence.
// Only output filenames change; all original assertions run unchanged.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const Module = require('node:module');
const { spawnSync } = require('node:child_process');
const verifiers = {
  '26-9': 'verify_barrier_pilot_browser.cjs',
  '26-10': 'verify_binary_lesson_browser.cjs',
  '26-11': 'verify_lookback_lesson_browser.cjs',
  '26-12': 'verify_shout_lesson_browser.cjs',
  '26-13': 'verify_asian_lesson_browser.cjs',
  '26-14': 'verify_exchange_lesson_browser.cjs',
  '26-15': 'verify_basket_lesson_browser.cjs',
};
const section = process.argv[2];
if (!section) {
  for (const key of Object.keys(verifiers)) {
    const child = spawnSync(process.execPath, [__filename, key], { stdio: 'inherit', env: process.env });
    if (child.status !== 0) process.exit(child.status || 1);
  }
} else {
  if (!verifiers[section]) throw new Error('Unknown accepted section ' + section);
  const filename = path.join(__dirname, verifiers[section]);
  const original = fs.readFileSync(filename, 'utf8');
  const transformed = original.replace(/\.png(?=['"])/g, '-m8-recheck.png')
    .replace(/browser-(?:m\d+b?-)?check\.json/g, 'browser-m8-recheck.json');
  const digest = text => crypto.createHash('sha256').update(text).digest('hex');
  const write = fs.writeFileSync;
  fs.writeFileSync = function (file, data, ...args) {
    if (String(file).endsWith('/browser-m8-recheck.json')) {
      const record = JSON.parse(data);
      record.command = 'CHROMIUM_BIN=<existing runtime> PLAYWRIGHT_MODULE=<existing runtime> node scripts/recheck_exotics_m8.cjs ' + section;
      record.recheck = {
        milestone: 'M8', original_verifier: 'scripts/' + verifiers[section],
        original_sha256: digest(original), executed_sha256: digest(transformed),
        wrapper_sha256: digest(fs.readFileSync(__filename)),
        changes: 'Only screenshot basenames and browser record basename; original assertions unchanged.',
      };
      // Older verifiers do not hash screenshots; include every new capture.
      const project = path.resolve(__dirname, '..');
      record.artifact_sha256 ||= {};
      for (const image of fs.readdirSync(path.dirname(file)).filter(n => n.endsWith('-m8-recheck.png'))) {
        const relative = 'docs/validation/section-' + section + '/' + image;
        record.artifact_sha256[relative] = digest(fs.readFileSync(path.join(project, relative)));
      }
      data = JSON.stringify(record, null, 2) + '\n';
    }
    return write.call(fs, file, data, ...args);
  };
  const compiled = new Module(filename, module);
  compiled.filename = filename;
  compiled.paths = Module._nodeModulePaths(__dirname);
  compiled._compile(transformed, filename);
}
