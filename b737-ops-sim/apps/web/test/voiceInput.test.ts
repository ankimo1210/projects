import { describe, expect, it } from 'vitest';
import { matchReadback } from '../src/audio/voiceInput.js';

/**
 * Voice matching (M5 T6). The recogniser proposes; this maps the proposal to an
 * option the ATC layer already produced. It must refuse when unsure — a wrong
 * guess would be graded as the crew's mistake.
 */
const OPTIONS = [
  { id: 'correct', text: 'Cleared for takeoff runway 28R, Boeing 737.' },
  { id: 'lineup', text: 'Line up and wait runway 28R, Boeing 737.' },
  { id: 'roger', text: 'Roger.' },
];

describe('matchReadback', () => {
  it('matches a faithful readback', () => {
    expect(matchReadback('cleared for takeoff runway 28R', OPTIONS)).toBe('correct');
  });

  it('matches the other option when that is what was said', () => {
    expect(matchReadback('line up and wait runway 28R', OPTIONS)).toBe('lineup');
  });

  it('refuses when the utterance is ambiguous between options', () => {
    expect(matchReadback('runway 28R', OPTIONS)).toBeNull();
  });

  it('refuses noise rather than guessing', () => {
    expect(matchReadback('uhh what was that', OPTIONS)).toBeNull();
    expect(matchReadback('', OPTIONS)).toBeNull();
  });

  it('ignores filler words and punctuation', () => {
    expect(matchReadback('roger!', OPTIONS)).toBe('roger');
  });
});
