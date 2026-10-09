# RB-F06 独立参照の実装報告

2026-10-09。担当範囲は research/RB-F06/reference_methods.py と
hullkit/tests/test_sabr_identifiability_reference.py のみ。Git操作なし。
公開API、sabr.py、production依存は変更していません。

## 出典と参照の役割

- Hagan, Kumar, Lesniewski, Woodward (2002), Managing Smile Risk,
  原著 (2.17a-c)、ATM (2.18)、Black (2.4)。
  著者URL: https://lesniewski.us/papers/published/ManagingSmileRisk.pdf
  原著PDF mirror:
  https://derivativesacademy.com/storage/uploads/files/modules/resources/1702213496_hagan_kumar_lesniewski_woodward_managing_smile_risk.pdf
  mirrorは原著本文を置いたものとして参照し、サイト解説は使わない。
  webではmirrorの原著本文を取得できたが、その後の式位置への再openと
  著者URLはtimeout。WSL直接fetchはnetwork unreachable。
  最終照合はrepositoryの原著抽出paper.md:290-308と原著crop画像で実施。
  local source PDFはmetadataのsource_pdf_sha256に一致:
  c267782462f7e762455c481cbdd32e41f2f984c74e89708796836d80515aeaca。
  抽出paper.mdのATM(2.18)にはsigma²とrho²のOCR混同がある。
  原著p0009-block-0015画像ではrho²を確認し、実装は原著cropに従う。
  一般式(2.17a)のcoefficients/分母とz/x(z)定義、ATM極限を照合済み。
  原著の抽出本文・画像・metadataは変更していない。
- 独立Hagan転記との一致は同じ漸近近似写像の実装検査。
  exact SABR価格・SDE動学・裁定不在の検証ではない。
- beta=1, nu=0はSDEのlognormal解析極限。
  rhoが価格法則から消えることと、Black価格 vs 正規密度payoff積分を別に検査。

## インターフェースと方法

theta=(a,rho,nu), a=alpha/F**(1-beta)。

1. independent_hagan_vols(F,T,beta,theta,strikes)
   dimensionless m=a exp((1-beta) log(F/K)/2)で原著式を転記。
   z/x(z)はrationalized log1pと小zの3次展開。
   public abs(z)<1e-6 の一次近似にはない2/3次項を保持するため、
   小zで微小な差はあり得る。一般価格モデル誤差と混同しない。

2. black_calls(F,T,strikes,vols)
   undiscounted、独立vector Black式。T=0またはvol=0はintrinsic。

3. flat_lognormal_quad(F,T,strike,alpha)
   正規密度とlognormal payoffの積をquadで積分。
   Completing-squareで無限端点のexp overflowを避ける。
   CDF/Black helperは呼ばない。このexact limitだけの独立価格参照。

4. independent_jacobian(...,noise_scale=.0005,h=1e-4)
   u=(a/.20,rho/.50,nu/.50)について d(IV/noise_scale)/du を返す。
   内部点は5点stencil。物理領域から出ないよう極端な点ではhを縮める。
   nu=0は3列を解析化し、正のnuへこの境界式を延長しない。

   L=log(F/K), b=1-beta, m=a exp(bL/2),
   D=1+b²L²/24+b⁴L⁴/1920, c0=b²m²/24 に対し、
   dIV/da=(m/a)(1+3c0 T)/D,
   dIV/drho=0,
   dIV/dnu=rho[-L(1+c0 T)/2+beta m²T/4]/D。
   rho=nu=0はrank1。rho!=0,nu=0のnu列は一般に非零。
   public log cancellationによる偽の弱特異値を引き継がない。

5. independent_fixed_fit(...,fixed=None,max_nfev=250)
   fixed={index:value}, index 0=a,1=rho,2=nu。
   production TRFと独立なSLSQP。scaled座標、同じresearch bounds:
   a[.05,.50],rho[-.95,.95],nu[0,1.5]。
   保存Q=sum(((IV-y)/.0005)**2)。
   最適化中はQ/10000を使い勾配量を調整（minimizerは同じ）。
   5点/解析Jacobianから独立勾配を計算する。
   max_nfevは実objective呼出の予算。Jacobian内の写像評価は含まない。
   予算不足をsuccess=False,status=9で保存し、有限best点を返す。
   all-fixedは1回のobjective評価。callerのstart配列を変更しない。
   return: theta,q,success,status,message,nfev,seconds,method,objective_scale。
   secondsはtimeの記録字段。solver successは局所停止で、大域保証ではない。

## TDDと検証

BLAS=1、PYTHONPATHはこのworktreeのhullkit/src。
runtime=/home/kazumasa/projects/.venv/bin/python。

コマンド:
python -m pytest johnhull/hullkit/tests/test_sabr_identifiability_reference.py -q

- 初回RED: 21 failed in 0.60s。全件が参照module未実装のassertで失敗。
- 最初のGREEN: 21 passed in 0.50s。
- ndarray startがfixed適用で変わることを追加regressionで検出:
  1 failed,21 deselected in 0.54s。fit内のtheta.copy()で原因を修正。
- 最終GREEN: 22 passed in 0.50s。
- ruff check: import順と内部例外Error suffixを整理し、全件PASS。
- ruff format --check: 2 files already formatted。

主な検証: rho3値のflat15点、Black vs quad5strike・ATM価格
7.965567455405804、beta3値での非零nu原著転記 vs public、
nu0/rho0 rank1、nu0/rho±.3の解析列、5点 vs 別2点差分、
fixed-axis nuisance再最適化、全fixedのQ=1.12、budget1失敗保持、
public SABR禁止guard、数学的未定義入力、start不変性。

全suite・protocol/pilot/main・独立最終レビューはroot担当。
この報告でmain研究受入・一般exact SABR参照・較正の大域性は主張しない。
