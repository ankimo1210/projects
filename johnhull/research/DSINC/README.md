# DSINC：3/2モデルのAmerican putを固定周波数spectral法で再現する

進捗と判定は[ROADMAPの現在地](../../ROADMAP.md)が正。設計は[設計](../../docs/superpowers/specs/2026-10-25-dsinc-american-design.md)、実装の順序とAPIは[実施計画](../../docs/superpowers/plans/2026-10-25-dsinc-american.md)。

## 目的と範囲

市場データを使わず、定数係数3/2モデルのAmerican putについて、European価格・早期行使プレミアム（EEP）・行使境界をローカルCPUで再現し、誤差と費用を独立な方法で評価する。速度向上は採択条件にしない。

- モデル：dS=(rd−rf)S dt+√v S dW_S、dv=κv(θ−v)dt+ξv^(3/2) dW_v、d⟨W_S,W_v⟩=ρdt。payoffは(K−S)⁺、行使は連続。
- v1の入力範囲：S,K>0、T≥0、rd>rf≥0、κ,θ,v0,ξ>0、|ρ|<1。3/2はtrue-martingale領域 ρξ≤κ+ξ²/2に限る。T=0はexact payoffを返す。範囲外、NaN/Inf、無効な格子や減衰はValueErrorにし、clipや代用値で隠さない。
- 単位：時間は年、金利は連続複利の年率。v,θは分散率（ボラではない）。価格はKで割って比べる。
- 「再現済み」と言える範囲：論文の印刷値への照合（paper_match）と、独立FDへの照合（independent_validated）の両方が通った宣言範囲だけ。通らなければ「未再現/制約付き」と記録する。
- 含めないもの：SABR、GARCH、lognormal-vol、負金利、rd<rf、strict local martingale、時変係数、Bermudan金利商品、較正、実市場データ、NN、教材サイトへの組込み。Hestonは制御実験用の作用素と公開コードの比較にだけ使い、新しい公開Heston APIは作らない。

実装はhullkitのprivateモジュール[`_dsinc_types`](../../hullkit/src/hullkit/_dsinc_types.py)（入力型・検証・digest）と[`_dsinc_spectral`](../../hullkit/src/hullkit/_dsinc_spectral.py)（周波数則・作用素・伝播・European・v0補間・診断）、およびこのディレクトリの研究コード。EEPの再帰・独立FD・runnerは実施計画に従って順に足す。

## 方法と出典

- 新方式：Andrey Itkin, *DSINC beyond Heston: the 3/2 and other non-affine stochastic-volatility models*, 2026-10-20, [arXiv:2610.28847v1](https://arxiv.org/html/2610.28847v1)。対応箇所はEq.(14), (53), (57)–(61)、§5.3–5.5、Tables 3–6, 9。
- 基礎：Andersen, Itkin, Kazbek, [arXiv:2606.27335v1](https://arxiv.org/abs/2606.27335v1)。
- 公開Heston実装：[DSINC-AMERICAN-HESTON](https://github.com/rakhymzhan11/DSINC-AMERICAN-HESTON/tree/20cfb802673b0a792984d25e1f45cd09d37e8c07)（固定commit）。Heston版であり、3/2版そのものではない。監査と比較は[`heston_baseline.py`](heston_baseline.py)。

固定周波数の伝播とEuropean（`_dsinc_spectral`）は次の順で組む。

1. x=log(S/K)、ζ=log vとし、反射周波数k=−ω−iχ（0<χ<1）ごとに、割引を含まない作用素 A_k f=½a²f″+(b+ikρ√v·a)f′+{ik(rd−rf)−½(k²+ik)v}f を、ζ格子の中心差分で組む。3/2はa=ξ√v、b=κθ−(κ+ξ²/2)v。Hestonの制御用はa=ξ/√v、b=κθ/v−κ−ξ²/(2v)。どちらも同じ組立てを通り、a,bだけが違う。−rdは作用素に入れず、価格側で一度だけ掛ける。
2. 両端はghost節点で反射する（一次微分0、二次微分2(f_隣−f_端)/h²）。
3. ωは正周波数のパネルごとのGauss–Legendre。M_k=expm(Δt·A_k)をωごとに1回作る（Δt=T/n_time）。伝播行列は(rd, rf, T, モデル, 設定, 係数のtag)のdigestに結びつけ、別の入力で作った行列を渡すとValueErrorにする。strikeは結びつけない。
4. EuropeanはEq.(61)。s=iω−χ、E_j=M_j^N·1として、ζ節点の値 e^{−rdT}[1+(1/π)Re Σ_j ϖ_j e^{(χ−iω_j)x}E_j/(s_j(1+s_j))] を求め、v0へnot-a-knotの3次スプラインで補間する。v0が格子の外ならValueErrorにする（外挿しない）。
5. 診断として、セルPeclet数|b|h/a²と、k=0の伝播行列M₀の最小成分・行和誤差を記録する。中心差分は低分散で非単調になりうるため、M₀の最小成分が−1e-10未満ならscheme_nonmonotoneとし、正値性を保証したとは扱わない。

検算は[`test_dsinc_spectral.py`](../../hullkit/tests/test_dsinc_spectral.py)に置く：Itô係数、定数分散で作用素がBSMの指数に一致すること、1/vのCIR平均（二次の収束）、既存のHeston特性関数価格、χ=.25/.5/.75でのBSM、v0格子の半セルずらし、Table 3(b)のEuropean 3点（許容6e-6）。

| 区分 | 項目 |
|---|---|
| 論文由来 | 作用素Eq.(53)、3/2の係数（Itôで導出し直したもの）、ζ格子[log 2e-4, log 2]と160節点、パネル{0,…,640}の各12点、反射周波数とχ=.5、n_time=200T、端点の半重み |
| 独自の選択 | ghost反射のNeumann、not-a-knotによるv0補間、根の走査と最上位の交差（D-1）、根を探す幅の予備0.5（D-6）、独立FD |

独自の選択による差は、論文の印刷値への照合基準（|差|/K≤6e-6）の中で説明する。D-1とD-6は設計からの逸脱として承認済みの規則で、根拠は[実施計画の§1](../../docs/superpowers/plans/2026-10-25-dsinc-american.md)に記録している。D-6は`root_widths`を0.1・0.2・0.3・0.5とする。幅は小さい順に試し、符号変化が見つかった節点はそこで確定するので、0.5が効くのは0.3までで符号変化がない節点だけで、他の節点の結果は変わらない。

伝播行列は、expmの直後に実部・虚部の絶対値が1e-200未満の成分を0にして保存する（独自の選択）。この大きさの成分は倍精度の価格に影響せず、subnormalのまま残すとEEP再帰の一括matmulが遅くなるため。S0・S1・S2のT=0.5と1のどれでも、0化の有無で価格・節点境界・状態・診断の全出力がビット一致し、S2のT=1のwallは97.8秒から76.2秒になった。

## 再実行

WSLの対象checkout rootから共有venvを使う（単一スレッド）。

```bash
export PYTHONPATH="$PWD/johnhull/hullkit/src"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
/home/kazumasa/projects/.venv/bin/python -m pytest -q johnhull/hullkit/tests/test_dsinc_types.py johnhull/hullkit/tests/test_dsinc_spectral.py
```

`test_dsinc_spectral.py`は22件で約15秒かかる。pilot・freeze・main・replayのrunnerは実装後にここへ追記する。
