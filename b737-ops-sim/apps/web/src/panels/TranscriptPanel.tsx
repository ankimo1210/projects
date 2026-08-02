import { useEffect, useRef } from 'react';
import { getSession, sendCommand } from '../state/connection.js';
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

  const awaitingReadback = session.transcript.some((e) => e.expectedResponse && !e.responseResult);
  const canRequestTakeoff =
    ['before_takeoff', 'hold_short'].includes(session.phaseId) &&
    session.runtime.getFlag('takeoffClearanceReceived') !== true &&
    !awaitingReadback;
  // Ground control is only in the loop for scenarios that start at a stand.
  const canRequestTaxi =
    session.atc.phase === 'awaiting_taxi_request' &&
    session.runtime.getFlag('taxiClearanceReceived') !== true &&
    !awaitingReadback;
  // Going around is the crew's decision, available whenever one can be flown.
  const canGoAround =
    ['approach_setup', 'final_approach', 'landing'].includes(session.phaseId) &&
    session.runtime.getFlag('goAroundAnnounced') !== true;

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
        {canRequestTaxi && (
          <button
            type="button"
            className="mic-btn"
            data-testid="request-taxi"
            onClick={() => session.requestTaxiClearance()}
          >
            🎙 Request taxi clearance
          </button>
        )}
        {canGoAround && (
          <button
            type="button"
            className="mic-btn go-around"
            data-testid="go-around"
            onClick={() => {
              // TO/GA to the aircraft, and tell ATC what we are doing.
              sendCommand({ type: 'set_toga', engaged: true });
              session.announceGoAround();
            }}
          >
            ⬆ Go around (TO/GA)
          </button>
        )}
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
