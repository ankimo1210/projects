# 2001-longstaff-schwartz-american-options-lsm

<!-- page: 1 -->

## UCLA

## Recent Work

## Title

Valuing American Options by Simulation: A Simple Least-Squares Approach

## Permalink

https://escholarship.org/uc/item/43n1k4jb

## Authors

Longstaff, Francis A

Schwartz, Eduardo S

## Publication Date

2001-05-09

<!-- page: 2 -->

## Valuing American Options by Simulation: A Simple Least-Squares Approach

Francis A. Longstaff UCLA

Eduardo S. Schwartz UCLA

This article presents a simple yet powerful new approach for approximating the value of American options by simulation. The key to this approach is the use of least squares to estimate the conditional expected payoff to the optionholder from continuation. This makes this approach readily applicable in path-dependent and multifactor situations where traditional finite difference techniques cannot be used. We illustrate this technique with several realistic examples including valuing an option when the underlying asset follows a jump-diffusion process and valuing an American swaption in a 20-factor string model of the term strucure.

One of the most important problems in option pricing theory is the valuation and optimal exercise of derivatives with American-style exercise features. These types of derivatives are found in all major financial markets including the equity, commodity, foreign exchange, insurance, energy, sovereign, agency, municipal, mortgage, credit, real estate, convertible, swap, and emerging markets. Despite recent advances, however, the valuation and optimal exercise of American options remains one of the most challenging problems in derivatives finance, particularly when more than one factor affects the value of the option. This is primarily because finite differençe and binomial techniques become impractical in situations where there are multiple factors.1

We are grateful for the comments of Yaser Abu-Mostafa, Giovanni Barone-Adesi, Marco Avellaneda, Peter Bossaerts, Peter Carr, Peter DeCrem, Craig Fithian, Bjorn Flesaker, James Gammill, Gordon Gemmill, Robert Geske, Eric Ghysels, Ravit Efraty Mandell, Soetojo Tanudjaja, John Thornley, Bruce Tuckman, Pedro Santa-Clara, Pratap Sondhi, Ross Valkaniov, and seminar participants at Bear Stearns, the University of British Columbia, the California Institute of Technology, Chase Manhattan Bank, Citibank, the Courant Institute at New York University, Credit Suisse First Boston, Daiwa Securities, Fuji Bank, Goldman Sachs, Greenwich Capital, Morgan Stanley Dean Witter, the Norinchukin Bank, Nikko Securities, the Math Week Risk Magazine Conferences in London and New York, Salomon Smith Barney in London and New York, Simplex Capital, the Sumitomo Bank, UCLA, the 1998 Danish Finance Association meetings, and the 1999 Western Finance Association meetings. We are particularly grateful for the comments of the editor Ravi Jagannathan and of an anonymous referee who made extensive and insightful suggestions for improving the article. All errors are our responsibility. Address correspondence to Francis A. Longstaff, The Anderson School at UCLA, Box 951481, Los Angeles, CA 90095-1481, or e-mail: francis.longstaff@anderson.ucla.edu.

.¹ For example, this explains why virtually all WallStreet firms value and exercise American swaptions using a simple single-factor model despite clear evidence that the term structure is driven by multiple factors.

<!-- page: 3 -->

In this article, we present a simple, yet powerful new approach to approximating the value of American options by simulation. By its nature, simulation is a promising alternative to traditional finite difference and binomial techniques and has many advantages as a framework for valuing, risk managing, and optimally exercising American options. For example, simulation is readily applied when the value of the option depends on multiple factors. Simulation can also be used to value derivatives with both path-dependent and American-exercise features. Simulation allows state variables to follow general stochastic processes such as jump diffusions, as in Merton (1976) and Cox and Ross (1976), non-Markovian processes, as in Heath, Jarrow, and Morton (1992), and even general semimartingales, as in Harrison and Pliska (1981).2 From a practical perspective, simulation is well suited to parallel computing, which allows significant gains in computational speed and efficiency. Finally, simulation techniques are simple, transparent, and flexible.

To understand the intuition behind this approach, recall that at any exercise time, the holder of an American option optimally compares the payoff from immediate exercise with the expected payoff from continuation, and then exercises if the immediate payoff is higher. Thus the optimal exercise strategy is fundamentally determined by the conditional expectation of the payoff from continuing to keep the option alive. The key insight underlying our approach is that this conditional expectation can be estimated from the cross-sectional information in the simulation by using least squares. Specifically, we regress the ex post realized payoffs from continuation on functions of the values of the state variables. The fitted value from this regression provides a direct estimate of the conditional expectation function. By estimating the conditional expectation function for each exercise date, we obtain a complete specification of the optimal exercise strategy along each path. With this specification, American options can then be valued accurately by simulation. We refer to this technique as the least squares Monte Carlo (LSM) approach.

This approach is easy to implement since nothing more than simple least squares is required. To illustrate this, we present a series of increasingly complex but realistic examples. In the first, we value an American put option in a single-factor setting. In the second, we value an exotic American-Bermuda— Asian option. This option is path dependent and has multifactor features. In the third, we value a cancelable index amortizing swap where the term structure is driven by several factors. This standard fixed-income derivative product has almost pathological path-dependent properties. In each case, the simulation algorithm gives values that are indistinguishable from those given by more computationally intensive finite difference techniques. In the fourth example, we value American options on an asset which follows a jumpdiffusion process. This option cannot be valued using standard finite difference techniques. To illustrate the full generality of this approach, the fifth example values a deferred American swaption in a 20-factor string model where each point on the interest-rate curve is a separate factor. We also show how the algorithm can be used in a risk-management context by computing the sensitivity of swaption values to each point along the curve.

Semimartingales are essentially the broadest class of processes for which stochastic integrals can be defined and standard option pricing theory applied.

<!-- page: 4 -->

A number of other recent articles also address the pricing of American options by simulation. In an important early contribution to this literature, Bossaerts (1989) solves for the exercise strategy that maximizes the simulated value of the option. Other important examples of this literature include Tilley (1993), Barraquand and Martineau (1995), Averbukh (1997), Broadie and Glasserman (1997a,b,c), Broadie, Glasserman, and Jain (1997), Raymar and Zwecher (1997), Broadie et al. (1998), Carr (1998), Ibanez and Zapatero (1998), and Garcia (1999). These articles use various stratification or parameterization techniques to approximate the transitional density function or the early exercise boundary. This article takes a fundamentally different approach by focusing directly on the conditional expectation function.

Several recent articles that use an approach similar to ours include Carriere (1996) and Tsitsiklis and Van Roy (1999). Our work, however, differs in a number of ways. For example, neither of these articles take the approach to the level of practical implementation we do in this article. Furthermore, we include in the regression only paths for which the option is in the money. This significantly increases the efficiency of the algorithm and decreases the computational time. In addition, we demonstrate the application of the methodology to complex derivatives with many underlying factors and evaluate the accuracy of the algorithm by comparing our solutions to finite difference approximations.3

The remainder of this article is organized as follows. Section 1 presents a simple numerical example of the simulation approach. Section 2 describes the underlying theoretical framework. Sections 3-7 provide specific examples of the application of this approach. Section 8 discusses a number of numerical and implementation issues. Section 9 summarizes the results and contains concluding remarks.

## 1. A Numerical Example

At the final exercise date, the optimal exercise strategy for an American option is to exercise the option if it is in the money. Prior to the final date, however, the optimal strategy is to compare the immediate exercise value with the expected cash flows from continuing, and then exercise if immediate exercise is more valuable. Thus, the key to optimally exercising an American option is identifying the conditional expected value of continuation. In this approach, we use the cross-sectional information in the simulated paths to identify the conditional expectation function. This is done by regressing the subsequent realized cash flows from continuation on a set of basis functions of the values of the relevant state variables. The fitted value of this regression is an efficient unbiased estimate of the conditional expectation function and allows us to accurately estimate the optimal stopping rule for the option. anows us aur 1 coh is

Another related article is Keane and Wolpin (1994), which uses regression in a simulation context to solve discrete choice dynamic programming problems.

<!-- page: 5 -->

Perhaps the best way to convey the intuition of the LSM approach is through a simple numerical example. Consider an American put option on a share of non-dividend-paying stock. The put option is exercisable at a strike price of 1.10 at times 1, 2, and 3, where time three is the final expiration date of the option. The riskless rate is 6%. For simplicity, we illustrate the algorithm using only eight sample paths for the price of the stock. These sample paths are generated under the risk-neutral measure and are shown in the following matrix.

[Table source crop](assets/tables/2001-longstaff-schwartz-american-options-lsm-p0005-block-0003-7807d70c2dd03089.jpg)


Our objective is to solve for the stopping rule that maximizes the value of the option at each point along each path. Since the algorithm is recursive, however, we first need to compute a number of intermediate matrices. Conditional on not exercising the option before the final expiration date at time 3, the cash flows realized by the optionholder from following the optimal strategy at time 3 are given below.

[Table source crop](assets/tables/2001-longstaff-schwartz-american-options-lsm-p0005-block-0005-b91a7851ae7d258a.jpg)
Cash-flow matrix at time 3

These cash flows are identical to the cash flows that would be received if the option were European rather than American.

<!-- page: 6 -->

If the put is in the money at time 2, the optionholder must then decide whether to exercise the option immediately or continue the option's life until the final expiration date at time 3. From the stock-price matrix, there are only five paths for which the option is in the money at time 2. Let X denote the stock prices at time 2 for these five paths and Y denote the corresponding discounted cash flows received at time 3 if the put is not exercised at time 2. We use only in-the-money paths since it allows us to better estimate the conditional expectation function in the region where exercise is relevant and significantly improves the efficiency of the algorithm. The vectors X and Y are given by the nondashed entries below.

[Table source crop](assets/tables/2001-longstaff-schwartz-american-options-lsm-p0006-block-0002-6677adb55b3315d8.jpg)
Regression at time 2

