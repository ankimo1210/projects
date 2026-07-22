import { useDskySocket } from "./useDskySocket";
import "./dsky.css";

const KEYS: [label: string, name: string][] = [
  ["VERB", "VERB"], ["NOUN", "NOUN"], ["+", "PLUS"], ["-", "MINUS"],
  ["0", "0"], ["1", "1"], ["2", "2"], ["3", "3"], ["4", "4"],
  ["5", "5"], ["6", "6"], ["7", "7"], ["8", "8"], ["9", "9"],
  ["CLR", "CLR"], ["PRO", "PRO"], ["KEY REL", "KEY_REL"],
  ["ENTR", "ENTR"], ["RSET", "RSET"],
];

const LAMPS: [label: string, key: string][] = [
  ["UPLINK ACTY", "uplink_acty"], ["NO ATT", "no_att"], ["TEMP", "__temp"],
  ["GIMBAL LOCK", "gimbal_lock"], ["PROG", "prog"], ["TRACKER", "tracker"],
  ["ALT", "alt"], ["VEL", "vel"], ["STBY", "__standby"],
  ["KEY REL", "__key_rel"], ["OPR ERR", "__opr_err"], ["RESTART", "__restart"],
];

export function Dsky() {
  const [s, sendKey, sendPro] = useDskySocket();
  const lampOn = (key: string) =>
    key === "__temp" ? s.temp : key === "__standby" ? s.standby :
    key === "__key_rel" ? s.keyRel : key === "__opr_err" ? s.oprErr :
    key === "__restart" ? s.restart : !!s.lamps[key];

  return (
    <div className="dsky">
      <div className="dsky-status">{s.connected ? "CONNECTED" : "NO LINK"}</div>
      <div className="dsky-lamps">
        {LAMPS.map(([label, key]) => (
          <div key={label} className={`lamp ${lampOn(key) ? "on" : ""}`}>{label}</div>
        ))}
      </div>
      <div className="dsky-display">
        <div className="disp-cell"><label>PROG</label><span>{s.prog}</span></div>
        <div className={`disp-cell ${s.verbNounFlash ? "flash" : ""}`}>
          <label>VERB</label><span>{s.verb}</span>
        </div>
        <div className={`disp-cell ${s.verbNounFlash ? "flash" : ""}`}>
          <label>NOUN</label><span>{s.noun}</span>
        </div>
        <div className="disp-reg">{s.r1}</div>
        <div className="disp-reg">{s.r2}</div>
        <div className="disp-reg">{s.r3}</div>
      </div>
      <div className="dsky-keys">
        {KEYS.map(([label, name]) =>
          name === "PRO" ? (
            <button key={name} className="key"
              onMouseDown={() => sendPro(true)} onMouseUp={() => sendPro(false)}>
              {label}
            </button>
          ) : (
            <button key={name} className="key" onClick={() => sendKey(name)}>
              {label}
            </button>
          ))}
      </div>
    </div>
  );
}
