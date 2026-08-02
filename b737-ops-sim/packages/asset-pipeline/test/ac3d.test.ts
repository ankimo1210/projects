import { describe, expect, it } from 'vitest';
import { isShaded, isTwoSided, parseAc3d, walkObjects } from '../src/ac3d.js';
import { acToGltf, computeBounds } from '../src/gltf.js';

/** Golden mini .ac: 1 material, world → group → textured quad + bare triangle. */
const MINI_AC = `AC3Db
MATERIAL "white" rgb 1 1 1  amb 0.2 0.2 0.2  emis 0.1 0 0  spec 0.5 0.5 0.5  shi 64  trans 0
MATERIAL "glass" rgb 0.2 0.3 0.4  amb 0.2 0.2 0.2  emis 0 0 0  spec 1 1 1  shi 128  trans 0.5
OBJECT world
kids 1
OBJECT group
name "cabin"
loc 1 0 0
kids 2
OBJECT poly
name "quad"
texture "panel.png"
texrep 2 1
crease 45.0
numvert 4
0 0 0
1 0 0
1 1 0
0 1 0
numsurf 1
SURF 0x30
mat 0
refs 4
0 0 0
1 1 0
2 1 1
3 0 1
kids 0
OBJECT poly
name "tri"
numvert 3
0 0 0
1 0 0
0 0 1
numsurf 1
SURF 0x0
mat 1
refs 3
0 0 0
1 1 0
2 0 1
kids 0
`;

describe('parseAc3d', () => {
  it('parses materials, hierarchy, vertices, surfaces and attributes', () => {
    const model = parseAc3d(MINI_AC);
    expect(model.materials).toHaveLength(2);
    expect(model.materials[0]!.emis[0]).toBeCloseTo(0.1);
    expect(model.materials[1]!.trans).toBeCloseTo(0.5);

    const objects = [...walkObjects(model.root)];
    expect(objects.map((o) => o.name)).toEqual(['', 'cabin', 'quad', 'tri']);
    const cabin = objects[1]!;
    expect(cabin.loc).toEqual([1, 0, 0]);
    const quad = objects[2]!;
    expect(quad.texture).toBe('panel.png');
    expect(quad.texrep).toEqual([2, 1]);
    expect(quad.vertices).toHaveLength(12);
    expect(quad.surfaces).toHaveLength(1);
    expect(isShaded(quad.surfaces[0]!)).toBe(true);
    expect(isTwoSided(quad.surfaces[0]!)).toBe(true);
    const tri = objects[3]!;
    expect(isShaded(tri.surfaces[0]!)).toBe(false);
    expect(tri.surfaces[0]!.materialIndex).toBe(1);
  });

  it('rejects non-AC3D input', () => {
    expect(() => parseAc3d('hello')).toThrow(/not an AC3D/);
  });

  it('computes bounds including loc offsets', () => {
    const bounds = computeBounds(parseAc3d(MINI_AC));
    expect(bounds.min).toEqual([1, 0, 0]); // cabin loc x=1
    expect(bounds.max).toEqual([2, 1, 1]);
  });
});

describe('acToGltf', () => {
  it('emits a valid glTF structure preserving names', () => {
    const model = parseAc3d(MINI_AC);
    const { json, bin } = acToGltf(model, { resolveTexture: (n) => `textures/${n}` });
    expect(json.asset).toMatchObject({ version: '2.0' });
    const nodes = json.nodes as { name?: string; mesh?: number; translation?: number[] }[];
    expect(nodes.map((n) => n.name)).toEqual([undefined, 'cabin', 'quad', 'tri']);
    expect(nodes[1]!.translation).toEqual([1, 0, 0]);
    const meshes = json.meshes as { name: string; primitives: unknown[] }[];
    expect(meshes.map((m) => m.name).sort()).toEqual(['quad', 'tri']);
    expect(bin.length).toBeGreaterThan(0);
  });

  it('quad becomes two triangles with flipped V and texrep applied', () => {
    const model = parseAc3d(MINI_AC);
    const { json, bin } = acToGltf(model, { resolveTexture: (n) => `textures/${n}` });
    const accessors = json.accessors as {
      bufferView: number;
      count: number;
      type: string;
      componentType: number;
    }[];
    const views = json.bufferViews as { byteOffset: number; byteLength: number }[];
    const meshes = json.meshes as {
      name: string;
      primitives: { attributes: { TEXCOORD_0: number }; indices: number }[];
    }[];
    const quad = meshes.find((m) => m.name === 'quad')!;
    const idxAcc = accessors[quad.primitives[0]!.indices]!;
    expect(idxAcc.count).toBe(6); // 2 triangles
    const uvAcc = accessors[quad.primitives[0]!.attributes.TEXCOORD_0]!;
    const uvView = views[uvAcc.bufferView]!;
    const uvs = new Float32Array(
      bin.buffer.slice(
        bin.byteOffset + uvView.byteOffset,
        bin.byteOffset + uvView.byteOffset + uvView.byteLength,
      ),
    );
    // ref (u=1,v=1) with texrep [2,1] → u=2, v' = 1-1 = 0
    const pairs = Array.from({ length: uvs.length / 2 }, (_, i) => [uvs[i * 2], uvs[i * 2 + 1]]);
    expect(pairs).toContainEqual([2, 0]);
    expect(pairs).toContainEqual([0, 1]); // (0,0) → v'=1
  });

  it('creates blended material for transparent AC3D materials', () => {
    const model = parseAc3d(MINI_AC);
    const { json } = acToGltf(model, { resolveTexture: () => null });
    const materials = json.materials as {
      alphaMode?: string;
      pbrMetallicRoughness: { baseColorFactor: number[] };
    }[];
    const glass = materials.find((m) => m.alphaMode === 'BLEND');
    expect(glass).toBeDefined();
    expect(glass!.pbrMetallicRoughness.baseColorFactor[3]).toBeCloseTo(0.5);
  });

  it('tolerates unresolved textures (untextured material)', () => {
    const model = parseAc3d(MINI_AC);
    const { json, usedTextures } = acToGltf(model, { resolveTexture: () => null });
    expect(usedTextures).toEqual([]);
    expect(json.textures).toBeUndefined();
  });
});
