import type { DskyView } from "./types";

export interface Interpretation {
  program: string;
  action: string;
  registers: string[];
  alerts: string[];
}

const VERBS: Record<string, string> = {
  "05": "8進数で表示",
  "06": "10進数で表示",
  "16": "連続監視表示（値が更新され続ける）",
  "21": "R1 に値をロード",
  "25": "R1–R3 に値をロード",
  "34": "モニタ/表示を終了",
  "35": "ランプテスト（全表示点灯の自己診断）",
  "37": "プログラム (P__) の変更要求",
};

const NOUNS: Record<string, string> = {
  "09": "アラームコード",
  "36": "ミッション時計",
  "65": "サンプル時刻（AGC 時刻のスナップショット）",
};

const REGISTER_HINTS: Record<string, string[]> = {
  "36": ["R1 = 時", "R2 = 分", "R3 = 秒（1/100 秒単位）"],
  "65": ["R1 = 時", "R2 = 分", "R3 = 秒（1/100 秒単位）"],
  "09": ["R1–R3 = アラームコード（8進。1202 はここに出る）"],
};

const PROGRAMS: Record<string, string> = {
  "00": "P00 — アイドル（待機中）",
};

const strip = (s: string) => s.replace(/\s/g, "");

export function interpret(s: DskyView): Interpretation {
  const v = strip(s.verb);
  const n = strip(s.noun);
  const p = strip(s.prog);

  const program =
    p.length === 0
      ? "プログラム表示なし（起動直後）"
      : PROGRAMS[p] ?? `P${p} 実行中`;

  let action: string;
  if (v.length === 0) {
    action = "待機中 — VERB を押すとコマンド入力が始まります";
  } else if (s.verb.trim().length === 1 || (n.length > 0 && s.noun.trim().length === 1)) {
    action = `入力中… 続きの数字を押してください（V${v}${n ? ` N${n}` : ""}）`;
  } else if (v === "35") {
    action = "V35 ランプテスト実行中 — 全表示が 88・ランプ全点灯なら正常（約 5 秒で復帰）";
  } else {
    const verbDesc = VERBS[v] ?? "（この動詞は辞書未登録）";
    const nounDesc = n.length > 0 ? NOUNS[n] ?? "（この名詞は辞書未登録）" : null;
    action = `V${v} ${verbDesc}` + (nounDesc ? ` ／ N${n} ${nounDesc}` : "");
  }

  const registers =
    n.length > 0 && ["05", "06", "16"].includes(v) ? REGISTER_HINTS[n] ?? [] : [];

  const alerts: string[] = [];
  if (!s.connected) alerts.push("サーバ未接続 — ランタイムが起動しているか確認");
  if (s.verbNounFlash) alerts.push("VERB/NOUN 点滅 = AGC が入力を待っています（数字か ENTR を）");
  if (s.oprErr) alerts.push("OPR ERR: 無効な入力です。RSET で消灯してやり直し");
  if (s.keyRel) alerts.push("KEY REL: AGC 側が表示を使いたがっています。KEY REL キーで解放");
  if (s.lamps.comp_acty) alerts.push("COMP ACTY: AGC が計算を実行中");
  if (s.restart) alerts.push("RESTART: AGC が再起動しました（起動直後は正常。RSET で消灯）");
  if (s.temp) alerts.push("TEMP: 温度警告");
  if (s.standby) alerts.push("STBY: スタンバイ状態");

  return { program, action, registers, alerts };
}
