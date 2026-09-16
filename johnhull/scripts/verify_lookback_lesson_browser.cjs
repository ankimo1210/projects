// §26.11 rendered acceptance; existing runtime only, no npm installation.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = path.resolve(__dirname, '..');
const relativeOut = 'docs/validation/section-26-11/';
const out = path.join(root, relativeOut);
const reference = JSON.parse(fs.readFileSync(path.join(out, 'browser-reference.json'), 'utf8'));
const timeout = Number(process.env.CHECK_TIMEOUT_MS || 30000);
const keys = ['lookback_payoffs', 'lookback_history', 'lookback_replication', 'lookback_monitoring'];
const contracts = ['floating_call', 'floating_put', 'fixed_call', 'fixed_put'];
const result = { checked_at: new Date().toISOString(), pages: {}, source_sha256: {}, artifact_sha256: {} };
function check(ok, message) { if (!ok) throw new Error(message); }
function close(a, b, message) { check(Number.isFinite(a) && Math.abs(a - b) <= 2e-8, `${message}: ${a} != ${b}`); }
function hash(file) { return crypto.createHash('sha256').update(fs.readFileSync(path.join(root, file))).digest('hex'); }
async function traces(plot) {
  return plot.evaluate(el => el._fullData.filter(t => t.visible === true)
    .map(t => ({ meta: t.meta, x: Array.from(t.x || []), y: Array.from(t.y || []) })));
}
function trace(rows, role, extra = {}) {
  const found = rows.filter(t => t.meta?.role === role && Object.entries(extra).every(([k,v]) => t.meta[k] === v));
  check(found.length === 1, 'Expected unique trace ' + role + JSON.stringify(extra));
  return found[0];
}
function point(row, x, expected, message) {
  const i = row.x.findIndex(v => typeof v === 'number' && Math.abs(v - x) < 1e-10);
  check(i >= 0, 'Missing point ' + message); close(row.y[i], expected, message);
}
function interpolate(row, x) {
  for (let i = 1; i < row.x.length; i++) if (row.x[i-1] <= x && x <= row.x[i])
    return row.y[i-1] + (row.y[i]-row.y[i-1]) * (x-row.x[i-1]) / (row.x[i]-row.x[i-1]);
  throw new Error('Missing interpolation interval ' + x);
}
function bars(rows, expected) {
  const row = trace(rows, 'payoffs');
  check(JSON.stringify(row.x) === JSON.stringify(contracts), 'Payoff contract order');
  expected.forEach((v,i) => close(row.y[i], v, 'payoff ' + contracts[i]));
}
function spot(rows) {
  const row = trace(rows, 'spot');
  check(row.x.length === reference.path.times.length, 'Full toy path length');
  reference.path.times.forEach((t,i) => { close(row.x[i],t,'path time'); close(row.y[i],reference.path.prices[i],'path price'); });
}
function replication(rows, kind) {
  for (const pin of reference.replication.filter(p => p.kind === kind))
    for (const role of ['floating_leg','stock_leg','cash_leg','reconstructed','fixed'])
      point(trace(rows, role, {kind}), pin.strike, pin[role], kind + ' ' + role + ' K=' + pin.strike);
}
async function settle(page) {
  await page.evaluate(() => document.fonts.ready);
  await page.waitForFunction(() => !document.getAnimations().some(a => a.playState === 'running'), null, {timeout});
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
}
async function center(page, locator) {
  await locator.evaluate(el => el.scrollIntoView({block:'center', inline:'nearest', behavior:'instant'}));
  await settle(page);
  const shift = await locator.evaluate(el => {
    const bottom = Math.max(0, ...Array.from(document.querySelectorAll('.topbar,.bd-header-article'))
      .map(n => n.getBoundingClientRect()).filter(r => r.top >= -1 && r.top < 150).map(r => r.bottom));
    return Math.min(0, el.getBoundingClientRect().top - bottom - 12);
  });
  if (shift < 0) { await page.evaluate(dy => window.scrollBy(0,dy),shift); await settle(page); }
}
async function plotFor(page, key) {
  await page.waitForFunction(key => Array.from(document.querySelectorAll('.plotly-graph-div'))
    .some(el => el.layout?.meta?.figure === key && el._fullLayout), key, {timeout});
  const ids = await page.locator('.plotly-graph-div').evaluateAll((els,key) =>
    els.filter(el => el.layout?.meta?.figure === key).map(el => el.id),key);
  check(ids.length === 1,'Unique plot ' + key);
  return page.locator('[id="' + ids[0] + '"]');
}
async function select(page, plot, label, field, expected) {
  await plot.locator('.updatemenu-header').click();
  await plot.locator('.updatemenu-dropdown-button').filter({hasText:new RegExp('^' + label + '$')}).click();
  await page.waitForFunction(({id,field,expected}) => document.getElementById(id).layout.meta[field] === expected,
    {id:await plot.getAttribute('id'),field,expected},{timeout});
  await settle(page);
  for (const width of [1440,1000]) {
    await page.setViewportSize({width,height:1050}); await settle(page);
    await layoutCheck(page,plot,label+'/'+width);
  }
  await page.setViewportSize({width:1440,height:1050}); await settle(page);
}
async function negativeControl(plot, kind) {
  const saved = await plot.evaluate(async (el,kind) => {
    const indices = ['floating_leg','stock_leg'].map(role => el._fullData.findIndex(t => t.visible === true && t.meta?.role === role && t.meta.kind === kind));
    const ys = indices.map(i => Array.from(el._fullData[i].y));
    const at = Array.from(el._fullData[indices[0]].x).findIndex(x => x === 100);
    const bad = ys.map(y => [...y]); bad[0][at] += 1; bad[1][at] -= 1;
    const totals = el._fullData.filter(t => t.visible === true && ['reconstructed','fixed'].includes(t.meta?.role)).map(t => Array.from(t.y));
    await Plotly.restyle(el, {y:bad}, indices);
    return {indices,ys,at,totals,original_sum:ys[0][at]+ys[1][at],mutated_sum:bad[0][at]+bad[1][at]};
  },kind);
  let rejected = false;
  try {
    close(saved.original_sum,saved.mutated_sum,'Negative control preserves leg sum');
    const rows = await traces(plot);
    for (const [i,role] of ['reconstructed','fixed'].entries())
      check(JSON.stringify(trace(rows,role,{kind}).y) === JSON.stringify(saved.totals[i]), 'Negative control changed total');
    try { replication(rows,kind); } catch (error) {
      check(error.message.includes('floating_leg'),'Unrelated negative control failure'); rejected = true;
    }
    check(rejected,'Misallocated individual legs passed');
  } finally { await plot.evaluate(async (el,s) => Plotly.restyle(el,{y:s.ys},s.indices),saved); }
  replication(await traces(plot),kind);
  return {kind, rejected, total_unchanged:true, mutation:'floating_leg +1, stock_leg -1 at K=100', restored:true};
}
async function layoutCheck(page,plot,label) {
  await center(page,plot);
  await page.waitForFunction(el => Math.abs(el.clientWidth-el._fullLayout.width)<3,await plot.elementHandle(),{timeout});
  const errors = await plot.evaluate(el => {
    const errors = [], frame = el.getBoundingClientRect();
    if (el.scrollWidth > el.clientWidth+3) errors.push('plot overflow');
    for (const n of el.querySelectorAll('.annotation-text,.gtitle,.xtitle,.ytitle,.xtick text,.ytick text,.legend')) {
      const b=n.getBoundingClientRect();
      if (b.width && b.height && (b.left<frame.left-3 || b.right>frame.right+3 || b.top<frame.top-3 || b.bottom>frame.bottom+3)) errors.push('clipped '+n.textContent);
    }
    const overlap=(a,b) => a.width>0 && b.width>0 && a.left<b.right-2 && a.right>b.left+2 && a.top<b.bottom-2 && a.bottom>b.top+2;
    const legend=el.querySelector('.legend')?.getBoundingClientRect();
    if(legend) for(const n of el.querySelectorAll('.annotation-text')) if(overlap(n.getBoundingClientRect(),legend)) errors.push('legend/annotation');
    for(const a of el.querySelectorAll('.xtitle,.ytitle,.xtick text,.ytick text'))
      for(const b of el.querySelectorAll('.legendtext')) if(overlap(a.getBoundingClientRect(),b.getBoundingClientRect())) errors.push('axis/legend');
    return errors;
  });
  check(errors.length===0,label+': '+errors.join('; '));
}
async function verifySurface(page,label) {
  const plots={}, states=[];
  for(const key of keys) plots[key]=await plotFor(page,key);
  for(const [scenario,name] of [['new','新規契約'],['seasoned','過去の極値あり']]) {
    await select(page,plots.lookback_payoffs,name,'scenario',scenario);
    const rows=await traces(plots.lookback_payoffs); spot(rows); bars(rows,reference.payoffs[scenario]);
    for(const pin of reference.running_extrema[scenario])
      for(const [role,field] of [['spot','spot'],['running_min','minimum'],['running_max','maximum']])
        close(interpolate(trace(rows,role),pin.time),pin[field],scenario+' '+role+' at '+pin.time);
    states.push({figure:'lookback_payoffs',scenario,interior_probes:reference.running_extrema[scenario].length});
  }
  for(const K of [80,100,125]) {
    await select(page,plots.lookback_history,'K='+K,'K',K);
    const rows=await traces(plots.lookback_history);
    for(const pin of reference.history.filter(p=>p.K===K)) for(const [contract,price] of Object.entries(pin.prices))
      point(trace(rows,'price',{contract,strike:K}),pin.extreme,price,'history '+K+' '+contract+' '+pin.extreme);
    states.push({figure:'lookback_history',K});
  }
  const negative_controls=[];
  for(const kind of ['call','put']) {
    await select(page,plots.lookback_replication,'fixed '+kind,'kind',kind);
    replication(await traces(plots.lookback_replication),kind);
    negative_controls.push(await negativeControl(plots.lookback_replication,kind));
    states.push({figure:'lookback_replication',kind});
  }
  for(const intervals of [1,2,4,8]) {
    await select(page,plots.lookback_monitoring,intervals+'区間','intervals',intervals);
    const rows=await traces(plots.lookback_monitoring); spot(rows); bars(rows,reference.monitoring[intervals]);
    const fixings=trace(rows,'fixings'), indices=Array.from({length:intervals+1},(_,i)=>i*8/intervals);
    check(fixings.x.length===indices.length,'Fixing count');
    indices.forEach((index,i)=>{close(fixings.x[i],reference.path.times[index],'fixing time');close(fixings.y[i],reference.path.prices[index],'fixing price');});
    states.push({figure:'lookback_monitoring',intervals});
  }
  const screenshots=[];
  for(const width of [1440,1000]) {
    await page.setViewportSize({width,height:1050}); await settle(page);
    check(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+3),label+' page overflow '+width);
    for(const key of keys) {
      await layoutCheck(page,plots[key],label+'/'+key+'/'+width);
      const file=relativeOut+label+'-'+key+'-'+width+'.png';
      await plots[key].screenshot({path:path.join(root,file)}); screenshots.push(file);
    }
  }
  return {figures:keys,states,negative_controls,screenshots,layout_errors:0};
}
async function bookMath(page) {
  const heading=page.locator('h3').filter({hasText:/4\.1 .*ルックバック/});
  check(await heading.count()===1,'Missing lookback h3');
  const section=heading.locator('xpath=..');
  await page.waitForFunction(()=>!!window.MathJax?.startup?.promise,null,{timeout});
  await page.evaluate(()=>window.MathJax.startup.promise);
  const math=await section.evaluate(el=>({typeset:el.querySelectorAll('mjx-container').length,errors:el.querySelectorAll('mjx-merror,.MathJax_Error').length,
    headings:Array.from(el.querySelectorAll('h4')).map(n=>n.textContent),rows:Array.from(el.querySelectorAll('tr')).map(n=>n.textContent),text:el.textContent}));
  check(math.typeset>=15 && math.errors===0,'Math typesetting failed');
  for(let i=1;i<=6;i++) check(math.headings.some(h=>h.includes('4.1.'+i)),'Missing h4 '+i);
  check(math.text.includes('abs(r-q)<1e-8') && math.text.includes('未対応'),'Missing boundary notice');
  math.prices={};
  for(const [contract,price] of Object.entries(reference.example)) {
    const label=contract.replace('_',' ');
    check(math.rows.filter(row=>row.includes(label)&&row.includes(price.toFixed(6))).length===1,'Mislabelled example '+label);
    math.prices[contract]=price.toFixed(6);
  }
  delete math.text; delete math.rows; math.screenshots=[];
  for(const width of [1440,1000]) {
    await page.setViewportSize({width,height:1050}); await settle(page);
    check(await section.evaluate(el=>Array.from(el.querySelectorAll('div.math')).every(n=>n.scrollWidth<=n.clientWidth+3)),'Math overflow '+width);
    const example=section.locator('h4').filter({hasText:/4\.1\.2/}).locator('xpath=..');
    const height=Math.ceil((await example.boundingBox()).height)+240;
    await page.setViewportSize({width,height:Math.max(1050,height)}); await settle(page); await center(page,example);
    const file=relativeOut+'book-lookback-example-'+width+'.png';
    await example.screenshot({path:path.join(root,file)}); math.screenshots.push(file);
  }
  return math;
}
(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_BIN||undefined,args:['--no-sandbox']});
  result.browser_version=browser.version();
  try {
    const context=await browser.newContext({viewport:{width:1440,height:1050}});
    for(const label of ['portal','book']) {
      const page=await context.newPage(), errors=[], requests=[];
      page.on('pageerror',e=>errors.push(e.message));
      if(label==='portal') await page.route(/^https?:/,route=>{requests.push(route.request().url());return route.abort();});
      else page.on('request',r=>{if(/^https?:/.test(r.url())) requests.push(r.url());});
      await page.goto('file://'+path.join(root,label==='portal'?'report/site/exotics.html':'book/_build/html/notebooks/10_exotics.html'));
      const math=label==='book'?await bookMath(page):undefined;
      result.pages[label]={...(await verifySurface(page,label)),math,external_network_blocked:label==='portal',external_requests:requests,page_errors:errors};
      check(errors.length===0,label+' JS errors: '+errors.join(';'));
      if(label==='portal') check(requests.length===0,'Portal external requests');
      await page.close();
    }
    for(const file of ['hullkit/src/hullkit/_lookback_lesson.py','hullkit/src/hullkit/exotics.py','hullkit/tests/test_lookback_reference.py',
      'volumes/10_exotics_martingales/build_exotics_notebook.py','volumes/10_exotics_martingales/exotics.ipynb',
      'report/report_builder/figures.py','report/report_builder/render.py','report/assets/style.css','book/_ext/book_runtime.py','book/_config.yml',
      'scripts/verify_lookback_lesson_browser.cjs',relativeOut+'browser-reference.json']) result.source_sha256[file]=hash(file);
    const artifacts=['report/site/exotics.html','report/site/assets/style.css','report/site/assets/plotly.min.js','book/_build/html/notebooks/10_exotics.html'];
    for(const p of Object.values(result.pages)) artifacts.push(...p.screenshots,...(p.math?.screenshots||[]));
    for(const file of artifacts) result.artifact_sha256[file]=hash(file);
    result.status='PASS'; console.log(JSON.stringify({status:'PASS',surfaces:2,screenshots:18,output:out},null,2));
  } finally {await browser.close();}
})().catch(error=>{result.status='FAIL';result.error=error.message;console.error(error.stack);process.exitCode=1;})
  .finally(()=>fs.writeFileSync(path.join(out,'browser-m3b-check.json'),JSON.stringify(result,null,2)+'\n'));
