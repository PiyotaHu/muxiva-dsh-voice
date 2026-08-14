# Muxiva Voice for DeepSeek Harness

Local-first, full-duplex voice for the official [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness), orchestrated by [Muxiva](https://github.com/PiyotaHu/muxiva).

Your microphone, VAD, ASR, sentence scheduling, TTS, playback and interruption path stay on the Mac. DSH remains the stateful Agent harness and keeps its tools, sessions and Web transcript.

> Alpha: the integration contract and source-checkout path are testable today. A public one-command binary install additionally needs a Muxiva macOS arm64 Python wheel; see [RFC-0001](docs/reference/rfc-0001-python-wheel.md).

## What runs where

```text
DSH Web microphone ──PCM16──▶ Muxiva Graph
                              ├─ Silero VAD ──barge-in──┐
                              └─ Zipformer ASR ──final──┼─▶ DSH Session / Agent / Tools
DSH assistant deltas ─────────▶ sentence buffer ─▶ speech formatter ─▶ Kokoro ─▶ browser speaker
```

- **Muxiva owns the real-time pipeline:** typed Frames, bounded queues, backpressure, Signals, cancellation and observability.
- **DSH owns the Agent:** session history, model selection, tools, permissions and Web UI.
- **The plugin owns only the bridge:** additive DSH UI, a versioned loopback protocol and project Node Packs. Neither upstream repository is patched.

## Quick start from source (Apple Silicon)

Prerequisites: macOS arm64, Node.js 22.19+, Python 3.11–3.13, Rust, Muxiva source at `../muxiva`, the `muxiva` CLI, and an installed official DSH CLI.

```bash
git clone https://github.com/muxiva/muxiva-dsh-voice.git
cd muxiva-dsh-voice

# Build the project Python environment and fetch SHA-256 pinned models.
npm run doctor -- --fix
npm run models

# Install this checkout as a DSH Bundle. No prepare script is executed.
dsh plugin --profile web add .
```

Start the two supervised processes:

```bash
# Terminal A
npm start

# Terminal B
dsh --profile web
```

Open the printed DSH URL, create or open a session, then select the microphone button in the composer. The button glow follows input energy; its tooltip moves through listening, hearing, thinking and speaking.

## Published release UX

Once the Muxiva wheel gate in RFC-0001 is shipped, the intended user path is:

```bash
dsh plugin --profile web add @muxiva/dsh-voice
npx @muxiva/dsh-voice setup
npx @muxiva/dsh-voice start
```

The package is a native DSH Bundle (`dsh.bundle`) and a dual-face Web plugin (`dsh.client`). Discovery uses the GitHub [`dsh-plugin`](https://github.com/topics/dsh-plugin) topic; DSH does not currently operate a centralized plugin marketplace.

## Security posture

- The speech bridge binds only to loopback and accepts one active client.
- Model artifacts are pinned by immutable revision/URL and SHA-256.
- No API key, microphone recording or transcript is uploaded by this plugin.
- Browser echo cancellation, noise suppression and automatic gain control are requested.
- Queue capacities are finite; stale TTS and Agent output are fenced after barge-in.
- The DSH plugin adds UI through a documented slot and uses only `Session.prompt` / `Session.cancel`; it never changes the agent loop.

See the [security model](docs/reference/security.md), [protocol](docs/reference/protocol.md), [model licenses](THIRD_PARTY_NOTICES.md), and [contribution guide](CONTRIBUTING.md).

## Development

```bash
npm test
npm run pack:smoke
python3 -m compileall -q python .muxiva/nodes

# After setup/models: boots the real Graph and certifies TTS -> PCM -> VAD/ASR.
npm run test:e2e
```

The first certification target is a MacBook Pro with M1 Pro. Latency budgets and the acceptance matrix live in [Performance](docs/guide/performance.md).

## License

Apache-2.0. Models remain under their own licenses and are downloaded at setup time; they are not redistributed in the npm package.
