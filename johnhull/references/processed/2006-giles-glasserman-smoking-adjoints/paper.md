---
paper_id: "2006-giles-glasserman-smoking-adjoints"
title: "Smoking Adjoints: Fast Monte Carlo Greeks"
authors: "Mike Giles; Paul Glasserman"
year: "2006"
source_url: "https://ora.ox.ac.uk/objects/uuid:f536b1a8-c988-4bda-9c5f-a322652139fd"
source_pdf: "references/papers/2006-giles-glasserman-smoking-adjoints.pdf"
source_sha256: "532d46c48bb98b6ef049f08b433237d0b5be114d281d09ceae387abed7de666a"
converter: "PyMuPDF4LLM 1.28.0"
---

<!-- page: 1 -->

# Smoking Adjoints: fast evaluation of Greeks in Monte Carlo calculations 

## Michael Giles 

Oxford University Computing Laboratory, Parks Road, Oxford, U.K. 

Paul Glasserman Columbia Business School, 403 Uris Hall, New York, NY 10028. 

This paper presents an adjoint method to accelerate the calculation of Greeks by Monte Carlo simulation. The method calculates price sensitivities along each path; but in contrast to a forward pathwise calculation, it works backward recursively using adjoint variables. Along each path, the forward and adjoint implementations produce the same values, but the adjoint method rearranges the calculations to generate potential computational savings. The adjoint method outperforms a forward implementation in calculating the sensitivities of a small number of outputs to a large number of inputs. This applies, for example, in estimating the sensitivities of an interest rate derivatives book to multiple points along an initial forward curve or the sensitivities of an equity derivatives book to multiple points on a volatility surface. We illustrate the application of the method in the setting of the LIBOR market model. Numerical results confirm that the computational advantage of the adjoint method grows in proportion to the number of initial forward rates. 

Key words and phrases: computational finance, Monte Carlo, adjoint 

Oxford University Computing Laboratory Numerical Analysis Group Wolfson Building Parks Road Oxford, England OX1 3QD 

August, 2005

<!-- page: 2 -->

# 1 Introduction 

The efficient calculation of price sensitivities continues to be among the greatest practical challenges facing users of Monte Carlo methods in the derivatives industry. Computing Greeks is essential to hedging and risk management, but typically requires substantially more computing time than pricing a derivative. This article shows how an adjoint formulation can be used to accelerate the calculation of the Greeks. This method is particularly well suited to applications requiring sensitivities to a large number of parameters. Examples include interest rate derivatives requiring sensitivities to all initial forward rates and equity derivatives requiring sensitivities to all points on a volatility surface. 

The simplest methods for estimating Greeks are based on finite difference approximations, in which a Monte Carlo pricing routine is re-run multiple times at different settings of the input parameters in order to estimate sensitivities to the parameters. In the fixed income setting, for example, this would mean perturbing each initial forward rate and then re-running the Monte Carlo simulation to re-price a security or a whole book. The main virtues of this method are that it is straightforward to understand and requires no additional programming. But the bias and variance properties of finite difference estimates can be rather poor, and their computing time requirements grow with the number of input parameters. 

Better estimates of price sensitivities can often be derived by using information about model dynamics in a Monte Carlo simulation. Techniques for doing this include the pathwise method and likelihood ratio method, both of which are reviewed in Chapter 7 of Glasserman [4]. When applicable, these methods produce unbiased estimates of price — sensitivities from a single set of simulated paths i.e., without perturbing any parameters. The pathwise method accomplishes this by differentiating the evolution of the underlying assets or state variables along each path; the likelihood ratio method instead differentiates the transition density of the underlying assets or state variables. In comparison to finite difference estimates, these methods require additional model analysis and programming, but the additional effort is often justified by the improvement in the quality of calculated Greeks. 

The adjoint method we develop here applies ideas used in computational fluid dynamics [3] to the calculation of pathwise estimates of Greeks. The estimate computed using the adjoint method is identical to the ordinary pathwise estimate; its potential advantage is therefore computational, rather than statistical. The relative merits of the ordinary (forward) calculation of pathwise Greeks and the adjoint calculation be summarized as follows: 

The adjoint method is advantageous for calculating the sensitivities of a small number of securities with respect to a large number of parameters. The forward method is advantageous for calculating the sensitivities of many securities with respect to a small number of parameters. 

The “small number of securities” in this dichotomy could be an entire book, consisting of many individual securities, so long as the sensitivities to be calculated are for the

