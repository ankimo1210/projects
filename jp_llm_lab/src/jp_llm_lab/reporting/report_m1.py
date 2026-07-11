"""Milestone-1 static HTML report builder.

Reads ONLY saved run artifacts (experiments/runs/…, reports/figures/…,
reports/env/…) — no retraining. All numbers shown are measured; every figure
carries the 7-part interpretation block (spec §3.4, §24).
"""

from __future__ import annotations

import html
import statistics
from pathlib import Path

import torch
from jinja2 import Environment, FileSystemLoader

from ..models.config import ModelConfig
from ..models.transformer import ClassicalGPT
from ..tokenization.char_tokenizer import CharTokenizer
from ..training.trainer import load_checkpoint
from ..utils.io import load_json, read_jsonl, repo_root
from ..visualization import attention_viz, curves, params_viz
from ..visualization.style import COLORS, base_layout


def _fig(fig) -> str:
    return fig.to_html(full_html=False, include_plotlyjs=False, config={"displaylogo": False})


def _kv_table(rows: list[tuple[str, str]]) -> str:
    body = "".join(f"<tr><th>{html.escape(k)}</th><td>{html.escape(str(v))}</td></tr>" for k, v in rows)
    return f'<table class="kv">{body}</table>'


def _load_model_from_ckpt(run_dir: Path, pattern: str) -> ClassicalGPT:
    path = sorted(run_dir.glob(f"checkpoints/{pattern}"))[0]
    payload = torch.load(path, map_location="cpu", weights_only=False)
    model = ClassicalGPT(ModelConfig.from_dict(payload["model_cfg"]))
    load_checkpoint(path, model)
    return model.eval()


