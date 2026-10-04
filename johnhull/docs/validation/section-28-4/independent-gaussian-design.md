# M29 exact joint Gaussian: independent reference and preflight

Date: 2026-10-04. Scratch only. Repository: /home/kazumasa/worktrees/m29.
The repository was read, not edited; no Git operation, production import,
notebook/browser acceptance, or final-review claim is included here.

Files:

- `/tmp/m29-gaussian-reference.py`: runnable independent scalar math/SciPy oracle.
- `/tmp/m29-gaussian-reference.json`: all finite outputs, `allow_nan=False`.
- This note: `/tmp/m29-gaussian-reference.md`.

Execute: `source /tmp/m29-env.sh; python /tmp/m29-gaussian-reference.py`.
Existing NumPy/SciPy only; no production dependency or public API proposal.
Financial inputs are synthetic, not Hull printed numeric examples. Original
§28.4 equations/requirements are mapped in the existing M29 source-design note;
this task did not repeat the source-page inspection.

## 1. Contract and units

Under Q, `dx=-a*x*dt+eta*dW`, `r=x+phi`, `phi(u)=r0+c(u)`,
`c(u)=eta^2 B(u)^2/2`, and `B(h)=(1-exp(-a*h))/a`.
The observed x_t is Q zero-mean OU state; it is not a forward-centered state.

- `a>0`, `eta>=0`, t and horizons in years.
- r0 and x are rate/year; eta is rate/sqrt(year).
- Brownian increment has sqrt(year) units; integral r is dimensionless.
- Stock loading is 1/sqrt(year), price inputs are nominal same-currency values.
- Simple rate `F=(P(t,T)/P(t,U)-1)/(U-T)` has rate/year units.
- Accruals are years; annuity is years times unit-notional bond price.
- Fix T and pay U are distinct, `t<=T<=U`, rate contracts require U>T.
- Annuity payments are strictly after T, accruals positive; negative rates/V/s
  are supported, A and DFs remain strictly positive.
- `eta=0` and `h=0` are exact degeneracies, not a fake epsilon variance.
- `a=0` is an analytic limit of the dimensionless formulas, not an expansion
  of the documented existing a>0 model boundary.

Production's scalar/broadcast API should validate inputs before the eta=0/h=0
branch: finite real numeric values, temporal/object-temporal rejection,
complex rejection, ordered times/schedule, shape contracts, positive S and K,
normal factor axis, representable exponentials. Empty-array bypasses of invalid
scalar parameters should not be allowed. No silent self-normalized RN weights.

## 2. Exact conditional Gaussian and rank 2

For h=T-t, future innovations have kernels, v in [0,h],

`K_X(v)=eta*exp(-a*(h-v))`,
`K_I(v)=eta*B(h-v)`, `K_W(v)=1`.

The reference integrates all kernel products independently with SciPy quad on
a unit interval, rather than importing a production covariance or bond price.

Mean vector for `(X_T, I_tT, W_T-W_t)`:

`m_Q=(exp(-a*h)*x_t, B(h)*x_t + integral_t^T phi(u)du, 0)`.

Covariances:

- `q=eta^2*(1-exp(-2*a*h))/(2*a)`.
- `v=eta^2/a^2*(h-2*B(h)+B_2(h))`,
  `B_2=(1-exp(-2*a*h))/(2*a)`.
- `c=Cov(X,I)=eta^2*B(h)^2/2`.
- `Cov(X,W)=eta*B(h)`.
- `Cov(I,W)=eta/a*(h-B(h))`.
- `Var(W)=h`.

Exactly `X_noise + a*I_noise = eta*W_increment`; the three-output covariance
has rank 2 for h>0, eta>0. A 3x3 Cholesky is therefore the wrong sampler.
Kernel covariance eigenvalues can show negative 1e-16-level roundoff even
when mathematically PSD. Do not reject this solely by an absolute unscaled
eigenvalue test or repair it by materially changing correlation.

The bond oracle comes directly from the Gaussian integral:

`P(t,T|x)=exp(-B(h)*x - integral_t^T phi + v(h)/2)`.

This covers the repaired public HW state's `-B*c(t)` convention. No public
HW function is used to create these expected values.

### Stable small-ah construction

Let u=ah, `b1(u)=(1-exp(-u))/u`, `b2(u)=b1(2u)`,

`d(u)=(1-b1(u))/u`,
`e(u)=(1-2*b1(u)+b2(u))/u^2`.

Then `Cov(I,W)=eta*h^2*d`, `Var(I)=eta^2*h^3*e`.
Near zero use:

`d = sum_k (-u)^k/(k+2)! = 1/2-u/6+u^2/24-u^3/120+...`,

