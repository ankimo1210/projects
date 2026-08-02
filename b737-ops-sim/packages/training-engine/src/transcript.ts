/** Crew/ATC communication transcript model (spec §12/§13). */

export type Speaker = 'captain' | 'first_officer' | 'atc' | 'system';

export interface ReadbackOption {
  id: string;
  text: string;
  correct: boolean;
}

export interface TranscriptEntry {
  id: string;
  simTimeSec: number;
  speaker: Speaker;
  message: string;
  /** Aircraft/scenario event that triggered this line, if any. */
  relatedEventId?: string;
  /** Non-null while a response is expected from the user. */
  expectedResponse?: {
    options: ReadbackOption[];
    /** Free-form label of what a correct response means (for the debrief). */
    kind: 'atc_readback' | 'callout_response';
  };
  /** Filled once the user responded. */
  responseResult?: 'correct' | 'incorrect';
}

let counter = 0;
export function transcriptId(prefix: string): string {
  counter += 1;
  return `${prefix}_${counter}`;
}

/** Reset the id counter (determinism in tests). */
export function resetTranscriptIds(): void {
  counter = 0;
}
