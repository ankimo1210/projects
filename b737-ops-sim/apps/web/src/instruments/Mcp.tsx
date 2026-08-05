import { normalizeDeg360, type AircraftState } from '@b737/shared';
import { audioEngine } from '../audio/audioEngine.js';
import { sendCommand } from '../state/connection.js';

/**
 * Mode Control Panel (spec §7). Windows show BACKEND state; knob clicks send
 * commands — the display never moves on its own (spec §7 pending rule: the
 * value updates when the state stream reflects it).
 */
export function Mcp({ state }: { state: AircraftState }): JSX.Element {
  const mcp = state.mcp;

  const adjust = (kind: 'speed' | 'heading' | 'altitude' | 'vs', delta: number): void => {
    audioEngine.click('rotary');
    switch (kind) {
      case 'speed':
        sendCommand({
          type: 'set_mcp_speed',
          speedKt: clampRange(mcp.selSpeedKt + delta, 100, 340),
        });
        break;
      case 'heading':
        sendCommand({
          type: 'set_mcp_heading',
          headingDeg: normalizeDeg360(mcp.selHeadingDeg + delta),
        });
        break;
      case 'altitude':
        sendCommand({
          type: 'set_mcp_altitude',
          altitudeFt: clampRange(mcp.selAltitudeFt + delta, 0, 41000),
        });
        break;
      case 'vs':
        sendCommand({
          type: 'set_mcp_vertical_speed',
          verticalSpeedFpm: clampRange(mcp.selVerticalSpeedFpm + delta, -8000, 8000),
        });
        break;
    }
  };

  return (
    <div className="mcp" data-testid="mcp" data-control-id="mcp">
      <McpWindow
        label="IAS"
        value={String(Math.round(mcp.selSpeedKt))}
        onDelta={(d, big) => adjust('speed', d * (big ? 10 : 1))}
      />
      <McpWindow
        label="HDG"
        value={String(Math.round(mcp.selHeadingDeg)).padStart(3, '0')}
        onDelta={(d, big) => adjust('heading', d * (big ? 10 : 1))}
      />
      <McpWindow
        label="ALT"
        value={String(Math.round(mcp.selAltitudeFt))}
        onDelta={(d, big) => adjust('altitude', d * (big ? 1000 : 100))}
      />
      <McpWindow
        label="V/S"
        value={String(Math.round(mcp.selVerticalSpeedFpm))}
        onDelta={(d, big) => adjust('vs', d * (big ? 500 : 100))}
      />
      <button
        type="button"
        className={`mcp-btn ${mcp.autopilotEngaged ? 'lit' : ''}`}
        data-testid="mcp-ap"
        onClick={() => {
          audioEngine.click();
          sendCommand({ type: 'set_autopilot', engaged: !mcp.autopilotEngaged });
        }}
      >
        CMD A
      </button>
      <button
        type="button"
        className={`mcp-btn ${mcp.flightDirectorOn ? 'lit' : ''}`}
        onClick={() => {
          audioEngine.click();
          sendCommand({ type: 'set_flight_director', on: !mcp.flightDirectorOn });
        }}
      >
        F/D
      </button>
    </div>
  );
}

function McpWindow({
  label,
  value,
  onDelta,
}: {
  label: string;
  value: string;
  onDelta: (direction: 1 | -1, big: boolean) => void;
}): JSX.Element {
  return (
    <div
      className="mcp-window"
      onWheel={(e) => {
        e.preventDefault();
        onDelta(e.deltaY < 0 ? 1 : -1, e.shiftKey);
      }}
    >
      <span className="mcp-label">{label}</span>
      <span className="mcp-value" data-testid={`mcp-${label.toLowerCase().replace('/', '')}`}>
        {value}
      </span>
      <span className="mcp-knob">
        <button
          type="button"
          onClick={(e) => onDelta(-1, e.shiftKey)}
          aria-label={`${label} decrease`}
        >
          −
        </button>
        <button
          type="button"
          onClick={(e) => onDelta(1, e.shiftKey)}
          aria-label={`${label} increase`}
        >
          +
        </button>
      </span>
    </div>
  );
}

function clampRange(v: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, v));
}
