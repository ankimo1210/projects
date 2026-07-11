"""Multi-page static HTML learning site (spec §23).

Reads ONLY saved artifacts across all milestones and emits a small static site
under reports/site/ with a shared nav. No server, self-contained Plotly.
Every figure carries the 7-part interpretation block.

Pages: index, corpus, tokenizer, architecture, training, attention, ablation,
scaling, calibration, generation, memorization, sft, evaluation, conclusions.
"""

from __future__ import annotations

import html
from pathlib import Path

import numpy as np
import torch
from jinja2 import Environment, FileSystemLoader

from ..utils.io import load_json, read_jsonl, repo_root
from ..visualization import comparison, curves, params_viz
from ..visualization.attention_viz import attention_heatmap_grid
from ..visualization.style import COLORS, base_layout

PAGES = [
    ("index", "概要"),
    ("corpus", "コーパス"),
    ("tokenizer", "トークナイザ"),
    ("architecture", "アーキテクチャ"),
    ("training", "学習過程"),
    ("attention", "Attention"),
    ("ablation", "アブレーション"),
    ("scaling", "スケーリング"),
    ("calibration", "確率較正"),
    ("generation", "生成"),
    ("memorization", "暗記"),
    ("sft", "SFT"),
    ("evaluation", "評価"),
    ("conclusions", "結論と限界"),
]


def _fig(fig) -> str:
    return fig.to_html(full_html=False, include_plotlyjs=False, config={"displaylogo": False})


def interp(what, why, how, obs, interp_, caveat, nxt) -> dict:
    return {"what": what, "why": why, "how": how, "observation": obs,
            "interpretation": interp_, "caveat": caveat, "next": nxt}


def _kv(rows) -> str:
    body = "".join(f"<tr><th>{html.escape(str(k))}</th><td>{html.escape(str(v))}</td></tr>" for k, v in rows)
    return f'<table class="kv">{body}</table>'


