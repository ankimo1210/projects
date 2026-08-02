import { vSpeedsForWeight, type AircraftState, type VSpeeds } from '@b737/shared';
import type { ScenarioEvent } from '@b737/scenario-engine';
import { transcriptId, type TranscriptEntry } from './transcript.js';

/**
 * Deterministic first officer acting as Pilot Monitoring (spec §12).
 * Every callout below is rule-driven from aircraft state / scenario events —
 * no language model is involved in deciding whether a condition is met.
 */

export interface FirstOfficerOptions {
  grossWeightLb: number;
  /** Phases in which takeoff speed callouts arm. */
  takeoffPhaseIds?: string[];
  approachPhaseIds?: string[];
}

interface PendingExpectation {
  transcriptEntryId: string;
  kind: 'gear_up_after_positive_rate';
  sinceSimTimeSec: number;
}

const APPROACH_ALT_CALLOUTS_FT = [1000, 500, 100, 50, 40, 30, 20, 10] as const;
/** Climb must persist this long before "Positive rate" is called. */
const POSITIVE_RATE_CONFIRM_SEC = 0.3;

export class FirstOfficer {
  readonly vSpeeds: VSpeeds;
  private saidTakeoff = new Set<'80kt' | 'v1' | 'rotate'>();
  private saidApproachAlt = new Set<number>();
  private saidPositiveRate = false;
  private saidGearReminder = false;
  private unstableSinceSec: number | null = null;
  private saidGoAround = false;
  private pending: PendingExpectation | null = null;
  private lastRaFt = 0;
  private climbingSinceSec: number | null = null;
  private readonly takeoffPhases: Set<string>;
  private readonly approachPhases: Set<string>;

  constructor(options: FirstOfficerOptions) {
    this.vSpeeds = vSpeedsForWeight(options.grossWeightLb);
    this.takeoffPhases = new Set(options.takeoffPhaseIds ?? ['takeoff_roll', 'rotation']);
    this.approachPhases = new Set(options.approachPhaseIds ?? ['final_approach', 'landing']);
  }

