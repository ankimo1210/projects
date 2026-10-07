// fast-v1: all requirements at one viewport, one representative per chapter screenshots.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve(__dirname,'..');
const cfg=JSON.parse(fs.readFileSync(path.join(root,process.argv[2]||'docs/acceptance/fast-ch10-15.json'),'utf8'));
const out=cfg.out;
const sha=n=>crypto.createHash('sha256').update(fs.readFileSync(path.join(root,n))).digest('hex');
const check=(v,m)=>{if(!v)throw Error(m)};
const record={status:'FAIL',profile:'fast-v1',sections:{},captures:[],source_sha256:{},artifact_sha256:{}};
const flat=s=>s.replaceAll(/\s+/g,' ').trim();
async function semantics(loc,identifier){
 const expected=cfg.expected_dom[identifier];check(expected,'expected DOM absent '+identifier);
 const actual=await loc.evaluate(el=>{
  const clone=el.cloneNode(true);
  clone.querySelectorAll('[data-source-tex]').forEach(e=>e.textContent='\\('+e.getAttribute('data-source-tex')+'\\)');
  return {text:clone.textContent,math:[...el.querySelectorAll('[data-source-tex]')].map(e=>e.getAttribute('data-source-tex')),rendered:el.querySelectorAll('[data-source-tex] mjx-container').length,tables:el.querySelectorAll('table').length};
 });
 const digest=crypto.createHash('sha256').update(flat(actual.text)).digest('hex');
 check(digest===expected.text_sha256,identifier+': prose/math content changed');
 check(JSON.stringify(actual.math)===JSON.stringify(expected.math)&&actual.rendered===expected.math.length,identifier+': formula missing');
 check(actual.tables===expected.tables,identifier+': table missing');
 return {text_sha256:digest,math:actual.math.length,tables:actual.tables};
}
async function requirement(page,q){
 const loc=page.locator('[id="'+q.id+'"]');
 check(await loc.count()===1,'missing/duplicate requirement '+q.id);
 check(await loc.isVisible(),'invisible requirement '+q.id);
 check((await loc.innerText()).trim().length>=10,'empty requirement '+q.id);
 await semantics(loc,q.id);
}
async function settle(page){await page.evaluate(async()=>{await document.fonts.ready;await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))})}
(async()=>{
 fs.mkdirSync(path.join(root,out),{recursive:true});
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_BIN,args:['--no-sandbox']});
 record.browser_version=browser.version();
 try{
  for(const c of [...new Set(cfg.sections.map(r=>r.chapter))]){
   const page=await browser.newPage({viewport:{width:1280,height:1000}}),errors=[];
   page.on('pageerror',e=>errors.push(e.message));
   const rows=cfg.sections.filter(r=>r.chapter===c);
   await page.goto('file://'+path.join(root,rows[0].page));
   await page.waitForFunction(()=>window.MathJax?.startup?.promise);
   await page.evaluate(()=>window.MathJax.startup.promise);await settle(page);
   check(await page.locator('mjx-merror,.MathJax_Error').count()===0,'math errors Ch'+c);
   const rawMath=await page.locator('.lesson').evaluateAll(els=>els.flatMap(el=>{
    const clone=el.cloneNode(true);clone.querySelectorAll('mjx-container,pre,code').forEach(e=>e.remove());
    const text=clone.textContent;return /\\(?:frac|sigma|rho|sum|prod|left|right|hat|Delta|beta)\b/.test(text)?[el.id]:[];
   }));check(rawMath.length===0,'unrendered TeX '+rawMath.join(','));
   // Check every local navigation target and click the chapter's section anchors.
   const links=await page.locator('a').evaluateAll(as=>as.map(a=>({href:a.href,raw:a.getAttribute('href')})));
   for(const a of links){
    if(a.href.startsWith('file:')){
     const u=new URL(a.href);check(fs.existsSync(decodeURIComponent(u.pathname)),'broken local link '+a.raw);
     if(u.hash&&decodeURIComponent(u.pathname)===path.join(root,rows[0].page))check(await page.locator('[id="'+u.hash.slice(1)+'"]').count()===1,'missing anchor '+a.raw);
    }else check(/^https?:/.test(a.href),'unexpected link '+a.raw);
   }
   for(const row of rows){
    const loc=page.locator('[id="section-'+row.id.replace('.','-')+'"]');
    check(await loc.count()===1,row.id+': section missing');
    await page.locator('nav a[href="#section-'+row.id.replace('.','-')+'"]').click();await settle(page);
    check(await loc.locator('h2').count()===1,row.id+': missing heading');
    const text=await loc.innerText();check(text.includes('出典: Hull 11e')&&text.includes('確認:'),row.id+': explanation/source missing');
    for(const q of row.requirements)await requirement(page,q);
    check(await loc.locator('mjx-merror').count()===0,row.id+': formula failed');
    check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+3),row.id+': overflow');
    const visible=await semantics(loc,'section-'+row.id.replace('.','-'));
    visible.paragraphs=await loc.locator('p').count();
    check(visible.paragraphs>=3,row.id+': prose not rendered');
    record.sections[row.id]={requirements:row.requirements.map(q=>q.id),width:1280,explanation_checked:true,math_checked:true,layout_checked:true,links_checked:true,...visible};
    if(cfg.samples[c]===row.id){
     const filename=out+'/chapter-'+c+'-representative.png';
     const height=await loc.evaluate(el=>Math.ceil(el.getBoundingClientRect().height));
     await page.setViewportSize({width:1280,height:Math.max(1000,height+70)});await settle(page);
     await loc.evaluate(el=>window.scrollTo({top:el.getBoundingClientRect().top+scrollY-20,behavior:'instant'}));await settle(page);
     const box=await loc.boundingBox();check(box.y>=0&&box.y+box.height<=page.viewportSize().height,row.id+': capture clipped');
     await page.screenshot({path:path.join(root,filename),clip:{x:0,y:box.y,width:1280,height:box.height}});
     record.captures.push({section:row.id,path:filename,sha256:sha(filename),width:1280});
     await page.setViewportSize({width:1280,height:1000});
    }
   }
   const q=rows[0].requirements[0],el=page.locator('[id="'+q.id+'"]');
   await el.evaluate(e=>e.remove());let rejected=false;try{await requirement(page,q)}catch(e){rejected=true}
   check(rejected,'missing requirement accepted');record.missing_requirement_rejected=true;
   const replace=rows.flatMap(r=>r.requirements).find(q=>q.id!==rows[0].requirements[0].id);
   await page.locator('[id="'+replace.id+'"]').evaluate(e=>e.innerHTML='<p>原典の要点をあとで学習する予定です。</p>');
   let changed=false;try{await requirement(page,replace)}catch(e){changed=true}
   check(changed,'changed prose/math accepted');record.mutated_requirement_rejected=true;
   check(!errors.length,'runtime errors '+errors.join(','));
   record.artifact_sha256[rows[0].page]=sha(rows[0].page);
   record.source_sha256[rows[0].lesson]=sha(rows[0].lesson);
   await page.close();
  }
  for(const n of [process.argv[2]||'docs/acceptance/fast-ch10-15.json','scripts/verify_fast_acceptance_options_browser.cjs'])record.source_sha256[n]=sha(n);
  for(const c of record.captures)record.artifact_sha256[c.path]=c.sha256;
  record.status='PASS';console.log(JSON.stringify({status:'PASS',sections:Object.keys(record.sections).length,captures:record.captures.length}));
 }finally{await browser.close()}
})().catch(e=>{record.error=e.message;console.error(e.stack);process.exitCode=1}).finally(()=>fs.writeFileSync(path.join(root,out,'browser-check.json'),JSON.stringify(record,null,2)+'\n'));
