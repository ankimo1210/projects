import { z } from 'zod';

/**
 * Versioned FlightGear property mapping (spec §5).
 * The single source of truth is `config/flightgear/737-800-property-map.json`;
 * no raw FlightGear property path may appear outside that file and this
 * adapter package.
 */

export const FgValueTypeSchema = z.enum(['number', 'bool']);

export const FgStateEntrySchema = z.object({
  /** FlightGear property path, e.g. "/position/altitude-ft". */
  fgProp: z.string().startsWith('/'),
  /** Multiply the FG value by this after reading (unit conversion). */
  scale: z.number().optional(),
  type: FgValueTypeSchema.optional(),
  /** Missing property tolerated (state field becomes null/default). */
  optional: z.boolean().optional(),
  comment: z.string().optional(),
});

export const FgCommandEntrySchema = z.object({
  /** One or more FG properties written when the command applies. */
  fgProps: z.array(z.string().startsWith('/')).min(1),
  /** Multiply the outgoing value by this before writing. */
  scale: z.number().optional(),
  type: FgValueTypeSchema.optional(),
  comment: z.string().optional(),
});

export const PropertyMapSchema = z.object({
  version: z.number().int(),
  aircraft: z.string(),
  notes: z.string().optional(),
  state: z.record(z.string(), FgStateEntrySchema),
  commands: z.record(z.string(), FgCommandEntrySchema),
});

export type FgStateEntry = z.infer<typeof FgStateEntrySchema>;
export type FgCommandEntry = z.infer<typeof FgCommandEntrySchema>;
export type PropertyMap = z.infer<typeof PropertyMapSchema>;

export function parsePropertyMap(json: unknown): PropertyMap {
  const parsed = PropertyMapSchema.safeParse(json);
  if (!parsed.success) {
    throw new Error(`invalid FlightGear property map: ${parsed.error.message}`);
  }
  return parsed.data;
}
