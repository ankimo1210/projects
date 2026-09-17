// ===== script block 1 =====
'use strict';
/* Deterministic monthly cash-flow model. All monetary values in JPY.
 * Tax law is a fixed-rate 2026 snapshot, not a tax-return calculator.
 * Identical initial capital and monthly disposable housing budgets for all strategies.
 */
const HousingModel = (() => {
 const clone=(p,x={})=>Object.assign({},p,x);
 function wageDeduction(g){return g<=2200000?Math.min(g,740000):g<=3600000?g*.3+80000:g<=6600000?g*.2+440000:g<=8500000?g*.1+1100000:1950000;}
 function basicDeduction(i,local=false){
  if(i>25000000)return 0;
  if(i>24500000)return local?150000:160000;
  if(i>24000000)return local?290000:320000;
  if(local)return 430000;
  if(i>23500000)return 480000;
  if(i>6550000)return 620000;
  if(i>4890000)return 670000;
  return 1040000;
 }
 function tax(g,s,other=0){
  const inc=Math.max(0,g-wageDeduction(g));
  const x=Math.max(0,Math.floor((inc-s-other-basicDeduction(inc))/1000)*1000);
  const xl=Math.max(0,Math.floor((inc-s-other-basicDeduction(inc,true))/1000)*1000);
  const brackets=[[1950000,.05,0],[3300000,.1,97500],[6950000,.2,427500],[9000000,.23,636000],[18000000,.33,1536000],[40000000,.4,2796000],[Infinity,.45,4796000]];
  const [,rate,offset]=brackets.find(([b])=>x<b);
  const national=Math.max(0,x*rate-offset)*1.021,local=xl*.1+5000;
  return {gross:g,wage_deduction:wageDeduction(g),income:inc,taxable:x,national,local,total:national+local,net:g-s-national-local,social:s,marginal:rate};
 }
 function housingTax(p,rent=p.rent,active=true){
  const R=rent*12,normal=tax(p.salary,p.social,p.other_deduction);
  if(!active)return {normal,corp:normal,annual_rent:R,annual_effective:R,benefit:0,tax_saving:0,amount_sacrificed:0,cash_gross:p.salary,annual_corp_net:normal.net-R};
  const A=p.cap>0?Math.min(R*p.sacrifice,p.cap):R*p.sacrifice;
  const corp=tax(p.salary-A+p.fringe,p.social_corp,p.other_deduction);
  const tax_saving=normal.total-corp.total,benefit=tax_saving+p.social-p.social_corp;
  return {normal,corp,annual_rent:R,annual_effective:R-benefit,benefit,tax_saving,amount_sacrificed:A,cash_gross:p.salary-A,annual_corp_net:p.salary-A-p.social_corp-corp.total-(R-A)};
 }
 function pmt(B,r,n){return n<=0?0:Math.abs(r)<1e-12?B/n:B*r/(1-Math.pow(1+r,-n));}
 function saleTax(p,price=null,years=p.years){
  const P=price===null?p.price*Math.pow(1+p.growth,years):price;
  const basisInitial=p.price*(1+p.basis_cost),B=basisInitial*p.building_share;
  // Acquisition is fixed at September 2026, as specified in the report.
  // Monthly hypothetical sales use the same calendar rule as terminal sales.
  const elapsedMonths=Math.round(years*12);
  const saleDate=new Date(Date.UTC(2026,8+elapsedMonths,17));
  const januaryFirst=new Date(Date.UTC(saleDate.getUTCFullYear(),0,1));
  const longTerm=januaryFirst>new Date(Date.UTC(2031,8,17));
  const reducedEligible=januaryFirst>new Date(Date.UTC(2036,8,17));
  const depreciationYears=Math.floor((elapsedMonths+6)/12);
  const dep=Math.min(B*.95,B*.9*.015*depreciationYears),basis=basisInitial-dep;
  const taxable=Math.max(0,P*(1-p.sell_cost)-basis-p.deduction_sale);
  let t=0;
  if(p.sale_tax){
   if(!longTerm)t=taxable*.3963;
   else if(reducedEligible&&p.reduced_long)t=Math.min(taxable,60000000)*.1421+Math.max(0,taxable-60000000)*.20315;
   else t=taxable*.20315;
  }
  return {tax:t,taxable_gain:taxable,depreciation:dep,basis,price:P,net_before_debt:P*(1-p.sell_cost)-t};
 }
 function run(p,allMonths=false){
  const n=p.years*12,term=p.mortgage_years*12;
  let bal=p.price*p.ltv,r=p.mortgage_rate/12;
  let pay=p.loan_type==='amortizing'?pmt(bal,r,term):bal*r;
  const initBuy=p.price*(1-p.ltv+p.buy_cost),initRent=p.rent*p.rent_initial,K=Math.max(initBuy,initRent);
  let ib=K-initBuy,ir=K-initRent,ic=ir,totalInt=0,taxSaved=0;
  const sums=[initBuy,initRent,initRent],rows=[];
  for(let m=1;m<=n;m++){
   const year=Math.floor((m-1)/12);
   if(p.step_year>0&&m===p.step_year*12+1&&m<=term){
    r=p.step_rate/12;pay=p.loan_type==='amortizing'?pmt(bal,r,term-m+1):bal*r;
   }
   const interest=m<=term?bal*r:0;
   let mp=0,principal=0;
   if(m<=term){mp=p.loan_type==='amortizing'?Math.min(pay,bal+interest):interest;principal=mp-interest;bal=Math.max(0,bal-principal);}
   totalInt+=interest;
   const rent=p.rent*Math.pow(1+p.rent_growth,year);
   const renewal=m%24===0&&m<n?rent*p.renewal:0;
   let cb=mp+p.owner_cost*Math.pow(1+p.owner_growth,year)/12;
   if(p.extra_repair&&m===p.repair_year*12)cb+=p.extra_repair;
   const cr=rent+renewal,tx=housingTax(p,rent,m<=p.corp_years*12),cc=tx.annual_effective/12+renewal;
   taxSaved+=tx.benefit/12;
   const budget=Math.max(cb,cr,cc);
   ib=ib*(1+p.invest/12)+(budget-cb);ir=ir*(1+p.invest/12)+(budget-cr);ic=ic*(1+p.invest/12)+(budget-cc);
   sums[0]+=cb;sums[1]+=cr;sums[2]+=cc;
   if(allMonths||m%12===0||m===n){
    const st=saleTax(p,null,m/12),wb=st.net_before_debt-bal+ib;
    rows.push({month:m,year:m/12,balance:bal,owner_spend:cb,rent_spend:cr,corp_spend:cc,common_budget:budget,principal,interest,owner_fin:ib,rent_fin:ir,corp_fin:ic,owner_wealth:wb,rent_wealth:ir,corp_wealth:ic,price:st.price,sale_tax:st.tax});
   }
  }
  const st=saleTax(p),wb=st.net_before_debt-bal+ib;
  return {owner_wealth:wb,rent_wealth:ir,corp_wealth:ic,balance:bal,owner_fin:ib,initial_capital:K,initial_buy:initBuy,initial_rent:initRent,total_interest:totalInt,sums,wealth_diff_rent:wb-ir,wealth_diff_corp:wb-ic,corp_advantage:ic-ir,tax_saved:taxSaved,rows,sale:st};
 }
 function bisect(f,lo,hi,iters=65){
  let fl=f(lo),fh=f(hi);if(!Number.isFinite(fl)||!Number.isFinite(fh))return null;
  if(Math.abs(fl)<.01)return lo;if(Math.abs(fh)<.01)return hi;
  if(fl*fh>0)return null;
  for(let k=0;k<iters;k++){const mid=(lo+hi)/2,fm=f(mid);if(fl*fm<=0){hi=mid;fh=fm;}else{lo=mid;fl=fm;}}
  return (lo+hi)/2;
 }
 function breakSale(p,mode='corp'){
  const res=run(p),target=res[mode+'_wealth']+res.balance-res.owner_fin;
  const price=bisect(x=>saleTax(p,x).net_before_debt-target,0,p.price*20);
  return price===null?null:{price,growth:Math.pow(price/p.price,1/p.years)-1,price_change:price/p.price-1,tax:saleTax(p,price).tax};
 }
 function breakPrice(p,mode='corp'){return bisect(x=>run(clone(p,{price:x}))['wealth_diff_'+mode],p.price*.05,p.price*4);}
 function breakEntry(p,mode='corp'){
  const exit=p.price*Math.pow(1+p.growth,p.years);
  return bisect(x=>run(clone(p,{price:x,growth:Math.pow(exit/x,1/p.years)-1}))['wealth_diff_'+mode],p.price*.05,p.price*4);
 }
 function breakRate(p,mode='corp'){return bisect(x=>run(clone(p,{mortgage_rate:x,step_year:0}))['wealth_diff_'+mode],0,.15);}
 return {clone,tax,housingTax,pmt,saleTax,run,bisect,breakSale,breakPrice,breakEntry,breakRate};
})();
if(typeof module!=='undefined')module.exports=HousingModel;


