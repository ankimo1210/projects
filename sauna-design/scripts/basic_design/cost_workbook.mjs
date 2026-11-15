import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';

// Authoritative inputs are the CPU calculation JSON. All monetary cells use 万円.
const [input,outputDir]=process.argv.slice(2);
const d=JSON.parse(await fs.readFile(input,'utf8'));
await fs.mkdir(outputDir,{recursive:true});
const wb=Workbook.create();
const names=['総額','工事明細','運転費','前提','根拠'];
const sheets=Object.fromEntries(names.map(n=>[n,wb.worksheets.add(n)]));
const dark='#23342F', green='#17704D', blue='#1652A2', pale='#FFF2CC', gray='#E9EDE9';
const cases=['low','base','high'];
const fmt='#,##0.0;(#,##0.0);"–"';
const last=d.items.length+6;
function val(s,range,m){s.getRange(range).values=m;}
function form(s,range,m){s.getRange(range).formulas=m;}
function header(s,r,a,z){s.getRange(`${a}${r}:${z}${r}`).format={fill:dark,font:{bold:true,color:'#FFFFFF'},horizontalAlignment:'center',rowHeight:27};}
function title(s,text,end='M'){
  const r=s.getRange(`A1:${end}120`);r.format.font={name:'Arial',size:10,color:dark};r.format.verticalAlignment='center';
  s.showGridLines=false;val(s,'C2',[[text]]);s.getRange('C2').format.font={size:16,bold:true};
  val(s,'C3',[['2026-11-15 / 金額：万円 / 公開価格のある一部を除き作成者の予算仮定']]);
  s.getRange('C3').format.font={size:10,color:'#65726A'};
  s.getRange('A:A').format.columnWidth=2;s.getRange('B:B').format.columnWidth=2;
  s.getRange(`C4:${end}4`).format.borders={bottom:{style:'thin',color:dark}};
}
function inputStyle(s,range){s.getRange(range).format.font.color=blue;s.getRange(range).format.fill=pale;}
function calcStyle(s,range,cross=false){s.getRange(range).format.font.color=cross?green:'#000000';s.getRange(range).setNumberFormat(fmt);}

