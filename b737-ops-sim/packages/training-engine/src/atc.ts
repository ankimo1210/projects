import {
  angleDiffDeg,
  getTaxiNetwork,
  normalizeDeg360,
  type AircraftState,
  type RunwayData,
} from '@b737/shared';
import { transcriptId, type ReadbackOption, type TranscriptEntry } from './transcript.js';

/**
 * Deterministic ATC layer (spec §13): clearances and vectors are produced by
 * this state machine from aircraft state — a voice/LLM layer may later
 * re-phrase them but never decides them. Text presentation is built in.
 */

export type AtcPhase =
  | 'awaiting_taxi_request'
  | 'taxi_out'
  | 'awaiting_takeoff_request'
  | 'takeoff_clearance_issued'
  | 'departure'
  | 'vector_crosswind'
  | 'vector_downwind'
  | 'vector_base'
  | 'vector_final'
  | 'cleared_approach'
  | 'cleared_to_land'
  | 'rollout'
  | 'runway_exited'
  | 'taxi_in'
  | 'go_around';

export interface AtcInstruction {
  id: string;
  transcriptEntry: TranscriptEntry;
  /** Flags applied to the scenario when read back correctly (or immediately if no readback expected). */
  flagsOnAccept: Record<string, boolean | number>;
  targetHeadingDeg?: number;
  targetAltitudeFt?: number;
}

export interface AtcEventSink {
  (instruction: AtcInstruction): void;
}

export interface AtcStats {
  readbacksTotal: number;
  readbacksCorrect: number;
}

interface VectorLeg {
  atcPhase: AtcPhase;
  headingDeg: number;
  altitudeFt?: number;
  say: string;
  /** Advance when heading captured and this much time in the leg elapsed. */
  minLegSec: number;
}

export class AtcController {
  phase: AtcPhase;
  readonly stats: AtcStats = { readbacksTotal: 0, readbacksCorrect: 0 };
  private pendingInstruction: AtcInstruction | null = null;
  private legStartedAtSec: number | null = null;
  private readonly legs: VectorLeg[];
  private legIndex = 0;
  private callsign = 'Boeing 737';

  constructor(
    private readonly runway: RunwayData,
    /** Surface wind actually in force in the scenario (spec §13). */
    private readonly wind: { dirDeg: number; speedKt: number } = { dirDeg: 0, speedKt: 0 },
    /** Where the flight joins the ATC sequence (depends on the scenario start). */
    initialPhase: AtcPhase = 'awaiting_takeoff_request',
  ) {
    this.phase = initialPhase;
    const rwyHdg = Math.round(runway.headingDegMag);
    // Right-hand pattern back to the ILS (KSFO 28R: right turns over the bay).
    this.legs = [
      {
        atcPhase: 'vector_crosswind',
        headingDeg: norm(rwyHdg + 90),
        say: `turn right heading ${fmtHdg(norm(rwyHdg + 90))}`,
        minLegSec: 50,
      },
      {
        atcPhase: 'vector_downwind',
        headingDeg: norm(rwyHdg + 180),
        say: `turn right heading ${fmtHdg(norm(rwyHdg + 180))}`,
        minLegSec: 130,
      },
      {
        atcPhase: 'vector_base',
        headingDeg: norm(rwyHdg + 270),
        altitudeFt: 1800,
        say: `turn right heading ${fmtHdg(norm(rwyHdg + 270))}, descend and maintain 1,800`,
        minLegSec: 70,
      },
      {
        atcPhase: 'vector_final',
        headingDeg: norm(rwyHdg + 330),
        say: `turn right heading ${fmtHdg(norm(rwyHdg + 330))}, maintain 1,800 until established, cleared ILS runway ${runway.runwayId} approach`,
        minLegSec: 0,
      },
    ];
  }

  /**
   * Surface wind as ATC reads it. Scenario wind is degrees TRUE (it drives the
   * physics); a controller reads magnetic, so convert here (F-07).
   */
  private windPhrase(): string {
    if (this.wind.speedKt < 3) return 'wind calm';
    const magDeg = normalizeDeg360(this.wind.dirDeg - this.runway.magneticVariationDeg);
    const dir = String(Math.round(magDeg / 10) * 10).padStart(3, '0');
    return `wind ${dir} at ${Math.round(this.wind.speedKt)}`;
  }

