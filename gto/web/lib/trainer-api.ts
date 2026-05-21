export interface Quiz {
  hand: string;
  description: string;
  spot_type: string;
  position: string;
}

export interface ActionFreq {
  action: string;
  freq: number;
}

export interface AnswerResult {
  correct: boolean;
  chosen: string;
  gto_action: string;
  gto_freq: number;
  all_actions: ActionFreq[];
  ev_loss: number;
  hand: string;
  description: string;
}

const BASE = "";

export async function fetchQuiz(): Promise<Quiz> {
  const res = await fetch(`${BASE}/api/trainer/quiz`);
  if (!res.ok) throw new Error("quiz fetch failed");
  return res.json();
}

export async function submitAnswer(quiz: Quiz, chosen: string): Promise<AnswerResult> {
  const res = await fetch(`${BASE}/api/trainer/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      hand:      quiz.hand,
      position:  quiz.position,
      spot_type: quiz.spot_type,
      chosen,
    }),
  });
  if (!res.ok) throw new Error("answer submit failed");
  return res.json();
}
