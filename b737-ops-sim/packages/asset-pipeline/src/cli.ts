import { fileURLToPath } from 'node:url';
import { join } from 'node:path';
import { existsSync } from 'node:fs';
import { convertCockpitAssets } from './convert.js';

const ROOT = join(fileURLToPath(new URL('.', import.meta.url)), '../../..');
const importedDir = join(ROOT, 'assets/imported/737-800YV');
const outDir = join(ROOT, 'assets/generated/webroot/cockpit');

if (!existsSync(importedDir)) {
  console.error(
    `[convert] ${importedDir} not found — run 'node scripts/fetch-cockpit-assets.mjs' first`,
  );
  process.exit(1);
}

console.log(`[convert] ${importedDir} → ${outDir}`);
const summary = convertCockpitAssets(importedDir, outDir);
for (const m of summary.models) {
  const missing = m.missingTextures.length
    ? `  (missing tex: ${m.missingTextures.join(', ')})`
    : '';
  console.log(`  ${m.name.padEnd(16)} ${String(m.meshes).padStart(4)} meshes${missing}`);
}
if (summary.missingSounds.length > 0) {
  console.warn(
    `[convert] sounds not found in the imported set: ${summary.missingSounds.join(', ')}`,
  );
}
const b = summary.bounds['cockpit'];
if (b) {
  console.log(
    `[convert] cockpit bounds  x ${b.min[0]!.toFixed(1)}..${b.max[0]!.toFixed(1)}  y ${b.min[1]!.toFixed(1)}..${b.max[1]!.toFixed(1)}  z ${b.min[2]!.toFixed(1)}..${b.max[2]!.toFixed(1)}`,
  );
}
console.log('[convert] done');
