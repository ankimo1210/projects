import { App } from "./ui/app";
import { ArtBank } from "./ui/render/art";
import { H, W } from "./ui/render/layout";

const canvas = document.getElementById("game") as HTMLCanvasElement;
const ctx = canvas.getContext("2d");
if (!ctx) throw new Error("no 2d context");

// Logical W×H, backed by a store sized for the display so sprites stay crisp.
// CSS scales the element down on narrow windows (index.html).
const dpr = Math.min(2, window.devicePixelRatio || 1);
canvas.width = Math.round(W * dpr);
canvas.height = Math.round(H * dpr);
canvas.style.width = `${W}px`;
ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

const art = new ArtBank();
void art.load();
const app = new App(ctx, window.localStorage, () => performance.now(), art);
// dev only: lets a browser session drive screens without playing to them
if (import.meta.env.DEV) (window as unknown as { app: App }).app = app;
app.draw();

canvas.addEventListener("pointerdown", (ev) => {
  // the backing store is scaled by dpr and the element by CSS, so go through
  // the rect rather than assuming either
  const r = canvas.getBoundingClientRect();
  app.click(((ev.clientX - r.left) / r.width) * W, ((ev.clientY - r.top) / r.height) * H);
});

window.addEventListener("keydown", (ev) => {
  if (ev.metaKey || ev.ctrlKey || ev.altKey) return;
  const handled = ev.key.length === 1 || ["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Enter", "Escape", "Tab"].includes(ev.key);
  if (!handled) return;
  ev.preventDefault();
  app.key(ev.key);
});

// animation loop: camera easing, movement slides, damage numbers
let last = 0;
const frame = (ts: number): void => {
  // full rate while the camera or a hit animation is running, a slow idle tick
  // otherwise (props and items keep bobbing)
  if (app.busy || ts - last > 50) {
    last = ts;
    app.draw();
  }
  requestAnimationFrame(frame);
};
requestAnimationFrame(frame);

declare global {
  interface Window {
    __mg: App;
  }
}
window.__mg = app;
