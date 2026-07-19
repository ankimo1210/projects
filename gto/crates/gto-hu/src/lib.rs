//! # gto-hu — Abstract HU NLHE equilibrium solver
//!
//! **This is an abstract HU NLHE equilibrium solver, not an unabstracted
//! full GTO solver.** Fixed action abstraction, explicit card abstraction
//! levels, exploitability is always reported alongside strategies.

pub mod bench;
pub mod game;
pub mod games;
pub mod ranges;
pub mod reports;
pub mod solver;
pub mod tree;
pub mod validation;
