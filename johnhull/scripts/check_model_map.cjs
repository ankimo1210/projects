// Offline browser contract for the guide map, glossary and chapter connections.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const {pathToFileURL, fileURLToPath} = require('node:url');
const output = process.env.MODEL_MAP_OUTPUT_DIR;
assert(output && output.trim(), 'Set MODEL_MAP_OUTPUT_DIR to a new output directory');
const playwright = process.env.PLAYWRIGHT_MODULE;
assert.equal(require(path.join(playwright, 'package.json')).version, '1.56.0');
const {chromium} = require(playwright);
const project = path.resolve(process.env.READING_GUIDE_PROJECT || 'johnhull');
const definition = JSON.parse(fs.readFileSync(path.join(project, 'book/notebooks/guide/model_map.json')));
const htmlRoot = path.join(project, 'book/_build/html/notebooks');
const pages = ['guide/models.html', 'guide/glossary.html', '00_overview.html'];
const results = [];
const fileCache = new Map();
const slug = s => s.toLowerCase().replace(/[^\p{L}\p{N}_\- ]/gu, '').replace(/ /g, '-');
function localTarget(href) {
  const u = new URL(href);
  if (u.protocol !== 'file:') return true;
  const file = fileURLToPath(u);
  if (!fs.existsSync(file)) return false;
  if (!u.hash) return true;
  if (!fileCache.has(file)) fileCache.set(file, fs.readFileSync(file, 'utf8'));
  const text = fileCache.get(file), id = decodeURIComponent(u.hash.slice(1));
  if (file.endsWith('.md')) return text.split('\n').some(line => /^#+ /.test(line) && slug(line.replace(/^#+ /, '')) === id);
  return text.includes(`id="${id}"`) || text.includes(`id='${id}'`);
}
(async () => {
 fs.mkdirSync(output, {recursive:true});
 const browser = await chromium.launch({executablePath: process.env.CHROMIUM_BIN});
 try {
  for (const width of [1280,390]) {
   const context = await browser.newContext({viewport:{width,height:900},locale:'ja-JP',timezoneId:'Asia/Tokyo',hasTouch:width<600});
   for (const filename of pages) {
    const page = await context.newPage(), external=[],errors=[];
    page.on('request',r=>{if(!/^(file:|data:|about:|blob:)/.test(r.url()))external.push(r.url());});
    page.on('pageerror',e=>errors.push(String(e)));
    await page.route(/^https?:/,route=>route.abort());
    const target=path.join(htmlRoot,filename);
    await page.goto(pathToFileURL(target).href,{waitUntil:'load'});
    await page.evaluate(async()=>{if(window.MathJax?.startup)await MathJax.startup.promise;await document.fonts.ready;});
    if(filename.endsWith('models.html')) await page.waitForFunction(()=>window.readingModelMapReady||window.readingModelMapError);
    const info=await page.evaluate(()=>{
     const a=document.querySelector('article.bd-article');
     return {documentWidth:document.documentElement.scrollWidth,width:innerWidth,mathVersion:window.MathJax?.version,
      mathErrors:a.querySelectorAll('mjx-merror,.merror').length,rawMath:a.querySelectorAll('.math:not(:has(mjx-container))').length,
      mathOverflow:[...a.querySelectorAll('mjx-container')].map((m,index)=>({index,width:m.getBoundingClientRect().width})).filter(m=>m.width>a.getBoundingClientRect().width+1),
      tableOverflow:[...a.querySelectorAll('table')].map((t,index)=>({index,width:t.getBoundingClientRect().width,available:t.parentElement.clientWidth})).filter(t=>t.width>t.available+1),
      links:[...a.querySelectorAll('a[href]')].map(e=>e.href),modelError:window.readingModelMapError||null};
    });
    const badLinks=info.links.filter(href=>!localTarget(href));delete info.links;
    const interactions=[];
    if(filename.endsWith('models.html')&&!info.modelError) {
     for(const group of definition.groups) {
      await page.selectOption('#model-map-family',group.id);
      const expected=definition.cards.filter(c=>c.group===group.id).map(c=>c.id).sort();
      await page.waitForFunction(want=>{
       const gd=document.getElementById('reading-model-map');
       const got=gd._fullData.filter(t=>t.visible&&t.customdata).flatMap(t=>t.customdata).sort();
       return JSON.stringify(got)===JSON.stringify(want);
      },expected);
      await page.locator('#reading-model-map-controls').evaluate(e=>e.scrollIntoView({behavior:'instant',block:'start'}));
      await page.evaluate(()=>scrollBy({top:-65,behavior:'instant'}));
      await page.screenshot({path:path.join(output,`map-${group.id}-${width}.png`)});
      interactions.push({group:group.id,visibleCards:expected.length});
     }
     await page.selectOption('#model-map-family','pricing');
     await page.waitForFunction(()=>document.getElementById('reading-model-map')._fullData.some(t=>t.visible&&t.customdata?.includes('bsm')));
     const before=await page.evaluate(()=>document.getElementById('reading-model-map').layout.xaxis.range.slice());
     await page.click('#model-map-zoom-in');
     await page.waitForFunction(previous=>{const r=document.getElementById('reading-model-map').layout.xaxis.range;return r[1]-r[0]<previous[1]-previous[0];},before);
     await page.click('#model-map-reset');
     const point=page.locator('#reading-model-map .scatterlayer .point:visible').first();
     await point.scrollIntoViewIfNeeded();
     const pointBox=await point.boundingBox();assert(pointBox);
     // Plotly's drag layer receives pointer events and performs point hit testing.
     const x=pointBox.x+pointBox.width/2,y=pointBox.y+pointBox.height/2;
     if(width<600)await page.touchscreen.tap(x,y);else await page.mouse.click(x,y);
     await page.waitForFunction(()=>location.hash==='#model-bsm');
     const box=await page.locator('#model-bsm').boundingBox();
     assert(box&&box.y>=-1&&box.y<900, 'Node click/tap must bring the model card into view');
     // The selector is an accessible alternative to targeting graph points.
     await page.selectOption('#model-map-card','rough-kernel');
     await page.waitForFunction(()=>location.hash==='#model-rough-kernel');
     await page.screenshot({path:path.join(output,`card-${width}.png`)});
    } else await page.screenshot({path:path.join(output,`${path.basename(filename,'.html')}-${width}.png`)});
    const result={filename,...info,badLinks,external,errors,interactions,htmlBytes:fs.statSync(target).size};results.push(result);
    console.log(JSON.stringify(result));
    await page.close();
   }
   await context.close();
  }
  const context=await browser.newContext({javaScriptEnabled:false,viewport:{width:390,height:900}});
  const page=await context.newPage();await page.goto(pathToFileURL(path.join(htmlRoot,'guide/models.html')).href);
  const readable=await page.locator('article.bd-article h3').allTextContents();
  for(const card of definition.cards) assert(readable.some(t=>t.includes(card.name)),card.id+' must be readable without JS');
  await page.screenshot({path:path.join(output,'no-js-390.png')});
  await context.close();
  fs.writeFileSync(path.join(output,'model-map-browser.json'),JSON.stringify({checkedAt:new Date().toISOString(),playwright:'1.56.0',chromium:browser.version(),noJsCards:definition.cards.length,results},null,2)+'\n');
  assert(results.every(r=>r.width===r.documentWidth&&!r.mathErrors&&!r.rawMath&&!r.mathOverflow.length&&!r.tableOverflow.length&&!r.badLinks.length&&!r.external.length&&!r.errors.length&&!r.modelError),'Inspect model-map-browser.json');
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
