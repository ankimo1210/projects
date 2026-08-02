/**
 * Minimal glTF 2.0 writer for AC3D-parsed models.
 * Emits a .gltf JSON structure + one binary buffer; object names are
 * preserved on nodes/meshes so interactive controls bind by name
 * (COCKPIT_CONTROL_MAPPING.md).
 *
 * Conventions handled here:
 *  - AC3D UV origin is bottom-left (OpenGL); glTF is top-left → v' = 1 - v.
 *  - Surfaces with the "shaded" flag get smooth per-position normals within
 *    their object; unshaded surfaces get flat face normals (crease angle is
 *    approximated by this split — documented in ASSET_PIPELINE.md).
 *  - Materials are emitted double-sided (cockpit interiors rely on it).
 */

import { isPolySurface, isShaded, walkObjects, type AcModel, type AcObject } from './ac3d.js';

export interface GltfResult {
  json: Record<string, unknown>;
  bin: Buffer;
  /** Texture URIs actually referenced (for copy verification). */
  usedTextures: string[];
}

export interface GltfOptions {
  /** Resolve an AC3D texture name to an output-relative URI, or null if missing. */
  resolveTexture: (textureName: string) => string | null;
  generator?: string;
}

interface Vec3 {
  x: number;
  y: number;
  z: number;
}

export function acToGltf(model: AcModel, options: GltfOptions): GltfResult {
  const builder = new GltfBuilder(model, options);
  return builder.build();
}

class GltfBuilder {
  private nodes: Record<string, unknown>[] = [];
  private meshes: Record<string, unknown>[] = [];
  private materials: Record<string, unknown>[] = [];
  private textures: Record<string, unknown>[] = [];
  private images: Record<string, unknown>[] = [];
  private accessors: Record<string, unknown>[] = [];
  private bufferViews: Record<string, unknown>[] = [];
  private chunks: Buffer[] = [];
  private byteOffset = 0;
  private materialCache = new Map<string, number>();
  private imageCache = new Map<string, number>();
  private used = new Set<string>();

  constructor(
    private model: AcModel,
    private options: GltfOptions,
  ) {}

  build(): GltfResult {
    const rootIndex = this.emitNode(this.model.root);
    const bin = Buffer.concat(this.chunks);
    const json: Record<string, unknown> = {
      asset: {
        version: '2.0',
        generator: this.options.generator ?? 'b737-ops-sim asset-pipeline (AC3D converter)',
      },
      scene: 0,
      scenes: [{ nodes: [rootIndex] }],
      nodes: this.nodes,
      meshes: this.meshes,
      materials: this.materials,
      textures: this.textures,
      images: this.images,
      samplers: [{ magFilter: 9729, minFilter: 9987, wrapS: 10497, wrapT: 10497 }],
      accessors: this.accessors,
      bufferViews: this.bufferViews,
      buffers: [{ byteLength: bin.length, uri: 'PLACEHOLDER.bin' }],
    };
    if (this.meshes.length === 0) delete json.meshes;
    if (this.materials.length === 0) delete json.materials;
    if (this.textures.length === 0) {
      delete json.textures;
      delete json.images;
      delete json.samplers;
    }
    return { json, bin, usedTextures: [...this.used] };
  }

  private emitNode(obj: AcObject): number {
    const node: Record<string, unknown> = {};
    if (obj.name) node.name = obj.name;
    if (obj.rot) {
      // row-major 3x3 + loc → column-major 4x4
      const r = obj.rot;
      node.matrix = [
        r[0],
        r[3],
        r[6],
        0,
        r[1],
        r[4],
        r[7],
        0,
        r[2],
        r[5],
        r[8],
        0,
        obj.loc[0],
        obj.loc[1],
        obj.loc[2],
        1,
      ];
    } else if (obj.loc.some((v) => v !== 0)) {
      node.translation = [...obj.loc];
    }
    const meshIndex = this.emitMesh(obj);
    if (meshIndex !== null) node.mesh = meshIndex;
    const index = this.nodes.length;
    this.nodes.push(node);
    const kidIndices = obj.kids.map((k) => this.emitNode(k));
    if (kidIndices.length > 0) node.children = kidIndices;
    return index;
  }