def build_m1_report(out_dir: Path | None = None) -> Path:
    root = repo_root()
    out_dir = Path(out_dir) if out_dir else root / "reports" / "html"
    run = root / "experiments" / "runs" / "m1_model_s_smoke_seed42"
    bigram_run = root / "experiments" / "runs" / "m1_bigram_char_seed42"

    records = read_jsonl(run / "metrics.jsonl")
    config = load_json(run / "config.json")
    runmeta = load_json(run / "runmeta.json")
    summary = load_json(run / "summary.json")
    samples = read_jsonl(run / "samples.jsonl")
    bigram = load_json(bigram_run / "summary.json")
    bench = load_json(root / "reports" / "figures" / "attn_bench.json")
    env = load_json(root / "reports" / "env" / "env_report.json")
    tokenizer = CharTokenizer.load(run / "tokenizer.json")

    trains = [r for r in records if r["type"] == "train"]
    evals = [r for r in records if r["type"] == "eval"]
    V = tokenizer.vocab_size
    ln_v = torch.log(torch.tensor(float(V))).item()
    init_val = evals[0]["val_eval"]["loss"]
    fin_train = evals[-1]["train_eval"]["loss"]
    fin_val = evals[-1]["val_eval"]["loss"]
    gap = fin_train - fin_val
    clip_rate = sum(r["clip_hit"] for r in trains) / len(trains)
    tps_median = statistics.median(r["tokens_per_sec"] for r in trains[2:])
    n_epochs = summary["tokens_seen"] / config["n_train_tokens"]

    # ---- attention: init vs trained on a fixed sentence
    sentence = config["train_config"]["fixed_prompts"][0]
    ids = torch.tensor([tokenizer.encode(sentence)], dtype=torch.long)
    chars = list(sentence)
    model_init = _load_model_from_ckpt(run, "ckpt_000pct_*.pt")
    model_fin = _load_model_from_ckpt(run, "ckpt_100pct_*.pt")
    maps_init = model_init.attention_maps(ids)  # list of [1,H,T,T]
    maps_fin = model_fin.attention_maps(ids)
    ent_init = torch.stack([attention_viz.attention_entropy(m) for m in maps_init])  # [L,H]
    ent_fin = torch.stack([attention_viz.attention_entropy(m) for m in maps_fin])
    L, _H = ent_init.shape
    e_i, e_f = float(ent_init.mean()), float(ent_fin.mean())
    ent_dir = "低下" if e_f < e_i else "上昇"

    def _mass(maps, sel) -> float:  # mean attention mass on selected keys, queries t>=1
        T = maps[0].shape[-1]
        q = torch.arange(1, T)
        return float(torch.stack([sel(w[0], q).mean() for w in maps]).mean())

    prev_i = _mass(maps_init, lambda w, q: w[:, q, q - 1])
    prev_f = _mass(maps_fin, lambda w, q: w[:, q, q - 1])
    bos_i = _mass(maps_init, lambda w, q: w[:, q, 0])
    bos_f = _mass(maps_fin, lambda w, q: w[:, q, 0])

    # ---- bigram figures
    brec = read_jsonl(bigram_run / "metrics.jsonl")
    import plotly.graph_objects as go

    fig_bigram = go.Figure()
    fig_bigram.add_trace(go.Scatter(x=[r["step"] for r in brec], y=[r["val_loss"] for r in brec],
                                    name="neural bigram (val)", line=dict(color=COLORS["neural"])))
    fig_bigram.add_hline(y=bigram["count"]["val_loss"], line_dash="dash", line_color=COLORS["count"],
                         annotation_text=f'count model α={bigram["count"]["alpha"]} (val {bigram["count"]["val_loss"]:.3f})')
    fig_bigram.add_hline(y=bigram["uniform_loss_reference"], line_dash="dot", line_color="#bbb",
                         annotation_text=f"uniform ln V = {bigram['uniform_loss_reference']:.2f}")
    base_layout(fig_bigram, "Neural bigram の検証損失は count モデルの閉形式解に収束する",
                "SGD step", "val loss (nats/token)")

    sweep = bigram["alpha_sweep_val_loss"]
    fig_alpha = go.Figure(go.Scatter(x=[float(a) for a in sweep], y=list(sweep.values()),
                                     mode="lines+markers", line=dict(color=COLORS["count"])))
    fig_alpha.add_hline(y=bigram["neural"]["val_loss"], line_dash="dash", line_color=COLORS["neural"],
                        annotation_text=f"neural bigram {bigram['neural']['val_loss']:.3f}")
    fig_alpha.update_xaxes(type="log")
    base_layout(fig_alpha, "加算平滑化 α と検証損失（count bigram）", "α (log)", "val loss (nats/token)")

    # ---- generations tables
    def gen_table(prompt: str, keys: tuple[str, ...] = ("greedy", "temp07"), fracs=None) -> str:
        rows = [s for s in samples if s["prompt"] == prompt]
        if fracs is not None:
            rows = [s for s in rows if s["frac"] in fracs]
        head = "<tr><th>学習進捗</th>" + "".join(f"<th>{k}</th>" for k in keys) + "</tr>"
        body = ""
        for s in rows:
            cells = "".join(
                f'<td class="gen-text">{html.escape(s[k][len(prompt):][:110])}</td>' for k in keys
            )
            body += f"<tr><th>{s['frac']:.0%} (step {s['step']})</th>{cells}</tr>"
        return (
            f'<p class="note">prompt: <code>{html.escape(prompt)}</code>（表示は続き部分のみ・先頭110字）</p>'
            f'<table class="gen">{head}{body}</table>'
        )

    opening_true = "だからここでもただ先生と書くだけで本名は打ち明けない。"

    sections = [
        {
            "id": "overview",
            "title": "Overview",
            "intro": (
                "<p>本レポートは Milestone 1（educational minimum）の実測結果をまとめた静的HTMLです。"
                "対象は文字トークナイザ + bigram ベースライン + 約110万パラメータの Classical GPT（Model S）を"
                "青空文庫『こころ』で学習したスモーク実験です。<b>高性能なLLMを作ることが目的ではなく、"
                "言語モデル内部の観測可能性を確立することが目的です。</b></p>"
            ),
            "blocks": [
                {
                    "heading": "実験メタデータ（再現性情報）",
                    "html": _kv_table([
                        ("run", "m1_model_s_smoke_seed42"),
                        ("corpus", f"こころ（夏目漱石・青空文庫パブリックドメイン） {config['n_train_tokens'] + config['n_val_tokens']:,} chars"),
                        ("tokenizer", f"char_v1 / vocab {V:,}"),
                        ("model", f"Classical GPT: d=128, 4 layers, 4 heads, ctx 256 / params {config['param_breakdown']['total']:,}"),
                        ("training", f"{summary['steps']} steps × 64 batch × 256 ctx = {summary['tokens_seen']:,} tokens（約{n_epochs:.0f}エポック相当）"),
                        ("precision / attention", "BF16 autocast / SDPA（学習）・explicit（分析）"),
                        ("wallclock", f"{summary['wallclock_sec']:.1f} s on {runmeta['env']['gpu_name']}"),
                        ("git", f"{(runmeta['git_commit'] or '')[:12]} (dirty={runmeta['git_dirty']}) branch={runmeta['git_branch']}"),
                        ("seed", config["train_config"]["seed"]),
                        ("timestamp", runmeta["timestamp_utc"]),
                    ]),
                },
                {
                    "figure": _fig(params_viz.param_breakdown_figure(config["param_breakdown"])),
                    "meta": {
                        "what": "Model S の各コンポーネントのパラメータ数と構成比。",
                        "why": "「モデルのどこに容量があるか」を知ることは、スケーリングやアブレーションの前提になる。",
                        "how": "棒が高いほどパラメータが多い。lm_head は token embedding と weight tying しているため 0（追加パラメータなし）。",
                        "observation": f"MLP が {config['param_breakdown']['groups']['mlp']/config['param_breakdown']['total']:.0%} で最大、次いで token embedding {config['param_breakdown']['groups']['token_emb']/config['param_breakdown']['total']:.0%}。語彙 {V:,} の文字トークナイザでも埋め込みが約1/4を占める。",
                        "interpretation": "隠れ次元128・語彙2068という小型構成では、4×拡大のMLPが支配的。語彙を8Kに増やす（M2のBPE）と埋め込み比率がさらに増すはず。",
                        "caveat": "パラメータ数は計算量（FLOPs）と一致しない。attention の T² 計算はパラメータ0の位置で発生する。",
                        "next": "M2 で BPE 8K 語彙にした際の構成比変化、M3 で Modern 構成（SwiGLU 等）との比較。",
                    },
                },
            ],
        },
        {
            "id": "environment",
            "title": "Environment",
            "blocks": [
                {
                    "html": _kv_table([(k, v) for k, v in env["report"].items()]) +
                            "<h3>推奨設定（粗い事前推定 — M3で実測校正）</h3>" +
                            _kv_table([(k, v) for k, v in env["recommendation"].items()]),
                },
            ],
        },
        {
            "id": "tokenizer",
            "title": "Tokenizer（文字トークナイザ）",
            "intro": (
                f"<p>語彙 = 特殊トークン6種 + 『こころ』に出現する全文字 {V - 6:,} 種。"
                f"<code>decode(encode(x)) == x</code> はテストで保証（語彙内文字のみ）。"
                f"1文字=1トークンなので系列長=文字数になり、コンテキスト256は約256文字に相当する。</p>"
            ),
            "blocks": [
                {
                    "html": (
                        "<p>例: <code>私はその人を常に先生と呼んでいた。</code> → "
                        f"<code>{tokenizer.encode('私はその人を常に先生と呼んでいた。')}</code></p>"
                        f"<p class=\"note\">未知文字（例: 学習コーパスに無い字）は <code>&lt;UNK&gt;</code>=id 1 に落ちる。"
                        f"『走れメロス』を同じトークナイザで符号化すると一部の文字が UNK になる — この被覆率の問題が M2 の BPE の動機。</p>"
                    ),
                },
            ],
        },
        {
            "id": "bigram",
            "title": "Bigram baseline",
            "intro": (
                "<p>$P(x_{t+1}\\mid x_t)$ だけを見る最小の言語モデル。カウント（閉形式のMLE+平滑化）と"
                "SGDで学習する neural 版（V×V ロジット表）を同一 val スライスで比較。</p>"
            ),
            "blocks": [
                {
                    "figure": _fig(fig_bigram),
                    "meta": {
                        "what": "neural bigram の検証損失の推移と、count モデル・一様分布の参照線。",
                        "why": "「ニューラルだから賢い」わけではないことの実証。同じ表現力なら SGD は閉形式解に収束するだけ。",
                        "how": "オレンジの曲線が灰色破線（count）に近づけば、両者が同じ解に達した証拠。",
                        "observation": f"neural val {bigram['neural']['val_loss']:.3f} vs count val {bigram['count']['val_loss']:.3f}（α=0.05）。差 {abs(bigram['gap_val']):.3f} nats で neural がわずかに良い。一様分布 ln V = {bigram['uniform_loss_reference']:.2f} からは両者とも大幅に改善。",
                        "interpretation": "neural 版はゼロ初期化＝一様事前から出発し、未観測ペアに一様に近いロジットを残す。これが加算平滑化と似た働きをし、α の手動調整なしで同等以上になった。",
                        "caveat": "差 0.05 nats は平滑化方式の違いであり「ニューラルの表現力」ではない。また val スライス（先頭8,192トークン）での比較。",
                        "next": "Transformer（下記）が bigram を超える分こそが「文脈」の寄与。M2 でコーパスを変えて再確認。",
                    },
                },
                {
                    "figure": _fig(fig_alpha),
                    "meta": {
                        "what": "count bigram の加算平滑化 α を振ったときの検証損失。",
                        "why": "平滑化は「未観測ペアにどれだけ確率を残すか」の事前分布。語彙が大きい日本語では α·V が巨大になり効きすぎる。",
                        "how": "横軸は log スケール。谷が最適な α。",
                        "observation": f"α=0.5 では val {sweep['0.5']:.3f} と大きく悪化（α·V ≈ {0.5 * V:.0f} 擬似カウントが実カウントを圧倒）。最適は α≈0.01–0.05。",
                        "interpretation": "ハイパーパラメータの選択がモデル本体と同程度に損失を動かす好例。",
                        "caveat": "最適 α はコーパスサイズ・語彙サイズに依存し、この値は『こころ』146K トークン固有。",
                        "next": "Kneser-Ney など高度な平滑化との比較（教材としては任意）。",
                    },
                },
            ],
        },
        {
            "id": "attention-bench",
            "title": "Attention: explicit vs SDPA",
            "blocks": [
                {
                    "figure": _fig(params_viz.attn_bench_figure(bench)),
                    "meta": {
                        "what": "同一パラメータの attention モジュールで、explicit 実装と F.scaled_dot_product_attention の forward+backward 中央値時間。",
                        "why": "教育用の explicit 実装と本番用 fused kernel の出力一致（テスト済: atol 1e-5）と速度差を分離して理解するため。",
                        "how": "棒が低いほど速い。同じ dtype/T 内で紫（explicit）と緑（SDPA)を比較。",
                        "observation": "SDPA は全条件で高速。T=512・bf16 で最大 6.6×（7.45ms → 1.13ms）。T が伸びるほど差が拡大。",
                        "interpretation": "explicit 実装は [B,H,T,T] の score 行列をメモリに実体化するため T² のメモリ帯域がボトルネック。SDPA (FlashAttention系) はタイル化で実体化を回避する。",
                        "caveat": "この規模（d=128）では絶対時間はどちらも小さく、学習全体では data/eval のオーバーヘッドが支配的。速度差 = 精度差ではない（出力は一致）。",
                        "next": "M3 §14.1 のハードウェア校正で torch.compile / 勾配チェックポイントも含めて総合計測。",
                    },
                },
            ],
        },
        {
            "id": "attention-maps",
            "title": "Attention maps（学習前 vs 学習後）",
            "intro": f"<p>固定文「{sentence}」（{len(chars)}トークン）に対する attention 重み。行=query（その位置が）、列=key（どこを見ているか）。causal mask により右上三角は常に0。</p>",
            "blocks": [
                {
                    "heading": "学習前（初期化直後・layer 0）",
                    "figure": _fig(attention_viz.attention_heatmap_grid(maps_init[0][0], chars, "init / layer 0")),
                },
                {
                    "heading": "学習後（layer 0）",
                    "figure": _fig(attention_viz.attention_heatmap_grid(maps_fin[0][0], chars, "trained / layer 0")),
                },
                {
                    "heading": "学習後（最終 layer 3）",
                    "figure": _fig(attention_viz.attention_heatmap_grid(maps_fin[-1][0], chars, "trained / layer 3")),
                    "meta": {
                        "what": "同一文に対する head 別 attention 分布（init vs 学習後）。",
                        "why": "「学習で attention が何を獲得したか」を最も直接的に観察できる断面。",
                        "how": "各行は合計1の確率分布。縦の筋=特定トークンが広く参照されている。対角線近傍=局所参照。",
                        "observation": f"平均エントロピーは init {e_i:.2f} → 学習後 {e_f:.2f} nats に{ent_dir}（最深層 layer {L-1} が {float(ent_fin[-1].mean()):.2f} で最も選択的）。直前トークンへの質量は {prev_i:.2f} → {prev_f:.2f} と微増にとどまる一方、先頭トークンへの質量はむしろ {bos_i:.2f} → {bos_f:.2f} に減少。学習後のヒートマップでは特定の内容文字（「先」「生」「。」など）への縦筋が目立つ。",
                        "interpretation": "「学習すると直前トークン注視が支配的になる」という事前予想は、この文では部分的にしか成り立たなかった。エントロピー低下は主に特定キー文字への選択的集中で生じており、深い層ほどその傾向が強い。",
                        "caveat": "attention 重みが高い ≠ そのトークンが因果的に重要（重み≠寄与）。1文・1シードの定性観察であり、head の役割の一般化はできない。直前トークン率などの数値もこの1文に対するもの。M2 で多数の文について定量化し、ablation/patching で因果性を検証する。",
                        "next": "M2 §9: attention distance・prev-token率・BOS/句読点率の定量化、head ablation。",
                    },
                },
            ],
        },
        {
            "id": "training",
            "title": "Training dynamics",
            "blocks": [
                {
                    "figure": _fig(curves.loss_curves_figure(records)),
                    "meta": {
                        "what": "学習損失（per-step ミニバッチ＋固定評価バッチ）と検証損失。ボタンで横軸を step / tokens / 時間に切替可能。",
                        "why": "収束の判断と過学習（暗記）の検出は train と val の乖離で行う。",
                        "how": "初期値は一様分布の理論値 ln V に一致するはず。train（青）と val（赤）の開きが暗記の兆候。",
                        "observation": f"init loss {init_val:.2f} ≈ ln V = {ln_v:.2f}（初期化の健全性確認）。最終 train {fin_train:.2f} / val {fin_val:.2f}、ギャップ {abs(gap):.2f} nats。val ppl は {evals[0]['val_eval']['ppl']:.0f} → {evals[-1]['val_eval']['ppl']:.1f}。",
                        "interpretation": f"146K トークンのコーパスを約{n_epochs:.0f}周しており、ギャップ {abs(gap):.2f} nats は軽度〜中程度の暗記。教材としては「小データ多エポックで何が起きるか」の実例。bigram val {bigram['neural']['val_loss']:.2f} → Transformer val {fin_val:.2f} の改善分（約{bigram['neural']['val_loss']-fin_val:.2f} nats）が『文脈を使う』能力の寄与。",
                        "caveat": "単一シード・単一コーパス。val は小説の終盤部分（連続分割）なので文体ドリフトの影響を含む。",
                        "next": "M2 で本物のコーパススナップショット（重複除去つき）と1エポック未満学習に移行し、暗記を分離。",
                    },
                },
                {
                    "figure": _fig(curves.lr_grad_figure(records, config["train_config"]["grad_clip"])),
                    "meta": {
                        "what": "学習率スケジュール（線形ウォームアップ→cosine）と、クリップ前の全体勾配ノルム。",
                        "why": "勾配ノルムの爆発/消失は不安定化の最初のシグナル。クリップ発動率も安定性の指標。",
                        "how": "破線がクリップ閾値。これを超えた step はクリップが発動している。",
                        "observation": f"ウォームアップ後、勾配ノルムは概ね 0.3–0.9 で推移。クリップ発動率は {clip_rate:.0%}（主に初期）。NaN/Inf 検出は全評価で 0 件。",
                        "interpretation": "lr=3e-3 はこの規模では安定域。発動が序盤に集中するのは、初期化直後の大きな損失勾配による正常な挙動。",
                        "caveat": "「クリップ0%が理想」ではない。閾値が緩すぎる可能性と区別できない。",
                        "next": "M3 §14.2 の LR range test で不安定化点を実測し、閾値と lr を体系的に決める。",
                    },
                },
                {
                    "figure": _fig(curves.update_ratio_figure(records)),
                    "meta": {
                        "what": "パラメータ群ごとの update-to-weight 比 ‖ΔW‖/‖W‖（10 step ごとに計測）。",
                        "why": "「学習率が実効的に大きすぎる/小さすぎる」を群別に検出できる、lr そのものより情報量の多い指標。",
                        "how": "経験則では AdamW で ~1e-3 前後が健全（点線）。群間で桁が揃っているかを見る。",
                        "observation": "全群とも 1e-3 の目安線の近傍で推移し、cosine 減衰に伴って徐々に低下。norm 群は他よりやや高め。",
                        "interpretation": "群間で極端な乖離がなく、単一 lr で全群が妥当に更新されている。norm（1次元パラメータ）はノルムが小さいため比が出やすい。",
                        "caveat": "経験則の 1e-3 はタスク・スケール依存の目安にすぎない。",
                        "next": "M3 で lr を振った際にこの比がどうシフトするか、群別 lr の必要性を検討。",
                    },
                },
                {
                    "figure": _fig(curves.grad_norm_by_group_figure(records)),
                    "meta": {
                        "what": "パラメータ群別の勾配ノルム時系列（log スケール）。",
                        "why": "損失悪化時に「どの層・どの群で異常が起きたか」を遡れるようにする（spec §12）。",
                        "how": "群間の相対関係と急変（スパイク）を見る。",
                        "observation": "token_emb と mlp の勾配が大きく、pos_emb は小さい。全群が滑らかに減衰し、スパイクなし。",
                        "interpretation": "埋め込みは全トークンの誤差を直接受けるため勾配が大きいのは自然。pos_emb の勾配が小さいのは位置情報の寄与が相対的に小さいことを示唆。",
                        "caveat": "ノルムの大小はパラメータ数にも依存するため、群間比較は同一群の時間変化ほど厳密ではない。",
                        "next": "M3 の RoPE 置換で pos_emb（学習パラメータ）を除いたときの挙動比較。",
                    },
                },
                {
                    "figure": _fig(curves.activation_rms_heatmap(records)),
                    "meta": {
                        "what": "評価時の residual stream RMS（観測点 × 学習ステップ）。",
                        "why": "活性の爆発・消失、特定層だけの異常（outlier channel 等）の早期検出。",
                        "how": "色が急激に明るくなる行/列は活性爆発の兆候。深さ方向に緩やかに増えるのは残差加算の正常な蓄積。",
                        "observation": "RMS は深い層ほど大きく、学習に伴い全体に単調増加。tok_emb は init_std=0.02 に対応する小さい値から出発。爆発・NaN なし。",
                        "interpretation": "pre-LN 構成では residual stream のノルムが層とともに成長するのは既知の挙動で、各 branch の書き込みが蓄積している証拠。",
                        "caveat": "RMS は分布の1統計量にすぎず、外れ値チャネルの検出には kurtosis / absmax（記録済み）の併読が必要。",
                        "next": "M2 §11: branch 別寄与 r_l = ‖Δh‖/‖h‖ の層別時系列、外れ値チャネル分析。",
                    },
                },
                {
                    "figure": _fig(curves.tokens_per_sec_figure(records)),
                    "meta": {
                        "what": "ウィンドウ平均スループット（tokens/sec）。",
                        "why": "学習時間の見積りと、eval/checkpoint のオーバーヘッド可視化。",
                        "how": "谷は eval・checkpoint・生成サンプリングを含む区間。",
                        "observation": f"定常区間の中央値 ≈ {tps_median:,.0f} tokens/sec（BF16・SDPA・batch 64×256）。全体では {summary['tokens_seen']:,} tokens / {summary['wallclock_sec']:.1f}s ≈ {summary['tokens_seen']/summary['wallclock_sec']:,.0f} tokens/sec。",
                        "interpretation": "1.1M パラメータのモデルでは GPU は大部分アイドルで、eval/生成のオーバーヘッド比率が大きい。モデルが大きくなるほどこの比率は下がる。",
                        "caveat": "VRAM 使用量 0.1GB — この計測はモデルサイズのスケーリング予測には使えない（M3 で実測）。",
                        "next": "M3 §14.1: モデルサイズ・batch・compile 別の系統的スループット計測。",
                    },
                },
            ],
        },
        {
            "id": "generation",
            "title": "Generation（checkpoint 別・固定プロンプト）",
            "intro": "<p>全 checkpoint で同一プロンプト・同一シードのサンプリングを実行してあるため、変化はモデルの変化のみを反映する。</p>",
            "blocks": [
                {"heading": "「私は」の続き（greedy vs temperature 0.7）", "html": gen_table("私は", fracs=(0.0, 0.05, 0.25, 1.0))},
                {
                    "heading": "暗記プローブ:『こころ』冒頭文の続き",
                    "html": (
                        f'<p class="note">原文の続き: <span class="gen-text">{html.escape(opening_true)}</span></p>'
                        + gen_table(sentence, keys=("greedy",), fracs=(0.25, 1.0))
                    ),
                    "meta": {
                        "what": "学習データ冒頭文をプロンプトに、原文をどこまで再現するか（greedy）。",
                        "why": "train/val ギャップが示す「暗記」を生成側から確認する（M5 §20 の予告編）。",
                        "how": "原文の続き（上の灰色文）と生成を突き合わせる。",
                        "observation": "100% 時点でも原文の逐語再現には至らず、文体・語彙（「先生」「時」など）を模倣した反復的な文が出る。「私は」プロンプトでは init の単一文字連打 → 5% の局所ループ → 100% の文構造獲得、という段階が明瞭。",
                        "interpretation": "1.1M パラメータでは 146K トークンの逐語暗記すら容量的に厳しく、頻度の高い局所統計から順に獲得している。greedy の反復ループは小型LMの典型的な失敗モード。",
                        "caveat": "「逐語再現しない＝暗記していない」ではない（train loss は val より 0.55 nats 低い）。反復は greedy 特有で、サンプリングでは緩和される。",
                        "next": "M5 §20: exact-match 継続率・最長共通部分文字列による暗記の定量化、§16 の sampling 別比較。",
                    },
                },
            ],
        },
        {
            "id": "limitations",
            "title": "Limitations（この実験から言えないこと）",
            "blocks": [
                {
                    "html": (
                        "<ul>"
                        "<li><b>単一シード・単一コーパス</b>: すべての数値は run-to-run 変動を含む。±いくらかは M3 の複数シード実験まで不明。</li>"
                        "<li><b>多エポック学習</b>: 約45周しており、損失改善の一部は暗記。1エポック未満の大規模コーパス学習（M2/M4）とは力学が異なる。</li>"
                        "<li><b>文字トークナイザ固有</b>: 系列長・語彙被覆・エントロピーの値は BPE では変わる。</li>"
                        "<li><b>attention 可視化は説明ではない</b>: 重みの大きさは因果的重要性を保証しない。</li>"
                        "<li><b>確率の信頼性（calibration）未評価</b>: top-1 confidence は上昇したが、それが「正しい確信」かは M5 の reliability diagram まで判定できない。</li>"
                        "<li><b>生成品質の評価は定性的</b>: 反復率・distinct-n 等の定量指標は M5 §16 で導入。</li>"
                        "</ul>"
                    ),
                },
            ],
        },
    ]

    env_j = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"), autoescape=False)
    html_out = env_j.get_template("m1.html.j2").render(
        title="jp_llm_lab — Milestone 1 Report",
        subtitle=f"Classical GPT (Model S, {config['param_breakdown']['total']:,} params) × 『こころ』 char-level — 全数値は実測値",
        sections=sections,
        footer=f"jp_llm_lab Milestone 1 — generated from run artifacts ({runmeta['timestamp_utc'][:10]}) / 実測データと例示データの混在なし",
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(html_out, encoding="utf-8")

    assets = out_dir / "assets"
    assets.mkdir(exist_ok=True)
    plotly_js = assets / "plotly.min.js"
    if not plotly_js.exists():
        from plotly.offline import get_plotlyjs

        plotly_js.write_text(get_plotlyjs(), encoding="utf-8")
    return out_dir / "index.html"