`e = sum_k (-u)^k*(2^(k+2)-2)/(k+3)!`
`  = 1/3-u/4+7u^2/60-u^3/24+31u^4/2520+...`.

For two independent standard normals z1,z2:

`W = sqrt(h)*z1`,
`I_noise = eta*h^(3/2)*(d*z1 + sqrt(e-d^2)*z2)`,
`X_noise = eta*W - a*I_noise`.

This generates the dependent three outputs from two factors and keeps the
small integrated-rate noise directly representable. It avoids subtracting
two almost equal O(sqrt(h)) samples to recover an O(h^(3/2)) integral.
`e-d^2 -> 1/12` is well conditioned at u=0. In the scratch proposal, 20-term
series are used for u<=0.1 and ordinary expm1 expressions beyond that.
At u=0.1001 the absolute dimensionless discrepancy is 1.75e-14, still inside
the fixed 2e-12 budget. This is a proposal, not a required public interface.
The separate oracle integrates positive kernels and does not use these series.

Stability fixtures: u=0,1e-16,1e-12,1e-8,1e-4,.01,.1,.1001,1,4,10,100.
All rank-2 factors match the kernel covariance within 2e-12. At u=100,
residual `e-d^2=4.900000000000173e-7` remains positive. No clipping was
needed. Joint fixtures also include h=1e-12, a=1e-8, eta=0, negative r0,
nonzero observed x_t, and h=0.

## 3. Payment measure at U>=T

At T, conditional RN density is proportional to

`exp(-I_tT)*P(T,U|X_T) / P(t,U|x_t)`.

Constants in P(T,U) do not affect the Gaussian mean tilt:

`l=(-B(U-T), -1, 0)`, `m_U=m_Q + covariance*l`.

Covariance is unchanged. Explicit shifts:

- `delta m_X = -c - B(U-T)*q`.
- `delta m_I = -v - B(U-T)*c`.
- `delta m_W = -Cov(I,W)-B(U-T)*Cov(X,W)`.

For U=T this is the ordinary T-bond measure. Merely shifting X and leaving
its correlated integral/stock driver unchanged is inconsistent. Term-rate
expectation can use just the X marginal, but a common stock/discount sampler
must shift all relevant components coherently.

## 4. Same stock call, futures versus forward

Synthetic same-currency non-dividend stock:

`log S_T = log S_t + I_tT - sigma_S^2*h/2 + sigma_S*(W_T-W_t)`.

Let `Y=log S_T`,
`vY=v+sigma_S^2*h+2*sigma_S*Cov(I,W)` and
`cYI=v+sigma_S*Cov(I,W)`.
Q mean is `log S_t + m_I - sigma_S^2*h/2`.
T mean is Q mean minus cYI; variance stays vY.

- Futures oracle = `E_Q[S_T]=exp(mY_Q+vY/2)`.
- Forward oracle = `E_T[S_T]=S_t/P(t,T)`.
- Q call oracle integrates `E[exp(-I)|Y]*(exp(Y)-K)+` in Y.
- T oracle independently integrates `P(t,T)*(exp(Y)-K)+` under tilted Y.
- erfc closed call is a third path using vY, without a production Black API.
- Wrong external-Q-discount example = `P(t,T)*E_Q[(S_T-K)+]`.
- Forward PV = `S_t-K*P(t,T)` on both expectation paths.
- Raw `E_Q[exp(-I)/P(t,T)]=1` is checked, without dividing by sample mean.

Base a=.2,eta=.02,r0=.04,t=0,T=2,S=100,K=105:

| signed sigma_S | futures Q | forward T | call Q=T | wrong external Q discount |
|---:|---:|---:|---:|---:|
| +.25 | 109.37244366983968 | 108.32870676749582 | 16.37161863952692 | 16.96123385289017 |
| -.25 | 107.46647739330601 | 108.32870676749592 | 14.45790389538092 | 13.98222673307748 |
| 0 | 108.41527219490550 | 108.32870676749582 | 3.262096905703644 | 3.331721538361990 |

A zero stock Wiener loading does not remove its integrated stochastic-rate
risk. eta=0 does make cash discount deterministic and futures=forward.
18 fixtures include t=.25/x=-.015, t=.75/x=.02, eta=0, r0=-.01/x=-.02,
and zero horizon. Max Q/T price discrepancy 2.5757e-14.

## 5. Term fixing and overnight realization

For delta=U-T, term rate is
`R_T=(1/P(T,U|X_T)-1)/delta`, fixed at T and paid U.
Given T-state marginal under Q^U, its exponential moment is independent of
any production rate function. Wrong Q^T mean is saved as a negative control.

Overnight rate is
`R_on=(exp(I_TU)-1)/delta`, known only at U and paid U.
With conditional observation x_t, integrate the single entire future Wiener
trajectory; do not generate J_T and J_U independently.

