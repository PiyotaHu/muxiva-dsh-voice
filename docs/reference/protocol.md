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
| `client.mute` / `client.unmute` | — | Pause/resume microphone admission without tearing down the Web Audio or WebSocket transport. No PCM is admitted while paused; the audio Source resets VAD/ASR state at both boundaries. |
| `client.stop` | — | Stop and drain the local session. |
| `benchmark.audio.marker` | `markerId`, `capturedNs` | Test-only marker associated with the next PCM chunk; production clients never send it. |

Server controls:

| Type | Meaning |
| --- | --- |
| `server.ready` | Graph transport is ready. |
| `speech.started` / `speech.stopped` | Silero VAD boundary. |
| `barge.in` | A non-empty ASR partial or an admitted multilingual Final has confirmed speech; cancel old playback/TTS and the running Agent turn. |
| `asr.partial` / `asr.final` | Preview-only text / Agent-admitted text. |
| `asr.rejected` | The segment was empty, too short, non-speech, or outside the accepted language set; return to listening without prompting DSH. |
| `tts.started` / `tts.stopped` | Synthesis state; the browser drains scheduled PCM before returning to listening. |
| `pipeline.metrics` | Bounded latency and queue gauges. |
| `pipeline.error` | User-actionable local failure. |
| `benchmark.audio.admitted` | Test-only acknowledgement emitted after the marked PCM chunk becomes a Muxiva AudioFrame. |

Only `asr.final` is submitted to DSH. `speech.started` is deliberately advisory. A non-empty streaming partial or a multilingual Final that passes the language/event/length gate emits `barge.in`; only then are current TTS/playback and the running DSH turn cancelled. VAD alone never interrupts. Rejected segments emit `asr.rejected`. Generation identifiers in Muxiva discard late worker results.
