import {
  SYSTEM_SWITCHES,
  type AircraftState,
  type EngineStartMode,
  type SystemSwitch,
} from '@b737/shared';
import { sendCommand, sendCommandWithSound } from '../state/connection.js';
import { useSettingsStore } from '../state/stores.js';

/**
 * Overhead panel and annunciators (spec §22 Phase 4 T5).
 *
 * Every switch shows BACKEND systems state and sends `set_system_switch`; the
 * panel owns nothing. A rejected command (generator without a running engine,
 * start without duct pressure) simply leaves the switch where it was, and the
 * status bar shows why.
 */

interface SwitchSpec {
  id: SystemSwitch;
  label: string;
  isOn: (s: AircraftState) => boolean;
}

interface SwitchGroup {
  title: string;
  switches: SwitchSpec[];
}

const GROUPS: SwitchGroup[] = [
  {
    title: 'ELEC',
    switches: [
      { id: 'battery', label: 'BAT', isOn: (s) => s.systems.electrical.batterySwitchOn },
      { id: 'standby_power', label: 'STBY', isOn: (s) => s.systems.electrical.standbyPowerOn },
      { id: 'external_power', label: 'EXT', isOn: (s) => s.systems.electrical.externalPowerOn },
      { id: 'apu_gen', label: 'APU GEN', isOn: (s) => s.systems.electrical.apuGenOn },
      { id: 'gen1', label: 'GEN 1', isOn: (s) => s.systems.electrical.gen1On },
      { id: 'gen2', label: 'GEN 2', isOn: (s) => s.systems.electrical.gen2On },
    ],
  },
  {
    title: 'APU',
    switches: [
      { id: 'apu_master', label: 'MASTER', isOn: (s) => s.systems.apu.state !== 'off' },
      { id: 'apu_start', label: 'START', isOn: (s) => s.systems.apu.state === 'starting' },
      { id: 'bleed_apu', label: 'BLEED', isOn: (s) => s.systems.apu.bleedOn },
    ],
  },
  {
    title: 'FUEL',
    switches: [
      { id: 'fuel_pump_left', label: 'L PUMP', isOn: (s) => s.systems.fuel.pumpLeftOn },
      { id: 'fuel_pump_center', label: 'CTR', isOn: (s) => s.systems.fuel.pumpCenterOn },
      { id: 'fuel_pump_right', label: 'R PUMP', isOn: (s) => s.systems.fuel.pumpRightOn },
    ],
  },
  {
    title: 'HYD',
    switches: [
      { id: 'hyd_pump_eng1', label: 'ENG 1', isOn: (s) => s.systems.hydraulic.engPump1On },
      { id: 'hyd_pump_eng2', label: 'ENG 2', isOn: (s) => s.systems.hydraulic.engPump2On },
      { id: 'hyd_pump_elec1', label: 'ELEC 1', isOn: (s) => s.systems.hydraulic.elecPump1On },
      { id: 'hyd_pump_elec2', label: 'ELEC 2', isOn: (s) => s.systems.hydraulic.elecPump2On },
    ],
  },
  {
    title: 'AIR',
    switches: [
      { id: 'bleed_eng1', label: 'BLEED 1', isOn: (s) => s.systems.pneumatic.bleed1On },
      { id: 'bleed_eng2', label: 'BLEED 2', isOn: (s) => s.systems.pneumatic.bleed2On },
      { id: 'isolation_valve', label: 'ISLN', isOn: (s) => s.systems.pneumatic.isolationValveOpen },
      { id: 'pack_left', label: 'PACK L', isOn: (s) => s.systems.pneumatic.packLeftOn },
      { id: 'pack_right', label: 'PACK R', isOn: (s) => s.systems.pneumatic.packRightOn },
    ],
  },
  {
    title: 'ANTI-ICE',
    switches: [
      { id: 'anti_ice_eng1', label: 'ENG 1', isOn: (s) => s.systems.iceProtection.engine1On },
      { id: 'anti_ice_eng2', label: 'ENG 2', isOn: (s) => s.systems.iceProtection.engine2On },
      { id: 'anti_ice_wing', label: 'WING', isOn: (s) => s.systems.iceProtection.wingOn },
    ],
  },
  {
    title: 'IRS',
    switches: [
      { id: 'irs_left', label: 'L NAV', isOn: (s) => s.systems.irs.leftState !== 'off' },
      { id: 'irs_right', label: 'R NAV', isOn: (s) => s.systems.irs.rightState !== 'off' },
    ],
  },
  {
    title: 'START LEVERS',
    switches: [
      {
        id: 'start_lever_left',
        label: 'ENG 1',
        isOn: (s) => s.systems.engines.left.fuelValveOpen,
      },
      {
        id: 'start_lever_right',
        label: 'ENG 2',
        isOn: (s) => s.systems.engines.right.fuelValveOpen,
      },
    ],
  },
];

// Every switch in the registry must appear exactly once on the panel.
const PANEL_SWITCH_IDS = new Set(GROUPS.flatMap((g) => g.switches.map((s) => s.id)));
export const MISSING_PANEL_SWITCHES = SYSTEM_SWITCHES.filter((id) => !PANEL_SWITCH_IDS.has(id));

