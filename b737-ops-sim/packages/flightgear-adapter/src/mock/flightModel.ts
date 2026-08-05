import { MockSystemsModel, type SystemsStartMode } from './systemsModel.js';
import {
  FLAP_DETENTS,
  FT_TO_M,
  G_MPS2,
  KT_TO_MPS,
  LB_TO_KG,
  M_TO_FT,
  MPS_TO_FPM,
  MPS_TO_KT,
  angleDiffDeg,
  clamp,
  createSeededRandom,
  degToRad,
  destinationPoint,
  flapDetentToNorm,
  getRunway,
  getTaxiNetwork,
  normalizeDeg360,
  runwayPointToLatLon,
  radToDeg,
  toLocalEnuM,
  fromLocalEnuM,
  type AircraftCommand,
  type AircraftState,
  type AutobrakeSetting,
  type CommandResult,
  type FlapDetent,
  buildRoute,
  emptyFmsState,
  headingForTrack,
  getProcedure,
  getWaypoint,
  trackLeg,
  type FailureKind,
  type FmsState,
  type PitchMode,
  type RollMode,
  type RunwayData,
  type ScenarioInitialState,
  type SystemSwitch,
} from '@b737/shared';

/**
 * Deterministic point-mass ("2.5-DOF") 737-class flight model for mock mode.
 *
 * NON_CERTIFIED_APPROXIMATION — this is a plausibility model for UI/procedure
 * development, not an aerodynamic reference. All coefficients are round
 * numbers chosen to give 737-800-like magnitudes (takeoff roll, climb rate,
 * approach behavior). FlightGear + JSBSim provides the real dynamics in
 * flightgear mode.
 *
 * Internals are SI (m, m/s, kg, N, rad only at trig call sites); the public
 * snapshot converts to the unit-explicit shared schema. Physics advances in
 * fixed steps of {@link PHYSICS_DT_SEC} regardless of wall clock, so a fixed
 * seed and command sequence reproduce identical trajectories (spec §5).
 */

export const PHYSICS_DT_SEC = 1 / 60;

/** Cold-and-dark scenarios start at a stand with everything off. */
function systemsModeFor(config: ScenarioInitialState): SystemsStartMode {
  return config.startAt === 'stand' && config.coldAndDark === true ? 'cold_and_dark' : 'running';
}

// --- Airframe constants (approximate 737-800 magnitudes) ---
const WING_AREA_M2 = 124.6;
const RHO_KGPM3 = 1.225;
const CD0 = 0.022;
const K_INDUCED = 0.045;
const CL0_CLEAN = 0.2;
const CL_PER_FLAP_NORM = 1.0;
const CL_ALPHA_PER_DEG = 0.095;
const CLMAX_CLEAN = 1.4;
const CLMAX_PER_FLAP_NORM = 1.2;
const CD_FLAP_FACTOR = 0.055;
const CD_GEAR = 0.02;
const CD_SPOILER = 0.065;
const CL_SPOILER_KILL_AIR = 0.5;
const MAX_TOTAL_THRUST_N = 220_000;
const IDLE_N1_PCT = 22;
const MAX_N1_PCT = 94;
const N1_TAU_SEC = 2.2;
const N1_RATE_LIMIT_PCT_PER_SEC = 14;
const REVERSE_MAX_N1_PCT = 85;
const REVERSE_EFFICIENCY = 0.45;
const MU_ROLLING = 0.02;
const MU_BRAKE_MAX = 0.38;
const AOA_STALL_DEG = 14;
const PITCH_RATE_MAX_DEGPS = 3.5;
const ROLL_RATE_MAX_DEGPS = 15;
const GEAR_TRANSIT_SEC = 8;
const FLAP_FULL_TRAVEL_SEC = 25;
const SPOILER_TRAVEL_SEC = 1.5;
const GROUND_STEER_MAX_DEGPS = 30;
/** Full single-engine thrust imbalance yaw rate in free flight. */
const ENGINE_ASYMMETRY_YAW_RATE_DEGPS = 3;
/** Full rudder authority at flying speed; sized to counter one failed engine. */
const RUDDER_YAW_RATE_MAX_DEGPS = 4;
/** Small rolling tendency toward the failed engine. */
const ENGINE_ASYMMETRY_ROLL_RATE_DEGPS = 1.5;

/**
 * RTO autobrake arming/trigger thresholds. NON_CERTIFIED_APPROXIMATION —
 * representative of published 737 behaviour, not taken from an FCOM.
 */
const RTO_ARM_THROTTLE_NORM = 0.6;
const RTO_TRIGGER_THROTTLE_NORM = 0.05;
const RTO_ARM_SPEED_KT = 60;
/** Altitude over which the surface wind blends into the wind aloft. */
const WIND_ALOFT_BLEND_FT = 3000;
/** Gust response time constant. */
const GUST_TAU_SEC = 4;
/** Attitude-perturbation amplitude added at turbulence = 1.0. */
const TURBULENCE_ATTITUDE_GAIN = 2.5;

/** V/S the simple autopilot uses when the MCP V/S window is zeroed. */
const DEFAULT_AP_CLIMB_FPM = 1800;

/**
 * Autopilot mode thresholds. NON_CERTIFIED_APPROXIMATION — tuned so capture
 * behaves plausibly in the mock world, not taken from a 737 FCOM.
 */
const LOC_CAPTURE_DOTS = 1.5;
const LOC_CAPTURE_DEG = 45;
const LOC_LOSS_DOTS = 2.2;
const LOC_TRACK_DEG_PER_DOT = 9;
const GS_CAPTURE_DOTS = 0.6;
const GS_LOSS_DOTS = 2.2;
const GS_TRACK_FPM_PER_DOT = 350;
const ALT_CAPTURE_FT = 400;
/** Below this radio altitude an armed approach keeps flying the path down. */
const GS_HOLD_BELOW_FT = 300;
/** Go-around attitude held by TO/GA. */
const TOGA_PITCH_DEG = 15;
/** `startAt: 'final_approach'` places the aircraft this far out, on profile. */
const FINAL_APPROACH_DIST_M = 9000; // ~4.9 NM
const FINAL_APPROACH_IAS_KT = 150;

const AUTOBRAKE_BRAKE_NORM: Record<AutobrakeSetting, number> = {
  OFF: 0,
  RTO: 0.9,
  '1': 0.25,
  '2': 0.4,
  '3': 0.6,
  MAX: 0.85,
};

export interface MockPilotInputs {
  elevatorNorm: number; // -1..1, +1 = nose up
  aileronNorm: number; // -1..1, +1 = right
  rudderNorm: number; // -1..1, +1 = right
  throttleNorm: number; // 0..1
  brakeNorm: number; // 0..1
  reverserLeverNorm: number; // 0..1
}

interface McpState {
  selSpeedKt: number;
  selHeadingDeg: number;
  selAltitudeFt: number;
  selVerticalSpeedFpm: number;
  autopilotEngaged: boolean;
  flightDirectorOn: boolean;
}

