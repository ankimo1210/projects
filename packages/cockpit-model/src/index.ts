/**
 * Declarative cockpit control registry (spec §9): cockpit geometry/UI binds to
 * aircraft state through these definitions — no per-switch custom wiring.
 * `stateSelector` is a dot path into AircraftState; `commandTemplate` names the
 * AircraftCommand the control emits.
 */

export type ControlInteraction = 'click' | 'toggle' | 'drag' | 'rotary' | 'lever';

export interface CockpitControlDefinition {
  id: string;
  label: string;
  panel: 'pedestal' | 'main' | 'glareshield' | 'overhead';
  /** 3D mesh names bound to this control (Phase 2 asset import tags). */
  meshNames: string[];
  interaction: ControlInteraction;
  /** AircraftCommand type this control emits. */
  command: string;
  /** Dot path into AircraftState that this control displays. */
  stateSelector: string;
  min?: number;
  max?: number;
  detents?: number[];
  trainingHint?: string;
  soundId?: string;
}

export const COCKPIT_CONTROLS: CockpitControlDefinition[] = [
  {
    id: 'throttle',
    label: 'Thrust levers',
    panel: 'pedestal',
    meshNames: ['throttle_lever_l', 'throttle_lever_r'],
    interaction: 'lever',
    command: 'set_throttle',
    stateSelector: 'engines.left.throttleLeverNorm',
    min: 0,
    max: 1,
    trainingHint: 'Set takeoff thrust smoothly; idle for landing.',
    soundId: 'lever',
  },
  {
    id: 'reverse_thrust',
    label: 'Reverse thrust',
    panel: 'pedestal',
    meshNames: ['reverser_lever_l', 'reverser_lever_r'],
    interaction: 'lever',
    command: 'set_reverse_thrust',
    stateSelector: 'engines.left.reverserNorm',
    min: 0,
    max: 1,
    trainingHint: 'Only on the ground, after touchdown, with thrust levers closed.',
    soundId: 'lever',
  },
  {
    id: 'flaps',
    label: 'Flap lever',
    panel: 'pedestal',
    meshNames: ['flap_lever'],
    interaction: 'lever',
    command: 'set_flaps',
    stateSelector: 'controls.flapHandleDetent',
    detents: [0, 1, 2, 5, 10, 15, 25, 30, 40],
    trainingHint: 'Flaps 5 for takeoff, 30 for landing in this scenario.',
    soundId: 'flap_lever',
  },
  {
    id: 'speedbrake',
    label: 'Speed brake',
    panel: 'pedestal',
    meshNames: ['speedbrake_lever'],
    interaction: 'lever',
    command: 'set_speedbrake',
    stateSelector: 'controls.speedbrakeLeverNorm',
    min: 0,
    max: 1,
    trainingHint: 'Arm before landing; verify DOWN before takeoff.',
    soundId: 'lever',
  },
  {
    id: 'speedbrake_arm',
    label: 'Speed brake ARM',
    panel: 'pedestal',
    meshNames: ['speedbrake_arm'],
    interaction: 'toggle',
    command: 'set_speedbrake_armed',
    stateSelector: 'controls.speedbrakeArmed',
    trainingHint: 'Armed spoilers deploy automatically at touchdown.',
    soundId: 'click',
  },
  {
    id: 'gear',
    label: 'Landing gear lever',
    panel: 'main',
    meshNames: ['gear_lever'],
    interaction: 'lever',
    command: 'set_gear',
    stateSelector: 'controls.gearLeverDown',
    trainingHint: 'Gear up after positive rate; down before the final approach fix.',
    soundId: 'gear_lever',
  },
  {
    id: 'parking_brake',
    label: 'Parking brake',
    panel: 'pedestal',
    meshNames: ['parking_brake'],
    interaction: 'toggle',
    command: 'set_parking_brake',
    stateSelector: 'controls.parkingBrakeSet',
    soundId: 'click',
  },
  {
    id: 'autobrake',
    label: 'Autobrake selector',
    panel: 'main',
    meshNames: ['autobrake_knob'],
    interaction: 'rotary',
    command: 'set_autobrake',
    stateSelector: 'controls.autobrake',
    trainingHint: 'RTO for takeoff; 2 or 3 for landing.',
    soundId: 'rotary',
  },
  {
    id: 'light_landing',
    label: 'Landing lights',
    panel: 'overhead',
    meshNames: ['sw_landing_lights'],
    interaction: 'toggle',
    command: 'set_light',
    stateSelector: 'lights.landing',
    soundId: 'click',
  },
  {
    id: 'light_taxi',
    label: 'Taxi light',
    panel: 'overhead',
    meshNames: ['sw_taxi_light'],
    interaction: 'toggle',
    command: 'set_light',
    stateSelector: 'lights.taxi',
    soundId: 'click',
  },
  {
    id: 'light_strobe',
    label: 'Strobe lights',
    panel: 'overhead',
    meshNames: ['sw_strobe'],
    interaction: 'toggle',
    command: 'set_light',
    stateSelector: 'lights.strobe',
    soundId: 'click',
  },
  {
    id: 'light_beacon',
    label: 'Beacon',
    panel: 'overhead',
    meshNames: ['sw_beacon'],
    interaction: 'toggle',
    command: 'set_light',
    stateSelector: 'lights.beacon',
    soundId: 'click',
  },
];

export function getControl(id: string): CockpitControlDefinition | undefined {
  return COCKPIT_CONTROLS.find((c) => c.id === id);
}
