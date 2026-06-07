pub mod regret;
pub mod rng;
pub mod scalar;
pub mod showdown;
pub mod variant;
pub mod vector;

pub use regret::regret_matching;
pub use scalar::{Game, InfoNode, ScalarCfr};
pub use showdown::{weighted_compat, ShowdownTable};
pub use variant::CfrVariant;
pub use vector::{ExplReport, VectorRiverSolver};
