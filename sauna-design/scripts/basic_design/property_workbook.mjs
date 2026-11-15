import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';

const [input,out]=process.argv.slice(2);
const d=JSON.parse(await fs.readFile(input,'utf8'));
await fs.mkdir(out,{recursive:true});
const w=Workbook.create();
const ns=['物件条件','候補判定','予算境界','根拠'];
const s=Object.fromEntries(ns.map(n=>[n,w.worksheets.add(n)]));
const ink='#23342F',green='#17704D',blue='#1652A2',amber='#FFF2CC',gray='#E9EDE9';
const fmt='#,##0.0;(#,##0.0);"–"';
const put=(a,r,v)=>a.getRange(r).values=v;
const f=(a,r,v)=>a.getRange(r).formulas=[[v]];
function title(a,t,end='J'){
 a.showGridLines=false;a.getRange(`A1:${end}100`).format.font={name:'Arial',size:10,color:ink};
 a.getRange(`A1:${end}100`).format.verticalAlignment='center';
 a.getRange('A:B').format.columnWidth=2;put(a,'C2',[[t]]);a.getRange('C2').format.font={size:16,bold:true};
 put(a,'C3',[['2026-11-15 / 物件未取得 / 金額：万円 / 数値は探索・比較条件で法定最低ではない']]);
 a.getRange(`C4:${end}4`).format.borders={bottom:{style:'thin',color:ink}};
}
function head(a,r,c,z){a.getRange(`${c}${r}:${z}${r}`).format={fill:ink,font:{color:'#FFFFFF',bold:true},rowHeight:26,horizontalAlignment:'center'};}
function inp(a,r){a.getRange(r).format.fill=amber;a.getRange(r).format.font.color=blue;}
function calc(a,r,cross=false){a.getRange(r).format.font.color=cross?green:'#000000';a.getRange(r).setNumberFormat(fmt);}
function textValid(ref){const clean=`TRIM(CLEAN(SUBSTITUTE(SUBSTITUTE(${ref},"　"," "),CHAR(160)," ")))`;return `AND(ISTEXT(${ref}),LEN(${clean})>0,COUNTIFS('根拠'!$C$46:$C$54,${clean})=0)`;}

const c=s['物件条件'];title(c,'総額2億円を目指す物件条件','L');
put(c,'C5',[['優先：地上階の元温浴用途。家賃100〜110万円・保証金6か月以下を探索目標。用途/支持/排気等は個別確認。']]);
put(c,'C6:L6',[['ID','分類','優先度','対象','目標・具体条件','保留/見送り/誤認防止','必要資料','関連費目','根拠ID','数値の性質']]);head(c,6,'C','L');
const n=d.conditions.length+6;
put(c,`C7:L${n}`,d.conditions.map(r=>[r.id,r.group,r.priority,r.topic,r.target,r.hold_or_reject,r.documents,r.cost_link,r.source_ids,r.basis_type]));
for(const [col,width]of Object.entries({C:8,D:21,E:15,F:26,G:80,H:78,I:70,J:32,K:20,L:25}))c.getRange(`${col}:${col}`).format.columnWidth=width;
c.getRange(`C7:L${n}`).format.rowHeight=58;c.getRange(`D7:L${n}`).format.wrapText=true;c.freezePanes.freezeRows(6);c.freezePanes.freezeColumns(6);

