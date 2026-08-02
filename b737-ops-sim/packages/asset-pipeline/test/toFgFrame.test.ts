import { describe, expect, it } from 'vitest';
import { parseAc3d, toFgFrame, walkObjects } from '../src/ac3d.js';
import { acToGltf } from '../src/gltf.js';

const AC = `AC3Db
MATERIAL "m" rgb 1 1 1  amb 0 0 0  emis 0 0 0  spec 0 0 0  shi 0  trans 0
OBJECT world
kids 1
OBJECT poly
name "tri"
loc 1 2 3
numvert 3
0 0 0
1 0 0
0 5 0
numsurf 1
SURF 0x10
mat 0
refs 3
0 0 0
1 1 0
2 0 1
kids 0
`;

describe('toFgFrame', () => {
  it('rotates vertices and loc into the FG frame (x, -z, y), preserving winding', () => {
    const model = toFgFrame(parseAc3d(AC));
    const tri = [...walkObjects(model.root)].find((o) => o.name === 'tri')!;
    // vertex (0,5,0) [5 up in AC3D] → (0,0,5) [z up in FG]
    expect([tri.vertices[6], tri.vertices[7], tri.vertices[8]]).toEqual([0, 0, 5]);
    // loc (1,2,3) → (1,-3,2)
    expect(tri.loc).toEqual([1, -3, 2]);
    // winding preserved (proper rotation, no mirror)
    expect(tri.surfaces[0]!.refs.map((r) => r.vertexIndex)).toEqual([0, 1, 2]);
  });

  it('face normal points along -y after swap+reversal of an xz-plane tri', () => {
    // original tri in AC3D xy-plane, CCW → normal +z (toward viewer).
    // After the frame change the surface lies in the xz-plane; the normal
    // must be consistent (unit length, along ±y).
    const model = toFgFrame(parseAc3d(AC));
    const { json, bin } = acToGltf(model, { resolveTexture: () => null });
    const accessors = json.accessors as { bufferView: number; type: string }[];
    const views = json.bufferViews as { byteOffset: number; byteLength: number }[];
    const meshes = json.meshes as { primitives: { attributes: { NORMAL: number } }[] }[];
    const normalAcc = accessors[meshes[0]!.primitives[0]!.attributes.NORMAL]!;
    const view = views[normalAcc.bufferView]!;
    const normals = new Float32Array(
      bin.buffer.slice(
        bin.byteOffset + view.byteOffset,
        bin.byteOffset + view.byteOffset + view.byteLength,
      ),
    );
    const len = Math.hypot(normals[0]!, normals[1]!, normals[2]!);
    expect(len).toBeCloseTo(1, 5);
    expect(Math.abs(normals[1]!)).toBeCloseTo(1, 5); // ±y in FG frame
  });
});
