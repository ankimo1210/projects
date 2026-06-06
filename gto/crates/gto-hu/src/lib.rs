//! # gto-hu — Abstract HU NLHE equilibrium solver
//!
//! **This is an abstract HU NLHE equilibrium solver, not an unabstracted
//! full GTO solver.** Fixed action abstraction, explicit card abstraction
//! levels, exploitability is always reported alongside strategies.

pub mod game;
pub mod ranges;
pub mod tree;
pub mod solver;
pub mod games;
pub mod validation;
pub mod reports;
