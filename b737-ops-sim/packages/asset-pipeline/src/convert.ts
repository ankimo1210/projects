import { createHash } from 'node:crypto';
import {
  copyFileSync,
  existsSync,
  mkdirSync,
  readFileSync,
  rmSync,
  statSync,
  writeFileSync,
} from 'node:fs';
import { dirname, join, posix } from 'node:path';
import { parseAc3d, toFgFrame } from './ac3d.js';
import { acToGltf, computeBounds } from './gltf.js';
import { extractBindings, type XmlSource } from './extractBindings.js';

/**
 * Convert the fetched 737-800YV cockpit models to glTF + bindings JSON.
 * Reproducible one-command step of the asset pipeline (ASSET_PIPELINE.md):
 *   imported .ac/.xml/.png → generated .gltf/.bin/textures + cockpit-bindings.json
 */

const MODELS: { ac: string; out: string }[] = [
  { ac: 'Models/cockpit.ac', out: 'cockpit' },
  { ac: 'Models/flightdesk.ac', out: 'flightdesk' },
  { ac: 'Models/pedestal.ac', out: 'pedestal' },
  { ac: 'Models/pedals.ac', out: 'pedals' },
  { ac: 'Models/yoke/yoke.ac', out: 'yoke' },
  { ac: 'Models/Overhead/Overhead.ac', out: 'overhead' },
  { ac: 'Models/OH-panel/OH-panel.ac', out: 'oh-panel' },
  { ac: 'Models/Instruments/autopilot-panel.ac', out: 'autopilot-panel' },
  { ac: 'Models/seats/cockpitseat.ac', out: 'cockpitseat' },
  { ac: 'Models/seats/cockpitseat2.ac', out: 'cockpitseat2' },
];

const TEXTURE_FALLBACK_DIRS = [
  'Models',
  'Models/Instruments',
  'Models/Overhead',
  'Models/OH-panel',
];

/**
 * Sounds the web audio engine loads by name (apps/web/src/audio/audioEngine.ts)
 * — the converter copies exactly these, nothing else.
 */
const SOUND_ALLOWLIST = [
  'click.wav',
  'flaps.wav',
  'gear.wav',
  'Wind.wav',
  'Apdisco.wav',
  'altAlert.wav',
  'approaching-minimums.wav',
  'cfm11a.wav',
  'cfm14a.wav',
  ...[10, 20, 30, 40, 50, 100, 200, 300, 400, 500, 1000, 2500].map((a) => `altitude-${a}.wav`),
];

/** Sample loops whose absence would make the verified sample build misleading. */
const REQUIRED_RUNTIME_SOUNDS = ['Wind.wav', 'cfm11a.wav', 'cfm14a.wav'];
const REQUIRED_BINDING_FILES = ['Models/cockpit.xml'];

export interface ConvertSummary {
  models: { name: string; meshes: number; missingTextures: string[] }[];
  bounds: Record<string, { min: number[]; max: number[] }>;
  missingSounds: string[];
}

function soundPath(importedDir: string, name: string): string | undefined {
  return ['Sounds', 'Sounds/FL2070', 'Sounds/gpws']
    .map((dir) => join(importedDir, dir, name))
    .find((abs) => existsSync(abs) && statSync(abs).size > 0);
}

/** Fail before deleting a previously usable generated tree. */
export function validateImportedAssets(importedDir: string): void {
  const requiredFiles = [...MODELS.map((model) => model.ac), ...REQUIRED_BINDING_FILES];
  const missingFiles = requiredFiles.filter((path) => {
    const abs = join(importedDir, path);
    return !existsSync(abs) || statSync(abs).size === 0;
  });
  const missingSounds = REQUIRED_RUNTIME_SOUNDS.filter(
    (name) => soundPath(importedDir, name) === undefined,
  );
  if (missingFiles.length > 0 || missingSounds.length > 0) {
    const detail = [
      ...missingFiles.map((path) => `required model/binding missing or empty: ${path}`),
      ...missingSounds.map((name) => `required runtime sound missing or empty: ${name}`),
    ];
    throw new Error(`invalid imported cockpit assets:\n${detail.join('\n')}`);
  }
}

