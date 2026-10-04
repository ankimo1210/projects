# 二因子Hull-White: 独立ガウス積分とTN14照合

2026-10-04。読み取り専用の独立数学監査。repo/Git/テスト/親fixture/既存flexicap memoの変更なし。追加探索なし。

## 原典の固定

- `/tmp/p3-input-recovery/TechnicalNote14.pdf`、物理=印刷p1-4、全4ページを抽出・画像確認。
- SHA256を実ファイルで確認: `9068c1d786837a5946fc7a3cd2114cafc4edb0293975f70508b4cadedc31af5f`。`/tmp/p3-input-recovery/download-records.json`の既存記録と一致し、元原本のSHAは既に固定されている。記録ファイルは変更不要・未変更。
- archive commit: `9b8dbfe37661dbd3de65d3a1489dc1297e840de7`、git blob SHA（取得記録）: `dccb5d395680ee0bf1fea9bef8ab0c2ed56a83af`。
- 原本URL: https://raw.githubusercontent.com/rotmanfinhub/john-hull-textbook-resources/9b8dbfe37661dbd3de65d3a1489dc1297e840de7/Options%2C%20Futures%2C%20and%20Other%20Derivatives%2C%2011th%20Edition/Technical%20Notes/TechnicalNote14.pdf
- Hull 11e Global原本 `/home/kazumasa/worktrees/m29/johnhull/options, futures and other derivatives 11th.pdf` §31.5、物理=印刷p728を画像確認。本文はthetaを含まないequilibrium SDE、TN14はtheta(t)を導入して初期カーブに合わせるモデル。この差を黙って同一視しない。

## 1. モデル・単位・核

リスク中立測度で
\[
dr_t=[\theta(t)+u_t-a r_t]dt+\sigma_1dW_{1t},\qquad
 du_t=-bu_tdt+\sigma_2dW_{2t},\quad d\langle W_1,W_2\rangle_t=\rho dt.
\]
定数係数、\(|\rho|\le1\)、有限horizon。通常a,bは正。時間単位は年、rとf0は年率decimal。uとthetaはrate/year、sigma1はrate/sqrt(year)、sigma2はrate/(year sqrt(year))。uはG2++の第2短期金利因子と同じ単位ではない。

\[
B_a(h)=\int_0^h e^{-as}ds=\frac{1-e^{-ah}}a,\quad
H_{ab}(h)=\frac{e^{-bh}-e^{-ah}}{a-b},\quad
C_{ab}(h)=\int_0^hH_{ab}(s)ds=\frac{B_b(h)-B_a(h)}{a-b}.
\]
\(B'=e^{-ah}\)、\(C'=H=B-bC\)。Bはyear、Cはyear²。TN14 p1と本文式31.14のCはこの式と一致する。

## 2. 条件付き短期金利積分と厳密債券価格

\(h=T-t\)、\(I_{tT}=\int_t^T r_sds\)。SDEの線形解を積分し、確率積分の順序を入れ替えると
\[
I_{tT}=B_a(h)r_t+C_{ab}(h)u_t+\int_t^TB_a(T-s)\theta(s)ds
 +\sigma_1\int_t^TB_a(T-s)dW_{1s}
 +\sigma_2\int_t^TC_{ab}(T-s)dW_{2s}.
\]
したがって条件付き平均は最初の3項、条件付き分散は
\[
V(h)=\int_0^hQ(v)dv,\quad
Q(v)=\sigma_1^2B_a(v)^2+\sigma_2^2C_{ab}(v)^2+2\rho\sigma_1\sigma_2B_a(v)C_{ab}(v).
\]
\(Q=(\sigma_1B+\rho\sigma_2C)^2+(1-\rho^2)\sigma_2^2C^2\ge0\)。Gaussianの指数モーメントから、近似なしで
\[
P(t,T)=\exp[-B_a(h)r_t-C_{ab}(h)u_t-\int_t^TB_a(T-s)\theta(s)ds+\tfrac12V(h)].
\]
ゆえに\(\ln A_\theta=-\int_t^TB_a(T-s)\theta(s)ds+V(h)/2\)。本文p728のtheta=0モデルなら\(A=\exp[V(h)/2]\)であり、任意の市場初期カーブを自動的にfitするモデルではない。