// Shared controls; each range bound is a labelled input, not a probabilistic forecast.
const a=sheets['前提'];title(a,'費用条件と資金の前提','I');
val(a,'C6:G6',[['項目','単位','低位','基準','上振れ']]);header(a,6,'C','G');
const assumptions=[
 ['tax_rate','消費税率','率',...cases.map(()=>.1)],
 ['contractor_rate','元請経費率','率',...cases.map(c=>d.config.profiles[c].contractor_rate)],
 ['contingency_rate','予備費率','率',...cases.map(c=>d.config.profiles[c].contingency_rate)],
 ['rent_ex_tax','月額賃料・共益費仮定','税抜万円/月',...cases.map(c=>d.config.profiles[c].rent_ex_tax/10000)],
 ['deposit_months','全額返還保証金','月数',...cases.map(c=>d.config.profiles[c].deposit_months)],
 ['construction_months','工事中の賃料負担','月数',...cases.map(c=>d.config.profiles[c].construction_months)],
 ['key_money_months','礼金','月数',...cases.map(c=>d.config.profiles[c].key_money_months)],
 ['broker_months','仲介手数料','月数',...cases.map(c=>d.config.profiles[c].broker_months)],
 ['guarantee_months','保証会社初回費用','賃料倍率',...cases.map(c=>d.config.profiles[c].guarantee_months)],
 ['visitors_day','来客条件（予測ではない）','人/日',...cases.map(c=>d.config.profiles[c].visitors_day)],
 ['operating_days','営業日','日/月',...cases.map(c=>d.config.profiles[c].operating_days)],
 ['staff_per_shift','現場常駐相当人数','人',...cases.map(c=>d.config.profiles[c].staff_per_shift)],
 ['coverage_hours','清掃等込み対応時間','h/日',...cases.map(c=>d.config.profiles[c].coverage_hours)],
 ['loaded_hourly_pay','雇用側負担込み時給仮定','円/h',...cases.map(c=>d.config.profiles[c].loaded_hourly_pay)],
 ['management_month','店長・管理人件費','万円/月',...cases.map(c=>d.config.profiles[c].management_month/10000)],
 ['power_contract_kw','仮電力契約','kW',...cases.map(c=>d.config.profiles[c].power_contract_kw)],
 ['power_kwh','電力量の感度条件','kWh/月',...cases.map(c=>d.config.profiles[c].power_kwh)],
 ['power_variable_incl_tax','調整等込み仮電気従量単価','税込円/kWh',...cases.map(c=>d.config.profiles[c].power_variable_incl_tax)],
 ['gas_m3','ガス使用量の感度条件','m³/月',...cases.map(c=>d.config.profiles[c].gas_m3)],
 ['gas_unit_incl_tax','ガス単価の感度条件','税込円/m³',...cases.map(c=>d.config.profiles[c].gas_unit_incl_tax)],
 ['laundry_per_guest_incl_tax','リネン・消耗品単価','税込円/人',...cases.map(c=>d.config.profiles[c].laundry_per_guest_incl_tax)],
 ['misc_month','保守・検査等','万円/月',...cases.map(c=>d.config.common['misc_month_'+c]/10000)],
 ['events','定期イベント開催数','回/月',4,8,12],
 ['event_unit','イベント出演・応援枠','万円/回',3,4,6],
 ['water_other_m3_day','便所・清掃等追加水量','m³/日',3,3,3],
 ['electric_basic','電気基本料金・税込公表値','円/kW月',2651.5,2651.5,2651.5],
];
const ar={};assumptions.forEach((r,i)=>{ar[r[0]]=i+7;val(a,`C${i+7}:G${i+7}`,[r.slice(1)]);});
inputStyle(a,`E7:G${assumptions.length+6}`);a.getRange(`E7:G${assumptions.length+6}`).setNumberFormat('#,##0.0');a.getRange('E7:G9').setNumberFormat('0.0%');
val(a,'C36',[[d.config.bounds_note]]);val(a,'C38',[['黄色・青字が編集入力。1億/1.5億/2億は同じ費用に対する予算枠。']]);
val(a,'C40',[['賃料/保証金/工期/調達価格は仮定。全額返還を仮定し償却なし。事業用家賃は消費税加算。']]);
val(a,'C42',[['上下水道は23区一般用50mm、1000m³/月まで。口径変更・範囲超過時は再計算が必要。']]);
val(a,'C45:F48',[
 ['2億円へ寄せる目標例（未交渉）',null,null,'目標入力'],
 ['直接工事の減額（重複なし）','万円',null,1200],
 ['月額家賃・共益費','税抜万円/月',null,120],
 ['全額返還保証金','月数',null,6]
]);inputStyle(a,'F46:F48');
a.getRange('C:C').format.columnWidth=37;a.getRange('D:D').format.columnWidth=19;a.getRange('E:G').format.columnWidth=15;

// Work-scope item build. Prices and quantities are visible beside their arithmetic.
const t=sheets['工事明細'];title(t,'数量と単価からの詳細内訳','R');
val(t,'C5',[['材料・機器と施工範囲を分離。元請経費/予備費/物件費は総額シートで加算。']]);
const heads=['ID','区分','工種','項目','数量','単位','低単価','基準単価','高単価','低金額','基準金額','高金額','税率','数量根拠','根拠ID','含む範囲・限界'];
val(t,'C6:R6',[heads]);header(t,6,'C','R');
const stageNames={direct:'direct',soft:'soft',startup:'startup',startup_labor:'startup_labor'};
val(t,`C7:R${last}`,d.items.map(r=>[r.id,stageNames[r.stage],r.category,r.item,r.quantity,r.unit,r.low/10000,r.base/10000,r.high/10000,null,null,null,r.tax_rate,r.quantity_basis,r.source_ids,r.scope_and_limit]));
for(let i=7;i<=last;i++)form(t,`L${i}:N${i}`,[['I','J','K'].map(c=>`=IF(OR(G${i}="",${c}${i}=""),NA(),G${i}*${c}${i})`)]);
inputStyle(t,`G7:G${last}`);inputStyle(t,`I7:K${last}`);t.getRange(`G7:N${last}`).setNumberFormat(fmt);t.getRange(`O7:O${last}`).setNumberFormat('0%');
calcStyle(t,`L7:N${last}`);t.getRange(`I7:K${last}`).setNumberFormat('#,##0.00');t.freezePanes.freezeRows(6);t.freezePanes.freezeColumns(6);
for(const [c,w] of Object.entries({C:9,D:16,E:24,F:43,G:12,H:9,I:13,J:13,K:13,L:14,M:14,N:14,O:9,P:63,Q:19,R:100}))t.getRange(`${c}:${c}`).format.columnWidth=w;
t.getRange(`C7:R${last}`).format.rowHeight=40;t.getRange(`P7:P${last}`).format.wrapText=true;t.getRange(`R7:R${last}`).format.wrapText=true;

