import { FLAP_DETENTS, clamp, type AutobrakeSetting, type FlapDetent } from '@b737/shared';
import { audioEngine } from '../audio/audioEngine.js';
import { sendCommand } from '../state/connection.js';
import { useSimStore } from '../state/stores.js';

/**
 * 3D cockpit interaction handlers (Phase 2): translate mesh picks/drags into
 * typed commands. Controls display backend state; a rejected command simply
 * doesn't move anything (spec §7).
 */

const AUTOBRAKE_CYCLE: AutobrakeSetting[] = ['RTO', 'OFF', '1', '2', '3', 'MAX'];

export interface DragSession {
  controlId: string;
  startValueNorm: number;
}

export function beginControlDrag(controlId: string): DragSession | null {
  const state = useSimStore.getState().latest;
  if (!state) return null;
  switch (controlId) {
    case 'throttle':
      return { controlId, startValueNorm: state.engines.left.throttleLeverNorm };
    case 'reverse_thrust':
      return { controlId, startValueNorm: state.engines.left.reverserNorm };
    case 'speedbrake':
      return { controlId, startValueNorm: state.controls.speedbrakeLeverNorm };
    case 'flaps':
      return {
        controlId,
        startValueNorm: FLAP_DETENTS.indexOf(state.controls.flapHandleDetent as FlapDetent) /
          (FLAP_DETENTS.length - 1),
      };
    default:
      return null;
  }
}

/** dyPx: pointer travel since drag start (screen px, + = downward). */
export function updateControlDrag(session: DragSession, dyPx: number): void {
  // pulling a lever toward you (down on screen) increases it
  const value = clamp(session.startValueNorm + dyPx / 220, 0, 1);
  switch (session.controlId) {
    case 'throttle':
      sendCommand({ type: 'set_throttle', valueNorm: value });
      return;
    case 'reverse_thrust':
      sendCommand({ type: 'set_reverse_thrust', leverNorm: value });
      return;
    case 'speedbrake':
      sendCommand({ type: 'set_speedbrake', leverNorm: value });
      return;
    case 'flaps': {
      const idx = Math.round(value * (FLAP_DETENTS.length - 1));
      const detent = FLAP_DETENTS[idx] as FlapDetent;
      const current = useSimStore.getState().latest?.controls.flapHandleDetent;
      if (detent !== current) {
        audioEngine.click('flap_lever');
        sendCommand({ type: 'set_flaps', detent });
      }
      return;
    }
  }
}

/** Single click on a discrete control mesh. */
export function clickControl(controlId: string, shiftKey: boolean): void {
  const state = useSimStore.getState().latest;
  if (!state) return;
  switch (controlId) {
    case 'gear': {
      audioEngine.click('gear_lever');
      sendCommand({ type: 'set_gear', down: !state.controls.gearLeverDown });
      return;
    }
    case 'parking_brake':
      audioEngine.click('click');
      sendCommand({ type: 'set_parking_brake', engaged: !state.controls.parkingBrakeSet });
      return;
    case 'autobrake': {
      const idx = AUTOBRAKE_CYCLE.indexOf(state.controls.autobrake);
      const next =
        AUTOBRAKE_CYCLE[
          (idx + (shiftKey ? AUTOBRAKE_CYCLE.length - 1 : 1)) % AUTOBRAKE_CYCLE.length
        ]!;
      audioEngine.click('rotary');
      sendCommand({ type: 'set_autobrake', setting: next });
      return;
    }
    case 'flaps': {
      const idx = FLAP_DETENTS.indexOf(state.controls.flapHandleDetent as FlapDetent);
      const nextIdx = clamp(idx + (shiftKey ? -1 : 1), 0, FLAP_DETENTS.length - 1);
      audioEngine.click('flap_lever');
      sendCommand({ type: 'set_flaps', detent: FLAP_DETENTS[nextIdx] as FlapDetent });
      return;
    }
    case 'speedbrake_arm':
      audioEngine.click('click');
      sendCommand({ type: 'set_speedbrake_armed', armed: !state.controls.speedbrakeArmed });
      return;
    default:
      return;
  }
}
