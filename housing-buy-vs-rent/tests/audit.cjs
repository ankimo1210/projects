// Audit current by default; pass the original directory to reproduce pre-fix defects.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const root = path.resolve(process.argv[2] || path.join(__dirname, '../current'));
const source = fs.readFileSync(path.join(root, 'source/extracted_scripts.js'), 'utf8');
const context = vm.createContext({});
vm.runInContext(source.split('// ===== script block 4 =====')[0] + '\nglobalThis.audit = {M: HousingModel, S: HousingSensitivity, p: BASE_PARAMS};', context);
const {M, S, p} = context.audit;
const checks = [];
function check(name, body) { try { body(); checks.push({name, status:'PASS'}); } catch(e) { checks.push({name, status:'FAIL', detail:e.message}); } }
function near(actual, expected, tol=.01) { assert.ok(Math.abs(actual-expected)<=tol, `${actual} != ${expected} (tolerance ${tol})`); }
const scenarios = [
 ['baseline', {}, .14, 2.46],
 ['mortgage 2%', {mortgage_rate:.02}, .60, 2.93],
 ['corporate housing 5 years', {corp_years:5}, .14, 1.33],
 ['investment 5%', {invest:.05}, .70, 3.28],
 ['purchase 220M', {price:220000000}, -.32, 2.28],
 ['residence 15 / corporate 10', {years:15}, -.21, 1.57]
].map(([name, patch, normal, corp]) => {
 const q={...p,...patch}, e=S.evaluate(q);
 check('snapshot: '+name,()=>{assert.equal(e.error,undefined);near(e.normal.growth*100,normal,.005);near(e.corp.growth*100,corp,.005);});
 check('break-even residual: '+name,()=>{for(const mode of ['rent','corp']){const be=M.breakSale(q,mode);near(M.run({...q,growth:be.growth})['wealth_diff_'+mode],0,.01);}});
 return {name, normal:e.normal.growth*100, corp:e.corp.growth*100};
});
const base=M.run(p,true), tax=M.housingTax(p);
check('closed-form amortization',()=>{
 const B=p.price*p.ltv, r=p.mortgage_rate/12, n=p.years*12;
 const payment=B*r/(1-(1+r)**(-p.mortgage_years*12));
 near(base.balance,B*(1+r)**n-payment*((1+r)**n-1)/r);
 near(base.total_interest,payment*n-(B-base.balance));
});
check('cash-flow difference independent of synthetic budget',()=>{
 const a=1+p.invest/12;
 const fvCosts=base.rows.reduce((total,r)=>total*a+r.rent_spend-r.owner_spend,0);
 const expected=base.sale.net_before_debt-base.balance+(base.initial_rent-base.initial_buy)*a**120+fvCosts;
 near(base.wealth_diff_rent,expected);
});
check('corporate saving independently calculated from high-income brackets',()=>{
 const normalNational=((50000000-1950000-1500000)*.45-4796000)*1.021;
 const corpNational=((41000000-1950000-1500000)*.4-2796000)*1.021;
 const expectedSaving=normalNational-corpNational+9000000*.1;
 near(tax.benefit,expectedSaving);
 near(base.corp_advantage,expectedSaving/12*((1+p.invest/12)**120-1)/(p.invest/12));
});
check('no corporate benefit => identical rent strategies',()=>{const r=M.run({...p,sacrifice:0});near(r.rent_wealth,r.corp_wealth);});
check('corporate duration zero => identical rent strategies',()=>{const r=M.run({...p,corp_years:0});near(r.rent_wealth,r.corp_wealth);});
check('corporate duration beyond residence has no effect',()=>{near(M.run({...p,corp_years:35}).corp_wealth,base.corp_wealth);});
check('zero-rate loan and maturity',()=>{const q={...p,mortgage_rate:0,mortgage_years:5};const r=M.run(q,true);near(r.total_interest,0);near(r.balance,0);near(r.rows[60].principal,0);near(r.rows[59].balance,0);});
check('rate reset payment independent remaining-term formula',()=>{const q={...p,step_year:5,step_rate:.03};const r=M.run(q,true);const b=r.rows[59].balance;const i=.03/12;near(r.rows[60].interest,b*i);near(r.rows[60].principal+r.rows[60].interest,b*i/(1-(1+i)**(-360)));});
check('IO retains principal and validates maturity',()=>{const q={...p,loan_type:'io'};const r=M.run(q);near(r.balance,p.price*p.ltv);near(r.total_interest,p.price*p.ltv*p.mortgage_rate*p.years);assert.ok(S.validate({...q,mortgage_years:5}));});
check('renewals exclude terminal month',()=>{const renewals=base.rows.filter(r=>r.rent_spend>p.rent).map(r=>r.month);assert.equal(JSON.stringify(renewals),JSON.stringify([24,48,72,96]));});
check('extra repair future value',()=>{const q={...p,extra_repair:10000000,repair_year:8};near(M.run(q).wealth_diff_rent-base.wealth_diff_rent,-q.extra_repair*(1+p.invest/12)**24);});
check('forecast growth does not change break-even growth',()=>{near(M.breakSale({...p,growth:.08}).growth,M.breakSale(p).growth,1e-12);});
check('HTML and source snapshots are byte-identical',()=>{assert.ok(fs.readFileSync(path.join(root,'source/full_source.html')).equals(fs.readFileSync(path.join(root,'report/housing_rent_corporate_buy_report_v2.html'))));});
check('audited JavaScript matches every live HTML script block',()=>{
 const html=fs.readFileSync(path.join(root,'report/housing_rent_corporate_buy_report_v2.html'),'utf8');
 const live=[...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)].map(x=>x[1].trim());
 const extracted=source.split(/\/\/ ===== script block \d+ =====/).slice(1).map(x=>x.trim());
 assert.deepEqual(extracted,live);
});
const probes={};
// For a September acquisition, January 1 after 5y4m switches to long-term.
const saleQ={...p,growth:.05,deduction_sale:0};
probes.month61Sale={years:61/12,actual:M.saleTax(saleQ,null,61/12),expectedRate:.3963};
probes.month61Sale.expectedTax=probes.month61Sale.actual.taxable_gain*.3963;
const initialBasis=saleQ.price*(1+saleQ.basis_cost);
const correctedDep=initialBasis*saleQ.building_share*.9*.015*5;
probes.month61Sale.correctedTaxWithRoundedDepreciation=(probes.month61Sale.actual.price*(1-saleQ.sell_cost)-initialBasis+correctedDep)*.3963;
probes.month125Sale={years:125/12,actual:M.saleTax(saleQ,null,125/12),expectedRate:.1421};
probes.month125Sale.expectedTaxAtSameBasis=Math.min(probes.month125Sale.actual.taxable_gain,60000000)*.1421+Math.max(0,probes.month125Sale.actual.taxable_gain-60000000)*.20315;
// Missing API guards are only reported where they differ from the UI validator.
const inactive={...p,salary:30000000,rent:2000000,corp_years:0};
probes.inactiveCorpValidation={error:S.validate(inactive),allFinite:Number.isFinite(M.run(inactive).wealth_diff_rent)};
const endRent={...p,salary:30000000,rent:1000000,rent_growth:.1,years:20,corp_years:1};
probes.afterCorpEndValidation={error:S.validate(endRent),firstYearGross:endRent.salary-endRent.rent*12};
probes.requireWholeModule=(()=>{try{require(path.join(root,'source/extracted_scripts.js'));return null;}catch(e){return e.name+': '+e.message;}})();
probes.fringeSensitivity=[0,600000,1200000].map(fringe=>({fringe,gstar:M.breakSale({...p,fringe}).growth*100,annualBenefit:M.housingTax({...p,fringe}).benefit}));
probes.effectiveAnnualReturn=(1+p.invest/12)**12-1;
const defects=[];
function expectation(name,body){try{body();defects.push({name,status:'PASS'});}catch(e){defects.push({name,status:'FAIL',detail:e.message});}}
expectation('month 61 must remain short-term under September acquisition',()=>near(probes.month61Sale.actual.tax,probes.month61Sale.expectedTax));
expectation('month 125 must qualify for reduced rate under September acquisition',()=>near(probes.month125Sale.actual.tax,probes.month125Sale.expectedTaxAtSameBasis));
expectation('non-business depreciation must round elapsed years',()=>near(probes.month61Sale.actual.depreciation,correctedDep));
expectation('inactive corporate salary must not reject ordinary rent',()=>assert.equal(S.validate(inactive),null));
expectation('rent after corporate housing ends must not invalidate salary',()=>assert.equal(S.validate(endRent),null));

