/**
 * AC3D (.ac) parser — the text format used by FlightGear aircraft models.
 * Format reference: https://www.inivis.com/ac3d/man/ac3dfileformat.html
 *
 * Parses the "AC3Db" dialect (positions only, per-surface UVs).
 */

export interface AcMaterial {
  name: string;
  rgb: [number, number, number];
  amb: [number, number, number];
  emis: [number, number, number];
  spec: [number, number, number];
  shi: number;
  trans: number;
}

export interface AcSurfaceRef {
  vertexIndex: number;
  u: number;
  v: number;
}

export interface AcSurface {
  /** Raw SURF flags: bits 0-3 type (0 poly), bit 4 shaded, bit 5 two-sided. */
  flags: number;
  materialIndex: number;
  refs: AcSurfaceRef[];
}

export interface AcObject {
  type: string; // world | group | poly | light
  name: string;
  texture: string | null;
  texrep: [number, number];
  crease: number | null;
  /** 3x3 rotation matrix, row-major; null = identity. */
  rot: number[] | null;
  loc: [number, number, number];
  vertices: Float64Array; // xyz triplets
  surfaces: AcSurface[];
  kids: AcObject[];
}

export interface AcModel {
  materials: AcMaterial[];
  root: AcObject;
}

export function isPolySurface(s: AcSurface): boolean {
  return (s.flags & 0x0f) === 0;
}

export function isShaded(s: AcSurface): boolean {
  return (s.flags & 0x10) !== 0;
}

export function isTwoSided(s: AcSurface): boolean {
  return (s.flags & 0x20) !== 0;
}

class LineReader {
  private index = 0;
  constructor(private lines: string[]) {}
  peek(): string | null {
    return this.index < this.lines.length ? this.lines[this.index]! : null;
  }
  next(): string {
    const line = this.peek();
    if (line === null) throw new Error('unexpected end of .ac file');
    this.index += 1;
    return line;
  }
  get lineNo(): number {
    return this.index;
  }
}

/** Extract a quoted or bare token after a keyword. */
function afterKeyword(line: string, keyword: string): string {
  const rest = line.slice(keyword.length).trim();
  const quoted = rest.match(/^"([^"]*)"/);
  return quoted ? quoted[1]! : (rest.split(/\s+/)[0] ?? '');
}

function parseFloats(text: string): number[] {
  return text
    .trim()
    .split(/\s+/)
    .map(Number)
    .filter((n) => !Number.isNaN(n));
}

const MATERIAL_RE =
  /^MATERIAL\s+"([^"]*)"\s+rgb\s+(\S+)\s+(\S+)\s+(\S+)\s+amb\s+(\S+)\s+(\S+)\s+(\S+)\s+emis\s+(\S+)\s+(\S+)\s+(\S+)\s+spec\s+(\S+)\s+(\S+)\s+(\S+)\s+shi\s+(\S+)\s+trans\s+(\S+)/;

export function parseAc3d(text: string): AcModel {
  const lines = text.split(/\r?\n/);
  const reader = new LineReader(lines);
  const header = reader.next().trim();
  if (!header.startsWith('AC3D')) throw new Error(`not an AC3D file (header '${header}')`);

  const materials: AcMaterial[] = [];
  // materials come before the first OBJECT
  while (reader.peek() !== null && !reader.peek()!.trim().startsWith('OBJECT')) {
    const line = reader.next().trim();
    if (!line.startsWith('MATERIAL')) continue;
    const m = line.match(MATERIAL_RE);
    if (!m) {
      // tolerate slightly malformed material lines with a gray default
      materials.push({
        name: 'invalid',
        rgb: [0.6, 0.6, 0.6],
        amb: [0.2, 0.2, 0.2],
        emis: [0, 0, 0],
        spec: [0.2, 0.2, 0.2],
        shi: 32,
        trans: 0,
      });
      continue;
    }
    const f = (i: number): number => Number(m[i]);
    materials.push({
      name: m[1]!,
      rgb: [f(2), f(3), f(4)],
      amb: [f(5), f(6), f(7)],
      emis: [f(8), f(9), f(10)],
      spec: [f(11), f(12), f(13)],
      shi: f(14),
      trans: f(15),
    });
  }

  const root = parseObject(reader);
  return { materials, root };
}