  /**
   * User keys the mic for a taxi clearance (spec §22 Phase 3 ground control).
   * The route is read from the taxi network so the clearance names taxiways
   * that actually exist.
   */
  requestTaxiClearance(state: AircraftState): AtcInstruction | TranscriptEntry {
    if (this.phase !== 'awaiting_taxi_request') {
      return {
        id: transcriptId('atc'),
        simTimeSec: state.simTimeSec,
        speaker: 'atc',
        message: `${this.callsign}, standby.`,
      };
    }
    this.phase = 'taxi_out';
    const rwy = this.runway.runwayId;
    const via = this.taxiRoute();
    return this.makeInstruction(
      state.simTimeSec,
      `${this.callsign}, ground, taxi to runway ${rwy} via ${via}, hold short of runway ${rwy}.`,
      { taxiClearanceReceived: true },
      [
        {
          id: 'correct',
          text: `Taxi to runway ${rwy} via ${via}, hold short runway ${rwy}, ${this.callsign}.`,
          correct: true,
        },
        {
          id: 'cross',
          text: `Taxi to runway ${rwy}, cleared to cross, ${this.callsign}.`,
          correct: false,
        },
        { id: 'roger', text: 'Roger.', correct: false },
      ],
    );
  }

  /**
   * The crew announces a go-around. ATC re-sequences them onto the pattern —
   * without this the first officer could call for something unflyable
   * (docs/REVIEW_RESPONSE.md).
   */
  announceGoAround(state: AircraftState): AtcInstruction {
    this.phase = 'go_around';
    const hdg = Math.round(this.runway.headingDegMag);
    return this.makeInstruction(
      state.simTimeSec,
      `${this.callsign}, roger, go around, fly runway heading, climb and maintain 3,000, expect vectors for another approach.`,
      {
        goAroundInstructionGiven: true,
        landingClearanceReceived: false,
        atcTargetHeadingDeg: hdg,
        atcTargetAltitudeFt: 3000,
      },
      [
        {
          id: 'correct',
          text: `Runway heading, climb and maintain 3,000, ${this.callsign}.`,
          correct: true,
        },
        { id: 'continue', text: `Continuing the approach, ${this.callsign}.`, correct: false },
        { id: 'roger', text: 'Roger.', correct: false },
      ],
      { targetHeadingDeg: hdg, targetAltitudeFt: 3000 },
    );
  }

  /** Taxi route from the stand to the runway, as ATC would read it. */
  private taxiRoute(): string {
    const network = getTaxiNetwork(this.runway.airportIcao, this.runway.runwayId);
    if (!network) return 'the parallel taxiway';
    const labels = [...new Set(network.segments.map((s) => s.label))].filter(
      (l) => l !== 'apron' && !l.startsWith('E'),
    );
    return labels.join(', ');
  }

  /** User keys the mic to request takeoff clearance. */
  requestTakeoffClearance(state: AircraftState): AtcInstruction | TranscriptEntry {
    if (this.phase !== 'awaiting_takeoff_request') {
      return {
        id: transcriptId('atc'),
        simTimeSec: state.simTimeSec,
        speaker: 'atc',
        message: `${this.callsign}, standby.`,
      };
    }
    this.phase = 'takeoff_clearance_issued';
    const rwy = this.runway.runwayId;
    const instruction = this.makeInstruction(
      state.simTimeSec,
      `${this.callsign}, ${this.windPhrase()}, runway ${rwy}, cleared for takeoff.`,
      { takeoffClearanceReceived: true },
      [
        {
          id: 'correct',
          text: `Cleared for takeoff runway ${rwy}, ${this.callsign}.`,
          correct: true,
        },
        { id: 'lineup', text: `Line up and wait runway ${rwy}, ${this.callsign}.`, correct: false },
        { id: 'roger', text: 'Roger.', correct: false },
      ],
    );
    return instruction;
  }

