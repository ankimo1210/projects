# RB-F05 短期／0DTE 独立事前設計レビュー

2026-10-09。**合成constant-vol＋Poisson cash-callの設計式は支持する。pilot／学習／速度採否は未承認。** 元RB-F05の「正しい微分教師の生成費用を含めてDMLをprice-only／強い積分・補間と比べる」という問いを満たす縮小v1である。digital／離散バリアの既存成果を短期callへ流用した性能証拠とはしない。Bates／PIDE／rough／dynamic hedgeの完遂とは区別する。

## 1. 指摘と具体的調整

### Important（設計段階で解消）：intrinsic＋smooth residualのATM kink

草案169行の未確定outputに対するroot候補 D(S-K)^++smooth tanh residual は、W>0でも S=K にDelta jump Dを必ず残す。smooth residualはこのjumpを相殺できず、AD GammaはintrinsicのDirac項を返さない。例えば1分/no-event/S=Kでは真のGamma=4.30982であり、満期前の普通微分をkinkで比較する設計にはならない。

正式spec §6/§12は **train-only shift/scale付きlinear total C/K** を選び、これを解消した。代案はsmoothなnojump Black baseline＋unconstrained residual。raw出力をclipせず、expiry exact routeはraw NNの短期極限保証から分離する。

x=log(S/K)、V=Cなら Delta=V_x/S、Gamma=(V_xx-V_x)/S²。output f=C/Kなら Delta=(K/S)f_x、Gamma=(K/S²)(f_xx-f_x)。train-only x/output scaleもchainへ含める。Gamma lossなしの6paired fitsでGamma改善は独立診断し、Delta改善から推定しない。

### Important（設計guard追加済み、実装は未検証）：compact IIDとrare count

zero-count値はLambda=0の値ではない。A0=exp((r-q)tau_c-kappa Lambda)を使う。390分/S105/eventで正しいN0 conditional Delta=1.001198>1なので、教師個票を期待Delta boundへclipしない。LR Delta/Gamma個票の符号もfilterしない。

正式spec §12の全count draws／active original indices／active counts・ZJ／zero_count・C0/D0/G0／Chan M2／元sample_count／raw診断別streamは適切。0-count群を既知確率で再重み付けするstratificationには変更しない。詳細は§5。

草案165行の「nonzero count=0なら未支持」だけではrare componentの精度条件にならない。正式planはcount>=100、全3stream/全slotのSEとoracle差、cap失敗時freeze拒否を加えた。これは工学的guardで、rare positive-jump tailのCLT／6SE coverage保証ではない。Lambda>0のSE0／underflow／実質全同値はnonzero count>0でもunresolvedとして独立oracle差を残す。mainの暗黙増量、成功まで再draw、失敗slot削除は禁止する。

### Minor／条件付き事項

- 式のLRPW名称は「PW DeltaへLRを適用し、固定terminal変数下で1/Sの明示依存も微分」と説明する。LR後にPWへ自動微分した別順序の式と名前だけで混同しない。
- 価格／Delta期待値のboundsは個票boundsと別。有限MC平均のわずかなbound超過も即clipしない。
- adaptive quadのerror estimate／再計算差は数値診断で、厳密上界とは呼ばない。Poisson tailの解析上界とは別列。
- FormalのC² quintic spot Hermiteは適切。cubic HermiteはnodeでGammaが一意でない。時間blendの非smoothさをTheta／hedge精度へ拡張しない。
- 3featuresが時計を一意に表すのは固定同日session／expiry／clock／pulse契約内。別日、early close、休日、別event契約はunsupportedまたは別契約入力を要する。

## 2. 独立モデル導出：carry／variance／jump clock

tau_cはUTC差のACT/365、D=exp(-r tau_c)、c=(r-q)tau_c。Wは累積拡散variance、Lambdaは累積Poisson平均件数で、互換の「T」ではない。

eta=mu+sigma_J²/2、g=exp(eta)、kappa=g-1とし、
\[
X=S_T=S\exp[c-\kappa\Lambda-W/2+\sqrt W Z_B+J],\quad
J=N\mu+\sqrt N\sigma_J Z_J,\quad N\sim Pois(\Lambda).
\]
N/ZB/ZJ独立、jump lawとclockはspot-independentとしてQ-measureの合成契約を指定する。
\[
E[e^J]=\exp(\kappa\Lambda),\quad
E[X]=Se^c,\quad
Var(\log(X/S))=W+\Lambda(\mu^2+\sigma_J^2).
\]
補償を落とす／符号を逆にする／mu²をPoisson varianceから落とす負対照を検出する。
今回kappa=-.0440025182、full Lambda=.028、jump logvariance=.00035。
正しい一般momentは
\[
E[(X/S)^p]=\exp\{pc+(p^2-p)W/2+
\Lambda[e^{p\mu+p^2\sigma_J^2/2}-1-p\kappa]\}.
\]
補償だけから一意な市場jump premiumは導かない。