function parseObject(reader: LineReader): AcObject {
  const objLine = reader.next().trim();
  if (!objLine.startsWith('OBJECT')) {
    throw new Error(`expected OBJECT at line ${reader.lineNo}, got '${objLine}'`);
  }
  const obj: AcObject = {
    type: afterKeyword(objLine, 'OBJECT'),
    name: '',
    texture: null,
    texrep: [1, 1],
    crease: null,
    rot: null,
    loc: [0, 0, 0],
    vertices: new Float64Array(0),
    surfaces: [],
    kids: [],
  };

  for (;;) {
    const raw = reader.peek();
    if (raw === null) return obj;
    const line = raw.trim();

    if (line.startsWith('name ')) {
      obj.name = afterKeyword(reader.next().trim(), 'name');
    } else if (line.startsWith('data ')) {
      const bytes = Number(afterKeyword(reader.next().trim(), 'data'));
      // data payload occupies following line(s); skip one line (typical case)
      if (bytes > 0) reader.next();
    } else if (line.startsWith('texture ')) {
      // some exporters emit extra texture lines (e.g. "texture ... tiled")
      const value = afterKeyword(reader.next().trim(), 'texture');
      if (obj.texture === null) obj.texture = value;
    } else if (line.startsWith('texrep ')) {
      const [x = 1, y = 1] = parseFloats(reader.next().trim().slice('texrep'.length));
      obj.texrep = [x, y];
    } else if (
      line.startsWith('texoff ') ||
      line.startsWith('subdiv ') ||
      line.startsWith('url ')
    ) {
      reader.next();
    } else if (line.startsWith('crease ')) {
      obj.crease = parseFloats(reader.next().trim().slice('crease'.length))[0] ?? null;
    } else if (line.startsWith('rot ')) {
      const nums = parseFloats(reader.next().trim().slice('rot'.length));
      if (nums.length === 9) obj.rot = nums;
    } else if (line.startsWith('loc ')) {
      const [x = 0, y = 0, z = 0] = parseFloats(reader.next().trim().slice('loc'.length));
      obj.loc = [x, y, z];
    } else if (line === 'hidden' || line === 'locked' || line === 'folded') {
      reader.next();
    } else if (line.startsWith('numvert ')) {
      reader.next();
      const count = Number(line.slice('numvert'.length).trim());
      const verts = new Float64Array(count * 3);
      for (let i = 0; i < count; i++) {
        const [x = 0, y = 0, z = 0] = parseFloats(reader.next());
        verts[i * 3] = x;
        verts[i * 3 + 1] = y;
        verts[i * 3 + 2] = z;
      }
      obj.vertices = verts;
    } else if (line.startsWith('numsurf ')) {
      reader.next();
      const count = Number(line.slice('numsurf'.length).trim());
      for (let i = 0; i < count; i++) {
        obj.surfaces.push(parseSurface(reader));
      }
    } else if (line.startsWith('kids ')) {
      reader.next();
      const count = Number(line.slice('kids'.length).trim());
      for (let i = 0; i < count; i++) {
        obj.kids.push(parseObject(reader));
      }
      return obj;
    } else {
      // unknown attribute — skip defensively
      reader.next();
    }
  }
}

function parseSurface(reader: LineReader): AcSurface {
  const surfLine = reader.next().trim();
  if (!surfLine.startsWith('SURF')) throw new Error(`expected SURF, got '${surfLine}'`);
  const flags = parseInt(surfLine.slice('SURF'.length).trim(), 16);
  let materialIndex = 0;
  let line = reader.peek()?.trim() ?? '';
  if (line.startsWith('mat ')) {
    materialIndex = Number(afterKeyword(reader.next().trim(), 'mat'));
    line = reader.peek()?.trim() ?? '';
  }
  const refs: AcSurfaceRef[] = [];
  if (line.startsWith('refs ')) {
    reader.next();
    const count = Number(line.slice('refs'.length).trim());
    for (let i = 0; i < count; i++) {
      const [vertexIndex = 0, u = 0, v = 0] = parseFloats(reader.next());
      refs.push({ vertexIndex, u, v });
    }
  }
  return { flags, materialIndex, refs };
}

/** Depth-first iteration over all objects. */
export function* walkObjects(obj: AcObject): Generator<AcObject> {
  yield obj;
  for (const kid of obj.kids) yield* walkObjects(kid);
}

/**
 * Convert a parsed model from AC3D's native frame (x aft, y up, z toward
 * viewer) into the FlightGear model frame used by the model XMLs
 * (x aft, y right/lateral, z up): (x, y, z)_fg = (x, -z, y)_ac.
 * This is a proper rotation (-90° about x), so winding is preserved and
 * nothing gets mirrored. After this, vertex data, XML offsets and XML
 * animation axes/centers all share one frame.
 */
export function toFgFrame(model: AcModel): AcModel {
  const mapVec = (x: number, y: number, z: number): [number, number, number] => [
    x,
    z === 0 ? 0 : -z,
    y,
  ];
  for (const obj of walkObjects(model.root)) {
    const v = obj.vertices;
    for (let i = 0; i < v.length; i += 3) {
      const [x, y, z] = mapVec(v[i]!, v[i + 1]!, v[i + 2]!);
      v[i] = x;
      v[i + 1] = y;
      v[i + 2] = z;
    }
    obj.loc = mapVec(obj.loc[0], obj.loc[1], obj.loc[2]);
    if (obj.rot) {
      // conjugate by the frame rotation Q: R' = Q·R·Qᵀ.
      // Q maps (x,y,z)→(x,−z,y); for the row-major 3x3 this permutes/negates
      // rows and columns: row/col 1↔2 with sign flips on the moved axis.
      const r = obj.rot;
      const q = (row: number, col: number): number => r[row * 3 + col]!;
      // build R' entries: indices via mapping m(0)=0, m(1)=2(+), m(2)=1(−)…
      // implemented directly:
      obj.rot = [
        q(0, 0),
        -q(0, 2),
        q(0, 1),
        -q(2, 0),
        q(2, 2),
        -q(2, 1),
        q(1, 0),
        -q(1, 2),
        q(1, 1),
      ];
    }
  }
  return model;
}