export class MockFlightModel {
  private runway: RunwayData;
  private rand: () => number = createSeededRandom(0);
  private massKg = 145000 * LB_TO_KG;
  private windDirDeg = 0;
  private windSpeedMps = 0;

  // Primary state (SI)
  private simTimeSec = 0;
  private latDeg = 0;
  private lonDeg = 0;
  private altM = 0; // MSL
  private iasMps = 0; // treated as TAS at these altitudes
  private headingDegTrue = 0;
  private pitchDeg = 0;
  private rollDeg = 0;
  private vsMps = 0;
  private onGround = true;
  private aoaDeg = 0;

  // Systems state
  private n1LeftPct = IDLE_N1_PCT;
  private n1RightPct = IDLE_N1_PCT;
  private flapHandleDetent: FlapDetent = 5;
  private flapsActualNorm = flapDetentToNorm(5);
  private gearLeverDown = true;
  private gearPositionNorm = 1;
  private speedbrakeLeverNorm = 0;
  private speedbrakeArmed = false;
  private spoilersNorm = 0;
  private parkingBrakeSet = true;
  private autobrake: AutobrakeSetting = 'OFF';
  private autobrakeActive = false;
  /** RTO autobrake armed: selected on the ground and takeoff thrust seen. */
  private rtoArmed = false;
  /** Manual braking inhibits RTO until the crew explicitly reselects it. */
  private rtoManualOverride = false;
  /** Approach armed on the MCP; drives LOC/GS capture. */
  private approachArmed = false;
  /** Route / FMS state (spec §22 Phase 5). */
  private fms: FmsState = emptyFmsState();
  /**
   * Where the first leg starts. It must be the position the route was built
   * from, not the live position — using the latter makes the cross-track
   * identically zero and the leg impossible to sequence.
   */
  private fmsOrigin: { latDeg: number; lonDeg: number } | null = null;
  /** Active failures; systems express them, this set records them. */
  private failures = new Set<FailureKind>();
  /** Exact target-state restorers, applied in reverse injection order on clear. */
  private failureRestores = new Map<FailureKind, () => void>();
  /** Weather beyond the steady surface wind. */
  private windAloftDirDeg = 0;
  private windAloftSpeedKt = 0;
  private gustMaxKt = 0;
  private visibilityM = 10000;
  private turbulence = 0;
  private gustKt = 0;
  private togaActive = false;
  private apRollMode: RollMode | null = null;
  private apPitchMode: PitchMode | null = null;
  /** Sub-step remainder carried between `step()` calls. */
  private stepCarrySec = 0;
  /** Aircraft systems (spec §22 Phase 4); drives what the engines can do. */
  readonly systems: MockSystemsModel;
  private lights = { landing: false, taxi: false, strobe: false, beacon: true };
  private mcp: McpState = {
    selSpeedKt: 150,
    selHeadingDeg: 284,
    selAltitudeFt: 3000,
    selVerticalSpeedFpm: 0,
    autopilotEngaged: false,
    flightDirectorOn: true,
  };

  readonly inputs: MockPilotInputs = {
    elevatorNorm: 0,
    aileronNorm: 0,
    rudderNorm: 0,
    throttleNorm: 0,
    brakeNorm: 0,
    reverserLeverNorm: 0,
  };

  constructor(config: ScenarioInitialState) {
    const rwy = getRunway(config.airportIcao, config.runwayId);
    if (!rwy) throw new Error(`unknown runway ${config.airportIcao}/${config.runwayId}`);
    this.runway = rwy;
    this.systems = new MockSystemsModel(systemsModeFor(config));
    this.reset(config);
  }

  reset(config: ScenarioInitialState): void {
    const rwy = getRunway(config.airportIcao, config.runwayId);
    if (!rwy) throw new Error(`unknown runway ${config.airportIcao}/${config.runwayId}`);
    this.runway = rwy;
    this.rand = createSeededRandom(config.seed);
    this.massKg = config.grossWeightLb * LB_TO_KG;
    this.windDirDeg = config.windDirDeg;
    this.windSpeedMps = config.windSpeedKt * KT_TO_MPS;

    this.simTimeSec = 0;
    const fieldAltM = rwy.elevationFtMsl * FT_TO_M;
    if (config.startAt === 'stand') {
      const network = getTaxiNetwork(rwy.airportIcao, rwy.runwayId);
      const stand = network?.stands[0];
      const standNode = stand ? network?.nodes[stand.nodeId] : undefined;
      if (standNode && stand) {
        this.latDeg = standNode.latDeg;
        this.lonDeg = standNode.lonDeg;
        this.headingDegTrue = stand.headingDegTrue;
      } else {
        this.latDeg = rwy.thresholdLatDeg;
        this.lonDeg = rwy.thresholdLonDeg;
        this.headingDegTrue = rwy.headingDegTrue;
      }
    } else if (config.startAt === 'final_approach') {
      // Established on the ILS at FINAL_APPROACH_DIST_M, on profile and on speed.
      const distM = FINAL_APPROACH_DIST_M;
      const pos = runwayPointToLatLon(rwy, -distM, 0);
      this.latDeg = pos.latDeg;
      this.lonDeg = pos.lonDeg;
      this.headingDegTrue = rwy.headingDegTrue;
    } else if (config.startAt === 'holding_point') {
      // Abeam the threshold on the parallel taxiway, facing the runway entry.
      const alongThreshold = destinationPoint(
        rwy.thresholdLatDeg,
        rwy.thresholdLonDeg,
        rwy.headingDegTrue,
        40,
      );
      const hold = destinationPoint(
        alongThreshold.latDeg,
        alongThreshold.lonDeg,
        normalizeDeg360(rwy.headingDegTrue + 90),
        90,
      );
      this.latDeg = hold.latDeg;
      this.lonDeg = hold.lonDeg;
      this.headingDegTrue = normalizeDeg360(rwy.headingDegTrue - 90);
    } else {
      const pos = destinationPoint(
        rwy.thresholdLatDeg,
        rwy.thresholdLonDeg,
        rwy.headingDegTrue,
        30,
      );
      this.latDeg = pos.latDeg;
      this.lonDeg = pos.lonDeg;
      this.headingDegTrue = rwy.headingDegTrue;
    }
    if (config.startAt === 'final_approach') {
      // On the 3° path with the threshold crossing height, gear down, on speed.
      const heightM =
        FINAL_APPROACH_DIST_M * Math.tan(degToRad(rwy.ils.glideslopeDeg)) +
        rwy.ils.thresholdCrossingHeightFt * FT_TO_M;
      this.altM = fieldAltM + heightM;
      this.iasMps = FINAL_APPROACH_IAS_KT * KT_TO_MPS;
      this.pitchDeg = 2;
      this.rollDeg = 0;
      this.vsMps = -this.iasMps * Math.sin(degToRad(rwy.ils.glideslopeDeg));
      this.onGround = false;
      this.aoaDeg = 4;
    } else {
      this.altM = fieldAltM;
      this.iasMps = 0;
      this.pitchDeg = 0;
      this.rollDeg = 0;
      this.vsMps = 0;
      this.onGround = true;
      this.aoaDeg = 0;
    }

    this.n1LeftPct = IDLE_N1_PCT;
    this.n1RightPct = IDLE_N1_PCT;
    this.flapHandleDetent = config.flapDetent;
    this.flapsActualNorm = flapDetentToNorm(config.flapDetent);
    this.gearLeverDown = true;
    this.gearPositionNorm = 1;
    this.speedbrakeLeverNorm = 0;
    this.speedbrakeArmed = false;
    this.spoilersNorm = 0;
    this.parkingBrakeSet = config.startAt === 'final_approach' ? false : config.parkingBrakeSet;
    this.autobrake = 'OFF';
    this.autobrakeActive = false;
    this.systems.reset(systemsModeFor(config));
    this.fms = emptyFmsState();
    this.fmsOrigin = null;
    this.failures.clear();
    this.failureRestores.clear();
    const wx = config.weather;
    this.windAloftDirDeg = wx?.windAloftDirDeg ?? config.windDirDeg;
    this.windAloftSpeedKt = wx?.windAloftSpeedKt ?? config.windSpeedKt;
    this.gustMaxKt = wx?.gustKt ?? 0;
    this.visibilityM = wx?.visibilityM ?? 10000;
    this.turbulence = wx?.turbulence ?? 0;
    this.gustKt = 0;
    for (const failure of config.failures ?? []) this.applyFailure(failure);
    this.rtoArmed = false;
    this.rtoManualOverride = false;
    this.approachArmed = false;
    this.togaActive = false;
    this.apRollMode = null;
    this.apPitchMode = null;
    this.stepCarrySec = 0;
    this.lights = { landing: false, taxi: false, strobe: false, beacon: true };
    this.mcp = {
      selSpeedKt: 150,
      selHeadingDeg: Math.round(this.runway.headingDegMag),
      selAltitudeFt: 3000,
      selVerticalSpeedFpm: 0,
      autopilotEngaged: false,
      flightDirectorOn: true,
    };
    this.inputs.elevatorNorm = 0;
    this.inputs.aileronNorm = 0;
    this.inputs.rudderNorm = 0;
    this.inputs.throttleNorm = 0;
    this.inputs.brakeNorm = 0;
    this.inputs.reverserLeverNorm = 0;
  }

