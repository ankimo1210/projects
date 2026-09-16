// §26.12 rendered acceptance; existing runtime only, no npm installation.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = path.resolve(__dirname, '..');
const relativeOut = 'docs/validation/section-26-12/';
const out = path.join(root, relativeOut);
const reference = JSON.parse(fs.readFileSync(path.join(out, 'browser-reference.json'), 'utf8'));
const timeout = Number(process.env.CHECK_TIMEOUT_MS || 30000);
const keys = ['shout_payoff', 'shout_decision', 'shout_boundary', 'shout_comparison'];

const result = { checked_at: new Date().toISOString(), pages: {}, source_sha256: {}, artifact_sha256: {} };
function check(ok, message) { if (!ok) throw new Error(message); }
function close(a, b, message) { check(Number.isFinite(a) && Math.abs(a - b) <= 1e-8, `${message}: ${a} != ${b}`); }
function hash(file) { return crypto.createHash('sha256').update(fs.readFileSync(path.join(root, file))).digest('hex'); }
async function traces(plot) {
  return plot.evaluate(el => el._fullData.filter(t => t.visible === true)
    .map(t => ({ meta: t.meta, x: Array.from(t.x || []), y: Array.from(t.y || []), text: t.text, customdata:t.customdata, mode:t.mode })));
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
function numeric(rows, key, state) {
  check(rows.every(t=>t.meta.scenario===state),'Wrong visible scenario');
  if(key==='shout_payoff') {
    check(rows.length===4,'Payoff trace count');
    for(const p of reference.payoff.filter(p=>'shout'+p.shouted===state))
      for(const role of ['european','locked','cash','reset_call']) point(trace(rows,role),p.terminal,p[role],role);
  } else if(key==='shout_decision') {
    const row=trace(rows,'nodes'); check(row.customdata.length===10,'10 actual nodes');
    for(const p of reference.small_tree.nodes) {
      const n=row.customdata.find(n=>n.step===p.step&&n.upcount===p.up_count); check(!!n,'Node '+p.id);
      for(const field of ['spot','value','step']) close(n[field],p[field],p.id+' '+field);
      close(n.upcount,p.up_count,'upcount');close(n.remaining_time,p.remaining,'remaining');
      if(p.action==='expiry') {
        check(n.action==='maturity','Terminal action');
        for(const field of ['immediate','continuation','discounted_cash','reset_atm']) check(n[field]===null,'Terminal null '+field);
      } else {
        check(n.action===p.action,'Node decision');
        for(const [field,pin] of [['discounted_cash','cash'],['reset_atm','reset_european'],['immediate','shout'],['continuation','continuation']])
          close(n[field],p[pin],p.id+' '+field);
      }
    }
  } else if(key==='shout_comparison') {
    check(rows.length===(state==='zero-carry'?2:3),'Comparison trace count');
    for(const p of reference.comparison.filter(p=>p.market===state)) {
      point(trace(rows,'european'),p.spot,p.european,'European');
      const shout=trace(rows,'shout'),i=shout.x.indexOf(p.spot);
      check(i>=0 && Math.abs(shout.y[i]-p.shout_reference)<=.005,'Shout tolerance .005');
      close(shout.customdata[i][1],p.shout_reference,'Independent reference in hover');
      close(shout.customdata[i][0],shout.y[i]-p.shout_reference,'Residual in hover');
      if(p.lookback!==null) point(trace(rows,'lookback'),p.spot,p.lookback,'Lookback');
      else check(!rows.some(t=>t.meta.role==='lookback'),'Missing is not zero');
    }
  } else {
    check(rows.length===5,'Boundary trace count');
    const pin=reference.boundaries.find(p=>p.market===state), b=trace(rows,'reference');
    const lo=trace(rows,'lower'),hi=trace(rows,'upper'),br=trace(rows,'bracket');
    check(lo.mode==='markers' && hi.mode==='markers','Do not interpolate node bounds');
    check(b.x.length===59 && br.x.length===177,'Sparse actual layers');
    const sigma={'positive-carry':.2,'zero-carry':.3,'long-high-vol':.7}[state];
    b.x.forEach((tau,i)=>{
      close(b.y[i],interpolate({x:pin.remaining_times,y:pin.levels},tau),'Independent B boundary');
      const layer=1024*(1-tau/pin.expiry);close(layer,Math.round(layer),'Actual CRR layer');
      for(const t of [lo,hi]) {
        close(t.x[i],tau,'Actual bound time');
        const j=(Math.log(t.y[i]/100)/(sigma*Math.sqrt(pin.expiry/1024))+layer)/2;
        close(j,Math.round(j),'Actual CRR node');
      }
      close(br.x[3*i],tau,'Bracket start time');close(br.x[3*i+1],tau,'Bracket end time');
      close(br.y[3*i],lo.y[i],'Bracket lower');close(br.y[3*i+1],hi.y[i],'Bracket upper');
      check(br.x[3*i+2]===null && br.y[3*i+2]===null,'Disconnected brackets');
    });
    const residual=trace(rows,'residual');check(JSON.stringify(residual.x)==='[128,256,512,1024]','Convergence steps');
    // Only N1024 residual is independently checked in the browser; other steps are layout-only.
    const p=reference.comparison.find(p=>p.market===state&&p.spot===100);
    check(Math.abs(residual.y[3])<=.005,'ATM final residual tolerance');
    close(residual.y[3],lessonPrices[state]-p.shout_reference,'Same-market ATM residual');
  }
}
const lessonPrices={};
async function nodeLabels(plot) {
  const labels=await plot.locator('.textpoint text').allTextContents();
  check(labels.length===10,'Rendered node label count');
  reference.small_tree.nodes.forEach((p,i)=>{
    const expected=p.action==='expiry'?[`S=${p.spot.toFixed(2)}`,`満期給付=${p.value.toFixed(3)}`]:
      [`S=${p.spot.toFixed(2)}`,p.action==='continue'?'継続':'宣言',`継続=${p.continuation.toFixed(3)}`,`宣言=${p.shout.toFixed(3)}`,`V=${p.value.toFixed(3)}`,`現金${p.cash>=0?'+':''}${p.cash.toFixed(3)}`,`call ${p.reset_european.toFixed(3)}`];
    expected.forEach(v=>check(labels[i].includes(v),'Rendered node '+p.id+' '+v));
  });
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
async function select(page,plot,state) {
  const label=await plot.evaluate((el,state)=>el.layout.updatemenus[0].buttons.find(b=>b.args[1].meta.scenario===state).label,state);
  await plot.locator('.updatemenu-header').click();
  await plot.locator('.updatemenu-dropdown-button').filter({hasText:label}).click();
  await page.waitForFunction(({id,state})=>document.getElementById(id).layout.meta.scenario===state,{id:await plot.getAttribute('id'),state},{timeout});
  await settle(page);
}
async function negativeControl(plot) {
  const saved=await plot.evaluate(async el=>{
    const index=el._fullData.findIndex(t=>t.meta?.role==='nodes');
    const data=JSON.parse(JSON.stringify(el._fullData[index].customdata)),bad=JSON.parse(JSON.stringify(data));
    bad[1].discounted_cash+=1;bad[1].reset_atm-=1;
    await Plotly.restyle(el,{customdata:[bad]},[index]);return {index,data};
  });
  let rejected=false;
  try {
    const rows=await traces(plot),n=trace(rows,'nodes').customdata[1],p=reference.small_tree.nodes[1];
    close(n.discounted_cash+n.reset_atm,p.shout,'Negative control preserves sum');
    close(n.value,p.value,'Negative control preserves value');
    try {numeric(rows,'shout_decision','positive-carry');} catch(e) {check(e.message.includes('discounted_cash'),'Unrelated corruption rejection');rejected=true;}
    check(rejected,'Signed constituent corruption passed');
  } finally {await plot.evaluate(async(el,s)=>Plotly.restyle(el,{customdata:[s.data]},[s.index]),saved);}
  numeric(await traces(plot),'shout_decision','positive-carry');await nodeLabels(plot);
  return {rejected,restored:true,sum_unchanged:true,value_unchanged:true,mutation:'node 1:0 cash +1, reset ATM -1'};
}
async function layoutCheck(page,plot,label) {
  await center(page,plot);
  await plot.hover({position:{x:10,y:10}});await settle(page);
  await page.waitForFunction(el => Math.abs(el.clientWidth-el._fullLayout.width)<3,await plot.elementHandle(),{timeout});
  const errors = await plot.evaluate(el => {
    const errors = [], frame = el.getBoundingClientRect();
    if (el.scrollWidth > el.clientWidth+3) errors.push('plot overflow');
    for (const n of el.querySelectorAll('.annotation-text,.gtitle,.xtitle,.ytitle,.xtick text,.ytick text,.legend,.textpoint text,.textpoint tspan')) {
      const b=n.getBoundingClientRect();
      if (b.width && b.height && (b.left<frame.left-3 || b.right>frame.right+3 || b.top<frame.top-3 || b.bottom>frame.bottom+3)) errors.push('clipped '+n.textContent);
    }
    const overlap=(a,b) => a.width>0 && b.width>0 && a.left<b.right-2 && a.right>b.left+2 && a.top<b.bottom-2 && a.bottom>b.top+2;
    const legend=el.querySelector('.legend')?.getBoundingClientRect();
    const modebar=el.querySelector('.modebar');
    if(modebar && Number(getComputedStyle(modebar).opacity)>0) {
      const title=el.querySelector('.gtitle');
      if(title && overlap(modebar.getBoundingClientRect(),title.getBoundingClientRect())) errors.push('modebar/title');
    }
    if(legend) for(const n of el.querySelectorAll('.annotation-text')) if(overlap(n.getBoundingClientRect(),legend)) errors.push('legend/annotation');
    for(const a of el.querySelectorAll('.xtitle,.ytitle,.xtick text,.ytick text'))
      for(const b of el.querySelectorAll('.legendtext')) if(overlap(a.getBoundingClientRect(),b.getBoundingClientRect())) errors.push('axis/legend');
    const labels=Array.from(el.querySelectorAll(".textpoint text"));
    for(let i=0;i<labels.length;i++) for(let j=i+1;j<labels.length;j++) if(overlap(labels[i].getBoundingClientRect(),labels[j].getBoundingClientRect())) errors.push("node label collision "+i+"/"+j);
    return errors;
  });
  check(errors.length===0,label+': '+errors.join('; '));
}
async function verifySurface(page,label) {
  if(label==='portal') {
    const text=await page.locator('body').innerText();
    for(const phrase of ['一定係数 GBM','S/K/T/σ>0','現金配当','時変ボラティリティ','契約固有の離散シャウト日','T=0/σ=0','全領域の安定性は対象外','put は原典外','この図は call']) check(text.includes(phrase),'Portal domain '+phrase);
  }
  const plots={},states=[],screenshots=[];
  for(const key of keys) plots[key]=await plotFor(page,key);
  const scenarios={shout_payoff:['shout60','shout50'],shout_decision:['positive-carry'],shout_boundary:['positive-carry','zero-carry','long-high-vol'],shout_comparison:[...new Set(reference.comparison.map(p=>p.market))]};
  // Read displayed N1024 ATM values for same-market residual identity, not as independent truth.
  const allComparison=await plots.shout_comparison.evaluate(el=>el.data.filter(t=>t.meta.role==='shout').map(t=>[t.meta.scenario,t.y[t.x.indexOf(100)]]));
  for(const [state,value] of allComparison) lessonPrices[state]=value;
  for(const width of [1440,1000]) {
    await page.setViewportSize({width,height:1050});await settle(page);
    for(const key of keys) for(const state of scenarios[key]) {
      await center(page,plots[key]);
      if(key!=='shout_decision') await select(page,plots[key],state);
      await layoutCheck(page,plots[key],label+'/'+key+'/'+state+'/'+width);
      const observed=await traces(plots[key]);numeric(observed,key,state);
      if(key==='shout_boundary') {
        const notes=await plots[key].locator('.annotation-text').allTextContents();
        check(notes.join(' ').includes('0.12618')&&notes.join(' ').includes('保証'),'Boundary limitation note');
      }
      if(key==='shout_decision') await nodeLabels(plots[key]);
      states.push({figure:key,scenario:state,width,numeric_checked:true,observed_values:observed});
    }
    check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+3),'Page overflow');
    for(const key of keys) {
      if(key!=='shout_decision') await select(page,plots[key],scenarios[key][0]);
      await layoutCheck(page,plots[key],label+'/'+key+'/'+width);
      const file=relativeOut+label+'-'+key+'-'+width+'.png';
      await plots[key].screenshot({path:path.join(root,file)});screenshots.push(file);
    }
  }
  const negative_controls=[await negativeControl(plots.shout_decision)];
  return {figures:keys,states,negative_controls,screenshots,layout_errors:0,numeric_scope:'Both widths: payoff 10 independent pins x4 legs, N3 all10 nodes and6 signed decompositions plus rendered labels,21 comparison call prices and independent B at all59 displayed times. CRR nodes checked for lattice membership, not independently solved optimal decisions. Convergence N1024 residual checked; earlier N residual values not independently re-solved in browser.'};
}
async function bookMath(page) {
  const heading=page.locator('h3').filter({hasText:/4\.2 シャウト/});check(await heading.count()===1,'Missing shout h3');
  const section=heading.locator('xpath=..');
  await page.waitForFunction(()=>!!window.MathJax?.startup?.promise,null,{timeout});await page.evaluate(()=>window.MathJax.startup.promise);
  const math=await section.evaluate(el=>({typeset:el.querySelectorAll('mjx-container').length,errors:el.querySelectorAll('mjx-merror,.MathJax_Error').length,headings:Array.from(el.querySelectorAll('h4')).map(n=>n.textContent),text:el.textContent,rows:Array.from(el.querySelectorAll('tr')).map(n=>n.textContent.replace(/\s/g,''))}));
  check(math.typeset>=15&&math.errors===0,'Shout math typesetting');
  for(let i=1;i<=6;i++)check(math.headings.some(h=>h.includes('4.2.'+i)),'Shout S0'+i);
  check(!math.text.includes('4.3 アジアン')&&!math.text.includes('4.1.1'),'Own section boundaries');
  for(const phrase of ['K=50、シャウト時60','11.681238968672309','36行・6市場','14行のみ','欠測であり0ではありません','0.12618','誤差上界'])check(math.text.includes(phrase),'Teaching text '+phrase);
  check(math.rows.includes('シャウト後の給付101025'),'Original example values');
  delete math.text;delete math.rows;math.screenshots=[];
  for(const width of [1440,1000]) {
    await page.setViewportSize({width,height:1050});await settle(page);
    check(await section.evaluate(el=>Array.from(el.querySelectorAll('div.math')).every(n=>n.scrollWidth<=n.clientWidth+3)),'Shout math overflow');
    const example=section.locator('h4').filter({hasText:/4\.2\.1/}).locator('xpath=..');
    const contentHeading=example.locator('h4'),table=example.locator('table');
    const contentHeight=await example.evaluate(el=>el.querySelector('table').getBoundingClientRect().bottom-el.querySelector('h4').getBoundingClientRect().top);
    await page.setViewportSize({width,height:Math.max(1050,Math.ceil(contentHeight)+260)});await settle(page);
    await contentHeading.evaluate(el=>{document.activeElement?.blur();window.scrollTo({top:scrollY+el.getBoundingClientRect().top-130,behavior:'instant'});});
    await settle(page);
    const clip=await example.evaluate(el=>{
      const a=el.querySelector('h4').getBoundingClientRect(),b=el.querySelector('table').getBoundingClientRect(),frame=el.getBoundingClientRect();
      return {x:frame.left,y:a.top,width:frame.width,height:b.bottom-a.top+12};
    });
    check((await table.boundingBox()).y+(await table.boundingBox()).height<page.viewportSize().height,'Example fully in viewport');
    const file=relativeOut+'book-shout-example-'+width+'.png';
    await page.screenshot({path:path.join(root,file),clip});math.screenshots.push(file);
  }
  return math;
}
(async()=>{
  for(const [file,digest] of Object.entries(reference.source_sha256)) check(hash(file)===digest,'Stale independent pin source '+file);
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
    for(const file of ['hullkit/src/hullkit/_shout_lesson.py','hullkit/src/hullkit/_shout.py','scripts/build_shout_browser_reference.py','scripts/build_shout_lesson_data.py',relativeOut+'lesson-data.json','hullkit/src/hullkit/exotics.py','hullkit/tests/test_lookback_reference.py',
      'volumes/10_exotics_martingales/build_exotics_notebook.py','volumes/10_exotics_martingales/exotics.ipynb',
      'report/report_builder/figures.py','report/report_builder/render.py','report/assets/style.css','book/_ext/book_runtime.py','book/_config.yml',
      'scripts/verify_shout_lesson_browser.cjs',relativeOut+'browser-reference.json']) result.source_sha256[file]=hash(file);
    const artifacts=['report/site/exotics.html','report/site/assets/style.css','report/site/assets/plotly.min.js','book/_build/html/notebooks/10_exotics.html'];
    for(const p of Object.values(result.pages)) artifacts.push(...p.screenshots,...(p.math?.screenshots||[]));
    for(const file of artifacts) result.artifact_sha256[file]=hash(file);
    result.status='PASS'; console.log(JSON.stringify({status:'PASS',surfaces:2,screenshots:18,output:out},null,2));
  } finally {await browser.close();}
})().catch(error=>{result.status='FAIL';result.error=error.message;console.error(error.stack);process.exitCode=1;})
  .finally(()=>fs.writeFileSync(path.join(out,'browser-m4b-check.json'),JSON.stringify(result,null,2)+'\n'));
