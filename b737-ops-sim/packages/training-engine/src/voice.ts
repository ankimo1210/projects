/**
 * Voice presentation layer interface (spec §13). The deterministic ATC/FO
 * systems own all decisions; a provider only renders/captures speech.
 * The simulator must remain fully usable with no provider (text-only).
 */

import type { Speaker } from './transcript.js';

export interface SpeechRequest {
  speaker: Speaker;
  text: string;
}

export interface ListenOptions {
  /** Expected phrases to bias recognition toward, when supported. */
  expectedPhrases?: string[];
}

export interface TranscriptEvent {
  text: string;
  final: boolean;
}

export interface VoiceProvider {
  speak(request: SpeechRequest): Promise<void>;
  listen(options: ListenOptions): AsyncIterable<TranscriptEvent>;
}