  /** Apply a validated command. Returns a rejection for physically invalid requests. */
  applyCommand(cmd: AircraftCommand): CommandResult {
    switch (cmd.type) {
      case 'set_control_axis':
        if (this.mcp.autopilotEngaged && Math.abs(cmd.valueNorm) > 0.3) {
          // Control override disengages the autopilot, like the real CWS/disconnect.
          this.mcp.autopilotEngaged = false;
        }
        if (cmd.axis === 'pitch') this.inputs.elevatorNorm = cmd.valueNorm;
        else if (cmd.axis === 'roll') this.inputs.aileronNorm = cmd.valueNorm;
        else this.inputs.rudderNorm = cmd.valueNorm;
        return { ok: true };
      case 'set_throttle':
        if (this.inputs.reverserLeverNorm > 0 && cmd.valueNorm > 0.05) {
          return { ok: false, error: 'stow reverse thrust before advancing throttle' };
        }
        this.inputs.throttleNorm = cmd.valueNorm;
        return { ok: true };
      case 'set_brakes':
        this.inputs.brakeNorm = cmd.valueNorm;
        if (cmd.valueNorm > 0.6 && this.autobrake === 'RTO') {
          // A manual takeover is a persistent disarm, not a one-frame drop of
          // autobrake pressure. RTO may arm again only after it is reselected.
          this.autobrakeActive = false;
          this.rtoArmed = false;
          this.rtoManualOverride = true;
        }
        return { ok: true };
      case 'set_parking_brake':
        if (cmd.engaged && this.iasMps * MPS_TO_KT > 5) {
          return { ok: false, error: 'cannot set parking brake while moving' };
        }
        this.parkingBrakeSet = cmd.engaged;
        return { ok: true };
      case 'set_flaps':
        this.flapHandleDetent = cmd.detent as FlapDetent;
        return { ok: true };
      case 'set_gear':
        if (!cmd.down && this.onGround) {
          return { ok: false, error: 'gear lever locked on ground' };
        }
        this.gearLeverDown = cmd.down;
        return { ok: true };
      case 'set_speedbrake':
        this.speedbrakeLeverNorm = cmd.leverNorm;
        if (cmd.leverNorm > 0.1) this.speedbrakeArmed = false;
        return { ok: true };
      case 'set_speedbrake_armed':
        this.speedbrakeArmed = cmd.armed;
        if (cmd.armed) this.speedbrakeLeverNorm = 0;
        return { ok: true };
      case 'set_reverse_thrust':
        if (!this.onGround && cmd.leverNorm > 0) {
          return { ok: false, error: 'reverse thrust only available on ground' };
        }
        if (cmd.leverNorm > 0 && this.inputs.throttleNorm > 0.05) {
          return { ok: false, error: 'close thrust levers before selecting reverse' };
        }
        this.inputs.reverserLeverNorm = cmd.leverNorm;
        return { ok: true };
      case 'set_autobrake':
        this.autobrake = cmd.setting;
        this.autobrakeActive = false;
        // RTO arms as soon as it is selected on the ground; it applies braking
        // only once takeoff thrust has been set and then retarded (see substep).
        this.rtoArmed = false;
        this.rtoManualOverride = false;
        return { ok: true };
      case 'set_mcp_speed':
        this.mcp.selSpeedKt = cmd.speedKt;
        return { ok: true };
      case 'set_mcp_heading':
        this.mcp.selHeadingDeg = normalizeDeg360(cmd.headingDeg);
        return { ok: true };
      case 'set_mcp_altitude':
        this.mcp.selAltitudeFt = cmd.altitudeFt;
        return { ok: true };
      case 'set_mcp_vertical_speed':
        this.mcp.selVerticalSpeedFpm = cmd.verticalSpeedFpm;
        return { ok: true };
      case 'set_autopilot':
        if (cmd.engaged && this.onGround) {
          return { ok: false, error: 'autopilot cannot engage on ground' };
        }
        this.mcp.autopilotEngaged = cmd.engaged;
        return { ok: true };
      case 'set_flight_director':
        this.mcp.flightDirectorOn = cmd.on;
        return { ok: true };
      case 'set_ap_approach_mode':
        this.approachArmed = cmd.armed;
        return { ok: true };
      case 'set_toga':
        if (cmd.engaged) {
          // TO/GA commands go-around thrust and drops the autopilot out of the
          // approach; the crew flies (or re-engages) from there.
          this.togaActive = true;
          this.approachArmed = false;
          this.mcp.autopilotEngaged = false;
          this.inputs.throttleNorm = 1;
          this.inputs.reverserLeverNorm = 0;
        } else {
          this.togaActive = false;
        }
        return { ok: true };
      case 'set_light':
        this.lights[cmd.light] = cmd.on;
        return { ok: true };
      case 'set_system_switch':
        if (cmd.on) {
          const blockingFailure = this.failureBlockingSwitch(cmd.switch);
          if (blockingFailure) {
            return { ok: false, error: `${cmd.switch} is unavailable: ${blockingFailure} active` };
          }
        }
        return this.systems.applySwitch(cmd.switch, cmd.on);
      case 'set_engine_start':
        if (
          (cmd.engine === 'left' && this.failures.has('engine_1_flameout')) ||
          (cmd.engine === 'right' && this.failures.has('engine_2_flameout'))
        ) {
          return { ok: false, error: `engine ${cmd.engine} start unavailable: flameout active` };
        }
        return this.systems.setEngineStart(cmd.engine, cmd.mode);
      case 'reset_master_caution':
        return this.systems.resetMasterCaution();
      case 'load_route': {
        const ids = [cmd.sidId, cmd.starId, cmd.approachId]
          .filter((id): id is string => id !== null)
          .flatMap((id) => getProcedure(id)?.waypointIds ?? []);
        if (ids.length === 0) return { ok: false, error: 'no known procedure in that route' };
        this.fmsOrigin = { latDeg: this.latDeg, lonDeg: this.lonDeg };
        this.fms = {
          ...emptyFmsState(),
          routeId: [cmd.sidId, cmd.starId, cmd.approachId].filter(Boolean).join('/'),
          legs: buildRoute(this.latDeg, this.lonDeg, ids),
          lnavArmed: this.fms.lnavArmed,
        };
        return { ok: true };
      }
      case 'direct_to': {
        const wp = getWaypoint(cmd.waypointId);
        if (!wp) return { ok: false, error: `unknown waypoint '${cmd.waypointId}'` };
        const index = this.fms.legs.findIndex((l) => l.waypoint.id === wp.id);
        if (index < 0) {
          // Not in the route: fly direct to it as a one-leg route.
          this.fmsOrigin = { latDeg: this.latDeg, lonDeg: this.lonDeg };
          this.fms = {
            ...this.fms,
            legs: buildRoute(this.latDeg, this.lonDeg, [wp.id]),
            activeLegIndex: 0,
          };
        } else {
          this.fms = { ...this.fms, activeLegIndex: index };
        }
        return { ok: true };
      }
      case 'set_lnav':
        if (cmd.armed && this.fms.legs.length === 0) {
          return { ok: false, error: 'no route loaded' };
        }
        this.fms = { ...this.fms, lnavArmed: cmd.armed };
        return { ok: true };
      case 'inject_failure':
        return this.applyFailure(cmd.failure);
      case 'clear_failures':
        return this.clearFailures();
    }
  }

