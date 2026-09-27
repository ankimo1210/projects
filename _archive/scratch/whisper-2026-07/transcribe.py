import json
import sys
import time
import wave

import numpy as np
import mlx_whisper

WAV = "rec23_16k.wav"
MODEL = "mlx-community/whisper-large-v3-turbo"

with wave.open(WAV) as w:
    assert w.getframerate() == 16000 and w.getnchannels() == 1, (
        w.getframerate(),
        w.getnchannels(),
    )
    audio = (
        np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
        / 32768.0
    )

print(f"audio: {len(audio) / 16000 / 60:.1f} min", flush=True)

t0 = time.time()
result = mlx_whisper.transcribe(
    audio,
    path_or_hf_repo=MODEL,
    language="ja",
    verbose=False,
    condition_on_previous_text=False,
)
elapsed = time.time() - t0
print(f"transcribed in {elapsed / 60:.1f} min", flush=True)

with open("rec23_result.json", "w") as f:
    json.dump(result, f, ensure_ascii=False, indent=1)


def ts(s):
    m, sec = divmod(int(s), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}"


lines = [f"[{ts(seg['start'])} - {ts(seg['end'])}] {seg['text'].strip()}" for seg in result["segments"]]
with open("rec23_transcript.txt", "w") as f:
    f.write("\n".join(lines) + "\n")

print(f"segments: {len(result['segments'])}", flush=True)
