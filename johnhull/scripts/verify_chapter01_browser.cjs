// Ch1 D3: every section on both surfaces and widths, including conceptual lessons.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve(__dirname,'..');
const cfg=JSON.parse(fs.readFileSync(path.join(root,'docs/acceptance/chapters/ch01.json'),'utf8'));
const ref=JSON.parse(fs.readFileSync(path.join(root,'docs/validation/chapter-01/reference.json'),'utf8'));
const out=path.join(root,'docs/validation/chapter-01');
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex');
const check=(v,msg)=>{if(!v)throw Error(msg)};
const record={status:'FAIL',chapter:1,source_sha256:{},artifact_sha256:{},sections:{},captures:[]};
async function settle(page){await page.evaluate(async()=>{await document.fonts.ready;await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))})}
async function numeric(el,key){
 const data=await el.evaluate(e=>e.data.map(t=>({role:t.meta.role,x:Array.from(t.x),y:Array.from(t.y)})));
 const rows=ref.figures[key];check(data.length===rows.length,key+': trace count');
 for(let j=0;j<rows.length;j++){
  const a=data[j],b=rows[j];check(a.role===b.role,key+': role');
  for(const axis of ['x','y']){check(a[axis].length===b[axis].length,key+': shape');for(let i=0;i<b[axis].length;i++)check(Number.isFinite(a[axis][i])&&Math.abs(a[axis][i]-b[axis][i])<1e-7,key+': '+axis+' value')}
 }
}
async function linked(page,locator,title){
 const url=await locator.getAttribute('href');check(url,title+': href missing');
 const target=await locator.evaluate(a=>a.href);check(target.startsWith('file:'),title+': local target');
 const p=decodeURIComponent(new URL(target).pathname);check(fs.existsSync(p),title+': target absent '+p);
 await locator.click();await page.waitForLoadState('load');
 check((await page.title()).length>0,title+': navigation failed');
 return target;
}
(async()=>{
 fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_BIN,args:['--no-sandbox']});
 record.browser_version=browser.version();
 try{
  for(const surface of ['book','portal']){
   const page=await browser.newPage({viewport:{width:1440,height:1050}});
   const errors=[],external=[];
   page.on('pageerror',e=>errors.push(e.message));
   await page.route(/^https?:/,route=>{
    const url=route.request().url();
    if((surface==='book'||page.url().includes('/book/_build/'))&&url.startsWith('https://cdn.jsdelivr.net/npm/mathjax@3/es5/'))return route.continue();
    external.push(url);return route.abort();
   });
   const source=surface==='book'?cfg.book_page:cfg.portal_page;
   await page.goto('file://'+path.join(root,source));
   if(surface==='book'){
    await page.waitForFunction(()=>window.MathJax?.startup?.promise);
    await page.evaluate(()=>window.MathJax.startup.promise);
    check(await page.locator('mjx-merror,.MathJax_Error').count()===0,'Book math errors');
   }
   const plots={};
   for(const key of Object.keys(ref.figures)){
    await page.waitForFunction(k=>[...document.querySelectorAll('.plotly-graph-div')].filter(e=>e.layout?.meta?.figure===k).length===1,key);
    const id=await page.evaluate(k=>[...document.querySelectorAll('.plotly-graph-div')].find(e=>e.layout?.meta?.figure===k).id,key);
    plots[key]=page.locator('[id="'+id+'"]');
   }
   for(const [width,height] of cfg.viewports){
    await page.setViewportSize({width,height});await settle(page);
    for(const spec of cfg.sections){
     const heading=page.locator('h3').filter({hasText:spec.heading});check(await heading.count()===1,spec.id+': unique heading');
     const section=heading.locator('..');
     await heading.scrollIntoViewIfNeeded();await settle(page);
     const text=await section.innerText();
     check(text.includes('出典: Hull 11e')&&text.includes('確認:'),spec.id+': source/explanation missing');
     // Semantic markers are independent reading requirements, not an exact prose hash.
     const markers={'1.1':['2契約','証拠金','執行','清算'],'1.2':['558.5','11.6','compression','Lehman'],'1.3':['1.2230','単利','63','途中時点'],'1.4':['日次決済','需給'],'1.5':['数量×','100株','European','2,030'],'1.6':['流動性','hedge fund','convertible','merger'],'1.7':['26,500','購入時からの利益','36,660,000'],'1.8':['20契約','20,000','75 USD','損失上限'],'1.9':['USD収支','GBP収支','300','400'],'1.10':['Kerviel','日次監視','想定不足']};
     for(const word of markers[spec.id])check(text.includes(word),spec.id+': missing meaning '+word);
     if(ref.values[spec.id]){
      const rows=await section.locator('table tr').evaluateAll(rs=>rs.map(r=>[...r.querySelectorAll('td')].map(c=>c.textContent.trim())).filter(r=>r.length===2));
      check(rows.length===Object.keys(ref.values[spec.id]).length,spec.id+': printed table count');
      const seen=new Set();
      for(const [label,value]of rows){
       const key=ref.labels[label];check(key&&Object.hasOwn(ref.values[spec.id],key)&&!seen.has(key),spec.id+': unknown or duplicated value label');seen.add(key);
       check(Math.abs(Number(value.replaceAll(',',''))-ref.values[spec.id][key])<1e-7,spec.id+': displayed cash value '+label);
      }
     }
     const checkedFigures=[];
     for(const [key,plot]of Object.entries(plots)){
      const belongs=await plot.evaluate((e,sid)=>e.layout.meta.section===sid,spec.id);if(!belongs)continue;
      await numeric(plot,key);checkedFigures.push(key);await plot.scrollIntoViewIfNeeded();await settle(page);try {await page.waitForFunction(el=>Math.abs(el.clientWidth-el._fullLayout.width)<3,await plot.elementHandle(),{timeout:5000});}catch(e){throw Error(surface+'/'+key+'/'+width+': resize '+JSON.stringify(await plot.evaluate(el=>({client:el.clientWidth,layout:el._fullLayout.width,scroll:el.scrollWidth}))))}
      const clip=await plot.evaluate(e=>{
       const frame=e.getBoundingClientRect();if(e.clientWidth<450||e.scrollWidth>e.clientWidth+3)return 'width';
       for(const n of e.querySelectorAll('.gtitle,.xtitle,.ytitle,.legend')){const b=n.getBoundingClientRect();if(b.width&&(b.left<frame.left-3||b.right>frame.right+3||b.top<frame.top-3||b.bottom>frame.bottom+3))return n.classList.toString()}return null;
      });check(!clip,key+': clipped '+clip);
     }
     check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+3),surface+'/'+spec.id+': page overflow');
     const filename='docs/validation/chapter-01/'+surface+'-section-'+spec.id.replace('.','-')+'-'+width+'.png';
     await heading.scrollIntoViewIfNeeded();await settle(page);
     // Capture a complete section without fullPage's temporary viewport reflow.
     // Width stays identical to the checked viewport; only capture height expands.
     const sectionHeight=await section.evaluate(e=>Math.ceil(e.getBoundingClientRect().height));
     await page.setViewportSize({width,height:Math.max(height,sectionHeight+100)});await settle(page);
     await section.evaluate(e=>window.scrollTo({top:e.getBoundingClientRect().top+scrollY-24,behavior:'instant'}));await settle(page);
     const box=await section.boundingBox();
     check(box.y>=0&&box.y+box.height<=Math.max(height,sectionHeight+100),surface+'/'+spec.id+': capture bounds '+JSON.stringify({box,sectionHeight,height,viewport:page.viewportSize()}));
     await page.screenshot({path:path.join(root,filename),clip:{x:0,y:box.y,width,height:box.height},style:'header,aside,.bd-header,.bd-header-article,.skip-link,.bd-sidebar,.bd-sidebar-primary,.bd-sidebar-secondary,.pst-back-to-top {visibility:hidden !important}'});
     record.captures.push({path:filename,section:spec.id,surface,width,checked_height:height,capture_height:Math.max(height,sectionHeight+100),sha256:sha(filename)});
     await page.setViewportSize({width,height});await settle(page);
     (record.sections[spec.id]??=[]).push({surface,width,explanation_checked:true,printed_values_checked:!!ref.values[spec.id],printed_value_count:Object.keys(ref.values[spec.id]||{}).length,figure_values_checked:checkedFigures.length>0,checked_figures:checkedFigures,layout_checked:true});
    }
   }
   const first=plots.intro_forward;
   // Exercise legend control, then restore before a deliberately incorrect displayed value.
   await first.locator('.legendtoggle').first().click();
   await page.waitForFunction(e=>e.data[0].visible==='legendonly',await first.elementHandle());
   await first.locator('.legendtoggle').first().click();
   await page.waitForFunction(e=>e._fullData[0].visible===true,await first.elementHandle());
   const saved=await first.evaluate(async e=>{const y=Array.from(e.data[0].y),bad=y.slice();bad[0]+=1;await Plotly.restyle(e,{y:[bad]},[0]);return y});
   let rejected=false;try{await numeric(first,'intro_forward')}catch{rejected=true}
   await first.evaluate((e,y)=>Plotly.restyle(e,{y:[y]},[0]),saved);
   check(rejected,surface+': mutated cash accepted');await numeric(first,'intro_forward');
   const link=surface==='book'?page.getByRole('link',{name:'Book表示からCh1のオフライン教材と共有図を開く'}):page.getByRole('link',{name:'Jupyter Book',exact:true});
   record[surface+'_link']=await linked(page,link,surface+' companion link');
   check(!errors.length&&!external.length,surface+': script/network errors '+errors.join(',')+external.join(','));
   record[surface+'_mutation_rejected']=rejected;
   await page.close();
  }
  for(const p of ['docs/acceptance/chapters/ch01.json','hullkit/src/hullkit/_chapter01_lesson.py','hullkit/src/hullkit/_intro_contracts.py','volumes/12_qualitative_summary/build_summary_notebook.py','volumes/12_qualitative_summary/qualitative_summary.ipynb','scripts/build_chapter01_portal.py','scripts/verify_chapter01_browser.cjs','docs/validation/chapter-01/reference.json'])record.source_sha256[p]=sha(p);
  for(const p of [cfg.book_page,cfg.portal_page])record.artifact_sha256[p]=sha(p);
  record.state_checks=Object.values(record.sections).flat().length;
  record.status='PASS';console.log(JSON.stringify({status:'PASS',sections:10,state_checks:record.state_checks,captures:record.captures.length}));
 }finally{await browser.close()}
})().catch(e=>{record.error=e.message;console.error(e.stack);process.exitCode=1}).finally(()=>fs.writeFileSync(path.join(out,'browser-check.json'),JSON.stringify(record,null,2)+'\n'));
