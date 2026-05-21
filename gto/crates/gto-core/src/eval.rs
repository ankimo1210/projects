/// Fast 7-card hand evaluator using rank-indexed lookup tables.
///
/// Approach:
///   1. Detect flush via suit bit-counts.
///   2. For flush hands, look up rank pattern in a flush table.
///   3. For non-flush, use prime-product hash (Cactus Kev style) to find
///      the best 5-card rank from rank-only table.
///
/// Returns u16 strength: higher = better (1 = worst high card, 7462 = royal flush).
/// We pre-build tables at program start (const-evaluated where possible).

use std::sync::OnceLock;

// --- Card encoding (compatible with gto-eval) ---
// card = rank*4 + suit,  rank 0=2 .. 12=A,  suit 0=c 1=d 2=h 3=s

pub type Card = u8; // 0..51

#[inline] pub fn rank(c: Card) -> u8 { c / 4 }
#[inline] pub fn suit(c: Card) -> u8 { c % 4 }

// --- Lookup tables ---

struct Tables {
    /// flush_rank_to_val[rank_bits] = hand value (rank_bits = 13-bit mask of ranks present in flush suit)
    flush: Box<[u16; 8192]>,
    /// For non-flush 5-card hands: prime product → hand value
    /// We use a flat array indexed by (product % MOD) with chaining; here we use a simple HashMap.
    unique5: std::collections::HashMap<u32, u16>,
    /// For pairs/trips/quads: rank histogram key → hand value
    nonuniq: std::collections::HashMap<u32, u16>,
}

static TABLES: OnceLock<Tables> = OnceLock::new();

fn get_tables() -> &'static Tables {
    TABLES.get_or_init(build_tables)
}

// Primes for ranks 2..A
const PRIMES: [u32; 13] = [2,3,5,7,11,13,17,19,23,29,31,37,41];

/// Encode a 5-card hand as product of rank-primes (order-independent).
fn prime_product(ranks: &[u8; 5]) -> u32 {
    ranks.iter().map(|&r| PRIMES[r as usize]).product()
}

/// Build rank histogram key for pair/trips/quads hands.
/// Key = sorted (freq, rank) pairs packed into u32.
fn hist_key(ranks: &[u8; 5]) -> u32 {
    let mut freq = [0u8; 13];
    for &r in ranks { freq[r as usize] += 1; }
    let mut groups: Vec<(u8,u8)> = freq.iter().enumerate()
        .filter(|(_,f)| **f>0)
        .map(|(r,&f)| (f, r as u8))
        .collect();
    groups.sort_unstable_by(|a,b| b.cmp(a));
    groups.iter().fold(0u32, |acc, &(f,r)| (acc << 8) | ((f as u32)<<4) | r as u32)
}

