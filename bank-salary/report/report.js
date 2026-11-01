(function () {
  'use strict';
  const COMPANIES = ['MS', 'GS', 'JPM', 'BOFA', 'CITI'];
  const COLORS = {MS:'var(--cat-1)',GS:'var(--cat-2)',JPM:'var(--cat-3)',BOFA:'var(--cat-4)',CITI:'var(--cat-5)'};
  const NAMES = {MS:'Morgan Stanley',GS:'Goldman Sachs',JPM:'JPMorgan Chase',BOFA:'Bank of America',CITI:'Citi'};
  const RANKS = ['Managing Director','Executive Director','SVP','Vice President','Director','AVP','Associate','Analyst','Senior / Lead','支店職','複数職位','職位語なし'];
  function classifyRank(title) {
    const t=title || '';
    const ed=/executive director|\bED\b/i.test(t), svp=/senior vice president|\bSVP\b/i.test(t), vp=/(?<!assistant |senior )vice president|\bVP\b/i.test(t);
    if((ed&&(vp||svp))||(svp&&vp)) return '複数職位';
    if(/managing director|\bMD\b/i.test(t)) return 'Managing Director';
    if(ed) return 'Executive Director';
    if(svp) return 'SVP';
    if(/assistant vice president|\bAVP\b/i.test(t)) return 'AVP';
    if(vp) return 'Vice President';
    if(/\bdirector\b/i.test(t)) return 'Director';
    if(/associate banker|relationship banker|private client banker|branch manager/i.test(t)) return '支店職';
    if(/\bassociate\b/i.test(t)) return 'Associate';
    if(/\banalyst\b/i.test(t)) return 'Analyst';
    if(/\b(?:senior|lead)\b/i.test(t)) return 'Senior / Lead';
    return '職位語なし';
  }
  function classifyFamily(title) {
    const t=title||'';
    if(/associate banker|relationship banker|private client banker|branch|home lending|mortgage/i.test(t)) return '支店・リテール';
    if(/risk|compliance|audit|financial crimes|control|regulatory|surveillance/i.test(t)) return 'リスク・コンプラ・監査';
    if(/engineer|developer|software|\bdata\b|\bAI\b|\bML\b|quant|\bstrats?\b|technology|infrastructure|cyber/i.test(t)) return '技術・データ・クオンツ';
    if(/investment bank|capital markets|\bM&A\b|trading|trader|derivatives|equities|\bFICC\b|fixed income|securitized/i.test(t)) return '投資銀行・マーケッツ';
    if(/asset|wealth|portfolio|private bank|investment|financial advis|client advis|private client|family office/i.test(t)) return '資産運用・WM';
    if(/operation|finance|financial|controller|treasury|tax|legal|attorney|human capital|recruit|account|business management|strategy|strategic|marketing|communications/i.test(t)) return '業務・財務・管理';
    return 'その他';
  }
  function isStudent(job) {
    return /\bintern(?:ship)?\b|\bsummer\b|off.cycle|\bcampus\b|\bgraduate\b|\bnew (?:analyst|associate)\b|202[6-9].*\bprogram\b|\bfull[- ]?time (?:analyst|associate)\b.*\b202[6-9]\b/i.test((job.title||'')+' '+(job.public_category||''));
  }
  function isNY(region) {
    return !region || /\bNY\b|New York|Brooklyn|Queens|Bronx|Staten Island/i.test(region);
  }
  function taxonomyValue(job,dimension) {
    return job.classification?.[dimension]?.label || '未分類';
  }
  function taxonomyOptions(jobs,s) {
    const pool=jobs.filter(j=>s.companies.includes(j.company));
    const unique=(items,dimension)=>[...new Set(items.map(j=>taxonomyValue(j,dimension)))].sort((a,b)=>a.localeCompare(b,'ja'));
    const departmentPool=pool.filter(j=>!s.businessDepartment||s.businessDepartment==='all'||taxonomyValue(j,'department')===s.businessDepartment);
    const subdepartmentPool=departmentPool.filter(j=>!s.businessSubdepartment||s.businessSubdepartment==='all'||taxonomyValue(j,'subdepartment')===s.businessSubdepartment);
    return {departments:unique(pool,'department'),subdepartments:unique(departmentPool,'subdepartment'),occupations:unique(subdepartmentPool,'occupation')};
  }
  function filteredJobs(jobs,s) {
    const q=(s.query||'').toLowerCase().trim();
    return jobs.filter(j => {
      if(!s.companies.includes(j.company))return false;
      if(s.rank!=='all' && classifyRank(j.title)!==s.rank)return false;
      if(s.family!=='all' && classifyFamily(j.title)!==s.family)return false;
      for(const [key,dimension] of [['businessDepartment','department'],['businessSubdepartment','subdepartment'],['occupation','occupation']]) {
        if(s[key] && s[key]!=='all' && taxonomyValue(j,dimension)!==s[key])return false;
      }
      if(s.program==='professional' && isStudent(j))return false;
      if(s.program==='student' && !isStudent(j))return false;
      if(s.status==='missing' && j.ranges.length)return false;
      if(s.status==='review' && !j.ranges.some(r=>r.parse_status==='review'))return false;
      if(s.status==='available' && !j.ranges.length)return false;
      return !q || [j.title,j.department,j.req,j.company,...j.locations,...['department','subdepartment','occupation'].map(d=>taxonomyValue(j,d))].join(' ').toLowerCase().includes(q);
    });
  }
  function selectRows(jobs,s) {
    const result=[];
    for(const job of filteredJobs(jobs,s)) {
      const seen=new Set();
      for(let index=0;index<job.ranges.length;index++) {
        const r=job.ranges[index];
        if(r.parse_status!=='parsed'||r.currency!=='USD'||!Number.isFinite(r.minimum)||!Number.isFinite(r.maximum)||r.minimum<=0||r.maximum<r.minimum)continue;
        if(!s.includeUnspecifiedPay && r.pay_type!=='base')continue;
        if(s.nyOnly && !isNY(r.region))continue;
        if(s.mode==='year' && r.period!=='year')continue;
        if(s.mode==='hour' && r.period!=='hour')continue;
        if(s.mode==='unknown' && r.period!=='unspecified')continue;
        if(s.mode==='small' && !(r.period==='unspecified'&&r.maximum<1000))continue;
        if(s.mode==='scenario' && !(r.period==='year'||(r.period==='unspecified'&&r.minimum>=s.threshold)))continue;
        const key=[r.minimum,r.maximum,r.currency,r.period,r.pay_type].join('|');
        if(seen.has(key))continue;
        seen.add(key);
        result.push({...r,job,index,assumed:s.mode==='scenario'&&r.period==='unspecified',midpoint:(r.minimum+r.maximum)/2,widthPct:(r.maximum-r.minimum)/((r.minimum+r.maximum)/2)*100});
      }
    }
    return result;
  }
  function quantile(values,p) {
    if(!values.length)return null;
    const a=[...values].sort((x,y)=>x-y),i=(a.length-1)*p,l=Math.floor(i),h=Math.ceil(i);
    return a[l]+(a[h]-a[l])*(i-l);
  }
  function quantiles(values) {
    return {min:quantile(values,0),q1:quantile(values,.25),median:quantile(values,.5),q3:quantile(values,.75),max:quantile(values,1)};
  }
  function summarize(rows) {
    return {...quantiles(rows.map(r=>r.midpoint)),jobs:new Set(rows.map(r=>r.job.id)).size,ranges:rows.length,
      assumed:rows.filter(r=>r.assumed).length,low:quantile(rows.map(r=>r.minimum),.5),high:quantile(rows.map(r=>r.maximum),.5),width:quantile(rows.map(r=>r.widthPct),.5)};
  }
  function toCSV(rows) {
    if(!rows.length)return '\uFEFF';
    const fields=Object.keys(rows[0]);
    const quote=x=>{let t=String(x??'');if(/^[\s]*[=+@-]/.test(t))t="'"+t;return '"'+t.replaceAll('"','""')+'"';};
    return '\uFEFF'+fields.map(quote).join(',')+'\r\n'+rows.map(r=>fields.map(f=>quote(r[f])).join(',')).join('\r\n');
  }
  function exportRows(rows,s) {
    return rows.map(r=>({company:r.job.company,requisition_id:r.job.req,title:r.job.title,
      public_department:r.job.department,business_department:taxonomyValue(r.job,'department'),business_subdepartment:taxonomyValue(r.job,'subdepartment'),occupation:taxonomyValue(r.job,'occupation'),
      ...Object.fromEntries(['department','subdepartment','occupation'].flatMap(d=>['basis','evidence'].map(k=>[d+'_'+k,r.job.classification?.[d]?.[k]||'']))),
      title_family:classifyFamily(r.job.title),title_rank:classifyRank(r.job.title),minimum:r.minimum,maximum:r.maximum,currency:r.currency,period_original:r.period,display_mode:s.mode,assumption:r.assumed?'annual_candidate':'none',scenario_threshold:s.mode==='scenario'?s.threshold:'',region:r.region,pay_type:r.pay_type,checked_at_utc:r.job.checked,url:r.job.url,evidence:r.evidence}));
  }
  const API={classifyRank,classifyFamily,isStudent,isNY,taxonomyValue,taxonomyOptions,filteredJobs,selectRows,quantile,quantiles,summarize,toCSV,exportRows};
  if(typeof module!=='undefined'&&module.exports)module.exports=API;
  globalThis.BankSalaryReport=API;
  if(typeof document==='undefined')return;

  const snapshot=JSON.parse(document.getElementById('snapshot').textContent);
  const jobs=snapshot.jobs;
  const $=id=>document.getElementById(id);
  const fmt=n=>n==null?'—':n.toLocaleString('en-US',{maximumFractionDigits:1});
  const money=n=>n==null?'—':'$'+n.toLocaleString('en-US',{maximumFractionDigits:n<1000?2:0});
  const compact=n=>n==null?'—':n>=1000?'$'+(n/1000).toLocaleString('en-US',{maximumFractionDigits:1})+'k':money(n);
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const period=p=>({year:'年額',hour:'時給',month:'月額',week:'週額',unspecified:'期間未記載'}[p]||p);
  const initial=()=>({companies:[...COMPANIES],mode:'scenario',threshold:20000,nyOnly:true,includeUnspecifiedPay:false,family:'all',rank:'all',businessDepartment:'all',businessSubdepartment:'all',occupation:'all',breakdown:'rank',program:'professional',query:'',status:'all',showAll:false,sort:'high',page:0});
  let state=initial(),currentRows=[],currentJobs=[];
  const tip=$('tip');
  function bind(node,text,click) {
    node.setAttribute('tabindex','0');node.setAttribute('aria-label',text);
    node.dataset.tooltip=text;
    const place=(x,y)=>{tip.textContent=text;tip.style.opacity='1';const w=tip.offsetWidth,h=tip.offsetHeight;tip.style.left=Math.max(8,Math.min(innerWidth-w-8,x+14))+'px';tip.style.top=Math.max(8,Math.min(innerHeight-h-8,y-h-12))+'px';};
    node.addEventListener('pointerenter',e=>place(e.clientX,e.clientY));
    node.addEventListener('pointermove',e=>place(e.clientX,e.clientY));
    node.addEventListener('pointerleave',()=>tip.style.opacity='0');
    node.addEventListener('focus',()=>{const r=node.getBoundingClientRect();place(r.left,r.top+20);});
    node.addEventListener('blur',()=>tip.style.opacity='0');
    if(click){node.style.cursor='pointer';node.addEventListener('click',click);node.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();click();}});}
  }
  function el(tag,attrs={},text) {
    const n=document.createElementNS('http://www.w3.org/2000/svg',tag);
    for(const [k,v] of Object.entries(attrs)) {
      if(['fill','stroke','font-family'].includes(k)&&String(v).includes('var('))n.style.setProperty(k,v);
      else n.setAttribute(k,v);
    }
    if(text!=null)n.textContent=text;
    return n;
  }
  function svg(id,height,minWidth=600) {
    const box=$(id),w=Math.max(minWidth,box.clientWidth||minWidth);
    box.replaceChildren();const s=el('svg',{viewBox:`0 0 ${w} ${height}`,width:w,height,role:'img','aria-label':box.dataset.label});
    s.style.maxWidth='none';box.append(s);return [s,w];
  }
  function empty(id,text='条件に一致する集計可能な給与レンジがありません。') {$(id).replaceChildren();const p=document.createElement('p');p.className='empty';p.textContent=text;$(id).append(p);}
  function legend(id,companies=COMPANIES) {$(id).innerHTML=companies.map(c=>`<span><i class="sq" style="background:${COLORS[c]}"></i>${esc(NAMES[c])}</span>`).join('');}
  function overview() {
    const all=jobs.flatMap(j=>j.ranges),unknown=all.filter(r=>r.period==='unspecified').length,reviewJobs=jobs.filter(j=>j.ranges.some(r=>r.parse_status==='review')).length;
    $('totalJobs').textContent=fmt(jobs.length);$('salaryJobs').textContent=fmt(jobs.filter(j=>j.ranges.length).length);
    $('unknownPct').textContent=(unknown/all.length*100).toFixed(1)+'%';$('unknownCount').textContent=`${fmt(unknown)} / ${fmt(all.length)} 給与行`;
    $('reviewJobs').textContent=fmt(reviewJobs);
    const [s,w]=svg('coverageChart',50+COMPANIES.length*64,400),left=76,right=100,max=Math.max(1,...COMPANIES.map(c=>jobs.filter(j=>j.company===c).length));
    COMPANIES.forEach((c,i)=>{
      const group=jobs.filter(j=>j.company===c),clean=group.filter(j=>j.ranges.length&&!j.ranges.some(r=>r.parse_status==='review')).length,review=group.filter(j=>j.ranges.some(r=>r.parse_status==='review')).length,missing=group.length-clean-review,y=35+i*64,scale=(w-left-right)/max;
      s.append(el('text',{x:12,y:y+21,'font-size':15,'font-weight':700},c));
      let x=left;
      for(const [n,color,label] of [[clean,COLORS[c],'給与取得'],[review,'var(--accent-soft)','原文要確認'],[missing,'var(--surface-2)','未記載・抽出不可']]) {
        if(!n)continue;const rect=el('rect',{x,y,width:Math.max(2,n*scale),height:30,rx:3,fill:color,stroke:'var(--rule)'});bind(rect,`${NAMES[c]} / ${label}: ${fmt(n)}求人（全${fmt(group.length)}求人）`);s.append(rect);x+=n*scale;
      }
      s.append(el('text',{x:w-right+14,y:y+21,'font-size':14},`${fmt(group.length)}求人`));
      $('coverage-'+c).textContent=group.length?`${fmt(group.length-missing)} / ${fmt(group.length)}（${((group.length-missing)/group.length*100).toFixed(1)}%）`:'この取得回は未収集';
    });
    const [u,uw]=svg('unitsChart',50+COMPANIES.length*64,400),ul=55,ur=120;
    COMPANIES.forEach((c,i)=>{
      const group=jobs.filter(j=>j.company===c).flatMap(j=>j.ranges);
      const counts=[group.filter(r=>r.period==='year').length,group.filter(r=>r.period==='hour').length,group.filter(r=>!['year','hour'].includes(r.period)).length];
      const colors=['var(--series-2)','var(--series-1)','var(--surface-2)'];let x=ul;const y=35+i*64,total=group.length;
      u.append(el('text',{x:12,y:y+21,'font-size':15,'font-weight':700},c));
      counts.forEach((n,k)=>{if(!n)return;const width=n/total*(uw-ul-ur),rect=el('rect',{x,y,width,height:30,fill:colors[k],stroke:'var(--rule)'});bind(rect,`${NAMES[c]} / ${['年額明記','時給明記','期間未記載等'][k]}: ${fmt(n)} / ${fmt(total)}行（${(n/total*100).toFixed(1)}%）`);u.append(rect);x+=width;});
      u.append(el('text',{x:uw-ur+10,y:y+20,'font-size':13},total?`未記載等 ${(counts[2]/total*100).toFixed(0)}%`:'未収集'));
    });
    $('scopeJobCount').textContent=fmt(jobs.length);
    $('classificationCoverage').textContent=`全${fmt(jobs.length)}求人の未分類：部門 ${fmt(jobs.filter(j=>taxonomyValue(j,'department')==='未分類').length)}件、サブ部門 ${fmt(jobs.filter(j=>taxonomyValue(j,'subdepartment')==='未分類').length)}件、職種 ${fmt(jobs.filter(j=>taxonomyValue(j,'occupation')==='未分類').length)}件。分類版 ${snapshot.meta.classification_version}。`;
  }
  function axis(s,w,height,max,left=130) {
    const right=34,top=24,bottom=46,plot=w-left-right;
    const steps=5;
    for(let i=0;i<=steps;i++) {const v=max*i/steps,x=left+plot*i/steps;s.append(el('line',{x1:x,y1:top,x2:x,y2:height-bottom,stroke:'var(--grid)','stroke-width':1}));s.append(el('text',{x,y:height-15,'font-size':13,'text-anchor':'middle'},compact(v)));}
    return n=>left+plot*n/max;
  }
  function boxplot(rows) {
    if(!rows.length)return empty('boxChart');
    const height=80+COMPANIES.length*74,[s,w]=svg('boxChart',height),max=Math.max(...rows.map(r=>r.midpoint))*1.08,x=axis(s,w,height,max);
    COMPANIES.forEach((c,i)=>{
      const values=rows.filter(r=>r.job.company===c),q=summarize(values),y=65+i*74;
      s.append(el('text',{x:12,y:y-2,'font-size':15,'font-weight':700},c));
      s.append(el('text',{x:12,y:y+17,'font-size':12},`${fmt(q.jobs)}求人 / ${fmt(q.ranges)}行`));
      if(!values.length){s.append(el('text',{x:140,y:y+6,'font-size':14},'該当なし'));return;}
      const text=`${NAMES[c]} / ${fmt(q.jobs)}求人・${fmt(q.ranges)}レンジ\n中点: 最小 ${money(q.min)} / 25% ${money(q.q1)} / 中央値 ${money(q.median)} / 75% ${money(q.q3)} / 最大 ${money(q.max)}\n期間を仮定した行: ${fmt(q.assumed)}`;
      s.append(el('line',{x1:x(q.min),x2:x(q.max),y1:y,y2:y,stroke:COLORS[c],'stroke-width':2}));
      [q.min,q.max].forEach(v=>s.append(el('line',{x1:x(v),x2:x(v),y1:y-7,y2:y+7,stroke:COLORS[c],'stroke-width':2})));
      if(values.length>=5) {const rect=el('rect',{x:x(q.q1),y:y-12,width:Math.max(2,x(q.q3)-x(q.q1)),height:24,fill:COLORS[c],opacity:.28,stroke:COLORS[c]});bind(rect,text);s.append(rect);}
      const mark=el('line',{x1:x(q.median),x2:x(q.median),y1:y-16,y2:y+16,stroke:COLORS[c],'stroke-width':3});bind(mark,text);s.append(mark);
      s.append(el('text',{x:Math.min(w-70,x(q.median)),y:y-23,'font-size':14,'font-weight':700,fill:'var(--ink)'},compact(q.median)));
      if(values.length<5)values.forEach(r=>{const d=el('circle',{cx:x(r.midpoint),cy:y,r:4,fill:COLORS[c]});bind(d,`${r.job.title}\n${money(r.minimum)}–${money(r.maximum)} / ${period(r.period)}`,()=>openJob(r.job.id));s.append(d);});
    });
  }
  function distribution(rows) {
    if(!rows.length)return empty('distributionChart');
    const [s,w]=svg('distributionChart',320),left=64,right=22,top=28,bottom=55,max=Math.max(...rows.map(r=>r.midpoint));
    const small=max<1000,step=small?Math.max(2,Math.ceil(max/15/2)*2):Math.max(10000,Math.ceil(max/18/10000)*10000),end=Math.ceil(max/step)*step,binCount=Math.max(1,Math.ceil(end/step));
    const bins=Object.fromEntries(COMPANIES.map(c=>[c,Array(binCount).fill(0)])),counts=Object.fromEntries(COMPANIES.map(c=>[c,rows.filter(r=>r.job.company===c).length]));
    rows.forEach(r=>bins[r.job.company][Math.min(binCount-1,Math.floor(r.midpoint/step))]++);
    const shares=COMPANIES.flatMap(c=>bins[c].map(n=>counts[c]?n/counts[c]*100:0)),maxY=Math.max(5,Math.ceil(Math.max(...shares)/5)*5),pw=w-left-right,ph=320-top-bottom;
    for(let i=0;i<=4;i++){const y=top+ph-ph*i/4;s.append(el('line',{x1:left,x2:w-right,y1:y,y2:y,stroke:'var(--grid)'}));s.append(el('text',{x:left-10,y:y+5,'text-anchor':'end','font-size':13},(maxY*i/4).toFixed(0)+'%'));}
    const bw=pw/binCount;
    for(let i=0;i<binCount;i++) {
      COMPANIES.forEach((c,ci)=>{const n=bins[c][i],pct=counts[c]?n/counts[c]*100:0;if(!n)return;const x=left+i*bw+ci*bw/COMPANIES.length,h=pct/maxY*ph,bar=el('rect',{x,y:top+ph-h,width:Math.max(1,bw/COMPANIES.length-1),height:h,fill:COLORS[c]});bind(bar,`${NAMES[c]}\n中点 ${money(i*step)}–${money((i+1)*step)}\n${n} / ${counts[c]}レンジ（${pct.toFixed(1)}%）`);s.append(bar);});
      if(i%Math.max(1,Math.ceil(binCount/6))===0)s.append(el('text',{x:left+i*bw,y:294,'font-size':13,'text-anchor':'middle'},compact(i*step)));
    }
    s.append(el('text',{x:w-right,y:314,'font-size':12,'text-anchor':'end'},`階級幅 ${money(step)} / 各社内の割合`));
  }
  function heatmap(rows) {
    const dimension=state.breakdown;
    const value=job=>dimension==='rank'?classifyRank(job.title):dimension==='subdepartment'?taxonomyValue(job,'department')+' / '+taxonomyValue(job,'subdepartment'):taxonomyValue(job,dimension);
    const labels=dimension==='rank'?RANKS:[...new Set(rows.map(r=>value(r.job)))].sort((a,b)=>a.localeCompare(b,'ja'));
    const axisLabel={rank:'タイトルの職位語',department:'部門',subdepartment:'部門 / サブ部門',occupation:'職種'}[dimension];
    $('breakdownHeading').textContent=axisLabel;
    const groups=labels.map(rank=>({rank,cells:COMPANIES.map(c=>summarize(rows.filter(r=>r.job.company===c&&value(r.job)===rank)))})).filter(g=>g.cells.some(c=>c.ranges));
    const values=groups.flatMap(g=>g.cells.filter(c=>c.ranges>=5).map(c=>c.median)),lo=Math.min(...values),hi=Math.max(...values);
    $('rankBody').innerHTML=groups.length?groups.map(g=>`<tr><th scope="row">${esc(g.rank)}</th>${g.cells.map((c,i)=>{const level=c.ranges<5?0:Math.min(4,1+Math.floor((c.median-lo)/Math.max(1,hi-lo)*3));return `<td><button class="heat-cell level-${level}" data-rank="${esc(g.rank)}" data-company="${COMPANIES[i]}" ${c.ranges?'':'disabled'}><strong>${compact(c.median)}</strong><small>${fmt(c.jobs)}求人 / ${fmt(c.ranges)}行${c.ranges>0&&c.ranges<5?' · 少数':''}</small></button></td>`;}).join('')}</tr>`).join(''):`<tr><td colspan="${COMPANIES.length+1}">集計可能なレンジがありません。</td></tr>`;
    $('rankBody').querySelectorAll('button:not([disabled])').forEach(b=>{bind(b,`${b.dataset.rank} / ${NAMES[b.dataset.company]}\nクリックするとこの会社・${axisLabel}で絞り込み`);b.addEventListener('click',()=>{
      if(dimension==='rank')state.rank=b.dataset.rank;
      else if(dimension==='department'){state.businessDepartment=b.dataset.rank;state.businessSubdepartment='all';state.occupation='all';}
      else if(dimension==='subdepartment'){[state.businessDepartment,state.businessSubdepartment]=b.dataset.rank.split(' / ');state.occupation='all';}
      else state.occupation=b.dataset.rank;
      state.companies=[b.dataset.company];state.page=0;syncControls();render();$('analysis').scrollIntoView({behavior:'smooth'});
    });});
  }
  function comparisons(rows) {
    $('comparisonBody').innerHTML=COMPANIES.map(c=>{const q=summarize(rows.filter(r=>r.job.company===c));return `<tr><th scope="row">${esc(NAMES[c])}</th><td class="num">${fmt(q.jobs)}</td><td class="num">${fmt(q.ranges)}</td><td class="num">${money(q.low)}</td><td class="num">${money(q.median)}</td><td class="num">${money(q.high)}</td><td class="num">${q.width==null?'—':q.width.toFixed(1)+'%'}</td><td class="num">${q.ranges?(q.assumed/q.ranges*100).toFixed(1)+'%':'—'}</td></tr>`;}).join('');
  }
  function tableRows() {
    let data=[...currentRows];
    if(state.showAll||['missing','review'].includes(state.status)) {
      const present=new Set(data.map(r=>r.job.id));
      data.push(...currentJobs.filter(j=>!present.has(j.id)).map(job=>({job,midpoint:null,minimum:null,maximum:null,period:null,assumed:false,placeholder:true})));
    }
    data.sort((a,b)=>{
      if(state.sort==='name')return a.job.company.localeCompare(b.job.company)||a.job.title.localeCompare(b.job.title);
      if(state.sort==='recent')return (b.job.posted||'').localeCompare(a.job.posted||'');
      if(a.midpoint==null)return b.midpoint==null?0:1;if(b.midpoint==null)return -1;
      return state.sort==='low'?a.midpoint-b.midpoint:b.midpoint-a.midpoint;
    });
    return data;
  }
  function renderTable() {
    const data=tableRows(),pageSize=25,pages=Math.max(1,Math.ceil(data.length/pageSize));state.page=Math.min(state.page,pages-1);
    $('tableCount').textContent=`${fmt(data.length)}行 · ${fmt(new Set(data.map(r=>r.job.id)).size)}求人`;
    $('pageLabel').textContent=`${state.page+1} / ${pages}`;$('prevPage').disabled=state.page===0;$('nextPage').disabled=state.page>=pages-1;
    $('jobsBody').innerHTML=data.length?data.slice(state.page*pageSize,(state.page+1)*pageSize).map(r=>`<tr><td><span class="company-label" data-company="${r.job.company}">${r.job.company}</span></td><td class="job-title"><button class="job-link" data-job="${esc(r.job.id)}">${esc(r.job.title)}</button><small>${esc(classifyRank(r.job.title))}${isStudent(r.job)?' · 学生向け候補':''}</small></td>${['department','subdepartment','occupation'].map(d=>`<td class="taxonomy-cell">${esc(taxonomyValue(r.job,d))}</td>`).join('')}<td class="salary-cell">${r.placeholder?'<span class="muted">表示モードの集計対象外</span>':`<strong>${money(r.minimum)}–${money(r.maximum)}</strong><small>${esc(r.region||'適用地域は未記載（NY求人）')}</small>`}</td><td>${r.placeholder?esc(r.job.status==='review'?'原文要確認':r.job.ranges.length?'条件外':'給与なし'):esc(r.assumed?'年額候補（仮定）':period(r.period))}</td><td><a href="${esc(r.job.url)}" target="_blank" rel="noopener noreferrer">公式求人 ↗</a></td></tr>`).join(''):'<tr><td colspan="8" class="empty">条件に一致する求人がありません。フィルターをリセットしてください。</td></tr>';
    $('jobsBody').querySelectorAll('[data-job]').forEach(b=>b.addEventListener('click',()=>openJob(b.dataset.job)));
  }
  function openJob(id) {
    const job=jobs.find(j=>j.id===id);if(!job)return;
    $('dialogTitle').textContent=job.title;$('dialogMeta').textContent=`${NAMES[job.company]} · ${job.req} · 確認 ${job.checked} UTC`;
    $('dialogLink').href=job.url;$('dialogLocations').textContent=job.locations.join(' / ');
    $('dialogClassification').innerHTML=`<p class="small muted">公開部門：${esc(job.department||'未記載')} · 公開職務カテゴリ：${esc(job.public_category||'未記載')}</p><dl class="classification-details">${[['department','部門'],['subdepartment','サブ部門'],['occupation','職種']].map(([dimension,name])=>{const c=job.classification?.[dimension]||{};return `<div><dt>${name}</dt><dd><strong>${esc(taxonomyValue(job,dimension))}</strong><small>${esc(c.basis||'情報不足')}</small>${c.evidence?`<blockquote>${esc(c.evidence)}</blockquote>`:''}</dd></div>`;}).join('')}</dl><p class="small muted">公開情報から作成した分析用分類です。会社の正式な組織名・所属を保証するものではありません。</p>`;
    $('dialogData').innerHTML=job.ranges.length?job.ranges.map(r=>`<article class="evidence-row"><div><strong>${money(r.minimum)}–${money(r.maximum)}</strong><span class="pill">${esc(period(r.period))}</span>${r.parse_status==='review'?'<span class="pill warning">原文要確認</span>':''}${r.pay_type!=='base'?'<span class="pill">給与種別未明記</span>':''}</div><p class="muted">${esc(r.region||'金額の適用地域は未記載')} · ${esc(r.currency)}</p><blockquote>${esc(r.evidence)}</blockquote></article>`).join(''):'<p>給与レンジは未記載、または保守的な抽出では取得できませんでした。</p>';
    $('jobDialog').showModal();
  }
  function modeLabel() {
    return {scenario:'年額候補を含む参考比較（USD・年額仮定）',year:'年額が明記された掲載レンジ（USD / 年）',hour:'時給が明記された掲載レンジ（USD / 時間）',unknown:'期間未記載の金額（USD・期間不明）',small:'期間未記載・上限$1,000未満（USD・期間不明）'}[state.mode];
  }
  function render() {
    syncTaxonomyControls();
    currentJobs=filteredJobs(jobs,state);currentRows=selectRows(jobs,state);const q=summarize(currentRows);
    $('viewLabel').textContent=modeLabel();$('selectedJobs').textContent=fmt(q.jobs);$('selectedRanges').textContent=fmt(q.ranges);
    for(const id of ['boxMode','distributionMode','rankMode'])$(id).textContent=modeLabel();
    $('assumedShare').textContent=q.ranges?(q.assumed/q.ranges*100).toFixed(1)+'%':'—';$('rangeWidth').textContent=q.width==null?'—':q.width.toFixed(1)+'%';
    $('assumedDetail').textContent=`${fmt(q.assumed)} / ${fmt(q.ranges)}行`;
    $('modeNote').textContent=state.mode==='scenario'?`年額未記載で下限${money(state.threshold)}以上の行を便宜的に年額候補へ含めています。${fmt(q.assumed)}行の期間は未確認です。「年額明記のみ」で仮定を外せます。`:state.mode==='unknown'||state.mode==='small'?'原文の金額を変換せず表示しています。年俸と時給の区別が付かないため、単位が明記された金額とは同じ集計に含めません。':'原文に単位が明記された行だけを表示しています。該当しない会社は「該当なし」になります。';
    $('thresholdWrap').hidden=state.mode!=='scenario';
    $('activeScope').textContent=`${state.companies.join(' / ')||'会社未選択'}${[state.businessDepartment,state.businessSubdepartment,state.occupation].filter(v=>v!=='all').map(v=>' · '+v).join('')} · ${state.nyOnly?'NYに適用可能な金額':'全勤務地の併記額も含む'} · ${state.program==='professional'?'学生向け候補を除外':state.program==='student'?'学生向け候補のみ':'全募集区分'} · 同一求人の同額重複は1行`;
    boxplot(currentRows);distribution(currentRows);heatmap(currentRows);comparisons(currentRows);renderTable();
    $('downloadCSV').disabled=!currentRows.length;
    window.reportReady=true;
  }
  function syncControls() {
    document.querySelectorAll('[data-company-filter]').forEach(c=>c.checked=state.companies.includes(c.dataset.companyFilter));
    for(const key of ['mode','threshold','rank','family','program','query','status','sort','breakdown'])$(key).value=state[key];
    for(const key of ['nyOnly','includeUnspecifiedPay','showAll'])$(key).checked=state[key];
    syncTaxonomyControls();
  }
  function syncTaxonomyControls() {
    for(const [key,optionKey,name] of [['businessDepartment','departments','部門'],['businessSubdepartment','subdepartments','サブ部門'],['occupation','occupations','職種']]) {
      const options=taxonomyOptions(jobs,state)[optionKey];
      if(state[key]!=='all'&&!options.includes(state[key]))state[key]='all';
      $(key).innerHTML=`<option value="all">すべての${name}</option>`+options.map(t=>`<option>${esc(t)}</option>`).join('');
      $(key).value=state[key];
    }
  }
  function download() {
    const rows=exportRows(currentRows,state);
    const blob=new Blob([toCSV(rows)],{type:'text/csv;charset=utf-8;'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`ny-bank-salary-${snapshot.meta.date}-${state.mode}.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  function init() {
    $('family').innerHTML='<option value="all">すべての大分類</option>'+[...new Set(jobs.map(j=>classifyFamily(j.title)))].sort().map(t=>`<option>${esc(t)}</option>`).join('');
    $('rank').innerHTML='<option value="all">すべての職位語</option>'+RANKS.map(t=>`<option>${esc(t)}</option>`).join('');
    syncControls();overview();legend('distributionLegend');legend('boxLegend');
    document.querySelectorAll('[data-company-filter]').forEach(c=>c.addEventListener('change',()=>{state.companies=COMPANIES.filter(k=>document.querySelector(`[data-company-filter="${k}"]`).checked);state.page=0;render();}));
    for(const key of ['mode','rank','family','program','status','sort','breakdown','businessDepartment','businessSubdepartment','occupation'])$(key).addEventListener('change',()=>{state[key]=$(key).value;
      if(key==='businessDepartment'){state.businessSubdepartment='all';state.occupation='all';}
      if(key==='businessSubdepartment')state.occupation='all';
      state.page=0;render();
    });
    $('threshold').addEventListener('change',()=>{state.threshold=Math.max(1000,Number($('threshold').value)||20000);$('threshold').value=state.threshold;state.page=0;render();});
    let typing;$('query').addEventListener('input',()=>{clearTimeout(typing);typing=setTimeout(()=>{state.query=$('query').value;state.page=0;render();},120);});
    for(const key of ['nyOnly','includeUnspecifiedPay','showAll'])$(key).addEventListener('change',()=>{state[key]=$(key).checked;state.page=0;render();});
    $('resetFilters').addEventListener('click',()=>{state=initial();syncControls();render();});
    $('prevPage').addEventListener('click',()=>{state.page--;renderTable();});$('nextPage').addEventListener('click',()=>{state.page++;renderTable();});
    $('downloadCSV').addEventListener('click',download);$('printReport').addEventListener('click',()=>window.print());
    $('closeDialog').addEventListener('click',()=>$('jobDialog').close());
    $('themeButton').addEventListener('click',()=>{const dark=document.documentElement.dataset.theme==='dark'||(!document.documentElement.dataset.theme&&matchMedia('(prefers-color-scheme: dark)').matches);document.documentElement.dataset.theme=dark?'light':'dark';$('themeButton').textContent=dark?'ダーク表示':'ライト表示';});
    $('sourceList').innerHTML=snapshot.meta.sources.map(s=>`<tr><th>${esc(s.label)}</th><td class="num">${fmt(s.expected)}</td><td class="num">${fmt(s.unique)}</td><td>${esc(s.note)}</td></tr>`).join('');
    render();let resizing;window.addEventListener('resize',()=>{clearTimeout(resizing);resizing=setTimeout(()=>{overview();render();},150);});
  }
  init();
})();