expectation('extracted script can be required without a browser',()=>assert.equal(probes.requireWholeModule,null));
expectation('sale-year boundary and six-month rounding over every monthly row',()=>{
 const q={...p,years:15,growth:.05,deduction_sale:0};
 const rows=M.run(q,true).rows;
 const initial=q.price*(1+q.basis_cost),building=initial*q.building_share;
 for(const row of rows){
  const dep=building*.9*.015*Math.floor((row.month+6)/12);
  const gain=Math.max(0,row.price*(1-q.sell_cost)-initial+dep);
  const expected=row.month<64?gain*.3963:row.month<124?gain*.20315:Math.min(gain,60000000)*.1421+Math.max(0,gain-60000000)*.20315;
  near(row.sale_tax,expected);
 }
});
expectation('active corporate salary below model range remains rejected',()=>assert.ok(S.validate({...inactive,corp_years:1})));
expectation('last active year of increasing rent remains validated',()=>assert.ok(S.validate({...endRent,corp_years:5})));
expectation('falling rent validates the most expensive active year',()=>assert.ok(S.validate({...p,salary:30000000,rent:1500000,rent_growth:-.05,years:20,corp_years:10})));
const output={checks,defects,scenarios,baseline:{normalGstar:M.breakSale(p,'rent'),corpGstar:M.breakSale(p),initialCapital:base.initial_capital,monthlyPayment:M.pmt(p.price*p.ltv,p.mortgage_rate/12,420),balance:base.balance,ownerWealth:base.owner_wealth,rentWealth:base.rent_wealth,corpWealth:base.corp_wealth,annualTaxBenefit:tax.benefit,effectiveMonthlyRent:tax.annual_effective/12},probes};
console.log(JSON.stringify(output,null,2));
if(checks.some(x=>x.status==='FAIL')||defects.some(x=>x.status==='FAIL'))process.exitCode=1;