U-clock normalizer=.95。1分でW=8.5684296211e-7、sqrt(W)=.0009256581。
calendar carryへW/vol²やremaining/252を代入しない。
Lambda(t)=.028×|(t,T]∩[15:30,16:00]|seconds/1800。
pulseは確実に1回発生する原子的ScheduledJumpと別で、pulse境界でLambdaは連続・傾きだけが変わる。
t=expiryではtau_c=W=Lambda=0。post-expiryをnegative clockで価格化しない。

## 3. PW／LR／hybrid GammaとBrownian conditioning

W>0で、f(x;S|N,J)のscoreは
\[
\ell_S={Z_B\over S\sqrt W},\qquad
{f_{SS}\over f}=\ell_S^2+\partial_S\ell_S
={Z_B^2-Z_B\sqrt W-1\over S^2W}.
\]
payoffはlocal Lipschitz、multiplierの指数momentsは有限、spot lawは線形なのでPW Deltaの期待値交換が成立する。
\[
Y_C=D(X-K)^+,\quad
Y_\Delta^{PW}=D{X\over S}1_{X>K},\quad
Y_\Delta^{LR}=Y_C{Z_B\over S\sqrt W}.
\]
PW Deltaへdensity LRを適用すると、固定xでpartial_S(x/S)=-x/S²も必要：
\[
Y_\Gamma^{LRPW}=D{X\over S^2}1_{X>K}
({Z_B\over\sqrt W}-1),\quad
Y_\Gamma^{LR2}=Y_C{Z_B^2-Z_B\sqrt W-1\over S^2W}.
\]
indicatorを普通に再微分したPW Gamma=0は負対照。digital PW=0とcall PW Deltaを混同しない。
方法と交換条件は [Broadie–Glasserman 1996 著者機関PDF](https://business.columbia.edu/sites/default/files-efs/pubfiles/1848/estimating.pdf) §2–3／Appendix A/Cを確認し、このclock/pulseへの拡張式は本レビューの独立導出である。

A=exp(c-kappa Lambda+J)、d2=[log(SA/K)-W/2]/sqrt(W)、d1=d2+sqrt(W)として
\[
Y_C^{cond}=D[SA\Phi(d1)-K\Phi(d2)],\
Y_\Delta^{cond}=DA\Phi(d1),\
Y_\Gamma^{cond}={DA\phi(d1)\over S\sqrt W}.
\]
これはBrownian全体の厳密積分で、payoff rampの置換ではない。Lambda=0なら全randomnessが消え、actual draws=0／analytic_deterministic／SE0でよい。予約sample slotsを観測MC件数と呼ばない。

Expiryは(S-K)^+。S≠KはDelta0/1・Gamma0、S=Kの通常Delta/Gammaは未定義。正のWのATM Delta→.5という極限をexpiryの普通微分へ割り当てない。W=0をLR分母へ通さない。

## 4. 条件付きNの独立級数・density・tail bound

\[
m_n=\log S+c-\kappa\Lambda-W/2+n\mu,\quad
v_n=W+n\sigma_J^2,\quad
B_n=e^{c-\kappa\Lambda+n\eta}.
\]
d2_n=(m_n-log K)/sqrt(v_n)、d1_n=d2_n+sqrt(v_n)と置けば
\[
(C_n,\Delta_n,\Gamma_n)=
D\left(SB_n\Phi(d1_n)-K\Phi(d2_n),\
B_n\Phi(d1_n),\
{B_n\phi(d1_n)\over S\sqrt{v_n}}\right).
\]
ordinary Pois(Lambda)の重みで合成する。count lawとBrownian conditioningを二重にtiltしない。

別density algorithmはa_n=(log K-m_n)/sqrt(v_n)、H_n(z)=(exp(m_n+sqrt(v_n)z)-K)で
\[
C_n=D\int_{a_n}^{\infty}H_n(z)\phi(z)\,dz,
\]
\[
\Delta_n=D\int_{a_n}^{\infty}H_n(z){z\over S\sqrt{v_n}}\phi(z)\,dz,
\quad
\Gamma_n=D\int_{a_n}^{\infty}H_n(z)
{z^2-z\sqrt{v_n}-1\over S^2v_n}\phi(z)\,dz.
\]
Gammaの別boundary-density identityは
\[
\Gamma_n=D{K^2\over S^2}f_{X|n}(K)
=D{K\over S^2\sqrt{v_n}}\phi(a_n).
\]
density積分はCDF／core teacherを呼ばず、exp(m+sqrt(v)z)phi(z)=S B_n phi(z-sqrt(v))の平方完成でoverflowを避ける。tiny WのGamma score integralの正負cancelを、そのboundary値で検知する。

Lambda*=Lambda exp(eta)に対して
\[
p_\Lambda(n)D B_n=e^{-q\tau_c}p_{\Lambda^*}(n)
\]
なので、n>nmaxの正の残余は
\[
B_C=S e^{-q\tau_c}SF_{\Lambda^*}(nmax),\
B_\Delta=e^{-q\tau_c}SF_{\Lambda^*}(nmax),\
B_\Gamma={e^{-q\tau_c}SF_{\Lambda^*}(nmax)\over S\sqrt{2\pi W}}.
\]
草案のboundは成立する。さらにGamma分母をsqrt(W+(nmax+1)sigma_J²)へ置換すれば厳しくできる。W=0でn0項がatomになる別契約の普通Greekをこの式で補うことはしない。

例Lambda=.028、S∈[100exp(-.05),100exp(.05)]、1分Wでnmax=6：
tail C≤2.01e-13、Delta≤1.91e-15、Gamma≤8.65e-15（sharper3.03e-17）。
固定nmax=8でも十分安いが、各metric／各inputのtail budgetを保存する。

既存Merton価格の別照合はtau_c>0でsigma_eff=sqrt(W/tau_c)、lambda_eff=Lambda/tau_c。
expiryで0/0を作らない。これは既存reweighted実装とのアルゴリズム比較であり、Merton原文の同一clock実験再現ではない。原著本文は今回のweb取得が403等で不可、**未読**。書誌 [Merton 1976 DOI](https://doi.org/10.1016/0304-405X(76)90022-2)のみを区別して記録する。

## 5. compact IIDの数学的契約

M original IID slots、n0=M-m、y0=(C0,D0,G0)、nonzero m個の3-vector yjを保存する。
\[
\bar y=(n0\,y0+\sum_j y_j)/M,\quad
M2=n0(y0-\bar y)(y0-\bar y)^T+
\sum_j(y_j-\bar y)(y_j-\bar y)^T.
\]
Cov(mean)=M2/[M(M-1)]、SEはその対角平方根。
active群のmean bとcentered M2_AからChan結合すると
\[
M2=M2_A+{n0\,m\over M}(b-y0)(b-y0)^T.
\]
m=0、n0=0を別branchにする。単純な二乗和−M mean²はcancelに注意。
active-onlyのddof／SE、known p0へn0/Mの暗黙置換、price/Greek個票のclipは誤る。

これはconditioned教師multisetのlossless compact化である。original indicesも保存すれば元のslot順序を復元できる。raw PW/LR/CRNには独立Brownian drawsを要し、compact条件付き3-vectorだけからraw分散を復元しない。count_seed/jump_seed、active-only Gaussian消費規則、actual full M Poisson drawsとm jump draws、Lambda0の0 drawsをbindする。

1分eventの期待nonzeroはM=2^14/16/18で15.28/61.14/244.55。
30秒は7.64/30.58/122.31、最小Mで全count0の確率4.78e-4。
count>=100／SE gateのformal規則は主1分以上に限定し、30秒・1秒診断の未支持を主datasetと混ぜない。
非zero数が十分でも価格を作るpositive jump tailの有効数は少なく、3streams＋oracle比較を省略しない。
full Nにprefixを使う候補選択の観測は独立反復ではない。

## 6. 少数の独立数値probeと推奨許容差

MC／学習／大sweepは未実施。4例（1分ATM no/event、30分S95 event、390分S105 event）のcount n=0/1についてmath.erfc CDFとadaptive payoff/LR Delta/LR2 Gamma／hybrid integralを照合。
最大price差8.2e-15、Delta差2.95e-13、Gamma差1.44e-13。
ordinary mixtureとexisting reweighted Merton価格差は最大7.65e-15。
1分ATMはno-event (C,D,G)=(.0369312679,.5002092415,4.3098225499)、event (.0409347297,.5177487839,4.3016755102)。

正式planのoracle候補C atol1e-9 K＋rtol1e-10、Delta atol1e-9＋rtol1e-10、K Gamma atol1e-7＋rtol1e-9はこのprobeを十分含む。独立reference testsでは更に厳しいC abs1e-10、Delta abs1e-10、Gamma abs1e-10＋rel1e-9を候補にする。tiny-tailの相対誤差だけで合否を作らない。Poisson tail、quad error estimate、eps/4再計算差へ各予算を別々に割り当てる。

3幅h=[.02,.05,.1]S sqrt(W)を維持する。CRN MCはまずoracle finite-h値へ検算し、そのfinite-h値と真Greekのbiasは別列。固定.001S bumpを短期Gammaの真値には使わない。有限差分の実測精度はhを縮めた収束とcancelの両方を確認してから固定する。

NN候補精度／N／cost capsはpilot前の工学的候補。教師成立、paired3seedのDelta改善、Gamma利用、強baselineとの同精度費用回収は別decisionとして残す。3seed／6SEから普遍的優位やcoverageを主張しない。

## 7. 原目的・境界・未検証

正式planはlinear C/K、spot chain、同じconditioned price labels、Gamma診断のみ、3paired seeds、C²価格補間器、freeze後main、全費用／元分母を含み、既存designの原目的に沿う。

このv1の欧州終値は決定論的W/Lambdaのexact terminal lawなのでEuler biasはない。Full Batesのstochastic variance／vol-price相関、PIDE jump-operator、Gamma/vega supervision、market較正、rough variance、dynamic hedgeには追加教師／参照が必要。[Sakuma v5一次論文](https://arxiv.org/abs/2603.07600v5)のBates/PIDE/3stage／rough研究との境界を維持する。著者のspeedup／hedge結果をこの縮小v1へ移さない。

まだ未検証：実装の極小W/underflow、expiry普通Greek mask、clock/calendar guard、compensator負対照、compact復元、全pilot precision/rare counts、ref convergence、学習6fitの達成精度、Gamma sign/shape、cold費用、補間精度、速度回収。以上はTDD→pilot→独立freeze reviewで確かめる。本稿は実装の承認記録ではない。

## 8. 読んだsource／出典fingerprint

- 草案 /tmp/rbf05-short-maturity-draft.md SHA256 6438f419f5886d6b9e2cef47a9dedb099e2064b2d46c4237c3aa01ed7d4488a0
- RB-F05_DESIGN.md aef098a33a893c3f41bb4d003ea32bb3b0e799de493dc35fa335c40eb076c62d
- _digital_teachers.py a2a826248938d75ca835f2e322533777069ef72215ccc5a493599a277331cdcf
- zero_dte.py e8f99291613b17e0ffb6a29535d9ea08a2ab604e7116513164e91eca6dc07265
- alternative_models.py a1b6001c1c508598240b806f0fa282bde2d5e9290ca4ff1c38a92baaa4cd64d0
- 正式spec/plan 2026-10-09-short-maturity-dml-design.md／2026-10-09-short-maturity-dml.md のcurrent版を再読。rootが並行編集するdocsの最終字句承認ではない。
- Broadie–Glassermanのlocal原文抽出 §2–3／Appendix A/C、著者機関PDFをweb確認。Merton原文本文は今回未取得。Sakuma v5のmetadata／localモデル境界を確認。

この設計レビューではsource／Gitを変更せず、指定/tmp本文のみ保存した。次の独立参照実装はrootから別途割当済みで、最終fresh reviewは別reviewerが担当する。

## 追記: 候補Nと独立参照の実装確認

- 42 event候補のconditioned price教師をordinary Poisson/normal mark密度で独立中心2次moment積分した。最大は390分、S=105.168670715、Var=1.17279024246。予測SEは2^18で.00211514532、2^20で.00105757266。価格SE<=.002を維持して2^20をpilot候補へ追加する根拠がある。観測SE・rare count・全stream・Delta/Gamma gateは正式pilotで別確認する。
- 参照担当への実装許可を受け、reference_methods.pyとtest_short_maturity_independent.pyの2ファイルをTDD実装した。core関数を呼ばずdataclass属性のみを読む。40件の実装欠如REDを確認後、expiry ATM FDの対称傾き0.5隠蔽とsigned splitのDelta quadrature報告誤差を各1件REDで捉えた。現対象47PASS、ruff PASS。
- density_quadはcash payoff×densityとLR first/second scoreを積分し、Gamma boundary-densityをprimary値として独立保存する。LR2Gammaとそのquadrature誤差はwitness。Poisson truncation bound、QUADPACK誤差推定、浮動小数点誤差は意味を分ける。Gamma primaryのquadrature誤差0は解析densityで積分を使わない意味であり、完全な数値誤差0を主張しない。
- 正式pilot候補84slotのdeterministic oracle事前確認でCDF/density最大差[C,Delta,Gamma]=[1.0853e-14,2.2205e-15,8.8818e-16]、eps/4再計算最大差[8.8818e-16,4.4409e-16,0]、既存reweighted Merton価格最大差1.9985e-14。全slotでreference各誤差予算/4とstatus gateを満たす。これはMC pilot・6fit・主結果の受入ではない。
- 完了後のfresh最終reviewは別reviewerが担当する。独立参照実装者による本追記は数学設計と担当コード検証の範囲だけ。

追加証拠: /tmp/rbf05-price-variance-probe.md/.json、/tmp/rbf05-independent-reference-preflight.json。
