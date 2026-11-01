const test = require('node:test');
const assert = require('node:assert/strict');
const R = require('./report.js');

const job = (ranges, overrides={}) => ({id:'MS:1',company:'MS',req:'1',title:'Software Engineer, Vice President',department:'',locations:['New York, NY'],status:'extracted',ranges,...overrides});
const range = (overrides={}) => ({minimum:100000,maximum:150000,period:'year',currency:'USD',region:'New York,NY',pay_type:'base',parse_status:'parsed',evidence:'salary',...overrides});
const state = (overrides={}) => ({companies:['MS','GS','JPM'],mode:'scenario',threshold:20000,nyOnly:true,includeUnspecifiedPay:false,family:'all',rank:'all',query:'',status:'all',...overrides});

test('strict year never silently includes unspecified periods', () => {
  const rows=R.selectRows([job([range(),range({period:'unspecified',minimum:160000})])],state({mode:'year'}));
  assert.equal(rows.length,1); assert.equal(rows[0].assumed,false);
});
test('scenario explicitly marks qualifying unknown amounts and excludes small amounts', () => {
  const rows=R.selectRows([job([range({period:'unspecified'}),range({period:'unspecified',minimum:25,maximum:31})])],state());
  assert.equal(rows.length,1); assert.equal(rows[0].assumed,true);
  assert.equal(rows[0].period,'unspecified');
});
test('NY scope, malformed ranges and unlabelled pay type do not leak into base comparison', () => {
  const rows=R.selectRows([job([range({region:'Chicago,IL'}),range({parse_status:'review'}),range({minimum:200000,maximum:100000}),range({pay_type:'salary_unspecified'})])],state());
  assert.equal(rows.length,0);
});
test('identical amounts within a job are counted once, distinct grade ranges remain', () => {
  const rows=R.selectRows([job([range(),range({region:'Brooklyn,NY'}),range({minimum:160000,maximum:180000})])],state());
  assert.equal(rows.length,2); assert.equal(R.summarize(rows).jobs,1);
});
test('title labels preserve multiple grades and do not equate lead with vice president', () => {
  assert.equal(R.classifyRank('Global Capital Markets – VP/ED'),'複数職位');
  assert.equal(R.classifyRank('Senior Lead Software Engineer'),'Senior / Lead');
  assert.equal(R.classifyRank('Investment Banking Associate'),'Associate');
});
test('senior vice president is its own title and is not merged into vice president', () => {
  assert.equal(R.classifyRank('Senior Vice President, Leveraged Finance Credit Underwriting'),'SVP');
  assert.equal(R.classifyRank('Balance Sheet & Pricing Management Product Manager, SVP'),'SVP');
  assert.equal(R.classifyRank('Vice President / Senior Vice President, Rates'),'複数職位');
  assert.equal(R.classifyRank('Assistant Vice President, Credit'),'AVP');
  assert.equal(R.classifyRank('Vice President, Strats'),'Vice President');
});
test('filters and summaries handle an empty group and median is range midpoint', () => {
  assert.equal(R.selectRows([job([range()])],state({companies:['GS']})).length,0);
  assert.equal(R.summarize([]).median,null);
  const rows=R.selectRows([job([range(),range({minimum:200000,maximum:250000})])],state());
  assert.equal(R.summarize(rows).median,175000);
  assert.deepEqual(R.quantiles([10,20,30,40]),{min:10,q1:17.5,median:25,q3:32.5,max:40});
});
test('CSV export retains assumption, source units and spreadsheet-safe values', () => {
  const text=R.toCSV([{title:'=bad()',period_original:'unspecified',assumption:'annual_candidate'}]);
  assert.ok(text.startsWith('\uFEFF')); assert.ok(text.includes("'=bad()"));
  assert.ok(text.includes('unspecified')); assert.ok(text.includes('annual_candidate'));
});

const classifiedJob=(id,department,subdepartment,occupation)=>job([range()],{id,classification:{
  department:{label:department,basis:'タイトル',evidence:'Equity Trading'},
  subdepartment:{label:subdepartment,basis:'タイトル',evidence:'Equity'},
  occupation:{label:occupation,basis:'タイトル',evidence:'Trader'}
}});
test('business department, subdepartment and occupation filter independently',()=>{
  const jobs=[classifiedJob('1','マーケッツ','株式部','トレーダー'),classifiedJob('2','マーケッツ','債券部','営業・セールス'),classifiedJob('3','投資銀行','M&A','投資銀行バンカー')];
  assert.equal(R.selectRows(jobs,state({businessDepartment:'マーケッツ'})).length,2);
  assert.equal(R.selectRows(jobs,state({businessDepartment:'マーケッツ',businessSubdepartment:'株式部',occupation:'トレーダー'})).length,1);
  assert.equal(R.selectRows(jobs,state({businessDepartment:'投資銀行',occupation:'トレーダー'})).length,0);
  assert.deepEqual(R.taxonomyOptions(jobs,state({businessDepartment:'マーケッツ'})).subdepartments.sort(),['債券部','株式部']);
});
test('classification and evidence are retained in downloadable rows',()=>{
  const rows=R.selectRows([classifiedJob('1','マーケッツ','株式部','トレーダー')],state());
  const record=R.exportRows(rows,state())[0];
  assert.equal(record.business_department,'マーケッツ');assert.equal(record.business_subdepartment,'株式部');assert.equal(record.occupation,'トレーダー');
  assert.equal(record.department_basis,'タイトル');assert.equal(record.occupation_evidence,'Trader');assert.equal(record.period_original,'year');
});
test('taxonomy options respect companies and parents while missing classifications remain searchable',()=>{
  const jobs=[classifiedJob('1','マーケッツ','株式部','トレーダー'),classifiedJob('2','投資銀行','M&A','投資銀行バンカー'),job([range()],{id:'3',company:'GS'})];
  assert.deepEqual(R.taxonomyOptions(jobs,state({companies:['GS']})).departments,['未分類']);
  assert.deepEqual(R.taxonomyOptions(jobs,state({businessDepartment:'マーケッツ',businessSubdepartment:'株式部'})).occupations,['トレーダー']);
  assert.equal(R.selectRows(jobs,state({businessDepartment:'未分類'})).length,1);
  assert.equal(R.selectRows(jobs,state({query:'株式部'})).length,1);
  assert.deepEqual(R.taxonomyOptions(jobs,state({companies:[]})),{departments:[],subdepartments:[],occupations:[]});
});
test('campus postings that put the class year after the title are student candidates', () => {
  for(const title of ['Functions - Risk Management, Full Time Analyst, Buffalo - USA, 2027','Banking - Investment Banking, LATAM Full-Time Analyst - NEW YORK, US 2027','Functions - Finance, Full Time Associate, New York - USA, 2027'])
    assert.equal(R.isStudent({title,public_category:'Training'}),true,title);
  assert.equal(R.isStudent({title:'Full Time Associate Banker Seventh and 37th Branch, New York, NY',public_category:'Associate Bankers'}),false);
  assert.equal(R.isStudent({title:'Merrill Advisor Development Program - Financial Advisor: Long Island East Market',public_category:'Relationship Management'}),false);
});