To estimate the expected cash flow from continuing the option's life conditional on the stock price at time 2, we regress Y on a constant, X, and $X ^ { 2 }$ This specification is one of the simplest possible; more general specifications are considered later in the article. The resulting conditional expectation function is $E [ \ Y \mid X ] = - 1 . 0 7 0 + 2 . 9 8 3 X - 1 . 8 1 3 X ^ { 2 }$

With this conditional expectation function, we now compare the value of immediate exercise at time 2, given in the first column below, with the value from continuation, given in the second column below.

[Table source crop](assets/tables/2001-longstaff-schwartz-american-options-lsm-p0006-block-0005-598b8ded1f53962a.jpg)
Optimal early exercise decision at time 2

The value of immediate exercise equals the intrinsic value 1.10 — X for the in-the-money paths, while the value from continuation is given by substituting X into the conditional expectation function. This comparison implies that it is optimal to exercise the option at time 2 for the fourth, sixth, and seventh paths. This leads to the following matrix, which shows the cash flows received by the optionholder conditional on not exercising prior to time 2.

<!-- page: 7 -->

[Table source crop](assets/tables/2001-longstaff-schwartz-american-options-lsm-p0007-block-0002-101c2becd71f5879.jpg)


Observe that when the option is exercised at time 2, the cash flow in the final column becomes zero. This is because once the option is exercised there are no further cash flows since the option can only be exercised once.

Proceeding recursively, we next examine whether the option should be exercised at time 1. From the stock price matrix, there are again five paths where the option is in the money at time 1. For these paths, we again define Y as the discounted value of subsequent option cash flows. Note that in defining Y, we use actual realized cash flows along each path; we do not use the conditional expected value of Y estimated at time 2 in defining Y at time 1. As is discussed later, discounting back the conditional expected value rather than actual cash flows can lead to an upward bias in the value of the option.

Since the option can only be exercised once, future cash flows occur at either time 2 or time 3, but not both. Cash flows received at time 2 are discounted back one period to time 1, and any cash flows received at time 3 are discounted back two periods to time 1. Similarly X represents the stock prices at time 1 for the paths where the option is in the money. The vectors X and Y are given by the nondashed elements in the following matrix.

[Table source crop](assets/tables/2001-longstaff-schwartz-american-options-lsm-p0007-block-0006-6076148731d06e1b.jpg)
Regression at time 1

<!-- page: 8 -->

The conditional expectation function at time 1 is estimated by again regressing Y on a constant, X and X². The estimated conditional expec- $X ^ { 2 }$ $E [ \ Y \mid X \ ] = 2 . 0 3 8 - 3 . 3 3 5 X + 1 . 3 5 6 X ^ { 2 }$ . Substituting the tation function is values of X into this regression gives the estimated conditional expectation function. These estimated continuation values and immediate exercise values at time 1 are given in the first and second columns below. Comparing the two columns shows that exercise at time 1 is optimal for the fourth, sixth, seventh, and eighth paths.

[Table source crop](assets/tables/2001-longstaff-schwartz-american-options-lsm-p0008-block-0002-7f7ebda4bad528d5.jpg)
Optimal early exercise decision at time 1

Having identified the exercise strategy at times 1, 2, and 3, the stopping rule can now be represented by the following matrix, where the ones denote exercise dates at which the option is exercised.

[Table source crop](assets/tables/2001-longstaff-schwartz-american-options-lsm-p0008-block-0004-4cad8a90a061797c.jpg)


With this specification of the stopping rule, it is now straightforward to determine the cash flows realized by following this stopping rule. This is done by simply exercising the option at the exercise dates where there is a one in the above matrix. This leads to the following option cash

<!-- page: 9 -->

flow matrix.

[Table source crop](assets/tables/2001-longstaff-schwartz-american-options-lsm-p0009-block-0002-ad18bc922227d8f9.jpg)
Option cash flow matrix

Having identified the cash flows generated by the American put at each date along each path, the option can now be valued by discounting each cash flow in the option cash flow matrix back to time zero, and averaging over all paths. Applying this procedure results in a value of .1144 for the American put. This is roughly twice the value of .0564 for the European put obtained by discounting back the cash flows at time 3 from the first cash flow matrix.

Although very stylized, this example illustrates how least squares can use the cross-sectional information in the simulated paths to estimate the conditional expectation function. In turn, the conditional expectation function is used to identify the exercise decision that maximizes the value of the option at each date along each path. As shown by this example, the LSM approach is easily implemented since nothing more than simple regression is involved.

## 2. The Valuation Algorithm

In this section we describe the general LSM algorithm. The valuation framework underlying the LSM algorithm is based on the general derivative pricing paradigm of Black and Scholes (1973), Merton (1973), Harrison and Kreps (1979), Harrison and Pliska (1981), Cox, Ingersoll, and Ross (1985), Heath, Jarrow, and Morton (1992), and others. We also present several convergence results for the algorithm.

## 2.1 The valuation framework

We assume an underlying complete probability space $( \Omega , { \mathcal { F } } , P )$ and finite time horizon [0, T], where the state space Ω is the set of all possible realizations of the stochastic economy between time 0 and T and has typical element $\omega$ representing a sample path, $\mathcal { F }$ is the sigma field of distinguishable events at time T, and P is a probability measure defined on the elements of $\mathcal { F }$ We define $F = \{ { \mathcal { F } } _ { t } ; t \in [ 0 , T ] \}$ to be the augmented filtration generated by the relevant price processes for the securities in the economy, and assume that $\mathcal { F } _ { T } = \mathcal { F }$ . Consistent with the no-arbitrage paradigm, we assume the existence of an equivalent martingale measure Q for this economy.

We are interested in valuing American-style derivative securities with random cash flows which may occur during [0, T]. We restrict our attention to derivatives with payoffs that are elements of the space of square-integrable or finite-variancefunctions $L ^ { 2 } ( \Omega , { \mathcal { F } } , Q )$ Standardresultssuchas Bensoussan (1984) and Karatzas (1988) imply that the value of an American option can be represented by the Snell envelope; the value of an American option equals the maximized value of the discounted cash flows from the option, where the maximum is taken over all stopping times with respect to the filtration F. We introduce the notation $C ( \omega , s ; t , T )$ to denote the path of cash flows generated by the option, conditional on the option not being exercised at or prior to time t and on the optionholder following the optimal stopping strategy for all s, $t ~ < ~ s ~ \le ~ T$ . This function is analogous to the intermediate cash-flow matrices used in the previous section.

<!-- page: 10 -->

The objective of the LSM algorithm is to provide a pathwise approximation to the optimal stopping rule that maximizes the value of the American option. To convey the intuition behind the LSM algorithm, we focus the discussion on the case where the American option can only be exercised at the K discrete times $0 < t _ { 1 } \leq t _ { 2 } \leq t _ { 3 } \leq \cdot \cdot \cdot \leq t _ { K } = T$ , and consider the optimal stopping policy at each exercise date. In practice, of course, many American options are continuously exercisable; the LSM algorithm can be used to approximate the value of these options by taking K to be sufficiently large.

At the final expiration date of the option, the investor exercises the option if it is in the money, or allows it to expire if it is out of the money. At exercise time tk prior to the final expiration date, however, the optionholder $t _ { k }$ must choose whether to exercise immediately or to continue the life of the option and revisit the exercise decision at the next exercise time. The value of the option is maximized pathwise, and hence unconditionally, if the investor exercises as soon as the immediate exercise value is greater than or equal to the value of continuation.

At time tk, the cash flow from immediate exercise is known to the investor, $t _ { k }$ and the value of immediate exercise simply equals this cash flow. The cash flows from continuation, of course, are not known at time tk. No-arbitrage $t _ { k }$ valuation theory, however, implies that the value of continuation, or equivalently, the value of the option assuming that it cannot be exercised until after $t _ { k } ,$ , is given by taking the expectation of the remaining discounted cash flows $C ( \omega , s ; t _ { k } , T )$ with respect to the risk-neutral pricing measure Q. Specifically, at time t, the value of continuation $t _ { k }$ $F ( \omega ; t _ { k } )$ can be expressed as

$$
F ( \omega ; t _ { k } ) = E _ { \mathcal { Q } } \Bigg [ \sum _ { j = k + 1 } ^ { K } \exp \Bigg ( - \int _ { t _ { k } } ^ { t _ { j } } r ( \omega , s ) d s \Bigg ) C ( \omega , t _ { j } ; t _ { k } , T ) \mid \mathcal { F } _ { t _ { k } } \Bigg ] ,\tag{1}
$$

4 For a discussion of optimal exercise policies for American options, see Duffie (1996) or Lamberton and Lapeyre (1996). Bossaerts (1989) directly uses this maximization property in developing simulation estimates of American option prices by parameterizing the stopping rule and then solving for the parameters that maximize the value of the option.

<!-- page: 11 -->

where $r ( \omega , t )$ is the (possibly stochastic) riskless discount rate, and the expectation is taken conditional on the information set $\mathcal { F } _ { t _ { k } }$ at time $t _ { k }$ With this representation, the problem of optimal exercise reduces to comparing the immediate exercise value with this conditional expectation, and then exercising as soon as the immediate exercise value is positive and greater than or equal to the conditional expectation.

## 2.2 The LSM algorithm

The LSM approach uses least squares to approximate the conditional expectation function at $t _ { K - 1 } , ~ t _ { K - 2 } , \ldots , t _ { 1 }$ . We work backwards since the path of cash flows $C ( \omega , s ; t , T )$ generated by the option is defined recursively; $C ( \omega , s ; t _ { k } , T )$ can differ from $C ( \omega , s ; t _ { k + 1 } , T )$ since it may be optimal to stop at time $t _ { k + 1 }$ , thereby changing all subsequent cash flows along a realized path ω. Specifically, at time $t _ { K - 1 }$ , we assume that the unknown functional form of $F ( \omega ; t _ { K - 1 } )$ in Equation (1) can be represented as a linear combination of a countable set of $\mathcal { F } _ { t _ { K - 1 } }$ -measurable basis functions.

