/// Card rank: 2=0 .. A=12
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct Rank(pub u8);

/// Card suit: Clubs=0, Diamonds=1, Hearts=2, Spades=3
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct Suit(pub u8);

/// A single card encoded as rank*4 + suit (0..51)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct Card(pub u8);

impl Card {
    pub fn new(rank: u8, suit: u8) -> Self {
        Card(rank * 4 + suit)
    }

    pub fn rank(self) -> Rank {
        Rank(self.0 / 4)
    }

    pub fn suit(self) -> Suit {
        Suit(self.0 % 4)
    }

    /// Parse a card string like "Ah", "2c", "Td", "Ks"
    pub fn from_str(s: &str) -> Option<Self> {
        let mut chars = s.chars();
        let r = chars.next()?;
        let s = chars.next()?;
        let rank = match r {
            '2' => 0, '3' => 1, '4' => 2, '5' => 3, '6' => 4,
            '7' => 5, '8' => 6, '9' => 7, 'T' | 't' => 8,
            'J' | 'j' => 9, 'Q' | 'q' => 10, 'K' | 'k' => 11,
            'A' | 'a' => 12,
            _ => return None,
        };
        let suit = match s {
            'c' | 'C' => 0,
            'd' | 'D' => 1,
            'h' | 'H' => 2,
            's' | 'S' => 3,
            _ => return None,
        };
        Some(Card::new(rank, suit))
    }

    pub fn to_display(self) -> String {
        let ranks = ['2','3','4','5','6','7','8','9','T','J','Q','K','A'];
        let suits = ['c','d','h','s'];
        format!("{}{}", ranks[self.rank().0 as usize], suits[self.suit().0 as usize])
    }
}

/// Full 52-card deck
pub fn full_deck() -> Vec<Card> {
    (0..52).map(Card).collect()
}

/// Hand strength categories (higher is better)
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum HandRank {
    HighCard = 0,
    OnePair = 1,
    TwoPair = 2,
    ThreeOfAKind = 3,
    Straight = 4,
    Flush = 5,
    FullHouse = 6,
    FourOfAKind = 7,
    StraightFlush = 8,
}

/// Evaluate the best 5-card hand from 5-7 cards.
/// Returns (HandRank, u32 tiebreaker) where higher tiebreaker wins within the same rank.
pub fn evaluate(cards: &[Card]) -> (HandRank, u32) {
    debug_assert!(cards.len() >= 5 && cards.len() <= 7);
    if cards.len() == 5 {
        eval5(cards)
    } else {
        best_of_combinations(cards)
    }
}

fn best_of_combinations(cards: &[Card]) -> (HandRank, u32) {
    let n = cards.len();
    let mut best = (HandRank::HighCard, 0u32);
    for i in 0..n {
        for j in (i + 1)..n {
            let five: Vec<Card> = cards.iter()
                .enumerate()
                .filter(|&(k, _)| k != i && k != j)
                .map(|(_, &c)| c)
                .collect();
            let result = eval5(&five);
            if result > best {
                best = result;
            }
        }
    }
    best
}

fn eval5(cards: &[Card]) -> (HandRank, u32) {
    let mut ranks: Vec<u8> = cards.iter().map(|c| c.rank().0).collect();
    let suits: Vec<u8> = cards.iter().map(|c| c.suit().0).collect();
    ranks.sort_unstable_by(|a, b| b.cmp(a));

    let is_flush = suits.iter().all(|&s| s == suits[0]);

    let is_straight_top: Option<u8> = {
        let normal = ranks.windows(2).all(|w| w[0] == w[1] + 1);
        let wheel = ranks == [12, 3, 2, 1, 0];
        if normal { Some(ranks[0]) } else if wheel { Some(3) } else { None }
    };

    if is_flush && is_straight_top.is_some() {
        return (HandRank::StraightFlush, is_straight_top.unwrap() as u32);
    }

    let mut freq = [0u8; 13];
    for &r in &ranks {
        freq[r as usize] += 1;
    }
    let mut groups: Vec<(u8, u8)> = freq.iter()
        .enumerate()
        .filter(|&(_, &f)| f > 0)
        .map(|(r, &f)| (f, r as u8))
        .collect();
    groups.sort_unstable_by(|a, b| b.cmp(a));

    let tiebreak = |g: &[(u8, u8)]| -> u32 {
        g.iter().fold(0u32, |acc, &(f, r)| (acc << 8) | ((f as u32) << 4) | r as u32)
    };

    if groups[0].0 == 4 {
        return (HandRank::FourOfAKind, tiebreak(&groups));
    }
    if groups[0].0 == 3 && groups[1].0 == 2 {
        return (HandRank::FullHouse, tiebreak(&groups));
    }
    if is_flush {
        let tb = ranks.iter().fold(0u32, |acc, &r| (acc << 4) | r as u32);
        return (HandRank::Flush, tb);
    }
    if let Some(top) = is_straight_top {
        return (HandRank::Straight, top as u32);
    }
    if groups[0].0 == 3 {
        return (HandRank::ThreeOfAKind, tiebreak(&groups));
    }
    if groups[0].0 == 2 && groups[1].0 == 2 {
        return (HandRank::TwoPair, tiebreak(&groups));
    }
    if groups[0].0 == 2 {
        return (HandRank::OnePair, tiebreak(&groups));
    }
    let tb = ranks.iter().fold(0u32, |acc, &r| (acc << 4) | r as u32);
    (HandRank::HighCard, tb)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_card_parse() {
        let c = Card::from_str("Ah").unwrap();
        assert_eq!(c.rank().0, 12);
        assert_eq!(c.suit().0, 2);
    }

    #[test]
    fn test_royal_flush() {
        let cards: Vec<Card> = ["As","Ks","Qs","Js","Ts"]
            .iter().map(|s| Card::from_str(s).unwrap()).collect();
        let (rank, _) = evaluate(&cards);
        assert_eq!(rank, HandRank::StraightFlush);
    }

    #[test]
    fn test_full_house_beats_flush() {
        let fh: Vec<Card> = ["Ah","As","Ad","Kh","Kd"]
            .iter().map(|s| Card::from_str(s).unwrap()).collect();
        let fl: Vec<Card> = ["2h","4h","6h","8h","Th"]
            .iter().map(|s| Card::from_str(s).unwrap()).collect();
        assert!(evaluate(&fh) > evaluate(&fl));
    }

    #[test]
    fn test_wheel_straight() {
        let cards: Vec<Card> = ["Ac","2d","3h","4s","5c"]
            .iter().map(|s| Card::from_str(s).unwrap()).collect();
        let (rank, _) = evaluate(&cards);
        assert_eq!(rank, HandRank::Straight);
    }
}
