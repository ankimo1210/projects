import { HarborAudio } from './audio';
import { createGame, getInteraction, stepGame } from './simulation';
import type { Stage } from './simulation';
import { HarborWorld } from './world';

const element = <E extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id)! as E;
const canvas = element<HTMLCanvasElement>('view'),
  loading = element('loading');
const audio = new HarborAudio();
let world: HarborWorld;
try {
  world = new HarborWorld(canvas);
} catch (error) {
  loading.querySelector('p')!.textContent =
    '3D画面を開けませんでした。WebGL 2 対応ブラウザで再読み込みしてください。';
  throw error;
}

const chapters: Record<Stage, [string, string, string, string]> = {
  terminal: ['01', 'FERRY TERMINAL', '渡船ターミナル', '非常灯をたどり、裏口を探す'],
  street: ['02', 'SHIOMI ARCADE', '潮見商店街', '商店街を抜け、第二水門へ向かう'],
  quay: ['03', 'FLOOD CONTROL', '水門保守通路', '操作盤で歩道橋を下ろす'],
  bridge: ['03', 'FLOOD CONTROL', '水門歩道橋', '降下を待ち、橋の先の誘導灯へ'],
  courtyard: ['04', 'POLICE STATION', '警察署前庭', '正面玄関に手をかける'],
  complete: ['04', 'POLICE STATION', '汐凪警察署', ''],
};
const keys = new Set<string>();
let game = createGame(),
  yaw = -0.53,
  pitch = 0.012,
  aim = false,
  fire = false,
  use = false,
  paused = false,
  mode: 'pause' | 'dead' | 'complete' = 'pause';
let engaged = false,
  started = false,
  muted = false,
  ignoreUnlock = false,
  softLook = false,
  lockPending = false;
let shownStage: Stage = 'terminal',
  stageAt = 0,
  stageDistance = 0,
  captionTime = 0,
  shutter = false,
  shadowCue = false,
  dragIn = 4,
  endTime = 0;