  private emitMesh(obj: AcObject): number | null {
    const polySurfaces = obj.surfaces.filter(
      (s) => isPolySurface(s) && s.refs.length >= 3 && s.refs.length <= 512,
    );
    if (polySurfaces.length === 0 || obj.vertices.length === 0) return null;

    // face normals + smooth accumulation per position index
    const faceNormals = new Map<number, Vec3>();
    const smooth = new Map<number, Vec3>();
    polySurfaces.forEach((s, si) => {
      const n = this.faceNormal(obj, s);
      faceNormals.set(si, n);
      if (isShaded(s)) {
        for (const ref of s.refs) {
          const acc = smooth.get(ref.vertexIndex) ?? { x: 0, y: 0, z: 0 };
          acc.x += n.x;
          acc.y += n.y;
          acc.z += n.z;
          smooth.set(ref.vertexIndex, acc);
        }
      }
    });
    for (const v of smooth.values()) {
      const len = Math.hypot(v.x, v.y, v.z) || 1;
      v.x /= len;
      v.y /= len;
      v.z /= len;
    }

    // group surfaces by material
    const groups = new Map<number, number[]>();
    polySurfaces.forEach((s, si) => {
      const list = groups.get(s.materialIndex) ?? [];
      list.push(si);
      groups.set(s.materialIndex, list);
    });

    const primitives: Record<string, unknown>[] = [];
    for (const [materialIndex, surfaceIds] of groups) {
      const positions: number[] = [];
      const normals: number[] = [];
      const uvs: number[] = [];
      const indices: number[] = [];
      const vertexCache = new Map<string, number>();

      for (const si of surfaceIds) {
        const surface = polySurfaces[si]!;
        const fn = faceNormals.get(si)!;
        const shaded = isShaded(surface);
        const cornerIndex = (refIdx: number): number => {
          const ref = surface.refs[refIdx]!;
          const n = shaded ? (smooth.get(ref.vertexIndex) ?? fn) : fn;
          const key = shaded
            ? `${ref.vertexIndex}|${ref.u}|${ref.v}`
            : `${ref.vertexIndex}|${ref.u}|${ref.v}|f${si}`;
          const cached = vertexCache.get(key);
          if (cached !== undefined) return cached;
          const vi = ref.vertexIndex * 3;
          positions.push(obj.vertices[vi]!, obj.vertices[vi + 1]!, obj.vertices[vi + 2]!);
          normals.push(n.x, n.y, n.z);
          uvs.push(ref.u * obj.texrep[0], 1 - ref.v * obj.texrep[1]);
          const idx = positions.length / 3 - 1;
          vertexCache.set(key, idx);
          return idx;
        };
        // fan triangulation
        for (let i = 1; i + 1 < surface.refs.length; i++) {
          indices.push(cornerIndex(0), cornerIndex(i), cornerIndex(i + 1));
        }
      }
      if (indices.length === 0) continue;

      const primitive: Record<string, unknown> = {
        attributes: {
          POSITION: this.addAccessor(new Float32Array(positions), 'VEC3', 34962, true),
          NORMAL: this.addAccessor(new Float32Array(normals), 'VEC3', 34962),
          TEXCOORD_0: this.addAccessor(new Float32Array(uvs), 'VEC2', 34962),
        },
        indices: this.addAccessor(
          positions.length / 3 > 65535 ? new Uint32Array(indices) : new Uint16Array(indices),
          'SCALAR',
          34963,
        ),
        material: this.material(materialIndex, obj.texture),
        mode: 4,
      };
      primitives.push(primitive);
    }
    if (primitives.length === 0) return null;
    const index = this.meshes.length;
    this.meshes.push({ name: obj.name || `mesh_${index}`, primitives });
    return index;
  }

  private faceNormal(obj: AcObject, s: { refs: { vertexIndex: number }[] }): Vec3 {
    // Newell's method (robust for non-planar polys)
    let nx = 0;
    let ny = 0;
    let nz = 0;
    const refs = s.refs;
    for (let i = 0; i < refs.length; i++) {
      const a = refs[i]!.vertexIndex * 3;
      const b = refs[(i + 1) % refs.length]!.vertexIndex * 3;
      const ax = obj.vertices[a]!;
      const ay = obj.vertices[a + 1]!;
      const az = obj.vertices[a + 2]!;
      const bx = obj.vertices[b]!;
      const by = obj.vertices[b + 1]!;
      const bz = obj.vertices[b + 2]!;
      nx += (ay - by) * (az + bz);
      ny += (az - bz) * (ax + bx);
      nz += (ax - bx) * (ay + by);
    }
    const len = Math.hypot(nx, ny, nz) || 1;
    return { x: nx / len, y: ny / len, z: nz / len };
  }

