pub mod regret;
pub mod scalar;
pub mod variant;

pub use regret::regret_matching;
pub use scalar::{Game, InfoNode, ScalarCfr};
pub use variant::CfrVariant;
