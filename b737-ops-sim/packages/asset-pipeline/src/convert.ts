import { createHash } from 'node:crypto';
import { copyFileSync, existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
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

const TEXTURE_FALLBACK_DIRS = ['Models', 'Models/Instruments', 'Models/Overhead', 'Models/OH-panel'];

export interface ConvertSummary {
  models: { name: string; meshes: number; missingTextures: string[] }[];
  bounds: Record<string, { min: number[]; max: number[] }>;
}

export function convertCockpitAssets(importedDir: string, outDir: string): ConvertSummary {
  mkdirSync(join(outDir, 'textures'), { recursive: true });
  const summary: ConvertSummary = { models: [], bounds: {} };
  const copiedByAbsPath = new Map<string, string>();

  for (const model of MODELS) {
    const acAbs = join(importedDir, model.ac);
    if (!existsSync(acAbs)) {
      summary.models.push({ name: model.out, meshes: 0, missingTextures: ['(model missing)'] });
      continue;
    }
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
  writeFileSync(join(outDir, 'cockpit-bindings.json'), JSON.stringify(enriched, null, 1));

  // flatten fetched GPL sounds for the web audio engine (basename-keyed)
  const soundsOut = join(outDir, 'sounds');
  mkdirSync(soundsOut, { recursive: true });
  const soundDirs = ['Sounds', 'Sounds/FL2070', 'Sounds/gpws'];
  for (const dir of soundDirs) {
    const abs = join(importedDir, dir);
    if (!existsSync(abs)) continue;
    for (const file of readdirSync(abs)) {
      if (file.endsWith('.wav')) copyFileSync(join(abs, file), join(soundsOut, file));
    }
  }
  return summary;
}

export function ensureDir(path: string): void {
  mkdirSync(dirname(path), { recursive: true });
}