  /**
   * Advance simulation by `dtSec` of simulated time. Physics always runs in
   * fixed {@link PHYSICS_DT_SEC} substeps; the leftover is carried to the next
   * call, so simulated time tracks requested time exactly at any publish rate.
   * (Rounding the step count instead made 25 Hz run at 0.83× and 40 Hz at
   * 1.33× real time — R-06.)
   */
  step(dtSec: number): void {
    if (!(dtSec > 0)) return;
    this.stepCarrySec += dtSec;
    while (this.stepCarrySec >= PHYSICS_DT_SEC) {
      this.substep(PHYSICS_DT_SEC);
      this.stepCarrySec -= PHYSICS_DT_SEC;
    }
  }

  private substep(dt: number): void {
    this.simTimeSec += dt;
    const fieldAltM = this.runway.elevationFtMsl * FT_TO_M;

    // --- Secondary surfaces move toward their commands ---
    // Flaps, gear and spoilers are hydraulic: with both systems down they stop
    // where they are (spec §22 Phase 4 D6).
    const hydraulics = this.systems.hydraulicsAvailable;
    const flapTargetNorm = hydraulics
      ? flapDetentToNorm(this.flapHandleDetent)
      : this.flapsActualNorm;
    const flapRate = dt / FLAP_FULL_TRAVEL_SEC;
    this.flapsActualNorm += clamp(flapTargetNorm - this.flapsActualNorm, -flapRate, flapRate);

    const gearTarget = hydraulics ? (this.gearLeverDown ? 1 : 0) : this.gearPositionNorm;
    const gearRate = dt / GEAR_TRANSIT_SEC;
    this.gearPositionNorm += clamp(gearTarget - this.gearPositionNorm, -gearRate, gearRate);

    // Auto speedbrake: armed + touchdown + idle thrust -> full deploy.
    if (
      this.speedbrakeArmed &&
      this.onGround &&
      this.inputs.throttleNorm < 0.1 &&
      this.iasMps * MPS_TO_KT > 40
    ) {
      this.speedbrakeLeverNorm = 1;
      this.speedbrakeArmed = false;
    }
    const spoilerTarget = hydraulics ? this.speedbrakeLeverNorm : this.spoilersNorm;
    const spoilerRate = dt / SPOILER_TRAVEL_SEC;
    this.spoilersNorm += clamp(spoilerTarget - this.spoilersNorm, -spoilerRate, spoilerRate);

    // --- Engines ---
    // Systems decide whether there is an engine at all (spec §22 Phase 4 D6):
    // a shut-down engine windmills, it does not idle.
    this.systems.step(dt, { onGround: this.onGround, dtSec: dt });
    this.updateFms();
    // Gusts are seeded noise, so a scenario stays reproducible (M5 D4).
    if (this.gustMaxKt > 0) {
      const target = this.gustMaxKt * this.rand() ** 2;
      this.gustKt += (target - this.gustKt) * clamp(dt / GUST_TAU_SEC, 0, 1);
    }
    const leftRunning = this.systems.engineRunning('left');
    const rightRunning = this.systems.engineRunning('right');
    const anyRunning = leftRunning || rightRunning;
    const reverserActive = anyRunning && this.onGround && this.inputs.reverserLeverNorm > 0.02;
    const commandedN1 = reverserActive
      ? IDLE_N1_PCT + this.inputs.reverserLeverNorm * (REVERSE_MAX_N1_PCT - IDLE_N1_PCT)
      : IDLE_N1_PCT + this.inputs.throttleNorm * (MAX_N1_PCT - IDLE_N1_PCT);
    const windmillN1 = clamp((this.iasMps * MPS_TO_KT) / 12, 0, 18);
    const targetN1Left = leftRunning ? commandedN1 : windmillN1;
    const targetN1Right = rightRunning ? commandedN1 : windmillN1;
    const stepN1 = (n1: number, target: number): number => {
      const delta = ((target - n1) / N1_TAU_SEC) * dt;
      const limited = clamp(delta, -N1_RATE_LIMIT_PCT_PER_SEC * dt, N1_RATE_LIMIT_PCT_PER_SEC * dt);
      return n1 + limited;
    };
    this.n1LeftPct = stepN1(this.n1LeftPct, targetN1Left);
    this.n1RightPct = stepN1(this.n1RightPct, targetN1Right);
    // Only running engines contribute thrust.
    const thrustOf = (n1: number, running: boolean): number =>
      running ? Math.max(0, (n1 - IDLE_N1_PCT) / (MAX_N1_PCT - IDLE_N1_PCT)) ** 2 : 0;
    const leftThrustFraction = thrustOf(this.n1LeftPct, leftRunning);
    const rightThrustFraction = thrustOf(this.n1RightPct, rightRunning);
    const thrustAsymmetry = leftThrustFraction - rightThrustFraction;
    const thrustFraction = (leftThrustFraction + rightThrustFraction) / 2;
    let thrustN = thrustFraction * MAX_TOTAL_THRUST_N;
    if (reverserActive) thrustN = -thrustN * REVERSE_EFFICIENCY;

    // --- Autopilot: HDG SEL / LOC and V/S / ALT HOLD / G/S, plus TO/GA ---
    let elevator = this.inputs.elevatorNorm;
    let aileron = this.inputs.aileronNorm;
    this.updateApModes();
    if (this.togaActive && !this.onGround) {
      // Go-around: hold the go-around attitude, wings level (spec §22 Phase 3).
      const pitchErr = TOGA_PITCH_DEG - this.pitchDeg;
      elevator = clamp(pitchErr * 0.12, -0.4, 0.8);
      aileron = clamp(-this.rollDeg * 0.08, -0.3, 0.3);
    } else if (this.mcp.autopilotEngaged && !this.onGround) {
      // ---- lateral ----
      const targetHeadingDeg =
        this.apRollMode === 'LOC'
          ? this.localizerInterceptHeadingDeg()
          : this.apRollMode === 'LNAV'
            ? this.lnavHeadingDeg()
            : this.mcp.selHeadingDeg;
      const hdgErr = angleDiffDeg(this.headingDegMag(), targetHeadingDeg);
      const targetBank = clamp(hdgErr * 1.2, -25, 25);
      aileron = clamp((targetBank - this.rollDeg) / 10, -1, 1);

      // ---- vertical ----
      const altErrFt = this.altM * M_TO_FT - this.mcp.selAltitudeFt;
      const selVsFpm = this.mcp.selVerticalSpeedFpm;
      let targetVsFpm: number;
      if (this.apPitchMode === 'GS') {
        targetVsFpm = this.glideslopeTargetVsFpm();
      } else if (this.apPitchMode === 'ALT_HOLD') {
        targetVsFpm = clamp(-altErrFt * 4, -1000, 1000);
      } else if (this.approachArmed && this.radioAltitudeFt() < GS_HOLD_BELOW_FT) {
        // On an armed approach near the ground the autopilot never commands a
        // climb; going around is the crew's decision (TO/GA), not the AP's.
        targetVsFpm = this.glideslopeTargetVsFpm();
      } else if (selVsFpm !== 0) {
        // Outside the capture window the selected V/S is followed with its sign
        // (an MCP V/S of -1000 means descend, whatever the selected altitude is
        // — R-17). Only when no V/S is selected does the model pick a direction.
        targetVsFpm = selVsFpm;
      } else {
        targetVsFpm = altErrFt < 0 ? DEFAULT_AP_CLIMB_FPM : -DEFAULT_AP_CLIMB_FPM;
      }
      const vsErrFpm = targetVsFpm - this.vsMps * MPS_TO_FPM;
      elevator = clamp(vsErrFpm * 0.0006, -0.6, 0.6);
    }

    // --- Attitude dynamics ---
    const iasKt = this.iasMps * MPS_TO_KT;
    if (this.onGround) {
      // Elevator becomes effective as dynamic pressure builds.
      const elevAuthority = clamp((iasKt - 80) / 40, 0, 1);
      const pitchRate = elevator * PITCH_RATE_MAX_DEGPS * elevAuthority;
      this.pitchDeg = clamp(this.pitchDeg + pitchRate * dt, -1, 12);
      // Derotation: nose falls through when unsupported.
      if (elevator < 0.05 && this.pitchDeg > 0) {
        this.pitchDeg = Math.max(0, this.pitchDeg - 2.0 * dt);
      }
      this.rollDeg = 0;
      const steerAuthority = 1 / (1 + (this.iasMps / 15) ** 1.5);
      const yawRate =
        this.inputs.rudderNorm *
        GROUND_STEER_MAX_DEGPS *
        steerAuthority *
        clamp(this.iasMps / 1.5, 0, 1);
      this.headingDegTrue = normalizeDeg360(this.headingDegTrue + yawRate * dt);
    } else {
      // Baseline light bumpiness plus the scenario's turbulence setting
      // (0..1) — at 1.0 the perturbation is several times the baseline (F-02).
      const turbAmplitude = 0.5 + this.turbulence * TURBULENCE_ATTITUDE_GAIN;
      const turbulence = this.iasMps > 15 ? (this.rand() - 0.5) * turbAmplitude : 0;
      const pitchRate = elevator * PITCH_RATE_MAX_DEGPS + turbulence * 0.3;
      this.pitchDeg = clamp(this.pitchDeg + pitchRate * dt, -15, 25);
      const rollRate =
        aileron * ROLL_RATE_MAX_DEGPS -
        this.rollDeg * 0.05 +
        turbulence +
        thrustAsymmetry * ENGINE_ASYMMETRY_ROLL_RATE_DEGPS;
      this.rollDeg = clamp(this.rollDeg + rollRate * dt, -60, 60);
      // Coordinated turn plus asymmetric-thrust yaw and airborne rudder.
      if (this.iasMps > 30) {
        const turnRateDegPs = radToDeg((G_MPS2 * Math.tan(degToRad(this.rollDeg))) / this.iasMps);
        const rudderAuthority = clamp((iasKt - 60) / 80, 0, 1);
        const yawRateDegPs =
          thrustAsymmetry * ENGINE_ASYMMETRY_YAW_RATE_DEGPS +
          this.inputs.rudderNorm * RUDDER_YAW_RATE_MAX_DEGPS * rudderAuthority;
        this.headingDegTrue = normalizeDeg360(
          this.headingDegTrue + (turnRateDegPs + yawRateDegPs) * dt,
        );
      }
    }

    // --- Aerodynamics ---
    const q = 0.5 * RHO_KGPM3 * this.iasMps * this.iasMps;
    const flapNorm = this.flapsActualNorm;
    const weightN = this.massKg * G_MPS2;
    const clMax = CLMAX_CLEAN + CLMAX_PER_FLAP_NORM * flapNorm;
    const cl0 = CL0_CLEAN + CL_PER_FLAP_NORM * flapNorm;

    let cl: number;
    let gammaDeg: number;
    if (this.onGround) {
      // On ground AoA == pitch (flat runway); γ = 0.
      this.aoaDeg = this.pitchDeg;
      cl = clamp(cl0 + CL_ALPHA_PER_DEG * this.aoaDeg, 0, clMax);
      cl -= 0.9 * this.spoilersNorm * cl; // ground spoilers dump lift
      gammaDeg = 0;
    } else {
      // Airborne: required CL for ~1g flight; AoA follows, γ = θ - α.
      const clNeeded = q > 50 ? weightN / (q * WING_AREA_M2) : clMax;
      const clSpoiled = clNeeded + CL_SPOILER_KILL_AIR * this.spoilersNorm; // spoilers force higher AoA
      this.aoaDeg = clamp((clSpoiled - cl0) / CL_ALPHA_PER_DEG, -5, AOA_STALL_DEG);
      cl = clamp(cl0 + CL_ALPHA_PER_DEG * this.aoaDeg, -0.5, clMax);
      let sinkExtraDeg = 0;
      if (clSpoiled > clMax) {
        // Stalled / lift deficit: flight path drops below θ - α_stall.
        sinkExtraDeg = 8 * (clSpoiled / clMax - 1);
      }
      gammaDeg = this.pitchDeg - this.aoaDeg - sinkExtraDeg;
    }

    const cd =
      CD0 +
      K_INDUCED * cl * cl +
      CD_FLAP_FACTOR * Math.pow(flapNorm, 1.5) +
      CD_GEAR * this.gearPositionNorm +
      CD_SPOILER * this.spoilersNorm;
    const dragN = q * WING_AREA_M2 * cd;
    const liftN = q * WING_AREA_M2 * cl;

    // --- Longitudinal acceleration ---
    let accelMps2 = (thrustN - dragN) / this.massKg - G_MPS2 * Math.sin(degToRad(gammaDeg));
    if (this.onGround) {
      const effectiveBrake = this.effectiveBrakeNorm(iasKt);
      const normalForceN = Math.max(0, weightN - liftN);
      const frictionN = (MU_ROLLING + MU_BRAKE_MAX * effectiveBrake) * normalForceN;
      if (this.iasMps > 0.05) {
        accelMps2 -= frictionN / this.massKg;
      } else if (thrustN <= frictionN) {
        accelMps2 = 0;
        this.iasMps = 0;
      }
    }
    this.iasMps = Math.max(0, this.iasMps + accelMps2 * dt);

    // --- RTO autobrake (rejected takeoff) ---
    // Boeing behaviour, NON_CERTIFIED_APPROXIMATION: RTO arms on the ground once
    // takeoff thrust is set, applies maximum braking when the thrust levers are
    // retarded to idle above the arming speed, and disarms at liftoff. It is not
    // a landing autobrake — touchdown must not activate it (R-07).
    if (this.autobrake === 'RTO') {
      if (this.rtoManualOverride) {
        this.rtoArmed = false;
        this.autobrakeActive = false;
      } else if (this.onGround) {
        if (this.inputs.throttleNorm >= RTO_ARM_THROTTLE_NORM) this.rtoArmed = true;
        if (
          this.rtoArmed &&
          !this.autobrakeActive &&
          this.inputs.throttleNorm < RTO_TRIGGER_THROTTLE_NORM &&
          iasKt >= RTO_ARM_SPEED_KT
        ) {
          this.autobrakeActive = true;
        }
      } else {
        this.rtoArmed = false;
        this.autobrakeActive = false;
      }
    }

    // --- Vertical motion ---
    if (this.onGround) {
      this.vsMps = 0;
      this.altM = fieldAltM;
      if (liftN > weightN && this.pitchDeg > 0.5) {
        this.onGround = false;
        this.vsMps = 0.5;
      }
    } else {
      this.vsMps = this.iasMps * Math.sin(degToRad(gammaDeg));
      this.altM += this.vsMps * dt;
      if (this.altM <= fieldAltM && this.vsMps < 0) {
        // Touchdown.
        this.altM = fieldAltM;
        this.onGround = true;
        this.vsMps = 0;
        this.rollDeg = 0;
        if (['1', '2', '3', 'MAX'].includes(this.autobrake)) {
          this.autobrakeActive = true;
        }
      }
    }

    // --- Ground track & position (wind applied to track, not IAS) ---
    // The wind the aircraft is IN: surface blended toward the wind aloft with
    // altitude, plus the seeded gust — the same wind the state reports and the
    // LNAV crab is computed for (F-02: it used to drift by the surface wind at
    // every altitude while LNAV crabbed for the blended one).
    const windNow = this.currentWind();
    const windSpeedNowMps = Math.max(0, windNow.speedKt + this.gustKt) * KT_TO_MPS;
    const windToDeg = normalizeDeg360(windNow.dirDeg + 180);
    const windE = windSpeedNowMps * Math.sin(degToRad(windToDeg));
    const windN = windSpeedNowMps * Math.cos(degToRad(windToDeg));
    const acE = this.iasMps * Math.sin(degToRad(this.headingDegTrue));
    const acN = this.iasMps * Math.cos(degToRad(this.headingDegTrue));
    // On ground the wheels dominate: track = heading, wind ignored.
    const gsE = this.onGround ? acE : acE + windE;
    const gsN = this.onGround ? acN : acN + windN;
    const gsMps = Math.hypot(gsE, gsN);
    const trackDegTrue =
      gsMps > 0.5 ? normalizeDeg360(radToDeg(Math.atan2(gsE, gsN))) : this.headingDegTrue;
    const moved = fromLocalEnuM(this.latDeg, this.lonDeg, gsE * dt, gsN * dt);
    this.latDeg = moved.latDeg;
    this.lonDeg = moved.lonDeg;
    this.lastGsMps = gsMps;
    this.lastTrackDegTrue = trackDegTrue;
  }

