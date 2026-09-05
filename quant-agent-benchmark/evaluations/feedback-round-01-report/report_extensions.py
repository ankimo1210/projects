"""Source-backed additions: calibration/test curve shapes, approaches, efficiency."""
import contextlib
import hashlib
import io
import json
import math
from pathlib import Path
import sqlite3
import sys

import numpy as np
import pandas as pd


def extend(b, artifact):
    root, here, new = b.ROOT, b.HERE, b.NEW
    shapes = f'{new}/curve_shapes'
    audit = b.read(f'{shapes}/capture_audit.json')
    b.check(len(audit['runs']) == 77 and audit['candidates_unchanged'] and audit['candidates_match_frozen'], '77 shape captures match frozen submissions')
    for phase in ['manifest_before', 'manifest_after']:
        b.check(all(not p['mismatches'] for p in audit[phase].values()), 'Shape capture ' + phase)
    sys.path.insert(0, str(root / 'evaluator'))
    import scoring
    data, blocks = artifact['snapshot']['datasets'], artifact['manifest']['blocks']
    added_charts, added_tables, chart_notes, quality = [], [], [], []
    file_sources = []
    db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
    db.execute('CREATE TABLE curve_vectors(case_id TEXT, model TEXT, maturities TEXT, zero_rates TEXT, forward_rates TEXT)')
    db.execute('CREATE TABLE display_grid(dataset TEXT, case_id TEXT, years REAL)')
    db.create_function('linear_interp',3,lambda x,t,v:float(np.interp(x,json.loads(t),json.loads(v))),deterministic=True)

    def frame(rel):
        path = root / rel
        b.INPUTS[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
        file_sources.append(rel)
        return pd.read_csv(path)

    def prose(id, body, source):
        return dict(id=id, type='markdown', body=body.strip(), layout='full', sourceId=source)

    def insert_after(id, additions):
        i = next(i for i, x in enumerate(blocks) if x['id'] == id)
        blocks[i+1:i+1] = additions

    def table(id, title, subtitle, rows, columns, source, order=('model', 'asc')):
        data[id] = rows
        added_tables.append(dict(id=id, title=title, subtitle=subtitle, dataset=id, sourceId=source,
            layout='full', density='spacious', defaultSort=dict(field=order[0], direction=order[1]),
            columns=[dict(field=f, label=l, type=t) for f, l, t in columns]))
        return dict(id=id+'-block', type='table', tableId=id, layout='full')

    def chart(id, title, subtitle, dataset, fields, source, kind='line'):
        spec = dict(id=id, title=title, subtitle=subtitle, dataset=dataset, sourceId=source, type=kind,
            layout='full', valueFormat='number', unit='%', showDescription=True, maxRows=2000,
            encodings=dict(x=dict(field='years', type='quantitative', label='満期（年）'),
                           y=dict(fields=fields, type='quantitative', label='金利（%）')),
            palette=dict(kind='semantic', name='blue'), labels=dict(values='none'),
            legend=dict(position='bottom', sort='spec'), settings=dict(sort='none', showPoints='never', showValues=False),
            surface=dict(surface='card', showControls=False, interactiveLegend=True))
        added_charts.append(spec)
        chart_notes.append(dict(id=id, family='ordered-axis shape' if kind=='line' else 'relationship',
            question=title, dataset=dataset, fields=fields, source=source,
            palette='Neutral semantic benchmark; up to four model identities in the packaged reader palette. Multi-model exception to the binary benchmark palette.',
            non_color='Explicit model legend and benchmark role; numeric series table remains available.',
            footprint='Full width; model groups split to prevent eight-line overplotting.',
            limitation='Lines show submitted curve estimates, not observed zero-rate data. Uniform maturity spacing avoids categorical-axis distortion; metrics use the full truth grid. Shared reader display interpolation is not a new estimator.'))
        return dict(id=id+'-block', type='chart', chartId=id, layout='full')

    methods = ['astra', 'sol', 'terra', 'luna', 'sonnet', 'opus', 'fable']
    groups = [('GPT', methods[:4]), ('Claude', methods[4:])]
    curves, truth_by = {}, {}
    cases = ['main'] + [f's{i:02}' for i in range(1, 11)]
    names = {'s01':'短期負金利', 's02':'急勾配', 's03':'強い逆イールド', 's04':'長期観測が疎',
             's05':'複数の大きな外れ値', 's06':'流動性の高い指標の欠損', 's07':'観測重複',
             's08':'単位誤り', 's09':'長期の低流動性', 's10':'有効だが雑音の多い観測'}
    for sid in cases:
        truth_path = 'evaluator/ground_truth/main_curve.csv' if sid=='main' else f'evaluator/hidden_scenarios/{sid}/truth_curve.csv'
        truth = frame(truth_path)
        truth_by[sid] = truth
        t = truth['maturity_years'].to_numpy(float)
        b.check(np.isfinite(truth.to_numpy(float)).all() and np.all(np.diff(t)>0), sid+': finite unique ordered truth grid')
        display_t = t[1:] if sid=='main' else np.linspace(t[1], t[-1], 361)
        db.executemany('INSERT INTO display_grid VALUES(?,?,?)', [('shape-'+sid,sid,float(x)) for x in display_t])
        db.execute('INSERT INTO curve_vectors VALUES(?,?,?,?,?)',(sid,'真値 benchmark',json.dumps(t.tolist()),json.dumps(truth['zero_rate'].tolist()),json.dumps(truth['instantaneous_forward_rate'].tolist())))
        b.check(np.allclose(np.diff(display_t),np.diff(display_t)[0],atol=2e-8,rtol=1e-6),sid+': uniformly spaced display maturity')
        rows = [dict(years=round(float(x), 9), case=sid,
                     **{'真値 benchmark z':round(float(np.interp(x,t,truth['zero_rate']))*100,6),
                        '真値 benchmark f':round(float(np.interp(x,t,truth['instantaneous_forward_rate']))*100,6)}) for x in display_t]
        for model in methods:
            curve = frame(f'{shapes}/{model}/{sid}_curve.csv')
            curves[model, sid] = curve
            b.check(curve['maturity_years'].is_unique and np.isfinite(curve.to_numpy(float)).all(), model+sid+': finite unique curve')
            z = scoring.interp_zero(curve, t)
            f = np.gradient(z*t, t, edge_order=1)
            db.execute('INSERT INTO curve_vectors VALUES(?,?,?,?,?)',(sid,model.title(),json.dumps(t.tolist()),json.dumps(z.tolist()),json.dumps(f.tolist())))
            frozen = b.read(f'{new}/{model}_score.json')['quantitative_diagnostics']
            expected = frozen if sid=='main' else frozen['hidden_scenarios'][sid]
            for label, values, true_col in [('zero_rate_rmse_bps', z, 'zero_rate'), ('forward_rate_rmse_bps', f, 'instantaneous_forward_rate')]:
                error = 1e4*np.sqrt(np.mean((values-truth[true_col].to_numpy(float))**2))
                b.check(np.isclose(error, expected[label], rtol=1e-9, atol=1e-9), model+sid+': retained CSV '+label)
            for row, x in zip(rows, display_t):
                row[model.title()+' z'] = round(float(np.interp(x,t,z))*100, 6)
                row[model.title()+' f'] = round(float(np.interp(x,t,f))*100, 6)
        quality.append(dict(case=sid, truth_rows=len(t), chart_rows=len(rows), display_start_years=float(display_t[0]),
                            chart_max_gap_years=float(np.max(np.diff(display_t)))))
        data['shape-'+sid] = rows
    # A separate uniform 1-day..2-year grid includes the earliest point omitted by the full view.
    t=truth_by['main']['maturity_years'].to_numpy(float)
    short=[]
    for x in np.linspace(t[0],2,97):
        db.execute('INSERT INTO display_grid VALUES(?,?,?)',('shape-main-short','main',float(x)))
        row=dict(years=round(float(x),9),case='main',**{'真値 benchmark z':round(float(np.interp(x,t,truth_by['main']['zero_rate']))*100,6)})
        for model in methods:row[model.title()+' z']=round(float(scoring.interp_zero(curves[model,'main'],x))*100,6)
        short.append(row)
    data['shape-main-short'] = short
    shape_sql='''SELECT g.dataset, g.case_id, round(g.years,9) AS years, v.model,
 round(100*linear_interp(g.years,v.maturities,v.zero_rates),6) AS zero_percent,
 round(100*linear_interp(g.years,v.maturities,v.forward_rates),6) AS forward_percent
FROM main.display_grid AS g JOIN main.curve_vectors AS v ON v.case_id=g.case_id
ORDER BY g.dataset,g.years,v.model;'''
    sampled={}
    for q in db.execute(shape_sql):
        key=(q['dataset'],q['years'])
        row=sampled.setdefault(key,dict(years=q['years'],case=q['case_id']))
        row[q['model']+' z']=q['zero_percent'];row[q['model']+' f']=q['forward_percent']
    for dataset in ['shape-'+s for s in cases]+['shape-main-short']:
        data[dataset]=[v for (d,_),v in sampled.items() if d==dataset]

    public = frame('input/market_data/market_observations.csv')
    all_instruments = frame('evaluator/ground_truth/all_instruments_truth.csv')
    holdout = frame('evaluator/ground_truth/holdout_instruments.csv')
    train_ids, test_ids = set(public.instrument_id), set(holdout.instrument_id)
    b.check(not train_ids & test_ids, 'Public/holdout instrument IDs are disjoint')
    b.check(train_ids | test_ids == set(all_instruments.instrument_id), 'Public + holdout cover all 160 canonical instruments')
    b.check(all_instruments.instrument_id.is_unique and holdout.instrument_id.is_unique, 'Canonical pricing target keys unique')
    train = all_instruments[all_instruments.instrument_id.isin(train_ids)]
    b.check(len(public)==143 and len(train)==136 and len(holdout)==24, '143 observations, 136 public instruments, 24 holdout instruments')
    pricing_rows = []
    db.execute('CREATE TABLE pricing_errors(model TEXT, split TEXT, instrument_type TEXT, instrument_id TEXT, error REAL)')
    for model in methods:
        result = dict(model=model.title())
        holdout_metric=scoring.curve_metrics(curves[model,'main'],truth_by['main'],holdout)['hidden_instrument_normalized_rmse']
        expected=b.read(f'{new}/{model}_score.json')['quantitative_diagnostics']['hidden_instrument_normalized_rmse']
        b.check(np.isclose(holdout_metric,expected,rtol=1e-9,atol=1e-9), model+': held-out pricing matches frozen score')
        for split, instruments in [('train', train), ('test', holdout)]:
            for kind, prefix, scale in [('deposit','deposit',100), ('ois_swap','swap',100), ('bond','bond',1)]:
                group = instruments[instruments.instrument_type==kind]
                errors = np.array([scoring.model_quote(r, curves[model,'main'])-r.true_quote for _,r in group.iterrows()])
                db.executemany('INSERT INTO pricing_errors VALUES(?,?,?,?,?)',[(model.title(),split,kind,identifier,float(e)*scale) for identifier,e in zip(group.instrument_id,errors)])
                result[f'{split}_{prefix}'] = float(np.sqrt(np.mean(errors**2))*scale)
                result[f'{split}_{prefix}_n'] = len(group)
        pricing_rows.append(result)
    pricing_sql='''SELECT model, split, instrument_type, count(*) AS instruments,
 sqrt(avg(error*error)) AS rmse FROM main.pricing_errors
GROUP BY model,split,instrument_type ORDER BY model,split,instrument_type;'''
    for q in db.execute(pricing_sql):
        r=next(r for r in pricing_rows if r['model']==q['model'])
        key=q['split']+'_'+{'deposit':'deposit','ois_swap':'swap','bond':'bond'}[q['instrument_type']]
        b.check(math.isclose(q['rmse'],r[key],rel_tol=1e-12,abs_tol=1e-12) and q['instruments']==r[key+'_n'],q['model']+key+': independent SQL repricing aggregate')
    b.save(root/new/'curve_shape_quality.json',dict(cases=quality, public_observations=len(public),
            public_unique_instruments=len(train_ids), holdout_instruments=len(test_ids), overlapping_instruments=0))
    b.save(root/new/'pricing_train_test.json',pricing_rows)

    shape_source = dict(id='curve-shapes', label='固定提出物のカーブ再取得・商品別価格照合', path=f'{shapes}/capture_audit.json',
        query=dict(engine='SQLite with deterministic NumPy linear_interp UDF',language='sql',sql=shape_sql,
            description='77 original-CLI runs in temporary copies. Retained curve zero/forward RMSEs rechecked against frozen final scores. Full public view uses 720 near-uniform points from 1 month to 30 years; hidden views use 361 uniformly spaced interpolated samples over the same range. Separate public short view uses 97 uniform points from 1 day to 2 years. Metrics use all 721 truth-grid points. SQL performs display interpolation and fraction-to-percent conversion from owner-verified full-grid vectors.',
            tables_used=list(dict.fromkeys(file_sources))+[f'{new}/capture_curves.py',f'{new}/curve_shape_quality.json',f'{new}/pricing_train_test.json',
                'evaluations/feedback-round-01-report/report_extensions.py','main.curve_vectors','main.display_grid','evaluations/feedback-round-01-report/curve_cost_context.sqlite'],
            metric_definitions=['One submitted algorithm is recalibrated separately for each hidden market. This is NOT a fixed public-trained curve predicting all scenarios.',
              'Public quote rows contain intentional duplicates, missingness and unit corruption. 143 rows represent 136 instruments; 24 canonical instruments are disjoint holdouts.',
              'Train/test pricing errors use canonical true_quote, not corrupted public quote_value or candidate-specific cleaned targets. Deposits/swaps in bp; bonds in price units per 100 par.',
              'Common emitted-curve interpolator and payment convention match the frozen evaluator. Payment-rule ambiguity remains.',
              'Shape capture computation is owner-side verification and excluded from agent time/tokens/API cost.']))
    artifact['manifest']['sources'].append(shape_source); artifact['sources'].append(shape_source) if artifact['sources'] is not artifact['manifest']['sources'] else None
    pricing_source=dict(id='pricing-split',label='公開商品・非公開商品の真値価格誤差',path=f'{new}/pricing_train_test.json',query=dict(
        engine='SQLite',language='sql',sql=pricing_sql,
        description='Canonical scorer model_quote prices every public/holdout instrument using the retained main curve. pricing_errors records model quote minus canonical true_quote; rate errors multiplied by 100 to bp, bond errors remain price units per 100 par. SQL independently aggregates RMSE and group counts.',
        tables_used=['main.pricing_errors','evaluations/feedback-round-01-report/curve_cost_context.sqlite','evaluator/scoring.py','evaluator/ground_truth/all_instruments_truth.csv','evaluator/ground_truth/holdout_instruments.csv','input/market_data/market_observations.csv',f'{new}/pricing_train_test.json','evaluations/feedback-round-01-report/report_extensions.py']))
    artifact['manifest']['sources'].append(pricing_source); artifact['sources'].append(pricing_source) if artifact['sources'] is not artifact['manifest']['sources'] else None

    train_blocks = [prose('training-shapes-heading','''## 2A. 公開データのカーブ：短期のずれとフォワードの跳びを分けて見る

ここでの「トレーニング」は、公開された143観測・136商品を使うカーブ較正を指す。ゼロ金利そのものが教師データとして渡されたわけではない。**生のスワップ金利・債券利回りをゼロ金利と同じ線には重ねていない。** 真値の線は今回、採点側だけで参照している。

以下は全て改善後の提出物から再実行したカーブ。全体図は1か月〜30年、短期拡大図は1日〜2年。満期は等間隔に表示し、ゼロ金利はz、フォワードはfと凡例に記す。GPT群とClaude群を分けるのは重なりを減らすためで、群ごとの順位ではない。縦軸は各図の自動範囲なので、異なる図の波の高さを画素で比較せず軸の%値を読む。線を結ぶ表示補間は推定器の追加フィットではなく、RMSEは図のサンプルではなく元の721点で計算している。''','curve-shapes')]
    for measure, suffix, title in [('zero','z','ゼロ金利'), ('forward','f','瞬間フォワード'), ('short','z','短期ゼロ金利 ≤2年')]:
        for label, models in groups:
            id=f'train-{measure}-{label.lower()}'
            interpretation = ('短期の差を拡大すると、半年単位の表現や端点の影響を見分けやすい。全体RMSEだけでは隠れる誤差を確認する図。' if measure=='short' else
                'フォワードは共通の数値微分 f=d[Tz(T)]/dT で再計算した。ゼロ金利の小さな傾きの差が、こちらでは大きく見えることがある。候補の出力フォワード列そのものではない。' if measure=='forward' else
                '真値との差がどの満期に集中するかを見る。滑らかさだけでは正確さは判断できず、価格再現・年限別誤差と併せて読む。')
            train_blocks += [prose(id+'-reading',f'**{label}群・{title}。** '+interpretation,'curve-shapes'),
                chart(id,f'公開データ較正後の{title}：{label}群','改善後。真値を含む同じ満期格子での比較。','shape-main-short' if measure=='short' else 'shape-main', ['真値 benchmark '+suffix]+[m.title()+' '+suffix for m in models],'curve-shapes')]
    train_blocks.append(prose('pricing-split-heading','''### 同じ市場の非公開商品：再フィットなしの価格予測

公開136商品と非公開24商品は商品IDで重ならず、同じ推定カーブを価格付けへ適用した。次表の「公開側」も誤差の相手は汚染された観測値でなく**採点側の無雑音の真値価格・金利**。候補自身の学習損失とは異なる。意図的な単位誤りをそのまま比較すると公平な適合度にならないためである。

預金・OISはbp、債券は額面100あたりの価格単位に分離した。支払規約は元の採点器と同じで、既述の規約不整合の留保は残る。''','curve-shapes'))
    for split, label in [('train','公開側'), ('test','非公開ホールドアウト')]:
        train_blocks.append(table('pricing-'+split, f'{label}の真値に対する商品別RMSE',
            f"預金{pricing_rows[0][split+'_deposit_n']}・OIS{pricing_rows[0][split+'_swap_n']}・債券{pricing_rows[0][split+'_bond_n']}商品。全候補で同じ商品集合。",
            [dict(model=r['model'],deposit=round(r[split+'_deposit'],4),swap=round(r[split+'_swap'],4),bond=round(r[split+'_bond'],4)) for r in pricing_rows],
            [('model','モデル','text'),('deposit','預金 bp','number'),('swap','OIS bp','number'),('bond','債券 価格単位','number')],'pricing-split'))
    insert_after('precision-limits', train_blocks)

    test_blocks = [prose('test-shapes-heading','''## 3A. 非公開テストのカーブ：10条件を選別せず比較する

ここでは各シナリオの観測で最終提出の推定器を**個別に再較正**した。公開市場のカーブをそのまま外挿する試験ではなく、別の市場形状・データ汚染に対するアルゴリズムの耐性試験である。真値はフィットに渡していない。シナリオ名を知ったうえで手法を再調整することもしていない。

良かった例だけを選ばず10条件すべてのゼロ金利を掲載する。ゼロ曲線の小さな波はフォワードで拡大するため、前節のフォワードRMSE表も併読する。各図のソースデータには共通方式のフォワード値も保持。''','curve-shapes')]
    scenario_rows=b.read(f'{new}/scenario_comparison.json')
    for sid in cases[1:]:
        entries=[r for r in scenario_rows if r['scenario']==sid]
        best=min(entries,key=lambda r:r['zero_final']); worst=max(entries,key=lambda r:r['zero_final'])
        for label, models in groups:
            id=f'test-{sid}-{label.lower()}'
            reading=f"**{sid}・{names[sid]}／{label}群。** この条件の全7モデルのゼロRMSEは最小{best['model'].title()} {best['zero_final']:.2f}bp、最大{worst['model'].title()} {worst['zero_final']:.2f}bp。真値から離れる満期を確認し、条件間の差は各軸の実数値で比較する。"
            if sid in ['s08','s09']:
                terra=next(r for r in entries if r['model']=='terra')
                reading+=f" Terraは初回比{terra['zero_delta']:+.3f}bp悪化した条件であり、平均改善の例外。"
            test_blocks += [prose(id+'-reading',reading,'curve-shapes'),chart(id,f'{sid} {names[sid]}：{label}群のゼロ金利','改善後の再較正カーブと採点側の真値。','shape-'+sid,['真値 benchmark z']+[m.title()+' z' for m in models],'curve-shapes')]
    insert_after('scenario-changes-block', test_blocks)

    approach_rows = [
        ('Astra','z(log(1+T)) の自然3次スプライン','Huber＋年限グループ検証','長期ノット・罰則・端点を試すが不採用','推定器維持。形式・説明を補修','長期誤差が残る'),
        ('Sol','一定利回り→半年集約→PCHIP','公開ホールドアウトで高度案を棄却','集約解除は短期改善と他指標悪化が競合','基準推定器を維持','短期情報圧縮・利回り≠ゼロ'),
        ('Terra','対数割引係数の自然3次スプライン','ロバスト適合＋局所フォワード罰則','15年以降の平滑化倍率を比較','長期倍率0.5を採用','10条件中8改善、2悪化'),
        ('Luna','区分線形ゼロ金利','ロバスト全商品適合・5%許容ゲート','ノット・罰則を検討','出力フォワードのみ解析式化','ゼロ不変・初回出力上書き'),
        ('Sonnet','区分線形ゼロ金利の全商品LS','公開ホールドアウトで基準を選択','短期検証不足・ノットの跳びを診断','数値推定器は維持','短期・フォワード誤差が残る'),
        ('Opus','瞬間フォワード3次スプラインを積分','商品別スケール・Huber→Tukey・ブロックCV','疎な汚染条件で1-SE・罰則下限を比較','安全条件で棄却、推定器維持','頑健性の失敗例は未解消'),
        ('Fable','瞬間フォワードBスプラインを積分','年限罰則・整合クラスタ保護・5-fold CV','疎なfold、孤立短期観測、支払規約を検証','単独クラスタ保護＋例外修正','共通10条件の精度効果は不変')]
    db.execute('CREATE TABLE approach_records(model TEXT, representation TEXT, selection TEXT, experiment TEXT, adopted TEXT, remaining TEXT)')
    db.executemany('INSERT INTO approach_records VALUES(?,?,?,?,?,?)',approach_rows)
    approach_sql='SELECT model, representation, selection, experiment, adopted, remaining FROM main.approach_records ORDER BY model;'
    b.check(len(db.execute(approach_sql).fetchall())==7,'Seven source-reviewed approach records')
    approach_source=dict(id='approaches',label='7モデルの手法・選択・採用変更の比較',path='evaluations/feedback-round-01-report/report_extensions.py',query=dict(
        engine='SQLite',language='sql',sql=approach_sql,
        description='Source-reviewed qualitative coding of candidate methods and adoption decisions. These rows summarize code and experiment records, not measured quantitative evidence. Source-specific profiles and owner scores remain distinct.',
        tables_used=['main.approach_records','evaluations/feedback-round-01-report/curve_cost_context.sqlite','evaluations/feedback-round-01-report/report_extensions.py']+
          next(s for s in artifact['manifest']['sources'] if s['id']=='methods')['query']['tables_used']+[f'{new}/combined_summary.json']))
    artifact['manifest']['sources'].append(approach_source); artifact['sources'].append(approach_source) if artifact['sources'] is not artifact['manifest']['sources'] else None
    approach_blocks=[prose('approach-comparison-heading','''### アプローチ横断比較：表現、選択基準、採用変更

Opus/Fableはフォワードを直接表現し、Astra/Terraは滑らかな別の曲線量を表現する。Sol/Luna/Sonnetも同じ「単純モデル」ではなく、商品利回りの集約と全商品同時適合は異なる。**採用しなかった実験を「未実装」とは数えない**。改善の判断基準と、その判断が共通評価に移ったかを分ける。''','methods'),
        table('approach-specification','曲線表現とモデル選択','最終採用された推定器。同じ系列名でも損失・罰則・検証方式が異なる。',
              [dict(model=x[0],representation=x[1],selection=x[2]) for x in approach_rows],
              [('model','モデル','text'),('representation','何を表現するか','text'),('selection','損失・選択基準','text')],'approaches'),
        table('approach-adoption','改善ラウンドの実験・採用・残る制約','候補の実験記録と共通の最終採点を区別して照合。',
              [dict(model=x[0],experiment=x[3],adopted=x[4],remaining=x[5]) for x in approach_rows],
              [('model','モデル','text'),('experiment','実験したこと','text'),('adopted','最終採用','text'),('remaining','共通評価・制約','text')],'approaches')]
    insert_after('methods-heading', approach_blocks)

    summaries=b.read(f'{new}/combined_summary.json'); usage=b.read(f'{new}/usage_cost_snapshot.json')
    u={r['model']:r for r in usage['summaries']}
    db.execute('CREATE TABLE cost_inputs(summary TEXT, usage TEXT)')
    db.executemany('INSERT INTO cost_inputs VALUES(?,?)',[(json.dumps(r),json.dumps(u[r['key']])) for r in summaries])
    cost_sql='''SELECT json_extract(summary,'$.model') AS model,
 json_extract(usage,'$.initial.usd_standard')+json_extract(usage,'$.feedback_all.usd_standard') AS cost,
 json_extract(usage,'$.initial.work_minutes')+json_extract(usage,'$.feedback_all.work_minutes') AS minutes,
 json_extract(summary,'$.zero_final') AS main_bp,
 json_extract(summary,'$.scenario_zero_final') AS test_bp,
 json_extract(summary,'$.scenario_forward_final') AS forward_bp,
 json_extract(summary,'$.additional_usd') AS extra_cost,
 json_extract(summary,'$.zero_initial')-json_extract(summary,'$.zero_final') AS gain_bp,
 (json_extract(summary,'$.zero_initial')-json_extract(summary,'$.zero_final'))/json_extract(summary,'$.additional_usd') AS gain_per_dollar,
 10 AS scenarios,
 json_extract(usage,'$.initial.total_tokens')+json_extract(usage,'$.feedback_all.total_tokens') AS tokens
FROM main.cost_inputs;'''
    efficiency=[]
    for r in summaries:
        v=u[r['key']]
        efficiency.append(dict(model=r['model'],cost=v['initial']['usd_standard']+v['feedback_all']['usd_standard'],
            minutes=v['initial']['work_minutes']+v['feedback_all']['work_minutes'], main_bp=r['zero_final'],test_bp=r['scenario_zero_final'],
            forward_bp=r['scenario_forward_final'],extra_cost=r['additional_usd'],gain_bp=r['zero_initial']-r['zero_final'],
            gain_per_dollar=(r['zero_initial']-r['zero_final'])/r['additional_usd'],scenarios=10,
            tokens=v['initial']['total_tokens']+v['feedback_all']['total_tokens']))
    sql_efficiency=[dict(r) for r in db.execute(cost_sql)]
    b.check(sql_efficiency==efficiency,'SQL cost and accuracy join matches independent Python calculation')
    efficiency=sql_efficiency
    def frontier(fields):
        return [r['model'] for r in efficiency if not any(all(q[k]<=r[k]+1e-12 for k in fields) and any(q[k]<r[k]-1e-12 for k in fields) for q in efficiency)]
    main_front=frontier(['cost','main_bp']); test_front=frontier(['cost','test_bp']); time_front=frontier(['cost','test_bp','minutes'])
    for r in efficiency:
        r['main_frontier']='残る' if r['model'] in main_front else '他候補が両指標で優位'
        r['test_frontier']='残る' if r['model'] in test_front else '他候補が両指標で優位'
    data['efficiency']=efficiency
    b.save(root/new/'cost_performance.json',dict(rows=efficiency,main_frontier=main_front,test_frontier=test_front,price_time_test_frontier=time_front,
        definition='Pareto set minimizes cost and RMSE (and optionally work minutes). One observation per model, no statistical generalization. Costs are cumulative Standard API equivalents.'))
    costsource=dict(id='efficiency',label='最終精度と累計・追加費用の照合',path=f'{new}/cost_performance.json',query=dict(engine='SQLite',language='sql',sql=cost_sql,
        description='One row per model: cumulative original+feedback Standard USD and work minutes joined to frozen final public/hidden RMSE. Pareto candidates have no other model weakly better in every selected metric and strictly better in at least one. No score-per-dollar composite.',
        tables_used=[f'{new}/combined_summary.json',f'{new}/usage_cost_snapshot.json',f'{new}/cost_performance.json','evaluations/feedback-round-01-report/report_extensions.py','main.cost_inputs','evaluations/feedback-round-01-report/curve_cost_context.sqlite'],
        metric_definitions=['API USD equivalent, not subscription invoice or curve-inference operating cost.',
            'Main accuracy = whole-grid zero RMSE. Test accuracy = arithmetic mean of zero RMSE across 10 scenarios.',
            'Additional efficiency = (initial minus final main zero RMSE in bp) / feedback additional USD; no effect on this metric does not mean bug fixes have no value.',
            'Seven individually labeled observations; no regression or fictitious independent observations.']))
    artifact['manifest']['sources'].append(costsource); artifact['sources'].append(costsource) if artifact['sources'] is not artifact['manifest']['sources'] else None
    cost_blocks=[prose('efficiency-heading',f'''## 6A. コスパ：低コストはLuna、テスト精度重視ではFableが比較候補

**累計費用と非公開10条件の平均ゼロRMSEを同時に見ると、パレート候補は{'・'.join(test_front)}。** ここでのパレート候補は「他の候補が費用も誤差も同等以下で、少なくとも片方が良い」という状態にないモデルを指す。主データのゼロRMSEを基準にすると{'・'.join(main_front)}が残る。目的の精度指標で結論が変わる。

完成品の価値は**初回＋改善追加の累計費用**で比較する。追加分だけと最終品質を割り算すると、初回の開発費を無視してしまう。横軸は累計USD、縦軸は誤差bpで、左下ほど少ない費用で小さい誤差。7点を全てモデル名で示し、回帰線や能力の一般順位は作らない。''','efficiency')]
    for metric,label in [('main_bp','主データ'),('test_bp','非公開10条件平均')]:
        id='efficiency-'+metric
        if metric=='test_bp':cost_blocks.append(prose(id+'-reading','非公開条件の平均ではFableが最小誤差。Opusは主データではFableより小さい誤差だが、この10条件の平均では逆転する。「品質」をどの範囲で測るかがコスパの判断を左右する。','efficiency'))
        block=chart(id,f'累計API換算費用と{label}ゼロRMSE','各モデル1実行。左下ほど費用・誤差が小さい。','efficiency',[], 'efficiency', kind='scatter')
        spec=added_charts[-1];spec['unit']='bp'
        spec['encodings']=dict(x=dict(field='cost',type='quantitative',label='累計費用（USD）'),y=dict(field=metric,type='quantitative',label='ゼロRMSE（bp）'),label=dict(field='model',type='nominal'),tooltip=[dict(field=k,type='quantitative') for k in ['minutes','tokens','forward_bp']])
        spec['labels']={'values':'all'};spec['palette']={'kind':'identity','name':'blue'};spec.pop('legend')
        spec['surface']['interactiveLegend']=False;cost_blocks.append(block)
    cost_blocks.append(table('efficiency-table','累計コスト・時間と最終精度','Standard API換算。主＝主データ、テスト＝非公開10条件の平均。',
        [dict(model=r['model'],cost=round(r['cost'],2),minutes=round(r['minutes'],2),main=round(r['main_bp'],3),test=round(r['test_bp'],3),front=r['test_frontier']) for r in efficiency],
        [('model','モデル','text'),('cost','累計 USD','number'),('minutes','作業 分','number'),('main','主 bp','number'),('test','テスト bp','number'),('front','費用×テスト精度','text')],'efficiency',('cost','asc')))
    cost_blocks.append(prose('efficiency-time-reading',f'''**時間も含めると候補は変わる。** 累計費用・テスト平均誤差・累計作業時間の3軸では{'・'.join(time_front)}が残る。API換算費の最小化と、早く完成させることは同じ目的ではない。

次表は「追加費用に対して何が改善したか」。主ゼロRMSEの改善/ドルは今回Terraだけ正であり、他モデルのゼロは**この指標の改善がなかった**という意味。形式対応、クラッシュ修正、説明や監査の改善を無価値と判定する尺度ではない。得点増加/ドルは形式点の影響が大きいため、推定精度のコスパには使わない。''','efficiency'))
    cost_blocks.append(table('marginal-efficiency','追加費用と主カーブ精度の改善幅','改善幅＝初回RMSE−最終RMSE。正が改善。累計費用ではなく追加ラウンドのみ。',
        [dict(model=r['model'],cost=round(r['extra_cost'],3),gain=round(r['gain_bp'],4),efficiency=round(r['gain_per_dollar'],4)) for r in efficiency],
        [('model','モデル','text'),('cost','追加 USD','number'),('gain','改善 bp','number'),('efficiency','改善 bp/USD','number')],'efficiency',('efficiency','desc')))
    cost_blocks.append(prose('efficiency-limits','''API換算は9月5日確認のStandard単価を再利用し、定額プランの請求・税・為替・ローカル計算費を含まない。GPTをFast料金とする既述の感度計算でも、今回の費用×テスト平均誤差の候補集合は変わらない。1モデル1実行なので、同じ費用をもう一度使えば同じ品質になる保証はない。推定器を完成後に何回利用するかによる償却や、本番でのカーブ較正速度はこのコスパの対象外。''','efficiency'))
    fast=[]
    for r in efficiency:
        q=dict(r);q['cost']*=2 if r['model'].lower() in methods[:4] else 1;fast.append(q)
    fast_front=[r['model'] for r in fast if not any(q['cost']<=r['cost'] and q['test_bp']<=r['test_bp'] and (q['cost']<r['cost'] or q['test_bp']<r['test_bp']) for q in fast)]
    b.check(fast_front==test_front,'Fast price sensitivity: same cost/test Pareto candidates')
    insert_after('rates-block', cost_blocks)
    artifact['manifest']['charts'].extend(added_charts);artifact['manifest']['tables'].extend(added_tables)
    b.CHART_MAP.extend(chart_notes)
    b.check(len(data)<=50 and all(len(x)<=2000 for x in data.values()),'Extended report dataset bounds')
    b.check(len(json.dumps(artifact,ensure_ascii=False).encode())<3_000_000,'Extended artifact below 3 MB')
    b.save(here/'extension_validation.json',dict(captured_curves=77,additional_charts=len(added_charts),additional_tables=len(added_tables),
        curve_sampling=quality,main_frontier=main_front,test_frontier=test_front,time_frontier=time_front,
        payload_bytes=len(json.dumps(artifact,ensure_ascii=False).encode()),chart_map=chart_notes))
    (here/'curve_cost_queries.sql').write_text('\n\n'.join([shape_sql,pricing_sql,approach_sql,cost_sql])+'\n')
    db.commit()
    with sqlite3.connect(here/'curve_cost_context.sqlite') as disk: db.backup(disk)
    db.close()


def companion_notebook(b):
    """Executable stdlib audit cells; no Jupyter dependencies required to review."""
    title='## tl;dr\n77本のカーブの再取得、公開136商品と非公開24商品の分離、コスパの候補集合を監査する。'
    code1="""import json, math
from pathlib import Path
ROOT = Path.cwd()
if not (ROOT / 'evaluator').exists(): ROOT = ROOT.parents[1]
BASE = ROOT / 'analysis/feedback-round-01-final-20260905'
quality = json.loads((BASE/'curve_shape_quality.json').read_text())
capture = json.loads((BASE/'curve_shapes/capture_audit.json').read_text())
assert len(capture['runs']) == 77 and capture['candidates_unchanged']
assert quality['public_unique_instruments'] == 136
assert quality['holdout_instruments'] == 24 and quality['overlapping_instruments'] == 0
print('PASS: 77 retained curves; 136 public + 24 disjoint holdout instruments')
"""
    code2="""cost = json.loads((BASE/'cost_performance.json').read_text())
rows = cost['rows']
def pareto(error):
    return [r['model'] for r in rows if not any(q['cost'] <= r['cost'] and q[error] <= r[error] and (q['cost'] < r['cost'] or q[error] < r[error]) for q in rows)]
assert pareto('test_bp') == cost['test_frontier']
assert pareto('main_bp') == cost['main_frontier']
assert math.isclose(sum(r['extra_cost'] for r in rows), 66.33494834)
print('Test frontier:', pareto('test_bp'))
print('Main frontier:', pareto('main_bp'))
print('Additional cost USD:', round(sum(r['extra_cost'] for r in rows), 2))
"""
    cells=[];namespace={};count=0
    content=[('markdown',title),('markdown','## Context & Methods\n### Key Assumptions\n固定提出物のAPI換算開発費と誤差を比較。隠し条件ごとに再較正。定額請求や本番利用費ではない。グラフは間引き、RMSEは全格子。'),
       ('markdown','## Data\n元データと再実行方法はcapture_curves.py、計算はreport_extensions.py。監査結果のパスを以下で参照。'),('code',code1),('markdown','## Results'),('code',code2),
       ('markdown','## Takeaways\nコスト×テスト平均誤差ではLuna/Fable、主データ精度ではOpusも候補。1回の実行結果であり一般能力順位ではない。')]
    for typ,source in content:
        cell=dict(cell_type=typ,metadata={},source=source.splitlines(keepends=True),id=f'cell-{len(cells)+1}')
        if typ=='code':
            count+=1;buffer=io.StringIO()
            with contextlib.redirect_stdout(buffer):exec(compile(source,'curve_cost_audit.ipynb','exec'),namespace)
            cell.update(execution_count=count,outputs=[dict(output_type='stream',name='stdout',text=buffer.getvalue().splitlines(keepends=True))])
        cells.append(cell)
    b.save(b.HERE/'curve_cost_audit.ipynb',dict(nbformat=4,nbformat_minor=5,cells=cells,
        metadata=dict(kernelspec=dict(display_name='Python 3',language='python',name='python3'),language_info=dict(name='python',version=sys.version.split()[0]),
            execution_note='Code cells executed sequentially in a fresh Python namespace by the report builder; Jupyter kernel runner not installed.')))
