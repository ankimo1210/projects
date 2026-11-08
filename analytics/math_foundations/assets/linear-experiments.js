(function(){
  'use strict';
  const math=globalThis.MathLinear;if(!math)return;
  let serial=0;
  const examples={identity:[1,0,0,1],shear:[1,.5,0,1],reflection:[-1,0,0,1],collapsed:[1,1,1,1]};
  const fmt=x=>(Math.abs(x)<.00005?0:x).toFixed(4);
  function initialize(host){
    const prefix='linear-lab-'+(++serial),names=['a','b','c','d'];
    host.innerHTML=`<div class="lab-controls"><label class="lab-control" for="${prefix}-example"><span class="lab-control-label">変換の例</span><select id="${prefix}-example"><option value="identity">単位行列</option><option value="shear" selected>せん断</option><option value="reflection">横反転</option><option value="collapsed">つぶす</option><option value="custom">自由に調整</option></select></label><div class="linear-controls">`+names.map((n,i)=>`<label class="lab-control" for="${prefix}-${n}"><span class="lab-control-label">行列の成分 ${n}</span><output data-value="${n}"></output><input type="range" id="${prefix}-${n}" data-key="${n}" min="-2" max="2" step=".25" value="${examples.shear[i]}"></label>`).join('')+`</div></div><div class="lab-actions"><button type="button">初期状態に戻す</button></div><p class="lab-note">A = ［a b; c d］。e₁、e₂ の像は列 u=(a,c)、v=(b,d)。点線は元の単位正方形、塗った図形は変換後です。</p><div data-figure></div><div class="lab-readout" aria-live="polite" aria-atomic="true"></div>`;
    const selection=host.querySelector('select');
    function set(values){names.forEach((n,i)=>{host.querySelector(`[data-key="${n}"]`).value=values[i];});}
    function update(){
      const q=Object.fromEntries(names.map(n=>[n,Number(host.querySelector(`[data-key="${n}"]`).value)]));
      const m=[[q.a,q.b],[q.c,q.d]],state=math.areaState(m);
      names.forEach(n=>{host.querySelector(`[data-value="${n}"]`).textContent=fmt(q[n]);});
      const extent=Math.max(1,Math.ceil(Math.max(...state.vertices.flatMap(v=>[Math.abs(v.x),Math.abs(v.y)]))));
      const unit=150/extent,px=x=>240+unit*x,py=y=>210-unit*y;
      let body='';
      for(let k=-extent;k<=extent;k++)body+=`<path d="M${px(k)} 60V360 M90 ${py(k)}H390" style="fill:none;stroke:var(--grid);stroke-width:${k===0?2:1}"/>`;
      body+='<polygon points="'+[{x:0,y:0},{x:1,y:0},{x:1,y:1},{x:0,y:1}].map(v=>`${px(v.x)},${py(v.y)}`).join(' ')+'" style="fill:none;stroke:var(--ink-2);stroke-width:2;stroke-dasharray:5 4"/>';
      body+='<polygon points="'+state.vertices.map(v=>`${px(v.x)},${py(v.y)}`).join(' ')+'" style="fill:var(--series-1);fill-opacity:.2;stroke:var(--series-1);stroke-width:2"/>';
      body+=`<line x1="240" y1="210" x2="${px(q.a)}" y2="${py(q.c)}" style="stroke:var(--series-1);stroke-width:7"/><line x1="240" y1="210" x2="${px(q.b)}" y2="${py(q.d)}" style="stroke:var(--series-2);stroke-width:4"/>`;
      if(state.signedArea!==0){
        const corners=state.vertices;
        corners.forEach((a,i)=>{
          const b=corners[(i+1)%corners.length],ax=px(a.x),ay=py(a.y),bx=px(b.x),by=py(b.y);
          const length=Math.hypot(bx-ax,by-ay),dx=(bx-ax)/length,dy=(by-ay)/length;
          const mx=(ax+bx)/2,my=(ay+by)/2;
          const tip=[mx+6*dx,my+6*dy],left=[mx-5*dx-4.5*dy,my-5*dy+4.5*dx],right=[mx-5*dx+4.5*dy,my-5*dy-4.5*dx];
          body+='<polygon data-boundary-arrow="'+i+'" points="'+[tip,left,right].map(p=>p.join(',')).join(' ')+'" fill="var(--ink-3)"/>';
        });
      }
      body+='<circle data-column-end="u" cx="'+px(q.a)+'" cy="'+py(q.c)+'" r="8" fill="none" stroke="var(--series-1)" stroke-width="3"/>';
      body+='<circle data-column-end="v" cx="'+px(q.b)+'" cy="'+py(q.d)+'" r="4.5" fill="var(--series-2)"/>';
      const label=(x,y,t)=>`<text x="${x}" y="${y}" text-anchor="middle" style="fill:var(--ink-2);font-size:var(--lab-label-size,20px)">${t}</text>`;
      body+=label(405,215,'x')+label(247,48,'y')+label(240,392,'橙の輪：u　青の点：v　点線：元の正方形');
      body+=label(240,22,'det '+fmt(state.signedArea)+' ／ 面積 '+fmt(state.area));
      body+=label(240,427,state.signedArea===0?'面積0：境界の回る向きは付けない':(state.signedArea>0?'反時計回り：':'時計回り：')+'0→u→u+v→v→0');
      body+=label(240,459,'格子1目盛=1（表示範囲は自動）');
      body+='<circle cx="240" cy="210" r="3" fill="var(--ink-2)"/>';
      const direction=state.orientation==='collapsed'?'面積は0。平行四辺形が線分または点につぶれ、逆変換はありません。':state.orientation==='reversed'?'向きが逆になります。面積は行列式の絶対値です。':'向きを保ちます。面積は行列式の絶対値です。';
      host.querySelector('[data-figure]').innerHTML=`<svg class="lab-svg" viewBox="0 0 480 480" role="img" aria-labelledby="${prefix}-title ${prefix}-desc"><title id="${prefix}-title">境界順序の向きと面積を、行列式の符号と絶対値へ対応づける</title><desc id="${prefix}-desc">行列式${state.signedArea}、面積${state.area}。${direction}各状態で格子一目盛は1、表示範囲は自動調整。点線の元の正方形と像は同じ縮尺だが、別の状態との画素面積の直接比較はしない。非零なら境界の矢印を0,u,u+v,v,0の順にたどって向きを比較する。零なら向きは付けず、入力が重なることを読む。uの端は橙の輪、vの端は青い点なので、同じ端点でも両方を区別できる。</desc>${body}</svg>`;
      host.querySelector('.lab-readout').innerHTML=`<p>A = ［${fmt(q.a)}　${fmt(q.b)}; ${fmt(q.c)}　${fmt(q.d)}］</p><p>det A = ad − bc = <strong>${fmt(state.signedArea)}</strong><br>変換後の面積 = |det A| = <strong>${fmt(state.area)}</strong></p><p>${direction}</p><p>u=(${fmt(q.a)},${fmt(q.c)})、v=(${fmt(q.b)},${fmt(q.d)})。一般の行列は長さや角度も変えます。面積だけが保存される例もあります。</p>`;
    }
    host.querySelectorAll('input').forEach(e=>e.addEventListener('input',()=>{selection.value='custom';update();}));
    selection.addEventListener('change',()=>{if(examples[selection.value])set(examples[selection.value]);update();});
    host.querySelector('button').addEventListener('click',()=>{selection.value='shear';set(examples.shear);update();});update();
  }
  function start(){document.querySelectorAll('[data-lab="determinants"]').forEach(h=>{if(!h.dataset.labInitialized){initialize(h);h.dataset.labInitialized='true';}});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
}());