<!-- page: 3 -->

book as a whole and not for the constituent securities. 

The rest of this article is organized as follows. Section 2 reviews the usual forward calculation of pathwise Greeks and Section 3 illustrates its application in the LIBOR market model. Section 4 develops the adjoint method for delta estimates. Section 5 extends it to applications like vega estimation requiring sensitivities to parameters of model dynamics, rather than just sensitivities to initial conditions; Section 6 extends it to gamma estimation. We use the LIBOR market model as an illustrative example in both settings. Section 7 presents numerical results which illustrate the computational savings offered by the adjoint method. 

# 2 Pathwise Delta: Forward Method 

We start by reviewing the application of the pathwise method for computing price sensitivities in the setting of a multidimensional diffusion process satisfying a stochastic differential equation 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0003-05.png)


The process X<sup>˜</sup> is m-dimensional, W is a d-dimensional Brownian motion, a(·) takes values in R<sup>m</sup> and b(·) takes values in R<sup>m×d</sup> . For example, X<sup>˜</sup> could record a vector — — of equity prices or as in the case of the LIBOR market model, below a vector of forward rates. We take (2.1) to be the risk-neutral or otherwise risk-adjusted dynamics of the relevant financial variables. A derivative security maturing at time T with discounted payoff g( X<sup>˜</sup> (T )) has price E[g( X<sup>˜</sup> (T )], the expected value of the discounted payoff. 

In a Monte Carlo simulation, the evolution of the process X<sup>˜</sup> is usually approximated using an Euler scheme. For simplicity, we take a fixed time step h = T/N , with N an integer. We write X(n) for the Euler approximation at time nh, which evolves according to 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0003-08.png)


where Z(1), Z(2), . . . are independent d-dimensional standard normal random vectors. With the normal random variables held fixed, (2.2) takes the form 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0003-10.png)


with Fn a transformation from R<sup>m</sup> to R<sup>m</sup> . 

The price of the derivative with discounted payoff function g is estimated using the average of independent replications of g(X(N )), N = T/h. Now consider the problem of estimating 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0003-13.png)


the delta with respect to the jth underlying variable. The pathwise method estimates this delta using 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0003-15.png)

<!-- page: 4 -->

the sensitivity of the discounted payoff along the path. This is an unbiased estimate if 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0004-02.png)


i.e., if the derivative and expectation can be interchanged. 

Conditions for this interchange are discussed in Glasserman [4], pp.393–395. Convenient sufficient conditions impose some modest restrictions on the evolution of X<sup>˜</sup> and some minimal smoothness on the discounted payoff g, such as a Lipschitz condition. If g is Lipschitz, it is differentiable almost everywhere and we may write 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0004-05.png)


Conditions under which X<sup>˜</sup> i(T ) is in fact differentiable in X<sup>˜</sup> i(0) are discussed in Protter [9], p.250. 

Using the Euler scheme (2.2), we approximate the pathwise derivative estimate using 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0004-08.png)


with 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0004-10.png)


Thus, in order to evaluate (2.4), we need to compute the state sensitivities ∆ij(N ). We simulate their evolution by differentiating (2.2) to get 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0004-12.png)


with ai denoting the ith component of a(X(n)) and biℓ denoting the (i, ℓ) component of the b(X(n)). 

We can write this as a matrix recursion by letting ∆(n) denote the m × m matrix with entries ∆ij(n). Let D(n) denote the m × m matrix with entries 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0004-15.png)


where δik is 1 if i = k and 0 otherwise. The evolution of ∆can now be written as 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0004-17.png)


with initial condition ∆(0) = I where I is the m×m identity matrix. The matrix D(n) is the derivative of the transformation Fn in (2.3). For large m, propagating this m×m recursion may add substantially to the computational effort required to simulate the original vector recursion (2.2).

<!-- page: 5 -->

# 3 LIBOR Market Model 

To help fix ideas, we now specialize to the LIBOR market model of Brace, Gatarek and Musiela [2]. Fix a set of m +1 bond maturities Ti, i = 1, . . . , m + 1, with spacings Ti+1 − Ti = δi. Let L<sup>˜</sup> i(t) denote the forward LIBOR rate fixed at time t for the interval [Ti, Ti+1), i = 1, . . . , m. Let η(t) denote the index of the next maturity date as of time t, Tη(t)−1 ≤ t < Tη(t). The arbitrage-free dynamics of the forward rates take the form 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0005-03.png)


