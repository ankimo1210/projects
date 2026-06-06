pub mod regret;
pub mod scalar;
pub mod variant;
pub mod vector;

pub use regret::regret_matching;
pub use scalar::{Game, InfoNode, ScalarCfr};
pub use variant::CfrVariant;
pub use vector::{ExplReport, VectorRiverSolver};