Kernel for overnight interval I_TU on s in [t,U]:

`K_I(s)=eta*(B(U-s)-1_{s<T}*B(T-s))`.

Mean under Q:
`m_I=(B(U-t)-B(T-t))*x_t + integral_T^U phi`.
Kernel products give v_I and covariances with I_tU (payment discount) and
I_tT (wrong fixing discount). Payment mean is
`m_I - Cov(I_TU,I_tU)`; variance is unchanged.

Both `E_U R_T = E_U R_on = F(t;T,U)`; original equation28.22.
The simple accrual convention is source .25 or .5 years, not continuous r0.

| T | U | delta | F0 | term E_U | overnight E_U | term wrong Q^T |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1.25 | .25 | .0402006683366718 | .0402006683366722 | .0402006683366722 | .0402798738664939 |
| 1 | 1.5 | .5 | .0404026800535116 | .0404026800535116 | .0404026800535116 | .0405549790621169 |
| 2 | 2.5 | .5 | .0404026800535116 | .0404026800535116 | .0404026800535116 | .0406570745045242 |

21 fixtures = 7 time/state contracts times standard/eta0/negative-r0 models.
Conditional t=.25/.75 and fixing-now t=T are included. At t=T the wrong
fixing measure equals current cash measure; overnight still has remaining
uncertainty. Max correct-pay expectation error 6.0368e-16; unit FRA PV is
zero to machine precision. No overnight rate is asserted fixed at T.

## 6. Annuity mixture and two curves

Annuity `A(t)=sum_i delta_i P_d(t,U_i)` is discount-curve only.
Let `s=V/A`, terminal T before every payment. Conditional annuity distribution
of X_T is a finite Gaussian mixture:

`w_i(t)=delta_i P_d(t,U_i|x_t)/A(t|x_t)`,
`m_i=exp(-a*h)*x_t - c(h) - B(U_i-T)*q(h)`, variance q(h).

The weights sum to one algebraically; do not replace the mixture by one
Gaussian with a moment-matched mean unless explicitly a labeled approximation.
For a single payment, Q^A exactly reduces to that payment's Q^U.

V alternatives are model contracts, not interchangeable formulas:

1. Single curve: `V=P_d(t,T)-P_d(t,U_N)`.
2. Prepared-design additive simple-rate basis:
   `b_i=F_p(0;i)-F_d(0;i)` deterministic;
   `V=P_d(t,T)-P_d(t,U_N)+sum_i delta_i*b_i*P_d(t,U_i)`.
3. Alternative multiplicative zero-spread basis b:
   `R_p=(exp(b*delta_i)*P_d(fix,start)/P_d(fix,pay)-1)/delta_i`,
   `V=sum_i [exp(b*delta_i)*P_d(t,U_{i-1})-P_d(t,U_i)]`.

Both 2/3 are coherent deterministic-basis examples and fit time0 flat initial
projection 5% versus discount4% when b=.01. They differ after time0 and in
option prices. Root should choose one in the private implementation/spec and
use matching reference fields; do not mix initial additive-basis fixtures
with a multiplicative production model. No general stochastic multi-curve
calibration or actual OIS/LIBOR historical data is claimed.

Base expiry1, payments1.5/2/2.5/3, delta=.5, a=.2/eta=.02/r0=.04:
A0=1.8283193673620008 for all three cases.

| basis model | V0 | s0 | E_A s(T) | payer Q=A, K=.045 |
|---|---:|---:|---:|---:|
| single | .07386900243516570 | .04040268005351162 | .04040268005351163 | .00747548751516941 |
| additive | .09256825028383309 | .05063024104885768 | .05063024104885768 | .01703921547355391 |
| multiplicative | .09256825028383275 | .05063024104885750 | .05063024104885747 | .01709151624311898 |

All use the same discount-only mixture weights/means. For the payer call,
SciPy brentq obtains the monotone root `s_T(x)=K` and quadrature is split at
the kink. This removes the 1.5e-13 pilot discrepancy seen in the earlier
unsplit integration. Independent Q path-discount conditioning and direct
mixture integral give at most 2.0817e-17 price differences.

18 fixtures include conditional t=.25/x=-.015, t=.75/x=.02, eta0,
negative-r0 and x=-.02, and one-payment annuity, for all three basis choices.
Negative-rate single-curve fixture:
A=2.107765863411879 >0, V=-.05041543859124609,
s=-.02391889889972774, E_A s=-.023918898899727786.
Negative swap rate is valid; positive-ratio-only M28 helpers are unsuitable.
Max annuity mean error 1.8735e-16; raw E_Q[Z_A]=1 to ~2e-16.

## 7. Fixed numerical budgets and independent MC

