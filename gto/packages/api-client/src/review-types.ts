// Wire types for POST /api/review/parse — mirror src/gto/api/routers/review.py
// (ported from web/lib/review-api.ts; web keeps its own copy until the v1.x
// refresh consumes this package).

export interface Stakes {
  small_blind: number;
  big_blind: number;
  currency: string;
}

export interface Player {
  seat: number;
  name: string;
  stack: number;
  sitting_out: boolean;
}

export interface BlindPost {
  player: string;
  blind_type: "small" | "big" | "small_and_big" | "ante";
  amount: number;
}

export interface HandAction {
  street: string;
  actor: string;
  action: "fold" | "check" | "call" | "bet" | "raise";
  amount: number | null;
  raise_to: number | null;
  all_in: boolean;
}

export interface StreetActions {
  preflop: HandAction[];
  flop: HandAction[];
  turn: HandAction[];
  river: HandAction[];
}

export interface ShowdownEntry {
  player: string;
  cards: [string, string] | null;
  mucked: boolean;
  description: string | null;
}

export interface UncalledBet {
  player: string;
  amount: number;
}

export interface Winner {
  player: string;
  amount: number;
  pot: string; // "pot" | "main pot" | "side pot(-N)"
}

export interface DeviationFlag {
  flag: "ok" | "loose" | "tight" | "missing_data";
  hand: string | null;
  spot_type: "RFI" | "FACING" | null;
  position: string | null;
  hero_action: "R" | "3B" | "C" | "F" | null;
  gto_action: "R" | "3B" | "C" | "F" | null;
  gto_frequencies: Record<string, number>; // 0-100 percent scale
  ev_loss: number | null;
  reason: string | null;
}

export interface ParsedHand {
  hand_id: string;
  stakes: Stakes;
  played_at: string | null;
  timezone: string | null;
  table_name: string;
  max_players: number | null;
  button_seat: number;
  players: Player[];
  hero_name: string | null;
  hero_cards: [string, string] | null;
  posts: BlindPost[];
  actions: StreetActions;
  board: string[];
  showdown: ShowdownEntry[];
  uncalled_bets: UncalledBet[];
  winners: Winner[];
  total_pot: number | null;
  rake: number | null;
  zoom: boolean;
  positions: Record<string, string>;
  preflop_deviation: DeviationFlag | null;
}

export interface ParseError {
  index: number;
  message: string;
  snippet: string;
}

export interface ParseResponse {
  hands: ParsedHand[];
  errors: ParseError[];
}
