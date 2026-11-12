(function () {
  'use strict';
  const math = globalThis.MathCalculus;
  if (!math) return;
  let serial = 0;
  const fmt = n => Math.abs(n) > 10000 ? n.toExponential(3) : n.toFixed(4);
  const line = (a,b,c,d,color,dash='') => `<line x1="${a}" y1="${b}" x2="${c}" y2="${d}" style="stroke:var(${color});stroke-width:2;${dash ? 'stroke-dasharray:'+dash : ''}"/>`;
  const label = (x,y,t,anchor='middle') => `<text x="${x}" y="${y}" text-anchor="${anchor}" style="fill:var(--ink-2);font-size:var(--lab-label-size,22px)">${t}</text>`;
  const path = (points,color) => `<polyline points="${points.map(p=>p.join(',')).join(' ')}" style="fill:none;stroke:var(${color});stroke-width:3"/>`;
  const dot = (x,y) => `<circle cx="${x}" cy="${y}" r="5" style="fill:var(--series-1)"/>`;
  function shell(host, title, description, controls, render) {
    const id = 'calculus-lab-' + (++serial);
    host.innerHTML = '<div class="lab-controls">' + controls.map(c=>`<label class="lab-control" for="${id}-${c.key}"><span class="lab-control-label">${c.label}</span><input type="range" id="${id}-${c.key}" data-key="${c.key}" min="${c.min}" max="${c.max}" step="${c.step}" value="${c.value}"></label>`).join('') + '</div><div class="lab-actions"><button type="button">初期状態に戻す</button></div><p class="lab-note">' + description + '</p><div data-figure></div><div class="lab-readout" aria-live="polite" aria-atomic="true"></div>';
    function update() {
      const values = Object.fromEntries([...host.querySelectorAll('input')].map(e=>[e.dataset.key,Number(e.value)]));
      const state = render(values,id);
      host.querySelector('[data-figure]').innerHTML = `<svg class="lab-svg" viewBox="0 0 480 ${state.height||320}" role="img" aria-labelledby="${id}-title ${id}-description"><title id="${id}-title">${title}</title><desc id="${id}-description">${state.alt}</desc>${state.svg}</svg>`;
      host.querySelector('.lab-readout').innerHTML = state.text;
    }
    host.querySelectorAll('input').forEach(e=>e.addEventListener('input',update));
    host.querySelector('button').addEventListener('click',()=>{
      controls.forEach(c=>{ host.querySelector(`[data-key="${c.key}"]`).value=c.value; }); update();
    });
    update();
  }
  function derivatives(host) {
    shell(host,'放物線の割線と接線','f(x)=x²、基準点a=1。hを0へ近づけ、割線の傾きと極限の接線を比べます。',[
      {key:'h',label:'基準点からのずれ h',min:-1,max:1,step:0.05,value:0.5}
    ],({h},id)=>{
      const s=math.secantSquare(1,h), x=t=>60+(t+0.3)*125, y=t=>250-t*35;
      const points=Array.from({length:101},(_,i)=>{const t=-0.3+i*0.028;return[x(t),y(t*t)];});
      const clipped=path(points,'--series-1')+line(x(-.3),y(-1.6),x(2.5),y(4),'--ink-2','5 4')
        +(h===0?'':line(x(-.3),y(1+s.quotient*(-1.3)),x(2.5),y(1+s.quotient*1.5),'--series-2'));
      let svg=`<defs><clipPath id="${id}-plot"><rect x="60" y="25" width="375" height="235"/></clipPath></defs>`
        +line(60,y(0),435,y(0),'--grid')+line(x(0),25,x(0),250,'--grid')
        +`<g clip-path="url(#${id}-plot)">${clipped}</g>`
        +line(x(s.x),y(s.y),x(s.x),y(1+2*h),'--series-2','3 3')
        +dot(x(1),y(1))+dot(x(s.x),y(s.y))
        +label(427,283,'x')+label(x(1),283,'a=1')+label(240,315,'実線 x² ／ 青 割線 ／ 破線 接線');
      const qx=t=>85+140*(t+1),qy=q=>465-45*(q-1),ry=q=>620-80*q;
      svg+=label(240,355,'二点の商 q(h)=2+h（h≠0）')
        +line(75,qy(2),415,qy(2),'--ink-2','5 5')+line(qx(0),375,qx(0),465,'--grid')
        +line(qx(-1),qy(1),qx(1),qy(3),'--series-2')
        +`<circle cx="${qx(0)}" cy="${qy(2)}" r="7" style="fill:var(--surface);stroke:var(--series-2);stroke-width:2"/>`
        +(h===0?'':dot(qx(h),qy(s.quotient)))
        +label(45,qy(2)+7,'2')+label(420,486,'h')+label(qx(-1),490,'−1')+label(qx(0),490,'0')+label(qx(1),490,'1');
      svg+=label(240,530,'接線からの縦の差 R(h)=h²')
        +line(75,ry(0),415,ry(0),'--grid')+line(qx(0),545,qx(0),ry(0),'--grid')
        +path(Array.from({length:81},(_,i)=>{const t=-1+i/40;return[qx(t),ry(t*t)];}),'--series-1')
        +dot(qx(h),ry(s.error))+label(45,ry(0)+7,'0')+label(420,647,'h')
        +label(240,680,h===0?'h=0：商とR(h)/hは未定義':'h≠0：R(h)/h=h → 0（h→0）');
      return {svg,height:705,alt:`h=${h}。上は割線と接線、中は二点の商2+hとh=0の穴、下は接線との差h²。hが0でなければR(h)/h=hが0に近づくことが接線近似の条件。差Rが0へ近づくだけでは接線を選べない。h=0では商もR(h)/hも未定義で、微分係数2を破線で区別する。有限の図は極限の証明ではない。`,
        text:`<p>h = ${fmt(h)}、次の点 (${fmt(s.x)}, ${fmt(s.y)})</p><p>割線の傾き：${s.quotient===null?'h=0では定義されません（0で割れない）':fmt(s.quotient)}<br>極限としての微分係数：${fmt(s.derivative)}</p><p>接線近似との差 h² = ${fmt(s.error)}。図の観察の理由は、本文で式から導きます。</p>`};
    });
  }
  function integration(host) {
    shell(host,'長方形の和で放物線の面積を挟む','f(x)=x²、区間[0,1]。橙は左端、青は右端の値で作る長方形です。',[
      {key:'n',label:'区間を分ける数 n',min:1,max:64,step:1,value:4}
    ],({n},id)=>{
      const s=math.squareRiemann(n), x=t=>60+360*t, y=t=>265-220*t;
      let svg=`<defs><pattern id="${id}-gap" patternUnits="userSpaceOnUse" width="7" height="7"><path d="M0 7 L7 0" style="stroke:var(--ink-2);stroke-width:1;fill:none"/></pattern></defs>`
        +line(60,265,430,265,'--grid')+line(60,20,60,265,'--grid');
      for(let k=0;k<n;k+=1){
        const l=k/n,r=(k+1)/n;
        svg+=`<rect x="${x(l)}" y="${y(r*r)}" width="${360/n}" height="${220*r*r}" style="fill:var(--series-2);fill-opacity:.18;stroke:var(--series-2);stroke-width:1"/>`;
        svg+=`<rect x="${x(l)}" y="${y(l*l)}" width="${360/n}" height="${220*l*l}" style="fill:var(--series-1);fill-opacity:.3;stroke:var(--series-1);stroke-width:1"/>`;
        svg+=`<rect x="${x(l)}" y="${y(r*r)}" width="${360/n}" height="${220*(r*r-l*l)}" fill="url(#${id}-gap)"/>`;
      }
      svg+=path(Array.from({length:101},(_,i)=>[x(i/100),y((i/100)**2)]),'--ink-2')+label(60,293,'0')+label(420,293,'1')
        +label(240,326,'斜線の総面積 = 上和−下和 = 1/n');
      const v=a=>70+340*a;
      svg+=label(240,365,'積分値Iを含む区間 [L,U]')
        +line(70,414,410,414,'--grid')+line(v(s.left),414,v(s.right),414,'--ink-2')
        +dot(v(s.left),414)+`<rect x="${v(s.right)-5}" y="409" width="10" height="10" style="fill:var(--series-2)"/>`
        +line(v(1/3),402,v(1/3),426,'--ink-2')
        +label(240,462,`L=${fmt(s.left)} ≤ I=1/3 ≤ U=${fmt(s.right)}`)
        +label(240,500,`区間幅 U−L=${fmt(1/n)}`);
      return {svg,height:525,alt:`${n}分割のx²。斜線は上和と下和の差、総面積1/n。下の数直線では左端の丸Lと右端の四角Uが積分値I=1/3の縦印を挟む。一般の関数の上下和は本文の条件で定義する。`,text:`<p>分割数 n = ${n}<br>左端の和 = ${fmt(s.left)}<br>右端の和 = ${fmt(s.right)}</p><p>本文で導く積分値 1/3 ≈ ${fmt(s.integral)}<br>上下の差 = 1/n = ${fmt(s.right-s.left)}</p><p>これは単調増加するx²での比較です。一般の関数では、各区間での最大の下界・最小の上界（連続なら最小値・最大値）を使って挟みます。</p>`};
    });
  }
  function series(host) {
    shell(host,'幾何級数の部分和と収束条件','有限個を足した部分和はいつも計算できます。無限に足した和の存在は、別に確かめます。',[
      {key:'r',label:'公比 r',min:-1.2,max:1.2,step:0.1,value:0.5},
      {key:'n',label:'足す項の数 N',min:1,max:30,step:1,value:6}
    ],({r,n},id)=>{
      const s=math.geometricPartial(r,n), values=[0,...s.partials,...(s.converges?[s.limit]:[])];
      const low=Math.min(...values),high=Math.max(...values), span=Math.max(1,high-low);
      const x=k=>n===1?240:75+300*(k-1)/(n-1),y=t=>260-215*(t-low)/span;
      let svg=`<defs><clipPath id="${id}-plot"><rect x="60" y="25" width="370" height="245"/></clipPath></defs>`
        +line(60,y(0),430,y(0),'--grid')+line(60,25,60,270,'--grid');
      if(s.converges)svg+=line(60,y(s.limit),430,y(s.limit),'--series-2','5 4');
      svg+=`<g clip-path="url(#${id}-plot)">${path(s.partials.map((value,k)=>[x(k+1),y(value)]),'--series-1')}</g>`;
      svg+=dot(x(n),y(s.sum))+label(n===1?240:75,295,n===1?'N=1':'1')+(n===1?'':label(375,295,'N'));
      if(s.converges)svg+=line(410,y(s.sum),410,y(s.limit),'--ink-2')+line(402,y(s.sum),418,y(s.sum),'--ink-2')+line(402,y(s.limit),418,y(s.limit),'--ink-2');
      svg+=label(240,335,'実線 部分和 ／ 破線 極限（|r|<1）')
        +label(240,380,`縦軸の下端 ${fmt(low)} ／ 上端 ${fmt(low+span)}`)
        +label(240,425,s.converges?`現在の残り |極限−G_N|=${fmt(s.errorBound)}`:'|r|≥1：有限和の先に極限はない')
        +label(240,475,'軸は自動調整。高さの印象より数値を比較');
      return {svg,height:505,alt:`公比${r}、${n}項。実線の部分和、収束時のみ破線の極限と現在和からの縦の差を示す。縦軸は自動調整し端の値を明示する。有限の部分和の表示だけで収束は証明しない。`,text:`<p>r = ${fmt(r)}、N = ${n}<br>G_N = 1 + r + … + r^(N−1) = ${fmt(s.sum)}</p>`+(s.converges?`<p>|r| &lt; 1 なので収束します。<br>極限 1/(1−r) = ${fmt(s.limit)}<br>極限との差の絶対値 = ${fmt(s.errorBound)}</p>`:'<p><strong>|r| ≥ 1 なので収束しません。</strong><br>有限の部分和の値を、無限級数の和と呼ぶことはできません。</p>')};
    });
  }
  function initialize(){
    const labs={derivatives,integration,series};
    document.querySelectorAll('[data-lab]').forEach(host=>{
      if(!host.dataset.labInitialized&&labs[host.dataset.lab]){ labs[host.dataset.lab](host);host.dataset.labInitialized='true'; }
    });
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initialize,{once:true});else initialize();
}());