fn build_tables() -> Tables {
    let mut flush  = Box::new([0u16; 8192]);
    let mut unique5 = std::collections::HashMap::new();
    let mut nonuniq = std::collections::HashMap::new();

    // Enumerate all C(13,5) = 1287 rank combinations for straights/flushes/high cards
    // and all multi-pair patterns.
    let mut val = 1u16; // lowest = worst

    // Helper: produce sorted rank arrays from combination index
    let ranks_13: Vec<u8> = (0..13).collect();

    // Collect all 5-rank combos
    let mut combos: Vec<[u8;5]> = Vec::with_capacity(2598960);
    for i in 0..13usize {
        for j in (i+1)..13 {
            for k in (j+1)..13 {
                for l in (k+1)..13 {
                    for m in (l+1)..13 {
                        combos.push([ranks_13[i],ranks_13[j],ranks_13[k],ranks_13[l],ranks_13[m]]);
                    }
                }
            }
        }
    }

    // Categorise and sort by hand strength (worst first → ascending val)
    // Category order (worst→best): high card, one pair, two pair, trips, straight, flush, full house, quads, straight flush

    // For unique-rank combos (high card / straight / flush / straight flush):
    fn is_straight(r: &[u8;5]) -> bool {
        // sorted ascending; wheel = A-2-3-4-5
        let top = r[4]; let bot = r[0];
        (top - bot == 4 && r[1]-bot==1 && r[2]-bot==2 && r[3]-bot==3)
        || (r == &[0,1,2,3,12]) // wheel
    }
    fn straight_top(r: &[u8;5]) -> u8 {
        if r == &[0,1,2,3,12] { 3 } else { r[4] } // wheel top = 5 (rank 3)
    }

    // Sort unique combos by strength
    let mut high_cards: Vec<[u8;5]> = Vec::new();
    let mut straights:  Vec<[u8;5]> = Vec::new();
    for c in &combos {
        if is_straight(c) { straights.push(*c); } else { high_cards.push(*c); }
    }
    // Worst high cards first (sort by rank tuple ascending)
    high_cards.sort();
    straights.sort_by_key(|c| straight_top(c));

    // High card (1..1277)
    for c in &high_cards {
        let mask: u16 = c.iter().fold(0u16, |acc,&r| acc|(1<<r));
        let pp = prime_product(c);
        unique5.insert(pp, val);
        flush[mask as usize] = val; // same value for flush = lower category for now (will override)
        val += 1;
    }

    // Pairs/two-pairs/trips/full-house/quads — enumerate via rank histograms
    // We encode all 5-card hands with repeated ranks.
    let mut pair_hands:    Vec<u32> = Vec::new(); // hist_key
    let mut two_pair:      Vec<u32> = Vec::new();
    let mut trips_hands:   Vec<u32> = Vec::new();
    let mut full_house:    Vec<u32> = Vec::new();
    let mut quads_hands:   Vec<u32> = Vec::new();

    for r0 in 0u8..13 {
        for r1 in r0..13 {
            for r2 in r1..13 {
                for r3 in r2..13 {
                    for r4 in r3..13 {
                        let hand = [r0,r1,r2,r3,r4];
                        if hand.iter().collect::<std::collections::HashSet<_>>().len() == 5 { continue; }
                        let key = hist_key(&hand);
                        let freqs = {
                            let mut f=[0u8;13]; for &r in &hand { f[r as usize]+=1; }
                            let mut v:Vec<u8>=f.into_iter().filter(|&x|x>0).collect(); v.sort_unstable_by(|a,b|b.cmp(a)); v
                        };
                        match freqs.as_slice() {
                            [2,1,1,1] => { if !pair_hands.contains(&key) { pair_hands.push(key); } }
                            [2,2,1]   => { if !two_pair.contains(&key)   { two_pair.push(key); } }
                            [3,1,1]   => { if !trips_hands.contains(&key){ trips_hands.push(key); } }
                            [3,2]     => { if !full_house.contains(&key)  { full_house.push(key); } }
                            [4,1]     => { if !quads_hands.contains(&key) { quads_hands.push(key); } }
                            _ => {}
                        }
                    }
                }
            }
        }
    }

    // Assign values in order (worst→best within category)
    // One pair
    pair_hands.sort();
    for k in &pair_hands { nonuniq.entry(*k).or_insert_with(|| { let v=val; val+=1; v }); }
    // Two pair
    two_pair.sort();
    for k in &two_pair  { nonuniq.entry(*k).or_insert_with(|| { let v=val; val+=1; v }); }
    // Trips
    trips_hands.sort();
    for k in &trips_hands { nonuniq.entry(*k).or_insert_with(|| { let v=val; val+=1; v }); }
    // Straight (non-flush)
    for c in &straights { let pp=prime_product(c); unique5.insert(pp, val); val+=1; }
    // Flush
    for c in &high_cards {
        let mask: u16 = c.iter().fold(0u16, |acc,&r| acc|(1<<r));
        flush[mask as usize] = val; val+=1; // override with higher flush value
    }
    // Full house
    full_house.sort();
    for k in &full_house { nonuniq.entry(*k).or_insert_with(|| { let v=val; val+=1; v }); }
    // Quads
    quads_hands.sort();
    for k in &quads_hands { nonuniq.entry(*k).or_insert_with(|| { let v=val; val+=1; v }); }
    // Straight flush
    for c in &straights {
        let mask: u16 = c.iter().fold(0u16, |acc,&r| acc|(1<<r));
        flush[mask as usize] = val; val+=1;
    }

    Tables { flush, unique5, nonuniq }
}