This assumption can be formally justified, for example, when the conditional expectation is an element of the $L ^ { 2 }$ space of square-integrable functions relative to some measure. Since $L ^ { 2 }$ is a Hilbert space, it has a countable orthonormal basis and the conditional expectation can be represented as, a linear function of the elements of the basis.⁵ As an example, assume that X is the value of the asset underlying the option and that X follows a Markov process.6 One possible choice of basis functions is the set of (weighted) Laguerre polynomials:

$$
L _ { 0 } ( X ) = \exp ( - X / 2 ) ,\tag{2}
$$

$$
L _ { 1 } ( X ) = \exp ( - X / 2 ) ~ ( 1 - X ) ,\tag{3}
$$

$$
L _ { 2 } ( X ) = \exp ( - X / 2 ) ( 1 - 2 X + X ^ { 2 } / 2 ) ,\tag{4}
$$

$$
L _ { n } ( X ) = \exp ( - X / 2 ) \frac { e ^ { X } } { n ! } \frac { d ^ { n } } { d X ^ { n } } ( X ^ { n } e ^ { - X } ) .\tag{5}
$$

With this specification, $F ( \omega ; t _ { K - 1 } )$ can be represented as

$$
F ( \omega ; t _ { K - 1 } ) = \sum _ { j = 0 } ^ { \infty } a _ { j } \ L _ { j } ( X ) ,\tag{6}
$$

where the $a _ { j }$ coefficients are constants. Other types of basis functions include the Hermite, Legendre, Chebyshev, Gegenbauer, and Jacobi polynomials.'

5 For a discussion of Hilbert space theory and Hilbert space representations of square-integrable functionș, see Royden (1968).

6 For Markovian problems, only current values of the state variables are necessary. For non-Markovian problems, both current and past realizations of the state variables can be included in the basis functions and the regressions.

7 These functions are described in Chapter 22 of Abramowitz and Stegun (1970).

<!-- page: 12 -->

Numerical tests indicate that Fourier or trigonometric series and even simple powers of the state variables also give accurate results.

To implement the LSM approach, we approximate $F ( \omega ; t _ { K - 1 } )$ using the frst $M \ : < \infty$ basis functions, and denote this approximation $F _ { M } ( \omega ; t _ { K - 1 } )$ Once this subset of basis functions has been specified, $F _ { M } ( \omega ; t _ { K - 1 } )$ is estimated by projecting or regressing the discounted values of $C ( \omega , s ; t _ { K - 1 } , T )$ onto the basis functions for the paths where the option is in the money at time $t _ { K - 1 }$ . We use only in-the-money paths in the estimation since the exercise decision is only relevant when the option is in the money. By focusing on the in-the-money paths, we limit the region over which the conditional expectation must be estimated, and far fewer basis functions are needed to obtain an accurate approximation to the conditional expectation function.8 Since the values of the basis functions are independently and identically distributed across paths, weak assumptions about the existence of moments allow us to use Theorem 3.5 of White (1984) to show that the fitted value of this regression $\widehat { F } _ { M } ( \omega ; t _ { K - 1 } )$ converges in mean square and in probability to $F _ { M } ( \omega ; t _ { K - 1 } )$ as the number N of (in-the-money) paths in the simulation goes to infinity. Furthermore, Theorem 1.2.1 of Amemiya (1985) implies that $\widehat { F } _ { M } ( \omega ; t _ { K - 1 } )$ is the best linear unbiased estimator of $F _ { M } ( \omega ; t _ { K - 1 } )$ based on a mean-squared metric.

Once the conditional expectation function at time $t _ { K - 1 }$ is estimated, we can determine whether early exercise at time $t _ { K - 1 }$ is optimal for an in-the-money path $\omega$ by comparing the immediate exercise value with $\widehat { F } _ { M } ( \omega ; t _ { K - 1 } )$ , and repeating for each in-the-money path. Once the exercise decision is identified, the option cash flow paths $C ( \omega , s ; t _ { K - 2 } , T )$ can then be approximated. The recursion proceeds by rolling back to time $t _ { K - 2 }$ and repeating the procedure until the exercise decisions at each exercise time along each path have been determined. The American option is then valued by starting at time zero, moving forward along each path until the first stopping time occurs, discounting the resulting cash flow from exercise back to time zero, and then taking the average over all paths ω.

When there are two state variables X and Y, the set of basis functions should include terms in X and in Y, as well as cross-products of these terms. Similarly for higher-dimensional problems. Intuitively this seems to suggest that the number of basis functions needed grows exponentially with the dimensionality of the problem. In actuality, however, there may be reasons why the number of basis functions necessary to obtain a desired level of convergence might grow at a slower rate. As an example, Judd (1998)

8We conducted a variety of numerical experiments which indicated that if all paths are used, more than two or three times as many basis functions may be needed to obtain the same level of accuracy as obtained by the estimator based on in-the-money paths. Intuitively this makes sense since we are interested in estimating the expectation conditional on the current state and the event that the option is in the money. By using all paths, and hence, not conditioning on the event that the option is in the money, we obtain estimates of the conditional expectation function which have larger standard errors than those obtained by using all of the conditioning information.

<!-- page: 13 -->

shows that by using sets of complete polynomials, kth degree convergence is obtained asymptotically using a number of terms that grows only polynomially with the dimension of the problem. Similar results are also well known in the neural-network literature; as examples, see Barron (1993) and Refenes, Burgess, and Bentz (1997). In the numerical results given later in the article, we find that the number of basis functions needed to obtain convergence appears to grow much more slowly than exponentially. Our experience suggests that the number of basis functions necessary to approximate the conditional expectation function may be very manageable even for highdimensional problems.

## 2.3 Convergence results

The LSM algorithm provides a simple and elegant way of approximating the optimal early exercise strategy for an American-style option. While the ultimate test of the algorithm is how well it performs using a realistic number of paths and basis functions, it is also useful to examine what can be said about the theoretical convergence of the algorithm to the true value V(X) of the American option.

The first convergence result addresses the bias of the LSM algorithm and is applicable even when the American option is continuously exercisable.

Proposition 1. For any finite choice of M, K, and vector $\theta \in R ^ { M \times ( K - 1 ) }$ representing the coefficients for the M basis functions at each of the K — 1 early exercise dates, let LSM (ω; M, K) denote the discounted cash flow resulting from following the LSM rule of exercising when the immediate exercise value is positive and greater than or equal to $\widehat { F } _ { M } ( \omega _ { i } ; t _ { k } )$ as defined by θ. Then the following inequality holds almost surely,

$$
V ( X ) \geq \operatorname* { l i m } _ { N  \infty } \frac { 1 } { N } \sum _ { i = 1 } ^ { N } L S M ( \omega _ { i } ; M , K ) .
$$

Proof. See the appendix.

The intuition for this result is easily understood. The LSM algorithm results in a stopping rule for an American-style option. The value of an American-style option, however, is based on the stopping rule that maximizes the value of the option; all other stopping rules, including the stopping rule implied by the LSM algorithm, result in values less than or equal to that implied by the optimal stopping rule.

This result is particularly useful since it provides an objective criterion for convergence. For example, this criterion provides guidance in determining the number of basis functions needed to obtain an accurate approximation; simply increase M until the value implied by the LSM algorithm no longer increases. This useful and important property is not shared by algorithms that simply discount back functions based on the estimated continuation value.9

<!-- page: 14 -->

By its nature, providing a general convergence result for the LSM algorithm is difficult since we need to consider limits as the number of discretization points K, the number of basis functions M, and the number of paths N go to infinity. In addition, we need to consider the effects of propagating the estimating stopping rule backwards through time from $t _ { K - 1 }$ to $t _ { 1 }$ . In the case where the American option can only be exercised at $K = 2$ discrete points in time, however, convergence of the algorithm is more easily demonstrated. As an example, consider the following proposition.

Proposition 2. Assume that the value of an American option depends on a single state variable X with support on $( 0 , \infty )$ which follows a Markov process. Assume further that the option can only be exercised at times $t _ { 1 }$ and t, and that the conditional expectation function $t _ { 2 } ,$ $F ( \omega ; t _ { 1 } )$ is absolutely continuous and

$$
\int _ { 0 } ^ { \infty } e ^ { - X } F ^ { 2 } ( \omega ; t _ { 1 } ) d X \ < \ \infty ,
$$

$$
\int _ { 0 } ^ { \infty } e ^ { - X } F _ { X } ^ { 2 } ( \omega ; t _ { 1 } ) d X < \infty .
$$

Then for any $\epsilon > 0$ , there exists an $M < \infty$ such that

$$
\operatorname* { l i m } _ { N  \infty } \operatorname* { P r } \biggl [ \mid V ( X ) - \frac { 1 } { N } \sum _ { i = 1 } ^ { N } L S M ( \omega _ { i } ; M , K ) \mid > \epsilon \biggr ] = 0 .
$$

Proof. See the appendix.

Intuitively this result means that by selecting M large enough and letting $N \infty$ , the LSM algorithm results in a value for the American option within € of the true value. Thus the LSM algorithm converges to any desired degree of accuracy since ∈ is arbitrary. The key to this result is that the convergence of $F _ { M } ( \omega ; t _ { 1 } )$ to $F ( \omega ; t _ { 1 } )$ is uniform on $( 0 , \infty )$ when the indicated integrability conditions are met. This bounds the maximum error in estimating the conditional expectation, which in turn, bounds the maximum pricing error. An important implication of this result is that the number of basis functions needed to obtain a desired level of accuracy need not go to infinity as $N \infty$ . While this proposition is limited to one-dimensional settings, we conjecture that similar results can be obtained for higher-dimensional problems by finding conditions under which uniform convergence occurs.

For example, if the American option were valued by taking the maximum of the immediate exercise value and the estimated continuation value, and discounting this value back, the resulting American option value could be severely upward biased. This bias arises since the maximum operator is convex; measurement error in the estimated continuation value results in the maximum operator being upward biased. We are indebted to Peter Bossaerts for making this point

