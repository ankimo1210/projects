import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';

const [input,out]=process.argv.slice(2);
const d=JSON.parse(await fs.readFile(input,'utf8'));
await fs.mkdir(out,{recursive:true});
const w=Workbook.create();
const a=w.worksheets.add('候補比較'), b=w.worksheets.add('募集条件');
const ink='#263830', green='#17704D', blue='#1652A2', amber='#FFF2CC', gray='#EEF1ED';
const fmt='#,##0.0;(#,##0.0);"–"';
const put=(s,r,v)=>s.getRange(r).values=v;
const f=(s,r,v)=>s.getRange(r).formulas=[[v]];
function base(s,t,end){
 s.showGridLines=false;s.getRange(`A1:${end}70`).format.font={name:'Arial',size:10,color:ink};
 s.getRange(`A1:${end}70`).format.verticalAlignment='center';
 s.getRange('A:B').format.columnWidth=2;put(s,'C2',[[t]]);s.getRange('C2').format.font={size:16,bold:true};
 put(s,'C3',[['2026-11-15 / 公開募集案内・空室未照会 / 金額は万円 / 280㎡計画の参考比較']]);
 s.getRange(`C4:${end}4`).format.borders={bottom:{style:'thin',color:ink}};
}
function head(s,r,c,z){s.getRange(`${c}${r}:${z}${r}`).format={fill:ink,font:{color:'#FFFFFF',bold:true},rowHeight:28,horizontalAlignment:'center'};}
function inp(s,r){s.getRange(r).format.fill=amber;s.getRange(r).format.font.color=blue;}
function calc(s,r,cross=false){s.getRange(r).format.font.color=cross?green:'#000000';s.getRange(r).setNumberFormat(fmt);}
base(a,'東京の候補4件 — 総額2億円の参考比較','K');
put(a,'C5',[['全件：浴場用途・収まり・再利用・追加費は未確認。以下は成立判定ではなく、掲載額＋共通仮定の参考総額。']]);
put(a,'C7:K7',[['候補','固定費/月税込','保証金支払*','純減額なし','700万純減','1200万純減','2億に必要な純減額','追加改修費等','判定']]);head(a,7,'C','K');
for(let i=0;i<4;i++){
 const r=8+i,col=['F','G','H','I'][i];put(a,`C${r}`,[[d.candidates[i].name]]);
 for(const [cell,expr]of [[`D${r}`,`${col}36`],[`E${r}`,`${col}37`],[`F${r}`,`${col}46`],[`G${r}`,`${col}47`],[`H${r}`,`${col}48`],[`I${r}`,`${col}49`]])f(a,cell,`=IF(COUNT(${col}34:${col}35)<>2,"要入力",${expr})`);
 put(a,`J${r}:K${r}`,[['未見積・未算入','資料不足']]);
}
calc(a,'D8:I11');a.getRange('C8:K11').format.rowHeight=30;
a.getRange('F8:H11').conditionalFormats.add('cellIs',{operator:'greaterThan',formula:20000,format:{fill:'#FDECE8',font:{color:'#AA2D24'}}});
put(a,'C13',[['*保証金は税抜家賃本体×掲載月数の仮定。償却を再加算しない。700/1200万は税抜直接工事の純減額で取得済みの再利用効果ではない。']]);
put(a,'C14',[['川口町は共益費未記載を試算外にしている。いづみ礼金の解釈差＋8.8万、川口礼金1→2月なら＋55万。譲渡料等の記載なしは0円確認ではない。']]);
put(a,'C16',[['共通仮定（黄色は比較用の変更欄）']]);
const specs=[
 [18,'⑥の税抜直接工事',d.frozen_basis.direct_yen/10000],
 [19,'元請10%・予備費15%・税込倍率',1.3915],
 [20,'⑥の設計/開業準備等',d.frozen_basis.soft_yen/10000],
 [21,'⑥の家賃以外月次支出',d.frozen_basis.nonrent_monthly_yen/10000],
 [22,'開業前有料賃料（月）',5],[23,'運転資金（月）',3],
 [24,'初回保証料＝税込固定費×月数',1],[25,'仲介＝税込家賃本体×月数',1],
 [26,'賃料等の税率',0.1],[27,'予算上限',20000],[28,'純減額比較A：税抜直接工事',700],[29,'純減額比較B：税抜直接工事',1200]
];
for(const [r,label,val]of specs){put(a,`C${r}`,[[label]]);put(a,`E${r}`,[[val]]);}
calc(a,'E18:E21',true);inp(a,'E22:E29');a.getRange('E18:E29').setNumberFormat(fmt);a.getRange('E19').setNumberFormat('0.0000');a.getRange('E26').setNumberFormat('0.0%');
put(a,'G18',[['基準に予備費15%と元請経費を含む。減額にも同じ倍率を適用。']]);
put(a,'G20',[['3か月分の運転資金は売上で相殺しない。200人/日は需要予測ではない。']]);
put(a,'G22',[['保証料は前回探索式0.7か月から税込固定費1か月へ変更した比較仮定。']]);
put(a,'G24',[['追加構造/基礎・本管/受変電・共用消防・外部設備・面積超過分の内装等は未見積。']]);
put(a,'G26',[['賃料以外の運転費は⑥の基準を維持。多摩地域の実料金・交通/需要差は未反映。']]);
put(a,'G28',[['税抜共益費が月1万円増えると、標準条件の参考総額は9.9万円増加。']]);
put(a,'C32:I32',[['計算過程（万円）',null,null,...d.candidates.map(c=>c.id)]]);head(a,32,'C','I');
const labels={34:'家賃本体：税抜/月',35:'共益費：税抜/月（未記載は試算外）',36:'家賃＋共益費：税込/月',37:'保証金支払全額（仮の月数基準）',38:'礼金（掲載月数の参考計算）',39:'仲介料（比較仮定）',40:'初回保証料（比較仮定）',41:'開業前の有料賃料',42:'月次支出（⑥家賃以外＋固定費）',43:'運転資金',44:'工事等（税込・純減額前）',45:'設計・開業準備等',46:'参考総額：純減額なし',47:'参考総額：純減額比較A',48:'参考総額：純減額比較B',49:'2億円以内に必要な税抜直接純減額',50:'比較Bの予算余白：追加費全体で共有'};
for(const [r,label]of Object.entries(labels))put(a,`C${r}`,[[label]]);
for(let i=0;i<4;i++){
 const col=['F','G','H','I'][i], sr=7+i;
 const expressions={34:`'募集条件'!G${sr}`,35:`'募集条件'!H${sr}`,36:`SUM(${col}34:${col}35)*(1+$E$26)`,37:`${col}34*'募集条件'!J${sr}`,38:`${col}34*(1+$E$26)*'募集条件'!K${sr}`,39:`${col}34*(1+$E$26)*$E$25`,40:`${col}36*$E$24`,41:`${col}36*$E$22`,42:`$E$21+${col}36`,43:`${col}42*$E$23`,44:'$E$18*$E$19',45:'$E$20',46:`SUM(${col}37:${col}41,${col}43:${col}45)`,47:`${col}46-$E$28*$E$19`,48:`${col}46-$E$29*$E$19`,49:`MAX(0,(${col}46-$E$27)/$E$19)`,50:`$E$27-${col}48`};
 for(const [r,expr]of Object.entries(expressions))f(a,`${col}${r}`,`=IF(OR(COUNT('募集条件'!G${sr}:H${sr})<>2,COUNT('募集条件'!J${sr}:K${sr})<>2,COUNT($E$18:$E$29)<>12),"要入力",${expr})`);
}
calc(a,'F34:I50',true);a.getRange('C46:I50').format.fill=gray;a.getRange('C46:I50').format.font.bold=true;
put(a,'C53',[['比較総額に未見積の費用を含めないため、予算内の数値でも成立見込みとは表示しない。']]);
for(const [col,width]of Object.entries({C:49,D:19,E:19,F:21,G:21,H:21,I:23,J:23,K:19}))a.getRange(`${col}:${col}`).format.columnWidth=width;