where W is a d-dimensional standard Brownian motion under a risk-adjusted measure and 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0005-05.png)


Although µi has an explicit dependence on t through η(t), we suppress this argument. To keep this example as simple as possible, we take each σi (a d-vector of volatilities) to be a function of time to maturity, 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0005-07.png)


as in [5]; however, the same ideas apply if σi is itself a function of L<sup>˜</sup> (t), as it often would be in trying to match a vol skew. 

To simulate, we apply an Euler scheme to the logarithms of the forward rates, rather than the forward rates themselves. This yields 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0005-10.png)


Once a rate settles at its maturity it remains fixed, so we set Li(n + 1) = Li(n) if i < η(nh). The computational cost of implementing (3.2) is minimized by first evaluating the summations 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0005-12.png)


This then gives µi = σi<sup>⊤Siand hence the total computational cost is O(m) per timestep.</sup> A simple example of a derivative in this context is a caplet for the interval [Tm, Tm+1) struck at K. It has discounted payoff 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0005-14.png)


LWe can express this as a function of˜i(t) at L˜i(Ti) for t > Ti. It is convenientL<sup>˜</sup> (Tm) (rather thanto includeL<sup>˜</sup> (theTi),maturities i = 1, . . . , mTi) by freezingamong the simulated dates of the Euler scheme, introducing unequal step sizes if necessary.

<!-- page: 6 -->

![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0006-01.png)


<!-- Start of picture text -->
 1 1   1 1 <br>   <br> 1   1 <br>   <br>D =  ×  , D ⊤ =  × × × × <br> × ×   × × × <br> × × ×   × × <br>× × × × ×<br>   <br><!-- End of picture text -->

Figure 1: Structure of the matrix D and its transpose: × is a non-zero entry, blanks are zero. 

Glasserman and Zhao [5] develop (and rigorously justify) the application of the pathwise method in this setting. Their application includes the evolution of the derivatives 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0006-04.png)


which can be found by differentiating (3.2). In the notation of (2.5), the matrix D(n) has the structure shown in Figure 1, with diagonal entries 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0006-06.png)


and, for j = i, 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0006-08.png)


The efficient implementation used in the numerical results of [5] uses ∆ij(n+1) = ∆ij(n) for i < η(nh), while for i ≥ η(nh) 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0006-10.png)


The summations on the right can be computed at a cost which is O(m) for each j, and hence the total computational cost per timestep is O(m<sup>2</sup> ) rather than the O(m<sup>3</sup> ) cost of implementing (2.5) in general. 

Despite this, the number of forward rates m in the LIBOR market model can easily be 20–80, making the numerical evaluation of ∆ij(n) rather costly. To get around this problem, Glasserman and Zhao [5] proposed faster approximations to (2.5). The adjoint method in the next section can achieve computational savings without introducing any approximation beyond that already present in the Euler scheme.

<!-- page: 7 -->

![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0007-01.png)


<!-- Start of picture text -->
X(0) - X(1) - . . . - X(N−1) - X(N )<br>$<br>?<br>D(0) D(1) D(N−1) g, ∂g/∂X<br>? ? ?<br>V (0) V (1) . . . V (N−1) V (N ) %<br><!-- End of picture text -->

Figure 2: Dataflow showing relationship between forward and adjoint calculations 

# 4 Pathwise Delta: Adjoint Method 

Consider again the general setting of (2.1) and (2.2) and write ∂g/∂X(0) for the row vector of derivatives of g(X(N )) with respect to the elements of X(0). With (2.4) and (2.5), we can write this as 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0007-05.png)


where V (0) can be calculated recursively using 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0007-07.png)


The key point is that the adjoint relation (4.2) is a vector recursion whereas (2.5) is a matrix recursion. Thus, rather than update m<sup>2</sup> variables at each time step, it suffices to update the m entries of the adjoint variables V (n). This can represent a substantial savings. 

The adjoint method accomplishes this by fixing the payoff g in the initialization of V (N ), whereas the forward method allows calculation of pathwise deltas for multiple payoffs once the ∆(n) matrices have been simulated. Thus, the adjoint method is beneficial if we are interested in calculating sensitivities of a single function g with respect – to multiple changes in the initial condition X(0) for example, if we need sensitivities with respect to each Xi(0). The function g need not be associated with an individual security; it could be the value of an entire portfolio. 

The adjoint recursion in (4.2) runs backward in time, starting at V (N ) and working recursively back to V (0). To implement it, we need to store the vectors X(0), . . . , X(N )

