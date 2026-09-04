export type Collection = 'core' | 'cafe';
export type Panel = 'code' | 'data' | 'research';
export type SceneStats = {
  meshes: number;
  triangles: number;
  fps: number;
  calls: number;
};

export const collections = {
  core: {
    title: 'Orbital core',
    number: '01',
    kind: 'DIGITAL SCULPTURE',
    asset: '/assets/orbit-core.glb',
    image: '/assets/orbit-core.png',
    description:
      'チタンの結び目と、光の軌道。Blenderで形づくった、小さな思考の核。',
  },
  cafe: {
    title: 'Komorebi café',
    number: '02',
    kind: 'MINIATURE WORLD',
    asset: '/assets/komorebi.glb',
    image: '/assets/komorebi.png',
    description:
      '夕暮れに灯る、路地の喫茶店。植栽や小さな看板まで、ぐるりと眺めて。',
  },
} as const;