/// Evaluate the best 5-card hand from exactly 7 cards. Returns strength u16 (higher = better).
pub fn evaluate7(cards: &[Card; 7]) -> u16 {
    let t = get_tables();

    // Count suits
    let mut suit_counts = [0u8; 4];
    let mut suit_ranks  = [0u16; 4];
    for &c in cards {
        let s = suit(c) as usize;
        let r = rank(c);
        suit_counts[s] += 1;
        suit_ranks[s] |= 1 << r;
    }

    // Flush check
    for s in 0..4 {
        if suit_counts[s] >= 5 {
            // Find best 5 from flush suit: we already have the rank mask
            // pick highest 5 bits
            let mask = best5_from_flush_mask(suit_ranks[s]);
            return t.flush[mask as usize];
        }
    }

    // Non-flush: try all C(7,5)=21 combos
    let mut best = 0u16;
    for i in 0..7 {
        for j in (i+1)..7 {
            let five: [u8;5] = {
                let mut v = [0u8;5]; let mut idx=0;
                for k in 0..7 { if k!=i && k!=j { v[idx]=rank(cards[k]); idx+=1; } }
                v
            };
            let mut sorted = five; sorted.sort_unstable();
            let v = eval5_nonflush(&sorted, t);
            if v > best { best = v; }
        }
    }
    best
}

fn best5_from_flush_mask(mut mask: u16) -> u16 {
    // Keep only top 5 bits set in mask
    let mut count = mask.count_ones();
    while count > 5 {
        mask &= mask - 1; // clear lowest set bit
        count -= 1;
    }
    mask
}

fn eval5_nonflush(sorted: &[u8;5], t: &Tables) -> u16 {
    // Check unique ranks (no pairs)
    let unique = sorted.iter().collect::<std::collections::HashSet<_>>().len() == 5;
    if unique {
        let pp = prime_product(sorted);
        return *t.unique5.get(&pp).unwrap_or(&0);
    }
    let key = hist_key(sorted);
    *t.nonuniq.get(&key).unwrap_or(&0)
}

/// Convenience: parse card string and evaluate
pub fn parse_card(s: &str) -> Option<Card> {
    crate::card::Card::from_str(s).map(|c| c.0)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn royal_beats_straight_flush() {
        let royal: [Card;7] = [
            parse_card("As").unwrap(), parse_card("Ks").unwrap(),
            parse_card("Qs").unwrap(), parse_card("Js").unwrap(),
            parse_card("Ts").unwrap(), parse_card("2c").unwrap(),
            parse_card("3d").unwrap(),
        ];
        let sf: [Card;7] = [
            parse_card("9s").unwrap(), parse_card("8s").unwrap(),
            parse_card("7s").unwrap(), parse_card("6s").unwrap(),
            parse_card("5s").unwrap(), parse_card("2c").unwrap(),
            parse_card("3d").unwrap(),
        ];
        assert!(evaluate7(&royal) > evaluate7(&sf));
    }

    #[test]
    fn quads_beat_full_house() {
        let quads: [Card;7] = [
            parse_card("Ah").unwrap(), parse_card("As").unwrap(),
            parse_card("Ad").unwrap(), parse_card("Ac").unwrap(),
            parse_card("2h").unwrap(), parse_card("3d").unwrap(),
            parse_card("4c").unwrap(),
        ];
        let fh: [Card;7] = [
            parse_card("Kh").unwrap(), parse_card("Ks").unwrap(),
            parse_card("Kd").unwrap(), parse_card("Qh").unwrap(),
            parse_card("Qs").unwrap(), parse_card("2d").unwrap(),
            parse_card("3c").unwrap(),
        ];
        assert!(evaluate7(&quads) > evaluate7(&fh));
    }
}