<!-- page: 15 -->

## 3. Valuing American Put Options

Earlier we used a stylized example to illustrate how this approach could be applied to the valuation of American put options. In this section we present an in-depth example of the application of the LSM algorithm to American put options

Assume that we are interested in pricing an American-style put option on a share of stock, where the risk-neutral stock price process follows the stochastic differential equation

$$
d S = r S d t + \sigma s d Z ,\tag{7}
$$

and where r and σ are constants, Z is a standard Brownian motion, and the stock does not pay dividends. Furthermore, assume that the option is excercisable 50 times per year at a strike price of K up to and including the final expiration date T of the option. This type of discrete American-style exercise $T$ feature is also sometimes termed a Bermuda exercise feature. As the set of basis functions, we use a constant and the first three Laguerre polynomials as given in Equations (2)-(4). Thus we regress discounted realized cash flows on a constant and three nonlinear functions of the stock price. Since we use linear regression to estimate the conditional expectation function, it is straightforward to add additional basis functions as explanatory variables in the regression if needed. Using more than three basis functions, however, does not change the numerical results; three basis functions are sufficient to obtain effective convergence of the algorithm in this example.

To illustrate the results, Table 1 reports the values of the early exercise option implied by both the finite difference and LSM techniques. The value of the early exercise option is the difference between the American and European put values. The European put value is given by the Black-Scholes formula. In this article we focus primarily on the early exercise value since it is the most difficult component of an American options's value to determine; the European component of an American option's value is much easier to identify.

The finite difference results reported in Table 1 are obtained from an implicit finite difference scheme with 40,000 time steps per year and 1,000 steps for the stock price. The partial differential equation satisfied by the put price $P ( S , t )$ is

$$
( \sigma ^ { 2 } S ^ { 2 } / 2 ) P _ { S S } + r S P _ { S } - r P + P _ { T } = 0 ,\tag{8}
$$

subject to the expiration condition $P ( S , T ) = \operatorname* { m a x } ( 0 , K - S _ { T } )$ . The implicit finite difference results were also compared with the results from an explicit finite difference algorithm; the two finite difference techniques resulted in values that were generally within one cent of each other. The LSM estimates are based on 100,000 (50,000 plus 50,000 antithetic) paths using 50 exercise points per year.

<!-- page: 16 -->

[Table source crop](assets/tables/2001-longstaff-schwartz-american-options-lsm-p0016-block-0001-7775717d5419c0da.jpg)
Table 1

As shown, the differences between the finite difference and LSM algorithms are typically very small. Of the 20 differences shown in Table 1, 16 are less than or equal to one cent in absolute value. The standard errors for the simulated values range from 0.7 to 2.4 cents, which is well within the market bid-ask spread for these types of options.1º In addition, the differences are both positive and negative. These results suggest that the LSM algorithm is able to approximate closely the finite-difference values.

Broadie ad Glasserman (1997a,b), Raymar and Zwecher (1997), Garcia (1999), and others suggest an interesting diagnostic test for the convergence of a simulation algorithm. Essentially the stopping rule is estimated from one set of paths and then applied to another set of paths. In our context, this can be implemented by estimating the conditional expectation regressions from one set of paths and then applying the regression functions to an outof-sample set of paths. A successful algorithm should lead to out-of-sample values that closely approximate the in-sample values for the option."

1º Exchange traded stock option premiums are typically quoted in sixteenths or eighths of a dollar. The bid-ask spread for an at-the-money option would generally be some multiple of these fractions.

<!-- page: 17 -->

The results from these diagnostic tests are shown in Table 2. For selected sets of parameters from Table 1, we estimate the regressions in sample, value the option using the in-sample LSM procedure, and then value the option out of sample using the in-sample regression parameters but different paths. We repeat this process for five different initial seeds of the random number generator; the five rows for each example shown in Table 2 correspond to different initial seeds. As shown, the in-sample and out-of-sample values are virtually identical. The differences between the in-sample and out-ofsample values are virtually identical. The differences between the in-sample and out-of-sample values are both positive and negative and only 5% of the values are larger than two standard errors. This provides strong support for the accuracy of the algorithm. Given these results, we recommend using the LSM algorithm in sample in order to minimize computational time.

## 4. Valuing an American-Bermuda-Asian Option

In this section we apply the LSM algorithm to a more exotic path-dependent option. In particular, we consider a call option on the average price of a stock over some horizon, where the call option can be exercised at any time after some initial lockout period. Thus this option is an Asian option since it is an option on an average, and has both a Bermuda and American exercise feature; an American-Bermuda-Asian option.

Define the current valuation date as time 0. We assume that the option has a final expiration date of T = 2, and that the option can be exercised at any time after t = .25 by payment of the strike price K. The underlying average $A _ { t } , . 2 5 \leq t \leq T$ , is the continuous arithmetic average of the underlying stock price during the period three months prior to the valuation date (a three-month lookback) to time t. Thus the cash flow from exercising the option at time t is max $( 0 , A _ { t } - K )$ . The risk-neutral dynamics for the stock price are the same as in the previous section.

This option is particularly complex because it not only has an American exercise feature, but the cash flow from exercise is path dependent since $A _ { t }$ depends on the path of the stock price over the averaging window. In general, these types of problems are very difficult to solve using finite difference techniques. In this case, we can value the option by finite difference techniques by transforming the problem from a path-dependent one to a Markovian problem. This is done by introducing the average to date as a second state variable in the problem. Consequently the option price $H ( S , A , t )$ is the solution of the following two-dimensional partial differential equation

I We are grateful to the referee for suggesting this diagnostic test and for providing some results about the performance of the LSM algorithm.

<!-- page: 18 -->

[Table source crop](assets/tables/2001-longstaff-schwartz-american-options-lsm-p0018-block-0001-2cd765d967581bbb.jpg)
Table 2

<!-- page: 19 -->

[Table source crop](assets/tables/2001-longstaff-schwartz-american-options-lsm-p0019-block-0001-378e1d98b4570fd5.jpg)
Table 3

$$
( \sigma ^ { 2 } S ^ { 2 } / 2 ) H _ { S S } + r S H _ { S } + \frac { 1 } { . 2 5 + t } ( S - A ) H _ { A } - r H + H _ { t } = 0 ,\tag{9}
$$

subject to the expiration condition $H ( S , A , T ) = \operatorname* { m a x } ( 0 , A _ { T } - K )$ . Note that the path dependence of the option payoff does not pose any difficulties to the simulation-based LSM algorithm.

Table 3 compares the numerical results from valuing this option by finite difference techniques with those obtained by the LSM approach. In this example, we compute both the value of the American-Bermuda-Asian option and its European counterpart, and focus primarily on the difference which represents the value of the early exercise option. The European counterpart of the American-Bermuda-Asian option is an option on the average stock price which can only be exercised at the final option maturity date $T = 2$ In this example, as well as in later examples in the article, we use the same paths to price the European option that is used to value the American option.

The finite difference results are obtained using an alternating directions implicit (ADI) algorithm with 10,000 time steps per year and 200 steps in both the stock price and the average stock price. The results were checked against a standard explicit finite difference scheme with a similar number of steps for the stock price and the average stock price. The finite difference algorithms result in values that are typically within three cents per \$100 notional. The LSM results are based on 50,000 (25,000 plus 25,000 antithetic) paths and use 100 discretization points per year to approximate the continuous exercise feature of the option. As basis functions in the regressions, we use a constant, the first two Laguerre polynomials evaluated at the stock price, the first two Laguerre polynomials evaluated at the average stock price, and the cross products of these Laguerre polynomials up to third-order terms. Thus we use a total of eight basis functions in the regressions.12

<!-- page: 20 -->

As shown in Table 3, the finite difference and LSM results are very similar. The differences in the early exercise values are typically less than two or three cents per \$100 notional value. The differences are again both positive and negative; there is no evidence that the LSM algorithm systematically undervalues the early exercise option. The differences in the early exercise values are also small relative to the level of the early exercise value, and very small relative to the level of the American and European option values. These differences would likely be well within the bid-ask spread or other transaction cost bounds.

## 5. Valuing Cancelable Index Amortizing Swaps

This section uses the LSM approach to value a cancelable index amortizing swap in a multifactor term structure model. Index amortizing swaps have been widely used on Wall Street in recent years and are among the most difficult types of structured interest-rate derivative products to value and risk manage. The reason for this is that the notional amount of these swaps declines over time in a complex way. For example, index amortizing swaps often have notional amounts that amortize on the basis of a nonlinear function of a constant maturity Treasury (CMT) or constant maturity swap (CMS) rate. This stochastic amortization property makes these derivatives highly path dependent. These swaps become even more complex when one of the counterparties has the right to cancel the swap at any time; a cancelable index amortizing swap consists of both an index amortizing swap and an American-style cancellation option. Index amortizing swaps are widely used to hedge or mimic the cash flows from mortgages; the amortization feature of an index amortizing swap is typically patterned after a mortgage prepayment model.

To simplify the example, we focus on a specific cancelable index amortizing swap with a five-year final maturity. We assume that the counterparty with the right to cancel receives a fixed coupon c and pays the floating Libor rate in the swap. We assume that the fixed coupon is received continuously and the floating rate is paid continuously on an actual/actual basis.

12 Numerical tests indicated that adding additional basis functions had little or no effect on the results; using eight basis functions was sufficient to obtain effective convergence.

<!-- page: 21 -->

The notional balance on which the fixed and floating cash flows are based is initially \$100, but amortizes continuously on the basis of the 10-year par swap rate, CMS 10. Let I, denote the notional balance of the swap at time t. $I _ { t }$ The dynamics of $I _ { t }$ are given by

$$
d I = - f ( \mathrm { C M S } 1 0 ) d t ,\tag{10}
$$

