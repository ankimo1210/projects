// Local file rendering over inherited pipes. No HTTP, WebSocket or TCP endpoint.
import {spawn} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import crypto from 'node:crypto';
const root=path.resolve(process.argv[2]);
const report=path.resolve(process.argv[3]);
const label=process.argv[4]||'main';
const qa=path.join(root,'audit','logs','html_qa',label);
fs.mkdirSync(qa,{recursive:true});
const profile=fs.mkdtempSync(path.join(root,'audit','tmp','chrome-pipe-'));
const log=fs.openSync(path.join(qa,'browser.log'),'w');
const browser=spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',[
 '--headless=new','--no-first-run','--no-default-browser-check','--disable-background-networking',
 '--disable-component-update','--disable-sync','--disable-crash-reporter','--no-pings','--metrics-recording-only',
 '--disable-features=OptimizationHints,MediaRouter','--host-resolver-rules=MAP * ~NOTFOUND',
 '--remote-debugging-pipe',`--user-data-dir=${profile}`,`--disk-cache-dir=${profile}/cache`,'about:blank'
],{stdio:['ignore',log,log,'pipe','pipe'],env:process.env});
let id=0,buffer='',session;
const pending=new Map(),exceptions=[];
browser.stdio[4].on('data',chunk=>{
 buffer+=chunk.toString();let index;
 while((index=buffer.indexOf('\0'))>=0){
  const raw=buffer.slice(0,index);buffer=buffer.slice(index+1);if(!raw)continue;
  const m=JSON.parse(raw);if(m.method==='Runtime.exceptionThrown')exceptions.push(m.params);
  if(pending.has(m.id)){const {resolve,reject,timer}=pending.get(m.id);pending.delete(m.id);clearTimeout(timer);m.error?reject(Error(JSON.stringify(m.error))):resolve(m.result);}
 }
});
function call(method,params={},sessionId){return new Promise((resolve,reject)=>{
 const requestId=++id,timer=setTimeout(()=>{pending.delete(requestId);reject(Error(`timeout: ${method}`));},15000);
 pending.set(requestId,{resolve,reject,timer});browser.stdio[3].write(JSON.stringify({id:requestId,method,params,...(sessionId?{sessionId}:{})})+'\0');
});}
const page=(method,params={})=>call(method,params,session);
const evaluate=async expression=>(await page('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true})).result.value;
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
try{
 const target=await call('Target.createTarget',{url:'about:blank'});
 session=(await call('Target.attachToTarget',{targetId:target.targetId,flatten:true})).sessionId;
 await page('Page.enable');await page('Runtime.enable');
 await page('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
 await page('Page.navigate',{url:pathToFileURL(report).href});
 for(let i=0;i<100;i++){if(await evaluate("document.readyState==='complete' && document.querySelectorAll('h2').length>=9"))break;await wait(100);}
 await evaluate('Promise.all([document.fonts.ready,...Array.from(document.images).map(i=>i.decode())]).then(()=>true)');
 const state=await evaluate(`({title:document.title,sections:Array.from(document.querySelectorAll('h2')).map(e=>({text:e.textContent,y:e.getBoundingClientRect().top+scrollY})),images:Array.from(document.images).map(e=>({complete:e.complete,width:e.naturalWidth,height:e.naturalHeight})),scrollWidth:document.documentElement.scrollWidth,clientWidth:document.documentElement.clientWidth})`);
 const screenshot=async name=>{const r=await page('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});fs.writeFileSync(path.join(qa,name),Buffer.from(r.data,'base64'));};
 await screenshot('top.png');
 for(let i=0;i<state.sections.length;i++){await evaluate(`scrollTo(0,${Math.max(0,state.sections[i].y-25)})`);await screenshot(`section-${i+1}.png`);}
 await page('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
 await evaluate('scrollTo(0,0)');await screenshot('mobile-top.png');
 const mobile=await evaluate('({scrollWidth:document.documentElement.scrollWidth,clientWidth:document.documentElement.clientWidth})');
 const result={...state,mobile,exceptions,node_version:process.version,browser_version:await call('Browser.getVersion'),
 html_sha256:crypto.createHash('sha256').update(fs.readFileSync(report)).digest('hex'),transport:'inherited OS pipes; no network connection',
 no_missing_images:state.images.every(i=>i.complete&&i.width>0),desktop_no_overflow:state.scrollWidth<=state.clientWidth,mobile_no_overflow:mobile.scrollWidth<=mobile.clientWidth};
 fs.writeFileSync(path.join(qa,'inspection.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
 if(state.sections.length<9||!result.no_missing_images||!result.desktop_no_overflow||!result.mobile_no_overflow||exceptions.length)throw Error('HTML QA failed');
 await call('Browser.close').catch(()=>{});
}finally{browser.kill('SIGTERM');fs.closeSync(log);}