  private lastGsMps = 0;
  private lastTrackDegTrue = 0;

  private effectiveBrakeNorm(iasKt: number): number {
    if (this.parkingBrakeSet) return 1;
    let brake = this.inputs.brakeNorm;
    if (
      this.autobrakeActive &&
      this.autobrake !== 'OFF' &&
      this.inputs.throttleNorm < 0.1 &&
      iasKt > 20
    ) {
      brake = Math.max(brake, AUTOBRAKE_BRAKE_NORM[this.autobrake]);
    }
    return clamp(brake, 0, 1);
  }

  private headingDegMag(): number {
    return normalizeDeg360(this.headingDegTrue - this.runway.magneticVariationDeg);
  }

  // ------------------------------------------------------------ autopilot modes

  /**
   * Mode logic (spec §22 Phase 3). Arming the approach lets the autopilot
   * capture the localizer and then the glideslope from real deviations instead
   * of the crew chasing them with the heading and V/S knobs.
   */
  private updateApModes(): void {
    if (this.togaActive) {
      this.apRollMode = null;
      this.apPitchMode = 'TOGA';
      return;
    }
    if (!this.mcp.autopilotEngaged || this.onGround) {
      this.apRollMode = null;
      this.apPitchMode = null;
      return;
    }
    const { locDots, gsDots } = this.computeIls();

    // ---- lateral ----
    if (!this.approachArmed) {
      this.apRollMode =
        this.fms.lnavArmed && this.fms.desiredTrackDegTrue !== null ? 'LNAV' : 'HDG_SEL';
    } else if (this.apRollMode === 'LOC') {
      // stay captured while guidance is usable
      if (locDots === null || Math.abs(locDots) > LOC_LOSS_DOTS) this.apRollMode = 'LOC_ARM';
    } else {
      const courseErrDeg = Math.abs(angleDiffDeg(this.headingDegMag(), this.runway.headingDegMag));
      const capture =
        locDots !== null && Math.abs(locDots) < LOC_CAPTURE_DOTS && courseErrDeg < LOC_CAPTURE_DEG;
      this.apRollMode = capture ? 'LOC' : 'LOC_ARM';
    }

    // ---- vertical ----
    const altErrFt = this.altM * M_TO_FT - this.mcp.selAltitudeFt;
    const raFt = Math.max(0, this.altM - this.runway.elevationFtMsl * FT_TO_M) * M_TO_FT;
    if (this.approachArmed && this.apPitchMode === 'GS') {
      // Close in, the beam is behind the aircraft and drops out — that is the
      // flare region, not a reason to climb back to the MCP altitude.
      const lostBeam = gsDots === null || Math.abs(gsDots) > GS_LOSS_DOTS;
      if (lostBeam && raFt > GS_HOLD_BELOW_FT) this.apPitchMode = 'GS_ARM';
    } else if (this.approachArmed) {
      // the glideslope is only armed once the localizer is captured
      const capture =
        this.apRollMode === 'LOC' && gsDots !== null && Math.abs(gsDots) < GS_CAPTURE_DOTS;
      this.apPitchMode = capture ? 'GS' : 'GS_ARM';
    } else {
      this.apPitchMode = Math.abs(altErrFt) < ALT_CAPTURE_FT ? 'ALT_HOLD' : 'VS';
    }
  }