export function convertCockpitAssets(importedDir: string, outDir: string): ConvertSummary {
  validateImportedAssets(importedDir);
  // Regenerate from scratch: stale output from an earlier asset set must not
  // survive into a new build (R-21).
  rmSync(outDir, { recursive: true, force: true });
  mkdirSync(join(outDir, 'textures'), { recursive: true });
  const summary: ConvertSummary = { models: [], bounds: {}, missingSounds: [] };
  const copiedByAbsPath = new Map<string, string>();

  for (const model of MODELS) {
    const acAbs = join(importedDir, model.ac);
    // normalize into the FG model frame so vertices match the XML data
    const parsed = toFgFrame(parseAc3d(readFileSync(acAbs, 'latin1')));
    const missingTextures: string[] = [];
    const acDir = posix.dirname(model.ac);

    const resolveTexture = (name: string): string | null => {
      const candidates = [
        posix.normalize(posix.join(acDir, name)),
        ...TEXTURE_FALLBACK_DIRS.map((d) => posix.join(d, posix.basename(name))),
      ];
      for (const candidate of candidates) {
        const abs = join(importedDir, candidate);
        if (!existsSync(abs)) continue;
        const already = copiedByAbsPath.get(abs);
        if (already) return already;
        // same basename can exist in several dirs with different content —
        // prefix a content hash to keep URIs collision-free
        const hash = createHash('sha256').update(readFileSync(abs)).digest('hex').slice(0, 8);
        const uri = `textures/${hash}-${posix.basename(candidate)}`;
        copyFileSync(abs, join(outDir, uri));
        copiedByAbsPath.set(abs, uri);
        return uri;
      }
      if (!missingTextures.includes(name)) missingTextures.push(name);
      return null;
    };

    const { json, bin } = acToGltf(parsed, { resolveTexture });
    (json.buffers as { uri: string }[])[0]!.uri = `${model.out}.bin`;
    writeFileSync(join(outDir, `${model.out}.gltf`), JSON.stringify(json));
    writeFileSync(join(outDir, `${model.out}.bin`), bin);
    summary.models.push({
      name: model.out,
      meshes: ((json.meshes as unknown[]) ?? []).length,
      missingTextures,
    });
    summary.bounds[model.out] = computeBounds(parsed);
  }

  // assembly + animation bindings from the FG XMLs
  const source: XmlSource = {
    read: (path: string) => {
      const abs = join(importedDir, path);
      return existsSync(abs) ? readFileSync(abs, 'utf8') : null;
    },
    exists: (path: string) => existsSync(join(importedDir, path)),
  };
  const bindings = extractBindings('Models/cockpit.xml', source);
  // map .ac paths to generated gltf names for the renderer
  const acToOut = new Map(MODELS.map((m) => [m.ac, `${m.out}.gltf`]));
  const enriched = {
    ...bindings,
    instances: bindings.instances
      .map((inst) => ({ ...inst, gltf: acToOut.get(inst.ac) ?? null }))
      .filter((inst) => inst.gltf !== null),
  };
  if (enriched.instances.length === 0 || enriched.animations.length === 0) {
    throw new Error('invalid cockpit bindings: expected at least one model instance and animation');
  }
  writeFileSync(join(outDir, 'cockpit-bindings.json'), JSON.stringify(enriched, null, 1));

  // Flatten the GPL sounds the audio engine actually asks for. Copying every
  // .wav that happened to be on disk made the output depend on leftovers from
  // previous fetches (R-21).
  const soundsOut = join(outDir, 'sounds');
  mkdirSync(soundsOut, { recursive: true });
  const missingSounds: string[] = [];
  for (const name of SOUND_ALLOWLIST) {
    const sourcePath = soundPath(importedDir, name);
    if (!sourcePath) {
      missingSounds.push(name);
      continue;
    }
    copyFileSync(sourcePath, join(soundsOut, name));
  }
  summary.missingSounds = missingSounds;
  return summary;
}

export function ensureDir(path: string): void {
  mkdirSync(dirname(path), { recursive: true });
}
