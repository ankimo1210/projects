// Material library. Everything batched uses vertex colours so one material can
// carry many paint jobs; texture density is set by the batcher's world UVs.

import * as THREE from "three";
import {
  asphaltSet,
  concreteSet,
  facadeSet,
  grateSet,
  linoSet,
  pavingSet,
  shutterSet,
  tileSet,
  vendingTexture,
} from "./textures";
import type { SurfaceSet } from "./textures";

export type Mats = Record<string, THREE.Material>;

function std(
  color: number,
  roughness: number,
  metalness: number,
  set?: SurfaceSet,
  extra: Partial<THREE.MeshStandardMaterialParameters> = {},
): THREE.MeshStandardMaterial {
  const p: THREE.MeshStandardMaterialParameters = {
    color,
    roughness,
    metalness,
    vertexColors: true,
    normalScale: new THREE.Vector2(0.35, 0.35),
    ...extra,
  };
  if (set) {
    p.map = set.map;
    if (set.normalMap) p.normalMap = set.normalMap;
    if (set.roughnessMap) p.roughnessMap = set.roughnessMap;
  }
  return new THREE.MeshStandardMaterial(p);
}

export function makeMaterials(): Mats {
  const asphalt = asphaltSet();
  const paving = pavingSet();
  const shutter = shutterSet();
  const concA = concreteSet("#8a8a84", 1);
  const concB = concreteSet("#8f8c80", 5);
  const concC = concreteSet("#7c8284", 9);
  const grate = grateSet();
  const m: Mats = {};

  // ground
  m["asphalt"] = std(0xffffff, 1.0, 0.0, asphalt, { normalScale: new THREE.Vector2(0.9, 0.9) });
  m["paving"] = std(0xffffff, 1.0, 0.0, paving, { normalScale: new THREE.Vector2(0.7, 0.7) });
  m["tile"] = std(0xffffff, 0.32, 0.0, tileSet());
  m["lino"] = std(0xffffff, 0.45, 0.0, linoSet());
  m["concreteFloor"] = std(0x8c8c88, 0.55, 0.0, concC);
  m["grate"] = std(0xffffff, 0.42, 0.75, grate, { normalScale: new THREE.Vector2(1, 1) });

  // structure
  m["termWall"] = std(0xa39f8f, 0.82, 0.0, concB);
  m["termInner"] = std(0x8a9488, 0.78, 0.0, concB);
  m["termTrim"] = std(0x3d4a44, 0.6, 0.1);
  m["termCeil"] = std(0x5a5c58, 0.95, 0.0, concA);
  m["concrete"] = std(0x8b8b86, 0.88, 0.0, concA);
  m["concreteDark"] = std(0x55575a, 0.9, 0.0, concA);
  m["warehouse"] = std(0x5f6b72, 0.62, 0.35, { map: concC.map, normalMap: shutter.normalMap as THREE.Texture }, { normalScale: new THREE.Vector2(1, 1) });
  m["winch"] = std(0x6f7972, 0.85, 0.0, concC);
  m["booth"] = std(0x8a9186, 0.8, 0.0, concB);
  m["station"] = std(0xa0a3a6, 0.82, 0.0, facadeSet(1));
  m["stationTrim"] = std(0x4a4d53, 0.7, 0.1, concA);
  m["roof"] = std(0x26282b, 0.95, 0.0, concA);
  m["shutter"] = std(0xffffff, 0.62, 0.4, shutter, { normalScale: new THREE.Vector2(1, 1) });
  for (let i = 0; i < 8; i++) m[`facade${i}`] = std(0xffffff, 0.86, 0.0, facadeSet(i));

  // props
  m["metalDark"] = std(0x2c3034, 0.42, 0.75);
  m["metalPaint"] = std(0xffffff, 0.5, 0.35);
  m["paint"] = std(0xffffff, 0.3, 0.55);
  m["carGlass"] = std(0x07090c, 0.08, 0.9);
  m["tire"] = std(0x0d0d0e, 0.92, 0.0);
  m["glassDark"] = std(0x0a0e12, 0.1, 0.85);
  m["wood"] = std(0x6b5237, 0.85, 0.0, concB);
  m["crate"] = std(0x7a6040, 0.85, 0.0, concB);
  m["pallet"] = std(0x8a714a, 0.9, 0.0, concB);
  m["sandbag"] = std(0x8a8268, 0.97, 0.0, concA);
  m["container"] = std(0x3d6079, 0.55, 0.45, { map: concC.map, normalMap: shutter.normalMap as THREE.Texture }, { normalScale: new THREE.Vector2(1, 1) });
  m["dumpster"] = std(0x345846, 0.55, 0.4, concC);
  m["vending"] = std(0xffffff, 0.4, 0.3, { map: vendingTexture() });
  m["locker"] = std(0x79848d, 0.5, 0.5, concC);
  m["counter"] = std(0x6d6253, 0.6, 0.05, concB);
  m["bin"] = std(0x445a66, 0.55, 0.3);
  m["ac"] = std(0xa5a8a2, 0.6, 0.4, concC);
  m["planter"] = std(0x6a6c66, 0.9, 0.0, concA);
  m["hedge"] = std(0x1d2c1c, 1.0, 0.0, concA);
  m["stone"] = std(0x62646a, 0.75, 0.0, concA);
  m["tarp"] = std(0x2d4c6c, 0.6, 0.0);
  m["pipe"] = std(0x66767e, 0.45, 0.7);
  m["void"] = new THREE.MeshBasicMaterial({ color: 0x010203 });
  m["skin"] = std(0xffffff, 0.75, 0.0);
  return m;
}