  /** Height above the runway elevation, in feet. */
  private radioAltitudeFt(): number {
    return Math.max(0, (this.altM - this.runway.elevationFtMsl * FT_TO_M) * M_TO_FT);
  }

  /** Heading that flies the aircraft back onto the localizer course. */
  private localizerInterceptHeadingDeg(): number {
    const { locDots } = this.computeIls();
    const correctionDeg = clamp((locDots ?? 0) * LOC_TRACK_DEG_PER_DOT, -20, 20);
    return normalizeDeg360(this.runway.headingDegMag + correctionDeg);
  }

  /** Descent rate that flies the glidepath, corrected for deviation. */
  private glideslopeTargetVsFpm(): number {
    const { gsDots } = this.computeIls();
    const gsMps = Math.max(30, this.lastGsMps);
    const nominalFpm = -gsMps * Math.tan(degToRad(this.runway.ils.glideslopeDeg)) * MPS_TO_FPM;
    const correctionFpm = clamp((gsDots ?? 0) * GS_TRACK_FPM_PER_DOT, -400, 400);
    return clamp(nominalFpm + correctionFpm, -1200, 200);
  }

  // ------------------------------------------------------------------ failures

  /**
   * Failures are expressed through the systems model, so the annunciator,
   * checklists and debrief see them without a second code path (M5 D5).
   */
  private applyFailure(failure: FailureKind): CommandResult {
    if (this.failures.has(failure)) return { ok: true };
    const s = this.systems.state;
    this.failures.add(failure);
    switch (failure) {
      case 'engine_1_flameout': {
        const engine = { ...s.engines.left };
        const generatorOn = s.electrical.gen1On;
        this.failureRestores.set(failure, () =>
          this.systems.restoreEngine('left', engine, generatorOn),
        );
        this.systems.failEngine('left');
        break;
      }
      case 'engine_2_flameout': {
        const engine = { ...s.engines.right };
        const generatorOn = s.electrical.gen2On;
        this.failureRestores.set(failure, () =>
          this.systems.restoreEngine('right', engine, generatorOn),
        );
        this.systems.failEngine('right');
        break;
      }
      case 'generator_1': {
        const previous = s.electrical.gen1On;
        this.failureRestores.set(failure, () => void this.systems.applySwitch('gen1', previous));
        this.systems.applySwitch('gen1', false);
        break;
      }
      case 'generator_2': {
        const previous = s.electrical.gen2On;
        this.failureRestores.set(failure, () => void this.systems.applySwitch('gen2', previous));
        this.systems.applySwitch('gen2', false);
        break;
      }
      case 'hydraulic_a': {
        const engPump = s.hydraulic.engPump1On;
        const elecPump = s.hydraulic.elecPump2On;
        this.failureRestores.set(failure, () => {
          this.systems.applySwitch('hyd_pump_eng1', engPump);
          this.systems.applySwitch('hyd_pump_elec2', elecPump);
        });
        this.systems.applySwitch('hyd_pump_eng1', false);
        this.systems.applySwitch('hyd_pump_elec2', false);
        break;
      }
      case 'hydraulic_b': {
        const engPump = s.hydraulic.engPump2On;
        const elecPump = s.hydraulic.elecPump1On;
        this.failureRestores.set(failure, () => {
          this.systems.applySwitch('hyd_pump_eng2', engPump);
          this.systems.applySwitch('hyd_pump_elec1', elecPump);
        });
        this.systems.applySwitch('hyd_pump_eng2', false);
        this.systems.applySwitch('hyd_pump_elec1', false);
        break;
      }
    }
    return { ok: true };
  }