const r=s['根拠'];title(r,'根拠と⑥から引き継ぐ固定値','H');
put(r,'C6:G6',[['ID','出典','参照範囲・留保','確認日','URL']]);head(r,6,'C','G');
put(r,`C7:G${d.sources.length+6}`,d.sources.map(v=>[v.id,v.title,v.scope,v.checked,v.url]));
r.getRange('C:C').format.columnWidth=10;r.getRange('D:D').format.columnWidth=49;r.getRange('E:E').format.columnWidth=95;r.getRange('F:F').format.columnWidth=22;r.getRange('G:G').format.columnWidth=110;
r.getRange(`D7:G${d.sources.length+6}`).format.wrapText=true;r.getRange(`C7:G${d.sources.length+6}`).format.rowHeight=43;
put(r,'C22',[['⑥の固定値（候補入力では変更しない）']]);
const b=d.frozen_cost;
const constants=[['基準直接工事',b.direct/10000],['設計・開業準備等税込',b.soft_cash/10000],['家賃を除く月次現金',b.nonrent_monthly/10000],['元請10%×予備15%×消費税10%',b.construction_multiplier],['総資金の上限',d.cap/10000],['ピット減額の元工事範囲上限',440],['MEP減額の元工事範囲上限',950],['探索固定式の切片',b.search_intercept/10000],['保証金以外の家賃係数',11.7],['事業用家賃の税込倍率',1.1],['運転資金月数',3]];
constants.forEach((v,i)=>{put(r,`D${24+i}`,[[v[0]]]);put(r,`F${24+i}`,[[v[1]]]);});
r.getRange('F24:F34').setNumberFormat('#,##0.0000');
put(r,'C37',[['受電103kVAは設備比較。110kWは料金仮定。床下1.31mは仮スラブ上端から、FLからは1.51m。']]);
put(r,'C39',[['探索固定式は費用見積でない。工事5か月/礼金1/仲介1/保証0.7/運転3か月/全額返還保証金を固定。']]);
put(r,'C41',[['候補判定は実額の保証金・非返還費・工事増減を入力し、工事IDと証拠の重複を確認する。']]);
put(r,'C44',[['未取得を示す入力（判定用）']]);put(r,'C46:C54',['未確認','未取得','未入力','未定','不明','n/a','na','?','-'].map(v=>[v]));

const a=s['候補判定'];title(a,'候補1件の入力と予算判定','H');
for(const [row,label]of [[6,'候補名'],[7,'所在地・管轄'],[8,'階・直下用途'],[9,'募集/契約面積㎡'],[10,'計画に割当可能な区画㎡'],[11,'主要区画の最低梁下m']]){put(a,`C${row}`,[[label]]);inp(a,`E${row}`);}
put(a,'C13',[['黄色欄へ入力。空欄は未確認、0は確認した追加なし等。根拠・日付がない項目を合格にしない。']]);
put(a,'C15:H15',[['費用条件','単位','候補実額','資料・計算根拠','参考例（物件なし）','根拠の有無']]);head(a,15,'C','H');
const fields=[
 ['rent_ex_tax','家賃・共益費等の固定費合計','税抜万円/月'],
 ['refundable_deposit','返還予定保証金（実額）','万円'],
 ['paid_preopening_months','開業前の有料賃料月数','月数'],
 ['nonref_initial_cash','礼金/仲介/保証料/償却等','税込万円'],
 ['pit_saving','適合ピット再利用の純減額','税抜万円'],
 ['mep_saving','別の既存MEP再利用の純減額','税抜万円'],
 ['procurement_saving','他工種調達/仕様整理の純減額','税抜万円'],
 ['extra_direct','基準を超える追加直接工事','税抜万円'],
 ['extra_cash','譲渡等その他追加の初期現金','税込万円'],
 ['opex_delta','家賃以外の月次費用の増減','税込万円/月']];
