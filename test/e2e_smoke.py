"""Real local model smoke: Agent text -> TTS -> browser -> mic -> VAD/ASR."""

from __future__ import annotations

import json
import time
import wave
from pathlib import Path

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
        synthesis_done = False
        while not synthesis_done:
            message = websocket.recv(timeout=45)
            if isinstance(message, bytes):
                tts_chunks.append(message)
                continue
            event_type = json.loads(message)["type"]
            tts_events.append(event_type)
            if event_type == "tts.stopped":
                synthesis_done = True

        # Audio and state travel over independent Graph edges. Drain binary
        # frames until the audio edge is quiet instead of truncating at the
        # synthesis-state event.
        while True:
            try:
                message = websocket.recv(timeout=0.5)
            except TimeoutError:
                break
            if isinstance(message, bytes):
                tts_chunks.append(message)

        source = np.frombuffer(b"".join(tts_chunks), dtype=np.int16).astype(np.float32)
        positions = np.linspace(0, len(source) - 1, round(len(source) * 16_000 / 24_000))
        microphone = np.interp(positions, np.arange(len(source)), source).astype(np.int16)
        microphone = np.concatenate((
            np.zeros(4_800, dtype=np.int16),
            microphone,
            np.zeros(24_000, dtype=np.int16),
        ))
        send_microphone(websocket, microphone)

        voice_events = receive_turn(websocket)

        kinds = [item["type"] for item in voice_events]
        assert tts_events == ["tts.started", "tts.stopped"], tts_events
        assert sum(map(len, tts_chunks)) > 4_800, "TTS returned no useful PCM"
        assert "speech.started" in kinds, kinds
        assert "asr.final" in kinds, kinds
        chinese_final = "".join(item["text"] for item in voice_events if item["type"] == "asr.final")
        assert "语音助手" in chinese_final, chinese_final

        model = Path(".models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17")
        with wave.open(str(model / "test_wavs/en.wav"), "rb") as source:
            assert source.getframerate() == 16_000 and source.getnchannels() == 1
            english = np.frombuffer(source.readframes(source.getnframes()), dtype=np.int16)
        send_microphone(websocket, np.concatenate((
            np.zeros(4_800, dtype=np.int16), english, np.zeros(24_000, dtype=np.int16),
        )))
        english_events = receive_turn(websocket)
        english_final = " ".join(item["text"] for item in english_events if item["type"] == "asr.final")
        assert "tribal chieftain" in english_final.lower(), english_final
        print(json.dumps({
            "ttsPcmBytes": sum(map(len, tts_chunks)),
            "asrFinalZh": chinese_final,
            "asrFinalEn": english_final,
            "events": kinds,
        }, ensure_ascii=False))


def send_microphone(websocket, samples: np.ndarray) -> None:
    for offset in range(0, len(samples), 320):
        websocket.send(samples[offset:offset + 320].tobytes())
        time.sleep(0.018)


def receive_turn(websocket) -> list[dict]:
    events: list[dict] = []
    deadline = time.monotonic() + 20
    quiet_deadline = None
    while time.monotonic() < deadline:
        try:
            message = websocket.recv(timeout=0.5)
        except TimeoutError:
            if quiet_deadline is not None and time.monotonic() >= quiet_deadline:
                return events
            continue
        if isinstance(message, str):
            event = json.loads(message)
            events.append(event)
            if event["type"] == "asr.final":
                # Qwen3-TTS may insert natural pauses which create multiple VAD
                # segments. Treat all finals in the same quiet window as one turn.
                quiet_deadline = time.monotonic() + 1.0
    raise AssertionError(events)


if __name__ == "__main__":
    main()