  /** Clear instructor failures and restore each affected target to its prior state. */
  private clearFailures(): CommandResult {
    for (const restore of [...this.failureRestores.values()].reverse()) restore();
    this.failureRestores.clear();
    this.failures.clear();
    return { ok: true };
  }

  private failureBlockingSwitch(id: SystemSwitch): FailureKind | null {
    const blocked: Partial<Record<SystemSwitch, FailureKind>> = {
      start_lever_left: 'engine_1_flameout',
      start_lever_right: 'engine_2_flameout',
      gen1: 'generator_1',
      gen2: 'generator_2',
      hyd_pump_eng1: 'hydraulic_a',
      hyd_pump_elec2: 'hydraulic_a',
      hyd_pump_eng2: 'hydraulic_b',
      hyd_pump_elec1: 'hydraulic_b',
    };
    const failure = blocked[id];
    return failure && this.failures.has(failure) ? failure : null;
  }

  // ----------------------------------------------------------------- route/FMS

  /** Follow the active leg, sequencing when the fix goes behind (M5 T2). */
  private updateFms(): void {
    const legs = this.fms.legs;
    if (legs.length === 0 || this.fms.activeLegIndex >= legs.length) {
      this.fms = {
        ...this.fms,
        distanceToWaypointNm: null,
        crossTrackNm: null,
        desiredTrackDegTrue: null,
      };
      return;
    }
    const index = this.fms.activeLegIndex;
    const leg = legs[index]!;
    const previous =
      index === 0
        ? (this.fmsOrigin ?? { latDeg: this.latDeg, lonDeg: this.lonDeg })
        : {
            latDeg: legs[index - 1]!.waypoint.latDeg,
            lonDeg: legs[index - 1]!.waypoint.lonDeg,
          };
    const tracking = trackLeg(leg, previous, { latDeg: this.latDeg, lonDeg: this.lonDeg });
    // Sequence on the fix OR once it is behind the aircraft — passing a mile
    // wide of a waypoint must not leave the route chasing it forever.
    if (tracking.sequenced && index + 1 < legs.length) {
      this.fms = { ...this.fms, activeLegIndex: index + 1 };
      return;
    }
    this.fms = {
      ...this.fms,
      distanceToWaypointNm: tracking.distanceToWaypointNm,
      crossTrackNm: tracking.crossTrackNm,
      desiredTrackDegTrue: tracking.desiredTrackDegTrue,
    };
  }