base(b,'公開募集条件・確認事項','O');
put(b,'C5',[['募集継続・空室は未照会。黄色は参考計算に使う数値。出典の実額や課税/償却基準と同一とは未確定。']]);
put(b,'C6:O6',[['ID','候補名','面積㎡','階','本体家賃税抜','共益費参考税抜','共益費の確認','保証金月数*','礼金参考月数*','礼金の掲載表示','契約','掲載日/次回予定','一次掲載URL']]);head(b,6,'C','O');
for(let i=0;i<4;i++){
 const c=d.candidates[i],r=7+i;
 put(b,`C${r}:O${r}`,[[c.id,c.name,c.area_m2,c.floor,c.rent_ex_yen/10000,c.common_ex_for_reference_yen/10000,c.common_confirmed_none?'共益費なし':c.id==='C03'?'未記載・試算外':'金額掲載あり',c.deposit_months,c.key_months_for_reference,c.key_published,c.lease,[c.listing_date||'日付未記載',c.next_update||'予定未記載'].join(' / '),c.sources[0].url]]);
}
inp(b,'G7:H10');inp(b,'J7:K10');b.getRange('E7:E10').setNumberFormat('0.00');b.getRange('G7:H10').setNumberFormat(fmt);b.getRange('C7:O10').format.rowHeight=28;
put(b,'C13',[['下記は掲載条件と未確認事項。既存設備の再利用額は全件未確認。']]);
for(let i=0;i<4;i++){
 const c=d.candidates[i],r=15+i*10;
 put(b,`C${r}`,[[c.id+' '+c.name]]);b.getRange(`C${r}:K${r}`).format.fill=gray;b.getRange(`C${r}`).format.font.bold=true;
 const notes=[['所在地・アクセス',c.address+' / '+c.access],['掲載状態',c.availability],['用途・制限',c.restrictions],['設備として掲載',c.reuse_listed],['再利用に必要な確認',c.reuse_conditions],['最初に確認',c.first_check],['保証金等',c.deposit_writeoff],['根拠',c.sources.map(s=>s.url).join(' | ')]];
 notes.forEach(([label,text],j)=>{put(b,`C${r+1+j}`,[[label]]);put(b,`E${r+1+j}`,[[text]]);});
}
for(const [col,width]of Object.entries({C:25,D:42,E:15,F:30,G:20,H:20,I:23,J:17,K:17,L:65,M:45,N:39,O:90}))b.getRange(`${col}:${col}`).format.columnWidth=width;

