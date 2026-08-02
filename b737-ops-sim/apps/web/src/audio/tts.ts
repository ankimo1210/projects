import type { SpeechRequest, TranscriptEntry, VoiceProvider } from '@b737/training-engine';

/**
 * Offline text-to-speech via the browser's Web Speech API (spec §13/§17):
 * purely a presentation layer — all content comes from the deterministic
 * ATC/FO systems. No external AI service is involved.
 */
export const webSpeechVoiceProvider: VoiceProvider = {
  speak(request: SpeechRequest): Promise<void> {
    return new Promise((resolve) => {
      if (!('speechSynthesis' in window)) return resolve();
      const utterance = new SpeechSynthesisUtterance(request.text);
      utterance.rate = request.speaker === 'atc' ? 1.25 : 1.05;
      utterance.pitch = request.speaker === 'atc' ? 0.9 : 1.0;
      utterance.onend = () => resolve();
      utterance.onerror = () => resolve();
      window.speechSynthesis.speak(utterance);
    });
  },
  // Speech recognition is a later phase; the interface exists per spec §13.
  async *listen(): AsyncIterable<{ text: string; final: boolean }> {
    // no-op in Milestone 1
  },
};

export function speakEntry(entry: TranscriptEntry): void {
  void webSpeechVoiceProvider.speak({ speaker: entry.speaker, text: entry.message });
}
