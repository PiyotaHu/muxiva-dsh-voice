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
| `client.stop` | — | Stop and drain the local session. |

Server controls:

| Type | Meaning |
| --- | --- |
| `server.ready` | Graph transport is ready. |
| `speech.started` / `speech.stopped` | Silero VAD boundary. |
| `asr.partial` / `asr.final` | Preview-only text / Agent-admitted text. |
| `tts.started` / `tts.stopped` | Synthesis state; the browser drains scheduled PCM before returning to listening. |
| `pipeline.metrics` | Bounded latency and queue gauges. |
| `pipeline.error` | User-actionable local failure. |

Only `asr.final` is submitted to DSH. `speech.started` cancels current TTS/playback immediately and requests cancellation of the running DSH turn. Generation identifiers in Muxiva discard late worker results.
