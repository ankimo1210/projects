export interface SimRequest {
  position:   string;
  board?:     string[];
  iterations?: number;
}

export interface ActionFreq {
  action: string;
  freq:   number;
}

export interface BBHand {
  hand:          string;
  call_freq:     number;
  fold_freq:     number;
  threebet_freq: number;
}

export interface PostflopResult {
  strategy:       ActionFreq[];
  exploitability: number;
  backend:        string;
  iterations:     number;
}

export interface SimResponse {
  position:      string;
  fold_equity:   number;
  call_freq:     number;
  threebet_freq: number;
  bb_hands:      BBHand[];
  postflop:      PostflopResult | null;
}

export async function runSimulation(req: SimRequest): Promise<SimResponse> {
  const res = await fetch("/api/simulation/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      position:   req.position,
      board:      req.board ?? [],
      iterations: req.iterations ?? 300,
    }),
  });
  if (!res.ok) throw new Error(await res.text().catch(() => res.statusText));
  return res.json();
}
