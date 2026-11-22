import { canStand, DOOR, findRoute, hasShotLine, hasSightLine, PANEL, PISTOL, PLAYER_START, RADIO, STATION } from './layout.ts';
import type { Point, Point3D } from './layout.ts';

export type Stage = 'terminal' | 'street' | 'quay' | 'bridge' | 'courtyard' | 'complete';
export type Status = 'playing' | 'dead' | 'complete';
export type EnemyMode = 'patrol' | 'investigate' | 'chase' | 'stunned' | 'down';
export type ShotRay = Point3D & { dx: number; dy: number; dz: number };
export type Input = {
  forward?: number; right?: number; yaw?: number;
  sprint?: boolean; interact?: boolean; fire?: boolean; aim?: boolean; shotRay?: ShotRay;
};
export type Player = Point & {
  yaw: number; hp: number; hasGun: boolean; ammo: number;
  moving: boolean; running: boolean; aiming: boolean; distanceWalked: number; invulnerable: number;
};
export type Enemy = Point & {
  id: string; active: boolean; yaw: number; hp: number; mode: EnemyMode; moving: boolean;
  patrol: Point[]; patrolIndex: number; focus: Point; path: Point[]; routeIn: number;
  senseIn: number; attention: number; stunnedFor: number; hitFlash: number; distanceWalked: number;
};
export type EventType = 'footstep' | 'door' | 'radio' | 'pickup' | 'shot' | 'empty' | 'hit' | 'down' |
  'damage' | 'alert' | 'bridge-start' | 'bridge-open' | 'pursuit' | 'dead' | 'complete';
export type GameEvent = Point & { type: EventType; enemyId?: string };
export type GameState = {
  player: Player; enemies: Enemy[]; stage: Stage; status: Status; elapsed: number;
  doorOpen: boolean; radioHeard: boolean; bridgeStarted: boolean; bridgeProgress: number;
  shotsFired: number; hits: number; damageFlash: number; shotFlash: number;
  message: string; messageTime: number; events: GameEvent[]; fireCooldown: number; stride: number;
};
export type Interaction = { id: 'door' | 'radio' | 'pistol' | 'panel' | 'station'; text: string; distance: number };

const distance = (a: Point, b: Point) => Math.hypot(b.x - a.x, b.z - a.z);
const point = (x: number, z: number): Point => ({ x, z });
const bridgeOpen = (game: GameState) => game.bridgeProgress === 1;

function watcher(id: string, yaw: number, patrol: Point[], active = true): Enemy {
  return {
    ...patrol[0], id, active, yaw, hp: 2, mode: 'patrol', moving: false,
    patrol, patrolIndex: 1, focus: { ...patrol[0] }, path: [], routeIn: 0, senseIn: 0,
    attention: 0, stunnedFor: 0, hitFlash: 0, distanceWalked: 0,
  };
}

export function createGame(): GameState {
  return {
    player: { ...PLAYER_START, yaw: 0, hp: 100, hasGun: false, ammo: 0, moving: false,
      running: false, aiming: false, distanceWalked: 0, invulnerable: 0 },
    enemies: [
      watcher('market', 0, [point(-0.8, -84), point(-2.1, -73), point(3, -69), point(1.5, -87)]),
      watcher('arcade', Math.PI, [point(-3.6, -122), point(1.8, -113), point(5.4, -118), point(0.8, -130)]),
      watcher('lock', Math.PI, [point(38.8, -219.5), point(34.8, -218), point(36.8, -209), point(36.2, -201)]),
      watcher('spill', 0, [point(31.1, -205.5), point(31.1, -213.5), point(31.1, -203.4), point(34, -201.8)]),
      watcher('wake', 0, [point(36, -252), point(31, -266), point(23, -283), point(32, -267)], false),
    ],
    stage: 'terminal', status: 'playing', elapsed: 0, doorOpen: false, radioHeard: false,
    bridgeStarted: false, bridgeProgress: 0, shotsFired: 0, hits: 0, damageFlash: 0, shotFlash: 0,
    message: '', messageTime: 0, events: [], fireCooldown: 0, stride: 0,
  };
}

