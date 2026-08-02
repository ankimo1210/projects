import { resolveProp, type ConditionEvaluator, type EvaluationContext } from './conditions.js';
import type { ChecklistDefinition, ChecklistItemDefinition } from './types.js';

export type ChecklistItemStatus = 'pending' | 'active' | 'completed' | 'failed';

export interface ChecklistItemRuntime {
  definition: ChecklistItemDefinition;
  status: ChecklistItemStatus;
  /** Live value for dynamic responses (e.g. current flap detent). */
  dynamicResponseValue: string | null;
  completedAtSimTimeSec: number | null;
  failureMessage: string | null;
}

/**
 * Checklist runtime: an item is only completed when its validation condition
 * holds against real aircraft state at the moment the crew answers it
 * (spec §11/§14). Items are worked strictly in order, challenge–response style.
 */
export class ChecklistRun {
  readonly items: ChecklistItemRuntime[];
  private cursor = 0;

  constructor(
    readonly definition: ChecklistDefinition,
    private readonly evaluator: ConditionEvaluator,
  ) {
    this.items = definition.items.map((definitionItem, i) => ({
      definition: definitionItem,
      status: i === 0 ? 'active' : 'pending',
      dynamicResponseValue: null,
      completedAtSimTimeSec: null,
      failureMessage: null,
    }));
  }

  get complete(): boolean {
    return this.cursor >= this.items.length;
  }

  get activeItem(): ChecklistItemRuntime | null {
    return this.complete ? null : (this.items[this.cursor] ?? null);
  }

  /** Refresh dynamic response values from live state. */
  observe(ctx: EvaluationContext): void {
    for (const item of this.items) {
      if (item.definition.dynamicResponseProp) {
        const v = resolveProp(ctx, item.definition.dynamicResponseProp);
        item.dynamicResponseValue = v === undefined || v === null ? null : String(v);
      }
    }
  }

  /**
   * The crew answers the active item's challenge. Returns the item outcome:
   * validated items complete only if their condition holds right now.
   */
  answerActiveItem(ctx: EvaluationContext): { item: ChecklistItemRuntime; ok: boolean } | null {
    const item = this.activeItem;
    if (!item) return null;
    const def = item.definition;
    let ok: boolean;
    if (def.validation) {
      ok = this.evaluator.evaluate(def.validation, ctx);
    } else {
      // Manual item (manualReason documents why it cannot be state-validated).
      ok = true;
    }
    if (ok) {
      item.status = 'completed';
      item.failureMessage = null;
      item.completedAtSimTimeSec = ctx.state.simTimeSec;
      this.cursor += 1;
      const next = this.items[this.cursor];
      if (next) next.status = 'active';
    } else {
      item.status = 'failed';
      item.failureMessage =
        def.failureMessage ??
        `${def.challenge}: aircraft state does not match the required response`;
    }
    return { item, ok };
  }

  /** Re-arm a failed item so it can be answered again after correction. */
  retryActiveItem(): void {
    const item = this.items[this.cursor];
    if (item && item.status === 'failed') item.status = 'active';
  }
}