fields.forEach((v,i)=>{const row=i+16;put(a,`C${row}:G${row}`,[[v[1],v[2],null,null,d.goal_example.inputs[v[0]]/(v[0]==='paid_preopening_months'?1:10000)]]);});
fields.forEach((v,i)=>f(a,`H${i+16}`,`=IF(${textValid('F'+(i+16))},"根拠あり","資料不足")`));
for(const row of [6,7])f(a,`H${row}`,`=IF(${textValid('E'+row)},"特定済","資料不足")`);
inp(a,'E16:F25');a.getRange('E16:E25').setNumberFormat(fmt);a.getRange('G16:G25').setNumberFormat(fmt);a.getRange('C16:G25').format.rowHeight=32;
put(a,'C27',[['総合予備判定']]);put(a,'C29',[['費用入力の状態']]);
f(a,'E29',`=IF(COUNT(E16:E25)<>10,"未入力",IF(OR(MIN(E16:E24)<0,E20>'根拠'!F29,E21>'根拠'!F30,SUM(E20:E22)>'根拠'!F24,E25+'根拠'!F26<0),"入力条件エラー","入力済"))`);
put(a,'C31',[['0＝未確認 / 1＝根拠照合 / 2＝変更案あり / 3＝成立困難を確認。点数ではありません。']]);
put(a,'C32:H32',[['ID','主要な成立条件','状態0〜3','証拠資料・回答','確認日','根拠の有無']]);head(a,32,'C','H');
d.empty_candidate.gates.forEach((g,i)=>{const row=i+33;put(a,`C${row}:G${row}`,[[g.id,g.label,0,null,null]]);f(a,`H${row}`,`=IF(AND(OR(E${row}=1,E${row}=2,E${row}=3),${textValid('F'+row)},ISNUMBER(G${row}),G${row}>=DATE(2000,1,1),G${row}<DATE(2101,1,1)),"根拠あり","資料不足")`);});
inp(a,'E33:G41');a.getRange('C33:H41').format.rowHeight=40;a.getRange('D33:D41').format.wrapText=true;
a.dataValidations.add({range:'E33:E41',rule:{type:'whole',operator:'between',formula1:0,formula2:3}});a.getRange('G33:G41').setNumberFormat('yyyy-mm-dd');
put(a,'C43',[['予算超過を解消する具体的な変更案']]);inp(a,'E43');
f(a,'E27',`=IF(OR(H6<>"特定済",H7<>"特定済"),"資料不足",IF(COUNTIFS(E33:E41,3,H33:H41,"根拠あり")>0,"成立困難",IF(OR(E29<>"入力済",COUNTIFS(H33:H41,"資料不足")>0,COUNTIFS(H16:H25,"資料不足")>0),"資料不足",IF(E60<0,IF(${textValid('E43')},"変更で対応","予算超過・変更案未確認"),IF(COUNTIFS(E33:E41,2)>0,"変更で対応","成立見込み（予備判定）")))))`);
put(a,'C44',[['金額は全て万円。実額の初期費用は家賃を変えても自動で増減しないため契約条件で再入力。']]);
const labs={46:'⑥基準の直接工事',47:'物件再利用の減額計',48:'別工種の調達等減額',49:'追加直接工事',50:'今回の直接工事',51:'経費・予備費・消費税込工事',52:'設計/調査/開業準備等',53:'開業前の家賃（税込）',54:'非返還の初期費用',55:'返還保証金',56:'その他追加現金',57:'月次運転費（家賃反映）',58:'運転資金3か月',59:'総必要現金',60:'2億円との差（正数は余裕）',61:'費用枠の評価'};
for(const [row,label]of Object.entries(labs))put(a,`C${row}`,[[label]]);
const build={46:"'根拠'!F24",47:'SUM(E20:E21)',48:'E22',49:'E23',50:'E46-SUM(E47:E48)+E49',51:"E50*'根拠'!F27",52:"'根拠'!F25",53:"E16*'根拠'!F33*E18",54:'E19',55:'E17',56:'E24',57:"'根拠'!F26+E16*'根拠'!F33+E25",58:"E57*'根拠'!F34",59:'SUM(E51:E56,E58)',60:"'根拠'!F28-E59"};
for(const [row,expr]of Object.entries(build))f(a,`E${row}`,`=IF($E$29<>"入力済","未入力",${expr})`);
f(a,'E61',`=IF(E29<>"入力済","未算定",IF(E60>=0,"2億円以下（概算）","2億円超"))`);
calc(a,'E46:E60',true);a.getRange('C59:E60').format.fill=gray;a.getRange('C59:E60').format.font.bold=true;
a.getRange('E60').conditionalFormats.add('cellIs',{operator:'lessThan',formula:0,format:{fill:'#FDECE8',font:{color:'#AA2D24',bold:true}}});
put(a,'C64',[['成立見込みは次の調査へ進める予備判定。契約判断・構造安全・許可取得を確定するものではない。']]);
put(a,'C66',[['償却は返還保証金から除き非返還初期費へ。二重に計上しない。追加工事は基準見積との純差額。']]);
put(a,'C68',[['主要な構造/本管/受変電/共用消防改修等は見積に応じ加算。未見積は0にせず根拠条件を未確認とする。']]);
put(a,'C70',[['確認日はExcelの日付として入力。日付文字列や「未確認」、空白だけの根拠は資料不足。']]);
for(const [col,width]of Object.entries({C:43,D:46,E:24,F:67,G:27,H:20}))a.getRange(`${col}:${col}`).format.columnWidth=width;

