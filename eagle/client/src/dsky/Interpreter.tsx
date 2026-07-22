import type { DskyView } from "./types";
import { interpretStable } from "./interpret";
import { useInterpretLog } from "./useInterpretLog";

export function Interpreter({ state }: { state: DskyView }) {
  const { entries, flashing, computing, oprErr, keyRel } = useInterpretLog(state);
  const stable = interpretStable(state);
  return (
    <div className="panel">
      <h2>いま何をしている？</h2>
      <div className="interp-program">{stable.program}</div>
      <div className="interp-action">{stable.action}</div>
      {stable.registers.length > 0 && (
        <ul className="interp-registers">
          {stable.registers.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      )}
      <div className="interp-chips">
        {flashing && <span className="chip">入力待ち</span>}
        {computing && <span className="chip">計算中</span>}
        {oprErr && <span className="chip chip-warn">OPR ERR → RSET で消灯</span>}
        {keyRel && <span className="chip chip-warn">KEY REL 要求</span>}
      </div>
      <div className="interp-log">
        {entries.length === 0 && (
          <div className="log-line log-empty">操作するとここに履歴が溜まります</div>
        )}
        {entries.map((e) => (
          <div key={e.id} className={`log-line log-${e.kind}`}>
            <span className="log-time">{e.time}</span> {e.text}
          </div>
        ))}
      </div>
    </div>
  );
}
