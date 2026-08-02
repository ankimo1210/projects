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
  normalizeDeg360,
  radToDeg,
  toLocalEnuM,
  fromLocalEnuM,
  type AircraftCommand,
  type AircraftState,
  type AutobrakeSetting,
  type CommandResult,
  type FlapDetent,
  type RunwayData,
  type ScenarioInitialState,
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

/**
 * RTO autobrake arming/trigger thresholds. NON_CERTIFIED_APPROXIMATION —
 * representative of published 737 behaviour, not taken from an FCOM.
 */
const RTO_ARM_THROTTLE_NORM = 0.6;
const RTO_TRIGGER_THROTTLE_NORM = 0.05;
const RTO_ARM_SPEED_KT = 60;
/** V/S the simple autopilot uses when the MCP V/S window is zeroed. */
const DEFAULT_AP_CLIMB_FPM = 1800;

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
  /** Sub-step remainder carried between `step()` calls. */
  private stepCarrySec = 0;
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
    if (config.startAt === 'holding_point') {
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
    this.altM = fieldAltM;
    this.iasMps = 0;
    this.pitchDeg = 0;
    this.rollDeg = 0;
    this.vsMps = 0;
    this.onGround = true;
    this.aoaDeg = 0;

    this.n1LeftPct = IDLE_N1_PCT;
    this.n1RightPct = IDLE_N1_PCT;
    this.flapHandleDetent = config.flapDetent;
    this.flapsActualNorm = flapDetentToNorm(config.flapDetent);
    this.gearLeverDown = true;
    this.gearPositionNorm = 1;
    this.speedbrakeLeverNorm = 0;
    this.speedbrakeArmed = false;
    this.spoilersNorm = 0;
    this.parkingBrakeSet = config.parkingBrakeSet;
    this.autobrake = 'OFF';
    this.autobrakeActive = false;
    this.rtoArmed = false;
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
        if (cmd.valueNorm > 0.6) this.autobrakeActive = false; // manual override disarms
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
      case 'set_light':
        this.lights[cmd.light] = cmd.on;
        return { ok: true };
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
    const flapTargetNorm = flapDetentToNorm(this.flapHandleDetent);
    const flapRate = dt / FLAP_FULL_TRAVEL_SEC;
    this.flapsActualNorm += clamp(flapTargetNorm - this.flapsActualNorm, -flapRate, flapRate);

    const gearTarget = this.gearLeverDown ? 1 : 0;
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
    const spoilerTarget = this.speedbrakeLeverNorm;
    const spoilerRate = dt / SPOILER_TRAVEL_SEC;
    this.spoilersNorm += clamp(spoilerTarget - this.spoilersNorm, -spoilerRate, spoilerRate);

    // --- Engines ---
    const reverserActive = this.onGround && this.inputs.reverserLeverNorm > 0.02;
    const targetN1 = reverserActive
      ? IDLE_N1_PCT + this.inputs.reverserLeverNorm * (REVERSE_MAX_N1_PCT - IDLE_N1_PCT)
      : IDLE_N1_PCT + this.inputs.throttleNorm * (MAX_N1_PCT - IDLE_N1_PCT);
    const stepN1 = (n1: number): number => {
      const delta = ((targetN1 - n1) / N1_TAU_SEC) * dt;
      const limited = clamp(delta, -N1_RATE_LIMIT_PCT_PER_SEC * dt, N1_RATE_LIMIT_PCT_PER_SEC * dt);
      return n1 + limited;
    };
    this.n1LeftPct = stepN1(this.n1LeftPct);
    this.n1RightPct = stepN1(this.n1RightPct);
    const n1Avg = (this.n1LeftPct + this.n1RightPct) / 2;
    const thrustFraction = Math.max(0, (n1Avg - IDLE_N1_PCT) / (MAX_N1_PCT - IDLE_N1_PCT)) ** 2;
    let thrustN = thrustFraction * MAX_TOTAL_THRUST_N;
    if (reverserActive) thrustN = -thrustN * REVERSE_EFFICIENCY;

    // --- Autopilot (simple HDG/ALT-VS hold; no autothrottle in M1) ---
    let elevator = this.inputs.elevatorNorm;
    let aileron = this.inputs.aileronNorm;
    if (this.mcp.autopilotEngaged && !this.onGround) {
      const hdgErr = angleDiffDeg(this.headingDegMag(), this.mcp.selHeadingDeg);
      const targetBank = clamp(hdgErr * 1.2, -25, 25);
      aileron = clamp((targetBank - this.rollDeg) / 10, -1, 1);
      const altErrFt = this.altM * M_TO_FT - this.mcp.selAltitudeFt;
      const capture = Math.abs(altErrFt) < 400;
      // Outside the capture window the selected V/S is followed with its sign
      // (an MCP V/S of -1000 means descend, whatever the selected altitude is —
      // R-17). Only when no V/S is selected does the model pick the direction.
      const selVsFpm = this.mcp.selVerticalSpeedFpm;
      const targetVsFpm = capture
        ? clamp(-altErrFt * 4, -1000, 1000)
        : selVsFpm !== 0
          ? selVsFpm
          : altErrFt < 0
            ? DEFAULT_AP_CLIMB_FPM
            : -DEFAULT_AP_CLIMB_FPM;
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
      const turbulence = this.iasMps > 15 ? (this.rand() - 0.5) * 0.5 : 0;
      const pitchRate = elevator * PITCH_RATE_MAX_DEGPS + turbulence * 0.3;
      this.pitchDeg = clamp(this.pitchDeg + pitchRate * dt, -15, 25);
      const rollRate = aileron * ROLL_RATE_MAX_DEGPS - this.rollDeg * 0.05 + turbulence;
      this.rollDeg = clamp(this.rollDeg + rollRate * dt, -60, 60);
      // Coordinated turn: ψ̇ = g·tanφ / V
      if (this.iasMps > 30) {
        const turnRateDegPs = radToDeg((G_MPS2 * Math.tan(degToRad(this.rollDeg))) / this.iasMps);
        this.headingDegTrue = normalizeDeg360(this.headingDegTrue + turnRateDegPs * dt);
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
      if (this.onGround) {
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
    const windToDeg = normalizeDeg360(this.windDirDeg + 180);
    const windE = this.windSpeedMps * Math.sin(degToRad(windToDeg));
    const windN = this.windSpeedMps * Math.cos(degToRad(windToDeg));
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
      mcp: { ...this.mcp },
      nav: {
        ilsTuned: true,
        locDeviationDots: ils.locDots,
        gsDeviationDots: ils.gsDots,
      },
      lights: { ...this.lights },
      airport: { icao: rwy.airportIcao, runwayId: rwy.runwayId },
    };
  }
}

/** Ordered flap detents helper re-export for UIs. */
export { FLAP_DETENTS };
