import { useState } from "react";
import { CheatSheet } from "./dsky/CheatSheet";
import { Dsky } from "./dsky/Dsky";
import { Interpreter } from "./dsky/Interpreter";
import { useDskySocket } from "./dsky/useDskySocket";
import { TelemetryPage } from "./telemetry/TelemetryPage";
import { useTelemetryBuffer } from "./telemetry/useTelemetryBuffer";
import "./App.css";

function App() {
  const [tab, setTab] = useState<"dsky" | "engr">("dsky");
  const buffer = useTelemetryBuffer();
  const { state, sendKey, sendPro, sendRod } = useDskySocket(buffer.push);

  return (
    <div className="app">
      <nav className="tabs">
        <button
          className={tab === "dsky" ? "active" : ""}
          onClick={() => setTab("dsky")}
        >
          DSKY
        </button>
        <button
          className={tab === "engr" ? "active" : ""}
          onClick={() => setTab("engr")}
        >
          ENGR
        </button>
      </nav>

      {tab === "dsky" ? (
        <div className="page">
          <Dsky state={state} sendKey={sendKey} sendPro={sendPro} />
          <div className="side">
            <Interpreter state={state} />
            <CheatSheet />
          </div>
        </div>
      ) : (
        <TelemetryPage buffer={buffer} sendRod={sendRod} />
      )}
    </div>
  );
}

export default App;
