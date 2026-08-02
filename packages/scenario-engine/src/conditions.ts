import { angleDiffDeg, type AircraftState } from '@b737/shared';

/**
 * Declarative, JSON-serializable condition DSL evaluated against live
 * aircraft state (spec §11: scenarios react to real state, not button clicks).
 *
 * Property paths address:
 *   - AircraftState via dot notation:  "speeds.iasKt", "weightOnWheels"
 *   - derived signals:                 "derived.radioAltitudeTrend" (string)
 *   - host-managed flags:              "flags.takeoffClearanceReceived"
 */

export type ConditionLeafOp = 'gt' | 'gte' | 'lt' | 'lte' | 'eq' | 'neq';

export type Condition =
  | { all: Condition[]; sustainedSec?: number }
  | { any: Condition[]; sustainedSec?: number }
  | { not: Condition; sustainedSec?: number }
  | {
      prop: string;
      op: ConditionLeafOp;
      value: number | boolean | string | null;
      /** Must hold continuously this long (sim seconds) before it is true. */
      sustainedSec?: number;
    }
  | { prop: string; op: 'between'; min: number; max: number; sustainedSec?: number }
  | {
      /** Heading-style comparison with 360° wraparound. */
      prop: string;
      op: 'withinDegOf';
      target: number;
      toleranceDeg: number;
      sustainedSec?: number;
    };

export type Trend = 'increasing' | 'decreasing' | 'flat';

export interface EvaluationContext {
  state: AircraftState;
  flags: Readonly<Record<string, boolean | number | string>>;
  derived: {
    radioAltitudeTrend: Trend;
    altitudeTrend: Trend;
    iasTrend: Trend;
  };
}

export function resolveProp(ctx: EvaluationContext, path: string): unknown {
  if (path.startsWith('flags.')) return ctx.flags[path.slice('flags.'.length)];
  if (path.startsWith('derived.')) {
    const key = path.slice('derived.'.length) as keyof EvaluationContext['derived'];
    return ctx.derived[key];
  }
  let cur: unknown = ctx.state;
  for (const part of path.split('.')) {
    if (cur === null || typeof cur !== 'object') return undefined;
    cur = (cur as Record<string, unknown>)[part];
  }
  return cur;
}

/**
 * Stateful evaluator: tracks `sustainedSec` timers per condition instance and
 * computes trend signals over a sliding window. One instance per scenario run.
 */
export class ConditionEvaluator {
  private sustainSince = new WeakMap<object, number | null>();
  private history: { simTimeSec: number; raFt: number; altFt: number; iasKt: number }[] = [];

  /** Push a state sample to update trend windows. Call once per update tick. */
  observe(state: AircraftState): void {
    this.history.push({
      simTimeSec: state.simTimeSec,
      raFt: state.position.radioAltitudeFt,
      altFt: state.position.altitudeFtMsl,
      iasKt: state.speeds.iasKt,
    });
    const cutoff = state.simTimeSec - 3;
    while (this.history.length > 2 && this.history[0]!.simTimeSec < cutoff) this.history.shift();
  }

  derived(): EvaluationContext['derived'] {
    const trendOf = (selector: (s: (typeof this.history)[number]) => number, eps: number): Trend => {
      if (this.history.length < 2) return 'flat';
      const first = this.history[0]!;
      const last = this.history[this.history.length - 1]!;
      const delta = selector(last) - selector(first);
      if (delta > eps) return 'increasing';
      if (delta < -eps) return 'decreasing';
      return 'flat';
    };
    return {
      radioAltitudeTrend: trendOf((s) => s.raFt, 4),
      altitudeTrend: trendOf((s) => s.altFt, 4),
      iasTrend: trendOf((s) => s.iasKt, 1.5),
    };
  }

  evaluate(condition: Condition, ctx: EvaluationContext): boolean {
    const instantaneous = this.evaluateInstant(condition, ctx);
    const sustained = 'sustainedSec' in condition ? condition.sustainedSec : undefined;
    if (sustained === undefined || sustained <= 0) return instantaneous;
    const now = ctx.state.simTimeSec;
    const since = this.sustainSince.get(condition as object) ?? null;
    if (!instantaneous) {
      this.sustainSince.set(condition as object, null);
      return false;
    }
    if (since === null) {
      this.sustainSince.set(condition as object, now);
      return sustained === 0;
    }
    return now - since >= sustained;
  }

  private evaluateInstant(condition: Condition, ctx: EvaluationContext): boolean {
    if ('all' in condition) return condition.all.every((c) => this.evaluate(c, ctx));
    if ('any' in condition) return condition.any.some((c) => this.evaluate(c, ctx));
    if ('not' in condition) return !this.evaluate(condition.not, ctx);

    const raw = resolveProp(ctx, condition.prop);
    if (condition.op === 'between') {
      return typeof raw === 'number' && raw >= condition.min && raw <= condition.max;
    }
    if (condition.op === 'withinDegOf') {
      return (
        typeof raw === 'number' &&
        Math.abs(angleDiffDeg(raw, condition.target)) <= condition.toleranceDeg
      );
    }
    switch (condition.op) {
      case 'eq':
        return raw === condition.value;
      case 'neq':
        return raw !== condition.value;
      case 'gt':
        return typeof raw === 'number' && typeof condition.value === 'number' && raw > condition.value;
      case 'gte':
        return typeof raw === 'number' && typeof condition.value === 'number' && raw >= condition.value;
      case 'lt':
        return typeof raw === 'number' && typeof condition.value === 'number' && raw < condition.value;
      case 'lte':
        return typeof raw === 'number' && typeof condition.value === 'number' && raw <= condition.value;
    }
  }
}
