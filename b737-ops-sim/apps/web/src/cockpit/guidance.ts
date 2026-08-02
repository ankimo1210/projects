import type { TrainingSession } from '@b737/training-engine';

/**
 * Guided-mode helper: which control should the user look at next, and why
 * (spec §15). Pure derivation from session state — no hidden state.
 */
export interface GuidanceHint {
  controlId: string | null;
  text: string;
}

const CHECKLIST_ITEM_TO_CONTROL: Record<string, string> = {
  flaps: 'flaps',
  autobrake: 'autobrake',
  speedbrake: 'speedbrake',
  speedbrake_armed: 'speedbrake_arm',
  speedbrake_down: 'speedbrake',
  exterior_lights: 'light_landing',
  lights_after_landing: 'light_landing',
  gear: 'gear',
  flaps_up: 'flaps',
  autobrake_off: 'autobrake',
  parking_brake: 'parking_brake',
  parking_brake_released: 'parking_brake',
  parking_brake_set: 'parking_brake',
  taxi_light: 'light_taxi',
  beacon: 'light_beacon',
  flaps_takeoff: 'flaps',
  thrust_idle: 'throttle',
  exterior_lights_off: 'light_landing',
};

export function deriveGuidance(session: TrainingSession): GuidanceHint {
  const phase = session.phaseId;
  // A pending response takes priority
  const pending = session.transcript.find((e) => e.expectedResponse && !e.responseResult);
  if (pending) {
    return {
      controlId: null,
      text: `Respond to ${pending.speaker === 'atc' ? 'ATC' : 'the first officer'}: "${pending.message}"`,
    };
  }
  const checklistId = session.activeChecklistId;
  if (checklistId) {
    const run = session.runtime.checklistRuns.get(checklistId);
    const item = run?.activeItem;
    if (item) {
      return {
        controlId: CHECKLIST_ITEM_TO_CONTROL[item.definition.id] ?? null,
        text:
          item.definition.trainingHint ?? `${run!.definition.title}: ${item.definition.challenge}`,
      };
    }
  }
  switch (phase) {
    // ---- ground phases (M3) ----
    case 'preflight':
      return {
        controlId: null,
        text: 'Complete the Before Start checklist, then request a taxi clearance.',
      };
    case 'taxi_out':
      return {
        controlId: 'throttle',
        text: 'Taxi via A to runway 28R and stop before the holding position.',
      };
    case 'hold_short':
      return {
        controlId: null,
        text: 'Holding short: finish the Before Takeoff checklist and request takeoff clearance.',
      };
    case 'taxi_in':
      return { controlId: 'throttle', text: 'Taxi to the stand via A.' };
    case 'parked':
      return { controlId: 'parking_brake', text: 'Set the parking brake and run Shutdown.' };
    case 'go_around':
      return {
        controlId: 'gear',
        text: 'Go-around: gear up, flaps 15, climb to 3,000 and follow ATC vectors.',
      };
    case 'before_takeoff':
      return {
        controlId: null,
        text: 'Complete the Before Takeoff checklist, then request takeoff clearance.',
      };
    case 'line_up':
      return { controlId: null, text: 'Taxi onto runway 28R and align with the centerline.' };
    case 'takeoff_roll':
      return { controlId: 'throttle', text: 'Set takeoff thrust. Rotate smoothly at VR.' };
    case 'rotation':
      return { controlId: null, text: 'Pitch to about 15° and establish a climb.' };
    case 'initial_climb':
      return { controlId: 'gear', text: 'Positive rate → gear up. Follow ATC instructions.' };
    case 'approach_setup':
      return {
        controlId: 'flaps',
        text: 'Configure for landing: flaps, gear, arm speed brake, set autobrake.',
      };
    case 'final_approach':
      return {
        controlId: null,
        text: 'Track the localizer and glideslope. Complete the Landing checklist.',
      };
    case 'landing':
      return {
        controlId: 'reverse_thrust',
        text: 'After touchdown: reverse thrust, brake, track the centerline.',
      };
    case 'runway_exit':
      return {
        controlId: 'flaps',
        text: 'Exit the runway, then complete the After Landing checklist.',
      };
    default:
      return { controlId: null, text: 'Review your debrief.' };
  }
}
