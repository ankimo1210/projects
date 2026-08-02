import { useEffect, useRef } from 'react';
import { getSession } from '../state/connection.js';
import { useSessionStore, useSettingsStore } from '../state/stores.js';

/** ATC / crew transcript with readback controls (spec §12/§13/§19). */
export function TranscriptPanel(): JSX.Element {
  useSessionStore((s) => s.version);
  const ttsEnabled = useSettingsStore((s) => s.ttsEnabled);
  const setTtsEnabled = useSettingsStore((s) => s.setTtsEnabled);
  const session = getSession();
  const listRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  });

  const canRequestTakeoff =
    session.phaseId === 'before_takeoff' &&
    session.runtime.getFlag('takeoffClearanceReceived') !== true &&
    !session.transcript.some((e) => e.expectedResponse && !e.responseResult);

  return (
    <div className="panel transcript-panel" data-testid="transcript-panel">
      <div className="panel-head">
        <span>ATC / Crew</span>
        <label className="tts-toggle">
          <input
            type="checkbox"
            checked={ttsEnabled}
            onChange={(e) => setTtsEnabled(e.target.checked)}
          />
          voice
        </label>
      </div>
      <div className="transcript-list" ref={listRef} data-testid="transcript-list">
        {session.transcript.map((entry) => (
          <div key={entry.id} className={`tr tr-${entry.speaker}`}>
            <span className="tr-time">{formatTime(entry.simTimeSec)}</span>
            <span className="tr-speaker">{speakerLabel(entry.speaker)}</span>
            <span className="tr-msg">{entry.message}</span>
            {entry.responseResult && (
              <span className={`tr-result tr-${entry.responseResult}`}>
                {entry.responseResult === 'correct' ? '✓ readback' : '✗ readback'}
              </span>
            )}
            {entry.expectedResponse && !entry.responseResult && (
              <div className="tr-options" data-testid="response-options">
                {entry.expectedResponse.options.map((o) => (
                  <button
                    key={o.id}
                    type="button"
                    className="tr-option"
                    onClick={() => session.respond(entry.id, o.id)}
                  >
                    {o.text}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="transcript-actions">
        <button
          type="button"
          className="mic-btn"
          data-testid="request-takeoff"
          disabled={!canRequestTakeoff}
          onClick={() => session.requestTakeoffClearance()}
        >
          🎙 Request takeoff clearance
        </button>
      </div>
    </div>
  );
}

function speakerLabel(s: string): string {
  switch (s) {
    case 'first_officer':
      return 'FO';
    case 'atc':
      return 'TWR';
    case 'captain':
      return 'CAPT';
    default:
      return 'SYS';
  }
}

function formatTime(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}
