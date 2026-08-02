/**
 * Extract cockpit assembly (model include offsets) and state-driven animation
 * specs (rotate/translate axis+center+interpolation) from FlightGear model
 * XMLs, producing `cockpit-bindings.json` for the web renderer.
 *
 * The FG XMLs are the authoritative source for lever pivots — no hand-tuned
 * geometry constants (spec §8: reproducible pipeline).
 */

export interface AssemblyInstance {
  id: string;
  /** Repo-relative .ac path this instance renders. */
  ac: string;
  /** Offset chain root→leaf; each is applied in its parent's frame. */
  chain: { t: [number, number, number]; rDeg: [number, number, number] }[];
}

export interface AnimationSpec {
  objects: string[];
  type: 'rotate' | 'translate';
  fgProperty: string;
  axis: [number, number, number];
  center: [number, number, number];
  factor: number;
  offsetDeg: number;
  /** Interpolation table [input, output]; overrides factor when present. */
  table: [number, number][] | null;
}

export interface CockpitBindings {
  version: number;
  sourceRepo: string;
  instances: AssemblyInstance[];
  animations: AnimationSpec[];
}

/** FG properties whose animations we extract (others are out of M2 scope). */
const RELEVANT_PROPERTIES = [
  'controls/engines/engine[0]/throttle',
  'controls/engines/engine[1]/throttle',
  'engines/engine[0]/reverser-pos-norm',
  'engines/engine[1]/reverser-pos-norm',
  'controls/flight/flaps',
  'b737/controls/flight/spoilers-lever-pos',
  'controls/gear/brake-parking',
  'b737/controls/gear/lever',
  'controls/gear/autobrakes',
  'controls/flight/elevator',
  'controls/flight/aileron',
];

const tag = (xml: string, name: string): string | null => {
  const m = xml.match(new RegExp(`<${name}>([^<]*)</${name}>`));
  return m ? m[1]!.trim() : null;
};

const num = (xml: string, name: string, fallback = 0): number => {
  const v = tag(xml, name);
  return v === null || v === '' || Number.isNaN(Number(v)) ? fallback : Number(v);
};

function blocks(xml: string, name: string): string[] {
  const out: string[] = [];
  const open = `<${name}>`;
  const close = `</${name}>`;
  let idx = 0;
  for (;;) {
    const start = xml.indexOf(open, idx);
    if (start < 0) return out;
    // find matching close handling nesting
    let depth = 1;
    let cursor = start + open.length;
    while (depth > 0) {
      const nextOpen = xml.indexOf(open, cursor);
      const nextClose = xml.indexOf(close, cursor);
      if (nextClose < 0) return out;
      if (nextOpen >= 0 && nextOpen < nextClose) {
        depth += 1;
        cursor = nextOpen + open.length;
      } else {
        depth -= 1;
        cursor = nextClose + close.length;
      }
    }
    out.push(xml.slice(start + open.length, cursor - close.length));
    idx = cursor;
  }
}

function stripComments(xml: string): string {
  return xml.replace(/<!--[\s\S]*?-->/g, '');
}

export interface XmlSource {
  /** Read a repo-relative file; returns null when not fetched. */
  read(path: string): string | null;
  /** Whether a repo-relative file was fetched (models included). */
  exists(path: string): boolean;
}

function normalize(path: string): string {
  const parts: string[] = [];
  for (const p of path.split('/')) {
    if (p === '..') parts.pop();
    else if (p !== '.' && p !== '') parts.push(p);
  }
  return parts.join('/');
}

/**
 * Resolve an FG <path> reference. FlightGear accepts either
 * file-relative paths or aircraft-root-relative paths (with or without the
 * "Aircraft/<name>/" prefix) — try both against the fetched files.
 */