const m=s['予算境界'];title(m,'家賃・保証金と必要な工事減額','I');
put(m,'C5',[['検索用の固定式。条件が変わる候補は候補判定へ実額入力する。全て万円、家賃は税抜月額。']]);
put(m,'C7',[['直接工事減額の比較条件（税抜）']]);put(m,'F7',[[1200]]);inp(m,'F7');
put(m,'C10:G10',[['家賃/月','保証金4か月','6か月','8か月','10か月']]);head(m,10,'C','G');
for(let i=0;i<6;i++){
 const row=i+11;put(m,`C${row}`,[[100+i*10]]);
 for(let j=0;j<4;j++)f(m,`${['D','E','F','G'][j]}${row}`,`='根拠'!$F$31+$C${row}*(${[4,6,8,10][j]}+'根拠'!$F$32)-$F$7*'根拠'!$F$27`);
}
calc(m,'D11:G16',true);m.getRange('D11:G16').conditionalFormats.add('cellIs',{operator:'greaterThan',formula:20000,format:{fill:'#FDECE8',font:{color:'#AA2D24'}}});
put(m,'C19:G19',[['2億以内に必要な直接減額','保証金4か月','6か月','8か月','10か月']]);head(m,19,'C','G');
for(let i=0;i<6;i++){
 const row=i+20;put(m,`C${row}`,[[100+i*10]]);
 for(let j=0;j<4;j++)f(m,`${['D','E','F','G'][j]}${row}`,`=MAX(0,('根拠'!$F$31+$C${row}*(${[4,6,8,10][j]}+'根拠'!$F$32)-'根拠'!$F$28)/'根拠'!$F$27)`);
}calc(m,'D20:G25',true);
put(m,'C28:F28',[['家賃上限/月（2億以内）','保証金月数','物件由来700万減のみ','合計1200万減']]);head(m,28,'C','F');
for(let i=0;i<4;i++){
 const row=i+29,n=[4,6,8,10][i];put(m,`C${row}:D${row}`,[[`保証金${n}か月`,n]]);
 for(const [col,saving]of [['E',700],['F',1200]])f(m,`${col}${row}`,`=('根拠'!$F$28-'根拠'!$F$31+${saving}*'根拠'!$F$27)/($D${row}+'根拠'!$F$32)`);
}calc(m,'E29:F32',true);
put(m,'C35',[['保証金6か月で物件由来700万減しか確認できない場合、家賃上限は約90.6万円/月。']]);
put(m,'C37',[['120万円/月・保証金6か月・1200万減の目標例は1億9824.4万円。余白175.6万円は追加費用全体で共有。']]);
put(m,'C39',[['工期+1か月で家賃だけ132万円増。1億9千万円を目指すなら同条件で直接減額約1792.5万円が必要。']]);
put(m,'C41',[['検索固定式＝19370.1982＋家賃R×（保証金月数d＋11.7）−工事減額S×1.3915。見積ではない。']]);
m.getRange('C:C').format.columnWidth=43;m.getRange('D:G').format.columnWidth=23;m.getRange('C10:G32').format.rowHeight=27;