const actions = [
  { id: 'radio', at: RADIO, text: '携帯無線を聞く', range: 2.6 },
  { id: 'door', at: DOOR, text: '裏口を開ける', range: 2.75 },
  { id: 'pistol', at: PISTOL, text: '拳銃を拾う', range: 2.5 },
  { id: 'panel', at: PANEL, text: '操作盤で橋を下ろす', range: 2.7 },
  { id: 'station', at: STATION, text: '玄関に手をかける', range: 1.18 },
] as const;

export function getInteraction(game: GameState): Interaction | null {
  if (game.status !== 'playing') return null;
  for (const action of actions) {
    const d = distance(game.player, action.at);
    if (d > action.range) continue;
    if (action.id === 'radio' && game.radioHeard) continue;
    if (action.id === 'door' && game.doorOpen) continue;
    if (action.id === 'pistol' && (!game.doorOpen || game.player.hasGun)) continue;
    if (action.id === 'panel' && (game.stage !== 'quay' || game.bridgeStarted)) continue;
    if (action.id === 'station' && game.stage !== 'courtyard') continue;
    return { id: action.id, text: action.text, distance: d };
  }
  return null;
}

function emit(game: GameState, type: EventType, at: Point, enemyId?: string): void {
  game.events.push({ type, x: at.x, z: at.z, enemyId });
}

function say(game: GameState, message: string, seconds = 4.6): void {
  game.message = message;
  game.messageTime = seconds;
}

function focusOn(enemy: Enemy, source: Point, mode: 'investigate' | 'chase', seconds: number): void {
  if (enemy.mode !== mode || distance(enemy.focus, source) > 2.5) enemy.routeIn = 0;
  enemy.mode = mode;
  enemy.focus.x = source.x;
  enemy.focus.z = source.z;
  enemy.attention = seconds;
}

function loudNoise(game: GameState, source: Point, range: number): void {
  for (const enemy of game.enemies) {
    if (!enemy.active || enemy.mode === 'down' || enemy.mode === 'stunned') continue;
    const d = distance(enemy, source);
    if (d > range) continue;
    const clear = hasSightLine(enemy, source, bridgeOpen(game), game.doorOpen);
    if (!clear && d > range * 0.68) continue;
    focusOn(enemy, source, enemy.mode === 'chase' ? 'chase' : 'investigate', 12);
  }
}

function interact(game: GameState): void {
  const target = getInteraction(game);
  switch (target?.id) {
    case 'radio':
      game.radioHeard = true;
      say(game, '「……汐凪署です。北岸の玄関を開けて待っています」', 7);
      emit(game, 'radio', RADIO);
      break;
    case 'door':
      game.doorOpen = true;
      emit(game, 'door', DOOR);
      break;
    case 'pistol':
      game.player.hasGun = true;
      game.player.ammo = 5;
      say(game, '拳銃を拾った。中に五発入っている。');
      emit(game, 'pickup', PISTOL);
      break;
    case 'panel':
      game.bridgeStarted = true;
      game.stage = 'bridge';
      loudNoise(game, PANEL, 46);
      say(game, '歯車が鳴り出した。橋が下りるまで、あと少し。', 5.6);
      emit(game, 'bridge-start', PANEL);
      break;
    case 'station':
      game.status = 'complete';
      game.stage = 'complete';
      game.player.moving = false;
      game.player.running = false;
      emit(game, 'complete', STATION);
      break;
  }
}

function forwardTarget(game: GameState, aimed: boolean): Enemy | undefined {
  const player = game.player;
  const sx = Math.sin(player.yaw), cz = Math.cos(player.yaw);
  let target: Enemy | undefined, closest = 23;
  for (const enemy of game.enemies) {
    if (!enemy.active || enemy.mode === 'down') continue;
    const dx = enemy.x - player.x, dz = enemy.z - player.z;
    const forward = dx * sx - dz * cz;
    if (forward <= 0 || forward > closest) continue;
    const lateral = Math.abs(dx * cz + dz * sx);
    const hitWidth = 0.48 + (aimed ? 0.044 : 0.019) * forward;
    if (lateral > hitWidth || !hasSightLine(player, enemy, bridgeOpen(game), game.doorOpen)) continue;
    closest = forward;
    target = enemy;
  }
  return target;
}

