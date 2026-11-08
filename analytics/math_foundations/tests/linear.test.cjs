'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const p=path.join(__dirname,'../assets/linear.js');
const math=fs.existsSync(p)?require(p):{};
test('determinant distinguishes shearing, orientation reversal, and collapse',()=>{
  assert.equal(math.determinant2([[1,2],[0,1]]),1);
  assert.equal(math.determinant2([[-2,0],[0,3]]),-6);
  assert.equal(math.determinant2([[1,2],[2,4]]),0);
  assert.equal(math.determinant2([[0,-1],[1,0]]),1);
});
test('the columns and transformed unit square agree with matrix action',()=>{
  const m=[[1,0.5],[0,1]];
  assert.deepEqual(math.transform2(m,{x:1,y:0}),{x:1,y:0});
  assert.deepEqual(math.transform2(m,{x:0,y:1}),{x:0.5,y:1});
  const s=math.areaState(m);
  assert.deepEqual(s.vertices,[{x:0,y:0},{x:1,y:0},{x:1.5,y:1},{x:0.5,y:1}]);
  assert.equal(s.area,1);
  assert.equal(s.orientation,'preserved');
  assert.equal(math.areaState([[-2,0],[0,3]]).orientation,'reversed');
  assert.equal(math.areaState([[1,1],[1,1]]).orientation,'collapsed');
});
test('area agrees with an independent polygon cross-product computation',()=>{
  for(const m of [[[2,1],[1,3]],[[-1,2],[2,1]],[[1,1],[1,1]]]){
    const s=math.areaState(m);
    const points=s.vertices;
    let twice=0;
    for(let i=0;i<4;i++){const j=(i+1)%4;twice+=points[i].x*points[j].y-points[j].x*points[i].y;}
    assert.equal(twice/2,s.signedArea);
  }
});
test('malformed matrices and nonfinite arithmetic are rejected',()=>{
  assert.equal(typeof math.determinant2,'function');
  for(const m of [null,[],[[1,2]],[[1,2],[3]],[[1,2],[3,Infinity]],[[1,'2'],[3,4]]])assert.throws(()=>math.determinant2(m));
  assert.throws(()=>math.determinant2([[1e200,0],[0,1e200]]));
  assert.throws(()=>math.transform2([[1,0],[0,1]],{x:NaN,y:0}));
});
