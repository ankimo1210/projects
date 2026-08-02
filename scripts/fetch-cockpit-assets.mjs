#!/usr/bin/env node
/**
 * Fetch 737-800YV cockpit assets (models, textures, FG XMLs, sounds, LICENSE)
 * into assets/imported/737-800YV/ — pinned to a specific commit for
 * reproducibility and provenance (spec §8; see THIRD_PARTY_ASSETS.md).
 *
 * Usage: node scripts/fetch-cockpit-assets.mjs [--force]
 * Idempotent: skips when the manifest matches PINNED_SHA unless --force.
 */
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, posix } from 'node:path';
import { fileURLToPath } from 'node:url';

const REPO = 'YV3399/737-800YV';
const PINNED_SHA = '9d967d89dd2ee0ae1bf01d00c49839a574aa9da5'; // master @ 2026-08-02
const LICENSE_SPDX = 'GPL-2.0';
const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const DEST = join(ROOT, 'assets/imported/737-800YV');
const MANIFEST = join(DEST, 'manifest.json');

/** Models + FG animation XMLs (the XMLs drive binding extraction). */
const MODEL_FILES = [
  'LICENSE',
  'Models/cockpit.ac',
  'Models/cockpit.xml',
  'Models/flightdesk.ac',
  'Models/flightdesk.xml',
  'Models/pedestal.ac',
  'Models/pedestal.xml',
  'Models/pedals.ac',
  'Models/pedals.xml',
  'Models/yoke/yoke.ac',
  'Models/yoke/yoke.xml',
  'Models/OH-panel/OH-panel.ac',
  'Models/OH-panel/OH-panel.xml',
  'Models/Overhead/Overhead.ac',
  'Models/Overhead/Overhead.xml',
  'Models/Instruments/autopilot-panel.ac',
  'Models/Instruments/autopilot-panel.xml',
  'Models/seats/cockpitseat.ac',
  'Models/seats/cockpitseat.xml',
  'Models/seats/cockpitseat2.ac',
  'Models/seats/cockpitseat2.xml',
];

/** GPL sounds selected for the audio engine (sample playback + fallback). */
const SOUND_FILES = [
  'Sounds/click.wav',
  'Sounds/flaps.wav',
  'Sounds/gear.wav',
  'Sounds/Wind.wav',
  'Sounds/altAlert.wav',
  'Sounds/Apdisco.wav',
  'Sounds/approaching-minimums.wav',
  ...['a', 'b'].flatMap((s) => [1, 2, 3, 4].map((n) => `Sounds/FL2070/cfm1${n}${s}.wav`)),
  ...[10, 20, 30, 40, 50, 100, 200, 300, 400, 500, 1000, 2500].map(
    (a) => `Sounds/gpws/altitude-${a}.wav`,
  ),
];

const force = process.argv.includes('--force');

if (!force && existsSync(MANIFEST)) {
  const manifest = JSON.parse(readFileSync(MANIFEST, 'utf8'));
  if (manifest.sha === PINNED_SHA) {
    console.log(`[fetch-assets] up to date (sha ${PINNED_SHA.slice(0, 10)}), skipping`);
    process.exit(0);
  }
}

async function fetchRaw(path) {
  const url = `https://raw.githubusercontent.com/${REPO}/${PINNED_SHA}/${path}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status} ${path}`);
  return Buffer.from(await res.arrayBuffer());
}

function save(relPath, buffer) {
  const abs = join(DEST, relPath);
  mkdirSync(dirname(abs), { recursive: true });
  writeFileSync(abs, buffer);
}

/** Extract texture file names referenced by an AC3D file. */
function textureRefs(acText) {
  return [...new Set([...acText.matchAll(/^texture\s+"([^"]+)"/gm)].map((m) => m[1]))];
}

const downloaded = [];
const missing = [];

async function fetchAndSave(path, { optional = false } = {}) {
  try {
    const buf = await fetchRaw(path);
    save(path, buf);
    downloaded.push({
      path,
      bytes: buf.length,
      sha256: createHash('sha256').update(buf).digest('hex').slice(0, 16),
    });
    return buf;
  } catch (err) {
    if (!optional) throw err;
    missing.push(path);
    return null;
  }
}

async function pool(items, worker, size = 6) {
  const queue = [...items];
  await Promise.all(
    Array.from({ length: size }, async () => {
      for (;;) {
        const item = queue.shift();
        if (item === undefined) return;
        await worker(item);
      }
    }),
  );
}

console.log(`[fetch-assets] ${REPO} @ ${PINNED_SHA.slice(0, 10)} → ${DEST}`);

// 1) models + XMLs + license
const acTexts = new Map();
await pool(MODEL_FILES, async (path) => {
  const buf = await fetchAndSave(path);
  if (path.endsWith('.ac') && buf) acTexts.set(path, buf.toString('latin1'));
});

// 2) textures referenced by each .ac — resolved relative to the .ac directory,
//    with Models/ and Models/Instruments/ as fallbacks (missing ones tolerated)
const textureCandidates = new Set();
for (const [acPath, text] of acTexts) {
  const dir = posix.dirname(acPath);
  for (const ref of textureRefs(text)) {
    textureCandidates.add(posix.normalize(posix.join(dir, ref)));
  }
}
await pool([...textureCandidates], async (path) => {
  const ok = await fetchAndSave(path, { optional: true });
  if (ok) return;
  const base = posix.basename(path);
  for (const fallback of [`Models/${base}`, `Models/Instruments/${base}`]) {
    if (fallback === path) continue;
    const buf = await fetchAndSave(fallback, { optional: true });
    if (buf) return;
  }
});

// 3) sounds
await pool(SOUND_FILES, (path) => fetchAndSave(path, { optional: true }));

writeFileSync(
  MANIFEST,
  JSON.stringify(
    {
      repo: REPO,
      sha: PINNED_SHA,
      license: LICENSE_SPDX,
      fetchedAt: new Date().toISOString(),
      files: downloaded.sort((a, b) => a.path.localeCompare(b.path)),
      missingOptional: missing.sort(),
    },
    null,
    2,
  ),
);

console.log(
  `[fetch-assets] done: ${downloaded.length} files (${(
    downloaded.reduce((a, f) => a + f.bytes, 0) / 1e6
  ).toFixed(1)} MB), ${missing.length} optional missing`,
);
if (missing.length) console.log('  missing:', missing.join(', '));
