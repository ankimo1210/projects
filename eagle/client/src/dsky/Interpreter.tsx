import type { DskyView } from "./types";
import { interpret } from "./interpret";

export function Interpreter({ state }: { state: DskyView }) {
  const i = interpret(state);
  return (
    <div className="panel">
      <h2>いま何をしている？</h2>
      <div className="interp-program">{i.program}</div>
      <div className="interp-action">{i.action}</div>
      {i.registers.length > 0 && (
        <ul className="interp-registers">
          {i.registers.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      )}
      {i.alerts.length > 0 && (
        <ul className="interp-alerts">
          {i.alerts.map((a) => (
            <li key={a}>{a}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