// Intersect the horizontal cylinder and the vertical height interval of an upright figure.
function entryDistance(ray: ShotRay, e: Enemy): number {
  const ox = ray.x - e.x, oz = ray.z - e.z;
  const a = ray.dx * ray.dx + ray.dz * ray.dz;
  const b = ox * ray.dx + oz * ray.dz;
  const c = ox * ox + oz * oz - 0.52 ** 2;
  let entry = 0, exit = Infinity;
  if (a < 1e-9) {
    if (c > 0) return Infinity;
  } else {
    const disc = b * b - a * c;
    if (disc < 0) return Infinity;
    const root = Math.sqrt(disc);
    entry = Math.max(0, (-b - root) / a);
    exit = (-b + root) / a;
  }
  if (Math.abs(ray.dy) < 1e-8) {
    if (ray.y < 0.25 || ray.y > 1.85) return Infinity;
  } else {
    const low = (0.25 - ray.y) / ray.dy, high = (1.85 - ray.y) / ray.dy;
    entry = Math.max(entry, Math.min(low, high));
    exit = Math.min(exit, Math.max(low, high));
  }
  return exit >= entry ? entry : Infinity;
}

function reticleTarget(game: GameState, input: ShotRay): Enemy | undefined {
  const length = Math.hypot(input.dx, input.dy, input.dz);
  if (!Number.isFinite(length) || length < 1e-8) return;
  const ray = { ...input, dx: input.dx / length, dy: input.dy / length, dz: input.dz / length };
  const muzzle = { x: game.player.x, y: 1.36, z: game.player.z };
  const open = bridgeOpen(game);
  let target: Enemy | undefined, closest = Infinity;
  for (const e of game.enemies) {
    if (!e.active || e.mode === 'down' || distance(e, game.player) > 23) continue;
    const t = entryDistance(ray, e);
    if (t >= closest) continue;
    const at = { x: ray.x + ray.dx * t, y: ray.y + ray.dy * t, z: ray.z + ray.dz * t };
    if (!hasShotLine(ray, at, open, game.doorOpen) || !hasShotLine(muzzle, at, open, game.doorOpen)) continue;
    closest = t;
    target = e;
  }
  return target;
}

function fire(game: GameState, input: Input): void {
  const player = game.player;
  if (!player.hasGun || game.fireCooldown > 0) return;
  game.fireCooldown = 0.3;
  if (!player.ammo) {
    emit(game, 'empty', player);
    return;
  }
  player.ammo--;
  game.shotsFired++;
  game.shotFlash = 1;
  emit(game, 'shot', player);
  loudNoise(game, player, 36);
  const target = input.shotRay ? reticleTarget(game, input.shotRay) : forwardTarget(game, Boolean(input.aim));
  if (!target) return;
  game.hits++;
  target.hp--;
  target.hitFlash = 1;
  target.moving = false;
  target.focus = point(player.x, player.z);
  target.routeIn = 0;
  emit(game, 'hit', target, target.id);
  if (!target.hp) {
    target.mode = 'down';
    emit(game, 'down', target, target.id);
  } else {
    target.mode = 'stunned';
    target.stunnedFor = 1.5;
  }
}

function move(game: GameState, body: Point, dx: number, dz: number, radius: number): number {
  const x = body.x, z = body.z;
  const fits = (px: number, pz: number) => canStand(px, pz, bridgeOpen(game), game.doorOpen, radius);
  if (fits(x + dx, z + dz)) {
    body.x += dx;
    body.z += dz;
  } else {
    if (dx && fits(x + dx, z)) body.x += dx;
    if (dz && fits(body.x, z + dz)) body.z += dz;
  }
  return Math.hypot(body.x - x, body.z - z);
}

