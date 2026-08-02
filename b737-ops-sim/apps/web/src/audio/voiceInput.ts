/**
 * Optional voice input for ATC readbacks (spec §22 Phase 5 T6).
 *
 * The recogniser only proposes text. Matching that text to one of the readback
 * options the deterministic ATC layer already produced is done here, and the
 * existing grader decides whether the readback was correct — a speech layer
 * never judges (spec §13).
 *
 * PRIVACY: browsers implement `SpeechRecognition` differently and some (Chrome)
 * send audio to a cloud service. This project is local-only by design, so voice
 * input is off by default and the UI says so before it is switched on.
 */

interface SpeechRecognitionLike {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start(): void;
  stop(): void;
  onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onerror: ((event: unknown) => void) | null;
  onend: (() => void) | null;
}

type RecognitionCtor = new () => SpeechRecognitionLike;

function recognitionCtor(): RecognitionCtor | null {
  const w = window as unknown as Record<string, RecognitionCtor | undefined>;
  return w['SpeechRecognition'] ?? w['webkitSpeechRecognition'] ?? null;
}

export function voiceInputAvailable(): boolean {
  return recognitionCtor() !== null;
}

/** Words that carry no information for matching a readback. */
const STOP_WORDS = new Set([
  'the',
  'a',
  'an',
  'and',
  'to',
  'for',
  'of',
  'at',
  'on',
  'we',
  'are',
  'is',
  'boeing',
]);

function tokens(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9 ]+/g, ' ')
    .split(/\s+/)
    .filter((t) => t.length > 0 && !STOP_WORDS.has(t));
}

/**
 * Match an utterance against readback options. Deterministic: the option with
 * the highest token overlap wins, and only if it covers at least half of that
 * option's words and beats the runner-up. Returns null when unsure — the crew
 * can always press the button.
 */
export function matchReadback(
  utterance: string,
  options: { id: string; text: string }[],
): string | null {
  const said = new Set(tokens(utterance));
  if (said.size === 0) return null;
  const scored = options
    .map((o) => {
      const want = tokens(o.text);
      const hit = want.filter((t) => said.has(t)).length;
      return { id: o.id, ratio: want.length === 0 ? 0 : hit / want.length, hit };
    })
    .sort((a, b) => b.ratio - a.ratio);
  const best = scored[0];
  const second = scored[1];
  if (!best || best.ratio < 0.5) return null;
  if (second && best.ratio - second.ratio < 0.15) return null;
  return best.id;
}

/** Thin wrapper so the UI never touches the vendor-prefixed API directly. */
export class VoiceInput {
  private recognition: SpeechRecognitionLike | null = null;
  private listening = false;

  start(onUtterance: (text: string) => void): boolean {
    const Ctor = recognitionCtor();
    if (!Ctor || this.listening) return false;
    const recognition = new Ctor();
    recognition.lang = 'en-US';
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.onresult = (event) => {
      const results = event.results;
      const last = results[results.length - 1];
      const alternative = last?.[0];
      if (alternative) onUtterance(alternative.transcript);
    };
    recognition.onerror = () => undefined;
    recognition.onend = () => {
      // keep listening while the toggle is on
      if (this.listening) {
        try {
          recognition.start();
        } catch {
          this.listening = false;
        }
      }
    };
    this.recognition = recognition;
    this.listening = true;
    try {
      recognition.start();
    } catch {
      this.listening = false;
    }
    return this.listening;
  }

  stop(): void {
    this.listening = false;
    this.recognition?.stop();
    this.recognition = null;
  }

  get active(): boolean {
    return this.listening;
  }
}

export const voiceInput = new VoiceInput();
