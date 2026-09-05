from pathlib import Path
import json
R=Path(__file__).resolve().parent.parent
p=R/'submission/src/quantcurve/reporting.py'
s=p.read_text()
for jp,en in [('手法','Methodology'),('データ品質','Data Quality'),('単純モデルと高度モデルの比較','Model Comparison'),('感度分析と安定性','Sensitivity Analysis'),('検証とリプライシング','Validation and Repricing'),('主要チャート','Charts'),('制約とモデルリスク','Limitations'),('推奨する次の検証','Recommended Next Steps')]:
    s=s.replace(f'<h2>{jp}</h2>',f'<h2>{jp} / {en}</h2>')
s=s.replace('ゼロ金利の2階微分の二乗積分に罰則を加えます。','bpで表したゼロ金利の、x=log(1+T) に関する2階微分の二乗積分に罰則を加えます。')
s=s.replace('および <code>logs/test_run_*.json</code>','に記録した監査ログ')
p.write_text(s)
print('Updated eight remaining bilingual headings, penalty units and log reference.')