function resolvePath(fromXml: string, ref: string, source: XmlSource): string {
  if (ref.startsWith('Aircraft/737-800YV/')) return normalize(ref.slice('Aircraft/737-800YV/'.length));
  const dir = fromXml.split('/').slice(0, -1).join('/');
  const fileRelative = normalize(dir ? `${dir}/${ref}` : ref);
  if (source.exists(fileRelative)) return fileRelative;
  const rootRelative = normalize(ref);
  if (source.exists(rootRelative)) return rootRelative;
  return fileRelative;
}

export function extractBindings(rootXmlPath: string, source: XmlSource): CockpitBindings {
  const instances: AssemblyInstance[] = [];
  const animations: AnimationSpec[] = [];
  const visitedAnimationFiles = new Set<string>();

  const offsetsOf = (xml: string): { t: [number, number, number]; rDeg: [number, number, number] } => {
    const off = blocks(xml, 'offsets')[0] ?? '';
    return {
      t: [num(off, 'x-m'), num(off, 'y-m'), num(off, 'z-m')],
      rDeg: [num(off, 'pitch-deg'), num(off, 'roll-deg'), num(off, 'heading-deg')],
    };
  };

  const collectAnimations = (xmlPath: string, xml: string): void => {
    if (visitedAnimationFiles.has(xmlPath)) return;
    visitedAnimationFiles.add(xmlPath);
    for (const anim of blocks(xml, 'animation')) {
      const type = tag(anim, 'type');
      if (type !== 'rotate' && type !== 'translate') continue;
      const property = tag(anim, 'property');
      if (!property || !RELEVANT_PROPERTIES.includes(property.replace(/^\//, ''))) continue;
      const objects = [...anim.matchAll(/<object-name>([^<]+)<\/object-name>/g)].map((m) =>
        m[1]!.trim(),
      );
      if (objects.length === 0) continue;
      const axisBlock = blocks(anim, 'axis')[0] ?? '';
      const centerBlock = blocks(anim, 'center')[0] ?? '';
      const interp = blocks(anim, 'interpolation')[0];
      const table: [number, number][] | null = interp
        ? blocks(interp, 'entry').map((e) => [num(e, 'ind'), num(e, 'dep')] as [number, number])
        : null;
      animations.push({
        objects,
        type,
        fgProperty: property.replace(/^\//, ''),
        axis: [num(axisBlock, 'x'), num(axisBlock, 'y'), num(axisBlock, 'z')],
        center: [num(centerBlock, 'x-m'), num(centerBlock, 'y-m'), num(centerBlock, 'z-m')],
        factor: num(anim, 'factor', 1),
        offsetDeg: num(anim, 'offset-deg', 0),
        table,
      });
    }
  };

  const visitModelXml = (
    xmlPath: string,
    chain: { t: [number, number, number]; rDeg: [number, number, number] }[],
    instanceId: string,
  ): void => {
    const raw = source.read(xmlPath);
    if (raw === null) return;
    const xml = stripComments(raw);
    collectAnimations(xmlPath, xml);

    // the XML's own <path> entries: either an .ac (leaf) or nested models
    const topPath = tag(xml.split('<model>')[0] ?? xml, 'path');
    if (topPath && topPath.endsWith('.ac')) {
      instances.push({
        id: instanceId,
        ac: resolvePath(xmlPath, topPath, source),
        chain,
      });
    }
    const models = blocks(xml, 'model');
    models.forEach((modelBlock, i) => {
      const ref = tag(modelBlock, 'path');
      if (!ref) return;
      const childOffsets = offsetsOf(modelBlock);
      const childChain = [...chain, childOffsets];
      const childId = `${instanceId}/${ref.split('/').pop()!.replace(/\.(xml|ac)$/, '')}_${i}`;
      const resolved = resolvePath(xmlPath, ref, source);
      if (ref.endsWith('.ac')) {
        instances.push({ id: childId, ac: resolved, chain: childChain });
      } else if (ref.endsWith('.xml')) {
        visitModelXml(resolved, childChain, childId);
      }
    });
  };

  visitModelXml(rootXmlPath, [], 'cockpit');
  return { version: 1, sourceRepo: 'YV3399/737-800YV', instances, animations };
}
