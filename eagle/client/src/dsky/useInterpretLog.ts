import { useEffect, useRef, useState } from "react";
import type { DskyView } from "./types";
import { interpretStable, stableKey } from "./interpret";

export interface LogEntry {
  id: number;
  time: string;
  text: string;
  kind: "action" | "alert";
}

const DECAY_MS = 2000;
const MAX_ENTRIES = 200;

/// Debounce an oscillating flag: turns on immediately, turns off only after
/// the raw flag has stayed false for DECAY_MS (longer than the DSKY's 1.28 s
/// blink cycle), so blinking reads as continuously "active".
function useDecayed(raw: boolean, ms = DECAY_MS): boolean {
  const [active, setActive] = useState(false);
  const timer = useRef<number | null>(null);
  useEffect(() => {
    if (raw) {
      if (timer.current !== null) {
        clearTimeout(timer.current);
        timer.current = null;
      }
      setActive(true);
    } else if (active && timer.current === null) {
      timer.current = window.setTimeout(() => {
        timer.current = null;
        setActive(false);
      }, ms);
    }
  }, [raw, active, ms]);
  useEffect(
    () => () => {
      if (timer.current !== null) clearTimeout(timer.current);
    },
    [],
  );
  return active;
}

function now(): string {
  return new Date().toLocaleTimeString("ja-JP", { hour12: false });
}

export interface InterpretLog {
  entries: LogEntry[];
  flashing: boolean;
  computing: boolean;
  oprErr: boolean;
  keyRel: boolean;
}

export function useInterpretLog(s: DskyView): InterpretLog {
  const [entries, setEntries] = useState<LogEntry[]>([]);
  const nextId = useRef(1);

  const push = (text: string, kind: LogEntry["kind"]) =>
    setEntries((e) =>
      [{ id: nextId.current++, time: now(), text, kind }, ...e].slice(0, MAX_ENTRIES),
    );

  // Blink-invariant "what is happening" line: log only on real changes.
  const stable = interpretStable(s);
  const key = stableKey(stable);
  const prevKey = useRef<string>("");
  useEffect(() => {
    if (key === prevKey.current) return;
    prevKey.current = key;
    const regs = stable.registers.length > 0 ? `（${stable.registers.join("、")}）` : "";
    push(`${stable.action}${regs}`, "action");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  // Debounced oscillating indicators: shown as steady chips, and only their
  // onset/offset (not each blink) becomes a log line.
  const flashing = useDecayed(s.verbNounFlash);
  const oprErr = useDecayed(s.oprErr);
  const keyRel = useDecayed(s.keyRel);
  const computing = useDecayed(!!s.lamps.comp_acty, 500); // chip only, never logged

  useTransitionLog(flashing, push, "AGC が入力待ち（VERB/NOUN 点滅）", "入力が確定（点滅停止）");
  useTransitionLog(oprErr, push, "OPR ERR 点灯 — 無効な入力。RSET で消灯", "OPR ERR 消灯");
  useTransitionLog(keyRel, push, "KEY REL 点灯 — AGC が表示を要求。KEY REL キーで解放", "KEY REL 消灯");

  // Rare steady flags: log transitions directly.
  useTransitionLog(s.restart, push, "RESTART 点灯 — AGC が再起動（起動直後は正常。RSET で消灯）", "RESTART 消灯");
  useTransitionLog(s.standby, push, "STBY — スタンバイ状態", "STBY 解除");
  useTransitionLog(s.temp, push, "TEMP 点灯 — 温度警告", "TEMP 消灯");
  useTransitionLog(!s.connected, push, "サーバとの接続が切れました", "サーバに接続しました");

  return { entries, flashing, computing, oprErr, keyRel };
}

function useTransitionLog(
  flag: boolean,
  push: (text: string, kind: LogEntry["kind"]) => void,
  onText: string,
  offText: string,
) {
  const prev = useRef<boolean | null>(null);
  useEffect(() => {
    if (prev.current === null) {
      // Initial render: log only if the flag starts raised.
      prev.current = flag;
      if (flag) push(onText, "alert");
      return;
    }
    if (flag !== prev.current) {
      prev.current = flag;
      push(flag ? onText : offText, "alert");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [flag]);
}
