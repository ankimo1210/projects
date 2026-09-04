import { access, copyFile, mkdir, writeFile } from 'node:fs/promises';
import { createStudioHdr } from './studio.mjs';

const assets = [
  ['export/orbit-core.glb', 'orbit-core.glb', 'build_orbit_core.py'],
  ['export/komorebi.glb', 'komorebi.glb', 'build_scene.py'],
  ['previews/orbit-core.png', 'orbit-core.png', 'build_orbit_core.py'],
  ['previews/komorebi.png', 'komorebi.png', 'build_scene.py'],
];
const source = new URL('../../assets/', import.meta.url);
const destination = new URL('../public/assets/', import.meta.url);

// Check every source first: a missing Blender output must not leave a partial set.
const missing = (
  await Promise.all(
    assets.map(async ([input, , script]) => {
      try {
        await access(new URL(input, source));
        return null;
      } catch {
        return [input, script];
      }
    }),
  )
).filter((entry) => entry !== null);

if (missing.length > 0) {
  const scripts = [...new Set(missing.map(([, script]) => script))];
  console.error(
    [
      `Missing ${missing.length} Blender output(s) under komorebi-3d/assets/:`,
      ...missing.map(([input]) => `  assets/${input}`),
      '',
      'These files are generated, not tracked by Git. Regenerate them with a',
      'local Blender install (see komorebi-3d/README.md), from the repo root:',
      '',
      ...scripts.map(
        (script) =>
          `  <blender> --background --factory-startup --python komorebi-3d/blender/${script}`,
      ),
      '',
      'Or copy assets/ from a machine that already has them.',
    ].join('\n'),
  );
  process.exit(1);
}

await mkdir(destination, { recursive: true });
await Promise.all(
  assets.map(([input, output]) =>
    copyFile(new URL(input, source), new URL(output, destination)),
  ),
);
console.log(`Synced ${assets.length} local Blender assets.`);
await writeFile(
  new URL('comparison-studio.hdr', destination),
  createStudioHdr(),
);