  /** Drive time/state-based ATC behavior. Returns new instructions. */
  update(state: AircraftState, scenarioPhaseId: string): AtcInstruction[] {
    const out: AtcInstruction[] = [];
    const t = state.simTimeSec;
    const ra = state.position.radioAltitudeFt;

    switch (this.phase) {
      case 'takeoff_clearance_issued': {
        if (!state.weightOnWheels && ra > 300) {
          this.phase = 'departure';
          out.push(
            this.makeInstruction(
              t,
              `${this.callsign}, fly runway heading, climb and maintain 3,000.`,
              {
                departureInstructionGiven: true,
                atcTargetHeadingDeg: Math.round(this.runway.headingDegMag),
                atcTargetAltitudeFt: 3000,
              },
              [
                {
                  id: 'correct',
                  text: `Runway heading, climb and maintain 3,000, ${this.callsign}.`,
                  correct: true,
                },
                {
                  id: 'wrong_alt',
                  text: `Climb and maintain 13,000, ${this.callsign}.`,
                  correct: false,
                },
                { id: 'roger', text: 'Roger.', correct: false },
              ],
              { targetHeadingDeg: Math.round(this.runway.headingDegMag), targetAltitudeFt: 3000 },
            ),
          );
        }
        return out;
      }
      case 'departure': {
        // Start vectors once through ~1,500 ft AGL.
        if (ra > 1500) {
          this.phase = this.legs[0]!.atcPhase;
          this.legIndex = 0;
          this.legStartedAtSec = t;
          out.push(this.legInstruction(t, this.legs[0]!));
        }
        return out;
      }
      case 'vector_crosswind':
      case 'vector_downwind':
      case 'vector_base': {
        const leg = this.legs[this.legIndex]!;
        const captured = Math.abs(angleDiffDeg(state.attitude.headingDegMag, leg.headingDeg)) < 15;
        if (
          this.legStartedAtSec !== null &&
          captured &&
          t - this.legStartedAtSec >= leg.minLegSec
        ) {
          this.legIndex += 1;
          const next = this.legs[this.legIndex]!;
          this.phase = next.atcPhase;
          this.legStartedAtSec = t;
          out.push(this.legInstruction(t, next));
          if (next.atcPhase === 'vector_final') this.phase = 'cleared_approach';
        }
        return out;
      }
      case 'cleared_approach': {
        // Landing clearance once established inbound and inside ~6 NM (RA proxy).
        const established =
          state.nav.locDeviationDots !== null &&
          Math.abs(state.nav.locDeviationDots) < 1 &&
          Math.abs(angleDiffDeg(state.attitude.headingDegMag, this.runway.headingDegMag)) < 25;
        if (established && ra < 2200) {
          this.phase = 'cleared_to_land';
          out.push(
            this.makeInstruction(
              t,
              `${this.callsign}, ${this.windPhrase()}, runway ${this.runway.runwayId}, cleared to land.`,
              { landingClearanceReceived: true },
              [
                {
                  id: 'correct',
                  text: `Cleared to land runway ${this.runway.runwayId}, ${this.callsign}.`,
                  correct: true,
                },
                { id: 'option', text: `Cleared for the option, ${this.callsign}.`, correct: false },
                { id: 'roger', text: 'Roger.', correct: false },
              ],
            ),
          );
        }
        return out;
      }
      case 'cleared_to_land': {
        if (state.weightOnWheels && state.speeds.gsKt < 45 && scenarioPhaseId !== 'debrief') {
          this.phase = 'rollout';
          out.push(
            this.makeInstruction(
              t,
              `${this.callsign}, exit the runway when able, then contact ground.`,
              { runwayExitInstructionGiven: true },
              [
                {
                  id: 'correct',
                  text: `Exit when able, to ground, ${this.callsign}.`,
                  correct: true,
                },
                { id: 'holdshort', text: `Hold short, ${this.callsign}.`, correct: false },
              ],
            ),
          );
        }
        return out;
      }
      case 'taxi_out': {
        // Geometry decides when the aircraft is holding short; ATC only reacts.
        if (scenarioPhaseId === 'hold_short' && state.speeds.gsKt < 5) {
          this.phase = 'awaiting_takeoff_request';
          out.push(
            this.makeInstruction(
              t,
              `${this.callsign}, hold short of runway ${this.runway.runwayId}, contact tower on 120.5.`,
              { towerHandoffGiven: true },
              [
                {
                  id: 'correct',
                  text: `Hold short runway ${this.runway.runwayId}, over to tower, ${this.callsign}.`,
                  correct: true,
                },
                {
                  id: 'lineup',
                  text: `Lining up runway ${this.runway.runwayId}, ${this.callsign}.`,
                  correct: false,
                },
              ],
            ),
          );
        }
        return out;
      }
      case 'go_around': {
        // Re-sequence: rejoin the pattern at the downwind leg.
        if (!state.weightOnWheels && ra > 1500) {
          this.legIndex = 1;
          const leg = this.legs[this.legIndex]!;
          this.phase = leg.atcPhase;
          this.legStartedAtSec = t;
          out.push(this.legInstruction(t, leg));
        }
        return out;
      }
      case 'rollout': {
        if (scenarioPhaseId === 'runway_exit') {
          this.phase = 'taxi_in';
          const stand = getTaxiNetwork(this.runway.airportIcao, this.runway.runwayId)?.stands[0];
          const standId = stand?.id ?? 'the ramp';
          out.push(
            this.makeInstruction(
              t,
              `${this.callsign}, ground, taxi to stand ${standId} via ${this.taxiRoute()}.`,
              { taxiInClearanceReceived: true },
              [
                {
                  id: 'correct',
                  text: `Taxi to stand ${standId} via ${this.taxiRoute()}, ${this.callsign}.`,
                  correct: true,
                },
                { id: 'roger', text: 'Roger.', correct: false },
              ],
            ),
          );
        }
        return out;
      }
      case 'awaiting_taxi_request':
      case 'taxi_in':
      case 'awaiting_takeoff_request':
      case 'runway_exited':
        return out;
      default:
        return out;
    }
  }