// Operating cost build with transparent quantity multipliers, tax-inclusive cash.
const op=sheets['運転費'];title(op,'月次運転費と資金バッファ','P');
val(op,'C5',[['売上を相殺しない資金バッファ。返済/利益への税/売上連動の決済費は別。']]);
val(op,'C6:P6',[['項目','単位','低数量','低単価','低月額','基準数量','基準単価','基準月額','高数量','高単価','高月額','数量・料金の意味','根拠','補足']]);header(op,6,'C','P');
const ref=(c,key)=>`'前提'!${c}${ar[key]}`;
const opKeys=['rent','staff','manager','electric_basic','electric_variable','gas','water','laundry','misc','events'];
const opLabels=d.cases.base.operation.rows;
for(let n=0;n<10;n++){
 const row=n+7;val(op,`C${row}:D${row}`,[[opLabels[n].item,n===0?'税抜万円/月':opLabels[n].unit]]);
 const rateUnits=['倍率（消費税込み）','円/有給h','万円/人月','税込円/kW月','税込円/kWh','税込円/m³','逓増料金・1000m³月超は再設定','税込円/来客','万円/月','万円/開催'];
 val(op,`N${row}:P${row}`,[[opLabels[n].basis,'A00 / C08-10','単価の単位：'+rateUnits[n]]]);
 for(let c=0;c<3;c++){
  const ac=['E','F','G'][c],qc=['E','H','K'][c],pc=['F','I','L'][c],oc=['G','J','M'][c];
  let q,p,amount;
  if(n===0){q=ref(ac,'rent_ex_tax');p=`1+${ref(ac,'tax_rate')}`;amount=`${qc}${row}*${pc}${row}`;}
  if(n===1){q=`${ref(ac,'staff_per_shift')}*${ref(ac,'coverage_hours')}*${ref(ac,'operating_days')}`;p=ref(ac,'loaded_hourly_pay');amount=`${qc}${row}*${pc}${row}/10000`;}
  if(n===2){q='1';p=ref(ac,'management_month');amount=`${qc}${row}*${pc}${row}`;}
  if(n===3){q=ref(ac,'power_contract_kw');p=ref(ac,'electric_basic');amount=`${qc}${row}*${pc}${row}/10000`;}
  if(n===4){q=ref(ac,'power_kwh');p=ref(ac,'power_variable_incl_tax');amount=`${qc}${row}*${pc}${row}/10000`;}
  if(n===5){q=ref(ac,'gas_m3');p=ref(ac,'gas_unit_incl_tax');amount=`${qc}${row}*${pc}${row}/10000`;}
  if(n===6){
   q=`(11.2384+0.044*${ref(ac,'visitors_day')}+${ref(ac,'water_other_m3_day')})*${ref(ac,'operating_days')}`;
   const x=`${qc}${row}`;
   const water=`20720+${x}*372+560+MAX(MIN(${x}-8,12),0)*110+MAX(MIN(${x}-20,10),0)*140+MAX(MIN(${x}-30,20),0)*170+MAX(MIN(${x}-50,50),0)*200+MAX(MIN(${x}-100,100),0)*230+MAX(MIN(${x}-200,300),0)*270+MAX(MIN(${x}-500,500),0)*310`;
   p=null;amount=`IF(${x}>1000,NA(),(${water})*1.1/10000)`;
  }
  if(n===7){q=`${ref(ac,'visitors_day')}*${ref(ac,'operating_days')}`;p=ref(ac,'laundry_per_guest_incl_tax');amount=`${qc}${row}*${pc}${row}/10000`;}
  if(n===8){q='1';p=ref(ac,'misc_month');amount=`${qc}${row}*${pc}${row}`;}
  if(n===9){q=ref(ac,'events');p=ref(ac,'event_unit');amount=`${qc}${row}*${pc}${row}`;}
  form(op,`${qc}${row}`,[[`=${q}`]]);if(p)form(op,`${pc}${row}`,[[`=${p}`]]);else val(op,`${pc}${row}`,[['逓増料金']]);form(op,`${oc}${row}`,[[`=${amount}`]]);
 }
}
val(op,'C18',[['月額現金支出']]);for(const c of ['G','J','M'])form(op,`${c}18`,[[`=SUM(${c}7:${c}16)`]]);
val(op,'C20',[['3か月分バッファ']]);val(op,'C21',[['6か月分バッファ']]);for(const c of ['G','J','M']){form(op,`${c}20`,[[`=${c}18*3`]]);form(op,`${c}21`,[[`=${c}18*6`]]);}
op.getRange('C:C').format.columnWidth=35;op.getRange('D:D').format.columnWidth=21;op.getRange('E:M').format.columnWidth=14;op.getRange('N:N').format.columnWidth=105;op.getRange('O:P').format.columnWidth=26;
calcStyle(op,'E7:M21',true);op.getRange('C7:P21').format.rowHeight=26;
val(op,'C24',[['電力量18/23/32MWhは平均負荷条件。46.8kWの3ヒーターを営業時間中ずっと100%で計算しない。']]);
val(op,'C26',[['基準23MWh/月はヒーター約50%・冷却・ポンプ・換気・除湿等を含む予算仮定。実機/季節で要再計算。']]);
val(op,'C28',[['ガス1400/1800/2400m³と単価150/170/210円は公表契約ではなく感度仮定。HP給湯は別方式。']]);
val(op,'C30',[['人件費は有給時間と雇用側負担込みの仮定。イベントは外部出演等を月4/8/12回追加。']]);

