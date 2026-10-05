// One configured Book/portal sweep for a chapter; independent reference trace values.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = path.resolve(__dirname, '..');
const configPath = process.env.JOHNHULL_CHAPTER_CONFIG || process.argv[2];
if (!configPath) throw new Error('provide chapter config relative to project root');
const config = JSON.parse(fs.readFileSync(path.join(root, configPath), 'utf8'));
const sections = config.sections.filter(s => !process.env.JOHNHULL_SECTION_ID || s.id === process.env.JOHNHULL_SECTION_ID);
if (!sections.length) throw new Error('no configured section selected');
const referencePath = config.output_dir + '/reference.json';
const reference = JSON.parse(fs.readFileSync(path.join(root, referencePath), 'utf8'));
const numerical = JSON.parse(fs.readFileSync(path.join(root, config.output_dir, 'numerical-check.json'), 'utf8'));
const keys = sections.flatMap(s => s.figures), sectionFor = key => sections.find(s => s.figures.includes(key)).id;
const out = path.join(root, config.output_dir); fs.mkdirSync(out, { recursive: true });
const sha = name => crypto.createHash('sha256').update(fs.readFileSync(path.join(root, name))).digest('hex');
const record = { status: 'FAIL', chapter: config.chapter, pages: {}, source_sha256: {}, artifact_sha256: {} };
const check = (test, message) => { if (!test) throw new Error(message); };
function closeArray(actual, expected, label) {
  check(Array.isArray(actual) && actual.length === expected.length, label + ': shape');
  actual.forEach((a,i) => check(Number.isFinite(a) && Math.abs(a-expected[i]) <= 1e-9+1e-10*Math.abs(expected[i]), label + '['+i+']'));
}
async function numeric(plot, key) {
  const actual = await plot.evaluate(el => ({meta: el.layout.meta, traces: el._fullData.filter(t => t.visible === true).map(t => ({role:t.meta?.role,x:Array.from(t.x),y:Array.from(t.y)}))}));
  check(actual.meta?.figure === key && actual.meta.section === sectionFor(key) && actual.meta.synthetic === true, key + ': metadata');
  const expected = reference.figures[key];
  check(expected && actual.traces.length === expected.length, key + ': trace count');
  for (const row of expected) {
    const matches = actual.traces.filter(t => t.role === row.role);
    check(matches.length === 1, key + ': role ' + row.role);
    for (const axis of ['x','y']) closeArray(matches[0][axis], row[axis], key+'/'+row.role+'.'+axis);
  }
}
async function settle(page) {
  await page.evaluate(async () => { await document.fonts.ready; await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))); });
}
async function layout(page, plot, key) {
  await plot.scrollIntoViewIfNeeded(); await settle(page);
  await page.waitForFunction(el => Math.abs(el.clientWidth-el._fullLayout.width)<3, await plot.elementHandle());
  const issue = await plot.evaluate(el => {
    const frame=el.getBoundingClientRect();
    if (el.clientWidth<650 || el.scrollWidth>el.clientWidth+3) return 'plot width/overflow';
    for (const node of el.querySelectorAll('.gtitle,.xtitle,.ytitle,.legend,.annotation-text,.g-xtitle,.g-ytitle')) {
      const b=node.getBoundingClientRect();
      if (b.width && b.height && (b.left<frame.left-3 || b.right>frame.right+3 || b.top<frame.top-3 || b.bottom>frame.bottom+3)) return 'clipped '+node.classList;
    }
    return null;
  });
  check(!issue, key+': '+issue);
  check(await page.evaluate(() => document.documentElement.scrollWidth<=innerWidth+3), key+': page overflow');
}
(async () => {
  check(numerical.status === 'PASS' && numerical.chapter === config.chapter, 'numerical acceptance missing');
  const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_BIN,args:['--no-sandbox']});
  record.browser_version=browser.version();
  try {
    const context=await browser.newContext({viewport:{width:1440,height:1050}});
    for (const surface of ['book','portal']) {
      const page=await context.newPage(), errors=[], requests=[], unapproved=[];
      page.on('pageerror', e => errors.push(e.message));
      await page.route(/^https?:/, route => {
        const url=route.request().url();requests.push(url);
        if(surface==='book' && url.startsWith('https://cdn.jsdelivr.net/npm/mathjax@3/es5/')) return route.continue();
        unapproved.push(url);return route.abort();
      });
      await page.goto('file://'+path.join(root,surface==='book'?config.book_page:config.portal_page));
      const headings=[];
      if(surface==='book') {
        await page.waitForFunction(() => !!window.MathJax?.startup?.promise);
        await page.evaluate(() => window.MathJax.startup.promise);
        const math=await page.evaluate(() => ({rendered:document.querySelectorAll('mjx-container').length,errors:document.querySelectorAll('mjx-merror,.MathJax_Error').length}));
        check(math.rendered>20 && math.errors===0,'Book MathJax');record.book_math=math;
        for(const section of sections) {
          const heading=page.locator('h2').filter({hasText:section.heading});check(await heading.count()===1,section.id+': unique heading');
          const parent=heading.locator('..');
          check(await parent.locator('h3').count()>=3,section.id+': explanatory subsections missing');
          check((await parent.innerText()).includes('印刷'),section.id+': synthetic/printed distinction missing');
          check(await parent.locator('mjx-container').count()>0,section.id+': equations absent');
          const invalid=await parent.locator('a[href^="#"]').evaluateAll(nodes => nodes.filter(a => !document.getElementById(decodeURIComponent(a.hash.slice(1)))).map(a=>a.hash));
          check(!invalid.length,section.id+': broken local links');
          headings.push({section:section.id,heading:section.heading,explanation_checked:true,math_checked:true});
        }
      }
      const plots={};
      for(const key of keys) {
        await page.waitForFunction(k => [...document.querySelectorAll('.plotly-graph-div')].filter(el=>el.layout?.meta?.figure===k && el._fullLayout).length===1,key);
        const id=await page.evaluate(k => [...document.querySelectorAll('.plotly-graph-div')].find(el=>el.layout?.meta?.figure===k).id,key);
        plots[key]=page.locator('[id="'+id+'"]');
      }
      const states=[],captures=[];
      for(const [width,height] of config.viewports) {
        await page.setViewportSize({width,height});await settle(page);
        for(const key of keys) {
          await numeric(plots[key],key);await layout(page,plots[key],key);
          const file=config.output_dir+'/'+surface+'-'+key+'-'+width+'.png';
          await plots[key].screenshot({path:path.join(root,file)});
          captures.push(file);states.push({section:sectionFor(key),figure:key,width,numeric_checked:true,layout_checked:true});
        }
      }
      const first=keys[0];
      const saved=await plots[first].evaluate(async el => {const y=Array.from(el.data[0].y),bad=y.slice();bad[0]+=.01;await Plotly.restyle(el,{y:[bad]},[0]);return y;});
      let rejected=false;try {await numeric(plots[first],first);}catch(e) {rejected=e.message.includes('.y[');}
      finally {await plots[first].evaluate((el,y)=>Plotly.restyle(el,{y:[y]},[0]),saved);}
      check(rejected,surface+': numeric mutation accepted');await numeric(plots[first],first);
      check(!errors.length && !unapproved.length,surface+': browser errors/network');
      record.pages[surface]={states,screenshots:captures,headings,numeric_mutation_rejected:rejected,page_errors:errors,external_requests:requests,unapproved_requests:unapproved,external_network_blocked:surface==='portal'};
      await page.close();
    }
    for(const name of [configPath,referencePath,config.output_dir+'/numerical-check.json','scripts/verify_chapter_browser.cjs',config.lesson,config.notebook,config.notebook_builder,'report/report_builder/figures.py'])record.source_sha256[name]=sha(name);
    for(const name of [config.book_page,config.portal_page])record.artifact_sha256[name]=sha(name);
    record.state_checks=Object.values(record.pages).reduce((n,p)=>n+p.states.length,0);
    record.screenshots=Object.values(record.pages).reduce((n,p)=>n+p.screenshots.length,0);
    record.capture_sha256=Object.fromEntries(Object.values(record.pages).flatMap(p=>p.screenshots).map(name=>[name,sha(name)]));
    record.status='PASS';console.log(JSON.stringify({status:'PASS',sections:sections.map(s=>s.id),state_checks:record.state_checks,screenshots:record.screenshots}));
  }finally {await browser.close();}
})().catch(e=>{record.error=e.message;console.error(e.stack);process.exitCode=1;}).finally(()=>fs.writeFileSync(path.join(out,'browser-check.json'),JSON.stringify(record,null,2)+'\n'));