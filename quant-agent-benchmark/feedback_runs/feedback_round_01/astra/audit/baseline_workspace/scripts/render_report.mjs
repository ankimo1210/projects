// Optional local HTML QA: Node 22+ and an installed Chromium-family browser.
// Fresh browser profile, disabled background networking, all artifacts local.
import {spawn} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import crypto from 'node:crypto';

const root = process.cwd();
const qa = path.join(root, 'logs', 'html_qa');
fs.mkdirSync(qa, {recursive:true});
const profile = fs.mkdtempSync(path.join(root, 'tmp', 'chrome-qa-'));
const executable = process.env.CHROME_EXECUTABLE || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const report = path.join(root, 'reports', 'research_report.html');
const browserLog = fs.openSync(path.join(qa, 'browser.log'), 'w');
const browser = spawn(executable, [
  '--headless=new', '--no-first-run', '--no-default-browser-check',
  '--disable-background-networking', '--disable-component-update', '--disable-sync',
  '--disable-crash-reporter', '--no-pings', '--metrics-recording-only',
  '--disable-features=OptimizationHints,MediaRouter',
  '--host-resolver-rules=MAP * ~NOTFOUND',
  '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=0',
  `--user-data-dir=${profile}`, `--disk-cache-dir=${path.join(profile,'disk-cache')}`,
  pathToFileURL(report).href,
], {cwd:root, stdio:['ignore', browserLog, browserLog]});
const wait = ms => new Promise(resolve => setTimeout(resolve,ms));
let ws;
try {
  const portFile = path.join(profile, 'DevToolsActivePort');
  for(let i=0;i<150&&!fs.existsSync(portFile);i++)await wait(100);
  if(!fs.existsSync(portFile))throw new Error('isolated browser did not expose its local QA port');
  const port = fs.readFileSync(portFile,'utf8').split('\n')[0];
  const tabs = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  const target = tabs.find(t=>t.type==='page'&&t.url===pathToFileURL(report).href);
  if(!target)throw new Error('report page not found in isolated browser');
  ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{ws.addEventListener('open',resolve,{once:true});ws.addEventListener('error',reject,{once:true});});
  let id=0;
  const pending=new Map();
  const exceptions=[];
  ws.addEventListener('message',event=>{
    const message=JSON.parse(event.data);
    if(message.method==='Runtime.exceptionThrown')exceptions.push(message.params);
    if(pending.has(message.id)){
      const {resolve,reject,timer}=pending.get(message.id);pending.delete(message.id);clearTimeout(timer);
      message.error?reject(new Error(JSON.stringify(message.error))):resolve(message.result);
    }
  });
  const call=(method,params={})=>new Promise((resolve,reject)=>{
    const requestId=++id;
    const timer=setTimeout(()=>{pending.delete(requestId);reject(new Error(`QA timeout: ${method}`));},15000);
    pending.set(requestId,{resolve,reject,timer});ws.send(JSON.stringify({id:requestId,method,params}));
  });
  const evaluate=async expression=>(await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true})).result.value;
  await call('Page.enable');await call('Runtime.enable');
  await call('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
  await evaluate('Promise.all([document.fonts.ready,...Array.from(document.images).map(i=>i.decode())]).then(()=>true)');
  const state=await evaluate(`({title:document.title,sections:Array.from(document.querySelectorAll('h2')).map(e=>({text:e.textContent,y:e.getBoundingClientRect().top+scrollY})),images:Array.from(document.images).map(e=>({complete:e.complete,width:e.naturalWidth,height:e.naturalHeight})),scrollWidth:document.documentElement.scrollWidth,clientWidth:document.documentElement.clientWidth})`);
  const screenshot=async name=>{
    const r=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
    fs.writeFileSync(path.join(qa,name),Buffer.from(r.data,'base64'));
  };
  await screenshot('01-top.png');
  for(const [index,label] of [[3,'comparison'],[4,'sensitivity'],[5,'validation'],[7,'limitations']]){
    await evaluate(`scrollTo(0,${Math.max(0,state.sections[index].y-25)})`);
    await screenshot(`${index+2}-${label}.png`);
  }
  await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  await evaluate('scrollTo(0,0)');
  await screenshot('mobile-top.png');
  const mobile=await evaluate('({scrollWidth:document.documentElement.scrollWidth,clientWidth:document.documentElement.clientWidth})');
  const browserVersion=await call('Browser.getVersion');
  const result={...state,mobile,exceptions,browser_runtime:browserVersion,node_version:process.version,html_sha256:crypto.createHash('sha256').update(fs.readFileSync(report)).digest('hex'),
    no_missing_images:state.images.every(i=>i.complete&&i.width>0),
    desktop_no_horizontal_overflow:state.scrollWidth<=state.clientWidth,
    mobile_no_horizontal_overflow:mobile.scrollWidth<=mobile.clientWidth};
  fs.writeFileSync(path.join(qa,'inspection.json'),JSON.stringify(result,null,2)+'\n');
  console.log(JSON.stringify(result,null,2));
  if(!result.no_missing_images||!result.desktop_no_horizontal_overflow||!result.mobile_no_horizontal_overflow||exceptions.length)throw new Error('HTML rendering QA failed');
  await call('Browser.close').catch(()=>{});
} finally {
  if(ws)ws.close();
  browser.kill('SIGTERM');
  fs.closeSync(browserLog);
}
