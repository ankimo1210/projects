//! SplitMix64 — tiny deterministic RNG for public chance sampling.
//! Dependency-free; the sequence for a given seed is part of the test
//! contract (sampled runs must be reproducible).

pub struct SplitMix64(u64);

impl SplitMix64 {
    pub fn new(seed: u64) -> Self {
        SplitMix64(seed)
    }

    pub fn next_u64(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.0;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }

    /// Uniform index in `0..n`. Modulo bias is < n/2^64 — negligible for
    /// n ≤ 52.
    pub fn next_index(&mut self, n: usize) -> usize {
        (self.next_u64() % n as u64) as usize
    }
}

#[cfg(test)]
mod tests {
    use super::SplitMix64;

    #[test]
    fn same_seed_same_sequence() {
        let mut a = SplitMix64::new(42);
        let mut b = SplitMix64::new(42);
        for _ in 0..100 {
            assert_eq!(a.next_u64(), b.next_u64());
        }
        let mut c = SplitMix64::new(43);
        let same = (0..100).all(|_| SplitMix64::new(42).next_u64() == c.next_u64());
        assert!(!same, "different seeds must diverge");
    }

    #[test]
    fn next_index_in_range() {
        let mut r = SplitMix64::new(7);
        for _ in 0..1000 {
            assert!(r.next_index(48) < 48);
        }
    }

    #[test]
    fn matches_reference_test_vector() {
        // Known-answer test pinning the canonical SplitMix64 constants
        // (Steele/Lea/Flood; first output for seed 0).
        let mut r = SplitMix64::new(0);
        assert_eq!(r.next_u64(), 0xE220_A839_7B1D_CDAF);
    }
}
