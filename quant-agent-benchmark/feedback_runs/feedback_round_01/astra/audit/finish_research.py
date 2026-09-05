from pathlib import Path
import json, base64, shutil, time
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from experiments import AUDIT,ROOT,fit_variant,truth

# Refit a previously declared, outlier-free synthetic case solely to inspect weights.
f=pd.read_csv(AUDIT/'synthetic/long_hump_normal.csv');fit=fit_variant(f,'reference')
w=f[['instrument_id','instrument_type','maturity_years','sigma','reliability']].copy()
w['robust_weight']=fit.robust_weights;w['residual']=fit.quotes-f.normalized_quote.to_numpy()
w.to_csv(AUDIT/'synthetic_weight_diagnostics.csv',index=False)
long=w.maturity_years>=15
mechanism={'case':'long_hump:normal','synthetic_outliers_injected':0,'long_instruments':int(long.sum()),
           'long_downweighted_count':int((w.loc[long,'robust_weight']<.999).sum()),
           'long_median_robust_weight':float(w.loc[long,'robust_weight'].median()),
           'interpretation':'Known clean shape with small noise receives reduced weights. This supports shape/robustness confounding; it does not justify disabling robustness on contaminated data.'}
(AUDIT/'robust_mechanism.json').write_text(json.dumps(mechanism,indent=2)+'\n')

# Show an actual rejected endpoint regression rather than only favorable examples.
d=pd.read_csv(AUDIT/'curve_diagnostics.csv');colors={'reference':'#146b83','smoothing_lower':'#c86820','endpoint_flat_zero':'#9661a8','long_penalty_taper':'#449062'}
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.2})
fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
for col,case in enumerate(['long_hump:normal','long_hump:long_illiquid']):
    for row,(column,truecolumn,label) in enumerate([('zero_rate','truth_zero','Zero rate (%)'),('forward_rate','truth_forward','Instantaneous forward (%)')]):
        ax=axes[row,col]
        for name,c in colors.items():
            v=d[(d.case==case)&(d.variant==name)];ax.plot(v.maturity_years,v[column]*100,label=name,color=c,lw=1.8)
        ax.plot(v.maturity_years,v[truecolumn]*100,color='black',ls='--',label='Independent analytic truth')
        ax.set(xlabel='Maturity (years)',ylabel=label,title=case.replace(':',' / '))
axes[0,0].legend(fontsize=8)
axes[0,1].text(.03,.05,'Long zero RMSE: reference 17.62 bp\nFlat endpoint 20.97 bp (rejected)',transform=axes[0,1].transAxes,fontsize=9)
fig.suptitle('Long-end shape is missed; endpoint improvement is not uniform',fontsize=14)
fig.savefig(AUDIT/'charts/synthetic_diagnostics.png',dpi=160,bbox_inches='tight');plt.close(fig)

summary=pd.read_csv(AUDIT/'factor_summary.csv')
display=summary[['variant','long_zero_rmse_bp','long_forward_rmse_bp','guardrail_violations']].rename(columns={'variant':'変更要因','long_zero_rmse_bp':'平均長期ゼロRMSE bp','long_forward_rmse_bp':'平均長期フォワードRMSE bp','guardrail_violations':'悪化条件への抵触セル数'})
quality=json.loads((AUDIT/'final_clean_output/diagnostics/data_quality.json').read_text())
validation=json.loads((AUDIT/'final_clean_output/diagnostics/validation.json').read_text())
oracle=json.loads((AUDIT/'pricing_summary.json').read_text())
ois=json.loads((AUDIT/'ois_convention_summary.json').read_text())
def figure(name,caption):
    b=base64.b64encode((AUDIT/'charts'/name).read_bytes()).decode()
    return f'<figure><img alt="{name}" src="data:image/png;base64,{b}"><figcaption>{caption}</figcaption></figure>'