  /** User selects a readback option for the pending instruction. */
  handleReadback(
    instruction: AtcInstruction,
    optionId: string,
    state: AircraftState,
  ): { correct: boolean; followUps: TranscriptEntry[]; flags: Record<string, boolean | number> } {
    const option = instruction.transcriptEntry.expectedResponse?.options.find(
      (o) => o.id === optionId,
    );
    const correct = option?.correct ?? false;
    this.stats.readbacksTotal += 1;
    if (correct) this.stats.readbacksCorrect += 1;
    if (correct && this.pendingInstruction?.id === instruction.id) this.pendingInstruction = null;
    const followUps: TranscriptEntry[] = [];
    if (!correct) {
      // "Negative — read back" has to be answerable, or the crew is stuck with
      // a controller waiting for a correction they cannot give (R-20).
      followUps.push({
        id: transcriptId('atc'),
        simTimeSec: state.simTimeSec,
        speaker: 'atc',
        message: `${this.callsign}, negative — read back: ${instruction.transcriptEntry.message}`,
        relatedEventId: instruction.id,
        expectedResponse: instruction.transcriptEntry.expectedResponse,
      });
    }
    // Operational flags apply even on an imperfect readback (the clearance was
    // issued); readback quality is scored separately in the debrief.
    return { correct, followUps, flags: instruction.flagsOnAccept };
  }

  private legInstruction(simTimeSec: number, leg: VectorLeg): AtcInstruction {
    const flags: Record<string, boolean | number> = {
      atcTargetHeadingDeg: leg.headingDeg,
    };
    if (leg.altitudeFt) flags.atcTargetAltitudeFt = leg.altitudeFt;
    if (leg.atcPhase === 'vector_final') flags.approachClearanceReceived = true;
    return this.makeInstruction(
      simTimeSec,
      `${this.callsign}, ${leg.say}.`,
      flags,
      [
        { id: 'correct', text: `${capitalize(leg.say)}, ${this.callsign}.`, correct: true },
        { id: 'roger', text: 'Roger.', correct: false },
      ],
      { targetHeadingDeg: leg.headingDeg, targetAltitudeFt: leg.altitudeFt },
    );
  }

  private makeInstruction(
    simTimeSec: number,
    message: string,
    flagsOnAccept: Record<string, boolean | number>,
    options: ReadbackOption[],
    targets: { targetHeadingDeg?: number; targetAltitudeFt?: number } = {},
  ): AtcInstruction {
    const entry: TranscriptEntry = {
      id: transcriptId('atc'),
      simTimeSec,
      speaker: 'atc',
      message,
      expectedResponse: { kind: 'atc_readback', options },
    };
    const instruction: AtcInstruction = {
      id: entry.id,
      transcriptEntry: entry,
      flagsOnAccept,
      ...targets,
    };
    this.pendingInstruction = instruction;
    return instruction;
  }
}

function norm(deg: number): number {
  return ((deg % 360) + 360) % 360;
}

function fmtHdg(deg: number): string {
  return String(Math.round(deg)).padStart(3, '0');
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