  private material(materialIndex: number, textureName: string | null): number {
    const key = `${materialIndex}|${textureName ?? ''}`;
    const cached = this.materialCache.get(key);
    if (cached !== undefined) return cached;
    const mat = this.model.materials[materialIndex] ?? this.model.materials[0];
    const rgb = mat?.rgb ?? [0.7, 0.7, 0.7];
    const emis = mat?.emis ?? [0, 0, 0];
    const trans = mat?.trans ?? 0;
    const shi = mat?.shi ?? 32;
    const material: Record<string, unknown> = {
      name: `${mat?.name ?? 'mat'}_${materialIndex}`,
      pbrMetallicRoughness: {
        baseColorFactor: [rgb[0], rgb[1], rgb[2], Math.max(0, 1 - trans)],
        metallicFactor: 0,
        roughnessFactor: Math.min(1, Math.max(0.35, 1 - shi / 160)),
      },
      emissiveFactor: emis.map((e) => Math.min(1, e)),
      doubleSided: true,
    };
    if (trans > 0.01) material.alphaMode = 'BLEND';
    if (textureName) {
      const uri = this.options.resolveTexture(textureName);
      if (uri) {
        this.used.add(uri);
        let imageIndex = this.imageCache.get(uri);
        if (imageIndex === undefined) {
          imageIndex = this.images.length;
          this.images.push({ uri });
          this.imageCache.set(uri, imageIndex);
          this.textures.push({ sampler: 0, source: imageIndex });
        }
        // texture index mirrors image index (1:1)
        (material.pbrMetallicRoughness as Record<string, unknown>).baseColorTexture = {
          index: imageIndex,
        };
        // textured surfaces: let the texture carry color detail
        (material.pbrMetallicRoughness as Record<string, unknown>).baseColorFactor = [
          1,
          1,
          1,
          Math.max(0, 1 - trans),
        ];
      }
    }
    const index = this.materials.length;
    this.materials.push(material);
    this.materialCache.set(key, index);
    return index;
  }

  private addAccessor(
    data: Float32Array | Uint16Array | Uint32Array,
    type: 'VEC3' | 'VEC2' | 'SCALAR',
    target: 34962 | 34963,
    withMinMax = false,
  ): number {
    const bytes = Buffer.from(data.buffer, data.byteOffset, data.byteLength);
    // 4-byte alignment
    const padding = (4 - (this.byteOffset % 4)) % 4;
    if (padding) {
      this.chunks.push(Buffer.alloc(padding));
      this.byteOffset += padding;
    }
    const viewIndex = this.bufferViews.length;
    this.bufferViews.push({
      buffer: 0,
      byteOffset: this.byteOffset,
      byteLength: bytes.length,
      target,
    });
    this.chunks.push(bytes);
    this.byteOffset += bytes.length;

    const componentType =
      data instanceof Float32Array ? 5126 : data instanceof Uint32Array ? 5125 : 5123;
    const componentCount = type === 'VEC3' ? 3 : type === 'VEC2' ? 2 : 1;
    const accessor: Record<string, unknown> = {
      bufferView: viewIndex,
      componentType,
      count: data.length / componentCount,
      type,
    };
    if (withMinMax && data instanceof Float32Array) {
      const min = [Infinity, Infinity, Infinity];
      const max = [-Infinity, -Infinity, -Infinity];
      for (let i = 0; i < data.length; i += 3) {
        for (let c = 0; c < 3; c++) {
          min[c] = Math.min(min[c]!, data[i + c]!);
          max[c] = Math.max(max[c]!, data[i + c]!);
        }
      }
      accessor.min = min;
      accessor.max = max;
    }
    this.accessors.push(accessor);
    return this.accessors.length - 1;
  }
}

/** Axis-aligned bounds of all vertices (world of the file, ignoring rot). */
export function computeBounds(model: AcModel): { min: number[]; max: number[] } {
  const min = [Infinity, Infinity, Infinity];
  const max = [-Infinity, -Infinity, -Infinity];
  const visit = (obj: AcObject, offset: [number, number, number]): void => {
    const loc: [number, number, number] = [
      offset[0] + obj.loc[0],
      offset[1] + obj.loc[1],
      offset[2] + obj.loc[2],
    ];
    for (let i = 0; i < obj.vertices.length; i += 3) {
      for (let c = 0; c < 3; c++) {
        const v = obj.vertices[i + c]! + loc[c]!;
        min[c] = Math.min(min[c]!, v);
        max[c] = Math.max(max[c]!, v);
      }
    }
    for (const kid of obj.kids) visit(kid, loc);
  };
  visit(model.root, [0, 0, 0]);
  return { min, max };
}

export { walkObjects };