const s=sheets['総額'];title(s,'サウナ計画　開業に必要な総資金','J');
val(s,'C5',[['280㎡・男性専用40人・サウナ3室・水風呂2槽・炭酸泉1槽 / 賃貸案']]);
val(s,'C7:F7',[['資金の内訳','条件良好・低位','基準予算','上振れ']]);header(s,7,'C','F');
const labels={8:'直接工事・機器・家具（税抜）',9:'元請経費',10:'予備費',11:'工事・機器・家具計（税抜）',12:'上記消費税',13:'工事・機器・家具計（税込）',15:'設計・調査・申請（税込枠）',16:'開業備品・広報等（税込）',17:'開業前人件費（消費税なし）',19:'工事中の賃料（税込）',20:'礼金（税込）',21:'仲介手数料（税込）',22:'保証会社初回（非課税仮定）',23:'物件費（返還保証金除く）',25:'開業支出・返還保証金を除く',26:'返還保証金（仮・全額返還）',27:'開業までの現金支出',29:'月次運転費',30:'運転資金3か月分',31:'総必要資金（3か月込み）',32:'運転資金6か月分',33:'総必要資金（6か月込み）',36:'1億円枠との差（正数は余裕）',37:'1.5億円枠との差',38:'2億円枠との差'};
for(const [r,label] of Object.entries(labels))val(s,`C${r}`,[[label]]);
for(let i=0;i<3;i++){
 const c=['D','E','F'][i],ac=['E','F','G'][i],dc=['L','M','N'][i],oc=['G','J','M'][i];
 const sumStage=(stage)=>`SUMPRODUCT(('工事明細'!$D$7:$D$${last}="${stage}")*'工事明細'!$${dc}$7:$${dc}$${last}*(1+'工事明細'!$O$7:$O$${last}))`;
 const formulas={
  8:`SUMIFS('工事明細'!${dc}7:${dc}${last},'工事明細'!$D$7:$D$${last},"direct")`,
  9:`${c}8*${ref(ac,'contractor_rate')}`,10:`SUM(${c}8:${c}9)*${ref(ac,'contingency_rate')}`,
  11:`SUM(${c}8:${c}10)`,12:`${c}11*${ref(ac,'tax_rate')}`,13:`SUM(${c}11:${c}12)`,
  15:sumStage('soft'),16:sumStage('startup'),17:sumStage('startup_labor'),
  19:`${ref(ac,'rent_ex_tax')}*${ref(ac,'construction_months')}*(1+${ref(ac,'tax_rate')})`,
  20:`${ref(ac,'rent_ex_tax')}*${ref(ac,'key_money_months')}*(1+${ref(ac,'tax_rate')})`,
  21:`${ref(ac,'rent_ex_tax')}*${ref(ac,'broker_months')}*(1+${ref(ac,'tax_rate')})`,
  22:`${ref(ac,'rent_ex_tax')}*${ref(ac,'guarantee_months')}`,23:`SUM(${c}19:${c}22)`,
  25:`SUM(${c}13,${c}15:${c}17,${c}23)`,26:`${ref(ac,'rent_ex_tax')}*${ref(ac,'deposit_months')}`,
  27:`SUM(${c}25:${c}26)`,29:`'運転費'!${oc}18`,30:`'運転費'!${oc}20`,31:`SUM(${c}27,${c}30)`,32:`'運転費'!${oc}21`,33:`SUM(${c}27,${c}32)`,
  36:`10000-${c}31`,37:`15000-${c}31`,38:`20000-${c}31`};
 for(const [r,f]of Object.entries(formulas))form(s,`${c}${r}`,[[`=${f}`]]);
}
s.getRange('C:C').format.columnWidth=45;s.getRange('D:F').format.columnWidth=21;s.getRange('C7:F38').format.rowHeight=25;s.getRange('D8:F38').setNumberFormat(fmt);
for(const row of [13,25,27,31,33]){s.getRange(`C${row}:F${row}`).format.fill=gray;s.getRange(`C${row}:F${row}`).format.font.bold=true;}
s.getRange('D36:F38').conditionalFormats.add('cellIs',{operator:'lessThan',formula:0,format:{font:{color:'#AA2D24',bold:true},fill:'#FDECE8'}});
val(s,'C41',[['2億円：現計画の基準予算では資金不足。既存設備再利用・調達条件等の改善が必要。']]);
val(s,'C43',[['1億円：今の規模・設備・体験を保つ新設計画の資金枠としては厳しい。']]);
val(s,'C45',[['低位は良好な物件・安い調達が揃う条件値。上振れは絶対上限ではない。土地建物購入は未算入。']]);
val(s,'C47',[['深槽の床下1.31m、屋外機置場・排熱、受電余力が前提。許可なしでは予備費を増やしても成立しない。']]);
val(s,'C49',[['①〜⑤資料作成済み / ⑥費用試算 / ⑦物件条件・最終3D統合は未着手 / GPU作業保留']]);
val(s,'C52:E52',[['2億円に近づける目標例（未交渉）',null,'目標額']]);header(s,52,'C','E');
for(const [r,label]of Object.entries({54:'調整後の直接工事',55:'調整後の家賃・税抜万円/月',56:'保証金月数',57:'調整後の月次運転費',58:'調整後の税込工事費',59:'調整後の物件費（保証金除く）',60:'調整後の返還保証金',61:'調整後の総資金・運転3か月込み',62:'2億円との差（正数は余裕）'}))val(s,`C${r}`,[[label]]);
const targetForms={54:"E8-'前提'!F46",55:"'前提'!F47",56:"'前提'!F48",57:"E29-('前提'!F10-E55)*(1+'前提'!F7)",58:"E54*(1+'前提'!F8)*(1+'前提'!F9)*(1+'前提'!F7)",59:"E55*('前提'!F12+'前提'!F13+'前提'!F14)*(1+'前提'!F7)+E55*'前提'!F15",60:'E55*E56',61:'SUM(E58:E60,E15:E17,E57*3)',62:'20000-E61'};
for(const [r,f]of Object.entries(targetForms))form(s,`E${r}`,[[`=${f}`]]);
s.getRange('E54:E62').setNumberFormat(fmt);s.getRange('C61:E61').format.fill=gray;
val(s,'C64',[['直接工事1200万減＝既存ピット200＋他のMEP再利用500＋別工種の調達整理500万円。']]);
val(s,'C66',[['予備費15%と運転3か月を維持。成立する物件・見積がないため予算内確定ではない。']]);