where $f ( u ) = . 0 0 , u \ge . 0 7 , f ( . 0 6 ) = . 1 0 , f ( . 0 5 ) = . 5 0 , f ( v ) = 4 . 0 0 ,$ $\upsilon ~ \leq ~ . 0 4$ . When CMS 10 is between .04 and .07, the function f(CMS 10) is linearly interpolated between the two closest points in this schedule. For $\mathrm { C \hat { M } S 1 0 } = . 0 5 4 3 , ~ f ( \mathrm { C M S 1 0 } ) = . 3 2 8$ Note that f(CMS 10) example, if is a rate; f (CMS 10) = 4.00 implies that the swap is amortizing at a rate that would completely amortize the swap in three months. The counterparty with the right to cancel can choose to cancel the swap at any time; canceling the swap terminates all future cash flows from the swap to either party. Since the cash flows accrue and pay on a continuous basis, there is no lump sum accrued coupon or interest payment made when the swap is canceled.13

In this example, we assume that the swap term structure is determined by a simple two-factor Vasicek (1977) type of model.14 In particular, we assume that the instantaneous Libor rate r equals the sum of two state variables, $r = X + Y$ . The risk-neutral dynamics of X and Y are assumed to be

$$
d X = ( \alpha - { \dot { \beta } } X ) d t + \sigma \ d Z _ { 1 } ,\tag{11}
$$

$$
d Y = ( \gamma - \eta Y ) d t + s \ d Z _ { 2 } ,\tag{12}
$$

where $\alpha , \beta , \sigma , \gamma , \eta$ , and s are constants and Z, and Z2 are independent $Z _ { 1 }$ $Z _ { 2 }$ Brownian motions. In this framework, the value of a zero-coupon bond D(X, Y, T) with maturity T is given by

$$
D ( X , Y , T ) = \exp \bigl ( - M ( X , Y , T ) + V ( T ) / 2 \bigr ) ,\tag{13}
$$

13 In practice, index amortizing swaps typically follow the swap market convention of exchanging payments on a quarterly or semiannual cycle, where the floating payment is determined at the beginning of the cycle and paid at the end of the cycle. Cancelable index amortizing swaps typically can only be canceled on a coupon payment date, and only after exchanging any accrued fixed or floating payments.

4 In this example, and in the swaption example in Section 8, we make the standard simplifying assumption that the swap curve can be modeled as if it were a risk-free term structure. In reality, Libor rates incorporate some small default-risk component. Since both legs of the swap are discounted using the same curve, however, the net effect on the value of the swap is typically very small.

<!-- page: 22 -->

where

$$
\begin{array} { l } { { { \cal M } ( X , Y , T ) = { \displaystyle { \frac { \alpha } { \beta } } T + \left( X - { \frac { \alpha } { \beta } } \right) \frac { ( 1 - \exp ( - \beta T ) ) } { \beta } } } } \\ { { { { } } \ ~ + { \displaystyle { \frac { \gamma } { \eta } T + \left( Y - { \frac { \gamma } { \eta } } \right) \frac { ( 1 - \exp ( - \eta T ) ) } { \eta } } } } } \\ { { { { \cal V } ( T ) = { \displaystyle { \frac { \sigma ^ { 2 } } { \beta ^ { 2 } } } \left( T - { \frac { 2 } { \beta } } ( 1 - \exp ( - \beta T ) ) + { \frac { 1 } { 2 \beta } } ( 1 - \exp ( - 2 \beta T ) ) \right) } } } } \\ { { { { } } \ ~ + { \displaystyle { \frac { s ^ { 2 } } { \eta ^ { 2 } } } \left( T - { \displaystyle { \frac { 2 } { \eta } } ( 1 - \exp ( - \eta T ) ) + { \displaystyle { \frac { 1 } { 2 \eta } } } ( 1 - \exp ( - 2 \eta T ) )  } } } } \\right)end{array} \end{array}
$$

The CMS 10 rate, conditional on the current values of X and Y, is given by

$$
\mathrm { C M S } 1 0 = 2 \times \bigg ( \frac { 1 - D ( X , Y , 1 0 ) } { \sum _ { i = 1 } ^ { 2 0 } D ( X , Y , i / 2 ) } \bigg ) .\tag{14}
$$

In this model, the value of the cancelable index amortizing swap depends on three state variables; the two factors X and Y as well as the current notional amount I. The swap S(X, Y, I, t) can be valued by finite difference techniques by solving the following three-dimensional partial differential equation implied by the dynamics for X, Y, and I.

$$
\begin{array} { r l r } {  { ( \sigma ^ { 2 } / 2 ) S _ { X X } + ( s ^ { 2 } / 2 ) S _ { Y Y } + ( \alpha - \beta X ) S _ { X } + ( \gamma - \eta Y ) S _ { Y } } } \\ & { } & { ~ - ~ f ( \mathrm { C M S \ 1 0 } ) S _ { I } - ( X + Y ) S + ( c - X - Y ) I + S _ { t } = 0 , } \end{array}\tag{15}
$$

subject to the conditions $S ( X , Y , I , T ) = 0$ and $S ( X , Y , 0 , t ) = 0 .$ Similarly, the swap can also be valued by the LSM algorithm by simulating paths of X and Y and keeping track of the notional balance along each path. The parameter values used in this example are chosen to approximate a current term structure and cap volatility curve.15

Table 4 presents the numerical results from the finite difference and LSM valuation of the cancellation option on the underlying index amortizing swap. The value of the cancellation option is the difference between the value of the cancelable index amortizing swap and the underlying noncancelable index amortizing swap. The table reports the results for a range of different values of the fixed' coupon paid on the swap. The finite difference methodology is an implementation of a successive overrelaxation technique similar to that described in Press et al. (1992). The finite difference algorithm uses 50 steps for X, 40 steps for Y, and 15 steps for I. The LSM algorithm is based on

15 The parameter values used in the example are $\alpha = . 0 0 1 , \beta = . 1 , \gamma = . 0 5 2 5 , \eta = 1 . 0 0 , \sigma = . 0 0 6 9 5 1 ,$ s = .00867. The initial values of X and Y are .002 and .050.

<!-- page: 23 -->

[Table source crop](assets/tables/2001-longstaff-schwartz-american-options-lsm-p0023-block-0001-8825a42da062b7f4.jpg)


e te e oe e e e e o o te e t s aa

<!-- page: 24 -->

Merton (1976) provides a closed-form solution for the value of a European option on the stock when its price follows the jump-to-ruin process in Equation (16). He also shows, however, that the price of an American option is given by a complex mixed differential-difference equation which is difficult to solve.17

To put the results into perspective, we compare the price and early exercise boundary for the American put option for the cases where there is no possibility of a jump $\lambda = . 0 0$ and when a jump can occur with intensity $\lambda = . 0 5$ , Note that when $\lambda > 0$ ), the stock price process has a mass point at zero, and the distribution of the stock price is no longer conditionally lognormal. Furthermore, as λ increases, the conditional variance of the future stock price increases. Specifically, the variance of the stock price is

$$
S ^ { 2 } ( 0 ) \exp ( 2 r ) \big ( \exp ( ( \lambda + \sigma ^ { 2 } ) T ) - 1 \big ) .\tag{17}
$$

To make the comparison more meaningful, we adjust the parameters in the two cases so that the means and variances are equal; the two cases differ in the shape of their conditional distributions but not in terms of their first two moments. From Equation (16), the mean of the risk-neutral distribution for the stock price is $S ( 0 ) \exp ( r T )$ and is the same across cases because of the martingale restriction implied by the risk-neutral framework. To equalize variances, we assume that when $\lambda = 0 , \sigma ^ { 2 } = . 0 9$ , Similarly, when $\lambda = . 0 5$ $\sigma ^ { 2 } = . 0 4$ . With these parameter values, the two distributions for the stock price have the same means and variances. We use 26 exercise points per year in the LSM algorithm and use the same basis functions in these examples as in Section 3. We focus on the case $T = 1$

Applying the LSM algorithm, the American put values are 3.80 for the $\lambda = . 0 0$ case and 3.40 for the $\lambda = . 0 5 { \mathrm { ~ c a s e } }$ . The European put values are 3.58 for the $\lambda = . 0 0$ case and 3.23 for the $\lambda = . 0 5$ case. The early exercise values are .22 and .17, respectively. Thus the values of the options are lower when there is a possibility of a jump, holding fixed the variance across the examples. This is intuitive since the diffusion coefficient in the $\lambda \ : = \ : . 0 5$ $\lambda = . 0 0$ case is .30. case is only .20, while the diffusion coefficient in the This means that in the absence of a jump, the option is less likely to be deep in the money in the $\lambda = . 0 5$ case. If a jump occurs, of course, then the option is much more valuable than it would be otherwise. The results indicate, however, that the windfall gain to the optionholder from a jump does not offset the effects of the lower diffusion coefficient.

Since the value of the early exercise premium is less in the case where $\lambda = . 0 5$ , there is less incentive to keep the option alive. Consequently, it is not surprising that the optimal early exercise strategy is more aggressive

17 7 Pham (1995) shows that the price of an American option can also be represented as the solution of a parabolic integrodifferential free boundary problem when the underlying price process exhibits jumps.

<!-- page: 25 -->

5,000 (2,500 plus 2,500 antithetic in both X and Y) paths. As basis functions, we use a constant, the first three powers of the value of the underlying noncancelable swap, $X , X ^ { 2 } , Y , Y ^ { 2 }$ , and XY. This results in a total of nine basis functions.16

As shown in Table 4, the two valuation approaches produce very similar numerical results for the value of the cancellation option; the differences in the value of the cancellation option are uniformly small. In fact, most of the differences are less than one cent per \$100 notional amount. The bid-ask spread on these complex derivatives is likely at least an order of magnitude greater than the size of these differences. As before, the differences are both positive and negative in sign. The numerical values of the cancelable and noncancelable swaps do differ slightly between the finite difference and LSM techniques. In general, the values implied by the finite difference algorithm for the cancelable and noncancelable swaps are about four to seven cents higher than the corresponding values implied by the LSM approach. This systematic pattern is due to slight differences in the way that the two techniques discretize the continuous coupon payments and the continuous amortization feature. These differences produce minor differences in the levels of the swap values, but have almost no effect on the value of the cancellation option.