w.recalculate();
const checks={};const assert=(test,message)=>{if(!test)throw Error(message);};
assert(a.getRange('E27').values[0][0]==='資料不足','Blank candidate passed');assert(a.getRange('E59').values[0][0]==='未入力','Blank finance became zero');
checks.initial={status:a.getRange('E27').values[0][0],total:a.getRange('E59').values[0][0]};
fields.forEach((v,i)=>put(a,`E${i+16}`,[[d.goal_example.inputs[v[0]]/(v[0]==='paid_preopening_months'?1:10000)]]));w.recalculate();
const target=a.getRange('E59').values[0][0];assert(Math.abs(target-d.goal_example.budget.total_cash/10000)<.001,'Target budget mismatch');
assert(a.getRange('E27').values[0][0]==='資料不足','Price overrode missing evidence');
put(a,'E6',[['検証用物件']]);put(a,'E7',[['東京都・検証用所在地']]);fields.forEach((v,i)=>put(a,`F${i+16}`,[['検証用の費用資料']]));
const testDate=new Date(Date.UTC(2026,10,15));
for(let row=33;row<=41;row++)put(a,`E${row}:G${row}`,[[1,'検証用・仮の証拠',testDate]]);w.recalculate();
assert(a.getRange('E27').values[0][0]==='成立見込み（予備判定）','Complete evidence not recognized');
put(a,'F33',[['　  ']]);w.recalculate();assert(a.getRange('E27').values[0][0]==='資料不足','Whitespace evidence passed');put(a,'F33',[['検証用証拠']]);
put(a,'F33',[[0]]);w.recalculate();assert(a.getRange('E27').values[0][0]==='資料不足','Numeric evidence treated as a document');put(a,'F33',[['検証用証拠']]);
put(a,'G33',[['未確認']]);w.recalculate();assert(a.getRange('E27').values[0][0]==='資料不足','Invalid date passed');put(a,'G33',[[testDate]]);
put(a,'E24',[[500]]);w.recalculate();assert(a.getRange('E27').values[0][0]==='予算超過・変更案未確認','Over-budget implied changeable');
put(a,'E43',[['別工種の再見積案・要確認']]);w.recalculate();assert(a.getRange('E27').values[0][0]==='変更で対応','Specific budget plan ignored');put(a,'E24',[[0]]);put(a,'E43',[[null]]);
put(a,'E33:F33',[[3,null]]);w.recalculate();assert(a.getRange('E27').values[0][0]==='資料不足','Unproven rejection treated as fact');
put(a,'F33',[['検証用の禁止書面']]);w.recalculate();assert(a.getRange('E27').values[0][0]==='成立困難','Proven rejection ignored');
put(a,'E33',[[2]]);w.recalculate();assert(a.getRange('E27').values[0][0]==='変更で対応','Change treated as pass');put(a,'E33',[[1]]);
put(a,'E22',[[null]]);w.recalculate();assert(a.getRange('E59').values[0][0]==='未入力','Missing saving became zero');
put(a,'E22',[[0]]);w.recalculate();const zero=a.getRange('E59').values[0][0];assert(zero>20000,'Real zero not preserved');
checks.goal={total_man:target,expected_man:d.goal_example.budget.total_cash/10000,zero_procurement_man:zero};
for(let i=0;i<6;i++)for(let j=0;j<4;j++){
 const row=i+11,col=['D','E','F','G'][j];const expected=d.matrix[i*4+j];
 assert(Math.abs(m.getRange(`${col}${row}`).values[0][0]-expected.total_cash/10000)<.001,'Matrix mismatch');
 assert(Math.abs(m.getRange(`${col}${i+20}`).values[0][0]-expected.required_direct_saving/10000)<.001,'Saving frontier mismatch');
}
fields.forEach((v,i)=>put(a,`E${i+16}:F${i+16}`,[[null,null]]));put(a,'E6',[[null]]);put(a,'E7',[[null]]);
for(let row=33;row<=41;row++)put(a,`E${row}:G${row}`,[[0,null,null]]);
w.recalculate();assert(a.getRange('E27').values[0][0]==='資料不足','Final candidate not restored');
const errors=await w.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:30},summary:'formula error scan'});
checks.final={status:a.getRange('E27').values[0][0],total:a.getRange('E59').values[0][0]};
await fs.writeFile(path.join(out,'verification.json'),JSON.stringify({checks,errors:errors.ndjson},null,2));
for(const [name,range]of [['物件条件','C2:I14'],['候補判定','C15:G29'],['候補判定-根拠','C31:H41'],['予算境界','C2:G32'],['根拠','C2:F17']]){
 const sheetName=name.startsWith('候補判定')?'候補判定':name;
 const blob=await w.render({sheetName,range,scale:1.3,format:'png'});
 await fs.writeFile(path.join(out,name+'-preview.png'),new Uint8Array(await blob.arrayBuffer()));
}
await (await SpreadsheetFile.exportXlsx(w)).save(path.join(out,'sauna_property_v1.xlsx'));
console.log(JSON.stringify({sheets:ns,conditions:d.conditions.length,checks,formula_errors:errors.ndjson}));
