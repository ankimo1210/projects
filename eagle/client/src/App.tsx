import { CheatSheet } from "./dsky/CheatSheet";
import { Dsky } from "./dsky/Dsky";
import { Interpreter } from "./dsky/Interpreter";
import { useDskySocket } from "./dsky/useDskySocket";
import "./App.css";

function App() {
  const [state, sendKey, sendPro] = useDskySocket();
  return (
    <div className="page">
      <Dsky state={state} sendKey={sendKey} sendPro={sendPro} />
      <div className="side">
        <Interpreter state={state} />
        <CheatSheet />
      </div>
    </div>
  );
}

export default App;
