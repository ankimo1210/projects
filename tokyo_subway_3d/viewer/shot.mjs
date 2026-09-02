// Render both modes headlessly: node viewer/shot.mjs  (serve the project root on :8137 first)
import { chromium } from '/home/kazumasa/projects/b737-ops-sim/node_modules/.pnpm/playwright@1.62.1/node_modules/playwright/index.mjs';
const out = process.argv[2] || '/tmp';
const b = await chromium.launch({ args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'] });
const p = await b.newPage({ viewport:{width:1440,height:900}, deviceScaleFactor:1 });
const errs=[];
p.on('console', m => { if (m.type()==='error') errs.push(m.text()); });
p.on('pageerror', e => errs.push('PAGEERROR: '+e.message));
await p.goto('http://localhost:8137/viewer/', { waitUntil:'networkidle', timeout:60000 });
await p.waitForTimeout(6000);
await p.screenshot({ path:`${out}/viewer_surface.png` });
await p.evaluate(()=>window.__setMode('underground')); await p.waitForTimeout(5000);
await p.screenshot({ path:`${out}/viewer_underground.png` });
console.log('lines:', await p.locator('#lines label').count(), '| src:', await p.locator('#src').innerText().then(t=>t.split('\n').pop()));
console.log('errors:', errs.length ? errs.slice(0,8).join('\n') : 'none');
await b.close();