let previous = performance.now();
const ui = {
  location: element('location'),
  num: element('area-num'),
  en: element('area-en'),
  jp: element('area-jp'),
  objective: element('objective'),
  life: [...element('life-bars').children],
  hp: element('hp'),
  ammo: element('ammo'),
  ammoLabel: element('ammo-label'),
  weapon: document.getElementById('equip-symbol')!,
  gunGuide: element('gun-guide'),
  reticle: element('reticle'),
  injury: element('injury'),
  interact: element('interact'),
  interaction: element('interaction'),
  notice: element('notice'),
  radio: element('radio-caption'),
  look: element('look-guide').querySelector('span')!,
  pause: element<HTMLButtonElement>('pause'),
  sound: element<HTMLButtonElement>('sound'),
  menu: element('menu'),
  kicker: element('menu-kicker'),
  title: element('menu-title'),
  copy: element('menu-copy'),
  keyList: element('key-list'),
  button: element<HTMLButtonElement>('continue'),
  curtain: element('curtain'),
};
function awaken() {
  if (!started) {
    started = true;
    canvas.focus({ preventScroll: true });
  }
  audio.unlock();
}
function release() {
  keys.clear();
  aim = false;
  fire = false;
  use = false;
  if (document.pointerLockElement === canvas) {
    ignoreUnlock = true;
    document.exitPointerLock();
  }
  engaged = false;
  softLook = false;
  ui.look.textContent = 'クリックで視点操作';
}
function lock() {
  if (document.pointerLockElement === canvas || lockPending || softLook) return;
  engaged = true;
  ui.look.textContent = '視点';
  if (!canvas.requestPointerLock) {
    softLook = true;
    return;
  }
  lockPending = true;
  try {
    const pending = canvas.requestPointerLock();
    if (pending)
      pending.catch(() => {
        lockPending = false;
        softLook = true;
      });
  } catch {
    lockPending = false;
    softLook = true;
  }
}
function menus(kind: 'pause' | 'dead' | 'complete') {
  mode = kind;
  paused = kind === 'pause';
  release();
  audio.setPaused(true);
  ui.menu.hidden = false;
  ui.menu.classList.toggle('result', kind !== 'pause');
  ui.keyList.hidden = kind !== 'pause';
  if (kind === 'pause') {
    ui.kicker.textContent = 'PAUSED';
    ui.title.textContent = '一時停止';
    ui.copy.textContent = chapters[game.stage][3];
    ui.button.replaceChildren('ゲームに戻る');
  } else {
    ui.kicker.textContent = kind === 'dead' ? 'SIGNAL LOST' : 'EVACUATION COMPLETE';
    ui.title.textContent = kind === 'dead' ? '途絶' : '汐凪警察署に到着';
    ui.copy.textContent = kind === 'dead' ? '雨音だけが、通りに残った。' : '扉の向こうで、雨音が遠ざかる。';
    ui.button.replaceChildren(kind === 'dead' ? 'ターミナルからリトライ' : 'もう一度プレイ');
  }
  const arrow = document.createElement('span');
  arrow.textContent = '↗';
  ui.button.append(arrow);
  ui.button.focus({ preventScroll: true });
}
function resume() {
  if (ui.menu.hidden) return;
  if (mode !== 'pause') {
    audio.reset();
    game = createGame();
    yaw = -0.53;
    pitch = 0.012;
    world.reset(yaw);
    shownStage = 'terminal';
    stageAt = 0;
    stageDistance = 0;
    captionTime = 0;
    shutter = false;
    shadowCue = false;
    dragIn = 4;
    endTime = 0;
    setLocation();
    ui.curtain.classList.remove('black');
  }
  paused = false;
  ui.menu.hidden = true;
  audio.setPaused(false);
  awaken();
  lock();
  canvas.focus({ preventScroll: true });
  previous = performance.now();
}
function togglePause() {
  if (game.status !== 'playing') return;
  if (paused) resume();
  else menus('pause');
}
ui.pause.addEventListener('click', () => {
  awaken();
  togglePause();
});
ui.button.addEventListener('click', resume);
ui.sound.addEventListener('click', () => {
  awaken();
  muted = !muted;
  audio.setMuted(muted);
  ui.sound.setAttribute('aria-pressed', String(muted));
  ui.sound.setAttribute('aria-label', muted ? '音声をオン' : '音声をミュート');
  document.getElementById('sound-icon')!.setAttribute('href', muted ? '#i-muted' : '#i-volume');
  canvas.focus({ preventScroll: true });
});
const controlKeys = new Set([
  'KeyW',
  'KeyA',
  'KeyS',
  'KeyD',
  'ShiftLeft',
  'ShiftRight',
  'KeyE',
  'ArrowLeft',
  'ArrowRight',
  'ArrowUp',
  'ArrowDown',
]);
document.addEventListener('keydown', (e) => {
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  if (e.code === 'Escape') {
    e.preventDefault();
    if (!e.repeat) togglePause();
    return;
  }
  if (!controlKeys.has(e.code) || paused || game.status !== 'playing') return;
  e.preventDefault();
  awaken();
  keys.add(e.code);
  if (e.code === 'KeyE' && !e.repeat) use = true;
});
document.addEventListener('keyup', (e) => keys.delete(e.code));
canvas.addEventListener('contextmenu', (e) => e.preventDefault());
canvas.addEventListener('mousedown', (e) => {
  if (paused || game.status !== 'playing') return;
  e.preventDefault();
  awaken();
  const already = engaged;
  lock();
  if (e.button === 2) aim = true;
  if (e.button === 0 && (already || aim)) fire = true;
});
document.addEventListener('mouseup', (e) => {
  if (e.button === 2) aim = false;
});
document.addEventListener('mousemove', (e) => {
  if (
    paused ||
    game.status !== 'playing' ||
    !(document.pointerLockElement === canvas || (softLook && engaged))
  )
    return;
  const sensitivity = aim && game.player.hasGun ? 0.00165 : 0.00265;
  yaw += e.movementX * sensitivity;
  pitch = Math.min(0.6, Math.max(-0.62, pitch - e.movementY * sensitivity));
});
document.addEventListener('pointerlockchange', () => {
  lockPending = false;
  if (document.pointerLockElement === canvas) {
    engaged = true;
    softLook = false;
    ui.look.textContent = '視点';
    return;
  }
  if (ignoreUnlock) {
    ignoreUnlock = false;
    return;
  }
  if (engaged && !paused && game.status === 'playing') menus('pause');
});
document.addEventListener('pointerlockerror', () => {
  lockPending = false;
  softLook = true;
});
function backgrounded() {
  if (started && !paused && game.status === 'playing') menus('pause');
}
document.addEventListener('visibilitychange', () => {
  if (document.hidden) backgrounded();
});
window.addEventListener('blur', backgrounded);
function setLocation() {
  const info = chapters[game.stage];
  ui.num.textContent = 'AREA ' + info[0];
  ui.en.textContent = info[1];
  ui.jp.textContent = info[2];
  ui.objective.textContent = info[3];
  ui.location.classList.remove('compact');
}
function panAt(x: number, z: number) {
  const dx = x - game.player.x,
    dz = z - game.player.z,
    d = Math.hypot(dx, dz);
  return Math.max(-0.93, Math.min(0.93, (dx * Math.cos(yaw) + dz * Math.sin(yaw)) / Math.max(2, d)));
}
function playEvents(dt: number) {
  const q = game.player;
  for (const e of game.events) {
    const pan = panAt(e.x, e.z);
    switch (e.type) {
      case 'footstep':
        audio.play(q.running ? 'run' : 'step');
        break;
      case 'door':
        audio.play('door');
        break;
      case 'radio':
        captionTime = 0;
        audio.play('handset');
        break;
      case 'pickup':
        audio.play('pickup');
        break;
      case 'shot':
        audio.play('shot');
        break;
      case 'empty':
        audio.play('empty');
        break;
      case 'damage':
        audio.play('hit');
        break;
      case 'alert':
      case 'pursuit':
        audio.play('drag', pan);
        break;
      case 'bridge-start':
        audio.play('bridge', pan);
        break;
      case 'bridge-open':
        audio.play('door', pan);
        break;
      case 'dead':
        audio.play('death');
        release();
        endTime = 0.95;
        break;
      case 'complete':
        audio.play('clear');
        release();
        ui.curtain.classList.add('black');
        endTime = 1.24;
        break;
    }
  }
  if (!shadowCue && q.distanceWalked > 1.0 && game.stage === 'terminal') {
    shadowCue = true;
    audio.play('drag', -0.88);
  }
  if (!shutter && q.z < -34.2) {
    shutter = true;
    audio.play('shutter', 0.85);
  }
  let nearest = 99,
    ex = 0,
    ez = 0;
  for (const e of game.enemies) {
    const d = Math.hypot(q.x - e.x, q.z - e.z);
    if (e.active && e.mode !== 'down' && d < nearest) {
      nearest = d;
      ex = e.x;
      ez = e.z;
    }
  }
  dragIn -= dt;
  if (nearest < 20 && dragIn <= 0) {
    audio.play('drag', panAt(ex, ez));
    dragIn = 2.9 + Math.min(3, nearest * 0.12);
  }
  audio.tick(dt, Math.max(0, Math.min(1, (-q.z - 29) / 12)), Math.max(0, 1 - nearest / 15));
}
function drawHud() {
  if (shownStage !== game.stage) {
    shownStage = game.stage;
    stageAt = game.elapsed;
    stageDistance = game.player.distanceWalked;
    setLocation();
  }
  const q = game.player;
  // Leave the first instruction visible while the player is still learning the controls.
  ui.location.classList.toggle(
    'compact',
    q.distanceWalked - stageDistance > 14 && game.elapsed - stageAt > 13,
  );
  const hp = String(q.hp);
  if (ui.hp.textContent !== hp) {
    ui.hp.textContent = hp;
    ui.life.forEach((v, i) => v.classList.toggle('lost', i >= Math.ceil(q.hp / 10)));
  }
  const ammo = q.hasGun ? String(q.ammo).padStart(2, '0') : '―';
  if (ui.ammo.textContent !== ammo) {
    ui.ammo.textContent = ammo;
    ui.ammoLabel.textContent = q.hasGun ? '発' : '未装備';
    ui.weapon.setAttribute('href', q.hasGun ? '#i-gun' : '#i-pouch');
  }
  ui.gunGuide.hidden = !q.hasGun;
  ui.reticle.hidden = !q.aiming || game.status !== 'playing' || paused;
  ui.injury.style.opacity = String(game.damageFlash * 0.83);
  const prompt = getInteraction(game);
  ui.interact.hidden = !prompt || paused;
  if (prompt) ui.interaction.textContent = prompt.text;
  const lowering = game.bridgeStarted && game.bridgeProgress < 1 && game.stage === 'bridge';
  const msg = lowering
    ? '歩道橋が降下中　' + Math.round(game.bridgeProgress * 100) + '%'
    : game.messageTime > 0
      ? game.message
      : '';
  ui.notice.hidden = !msg || game.status !== 'playing' || paused;
  if (msg && ui.notice.textContent !== msg) ui.notice.textContent = msg;
  ui.radio.hidden =
    captionTime <= 0 || Boolean(msg) || Boolean(prompt) || paused || game.status !== 'playing';
}
// Caption the recurring municipal announcement at its actual start.
audio.onBroadcast = () => {
  captionTime = 8.4;
};
function frame(now: number) {
  const dt = Math.max(0, Math.min((now - previous) / 1000, 0.28));
  previous = now;
  if (!paused && ui.menu.hidden) {
    if (game.status === 'playing' && started) {
      const steer = Number(keys.has('ArrowRight')) - Number(keys.has('ArrowLeft'));
      const tilt = Number(keys.has('ArrowUp')) - Number(keys.has('ArrowDown'));
      yaw += steer * dt * 1.65;
      pitch = Math.max(-0.62, Math.min(0.6, pitch + tilt * dt * 0.8));
      const forward = Number(keys.has('KeyW')) - Number(keys.has('KeyS')),
        right = Number(keys.has('KeyD')) - Number(keys.has('KeyA'));
      const input = {
        forward,
        right,
        yaw,
        sprint: keys.has('ShiftLeft') || keys.has('ShiftRight'),
        interact: use,
        aim,
        fire,
        shotRay: fire ? world.shotRay() : undefined,
      };
      stepGame(game, input, dt);
      use = false;
      fire = false;
      captionTime = Math.max(0, captionTime - dt);
      playEvents(dt);
    } else if (endTime > 0) {
      endTime -= dt;
      if (endTime <= 0) menus(game.status === 'complete' ? 'complete' : 'dead');
    }
    world.frame(game, yaw, pitch, dt);
    drawHud();
  }
  requestAnimationFrame(frame);
}
world.reset(yaw);
world.frame(game, yaw, pitch, 1 / 60);
drawHud();
loading.hidden = true;
requestAnimationFrame(frame);
