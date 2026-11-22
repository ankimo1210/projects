import * as T from 'three';
import {
  canvasTexture,
  lettering,
  nameplate,
  paint as p,
  plain,
  random,
  signTexture,
  surface,
} from './materials';
import { contact, decal, emitter, ring, wetPatch, type SetKit } from './fixtures';

const halfTurn = Math.PI / 2;
const hazard = signTexture(
  'pier-bumper',
  192,
  80,
  (c) => {
    c.fillStyle = '#a38c57';
    c.fillRect(0, 0, 192, 80);
    c.fillStyle = '#343d37';
    for (let i = -96; i < 256; i += 57) {
      c.beginPath();
      c.moveTo(i, 0);
      c.lineTo(i + 23, 0);
      c.lineTo(i + 75, 80);
      c.lineTo(i + 52, 80);
      c.fill();
    }
  },
  0.08,
);
const numberPlate = (no: string) =>
  signTexture(
    'pier-id' + no,
    220,
    270,
    (c) => {
      c.fillStyle = '#34514f';
      c.fillRect(0, 0, 220, 270);
      c.strokeStyle = '#a3afa1';
      c.lineWidth = 3;
      c.strokeRect(9, 9, 202, 252);
      lettering(c, '桟  橋', 22, 43, 31, '#d6d7bc');
      lettering(c, no, 18, 135, 123, '#d8d9c3', 700, true);
      c.fillStyle = '#b2c1aa';
      c.fillRect(20, 206, 180, 2);
      lettering(c, 'SHIONAGI  PORT', 20, 231, 18, '#c1ccbb', 600, true);
    },
    0.3,
  );
function harborStamp() {
  const tex = canvasTexture(400, 260, (c) => {
    c.fillStyle = '#c1bc99';
    c.fillRect(14, 20, 13, 219);
    lettering(c, '03', 43, 109, 134, '#c9c5a6', 700, true);
    lettering(c, 'の り ば', 55, 204, 35, '#c4bea3');
    c.strokeStyle = '#c7c2a3';
    c.lineWidth = 13;
    c.beginPath();
    c.moveTo(290, 188);
    c.lineTo(290, 50);
    c.moveTo(248, 97);
    c.lineTo(290, 52);
    c.lineTo(332, 97);
    c.stroke();
    const r = random(3012);
    c.globalCompositeOperation = 'destination-out';
    for (let i = 0; i < 9500; i++) {
      c.fillStyle = 'rgba(0,0,0,' + r() * 0.83 + ')';
      c.fillRect(r() * 400, r() * 260, r() * 3.5 + 0.5, r() * 2 + 0.5);
    }
  });
  return new T.MeshBasicMaterial({
    map: tex,
    transparent: true,
    opacity: 0.49,
    depthWrite: false,
    polygonOffset: true,
    polygonOffsetFactor: -1,
  });
}