<!-- page: 8 -->

as we simulate forward in time so that we can evaluate the matrices D(N −1), . . . , D(0) as we work backward. This introduces some additional storage requirements, but these requirements are relatively minor because it suffices to store just the current path. The final calculation V (0)<sup>⊤</sup> ∆(0) produces exactly the same result as the forward calculations (2.4)–(2.5), but it does so with O(Nm<sup>2</sup> ) operations rather than O(Nm<sup>3</sup> ) operations. 

To help fix ideas, we unravel the adjoint calculation in the setting of the LIBOR market model. After initializing V (N ) according to (4.2), we set Vi(n) = Vi(n+1) for i < η(nh), while for i ≥ η(nh) 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0008-03.png)


The summations on the right can be computed at a cost which is O(m), so the total cost per timestep is O(m) which is better than in the general case. 

This is an example of a general feature of adjoint methods; whenever there is a particularly efficient way of implementing the original calculation there is also an efficient implementation of the adjoint calculation. This comes from a general result in the theory of Algorithmic Differentiation [7], proving that the computational complexity of the adjoint calculation is no more than 4 times greater than the complexity of the original algorithm. There are a variety of tools available for the automatic generation of efficient adjoint implementations, given an implementation of the original algorithm in C or C++ [1]. A brief overview of the key ideas in Algorithmic Differentiation is given in the appendix. 

# 5 Pathwise Vegas 

Section 4 considers only the case of pathwise deltas, but similar ideas apply in calculating sensitivities to volatility parameters. The key distinction is that volatility parameters affect the evolution equation (2.3), and not just its initial conditions. Indeed, although we focus on vega, the same ideas apply to other parameters of the dynamics of the underlying process. 

To keep the discussion generic, let θ denote a parameter of Fn in (2.3). For example, θ could parameterize an entire vol surface or it could be the volatility of an individual rate at a specific date. The pathwise estimate of sensitivity to θ is 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0008-09.png)


If we write Θ(n) for the vector ∂X(n)/∂θ, then we get 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0008-11.png)

<!-- page: 9 -->

with initial conditions Θ(0) = 0. The sensitivity to θ can then be evaluated as 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0009-02.png)


where V (n) is the same vector of adjoint variables defined by (4.2). 

In applying these ideas to the LIBOR market model, B becomes a matrix, with each column corresponding to a different element of the initial volatility vector σj(0). The derivative of the i<sup>th</sup> element of Fn(Xn) with respect to σj(nh) is 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0009-05.png)


where Si is as defined in (3.3). This has a similar structure to that of the matrix D in Figure 1, except for the leading diagonal elements which are now zero. However, the matrix B is the derivative of Fn(Xn) with respect to the initial volatilities σj(0), so given the definition (3.1), the entries in the matrix B are offset so that it has the structure shown in Figure 3. 

From (5.2), the column vector of vega sensitivities is equal to 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0009-08.png)


The i<sup>th</sup> element of the product B(n)<sup>⊤</sup> V (n+1) is zero except for 1 ≤ i ≤ N −η(nh) + 1 for which 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0009-10.png)


where i<sup>∗</sup> ≡ i + η(nh) − 1. The summations on the right for the different values of i<sup>∗</sup> are exactly the same summations performed in the efficient implementation of the adjoint calculation described in the previous section. Hence, the computational cost is O(m) per timestep.

<!-- page: 10 -->

![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0010-01.png)


Figure 3: Structure of the matrix B and its transpose: × is a non-zero entry, blanks are zero. 

# 6 Pathwise Gamma 

The second order sensitivity of g to changes in X(0) is 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0010-05.png)


where 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0010-07.png)


Differentiating (2.3) twice yields 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0010-09.png)


where Diℓ(n) is as defined previously, and 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0010-11.png)


For a particular index pair (j, k), by defining 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0010-13.png)


this may be written as 

## G(n+1) = D(n) G(n) + C(n). 

This is now in exactly the same form as the vega calculation, and so the same adjoint approach can be used. Option payoffs ordinarily fail to be twice differentiable, so using (6.1) requires replacing the true payoff g with a smoothed approximation. 

The computational operation count is O(Nm<sup>3</sup> ) for the forward calculation of L(n) and ∆(n) (and hence D(n) and the vectors C(n) for each index pair (j, k)) plus O(Nm<sup>2</sup> ) for the backward calculation of the adjoint variables V (n), followed by an O(Nm<sup>3</sup> ) cost for evaluating the final sums in (5.2) for each (j, k). This is again a factor O(m) less expensive than the alternative approach based on a forward calculation of Γijk(n).

