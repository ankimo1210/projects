"""la_book — shared helpers for the linear algebra notebook textbook."""

from .algebra import (
    conjugate_gradient,
    gauss_seidel,
    gradient_descent_quadratic,
    gram_schmidt,
    jacobi,
    least_squares,
    markov_stationary,
    newton_method,
    page_rank,
    power_iteration,
    project_onto,
    projection_matrix,
    rank,
    ridge,
    rref,
)
from .decompositions import (
    PCAResult,
    cholesky,
    compression_ratio,
    lowrank_errors,
    lu,
    pca_fit,
    qr,
    svd_lowrank,
    whiten,
)

__version__ = "0.1.0"
