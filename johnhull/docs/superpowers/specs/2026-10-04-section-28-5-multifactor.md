# M30 §28.5 Extension to Several Factors — design

日付2026-10-04。P3全37節の第5受入単位。基点はM29 main統合後commitをplan ledgerへ固定。原典Hull GE pp.679–680/脚注7、補助Problem28.12 p686。印刷数値pinなし、独立数値fixtureはsynthetic。

## Requirements

元D28.5-01/02をMF01–06へ具体化して全5軸。n個独立WienerのQ drift r/一般world r+lambda・s、比の相対Itô driftとlog drift、g-world lambda=s_g、有限GBMでの真の条件付きmartingale、同一給付価格、相関から独立basisへの直交化を扱う。
C=L L^T、相関loading row s L、gのdrift r+s_f^T C s_g / r+s_g^T C s_g。相関座標のrisk vectorはC s_g。PSD退化でinverse不要。金利が確率的でも点ごとのdrift相殺は成立。GBM価格teacherの一定rという限定はM29確率金利契約を置き換えない。

## Private numerical contract

新private _multi_factor_martingales.py。公開export/signature/production依存変更なし。
correlation_factor(C)->L、factor_ratio_drift(mu_f,mu_g,s_f,s_g,C=None)、factor_numeraire_drifts(r,s_f,s_g,C=None)、factor_ratio_conditional_mean(value,mu_f,mu_g,s_f,s_g,h,C=None)。Cはsingle nonempty NxN、loadingのfinalaxis N>0、scalar loading拒否。leading batchのみbroadcast。有限real numeric i/u/f、temporal/bool/string/object/complex拒否。domainはbroadcast前、value>0/h>=0、signed rates/loadings可。empty batch可/emptyfactor不可。overflow/positive moment underflow/invalidshape/非PSDはValueError。
Cは対称/unit diagonal/PSD、近傍丸めのみ64 eps N ||C||2に基づき許容。最初に|Cij|<=1+roundoffを検査し、大きな無効行列をlarge-scaled toleranceで受容しない。L自体の成分/符号をpinしない。Cを2回掛けない。scalarsはfloat、batch ndarray。

## Independent acceptance

独立math.fsum bilinear + scipy Gaussian quadrature、production importなし。11市場/132条件付き状態、n1/n2/n3/rho±1/nearPSD/zero/signed/負rate/時刻0。現在ratio .65/1.25/2、h0/.25/1/2.5。t=0やratio退化の場合の異なる現在値は別の初期市場を表し、単一市場で実現した別状態とは主張しない。conditional mean/second moment、same f call Q/3g、covariance/orthogonalrotation invariant、raw direct MC262144/5SE（SE0はabs1e−12）。drift abs1e−12、quad mean1e−10、price1e−9、PSD/rotation scaled machine tolerance。閾値を出力に合わせて緩めない。
wrong cross sign/missingC/doubleC/wronggdrift/missingrandomg/oldinitialratio/missingRNの変異拒否。保存結果消費gateはre-signed改変でも拒否。

## Lesson and distribution

vol10 §6D.1–6D.6、新11セル/旧257本文・保存出力・Plotly保持。4共有図：factor_ratio_ito/factor_ratio_conditional/factor_basis_covariance/factor_measure_price。同一市場価格と違う市場価格を区別。Book/portal×1440/1000=16状態、MathJax、700px以上、値/label/SE/表示変異/実目視。registry198/exotics86、public72/private33予定（実生成値と照合）。Book旧144+Plotly4。
29既受入節D1/個別tests/browser/runtime/両保管庫、統合gate/updaterfail-before-write、台帳30/276/P3 5/37。全suite/ruff/4checks/tracked release/1fresh最終レビュー、重要TDDfix一回、mainFF/push/live remote一致。次M31 §28.6。全P3はactiveを維持。
