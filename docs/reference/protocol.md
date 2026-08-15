# Loopback protocol

Protocol identifier: `muxiva.dsh.voice/v1`.

The browser opens `ws://127.0.0.1:4390/voice`. Client-to-server binary messages are raw mono PCM16 at 16 kHz; server-to-client binary messages are mono PCM16 at 24 kHz. Text messages are JSON control frames with `version` and `type`.

Client controls:

| Type | Payload | Meaning |
| --- | --- | --- |
| `client.hello` | `sessionId`, audio format | Bind the DSH session and negotiate audio. |
| `agent.delta` | `text` | One complete sentence or bounded speech chunk. |
| `agent.final` | `text` | Flush the final tail. |
| `agent.cancel` | `reason` | Invalidate current TTS generation. |
| `client.mute` / `client.unmute` | — | Change microphone state without tearing down the audio transport. Muted worklet frames are replaced with silence. |
| `client.stop` | — | Stop and drain the local session. |

Server controls:

| Type | Meaning |
| --- | --- |
| `server.ready` | Graph transport is ready. |
| `speech.started` / `speech.stopped` | Silero VAD boundary. |
| `barge.in` | ASR has confirmed non-empty speech; cancel old playback/TTS and the running Agent turn. |
| `asr.partial` / `asr.final` | Preview-only text / Agent-admitted text. |
| `asr.rejected` | The VAD segment produced no text; return to listening without prompting DSH. |
| `tts.started` / `tts.stopped` | Synthesis state; the browser drains scheduled PCM before returning to listening. |
| `pipeline.metrics` | Bounded latency and queue gauges. |
| `pipeline.error` | User-actionable local failure. |

Only `asr.final` is submitted to DSH. `speech.started` is deliberately advisory: it changes the UI to hearing but does not interrupt anything. The first non-empty streaming partial—or the multilingual final when the preview model cannot decode the language—emits `barge.in`; only then are current TTS/playback and the running DSH turn cancelled. Empty VAD segments emit `asr.rejected`. Generation identifiers in Muxiva discard late worker results.