w.recalculate();
const checks={};const assert=(v,t)=>{if(!v)throw Error(t);};
for(let i=0;i<4;i++){
 const col=['F','G','H','I'][i],c=d.candidates[i];
 for(let j=0;j<3;j++)assert(Math.abs(a.getRange(`${col}${46+j}`).values[0][0]-c.cases[j].reference_total_yen/10000)<.001,'Python comparison mismatch '+c.id);
 assert(Math.abs(a.getRange(`${col}49`).values[0][0]-c.required_net_direct_saving_yen/10000)<.001,'Required saving mismatch');
}
const before=a.getRange('G46').values[0][0];put(b,'H8',[[35]]);w.recalculate();
assert(Math.abs(a.getRange('G46').values[0][0]-before-9.9)<.001,'Common fee not propagated');put(b,'H8',[[34]]);
put(b,'G7',[[null]]);w.recalculate();assert(a.getRange('F46').values[0][0]==='要入力','Missing rent became zero');put(b,'G7',[[80]]);
put(a,'E29',[[1000]]);w.recalculate();assert(Math.abs(a.getRange('F48').values[0][0]-(d.candidates[0].cases[0].reference_total_yen/10000-1391.5))<.001,'Saving sensitivity stale');put(a,'E29',[[1200]]);
w.recalculate();
checks.common_fee_delta_man=9.9;checks.missing_input='要入力';checks.results=d.candidates.map((c,i)=>({id:c.id,totals:[46,47,48].map(r=>a.getRange(`${['F','G','H','I'][i]}${r}`).values[0][0])}));
const errors=await w.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:30},summary:'formula error scan'});
await fs.writeFile(path.join(out,'workbook_verification.json'),JSON.stringify({checks,errors:errors.ndjson},null,2));
for(const [name,range]of [['候補比較','C2:K14'],['計算過程','C32:I50'],['募集条件','C15:K23']]){
 const blob=await w.render({sheetName:name==='計算過程'?'候補比較':name,range,scale:1.3,format:'png'});
 await fs.writeFile(path.join(out,name+'-preview.png'),new Uint8Array(await blob.arrayBuffer()));
}
await (await SpreadsheetFile.exportXlsx(w)).save(path.join(out,'sauna_candidates_20261115.xlsx'));
console.log(JSON.stringify({sheets:['候補比較','募集条件'],checks,formula_errors:errors.ndjson}));
