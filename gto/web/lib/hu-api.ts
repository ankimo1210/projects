// Client for the gto-hu exact river equilibrium endpoint (/api/hu/river).
// Unlike /solver (gto-cuda single-street approximation), this returns an
// EXACT exploitability number — the differentiator surfaced in the UI.

export interface HuRiverRequest {
  board: string[]; // exactly 5 cards
  pot_bb: number;
  effective_stack_bb: number;
  iterations: number;
}

export interface ActionFreq {
  action: string;
  freq: number;
}

export interface ComboStrategy {
  card_a: string;
  card_b: string;
  freqs: number[]; // aligned with HuRiverResponse.actions
}

export interface HuRiverResponse {
  strategy: ActionFreq[];
  actions: string[];
  exploitability: number;
  br_sb: number;
  br_bb: number;
  game_value_sb: number;
  iterations: number;
  elapsed_secs: number;
  combos: ComboStrategy[];
}

export async function solveHuRiver(req: HuRiverRequest): Promise<HuRiverResponse> {
  const res = await fetch("/api/hu/river", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.text().catch(() => res.statusText);
    throw new Error(err);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// 169-class aggregation for the range heatmap
// ---------------------------------------------------------------------------

const RANK_ORDER = "AKQJT98765432"; // index 0 = A (highest)
const RANK_OF: Record<string, number> = Object.fromEntries(
  RANK_ORDER.split("").map((r, i) => [r, i]),
);

/** Row/col (0-12, A-high) and "s"/"o"/"p" type for a 169 grid cell. */
export function comboCell(card_a: string, card_b: string): { row: number; col: number } {
  const ra = RANK_OF[card_a[0]];
  const rb = RANK_OF[card_b[0]];
  const suited = card_a[1] === card_b[1];
  const [hi, lo] = ra <= rb ? [ra, rb] : [rb, ra]; // hi = higher rank (smaller index)
  if (ra === rb) return { row: hi, col: lo }; // pair: diagonal
  // suited above the diagonal (row=hi, col=lo); offsuit below (row=lo, col=hi)
  return suited ? { row: hi, col: lo } : { row: lo, col: hi };
}

/**
 * Aggregate per-combo strategies into a 13×13 grid of the range-weighted
 * frequency of a chosen action set (default: aggressive = everything but
 * the first action, which is always "check"). Cells with no combos are null.
 */
export function aggressiveGrid(resp: HuRiverResponse): (number | null)[][] {
  const sum: number[][] = Array.from({ length: 13 }, () => Array(13).fill(0));
  const cnt: number[][] = Array.from({ length: 13 }, () => Array(13).fill(0));
  for (const c of resp.combos) {
    const { row, col } = comboCell(c.card_a, c.card_b);
    const aggressive = c.freqs.slice(1).reduce((a, b) => a + b, 0); // 1 - check
    sum[row][col] += aggressive;
    cnt[row][col] += 1;
  }
  return sum.map((r, i) => r.map((v, j) => (cnt[i][j] > 0 ? v / cnt[i][j] : null)));
}

export const RANK_LABELS = RANK_ORDER.split("");