// ===== script block 2 =====
const BASE_PARAMS={"price": 250000000, "rent": 750000, "years": 10, "salary": 50000000, "social": 1500000, "social_corp": 1500000, "other_deduction": 0, "sacrifice": 1.0, "cap": 0, "fringe": 0, "corp_years": 10, "ltv": 0.9, "mortgage_rate": 0.015, "mortgage_years": 35, "loan_type": "amortizing", "buy_cost": 0.07, "sell_cost": 0.035, "owner_cost": 2500000, "rent_initial": 2.0, "renewal": 1.0, "growth": 0, "rent_growth": 0, "owner_growth": 0, "invest": 0.03, "building_share": 0.3, "basis_cost": 0.04, "deduction_sale": 30000000, "sale_tax": true, "reduced_long": true, "extra_repair": 0, "repair_year": 8, "step_year": 0, "step_rate": 0.03};


// ===== script block 3 =====
'use strict';
/* Sensitivity layer v2.1 — corrected monthly sale tax and active housing validation.
 * Monetary values: JPY. Rates: decimal. A sensitivity changes only named inputs;
 * dependent loan balances, cash flows, tax and sale proceeds are recomputed.
 */
const HousingSensitivity = (() => {
 const M=HousingModel;
 const specs=[
  ['price','dynamic','物件','購入価格','P','億円',1e8, .1,10,.01,'同じ住戸の家賃・所有中費用は固定。頭金、借入、取得費は価格に連動。','仮定'],
  ['rent','dynamic','賃貸','同等住戸の月額家賃','R','万円／月',1e4,10,200,1,'購入価格は固定。初期費用、更新料、社宅の税前振替額は家賃に連動。','本人申告'],
  ['years','dynamic','期間','居住・比較期間','T','年',1,1,35,1,'最後に売却。社宅の入力年数は固定し、実効適用年数は両者の短い方。','仮定'],
  ['growth','dynamic','判断用','予想する住戸価格変化率','g_H','%／年',.01,-10,10,.1,'最終純資産の評価用。g*を逆算するときの入力ではなく、g*との比較対象。','予想・仮定'],
  ['mortgage_rate','dynamic','融資','当初の住宅ローン金利','r_M','%／年',.01,0,15,.1,'金利変更なしなら全期間一定。変更設定があるときは当初期間だけを変更。','仮定'],
  ['invest','dynamic','資産運用','金融資産の税後利回り','r_F','%／年',.01,0,10,.5,'名目年率を12分割した月次複利。利回りの変動・損失確率は未モデル化。','仮定'],
  ['corp_years','dynamic','社宅','社宅を利用できる年数','T_C','年',1,0,35,1,'終了後は通常賃貸、額面報酬も元に戻る。失職・引越費用は別。','仮定'],
  ['owner_cost','dynamic','購入','所有中の費用','C_O','万円／年',1e4,0,1000,10,'管理・修繕積立・税・保険等の合計。買値を変えても自動比例させない。','要実額'],
  ['rent_growth','dynamic','賃貸','家賃増加率','g_R','%／年',.01,-5,10,.5,'年初に変更。税前振替率・上限に従って社宅側の税効果も再計算。','仮定'],
  ['owner_growth','dynamic','購入','所有中費用の増加率','g_C','%／年',.01,-5,10,.5,'年初に変更。臨時の追加修繕負担とは別計上。','仮定'],
  ['step_year','dynamic','金利経路','金利変更までの年数','T_r','年',1,0,34,1,'0なら変更なし。例えば5は6年目の開始時に変更。','仮定'],
  ['step_rate','dynamic','金利経路','変更後の金利','r_2','%／年',.01,0,15,.1,'変更時期が0なら計算に影響しない。5年・125%ルールは未実装。','仮定'],
  ['extra_repair','dynamic','修繕','追加修繕の一時負担','C_X','万円',1e4,0,5000,100,'指定年の年末に一度支出。平常時費用との二重計上に注意。','仮定'],
  ['repair_year','dynamic','修繕','追加修繕の支払年','T_X','年',1,1,35,1,'追加修繕額0円、または比較期間後の支払なら影響しない。','仮定'],
  ['salary','static','本人','社宅利用前の額面報酬','G','万円／年',1e4,3000,10000,100,'購入・通常賃貸では全額が現金給与に戻る前提。期間中固定。','本人申告'],
  ['sacrifice','static','社宅','家賃の税前振替率','a','%',.01,0,100,5,'残りは税引後本人負担。一般的な社宅非課税要件の判定とは別。','本人説明を仮定'],
  ['cap','static','社宅','税前振替の月額上限','A_max','万円／月',120000,0,200,5,'0は上限なし。内部では年額換算。会社規程は未確認。','要規程確認'],
  ['fringe','static','社宅','追加で課税される現物利益','V','万円／月',120000,0,50,1,'内部では年額換算。課税給与にだけ加算し、現金収入には加えない。','要明細確認'],
  ['social','static','税・社保','通常・購入の社会保険料','S_0','万円／年',1e4,0,500,10,'制度から自動推計せず入力額を使う。給与明細の実額に置換。','要実額'],
  ['social_corp','static','税・社保','社宅利用時の社会保険料','S_1','万円／年',1e4,0,500,10,'所得税の現物給与評価とは別。基準値は通常時と同額。','要実額'],
  ['other_deduction','static','税・社保','その他の所得控除','D','万円／年',1e4,0,500,10,'両ケース共通。所得税と住民税の控除差等は簡略化。','仮定'],
  ['ltv','static','融資','LTV','LTV','%',.01,0,100,5,'購入価格に対する借入割合。審査・担保評価は別途確認。','仮定'],
  ['mortgage_years','static','融資','ローン期間','T_M','年',1,5,50,1,'元利均等は満期に返済終了。IOは比較期間が満期を超えない範囲のみ。','仮定'],
  ['loan_type','static','融資','返済方法','—','',1,null,null,null,'IOは同金利・同費用の仮想比較。購入終了時に残債を売却代金から返す。','仮定'],
  ['buy_cost','static','取引','購入諸費用率','c_B','%',.01,0,15,.5,'頭金とは別の初期支出。税務取得費に含まれる額とは一致しない。','仮定'],
  ['sell_cost','static','取引','売却費用率','c_S','%',.01,0,10,.1,'損益分岐として求める売値にも比例。','仮定'],
  ['rent_initial','static','賃貸','賃貸初期費用','n_0','か月分',1,0,10,.5,'返還される敷金を除く。社宅側も税引後で同額を負担。','仮定'],
  ['renewal','static','賃貸','2年ごとの更新料','n_U','か月分',1,0,3,.5,'退出する最終月には課さない。社宅側も税引後負担。','仮定'],
  ['building_share','static','売却税','税務上の建物比率','s_B','%',.01,0,100,5,'非業務用RCの取得費減額に使用。住宅の価格予想とは別。','要資料確認'],
  ['basis_cost','static','売却税','取得費に入れる購入費率','c_A','%',.01,0,15,.5,'購入諸費用率以下。土地・建物に価格比率で配分。','要資料確認'],
  ['deduction_sale','static','売却税','売却益の特別控除','D_S','万円',1e4,0,3000,1000,'3,000万円控除等の要件を満たす仮定。自動資格判定はしない。','要件付き仮定'],
  ['sale_tax','static','売却税','売却税の算入','—','',1,null,null,null,'2026年に確認した税率を固定する簡易計算。特例の適否は別途確認。','算入'],
  ['reduced_long','static','売却税','10年超所有の軽減税率','—','',1,null,null,null,'2026年9月取得とし、売却年1月1日に10年超かを判定。月次CSVでは124か月から。','要件付き仮定']
 ];
 const meta=specs.map(v=>Object.fromEntries(['key','group','category','label','symbol','unit','scale','min','max','step','note','source'].map((k,i)=>[k,v[i]])));
 const byKey=Object.fromEntries(meta.map(s=>[s.key,s]));
 function validate(p){
  for(const s of meta){
   if(['loan_type','sale_tax','reduced_long'].includes(s.key))continue;
   const v=p[s.key]/s.scale;
   if(!Number.isFinite(v)||v<s.min-1e-8||v>s.max+1e-8)return s.label+'が入力範囲外';
  }
  for(const k of ['years','corp_years','mortgage_years','step_year','repair_year'])if(!Number.isInteger(p[k]))return '年数は整数';
  if(p.basis_cost>p.buy_cost)return '税務取得費への算入率が購入諸費用率を超える';
  if(!['io','amortizing'].includes(p.loan_type))return '返済方式が不正';
  if(p.loan_type==='io'&&p.years>p.mortgage_years)return 'IOの比較期間がローン満期を超える';
  const activeYears=Math.min(p.years,p.corp_years);
  if(activeYears>0){
   const maxRent=Math.max(p.rent,p.rent*Math.pow(1+p.rent_growth,activeYears-1));
   const a=p.cap>0?Math.min(maxRent*12*p.sacrifice,p.cap):maxRent*12*p.sacrifice;
   if(p.salary-a+p.fringe<15000000)return '社宅振替後給与が高所得者向けモデルの範囲外';
  }
  return null;
 }
 function solve(p,r,mode){
  const target=r[mode+'_wealth']+r.balance-r.owner_fin;
  const f=x=>M.saleTax(p,x).net_before_debt-target;
  if(f(0)>0.01)return {status:'dominates',price:0,growth:null,text:'売値0円でも購入優位'};
  const price=M.bisect(f,0,p.price*20);
  if(price===null)return {status:'outside',price:null,growth:null,text:'0〜買値20倍に分岐なし'};
  return {status:'ok',price,growth:Math.pow(price/p.price,1/p.years)-1,price_change:price/p.price-1,tax:M.saleTax(p,price).tax,residual:f(price)};
 }
 function evaluate(p){
  const error=validate(p);if(error)return {error,p};
  const r=M.run(p);if(!Number.isFinite(r.owner_wealth+r.rent_wealth+r.corp_wealth))return {error:'計算範囲外',p};
  return {p,r,normal:solve(p,r,'rent'),corp:solve(p,r,'corp')};
 }
 function unique(xs){return [...new Set(xs.map(x=>Number(x.toFixed(8))))].sort((a,b)=>a-b);}
 function defaultValues(key,p){
  const s=byKey[key],v=p[key]/s.scale;
  let vs;
  switch(key){
   case 'price':vs=[v*.6,v*.7,v*.8,v*.88,v,v*1.1,v*1.2,v*1.3,v*1.4];break;
   case 'rent':vs=[v*.6,v*.8,v,v*1.2,v*1.4,v*1.6];break;
   case 'mortgage_rate':vs=[0,.5,1,1.5,2,2.5,3,4,5];break;
   case 'invest':vs=[0,1,2,3,4,5,6,8];break;
   case 'years':vs=[3,5,6,10,11,15,20,25,30];break;
   case 'corp_years':vs=[0,1,3,5,7,10,15,20,p.years];break;
   case 'owner_cost':vs=v===0?[0,50,100,150,250,350,500]:[0,v*.4,v*.6,v*.8,v,v*1.2,v*1.4,v*1.6];break;
   case 'rent_growth':case 'owner_growth':vs=[-2,0,1,2,3,4,5];break;
   case 'ltv':vs=[0,25,50,70,80,90,100];break;
   case 'buy_cost':vs=[3,4,5,6,7,8,10];break;
   case 'sell_cost':vs=[0,1,2,3,3.5,4,5];break;
   case 'salary':vs=[3000,3500,4000,4500,5000,6000,7500,10000];break;
   case 'sacrifice':vs=[0,25,50,70,80,90,100];break;
   case 'extra_repair':vs=[0,300,500,1000,2000,3000];break;
   case 'building_share':vs=[0,10,20,30,40,50,70,100];break;
   case 'mortgage_years':vs=[10,15,20,25,30,35,40,50];break;
   case 'fringe':vs=[0,1,3,5,10,20,30];break;
   default:vs=[v*.5,v*.75,v,v*1.25,v*1.5];
  }
  return unique([...vs,v].map(x=>Number(x.toFixed(3))).filter(x=>x>=s.min&&x<=s.max));
 }
 function curve(p,key,values){const s=byKey[key];return values.map(value=>({value,...evaluate({...p,[key]:Number((value*s.scale).toPrecision(14))})}));}
 function stresses(p){
  const clamp=(key,v)=>Math.max(byKey[key].min*byKey[key].scale,Math.min(byKey[key].max*byKey[key].scale,v));
  const rows=[
   ['price',p.price*.8,p.price*1.2,'買値 −20% / ＋20%'],
   ['rent',p.rent*.8,p.rent*1.2,'家賃 −20% / ＋20%'],
   ['mortgage_rate',p.mortgage_rate-.01,p.mortgage_rate+.01,'当初金利 −1pp / ＋1pp'],
   ['invest',p.invest-.02,p.invest+.02,'運用利回り −2pp / ＋2pp'],
   ['years',p.years-5,p.years+5,'居住年数 −5年 / ＋5年'],
   ['corp_years',0,p.years,'社宅なし / 居住全期間'],
   ['owner_cost',p.owner_cost*.6,p.owner_cost*1.4,'所有費用 −40% / ＋40%'],
   ['ltv',p.ltv-.2,p.ltv+.1,'LTV −20pp / ＋10pp']
  ];
  return rows.map(([key,lo,hi,label])=>({key,label,lo:evaluate({...p,[key]:clamp(key,lo)}),hi:evaluate({...p,[key]:clamp(key,hi)})}));
 }
 function grid(p,preset){
  let xkey,ykey,xs,ys;
  if(preset==='price_rent'){
   xkey='price';ykey='rent';const P=p.price/1e8,R=p.rent/1e4;
   xs=[P*.7,P*.8,P*.88,P,P*1.1,P*1.2];ys=[R*.6,R*.8,R,R*1.2,R*1.4];
  }else if(preset==='duration'){
   xkey='years';ykey='corp_years';xs=[3,5,10,15,20,p.years];ys=[0,3,5,10,20,p.corp_years];
  }else{
   xkey='mortgage_rate';ykey='invest';xs=[0,1,1.5,2,2.5,3,4];ys=[0,1,3,5];
  }
  function prep(key,a){const s=byKey[key];return unique([...a,p[key]/s.scale].map(v=>Number(v.toFixed(3))).filter(v=>v>=s.min&&v<=s.max));}
  xs=prep(xkey,xs);ys=prep(ykey,ys);
  const cells=ys.map(y=>xs.map(x=>({x,y,...evaluate({...p,[xkey]:Number((x*byKey[xkey].scale).toPrecision(14)),[ykey]:Number((y*byKey[ykey].scale).toPrecision(14))})})));
  return {preset,xkey,ykey,xs,ys,cells};
 }
 return {meta,byKey,validate,evaluate,curve,stresses,grid,defaultValues};
})();
if(typeof module!=='undefined')module.exports=HousingSensitivity;