Suggested deterministic oracle budgets, fixed before production comparison:

- Dimensionless moment/factor entries: absolute 2e-12.
- Physical kernel entries: relative 2e-12 plus 1e-25 absolute; for very small
  scales retain dimensionless tests so the absolute budget cannot hide a
  covariance sign/rank bug.
- Rates and raw RN expectation: absolute 2e-12.
- Nominal stock/unit-notional option prices: absolute 1e-9.
- Conditional A/V/s legs: use unit-aware rate/price budgets above; do not use
  one universal absolute tolerance for dollar prices and decimal rates.
- Literal independent integral outputs are stored with all input/state/model
  metadata, source-synthetic label, no NaN/Inf. Actual drift/price thresholds
  must stay separate from source printed precision (there is no printed pin).

MC uses 262144 IID samples per measure, no antithetic pairing. Q seed290041
and T seed290042 are independent. Within a measure, signed stock-loading
cases share noise; they are separate contract fixtures, not independent
replications or a confidence-interval average. The stored MC is diagnostics,
not a source price.

The independent reference MC uses kernel-quad covariance and Cholesky of
(X,W), then exact identity `I_noise=(eta*W-X_noise)/a`, only at well-conditioned
base a=.2,h=2. This is a second sampler path independent of the proposed
stable (I,W) factor. Tiny-ah tests rely on deterministic kernels/series; this
scratch MC's subtraction must not be copied to tiny-ah production sampling.
No production sampler, price function, or generated result is imported.

Q evaluates sample `exp(-I)*payoff`; T separately evaluates P_tT*payoff.
Raw Q RN weights are stored without normalization. SE=sample SD(ddof=1)/sqrt(n)
for IID observations. Fixed gate is `abs(estimate-oracle)<=5*SE+price_budget`.
If production uses antithetics, compute SE on independent pair averages and
record both pairs and total paths. Do not divide by sqrt(total paths) using
uncorrected correlated-path sample SD.

| sigma_S | Q estimate (SE) | T estimate (SE) | max abs error/SE |
|---:|---:|---:|---:|
| +.25 | 16.3611193125 (.0544719308) | 16.3652411897 (.0563306391) | .1927 |
| -.25 | 14.5423882922 (.0493719051) | 14.4796275416 (.0476382831) | 1.7112 |
| 0 | 3.2635593780 (.0047287524) | 3.2642760483 (.0049214203) | .4428 |

Raw RN mean=1.0000124901052407, SE=5.541447523610356e-5, .2254SE from1.
Keep raw E[Z], E[Z*H], sample variance/SE, effective counts, RNG seed,
numeraire/fixing/payment metadata. A sampler can pass a price accidentally,
so deterministic covariance/tilt and raw density checks remain required.
Annuity MC, if added, should draw component categorical index with exact
weights and an independent normal conditional on the index, separately from
Q discounted sampling; no approximate normal collapsed mixture.

## 8. Specific controls to reject

1. Bond formula drops -B*c(t): fails conditional integral and discounted tower.
2. Q cash discount replaced by P_tT outside EQ payoff: base positive-loading
   call differs .58961521336; negative loading reverses direction.
3. Wrong sign in Gaussian RN tilt, or only X shifted: fails same-stock pricing
   and raw-density/mean checks.
4. Term uses Q^T instead of Q^U: .04055497906 versus .04040268005 base semiannual.
5. Overnight fixed at T, or J_T/J_U independent: fails stored kernel covariance
   and payment-measure mean.
6. Annual continuous .04 substituted for simple rate: fails .25/.5 examples.
7. A uses projection DFs: A must equal across basis models with same discount
   curve; density/martingale and unit checks fail otherwise.
8. Mixture replaced by Q/T or one Gaussian: EQ/E_T swap-rate means differ from
   s0, and mixture source outputs/distribution are not preserved.
9. Additive and multiplicative basis mixed: t0 s0 alone does not expose it;
   payer prices .01703921547 vs .01709151624 and conditional V do.
10. Fixed positive rate/ratio restriction on s/V: rejects valid negative cases.
11. Tiny-ah direct difference variance or 3x3 Cholesky: kernel/factor and exact
    rank relation fail; h=0/eta=0 must stay well-defined.
12. Saved result amended without independent input/hash/finite/source gate:
    numerical consistency in plots alone cannot certify it. Production API
    mutation and consumed-result mutations must be separate rejection tests.

## 9. Scope still pending

This is reference/preflight material. No M29 acceptance/ledger increment is
claimed. General multi-factor derivation belongs to §28.5, lognormal swaption
assumptions to §28.6/Ch29, and arbitrary numeraire drift changes to §28.8.
Do not treat the one-factor synthetic model as fulfilling those later sections.