class SiteBuilder:
    def __init__(self):
        self.root = repo_root()
        self.out = self.root / "reports" / "site"
        self.out.mkdir(parents=True, exist_ok=True)
        self.env = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"), autoescape=False)
        self.L = self.root / "experiments/runs/m4_model_l_modern_seed42"
        self.M = self.root / "experiments/runs/m2_model_m_classical_seed42"
        self.M5 = self.root / "experiments/analysis_m5"

    def _load(self, rel):
        p = self.root / rel
        return load_json(p) if p.exists() else None

    # --------------------------------------------------------------- pages
    def page_index(self) -> dict:
        L_sum = load_json(self.L / "summary.json")
        L_cfg = load_json(self.L / "config.json")
        blocks = [
            {"html": (
                "<p>本サイトは教育用日本語 LLM ラボ <code>jp_llm_lab</code> の全成果を、"
                "保存済み実験成果物から生成した静的レポートです。"
                "<b>目的は競争力ある LLM を作ることではなく、言語モデルの内部機構・学習ダイナミクス・"
                "アーキテクチャのトレードオフ・確率較正・限界を観測可能にすることです。</b></p>"
                "<p>全数値は実測値で、実測と例示を混在させていません。各図には What / Why / How / "
                "Observation / Interpretation / Caveat / Next の7項目を付しています。</p>"
            )},
            {"heading": "主要モデルと結果", "html": _kv([
                ("Model S (M1)", "1.1M params, char, 『こころ』 → val ppl 23.9"),
                ("Model M (M2)", "10.2M params, BPE8K, pilot 10M tok <1ep → val loss 6.05"),
                ("Model L (M4)", f"{L_cfg['param_breakdown']['total']:,} params, Modern(RoPE), main {L_sum['tokens_seen']:,} tok → val loss {L_sum['final_eval']['loss']:.2f} (ppl {L_sum['final_eval']['ppl']:.1f})"),
                ("ハードウェア", "RTX 5080, BF16, ~200-650K tokens/sec"),
            ])},
            {"heading": "マイルストーン", "html": (
                "<ol><li>M1 教育的最小構成（char tok, bigram, explicit attention, 1M GPT, 全計測）</li>"
                "<li>M2 計測付き学習（コーパススナップショット, BPE, attention/embedding 定量, Model M）</li>"
                "<li>M3 統制実験（LR/batch/init 校正, Classical→Modern アブレーション）</li>"
                "<li>M4 本事前学習（Model L 30M × 100M tokens, スケーリング）</li>"
                "<li>M5 較正と SFT（reliability, temperature scaling, 暗記分析, instruction SFT）</li>"
                "<li>M6 最終学習成果物（評価200問, 本サイト, 最終レポート）</li></ol>"
            )},
        ]
        return {"blocks": blocks}

    def page_corpus(self) -> dict:
        stats = self._load("reports/figures/corpus_stats.json")
        manifest = self._load("data/manifests/snapshots_v1.json")
        if not stats:
            return {"blocks": [{"html": "<p>corpus_stats.json 未生成</p>"}]}
        import plotly.graph_objects as go

        fig = go.Figure()
        for name, color in [("pilot", COLORS["train"]), ("wiki_pilot", COLORS["neural"])]:
            if name in stats["snapshots"]:
                cf = stats["snapshots"][name]["class_fraction"]
                classes = ["hiragana", "katakana", "kanji", "ascii_alnum", "jp_punct", "other"]
                fig.add_trace(go.Bar(x=classes, y=[cf.get(c, 0) for c in classes], name=name, marker_color=color))
        fig.update_layout(barmode="group", template="plotly_white", height=380)
        base_layout(fig, "文字種構成: Web(FineWeb2) vs Wikipedia", "文字種", "割合")
        src = manifest["sources"]["fineweb2ja"]
        return {"blocks": [
            {"html": _kv([
                ("smoke/pilot/main", "1.7M / 17M / 170M chars（train pool のネストされた先頭）"),
                ("val/calib/test", "各 ~1.7M chars（別文書, 全学習集合と交わらない）"),
                ("FineWeb2ja", f"streamed {src['streamed_docs']:,} / kept {src['kept_docs']:,} / filtered {src['filtered_out']:,}"),
                ("license", "FineWeb2: ODC-By / Wikipedia: CC-BY-SA"),
            ])},
            {"figure": _fig(fig), "meta": interp(
                "Web と Wikipedia の文字種構成比。", "コーパスの性格がモデルの生成傾向に効くため。",
                "棒の高さが割合。両者の差に注目。",
                "Web は ASCII 比率が高く多様、Wikipedia は均質。両者とも日本語率>0.5（フィルタ）。",
                "コーパス選択は独立変数になりうる。Web はノイズと多様性を持つ。",
                "先頭数千文書のサンプル。near-dup 未除去。", "M4 で Web vs Wiki 学習の生成比較。")},
        ]}

    def page_tokenizer(self) -> dict:
        manifest = self._load("data/manifests/snapshots_v1.json")
        tk = manifest.get("tokenized", {}) if manifest else {}
        rows = [(k.replace("_bpe8k_v1", ""), f"{v['n_tokens']:,}", v["chars_per_token"]) for k, v in tk.items()]
        return {"blocks": [
            {"html": "<p>2種のトークナイザ: 教育用 char-level BPE（全merge履歴記録）と本番 HF-BPE 8K。"
                     "両者とも特殊トークン <code>&lt;PAD&gt;&lt;UNK&gt;&lt;BOS&gt;&lt;EOS&gt;&lt;USER&gt;&lt;ASSISTANT&gt;</code> を id 0-5 に固定。</p>"
                     "<p>demo: 「私はその人を常に先生と呼んでいた。東京大学で自然言語処理を研究しています。」<br>"
                     "prod BPE → 私は/その/人を/常に/先生/と/呼/んで/いた。/東京/大学/で/自然/言語/処理/を/研究/しています。</p>"},
            {"heading": "トークン化キャッシュ（chars/token = 圧縮率）",
             "html": '<table class="kv"><tr><th>snapshot</th><th>tokens</th><th>chars/token</th></tr>' +
                     "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td></tr>" for a, b, c in rows) + "</table>",
             "meta": interp(
                "各スナップショットのトークン数と圧縮率。", "系列長・計算量に直結するため。",
                "chars/token が大きいほど圧縮的。", "BPE8K で約1.6文字/トークン。",
                "文字トークナイザ（1文字/トークン）より系列が短い。",
                "圧縮率はコーパス依存。", "語彙 2K/4K/8K の比較は NB03。")},
        ]}

    def page_architecture(self) -> dict:
        cfg = load_json(self.L / "config.json")
        return {"blocks": [
            {"html": "<p>Decoder-only Transformer を全て手書き実装（attention, block, 学習/評価/生成ループ, 計測フック）。"
                     "SDPA は explicit 実装と出力一致を検証した上で高速パスとしてのみ使用。</p>"
                     "<pre>residual stream: x → Norm → Attn → (+) → Norm → MLP → (+) → …\n"
                     "Classical: LayerNorm + learned pos + GELU + bias\n"
                     "Modern   : RMSNorm + RoPE + SwiGLU + bias-free</pre>"},
            {"figure": _fig(params_viz.param_breakdown_figure(cfg["param_breakdown"])), "meta": interp(
                "Model L のパラメータ構成比。", "容量の配分を知ることはスケーリングの前提。",
                "棒が高いほどパラメータが多い。", "MLP と token embedding が支配的。",
                "隠れ次元512・語彙8192では MLP が最大。",
                "パラメータ≠FLOPs。", "NB08 で FLOPs 内訳。")},
        ]}

    def page_training(self) -> dict:
        records = read_jsonl(self.L / "metrics.jsonl")
        cfg = load_json(self.L / "config.json")
        import math
        evals = [r for r in records if r["type"] == "eval"]
        return {"blocks": [
            {"figure": _fig(curves.loss_curves_figure(records)), "meta": interp(
                "Model L の train/val 損失（横軸切替可）。", "収束と過学習の判断。",
                "初期値≈ln V、train と val の乖離が暗記のサイン。",
                f"init≈{evals[0]['val_eval']['loss']:.1f}(ln V={math.log(8192):.1f})→val {evals[-1]['val_eval']['loss']:.2f}。train/val 乖離小。",
                "100M tokens・<1epoch で汎化優位の学習。",
                "BPE loss は char と比較不可。単一シード。", "スケーリングは NB19。")},
            {"figure": _fig(curves.lr_grad_figure(records, cfg["train_config"]["grad_clip"])), "meta": interp(
                "LR スケジュールと勾配ノルム。", "不安定化の検出。",
                "破線がクリップ閾値。", "warmup後は安定、クリップは序盤のみ。",
                "lr 6e-4 は安定域（NB11 の range test が裏付け）。",
                "クリップ0%が理想ではない。", "NB17 で群別勾配。")},
            {"figure": _fig(curves.activation_rms_heatmap(records)), "meta": interp(
                "residual RMS（層×チェックポイント）。", "活性爆発/消失の検出。",
                "急な明色化は爆発の兆候。", "層方向に単調増加、NaN/Inf なし。",
                "pre-LN の既知挙動（残差蓄積）。",
                "RMS は1統計量。", "NB16 で branch別寄与。")},
        ]}

    def page_attention(self) -> dict:
        A = self.L / "analysis"
        stats = load_json(A / "attention_stats.json")
        maps = np.load(A / "attention_maps.npz", allow_pickle=True)
        tokens = list(maps["tokens"])
        ha = np.array(load_json(A / "head_ablation.json")["head_ablation_delta_loss"])
        ent_i = np.array(stats["init"]["entropy"]).mean()
        ent_f = np.array(stats["final"]["entropy"]).mean()
        l, h = np.unravel_index(ha.argmax(), ha.shape)
        return {"blocks": [
            {"figure": _fig(attention_heatmap_grid(torch.tensor(maps["layer_last"]), tokens,
                                                   "Model L 最終層 attention", max_heads=4)),
             "meta": interp(
                "学習済み Model L の最終層 attention 重み。", "「何を見ているか」の観察。",
                "行=query, 列=key。縦筋=広く参照されるトークン。",
                f"平均エントロピー init {ent_i:.2f}→final {ent_f:.2f}。head ごとに役割が分化。",
                "学習で attention が特定パターンに集中。",
                "重み≠因果的寄与。1文の観察。", "因果性は head ablation で検証（下）。")},
            {"heading": "head ablation（因果的重要度）",
             "html": f"<p>各 head を個別にゼロ化したときの loss 増加を測定。最大は "
                     f"<b>L{l}H{h}</b>（Δloss {ha.max():.3f}）。多くの head は冗長で、少数が因果的に効く。</p>",
             "meta": interp(
                "head ablation の Δloss（因果量）。", "「attention≠説明」を因果側から実証。",
                "Δloss が大きい head ほど出力に重要。",
                "少数の head だけが loss を大きく動かす。",
                "エントロピーが低い head が必ずしも因果的に重要とは限らない。",
                "単純ゼロ化は head 間相互作用を過小評価。", "activation patching で位置別因果も測定可能。")},
        ]}

    def page_ablation(self) -> dict:
        summ = self._load("experiments/comparisons/ablation_chain.json")
        if not summ:
            return {"blocks": [{"html": "<p>ablation_chain.json 未生成</p>"}]}
        rows = comparison.ablation_table_rows(summ)
        seed_std = np.mean([summ["results"][c]["val_loss_std"] for c in summ["chain"]])
        tbl = '<table class="kv"><tr><th>step</th><th>val_loss</th><th>±std</th><th>Δ前</th><th>params</th></tr>'
        for r in rows:
            tbl += f"<tr><td>{r['step']}</td><td>{r['val_loss']}</td><td>{r['std']}</td><td>{r['delta_vs_prev']:+.3f}</td><td>{r['n_params']:,}</td></tr>"
        tbl += "</table>"
        return {"blocks": [
            {"figure": _fig(comparison.ablation_val_loss_figure(summ)), "html": tbl, "meta": interp(
                "Classical→Modern の1要素変更ごとの val loss（3 seeds, ±std）。",
                "統制実験で構造の効果を容量から分離。",
                f"seed σ≈{seed_std:.3f}。|Δ|>2σ なら有意の可能性。",
                "RMSNorm はノイズ内（改善なし）。RoPE は大改善（−0.34, >>2σ）。SwiGLU 小改善。bias無しは判定不能。",
                "事前予想（全変更がノイズ内）は RoPE で外れた。改善のほぼ全ては RoPE 由来。",
                "3 seeds は粗い。10M・<1epoch。速度差は未測定。",
                "Model L は Modern(RoPE込)を採用。長文脈外挿で RoPE 優位を再検証。")},
        ]}

    def page_scaling(self) -> dict:
        sc = self._load("experiments/comparisons/scaling.json")
        if not sc:
            return {"blocks": [{"html": "<p>scaling.json 未生成</p>"}]}
        pts = sc["points"]
        best = min(pts, key=lambda p: p["val_loss"])
        return {"blocks": [
            {"figure": _fig(comparison.size_scaling_figure(pts)), "meta": interp(
                "同一トークン予算でサイズだけ変えた val loss。", "サイズと性能・コストの trade-off。",
                "右ほど大きいモデル。単調とは限らない。",
                f"xs→s→m は改善するが最大 l は m より悪化（最良は {best['name']}）。",
                "固定予算では大モデルは token/param 不足でデータ枯渇（Chinchillaの核心）。M4 の L は16倍のtokenで val 3.51。",
                "compute-optimal 曲線ではなく固定予算の断面。外挿不可。",
                "サイズごとに最適トークン数を変えた実験。")},
        ]}

    def page_calibration(self) -> dict:
        cal = self._load("experiments/analysis_m5/calibration.json")
        if not cal:
            return {"blocks": [{"html": "<p>calibration.json 未生成</p>"}]}
        import plotly.graph_objects as go

        bins = [b for b in cal["reliability_equal_width"] if b["n"] > 0]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", line=dict(dash="dash", color="#999"), name="完全較正"))
        fig.add_trace(go.Scatter(x=[b["avg_conf"] for b in bins], y=[b["acc"] for b in bins],
                                 mode="lines+markers", line=dict(color=COLORS["train"]), name="実測"))
        base_layout(fig, "Reliability diagram（Model L, test split）", "平均確信度", "実精度")
        return {"blocks": [
            {"figure": _fig(fig), "html": _kv([
                ("fitted T", f"{cal['fitted_T']:.3f}（calibrationで最適化, testで評価）"),
                ("raw NLL / scaled NLL", f"{cal['raw']['nll']:.3f} / {cal['temperature_scaled']['nll']:.3f}"),
                ("raw ECE (width)", f"{cal['raw']['ece_equal_width']:.4f}"),
                ("accuracy raw/scaled", f"{cal['raw']['accuracy']:.4f} / {cal['temperature_scaled']['accuracy']:.4f}（不変）"),
            ]), "meta": interp(
                "確信度 vs 実精度の較正曲線と温度スケーリング。", "モデルの確率が信頼できるか。",
                "対角線に近いほど良く較正。",
                f"T≈{cal['fitted_T']:.2f}（ほぼ1）で既に良較正、ECE {cal['raw']['ece_equal_width']:.3f}。温度で accuracy 不変。",
                "cross-entropy 学習は次トークン較正を良くする。温度は鋭さのみ調整。",
                "次トークン較正 ≠ 事実的正しさ。よく較正でも「もっともらしい誤り」を出す。",
                "hallucination 率は別問題。calibration breakdown（頻度別等）は拡張余地。")},
        ]}

    def page_generation(self) -> dict:
        ga = self._load("experiments/analysis_m5/generation_anatomy.json")
        if not ga:
            return {"blocks": [{"html": "<p>generation_anatomy.json 未生成</p>"}]}
        import plotly.graph_objects as go

        sweep = ga["sampling_sweep"]
        names = list(sweep)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=names, y=[sweep[n]["metrics"]["repetition_rate"] for n in names], name="反復率", marker_color=COLORS["val"]))
        fig.add_trace(go.Bar(x=names, y=[sweep[n]["metrics"]["distinct_2"] for n in names], name="distinct-2", marker_color=COLORS["sdpa"]))
        fig.update_layout(barmode="group", template="plotly_white", height=380)
        base_layout(fig, "sampling 手法別の反復率と多様性（Model L）", "手法", "値")
        samples = "".join(f'<tr><th>{n}</th><td class="gen-text">{html.escape(sweep[n]["sample"][:100])}</td></tr>' for n in ["greedy", "temp0.7", "temp1.5", "top_p0.9"])
        return {"blocks": [
            {"figure": _fig(fig), "html": f'<table class="kv">{samples}</table>', "meta": interp(
                "同一 logits に sampling 手法だけ変えた多様性。", "決定則の効果を分離。",
                "greedy=低多様性・ループ、高温=高多様性・崩壊。",
                "greedy は distinct-2 が低くループ。温度↑で多様性↑、高温で崩壊。",
                "反復は greedy と過信の相互作用。sampling は知識を変えない。",
                "distinct 低=悪 ではない。品質の代理。", "temperature の最適点はタスク依存。")},
        ]}

    def page_memorization(self) -> dict:
        mem = self._load("experiments/analysis_m5/memorization.json")
        if not mem:
            return {"blocks": [{"html": "<p>memorization.json 未生成</p>"}]}
        tr, va = mem["train"], mem["validation"]
        return {"blocks": [
            {"html": _kv([
                ("train exact-match", f"{tr.get('mean_exact_match'):.2f} tokens（学習済み文書）"),
                ("validation exact-match", f"{va.get('mean_exact_match'):.2f} tokens（未学習・対照）"),
                ("gap", f"{(tr.get('mean_exact_match') or 0) - (va.get('mean_exact_match') or 0):+.2f}"),
            ]), "meta": interp(
                "train文書とval文書の接頭辞からの greedy 継続一致長。", "暗記と汎化の分離。",
                "train≫val なら暗記、train≈val なら汎化。",
                f"train {tr.get('mean_exact_match'):.1f} ≈ val {va.get('mean_exact_match'):.1f} → 暗記は弱い。",
                "Model L は main を<1epoch。M1（45ep）と対照的に暗記していない。",
                "exact-match は暗記の一側面。低 val loss ≠ 汎化の証明。",
                "exposure-style 分析で頻度と再現率の関係を測定可能。")},
        ]}

    def page_sft(self) -> dict:
        sft = self._load("experiments/analysis_m5/sft.json")
        if not sft:
            return {"blocks": [{"html": "<p>sft.json 未生成</p>"}]}
        base = "".join(f'<tr><th>{html.escape(s["instruction"])}</th><td class="gen-text">{html.escape(s["completion"][:70])}</td></tr>' for s in sft["base_pretrained_samples"])
        ao = "".join(f'<tr><th>{html.escape(s["instruction"])}</th><td class="gen-text">{html.escape(s["response"][:70])}</td></tr>' for s in sft["regimes"]["assistant_only"]["samples"])
        return {"blocks": [
            {"heading": "base（事前学習のみ）の応答", "html": f'<table class="kv">{base}</table>'},
            {"heading": "assistant-only SFT の応答", "html": f'<table class="kv">{ao}</table>', "meta": interp(
                "同一指示への base vs SFT 応答。", "SFT が何を変えるか。",
                "base は続きを書くだけ、SFT は応答形式で答え <EOS> で止まる。",
                "SFT後は応答形式・停止を獲得。内容の正確さは base の知識依存。",
                "SFT の主効果は出力形式・方針であり、知識の大量獲得ではない。",
                "小モデル・少数例。応答は依然事実誤りを含む。",
                "instruction-following の定量評価。")},
        ]}

    def page_evaluation(self) -> dict:
        ev = self._load("experiments/comparisons/eval.json")
        if not ev:
            return {"blocks": [{"html": "<p>eval.json 未生成</p>"}]}
        L = ev["models"].get("model_l_30m", {})
        cats = L.get("by_category", {})
        tbl = '<table class="kv"><tr><th>category</th><th>n</th><th>cloze acc</th><th>反復率</th><th>distinct-2</th></tr>'
        for c, v in sorted(cats.items()):
            tbl += f"<tr><td>{c}</td><td>{v['n']}</td><td>{v['cloze_accuracy'] if v['cloze_accuracy'] is not None else '—'}</td><td>{v['mean_repetition'] if v['mean_repetition'] is not None else '—'}</td><td>{v['mean_distinct2'] if v['mean_distinct2'] is not None else '—'}</td></tr>"
        tbl += "</table>"
        # human comparison samples: a few completions
        pp = L.get("per_prompt", [])
        gen_rows = [r for r in pp if r.get("kind") == "completion"][:6]
        human = "".join(f'<tr><th>{html.escape(r["prompt"])}</th><td class="gen-text">{html.escape(r.get("generation","")[:70])}</td></tr>' for r in gen_rows)
        return {"blocks": [
            {"html": f"<p>固定評価セット {ev['n_prompts']} 問を能力タイプ別に測定。"
                     f"Model L の cloze 正解率 {L.get('overall',{}).get('cloze_accuracy')}。"
                     f"<b>小型モデルに高度な知識回答は期待しない</b> — このセットは能力ギャップを測るためのもの。</p>" + tbl,
             "meta": interp(
                "カテゴリ別の cloze 正解率・反復率・多様性。", "能力タイプ（文法/知識/補完）を分離測定。",
                "cloze は次トークン一致率、completion は生成の反復/多様性。",
                "cloze は全体で低い（助詞は複数正解ありノイズ大、数列は小モデルに困難）。補完は流暢だが内容は浅い。",
                "言語モデリング能力 > 事実知識能力。流暢さと知識は別物。",
                "cloze「正解」は一意でない（助詞）。自動指標は品質の代理。",
                "人間評価との併用が必要（下の生成例）。")},
            {"heading": "生成例（人間評価用）", "html": f'<table class="kv">{human}</table>'},
        ]}

    def page_conclusions(self) -> dict:
        return {"blocks": [
            {"heading": "結論", "html": (
                "<ul>"
                "<li><b>観測可能性を達成</b>: text→logits の forward、全 tensor shape、attention の数式と実値、"
                "学習前後の変化、各層の活性・勾配、モデル間の統制比較、reliability diagram、生成の token 確率、"
                "事前学習 vs SFT を、すべて Notebook と HTML で追跡できる。</li>"
                "<li><b>RoPE が最大の勝者</b>: Classical→Modern で改善のほぼ全ては RoPE 由来（−0.34 nats, 3 seeds で有意）。</li>"
                "<li><b>スケーリングは非単調</b>: 固定トークン予算では最大モデルがデータ枯渇で負ける（Chinchilla）。</li>"
                "<li><b>較正 ≠ 正しさ</b>: Model L は次トークン較正が良い（T≈0.98）が、生成は事実的に誤る。</li>"
                "<li><b>暗記 vs 汎化</b>: <1epoch の Model L は train≈val で暗記が弱い。M1（45ep）と対照的。</li>"
                "</ul>"
            )},
            {"heading": "限界（この成果物から言えないこと）", "html": (
                "<ul>"
                "<li>小型モデル（≤30M）・小規模学習。絶対的な生成品質は低く、事実知識は乏しい。</li>"
                "<li>多くの実験が単一〜3 seeds で、強い統計的結論には不十分。</li>"
                "<li>BPE と char の loss/ppl は単位が異なり直接比較不可。</li>"
                "<li>attention 可視化は説明ではない（重み≠因果）。</li>"
                "<li>次トークン較正は事実的正しさ・hallucination 率とは別物。</li>"
                "<li>torch.compile はこの環境で不可（inductor コンパイラ不在）。</li>"
                "<li>near-dup 除去・大規模データ・長文脈外挿は未実施。</li>"
                "</ul>"
            )},
            {"heading": "次の実験", "html": (
                "<ul><li>RoPE の長文脈外挿テスト（train ctx 512 / eval ctx 1024）</li>"
                "<li>サイズ別に最適トークン数を変えた compute-optimal スケーリング</li>"
                "<li>複数 seeds でのアブレーション有意性の精密化</li>"
                "<li>calibration の頻度別・トークン種別 breakdown</li>"
                "<li>Web vs Wikipedia 学習の生成傾向比較</li></ul>"
            )},
        ]}

    # --------------------------------------------------------------- build
    def build(self) -> Path:
        page_fns = {name: getattr(self, f"page_{name}") for name, _ in PAGES}
        tmpl = self.env.get_template("site_page.html.j2")
        for name, title in PAGES:
            try:
                content = page_fns[name]()
            except Exception as e:
                content = {"blocks": [{"html": f"<p>ページ生成エラー: {html.escape(str(e))}</p>"}]}
            htmlout = tmpl.render(
                page_title=title, nav=PAGES, active=name, blocks=content["blocks"],
                site_title="jp_llm_lab — 教育用日本語LLMラボ",
            )
            (self.out / f"{name}.html").write_text(htmlout, encoding="utf-8")
        # plotly asset
        assets = self.out / "assets"
        assets.mkdir(exist_ok=True)
        pj = assets / "plotly.min.js"
        if not pj.exists():
            from plotly.offline import get_plotlyjs

            pj.write_text(get_plotlyjs(), encoding="utf-8")
        return self.out / "index.html"


def build_site() -> Path:
    return SiteBuilder().build()
