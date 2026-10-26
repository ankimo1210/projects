# DSINCによるAmerican putの数値再現 — 設計

更新日: 2026-10-27（JST）。状態: **実装中（branch `claude/dsinc-american`）。Task 1〜6完了。2026-10-26のpilotは判断点で止まり、D-6・D-7を2026-10-27に承認した。pilotのやり直しが次で、本計算は未着手**。Opus承認後、§5/§6に論文Table 3(b)/4の印刷値を照合対象として追加した（[レビュー記録](../reviews/2026-10-25-dsinc-american-opus.md)の「Opus承認後の追加照合と変更」）。2026-10-26、[実装計画](../plans/2026-10-25-dsinc-american.md)を完全版に改訂し、§4〜§6からの逸脱D-1〜D-5を提案した（計画の§1。根拠の実測もそちら）。D-1〜D-5は同日ユーザーが承認し、本文の§4〜§6へ反映した（計画のTask 1。反映箇所は「逸脱D-n」と明記）。改訂版のOpus再レビューはない。2026-10-26のpilotが判断点で止まった後、D-6（根を探す幅に予備の.5）とD-7（上下界を通らない段は採用しない）を2026-10-27にユーザーが承認し、§4の幅の規則と§6の段の選択へ反映した（計画のTask 7R。根拠は計画の§1）。

## 1. 目的と承認範囲

ユーザー依頼は「実装プランを作ってopusのレビューにかける」。このターンで行うのは設計、実施計画、レビューとその是正である。以下の実装・実験は実施計画であり、着手済みと扱わない。

目的は、市場データを用いず、American putのEuropean価格・早期行使プレミアム（EEP）・行使境界をローカルCPUで再現し、誤差と費用を独立な方法で評価すること。速度向上を採択条件にしない。

実装時のv1範囲は、(A) 公開Heston版の監査・比較と、(B) 新論文の固定周波数・節点境界方式による**定数係数3/2モデル**。SABR、GARCH、lognormal-vol、負金利、rd<rf、strict local martingaleのケース、時変係数、Bermudan金利商品、較正、実市場データ、NN、教材サイトへの組込みはv1に含めない。Hestonの制御実験用作用素は作るが、新しい公開Heston APIの提供は目的にしない。

本編・既存研究の完了を取り消さず、保留中のRB-F04動的ヘッジも再開しない。研究名は既存RB-IDを流用せず `DSINC` とする。実装・数値閾値は本計画の提案で、ユーザーが個別に選択済みとは表現しない。

## 2. 確認した入力と出典