body=f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Astra 改善ラウンドの判断</title><style>
body{{margin:0;background:#edf3f6;color:#20333d;font-family:-apple-system,BlinkMacSystemFont,sans-serif;line-height:1.75}}main{{max-width:1120px;margin:auto;background:white;padding:36px}}h2{{border-bottom:1px solid #b3c8d0;margin-top:2.4em}}.lead{{background:#e7f2f5;padding:20px;border-left:5px solid #146b83}}.warn{{border-left:4px solid #c86820;padding-left:16px}}table{{border-collapse:collapse;font-size:.85em;width:100%}}th,td{{padding:8px;border-bottom:1px solid #ccdce3;text-align:left}}.scroll{{overflow:auto}}img{{max-width:100%;height:auto}}figure{{margin:28px 0}}figcaption{{font-size:.9em;color:#526976}}code{{overflow-wrap:anywhere}}@media(max-width:700px){{main{{padding:20px}}h1{{font-size:1.5em}}}}</style></head><body><main>
<p>Astra / xhigh（ユーザー指定ラベル。実行設定は独立確認不可） / feedback_round_01</p><h1>採用できる数値改善は確認できませんでした</h1>
<h2>要旨 / Executive Summary</h2><p class="lead">数値モデルは初回を維持しました。JSON、日英章名、直接割引関数の価格付けAPIを整備しました。人工20条件の平均長期ゼロRMSEを5.8356→3.9156bpに改善する候補もありましたが、公開短期OISや人工フォワードの悪化が事前条件を超え、不採用です。</p>
<h2>手法 / Methodology</h2><p>公開商品の属性に独自の解析的5カーブを価格付けし、通常・10%欠落・長端低流動性・異常値の4条件を固定seed=20260905で生成しました。価格は製品の支払列を呼ばない独立式です。短期T≤2、中期2&lt;T&lt;15、長期T≥15に分け、各条件内で一要因のみ変えました。これは研究用の人工集合であり、隠し真値や時間外データではありません。公開S0〜S3の分割IDと近傍除外IDを保存しています。</p>
<p>事前採用条件は長期ゼロ平均5%以上改善、公開4分割Huber悪化2%以内、各条件・年限・商品の許容幅遵守です。ゼロはmax(比較元10%,0.25bp)、フォワードRMSEはmax(10%,1bp)、最大フォワード誤差はmax(10%,2bp)、商品価格RMSEはmax(10%,金利0.25bpまたは債券0.025ポイント)を超える悪化を許しません。採用条件を結果に合わせて変更していません。</p>
<p>罰則は nλ∫(d²z_bp/dx²)²dx、x=log(1+T)です。λの尺度はbp⁻²で、金利小数の罰則へ同じ値のλを使えません。d²z/dx²=(1+T)²z″(T)+(1+T)z′(T)なので、年数上で直線のゼロ金利にも罰則がかかります。</p>
<h2>データ品質 / Data Quality</h2><p>公開143行から131商品を使用。7重複と5古い観測を除外し、初回と同じ単位補正を維持しました。全観測の監査と欠測セルを保存し、誤差で検証商品を削除していません。公開の単位補正が分割前の全テープを参照する限界は残ります。</p><p>公開の長期債券24商品の22商品がHuberで低下し、重み中央値は0.1423でした。真の山を持つ外れ値なしの人工通常条件でも、長期{mechanism['long_instruments']}商品の{mechanism['long_downweighted_count']}商品が低下しました。重みの低下を観測不正の確定証拠とは扱えません。</p>
<h2>モデル比較 / Model Comparison</h2><div class="scroll">{display.to_html(index=False,border=0,float_format=lambda x:f'{x:.4f}')}</div><p>表は20条件を等重みで平均したRMSEで、全点を一括したRMSEではありません。抵触セル数には全期間と長期の重複セルが含まれます。referenceは初回の高度モデル、simple_baselineは同じ重み付きNelson–Siegelです。密な長期ノットは0.0125%改善に留まり、5%条件に達しません。</p>
<h2>感度分析 / Sensitivity Analysis</h2><p class="warn">λを0.001から0.0001にすると平均長期ゼロRMSEは32.90%改善しますが、公開S2短期OISのRMSEは2.0274→9.1071bp、S3長期債券は4.1308→5.8540ポイントへ悪化しました。長期山の通常条件では中期最大フォワード誤差が10.5104→16.8709bpへ悪化します。端点のゼロ傾き固定は平均長期ゼロを23.62%改善する一方、長期山・低流動性の長期RMSEを17.6196→20.9706bpに悪化させました。</p>
<p>長期罰則の縮小も平均9.57%改善と局所悪化を併せ持ち、不採用です。Huber閾値や頑健化解除のいずれも採用条件を満たしません。複数数値要因を合成しておらず、相互作用を一要因実験から主張しません。</p>
<h2>検証と価格再現 / Validation and Repricing</h2><p>独立価格式1965照合で率の最大差は{oracle['maximum_rate_difference']:.3g}（年率小数）、債券は{oracle['maximum_price_difference']:.3g}ポイントです。これは仮定した規約内の実装照合です。同じ公開カーブで端数利息をなくすと価格RMS差0.5416、全額にすると0.5813ポイント。規約変更後の再校正による30年ゼロ差はそれぞれ+1.1235bp、−2.8474bpでした。</p>
<p>OISを「2年まで年払、その後半年払」と読む代替では、固定した公開カーブ上で最大{ois['reference_curve_max_quote_change_bp']:.4f}bpの価格付け金利差が生じました。これを隠し生成規約と推定せず、既存の商品属性を使う全脚頻度を維持します。独立式への一致と隠し採点の改善は別です。</p>
<p>最終全46テストと新規出力先のフルCLIが成功。721格子、正の割引因子、フォワード微分、有限なリスク、キー集計を検証しました。フォワードの差分誤差最大{validation['forward_max_absolute_fd_error']:.3g}、DV01半ステップ相対差最大{validation['dv01_max_relative_half_step_error']:.3g}です。初回数値CSVはコピーでバイト一致を再現しています。</p>
<h2>図 / Charts</h2>{figure('factor_comparison.png','全候補を表示。平均だけで採用せず、年限・商品・条件ごとの悪化で判断しました。')}{figure('synthetic_diagnostics.png','自作の真値と推定。長期の山は十分再現できず、端点変更による悪化も残ります。')}{figure('public_diagnostics.png','公開データのゼロ・フォワード・重み・債券残差。真の公開カーブの値は不明です。')}
<h2>制約 / Limitations</h2><p>支払規約の真の指定、長期形状、前処理漏洩、時間外再現性は未解決です。人工集合は今回の比較に使用したため、採用後の独立確認集合ではありません。人工全条件でCLI内部の平滑化選択まで再実行した比較は未検証です。生の価格誤差、人工カーブ誤差、標準化損失、内部整合性、提出形式を混同しません。トークン・料金・割当消費は取得できずnullです。</p>
<h2>次の検証 / Recommended Next Steps</h2><p>このラウンドは現設定で確定します。次回の許可された研究では、最初に支払日と端数クーポンを公開仕様として確定し、その後、今回使用していない観測配置・別日・独立形状で平滑化とロバスト重みの相互作用を調べることを推奨します。隠し採点を使った反復は行っていません。</p></main></body></html>'''
(ROOT/'submission/reports/feedback_review.html').write_text(body)

# Promote verified CLI artifacts, preserving the independent clean run for audit.
shutil.copytree(AUDIT/'final_clean_output',ROOT/'submission/outputs',dirs_exist_ok=True)
shutil.copyfile(AUDIT/'final_clean_output/reports/research_report.html',ROOT/'submission/reports/research_report.html')
relocated=AUDIT/'relocated_project';relocated.mkdir(exist_ok=False)
shutil.copytree(ROOT/'submission/src',relocated/'src')
(AUDIT/'protocol.md').write_text((AUDIT/'protocol.md').read_text()+'''\n2026-09-05 08:22 UTC以降の整理：数値候補はすべて不採用で確定。採用閾値・分割・入力は変更なし。規約分離の補足としてOIS頻度の別解釈を固定D上だけで測定（再校正・採用なし）。既定の人工通常条件の重みを診断のため再取得。図では端点条件が悪化した長期山・低流動性を明示。いずれも選択規則の変更ではない。\n''')
print(json.dumps({'robust_mechanism':mechanism,'reports_written':True,'relocation_prepared':True},indent=2))
