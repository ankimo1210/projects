# M31 §28.6 Black's Model Revisited — design

2026-10-04。P3全37節の第6受入単位。M30 main push済みcommitをexecutor ledgerのBASEに固定。原典Hull GE pp680–681、式28.26–28.29。印刷数値pinはなく、数値例はsynthetic。

## Original requirements BF01–06

1. T満期ZCB numeraireでcall／putの期待値を置く（28.26）。option給付日とforwardの満期は同じT、ST=FT。
2. T-forward worldでterminal forwardがlognormalと仮定、E_T FT=F0。実効sigma_F²Tはterminal logvarianceで、spot sigmaと区別（28.27）。
3. 28.28／28.29のBlack call／putとparity。確率金利でもQの経路割引価格とT外側DF価格は同じ。Qで割引因子を外へ出す一般化はしない。
4. futuresはQ平均、forwardはT平均で一般に代用不可。金利とspotの共分散が0になる特別例を一般則へ昇格させない。
5. investment／consumptionの市場forwardを価格入力にできる。consumptionのspot cost-of-carry式を仮定しない。
6. 単位／可積分性／条件／zero sigma・Tの極限／負金利とDF>1／入力domain。全小節と旧268保持、16表示・30D1・両保管庫・台帳全5軸。

## Private interfaces

New private `_forward_black.py`:

- `forward_black_price(discount, forward, strike, volatility, horizon, kind='call')`: float scalar／leading broadcast ndarray。discount/F/K>0、sigma/T>=0、kindはcall/put文字列のみ。sigma=0またはT=0はdiscount×intrinsic。外部市場forwardを使い、rateを逆推定しない。
- `gaussian_forward_statistics(spot, rate, rate_volatility, stock_volatility, correlation, horizon)`: 同じshapeのscalar／arrayを値に持つdict。spot>0、eta／sigmaS／T>=0、rho[-1,1]、negative r valid。keys `discount,forward,futures,forward_sigma,terminal_variance,mean_integral,variance_integral,mean_log_spot_Q,mean_log_spot_T,cov_integral_log_spot`。T0はDF1、forward/futures spot、variances/covariance0、mean_logS=logspot、forward_sigma=sigmaS（連続極限）。

finite real i/u/fをfloat化前に検査。temporal／bool（mixedlistを含む）／string／object／complexを拒否。domainはemptybatchのbroadcast前に検査。不正shape・非有限／overflow・正のDF/forward/futuresのunderflowはValueError。価格の完全なfloat域精度は保証せず、表現域を外れる極小tailは0となり得る。通常のdeep-tailとtiny-ATMは独立に精度検査し、許容差を出力に合わせて緩めない。新公開export/API・production依存なし。既存 ir_options._black／bond_option_blackのzero拒否契約は保持し、positive比較だけ行う。

Ho–Lee synthetic Q: dr=eta dWr、dS/S=r dt+sigmaS dWs、corr=rho。J=∫r、Y=logS。VJ=eta²T³/3、cJY=VJ+rho eta sigmaS T²/2、mY=logS0+r0T−sigmaS²T/2。VYはPSD-safe `T*(sigmaS+rho etaT/2)^2+eta²T³*(1/3−rho²/4)`。DF=exp(−r0T+VJ/2)、F=S0/DF、futures=S0 exp(r0T+VJ/2+rho eta sigmaS T²/2)、sigmaF=sqrt(VY/T)、T logmean=mY−cJY。M29 flat initial HWと混用しない。sigma_F(t)²=sigmaS²+2rho eta sigmaS(T−t)+eta²(T−t)²の積分を説明する。

## Independent acceptance

Productionをimportしない純math/erfc/Gaussian条件付き割引求積を教師とする。7市場×3strikes×callput42prices、provided-forward3、12zero/nearzero rows、parity、RN平均1、discounted spot、E_T ST=F0。Q条件付きJ|Y求積とT直接Y求積を別に計算。価格abs1e−9/rel1e−11、moment1e−10、MC5SE、cut12の解析tail bound。正値域で既存公開Blackと照合。

RawMC262144 fixedseed、Q joint(J,Y)exact bridge／T Gaussian tilt、density=exp(−J)/DF、自己正規化しない。sigmaS0/K140ではdirect0hits/SE0でも真のcall7.168352139439199e−8。stochastic varianceがある限りSE0をdeterministicPASSにせず、Gaussian importanceのraw likelihood、shift、hitcount、SEを記録する。確率的SEは消費時にfixedseed replayと完全照合し、jointly resigned mean/SE/z/digestも拒否する。

Wrong futures/spotvol/Q外側DF/RN方向/zero-SE/保存teacher/results/source/pathの負例を実際に拒否。teacher/source/result hashes・matrix/order・samples/control一覧の契約を消費時と統合gateで検査する。一般状態依存forwardのlognormal保証やzero-hitの統計的確定を主張しない。

## Lesson / delivery

vol10 §6E.1–6E.6、新11セル、旧268本文/保存出力/Plotly保持、全279fresh。4共有図 `forward_black_pricing,forward_black_expectation,forward_black_volatility,forward_black_limits`。Book/portal×1440/1000=16状態、MathJax・幅700px・全trace/SE・変異・目視。registry202/exotics90/private35、Book旧148+4Plotly=152予定。実生成の値で確認。

30既受入D1のcurrentproducer inventory／個別tests／browser/runtime／C-F両保管庫を検証。Integrated/updaterはmissing/stale/re-signed/path/store/matrixを台帳書込み前に拒否。31受入275未評価/P3 6/37。whole/ruff/4checks/strictrelease、1fresh finalreview、重要だけ1回TDDfix+whole/minor記録、mainFF/fresh/push/live一致。全P3目標はactive、次M32 §28.7。Ch33 flexicap入力不足はpendingのままで合成価格による受入に置き換えない。
