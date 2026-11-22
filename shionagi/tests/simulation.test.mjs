import test from 'node:test';
import assert from 'node:assert/strict';
import { canStand, isWall } from '../src/layout.ts';
import { createGame, getInteraction, stepGame } from '../src/simulation.ts';

const frame = 0.1;

function travel(game, x, z, sprint = true) {
  const distance = () => Math.hypot(x - game.player.x, z - game.player.z);
  const limit = Math.ceil((distance() + 2) / frame / (sprint ? 2.45 : 0.84));
  for (let i = 0; distance() > 0.17 && i < limit && game.status === 'playing'; i++) {
    const yaw = Math.atan2(x - game.player.x, game.player.z - z);
    stepGame(game, { forward: 1, yaw, sprint }, frame);
  }
  assert.ok(distance() <= 0.17,
    `Could not reach (${x}, ${z}) from (${game.player.x.toFixed(2)}, ${game.player.z.toFixed(2)}), status=${game.status}, hp=${game.player.hp}`);
}

function use(game, id) {
  assert.equal(getInteraction(game)?.id, id);
  stepGame(game, { interact: true }, frame);
}

function exitTerminal(game) {
  travel(game, 3.9, 2.6);
  travel(game, 4, -29.1);
  use(game, 'door');
  travel(game, 4, -44);
  assert.equal(game.stage, 'street');
}

function finishFromStreet(game) {
  travel(game, 2.5, -170.5);
  travel(game, 36.4, -172);
  travel(game, 42.15, -188);
  travel(game, 42.15, -206);
  travel(game, 38.4, -228.4);
  assert.equal(game.stage, 'quay');
  use(game, 'panel');
  assert.equal(game.stage, 'bridge');
  assert.equal(game.bridgeProgress < 1, true);

  // Both sides of the pump lead back to the bridge mouth while it lowers.
  travel(game, 37.2, -233.2);
  travel(game, 31, -233.2);
  travel(game, 31, -222.8);
  travel(game, 37.2, -222.8);
  travel(game, 36, -233.2);
  assert.equal(game.bridgeProgress, 1);
  travel(game, 36, -253.5);
  assert.equal(game.stage, 'courtyard');
  assert.equal(game.enemies.find(e => e.id === 'wake').active, true);
  travel(game, 28, -265);
  travel(game, 28, -296.8);
  assert.equal(game.status, 'playing');
  use(game, 'station');
  assert.equal(game.status, 'complete');
  assert.equal(game.stage, 'complete');
}

function encounter(px, pz, ex, ez, yaw) {
  const game = createGame();
  game.doorOpen = true;
  game.stage = 'street';
  Object.assign(game.player, { x: px, z: pz });
  const enemy = game.enemies.find(e => e.id === 'market');
  Object.assign(enemy, { x: ex, z: ez, yaw });
  return { game, enemy };
}

function ray(from, to) {
  const dx = to.x - from.x, dy = to.y - from.y, dz = to.z - from.z;
  const length = Math.hypot(dx, dy, dz);
  return { ...from, dx: dx / length, dy: dy / length, dz: dz / length };
}

test('only an open rear door and a fully lowered bridge connect their banks', () => {
  assert.equal(canStand(4, -31, false, false), false);
  assert.equal(canStand(4, -31, false, true), true);
  assert.equal(canStand(0, -34, false, true), false);
  assert.equal(canStand(36, -241, false, true), false);
  assert.equal(canStand(36, -241, true, true), true);
  assert.equal(canStand(32, -241, true, true), false);
  assert.equal(canStand(36, -234, true, true), true);
  assert.equal(canStand(36, -250, true, true), true);
  assert.equal(canStand(15, -55), true);
  assert.equal(canStand(15, -72), false);
});

test('camera probes distinguish low furniture, tall cover and wall clearance', () => {
  assert.equal(canStand(-4.7, 1.3), false);
  assert.equal(isWall(-4.7, 1.3, 0.7), true);
  assert.equal(isWall(-4.7, 1.3, 1.7), false);
  assert.equal(isWall(-5.5, -78, 1.7), true);
  assert.equal(isWall(-4.1, -78, 1.7), false);
  assert.equal(isWall(-4.1, -78, 1.7, true, true, 0.3), true);
});