## 6. Jump-Diffusions and American Option Valuation

In this section, we illustrate how the LSM approach can be applied to value American options when the underlying asset follows a jump-diffusion process. In particular, we revisit the American put option considered in Section 3. To simplify the illustration, we focus on the basic jump-to-ruin model presented in Merton (1976). In this model, the stock price follows a geometric Brownian motion as in Equation (7) until a Poisson event occurs, at which point the stock price becomes zero. The dynamics for this jump-diffusion process are given by

$$
d S = ( r + \lambda ) S d t + \sigma S d Z - S d q ,\tag{16}
$$

where q is an independent Poisson process with intensity λ. When a Poisson $d q = 1$ , and event occurs, the value of q jumps from zero to one, implying the stock price jumps downward from S to zero. As in Merton, we assume that jump risk is nonsystematic and unpriced by the market. This assumption could easily be relaxed. Similarly, the LSM approach can be readily applied using much more complex jump-diffusion processes than in this example or the other examples given in Merton.

16 Again, adding more basis functions has little effect on the value of the option. This provides numerical evidence that the number of basis functions needed to obtain effective convergence grows at a much slower rate than exponential as the dimensionality of the problem increases, consistent with Judd (1998).

<!-- page: 26 -->

![riguie 1 Graph of the early exercise boundary for an American put option Graph of the earıy exercise vounuaı y 1oı an p . The early exercise boundary is shown as a proportion of the exercise price of the option. The jump graph shows the early exercise boundary when the underlying stock price follows a jump diffusion. The no-jump graph shows the early exercise boundary when the underlying stock price follows a pure diffusion process.](assets/figures/2001-longstaff-schwartz-american-options-lsm-p0026-block-0001-16d286e4ee9cfdf0.jpg)

in the case where $\lambda = . 0 5$ than in the case where $\lambda = . 0 0$ To see this, Figure 1 plots the early exercise boundaries for the two cases. The early exercise boundaries are obtained by solving for the critical stock price at each exercise point at which the estimated conditional expectation function equals the immediate exercise value of the option. As shown, the early exercise boundary for the case where the stock price can jump is significantly higher than for the continuous case.

## 7. Valuing Swaptions in a String Model

To illustrate its generality, we apply the LSM approach to a deferred American swaption in a 20-factor string model. Swaptions are one of the most important and widely used derivatives in fixed-income markets. We focus on a basic swaption where the optionholder has the right to enter into a swap in which the optionholder receives fixed coupons and pays floating coupons on a semiannual cycle. The floating coupon paid at the end of the semiannual cycle is tied to the six-month rate determined at the beginning of the semiannual cycle; the floating leg sets in advance and pays in arrears. Both legs of the swap are paid on an actual/actual basis. The swaption can only be exercised on semiannual coupon payment dates and only after exchanging the coupons due on the payment date. As is typical, the swaption cannot be exercised until after a specific lockout period.

<!-- page: 27 -->

To provide a specific example, we focus on a 10 NC 1 swaption. This notation indicates the underlying swap has a final maturity of 10 years. The NC 1 (noncall 1) feature indicates that the swaption cannot be exercised until one year has elapsed; the swaption cannot be exercised until the second semiannual coupon payment date. Since there are 20 semiannual coupon payment dates during the life of the underlying 10-year swap, there are 18 possible exercise dates for the swaption; the swaption cannot be exercised at the first coupon payment date, and the swaption has no value at the final coupon payment date.

String models of the term structure have recently received a significant amount of attention in fixed-income markets. In these models, each point along the term structure is a separate random variable, where the term structure is defined either as a discount function or spot curve as in Ho and Lee (1986), a forward curve as in Heath, Jarrow, and Morton (1992), or as a par curve as in Longstaff, Santa-Clara, and Schwartz (1999). Important examples of string models include the recent articles by Goldstein (1997), Santa-Clara and Sornette (2001), Longstaff, Santa-Clara, and Schwartz (1999, 2000).

Since the underlying swap makes coupon payments at 20 different points in time, its value is sensitive to 20 different points along the curve. We implement a simple string model by assuming that each of these 20 points represents a separate but correlated actor, and model the joint dynamics of these 20 factors. Specifically, 'let $D ( t , T )$ denote the value at time t of a zerocoupon bond with final maturity date T, where $t ~ \leq T$ . Since the expected rate of return on all securities must equal the riskless rate in the no-arbitrage equivalent martingale-measure framework, we can represent the no-arbitrage dynamics of the zero-coupon bond price by the following.

$$
\begin{array} { r } { d D ( t , T ) = r ( t ) D ( t , T ) d t + \sigma ( T - t ) D ( t , T ) d Z _ { T } , } \end{array}\tag{18}
$$

where $r ( t )$ is the riskless rate, $\sigma ( T - t )$ is a time-homogeneous volatility function, and Zr is a standard Brownian motion specific to the zero-coupon $Z _ { T }$ bond with final maturity date T.

To operationalize this string model, we assume that the 20 factors are the 20 zero-coupon bond prices with maturities corresponding to the 20 coupon payment dates; specifically, $D ( t , . 5 ) , D ( t , 1 . 0 ) , D ( t , 1 . 5 ) , \ldots , D ( t , 1 0 . 0 )$ We assume that the volatility function $\sigma ( T - t )$ is piecewise constant; $\sigma ( T - t )$ $. 5 ( N - 1 ) \dot { } < T - t \le . 5 N , N = 1 , 2 , \dots , 2 0$ . For simplicis constant over ity, we set $\sigma ( T - t ) = 0$ for values of $T \ : - \ : t \ : < \ : . 5$ The remaining 19 values of $\sigma ( T - t )$ are selected to approximate a cap volatility curve. Similarly, we assume that $r ( t )$ is piecewise constant over six-month intervals;

<!-- page: 28 -->

we set r(t) equal to the six-month rate defined by $r ( t )$ $- 2 \ln ( D ( t , t + 1 / 2 ) )$ . This discretization results in little loss of accuracy and guarantees that the price of a zero-coupon bond converges to one at its maturity date.18

The dynamics of the term structure are simulated by first solving the stochastic differential equation in Equation (18),

$$
\begin{array} { r l r } & { } & { D ( t + 1 / 2 , T ) = D ( t , T ) \exp \bigl ( r ( t ) / 2 - \sigma ^ { 2 } ( T - t ) / 4 } \\ & { } & { \qquad + \sigma ( T - t ) \bigl ( Z _ { T } ( t + 1 / 2 ) - Z _ { T } ( t ) \bigr ) \bigr ) . } \end{array}\tag{19}
$$

With this closed-form expression, the evolution of the term structure can be simulated over six-month periods. The only remaining issue is the correlation structure of the fundamental Brownian motions Zr. To model the correlation $Z _ { T }$ matrix in a parsimonious way, we assume that the correlation between Z: $Z _ { i }$ and $Z _ { j } , i , j \le T$ is given by the function $\rho _ { i j } = \exp ( - \kappa \mid i - j \mid )$ , where $\kappa = . 0 2$ This results in correlations among spot rates similar to those observed empirically. Alternatively, spot-rate correlations could be estimated using historical data and then directly incorporated into the simulation.

The simulation consists of paths where at each coupon date, the entire vector of zero-coupon bond prices is specified. From these zero-coupon bonds, the value of the underlying swap at that coupon date is easily computed by discounting the remaining fixed coupon payments; recall that the floating leg of the swap can be assumed to be worth par on coúpon payment dates. Given the value of the swap, the basis functions are chosen to be a constant, the first three powers of the value of the underlying swap, and all unmatured discount bond prices with final maturity dates up to and including the final maturity date of the swap. Thus there are up to 22 basis functions in the regression. This specification results in values very similar to those obtained by using additional basis functions.

Table 5 reports the estimated values of the deferred American swaption, the corresponding European swaption, and the probabilities of early exercise at each coupon payment date for a variety of fixed coupon rates. As shown, the deferred American exercise feature has significant value; when the coupon rate is .0575, the deferred American swaption is more than three times as valuable as its European counterpart. This underscores the fact that the deferred American and European swaptions are fundamentally different derivatives despite their superficial similarities.

The coupon rate on the fixed leg of the swap also has a major effect on the properties of the swaptions. Clearly, the higher the coupon, the more valuable it is to enter the swap and receive the fixed coupons. For the European swaption, this translates into a higher probability of exercise at the exercise date.

18 The minor discretization error induced by using the six-month rate as a proxy for r(t) can easily be avoided by using more points along the term structure. For example, we could use daily, monthly, or even quarterly rates. Alternatively, we could simply develop the model in a discrete rather than continuous framework as is commonly done in practice.

<!-- page: 29 -->

[Table source crop](assets/tables/2001-longstaff-schwartz-american-options-lsm-p0029-block-0001-8d6a8414cd72abeb.jpg)


In contrast, a higher fixed coupon does not necessarily imply a higher probability of exercise at a specific coupon date for the deferred American swaption. To see this, note that the probability of exercise at the 19th coupon date is 8.33% when the coupon is .0575, but is only 5.45% when the coupon is .0635. The total probability of exercise, however, is monotonic in the coupon rate. These results illustrate that the term structure of exercise probabilities for American options can display very complex patterns in a multifactor framework.

Since each point on the term structure affects the values of the deferred American and European swaptions, it is also interesting to compare the sensitivities of each swaption to each point on the curve. This is done by varying each of the six-month forward rates implied by the initial zero-coupon curve to express the risk exposures in a forward-space metric. As shown in Table 6, deferred American and European swaptions have major differences in their sensitivities to movements in the term structure. For example, the European swaption has the greatest sensitivity to the third forward. In contrast, the deferred American swaption has its greatest sensitivity to the 20th forward. These results illustrate the importance of incorporating the multifactor nature of the term structure in fixed-income derivative risk management.