function walk(game: GameState, input: Input, dt: number): void {
  const p = game.player;
  const forward = input.forward || 0, right = input.right || 0;
  p.aiming = Boolean(input.aim && p.hasGun);
  const magnitude = Math.hypot(forward, right);
  const running = Boolean(input.sprint && !p.aiming);
  const flood = Math.max(0, Math.min(1, (-p.z - 48) / 20, (p.z + 163) / 16,
    (p.x + 9.7) / 1.2, (8.7 - p.x) / 1.2));
  const speed = (p.aiming ? 0.82 : running ? 3.0 : 1.20) * (1 - flood * (running ? 0.12 : 0.26));
  let traveled = 0;
  if (magnitude > 0) {
    const step = speed * dt / Math.max(1, magnitude);
    const sin = Math.sin(p.yaw), cos = Math.cos(p.yaw);
    traveled = move(game, p, (forward * sin + right * cos) * step,
      (-forward * cos + right * sin) * step, 0.34);
  }
  p.moving = traveled > 0.0001;
  p.running = p.moving && running;
  p.distanceWalked += traveled;
  game.stride += traveled;
  const stride = p.running ? 1.05 : 0.83;
  if (game.stride >= stride) {
    game.stride %= stride;
    emit(game, 'footstep', p);
  }
}

function progress(game: GameState, dt: number): void {
  if (game.bridgeStarted && game.bridgeProgress < 1) {
    game.bridgeProgress = Math.min(1, game.bridgeProgress + dt / 8);
    if (game.bridgeProgress >= 1 - 1e-9) {
      game.bridgeProgress = 1;
      emit(game, 'bridge-open', PANEL);
    }
  }
  const p = game.player;
  if (game.stage === 'terminal' && game.doorOpen && p.z < -42) {
    game.stage = 'street';
  } else if (game.stage === 'street' && p.z < -164.4) {
    game.stage = 'quay';
  } else if (game.stage === 'bridge' && bridgeOpen(game) && p.z < -250.2) {
    game.stage = 'courtyard';
    const wake = game.enemies.find(e => e.id === 'wake');
    if (wake) {
      wake.active = true;
      wake.x = Math.max(33.7, Math.min(38.3, p.x));
      wake.z = -244.4;
      focusOn(wake, p, 'chase', 5.5);
      emit(game, 'pursuit', wake, wake.id);
    }
    say(game, '背後で濡れた靴音がした。正面に、玄関の灯りが見える。');
  }
}

function sense(game: GameState, e: Enemy): void {
  const p = game.player;
  const dx = p.x - e.x, dz = p.z - e.z, d = Math.hypot(dx, dz);
  if (d > 13.5) return;
  const clear = hasSightLine(e, p, bridgeOpen(game), game.doorOpen);
  const facing = d < 0.001 ? 1 : (Math.sin(e.yaw) * dx - Math.cos(e.yaw) * dz) / d;
  if (clear && (d < 2.05 || facing > 0.28)) {
    if (e.mode !== 'chase') emit(game, 'alert', e, e.id);
    focusOn(e, p, 'chase', 3.7);
    return;
  }
  const hearing = (p.running ? 10.7 : 2.65) * (clear ? 1 : 0.52);
  if (p.moving && d <= hearing) {
    focusOn(e, p, e.mode === 'chase' ? 'chase' : 'investigate', e.mode === 'chase' ? 3.7 : 9);
  }
}

function navigate(game: GameState, e: Enemy, target: Point, speed: number, dt: number): void {
  e.routeIn -= dt;
  if (e.routeIn <= 0) {
    e.path = findRoute(e, target, bridgeOpen(game), game.doorOpen);
    e.routeIn = e.mode === 'chase' ? 0.47 : 1.05;
  }
  while (e.path[0] && distance(e, e.path[0]) <= 0.07) e.path.shift();
  const next = e.path[0];
  if (!next) return;
  const dx = next.x - e.x, dz = next.z - e.z, d = Math.hypot(dx, dz);
  const angle = Math.atan2(dx, -dz) - e.yaw;
  const delta = Math.atan2(Math.sin(angle), Math.cos(angle));
  const turn = (e.mode === 'patrol' ? 2.4 : 4.3) * dt;
  e.yaw += Math.max(-turn, Math.min(turn, delta));
  const fraction = Math.min(speed * dt / d, 1);
  const traveled = move(game, e, dx * fraction, dz * fraction, 0.39);
  e.moving = traveled > 0.0001;
  e.distanceWalked += traveled;
}