test('the terminal radio is optional and walking straight into the closed door cannot open it', () => {
  const game = createGame();
  travel(game, 3.9, 2.6);
  travel(game, 4.3, -0.8);
  use(game, 'radio');
  assert.equal(game.radioHeard, true);
  travel(game, 4, -29.1);
  stepGame(game, { forward: 1, yaw: 0, sprint: true }, 3);
  assert.equal(game.doorOpen, false);
  assert.ok(game.player.z > -31);
  assert.equal(game.stage, 'terminal');
  use(game, 'door');
  travel(game, 4, -44);
  assert.equal(game.stage, 'street');
});

test('the shopping alley reaches the police entrance with an empty inventory', () => {
  const game = createGame();
  exitTerminal(game);
  travel(game, 4, -56.6);
  travel(game, 23.7, -56.6);
  travel(game, 23.7, -153, false);
  travel(game, 2.5, -153);
  finishFromStreet(game);
  assert.equal(game.player.hasGun, false);
  assert.equal(game.shotsFired, 0);
});

test('the main street can be completed after taking the pistol and firing', () => {
  const game = createGame();
  exitTerminal(game);
  travel(game, 5.1, -54);
  use(game, 'pistol');
  assert.equal(game.player.ammo, 5);
  travel(game, 0.9, -61);
  travel(game, 0.9, -64);
  const nearest = game.enemies.find(e => e.id === 'market');
  const yaw = Math.atan2(nearest.x - game.player.x, game.player.z - nearest.z);
  stepGame(game, { aim: true, fire: true, yaw }, 0.35);
  assert.equal(game.hits, 1);
  assert.equal(game.player.ammo, 4);
  stepGame(game, { aim: true, fire: true, yaw }, 0.35);
  assert.equal(nearest.mode, 'down');
  travel(game, 1, -127);
  travel(game, 3, -144);
  travel(game, 2.5, -153);
  finishFromStreet(game);
});

test('an approaching player can be seen across a clear lane but is hidden behind the van', () => {
  const open = encounter(-2.5, -71, -2.5, -82, Math.PI);
  stepGame(open.game, {}, 0.05);
  assert.equal(open.enemy.mode, 'chase');
  const covered = encounter(-5.5, -71, -5.5, -82, Math.PI);
  stepGame(covered.game, {}, 0.05);
  assert.equal(covered.enemy.mode, 'patrol');
});

test('a running footfall behind a watcher attracts it from farther away than walking', () => {
  for (const sprint of [false, true]) {
    const { game, enemy } = encounter(0, -78, 0, -85, 0);
    stepGame(game, { forward: 1, yaw: 0, sprint }, 0.05);
    assert.equal(enemy.mode, sprint ? 'investigate' : 'patrol');
  }
});

test('turning into the side alley can break contact and return the watcher to its patrol', () => {
  const { game, enemy } = encounter(7.6, -103, 0, -103, Math.PI / 2);
  stepGame(game, {}, 0.05);
  assert.equal(enemy.mode, 'chase');
  travel(game, 23.7, -103);
  travel(game, 23.7, -121);
  stepGame(game, {}, 12);
  assert.equal(enemy.mode, 'patrol');
  assert.equal(game.player.hp, 100);
});

test('a loud shot behind solid cover brings a watcher around the van', () => {
  const { game, enemy } = encounter(-5.5, -71, -5.5, -82, Math.PI);
  Object.assign(game.player, { hasGun: true, ammo: 5 });
  stepGame(game, { aim: true, fire: true, yaw: 0 }, 0.05);
  assert.equal(game.hits, 0);
  assert.equal(enemy.mode, 'investigate');
  let leftItsLane = false;
  for (let i = 0; i < 140; i++) {
    stepGame(game, {}, frame);
    leftItsLane ||= Math.abs(enemy.x + 5.5) > 1.6;
    assert.equal(canStand(enemy.x, enemy.z, false, true), true);
  }
  assert.ok(leftItsLane);
  assert.ok(enemy.z > -75, 'watcher should have reached the other side');
});

test('a five-round pickup cannot be replenished, and a second hit brings a watcher down', () => {
  const { game, enemy } = encounter(5.5, -54, 5.5, -64, Math.PI);
  use(game, 'pistol');
  for (let i = 0; i < 6; i++) {
    stepGame(game, { aim: true, fire: true, yaw: 0 }, 0.4);
  }
  assert.equal(game.shotsFired, 5);
  assert.equal(game.hits, 2);
  assert.equal(enemy.mode, 'down');
  assert.equal(game.player.ammo, 0);
  assert.equal(getInteraction(game), null);
  assert.ok(game.events.some(event => event.type === 'empty'));
});