const src=sheets['根拠'];title(src,'数量・公開価格・未見積範囲','H');
val(src,'C6:G6',[['ID','資料','確からしさ','根拠・限界','URL']]);header(src,6,'C','G');
val(src,`C7:G${d.sources.length+6}`,d.sources.map(r=>[r.id,r.title,r.confidence,r.basis,r.url]));
src.getRange('C:C').format.columnWidth=9;src.getRange('D:D').format.columnWidth=42;src.getRange('E:E').format.columnWidth=32;src.getRange('F:F').format.columnWidth=110;src.getRange('G:G').format.columnWidth=110;
src.getRange(`C7:G${d.sources.length+6}`).format.rowHeight=48;src.getRange(`D7:F${d.sources.length+6}`).format.wrapText=true;
const qr=25;val(src,`C${qr}:E${qr}`,[['数量','値','意味']]);header(src,qr,'C','E');
val(src,`C${qr+1}:E${qr+9}`,Object.entries(d.quantities).map(([k,v])=>[k,v,k==='wet_tile_order'?'10%ロス＋83ケース切上げ。㎡/ケースはカタログ参考':'①〜⑤の内法/槽形状又は仮数量']));
val(src,'C37',[['金額未算入・ゼロ円という意味ではない']]);
d.config.unpriced_exclusions.forEach((v,i)=>val(src,`C${39+i*2}`,[[v]]));
src.freezePanes.freezeRows(6);

