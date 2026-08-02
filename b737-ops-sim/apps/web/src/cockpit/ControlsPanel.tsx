import { FLAP_DETENTS, type AircraftState, type AutobrakeSetting, type FlapDetent } from '@b737/shared';
import { COCKPIT_CONTROLS } from '@b737/cockpit-model';
import { audioEngine } from '../audio/audioEngine.js';
import { inputManager } from '../input/inputManager.js';
import { sendCommand } from '../state/connection.js';
import { useSettingsStore } from '../state/stores.js';

/**
 * Pedestal / gear panel bound through the cockpit control registry (spec §9):
 * every control displays BACKEND state and sends typed commands; nothing here
 * owns aircraft state. `guidedControlId` pulses the next relevant control.
 */

const AUTOBRAKE_ORDER: AutobrakeSetting[] = ['RTO', 'OFF', '1', '2', '3', 'MAX'];

export function ControlsPanel({
  state,
  guidedControlId,
}: {
  state: AircraftState;
  guidedControlId: string | null;
}): JSX.Element {
  const mode = useSettingsStore((s) => s.mode);
  const showHints = mode === 'guided';
  const cls = (id: string): string =>
    `ctl ${guidedControlId === id && showHints ? 'ctl-guided' : ''}`;
  const hint = (id: string): string | undefined =>
    showHints ? COCKPIT_CONTROLS.find((c) => c.id === id)?.trainingHint : undefined;

  return (
    <div className="controls-panel" data-testid="controls-panel">
      {/* Thrust + reverse */}
      <div className={cls('throttle')} title={hint('throttle')}>
        <label htmlFor="ctl-throttle">THROTTLE</label>
        <input
          id="ctl-throttle"
          type="range"
          min={0}
          max={100}
          value={Math.round(state.engines.left.throttleLeverNorm * 100)}
          onChange={(e) => {
            const v = Number(e.target.value) / 100;
            inputManager.setThrottle(v);
            sendCommand({ type: 'set_throttle', valueNorm: v });
          }}
          className="vertical-slider"
          data-testid="throttle-slider"
        />
        <span className="ctl-value">{Math.round(state.engines.left.throttleLeverNorm * 100)}%</span>
      </div>
      <div className={cls('reverse_thrust')} title={hint('reverse_thrust')}>
        <label htmlFor="ctl-reverse">REVERSE</label>
        <input
          id="ctl-reverse"
          type="range"
          min={0}
          max={100}
          value={Math.round(state.engines.left.reverserNorm * 100)}
          onChange={(e) => inputManager.setReverser(Number(e.target.value) / 100)}
          className="vertical-slider rev"
        />
        <span className="ctl-value">{Math.round(state.engines.left.reverserNorm * 100)}%</span>
      </div>

      {/* Flap lever with detents */}
      <div className={cls('flaps')} title={hint('flaps')}>
        <label>FLAPS</label>
        <div className="flap-detents" data-testid="flap-lever">
          {FLAP_DETENTS.map((d) => (
            <button
              key={d}
              type="button"
              className={state.controls.flapHandleDetent === d ? 'detent active' : 'detent'}
              onClick={() => {
                audioEngine.click('flap_lever');
                sendCommand({ type: 'set_flaps', detent: d as FlapDetent });
              }}
            >
              {d}
            </button>
          ))}
        </div>
      </div>

      {/* Speed brake */}
      <div className={cls('speedbrake')} title={hint('speedbrake')}>
        <label htmlFor="ctl-spdbrk">SPD BRK</label>
        <input
          id="ctl-spdbrk"
          type="range"
          min={0}
          max={100}
          value={Math.round(state.controls.speedbrakeLeverNorm * 100)}
          onChange={(e) => {
            audioEngine.click('lever');
            sendCommand({ type: 'set_speedbrake', leverNorm: Number(e.target.value) / 100 });
          }}
          className="vertical-slider"
        />
        <button
          type="button"
          className={`ctl-btn ${cls('speedbrake_arm')} ${state.controls.speedbrakeArmed ? 'lit' : ''}`}
          data-testid="speedbrake-arm"
          title={hint('speedbrake_arm')}
          onClick={() => {
            audioEngine.click();
            sendCommand({ type: 'set_speedbrake_armed', armed: !state.controls.speedbrakeArmed });
          }}
        >
          ARM
        </button>
      </div>

      {/* Gear lever */}
      <div className={cls('gear')} title={hint('gear')}>
        <label>GEAR</label>
        <div className="gear-lever" data-testid="gear-lever">
          <button
            type="button"
            className={!state.controls.gearLeverDown ? 'detent active' : 'detent'}
            onClick={() => {
              audioEngine.click('gear_lever');
              sendCommand({ type: 'set_gear', down: false });
            }}
          >
            UP
          </button>
          <button
            type="button"
            className={state.controls.gearLeverDown ? 'detent active' : 'detent'}
            onClick={() => {
              audioEngine.click('gear_lever');
              sendCommand({ type: 'set_gear', down: true });
            }}
          >
            DN
          </button>
        </div>
      </div>

      {/* Autobrake rotary */}
      <div className={cls('autobrake')} title={hint('autobrake')}>
        <label>AUTOBRK</label>
        <div className="rotary" data-testid="autobrake">
          {AUTOBRAKE_ORDER.map((s) => (
            <button
              key={s}
              type="button"
              className={state.controls.autobrake === s ? 'detent active' : 'detent'}
              onClick={() => {
                audioEngine.click('rotary');
                sendCommand({ type: 'set_autobrake', setting: s });
              }}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Lights + parking brake */}
      <div className="ctl lights">
        <label>LIGHTS / BRAKE</label>
        <div className="switch-column">
          {(
            [
              ['light_landing', 'LAND', 'landing'],
              ['light_taxi', 'TAXI', 'taxi'],
              ['light_strobe', 'STRB', 'strobe'],
              ['light_beacon', 'BCN', 'beacon'],
            ] as const
          ).map(([id, label, light]) => (
            <button
              key={id}
              type="button"
              title={hint(id)}
              data-testid={`light-${light}`}
              className={`ctl-btn ${guidedControlId === id ? 'ctl-guided' : ''} ${state.lights[light] ? 'lit' : ''}`}
              onClick={() => {
                audioEngine.click();
                sendCommand({ type: 'set_light', light, on: !state.lights[light] });
              }}
            >
              {label}
            </button>
          ))}
          <button
            type="button"
            data-testid="parking-brake"
            className={`ctl-btn ${state.controls.parkingBrakeSet ? 'lit-red' : ''}`}
            onClick={() => {
              audioEngine.click();
              sendCommand({ type: 'set_parking_brake', engaged: !state.controls.parkingBrakeSet });
            }}
          >
            PARK
          </button>
        </div>
      </div>
    </div>
  );
}