export function OverheadPanel({
  state,
  guidedControlId,
}: {
  state: AircraftState;
  guidedControlId: string | null;
}): JSX.Element {
  const sys = state.systems;
  const guidedMode = useSettingsStore((s) => s.mode === 'guided');
  return (
    <div className="panel overhead-panel" data-testid="overhead-panel">
      <div className="panel-head">
        <span>Overhead</span>
        <Annunciators state={state} />
      </div>
      <div className="overhead-groups">
        {GROUPS.map((group) => (
          <div className="oh-group" key={group.title}>
            <label>{group.title}</label>
            <div className="oh-switches">
              {group.switches.map((sw) => {
                const on = sw.isOn(state);
                return (
                  <button
                    key={sw.id}
                    type="button"
                    className={`oh-switch ${on ? 'on' : ''} ${guidedMode && guidedControlId === `system:${sw.id}` ? 'ctl-guided' : ''}`}
                    data-testid={`sw-${sw.id}`}
                    data-control-id={`system:${sw.id}`}
                    onClick={() =>
                      sendCommandWithSound(
                        { type: 'set_system_switch', switch: sw.id, on: !on },
                        'click',
                      )
                    }
                  >
                    {sw.label}
                  </button>
                );
              })}
            </div>
          </div>
        ))}

        <div className="oh-group">
          <label>ENG START</label>
          <div className="oh-switches">
            {(['left', 'right'] as const).map((engine) => {
              const eng = sys.engines[engine];
              return (
                <div className="oh-start" key={engine}>
                  <span className="oh-start-label">{engine === 'left' ? 'ENG 1' : 'ENG 2'}</span>
                  {(['off', 'ground'] as EngineStartMode[]).map((mode) => (
                    <button
                      key={mode}
                      type="button"
                      className={`oh-switch ${eng.startMode === mode ? 'on' : ''} ${guidedMode && guidedControlId === `system:start_${engine}_${mode}` ? 'ctl-guided' : ''}`}
                      data-testid={`start-${engine}-${mode}`}
                      data-control-id={`system:start_${engine}_${mode}`}
                      onClick={() => sendCommand({ type: 'set_engine_start', engine, mode })}
                    >
                      {mode === 'off' ? 'OFF' : 'GND'}
                    </button>
                  ))}
                  <span className="oh-readout">N2 {eng.n2Pct.toFixed(0)}%</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <Synoptic state={state} />
    </div>
  );
}

/** Master caution / warning plus the active annunciation list. */
function Annunciators({ state }: { state: AircraftState }): JSX.Element {
  const { annunciations, masterCaution, masterWarning } = state.systems;
  return (
    <div className="annunciators" data-testid="annunciators">
      <button
        type="button"
        className={`ann-master ${masterWarning ? 'warning' : masterCaution ? 'caution' : ''}`}
        data-testid="master-caution"
        title="master caution / warning — click to recall"
        onClick={() => sendCommand({ type: 'reset_master_caution' })}
      >
        {masterWarning ? 'MASTER WARNING' : masterCaution ? 'MASTER CAUTION' : 'NO ALERTS'}
      </button>
      <div className="ann-list">
        {annunciations.map((a) => (
          <span key={a.id} className={`ann ann-${a.severity}`} data-testid={`ann-${a.id}`}>
            {a.text}
          </span>
        ))}
      </div>
    </div>
  );
}

/** Read-only systems synoptic: what is powered, pressurised and available. */
function Synoptic({ state }: { state: AircraftState }): JSX.Element {
  const s = state.systems;
  const rows: [string, string][] = [
    ['DC bus', s.electrical.dcBusPowered ? 'POWERED' : 'OFF'],
    ['AC buses', s.electrical.acBus1Powered ? 'POWERED' : 'OFF'],
    ['APU', `${s.apu.state.toUpperCase()} ${s.apu.n1Pct.toFixed(0)}% ${s.apu.egtC.toFixed(0)}°C`],
    ['Duct', `${s.pneumatic.ductPressurePsi.toFixed(0)} psi`],
    ['Fuel', s.fuel.pressurised ? 'PRESSURISED' : 'NO PRESSURE'],
    [
      'HYD A/B',
      `${s.hydraulic.systemAPressurePsi.toFixed(0)} / ${s.hydraulic.systemBPressurePsi.toFixed(0)} psi`,
    ],
    [
      'IRS',
      s.irs.leftState === 'aligned' && s.irs.rightState === 'aligned'
        ? 'ALIGNED'
        : `${s.irs.leftState.toUpperCase()} ${(s.irs.alignProgress * 100).toFixed(0)}%`,
    ],
  ];
  return (
    <div className="synoptic" data-testid="synoptic">
      {rows.map(([label, value]) => (
        <div className="syn-row" key={label}>
          <span className="syn-label">{label}</span>
          <span className="syn-value">{value}</span>
        </div>
      ))}
    </div>
  );
}
