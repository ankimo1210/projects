# Independent Heston homogeneity formula audit

Reviewer: /root/task5_replay_review/homogeneity_audit. Source read only; no experiment/source/Git/docs edits.

Fixed current Heston variance v, calendar, fixing times, currency memory A and original IID normals imply S_j=S R_j. Normalized model primitives and auxiliary GBM variance/path/known law are independent of S.

Each path g_i(x)=X_i^CE(x)-Y_i^CE(x)+mu_Y(x), Vhat=D*S*mean(g_i(x))/12, x=(1200-A)/S gives VS_hat=D*(mean(g)-x*mean(g_x))/12 path/block wise.

Conditions: fix A and v; no spot-dependent correction; differentiate the same price curve; preserve atom/invalid/underresolved qualification. This is fixed-v Delta. Fixed-Q holding hS=VS-CS*hQ.

primitive_labels: raw_x=-indicator(b+c*exp(mu+sigma*z)>x), CE derivative=conditional_tail f_x, CV derivative=CE f_x-aux CE f_x+known f_x (435). derivative_samples order raw/conditioned/CV. f_x_samples is CV. Auxiliary conditioned f_x is not exported directly; reconstruct prefix/loading. aux_raw_samples is not this conditional CV Greek subtraction term.

Same-block Var(VS)=(D/12)^2[Var(f)+x^2 Var(f_x)-2x Cov(f,f_x)]. joint_block_covariance preserves this correlation.

unknown_underresolved keeps finite f/f_x and cannot qualify teacher from zero empirical SE. Under-observed tails, underflow and identical samples differ from analytic/deterministic/linear/settled branches.

hQ=V_current_variance/C_current_variance remains unresolved by homogeneity. Current variance differs from Heston parameters.theta (long-term mean). Both state bumps must change model CE, auxiliary CE and analytic mean. Numerator/control and bump covariance are required. Deterministic solver denominator numerical error remains separate from MC covariance; a small denominator can invalidate linearized propagation. Local homogeneity is forbidden.
