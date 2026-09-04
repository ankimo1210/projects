import { access, copyFile, mkdir } from 'node:fs/promises';

const assets = [
  ['export/orbit-core.glb', 'orbit-core.glb'],
  ['export/komorebi.glb', 'komorebi.glb'],
  ['previews/orbit-core.png', 'orbit-core.png'],
  ['previews/komorebi.png', 'komorebi.png'],
];
const source = new URL('../../assets/', import.meta.url);
const destination = new URL('../public/assets/', import.meta.url);

// Check every source first: a missing Blender output must not leave a partial set.
await Promise.all(assets.map(([input]) => access(new URL(input, source))));
await mkdir(destination, { recursive: true });
await Promise.all(
  assets.map(([input, output]) =>
    copyFile(new URL(input, source), new URL(output, destination)),
  ),
);
console.log(`Synced ${assets.length} local Blender assets.`);