<!-- page: 30 -->

[Table source crop](assets/tables/2001-longstaff-schwartz-american-options-lsm-p0030-block-0001-279b410cf858cef2.jpg)


## 8. Numerical and Implementation Issues

In this section, we discuss a number of numerical and implementation issues associated with the LSM algorithm. These are discussed individually below.

## 8.1 Higher-dimensional problems

The numerical examples in Sections 3-5 benchmark the performance of the LSM algorithm for several low-dimensional problems which can be solved by standard finite difference techniques. As an additional benchmark, we also investigate the performance of the algorithm for a higher dimensional problem studied by Broadie and Glasserman (1997c), the valuation of an American options on the maximum of five risky assets.

In their article, Broadie and Glasserman (1997) apply a stochastic mesh approach to place bounds on the value an American call option on the maximum of five assets, where each asset has a return volatility of 20% and each return is independent of the others. The option has a three-year life and is exercisable three times per year. The assets each pay a 10% proportional dividend and the riskless rate is assumed to be 5%. The strike price of the option is 100, and the initial values of all assets are assumed to be the same and equal to either 90, 100, or 110. Using their algorithm, they are able to estimate a 90% confidence band for the value of the option. From Table 6 of their article, the tightest 90% confidence bands reported are [16.602, 16.710], [26.101, 26.211], and [36.719, 36.842] for the cases where the initial asset values are 90, 100, and 110, respectively. Broadie and Glasserman report that computing these bounds requires slightly more than 20 hours apiece using a 266 MHz Pentium II processor.

<!-- page: 31 -->

We value this American call option using essentially the same simulation procedure used in Section 3. Specifically, we use 50,000 paths and choose 19 basis functions consisting of a constant, the first five Hermite polynomials in the maximum of the values of the five assets, the four values and squares of the values of the second through fifth highest asset prices, the product of the highest and second highest, second highest and third highest, etc., and finally, the product of all five asset values. The values of the American call option given by the LSM algorithm are 16.657, 26.182, and 36.812 for the cases where the initial asset values are 90, 100, and 110, respectively. In each of these cases, the LSM value is within the tightest bounds given by the Broadie and Glasserman algorithm. We note that computing these values by LSM requires only one to two minutes apiece using a 300 MHz Pentium II processor.

## 8.2 Least squares

In this article, we use ordinary least squares to estimate the conditional expectation function. In some cases, however, it may be more efficient to use other techniques such as weighted least squares, generalized least squares, or even GMM in estimating the conditional expectation function. For example, if the process for the state variables has state dependent volatility, the residuals from the regression may be heteroskedastic and these alternative least squares techniques may have advantages.

In estimating the least squares regressions, it may be noted that the $R ^ { 2 } \ S$ from the regressions are often somewhat low. The reason for this is simply the volatility of realized cash flows around their conditional expected values. The $R ^ { 2 }$ from the regression measures the percentage of the total variation in the ex post cash flows explained by the variation in the conditional expectation function; a low R² simply means that the volatility of unexpected cash flows $R ^ { 2 }$ is large relative to the volatility of expected cash flows. Thus low $R ^ { 2 }$ are to be expected when unexpected cash flows are highly volatile. In general, since the LSM algorithm is based on conditional first moments rather than second moments, the $R ^ { 2 } { \sf s }$ from the regression should have little impact on the quality of the LSM approximation to the American option value.

## 8.3 Choice of basis functions

Extensive numerical tests indicate that the results from the LSM algorithm are remarkably robust to the choice of basis functions. For example, we use the first three Laguerre polynomials as basis functions in the American put illustration in Section 3. We obtain results that are virtually identical to those reported in Table 1 when we use $S , S ^ { 2 }$ 2, and S³ as basis functions, when we $S ^ { 3 }$ use the first three Hermite polynomials as basis functions, or when we use three trigonometric functions as basis functions. Similarly for all of the other examples presented in the article. As reported earlier, few basis functions are needed to closely approximate the conditional expectation function over the relevant range where early exercise may be optimal.

<!-- page: 32 -->

While the results are robust to the choice of basis functions, it is important to be aware of the numerical implications of the choice. For example, the weighted Laguerre polynomials used in the American put illustration in Section 3 include an exponential term in the stock price S. In Table 1, however, the stock price ranges from 36 to 44. Thus, directly applying the weighted Laguerre polynomials to the problem could result in computational underflows. To avoid this problem, we renormalized the American put example by dividing all cash flows and prices by the strike price, and estimating the conditional expectation function in the renormalized space; the results reported in Table 1 are based on this renormalization. Note that this is only for numerical convenience; the option value is unaffected since we discount back the unnormalized value of the cash flows along each path to obtain its value. We recommend normalizing appropriately to avoid numerical errors resulting from scaling problems.

Finally, the choice of basis functions also has implications for the statistical significance of individual basis functions in the regression. In particular, some choices of basis functions are highly correlated with each other, resulting in estimation difficulties for individual regression coefficients akin to the multicolinearity problem in econometrics. This difficulty does not affect the LSM algorithm since the focus is on the fitted value of the regression rather than on individual coefficients; the fitted value of the regression is unaffected by the degree of correlation among the explanatory variables. However, if the choice of basis functions leads to a cross-moment matrix that is nearly singular, then numerical inaccuracies in some least squares algorithms may affect the functional form of estimated conditional expectation function. To avoid these types of numerical problems, the regressions are estimated using the double-precision DLSBRR algorithm in IMSL which estimates least squares via an iterative-refinement algorithm. We also cross-checked the results by estimating the regressions using a variety of alternative procedures such as Cholesky-decomposition and QR-algorithm least squares techniques.

## 8.4 Computational speed

An important advantage of simulation techniques is that they lend themselves well to parallel computing architecture. For example, we could generate 5,000 paths using a single CPU, or we could generate 100 paths each on 50 CPUs. In many large-scale applications, computational speed is far more important than the cost of hardware; valuation and risk management by simulation is ideally suited for these applications. Furthermore, for some types of large-scale applications such as valuing large portfolios of fixedincome or mortgage derivatives, the same paths can be used for all options; significant computational efficiencies are obtained by only having to generate paths once. From the perspective of the LSM algorithm, the only constraint on parallel computation is that the regression needs to use the cross-sectional information in the simulation. Given the speed at which regressions can be estimated, however, this bottleneck involves little loss of computational efficiency. Furthermore, there are many ways in which regressions could be estimated using individual CPUs, and then aggregated across CPUs to form a composite estimate of the conditional expectation function. Finally, the use of quasi-Monte-Carlo techniques in conjunction with the LSM algorithm may lead to significant improvements in computational speed and efficiency. Important recent examples of the application of quasi-Monte-Carlo techniques include Morokoff and Caflisch (1994, 1995).

<!-- page: 33 -->

## 9. Conclusion

This article presents a simple new technique for approximating the value of American-style options by simulation. This approach is intuitive, accurate, easy to apply, and computationally efficient. We illustrate this technique using a number of realistic examples, including the valuation of an American put when the underlying stock price follows a jump-diffusion as well as the valuation of a deferred American swaption in a 20-factor string model of the term structure.

As a framework for valuing and. risk managing derivatives, simulation has many important advantages. With the ability to value American options, the applicability of simulation techniques becomes much broader and more promising, particularly in markets with multiple factors. Furthermore, simulation techniques make it much easier to implement advanced models such as Heath, Jarrow, and Morton (1992) or Santa-Clara and Sornette (1997) in practice.

## Appendix

Proof of Proposition 1. By definition, the value of the underlying asset X is Ft-measurable. $X _ { t _ { k } }$ $\mathcal { F } _ { t _ { k } }$ Similarly, the immediate exercise value of the option is F-measurable. By construction, $\mathcal { F } _ { t _ { k } }$ $F _ { M } ( \omega ; t _ { k } )$ is a linear function of F-measurable functions of X,r, and is therefore F -measurable. $\mathcal { F } _ { t _ { k } }$ $X _ { t _ { K } }$ $\mathcal { F } _ { t _ { k } }$ Hence the event that the immediate exercise value is greater than zero and greater than or equal to $F _ { M } ^ { } ( \omega ; t _ { k } )$ is in F, and therefore, the LSM rule to exercise when this event occurs $\mathcal { F } _ { \iota _ { k } }$ defines a stopping time. Denote the present value of following this stopping rule by E. Since $E _ { \theta }$ V(X) is the supremum of the present values obtained over the set of all stopping times, $V ( X ) \geq E _ { \theta }$ . Since the functional form of $F _ { M } ( \omega ; t _ { k } )$ is the same across all paths, the discounted cash flows $\mathbf { L S M } ( \omega _ { i } ; M , K )$ are independently and identically distributed, and the strong law of large numbers [Billingsley (1979; Theorem 6.1)] implies that

$$
\operatorname* { P r } \biggr [ \operatorname* { l i m } _ { N \to \infty } \frac { 1 } { N } \sum _ { i = 1 } ^ { N } L S M ( \omega _ { i } ; M , K ) = E _ { \theta } \biggr ] = 1 .
$$

<!-- page: 34 -->

This result, combined with the inequality $V ( X ) \geq E _ { \theta }$ , implies the result.

Proof of Proposition 2. At time t2, the LSM stopping strategy is the same as the optimal $t _ { 2 } :$ strategy; the option is exercised if it is in the money. Under the given assumptions, the conditional expectation function $F ( \omega ; t _ { 1 } )$ is a function only of $X _ { t _ { 1 } } , ~ \mathrm { I f } ~ F ( \omega ; t _ { 1 } )$ satisfies the indicated conditions, then Theorem IV.9.1 of Sansone (1959) implies that the convergence of $F _ { M } ( \omega ; t _ { 1 } )$ to $F ( \omega ; t _ { \mathrm { i } } )$ is uniform in M on the set (0, ∞), where the first M Laguerre polynomials are used as the set of basis functions. This implies that for a given €, there exists an M such $\epsilon ,$ that $\begin{array} { r } { \operatorname* { s u p } _ { X _ { t _ { 1 } } } \mid F ( \omega ; t _ { 1 } ) - F _ { M } ( \omega ; t _ { 1 } ) \mid < \epsilon / 2 } \end{array}$ From the integrability conditions and Theorem 3.5 of White (1984), the fitted value of the LSM regression $\widehat { F } _ { M } ( \omega ; t _ { 1 } )$ converges in probability to $F _ { M } ( \omega ; t _ { 1 } )$ as $N \to \infty$