// ===== script block 4 =====
'use strict';
if(typeof document!=='undefined')(()=>{
 const M=HousingModel, $=id=>document.getElementById(id);
 const defaults={...BASE_PARAMS,corp_years:10,step_rate:.03};
 const moneyKeys=new Set(['price','rent','salary','social','social_corp','other_deduction','owner_cost','deduction_sale','extra_repair']);
 const pctKeys=new Set(['ltv','mortgage_rate','buy_cost','sell_cost','growth','rent_growth','owner_growth','invest','building_share','basis_cost','step_rate','sacrifice']);
 const annualFromMonthly=new Set(['cap','fringe']);
 let current=null, result=null;
 const fmtMan=(v,d=0)=>Number(v/10000).toLocaleString('ja-JP',{minimumFractionDigits:d,maximumFractionDigits:d})+'万円';
 const fmtOku=(v,d=3)=>(v/1e8).toFixed(d)+'億円';
 const fmtPct=(v,d=2)=>((v>=0?'+':'')+(v*100).toFixed(d)+'%');
 const fmtDelta=v=>(v>=0?'+':'−')+fmtMan(Math.abs(v));
 function fill(p){
  for(const e of document.querySelectorAll('[data-param]')){
   const k=e.dataset.param;let v=p[k];if(v===undefined)continue;
   if(e.type==='checkbox'){e.checked=Boolean(v);continue;}
   if(moneyKeys.has(k))v/=10000;else if(pctKeys.has(k))v*=100;else if(annualFromMonthly.has(k))v/=120000;
   e.value=typeof v==='number'?String(Number(v.toFixed(7))):v;
  }
 }
 function read(){
  const p={...defaults};
  for(const e of document.querySelectorAll('[data-param]')){
   const k=e.dataset.param;
   if(e.type==='checkbox'){p[k]=e.checked;continue;}
   if(k==='loan_type'){p[k]=e.value;continue;}
   if(e.value.trim()==='')throw new Error('空欄の入力があります。すべての金額・年数を入力してください。');
   let v=Number(e.value);if(!Number.isFinite(v))throw new Error('数値を確認してください。');
   if(e.min!==''&&v<Number(e.min)||e.max!==''&&v>Number(e.max))throw new Error(e.previousElementSibling.textContent+'：'+e.min+'〜'+e.max+'の範囲で入力してください。');
   if(moneyKeys.has(k))v*=10000;else if(pctKeys.has(k))v/=100;else if(annualFromMonthly.has(k))v*=120000;
   p[k]=v;
  }
  const error=HousingSensitivity.validate(p);
  if(error)throw new Error(error);
  return p;
 }
 function makeTable(head,rows){return '<div class="table-wrap"><table><thead><tr>'+head.map(s=>'<th>'+s+'</th>').join('')+'</tr></thead><tbody>'+rows.map(r=>'<tr>'+r.map(v=>'<td>'+v+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>';}
 function plot(p){
  const xmin=Math.min(-3,p.growth*100-1),xmax=Math.max(6,p.growth*100+1),N=64;
  const xs=Array.from({length:N+1},(_,i)=>xmin+(xmax-xmin)*i/N),rr=xs.map(x=>M.run({...p,growth:x/100}));
  const vals=[...rr.map(r=>r.wealth_diff_rent/1e4),...rr.map(r=>r.wealth_diff_corp/1e4)];
  let lo=Math.min(0,...vals),hi=Math.max(0,...vals);const range=Math.max(1,hi-lo);lo-=range*.06;hi+=range*.06;
  const W=940,H=355,L=88,R=28,T=30,B=62,w=W-L-R,h=H-T-B;
  const X=x=>L+(x-xmin)/(xmax-xmin)*w,Y=y=>T+(hi-y)/(hi-lo)*h;
  let out='<div class="legend"><span class="rent">購入 − 通常賃貸</span><span class="corp">購入 − 借上社宅</span></div><svg class="chart" viewBox="0 0 '+W+' '+H+'" role="img" aria-label="入力に基づく損益分岐チャート">';
  for(let i=0;i<=5;i++){
   const y=lo+(hi-lo)*i/5;
   out+='<line class="grid" x1="'+L+'" x2="'+(W-R)+'" y1="'+Y(y)+'" y2="'+Y(y)+'"/><text class="tick" x="'+(L-10)+'" y="'+(Y(y)+4)+'" text-anchor="end">'+Math.round(y).toLocaleString('ja-JP')+'</text>';
  }
  out+='<line class="grid zero" x1="'+L+'" x2="'+(W-R)+'" y1="'+Y(0)+'" y2="'+Y(0)+'"/>';
  for(let i=Math.ceil(xmin);i<=xmax;i++)out+='<text class="tick" x="'+X(i)+'" y="'+(H-29)+'" text-anchor="middle">'+i+'</text>';
  for(const [field,cl] of [['wealth_diff_rent','rent'],['wealth_diff_corp','corp']]){
   const points=rr.map((r,i)=>X(xs[i]).toFixed(2)+','+Y(r[field]/1e4).toFixed(2)).join(' ');
   out+='<polyline class="series '+cl+'" points="'+points+'"/>';
  }
  const x=X(p.growth*100);
  out+='<line x1="'+x+'" x2="'+x+'" y1="'+T+'" y2="'+(H-B)+'" stroke="#9eafb5" stroke-dasharray="3 5"/><text class="tick" x="'+Math.min(W-R-90,Math.max(L,x+7))+'" y="'+(T+13)+'">現在の設定 '+fmtPct(p.growth)+'</text>';
  return out+'<text class="axis-title" x="'+L+'" y="17">購入 − 賃貸の最終純資産差（万円）</text><text class="axis-title" x="'+(W-R)+'" y="'+(H-3)+'" text-anchor="end">その住戸の年率価格変化率（%）</text></svg>';
 }
 function recalc(){
  try{
   const p=read(),r=M.run(p),tx=M.housingTax(p,p.rent,p.corp_years>0),bc=M.breakSale(p),br=M.breakSale(p,'rent');
   current=p;result=r;$('sim-error').style.display='none';$('sim-results').style.opacity='1';
   $('sim-rent').textContent=fmtMan(tx.annual_effective/12,1);
   $('sim-tax').textContent=fmtMan(tx.benefit);
   $('sim-be-price').textContent=bc?fmtOku(bc.price):'範囲内なし';
   $('sim-be-growth').textContent=bc?fmtPct(bc.growth):'範囲内なし';
   $('sim-be-period').textContent=p.years+'年後の売却価格';
   const preferred=r.wealth_diff_corp>=0?'購入':'借上社宅';
   $('sim-verdict').innerHTML='<strong>現在の仮定では、'+preferred+'が'+(preferred==='購入'?'借上社宅':'購入')+'を約'+fmtMan(Math.abs(r.wealth_diff_corp))+'上回ります。</strong><p>住戸価格 '+fmtPct(p.growth)+' / 年、比較期間 '+p.years+'年、社宅適用 '+Math.min(p.corp_years,p.years)+'年。通常賃貸との比較は購入側 '+fmtDelta(r.wealth_diff_rent)+'。</p>';
   const mp=p.loan_type==='io'?p.price*p.ltv*p.mortgage_rate/12:M.pmt(p.price*p.ltv,p.mortgage_rate/12,p.mortgage_years*12);
   $('sim-table').innerHTML=makeTable([p.years+'年後の比較','購入','通常賃貸','借上社宅'],[
    ['共通の初期資金',fmtMan(r.initial_capital),fmtMan(r.initial_capital),fmtMan(r.initial_capital)],
    ['初期の住居支出',fmtMan(r.initial_buy),fmtMan(r.initial_rent),fmtMan(r.initial_rent)],
    ['初年度の通常月負担',fmtMan(mp+p.owner_cost/12,1),fmtMan(p.rent,1),fmtMan(tx.annual_effective/12,1)],
    ['購入側の最終売値',fmtOku(r.sale.price),'—','—'],
    ['売却税 / 残債',fmtMan(r.sale.tax)+' / '+fmtMan(r.balance),'—','—'],
    ['最終金融資産',fmtMan(r.owner_fin),fmtMan(r.rent_wealth),fmtMan(r.corp_wealth)],
    ['最終比較用純資産','<strong>'+fmtMan(r.owner_wealth)+'</strong>','<strong>'+fmtMan(r.rent_wealth)+'</strong>','<strong>'+fmtMan(r.corp_wealth)+'</strong>'],
    ['購入と互角の売値','—',br?fmtOku(br.price):'範囲内なし',bc?fmtOku(bc.price):'範囲内なし'],
    ['必要な住戸の年率価格変化','—',br?fmtPct(br.growth):'—',bc?fmtPct(bc.growth):'—']
   ]);
   const beEntry=M.breakEntry(p),beRate=M.breakRate(p),beFlat=M.breakPrice(p);
   const texts=[];
   if(beEntry!==null)texts.push('将来売値 '+fmtOku(r.sale.price)+' を固定した分岐買値：'+fmtOku(beEntry)+'。');
   if(beFlat!==null)texts.push('住戸の年率価格変化 '+fmtPct(p.growth)+' を固定した分岐買値：'+fmtOku(beFlat)+'。');
   if(beRate!==null)texts.push('一定金利での分岐金利：'+(beRate*100).toFixed(2)+'%。');
   else if(M.run({...p,mortgage_rate:0,step_year:0}).wealth_diff_corp<0)texts.push('一定金利0%でも購入は社宅を下回る。');
   else texts.push('一定金利0〜15%の範囲に金利分岐なし。');
   $('sim-thresholds').textContent=texts.join(' ');
   $('sim-plot').innerHTML=plot(p);
   const warnings=['給与課税・住民税は年次帰属で概算。税制・報酬は期間中固定し、住民税の徴収時差は未再現。'];
   if(p.corp_years<p.years)warnings.push('社宅終了後は通常賃貸へ移行し、報酬が元の額面に戻る。失職による収入減や引越費用は含まない。');
   if(p.step_year>0)warnings.push('金利変更時に返済額を再計算。5年・125%ルールなし。分岐金利の表示だけは金利一定として逆算。');
   if(p.loan_type==='io')warnings.push('IOは仮想比較。最後に残元本を売却代金から一括返済する。');
   if(!p.sale_tax)warnings.push('売却税OFF：税引後の購入価値を過大に評価する可能性がある。');
   if(p.rent_growth>0&&p.cap===0)warnings.push('家賃上昇分も税前振替が全額または指定率で続く仮定。勤務先上限は未確認。');
   if(r.sale.taxable_gain>100000000)warnings.push('売却益が大きいため、高所得者への追加課税等を含む個別税務確認が必要。本モデルは通常の譲渡税計算に限定。');
   if(p.years>20)warnings.push('20年超の試算は制度・税制・報酬の固定仮定への依存が強い。');
   if(p.fringe>0)warnings.push('現物利益 '+fmtMan(p.fringe)+' / 年は課税給与に加算するが、現金支給には加算しない。');
   $('sim-warning').textContent=warnings.join(' ');
   $('sim-status').textContent='再計算済み · 購入 '+fmtOku(p.price,2)+' / 家賃 '+fmtMan(p.rent,1)+' / '+p.years+'年';
   document.dispatchEvent(new CustomEvent('housing:updated',{detail:{parameters:{...p},result:r}}));
   return true;
  }catch(e){
   $('sim-error').textContent=e.message;$('sim-error').style.display='block';$('sim-results').style.opacity='.45';
   $('sim-status').textContent='入力を確認してください。結果は直前の有効な設定です。';
   document.dispatchEvent(new CustomEvent('housing:invalid',{detail:{message:e.message}}));
   return false;
  }
 }
 function download(text,name,type){const a=document.createElement('a');const url=URL.createObjectURL(new Blob([text],{type}));a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);}
 $('recalculate').addEventListener('click',recalc);
 $('reset').addEventListener('click',()=>{fill(defaults);recalc();});
 $('previous').addEventListener('click',()=>{fill({...defaults,price:100000000,rent:300000,owner_cost:1000000});recalc();});
 for(const e of document.querySelectorAll('[data-param]')){
  e.addEventListener('input',()=>{$('sim-status').textContent='入力変更あり · 「再計算」を押してください';document.dispatchEvent(new Event('housing:dirty'));});
  e.addEventListener('keydown',event=>{if(event.key==='Enter')recalc();});
 }
 $('csv').addEventListener('click',()=>{
  recalc();if($('sim-error').style.display==='block'||!current)return;
  const r=M.run(current,true),cols=[['month','経過月'],['year','経過年'],['common_budget','共通住居予算_円'],['owner_spend','購入住居支出_円'],['rent_spend','通常賃貸支出_円'],['corp_spend','社宅実質支出_円'],['interest','支払利息_円'],['principal','元本返済_円'],['balance','ローン残高_円'],['price','住宅価格_円'],['sale_tax','仮売却税_円'],['owner_fin','購入金融資産_円'],['rent_fin','通常賃貸金融資産_円'],['corp_fin','社宅金融資産_円'],['owner_wealth','購入比較純資産_円'],['rent_wealth','通常賃貸比較純資産_円'],['corp_wealth','社宅比較純資産_円']];
  const lines=[cols.map(c=>c[1]).join(',')];for(const row of r.rows)lines.push(cols.map(([k])=>Number(row[k]).toFixed(k==='year'?6:2)).join(','));
  download('\ufeff'+lines.join('\r\n'),'housing_monthly_cashflows.csv','text/csv;charset=utf-8');
 });
 $('save-settings').addEventListener('click',()=>{recalc();if($('sim-error').style.display==='block'||!current)return;download(JSON.stringify({model:'housing-tax-comparison-v2-2026-09-17',units:'JPY and decimal rates',parameters:current},null,2),'housing_scenario_settings.json','application/json');});
 window.HousingUI={defaults:{...defaults},getCurrent:()=>({...current||defaults}),getResult:()=>result,recalculate:recalc,update:patch=>{fill(patch);return recalc();}};
 fill(defaults);recalc();
})();


// ===== script block 5 =====
'use strict';
if(typeof document!=='undefined')(() => {
 const S=HousingSensitivity,M=HousingModel,U=window.HousingUI,$=id=>document.getElementById(id);
 const E=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const n=(v,d=0)=>Number(v).toLocaleString('ja-JP',{minimumFractionDigits:d,maximumFractionDigits:d});
 const m=(v,d=0)=>n(v/1e4,d)+'万円',o=(v,d=3)=>n(v/1e8,d)+'億円';
 const sign=v=>v>=-1e-10?'+':'−';
 const rate=(v,d=2)=>Number.isFinite(v)?sign(v)+n(Math.abs(v*100),d)+'%':'—';
 const pp=(v,d=2)=>Number.isFinite(v)?sign(v)+n(Math.abs(v*100),d)+'pp':'—';
 const num=v=>Number.isFinite(v)?n(v,Math.abs(v-Math.round(v))<1e-7?0:Math.abs(v)<10?2:1):'—';
 const label=(k,v)=>k==='loan_type'?(v==='io'?'全期間IO':'元利均等'):typeof v==='boolean'?(v?'ON':'OFF'):num(v/S.byKey[k].scale)+(S.byKey[k].unit?' '+S.byKey[k].unit:'');
 const g=r=>r?.status==='ok'?r.growth:null;
 const gr=r=>r?.status==='ok'?rate(r.growth):E(r?.text||'—');
 const sp=r=>r?.status==='ok'?o(r.price):E(r?.text||'—');
 const same=(a,b)=>typeof a==='number'&&typeof b==='number'?Math.abs(a-b)<1e-7*Math.max(1,Math.abs(a)):a===b;
 const table=(head,rows,cls='')=>'<div class="table-wrap" tabindex="0" role="region" aria-label="横にスクロールできるデータ表"><table class="'+cls+'"><thead><tr>'+head.map(h=>'<th scope="col">'+h+'</th>').join('')+'</tr></thead><tbody>'+rows.join('')+'</tbody></table></div>';
 const row=(cells,cls='')=>'<tr class="'+cls+'">'+cells.map(c=>'<td>'+c+'</td>').join('')+'</tr>';
 const modeNames={corp:'借上社宅',normal:'通常賃貸'};
 const curveKeys=['mortgage_rate','invest','price','rent','years','corp_years','owner_cost','rent_growth','owner_growth','ltv','buy_cost','sell_cost','salary','sacrifice','extra_repair','building_share','mortgage_years','fringe'];
 let p=U.getCurrent(),base=S.evaluate(p),curves=[],trows=[],hg=null,gridKey='mortgage_rate',customValues=false,dirty=false;
 let renderVersion=0;
 function showMsg(text){$('export-message').textContent=text;}
 function emitDownload(text,name,type){
  const url=URL.createObjectURL(new Blob([text],{type})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),2500);
 }
 function csv(data){return '\ufeff'+data.map(r=>r.map(v=>'"'+String(v??'').replace(/"/g,'""')+'"').join(',')).join('\r\n');}
 function checkFresh(){if(!U.recalculate())return false;return true;}
 function baselineMark(key,value){return same(value,p[key])?'<span class="baseline-label">現在値</span>':'';}
 function kpis(){
  const ng=g(base.normal),cg=g(base.corp),delta=(ng!==null&&cg!==null)?cg-ng:null,margin=cg===null?null:p.growth-cg;
  const card=(title,value,sub,cls)=>'<div class="kpi '+cls+'"><span>'+title+'</span><strong>'+value+'</strong><small>'+sub+'</small></div>';
  $('dash-kpis').innerHTML=card('購入 vs 通常賃貸',gr(base.normal),'分岐売値 '+sp(base.normal),'rent-color')+
   card('購入 vs 借上社宅',gr(base.corp),'分岐売値 '+sp(base.corp),'purple')+
   card('社宅で上がるハードル',delta===null?'—':pp(delta),'社宅 g* − 通常賃貸 g*','navy')+
   card('予想と分岐の差',margin===null?'—':pp(margin),'予想 '+rate(p.growth)+' − 社宅 g*','');
  const tx=M.housingTax(p,p.rent,p.corp_years>0);
  $('dash-payroll').innerHTML='現在の条件：社宅の実質家賃 <strong>'+m(tx.annual_effective/12,1)+'/月</strong>、初年度の税・社保メリット <strong>'+m(tx.benefit)+'/年</strong>。基準入力は年収・家賃の本人説明、その他は明示した仮定。';
  $('dash-status').className='scenario-status';
  $('dash-status').textContent='計算済み ｜ 買値 '+o(p.price,2)+'・家賃 '+m(p.rent,1)+'/月・保有 '+p.years+'年・社宅入力 '+p.corp_years+'年（有効 '+Math.min(p.years,p.corp_years)+'年）・金利 '+num(p.mortgage_rate*100)+'%・運用 '+num(p.invest*100)+'%';
 }
 function renderParamTables(){
  for(const group of ['dynamic','static']){
   const specs=S.meta.filter(s=>s.group===group);
   $(group+'-count').textContent=specs.length+'項目';
   const rows=specs.map(s=>{
    const k=s.key,v=U.defaults[k],editableId='p-'+k;
    let editor;
    if(k==='loan_type')editor='<select class="param-editor" id="'+editableId+'" data-edit="'+k+'" aria-label="'+E(s.label)+'"><option value="amortizing">元利均等</option><option value="io">全期間IO</option></select>';
    else if(typeof v==='boolean')editor='<input class="param-editor" id="'+editableId+'" type="checkbox" data-edit="'+k+'" aria-label="'+E(s.label)+'">';
    else editor='<input class="param-editor" id="'+editableId+'" type="number" inputmode="decimal" data-edit="'+k+'" min="'+s.min+'" max="'+s.max+'" step="'+s.step+'" aria-label="'+E(s.label)+'（'+E(s.unit)+'）"><small class="param-unit">'+E(s.unit)+'</small>';
    const sourceClass=s.source.includes('本人')?'declared':s.source.includes('要')?'verify':'assumed';
    const link=curveKeys.includes(k)?'<button type="button" class="param-sense no-print" data-view="'+k+'">感応度を見る ↗</button>':'';
    return '<tr id="pr-'+k+'"><td><label for="'+editableId+'">'+E(s.label)+'</label><span class="param-symbol">'+E(s.symbol)+' · '+E(s.category)+'</span>'+link+'</td><td>'+E(label(k,v))+'</td><td class="param-current">'+editor+'</td><td><span class="source-mark"><i class="source-dot '+sourceClass+'"></i>'+E(s.source)+'</span></td><td class="param-note">'+E(s.note)+'</td></tr>';
   });
   $(group+'-table').innerHTML=table(['パラメータ','初期値','現在の値（編集）','根拠','固定・連動の扱い'],rows,'param-table');
  }
 }
 function syncParams(){
  for(const s of S.meta){const e=$('p-'+s.key),v=p[s.key];if(e.type==='checkbox')e.checked=v;else e.value=typeof v==='number'?String(Number((v/s.scale).toFixed(7))):v;$('pr-'+s.key).classList.toggle('changed',!same(v,U.defaults[s.key]));}
 }
 function states(){
  const r=base.r,last=r.rows.at(-1),ownerInc=p.owner_cost*Math.pow(1+p.owner_growth,p.years-1);
  $('states-table').innerHTML=table(['状態変数','最終時点の値','計算の意味'],[
   row(['住戸価格 P_T',o(last.price),'入力した予想 g_H で評価。分岐売値 P* とは別。']),
   row(['ローン残高 B_T',m(last.balance),'元本返済後・住宅売却前。IOなら元本が残る。']),
   row(['最終月の元本 / 利息',m(last.principal,1)+' / '+m(last.interest,1),'ローン満期後は0円。']),
   row(['最終年の月額家賃',m(p.rent*Math.pow(1+p.rent_growth,p.years-1),1),'家賃増加率に従って毎年変更。']),
   row(['最終年の所有費用',m(ownerInc)+'/年','追加修繕の一時金を除く。']),
   row(['金融資産：購入 / 通常 / 社宅',m(r.owner_fin)+' / '+m(r.rent_wealth)+' / '+m(r.corp_wealth),'同じ初期資金・共通予算で差額を運用。絶対水準は共通予算の取り方に依存。']),
   row(['売却手取りEquity',m(r.sale.net_before_debt-r.balance),'予想売値 − 売却費用 − 売却税 − 残債。']),
   row(['純資産差：購入 − 通常賃貸',(r.wealth_diff_rent>=0?'+':'−')+m(Math.abs(r.wealth_diff_rent)),'正なら、入力した予想経路では購入が上回る。']),
   row(['純資産差：購入 − 借上社宅',(r.wealth_diff_corp>=0?'+':'−')+m(Math.abs(r.wealth_diff_corp)),'購入・賃貸の優劣は純資産差で比較。']),
   row(['累計税・社保メリット',m(r.tax_saved),'社宅利用月だけを集計した名目合計。運用収益を含めない。'])
  ]);
 }
 function chartCurve(key,data){
  const s=S.byKey[key],valid=data.filter(q=>!q.error),xmin=Math.min(...data.map(x=>x.value)),xmax=Math.max(...data.map(x=>x.value));
  const values=valid.flatMap(q=>[g(q.normal),g(q.corp)]).filter(v=>v!==null).map(v=>v*100);
  if(!values.length)return '<p class="note">入力範囲内に有効な分岐点がありません。試す値または他のパラメータを確認してください。</p>';
  let lo=Math.min(0,p.growth*100,...values),hi=Math.max(0,p.growth*100,...values),span=Math.max(.5,hi-lo);lo-=span*.12;hi+=span*.15;
  const W=980,H=390,L=78,R=30,T=38,B=65,w=W-L-R,h=H-T-B;
  const X=x=>L+(x-xmin)/(xmax-xmin||1)*w,Y=y=>T+(hi-y)/(hi-lo)*h;
  let out='<div class="legend"><span class="rent">購入 vs 通常賃貸</span><span class="corp">購入 vs 借上社宅</span></div><svg class="chart" viewBox="0 0 '+W+' '+H+'" role="img" aria-label="'+E(s.label)+'と必要な年率価格変化の感応度"><title>'+E(s.label)+'を変更した損益分岐</title>';
  for(let i=0;i<=5;i++){const y=lo+(hi-lo)*i/5;out+='<line class="grid" x1="'+L+'" x2="'+(W-R)+'" y1="'+Y(y)+'" y2="'+Y(y)+'"/><text class="tick" x="'+(L-12)+'" y="'+(Y(y)+4)+'" text-anchor="end">'+n(y,1)+'%</text>';}
  const predict=p.growth*100;out+='<line class="s-line-reference" x1="'+L+'" x2="'+(W-R)+'" y1="'+Y(predict)+'" y2="'+Y(predict)+'"/><text class="tick" x="'+(W-R-4)+'" y="'+(Y(predict)-7)+'" text-anchor="end">予想 g_H '+rate(p.growth)+'</text>';
  const currentX=X(p[key]/s.scale);out+='<line class="s-line-reference" x1="'+currentX+'" x2="'+currentX+'" y1="'+T+'" y2="'+(H-B)+'"/>';
  const tickEvery=Math.max(1,Math.ceil(data.length/11));
  data.forEach((q,i)=>{const isBase=same(q.value*s.scale,p[key]);if(i%tickEvery===0||isBase||i===data.length-1)out+='<line class="grid" x1="'+X(q.value)+'" x2="'+X(q.value)+'" y1="'+T+'" y2="'+(H-B)+'"/><text class="tick" x="'+X(q.value)+'" y="'+(H-B+25)+'" text-anchor="middle">'+num(q.value)+'</text>';});
  for(const [mode,cl] of [['normal','rent'],['corp','corp']]){
   let part=[];const flush=()=>{if(part.length)out+='<polyline class="series '+cl+'" points="'+part.join(' ')+'"/>';part=[];};
   for(const q of data){const v=q.error?null:g(q[mode]);if(v===null){flush();continue;}part.push(X(q.value).toFixed(2)+','+Y(v*100).toFixed(2));}flush();
   for(const q of data){const v=q.error?null:g(q[mode]);if(v===null)continue;const isBase=same(q.value*s.scale,p[key]);out+='<circle class="s-dot-'+cl+(isBase?' s-base-dot':'')+'" cx="'+X(q.value)+'" cy="'+Y(v*100)+'" r="'+(isBase?6:4)+'"><title>'+E(s.label)+': '+num(q.value)+' '+E(s.unit)+' / '+modeNames[mode]+' g*: '+rate(v)+'</title></circle>';}
  }
  out+='<text class="axis-title" x="'+L+'" y="18">購入に必要な年率価格変化 g*（% / 年）</text><text class="axis-title" x="'+(W-R)+'" y="'+(H-6)+'" text-anchor="end">'+E(s.label)+'（'+E(s.unit)+'）</text></svg>';
  return out;
 }
 function setStandardValues(){const k=$('s-key').value;gridKey=k;customValues=false;$('s-values').value=S.defaultValues(k,p).join(', ');}
 function drawCurve(){
  try{
   const k=$('s-key').value,s=S.byKey[k];
   $('s-values-label').textContent='試す値（'+s.unit+'）';
   const tokens=$('s-values').value.replace(/、|，/g,',').split(',').map(x=>x.trim());
   if(tokens.length<2||tokens.length>25||tokens.some(x=>x===''))throw new Error('試す値は、カンマ区切りで2〜25個を入力してください。');
   let xs=tokens.map(Number);if(xs.some(x=>!Number.isFinite(x)))throw new Error('試す値は数値のみを入力してください。');
   xs=[...new Set([...xs,Number((p[k]/s.scale).toFixed(7))])].sort((a,b)=>a-b);
   curves=S.curve(p,k,xs);$('s-error').style.display='none';
   $('s-chart').innerHTML=chartCurve(k,curves);
   let explain=s.note;
   if(k==='years')explain+=' 現在は社宅 '+p.corp_years+'年を固定。保有年数を延ばしても社宅は自動延長しません。税務上、保有6年・11年で扱いが切り替わる仮定です。';
   if(k==='corp_years')explain+=' 保有 '+p.years+'年を超える設定は同じ結果になります。';
   if(k==='mortgage_rate'&&p.step_year>0)explain+=' 現在は'+p.step_year+'年後に '+num(p.step_rate*100)+'%へ変更する設定です。';
   $('s-explanation').textContent=explain;
   $('s-table').innerHTML=table([E(s.label)+'<br>('+E(s.unit)+')','vs 通常賃貸<br>g*','vs 借上社宅<br>g*','Δg*（社宅）<br>vs 現在値','社宅との分岐売値','社宅の実効年数'],curves.map(q=>{
    if(q.error)return row([num(q.value),'<span title="'+E(q.error)+'">対象外</span>','—','—',E(q.error),'—'],'invalid-row');
    const cg=g(q.corp),bg=g(base.corp),diff=cg===null||bg===null?null:cg-bg;
    return row([num(q.value)+baselineMark(k,q.p[k]),'<span class="rent-text">'+gr(q.normal)+'</span>','<strong class="corp-text">'+gr(q.corp)+'</strong>',diff===null?'—':pp(diff),sp(q.corp),Math.min(q.p.years,q.p.corp_years)+'年'],same(q.p[k],p[k])?'baseline-row':'');
   }),'sensitivity-table');
   const valid=curves.filter(q=>!q.error&&g(q.corp)!==null),ng=g(base.normal),cg=g(base.corp);
   $('s-reading').textContent=valid.length?'試した '+s.label+' の範囲で、社宅との分岐率は '+rate(Math.min(...valid.map(q=>q.corp.growth)))+' 〜 '+rate(Math.max(...valid.map(q=>q.corp.growth)))+' / 年。現在値は通常賃貸 '+(ng===null?'—':rate(ng))+'、借上社宅 '+(cg===null?'—':rate(cg))+'。':'有効な試算点がありません。';
  }catch(e){$('s-error').textContent=e.message;$('s-error').style.display='block';$('s-chart').innerHTML='';$('s-table').innerHTML='';$('s-reading').textContent='';curves=[];}
 }
 function drawHeat(){
  const preset=$('h-preset').value,mode=$('h-mode').value;hg=S.grid(p,preset);
  const value=q=>q.error?null:mode==='gap'?(g(q.corp)===null||g(q.normal)===null?null:g(q.corp)-g(q.normal)):g(q[mode]);
  const vals=hg.cells.flat().map(value).filter(v=>v!==null),min=Math.min(...vals),max=Math.max(...vals),range=Math.max(.00001,max-min);
  const xs=S.byKey[hg.xkey],ys=S.byKey[hg.ykey];
  const heading=['<span>'+E(ys.label)+' ↓<br>'+E(xs.label)+' →</span>',...hg.xs.map(x=>num(x)+'<br><small>'+E(xs.unit)+'</small>')];
  const rows=hg.cells.map((r,i)=>'<tr><td class="row-head">'+num(hg.ys[i])+' '+E(ys.unit)+'</td>'+r.map((q,j)=>{
   const v=value(q),isCurrent=same(q.p[hg.xkey],p[hg.xkey])&&same(q.p[hg.ykey],p[hg.ykey]);
   const alpha=v===null?0:.025+.23*(v-min)/range;
   return '<td style="background:rgba(121,86,170,'+alpha.toFixed(4)+')"><button type="button" class="heat-button" data-hi="'+i+'" data-hj="'+j+'" aria-current="'+isCurrent+'"'+(q.error?' disabled':'')+' title="'+E(q.error||ys.label+' '+label(hg.ykey,q.p[hg.ykey])+' / '+xs.label+' '+label(hg.xkey,q.p[hg.xkey]))+'">'+(q.error?'条件範囲外':v===null?'分岐なし':mode==='gap'?pp(v):rate(v))+(isCurrent?'<small>現在の設定</small>':'')+'</button></td>';
  }).join('')+'</tr>');
  $('h-map').innerHTML=table(heading,rows,'heat-map');
  const modeText=mode==='gap'?'社宅 g* − 通常賃貸 g*（pp）':('購入 vs '+modeNames[mode]+' の g*（年率）');
  let note='表示：'+modeText+'。その他の入力は現在値で固定。';
  if(preset==='duration')note+=' 有効な社宅年数は「居住年数と社宅年数の短い方」。税務上の保有期間判定も各セルで再計算します。';
  if(preset==='price_rent')note+=' 所有費用は年 '+m(p.owner_cost)+' のまま固定。価格に応じた頭金・借入・取引費用は再計算します。';
  if(preset==='rates'&&p.step_year>0)note+=' 変更後金利は '+num(p.step_rate*100)+'%（'+p.step_year+'年後）のまま固定し、当初金利を動かします。';
  $('h-note').textContent=note;
  $('h-selection').textContent='セルを選ぶと、通常賃貸・社宅の両方の分岐率と売却価格を確認できます。';
 }
 function selectCell(i,j){
  const q=hg.cells[i]?.[j];if(!q||q.error)return;
  const patch={[hg.xkey]:q.p[hg.xkey],[hg.ykey]:q.p[hg.ykey]};
  $('h-selection').innerHTML='<strong>'+E(S.byKey[hg.xkey].label)+' '+E(label(hg.xkey,patch[hg.xkey]))+' × '+E(S.byKey[hg.ykey].label)+' '+E(label(hg.ykey,patch[hg.ykey]))+'</strong>'+table(['比較先','必要上昇率','分岐売値'],[row(['通常賃貸',gr(q.normal),sp(q.normal)]),row(['借上社宅',gr(q.corp),sp(q.corp)])])+'<div class="buttons no-print"><button type="button" id="h-apply">この2条件を現在の設定に反映</button></div>';
  $('h-apply').addEventListener('click',()=>{U.update(patch);$('h-selection').textContent='選択した2条件を反映しました。パラメータ一覧・感応度・シミュレーターは同じ設定です。';});
 }
 function drawTornado(){
  const mode=$('t-mode').value,bg=g(base[mode]);
  if(bg===null){$('t-chart').textContent='現在の設定に有効な分岐率がありません。';$('t-table').textContent='';return;}
  trows=S.stresses(p).map(t=>({...t,dl:t.lo.error||g(t.lo[mode])===null?null:g(t.lo[mode])-bg,dh:t.hi.error||g(t.hi[mode])===null?null:g(t.hi[mode])-bg}));
  trows.sort((a,b)=>Math.max(Math.abs(b.dl||0),Math.abs(b.dh||0))-Math.max(Math.abs(a.dl||0),Math.abs(a.dh||0)));
  const vals=trows.flatMap(t=>[t.dl,t.dh]).filter(v=>v!==null).map(v=>v*100),lim=Math.max(.2,...vals.map(Math.abs))*1.18;
  const W=990,L=280,R=68,T=37,rowH=57,H=T+trows.length*rowH+65,w=W-L-R;
  const X=x=>L+(x+lim)/(2*lim)*w;
  let out='<div class="tornado-legend"><span>小さい試算値</span><span class="high">大きい試算値</span></div><svg class="chart" viewBox="0 0 '+W+' '+H+'" role="img" aria-label="'+modeNames[mode]+'との分岐率の単独ストレス"><title>現在値からの分岐率の変化</title>';
  for(let i=0;i<=4;i++){const x=-lim+2*lim*i/4;out+='<line class="grid '+(i===2?'zero':'')+'" x1="'+X(x)+'" x2="'+X(x)+'" y1="'+T+'" y2="'+(H-58)+'"/><text class="tick" x="'+X(x)+'" y="'+(H-34)+'" text-anchor="middle">'+(x>0?'+':'')+n(x,1)+'</text>';}
  trows.forEach((t,i)=>{
   const y=T+i*rowH+20,lo=t.dl===null?null:t.dl*100,hi=t.dh===null?null:t.dh*100;
   out+='<text class="tornado-text" x="12" y="'+(y-4)+'">'+E(S.byKey[t.key].label)+'</text><text class="tornado-sublabel" x="12" y="'+(y+14)+'">'+E(label(t.key,t.lo.p[t.key]))+' / '+E(label(t.key,t.hi.p[t.key]))+'</text>';
   if(lo!==null&&hi!==null)out+='<line class="tornado-range" x1="'+X(lo)+'" x2="'+X(hi)+'" y1="'+y+'" y2="'+y+'"/>';
   if(lo!==null)out+='<circle class="tornado-low" cx="'+X(lo)+'" cy="'+y+'" r="5"><title>'+E(t.label)+': '+pp(t.dl)+'</title></circle>';
   if(hi!==null)out+='<circle class="tornado-high" cx="'+X(hi)+'" cy="'+y+'" r="5.5"><title>'+E(t.label)+': '+pp(t.dh)+'</title></circle>';
  });
  out+='<text class="axis-title" x="'+L+'" y="18">Δg*（pp）｜現在 '+rate(bg)+' / 年 をゼロとして比較</text><text class="axis-title" x="'+L+'" y="'+(H-7)+'">← 購入のハードルが下がる</text><text class="axis-title" x="'+(W-R)+'" y="'+(H-7)+'" text-anchor="end">購入のハードルが上がる →</text></svg>';
  $('t-chart').innerHTML=out;
  $('t-table').innerHTML=table(['変更パラメータ','小さい試算値','その g*','Δg*','大きい試算値','その g*','Δg*'],trows.map(t=>row([E(S.byKey[t.key].label),E(label(t.key,t.lo.p[t.key])),t.lo.error?'対象外':gr(t.lo[mode]),t.dl===null?'—':pp(t.dl),E(label(t.key,t.hi.p[t.key])),t.hi.error?'対象外':gr(t.hi[mode]),t.dh===null?'—':pp(t.dh)])),'sensitivity-table');
 }
 function update(newP){
  p={...newP};base=S.evaluate(p);if(base.error){markDirty(base.error);return;}
  dirty=false;renderVersion++;kpis();syncParams();states();
  if(!customValues||gridKey!==$('s-key').value)setStandardValues();
  drawCurve();drawHeat();drawTornado();
 }
 function markDirty(message){dirty=true;$('dash-status').className='scenario-status dirty';$('dash-status').textContent=message||'入力変更あり。下の入力フォームで「再計算」を押してください。以下の感応度は直前の有効な設定です。';}
 function ensureChartFresh(){if(dirty)return checkFresh();return true;}
 function parameterCSV(){
  if(!checkFresh())return;
  const rows=[['分類','パラメータ','キー','初期値','現在値','単位','根拠','固定・連動の扱い']];
  for(const s of S.meta)rows.push([s.group==='dynamic'?'動的':'静的',s.label,s.key,typeof U.defaults[s.key]==='number'?U.defaults[s.key]/s.scale:U.defaults[s.key],typeof p[s.key]==='number'?p[s.key]/s.scale:p[s.key],s.unit,s.source,s.note]);
  emitDownload(csv(rows),'housing_parameters_v2.csv','text/csv;charset=utf-8');showMsg('パラメータCSVを作成しました。給与・家賃等の個人情報を含みます。');
 }
 function sensitivityCSV(){
  if(!checkFresh())return;
  const keys=S.meta.map(s=>s.key),header=['種類','変更項目','試す値','表示単位','状態','通常賃貸_gstar_pct','社宅_gstar_pct','通常賃貸_分岐売値_円','社宅_分岐売値_円','社宅_delta_gstar_pp',...keys.map(k=>'p_'+k)];
  const rows=[header];
  const add=(kind,k,v,unit,q)=>rows.push([kind,k,v,unit,q.error||q.corp.status,g(q.normal)===null?'':g(q.normal)*100,g(q.corp)===null?'':g(q.corp)*100,q.normal?.price??'',q.corp?.price??'',g(q.corp)===null||g(base.corp)===null?'':(g(q.corp)-g(base.corp))*100,...keys.map(key=>q.p[key])]);
  add('現在値','baseline','','',base);
  for(const k of curveKeys)for(const q of S.curve(p,k,S.defaultValues(k,p)))add('1変数_標準幅',k,q.value,S.byKey[k].unit,q);
  for(const q of curves)add('表示中_1変数',$('s-key').value,q.value,S.byKey[$('s-key').value].unit,q);
  for(const preset of ['rates','price_rent','duration']){
   const grid=S.grid(p,preset);for(const q of grid.cells.flat())add('2変数_'+preset,grid.xkey+' / '+grid.ykey,q.x+' / '+q.y,S.byKey[grid.xkey].unit+' / '+S.byKey[grid.ykey].unit,q);
  }
  emitDownload(csv(rows),'housing_sensitivity_v2.csv','text/csv;charset=utf-8');showMsg('全パラメータの標準感応度・表示中の試算・3種類の2変数表を出力しました。p_列の金額は円、利率は小数です。');
 }
 function setup(){
  $('s-key').innerHTML=curveKeys.map(k=>'<option value="'+k+'">'+E(S.byKey[k].label)+'</option>').join('');
  renderParamTables();
  $('s-key').addEventListener('change',()=>{if(!ensureChartFresh())return;setStandardValues();drawCurve();});
  $('s-values').addEventListener('input',()=>{customValues=true;});
  $('s-values').addEventListener('keydown',e=>{if(e.key==='Enter'&&ensureChartFresh())drawCurve();});
  $('s-redraw').addEventListener('click',()=>{if(ensureChartFresh())drawCurve();});
  $('s-default-grid').addEventListener('click',()=>{if(!ensureChartFresh())return;setStandardValues();drawCurve();});
  for(const id of ['h-preset','h-mode'])$(id).addEventListener('change',()=>{if(ensureChartFresh())drawHeat();});
  $('t-mode').addEventListener('change',()=>{if(ensureChartFresh())drawTornado();});
  $('h-map').addEventListener('click',e=>{const b=e.target.closest('[data-hi]');if(b&&!dirty)selectCell(Number(b.dataset.hi),Number(b.dataset.hj));});
  document.querySelectorAll('[data-quick]').forEach(b=>b.addEventListener('click',()=>{
   const patches={rate:{mortgage_rate:.02},corp:{corp_years:5},invest:{invest:.05},price:{price:220000000}};
   U.update({...U.defaults,...patches[b.dataset.quick]});
  }));
  $('dash-reset').addEventListener('click',()=>{customValues=false;U.update({...U.defaults});});
  $('parameters').addEventListener('change',e=>{
   const el=e.target.closest('[data-edit]');if(!el)return;
   const key=el.dataset.edit,s=S.byKey[key];let v;
   if(el.type==='checkbox')v=el.checked;
   else if(key==='loan_type')v=el.value;
   else{if(el.value.trim()===''||!Number.isFinite(Number(el.value))){$ ('f-'+key).value='';U.recalculate();return;}v=Number(el.value)*s.scale;}
   U.update({[key]:v});
  });
  $('parameters').addEventListener('keydown',e=>{if(e.key==='Enter'&&e.target.matches('[data-edit]')){e.preventDefault();e.target.blur();}});
  $('parameters').addEventListener('click',e=>{const b=e.target.closest('[data-view]');if(!b)return;if(!ensureChartFresh())return;$('s-key').value=b.dataset.view;setStandardValues();drawCurve();$('sensitivity').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});});
  $('params-csv').addEventListener('click',parameterCSV);$('sensitivity-csv').addEventListener('click',sensitivityCSV);
  $('load-settings').addEventListener('click',()=>$('settings-file').click());
  $('settings-file').addEventListener('change',async e=>{
   try{
    const f=e.target.files[0];if(!f)return;if(f.size>1000000)throw new Error('設定ファイルが大きすぎます。');
    const doc=JSON.parse(await f.text()),params=doc.parameters;if(!params||typeof params!=='object')throw new Error('parametersを含む設定JSONではありません。');
    const q={};for(const s of S.meta){const v=params[s.key];if(v===undefined||typeof v!==typeof U.defaults[s.key])throw new Error(s.label+'の値または型が不正です。');q[s.key]=v;}
    const er=S.validate(q);if(er)throw new Error(er);customValues=false;U.update(q);showMsg('設定を読み込み、すべての比較を再計算しました。');
   }catch(err){showMsg('設定は変更していません：'+err.message);}finally{e.target.value='';}
  });
  document.addEventListener('housing:updated',e=>update(e.detail.parameters));
  document.addEventListener('housing:dirty',()=>markDirty());
  document.addEventListener('housing:invalid',e=>markDirty('入力エラー：'+e.detail.message+'。結果は直前の有効な設定です。'));
  for(const a of document.querySelectorAll('a[href^="#"]'))a.addEventListener('click',()=>{const target=document.getElementById(a.hash.slice(1));if(target){let el=target;while(el){if(el.tagName==='DETAILS')el.open=true;el=el.parentElement;}}});
  if(location.hash){const t=document.getElementById(location.hash.slice(1));if(t){let el=t;while(el){if(el.tagName==='DETAILS')el.open=true;el=el.parentElement;}}}
  update(U.getCurrent());
  window.HousingDashboard={getParameters:()=>({...p}),getEvaluation:()=>base,getCurve:()=>curves,getGrid:()=>hg,getStresses:()=>trows,getVersion:()=>renderVersion};
 }
 setup();
})();