  /** Heading that makes good the FMS desired track, allowing for wind. */
  private lnavHeadingDeg(): number {
    const desiredTrue = this.fms.desiredTrackDegTrue;
    if (desiredTrue === null) return this.mcp.selHeadingDeg;
    const wind = this.currentWind();
    const headingTrue = headingForTrack(
      desiredTrue,
      this.iasMps * MPS_TO_KT,
      wind.dirDeg,
      wind.speedKt,
    );
    return normalizeDeg360(headingTrue - this.runway.magneticVariationDeg);
  }

  /** Steady wind at the current altitude, blended surface → aloft. */
  private currentWind(): { dirDeg: number; speedKt: number } {
    const altAglFt = Math.max(0, (this.altM - this.runway.elevationFtMsl * FT_TO_M) * M_TO_FT);
    const blend = clamp(altAglFt / WIND_ALOFT_BLEND_FT, 0, 1);
    const surfaceKt = this.windSpeedMps * MPS_TO_KT;
    return {
      dirDeg: normalizeDeg360(
        this.windDirDeg + angleDiffDeg(this.windAloftDirDeg, this.windDirDeg) * -blend,
      ),
      speedKt: surfaceKt + (this.windAloftSpeedKt - surfaceKt) * blend,
    };
  }

  // ---------------------------------------------------------------- ILS geometry

  /**
   * Geometric localizer/glideslope deviations against the scenario runway.
   * Sign conventions per shared schema: loc + = fly right, gs + = fly up.
   */
  private computeIls(): { locDots: number | null; gsDots: number | null } {
    const rwy = this.runway;
    const { eastM, northM } = toLocalEnuM(
      rwy.thresholdLatDeg,
      rwy.thresholdLonDeg,
      this.latDeg,
      this.lonDeg,
    );
    // Runway frame: x along approach course (course = runway heading), origin threshold.
    const courseRad = degToRad(rwy.headingDegTrue);
    const alongM = eastM * Math.sin(courseRad) + northM * Math.cos(courseRad);
    const crossM = eastM * Math.cos(courseRad) - northM * Math.sin(courseRad); // + = right of course
    const lengthM = rwy.lengthFt * FT_TO_M;

    // Localizer antenna at the stop end.
    const approachingDistM = -alongM; // >0 when on approach side of threshold
    if (approachingDistM > 25 * 1852 || alongM > lengthM + 500) {
      return { locDots: null, gsDots: null };
    }
    const angleOffDeg = radToDeg(Math.atan2(crossM, Math.max(200, lengthM - alongM)));
    if (Math.abs(angleOffDeg) > 35) return { locDots: null, gsDots: null };
    const locDotsPerDeg = 2 / rwy.ils.locFullScaleDeg;
    const locDots = clamp(-angleOffDeg * locDotsPerDeg, -2.5, 2.5);

    // Glideslope antenna ~300 m past threshold. The beam is narrow: only
    // valid near the localizer course (prevents bogus capture on base leg).
    const gsAntennaAlongM = 300;
    const horizDistM = Math.hypot(alongM - gsAntennaAlongM, crossM);
    const heightM = this.altM - rwy.elevationFtMsl * FT_TO_M;
    let gsDots: number | null = null;
    if (
      approachingDistM > -gsAntennaAlongM &&
      horizDistM > 300 &&
      horizDistM < 10 * 1852 &&
      Math.abs(angleOffDeg) < 10
    ) {
      const elevAngleDeg = radToDeg(Math.atan2(heightM, horizDistM));
      const gsDotsPerDeg = 2 / rwy.ils.gsFullScaleDeg;
      gsDots = clamp((rwy.ils.glideslopeDeg - elevAngleDeg) * gsDotsPerDeg, -2.5, 2.5);
    }
    return { locDots, gsDots };
  }

  // ---------------------------------------------------------------- snapshot

  snapshot(timestampMs: number): AircraftState {
    const rwy = this.runway;
    const fieldAltM = rwy.elevationFtMsl * FT_TO_M;
    const ils = this.computeIls();
    const detent = this.flapHandleDetent;
    return {
      timestampMs,
      simTimeSec: this.simTimeSec,
      position: {
        latDeg: this.latDeg,
        lonDeg: this.lonDeg,
        altitudeFtMsl: this.altM * M_TO_FT,
        radioAltitudeFt: Math.max(0, (this.altM - fieldAltM) * M_TO_FT),
      },
      attitude: {
        pitchDeg: this.pitchDeg,
        rollDeg: this.rollDeg,
        headingDegMag: this.headingDegMag(),
        groundTrackDegMag: normalizeDeg360(this.lastTrackDegTrue - rwy.magneticVariationDeg),
        aoaDeg: this.onGround ? null : this.aoaDeg,
      },
      speeds: {
        iasKt: this.iasMps * MPS_TO_KT,
        gsKt: this.lastGsMps * MPS_TO_KT,
        verticalSpeedFpm: this.vsMps * MPS_TO_FPM,
      },
      weightOnWheels: this.onGround,
      engines: {
        left: {
          n1Pct: this.n1LeftPct,
          throttleLeverNorm: this.inputs.throttleNorm,
          reverserNorm: this.inputs.reverserLeverNorm,
        },
        right: {
          n1Pct: this.n1RightPct,
          throttleLeverNorm: this.inputs.throttleNorm,
          reverserNorm: this.inputs.reverserLeverNorm,
        },
      },
      controls: {
        flapHandleDetent: detent,
        flapsActualNorm: this.flapsActualNorm,
        gearLeverDown: this.gearLeverDown,
        gearPositionNorm: this.gearPositionNorm,
        speedbrakeLeverNorm: this.speedbrakeLeverNorm,
        speedbrakeArmed: this.speedbrakeArmed,
        spoilersDeployedNorm: this.spoilersNorm,
        parkingBrakeSet: this.parkingBrakeSet,
        brakeNorm: this.effectiveBrakeNorm(this.iasMps * MPS_TO_KT),
        autobrake: this.autobrake,
      },
      mcp: {
        ...this.mcp,
        approachArmed: this.approachArmed,
        rollMode: this.apRollMode,
        pitchMode: this.apPitchMode,
      },
      nav: {
        ilsTuned: true,
        locDeviationDots: ils.locDots,
        gsDeviationDots: ils.gsDots,
      },
      lights: { ...this.lights },
      systems: this.systems.state,
      fms: this.fms,
      weather: {
        windDirDeg: this.currentWind().dirDeg,
        windSpeedKt: this.currentWind().speedKt,
        gustKt: this.gustKt,
        visibilityM: this.visibilityM,
        turbulence: this.turbulence,
      },
      activeFailures: [...this.failures],
      airport: { icao: rwy.airportIcao, runwayId: rwy.runwayId },
    };
  }
}

/** Ordered flap detents helper re-export for UIs. */
export { FLAP_DETENTS };