test('the actual camera ray can shoot over or beside a watcher and can hit its torso', () => {
  const { game, enemy } = encounter(0, -69, 0, -79, Math.PI);
  Object.assign(game.player, { hasGun: true, ammo: 5 });
  const camera = { x: 1.65, y: 2.3, z: -66 };
  const shoot = (target) => stepGame(game, { aim: true, fire: true, yaw: 0, shotRay: ray(camera, target) }, 0.4);
  shoot({ x: enemy.x, z: enemy.z, y: 3.7 });
  assert.equal(game.hits, 0);
  shoot({ x: enemy.x + 1.2, z: enemy.z, y: 1.2 });
  assert.equal(game.hits, 0);
  shoot({ x: enemy.x, z: enemy.z, y: 1.2 });
  assert.equal(game.hits, 1);
  assert.equal(game.player.ammo, 2);
});

test('a camera peeking past a van cannot shoot through it from the player position', () => {
  const { game, enemy } = encounter(-5.5, -71.1, -5.5, -82, Math.PI);
  Object.assign(game.player, { hasGun: true, ammo: 5 });
  const shotRay = ray({ x: -3.5, y: 1.9, z: -80.8 }, { x: enemy.x, y: 1.35, z: enemy.z });
  stepGame(game, { aim: true, fire: true, shotRay }, 0.05);
  assert.equal(game.hits, 0);
});

test('bridge lowering takes about eight seconds and draws watchers from both service lanes', () => {
  const game = createGame();
  game.stage = 'quay';
  game.doorOpen = true;
  Object.assign(game.player, { x: 38.5, z: -228.5 });
  const guard = game.enemies.find(e => e.id === 'lock');
  const second = game.enemies.find(e => e.id === 'spill');
  assert.ok(second, 'the west service lane needs its own watcher');
  Object.assign(guard, { x: 36.5, z: -208, yaw: Math.PI });
  Object.assign(second, { x: 31.1, z: -204.4, yaw: Math.PI });
  use(game, 'panel');
  assert.equal(guard.mode, 'investigate');
  assert.equal(second.mode, 'investigate');
  const oldDistance = Math.hypot(second.x - 39, second.z + 229);
  stepGame(game, {}, 7);
  assert.ok(Math.hypot(second.x - 39, second.z + 229) < oldDistance - 4);
  assert.ok(game.bridgeProgress > 0.8 && game.bridgeProgress < 1);
  assert.equal(canStand(36, -237, game.bridgeProgress === 1, true), false);
  stepGame(game, {}, 1.2);
  assert.equal(game.bridgeProgress, 1);
  assert.equal(canStand(36, -237, true, true), true);
});

test('contact can kill, time stops after death, and retry creates a fresh run', () => {
  const { game } = encounter(0, -78.5, 0, -79.3, Math.PI);
  stepGame(game, {}, 0.1);
  assert.ok(game.player.hp < 100);
  stepGame(game, {}, 12);
  assert.equal(game.status, 'dead');
  assert.equal(game.player.hp, 0);
  const stamp = game.elapsed;
  stepGame(game, { forward: 1, interact: true }, 1);
  assert.equal(game.elapsed, stamp);
  const retry = createGame();
  assert.equal(retry.status, 'playing');
  assert.deepEqual([retry.player.x, retry.player.z, retry.player.hp, retry.player.ammo], [-2, 5.8, 100, 0]);
  assert.equal(retry.doorOpen || retry.bridgeStarted || retry.radioHeard, false);
});

test('the police entrance can only be opened within reach of its handle', () => {
  const game = createGame();
  game.stage = 'courtyard';
  Object.assign(game.player, { x: 28, z: -294.8 });
  assert.equal(getInteraction(game), null);
  Object.assign(game.player, { z: -296.9 });
  assert.equal(getInteraction(game)?.id, 'station');
});

test('the waiting hall piers and the station vestibule block passage', () => {
  assert.equal(canStand(0.7, -8.55), false);
  assert.equal(canStand(0.7, -23.8), false);
  assert.equal(canStand(28, -298.6, true, true), false);
  assert.equal(canStand(28, -296.9, true, true), true);
});

test('floodwater on the boulevard slows a walking player and still allows an escape sprint', () => {
  function distanceInLane(x, sprint) {
    const game = createGame();
    game.enemies = [];
    Object.assign(game.player, {x, z: -90});
    stepGame(game, {forward: 1, yaw: 0, sprint}, 1);
    return -90 - game.player.z;
  }
  assert.ok(distanceInLane(0, false) < distanceInLane(23, false) * .82);
  assert.ok(distanceInLane(0, true) > 2.3);
});
