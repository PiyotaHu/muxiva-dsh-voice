"""Real local model smoke: Agent text -> TTS -> browser -> mic -> VAD/ASR."""

from __future__ import annotations

import json
import time

import numpy as np
from websockets.sync.client import connect


def main() -> None:
    with connect("ws://127.0.0.1:4390/voice", max_size=262_144, compression=None) as websocket:
        ready = json.loads(websocket.recv(timeout=5))
        assert ready["type"] == "server.ready", ready
        websocket.send(json.dumps({
            "version": "muxiva.dsh.voice/v1",
            "type": "agent.final",
            "text": "你好，这是本地语音助手。",
        }, ensure_ascii=False))

        tts_chunks: list[bytes] = []
        tts_events: list[str] = []
        while True:
            message = websocket.recv(timeout=15)
            if isinstance(message, bytes):
                tts_chunks.append(message)
                continue
            event_type = json.loads(message)["type"]
            tts_events.append(event_type)
            if event_type == "tts.stopped":
                break

        source = np.frombuffer(b"".join(tts_chunks), dtype=np.int16).astype(np.float32)
        positions = np.linspace(0, len(source) - 1, round(len(source) * 16_000 / 24_000))
        microphone = np.interp(positions, np.arange(len(source)), source).astype(np.int16)
        microphone = np.concatenate((
            np.zeros(4_800, dtype=np.int16),
            microphone,
            np.zeros(24_000, dtype=np.int16),
        ))
        for offset in range(0, len(microphone), 320):
            websocket.send(microphone[offset:offset + 320].tobytes())
            time.sleep(0.018)

        voice_events: list[dict] = []
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            try:
                message = websocket.recv(timeout=2)
            except TimeoutError:
                continue
            if isinstance(message, str):
                event = json.loads(message)
                voice_events.append(event)
                if event["type"] == "asr.final":
                    break

        kinds = [item["type"] for item in voice_events]
        assert tts_events == ["tts.started", "tts.stopped"], tts_events
        assert sum(map(len, tts_chunks)) > 4_800, "TTS returned no useful PCM"
        assert "speech.started" in kinds, kinds
        assert "asr.final" in kinds, kinds
        print(json.dumps({
            "ttsPcmBytes": sum(map(len, tts_chunks)),
            "asrFinal": next(item["text"] for item in voice_events if item["type"] == "asr.final"),
            "events": kinds,
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()