<!-- page: 11 -->

![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0011-01.png)


<!-- Start of picture text -->
40<br>forward delta<br>35 forward delta/vega<br>adjoint delta<br>adjoint delta/vega<br>30<br>25<br>20<br>15<br>10<br>5<br>0<br>0 20 40 60 80 100<br>Maturity N<br>relative cost<br><!-- End of picture text -->

Figure 4: Relative CPU cost of forward and adjoint delta and vega evaluation for a portfolio of 15 swaptions 

# 7 Numerical Results 

Since the adjoint method produces exactly the same sensitivity values as the forward pathwise approach, the numerical results address the computational savings given by the adjoint approach applied to the LIBOR market model. The calculations are performed using one timestep per LIBOR interval (i.e., the timestep h equals the spacing δi ≡ δ, which we take to be a quarter of a year). We take the initial forward curve to be flat at 5% and all volatilities equal to 20% in a single-factor (d = 1) model. Our test portfolio consists of options on 1-year, 2-year, 5-year, 7-year and 10-year swaps with quarterly payments and swap rates of 4.5%, 5.0% and 5.5%, for a total of 15 swaptions. All swaptions expire in N periods, with N varying from 1 to 80. 

Figure 4 plots the execution time for the forward and adjoint evaluation of both deltas and vegas, relative to the cost of simply valuing the swaption portfolio. The two curves marked with circles compare the forward and adjoint calculations of all deltas; the curves marked with stars compare the combined calculations of all deltas and vegas. 

As expected, the relative cost of the forward method increases linearly with N , whereas the relative cost of the adjoint method is approximately constant. Moreover, adding the vega calculation to the delta calculation substantially increases the time required using the forward method; but this has virtually no impact on the adjoint method because the deltas and vegas use the same adjoint variables. 

It is also interesting to note the actual magnitudes of the costs. For the forward method, the time required for each delta and vega evaluation is approximately 10%

<!-- page: 12 -->

and 20%, respectively, of the time required to evaluate the portfolio. This makes the forward method 10–20 times more efficient than using central differences, indicating a clear superiority for forward pathwise evaluation compared to finite differences for applications in which one is interested in the sensitivities of a large number of different financial products. For the adjoint method, the observation is that one can obtain the sensitivity of one financial product (or a portfolio) to any number of input parameters for less than the cost of the original product evaluation. 

The reason for the forward and adjoint methods having much lower computational cost than one might expect, relative to the original evaluation, is that in modern microprocessors, division and exponential function evaluation are 10–20 times more costly than multiplication and addition. By re-using quantities such as Li(n +1)/Li(n) and (1 + δiLi(n))<sup>−1</sup> which have already been evaluated in the original calculation, the forward and adjoint methods can be implemented using only multiplication and addition, making their execution very rapid. 

# 8 Conclusions 

We have shown how an adjoint formulation can be used to accelerate the calculation of Greeks by Monte Carlo simulation using the pathwise method. The adjoint method produces exactly the same value on each simulated path as would be obtained using a – forward implementation of the pathwise method; but it rearranges the calculations – working backward along each path to generate potential computational savings. 

The adjoint formulation outperforms a forward implementation in computing the sensitivity of a small number of outputs to a large number of inputs. This applies, for example, in a fixed income setting, in which the output is the value of a derivatives book and the inputs are points along the forward curve. We have illustrated the use of the — adjoint method in the setting of the LIBOR market model and found it to be fast smoking fast. 

# References 

- [1] Automatic Differentiation research community website, www.autodiff.org. 

- [2] Brace, A., Gatarek, D., and Musiela, M. (1997) The market model of interest rate dynamics, Mathematical Finance 7:127–155. 

- [3] Giles, M.B., and Pierce, N.A. (2000) An introduction to the adjoint approach to design, Flow, Turbulence and Control 65:393–415. 

- [4] Glasserman, P. Monte Carlo Methods in Financial Engineering, Springer-Verlag, New York, (2004). 

- [5] Glasserman, P., and Zhao, X. (1999) Fast Greeks by simulation in forward LIBOR models, Journal of Computational Finance 3:5–39.

<!-- page: 13 -->

- [6] Giering, R., and Kaminski, T. (1998) Recipes for adjoint code construction, ACM Transactions on Mathematical Software 24(4):437–474. 

