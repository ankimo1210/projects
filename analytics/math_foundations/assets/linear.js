(function(root,factory){
  'use strict';
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;else root.MathLinear=api;
}(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  function finite(x){if(typeof x!=='number'||!Number.isFinite(x))throw new TypeError('Expected a finite number');}
  function matrix(m){
    if(!Array.isArray(m)||m.length!==2||m.some(row=>!Array.isArray(row)||row.length!==2))throw new TypeError('Expected a 2 by 2 matrix');
    m.flat().forEach(finite);
  }
  function determinant2(m){
    matrix(m);const d=m[0][0]*m[1][1]-m[0][1]*m[1][0];
    if(!Number.isFinite(d))throw new RangeError('Numeric overflow');return d===0?0:d;
  }
  function transform2(m,v){
    matrix(m);if(!v||typeof v!=='object')throw new TypeError('Expected coordinates');finite(v.x);finite(v.y);
    const x=m[0][0]*v.x+m[0][1]*v.y,y=m[1][0]*v.x+m[1][1]*v.y;
    if(!Number.isFinite(x)||!Number.isFinite(y))throw new RangeError('Numeric overflow');
    return{x:x===0?0:x,y:y===0?0:y};
  }
  function areaState(m){
    const signedArea=determinant2(m);
    return{signedArea,area:Math.abs(signedArea),orientation:signedArea===0?'collapsed':signedArea>0?'preserved':'reversed',
      vertices:[{x:0,y:0},{x:1,y:0},{x:1,y:1},{x:0,y:1}].map(v=>transform2(m,v))};
  }
  return Object.freeze({determinant2,transform2,areaState});
}));