export function installHallFixtures(k: SetKit) {
  const { b } = k;
  const red = surface('#894b3e', 'metal'),
    painted = surface('#52706a'),
    enamel = surface('#74837a', 'metal');
  for (const [z, no] of [
    [-8.55, '03'],
    [-23.8, '02'],
  ] as const) {
    const x = 0.7;
    b.box(x, 2.31, z, 0.56, 4.62, 0.56, p.structure);
    b.box(x, 0.76, z, 0.58, 1.52, 0.58, painted);
    b.box(x, 0.13, z, 0.74, 0.26, 0.74, enamel);
    b.box(x, 4.33, z, 0.88, 0.55, 0.79, p.structure);
    b.box(x, 0.85, z, 0.585, 0.24, 0.585, p.yellow);
    b.board(x, 0.85, z + 0.296, 0.58, 0.24, hazard);
    b.board(x - 0.295, 0.85, z, 0.58, 0.24, hazard, -halfTurn);
    b.board(x + 0.295, 0.85, z, 0.58, 0.24, hazard, halfTurn);
    b.box(x, 2.28, z + 0.303, 0.45, 0.66, 0.07, p.dark);
    b.board(x, 2.28, z + 0.341, 0.415, 0.61, numberPlate(no));
    b.tube([x + 0.19, 0.18, z + 0.32], [x + 0.19, 3.22, z + 0.32], 0.025, p.metal);
    b.box(x, 3.32, z + 0.33, 0.41, 0.49, 0.13, p.dark);
    b.box(x, 3.35, z + 0.458, 0.29, 0.22, 0.14, red);
    b.box(x, 3.35, z + 0.539, 0.267, 0.137, 0.023, plain('#ff7550', true));
    for (const dx of [-0.15, -0.074, 0, 0.074, 0.15])
      b.tube([x + dx, 3.21, z + 0.52], [x + dx, 3.48, z + 0.52], 0.0075, p.dark, 5);
    b.box(x, 3.2, z + 0.415, 0.4, 0.046, 0.24, p.metal);
    emitter(k, x, 3.39, z + 0.69, '#ff5e3c', 35, 12, 2.1);
    wetPatch(b, x, z + 1.11, '#e06a46', 1.62, 6.85);
    b.box(x + 0.304, 1.27, z, 0.14, 0.79, 0.51, red);
    b.board(x + 0.382, 1.29, z, 0.42, 0.34, nameplate('消火器', 'FIRE', '#874c40', '#d3c7a7'), halfTurn);
    contact(b, x, z, 1.35, 1.28);
  }
  ring(b, -8.78, 1.28, 3.14, 0.42, halfTurn);
  b.board(-8.83, 2.12, 3.17, 0.87, 0.22, nameplate('救命浮環', 'LIFE RING', '#6f5b43'), halfTurn);
  for (const [z, no] of [
    [3.9, '03'],
    [-7.7, '02'],
    [-19.3, '01'],
  ] as const) {
    b.box(-8.998, 1.73, z, 0.32, 2.1, 0.31, painted);
    b.board(-8.818, 2.0, z, 0.284, 0.36, numberPlate(no), halfTurn);
    b.box(-9, 0.075, z, 0.48, 0.15, 0.53, p.metal);
    for (const zz of [-0.19, 0.19]) b.box(-8.83, 0.16, z + zz, 0.05, 0.035, 0.054, p.dark);
  }
  // Salt, water and curling paper rub away the original boarding-lane stencil.
  decal(b, 0.14, -2.1, 2.03, 1.38, harborStamp(), 0.044);
  const ticket = signTexture(
    'ferry-ticket',
    160,
    90,
    (c) => {
      c.fillStyle = '#bcb69d';
      c.fillRect(0, 0, 160, 90);
      c.fillStyle = '#51665e';
      c.fillRect(4, 6, 151, 14);
      lettering(c, '渡 船 乗 船 券', 13, 36, 14, '#414d45');
      for (let j = 0; j < 5; j++) c.fillRect(12 + j * 4, 58, 2, 17);
      lettering(c, '03', 113, 62, 24, '#48594d', 700, true);
    },
    0.08,
  );
  const r = random(607);
  for (let i = 0; i < 11; i++) {
    const x = (r() - 0.5) * 7.2 - 2.1,
      z = -3 - r() * 18,
      g = new T.PlaneGeometry(0.14 + r() * 0.17, 0.09 + r() * 0.06);
    g.rotateZ(r() * 3.0);
    b.add(g, ticket, x, 0.049, z, new T.Euler(-halfTurn, 0, 0));
  }
  // The abandoned counter overlooks the pier.
  const window = plain('#374c4b');
  b.box(-7.15, 2.81, -17.5, 2.83, 0.18, 9.03, p.metal);
  for (const zz of [-21.62, -19.23, -16.87, -14.53, -13.33]) {
    b.box(-5.85, 2.2, zz, 0.09, 1.1, 0.11, p.metal);
  }
  b.box(-7.15, 2.17, -13.18, 2.59, 1.03, 0.075, window);
  b.board(-7.15, 2.23, -13.13, 1.8, 0.39, nameplate('きっぷ売場', 'FERRY TICKETS', '#b1b49b', '#334740'));
  b.box(-6.64, 1.79, -15.09, 0.55, 0.3, 0.49, p.dark);
  b.box(-6.64, 2.02, -15.03, 0.5, 0.26, 0.16, p.metal);
}