- [7] Griewank, A. Evaluating derivatives : principles and techniques of algorithmic differentiation, SIAM, (2000). 

- [8] Griewank, A., and Juedes, D. and Utke, J. (1996) ADOL-C: a package for the automatic differentiation of algorithms written in C/C++, ACM Transactions on Mathematical Software 22(2):437–474. 

- [9] Protter, P. Stochastic Integration and Differential Equations, Springer-Verlag, Berlin, (1990).

<!-- page: 14 -->

# Appendix A Algorithmic Differentiation 

AD, which can stand for either Algorithmic Differentiation [7] or Automatic Differentiation [8], concerns the computation of sensitivity information from an algorithm or computer program. 

Consider a computer program which starts with a number of input variables ui, i = 1, . . . I which can be represented collectively as an input vector u<sup>0</sup> . Each step in the execution of the computer program computes a new value as a function of two previous values; unitary functions such as exp(x) can be viewed as a binary function with no dependence on the second parameter. Appending this new value to the vector of active variables, the n<sup>th</sup> execution step can be expressed as 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0014-04.png)


where fn is a scalar function of two of the elements of u<sup>n−1</sup> . The result of the complete N steps of the computer program can then be expressed as the composition of these individual functions to give 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0014-06.png)


In computing sensitivities, what we are interested in is the derivative of one or more elements of the output vector u<sup>N</sup> with respect to one or more elements of the input vector u<sup>0</sup> . Using the notation which is standard within the AD literature, we define ˙u<sup>n</sup> to be the derivative of the vector u<sup>n</sup> with respect to one particular element of u<sup>0</sup> . Differentiating (A.1) then gives 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0014-08.png)


with I<sup>n−1</sup> being the identity matrix with dimension equal to the length of the vector u<sup>n−1</sup> . The derivative of (A.2) then gives 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0014-10.png)


which gives the sensitivity of the entire output vector to the change in one particular element of the input vector. The elements of the initial vector ˙u<sup>0</sup> are all zero except for a unit value for the particular element of interest. If one is interested in the sensitivity to NI different input elements, then (A.4) must be evaluated for each one, at a cost which is proportional to NI. 

The above description is of the forward mode of AD sensitivity calculation, which is intuitively quite natural. However, there is a second approach, the reverse or adjoint mode, which is computationally much more efficient when one is interested in the sensitivity of a small number of output quantities with respect to a large number of input

<!-- page: 15 -->

parameters. Again using the standard AD notation, we define the column vector <u>u</u><sup>n</sup> to be the derivative of a particular element of the output vector u<sup>N</sup> i with respect to the elements of u<sup>n</sup> . Using the chain rule of differentiation, 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0015-02.png)


Hence, the sensitivity of the particular output element to all of the elements of the input vector is given by 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0015-04.png)


If one is interested in the sensitivity of NO different output elements, then (A.6) must be evaluated for each one, at a cost which is proportional to NO. Thus the reverse mode is computationally much more efficient than the forward mode when NO ≪ NI. 

Looking in more detail at what is involved in (A.3) and (A.5), suppose that the n<sup>th</sup> step of the original program involves the computation 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0015-07.png)


The corresponding forward mode step will be 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0015-09.png)


at a computational cost which is no more than a factor 3 greater than the original nonlinear calculation. Looking at the structure of (L<sup>n</sup> )<sup>T</sup> , one finds that the corresponding reverse mode step consists of two calculations: 


![](assets/2006-giles-glasserman-smoking-adjoints.pdf-0015-11.png)


At worst, this has a cost which is a factor 4 greater than the original nonlinear calculation. Note however that the reverse mode calculation proceeds backwards from n = N to n =1. Therefore, it is necessary to first perform the original calculation forwards from n =1 to n = N , storing all of the partial derivatives needed for L<sup>n</sup> , before then doing the reverse mode calculation. In some applications, for example in computational fluid dynamics, the storage requirements can be excessive, but in financial Monte Carlo applications the sensitivities are calculated one path at a time, requiring very little storage. 

The above description outlines a clear algorithmic approach to the reverse mode calculation of sensitivity information. However, the programming implementation can be tedious and error-prone. Fortunately, tools have been developed to automate this process, either through operator overloading involving a process known as “taping” which records all of the partial derivatives in the nonlinear calculation then performs the reverse mode calculations [8], or through source code transformation which takes as an input the original program and generates a new program to perform the necessary calculations [6]. Further information about AD tools and publications is available from a website [1] which includes links to all of the major groups working in this field.