function hurt(game: GameState, e: Enemy): void {
  const p = game.player;
  if (p.invulnerable > 0 || distance(e, p) > 1.24) return;
  if (!hasSightLine(e, p, bridgeOpen(game), game.doorOpen)) return;
  p.hp = Math.max(0, p.hp - 27);
  p.invulnerable = 2.25;
  game.damageFlash = 1;
  emit(game, 'damage', p, e.id);
  if (!p.hp) {
    game.status = 'dead';
    p.moving = false;
    p.running = false;
    emit(game, 'dead', p, e.id);
  }
}

function advanceEnemy(game: GameState, e: Enemy, dt: number): void {
  e.moving = false;
  if (!e.active) return;
  e.hitFlash = Math.max(0, e.hitFlash - dt * 3);
  if (e.mode === 'down') return;
  if (e.mode === 'stunned') {
    e.stunnedFor -= dt;
    if (e.stunnedFor <= 0) focusOn(e, e.focus, 'investigate', 9);
    return;
  }
  if (distance(e, game.player) > 53 && e.mode === 'patrol') return;
  e.attention -= dt;
  if (e.mode === 'chase' && e.attention <= 0) {
    focusOn(e, e.focus, 'investigate', 6.8);
  } else if (e.mode === 'investigate' && e.attention <= 0) {
    e.mode = 'patrol';
    e.routeIn = 0;
  }
  e.senseIn -= dt;
  if (e.senseIn <= 0) {
    sense(game, e);
    e.senseIn = 0.15;
  }
  if (e.mode === 'patrol') {
    if (distance(e, e.patrol[e.patrolIndex]) < 0.35) {
      e.patrolIndex = (e.patrolIndex + 1) % e.patrol.length;
      e.routeIn = 0;
    }
    navigate(game, e, e.patrol[e.patrolIndex], 0.82, dt);
  } else {
    const chasing = e.mode === 'chase';
    if (distance(e, e.focus) > (chasing ? 0.72 : 0.23)) {
      const speed = chasing ? (e.id === 'wake' ? 2.12 : 1.98) : 1.55;
      navigate(game, e, e.focus, speed, dt);
    } else if (!chasing) {
      e.yaw += dt * 0.75;
    }
    if (chasing) hurt(game, e);
  }
}

export function stepGame(game: GameState, input: Input, dt: number): void {
  game.events.length = 0;
  if (game.status !== 'playing' || !Number.isFinite(dt) || dt <= 0) return;
  if (Number.isFinite(input.yaw)) game.player.yaw = input.yaw!;
  if (input.interact) interact(game);
  if (game.status !== 'playing') return;
  if (input.fire) fire(game, input);
  // Long host frames still sweep the same small collision steps as a fast display.
  const steps = Math.ceil(dt / 0.05);
  const slice = dt / steps;
  for (let i = 0; i < steps && game.status === 'playing'; i++) {
    game.elapsed += slice;
    game.player.invulnerable = Math.max(0, game.player.invulnerable - slice);
    game.fireCooldown = Math.max(0, game.fireCooldown - slice);
    game.damageFlash = Math.max(0, game.damageFlash - slice * 1.8);
    game.shotFlash = Math.max(0, game.shotFlash - slice * 8);
    game.messageTime = Math.max(0, game.messageTime - slice);
    walk(game, input, slice);
    progress(game, slice);
    for (const enemy of game.enemies) {
      advanceEnemy(game, enemy, slice);
      if (game.status !== 'playing') break;
    }
  }
}