厳密な状態と積分のjoint Gaussianを必要とする場合、noise kernelは\((r_T,u_T,I_{tT})\)順で
\[
g_1(v)=(e^{-av},0,B_a(v))^\top,\qquad
g_2(v)=(H_{ab}(v),e^{-bv},C_{ab}(v))^\top.
\]
共分散は\(\int_0^h[\sigma_1^2g_1g_1^\top+\sigma_2^2g_2g_2^\top+\rho\sigma_1\sigma_2(g_1g_2^\top+g_2g_1^\top)]dv\)。正規乱数の相関rhoをそのまま終点state相関と見なしてはいけない。

## 3. 初期カーブ適合: total shiftとTN14のphiを区別

正で十分滑らかな市場割引曲線\(P_0(T)\)、\(f_0(T)=-\partial_T\ln P_0(T)\)とする。u0=0、centered state x0=0を置き、\(r_t=\varphi(t)+x_t\)、\(dx=(-ax+u)dt+\sigma_1dW_1\)。初期曲線は
\[
\ln P_0(T)=-\int_0^T\varphi(s)ds+\tfrac12V(T).
\]
満期で微分して
\[
\boxed{\varphi(t)=f_0(t)+\tfrac12V'(t)},\quad
\psi(t):=\tfrac12V'(t)=\tfrac12Q(t),\quad
\boxed{\theta(t)=\varphi'(t)+a\varphi(t)}.
\]
初期境界は\(r_0=\varphi(0)=f_0(0)\)。TN14 p4の\(\phi(t,T)\)はtotal shiftではなく\(\psi(T-t)\)である。名称の違いを区別すれば、volatility correction自体は一致する。

fit後の厳密式は
\[
\ln P(t,T)=\ln\frac{P_0(T)}{P_0(t)}-B_a(h)[r_t-\varphi(t)]-C_{ab}(h)u_t
 +\tfrac12[V(h)-V(T)+V(t)].
\]
従って\(\ln A=\ln[P_0(T)/P_0(t)]+B_a(h)f_0(t)-\eta\)、
\[
\boxed{\eta=\tfrac12[V(T)-V(t)-V(h)]-B_a(h)\psi(t)}.
\]

## 4. TN14 p3のeta・gamma1..6: 全て一致

\(B(z)=B_a(z),C(z)=C_{ab}(z),H(z)=H_{ab}(z),h=T-t\)と置くと、印刷された閉形式の各gammaは厳密に次の積分を表す。

| TN14変数 | 独立に確認した意味 |
|---|---|
| gamma1 | \(\int_h^T e^{-az}H(z)dz\) |
| gamma3 | \(\int_0^t e^{-az}H(z)dz\) |
| gamma2 | \(\int_h^T B(z)C(z)dz\) |
| gamma4 | \(\int_0^t B(z)C(z)dz\) |
| gamma5 | \(\int_h^T C(z)^2dz\) |
| gamma6 | \(\int_0^t C(z)^2dz\) |

証明の要点: gamma1/3は指数を直接積分。gamma2の角括弧を積分形へ変えると、被積分関数は\(e^{-az}H-H-BB'+B=(1-e^{-az})(B-H)=abBC\)。gamma4は同式のh=0版。gamma5/6は\((C^2/2)'=BC-bC^2\)を積分すれば得られる。

これらを上の独立etaへ代入すると
\[
\eta=\frac{\sigma_1^2}{4a}(1-e^{-2at})B(h)^2
-\rho\sigma_1\sigma_2[B(t)C(t)B(h)+\gamma_4-\gamma_2]
-\tfrac12\sigma_2^2[C(t)^2B(h)+\gamma_6-\gamma_5],
\]
つまりTN14 p3の全項・符号と一致する。gammaは高次の差/除算を含む閉形式なので、a=b等の境界では上の積分定義が連続拡張を与える。etaの式に真正な不一致は見つからない。

## 5. TN14 p4の偏微分添字: literalには採用できない

印刷式は\(\theta(t)=F_t(0,t)+aF(0,t)+\phi_t(0,t)+a\phi(0,t)\)で、subscriptをpartial derivativeと説明する。しかしp3では\(F(t,T)\)を観測時刻t・満期Tのforward rateと定義し、p4の\(\phi(t,T)=\psi(T-t)\)。したがってfirst argumentのpartialとして読むと
\[
\partial_t\phi(t,T)=-\psi'(T-t),\qquad \partial_T\phi(t,T)=+\psi'(T-t).
\]
カーブ適合に必要なのは満期方向の微分であり、矛盾を避けた明確な表記は
\[
\boxed{\theta(t)=\partial_TF(0,T)|_{T=t}+aF(0,t)
+\partial_T\phi(0,T)|_{T=t}+a\phi(0,t)}
\]
または\(d[F(0,t)+\phi(0,t)]/dt+a[F(0,t)+\phi(0,t)]\)。初期カーブだけから未来の観測時刻方向の\(F_t\)を取得することもできない。これは印刷添字/説明の記法不整合としてflagし、黙ってfirst argument derivativeを実装してはいけない。修正すべき微分方向は独立導出で確定するが、著者による訂正済みという意味ではない。

## 6. a=bの可除特異点

\[
H_{aa}(h)=h e^{-ah},\qquad
\boxed{C_{aa}(h)=\frac{1-(1+ah)e^{-ah}}{a^2}=-\partial_aB_a(h)}.
\]
a=b=0ならB=h、H=h、C=h²/2。したがってモデルや条件付き債券価格に特異性はなく、a-bを分母にした表現だけが特異。TN14 p2の\(y=r+u/(b-a)\)変換はa=bでは利用不可だが、元の連立SDEと上のGaussian核は利用できる。

## 7. u0!=0の初期状態境界

TN14はp1でu0=0を明示する。u0!=0へそのままAを転用すると、r0=f0(0)であっても
\[
P_{\rm naive}(0,T)=P_0(T)e^{-C_{ab}(T)u_0}
\]
となり曲線適合が壊れる。一般にはさらに\(e^{-B_a(T)[r_0-f_0(0)]}\)が残る。

u0を明示的に保持しながらfitするなら\(v_t=u_t-u_0e^{-bt}\)、\(x_t=r_t-\varphi(t)\)をcenterし、
\[
\boxed{\theta(t)=\varphi'(t)+a\varphi(t)-u_0e^{-bt}}.
\]
債券式の\(-Cu_t\)を\(-C[u_t-u_0e^{-bt}]\)とし、\(\ln A\)へ\(+C_{ab}(h)u_0e^{-bt}\)を加える。同時にr0=f0(0)が必要。有限のthetaで瞬間短期金利のr0不整合を全満期にわたり補うことはできない。

## 8. rho=+/-1: 瞬間rankと有限step rankは異なる

rho=epsilon in {+1,-1}では瞬間diffusion covarianceはrank1（非ゼロvolatilityの場合）。しかし時間方向に異なる核が作用するため、有限h>0のstate (r,u) covarianceは通常rank2になり得る。

\[
M=\begin{pmatrix}-a&1\\0&-b\end{pmatrix},\quad
g=(\sigma_1,\epsilon\sigma_2)^\top,\quad
\det[g,Mg]=\sigma_2[\epsilon\sigma_1(a-b)-\sigma_2].
\]
このdeterminantが非ゼロなら有限step state covarianceはpositive definite。sigma2!=0かつ\(\epsilon\sigma_1(a-b)=\sigma_2\)の退化条件ではrank1。sigma2=0の場合はuがdeterministicなのでrank<=1。特にa=b、sigma2!=0ならdet=-sigma2²!=0で、rho=+/-1でも有限step covarianceはrank2。

TN14 p2のsigma3はrho=epsilonで\(|\sigma_1+\epsilon\sigma_2/(b-a)|\)。上記退化条件ではsigma3=0となり、印刷された新しいBrownian correlationは0/0で未定義。その枝ではyがdeterministicであり、任意のcorrelationを代入してはいけない。元のGaussian期待値/債券式は共分散がsingularでも成立し、逆行列を要しない。

結論: TN14のB/C・eta/gammaは独立Gaussian導出と一致。校正上の論点はp4微分添字、u0=0の適用境界、a=bの表現上の特異点、rho=+/-1のrank/変換退化である。