  /** Feed each state sample; returns transcript lines to speak now. */
  update(state: AircraftState, phaseId: string): TranscriptEntry[] {
    const out: TranscriptEntry[] = [];
    const t = state.simTimeSec;
    const ias = state.speeds.iasKt;
    const ra = state.position.radioAltitudeFt;

    // --- Takeoff roll speed callouts (ordered, once each) ---
    if (this.takeoffPhases.has(phaseId) && state.weightOnWheels) {
      if (!this.saidTakeoff.has('80kt') && ias >= 80) {
        this.saidTakeoff.add('80kt');
        out.push(this.say(t, 'Eighty knots.', 'callout:80kt'));
      }
      if (!this.saidTakeoff.has('v1') && ias >= this.vSpeeds.v1Kt) {
        this.saidTakeoff.add('v1');
        out.push(this.say(t, 'V1.', 'callout:v1'));
      }
      if (!this.saidTakeoff.has('rotate') && ias >= this.vSpeeds.vrKt) {
        this.saidTakeoff.add('rotate');
        out.push(this.say(t, 'Rotate.', 'callout:rotate'));
      }
    }

    // --- Positive rate (from state, mirrors the scenario rule) ---
    // Climb is confirmed over elapsed time, not over one sample: requiring the
    // radio altitude to gain a foot per sample made the callout depend on the
    // state rate and never fire at 30 Hz (R-12).
    const climbing = !state.weightOnWheels && state.speeds.verticalSpeedFpm > 300 && ra > 20;
    if (!climbing) {
      this.climbingSinceSec = null;
    } else if (this.climbingSinceSec === null) {
      this.climbingSinceSec = t;
    }
    if (
      !this.saidPositiveRate &&
      climbing &&
      this.climbingSinceSec !== null &&
      t - this.climbingSinceSec >= POSITIVE_RATE_CONFIRM_SEC
    ) {
      this.saidPositiveRate = true;
      const entry: TranscriptEntry = {
        id: transcriptId('fo'),
        simTimeSec: t,
        speaker: 'first_officer',
        message: 'Positive rate.',
        relatedEventId: 'callout:positive_rate',
        expectedResponse: {
          kind: 'callout_response',
          options: [
            { id: 'gear_up', text: 'Gear up.', correct: true },
            { id: 'flaps_up', text: 'Flaps up.', correct: false },
            { id: 'roger', text: 'Roger.', correct: false },
          ],
        },
      };
      this.pending = {
        transcriptEntryId: entry.id,
        kind: 'gear_up_after_positive_rate',
        sinceSimTimeSec: t,
      };
      out.push(entry);
    }

    // --- Procedural omission: gear still down long after positive rate ---
    if (
      this.saidPositiveRate &&
      !this.saidGearReminder &&
      state.controls.gearLeverDown &&
      !state.weightOnWheels &&
      this.pending === null &&
      ra > 400
    ) {
      this.saidGearReminder = true;
      out.push(this.say(t, 'Gear is still down.', 'fo:gear_reminder'));
    }

    // --- Approach altitude callouts (descending through, once each) ---
    if (this.approachPhases.has(phaseId) && state.speeds.verticalSpeedFpm < 0) {
      for (const alt of APPROACH_ALT_CALLOUTS_FT) {
        if (!this.saidApproachAlt.has(alt) && this.lastRaFt > alt && ra <= alt) {
          this.saidApproachAlt.add(alt);
          out.push(this.say(t, alt >= 500 ? `${alt}.` : `${alt}`, `callout:ra_${alt}`));
        }
      }
    }

    // --- Stabilized approach monitoring below 1000 ft (spec §12) ---
    if (this.approachPhases.has(phaseId) && !state.weightOnWheels && ra < 1000 && ra > 50) {
      const speedOk = ias >= this.vSpeeds.vappKt - 5 && ias <= this.vSpeeds.vappKt + 20;
      const configOk = state.controls.gearLeverDown && state.controls.flapHandleDetent >= 30;
      const pathOk =
        (state.nav.locDeviationDots === null || Math.abs(state.nav.locDeviationDots) <= 1) &&
        (state.nav.gsDeviationDots === null || Math.abs(state.nav.gsDeviationDots) <= 1);
      const sinkOk = state.speeds.verticalSpeedFpm > -1100;
      const stable = speedOk && configOk && pathOk && sinkOk;
      if (stable) {
        this.unstableSinceSec = null;
      } else if (this.unstableSinceSec === null) {
        this.unstableSinceSec = t;
      } else if (!this.saidGoAround && t - this.unstableSinceSec > 3) {
        this.saidGoAround = true;
        const reasons = [
          !speedOk ? 'speed' : null,
          !configOk ? 'configuration' : null,
          !pathOk ? 'flight path' : null,
          !sinkOk ? 'sink rate' : null,
        ]
          .filter(Boolean)
          .join(', ');
        out.push(this.say(t, `Unstable — ${reasons}. Go around.`, 'fo:unstable_approach'));
      }
    }

    this.lastRaFt = ra;
    return out;
  }

  /** React to scenario events (checklist reading etc.). */
  onScenarioEvent(event: ScenarioEvent): TranscriptEntry[] {
    if (event.kind === 'checklist_item_failed') {
      return [this.say(event.simTimeSec, event.message, event.id)];
    }
    if (event.kind === 'checklist_completed') {
      return [this.say(event.simTimeSec, `${event.message}.`, event.id)];
    }
    return [];
  }

  /**
   * The user answered a pending callout. Returns correctness plus a follow-up
   * line when appropriate. Correctness is judged by the option's flag only.
   */
  respond(
    entry: TranscriptEntry,
    optionId: string,
    state: AircraftState,
  ): {
    correct: boolean;
    followUps: TranscriptEntry[];
  } {
    const option = entry.expectedResponse?.options.find((o) => o.id === optionId);
    const correct = option?.correct ?? false;
    entry.responseResult = correct ? 'correct' : 'incorrect';
    const followUps: TranscriptEntry[] = [];
    if (this.pending?.transcriptEntryId === entry.id) {
      this.pending = null;
      if (correct) {
        followUps.push(this.say(state.simTimeSec, 'Gear up.', 'fo:gear_up_ack'));
      }
    }
    return { correct, followUps };
  }

  private say(simTimeSec: number, message: string, relatedEventId: string): TranscriptEntry {
    return {
      id: transcriptId('fo'),
      simTimeSec,
      speaker: 'first_officer',
      message,
      relatedEventId,
    };
  }
}