$$
\operatorname* { l i m } _ { N \to \infty } \operatorname* { P r } \bigl \{ | ~ { \cal F } _ { M } ( \omega ; t _ { 1 } ) - \widehat { { \cal F } } _ { M } ( \omega ; t _ { 1 } ) ~ | > \epsilon / 2 \bigr \} = 0 .
$$

Thus, for any €, there is an M such that

$$
\operatorname* { l i m } _ { N \to \infty } \operatorname* { P r } \bigl [ | \ F ( \omega ; t _ { 1 } ) - \widehat { F } _ { M } ( \omega ; t _ { 1 } ) \ | > \epsilon \bigr ] = 0 .
$$

To complete the proof, we partition Ω into five sets: 1) the set of paths where the option is exercised at time t, under both the optimal and the LSM strategy, 2) the set of paths where $t _ { 1 }$ the option is not exercised at time t1 under either the optimal or LSM strategies, 3) the set $t _ { 1 }$ of paths where the option is exercised at time t, under the LSM strategy but not under the $t _ { \textup I }$ optimal strategy, 4) the set of paths where the option is exercised at time t, under the optimal $t _ { \downarrow }$ strategy, but not under the LSM strategy, and 5) a zero-probability set of paths for which the difference between $F ( \omega ; t _ { 1 } )$ and $\widehat { F } _ { M } ( \omega ; t _ { 1 } )$ is greater than $\epsilon \mathrm { ~ \ a s ~ \ } N \mathrm { ~ ~ \infty ~ }$ .Now consider a portfolio consisting of a long position in an option exercised using the LSM strategy, an investment of ε in a money market account, and a short position in an option exercised using the optimal strategy. For paths in set 3), at time t1, use the funds from the money market account $t _ { 1 } { \mathrm { : } }$ and the option exercise to purchase a European option with final maturity date t2. For paths in $t _ { 2 }$ set 4), at time t1, use the funds from the money market account and from shorting a European $t _ { \mathrm { l } } ,$ option with final maturity date t2 to fund the cash outflow from the option exercise. It is easily $t _ { 2 }$ shown that this strategy results in cash flows that are greater than or equal to zero for each path in sets 1), 2), 3), and 4). Since the pathwise cash flows are nonnegative, averages over paths are nonnegative, and the result follows from a standard no-arbitrage argument, the definition of $V ( X )$ , and the law of large numbers. ■

## References

Abramowitz, M., and I. A. Stegun, 1970, Handbook of Mathematical Functions, Dover Publications, New York. Amemiya, T., 1985, Advanced Econometrics, Basil Blackwell, London, UK. Averbukh, V., 1997, "Pricing American Options Using Monte Carlo Simulation," Ph.D. dissertation, Cornell University. Barraquand, J., and D. Martineau, 1995, "Numerical Valuation of High Dimensional Multivariate American Securities," Journal of Financial and Quantitative Analysis, 30, 383–405. Barron, A., 1993, “Universal Approximation Bounds for Superpositions of a Sigmoidal Function," IEEE Transactions, Information Theory, 39, 930–945. Bensoussan, A., 1984, "On the Theory of Option Pricing," Acta Applicandae Mathematicae, 2, 139–158. Billingsley, P., 1979, Probability and Measure, Wiley, New York.

<!-- page: 35 -->

Black, F., and M. Scholes, 1973, "The Pricing of Options and Corporate Liabilities," Journal of Political Economy, 81, 637–654. Bossaerts, P., 1989, "Simulation Estimators of Optimal Early Exercise," working paper, Carnegie-Mellon University. Broadie, M., J. Detemple, E. Ghysels, and O. Torres, 1998, "American Options with Stochastic Dividends and Volatility: A Nonparametric Investigation," working paper, Columbia University. Broadie, M., and P. Glasserman, 1997a, "Monte Carlo Methods for Pricing High-Dimensional American Options: An Overview," working paper, Columbia University. Broadie, M., and P. Glasserman, 1997b, "Pricing American-Style Securities Using Simulation," Journal of Economic Dynamics and Control, 21, 1323–1352. Broadie. M., and P. Glasserman. 1997c, "A Stochastic Mesh Method for Pricing High-Dimensional American Options," working paper, Columbia University. Broadie, M., P. Glasserman, and G. Jain, 1997, "Enhanced Monte Carlo Estimates for American Option Prices," Journal of Derivatives, 5, 25–44. Carriere, J.. 1996, "Valuation of Early-Exercise Price of Options Using Simulations and Nonparametric Regression," Insurance: Mathematics and Economics, 19, 19–30. Carr, P., 1998, "Randomization and the American Put," Review of Financial Studies, 11, 597-626. Cox, J., J. E. Ingersoll, and S. A. Ross, 1985, "An Intertemporal General Equilibrium Model of Asset Prices," Econometrica, 53, 363-384. Cox, J., and S. A. Ross, 1976, "The Valuation of Options for Alternative Stochastic Processes," Journal of Financial Economics, 3, 145–166. Duffie, D., 1996, Dynamic Asset Pricing Theory, Princeton University Press, Princeton, N.J. Garcia, D., 1999, “A Monte Carlo Method for Pricing American Options," working paper, University of California, Berkeley. Goldstein, R., 1997, "The Term Structure of Interest Rates as a Random Field," working paper, Ohio State University. Harrison. J. M., and D. M. Kreps, 1979, "Martingales and Arbitrage in Multiperiod Securities Markets," Journal of Economic Theory, 20, 381–408. Harrison, J. M., and S. R. Pliska, 1981, "Martingales and Stochastic Integrals in the Theory of Continuous Trading," Stochastic Processes and their Applications, 11, 261–271. Heath, D., R. Jarrow, and A. Morton, 1992, "Bond Pricing and the Term Structure of Interest Rates," Econometrica, 60, 77–106 Ho, T., and S. Lee, 1986, "Term Structure Movements and Pricing Interest Rate Contingent Claims," Journal of Finance, 41, 1011–1029. Ibanez, A., and F. Zapatero, 1998, "Monte Carlo Valuation of American Options through Computation of the Optimal Exercise Frontier," working paper, .University of Southern California. Keane, M., and K. Wolpin, 1994, "The Solution and Estimation of Discrete Choice Dynamic Programming Models by Simulation: Monte Carlo Evidence," Review of Economics and Statistics, 76, 648-672. Judd. K., 1998, Numerical Methods in Economics, MIT Press, Cambridge, Mass. Karatzas, I, 1988, "On the Pricing of American Options," Applied Mathematics and Optimization, 17, 37–60 Lamberton, D., and B. Lapeyre, 1996, Stochastic Calculus Applied to Finance, Chapman & Hall, London,UK.

<!-- page: 36 -->

Longstaff, F., P. Santa-Clara, and E. Schwartz, 1999, "Throwing Away a Billion Dollars: The Cost of Suboptimal Exercise Strategies in the Swaptions Market," working paper, University of California, Los Angeles. Longstaff, F., P. Santa-Clara, and E. Schwartz, 2000, "The Relative Valuation of Interest-Rate Caps and Swaptions: Theory and Empirical Evidence," working paper, University of California, Los Angeles. Merton, R. C., 1973, "The Theory of Rational Option Pricing," Bell Journal of Economics and Management Science, 4, 141–183. Merton, R. C., 1976, "Option Pricing When Underlying Stock Returns Are Discontinuous," Journal of Financial Economics, 3, 125–144. Morokoff, W. J., and R. E. Caflisch, 1994, "Quasi-Random Sequences and Their Discrepancies," SIAM Journal of Computing, 15, 1251–1279. Morokoff, W. J., and R. E. Caflisch, 1995, "Quasi-Monte Carlo Integration," Journal of Computational Physics, 122, 218–230. Pham, H., 1995, "Optimal Stopping, Free Boundary and American Option in a Jump Diffusion Model," working paper, Universite Paris IX Dauphine. Press, W. H., S. A. Teukolsky, W. T. Vetterling, and B. P. Flannery, 1992, Numerical Recipes in Fortran, 2nd ed., Cambridge University Press, Cambridge, UK. Raymar, S., and M. Zwecher, 1997, "A Monte Carlo Valuation of American Call Options on the Maximum of Several Stocks," Journal of Derivatives, 5, 7–23. Refenes, A., A. Burgess, and Y. Bentz, 1997, "Neural Networks in Financial Engineering: A Study in Methodology," IEEE Transactions, Neural Networks, 8, 1222–1267. Royden, H. L., 1968, Real Analysis, MacMillan, New York., Sansone, G., 1959, Orthogonal Functions, Interscience Publishers, New York. Santa-Clara, P., and D. Sornette, 2001, "The Dynamics of the Forward Interest Rate Curve with Stochastic String Shocks," The Review of Financial Studies, 14, 149–185. Tilley, J. A., 1993, "Valuing American Options in a Path Simulation Model," Transactions of the Society of Actuaries, 45, 83–104. Tsitsiklis, J., and B. Van Roy, 1999, "Optimal Stopping of Markov Processes: Hilbert Space Theory, Approximation Algorithms, and an Application to Pricing High-Dimensional Financial Derivatives,"lEEE Transactions on Automatic Control, 44, 1840–1851. Vasicek, O., 1977, "An Equilibrium Characterization of the Term Structure," Journal of Financial Economics, 5, 177–188. White, H., 1984, Asymptotic Theory for Econometricians, Academic Press, New York.