- 最新論文v1: Andrey Itkin, *DSINC beyond Heston: the 3/2 and other non-affine stochastic-volatility models*, 2026-10-20, [arXiv:2610.28847v1](https://arxiv.org/html/2610.28847v1)。主な対応箇所はEq.(14), (53), (57)–(61)、§5.3–5.5、Tables 3–6, 9。
- 基礎論文: Andersen, Itkin, Kazbek, [arXiv:2606.27335v1](https://arxiv.org/abs/2606.27335v1)。公開コードはこのHeston研究に対応し、新論文の非アフィン版そのものではない。
- 公開コード: [DSINC-AMERICAN-HESTON](https://github.com/rakhymzhan11/DSINC-AMERICAN-HESTON/tree/20cfb802673b0a792984d25e1f45cd09d37e8c07)、固定commit `20cfb802673b0a792984d25e1f45cd09d37e8c07`。
  - `dsinc_pricer.py`: Git blob `33d4d6a78f63d89025786fe75a774d565ba5a9dc`。
  - `fd_adi_pricer.py`: Git blob `3518f6b1979f7856f1c9825ba37446e7849b6e85`。
  - `benchmark.py`: Git blob `59b7f490942b7099abf1a90c0987f1c08603416a`。
  - `LICENSE`: Git blob `04fabfeb16dba4d1179fe3337d27be15019b50a9`、MIT。著作権行の `<COPYRIGHT HOLDER>` を勝手に補完せず原文保持する。
- ローカル基点: `ed0cf2f8a2283e3444334aa7a0acb073ff9d685f`、main、開始時working tree clean。
- Python >=3.12、既存NumPy >=2.0 / SciPy >=1.13。準備時の実環境はNumPy 2.4.6 / SciPy 1.17.1。新しいproduction依存は追加しない。
- 既存の `hullkit.trees`、`hullkit.fd`、`hullkit.stochastic_volatility`、`hullkit.american_mc` を参照した。一定ボラputのCRR 4,000 stepsは6.090180715、European解析式は5.573526022（S=K=100,T=1,r=.05,q=0,sigma=.2）。これは準備用対照で、DSINC再現の証拠ではない。

## 3. 監査で判明した差異

1. 上流READMEのDSINC例はkappa=.5、FD例はkappa=2。比較には単一の正規化された契約・モデル入力を両方式へ明示転送する。
2. 上流DSINCはchi=-1を内部固定し、facet/band-mass方式を使う。新論文のv1実装はchi=.5、節点境界、固定周波数方程式である。上流のクラスへ3/2係数だけ差し替えて移植しない。
3. 上流 `_solve_boundary` は予測値のclip、局所brentq、広範囲scanの最初のroot、最小残差点の順で処理し、`_safe` は例外をNaN化する。さらに `_heston_cf` の非finite値の0置換、`_european_value` の非負化、`_final_eep` の非負化、`price()` のpayoff下限を監査する。原本は変更せず、研究用サブクラスの観測版helperで加工前後・分岐・残差を記録し、無改変版との値の一致も検査する。fallbackや加工を観測した値は無条件に「収束」と認定しない。
4. 上流FDの実設定はpolicy=1だが冒頭docstringはpolicy=0をdefaultと記載する。penalty最大反復到達時も明示的失敗を返さない。基礎比較では設定と実挙動を監査し、新3/2参照は独立実装で収束診断を返す。
5. 上流benchmarkはassertionのない印刷スクリプトで、importすると計算を実行するためimportしない。上流Europeanは閉形式CFからのCOSで、上流EEPの時間和も新論文の端点項を検証する対照ではない。上流の印刷値や二方式の一致だけでは受入にしない。原本はruff/format対象外にし、研究adapterはimportlibでファイルを指定して読み、sys.pathを変更しない。

## 4. 金融契約と計算方法

単位は年、連続複利の年率、価格は原資産と同じ通貨。保存・比較は価格/Kを基本にし、生価格も保存する。v,thetaは分散率でありボラではない。xiはvol-of-variance。rhoは相関。

\[
dS=(r_d-r_f)Sdt+\sqrt v S\,dW_S,\qquad
dv=\kappa v(\theta-v)dt+\xi v^{3/2}dW_v,
\quad d\langle W_S,W_v\rangle=\rho dt.
\]

契約はpayoff=(K-S)^+、連続American行使、K>0、S>0。v1はrd>rf>=0、kappa,theta,v0,xi>0、|rho|<1、かつ3/2のtrue-martingale領域 `rho*xi <= kappa + xi**2/2` に限定する。境界の満期直前極限はx*=0。T=0はexact payoffを返し、境界診断はnot_applicable。負のT、NaN/Inf、無効な格子・減衰はValueError。xi=0はv1の公開されない研究入力でもunsupportedとし、定数分散の検算は作用素の別fixtureとして定義する。

x=log(S/K)、zeta=log(v)、v=exp(zeta)、a=eta(v)/v、b=mu(v)/v-eta(v)^2/(2v^2)。複素周波数kの非割引作用素は

\[
A_k f=\tfrac12a^2f''+
 (b+ik\rho\sqrt v\,a)f'
 +\{ik(r_d-r_f)-\tfrac12(k^2+ik)v\}f.
\]

3/2ではa=xi*sqrt(v)、b=kappa*theta-(kappa+xi^2/2)*v。Heston制御用はa=xi/sqrt(v)、b=kappa*theta/v-kappa-xi^2/(2v)。ここに割引項-rdを混ぜず、価格側で一度だけ割り引く。

新方式は正周波数パネルGauss–Legendre、反射周波数k=-omega-i*chi、0<chi<1、中心差分、`scipy.linalg.expm` の一段伝播を使う。n_varは両端を含む節点数でh=(zeta_max-zeta_min)/(n_var-1)。Neumann端はghost反射で一次微分を0、二次微分を2*(f_neighbor-f_endpoint)/h^2とする。v0への評価は最終価格をzeta方向へnot-a-knot CubicSpline補間し、外挿を拒否する。Heston/3/2は同じ作用素構築経路を通り、a,bだけを替える。

EuropeanはEq.(61)、EEPの蓄積はEq.(57)、境界はEq.(58)に対応させる。正減衰の留数項、最終時点の台形半重み、境界方程式だけの端点項 `dt*g(x)/4`（g=rd-rf*exp(x)）を明示する。初期価格のcontinuation側評価にこの端点項を加えない。行使領域内の価格はexact payoffにするが、計算違反をmax/clipで隠さない。T=0の境界・時刻・分散格子は空（boundary shape=(0,0)）、diagnostics.boundary_status=not_applicableとする。

中央差分は低分散で非単調になりうる。Pe、実周波数0の伝播行列の最小成分と行和誤差を保存し、正値性を理論保証したとは表現しない。負成分が-1e-10未満ならscheme_nonmonotoneを記録し、分散細分・領域/offset感度と独立FDの全価格gateで影響を確認できなければunsupportedとする。

境界は各時刻・分散節点で求める。残差R(x)はEq.(58)の左辺から右辺を引いた無次元量（価格をKで割った残差）と定義する。次時点の境界pを予測値とし、[p-.1,min(0,p+.1)]→幅.2→幅.3→幅.5（逸脱D-6）の順に候補を作り、put向きのR(lo)>0>R(hi)を必須にする。各候補はm=max(65,ceil(2*omega_max*(hi-lo)/pi)+1)点で走査し、許容零近傍をまとめた符号変化を数える。逆向き、符号変化なし、曖昧な零の平坦部はそれぞれwrong_orientation/missing_sign_change/ambiguous_contactで失敗とする。ambiguous_contactは|R|<=root_residual_tolの走査点が2点以上続く場合に限り、交差点上の零が1点だけなら交差として扱う。bracket内に複数の符号変化があっても失敗にはしない（逸脱D-1）。putの行使域はx<=x*なので、x*を残差Rが正である最上位の点、つまり最上位の+→−交差と定義し、状態をmultiple_crossingsとして記録する。S0のT=.5では16,000 node-stepのうち58件でbracket内に交差が3つあり、失敗にすると最初のstepで止まるためである。歯止めは二つ置く。(i) 最下位の交差を選ぶ個別感度crossing_lowerを、他の感度と同じ5e-6のgateにする（§6）。(ii) 境界照合の窓（§5）の中にmultiple_crossingsが1点でもあれば、境界gateをFAILにする。これはサンプル上の診断であり、連続関数のrootの一意性証明ではない。走査費用も予算に含める。

二分法は最大60回、x幅<=1e-10かつabs(R)<=1e-8。sign change無し、非finite、最大反復も構造化したPricingFailureとする。min-residual点への置換や広範囲の最初のrootへの移動はしない。失敗時刻では全分散節点を最後まで処理してstatus配列を埋め、それからケースを停止する。さらに早い時刻はnot_runとして保持し、失敗境界でQを更新しない。走査はnode/候補xの小ブロックで行い、scan数×n_var×n_omegaの巨大配列を一括保持しない。独立FDの接触領域・時間方向整合も照合する。

## 5. 独立参照と受入条件

3/2参照は `research/DSINC/reference_fd.py` に置き、spectral作用素、payoff transform、境界solverをimportしない。x,zetaのSDEから直接組む。

\[
L V=(r_d-r_f-v/2)V_x+
 [\kappa\theta-(\kappa+\xi^2/2)v]V_\zeta
 +\tfrac12vV_{xx}+\rho\xi vV_{x\zeta}
 +\tfrac12\xi^2vV_{\zeta\zeta}-r_dV.
\]

四つのimplicit Euler half-stepsのRannacher起動後にCN、American制約はIkonen–Toivanen splittingを用いる。American左端のpayoffと右端0は有限領域の近似で、高分散の全行で正しい境界とは主張しない。European左端はmax(K*exp(-rd*tau)-S_min*exp(-rf*tau),0)。分散端はNeumann。接触はlambda>1e-10*Kかつabs(V-payoff)<=1e-8*Kで判定し、乗数・payoff gap・離散方程式の残差を保存する。境界条件の誤差は格子幅を固定した領域拡大で別測定する。

paper設定照合用FDと独立正当性用FDを区別する。前者は論文の領域/格子、後者の分散領域は[log(1e-5),log(8)]から始め、spectralと同じ端の誤差を共有しない。未知数は短い次元を内側に並べる。全軸同時の第3細分は行わず、xのみ、分散のみ、tのみの軸別に観測収束を調べる（水準は§6。x軸は4水準）。参照値と収束の判定は、設計では未定義だったため次のように定める（逸脱D-3）。参照値は、基準B=(241,101,300*T)と各軸の最細水準から P_ref = P_B + Σ_軸(P_軸の最細水準 − P_B) とする。各軸は、最終差<=5e-6で、かつ (a) 最終差<=5e-7（基準の1/10で、判定を動かさない大きさ）、または (b) 変化が縮小し（|最終差|<|前の差|）観測次数が[1,3]に入る、のどちらかを満たせば収束とする。分散軸は最終の変化が基準の1/20以下と小さく、観測次数が5.3/5.0/1.7とばらつくため(a)を置く。領域を広げたときの差も<=5e-6とする。次数は、等比でない刻みhについては根を解いて求める。二次外挿は観測次数が整合した軸についてだけ診断に使い、参照の保証誤差とは呼ばない。

独立制御は、(i) 既存Heston European CF/COS、(ii) 定数分散作用素の解析的伝播＋BSM/CRR、(iii) 3/2のu=1/vがCIRとなることからの解析的条件付平均、(iv) 独立FD。Heston制御はkappa=2,theta=v0=.04,xi=.2,rho=-.5,rd=.05,rf=.02,T=.5、S/K={.9,1,1.1}とし、Feller条件を満たす。既存heston_priceのdividend_yieldとCRR/BSMのqが利用できることは準備時にsignatureで確認した。

CIR平均の制御はn_var={160,240,320}で共通v0=.04へ3次補間し、観測次数1.5〜2.5と最細格子の相対誤差<=1e-4を調べる。元の絶対誤差1e-4基準は撤回した。原点に近い節点での準備計算では絶対誤差が約.001975/.000888/.000529となり、旧基準が不適切なことを確認した。この小さな制御計算を研究pricerの実装済みとは扱わない。

文献再現と独立正当性は別gateにする。paper_matchは必ずS0（n_var160、n_time=200*T、108周波数、chi=.5）のspectral値を、Table 4の3/2 American 3spots、Table 3(b)の3/2 European 3spots {.102557,.047224,.019105}（論文ではspectralと閉形式Eq.(31)が6桁一致）、Table 9のT=1,ATM=.063668に比較し、絶対差/K<=6e-6（丸め分1e-6＋事前宣言差5e-6）で判定する。Table 4のEEP列{.005044,.001438,.000394}（=American−European）は不一致をEuropean側とEEP側に切り分ける診断列とし、gateに二重計上しない。Table 4のDSINC N=200列{.107599,.048660,.019497}はS0の時間倍（cutoff固定）と同じ設定なので、pilotの差を診断列に残し、停止条件にしない。Task 3/5のsmokeを経てTask 7で正式判定し、超過はpaper_mismatchとして停止・レビューする。許容差を自動緩和しない。T=1非ATM2点は印刷価格がないためnot_available。FDと論文のcoarse/fine値の差は別の診断列とし、端/補間などの離散化の同一性が未確認なので6e-6の停止条件に含めない。再現済みの主張は、宣言したspectral文献照合と下記独立gateの両方が成立した範囲に限定する。

実装時のsource対応表に、パネル端・節点数・時間格子は論文由来、ghost端の具体化・初期分散補間・root走査は独自選択、と明示する。独自選択による差も上記の文献照合基準の中で説明する。

v1の提案値は次の通り。pilotで達成性と費用を確認して主実験前に設定をfreezeする。閾値を緩める場合は計画改訂としてレビューし、失敗条件を黙って外さない。

- 主価格: 6ケースすべてで `abs(P_spectral-P_reference)/K <= 2e-5`、reference最終細分差<=5e-6、spectralの個別細分差<=5e-6。EEPも同じ絶対精度で評価し、小EEPの相対精度を主張しない。
- American>=European、American>=payoff、American<=Kは許容差2e-5*K。違反のraw値を保存し、許容差を超えたらFAIL。Europeanの上下界・strike homogeneityも確認する。
- chi=.25,.5,.75、周波数cutoff、パネル節点数、分散領域・節点数、時間刻みを一軸ずつ変える。時間細分時はcutoff固定の検査とcutoff拡大を伴う検査を分ける。
- 行使境界: 時刻indexの整数交差条件j*N_fd=k*N_spectralを満たす共通時刻に限り、t/T∈[.1,.9]、v∈[.01,.16]を比較対象にする。FDの接触/継続bracketの両端をzetaで線形補間してspectral節点へ写す。bracketが取れない、またはFD/spectral境界がx端から4セル以内ならgeometry_invalidとして理由つきでmaskし、事前対象の有効coverageが90%未満なら境界gateをunsupportedにする。有効点ではspectral境界がFD bracketから2*dx以内、価値一致残差<=1e-8。maskはroot計算の失敗を除く手段にしない。窓の中にmultiple_crossingsが1点でもあれば、境界gateはFAILとする（逸脱D-1、§4）。境界gateのFDは、専用の細かい時間刻みで走らせる（逸脱D-4）。独立FDと同じ広い分散領域でAmerican FD (961,101,1200*T)を主、(961,101,600*T)を確認用とし、x∈[-1.2,1.2]なのでdx=.0025、許容は2*dx=.005。窓の中で確認用との接触端の差が1セル以下なら「収束確認済み」とする。比較する時刻は、上記の整数交差条件を満たす時刻だけ。FD (961,101,300*T)とS0の比較では、FDの時間方向の遅れで最大の外れが.0092（3.7dx）に達したが、時間刻みを600/1200/2400*Tにすると最大の外れは.0047/.00257/.00114で2dx以内に入る。
- Deltaは両方式とも最終価格のspot bump/K={1e-3,5e-4,2.5e-4}で抽出する。FDは価格補間後に同じbumpを使う。数値を報告する診断であり、Delta/Gammaの正式PASSや精度認定はv1の完了条件にしない。
- すべて元ケース数、非finite、root失敗、時間切れ、予算超過を記録し、失敗を除いた平均だけを表示しない。

## 6. 固定ケースと計算予算

Heston準備比較は上流benchmarkの1+10ケースを入力表に転記し、pilotは最初の1ケースのみ。印刷参照の差とfallbackを観測し、既定設定の精度を保証しない。新方式のEuropean制御にはまず同じモデルでS/K=.9,1,1.1を使う。

3/2主ケースはrd=.05,rf=.02,K=1,kappa=20,theta=v0=.04,xi=4,rho=-.5、T={.5,1}×S/K={.9,1,1.1}の6件。paper Table 4のT=.5, N=100のAmerican値{.107601,.048662,.019499}はTask 5でsmokeとして確認し、Task 7でS0のpaper_matchに使う。Table 3(b)のEuropean値も同様に、Task 3でsmoke、Task 7でpaper_matchに使う。

初期spectral設定S0はn_var=160,n_time=200*T、zeta∈[log(.0002),log(2)]、chi=.5、パネル端{0,2,5,10,20,40,80,160,320,640}、各12点。価格選択ladderはS1=(240,400*T,cutoff1280,各12点)、S2=(320,800*T,cutoff2560,各16点)。追加cutoffは末尾へ順に倍のパネルを足す。S0→S1→S2以外を主計算で追加しない。最初の隣接差<=5e-6、独立FD差<=2e-5、個別感度gate成立を満たし、さらに満期ごとに価格を出した全spot（主3点・bump・境界走査）で上下界（許容2e-5）を通る粗い側Sjを採用する（逸脱D-7）。採用はS0またはS1で、S2は上限側の検算用。同一満期の3spotsの最大差と上記の上下界で一段を選び、spotごとに段を選別しない。どの隣接対も通らなければ未達。全段・準備費用を保存する。

pilotの個別感度はS0起点。mainでは採用候補Sj自身を起点に、時間倍・次の分散段（160→240、240→320）・各パネル点数+4・cutoff倍・chi=.25/.75・領域拡大・offset±h/2・crossing_lower（最下位の交差を選ぶ。逸脱D-1、§4）を一軸ずつ評価し、各価格差/K<=5e-6を正式な個別gateにする。Sjが不合格なら次の隣接対へ進み、予算内に合格段がなければ未達。領域はh固定で両側ceil(log(2)/h)節点ずつ追加。S0のpilotだけでS1の安定性を認定しない。scheme_nonmonotoneの影響確認も、この全個別gate・文献gate・独立FD gate・境界gateの成立を意味する。mainの各候補に必要な全ジョブをfreezeし、全軸の直積sweepはしない。ただしS1候補の個別感度は、その満期でS0が採用されなかった場合だけ実行する条件付きジョブとし、この規則をfreezeに含める（逸脱D-5）。必ず走るジョブに入れると、naive実装の見積もりが2倍則で約55分になり、30分を超えるためである。

paper照合FDはx∈[-1.2,1.2]、(nx,nv,nt)=(241,101,300*T)→(481,201,600*T)、分散領域はpaper設定。独立FDは上記の広い分散領域で同じ節点数から始め、軸別にx={241,481,961,1921}、分散={101,151,201}、nt={300*T,600*T,1200*T}を他軸固定で調べる（逸脱D-2）。xを3水準にすると、T=.5のAmericanで481→961の変化が[5.2e-6, 7.6e-6, 4.7e-6]で、3点のうち2点が基準の5e-6を超えるため1921を足す（961→1921は[9.0e-7, 1.9e-6, 1.2e-6]で、観測次数は2.5/2.0/2.0）。x軸の次数は最後の3水準から求める。x=1921のAmericanはT=.5で5.7秒、T=1で11.5秒（実測）。分散の不等比細分は実際のhで観測次数をfitし、均等2倍と仮定しない。x領域拡大は[-2.4,2.4]にhを保って節点追加する。実行する全構成と順番をfreezeに含め、参照精度・予算が成立しなければ主計算を止める。

単一CPU core、float64/complex128。OPENBLAS_NUM_THREADS=OMP_NUM_THREADS=MKL_NUM_THREADS=NUMEXPR_NUM_THREADS=1。上限単位は「1方式×1満期×1設定を解き、3spotをまとめて返すsolver subprocess」でwall 180秒/peak RSS 2 GiB。spotを別caseとして同じsolveを繰り返さない。pilot合計10分、主実験合計30分を停止予算とする。pilotにT=1のFD fine Americanの費用測定（x=1921と境界gate用の主FD。実測はT=1でそれぞれ11.5秒と18秒）を含める。必ず走るジョブの推定費用が30分を超える場合も主計算へ進まない。この30分の推定gateは必ず走るジョブにだけ適用し、条件付きジョブには適用しない（逸脱D-5）。

反復計時は選定後のspectralだけ1 warmup+3測定とし（どの段が採用されるかはmainの途中で決まるため、この採用段の計時4本も条件付きジョブとする。逸脱D-5）、FDは1回のsolveの実測値とする。FDの速度分布や統計的速度優位を主張しない。cold setupとwarm queryを分け、FDもsetupを除かない。計時の反復数を含むjob rosterと予算をfreezeする。見積もりは同じ構成の実測があればその2倍、未測定spectralはpilotのsetup*(Nw比)*(Nv比)^3＋solve*(Nt比)*(Nw比)*(Nv比)^2*(走査点数比)の2倍、FDはpilotからLU∝nodes*bandwidth^2、step∝Nt*nodes*bandwidthを使って2倍の余裕を取る。係数と式をmanifestへ記録し、係数未測定、1job予測180秒超（条件付きも含む）、必ず走るジョブの合計30分超ならmainへ進まない。条件付きジョブは、推定がその時点の残り予算に収まるときだけ走らせ、収まらなければnot_achieved_budgetとして記録する（逸脱D-5）。予算と許容差は自動では増やさない。これは予測であって保証ではなく、実行中にも上限を監視する。

密な伝播行列の見積もりは108*160^2*16=44,236,800 bytes（約42.2 MiB）、240節点で約94.9 MiB。二つの解像度を同時保持せず、FDのsparse LU fill-inもpilotで測る。保存は結果・境界・設定・入力/コードhash・計時・検算要約だけで、目標50 MiB以下。伝播行列、全時点のFD面、中間配列は保存しない。

Git管理外の1run rootは `_data/johnhull/DSINC/<run-id>/`。再生成可能な中間配列は固定設定から再計算しhashを比較する。freeze manifestは主run rootとrepoの小ファイルへ複製し、pilot root削除後も再実行できるようにする。主結果の小JSON/圧縮NPZだけ研究ディレクトリへ選別し、追加ファイル2 MB制限を守る。重い成果が必要になればADR 0004に従い、1rootが30 GiBを超える計画は事前承認を得る。

## 7. 成果物と完了

private pricer、独立FD、テスト、固定入力表、結果JSON/圧縮NPZ、再実行CLI、研究README、レビュー記録を作る。図は価格誤差vs費用、行使境界、細分・減衰安定性の3図を小さな保存結果から描く。HTML/Book/portalは追加しない。

完了条件は、文献照合gate、6ケースの価格・境界・独立参照・収束/領域検査、raw failure会計、実測費用/サイズ、関係テスト、最終独立レビューと採否をすべて残すこと。paper_matchとindependent_validatedの両列をrunnerから機械判定し、両方が通った宣言範囲だけ再現済みとする。高速でなくても検算が成立すれば研究として完了できる。未達なら「未再現/制約付き」と記録し、市場妥当性や全American商品への一般化を宣言しない。

実装の順番と正確なファイル/API/テストは [実装計画](../plans/2026-10-25-dsinc-american.md)。