wb.recalculate();
// Independent Python controls and an input change verify arithmetic, not just formula strings.
const check={};
const targetValue=s.getRange('E61').values[0][0];if(Math.abs(targetValue-d.target_to_200m.summary.funding_3m/10000)>.001)throw Error('Target budget mismatch');
check.target_man=targetValue;
for(let i=0;i<3;i++){
 const c=['D','E','F'][i],caseName=cases[i];
 const value=s.getRange(`${c}31`).values[0][0];const expected=d.cases[caseName].summary.funding_3m/10000;
 if(typeof value!=='number'||Math.abs(value-expected)>.001)throw Error(`Funding mismatch ${caseName}: ${value} vs ${expected}`);
 check[caseName]={actual_man:value,expected_man:expected};
}
const before=s.getRange('E31').values[0][0];const rentCell=a.getRange(`F${ar.rent_ex_tax}`);const oldRent=rentCell.values[0][0];rentCell.values=[[oldRent+10]];wb.recalculate();
const after=s.getRange('E31').values[0][0];if(!(after>before))throw Error('Rent edit did not recalculate');
rentCell.values=[[oldRent]];wb.recalculate();if(Math.abs(s.getRange('E31').values[0][0]-before)>.001)throw Error('Rent restore failed');
check.rent_change={before,after,restored:s.getRange('E31').values[0][0]};
const qty=t.getRange('G7');const originalQty=qty.values[0][0];qty.values=[[null]];wb.recalculate();
const blank=s.getRange('E31').values[0][0];if(typeof blank==='number'&&Number.isFinite(blank))throw Error('Missing quantity was silently zeroed');
qty.values=[[0]];wb.recalculate();const zero=s.getRange('E31').values[0][0];if(!(zero<before))throw Error('Deliberate zero not applied');
qty.values=[[originalQty]];wb.recalculate();if(Math.abs(s.getRange('E31').values[0][0]-before)>.001)throw Error('Quantity restore failed');
check.quantity_change={blank,zero,restored:s.getRange('E31').values[0][0]};
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:30},summary:'formula error scan'});
await fs.writeFile(path.join(outputDir,'verification.json'),JSON.stringify({check,errors:errors.ndjson},null,2));
await fs.writeFile(path.join(outputDir,'summary-inspect.ndjson'),(await wb.inspect({kind:'table',range:'総額!C25:F38',include:'values,formulas',tableMaxRows:14,tableMaxCols:4,maxChars:7000})).ndjson);
for(const [name,range]of [['総額','C2:F38'],['工事明細','C2:N20'],['運転費','C2:M21'],['前提','C2:G32'],['根拠','C2:F17']]){
 const blob=await wb.render({sheetName:name,range,scale:1.5,format:'png'});
 await fs.writeFile(path.join(outputDir,`${name}-preview.png`),new Uint8Array(await blob.arrayBuffer()));
}
await (await SpreadsheetFile.exportXlsx(wb)).save(path.join(outputDir,'sauna_cost_v1.xlsx'));
console.log(JSON.stringify({worksheets:names,items:d.items.length,checks:check,formula_errors:errors.ndjson}));
